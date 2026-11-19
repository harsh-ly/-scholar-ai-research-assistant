/**
 * library.js — Research Library page
 */

const LibraryModule = (() => {
  let allDocs = [];
  let isListView = false;

  async function onEnter() {
    await refresh();
  }

  async function refresh() {
    const container = document.getElementById('library-docs');
    container.innerHTML = renderSkeletons(6);

    try {
      const searchVal = document.getElementById('library-search')?.value.trim() || '';
      const statusFilter = document.getElementById('library-status-filter')?.value || '';
      const sortBy = document.getElementById('library-sort')?.value || 'created_at';

      const params = { sort_by: sortBy, order: 'desc' };
      if (searchVal) params.search = searchVal;
      if (statusFilter) params.status = statusFilter;

      const data = await API.documents.list(params);
      allDocs = data.documents;

      renderDocuments(allDocs);
      DocumentsModule.pollProcessingDocs(allDocs);
      updateSidebarPapers();
    } catch (err) {
      container.innerHTML = `
        <div class="error-state" style="grid-column:1/-1">
          <i data-lucide="alert-circle"></i>
          <h3>Failed to load library</h3>
          <p>${escapeHtml(err.message)}</p>
          <button class="btn btn-ghost btn-sm" onclick="LibraryModule.refresh()">Retry</button>
        </div>`;
      lucide.createIcons({ nodes: [container] });
    }
  }

  function renderDocuments(docs) {
    const container = document.getElementById('library-docs');
    if (!docs.length) {
      container.innerHTML = DocumentsModule.renderEmptyLibrary();
      lucide.createIcons({ nodes: [container] });
      return;
    }

    if (isListView) {
      container.className = 'doc-grid list-view';
    } else {
      container.className = 'doc-grid';
    }

    container.innerHTML = docs.map(d => DocumentsModule.renderDocCard(d, isListView)).join('');
    lucide.createIcons({ nodes: [container] });
    DocumentsModule.attachCardActions(container);
  }

  function renderSkeletons(n) {
    return Array(n).fill(0).map(() => `
      <div class="doc-card" style="cursor:default">
        <div class="skeleton" style="width:36px;height:36px;border-radius:8px"></div>
        <div style="flex:1">
          <div class="skeleton skeleton-title"></div>
          <div class="skeleton skeleton-text" style="width:70%"></div>
        </div>
      </div>`).join('');
  }

  function initControls() {
    document.getElementById('library-search')?.addEventListener('input', debounce(refresh, 400));
    document.getElementById('library-status-filter')?.addEventListener('change', refresh);
    document.getElementById('library-sort')?.addEventListener('change', refresh);

    document.getElementById('view-grid')?.addEventListener('click', () => {
      isListView = false;
      document.getElementById('view-grid').classList.add('active');
      document.getElementById('view-list').classList.remove('active');
      renderDocuments(allDocs);
    });
    document.getElementById('view-list')?.addEventListener('click', () => {
      isListView = true;
      document.getElementById('view-list').classList.add('active');
      document.getElementById('view-grid').classList.remove('active');
      renderDocuments(allDocs);
    });
  }

  function debounce(fn, delay) {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
  }

  return { onEnter, refresh, initControls };
})();

window.LibraryModule = LibraryModule;

