/**
 * notes.js — Notes panel in PDF viewer
 */

const NotesModule = (() => {
  let currentDocId = null;
  let editingNoteId = null;

  async function loadNotes(docId) {
    currentDocId = docId;
    const list = document.getElementById('notes-list');
    list.innerHTML = '<div class="panel-hint">Loading…</div>';

    try {
      const data = await API.notes.list(docId);
      const notes = data.notes;
      if (!notes.length) {
        list.innerHTML = `
          <div class="empty-state-sm">
            <i data-lucide="sticky-note"></i>
            <p>No notes yet. Click "New Note" to add one.</p>
          </div>`;
        lucide.createIcons({ nodes: [list] });
        return;
      }
      list.innerHTML = notes.map(n => renderNote(n)).join('');
      lucide.createIcons({ nodes: [list] });
      attachNoteActions(list);
    } catch (e) {
      list.innerHTML = `<div class="panel-hint" style="color:var(--danger)">Failed to load notes</div>`;
    }
  }

  function renderNote(note) {
    return `
      <div class="note-item" data-note-id="${note.id}">
        <div class="note-item-header">
          <span class="note-item-title">${escapeHtml(note.title || 'Untitled Note')}</span>
          <div style="display:flex;align-items:center;gap:6px">
            ${note.page_number ? `<span class="note-item-page">Pg. ${note.page_number}</span>` : ''}
            <div class="note-item-actions">
              <button class="icon-btn" data-action="edit" title="Edit"><i data-lucide="pencil"></i></button>
              <button class="icon-btn" data-action="delete" title="Delete" style="color:var(--danger)"><i data-lucide="trash-2"></i></button>
            </div>
          </div>
        </div>
        <p class="note-item-content">${escapeHtml(note.content)}</p>
        <div style="font-size:0.72rem;color:var(--text-muted);margin-top:6px">
          ${formatRelative(note.updated_at)}
        </div>
      </div>`;
  }

  function attachNoteActions(container) {
    container.querySelectorAll('[data-action="edit"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const noteId = btn.closest('[data-note-id]').dataset.noteId;
        openNoteEditor(noteId);
      });
    });
    container.querySelectorAll('[data-action="delete"]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const item = btn.closest('[data-note-id]');
        const noteId = item.dataset.noteId;
        if (await showConfirm('Delete note', 'Delete this note?')) {
          try {
            await API.notes.delete(noteId);
            item.remove();
            showToast('Note deleted', 'success');
          } catch (err) {
            showToast(err.message || 'Delete failed', 'error');
          }
        }
      });
    });
  }

  function openNoteEditor(noteId = null) {
    editingNoteId = noteId;
    const editor = document.getElementById('note-editor');
    const titleInput = document.getElementById('note-title-input');
    const contentInput = document.getElementById('note-content-input');

    if (noteId) {
      // Find existing note content
      const noteItem = document.querySelector(`[data-note-id="${noteId}"]`);
      titleInput.value = noteItem?.querySelector('.note-item-title')?.textContent || '';
      contentInput.value = noteItem?.querySelector('.note-item-content')?.textContent || '';
    } else {
      titleInput.value = '';
      contentInput.value = '';
      // Pre-fill current page
      const currentPage = PDFViewer.getCurrentPage();
      if (currentPage) titleInput.placeholder = `Note for page ${currentPage}`;
    }

    editor.classList.remove('hidden');
    contentInput.focus();
  }

  function closeNoteEditor() {
    editingNoteId = null;
    document.getElementById('note-editor').classList.add('hidden');
    document.getElementById('note-title-input').value = '';
    document.getElementById('note-content-input').value = '';
  }

  async function saveNote() {
    const title = document.getElementById('note-title-input').value.trim();
    const content = document.getElementById('note-content-input').value.trim();

    if (!content) { showToast('Note content cannot be empty', 'warn'); return; }

    const saveBtn = document.getElementById('note-save-btn');
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving…';

    try {
      if (editingNoteId) {
        await API.notes.update(editingNoteId, { title, content });
        showToast('Note updated', 'success');
      } else {
        const pageNum = PDFViewer.getCurrentPage();
        await API.notes.create({
          document_id: currentDocId || null,
          page_number: pageNum || null,
          title: title || null,
          content,
        });
        showToast('Note saved', 'success');
      }
      closeNoteEditor();
      loadNotes(currentDocId);
    } catch (err) {
      showToast(err.message || 'Save failed', 'error');
    }

    saveBtn.disabled = false;
    saveBtn.textContent = 'Save Note';
  }

  function initControls() {
    document.getElementById('new-note-btn')?.addEventListener('click', () => openNoteEditor(null));
    document.getElementById('note-save-btn')?.addEventListener('click', saveNote);
    document.getElementById('note-cancel-btn')?.addEventListener('click', closeNoteEditor);
  }

  return { loadNotes, initControls };
})();

window.NotesModule = NotesModule;

