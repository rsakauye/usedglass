// Challenge hash and GET/POST handler tests for site/functions/ebay/account-deletion.js.
import test from 'node:test';
import assert from 'node:assert/strict';
import nodeCrypto from 'node:crypto';
import {
  accountDeletion, challengeResponse, expireCachesForTests, onRequest, onRequestGet, onRequestPost, resetCachesForTests,
} from '../site/functions/ebay/account-deletion.js';

// Known vector, computed with Python hashlib.sha256 of the concatenation in this order
// (independent of challengeResponse): challenge code, verification token, endpoint URL.
const CODE = 'c8314a63-6f4f-4f1e-9a6b-2c0d5e7f9a1b';
const TOKEN = '0123456789abcdefghijklmnopqrstuvwxyzABCD';
const ENDPOINT = 'https://usedglass.ca/ebay/account-deletion';
const EXPECTED = 'c005b6ba252da561579daedc2adc9413ab111d7a226449f5e3ba28c8a8f9957e';

const FIXTURE_USER = 'fixture-username';
const FIXTURE_ID = 'fixture-user-id';
const FIXTURE_EIAS = 'fixture-eias-token';
const NOTIFICATION_ID = '8b9c0d1e-2222-4333-8444-555566667777';
const ENV = { EBAY_CLIENT_ID: 'test-client-id', EBAY_CLIENT_SECRET: 'test-client-secret' };

const { privateKey, publicKey } = nodeCrypto.generateKeyPairSync('ec', { namedCurve: 'prime256v1' });
const message = {
  metadata: { topic: 'MARKETPLACE_ACCOUNT_DELETION', schemaVersion: '1.0', deprecated: false },
  notification: {
    notificationId: NOTIFICATION_ID,
    eventDate: '2026-10-26T00:00:00.000Z',
    publishDate: '2026-10-26T00:00:00.000Z',
    publishAttemptCount: 1,
    data: { username: FIXTURE_USER, userId: FIXTURE_ID, eiasToken: FIXTURE_EIAS },
  },
};
const payload = JSON.stringify(message);
const der = nodeCrypto.sign('ssl3-sha1', Buffer.from(payload), privateKey);
const singleLineKey = `-----BEGIN PUBLIC KEY-----${publicKey.export({ type: 'spki', format: 'der' }).toString('base64')}-----END PUBLIC KEY-----`;
const xEbaySignature = Buffer.from(JSON.stringify({
  alg: 'ECDSA', kid: 'test-key-1', signature: der.toString('base64'), digest: 'SHA1',
})).toString('base64');

function postContext(body, signature, waitUntil) {
  return {
    request: new Request(ENDPOINT, {
      method: 'POST',
      headers: { 'content-type': 'application/json', ...(signature ? { 'x-ebay-signature': signature } : {}) },
      body,
    }),
    env: ENV,
    waitUntil,
  };
}

async function withLogs(fn) {
  const lines = [];
  const orig = console.log;
  console.log = (...args) => { lines.push(args.map(String).join(' ')); };
  try { return { result: await fn(), lines }; }
  finally { console.log = orig; }
}

function assertNoSecrets(text) {
  for (const secret of [FIXTURE_USER, FIXTURE_ID, FIXTURE_EIAS, TOKEN, ENV.EBAY_CLIENT_SECRET, 'app-token']) {
    assert.equal(text.includes(secret), false);
  }
}

test('challenge hash matches the known vector', async () => {
  assert.equal(await challengeResponse(CODE, TOKEN, ENDPOINT), EXPECTED);
});

test('GET returns the challenge JSON', async () => {
  const res = await onRequestGet({
    request: new Request(`${ENDPOINT}?challenge_code=${CODE}`),
    env: { EBAY_VERIFICATION_TOKEN: TOKEN, EBAY_ENDPOINT_URL: ENDPOINT },
  });
  assert.equal(res.status, 200);
  assert.match(res.headers.get('content-type'), /^application\/json/);
  const text = await res.text();
  assert.deepEqual(JSON.parse(text), { challengeResponse: EXPECTED });
  assertNoSecrets(text);
});

test('GET without a challenge code is 400 and does not echo secrets', async () => {
  const res = await onRequestGet({
    request: new Request(ENDPOINT),
    env: { EBAY_VERIFICATION_TOKEN: TOKEN, EBAY_ENDPOINT_URL: ENDPOINT },
  });
  assert.equal(res.status, 400);
  const text = await res.text();
  assert.deepEqual(JSON.parse(text), { error: 'missing_challenge_code' });
  assertNoSecrets(text);
});

