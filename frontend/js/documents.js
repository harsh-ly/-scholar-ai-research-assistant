/**
 * documents.js — Document card rendering & upload helpers
 */

const DocumentsModule = (() => {

  function renderDocCard(doc, isListView = false) {
    const statusDot = `<span class="status-dot ${doc.status}"></span>`;
    return `
      <div class="doc-card ${isListView ? 'list-view' : ''}" data-doc-id="${doc.id}">
        <div class="doc-card-icon"><i data-lucide="file-text"></i></div>
        <div class="doc-card-body">
          <p class="doc-card-title">${escapeHtml(doc.title)}</p>
          <p class="doc-card-meta">
            ${doc.authors ? escapeHtml(truncate(doc.authors, 40)) + ' · ' : ''}
            ${doc.publication_year || ''}
            ${doc.total_pages ? ' · ' + doc.total_pages + ' pp' : ''}
          </p>
        </div>
        <div class="doc-card-footer">
          <div class="doc-card-badges">
            ${statusDot} <span style="font-size:0.78rem;color:var(--text-muted)">${doc.status}</span>
            ${doc.chunk_count ? `<span class="badge badge-accent">${doc.chunk_count} chunks</span>` : ''}
          </div>
          <div class="doc-card-actions">
            ${doc.status === 'failed' ? `
              <button class="icon-btn" data-action="retry" title="Retry processing" style="color:var(--warning)">
                <i data-lucide="refresh-cw"></i>
              </button>` : ''}
            ${doc.status === 'ready' ? `
              <button class="icon-btn" data-action="open" title="Open in viewer">
                <i data-lucide="eye"></i>
              </button>
              <button class="icon-btn" data-action="chat" title="Chat about this paper">
                <i data-lucide="message-square"></i>
              </button>` : ''}
            <button class="icon-btn" data-action="delete" title="Delete" style="color:var(--danger)">
              <i data-lucide="trash-2"></i>
            </button>
          </div>
        </div>
        <div style="font-size:0.72rem;color:var(--text-muted);margin-top:4px">
          Added ${formatRelative(doc.created_at)}
        </div>
      </div>`;
  }

  function attachCardActions(container) {
    container.querySelectorAll('[data-action="open"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const docId = btn.closest('[data-doc-id]').dataset.docId;
        PDFViewer.loadDocument(docId);
        // Open pdf panel if collapsed
        const shell = document.getElementById('app-shell');
        if (shell.classList.contains('pdf-panel-hidden')) togglePdfPanel();
      });
    });

    container.querySelectorAll('[data-action="chat"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const docId = btn.closest('[data-doc-id]').dataset.docId;
        navigateTo('chat');
        // Auto-select doc
        ChatModule.newConversation();
        PDFViewer.loadDocument(docId);
      });
    });

    container.querySelectorAll('[data-action="delete"]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const card = btn.closest('[data-doc-id]');
        const docId = card.dataset.docId;
        const title = card.querySelector('.doc-card-title')?.textContent || 'this document';
        if (await showConfirm('Delete document', `Delete "${title}"? This cannot be undone.`)) {
          try {
            await API.documents.delete(docId);
            showToast('Document deleted', 'success');
            card.remove();
            window.HomeModule?.refresh();
            updateSidebarPapers();
          } catch (err) {
            showToast(err.message || 'Delete failed', 'error');
          }
        }
      });
    });

    container.querySelectorAll('[data-action="retry"]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const docId = btn.closest('[data-doc-id]').dataset.docId;
        try {
          await API.documents.retry(docId);
          showToast('Processing restarted', 'success');
          window.LibraryModule?.refresh();
        } catch (err) {
          showToast(err.message || 'Retry failed', 'error');
        }
      });
    });

    // Card click → open PDF
    container.querySelectorAll('.doc-card').forEach(card => {
      card.addEventListener('click', () => {
        const docId = card.dataset.docId;
        const doc = { status: card.querySelector('.status-dot')?.classList[1] };
        if (doc.status === 'ready') {
          PDFViewer.loadDocument(docId);
          const shell = document.getElementById('app-shell');
          if (shell.classList.contains('pdf-panel-hidden')) togglePdfPanel();
        }
      });
    });
  }

  function renderEmptyLibrary() {
    return `
      <div class="empty-state" style="grid-column:1/-1">
        <i data-lucide="file-plus"></i>
        <h3>No research papers yet</h3>
        <p>Upload your first PDF to get started with Scholar AI</p>
        <button class="btn btn-primary" onclick="openUploadModal()">
          <i data-lucide="upload"></i> Upload Paper
        </button>
      </div>`;
  }

  // Poll all processing documents for status updates
  async function pollProcessingDocs(docs) {
    const processing = docs.filter(d => d.status === 'processing' || d.status === 'uploaded');
    for (const doc of processing) {
      pollDocumentStatus(doc.id, (status) => {
        const card = document.querySelector(`[data-doc-id="${doc.id}"]`);
        if (card) {
          const dot = card.querySelector('.status-dot');
          if (dot) { dot.className = `status-dot ${status.status}`; }
          if (status.status === 'ready' || status.status === 'failed') {
            window.LibraryModule?.refresh();
          }
        }
      });
    }
  }

  return { renderDocCard, attachCardActions, renderEmptyLibrary, pollProcessingDocs };
})();

window.DocumentsModule = DocumentsModule;

