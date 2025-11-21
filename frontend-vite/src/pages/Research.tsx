import React, { useState, useEffect } from 'react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Textarea } from '../components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Label } from '../components/ui/label'
import { Search, Loader2, ExternalLink, Calendar, User, Sparkles, CheckCircle2, Code2, Copy, Check, Share2, Send } from 'lucide-react'

interface ResearchResult {
  source: string
  title: string
  link: string
  excerpt: string
  date?: string
  authors?: string[]
  categories?: string[]
  score: number
}

export default function Research(){
  const [query, setQuery] = useState('');
  const [sources, setSources] = useState(['arxiv', 'web']);
  const [maxResults, setMaxResults] = useState(10);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<ResearchResult[]>([]);
  const [searchMeta, setSearchMeta] = useState<any>(null);
  const [summarizing, setSummarizing] = useState(false);
  const [summaries, setSummaries] = useState<any>(null);
  const [generatingCode, setGeneratingCode] = useState(false);
  const [codeExamples, setCodeExamples] = useState<any>(null);
  const [selectedStack, setSelectedStack] = useState('langchain');
  const [copiedCode, setCopiedCode] = useState<number | null>(null);
  
  // Social Post State
  const [generatingPost, setGeneratingPost] = useState(false);
  const [postDraft, setPostDraft] = useState<any>(null);
  const [platform, setPlatform] = useState('linkedin');
  const [publishing, setPublishing] = useState(false);
  
  // Tabs
  const [activeTab, setActiveTab] = useState<'search' | 'history'>('search');
  const [postHistory, setPostHistory] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
      if (activeTab === 'history') {
          fetchPostHistory();
      }
  }, [activeTab]);

  async function fetchPostHistory() {
      setLoadingHistory(true);
      try {
          const res = await fetch('/api/post/history', {
              headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
          });
          if (res.ok) {
              const data = await res.json();
              setPostHistory(data.history || []);
          }
      } catch (e) {
          console.error(e);
      } finally {
          setLoadingHistory(false);
      }
  }

  async function performSearch() {
    if (!query.trim()) return;
    
    setLoading(true);
    setPostDraft(null);
    try {
      const response = await fetch('/api/research/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          query,
          sources,
          max_results: maxResults,
          namespace: 'default',
          store: true
        })
      });
      
      if (!response.ok) throw new Error('Search failed');
      
      const data = await response.json();
      setResults(data.results || []);
      setSearchMeta({
        total: data.total,
        timestamp: data.timestamp,
        storedId: data.stored_id
      });
      setSummaries(null); // Clear old summaries
    } catch (error) {
      console.error('Search error:', error);
      alert('Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  async function summarizeResults() {
    if (!searchMeta?.storedId) return;
    
    setSummarizing(true);
    try {
      const response = await fetch(`/api/summarize/research/${searchMeta.storedId}?aggregate=true`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });
      
      if (!response.ok) throw new Error('Summarization failed');
      
      const data = await response.json();
      setSummaries(data);
    } catch (error) {
      console.error('Summarization error:', error);
      alert('Summarization failed. Please try again.');
    } finally {
      setSummarizing(false);
    }
  }

  async function generateCode() {
    if (!summaries?.summary_id) return;
    
    setGeneratingCode(true);
    try {
      const response = await fetch(
        `/api/code/from-summary/${summaries.summary_id}?stack=${selectedStack}&language=python&max_examples=3`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        }
      );
      
      if (!response.ok) throw new Error('Code generation failed');
      
      const data = await response.json();
      setCodeExamples(data);
    } catch (error) {
      console.error('Code generation error:', error);
      alert('Code generation failed. Please try again.');
    } finally {
      setGeneratingCode(false);
    }
  }

  async function generatePost() {
      if (!summaries?.aggregate_summary?.synthesis) return;
      setGeneratingPost(true);
      try {
        const response = await fetch('/api/post/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({
                content: summaries.aggregate_summary.synthesis,
                platform: platform,
                tone: 'professional'
            })
        });
        if (!response.ok) throw new Error("Failed to generate post");
        const data = await response.json();
        setPostDraft(data);
      } catch (e) {
          console.error(e);
          alert("Failed to generate post draft");
      } finally {
          setGeneratingPost(false);
      }
  }

  async function publishPost() {
      if (!postDraft) return;
      setPublishing(true);
      try {
          const response = await fetch('/api/post/publish', {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${localStorage.getItem('access_token')}`
              },
              body: JSON.stringify({ post_data: postDraft })
          });
          if (!response.ok) throw new Error("Publish failed");
          alert("Post published successfully (to webhook)!");
          setPostDraft(null);
      } catch (e) {
          console.error(e);
          alert("Failed to publish post");
      } finally {
          setPublishing(false);
      }
  }

  function copyCode(code: string, index: number) {
    navigator.clipboard.writeText(code);
    setCopiedCode(index);
    setTimeout(() => setCopiedCode(null), 2000);
  }

  return (
    <div className="container max-w-6xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-text">Research & Content</h1>
          <p className="text-dim mt-1">Discover insights and manage social presence</p>
        </div>
        <div className="flex bg-gray-900 p-1 rounded-lg">
            <button 
                onClick={() => setActiveTab('search')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${activeTab === 'search' ? 'bg-primary text-white shadow-sm' : 'text-dim hover:text-text'}`}
            >
                Discover
            </button>
            <button 
                onClick={() => setActiveTab('history')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${activeTab === 'history' ? 'bg-primary text-white shadow-sm' : 'text-dim hover:text-text'}`}
            >
                Post History
            </button>
        </div>
      </div>

      {activeTab === 'history' ? (
          <div className="space-y-4">
              {loadingHistory && <div className="flex justify-center p-8"><Loader2 className="h-8 w-8 animate-spin" /></div>}
              
              {!loadingHistory && postHistory.length === 0 && (
                  <div className="text-center py-12 text-muted-foreground border border-dashed rounded-lg">
                      <p>No posts generated yet.</p>
                  </div>
              )}

              <div className="grid gap-4 md:grid-cols-2">
                  {postHistory.map((post) => (
                      <Card key={post._id} className="border-border/50">
                          <CardHeader className="pb-2">
                              <div className="flex justify-between items-start">
                                  <div className="flex items-center gap-2">
                                      <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${
                                          post.platform === 'linkedin' ? 'bg-blue-900/30 text-blue-400' : 'bg-sky-900/30 text-sky-400'
                                      }`}>
                                          {post.platform}
                                      </span>
                                      <span className={`px-2 py-1 rounded text-xs ${
                                          post.status === 'published' ? 'bg-green-900/30 text-green-400' : 'bg-yellow-900/30 text-yellow-400'
                                      }`}>
                                          {post.status}
                                      </span>
                                  </div>
                                  <span className="text-xs text-dim">{new Date(post.created_at * 1000).toLocaleDateString()}</span>
                              </div>
                          </CardHeader>
                          <CardContent>
                              <div className="bg-gray-950/50 p-3 rounded-md border border-gray-800 mb-3">
                                <p className="text-sm whitespace-pre-wrap line-clamp-6">
                                    {typeof post.content?.post_text === 'string' 
                                        ? post.content.post_text 
                                        : Array.isArray(post.content?.post_text) 
                                            ? post.content.post_text.join('\n\n') 
                                            : 'No content'}
                                </p>
                              </div>
                              <div className="flex justify-between items-center text-xs text-dim">
                                  <span>Tone: {post.tone}</span>
                                  {post.content?.hashtags && (
                                      <span className="truncate max-w-[200px]">{post.content.hashtags.join(' ')}</span>
                                  )}
                              </div>
                          </CardContent>
                      </Card>
                  ))}
              </div>
          </div>
      ) : (
      <>
      <Card>
        <CardHeader>
          <CardTitle>Search Parameters</CardTitle>
          <CardDescription>Find the latest AI research and knowledge</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="query">Research Topic</Label>
            <Input 
              id="query"
              value={query} 
              onChange={e => setQuery(e.target.value)} 
              placeholder="e.g., 'agentic AI architectures', 'RAG systems', 'transformer models'"
              onKeyDown={e => e.key === 'Enter' && performSearch()}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Sources</Label>
              <div className="flex gap-4">
                <label className="flex items-center">
                  <input 
                    type="checkbox" 
                    checked={sources.includes('arxiv')}
                    onChange={e => {
                      if (e.target.checked) setSources([...sources, 'arxiv']);
                      else setSources(sources.filter(s => s !== 'arxiv'));
                    }}
                    className="mr-2"
                  />
                  arXiv
                </label>
                <label className="flex items-center">
                  <input 
                    type="checkbox" 
                    checked={sources.includes('web')}
                    onChange={e => {
                      if (e.target.checked) setSources([...sources, 'web']);
                      else setSources(sources.filter(s => s !== 'web'));
                    }}
                    className="mr-2"
                  />
                  Web
                </label>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="maxResults">Max Results</Label>
              <Input 
                id="maxResults"
                type="number" 
                value={maxResults} 
                onChange={e => setMaxResults(parseInt(e.target.value) || 10)}
                min="1"
                max="50"
              />
            </div>
          </div>

          <Button 
            onClick={performSearch} 
            disabled={loading || !query.trim() || sources.length === 0}
            className="w-full"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Searching...
              </>
            ) : (
              <>
                <Search className="mr-2 h-4 w-4" />
                Search Research
              </>
            )}
          </Button>
        </CardContent>
      </Card>
      
      {/* Search Meta & Summary Trigger */}
      {searchMeta && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-dim">
            Found {searchMeta.total} results • {new Date(searchMeta.timestamp).toLocaleString()}
          </div>
          {results.length > 0 && !summaries && (
            <Button 
              onClick={summarizeResults} 
              disabled={summarizing}
              variant="outline"
            >
              {summarizing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Summarizing...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Generate Summaries
                </>
              )}
            </Button>
          )}
        </div>
      )}

      {/* Summary Section */}
      {summaries && summaries.aggregate_summary && (
        <Card className="border-accent/50 bg-accent/5">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="flex items-center">
                  <Sparkles className="mr-2 h-5 w-5 text-accent" />
                  {summaries.aggregate_summary.aggregate_headline || 'Research Summary'}
                </CardTitle>
                <CardDescription>
                  Synthesized from {summaries.total} sources
                </CardDescription>
              </div>
              <div className="flex gap-2 items-center">
                 {!codeExamples && (
                    <>
                    <select 
                        value={selectedStack} 
                        onChange={e => setSelectedStack(e.target.value)}
                        className="h-9 rounded-lg border border-gray-700 bg-gray-900 px-3 text-sm text-text"
                    >
                        <option value="langchain">LangChain</option>
                        <option value="pytorch">PyTorch</option>
                        <option value="tensorflow">TensorFlow</option>
                        <option value="vanilla">Vanilla Python</option>
                    </select>
                    <Button 
                        onClick={generateCode} 
                        disabled={generatingCode}
                        size="sm"
                        variant="secondary"
                    >
                        {generatingCode ? <Loader2 className="h-4 w-4 animate-spin" /> : <Code2 className="h-4 w-4 mr-2" />}
                        Code
                    </Button>
                    </>
                 )}
                 <Button 
                    onClick={generatePost}
                    disabled={generatingPost}
                    size="sm"
                    variant="outline"
                 >
                     {generatingPost ? <Loader2 className="h-4 w-4 animate-spin" /> : <Share2 className="h-4 w-4 mr-2" />}
                     Create Post
                 </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-text whitespace-pre-wrap">{summaries.aggregate_summary.synthesis}</p>
          </CardContent>
        </Card>
      )}
      
      {/* Post Draft Section */}
      {postDraft && (
          <Card className="border-blue-500/30 bg-blue-500/5">
              <CardHeader>
                  <CardTitle className="flex items-center"><Share2 className="mr-2 h-5 w-5" /> Social Media Draft</CardTitle>
                  <CardDescription>Review and publish your content</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                  <div className="space-y-2">
                      <Label>Platform</Label>
                      <div className="flex gap-4">
                        <label className="flex items-center cursor-pointer">
                            <input type="radio" name="platform" value="linkedin" checked={platform==='linkedin'} onChange={() => setPlatform('linkedin')} className="mr-2" />
                            LinkedIn
                        </label>
                        <label className="flex items-center cursor-pointer">
                            <input type="radio" name="platform" value="twitter" checked={platform==='twitter'} onChange={() => setPlatform('twitter')} className="mr-2" />
                            Twitter
                        </label>
                      </div>
                  </div>
                  
                  <div className="space-y-2">
                      <Label>Post Content</Label>
                      <Textarea 
                        rows={8} 
                        value={typeof postDraft.post_text === 'string' ? postDraft.post_text : postDraft.post_text.join('\n\n')} 
                        onChange={e => setPostDraft({...postDraft, post_text: e.target.value})}
                        className="font-mono text-sm"
                      />
                  </div>

                  {postDraft.image_prompt && (
                      <div className="p-3 bg-gray-900 rounded text-xs text-dim border border-gray-800">
                          <span className="font-bold text-purple-400">Image Prompt:</span> {postDraft.image_prompt}
                      </div>
                  )}
                  
                  <div className="flex justify-end gap-2">
                      <Button variant="ghost" onClick={() => setPostDraft(null)}>Discard</Button>
                      <Button onClick={publishPost} disabled={publishing}>
                          {publishing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Send className="h-4 w-4 mr-2" />}
                          Publish to Webhook
                      </Button>
                  </div>
              </CardContent>
          </Card>
      )}

      {/* Code Examples Section */}
      {codeExamples && codeExamples.code_examples && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-text flex items-center">
              <Code2 className="mr-2 h-5 w-5" />
              Generated Code Examples
            </h2>
            <span className="text-sm text-dim">{codeExamples.total} example(s) • {codeExamples.stack}</span>
          </div>
          
          {codeExamples.code_examples.map((example: any, idx: number) => {
            const code = example.code;
            if (!code) return null;
            return (
              <Card key={idx} className="border-green-800/50">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>{code.title}</span>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => copyCode(code.code, idx)}
                    >
                      {copiedCode === idx ? (
                        <>
                          <Check className="h-4 w-4 mr-2" />
                          Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="h-4 w-4 mr-2" />
                          Copy Code
                        </>
                      )}
                    </Button>
                  </CardTitle>
                  <CardDescription>{code.description}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {code.dependencies && code.dependencies.length > 0 && (
                    <div>
                      <p className="text-sm font-semibold mb-2">Dependencies:</p>
                      <div className="flex flex-wrap gap-2">
                        {code.dependencies.map((dep: string, i: number) => (
                          <span key={i} className="px-2 py-1 rounded bg-gray-900 border border-gray-800 text-xs font-mono text-dim">
                            {dep}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <div>
                    <p className="text-sm font-semibold mb-2">Code:</p>
                    <pre className="p-4 rounded-lg bg-gray-950 border border-gray-800 text-xs text-green-400 overflow-x-auto">
                      <code>{code.code}</code>
                    </pre>
                  </div>
                  
                  {code.explanation && (
                    <div>
                      <p className="text-sm font-semibold mb-2">Explanation:</p>
                      <p className="text-sm text-dim">{code.explanation}</p>
                    </div>
                  )}
                  
                  {code.usage_instructions && (
                    <div>
                      <p className="text-sm font-semibold mb-2">How to Use:</p>
                      <p className="text-sm text-dim">{code.usage_instructions}</p>
                    </div>
                  )}
                  
                  {code.test_code && (
                    <div>
                      <p className="text-sm font-semibold mb-2">Test Code:</p>
                      <pre className="p-4 rounded-lg bg-gray-950 border border-gray-800 text-xs text-blue-400 overflow-x-auto">
                        <code>{code.test_code}</code>
                      </pre>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <div className="space-y-4">
        {results.map((result, idx) => {
          const summary = summaries?.summaries?.[idx]?.summary;
          
          return (
            <Card key={idx}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        result.source === 'arxiv' 
                          ? 'bg-blue-900/30 text-blue-400' 
                          : 'bg-green-900/30 text-green-400'
                      }`}>
                        {result.source}
                      </span>
                      {result.date && (
                        <span className="flex items-center text-xs text-dim">
                          <Calendar className="h-3 w-3 mr-1" />
                          {new Date(result.date).toLocaleDateString()}
                        </span>
                      )}
                      {summary && (
                        <span className="flex items-center text-xs text-accent">
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                          Summarized
                        </span>
                      )}
                    </div>
                    <CardTitle className="text-lg">
                      <a 
                        href={result.link} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="hover:text-accent flex items-center gap-2"
                      >
                        {result.title}
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    </CardTitle>
                    {result.authors && result.authors.length > 0 && (
                      <div className="flex items-center text-sm text-dim mt-2">
                        <User className="h-3 w-3 mr-1" />
                        {result.authors.slice(0, 3).join(', ')}
                        {result.authors.length > 3 && ` +${result.authors.length - 3} more`}
                      </div>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {summary ? (
                  <div className="space-y-3">
                    <div className="p-3 rounded-lg bg-accent/10 border border-accent/30">
                      <p className="font-semibold text-accent text-sm mb-1">TL;DR</p>
                      <p className="text-text">{summary.tldr}</p>
                    </div>
                    {summary.key_points && summary.key_points.length > 0 && (
                      <div>
                        <p className="font-semibold text-sm mb-2">Key Points:</p>
                        <ul className="list-disc list-inside space-y-1 text-sm text-dim">
                          {summary.key_points.map((point: string, i: number) => (
                            <li key={i}>{point}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-dim text-sm">{result.excerpt}</p>
                )}
                {result.categories && result.categories.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-3">
                    {result.categories.slice(0, 5).map((cat, i) => (
                      <span key={i} className="px-2 py-1 rounded bg-gray-800 text-xs text-dim">
                        {cat}
                      </span>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {results.length === 0 && !loading && (
        <Card>
          <CardContent className="py-12 text-center">
            <Search className="h-12 w-12 mx-auto text-dim mb-4" />
            <p className="text-dim">Enter a research topic to discover papers and articles</p>
          </CardContent>
        </Card>
      )}
      </>
      )}
    </div>
  )
}
