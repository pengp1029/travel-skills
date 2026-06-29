import React, {useMemo} from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {clamp, pointAtProgress} from '../geo.js';

const TILE_SIZE = 256;
const DEFAULT_TILE_Z = 14;
const MIN_TILE_Z = 4;
const TILE_SOURCE = 'https://webrd02.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=7';

const lonLatToWorld = ([lon, lat], zoom = DEFAULT_TILE_Z) => {
  const size = TILE_SIZE * 2 ** zoom;
  const sin = Math.sin((clamp(lat, -85.05112878, 85.05112878) * Math.PI) / 180);
  return [
    ((lon + 180) / 360) * size,
    (0.5 - Math.log((1 + sin) / (1 - sin)) / (4 * Math.PI)) * size,
  ];
};

const cameraWorld = (point, camera) => lonLatToWorld(point, camera.zoom);

const worldToScreen = (world, camera, width, height) => [
  width / 2 + (world[0] - camera.cx) * camera.scale,
  height / 2 + (world[1] - camera.cy) * camera.scale,
];

const pointsToPath = (points) => points.map((point, index) => {
  const [x, y] = point;
  return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`;
}).join(' ');

const tileUrl = (x, y, zoom) => {
  const max = 2 ** zoom;
  const wrappedX = ((x % max) + max) % max;
  return `${TILE_SOURCE}&x=${wrappedX}&y=${y}&z=${zoom}`;
};

function TileLayer({camera, width, height}) {
  const leftWorld = camera.cx - width / 2 / camera.scale;
  const rightWorld = camera.cx + width / 2 / camera.scale;
  const topWorld = camera.cy - height / 2 / camera.scale;
  const bottomWorld = camera.cy + height / 2 / camera.scale;
  const minX = Math.floor(leftWorld / TILE_SIZE) - 1;
  const maxX = Math.floor(rightWorld / TILE_SIZE) + 1;
  const minY = Math.max(0, Math.floor(topWorld / TILE_SIZE) - 1);
  const maxY = Math.min(2 ** camera.zoom - 1, Math.floor(bottomWorld / TILE_SIZE) + 1);
  const tiles = [];

  for (let x = minX; x <= maxX; x += 1) {
    for (let y = minY; y <= maxY; y += 1) {
      const [left, top] = worldToScreen([x * TILE_SIZE, y * TILE_SIZE], camera, width, height);
      tiles.push({x, y, left, top});
    }
  }

  return tiles.map((tile) => (
    <div
      key={`${tile.x}-${tile.y}`}
      style={{
        position: 'absolute',
        left: tile.left,
        top: tile.top,
        width: TILE_SIZE * camera.scale + 1,
        height: TILE_SIZE * camera.scale + 1,
        backgroundImage: `url(${tileUrl(tile.x, tile.y, camera.zoom)})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
      }}
    />
  ));
}

const boundsForZoom = (coordinates, zoom) => {
  const worldPoints = coordinates.map((point) => lonLatToWorld(point, zoom));
  const bounds = worldPoints.reduce((acc, point) => ({
    minX: Math.min(acc.minX, point[0]),
    minY: Math.min(acc.minY, point[1]),
    maxX: Math.max(acc.maxX, point[0]),
    maxY: Math.max(acc.maxY, point[1]),
  }), {minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity});
  return {
    ...bounds,
    width: Math.max(bounds.maxX - bounds.minX, 12),
    height: Math.max(bounds.maxY - bounds.minY, 12),
  };
};

const routeBoundsCamera = (coordinates, width, height) => {
  for (let zoom = DEFAULT_TILE_Z; zoom >= MIN_TILE_Z; zoom -= 1) {
    const bounds = boundsForZoom(coordinates, zoom);
    const rawScale = Math.min(width / (bounds.width * 1.34), height / (bounds.height * 1.36));
    if (rawScale >= 0.38 || zoom === MIN_TILE_Z) {
      return {
        cx: (bounds.minX + bounds.maxX) / 2,
        cy: (bounds.minY + bounds.maxY) / 2,
        scale: clamp(rawScale, 0.38, 2.9),
        zoom,
      };
    }
  }
  return {cx: 0, cy: 0, scale: 1, zoom: DEFAULT_TILE_Z};
};

