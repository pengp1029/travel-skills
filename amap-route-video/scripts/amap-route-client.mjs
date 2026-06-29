import {loadOpenClawEnv} from './load-openclaw-env.mjs';

loadOpenClawEnv(import.meta.url);

const AMAP_BASE = 'https://restapi.amap.com/v3';
const AMAP_V4_BASE = 'https://restapi.amap.com/v4';
const AMAP_MIN_REQUEST_INTERVAL_MS = Number(process.env.AMAP_MIN_REQUEST_INTERVAL_MS || 350);
let amapRequestQueue = Promise.resolve();
let lastAmapRequestAt = 0;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const runAmapRequestSerially = (task) => {
  const run = amapRequestQueue.then(async () => {
    const elapsed = Date.now() - lastAmapRequestAt;
    if (elapsed < AMAP_MIN_REQUEST_INTERVAL_MS) {
      await sleep(AMAP_MIN_REQUEST_INTERVAL_MS - elapsed);
    }
    try {
      return await task();
    } finally {
      lastAmapRequestAt = Date.now();
    }
  });
  amapRequestQueue = run.catch(() => {});
  return run;
};

export const modeLabels = {
  walking: '步行',
  bicycling: '骑行',
  driving: '驾车',
  transit: '地铁/公交',
};

const ensureKey = () => {
  const key = process.env.AMAP_KEY || process.env.AMAP_WEB_SERVICE_KEY;
  if (!key) throw new Error('缺少 AMAP_KEY 或 AMAP_WEB_SERVICE_KEY 环境变量');
  return key;
};

const requestJson = async (url) => runAmapRequestSerially(async () => {
  const response = await fetch(url);
  const text = await response.text();
  if (!response.ok) throw new Error(`高德请求失败：${response.status} ${text}`);
  const data = JSON.parse(text);
  if (data.status && data.status !== '1') {
    throw new Error(`高德接口错误：${data.info || data.message || text}`);
  }
  if (data.errcode) {
    throw new Error(`高德接口错误：${data.errmsg || text}`);
  }
  return data;
});

const urlWithParams = (base, params) => {
  const url = new URL(base);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value);
  });
  return url;
};

const parsePolyline = (polyline) => {
  if (!polyline || typeof polyline !== 'string') return [];
  return polyline.split(';')
    .map((pair) => pair.split(',').map(Number))
    .filter((pair) => Number.isFinite(pair[0]) && Number.isFinite(pair[1]));
};

const dedupePath = (path) => {
  const output = [];
  let previous = '';
  for (const point of path) {
    const key = `${point[0].toFixed(7)},${point[1].toFixed(7)}`;
    if (key !== previous) {
      output.push(point);
      previous = key;
    }
  }
  return output;
};

const appendPolyline = (target, polyline) => {
  target.push(...parsePolyline(polyline));
};

const toLngLat = (location) => {
  if (!location || typeof location !== 'string') return null;
  const [lng, lat] = location.split(',').map(Number);
  if (!Number.isFinite(lng) || !Number.isFinite(lat)) return null;
  return [lng, lat];
};

const numberValue = (value) => {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : 0;
};

const sum = (items, key) => items.reduce((total, item) => total + numberValue(item[key]), 0);
const formatInstruction = (step, fallback) => step.instruction || step.instructions || step.road || fallback;

export async function geocodePlace(place, city, key = ensureKey()) {
  const url = urlWithParams(`${AMAP_BASE}/geocode/geo`, {
    key,
    address: place,
    city,
    output: 'json',
  });
  const data = await requestJson(url);
  const geocode = data.geocodes?.[0];
  if (!geocode?.location) throw new Error(`地理编码失败：${place}`);
  return {
    name: place,
    coordinates: toLngLat(geocode.location),
    formattedAddress: geocode.formatted_address,
    adcode: geocode.adcode,
  };
}

async function planWalking(segment, from, to, key) {
  const url = urlWithParams(`${AMAP_BASE}/direction/walking`, {
    key,
    origin: from.coordinates.join(','),
    destination: to.coordinates.join(','),
    output: 'json',
  });
  const data = await requestJson(url);
  const route = data.route?.paths?.[0];
  if (!route) throw new Error(`步行规划失败：${segment.from}->${segment.to}`);
  const path = [];
  const steps = (route.steps || []).map((step) => {
    appendPolyline(path, step.polyline);
    return {mode: '步行', text: formatInstruction(step, '步行路段'), distanceMeters: numberValue(step.distance), durationSeconds: numberValue(step.duration)};
  });
  return makeSegment(segment, from, to, 'walking', '步行', '#1d6fea', path, route.distance, route.duration, 0, steps);
}

