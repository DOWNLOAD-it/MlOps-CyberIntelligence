'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';

// Auto-detect the API host from the browser's current hostname so the dashboard
// works identically on localhost AND when accessed via a remote server URL.
// NEXT_PUBLIC_API_URL overrides everything (useful for custom setups).
const API_PORT = process.env.NEXT_PUBLIC_API_PORT || '4308';
const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== 'undefined'
    ? `${window.location.protocol}//${window.location.hostname}:${API_PORT}`
    : `http://localhost:${API_PORT}`);
const POLL_INTERVAL_MS = 2500;
const MAX_LIVE_ALERTS = 200;

// ─── Icons ──────────────────────────────────────────────────────────────────
const RadioIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="2"/><path d="M4.93 19.07A10 10 0 0 1 4.93 4.93"/><path d="M7.76 16.24A6 6 0 0 1 7.76 7.76"/><path d="M19.07 4.93A10 10 0 0 1 19.07 19.07"/><path d="M16.24 7.76A6 6 0 0 1 16.24 16.24"/>
  </svg>
);
const BarChartIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/><line x1="2" y1="20" x2="22" y2="20"/>
  </svg>
);
const CpuIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/>
    <line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/>
    <line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/>
    <line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/>
    <line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/>
  </svg>
);
const ServerIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/>
    <line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/>
  </svg>
);
const ShieldIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
  </svg>
);
const AlertTriangleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
    <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
  </svg>
);
const CheckCircleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
    <polyline points="22 4 12 14.01 9 11.01"/>
  </svg>
);
const XCircleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
  </svg>
);
const ActivityIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
  </svg>
);

// ─── Types ───────────────────────────────────────────────────────────────────
interface LiveAlert {
  id: number;
  timestamp: string;
  attack_type: string;
  destination_port: number;
  flow_duration: number;
  confidence: number;
  _isNew?: boolean;
}

interface ModelInfo {
  model_name: string;
  model_version: string;
  f1_score: number;
  precision: number;
  recall: number;
  accuracy: number;
  roc_auc: number;
  training_date: string | null;
  feature_count: number;
  best_model: string;
  n_train: number;
  n_test: number;
  cv_folds: number;
  status: string;
}

interface ServiceHealth {
  name: string;
  status: string;
  latency_ms: number;
  detail: string;
}

interface AlertStats {
  total_alerts: number;
  alerts_24h: number;
  by_type: Record<string, number>;
  by_hour: Array<{ hour: string; count: number }>;
  avg_confidence: number;
  top_ports: Array<{ port: number; count: number }>;
}

