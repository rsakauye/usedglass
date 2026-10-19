// Shared rendering for /my/ (editable) and /kit/ (read-only shared view).
import { esc, money, scoreLabel, scoreCls, checkList, kitTotals, CAT_LABEL, isBodyCat } from './mykit-core.js';

export function mountOf(cat) { return (it) => it.m || (it.k && cat?.byKey.get(it.k)?.mount) || null; }
export function nameOf(cat, it) { return (it.k && cat?.byKey.get(it.k)?.name) || it.n; }

const STATUS = { ok: ['good', 'Fits'], adapter: ['warn', 'Needs an adapter'], nofit: ['bad', "Won't fit"] };

export function itemsHtml(items, cat, { base = '/', editable = false, lists = [], currentId = '' } = {}) {
  if (!items.length) return `<p class="muted mk-empty">${editable ? 'Nothing here yet. Tap the ♡ on any listing, deal or model page, or add gear below.' : 'This kit is empty.'}</p>`;
  const compat = checkList(items, mountOf(cat));
  return items.map((it, idx) => {
    const m = it.k ? cat?.byKey.get(it.k) : null;
    const name = nameOf(cat, it), mount = mountOf(cat)(it);
    const hit = m && it.t && m.used != null && m.used <= it.t;
    const c = compat.get(it);
    const st = c && c.status !== 'ok' ? STATUS[c.status] : null;
    const moveOpts = lists.filter((l) => l.id !== currentId).map((l) => `<option value="${esc(l.id)}">${esc(l.name)}</option>`).join('');
    return `<div class="mk-item${hit ? ' mk-hit' : ''}" data-idx="${idx}">
      <div class="mk-main">
        <div class="mk-name">${m ? `<a href="${base}model/${esc(m.key)}/">${esc(name)}</a>` : esc(name)}</div>
        <div class="mk-tags"><span class="pill">${esc(CAT_LABEL[it.c] || 'Other')}</span>${mount ? `<span class="pill">${esc(mount)}</span>` : ''}${st ? `<span class="pill mk-${st[0]}" title="${esc(c.note)}">${st[1]}</span>` : ''}${c && c.status === 'ok' ? '<span class="pill good">Fits your body</span>' : ''}${hit ? '<span class="pill good">At or below your target</span>' : ''}</div>
        ${st ? `<div class="mk-note mk-${st[0]}">${esc(c.note.charAt(0).toUpperCase() + c.note.slice(1))}${c.body ? ` (with ${esc(nameOf(cat, c.body))})` : ''}.</div>` : ''}
      </div>
      <div class="mk-price">
        ${m && m.used != null ? `<div class="mk-used"><b>${money(m.used)}</b> <span class="muted">used at ${m.usedUrl ? `<a href="${esc(m.usedUrl)}" rel="nofollow noopener" target="_blank">${esc(m.usedDealer)}</a>` : esc(m.usedDealer)}</span></div>` : `<div class="muted">${m ? 'No used listing today' : 'Not tracked yet'}</div>`}
        ${m && m.newPrice != null ? `<div class="muted">New ${money(m.newPrice)}${m.newDealer ? ` at ${m.newUrl ? `<a href="${esc(m.newUrl)}" rel="nofollow noopener" target="_blank">${esc(m.newDealer)}</a>` : esc(m.newDealer)}` : ''}</div>` : ''}
        ${m && m.score != null ? `<a class="pill score ${scoreCls(m.score)}" href="${base}about/deal-score/" title="Best Deal Score among today's listings">Deal Score ${m.score} · ${scoreLabel(m.score)}</a>` : ''}
      </div>
      ${editable ? `<div class="mk-edit">
        <label>Target $ <input type="number" min="0" step="1" inputmode="decimal" class="mk-target" value="${it.t || ''}" placeholder="optional" /></label>
        <select class="mk-cat" aria-label="Category">${Object.entries(CAT_LABEL).map(([k, v]) => `<option value="${k}"${k === it.c ? ' selected' : ''}>${esc(v)}</option>`).join('')}</select>
        ${moveOpts ? `<select class="mk-move" aria-label="Move or copy to another list"><option value="">Move to…</option>${moveOpts}</select>` : ''}
        <button type="button" class="mk-rm secondary" aria-label="Remove ${esc(name)}">Remove</button>
      </div>` : ''}
    </div>`;
  }).join('');
}