test('GET with a missing or invalid secret is 500 and does not echo values', async () => {
  const missingToken = await onRequestGet({
    request: new Request(`${ENDPOINT}?challenge_code=${CODE}`),
    env: { EBAY_ENDPOINT_URL: ENDPOINT },
  });
  assert.equal(missingToken.status, 500);
  const missingTokenBody = await missingToken.text();
  assert.deepEqual(JSON.parse(missingTokenBody), { error: 'not_configured' });
  assert.equal(missingTokenBody.includes(ENDPOINT), false);

  const missingEndpoint = await onRequestGet({
    request: new Request(`${ENDPOINT}?challenge_code=${CODE}`),
    env: { EBAY_VERIFICATION_TOKEN: TOKEN },
  });
  assert.equal(missingEndpoint.status, 500);
  const missingEndpointBody = await missingEndpoint.text();
  assert.equal(missingEndpointBody.includes(TOKEN), false);

  const bad = 'not a valid token because of spaces!!';
  const badToken = await onRequestGet({
    request: new Request(`${ENDPOINT}?challenge_code=${CODE}`),
    env: { EBAY_VERIFICATION_TOKEN: bad, EBAY_ENDPOINT_URL: ENDPOINT },
  });
  assert.equal(badToken.status, 500);
  assert.equal((await badToken.text()).includes(bad), false);
});

test('other methods are 405', async () => {
  const res = await onRequest();
  assert.equal(res.status, 405);
});

test('POST returns 204 before verification finishes', async () => {
  resetCachesForTests();
  let release;
  const gate = new Promise((resolve) => { release = resolve; });
  const origFetch = globalThis.fetch;
  const origHook = accountDeletion.deleteStoredData;
  let calls = 0;
  accountDeletion.deleteStoredData = async () => { calls += 1; };
  globalThis.fetch = () => gate.then(() => new Response('nope', { status: 500 }));
  let waited;
  try {
    const res = await onRequestPost(postContext(payload, xEbaySignature, (p) => { waited = p; }));
    assert.equal(res.status, 204);
    assert.equal(await res.text(), '');
    let settled = false;
    waited.then(() => { settled = true; }, () => { settled = true; });
    await Promise.resolve();
    await Promise.resolve();
    assert.equal(settled, false);
    release();
    const { lines } = await withLogs(() => waited);
    assert.equal(calls, 0);
    assert.equal(JSON.parse(lines[0]).ok, false);
    assertNoSecrets(lines.join('\n'));
  } finally {
    release();
    globalThis.fetch = origFetch;
    accountDeletion.deleteStoredData = origHook;
    resetCachesForTests();
  }
});

test('POST verifies a signed notification, caches the key, and logs only the notification id', async () => {
  resetCachesForTests();
  const origFetch = globalThis.fetch;
  const origHook = accountDeletion.deleteStoredData;
  const fetches = [];
  let hookCalls = 0;
  accountDeletion.deleteStoredData = async () => { hookCalls += 1; };
  globalThis.fetch = async (url, init) => {
    fetches.push({ url: String(url), init });
    if (String(url) === 'https://api.ebay.com/identity/v1/oauth2/token') {
      const body = init.body instanceof URLSearchParams ? init.body.toString() : String(init.body);
      assert.match(body, /grant_type=client_credentials/);
      assert.match(body, /scope=https%3A%2F%2Fapi\.ebay\.com%2Foauth%2Fapi_scope/);
      assert.equal(init.headers.authorization, `Basic ${Buffer.from(`${ENV.EBAY_CLIENT_ID}:${ENV.EBAY_CLIENT_SECRET}`).toString('base64')}`);
      return new Response(JSON.stringify({ access_token: 'app-token', expires_in: 7200 }), { status: 200 });
    }
    assert.equal(String(url), 'https://api.ebay.com/commerce/notification/v1/public_key/test-key-1');
    assert.equal(init.headers.authorization, 'Bearer app-token');
    return new Response(JSON.stringify({ key: singleLineKey, algorithm: 'ECDSA', digest: 'SHA1' }), { status: 200 });
  };
  try {
    const run = async () => {
      let waited;
      const res = await onRequestPost(postContext(payload, xEbaySignature, (p) => { waited = p; }));
      assert.equal(res.status, 204);
      return waited;
    };
    const first = await withLogs(run);
    assert.equal(hookCalls, 1);
    assert.deepEqual(JSON.parse(first.lines[0]), { source: 'ebay-account-deletion', ok: true, notificationId: NOTIFICATION_ID });
    assertNoSecrets(first.lines.join('\n'));
    assert.equal(fetches.filter((f) => f.url.includes('/public_key/')).length, 1);
    assert.equal(fetches.filter((f) => f.url.includes('/oauth2/token')).length, 1);

    const second = await withLogs(run);
    assert.equal(hookCalls, 2);
    assert.equal(JSON.parse(second.lines[0]).ok, true);
    assert.equal(fetches.length, 2);

    expireCachesForTests();
    await withLogs(run);
    assert.equal(fetches.filter((f) => f.url.includes('/public_key/')).length, 2);
    assert.equal(fetches.filter((f) => f.url.includes('/oauth2/token')).length, 2);
  } finally {
    globalThis.fetch = origFetch;
    accountDeletion.deleteStoredData = origHook;
    resetCachesForTests();
  }
});

