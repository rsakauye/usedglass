"""Polite HTTP helper: robots.txt aware, per-host rate limiting, identifiable user agent."""
import time
import urllib.parse
import urllib.request
import urllib.robotparser

UA = "UsedGlassBot/0.2 (+https://usedglass.ca/about/#bots)"
DEFAULT_DELAY = 2.0
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
    try:
        return urllib.request.urlopen(req, timeout=timeout).read()
    finally:
        _last[host] = time.time()
