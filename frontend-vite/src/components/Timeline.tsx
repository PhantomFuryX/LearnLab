import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { CheckCircle, Circle, Clock, PlayCircle, BookOpen, BrainCircuit } from 'lucide-react';
import { Button } from './ui/button';

interface Module {
  module_id: string;
  week: number;
  title: string;
  estimated_hours: number;
  description: string;
}

interface TimelineProps {
  modules: Module[];
  completedModuleIds: string[];
  onStartModule: (moduleId: string) => void;
  onMarkComplete: (moduleId: string) => void;
  onTakeQuiz: (quiz: any) => void;
  quizSchedule?: any[];
}

export function Timeline({ modules, completedModuleIds, onStartModule, onMarkComplete, onTakeQuiz, quizSchedule = [] }: TimelineProps) {
  // Group by week
  const weeks = Array.from(new Set(modules.map(m => m.week))).sort((a,b) => a-b);

  const getStatus = (modId: string, index: number) => {
    if (completedModuleIds.includes(modId)) return 'completed';
    // If previous module is completed (or this is first), it's in-progress/available
    const prevMod = index > 0 ? modules[index-1] : null;
    if (!prevMod || completedModuleIds.includes(prevMod.module_id)) return 'in-progress';
    return 'locked';
  };

  return (
    <Card className="w-full border-none shadow-none bg-transparent">
      <CardHeader className="px-0">
        <CardTitle>Your Learning Timeline</CardTitle>
      </CardHeader>
      <CardContent className="px-0">
        <div className="space-y-8">
          {weeks.map(week => {
             const weekModules = modules.filter(m => m.week === week);
             const weekQuizzes = quizSchedule.filter(q => q.week === week);
             
             return (
            <div key={week} className="relative pl-6 border-l-2 border-gray-800 ml-3">
              <div className="absolute -left-[9px] top-0 h-4 w-4 rounded-full bg-gray-800 border-2 border-gray-950" />
              <div className="mb-4 font-semibold text-lg flex justify-between items-center">
                <span>Week {week}</span>
                {weekQuizzes.length > 0 && (
                   <div className="flex gap-2">
                     {weekQuizzes.map((q, i) => (
                        <Button key={i} variant="outline" size="sm" className="h-7 text-xs gap-2" onClick={() => onTakeQuiz(q)}>
                           <BrainCircuit className="h-3 w-3" />
                           Take Quiz
                        </Button>
                     ))}
                   </div>
                )}
              </div>
              <div className="space-y-4">
                {weekModules.map((module, idx) => {
                   // We need global index to check previous module correctly across weeks, 
                   // but simply checking if it's the first uncompleted one is easier in parent. 
                   // Here we assume passed modules are sorted.
                   const globalIndex = modules.findIndex(m => m.module_id === module.module_id);
                   const status = getStatus(module.module_id, globalIndex);

                   return (
                  <div key={module.module_id} className={`flex flex-col gap-2 bg-card p-4 rounded-xl border ${status === 'in-progress' ? 'border-blue-500/30 bg-blue-500/5' : 'border-border'}`}>
                    <div className="flex items-start gap-4">
                        <div className="flex-shrink-0 mt-1">
                        {status === 'completed' ? (
                            <CheckCircle className="h-6 w-6 text-green-500" />
                        ) : status === 'in-progress' ? (
                            <PlayCircle className="h-6 w-6 text-blue-500 animate-pulse" />
                        ) : (
                            <Circle className="h-6 w-6 text-muted-foreground" />
                        )}
                        </div>
                        <div className="flex-grow">
                            <div className="flex justify-between items-start">
                                <h4 className={`font-medium text-base ${status === 'locked' ? 'text-muted-foreground' : 'text-foreground'}`}>{module.title}</h4>
                                <span className="text-xs text-muted-foreground bg-secondary px-2 py-1 rounded flex items-center gap-1">
                                    <Clock className="h-3 w-3" /> {module.estimated_hours}h
                                </span>
                            </div>
                            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{module.description}</p>
                            
                            {status === 'in-progress' && (
                                <div className="mt-4 flex gap-3">
                                    <Button size="sm" onClick={() => onStartModule(module.module_id)} className="gap-2">
                                        <BookOpen className="h-4 w-4" /> Start Learning
                                    </Button>
                                    <Button size="sm" variant="ghost" onClick={() => onMarkComplete(module.module_id)} className="gap-2 text-muted-foreground hover:text-foreground">
                                        Mark Complete
                                    </Button>
                                </div>
                            )}
                        </div>
                    </div>
                  </div>
                )})}
              </div>
            </div>
          )})}
        </div>
      </CardContent>
    </Card>
  );
}

