// POST /api/event: event submissions from /events/. Verifies Turnstile on the server, rate-limits by a
// hashed IP (hash only, kept 1 hour), and stores the entry in KV under "pending:" for manual review.
// Nothing is ever published automatically. Entries expire 90 days after the event (privacy policy).
const LIM = { org: 100, email: 200, title: 140, when: 60, venue: 140, city: 80, url: 500, desc: 2000 };
const MAX_PER_HOUR = 5;
const clean = (v, n) => String(v ?? '').replace(/[\u0000-\u0008\u000b-\u001f\u007f]/g, ' ').trim().slice(0, n);

async function sha256(s) {
  const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, '0')).join('').slice(0, 32);
}
function reply(request, status, body) {
  const wantsJson = (request.headers.get('accept') || '').includes('application/json');
  if (wantsJson) return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });
  const q = body.ok ? 'submitted=1' : 'submit_error=' + encodeURIComponent(body.error || 'error');
  return Response.redirect(new URL('/events/?' + q + '#submit', request.url).href, 303);
}

// Any unexpected failure (e.g. the free KV daily write quota is used up during a traffic spike) gets a friendly
// message instead of a raw 500, so the form tells people to email us.
export async function onRequestPost(ctx) {
  try { return await handle(ctx); }
  catch { return reply(ctx.request, 503, { ok: false, error: 'Submissions are busy right now. Please try again later or email hello@usedglass.ca.' }); }
}

async function handle({ request, env }) {
  if (!env.UG_EVENTS || !env.TURNSTILE_SECRET) return reply(request, 503, { ok: false, error: 'Submissions are switched off right now. Please email hello@usedglass.ca.' });
  let f;
  try {
    const ct = request.headers.get('content-type') || '';
    if (Number(request.headers.get('content-length') || 0) > 20000) throw new Error('big');
    f = ct.includes('application/json') ? await request.json() : Object.fromEntries(await request.formData());
  } catch { return reply(request, 400, { ok: false, error: "We couldn't read that form." }); }

  if (clean(f.website, 50)) return reply(request, 200, { ok: true }); // honeypot: pretend success, store nothing
  const ip = request.headers.get('cf-connecting-ip') || '';

  // Turnstile, server side.
  const token = clean(f['cf-turnstile-response'], 2048);
  if (!token) return reply(request, 400, { ok: false, error: 'Please complete the spam check.' });
  const tv = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
    method: 'POST', body: new URLSearchParams({ secret: env.TURNSTILE_SECRET, response: token, remoteip: ip }),
  }).then((r) => r.json()).catch(() => ({ success: false }));
  if (!tv.success) return reply(request, 400, { ok: false, error: 'The spam check failed. Please try again.' });

  // Light rate limit: 5 submissions per hour per (hashed) IP.
  const rk = 'rl:' + (await sha256('ug-events|' + ip));
  const n = Number((await env.UG_EVENTS.get(rk)) || 0);
  if (n >= MAX_PER_HOUR) return reply(request, 429, { ok: false, error: 'Too many submissions from here. Please try again in an hour.' });
  await env.UG_EVENTS.put(rk, String(n + 1), { expirationTtl: 3600 });

  const e = {
    organizer: clean(f.organizer, LIM.org), email: clean(f.email, LIM.email).toLowerCase(), title: clean(f.title, LIM.title),
    date: clean(f.date, 10), time: clean(f.time, 5), end_date: clean(f.end_date, 10),
    venue: clean(f.venue, LIM.venue), city: clean(f.city, LIM.city), province: clean(f.province, 2).toUpperCase(),
    url: clean(f.url, LIM.url), description: clean(f.description, LIM.desc),
  };
  const missing = ['organizer', 'email', 'title', 'date', 'venue', 'city', 'url', 'description'].filter((k) => !e[k]);
  if (missing.length) return reply(request, 400, { ok: false, error: 'Please fill in: ' + missing.join(', ') + '.' });
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e.email)) return reply(request, 400, { ok: false, error: 'Please check the email address.' });
  if (!/^\d{4}-\d{2}-\d{2}$/.test(e.date) || (e.end_date && !/^\d{4}-\d{2}-\d{2}$/.test(e.end_date)) || (e.time && !/^\d{2}:\d{2}$/.test(e.time))) return reply(request, 400, { ok: false, error: 'Please check the date and time.' });
  let u; try { u = new URL(e.url); } catch {}
  if (!u || !/^https?:$/.test(u.protocol)) return reply(request, 400, { ok: false, error: 'Please give a link starting with https://' });
  const last = Date.parse((e.end_date || e.date) + 'T23:59:59-07:00');
  const now = Date.now();
  if (!(last > now - 864e5) || last > now + 2 * 365 * 864e5) return reply(request, 400, { ok: false, error: 'Please give an upcoming date (within two years).' });

  e.submitted_at = new Date().toISOString();
  e.status = 'pending';
  e.test = clean(f.test, 10) === 'yes' || undefined;
  const key = `pending:${e.submitted_at}:${crypto.randomUUID().slice(0, 8)}`;
  // Expire 90 days after the event's last day (covers the email address as well).
  await env.UG_EVENTS.put(key, JSON.stringify(e), { expiration: Math.floor(last / 1000) + 90 * 86400 });
  return reply(request, 200, { ok: true });
}
export const onRequest = ({ request }) => new Response('Method not allowed', { status: 405, headers: { allow: 'POST' } });
