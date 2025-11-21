import React, { useState } from 'react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Textarea } from '../components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Label } from '../components/ui/label'
import { Upload, Link as LinkIcon, FileText, Loader2 } from 'lucide-react'

export default function Ingest(){
  const [ns,setNs]=useState('default');
  const [urls,setUrls]=useState('');
  const [out,setOut]=useState('');
  const [loading,setLoading]=useState(false);
  
  async function post(path:string, body:any){ 
    setLoading(true);
    try {
      const r=await fetch('/api'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); 
      setOut(JSON.stringify(await r.json(),null,2)); 
    } finally {
      setLoading(false);
    }
  }
  
  async function ingestFiles(){
    setLoading(true);
    try {
      const fd = new FormData(); 
      fd.append('namespace', ns); 
      const inp=document.getElementById('files') as HTMLInputElement; 
      if(!inp.files) return; 
      for(let i=0;i<inp.files.length;i++){ 
        fd.append('files', inp.files[i], inp.files[i].name); 
      }
      const r = await fetch('/api/knowledge/ingest_files', { method:'POST', body: fd }); 
      setOut(JSON.stringify(await r.json(),null,2));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text">Ingest Data</h1>
          <p className="text-dim mt-1">Import knowledge from URLs, files, or sitemaps</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Namespace</CardTitle>
          <CardDescription>All ingested data will be stored in this namespace</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label htmlFor="namespace-ingest">Namespace</Label>
            <Input 
              id="namespace-ingest"
              value={ns} 
              onChange={e=>setNs(e.target.value)} 
              placeholder="default"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <LinkIcon className="mr-2 h-5 w-5" />
            Ingest from URLs
          </CardTitle>
          <CardDescription>Enter one URL per line</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea 
            rows={6} 
            value={urls} 
            onChange={e=>setUrls(e.target.value)} 
            placeholder="https://example.com/page1&#10;https://example.com/page2"
            className="font-mono text-xs"
          />
          <div className="flex gap-2">
            <Button 
              onClick={()=>post('/knowledge/ingest_urls', {
                namespace:ns, 
                urls: urls.split(/\n+/).map(x=>x.trim()).filter(Boolean), 
                use_trafilatura:true
              })}
              disabled={loading || !urls.trim()}
            >
              {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <LinkIcon className="mr-2 h-4 w-4" />}
              Ingest URLs
            </Button>
            <Button 
              variant="secondary"
              onClick={()=>post('/knowledge/ingest_sitemaps_bg', {
                namespace:ns, 
                sitemap_urls: urls.split(/\n+/).map(x=>x.trim()).filter(Boolean)
              })}
              disabled={loading || !urls.trim()}
            >
              Start Sitemap Job
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <FileText className="mr-2 h-5 w-5" />
            Ingest from Files
          </CardTitle>
          <CardDescription>Upload documents, PDFs, or text files</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="files">Select Files</Label>
            <Input 
              id="files" 
              type="file" 
              multiple 
              className="cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-accent file:text-white hover:file:bg-accent/90"
            />
          </div>
          <Button onClick={ingestFiles} disabled={loading}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
            Upload & Ingest Files
          </Button>
        </CardContent>
      </Card>

      {out && (
        <Card>
          <CardHeader>
            <CardTitle>Response</CardTitle>
            <CardDescription>Ingestion result</CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="p-4 rounded-lg bg-gray-900 border border-gray-800 text-xs text-dim overflow-x-auto max-h-96">{out}</pre>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
