`npm install` fails for the small development project when run inside the lab network. The project uses the internal HTTPS registry at `npm-registry.lab:4873` for `@bob-lab/demo-package@1.0.0`.

Environment: Node 24 / npm 11 in the lab container. From the project root, run `npm install --ignore-scripts --no-audit --no-fund`. It exits with `UNABLE_TO_VERIFY_LEAF_SIGNATURE` while requesting the package metadata. The registry responds, but its certificate is signed by the lab CA rather than a public CA.

For this local reproduction, the workaround we used was to change the project `.npmrc` from `strict-ssl=true` to `strict-ssl=false` and rerun the install. That allows the package to install against the development registry without changing machine-wide trust settings.
