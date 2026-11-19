/**
 * navigation.js — Page routing, sidebar, keyboard shortcuts
 */

// ── State ──────────────────────────────────────────────────────
let currentPage = 'home';

// ── Init ───────────────────────────────────────────────────────
function initNavigation() {
  // Sidebar toggle
  document.getElementById('sidebar-toggle').addEventListener('click', toggleSidebar);

  // PDF panel toggle
  document.getElementById('pdf-panel-toggle').addEventListener('click', togglePdfPanel);

  // Nav items
  document.querySelectorAll('[data-page]').forEach(el => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      const page = el.dataset.page;
      if (page) navigateTo(page);
    });
  });

  // New Chat btn in sidebar
  document.getElementById('new-chat-btn').addEventListener('click', () => {
    navigateTo('chat');
    if (window.ChatModule) ChatModule.newConversation();
  });
  document.getElementById('home-new-chat-btn').addEventListener('click', () => {
    navigateTo('chat');
    if (window.ChatModule) ChatModule.newConversation();
  });

  // Upload buttons that open modal
  ['home-upload-btn', 'library-upload-btn', 'pdf-upload-btn'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('click', () => openUploadModal());
  });

  // Settings page nav
  document.querySelectorAll('[data-page="settings"]').forEach(el => {
    el.addEventListener('click', (e) => { e.preventDefault(); navigateTo('settings'); });
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', handleKeydown);

  // Mobile sidebar overlay
  document.querySelector('.mobile-overlay')?.addEventListener('click', closeMobileSidebar);
}

function navigateTo(page) {
  // Hide all pages
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  // Show target
  const target = document.getElementById(`page-${page}`);
  if (!target) return;
  target.classList.add('active');
  currentPage = page;

  // Update nav active state
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });

  // Page-specific onEnter hooks
  if (page === 'home')      window.HomeModule?.onEnter();
  if (page === 'library')   window.LibraryModule?.onEnter();
  if (page === 'compare')   window.CompareModule?.onEnter();
  if (page === 'summarize') window.SummarizeModule?.onEnter();
  if (page === 'insights')  window.InsightsModule?.onEnter();
  if (page === 'chat')      window.ChatModule?.onEnter();
  if (page === 'settings')  window.SettingsModule?.onEnter();

  // Close mobile sidebar when navigating
  closeMobileSidebar();
}

function toggleSidebar() {
  document.getElementById('app-shell').classList.toggle('sidebar-collapsed');
  const icon = document.querySelector('#sidebar-toggle i');
  if (icon) {
    const collapsed = document.getElementById('app-shell').classList.contains('sidebar-collapsed');
    icon.setAttribute('data-lucide', collapsed ? 'panel-left-open' : 'panel-left-close');
    lucide.createIcons();
  }
}

function togglePdfPanel() {
  const shell = document.getElementById('app-shell');
  const panel = document.getElementById('pdf-panel');
  const collapsed = shell.classList.toggle('pdf-panel-hidden');
  panel.classList.toggle('panel-open', !collapsed);
  const icon = document.querySelector('#pdf-panel-toggle i');
  if (icon) {
    icon.setAttribute('data-lucide', collapsed ? 'panel-right-open' : 'panel-right-close');
    lucide.createIcons();
  }
}

function openMobileSidebar() {
  document.getElementById('sidebar').classList.add('sidebar-open');
  document.querySelector('.mobile-overlay')?.classList.add('visible');
}

function closeMobileSidebar() {
  document.getElementById('sidebar').classList.remove('sidebar-open');
  document.querySelector('.mobile-overlay')?.classList.remove('visible');
}

function handleKeydown(e) {
  // Ctrl/Cmd + K → new chat
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    navigateTo('chat');
    window.ChatModule?.newConversation();
  }
  // Ctrl/Cmd + U → upload
  if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
    e.preventDefault();
    openUploadModal();
  }
  // Escape → close modals/dropdowns
  if (e.key === 'Escape') {
    closeUploadModal();
    document.getElementById('doc-selector-dropdown')?.classList.add('hidden');
    document.querySelectorAll('.context-menu').forEach(m => m.remove());
  }
}

