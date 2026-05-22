import { Icon } from '@iconify/react';
import { ConfidenceBadge } from './StatusBadge';
import Markdown from './Markdown';

export default function RCASynthesis({ rca, locked = false }) {
  return (
    <div style={{ borderBottom: '1px solid var(--color-border)', flexShrink: 0 }}>
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid var(--color-border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <h3 style={{ font: '500 14px/1 var(--font-body)', color: 'var(--color-text-primary)' }}>
            Root Cause Analysis
          </h3>
          {locked && (
            <Icon
              icon="fluent:lock-closed-24-filled"
              style={{ fontSize: 14, color: 'var(--color-text-muted)' }}
              title="RCA complete — read-only"
            />
          )}
        </div>
        <ConfidenceBadge confidence={rca.confidence} />
      </div>

      <div style={{ padding: '16px 20px', maxHeight: 320, overflow: 'auto', opacity: locked ? 0.8 : 1 }}>
        <Section icon="fluent:pulse-24-regular" label="Symptoms">
          <div style={{ font: '400 12px/1.5 var(--font-body)', color: 'var(--color-text-body)' }}>
            {rca.symptoms.map((s, i) => <Markdown key={i} style={{ marginBottom: 8 }}>{s}</Markdown>)}
          </div>
        </Section>

        <Section icon="fluent:arrow-trending-lines-24-regular" label="Contributing Factors">
          <div style={{ font: '400 12px/1.5 var(--font-body)', color: 'var(--color-text-body)' }}>
            {rca.factors.map((f, i) => <Markdown key={i} style={{ marginBottom: 4 }}>{`- ${f}`}</Markdown>)}
          </div>
        </Section>

        <Section icon="fluent:lightbulb-24-regular" label="Probable Root Cause">
          <Markdown style={{
            padding: '12px',
            background: 'rgba(155,255,163,0.05)',
            border: '1px solid rgba(155,255,163,0.2)',
            borderRadius: 'var(--radius-md)',
            font: '400 13px/1.5 var(--font-body)',
            color: 'var(--color-text-body)',
          }}>{rca.rootCause}</Markdown>
        </Section>
      </div>
    </div>
  );
}

function Section({ icon, label, children }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{
        font: '600 11px/1 var(--font-body)',
        color: 'var(--color-primary)',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        marginBottom: 8,
        display: 'flex',
        alignItems: 'center',
        gap: 6,
      }}>
        <Icon icon={icon} style={{ fontSize: 14 }} />
        {label}
      </div>
      {children}
    </div>
  );
}
