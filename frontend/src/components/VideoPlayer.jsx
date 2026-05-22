import React, { useRef, useState, useEffect } from 'react';

export default function VideoPlayer({ videoUrl, scenePlan, onTimeUpdate }) {
  const videoRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [volume, setVolume] = useState(0.8);
  const [hoverScene, setHoverScene] = useState(null);

  // Playback listener
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleTime = () => {
      setCurrentTime(video.currentTime);
      if (onTimeUpdate) onTimeUpdate(video.currentTime);
    };
    const handleDuration = () => setDuration(video.duration);

    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('timeupdate', handleTime);
    video.addEventListener('durationchange', handleDuration);

    return () => {
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      video.removeEventListener('timeupdate', handleTime);
      video.removeEventListener('durationchange', handleDuration);
    };
  }, [onTimeUpdate]);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) videoRef.current.pause();
    else videoRef.current.play();
  };

  const handleScrub = (e) => {
    if (!videoRef.current || !duration) return;
    const time = (parseFloat(e.target.value) / 100) * duration;
    videoRef.current.currentTime = time;
    setCurrentTime(time);
  };

  const handleSpeed = (s) => {
    if (!videoRef.current) return;
    videoRef.current.playbackRate = s;
    setSpeed(s);
  };

  const handleVolume = (e) => {
    if (!videoRef.current) return;
    const v = parseFloat(e.target.value);
    videoRef.current.volume = v;
    setVolume(v);
  };

  // Compute scene tick mark positions
  const getSceneTicks = () => {
    if (!scenePlan || !duration) return [];
    let accTime = 0;
    return scenePlan.map(sc => {
      const pct = (accTime / duration) * 100;
      const sceneDuration = sc.duration_seconds || 10;
      accTime += sceneDuration;
      return { ...sc, pct, startTime: accTime - sceneDuration };
    });
  };

  const ticks = getSceneTicks();

  // Custom visual fallback when no MP4 file loads
  const isMockUrl = !videoUrl || videoUrl.includes('placeholder') || videoUrl.includes('output.mp4');

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        background: '#000000',
        borderRadius: 'var(--r-lg)',
        overflow: 'hidden',
        border: '1px solid var(--border-default)',
        position: 'relative'
      }}
    >
      {/* Real Video Core or Aesthetic Mock Canvas Card */}
      {isMockUrl ? (
        <div
          style={{
            aspectRatio: '16/9',
            width: '100%',
            background: 'linear-gradient(135deg, #151520, #0f0f14)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            gap: '15px',
            color: 'var(--text-secondary)',
            padding: '20px',
            position: 'relative'
          }}
        >
          <div style={{ fontSize: '42px' }}>🎞️</div>
          <span style={{ fontSize: '13px', letterSpacing: '0.04em', fontFamily: 'var(--font-mono)' }}>
            [MOCK ACTIVE: Simulation Workspace Rendering]
          </span>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', maxWidth: '340px' }}>
            Normally, the Python Manim engine outputs a real MP4 video here. Running simulation timeline is playing at 1x speed.
          </p>
          <div style={{ position: 'absolute', bottom: '20px', left: '20px', display: 'flex', gap: '8px' }}>
            <span className="badge badge-amber">Interactive Nodes active</span>
          </div>
        </div>
      ) : (
        <video
          ref={videoRef}
          src={videoUrl}
          style={{ width: '100%', aspectRatio: '16/9', display: 'block', background: '#000000' }}
          onClick={togglePlay}
        />
      )}

      {/* Scrubber Timeline Area */}
      <div style={{ padding: '8px 16px 4px', background: 'var(--bg-overlay)', position: 'relative' }}>
        
        {/* Hovering Scene Tooltip Label */}
        {hoverScene && (
          <div
            style={{
              position: 'absolute',
              bottom: '100%',
              left: `${hoverScene.pct}%`,
              transform: 'translateX(-50%)',
              background: 'var(--bg-base)',
              border: '1px solid var(--border-strong)',
              borderRadius: 'var(--r-sm)',
              padding: '6px 10px',
              fontSize: '11px',
              color: 'var(--text-primary)',
              whiteSpace: 'nowrap',
              zIndex: 10,
              boxShadow: '0 4px 10px rgba(0,0,0,0.3)',
              marginBottom: '6px'
            }}
          >
            <strong>Scene {hoverScene.scene_number}:</strong> {hoverScene.title} ({hoverScene.duration_seconds}s)
          </div>
        )}

        {/* The Track Slider */}
        <div style={{ position: 'relative', width: '100%', height: '14px', display: 'flex', alignItems: 'center' }}>
          <input
            type="range"
            min="0"
            max="100"
            value={duration ? (currentTime / duration) * 100 : 0}
            onChange={handleScrub}
            style={{
              width: '100%',
              height: '4px',
              background: 'var(--bg-raised)',
              borderRadius: '2px',
              outline: 'none',
              cursor: 'pointer',
              accentColor: 'var(--accent-amber)',
              position: 'relative',
              zIndex: 2
            }}
          />

          {/* Scene Ticks Overlaid on Timeline Track */}
          {ticks.map((t, idx) => (
            <div
              key={idx}
              onMouseEnter={() => setHoverScene(t)}
              onMouseLeave={() => setHoverScene(null)}
              onClick={() => {
                if (videoRef.current) videoRef.current.currentTime = t.startTime;
              }}
              style={{
                position: 'absolute',
                left: `${t.pct}%`,
                width: '6px',
                height: '6px',
                background: 'var(--accent-amber)',
                borderRadius: '50%',
                border: '1px solid var(--bg-overlay)',
                cursor: 'pointer',
                transform: 'translate(-50%, -50%)',
                top: '50%',
                zIndex: 3,
                boxShadow: '0 0 4px var(--accent-amber)'
              }}
            />
          ))}
        </div>
      </div>

      {/* Control Buttons Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '8px 16px',
          background: 'var(--bg-overlay)',
          borderTop: '1px solid var(--border-subtle)',
          flexWrap: 'wrap',
          gap: '10px'
        }}
      >
        {/* Play/Pause controls */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button
            onClick={togglePlay}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-primary)',
              fontSize: '18px',
              cursor: 'pointer'
            }}
          >
            {isPlaying ? '⏸️' : '▶️'}
          </button>
          
          <span className="mono-text" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            {Math.floor(currentTime / 60)}:{(Math.floor(currentTime % 60) < 10 ? '0' : '') + Math.floor(currentTime % 60)}
            {' / '}
            {duration ? `${Math.floor(duration / 60)}:${(Math.floor(duration % 60) < 10 ? '0' : '') + Math.floor(duration % 60)}` : '0:30'}
          </span>
        </div>

        {/* Volume controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '14px' }}>🔊</span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={volume}
            onChange={handleVolume}
            style={{ width: '60px', accentColor: 'var(--accent-blue)', height: '4px' }}
          />
        </div>

        {/* Speed controls */}
        <div style={{ display: 'flex', gap: '4px' }}>
          {[0.75, 1, 1.25, 1.5, 2].map(s => (
            <button
              key={s}
              onClick={() => handleSpeed(s)}
              style={{
                padding: '2px 6px',
                borderRadius: '4px',
                border: 'none',
                background: speed === s ? 'var(--accent-amber-dim)' : 'transparent',
                color: speed === s ? 'var(--accent-amber)' : 'var(--text-secondary)',
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
                cursor: 'pointer',
                fontWeight: speed === s ? '600' : '400'
              }}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
