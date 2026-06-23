import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, ArrowRight, Loader2 } from 'lucide-react';

export default function CandidatePortal() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const formData = new FormData(e.currentTarget);
    
    // Ensure both files are selected
    const resumeFile = formData.get('resume') as File;
    if (!resumeFile || resumeFile.size === 0) {
      setError('Please upload a PDF resume.');
      setLoading(false);
      return;
    }

    const jdFile = formData.get('jd_file') as File;
    if (!jdFile || jdFile.size === 0) {
      setError('Please upload a PDF Job Description.');
      setLoading(false);
      return;
    }

    try {
      const response = await fetch('http://localhost:8000/api/v1/interviews/register', {
        method: 'POST',
        body: formData, // Browser automatically sets multipart/form-data boundary
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to register candidate');
      }

      const data = await response.json();
      
      // Redirect to the interview room
      navigate(`/interview/${data.interview_id}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '600px', margin: '60px auto', padding: '0 20px' }}>
      <div style={{ textAlign: 'center', marginBottom: '40px' }}>
        <h1 className="gradient-text" style={{ fontSize: '2.5rem', marginBottom: '16px' }}>Nova AI Interviwer</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem' }}>
          Please provide your details and upload your resume and job description to begin your technical interview.
        </p>
      </div>

      <div className="glass-panel" style={{ padding: '32px' }}>
        {error && (
          <div style={{ background: 'rgba(255, 77, 77, 0.1)', border: '1px solid var(--danger)', color: 'var(--danger)', padding: '12px', borderRadius: '8px', marginBottom: '24px' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>Full Name</label>
            <input type="text" name="name" required className="glass-input" placeholder="John Doe" />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>Email</label>
              <input type="email" name="email" required className="glass-input" placeholder="john@example.com" />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>Phone</label>
              <input type="tel" name="phone" required className="glass-input" placeholder="+1 (555) 000-0000" />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>Target Job Title</label>
            <input type="text" name="job_title" required className="glass-input" placeholder="Senior Backend Engineer" />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>Job Description (PDF Only)</label>
            <div style={{ position: 'relative' }}>
              <input 
                type="file" 
                name="jd_file" 
                accept="application/pdf" 
                required 
                className="glass-input" 
                style={{ paddingLeft: '40px' }}
              />
              <Upload size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>Resume (PDF Only)</label>
            <div style={{ position: 'relative' }}>
              <input 
                type="file" 
                name="resume" 
                accept="application/pdf" 
                required 
                className="glass-input" 
                style={{ paddingLeft: '40px' }}
              />
              <Upload size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            </div>
          </div>

          <button type="submit" disabled={loading} className="glass-button" style={{ marginTop: '12px' }}>
            {loading ? (
              <><Loader2 size={20} className="orb-active" style={{ animation: 'spin 1s linear infinite' }} /> Analyzing Resume...</>
            ) : (
              <>Start Interview <ArrowRight size={20} /></>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
