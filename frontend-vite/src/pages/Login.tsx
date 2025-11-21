import React, { useState } from 'react'
import { login } from '../lib/api'
import { useAuth } from '../lib/authStore'
import { useNavigate, Link } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../components/ui/card'
import { Label } from '../components/ui/label'
import { LogIn, Loader2 } from 'lucide-react'

export default function Login(){
  const [email,setEmail]=useState('')
  const [pw,setPw]=useState('')
  const [err,setErr]=useState('')
  const [loading,setLoading]=useState(false)
  const setUser = useAuth(s=>s.setUser)
  const nav = useNavigate()
  
  async function onSubmit(e:React.FormEvent){ 
    e.preventDefault(); 
    setErr(''); 
    setLoading(true);
    try{ 
      const u = await login(email,pw); 
      setUser(u); 
      nav('/'); 
    }catch(e:any){ 
      setErr(String(e)); 
    } finally {
      setLoading(false);
    }
  }
  
  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-bg via-bg to-panel">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-text mb-2">LearnLab</h1>
          <p className="text-dim">AI-powered knowledge platform</p>
        </div>
        
        <Card>
          <form onSubmit={onSubmit}>
            <CardHeader>
              <CardTitle>Sign In</CardTitle>
              <CardDescription>Enter your credentials to access your account</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input 
                  id="email"
                  type="email" 
                  value={email} 
                  onChange={e=>setEmail(e.target.value)} 
                  placeholder="you@example.com"
                  required 
                  autoFocus
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input 
                  id="password"
                  type="password" 
                  value={pw} 
                  onChange={e=>setPw(e.target.value)} 
                  placeholder="••••••••"
                  required 
                />
              </div>
              {err && (
                <div className="p-3 rounded-lg bg-red-900/20 border border-red-700 text-red-400 text-sm">
                  {err}
                </div>
              )}
            </CardContent>
            <CardFooter className="flex flex-col space-y-4">
              <Button 
                type="submit" 
                className="w-full"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  <>
                    <LogIn className="mr-2 h-4 w-4" />
                    Sign In
                  </>
                )}
              </Button>
              <p className="text-sm text-center text-dim">
                Don't have an account?{' '}
                <Link to="/signup" className="text-accent hover:underline font-medium">
                  Sign up
                </Link>
              </p>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  )
}
