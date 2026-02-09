import React, { useState, useEffect } from 'react';
import './App.css';
import ResultsDashboard from './components/ResultsDashboard';

import TrusteePanel from './components/TrusteePanel';
import TestingPanel from './components/TestingPanel';
import OpsDashboard from './components/OpsDashboard';
import VerificationPortal from './components/VerificationPortal';
import SecurityLab from './components/SecurityLab';
import LedgerExplorer from './components/LedgerExplorer';
import VoterAccess from './components/VoterAccess';
import { authAPI } from './services/api';

function App() {
  const roleOrder = ['voter', 'trustee', 'auditor', 'security_engineer', 'admin'];
  const [activeTab, setActiveTab] = useState('results');
  const [systemStatus, setSystemStatus] = useState({ status: 'checking...' });
  const [authRole, setAuthRole] = useState(localStorage.getItem('authRole'));
  const [credential, setCredential] = useState('');
  const [authError, setAuthError] = useState(null);
  const [selectedRole, setSelectedRole] = useState('voter');

  useEffect(() => {
    // Check backend health on mount using proxy
    fetch('/health')
      .then(res => res.json())
      .then(data => setSystemStatus(data))
      .catch(() => setSystemStatus({ status: 'offline' }));
  }, []);

  const availableTabsByRole = {
    admin: ['results', 'ledger', 'trustees', 'testing', 'ops', 'verification', 'security'],
    trustee: ['trustees', 'results', 'ledger', 'verification'],
    auditor: ['results', 'ledger', 'ops', 'verification'],
    security_engineer: ['security', 'ops', 'ledger', 'verification'],
    voter: ['voter', 'results', 'ledger', 'verification'],
  };

  const roleCredentialHint = {
    admin: 'admin',
    trustee: 'trustee',
    auditor: 'auditor',
    security_engineer: 'security_engineer',
    voter: 'voter1'
  };

  const roleCredentialPlaceholder = {
    admin: 'admin',
    trustee: 'trustee',
    auditor: 'auditor',
    security_engineer: 'security_engineer',
    voter: 'voter1 (voter1-voter5)'
  };

  const allowedTabs = availableTabsByRole[authRole] || ['voter', 'results', 'ledger', 'verification'];

  useEffect(() => {
    if (!allowedTabs.includes(activeTab)) {
      setActiveTab(allowedTabs[0]);
    }
  }, [authRole]);

  const handleLogin = async () => {
    setAuthError(null);
    try {
      const res = await authAPI.login(credential);
      localStorage.setItem('authToken', res.data.access_token);
      localStorage.setItem('authRole', res.data.role);
      setAuthRole(res.data.role);
      setCredential('');
    } catch (err) {
      setAuthError(err.response?.data?.detail || 'Login failed');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('authRole');
    setAuthRole(null);
    setActiveTab('results');
  };

  const handleRoleChange = (e) => {
    const role = e.target.value;
    setSelectedRole(role);
    setCredential(roleCredentialHint[role] || '');
  };

  if (!authRole) {
    return (
      <div className="App">
        <div className="login-screen">
          <div className="login-card glass-panel">
            <div className="login-banner">
              <h1>🗳️ E-Voting System</h1>
              <p>Secure role-based access to election workflows</p>
            </div>

            <div className="system-status">
              Backend: <span className={systemStatus.status === 'healthy' ? 'status-healthy' : 'status-offline'}>
                {systemStatus.status}
              </span>
            </div>

            <div className="login-form">
              <label className="login-label">Select Role</label>
              <select className="role-select" value={selectedRole} onChange={handleRoleChange}>
                {roleOrder.map(role => (
                  <option key={role} value={role}>
                    {role.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
                  </option>
                ))}
              </select>

              <label className="login-label">Credential</label>
              <input
                type="text"
                placeholder={`Example: ${roleCredentialPlaceholder[selectedRole] || 'user123'}`}
                value={credential}
                onChange={(e) => setCredential(e.target.value)}
              />

              <div className="login-actions">
                <button className="btn-auth" onClick={handleLogin}>
                  Login
                </button>
                <span className="login-hint">
                  {selectedRole === 'voter'
                    ? 'Voter credentials: voter1-voter5'
                    : 'Role-based dashboards load after login'}
                </span>
              </div>

              {authError && <div className="auth-error">{authError}</div>}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>🗳️ E-Voting System</h1>
        <p>Verification & Audit Ops</p>
        <div className="system-status">
          Backend: <span className={systemStatus.status === 'healthy' ? 'status-healthy' : 'status-offline'}>
            {systemStatus.status}
          </span>
        </div>
        <div className="auth-bar">
          <div className="auth-status">
            <span className="auth-role">Role: {authRole}</span>
            <button className="btn-auth" onClick={handleLogout}>Logout</button>
          </div>
        </div>
      </header>

      <nav className="App-nav">
        {allowedTabs.includes('results') && (
          <button className={activeTab === 'results' ? 'active' : ''} onClick={() => setActiveTab('results')}>
            📊 Results
          </button>
        )}
        {allowedTabs.includes('voter') && (
          <button className={activeTab === 'voter' ? 'active' : ''} onClick={() => setActiveTab('voter')}>
            👤 Voter Access
          </button>
        )}
        {allowedTabs.includes('trustees') && (
          <button className={activeTab === 'trustees' ? 'active' : ''} onClick={() => setActiveTab('trustees')}>
            🔐 Trustees
          </button>
        )}
        {allowedTabs.includes('ledger') && (
          <button className={activeTab === 'ledger' ? 'active' : ''} onClick={() => setActiveTab('ledger')}>
            🔗 Ledger
          </button>
        )}
        {allowedTabs.includes('testing') && (
          <button className={activeTab === 'testing' ? 'active' : ''} onClick={() => setActiveTab('testing')}>
            🧪 Testing
          </button>
        )}
        {allowedTabs.includes('ops') && (
          <button className={activeTab === 'ops' ? 'active' : ''} onClick={() => setActiveTab('ops')}>
            🛡️ Ops & Audit
          </button>
        )}
        {allowedTabs.includes('verification') && (
          <button className={activeTab === 'verification' ? 'active' : ''} onClick={() => setActiveTab('verification')}>
            ✅ Verification
          </button>
        )}
        {allowedTabs.includes('security') && (
          <button className={activeTab === 'security' ? 'active' : ''} onClick={() => setActiveTab('security')}>
            🧪 Security Lab
          </button>
        )}
      </nav>

      <main className="App-main">
        {activeTab === 'results' && <ResultsDashboard />}
        {activeTab === 'voter' && <VoterAccess authRole={authRole} />}
        {activeTab === 'trustees' && <TrusteePanel />}
        {activeTab === 'ledger' && <LedgerExplorer />}
        {activeTab === 'testing' && <TestingPanel />}
        {activeTab === 'ops' && <OpsDashboard />}
        {activeTab === 'verification' && <VerificationPortal />}
        {activeTab === 'security' && <SecurityLab />}
      </main>

      <footer className="App-footer">
        <p>Privacy-Preserving Tallying & Result Verification</p>
        <p>Threshold: 3-of-5 Trustees | Homomorphic Encryption Enabled</p>
      </footer>
    </div>
  );
}

export default App;
