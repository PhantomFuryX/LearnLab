import React, { useState, useEffect } from 'react';
import { Timeline } from '../components/Timeline';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Award, Calendar, Clock, Flame, Settings, Loader2, BookOpen, ChevronRight, Layout, BarChart3, Trophy } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

export default function Dashboard() {
  const navigate = useNavigate();
  const [plans, setPlans] = useState<any[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [planDetails, setPlanDetails] = useState<any>(null);
  const [progress, setProgress] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPlans();
  }, []);

  useEffect(() => {
    if (selectedPlanId) {
      fetchPlanDetails(selectedPlanId);
      fetchProgress(selectedPlanId);
    }
  }, [selectedPlanId]);

  const fetchPlans = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/api/v1/plans/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setPlans(data.plans || []);
        if (data.plans && data.plans.length > 0 && !selectedPlanId) {
          setSelectedPlanId(data.plans[0]._id);
        }
      }
    } catch (e) {
      console.error("Failed to fetch plans", e);
    } finally {
      setLoading(false);
    }
  };

  const fetchPlanDetails = async (id: string) => {
    try {
        const token = localStorage.getItem('access_token');
        const res = await fetch(`/api/v1/plans/${id}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) setPlanDetails(await res.json());
    } catch(e) { console.error(e); }
  };

  const fetchProgress = async (id: string) => {
      try {
        const token = localStorage.getItem('access_token');
        const res = await fetch(`/api/v1/plans/${id}/progress`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) setProgress(await res.json());
    } catch(e) { console.error(e); }
  };

  const handleStartModule = (modId: string) => {
    const module = planDetails?.modules?.find((m:any) => m.module_id === modId);
    if (module) {
        const prompt = `Teach me about ${module.title}. ${module.description}`;
        navigate(`/?prompt=${encodeURIComponent(prompt)}`);
    } else {
        navigate(`/?prompt=Teach me about module ${modId}`);
    }
  };

  const handleMarkComplete = async (modId: string) => {
      if (!selectedPlanId) return;
      try {
        const token = localStorage.getItem('access_token');
        const res = await fetch(`/api/v1/plans/${selectedPlanId}/modules/${modId}`, {
            method: 'PATCH',
            headers: { 
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                status: 'completed',
                time_spent_hours: 2, // Default or prompt user
                quiz_score: null
            })
        });
        if (res.ok) {
            // Refresh progress
            fetchProgress(selectedPlanId);
        }
      } catch (e) {
          console.error("Failed to mark complete", e);
      }
  };

  const handleTakeQuiz = (quiz: any) => {
      // Navigate to quiz page with topic
      const topic = (quiz.topics && quiz.topics.length > 0) ? quiz.topics.join(', ') : "General Review";
      navigate(`/quiz?topic=${encodeURIComponent(topic)}`);
  };

  if (loading) {
    return <div className="flex h-screen items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>;
  }

  // Derived Stats
  const completedCount = progress?.completed_modules?.length || 0;
  const totalModules = planDetails?.modules?.length || 0;
  const completionPct = totalModules > 0 ? Math.round((completedCount / totalModules) * 100) : 0;
  const hoursSpent = progress?.total_hours_spent || 0;
  const streak = progress?.streak_days || 0;
  
  // Current Module Logic
  let currentModule = null;
  let nextUpWeek = 1;
  if (planDetails && planDetails.modules) {
      const completedIds = (progress?.completed_modules || []).map((m:any) => m.module_id);
      currentModule = planDetails.modules.find((m:any) => !completedIds.includes(m.module_id));
      if (currentModule) nextUpWeek = currentModule.week;
      else nextUpWeek = planDetails.duration_weeks; // All done
  }

  return (
    <div className="container mx-auto p-6 flex gap-8">
      
      {/* Left Sidebar: My Plans */}
      <div className="w-64 flex-shrink-0 space-y-6 hidden lg:block">
         <div className="flex items-center gap-2 mb-4">
            <Layout className="h-5 w-5" />
            <h2 className="font-bold text-lg">My Plans</h2>
         </div>
         <div className="space-y-2">
            {plans.map(p => (
                <div 
                    key={p._id}
                    onClick={() => setSelectedPlanId(p._id)}
                    className={`p-3 rounded-lg cursor-pointer transition-all border ${
                        selectedPlanId === p._id 
                        ? 'bg-accent/20 border-accent text-foreground shadow-sm' 
                        : 'bg-card border-border text-muted-foreground hover:bg-accent/10'
                    }`}
                >
                    <h3 className="font-semibold text-sm truncate">{p.plan_title}</h3>
                    <div className="flex justify-between items-center mt-2">
                       <span className="text-xs text-muted-foreground">{p.duration_weeks} Weeks</span>
                       {/* Mini Progress Bar could go here */}
                    </div>
                </div>
            ))}
            
            <Link to="/planner/new">
                <Button variant="outline" className="w-full border-dashed mt-4">
                    + Create New Plan
                </Button>
            </Link>
         </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 space-y-8 min-w-0">
        {/* Header */}
        <div className="flex justify-between items-start">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">{planDetails?.plan_title || "Dashboard"}</h1>
                <p className="text-muted-foreground mt-1">
                   {currentModule ? `Continue Learning: ${currentModule.title}` : "All caught up!"}
                </p>
            </div>
            <div className="flex gap-2">
                <Link to="/settings">
                    <Button variant="outline" size="icon">
                        <Settings className="h-5 w-5" />
                    </Button>
                </Link>
            </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
            <CardContent className="pt-6 flex flex-col items-center text-center">
                <div className="p-3 rounded-full bg-blue-500/10 mb-3">
                <Award className="h-6 w-6 text-blue-500" />
                </div>
                <div className="text-2xl font-bold">{completionPct}%</div>
                <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Completion</div>
            </CardContent>
            </Card>
            
            <Card>
            <CardContent className="pt-6 flex flex-col items-center text-center">
                <div className="p-3 rounded-full bg-green-500/10 mb-3">
                <Clock className="h-6 w-6 text-green-500" />
                </div>
                <div className="text-2xl font-bold">{hoursSpent.toFixed(1)}h</div>
                <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Time Spent</div>
            </CardContent>
            </Card>

            <Card>
            <CardContent className="pt-6 flex flex-col items-center text-center">
                <div className="p-3 rounded-full bg-orange-500/10 mb-3">
                <Flame className="h-6 w-6 text-orange-500" />
                </div>
                <div className="text-2xl font-bold">{streak} Days</div>
                <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Streak</div>
            </CardContent>
            </Card>

            <Card>
            <CardContent className="pt-6 flex flex-col items-center text-center">
                <div className="p-3 rounded-full bg-purple-500/10 mb-3">
                <Calendar className="h-6 w-6 text-purple-500" />
                </div>
                <div className="text-2xl font-bold">Week {nextUpWeek}</div>
                <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Current Week</div>
            </CardContent>
            </Card>
        </div>

        {/* "Start Learning" Hero Section */}
        {currentModule && (
             <div className="relative overflow-hidden rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 p-6 text-white shadow-lg">
                <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div>
                        <div className="flex items-center gap-2 text-blue-100 mb-1 text-sm font-medium">
                            <BookOpen className="h-4 w-4" />
                            <span>Up Next</span>
                        </div>
                        <h3 className="text-2xl font-bold mb-1">{currentModule.title}</h3>
                        <p className="text-blue-100 max-w-xl line-clamp-1">{currentModule.description}</p>
                    </div>
                    <Button 
                        onClick={() => handleStartModule(currentModule.module_id)}
                        size="lg" 
                        className="bg-white text-blue-600 hover:bg-blue-50 border-none font-semibold shadow-md whitespace-nowrap"
                    >
                        Start Learning <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                </div>
                {/* Background Pattern */}
                <div className="absolute top-0 right-0 -mt-10 -mr-10 h-40 w-40 rounded-full bg-white/10 blur-3xl"></div>
                <div className="absolute bottom-0 left-0 -mb-10 -ml-10 h-40 w-40 rounded-full bg-black/10 blur-3xl"></div>
            </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Main Timeline */}
            <div className="lg:col-span-2 space-y-6">
                <div className="flex items-center justify-between">
                    <h3 className="text-xl font-bold flex items-center gap-2">
                        <BarChart3 className="h-5 w-5 text-muted-foreground" />
                        Course Curriculum
                    </h3>
                </div>
                {planDetails && (
                    <Timeline 
                        modules={planDetails.modules || []} 
                        completedModuleIds={(progress?.completed_modules || []).map((m:any) => m.module_id)}
                        onStartModule={handleStartModule}
                        onMarkComplete={handleMarkComplete}
                        onTakeQuiz={handleTakeQuiz}
                        quizSchedule={planDetails.quiz_schedule || []}
                    />
                )}
            </div>

            {/* Right Sidebar Widgets */}
            <div className="space-y-6">
                {/* Quiz Performance */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Trophy className="h-5 w-5 text-yellow-500" />
                            Quiz Performance
                        </CardTitle>
                        <CardDescription>Your recent scores</CardDescription>
                    </CardHeader>
                    <CardContent>
                        {progress?.average_quiz_score !== null ? (
                            <div className="space-y-4">
                                <div className="flex items-center justify-center py-4">
                                    <div className="relative flex items-center justify-center h-32 w-32 rounded-full border-8 border-green-500/20">
                                        <div className="absolute text-3xl font-bold text-green-500">
                                            {Math.round(progress?.average_quiz_score || 0)}%
                                        </div>
                                        <svg className="absolute h-full w-full -rotate-90 transform" viewBox="0 0 100 100">
                                            <circle
                                                className="text-green-500"
                                                strokeWidth="8"
                                                strokeDasharray={`${(progress?.average_quiz_score || 0) * 2.51} 251`}
                                                strokeLinecap="round"
                                                stroke="currentColor"
                                                fill="transparent"
                                                r="40"
                                                cx="50"
                                                cy="50"
                                            />
                                        </svg>
                                    </div>
                                </div>
                                <p className="text-center text-sm text-muted-foreground">Average Score</p>
                            </div>
                        ) : (
                            <div className="text-center py-8 text-muted-foreground">
                                No quizzes taken yet.
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Milestones */}
                <Card>
                    <CardHeader>
                        <CardTitle>Milestones</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {(planDetails?.milestones || []).map((m: any) => (
                                <div key={m.milestone_id} className="flex gap-3 items-start p-3 rounded-lg bg-accent/30 border border-accent/50">
                                    <div className="mt-0.5 bg-accent p-1 rounded-full">
                                        <Award className="h-4 w-4 text-foreground" />
                                    </div>
                                    <div>
                                        <h4 className="text-sm font-semibold">{m.title}</h4>
                                        <p className="text-xs text-muted-foreground mt-0.5">Week {m.week} • {m.type}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
      </div>
    </div>
  );
}
