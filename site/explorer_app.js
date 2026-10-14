document.documentElement.setAttribute('data-theme', 'dark');
// Ten of the page's bullets are headings the article uses to group the problems beneath them, not
// problems: they carry is_grouping and were never researched. They are dropped here, so every
// count on the site is against the 457 problems.
const PROBLEMS = ALL_DATA.filter(p => !p.is_grouping);
// ALL_DATA is the full snapshot; DATA is the corpus every tab reads, narrowed by the site-wide
// scope control in the tab bar. Reassigned by applyScope(), so all counts and denominators follow.
let DATA = PROBLEMS;
const SCOPES = [
  ['all', 'All problems', () => true],
  ['now', 'Problems with dedicated article today', p => p.own_page_now],
  ['2024', 'Problems with dedicated article Jan 2024', p => p.own_page_2024],
];
const TYPE_ORDER = ['conjecture', 'question', 'problem', 'other'];
const TYPE_LABEL = { conjecture: 'Conjecture', question: 'Open question', problem: 'Named problem', other: 'Other' };
const TYPE_VAR = { conjecture: 'var(--c-conj)', question: 'var(--c-q)', problem: 'var(--c-prob)', other: 'var(--c-other)' };
const kind = p => TYPE_ORDER.includes(p.type) ? p.type : 'other';
const FIELD_ORDER = [...new Set(DATA.map(p => p.field))];
const LISTS = [
  ['millennium', 'Millennium Prize', p => p.millennium_prize],
  ['hilbert', "Hilbert's problems", p => p.hilbert_problem != null],
  ['landau', "Landau's problems", p => p.landau_problem],
  ['smale', "Smale's problems", p => p.smale_problem != null],
  ['named', 'Named after someone', p => p.named_after.length > 0],
];
const STATUS_ORDER = ['resolved', 'claimed', 'partial', 'progress', 'open_stale', 'open'];
const STATUS_LABEL = { resolved: 'Resolved', claimed: 'Resolution claimed', partial: 'Partially resolved', progress: 'Notable progress', open_stale: 'Settled before snapshot', open: 'Still open' };
const AI_ORDER = ['generated', 'assisted', 'incident', 'none'];
const AI_STACK = ['none', 'incident', 'assisted', 'generated'];
const AI_LABEL = { generated: 'AI-generated', assisted: 'AI-assisted', incident: 'AI claim retracted', none: 'No AI involvement' };
const aiTouched = p => p.ai_involvement && p.ai_involvement !== 'none';

/* ---- Per-chart rules. Each chart answers its own question from a problem's events (p.events:
   every event that survives JUDGE.md §3 step 1, with the judge's answers), instead of from one
   status per problem. The rules live here, beside the charts that use them. */
const sinceSnapshot = p => (p.events || []).filter(e => e.after_snapshot === true);
// Dates compare as strings, so '2026-07' sorts before '2026-07-03'; a missing date sorts last.
const byDate = (a, b) => String(a.date || '9999').localeCompare(String(b.date || '9999'));
// Resolutions: the first event after the snapshot that settles the whole problem, either way. It
// sets the problem's resolution date and its credit.
const firstResolution = p => sinceSnapshot(p).filter(e => e.tier === 'resolved' || e.tier === 'claimed').sort(byDate)[0] || null;
// "Accepted" when any whole-problem event has been checked (digested or directly checkable).
const resolutionAccepted = p => sinceSnapshot(p).some(e => e.tier === 'resolved');
// Progress: every surviving event after the snapshot counts. A problem is AI-only when every one of
// them was AI-generated, human when none involved AI, and otherwise AI-assisted or both: some AI
// help on an event, or AI and human events side by side.
// 'both' (AI and human events side by side) is kept apart from 'assisted' (every event involved
// AI, at least one only as help) so a chart can draw it distinctly; both count as involving AI.
const PROGRESS_LABEL = { generated: 'entirely by AI', assisted: 'AI-assisted', both: 'by AI and humans both', none: 'without AI' };
const progressCredit = p => {
  const ev = sinceSnapshot(p);
  if (!ev.length) return null;
  const ai = ev.filter(e => e.ai && e.ai !== 'none');
  if (!ai.length) return 'none';
  if (ai.length < ev.length) return 'both';
  return ai.every(e => e.ai === 'generated') ? 'generated' : 'assisted';
};
// A hatched swatch: the band's colour striped with the panel's, so a mixed band reads as the same
// family as its solid neighbour but visibly not the same thing. Used in legends and tooltips.
const hatchCSS = c => `repeating-linear-gradient(45deg,${c} 0 2.5px,var(--panel) 2.5px 4px)`;
const state = { q: '', fields: new Set(), y0: null, y1: null, noyear: true, scope: 'all', lists: new Set(), status: new Set(), ai: new Set(), models: new Set(), tab: 'attribution', aMode: 'count', cMode: 'count', view: 'cards', sort: 'page', open: new Set(), sortCol: 'id', sortAsc: true };
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const fmtYear = y => y == null ? '—' : y < 0 ? `${-y} BC` : String(y);
const wpUrl = t => 'https://en.wikipedia.org/wiki/' + encodeURIComponent(t.replace(/ /g, '_'));
const MODEL_ORDER = (() => { const c = {}; DATA.forEach(p => p.ai_models.forEach(m => c[m] = (c[m] || 0) + 1)); return Object.keys(c).sort((x, y) => c[y] - c[x] || x.localeCompare(y)); })();
// The lab is researched, one entry per system in MODEL_RELEASES (pipeline/model_aliases.py), so it
// is read from there rather than guessed. An earlier version pattern-matched the model's name and
// fell back to 'other', which put every system outside OpenAI/Anthropic/DeepMind — xAI, Together
// AI, Axiom Math, the university harnesses — into one unlabelled bucket.
// Every system in MODEL_RELEASES, not only those a problem headlines, since the systems chart now
// counts credits on any event.
const LAB_OF = (() => { const m = {}; [...MODEL_ORDER, ...Object.keys(MODEL_RELEASES)].forEach(mm => m[mm] = (MODEL_RELEASES[mm] || {}).lab || 'unattributed'); return m; })();
// The three frontier labs get their own heading; everything else — one or two systems each, from
// universities, smaller labs and academic groups — is grouped under Other rather than producing a
// heading per system. The real lab is still on the record and in MODEL_RELEASES.
const BIG3 = ['OpenAI', 'Anthropic', 'Google DeepMind'];
const GROUP_OF = m => BIG3.includes(LAB_OF[m]) ? LAB_OF[m] : 'Other';
const LAB_ORDER = [...BIG3, 'Other'];
const modelCount = m => DATA.filter(p => p.ai_models.includes(m)).length;
const searchText = p => [p.name, p.ai_models.join(' '), p.ai_labs.join(' '), p.statement, p.field, p.subfield, p.named_after.join(' '), p.wikilinks.join(' '), p.year_note, p.resolved_by, p.ai_system, p.status_note, STATUS_LABEL[p.status], AI_LABEL[p.ai_involvement]].join(' ').toLowerCase();
DATA.forEach(p => { p._s = searchText(p); });

function filtered() {
  const q = state.q.trim().toLowerCase().split(/\s+/).filter(Boolean);
  return DATA.filter(p => {
    if (state.fields.size && !state.fields.has(p.field)) return false;
    if (p.year_introduced == null) { if (!state.noyear) return false; }
    else { if (state.y0 != null && p.year_introduced < state.y0) return false; if (state.y1 != null && p.year_introduced > state.y1) return false; }
    for (const [id, , fn] of LISTS) if (state.lists.has(id) && !fn(p)) return false;
    if (state.status.size && !state.status.has(p.status)) return false;
    if (state.ai.size && !state.ai.has(p.ai_involvement)) return false;
    if (state.models.size && !p.ai_models.some(m => state.models.has(m))) return false;
    return q.every(w => p._s.includes(w));
  });
}
function sorted(rows) {
  const r = rows.slice();
  if (state.sort === 'status') r.sort((a, b) => STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status) || (b.year_resolved || 0) - (a.year_resolved || 0));
  else if (state.sort === 'year') r.sort((a, b) => (a.year_introduced ?? 9e9) - (b.year_introduced ?? 9e9));
  else if (state.sort === 'name') r.sort((a, b) => a.name.localeCompare(b.name));
  else if (state.sort === 'links') r.sort((a, b) => b.wikilinks.length - a.wikilinks.length);
  return r;
}

function renderRail() {
  const counts = {}; FIELD_ORDER.forEach(f => counts[f] = 0); DATA.forEach(p => counts[p.field]++);
  const max = Math.max(1, ...Object.values(counts));
  $('#fields').innerHTML = FIELD_ORDER.map(f => `<button class="fieldrow${state.fields.has(f) ? ' on' : ''}" data-f="${esc(f)}"><span class="bar" style="width:${Math.max(4, 60 * counts[f] / max)}px"></span><span>${esc(f)}</span><span class="n mono">${counts[f]}</span></button>`).join('');
  $('#fields').querySelectorAll('button').forEach(b => b.onclick = () => { const f = b.dataset.f; state.fields.has(f) ? state.fields.delete(f) : state.fields.add(f); update(); });
  $('#lists').innerHTML = LISTS.map(([id, lab, fn]) => `<button class="chip${state.lists.has(id) ? ' on' : ''}" data-l="${id}">${lab} <span class="mono" style="color:var(--ink-3)">${DATA.filter(fn).length}</span></button>`).join('');
  $('#lists').querySelectorAll('button').forEach(b => b.onclick = () => { const l = b.dataset.l; state.lists.has(l) ? state.lists.delete(l) : state.lists.add(l); update(); });
  const sc = {}; DATA.forEach(p => sc[p.status] = (sc[p.status] || 0) + 1);
  $('#status').innerHTML = STATUS_ORDER.map(s => `<button class="chip${state.status.has(s) ? ' on' : ''}" data-s="${s}">${STATUS_LABEL[s]} <span class="mono" style="color:var(--ink-3)">${sc[s] || 0}</span></button>`).join('');
  $('#status').querySelectorAll('button').forEach(b => b.onclick = () => { const s = b.dataset.s; state.status.has(s) ? state.status.delete(s) : state.status.add(s); update(); });
  $('#models').innerHTML = MODEL_ORDER.map(m => `<button class="chip${state.models.has(m) ? ' on' : ''}" data-m="${esc(m)}">${esc(m)} <span class="mono" style="color:var(--ink-3)">${modelCount(m)}</span></button>`).join('');
  $('#models').querySelectorAll('button').forEach(b => b.onclick = () => { const m = b.dataset.m; state.models.has(m) ? state.models.delete(m) : state.models.add(m); update(); });
  const ac = {}; DATA.forEach(p => ac[p.ai_involvement] = (ac[p.ai_involvement] || 0) + 1);
  $('#ai').innerHTML = AI_ORDER.map(s => `<button class="chip${state.ai.has(s) ? ' on' : ''}" data-a="${s}">${AI_LABEL[s]} <span class="mono" style="color:var(--ink-3)">${ac[s] || 0}</span></button>`).join('');
  $('#ai').querySelectorAll('button').forEach(b => b.onclick = () => { const s = b.dataset.a; state.ai.has(s) ? state.ai.delete(s) : state.ai.add(s); update(); });
}

