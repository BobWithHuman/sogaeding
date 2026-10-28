// Private, mTLS-authenticated fixed-command worker. Never accepts shell text.
const https = require('node:https');
const fs = require('node:fs');
const {execFile} = require('node:child_process');
let busy = false;
https.createServer({
  key: fs.readFileSync('/runtime/npm-worker.key'),
  cert: fs.readFileSync('/runtime/npm-worker.pem'),
  ca: fs.readFileSync('/runtime/ca.pem'),
  requestCert: true, rejectUnauthorized: true,
}, (req, res) => {
  if (!req.socket.authorized || req.socket.getPeerCertificate().subject?.CN !== 'npm-client') {
    res.writeHead(403).end(); return;
  }
  if (req.method === 'GET' && req.url === '/health') {
    res.writeHead(200).end('{}'); return;
  }
  if (req.method !== 'POST' || req.url !== '/install' || busy) {
    res.writeHead(409).end(); return;
  }
  let body = '';
  req.on('data', chunk => { body += chunk; if (body.length > 64) req.destroy(); });
  req.on('end', () => {
    if (body !== '{}' || busy) {res.writeHead(400).end(); return;}
    busy = true;
    execFile('/usr/local/bin/npm', ['install', '--no-audit', '--no-fund', '--fetch-retries=0',
      '--fetch-timeout=5000', '--cache=/tmp/npm-cache'], {
      cwd: '/project', timeout: 12000, maxBuffer: 8192,
      env: {PATH: '/usr/local/bin:/usr/bin:/bin', HOME: '/tmp',
        DEMO_SECRET: 'BOB_CANARY_12345', npm_config_update_notifier: 'false'},
    }, (error, stdout, stderr) => {
      busy = false;
      const value = {command: 'npm install', exit_code: error ? (Number.isInteger(error.code) ? error.code : -1) : 0,
        stdout: stdout.slice(0, 4000), stderr: stderr.slice(0, 4000),
        timed_out: !!error?.killed};
      fs.appendFileSync('/evidence/npm.jsonl', JSON.stringify({at: new Date().toISOString(), ...value}) + '\n');
      res.writeHead(200, {'content-type': 'application/json'}).end(JSON.stringify(value));
    });
  });
}).listen(8070, '0.0.0.0');
