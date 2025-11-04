// Shared utilities for TaskMaster frontend

// DOM helpers
const $ = (sel, root = document) => root.querySelector(sel)
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel))

// Token utilities
const TOKEN_KEY = 'taskmaster_token'
const getToken = () => localStorage.getItem(TOKEN_KEY)
const setToken = (t) => localStorage.setItem(TOKEN_KEY, t)
const clearToken = () => localStorage.removeItem(TOKEN_KEY)

// Toasts
function ensureToastContainer () {
  let el = document.getElementById('toast-container')
  if (!el) {
    el = document.createElement('div')
    el.id = 'toast-container'
    el.setAttribute('role', 'status')
    el.setAttribute('aria-live', 'polite')
    document.body.appendChild(el)
  }
  return el
}
function showToast (msg, type = 'info', timeout = 3000) {
  const container = ensureToastContainer()
  const toast = document.createElement('div')
  toast.className = `toast ${type}`
  toast.textContent = msg
  container.appendChild(toast)
  requestAnimationFrame(() => toast.classList.add('show'))
  setTimeout(() => {
    toast.classList.remove('show')
    setTimeout(() => toast.remove(), 300)
  }, timeout)
}

// Safe error text extraction
async function safeText (res) {
  try {
    const t = await res.text()
    try {
      const j = JSON.parse(t)
      if (j && j.detail) return Array.isArray(j.detail) ? j.detail.map(d => d.msg || d).join(', ') : (j.detail.msg || j.detail)
      return t
    } catch {
      return t
    }
  } catch {
    return `${res.status} ${res.statusText}`
  }
}

// API helpers
async function apiFetch (path, opts = {}) {
  const headers = new Headers(opts.headers || {})
  headers.set('Content-Type', 'application/json')
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(path, { ...opts, headers })
  if (res.status === 401) {
    showToast('Sesión expirada. Inicia sesión nuevamente.', 'error')
    clearToken()
    setTimeout(() => location.assign('/login.html'), 800)
    throw new Error('Unauthorized')
  }
  return res
}

const api = {
  login: async (email, password) => {
    const res = await fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    })
    if (!res.ok) throw new Error(await safeText(res))
    const j = await res.json()
    // Normalizar forma: devolver access_token
    return { access_token: j.access_token || j.token, token_type: j.token_type || 'bearer' }
  },
  register: async (email, password) => {
    const res = await fetch('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    })
    if (!res.ok) throw new Error(await safeText(res))
    return res.json()
  },
  getNotes: async ({ page = 1, limit = 10, q } = {}) => {
    const params = new URLSearchParams({ page, limit })
    if (q) params.set('q', q)
    const res = await apiFetch(`/tasks/?${params.toString()}`)
    if (!res.ok) throw new Error(await safeText(res))
    return res.json()
  },
  createNote: async (title, description = "") => {
    const res = await apiFetch('/tasks/', {
      method: 'POST',
      body: JSON.stringify({ title, description })
    })
    if (!res.ok) throw new Error(await safeText(res))
    return res.json()
  },
  deleteNote: async (id) => {
    const res = await apiFetch(`/tasks/${id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error(await safeText(res))
    return true
  }
}

// Auth guard utilities
function ensureAuthOrRedirect () {
  if (!getToken()) {
    location.replace('/login.html')
    return false
  }
  return true
}

// UI helpers
function setButtonLoading(btn, isLoading, labelWhileLoading = 'Procesando...') {
  if (!btn) return
  if (isLoading) {
    btn.dataset.prevText = btn.textContent
    btn.classList.add('btn-loading')
    btn.disabled = true
    btn.innerHTML = `<span class="spinner" aria-hidden="true"></span><span style="margin-left:16px">${labelWhileLoading}</span>`
  } else {
    const prev = btn.dataset.prevText
    btn.classList.remove('btn-loading')
    btn.disabled = false
    btn.innerHTML = prev || btn.textContent
  }
}

function escapeHTML (s = '') {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))
}

// Expose helpers for inline scripts
window.$ = $
window.$$ = $$
window.api = api
window.getToken = getToken
window.setToken = setToken
window.clearToken = clearToken
window.showToast = showToast
window.ensureAuthOrRedirect = ensureAuthOrRedirect
window.setButtonLoading = setButtonLoading
window.escapeHTML = escapeHTML
