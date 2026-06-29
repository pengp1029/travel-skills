#!/usr/bin/env node
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const skillDir = path.resolve(__dirname, '..');

const CITY_COORDS = new Map(Object.entries({
  北京: [116.4074, 39.9042], 北京市: [116.4074, 39.9042],
  上海: [121.4737, 31.2304], 上海市: [121.4737, 31.2304],
  广州: [113.2644, 23.1291], 广州市: [113.2644, 23.1291],
  深圳: [114.0579, 22.5431], 深圳市: [114.0579, 22.5431],
  杭州: [120.1551, 30.2741], 杭州市: [120.1551, 30.2741],
  南京: [118.7969, 32.0603], 南京市: [118.7969, 32.0603],
  苏州: [120.5853, 31.2989], 苏州市: [120.5853, 31.2989],
  天津: [117.2000, 39.0842], 天津市: [117.2000, 39.0842],
  济南: [117.1201, 36.6512], 济南市: [117.1201, 36.6512],
  徐州: [117.1848, 34.2618], 徐州市: [117.1848, 34.2618],
  武汉: [114.3054, 30.5931], 武汉市: [114.3054, 30.5931],
  成都: [104.0665, 30.5723], 成都市: [104.0665, 30.5723],
  重庆: [106.5516, 29.5630], 重庆市: [106.5516, 29.5630],
  西安: [108.9398, 34.3416], 西安市: [108.9398, 34.3416],
  郑州: [113.6254, 34.7466], 郑州市: [113.6254, 34.7466],
  长沙: [112.9388, 28.2282], 长沙市: [112.9388, 28.2282],
  南昌: [115.8582, 28.6820], 南昌市: [115.8582, 28.6820],
  合肥: [117.2272, 31.8206], 合肥市: [117.2272, 31.8206],
  青岛: [120.3826, 36.0671], 青岛市: [120.3826, 36.0671],
  厦门: [118.0894, 24.4798], 厦门市: [118.0894, 24.4798],
  福州: [119.2965, 26.0745], 福州市: [119.2965, 26.0745],
  昆明: [102.8329, 24.8801], 昆明市: [102.8329, 24.8801],
  哈尔滨: [126.5349, 45.8038], 哈尔滨市: [126.5349, 45.8038],
  沈阳: [123.4315, 41.8057], 沈阳市: [123.4315, 41.8057],
  大连: [121.6147, 38.9140], 大连市: [121.6147, 38.9140],
  海口: [110.1983, 20.0458], 海口市: [110.1983, 20.0458],
  三亚: [109.5119, 18.2528], 三亚市: [109.5119, 18.2528],
}));

function argValue(name, fallback = '') {
  const idx = process.argv.indexOf(name);
  if (idx === -1 || idx + 1 >= process.argv.length) return fallback;
  return process.argv[idx + 1];
}

function hasFlag(name) {
  return process.argv.includes(name);
}

function defaultBrowserExecutable() {
  return process.env.REMOTION_BROWSER_EXECUTABLE || process.env.CHROME_PATH || null;
}

function parseCoord(text) {
  const trimmed = String(text || '').trim();
  const namedCoord = trimmed.match(/^([^:：]+)[:：](-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)$/);
  if (namedCoord) {
    return {name: namedCoord[1].trim(), coordinates: [Number(namedCoord[2]), Number(namedCoord[3])]};
  }
  const coordOnly = trimmed.match(/^(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)$/);
  if (coordOnly) {
    return {name: trimmed, coordinates: [Number(coordOnly[1]), Number(coordOnly[2])]};
  }
  const known = CITY_COORDS.get(trimmed);
  if (!known) {
    throw new Error(`Unknown place: ${trimmed}. Use a known city name or pass name:lng,lat`);
  }
  return {name: trimmed.replace(/市$/, ''), coordinates: known};
}

function parseVia(text) {
  if (!text) return [];
  return text.split(/[;；]/).map((item) => item.trim()).filter(Boolean).map(parseCoord);
}

function interpolatePath(points, mode) {
  if (points.length >= 3) return points.map((point) => point.coordinates);
  const start = points[0].coordinates;
  const end = points[1].coordinates;
  const steps = 7;
  const dx = end[0] - start[0];
  const dy = end[1] - start[1];
  const curve = mode === 'flight' ? 0.22 : 0.08;
  const pathPoints = [];
  for (let i = 0; i < steps; i += 1) {
    const t = i / (steps - 1);
    const bow = Math.sin(Math.PI * t) * curve;
    pathPoints.push([
      start[0] + dx * t - dy * bow,
      start[1] + dy * t + dx * bow,
    ]);
  }
  return pathPoints;
}

