'use strict';
const $ = selector => document.querySelector(selector);
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// Escape source text first; generate only controlled presentation elements.
function renderInline(value) {
  return escapeHTML(value)
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/__([^_]+)__/g, '<strong>$1</strong>')
    .replace(/\*([^\s*](?:[^*]*?[^\s*])?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\[([^\]]+)\]\([^\s)]+\)/g, '$1')
    .replace(/\*/g, '×');
}
function renderContext(source) {
  const lines = String(source ?? '').split(/\r?\n/);
  let html = '', list = null, quote = false;
  const closeList = () => { if (list) { html += `</${list}>`; list = null; } };
  const closeQuote = () => { if (quote) { html += '</blockquote>'; quote = false; } };
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (/^\|.+\|$/.test(line) && /^\|?[\s:|-]+\|$/.test((lines[i+1] || '').trim())) {
      closeList(); closeQuote();
      const cells = row => row.trim().replace(/^\||\|$/g, '').split('|').map(v => v.trim());
      html += '<div class="table-scroll"><table><thead><tr>' + cells(line).map(v=>`<th scope="col">${renderInline(fieldLabel(v).replace(/Turn(\d)/g, 'Turn $1').replace(/avg /gi, 'average '))}</th>`).join('') + '</tr></thead><tbody>';
      i++;
      while (i+1 < lines.length && /^\|.+\|$/.test(lines[i+1].trim())) {
        html += '<tr>' + cells(lines[++i]).map(v=>`<td>${renderInline(v === '-' ? 'Not recorded' : v)}</td>`).join('') + '</tr>';
      }
      html += '</tbody></table></div>'; continue;
    }
    if (/^```/.test(line)) { closeList(); closeQuote(); continue; }
    if (/^[-*_=]{3,}$/.test(line)) { closeList(); closeQuote(); html += '<hr>'; continue; }
    const bullet = line.match(/^[-*+]\s+(.+)/);
    const ordered = line.match(/^(\d+)[.)]\s+(.+)/);
    const type = bullet ? 'ul' : ordered ? 'ol' : null;
    if (list !== type) closeList();
    if (!line) { closeQuote(); continue; }
    if (type) {
      closeQuote();
      if (!list) { list=type; html += ordered ? `<ol start="${Number(ordered[1])}">` : '<ul>'; }
      html += `<li>${renderInline(bullet ? bullet[1] : ordered[2])}</li>`;
    } else if (/^>\s?/.test(line)) {
      if (!quote) { quote=true;html+='<blockquote>'; }
      html += `<p>${renderInline(line.replace(/^>\s?/, ''))}</p>`;
    } else {
      closeQuote();
      const heading = line.match(/^#{1,6}\s+(.+)/);
      html += heading ? `<h3>${renderInline(heading[1])}</h3>` : `<p>${renderInline(line)}</p>`;
    }
  }
  closeList(); closeQuote(); return html;
}
function fieldLabel(key) {
  const label = String(key).replace(/_/g, ' ').replace(/([a-z])([A-Z])/g, '$1 $2').replace(/^avg /i, 'Average ');
  return label.charAt(0).toUpperCase() + label.slice(1);
}
function renderValue(value, depth = 0) {
  if (value === null || value === undefined) return '<span class="muted">Not recorded</span>';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') return escapeHTML(Number.isInteger(value) ? value : Number(value.toFixed(6)));
  if (typeof value === 'string') {
    const text = value.trim();
    if (/^[{[]/.test(text)) {
      try { return renderValue(JSON.parse(text), depth+1); } catch (_) { /* Keep recorded text. */ }
    }
    return renderContext(/^[A-Z][A-Z_]+$/.test(text) ? fieldLabel(text.toLowerCase()) : value);
  }
  if (Array.isArray(value)) {
    if (!value.length) return '<span class="muted">None</span>';
    return value.map((item, i) => `<details class="record-group"><summary>Entry ${i+1}</summary><div>${renderValue(item, depth+1)}</div></details>`).join('');
  }
  const pairs = Object.entries(value);
  if (!pairs.length) return '<span class="muted">None</span>';
  return '<dl class="record-fields">' + pairs.map(([key, item]) => {
    const definition = typeof item === 'number' ? metricDefinitions[key] : null;
    const content = definition ? `${(item * (definition[2] === '%' ? 100 : 1)).toFixed(definition[1])}${definition[2]}` : renderValue(item, depth+1);
    const nested = item && typeof item === 'object' && depth > 0;
    return `<div class="record-field"><dt>${escapeHTML(fieldLabel(key))}</dt><dd>${nested ? `<details class="record-group"><summary>View details</summary>${content}</details>` : content}</dd></div>`;
  }).join('') + '</dl>';
}
function renderEvaluationMarkdown(source) {
  const cards=[];
  const body=source.replace(/^# Evaluation Summary.*\n/, '').split('\n').filter(line=>{
    const match=line.match(/^- ([^:]+): ([0-9.]+)$/);
    if(!match) return true;
    const score=/score/i.test(match[1]);
    const value=Number(match[2]);
    cards.push(`<div class="metric-card"><div class="metric-value" title="${escapeHTML(match[2])}">${score ? value.toFixed(3) : value}${score ? '<span class="metric-unit"> / 5</span>' : ''}</div><div class="metric-label">${escapeHTML(match[1].replace(/Turn(\d)/g, 'Turn $1'))}</div></div>`);
    return false;
  }).join('\n');
  const tableStart=body.indexOf('\n|');
  const guide=tableStart>=0 ? body.slice(0,tableStart) : body;
  const table=tableStart>=0 ? body.slice(tableStart) : '';
  return '<section><h3>Run summary</h3><div class="result-metrics">'+cards.join('')+'</div></section>'
    +'<details class="record-section"><summary>Scoring guide</summary><div>'+renderContext(guide)+'</div></details>'
    +(table ? '<section><h3>Individual case results</h3>'+renderContext(table)+'</section>' : '');
}
function renderTool(text) {
  try { return renderValue(JSON.parse(text)); } catch (_) { return renderContext(text); }
}
const detailDialog = $('#detailDialog');
let detailRequest = 0;
$('#closeDetails').addEventListener('click', () => detailDialog.close());
detailDialog.addEventListener('click', event => { if(event.target === detailDialog) {
  const r=detailDialog.getBoundingClientRect();
  if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom) detailDialog.close();
}});
detailDialog.addEventListener('close', () => { detailRequest++; document.body.classList.remove('dialog-open'); });
async function openSource(path, type) {
  const request = ++detailRequest;
  $('#detailTitle').textContent = type === 'metrics' ? 'Evaluation results' : 'Conversation details';
  $('#detailSubtitle').textContent = `${registry.models.find(m=>m.id===modelId).name} · ${registry.tracks.find(t=>t.id===trackId).name}`;
  $('#detailBody').innerHTML = '<p role="status">Loading details…</p>';
  document.body.classList.add('dialog-open');
  detailDialog.showModal();
  detailDialog.scrollTop = 0;
  try {
    const response=await fetch(path);
    if(!response.ok) throw new Error('Unable to load source');
    const markdown=path.endsWith('.md');
    const data=markdown ? await response.text() : await response.json();
    if(request !== detailRequest) return;
    if(markdown) {
      // The heading identifies the selected run above, so hide the technical filename title.
      $('#detailBody').innerHTML=renderEvaluationMarkdown(data);
    } else {
      const primary=type==='metrics' ? data.overall : null;
      let html = primary ? '<section><h3>Run summary</h3>' + renderValue(primary) + '</section>' : '';
      const fields=Object.entries(data).filter(([key])=>key!=='overall');
      const overview=Object.fromEntries(fields.filter(([,v])=>v===null || typeof v!=='object').filter(([k])=>!['long_description','expected_answer','expected_answer_turn2','output','output_turn1','output_turn2','user_prompt','user_prompt_turn2'].includes(k)));
      html += '<section><h3>Record information</h3>'+renderValue(overview)+'</section>';
      for(const [key,value] of fields) {
        if(key in overview) continue;
        const label=key==='cases' ? 'Individual case results' : fieldLabel(key);
        html += `<details class="record-section"><summary>${escapeHTML(label)}</summary><div>${renderValue(value)}</div></details>`;
      }
      $('#detailBody').innerHTML=html;
    }
  } catch (_) {
    if(request===detailRequest) $('#detailBody').innerHTML='<p role="alert">Could not load these details. Please close this panel and try again.</p>';
  }
}
let registry, modelId, trackId, selectedCase, requestId = 0;
const player = $('#audioPlayer');
let playingButton = null;
function stopAudio() {
  player.pause();
  if (playingButton) {
    playingButton.classList.remove('playing');
    playingButton.setAttribute('aria-pressed', 'false');
  }
  playingButton = null;
}
player.addEventListener('ended', stopAudio);
player.addEventListener('error', () => {
  stopAudio();
  $('#loadStatus').textContent = 'This recording could not be played. Please try again.';
});
async function playAudio(button) {
  if (button === playingButton && !player.paused) { stopAudio(); return; }
  stopAudio();
  playingButton = button;
  player.src = window.previewAudio?.[button.dataset.audio] || button.dataset.audio;
  try {
    await player.play();
    if (playingButton !== button) return;
    button.classList.add('playing');
    button.setAttribute('aria-pressed', 'true');
  } catch (error) {
    if (playingButton !== button) return;
    stopAudio();
    if (error.name !== 'AbortError') $('#loadStatus').textContent = 'Playback failed. Please try the recording again.';
  }
}
const metricDefinitions = {
  total_scenarios_processed: ['Evaluated scenarios', 0, ''],
  total_completed: ['Completed scenarios', 0, ''],
  success_rate: ['Task success rate', 1, '%'],
  avg_turn_count: ['Average turns', 2, ''],
  avg_experience_score: ['Experience score', 2, ' / 5'],
  avg_tool_call_accuracy: ['Tool-call accuracy', 1, '%'],
  avg_tool_call_order_accuracy: ['Tool-order accuracy', 1, '%'],
  avg_agent_tool_call_accuracy: ['Agent tool accuracy', 1, '%'],
  avg_agent_tool_call_order_accuracy: ['Agent tool-order accuracy', 1, '%'],
  avg_user_tool_call_accuracy: ['User tool accuracy', 1, '%'],
  avg_user_tool_call_order_accuracy: ['User tool-order accuracy', 1, '%'],
  turn_count: ['Average turns', 2, ''],
  state_alignment: ['State alignment', 2, ' / 5'],
  utility: ['Utility', 2, ' / 5'],
  interaction_comfort: ['Interaction comfort', 2, ' / 5'],
  paralinguistic_comfort: ['Paralinguistic comfort', 2, ' / 5'],
  trust_level: ['Trust level', 2, ' / 5'],
  cognitive_load: ['Cognitive load', 2, ' / 5'],
  felt_understood: ['Felt understood', 2, ' / 5'],
  interaction_acceptance: ['Interaction acceptance', 2, ' / 5'],
  correction_rate: ['Correction rate', 1, '%'],
  total_samples: ['Evaluated samples', 0, ''],
  rule_score: ['Mean rule score', 2, ' / 5'],
  sample_score: ['Mean sample score', 2, ' / 5'],
  turn1_score: ['Turn 1 sample score', 2, ' / 5'],
  turn2_score: ['Turn 2 sample score', 2, ' / 5']
};
function renderMetrics() {
  const stats = registry.stats[trackId]?.[modelId] || {};
  const cards = Object.entries(metricDefinitions).filter(([key]) => Number.isFinite(stats[key]));
  $('#metricsRow').innerHTML = cards.map(([key, [label, digits, unit]]) => {
    const value = (stats[key] * (unit === '%' ? 100 : 1)).toFixed(digits);
    return `<div class="metric-card"><div class="metric-value">${value}<span style="font-size:.75rem">${unit}</span></div><div class="metric-label">${label}</div></div>`;
  }).join('');
  $('#metricsRow').hidden = cards.length === 0;
  $('#metricsNote').hidden = cards.length === 0;
  const source = registry.metric_sources?.[trackId]?.[modelId];
  $('#metricsNote').innerHTML = cards.length ? `Evaluation run metrics · ${source ? '<button type="button" class="text-button" id="sourceResults">Source results</button>' : ''}` : '';
  $('#sourceResults')?.addEventListener('click', () => openSource(source, 'metrics'));
}
async function loadCase(entry) {
  selectedCase = entry.case;
  const request = ++requestId;
  stopAudio();
  $('#chatMessages').replaceChildren();
  $('#taskContext').hidden = true;
  $('#taskContext').open = false;
  $('#rawSource').hidden = true;
  $('#loadStatus').textContent = 'Loading conversation…';
  $('#currentCaseDesc').textContent = entry.case;
  try {
    const response = await fetch(entry.path);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const conversation = await response.json();
    if (request !== requestId) return;
    $('#currentCaseDesc').textContent = [entry.case, conversation.title].filter(Boolean).join(' · ');
    $('#taskContext').hidden = !conversation.context;
    $('#taskContextText').innerHTML = renderContext(conversation.context || '');
    let previousRound = null;
    $('#chatMessages').innerHTML = conversation.messages.map(message => {
      if (!message.text && !message.audio) return '';
      let divider = '';
      if (message.round !== previousRound) {
        previousRound = message.round;
        divider = `<div class="round-divider"><span class="line"></span><span class="label">Round ${Number(message.round) + 1}</span><span class="line"></span></div>`;
      }
      const role = ['user', 'model', 'tool'].includes(message.role) ? message.role : 'model';
      const label = role === 'model' ? registry.models.find(m => m.id === modelId).name : (role === 'tool' ? fieldLabel(message.label) : message.label);
      const content = role === 'tool' ? `<details><summary>${escapeHTML(message.who === 'user' ? 'User tool call' : 'Agent tool call')}</summary><div class="rich-text tool-content">${renderTool(message.text)}</div></details>` : (message.text ? `<div class="rich-text">${renderContext(message.text)}</div>` : '');
      const audio = message.audio ? `<button class="voice-btn" type="button" title="Play recording" aria-label="Play ${escapeHTML(label)} recording, round ${Number(message.round) + 1}" aria-pressed="false" data-audio="${escapeHTML(message.audio)}"><span class="speaker-icon">▶</span><span class="bars"><span class="bar"></span><span class="bar"></span><span class="bar"></span></span></button>` : '';
      return `${divider}<div class="message ${role}"><div class="avatar" aria-hidden="true">${role === 'user' ? 'U' : role === 'tool' ? 'T' : 'M'}</div><div class="msg-body"><span class="msg-label ${role}">${escapeHTML(label)}</span>${content ? `<div class="bubble">${content}</div>` : ''}</div>${audio}</div>`;
    }).join('');
    $('#chatMessages').querySelectorAll('.voice-btn').forEach(button => button.addEventListener('click', () => playAudio(button)));
    $('#rawSource').onclick = () => openSource(conversation.raw_json, 'conversation');
    $('#rawSource').hidden = false;
    $('#loadStatus').textContent = '';
  } catch (error) {
    if (request !== requestId) return;
    $('#loadStatus').textContent = 'Could not load this conversation. Please select it again or reload the page.';
  }
}
function render() {
  const tracks = registry.tracks.filter(track => registry.cases[track.id]?.[modelId]?.length);
  if (!tracks.some(t => t.id === trackId)) trackId = tracks[0].id;
  const model = registry.models.find(m => m.id === modelId);
  const track = tracks.find(t => t.id === trackId);
  $('#currentModelName').textContent = model.name;
  $('#currentCaseBadge').textContent = track.name;
  $('#modelSelector').innerHTML = registry.models.map(m => `<button type="button" class="model-btn${m.id === modelId ? ' active' : ''}" aria-pressed="${m.id === modelId}" data-model="${escapeHTML(m.id)}">${escapeHTML(m.name)}</button>`).join('');
  $('#modelSelector').querySelectorAll('button').forEach(b => b.addEventListener('click', () => { modelId = b.dataset.model; render(); }));
  $('#caseTabs').innerHTML = tracks.map(t => `<button type="button" class="case-tab${t.id === trackId ? ' active' : ''}" aria-pressed="${t.id === trackId}" data-track="${escapeHTML(t.id)}">${escapeHTML(t.name)}</button>`).join('');
  $('#caseTabs').querySelectorAll('button').forEach(b => b.addEventListener('click', () => { trackId = b.dataset.track; render(); }));
  renderMetrics();
  const entries = registry.cases[trackId][modelId];
  const entry = entries.find(e => e.case === selectedCase) || entries[0];
  $('#casePicker').hidden = entries.length <= 1;
  $('#casePicker').innerHTML = `<label for="exampleSelect">Recorded example</label><select id="exampleSelect">${entries.map(e => `<option value="${escapeHTML(e.case)}"${e.case === entry.case ? ' selected' : ''}>${escapeHTML(e.case)}${e.title ? ' · ' + escapeHTML(e.title) : ''}</option>`).join('')}</select>`;
  $('#exampleSelect').addEventListener('change', event => loadCase(entries.find(e => e.case === event.target.value)));
  loadCase(entry);
}
(async function init() {
  try {
    const response = await fetch('data/index.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    registry = await response.json();
    registry.models = registry.models.filter(m => registry.tracks.some(t => registry.cases[t.id]?.[m.id]?.length));
    if (!registry.models.length) throw new Error('No recorded examples');
    modelId = registry.models[0].id;
    render();
  } catch (error) {
    $('#loadStatus').textContent = 'Could not load benchmark data. Reload this page from its web server.';
  }
})();
