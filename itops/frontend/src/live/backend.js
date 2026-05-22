// Context, hook, and selectors for the live backend layer. Kept in a separate
// (non-component) module from BackendProvider.jsx so that file can export only
// its component — a requirement for React Fast Refresh.

import { createContext, useContext } from 'react';
import { DIAG_ORDER, REM_ORDER, confidenceToNum } from './mappers';

export const Ctx = createContext(null);

export function useBackend() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useBackend must be used within <BackendProvider>');
  return ctx;
}

// ─── Selectors ──────────────────────────────────────────────────────────

export function selectInvestigations(state) {
  return Object.values(state.tickets).sort((a, b) => b.opened - a.opened);
}

function agentsForChannel(ch, now, order) {
  if (!ch) return [];
  const list = Object.values(ch.agents).map((a) => {
    const end = a.endMs ?? now;
    return {
      id: a.id,
      name: a.name,
      status: a.status,
      startTime: Math.max(0, Math.round((a.startMs - ch.t0) / 1000)),
      duration: Math.max(1, Math.round((end - a.startMs) / 1000)),
      hitlReason: a.hitlReason,
      // intentionally no findings/actions count — each agent posts once, so a
      // per-agent "1" was just noise. The bar shows the duration instead.
    };
  });
  list.sort((x, y) => {
    const ix = order.indexOf(x.name); const iy = order.indexOf(y.name);
    return (ix === -1 ? 999 : ix) - (iy === -1 ? 999 : iy);
  });
  return list;
}

export function selectWorkflow(state, now, ticketId) {
  const tc = state.ticketChannels[ticketId] || {};
  const diagCh = state.channels[tc.diagnosis];
  const remCh = state.channels[tc.remediation];
  const inv = state.tickets[ticketId];

  const findings = (diagCh?.evidence || [])
    .filter((e) => e.type === 'evidence' && e.agent !== 'IntakeLookup')
    .map((e) => e.text);

  const rca = inv ? {
    confidence: confidenceToNum(inv.confidence),
    symptoms: findings.length ? findings.slice(0, 5) : (inv.rca ? [inv.rca] : []),
    factors: inv.recommendations || [],
    rootCause: inv.rca || 'Awaiting root cause analysis…',
  } : null;

  return {
    inv,
    diagnosisAgents: agentsForChannel(diagCh, now, DIAG_ORDER),
    remediationAgents: agentsForChannel(remCh, now, REM_ORDER),
    diagnosisEvidence: diagCh?.evidence || [],
    remediationEvidence: remCh?.evidence || [],
    rca,
    hitl: remCh ? state.hitl[tc.remediation] : null,
    hasRemediation: !!remCh,
    remediationChannelId: tc.remediation,
  };
}
