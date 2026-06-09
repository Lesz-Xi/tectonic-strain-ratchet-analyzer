// TSRA — Live Viewer Count + Static File Server
// Run: node viewer-server.js
// Then open: http://<your-ip>:5173 on any device on the same network.

const http = require('http');
const fs   = require('fs');
const path = require('path');
const { WebSocketServer } = require('ws');

const PORT = 5173;
const ROOT = __dirname;
const PING_INTERVAL_MS = 10000;

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.js':   'application/javascript',
  '.css':  'text/css',
};

// ── HTTP — serve static files ─────────────────────────────────────────────
const server = http.createServer((req, res) => {
  let urlPath = req.url.split('?')[0];
  if (urlPath === '/') urlPath = '/seismic_report.html';

  const filePath = path.join(ROOT, urlPath);
  // safety: don't serve files outside ROOT
  if (!filePath.startsWith(ROOT)) { res.writeHead(403); res.end(); return; }

  fs.readFile(filePath, (err, data) => {
    if (err) { res.writeHead(404); res.end('Not found'); return; }
    const ext  = path.extname(filePath).toLowerCase();
    const mime = MIME[ext] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': mime, 'Access-Control-Allow-Origin': '*' });
    res.end(data);
  });
});

// ── WebSocket — live viewer count ─────────────────────────────────────────
const wss = new WebSocketServer({ server });

function liveCount() {
  return [...wss.clients].filter(c => c.readyState === 1).length;
}
function broadcast(n) {
  const msg = JSON.stringify({ viewers: n });
  for (const c of wss.clients) { if (c.readyState === 1) c.send(msg); }
}

// Ping/pong heartbeat — kills zombie connections every PING_INTERVAL_MS
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

  const ip = req.socket.remoteAddress;
  console.log(`[+] connected  — viewers: ${liveCount()}  (${ip})`);
  broadcast(liveCount());

  ws.on('close', () => {
    setTimeout(() => {
      console.log(`[-] disconnected — viewers: ${liveCount()}`);
      broadcast(liveCount());
    }, 50);
  });

  ws.on('error', err => console.error(`[!] ${err.message}`));
});

// ── Start ─────────────────────────────────────────────────────────────────
server.listen(PORT, '0.0.0.0', () => {
  const { networkInterfaces } = require('os');
  const nets = networkInterfaces();
  const ips  = [];
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
