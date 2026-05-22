// Display-config maps only. The actual mock *world* data (systems, ambient
// logs, tool results, incidents) is owned by the backend and served via
// GET /world; everything else (tickets, agents, evidence, RCA, HITL) is live
// over the WebSocket. This file just maps statuses / severities / types to
// colors + icons for rendering.

export const STATUS_CONFIG = {
  // Live backend statuses
  Diagnosing:                { color: 'var(--color-blue)',       label: 'Diagnosing',          icon: 'fluent:search-24-regular' },
  Remediation_Recommended:   { color: 'var(--color-primary)',    label: 'RCA Ready',           icon: 'fluent:lightbulb-24-regular' },
  Remediating:               { color: 'var(--color-blue)',       label: 'Remediating',         icon: 'fluent:wrench-24-regular' },
  Resolved:                  { color: 'var(--color-text-muted)', label: 'Resolved',            icon: 'fluent:checkmark-circle-24-regular' },
  'Partially Resolved':      { color: 'var(--color-green)',      label: 'Partially Resolved',  icon: 'fluent:checkmark-circle-24-regular' },
  'Needs Followup':          { color: 'var(--color-pink)',       label: 'Needs Follow-up',     icon: 'fluent:alert-24-regular' },
  Duplicate:                 { color: 'var(--color-text-muted)', label: 'Duplicate',           icon: 'fluent:copy-24-regular' },
  // Fallbacks (frontend scaffold defaults)
  investigating:             { color: 'var(--color-blue)',       label: 'Investigating',       icon: 'fluent:search-24-regular' },
  'rca-ready':               { color: 'var(--color-green)',      label: 'RCA Ready',           icon: 'fluent:lightbulb-24-regular' },
  resolved:                  { color: 'var(--color-text-muted)', label: 'Resolved',            icon: 'fluent:checkmark-circle-24-regular' },
  monitoring:                { color: 'var(--color-primary)',    label: 'Monitoring',          icon: 'fluent:eye-24-regular' },
};

export const SEVERITY_CONFIG = {
  sev1: { color: 'var(--color-pink)',    label: 'SEV1' },
  sev2: { color: 'var(--color-primary)', label: 'SEV2' },
  sev3: { color: 'var(--color-blue)',    label: 'SEV3' },
  // Fallbacks
  critical: { color: 'var(--color-pink)',    label: 'Critical' },
  warning:  { color: 'var(--color-primary)', label: 'Warning' },
  info:     { color: 'var(--color-blue)',    label: 'Info' },
};

export const SYSTEM_ICONS = {
  grafana: 'fluent:chart-multiple-24-regular',
  loki: 'fluent:database-24-regular',
  prometheus: 'fluent:gauge-24-regular',
  betterstack: 'fluent:stack-24-regular',
  railway: 'fluent:cloud-24-regular',
  servicenow: 'fluent:ticket-24-regular',
};

export const ACTION_LABELS = {
  rollback: 'Rollback',
  restart: 'Restart',
  'scale-workers': 'Scale Workers',
  'deploy-patch': 'Deploy Patch',
  'renew-cert': 'Renew Cert',
};

export const EVIDENCE_TYPE_CONFIG = {
  agent:     { icon: 'fluent:brain-circuit-24-regular', color: 'var(--color-primary)', bg: 'rgba(243,255,155,0.1)' },
  evidence:  { icon: 'fluent:document-search-24-regular', color: 'var(--color-blue)', bg: 'rgba(155,221,255,0.1)' },
  finding:   { icon: 'fluent:checkmark-circle-24-regular', color: 'var(--color-green)', bg: 'rgba(155,255,163,0.1)' },
  synthesis: { icon: 'fluent:lightbulb-24-regular', color: 'var(--color-green)', bg: 'rgba(155,255,163,0.1)' },
  action:    { icon: 'fluent:wrench-24-regular', color: 'var(--color-primary)', bg: 'rgba(243,255,155,0.1)' },
  hitl:      { icon: 'fluent:person-feedback-24-regular', color: 'var(--color-pink)', bg: 'rgba(213,155,255,0.1)' },
};
