import React, { useState, useEffect, useRef } from 'react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Textarea } from '../components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Label } from '../components/ui/label'
import { Send, Loader2, Code2, MessageSquare, Copy, Check, Plus, Trash2, MessageCircle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { useSearchParams } from 'react-router-dom'

function es(url: string, payload: any, onStep: (s:any)=>void, onToken:(t:string)=>void, onDone:()=>void){
  const ctrl = new AbortController();
  const token = localStorage.getItem('access_token');
  const headers: Record<string,string> = {'Content-Type':'application/json'};
  if(token) headers['Authorization'] = `Bearer ${token}`;
  fetch(url, { method:'POST', headers, body: JSON.stringify(payload), signal: ctrl.signal }).then(async res=>{
    if (!res.ok) { onDone(); return; }
    const reader = res.body!.getReader();
    const dec = new TextDecoder();
    let buf='';
    while(true){
      const {value, done} = await reader.read(); if(done) break;
      buf += dec.decode(value, {stream:true});
      let idx; while((idx=buf.indexOf('\n\n'))>=0){
        const chunk = buf.slice(0,idx); buf = buf.slice(idx+2);
        const lines = chunk.split('\n'); let event='message', data='';
        for(const ln of lines){ 
          if(ln.startsWith('event:')) event = ln.slice(6).trim(); 
          else if(ln.startsWith('data:')) data += (data?'\n':'') + ln.slice(5); 
        }
        if(event==='step'){ try{ onStep(JSON.parse(data)); }catch{} }
        if(event==='token'){ try{ onToken(JSON.parse(data)); }catch{ onToken(data); } }
        if(event==='done'){ onDone(); ctrl.abort(); }
      }
    }
  }).catch(() => onDone());
  return ()=>ctrl.abort();
}

interface Session {
  id: string;
  title: string;
  updated_at: number;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  created_at?: number;
}

export default function Chat(){
  // Session State
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  
  // Config State
  const [ns,setNs]=useState('default');
  const [k,setK]=useState(4);
  const [q,setQ]=useState('');
  const [streamingAns, setStreamingAns] = useState('');
  const [steps,setSteps]=useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<'chat' | 'code'>('chat');
  
  // Code Gen State
  const [stack, setStack] = useState('langchain');
  const [codeResult, setCodeResult] = useState<any>(null);
  const [copied, setCopied] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const [searchParams] = useSearchParams();
  const initialPrompt = searchParams.get('prompt');

  useEffect(() => {
    if (initialPrompt) {
      setQ(initialPrompt);
    }
  }, [initialPrompt]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingAns]);

  useEffect(() => {
    fetchSessions();
  }, []);

  useEffect(() => {
    if (currentSessionId) {
      fetchMessages(currentSessionId);
    } else {
      setMessages([]);
    }
  }, [currentSessionId]);

  const fetchSessions = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/api/chat/sessions', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
        if (data.length > 0 && !currentSessionId) {
          // Optionally select first session
          // setCurrentSessionId(data[0].id); 
        }
      }
    } catch (e) {
      console.error("Failed to fetch sessions", e);
    }
  };

  const fetchMessages = async (sessId: string) => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/api/chat/sessions/${sessId}/messages`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }
    } catch (e) {
      console.error("Failed to fetch messages", e);
    }
  };

  const createSession = async (title: string = "New Chat") => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/api/chat/sessions', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({ title })
      });
      if (res.ok) {
        const data = await res.json();
        setSessions([data, ...sessions]);
        setCurrentSessionId(data.id);
        return data.id;
      }
    } catch (e) {
      console.error("Failed to create session", e);
    }
    return null;
  };

  const deleteSession = async (sessId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this chat?")) return;
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/api/chat/sessions/${sessId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        setSessions(sessions.filter(s => s.id !== sessId));
        if (currentSessionId === sessId) {
          setCurrentSessionId(null);
          setMessages([]);
        }
      }
    } catch (e) {
      console.error("Failed to delete session", e);
    }
  };

  const handleAsk = async () => {
    if (mode === 'code') {
      handleGenerateCode();
      return;
    }

    let sessId = currentSessionId;
    if (!sessId) {
      sessId = await createSession(q.slice(0, 30) + (q.length > 30 ? '...' : ''));
      if (!sessId) return;
    }

    const userMsg: Message = { role: 'user', content: q };
    setMessages(prev => [...prev, userMsg]);
    setQ('');
    setStreamingAns('');
    setSteps([]);
    setLoading(true);

    es('/api/chat/ask_stream', { prompt: userMsg.content, namespace: ns, k, session_id: sessId }, 
      s => setSteps(p => [...p, s]), 
      t => setStreamingAns(p => p + t), 
      () => {
        setLoading(false);
        // After streaming is done, we should ideally fetch messages or append the completed one.
        // Since we have the full streamed answer, let's append it locally.
        setMessages(prev => [...prev, { role: 'assistant', content: streamingAns + (loading ? '' : '') }]); 
        // Note: inside this callback, 'streamingAns' might be stale closure. 
        // Better to trigger a fetch or use a ref for accumulation. 
        // But for now, let's just re-fetch messages to be safe and sync with DB.
        if (sessId) fetchMessages(sessId);
        setStreamingAns('');
      }
    );
  };

  const handleGenerateCode = async () => {
    setLoading(true);
    setCodeResult(null);
    try {
      const response = await fetch('/api/chat/generate-code', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          topic: q,
          stack: stack,
          language: 'python'
        })
      });
      
      if (!response.ok) throw new Error('Code generation failed');
      
      const data = await response.json();
      setCodeResult(data);
    } catch (error) {
      console.error('Code generation error:', error);
      alert('Code generation failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const copyCode = () => {
    if (codeResult?.code?.code) {
      navigator.clipboard.writeText(codeResult.code.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="flex h-[calc(100vh-6rem)] gap-6 container max-w-7xl mx-auto p-4">
      {/* Sidebar - Session List */}
      <div className="w-64 flex-shrink-0 flex flex-col gap-4">
        <Button onClick={() => {setCurrentSessionId(null); setMessages([]); setQ('');}} className="w-full justify-start" variant={currentSessionId ? "outline" : "default"}>
          <Plus className="mr-2 h-4 w-4" />
          New Chat
        </Button>
        
        <div className="flex-1 overflow-y-auto space-y-2 pr-2">
          {sessions.map(s => (
             <div 
               key={s.id} 
               onClick={() => setCurrentSessionId(s.id)}
               className={`group flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors ${currentSessionId === s.id ? 'bg-accent text-white' : 'hover:bg-gray-900 text-dim'}`}
             >
               <div className="flex items-center overflow-hidden">
                 <MessageCircle className="h-4 w-4 mr-3 flex-shrink-0" />
                 <span className="truncate text-sm">{s.title}</span>
               </div>
               <button 
                 onClick={(e) => deleteSession(s.id, e)}
                 className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-900/50 rounded text-red-400 transition-opacity"
               >
                 <Trash2 className="h-3 w-3" />
               </button>
             </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 gap-4">
        {/* Header / Config Toggle */}
        <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold">{mode === 'chat' ? (currentSessionId ? sessions.find(s=>s.id===currentSessionId)?.title || 'Chat' : 'New Chat') : 'Code Generator'}</h2>
             <div className="flex gap-2">
                <Button 
                   variant={mode === 'chat' ? "secondary" : "ghost"} 
                   size="sm" 
                   onClick={() => setMode('chat')}
                >
                  <MessageSquare className="h-4 w-4 mr-2" />
                  Chat
                </Button>
                <Button 
                   variant={mode === 'code' ? "secondary" : "ghost"} 
                   size="sm" 
                   onClick={() => setMode('code')}
                >
                  <Code2 className="h-4 w-4 mr-2" />
                  Code
                </Button>
             </div>
        </div>

        {mode === 'chat' ? (
          <>
             {/* Messages List */}
             <div className="flex-1 overflow-y-auto rounded-xl border border-gray-800 bg-gray-950/50 p-4 space-y-6">
                {messages.length === 0 && !loading && (
                   <div className="h-full flex flex-col items-center justify-center text-dim opacity-50">
                      <MessageSquare className="h-12 w-12 mb-4" />
                      <p>Select a session or start a new chat</p>
                   </div>
                )}
                
                {messages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                      msg.role === 'user' 
                        ? 'bg-blue-600/20 border border-blue-500/30 text-blue-100 rounded-br-none' 
                        : 'bg-gray-900 border border-gray-800 text-gray-100 rounded-bl-none'
                    }`}>
                       <div className="prose prose-invert text-sm max-w-none">
                          <ReactMarkdown 
                            remarkPlugins={[remarkGfm]}
                            components={{
                              code({node, inline, className, children, ...props}: any) {
                                const match = /language-(\w+)/.exec(className || '')
                                return !inline && match ? (
                                  <SyntaxHighlighter style={vscDarkPlus} language={match[1]} PreTag="div" {...props}>{String(children).replace(/\n$/, '')}</SyntaxHighlighter>
                                ) : (
                                  <code className={className} {...props}>{children}</code>
                                )
                              }
                            }}
                          >
                            {msg.content}
                          </ReactMarkdown>
                       </div>
                    </div>
                  </div>
                ))}

                {loading && streamingAns && (
                  <div className="flex justify-start">
                    <div className="max-w-[80%] rounded-2xl rounded-bl-none px-4 py-3 bg-gray-900 border border-gray-800 text-gray-100">
                       <div className="prose prose-invert text-sm max-w-none">
                          <ReactMarkdown>{streamingAns}</ReactMarkdown>
                       </div>
                    </div>
                  </div>
                )}
                
                {loading && !streamingAns && (
                   <div className="flex justify-start">
                      <div className="flex items-center space-x-2 text-dim bg-gray-900 px-4 py-2 rounded-full">
                         <Loader2 className="h-3 w-3 animate-spin" />
                         <span className="text-xs">Thinking...</span>
                      </div>
                   </div>
                )}
                <div ref={messagesEndRef} />
             </div>

             {/* Input Area */}
             <div className="space-y-4">
                {/* Steps / Config (Collapsible or simple) */}
                <div className="flex gap-4 items-end">
                  <div className="flex-1 relative">
                     <Textarea 
                       value={q} 
                       onChange={e=>setQ(e.target.value)} 
                       onKeyDown={e => { if(e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleAsk(); } }}
                       placeholder="Type your message..." 
                       className="min-h-[60px] resize-none pr-12"
                     />
                     <Button 
                        size="icon" 
                        className="absolute right-2 bottom-2 h-8 w-8" 
                        onClick={handleAsk}
                        disabled={!q.trim() || loading}
                     >
                        <Send className="h-4 w-4" />
                     </Button>
                  </div>
                </div>
                <div className="flex gap-4 text-xs text-dim items-center">
                   <span>Namespace:</span>
                   <Input className="h-6 w-24 text-xs" value={ns} onChange={e=>setNs(e.target.value)} />
                   <span>K:</span>
                   <Input className="h-6 w-16 text-xs" type="number" value={k} onChange={e=>setK(parseInt(e.target.value)||4)} />
                   <span className="ml-auto">Model: Knowledge Agent</span>
                </div>
             </div>
          </>
        ) : (
          /* Code Generator UI */
          <div className="flex-1 flex flex-col space-y-6">
             {/* Reuse existing code UI structure here */}
             <Card>
                <CardHeader><CardTitle>Configuration</CardTitle></CardHeader>
                <CardContent>
                    <div className="space-y-2">
                      <Label>Target Stack</Label>
                      <select value={stack} onChange={e => setStack(e.target.value)} className="flex h-10 w-full rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-text">
                        <option value="langchain">LangChain</option>
                        <option value="pytorch">PyTorch</option>
                        <option value="tensorflow">TensorFlow</option>
                        <option value="vanilla">Vanilla Python</option>
                      </select>
                    </div>
                </CardContent>
             </Card>
             
             <Card>
               <CardContent className="pt-6 space-y-4">
                  <Textarea value={q} onChange={e=>setQ(e.target.value)} placeholder="Describe the code you need..." rows={4} />
                  <Button onClick={handleGenerateCode} disabled={!q.trim() || loading} className="w-full">
                     {loading ? <Loader2 className="animate-spin mr-2" /> : <Code2 className="mr-2" />} Generate Code
                  </Button>
               </CardContent>
             </Card>

             {codeResult && (
               <Card className="border-green-800/50">
                  <CardHeader><CardTitle className="flex justify-between"><span>{codeResult.code?.title}</span> <Button size="sm" variant="outline" onClick={copyCode}>{copied ? <Check className="h-4 w-4"/> : <Copy className="h-4 w-4"/>}</Button></CardTitle></CardHeader>
                  <CardContent>
                     <pre className="p-4 rounded-lg bg-gray-950 border border-gray-800 text-xs text-green-400 overflow-x-auto max-h-96">
                        <code>{codeResult.code?.code}</code>
                     </pre>
                  </CardContent>
               </Card>
             )}
          </div>
        )}
      </div>
    </div>
  )
}
