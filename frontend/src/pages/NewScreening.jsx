import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Webcam from 'react-webcam';
import {
  Camera, ScanLine, CheckCircle2, RotateCcw, Info, AlertTriangle, Loader
} from 'lucide-react';
import FileUploadZone from '../components/ui/FileUploadZone';
import PipelineStep from '../components/ui/PipelineStep';
import { submitScreening } from '../services/api';
import { PIPELINE_STEPS } from '../data/mockData';

export default function NewScreening() {
  const navigate = useNavigate();
  const webcamRef = useRef(null);

  const [files, setFiles] = useState({ front: null, back: null, live: null });
  const [liveMode, setLiveMode] = useState('upload'); // 'upload' | 'camera'
  const [captured, setCaptured] = useState(null);

  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  const canSubmit = !running && files.front && files.back && (files.live || captured);

  const capture = useCallback(() => {
    const img = webcamRef.current?.getScreenshot();
    if (img) {
      const blob = dataURItoBlob(img);
      const f = new File([blob], 'live_capture.jpg', { type: 'image/jpeg' });
      setCaptured(img);
      setFiles(prev => ({ ...prev, live: f }));
    }
  }, []);

  const resetCapture = () => {
    setCaptured(null);
    setFiles(prev => ({ ...prev, live: null }));
  };

  const handleSubmit = async () => {
    if (!canSubmit) {
      setError('Please upload all required files before screening.');
      return;
    }
    setError('');
    setRunning(true);
    setDone(false);

    try {
      const result = await submitScreening(files.front, files.back, files.live);
      setDone(true);

      // Small delay so user sees "done" state before redirect
      setTimeout(() => {
        navigate(`/screening/result/${result.screening_id}`, { state: { result } });
      }, 600);
    } catch (err) {
      setRunning(false);
      // Show a user-friendly error — never expose stack traces or secrets
      if (err.status === 400 || err.status === 422) {
        setError(err.message || 'Invalid file or request. Please check your uploads and try again.');
      } else if (err.type === 'network') {
        setError('Cannot reach the screening server. Please check your connection.');
      } else {
        setError(err.message || 'Screening failed. Please try again or contact support.');
      }
    }
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-title">New Screening</div>
        <div className="page-subtitle">Upload documents and capture a live photo to begin identity verification</div>
      </div>

      {/* Pipeline progress — shown while running or done */}
      {(running || done) && (
        <div className="card mb-6" style={{ marginBottom: 24 }}>
          <div className="card-title" style={{ marginBottom: 8 }}>
            <ScanLine size={15} color="var(--accent-blue-light)" />
            Screening Pipeline
          </div>
          <div className="pipeline-wrap">
            {PIPELINE_STEPS.map((step, i) => (
              <PipelineStep
                key={step.id}
                label={step.label}
                state={done ? 'done' : i === 0 ? 'active' : 'idle'}
                isLast={i === PIPELINE_STEPS.length - 1}
              />
            ))}
          </div>
          {running && !done && (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 12 }}>
              <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} />
              Processing — please wait…
            </div>
          )}
          {done && (
            <div style={{ textAlign: 'center', color: 'var(--success)', fontSize: 13, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 12 }}>
              <CheckCircle2 size={16} /> Pipeline complete. Redirecting to result…
            </div>
          )}
        </div>
      )}

      {!running && !done && (
        <>
          {/* Info banner */}
          <div className="info-box blue mb-6" style={{ marginBottom: 24 }}>
            <Info size={16} color="var(--accent-blue-light)" style={{ flexShrink: 0, marginTop: 1 }} />
            <div>
              Upload the <strong>front and back</strong> of the ID card and a <strong>live photo</strong> of the person.
              All images must be JPG or PNG, max 10 MB. The live photo is used for face verification against the database reference.
            </div>
          </div>

          {/* Upload grid */}
          <div className="card mb-6" style={{ marginBottom: 24 }}>
            <div className="card-title" style={{ marginBottom: 20 }}>
              Document Upload
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div>
                <div className="form-label">ID Card — Front Side</div>
                <FileUploadZone
                  label="Upload Front of ID Card"
                  file={files.front}
                  onFile={f => setFiles(prev => ({ ...prev, front: f }))}
                />
              </div>
              <div>
                <div className="form-label">ID Card — Back Side</div>
                <FileUploadZone
                  label="Upload Back of ID Card"
                  file={files.back}
                  onFile={f => setFiles(prev => ({ ...prev, back: f }))}
                />
              </div>
            </div>
          </div>

          {/* Live photo */}
          <div className="card mb-6" style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <div className="card-title">Live Photo</div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  className={`btn btn-sm ${liveMode === 'upload' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => { setLiveMode('upload'); resetCapture(); }}
                >
                  Upload File
                </button>
                <button
                  className={`btn btn-sm ${liveMode === 'camera' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => { setLiveMode('camera'); setFiles(prev => ({ ...prev, live: null })); }}
                >
                  <Camera size={13} /> Use Camera
                </button>
              </div>
            </div>

            {liveMode === 'upload' ? (
              <div style={{ maxWidth: 400 }}>
                <FileUploadZone
                  label="Upload Live Photo"
                  file={files.live}
                  onFile={f => setFiles(prev => ({ ...prev, live: f }))}
                />
              </div>
            ) : (
              <div style={{ maxWidth: 400 }}>
                {captured ? (
                  <div>
                    <div style={{ borderRadius: 10, overflow: 'hidden', border: '2px solid var(--success)', marginBottom: 12 }}>
                      <img src={captured} alt="captured" style={{ width: '100%', display: 'block' }} />
                    </div>
                    <button className="btn btn-secondary btn-sm" onClick={resetCapture}>
                      <RotateCcw size={13} /> Retake
                    </button>
                  </div>
                ) : (
                  <div>
                    <div className="webcam-wrap" style={{ marginBottom: 12 }}>
                      <Webcam
                        ref={webcamRef}
                        screenshotFormat="image/jpeg"
                        videoConstraints={{ facingMode: 'user', width: 400, height: 280 }}
                        style={{ width: '100%', maxHeight: 220, objectFit: 'cover', display: 'block' }}
                      />
                      <div className="webcam-overlay">
                        <div className="webcam-corner tl" />
                        <div className="webcam-corner tr" />
                        <div className="webcam-corner bl" />
                        <div className="webcam-corner br" />
                      </div>
                    </div>
                    <button className="btn btn-primary btn-sm" onClick={capture}>
                      <Camera size={13} /> Capture Photo
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Upload checklist */}
          <div className="card mb-6" style={{ marginBottom: 24 }}>
            <div className="card-title" style={{ marginBottom: 14 }}>Upload Checklist</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[
                { label: 'ID Card Front', ok: !!files.front },
                { label: 'ID Card Back', ok: !!files.back },
                { label: 'Live Photo', ok: !!(files.live || captured) },
              ].map(({ label, ok }) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <CheckCircle2 size={16} color={ok ? 'var(--success)' : 'var(--border-default)'} />
                  <span style={{ fontSize: 13, color: ok ? 'var(--text-primary)' : 'var(--text-muted)' }}>{label}</span>
                  <span style={{ marginLeft: 'auto', fontSize: 11, color: ok ? 'var(--success)' : 'var(--text-muted)' }}>
                    {ok ? 'Ready' : 'Required'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Error message */}
          {error && (
            <div className="info-box" style={{ marginBottom: 16, background: 'var(--danger-bg)', borderColor: 'var(--danger)' }}>
              <AlertTriangle size={15} color="var(--danger)" style={{ flexShrink: 0 }} />
              <span style={{ color: 'var(--danger)', fontSize: 13 }}>{error}</span>
            </div>
          )}

          <div style={{ display: 'flex', gap: 12 }}>
            <button
              className="btn btn-primary btn-lg"
              onClick={handleSubmit}
              disabled={!canSubmit}
            >
              <ScanLine size={16} /> Start Screening
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => {
                setFiles({ front: null, back: null, live: null });
                setCaptured(null);
                setError('');
              }}
            >
              Clear All
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function dataURItoBlob(dataURI) {
  const byteString = atob(dataURI.split(',')[1]);
  const mimeString = dataURI.split(',')[0].split(':')[1].split(';')[0];
  const ab = new ArrayBuffer(byteString.length);
  const ia = new Uint8Array(ab);
  for (let i = 0; i < byteString.length; i++) ia[i] = byteString.charCodeAt(i);
  return new Blob([ab], { type: mimeString });
}
