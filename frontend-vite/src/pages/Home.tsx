import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { 
  MessageSquare, 
  Map, 
  GraduationCap, 
  Search, 
  Database, 
  Code2, 
  BookOpen, 
  ArrowRight, 
  Bot,
  Sparkles
} from 'lucide-react';

const agents = [
  {
    id: 'tutor',
    title: 'AI Tutor',
    description: 'Chat with an advanced AI assistant to learn new concepts, debug code, or get explanations.',
    icon: MessageSquare,
    color: 'text-blue-500',
    bg: 'bg-blue-500/10',
    route: '/chat'
  },
  {
    id: 'planner',
    title: 'Curriculum Planner',
    description: 'Generate personalized learning paths, schedules, and milestones for any skill.',
    icon: Map,
    color: 'text-purple-500',
    bg: 'bg-purple-500/10',
    route: '/dashboard'
  },
  {
    id: 'quiz',
    title: 'Quiz Master',
    description: 'Test your knowledge with AI-generated quizzes on any topic or from your learning plan.',
    icon: GraduationCap,
    color: 'text-green-500',
    bg: 'bg-green-500/10',
    route: '/quiz'
  },
  {
    id: 'researcher',
    title: 'Deep Researcher',
    description: 'Conduct autonomous web research to gather comprehensive reports and summaries.',
    icon: Search,
    color: 'text-orange-500',
    bg: 'bg-orange-500/10',
    route: '/research'
  },
  {
    id: 'librarian',
    title: 'Knowledge Base',
    description: 'Ingest documents, websites, and videos to build your personal knowledge graph.',
    icon: Database,
    color: 'text-cyan-500',
    bg: 'bg-cyan-500/10',
    route: '/ingest'
  },
  {
    id: 'feed',
    title: 'Learning Feed',
    description: 'Stay updated with curated content, RSS feeds, and AI-summarized news.',
    icon: BookOpen,
    color: 'text-pink-500',
    bg: 'bg-pink-500/10',
    route: '/feed'
  }
];

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="container mx-auto p-8 max-w-7xl">
      <div className="mb-10 text-center">
        <div className="inline-flex items-center justify-center p-3 bg-primary/10 rounded-full mb-4">
            <Bot className="h-8 w-8 text-primary" />
        </div>
        <h1 className="text-4xl font-bold tracking-tight mb-3">Welcome to LearnLab</h1>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Your AI-powered personal learning environment. Select an agent to get started.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {agents.map((agent) => (
          <Card 
            key={agent.id} 
            className="group hover:shadow-lg transition-all cursor-pointer border-border/50 hover:border-primary/50"
            onClick={() => navigate(agent.route)}
          >
            <CardHeader>
              <div className={`w-12 h-12 rounded-lg flex items-center justify-center mb-4 ${agent.bg}`}>
                <agent.icon className={`h-6 w-6 ${agent.color}`} />
              </div>
              <CardTitle className="group-hover:text-primary transition-colors flex items-center justify-between">
                {agent.title}
              </CardTitle>
              <CardDescription>
                {agent.description}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Optional content area */}
            </CardContent>
            <CardFooter>
              <Button variant="ghost" className="w-full justify-between group-hover:bg-secondary">
                Open Agent <ArrowRight className="h-4 w-4 ml-2 group-hover:translate-x-1 transition-transform" />
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>

      <div className="mt-16 p-8 rounded-2xl bg-gradient-to-r from-gray-900 to-gray-800 border border-gray-700">
         <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div>
                <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-yellow-400" /> 
                    Quick Start
                </h2>
                <p className="text-gray-400">Want to jump right into coding? Use our code generator.</p>
            </div>
            <div className="flex gap-4">
                <Button onClick={() => navigate('/chat')} className="bg-white text-black hover:bg-gray-200">
                    <Code2 className="h-4 w-4 mr-2" />
                    Code Generator
                </Button>
            </div>
         </div>
      </div>
    </div>
  );
}