async function planDriving(segment, from, to, key) {
  const url = urlWithParams(`${AMAP_BASE}/direction/driving`, {
    key,
    origin: from.coordinates.join(','),
    destination: to.coordinates.join(','),
    extensions: 'all',
    output: 'json',
  });
  const data = await requestJson(url);
  const route = data.route?.paths?.[0];
  if (!route) throw new Error(`驾车规划失败：${segment.from}->${segment.to}`);
  const path = [];
  const steps = (route.steps || []).map((step) => {
    appendPolyline(path, step.polyline);
    return {mode: '驾车', text: formatInstruction(step, '驾车路段'), distanceMeters: numberValue(step.distance), durationSeconds: numberValue(step.duration)};
  });
  return makeSegment(segment, from, to, 'driving', '驾车', '#f59f00', path, route.distance, route.duration, route.tolls, steps);
}

async function planBicycling(segment, from, to, key) {
  const url = urlWithParams(`${AMAP_V4_BASE}/direction/bicycling`, {
    key,
    origin: from.coordinates.join(','),
    destination: to.coordinates.join(','),
    output: 'json',
  });
  const data = await requestJson(url);
  const route = data.data?.paths?.[0] || data.route?.paths?.[0];
  if (!route) throw new Error(`骑行规划失败：${segment.from}->${segment.to}`);
  const path = [];
  const steps = (route.steps || []).map((step) => {
    appendPolyline(path, step.polyline);
    return {mode: '骑行', text: formatInstruction(step, '骑行路段'), distanceMeters: numberValue(step.distance), durationSeconds: numberValue(step.duration)};
  });
  return makeSegment(segment, from, to, 'bicycling', '骑行', '#0f9f6e', path, route.distance, route.duration, 0, steps);
}

const lineName = (line) => String(line.name || '').split('(')[0].trim() || '公交/地铁';
const stopName = (stop) => stop?.name || '';
const lineMode = (line) => `${line.type || ''}${line.name || ''}`.includes('地铁') ? '地铁' : '公交';

const scoreTransit = (plan, preferredVehicle) => {
  const lines = (plan.segments || []).flatMap((segment) => segment.bus?.buslines || []);
  const hasSubway = lines.some((line) => lineMode(line) === '地铁');
  let score = numberValue(plan.duration);
  if (preferredVehicle === 'subway' && hasSubway) score -= 100000;
  if (preferredVehicle === 'bus' && !hasSubway) score -= 50000;
  return score;
};

async function planTransit(segment, from, to, key, city) {
  const url = urlWithParams(`${AMAP_BASE}/direction/transit/integrated`, {
    key,
    origin: from.coordinates.join(','),
    destination: to.coordinates.join(','),
    city,
    strategy: 0,
    extensions: 'all',
    output: 'json',
  });
  const data = await requestJson(url);
  const plans = data.route?.transits || [];
  if (!plans.length) throw new Error(`换乘规划失败：${segment.from}->${segment.to}`);
  const plan = [...plans].sort((a, b) => scoreTransit(a, segment.preferredVehicle) - scoreTransit(b, segment.preferredVehicle))[0];
  const path = [];
  const steps = [];

  for (const routeSegment of plan.segments || []) {
    const walking = routeSegment.walking;
    if (walking?.steps?.length) {
      const walkPath = [];
      for (const step of walking.steps) {
        appendPolyline(path, step.polyline);
        appendPolyline(walkPath, step.polyline);
      }
      if (walkPath.length) {
        steps.push({mode: '步行', text: '步行前往换乘点', distanceMeters: numberValue(walking.distance) || sum(walking.steps, 'distance'), durationSeconds: sum(walking.steps, 'duration')});
      }
    }

    for (const line of routeSegment.bus?.buslines || []) {
      appendPolyline(path, line.polyline);
      const mode = lineMode(line);
      const stops = [stopName(line.departure_stop), stopName(line.arrival_stop)].filter(Boolean).join(' -> ');
      const viaText = numberValue(line.via_num) ? `，途经 ${line.via_num} 站` : '';
      steps.push({mode, text: `${lineName(line)} ${stops || '按规划站点乘坐'}${viaText}`, distanceMeters: numberValue(line.distance), durationSeconds: numberValue(line.duration)});
    }
  }

  const hasSubway = steps.some((step) => step.mode === '地铁');
  const label = hasSubway ? '地铁/换乘' : '公交/换乘';
  return makeSegment(segment, from, to, 'transit', label, '#7c3aed', path, plan.distance, plan.duration, plan.cost, steps);
}

