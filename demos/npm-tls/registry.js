const https = require('node:https');
const fs = require('node:fs');
const crypto = require('node:crypto');

const tarball = fs.readFileSync('/lab/assets/package.tgz');

const shasum =
  crypto.createHash('sha1').update(tarball).digest('hex');

const integrity =
  'sha512-' +
  crypto.createHash('sha512').update(tarball).digest('base64');

const base = 'https://npm-registry.lab:4873';

const metadata = {
  name: '@bob-lab/demo-package',
  'dist-tags': {
    latest: '1.0.0'
  },
  versions: {
    '1.0.0': {
      name: '@bob-lab/demo-package',
      version: '1.0.0',
      scripts: {
        postinstall: 'node postinstall.js'
      },
      dist: {
        tarball:
          `${base}/@bob-lab/demo-package/-/demo-package-1.0.0.tgz`,
        shasum,
        integrity
      }
    }
  }
};

https.createServer({
  key: fs.readFileSync('/runtime/registry.key'),
  cert: fs.readFileSync('/runtime/registry.pem')
}, (req, res) => {
  const path =
    decodeURIComponent((req.url || '').split('?')[0]);

  if (path === '/-/ping') {
    res.writeHead(200, {
      'content-type': 'application/json'
    });

    res.end('{}');
    return;
  }

  if (path === '/@bob-lab/demo-package') {
    res.writeHead(200, {
      'content-type': 'application/json'
    });

    res.end(JSON.stringify(metadata));
    return;
  }

  if (
    path ===
    '/@bob-lab/demo-package/-/demo-package-1.0.0.tgz'
  ) {
    res.writeHead(200, {
      'content-type': 'application/octet-stream',
      'content-length': tarball.length
    });

    res.end(tarball);
    return;
  }

  res.writeHead(404);
  res.end('not found');
}).listen(4873, '0.0.0.0');
