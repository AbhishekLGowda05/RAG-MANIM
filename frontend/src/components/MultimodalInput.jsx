import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Mic, MicOff, Image as ImageIcon, X, Send, Loader2, Sparkles } from 'lucide-react';

const BACKEND = 'http://localhost:8000';

/**
 * MultimodalInput – A ChatGPT/Gemini-style input bar supporting:
 *   1. Text  – plain keyboard typing
 *   2. Voice – Web Speech API (live transcript) with Gemini audio fallback
 *   3. Image – Upload image → Gemini Vision extracts educational topic
 */
export default function MultimodalInput({
  onSubmit,
  disabled = false,
  placeholder = "Ask about any textbook topic — type, speak, or attach an image...",
  subject,
}) {
  const [text, setText] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [imageLoading, setImageLoading] = useState(false);
  const [imageError, setImageError] = useState('');

  // Voice state
  const [voiceState, setVoiceState] = useState('idle'); // idle | listening | processing | done | error
  const [voiceError, setVoiceError] = useState('');
  const recognitionRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const imageInputRef = useRef(null);

  // ── Helpers ──────────────────────────────────────────────────────────────

  const isBrowserSpeechSupported = () =>
    'SpeechRecognition' in window || 'webkitSpeechRecognition' in window;

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    const finalText = text.trim();
    if (!finalText || disabled) return;
    onSubmit(finalText, subject);
    setText('');
    setImageFile(null);
    setImagePreview(null);
    setImageError('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // ── Image handling ────────────────────────────────────────────────────────

  const handleImageSelect = async (file) => {
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setImageError('Please select a valid image file.');
      return;
    }

    setImageFile(file);
    setImageError('');
    // Local preview
    const reader = new FileReader();
    reader.onload = (e) => setImagePreview(e.target.result);
    reader.readAsDataURL(file);

    // Send to backend Gemini Vision
    setImageLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch(`${BACKEND}/api/input/understand-image`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Image analysis failed');
      }

      const data = await res.json();
      if (data.topic) {
        setText(data.topic);
      }
    } catch (err) {
      setImageError(`Vision error: ${err.message}`);
    } finally {
      setImageLoading(false);
    }
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) handleImageSelect(file);
  };

  const clearImage = () => {
    setImageFile(null);
    setImagePreview(null);
    setImageError('');
    if (imageInputRef.current) imageInputRef.current.value = '';
  };

  // ── Voice handling ────────────────────────────────────────────────────────

  const startVoiceInput = useCallback(async () => {
    setVoiceError('');

    // Strategy 1: Web Speech API (Chrome / Edge) — live transcript, no backend
    if (isBrowserSpeechSupported()) {
      const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.lang = 'en-US';
      recognition.continuous = false;
      recognition.interimResults = true;

      recognition.onstart = () => setVoiceState('listening');

      recognition.onresult = (event) => {
        let interim = '';
        let final = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            final += transcript;
          } else {
            interim += transcript;
          }
        }
        setText(final || interim);
      };

      recognition.onerror = (event) => {
        setVoiceState('error');
        setVoiceError(`Voice error: ${event.error}. Please try again.`);
      };

      recognition.onend = () => {
        setVoiceState('done');
        setTimeout(() => setVoiceState('idle'), 1500);
      };

      recognitionRef.current = recognition;
      recognition.start();
      return;
    }

    // Strategy 2: MediaRecorder → send audio blob to Gemini via backend
    setVoiceState('listening');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        setVoiceState('processing');
        stream.getTracks().forEach((t) => t.stop());

        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.webm');

        try {
          const res = await fetch(`${BACKEND}/api/input/transcribe-audio`, {
            method: 'POST',
            body: formData,
          });
          if (!res.ok) throw new Error('Transcription failed');
          const data = await res.json();
          if (data.transcript) setText(data.transcript);
          setVoiceState('done');
          setTimeout(() => setVoiceState('idle'), 1500);
        } catch (err) {
          setVoiceError(`Transcription error: ${err.message}`);
          setVoiceState('error');
        }
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
    } catch (err) {
      setVoiceState('error');
      setVoiceError('Microphone access denied. Please allow microphone permissions.');
    }
  }, []);

  const stopVoiceInput = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (voiceState === 'listening') setVoiceState('processing');
  }, [voiceState]);

  const handleMicToggle = () => {
    if (voiceState === 'idle' || voiceState === 'error' || voiceState === 'done') {
      startVoiceInput();
    } else if (voiceState === 'listening') {
      stopVoiceInput();
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) recognitionRef.current.abort();
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  // ── Render ────────────────────────────────────────────────────────────────

  const isListening = voiceState === 'listening';
  const isProcessing = voiceState === 'processing' || imageLoading;
  const canSubmit = text.trim().length > 0 && !disabled && !isProcessing;

  return (
    <div
      style={{ width: '100%', position: 'relative' }}
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleFileDrop}
    >
      {/* Image preview strip */}
      {imagePreview && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '10px',
          marginBottom: '8px', padding: '8px 12px',
          background: 'rgba(99,102,241,0.1)', borderRadius: '12px',
          border: '1px solid rgba(99,102,241,0.25)'
        }}>
          <img
            src={imagePreview}
            alt="Attached"
            style={{ width: 40, height: 40, borderRadius: 8, objectFit: 'cover', border: '1px solid rgba(255,255,255,0.1)' }}
          />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 4 }}>
              {imageLoading ? (
                <>
                  <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} />
                  <span>Gemini Vision is reading the image…</span>
                </>
              ) : (
                <>
                  <Sparkles size={12} style={{ color: '#a78bfa' }} />
                  <span style={{ color: '#a78bfa' }}>Topic extracted from image</span>
                </>
              )}
            </div>
            {imageFile && (
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {imageFile.name}
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={clearImage}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4, borderRadius: 4, display: 'flex' }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Error banners */}
      {(voiceError || imageError) && (
        <div style={{
          marginBottom: 8, padding: '6px 12px', borderRadius: 8,
          background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)',
          fontSize: 12, color: '#f87171', display: 'flex', alignItems: 'center', gap: 6
        }}>
          <X size={12} />
          {voiceError || imageError}
          <button
            type="button"
            onClick={() => { setVoiceError(''); setImageError(''); setVoiceState('idle'); }}
            style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#f87171', padding: 0 }}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Voice status banner */}
      {(isListening || voiceState === 'processing' || voiceState === 'done') && !voiceError && (
        <div style={{
          marginBottom: 8, padding: '6px 12px', borderRadius: 8,
          background: isListening ? 'rgba(239,68,68,0.08)' : 'rgba(99,102,241,0.08)',
          border: `1px solid ${isListening ? 'rgba(239,68,68,0.25)' : 'rgba(99,102,241,0.25)'}`,
          fontSize: 12, color: isListening ? '#fca5a5' : '#a5b4fc',
          display: 'flex', alignItems: 'center', gap: 6
        }}>
          {isListening && (
            <>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#ef4444', animation: 'pulse 1s infinite' }} />
              Listening… speak your question, then click the mic to stop.
            </>
          )}
          {voiceState === 'processing' && !imageLoading && (
            <>
              <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} />
              Transcribing with Gemini…
            </>
          )}
          {voiceState === 'done' && (
            <>
              <Sparkles size={12} />
              Voice captured!
            </>
          )}
        </div>
      )}

      {/* Main input row */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        background: 'var(--bg-raised)',
        border: '1px solid var(--border-default)',
        borderRadius: 24,
        padding: '4px 8px 4px 20px',
        boxShadow: '0 2px 12px rgba(0,0,0,0.25)',
        transition: 'border-color 0.2s, box-shadow 0.2s',
      }}
        onFocus={() => {}}
      >
        {/* Text area */}
        <textarea
          rows={1}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            // Auto-resize
            e.target.style.height = 'auto';
            e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
          }}
          onKeyDown={handleKeyDown}
          disabled={disabled || isProcessing}
          placeholder={isListening ? 'Listening… speak now…' : placeholder}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'var(--text-primary)',
            fontSize: '14px',
            lineHeight: '1.5',
            resize: 'none',
            maxHeight: 120,
            padding: '10px 0',
            fontFamily: 'inherit',
          }}
        />

        {/* Action buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, paddingRight: 4 }}>

          {/* Image attach */}
          <label
            title="Attach an image — Gemini Vision will read it"
            style={{
              cursor: disabled ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: 32, height: 32, borderRadius: '50%',
              color: imageFile ? '#a78bfa' : 'var(--text-muted)',
              transition: 'all 0.2s',
            }}
          >
            <input
              ref={imageInputRef}
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              disabled={disabled}
              onChange={(e) => handleImageSelect(e.target.files?.[0])}
            />
            {imageLoading ? (
              <Loader2 size={17} style={{ animation: 'spin 1s linear infinite', color: '#a78bfa' }} />
            ) : (
              <ImageIcon size={17} />
            )}
          </label>

          {/* Mic button */}
          <button
            type="button"
            onClick={handleMicToggle}
            disabled={disabled || voiceState === 'processing'}
            title={
              isListening ? 'Click to stop recording' :
              voiceState === 'processing' ? 'Processing…' :
              'Click to speak'
            }
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: 32, height: 32, borderRadius: '50%', border: 'none',
              cursor: disabled || voiceState === 'processing' ? 'not-allowed' : 'pointer',
              background: isListening ? '#ef4444' : 'transparent',
              color: isListening ? '#fff' : voiceState === 'done' ? '#a5b4fc' : 'var(--text-muted)',
              transition: 'all 0.2s',
              animation: isListening ? 'pulse-ring 1.5s ease-out infinite' : 'none',
            }}
          >
            {voiceState === 'processing' ? (
              <Loader2 size={17} style={{ animation: 'spin 1s linear infinite' }} />
            ) : isListening ? (
              <MicOff size={17} />
            ) : (
              <Mic size={17} />
            )}
          </button>

          {/* Divider */}
          <div style={{ width: 1, height: 20, background: 'var(--border-subtle)', margin: '0 4px' }} />

          {/* Send button */}
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!canSubmit}
            title="Generate lesson"
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: 34, height: 34, borderRadius: '50%', border: 'none',
              cursor: canSubmit ? 'pointer' : 'not-allowed',
              background: canSubmit
                ? 'linear-gradient(135deg, #6366f1, #8b5cf6)'
                : 'var(--bg-surface)',
              color: canSubmit ? '#fff' : 'var(--text-muted)',
              transition: 'all 0.2s',
              boxShadow: canSubmit ? '0 2px 8px rgba(99,102,241,0.4)' : 'none',
            }}
          >
            <Send size={15} />
          </button>
        </div>
      </div>

      {/* Inline CSS animations */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes pulse-ring {
          0% { box-shadow: 0 0 0 0 rgba(239,68,68,0.5); }
          70% { box-shadow: 0 0 0 8px rgba(239,68,68,0); }
          100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); }
        }
      `}</style>
    </div>
  );
}
