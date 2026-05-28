import { useState } from 'react';
import { UploadCloud } from 'lucide-react';
import axios from 'axios';

const UploadForm = () => {
  const [file, setFile] = useState(null);
  const [sourceType, setSourceType] = useState('1'); // Maps to a DataSource ID
  const [status, setStatus] = useState('');

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file && sourceType !== '3') {
        setStatus("Please select a file.");
        return;
    }
    
    setStatus("Uploading...");
    
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      if (sourceType === '3') {
        // Mock JSON webhook for Travel data
        const payload = [
          { id: "T1001", travel_type: "Flight", origin_airport: "JFK", destination_airport: "LHR", traveler_email: "ceo@company.com" },
          { id: "T1002", travel_type: "Flight", origin_airport: "XXX", destination_airport: "SFO", traveler_email: "sales@company.com" }
        ];
        
        await axios.post(`${API_URL}/api/ingestion/upload_json/`, {
          tenant_id: 1,
          data_source_id: 3,
          payload: payload
        });
      } else {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('tenant_id', 1);
        formData.append('data_source_id', sourceType);

        await axios.post(`${API_URL}/api/ingestion/upload_csv/`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
      }
      
      setStatus("Upload successful! Records are being normalized.");
    } catch (err) {
      console.error(err);
      setStatus("Error during upload.");
    }
  };

  return (
    <div className="bg-white p-8 rounded-lg shadow-sm border max-w-2xl mx-auto">
      <h2 className="text-2xl font-semibold mb-6">Data Ingestion</h2>
      
      <form onSubmit={handleUpload} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Data Source</label>
          <select 
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value)}
            className="w-full border-gray-300 rounded-md shadow-sm focus:ring-emerald-500 focus:border-emerald-500 p-2 border"
          >
            <option value="1">SAP - Fuel Procurement (CSV)</option>
            <option value="2">Utility Portal - Electricity (CSV)</option>
            <option value="3">Travel Portal - Flights (JSON API Simulation)</option>
          </select>
        </div>

        {sourceType !== '3' && (
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:bg-gray-50 transition-colors cursor-pointer">
            <UploadCloud className="mx-auto h-12 w-12 text-gray-400" />
            <div className="mt-4 flex text-sm text-gray-600 justify-center">
              <label className="relative cursor-pointer rounded-md font-medium text-emerald-600 hover:text-emerald-500 focus-within:outline-none">
                <span>Upload a file</span>
                <input type="file" className="sr-only" onChange={(e) => setFile(e.target.files[0])} />
              </label>
              <p className="pl-1">or drag and drop</p>
            </div>
            <p className="text-xs text-gray-500 mt-2">CSV up to 10MB</p>
            {file && <p className="text-sm font-medium text-gray-900 mt-4">Selected: {file.name}</p>}
          </div>
        )}

        {sourceType === '3' && (
          <div className="bg-blue-50 p-4 rounded-md border border-blue-200">
            <p className="text-sm text-blue-800">
              This will simulate receiving a JSON payload from a travel booking platform via webhook.
            </p>
          </div>
        )}

        <div className="flex items-center justify-between">
          <button
            type="submit"
            className="bg-emerald-600 text-white px-6 py-2 rounded-md hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500"
          >
            {sourceType === '3' ? 'Trigger Webhook' : 'Upload File'}
          </button>
          
          {status && <span className="text-sm font-medium text-gray-600">{status}</span>}
        </div>
      </form>
    </div>
  );
};

export default UploadForm;
