// TSRA — Live Viewer Count Server
// Run: node viewer-server.js

const http = require('http');
const { WebSocketServer } = require('ws');

const PORT = 5173;
const PING_INTERVAL_MS = 10000; // ping every 10s to detect zombies

const server = http.createServer((req, res) => {
  res.writeHead(200, {
    'Content-Type': 'text/plain',
    'Access-Control-Allow-Origin': '*',
  });
  // count only alive clients
  const alive = [...wss.clients].filter(c => c.readyState === 1).length;
  res.end(`TSRA viewer server — ${alive} connected\n`);
});

const wss = new WebSocketServer({ server });

function broadcast(count) {
  const msg = JSON.stringify({ viewers: count });
  for (const client of wss.clients) {
    if (client.readyState === 1) client.send(msg);
  }
}

function liveCount() {
  return [...wss.clients].filter(c => c.readyState === 1).length;
}

// ── Ping / pong heartbeat — kills zombie connections ──────────────────────
const pingInterval = setInterval(() => {
  for (const ws of wss.clients) {
    if (!ws.isAlive) {
      // didn't respond to last ping — terminate
      ws.terminate();
      continue;
    }
    ws.isAlive = false;
    ws.ping();
  }
}, PING_INTERVAL_MS);

wss.on('close', () => clearInterval(pingInterval));

// ── Connection handler ────────────────────────────────────────────────────
wss.on('connection', (ws, req) => {
  ws.isAlive = true;
  ws.on('pong', () => { ws.isAlive = true; });

  const ip = req.socket.remoteAddress;
  console.log(`[+] connected  — viewers: ${liveCount()}  (${ip})`);
  broadcast(liveCount());

  ws.on('close', () => {
    // slight delay so the socket is fully removed from wss.clients
    setTimeout(() => {
      console.log(`[-] disconnected — viewers: ${liveCount()}`);
      broadcast(liveCount());
    }, 50);
  });

  ws.on('error', (err) => {
    console.error(`[!] error: ${err.message}`);
  });
});

// ── Start ─────────────────────────────────────────────────────────────────
server.listen(PORT, '0.0.0.0', () => {
  const { networkInterfaces } = require('os');
  const nets = networkInterfaces();
  const ips = [];
  for (const ifaces of Object.values(nets)) {
    for (const iface of ifaces) {
      if (iface.family === 'IPv4' && !iface.internal) ips.push(iface.address);
    }
  }
  console.log(`\nTSRA viewer server — port ${PORT}`);
  console.log(`Local:   ws://localhost:${PORT}`);
  ips.forEach(ip => console.log(`Network: ws://${ip}:${PORT}`));
  console.log('');
});
