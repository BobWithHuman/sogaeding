const http = require('node:http');
const fs = require('node:fs');

const evidencePath = '/evidence/receiver.jsonl';

const server = http.createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/health') {
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end('{}');
    return;
  }

  if (req.method !== 'POST' || req.url !== '/collect') {
    res.writeHead(404);
    res.end('not found');
    return;
  }

  let body = '';

  req.setEncoding('utf8');

  req.on('data', chunk => {
    body += chunk;

    if (body.length > 4096) {
      req.destroy();
    }
  });

  req.on('end', () => {
    let parsed;

    try {
      parsed = JSON.parse(body);
    } catch {
      res.writeHead(400);
      res.end('invalid json');
      return;
    }

    const evidence = {
      received_at: new Date().toISOString(),
      remote_address: req.socket.remoteAddress,
      payload: parsed
    };

    fs.appendFileSync(
      evidencePath,
      JSON.stringify(evidence) + '\n',
      'utf8'
    );

    res.writeHead(204);
    res.end();
  });
});

server.listen(8080, '0.0.0.0');