import { useState } from 'react';
import { Icon } from '@iconify/react';
import { SEVERITY_CONFIG } from '../data/mockData';
import StatusBadge from '../components/StatusBadge';
import { useBackend, selectInvestigations } from '../live/backend';
import { ACTIVE_STATUSES, RESOLVED_STATUSES } from '../live/mappers';

export default function DashboardPage({ onOpenInvestigation }) {
  const { state, now } = useBackend();
  const investigations = selectInvestigations(state);
  const [filter, setFilter] = useState('all');

  const filtered = investigations.filter((inv) => {
    if (filter === 'all') return true;
    if (filter === 'active') return ACTIVE_STATUSES.includes(inv.status);
    if (filter === 'resolved') return RESOLVED_STATUSES.includes(inv.status);
    return true;
  });

  const counts = {
    all: investigations.length,
    active: investigations.filter((i) => ACTIVE_STATUSES.includes(i.status)).length,
    resolved: investigations.filter((i) => RESOLVED_STATUSES.includes(i.status)).length,
  };

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Filter bar */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid var(--color-border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', gap: 8 }}>
          {[
            { id: 'all', label: 'All Investigations', count: counts.all },
            { id: 'active', label: 'Active', count: counts.active },
            { id: 'resolved', label: 'Resolved', count: counts.resolved },
          ].map((f) => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              style={{
                padding: '8px 16px',
                background: filter === f.id ? 'rgba(243,255,155,0.1)' : 'transparent',
                border: filter === f.id ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
                borderRadius: 'var(--radius-pill)',
                color: filter === f.id ? 'var(--color-primary)' : 'var(--color-text-muted)',
                font: '500 13px/1 var(--font-body)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                transition: 'all 150ms ease-out',
              }}
            >
              {f.label}
              <span style={{
                padding: '2px 6px',
                background: 'var(--color-surface-subtle)',
                borderRadius: 'var(--radius-sm)',
                font: '500 11px/1 var(--font-mono)',
              }}>{f.count}</span>
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, font: '400 12px/1 var(--font-body)', color: 'var(--color-text-muted)' }}>
          <Icon icon="fluent:brain-circuit-24-regular" style={{ fontSize: 16, color: 'var(--color-blue)' }} />
          <span>Live — diagnosis &amp; remediation workflows</span>
        </div>
      </div>

      {/* Table header */}
      <div style={{
        display: 'flex',
        padding: '12px 20px',
        borderBottom: '1px solid var(--color-border)',
        background: 'var(--color-surface-subtle)',
        font: '600 11px/1 var(--font-body)',
        color: 'var(--color-text-muted)',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        flexShrink: 0,
      }}>
        <div style={{ width: 180 }}>Incident</div>
        <div style={{ flex: 1 }}>Title / Service</div>
        <div style={{ width: 140 }}>Status</div>
        <div style={{ width: 120 }}>Severity</div>
        <div style={{ width: 140 }}>Opened</div>
        <div style={{ width: 100 }}>Time to RCA</div>
        <div style={{ width: 180 }}>Outcome</div>
      </div>

      {/* Rows */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {filtered.length === 0 ? (
          <div style={{ padding: '48px 20px', textAlign: 'center', color: 'var(--color-text-muted)', font: '400 13px/1.5 var(--font-body)' }}>
            No investigations yet — inject an incident from the <strong>Monitoring</strong> tab.
          </div>
        ) : (
          filtered.map((inv) => (
            <InvestigationRow key={inv.id} investigation={inv} now={now} onClick={() => onOpenInvestigation(inv.id)} />
          ))
        )}
      </div>
    </div>
  );
}

function InvestigationRow({ investigation, onClick, now }) {
  const severity = SEVERITY_CONFIG[investigation.severity] || SEVERITY_CONFIG.warning;

  const elapsed = now - investigation.opened;
  const hours = Math.floor(elapsed / 3600000);
  const mins = Math.floor((elapsed % 3600000) / 60000);
  const secs = Math.floor((elapsed % 60000) / 1000);
  const timeStr = hours > 0 ? `${hours}h ${mins}m ago` : mins > 0 ? `${mins}m ago` : `${secs}s ago`;
  const rcaTime = investigation.timeToRCA != null
    ? `${Math.floor(investigation.timeToRCA / 60)}m ${investigation.timeToRCA % 60}s`
    : '—';
  const outcome = investigation.resolution || (investigation.parent ? `⊃ duplicate of ${investigation.parent}` : (investigation.rca || '—'));

  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex',
        padding: '16px 20px',
        borderBottom: '1px solid var(--color-border)',
        borderLeft: `3px solid ${investigation.needsHuman ? 'var(--color-pink)' : 'transparent'}`,
        cursor: 'pointer',
        transition: 'background 150ms ease-out',
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--color-surface-subtle)')}
      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
    >
      <div style={{ width: 180, display: 'flex', alignItems: 'center' }}>
        <span style={{ font: '600 13px/1 var(--font-mono)', color: 'var(--color-primary)' }}>
          {investigation.id}
        </span>
      </div>
      <div style={{ flex: 1, display: 'flex', alignItems: 'center' }}>
        <div>
          <div style={{ font: '500 13px/1.2 var(--font-body)', color: 'var(--color-text-primary)', marginBottom: 4 }}>
            {investigation.title}
          </div>
          <div style={{ font: '400 12px/1 var(--font-mono)', color: 'var(--color-text-muted)' }}>
            {investigation.service}
          </div>
        </div>
      </div>
      <div style={{ width: 140, display: 'flex', alignItems: 'center', gap: 6 }}>
        <StatusBadge status={investigation.status} />
        {investigation.needsHuman && (
          <Icon
            icon="fluent:person-feedback-24-filled"
            title={investigation.humanPrompt || 'Awaiting human input'}
            style={{ fontSize: 16, color: 'var(--color-pink)' }}
          />
        )}
      </div>
      <div style={{ width: 120, display: 'flex', alignItems: 'center' }}>
        <div style={{ font: '600 11px/1 var(--font-body)', textTransform: 'uppercase', letterSpacing: '0.05em', color: severity.color }}>
          {severity.label}
        </div>
      </div>
      <div style={{ width: 140, display: 'flex', alignItems: 'center' }}>
        <div style={{ font: '400 12px/1 var(--font-mono)', color: 'var(--color-text-body)', fontVariantNumeric: 'tabular-nums' }}>
          {timeStr}
        </div>
      </div>
      <div style={{ width: 100, display: 'flex', alignItems: 'center' }}>
        <div style={{ font: '400 12px/1 var(--font-mono)', color: 'var(--color-text-body)', fontVariantNumeric: 'tabular-nums' }}>
          {rcaTime}
        </div>
      </div>
      <div style={{ width: 180, display: 'flex', alignItems: 'center' }}>
        <div style={{ font: '400 12px/1.3 var(--font-body)', color: 'var(--color-text-muted)', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
          {outcome}
        </div>
      </div>
    </div>
  );
}
