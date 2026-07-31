#!/usr/bin/env node
// claude-visual-server — local HTTP daemon for /visual skill.
// Receives state from the browser (via fetch POST) and writes to ~/.claude/visual-state/.
// Binds ONLY on 127.0.0.1. Auto-shuts down after IDLE_TIMEOUT.
// Zero external deps — uses Node stdlib only.

import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';

const PORT = Number(process.env.CLAUDE_VISUAL_PORT || 7755);
const HOST = '127.0.0.1';
const STATE_DIR = path.join(os.homedir(), '.claude', 'visual-state');
const IDLE_TIMEOUT_MS = 30 * 60 * 1000;   // 30 min auto-shutdown
const MAX_BODY_SIZE = 256 * 1024;         // 256 KB plenty for decisions state
const SESSION_RE = /^[a-zA-Z0-9_-]{4,64}$/;

await fs.mkdir(STATE_DIR, { recursive: true });

let lastActivity = Date.now();

function jsonResponse(res, code, body) {
  res.writeHead(code, {
    'Content-Type': 'application/json',
    // Allow any origin — only listens on 127.0.0.1 so only local contexts reach it.
    // `file://` shows up as origin `null`, handled by '*'.
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Cache-Control': 'no-store'
  });
  res.end(JSON.stringify(body));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on('data', chunk => {
      size += chunk.length;
      if (size > MAX_BODY_SIZE) {
        reject(new Error('body-too-large'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    req.on('error', reject);
  });
}

const server = http.createServer(async (req, res) => {
  lastActivity = Date.now();
  const url = new URL(req.url, `http://${HOST}:${PORT}`);

  if (req.method === 'OPTIONS') {
    jsonResponse(res, 204, {});
    return;
  }

  // Liveness check — used by start.sh to decide whether to spawn.
  if (url.pathname === '/ping') {
    jsonResponse(res, 200, { status: 'ok', pid: process.pid, port: PORT });
    return;
  }

  // Receive state snapshot from browser.
  if (req.method === 'POST' && url.pathname === '/state') {
    let raw;
    try {
      raw = await readBody(req);
    } catch (err) {
      jsonResponse(res, 413, { error: err.message });
      return;
    }
    let payload;
    try { payload = JSON.parse(raw); }
    catch { jsonResponse(res, 400, { error: 'invalid-json' }); return; }

    const session = (payload.session || '').trim();
    if (!SESSION_RE.test(session)) {
      jsonResponse(res, 400, { error: 'invalid-session' });
      return;
    }
    const stateFile = path.join(STATE_DIR, `${session}.json`);
    const record = {
      session,
      timestamp: new Date().toISOString(),
      docTitle: payload.docTitle || null,
      state: payload.state || {}
    };
    try {
      await fs.writeFile(stateFile, JSON.stringify(record, null, 2), 'utf8');
      // Maintain a "latest" pointer so Claude can read the most recent session
      // without knowing the exact token. Contains the same record, plus a pointer
      // to the per-session file.
      const latest = { ...record, stateFile };
      await fs.writeFile(path.join(STATE_DIR, 'latest.json'), JSON.stringify(latest, null, 2), 'utf8');
      jsonResponse(res, 200, { ok: true });
    } catch (err) {
      jsonResponse(res, 500, { error: err.message });
    }
    return;
  }

  // Read state (useful for debugging or pulling a past session).
  if (req.method === 'GET' && url.pathname === '/state') {
    const session = (url.searchParams.get('session') || '').trim();
    if (!SESSION_RE.test(session)) {
      jsonResponse(res, 400, { error: 'invalid-session' });
      return;
    }
    try {
      const raw = await fs.readFile(path.join(STATE_DIR, `${session}.json`), 'utf8');
      jsonResponse(res, 200, JSON.parse(raw));
    } catch {
      jsonResponse(res, 404, { error: 'not-found' });
    }
    return;
  }

  jsonResponse(res, 404, { error: 'not-found' });
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    // Another instance already running on this port — exit silently,
    // start.sh treats this as success.
    process.exit(0);
  }
  console.error('claude-visual-server error:', err);
  process.exit(1);
});

server.listen(PORT, HOST, () => {
  console.log(`claude-visual-server pid=${process.pid} http://${HOST}:${PORT}`);
});

// Idle shutdown — every minute, check if we've been quiet for IDLE_TIMEOUT_MS.
setInterval(() => {
  if (Date.now() - lastActivity > IDLE_TIMEOUT_MS) {
    console.log('claude-visual-server: idle timeout, shutting down');
    server.close(() => process.exit(0));
  }
}, 60 * 1000).unref();

// Graceful shutdown on signals so `pkill -f visual_server` behaves nicely.
['SIGINT', 'SIGTERM'].forEach(sig => {
  process.on(sig, () => {
    console.log(`claude-visual-server: received ${sig}, closing`);
    server.close(() => process.exit(0));
  });
});
