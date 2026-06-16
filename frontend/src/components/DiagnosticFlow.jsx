import React, { useState } from 'react';
import DiagnosticQuiz from './DiagnosticQuiz';
import ThetaResultScreen from './ThetaResultScreen';
import { useThetaProfile } from '../hooks/useThetaProfile';

const TOTAL_QUESTIONS = 7;

const STAGES = {
  PHYSICS_QUIZ: 'physics_quiz',
  PHYSICS_RESULT: 'physics_result',
  CHEMISTRY_QUIZ: 'chemistry_quiz',
  CHEMISTRY_RESULT: 'chemistry_result',
};

export default function DiagnosticFlow({ onComplete, onSkip }) {
  const { setTheta } = useThetaProfile();
  const [stage, setStage] = useState(STAGES.PHYSICS_QUIZ);
  const [screenResult, setScreenResult] = useState(null);
  const [finalThetas, setFinalThetas] = useState({ Physics: null, Chemistry: null });

  const handleQuizComplete = async (subject, payload) => {
    const { theta, correctCount } = payload;
    await setTheta(subject, theta, {
      [`${subject.toLowerCase()}_correct_count`]: correctCount,
      totalQuestionsAnswered: TOTAL_QUESTIONS,
    });

    const result = {
      subject,
      theta,
      correctCount,
      totalCount: TOTAL_QUESTIONS,
    };
    setScreenResult(result);
    setFinalThetas((prev) => ({ ...prev, [subject]: theta }));

    if (subject === 'Physics') {
      setStage(STAGES.PHYSICS_RESULT);
    } else {
      setStage(STAGES.CHEMISTRY_RESULT);
    }
  };

  const handlePhysicsContinue = () => {
    setScreenResult(null);
    setStage(STAGES.CHEMISTRY_QUIZ);
  };

  const handleChemistryContinue = () => {
    onComplete({
      Physics: finalThetas.Physics,
      Chemistry: screenResult?.theta ?? finalThetas.Chemistry,
    });
  };

  if (stage === STAGES.PHYSICS_QUIZ) {
    return (
      <DiagnosticQuiz
        subject="Physics"
        totalQuestions={TOTAL_QUESTIONS}
        onComplete={(payload) => handleQuizComplete('Physics', payload)}
        onSkip={onSkip}
      />
    );
  }

  if (stage === STAGES.PHYSICS_RESULT && screenResult) {
    return (
      <ThetaResultScreen
        subject="Physics"
        theta={screenResult.theta}
        correctCount={screenResult.correctCount}
        totalCount={screenResult.totalCount}
        onContinue={handlePhysicsContinue}
        continueLabel="Continue to Chemistry"
      />
    );
  }

  if (stage === STAGES.CHEMISTRY_QUIZ) {
    return (
      <DiagnosticQuiz
        subject="Chemistry"
        totalQuestions={TOTAL_QUESTIONS}
        onComplete={(payload) => handleQuizComplete('Chemistry', payload)}
        onSkip={onSkip}
      />
    );
  }

  if (stage === STAGES.CHEMISTRY_RESULT && screenResult) {
    return (
      <ThetaResultScreen
        subject="Chemistry"
        theta={screenResult.theta}
        correctCount={screenResult.correctCount}
        totalCount={screenResult.totalCount}
        onContinue={handleChemistryContinue}
        continueLabel="View Summary"
      />
    );
  }

  return null;
}
