/* Scarlett Progress, zero-dependency client-side dashboard. */
'use strict';
let dataset = {generated_at: null, projects: []};
const $ = id => document.getElementById(id);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const text = x => x === null || x === undefined ? '—' : Number(x).toLocaleString();
const date = v => v ? new Date(v).toLocaleDateString(undefined,{year:'numeric',month:'short',day:'numeric'}) : 'Not available';
const ago = v => {
  if (!v) return 'No commit data';
  const days = Math.max(0,Math.floor((Date.now()-new Date(v).getTime())/86400000));
  if (days < 1) return 'Today';
  if (days === 1) return '1 day ago';
  return `${days} days ago`;
};
const safeUrl = value => {
  try { const u = new URL(value);return u.protocol === 'https:' ? u.href : '#'; }
  catch { return '#'; }
};
const githubUrl = value => {
  try { const u = new URL(value);return u.hostname === 'github.com' && u.protocol === 'https:' ? u.href : '#'; }
  catch { return '#'; }
};
const recent = v => !!v && Date.now()-new Date(v).getTime() < 7*86400000;
const rank = p => ({'GTA VI direct':0,'Core runtime':1,'Supporting technology':2})[p.priority] ?? 9;

function projectCard(p) {
  const isDirect=p.priority==='GTA VI direct';
  const kindClass = isDirect?'direct':p.priority==='Supporting technology'?'support':'';
  const stale = !!p.scan_error;
  const last = p.last_commit_at;
  const tag = isDirect?'GTA VI DIRECT':p.priority==='Supporting technology'?'SUPPORTING':'SERIES RUNTIME';
  const counts = p.commits_30d_capped ? `${text(p.commits_30d)}+` : text(p.commits_30d);
  const branch = p.branch?` · branch: ${esc(p.branch)}`:'';
  return `<article class="project-card">
    <div class="card-head"><span class="tag ${kindClass}">${tag}</span><span class="status ${stale?'stale':recent(last)?'recent':''}">${stale?'API stale':recent(last)?'Active this week':'Tracking'}</span></div>
    <a href="${githubUrl(p.url||'https://github.com/'+p.repo)}" target="_blank" rel="noopener noreferrer" class="card-title">${esc(p.name)} ↗</a>
    <div class="card-repo">${esc(p.repo)}${branch}</div>
    <p class="card-desc">${esc(p.description)}</p>
    <div class="card-stats"><div><strong>${counts}</strong><small>Commits /30d</small></div><div><strong>${text(p.open_prs)}</strong><small>Open PRs</small></div><div><strong>${text(p.stars)}</strong><small>Stars</small></div></div>
    <div class="card-footer"><span class="last-commit">${last?'Last commit · '+esc(ago(last)):'Awaiting first sync'}</span><a href="${githubUrl('https://github.com/'+p.repo)}" class="visit" target="_blank" rel="noopener noreferrer">VIEW SOURCE ↗</a></div>
  </article>`;
}

function renderGrid() {
  const query=$('query').value.trim().toLowerCase(), kind=$('kind').value, platform=$('platform').value, sort=$('sort').value;
  let ps=dataset.projects.filter(p => {
    const haystack=[p.name,p.repo,p.description,p.kind,p.description_upstream,p.scope].join(' ').toLowerCase();
    return (!query||haystack.includes(query)) && (kind==='all'||p.priority===kind) && (platform==='all'||(p.platforms||[]).includes(platform));
  });
  ps.sort((a,b)=>{
    if(sort==='name')return a.name.localeCompare(b.name);
    if(sort==='commits')return (b.commits_30d??-1)-(a.commits_30d??-1)||a.name.localeCompare(b.name);
    if(sort==='recent')return (b.last_commit_at||'').localeCompare(a.last_commit_at||'');
    if(sort==='stars')return (b.stars??-1)-(a.stars??-1);
    return rank(a)-rank(b)||a.name.localeCompare(b.name);
  });
  $('projectGrid').innerHTML=ps.map(projectCard).join('');
  $('shownCount').textContent=`${ps.length} of ${dataset.projects.length} projects`;
  $('empty').hidden=ps.length>0;
}

function renderFeed() {
  const items=dataset.projects.flatMap(p=>(p.recent_commits||[]).map(c=>({...c,project:p.name,repo:p.repo}))).sort((a,b)=>(b.date||'').localeCompare(a.date||'')).slice(0,16);
  $('feedCount').textContent=items.length?`${items.length} recent commits`:'No recent commit data';
  $('commitFeed').innerHTML=items.length?items.map(c=>`<div class="commit-entry"><div class="commit-node"></div><div><strong>${esc(c.message)}</strong><span>${esc(c.project)} · ${esc(c.sha?.slice(0,7)||'')}</span></div><div class="commit-time">${esc(ago(c.date))} · <a href="${githubUrl(c.url)}" target="_blank" rel="noopener noreferrer">Commit ↗</a></div></div>`).join(''):'<div class="pending">No commit feed yet. Run the Sync workflow in GitHub Actions.</div>';
}

function renderMetrics() {
  const ps=dataset.projects;
  $('metricRepos').textContent=ps.length;
  const scanned=ps.filter(p=>p.commits_30d!==undefined&&p.commits_30d!==null);
  $('metricCommits').textContent=scanned.length?text(scanned.reduce((n,p)=>n+(p.commits_30d||0),0)):'—';
  $('metricActive').textContent=scanned.length?text(ps.filter(p=>recent(p.last_commit_at)).length):'—';
  const measures=ps.reduce((n,p)=>n+(p.coverage?.reported_metrics?.length||0)+(p.coverage?.checklist?1:0),0);
  $('metricReported').textContent=dataset.generated_at?text(measures):'—';
  if (dataset.generated_at) {
    $('syncTime').textContent=date(dataset.generated_at);
    $('dataInfo').textContent=`Snapshot: ${new Date(dataset.generated_at).toLocaleString()}`;
  }
}

async function load() {
  try {
    const res=await fetch('./data.json',{cache:'no-store'});
    if (!res.ok) throw Error(`HTTP ${res.status}`);
    dataset=await res.json();
    if (!Array.isArray(dataset.projects))throw Error('Malformed feed');
    renderMetrics();renderGrid();renderFeed();
    if (typeof window.renderCoverage === 'function') window.renderCoverage(dataset);
  } catch(e) {
    $('dataInfo').textContent='Could not load feed: '+e.message;
    $('projectGrid').innerHTML='<div class="pending">Feed unavailable. For local testing run <code>python -m http.server 8000 -d docs</code>, then visit <code>http://localhost:8000</code>.</div>';
  }
}
['query','kind','platform','sort'].forEach(id=>$(id).addEventListener('input',renderGrid));
load();
