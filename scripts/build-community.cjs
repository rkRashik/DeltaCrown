/* Compile the existing independent React scripts without changing their globals. */
const fs = require('node:fs');
const path = require('node:path');
const esbuild = require('esbuild');
const source = path.join(__dirname, '..', 'static', 'community');
const entryPoints = fs.readdirSync(source)
  .filter((name) => name.endsWith('.jsx'))
  .map((name) => path.join(source, name));
esbuild.buildSync({
  entryPoints,
  outdir: path.join(source, 'build'),
  bundle: false,
  target: 'es2019',
  jsx: 'transform',
  charset: 'utf8',
  legalComments: 'none',
  logLevel: 'info',
});
