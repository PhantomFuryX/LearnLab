import create from 'zustand'

type User = { id: string; email: string; roles: string[] }

type AuthState = {
  user: User | null
  setUser: (u: User | null) => void
}

export const useAuth = create<AuthState>((set)=>({
  user: JSON.parse(localStorage.getItem('user')||'null'),
  setUser: (u)=>{ if(u) localStorage.setItem('user', JSON.stringify(u)); else localStorage.removeItem('user'); set({user:u}); }
}))
