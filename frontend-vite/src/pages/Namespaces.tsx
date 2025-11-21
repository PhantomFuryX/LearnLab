import React, { useState } from 'react'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Trash2, BarChart3, RefreshCw, Database } from 'lucide-react'

export default function Namespaces(){
  const [list,setList]=useState<string[]>([]);
  const [stats,setStats]=useState('');
  const [loading,setLoading]=useState(false);
  const [selectedNs,setSelectedNs]=useState<string>('');
  
  async function load(){ 
    setLoading(true);
    try {
      const r=await fetch('/api/knowledge/namespaces'); 
      const js=await r.json(); 
      setList(js.namespaces||[]); 
    } finally {
      setLoading(false);
    }
  }
  
  async function stat(ns:string){ 
    setSelectedNs(ns);
    setLoading(true);
    try {
      const r=await fetch('/api/knowledge/stats/'+encodeURIComponent(ns)); 
      setStats(JSON.stringify(await r.json(),null,2)); 
    } finally {
      setLoading(false);
    }
  }
  
  async function del(ns:string){ 
    if(!confirm(`Delete namespace "${ns}"? This cannot be undone.`)) return;
    setLoading(true);
    try {
      await fetch('/api/knowledge/namespaces/'+encodeURIComponent(ns), {method:'DELETE'}); 
      await load(); 
      if(selectedNs === ns) {
        setStats('');
        setSelectedNs('');
      }
    } finally {
      setLoading(false);
    }
  }
  
  React.useEffect(()=>{ load(); },[]);
  
  return (
    <div className="container max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text">Namespaces</h1>
          <p className="text-dim mt-1">Manage your knowledge base namespaces</p>
        </div>
        <Button onClick={load} variant="outline" disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Database className="mr-2 h-5 w-5" />
              Namespaces
            </CardTitle>
            <CardDescription>
              {list.length === 0 ? 'No namespaces found' : `${list.length} namespace(s)`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {list.length === 0 ? (
              <p className="text-dim text-center py-8">No namespaces available</p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {list.map(ns=> (
                  <div 
                    key={ns} 
                    className={`p-3 rounded-lg border transition-colors ${
                      selectedNs === ns 
                        ? 'bg-accent/10 border-accent' 
                        : 'bg-gray-900 border-gray-800 hover:border-gray-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-text">{ns}</span>
                      <div className="flex gap-2">
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={()=>stat(ns)}
                          disabled={loading}
                        >
                          <BarChart3 className="h-4 w-4" />
                        </Button>
                        <Button 
                          size="sm" 
                          variant="destructive"
                          onClick={()=>del(ns)}
                          disabled={loading}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <BarChart3 className="mr-2 h-5 w-5" />
              Statistics
            </CardTitle>
            <CardDescription>
              {selectedNs ? `Details for "${selectedNs}"` : 'Select a namespace to view stats'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {stats ? (
              <pre className="p-4 rounded-lg bg-gray-900 border border-gray-800 text-xs text-dim overflow-x-auto max-h-80">{stats}</pre>
            ) : (
              <p className="text-dim text-center py-8">
                Click the stats button to view namespace details
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
