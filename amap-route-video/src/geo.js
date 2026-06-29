export const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

export const lerp = (from, to, progress) => from + (to - from) * progress;

export const lerpPoint = (from, to, progress) => [
  lerp(from[0], to[0], progress),
  lerp(from[1], to[1], progress),
];

export const pointAtProgress = (coordinates, progress) => {
  if (coordinates.length < 2) {
    return coordinates[0] || [0, 0];
  }
  const index = clamp(Math.floor(progress * (coordinates.length - 1)), 0, coordinates.length - 2);
  const local = progress * (coordinates.length - 1) - index;
  return lerpPoint(coordinates[index], coordinates[index + 1], local);
};
