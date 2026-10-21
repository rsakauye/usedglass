// Shared rendering for /my/ (editable) and /kit/ (read-only shared view).
import { esc, money, scoreLabel, scoreCls, checkList, kitTotals, CAT_LABEL, isBodyCat } from './mykit-core.js';

export function mountOf(cat) { return (it) => it.m || (it.k && cat?.byKey.get(it.k)?.mount) || null; }
export function nameOf(cat, it) { return (it.k && cat?.byKey.get(it.k)?.name) || it.n; }

const STATUS = { ok: ['good', 'Fits'], adapter: ['warn', 'Needs an adapter'], nofit: ['bad', "Won't fit"] };

// show: 'all' | 'owned' | 'wish' (not owned). Hidden items keep their index so edits still hit the right one.
export const SHOW_MATCH = { all: () => true, owned: (it) => it.owned === true, wish: (it) => it.owned !== true };
export function itemsHtml(items, cat, { base = '/', editable = false, lists = [], currentId = '', show = 'all' } = {}) {
  if (!items.length) return `<p class="muted mk-empty">${editable ? 'Nothing here yet. Tap the ♡ on any listing, deal or model page, or add gear below.' : 'This kit is empty.'}</p>`;
  const compat = checkList(items, mountOf(cat));
  const keep = Object.prototype.hasOwnProperty.call(SHOW_MATCH, show) ? SHOW_MATCH[show] : SHOW_MATCH.all;
  if (!items.some(keep)) return `<p class="muted mk-empty">${show === 'owned' ? 'Nothing in this list is marked Owned yet.' : 'Everything in this list is marked Owned.'}</p>`;
  return items.map((it, idx) => {
    if (!keep(it)) return '';
    const m = it.k ? cat?.byKey.get(it.k) : null;
    const name = nameOf(cat, it), mount = mountOf(cat)(it);
    const hit = m && it.t && m.used != null && m.used <= it.t;
    const c = compat.get(it);
    const st = c && c.status !== 'ok' ? STATUS[c.status] : null;
    const moveOpts = lists.filter((l) => l.id !== currentId).map((l) => `<option value="${esc(l.id)}">${esc(l.name)}</option>`).join('');
    return `<div class="mk-item${hit ? ' mk-hit' : ''}" data-idx="${idx}">
      <div class="mk-main">
        <div class="mk-name">${m ? `<a href="${base}model/${esc(m.key)}/">${esc(name)}</a>` : esc(name)}</div>
        <div class="mk-tags">${it.owned === true ? '<span class="pill mk-own-pill">Owned</span>' : ''}<span class="pill">${esc(CAT_LABEL[it.c] || 'Other')}</span>${mount ? `<span class="pill">${esc(mount)}</span>` : ''}${st ? `<span class="pill mk-${st[0]}" title="${esc(c.note)}">${st[1]}</span>` : ''}${c && c.status === 'ok' ? '<span class="pill good">Fits your body</span>' : ''}${hit ? '<span class="pill good">At or below your target</span>' : ''}</div>
        ${st ? `<div class="mk-note mk-${st[0]}">${esc(c.note.charAt(0).toUpperCase() + c.note.slice(1))}${c.body ? ` (with ${esc(nameOf(cat, c.body))})` : ''}.</div>` : ''}
      </div>
      <div class="mk-price">
        ${m && m.used != null ? `<div class="mk-used"><b>${money(m.used)}</b> <span class="muted">used at ${m.usedUrl ? `<a href="${esc(m.usedUrl)}" rel="nofollow noopener" target="_blank">${esc(m.usedDealer)}</a>` : esc(m.usedDealer)}</span></div>` : `<div class="muted">${m ? 'No used listing today' : 'Not tracked yet'}</div>`}
        ${m && m.newPrice != null ? `<div class="muted">New ${money(m.newPrice)}${m.newDealer ? ` at ${m.newUrl ? `<a href="${esc(m.newUrl)}" rel="nofollow noopener" target="_blank">${esc(m.newDealer)}</a>` : esc(m.newDealer)}` : ''}</div>` : ''}
        ${m && m.score != null ? `<a class="pill score ${scoreCls(m.score)}" href="${base}about/deal-score/" title="Best Deal Score among today's listings">Deal Score ${m.score} · ${scoreLabel(m.score)}</a>` : ''}
      </div>
      ${editable ? `<div class="mk-edit">
        <label class="mk-own"><input type="checkbox" class="mk-owned" aria-label="Owned: ${esc(name)}"${it.owned === true ? ' checked' : ''} /> Owned</label>
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
  const owned = items.filter((i) => i.owned === true).length;
  if (owned) {
    const wish = t.items - owned;
    parts.push(`<div><b>${owned}</b><span class="muted">owned${wish ? ` · ${wish} on the wishlist` : ''}</span></div>`);
  }
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
.mk-item { display:grid; grid-template-columns: minmax(0,1fr) auto; gap:.3rem 1rem; background:var(--card); border:1px solid var(--line); border-radius:10px; padding:.7rem .8rem; margin-bottom:.55rem; min-width:0; }
.mk-item.mk-hit { border-color:#7cc59a; box-shadow: inset 4px 0 0 var(--good); }
.mk-name { font-weight:600; overflow-wrap:anywhere; }
.mk-tags { margin-top:.2rem; display:flex; flex-wrap:wrap; gap:.25rem; }
.mk-price { text-align:right; font-variant-numeric:tabular-nums; }
.mk-used b { font-size:1.15rem; }
.mk-note { font-size:.85rem; margin-top:.25rem; }
.mk-edit { grid-column:1 / -1; display:flex; flex-wrap:wrap; gap:.4rem; align-items:center; border-top:1px dashed var(--line); padding-top:.45rem; font-size:.9rem; min-width:0; }
.mk-edit input.mk-target { width:6.5rem; }
.pill.mk-warn, .mk-note.mk-warn, li.mk-warn { color:#9a3d00; } .pill.mk-warn { background:#fdebd9; }
.pill.mk-bad, .mk-note.mk-bad, li.mk-bad { color:#a8071a; } .pill.mk-bad { background:#fde2e4; }
.mk-good { color:var(--good); }
.pill.mk-own-pill { background:#e3f6ea; color:var(--good); font-weight:600; }
html[data-theme=dark] .pill.mk-own-pill { background:#17291d; color:var(--good); border-color:#2a4a33; }
.mk-own { display:inline-flex; align-items:center; gap:.35rem; cursor:pointer; }
.mk-own input, .mk-show input { width:1.15rem; height:1.15rem; margin:0; padding:0; flex:none; accent-color:var(--good); border:0; background:transparent; }
html[data-theme=dark] .mk-own input, html[data-theme=dark] .mk-show input,
html[data-a11y-space=on] .mk-own input, html[data-a11y-space=on] .mk-show input { width:1.15rem; height:1.15rem; min-height:0; margin:0; padding:0; border:0; background:transparent; box-shadow:none; }
html[data-a11y-space=on] .mk-own, html[data-a11y-space=on] .mk-show label { min-height:48px; }
.mk-show { display:flex; flex-wrap:wrap; gap:.3rem .8rem; align-items:center; border:0; padding:0; margin:.2rem 0 .6rem; min-inline-size:0; width:100%; max-width:100%; }
.mk-show legend { float:left; width:auto; font-weight:600; padding:0; margin-right:.2rem; }
.mk-show label { display:inline-flex; align-items:center; gap:.3rem; cursor:pointer; }
.mk-compat { margin:.6rem 0; } .mk-compat ul { margin:.4rem 0 0 1.1rem; padding:0; }
button.secondary { background:#fff; color:var(--fg); border-color:#c9ccd3; }
@media (max-width:640px) {
  .mk-item { grid-template-columns: 1fr; }
  .mk-price { text-align:left; }
  .mk-own, .mk-show label { min-height:44px; min-width:44px; padding:0 .3rem; flex-shrink:0; }
  .mk-edit select, .mk-edit input.mk-target { max-width:100%; }
}
`;
