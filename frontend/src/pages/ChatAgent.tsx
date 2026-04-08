import React, { useState, useEffect, useRef } from 'react';
import { Send, Loader2, Bot, User } from 'lucide-react';
import axios from 'axios';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

const ChatAgent = () => {
    const [messages, setMessages] = useState<Message[]>([
        { role: 'assistant', content: "Hi! I'm your Career Coach AI. Ask me for interview preparation tips or questions about your resume!" }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [threadId, setThreadId] = useState<string>('default-career-coach');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const id = localStorage.getItem('career_thread_id');
        if (id) {
            setThreadId(id);
        }
    }, []);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim()) return;
        const userMessage = input.trim();
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        
        setLoading(true);
        try {
            const response = await axios.post('http://localhost:8000/api/v1/chat', {
                thread_id: threadId,
                message: userMessage
            });
            setMessages(prev => [...prev, { role: 'assistant', content: response.data.reply }]);
        } catch (error) {
            console.error(error);
            setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I'm having trouble connecting to the server." }]);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="animate-fade-in" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <div className="page-header">
                <h1 className="page-title">Career Coach AI</h1>
                <p className="page-desc">Chat with an agent that knows your resume inside out.</p>
            </div>

            <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                <div style={{ flex: 1, overflowY: 'auto', paddingRight: '1rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    {messages.map((m, idx) => (
                        <div key={idx} style={{ display: 'flex', gap: '1rem', flexDirection: m.role === 'user' ? 'row-reverse' : 'row' }}>
                            <div style={{ 
                                width: '40px', height: '40px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                                background: m.role === 'user' ? 'var(--primary)' : 'rgba(236, 72, 153, 0.2)'
                            }}>
                                {m.role === 'user' ? <User size={20} /> : <Bot size={20} color="var(--accent)" />}
                            </div>
                            <div style={{ 
                                maxWidth: '70%', padding: '1rem 1.5rem', borderRadius: '16px',
                                background: m.role === 'user' ? 'rgba(99, 102, 241, 0.1)' : 'rgba(255, 255, 255, 0.05)',
                                border: '1px solid rgba(255,255,255,0.1)'
                            }}>
                                <div className="prose" style={{ whiteSpace: 'pre-wrap' }}>
                                    {m.content}
                                </div>
                            </div>
                        </div>
                    ))}
                    {loading && (
                        <div style={{ display: 'flex', gap: '1rem' }}>
                             <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'rgba(236, 72, 153, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <Bot size={20} color="var(--accent)" />
                            </div>
                            <div style={{ padding: '1rem 1.5rem', borderRadius: '16px', background: 'rgba(255, 255, 255, 0.05)' }}>
                                <Loader2 className="animate-spin" size={20} />
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem' }}>
                    <input 
                        className="input-glass" 
                        placeholder="Type your message..." 
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleSend()}
                    />
                    <button className="btn-primary" style={{ padding: '0 2rem' }} onClick={handleSend} disabled={loading || !input.trim()}>
                        <Send size={20} />
                    </button>
                </div>
            </div>
        </div>
    )
}

export default ChatAgent;
