export const THETA_MIN = -3;
export const THETA_MAX = 3;

export function getLabelFromTheta(theta) {
  if (theta == null || Number.isNaN(theta)) return 'Intermediate';
  if (theta < -1.0) return 'Beginner';
  if (theta < 0.0) return 'Developing';
  if (theta < 0.5) return 'Intermediate';
  if (theta < 1.0) return 'Advanced';
  return 'Expert';
}

export function getZoneColor(theta) {
  if (theta == null || Number.isNaN(theta)) return '#eab308';
  if (theta < -1.0) return '#ef4444';
  if (theta < 0.0) return '#f97316';
  if (theta < 0.5) return '#eab308';
  if (theta < 1.0) return '#3b82f6';
  return '#22c55e';
}

export function getTaglineFromLabel(label) {
  const taglines = {
    Beginner: "We'll build your foundation step by step.",
    Developing: "We'll reinforce the concepts you need.",
    Intermediate: "We'll match explanations to your level.",
    Advanced: "We'll challenge you with deeper content.",
    Expert: "We'll give you concise, high-level explanations.",
  };
  return taglines[label] || taglines.Intermediate;
}

export function clampTheta(theta) {
  return Math.max(THETA_MIN, Math.min(THETA_MAX, theta));
}

export function thetaToPercent(theta) {
  const clamped = clampTheta(theta ?? 0);
  return ((clamped - THETA_MIN) / (THETA_MAX - THETA_MIN)) * 100;
}

export function formatTheta(theta) {
  if (theta == null || Number.isNaN(theta)) return '—';
  const rounded = Math.round(theta * 100) / 100;
  return rounded >= 0 ? `+${rounded.toFixed(2)}` : rounded.toFixed(2);
}
