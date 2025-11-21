import React, { useState, useEffect } from 'react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Label } from '../components/ui/label'
import { Search, Loader2, RefreshCw, PlayCircle, CheckCircle, XCircle, Clock } from 'lucide-react'

export default function Jobs(){
  const [jid,setJid]=useState('');
  const [out,setOut]=useState('');
  const [loading,setLoading]=useState(false);
  const [jobs, setJobs] = useState<any[]>([]);
  
  async function check(id?: string){ 
    const targetId = id || jid;
    if(!targetId.trim()) return;
    setLoading(true);
    try {
      const r=await fetch('/api/knowledge/jobs/'+targetId); 
      setOut(JSON.stringify(await r.json(),null,2)); 
      if (id) setJid(id);
    } finally {
      setLoading(false);
    }
  }

  async function fetchRecentJobs(){
    try {
        const r = await fetch('/api/knowledge/jobs');
        if (r.ok) {
            const data = await r.json();
            setJobs(data.jobs || []);
        }
    } catch(e) {
        console.error(e);
    }
  }

  useEffect(() => {
      fetchRecentJobs();
      const interval = setInterval(fetchRecentJobs, 5000); // Auto-refresh
      return () => clearInterval(interval);
  }, []);
  
  return (
    <div className="container max-w-4xl mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
            <h1 className="text-3xl font-bold text-text">Background Jobs</h1>
            <p className="text-dim mt-1">Check status of ingestion and processing jobs</p>
        </div>
        <Button variant="outline" onClick={fetchRecentJobs}><RefreshCw className="h-4 w-4 mr-2" /> Refresh</Button>
      </div>

      {/* Recent Jobs List */}
      <Card>
          <CardHeader>
              <CardTitle>Recent Jobs</CardTitle>
          </CardHeader>
          <CardContent>
              {jobs.length === 0 ? (
                  <p className="text-muted-foreground text-center py-4">No jobs found.</p>
              ) : (
                  <div className="space-y-2">
                      {jobs.map(job => (
                          <div 
                            key={job.job_id} 
                            className="flex items-center justify-between p-3 rounded-lg border border-border bg-card hover:bg-accent/10 cursor-pointer transition-colors"
                            onClick={() => check(job.job_id)}
                          >
                              <div className="flex items-center gap-3">
                                  {job.status === 'done' || job.status === 'finished' ? <CheckCircle className="h-5 w-5 text-green-500" /> :
                                   job.status === 'failed' || job.status === 'error' ? <XCircle className="h-5 w-5 text-red-500" /> :
                                   job.status === 'running' || job.status === 'started' ? <PlayCircle className="h-5 w-5 text-blue-500 animate-pulse" /> :
                                   <Clock className="h-5 w-5 text-yellow-500" />}
                                  <div>
                                      <p className="font-medium text-sm">{job.type}</p>
                                      <p className="text-xs text-muted-foreground font-mono">{job.job_id.substring(0, 8)}...</p>
                                  </div>
                              </div>
                              <div className="text-right">
                                  <p className={`text-sm font-bold capitalize ${
                                      job.status === 'done' ? 'text-green-500' : 
                                      job.status === 'failed' ? 'text-red-500' : 
                                      'text-blue-500'
                                  }`}>{job.status}</p>
                                  <p className="text-xs text-muted-foreground">{new Date(job.created_at * 1000).toLocaleTimeString()}</p>
                              </div>
                          </div>
                      ))}
                  </div>
              )}
          </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Job Details</CardTitle>
          <CardDescription>Inspect full output of a selected job</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="job-id">Job ID</Label>
            <div className="flex gap-2">
              <Input 
                id="job-id"
                placeholder="Enter job ID" 
                value={jid} 
                onChange={e=>setJid(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && check()}
                className="font-mono"
              />
              <Button onClick={() => check()} disabled={loading || !jid.trim()}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              </Button>
            </div>
          </div>
          {out && (
            <pre className="p-4 rounded-lg bg-gray-950 border border-gray-800 text-xs text-green-400 overflow-x-auto max-h-96 font-mono">
                {out}
            </pre>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
