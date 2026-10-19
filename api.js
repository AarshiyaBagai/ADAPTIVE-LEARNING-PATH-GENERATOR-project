/* ALPG backend client. Optional: if no server answers, the app runs in offline demo mode.
   Served by backend/server.py the base is same-origin (''); opened from a file it tries http://127.0.0.1:8000. */
const API = {
  base: (typeof location !== 'undefined' && /^https?:$/.test(location.protocol)) ? '' : 'http://127.0.0.1:8000',
  online: false,

  /* Returns { ok, status, data, message }. status 0 means the server could not be reached. */
  async call(method, path, body, token) {
    const ctl = typeof AbortController !== 'undefined' ? new AbortController() : null;
    const timer = ctl ? setTimeout(() => ctl.abort(), 5000) : null;
    try {
      const headers = {};
      if (body) headers['Content-Type'] = 'application/json';
      if (token) headers.Authorization = 'Bearer ' + token;
      const res = await fetch(API.base + path, { method, headers, body: body ? JSON.stringify(body) : undefined, signal: ctl ? ctl.signal : undefined, cache: 'no-store' });
      let data = null;
      try { data = await res.json(); } catch (e) { /* non-JSON reply (e.g. a plain static server's 404 page) */ }
      return { ok: res.ok && data !== null, status: res.status, data, message: data && data.error ? data.error.message : null };
    } catch (e) {
      return { ok: false, status: 0, data: null, message: 'Server unreachable' };
    } finally {
      if (timer) clearTimeout(timer);
    }
  },

  async probe() {
    const r = await API.call('GET', '/api/health');
    API.online = r.ok && r.data && r.data.status === 'ok';
    return API.online;
  },
};
