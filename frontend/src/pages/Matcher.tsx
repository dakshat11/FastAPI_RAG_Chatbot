import React, { useState, useEffect } from 'react';
import { Target, Loader2, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';
import axios from 'axios';

const Matcher = () => {
    const [jd, setJd] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [threadId, setThreadId] = useState<string | null>(null);

    useEffect(() => {
        const id = localStorage.getItem('career_thread_id');
        setThreadId(id);
    }, []);

    const handleMatch = async () => {
        if (!threadId) {
            alert("Please upload a resume in the Analyzer tab first.");
            return;
        }
        if (!jd.trim()) return;

        setLoading(true);
        try {
            const response = await axios.post(`http://localhost:8000/api/v1/resume/match`, {
                thread_id: threadId,
                job_description: jd
            });
            setResult(response.data);
        } catch (error) {
            console.error(error);
            alert("Error matching JD. Make sure backend is running and resume is uploaded.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="animate-fade-in">
            <div className="page-header">
                <h1 className="page-title">Job Description Matcher</h1>
                <p className="page-desc">See how well your resume fits a specific job posting.</p>
            </div>

            {!threadId && (
                <div className="glass-panel" style={{ display: 'flex', alignItems: 'center', gap: '1rem', color: 'var(--warning)', marginBottom: '2rem' }}>
                    <AlertTriangle />
                    <span>You haven't uploaded a resume yet. Go to the <strong>Resume Analyzer</strong> first to upload your profile.</span>
                </div>
            )}

            <div className="grid-2">
                <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                        <Target color="var(--primary)" /> 
                        <h3>Target Job Description</h3>
                    </div>
                    <textarea 
                        className="input-glass"
                        style={{ flex: 1, minHeight: '300px', resize: 'vertical' }}
                        placeholder="Paste the full job description text here..."
                        value={jd}
                        onChange={e => setJd(e.target.value)}
                    ></textarea>
                    <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'flex-end' }}>
                        <button className="btn-primary" disabled={!jd || !threadId || loading} onClick={handleMatch}>
                            {loading ? <Loader2 className="animate-spin" /> : "Calculate Match Score"}
                        </button>
                    </div>
                </div>

                <div className="glass-panel">
                    {!result ? (
                        <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                            {loading ? <Loader2 className="animate-spin" size={32} /> : "Results will appear here"}
                        </div>
                    ) : (
                        <div className="animate-fade-in">
                            <h3 style={{ textAlign: 'center', marginBottom: '1rem', color: 'var(--text-muted)' }}>Fit Score</h3>
                            <div className="score-circle" style={{ borderColor: result.match_score > 70 ? 'var(--success)' : result.match_score > 40 ? 'var(--warning)' : 'var(--danger)' }}>
                                {result.match_score}%
                            </div>
                            
                            <p className="prose" style={{ marginTop: '1.5rem', textAlign: 'center', fontStyle: 'italic' }}>
                                "{result.profile_fit}"
                            </p>

                            <div style={{ marginTop: '2rem' }}>
                                <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: 'var(--success)' }}>
                                    <CheckCircle2 size={18} /> Matching Skills
                                </h4>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1.5rem' }}>
                                    {result.matching_skills.map((s: string, i: number) => <span key={i} className="badge" style={{ borderColor: 'var(--success)' }}>{s}</span>)}
                                </div>

                                <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', color: 'var(--danger)' }}>
                                    <XCircle size={18} /> Missing Skills
                                </h4>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1.5rem' }}>
                                    {result.missing_skills.map((s: string, i: number) => <span key={i} className="badge" style={{ borderColor: 'var(--danger)' }}>{s}</span>)}
                                </div>

                                <h4>Recommendations</h4>
                                <ul className="prose" style={{ marginTop: '0.5rem' }}>
                                    {result.recommendations.map((r: string, i: number) => <li key={i}>{r}</li>)}
                                </ul>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

export default Matcher;
