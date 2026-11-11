#!/usr/bin/env node
// claude-visual-server — local HTTP daemon for /visual skill.
// Receives state from the browser (via fetch POST) and writes to ~/.claude/visual-state/.
// Binds ONLY on 127.0.0.1. Auto-shuts down after IDLE_TIMEOUT.
// Zero external deps — uses Node stdlib only.
//
// Binding to loopback does not keep the user's own browser out: any web page can
// fetch http://127.0.0.1:7755. So every request to /state must carry the secret in
// ~/.claude/visual-state/.token (header X-Visual-Token), come from an expected
// Origin/Host, and POST must be application/json (text/plain would skip the CORS
// preflight). The generated /visual page embeds the token; web pages cannot read it.

import http from 'node:http';
import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import path from 'node:path';
import os from 'node:os';

const PORT = Number(process.env.CLAUDE_VISUAL_PORT || 7755);
const HOST = '127.0.0.1';
const STATE_DIR = path.join(os.homedir(), '.claude', 'visual-state');
const TOKEN_FILE = path.join(STATE_DIR, '.token');
const TOKEN_RE = /^[0-9a-f]{64}$/;
const IDLE_TIMEOUT_MS = 30 * 60 * 1000;   // 30 min auto-shutdown
const MAX_BODY_SIZE = 256 * 1024;         // 256 KB plenty for decisions state
const SESSION_RE = /^[a-zA-Z0-9_-]{4,64}$/;
// Files that share the state dir with <session>.json. A session with one of these
// names would overwrite them (compared lowercase: macOS/Windows are case-insensitive).
const RESERVED_SESSIONS = new Set(['latest', 'config', 'licoes-clareza']);
// Origins that may talk to the daemon: the page opened from disk (`null`) and the
// daemon's own address. A request with no Origin is not a browser cross-site request.
const ALLOWED_ORIGINS = new Set(['null', `http://127.0.0.1:${PORT}`, `http://localhost:${PORT}`]);
const ALLOWED_HOSTS = new Set([`127.0.0.1:${PORT}`, `localhost:${PORT}`]);

// The state dir now holds a secret: owner only (it was created 0755 by older versions).
await fs.mkdir(STATE_DIR, { recursive: true, mode: 0o700 });
await fs.chmod(STATE_DIR, 0o700).catch(() => {});

// The token is created by start.sh / visual_page.py / here — whoever comes first.
// It is written to a private temp file (0600) and then hard-linked into place, so
// the token file never exists half-written and a concurrent creator never overwrites
// another's token (link fails with EEXIST: the first one wins). A file that is there
// but is not a valid token is corrupt: it is replaced, atomically.
async function readValidToken() {
  try {
    const t = (await fs.readFile(TOKEN_FILE, 'utf8')).trim();
    return TOKEN_RE.test(t) ? t : null;
  } catch { return null; }
}

async function loadToken() {
  for (let attempt = 0; attempt < 5; attempt++) {
    const existing = await readValidToken();
    if (existing) {
      // An older version (or a hand-made file) may have left it world-readable.
      await fs.chmod(TOKEN_FILE, 0o600).catch(() => {});
      return existing;
    }
    const fresh = crypto.randomBytes(32).toString('hex');
    const tmp = path.join(STATE_DIR, `.token.${process.pid}.${crypto.randomBytes(4).toString('hex')}`);
    try {
      await fs.writeFile(tmp, fresh + '\n', { mode: 0o600, flag: 'wx' });
      try {
        await fs.link(tmp, TOKEN_FILE);
        return fresh;
      } catch (err) {
        if (err.code !== 'EEXIST') {
          // No hard links here (some Windows/exFAT volumes): create it in place, exclusively.
          await fs.writeFile(TOKEN_FILE, fresh + '\n', { mode: 0o600, flag: 'wx' });
          return fresh;
        }
        // Lost the race, or the file there is corrupt. Valid → next loop reads it.
        if (!(await readValidToken())) {
          await fs.rename(tmp, TOKEN_FILE);   // replaces the corrupt file atomically
          return fresh;
        }
      }
    } finally {
      await fs.rm(tmp, { force: true }).catch(() => {});
    }
  }
  throw new Error('could not create the token file');
}
const TOKEN = await loadToken();
const TOKEN_BUF = Buffer.from(TOKEN);

function tokenOk(req) {
  const given = req.headers['x-visual-token'];
  if (typeof given !== 'string') return false;
  const buf = Buffer.from(given);
  return buf.length === TOKEN_BUF.length && crypto.timingSafeEqual(buf, TOKEN_BUF);
}

let lastActivity = Date.now();

function corsHeaders(req) {
  // Only echo an origin that was already accepted; never `*`.
  const origin = req.headers.origin;
  if (typeof origin !== 'string') return {};
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-Visual-Token',
    'Access-Control-Max-Age': '600',
    'Vary': 'Origin'
  };
}