interface RealtimeStats {
  rate_per_minute: number;
  total_last_hour: number;
  attacks_last_hour: number;
  benign_last_hour: number;
  top_attack_type: string;
  avg_confidence_last_hour: number;
  by_type_last_hour: Record<string, number>;
  by_minute: Array<{ minute: string; count: number }>;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function timeAgo(ts: string): string {
  const diff = (Date.now() - new Date(ts).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

function getSeverityConfig(confidence: number, attackType: string): { cls: string; label: string; dotColor: string } {
  const isBenign = ['benign', 'normal', 'benign traffic'].includes(attackType?.toLowerCase?.() ?? '');
  if (isBenign) return { cls: 'badge-benign', label: 'Benign', dotColor: '#22d3ee' };
  if (confidence > 0.9) return { cls: 'badge-critical', label: 'Critical', dotColor: '#f87171' };
  if (confidence > 0.7) return { cls: 'badge-high', label: 'High', dotColor: '#fb923c' };
  if (confidence > 0.5) return { cls: 'badge-medium', label: 'Medium', dotColor: '#fbbf24' };
  return { cls: 'badge-low', label: 'Low', dotColor: '#34d399' };
}

function fmtPct(v: number) { return `${(v * 100).toFixed(2)}%`; }
function fmtNum(v: number) { return v.toLocaleString(); }

// ─── Root ─────────────────────────────────────────────────────────────────────
export default function SOCDashboard() {
  const [activeTab, setActiveTab] = useState(0);
  const [liveAlerts, setLiveAlerts] = useState<LiveAlert[]>([]);
  const [lastAlertId, setLastAlertId] = useState(0);
  const [totalDetections, setTotalDetections] = useState(0);
  const [ratePerMin, setRatePerMin] = useState(0);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [modelLoading, setModelLoading] = useState(true);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Load initial alerts (latest 50) + model info on mount
  useEffect(() => {
    const init = async () => {
      try {
        const [alertsRes, modelRes, statsRes] = await Promise.all([
          fetch(`${API_URL}/api/v1/alerts?limit=50`).catch(() => null),
          fetch(`${API_URL}/api/v1/model/info`).catch(() => null),
          fetch(`${API_URL}/api/v1/alerts/stats`).catch(() => null),
        ]);
        if (alertsRes?.ok) {
          const data: LiveAlert[] = await alertsRes.json();
          setLiveAlerts(data.slice(0, MAX_LIVE_ALERTS));
          if (data.length > 0) setLastAlertId(Math.max(...data.map(a => a.id)));
        }
        if (modelRes?.ok) setModelInfo(await modelRes.json());
        if (statsRes?.ok) {
          const s = await statsRes.json();
          setTotalDetections(s.total_alerts || 0);
        }
      } finally {
        setModelLoading(false);
      }
    };
    init();
  }, []);

  // ── Polling for new alerts
  const pollAlerts = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/realtime/latest?since_id=${lastAlertId}&limit=30`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.alerts?.length > 0) {
        setLastAlertId(data.last_id);
        setLiveAlerts(prev => {
          const tagged = (data.alerts as LiveAlert[]).map((a: LiveAlert) => ({ ...a, _isNew: true }));
          const combined = [...tagged, ...prev].slice(0, MAX_LIVE_ALERTS);
          return combined;
        });
        setTotalDetections(prev => prev + data.alerts.length);
      }
      // Fetch rate
      const rateRes = await fetch(`${API_URL}/api/v1/realtime/stats`).catch(() => null);
      if (rateRes?.ok) {
        const rs: RealtimeStats = await rateRes.json();
        setRatePerMin(rs.rate_per_minute);
      }
    } catch { /* silent */ }
  }, [lastAlertId]);

  useEffect(() => {
    pollingRef.current = setInterval(pollAlerts, POLL_INTERVAL_MS);
    return () => { if (pollingRef.current) clearInterval(pollingRef.current); };
  }, [pollAlerts]);

  const tabs = [
    { name: 'Live Threat Feed', icon: <RadioIcon /> },
    { name: 'Threat Analytics', icon: <BarChartIcon /> },
    { name: 'Model Intelligence', icon: <CpuIcon /> },
    { name: 'System Status', icon: <ServerIcon /> },
  ];

  const attackCount = liveAlerts.filter(a => !['benign', 'normal'].includes(a.attack_type?.toLowerCase?.() ?? '')).length;

  return (
    <div className="min-h-screen flex flex-col bg-[#070b14]">
      {/* Header */}
      <header className="border-b border-[#1e2d3d] bg-[#0d1117]/80 backdrop-blur-sm px-6 py-3 sticky top-0 z-50">
        <div className="flex items-center justify-between max-w-screen-2xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="text-cyan-500"><ShieldIcon /></div>
            <div>
              <h1 className="text-base font-bold text-white tracking-wide">
                MLSecOps <span className="text-slate-400 font-normal">Threat Intelligence</span>
              </h1>
              <p className="text-[10px] text-slate-500 uppercase tracking-widest">CICIDS2017 · Real-time ML Detection</p>
            </div>
          </div>

          {/* Live stats header bar */}
          <div className="hidden md:flex items-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <span className="live-indicator" />
              <span className="text-slate-400 text-xs">Live</span>
            </div>
            <div className="text-right">
              <div className="text-white font-bold text-base">{fmtNum(totalDetections)}</div>
              <div className="text-slate-500 text-[10px] uppercase tracking-wider">Total Detections</div>
            </div>
            <div className="text-right">
              <div className="text-amber-400 font-bold text-base">{ratePerMin.toFixed(1)}/min</div>
              <div className="text-slate-500 text-[10px] uppercase tracking-wider">Detection Rate</div>
            </div>
            {modelInfo && modelInfo.status === 'trained' && (
              <div className="text-right">
                <div className="text-cyan-400 font-bold text-base glow-cyan">{fmtPct(modelInfo.f1_score)}</div>
                <div className="text-slate-500 text-[10px] uppercase tracking-wider">Model F1</div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="bg-[#0d1117] border-b border-[#1e2d3d] px-6">
        <div className="flex space-x-1 max-w-screen-2xl mx-auto">
          {tabs.map((tab, idx) => (
            <button
              key={idx}
              onClick={() => setActiveTab(idx)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-all border-b-2 ${
                activeTab === idx
                  ? 'border-cyan-500 text-cyan-400'
                  : 'border-transparent text-slate-500 hover:text-slate-300 hover:border-slate-600'
              }`}
            >
              {tab.icon}
              <span className="hidden sm:inline">{tab.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="flex-1 overflow-auto p-4 md:p-6">
        <div className="max-w-screen-2xl mx-auto">
          {activeTab === 0 && <LiveFeedTab alerts={liveAlerts} attackCount={attackCount} />}
          {activeTab === 1 && <AnalyticsTab />}
          {activeTab === 2 && <ModelTab info={modelInfo} loading={modelLoading} />}
          {activeTab === 3 && <SystemStatusTab />}
        </div>
      </main>
    </div>
  );
}

// ─── Tab 1: Live Threat Feed ──────────────────────────────────────────────────
function LiveFeedTab({ alerts, attackCount }: { alerts: LiveAlert[]; attackCount: number }) {
  const [filter, setFilter] = useState<'all' | 'attacks' | 'benign'>('all');
  const [paused, setPaused] = useState(false);

  const filtered = alerts.filter(a => {
    const isBenign = ['benign', 'normal'].includes(a.attack_type?.toLowerCase?.() ?? '');
    if (filter === 'attacks') return !isBenign;
    if (filter === 'benign') return isBenign;
    return true;
  });

  const displayAlerts = paused ? filtered : filtered;

  return (
    <div className="space-y-4">
      {/* Controls row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2">
          {(['all', 'attacks', 'benign'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider transition-all ${
                filter === f
                  ? f === 'attacks' ? 'bg-red-500/20 text-red-400 border border-red-500/50'
                    : f === 'benign' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/50'
                    : 'bg-cyan-600 text-white'
                  : 'bg-[#0d1117] border border-[#1e2d3d] text-slate-400 hover:border-slate-500'
              }`}
            >
              {f === 'all' ? `All (${alerts.length})` : f === 'attacks' ? `⚠ Threats (${attackCount})` : `✓ Benign`}
            </button>
          ))}
        </div>
        <button
          onClick={() => setPaused(p => !p)}
          className={`px-4 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider border transition-all ${
            paused
              ? 'bg-amber-500/20 text-amber-400 border-amber-500/50'
              : 'bg-[#0d1117] border-[#1e2d3d] text-slate-400 hover:border-slate-500'
          }`}
        >
          {paused ? '▶ Resume' : '⏸ Pause'}
        </button>
      </div>

      {/* Alert stream */}
      {displayAlerts.length === 0 ? (
        <div className="soc-card p-16 text-center">
          <div className="text-slate-600 mb-3"><ActivityIcon /></div>
          <p className="text-slate-500">Waiting for detections…</p>
          <p className="text-slate-600 text-sm mt-1">Alerts from the inference pipeline will appear here in real-time</p>
        </div>
      ) : (
        <div className="space-y-2">
          {displayAlerts.map(alert => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
        </div>
      )}
    </div>
  );
}

function AlertCard({ alert }: { alert: LiveAlert }) {
  const sev = getSeverityConfig(alert.confidence, alert.attack_type);
  const isBenign = sev.label === 'Benign';
  const isCritical = sev.label === 'Critical';

  return (
    <div className={`soc-card px-4 py-3 flex flex-wrap md:flex-nowrap items-center gap-4 ${alert._isNew ? 'alert-new' : ''} ${isCritical ? 'alert-critical-flash' : ''}`}>
      {/* Severity dot */}
      <div
        className="w-2.5 h-2.5 rounded-full flex-shrink-0"
        style={{ backgroundColor: sev.dotColor, boxShadow: `0 0 8px ${sev.dotColor}` }}
      />

      {/* Time */}
      <div className="text-slate-500 text-xs w-16 flex-shrink-0">{timeAgo(alert.timestamp)}</div>

      {/* Attack type */}
      <div className="flex-1 min-w-0">
        <span className={`badge ${sev.cls}`}>{alert.attack_type || 'Unknown'}</span>
      </div>

      {/* Port */}
      <div className="text-slate-400 text-sm font-mono w-20 text-right flex-shrink-0">
        <span className="text-slate-600 text-xs mr-1">PORT</span>{alert.destination_port ?? '—'}
      </div>

      {/* Duration */}
      <div className="text-slate-400 text-sm font-mono w-28 text-right flex-shrink-0">
        <span className="text-slate-600 text-xs mr-1">DUR</span>{alert.flow_duration != null ? `${(alert.flow_duration / 1000).toFixed(1)}ms` : '—'}
      </div>

      {/* Confidence bar */}
      <div className="flex items-center gap-2 w-32 flex-shrink-0">
        <div className="gauge-track flex-1">
          <div
            className="gauge-fill"
            style={{
              width: `${(alert.confidence ?? 0) * 100}%`,
              backgroundColor: isBenign ? '#22d3ee' : sev.dotColor,
            }}
          />
        </div>
        <span className="text-xs font-mono text-slate-300 w-10 text-right">
          {((alert.confidence ?? 0) * 100).toFixed(0)}%
        </span>
      </div>
    </div>
  );
}

// ─── Tab 2: Threat Analytics ──────────────────────────────────────────────────
function AnalyticsTab() {
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [rtStats, setRtStats] = useState<RealtimeStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [s, rt] = await Promise.all([
          fetch(`${API_URL}/api/v1/alerts/stats`).then(r => r.ok ? r.json() : null).catch(() => null),
          fetch(`${API_URL}/api/v1/realtime/stats`).then(r => r.ok ? r.json() : null).catch(() => null),
        ]);
        if (s) setStats(s);
        if (rt) setRtStats(rt);
      } finally {
        setLoading(false);
      }
    };
    load();
    const iv = setInterval(load, 15000);
    return () => clearInterval(iv);
  }, []);

