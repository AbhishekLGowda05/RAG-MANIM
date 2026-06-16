import React, { useEffect, useState } from 'react';
import { thetaToPercent, THETA_MIN, THETA_MAX } from '../utils/thetaUtils';

const ZONES = [
  { min: -3, max: -1, color: '#ef4444' },
  { min: -1, max: 0, color: '#f97316' },
  { min: 0, max: 0.5, color: '#eab308' },
  { min: 0.5, max: 1, color: '#3b82f6' },
  { min: 1, max: 3, color: '#22c55e' },
];

function zoneWidth(min, max) {
  return ((max - min) / (THETA_MAX - THETA_MIN)) * 100;
}

export default function ThetaGauge({ theta = 0, size = 'full', animate = true }) {
  const targetPercent = thetaToPercent(theta);
  const [indicatorPercent, setIndicatorPercent] = useState(animate ? 0 : targetPercent);
  const height = size === 'compact' ? 10 : 16;
  const markerSize = size === 'compact' ? 12 : 18;

  useEffect(() => {
    if (!animate) {
      setIndicatorPercent(targetPercent);
      return;
    }
    const timeout = setTimeout(() => setIndicatorPercent(targetPercent), 80);
    return () => clearTimeout(timeout);
  }, [targetPercent, animate]);

  return (
    <div style={{ width: '100%' }}>
      <div
        style={{
          position: 'relative',
          height,
          borderRadius: height,
          overflow: 'hidden',
          display: 'flex',
          border: '1px solid var(--border-subtle)',
        }}
      >
        {ZONES.map((zone) => (
          <div
            key={`${zone.min}-${zone.max}`}
            style={{
              width: `${zoneWidth(zone.min, zone.max)}%`,
              background: zone.color,
              opacity: 0.85,
            }}
          />
        ))}
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: `${indicatorPercent}%`,
            transform: 'translate(-50%, -50%)',
            width: markerSize,
            height: markerSize,
            borderRadius: '50%',
            background: 'var(--text-primary)',
            border: '2px solid var(--bg-base)',
            boxShadow: '0 2px 8px rgba(0,0,0,0.35)',
            transition: animate ? 'left 1.2s cubic-bezier(0.22, 1, 0.36, 1)' : 'none',
            zIndex: 2,
          }}
        />
      </div>
      {size === 'full' && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            marginTop: '6px',
            fontSize: '10px',
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono)',
          }}
        >
          <span>{THETA_MIN}</span>
          <span>0</span>
          <span>{THETA_MAX}</span>
        </div>
      )}
    </div>
  );
}
