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
  const catalog = (data.catalog || {}).features || [];
  const overlap = data.overlap || [];
  const available = ps.filter(p => p.coverage?.inventory?.status === 'ok');
  const matched = overlap.filter(f => f.project_count > 0);
  const shared = overlap.filter(f => f.project_count >= 2);
  const summary = document.getElementById('coverageSummary');
  summary.innerHTML = `<div class="coverage-stat"><b>${num(available.length)} / ${num(ps.length)}</b><span>Source trees scanned</span></div><div class="coverage-stat"><b>${num(matched.length)} / ${num(catalog.length)}</b><span>Research areas with code-path signals</span></div><div class="coverage-stat"><b>${num(shared.length)}</b><span>Areas investigated by 2+ projects</span></div><div class="coverage-stat"><b>${num(ps.reduce((sum,p) => sum+(p.coverage?.verified_implemented||0), 0))}</b><span>Independently verified project-capabilities</span></div>`;
  document.getElementById('coverageCaveat').textContent = `A catalog of ${catalog.length} research areas is only a comparison reference, not a list of every Xbox API. File matches mean potential work in an area, not implemented or working code. README checklist totals describe upstream tasks, not console compatibility.`;
  const comparison = document.getElementById('coverageComparison');
  comparison.innerHTML = ps.map(p => {
    const cov = p.coverage || {}, inv = cov.inventory || {}, checklist = cov.checklist;
    const evidenceCount = Object.keys(cov.reviewed || {}).length;
    const detected = inv.status === 'ok' ? `${num((inv.features || []).length)} / ${num(catalog.length)}${inv.truncated?'*':''}` : 'Unavailable';
    const metrics = [...(cov.reported_metrics || []), ...(checklist ? [{...checklist,label:'README task boxes'}] : [])];
    const todo = metrics.length ? metrics.map(m => {
      const estimate = cov.metric_forecasts?.[m.id]?.status === 'experimental'
        ? `Experimental scope ETA: ${e(cov.metric_forecasts[m.id].target_date)}`
        : cov.metric_forecasts?.[m.id]?.status === 'scope_complete'
          ? 'Declared scope completed, unverified' : 'Scope ETA unavailable';
      return `<div class="published-metric"><a href="${safeGitHub(m.source)}" target="_blank" rel="noopener noreferrer">${num(m.implemented)} / ${num(m.total)}</a><small>${e(m.label)} (self-reported)</small><small>${estimate}</small></div>`;
    }).join('') : 'Not published';
    const verified = evidenceCount ? `${num(cov.verified_implemented)} / ${num(catalog.length)} <small>(${num(evidenceCount)} reviewed)</small>` : 'Unreviewed';
    const eta = cov.forecast?.status === 'experimental' ? `${e(cov.forecast.target_date)} †` : 'Not estimable';
    return `<tr><th scope="row"><a href="https://github.com/${e(p.repo)}" target="_blank" rel="noopener noreferrer">${e(p.name)}</a></th><td>${todo}</td><td>${detected}</td><td>${verified}</td><td>${eta}</td></tr>`;
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
      const manual = ps.filter(p => filter==='all'||p.repo===filter).flatMap(p => {
        const r = p.coverage?.reviewed?.[f.id];
        return r ? [{...r,repo:p.repo,name:p.name}] : [];
      });
      return {f,people,manual};
    });
    target.innerHTML = items.map(({f,people,manual}) => {
      const label = people.length === 0 ? 'No matching source path' : `${people.length} repo${people.length === 1?'':'s'} with matching files`;
      const examples = people.map(p => `<a class="coverage-chip" target="_blank" rel="noopener noreferrer" href="${safeGitHub(p.examples?.[0])}" title="${e(p.matching_files)} matching source files in ${e(p.name)}">${e(p.name)} <small>${num(p.matching_files)}</small></a>`).join('');
      const checks = manual.map(m=>`<a class="review-chip ${m.evidence === 'independently_verified'?'independent':''}" href="${safeGitHub(m.source)}" target="_blank" rel="noopener noreferrer">${e(m.name)}: ${e(m.state.replaceAll('_',' '))} (${e(m.evidence === 'independently_verified'?'independent':'claimed')})</a>`).join('');
      return `<div class="cap-row"><div class="cap-main"><span class="cap-group">${e(f.group)}</span><h3>${e(f.title)}</h3><p>${e(f.description)}</p><small>${label}</small></div><div class="cap-links">${examples || '<span class="cap-none">Unobserved, not necessarily absent</span>'}${checks}</div></div>`;
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
  const n = ps.filter(p => p.coverage?.forecast?.status === 'experimental').length;
  document.getElementById('forecastExplanation').textContent = n ? `${n} experimental catalog forecasts qualify. These only extrapolate independently verified research-area milestones, never game playability.` : 'No defensible forecast yet. The catalog ETA requires at least four daily snapshots over 28 days, two separate independent verification gains, a stable catalog, and at least 25% of the catalog verified. Separately, an upstream metric may earn its own experimental scope ETA after 28 days of comparable progress. There is no reliable overall ETA for full Xbox Series emulation or GTA VI compatibility.';
}
window.renderCoverage = renderCoverage;
})();