test('POST with a bad signature does not delete and does not log account fields', async () => {
  resetCachesForTests();
  const origFetch = globalThis.fetch;
  const origHook = accountDeletion.deleteStoredData;
  let hookCalls = 0;
  accountDeletion.deleteStoredData = async () => { hookCalls += 1; };
  globalThis.fetch = async (url) => {
    if (String(url).includes('/oauth2/token')) return new Response(JSON.stringify({ access_token: 'app-token', expires_in: 7200 }), { status: 200 });
    return new Response(JSON.stringify({ key: singleLineKey, algorithm: 'ECDSA', digest: 'SHA1' }), { status: 200 });
  };
  const badDer = nodeCrypto.sign('ssl3-sha1', Buffer.from(payload + ' '), privateKey);
  const badHeader = Buffer.from(JSON.stringify({ alg: 'ECDSA', kid: 'test-key-1', signature: badDer.toString('base64') })).toString('base64');
  let lines;
  try {
    const logged = await withLogs(async () => {
      let waited;
      const res = await onRequestPost(postContext(payload, badHeader, (p) => { waited = p; }));
      assert.equal(res.status, 204);
      return waited;
    });
    lines = logged.lines;
  } finally {
    globalThis.fetch = origFetch;
    accountDeletion.deleteStoredData = origHook;
    resetCachesForTests();
  }
  assert.equal(hookCalls, 0);
  assert.deepEqual(JSON.parse(lines[0]), { source: 'ebay-account-deletion', ok: false, notificationId: NOTIFICATION_ID });
  assertNoSecrets(lines.join('\n'));
});

function headerFor(kid) {
  return Buffer.from(JSON.stringify({ alg: 'ECDSA', kid, signature: der.toString('base64'), digest: 'SHA1' })).toString('base64');
}

async function runPost(signature) {
  let waited;
  const res = await onRequestPost(postContext(payload, signature, (p) => { waited = p; }));
  assert.equal(res.status, 204);
  return waited;
}

test('a failed key lookup is remembered, so the same unknown key id does not call eBay again', async () => {
  resetCachesForTests();
  const origFetch = globalThis.fetch;
  const origHook = accountDeletion.deleteStoredData;
  let hookCalls = 0;
  accountDeletion.deleteStoredData = async () => { hookCalls += 1; };
  const keyFetches = [];
  globalThis.fetch = async (url) => {
    if (String(url).includes('/oauth2/token')) return new Response(JSON.stringify({ access_token: 'app-token', expires_in: 7200 }), { status: 200 });
    keyFetches.push(String(url));
    return new Response('not found', { status: 404 });
  };
  try {
    const first = await withLogs(() => runPost(headerFor('made-up-kid')));
    assert.equal(JSON.parse(first.lines[0]).ok, false);
    assert.equal(keyFetches.length, 1);

    const again = await withLogs(() => runPost(headerFor('made-up-kid')));
    assert.equal(JSON.parse(again.lines[0]).ok, false);
    assert.equal(keyFetches.length, 1, 'same kid must not trigger a second eBay call');

    await withLogs(() => runPost(headerFor('another-kid')));
    assert.equal(keyFetches.length, 2, 'a different kid is still looked up');
    assert.equal(hookCalls, 0);
  } finally {
    globalThis.fetch = origFetch;
    accountDeletion.deleteStoredData = origHook;
    resetCachesForTests();
  }
});

test('the failure memory is bounded and a failure never blocks a later good key', async () => {
  resetCachesForTests();
  const origFetch = globalThis.fetch;
  const origHook = accountDeletion.deleteStoredData;
  accountDeletion.deleteStoredData = async () => {};
  let keyFetches = 0;
  let good = false;
  globalThis.fetch = async (url) => {
    if (String(url).includes('/oauth2/token')) return new Response(JSON.stringify({ access_token: 'app-token', expires_in: 7200 }), { status: 200 });
    keyFetches += 1;
    if (good) return new Response(JSON.stringify({ key: singleLineKey, algorithm: 'ECDSA', digest: 'SHA1' }), { status: 200 });
    return new Response('nope', { status: 500 });
  };
  try {
    await withLogs(async () => { for (let i = 0; i < 150; i += 1) await runPost(headerFor(`junk-${i}`)); });
    assert.equal(keyFetches, 150);
    // The oldest entries were dropped to stay within the limit, so junk-0 is looked up again.
    await withLogs(() => runPost(headerFor('junk-0')));
    assert.equal(keyFetches, 151);
    // The newest entry is still remembered.
    await withLogs(() => runPost(headerFor('junk-149')));
    assert.equal(keyFetches, 151);

    // Once the memory is cleared and eBay answers, a real key verifies and notifies.
    expireCachesForTests();
    good = true;
    const ok = await withLogs(() => runPost(xEbaySignature));
    assert.equal(JSON.parse(ok.lines[0]).ok, true);
  } finally {
    globalThis.fetch = origFetch;
    accountDeletion.deleteStoredData = origHook;
    resetCachesForTests();
  }
});