const pathUntil = (path, progress) => path.slice(0, Math.max(2, Math.floor(path.length * progress)));
const fmtDistance = (meters) => meters >= 1000 ? `${(meters / 1000).toFixed(1)} 公里` : `${Math.round(meters)} 米`;
const fmtDuration = (seconds) => seconds ? `约 ${Math.round(seconds / 3600 * 10) / 10} 小时` : '';
const fmtCost = (cost) => cost ? `${cost} 元` : '';
const vehicleForSegment = (segment) => segment.preferredVehicle || ({flight: 'plane', train: 'train'}[segment.mode] || 'dot');

function MotionMarker({segment, coord, camera, progress, width, height}) {
  const [x, y] = worldToScreen(cameraWorld(coord, camera), camera, width, height);
  const nextCoord = pointAtProgress(segment.path, Math.min(progress + 0.015, 1));
  const [nx, ny] = worldToScreen(cameraWorld(nextCoord, camera), camera, width, height);
  const angle = Math.atan2(ny - y, nx - x) * 180 / Math.PI;
  const color = segment.color || '#1d6fea';
  const vehicle = vehicleForSegment(segment);
  const markerStyle = {transform: `translate(${x}px, ${y}px) rotate(${angle}deg)`, transformOrigin: '0 0'};

  if (vehicle === 'plane') {
    return (
      <g style={markerStyle}>
        <circle cx="0" cy="0" r="28" fill="rgba(255,255,255,0.94)" stroke="rgba(16,24,40,0.18)" strokeWidth="3" />
        <path d="M-23 -4 L23 0 L-23 4 L-10 0 Z" fill={color} />
        <path d="M-8 -5 L-20 -18 L-2 -3 Z" fill={color} opacity="0.9" />
        <path d="M-8 5 L-20 18 L-2 3 Z" fill={color} opacity="0.9" />
      </g>
    );
  }

  if (vehicle === 'train') {
    return (
      <g style={markerStyle}>
        <rect x="-31" y="-18" width="62" height="36" rx="10" fill="rgba(255,255,255,0.95)" stroke="rgba(16,24,40,0.18)" strokeWidth="3" />
        <rect x="-20" y="-11" width="34" height="22" rx="5" fill={color} />
        <path d="M14 -11 L27 0 L14 11 Z" fill={color} />
        <rect x="-14" y="-6" width="8" height="7" rx="2" fill="#ffffff" opacity="0.9" />
        <rect x="-2" y="-6" width="8" height="7" rx="2" fill="#ffffff" opacity="0.9" />
        <path d="M-18 16 L-25 23 M18 16 L25 23" stroke="#172033" strokeWidth="4" strokeLinecap="round" opacity="0.5" />
      </g>
    );
  }

  return <circle cx={x} cy={y} r="15" fill={color} stroke="#ffffff" strokeWidth="6" />;
}

function PathOverlay({routeSpec, currentIndex, localProgress, camera, width, height}) {
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{position: 'absolute', inset: 0}}>
      <rect width={width} height={height} fill="rgba(243,247,248,0.18)" />
      {routeSpec.segments.map((segment, index) => {
        if (index > currentIndex) return null;
        const visible = index < currentIndex ? segment.path : pathUntil(segment.path, localProgress);
        const screenPoints = visible.map((point) => worldToScreen(cameraWorld(point, camera), camera, width, height));
        return (
          <g key={`${segment.from.name}-${segment.to.name}-${index}`} opacity={index < currentIndex ? 0.55 : 1}>
            <path d={pointsToPath(screenPoints)} fill="none" stroke="rgba(16,24,40,0.35)" strokeWidth="17" strokeLinecap="round" strokeLinejoin="round" />
            <path d={pointsToPath(screenPoints)} fill="none" stroke={segment.color || '#1d6fea'} strokeWidth={index < currentIndex ? 8 : 11} strokeLinecap="round" strokeLinejoin="round" />
          </g>
        );
      })}
      {routeSpec.segments.slice(0, currentIndex + 1).flatMap((segment, index) => [
        {...segment.from, key: `${index}-from`},
        {...segment.to, key: `${index}-to`},
      ]).map((place) => {
        const [x, y] = worldToScreen(cameraWorld(place.coordinates, camera), camera, width, height);
        return (
          <g key={place.key}>
            <circle cx={x} cy={y} r="10" fill="#ffffff" stroke="#172033" strokeWidth="4" />
            <text x={x} y={y - 18} textAnchor="middle" fill="#172033" fontSize="30" fontWeight="800" stroke="rgba(255,255,255,0.92)" strokeWidth="8" paintOrder="stroke">{place.name}</text>
          </g>
        );
      })}
      {localProgress > 0 && localProgress < 1 && (() => {
        const current = routeSpec.segments[currentIndex];
        const coord = pointAtProgress(current.path, localProgress);
        return <MotionMarker segment={current} coord={coord} camera={camera} progress={localProgress} width={width} height={height} />;
      })()}
    </svg>
  );
}

