/* ═══════════════════════════════════════════════════════════════
   HR Assistant — Frontend Logic
   ═══════════════════════════════════════════════════════════════ */

const API = '';          // same-origin; change to 'http://localhost:8000' for local dev
const STORAGE_KEY = 'hr_auth';

let selectedSource = null;  // null = query all docs; string = filter by this filename
let _cachedDocs    = [];

// ── Auth helpers ──────────────────────────────────────────────────────────────

function saveAuth(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

function loadAuth() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)); }
  catch { return null; }
}

function clearAuth() {
  localStorage.removeItem(STORAGE_KEY);
}

function authHeaders() {
  const auth = loadAuth();
  return auth ? { Authorization: `Bearer ${auth.access_token}` } : {};
}

// ── Page switching ────────────────────────────────────────────────────────────

function showPage(id) {
  document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
  document.getElementById(id).classList.remove('hidden');
}

function initChatUI(auth) {
  const initial = auth.name.charAt(0).toUpperCase();

  // Header
  document.getElementById('hdr-avatar').textContent = initial;
  document.getElementById('hdr-name').textContent = auth.name;
  document.getElementById('hdr-role').textContent = auth.is_admin ? '🔑 Admin' : auth.position;

  // Sidebar card
  document.getElementById('card-avatar').textContent = initial;
  document.getElementById('card-name').textContent = auth.name;
  document.getElementById('card-position').textContent = auth.position;
  document.getElementById('card-dept').textContent = auth.department;

  // Role-based visibility: only admins see upload, docs, and employee panel
  const isAdmin = !!auth.is_admin;
  document.querySelector('.upload-box').classList.toggle('hidden', !isAdmin);
  document.querySelector('.docs-panel').classList.toggle('hidden', !isAdmin);
  document.getElementById('emp-panel').classList.toggle('hidden', !isAdmin);
  const uploadHint = document.getElementById('upload-hint');
  if (uploadHint) uploadHint.classList.toggle('hidden', !isAdmin);

  showPage('chat-page');
  if (isAdmin) { loadDocuments(); loadEmployees(); }
}

// ── Login ─────────────────────────────────────────────────────────────────────

const loginForm    = document.getElementById('login-form');
const loginError   = document.getElementById('login-error');
const loginBtn     = document.getElementById('login-btn');
const loginBtnText = document.getElementById('login-btn-text');
const loginSpinner = document.getElementById('login-spinner');

function setLoginLoading(on) {
  loginBtn.disabled = on;
  loginBtnText.textContent = on ? 'Signing in…' : 'Sign In';
  loginSpinner.classList.toggle('hidden', !on);
}

loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  loginError.classList.add('hidden');
  setLoginLoading(true);

  const email    = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;

  try {
    const res = await fetch(`${API}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Login failed');
    }

    const auth = await res.json();
    saveAuth(auth);
    initChatUI(auth);
  } catch (err) {
    loginError.textContent = err.message;
    loginError.classList.remove('hidden');
  } finally {
    setLoginLoading(false);
  }
});

// ── Logout ────────────────────────────────────────────────────────────────────

document.getElementById('logout-btn').addEventListener('click', () => {
  clearAuth();
  document.getElementById('login-email').value = '';
  document.getElementById('login-password').value = '';
  showPage('login-page');
});

// ── Chat ──────────────────────────────────────────────────────────────────────

const messagesArea = document.getElementById('messages');
const msgInput     = document.getElementById('msg-input');
const sendBtn      = document.getElementById('send-btn');
const charCount    = document.getElementById('char-count');

function scrollToBottom() {
  messagesArea.scrollTop = messagesArea.scrollHeight;
}

function appendMessage(role, html, sources = []) {
  const div = document.createElement('div');
  div.className = `message ${role === 'user' ? 'user-message' : 'bot-message'}`;

  const avatarEl = document.createElement('div');
  avatarEl.className = 'msg-avatar';
  avatarEl.textContent = role === 'user' ? '👤' : '🤖';

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML = html;

  if (sources.length) {
    const srcs = document.createElement('div');
    srcs.className = 'msg-sources';
    sources.forEach(s => {
      const tag = document.createElement('span');
      tag.className = 'source-tag';
      tag.textContent = `📄 ${s}`;
      srcs.appendChild(tag);
    });
    bubble.appendChild(srcs);
  }

  div.appendChild(avatarEl);
  div.appendChild(bubble);
  messagesArea.appendChild(div);
  scrollToBottom();
  return div;
}

function showTyping() {
  const div = document.createElement('div');
  div.className = 'message bot-message typing-indicator';
  div.id = 'typing';
  div.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-bubble">
      <span class="dot"></span><span class="dot"></span><span class="dot"></span>
    </div>`;
  messagesArea.appendChild(div);
  scrollToBottom();
}

function removeTyping() {
  document.getElementById('typing')?.remove();
}

function escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function formatBotText(text) {
  // Basic markdown: **bold**, *italic*, newlines → <br>
  return escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
}

async function sendMessage() {
  const text = msgInput.value.trim();
  if (!text) return;

  appendMessage('user', `<p>${escapeHtml(text)}</p>`);
  msgInput.value = '';
  msgInput.style.height = 'auto';
  charCount.textContent = '0 / 2000';
  charCount.className = 'char-count';
  sendBtn.disabled = true;
  showTyping();

  try {
    const res = await fetch(`${API}/api/v1/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ message: text, source: selectedSource }),
    });

    removeTyping();

    if (res.status === 401) {
      clearAuth();
      showPage('login-page');
      return;
    }

    if (!res.ok) {
      const err = await res.json();
      appendMessage('bot', `<p style="color:var(--error)">⚠️ ${escapeHtml(err.detail || 'Something went wrong')}</p>`);
      return;
    }

    const data = await res.json();
    appendMessage('bot', `<p>${formatBotText(data.message)}</p>`, data.sources || []);
  } catch (err) {
    removeTyping();
    appendMessage('bot', `<p style="color:var(--error)">⚠️ Network error. Please try again.</p>`);
  } finally {
    sendBtn.disabled = false;
    msgInput.focus();
  }
}

// Send on Enter (Shift+Enter = newline)
msgInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

sendBtn.addEventListener('click', sendMessage);

// Auto-resize textarea
msgInput.addEventListener('input', () => {
  msgInput.style.height = 'auto';
  msgInput.style.height = Math.min(msgInput.scrollHeight, 160) + 'px';

  const len = msgInput.value.length;
  charCount.textContent = `${len} / 2000`;
  charCount.className = 'char-count' + (len > 1800 ? ' warn' : '') + (len >= 2000 ? ' over' : '');
});


// ── PDF Upload ────────────────────────────────────────────────────────────────

const pdfInput      = document.getElementById('pdf-upload');
const progressWrap  = document.getElementById('upload-progress');
const progressFill  = document.getElementById('progress-fill');
const uploadLabel   = document.getElementById('upload-label-text');
const uploadStatus  = document.getElementById('upload-status-text');

pdfInput.addEventListener('change', async () => {
  const file = pdfInput.files[0];
  if (!file) return;

  uploadLabel.textContent = file.name;
  progressWrap.classList.remove('hidden');
  progressFill.style.width = '30%';
  uploadStatus.textContent = 'Uploading…';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch(`${API}/api/v1/upload-pdf`, {
      method: 'POST',
      headers: authHeaders(),
      body: formData,
    });

    progressFill.style.width = '100%';

    if (res.status === 401) { clearAuth(); showPage('login-page'); return; }

    const data = await res.json();

    if (!res.ok) {
      uploadStatus.textContent = `❌ ${data.detail || 'Upload failed'}`;
      uploadStatus.style.color = 'var(--error)';
    } else {
      uploadStatus.textContent = `✅ Ingested ${data.data?.chunks ?? '?'} chunks`;
      uploadStatus.style.color = 'var(--success)';
      loadDocuments(file.name);   // refresh list and auto-select the new doc
      appendMessage(
        'bot',
        `<p>📄 <strong>${escapeHtml(file.name)}</strong> has been uploaded and indexed. Now querying this document only.</p>`
      );
    }
  } catch {
    uploadStatus.textContent = '❌ Network error during upload';
    uploadStatus.style.color = 'var(--error)';
  } finally {
    pdfInput.value = '';
    setTimeout(() => {
      progressWrap.classList.add('hidden');
      progressFill.style.width = '0%';
      uploadLabel.textContent = 'Choose PDF to upload';
      uploadStatus.style.color = '';
    }, 3000);
  }
});

// ── Document List ─────────────────────────────────────────────────────────────

async function loadDocuments(selectAfter = undefined) {
  try {
    const res = await fetch(`${API}/api/v1/documents`, { headers: authHeaders() });
    if (!res.ok) return;
    _cachedDocs = await res.json();
    if (selectAfter !== undefined) {
      selectedSource = selectAfter;
      updateContextBadge();
    }
    renderDocsList();
  } catch { /* silent — docs panel is non-critical */ }
}

function renderDocsList() {
  const list = document.getElementById('docs-list');
  list.innerHTML = '';

  const allRow = document.createElement('div');
  allRow.className = 'doc-all' + (selectedSource === null ? ' active' : '');
  allRow.innerHTML = '<span>🗂️</span><span>All Documents</span>';
  allRow.addEventListener('click', () => {
    selectedSource = null;
    updateContextBadge();
    renderDocsList();
  });
  list.appendChild(allRow);

  if (!_cachedDocs.length) {
    const empty = document.createElement('div');
    empty.className = 'doc-empty';
    empty.textContent = 'No documents yet. Upload a PDF above.';
    list.appendChild(empty);
    return;
  }

  _cachedDocs.forEach(doc => {
    const notIndexed = doc.chunks === 0;
    const item = document.createElement('div');
    item.className = 'doc-item' + (selectedSource === doc.filename ? ' active' : '') + (notIndexed ? ' doc-unindexed' : '');
    const date = new Date(doc.uploaded_at).toLocaleDateString();
    const chunkStr = notIndexed ? '⚠️ not indexed' : `${doc.chunks} chunks`;
    item.innerHTML =
      `<span class="doc-icon">${notIndexed ? '⚠️' : '📄'}</span>` +
      `<div class="doc-info">` +
        `<div class="doc-name" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</div>` +
        `<div class="doc-meta">${escapeHtml(chunkStr)} · ${date}</div>` +
      `</div>`;
    if (!notIndexed) {
      item.addEventListener('click', () => {
        selectedSource = selectedSource === doc.filename ? null : doc.filename;
        updateContextBadge();
        renderDocsList();
      });
    } else {
      item.title = 'No text could be extracted. Re-upload a text-based PDF.';
    }
    list.appendChild(item);
  });
}

function updateContextBadge() {
  const badge = document.getElementById('context-badge');
  if (selectedSource) {
    badge.textContent = `📄 ${selectedSource}`;
    badge.classList.remove('hidden');
    badge.title = 'Click to query all documents';
    badge.onclick = () => { selectedSource = null; updateContextBadge(); renderDocsList(); };
  } else {
    badge.classList.add('hidden');
    badge.onclick = null;
  }
}

// ── Employee Management (Admin) ───────────────────────────────────────────────

async function loadEmployees() {
  try {
    const res = await fetch(`${API}/api/v1/admin/employees`, { headers: authHeaders() });
    if (!res.ok) return;
    renderEmployeeList(await res.json());
  } catch { /* silent */ }
}

function renderEmployeeList(employees) {
  const list = document.getElementById('emp-list');
  if (!list) return;
  list.innerHTML = '';

  if (!employees.length) {
    list.innerHTML = '<div class="emp-empty">No employees yet.</div>';
    return;
  }

  const auth = loadAuth();
  employees.forEach(emp => {
    const isSelf = auth && auth.employee_id === emp.employee_id;
    const row = document.createElement('div');
    row.className = 'emp-row';
    row.innerHTML =
      `<div class="emp-row-avatar">${emp.name.charAt(0).toUpperCase()}</div>` +
      `<div class="emp-info">` +
        `<div class="emp-name">${escapeHtml(emp.name)}` +
          (emp.is_admin ? ' <span class="emp-admin-badge">Admin</span>' : '') +
        `</div>` +
        `<div class="emp-meta">${escapeHtml(emp.department)}</div>` +
      `</div>` +
      (!isSelf
        ? `<button class="btn-delete-emp" data-id="${emp.employee_id}" title="Deactivate">🗑️</button>`
        : '');

    if (!isSelf) {
      row.querySelector('.btn-delete-emp').addEventListener('click', () =>
        deleteEmployee(emp.employee_id, emp.name)
      );
    }
    list.appendChild(row);
  });
}

async function deleteEmployee(employeeId, name) {
  if (!confirm(`Deactivate ${name}? They will lose login access.`)) return;
  try {
    const res = await fetch(`${API}/api/v1/admin/employees/${employeeId}`, {
      method: 'DELETE',
      headers: authHeaders(),
    });
    if (res.status === 401) { clearAuth(); showPage('login-page'); return; }
    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || 'Delete failed');
      return;
    }
    loadEmployees();
  } catch { alert('Network error. Try again.'); }
}

// ── Add Employee Modal ────────────────────────────────────────────────────────

const empModal   = document.getElementById('emp-modal');
const addEmpBtn  = document.getElementById('add-emp-btn');
const addEmpForm = document.getElementById('add-emp-form');
const empFormErr = document.getElementById('emp-form-error');

function openEmpModal() {
  addEmpForm.reset();
  empFormErr.classList.add('hidden');
  empModal.classList.remove('hidden');
  document.getElementById('emp-field-id').focus();
}
function closeEmpModal() { empModal.classList.add('hidden'); }

addEmpBtn?.addEventListener('click', openEmpModal);
document.getElementById('modal-close')?.addEventListener('click', closeEmpModal);
document.getElementById('modal-cancel')?.addEventListener('click', closeEmpModal);
empModal?.addEventListener('click', e => { if (e.target === empModal) closeEmpModal(); });

addEmpForm?.addEventListener('submit', async e => {
  e.preventDefault();
  empFormErr.classList.add('hidden');

  const submitBtn  = document.getElementById('emp-submit-btn');
  const submitText = document.getElementById('emp-submit-text');
  const spinner    = document.getElementById('emp-submit-spinner');
  submitBtn.disabled = true;
  submitText.textContent = 'Creating…';
  spinner.classList.remove('hidden');

  const payload = {
    employee_id: document.getElementById('emp-field-id').value.trim().toUpperCase(),
    name:        document.getElementById('emp-field-name').value.trim(),
    email:       document.getElementById('emp-field-email').value.trim(),
    password:    document.getElementById('emp-field-password').value,
    department:  document.getElementById('emp-field-dept').value.trim(),
    position:    document.getElementById('emp-field-position').value.trim(),
    is_admin:    document.getElementById('emp-field-is-admin').checked,
  };

  try {
    const res = await fetch(`${API}/api/v1/admin/employees`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      empFormErr.textContent = data.detail || 'Failed to create employee';
      empFormErr.classList.remove('hidden');
    } else {
      closeEmpModal();
      loadEmployees();
    }
  } catch {
    empFormErr.textContent = 'Network error. Please try again.';
    empFormErr.classList.remove('hidden');
  } finally {
    submitBtn.disabled = false;
    submitText.textContent = 'Create Employee';
    spinner.classList.add('hidden');
  }
});

// ── Initialise ────────────────────────────────────────────────────────────────

(function init() {
  const auth = loadAuth();
  if (auth && auth.access_token) {
    initChatUI(auth);
  } else {
    showPage('login-page');
  }
})();