const AIC = { generated: 'var(--ai-gen)', assisted: 'var(--ai-asst)', incident: 'var(--ai-retr)', none: 'var(--ai-none)' };
const attr = s => String(s).replace(/"/g, '&quot;');
const names = ps => ps.slice(0, 5).map(p => p.name).join(', ') + (ps.length > 5 ? `, +${ps.length - 5} more` : '');

// one stacked row: segments sized by `scale` (fraction of the track), each with a tooltip
function barRow(label, groups, opts = {}) {
  const total = groups.reduce((s, g) => s + g.n, 0);
  const denom = opts.denom || total || 1;
  // opts.outline draws the row's own denominator as an empty frame the stack sits inside, so a
  // short bar in a large field reads as a small share rather than as a small count.
  const outline = opts.outline ? `<i class="outline" style="width:${100 * opts.outline / denom}%" data-tip="${attr(`<b>${label}</b><br>${total} of ${opts.outline} problems in this field`)}"></i>` : '';
  const segs = groups.filter(g => g.n).map(g => {
    const pct = 100 * g.n / denom;
    const tip = `<b>${label} · ${g.label}</b><br>${g.n} of ${total} (${Math.round(100 * g.n / (total || 1))}%)` + (opts.noNames ? '' : `<br><span style="opacity:.75">${esc(names(g.ps))}</span>`);
    return `<i style="width:${pct}%;background:${g.hatch ? hatchCSS(g.color) : g.color}${g.opacity != null ? `;opacity:${g.opacity}` : ''}" data-tip="${attr(tip)}">${pct >= 11 && g.n > 1 ? `<b>${g.n}</b>` : ''}</i>`;
  }).join('');
  const rowTip = `<b>${label}</b>: ${total}<br>` + groups.filter(g => g.n).map(g => `${g.label}: ${g.n}`).join('<br>');
  return `<div class="brow"${opts.gapAfter ? ' style="margin-bottom:15px"' : ''}><span class="lab" style="width:${opts.labW || 168}px" data-tip="${attr(rowTip)}">${esc(label)}</span><span class="track">${outline}${segs}</span><span class="n" data-tip="${attr(rowTip)}">${opts.nText || total}</span></div>`;
}
const aiGroups = ps => AI_ORDER.map(k => ({ label: AI_LABEL[k], color: AIC[k], n: ps.filter(p => p.ai_involvement === k).length, ps: ps.filter(p => p.ai_involvement === k) }));

const isRes = p => ['resolved', 'claimed'].includes(p.status);
// Who did the work, in three buckets. `incident` is a retracted claim: on a resolution the AI only
// critiqued human work (Hopf: Refine found gaps in Brendle-Hung), so it reads as human; on a
// still-open problem nothing moved at all, so the row is dropped rather than drawn as progress.
const attrOf = p => p.ai_involvement === 'generated' ? 'ai'
  : p.ai_involvement === 'assisted' ? 'with'
    : isRes(p) ? 'human'
      : p.ai_involvement === 'incident' ? null : 'human';
const ATTR = [['human', 'human only', AIC.none], ['with', 'with AI', AIC.assisted], ['ai', 'AI only', AIC.generated]];

// The same three buckets as bars, for charts that split a set by who did the work.
const ATTR_LABEL = { human: 'No AI involvement', with: 'AI-assisted', ai: 'AI-generated' };
const aiGroups3 = ps => ATTR.map(([k, , color]) => ({ label: ATTR_LABEL[k], color, n: ps.filter(p => attrOf(p) === k).length, ps: ps.filter(p => attrOf(p) === k) }));


/* ---- cumulative stacked area, monthly steps ---- */
// The axis runs from January 2024 to the latest dated event in the data (never before September
// 2026), so a release dated after the last chart was drawn is not silently cut off the end.
const LAST_MONTH = PROBLEMS.flatMap(p => (p.events || []).filter(e => e.after_snapshot === true && e.precision !== 'year')
  .map(e => String(e.date || '').slice(0, 7))).filter(s => /^\d{4}-\d{2}$/.test(s)).reduce((a, b) => (b > a ? b : a), '2026-09');
const MONTHS_AXIS = (() => { const out = []; for (let y = 2024, m = 1; ; m++) { if (m > 12) { m = 1; y++; } const s = `${y}-${String(m).padStart(2, '0')}`; out.push(s); if (s >= LAST_MONTH) break; } return out; })();
const monthLabel = s => ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][+s.slice(5) - 1] + ' ' + s.slice(0, 4);

const pctOf = v => (100 * v / DATA.length);
const fmtPct = v => { const p = pctOf(v); return (p === 0 ? '0' : p < 1 ? p.toFixed(1) : p.toFixed(p % 1 ? 1 : 0)) + '%'; };
const fmtVal = v => state.cMode === 'norm' ? Math.round(100 * v) + '%' : state.cMode === 'share' ? fmtPct(v) : String(v);

function cumulativeChart(svgSel, legSel, tipSel, rows, bands, opts = {}) {
  // 'norm' restacks each month to the running total, so the bands read as composition over time
  const norm = state.cMode === 'norm';
  const MS = MONTHS_AXIS, n = MS.length;
  // the extra 16px on the left is the rotated axis title, which names what the height measures
  const W = 560, H = 250, m = { l: (state.cMode === 'count' ? 34 : 42) + 16, r: 12, t: 12, b: 26 };
  // Each chart says which date places a problem (opts.monthOf); by default the one-status month.
  const monthOf = opts.monthOf || (p => p.month_resolved);
  const inWin = rows.filter(p => monthOf(p) && monthOf(p) >= MS[0] && monthOf(p) <= MS[n - 1]);
  const early = rows.length - inWin.length;
  const cum = bands.map(b => { let c = 0; return MS.map(mm => { c += inWin.filter(p => monthOf(p) === mm && b.test(p)).length; return c; }); });
  const totals = cum.map(c => c[n - 1]);
  const grand = totals.reduce((s, v) => s + v, 0) || 1;
  const monthTot = MS.map((_, i) => cum.reduce((s, c) => s + c[i], 0));
  const firstMonth = monthTot.findIndex(v => v > 0);
  const unit = i => norm ? (monthTot[i] ? 1 / monthTot[i] : 0) : 1;
  const yMax = norm ? 1 : (opts.yMax || grand);
  const iw = W - m.l - m.r, ih = H - m.t - m.b, bw = iw / n;
  const y = v => m.t + ih - ih * v / yMax, x = i => m.l + i * bw;
  let ticks = [];
  if (norm) {
    ticks = [0, 0.25, 0.5, 0.75, 1];
  } else if (state.cMode === 'share') {
    const pctMax = pctOf(yMax);
    const pStep = [0.25, 0.5, 1, 2, 5, 10].find(s => pctMax / s <= 6) || 10;
    for (let p0 = 0; p0 <= pctMax + 1e-9; p0 += pStep) ticks.push(p0 / 100 * DATA.length);
  } else {
    // About six gridlines at a round interval; a fixed step of 5 drew forty labels on top of each
    // other on the panel that reaches the whole progressed corpus.
    const mag = Math.pow(10, Math.floor(Math.log10(Math.max(yMax, 1) / 6)));
    // never below 1: this axis counts problems, so half a gridline unit would be meaningless
    const step = Math.max(1, [1, 2, 5, 10].map(f => f * mag).find(s => yMax / s <= 6) || mag * 10);
    for (let v = 0; v <= yMax + 1e-9; v += step) ticks.push(v);
  }
  let g = '';
  for (const v of ticks) g += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" stroke="var(--grid)"/><text x="${m.l - 6}" y="${y(v) + 3.5}" text-anchor="end">${fmtVal(v)}</text>`;
  // One stacked bar per month, gapped, rather than a continuous stepped area: the series is a
  // running total read month by month, and a filled area invited reading it as a smooth curve.
  let areas = '';
  const i0 = norm ? firstMonth : 0;
  const gap = Math.min(3, bw * 0.28), barW = Math.max(1, bw - gap);
  for (let i = i0; i0 >= 0 && i < n; i++) {
    if (!monthTot[i]) continue;
    const bx = x(i) + gap / 2;
    for (let k = 0; k < bands.length; k++) {
      if (!cum[k][i]) continue;
      const top = cum.slice(0, k + 1).reduce((s, c) => s + c[i], 0) * unit(i);
      const bot = cum.slice(0, k).reduce((s, c) => s + c[i], 0) * unit(i);
      const fill = bands[k].hatch ? `url(#${svgSel.slice(1)}-hatch-${k})` : bands[k].color;
      areas += `<rect x="${bx}" y="${y(top)}" width="${barW}" height="${Math.max(0, y(bot) - y(top))}" fill="${fill}" opacity="${bands[k].opacity ?? 0.9}"/>`;
    }
  }
  let hits = '';
  for (let i = 0; i < n; i++) {
    const tot = cum.reduce((s, c) => s + c[i], 0);
    const sw = b => `<span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${b.hatch ? hatchCSS(b.color) : b.color};margin-right:5px"></span>`;
    const pctTo = v => tot ? Math.round(100 * v / tot) + '%' : '—';
    const lines = bands.map((b, k) => `${sw(b)}${b.label}: ${cum[k][i]}${norm ? ` (${pctTo(cum[k][i])})` : state.cMode === 'share' ? ` (${fmtPct(cum[k][i])})` : ''}`).join('<br>');
    const tip = `<b>${monthLabel(MS[i])}</b> · ${tot} to date${norm ? ' — shares of that running total' : state.cMode === 'share' ? ` — ${fmtPct(tot)} of all ${DATA.length}` : ''}<br>${lines}`;
    hits += `<rect x="${x(i)}" y="${m.t}" width="${bw}" height="${ih}" fill="transparent" data-tip="${attr(tip)}"/>`;
  }
  let ax = '';
  // Every tick names its month and year ("Jan 2024"): a bare "Jul" between two years left the
  // reader working out which year it belonged to.
  MS.forEach((mm, i) => { if (mm.slice(5) === '01' || mm.slice(5) === '07') ax += `<text x="${x(i) + bw / 2}" y="${H - 8}" text-anchor="middle">${monthLabel(mm)}</text>`; });
  const yTitle = opts.yLabel
    ? `<text class="axtitle" transform="rotate(-90)" x="${-(m.t + ih / 2)}" y="11" text-anchor="middle">${esc(opts.yLabel)}</text>` : '';
  const svg = $(svgSel); svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.style.width = '100%'; svg.style.height = 'auto';
  // One diagonal-stripe pattern per hatched band, in that band's colour over the panel's.
  const defs = bands.map((b, k) => b.hatch
    ? `<pattern id="${svgSel.slice(1)}-hatch-${k}" patternUnits="userSpaceOnUse" width="4" height="4" patternTransform="rotate(45)"><rect width="4" height="4" fill="${b.color}"/><rect width="1.4" height="4" fill="var(--panel)"/></pattern>` : '').join('');
  svg.innerHTML = `<defs>${defs}</defs>${g}${areas}${hits}<line x1="${m.l}" x2="${W - m.r}" y1="${y(0)}" y2="${y(0)}" stroke="var(--line)"/>${ax}${yTitle}`;
  $(legSel).innerHTML = bands.map((b, k) => totals[k] ? `<span data-tip="${attr(`<b>${b.label}</b><br>${totals[k]} of the ${grand} shown · ${fmtPct(totals[k])} of all ${DATA.length} problems`)}"><i style="background:${b.hatch ? hatchCSS(b.color) : b.color};opacity:${b.opacity ?? 0.9}"></i>${b.label} <span class="mono" style="color:var(--ink-3)">${state.cMode === 'share' ? fmtPct(totals[k]) : totals[k]}</span></span>` : '').join('');
  attachTip(svg, $(tipSel)); attachTip($(legSel), $(tipSel));
  return { grand, early, totals };
}

