import React, { useState, useEffect } from 'react';
import { useSession } from '../context/SessionContext';
import { useProfile } from '../context/ProfileContext';
import VideoPlayer from '../components/VideoPlayer';
import TranscriptPanel from '../components/TranscriptPanel';
import ChatPanel from '../components/ChatPanel';
import MarkdownEditor from '../components/MarkdownEditor';
import PipelineStatus from '../components/PipelineStatus';
import MultimodalInput from '../components/MultimodalInput';

export default function Workspace() {
  const {
    session,
    updateNotes,
    addChatMessage,
    startPipeline,
    activeStageMsg,
    activeProgress
  } = useSession();

  const [selectedSubject, setSelectedSubject] = useState('Physics');
  const [currentTime, setCurrentTime] = useState(0);
  const { profile } = useProfile() || {};

  const getSubjectTheta = (subject) => {
    if (profile?.subject_thetas && profile.subject_thetas[subject] !== undefined) {
      return parseFloat(profile.subject_thetas[subject]).toFixed(2);
    }
    const conf = profile?.confidence_map?.[subject];
    if (conf !== undefined) {
      const mapped = -2.0 + 4.0 * (conf / 100.0);
      return parseFloat(mapped).toFixed(2);
    }
    return '0.00';
  };

  useEffect(() => {
    setCurrentTime(0);
  }, [session.video_url]);

  const isPipelineRunning =
    session.pipeline_stage !== 'idle' &&
    session.pipeline_stage !== 'complete' &&
    session.pipeline_stage !== 'error';

  const handleMultimodalSubmit = (topic, subjectOverride) => {
    const sub = subjectOverride || selectedSubject;
    startPipeline(topic.trim(), sub);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100%', overflow: 'hidden' }}>
      
      {/* Top Topic Input Bar */}
      <div
        style={{
          padding: '12px 32px',
          background: 'var(--bg-surface)',
          borderBottom: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '12px', maxWidth: '900px' }}>
          {/* Subject selector */}
          <select
            value={selectedSubject}
            onChange={(e) => setSelectedSubject(e.target.value)}
            disabled={isPipelineRunning}
            style={{
              background: 'var(--bg-raised)',
              border: '1px solid var(--border-default)',
              color: 'var(--text-primary)',
              borderRadius: '20px',
              padding: '10px 14px',
              fontSize: '13px',
              outline: 'none',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              flexShrink: 0,
            }}
          >
            <option value="Physics">⚡ Physics</option>
            <option value="Chemistry">🧪 Chemistry</option>
            <option value="Mathematics">📐 Mathematics</option>
            <option value="Biology">🌿 Biology</option>
          </select>

          {/* Dynamic Theta Ability Rating Indicator */}
          <div
            style={{
              background: 'var(--bg-raised)',
              border: '1px solid var(--border-default)',
              color: 'var(--text-primary)',
              borderRadius: '20px',
              padding: '10px 16px',
              fontSize: '13px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              whiteSpace: 'nowrap',
              flexShrink: 0
            }}
          >
            <span style={{ color: 'var(--text-secondary)' }}>Ability Rating:</span>
            <strong style={{ color: 'var(--accent-blue)', fontFamily: 'var(--font-mono)' }}>
              θ = {getSubjectTheta(selectedSubject)}
            </strong>
          </div>

          {/* Multimodal input */}
          <div style={{ flex: 1 }}>
            <MultimodalInput
              onSubmit={handleMultimodalSubmit}
              disabled={isPipelineRunning}
              subject={selectedSubject}
              placeholder="Ask about any topic — type, speak 🎙️, or attach an image 📷"
            />
          </div>
        </div>

        {session.topic_resolved && (
          <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center', marginTop: 8 }}>
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
          </div>
        )}
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
