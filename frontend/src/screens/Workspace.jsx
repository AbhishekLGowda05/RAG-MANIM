import React, { useState, useEffect } from 'react';
import { useSession } from '../context/SessionContext';
import VideoPlayer from '../components/VideoPlayer';
import TranscriptPanel from '../components/TranscriptPanel';
import ChatPanel from '../components/ChatPanel';
import MarkdownEditor from '../components/MarkdownEditor';
import PipelineStatus from '../components/PipelineStatus';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:5000';

// Maps subject names to indexed document IDs. Populated dynamically from the
// /api/curriculum/documents endpoint; this object is the static fallback.
const _STATIC_SUBJECT_DOC_MAP = {
  Chemistry: 'Chemistry.pdf',
  Physics: 'physics.pdf',
};

export default function Workspace() {
  const {
    session,
    updateNotes,
    addChatMessage,
    startPipeline,
    newSession,
    activeStageMsg,
    activeProgress
  } = useSession();

  const [inputTopic, setInputTopic] = useState('');
  const [selectedSubject, setSelectedSubject] = useState('Physics');
  const [currentTime, setCurrentTime] = useState(0);
  const [subjectDocMap, setSubjectDocMap] = useState(_STATIC_SUBJECT_DOC_MAP);

  // Fetch indexed documents and build subject → docId map dynamically.
  useEffect(() => {
    async function fetchDocMap() {
      try {
        const res = await fetch(`${BACKEND_URL}/api/curriculum/documents`);
        if (!res.ok) return;
        const data = await res.json();
        const docs = data.documents || [];
        const map = {};
        for (const doc of docs) {
          if (doc.subject && doc.id && doc.indexed !== false) {
            map[doc.subject] = doc.id;
          }
        }
        if (Object.keys(map).length > 0) {
          setSubjectDocMap(map);
        }
      } catch (_) {
        // Fall back to static map silently.
      }
    }
    fetchDocMap();
  }, []);

  useEffect(() => {
    setCurrentTime(0);
  }, [session.video_url]);

  const handleNewLesson = async () => {
    await newSession();
    setInputTopic('');
    setCurrentTime(0);
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (!inputTopic.trim()) return;
    const docId = subjectDocMap[selectedSubject] || null;
    startPipeline(inputTopic.trim(), selectedSubject, docId);
  };

  const isPipelineRunning =
    session.pipeline_stage !== 'idle' &&
    session.pipeline_stage !== 'complete' &&
    session.pipeline_stage !== 'error';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100%', overflow: 'hidden' }}>
      
      {/* Top Topic Input Bar */}
      <div
        style={{
          padding: 'var(--space-4) var(--space-8)',
          background: 'var(--bg-surface)',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 'var(--space-4)'
        }}
      >
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', flex: 1, gap: 'var(--space-3)', maxWidth: '800px' }}>
          <button
            type="button"
            onClick={handleNewLesson}
            disabled={isPipelineRunning}
            className="btn btn-ghost"
            title="Start a new lesson"
            style={{
              padding: '0 14px',
              fontSize: '18px',
              borderRadius: 'var(--r-md)',
              border: '1px solid var(--border-default)',
              minWidth: '44px',
              lineHeight: 1,
            }}
          >
            +
          </button>
          <input
            type="text"
            value={inputTopic}
            onChange={(e) => setInputTopic(e.target.value)}
            disabled={isPipelineRunning}
            placeholder="Ask about any high school textbook topic — e.g., Bohr's Model, Kinetic Theory, Redox Reactions..."
            style={{
              flex: 1,
              background: 'var(--bg-raised)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--r-md)',
              padding: '10px var(--space-4)',
              color: 'var(--text-primary)',
              fontSize: '13px',
              outline: 'none',
              transition: 'border-color 0.2s'
            }}
            onFocus={(e) => (e.target.style.borderColor = 'var(--accent-blue)')}
            onBlur={(e) => (e.target.style.borderColor = 'var(--border-default)')}
          />
          
          <select
            value={selectedSubject}
            onChange={(e) => setSelectedSubject(e.target.value)}
            disabled={isPipelineRunning}
            style={{
              background: 'var(--bg-raised)',
              border: '1px solid var(--border-default)',
              color: 'var(--text-primary)',
              borderRadius: 'var(--r-md)',
              padding: '0 var(--space-4)',
              fontSize: '13px',
              outline: 'none'
            }}
          >
            <option value="Physics">Physics ⚡</option>
            <option value="Chemistry">Chemistry 🧪</option>
            <option value="Mathematics">Mathematics 📐</option>
            <option value="Biology">Biology 🌿</option>
          </select>

          <button
            type="submit"
            disabled={isPipelineRunning || !inputTopic.trim()}
            className="btn btn-primary"
            style={{
              padding: '0 var(--space-6)',
              fontSize: '13px',
              borderRadius: 'var(--r-md)',
              whiteSpace: 'nowrap'
            }}
          >
            Generate Lesson
          </button>
        </form>

        {session.topic_resolved && session.pipeline_stage !== 'idle' ? (
          <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Current Topic:</span>
            <span
              className="badge badge-amber"
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: '12px',
                padding: '4px 10px',
                borderRadius: '100px'
              }}
            >
              {session.topic_resolved}
            </span>
            <button
              type="button"
              onClick={handleNewLesson}
              disabled={isPipelineRunning}
              className="btn btn-ghost"
              style={{ fontSize: '11px', padding: '4px 10px' }}
            >
              New Lesson
            </button>
          </div>
        ) : null}
      </div>

      {/* Main Workspace Workspace Flow */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>
        {/* Pipeline running active screen view overlay */}
        {isPipelineRunning ? (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              background: 'rgba(15,15,20,0.92)',
              backdropFilter: 'blur(10px)',
              zIndex: 100,
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              padding: 'var(--space-6)',
              overflowY: 'auto'
            }}
          >
            <PipelineStatus
              currentStage={session.pipeline_stage}
              message={activeStageMsg}
              progress={activeProgress}
            />
          </div>
        ) : null}

        {/* Dynamic workspace views split panels */}
        {session.pipeline_stage === 'idle' && !isPipelineRunning ? (
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              alignItems: 'center',
              color: 'var(--text-secondary)',
              gap: 'var(--space-4)',
              textAlign: 'center',
              padding: 'var(--space-10)'
            }}
          >
            <span style={{ fontSize: '64px' }}>🎓</span>
            <h2 className="serif-title" style={{ fontSize: '28px', color: 'var(--text-primary)', margin: 0 }}>
              Your Lecture Theatre Awaits
            </h2>
            <p style={{ maxWidth: '400px', fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
              Type a textbook chapter or scientific concept above. The multi-agent educational pipeline will index the syllabus, planning visual scenes, and synthesizing premium animated movies with professional spoken explanations.
            </p>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', flex: 1, height: '100%', overflow: 'hidden' }}>
            
            {/* Left Column: Player & Transcript */}
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--space-4)',
                padding: 'var(--space-6)',
                borderRight: '1px solid var(--border-subtle)',
                overflowY: 'auto',
                height: '100%'
              }}
            >
              {/* Custom custom video player with ticks */}
              <VideoPlayer
                videoUrl={session.video_url}
                scenePlan={session.scene_plan}
                onTimeUpdate={setCurrentTime}
              />

              {/* Time synchronized word highlight scrolling transcription */}
              <div style={{ flex: 1, minHeight: '200px' }}>
                <TranscriptPanel
                  currentTime={currentTime}
                  scenePlan={session.scene_plan}
                  isPipelineRunning={isPipelineRunning}
                />
              </div>
            </div>

            {/* Right Column: AI Doubts Chat & Notebook */}
            <div style={{ display: 'grid', gridTemplateRows: '1.2fr 1fr', height: '100%', overflow: 'hidden' }}>
              
              {/* Bubble dialog conversation co-pilot */}
              <div style={{ overflow: 'hidden' }}>
                <ChatPanel
                  messages={session.messages || []}
                  onSendMessage={(content) => addChatMessage('user', content)}
                  isPipelineRunning={isPipelineRunning}
                />
              </div>

              {/* Autosaving Personal markdown journal */}
              <div style={{ borderTop: '1px solid var(--border-subtle)', overflow: 'hidden' }}>
                <MarkdownEditor
                  notes={session.notes || ''}
                  onNotesChange={updateNotes}
                />
              </div>

            </div>

          </div>
        )}
      </div>

    </div>
  );
}
