import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Search, Filter, Download, User, Mail, Phone, Briefcase, 
  Calendar, ArrowLeft, CheckCircle, AlertCircle, Clock, 
  FileText, Star, Award, ShieldAlert, Video, RefreshCw, BarChart2
} from 'lucide-react';

interface Candidate {
  interview_id: string;
  candidate_name: string;
  candidate_email: string;
  candidate_phone: string;
  job_title: string;
  status: string;
  created_at: string;
  evaluation: {
    overall_score: number;
    recommendation: string;
  } | null;
}

interface ResponseDetail {
  response_id: string;
  question_text: string;
  question_category: string;
  candidate_transcript: string;
  bot_transcript: string;
  technical_score: number | null;
  relevance_score: number | null;
  communication_score: number | null;
  confidence_score: number | null;
  created_at: string;
}

interface InterviewDetail {
  interview_id: string;
  status: string;
  created_at: string;
  completed_at: string | null;
  candidate: {
    name: string;
    email: string;
    phone: string;
  };
  job: {
    title: string;
    description: string;
  };
  evaluation: {
    id: string;
    technical_score: number;
    communication_score: number;
    behavioral_score: number;
    vision_score: number;
    overall_score: number;
    recommendation: string;
    summary: string;
    created_at: string;
  } | null;
  responses: ResponseDetail[];
  questions: Array<{
    question_text: string;
    category: string;
    sort_order: number;
  }>;
}