function makeSegment(input, from, to, mode, label, color, path, distance, duration, cost, steps) {
  const cleanPath = dedupePath(path);
  if (cleanPath.length < 2) {
    cleanPath.push(from.coordinates, to.coordinates);
  }
  return {
    mode,
    preferredVehicle: input.preferredVehicle,
    label,
    color,
    from,
    to,
    path: cleanPath,
    distanceMeters: numberValue(distance) || sum(steps, 'distanceMeters'),
    durationSeconds: numberValue(duration) || sum(steps, 'durationSeconds'),
    cost: numberValue(cost),
    steps: steps.filter((step) => step.text || step.distanceMeters || step.durationSeconds).slice(0, 10),
  };
}

const createPlannerContext = (plan) => {
  const key = ensureKey();
  const city = plan.city || process.env.AMAP_CITY || '北京';
  const geocodeCache = new Map();
  const getPlace = async (name) => {
    if (!geocodeCache.has(name)) geocodeCache.set(name, await geocodePlace(name, city, key));
    return geocodeCache.get(name);
  };
  return {key, city, getPlace};
};

async function planSegment(segment, from, to, key, city, mode = segment.mode) {
  if (mode === 'walking') return planWalking({...segment, mode}, from, to, key);
  if (mode === 'bicycling') return planBicycling({...segment, mode}, from, to, key);
  if (mode === 'driving') return planDriving({...segment, mode}, from, to, key);
  return planTransit({...segment, mode}, from, to, key, city);
}

const withSegmentMeta = (planned, input) => ({
  ...planned,
  dayId: input.dayId,
  segmentId: input.segmentId,
});

export async function buildRouteSpec(plan) {
  const {key, city, getPlace} = createPlannerContext(plan);
  const segments = [];
  for (const segment of plan.segments) {
    const from = await getPlace(segment.from);
    const to = await getPlace(segment.to);
    segments.push(withSegmentMeta(await planSegment(segment, from, to, key, city), segment));
  }

  return {
    title: plan.title || `${segments[0].from.name}到${segments[segments.length - 1].to.name}`,
    city,
    generatedAt: new Date().toISOString(),
    segments,
    totalDistanceMeters: segments.reduce((total, item) => total + item.distanceMeters, 0),
    totalDurationSeconds: segments.reduce((total, item) => total + item.durationSeconds, 0),
  };
}

export async function buildRouteOptionsSpec(plan) {
  const {key, city, getPlace} = createPlannerContext(plan);
  const modes = plan.modes || ['walking', 'transit', 'driving'];
  const segments = [];

  for (const segment of plan.segments) {
    const from = await getPlace(segment.from);
    const to = await getPlace(segment.to);
    const options = {};
    const routeErrors = [];

    for (const mode of modes) {
      try {
        options[mode] = withSegmentMeta(await planSegment(segment, from, to, key, city, mode), segment);
      } catch (error) {
        routeErrors.push({mode, message: error.message});
      }
    }

    const preferredMode = segment.mode && options[segment.mode] ? segment.mode : modes.find((mode) => options[mode]);
    if (!preferredMode) {
      throw new Error(`所有出行方案均规划失败：${segment.from}->${segment.to} ${routeErrors.map((item) => `${item.mode}:${item.message}`).join('；')}`);
    }

    const selected = options[preferredMode];
    segments.push({
      ...selected,
      mode: preferredMode,
      dayId: segment.dayId,
      segmentId: segment.segmentId,
      options,
      routeErrors,
    });
  }

  return {
    title: plan.title || `${segments[0].from.name}到${segments[segments.length - 1].to.name}`,
    city,
    generatedAt: new Date().toISOString(),
    routeOptionModes: modes,
    segments,
    totalDistanceMeters: segments.reduce((total, item) => total + item.distanceMeters, 0),
    totalDurationSeconds: segments.reduce((total, item) => total + item.durationSeconds, 0),
  };
}
