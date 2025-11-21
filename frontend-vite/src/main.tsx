import './index.css'
import React, { useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom'
import Home from './pages/Home'
import Chat from './pages/Chat'
import Ingest from './pages/Ingest'
import Namespaces from './pages/Namespaces'
import Jobs from './pages/Jobs'
import Research from './pages/Research'
import Login from './pages/Login'
import Signup from './pages/Signup'
import PlanCreation from './pages/PlanCreation'
import Dashboard from './pages/Dashboard'
import Feed from './pages/Feed'
import Settings from './pages/Settings'
import QuizView from './pages/Quiz'
import { useAuth } from './lib/authStore.ts'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Automation from './pages/Automation'
import Scheduler from './pages/Scheduler'
import { MessageSquare, Upload, Database, Briefcase, Search, LogOut, LayoutDashboard, Map, Settings as SettingsIcon, GraduationCap, PlayCircle, Code as CodeIcon, HelpCircle, BookOpen, Menu, X, Home as HomeIcon, Zap, Clock } from 'lucide-react'
import { Button } from './components/ui/button'

// If UI components missing, we'll use standard div
// We'll build a SidebarLayout

function Guard({children}:{children:React.ReactNode}){
  const user = useAuth(s=>s.user)
  if(!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

function NavItem({ to, children, icon: Icon, collapsed }: { to: string; children: React.ReactNode; icon: any, collapsed?: boolean }) {
  const location = useLocation();
  const isActive = location.pathname === to;
  
  return (
    <Link 
      to={to} 
      className={`flex items-center px-3 py-2.5 rounded-lg transition-all duration-200 group ${
        isActive 
          ? 'bg-primary text-primary-foreground shadow-md' 
          : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
      }`}
      title={typeof children === 'string' ? children : ''}
    >
      <Icon className={`h-5 w-5 ${collapsed ? 'mx-auto' : 'mr-3'} flex-shrink-0`} />
      {!collapsed && <span className="font-medium truncate">{children}</span>}
    </Link>
  );
}

function Sidebar({ collapsed, setCollapsed }: { collapsed: boolean, setCollapsed: (v:boolean)=>void }) {
    const user = useAuth(s=>s.user);
    const setUser = useAuth(s=>s.setUser);

    return (
        <aside className={`${collapsed ? 'w-16' : 'w-64'} hidden md:flex flex-col border-r border-border bg-card transition-all duration-300 ease-in-out sticky top-0 h-screen`}>
            {/* Header */}
            <div className={`h-16 flex items-center ${collapsed ? 'justify-center' : 'px-6'} border-b border-border`}>
                <div className="flex items-center gap-2 cursor-pointer" onClick={() => setCollapsed(!collapsed)}>
                    <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold text-xl">L</div>
                    {!collapsed && <span className="font-bold text-xl tracking-tight">LearnLab</span>}
                </div>
            </div>

            {/* Nav Links */}
            <div className="flex-1 overflow-y-auto py-6 px-3 space-y-1">
                <NavItem to="/" icon={HomeIcon} collapsed={collapsed}>Home</NavItem>
                <div className="my-4 border-t border-border/50"></div>
                <NavItem to="/chat" icon={MessageSquare} collapsed={collapsed}>Chat</NavItem>
                <NavItem to="/dashboard" icon={LayoutDashboard} collapsed={collapsed}>My Plans</NavItem>
                <NavItem to="/plan" icon={Map} collapsed={collapsed}>Planner</NavItem>
                <NavItem to="/quiz" icon={GraduationCap} collapsed={collapsed}>Quiz</NavItem>
                <NavItem to="/research" icon={Search} collapsed={collapsed}>Research</NavItem>
                <NavItem to="/feed" icon={BookOpen} collapsed={collapsed}>Feed</NavItem>
                <div className="my-4 border-t border-border/50"></div>
                <NavItem to="/ingest" icon={Upload} collapsed={collapsed}>Ingest</NavItem>
                <NavItem to="/namespaces" icon={Database} collapsed={collapsed}>Knowledge</NavItem>
                <NavItem to="/automation" icon={Zap} collapsed={collapsed}>Automation</NavItem>
                <NavItem to="/scheduler" icon={Clock} collapsed={collapsed}>Scheduler</NavItem>
                <NavItem to="/jobs" icon={Briefcase} collapsed={collapsed}>Jobs</NavItem>
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-border">
                <NavItem to="/settings" icon={SettingsIcon} collapsed={collapsed}>Settings</NavItem>
                {user && (
                    <button 
                        onClick={() => setUser(null)}
                        className={`w-full flex items-center px-3 py-2.5 rounded-lg transition-colors text-muted-foreground hover:bg-red-500/10 hover:text-red-500 mt-1`}
                    >
                        <LogOut className={`h-5 w-5 ${collapsed ? 'mx-auto' : 'mr-3'}`} />
                        {!collapsed && <span className="font-medium">Logout</span>}
                    </button>
                )}
            </div>
        </aside>
    );
}

function MobileHeader() {
    const [open, setOpen] = useState(false);
    const user = useAuth(s=>s.user);
    const setUser = useAuth(s=>s.setUser);

    return (
        <div className="md:hidden h-16 border-b border-border bg-card flex items-center justify-between px-4 sticky top-0 z-50">
            <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold">L</div>
                <span className="font-bold text-lg">LearnLab</span>
            </div>
            
            {/* Simple Mobile Menu Toggle since Sheet component might not exist fully */}
            <button onClick={() => setOpen(!open)} className="p-2 hover:bg-accent rounded-md">
                {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>

            {/* Mobile Menu Dropdown */}
            {open && (
                <div className="absolute top-16 left-0 right-0 bg-card border-b border-border p-4 shadow-2xl space-y-2 z-50">
                     <NavItem to="/" icon={HomeIcon}>Home</NavItem>
                     <NavItem to="/chat" icon={MessageSquare}>Chat</NavItem>
                     <NavItem to="/dashboard" icon={LayoutDashboard}>My Plans</NavItem>
                     <NavItem to="/quiz" icon={GraduationCap}>Quiz</NavItem>
                     <NavItem to="/research" icon={Search}>Research</NavItem>
                     <div className="border-t border-border my-2"></div>
                     <NavItem to="/settings" icon={SettingsIcon}>Settings</NavItem>
                     {user && (
                         <button onClick={() => setUser(null)} className="w-full flex items-center px-3 py-2 text-red-500">
                             <LogOut className="h-5 w-5 mr-3" /> Logout
                         </button>
                     )}
                </div>
            )}
        </div>
    )
}

function AppLayout({children}: {children: React.ReactNode}) {
  const user = useAuth(s=>s.user);
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  
  if(location.pathname === '/login' || location.pathname === '/signup') {
    return <>{children}</>;
  }
  
  return (
    <div className="min-h-screen bg-background flex flex-col md:flex-row">
        <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
        <div className="flex-1 flex flex-col min-w-0 h-screen">
            <MobileHeader />
            <main className="flex-1 overflow-y-auto overflow-x-hidden bg-background/50">
                {children}
            </main>
        </div>
    </div>
  );
}

const qc = new QueryClient()

function App(){
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <AppLayout>
          <Routes>
            <Route path="/login" element={<Login/>} />
            <Route path="/signup" element={<Signup/>} />
            <Route path="/" element={<Guard><Home/></Guard>} />
            <Route path="/chat" element={<Guard><Chat/></Guard>} />
            <Route path="/dashboard" element={<Guard><Dashboard/></Guard>} />
            <Route path="/feed" element={<Guard><Feed/></Guard>} />
            <Route path="/plan" element={<Guard><PlanCreation/></Guard>} />
            <Route path="/quiz" element={<Guard><QuizView/></Guard>} />
            <Route path="/settings" element={<Guard><Settings/></Guard>} />
            <Route path="/research" element={<Guard><Research/></Guard>} />
            <Route path="/ingest" element={<Guard><Ingest/></Guard>} />
            <Route path="/namespaces" element={<Guard><Namespaces/></Guard>} />
            <Route path="/jobs" element={<Guard><Jobs/></Guard>} />
            <Route path="/automation" element={<Guard><Automation/></Guard>} />
            <Route path="/scheduler" element={<Guard><Scheduler/></Guard>} />
          </Routes>
        </AppLayout>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

createRoot(document.getElementById('root')!).render(<App/>)
