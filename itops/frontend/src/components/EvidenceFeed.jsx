import { useEffect, useRef } from 'react';
import { Icon } from '@iconify/react';
import { EVIDENCE_TYPE_CONFIG } from '../data/mockData';
import Markdown from './Markdown';

function EvidenceEntry({ item }) {
  const config = EVIDENCE_TYPE_CONFIG[item.type] || EVIDENCE_TYPE_CONFIG.evidence;
  const secs = Math.floor(item.time / 1000);
  const timeStr = `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')}`;

  return (
    <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
        <div style={{
          width: 32,
          height: 32,
          borderRadius: '50%',
          display: 'grid',
          placeItems: 'center',
          flexShrink: 0,
          background: config.bg,
          color: config.color,
        }}>
          <Icon icon={config.icon} style={{ fontSize: 16 }} />
        </div>
        <div style={{ width: 1, flex: 1, background: 'rgba(255,255,255,0.1)' }} />
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
          <span style={{
            font: '600 11px/1 var(--font-mono)',
            color: 'var(--color-text-primary)',
            textTransform: 'uppercase',
          }}>{item.agent}</span>
          <span style={{
            font: '500 10px/1 var(--font-mono)',
            color: config.color,
            textTransform: 'uppercase',
            padding: '2px 6px',
            background: config.bg,
            borderRadius: 'var(--radius-sm)',
          }}>{item.type}</span>
          {item.source && (
            <span style={{
              font: '500 10px/1 var(--font-mono)',
              color: 'var(--color-blue)',
              textTransform: 'uppercase',
              padding: '2px 6px',
              background: 'rgba(155,221,255,0.1)',
              borderRadius: 'var(--radius-sm)',
            }}>{item.source}</span>
          )}
          <span style={{
            marginLeft: 'auto',
            font: '400 11px/1 var(--font-mono)',
            color: 'var(--color-text-muted)',
            fontVariantNumeric: 'tabular-nums',
          }}>+{timeStr}</span>
        </div>
        <Markdown style={{
          font: '400 13px/1.4 var(--font-body)',
          color: 'var(--color-text-body)',
        }}>{item.text}</Markdown>
      </div>
    </div>
  );
}

export default function EvidenceFeed({ evidence, stage }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [evidence]);

  const title = stage === 'remediation' ? 'Remediation Actions' : 'Investigation Findings';

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-border)', flexShrink: 0 }}>
        <h3 style={{ font: '500 14px/1 var(--font-body)', color: 'var(--color-text-primary)', marginBottom: 4 }}>
          {title}
        </h3>
        <span style={{ font: '400 11px/1 var(--font-body)', color: 'var(--color-text-muted)' }}>
          Shared memory · {evidence.length} entries
        </span>
      </div>
      <div ref={scrollRef} style={{ flex: 1, overflow: 'auto', padding: '20px' }}>
        {evidence.map((item, i) => (
          <EvidenceEntry key={i} item={item} />
        ))}
      </div>
    </div>
  );
}
