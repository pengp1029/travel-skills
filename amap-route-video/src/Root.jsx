import React from 'react';
import {Composition} from 'remotion';
import {AmapSegmentedRouteVideo, framesPerSegment} from './components/AmapSegmentedRouteVideo.jsx';
import {generatedRouteSpec} from './route/generatedRouteSpec.js';

export function Root() {
  return (
    <Composition
      id="AmapSegmentedRouteVideo"
      component={AmapSegmentedRouteVideo}
      durationInFrames={Math.max(1, generatedRouteSpec.segments.length) * framesPerSegment}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{routeSpec: generatedRouteSpec}}
    />
  );
}
