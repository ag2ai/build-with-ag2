// Pure mapping helpers between the backend's WebSocket events and the
// frontend's existing data shapes. No React here.

const host = (typeof location !== 'undefined' && location.hostname) || '127.0.0.1';

export const API_BASE = import.meta.env.VITE_API_BASE || `http://${host}:8000`;
export const WS_URL = import.meta.env.VITE_WS_URL || `ws://${host}:8000/ws`;

// Backend wire event_type constants (autogen.beta.network).
export const EV_TEXT = 'ag2.msg.text';
export const EV_PACKET = 'ag2.packet';

// assign_* tool-arg nicknames → live agent display names, per stage.
export const DIAG_NICK = { network: 'Network', storage: 'Storage', web: 'Web' };
export const REM_NICK = { infra: 'Infra', storage: 'StorageFix', config: 'ConfigFix', human: 'Human' };

// Canonical pipeline order so the trace rail renders in a stable shape.
export const DIAG_ORDER = [
  'TicketBot', 'IntakeLookup', 'IntakeDecide', 'Triage',
  'Network', 'Storage', 'Web', 'RCA', 'Remediation',
];
export const REM_ORDER = [
  'RemBot', 'RemTriage', 'Infra', 'StorageFix', 'ConfigFix', 'Human', 'Resolver',
];

export function nickName(stage, nick) {
  return (stage === 'remediation' ? REM_NICK : DIAG_NICK)[nick] || nick;
}

// Map a routing tool to the EvidenceFeed entry type.
export function evidenceTypeForTool(tool) {
  switch (tool) {
    case 'submit_rca': return 'synthesis';
    case 'submit_findings': return 'evidence';
    case 'list_recent_tickets': return 'evidence';
    case 'submit_fix': return 'action';
    case 'assign_specialists':
    case 'assign_fixers': return 'agent';
    default: return 'finding';
  }
}

export function confidenceToNum(c) {
  const m = { high: 0.9, medium: 0.65, low: 0.35 };
  return m[(c || '').toLowerCase()] ?? 0.7;
}

export function humanizeIssue(issue) {
  return (issue || '').replace(/_/g, ' ');
}

export function argsPreview(args) {
  if (!args) return '';
  return Object.entries(args)
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(', ')
    .slice(0, 90);
}

// Backend ticket JSON → frontend "investigation" shape (+ live extras).
export function toInvestigation(t, openedMs) {
  return {
    id: t.id,
    title: `${humanizeIssue(t.issue)} · ${t.system}`,
    status: t.status,
    severity: t.sev,
    service: t.system,
    opened: openedMs ?? Date.now(),
    timeToRCA: null,
    systems: [],
    actions: [],
    specialists: [],
    // live extras consumed by the investigation view
    issue: t.issue,
    rca: t.rca,
    confidence: t.confidence,
    recommendations: t.recommendations || [],
    resolution: t.resolution,
    parent: t.parent,
    history: t.history || [],
    needsHuman: !!t.needs_human,
    humanPrompt: t.human_prompt || '',
  };
}

export function hitlQuestion(payload) {
  const recs = payload.recommendations || [];
  const list = recs.length ? recs.join('; ') : 'the recommended remediation';
  return (
    `Approve the disruptive remediation for ${payload.ticket_id}? ` +
    `The fixers will apply: ${list}. The disruptive step needs operator sign-off; ` +
    `the other fixers keep working while this is pending.`
  );
}

export const HITL_APPROVE =
  'Human sign-off: APPROVED. Proceed with the recommended remediation, ' +
  'including the disruptive step, during the current change window. Standby capacity confirmed.';

export const HITL_DEFER =
  'Human sign-off: DEFERRED. Hold the disruptive step (e.g. disk hot-swap) for the next ' +
  'maintenance window; apply only the non-disruptive fixes now.';

export const HITL_REJECT =
  'Human sign-off: REJECTED. Do not proceed with the recommended disruptive remediation — ' +
  'the proposed fix is not approved. Escalate the incident for a human-led plan; any ' +
  'non-disruptive fixes already applied stand.';

// Status groupings shared by the dashboard filter + tab counters.
export const ACTIVE_STATUSES = ['Diagnosing', 'Remediation_Recommended', 'Remediating'];
export const RESOLVED_STATUSES = ['Resolved', 'Partially Resolved', 'Needs Followup', 'Duplicate'];
