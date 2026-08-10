"use client";

import type { TrajectoryPoint, TripTrajectory } from "@/lib/contracts";
import type { TripEvidence } from "@/lib/trip-evidence";

const PLOT_WIDTH = 760;
const PLOT_HEIGHT = 332;
const PLOT_PADDING = 28;

export function TripTrajectory({
  trajectory,
  currentFrameIndex = null,
  events = [],
}: {
  trajectory: TripTrajectory | null;
  currentFrameIndex?: number | null;
  events?: TripEvidence[];
}) {
  if (!trajectory || trajectory.points.length < 2) {
    return (
      <article className="panel trajectory-panel trajectory-empty">
        <span className="eyebrow">Telemetry route</span>
        <h2>Trajectory unavailable</h2>
        <p>The replay remains available while the historical trip telemetry is loading.</p>
      </article>
    );
  }

  const projection = createProjection(trajectory.points);
  const domain = speedDomain(trajectory.points);
  const midpoint = (domain.min + domain.max) / 2;
  const start = trajectory.points[0];
  const end = trajectory.points[trajectory.points.length - 1];
  const currentPoint = currentFrameIndex === null ? null : findTrajectoryPoint(trajectory.points, currentFrameIndex);

  return (
    <article className="panel trajectory-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Telemetry route</span>
          <h2>Speed-coloured trip trajectory</h2>
        </div>
        <span className="trajectory-distance">{formatDistance(trajectory.distanceM)} route</span>
      </div>
      <div className="trajectory-layout">
        <div className="trajectory-plot" aria-label={`Trip trajectory coloured from blue at ${formatScaleSpeed(domain.min)} to red at ${formatScaleSpeed(domain.max)} km/h`}>
          <svg viewBox={`0 0 ${PLOT_WIDTH} ${PLOT_HEIGHT}`} role="img" aria-labelledby="trajectory-title trajectory-description">
            <title id="trajectory-title">Trip route coloured by speed</title>
            <desc id="trajectory-description">Each route segment uses recorded world position. Colour is scaled from five kilometres per hour below this trip&apos;s minimum to five above its maximum.</desc>
            <rect className="trajectory-background" x="0" y="0" width={PLOT_WIDTH} height={PLOT_HEIGHT} rx="12" />
            <path className="trajectory-grid" d={`M ${PLOT_PADDING} 92 H ${PLOT_WIDTH - PLOT_PADDING} M ${PLOT_PADDING} 166 H ${PLOT_WIDTH - PLOT_PADDING} M ${PLOT_PADDING} 240 H ${PLOT_WIDTH - PLOT_PADDING}`} />
            {trajectory.points.slice(1).map((point, index) => {
              const previous = trajectory.points[index];
              const from = projection(previous);
              const to = projection(point);
              return <line className="trajectory-segment" key={point.frameIndex} x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke={speedColor(point.speedKmh, domain)} />;
            })}
            <circle className="trajectory-start" cx={projection(start).x} cy={projection(start).y} r="6" />
            <circle className="trajectory-end" cx={projection(end).x} cy={projection(end).y} r="6" />
            {events.map((event) => {
              const eventPoint = findTrajectoryPoint(trajectory.points, event.frameIndex);
              const position = projection(eventPoint);
              return (
                <g key={`${event.label}-${event.frameIndex}`} className={`trajectory-event severity-${event.severity}`} aria-label={`Risk event: ${event.label} at frame ${event.frameIndex}`} transform={`translate(${position.x} ${position.y})`}>
                  <circle r="8" />
                  <path d="M -3 -3 L 3 3 M 3 -3 L -3 3" />
                </g>
              );
            })}
            {currentPoint ? <CurrentVehicle point={currentPoint} projection={projection} /> : null}
          </svg>
          <div className="trajectory-legend" aria-label="Speed legend">
            <span>{formatScaleSpeed(domain.min)}</span><i /><span>{formatScaleSpeed(midpoint)}</span><span>{formatScaleSpeed(domain.max)} km/h</span>
          </div>
        </div>
        <div className="trajectory-summary">
          <Metric label="Replay frame" value={currentPoint ? `${currentPoint.frameIndex} / ${end.frameIndex}` : "Waiting"} />
          <Metric label="Current speed" value={currentPoint ? `${currentPoint.speedKmh.toFixed(0)} km/h` : "-- km/h"} />
          <Metric label="Peak speed" value={`${trajectory.maxSpeedKmh.toFixed(0)} km/h`} />
          <Metric label="Peak lateral accel" value={`${trajectory.maxLateralAccelMps2.toFixed(1)} m/s2`} />
          <div className="route-key"><span className="route-key-start" />Start</div>
          <div className="route-key"><span className="route-key-end" />End</div>
          <p>Geometry uses recorded vehicle position. Acceleration marks handling context without accumulated integration drift.</p>
        </div>
      </div>
    </article>
  );
}

