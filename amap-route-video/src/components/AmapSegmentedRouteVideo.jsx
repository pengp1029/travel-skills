import React, {useMemo} from 'react';
import {AbsoluteFill, Img, interpolate, useCurrentFrame} from 'remotion';
import {clamp, pointAtProgress} from '../geo.js';

const WIDTH = 1920;
const HEIGHT = 1080;
const TILE_SIZE = 256;
const TILE_Z = 14;
const TILE_SOURCE = 'https://webrd02.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=7';
const FRAMES_PER_SEGMENT = 150;

const lonLatToWorld = ([lon, lat], zoom = TILE_Z) => {
  const size = TILE_SIZE * 2 ** zoom;
  const sin = Math.sin((clamp(lat, -85.05112878, 85.05112878) * Math.PI) / 180);
  return [
    ((lon + 180) / 360) * size,
    (0.5 - Math.log((1 + sin) / (1 - sin)) / (4 * Math.PI)) * size,
  ];
};

const worldToScreen = (world, camera) => [
  WIDTH / 2 + (world[0] - camera.cx) * camera.scale,
  HEIGHT / 2 + (world[1] - camera.cy) * camera.scale,
];

const pointsToPath = (points) => points.map((point, index) => {
  const [x, y] = point;
  return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`;
}).join(' ');

const tileUrl = (x, y) => {
  const max = 2 ** TILE_Z;
  const wrappedX = ((x % max) + max) % max;
  return `${TILE_SOURCE}&x=${wrappedX}&y=${y}&z=${TILE_Z}`;
};

function TileLayer({camera}) {
  const leftWorld = camera.cx - WIDTH / 2 / camera.scale;
  const rightWorld = camera.cx + WIDTH / 2 / camera.scale;
  const topWorld = camera.cy - HEIGHT / 2 / camera.scale;
  const bottomWorld = camera.cy + HEIGHT / 2 / camera.scale;
  const minX = Math.floor(leftWorld / TILE_SIZE) - 1;
  const maxX = Math.floor(rightWorld / TILE_SIZE) + 1;
  const minY = Math.max(0, Math.floor(topWorld / TILE_SIZE) - 1);
  const maxY = Math.min(2 ** TILE_Z - 1, Math.floor(bottomWorld / TILE_SIZE) + 1);
  const tiles = [];

  for (let x = minX; x <= maxX; x += 1) {
    for (let y = minY; y <= maxY; y += 1) {
      const [left, top] = worldToScreen([x * TILE_SIZE, y * TILE_SIZE], camera);
      tiles.push({x, y, left, top});
    }
  }

  return tiles.map((tile) => (
    <Img
      key={`${tile.x}-${tile.y}`}
      src={tileUrl(tile.x, tile.y)}
      style={{
        position: 'absolute',
        left: tile.left,
        top: tile.top,
        width: TILE_SIZE * camera.scale + 1,
        height: TILE_SIZE * camera.scale + 1,
        objectFit: 'cover',
      }}
    />
  ));
}

const routeBoundsCamera = (coordinates) => {
  const worldPoints = coordinates.map((point) => lonLatToWorld(point));
  const bounds = worldPoints.reduce((acc, point) => ({
    minX: Math.min(acc.minX, point[0]),
    minY: Math.min(acc.minY, point[1]),
    maxX: Math.max(acc.maxX, point[0]),
    maxY: Math.max(acc.maxY, point[1]),
  }), {minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity});
  const width = Math.max(bounds.maxX - bounds.minX, 12);
  const height = Math.max(bounds.maxY - bounds.minY, 12);
  return {
    cx: (bounds.minX + bounds.maxX) / 2,
    cy: (bounds.minY + bounds.maxY) / 2,
    scale: clamp(Math.min(WIDTH / (width * 1.34), HEIGHT / (height * 1.36)), 0.38, 2.9),
  };
};

const pathUntil = (path, progress) => path.slice(0, Math.max(2, Math.floor(path.length * progress)));
const fmtDistance = (meters) => meters >= 1000 ? `${(meters / 1000).toFixed(1)} 公里` : `${Math.round(meters)} 米`;
const fmtDuration = (seconds) => seconds ? `约 ${Math.round(seconds / 60)} 分钟` : '';
const fmtCost = (cost) => cost ? `${cost} 元` : '';

function PathOverlay({routeSpec, currentIndex, localProgress, camera}) {
  return (
    <svg width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} style={{position: 'absolute', inset: 0}}>
      <rect width={WIDTH} height={HEIGHT} fill="rgba(243,247,248,0.2)" />
      {routeSpec.segments.map((segment, index) => {
        if (index > currentIndex) return null;
        const visible = index < currentIndex ? segment.path : pathUntil(segment.path, localProgress);
        const screenPoints = visible.map((point) => worldToScreen(lonLatToWorld(point), camera));
        const opacity = index < currentIndex ? 0.55 : 1;
        return (
          <g key={`${segment.from.name}-${segment.to.name}-${index}`} opacity={opacity}>
            <path d={pointsToPath(screenPoints)} fill="none" stroke="rgba(16,24,40,0.35)" strokeWidth="17" strokeLinecap="round" strokeLinejoin="round" />
            <path d={pointsToPath(screenPoints)} fill="none" stroke={segment.color || '#1d6fea'} strokeWidth={index < currentIndex ? 8 : 11} strokeLinecap="round" strokeLinejoin="round" />
          </g>
        );
      })}
      {routeSpec.segments.slice(0, currentIndex + 1).flatMap((segment, index) => [
        {...segment.from, key: `${index}-from`},
        {...segment.to, key: `${index}-to`},
      ]).map((place) => {
        const [x, y] = worldToScreen(lonLatToWorld(place.coordinates), camera);
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
        const [x, y] = worldToScreen(lonLatToWorld(coord), camera);
        return <circle cx={x} cy={y} r="15" fill={current.color || '#1d6fea'} stroke="#ffffff" strokeWidth="6" />;
      })()}
    </svg>
  );
}

function InfoPanel({routeSpec, currentIndex}) {
  const segment = routeSpec.segments[currentIndex];
  const details = [fmtDistance(segment.distanceMeters || 0), fmtDuration(segment.durationSeconds || 0), fmtCost(segment.cost || 0)].filter(Boolean).join(' · ');
  const previous = currentIndex > 0 ? `已完成 ${currentIndex} 段` : '第 1 段';
  return (
    <div style={{position: 'absolute', left: 56, top: 48, width: 600, padding: '28px 32px', borderRadius: 18, background: 'rgba(255,255,255,0.92)', boxShadow: '0 24px 80px rgba(16,24,40,0.18)'}}>
      <div style={{fontSize: 24, fontWeight: 800, color: segment.color || '#1d6fea', marginBottom: 10}}>{previous}</div>
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

export const framesPerSegment = FRAMES_PER_SEGMENT;

export function AmapSegmentedRouteVideo({routeSpec}) {
  const frame = useCurrentFrame();
  const segmentCount = routeSpec.segments.length;
  const currentIndex = clamp(Math.floor(frame / FRAMES_PER_SEGMENT), 0, segmentCount - 1);
  const localFrame = frame - currentIndex * FRAMES_PER_SEGMENT;
  const localProgress = clamp(interpolate(localFrame, [14, FRAMES_PER_SEGMENT - 20], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}), 0, 1);
  const currentSegment = routeSpec.segments[currentIndex];
  const camera = useMemo(() => routeBoundsCamera(currentSegment.path), [currentSegment]);

  return (
    <AbsoluteFill style={{backgroundColor: '#f3f6f8', fontFamily: 'Inter, Arial, "PingFang SC", "Microsoft YaHei", sans-serif'}}>
      <TileLayer camera={camera} />
      <PathOverlay routeSpec={routeSpec} currentIndex={currentIndex} localProgress={localProgress} camera={camera} />
      <InfoPanel routeSpec={routeSpec} currentIndex={currentIndex} />
      <div style={{position: 'absolute', right: 48, bottom: 36, fontSize: 22, color: 'rgba(23,32,51,0.62)', fontWeight: 700}}>{routeSpec.title}</div>
    </AbsoluteFill>
  );
}
