import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Loader2, Clock, Play, RefreshCw, Calendar } from 'lucide-react';

interface Job {
  id: string;
  name: string;
  next_run_time: string | null;
  trigger: string;
}

export default function Scheduler() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState<string | null>(null);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/scheduler/jobs', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
      });
      if (res.ok) {
        const data = await res.json();
        setJobs(data.jobs || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const triggerJob = async (jobId: string) => {
    setTriggering(jobId);
    try {
      const res = await fetch(`/api/scheduler/trigger/${jobId}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
      });
      if (res.ok) {
        alert(`Job ${jobId} triggered successfully`);
        fetchJobs(); // Refresh to see any status update if applicable
      } else {
        alert('Failed to trigger job');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setTriggering(null);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  return (
    <div className="container mx-auto p-6 max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text">Scheduler</h1>
          <p className="text-dim mt-1">Manage recurring background tasks</p>
        </div>
        <Button variant="outline" onClick={fetchJobs} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </Button>
      </div>

      <div className="grid gap-4">
        {jobs.map((job) => (
          <Card key={job.id} className="flex flex-col md:flex-row items-start md:items-center justify-between p-2">
            <CardHeader className="pb-2 md:pb-6">
              <CardTitle className="text-lg flex items-center gap-2">
                <Clock className="h-5 w-5 text-accent" />
                {job.name || job.id}
              </CardTitle>
              <CardDescription className="font-mono text-xs">
                ID: {job.id}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-1 md:text-right pt-0 md:pt-6">
              <div className="space-y-1 mb-4 md:mb-0">
                <p className="text-sm text-dim flex items-center md:justify-end gap-2">
                  <Calendar className="h-4 w-4" />
                  Next Run: {job.next_run_time ? new Date(job.next_run_time).toLocaleString() : 'Paused/None'}
                </p>
                <p className="text-xs text-muted-foreground">Trigger: {job.trigger}</p>
              </div>
            </CardContent>
            <div className="p-6 pt-0 md:pt-6 flex items-center">
                <Button 
                    size="sm" 
                    variant="secondary" 
                    onClick={() => triggerJob(job.id)}
                    disabled={triggering === job.id}
                >
                    {triggering === job.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4 mr-2" />}
                    Run Now
                </Button>
            </div>
          </Card>
        ))}

        {!loading && jobs.length === 0 && (
            <p className="text-center text-dim py-8">No scheduled jobs found.</p>
        )}
      </div>
    </div>
  );
}
