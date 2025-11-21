import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Loader2, Play, Zap, CheckCircle, AlertCircle } from 'lucide-react';

export default function Automation() {
  const [action, setAction] = useState('');
  const [payload, setPayload] = useState('{}');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const handleRun = async () => {
    setLoading(true);
    setResult(null);
    setError('');
    
    try {
      let parsedData = {};
      try {
        parsedData = JSON.parse(payload);
      } catch (e) {
        throw new Error("Invalid JSON payload");
      }

      const res = await fetch('/api/automate/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          payload: {
            n8n_action: action,
            data: parsedData
          }
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Automation failed");
      }

      const data = await res.json();
      setResult(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text">Automation Manager</h1>
          <p className="text-dim mt-1">Trigger n8n workflows and custom automations</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Quick Actions */}
        <Card className="md:col-span-1 h-fit">
          <CardHeader>
            <CardTitle className="text-lg">Quick Actions</CardTitle>
            <CardDescription>Common workflows</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button variant="outline" className="w-full justify-start" onClick={() => setAction('summarize_email')}>
              <Zap className="mr-2 h-4 w-4 text-yellow-500" /> Summarize Emails
            </Button>
            <Button variant="outline" className="w-full justify-start" onClick={() => setAction('social_post')}>
              <Zap className="mr-2 h-4 w-4 text-blue-500" /> Post to Socials
            </Button>
            <Button variant="outline" className="w-full justify-start" onClick={() => setAction('daily_report')}>
              <Zap className="mr-2 h-4 w-4 text-green-500" /> Generate Report
            </Button>
          </CardContent>
        </Card>

        {/* Main Runner */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Run Workflow</CardTitle>
            <CardDescription>Execute a specific n8n action</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="action">Action Name (Webhook ID)</Label>
              <Input 
                id="action" 
                value={action} 
                onChange={e => setAction(e.target.value)} 
                placeholder="e.g. my-workflow-1" 
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="payload">JSON Payload</Label>
              <Textarea 
                id="payload" 
                value={payload} 
                onChange={e => setPayload(e.target.value)} 
                rows={6}
                className="font-mono text-xs"
              />
            </div>

            <Button onClick={handleRun} disabled={loading || !action} className="w-full">
              {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
              Execute Workflow
            </Button>

            {error && (
              <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 flex items-start gap-3 text-red-400">
                <AlertCircle className="h-5 w-5 flex-shrink-0" />
                <p className="text-sm">{error}</p>
              </div>
            )}

            {result && (
              <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20 space-y-2">
                <div className="flex items-center gap-2 text-green-400 font-semibold">
                  <CheckCircle className="h-5 w-5" />
                  <span>Execution Successful</span>
                </div>
                <pre className="text-xs text-dim overflow-x-auto max-h-60 bg-black/20 p-2 rounded">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
