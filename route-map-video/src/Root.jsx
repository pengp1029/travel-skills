import React from 'react';
import {Composition} from 'remotion';
import {RouteMapVideo} from './components/RouteMapVideo.jsx';

const defaultSpec = {
  title: 'Route Map Video',
  width: 1920,
  height: 1080,
  durationSeconds: 10,
  segments: [
    {
      mode: 'train',
      preferredVehicle: 'train',
      label: '高铁',
      color: '#16a34a',
      from: {name: '上海', coordinates: [121.4737, 31.2304]},
      to: {name: '北京', coordinates: [116.4074, 39.9042]},
      path: [[121.4737, 31.2304], [118.7969, 32.0603], [116.9971, 36.6512], [116.4074, 39.9042]],
      distanceMeters: 1318000,
      durationSeconds: 18000,
      cost: 553,
      steps: [{mode: '高铁', text: '沿跨城路线前进'}],
    },
  ],
};

export function Root() {
  const width = Number(process.env.ROUTE_VIDEO_WIDTH || 1920);
  const height = Number(process.env.ROUTE_VIDEO_HEIGHT || 1080);
  const durationSeconds = Number(process.env.ROUTE_VIDEO_DURATION || defaultSpec.durationSeconds);
  return (
    <Composition
      id="RouteMapVideo"
      component={RouteMapVideo}
      durationInFrames={Math.max(30, Math.round(durationSeconds * 30))}
      fps={30}
      width={width}
      height={height}
      defaultProps={{routeSpec: {...defaultSpec, width, height, durationSeconds}}}
    />
  );
}
