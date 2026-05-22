import { Icon } from '@iconify/react';
import { STATUS_CONFIG } from '../data/mockData';

export default function StatusBadge({ status, style }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.investigating;
  return (
    <div style={{
      padding: '4px 10px',
      border: `1px solid ${config.color}`,
      borderRadius: 'var(--radius-pill)',
      font: '500 11px/1 var(--font-body)',
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      color: config.color,
      ...style,
    }}>
      <Icon icon={config.icon} style={{ fontSize: 14 }} />
      {config.label}
    </div>
  );
}

export function PulseDot({ color }) {
  return (
    <span style={{
      width: 7,
      height: 7,
      borderRadius: '50%',
      background: color,
      boxShadow: `0 0 6px ${color}`,
      display: 'inline-block',
    }} />
  );
}

export function ConfidenceBadge({ confidence }) {
  const percent = Math.round(confidence * 100);
  const color = confidence >= 0.8
    ? 'var(--color-green)'
    : confidence >= 0.6
    ? 'var(--color-primary)'
    : 'var(--color-pink)';

  return (
    <div style={{
      padding: '4px 10px',
      border: `1px solid ${color}`,
      borderRadius: 'var(--radius-pill)',
      color,
      font: '500 11px/1 var(--font-mono)',
      display: 'flex',
      gap: 6,
    }}>
      <span style={{ fontVariantNumeric: 'tabular-nums' }}>{percent}%</span>
      <span style={{ fontWeight: 400, textTransform: 'uppercase', letterSpacing: '0.05em' }}>confidence</span>
    </div>
  );
}
