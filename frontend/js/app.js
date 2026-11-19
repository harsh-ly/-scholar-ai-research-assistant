/**
 * app.js — Main application entry point
 * Initializes all modules and bootstraps Scholar AI.
 */

// ── Home Module ────────────────────────────────────────────────
const HomeModule = (() => {
  async function onEnter() {
    await refresh();
  }

  async function refresh() {
    await Promise.all([loadStats(), loadRecentPapers(), loadRecentChats()]);
  }

  async function loadStats() {
    try {
      const data = await API.research.stats();
      document.getElementById('stat-docs').textContent = data.total_documents;
      document.getElementById('stat-chats').textContent = data.total_conversations;
      document.getElementById('stat-notes').textContent = data.total_notes;
      document.getElementById('stat-chunks').textContent = data.total_chunks?.toLocaleString() || '0';
    } catch (e) { /* silent — backend may be starting */ }
  }

  async function loadRecentPapers() {
    const container = document.getElementById('home-recent-papers');
    try {
      const data = await API.documents.list({ sort_by: 'created_at', order: 'desc' });
      const docs = data.documents.slice(0, 4);
      if (!docs.length) {
        container.innerHTML = `
          <div class="empty-state-sm">
            <i data-lucide="file-plus"></i>
            <p>Upload your first research paper to get started</p>
          </div>`;
        lucide.createIcons({ nodes: [container] });
        return;
      }
      container.innerHTML = docs.map(d => `
        <div class="home-doc-item" onclick="openDocInViewer('${d.id}')">
          <i data-lucide="file-text"></i>
          <span class="home-item-title">${escapeHtml(truncate(d.title, 40))}</span>
          <span class="home-item-meta"><span class="status-dot ${d.status}"></span>${formatRelative(d.created_at)}</span>
        </div>
      `).join('');
      lucide.createIcons({ nodes: [container] });
    } catch (e) { /* silent */ }
  }

  async function loadRecentChats() {
    const container = document.getElementById('home-recent-chats');
    try {
      const data = await API.conversations.list();
      const convs = data.conversations.slice(0, 4);
      if (!convs.length) {
        container.innerHTML = `
          <div class="empty-state-sm">
            <i data-lucide="message-square-plus"></i>
            <p>Start a conversation about your research papers</p>
          </div>`;
        lucide.createIcons({ nodes: [container] });
        return;
      }
      container.innerHTML = convs.map(c => `
        <div class="home-chat-item" onclick="openConversation('${c.id}')">
          <i data-lucide="message-square"></i>
          <span class="home-item-title">${escapeHtml(truncate(c.title, 40))}</span>
          <span class="home-item-meta">${formatRelative(c.updated_at)}</span>
        </div>
      `).join('');
      lucide.createIcons({ nodes: [container] });
    } catch (e) { /* silent */ }
  }

  return { onEnter, refresh };
})();

window.HomeModule = HomeModule;

// ── Bootstrap ──────────────────────────────────────────────────
async function bootstrap() {
  // Initialize Lucide icons
  lucide.createIcons();

  // Apply saved theme
  const theme = localStorage.getItem('scholar-theme') || 'dark';
  if (theme === 'light') document.documentElement.setAttribute('data-theme', 'light');

  // Add mobile header (hamburger menu)
  const mainContent = document.getElementById('main-content');
  const mobileHeader = document.createElement('div');
  mobileHeader.className = 'mobile-header';
  mobileHeader.innerHTML = `
    <button class="icon-btn mobile-menu-btn" id="mobile-menu-btn">
      <i data-lucide="menu"></i>
    </button>
    <div class="brand">
      <div class="brand-logo"><i data-lucide="graduation-cap"></i></div>
      <span class="brand-name">Scholar AI</span>
    </div>
    <button class="icon-btn" onclick="openUploadModal()" title="Upload paper">
      <i data-lucide="upload"></i>
    </button>
  `;
  mainContent.insertBefore(mobileHeader, mainContent.firstChild);
  lucide.createIcons();

  document.getElementById('mobile-menu-btn')?.addEventListener('click', openMobileSidebar);

  // Add mobile overlay
  const overlay = document.createElement('div');
  overlay.className = 'mobile-overlay';
  overlay.id = 'mobile-overlay';
  document.body.appendChild(overlay);
  overlay.addEventListener('click', closeMobileSidebar);

  // Initialize all modules
  initNavigation();
  initUploadModal();
  PDFViewer.initControls();
  ChatModule.initComposer();
  LibraryModule.initControls();
  CompareModule.initControls();
  SummarizeModule.initControls();
  InsightsModule.initControls();
  NotesModule.initControls();
  SettingsModule.initControls();

  // Preload document options for tools
  SummarizeModule.loadDocumentOptions?.();
  InsightsModule.loadDocumentOptions?.();

  // Load sidebar data
  await Promise.all([
    updateSidebarPapers(),
    updateSidebarChats(),
  ]);

  // Navigate to home
  navigateTo('home');

  // Check backend connectivity
  checkBackendHealth();

  // Set up view-all buttons in home
  document.querySelectorAll('[data-page]').forEach(btn => {
    if (btn.tagName === 'BUTTON') {
      btn.addEventListener('click', (e) => {
        const page = btn.dataset.page;
        if (page) { e.preventDefault(); navigateTo(page); }
      });
    }
  });

  console.log('%c🎓 Scholar AI Ready', 'color:#8B7CFF;font-weight:bold;font-size:14px');
}

async function checkBackendHealth() {
  try {
    await API.health.check();
  } catch (e) {
    showToast(
      'Cannot reach backend. Run: cd backend && python run.py',
      'error',
      8000
    );
  }
}

// ── Global resize handler ────────────────────────────────────
window.addEventListener('resize', () => {
  // Close mobile sidebar on resize to desktop
  if (window.innerWidth > 768) closeMobileSidebar();
});

// ── DOMContentLoaded ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', bootstrap);

