import express from 'express';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const router = express.Router();
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '../../data/user');

// Helper to write file atomically
function writeAtomic(filePath, data) {
  const tempPath = `${filePath}.tmp`;
  fs.writeFileSync(tempPath, JSON.stringify(data, null, 2), 'utf8');
  fs.renameSync(tempPath, filePath);
}

// Active connections for SSE status tracking
let activeStreams = new Set();

router.post('/pipeline/run', (req, res) => {
  const { topic, subject } = req.body;

  if (!topic) {
    return res.status(400).json({ error: 'Missing topic' });
  }

  const sessionId = `session-${Date.now()}`;
  const resolvedTopic = `${topic} — Chapter ${Math.floor(Math.random() * 10) + 1}`;

  // Start the background generation simulation
  startPipelineSimulation(sessionId, topic, resolvedTopic, subject || 'General');

  return res.status(200).json({
    success: true,
    message: 'Pipeline started successfully',
    sessionId,
    resolvedTopic
  });
});

// SSE endpoint to stream pipeline events
router.get('/pipeline/status/:sessionId', (req, res) => {
  const { sessionId } = req.params;

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders(); // Tell client headers are sent

  const streamObj = { sessionId, res };
  activeStreams.add(streamObj);

  req.on('close', () => {
    activeStreams.delete(streamObj);
  });
});

