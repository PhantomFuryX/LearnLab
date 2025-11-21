export const API_BASE = (import.meta as any).env?.VITE_API_BASE || '/api';

export function authHeaders(): Record<string,string> {
  const t = localStorage.getItem('access_token');
  return t ? { Authorization: `Bearer ${t}` } : {};
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string,string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string,string> || {}),
    ...authHeaders(),
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export async function login(email: string, password: string){
  const data = await api<{access_token:string; refresh_token:string; user:any}>(`/auth/login`, {method:'POST', body: JSON.stringify({email,password})});
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
  localStorage.setItem('user', JSON.stringify(data.user));
  return data.user;
}

export async function register(email: string, password: string){
  const data = await api<{access_token:string; refresh_token:string; user:any}>(`/auth/register`, {method:'POST', body: JSON.stringify({email,password})});
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
  localStorage.setItem('user', JSON.stringify(data.user));
  return data.user;
}

export async function signup(email: string, password: string){
  return register(email, password);
}

export function logout(){ localStorage.removeItem('access_token'); localStorage.removeItem('refresh_token'); localStorage.removeItem('user'); }
