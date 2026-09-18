'use client';

import React, { useState, useEffect, useCallback } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4308';

// --- Icons ---
const GridIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>;
const BellIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>;
const ShieldIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>;
const CpuIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line><line x1="20" y1="9" x2="23" y2="9"></line><line x1="20" y1="14" x2="23" y2="14"></line><line x1="1" y1="9" x2="4" y2="9"></line><line x1="1" y1="14" x2="4" y2="14"></line></svg>;
const ServerIcon = () => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>;

// --- Types ---
interface Alert {
  id: number;
  timestamp: string;
  attack_type: string;
  destination_port: number;
  flow_duration: number;
  confidence: number;
}

interface AlertStats {
  total_alerts: number;
  alerts_24h: number;
  by_type: Record<string, number>;
  by_hour: Array<{ hour: string; count: number }>;
  avg_confidence: number;
  top_ports: Array<{ port: number; count: number }>;
}

interface ModelInfo {
  model_name: string;
  model_version: string;
  f1_score: number;
  precision: number;
  recall: number;
  accuracy: number;
  training_date: string | null;
  feature_count: number;
  status: string;
}

interface ServiceHealth {
  name: string;
  status: string;
  latency_ms: number;
  detail: string;
}

interface SystemHealthResponse {
  services: ServiceHealth[];
}

interface PredictionResult {
  is_attack: boolean;
  confidence: number;
  attack_type: string;
}

