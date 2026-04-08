import React, { useState } from 'react';
import { UploadCloud, Loader2, Award, Zap } from 'lucide-react';
import axios from 'axios';

const Analyzer = () => {
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [threadId, setThreadId] = useState<string>('');

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            setFile(e.dataTransfer.files[0]);
        }
    }

    const handleUpload = async () => {
        if (!file) return;
        setLoading(true);
        try {
            const tempThreadId = Math.random().toString(36).substring(7);
            
            // Upload to rag endpoint
            const formData = new FormData();
            formData.append('file', file);
            await axios.post(`http://localhost:8000/api/v1/pdf/upload?thread_id=${tempThreadId}`, formData);

            setThreadId(tempThreadId);

            // Analyze
            const response = await axios.post(`http://localhost:8000/api/v1/resume/analyze?thread_id=${tempThreadId}`);
            setResult(response.data);
            
            // store threadId in localStorage for Matcher or Chat to pick up
            localStorage.setItem('career_thread_id', tempThreadId);
        } catch (error) {
            console.error(error);
            alert("Error analyzing resume. Make sure backend is running.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="animate-fade-in">
            <div className="page-header">
                <h1 className="page-title">Resume Analyzer</h1>
                <p className="page-desc">Check your ATS score and get actionable feedback.</p>
            </div>

            {!result && (
                <div 
                    className="dropzone" 
                    onDragOver={(e) => e.preventDefault()} 
                    onDrop={handleDrop}
                    onClick={() => document.getElementById('fileUpload')?.click()}
                >
                    <input 
                        type="file" 
                        id="fileUpload" 
                        accept=".pdf" 
                        hidden 
                        onChange={(e) => e.target.files && setFile(e.target.files[0])} 
                    />
                    <UploadCloud size={48} color="var(--primary)" style={{ margin: '0 auto 1rem' }} />
                    <h3 style={{ marginBottom: '0.5rem' }}>{file ? file.name : "Drag and drop your PDF resume here"}</h3>
                    <p style={{ color: 'var(--text-muted)' }}>or click to browse from your computer</p>

                    {file && (
                        <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'center' }}>
                            <button className="btn-primary" onClick={(e) => { e.stopPropagation(); handleUpload()}} disabled={loading}>
                                {loading ? <Loader2 className="animate-spin" /> : "Analyze Resume"}
                            </button>
                        </div>
                    )}
                </div>
            )}

            {result && (
                <div className="animate-fade-in">
                    <div className="grid-2">
                        <div className="glass-panel" style={{ textAlign: 'center' }}>
                            <h3 style={{ marginBottom: '1.5rem', color: 'var(--text-muted)' }}>Overall ATS Score</h3>
                            <div className="score-circle">
                                {result.overall_score}%
                            </div>
                            <p style={{ marginTop: '1.5rem', fontWeight: 500 }}>
                                {result.overall_score > 80 ? "Excellent" : result.overall_score > 60 ? "Good" : "Needs Improvement"}
                            </p>
                        </div>
                        <div className="glass-panel">
                            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                                <Award color="var(--primary)" /> Profile Summary
                            </h3>
                            <p className="prose">{result.candidate_summary}</p>
                            <div style={{ marginTop: '1rem' }}>
                                <strong>Experience:</strong> {result.experience_years} years
                            </div>
                        </div>
                    </div>

                    <div className="glass-panel" style={{ marginTop: '1.5rem' }}>
                        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                            <Zap color="var(--warning)" /> Key Skills
                        </h3>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                            {result.key_skills.map((skill: string, i: number) => (
                                <span key={i} className="badge">{skill}</span>
                            ))}
                        </div>
                    </div>

                    <div className="grid-2" style={{ marginTop: '1.5rem' }}>
                        <div className="glass-panel">
                            <h3 style={{ marginBottom: '1rem', color: 'var(--success)' }}>Strengths</h3>
                            <ul className="prose">
                                {result.strengths.map((s: string, i: number) => <li key={i}>{s}</li>)}
                            </ul>
                        </div>
                        <div className="glass-panel">
                            <h3 style={{ marginBottom: '1rem', color: 'var(--danger)' }}>Areas for Improvement</h3>
                            <ul className="prose">
                                {result.areas_for_improvement.map((s: string, i: number) => <li key={i}>{s}</li>)}
                            </ul>
                        </div>
                    </div>
                    
                    <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'center' }}>
                        <button className="btn-secondary" onClick={() => {setResult(null); setFile(null)}}>
                            Upload Another Resume
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}

export default Analyzer;