export default function RecruiterDashboard() {
  const navigate = useNavigate();
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Search & Filter State
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [recommendationFilter, setRecommendationFilter] = useState('all');

  // Detail View State
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<InterviewDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);

  // Fetch Candidates List
  const fetchCandidates = async (autoSelectFirst = false) => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch('http://localhost:8000/api/v1/recruiter/candidates');
      if (!response.ok) {
        throw new Error('Failed to load candidate directory');
      }
      const data = await response.json();
      setCandidates(data);

      if (autoSelectFirst && data.length > 0) {
        setSelectedId(data[0].interview_id);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCandidates(true);
  }, []);

  // Fetch Specific Interview Detail
  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }

    const fetchDetail = async () => {
      try {
        setDetailLoading(true);
        const response = await fetch(`http://localhost:8000/api/v1/recruiter/interviews/${selectedId}`);
        if (!response.ok) {
          throw new Error('Failed to load candidate details');
        }
        const data = await response.json();
        setDetail(data);
      } catch (err: any) {
        console.error(err);
      } finally {
        setDetailLoading(false);
      }
    };

    fetchDetail();
  }, [selectedId]);

  // Handle PDF Report Download
  const handleDownloadPDF = async (interviewId: string) => {
    try {
      setDownloading(true);
      const response = await fetch(`http://localhost:8000/api/v1/recruiter/interviews/${interviewId}/report`);
      if (!response.ok) {
        throw new Error('PDF report not ready or not found.');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Nova_Evaluation_Report_${interviewId.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(err.message || 'Error downloading PDF');
    } finally {
      setDownloading(false);
    }
  };

  // Filter Logic
  const filteredCandidates = candidates.filter(c => {
    const matchesSearch = 
      c.candidate_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.candidate_email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.job_title.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus = statusFilter === 'all' || c.status === statusFilter;
    
    const matchesRec = recommendationFilter === 'all' || 
      (c.evaluation && c.evaluation.recommendation.toLowerCase() === recommendationFilter.toLowerCase());

    return matchesSearch && matchesStatus && matchesRec;
  });

  const getStatusBadgeStyles = (status: string) => {
    switch (status) {
      case 'evaluated':
        return { bg: 'rgba(0, 230, 118, 0.15)', color: 'var(--success)', icon: CheckCircle };
      case 'completed':
        return { bg: 'rgba(109, 93, 252, 0.15)', color: 'var(--accent-hover)', icon: Award };
      case 'active':
        return { bg: 'rgba(255, 179, 0, 0.15)', color: '#ffb300', icon: RefreshCw };
      default:
        return { bg: 'rgba(255, 255, 255, 0.08)', color: 'var(--text-muted)', icon: Clock };
    }
  };

  const getRecBadgeStyles = (rec: string) => {
    switch (rec.toLowerCase()) {
      case 'strong hire':
        return { bg: 'rgba(0, 230, 118, 0.25)', color: '#00ff88', border: '1px solid rgba(0, 230, 118, 0.4)' };
      case 'hire':
        return { bg: 'rgba(0, 230, 118, 0.15)', color: 'var(--success)', border: '1px solid rgba(0, 230, 118, 0.2)' };
      case 'consider':
      case 'hold':
        return { bg: 'rgba(255, 179, 0, 0.15)', color: '#ffb300', border: '1px solid rgba(255, 179, 0, 0.3)' };
      case 'reject':
        return { bg: 'rgba(255, 77, 77, 0.15)', color: 'var(--danger)', border: '1px solid rgba(255, 77, 77, 0.3)' };
      default:
        return { bg: 'rgba(255, 255, 255, 0.08)', color: 'var(--text-muted)', border: '1px solid rgba(255, 255, 255, 0.1)' };
    }
  };

  const formatDate = (isoStr: string) => {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'var(--bg-dark)', color: 'var(--text-main)', fontFamily: 'Inter, sans-serif' }}>
      
      {/* Top Header */}
      <header style={{ 
        padding: '16px 32px', 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)', 
        background: 'rgba(10, 10, 18, 0.7)', 
        backdropFilter: 'blur(16px)',
        zIndex: 50
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button 
            onClick={() => navigate('/')} 
            className="glass-button" 
            style={{ padding: '8px 16px', background: 'rgba(255,255,255,0.05)', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            <ArrowLeft size={16} /> Portal Home
          </button>
          <div style={{ width: '1px', height: '24px', background: 'rgba(255,255,255,0.1)' }} />
          <h1 className="gradient-text" style={{ fontSize: '1.4rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BarChart2 size={24} color="var(--accent-primary)" /> Nova Recruiter Dashboard
          </h1>
        </div>

        <button 
          onClick={() => fetchCandidates()} 
          className="glass-button" 
          style={{ padding: '8px 16px', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px' }}
        >
          <RefreshCw size={16} /> Refresh Directory
        </button>
      </header>

      {/* Main Panel Content */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        
        {/* Left Side: Candidates list list */}
        <aside style={{ 
          width: '380px', 
          borderRight: '1px solid rgba(255, 255, 255, 0.08)', 
          background: 'rgba(15, 15, 25, 0.4)', 
          display: 'flex', 
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
          {/* Search and Filters */}
          <div style={{ padding: '20px', borderBottom: '1px solid rgba(255,255,255,0.08)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ position: 'relative' }}>
              <input 
                type="text" 
                placeholder="Search candidates, email, job..." 
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="glass-input" 
                style={{ paddingLeft: '38px', fontSize: '0.9rem' }}
              />
              <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>Status</label>
                <div style={{ position: 'relative' }}>
                  <select 
                    value={statusFilter} 
                    onChange={e => setStatusFilter(e.target.value)}
                    style={{
                      background: 'rgba(0,0,0,0.3)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '6px',
                      color: 'var(--text-main)',
                      padding: '8px 24px 8px 8px',
                      fontSize: '0.8rem',
                      width: '100%',
                      appearance: 'none',
                      cursor: 'pointer'
                    }}
                  >
                    <option value="all">All Statuses</option>
                    <option value="scheduled">Scheduled</option>
                    <option value="active">Active</option>
                    <option value="completed">Completed</option>
                    <option value="evaluated">Evaluated</option>
                  </select>
                  <Filter size={12} style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} />
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>Decision</label>
                <div style={{ position: 'relative' }}>
                  <select 
                    value={recommendationFilter} 
                    onChange={e => setRecommendationFilter(e.target.value)}
                    style={{
                      background: 'rgba(0,0,0,0.3)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '6px',
                      color: 'var(--text-main)',
                      padding: '8px 24px 8px 8px',
                      fontSize: '0.8rem',
                      width: '100%',
                      appearance: 'none',
                      cursor: 'pointer'
                    }}
                  >
                    <option value="all">All Recs</option>
                    <option value="strong hire">Strong Hire</option>
                    <option value="hire">Hire</option>
                    <option value="consider">Consider/Hold</option>
                    <option value="reject">Reject</option>
                  </select>
                  <Filter size={12} style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} />
                </div>
              </div>
            </div>
          </div>

          {/* Candidates Directory */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
            {loading ? (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px 0' }}>
                <RefreshCw className="orb-active" style={{ animation: 'spin 1.5s linear infinite', marginBottom: '12px' }} />
                <p>Loading candidate list...</p>
              </div>
            ) : error ? (
              <div style={{ color: 'var(--danger)', padding: '20px', textAlign: 'center', fontSize: '0.9rem' }}>
                {error}
              </div>
            ) : filteredCandidates.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px 0', fontSize: '0.9rem' }}>
                No candidates found.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {filteredCandidates.map(c => {
                  const isSelected = selectedId === c.interview_id;
                  const statusInfo = getStatusBadgeStyles(c.status);
                  const StatusIcon = statusInfo.icon;
                  
                  return (
                    <div 
                      key={c.interview_id}
                      onClick={() => setSelectedId(c.interview_id)}
                      className="glass-panel"
                      style={{
                        padding: '16px',
                        cursor: 'pointer',
                        transition: 'all 0.25s ease',
                        border: isSelected ? '1px solid var(--accent-primary)' : '1px solid rgba(255,255,255,0.06)',
                        background: isSelected ? 'rgba(109, 93, 252, 0.08)' : 'var(--bg-card)',
                        boxShadow: isSelected ? '0 4px 15px rgba(109, 93, 252, 0.15)' : 'none'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                        <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#fff' }}>{c.candidate_name}</h3>
                        {c.evaluation && (
                          <div style={{ 
                            background: 'rgba(109, 93, 252, 0.15)', 
                            color: 'var(--accent-hover)', 
                            padding: '2px 8px', 
                            borderRadius: '12px', 
                            fontSize: '0.75rem', 
                            fontWeight: 'bold',
                            border: '1px solid rgba(109, 93, 252, 0.2)'
                          }}>
                            {c.evaluation.overall_score.toFixed(1)} / 10
                          </div>
                        )}
                      </div>

                      <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '12px' }}>
                        <Briefcase size={12} /> {c.job_title}
                      </p>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ 
                          display: 'inline-flex', 
                          alignItems: 'center', 
                          gap: '4px', 
                          padding: '4px 8px', 
                          borderRadius: '4px', 
                          fontSize: '0.7rem', 
                          fontWeight: 600,
                          background: statusInfo.bg,
                          color: statusInfo.color
                        }}>
                          <StatusIcon size={10} />
                          {c.status}
                        </span>

                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                          {formatDate(c.created_at)}
                        </span>
                      </div>

                      {c.evaluation && (
                        <div style={{ 
                          marginTop: '10px', 
                          paddingTop: '8px', 
                          borderTop: '1px solid rgba(255,255,255,0.05)',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center'
                        }}>
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Decision:</span>
                          <span style={{
                            padding: '2px 8px',
                            borderRadius: '10px',
                            fontSize: '0.7rem',
                            fontWeight: 'bold',
                            ...getRecBadgeStyles(c.evaluation.recommendation)
                          }}>
                            {c.evaluation.recommendation}
                          </span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </aside>

        {/* Right Side: Detailed report & Playback */}
        <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflowY: 'auto', background: 'rgba(5, 5, 8, 0.3)' }}>
          {selectedId ? (
            detailLoading ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1 }}>
                <RefreshCw className="orb-active" style={{ animation: 'spin 1.5s linear infinite', width: '32px', height: '32px', color: 'var(--accent-primary)', marginBottom: '16px' }} />
                <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>Compiling interview metrics and transcripts...</p>
              </div>
            ) : detail ? (
              <div style={{ padding: '32px', display: 'flex', flexDirection: 'column', gap: '32px' }}>
                
                {/* Section 1: Candidate Overview banner */}
                <section className="glass-panel" style={{ padding: '24px 32px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '8px' }}>
                      <h2 style={{ fontSize: '1.6rem', fontWeight: 700 }}>{detail.candidate.name}</h2>
                      <span style={{ 
                        padding: '4px 12px', 
                        borderRadius: '4px', 
                        fontSize: '0.8rem', 
                        fontWeight: 600,
                        background: getStatusBadgeStyles(detail.status).bg,
                        color: getStatusBadgeStyles(detail.status).color
                      }}>
                        {detail.status}
                      </span>
                    </div>

                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Mail size={14} /> {detail.candidate.email}</span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Phone size={14} /> {detail.candidate.phone}</span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Briefcase size={14} /> {detail.job.title}</span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Calendar size={14} /> {formatDate(detail.created_at)}</span>
                    </div>
                  </div>

                  {/* Actions (PDF Download, etc.) */}
                  {detail.evaluation && (
                    <button 
                      onClick={() => handleDownloadPDF(detail.interview_id)} 
                      disabled={downloading}
                      className="glass-button" 
                      style={{ background: 'var(--accent-primary)', color: '#fff', fontSize: '0.9rem', minWidth: '160px' }}
                    >
                      {downloading ? (
                        <RefreshCw style={{ animation: 'spin 1s linear infinite' }} size={16} />
                      ) : (
                        <Download size={16} />
                      )}
                      Download Report PDF
                    </button>
                  )}
                </section>

                {/* Section 2: AI Evaluation Results */}
                {detail.evaluation ? (
                  <section style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.8fr', gap: '30px' }}>
                    
                    {/* Scores Breakdowns */}
                    <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
                      <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-muted)', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '12px' }}>
                        Performance Breakdown
                      </h3>

                      {/* Overall Large Score Card */}
                      <div style={{ 
                        textAlign: 'center', 
                        padding: '20px', 
                        background: 'rgba(255,255,255,0.02)', 
                        border: '1px solid rgba(255,255,255,0.05)', 
                        borderRadius: '12px' 
                      }}>
                        <div style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--accent-hover)', lineHeight: 1 }}>
                          {detail.evaluation.overall_score.toFixed(1)}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', tracking: '1px', marginTop: '4px' }}>
                          Overall Grade
                        </div>
                        <div style={{ 
                          display: 'inline-block',
                          marginTop: '12px',
                          padding: '4px 16px',
                          borderRadius: '16px',
                          fontSize: '0.85rem',
                          fontWeight: 'bold',
                          ...getRecBadgeStyles(detail.evaluation.recommendation)
                        }}>
                          {detail.evaluation.recommendation}
                        </div>
                      </div>

                      {/* Category Sliders */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                        {[
                          { name: 'Technical Depth', score: detail.evaluation.technical_score, icon: Code2Icon },
                          { name: 'Communication Style', score: detail.evaluation.communication_score, icon: MessageCircleIcon },
                          { name: 'Behavioral Traits', score: detail.evaluation.behavioral_score, icon: UserCheckIcon },
                          { name: 'Visual Presence (Vision)', score: detail.evaluation.vision_score, icon: Video }
                        ].map((cat, idx) => (
                          <div key={idx}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '0.85rem' }}>
                              <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)' }}>
                                <cat.icon size={13} /> {cat.name}
                              </span>
                              <span style={{ fontWeight: 600, color: '#fff' }}>{cat.score.toFixed(1)} / 10</span>
                            </div>
                            <div style={{ height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                              <div style={{ 
                                width: `${cat.score * 10}%`, 
                                height: '100%', 
                                background: 'linear-gradient(90deg, var(--accent-primary), var(--accent-hover))' 
                              }} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* AI Executive Summary */}
                    <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column' }}>
                      <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-muted)', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '12px', marginBottom: '16px' }}>
                        Recruiter Executive Summary
                      </h3>
                      <div style={{ 
                        flex: 1, 
                        fontSize: '0.95rem', 
                        lineHeight: 1.6, 
                        color: 'var(--text-main)', 
                        whiteSpace: 'pre-line',
                        overflowY: 'auto',
                        paddingRight: '8px'
                      }}>
                        {detail.evaluation.summary}
                      </div>
                    </div>
                  </section>
                ) : (
                  <section className="glass-panel" style={{ padding: '30px', textAlign: 'center', background: 'rgba(255,179,0,0.03)', border: '1px solid rgba(255,179,0,0.1)' }}>
                    <AlertCircle size={28} style={{ color: '#ffb300', marginBottom: '10px' }} />
                    <h3 style={{ color: '#fff', fontSize: '1.1rem', fontWeight: 600 }}>Evaluation Pending</h3>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '6px', maxWidth: '500px', margin: '6px auto 0 auto' }}>
                      The candidate has not finished their interview session yet, or the automated evaluation engine is currently running.
                    </p>
                  </section>
                )}

                {/* Section 3: Conversation Transcript & Response Playback */}
                <section className="glass-panel" style={{ padding: '24px' }}>
                  <h3 style={{ 
                    fontSize: '1.1rem', 
                    fontWeight: 600, 
                    color: 'var(--text-muted)', 
                    borderBottom: '1px solid rgba(255,255,255,0.06)', 
                    paddingBottom: '12px',
                    marginBottom: '20px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <Video size={18} /> Interview Playback & Response Log
                  </h3>

                  {detail.responses.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                      No responses recorded yet. Once the interview begins, the bot and candidate exchanges will be stored.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                      {detail.responses.map((resp, index) => (
                        <div 
                          key={resp.response_id}
                          style={{
                            background: 'rgba(255,255,255,0.02)',
                            border: '1px solid rgba(255,255,255,0.05)',
                            borderRadius: '12px',
                            padding: '20px',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '12px'
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ 
                              background: 'rgba(109, 93, 252, 0.15)', 
                              color: 'var(--accent-hover)', 
                              padding: '3px 8px', 
                              borderRadius: '4px', 
                              fontSize: '0.75rem', 
                              fontWeight: 600 
                            }}>
                              Q{index + 1}: {resp.question_category}
                            </span>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                              {formatDate(resp.created_at)}
                            </span>
                          </div>

                          {/* Bot Question */}
                          <div style={{ display: 'flex', gap: '10px', background: 'rgba(109, 93, 252, 0.04)', padding: '12px', borderRadius: '8px', borderLeft: '3px solid var(--accent-primary)' }}>
                            <div style={{ width: '20px', height: '20px', borderRadius: '50%', background: 'var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', fontWeight: 'bold', color: 'white' }}>N</div>
                            <div style={{ flex: 1, fontSize: '0.9rem' }}>
                              <strong>Nova: </strong>
                              <span style={{ color: 'var(--text-main)' }}>{resp.bot_transcript || resp.question_text}</span>
                            </div>
                          </div>

                          {/* Candidate Answer */}
                          <div style={{ display: 'flex', gap: '10px', background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px', borderLeft: '3px solid rgba(255,255,255,0.15)' }}>
                            <div style={{ width: '20px', height: '20px', borderRadius: '50%', background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', fontWeight: 'bold', color: 'var(--text-muted)' }}>C</div>
                            <div style={{ flex: 1, fontSize: '0.9rem' }}>
                              <strong>Candidate: </strong>
                              <span style={{ color: 'var(--text-main)', fontStyle: resp.candidate_transcript ? 'normal' : 'italic' }}>
                                {resp.candidate_transcript || '[No spoken response captured]'}
                              </span>
                            </div>
                          </div>

                          {/* Question Scoring breakdown */}
                          {resp.technical_score !== null && (
                            <div style={{ 
                              display: 'flex', 
                              flexWrap: 'wrap', 
                              gap: '10px', 
                              marginTop: '8px', 
                              paddingTop: '8px', 
                              borderTop: '1px solid rgba(255,255,255,0.03)' 
                            }}>
                              {[
                                { name: 'Technical Depth', val: resp.technical_score },
                                { name: 'Relevance', val: resp.relevance_score },
                                { name: 'Communication', val: resp.communication_score },
                                { name: 'Confidence', val: resp.confidence_score }
                              ].map((pill, pIdx) => (
                                <div 
                                  key={pIdx}
                                  style={{
                                    fontSize: '0.75rem',
                                    color: 'var(--text-muted)',
                                    background: 'rgba(255,255,255,0.02)',
                                    border: '1px solid rgba(255,255,255,0.05)',
                                    padding: '4px 10px',
                                    borderRadius: '16px',
                                    display: 'flex',
                                    gap: '6px'
                                  }}
                                >
                                  <span>{pill.name}:</span>
                                  <strong style={{ color: '#fff' }}>{pill.val !== null ? pill.val.toFixed(1) : 'N/A'}</strong>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </section>
              </div>
            ) : (
              <div style={{ display: 'flex', flex: 1, alignItems: 'center', justifyContent: 'center' }}>
                <p style={{ color: 'var(--text-muted)' }}>Could not load selected interview details.</p>
              </div>
            )
          ) : (
            <div style={{ display: 'flex', flex: 1, flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px' }}>
              <div style={{ opacity: 0.2, marginBottom: '20px' }}>
                <User size={80} />
              </div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '8px' }}>Select Candidate</h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', textAlign: 'center', maxWidth: '320px' }}>
                Choose a candidate from the listing on the left to inspect their live transcripts, scores, and evaluation reports.
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

// Inline fallback icons to avoid missing import bugs
function Code2Icon(props: any) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width={props.size || 24} height={props.size || 24} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <polyline points="16 18 22 12 16 6" />
      <polyline points="8 6 2 12 8 18" />
    </svg>
  );
}

function MessageCircleIcon(props: any) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width={props.size || 24} height={props.size || 24} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />
    </svg>
  );
}

function UserCheckIcon(props: any) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width={props.size || 24} height={props.size || 24} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <polyline points="16 11 18 13 22 9" />
    </svg>
  );
}
