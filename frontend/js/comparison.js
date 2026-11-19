/**
 * comparison.js — Multi-paper comparison page
 */

const CompareModule = (() => {
  let selectedDocIds = new Set();
  let allReadyDocs = [];
  let lastComparison = null;

  async function onEnter() {
    await loadReadyDocs();
  }

  async function loadReadyDocs() {
    const container = document.getElementById('compare-paper-select');
    container.innerHTML = '<div class="panel-hint">Loading papers…</div>';
    try {
      const data = await API.documents.list({ status: 'ready' });
      allReadyDocs = data.documents;
      renderPaperSelect();
    } catch (e) {
      container.innerHTML = `<div class="panel-hint" style="color:var(--danger)">Failed to load documents</div>`;
    }
  }

  function renderPaperSelect() {
    const container = document.getElementById('compare-paper-select');
    if (!allReadyDocs.length) {
      container.innerHTML = `
        <div class="empty-state-sm" style="grid-column:1/-1">
          <i data-lucide="file-plus"></i>
          <p>No ready papers available. Upload and process some papers first.</p>
        </div>`;
      lucide.createIcons({ nodes: [container] });
      return;
    }
    container.innerHTML = allReadyDocs.map(d => `
      <div class="compare-paper-item ${selectedDocIds.has(d.id) ? 'selected' : ''}" data-doc-id="${d.id}">
        <i data-lucide="file-text"></i>
        <span class="compare-paper-item-title">${escapeHtml(truncate(d.title, 40))}</span>
        <span style="font-size:0.72rem;color:var(--text-muted)">${d.total_pages ? d.total_pages + 'pp' : ''}</span>
      </div>
    `).join('');
    lucide.createIcons({ nodes: [container] });

    container.querySelectorAll('.compare-paper-item').forEach(item => {
      item.addEventListener('click', () => {
        const id = item.dataset.docId;
        if (selectedDocIds.has(id)) {
          selectedDocIds.delete(id);
          item.classList.remove('selected');
        } else {
          selectedDocIds.add(id);
          item.classList.add('selected');
        }
        updateRunButton();
      });
    });
  }

  function updateRunButton() {
    const btn = document.getElementById('compare-run-btn');
    btn.disabled = selectedDocIds.size < 2;
  }

  async function runComparison() {
    if (selectedDocIds.size < 2) return;

    const loading = document.getElementById('compare-loading');
    const results = document.getElementById('compare-results');
    const setup = document.getElementById('compare-setup');

    loading.classList.remove('hidden');
    results.classList.add('hidden');

    try {
      const data = await API.research.compare({ document_ids: [...selectedDocIds] });
      lastComparison = data;
      renderResults(data);
      results.classList.remove('hidden');
    } catch (err) {
      showToast(err.message || 'Comparison failed', 'error');
    }
    loading.classList.add('hidden');
  }

  function renderResults(data) {
    const results = document.getElementById('compare-results');
    const comp = data.comparison;
    const docs = data.documents || [];

    if (!comp) {
      results.innerHTML = `<div class="error-state">
        <i data-lucide="alert-circle"></i>
        <h3>Comparison data unavailable</h3>
        <p>The AI could not generate a structured comparison. Try again.</p>
      </div>`;
      lucide.createIcons({ nodes: [results] });
      return;
    }

    const docList = docs.map((d, i) => `<strong>Paper ${i + 1}:</strong> ${escapeHtml(d.title)}`).join('<br>');

    const sections = [
      { key: 'overview', label: 'Overview', icon: 'layers' },
      { key: 'research_objectives', label: 'Research Objectives', icon: 'target' },
      { key: 'methodologies', label: 'Methodologies', icon: 'settings' },
      { key: 'datasets', label: 'Datasets', icon: 'database' },
      { key: 'evaluation_metrics', label: 'Evaluation Metrics', icon: 'bar-chart-2' },
      { key: 'results', label: 'Results', icon: 'trending-up' },
    ];

    let html = `
      <div class="compare-section">
        <div class="compare-section-header"><i data-lucide="files"></i> Papers Being Compared</div>
        <div class="compare-section-body">${docList}</div>
      </div>`;

    for (const sec of sections) {
      const val = comp[sec.key];
      if (!val) continue;
      let content = '';
      if (typeof val === 'string') {
        content = `<div class="markdown-body">${renderMarkdown(val)}</div>`;
      } else if (typeof val === 'object') {
        const rows = Object.entries(val).map(([k, v]) =>
          `<tr><td><strong>${escapeHtml(k)}</strong></td><td>${escapeHtml(v || '')}</td></tr>`
        ).join('');
        content = `<table class="compare-table"><thead><tr><th>Aspect</th><th>Details</th></tr></thead><tbody>${rows}</tbody></table>`;
      }
      html += `
        <div class="compare-section">
          <div class="compare-section-header"><i data-lucide="${sec.icon}"></i> ${sec.label}</div>
          <div class="compare-section-body">${content}</div>
        </div>`;
    }

    // Common themes
    if (comp.common_themes?.length) {
      html += `
        <div class="compare-section">
          <div class="compare-section-header"><i data-lucide="share-2"></i> Common Themes</div>
          <div class="compare-section-body">
            <div class="tags-list">${comp.common_themes.map(t => `<span class="tag-item">${escapeHtml(t)}</span>`).join('')}</div>
          </div>
        </div>`;
    }

    // Research gaps
    if (comp.research_gaps?.length) {
      html += `
        <div class="compare-section">
          <div class="compare-section-header"><i data-lucide="search"></i> Research Gaps Identified</div>
          <div class="compare-section-body">
            <ul class="insight-list">${comp.research_gaps.map(g => `<li>${escapeHtml(g)}</li>`).join('')}</ul>
          </div>
        </div>`;
    }

    // Conflicting findings
    if (comp.conflicting_findings) {
      html += `
        <div class="compare-section">
          <div class="compare-section-header"><i data-lucide="git-branch"></i> Conflicting Findings</div>
          <div class="compare-section-body"><div class="markdown-body">${renderMarkdown(comp.conflicting_findings)}</div></div>
        </div>`;
    }

    // Recommendation
    if (comp.recommendation) {
      html += `
        <div class="compare-section">
          <div class="compare-section-header"><i data-lucide="lightbulb"></i> Synthesis & Recommendation</div>
          <div class="compare-section-body"><div class="markdown-body">${renderMarkdown(comp.recommendation)}</div></div>
        </div>`;
    }

    // Export button
    html += `
      <div style="display:flex;gap:10px;justify-content:flex-end">
        <button class="btn btn-ghost btn-sm" id="compare-export-btn">
          <i data-lucide="download"></i> Export as Markdown
        </button>
      </div>`;

    results.innerHTML = html;
    lucide.createIcons({ nodes: [results] });

    document.getElementById('compare-export-btn')?.addEventListener('click', () => {
      exportComparison(comp, docs);
    });
  }

  async function exportComparison(comp, docs) {
    try {
      const titles = docs.map(d => d.title);
      const response = await fetch(`${API_BASE}/exports`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'comparison', comparison_data: comp, document_titles: titles }),
      });
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'paper-comparison.md'; a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      showToast('Export failed', 'error');
    }
  }

  function initControls() {
    document.getElementById('compare-run-btn')?.addEventListener('click', runComparison);
  }

  return { onEnter, initControls };
})();

window.CompareModule = CompareModule;

