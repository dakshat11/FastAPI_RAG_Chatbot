import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { LayoutDashboard, FileText, CheckCircle, MessageSquare } from 'lucide-react';
import React from 'react';

// Placeholders for Pages
import Dashboard from './pages/Dashboard';
import Analyzer from './pages/Analyzer';
import Matcher from './pages/Matcher';
import ChatAgent from './pages/ChatAgent';

const Sidebar = () => {
  return (
    <div className="sidebar">
      <div className="sidebar-brand">
        <div style={{ padding: '4px', background: 'white', borderRadius: '8px', display:'flex' }}>
          <LayoutDashboard color="var(--primary)" size={24} />
        </div>
        Career AI
      </div>
      <nav style={{ marginTop: '2rem' }}>
        <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} end>
          <LayoutDashboard size={20} /> Dashboard
        </NavLink>
        <NavLink to="/analyze" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <FileText size={20} /> Resume Analyzer
        </NavLink>
        <NavLink to="/match" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <CheckCircle size={20} /> JD Matcher
        </NavLink>
        <NavLink to="/coach" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <MessageSquare size={20} /> AI Career Coach
        </NavLink>
      </nav>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <div className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/analyze" element={<Analyzer />} />
            <Route path="/match" element={<Matcher />} />
            <Route path="/coach" element={<ChatAgent />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
