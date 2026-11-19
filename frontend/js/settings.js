/**
 * settings.js — Settings page
 */

const SettingsModule = (() => {
  async function onEnter() {
    await checkGeminiStatus();
    await loadStats();
    loadThemeSetting();
  }

  async function checkGeminiStatus() {
    const badge = document.getElementById('gemini-status-badge');
    const modelEl = document.getElementById('settings-gemini-model');
    const embedEl = document.getElementById('settings-embed-model');

    if (!badge) return;
    badge.textContent = 'Checking…';
    badge.className = 'status-badge check';

    try {
      const data = await API.health.ready();
      const geminiOk = data.checks?.gemini_configured;

      badge.textContent = geminiOk ? 'Connected' : 'Not configured';
      badge.className = `status-badge ${geminiOk ? 'ok' : 'error'}`;

      if (modelEl && data.checks?.embedding_model) {
        embedEl.textContent = data.checks.embedding_model;
      }
    } catch (e) {
      badge.textContent = 'Unreachable';
      badge.className = 'status-badge error';
    }

    // Get model name from health endpoint
    try {
      const resp = await fetch(`${API_BASE}/health/ready`);
      const d = await resp.json();
      if (modelEl) modelEl.textContent = 'gemini-3.5-flash';
    } catch (e) {}
  }

  async function loadStats() {
    try {
      const data = await API.research.stats();
      if (document.getElementById('settings-doc-count'))
        document.getElementById('settings-doc-count').textContent = data.total_documents;
      if (document.getElementById('settings-chunk-count'))
        document.getElementById('settings-chunk-count').textContent = data.total_chunks?.toLocaleString() || '0';
    } catch (e) {}
  }

  function loadThemeSetting() {
    const stored = localStorage.getItem('scholar-theme') || 'dark';
    const select = document.getElementById('theme-select');
    if (select) select.value = stored;
    applyTheme(stored);
  }

  function applyTheme(theme) {
    if (theme === 'light') {
      document.documentElement.setAttribute('data-theme', 'light');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    localStorage.setItem('scholar-theme', theme);
  }

  function initControls() {
    document.getElementById('theme-select')?.addEventListener('change', (e) => {
      applyTheme(e.target.value);
      showToast(`Theme changed to ${e.target.value}`, 'info');
    });
  }

  return { onEnter, initControls };
})();

window.SettingsModule = SettingsModule;

