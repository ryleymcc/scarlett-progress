/* Combined Xbox API symbols from sampled public source files; zero dependencies. */
(() => {
'use strict';
let snapshot = null;
let visible = 50;
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = n => Number.isFinite(n) ? n.toLocaleString() : '—';
const sourceUrl = s => {
  try { const u = new URL(s); return u.protocol === 'https:' && u.hostname === 'github.com' ? u.href : '#'; }
  catch { return '#'; }
};

async function renderApiGrid(data) {
  let matrix = data.api_matrix;
  if (!matrix) {
    try {
      const feed = data.api_matrix_feed || 'api_matrix.json';
      const res = await fetch('./' + feed, {cache: 'no-store'});
      if (!res.ok) throw new Error('HTTP ' + res.status);
      matrix = await res.json();
    } catch (error) {
      $('apiGridUpdated').textContent = 'API matrix not published yet';
    }
  }
  snapshot = {...data, api_matrix: matrix};
  const ps = data.projects || [];
  if (!matrix || !Array.isArray(matrix.rows)) {
    $('apiGridStats').innerHTML = '<div class="api-stat"><b>Pending</b><small>First automated API source scan</small></div>';
    $('apiGridUpdated').textContent = 'Waiting for sync';
    $('apiMatrixHead').innerHTML = '<tr><th scope="col">API name</th></tr>';
    $('apiMatrixBody').innerHTML = '<tr><td>Run Sync Xbox Series projects to collect the unified API index.</td></tr>';
    $('apiMatrixCount').textContent = 'Source data not yet available';
    $('apiMatrixMore').hidden = true;
    return;
  }
  const rows = matrix.rows;
  const multi = rows.filter(row => row.project_count > 1).length;
  const definitions = rows.filter(row => row.candidate_count > 0).length;
  $('apiGridStats').innerHTML = [
    [matrix.total_symbols, 'API names detected across repositories'],
    [definitions, 'Names with possible definitions'],
    [multi, 'Names found in 2+ repositories'],
    [matrix.repositories_scanned + ' / ' + ps.length, 'Repositories with source scans']
  ].map(([v, label]) => `<div class="api-stat"><b>${typeof v==='number'?number(v):esc(v)}</b><small>${esc(label)}</small></div>`).join('');
  $('apiGridUpdated').textContent = data.generated_at ? 'Indexed ' + new Date(data.generated_at).toLocaleString() : 'No scan timestamp';

  const groupSel = $('apiGridGroup');
  const prior = groupSel.value;
  const groups = [...new Set(rows.map(r=>r.group))].sort();
  groupSel.innerHTML = '<option value="all">All subsystems</option>' +
    groups.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join('');
  groupSel.value = groups.includes(prior) ? prior : 'all';

  $('apiMatrixHead').innerHTML = '<tr><th scope="col" class="api-name-head">Function / symbol</th>' +
    ps.map(p => {
      const scan = p.api_scan || {};
      const scanned = scan.status === 'ok' || scan.status === 'partial';
      const label = scanned ? (scan.files_scanned ?? 0) + ' files' : 'Unavailable';
      return `<th scope="col" title="${esc(p.repo)}"><span class="api-col-name">${esc(p.name)}</span><span class="api-col-scanned">${esc(label)}</span></th>`;
    }).join('') + '</tr>';

  if (!$('apiGridSearch').dataset.bound) {
    ['apiGridSearch','apiGridGroup','apiGridFilter','apiGridSort'].forEach(id => {
      $(id).addEventListener('input', () => { visible = 50; paint(); });
    });
    $('apiMatrixMore').addEventListener('click', () => { visible += 50; paint(); });
    $('apiGridSearch').dataset.bound = '1';
  }
  visible = 50;
  paint();
}

function paint() {
  if (!snapshot?.api_matrix) return;
  const rows = snapshot.api_matrix.rows || [];
  const ps = snapshot.projects || [];
  const q = $('apiGridSearch').value.trim().toLowerCase();
  const group = $('apiGridGroup').value;
  const choice = $('apiGridFilter').value;
  const sort = $('apiGridSort').value;
  const filtered = rows.filter(row => {
    if (group !== 'all' && row.group !== group) return false;
    if (q && !(row.symbol + ' ' + row.group).toLowerCase().includes(q)) return false;
    if (choice === 'shared' && row.project_count < 2) return false;
    if (choice === 'definitions' && !row.candidate_count) return false;
    if (choice === 'stubs' && !row.stub_count) return false;
    return true;
  });
  filtered.sort((a,b) => {
    if (sort === 'name') return a.symbol.localeCompare(b.symbol);
    if (sort === 'definitions') return b.candidate_count - a.candidate_count ||
      b.project_count - a.project_count || a.symbol.localeCompare(b.symbol);
    return b.project_count - a.project_count || b.candidate_count - a.candidate_count ||
      a.symbol.localeCompare(b.symbol);
  });
  const selected = filtered.slice(0, visible);
  const rowHtml = selected.map(row => {
    const sources = row.sources || {};
    return `<tr><th scope="row">
      <span class="api-symbol">${esc(row.symbol)}</span>
      <span class="api-subgroup">${esc(row.group)} · ${number(row.project_count)} repos</span>
    </th>${ps.map(p => {
      const cell = sources[p.repo];
      if (!cell) {
        const unavailable = !['ok','partial'].includes(p.api_scan?.status);
        return `<td><span class="api-cell na" title="${unavailable ? 'Source scan unavailable' : 'Not detected in limited source sample; NOT evidence of absence'}">${unavailable?'?':'·'}</span></td>`;
      }
      const status = cell.status;
      const kind = status==='definition_candidate' ? 'def' : status==='stub_candidate' ? 'stub' : 'ref';
      const label = kind==='def' ? 'Def' : kind==='stub' ? 'Stub?' : 'Ref';
      const meaning = kind==='def' ? 'Candidate function body, NOT runtime-tested' :
        kind==='stub' ? 'Possible unimplemented body' : 'Mention or declaration only';
      const tooltip = `${meaning} · ${cell.file}:${cell.line}`;
      return `<td><a class="api-cell ${kind}" href="${sourceUrl(cell.source)}" target="_blank" rel="noopener noreferrer" title="${esc(tooltip)}" aria-label="${esc(p.name + ': ' + row.symbol + ', ' + meaning)}">${label}</a></td>`;
    }).join('')}</tr>`;
  }).join('');
  $('apiMatrixBody').innerHTML = rowHtml || `<tr><td colspan="${ps.length+1}" class="pending">No symbols match these filters.</td></tr>`;
  const total = snapshot.api_matrix.total_symbols ?? rows.length;
  const cap = total > rows.length ? ` · showing the top ${number(rows.length)} discovered names` : '';
  $('apiMatrixCount').textContent = `Showing ${number(selected.length)} of ${number(filtered.length)} matching symbols${cap}`;
  $('apiMatrixMore').hidden = filtered.length <= visible;
}
window.renderApiGrid = renderApiGrid;
})();
