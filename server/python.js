import {spawn} from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

// Find the best Python executable
function getPythonBin() {
  if (process.env.PYTHON_BIN && process.env.PYTHON_BIN !== 'python') {
    return process.env.PYTHON_BIN;
  }
  const winVenv = path.join(root, '.venv', 'Scripts', 'python.exe');
  if (process.platform === 'win32' && fs.existsSync(winVenv)) {
    return winVenv;
  }
  const posixVenv = path.join(root, '.venv', 'bin', 'python');
  if (fs.existsSync(posixVenv)) {
    return posixVenv;
  }
  return process.env.PYTHON_BIN || 'python';
}

const HEAVY_OPERATIONS = new Set(['train', 'screen', 'simulate', 'import', 'report', 'backup', 'reset']);

let activeHeavy = 0;
const runningTaskKeys = new Set();
const waitQueue = [];
const MAX_CONCURRENT_HEAVY = 2;
const QUEUE_WAIT_TIMEOUT_MS = 15000;

function acquireSlot(operation, resourceKey) {
  const isHeavy = HEAVY_OPERATIONS.has(operation);
  
  // Prevent duplicate concurrent mutation on the exact same resource
  if (resourceKey) {
    if (runningTaskKeys.has(resourceKey)) {
      throw Object.assign(
        new Error(`An analytics task is already running for this resource (${operation}). Retry shortly.`),
        {status: 409}
      );
    }
  }

  if (!isHeavy) {
    if (resourceKey) runningTaskKeys.add(resourceKey);
    return Promise.resolve(() => {
      if (resourceKey) runningTaskKeys.delete(resourceKey);
    });
  }

  if (activeHeavy < MAX_CONCURRENT_HEAVY) {
    activeHeavy++;
    if (resourceKey) runningTaskKeys.add(resourceKey);
    return Promise.resolve(() => {
      activeHeavy--;
      if (resourceKey) runningTaskKeys.delete(resourceKey);
      processNextQueue();
    });
  }

  // Queue request briefly
  return new Promise((resolve, reject) => {
    let resolved = false;
    const timer = setTimeout(() => {
      if (resolved) return;
      resolved = true;
      const idx = waitQueue.findIndex(q => q.resolve === onSlotAvailable);
      if (idx !== -1) waitQueue.splice(idx, 1);
      reject(Object.assign(new Error('Two analytics tasks are running. Retry shortly.'), {status: 429}));
    }, QUEUE_WAIT_TIMEOUT_MS);

    function onSlotAvailable() {
      if (resolved) return;
      resolved = true;
      clearTimeout(timer);
      activeHeavy++;
      if (resourceKey) runningTaskKeys.add(resourceKey);
      resolve(() => {
        activeHeavy--;
        if (resourceKey) runningTaskKeys.delete(resourceKey);
        processNextQueue();
      });
    }

    waitQueue.push({resolve: onSlotAvailable, operation, resourceKey});
  });
}

function processNextQueue() {
  if (activeHeavy < MAX_CONCURRENT_HEAVY && waitQueue.length > 0) {
    const next = waitQueue.shift();
    if (next) next.resolve();
  }
}

export async function python(operation, args = {}) {
  const resourceKey = HEAVY_OPERATIONS.has(operation) && (args.batchId || args.runId || args.modelId)
    ? `${operation}:${args.batchId || ''}:${args.runId || ''}:${args.modelId || ''}`
    : null;

  const release = await acquireSlot(operation, resourceKey);

  try {
    return await new Promise((resolve, reject) => {
      const pythonBin = getPythonBin();
      const artifactDir = process.env.ARTIFACT_DIR || path.join(root, 'var/artifacts');
      
      const child = spawn(
        pythonBin,
        [path.join(root, 'ml-service/bridge.py')],
        {
          cwd: root,
          env: {
            ...process.env,
            ARTIFACT_DIR: artifactDir,
            OMP_NUM_THREADS: '1',
            OPENBLAS_NUM_THREADS: '1'
          },
          stdio: ['pipe', 'pipe', 'pipe']
        }
      );

      let stdout = '', stderr = '', done = false;

      const finish = (err, data) => {
        if (done) return;
        done = true;
        clearTimeout(timer);
        if (err) {
          reject(err);
        } else {
          resolve(data);
        }
      };

      const timer = setTimeout(() => {
        child.kill('SIGKILL');
        finish(Object.assign(new Error('Analytics timed out; check audit history before retrying a write.'), {status: 504}));
      }, Number(process.env.ML_TIMEOUT_MS || 300000));

      child.stdout.on('data', b => {
        stdout += b;
        if (stdout.length > 100 * 1024 * 1024) {
          child.kill();
          finish(Object.assign(new Error('Analytics response exceeds limit'), {status: 413}));
        }
      });

      child.stderr.on('data', b => {
        stderr = (stderr + b).slice(-3000);
      });

      child.on('error', () => {
        finish(Object.assign(new Error('Python runtime unavailable'), {status: 503}));
      });

      child.on('close', code => {
        try {
          if (!stdout) {
            throw Object.assign(new Error('Empty response from Python worker: ' + (stderr || `code ${code}`)), {status: 503});
          }
          const r = JSON.parse(stdout);
          if (!r.ok) {
            throw Object.assign(new Error(r.error), {status: r.type === 'ValueError' ? 422 : 503});
          }
          finish(null, r.data);
        } catch (e) {
          finish(e.status ? e : Object.assign(new Error('Python service failed; inspect runtime dependencies.'), {status: 503}));
        }
      });

      child.stdin.on('error', () => {});
      child.stdin.end(JSON.stringify({operation, args}));
    });
  } finally {
    release();
  }
}
