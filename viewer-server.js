// TSRA — Live Viewer Count Server
// Run: node viewer-server.js
// Tracks real connections across machines on the same network.

const http = require('http');
const { WebSocketServer } = require('ws');

const PORT = 5173;
const clients = new Set();

const server = http.createServer((req, res) => {
  res.writeHead(200, {
    'Content-Type': 'text/plain',
    'Access-Control-Allow-Origin': '*',
  });
  res.end(`TSRA viewer server — ${clients.size} connected\n`);
});

const wss = new WebSocketServer({ server });

function broadcast(count) {
  const msg = JSON.stringify({ viewers: count });
  for (const client of clients) {
    if (client.readyState === 1) client.send(msg);
  }
}

wss.on('connection', (ws, req) => {
  clients.add(ws);
  console.log(`[+] connected  — total: ${clients.size}  (${req.socket.remoteAddress})`);
  broadcast(clients.size);

  ws.on('close', () => {
    clients.delete(ws);
    console.log(`[-] disconnected — total: ${clients.size}`);
    broadcast(clients.size);
  });

  ws.on('error', () => {
    clients.delete(ws);
    broadcast(clients.size);
  });
});

server.listen(PORT, '0.0.0.0', () => {
  const { networkInterfaces } = require('os');
  const nets = networkInterfaces();
  const ips = [];
  for (const ifaces of Object.values(nets)) {
    for (const iface of ifaces) {
      if (iface.family === 'IPv4' && !iface.internal) ips.push(iface.address);
    }
  }
  console.log(`\nTSRA viewer server running on port ${PORT}`);
  console.log(`Local:   ws://localhost:${PORT}`);
  ips.forEach(ip => console.log(`Network: ws://${ip}:${PORT}`));
  console.log('\nOpen seismic_report.html on any machine on this network.');
  console.log('Viewer count will update live.\n');
});
