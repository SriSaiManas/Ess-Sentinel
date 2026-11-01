// Test academic demonstration mode without tokens and public-demo protections.
import {test, before, after} from 'node:test';
import assert from 'node:assert/strict';
import mongoose from 'mongoose';
import request from 'supertest';
import {MongoMemoryServer} from 'mongodb-memory-server';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';

import {createApp} from '../server/app.js';
import {models as M} from '../server/models.js';

let mongod, app, dir;

before(async () => {
  dir = await fs.mkdtemp(path.join(os.tmpdir(), 'ess-demo-test-'));
  mongod = await MongoMemoryServer.create({binary: {version: '7.0.14'}});
  process.env.MONGO_URI = mongod.getUri();
  process.env.MONGO_DB = 'ess_demo_test_' + Date.now();
  process.env.ARTIFACT_DIR = dir;
  process.env.DEMO_MODE = 'true';
  delete process.env.ADMIN_TOKEN;
  delete process.env.VIEWER_TOKEN;

  await mongoose.connect(process.env.MONGO_URI, {dbName: process.env.MONGO_DB});
  await Promise.all(Object.values(M).map(m => m.init()));

  // Mock runner for fast unit testing of demo route protections
  app = createApp(async (op, args) => {
    if (op === 'context') return {workspace: 'Academic Demo', policy: {}, batchId: null};
    if (op === 'overview') return {batchId: null, counts: {NORMAL: 10, WATCH: 2, 'HIGH RISK': 1, CRITICAL: 0}, priority: []};
    if (op === 'seed') return {batchId: '6ae602645a2d464df0eb7692'};
    return {ok: true, operation: op, args};
  });
});

after(async () => {
  if (mongoose.connection.readyState === 1) await mongoose.connection.dropDatabase();
  await mongoose.disconnect();
  await mongod?.stop();
  if (dir) await fs.rm(dir, {recursive: true, force: true});
});

test('evaluators can access API context without authentication token', async () => {
  const res = await request(app).get('/api/context').expect(200);
  assert.equal(res.body.workspace, 'Academic Demo');
});

test('evaluators can access fast overview endpoint without authentication token', async () => {
  const res = await request(app).get('/api/overview').expect(200);
  assert.equal(res.body.counts.NORMAL, 10);
});

test('evaluators can list batches, models, and policies without tokens', async () => {
  const batches = await request(app).get('/api/batches').expect(200);
  assert.ok(Array.isArray(batches.body.items));
  const models = await request(app).get('/api/models').expect(200);
  assert.ok(Array.isArray(models.body.items));
});

test('evaluators can invoke normal operations (seed, policy, diagnostics) without tokens', async () => {
  await request(app).post('/api/actions/seed').send({}).expect(200);
  await request(app).post('/api/actions/diagnostics').send({}).expect(200);
});

test('public demo mode protects database: batch deletion is blocked', async () => {
  // Create a batch document
  const batch = await M.batches.create({
    name: 'Protected Demo Batch',
    source: 'SYNTHETIC',
    created: new Date().toISOString(),
    rows: 100,
    components: 10,
    health: 98
  });

  // Attempting to delete batch in DEMO_MODE should be blocked with 403
  const res = await request(app).delete('/api/batches/' + batch._id).expect(403);
  assert.match(res.body.error.message, /Batch deletion is disabled in public demonstration mode/);

  // Batch still exists in database
  const check = await M.batches.findById(batch._id);
  assert.ok(check !== null);
});

test('evaluators can archive batches instead of deleting', async () => {
  const batch = await M.batches.create({
    name: 'Archivable Demo Batch',
    source: 'SYNTHETIC',
    created: new Date().toISOString(),
    rows: 100,
    components: 10,
    health: 98
  });

  const res = await request(app).patch('/api/batches/' + batch._id).send({archived: true}).expect(200);
  assert.equal(res.body.archived, true);
});
