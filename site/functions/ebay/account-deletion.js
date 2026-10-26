// GET/POST /ebay/account-deletion: eBay Marketplace Account Deletion endpoint.
// https://developer.ebay.com/marketplace-account-deletion
//
// GET ?challenge_code= verifies the endpoint. challengeResponse is the lowercase hex SHA-256 of
// challengeCode + EBAY_VERIFICATION_TOKEN + EBAY_ENDPOINT_URL (eBay's Node SDK hashes those three
// in that order). POST is acknowledged with 204 immediately; signature checks run in waitUntil.
//
// Verification follows eBay's event-notification-nodejs-sdk: base64-decode the x-ebay-signature
// header, fetch the ECDSA public key from the Notification API (getPublicKey) with an application
// access token (client credentials), and verify JSON.stringify(message) with SHA-1. The SDK calls
// crypto.createVerify('ssl3-sha1'), which is ECDSA over SHA-1. Web Crypto needs the same hash and
// the DER signature converted to IEEE P1363. The public key is cached for about an hour.
//
// Pages secrets (not created here): EBAY_VERIFICATION_TOKEN, EBAY_ENDPOINT_URL, and the same
// EBAY_CLIENT_ID / EBAY_CLIENT_SECRET names the scraper workflow already uses.
const TOKEN_URL = 'https://api.ebay.com/identity/v1/oauth2/token';
const PUBLIC_KEY_URL = 'https://api.ebay.com/commerce/notification/v1/public_key/';
const OAUTH_SCOPE = 'https://api.ebay.com/oauth/api_scope';
const TOKEN_RE = /^[A-Za-z0-9_-]{32,80}$/;
const KEY_TTL_MS = 60 * 60 * 1000;
const KEY_START = '-----BEGIN PUBLIC KEY-----';
const KEY_END = '-----END PUBLIC KEY-----';
const MAX_BODY = 262144;

const keyCache = new Map();
const tokenCache = { accessToken: null, exp: 0 };

export function resetCachesForTests() {
  keyCache.clear();
  tokenCache.accessToken = null;
  tokenCache.exp = 0;
}

export function expireCachesForTests() {
  for (const hit of keyCache.values()) hit.exp = 0;
  tokenCache.exp = 0;
}

// Nothing is stored under an eBay account key. Currency gaps use the fixed label "eBay US seller"
// and never a username, userId, or eiasToken, so this deletes nothing.
// If a future store is keyed by one of those fields, delete that account's rows here.
// Do not log username, userId, or eiasToken.
export const accountDeletion = {
  async deleteStoredData(_account) {},
};

