import React, { useState, useEffect } from 'react';

export default function DiagnosticQuiz({
  onComplete,
  onSkip,
  subject = 'Physics',
  totalQuestions = 7,
}) {
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [responses, setResponses] = useState([]);
  const [selectedOption, setSelectedOption] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    startDiagnostic();
  }, [subject]);

  const getItemId = (item) => item?.question_id || item?.item_id;

  const startDiagnostic = async () => {
    setLoading(true);
    setError(null);
    setResponses([]);
    setSelectedOption(null);
    try {
      const res = await fetch('/api/diagnostic/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subject }),
      });
      const data = await res.json();
      if (data.item && Object.keys(data.item).length > 0) {
        setCurrentQuestion(data.item);
      } else {
        onSkip();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitAnswer = async () => {
    if (!currentQuestion || !selectedOption || submitting) return;

    setSubmitting(true);
    const isCorrect = selectedOption === currentQuestion.answer ? 1 : 0;
    const itemId = getItemId(currentQuestion);

    const newResponses = [
      ...responses,
      { item_id: itemId, is_correct: isCorrect },
    ];

    setResponses(newResponses);
    setSelectedOption(null);

    try {
      const res = await fetch('/api/diagnostic/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ responses: newResponses, subject }),
      });
      const data = await res.json();

      if (data.complete || !data.item) {
        const correctCount = newResponses.filter((r) => r.is_correct === 1).length;
        onComplete({
          theta: data.theta ?? 0.0,
          correctCount,
          totalCount: newResponses.length,
        });
      } else {
        setCurrentQuestion(data.item);
        setSubmitting(false);
      }
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  };

  const progressPercent = (responses.length / totalQuestions) * 100;
  const questionNumber = responses.length + 1;

  if (loading && !currentQuestion) {
    return (
      <div style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--text-secondary)' }}>
        Loading {subject} diagnostic...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--accent-rose)' }}>
        Error: {error}
      </div>
    );
  }

  return (
    <div
      style={{
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-5)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)' }}>
          {subject} Diagnostic
        </h3>
        <span
          style={{
            fontSize: '12px',
            fontWeight: 500,
            padding: '4px 12px',
            borderRadius: '100px',
            background: 'var(--bg-overlay)',
            color: 'var(--accent-teal)',
            border: '1px solid rgba(45, 212, 191, 0.2)',
            fontFamily: 'var(--font-mono)',
          }}
        >
          Question {questionNumber} of {totalQuestions}
        </span>
      </div>

      <div
        style={{
          height: '4px',
          borderRadius: '2px',
          background: 'var(--bg-overlay)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${progressPercent}%`,
            background: 'var(--accent-teal)',
            transition: 'width 0.3s ease',
          }}
        />
      </div>

      {currentQuestion && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          <p style={{ fontSize: '17px', color: 'var(--text-primary)', lineHeight: 1.6 }}>
            {currentQuestion.question}
          </p>

          <div style={{ display: 'grid', gap: 'var(--space-3)' }}>
            {currentQuestion.options.map((opt, idx) => {
              const isSelected = selectedOption === opt;
              const letter = String.fromCharCode(65 + idx);
              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => !submitting && setSelectedOption(opt)}
                  disabled={submitting}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    padding: 'var(--space-4)',
                    borderRadius: 'var(--r-md)',
                    border: isSelected
                      ? '1px solid var(--accent-teal)'
                      : '1px solid var(--border-default)',
                    background: isSelected ? 'var(--accent-teal-dim, rgba(45,212,191,0.1))' : 'var(--bg-overlay)',
                    color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
                    cursor: submitting ? 'not-allowed' : 'pointer',
                    opacity: submitting ? 0.6 : 1,
                    transition: 'all 0.15s',
                    display: 'flex',
                    gap: 'var(--space-3)',
                    alignItems: 'flex-start',
                  }}
                >
                  <span
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '12px',
                      color: isSelected ? 'var(--accent-teal)' : 'var(--text-muted)',
                      minWidth: '18px',
                    }}
                  >
                    {letter})
                  </span>
                  <span>{opt}</span>
                </button>
              );
            })}
          </div>

          <button
            type="button"
            onClick={handleSubmitAnswer}
            disabled={!selectedOption || submitting}
            className="btn btn-primary"
            style={{
              alignSelf: 'flex-end',
              minWidth: '120px',
              opacity: !selectedOption || submitting ? 0.5 : 1,
            }}
          >
            {submitting ? 'Submitting...' : 'Next'}
          </button>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 'var(--space-2)' }}>
        <button
          type="button"
          onClick={onSkip}
          style={{
            fontSize: '12px',
            color: 'var(--text-tertiary, var(--text-muted))',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
          }}
        >
          Skip diagnostic (default abilities will be used)
        </button>
      </div>
    </div>
  );
}