// Simulate pipeline executing in the background and sending SSE events
async function startPipelineSimulation(sessionId, rawQuery, resolvedTopic, subject) {
  const sendEvent = (stage, progress, message, data = null) => {
    const eventPayload = JSON.stringify({ sessionId, stage, progress, message, data });
    for (const stream of activeStreams) {
      if (stream.sessionId === sessionId) {
        stream.res.write(`data: ${eventPayload}\n\n`);
      }
    }
  };

  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

  try {
    // 1. Retrieving (800ms)
    sendEvent('retrieving', 10, 'Searching textbook structure.json and summaries...');
    await sleep(800);

    // 2. Explaining (2400ms)
    sendEvent('explaining', 30, 'Generating learning objectives and core explanations with Gemini...');
    await sleep(2400);

    const explanationPackage = {
      topic: resolvedTopic,
      learning_objectives: [
        `Understand the fundamental principles of ${rawQuery}`,
        `Apply core formulas of ${rawQuery} to solve basic problems`,
        `Explore real-world analogies regarding ${rawQuery}`
      ],
      core_explanation: `${rawQuery} represents a key physical phenomenon where system interactions establish thermodynamic, mechanical, or chemical equilibriums. To grasp this, let's look at the basic equations that define it...`,
      analogies: [
        `Think of ${rawQuery} like a tug-of-war where both sides pull with equal strength, maintaining absolute stillness while experiencing high tension.`,
        `It is like two escalator tracks moving at identical speeds in opposite directions, keeping a walking person perfectly in place.`
      ],
      visual_elements: ['Vector lines representing balance', 'Highlighted mathematical equalities', 'Glow animations for peak stress points'],
      difficulty: 'Medium',
      prerequisites: [`Introduction to basic algebra`, `Fundamental mechanics`]
    };
    sendEvent('explaining', 40, 'Explanation formulated.', explanationPackage);

    // 3. Planning (3100ms)
    sendEvent('planning', 50, 'Formulating visual storyboard and Manim scene graph...');
    await sleep(3100);

    const scenePlan = [
      {
        scene_number: 1,
        title: 'Conceptual Introduction',
        description: `Visualizes the base representation of ${rawQuery} using floating particles and scale vector axes.`,
        duration_seconds: 7.5
      },
      {
        scene_number: 2,
        title: 'Mathematical Breakdown',
        description: `Derives key state equations step-by-step using highlighted equations zooming into focus.`,
        duration_seconds: 12.0
      },
      {
        scene_number: 3,
        title: 'Analogy Demonstration',
        description: `Visualizes a dynamic model of a balance scale adjusting in real-time, showing visual equilibrium.`,
        duration_seconds: 9.2
      }
    ];
    sendEvent('planning', 60, 'Visual storyboard planned.', scenePlan);

    // 4. Generating (10000ms)
    sendEvent('generating', 70, 'Compiling Python scripts and executing Manim rendering engine...');
    await sleep(10000);
    const mockPythonScript = `from manim import *

class LearnOSScene(Scene):
    def construct(self):
        # Title slide
        title = Text("${rawQuery} in action", font_size=40, color=GOLD)
        self.play(Write(title))
        self.wait(2)
        
        # Grid layout representation
        grid = NumberPlane()
        self.play(Create(grid))
        
        # Interactive vector arrows
        arrow = Arrow(start=LEFT*2, end=RIGHT*2, color=BLUE)
        self.play(GrowArrow(arrow))
        self.wait(3)
`;
    sendEvent('generating', 80, 'Manim rendering complete.', { script: mockPythonScript });

    // 5. Narrating (2000ms)
    sendEvent('narrating', 85, 'Assembling voiceover timelines and syncing frames...');
    await sleep(2000);

    // 6. TTS (4000ms)
    sendEvent('tts', 95, 'Synthesizing voice narration using Piper TTS engine...');
    await sleep(4000);

    const narrationPackage = {
      transcript: `Welcome to this LearnOS module on ${rawQuery}. Today we will discover how this beautiful concept balances forces in our universe. Let's start by looking at a coordinate grid. As you can see, equal arrows pull in opposite directions, creating absolute harmony.`,
      words: [
        { word: 'Welcome', start: 0, end: 0.5 },
        { word: 'to', start: 0.5, end: 0.8 },
        { word: 'this', start: 0.8, end: 1.1 },
        { word: 'LearnOS', start: 1.1, end: 1.6 },
        { word: 'module', start: 1.6, end: 2.1 },
        { word: 'on', start: 2.1, end: 2.3 },
        { word: rawQuery, start: 2.3, end: 3.2 }
      ]
    };

    // Complete (Finished!)
    const duration = 28.7;
    const finalVideoPath = `/generated/${sessionId}/output.mp4`;

    // Persist final session data
    const sessionFile = path.join(DATA_DIR, 'session.json');
    const historyFile = path.join(DATA_DIR, 'history.json');
    const analyticsFile = path.join(DATA_DIR, 'analytics.json');

    const sessionPayload = {
      session_id: sessionId,
      topic_query: rawQuery,
      topic_resolved: resolvedTopic,
      pipeline_stage: 'complete',
      messages: [
        { role: 'user', content: `Explain ${rawQuery}`, timestamp: new Date().toISOString() },
        { role: 'assistant', content: `Here is your fully animated lesson for **${resolvedTopic}**!`, timestamp: new Date().toISOString() }
      ],
      video_url: finalVideoPath,
      explanation_package: explanationPackage,
      scene_plan: scenePlan,
      notes: `# Learning Notes: ${resolvedTopic}\n\n- Core concept: ...\n- Analogy: Balance of opposite vectors.\n`
    };

    writeAtomic(sessionFile, sessionPayload);

    // Update history.json
    let history = { sessions: [] };
    if (fs.existsSync(historyFile)) {
      try { history = JSON.parse(fs.readFileSync(historyFile, 'utf8')); } catch(e){}
    }
    history.sessions.unshift({
      session_id: sessionId,
      topic: resolvedTopic,
      subject: subject,
      duration_seconds: Math.floor(duration),
      completed_at: new Date().toISOString(),
      video_path: finalVideoPath,
      follow_up_count: 0
    });
    writeAtomic(historyFile, history);

    // Update analytics.json
    let analytics = {
      total_sessions: 0,
      total_watch_time_seconds: 0,
      topics_covered: [],
      weak_topic_flags: [],
      daily_activity: [],
      subject_distribution: {}
    };
    if (fs.existsSync(analyticsFile)) {
      try { analytics = JSON.parse(fs.readFileSync(analyticsFile, 'utf8')); } catch(e){}
    }

    analytics.total_sessions += 1;
    analytics.total_watch_time_seconds += Math.floor(duration);
    if (!analytics.topics_covered.includes(resolvedTopic)) {
      analytics.topics_covered.push(resolvedTopic);
    }
    analytics.subject_distribution[subject] = (analytics.subject_distribution[subject] || 0) + 1;

    // Heatmap update
    const todayStr = new Date().toISOString().split('T')[0];
    let todayActivity = analytics.daily_activity.find(d => d.date === todayStr);
    if (todayActivity) {
      todayActivity.minutes += Math.ceil(duration / 60);
      todayActivity.sessions += 1;
    } else {
      analytics.daily_activity.push({
        date: todayStr,
        minutes: Math.ceil(duration / 60),
        sessions: 1
      });
    }
    writeAtomic(analyticsFile, analytics);

    sendEvent('complete', 100, 'All files synchronized. Visual workspace loaded.', {
      video_url: finalVideoPath,
      narration_package: narrationPackage,
      explanation_package: explanationPackage,
      scene_plan: scenePlan,
      script: mockPythonScript
    });

  } catch (err) {
    console.error('Pipeline error:', err);
    sendEvent('error', 0, `Execution failed: ${err.message}`);
  }
}

export default router;
