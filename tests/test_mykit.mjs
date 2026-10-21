// Unit tests for the client-side kit builder (site/src/lib/mykit-core.js). Run: node --test tests/
import test from 'node:test';
import assert from 'node:assert/strict';
import * as K from '../site/src/lib/mykit-core.js';
import { itemsHtml, totalsHtml, KIT_CSS } from '../site/src/lib/mykit-ui.js';

test('mount rules: native, adapters and no-fit', () => {
  assert.equal(K.mountCompat('Sony E', 'Sony E').status, 'ok');
  assert.equal(K.mountCompat('Canon EF', 'Sony E').status, 'adapter');
  assert.match(K.mountCompat('Canon EF', 'Canon RF').note, /EF-EOS R/);
  assert.equal(K.mountCompat('Canon RF', 'Canon EF').status, 'nofit');
  assert.equal(K.mountCompat('Nikon F', 'Nikon Z').status, 'adapter');
  assert.equal(K.mountCompat('Nikon Z', 'Nikon F').status, 'nofit');
  assert.equal(K.mountCompat('Fujifilm X', 'Sony E').status, 'nofit');
  assert.equal(K.mountCompat('M42', 'Fujifilm X').status, 'adapter');
  assert.equal(K.mountCompat('Canon FD', 'Nikon F').status, 'nofit');
  assert.equal(K.mountCompat('Fixed Lens', 'Sony E').status, 'unknown');
});

test('checkList picks the best body for each lens', () => {
  const items = [
    { n: 'A7', c: 'body', m: 'Sony E' }, { n: 'R6', c: 'body', m: 'Canon RF' },
    { n: 'EF 50', c: 'lens', m: 'Canon EF' }, { n: 'FE 35', c: 'lens', m: 'Sony E' }, { n: 'X 23', c: 'lens', m: 'Fujifilm X' },
  ];
  const r = K.checkList(items);
  assert.equal(r.get(items[2]).status, 'adapter');
  assert.equal(r.get(items[2]).body.n, 'R6');
  assert.equal(r.get(items[3]).status, 'ok');
  assert.equal(r.get(items[4]).status, 'nofit');
  assert.equal(K.checkList([{ n: 'lens', c: 'lens', m: 'Sony E' }]).size, 0);
});

test('totals use cheapest used and new where known', () => {
  const cat = K.indexCatalog([
    ['a', 'A', 'camera', 'X', 'Sony E', 800, 'D1', '', 60, 1000, 'N', '', 2],
    ['b', 'B', 'lens', 'X', 'Sony E', null, '', '', null, 500, 'N', '', 0],
  ]);
  const t = K.kitTotals([{ k: 'a', n: 'A', c: 'body' }, { k: 'b', n: 'B', c: 'lens' }, { n: 'strap', c: 'bag' }], cat);
  assert.deepEqual([t.items, t.used, t.usedN, t.new, t.newN, t.best, t.bestN], [3, 800, 1, 1500, 2, 1300, 2]);
});

test('share links round-trip and reject junk', async () => {
  const list = { name: 'Wedding kit', items: [{ k: 'camera-sony-a6400', n: 'Sony A6400', c: 'body', t: 900 }, { k: null, n: 'Godox V1', c: 'flash', m: null, t: null }] };
  const h = await K.encodeList(list, 'Russ');
  assert.equal(h[0], 'z');
  const back = await K.decodeList('#' + h);
  assert.equal(back.name, 'Wedding kit');
  assert.equal(back.handle, 'Russ');
  assert.equal(back.items[0].k, 'camera-sony-a6400');
  assert.equal(back.items[0].t, 900);
  assert.equal(back.items[1].n, 'Godox V1');
  await assert.rejects(K.decodeList('#xnope'));
  await assert.rejects(K.decodeList(''));
});

test('imports are sanitised', () => {
  const s = K.cleanState({ lists: [{ id: 'a', name: 'x'.repeat(500), items: [{ k: 'lens-<script>', c: 'evil', t: -5 }, { foo: 1 }, null] }], active: 'zzz' });
  assert.equal(s.lists[0].name.length, 60);
  assert.equal(s.lists[0].items.length, 1);
  assert.equal(s.lists[0].items[0].k, 'lens-script');
  assert.equal(s.lists[0].items[0].c, 'lens');
  assert.equal(s.lists[0].items[0].t, null);
  assert.equal(s.active, 'a');
});

test('default categories from model data', () => {
  assert.equal(K.defaultCat('camera', 'Canon FD'), 'film');
  assert.equal(K.defaultCat('camera', 'Sony E'), 'body');
  assert.equal(K.defaultCat('', '', 'lens-foo'), 'lens');
});

