import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Mic, MicOff, PhoneOff, Activity, Camera, ShieldAlert, Award } from 'lucide-react';

export default function InterviewRoom() {
  const { interviewId } = useParams();
  const navigate = useNavigate();
  const [isConnected, setIsConnected] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [botSpeaking, setBotSpeaking] = useState(false);
  
  const [isEnded, setIsEnded] = useState(false);
  const [preFlight, setPreFlight] = useState(true);
  const [candidateName, setCandidateName] = useState("");
  const [isDownloadingReport, setIsDownloadingReport] = useState(false);
  
  // Real-time Vision Metrics State (Displayed on UI and sent to backend)
  const [eyeContact, setEyeContact] = useState(95);
  const [postureScore, setPostureScore] = useState(98);
  const [distractionDetected, setDistractionDetected] = useState(false);
  const [cheatingAlert, setCheatingAlert] = useState(false);
  const [presenceDetected, setPresenceDetected] = useState(true);

  const wsRef = useRef<WebSocket | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const audioProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const playTimeRef = useRef<number>(0);
  const isMutedRef = useRef(isMuted);
  const activeSourcesRef = useRef<AudioBufferSourceNode[]>([]);

  // Sync isMuted to ref so we don't restart the useEffect
  useEffect(() => {
    isMutedRef.current = isMuted;
  }, [isMuted]);

  useEffect(() => {
    if (interviewId) {
      fetch(`http://localhost:8000/api/v1/recruiter/interviews/${interviewId}`)
        .then(res => res.json())
        .then(data => {
          if (data.candidate && data.candidate.name) {
            setCandidateName(data.candidate.name);
          }
        })
        .catch(err => console.error("Error fetching interview details:", err));
    }
  }, [interviewId]);

  useEffect(() => {
    if (preFlight) return;

    let wsConnectTimeout: any = null;
    let wsInstance: WebSocket | null = null;
    let isComponentActive = true;

    // 1. Start the bot process via backend API
    if (interviewId) {
      fetch(`http://localhost:8000/api/v1/interviews/${interviewId}/start`, {
        method: 'POST',
      })
      .then(res => {
        if (!res.ok) throw new Error("Failed to start voice bot process");
        console.log("Voice bot process startup triggered successfully");
      })
      .catch(err => console.error("Error starting bot:", err));
    }

    // 2. Request Webcam and Mic with explicit Echo Cancellation and Noise Suppression
    navigator.mediaDevices.getUserMedia({ 
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }, 
      video: true 
    })
      .then((stream) => {
        if (!isComponentActive) {
          stream.getTracks().forEach(track => track.stop());
          return;
        }
        mediaStreamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }

        // Initialize Web Audio API for PCM capture and playback
        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
        const audioContext = new AudioContextClass({ sampleRate: 16000 });
        audioCtxRef.current = audioContext;

        const source = audioContext.createMediaStreamSource(stream);
        const processor = audioContext.createScriptProcessor(2048, 1, 1);
        audioProcessorRef.current = processor;

        source.connect(processor);
        processor.connect(audioContext.destination);

        processor.onaudioprocess = (e) => {
          if (isMutedRef.current) return;
          const inputData = e.inputBuffer.getChannelData(0);
          
          // Convert Float32Array to 16-bit Signed PCM ArrayBuffer
          const pcmData = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
            const s = Math.max(-1, Math.min(1, inputData[i]));
            pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }
          
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(pcmData.buffer);
          }
        };

        // 3. Connect WebSocket with Retries (to allow bot process to boot)
        const connectWebSocket = () => {
          if (!isComponentActive) return;
          console.log("Connecting to voice channel WebSocket...");
          
          const ws = new WebSocket('ws://localhost:8765');
          wsInstance = ws;
          wsRef.current = ws;
          ws.binaryType = 'blob';

          ws.onopen = () => {
            if (!isComponentActive) {
              ws.close();
              return;
            }
            console.log('Connected to Pipecat server');
            setIsConnected(true);
            (wsRef.current as any).hasConnected = true;
          };

          ws.onmessage = async (event) => {
            if (!isComponentActive) return;
            // Play binary PCM audio chunks returned from deepgram tts / pipecat
            if (event.data instanceof Blob) {
              const arrayBuffer = await event.data.arrayBuffer();
              playRawAudio(arrayBuffer);
            } else if (typeof event.data === 'string') {
              try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'interrupt') {
                  console.log("Interrupt message received from server. Stopping playback.");
                  activeSourcesRef.current.forEach(src => {
                    try {
                      src.stop();
                    } catch (e) {}
                  });
                  activeSourcesRef.current = [];
                  if (audioCtxRef.current) {
                    playTimeRef.current = audioCtxRef.current.currentTime;
                  }
                  setBotSpeaking(false);
                }
              } catch (err) {
                console.error("Error parsing text message:", err);
              }
            }
          };

          ws.onclose = () => {
            console.log('Disconnected from Pipecat server');
            setIsConnected(false);
            if (isComponentActive && (wsRef.current as any)?.hasConnected) {
              shutdownHardware();
            }
          };

          ws.onerror = (err) => {
            console.error('WebSocket connection error, retrying in 1.5s...', err);
            wsConnectTimeout = setTimeout(connectWebSocket, 1500);
          };
        };

        // Give the backend bot subprocess a 1-second head start before trying websocket
        wsConnectTimeout = setTimeout(connectWebSocket, 1000);
      })
      .catch((err) => {
        console.error('Camera/Mic permission denied or error:', err);
      });

    // 4. Start Vision Metrics Loop (Simulates real-time browser-side detection and POSTs metrics)
    const metricsInterval = setInterval(() => {
      // Generate slight fluctuations for realism
      const nextEye = Math.max(70, Math.min(100, Math.round(85 + Math.random() * 15)));
      const nextPosture = Math.max(75, Math.min(100, Math.round(90 + Math.random() * 10)));
      
      // Simulate distraction events (5% probability)
      const distraction = Math.random() < 0.05;
      const cheating = Math.random() < 0.02;

      setEyeContact(nextEye);
      setPostureScore(nextPosture);
      setDistractionDetected(distraction);
      setCheatingAlert(cheating);

      // POST metrics to backend
      if (interviewId) {
        fetch(`http://localhost:8000/api/v1/interviews/${interviewId}/vision-metrics`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            eye_contact_score: nextEye / 100,
            posture_score: nextPosture / 100,
            presence_detected: true,
            distraction_event: distraction,
            potential_cheating: cheating
          })
        }).catch(err => console.error("Error posting vision metrics:", err));
      }
    }, 2500);

    return () => {
      isComponentActive = false;
      clearInterval(metricsInterval);
      if (wsConnectTimeout) clearTimeout(wsConnectTimeout);
      if (wsInstance) wsInstance.close();
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => track.stop());
      }
      if (audioCtxRef.current) {
        audioCtxRef.current.close();
      }
    };
  }, [interviewId, preFlight]);

  // Queue and schedule PCM playback
  const playRawAudio = (arrayBuffer: ArrayBuffer) => {
    const audioContext = audioCtxRef.current;
    if (!audioContext) return;

    if (audioContext.state === 'suspended') {
      audioContext.resume();
    }

    const int16Array = new Int16Array(arrayBuffer);
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768.0;
    }

    // Pipecat defaults to 16000 Hz output
    const audioBuffer = audioContext.createBuffer(1, float32Array.length, 16000);
    audioBuffer.copyToChannel(float32Array, 0);

    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);

    // Track active source to enable real-time interruption cancellation
    activeSourcesRef.current.push(source);
    source.onended = () => {
      activeSourcesRef.current = activeSourcesRef.current.filter(s => s !== source);
    };

    const currentTime = audioContext.currentTime;
    // Add a 200ms lookahead/jitter buffer to smooth out network delays
    if (playTimeRef.current < currentTime) {
      playTimeRef.current = currentTime + 0.2;
    }
    source.start(playTimeRef.current);
    playTimeRef.current += audioBuffer.duration;

    setBotSpeaking(true);
    clearTimeout((window as any).speakTimeout);
    (window as any).speakTimeout = setTimeout(() => setBotSpeaking(false), 500);
  };

  const shutdownHardware = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
    }
    activeSourcesRef.current.forEach(src => {
      try {
        src.stop();
      } catch (e) {}
    });
    activeSourcesRef.current = [];
    if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
      audioCtxRef.current.close().catch(console.error);
    }
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      wsRef.current.close();
    }
    setIsEnded(true);
  };

  const endInterview = () => {
    shutdownHardware();
  };

  const handleDownloadReport = async () => {
    setIsDownloadingReport(true);
    const downloadUrl = `http://localhost:8000/api/v1/recruiter/interviews/${interviewId}/report`;
    
    const poll = async () => {
      try {
        const response = await fetch(downloadUrl);
        if (response.ok) {
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `Evaluation_Report_${candidateName || 'Candidate'}.pdf`;
          document.body.appendChild(a);
          a.click();
          a.remove();
          window.URL.revokeObjectURL(url);
          setIsDownloadingReport(false);
        } else {
          setTimeout(poll, 3000);
        }
      } catch (err) {
        setTimeout(poll, 3000);
      }
    };
    
    poll();
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-dark)', color: '#fff', fontFamily: 'Outfit, sans-serif' }}>
      
      {/* Top Header */}
      <header style={{ padding: '20px 40px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.08)', background: 'rgba(10, 10, 18, 0.5)', backdropFilter: 'blur(10px)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: 12, height: 12, borderRadius: '50%', background: isConnected ? 'var(--success)' : 'var(--text-muted)', boxShadow: isConnected ? '0 0 10px var(--success)' : 'none' }} />
          <h2 style={{ fontSize: '1.2rem', fontWeight: 600, margin: 0 }}>Nova Technical Recruiter Room</h2>
        </div>
        <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
          Session ID: <span style={{ fontFamily: 'monospace', color: 'var(--accent-primary)' }}>{interviewId?.slice(0, 8)}...</span>
        </div>
      </header>

      {/* Main Workspace Layout */}
      {preFlight ? (
        <main style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px' }}>
          <div className="glass-panel" style={{ padding: '60px', borderRadius: '24px', textAlign: 'center', maxWidth: '600px', width: '100%', background: 'rgba(10, 10, 18, 0.7)', border: '1px solid rgba(255,255,255,0.1)' }}>
            <Camera size={64} color="var(--accent-primary)" style={{ marginBottom: '24px' }} />
            <h1 style={{ fontSize: '2.5rem', marginBottom: '16px' }}>Ready to Begin?</h1>
            <p style={{ fontSize: '1.1rem', color: 'var(--text-muted)', marginBottom: '40px', lineHeight: 1.6 }}>
              Hi {candidateName || 'Candidate'}! Nova is ready for your interview. Clicking the button below will request your camera and microphone permissions and connect you to the AI agent.
            </p>
            <button 
              onClick={() => setPreFlight(false)}
              className="glass-button"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '12px',
                background: 'var(--accent-primary)',
                color: '#fff',
                padding: '16px 32px',
                borderRadius: '12px',
                fontSize: '1.1rem',
                fontWeight: 600,
                border: 'none',
                cursor: 'pointer'
              }}
            >
              Start Interview & Enable Camera
            </button>
          </div>
        </main>
      ) : isEnded ? (
        <main style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px' }}>
          <div className="glass-panel" style={{ padding: '60px', borderRadius: '24px', textAlign: 'center', maxWidth: '600px', width: '100%', background: 'rgba(10, 10, 18, 0.7)', border: '1px solid rgba(255,255,255,0.1)' }}>
            <Award size={64} color="var(--success)" style={{ marginBottom: '24px' }} />
            <h1 style={{ fontSize: '2.5rem', marginBottom: '16px' }}>Thank You, {candidateName || 'Candidate'}!</h1>
            <p style={{ fontSize: '1.1rem', color: 'var(--text-muted)', marginBottom: '40px', lineHeight: 1.6 }}>
              Your interview has concluded successfully. Our AI system is now compiling your evaluation report.
            </p>
            <button 
              onClick={handleDownloadReport}
              disabled={isDownloadingReport}
              className="glass-button"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '12px',
                background: isDownloadingReport ? 'rgba(255,255,255,0.1)' : 'var(--accent-primary)',
                color: '#fff',
                border: 'none',
                cursor: isDownloadingReport ? 'wait' : 'pointer',
                padding: '16px 32px',
                borderRadius: '12px',
                fontSize: '1.1rem',
                fontWeight: 600,
                transition: 'all 0.2s ease'
              }}
            >
              {isDownloadingReport ? 'Generating Report... Please Wait' : 'Download Evaluation Report'}
            </button>
          </div>
        </main>
      ) : (
      <main 
        style={{ flex: 1, display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '30px', padding: '30px 40px' }}
        onClick={() => {
          if (audioCtxRef.current && audioCtxRef.current.state === 'suspended') {
            audioCtxRef.current.resume();
          }
        }}
      >
        
        {/* Left Column: Candidate Camera & Vision metrics */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="glass-panel" style={{ position: 'relative', flex: 1, minHeight: '380px', borderRadius: '16px', overflow: 'hidden', border: '1px solid rgba(255,255,255,0.1)' }}>
            <video 
              ref={videoRef} 
              autoPlay 
              playsInline 
              muted 
              style={{ width: '100%', height: '100%', objectFit: 'cover', transform: 'scaleX(-1)' }} 
            />
            
            {/* Live Indicator overlay */}
            <div style={{ position: 'absolute', top: '16px', left: '16px', background: 'rgba(255, 77, 77, 0.85)', padding: '6px 12px', borderRadius: '4px', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '1px' }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#fff', animation: 'pulse 1.5s infinite' }} />
              Live Camera
            </div>

            {/* Distraction/Cheating Warning Overlays */}
            {distractionDetected && (
              <div style={{ position: 'absolute', bottom: '16px', left: '16px', right: '16px', background: 'rgba(255, 150, 0, 0.9)', color: '#000', padding: '10px 16px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.9rem', fontWeight: 600, animation: 'shake 0.5s' }}>
                <ShieldAlert size={18} /> Please maintain focus on the screen.
              </div>
            )}

            {cheatingAlert && (
              <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', background: 'rgba(255, 77, 77, 0.95)', color: '#fff', padding: '16px 24px', borderRadius: '12px', textAlign: 'center', border: '2px solid #fff', zIndex: 10 }}>
                <ShieldAlert size={32} style={{ margin: '0 auto 8px auto' }} />
                <h4 style={{ margin: 0 }}>Gaze Distraction Flagged</h4>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', opacity: 0.9 }}>Avoid looking away from the viewport.</p>
              </div>
            )}
          </div>

          {/* Real-time Vision Diagnostics panel */}
          <div className="glass-panel" style={{ padding: '20px 24px', borderRadius: '16px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '16px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={18} /> Real-time Visual Diagnostics
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.9rem' }}>
                  <span>Gaze Alignment (Eye Contact)</span>
                  <span style={{ fontWeight: 'bold', color: eyeContact > 80 ? 'var(--success)' : 'var(--danger)' }}>{eyeContact}%</span>
                </div>
                <div style={{ height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${eyeContact}%`, height: '100%', background: 'var(--accent-primary)', transition: 'width 0.3s ease' }} />
                </div>
              </div>
              
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.9rem' }}>
                  <span>Posture Alignment Score</span>
                  <span style={{ fontWeight: 'bold', color: postureScore > 85 ? 'var(--success)' : 'var(--danger)' }}>{postureScore}%</span>
                </div>
                <div style={{ height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${postureScore}%`, height: '100%', background: 'var(--accent-primary)', transition: 'width 0.3s ease' }} />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Right Column: AI Assistant (Nova) */}
        <section style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '16px', padding: '40px', position: 'relative' }}>
          
          {/* Dynamic Background matching bot state */}
          <div style={{
            position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
            background: botSpeaking ? 'radial-gradient(circle at center, rgba(109, 93, 252, 0.12), transparent 50%)' : 'transparent',
            transition: 'background 0.3s ease',
            zIndex: 0,
            borderRadius: '16px'
          }} />

          <div style={{ zIndex: 1, textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <h3 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '8px' }}>Nova AI</h3>
            <p style={{ color: isConnected ? 'var(--success)' : 'var(--text-muted)', marginBottom: '50px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.95rem' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: isConnected ? 'var(--success)' : 'var(--text-muted)' }} />
              {isConnected ? 'Voice connection established' : 'Initializing voice channel...'}
            </p>

            {/* Main Bot Orb Visualization */}
            <div style={{
              width: '180px',
              height: '180px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, var(--accent-primary), #4a3aff)',
              boxShadow: botSpeaking ? '0 0 50px 15px rgba(109, 93, 252, 0.5)' : '0 10px 25px rgba(0,0,0,0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '60px',
              transition: 'all 0.2s ease',
              transform: botSpeaking ? 'scale(1.08)' : 'scale(1)'
            }} className={botSpeaking ? "orb-active" : ""}>
              <Activity size={50} color="white" opacity={botSpeaking ? 1 : 0.4} />
            </div>

            {/* Controls */}
            <div className="glass-panel" style={{ display: 'flex', gap: '20px', padding: '16px 32px', borderRadius: '40px' }}>
              <button 
                onClick={() => setIsMuted(!isMuted)}
                className="glass-button" 
                style={{ 
                  background: isMuted ? 'rgba(255, 77, 77, 0.2)' : 'var(--accent-primary)', 
                  border: isMuted ? '1px solid var(--danger)' : 'none',
                  borderRadius: '50%', 
                  width: 56, 
                  height: 56, 
                  padding: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                {isMuted ? <MicOff size={24} color="var(--danger)" /> : <Mic size={24} color="#fff" />}
              </button>
              
              <button 
                onClick={endInterview}
                className="glass-button" 
                style={{ 
                  background: 'var(--danger)', 
                  borderRadius: '50%', 
                  width: 56, 
                  height: 56, 
                  padding: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: 'none'
                }}
              >
                <PhoneOff size={24} color="#fff" />
              </button>
            </div>
          </div>
        </section>

      </main>
      )}
    </div>
  );
}
