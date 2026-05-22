// Live data layer: one WebSocket to the backend, a reducer that folds the
// event stream into the shapes the existing components expect, and selectors
// the pages use. Wrap the app in <BackendProvider> and read via useBackend().

import {
  useEffect, useMemo, useReducer, useRef, useState,
} from 'react';
import {
  API_BASE, WS_URL, EV_TEXT, EV_PACKET,
  nickName, evidenceTypeForTool, toInvestigation,
  hitlQuestion, argsPreview,
} from './mappers';
import { Ctx } from './backend';

const initialState = {
  connected: false,
  simRunning: false,    // driven by the backend's broadcast 'sim_state' (survives reload via replay)
  world: { systems: [], ambient_logs: {}, incidents: [] },
  tickets: {},          // id -> investigation
  openedAt: {},         // id -> ms first seen
  channels: {},         // channel_id -> { ticketId, stage, t0, agents, evidence, closed, reason, lastMs }
  ticketChannels: {},   // ticketId -> { diagnosis, remediation }
  hitl: {},             // channel_id -> { id, ticketId, agent, question, options, status, recommendations }
  logs: [],             // backend-owned log stream (folded from 'log' events; survives reload)
};

function applyEvent(state, ev) {
  const p = ev.payload || {};
  const tnow = (ev.ts || Date.now() / 1000) * 1000;

  switch (ev.type) {
    case 'snapshot': {
      const tickets = { ...state.tickets };
      const openedAt = { ...state.openedAt };
      for (const t of p.tickets || []) {
        openedAt[t.id] = openedAt[t.id] || tnow;
        tickets[t.id] = toInvestigation(t, openedAt[t.id]);
      }
      return { ...state, tickets, openedAt };
    }

    case 'ticket_created':
    case 'ticket_status': {
      const openedAt = { ...state.openedAt };
      openedAt[p.id] = openedAt[p.id] || tnow;
      const inv = toInvestigation(p, openedAt[p.id]);
      const prev = state.tickets[p.id];
      let timeToRCA = prev?.timeToRCA ?? null;
      if (timeToRCA == null && p.status === 'Remediation_Recommended') {
        timeToRCA = Math.round((tnow - openedAt[p.id]) / 1000);
      }
      inv.timeToRCA = timeToRCA;
      return { ...state, openedAt, tickets: { ...state.tickets, [p.id]: inv } };
    }

    case 'channel_opened': {
      const channels = {
        ...state.channels,
        [p.channel_id]: {
          ticketId: p.ticket_id, stage: p.stage, t0: tnow,
          agents: {}, evidence: [], closed: false, reason: null, lastMs: tnow,
        },
      };
      const tc = { ...(state.ticketChannels[p.ticket_id] || {}), [p.stage]: p.channel_id };
      return { ...state, channels, ticketChannels: { ...state.ticketChannels, [p.ticket_id]: tc } };
    }

    case 'envelope': {
      const ch = state.channels[p.channel_id];
      if (!ch) return state;
      if (p.event_type !== EV_TEXT && p.event_type !== EV_PACKET) return state;

      const agents = { ...ch.agents };
      const evidence = ch.evidence.slice();
      const sender = p.sender;
      const tool = p.tool;

      const ensure = (name, status) => {
        if (!agents[name]) {
          agents[name] = { id: name, name, status, startMs: ch.lastMs || tnow, endMs: null, count: 0 };
        }
        return agents[name];
      };
      const complete = (name) => {
        ensure(name, 'running');
        agents[name] = { ...agents[name], status: 'completed', endMs: tnow, count: agents[name].count + 1 };
      };

      if (p.event_type === EV_PACKET && (tool === 'assign_specialists' || tool === 'assign_fixers')) {
        complete(sender);
        const arr = (p.tool_args && (p.tool_args.specialists || p.tool_args.fixers)) || [];
        for (const nick of arr) {
          const nm = nickName(ch.stage, nick);
          ensure(nm, 'running');
          agents[nm] = { ...agents[nm], status: 'running', startMs: tnow, endMs: null };
        }
      } else {
        // every other packet / text post = that speaker finishing a turn
        complete(sender);
      }

      const type = p.event_type === EV_TEXT
        ? (sender === 'Human' ? 'hitl' : 'agent')
        : evidenceTypeForTool(tool);
      const text = p.body || p.text || (tool ? `${tool}(${argsPreview(p.tool_args)})` : '');
      evidence.push({ time: tnow - ch.t0, stage: ch.stage, agent: sender, type, text });

      return {
        ...state,
        channels: { ...state.channels, [p.channel_id]: { ...ch, agents, evidence, lastMs: tnow } },
      };
    }

    case 'hitl_requested': {
      const cid = p.channel_id;
      const channels = { ...state.channels };
      const ch = channels[cid];
      if (ch) {
        const op = ch.agents.Human || { id: 'Human', name: 'Human', startMs: tnow, endMs: null, count: 0 };
        channels[cid] = {
          ...ch,
          agents: { ...ch.agents, Human: { ...op, status: 'blocked', hitlReason: 'Human sign-off required' } },
        };
      }
      const hitl = {
        ...state.hitl,
        [cid]: {
          id: cid, ticketId: p.ticket_id, agent: 'Remediation sign-off',
          question: hitlQuestion(p),
          options: ['Approve remediation', 'Defer disruptive step', 'Reject remediation'],
          status: 'pending', recommendations: p.recommendations || [],
        },
      };
      return { ...state, channels, hitl };
    }

    case 'hitl_resolved': {
      const cid = p.channel_id;
      const hitl = { ...state.hitl };
      // Derive the decision kind from the human's response text.
      const d = (p.decision || '').toUpperCase();
      const status = !p.decision ? 'rejected'
        : d.includes('REJECT') ? 'rejected'
          : d.includes('DEFER') ? 'deferred'
            : 'approved';
      if (hitl[cid]) hitl[cid] = { ...hitl[cid], status };
      const channels = { ...state.channels };
      const ch = channels[cid];
      if (ch && ch.agents.Human) {
        channels[cid] = {
          ...ch,
          agents: { ...ch.agents, Human: { ...ch.agents.Human, status: 'running', endMs: null, hitlReason: undefined } },
        };
      }
      return { ...state, hitl, channels };
    }

    case 'channel_closed': {
      const ch = state.channels[p.channel_id];
      if (!ch) return state;
      const agents = { ...ch.agents };
      for (const k of Object.keys(agents)) {
        if (agents[k].status !== 'completed') {
          agents[k] = { ...agents[k], status: 'completed', endMs: tnow };
        }
      }
      return {
        ...state,
        channels: { ...state.channels, [p.channel_id]: { ...ch, agents, closed: true, reason: p.reason } },
      };
    }

    case 'reset':
      return { ...state, tickets: {}, openedAt: {}, channels: {}, ticketChannels: {}, hitl: {}, logs: [] };

    case 'log':
      return {
        ...state,
        logs: [...state.logs, { time: tnow, level: p.level, service: p.service, message: p.message }].slice(-200),
      };

    case 'sim_state':
      return { ...state, simRunning: !!p.running };

    default:
      return state;
  }
}

