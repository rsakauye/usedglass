// Precision checks for the /vintage/ classifier using real dealer titles. Run: node --test tests/
import test from 'node:test';
import assert from 'node:assert/strict';
import { classify } from '../site/src/lib/vintage.js';
const C = (title, mount = null, category = 'camera') => classify({ title, mount, category, price_cad: 100 });

test('film bodies on shared mounts', () => {
  assert.equal(C('NIKON FE2 W/50F1.8E', 'Nikon F'), 'film35');
  assert.equal(C('Pentax K1000 Used Film Camera', 'Pentax K'), 'film35');
  assert.equal(C('Canon EOS Rebel 2000 (boitier seul)', 'Canon EF'), 'film35');
  assert.equal(C('LEICA M3 DS W/50F2 SUMMICRON', 'Leica M'), 'film35');
  assert.equal(C('Canon AE-1 + 50mm f1.8 (BGN) used', 'Canon FD'), 'film35');
});
test('digital bodies are excluded', () => {
  assert.equal(C('Canon EOS 5D Mark II', 'Canon EF'), null);
  assert.equal(C('[Very Good] - Canon EOS 5D Mark IV', 'Canon EF'), null);
  assert.equal(C('LEICA CL W/18-56 silver', 'L-Mount'), null);
  assert.equal(C('Canon PowerShot SX70 HS Digital Bridge Camera', 'Fixed Lens'), null);
  assert.equal(C('PENTAX 645Z W/55F2.8 SDM AW', 'Pentax K'), null);
  assert.equal(C('Nikon D3200', 'Nikon F'), null);
  assert.equal(C('Ricoh GR IV Monochrome Camera OPEN BOX', 'Fixed Lens'), null);
  assert.equal(C('SIGMA FP W/45F2.8+LVF-11+GRIP'), null);
});
test('medium format, compacts, instant', () => {
  assert.equal(C('Yashica Mat 124G TLR Film Camera'), 'filmmf');
  assert.equal(C('MAMIYA C330S W/80F2.8 BLUEDOT', null, 'lens'), 'filmmf');
  assert.equal(C('Hasselblad HASSELBLA 503CW /80CFi/A12/WL', 'Hasselblad V'), 'filmmf');
  assert.equal(C('Canon Prima Zoom 85N Used Film Camera'), 'compact');
  assert.equal(C('POLAROID SX70 ORIGINAL SILVER', 'Fixed Lens'), 'instant');
  assert.equal(C('NONS SL600 W/35F2.4', 'Fixed Lens'), 'instant');
});
test('accessories are excluded', () => {
  assert.equal(C('Olympus Accessory Shoe 1 (OM-1, OM-2) - Used', 'Olympus OM'), null);
  assert.equal(C('Pentax 67 Quick Focus Handle (Type B)', 'Pentax 67'), null);
  assert.equal(C('Crystal Hasselblad 500C/M Display model', 'Hasselblad V'), null);
  assert.equal(C('Canon Lens Mount Converter A (L39 To FL/FD)(EX) Used', 'Canon FD', 'lens'), null);
});
test('vintage manual lenses vs modern/AF', () => {
  assert.equal(C('Asahi SMC Takumar 55mm f2', 'M42', 'lens'), 'lens');
  assert.equal(C('NIKON 105F2.5 NIKKOR-P', 'Nikon F', 'lens'), 'lens');
  assert.equal(C('Nikon AI-S 50mm F1.4 Used Lens', 'Nikon F', 'lens'), 'lens');
  assert.equal(C('Used Nikon AF-S 14-24mm f/2.8 G ED', 'Nikon F', 'lens'), null);
  assert.equal(C('Pentax-M 50mm F2 (BGN) Used Lens', 'Pentax K', 'lens'), 'lens');
  assert.equal(C('PENTAX 16-50mm f/2.8 DA STAR', 'Pentax K', 'lens'), null);
  assert.equal(C('Pentax-F 35-105mm F4-5.6 SMC Used Lens', 'Pentax K', 'lens'), null);
  assert.equal(C('Typoch Simera 28mm F/1.4 Leica M', 'Leica M', 'lens'), null);
  assert.equal(C('LEICA 90F2 SUMMICRON-M', 'Leica M', 'lens'), 'lens');
  assert.equal(C('Carl Zeiss Jena Biotar 5.8cm f2 for Exakta', null, 'lens'), 'lens');
  assert.equal(C('Minolta Lens Shade for CLE 28mm f2.8', 'Minolta MD', 'lens'), null);
});
