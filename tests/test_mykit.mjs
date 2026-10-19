// Unit tests for the client-side kit builder (site/src/lib/mykit-core.js). Run: node --test tests/
import test from 'node:test';
import assert from 'node:assert/strict';
import * as K from '../site/src/lib/mykit-core.js';

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
