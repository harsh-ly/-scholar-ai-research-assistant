/**
 * api.js — Scholar AI API client
 * All communication with the Flask backend goes through this module.
 */

const API_BASE = (window.location.protocol === 'http:' || window.location.protocol === 'https:') && window.location.port !== '5500' && window.location.port !== '3000'
  ? `${window.location.origin}/api/v1`
  : `http://${window.location.hostname || '127.0.0.1'}:5000/api/v1`;

class APIError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function apiRequest(method, path, body = null, isFormData = false) {
  const url = `${API_BASE}${path}`;
  const options = {
    method,
    headers: {},
  };

  if (body && !isFormData) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  } else if (body && isFormData) {
    options.body = body; // FormData — browser sets content-type with boundary
  }

  let res;
  try {
    res = await fetch(url, options);
  } catch (err) {
    throw new APIError('Cannot reach Scholar AI backend. Is the Flask server running?', 0, err.message);
  }

  let data;
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    data = await res.json();
  } else {
    data = await res.text();
  }

  if (!res.ok) {
    const msg = (data && data.error) ? data.error : `HTTP ${res.status}`;
    throw new APIError(msg, res.status, data);
  }
  return data;
}

// ── Health ──────────────────────────────────────────────────────
const API = {
  health: {
    check: () => apiRequest('GET', '/health'),
    ready: () => apiRequest('GET', '/health/ready'),
  },

  // ── Documents ───────────────────────────────────────────────
  documents: {
    upload: (formData) => apiRequest('POST', '/documents', formData, true),
    list: (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return apiRequest('GET', `/documents${qs ? '?' + qs : ''}`);
    },
    get: (id) => apiRequest('GET', `/documents/${id}`),
    delete: (id) => apiRequest('DELETE', `/documents/${id}`),
    status: (id) => apiRequest('GET', `/documents/${id}/status`),
    retry: (id) => apiRequest('POST', `/documents/${id}/retry`),
    pdfUrl: (id) => `${API_BASE}/documents/${id}/pdf`,
    pageText: (id, page) => apiRequest('GET', `/documents/${id}/pages/${page}`),
  },

  // ── Chat / Conversations ─────────────────────────────────────
  conversations: {
    create: (data) => apiRequest('POST', '/conversations', data),
    list: (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return apiRequest('GET', `/conversations${qs ? '?' + qs : ''}`);
    },
    get: (id) => apiRequest('GET', `/conversations/${id}`),
    update: (id, data) => apiRequest('PATCH', `/conversations/${id}`, data),
    delete: (id) => apiRequest('DELETE', `/conversations/${id}`),
  },

  chat: {
    send: (data) => apiRequest('POST', '/chat', data),
    feedback: (msgId, feedback) => apiRequest('POST', `/messages/${msgId}/feedback`, { feedback }),
  },

  // ── Research ─────────────────────────────────────────────────
  research: {
    summary: (docId, data) => apiRequest('POST', `/documents/${docId}/summaries`, data),
    compare: (data) => apiRequest('POST', '/compare', data),
    insights: (docId) => apiRequest('GET', `/documents/${docId}/insights`),
    generateInsights: (docId, data = {}) => apiRequest('POST', `/documents/${docId}/insights`, data),
    search: (params) => {
      const qs = new URLSearchParams(params).toString();
      return apiRequest('GET', `/search?${qs}`);
    },
    stats: () => apiRequest('GET', '/stats'),
  },

  // ── Notes ────────────────────────────────────────────────────
  notes: {
    list: (docId) => apiRequest('GET', `/notes${docId ? '?document_id=' + docId : ''}`),
    create: (data) => apiRequest('POST', '/notes', data),
    update: (id, data) => apiRequest('PATCH', `/notes/${id}`, data),
    delete: (id) => apiRequest('DELETE', `/notes/${id}`),
    exportUrl: (id) => `${API_BASE}/notes/${id}/export`,
  },

  // ── Collections ───────────────────────────────────────────────
  collections: {
    list: () => apiRequest('GET', '/collections'),
    create: (data) => apiRequest('POST', '/collections', data),
    get: (id) => apiRequest('GET', `/collections/${id}`),
    update: (id, data) => apiRequest('PATCH', `/collections/${id}`, data),
    delete: (id) => apiRequest('DELETE', `/collections/${id}`),
    addDocument: (collId, docId) => apiRequest('POST', `/collections/${collId}/documents`, { document_id: docId }),
    removeDocument: (collId, docId) => apiRequest('DELETE', `/collections/${collId}/documents/${docId}`),
  },

  // ── Exports ───────────────────────────────────────────────────
  exports: {
    create: (data) => apiRequest('POST', '/exports', data),
  },
};

// Poll document status until ready/failed
async function pollDocumentStatus(docId, onProgress, maxWait = 300000) {
  const start = Date.now();
  while (Date.now() - start < maxWait) {
    try {
      const data = await API.documents.status(docId);
      if (onProgress) onProgress(data);
      if (data.status === 'ready' || data.status === 'failed') return data;
    } catch (e) {
      // ignore transient errors during polling
    }
    await new Promise(r => setTimeout(r, 2500));
  }
  return null;
}

