import { useState } from 'react';
import UploadForm from './components/UploadForm';
import ReviewQueue from './components/ReviewQueue';
import Dashboard from './components/Dashboard';
import { Leaf } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-2 text-emerald-600">
          <Leaf className="w-6 h-6" />
          <h1 className="text-xl font-bold">Breathe ESG</h1>
        </div>
        <nav className="flex space-x-4">
          <button 
            onClick={() => setActiveTab('dashboard')}
            className={`px-4 py-2 rounded-md font-medium ${activeTab === 'dashboard' ? 'bg-emerald-50 text-emerald-700' : 'text-gray-600 hover:bg-gray-50'}`}
          >
            Dashboard
          </button>
          <button 
            onClick={() => setActiveTab('upload')}
            className={`px-4 py-2 rounded-md font-medium ${activeTab === 'upload' ? 'bg-emerald-50 text-emerald-700' : 'text-gray-600 hover:bg-gray-50'}`}
          >
            Ingestion
          </button>
          <button 
            onClick={() => setActiveTab('review')}
            className={`px-4 py-2 rounded-md font-medium ${activeTab === 'review' ? 'bg-emerald-50 text-emerald-700' : 'text-gray-600 hover:bg-gray-50'}`}
          >
            Review Queue
          </button>
        </nav>
      </header>

      <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'upload' && <UploadForm />}
        {activeTab === 'review' && <ReviewQueue />}
      </main>
    </div>
  );
}

export default App;