  if (loading) return <div className="text-center text-slate-500 mt-20 text-sm">Loading analytics…</div>;

  const byHour = stats?.by_hour ?? [];
  const maxHour = Math.max(...byHour.map(h => h.count), 1);
  const byType = stats?.by_type ?? {};
  const maxType = Math.max(...Object.values(byType), 1);
  const topPorts = stats?.top_ports ?? [];
  const byMinute = rtStats?.by_minute ?? [];
  const maxMin = Math.max(...byMinute.map(m => m.count), 1);

  const ATTACK_COLORS: Record<string, string> = {
    'DDoS': '#f87171',
    'DoS': '#fb923c',
    'PortScan': '#fbbf24',
    'FTP-Patator': '#a78bfa',
    'SSH-Patator': '#c084fc',
    'Web Attack': '#f472b6',
    'Infiltration': '#f43f5e',
    'Botnet': '#ef4444',
    'Benign': '#22d3ee',
  };
  function colorForType(t: string) {
    for (const [k, v] of Object.entries(ATTACK_COLORS)) {
      if (t.toLowerCase().includes(k.toLowerCase())) return v;
    }
    return '#60a5fa';
  }

  return (
    <div className="space-y-6">
      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'All-Time Detections', value: fmtNum(stats?.total_alerts ?? 0), color: 'text-white' },
          { label: 'Last 24 h', value: fmtNum(stats?.alerts_24h ?? 0), color: 'text-amber-400' },
          { label: 'Threats Last Hour', value: fmtNum(rtStats?.attacks_last_hour ?? 0), color: 'text-red-400' },
          { label: 'Avg Confidence', value: fmtPct(stats?.avg_confidence ?? 0), color: 'text-cyan-400' },
        ].map(kpi => (
          <div key={kpi.label} className="soc-card p-5">
            <div className="text-slate-500 text-xs uppercase tracking-wider mb-2">{kpi.label}</div>
            <div className={`text-3xl font-bold ${kpi.color}`}>{kpi.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Hourly bar chart */}
        <div className="soc-card p-5 lg:col-span-2">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-base font-semibold text-white">Alert Volume — Last 24 Hours</h3>
            <span className="text-slate-500 text-xs">{byHour.length} hours with data</span>
          </div>
          {byHour.length > 0 ? (
            <div className="flex items-end gap-1 h-40">
              {byHour.map((item, i) => (
                <div
                  key={i}
                  className="spark-bar"
                  style={{ height: `${(item.count / maxHour) * 100}%` }}
                  title={`${item.hour}: ${item.count} alerts`}
                />
              ))}
            </div>
          ) : (
            <div className="h-40 flex items-center justify-center text-slate-600 text-sm">No data in last 24h</div>
          )}
        </div>

        {/* Per-minute sparkline */}
        <div className="soc-card p-5">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-base font-semibold text-white">Last 30 Minutes</h3>
            <span className="text-amber-400 text-sm font-mono">{rtStats?.rate_per_minute ?? 0}/min</span>
          </div>
          {byMinute.length > 0 ? (
            <div className="flex items-end gap-0.5 h-40">
              {byMinute.map((item, i) => (
                <div
                  key={i}
                  className="spark-bar"
                  style={{ height: `${(item.count / maxMin) * 100}%`, backgroundColor: '#f59e0b' }}
                  title={`${item.minute}: ${item.count}`}
                />
              ))}
            </div>
          ) : (
            <div className="h-40 flex items-center justify-center text-slate-600 text-sm">No recent data</div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Attack type breakdown */}
        <div className="soc-card p-5">
          <h3 className="text-base font-semibold text-white mb-4">Attack Type Breakdown</h3>
          {Object.keys(byType).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(byType).map(([type, count]) => {
                const pct = (count / maxType) * 100;
                const color = colorForType(type);
                return (
                  <div key={type}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-slate-300 truncate max-w-[60%]">{type}</span>
                      <span className="font-mono text-slate-400">{fmtNum(count)}</span>
                    </div>
                    <div className="gauge-track">
                      <div className="gauge-fill" style={{ width: `${pct}%`, backgroundColor: color }} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-slate-600 text-sm">No attack type data</div>
          )}
        </div>

        {/* Top attacked ports */}
        <div className="soc-card p-5">
          <h3 className="text-base font-semibold text-white mb-4">Top Targeted Ports</h3>
          {topPorts.length > 0 ? (
            <table className="soc-table">
              <thead>
                <tr>
                  <th>Port</th>
                  <th>Hits</th>
                  <th>Share</th>
                </tr>
              </thead>
              <tbody>
                {topPorts.map((p, i) => {
                  const total = topPorts.reduce((s, x) => s + x.count, 0);
                  return (
                    <tr key={p.port}>
                      <td className="font-mono text-cyan-400">{p.port}</td>
                      <td className="font-mono text-slate-300">{fmtNum(p.count)}</td>
                      <td>
                        <div className="flex items-center gap-2">
                          <div className="gauge-track w-16">
                            <div className="gauge-fill bg-cyan-500" style={{ width: `${(p.count / total) * 100}%` }} />
                          </div>
                          <span className="text-xs text-slate-500">{((p.count / total) * 100).toFixed(1)}%</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <div className="text-slate-600 text-sm">No port data</div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Tab 3: Model Intelligence ────────────────────────────────────────────────
function ModelTab({ info, loading }: { info: ModelInfo | null; loading: boolean }) {
  const [reloading, setReloading] = useState(false);
  const [reloadMsg, setReloadMsg] = useState('');

  const handleReload = async () => {
    setReloading(true);
    setReloadMsg('');
    try {
      const res = await fetch(`${API_URL}/api/v1/reload-model`, { method: 'POST' });
      const data = await res.json();
      setReloadMsg(res.ok ? '✓ Model reloaded' : `✗ ${data.detail}`);
    } catch {
      setReloadMsg('✗ Request failed');
    } finally {
      setReloading(false);
      setTimeout(() => setReloadMsg(''), 4000);
    }
  };

  if (loading) return <div className="text-center text-slate-500 mt-20 text-sm">Loading model info…</div>;

  if (!info || info.status === 'not_trained') {
    return (
      <div className="soc-card p-16 text-center max-w-xl mx-auto">
        <div className="text-slate-600 flex justify-center mb-4"><CpuIcon /></div>
        <h3 className="text-xl font-semibold text-white mb-2">No Model Trained Yet</h3>
        <p className="text-slate-400 mb-6 text-sm">Run the full Dagster pipeline to train and register the anomaly detection model.</p>
        <a
          href="http://exp.s3.fsbm.ma:4301"
          target="_blank"
          rel="noreferrer"
          className="inline-block bg-cyan-600 hover:bg-cyan-500 text-white font-semibold px-6 py-2.5 rounded-lg transition-colors"
        >
          Open Dagster
        </a>
      </div>
    );
  }

  const metrics = [
    { label: 'F1 Score', value: info.f1_score, color: '#06b6d4', glow: 'glow-cyan', desc: 'Harmonic mean of precision & recall' },
    { label: 'Precision', value: info.precision, color: '#10b981', glow: 'glow-green', desc: 'True positives / predicted positives' },
    { label: 'Recall', value: info.recall, color: '#f59e0b', glow: '', desc: 'True positives / actual positives' },
    { label: 'Accuracy', value: info.accuracy, color: '#3b82f6', glow: '', desc: 'Correct classifications / total' },
    { label: 'ROC-AUC', value: info.roc_auc, color: '#8b5cf6', glow: '', desc: 'Area under ROC curve' },
  ];

  return (
    <div className="space-y-6">
      {/* Model header card */}
      <div className="soc-card p-6 relative overflow-hidden">
        <div className="scan-overlay"><div className="scan-line" /></div>
        <div className="flex flex-wrap justify-between items-start gap-4 relative z-10">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h2 className="text-xl font-bold text-white">{info.best_model || 'Network Anomaly Detector'}</h2>
              <span className="badge badge-low">v{info.model_version}</span>
              <span className="badge badge-info">{info.status}</span>
            </div>
            <div className="flex flex-wrap gap-6 text-sm text-slate-400">
              <span>Registered name: <strong className="text-slate-200">network-anomaly-detector</strong></span>
              <span>Features: <strong className="text-slate-200">{info.feature_count}</strong></span>
              <span>Train samples: <strong className="text-slate-200">{fmtNum(info.n_train)}</strong></span>
              <span>Test samples: <strong className="text-slate-200">{fmtNum(info.n_test)}</strong></span>
              <span>CV folds: <strong className="text-slate-200">{info.cv_folds}</strong></span>
              {info.training_date && (
                <span>Trained: <strong className="text-slate-200">{new Date(info.training_date).toLocaleString()}</strong></span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            {reloadMsg && <span className={`text-sm ${reloadMsg.startsWith('✓') ? 'text-green-400' : 'text-red-400'}`}>{reloadMsg}</span>}
            <button
              onClick={handleReload}
              disabled={reloading}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-[#1e2d3d] rounded-lg text-sm text-white transition-colors disabled:opacity-50"
            >
              {reloading ? 'Reloading…' : '↻ Reload Model'}
            </button>
          </div>
        </div>
      </div>

      {/* Metric gauges */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {metrics.map(m => (
          <div key={m.label} className="soc-card p-6 text-center">
            <div className="text-slate-500 text-xs uppercase tracking-wider mb-3">{m.label}</div>
            <div
              className={`text-4xl font-bold mb-3 ${m.glow}`}
              style={{ color: m.color }}
            >
              {(m.value * 100).toFixed(2)}%
            </div>
            <div className="gauge-track mb-3">
              <div
                className="gauge-fill"
                style={{ width: `${m.value * 100}%`, backgroundColor: m.color }}
              />
            </div>
            <div className="text-slate-600 text-[10px] leading-tight">{m.desc}</div>
          </div>
        ))}
      </div>

      {/* Feature columns used */}
      <div className="soc-card p-5">
        <h3 className="text-base font-semibold text-white mb-4">Feature Set ({info.feature_count} features from CICIDS2017)</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
          {[
            'destination_port', 'flow_duration', 'total_fwd_packets', 'total_backward_packets',
            'total_length_of_fwd_packets', 'total_length_of_bwd_packets', 'fwd_packet_length_max',
            'fwd_packet_length_min', 'fwd_packet_length_mean', 'fwd_packet_length_std',
            'bwd_packet_length_max', 'bwd_packet_length_min', 'bwd_packet_length_mean',
            'bwd_packet_length_std', 'flow_iat_mean', 'flow_iat_std', 'flow_iat_max',
            'flow_iat_min', 'fwd_iat_total', 'fwd_iat_mean', 'fwd_iat_std', 'bwd_iat_total',
            'bwd_iat_mean', 'bwd_iat_std', 'fin_flag_count', 'syn_flag_count', 'rst_flag_count',
            'psh_flag_count', 'ack_flag_count', 'average_packet_size', 'init_win_bytes_forward',
            'init_win_bytes_backward', 'active_mean', 'active_std', 'idle_mean', 'idle_std',
          ].map(f => (
            <div key={f} className="bg-[#070b14] border border-[#1e2d3d] rounded px-2 py-1 text-[10px] font-mono text-slate-400 truncate" title={f}>
              {f}
            </div>
          ))}
        </div>
      </div>

      {/* Pipeline info */}
      <div className="soc-card p-5">
        <h3 className="text-base font-semibold text-white mb-4">Training Pipeline</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          {[
            { title: 'Data Source', body: 'CICIDS2017 network traffic dataset. Contains benign flows and 14 attack categories including DDoS, DoS, PortScan, Brute-force, Web attacks, Infiltration, and Botnet.' },
            { title: 'Methodology', body: 'Multi-model comparison: RandomForest, ExtraTrees, GradientBoosting, LogisticRegression. 5-fold stratified cross-validation on training split. Winner selected by CV F1. Evaluated once on held-out 20% test set.' },
            { title: 'Anti-Leakage', body: 'Train/test split performed before all preprocessing. StandardScaler fitted on training data only. Test set evaluated exactly once after model selection to prevent data snooping.' },
          ].map(card => (
            <div key={card.title} className="bg-[#070b14] border border-[#1e2d3d] rounded-lg p-4">
              <div className="text-cyan-400 font-semibold text-xs uppercase tracking-wider mb-2">{card.title}</div>
              <p className="text-slate-400 text-xs leading-relaxed">{card.body}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Tab 4: System Status ─────────────────────────────────────────────────────
function SystemStatusTab() {
  const [services, setServices] = useState<ServiceHealth[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchHealth = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/system/health`);
      if (res.ok) {
        const data = await res.json();
        setServices(data.services ?? []);
        setLastRefresh(new Date());
      }
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    fetchHealth();
    const iv = setInterval(fetchHealth, 30000);
    return () => clearInterval(iv);
  }, [fetchHealth]);

  const serviceLinks: Record<string, string> = {
    'api': `${API_URL}/docs`,
    'mlflow': 'http://exp.s3.fsbm.ma:4302',
    'dagster': 'http://exp.s3.fsbm.ma:4301',
    'grafana': 'http://exp.s3.fsbm.ma:4307',
    'postgres': '#',
    'redpanda': '#',
  };

  const serviceIcons: Record<string, string> = {
    'api': '⚡',
    'mlflow': '🧪',
    'postgres': '🗄',
    'redpanda': '📡',
    'dagster': '🔄',
    'grafana': '📊',
  };

  const allHealthy = services.length > 0 && services.every(s => s.status === 'healthy');
  const unhealthyCount = services.filter(s => s.status !== 'healthy').length;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-white">Platform Services</h2>
          {lastRefresh && <p className="text-slate-500 text-xs mt-1">Last checked: {lastRefresh.toLocaleTimeString()}</p>}
        </div>
        <div className="flex items-center gap-3">
          {services.length > 0 && (
            <div className={`flex items-center gap-2 text-sm ${allHealthy ? 'text-green-400' : 'text-amber-400'}`}>
              {allHealthy ? <CheckCircleIcon /> : <AlertTriangleIcon />}
              {allHealthy ? 'All systems operational' : `${unhealthyCount} service(s) degraded`}
            </div>
          )}
          <button
            onClick={fetchHealth}
            disabled={loading}
            className="text-sm px-4 py-2 bg-[#0d1117] border border-[#1e2d3d] rounded-lg hover:border-slate-500 text-slate-300 transition-colors disabled:opacity-50"
          >
            {loading ? 'Checking…' : '↻ Refresh'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {services.map(svc => {
          const isHealthy = svc.status === 'healthy';
          const link = serviceLinks[svc.name] ?? '#';
          return (
            <div key={svc.name} className={`soc-card p-5 border ${isHealthy ? 'border-[#1e2d3d]' : 'border-red-500/30'}`}>
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-2">
                  <span className="text-xl">{serviceIcons[svc.name] ?? '🔧'}</span>
                  <span className="font-semibold text-white capitalize">{svc.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  {isHealthy
                    ? <span className="text-green-400"><CheckCircleIcon /></span>
                    : <span className="text-red-400"><XCircleIcon /></span>
                  }
                  <span className={`badge ${isHealthy ? 'badge-low' : 'badge-critical'}`}>
                    {svc.status}
                  </span>
                </div>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-500">Latency</span>
                  <span className={`font-mono ${svc.latency_ms < 100 ? 'text-green-400' : svc.latency_ms < 500 ? 'text-amber-400' : 'text-red-400'}`}>
                    {svc.latency_ms}ms
                  </span>
                </div>
                {svc.detail && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">Detail</span>
                    <span className="text-slate-400 text-xs truncate max-w-[60%] text-right">{svc.detail}</span>
                  </div>
                )}
              </div>
              {link !== '#' && (
                <a
                  href={link}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-4 block text-center text-xs text-cyan-500 hover:text-cyan-400 transition-colors border border-[#1e2d3d] hover:border-cyan-500/50 rounded py-1.5"
                >
                  Open →
                </a>
              )}
            </div>
          );
        })}
      </div>

      {/* Architecture overview */}
      <div className="soc-card p-5">
        <h3 className="text-base font-semibold text-white mb-4">Platform Architecture</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs text-center">
          {[
            { label: 'CICIDS2017 CSV', sub: 'Raw data source', color: 'border-slate-600', icon: '📁' },
            { label: 'Redpanda', sub: 'Kafka-compatible streaming', color: 'border-blue-500/40', icon: '📡' },
            { label: 'Dagster Pipeline', sub: 'Ingest → Clean → Train → Infer', color: 'border-cyan-500/40', icon: '🔄' },
            { label: 'MLflow Registry', sub: 'Model versioning & metrics', color: 'border-purple-500/40', icon: '🧪' },
          ].map(n => (
            <div key={n.label} className={`bg-[#070b14] border ${n.color} rounded-lg p-3`}>
              <div className="text-2xl mb-1">{n.icon}</div>
              <div className="font-semibold text-slate-200">{n.label}</div>
              <div className="text-slate-500 mt-1">{n.sub}</div>
            </div>
          ))}
        </div>
        <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
          <span>Postgres stores all inference results → this dashboard reads them in real-time via the FastAPI polling endpoint.</span>
        </div>
      </div>
    </div>
  );
}