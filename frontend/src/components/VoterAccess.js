/* global BigInt */
import React, { useState } from 'react';
import axios from 'axios';
import { Shield, Lock, CheckCircle, AlertCircle, Fingerprint } from 'lucide-react';
import './VoterAccess.css';

const VoterAccess = () => {
  const [loginMode, setLoginMode] = useState('voter'); // 'voter' or 'admin'

  const [step, setStep] = useState('login'); // login, mfa, dashboard
  const [identity, setIdentity] = useState('');
  const [token, setToken] = useState(null);
  const [otp, setOtp] = useState('');
  const [mfaData, setMfaData] = useState(null);
  const [messages, setMessages] = useState([]);
  const [eligibility, setEligibility] = useState(null);
  const [electionData, setElectionData] = useState(null);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [voteReceipt, setVoteReceipt] = useState(null);
  const [blindedToken, setBlindedToken] = useState(null); // Valid token for voting
  const [signature, setSignature] = useState(null); // State for the signature

  // Hardcoded election ID for demo purposes
  const electionId = "00000000-0000-0000-0000-000000000001";

  // Helper for logging messages
  const log = (msg) => {
    setMessages(prev => [...prev, msg]);
    console.log(msg);
  };



  // Fetch election details on mount
  React.useEffect(() => {
    const fetchElection = async () => {
      try {
        // Use the hardcoded demo election ID
        const res = await axios.get(`/api/mock/election-stats?election_id=${electionId}`);
        setElectionData(res.data.election);
      } catch (err) {
        log(`Failed to load election data: ${err.message}`);
      }
    };
    fetchElection();
  }, []);

  // Real OIDC Login
  const handleLogin = async () => {
    log(`Attempting login for: ${identity}`);
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
      log(`Login Error: ${err.response?.data?.detail || err.message}`);
    }
  };

  // Real MFA Setup
  const setupMfa = async () => {
    log("Setting up MFA...");
    try {
      const res = await axios.post(
        '/auth/mfa/setup',
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setMfaData(res.data);
      log("MFA Setup initiated. Scan QR code (URI provided).");
    } catch (err) {
      log(`MFA Setup Error: ${err.response?.data?.detail || err.message}`);
    }
  };

  // Real MFA Verification
  const verifyMfa = async () => {
    log(`Verifying OTP: ${otp}`);
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
      log(`MFA Verify Error: ${err.response?.data?.detail || err.message}`);
    }
  };

  // Real Eligibility Check
  const checkEligibility = async () => {
    log("Checking voter eligibility...");
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

  // Real Blind Credential Issuance
  const issueCredential = async () => {
    if (!eligibility?.is_eligible) {
      log("You are not eligible to receive a credential.");
      return;
    }
    log("Requesting blind credential...");
    log("Requesting blind credential...");
    try {
      // Client-side blinding logic would go here.
      // Construct structured payload: "election_id|expiry|nonce"
      const expiry = Math.floor(Date.now() / 1000) + 86400; // 24h
      const nonce = Math.floor(Math.random() * 1000000).toString();
      const payloadStr = `${electionId}|${expiry}|${nonce}`;

      // Convert string to BigInt matches Python's int.from_bytes(..., 'big')
      const encoder = new TextEncoder();
      const bytes = encoder.encode(payloadStr);
      let hex = "";
      for (let b of bytes) {
        hex += b.toString(16).padStart(2, '0');
      }
      const blindedPayload = BigInt("0x" + hex).toString();

      const res = await axios.post(
        `/api/voter/credential/issue`,
        {
          election_id: electionId,
          blinded_payload: blindedPayload
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setSignature(res.data.signature);
      setBlindedToken(blindedPayload); // Save for voting
      log(`Credential Issued! Signature: ${res.data.signature.substring(0, 20)}...`);
    } catch (err) {
      log(`Issuance Error: ${err.response?.data?.detail || err.message}`);
    }
  };

  const castVote = async () => {
    if (!selectedCandidate) {
      log("Please select a candidate first.");
      return;
    }
    if (!blindedToken || !signature) {
      log("No valid credential found. Please get a blind credential first.");
      return;
    }

    try {
      // Simulate client-side encryption (In a real app, use Paillier/ElGamal JS lib here)
      const votePayload = JSON.stringify({
        candidate_id: selectedCandidate,
        timestamp: Date.now()
      });

      const res = await axios.post('/api/voter/vote', {
        election_id: electionId,
        token: blindedToken, // The token we got signed
        signature: signature,
        vote_ciphertext: votePayload
      });

      setVoteReceipt(res.data);
      setStep('voted');
      log(`Vote Cast Successfully! Receipt: ${res.data.receipt_hash.substring(0, 15)}...`);
    } catch (err) {
      log(`Vote Error: ${err.response?.data?.detail || err.message}`);
    }
  };

  // Voted View
  if (step === 'voted') {
    return (
      <div className="voter-access project-box">
        <h2>🗳️ Vote Submitted</h2>
        <div className="login-card" style={{ maxWidth: '500px', margin: '2rem auto', textAlign: 'center' }}>
          <CheckCircle size={64} color="#10b981" style={{ marginBottom: '1rem' }} />
          <h3>Thank you for voting!</h3>
          <p>Your vote has been anonymously cast and recorded on the immutable ledger.</p>

          <div className="credential-box" style={{ marginTop: '2rem', textAlign: 'left' }}>
            <p><strong>Receipt Hash:</strong></p>
            <code style={{ wordBreak: 'break-all' }}>{voteReceipt?.receipt_hash}</code>
            <p style={{ marginTop: '1rem' }}>
              <strong>Timestamp:</strong> {new Date(voteReceipt?.timestamp).toLocaleString()}
            </p>
          </div>

          <button className="auth-btn" style={{ marginTop: '2rem' }} onClick={() => setStep('dashboard')}>
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  // ... (rest of functions)

  // Login View
  if (step === 'login') {
    return (
      <div className="login-container">
        <div className="login-card">
          <div className="brand-section">
            <div className="logo-icon">{loginMode === 'voter' ? '🗳️' : '🛡️'}</div>
            <h1 className="login-title">
              {loginMode === 'voter' ? 'National E-Voting Portal' : 'Administrative Access'}
            </h1>
            <p className="login-subtitle">
              {loginMode === 'voter' ? 'Secure Identity Verification System' : 'Restricted System Access -- Authorized Personnel Only'}
            </p>
          </div>

          <div className="login-form">
            <div className="input-group">
              <label className="input-label">
                {loginMode === 'voter' ? 'Digital ID / Email' : 'Admin / Trustee Username'}
              </label>
              <input
                className="input-field"
                type="text"
                placeholder={loginMode === 'voter' ? "Enter your Digital ID" : "username"}
                value={identity}
                onChange={e => setIdentity(e.target.value)}
              />
            </div>

            <button className={`auth-btn ${loginMode === 'admin' ? 'admin-theme' : ''}`} onClick={handleLogin}>
              <Lock className="auth-icon" />
              {loginMode === 'voter' ? 'Authenticate with OIDC' : 'System Login'}
            </button>
          </div>

          <div className="admin-link">
            <button className="admin-login-btn" onClick={() => setLoginMode(loginMode === 'voter' ? 'admin' : 'voter')}>
              {loginMode === 'voter' ? 'Login as Administrator / Trustee' : 'Return to Voter Login'}
            </button>
          </div>

          {loginMode === 'admin' && (
            <div style={{ marginTop: '10px', fontSize: '0.8rem', color: '#666' }}>
              <p>Demo Config (Hardcoded):</p>
              <ul style={{ listStyle: 'none', padding: 0 }}>
                <li>Admin: <code>admin123</code></li>
                <li>Trustee: <code>trustee1</code></li>
              </ul>
            </div>
          )}

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
                <p><small style={{ color: '#10b981' }}>Ready to Vote</small></p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Voting Booth - Visible only after getting signature */}
      {signature && electionData && (
        <div className="voting-booth" style={{ marginTop: '2rem', padding: '1.5rem', background: 'white', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          <h2 style={{ borderBottom: '2px solid #3b82f6', paddingBottom: '0.5rem' }}>🗳️ Voting Booth: {electionData.title}</h2>
          <p style={{ color: '#666', marginBottom: '1.5rem' }}>Select your candidate. Your vote will be anonymously cast.</p>

          <div className="candidates-list" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
            {electionData.candidates && electionData.candidates.map(c => (
              <label key={c.id} className={`candidate-card ${selectedCandidate === c.id ? 'selected' : ''}`}
                style={{
                  padding: '1rem',
                  border: selectedCandidate === c.id ? '2px solid #3b82f6' : '1px solid #eee',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  background: selectedCandidate === c.id ? '#eff6ff' : 'white',
                  transition: 'all 0.2s'
                }}
              >
                <input
                  type="radio"
                  name="candidate"
                  value={c.id}
                  onChange={() => setSelectedCandidate(c.id)}
                  style={{ marginRight: '10px' }}
                />
                <strong>{c.name}</strong>
                <div style={{ fontSize: '0.8rem', color: '#888' }}>{c.party}</div>
              </label>
            ))}
          </div>

          <button
            className="auth-btn"
            style={{ marginTop: '2rem', background: '#ec4899', fontSize: '1.1rem' }}
            onClick={castVote}
          >
            🔒 Cast Private Vote
          </button>
        </div>
      )}

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