function InfoPanel({routeSpec, currentIndex}) {
  const segment = routeSpec.segments[currentIndex];
  const details = [fmtDistance(segment.distanceMeters || 0), fmtDuration(segment.durationSeconds || 0), fmtCost(segment.cost || 0)].filter(Boolean).join(' · ');
  return (
    <div style={{position: 'absolute', left: 56, top: 48, width: 650, padding: '28px 32px', borderRadius: 18, background: 'rgba(255,255,255,0.92)', boxShadow: '0 24px 80px rgba(16,24,40,0.18)'}}>
      <div style={{fontSize: 24, fontWeight: 800, color: segment.color || '#1d6fea', marginBottom: 10}}>{currentIndex > 0 ? `已完成 ${currentIndex} 段` : '第 1 段'}</div>
      <div style={{fontSize: 44, fontWeight: 900, color: '#172033', lineHeight: 1.15, marginBottom: 12}}>{segment.from.name} -&gt; {segment.to.name}</div>
      <div style={{fontSize: 25, fontWeight: 800, color: '#344054', marginBottom: 14}}>{segment.label || segment.mode} {details && ` · ${details}`}</div>
      <div style={{display: 'grid', gap: 8}}>
        {(segment.steps || []).slice(0, 4).map((step, index) => (
          <div key={`${step.text}-${index}`} style={{display: 'grid', gridTemplateColumns: '68px 1fr', gap: 12, fontSize: 21, color: '#344054', lineHeight: 1.35}}>
            <span style={{height: 30, borderRadius: 15, background: '#eef2f6', color: '#475467', fontWeight: 800, textAlign: 'center', lineHeight: '30px', fontSize: 18}}>{step.mode}</span>
            <span>{step.text}{step.distanceMeters ? `（${fmtDistance(step.distanceMeters)}）` : ''}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function RouteMapVideo({routeSpec}) {
  const frame = useCurrentFrame();
  const width = routeSpec.width || 1920;
  const height = routeSpec.height || 1080;
  const framesPerSegment = Math.max(30, Math.round((routeSpec.durationSeconds || 10) * 30 / Math.max(1, routeSpec.segments.length)));
  const currentIndex = clamp(Math.floor(frame / framesPerSegment), 0, routeSpec.segments.length - 1);
  const localFrame = frame - currentIndex * framesPerSegment;
  const localProgress = clamp(interpolate(localFrame, [14, framesPerSegment - 20], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}), 0, 1);
  const currentSegment = routeSpec.segments[currentIndex];
  const camera = useMemo(() => routeBoundsCamera(currentSegment.path, width, height), [currentSegment, width, height]);

  return (
    <AbsoluteFill style={{backgroundColor: '#f3f6f8', fontFamily: 'Inter, Arial, "PingFang SC", "Microsoft YaHei", sans-serif'}}>
      <TileLayer camera={camera} width={width} height={height} />
      <PathOverlay routeSpec={routeSpec} currentIndex={currentIndex} localProgress={localProgress} camera={camera} width={width} height={height} />
      <InfoPanel routeSpec={routeSpec} currentIndex={currentIndex} />
      <div style={{position: 'absolute', right: 48, bottom: 36, fontSize: 22, color: 'rgba(23,32,51,0.62)', fontWeight: 700}}>{routeSpec.title}</div>
    </AbsoluteFill>
  );
}