export function totalsHtml(items, cat) {
  const t = kitTotals(items, cat);
  const parts = [`<div><b>${t.items}</b><span class="muted">item${t.items === 1 ? '' : 's'}</span></div>`];
  if (t.usedN) parts.push(`<div><b>${money(t.used)}</b><span class="muted">cheapest used (${t.usedN} of ${t.items})</span></div>`);
  if (t.newN) parts.push(`<div><b>${money(t.new)}</b><span class="muted">new (${t.newN} of ${t.items})</span></div>`);
  if (t.bestN) parts.push(`<div><b>${money(t.best)}</b><span class="muted">best of used/new (${t.bestN} of ${t.items})</span></div>`);
  return `<div class="stats mk-totals">${parts.join('')}</div>`;
}

export function compatHtml(items, cat) {
  const compat = checkList(items, mountOf(cat));
  const bad = [...compat].filter(([, c]) => c.status !== 'ok');
  if (!items.some((i) => isBodyCat(i.c))) return items.some((i) => i.c === 'lens') ? '<p class="muted mk-compat">Add a camera body to this list to check lens mounts.</p>' : '';
  if (!bad.length) return compat.size ? '<p class="mk-compat mk-good">✓ Every lens in this list fits a body in this list.</p>' : '';
  return `<div class="mk-compat card"><b>Mount check</b> <span class="muted">(simplified rules: same mount fits; SLR lenses usually adapt to mirrorless bodies; mirrorless lenses don't fit SLRs or other mirrorless mounts)</span><ul>${bad.map(([it, c]) => `<li class="mk-${STATUS[c.status][0]}"><b>${esc(nameOf(cat, it))}</b>: ${esc(c.note)}.</li>`).join('')}</ul></div>`;
}

export const KIT_CSS = `
.mk-item { display:grid; grid-template-columns: minmax(0,1fr) auto; gap:.3rem 1rem; background:var(--card); border:1px solid var(--line); border-radius:10px; padding:.7rem .8rem; margin-bottom:.55rem; }
.mk-item.mk-hit { border-color:#7cc59a; box-shadow: inset 4px 0 0 var(--good); }
.mk-name { font-weight:600; overflow-wrap:anywhere; }
.mk-tags { margin-top:.2rem; display:flex; flex-wrap:wrap; gap:.25rem; }
.mk-price { text-align:right; font-variant-numeric:tabular-nums; }
.mk-used b { font-size:1.15rem; }
.mk-note { font-size:.85rem; margin-top:.25rem; }
.mk-edit { grid-column:1 / -1; display:flex; flex-wrap:wrap; gap:.4rem; align-items:center; border-top:1px dashed var(--line); padding-top:.45rem; font-size:.9rem; }
.mk-edit input.mk-target { width:6.5rem; }
.pill.mk-warn, .mk-note.mk-warn, li.mk-warn { color:#9a3d00; } .pill.mk-warn { background:#fdebd9; }
.pill.mk-bad, .mk-note.mk-bad, li.mk-bad { color:#a8071a; } .pill.mk-bad { background:#fde2e4; }
.mk-good { color:var(--good); }
.mk-compat { margin:.6rem 0; } .mk-compat ul { margin:.4rem 0 0 1.1rem; padding:0; }
button.secondary { background:#fff; color:var(--fg); border-color:#c9ccd3; }
@media (max-width:640px) {
  .mk-item { grid-template-columns: 1fr; }
  .mk-price { text-align:left; }
}
`;
