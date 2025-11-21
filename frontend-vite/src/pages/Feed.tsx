import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge'; // Assume we have a badge component, or style it
import { ExternalLink, Rss, Globe, BookOpen, RefreshCw, Loader2 } from 'lucide-react';
import { useAuth } from '../lib/authStore';

function BadgeComponent({ children, className }: { children: React.ReactNode, className?: string }) {
    return <span className={`px-2 py-1 rounded-full text-xs font-semibold ${className}`}>{children}</span>;
}

interface FeedItem {
    title: string;
    link: string;
    excerpt: string;
    source: string;
    date: string;
    feed_title?: string;
    query?: string;
    research_id: string;
}

export default function Feed() {
    const [items, setItems] = useState<FeedItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const token = useAuth(s => s.token);

    const fetchFeed = async (isRefresh = false) => {
        if (isRefresh) setRefreshing(true);
        else setLoading(true);
        try {
            const res = await fetch('/api/research/feed?limit=50', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
            });
            if (res.ok) {
                const data = await res.json();
                setItems(data);
            }
        } catch (error) {
            console.error("Failed to fetch feed", error);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        fetchFeed();
    }, []);

    const getSourceIcon = (source: string) => {
        if (source === 'rss') return <Rss className="h-4 w-4" />;
        if (source === 'arxiv') return <BookOpen className="h-4 w-4" />;
        return <Globe className="h-4 w-4" />;
    };

    const getSourceColor = (source: string) => {
        if (source === 'rss') return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
        if (source === 'arxiv') return 'bg-red-500/10 text-red-500 border-red-500/20';
        return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
    };

    const formatDate = (dateStr: string) => {
        if (!dateStr) return '';
        return new Date(dateStr).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    };

    return (
        <div className="container mx-auto p-6 max-w-5xl space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold">AI Knowledge Feed</h1>
                    <p className="text-muted-foreground">Latest research, news, and updates</p>
                </div>
                <Button variant="outline" onClick={() => fetchFeed(true)} disabled={refreshing}>
                    {refreshing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />}
                    Refresh
                </Button>
            </div>

            {loading && (
                <div className="flex justify-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {items.map((item, idx) => (
                    <Card key={idx} className="flex flex-col hover:shadow-lg transition-shadow duration-200 border-border/50 bg-card/50">
                        <CardHeader className="pb-3">
                            <div className="flex justify-between items-start gap-2">
                                <BadgeComponent className={`${getSourceColor(item.source)} flex items-center gap-1`}>
                                    {getSourceIcon(item.source)}
                                    {item.source.toUpperCase()}
                                </BadgeComponent>
                                <span className="text-xs text-muted-foreground whitespace-nowrap">{formatDate(item.date)}</span>
                            </div>
                            <a href={item.link} target="_blank" rel="noopener noreferrer" className="hover:underline decoration-primary underline-offset-4">
                                <CardTitle className="text-lg leading-tight mt-2 line-clamp-2" title={item.title}>
                                    {item.title}
                                </CardTitle>
                            </a>
                            {item.feed_title && (
                                <p className="text-xs text-dim mt-1 font-medium">{item.feed_title}</p>
                            )}
                        </CardHeader>
                        <CardContent className="flex-grow flex flex-col">
                            <p className="text-sm text-muted-foreground line-clamp-4 mb-4 flex-grow">
                                {item.excerpt}
                            </p>
                            <div className="mt-auto pt-4 border-t border-border/50 flex justify-between items-center">
                                <span className="text-xs text-dim truncate max-w-[150px]" title={`Query: ${item.query}`}>
                                    Q: {item.query}
                                </span>
                                <a 
                                    href={item.link} 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    className="text-primary hover:text-primary/80 text-sm flex items-center gap-1 font-medium"
                                >
                                    Read <ExternalLink className="h-3 w-3" />
                                </a>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>
            
            {!loading && items.length === 0 && (
                <div className="text-center py-12 text-muted-foreground">
                    <p>No items found. Try running a research query or waiting for the scheduler.</p>
                </div>
            )}
        </div>
    );
}
