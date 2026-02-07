import React, { useState } from 'react';
import axios from 'axios';
import { Shield, Lock, CheckCircle, AlertCircle, Fingerprint } from 'lucide-react';
import './VoterAccess.css';

const VoterAccess = () => {
  const [step, setStep] = useState('login'); // login, mfa, dashboard
  const [identity, setIdentity] = useState('');
  const [token, setToken] = useState(null);
  const [otp, setOtp] = useState('');
  const [mfaData, setMfaData] = useState(null);
  const [messages, setMessages] = useState([]);
  const [eligibility, setEligibility] = useState(null);
  const [signature, setSignature] = useState(null);

  // Temporary election ID for demo
  const electionId = "00000000-0000-0000-0000-000000000001";

  const log = (msg) => setMessages(prev => [...prev, `${new Date().toLocaleTimeString()} - ${msg}`]);

  const handleLogin = async () => {
    try {
      const res = await axios.post('/auth/login', { credential: identity });
      log("Login response received");

      if (res.data.mfa_required) {
        setToken(res.data.access_token);
        setStep('mfa_login');
        log("MFA Required");
      } else {
        setToken(res.data.access_token);
        setStep('dashboard');
        log("Logged in successfully");
      }
    } catch (err) {
      log(`Error: ${err.response?.data?.detail || err.message}`);
    }
  };

  const verifyMfa = async () => {
    try {
      const res = await axios.post(
        '/auth/mfa/verify',
        { token: otp },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setToken(res.data.access_token);
      setStep('dashboard');
      log("MFA Verified. Logged in.");
    } catch (err) {
      log(`MFA Error: ${err.response?.data?.detail || err.message}`);
    }
  };

  const setupMfa = async () => {
    try {
      const res = await axios.post(
        '/auth/mfa/setup',
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setMfaData(res.data);
      log("MFA Setup initiated. Scan QR code (URI provided).");
      // UI would render QR code here using res.data.provisioning_uri
    } catch (err) {
      log(`Setup Error: ${err.response?.data?.detail || err.message}`);
    }
  };

  const checkEligibility = async () => {
    try {
      const res = await axios.get(
        `/api/voter/eligibility/${electionId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setEligibility(res.data);
      log(`Eligibility: ${res.data.is_eligible ? "YES" : "NO"} (${res.data.reason_code})`);
    } catch (err) {
      log(`Check Error: ${err.response?.data?.detail || err.message}`);
    }
  };

  const issueCredential = async () => {
    try {
      // Client-side blinding logic would go here.
      // For demo, we send a mock "blinded" payload (just a random int).
      const blindedPayload = Math.floor(Math.random() * 1000000000).toString();

      const res = await axios.post(
        `/api/voter/credential/issue`,
        {
          election_id: electionId,
          blinded_payload: blindedPayload
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setSignature(res.data.signature);
      log(`Credential Issued! Signature: ${res.data.signature.substring(0, 20)}...`);
    } catch (err) {
      log(`Issuance Error: ${err.response?.data?.detail || err.message}`);
    }
  };

  // Login View
  if (step === 'login') {
    return (
      <div className="login-container">
        <div className="login-card">
          <div className="brand-section">
            <div className="logo-icon">🗳️</div>
            <h1 className="login-title">National E-Voting Portal</h1>
            <p className="login-subtitle">Secure Identity Verification System</p>
          </div>

          <div className="login-form">
            <div className="input-group">
              <label className="input-label">Digital ID / Email</label>
              <input
                className="input-field"
                type="text"
                placeholder="Enter your Digital ID"
                value={identity}
                onChange={e => setIdentity(e.target.value)}
              />
            </div>

            <button className="auth-btn" onClick={handleLogin}>
              <Lock className="auth-icon" />
              Authenticate with OIDC
            </button>
          </div>

          <div className="admin-link">
            <button className="admin-login-btn">Login as Administrator</button>
          </div>

          <div className="footer-badge">
            <Shield className="footer-icon" />
            <span>256-bit Secure System</span>
          </div>
        </div>
      </div>
    );
  }

  // MFA View
  if (step === 'mfa_login') {
    return (
      <div className="login-container">
        <div className="login-card">
          <div className="brand-section">
            <div className="logo-icon">🔐</div>
            <h1 className="login-title">Two-Factor Authentication</h1>
            <p className="login-subtitle">Please enter the code from your authenticator app.</p>
          </div>

          <div className="login-form">
            <div className="input-group">
              <label className="input-label">Authentication Code</label>
              <input
                className="input-field"
                type="text"
                placeholder="000 000"
                value={otp}
                onChange={e => setOtp(e.target.value)}
                style={{ textAlign: 'center', letterSpacing: '4px', fontSize: '1.2rem' }}
              />
            </div>

            <button className="auth-btn" onClick={verifyMfa}>
              Verify Identity
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Dashboard View
  return (
    <div className="voter-access project-box">
      <h2>👤 Voter Access & Credentials</h2>

      <div className="dashboard-controls">
        <div className="status-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Fingerprint size={16} />
            <span>Logged in as: <strong>{identity}</strong></span>
          </div>
          <button className="refresh-btn" style={{ padding: '4px 12px' }} onClick={() => setStep('login')}>Logout</button>
        </div>

        <div className="control-panel">
          <div className="card">
            <div className="card-header">
              <h3>🛡️ Security Settings</h3>
            </div>
            {!mfaData ? (
              <button className="auth-btn" style={{ marginTop: '1rem' }} onClick={setupMfa}>Enable 2FA Protection</button>
            ) : (
              <div className="mfa-setup">
                <p><strong>Config Secret:</strong> <code>{mfaData.secret}</code></p>
                <p style={{ fontSize: '0.8rem', color: '#666' }}>{mfaData.provisioning_uri}</p>
                <input
                  type="text"
                  className="input-field"
                  placeholder="Verify Code to Activate"
                  value={otp}
                  onChange={e => setOtp(e.target.value)}
                  style={{ marginTop: '10px' }}
                />
                <button className="auth-btn" style={{ marginTop: '10px' }} onClick={verifyMfa}>Activate 2FA</button>
              </div>
            )}
          </div>

          <div className="card">
            <h3>🗳️ Election Actions</h3>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', alignItems: 'center' }}>
              <button className="refresh-btn" onClick={checkEligibility}>Check Eligibility</button>
              {eligibility && (
                <span className={`status-badge ${eligibility.is_eligible ? 'success' : 'error'}`} style={{ padding: '4px 8px', borderRadius: '4px', background: eligibility.is_eligible ? '#d1fae5' : '#fee2e2', color: eligibility.is_eligible ? '#065f46' : '#991b1b' }}>
                  {eligibility.is_eligible ? <CheckCircle size={16} style={{ verticalAlign: 'middle' }} /> : <AlertCircle size={16} style={{ verticalAlign: 'middle' }} />}
                  {' '}{eligibility.is_eligible ? "Eligible" : "Ineligible"}
                </span>
              )}
            </div>

            <hr style={{ margin: '1.5rem 0', border: '0', borderTop: '1px solid #eee' }} />

            <button className="auth-btn" onClick={issueCredential} disabled={!eligibility?.is_eligible}>
              Get Blind Credential
            </button>
            {signature && (
              <div className="credential-box">
                <h4>✅ Credential Issued</h4>
                <textarea readOnly value={signature} />
                <p><small>Valid for Election ID: {electionId}</small></p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="log-console" style={{ marginTop: '2rem' }}>
        <h3>Audit / Activity Log</h3>
        <ul>
          {messages.map((m, i) => <li key={i}>{m}</li>)}
        </ul>
      </div>
    </div>
  );
};

export default VoterAccess;