function CurrentVehicle({
  point,
  projection,
}: {
  point: TrajectoryPoint;
  projection: (point: TrajectoryPoint) => { x: number; y: number };
}) {
  const position = projection(point);
  return (
    <g className="trajectory-current-vehicle" transform={`translate(${position.x} ${position.y})`}>
      <title>{`Current vehicle position: frame ${point.frameIndex}, ${point.speedKmh.toFixed(1)} km/h`}</title>
      <circle r="12" />
      <path d="M -5 -3 H 5 L 7 2 V 5 H -7 V 2 Z M -4 5 V 7 M 4 5 V 7" />
      <text y="-18" textAnchor="middle">NOW</text>
    </g>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="trajectory-metric"><span>{label}</span><strong>{value}</strong></div>;
}

function createProjection(points: TrajectoryPoint[]) {
  const xValues = points.map((point) => point.xM);
  const yValues = points.map((point) => point.yM);
  const minX = Math.min(...xValues);
  const maxX = Math.max(...xValues);
  const minY = Math.min(...yValues);
  const maxY = Math.max(...yValues);
  const rangeX = Math.max(maxX - minX, 1);
  const rangeY = Math.max(maxY - minY, 1);
  const innerWidth = PLOT_WIDTH - PLOT_PADDING * 2;
  const innerHeight = PLOT_HEIGHT - PLOT_PADDING * 2;
  const scale = Math.min(innerWidth / rangeX, innerHeight / rangeY);
  const offsetX = PLOT_PADDING + (innerWidth - rangeX * scale) / 2;
  const offsetY = PLOT_PADDING + (innerHeight - rangeY * scale) / 2;
  return (point: TrajectoryPoint) => ({
    x: offsetX + (point.xM - minX) * scale,
    y: offsetY + (point.yM - minY) * scale,
  });
}

export function findTrajectoryPoint(points: TrajectoryPoint[], frameIndex: number) {
  let nearest = points[0];
  for (const point of points) {
    if (point.frameIndex > frameIndex) return nearest;
    nearest = point;
  }
  return nearest;
}

export function speedDomain(points: readonly Pick<TrajectoryPoint, "speedKmh">[]) {
  const speeds = points.map((point) => point.speedKmh);
  return { min: Math.min(...speeds) - 5, max: Math.max(...speeds) + 5 };
}

function speedColor(speedKmh: number, domain: { min: number; max: number }) {
  const progress = Math.max(0, Math.min(1, (speedKmh - domain.min) / (domain.max - domain.min)));
  return `hsl(${220 - progress * 220} 82% 49%)`;
}

function formatScaleSpeed(speedKmh: number) {
  return speedKmh.toFixed(0);
}

function formatDistance(distanceM: number) {
  return distanceM >= 1000 ? `${(distanceM / 1000).toFixed(2)} km` : `${distanceM.toFixed(0)} m`;
}