test('owned flag: defaults to false for old data and survives share links', async () => {
  assert.equal(K.cleanItem({ k: 'camera-sony-a7-iii', n: 'A7 III', c: 'body' }).owned, false);
  assert.equal(K.cleanItem({ n: 'Tripod', owned: true }).owned, true);
  assert.equal(K.cleanItem({ n: 'Tripod', owned: 'yes' }).owned, false);
  assert.equal(K.cleanItem({ n: 'Tripod', owned: 1 }).owned, false);
  const old = K.unpackList({ v: 1, n: 'Old', i: [['camera-sony-a7-iii', '', 'body', '', 0]] });
  assert.equal(old.items[0].owned, false);
  assert.equal(K.unpackList({ v: 1, n: 'X', i: [['', 'A', 'other', '', 0, true]] }).items[0].owned, false);
  assert.equal(K.unpackList({ v: 1, n: 'X', i: [['', 'A', 'other', '', 0, '1']] }).items[0].owned, false);
  assert.equal(K.unpackList({ v: 1, n: 'X', i: [['', 'A', 'other', '', 0, 1]] }).items[0].owned, true);
  const list = { name: 'Mine', items: [K.cleanItem({ n: 'Tripod', c: 'support', owned: true }), K.cleanItem({ n: 'Strap', c: 'bag' })] };
  assert.deepEqual(K.packList(list).i.map((row) => row[5]), [1, 0]);
  const back = await K.decodeList(await K.encodeList(list));
  assert.deepEqual(back.items.map((i) => i.owned), [true, false]);
  const saved = K.cleanState(JSON.parse(JSON.stringify({ lists: [{ id: 'a', name: 'Kit', items: [{ n: 'Old' }, { n: 'Mine', owned: true }, { n: 'Num', owned: 1 }] }] })));
  assert.deepEqual(saved.lists[0].items.map((i) => i.owned), [false, true, false]);
});

test('owned badge, checkbox, filter and totals', () => {
  const items = [
    K.cleanItem({ n: 'Tripod', c: 'support', owned: true }),
    K.cleanItem({ n: 'A "strap" <x>', c: 'bag' }),
  ];
  const all = itemsHtml(items, null, { editable: true });
  const boxes = all.match(/<input type="checkbox" class="mk-owned"[^>]*>/g);
  assert.equal(boxes.length, 2);
  assert.match(boxes[0], /aria-label="Owned: Tripod"/);
  assert.match(boxes[0], /checked/);
  assert.match(boxes[1], /aria-label="Owned: A &quot;strap&quot; &lt;x&gt;"/);
  assert.doesNotMatch(boxes[1], /checked/);
  assert.doesNotMatch(all, /<x>/);
  assert.match(all, /data-idx="0"/);
  assert.match(all, /data-idx="1"/);
  assert.match(all, /mk-own-pill">Owned/);

  const ownedOnly = itemsHtml(items, null, { editable: true, show: 'owned' });
  assert.match(ownedOnly, /data-idx="0"/);
  assert.doesNotMatch(ownedOnly, /data-idx="1"/);
  const wish = itemsHtml(items, null, { show: 'wish' });
  assert.match(wish, /data-idx="1"/);
  assert.doesNotMatch(wish, /data-idx="0"/);
  assert.doesNotMatch(wish, /mk-own-pill/);
  assert.doesNotMatch(wish, /mk-owned/);

  assert.match(itemsHtml([items[1]], null, { show: 'owned' }), /Nothing in this list is marked Owned yet/);
  assert.match(itemsHtml([items[0]], null, { show: 'wish' }), /Everything in this list is marked Owned/);
  assert.match(itemsHtml([], null, { editable: true, show: 'owned' }), /Nothing here yet/);
  assert.match(itemsHtml(items, null, { show: 'nope' }), /Tripod/);
  assert.match(itemsHtml(items, null, { show: 'nope' }), /strap/);

  const readOnly = itemsHtml(items, null, {});
  assert.match(readOnly, /mk-own-pill">Owned/);
  assert.doesNotMatch(readOnly, /mk-owned/);

  assert.match(totalsHtml(items, null), />1<\/b><span class="muted">owned · 1 on the wishlist/);
  assert.match(totalsHtml([items[0]], null), />1<\/b><span class="muted">owned</);
  assert.doesNotMatch(totalsHtml([items[0]], null), /wishlist/);
  assert.doesNotMatch(totalsHtml([{ n: 'A', c: 'other', owned: 1 }], null), /owned/);
  assert.match(KIT_CSS, /min-height:44px/);
  assert.match(KIT_CSS, /min-inline-size:0/);
  assert.match(KIT_CSS, /html\[data-theme=dark\] \.pill\.mk-own-pill/);
});
