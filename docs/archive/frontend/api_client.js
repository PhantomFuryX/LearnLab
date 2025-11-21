const API_BASE = (window.API_BASE || "");

export async function ingestUrls(namespace, urls, opts={}) {
  const body = { namespace, urls, ...opts };
  const res = await fetch(`${API_BASE}/knowledge/ingest_urls`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error(`ingest_urls failed: ${res.status}`);
  return await res.json();
}

export async function ingestFetch(namespace, urls, opts={}) {
  const body = { namespace, urls, ...opts };
  const res = await fetch(`${API_BASE}/knowledge/ingest_fetch`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error(`ingest_fetch failed: ${res.status}`);
  return await res.json();
}

export async function listNamespaces() {
  const res = await fetch(`${API_BASE}/knowledge/namespaces`);
  if (!res.ok) throw new Error(`namespaces failed`);
  return await res.json();
}

export async function namespaceStats(ns) {
  const res = await fetch(`${API_BASE}/knowledge/stats/${encodeURIComponent(ns)}`);
  if (!res.ok) throw new Error(`stats failed`);
  return await res.json();
}

export async function deleteNamespace(ns) {
  const res = await fetch(`${API_BASE}/knowledge/namespaces/${encodeURIComponent(ns)}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`delete failed`);
  return await res.json();
}

export function agentsStream(payload, onStep, onToken, onDone, onError) {
  const es = new EventSourcePolyfill(`${API_BASE}/agents/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    payload: JSON.stringify(payload)
  });
  es.addEventListener('step', (e) => onStep && onStep(JSON.parse(e.data)));
  es.addEventListener('token', (e) => onToken && onToken(e.data));
  es.addEventListener('done', () => { onDone && onDone(); es.close(); });
  es.addEventListener('error', (e) => { onError && onError(e); es.close(); });
  return es;
}

export function chatAskStream(payload, onStep, onToken, onDone, onError) {
  const es = new EventSourcePolyfill(`${API_BASE}/chat/ask_stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    payload: JSON.stringify(payload)
  });
  es.addEventListener('step', (e) => onStep && onStep(JSON.parse(e.data)));
  es.addEventListener('token', (e) => onToken && onToken(e.data));
  es.addEventListener('done', () => { onDone && onDone(); es.close(); });
  es.addEventListener('error', (e) => { onError && onError(e); es.close(); });
  return es;
}

export async function chatAsk(payload) {
  const res = await fetch(`${API_BASE}/chat/ask`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(`chat/ask failed: ${res.status}`);
  return await res.json();
}

// Lightweight EventSource polyfill for POST-based SSE
class EventSourcePolyfill {
  constructor(url, { method='GET', headers={}, payload=null }={}) {
    this._ctrl = new AbortController();
    this._listeners = {};
    this._run(url, method, headers, payload);
  }
  addEventListener(type, cb) { (this._listeners[type] = this._listeners[type] || []).push(cb); }
  close() { this._ctrl.abort(); }
  async _run(url, method, headers, payload) {
    try {
      const res = await fetch(url, { method, headers, body: payload, signal: this._ctrl.signal });
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buf.indexOf('\n\n')) >= 0) {
          const chunk = buf.slice(0, idx); buf = buf.slice(idx+2);
          const lines = chunk.split('\n');
          let event = 'message'; let data = '';
          for (const line of lines) {
            if (line.startsWith('event:')) event = line.slice(6).trim();
            else if (line.startsWith('data:')) data += (data ? '\n' : '') + line.slice(5).trim();
          }
          const list = this._listeners[event] || [];
          list.forEach(cb => cb({ data }));
        }
      }
    } catch (e) {
      const list = this._listeners['error'] || [];
      list.forEach(cb => cb(e));
    }
  }
}
