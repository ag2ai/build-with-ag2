import { useState, useEffect, useRef } from 'react';
import { Icon } from '@iconify/react';
import { useBackend, selectInvestigations } from '../live/backend';
import StatusBadge from '../components/StatusBadge';

export default function MonitoringPage({ onOpenInvestigation }) {
  const { state, inject, connected, simRunning, logs, now } = useBackend();
  const world = state.world;
  const investigations = selectInvestigations(state);
  const [cooling, setCooling] = useState({});

  // Inject: tell the backend to start the workflow. The backend owns the log
  // stream now, so it emits this incident's error lines itself (every client
  // sees them, and they survive reload). Per-incident cooldown guards runaways.
  const injectIncident = (inc) => {
    if (!simRunning || cooling[inc.key]) return;
    inject(inc.key);
    setCooling((c) => ({ ...c, [inc.key]: true }));
    setTimeout(() => setCooling((c) => ({ ...c, [inc.key]: false })), 2500);
  };

  return (
    <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
      <div style={{ width: 460, borderRight: '1px solid var(--color-border)', display: 'flex', flexDirection: 'column' }}>
        <InjectPanel
          systems={world.systems || []}
          incidents={world.incidents || []}
          connected={connected}
          simRunning={simRunning}
          cooling={cooling}
          onInject={injectIncident}
        />
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <LiveLogStream logs={logs} simRunning={simRunning} />
      </div>
      <div style={{ width: 400, borderLeft: '1px solid var(--color-border)', display: 'flex', flexDirection: 'column' }}>
        <LiveIncidents investigations={investigations} onOpenInvestigation={onOpenInvestigation} now={now} />
      </div>
    </div>
  );
}

