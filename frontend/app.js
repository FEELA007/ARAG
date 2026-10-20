const $ = (id) => document.getElementById(id);
const fileInput = $('fileInput');
const dropzone = $('dropzone');
const fileCard = $('fileCard');
const questionInput = $('questionInput');
const sendBtn = $('sendBtn');
const chatBody = $('chatBody');
const emptyState = $('emptyState');
const MAX_FILE_BYTES = 10 * 1024 * 1024;
const allowedExtensions = ['pdf', 'docx', 'txt'];
let selectedFiles = [];
let documentId = null;
let toastTimer;
let tokenBudget = Number(localStorage.getItem('aragTokenBudget') || 10000);

const modelDetails = {
  model_1: {
    title: 'ARAG Lite', description: 'MiniLM dense retrieval · 1 document', label: 'MODEL 1',
    maxFiles: 1, target: 75, contextCap: 1000, outputTokens: 128,
    strategy: 'Dense semantic retrieval'
  },
  model_2: {
    title: 'ARAG Balanced', description: 'BGE embeddings · BM25 · RRF · up to 4 documents', label: 'MODEL 2',
    maxFiles: 4, target: 85, contextCap: 4000, outputTokens: 256,
    strategy: 'Hybrid retrieval with reciprocal-rank fusion'
  },
  model_3: {
    title: 'ARAG Advanced', description: 'GTE · multi-query hybrid · cross-encoder reranking', label: 'MODEL 3',
    maxFiles: 10, target: 95, contextCap: 32000, outputTokens: 512,
    strategy: 'Adaptive hybrid retrieval, reranking and evidence checks'
  }
};

