import logo from '../assets/ag2-logo-white.svg';
import { Icon } from '@iconify/react';

export default function TitleBar({ center, right }) {
  return (
    <header style={{
      height: 56,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 20px',
      borderBottom: '1px solid var(--color-border)',
      background: 'var(--color-page-bg)',
      flexShrink: 0,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <img src={logo} style={{ height: 20, marginRight: 18 }} alt="AG2" />
        <span style={{ color: 'rgba(255,255,255,0.2)' }}>|</span>
        <span style={{ font: '400 13px/1 var(--font-body)', color: 'var(--color-text-muted)' }}>
          Ops Triage Design
        </span>
      </div>

      {center && <div style={{ display: 'flex' }}>{center}</div>}

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {right}
        <button style={{
          width: 36,
          height: 36,
          borderRadius: '50%',
          border: '1px solid var(--color-border)',
          background: 'transparent',
          color: 'var(--color-text-primary)',
          cursor: 'pointer',
          display: 'grid',
          placeItems: 'center',
        }} aria-label="settings">
          <Icon icon="fluent:settings-24-regular" style={{ fontSize: 18 }} />
        </button>
      </div>
    </header>
  );
}