// ── Upload Modal ────────────────────────────────────────────────
let selectedUploadFile = null;

function openUploadModal() {
  resetUploadModal();
  document.getElementById('upload-modal').classList.remove('hidden');
}

function closeUploadModal() {
  document.getElementById('upload-modal').classList.add('hidden');
  selectedUploadFile = null;
}

function resetUploadModal() {
  selectedUploadFile = null;
  document.getElementById('upload-drop-zone').classList.remove('hidden');
  document.getElementById('upload-preview').classList.add('hidden');
  document.getElementById('upload-progress-wrap').classList.add('hidden');
  document.getElementById('upload-submit-btn').disabled = true;
  document.getElementById('upload-title-input').value = '';
  document.getElementById('upload-file-input').value = '';
  document.getElementById('upload-progress-inner').style.width = '0%';
}

function initUploadModal() {
  const modal = document.getElementById('upload-modal');
  const closeBtn = document.getElementById('upload-modal-close');
  const cancelBtn = document.getElementById('upload-cancel-btn');
  const submitBtn = document.getElementById('upload-submit-btn');
  const dropZone = document.getElementById('upload-drop-zone');
  const fileInput = document.getElementById('upload-file-input');
  const removeBtn = document.getElementById('upload-remove-file');

  closeBtn.addEventListener('click', closeUploadModal);
  cancelBtn.addEventListener('click', closeUploadModal);
  modal.addEventListener('click', (e) => { if (e.target === modal) closeUploadModal(); });

  // Drop zone click
  dropZone.addEventListener('click', () => fileInput.click());

  // Drag and drop
  dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) handleFileSelect(fileInput.files[0]);
  });

  removeBtn.addEventListener('click', resetUploadModal);

  submitBtn.addEventListener('click', handleUploadSubmit);
}

function handleFileSelect(file) {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    showToast('Only PDF files are supported', 'error');
    return;
  }
  if (file.size > 52428800) {
    showToast('File too large. Maximum size is 50MB', 'error');
    return;
  }
  selectedUploadFile = file;
  document.getElementById('upload-drop-zone').classList.add('hidden');
  document.getElementById('upload-preview').classList.remove('hidden');
  document.getElementById('upload-filename').textContent = file.name;
  document.getElementById('upload-filesize').textContent = `${(file.size / (1024 * 1024)).toFixed(2)} MB`;
  document.getElementById('upload-submit-btn').disabled = false;
}

async function handleUploadSubmit() {
  if (!selectedUploadFile) return;
  const submitBtn = document.getElementById('upload-submit-btn');
  const progressWrap = document.getElementById('upload-progress-wrap');
  const progressInner = document.getElementById('upload-progress-inner');
  const progressLabel = document.getElementById('upload-progress-label');

  submitBtn.disabled = true;
  document.getElementById('upload-preview').classList.add('hidden');
  progressWrap.classList.remove('hidden');
  progressLabel.textContent = 'Uploading…';
  progressInner.style.width = '30%';

  const formData = new FormData();
  formData.append('file', selectedUploadFile);
  const customTitle = document.getElementById('upload-title-input').value.trim();
  if (customTitle) formData.append('title', customTitle);

  try {
    progressInner.style.width = '60%';
    const result = await API.documents.upload(formData);
    progressInner.style.width = '100%';
    progressLabel.textContent = 'Processing… This may take a minute.';

    showToast(`"${result.document.title}" uploaded successfully! Processing…`, 'success');

    // Poll for status
    pollDocumentStatus(result.document.id, (statusData) => {
      if (statusData.status === 'processing') {
        progressLabel.textContent = `Processing chunks…`;
      } else if (statusData.status === 'ready') {
        progressLabel.textContent = 'Ready!';
      }
    }).then(() => {
      // Refresh sidebar & relevant pages
      window.HomeModule?.refresh();
      window.LibraryModule?.refresh();
      updateSidebarPapers();
    });

    setTimeout(closeUploadModal, 1500);
  } catch (err) {
    showToast(err.message || 'Upload failed', 'error');
    progressWrap.classList.add('hidden');
    document.getElementById('upload-preview').classList.remove('hidden');
    submitBtn.disabled = false;
  }
}

