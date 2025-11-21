import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Label } from '../components/ui/label';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Loader2, Check, AlertCircle } from 'lucide-react';

export default function Settings() {
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  
  // Preferences
  const [emailReminders, setEmailReminders] = useState(true);
  const [pushReminders, setPushReminders] = useState(false);
  const [smsReminders, setSmsReminders] = useState(false);
  const [scheduleTime, setScheduleTime] = useState('09:00');
  
  // API Keys
  const [openaiKey, setOpenaiKey] = useState('');
  const [anthropicKey, setAnthropicKey] = useState('');

  // Load initial settings
  useEffect(() => {
    loadSettings();
  }, []);

  async function loadSettings() {
    setLoading(true);
    try {
      const res = await fetch('/api/auth/me', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
      });
      if (res.ok) {
        const data = await res.json();
        const p = data.profile || {};
        const k = data.api_keys || {};
        
        if (p.preferences) {
            setEmailReminders(p.preferences.emailReminders ?? true);
            setPushReminders(p.preferences.pushReminders ?? false);
            setSmsReminders(p.preferences.smsReminders ?? false);
            setScheduleTime(p.preferences.scheduleTime || '09:00');
        }
        if (k) {
            setOpenaiKey(k.openai || '');
            setAnthropicKey(k.anthropic || '');
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function saveSettings() {
    setLoading(true);
    setSaved(false);
    setError('');
    
    try {
      const res = await fetch('/api/auth/profile', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          profile: {
            preferences: {
                emailReminders,
                pushReminders,
                smsReminders,
                scheduleTime
            }
          },
          api_keys: {
              openai: openaiKey,
              anthropic: anthropicKey
          }
        })
      });
      
      if (!res.ok) throw new Error('Failed to save settings');
      
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      console.error(e);
      setError('Failed to save settings');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container mx-auto p-6 max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
            <h1 className="text-3xl font-bold text-text">Settings</h1>
            <p className="text-dim mt-1">Manage your preferences and API keys</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>API Configuration</CardTitle>
          <CardDescription>Bring your own API keys to use specific models (stored securely).</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
            <div className="grid gap-2">
                <Label htmlFor="openai">OpenAI API Key</Label>
                <Input 
                    id="openai" 
                    type="password" 
                    placeholder="sk-..." 
                    value={openaiKey}
                    onChange={(e) => setOpenaiKey(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">Required for GPT-4o models if not configured on server.</p>
            </div>
            <div className="grid gap-2">
                <Label htmlFor="anthropic">Anthropic API Key</Label>
                <Input 
                    id="anthropic" 
                    type="password" 
                    placeholder="sk-ant-..." 
                    value={anthropicKey}
                    onChange={(e) => setAnthropicKey(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">Required for Claude 3.5 models.</p>
            </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Reminder Settings</CardTitle>
          <CardDescription>Manage how and when you want to be reminded to learn.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          
          {/* Reminder Types */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Notification Channels</h3>
            
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="space-y-0.5">
                <Label className="text-base">Email Reminders</Label>
                <p className="text-sm text-muted-foreground">Receive daily summaries and due date alerts.</p>
              </div>
              <input 
                type="checkbox" 
                checked={emailReminders}
                onChange={(e) => setEmailReminders(e.target.checked)}
                className="h-5 w-5 accent-primary"
              />
            </div>

            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="space-y-0.5">
                <Label className="text-base">Push Notifications</Label>
                <p className="text-sm text-muted-foreground">Get instant alerts on your device.</p>
              </div>
              <input 
                type="checkbox" 
                checked={pushReminders}
                onChange={(e) => setPushReminders(e.target.checked)}
                className="h-5 w-5 accent-primary"
              />
            </div>

            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="space-y-0.5">
                <Label className="text-base">SMS Reminders</Label>
                <p className="text-sm text-muted-foreground">Get text messages for urgent deadlines.</p>
              </div>
               <input 
                type="checkbox" 
                checked={smsReminders}
                onChange={(e) => setSmsReminders(e.target.checked)}
                className="h-5 w-5 accent-primary"
              />
            </div>
          </div>

          {/* Schedule Editor */}
          <div className="space-y-4">
             <h3 className="text-lg font-medium">Schedule</h3>
             <div className="grid gap-2">
                <Label htmlFor="time">Preferred Reminder Time</Label>
                <Input 
                    id="time" 
                    type="time" 
                    value={scheduleTime}
                    onChange={(e) => setScheduleTime(e.target.value)}
                />
             </div>
          </div>

          {/* Test Button */}
          <div className="pt-4">
            <Button 
                variant="secondary" 
                onClick={() => alert('Test reminder sent!')}
                className="w-full"
            >
                Send Test Reminder
            </Button>
          </div>
          
           <div className="pt-4">
            <Button className="w-full" onClick={saveSettings} disabled={loading}>
                {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Check className="mr-2 h-4 w-4" />}
                Save Changes
            </Button>
            {saved && <p className="text-green-500 text-sm text-center mt-2">Settings saved successfully!</p>}
            {error && <p className="text-red-500 text-sm text-center mt-2">{error}</p>}
          </div>

        </CardContent>
      </Card>
    </div>
  );
}
