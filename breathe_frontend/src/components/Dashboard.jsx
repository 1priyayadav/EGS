import { useState, useEffect } from 'react';
import { BarChart, Activity, AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import axios from 'axios';

const Dashboard = () => {
  const [stats, setStats] = useState({ TOTAL: 0, FLAGGED: 0, PENDING: 0, APPROVED: 0, REJECTED: 0 });

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/records/stats/');
      setStats(response.data);
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  };

  const cards = [
    { title: 'Total Ingested', count: stats.TOTAL, icon: <Activity className="w-6 h-6 text-blue-500" />, bg: 'bg-blue-50', border: 'border-blue-200' },
    { title: 'Flagged Anomalies', count: stats.FLAGGED, icon: <AlertTriangle className="w-6 h-6 text-red-500" />, bg: 'bg-red-50', border: 'border-red-200' },
    { title: 'Pending Review', count: stats.PENDING, icon: <Clock className="w-6 h-6 text-amber-500" />, bg: 'bg-amber-50', border: 'border-amber-200' },
    { title: 'Approved', count: stats.APPROVED, icon: <CheckCircle className="w-6 h-6 text-emerald-500" />, bg: 'bg-emerald-50', border: 'border-emerald-200' },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center space-x-3 mb-8">
        <BarChart className="w-8 h-8 text-emerald-600" />
        <h1 className="text-2xl font-bold text-gray-800">System Overview</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {cards.map((card, idx) => (
          <div key={idx} className={`p-6 rounded-xl border ${card.border} ${card.bg} shadow-sm flex flex-col`}>
            <div className="flex justify-between items-start">
              <h3 className="text-gray-600 font-medium">{card.title}</h3>
              {card.icon}
            </div>
            <div className="mt-4">
              <span className="text-4xl font-bold text-gray-900">{card.count}</span>
            </div>
          </div>
        ))}
      </div>
      
      <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm mt-8">
        <h3 className="font-semibold text-gray-800 mb-4">Ingestion Health</h3>
        <p className="text-sm text-gray-600">
          The pipeline is actively listening for incoming payloads via API webhooks and CSV uploads. 
          Currently, <strong>{stats.FLAGGED}</strong> records require analyst intervention due to schema drift or semantic anomalies, 
          while <strong>{stats.PENDING}</strong> records are awaiting final sign-off.
        </p>
      </div>
    </div>
  );
};

export default Dashboard;
