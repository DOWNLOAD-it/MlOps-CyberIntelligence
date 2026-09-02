"use client";
import { useState } from 'react';

export default function Home() {
  const [activeTab, setActiveTab] = useState('single');
  const [file, setFile] = useState<File | null>(null);
  const [prediction, setPrediction] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [formData, setFormData] = useState({
    destination_port: 80,
    flow_duration: 1000,
    total_fwd_packets: 5,
    flow_bytes_s: 500,
  });

  const handlePredict = async (e: any) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setPrediction(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4308';
      const res = await fetch(`${apiUrl}/api/v1/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      if (!res.ok) throw new Error('API Error');
      const data = await res.json();
      setPrediction(data);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to ML API');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 font-sans p-8">
      <div className="max-w-5xl mx-auto space-y-8">
        
        <header className="border-b border-gray-800 pb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
              <span className="text-blue-500">🛡️</span> MLSecOps Platform
            </h1>
            <p className="text-gray-400 mt-2">Real-time Network Threat Intelligence</p>
          </div>
          <div className="flex gap-4">
            <span className="px-3 py-1 bg-green-500/10 text-green-400 rounded-full text-sm font-medium border border-green-500/20">System Online</span>
          </div>
        </header>

        <main className="grid grid-cols-1 md:grid-cols-12 gap-8">
          
          <div className="col-span-12 md:col-span-8 space-y-6">
            
            <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden shadow-2xl">
              <div className="flex border-b border-gray-800">
                <button 
                  onClick={() => setActiveTab('single')}
                  className={`flex-1 py-4 text-sm font-medium transition-colors ${activeTab === 'single' ? 'bg-gray-800 text-white border-b-2 border-blue-500' : 'text-gray-400 hover:text-white hover:bg-gray-800/50'}`}>
                  Manual Threat Inspector
                </button>
                <button 
                  onClick={() => setActiveTab('batch')}
                  className={`flex-1 py-4 text-sm font-medium transition-colors ${activeTab === 'batch' ? 'bg-gray-800 text-white border-b-2 border-blue-500' : 'text-gray-400 hover:text-white hover:bg-gray-800/50'}`}>
                  Bulk Log Scanner
                </button>
              </div>

              <div className="p-6">
                {activeTab === 'single' ? (
                  <form onSubmit={handlePredict} className="space-y-6">
                    <div className="grid grid-cols-2 gap-6">
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-300">Destination Port</label>
                        <input type="number" value={formData.destination_port} onChange={e => setFormData({...formData, destination_port: Number(e.target.value)})} className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all" />
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-300">Flow Duration (ms)</label>
                        <input type="number" value={formData.flow_duration} onChange={e => setFormData({...formData, flow_duration: Number(e.target.value)})} className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all" />
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-300">Total Fwd Packets</label>
                        <input type="number" value={formData.total_fwd_packets} onChange={e => setFormData({...formData, total_fwd_packets: Number(e.target.value)})} className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all" />
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-gray-300">Flow Bytes / Sec</label>
                        <input type="number" value={formData.flow_bytes_s} onChange={e => setFormData({...formData, flow_bytes_s: Number(e.target.value)})} className="w-full bg-gray-950 border border-gray-800 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all" />
                      </div>
                    </div>
                    
                    <button type="submit" disabled={loading} className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2">
                      {loading ? 'Analyzing...' : 'Analyze Network Flow'}
                    </button>
                  </form>
                ) : (
                  <div className="border-2 border-dashed border-gray-700 rounded-xl p-12 flex flex-col items-center justify-center text-center space-y-4 hover:border-blue-500 hover:bg-gray-800/30 transition-all cursor-pointer">
                    <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center">
                      <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>
                    </div>
                    <div>
                      <p className="text-lg font-medium text-white">Drop your PCAP or CSV here</p>
                      <p className="text-sm text-gray-400 mt-1">Files up to 50MB are supported</p>
                    </div>
                    <button className="px-4 py-2 bg-gray-800 text-white rounded-lg text-sm font-medium hover:bg-gray-700">Select File</button>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="col-span-12 md:col-span-4 space-y-6">
            <div className="bg-gray-900 border border-gray-800 rounded-xl shadow-2xl p-6 h-full flex flex-col">
              <h2 className="text-lg font-semibold text-white mb-4">Analysis Result</h2>
              
              <div className="flex-1 flex flex-col items-center justify-center text-center">
                {!prediction && !loading && !error && (
                  <div className="text-gray-500">
                    <div className="w-16 h-16 border-2 border-gray-800 rounded-full mx-auto mb-4 flex items-center justify-center">🔍</div>
                    <p>Awaiting network payload...</p>
                  </div>
                )}

                {loading && (
                  <div className="animate-pulse flex flex-col items-center">
                    <div className="w-16 h-16 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mb-4"></div>
                    <p className="text-blue-400 font-medium">Running ML Inference...</p>
                  </div>
                )}

                {error && (
                  <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-lg w-full">
                    <p className="font-semibold text-sm">Connection Failed</p>
                    <p className="text-xs mt-1">{error}</p>
                  </div>
                )}

                {prediction && !loading && (
                  <div className={`w-full p-6 rounded-xl border ${prediction.is_attack ? 'bg-red-950/30 border-red-900/50' : 'bg-green-950/30 border-green-900/50'}`}>
                    <div className={`w-16 h-16 rounded-full mx-auto flex items-center justify-center text-3xl shadow-lg mb-4 ${prediction.is_attack ? 'bg-red-500/20 text-red-500 shadow-red-500/20' : 'bg-green-500/20 text-green-500 shadow-green-500/20'}`}>
                      {prediction.is_attack ? '⚠️' : '✅'}
                    </div>
                    <h3 className={`text-2xl font-bold mb-1 ${prediction.is_attack ? 'text-red-400' : 'text-green-400'}`}>
                      {prediction.is_attack ? 'Threat Detected' : 'Traffic Safe'}
                    </h3>
                    <p className="text-gray-400 text-sm mb-6">Classification: <span className="text-white font-medium">{prediction.attack_type}</span></p>
                    
                    <div className="bg-gray-950/50 rounded-lg p-4 text-left">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm text-gray-400">Confidence Score</span>
                        <span className="text-sm font-bold text-white">{(prediction.confidence * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-gray-800 rounded-full h-2">
                        <div className={`h-2 rounded-full ${prediction.is_attack ? 'bg-red-500' : 'bg-green-500'}`} style={{ width: `${prediction.confidence * 100}%` }}></div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
          
        </main>
      </div>
    </div>
  );
}