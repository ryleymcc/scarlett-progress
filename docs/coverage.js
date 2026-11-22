/* Supplemental Scarlett implementation and overlap dashboard. No libraries. */
(() => {
'use strict';
const e = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeGitHub = value => {
  try { const u = new URL(value); return u.protocol === 'https:' && (u.hostname === 'github.com' || u.hostname === 'raw.githubusercontent.com') ? u.href : '#'; }
  catch { return '#'; }
};
const num = value => Number.isFinite(value) ? value.toLocaleString() : '—';
function renderCoverage(data) {
  const target = document.getElementById('coverageMatrix');
  if (!target) return;
  const ps = data.projects || [];
  if (!data.catalog || !Array.isArray(data.catalog.features)) {
    const note = 'Implementation data has not been generated yet. The next GitHub Actions sync will scan the upstream projects and populate these panels.';
    document.getElementById('coverageSummary').innerHTML =
      '<div class="coverage-stat"><b>Pending sync</b><span>Implementation inventory</span></div>';
    document.getElementById('coverageCaveat').textContent = note;
    document.getElementById('coverageComparison').innerHTML =
      '<tr><td colspan="4">Waiting for the first implementation-aware data refresh.</td></tr>';
    target.innerHTML = '<div class="pending">Capability map will appear after the sync.</div>';
    document.getElementById('overlapPairs').innerHTML =
      '<div class="pending">Research overlaps will appear after the sync.</div>';
    document.getElementById('forecastExplanation').textContent =
      'Estimates require historical measurements from repeated automatic syncs.';
    return;
  }
  const catalog = data.catalog.features;
  const overlap = data.overlap || [];
  const available = ps.filter(p => p.coverage?.inventory?.status === 'ok');
  const matched = overlap.filter(f => f.project_count > 0);
  const shared = overlap.filter(f => f.project_count >= 2);
  const summary = document.getElementById('coverageSummary');
  summary.innerHTML = `<div class="coverage-stat"><b>${num(available.length)} / ${num(ps.length)}</b><span>Source trees scanned</span></div><div class="coverage-stat"><b>${num(matched.length)} / ${num(catalog.length)}</b><span>Research areas with code-path signals</span></div><div class="coverage-stat"><b>${num(shared.length)}</b><span>Areas investigated by 2+ projects</span></div><div class="coverage-stat"><b>${num(ps.reduce((sum,p) => sum+(p.coverage?.reported_metrics?.length||0)+(p.coverage?.checklist?1:0), 0))}</b><span>Upstream progress measures tracked</span></div>`;
  document.getElementById('coverageCaveat').textContent = `A catalog of ${catalog.length} research areas is only a comparison reference, not a list of every Xbox API. File matches mean potential work in an area, not implemented or working code. README checklist totals describe upstream tasks, not console compatibility.`;
  const comparison = document.getElementById('coverageComparison');
  comparison.innerHTML = ps.map(p => {
    const cov = p.coverage || {}, inv = cov.inventory || {}, checklist = cov.checklist;
    const detected = inv.status === 'ok' ? `${num((inv.features || []).length)} / ${num(catalog.length)}${inv.truncated?'*':''}` : 'Unavailable';
    const metrics = [...(cov.reported_metrics || []), ...(checklist ? [{...checklist,id:'readme_tasks',label:'README task boxes'}] : [])];
    const todo = metrics.length ? metrics.map(m => {
      const estimate = cov.metric_forecasts?.[m.id]?.status === 'experimental'
        ? `Experimental scope ETA: ${e(cov.metric_forecasts[m.id].target_date)}`
        : cov.metric_forecasts?.[m.id]?.status === 'scope_complete'
          ? 'Declared scope completed, unverified' : 'Scope ETA unavailable';
      return `<div class="published-metric"><a href="${safeGitHub(m.source)}" target="_blank" rel="noopener noreferrer">${num(m.implemented)} / ${num(m.total)}</a><small>${e(m.label)} (self-reported)</small><small>${estimate}</small></div>`;
    }).join('') : 'Not published';
    const dated=metrics.filter(m=>cov.metric_forecasts?.[m.id]?.status==='experimental');
    const forecast=dated.length ? dated.map(m=>`${e(m.label)}: ${e(cov.metric_forecasts[m.id].target_date)}`).join('<br>') : 'Not estimable';
    return `<tr><th scope="row"><a href="https://github.com/${e(p.repo)}" target="_blank" rel="noopener noreferrer">${e(p.name)}</a></th><td>${todo}</td><td>${detected}</td><td>${forecast}</td></tr>`;
  }).join('');
  const sel = document.getElementById('coverageProject');
  const prior = sel.value;
  sel.innerHTML = `<option value="all">All repositories</option>${ps.map(p=>`<option value="${e(p.repo)}">${e(p.name)}</option>`).join('')}`;
  if ([...sel.options].some(x => x.value === prior)) sel.value = prior;
  const paint = () => {
    const filter = sel.value;
    const items = catalog.map(f => {
      const ov = overlap.find(x => x.id === f.id) || {projects:[],project_count:0};
      const people = (ov.projects || []).filter(x=>filter==='all'||x.repo===filter);
      return {f,people};
    });
    target.innerHTML = items.map(({f,people}) => {
      const label = people.length === 0 ? 'No matching source path' : `${people.length} repo${people.length === 1?'':'s'} with matching files`;
      const examples = people.map(p => `<a class="coverage-chip" target="_blank" rel="noopener noreferrer" href="${safeGitHub(p.examples?.[0])}" title="${e(p.matching_files)} matching source files in ${e(p.name)}">${e(p.name)} <small>${num(p.matching_files)}</small></a>`).join('');
      return `<div class="cap-row"><div class="cap-main"><span class="cap-group">${e(f.group)}</span><h3>${e(f.title)}</h3><p>${e(f.description)}</p><small>${label}</small></div><div class="cap-links">${examples || '<span class="cap-none">Unobserved, not necessarily absent</span>'}</div></div>`;
    }).join('');
  };
  sel.onchange = paint;
  paint();
  const pairs = [];
  for (let i=0;i<ps.length;i++) for(let j=i+1;j<ps.length;j++) {
    const a = new Set(ps[i].coverage?.inventory?.features?.map(x=>x.id) || []);
    const b = new Set(ps[j].coverage?.inventory?.features?.map(x=>x.id) || []);
    if (ps[i].coverage?.inventory?.status !== 'ok' || ps[j].coverage?.inventory?.status !== 'ok') continue;
    const intersection = [...a].filter(x => b.has(x));
    if (intersection.length) pairs.push({a:ps[i],b:ps[j],shared:intersection.length,ids:intersection});
  }
  pairs.sort((a,b) => b.shared-a.shared || a.a.name.localeCompare(b.a.name));
  document.getElementById('overlapPairs').innerHTML = pairs.slice(0,12).map(p => `<div class="overlap-pair"><strong>${e(p.a.name)} <span>↔</span> ${e(p.b.name)}</strong><b>${p.shared} shared areas</b><small>${e(p.ids.map(id => catalog.find(c=>c.id===id)?.title||id).join(' · '))}</small></div>`).join('') || '<div class="pending">Overlap will appear after the next successful source-tree scan.</div>';
  const estimates=ps.flatMap(p=>Object.values(p.coverage?.metric_forecasts||{})).filter(f=>f.status==='experimental');
  document.getElementById('forecastExplanation').textContent = estimates.length ? `${estimates.length} experimental scope forecast(s) based on upstream-published progress. Each date applies only to its named fixed denominator; it is not a full-emulator or GTA VI playability ETA.` : 'No scope forecast yet. Automatic estimates require at least four daily observations over 28 days with a stable total, two separate increases and no reported regressions. These figures describe upstream-published task/function/shader scopes, not the date when Xbox Series emulation or GTA VI will be playable.';
}
window.renderCoverage = renderCoverage;
})();
