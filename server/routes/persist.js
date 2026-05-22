import express from 'express';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const router = express.Router();
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '../../data/user');

// Ensure data directory exists
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

const ALLOWED_FILES = [
  'profile.json',
  'session.json',
  'history.json',
  'analytics.json',
  'prompt_context.json'
];

router.post('/persist', async (req, res) => {
  try {
    const { filename, payload } = req.body;

    if (!filename || !payload) {
      return res.status(400).json({ error: 'Missing filename or payload' });
    }

    if (!ALLOWED_FILES.includes(filename)) {
      return res.status(400).json({ error: `Unauthorized file write: ${filename}` });
    }

    const filePath = path.join(DATA_DIR, filename);
    const tempPath = `${filePath}.tmp`;

    // Perform atomic write: write to temp file then rename
    fs.writeFileSync(tempPath, JSON.stringify(payload, null, 2), 'utf8');
    fs.renameSync(tempPath, filePath);

    // Also auto-generate prompt_context.json if profile or analytics updates
    if (filename === 'profile.json' || filename === 'analytics.json') {
      try {
        await generatePromptContext();
      } catch (err) {
        console.error('Failed to regenerate prompt_context.json:', err);
      }
    }

    return res.status(200).json({ success: true, message: `Successfully persisted ${filename}` });
  } catch (error) {
    console.error('Error persisting data:', error);
    return res.status(500).json({ error: 'Failed to write data file', details: error.message });
  }
});

// Helper function to read a user data file safely
router.get('/load/:filename', (req, res) => {
  const { filename } = req.params;

  if (!ALLOWED_FILES.includes(filename)) {
    return res.status(400).json({ error: `Unauthorized file read: ${filename}` });
  }

  const filePath = path.join(DATA_DIR, filename);

  if (!fs.existsSync(filePath)) {
    // Return appropriate default empty objects/arrays instead of 404 to avoid frontend errors
    let defaultVal = {};
    if (filename === 'history.json') defaultVal = { sessions: [] };
    else if (filename === 'analytics.json') defaultVal = { total_sessions: 0, total_watch_time_seconds: 0, topics_covered: [], weak_topic_flags: [], daily_activity: [], subject_distribution: {} };
    return res.status(200).json(defaultVal);
  }

  try {
    const content = fs.readFileSync(filePath, 'utf8');
    return res.status(200).json(JSON.parse(content));
  } catch (err) {
    return res.status(500).json({ error: 'Failed to read file', details: err.message });
  }
});

// Helper to auto-generate prompt_context.json
async function generatePromptContext() {
  const profilePath = path.join(DATA_DIR, 'profile.json');
  const analyticsPath = path.join(DATA_DIR, 'analytics.json');
  const contextPath = path.join(DATA_DIR, 'prompt_context.json');

  let profile = {};
  let analytics = {};

  if (fs.existsSync(profilePath)) {
    try { profile = JSON.parse(fs.readFileSync(profilePath, 'utf8')); } catch(e){}
  }
  if (fs.existsSync(analyticsPath)) {
    try { analytics = JSON.parse(fs.readFileSync(analyticsPath, 'utf8')); } catch(e){}
  }

  const recentTopics = analytics.topics_covered ? analytics.topics_covered.slice(-5) : [];
  const currentWeakAreas = analytics.weak_topic_flags || [];

  const name = profile.name || 'Learner';
  const level = profile.academic_level || 'class_11';
  const style = profile.learning_style || 'visual';
  const pace = profile.pace_preference || 'balanced';

  // Generate a friendly prose summary of the learner
  const summary = `${name} is an academic student studying at the ${level} level, preparing for targets like ${profile.exam_target?.join(', ') || 'exams'}. They prefer a ${style} learning style at a ${pace} pace.`;

  let styleInstructions = '';
  if (style === 'visual') {
    styleInstructions = 'Emphasize intuitive animations, shapes, coordinate grids, and visual analogies. Avoid listing long formulas first; instead, build the shape of the equation.';
  } else if (style === 'conceptual') {
    styleInstructions = 'Focus on the "why" and core definitions. Build concepts from historical context or first principles before giving numerical examples.';
  } else if (style === 'example_first') {
    styleInstructions = 'Begin with a highly grounded everyday numerical example, then generalize the math and build the formal definition from there.';
  } else if (style === 'equation_first') {
    styleInstructions = 'Present the core equations clearly at the beginning, break down each term, and then derive or explain its physical implications.';
  }

  const promptContext = {
    learner_summary: summary,
    style_instructions: styleInstructions,
    recent_topics: recentTopics,
    current_weak_areas: currentWeakAreas,
    generated_at: new Date().toISOString()
  };

  const tempPath = `${contextPath}.tmp`;
  fs.writeFileSync(tempPath, JSON.stringify(promptContext, null, 2), 'utf8');
  fs.renameSync(tempPath, contextPath);
}

export default router;
