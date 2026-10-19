// Canvas "My kit" card: drawn entirely with canvas primitives (logo included as Path2D), no external images,
// so the canvas never gets tainted and toDataURL/toBlob always work.
import { groupByCat, CAT_PLURAL } from './mykit-core.js';

export const SIZES = {
  sig: { w: 600, h: 150, scale: 2, label: 'Email signature (600×150)' },
  forum: { w: 1200, h: 630, scale: 1, label: 'Forum card (1200×630)' },
};
const C = { navy: '#14213d', blue: '#2a9df4', orange: '#f4a261', paper: '#f7f2e8', ink: '#14213d', soft: '#6b6455', rule: '#e2d9c6' };
const SANS = 'system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
const MONO = 'ui-monospace, "SF Mono", Menlo, Consolas, "Liberation Mono", "Courier New", monospace';

// Same geometry as the header logo (64×64 viewBox), dark variant for the paper background.
export function drawLogo(ctx, x, y, size) {
  ctx.save(); ctx.translate(x, y); ctx.scale(size / 64, size / 64);
  const rr = (rx, ry, w, h, r, fill) => { ctx.beginPath(); ctx.roundRect(rx, ry, w, h, r); ctx.fillStyle = fill; ctx.fill(); };
  const circ = (cx, cy, r, fill) => { ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fillStyle = fill; ctx.fill(); };
  rr(35, 12, 9, 5, 2, C.orange);
  rr(6, 16, 44, 32, 6, C.navy);
  ctx.fillStyle = C.navy; ctx.strokeStyle = C.navy; ctx.lineWidth = 2; ctx.lineJoin = 'round';
  const hump = new Path2D('M11 17 L14 10.5 H23 L26 17 Z'); ctx.fill(hump); ctx.stroke(hump);
  rr(38, 21, 7, 4, 1.5, C.blue);
  ctx.lineCap = 'round';
  ctx.strokeStyle = C.navy; ctx.lineWidth = 7.5; ctx.beginPath(); ctx.moveTo(39.5, 40.5); ctx.lineTo(56, 57); ctx.stroke();
  ctx.strokeStyle = C.orange; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(41, 42); ctx.lineTo(55.5, 56.5); ctx.stroke();
  circ(28, 32, 13, C.navy); circ(28, 32, 11, '#fff'); circ(28, 32, 9.2, C.navy); circ(28, 32, 7.2, C.blue);
  ctx.strokeStyle = '#fff'; ctx.lineWidth = 2.2; ctx.beginPath(); ctx.arc(29, 31.5, 5.5, Math.PI * 1.08, Math.PI * 1.55); ctx.stroke();
  ctx.restore();
}
function wordmark(ctx, x, y, px, align = 'left') {
  ctx.font = `800 ${px}px ${SANS}`; ctx.textBaseline = 'alphabetic';
  const parts = [['Used', C.navy], ['Glass', C.blue], ['.ca', C.navy]];
  const w = parts.reduce((s, [t]) => s + ctx.measureText(t).width, 0);
  let cx = align === 'right' ? x - w : x;
  for (const [t, col] of parts) { ctx.fillStyle = col; ctx.textAlign = 'left'; ctx.fillText(t, cx, y); cx += ctx.measureText(t).width; }
  return w;
}
function fit(ctx, text, maxW) {
  if (ctx.measureText(text).width <= maxW) return text;
  let t = text;
  while (t.length > 1 && ctx.measureText(t + '…').width > maxW) t = t.slice(0, -1);
  return t.trimEnd() + '…';
}
function grain(ctx, w, h) {
  // Deterministic paper speckle (seeded) for an analog feel without any image assets.
  let s = 7; const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  ctx.save(); ctx.globalAlpha = 0.05; ctx.fillStyle = '#5b4a2a';
  for (let i = 0; i < (w * h) / 900; i++) ctx.fillRect(rnd() * w, rnd() * h, 1.2, 1.2);
  ctx.restore();
}
function sprockets(ctx, w, y, hole = 10) {
  ctx.fillStyle = C.navy; ctx.fillRect(0, y, w, hole * 2.4);
  ctx.fillStyle = C.paper;
  for (let x = hole; x < w; x += hole * 2.6) { ctx.beginPath(); ctx.roundRect(x, y + hole * 0.6, hole * 1.3, hole * 1.2, 2); ctx.fill(); }
}

