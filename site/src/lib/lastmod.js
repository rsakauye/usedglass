// Real "last changed" dates for the sitemap (and IndexNow), instead of stamping every URL with the build date.
//  - Model pages: from data/state.json, the latest day one of the model's listings appeared, changed price or
//    sold/was removed (the day after it was last seen).
//  - Other pages: the last git commit that touched the page's source or the data it shows (needs full history;
//    CI checks out with fetch-depth 0). On a shallow or missing git history we return null, and the sitemap
//    omits <lastmod> rather than guessing.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const SITE = process.cwd();
const ROOT = path.resolve(SITE, '..');
const DATA_DIR = process.env.DATA_DIR || path.join(ROOT, 'data');
const ymd = (ms) => new Date(ms).toLocaleDateString('en-CA', { timeZone: 'America/Edmonton' });
const addDay = (d) => new Date(Date.parse(d + 'T12:00:00Z') + 864e5).toISOString().slice(0, 10);

function readJson(name, fallback) {
  try { return JSON.parse(fs.readFileSync(path.join(DATA_DIR, name), 'utf8')); } catch { return fallback; }
}

let gitOk = null;
function git(args) { return execFileSync('git', args, { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim(); }
function gitUsable() {
  if (gitOk === null) {
    try { gitOk = git(['rev-parse', '--is-shallow-repository']) === 'false'; } catch { gitOk = false; }
  }
  return gitOk;
}
// Paths are relative to the repo root. Returns YYYY-MM-DD (America/Edmonton) or null.
export function gitDate(paths) {
  if (!gitUsable()) return null;
  try {
    const t = git(['log', '-1', '--format=%ct', '--', ...paths]);
    return t ? ymd(Number(t) * 1000) : null;
  } catch { return null; }
}

// model key -> YYYY-MM-DD of its last listing-set or price change.
let modelDates = null;
export function modelLastmod(key) {
  if (!modelDates) {
    modelDates = {};
    const state = readJson('state.json', {});
    const runDate = readJson('meta.json', {}).date || null;
    for (const v of Object.values(state)) {
      if (!v || !v.mk) continue;
      const ds = [v.fs, ...(v.p || []).slice(-1).map((x) => x[0])];
      if (runDate && v.ls && v.ls < runDate) ds.push(addDay(v.ls) > runDate ? runDate : addDay(v.ls)); // removed/sold
      const d = ds.filter(Boolean).sort().pop();
      if (d && (!modelDates[v.mk] || d > modelDates[v.mk])) modelDates[v.mk] = d;
    }
  }
  return modelDates[key] || null;
}
export const maxDate = (ds) => ds.filter(Boolean).sort().pop() || null;
