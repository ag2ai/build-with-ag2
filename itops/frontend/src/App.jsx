import { useState } from 'react';
import { Icon } from '@iconify/react';
import TitleBar from './components/TitleBar';
import MonitoringPage from './pages/MonitoringPage';
import DashboardPage from './pages/DashboardPage';
import InvestigationPage from './pages/InvestigationPage';
import { PulseDot } from './components/StatusBadge';
import { BackendProvider } from './live/BackendProvider';
import { useBackend, selectInvestigations } from './live/backend';
import { ACTIVE_STATUSES } from './live/mappers';

function Shell() {
  const { state, connected, simRunning, startSimulation, stopSimulation } = useBackend();
  const [activeView, setActiveView] = useState('monitoring');
  const [selectedTicketId, setSelectedTicketId] = useState(null);

  const investigations = selectInvestigations(state);
  const activeCount = investigations.filter((i) => ACTIVE_STATUSES.includes(i.status)).length;

  const openInvestigation = (id) => {
    if (id) setSelectedTicketId(id);
    setActiveView('investigation');
  };

  const TABS = [
    { id: 'monitoring', label: 'Monitoring', icon: 'fluent:eye-24-regular' },
    { id: 'dashboard', label: 'Investigations', icon: 'fluent:list-24-regular', badge: investigations.length || null },
    { id: 'investigation', label: 'Live Investigation', icon: 'fluent:search-24-regular', badge: activeCount || null },
  ];

  const titleBarCenter = (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, font: '500 12px/1 var(--font-body)', color: connected ? 'var(--color-green)' : 'var(--color-pink)' }}>
      <PulseDot color={connected ? 'var(--color-green)' : 'var(--color-pink)'} />
      {connected ? 'Connected' : 'Disconnected'}
    </div>
  );

  const simButton = (
    <button
      onClick={() => (simRunning ? stopSimulation() : startSimulation())}
      disabled={!connected}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '8px 16px',
        borderRadius: 'var(--radius-pill)',
        font: '600 13px/1 var(--font-body)',
        cursor: connected ? 'pointer' : 'not-allowed',
        opacity: connected ? 1 : 0.4,
        border: simRunning ? '1px solid var(--color-border)' : '1px solid var(--color-green)',
        background: simRunning ? 'transparent' : 'var(--color-green)',
        color: simRunning ? 'var(--color-text-muted)' : '#11240f',
      }}
    >
      <Icon icon={simRunning ? 'fluent:stop-24-filled' : 'fluent:play-24-filled'} style={{ fontSize: 16 }} />
      {simRunning ? 'Stop Simulation' : 'Start Simulation'}
    </button>
  );

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <TitleBar center={titleBarCenter} right={simButton} />

      <nav style={{
        display: 'flex',
        borderBottom: '1px solid var(--color-border)',
        padding: '0 20px',
        gap: 4,
        flexShrink: 0,
      }}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveView(tab.id)}
            style={{
              padding: '12px 16px',
              background: 'transparent',
              border: 'none',
              borderBottom: activeView === tab.id ? '2px solid var(--color-primary)' : '2px solid transparent',
              color: activeView === tab.id ? 'var(--color-primary)' : 'var(--color-text-muted)',
              font: '500 13px/1 var(--font-body)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              transition: 'all 150ms ease-out',
            }}
          >
            <Icon icon={tab.icon} style={{ fontSize: 16 }} />
            {tab.label}
            {tab.badge != null && (
              <span style={{
                padding: '1px 7px',
                borderRadius: 'var(--radius-pill)',
                background: activeView === tab.id ? 'rgba(243,255,155,0.15)' : 'var(--color-surface-subtle)',
                color: activeView === tab.id ? 'var(--color-primary)' : 'var(--color-text-muted)',
                font: '600 11px/1 var(--font-mono)',
                fontVariantNumeric: 'tabular-nums',
              }}>{tab.badge}</span>
            )}
          </button>
        ))}
      </nav>

      {activeView === 'monitoring' && <MonitoringPage onOpenInvestigation={openInvestigation} />}
      {activeView === 'dashboard' && <DashboardPage onOpenInvestigation={openInvestigation} />}
      {activeView === 'investigation' && <InvestigationPage investigationId={selectedTicketId} onOpenInvestigation={openInvestigation} />}
    </div>
  );
}

export default function App() {
  return (
    <BackendProvider>
      <Shell />
    </BackendProvider>
  );
}