export default function SOCDashboard() {
  const [activeTab, setActiveTab] = useState(0);

  const tabs = [
    { name: 'Overview', icon: <GridIcon /> },
    { name: 'Alert Feed', icon: <BellIcon /> },
    { name: 'Threat Inspector', icon: <ShieldIcon /> },
    { name: 'Model Health', icon: <CpuIcon /> },
    { name: 'System Status', icon: <ServerIcon /> },
  ];

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-cyan-500"><ShieldIcon /></div>
            <h1 className="text-xl font-bold text-white tracking-wide">MLSecOps <span className="text-slate-400 font-normal">SOC Dashboard</span></h1>
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <div className="live-indicator mr-2"></div>
            Live Monitoring Active
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="bg-slate-900 border-b border-slate-800 px-6">
        <div className="flex space-x-1">
          {tabs.map((tab, idx) => (
            <button
              key={idx}
              onClick={() => setActiveTab(idx)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors border-b-2 ${
                activeTab === idx 
                  ? 'border-cyan-500 text-cyan-400' 
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
              }`}
            >
              {tab.icon}
              {tab.name}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="flex-1 p-6 overflow-auto">
        <div className="max-w-7xl mx-auto">
          {activeTab === 0 && <OverviewTab />}
          {activeTab === 1 && <AlertFeedTab />}
          {activeTab === 2 && <ThreatInspectorTab />}
          {activeTab === 3 && <ModelHealthTab />}
          {activeTab === 4 && <SystemStatusTab />}
        </div>
      </main>
    </div>
  );
}

// --- Tab 1: Overview ---
function OverviewTab() {
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [systemHealth, setSystemHealth] = useState<SystemHealthResponse | null>(null);
  const [recentAlerts, setRecentAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, modelRes, healthRes, alertsRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/alerts/stats`).catch(() => null),
        fetch(`${API_URL}/api/v1/model/info`).catch(() => null),
        fetch(`${API_URL}/api/v1/system/health`).catch(() => null),
        fetch(`${API_URL}/api/v1/alerts?limit=10`).catch(() => null),
      ]);

      if (statsRes?.ok) setStats(await statsRes.json());
      if (modelRes?.ok) setModelInfo(await modelRes.json());
      if (healthRes?.ok) setSystemHealth(await healthRes.json());
      if (alertsRes?.ok) setRecentAlerts(await alertsRes.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading) return <div className="text-center text-slate-400 mt-20">Loading dashboard...</div>;

  const isSystemHealthy = systemHealth?.services?.every(s => s.status === 'healthy') ?? false;

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="soc-card p-5">
          <div className="text-slate-400 text-sm mb-1">Total Alerts (24h)</div>
          <div className="text-3xl font-bold text-white">{stats?.alerts_24h || 0}</div>
        </div>
        <div className="soc-card p-5">
          <div className="text-slate-400 text-sm mb-1">All-time Threats</div>
          <div className="text-3xl font-bold text-red-500">{stats?.total_alerts || 0}</div>
        </div>
        <div className="soc-card p-5">
          <div className="text-slate-400 text-sm mb-1">Model F1 Score</div>
          <div className="text-3xl font-bold text-cyan-400">
            {modelInfo?.f1_score ? (modelInfo.f1_score * 100).toFixed(1) + '%' : 'N/A'}
          </div>
        </div>
        <div className="soc-card p-5">
          <div className="text-slate-400 text-sm mb-1">System Health</div>
          <div className={`text-3xl font-bold ${isSystemHealthy ? 'text-green-500' : 'text-amber-500'}`}>
            {isSystemHealthy ? '100%' : 'Degraded'}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Charts */}
        <div className="soc-card p-5 lg:col-span-2">
          <h3 className="text-lg font-medium text-white mb-4">Alert Trend (24h)</h3>
          <div className="bar-chart-container h-48">
            {stats?.by_hour?.length ? stats.by_hour.map((item, i) => {
              const max = Math.max(...stats.by_hour.map(h => h.count), 1);
              const height = (item.count / max) * 100;
              return (
                <div 
                  key={i} 
                  className="bar" 
                  style={{ height: `${height}%` }}
                  title={`${item.hour}: ${item.count} alerts`}
                />
              );
            }) : <div className="text-slate-500 w-full text-center self-center">No data available</div>}
          </div>
        </div>

        <div className="soc-card p-5">
          <h3 className="text-lg font-medium text-white mb-4">Threat Types</h3>
          <div className="space-y-3">
            {stats?.by_type && Object.keys(stats.by_type).length > 0 ? Object.entries(stats.by_type).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between">
                <span className="text-sm text-slate-300">{type}</span>
                <span className="badge badge-high">{count}</span>
              </div>
            )) : <div className="text-slate-500 text-sm">No threats detected</div>}
          </div>
        </div>
      </div>

      {/* Recent Alerts */}
      <div className="soc-card overflow-hidden">
        <div className="p-5 border-b border-slate-800">
          <h3 className="text-lg font-medium text-white">Recent Alerts</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="soc-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Type</th>
                <th>Port</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {recentAlerts.map(alert => (
                <tr key={alert.id}>
                  <td>{new Date(alert.timestamp).toLocaleString()}</td>
                  <td>
                    <span className={`badge ${alert.attack_type.toLowerCase() === 'benign' ? 'badge-benign' : 'badge-critical'}`}>
                      {alert.attack_type}
                    </span>
                  </td>
                  <td>{alert.destination_port}</td>
                  <td>{(alert.confidence * 100).toFixed(1)}%</td>
                </tr>
              ))}
              {recentAlerts.length === 0 && (
                <tr>
                  <td colSpan={4} className="text-center text-slate-500 py-8">No recent alerts</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// --- Tab 2: Alert Feed ---
function AlertFeedTab() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filter, setFilter] = useState('All');
  const [loading, setLoading] = useState(true);

  const fetchAlerts = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/alerts?limit=50`);
      if (res.ok) {
        setAlerts(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 10000);
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  const getSeverityClass = (confidence: number) => {
    if (confidence > 0.9) return 'badge-critical';
    if (confidence > 0.7) return 'badge-high';
    if (confidence > 0.5) return 'badge-medium';
    return 'badge-low';
  };

  const getSeverityText = (confidence: number) => {
    if (confidence > 0.9) return 'Critical';
    if (confidence > 0.7) return 'High';
    if (confidence > 0.5) return 'Medium';
    return 'Low';
  };

  const filteredAlerts = alerts.filter(a => {
    if (filter === 'All') return true;
    return getSeverityText(a.confidence) === filter;
  });

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {['All', 'Critical', 'High', 'Medium'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              filter === f ? 'bg-cyan-600 text-white' : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      <div className="soc-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="soc-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Attack Type</th>
                <th>Port</th>
                <th>Duration (ms)</th>
                <th>Confidence</th>
                <th>Severity</th>
              </tr>
            </thead>
            <tbody>
              {filteredAlerts.map(alert => (
                <tr key={alert.id}>
                  <td className="text-slate-300">{new Date(alert.timestamp).toLocaleString()}</td>
                  <td className="font-mono text-cyan-400">{alert.attack_type}</td>
                  <td>{alert.destination_port}</td>
                  <td>{alert.flow_duration}</td>
                  <td>
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-cyan-500" 
                          style={{ width: `${alert.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-xs">{(alert.confidence * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td>
                    <span className={`badge ${getSeverityClass(alert.confidence)}`}>
                      {getSeverityText(alert.confidence)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {filteredAlerts.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center py-16 text-slate-500">
              <ShieldIcon />
              <p className="mt-4">No alerts detected yet</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// --- Tab 3: Threat Inspector ---
function ThreatInspectorTab() {
  const [features, setFeatures] = useState<Record<string, number>>({
    destination_port: 80,
    flow_duration: 1000,
    total_fwd_packets: 10,
    flow_bytes_s: 500,
  });
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const presets = {
    Benign: { destination_port: 443, flow_duration: 5000000, total_fwd_packets: 12, flow_bytes_s: 1500 },
    DDoS: { destination_port: 80, flow_duration: 100, total_fwd_packets: 200, flow_bytes_s: 5000000 },
    PortScan: { destination_port: 22, flow_duration: 50, total_fwd_packets: 1, flow_bytes_s: 0 },
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFeatures(prev => ({ ...prev, [e.target.name]: parseFloat(e.target.value) || 0 }));
  };

  const handlePredict = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(features),
      });
      if (res.ok) {
        setResult(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="space-y-6">
        <div className="soc-card p-6">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-medium text-white">Manual Traffic Inspection</h3>
            <div className="flex gap-2">
              {Object.entries(presets).map(([name, vals]) => (
                <button
                  key={name}
                  onClick={() => setFeatures(prev => ({ ...prev, ...vals }))}
                  className="px-3 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors border border-slate-700"
                >
                  {name}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            {['destination_port', 'flow_duration', 'total_fwd_packets', 'flow_bytes_s'].map(field => (
              <div key={field}>
                <label className="block text-sm font-medium text-slate-400 mb-1">
                  {field.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                </label>
                <input
                  type="number"
                  name={field}
                  value={features[field]}
                  onChange={handleChange}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-white focus:outline-none focus:border-cyan-500"
                />
              </div>
            ))}
          </div>

          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="mt-4 text-sm text-cyan-500 hover:text-cyan-400"
          >
            {showAdvanced ? '- Hide Advanced Features' : '+ Show Advanced Features'}
          </button>

          {showAdvanced && (
            <div className="mt-4 p-4 bg-slate-900 rounded border border-slate-800 text-sm text-slate-500">
              Advanced feature inputs would go here. (Placeholder)
            </div>
          )}

          <button
            onClick={handlePredict}
            disabled={loading}
            className="w-full mt-6 bg-cyan-600 hover:bg-cyan-500 text-white font-medium py-2 rounded transition-colors disabled:opacity-50"
          >
            {loading ? 'Analyzing...' : 'Analyze Traffic'}
          </button>
        </div>
      </div>

      <div>
        <div className="soc-card p-6 min-h-[300px] flex flex-col justify-center">
          {result ? (
            <div className="text-center space-y-6">
              <h4 className="text-slate-400 uppercase tracking-widest text-sm">Analysis Result</h4>
              
              <div className={`inline-block px-6 py-3 rounded-lg border-2 ${
                !result.is_attack 
                  ? 'bg-green-900/20 border-green-500/50 text-green-400'
                  : 'bg-red-900/20 border-red-500/50 text-red-400'
              }`}>
                <div className="text-2xl font-bold tracking-wider">
                  {!result.is_attack ? 'TRAFFIC SAFE' : 'THREAT DETECTED'}
                </div>
              </div>

              <div className="space-y-2 max-w-xs mx-auto mt-8">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Classification</span>
                  <span className="font-mono text-white">{result.attack_type}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Confidence</span>
                  <span className="font-mono text-white">{(result.confidence * 100).toFixed(2)}%</span>
                </div>
                <div className="w-full h-2 bg-slate-800 rounded-full mt-2 overflow-hidden">
                  <div 
                    className={`h-full ${!result.is_attack ? 'bg-green-500' : 'bg-red-500'}`}
                    style={{ width: `${result.confidence * 100}%` }}
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center text-slate-600">
              <ShieldIcon />
              <p className="mt-4">Submit traffic features to view analysis</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// --- Tab 4: Model Performance ---
function ModelHealthTab() {
  const [info, setInfo] = useState<ModelInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloading, setReloading] = useState(false);

  const fetchModelInfo = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/model/info`);
      if (res.ok) setInfo(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchModelInfo();
  }, [fetchModelInfo]);

  const handleReload = async () => {
    setReloading(true);
    try {
      await fetch(`${API_URL}/api/v1/reload-model`, { method: 'POST' });
      await fetchModelInfo();
    } catch (e) {
      console.error(e);
    } finally {
      setReloading(false);
    }
  };

  if (loading) return <div className="text-slate-400">Loading model info...</div>;

  if (!info || info.status === 'not_trained') {
    return (
      <div className="soc-card p-10 text-center max-w-2xl mx-auto">
        <CpuIcon />
        <h3 className="text-xl font-medium text-white mt-4 mb-2">No Model Trained Yet</h3>
        <p className="text-slate-400 mb-6">Run the Dagster pipeline to train and register the initial model.</p>
        <a href="http://exp.s3.fsbm.ma:4301" target="_blank" rel="noreferrer" className="inline-block bg-cyan-600 hover:bg-cyan-500 text-white font-medium px-6 py-2 rounded">
          Open Dagster
        </a>
      </div>
    );
  }

  const metrics = [
    { label: 'F1 Score', value: info.f1_score, color: 'text-cyan-400' },
    { label: 'Precision', value: info.precision, color: 'text-green-400' },
    { label: 'Recall', value: info.recall, color: 'text-amber-400' },
    { label: 'Accuracy', value: info.accuracy, color: 'text-blue-400' },
  ];

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="soc-card p-6 flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-3">
            {info.model_name}
            <span className="badge badge-low text-xs">{info.status}</span>
          </h2>
          <div className="text-sm text-slate-400 mt-2 flex gap-6">
            <span>Version: <strong className="text-slate-200">{info.model_version}</strong></span>
            <span>Trained: <strong className="text-slate-200">{info.training_date ? new Date(info.training_date).toLocaleString() : 'Unknown'}</strong></span>
          </div>
        </div>
        <button
          onClick={handleReload}
          disabled={reloading}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded text-sm text-white transition-colors"
        >
          {reloading ? 'Reloading...' : 'Reload Model'}
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {metrics.map(m => (
          <div key={m.label} className="soc-card p-6 text-center">
            <div className="text-slate-400 text-sm mb-4">{m.label}</div>
            <div className={`text-4xl font-bold ${m.color}`}>
              {(m.value * 100).toFixed(1)}%
            </div>
            <div className="w-full h-1 bg-slate-800 mt-4 rounded-full overflow-hidden">
              <div className="h-full bg-current" style={{ width: `${m.value * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- Tab 5: System Status ---
function SystemStatusTab() {
  const [health, setHealth] = useState<SystemHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchHealth = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/v1/system/health`);
      if (res.ok) setHealth(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  const serviceLinks: Record<string, string> = {
    'FastAPI': 'http://exp.s3.fsbm.ma:4308/docs',
    'MLflow': 'http://exp.s3.fsbm.ma:4302',
    'Dagster': 'http://exp.s3.fsbm.ma:4301',
    'Grafana': 'http://exp.s3.fsbm.ma:4307',
    'PostgreSQL': '#',
    'Redpanda': '#',
  };

  const defaultServices = ['api', 'mlflow', 'postgres', 'redpanda', 'dagster'];
  const servicesData = health?.services || defaultServices.map(name => ({ name, status: 'checking', latency_ms: 0, detail: '' }));

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-white">Platform Services</h2>
        <button
          onClick={fetchHealth}
          disabled={loading}
          className="text-sm px-4 py-2 bg-slate-800 rounded hover:bg-slate-700 text-slate-300"
        >
          {loading ? 'Refreshing...' : 'Refresh Status'}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {servicesData.map((data: any) => (
          <div key={data.name} className="soc-card p-5">
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-slate-800 rounded text-slate-400">
                  <ServerIcon />
                </div>
                <div className="font-medium text-white capitalize">{data.name}</div>
              </div>
              <span className={`badge ${
                data.status === 'healthy' || data.status === 'up' ? 'badge-low' : 
                data.status === 'checking' ? 'bg-slate-800 text-slate-400' : 'badge-critical'
              }`}>
                {data.status || 'unknown'}
              </span>
            </div>
            
            <div className="flex justify-between items-end mt-4">
              <div className="text-sm text-slate-400">
                Latency: <span className="text-slate-200 font-mono">{data.latency_ms || 0}ms</span>
                {data.detail && <div className="text-xs text-slate-500 truncate mt-1 max-w-[150px]">{data.detail}</div>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}