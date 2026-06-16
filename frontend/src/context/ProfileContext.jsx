import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const ProfileContext = createContext();

export const useProfile = () => useContext(ProfileContext);

const DEFAULT_PROFILE = {
  learner_id: '',
  name: '',
  academic_level: 'class_11',
  exam_target: ['JEE'],
  learning_style: 'visual',
  pace_preference: 'balanced',
  weak_subjects: [],
  confidence_map: {
    Chemistry: 50,
    Physics: 50,
    Mathematics: 50
  },
  subject_thetas: {
    Physics: null,
    Chemistry: null,
  },
  created_at: '',
  updated_at: ''
};

export const ProfileProvider = ({ children }) => {
  const [profile, setProfile] = useState(DEFAULT_PROFILE);
  const [subjectThetas, setSubjectThetas] = useState({ ...DEFAULT_PROFILE.subject_thetas });
  const [loading, setLoading] = useState(true);

  const loadSubjectThetas = useCallback(async () => {
    try {
      const response = await fetch('/api/learner/theta');
      if (response.ok) {
        const data = await response.json();
        const thetas = data.subject_thetas || {};
        setSubjectThetas((prev) => ({ ...prev, ...thetas }));
        setProfile((prev) => ({
          ...prev,
          theta: data.theta ?? prev.theta,
          subject_thetas: { ...DEFAULT_PROFILE.subject_thetas, ...thetas },
        }));
        return thetas;
      }
    } catch (err) {
      console.warn('Failed to load subject thetas:', err);
    }
    return null;
  }, []);

  // Load profile from API or LocalStorage fallback
  useEffect(() => {
    async function loadProfile() {
      try {
        const response = await fetch('/api/load/profile.json');
        if (response.ok) {
          const data = await response.json();
          if (data && data.learner_id) {
            setProfile({
              ...DEFAULT_PROFILE,
              ...data,
              subject_thetas: {
                ...DEFAULT_PROFILE.subject_thetas,
                ...(data.subject_thetas || {}),
              },
            });
            if (data.subject_thetas) {
              setSubjectThetas((prev) => ({ ...prev, ...data.subject_thetas }));
            }
            await loadSubjectThetas();
            setLoading(false);
            return;
          }
        }
      } catch (err) {
        console.warn('Failed to load profile from server, checking local storage:', err);
      }

      // Check local storage fallback
      const local = localStorage.getItem('learnos_profile');
      const learnerLocal = localStorage.getItem('aicarls_learner_profile');
      if (local) {
        try {
          const parsed = JSON.parse(local);
          setProfile({
            ...DEFAULT_PROFILE,
            ...parsed,
            subject_thetas: {
              ...DEFAULT_PROFILE.subject_thetas,
              ...(parsed.subject_thetas || {}),
            },
          });
          if (parsed.subject_thetas) {
            setSubjectThetas((prev) => ({ ...prev, ...parsed.subject_thetas }));
          }
        } catch (e) {}
      } else if (learnerLocal) {
        try {
          const parsed = JSON.parse(learnerLocal);
          if (parsed.subject_thetas) {
            setSubjectThetas(parsed.subject_thetas);
            setProfile((prev) => ({
              ...prev,
              subject_thetas: parsed.subject_thetas,
            }));
          }
        } catch (e) {}
      } else {
        // Generate new guest profile
        const newProfile = {
          ...DEFAULT_PROFILE,
          learner_id: `user-${Math.random().toString(36).substr(2, 9)}`,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        };
        setProfile(newProfile);
        localStorage.setItem('learnos_profile', JSON.stringify(newProfile));
      }

      await loadSubjectThetas();
      setLoading(false);
    }
    loadProfile();
  }, [loadSubjectThetas]);

  // Save profile to API and local storage
  const updateProfile = async (updates) => {
    const newProfile = {
      ...profile,
      ...updates,
      updated_at: new Date().toISOString()
    };

    setProfile(newProfile);
    localStorage.setItem('learnos_profile', JSON.stringify(newProfile));

    try {
      await fetch('/api/persist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: 'profile.json',
          payload: newProfile
        })
      });
    } catch (err) {
      console.error('Failed to sync profile with server:', err);
    }
  };

  const resetProfile = async () => {
    const newId = `user-${Math.random().toString(36).substr(2, 9)}`;
    const freshProfile = {
      ...DEFAULT_PROFILE,
      learner_id: newId,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    setProfile(freshProfile);
    localStorage.setItem('learnos_profile', JSON.stringify(freshProfile));

    try {
      await fetch('/api/persist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: 'profile.json',
          payload: freshProfile
        })
      });
      
      // Clear other files by writing empty targets
      await fetch('/api/persist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: 'history.json', payload: { sessions: [] } })
      });

      await fetch('/api/persist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: 'analytics.json',
          payload: {
            total_sessions: 0,
            total_watch_time_seconds: 0,
            topics_covered: [],
            weak_topic_flags: [],
            daily_activity: [],
            subject_distribution: {}
          }
        })
      });
    } catch (err) {
      console.error('Failed to reset data on server:', err);
    }
  };

  const reloadProfile = async () => {
    try {
      const response = await fetch('/api/load/profile.json');
      if (response.ok) {
        const data = await response.json();
        if (data && data.learner_id) {
          const merged = {
            ...DEFAULT_PROFILE,
            ...data,
            subject_thetas: {
              ...DEFAULT_PROFILE.subject_thetas,
              ...(data.subject_thetas || {}),
            },
          };
          setProfile(merged);
          if (data.subject_thetas) {
            setSubjectThetas((prev) => ({ ...prev, ...data.subject_thetas }));
          }
          localStorage.setItem('learnos_profile', JSON.stringify(merged));
          await loadSubjectThetas();
          return merged;
        }
      }
    } catch (err) {
      console.warn('Failed to reload profile:', err);
    }
    return null;
  };

  const updateSubjectTheta = useCallback(async (subject, theta) => {
    const rounded = Math.round(theta * 100) / 100;
    setSubjectThetas((prev) => {
      const next = { ...prev, [subject]: rounded };
      setProfile((p) => ({
        ...p,
        subject_thetas: next,
        theta: rounded,
        updated_at: new Date().toISOString(),
      }));
      return next;
    });

    try {
      await fetch('/api/learner/theta', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theta: rounded, subject }),
      });
    } catch (err) {
      console.error('Failed to sync subject theta:', err);
    }
  }, []);

  const resetSubjectThetas = useCallback(async () => {
    const cleared = { ...DEFAULT_PROFILE.subject_thetas };
    setSubjectThetas(cleared);
    setProfile((prev) => ({
      ...prev,
      subject_thetas: cleared,
      theta: null,
    }));
    localStorage.removeItem('aicarls_learner_profile');
  }, []);

  return (
    <ProfileContext.Provider
      value={{
        profile,
        subjectThetas,
        updateProfile,
        resetProfile,
        reloadProfile,
        updateSubjectTheta,
        resetSubjectThetas,
        loadSubjectThetas,
        loading,
      }}
    >
      {children}
    </ProfileContext.Provider>
  );
};