function showToast(message) {
  const toast = $('toast');
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 4200);
}
function formatBytes(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}
function extension(fileName) { return fileName.split('.').pop().toLowerCase(); }
function activeModel() { return $('modelSelect').value; }
function setDocumentEnabled(enabled) {
  questionInput.disabled = !enabled;
  sendBtn.disabled = !enabled;
  $('composerContext').textContent = enabled ? `${selectedFiles.length} document(s) indexed` : 'Waiting for documents';
  $('composerContext').style.color = enabled ? '#c3b2f4' : '';
}
function addMessage(role, label, text) {
  if (emptyState && emptyState.isConnected) emptyState.remove();
  const message = document.createElement('div');
  message.className = `chat-message ${role}`;
  const messageLabel = document.createElement('div');
  messageLabel.className = 'message-label';
  messageLabel.textContent = label;
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';
  bubble.textContent = text;
  message.append(messageLabel, bubble);
  chatBody.appendChild(message);
  chatBody.scrollTop = chatBody.scrollHeight;
  return message;
}
function showEvidence(sources) {
  const list = $('evidenceList');
  list.innerHTML = '';
  $('evidenceCount').textContent = String(sources.length);
  if (!sources.length) {
    list.classList.add('hidden');
    document.querySelector('.evidence-empty').classList.remove('hidden');
    return;
  }
  document.querySelector('.evidence-empty').classList.add('hidden');
  list.classList.remove('hidden');
  sources.forEach((source) => {
    const item = document.createElement('div');
    item.className = 'evidence-item';
    const score = document.createElement('span');
    score.className = 'score';
    score.textContent = `dense ${Number(source.score || 0).toFixed(3)}`;
    const title = document.createElement('strong');
    title.textContent = `Source ${source.rank}: ${source.filename}`;
    const meta = document.createElement('small');
    const rerank = source.rerank_score === null || source.rerank_score === undefined ? '' : ` · rerank ${Number(source.rerank_score).toFixed(3)}`;
    meta.textContent = `${source.page ? `Page ${source.page}` : 'Page not available'} · ${source.chunk_id || `passage ${source.rank}`}${rerank}`;
    const text = document.createElement('p');
    text.textContent = source.text;
    item.append(score, title, meta, text);
    list.appendChild(item);
  });
}
function renderSelectedFiles() {
  const model = modelDetails[activeModel()];
  $('uploadLimitText').textContent = `${model.title}: up to ${model.maxFiles} document(s) · 10 MB per file`;
  $('fileModeLabel').textContent = `${model.maxFiles} FILE${model.maxFiles === 1 ? '' : 'S'} MAX`;
  if (!selectedFiles.length) {
    fileCard.classList.add('hidden');
    dropzone.classList.remove('hidden');
    return;
  }
  $('fileName').textContent = selectedFiles.map(f => f.name).join('\n');
  $('fileSize').textContent = `${selectedFiles.length} selected · ${formatBytes(selectedFiles.reduce((sum, f) => sum + f.size, 0))} total`;
  $('fileType').textContent = selectedFiles.length === 1 ? extension(selectedFiles[0].name).toUpperCase() : `${selectedFiles.length} FILES`;
  fileCard.classList.remove('hidden');
  dropzone.classList.add('hidden');
}
async function handleFiles(fileList) {
  const incoming = Array.from(fileList || []);
  if (!incoming.length) return;
  const model = activeModel();
  const tier = modelDetails[model];
  if (incoming.length > tier.maxFiles) {
    showToast(`${tier.title} allows up to ${tier.maxFiles} document(s). Select fewer files or choose a higher tier.`);
    fileInput.value = '';
    return;
  }
  for (const file of incoming) {
    if (!allowedExtensions.includes(extension(file.name))) {
      showToast(`Unsupported file type: ${file.name}. Use PDF, DOCX or TXT.`);
      fileInput.value = '';
      return;
    }
    if (file.size > MAX_FILE_BYTES) {
      showToast(`${file.name} is larger than 10 MB. Each file must be 10 MB or smaller.`);
      fileInput.value = '';
      return;
    }
  }
  selectedFiles = incoming;
  documentId = null;
  renderSelectedFiles();
  $('documentStatus').textContent = `Uploading and indexing ${selectedFiles.length} document(s)…`;
  $('documentStatus').style.color = '#c0b0f3';
  $('sourceCount').textContent = '0';
  setDocumentEnabled(false);
  try {
    const form = new FormData();
    selectedFiles.forEach(file => form.append('files', file));
    form.append('model', model);
    const response = await fetch('/api/upload', { method: 'POST', body: form });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Upload failed.');
    documentId = data.document_id;
    $('fileSize').textContent = `${data.file_count} document(s) indexed · ${formatBytes(data.total_bytes)} total`;
    $('documentStatus').textContent = `${data.file_count} document(s) indexed and ready`;
    $('documentStatus').style.color = '#83e7bb';
    $('sourceCount').textContent = String(data.file_count);
    $('chunkMetric').textContent = String(data.chunk_count);
    setDocumentEnabled(selectedFiles.length <= modelDetails[activeModel()].maxFiles);
    showToast(`${data.file_count} document(s) indexed. ${data.chunk_count} passages created.`);
  } catch (error) {
    documentId = null;
    $('documentStatus').textContent = 'Upload or indexing failed';
    $('fileSize').textContent = `${selectedFiles.length} selected · indexing failed`;
    setDocumentEnabled(false);
    showToast(error.message || 'Could not connect to the backend. Is the API running?');
  }
  fileInput.value = '';
}
function clearFiles() {
  selectedFiles = [];
  documentId = null;
  fileInput.value = '';
  renderSelectedFiles();
  $('documentStatus').textContent = 'No documents loaded';
  $('documentStatus').style.color = '';
  $('sourceCount').textContent = '0';
  $('chunkMetric').textContent = '—';
  $('retrievedMetric').textContent = '—';
  $('latencyMetric').textContent = '—';
  setDocumentEnabled(false);
  showEvidence([]);
}
function updateModel() {
  const key = activeModel();
  const detail = modelDetails[key];
  $('modelTitle').textContent = detail.title;
  $('modelDescription').textContent = detail.description;
  $('composerModel').textContent = detail.label;
  $('backendMetric').textContent = detail.label;
  $('uploadLimitText').textContent = `${detail.title}: up to ${detail.maxFiles} document(s) · 10 MB per file`;
  $('fileModeLabel').textContent = `${detail.maxFiles} FILE${detail.maxFiles === 1 ? '' : 'S'} MAX`;
  $('modelFootnote').textContent = `Target: ${detail.target}% answer accuracy · ${detail.strategy}. This is a target, not a measured result.`;
  if (selectedFiles.length) {
    if (selectedFiles.length > detail.maxFiles) {
      $('documentStatus').textContent = `${selectedFiles.length} files loaded; ${detail.title} allows ${detail.maxFiles}. Choose a higher tier or re-upload fewer files.`;
      $('documentStatus').style.color = '#e6bf87';
      setDocumentEnabled(false);
    } else {
      setDocumentEnabled(Boolean(documentId));
      if (documentId) $('documentStatus').textContent = `${selectedFiles.length} document(s) indexed · ${detail.title} selected`;
    }
  }
  const effective = Math.min(tokenBudget, detail.contextCap);
  $('tokenBudgetValue').textContent = Number(tokenBudget).toLocaleString('en-US');
  $('modelDescription').textContent = `${detail.description} · ${effective.toLocaleString('en-US')} context / ${detail.outputTokens} output tokens`;
}
async function askQuestion(question) {
  const model = activeModel();
  const message = addMessage('assistant', `${modelDetails[model].label} · ${modelDetails[model].title}`, 'Analyzing query, retrieving evidence and checking support…');
  const bubble = message.querySelector('.message-bubble');
  sendBtn.disabled = true;
  try {
    const response = await fetch('/api/query', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_id: documentId, question, model, token_budget: tokenBudget })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Question failed.');
    bubble.textContent = data.answer;
    $('chunkMetric').textContent = String(data.chunk_count);
    $('retrievedMetric').textContent = String(data.retrieved_count);
    $('latencyMetric').textContent = `${data.latency_ms} ms`;
    $('backendMetric').textContent = modelDetails[data.model].label;
    $('sourceCount').textContent = String(data.document_count);
    showEvidence(data.sources || []);
    const statusText = data.status === 'insufficient_evidence'
      ? 'Insufficient evidence — answer withheld'
      : data.status === 'extractive_fallback' ? 'Generator unavailable — fallback evidence shown' : 'Answer generated with evidence';
    if (data.generation_warning) showToast(`${statusText}. ${data.generation_warning}`);
    else showToast(`${statusText}. Context budget: ${Number(data.effective_context_budget).toLocaleString()} tokens; output limit: ${data.output_token_limit}.`);
  } catch (error) {
    bubble.textContent = `Request failed: ${error.message}\n\nCheck that the backend is running, the selected tier supports this many documents, and the required model dependencies can load.`;
    showToast(error.message || 'Backend request failed.');
  } finally {
    sendBtn.disabled = !documentId || selectedFiles.length > modelDetails[activeModel()].maxFiles;
  }
}