function jsonResponse(res, code, body, extra = {}) {
  res.writeHead(code, {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-store',
    ...extra
  });
  res.end(code === 204 ? undefined : JSON.stringify(body));
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

function isPlainObject(v) {
  return v !== null && typeof v === 'object' && !Array.isArray(v);
}

// Returns the validated session id, or null after answering 400.
function sessionOrReject(res, cors, raw) {
  const session = typeof raw === 'string' ? raw.trim() : '';
  if (!SESSION_RE.test(session) || RESERVED_SESSIONS.has(session.toLowerCase())) {
    jsonResponse(res, 400, { error: 'invalid-session' }, cors);
    return null;
  }
  return session;
}

async function handle(req, res) {
  const url = new URL(req.url, `http://${HOST}:${PORT}`);
  const origin = req.headers.origin;

  // Foreign page (Origin) or DNS-rebinding (Host): refuse, with no CORS headers so
  // the browser does not hand the response to the page either.
  if (!ALLOWED_HOSTS.has(String(req.headers.host || '').toLowerCase())) {
    jsonResponse(res, 403, { error: 'forbidden-host' });
    return;
  }
  if (origin !== undefined && !ALLOWED_ORIGINS.has(origin)) {
    jsonResponse(res, 403, { error: 'forbidden-origin' });
    return;
  }
  const cors = corsHeaders(req);

  // Preflight (a file:// page sending X-Visual-Token + JSON). Cannot carry the token.
  if (req.method === 'OPTIONS') {
    jsonResponse(res, 204, {}, cors);
    return;
  }

  // Liveness check — used by start.sh to decide whether to spawn. `auth: true` tells
  // start.sh this daemon enforces the token (an older one does not and gets replaced).
  // No CORS headers here, and no pid for a request that carries an Origin: a sandboxed
  // iframe or data: page (Origin `null`) must not learn the daemon is there or its pid.
  if (url.pathname === '/ping') {
    if (origin === undefined) {
      lastActivity = Date.now();
      jsonResponse(res, 200, { status: 'ok', pid: process.pid, port: PORT, auth: true });
    } else {
      jsonResponse(res, 200, { status: 'ok' });
    }
    return;
  }

  if (url.pathname === '/state' && (req.method === 'POST' || req.method === 'GET')) {
    if (!tokenOk(req)) {
      jsonResponse(res, 403, { error: 'forbidden' }, cors);
      return;
    }
    lastActivity = Date.now();
  }

  // Receive state snapshot from browser.
  if (req.method === 'POST' && url.pathname === '/state') {
    const ctype = String(req.headers['content-type'] || '').split(';')[0].trim().toLowerCase();
    if (ctype !== 'application/json') {
      jsonResponse(res, 415, { error: 'unsupported-media-type' }, cors);
      return;
    }
    let raw;
    try {
      raw = await readBody(req);
    } catch (err) {
      jsonResponse(res, 413, { error: err.message }, cors);
      return;
    }
    let payload;
    try { payload = JSON.parse(raw); }
    catch { jsonResponse(res, 400, { error: 'invalid-json' }, cors); return; }
    if (!isPlainObject(payload)) {
      jsonResponse(res, 400, { error: 'invalid-payload' }, cors);
      return;
    }
    const session = sessionOrReject(res, cors, payload.session);
    if (session === null) return;
    if (payload.state !== undefined && payload.state !== null && !isPlainObject(payload.state)) {
      jsonResponse(res, 400, { error: 'invalid-state' }, cors);
      return;
    }
    const stateFile = path.join(STATE_DIR, `${session}.json`);
    const record = {
      session,
      timestamp: new Date().toISOString(),
      docTitle: typeof payload.docTitle === 'string' ? payload.docTitle : null,
      state: payload.state || {}
    };
    try {
      await fs.writeFile(stateFile, JSON.stringify(record, null, 2), 'utf8');
      // Maintain a "latest" pointer so Claude can read the most recent session
      // without knowing the exact token. Contains the same record, plus a pointer
      // to the per-session file.
      const latest = { ...record, stateFile };
      await fs.writeFile(path.join(STATE_DIR, 'latest.json'), JSON.stringify(latest, null, 2), 'utf8');
      jsonResponse(res, 200, { ok: true }, cors);
    } catch (err) {
      jsonResponse(res, 500, { error: err.message }, cors);
    }
    return;
  }

  // Read state (useful for debugging or pulling a past session). Agents read
  // latest.json from disk; there is no `latest` alias over HTTP.
  if (req.method === 'GET' && url.pathname === '/state') {
    const session = sessionOrReject(res, cors, url.searchParams.get('session') || '');
    if (session === null) return;
    try {
      const raw = await fs.readFile(path.join(STATE_DIR, `${session}.json`), 'utf8');
      jsonResponse(res, 200, JSON.parse(raw), cors);
    } catch {
      jsonResponse(res, 404, { error: 'not-found' }, cors);
    }
    return;
  }

  jsonResponse(res, 404, { error: 'not-found' }, cors);
}

const server = http.createServer((req, res) => {
  handle(req, res).catch((err) => {
    console.error('claude-visual-server: request failed:', err);
    try {
      if (!res.headersSent) jsonResponse(res, 500, { error: 'internal-error' });
      else res.end();
    } catch { /* socket already gone */ }
  });
});

// A bug in one request must never take the daemon (and the live sync) down.
process.on('unhandledRejection', (err) => {
  console.error('claude-visual-server: unhandled rejection:', err);
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
    // Keep-alive sockets would hold close() for seconds on old Node; start.sh waits 2 s.
    server.closeAllConnections?.();
  });
});