function haversineMeters(pathPoints) {
  const radius = 6371000;
  let total = 0;
  for (let i = 1; i < pathPoints.length; i += 1) {
    const [lon1, lat1] = pathPoints[i - 1].map((value) => value * Math.PI / 180);
    const [lon2, lat2] = pathPoints[i].map((value) => value * Math.PI / 180);
    const dLat = lat2 - lat1;
    const dLon = lon2 - lon1;
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
    total += radius * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }
  return Math.round(total);
}

function buildSpec() {
  const mode = argValue('--mode', 'train');
  if (!['train', 'flight'].includes(mode)) {
    throw new Error('--mode must be train or flight');
  }
  const from = parseCoord(argValue('--from'));
  const to = parseCoord(argValue('--to'));
  const via = parseVia(argValue('--via'));
  const points = [from, ...via, to];
  const pathPoints = interpolatePath(points, mode);
  const distanceMeters = Number(argValue('--distance-meters', '')) || haversineMeters(pathPoints);
  const durationSeconds = Number(argValue('--travel-seconds', '')) || (mode === 'flight' ? Math.round(distanceMeters / 230) : Math.round(distanceMeters / 73));
  const cost = Number(argValue('--cost', '')) || 0;
  const label = mode === 'flight' ? '飞机' : '高铁';
  const color = mode === 'flight' ? '#0ea5e9' : '#16a34a';
  const title = argValue('--title', `${from.name} → ${to.name} ${label}路线`);
  const width = Number(argValue('--width', '1920'));
  const height = Number(argValue('--height', '1080'));
  const videoSeconds = Number(argValue('--duration', '10'));

  return {
    title,
    width,
    height,
    durationSeconds: videoSeconds,
    generatedAt: new Date().toISOString(),
    segments: [
      {
        mode,
        preferredVehicle: mode === 'flight' ? 'plane' : 'train',
        label,
        color,
        from,
        to,
        path: pathPoints,
        distanceMeters,
        durationSeconds,
        cost,
        steps: [
          {mode: label, text: `${from.name}出发，沿${label}路线前进`, distanceMeters: Math.round(distanceMeters / 2)},
          {mode: label, text: `抵达${to.name}`, distanceMeters: Math.round(distanceMeters / 2)},
        ],
      },
    ],
    totalDistanceMeters: distanceMeters,
    totalDurationSeconds: durationSeconds,
  };
}

async function main() {
  if (!argValue('--from') || !argValue('--to')) {
    throw new Error('Usage: node scripts/generate-route-map-video.mjs --from 上海 --to 北京 --mode train [--via 南京;济南] [--out-dir out/demo]');
  }

  const spec = argValue('--input-file')
    ? JSON.parse(await readFile(path.resolve(argValue('--input-file')), 'utf8'))
    : buildSpec();
  const outDir = path.resolve(argValue('--out-dir', path.join(skillDir, 'out', `${Date.now()}-${spec.segments[0].mode}`)));
  await mkdir(outDir, {recursive: true});
  const specPath = path.join(outDir, 'route-spec.json');
  await writeFile(specPath, JSON.stringify(spec, null, 2), 'utf8');

  if (hasFlag('--spec-only')) {
    process.stdout.write(JSON.stringify({specPath, outputPath: null, spec}, null, 2) + '\n');
    return;
  }

  process.env.ROUTE_VIDEO_WIDTH = String(spec.width || 1920);
  process.env.ROUTE_VIDEO_HEIGHT = String(spec.height || 1080);
  process.env.ROUTE_VIDEO_DURATION = String(spec.durationSeconds || 10);

  const entryPoint = path.join(skillDir, 'src', 'index.jsx');
  const browserExecutable = defaultBrowserExecutable();
  const browserOptions = browserExecutable ? {browserExecutable} : {};
  const serveUrl = await bundle({entryPoint});
  const composition = await selectComposition({
    serveUrl,
    id: 'RouteMapVideo',
    inputProps: {routeSpec: spec},
    timeoutInMilliseconds: 120000,
    ...browserOptions,
  });
  const renderComposition = {
    ...composition,
    durationInFrames: Math.max(30, Math.round((spec.durationSeconds || 10) * 30)),
  };
  const outputPath = path.join(outDir, 'route-map-video.mp4');
  await renderMedia({
    composition: renderComposition,
    serveUrl,
    codec: 'h264',
    outputLocation: outputPath,
    inputProps: {routeSpec: spec},
    pixelFormat: 'yuv420p',
    timeoutInMilliseconds: 120000,
    concurrency: 1,
    ...browserOptions,
  });

  process.stdout.write(JSON.stringify({
    specPath,
    outputPath,
    outputUrl: pathToFileURL(outputPath).href,
    mode: spec.segments[0].mode,
    width: spec.width || 1920,
    height: spec.height || 1080,
    durationSeconds: spec.durationSeconds || 10,
  }, null, 2) + '\n');
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
