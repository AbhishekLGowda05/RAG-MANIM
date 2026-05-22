import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

// Routes
import persistRoutes from './routes/persist.js';
import pipelineRoutes from './routes/pipeline.js';
import healthRoutes from './routes/health.js';

const app = express();
const PORT = process.env.PORT || 5000;

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.join(__dirname, '..');
const GENERATED_DIR = path.join(ROOT_DIR, 'generated');
const RESULTS_DIR = path.join(ROOT_DIR, 'results');
const DATA_DIR = path.join(ROOT_DIR, 'data/user');

// Ensure directories exist
[GENERATED_DIR, RESULTS_DIR, DATA_DIR].forEach(dir => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
});

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Serve static assets
app.use('/generated', express.static(GENERATED_DIR));
app.use('/results', express.static(RESULTS_DIR));

// Setup thin API endpoints
app.use('/api', persistRoutes);
app.use('/api', pipelineRoutes);
app.use('/api', healthRoutes);

// Fallback error handler
app.use((err, req, res, next) => {
  console.error('Express Error Handler:', err);
  res.status(500).json({ error: 'Internal Server Error', message: err.message });
});

app.listen(PORT, () => {
  console.log(`=========================================`);
  console.log(` LearnOS API Server Listening on Port ${PORT}`);
  console.log(` Workspace Directory: ${ROOT_DIR}`);
  console.log(`=========================================`);
});