export function renderCard(canvas, { items, listName = '', handle = '', size = 'forum', url = 'usedglass.ca' }) {
  const S = SIZES[size] || SIZES.forum;
  canvas.width = S.w * S.scale; canvas.height = S.h * S.scale;
  const ctx = canvas.getContext('2d');
  ctx.setTransform(S.scale, 0, 0, S.scale, 0, 0);
  const { w, h } = S;
  ctx.fillStyle = C.paper; ctx.fillRect(0, 0, w, h); grain(ctx, w, h);
  const groups = groupByCat(items);
  const title = handle ? `${handle}'s kit` : (listName || 'My kit');

  if (size === 'sig') {
    ctx.fillStyle = C.orange; ctx.fillRect(0, 0, 6, h);
    drawLogo(ctx, 18, 14, 50);
    ctx.textAlign = 'left'; ctx.fillStyle = C.ink; ctx.font = `700 19px ${SANS}`;
    ctx.fillText(fit(ctx, title, 330), 82, 36);
    ctx.font = `13px ${MONO}`;
    let y = 60; const lines = groups.length ? groups : [['other', [{ n: 'Add gear on usedglass.ca/my/' }]]];
    const maxLines = 4;
    lines.slice(0, maxLines).forEach(([c, its], i) => {
      const more = i === maxLines - 1 && lines.length > maxLines ? ` (+${lines.length - maxLines} more groups)` : '';
      ctx.fillStyle = C.soft; ctx.font = `700 11px ${SANS}`;
      const lab = (CAT_PLURAL[c] || 'Other').toUpperCase();
      ctx.fillText(lab, 82, y);
      ctx.fillStyle = C.ink; ctx.font = `13px ${MONO}`;
      ctx.fillText(fit(ctx, its.map((x) => x.n).join(' · ') + more, w - 82 - 92 - 20), 82 + 92, y);
      y += 21;
    });
    wordmark(ctx, w - 14, 30, 13, 'right');
    return canvas;
  }

  // Forum card 1200×630
  sprockets(ctx, w, 0, 11); sprockets(ctx, w, h - 26.4, 11);
  const pad = 64;
  drawLogo(ctx, pad, 58, 92);
  ctx.textAlign = 'left'; ctx.fillStyle = C.ink; ctx.font = `800 46px ${SANS}`;
  ctx.fillText(fit(ctx, title, w - pad * 2 - 120 - 260), pad + 116, 104);
  ctx.fillStyle = C.soft; ctx.font = `20px ${SANS}`;
  const sub = [handle && listName ? listName : '', `${items.length} item${items.length === 1 ? '' : 's'}`].filter(Boolean).join(' · ');
  ctx.fillText(fit(ctx, sub, 560), pad + 118, 136);
  wordmark(ctx, w - pad, 100, 30, 'right');
  ctx.strokeStyle = C.navy; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(pad, 174); ctx.lineTo(w - pad, 174); ctx.stroke();

  // Two columns of category groups, each item on its own line; overflow becomes "+N more".
  const colW = (w - pad * 2 - 48) / 2, top = 214, bottom = h - 70, lh = 30;
  let col = 0, y = top;
  const empty = !groups.length;
  const src = empty ? [['other', [{ n: 'Build your kit at usedglass.ca/my/' }]]] : groups;
  outer: for (const [c, its] of src) {
    const need = 30 + Math.min(its.length, 2) * lh;
    if (y + need > bottom) { if (col === 1) break; col = 1; y = top; }
    const x = pad + col * (colW + 48);
    ctx.fillStyle = C.orange; ctx.fillRect(x, y - 15, 5, 18);
    ctx.fillStyle = C.navy; ctx.font = `800 17px ${SANS}`; ctx.fillText((CAT_PLURAL[c] || 'Other').toUpperCase(), x + 14, y);
    y += 32;
    for (let i = 0; i < its.length; i++) {
      if (y > bottom - lh * 0.4 || (y + lh > bottom && i < its.length - 1)) {
        if (col === 0) { col = 1; y = top; }
        else { ctx.fillStyle = C.soft; ctx.font = `20px ${MONO}`; ctx.fillText(`+${its.length - i} more`, x + 14, y); break outer; }
      }
      const cx = pad + col * (colW + 48);
      ctx.fillStyle = C.ink; ctx.font = `21px ${MONO}`;
      ctx.fillText(fit(ctx, '› ' + its[i].n, colW - 14), cx + 14, y);
      y += lh;
    }
    y += 14;
  }
  ctx.fillStyle = C.soft; ctx.font = `600 17px ${SANS}`; ctx.textAlign = 'right';
  ctx.fillText(`${url} · used camera prices from Canadian dealers`, w - pad, h - 42);
  return canvas;
}
