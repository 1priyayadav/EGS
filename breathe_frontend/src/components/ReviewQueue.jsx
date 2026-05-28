import { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle2, XCircle, Edit3, History, ArrowRight } from 'lucide-react';
import axios from 'axios';

const ReviewQueue = () => {
  const [records, setRecords] = useState([]);
  const [filter, setFilter] = useState('FLAGGED');
  const [selectedRecord, setSelectedRecord] = useState(null);

  useEffect(() => {
    fetchRecords();
  }, [filter]);

  const fetchRecords = async () => {
    try {
      const endpoint = filter === 'FLAGGED' ? 'flagged' : 'pending';
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await axios.get(`${API_URL}/api/records/${endpoint}/`);
      setRecords(response.data);
    } catch (err) {
      console.error(err);
      // Fallback for UI testing
      if (filter === 'FLAGGED' && records.length === 0) {
        setRecords([
          {
            id: 1,
            category: 'SCOPE_3',
            activity_type: 'Flight',
            status: 'FLAGGED',
            validation_flags: ['impossible airport pair'],
            raw_record: { raw_payload: { origin_airport: 'XXX', destination_airport: 'SFO' } },
            auto_normalized_payload: { origin_airport: 'XXX', destination_airport: 'SFO', raw_value: 0 },
            audit_history: []
          }
        ]);
      }
    }
  };

  const handleAction = async (action, payload = null, reason = '') => {
    if (!selectedRecord) return;
    
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      await axios.post(`${API_URL}/api/records/${selectedRecord.id}/review/`, {
        action,
        corrected_payload: payload,
        correction_reason: reason
      });
      setSelectedRecord(null);
      fetchRecords();
    } catch (err) {
      console.error(err);
      alert('Action failed. See console.');
    }
  };

  return (
    <div className="flex space-x-6 h-[calc(100vh-8rem)]">
      {/* Left List */}
      <div className="w-1/3 bg-white rounded-lg shadow-sm border overflow-hidden flex flex-col">
        <div className="flex border-b">
          <button 
            className={`flex-1 py-3 text-sm font-medium ${filter === 'FLAGGED' ? 'border-b-2 border-red-500 text-red-600' : 'text-gray-500'}`}
            onClick={() => setFilter('FLAGGED')}
          >
            Flagged {filter === 'FLAGGED' ? `(${records.length})` : ''}
          </button>
          <button 
            className={`flex-1 py-3 text-sm font-medium ${filter === 'PENDING' ? 'border-b-2 border-amber-500 text-amber-600' : 'text-gray-500'}`}
            onClick={() => setFilter('PENDING')}
          >
            Pending Review {filter === 'PENDING' ? `(${records.length})` : ''}
          </button>
        </div>
        
        <div className="overflow-y-auto flex-1 p-2 space-y-2 bg-gray-50">
          {records.map(record => (
            <div 
              key={record.id}
              onClick={() => setSelectedRecord(record)}
              className={`p-4 rounded-md cursor-pointer border ${selectedRecord?.id === record.id ? 'border-emerald-500 bg-emerald-50' : 'border-gray-200 bg-white hover:border-gray-300'}`}
            >
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-bold text-gray-500 uppercase">{record.category} - {record.activity_type}</span>
                {record.status === 'FLAGGED' ? (
                  <AlertCircle className="w-4 h-4 text-red-500" />
                ) : (
                  <span className="w-2 h-2 rounded-full bg-amber-400 mt-1"></span>
                )}
              </div>
              <p className="text-sm font-medium text-gray-900 truncate">
                {record.validation_flags.length > 0 ? (
                  <span className="text-red-600">{record.validation_flags.join(', ')}</span>
                ) : 'Awaiting Sign-off'}
              </p>
            </div>
          ))}
          {records.length === 0 && <p className="text-sm text-gray-500 p-4 text-center">No records found.</p>}
        </div>
      </div>

      {/* Right Detail Panel */}
      <div className="w-2/3 bg-white rounded-lg shadow-sm border flex flex-col overflow-hidden">
        {selectedRecord ? (
          <RecordDetail key={selectedRecord.id} record={selectedRecord} onAction={handleAction} />
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
            <CheckCircle2 className="w-12 h-12 mb-4 text-gray-300" />
            <p>Select a record from the queue to review.</p>
          </div>
        )}
      </div>
    </div>
  );
};

