import React, { useState, useEffect } from 'react';
import './App.css';
import ResultsDashboard from './components/ResultsDashboard';

import TrusteePanel from './components/TrusteePanel';
import TestingPanel from './components/TestingPanel';
import OpsDashboard from './components/OpsDashboard';
import VerificationPortal from './components/VerificationPortal';
import SecurityLab from './components/SecurityLab';
import TallyAudit from './components/TallyAudit';
import LedgerExplorer from './components/LedgerExplorer';
import VoterAccess from './components/VoterAccess';
import axios from 'axios';
import { authAPI } from './services/api';
import { Lock, Vote, BarChart2, User, Scale, Key, Link, FlaskConical, Shield, CheckCircle, TestTube2 } from 'lucide-react';

function App() {
  const roleOrder = ['voter', 'trustee', 'auditor', 'security_engineer', 'admin'];
  const [activeTab, setActiveTab] = useState('results');
  const [systemStatus, setSystemStatus] = useState({ status: 'checking...' });
  const [credential, setCredential] = useState('');
  const [authError, setAuthError] = useState(null);
  const [selectedRole, setSelectedRole] = useState('voter');
  const [mfaPending, setMfaPending] = useState(false);
  const [mfaOtp, setMfaOtp] = useState('');
  const [mfaToken, setMfaToken] = useState(null);

  // Clean up stale mfa_pending role from previous broken sessions
  const storedRole = localStorage.getItem('authRole');
  const initialRole = (storedRole === 'mfa_pending') ? null : storedRole;
  if (storedRole === 'mfa_pending') {
    localStorage.removeItem('authRole');
    localStorage.removeItem('authToken');
  }
  const [authRole, setAuthRole] = useState(initialRole);

  useEffect(() => {
    // Check backend health on mount using proxy
    fetch('/health')
      .then(res => res.json())
      .then(data => setSystemStatus(data))
      .catch(() => setSystemStatus({ status: 'offline' }));
  }, []);

  const availableTabsByRole = {
    admin: ['results', 'tally', 'trustees', 'ledger', 'testing', 'ops', 'verification', 'security'],
    trustee: ['trustees', 'tally', 'results', 'ledger', 'verification'],
    auditor: ['results', 'tally', 'ledger', 'ops', 'verification'],
    security_engineer: ['security', 'ops', 'ledger', 'verification', 'tally'],
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
      if (res.data.mfa_required) {
        // MFA is enabled — store temp token and show OTP screen
        setMfaToken(res.data.access_token);
        setMfaPending(true);
        setAuthError(null);
      } else {
        localStorage.setItem('authToken', res.data.access_token);
        localStorage.setItem('authRole', res.data.role);
        setAuthRole(res.data.role);
        setCredential('');
      }
    } catch (err) {
      setAuthError(err.response?.data?.detail || 'Login failed');
    }
  };

  const handleMfaVerify = async () => {
    setAuthError(null);
    try {
      const res = await axios.post(
        '/auth/mfa/verify',
        { token: mfaOtp },
        { headers: { Authorization: `Bearer ${mfaToken}` } }
      );
      localStorage.setItem('authToken', res.data.access_token);
      localStorage.setItem('authRole', res.data.role);
      setAuthRole(res.data.role);
      setMfaPending(false);
      setMfaOtp('');
      setMfaToken(null);
      setCredential('');
    } catch (err) {
      setAuthError(err.response?.data?.detail || 'Invalid OTP');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('authRole');
    setAuthRole(null);
    setActiveTab('results');
    setMfaPending(false);
    setMfaOtp('');
    setMfaToken(null);
  };

  const handleRoleChange = (e) => {
    const role = e.target.value;
    setSelectedRole(role);
    setCredential(roleCredentialHint[role] || '');
  };

  if (!authRole) {
    // MFA verification screen
    if (mfaPending) {
      return (
        <div className="App">
          <div className="login-screen">
            <div className="login-card glass-panel">
              <div className="login-banner">
                <h1>Two-Factor Authentication</h1>
                <p>Enter the code from your authenticator app</p>
              </div>

              <div className="login-form">
                <label className="login-label">Authentication Code</label>
                <input
                  type="text"
                  placeholder="Enter 6-digit OTP"
                  value={mfaOtp}
                  onChange={(e) => setMfaOtp(e.target.value)}
                  style={{ textAlign: 'center', letterSpacing: '4px', fontSize: '1.2rem' }}
                  onKeyDown={(e) => e.key === 'Enter' && handleMfaVerify()}
                />

                <div className="login-actions">
                  <button className="btn-auth" onClick={handleMfaVerify}>
                    Verify
                  </button>
                  <button className="btn-auth" style={{ background: '#6b7280', marginLeft: '0.5rem' }} onClick={() => { setMfaPending(false); setMfaToken(null); setMfaOtp(''); }}>
                    Cancel
                  </button>
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
        <div className="login-screen">
          <div className="login-card glass-panel">
            <div className="login-banner">
              <h1>E-Voting System</h1>
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
                onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
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
        <h1><Vote className="inline-icon mr-2" /> E-Voting System</h1>
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
            Results
          </button>
        )}
        {allowedTabs.includes('voter') && (
          <button className={activeTab === 'voter' ? 'active' : ''} onClick={() => setActiveTab('voter')}>
            Voter Access
          </button>
        )}
        {allowedTabs.includes('tally') && (
          <button className={activeTab === 'tally' ? 'active' : ''} onClick={() => setActiveTab('tally')}>
            Tally & Audit
          </button>
        )}
        {allowedTabs.includes('trustees') && (
          <button className={activeTab === 'trustees' ? 'active' : ''} onClick={() => setActiveTab('trustees')}>
            Trustees
          </button>
        )}
        {allowedTabs.includes('ledger') && (
          <button className={activeTab === 'ledger' ? 'active' : ''} onClick={() => setActiveTab('ledger')}>
            Ledger
          </button>
        )}
        {allowedTabs.includes('testing') && (
          <button className={activeTab === 'testing' ? 'active' : ''} onClick={() => setActiveTab('testing')}>
            Testing
          </button>
        )}
        {allowedTabs.includes('ops') && (
          <button className={activeTab === 'ops' ? 'active' : ''} onClick={() => setActiveTab('ops')}>
            Ops Center
          </button>
        )}
        {allowedTabs.includes('verification') && (
          <button className={activeTab === 'verification' ? 'active' : ''} onClick={() => setActiveTab('verification')}>
            Verification
          </button>
        )}
        {allowedTabs.includes('security') && (
          <button className={activeTab === 'security' ? 'active' : ''} onClick={() => setActiveTab('security')}>
            Security Lab
          </button>
        )}
      </nav>

      <main className="App-main">
        {activeTab === 'results' && <ResultsDashboard />}
        {activeTab === 'voter' && <VoterAccess authRole={authRole} />}
        {activeTab === 'tally' && <TallyAudit />}
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
