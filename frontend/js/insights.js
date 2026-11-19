/**
 * insights.js — Research Insights page & PDF panel insights tab
 */

const InsightsModule = (() => {
  let currentInsight = null;

  async function onEnter(preselectDocId = null) {
    await loadDocumentOptions(preselectDocId);
  }

  async function loadDocumentOptions(preselectDocId = null) {
    const select = document.getElementById('insights-doc-select');
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

  async function generateInsights(docId) {
    if (!docId) {
      showToast('Please select a paper', 'warn');
      return;
    }

    const loading = document.getElementById('insights-loading');
    const results = document.getElementById('insights-results');
    const runBtn = document.getElementById('insights-run-btn');

    loading.classList.remove('hidden');
    results.classList.add('hidden');
    if (runBtn) runBtn.disabled = true;

    try {
      const data = await API.research.generateInsights(docId);
      currentInsight = data.insight;
      renderInsights(data.insight, results);
      results.classList.remove('hidden');
    } catch (err) {
      showToast(err.message || 'Insights generation failed', 'error');
    }

    loading.classList.add('hidden');
    if (runBtn) runBtn.disabled = false;
  }

  function renderInsights(insight, container) {
    const sd = insight?.structured_data;
    if (!sd) {
      container.innerHTML = `<div class="markdown-body">${renderMarkdown(insight?.content || 'No insights available.')}</div>`;
      return;
    }

    const sections = [
      { key: 'research_themes', label: 'Research Themes', icon: 'layers', type: 'tags' },
      { key: 'key_concepts', label: 'Key Concepts', icon: 'bookmark', type: 'tags' },
      { key: 'main_findings', label: 'Main Findings', icon: 'trending-up', type: 'list' },
      { key: 'technical_terminology', label: 'Technical Terminology', icon: 'code', type: 'list' },
      { key: 'methodology_insights', label: 'Methodology Insights', icon: 'settings', type: 'text' },
      { key: 'research_gaps', label: 'Research Gaps', icon: 'search', type: 'list' },
      { key: 'potential_applications', label: 'Potential Applications', icon: 'zap', type: 'list' },
      { key: 'significance', label: 'Research Significance', icon: 'star', type: 'text' },
    ];

    const cards = sections.map(sec => {
      const val = sd[sec.key];
      if (!val || (Array.isArray(val) && !val.length)) return '';

      let content = '';
      if (sec.type === 'tags' && Array.isArray(val)) {
        content = `<div class="tags-list">${val.map(t => `<span class="tag-item">${escapeHtml(t)}</span>`).join('')}</div>`;
      } else if (sec.type === 'list' && Array.isArray(val)) {
        content = `<ul class="insight-list">${val.map(i => `<li>${escapeHtml(i)}</li>`).join('')}</ul>`;
      } else if (sec.type === 'text') {
        content = `<p class="insight-full">${escapeHtml(typeof val === 'string' ? val : JSON.stringify(val))}</p>`;
      } else if (Array.isArray(val)) {
        content = `<ul class="insight-list">${val.map(i => `<li>${escapeHtml(i)}</li>`).join('')}</ul>`;
      } else {
        content = `<p class="insight-full">${escapeHtml(String(val))}</p>`;
      }

      return `
        <div class="insight-card">
          <div class="insight-card-title">
            <i data-lucide="${sec.icon}"></i> ${sec.label}
          </div>
          ${content}
        </div>`;
    }).filter(Boolean).join('');

    container.innerHTML = `<div class="insights-grid">${cards}</div>`;
    lucide.createIcons({ nodes: [container] });
  }

  // Panel version (right PDF sidebar)
  async function loadInsightsForDoc(docId) {
    const panelContent = document.getElementById('insights-panel-content');
    if (!panelContent || !docId) return;

    panelContent.innerHTML = '<div class="ai-loading" style="padding:24px"><div class="ai-loading-spinner"></div><p>Loading…</p></div>';

    try {
      const data = await API.research.insights(docId);
      const insights = data.insights;
      if (!insights.length) {
        panelContent.innerHTML = `
          <div class="panel-hint-state">
            <i data-lucide="lightbulb"></i>
            <p>No insights generated yet</p>
            <button class="btn btn-primary btn-sm" onclick="InsightsModule.generateForCurrentDoc()">
              <i data-lucide="sparkles"></i> Generate
            </button>
          </div>`;
        lucide.createIcons({ nodes: [panelContent] });
        return;
      }

      const latest = insights[0];
      panelContent.innerHTML = '';
      renderInsightsMini(latest, panelContent);

      // Add regenerate button
      panelContent.innerHTML += `<button class="btn btn-ghost btn-sm" style="margin:8px" onclick="InsightsModule.generateForCurrentDoc()">
        <i data-lucide="refresh-cw"></i> Regenerate
      </button>`;
      lucide.createIcons({ nodes: [panelContent] });
    } catch (e) {
      panelContent.innerHTML = `<div class="panel-hint-state">
        <i data-lucide="alert-circle"></i><p>Failed to load insights</p>
        <button class="btn btn-ghost btn-sm" onclick="InsightsModule.loadInsightsForDoc('${docId}')">Retry</button>
      </div>`;
      lucide.createIcons({ nodes: [panelContent] });
    }
  }

  function renderInsightsMini(insight, container) {
    const sd = insight?.structured_data;
    if (!sd) {
      container.innerHTML = `<div class="markdown-body" style="padding:14px;font-size:0.82rem">${renderMarkdown(insight?.content || '')}</div>`;
      return;
    }

    let html = '';
    if (sd.research_themes?.length) {
      html += `<div class="insight-card"><div class="insight-card-title"><i data-lucide="layers"></i> Themes</div>
        <div class="tags-list">${sd.research_themes.map(t => `<span class="tag-item">${escapeHtml(t)}</span>`).join('')}</div></div>`;
    }
    if (sd.main_findings?.length) {
      html += `<div class="insight-card"><div class="insight-card-title"><i data-lucide="trending-up"></i> Key Findings</div>
        <ul class="insight-list">${sd.main_findings.map(f => `<li>${escapeHtml(f)}</li>`).join('')}</ul></div>`;
    }
    if (sd.research_gaps?.length) {
      html += `<div class="insight-card"><div class="insight-card-title"><i data-lucide="search"></i> Research Gaps</div>
        <ul class="insight-list">${sd.research_gaps.map(g => `<li>${escapeHtml(g)}</li>`).join('')}</ul></div>`;
    }
    container.innerHTML = html || '<p class="panel-hint">No structured insights</p>';
  }

  async function generateForCurrentDoc() {
    const docId = PDFViewer.getCurrentDocId();
    if (!docId) { showToast('No document selected', 'warn'); return; }

    const panelContent = document.getElementById('insights-panel-content');
    if (panelContent) {
      panelContent.innerHTML = '<div class="ai-loading" style="padding:24px"><div class="ai-loading-spinner"></div><p>Generating insights…</p></div>';
    }

    try {
      await API.research.generateInsights(docId);
      await loadInsightsForDoc(docId);
      showToast('Insights generated', 'success');
    } catch (e) {
      showToast(e.message || 'Insights generation failed', 'error');
      await loadInsightsForDoc(docId);
    }
  }

  function initControls() {
    document.getElementById('insights-run-btn')?.addEventListener('click', () => {
      const docId = document.getElementById('insights-doc-select')?.value;
      generateInsights(docId);
    });

    document.getElementById('panel-gen-insights-btn')?.addEventListener('click', generateForCurrentDoc);
  }

  return { onEnter, initControls, generateInsights, loadInsightsForDoc, generateForCurrentDoc, loadDocumentOptions };
})();

window.InsightsModule = InsightsModule;