fileInput.addEventListener('change', event => handleFiles(event.target.files));
$('removeFile').addEventListener('click', clearFiles);
$('modelSelect').addEventListener('change', updateModel);
dropzone.addEventListener('dragover', event => { event.preventDefault(); dropzone.classList.add('dragover'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
dropzone.addEventListener('drop', event => { event.preventDefault(); dropzone.classList.remove('dragover'); handleFiles(event.dataTransfer.files); });
$('questionForm').addEventListener('submit', async event => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question || !documentId || selectedFiles.length > modelDetails[activeModel()].maxFiles) return;
  addMessage('user', 'YOU', question);
  questionInput.value = '';
  questionInput.style.height = 'auto';
  await askQuestion(question);
});
questionInput.addEventListener('input', () => {
  questionInput.style.height = 'auto';
  questionInput.style.height = `${Math.min(questionInput.scrollHeight, 100)}px`;
});
questionInput.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); if (!sendBtn.disabled) $('questionForm').requestSubmit(); }
});
document.querySelectorAll('.suggestion').forEach(button => button.addEventListener('click', () => {
  if (!documentId) { showToast('Upload and index documents first.'); return; }
  questionInput.value = button.dataset.question;
  questionInput.focus();
  questionInput.dispatchEvent(new Event('input'));
}));
$('newChatBtn').addEventListener('click', () => {
  chatBody.innerHTML = '';
  const freshEmpty = emptyState.cloneNode(true);
  freshEmpty.classList.remove('hidden');
  chatBody.appendChild(freshEmpty);
  $('retrievedMetric').textContent = '—';
  $('latencyMetric').textContent = '—';
  showEvidence([]);
  showToast('New conversation started. Indexed documents are unchanged.');
});
$('clearChatBtn').addEventListener('click', () => $('newChatBtn').click());
$('helpBtn').addEventListener('click', () => $('helpDialog').showModal());
$('closeHelp').addEventListener('click', () => $('helpDialog').close());
$('gotIt').addEventListener('click', () => $('helpDialog').close());
$('settingsBtn').addEventListener('click', () => { $('tokenBudget').value = tokenBudget; $('tokenBudgetValue').textContent = Number(tokenBudget).toLocaleString('en-US'); $('settingsDialog').showModal(); });
$('closeSettings').addEventListener('click', () => $('settingsDialog').close());
$('tokenBudget').addEventListener('input', () => { $('tokenBudgetValue').textContent = Number($('tokenBudget').value).toLocaleString('en-US'); });
$('saveSettings').addEventListener('click', () => {
  tokenBudget = Math.max(1000, Math.min(32000, Number($('tokenBudget').value) || 10000));
  localStorage.setItem('aragTokenBudget', String(tokenBudget));
  $('settingsDialog').close();
  updateModel();
  showToast(`Token budget saved: ${tokenBudget.toLocaleString()} tokens. The active tier cap still applies.`);
});
$('sourcesNav').addEventListener('click', () => $('evidencePanel').scrollIntoView({ behavior: 'smooth', block: 'center' }));
$('metricsNav').addEventListener('click', () => $('metricsPanel').scrollIntoView({ behavior: 'smooth', block: 'center' }));
window.addEventListener('keydown', event => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); questionInput.focus(); }
});
$('tokenBudget').value = tokenBudget;
$('tokenBudgetValue').textContent = tokenBudget.toLocaleString('en-US');
setDocumentEnabled(false);
updateModel();