const RecordDetail = ({ record, onAction }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editPayload, setEditPayload] = useState(
    JSON.stringify(record.analyst_corrected_payload || record.auto_normalized_payload, null, 2)
  );
  const [editReason, setEditReason] = useState('');

  const submitEdit = () => {
    try {
      const parsed = JSON.parse(editPayload);
      onAction('EDIT', parsed, editReason);
      setIsEditing(false);
    } catch (e) {
      alert("Invalid JSON format");
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-6 border-b flex justify-between items-start">
        <div>
          <h2 className="text-xl font-semibold mb-1">Review Record #{record.id}</h2>
          <div className="flex space-x-2 text-sm text-gray-500">
            <span>{record.category}</span>
            <span>&bull;</span>
            <span>{record.activity_type}</span>
          </div>
        </div>
        <div className="flex space-x-2">
          {!isEditing && (
            <>
              <button onClick={() => setIsEditing(true)} className="px-3 py-1.5 text-sm border rounded-md hover:bg-gray-50 flex items-center">
                <Edit3 className="w-4 h-4 mr-1" /> Edit
              </button>
              <button onClick={() => onAction('REJECT')} className="px-3 py-1.5 text-sm border border-red-200 text-red-600 bg-red-50 hover:bg-red-100 rounded-md flex items-center">
                <XCircle className="w-4 h-4 mr-1" /> Reject
              </button>
              <button onClick={() => onAction('APPROVE')} className="px-3 py-1.5 text-sm bg-emerald-600 text-white hover:bg-emerald-700 rounded-md flex items-center">
                <CheckCircle2 className="w-4 h-4 mr-1" /> Approve
              </button>
            </>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {record.validation_flags.length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 flex items-start">
            <AlertCircle className="w-5 h-5 text-red-600 mr-3 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-semibold text-red-800">Normalization Anomalies Detected</h4>
              <ul className="list-disc list-inside text-sm text-red-700 mt-1">
                {record.validation_flags.map((f, i) => <li key={i}>{f}</li>)}
              </ul>
            </div>
          </div>
        )}

        {isEditing ? (
          <div className="space-y-4">
            <h3 className="font-medium">Correct Payload</h3>
            <textarea 
              className="w-full h-48 font-mono text-sm p-3 border rounded-md focus:ring-emerald-500 focus:border-emerald-500"
              value={editPayload}
              onChange={e => setEditPayload(e.target.value)}
            />
            <input 
              type="text" 
              placeholder="Correction Reason (Required for audit trail)" 
              className="w-full p-2 border rounded-md"
              value={editReason}
              onChange={e => setEditReason(e.target.value)}
            />
            <div className="flex justify-end space-x-2">
              <button onClick={() => setIsEditing(false)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-md">Cancel</button>
              <button onClick={submitEdit} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700">Save Correction</button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-6">
            <div>
              <h3 className="font-medium text-sm text-gray-500 mb-2 uppercase">Raw Ingestion Payload</h3>
              <pre className="bg-gray-100 p-4 rounded-md text-xs font-mono overflow-x-auto">
                {JSON.stringify(record.raw_record?.raw_payload, null, 2)}
              </pre>
            </div>
            <div>
              <div className="flex items-center space-x-2 mb-2">
                <ArrowRight className="w-4 h-4 text-gray-400" />
                <h3 className="font-medium text-sm text-emerald-600 uppercase">Normalized Payload</h3>
              </div>
              <pre className={`p-4 rounded-md text-xs font-mono overflow-x-auto ${record.analyst_corrected_payload ? 'bg-blue-50 border border-blue-100' : 'bg-emerald-50 border border-emerald-100'}`}>
                {JSON.stringify(record.analyst_corrected_payload || record.auto_normalized_payload, null, 2)}
              </pre>
            </div>
          </div>
        )}

        <div>
          <h3 className="font-medium text-sm text-gray-500 mb-3 flex items-center"><History className="w-4 h-4 mr-1" /> Lineage & Audit History</h3>
          <div className="space-y-3">
            {record.audit_history?.map(event => (
              <div key={event.id} className="text-sm flex">
                <span className="text-gray-400 w-32 shrink-0">{new Date(event.timestamp).toLocaleString()}</span>
                <span className="font-medium w-32 shrink-0">{event.action_type}</span>
                <span className="text-gray-700 flex-1">{event.notes}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReviewQueue;
