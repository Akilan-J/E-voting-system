import React, { useState, useEffect } from 'react';
import './App.css';
import ResultsDashboard from './components/ResultsDashboard';
import TrusteePanel from './components/TrusteePanel';
import TestingPanel from './components/TestingPanel';
import LedgerExplorer from './components/LedgerExplorer';
import VoterAccess from './components/VoterAccess';

function App() {
  const [activeTab, setActiveTab] = useState('results');
  const [systemStatus, setSystemStatus] = useState({ status: 'checking...' });

  useEffect(() => {
    // Check backend health on mount using proxy
    fetch('/health')
      .then(res => res.json())
      .then(data => setSystemStatus(data))
      .catch(() => setSystemStatus({ status: 'offline' }));
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>🗳️ E-Voting System</h1>
        <p>Privacy-Preserving Tallying & Result Verification</p>
        <div className="system-status">
          Backend: <span className={systemStatus.status === 'healthy' ? 'status-healthy' : 'status-offline'}>
            {systemStatus.status}
          </span>
        </div>
      </header>

      <nav className="App-nav">
        <button
          className={activeTab === 'results' ? 'active' : ''}
          onClick={() => setActiveTab('results')}
        >
          📊 Results
        </button>
        <button
          className={activeTab === 'voter' ? 'active' : ''}
          onClick={() => setActiveTab('voter')}
        >
          👤 Voter Access
        </button>
        <button
          className={activeTab === 'trustees' ? 'active' : ''}
          onClick={() => setActiveTab('trustees')}
        >
          🔐 Trustees
        </button>
        <button
          className={activeTab === 'ledger' ? 'active' : ''}
          onClick={() => setActiveTab('ledger')}
        >
          🔗 Ledger
        </button>
        <button
          className={activeTab === 'testing' ? 'active' : ''}
          onClick={() => setActiveTab('testing')}
        >
          🧪 Testing
        </button>
      </nav>

      <main className="App-main">
        {activeTab === 'results' && <ResultsDashboard />}
        {activeTab === 'voter' && <VoterAccess />}
        {activeTab === 'trustees' && <TrusteePanel />}
        {activeTab === 'ledger' && <LedgerExplorer />}
        {activeTab === 'testing' && <TestingPanel />}
      </main>

      <footer className="App-footer">
        <p>Privacy-Preserving Tallying & Result Verification</p>
        <p>Threshold: 3-of-5 Trustees | Homomorphic Encryption Enabled</p>
      </footer>
    </div>
  );
}

export default App;
