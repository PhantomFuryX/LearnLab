import React, { useState } from 'react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Label } from '../components/ui/label';
import { Input } from '../components/ui/input';
import { Loader2, CheckCircle, XCircle, HelpCircle } from 'lucide-react';
import { useAuth } from '../lib/authStore';

interface Question {
  id: string;
  type: string;
  question: string;
  options: string[];
  difficulty: string;
}

interface Quiz {
  title: string;
  description: string;
  questions: Question[];
}

interface SubmissionResult {
  score: number;
  total: number;
  percentage: number;
  results: {
    question_id: string;
    correct: boolean;
    feedback: string;
    correct_answer: string;
  }[];
}

export default function QuizView() {
  const [topic, setTopic] = useState('');
  const [loading, setLoading] = useState(false);
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<SubmissionResult | null>(null);
  const token = useAuth(s => s.token);

  const handleGenerate = async () => {
    if (!topic.trim()) return;
    setLoading(true);
    setQuiz(null);
    setResult(null);
    setAnswers({});
    
    try {
      const res = await fetch('/api/quiz/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({ topic, num_questions: 5 })
      });
      
      if (!res.ok) throw new Error('Failed to generate quiz');
      const data = await res.json();
      setQuiz(data);
    } catch (error) {
      console.error(error);
      alert('Failed to generate quiz');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!quiz) return;
    setLoading(true);
    
    const submissions = Object.entries(answers).map(([qid, ans]) => ({
      question_id: qid,
      user_answer: ans
    }));
    
    try {
      const res = await fetch('/api/quiz/grade', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({ quiz, submissions })
      });
      
      if (!res.ok) throw new Error('Failed to grade quiz');
      const data = await res.json();
      setResult(data);
    } catch (error) {
      console.error(error);
      alert('Failed to submit quiz');
    } finally {
      setLoading(false);
    }
  };

  const getFeedback = (qid: string) => {
    if (!result) return null;
    return result.results.find(r => r.question_id === qid);
  };

  return (
    <div className="container mx-auto p-6 max-w-3xl space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">AI Quiz Generator</h1>
          <p className="text-muted-foreground">Test your knowledge on any topic</p>
        </div>
      </div>

      {/* Generation Form */}
      {!quiz && (
        <Card>
          <CardHeader>
            <CardTitle>Create a New Quiz</CardTitle>
            <CardDescription>Enter a topic to generate a custom quiz instantly.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="topic">Topic</Label>
              <div className="flex gap-2">
                <Input 
                  id="topic" 
                  placeholder="e.g., React Hooks, Python Asyncio, Docker Networking" 
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
                />
                <Button onClick={handleGenerate} disabled={loading || !topic.trim()}>
                  {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                  Generate
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quiz View */}
      {quiz && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle>{quiz.title}</CardTitle>
                  <CardDescription>{quiz.description}</CardDescription>
                </div>
                <Button variant="ghost" size="sm" onClick={() => { setQuiz(null); setResult(null); setTopic(''); }}>
                  New Quiz
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-8">
              {quiz.questions.map((q, idx) => {
                const feedback = getFeedback(q.id);
                const isCorrect = feedback?.correct;
                
                return (
                  <div key={q.id} className={`p-4 rounded-lg border ${feedback ? (isCorrect ? 'border-green-500/50 bg-green-500/10' : 'border-red-500/50 bg-red-500/10') : 'border-border'}`}>
                    <div className="flex gap-3">
                      <div className="flex-shrink-0 mt-1">
                        <div className="h-6 w-6 rounded-full bg-secondary flex items-center justify-center text-xs font-bold">
                          {idx + 1}
                        </div>
                      </div>
                      <div className="flex-grow space-y-3">
                        <p className="font-medium text-lg">{q.question}</p>
                        
                        <div className="space-y-2">
                          {q.options?.map((opt) => (
                            <label 
                              key={opt} 
                              className={`flex items-center p-3 rounded-md border cursor-pointer transition-colors ${
                                answers[q.id] === opt 
                                  ? 'border-primary bg-primary/10' 
                                  : 'border-border hover:bg-accent'
                              } ${result ? 'pointer-events-none opacity-80' : ''}`}
                            >
                              <input 
                                type="radio" 
                                name={q.id} 
                                value={opt}
                                checked={answers[q.id] === opt}
                                onChange={() => setAnswers({...answers, [q.id]: opt})}
                                className="mr-3 h-4 w-4 accent-primary"
                                disabled={!!result}
                              />
                              <span>{opt}</span>
                            </label>
                          ))}
                        </div>

                        {feedback && (
                          <div className="mt-4 pt-4 border-t border-border/50 text-sm">
                            <div className="flex items-center gap-2 mb-1">
                              {isCorrect ? (
                                <span className="text-green-500 flex items-center font-bold"><CheckCircle className="h-4 w-4 mr-1"/> Correct</span>
                              ) : (
                                <span className="text-red-500 flex items-center font-bold"><XCircle className="h-4 w-4 mr-1"/> Incorrect</span>
                              )}
                            </div>
                            {!isCorrect && (
                                <p className="text-dim mb-1">Correct Answer: <span className="font-mono text-text">{feedback.correct_answer}</span></p>
                            )}
                            <p className="text-muted-foreground">{feedback.feedback}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {!result && (
             <div className="flex justify-end">
                <Button size="lg" onClick={handleSubmit} disabled={loading || Object.keys(answers).length < quiz.questions.length}>
                  {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                  Submit Quiz
                </Button>
             </div>
          )}
          
          {result && (
              <Card className="border-green-500/20 bg-green-500/5">
                  <CardContent className="p-6 flex items-center justify-between">
                      <div>
                          <h3 className="text-2xl font-bold">Score: {result.score} / {result.total}</h3>
                          <p className="text-muted-foreground">You scored {result.percentage}%</p>
                      </div>
                      <Button onClick={() => { setQuiz(null); setResult(null); setTopic(''); }}>
                          Take Another Quiz
                      </Button>
                  </CardContent>
              </Card>
          )}
        </div>
      )}
    </div>
  );
}
