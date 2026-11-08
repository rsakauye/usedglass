// Dealer listing titles are untrusted text. They must never be able to end or confuse an inline <script>.
// Run: node --test tests/
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { safeJson } from '../site/src/lib/safeJson.js';

const LS = String.fromCharCode(0x2028);
const PS = String.fromCharCode(0x2029);
const PAYLOADS = [
  'Canon FD to Sony E mount adapter </script><script>alert(1)</script>',
  'x </SCRIPT >y',
  'x </script/>y',
  'x <!--<script>y',
  'a & b > c < d',
  'line' + LS + 'sep' + PS + 'end',
  'quote " and \\ slash',
];

test('output holds none of the characters that can end or confuse a script element', () => {
  for (const t of PAYLOADS) {
    const out = safeJson({ t });
    for (const ch of ['<', '>', '&', LS, PS]) assert.ok(!out.includes(ch), `${JSON.stringify(t)} leaked ${JSON.stringify(ch)}`);
  }
});

test('JSON.parse gives back exactly what went in', () => {
  const value = { adapters: PAYLOADS.map((t, i) => ({ t, p: i, ok: true, n: null })), list: [1, 2], s: 'plain' };
  assert.deepEqual(JSON.parse(safeJson(value)), value);
});

test('the adapter page does not pass scraped listings through define:vars', () => {
  const page = readFileSync(new URL('../site/src/pages/adapt.astro', import.meta.url), 'utf8');
  assert.doesNotMatch(page, /define:vars=\{\{[^}]*\badapters\b/);
  assert.match(page, /id="ad-data"/);
  assert.match(page, /safeJson\(/);
});
