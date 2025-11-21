import React, { useState } from 'react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';

export default function PlanCreation() {
  const navigate = useNavigate();
  const [goal, setGoal] = useState('');
  const [skillLevel, setSkillLevel] = useState('beginner');
  const [hoursPerWeek, setHoursPerWeek] = useState(5);
  const [duration, setDuration] = useState('4');
  const [topics, setTopics] = useState<string[]>([]);
  const [customTopic, setCustomTopic] = useState('');
  const [loading, setLoading] = useState(false);

  const availableTopics = ['React', 'Node.js', 'Python', 'Machine Learning', 'System Design', 'DevOps'];

  const toggleTopic = (topic: string) => {
    if (topics.includes(topic)) {
      setTopics(topics.filter(t => t !== topic));
    } else {
      setTopics([...topics, topic]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/api/v1/plans/', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          goal,
          skill_level: skillLevel,
          hours_per_week: hoursPerWeek,
          duration_weeks: parseInt(duration),
          topics: topics.length > 0 ? topics : [goal],
          include_past_summaries: true
        })
      });

      if (res.ok) {
        navigate('/dashboard');
      } else {
        const err = await res.json();
        alert(`Failed to create plan: ${err.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error("Plan creation error", error);
      alert("Network error creating plan");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>Create Your Learning Plan</CardTitle>
          <CardDescription>Define your goals and availability to generate a personalized roadmap.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            
            {/* Goal Input */}
            <div className="space-y-2">
              <Label htmlFor="goal">Main Goal</Label>
              <Input 
                id="goal" 
                placeholder="e.g., Become a Senior React Developer" 
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                required
              />
            </div>

            {/* Skill Level Selector */}
            <div className="space-y-2">
              <Label htmlFor="skill-level">Current Skill Level</Label>
              <select 
                id="skill-level"
                className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                value={skillLevel}
                onChange={(e) => setSkillLevel(e.target.value)}
              >
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>

            {/* Hours per week Slider */}
            <div className="space-y-2">
              <div className="flex justify-between">
                <Label htmlFor="hours">Time Commitment</Label>
                <span className="text-sm text-muted-foreground">{hoursPerWeek} hours/week</span>
              </div>
              <input 
                id="hours"
                type="range" 
                min="1" 
                max="40" 
                value={hoursPerWeek}
                onChange={(e) => setHoursPerWeek(Number(e.target.value))}
                className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer"
              />
            </div>

            {/* Duration Selector */}
            <div className="space-y-2">
              <Label htmlFor="duration">Target Duration (Weeks)</Label>
              <select 
                id="duration"
                className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
              >
                <option value="2">2 Weeks (Crash Course)</option>
                <option value="4">4 Weeks (Standard)</option>
                <option value="8">8 Weeks (In-depth)</option>
                <option value="12">12 Weeks (Mastery)</option>
              </select>
            </div>

            {/* Topics Multi-select */}
            <div className="space-y-2">
              <Label>Topics of Interest</Label>
              <div className="flex flex-wrap gap-2 mt-2">
                {availableTopics.map(topic => (
                  <button
                    key={topic}
                    type="button"
                    onClick={() => toggleTopic(topic)}
                    className={`px-3 py-1 text-sm rounded-full transition-colors ${
                      topics.includes(topic) 
                        ? 'bg-primary text-primary-foreground' 
                        : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                    }`}
                  >
                    {topic}
                  </button>
                ))}
              </div>
              <div className="flex gap-2 mt-2">
                <Input 
                  placeholder="Add custom topic..." 
                  value={customTopic}
                  onChange={(e) => setCustomTopic(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      if (customTopic.trim()) {
                        toggleTopic(customTopic.trim());
                        setCustomTopic('');
                      }
                    }
                  }}
                />
                <Button 
                  type="button" 
                  variant="outline"
                  onClick={() => {
                    if (customTopic.trim()) {
                      toggleTopic(customTopic.trim());
                      setCustomTopic('');
                    }
                  }}
                >
                  Add
                </Button>
              </div>
            </div>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating Plan...
                </>
              ) : (
                'Generate Plan'
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
