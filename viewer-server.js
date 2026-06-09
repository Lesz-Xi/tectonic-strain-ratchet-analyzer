// TSRA — Live Viewer Count + Static File Server

const http = require('http');
const fs = require('fs');
const path = require('path');
const { WebSocketServer } = require('ws');

const PORT = 5173;
const ROOT = __dirname;
const PING_INTERVAL_MS = 10000;

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.js': 'application/javascript',
  '.css': 'text/css',
};

// ── HTTP — serve static files ─────────────────────────────────────────────
const server = http.createServer((req, res) => {
  let urlPath = req.url.split('?')[0];
  if (urlPath === '/') urlPath = '/seismic_report.html';

  const filePath = path.join(ROOT, urlPath);
  if (!filePath.startsWith(ROOT)) { res.writeHead(403); res.end(); return; }

  fs.readFile(filePath, (err, data) => {
    if (err) { res.writeHead(404); res.end('Not found'); return; }
    const ext = path.extname(filePath).toLowerCase();
    const mime = MIME[ext] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': mime, 'Access-Control-Allow-Origin': '*' });
    res.end(data);
  });
});

// ── WebSocket — live viewer count ─────────────────────────────────────────
const wss = new WebSocketServer({ server });

function getUniqueViewerCount() {
  const uniqueClients = new Set();
  for (const c of wss.clients) {
    if (c.readyState === 1 && c.clientId) {
      uniqueClients.add(c.clientId);
    }
  }
  return uniqueClients.size;
}

function broadcast() {
  const n = getUniqueViewerCount();
  const msg = JSON.stringify({ viewers: n });
  for (const c of wss.clients) {
    if (c.readyState === 1) c.send(msg);
  }
}

// Ping/pong heartbeat — kills zombie connections
const pingInterval = setInterval(() => {
  for (const ws of wss.clients) {
    if (!ws.isAlive) { ws.terminate(); continue; }
    ws.isAlive = false;
    ws.ping();
  }
}, PING_INTERVAL_MS);
wss.on('close', () => clearInterval(pingInterval));

wss.on('connection', (ws, req) => {
  ws.isAlive = true;
  ws.on('pong', () => { ws.isAlive = true; });

  // Extract persistent clientId from URL to group tabs by device
  try {
    const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
    ws.clientId = url.searchParams.get('clientId') || req.socket.remoteAddress;
  } catch (err) {
    ws.clientId = req.socket.remoteAddress;
  }

  console.log(`[+] connected  — viewers: ${getUniqueViewerCount()}  (ID: ${ws.clientId.substring(0, 6)}...)`);
  broadcast();

  ws.on('close', () => {
    // 500ms debounce prevents count flickering during rapid tab reloads
    setTimeout(() => {
      console.log(`[-] disconnected — viewers: ${getUniqueViewerCount()}`);
      broadcast();
    }, 500);
  });

  ws.on('error', err => console.error(`[!] ${err.message}`));
});

// ── Start ─────────────────────────────────────────────────────────────────
server.listen(PORT, '0.0.0.0', () => {
  const { networkInterfaces } = require('os');
  const nets = networkInterfaces();
  const ips = [];
  for (const ifaces of Object.values(nets)) {
    for (const i of ifaces) {
      if (i.family === 'IPv4' && !i.internal) ips.push(i.address);
    }
  }
  console.log(`\nTSRA viewer server — port ${PORT}`);
  console.log(`Local:   http://localhost:${PORT}`);
  ips.forEach(ip => console.log(`Network: http://${ip}:${PORT}  ← open this on your phone`));
  console.log('');
});