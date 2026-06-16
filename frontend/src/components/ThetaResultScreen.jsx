import React, { useEffect, useState } from 'react';
import ThetaGauge from './ThetaGauge';
import {
  formatTheta,
  getLabelFromTheta,
  getTaglineFromLabel,
  getZoneColor,
} from '../utils/thetaUtils';

export default function ThetaResultScreen({
  subject,
  theta,
  correctCount,
  totalCount = 7,
  onContinue,
  continueLabel = 'Continue',
}) {
  const [displayTheta, setDisplayTheta] = useState(0);
  const label = getLabelFromTheta(theta);
  const zoneColor = getZoneColor(theta);
  const tagline = getTaglineFromLabel(label);

  useEffect(() => {
    const duration = 1500;
    const start = performance.now();
    const from = 0;
    const to = theta ?? 0;

    function tick(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - (1 - progress) ** 3;
      setDisplayTheta(from + (to - from) * eased);
      if (progress < 1) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
  }, [theta]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-5)',
        alignItems: 'center',
        textAlign: 'center',
        padding: 'var(--space-2) 0',
      }}
    >
      <span
        style={{
          fontSize: '11px',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color: 'var(--text-muted)',
        }}
      >
        {subject} Diagnostic Complete
      </span>

      <div
        className="mono-text"
        style={{
          fontSize: '48px',
          fontWeight: 500,
          color: 'var(--text-primary)',
          lineHeight: 1,
        }}
      >
        θ = {formatTheta(displayTheta)}
      </div>

      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          padding: '6px 14px',
          borderRadius: '100px',
          background: `${zoneColor}22`,
          color: zoneColor,
          border: `1px solid ${zoneColor}55`,
          fontSize: '13px',
          fontWeight: 600,
        }}
      >
        <span
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: zoneColor,
          }}
        />
        {label}
      </span>

      <div style={{ width: '100%', maxWidth: '420px' }}>
        <ThetaGauge theta={theta} size="full" animate />
      </div>

      <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
        You answered {correctCount} out of {totalCount} questions correctly
      </p>

      <p
        style={{
          fontSize: '13px',
          color: 'var(--text-secondary)',
          maxWidth: '360px',
          lineHeight: 1.5,
        }}
      >
        {tagline}
      </p>

      <button
        type="button"
        onClick={onContinue}
        className="btn btn-primary"
        style={{ minWidth: '160px', marginTop: 'var(--space-2)' }}
      >
        {continueLabel}
      </button>
    </div>
  );
}
