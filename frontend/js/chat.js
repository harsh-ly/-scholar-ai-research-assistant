/**
 * chat.js — AI Chat workspace
 */

const ChatModule = (() => {
  let currentConvId = null;
  let selectedDocIds = [];
  let selectedDocTitles = {};
  let isStreaming = false;
  let pendingRegenerateMsg = null;

  function onEnter() {
    loadConversationList();
  }

  function newConversation() {
    currentConvId = null;
    selectedDocIds = [];
    selectedDocTitles = {};
    document.getElementById('messages-area').innerHTML = `
      <div class="messages-empty" id="messages-empty">
        <i data-lucide="message-circle"></i>
        <p>Ask anything about your research paper</p>
        <p class="hint">Select a paper first, then start your conversation</p>
      </div>`;
    lucide.createIcons();
    document.getElementById('chat-conv-title').textContent = 'New Conversation';
    document.getElementById('chat-doc-indicator').classList.add('hidden');
    document.getElementById('selected-doc-chip').classList.add('hidden');
    document.getElementById('chat-send-btn').disabled = true;
    document.getElementById('chat-input').value = '';
    document.querySelectorAll('.chat-list-item').forEach(el => el.classList.remove('active'));
  }

  async function loadConversationList() {
    const list = document.getElementById('chat-list');
    list.innerHTML = '<div class="panel-hint">Loading…</div>';
    try {
      const data = await API.conversations.list();
      const convs = data.conversations;
      if (!convs.length) {
        list.innerHTML = `<div class="empty-state" style="padding:24px;">
          <i data-lucide="message-square"></i>
          <h3>No conversations yet</h3>
          <p>Upload a paper and start asking questions</p>
        </div>`;
        lucide.createIcons({ nodes: [list] });
        return;
      }
      list.innerHTML = convs.map(c => renderConvItem(c)).join('');
      lucide.createIcons({ nodes: [list] });
      list.querySelectorAll('.chat-list-item').forEach(el => {
        el.addEventListener('click', () => loadConversation(el.dataset.convId));
      });
      list.querySelectorAll('[data-action="delete"]').forEach(el => {
        el.addEventListener('click', async (e) => {
          e.stopPropagation();
          const id = el.closest('[data-conv-id]').dataset.convId;
          if (await showConfirm('Delete conversation', 'This cannot be undone.')) {
            await API.conversations.delete(id);
            if (currentConvId === id) newConversation();
            loadConversationList();
            updateSidebarChats();
          }
        });
      });
      list.querySelectorAll('[data-action="rename"]').forEach(el => {
        el.addEventListener('click', async (e) => {
          e.stopPropagation();
          const id = el.closest('[data-conv-id]').dataset.convId;
          const title = el.closest('.chat-list-item').querySelector('.chat-list-item-title').textContent;
          const newTitle = prompt('Rename conversation:', title);
          if (newTitle && newTitle.trim()) {
            await API.conversations.update(id, { title: newTitle.trim() });
            loadConversationList();
            updateSidebarChats();
            if (currentConvId === id) document.getElementById('chat-conv-title').textContent = newTitle.trim();
          }
        });
      });
    } catch (e) {
      list.innerHTML = `<div class="panel-hint" style="color:var(--danger)">Failed to load conversations</div>`;
    }
  }

  function renderConvItem(c) {
    return `
      <div class="chat-list-item" data-conv-id="${c.id}">
        <div class="chat-list-item-icon"><i data-lucide="message-square"></i></div>
        <div class="chat-list-item-body">
          <p class="chat-list-item-title">${escapeHtml(truncate(c.title, 32))}</p>
          <p class="chat-list-item-meta">${c.message_count} messages · ${formatRelative(c.updated_at)}</p>
        </div>
        <div class="chat-list-item-actions">
          <button class="icon-btn" data-action="rename" title="Rename"><i data-lucide="pencil"></i></button>
          <button class="icon-btn" data-action="delete" title="Delete" style="color:var(--danger)"><i data-lucide="trash-2"></i></button>
        </div>
      </div>`;
  }

  async function loadConversation(convId) {
    currentConvId = convId;
    document.querySelectorAll('.chat-list-item').forEach(el =>
      el.classList.toggle('active', el.dataset.convId === convId));

    const area = document.getElementById('messages-area');
    area.innerHTML = '<div class="panel-hint">Loading…</div>';

    try {
      const data = await API.conversations.get(convId);
      const conv = data.conversation;
      document.getElementById('chat-conv-title').textContent = conv.title;

      // Restore selected documents
      selectedDocIds = conv.document_ids || [];
      updateDocChip();

      area.innerHTML = '';
      if (!conv.messages || !conv.messages.length) {
        area.innerHTML = `<div class="messages-empty"><i data-lucide="message-circle"></i><p>No messages yet. Ask a question!</p></div>`;
        lucide.createIcons({ nodes: [area] });
      } else {
        conv.messages.forEach(m => appendMessage(m));
      }
      area.scrollTop = area.scrollHeight;
    } catch (e) {
      area.innerHTML = `<div class="error-state"><i data-lucide="alert-circle"></i><h3>Failed to load conversation</h3></div>`;
      lucide.createIcons({ nodes: [area] });
    }
  }

  function appendMessage(msg) {
    const area = document.getElementById('messages-area');
    // Remove empty state
    area.querySelector('.messages-empty')?.remove();

    const el = document.createElement('div');
    el.className = `message ${msg.role}`;
    el.dataset.msgId = msg.id;

    const citations = msg.citations || [];
    const followUps = msg.follow_up_questions || [];

    el.innerHTML = `
      <div class="message-avatar">
        ${msg.role === 'user' ? 'U' : '<i data-lucide="graduation-cap"></i>'}
      </div>
      <div class="message-body">
        <div class="message-bubble markdown-body">
          ${msg.role === 'assistant' ? renderMarkdown(msg.content) : escapeHtml(msg.content)}
        </div>
        ${citations.length ? `
          <div class="citations-row">
            ${citations.map((c, i) => `
              <span class="citation-chip" title="Page ${c.page_number}: ${escapeHtml(truncate(c.excerpt || '', 80))}"
                    onclick="handleCitationClick('${c.document_id}', ${c.page_number})">
                <i data-lucide="file-text"></i>
                Pg.${c.page_number}${c.document_title ? ' · ' + escapeHtml(truncate(c.document_title, 20)) : ''}
              </span>
            `).join('')}
          </div>` : ''}
        ${msg.role === 'assistant' && followUps.length ? `
          <div class="follow-ups">
            <p class="follow-up-label">Suggested follow-up questions:</p>
            <div class="follow-up-btns">
              ${followUps.map(q => `<button class="follow-up-btn" onclick="ChatModule.sendFollowUp(this)">${escapeHtml(q)}</button>`).join('')}
            </div>
          </div>` : ''}
        <div class="message-meta">
          <span class="message-time">${formatRelative(msg.created_at)}</span>
          ${msg.role === 'assistant' ? `
            <div class="message-actions">
              <button class="message-action-btn" title="Copy" onclick="copyMessageContent(this)">
                <i data-lucide="copy"></i>
              </button>
              <button class="message-action-btn ${msg.feedback === 'helpful' ? 'active' : ''}" title="Helpful"
                      onclick="sendFeedback('${msg.id}', 'helpful', this)">
                <i data-lucide="thumbs-up"></i>
              </button>
              <button class="message-action-btn ${msg.feedback === 'not_helpful' ? 'active' : ''}" title="Not helpful"
                      onclick="sendFeedback('${msg.id}', 'not_helpful', this)">
                <i data-lucide="thumbs-down"></i>
              </button>
            </div>` : ''}
        </div>
      </div>`;

    area.appendChild(el);
    lucide.createIcons({ nodes: [el] });
    area.scrollTop = area.scrollHeight;
  }

  function appendTypingIndicator() {
    const area = document.getElementById('messages-area');
    const el = document.createElement('div');
    el.className = 'message assistant';
    el.id = 'typing-indicator';
    el.innerHTML = `
      <div class="message-avatar"><i data-lucide="graduation-cap"></i></div>
      <div class="message-body">
        <div class="message-bubble">
          <div class="typing-indicator">
            <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
          </div>
        </div>
      </div>`;
    area.appendChild(el);
    lucide.createIcons({ nodes: [el] });
    area.scrollTop = area.scrollHeight;
    return el;
  }

  async function sendMessage(questionText) {
    if (!questionText.trim() || isStreaming) return;
    if (!selectedDocIds.length) {
      showToast('Please select a research paper first', 'warn');
      openDocSelector();
      return;
    }

    isStreaming = true;
    const sendBtn = document.getElementById('chat-send-btn');
    const input = document.getElementById('chat-input');
    sendBtn.disabled = true;
    input.disabled = true;

    // Append user message locally
    appendMessage({ role: 'user', content: questionText, id: 'local-' + Date.now(), created_at: new Date().toISOString() });

    // Typing indicator
    const typingEl = appendTypingIndicator();
    input.value = '';
    autoResizeTextarea(input);

    try {
      const result = await API.chat.send({
        question: questionText,
        document_ids: selectedDocIds,
        conversation_id: currentConvId,
      });

      typingEl.remove();
      currentConvId = result.conversation_id;

      appendMessage(result.message);
      loadConversationList();
      updateSidebarChats();
    } catch (err) {
      typingEl.remove();
      appendMessage({
        role: 'assistant',
        content: `**Error:** ${err.message || 'Request failed. Please try again.'}`,
        id: 'err-' + Date.now(),
        created_at: new Date().toISOString(),
        citations: [],
        follow_up_questions: [],
      });
      showToast(err.message || 'Chat request failed', 'error');
    }

    isStreaming = false;
    sendBtn.disabled = false;
    input.disabled = false;
    input.focus();
  }

  function sendFollowUp(btn) {
    const q = btn.textContent;
    document.getElementById('chat-input').value = q;
    sendMessage(q);
  }

  function updateDocChip() {
    const chip = document.getElementById('selected-doc-chip');
    const chipName = document.getElementById('selected-doc-chip-name');
    const indicator = document.getElementById('chat-doc-indicator');
    const sendBtn = document.getElementById('chat-send-btn');

    if (selectedDocIds.length) {
      const titles = selectedDocIds.map(id => selectedDocTitles[id] || id).join(', ');
      chip.classList.remove('hidden');
      chipName.textContent = truncate(titles, 45);
      indicator.innerHTML = `<i data-lucide="file-text"></i> ${escapeHtml(truncate(titles, 40))}`;
      indicator.classList.remove('hidden');
      lucide.createIcons({ nodes: [indicator] });
      sendBtn.disabled = false;
    } else {
      chip.classList.add('hidden');
      indicator.classList.add('hidden');
      sendBtn.disabled = true;
    }
  }

  function openDocSelector() {
    const dropdown = document.getElementById('doc-selector-dropdown');
    const btn = document.getElementById('chat-select-doc-btn');

    if (!dropdown.classList.contains('hidden')) {
      dropdown.classList.add('hidden');
      return;
    }

    populateDocSelector();

    // Position near the button
    const rect = btn.getBoundingClientRect();
    dropdown.style.top = (rect.bottom + 8) + 'px';
    dropdown.style.right = (window.innerWidth - rect.right) + 'px';
    dropdown.classList.remove('hidden');

    // Close on outside click
    setTimeout(() => {
      document.addEventListener('click', closeDocSelectorOutside, { once: true });
    }, 100);
  }

  function closeDocSelectorOutside(e) {
    const dropdown = document.getElementById('doc-selector-dropdown');
    if (!dropdown.contains(e.target)) dropdown.classList.add('hidden');
  }

  async function populateDocSelector() {
    const list = document.getElementById('doc-selector-list');
    list.innerHTML = '<div class="panel-hint">Loading…</div>';
    try {
      const data = await API.documents.list({ status: 'ready' });
      const docs = data.documents;
      if (!docs.length) {
        list.innerHTML = '<div class="panel-hint">No ready papers. Upload one first.</div>';
        return;
      }
      list.innerHTML = docs.map(d => `
        <div class="doc-selector-item ${selectedDocIds.includes(d.id) ? 'selected' : ''}" data-doc-id="${d.id}">
          <i data-lucide="file-text"></i>
          <span class="doc-selector-title">${escapeHtml(truncate(d.title, 40))}</span>
          <span class="doc-selector-status" style="color:var(--success)">
            ${selectedDocIds.includes(d.id) ? '✓' : ''}
          </span>
        </div>
      `).join('');
      lucide.createIcons({ nodes: [list] });

      list.querySelectorAll('.doc-selector-item').forEach(item => {
        item.addEventListener('click', () => {
          const docId = item.dataset.docId;
          const doc = docs.find(d => d.id === docId);

          // Single selection for now (could toggle multi-select)
          selectedDocIds = [docId];
          selectedDocTitles[docId] = doc?.title || docId;

          // Load PDF in viewer
          PDFViewer.loadDocument(docId);

          updateDocChip();
          document.getElementById('doc-selector-dropdown').classList.add('hidden');
          showToast(`Selected: ${truncate(doc?.title || docId, 40)}`, 'info');
        });
      });
    } catch (e) {
      list.innerHTML = `<div class="panel-hint" style="color:var(--danger)">Error loading documents</div>`;
    }
  }

  function initComposer() {
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('chat-send-btn');

    input.addEventListener('input', () => {
      autoResizeTextarea(input);
      sendBtn.disabled = !input.value.trim() || !selectedDocIds.length;
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!sendBtn.disabled) sendMessage(input.value.trim());
      }
    });

    sendBtn.addEventListener('click', () => {
      const q = input.value.trim();
      if (q) sendMessage(q);
    });

    document.getElementById('chat-select-doc-btn').addEventListener('click', openDocSelector);
    document.getElementById('composer-attach-btn').addEventListener('click', openDocSelector);

    document.getElementById('clear-doc-chip').addEventListener('click', () => {
      selectedDocIds = [];
      selectedDocTitles = {};
      updateDocChip();
    });

    document.getElementById('upload-from-chat').addEventListener('click', () => {
      document.getElementById('doc-selector-dropdown').classList.add('hidden');
      openUploadModal();
    });

    // Rename conversation on title click
    const titleEl = document.getElementById('chat-conv-title');
    document.getElementById('chat-title-edit').addEventListener('click', () => {
      titleEl.contentEditable = 'true';
      titleEl.focus();
      const range = document.createRange();
      range.selectNodeContents(titleEl);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);
    });
    titleEl.addEventListener('blur', async () => {
      titleEl.contentEditable = 'false';
      const newTitle = titleEl.textContent.trim();
      if (newTitle && currentConvId) {
        try {
          await API.conversations.update(currentConvId, { title: newTitle });
          loadConversationList();
          updateSidebarChats();
        } catch (e) { /* ignore */ }
      }
    });
    titleEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); titleEl.blur(); }
    });

    // Chat new btn
    document.getElementById('chat-new-btn').addEventListener('click', newConversation);
    document.getElementById('chat-back-btn').addEventListener('click', () => {
      const panel = document.getElementById('chat-list-panel');
      panel.classList.toggle('mobile-show');
    });

    // Chat search
    document.getElementById('chat-search').addEventListener('input', (e) => {
      const q = e.target.value.trim().toLowerCase();
      document.querySelectorAll('.chat-list-item').forEach(el => {
        const title = el.querySelector('.chat-list-item-title')?.textContent.toLowerCase() || '';
        el.style.display = title.includes(q) ? '' : 'none';
      });
    });
  }

  function autoResizeTextarea(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 140) + 'px';
  }

  return { onEnter, newConversation, loadConversation, sendFollowUp, initComposer };
})();

window.ChatModule = ChatModule;

// Global helpers (called from inline HTML)
function handleCitationClick(docId, pageNum) {
  if (docId) PDFViewer.loadDocument(docId).then?.(() => {});
  if (pageNum) PDFViewer.jumpToPage(pageNum);
  // Open PDF panel if hidden
  const shell = document.getElementById('app-shell');
  if (shell.classList.contains('pdf-panel-hidden')) togglePdfPanel?.();
}

function copyMessageContent(btn) {
  const bubble = btn.closest('.message-body').querySelector('.message-bubble');
  const text = bubble?.innerText || '';
  navigator.clipboard.writeText(text).then(() => showToast('Copied to clipboard', 'success'));
}

function sendFeedback(msgId, feedback, btn) {
  API.chat.feedback(msgId, feedback).then(() => {
    btn.classList.toggle('active');
    showToast('Feedback recorded', 'success');
  }).catch(() => {});
}

