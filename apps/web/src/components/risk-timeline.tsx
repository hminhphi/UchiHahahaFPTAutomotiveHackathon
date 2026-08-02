export interface TimelineEvent {
  frameIndex?: number;
  time: string;
  label: string;
  detail: string;
  severity: number;
}

export function RiskTimeline({ events }: { events: TimelineEvent[] }) {
  return (
    <section className="panel timeline-panel">
      <div className="panel-heading">
        <span className="eyebrow">Synchronized evidence</span>
        <h2>Risk timeline</h2>
      </div>
      <div className="timeline-track">
        {events.length ? events.map((event) => (
          <article className="timeline-event" key={`${event.time}-${event.label}`}>
            <span className={`event-dot severity-${event.severity}`} />
            <time>{event.time}</time>
            <div>
              <strong>{event.label}</strong>
              <p>{event.detail}</p>
            </div>
          </article>
        )) : <p className="empty-evidence">No frame-level evidence was produced for this trip.</p>}
      </div>
    </section>
  );
}