function reducer(state, action) {
  switch (action.kind) {
    case 'connected': return { ...state, connected: action.value };
    case 'world': return { ...state, world: action.world };
    case 'event': return applyEvent(state, action.event);
    default: return state;
  }
}

export function BackendProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [now, setNow] = useState(() => Date.now());
  const wsRef = useRef(null);

  // WebSocket with auto-reconnect.
  useEffect(() => {
    let stopped = false;
    let ws;
    const connect = () => {
      ws = new WebSocket(WS_URL);
      wsRef.current = ws;
      ws.onopen = () => dispatch({ kind: 'connected', value: true });
      ws.onmessage = (e) => {
        try { dispatch({ kind: 'event', event: JSON.parse(e.data) }); } catch { /* ignore */ }
      };
      ws.onerror = () => { try { ws.close(); } catch { /* ignore */ } };
      ws.onclose = () => {
        dispatch({ kind: 'connected', value: false });
        if (!stopped) setTimeout(connect, 1500);
      };
    };
    connect();
    return () => { stopped = true; try { ws && ws.close(); } catch { /* ignore */ } };
  }, []);

  // One-shot fetch of the mock-world setup (systems, ambient logs, incidents).
  useEffect(() => {
    fetch(`${API_BASE}/world`)
      .then((r) => r.json())
      .then((w) => dispatch({ kind: 'world', world: w }))
      .catch(() => { /* backend not up yet; reconnect will refetch on next mount */ });
  }, []);

  // 1s tick so running/blocked Gantt bars grow live.
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  const actions = useMemo(() => ({
    inject: (incidentKey) => {
      try { wsRef.current?.send(JSON.stringify({ type: 'inject', incident: incidentKey })); } catch { /* ignore */ }
    },
    respondHitl: (channelId, decision) => {
      try { wsRef.current?.send(JSON.stringify({ type: 'hitl_response', channel_id: channelId, decision })); } catch { /* ignore */ }
    },
    // Start/Stop are backend-owned: the server resets + broadcasts 'sim_state'
    // so every client (and any reloaded/new page) agrees on the running state.
    startSimulation: () => {
      try { wsRef.current?.send(JSON.stringify({ type: 'start' })); } catch { /* ignore */ }
    },
    stopSimulation: () => {
      try { wsRef.current?.send(JSON.stringify({ type: 'stop' })); } catch { /* ignore */ }
    },
  }), []);

  const value = useMemo(
    () => ({ state, connected: state.connected, now, simRunning: state.simRunning, logs: state.logs, ...actions }),
    [state, now, actions],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
