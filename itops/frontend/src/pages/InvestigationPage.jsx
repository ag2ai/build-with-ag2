import { useMemo, useState } from 'react';
import { Icon } from '@iconify/react';
import AgentTrace from '../components/AgentTrace';
import EvidenceFeed from '../components/EvidenceFeed';
import RCASynthesis from '../components/RCASynthesis';
import HITLPanel, { ActionHistory } from '../components/HITLPanel';
import StatusBadge from '../components/StatusBadge';
import { useBackend, selectInvestigations, selectWorkflow } from '../live/backend';
import { HITL_APPROVE, HITL_DEFER, HITL_REJECT } from '../live/mappers';

export default function InvestigationPage({ investigationId }) {
  const { state, now, respondHitl } = useBackend();
  const investigations = selectInvestigations(state);
  const ticketId = investigationId || investigations[0]?.id || null;

  const wf = useMemo(
    () => (ticketId ? selectWorkflow(state, now, ticketId) : null),
    [state, now, ticketId],
  );

  const [stageOverride, setStageOverride] = useState(null);
  const stage = stageOverride || (wf?.hasRemediation ? 'remediation' : 'diagnosis');

  if (!ticketId || !wf || !wf.inv) {
    return (
      <div style={{ flex: 1, display: 'grid', placeItems: 'center', color: 'var(--color-text-muted)' }}>
        <div style={{ textAlign: 'center', font: '400 14px/1.6 var(--font-body)' }}>
          <Icon icon="fluent:search-24-regular" style={{ fontSize: 32, opacity: 0.5 }} />
          <div style={{ marginTop: 12 }}>No investigation selected.</div>
          <div>Inject an incident from <strong>Monitoring</strong> or pick one in <strong>Investigations</strong>.</div>
        </div>
      </div>
    );
  }

  const inv = wf.inv;
  const agents = stage === 'diagnosis' ? wf.diagnosisAgents : wf.remediationAgents;
  const evidence = stage === 'diagnosis' ? wf.diagnosisEvidence : wf.remediationEvidence;
  const history = (stage === 'remediation' ? wf.remediationEvidence : wf.diagnosisEvidence)
    .map((e) => ({ time: inv.opened + e.time, user: e.agent, text: e.text }));

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <IncidentHeader inv={inv} />
      <StageIndicator
        stage={stage}
        hasRemediation={wf.hasRemediation}
        onChangeStage={setStageOverride}
      />

      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        <div style={{ width: 360, borderRight: '1px solid var(--color-border)' }}>
          <AgentTrace
            agents={agents}
            title={stage === 'diagnosis' ? 'Diagnosis Agents' : 'Remediation Fixers'}
          />
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <EvidenceFeed evidence={evidence} stage={stage} />
        </div>

        <div style={{ width: 440, borderLeft: '1px solid var(--color-border)', display: 'flex', flexDirection: 'column' }}>
          <RCASynthesis rca={wf.rca} locked={stage === 'remediation'} />
          {stage === 'remediation' && wf.hitl
            ? (
              <HITLPanel
                request={wf.hitl}
                history={history}
                onApprove={() => respondHitl(wf.remediationChannelId, HITL_APPROVE)}
                onDefer={() => respondHitl(wf.remediationChannelId, HITL_DEFER)}
                onReject={() => respondHitl(wf.remediationChannelId, HITL_REJECT)}
              />
            )
            : <ActionHistory history={history} />}
        </div>
      </div>
    </div>
  );
}

function IncidentHeader({ inv }) {
  return (
    <div style={{
      padding: '12px 20px',
      borderBottom: '1px solid var(--color-border)',
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      flexShrink: 0,
    }}>
      <span style={{ font: '600 14px/1 var(--font-mono)', color: 'var(--color-primary)' }}>{inv.id}</span>
      <span style={{ font: '500 13px/1 var(--font-body)', color: 'var(--color-text-primary)' }}>{inv.title}</span>
      <StatusBadge status={inv.status} style={{ marginLeft: 'auto' }} />
    </div>
  );
}

function StageIndicator({ stage, hasRemediation, onChangeStage }) {
  return (
    <div style={{
      padding: '16px 20px',
      borderBottom: '1px solid var(--color-border)',
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      flexShrink: 0,
    }}>
      <StageButton
        active={stage === 'diagnosis'}
        onClick={() => onChangeStage('diagnosis')}
        icon="fluent:search-24-regular"
        label="Diagnosis"
        color="var(--color-blue)"
        activeBg="rgba(155,221,255,0.15)"
        done={stage === 'remediation'}
      />

      <div style={{ flex: 1, height: 2, background: 'var(--color-border)', position: 'relative' }}>
        <div style={{
          position: 'absolute',
          left: 0,
          top: 0,
          height: '100%',
          width: stage === 'remediation' ? '100%' : '0%',
          background: 'var(--color-blue)',
          transition: 'width 300ms ease-out',
        }} />
      </div>

      <StageButton
        active={stage === 'remediation'}
        disabled={!hasRemediation}
        onClick={() => hasRemediation && onChangeStage('remediation')}
        icon="fluent:wrench-24-regular"
        label="Remediation"
        color="var(--color-primary)"
        activeBg="rgba(243,255,155,0.15)"
        trailing={stage === 'remediation' ? <Icon icon="fluent:arrow-sync-24-regular" style={{ fontSize: 14 }} /> : null}
      />
    </div>
  );
}

function StageButton({ active, disabled, onClick, icon, label, color, activeBg, done, trailing }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: '8px 16px',
        background: active ? activeBg : 'transparent',
        border: active ? `1px solid ${color}` : '1px solid var(--color-border)',
        borderRadius: 'var(--radius-pill)',
        color: active ? color : 'var(--color-text-muted)',
        font: '500 13px/1 var(--font-body)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.4 : 1,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        transition: 'all 150ms ease-out',
      }}
    >
      <Icon icon={icon} style={{ fontSize: 16 }} />
      {label}
      {done && <Icon icon="fluent:checkmark-circle-24-filled" style={{ fontSize: 14, color: 'var(--color-green)' }} />}
      {trailing}
    </button>
  );
}
