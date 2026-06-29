#!/usr/bin/env node
import {spawn} from 'node:child_process';
import {existsSync} from 'node:fs';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadOpenClawEnv} from './load-openclaw-env.mjs';
import {parsePlan} from './plan-to-route-spec.mjs';
import {buildRouteOptionsSpec, buildRouteSpec} from './amap-route-client.mjs';

loadOpenClawEnv(import.meta.url);

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const skillDir = path.resolve(__dirname, '..');
const outDir = path.join(skillDir, 'out');
const routeSpecPath = path.join(outDir, 'route-spec.json');
const routeSpecModulePath = path.join(skillDir, 'src', 'route', 'generatedRouteSpec.js');
const outputPath = path.join(outDir, 'amap-segmented-route.mp4');
const defaultChromePath = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

function argValue(name) {
  const index = process.argv.indexOf(name);
  if (index === -1 || index + 1 >= process.argv.length) return '';
  return process.argv[index + 1];
}

function hasFlag(name) {
  return process.argv.includes(name);
}

function browserExecutableArgs() {
  const browserExecutable = process.env.REMOTION_BROWSER_EXECUTABLE || defaultChromePath;
  return existsSync(browserExecutable) ? ['--browser-executable', browserExecutable] : [];
}

const run = (command, args, options = {}) => new Promise((resolve, reject) => {
  const child = spawn(command, args, {
    cwd: skillDir,
    stdio: 'inherit',
    shell: process.platform === 'win32',
    ...options,
  });
  child.on('error', reject);
  child.on('exit', (code) => {
    if (code === 0) resolve();
    else reject(new Error(`${command} ${args.join(' ')} 退出码 ${code}`));
  });
});

async function loadPlan() {
  const inputFile = argValue('--input-file');
  if (inputFile) {
    const resolved = path.resolve(inputFile);
    if (resolved.endsWith('.js') || resolved.endsWith('.mjs')) {
      const mod = await import(`file://${resolved}`);
      return mod.defaultRouteSpec || mod.generatedRouteSpec || mod.default;
    }
    return JSON.parse(await readFile(resolved, 'utf8'));
  }
  const text = argValue('--plan') || process.argv.slice(2).filter((item) => !item.startsWith('--')).join(' ').trim();
  if (!text) {
    throw new Error('用法：node scripts/generate-route-video.mjs --plan "雍和宫->什刹海步行一段，什刹海->王府井地铁一段"');
  }
  return parsePlan(text);
}

const plan = await loadPlan();
const routeSpec = plan.segments?.[0]?.path ? plan : hasFlag('--all-modes') || hasFlag('--route-options') ? await buildRouteOptionsSpec(plan) : await buildRouteSpec(plan);

await mkdir(outDir, {recursive: true});
await writeFile(routeSpecPath, `${JSON.stringify(routeSpec, null, 2)}\n`, 'utf8');
await writeFile(routeSpecModulePath, `export const generatedRouteSpec = ${JSON.stringify(routeSpec, null, 2)};\n`, 'utf8');
console.log(`已写入 ${routeSpecPath}`);
console.log(`已写入 ${routeSpecModulePath}`);

if (hasFlag('--spec-only')) {
  console.log(JSON.stringify({routeSpecPath, outputPath: null}, null, 2));
  process.exit(0);
}

await run('npx', [
  'remotion',
  'render',
  'src/index.jsx',
  'AmapSegmentedRouteVideo',
  outputPath,
  ...browserExecutableArgs(),
  '--disable-web-security',
  '--ignore-certificate-errors',
  '--concurrency=1',
  '--codec=h264',
  '--pixel-format=yuv420p',
]);

console.log(JSON.stringify({routeSpecPath, outputPath}, null, 2));