function LiveLogStream({ logs, simRunning }) {
  const scrollRef = useRef(null);
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [logs]);

  const levelColors = { info: 'var(--color-text-muted)', warn: 'var(--color-primary)', error: 'var(--color-pink)' };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <PanelHeader title="Live Log Stream" subtitle="Regex log analysis · non-error lines are ambient" />
      <div ref={scrollRef} style={{ flex: 1, overflow: 'auto', padding: '12px 20px', fontFamily: 'var(--font-mono)', fontSize: '11px', lineHeight: 1.6 }}>
        {!simRunning && logs.length === 0 && (
          <div style={{ fontFamily: 'var(--font-body)', font: '400 12px/1.6 var(--font-body)', color: 'var(--color-text-muted)' }}>
            Simulation stopped. Press <strong style={{ color: 'var(--color-green)' }}>Start Simulation</strong> (top right) to stream logs.
          </div>
        )}
        {logs.map((log, i) => {
          const t = new Date(log.time);
          const ts = `${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}:${String(t.getSeconds()).padStart(2, '0')}`;
          return (
            <div key={i} style={{ marginBottom: 4, display: 'flex', gap: 8 }}>
              <span style={{ color: 'var(--color-text-muted)', flexShrink: 0 }}>{ts}</span>
              <span style={{ color: levelColors[log.level], flexShrink: 0, textTransform: 'uppercase', width: 40 }}>{log.level}</span>
              <span style={{ color: 'var(--color-blue)', flexShrink: 0 }}>{log.service}</span>
              <span style={{ color: log.level === 'error' ? 'var(--color-pink)' : 'var(--color-text-body)' }}>{log.message}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function InjectPanel({ systems, incidents, connected, simRunning, cooling, onInject }) {
  const pulse = { healthy: 'var(--color-green)', degraded: 'var(--color-primary)', critical: 'var(--color-pink)' };
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <PanelHeader
        title="Monitored Systems"
        subtitle="Inject an incident to open a ticket and start a diagnosis workflow"
        right={(
          <span style={{ display: 'flex', alignItems: 'center', gap: 6, font: '400 11px/1 var(--font-mono)', color: connected ? 'var(--color-green)' : 'var(--color-pink)' }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: connected ? 'var(--color-green)' : 'var(--color-pink)' }} />
            {connected ? 'backend connected' : 'backend offline'}
          </span>
        )}
      />
      <div style={{ flex: 1, overflow: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {!simRunning && (
          <div style={{
            padding: '10px 14px',
            border: '1px dashed var(--color-green)',
            background: 'rgba(155,255,163,0.07)',
            borderRadius: 'var(--radius-md)',
            font: '400 12px/1.5 var(--font-body)',
            color: 'var(--color-text-body)',
          }}>
            Press <strong style={{ color: 'var(--color-green)' }}>Start Simulation</strong> (top right) to go live —
            logs begin streaming and incident injection is enabled.
          </div>
        )}
        {systems.map((sys) => {
          const sysIncidents = incidents.filter((inc) => inc.system === sys.id);
          return (
            <div key={sys.id} style={{ padding: 14, background: 'var(--color-surface-subtle)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: sysIncidents.length ? 12 : 0 }}>
                <span style={{ font: '600 13px/1 var(--font-mono)', color: 'var(--color-text-primary)' }}>{sys.id}</span>
                <span style={{ font: '400 10px/1 var(--font-mono)', color: 'var(--color-text-muted)', textTransform: 'uppercase', padding: '2px 7px', background: 'var(--color-page-bg)', borderRadius: 'var(--radius-sm)' }}>{sys.kind}</span>
                <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6, font: '400 11px/1 var(--font-body)', color: 'var(--color-text-muted)' }}>
                  <span style={{ width: 7, height: 7, borderRadius: '50%', background: pulse[sys.status] || 'var(--color-text-muted)' }} />
                  {sys.status}
                </span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {sysIncidents.map((inc) => {
                  const isCooling = !!cooling[inc.key];
                  const enabled = connected && simRunning && !isCooling;
                  return (
                    <button
                      key={inc.key}
                      onClick={() => onInject(inc)}
                      disabled={!enabled}
                      style={{
                        padding: '6px 12px',
                        background: 'transparent',
                        border: '1px solid var(--color-pink)',
                        borderRadius: 'var(--radius-pill)',
                        color: 'var(--color-pink)',
                        font: '500 12px/1 var(--font-body)',
                        cursor: enabled ? 'pointer' : 'not-allowed',
                        opacity: enabled ? 1 : 0.4,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                      }}
                    >
                      <Icon icon="fluent:flash-24-regular" style={{ fontSize: 14 }} />
                      {isCooling ? 'Injected — cooling…' : `Inject: ${inc.title}`}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
        {systems.length === 0 && (
          <div style={{ color: 'var(--color-text-muted)', font: '400 13px/1.5 var(--font-body)' }}>
            Waiting for the backend (GET /world)…
          </div>
        )}
      </div>
    </div>
  );
}

function LiveIncidents({ investigations, onOpenInvestigation, now }) {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <PanelHeader title="Live Incidents" subtitle={`${investigations.length} total`} />
      <div style={{ flex: 1, overflow: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {investigations.length === 0 && (
          <div style={{ color: 'var(--color-text-muted)', font: '400 12px/1.5 var(--font-body)' }}>
            No incidents yet — inject one to see it appear here and flow through the workflows.
          </div>
        )}
        {investigations.map((inv) => {
          const mins = Math.floor((now - inv.opened) / 60000);
          const secs = Math.floor(((now - inv.opened) % 60000) / 1000);
          const timeStr = mins > 0 ? `${mins}m ago` : `${secs}s ago`;
          return (
            <button
              key={inv.id}
              onClick={() => onOpenInvestigation(inv.id)}
              style={{
                textAlign: 'left',
                padding: 12,
                background: 'var(--color-surface-subtle)',
                border: `1px solid ${inv.needsHuman ? 'var(--color-pink)' : 'var(--color-border)'}`,
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <span style={{ font: '600 12px/1 var(--font-mono)', color: 'var(--color-primary)' }}>{inv.id}</span>
                <span style={{ marginLeft: 'auto', font: '400 10px/1 var(--font-mono)', color: 'var(--color-text-muted)' }}>{timeStr}</span>
              </div>
              <div style={{ font: '400 12px/1.4 var(--font-body)', color: 'var(--color-text-body)', marginBottom: 8 }}>{inv.title}</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <StatusBadge status={inv.status} />
                {inv.needsHuman && (
                  <span style={{
                    display: 'flex', alignItems: 'center', gap: 4,
                    padding: '3px 8px', borderRadius: 'var(--radius-pill)',
                    border: '1px solid var(--color-pink)', color: 'var(--color-pink)',
                    font: '600 10px/1 var(--font-body)',
                  }}>
                    <Icon icon="fluent:person-feedback-24-filled" style={{ fontSize: 12 }} /> input needed
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function PanelHeader({ title, subtitle, right }) {
  return (
    <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
      <div>
        <h3 style={{ font: '500 14px/1 var(--font-body)', color: 'var(--color-text-primary)', marginBottom: subtitle ? 4 : 0 }}>{title}</h3>
        {subtitle && <span style={{ font: '400 11px/1 var(--font-mono)', color: 'var(--color-text-muted)' }}>{subtitle}</span>}
      </div>
      {right}
    </div>
  );
}
