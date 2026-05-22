import { Icon } from '@iconify/react';
import mascot1 from '../assets/mascot-1.png';
import mascot2 from '../assets/mascot-2.png';
import mascot3 from '../assets/mascot-3.png';
import mascot4 from '../assets/mascot-4.png';
import mascot5 from '../assets/mascot-5.png';

const MASCOTS = [mascot1, mascot2, mascot3, mascot4, mascot5];

function AgentLane({ agent, index, maxTime }) {
  const isBlocked = agent.status === 'blocked';
  const isRunning = agent.status === 'running';
  const isCompleted = agent.status === 'completed';

  const startPct = (agent.startTime / maxTime) * 100;
  const durPct = agent.duration ? (agent.duration / maxTime) * 100 : 30;

  let bgColor, borderColor, statusColor, statusText;
  if (isBlocked) {
    bgColor = 'rgba(213,155,255,0.1)';
    borderColor = 'rgba(213,155,255,0.4)';
    statusColor = 'var(--color-pink)';
    statusText = 'blocked';
  } else if (isRunning) {
    bgColor = 'rgba(155,221,255,0.15)';
    borderColor = 'rgba(155,221,255,0.4)';
    statusColor = 'var(--color-blue)';
    statusText = 'running';
  } else {
    bgColor = 'rgba(155,255,163,0.15)';
    borderColor = 'rgba(155,255,163,0.4)';
    statusColor = 'var(--color-green)';
    statusText = 'completed';
  }

  return (
    <div style={{ marginBottom: 20, position: 'relative' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <img
            src={MASCOTS[index % 5]}
            style={{ width: 20, height: 20, imageRendering: 'pixelated' }}
            alt=""
          />
          <span style={{ font: '500 13px/1 var(--font-body)', color: 'var(--color-text-primary)' }}>
            {agent.name}
          </span>
        </div>
        <span style={{
          font: '500 10px/1 var(--font-mono)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          color: statusColor,
        }}>{statusText}</span>
      </div>

      <div style={{
        height: 36,
        background: 'var(--color-surface-subtle)',
        borderRadius: 'var(--radius-md)',
        padding: 4,
        position: 'relative',
      }}>
        <div style={{
          height: '100%',
          width: `${durPct}%`,
          marginLeft: `${startPct}%`,
          borderRadius: 'var(--radius-sm)',
          background: bgColor,
          border: isBlocked ? `1px dashed ${borderColor}` : `1px solid ${borderColor}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 8px',
          transition: 'width 500ms ease-out',
        }}>
          {(agent.findings != null || agent.actions != null) && (
            <span style={{ font: '600 11px/1 var(--font-mono)', color: 'var(--color-text-primary)' }}>
              {agent.findings ?? agent.actions}
            </span>
          )}
          {isCompleted && agent.duration && (
            <span style={{ font: '400 10px/1 var(--font-mono)', color: 'var(--color-text-muted)' }}>
              {agent.duration}s
            </span>
          )}
          {isBlocked && (
            <Icon icon="fluent:error-circle-24-filled" style={{ fontSize: 14, color: 'var(--color-pink)' }} />
          )}
        </div>
      </div>

      {isBlocked && agent.hitlReason && (
        <div style={{
          marginTop: 6,
          font: '400 11px/1.3 var(--font-body)',
          color: 'var(--color-pink)',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
        }}>
          <Icon icon="fluent:person-feedback-24-regular" style={{ fontSize: 12 }} />
          {agent.hitlReason}
        </div>
      )}
    </div>
  );
}

export default function AgentTrace({ agents, title }) {
  const maxTime = Math.max(1, ...agents.map(a => a.startTime + (a.duration || 0)));

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-border)', flexShrink: 0 }}>
        <h3 style={{ font: '500 14px/1 var(--font-body)', color: 'var(--color-text-primary)', marginBottom: 4 }}>
          {title}
        </h3>
        <span style={{ font: '400 11px/1 var(--font-body)', color: 'var(--color-text-muted)' }}>
          Parallel execution timeline
        </span>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
        {agents.map((agent, i) => (
          <AgentLane key={agent.id} agent={agent} index={i} maxTime={maxTime} />
        ))}
      </div>
    </div>
  );
}
