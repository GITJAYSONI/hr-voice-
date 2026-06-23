import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import CandidatePortal from './pages/CandidatePortal';
import InterviewRoom from './pages/InterviewRoom';
import RecruiterDashboard from './pages/RecruiterDashboard';
import './index.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<CandidatePortal />} />
        <Route path="/interview/:interviewId" element={<InterviewRoom />} />
        <Route path="/dashboard" element={<RecruiterDashboard />} />
      </Routes>
    </Router>
  );
}

export default App;
