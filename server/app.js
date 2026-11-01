import express from 'express';
import helmet from 'helmet';
import cors from 'cors';
import rateLimit from 'express-rate-limit';
import multer from 'multer';
import mongoose from 'mongoose';
import crypto from 'node:crypto';
import path from 'node:path';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {z} from 'zod';
import {models as M} from './models.js';
import {python} from './python.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const id = z.string().regex(/^[a-f0-9]{24}$/i);
const name = z.string().trim().min(1).max(120);

function parseJSON(s) {
  try {
    return JSON.parse(s);
  } catch {
    throw Object.assign(new Error('Mapping and unit fields must contain valid JSON'), {status: 400});
  }
}

export function createApp(run = python) {
  const app = express();
  app.disable('x-powered-by');
  app.use(helmet());
  app.use(cors({origin: process.env.CLIENT_ORIGIN || true}));
  app.use(express.json({limit: '2mb'}));
  app.use('/api', rateLimit({windowMs: 60000, limit: 600}));

  app.use((req, res, next) => {
    req.requestId = crypto.randomUUID();
    res.setHeader('X-Request-ID', req.requestId);
    res.on('finish', () => {
      console.log(JSON.stringify({id: req.requestId, method: req.method, path: req.path, status: res.statusCode}));
    });
    next();
  });

  const equal = (a, b) => {
    const x = Buffer.from(a || ''), y = Buffer.from(b || '');
    return y.length > 0 && x.length === y.length && crypto.timingSafeEqual(x, y);
  };

  // Health check endpoint
  app.get('/api/health', async (req, res) => {
    const dbReady = mongoose.connection.readyState === 1;
    res.status(dbReady ? 200 : 503).json({
      status: dbReady ? 'ready' : 'database unavailable',
      version: '3.0.0',
      demoMode: process.env.DEMO_MODE !== 'false'
    });
  });

  // Authentication & Demo Mode Middleware
  app.use('/api', (req, res, next) => {
    const isDemoMode = process.env.DEMO_MODE === 'true' || (!process.env.ADMIN_TOKEN && process.env.DEMO_MODE !== 'false');
    if (isDemoMode) {
      // In academic demo mode, automatically grant operator privileges without tokens
      req.role = 'admin';
      return next();
    }

    // Secured enterprise mode (when DEMO_MODE=false and ADMIN_TOKEN is configured)
    const token = req.get('authorization')?.replace(/^Bearer /, '');
    req.role = equal(token, process.env.ADMIN_TOKEN) ? 'admin' : equal(token, process.env.VIEWER_TOKEN) ? 'viewer' : null;
    if (!req.role) {
      return res.status(401).json({error: {message: 'Sign in with an operator or viewer token'}});
    }
    next();
  });

  const admin = (req, res, next) => {
    if (req.role === 'admin') return next();
    return res.status(403).json({error: {message: 'Operator role required'}});
  };

  // Cached context for ultra-fast page transitions
  let contextCache = null;
  let contextCacheTime = 0;
  const CONTEXT_CACHE_TTL = 3000;

  app.get('/api/context', async (req, res) => {
    const targetBatchId = req.query.batchId ? id.parse(req.query.batchId) : null;
    const now = Date.now();
    if (!targetBatchId && contextCache && (now - contextCacheTime < CONTEXT_CACHE_TTL)) {
      return res.json(contextCache);
    }
    const result = await run('context', targetBatchId ? {batchId: targetBatchId} : {});
    if (!targetBatchId) {
      contextCache = result;
      contextCacheTime = now;
    }
    res.json(result);
  });

  // Dedicated fast overview endpoint (pre-aggregated metrics)
  app.get('/api/overview', async (req, res) => {
    const targetBatchId = req.query.batchId ? id.parse(req.query.batchId) : null;
    const result = await run('overview', targetBatchId ? {batchId: targetBatchId} : {});
    res.json(result);
  });

  const resources = {
    'batches': 'batches',
    'screening-runs': 'runs',
    'reviews': 'reviews',
    'models': 'models',
    'policies': 'policies',
    'scenarios': 'scenarios',
    'reports': 'reports',
    'audit-events': 'events'
  };

  for (const [route, col] of Object.entries(resources)) {
    app.get('/api/' + route, async (req, res) => {
      const page = z.coerce.number().int().min(1).default(1).parse(req.query.page);
      const limit = z.coerce.number().int().min(1).max(100).default(25).parse(req.query.limit);
      const filter = {};

      if (req.query.batchId && col === 'runs') filter.batch_id = id.parse(req.query.batchId);
      if (req.query.runId && col === 'reviews') filter.run_id = id.parse(req.query.runId);
      if (req.query.componentId && col === 'reviews') filter.component_id = z.string().max(200).parse(req.query.componentId);
      if (req.query.source && col === 'batches') filter.source = z.enum(['IMPORTED', 'SYNTHETIC']).parse(req.query.source);
      if (req.query.search && col === 'batches') {
        filter.name = {$regex: z.string().max(100).parse(req.query.search).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), $options: 'i'};
      }

      const sort = req.query.sort === 'oldest' ? 1 : -1;
      const sortField = col === 'events' ? 'timestamp' : 'created';

      const [items, total] = await Promise.all([
        M[col].find(filter).sort({[sortField]: sort, _id: sort}).skip((page - 1) * limit).limit(limit).lean(),
        M[col].countDocuments(filter)
      ]);

      res.json({items, total, page, limit});
    });

    app.get('/api/' + route + '/:id', async (req, res) => {
      const row = await M[col].findById(id.parse(req.params.id)).lean();
      if (!row) return res.status(404).json({error: {message: 'Record not found'}});
      res.json(row);
    });
  }

  app.patch('/api/batches/:id', admin, async (req, res) => {
    const patch = z.object({name: name.optional(), archived: z.boolean().optional()}).strict().parse(req.body);
    if (!Object.keys(patch).length) throw Object.assign(new Error('No fields provided'), {status: 400});
    const row = await M.batches.findByIdAndUpdate(id.parse(req.params.id), {$set: patch}, {new: true, runValidators: true});
    if (!row) return res.status(404).json({error: {message: 'Batch not found'}});
    await M.events.create({timestamp: new Date().toISOString(), action: 'batch_updated', batch_id: row._id, details: patch, outcome: 'success'});
    contextCache = null;
    res.json(row);
  });

  app.delete('/api/batches/:id', admin, async (req, res) => {
    const bid = id.parse(req.params.id);
    const isDemoMode = process.env.DEMO_MODE === 'true';
    if (isDemoMode) {
      return res.status(403).json({error: {message: 'Batch deletion is disabled in public demonstration mode. Archive this batch instead.'}});
    }
    if (await M.runs.exists({batch_id: bid}) || await M.scenarios.exists({$or: [{batch_id: bid}, {baseline_batch: bid}]})) {
      return res.status(409).json({error: {message: 'Historical references exist. Archive this batch instead.'}});
    }
    if (!await M.batches.findByIdAndDelete(bid)) return res.status(404).json({error: {message: 'Batch not found'}});
    await M.settings.deleteOne({key: 'active_batch', value: bid});
    await M.events.create({timestamp: new Date().toISOString(), action: 'batch_deleted', batch_id: bid, outcome: 'success', details: {artifactsRetained: true}});
    contextCache = null;
    res.status(204).end();
  });

  const upload = multer({storage: multer.memoryStorage(), limits: {fileSize: 25 * 1024 * 1024, files: 1, fields: 5}});
  
  app.post('/api/batches', admin, upload.single('file'), async (req, res) => {
    if (!req.file || !/\.(csv|xlsx)$/i.test(req.file.originalname)) {
      throw Object.assign(new Error('Upload a CSV or XLSX file'), {status: 400});
    }
    const mapping = z.record(z.string(), z.string()).parse(parseJSON(req.body.mapping || '{}'));
    const units = z.record(z.string(), z.string().max(40)).parse(parseJSON(req.body.units || '{}'));
    contextCache = null;
    res.status(req.body.commit === 'true' ? 201 : 200).json(
      await run('import', {
        content: req.file.buffer.toString('base64'),
        filename: req.file.originalname,
        name: name.parse(req.body.name || 'Imported batch'),
        mapping,
        units,
        commit: req.body.commit === 'true'
      })
    );
  });

  const readOps = {
    'quality': z.object({batchId: id}),
    'measurements': z.object({batchId: id}),
    'results': z.object({runId: id}),
    'model': z.object({modelId: id}),
    'predict': z.object({batchId: id, modelId: id}),
    'evaluate': z.object({runId: id}),
    'diagnostics': z.object({}),
    'smoke': z.object({})
  };

  const writeOps = {
    seed: z.object({}),
    screen: z.object({batchId: id, stage: z.union([z.literal(24), z.literal(96), z.literal(168)]).default(24), statisticsOnly: z.boolean().default(false)}),
    train: z.object({batchId: id, options: z.object({cutoff: z.union([z.literal(24), z.literal(96)]), seed: z.number().int().min(0).max(2147483647), trees: z.number().int().min(20).max(300), boosting_stages: z.number().int().min(20).max(300), candidate_names: z.array(z.enum(['Linear', 'Ridge-1', 'Ridge-10', 'RandomForest', 'GradientBoosting-2', 'GradientBoosting-3'])).min(1).optional()})}),
    activate: z.object({modelId: id}),
    simulate: z.object({name: z.enum(['Normal Lot', 'Obvious Failure', 'Latent Defect', 'Early Warning', 'Population Anomaly', 'Missing measurements', 'Mixed-quality population', 'Elevated measurement variation']), seed: z.number().int().min(0).max(2147483647).default(42), n: z.number().int().min(100).max(100000).default(600), lots: z.number().int().min(1).max(100).default(12), noise: z.number().min(0).max(.2).default(.015), severity: z.number().min(.2).max(2).default(1), defect_fraction: z.number().min(0).max(.5).default(.15)}),
    policy: z.object({config: z.record(z.string(), z.number().finite()), save: z.boolean().default(false), batchId: id.optional()}),
    review: z.object({runId: id, componentId: z.string().min(1).max(200), state: z.enum(['Unreviewed', 'In review', 'Reviewed']), note: z.string().max(2000)}),
    settings: z.object({name: name}),
    reset: z.object({}),
    backup: z.object({}),
    report: z.object({kind: z.enum(['batch', 'component', 'quality', 'evaluation', 'audit', 'scenario']), runId: id.optional(), batchId: id.optional(), modelId: id.optional(), componentId: z.string().max(200).optional()})
  };

  for (const [op, schema] of Object.entries({...readOps, ...writeOps})) {
    app.post('/api/actions/' + op, ...(writeOps[op] ? [admin] : []), async (req, res) => {
      const args = schema.strict().parse(req.body);
      for (const [key, col] of [['batchId', 'batches'], ['runId', 'runs'], ['modelId', 'models']]) {
        if (args[key] && !await M[col].exists({_id: args[key]})) {
          return res.status(404).json({error: {message: key + ' not found'}});
        }
      }
      contextCache = null;
      res.json(await run(op, args));
    });
  }

  app.get('/api/components', async (req, res) => {
    const rows = await run('measurements', {batchId: id.parse(req.query.batchId)});
    const search = z.string().max(100).default('').parse(req.query.search).toLowerCase();
    const filtered = rows.filter(r => r.component_id.toLowerCase().includes(search));
    const page = z.coerce.number().int().min(1).default(1).parse(req.query.page);
    res.json({items: filtered.slice((page - 1) * 100, page * 100), total: filtered.length, page, limit: 100});
  });

  // Durable report download streaming from MongoDB GridFS
  app.get('/api/reports/:id/download/:ext', async (req, res, next) => {
    try {
      const rid = id.parse(req.params.id);
      const ext = z.enum(['pdf', 'xlsx', 'csv', 'zip']).parse(req.params.ext);
      const r = await M.reports.findById(rid);
      if (!r) return res.status(404).json({error: {message: 'Report not found'}});
      if ((ext === 'zip') !== (r.kind === 'backup')) {
        return res.status(400).json({error: {message: 'Invalid report format'}});
      }

      const filename = ext === 'zip' ? 'backup.zip' : 'report.' + ext;
      const downloadName = `ess-${r.kind}.${ext}`;
      const mimeTypes = {
        pdf: 'application/pdf',
        xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        csv: 'text/csv; charset=utf-8',
        zip: 'application/zip'
      };

      // 1. Try streaming from MongoDB GridFS
      if (mongoose.connection?.db) {
        const bucket = new mongoose.mongo.GridFSBucket(mongoose.connection.db);
        const files = await mongoose.connection.db.collection('fs.files').find({
          $or: [
            {'metadata.category': 'reports', 'metadata.identifier': rid, 'metadata.filename': filename},
            {filename: `reports/${rid}/${filename}`},
            {filename: filename, 'metadata.identifier': rid}
          ]
        }).sort({uploadDate: -1}).limit(1).toArray();

        if (files.length > 0) {
          const fileDoc = files[0];
          res.setHeader('Content-Type', fileDoc.metadata?.content_type || mimeTypes[ext] || 'application/octet-stream');
          res.setHeader('Content-Disposition', `attachment; filename="${downloadName}"`);
          if (fileDoc.length) {
            res.setHeader('Content-Length', fileDoc.length);
          }
          const stream = bucket.openDownloadStream(fileDoc._id);
          stream.on('error', (err) => {
            if (!res.headersSent) res.status(500).json({error: {message: 'Failed to stream report artifact'}});
          });
          return stream.pipe(res);
        }
      }

      // 2. Fallback to local filesystem if file exists locally
      const localPath = path.join(process.env.ARTIFACT_DIR || path.join(root, 'var/artifacts'), 'reports', rid, filename);
      try {
        await fs.access(localPath);
        return res.download(localPath, downloadName);
      } catch {
        return res.status(404).json({error: {message: 'Report artifact not found in persistent storage'}});
      }
    } catch (err) {
      next(err);
    }
  });

  app.get('/api/openapi.json', (req, res) => res.json({
    openapi: '3.0.3',
    info: {title: 'ESS Sentinel Web', version: '3.0.0'},
    components: {securitySchemes: {bearerAuth: {type: 'http', scheme: 'bearer'}}},
    security: [{bearerAuth: []}],
    paths: Object.fromEntries([
      ...Object.keys(resources).map(r => ['/api/' + r, {get: {summary: 'Paginated ' + r, responses: {200: {description: 'items, total, page, limit'}}}}]),
      ...Object.keys({...readOps, ...writeOps}).map(op => ['/api/actions/' + op, {post: {summary: op, responses: {200: {description: 'Computed result'}, 422: {description: 'Invalid input'}}}}])
    ])
  }));

  app.use('/api', (req, res) => res.status(404).json({error: {message: 'Endpoint not found'}}));

  app.use(express.static(path.join(root, 'client/dist')));
  app.get('/{*path}', (req, res) => res.sendFile(path.join(root, 'client/dist/index.html')));

  app.use((err, req, res, next) => {
    req.requestId = req.requestId || crypto.randomUUID();
    const status = err instanceof z.ZodError ? 400 : err.code === 'LIMIT_FILE_SIZE' ? 413 : err.status || (/Mongo|Mongoose/.test(err.name) ? 503 : 500);
    res.status(status).json({
      error: {
        message: err instanceof z.ZodError ? err.issues.map(i => i.path.join('.') + ': ' + i.message).join('; ') : status === 500 ? 'Internal error; check service configuration' : err.message,
        requestId: req.requestId
      }
    });
  });

  return app;
}
