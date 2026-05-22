import { Icon } from '@iconify/react';
import Markdown from './Markdown';

function ActionHistoryList({ history }) {
  return (
    <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: 16 }}>
      <div style={{
        font: '600 11px/1 var(--font-body)',
        color: 'var(--color-text-muted)',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        marginBottom: 12,
      }}>Action History</div>
      {history.map((h, i) => (
        <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 10, font: '400 11px/1.3 var(--font-body)' }}>
          <span style={{
            color: 'var(--color-text-muted)',
            fontFamily: 'var(--font-mono)',
            flexShrink: 0,
            fontVariantNumeric: 'tabular-nums',
          }}>
            {new Date(h.time).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </span>
          <span style={{ color: 'var(--color-blue)', fontWeight: 600, flexShrink: 0 }}>{h.user}</span>
          <Markdown style={{ color: 'var(--color-text-body)', flex: 1, minWidth: 0 }}>{h.text}</Markdown>
        </div>
      ))}
    </div>
  );
}

export default function HITLPanel({ request, history, onApprove, onDefer, onReject }) {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-border)', flexShrink: 0 }}>
        <h3 style={{ font: '500 14px/1 var(--font-body)', color: 'var(--color-text-primary)' }}>
          Human in the Loop
        </h3>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
        {request.status === 'pending' && (
          <div style={{
            padding: '16px',
            background: 'rgba(213,155,255,0.1)',
            border: '1px solid rgba(213,155,255,0.4)',
            borderRadius: 'var(--radius-md)',
            marginBottom: 16,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <Icon icon="fluent:person-feedback-24-regular" style={{ fontSize: 18, color: 'var(--color-pink)' }} />
              <span style={{
                font: '600 10px/1 var(--font-mono)',
                color: 'var(--color-pink)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}>DECISION REQUIRED</span>
            </div>
            <div style={{ font: '500 15px/1.3 var(--font-body)', color: 'var(--color-text-primary)', marginBottom: 4 }}>
              {request.agent}
            </div>
            <Markdown style={{ font: '400 13px/1.5 var(--font-body)', color: 'var(--color-text-body)', marginBottom: 16 }}>
              {request.question}
            </Markdown>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <DecisionButton
                onClick={onApprove}
                icon="fluent:checkmark-24-regular"
                label={request.options[0]}
                filled
                color="var(--color-green)"
              />
              <DecisionButton
                onClick={onDefer}
                icon="fluent:clock-24-regular"
                label={request.options[1]}
                color="var(--color-primary)"
              />
              <DecisionButton
                onClick={onReject}
                icon="fluent:dismiss-24-regular"
                label={request.options[2]}
                color="var(--color-pink)"
              />
            </div>
          </div>
        )}

        {request.status === 'approved' && (
          <StatusCard
            icon="fluent:checkmark-circle-24-regular"
            color="var(--color-green)"
            bg="rgba(155,255,163,0.1)"
            border="rgba(155,255,163,0.4)"
            label="APPROVED"
            text="Disruptive remediation approved — fixers proceeding."
          />
        )}

        {request.status === 'deferred' && (
          <StatusCard
            icon="fluent:clock-24-regular"
            color="var(--color-primary)"
            bg="rgba(243,255,155,0.1)"
            border="rgba(243,255,155,0.4)"
            label="DEFERRED"
            text="Disruptive step held for the next maintenance window; non-disruptive fixes stand."
          />
        )}

        {request.status === 'rejected' && (
          <StatusCard
            icon="fluent:dismiss-circle-24-regular"
            color="var(--color-pink)"
            bg="rgba(213,155,255,0.1)"
            border="rgba(213,155,255,0.4)"
            label="REJECTED"
            text="Remediation rejected — escalated for a human-led follow-up."
          />
        )}

        <ActionHistoryList history={history} />
      </div>
    </div>
  );
}

function DecisionButton({ onClick, icon, label, color, filled }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '10px 16px',
        borderRadius: 'var(--radius-pill)',
        font: '500 13px/1 var(--font-body)',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 6,
        border: filled ? 'none' : `1px solid ${color}`,
        background: filled ? color : 'transparent',
        color: filled ? '#1D1C1B' : color,
        boxShadow: filled ? 'inset 0 2px 12px rgba(255,255,255,0.25)' : 'none',
      }}
    >
      <Icon icon={icon} style={{ fontSize: 16 }} />
      {label}
    </button>
  );
}

function StatusCard({ icon, color, bg, border, label, text }) {
  return (
    <div style={{
      padding: '16px',
      background: bg,
      border: `1px solid ${border}`,
      borderRadius: 'var(--radius-md)',
      marginBottom: 16,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <Icon icon={icon} style={{ fontSize: 18, color }} />
        <span style={{
          font: '600 10px/1 var(--font-mono)',
          color,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}>{label}</span>
      </div>
      <div style={{ font: '400 13px/1.5 var(--font-body)', color: 'var(--color-text-body)' }}>{text}</div>
    </div>
  );
}

export function ActionHistory({ history }) {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-border)', flexShrink: 0 }}>
        <h3 style={{ font: '500 14px/1 var(--font-body)', color: 'var(--color-text-primary)' }}>
          Action History
        </h3>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
        <ActionHistoryList history={history} />
      </div>
    </div>
  );
}
