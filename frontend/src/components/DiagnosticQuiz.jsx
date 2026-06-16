import React, { useState, useEffect } from 'react';

export default function DiagnosticQuiz({ onComplete, onSkip, subject = "Physics" }) {
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [responses, setResponses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    startDiagnostic();
  }, []);

  const startDiagnostic = async () => {
    try {
      const res = await fetch('/api/diagnostic/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subject })
      });
      const data = await res.json();
      if (data.item) {
        setCurrentQuestion(data.item);
      } else {
        onSkip(); // Fallback if no questions
      }
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const handleAnswer = async (selectedOption) => {
    if (!currentQuestion) return;
    
    setLoading(true);
    const isCorrect = selectedOption === currentQuestion.answer ? 1 : 0;
    
    const newResponses = [
      ...responses, 
      { item_id: currentQuestion.item_id, is_correct: isCorrect }
    ];
    
    setResponses(newResponses);

    try {
      const res = await fetch('/api/diagnostic/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ responses: newResponses, subject })
      });
      const data = await res.json();
      
      if (data.complete || !data.item) {
        onComplete(data.theta || 0.0);
      } else {
        setCurrentQuestion(data.item);
        setLoading(false);
      }
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  if (loading && !currentQuestion) return <div className="text-center p-8 text-text-secondary">Loading diagnostic...</div>;
  if (error) return <div className="text-center p-8 text-accent-rose">Error: {error}</div>;

  return (
    <div className="w-full max-w-2xl mx-auto p-6 bg-bg-card rounded-2xl border border-border-default">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-xl font-bold text-text-primary">Diagnostic Assessment</h3>
        <span className="text-sm font-medium px-3 py-1 rounded-full bg-bg-overlay text-accent-teal border border-accent-teal/20">
          Question {responses.length + 1}
        </span>
      </div>
      
      {currentQuestion && (
        <div className="space-y-6">
          <p className="text-lg text-text-primary leading-relaxed">
            {currentQuestion.question}
          </p>
          
          <div className="grid gap-3">
            {currentQuestion.options.map((opt, idx) => (
              <button
                key={idx}
                onClick={() => handleAnswer(opt)}
                disabled={loading}
                className="w-full text-left p-4 rounded-xl border border-border-default bg-bg-overlay hover:bg-border-default hover:border-accent-teal/50 transition-all text-text-secondary hover:text-text-primary disabled:opacity-50"
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      )}
      
      <div className="mt-8 flex justify-center">
        <button 
          onClick={onSkip}
          className="text-sm text-text-tertiary hover:text-text-secondary transition-colors"
        >
          Skip diagnostic (Default abilities will be used)
        </button>
      </div>
    </div>
  );
}
