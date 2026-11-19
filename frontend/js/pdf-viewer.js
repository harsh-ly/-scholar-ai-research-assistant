/**
 * pdf-viewer.js — PDF rendering using PDF.js
 */

const PDFViewer = (() => {
  let pdfDoc = null;
  let currentPage = 1;
  let totalPages = 0;
  let scale = 1.4;
  let rendering = false;
  let currentDocId = null;
  let currentDocData = null;

  const canvas = document.getElementById('pdf-canvas');
  const ctx = canvas?.getContext('2d');
  const emptyState = document.getElementById('pdf-empty-state');
  const pdfLoading = document.getElementById('pdf-loading');
  const pdfPageInput = document.getElementById('pdf-page-input');
  const totalPagesEl = document.getElementById('pdf-total-pages');

  function showLoading() {
    canvas?.classList.add('hidden');
    emptyState?.classList.add('hidden');
    pdfLoading?.classList.remove('hidden');
  }

  function showCanvas() {
    canvas?.classList.remove('hidden');
    emptyState?.classList.add('hidden');
    pdfLoading?.classList.add('hidden');
  }

  function showEmpty() {
    canvas?.classList.add('hidden');
    emptyState?.classList.remove('hidden');
    pdfLoading?.classList.add('hidden');
  }

  async function loadDocument(docId) {
    if (!docId) { showEmpty(); return; }

    currentDocId = docId;

    // Fetch document metadata
    try {
      const data = await API.documents.get(docId);
      currentDocData = data.document;
      updatePaperOverview(currentDocData);

      if (data.document.status !== 'ready') {
        showEmpty();
        emptyState.querySelector('p').textContent = `Document status: ${data.document.status}`;
        return;
      }
    } catch (e) {
      showEmpty();
      return;
    }

    // Load PDF via PDF.js
    showLoading();
    const pdfUrl = API.documents.pdfUrl(docId);

    try {
      pdfDoc = await pdfjsLib.getDocument(pdfUrl).promise;
      totalPages = pdfDoc.numPages;
      currentPage = 1;
      totalPagesEl.textContent = totalPages;
      updatePageInput();
      updateNavButtons();
      await renderPage(currentPage);
      showCanvas();
    } catch (err) {
      showEmpty();
      emptyState.querySelector('p').textContent = 'Failed to load PDF.';
      console.error('PDF load error:', err);
    }
  }

  async function renderPage(pageNum) {
    if (!pdfDoc || rendering) return;
    rendering = true;

    try {
      const page = await pdfDoc.getPage(pageNum);
      const container = document.getElementById('pdf-canvas-container');
      const containerWidth = container?.clientWidth - 24 || 300;

      // Fit-to-container scale
      const viewport = page.getViewport({ scale: 1.0 });
      const fitScale = Math.min(scale, containerWidth / viewport.width);
      const scaledViewport = page.getViewport({ scale: fitScale });

      canvas.width = scaledViewport.width;
      canvas.height = scaledViewport.height;

      await page.render({ canvasContext: ctx, viewport: scaledViewport }).promise;

      currentPage = pageNum;
      updatePageInput();
      updateNavButtons();
    } catch (err) {
      console.error('Page render error:', err);
    }
    rendering = false;
  }

  function updatePageInput() {
    if (pdfPageInput) pdfPageInput.value = currentPage;
  }

  function updateNavButtons() {
    const prevBtn = document.getElementById('pdf-prev');
    const nextBtn = document.getElementById('pdf-next');
    if (prevBtn) prevBtn.disabled = currentPage <= 1 || !pdfDoc;
    if (nextBtn) nextBtn.disabled = currentPage >= totalPages || !pdfDoc;
  }

  function updatePaperOverview(doc) {
    const container = document.getElementById('pdf-paper-overview');
    if (!container || !doc) return;

    container.innerHTML = `
      <div class="paper-overview-card">
        <p class="paper-overview-title">${escapeHtml(doc.title)}</p>
        <div class="paper-overview-meta">
          ${doc.authors ? `<span class="paper-meta-badge">${escapeHtml(truncate(doc.authors, 40))}</span>` : ''}
          ${doc.publication_year ? `<span class="paper-meta-badge">${doc.publication_year}</span>` : ''}
          ${doc.total_pages ? `<span class="paper-meta-badge">${doc.total_pages} pages</span>` : ''}
          ${doc.research_area ? `<span class="paper-meta-badge">${escapeHtml(doc.research_area)}</span>` : ''}
          <span class="paper-status-badge ${doc.status}">${doc.status}</span>
        </div>
        ${doc.abstract ? `<p style="font-size:0.78rem;color:var(--text-muted);margin-top:6px;line-height:1.5;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;">${escapeHtml(doc.abstract)}</p>` : ''}
        <div class="paper-overview-actions">
          <button class="btn btn-ghost btn-xs" onclick="navigateTo('summarize')">
            <i data-lucide="file-text"></i> Summarize
          </button>
          <button class="btn btn-ghost btn-xs" onclick="navigateTo('insights')">
            <i data-lucide="lightbulb"></i> Insights
          </button>
        </div>
      </div>
    `;
    lucide.createIcons();
  }

  function jumpToPage(pageNum) {
    if (!pdfDoc) return;
    const p = Math.max(1, Math.min(totalPages, parseInt(pageNum) || 1));
    renderPage(p).then(showCanvas);
  }

  function initControls() {
    document.getElementById('pdf-prev')?.addEventListener('click', () => {
      if (currentPage > 1) renderPage(currentPage - 1).then(showCanvas);
    });
    document.getElementById('pdf-next')?.addEventListener('click', () => {
      if (currentPage < totalPages) renderPage(currentPage + 1).then(showCanvas);
    });
    document.getElementById('pdf-zoom-in')?.addEventListener('click', () => {
      scale = Math.min(scale + 0.2, 3.0);
      updateZoomLabel();
      if (pdfDoc) renderPage(currentPage).then(showCanvas);
    });
    document.getElementById('pdf-zoom-out')?.addEventListener('click', () => {
      scale = Math.max(scale - 0.2, 0.5);
      updateZoomLabel();
      if (pdfDoc) renderPage(currentPage).then(showCanvas);
    });
    document.getElementById('pdf-fit-width')?.addEventListener('click', () => {
      scale = 1.4;
      updateZoomLabel();
      if (pdfDoc) renderPage(currentPage).then(showCanvas);
    });
    pdfPageInput?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') jumpToPage(pdfPageInput.value);
    });
    pdfPageInput?.addEventListener('blur', () => jumpToPage(pdfPageInput.value));

    // PDF tab in panel
    document.querySelectorAll('.pdf-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.pdf-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.pdf-tab-content').forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        const tabId = `pdf-tab-${tab.dataset.tab}`;
        document.getElementById(tabId)?.classList.add('active');
      });
    });
  }

  function updateZoomLabel() {
    document.getElementById('pdf-zoom-level').textContent = `${Math.round(scale * 100)}%`;
  }

  function getCurrentDocId() { return currentDocId; }
  function getCurrentPage() { return currentPage; }

  // public API
  return { loadDocument, jumpToPage, initControls, getCurrentDocId, getCurrentPage };
})();

window.PDFViewer = PDFViewer;

