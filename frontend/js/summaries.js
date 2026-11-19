/**
 * summaries.js — Paper summarization page
 */

const SummarizeModule = (() => {
  let currentSummary = null;
  let currentDocId = null;

  async function onEnter(preselectDocId = null) {
    await loadDocumentOptions(preselectDocId);
  }

  async function loadDocumentOptions(preselectDocId = null) {
    const select = document.getElementById('summarize-doc-select');
    if (!select) return;
    const targetDocId = preselectDocId || select.value || (window.PDFViewer ? window.PDFViewer.getCurrentDocId() : null);
    select.innerHTML = '<option value="">Loading papers…</option>';
    try {
      const data = await API.documents.list({ status: 'ready' });
      const docs = data.documents;
      if (!docs.length) {
        select.innerHTML = '<option value="">No ready papers available</option>';
        return;
      }
      select.innerHTML = '<option value="">Select a paper…</option>' +
        docs.map(d => `<option value="${d.id}" ${d.id === targetDocId ? 'selected' : ''}>${escapeHtml(truncate(d.title, 70))}</option>`).join('');
    } catch (e) {
      select.innerHTML = '<option value="">Failed to load papers</option>';
    }
  }

  async function generateSummary(regenerate = false) {
    const docId = document.getElementById('summarize-doc-select').value;
    const type = document.getElementById('summarize-type').value;

    if (!docId) {
      showToast('Please select a paper', 'warn');
      return;
    }

    currentDocId = docId;

    const loading = document.getElementById('summarize-loading');
    const results = document.getElementById('summarize-results');
    const runBtn = document.getElementById('summarize-run-btn');

    loading.classList.remove('hidden');
    results.classList.add('hidden');
    runBtn.disabled = true;

    try {
      const data = await API.research.summary(docId, { summary_type: type, regenerate });
      currentSummary = data.summary;

      // Get document title
      const docSelect = document.getElementById('summarize-doc-select');
      const docTitle = docSelect.options[docSelect.selectedIndex]?.text || 'Document';
      document.getElementById('summarize-doc-title').textContent = docTitle;

      renderSummary(data.summary);
      results.classList.remove('hidden');
    } catch (err) {
      showToast(err.message || 'Summary generation failed', 'error');
    }

    loading.classList.add('hidden');
    runBtn.disabled = false;
  }

  function renderSummary(summary) {
    const container = document.getElementById('summarize-content');

    if (summary.structured_data) {
      const sd = summary.structured_data;
      const sectionLabels = {
        executive_summary: 'Executive Summary',
        abstract_summary: 'Abstract',
        research_objectives: 'Research Objectives',
        methodology: 'Methodology',
        dataset: 'Dataset',
        experimental_setup: 'Experimental Setup',
        main_findings: 'Main Findings',
        key_contributions: 'Key Contributions',
        limitations: 'Limitations',
        conclusion: 'Conclusion',
        future_work: 'Future Research Directions',
      };

      let html = '';
      for (const [key, label] of Object.entries(sectionLabels)) {
        const val = sd[key];
        if (val && val.trim()) {
          html += `<h2>${label}</h2>${renderMarkdown(val)}<hr>`;
        }
      }
      container.innerHTML = html || renderMarkdown(summary.content);
    } else {
      container.innerHTML = renderMarkdown(summary.content);
    }
  }

  function copySummary() {
    const content = document.getElementById('summarize-content')?.innerText || '';
    navigator.clipboard.writeText(content).then(() => showToast('Summary copied', 'success'));
  }

  async function downloadSummary() {
    if (!currentSummary?.id) { showToast('Generate a summary first', 'warn'); return; }
    try {
      const response = await fetch(`${API_BASE}/exports`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'summary', resource_id: currentSummary.id }),
      });
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'summary.md'; a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      showToast('Download failed', 'error');
    }
  }

  function initControls() {
    document.getElementById('summarize-run-btn')?.addEventListener('click', () => generateSummary(false));
    document.getElementById('summarize-regen-btn')?.addEventListener('click', () => generateSummary(true));
    document.getElementById('summarize-copy-btn')?.addEventListener('click', copySummary);
    document.getElementById('summarize-download-btn')?.addEventListener('click', downloadSummary);
  }

  return { onEnter, initControls, loadDocumentOptions };
})();

window.SummarizeModule = SummarizeModule;