/* ---- problems credited, by the month a model became available ----
   One bar per dated system on a monthly axis, split by kind of contribution in the same bands and
   order as the per-system bars below; systems available in the same month are dodged side by side.
   Nothing is placed more precisely than a month, and bar width is derived from the month's slot so
   neighbouring months cannot overdraw each other. The system behind a bar is named on hover rather
   than on the axis, and systems with no date at all are named in the note instead of being placed.
   A bar can sit later than results it contains — pre-release and internal runs. */
function releaseChart() {
  // same bands, in the same order, as the per-system bars below ('none' can't occur on a credited model)
  // `incident` is left out: a retracted claim is not a contribution, and stacking it on a model's
  // bar would read as work that system did.
  const kinds = AI_ORDER.filter(k => !['none', 'incident'].includes(k)).map(k => ({ key: k, label: AI_LABEL[k], color: AIC[k] }));
  // Chart 5 uses the resolution rule of charts 1 and 2: a problem is counted under the systems
  // credited on the first event that settled it, by that event's AI role. Problems whose first
  // resolution involved no AI are not on this chart.
  const aiFirst = DATA.map(p => [p, firstResolution(p)]).filter(([, e]) => e && e.ai !== 'none');
  const withCounts = m => { const ps = aiFirst.filter(([, e]) => (e.ai_models || []).includes(m));
    return Object.fromEntries(kinds.map(k => [k.key, ps.filter(([, e]) => e.ai === k.key).map(([p]) => p)])); };
  const total = d => kinds.reduce((s, k) => s + d[k.key].length, 0);
  const all = Object.entries(MODEL_RELEASES).map(([model, v]) => ({ model, ...v, ...withCounts(model) })).filter(d => total(d) > 0);
  // `available` is the private preview where a system had one, otherwise the public release —
  // the same date predates_availability compares a result against, so the chart and the flag agree.
  const items = all.filter(d => d.available).sort((a, b) => a.available.localeCompare(b.available) || a.model.localeCompare(b.model));
  const svg = $('#svg-release');

  if (!items.length) { svg.innerHTML = ''; $('#leg-release').innerHTML = ''; $('#release-note').textContent = 'No released model in this corpus is credited on a problem.'; return; }

  const bin = d => d.available.slice(0, 7);
  const END = MONTHS_AXIS[MONTHS_AXIS.length - 1];
  const MS = (() => { const out = []; const [y0, m0] = bin(items[0]).split('-').map(Number); let yy = y0, mm = m0;
    for (let i = 0; i < 120; i++) { const s = `${yy}-${String(mm).padStart(2, '0')}`; out.push(s); if (s >= END) break; mm++; if (mm > 12) { mm = 1; yy++; } }
    return out; })();
  const n = MS.length;
  // Wider viewBox than the other charts: this axis spans five years of monthly slots, and at
  // W=560 a month was 8px, which left the busiest month drawing 1.7px bars.
  const W = 1100, H = 300, m = { l: 34, r: 16, t: 18, b: 30 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b, bw = iw / n;
  // One bar per month: height is the number of problems credited to any system that became
  // available that month, stacked by kind of contribution. Two systems available in the same month
  // share one bar, and a problem credited to both is counted once in it.
  const groups = new Map();
  items.forEach(d => { const b = bin(d); if (!groups.has(b)) groups.set(b, []); groups.get(b).push(d); });
  const monthKind = (ds, k) => { const seen = new Set(); return ds.flatMap(d => d[k]).filter(p => !seen.has(p.id) && seen.add(p.id)); };
  const monthTot = ds => kinds.reduce((t, k) => t + monthKind(ds, k.key).length, 0);
  const yMax = Math.max(2, ...Array.from(groups.values(), monthTot));
  const y = v => m.t + ih - ih * v / yMax;

  let g = '';
  const yStep = yMax > 20 ? 5 : yMax > 8 ? 2 : 1;
  for (let v = 0; v <= yMax; v += yStep) g += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" stroke="var(--grid)"/><text x="${m.l - 6}" y="${y(v) + 3.5}" text-anchor="end">${v}</text>`;

  const topRect = (x, w, y0, y1, fill, extra) => { const h = Math.max(0, y0 - y1), r = Math.min(4, w / 2, h);
    return `<path d="M ${x} ${y0} L ${x} ${y1 + r} Q ${x} ${y1} ${x + r} ${y1} L ${x + w - r} ${y1} Q ${x + w} ${y1} ${x + w} ${y1 + r} L ${x + w} ${y0} Z" fill="${fill}" ${extra || ''}/>`; };

  let bars = '';
  for (const [b, ds] of groups) {
    const i = MS.indexOf(b); if (i < 0) continue;
    const w = Math.max(1.5, Math.min(30, bw - 2));
    const x = m.l + i * bw + (bw - w) / 2;
    const tot = monthTot(ds), who = ds.map(d => d.model).sort();
    let base = 0;
    kinds.forEach((kd, ki) => {
      const ps = monthKind(ds, kd.key), cnt = ps.length; if (!cnt) return;
      const y0 = y(base), y1 = y(base + cnt);
      const isTop = !kinds.slice(ki + 1).some(o => monthKind(ds, o.key).length);
      const names = ps.slice(0, 5).map(q => q.name).join(', ');
      const tip = `<b>${monthLabel(b)}</b> \u00b7 ${tot} problem${tot > 1 ? 's' : ''} credited`
        + `<br><span style="opacity:.75">${esc(who.join(', '))}</span>`
        + `<br>${kd.label}: ${cnt}<br><span style="opacity:.75">${esc(names)}${cnt > 5 ? `, +${cnt - 5} more` : ''}</span>`;
      bars += isTop ? topRect(x, w, y0, y1, kd.color, `data-tip="${attr(tip)}"`)
        : `<rect x="${x}" y="${y1}" width="${w}" height="${Math.max(0.8, y0 - y1 - 1)}" fill="${kd.color}" data-tip="${attr(tip)}"/>`;
      base += cnt;
    });
  }

  let ax = '';
  // Label interval is chosen from the width actually available, not from the month count, so the
  // ticks stay ~50px apart whatever the span.
  // 62px, not 50: the ticks now carry the full year ("Jan 2024"), which is wider than "Jan '24".
  const every = [1, 3, 6, 12].find(v => bw * v >= 62) || 12;
  MS.forEach((s, i) => {
    const mo = +s.slice(5);
    if ((mo - 1) % every) return;
    const lab = every >= 12 ? s.slice(0, 4) : monthLabel(s);
    ax += `<text x="${m.l + i * bw + bw / 2}" y="${H - 8}" text-anchor="middle">${lab}</text>`; });

  svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.style.width = '100%'; svg.style.height = 'auto';
  svg.innerHTML = `${g}${bars}<line x1="${m.l}" x2="${W - m.r}" y1="${y(0)}" y2="${y(0)}" stroke="var(--line)"/>${ax}`;

  const tot = k => items.reduce((s, d) => s + d[k].length, 0);
  $('#leg-release').innerHTML = kinds.filter(k => tot(k.key)).map(k => `<span data-tip="${attr(`<b>${k.label}</b><br>${tot(k.key)} across ${items.length} dated models`)}"><i style="background:${k.color}"></i>${k.label} <span class="mono" style="color:var(--ink-3)">${tot(k.key)}</span></span>`).join('');

  // Only two things a reader needs: which systems are missing from the axis, and which date each
  // bar sits on when a system has more than one.
  // Resolutions the chart cannot place: their first resolution credits no system with a date
  // (an internal model, an unversioned product name, or an AI the source did not name).
  const datedModel = m => (MODEL_RELEASES[m] || {}).available;
  const offChart = aiFirst.filter(([, e]) => !(e.ai_models || []).some(datedModel));
  $('#release-note').innerHTML =
    `Each resolution that involved AI is counted under the systems credited on the first event to settle the problem. A bar sits at the month a system first became <b>available</b> to the people who used it: the private preview where there was one, otherwise the public release. A resolution credited to systems that arrived in different months appears once under each of them, so the bars sum to more than the number of problems.` +
    (offChart.length ? ` <b>${offChart.length} of the ${aiFirst.length}</b> AI resolutions are not on the chart: the systems credited have no public release date (an internal model such as OpenAI's), name no version, or are not named at all.` : '');
  attachTip(svg, $('#tip-a3')); attachTip($('#leg-release'), $('#tip-a3'));
}

/* ============================ TAB 1 · attribution ============================ */
function renderAttribution() {
  const changed = DATA.filter(p => p.status !== 'open');
  const rc = changed.filter(p => ['resolved', 'claimed'].includes(p.status));
  // A retracted claim on a still-open problem is not an advance — the problem did not move — so
  // those rows are out of the progress count as well as out of the chart below.
  const retracted = p => p.ai_involvement === 'incident' && !['resolved', 'claimed'].includes(p.status);
  const progAll = DATA.filter(p => ['resolved', 'claimed', 'partial', 'progress'].includes(p.status) && !retracted(p));
  const pct = (a, b) => `${Math.round(100 * a / b)}%`;
  const tile = (v, u, l, extra) => `<div class="stat"><div class="v"><span>${v}</span><span class="u">${u}</span></div>${extra || ''}<div class="l">${l}</div></div>`;
  // The tiles use the per-chart rules above: a resolution is credited by the first event that
  // settled the problem, and progress counts every event, with mixed problems shown as such.
  const firsts = DATA.map(p => [p, firstResolution(p)]).filter(([, e]) => e);
  const firstAI = firsts.filter(([, e]) => e.ai !== 'none');
  const moved = DATA.map(p => progressCredit(p)).filter(Boolean);
  const nMoved = k => moved.filter(c => c === k).length;
  $('#a-stats').innerHTML = [
    tile(DATA.length, 'open problems', 'listed by Wikipedia in January 2024'),
    // "resolved" is in quotes because most of these are not: only those with a checked
    // whole-problem event are accepted, and the rest are preprints and announcements nobody has
    // checked. The subtitle gives the split.
    tile(firsts.length, 'problems “resolved”', `${firsts.filter(([p]) => resolutionAccepted(p)).length} accepted, ${firsts.filter(([p]) => !resolutionAccepted(p)).length} still contested`),
    tile(pct(firstAI.length, firsts.length), 'involved an AI system',
      `of the ${firsts.length} resolutions, credited by the first event to settle each`,
      `<div class="v v2"><span class="n2">${pct(firsts.filter(([, e]) => e.ai === 'generated').length, firsts.length)}</span><span class="u">done entirely by AI</span></div>`),
    tile(moved.length, 'saw any progress',
      `${pct(nMoved('generated'), moved.length)} ${PROGRESS_LABEL.generated}, ${pct(nMoved('assisted') + nMoved('both'), moved.length)} AI-assisted or by AI and humans both`),
  ].join('');


  // The two panels used to share one axis, which drew the 30 resolutions as a sliver beside the
  // 158 progressed problems. Each now scales to its own total, rounded up for headroom, so the
  // panels are read against their axes rather than against each other.
  const niceMax = v => [10, 20, 25, 50, 75, 100, 150, 200, 250, 300, 400, 500].find(t => t >= v * 1.2) || Math.ceil(v * 1.2 / 100) * 100;
  // 'norm' restacks to the running total of the chart's own rows, so it is a share of the results
  // so far, not of the corpus — the wording differs from the other two modes for that reason.
  const yLabel = what => state.cMode === 'count' ? `Number of Problems ${what}`
    : state.cMode === 'share' ? `Percent of All Problems ${what}`
      : `Portion of Problems ${what}, to Date`;
  // Chart 2 uses the rule of the tiles: a problem enters on the date of the first event to settle
  // it, in the colour of that event's AI role. A year-only date places it nowhere on a month axis.
  const resA = DATA.filter(p => firstResolution(p));
  const ROLE_TO_ATTR = { generated: 'ai', assisted: 'with', none: 'human' };
  const resBands = ATTR.map(([k, lab, color]) => ({ key: `-${k}`, label: lab[0].toUpperCase() + lab.slice(1), color,
    test: p => ROLE_TO_ATTR[firstResolution(p).ai] === k }));
  const firstMonth = p => { const e = firstResolution(p); return e.precision === 'year' ? null : String(e.date || '').slice(0, 7) || null; };
  cumulativeChart('#svg-cum-a', '#leg-cum-a', '#tip-c1', resA, resBands,
    { yMax: niceMax(resA.length), yLabel: yLabel('Resolved'), monthOf: firstMonth });
  // Chart 3 uses the progress rule of the tiles: every relevant event counts, and a problem is AI
  // only, AI-assisted or both, or human by all of them together. It enters on the date of its
  // first relevant event. Resolved problems (chart 2's set) are shaded darker within each colour.
  const movedB = DATA.filter(p => progressCredit(p));
  // 'both' sits between human and AI-assisted, in the assisted colour but hatched.
  const CREDIT = [['none', 'human only', AIC.none, false], ['both', 'AI and human both', AIC.assisted, true],
    ['assisted', 'AI-assisted', AIC.assisted, false], ['generated', 'AI only', AIC.generated, false]];
  const progBands = (prefix, extra, opacity) => CREDIT.map(([k, lab, color, hatch]) =>
    ({ key: `${prefix}-${k}`, label: `${prefix}, ${lab}`, color, hatch, opacity, test: p => extra(p) && progressCredit(p) === k }));
  const firstMoved = p => { const e = sinceSnapshot(p).sort(byDate)[0]; return !e || e.precision === 'year' ? null : String(e.date || '').slice(0, 7) || null; };
  cumulativeChart('#svg-cum-b', '#leg-cum-b', '#tip-c2', movedB,
    [...progBands('Resolved', p => !!firstResolution(p), .95), ...progBands('Progress', p => !firstResolution(p), .5)],
    { yMax: niceMax(movedB.length), yLabel: yLabel('Materially Advanced'), monthOf: firstMoved });

  const share = state.aMode === 'share';
  // Four rows, by what has happened to the problem. `open_stale` is left out: those were settled
  // before the snapshot, so they are neither movement nor an open problem. `partial` and
  // `progress` are one row, because the split between them is about the kind of advance, which is
  // not what this chart is asking.
  // Each row counts problems, by the rule of the chart above it: a resolved or claimed problem is
  // credited by the first event that settled it (charts 1 and 2), and a problem that only moved is
  // credited by all its relevant events (chart 3), so it can be AI and human both.
  const settledBefore = p => !sinceSnapshot(p).length && (p.events || []).some(e => e.after_snapshot === false && e.tier === 'resolved');
  const STATUS_ROWS = [
    ['Resolved', p => firstResolution(p) && resolutionAccepted(p), 'first'],
    ['Resolution claimed', p => firstResolution(p) && !resolutionAccepted(p), 'first'],
    ['Progress of some kind', p => !firstResolution(p) && progressCredit(p), 'progress'],
    // Settled before the snapshot is neither movement nor an open problem, so it is left out.
    ['Still open', p => !progressCredit(p) && !settledBefore(p), 'open'],
  ];
  const OPEN_C = 'var(--st-open)';
  // [key, label, colour, hatched]: the same four kinds of credit as chart 3, in the same order.
  const KINDS = [['none', AI_LABEL.none, AIC.none, false], ['both', 'AI and human both', AIC.assisted, true],
    ['assisted', AI_LABEL.assisted, AIC.assisted, false], ['generated', AI_LABEL.generated, AIC.generated, false]];
  const kindOf = (p, rule) => rule === 'first' ? (firstResolution(p).ai || 'none') : progressCredit(p);
  const maxTotal = Math.max(...STATUS_ROWS.map(([, f]) => DATA.filter(f).length));
  $('#a-status-bars').innerHTML = STATUS_ROWS.map(([label, f, rule]) => {
    const ps = DATA.filter(f); if (!ps.length) return '';
    // A still-open problem has not been solved by anyone, so it does not share the colour of work
    // finished without AI: it gets its own, and the row reads as one flat band.
    const g = rule === 'open'
      ? [{ label: 'Not yet solved', color: OPEN_C, n: ps.length, ps }]
      : KINDS.map(([k, lab, color, hatch]) => ({ label: lab, color, hatch, n: ps.filter(p => kindOf(p, rule) === k).length, ps: ps.filter(p => kindOf(p, rule) === k) }));
    return barRow(label, g, { denom: share ? ps.length : maxTotal, nText: `${ps.length}`, noNames: true });
  }).join('');
  const LEG = [...KINDS.map(([k, lab, color, hatch]) => [lab, color, hatch,
    STATUS_ROWS.filter(([, , r]) => r !== 'open').reduce((s, [, f, r]) => s + DATA.filter(p => f(p) && kindOf(p, r) === k).length, 0)]),
    ['Not yet solved', OPEN_C, false, DATA.filter(STATUS_ROWS[3][1]).length]];
  $('#a-legend').innerHTML = LEG.filter(([, , , n]) => n).map(([lab, color, hatch, n]) => `<span data-tip="${attr(`<b>${esc(lab)}</b><br>${n} problems`)}"><i style="background:${hatch ? hatchCSS(color) : color}"></i>${esc(lab)}</span>`).join('');
  attachTip($('#a-status'), $('#tip-a1'));


  releaseChart();

  // Chart 6 counts problems, not events: a problem appears under a system if that system is credited
  // on any of its relevant events. The shading follows the system's own contribution: darker where
  // it was credited on an event settling the whole problem (resolved or claimed), lighter where its
  // credits were only partial results or bounds. Within that, the strongest role it had on those
  // events (generated over assisted).
  // `unnamed model` is the placeholder for a credit no source attaches a name to: it stays in the
  // data and the Explore filter, but it is not a system, so it gets no bar here.
  const named = m => m !== 'unnamed model';
  const WHOLE = e => e.tier === 'resolved' || e.tier === 'claimed';
  const creditsOf = p => { const out = new Map();             // model -> { resolved, role }
    sinceSnapshot(p).forEach(e => { if (!e.ai || e.ai === 'none') return;
      (e.ai_models || []).forEach(m => {
        const cur = out.get(m), res = WHOLE(e);
        if (!cur || (res && !cur.resolved)) out.set(m, { resolved: res, role: e.ai });   // a resolution outranks progress
        else if (res === cur.resolved && e.ai === 'generated') cur.role = 'generated';  // then generated outranks assisted
      }); });
    return out; };
  const credits = DATA.map(p => ({ p, c: creditsOf(p) })).filter(x => x.c.size);
  const problemsUnder = m => credits.filter(x => x.c.has(m));
  const ORDER6 = [...new Set(credits.flatMap(x => [...x.c.keys()]))].filter(named)
    .sort((a, b) => problemsUnder(b).length - problemsUnder(a).length || a.localeCompare(b));
  const maxM = Math.max(1, ...ORDER6.map(m => problemsUnder(m).length));
  const SEGS6 = [[true, 'generated'], [true, 'assisted'], [false, 'generated'], [false, 'assisted']];
  const segsFor = m => SEGS6.map(([res, k]) => { const ps = problemsUnder(m).filter(x => x.c.get(m).resolved === res && x.c.get(m).role === k).map(x => x.p);
    return { label: `${res ? 'Credited on a resolution' : 'Credited on progress'}, ${AI_LABEL[k]}`, color: AIC[k], opacity: res ? 0.95 : 0.5, n: ps.length, ps }; });
  $('#a-model-bars').innerHTML = LAB_ORDER.filter(l => ORDER6.some(m => GROUP_OF(m) === l)).map(l => {
    const ms = ORDER6.filter(m => GROUP_OF(m) === l);
    const labN = credits.filter(x => [...x.c.keys()].some(m => named(m) && GROUP_OF(m) === l)).length;
    return `<div class="labgroup">${esc(l)} <span class="mono" style="letter-spacing:0;text-transform:none">${labN} problem${labN > 1 ? 's' : ''}</span></div>` +
      ms.map(m => barRow(m, segsFor(m), { denom: maxM, labW: 150 })).join('');
  }).join('');
  attachTip($('#a-models'), $('#tip-a2'));

}

/* ============================ TAB 2 · outcomes ============================ */
// Which way a result went is p.resolution_direction (refuted | confirmed | mixed), and whether it
// is an exhibited counterexample is p.counterexample. They are separate: a question answered in
// the negative is refuted with no counterexample to a stated conjecture. p.outcome is prose.
const OUT_ORDER = ['refuted', 'confirmed', 'mixed'];
const OUT_LABEL = { refuted: 'Refuted', confirmed: 'Proved', mixed: 'Contested' };
const OUTC = { refuted: 'var(--o-disproved)', confirmed: 'var(--o-proved)', mixed: 'var(--o-mixed)' };
// The direction as a reader should see it: a full resolution proved or refuted the problem, a
// partial result only one case of it, and a moved bound went no direction at all.
const CASE_LABEL = { refuted: 'Case refuted', confirmed: 'Case proved', mixed: 'Cases mixed' };
const dirLabel = p => isRes(p) ? OUT_LABEL[p.resolution_direction] || '' : p.status === 'partial' ? CASE_LABEL[p.resolution_direction] || '' : '';
const isCx = p => !!p.counterexample;
function renderOutcomes() {
  const rc = DATA.filter(p => ['resolved', 'claimed'].includes(p.status));
  const ai = rc.filter(aiTouched), hum = rc.filter(p => !aiTouched(p));
  const gen = rc.filter(p => p.ai_involvement === 'generated');
  const shareCx = ps => ps.length ? Math.round(100 * ps.filter(isCx).length / ps.length) : 0;
  $('#x-stats').innerHTML = [
    [`${shareCx(gen)}%`, 'of AI-generated resolutions', `are counterexamples rather than proofs — ${gen.filter(isCx).length} of ${gen.length}`],
    [`${shareCx(ai)}%`, 'of AI-generated or AI-assisted', `are counterexamples rather than proofs — ${ai.filter(isCx).length} of ${ai.length}`],
    [`${shareCx(hum)}%`, 'of resolutions without AI', `are counterexamples rather than proofs — ${hum.filter(isCx).length} of ${hum.length}`],
  ].map(([v, u, l]) => `<div class="stat"><div class="v"><span>${v}</span><span class="u">${u}</span></div><div class="l">${l}</div></div>`).join('');


  // Every resolution first, as the baseline the four breakdown rows are read against. `gap` sets
  // that row off from the breakdown, the three AI rows off from the row without AI, and the last
  // row off from the legend.
  const groups = [['All resolutions', rc, true], ['AI-generated', rc.filter(p => p.ai_involvement === 'generated')], ['AI-assisted', rc.filter(p => p.ai_involvement === 'assisted')], ['AI-generated OR AI-assisted', ai, true], ['No AI involvement', hum, true]];
  $('#x-split-bars').innerHTML = groups.map(([lab, ps, gap]) => barRow(lab, OUT_ORDER.map(k => ({ label: OUT_LABEL[k], color: OUTC[k], n: ps.filter(p => p.resolution_direction === k).length, ps: ps.filter(p => p.resolution_direction === k) })), { labW: 170, gapAfter: gap })).join('');
  $('#leg-x-split').innerHTML = OUT_ORDER.map(k => `<span><i style="background:${OUTC[k]}"></i>${OUT_LABEL[k]}</span>`).join('');
  attachTip($('#x-split'), $('#tip-x3'));

  // Two panels on one scale: resolutions on the left, every kind of movement on the right, both
  // split into the same three buckets by who did the work.
  const mov = DATA.filter(p => isRes(p) || ['partial', 'progress'].includes(p.status));
  const perField = set => FIELD_ORDER.map(f => [f, set.filter(p => p.field === f)]).filter(([, ps]) => ps.length).sort((a, b) => b[1].length - a[1].length);
  const fres = perField(rc), fmov = perField(mov);
  const fieldTotal = f => DATA.filter(p => p.field === f).length;
  // Both panels are scaled to the largest field on either of them, so a bar's length is a share of
  // the whole corpus's biggest field and the outlines are comparable across the two panels.
  const maxF = Math.max(1, ...fres.map(([f]) => fieldTotal(f)), ...fmov.map(([f]) => fieldTotal(f)));
  // The label column is wide enough for the longest field name ("Model theory and formal
  // languages"), so no truncation here; .brow .lab still ellipsises if one grows longer.
  const fieldBars = rows => rows.map(([f, ps]) => barRow(f, aiGroups3(ps),
    { denom: maxF, labW: 212, outline: fieldTotal(f), nText: `${ps.length}/${fieldTotal(f)}` })).join('');
  const fieldLeg = set => ATTR.map(([k, , color]) => set.some(p => attrOf(p) === k)
    ? `<span><i style="background:${color}"></i>${ATTR_LABEL[k]}</span>` : '').join('');
  $('#x-field-bars').innerHTML = fieldBars(fres);
  $('#leg-x-fields').innerHTML = fieldLeg(rc);
  $('#x-field-bars-mov').innerHTML = fieldBars(fmov);
  $('#leg-x-fields-mov').innerHTML = fieldLeg(mov);
  attachTip($('#x-fields-res'), $('#tip-x4')); attachTip($('#x-fields-mov'), $('#tip-x5'));


  const rows = rc.slice().sort((x, y) => (y.month_resolved || String(y.year_resolved || '')).localeCompare(x.month_resolved || String(x.year_resolved || '')));
  // The chip is the direction the result went, through OUT_LABEL (Refuted / Proved / Contested).
  // It used to read `p.outcome`, which is the prose account of what happened, not a token — which
  // is why every row rendered a paragraph inside a one-word chip. That prose is the fold-out below.
  $('#x-hl').innerHTML = `<ol>${rows.map(p => {
    const dir = p.resolution_direction;
    const chip = dir ? `<span class="st ${p.status}" style="color:${OUTC[dir]};background:transparent;border:1px solid currentColor">${OUT_LABEL[dir]}${p.status === 'claimed' ? ' (claimed)' : ''}</span>` : '';
    const fold = p.outcome ? `<span class="fold"><span class="fold-body"><span class="fold-inner">${esc(p.outcome)}<span class="llmtag">Summary is LLM generated</span></span></span></span>` : '';
    return `<li><span class="d">${p.month_resolved ? monthLabel(p.month_resolved).replace(' ', '\u00a0') : p.year_resolved}</span><span><b>${esc(p.name)}</b> ${chip}${aiTouched(p) ? ` <span class="ai">✦ ${esc(p.ai_system || 'AI')}</span>` : ''}<div class="who">${esc(p.resolved_by || '')}</div>${fold}</span></li>`;
  }).join('')}</ol>`;
}

/* ============================== TAB 3 · origins ==============================*/
function renderOrigins() {
  const withY = DATA.filter(p => p.year_introduced != null);
  // year_introduced is researched by a pass of its own, which has not been run for this version:
  // only the five Millennium problems carry a year, from build.py's own list. Five is not a
  // corpus, so the tab says so rather than drawing an age distribution over it.
  if (withY.length < 20) {
    $('#view-origins').innerHTML = `<div class="sub" style="padding:24px 0">The year each problem was
      posed is not part of this dataset version — it is researched by a separate pass that has not
      been run. ${withY.length} of ${DATA.length} problems carry a year, so the age charts are
      omitted rather than drawn over a handful of records.</div>`;
    return;
  }
  const oldest = withY.reduce((a, b) => a.year_introduced < b.year_introduced ? a : b);
  const ageOf = p => (p.year_resolved || 2026) - p.year_introduced;
  const rcY = withY.filter(p => ['resolved', 'claimed'].includes(p.status));
  const mean = xs => xs.reduce((s, p) => s + ageOf(p), 0) / xs.length;
  const medOf = xs => { const a = xs.map(ageOf).sort((x, y) => x - y); return a[Math.floor(a.length / 2)]; };
  const AGE_ROWS = [
    ['All listed problems', withY, 'var(--ai-none)'],
    ['Resolved with an AI system', rcY.filter(aiTouched), 'var(--ai-gen)'],
    ['Resolved without AI', rcY.filter(p => !aiTouched(p)), 'var(--ai-bound)'],
  ];
  const seOf = xs => { const a = xs.map(ageOf), m = mean(xs); return Math.sqrt(a.reduce((s, v) => s + (v - m) ** 2, 0) / (a.length - 1) / a.length); };
  (() => {
    const W = 900, m = { l: 34, r: 34 };
    const hi = Math.max(...AGE_ROWS.map(([, xs]) => mean(xs) + seOf(xs)));
    const xMax = Math.ceil(hi / 20) * 20 + 20;
    const iw = W - m.l - m.r, X = v => m.l + iw * v / xMax;
    // Labels are placed in lanes so they never sit on top of each other: each row takes the
    // nearest free lane in its zone, and the zone grows to fit. Fixed offsets collided whenever
    // two means landed close together, which is exactly what happens when the groups agree.
    const CH = 6.4, LANE = 30, PAD = 10;
    const place = AGE_ROWS.map(([lab, xs], k) => {
      const mv = mean(xs), w = Math.max(lab.length, 12) * CH;
      const anchor = mv / xMax > 0.82 ? 'end' : mv / xMax < 0.08 ? 'start' : 'middle';
      const cx = X(mv);
      const x0 = anchor === 'end' ? cx - w : anchor === 'start' ? cx : cx - w / 2;
      return { k, mv, up: k !== 2, anchor, x0, x1: x0 + w };
    });
    const lanes = { up: [], down: [] };
    for (const p of place) {
      const zone = p.up ? lanes.up : lanes.down;
      let i = 0;
      while (zone[i] && zone[i].some(o => p.x0 < o.x1 + PAD && o.x0 < p.x1 + PAD)) i++;
      (zone[i] = zone[i] || []).push(p);
      p.lane = i;
    }
    const upDepth = (lanes.up.length ? (lanes.up.length - 1) * LANE : 0) + 40;
    const downDepth = (lanes.down.length ? (lanes.down.length - 1) * LANE : 0) + 70;
    const yA = upDepth + 8, H = yA + downDepth + 8;
    let ax = `<line x1="${m.l}" x2="${W - m.r}" y1="${yA}" y2="${yA}" stroke="var(--canvas-line)" stroke-width="2"/>`;
    for (let v = 0; v <= xMax; v += 20) ax += `<line x1="${X(v)}" x2="${X(v)}" y1="${yA}" y2="${yA + 6}" stroke="var(--canvas-line)"/><text x="${X(v)}" y="${yA + 20}" text-anchor="middle">${v}</text>`;
    ax += `<text x="${W - m.r}" y="${yA + 36}" text-anchor="end">years standing</text>`;
    const pts = AGE_ROWS.map(([lab, xs, col], k) => {
      const P = place[k], mv = P.mv, se = seOf(xs), up = P.up;
      const off = (up ? 22 : 52) + P.lane * LANE;
      const ty = up ? yA - off : yA + off, anchor = P.anchor;
      const tip = attr(`<b>${lab}</b><br>${xs.length} problems<br>mean ${mv.toFixed(1)} yr ± ${se.toFixed(1)} (SE)<br>median ${medOf(xs)} yr`);
      // One standard error either side, drawn as the parentheses of an interval: ( • )
      const paren = (x, s) => `<path d="M${x + 3 * s},${yA - 9} Q${x - 3 * s},${yA} ${x + 3 * s},${yA + 9}" fill="none" stroke="${col}" stroke-width="2" stroke-linecap="round"/>`;
      return `<g data-tip="${tip}">` + paren(X(mv - se), 1) + paren(X(mv + se), -1) +
        `<circle cx="${X(mv)}" cy="${yA}" r="6.5" fill="${col}" stroke="var(--bg)" stroke-width="2"/>` +
        `<line x1="${X(mv)}" x2="${X(mv)}" y1="${up ? ty + 6 : ty - 12}" y2="${up ? yA - 9 : yA + 9}" stroke="${col}" stroke-width="1" opacity=".5"/>` +
        `<text x="${X(mv)}" y="${ty}" text-anchor="${anchor}" class="aval" fill="${col}">${mv.toFixed(0)} ± ${se.toFixed(0)} yr</text>` +
        `<text x="${X(mv)}" y="${ty + (up ? -14 : 14)}" text-anchor="${anchor}" class="alab">${lab}</text></g>`;
    }).join('');
    const svg = $('#o-mean-svg'); svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.style.width = '100%'; svg.style.height = 'auto';
    svg.innerHTML = ax + pts;
    attachTip($('#o-mean'), $('#tip-o0'));
    const all = AGE_ROWS[0][1];
    $('#o-mean-note').innerHTML = `Points are means; the parentheses mark one standard error either side. The mean for the whole list, ${mean(all).toFixed(0)} years, is pulled up by a handful of problems from antiquity — its median is ${medOf(all)}.`;
  })();

  (() => {
    const rcAll = rcY, D1 = 2020;
    const D0 = Math.floor(Math.min(...rcAll.map(p => p.year_introduced)) / 10) * 10, nb = (D1 - D0) / 10 + 1;
    const sets = [
      ['#o-ai-svg', '#o-ai', '#tip-o3', '#o-ai-sub', rcY.filter(aiTouched), 'var(--ai-gen)', 'with an AI system'],
      ['#o-hum-svg', '#o-hum', '#tip-o4', '#o-hum-sub', rcY.filter(p => !aiTouched(p)), 'var(--ai-none)', 'without AI'],
    ];
    const binOf = ps => { const b = {}; ps.forEach(p => { if (p.year_introduced >= D0) b[Math.floor(p.year_introduced / 10) * 10] = (b[Math.floor(p.year_introduced / 10) * 10] || 0) + 1; }); return b; };
    const bins = sets.map(([, , , , ps]) => binOf(ps));
    const yMax = Math.max(2, ...bins.flatMap(b => Object.values(b)));
    sets.forEach(([sel, panel, tip, sub, ps, col, lab], si) => {
      const W = 1000, H = 150, m = { l: 34, r: 14, t: 10, b: 26 };
      const iw = W - m.l - m.r, ih = H - m.t - m.b, bw = iw / nb, Y = v => m.t + ih - ih * v / yMax;
      let g = '';
      for (let v = 0; v <= yMax; v++) g += `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--grid)"/><text x="${m.l - 6}" y="${Y(v) + 3.5}" text-anchor="end">${v}</text>`;
      let bars = '';
      for (let i = 0; i < nb; i++) {
        const d = D0 + i * 10, v = bins[si][d] || 0; if (!v) continue;
        const list = ps.filter(p => Math.floor(p.year_introduced / 10) * 10 === d);
        const t = attr(`<b>${d}s</b><br>${v} resolved ${lab}<br><span style="opacity:.75">${esc(names(list))}</span>`);
        bars += `<rect x="${m.l + i * bw + 0.8}" y="${Y(v)}" width="${Math.max(2, bw - 1.6)}" height="${Y(0) - Y(v)}" rx="2" fill="${col}" data-tip="${t}"/>`;
      }
      let ax = '';
      for (let d = D0; d <= D1; d += 20) ax += `<text x="${m.l + (d - D0) / 10 * bw + bw / 2}" y="${H - 9}" text-anchor="middle">${d}</text>`;
      const svg = $(sel); svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.style.width = '100%'; svg.style.height = 'auto';
      svg.innerHTML = `${g}${bars}<line x1="${m.l}" x2="${W - m.r}" y1="${Y(0)}" y2="${Y(0)}" stroke="var(--line)"/>${ax}`;
      $(sub).textContent = `${ps.length} problems resolved ${lab}, placed in the decade each was first posed`;
      attachTip($(panel), $(tip));
    });
  })();

  // Status only, with `partial` and `progress` as one band: the split between a case settled and a
  // bound moved is about the kind of advance, which is not what a chart of when problems were posed
  // is asking. `open` gets its own colour rather than sharing one with work finished without AI.
  const KEYS = ['resolved', 'claimed', 'progress', 'open_stale', 'open'];
  const KLAB = { resolved: 'Resolved', claimed: 'Resolution claimed', progress: 'Progress of some kind', open_stale: 'Settled before snapshot', open: 'Still open' };
  const KCOL = { resolved: 'var(--ai-gen)', claimed: 'var(--ai-asst)', progress: 'var(--o-proved)', open_stale: 'var(--o-mixed)', open: 'var(--st-open)' };
  const keyOf = p => p.status === 'partial' ? 'progress' : p.status;
  const W = 1000, H = 260, m = { l: 40, r: 14, t: 14, b: 30 };
  const d0 = 1600, d1 = 2020, n = (d1 - d0) / 10 + 1;
  const inRange = DATA.filter(p => p.year_introduced != null && p.year_introduced >= d0);
  const pre = DATA.filter(p => p.year_introduced != null && p.year_introduced < d0);
  const und = DATA.length - inRange.length - pre.length;
  const dec = {}; inRange.forEach(p => { const d = Math.floor(p.year_introduced / 10) * 10; (dec[d] ||= {})[keyOf(p)] = ((dec[d] || {})[keyOf(p)] || 0) + 1; });
  const tot = d => Object.values(dec[d] || {}).reduce((s, v) => s + v, 0);
  const maxV = Math.max(1, ...Array.from({ length: n }, (_, i) => tot(d0 + i * 10)));
  const iw = W - m.l - m.r, ih = H - m.t - m.b, bw = iw / n, y = v => m.t + ih - ih * v / maxV;
  const step = maxV > 40 ? 20 : maxV > 16 ? 10 : 5;
  let g = '';
  for (let v = 0; v <= maxV; v += step) g += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" stroke="var(--grid)"/><text x="${m.l - 7}" y="${y(v) + 3.5}" text-anchor="end">${v}</text>`;
  let bars = '';
  for (let i = 0; i < n; i++) {
    const d = d0 + i * 10, t = tot(d); if (!t) continue;
    let acc = 0; const x = m.l + i * bw + 1;
    KEYS.forEach(k => {
      const v = (dec[d] || {})[k] || 0; if (!v) return;
      const y1 = y(acc + v), y0 = y(acc); acc += v;
      const top = acc === t;
      const list = inRange.filter(p => Math.floor(p.year_introduced / 10) * 10 === d && keyOf(p) === k);
      const tip = `<b>${d}s · ${KLAB[k]}</b><br>${v} of ${t} posed this decade<br><span style="opacity:.75">${esc(names(list))}</span>`;
      bars += `<rect x="${x}" y="${y1}" width="${Math.max(1.5, bw - 2)}" height="${Math.max(0.8, y0 - y1 - (top ? 0 : 1))}" fill="${KCOL[k]}" ${top ? 'rx="2"' : ''} data-tip="${attr(tip)}"/>`;
    });
  }
  let ax = '';
  for (let d = 1600; d <= 2020; d += 40) ax += `<text x="${m.l + (d - d0) / 10 * bw + bw / 2}" y="${H - 9}" text-anchor="middle">${d}</text>`;
  const svg = $('#o-svg');
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.style.width = '100%'; svg.style.height = 'auto';
  svg.innerHTML = `${g}${bars}<line x1="${m.l}" x2="${W - m.r}" y1="${y(0)}" y2="${y(0)}" stroke="var(--line)"/>${ax}`;
  $('#o-legend').innerHTML = KEYS.filter(k => inRange.some(p => keyOf(p) === k)).map(k => `<span data-tip="${attr(`<b>${KLAB[k]}</b><br>${DATA.filter(p => keyOf(p) === k).length} problems`)}"><i style="background:${KCOL[k]}"></i>${KLAB[k]}</span>`).join('');
  $('#o-note').innerHTML = `Not drawn: ${pre.length} problems posed before 1600 (from ${fmtYear(oldest.year_introduced)} onwards) and ${und} I could not date. Colour marks status as of September 2026: the problems that have moved were posed across the whole span rather than clustering in any one era. ${Math.round(100 * withY.filter(p => p.year_introduced >= 1950).length / withY.length)}% of the dated problems were posed in 1950 or later, and the single busiest decade is the ${(() => { let best = 0, bd = 0; for (let i = 0; i < n; i++) { const t = tot(d0 + i * 10); if (t > best) { best = t; bd = d0 + i * 10; } } return `${bd}s with ${best}`; })()}.`;
  attachTip(svg, $('#tip-o1')); attachTip($('#o-legend'), $('#tip-o1'));

  const fell = DATA.filter(p => ['resolved', 'claimed'].includes(p.status) && p.year_introduced != null && p.year_resolved)
    .map(p => ({ p, yrs: p.year_resolved - p.year_introduced })).sort((x, y) => y.yrs - x.yrs);
  const maxY = Math.max(...fell.map(f => f.yrs));
  $('#o-open-bars').innerHTML = fell.map(({ p, yrs }) => {
    const col = p.ai_involvement === 'generated' ? AIC.generated : p.ai_involvement === 'assisted' ? AIC.assisted : AIC.none;
    const tip = `<b>${esc(p.name)}</b><br>posed ${fmtYear(p.year_introduced)}${p.year_source && p.year_source.startsWith('math') ? ' (approx.)' : ''} · ${p.status === 'claimed' ? 'claimed' : 'resolved'} ${p.year_resolved}<br>${yrs} years open<br><span style="opacity:.75">${esc(p.resolved_by || '')}</span>`;
    return `<div class="brow"><span class="lab" style="width:210px" data-tip="${attr(tip)}">${esc(p.name.length > 30 ? p.name.slice(0, 29) + '…' : p.name)}</span><span class="track"><i style="width:${100 * yrs / maxY}%;background:${col}" data-tip="${attr(tip)}"></i></span><span class="n" data-tip="${attr(tip)}">${yrs} yr</span></div>`;
  }).join('');
  const s = fell.map(f => f.yrs).sort((a, b) => a - b), k = s.length;
  const median = k % 2 ? s[(k - 1) / 2] : (s[k / 2 - 1] + s[k / 2]) / 2;
  const undated = DATA.filter(p => ['resolved', 'claimed'].includes(p.status)).length - k;
  const top = fell[0].p;
  $('#o-open-note').innerHTML = `<span class="legend" style="margin:0 0 6px"><span><i style="background:${AIC.generated}"></i>AI-generated</span><span><i style="background:${AIC.assisted}"></i>AI-assisted</span><span><i style="background:${AIC.none}"></i>no AI</span></span><br>The ${k} resolved or claimed problems whose posing year is known, longest-standing first${undated ? `; ${undated} more have no known year and are not shown` : ''}. Half had been open for more than ${median} years. The longest-standing was ${esc(top.name)}, posed in ${fmtYear(top.year_introduced)}${top.status === 'claimed' ? ', and its resolution is still only claimed' : ''}. The chart at the top of this tab compares how long the AI and non-AI results had stood.`;
  attachTip($('#o-open'), $('#tip-o2'));
}

function renderSince(rows) {
  const changed = rows.filter(p => p.status !== 'open');
  const cats = ['resolved', 'claimed', 'partial', 'progress', 'open_stale'];
  const max = Math.max(1, ...cats.map(c => changed.filter(p => p.status === c).length));
  const rowsHtml = cats.map(c => {
    const ps = changed.filter(p => p.status === c); if (!ps.length) return '';
    const segs = AI_ORDER.map(a => {
      const n = ps.filter(p => p.ai_involvement === a).length; if (!n) return '';
      const names = ps.filter(p => p.ai_involvement === a).slice(0, 4).map(p => p.name).join(', ');
      const tip = `<b>${STATUS_LABEL[c]} · ${AI_LABEL[a]}</b><br>${n} of ${ps.length} (${Math.round(100 * n / ps.length)}%)<br><span style="opacity:.75">${esc(names)}${n > 4 ? `, +${n - 4} more` : ''}</span>`;
      return `<i style="width:${100 * n / max}%;background:${AIC[a]}" data-tip="${tip.replace(/"/g, '&quot;')}" data-cat="${a}"></i>`;
    }).join('');
    const rowTip = `<b>${STATUS_LABEL[c]}</b>: ${ps.length}<br>` + AI_ORDER.filter(a => ps.some(p => p.ai_involvement === a)).map(a => `${AI_LABEL[a]}: ${ps.filter(p => p.ai_involvement === a).length}`).join('<br>');
    return `<div class="row"><span class="lab" data-tip="${rowTip.replace(/"/g, '&quot;')}">${STATUS_LABEL[c]}</span><span class="track">${segs}</span><span class="n" data-tip="${rowTip.replace(/"/g, '&quot;')}">${ps.length}</span></div>`;
  }).join('');
  const hl = changed.filter(p => ['resolved', 'claimed'].includes(p.status)).sort((a, b) => (b.year_resolved || 0) - (a.year_resolved || 0) || a.name.localeCompare(b.name));
  $('#since').innerHTML = `<div class="tip" id="tip3"></div><div><h3>What changed after the snapshot</h3><div class="sub">${changed.length} of ${rows.length} problems in the selection have moved; bars split by who did the work — hover any band for its exact count</div>${rowsHtml || '<div class="small">No changes in the current selection.</div>'}
    <div class="legend">${AI_ORDER.filter(a => changed.some(p => p.ai_involvement === a)).map(a => `<span data-tip="<b>${AI_LABEL[a]}</b><br>${changed.filter(p => p.ai_involvement === a).length} of the ${changed.length} changes"><i style="background:${AIC[a]}"></i>${AI_LABEL[a]}</span>`).join('')}</div>
    <div class="small" style="margin-top:8px">${changed.filter(aiTouched).length} of the ${changed.length} changes involved an AI system; of the ${changed.filter(p => ['resolved', 'claimed'].includes(p.status)).length} resolved or claimed, ${changed.filter(p => p.ai_involvement === 'generated' && ['resolved', 'claimed'].includes(p.status)).length} were AI-generated and ${changed.filter(p => p.ai_involvement === 'assisted' && ['resolved', 'claimed'].includes(p.status)).length} AI-assisted.</div></div>
    <div><h3>Resolved or claimed, newest first</h3><div class="sub">every problem in the selection now carrying a proof or counterexample</div><div class="hl"><ol>${hl.slice(0, 10).map(p => `<li><span class="d">${p.year_resolved}</span><span><b>${esc(p.name)}</b> <span class="st ${p.status}">${OUT_LABEL[p.resolution_direction] || ''}${p.status === 'claimed' ? ' (claimed)' : ''}</span>${aiTouched(p) ? ` <span class="ai">✦ ${esc(p.ai_system || 'AI')}</span>` : ''}<div class="who">${esc(p.resolved_by || '')}</div></span></li>`).join('')}${hl.length > 10 ? `<li><span class="d"></span><span class="small">and ${hl.length - 10} more — filter by status to see them</span></li>` : ''}</ol></div></div>`;
  attachTip($('#since'), $('#tip3'));
}


function attachTip(svg, tipEl, get) {
  svg.querySelectorAll('[data-tip]').forEach(el => {
    el.addEventListener('mousemove', e => {
      const r = tipEl.parentElement.getBoundingClientRect();
      tipEl.innerHTML = el.dataset.tip;
      tipEl.style.left = '0px'; tipEl.style.top = '0px';
      const w = tipEl.offsetWidth, h = tipEl.offsetHeight;
      const x = Math.min(Math.max(e.clientX - r.left, w / 2 + 4), Math.max(w / 2 + 4, r.width - w / 2 - 4));
      const yTop = e.clientY - r.top;
      const below = yTop - h - 12 < 0;
      tipEl.style.left = x + 'px';
      tipEl.style.top = (below ? yTop + h + 22 : yTop) + 'px';
      tipEl.style.opacity = 1;
    });
    el.addEventListener('mouseleave', () => tipEl.style.opacity = 0);
  });
}

function renderYears(rows) {
  const W = 640, H = 210, m = { l: 34, r: 10, t: 10, b: 26 };
  const withY = rows.filter(p => p.year_introduced != null && p.year_introduced >= 1600);
  const ancient = rows.filter(p => p.year_introduced != null && p.year_introduced < 1600).length;
  const noY = rows.length - withY.length - ancient;
  const dec = {}; withY.forEach(p => { const d = Math.floor(p.year_introduced / 10) * 10; (dec[d] ||= { conjecture: 0, question: 0, problem: 0, other: 0 })[kind(p)]++; });
  const d0 = 1600, d1 = 2020, n = (d1 - d0) / 10 + 1;
  const tot = d => TYPE_ORDER.reduce((s, t) => s + (dec[d]?.[t] || 0), 0);
  const maxV = Math.max(1, ...Array.from({ length: n }, (_, i) => tot(d0 + i * 10)));
  const iw = W - m.l - m.r, ih = H - m.t - m.b, bw = iw / n;
  const y = v => m.t + ih - ih * v / maxV;
  const step = maxV > 40 ? 20 : maxV > 16 ? 10 : maxV > 8 ? 4 : 2;
  let g = '';
  for (let v = 0; v <= maxV; v += step) g += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" stroke="var(--grid)"/><text x="${m.l - 6}" y="${y(v) + 3.5}" text-anchor="end">${v}</text>`;
  let bars = '';
  for (let i = 0; i < n; i++) {
    const d = d0 + i * 10; let acc = 0; const x = m.l + i * bw + 1;
    TYPE_ORDER.forEach(t => {
      const v = dec[d]?.[t] || 0; if (!v) return;
      const y1 = y(acc + v), y0 = y(acc); acc += v;
      const isTop = acc === tot(d);
      bars += `<rect x="${x}" y="${y1}" width="${Math.max(1, bw - 2)}" height="${Math.max(0, y0 - y1 - (isTop ? 0 : 1))}" fill="${TYPE_VAR[t]}" ${isTop ? 'rx="2"' : ''} data-tip="<b>${d}s</b> · ${TYPE_LABEL[t]}: ${v}<br>all kinds: ${tot(d)}"/>`;
    });
  }
  let ax = '';
  for (let d = 1600; d <= 2020; d += 50) ax += `<text x="${m.l + (d - d0) / 10 * bw + bw / 2}" y="${H - 8}" text-anchor="middle">${d}</text>`;
  const note = (ancient ? `${ancient} before 1600` : '') + (ancient && noY ? ' · ' : '') + (noY ? `${noY} undated` : '');
  if (!$('#ch-years')) return;
  $('#ch-years').querySelector('svg')?.remove(); $('#ch-years').querySelector('.legend')?.remove();
  $('#ch-years').insertAdjacentHTML('beforeend', `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Problems per decade">${g}${bars}<line x1="${m.l}" x2="${W - m.r}" y1="${y(0)}" y2="${y(0)}" stroke="var(--line)"/>${ax}${note ? `<text x="${m.l + 6}" y="${m.t + 8}">not shown: ${note}</text>` : ''}</svg><div class="legend">${TYPE_ORDER.map(t => `<span><i style="background:${TYPE_VAR[t]}"></i>${TYPE_LABEL[t]}</span>`).join('')}</div>`);
  attachTip($('#ch-years svg'), $('#tip1'));
}

function renderFields(rows) {
  const counts = {}; rows.forEach(p => counts[p.field] = (counts[p.field] || 0) + 1);
  const fs = FIELD_ORDER.filter(f => counts[f]).sort((a, b) => counts[b] - counts[a]);
  const W = 420, rh = 18, m = { l: 150, r: 34, t: 4, b: 4 }, H = m.t + m.b + fs.length * rh;
  const max = Math.max(1, ...fs.map(f => counts[f])), iw = W - m.l - m.r;
  let s = '';
  fs.forEach((f, i) => {
    const yy = m.t + i * rh, w = iw * counts[f] / max, on = state.fields.has(f);
    s += `<g style="cursor:pointer" data-f="${esc(f)}" data-tip="<b>${esc(f)}</b>: ${counts[f]}"><rect x="0" y="${yy}" width="${W}" height="${rh}" fill="transparent"/><text x="${m.l - 8}" y="${yy + rh / 2 + 3.5}" text-anchor="end" style="fill:${on ? 'var(--accent)' : 'var(--ink-2)'};font-family:'IBM Plex Sans',system-ui,sans-serif;font-size:11.5px">${esc(f.length > 24 ? f.slice(0, 23) + '…' : f)}</text><rect x="${m.l}" y="${yy + 3}" width="${Math.max(2, w)}" height="${rh - 6}" rx="2" fill="${on ? 'var(--accent)' : 'var(--c-conj)'}" opacity="${state.fields.size && !on ? .45 : 1}"/><text x="${m.l + w + 5}" y="${yy + rh / 2 + 3.5}">${counts[f]}</text></g>`;
  });
  $('#ch-fields').querySelector('svg')?.remove();
  $('#ch-fields').insertAdjacentHTML('beforeend', `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Problems per field">${s}</svg>`);
  const svg = $('#ch-fields svg'); attachTip(svg, $('#tip2'));
  svg.querySelectorAll('g[data-f]').forEach(el => el.onclick = () => { const f = el.dataset.f; state.fields.has(f) ? state.fields.delete(f) : state.fields.add(f); update(); });
}

// What stood at the problem's own title on 26 Jan 2024, when it differs from today's reading
function pageNote(p) {
  if (p.page_snapshot === 'article') return 'yes, and it already existed at the Jan 2024 snapshot';
  if (p.page_snapshot === 'alias') return `yes — in Jan 2024 the title redirected to ${esc(p.page_redirect_target || 'another title')}, an article on the same problem`;
  if (p.page_snapshot === 'broader') return `no — in Jan 2024 the title redirected into ${esc(p.page_redirect_target || 'another article')}`;
  if (p.page_snapshot === 'absent') return `no — the title was a red link in Jan 2024${p.page_created ? `; the article was created ${esc(p.page_created.slice(0, 10))}` : ''}`;
  if (p.page_snapshot === 'none') return 'no — the bullet links only to background topics';
  return '';
}

function card(p) {
  const k = kind(p), est = p.year_source && p.year_source.startsWith('mathematical');
  const tags = [];
  if (p.millennium_prize) tags.push('<span class="tag prize">Millennium Prize</span>');
  if (p.hilbert_problem) tags.push(`<span class="tag">Hilbert #${p.hilbert_problem}</span>`);
  if (p.smale_problem) tags.push(`<span class="tag">Smale #${p.smale_problem}</span>`);
  if (p.landau_problem) tags.push('<span class="tag">Landau</span>');
  if (p.subfield) tags.push(`<span class="tag">${esc(p.subfield)}</span>`);
  const stBadge = p.status !== 'open' ? `<span class="st ${p.status}">${STATUS_LABEL[p.status]}${dirLabel(p) ? ' · ' + dirLabel(p) : ''}${p.year_resolved ? ' ' + p.year_resolved : ''}</span>` : '';
  const aiBadge = aiTouched(p) ? `<span class="ai" title="${esc(AI_LABEL[p.ai_involvement])}">✦ ${esc(p.ai_system || 'AI')}</span>` : '';
  if (p.parent) tags.push(`<span class="tag">↳ ${esc(p.parent.slice(0, 30))}</span>`);
  const desc = p.description && p.description !== p.name ? p.description : p.statement;
  return `<article class="card${state.open.has(p.id) ? ' open' : ''}${p.status !== 'open' ? ' changed' : ''}" data-id="${p.id}" style="--tc:${TYPE_VAR[k]}" tabindex="0">
    <div class="top"><div class="name">${esc(p.name)}</div><div class="yr${est ? ' est' : ''}" title="${est ? 'estimated from the literature' : 'stated in the linked article'}">${fmtYear(p.year_introduced)}</div></div>
    ${stBadge || aiBadge ? `<div class="meta">${stBadge}${aiBadge}</div>` : ''}
    <div class="desc">${esc(desc)}</div>
    <div class="meta"><span style="color:${TYPE_VAR[k]};font-weight:600">${TYPE_LABEL[k]}</span>${tags.join('')}${p.wikilinks.length ? `<span>${p.wikilinks.length} link${p.wikilinks.length > 1 ? 's' : ''}</span>` : ''}</div>
    <div class="more">
      <div><span class="k">As listed</span>${esc(p.statement)}</div>
      ${p.named_after.length ? `<div style="margin-top:4px"><span class="k">Named after</span>${esc(p.named_after.join(', '))}</div>` : ''}
      ${p.year_introduced != null ? `<div style="margin-top:4px"><span class="k">Year</span>${fmtYear(p.year_introduced)} · ${esc(p.year_source)}${p.year_note ? ` · ${esc(p.year_note)}` : ''}</div>` : '<div style="margin-top:4px"><span class="k">Year</span>not determined</div>'}
      ${pageNote(p) ? `<div style="margin-top:4px"><span class="k">Dedicated article</span><span style="color:var(--ink-3)">${pageNote(p)}</span></div>` : ''}
      ${p.status !== 'open' ? `<div class="statusbox"><div class="hd"><span class="st ${p.status}">${STATUS_LABEL[p.status]}</span>${dirLabel(p) ? `<b>${dirLabel(p)}</b>` : ''}${p.year_resolved ? `<span class="mono" style="color:var(--ink-3)">${p.year_resolved}</span>` : ''}${aiTouched(p) ? `<span class="ai">✦ ${esc(AI_LABEL[p.ai_involvement])}${p.ai_system ? ' · ' + esc(p.ai_system) : ''}</span>` : ''}</div>${p.resolved_by ? `<div><span class="k">By</span>${esc(p.resolved_by)}</div>` : ''}${p.status_note ? `<span class="fold"><span class="fold-body"><span class="fold-inner">${esc(p.status_note)}<span class="llmtag">Summary is LLM generated</span></span></span></span>` : ''}${p.status_sources.length ? `<div class="src"><span class="k">Sources</span>${p.status_sources.map(u => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(new URL(u).hostname.replace(/^www\./, ''))}${/arxiv/.test(u) ? ' ' + esc((u.match(/(\d{4}\.\d{4,5})/) || [])[1] || '') : ''}</a>`).join('')}</div>` : ''}</div>` : ''}
      <div class="links">${p.wikipedia_url ? `<a href="${esc(p.wikipedia_url)}" target="_blank" rel="noopener">Wikipedia article ↗</a>` : ''}${p.wikilinks.map(t => `<a href="${wpUrl(t)}" target="_blank" rel="noopener">${esc(t)}</a>`).join('')}</div>
    </div></article>`;
}

function renderList(rows) {
  const el = $('#list');
  if (!rows.length) { el.innerHTML = '<div class="empty">Nothing matches these filters.</div>'; return; }
  if (state.view === 'table') {
    const cols = [['id', '#'], ['name', 'Problem'], ['field', 'Field'], ['type', 'Kind'], ['year_introduced', 'Year'], ['status', 'Status since 2024'], ['ai_involvement', 'AI'], ['named_after', 'Named after'], ['wikilinks', 'Links']];
    const r = rows.slice().sort((a, b) => {
      let va = a[state.sortCol], vb = b[state.sortCol];
      if (Array.isArray(va)) { va = va.length; vb = vb.length; }
      if (state.sortCol === 'status') { va = STATUS_ORDER.indexOf(va); vb = STATUS_ORDER.indexOf(vb); }
      if (state.sortCol === 'ai_involvement') { va = AI_ORDER.indexOf(va); vb = AI_ORDER.indexOf(vb); }
      if (va == null) return 1; if (vb == null) return -1;
      const c = typeof va === 'number' ? va - vb : String(va).localeCompare(String(vb));
      return state.sortAsc ? c : -c;
    });
    el.innerHTML = `<div class="tablewrap"><table><thead><tr>${cols.map(([k, l]) => `<th data-c="${k}" class="${state.sortCol === k ? 'sorted' + (state.sortAsc ? ' asc' : '') : ''}">${l}</th>`).join('')}</tr></thead><tbody>${r.map(p => `<tr><td class="num">${p.id}</td><td>${p.wikipedia_url ? `<a href="${esc(p.wikipedia_url)}" target="_blank" rel="noopener">${esc(p.name)}</a>` : esc(p.name)}<div class="small">${esc(p.description !== p.name ? p.description.slice(0, 160) : '')}</div></td><td>${esc(p.field)}${p.subfield ? `<div class="small">${esc(p.subfield)}</div>` : ''}</td><td><span style="color:${TYPE_VAR[kind(p)]};font-weight:600">${TYPE_LABEL[kind(p)]}</span></td><td class="num">${fmtYear(p.year_introduced)}${p.year_approx ? '~' : ''}</td><td>${p.status !== 'open' ? `<span class="st ${p.status}">${STATUS_LABEL[p.status]}</span><div class="small">${dirLabel(p)} ${p.year_resolved || ''} · ${esc((p.resolved_by || '').slice(0, 70))}</div>` : '<span class="small">open</span>'}</td><td>${aiTouched(p) ? `<span class="ai">✦ ${esc(AI_LABEL[p.ai_involvement])}</span><div class="small">${esc(p.ai_system || '')}</div>` : ''}</td><td>${esc(p.named_after.join(', '))}</td><td class="num">${p.wikilinks.length}</td></tr>`).join('')}</tbody></table></div>`;
    el.querySelectorAll('th').forEach(th => th.onclick = () => { const c = th.dataset.c; if (state.sortCol === c) state.sortAsc = !state.sortAsc; else { state.sortCol = c; state.sortAsc = true; } renderList(filtered()); });
    return;
  }
  const rs = sorted(rows);
  if (state.sort === 'page') {
    const groups = new Map(); rs.forEach(p => { if (!groups.has(p.field)) groups.set(p.field, []); groups.get(p.field).push(p); });
    el.innerHTML = [...groups].map(([f, ps]) => `<section class="group"><h2>${esc(f)} <span class="n">${ps.length}</span></h2><div class="cards">${ps.map(card).join('')}</div></section>`).join('');
  } else el.innerHTML = `<div class="cards">${rs.map(card).join('')}</div>`;
  if (!$('#tip-list')) el.insertAdjacentHTML('afterbegin', '<div class="tip" id="tip-list"></div>');
  el.style.position = 'relative';
  attachTip(el, $('#tip-list'));
  el.querySelectorAll('.card').forEach(c => {
    const toggle = e => { if (e.target.closest('a')) return; const id = +c.dataset.id; state.open.has(id) ? state.open.delete(id) : state.open.add(id); c.classList.toggle('open'); };
    c.onclick = toggle; c.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(e); } };
  });
}

function renderSolved() {
  const rows = SOLVED.filter(s => !state.fields.size || state.fields.has(s.field) || (s.field === 'Game theory' && state.fields.has('Games and puzzles')) || (s.field === 'Group theory' && state.fields.has('Algebra')) || (s.field === 'Ramsey theory' && state.fields.has('Combinatorics')));
  const byYear = rows.slice().sort((a, b) => (b.year_solved || 0) - (a.year_solved || 0));
  $('#solved').innerHTML = `<h3>Recorded as solved since 1995 <span class="mono" style="color:var(--ink-3);font-weight:400">${rows.length}</span></h3><div class="sub">The same page keeps a ledger of problems settled in the previous 30 years — a reminder that the list above is a snapshot, not a fixed canon.</div><div class="solvedlist">${byYear.map(s => `<div><span class="y">${s.year_solved || '—'}</span><span>${s.wikipedia_url ? `<a href="${esc(s.wikipedia_url)}" target="_blank" rel="noopener">${esc(s.name)}</a>` : esc(s.name)}${s.disproof ? ' (disproved)' : ''} <span style="color:var(--ink-3)">· ${esc(s.solved_by)}</span></span></div>`).join('')}</div>`;
}

function setTab(v) {
  state.tab = v;
  ['attribution', 'outcomes', 'explore', 'origins', 'about'].forEach(t => $('#view-' + t).hidden = t !== v);
  $('#tabs').querySelectorAll('button[data-v]').forEach(b => b.classList.toggle('on', b.dataset.v === v));
  update();
}

function update() {
  if (state.tab === 'attribution') { renderAttribution(); return; }
  if (state.tab === 'origins') { renderOrigins(); return; }
  if (state.tab === 'outcomes') { renderOutcomes(); return; }
  if (state.tab === 'about') return;
  const rows = filtered();
  renderRail(); renderSince(rows); renderFields(rows); renderList(rows); renderSolved();
  $('#count').textContent = rows.length;
}

$('#tabs').querySelectorAll('button[data-v]').forEach(b => b.onclick = () => setTab(b.dataset.v));
document.querySelectorAll('[data-goto]').forEach(el => el.onclick = e => { e.preventDefault(); setTab(el.dataset.goto); window.scrollTo({ top: 0, behavior: 'smooth' }); });
$('#a-mode').querySelectorAll('button').forEach(b => b.onclick = () => { state.aMode = b.dataset.m; $('#a-mode').querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b)); renderAttribution(); });
$('#c-mode').querySelectorAll('button').forEach(b => b.onclick = () => { state.cMode = b.dataset.m; $('#c-mode').querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b)); renderAttribution(); });
$('#q').addEventListener('input', e => { state.q = e.target.value; update(); });
$('#y0').addEventListener('input', e => { state.y0 = e.target.value === '' ? null : +e.target.value; update(); });
$('#y1').addEventListener('input', e => { state.y1 = e.target.value === '' ? null : +e.target.value; update(); });
$('#noyear').addEventListener('change', e => { state.noyear = e.target.checked; update(); });
function renderScope() {
  $('#scope').innerHTML = '<span class="lab">Corpus</span>'
    + `<select id="scope-sel" aria-label="Corpus">${SCOPES.map(([id, lab, fn]) =>
        `<option value="${id}"${state.scope === id ? ' selected' : ''}>${lab} · ${PROBLEMS.filter(fn).length}</option>`).join('')}</select>`;
  $('#scope-sel').onchange = e => applyScope(e.target.value);
}

function applyScope(id) {
  state.scope = id;
  DATA = PROBLEMS.filter(SCOPES.find(s => s[0] === id)[2]);
  $('#n-corpus').textContent = DATA.length;
  document.querySelectorAll('.n-corpus').forEach(el => el.textContent = DATA.length);
  renderScope(); renderRail(); update();
}
$('#sort').addEventListener('change', e => { state.sort = e.target.value; update(); });
$('#v-cards').onclick = () => { state.view = 'cards'; $('#v-cards').classList.add('on'); $('#v-table').classList.remove('on'); update(); };
$('#v-table').onclick = () => { state.view = 'table'; $('#v-table').classList.add('on'); $('#v-cards').classList.remove('on'); update(); };
$('#reset').onclick = () => { Object.assign(state, { q: '', fields: new Set(), y0: null, y1: null, noyear: true, lists: new Set(), status: new Set(), ai: new Set(), models: new Set() }); $('#q').value = ''; $('#y0').value = ''; $('#y1').value = ''; $('#noyear').checked = true; update(); };
// The About tab's snapshot paragraph describes the frozen list, so it is bound to PROBLEMS, not to
// DATA — unlike .n-corpus it must not follow the corpus control.
document.querySelectorAll('.n-snapshot').forEach(el => el.textContent = PROBLEMS.length);
// Prose links that cross to another tab: the tabs are buttons, so the href alone would do nothing.
document.querySelectorAll('[data-goto]').forEach(a => a.onclick = e => { e.preventDefault(); setTab(a.dataset.goto); });
applyScope(state.scope);
setTab('attribution');
