'use strict';
const $ = id => document.getElementById(id);
// These SVG fragments are fixed application assets; no user/model text enters innerHTML.
const icons = {
  'washing-machine': '<svg viewBox="0 0 36 42" aria-hidden="true"><rect x="5" y="3" width="26" height="35" rx="3"/><path d="M5 11h26M10 7h5M25 7h1"/><circle cx="18" cy="24" r="9"/><path d="M10 25c5-6 10 6 16-1M9 38v2m18-2v2"/></svg>',
  dishwasher: '<svg viewBox="0 0 36 42" aria-hidden="true"><rect x="5" y="3" width="26" height="35" rx="3"/><path d="M5 12h26M10 7h5m10 0h1M11 20h14M11 25h14M11 30h14M9 38v2m18-2v2"/></svg>',
  'coffee-machine': '<svg viewBox="0 0 36 42" aria-hidden="true"><path d="M6 37V6a3 3 0 0 1 3-3h16a3 3 0 0 1 3 3v31ZM6 13h22M11 8h4m8 0h1M16 13v7m4-7v7M9 34h16"/><path d="M12 24h10v5a4 4 0 0 1-4 4h-2a4 4 0 0 1-4-4Zm10 1h2a2 2 0 0 1 0 4h-2"/></svg>'
};
let docs = [], selected = null, busy = false;
const input = $('question');
const mobile = window.matchMedia('(max-width: 760px)');
function element(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}
function icon(id, className = 'appliance-icon') {
  const el = element('span', className);
  el.innerHTML = icons[id] || icons['washing-machine'];
  return el;
}
function navigation(open) {
  $('sidebar').classList.toggle('open', open);
  $('backdrop').hidden = !open;
  $('menu-toggle').setAttribute('aria-expanded', String(open));
  $('sidebar').inert = mobile.matches && !open;
  if (open) $('new-chat').focus();
}
$('menu-toggle').addEventListener('click', () => navigation(!$('sidebar').classList.contains('open')));
$('backdrop').addEventListener('click', () => { navigation(false); $('menu-toggle').focus(); });
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && mobile.matches && $('sidebar').classList.contains('open')) {
    navigation(false); $('menu-toggle').focus();
  }
  if (event.key === 'Tab' && mobile.matches && $('sidebar').classList.contains('open')) {
    const items = [...$('sidebar').querySelectorAll('a,button:not(:disabled)')];
    const first = items[0], last = items.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
});
mobile.addEventListener('change', () => navigation(false));
navigation(false);
function setBusy(value) {
  busy = value;
  $('chat-form').setAttribute('aria-busy', String(value));
  $('new-chat').disabled = value;
  document.querySelectorAll('.appliance-button,.suggestion').forEach(button => { button.disabled = value; });
  $('send').disabled = value || !selected || !input.value.trim();
}
function resetChat() {
  if (busy) return;
  $('messages').replaceChildren();
  $('welcome').hidden = false;
  input.value = '';
  input.style.height = 'auto';
  $('scroll-area').scrollTop = 0;
  setBusy(false);
}
$('new-chat').addEventListener('click', () => { resetChat(); navigation(false); input.focus(); });
function selectAppliance(doc, focusComposer = true) {
  if (busy) return;
  selected = doc;
  resetChat();
  $('active-title').textContent = doc.appliance;
  $('model-label').textContent = doc.model;
  $('welcome-icon').replaceChildren(icon(doc.id));
  input.placeholder = `Ask about your ${doc.appliance.toLowerCase()}…`;
  document.querySelectorAll('.appliance-button').forEach(button => {
    const active = button.dataset.id === doc.id;
    button.setAttribute('aria-pressed', String(active));
    button.querySelector('.appliance-check').textContent = active ? '✓' : '';
  });
  $('suggestions').replaceChildren();
  doc.questions.forEach((item, index) => {
    const button = element('button', 'suggestion');
    button.type = 'button';
    button.append(element('span', 'suggestion-tag', index === 0 ? 'Everyday know-how' : 'Care & troubleshooting'),
      element('span', 'suggestion-question', item.question), element('span', 'suggestion-arrow', '↗'));
    button.addEventListener('click', () => { input.value = item.question; submit(); });
    $('suggestions').append(button);
  });
  navigation(false);
  if (focusComposer) input.focus();
}
function renderDocuments() {
  $('appliance-list').replaceChildren(); $('document-list').replaceChildren();
  $('appliance-count').textContent = String(docs.length).padStart(2, '0');
  docs.forEach(doc => {
    const button = element('button', 'appliance-button');
    button.type = 'button'; button.dataset.id = doc.id;
    button.setAttribute('aria-pressed', 'false');
    const label = element('span', 'appliance-text', doc.appliance);
    label.append(element('small', '', doc.model.replace(/^Bosch /, '')));
    const check = element('span', 'appliance-check'); check.setAttribute('aria-hidden', 'true');
    button.append(icon(doc.id), label, check);
    button.addEventListener('click', () => selectAppliance(doc));
    $('appliance-list').append(button);
    const link = element('a', 'document-link');
    link.href = doc.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
    link.title = doc.filename;
    const text = element('span', 'document-name', `${doc.appliance} manual`);
    const state = doc.indexed_chunks ? 'Indexed' : doc.available ? 'Ready to index' : 'PDF missing';
    text.append(element('small', '', `${doc.page_count} pages · ${state}`));
    link.append(element('span', 'pdf-tag', 'PDF'), text);
    link.setAttribute('aria-label', `Open ${doc.appliance.toLowerCase()} manual, ${doc.filename}, in a new tab`);
    $('document-list').append(link);
  });
}
function renderCitations(container, text, sources) {
  const regex = /\[([^\[\]\n]+), p\. ([1-9]\d*)\]/g;
  let last = 0;
  for (const match of text.matchAll(regex)) {
    container.append(document.createTextNode(text.slice(last, match.index)));
    const source = sources.find(s => s.filename === match[1] && s.page === Number(match[2]));
    if (source) {
      const link = element('a', 'citation', match[0]);
      link.href = source.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
      link.setAttribute('aria-label', `${source.filename}, page ${source.page}, opens original PDF in a new tab`);
      container.append(link);
    } else container.append(document.createTextNode(match[0]));
    last = match.index + match[0].length;
  }
  container.append(document.createTextNode(text.slice(last)));
}
function addMessage(role, text, sources = [], status = '') {
  const article = element('article', `message ${role}`);
  const heading = element('div', 'message-heading');
  const avatar = element('span', 'message-avatar', role === 'user' ? 'Y' : '⌂');
  avatar.setAttribute('aria-hidden', 'true');
  heading.append(avatar, document.createTextNode(role === 'user' ? 'You' : 'HomeGuide'));
  const body = element('div', 'message-body');
  if (status === 'insufficient_information') body.append(element('div', 'message-status', 'No supported answer found'));
  renderCitations(body, text, sources);
  if (sources.length) {
    const details = element('details', 'sources');
    details.append(element('summary', '', `Sources · ${sources.length} ${sources.length === 1 ? 'page' : 'pages'} reviewed`));
    sources.forEach(source => {
      const card = element('div', 'source-card');
      const link = element('a', '', `${source.filename}, p. ${source.page}`);
      link.href = source.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
      card.append(link, element('span', 'source-kind', source.kind), element('p', '', source.text));
      details.append(card);
    });
    body.append(details);
  }
  article.append(heading, body); $('messages').append(article);
  return article;
}
function scrollToLatest(force = false) {
  const area = $('scroll-area');
  if (force || area.scrollHeight - area.scrollTop - area.clientHeight < 180) area.scrollTop = area.scrollHeight;
}
async function submit() {
  const text = input.value.trim();
  if (busy || !text || !selected) return;
  setBusy(true); $('welcome').hidden = true;
  addMessage('user', text);
  input.value = ''; input.style.height = 'auto';
  const loading = element('div', 'loading'); loading.setAttribute('role', 'status');
  const spinner = element('span', 'spinner'); spinner.setAttribute('aria-hidden', 'true');
  loading.append(spinner, document.createTextNode('Finding the right pages in your manual…'));
  $('messages').append(loading); scrollToLatest(true);
  try {
    const response = await fetch('/api/chat', {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({appliance: selected.id, question: text})});
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'HomeGuide could not answer this question. Please try again.');
    loading.remove(); addMessage('assistant', data.answer, data.sources || [], data.status);
  } catch (error) {
    loading.remove();
    addMessage('assistant error', error instanceof TypeError ? 'Cannot connect to HomeGuide. Check that the local server is running, then try again.' : error.message);
    input.value = text;
  } finally {
    setBusy(false); scrollToLatest(); input.focus();
  }
}
$('chat-form').addEventListener('submit', event => { event.preventDefault(); submit(); });
input.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); submit(); }
});
input.addEventListener('input', () => {
  input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 150) + 'px';
  $('send').disabled = busy || !selected || !input.value.trim();
});
async function initialize() {
  try {
    const response = await fetch('/api/appliances');
    if (!response.ok) throw new Error('Cannot load the manual library. Check documents.json and restart the server.');
    const data = await response.json(); docs = data.documents;
    if (!docs.length) throw new Error('No registered manuals found. Add documents to documents.json.');
    renderDocuments(); selectAppliance(docs[0], false);
    const notices = [];
    if (!data.index_ready) notices.push(data.index_issue);
    if (!data.llm_ready) notices.push('Answer generation needs an API key. Set LLM_API_KEY in your local .env and restart the server.');
    if (notices.length) { $('setup-notice').textContent = notices.join(' '); $('setup-notice').hidden = false; }
  } catch (error) {
    $('setup-notice').textContent = error instanceof TypeError ? 'Cannot connect to HomeGuide. Check that the server is running and reload this page.' : error.message;
    $('setup-notice').hidden = false;
    $('model-label').textContent = 'Manual library unavailable';
  }
}
initialize();
