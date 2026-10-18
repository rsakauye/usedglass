"""Polite HTTP helper: robots.txt aware, per-host rate limiting, identifiable user agent."""
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

UA = "UsedGlassBot/0.2 (+https://usedglass.ca/about/#bots)"
DEFAULT_DELAY = 2.0
RETRIES = 2          # transient network errors / 429 / 5xx only
BACKOFF = 10.0       # seconds, grows linearly per attempt
_last: dict[str, float] = {}
_robots: dict[str, urllib.robotparser.RobotFileParser] = {}
_delays: dict[str, float] = {}


def _robots_for(url: str) -> urllib.robotparser.RobotFileParser:
    p = urllib.parse.urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(base + "/robots.txt", headers={"User-Agent": UA})
            rp.parse(urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore").splitlines())
        except Exception:
            rp.parse([])
        _robots[base] = rp
        cd = rp.crawl_delay(UA) or rp.crawl_delay("*")
        if cd:
            _delays[p.netloc] = float(cd)
    return _robots[base]


def allowed(url: str) -> bool:
    return _robots_for(url).can_fetch(UA, url)


def fetch(url: str, data: bytes | None = None, headers: dict | None = None, check_robots: bool = True,
          timeout: int = 60) -> bytes:
    if check_robots and not allowed(url):
        raise PermissionError(f"robots.txt disallows {url}")
    host = urllib.parse.urlparse(url).netloc
    delay = max(DEFAULT_DELAY, _delays.get(host, 0))
    wait = delay - (time.time() - _last.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    h = {"User-Agent": UA, "Accept": "*/*"}
    if data is not None:
        h["Content-Type"] = "application/x-www-form-urlencoded"
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    for attempt in range(RETRIES + 1):
        try:
            return urllib.request.urlopen(req, timeout=timeout).read()
        except urllib.error.HTTPError as e:
            # retry only "try again later" answers; a 403/404 is an answer, not a blip
            if e.code not in (429, 500, 502, 503, 504) or attempt == RETRIES:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            if attempt == RETRIES:
                raise
        finally:
            _last[host] = time.time()
        time.sleep(BACKOFF * (attempt + 1))
    raise RuntimeError("unreachable")