// ── Sidebar paper/chat lists ────────────────────────────────────
async function updateSidebarPapers() {
  try {
    const data = await API.documents.list({ sort_by: 'created_at', order: 'desc' });
    const container = document.getElementById('sidebar-recent-papers');
    const docs = data.documents.slice(0, 5);
    if (!docs.length) {
      container.innerHTML = '<p class="sidebar-empty-hint">No papers yet</p>';
      return;
    }
    container.innerHTML = docs.map(d => `
      <div class="sidebar-list-item" data-doc-id="${d.id}" onclick="openDocInViewer('${d.id}')">
        <i data-lucide="file-text"></i>
        <span>${escapeHtml(truncate(d.title, 28))}</span>
      </div>
    `).join('');
    lucide.createIcons();
  } catch (e) { /* silent */ }
}

async function updateSidebarChats() {
  try {
    const data = await API.conversations.list();
    const container = document.getElementById('sidebar-recent-chats');
    const convs = data.conversations.slice(0, 5);
    if (!convs.length) {
      container.innerHTML = '<p class="sidebar-empty-hint">No conversations yet</p>';
      return;
    }
    container.innerHTML = convs.map(c => `
      <div class="sidebar-list-item" onclick="openConversation('${c.id}')">
        <i data-lucide="message-square"></i>
        <span>${escapeHtml(truncate(c.title, 26))}</span>
      </div>
    `).join('');
    lucide.createIcons();
  } catch (e) { /* silent */ }
}

function openDocInViewer(docId) {
  navigateTo('chat');
  window.PDFViewer?.loadDocument(docId);
}

function openConversation(convId) {
  navigateTo('chat');
  window.ChatModule?.loadConversation(convId);
}

// ── Toast ───────────────────────────────────────────────────────
function showToast(message, type = 'info', duration = 4000) {
  const container = document.getElementById('toast-container');
  const icons = { success: 'check-circle', error: 'alert-circle', warn: 'alert-triangle', info: 'info' };
  const icon = icons[type] || 'info';

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<i data-lucide="${icon}"></i><span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);
  lucide.createIcons({ nodes: [toast] });

  setTimeout(() => {
    toast.classList.add('fade-out');
    toast.addEventListener('animationend', () => toast.remove());
  }, duration);
}

// ── Confirm Dialog ──────────────────────────────────────────────
function showConfirm(title, message) {
  return new Promise((resolve) => {
    const dialog = document.getElementById('confirm-dialog');
    document.getElementById('confirm-title').textContent = title;
    document.getElementById('confirm-message').textContent = message;
    dialog.classList.remove('hidden');

    function cleanup(result) {
      dialog.classList.add('hidden');
      okBtn.removeEventListener('click', onOk);
      cancelBtn.removeEventListener('click', onCancel);
      resolve(result);
    }
    const okBtn = document.getElementById('confirm-ok');
    const cancelBtn = document.getElementById('confirm-cancel');
    function onOk() { cleanup(true); }
    function onCancel() { cleanup(false); }
    okBtn.addEventListener('click', onOk);
    cancelBtn.addEventListener('click', onCancel);
    dialog.addEventListener('click', (e) => { if (e.target === dialog) cleanup(false); }, { once: true });
  });
}

// ── Utilities ───────────────────────────────────────────────────
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function truncate(str, maxLen) {
  if (!str) return '';
  return str.length > maxLen ? str.slice(0, maxLen) + '…' : str;
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatRelative(iso) {
  if (!iso) return '';
  const now = Date.now();
  const then = new Date(iso).getTime();
  const diff = Math.floor((now - then) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
  return formatDate(iso);
}

function renderMarkdown(text) {
  if (!text) return '';
  if (typeof marked === 'undefined') return `<p>${escapeHtml(text)}</p>`;
  const html = marked.parse(text);
  return typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(html) : html;
}

function getStatusBadge(status) {
  const map = {
    ready: '<span class="badge badge-success">Ready</span>',
    processing: '<span class="badge badge-warn">Processing</span>',
    uploaded: '<span class="badge badge-info">Uploaded</span>',
    failed: '<span class="badge badge-danger">Failed</span>',
  };
  return map[status] || `<span class="badge">${status}</span>`;
}