export async function challengeResponse(challengeCode, verificationToken, endpoint) {
  const bytes = new TextEncoder().encode(String(challengeCode) + String(verificationToken) + String(endpoint));
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

function jsonError(status, error) {
  return Response.json({ error }, { status, headers: { 'cache-control': 'no-store' } });
}

export async function onRequestGet(context) {
  const challengeCode = new URL(context.request.url).searchParams.get('challenge_code');
  if (!challengeCode || challengeCode.length > 256) return jsonError(400, 'missing_challenge_code');
  const env = context.env || {};
  const token = String(env.EBAY_VERIFICATION_TOKEN || '').trim();
  const endpoint = String(env.EBAY_ENDPOINT_URL || '').trim();
  if (!TOKEN_RE.test(token) || !endpoint) return jsonError(500, 'not_configured');
  const challengeResponseValue = await challengeResponse(challengeCode, token, endpoint);
  return Response.json({ challengeResponse: challengeResponseValue }, { status: 200, headers: { 'cache-control': 'no-store' } });
}

export async function onRequestPost(context) {
  const signature = context.request.headers.get('x-ebay-signature');
  let bodyText = '';
  try { bodyText = await context.request.text(); } catch { bodyText = ''; }
  if (bodyText.length > MAX_BODY) bodyText = '';
  // Do not destructure waitUntil; Pages requires the method call on context.
  context.waitUntil(handleNotification(bodyText, signature, context.env || {}));
  return new Response(null, { status: 204 });
}

export const onRequest = () => new Response('Method not allowed', { status: 405, headers: { allow: 'GET, POST' } });

async function handleNotification(bodyText, signature, env) {
  let notificationId = null;
  try {
    const message = JSON.parse(bodyText);
    const id = message && message.notification && message.notification.notificationId;
    if (typeof id === 'string') notificationId = id;
    if (!message || typeof message !== 'object' || !message.metadata || !message.notification) throw new Error('bad message');
    if (!(await verifySignature(message, signature, env))) throw new Error('signature rejected');
    await accountDeletion.deleteStoredData(message.notification.data);
    console.log(JSON.stringify({ source: 'ebay-account-deletion', ok: true, notificationId }));
  } catch {
    console.log(JSON.stringify({ source: 'ebay-account-deletion', ok: false, notificationId }));
  }
}

async function verifySignature(message, signatureHeader, env) {
  if (!signatureHeader) return false;
  const header = JSON.parse(new TextDecoder().decode(b64decode(signatureHeader)));
  if (!header || typeof header.kid !== 'string' || typeof header.signature !== 'string') return false;
  const publicKey = await getPublicKey(header.kid, env);
  const cryptoKey = await crypto.subtle.importKey('spki', spkiFromPem(formatKey(publicKey.key)), { name: 'ECDSA', namedCurve: 'P-256' }, false, ['verify']);
  const raw = derToRaw(b64decode(header.signature));
  const data = new TextEncoder().encode(JSON.stringify(message));
  return crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-1' }, cryptoKey, raw, data);
}

// Same newline normalization as the Node SDK's formatKey, before the PEM body is decoded.
function formatKey(key) {
  return String(key).replace(KEY_START, `${KEY_START}\n`).replace(KEY_END, `\n${KEY_END}`);
}

function spkiFromPem(pem) {
  const b64 = pem.replace(/-----BEGIN PUBLIC KEY-----/g, '').replace(/-----END PUBLIC KEY-----/g, '').replace(/\s+/g, '');
  return b64decode(b64);
}

function b64decode(s) {
  const norm = String(s).replace(/-/g, '+').replace(/_/g, '/');
  const pad = norm.length % 4 === 0 ? norm : norm + '='.repeat(4 - (norm.length % 4));
  const bin = atob(pad);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

// ECDSA DER (SEQUENCE of two INTEGERs) -> raw r||s, 32 bytes each, for P-256 Web Crypto.
function derToRaw(bytes, size = 32) {
  if (bytes[0] !== 0x30) throw new Error('bad signature');
  let offset = 2;
  if (bytes[1] & 0x80) offset = 2 + (bytes[1] & 0x7f);
  const readInt = () => {
    if (bytes[offset] !== 0x02) throw new Error('bad signature');
    const len = bytes[offset + 1];
    let v = bytes.slice(offset + 2, offset + 2 + len);
    offset += 2 + len;
    while (v.length > size && v[0] === 0) v = v.slice(1);
    if (v.length > size) throw new Error('bad signature');
    const out = new Uint8Array(size);
    out.set(v, size - v.length);
    return out;
  };
  const r = readInt();
  const s = readInt();
  const raw = new Uint8Array(size * 2);
  raw.set(r, 0);
  raw.set(s, size);
  return raw;
}

function basicAuth(id, secret) {
  const bytes = new TextEncoder().encode(`${id}:${secret}`);
  let bin = '';
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

async function discard(res) {
  try { await res.arrayBuffer(); } catch { /* ignore */ }
}

async function getAppToken(env) {
  if (tokenCache.accessToken && tokenCache.exp > Date.now()) return tokenCache.accessToken;
  const id = env.EBAY_CLIENT_ID;
  const secret = env.EBAY_CLIENT_SECRET;
  if (!id || !secret) throw new Error('missing client credentials');
  const res = await fetch(TOKEN_URL, {
    method: 'POST',
    headers: { authorization: `Basic ${basicAuth(id, secret)}`, 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ grant_type: 'client_credentials', scope: OAUTH_SCOPE }),
    redirect: 'manual',
  });
  if (!res.ok) { await discard(res); throw new Error('token request failed'); }
  const body = await res.json();
  if (!body || typeof body.access_token !== 'string' || !body.access_token) throw new Error('token request failed');
  const ttlSec = Number(body.expires_in);
  const life = (Number.isFinite(ttlSec) ? ttlSec : 7200) - 60;
  tokenCache.accessToken = body.access_token;
  tokenCache.exp = Date.now() + Math.max(0, life) * 1000;
  return body.access_token;
}

async function getPublicKey(kid, env) {
  const hit = keyCache.get(kid);
  if (hit && hit.exp > Date.now()) return hit.value;
  const token = await getAppToken(env);
  const res = await fetch(PUBLIC_KEY_URL + encodeURIComponent(kid), {
    headers: { authorization: `Bearer ${token}`, accept: 'application/json' },
    redirect: 'manual',
  });
  if (!res.ok) { await discard(res); throw new Error('public key request failed'); }
  const body = await res.json();
  if (!body || typeof body.key !== 'string') throw new Error('public key request failed');
  keyCache.set(kid, { value: body, exp: Date.now() + KEY_TTL_MS });
  return body;
}
