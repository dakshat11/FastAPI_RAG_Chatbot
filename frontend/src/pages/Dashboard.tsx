import React from 'react';
import { ArrowRight, FileText, CheckCircle, MessageSquare } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Dashboard = () => {
  const navigate = useNavigate();

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Welcome to Career AI</h1>
        <p className="page-desc">Your intelligent ATS assistant and career coach.</p>
      </div>

      <div className="grid-2" style={{ marginTop: '3rem' }}>
        <div className="glass-panel" style={{ cursor: 'pointer' }} onClick={() => navigate('/analyze')}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <div style={{ background: 'rgba(99, 102, 241, 0.2)', padding:'12px', borderRadius: '12px' }}>
              <FileText color="var(--primary)" size={32} />
            </div>
            <ArrowRight color="var(--text-muted)" />
          </div>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Resume Analyzer</h2>
          <p style={{ color: 'var(--text-muted)' }}>Upload your resume and get instant ATS feedback, scoring, and formatting tips.</p>
        </div>

        <div className="glass-panel" style={{ cursor: 'pointer' }} onClick={() => navigate('/match')}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <div style={{ background: 'rgba(34, 197, 94, 0.2)', padding:'12px', borderRadius: '12px' }}>
              <CheckCircle color="var(--success)" size={32} />
            </div>
            <ArrowRight color="var(--text-muted)" />
          </div>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>JD Matcher</h2>
          <p style={{ color: 'var(--text-muted)' }}>Paste a job description to instantly see how well your resume matches the requirements.</p>
        </div>

        <div className="glass-panel" style={{ cursor: 'pointer', gridColumn: '1 / -1' }} onClick={() => navigate('/coach')}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <div style={{ background: 'rgba(236, 72, 153, 0.2)', padding:'12px', borderRadius: '12px' }}>
              <MessageSquare color="var(--accent)" size={32} />
            </div>
            <ArrowRight color="var(--text-muted)" />
          </div>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>AI Career Coach</h2>
          <p style={{ color: 'var(--text-muted)' }}>Chat with an AI that knows your resume context to prepare for interviews and answer tricky career questions.</p>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
