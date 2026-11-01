import mongoose from 'mongoose';
import {createApp} from './app.js';
import {models} from './models.js';
import {python} from './python.js';

if (!process.env.MONGO_URI) {
  throw new Error('Set MONGO_URI in your environment configuration');
}

// In academic demonstration mode, ADMIN_TOKEN and VIEWER_TOKEN are not required.
process.env.DEMO_MODE = process.env.DEMO_MODE || 'true';

await mongoose.connect(process.env.MONGO_URI, {
  dbName: process.env.MONGO_DB || 'ess_sentinel',
  serverSelectionTimeoutMS: 5000
});

await Promise.all(Object.values(models).map(m => m.init()));

// Auto-seed demo dataset if database has no batches (evaluator friendly first run)
try {
  const batchCount = await models.batches.countDocuments();
  if (batchCount === 0) {
    console.log('No batches found. Initializing demonstration workspace...');
    await python('seed');
    console.log('Demonstration workspace successfully initialized.');
  }
} catch (err) {
  console.warn('Initial demo seed check note:', err.message);
}

const server = createApp().listen(process.env.PORT || 3001, () => {
  console.log(`ESS Sentinel Web 3.0 API listening on port ${process.env.PORT || 3001} (DEMO_MODE=${process.env.DEMO_MODE})`);
});

process.on('SIGTERM', () => server.close(async () => {
  await mongoose.disconnect();
  process.exit(0);
}));
