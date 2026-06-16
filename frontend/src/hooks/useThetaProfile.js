import { useCallback, useEffect, useState } from 'react';

const STORAGE_KEY = 'aicarls_learner_profile';

const DEFAULT_SUBJECT_THETAS = {
  Physics: null,
  Chemistry: null,
};

function readLocalProfile() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function writeLocalProfile(profile) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
}

export function useThetaProfile() {
  const [subjectThetas, setSubjectThetas] = useState({ ...DEFAULT_SUBJECT_THETAS });
  const [loading, setLoading] = useState(true);

  const syncFromServer = useCallback(async () => {
    try {
      const res = await fetch('/api/learner/theta');
      if (res.ok) {
        const data = await res.json();
        const serverThetas = data.subject_thetas || {};
        setSubjectThetas((prev) => ({
          ...prev,
          ...serverThetas,
        }));
        const local = readLocalProfile() || {};
        writeLocalProfile({
          ...local,
          subject_thetas: { ...DEFAULT_SUBJECT_THETAS, ...serverThetas },
          completedDiagnostic: Object.values(serverThetas).some((v) => v != null),
        });
        return serverThetas;
      }
    } catch (err) {
      console.warn('Failed to load theta from server:', err);
    }
    return null;
  }, []);

  useEffect(() => {
    async function load() {
      const local = readLocalProfile();
      if (local?.subject_thetas) {
        setSubjectThetas((prev) => ({ ...prev, ...local.subject_thetas }));
      }
      await syncFromServer();
      setLoading(false);
    }
    load();
  }, [syncFromServer]);

  const getTheta = useCallback(
    (subject) => {
      const val = subjectThetas[subject];
      return val != null ? val : null;
    },
    [subjectThetas]
  );

  const setTheta = useCallback(async (subject, theta, meta = {}) => {
    const rounded = Math.round(theta * 100) / 100;
    setSubjectThetas((prev) => {
      const next = { ...prev, [subject]: rounded };
      const local = readLocalProfile() || {};
      writeLocalProfile({
        ...local,
        subject_thetas: next,
        completedDiagnostic: true,
        diagnosticDate: new Date().toISOString(),
        ...meta,
      });
      return next;
    });

    try {
      await fetch('/api/learner/theta', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theta: rounded, subject }),
      });
    } catch (err) {
      console.warn('Failed to persist theta to server:', err);
    }
  }, []);

  const resetThetas = useCallback(async () => {
    const cleared = { ...DEFAULT_SUBJECT_THETAS };
    setSubjectThetas(cleared);
    localStorage.removeItem(STORAGE_KEY);

    try {
      await fetch('/api/learner/theta', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theta: 0, subject: '' }),
      });
    } catch (err) {
      console.warn('Failed to reset theta on server:', err);
    }
  }, []);

  const hasCompletedDiagnostic = useCallback(() => {
    return subjectThetas.Physics != null && subjectThetas.Chemistry != null;
  }, [subjectThetas]);

  return {
    subjectThetas,
    loading,
    getTheta,
    setTheta,
    resetThetas,
    syncFromServer,
    hasCompletedDiagnostic,
  };
}
