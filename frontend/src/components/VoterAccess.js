/* global BigInt */
import React, { useState } from 'react';
import axios from 'axios';
import { Shield, Lock, CheckCircle, AlertCircle, Fingerprint } from 'lucide-react';
import './VoterAccess.css';

/* global BigInt */
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Shield, Lock, CheckCircle, AlertCircle, Fingerprint } from 'lucide-react';
import './VoterAccess.css';

const VoterAccess = ({ authRole }) => {
  // Use authRole prop directly. No internal login state.

  const [step, setStep] = useState('dashboard');
  const [messages, setMessages] = useState([]);
  const [eligibility, setEligibility] = useState(null);
  const [electionData, setElectionData] = useState(null);
  const [electionError, setElectionError] = useState(null);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [voteReceipt, setVoteReceipt] = useState(null);
  const [blindedToken, setBlindedToken] = useState(null); // Valid token for voting
  const [signature, setSignature] = useState(null); // State for the signature
  const [language, setLanguage] = useState('en');
  const [showPreview, setShowPreview] = useState(false);
  const [voteError, setVoteError] = useState(null);
  const [retryCount, setRetryCount] = useState(0);

  // Mfa data for setup
  const [mfaData, setMfaData] = useState(null);
  const [otp, setOtp] = useState('');

  // Hardcoded election ID for demo purposes
  const electionId = "00000000-0000-0000-0000-000000000001";

  // Helper for logging messages
  const log = (msg) => {
    setMessages(prev => [...prev, msg]);
    console.log(msg);
  };

  const hashProof = async (payload) => {
    if (!window.crypto?.subtle) return '';
    const encoder = new TextEncoder();
    const data = encoder.encode(payload);
    const digest = await window.crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(digest));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  };

  // Fetch election details on mount
  useEffect(() => {
    const fetchElection = async () => {
      try {
        setElectionError(null);
        // Use the hardcoded demo election ID
        const res = await axios.get(`/api/mock/election-stats?election_id=${electionId}`);
        setElectionData(res.data.election);
      } catch (err) {
        const errorMessage = `Failed to load election data: ${err.response?.data?.detail || err.message}`;
        setElectionError(errorMessage);
        log(errorMessage);
      }
    };
    fetchElection();
  }, []);

  const handleElectionReload = async () => {
    try {
      setElectionError(null);
      const res = await axios.get(`/api/mock/election-stats?election_id=${electionId}`);
      setElectionData(res.data.election);
    } catch (err) {
      const errorMessage = `Failed to load election data: ${err.response?.data?.detail || err.message}`;
      setElectionError(errorMessage);
      log(errorMessage);
    }
  };

  const uiText = {
    en: {
      votingBooth: 'Voting Booth',
      selectCandidate: 'Select your candidate. Your vote will be anonymously cast.',
      review: 'Review & Encrypt',
      castVote: 'Cast Private Vote',
      confirmVote: 'Confirm and Submit',
      back: 'Go Back',
      retry: 'Retry with new nonce',
      languageLabel: 'Language'
    },
    ta: {
      votingBooth: 'வாக்குப்பதிவு அறை',
      selectCandidate: 'உங்கள் வேட்பாளரை தேர்வு செய்யவும். உங்கள் வாக்கு பாதுகாப்பாக பதிவாகும்.',
      review: 'மீளாய்வு செய்து குறியாக்கம் செய்',
      castVote: 'வாக்கை சமர்ப்பி',
      confirmVote: 'உறுதிப்படுத்தி சமர்ப்பி',
      back: 'மீண்டும் திரும்பு',
      retry: 'புதிய நான்ஸ் கொண்டு மீண்டும் முயற்சி',
      languageLabel: 'மொழி'
    }
  };

  const resolveCandidates = () => {
    if (!electionData) return [];
    let candidates = electionData.candidates;
    if (typeof candidates === 'string') {
      try {
        candidates = JSON.parse(candidates);
      } catch (parseError) {
        candidates = [];
      }
    }
    return Array.isArray(candidates) ? candidates : [];
  };


  const importPublicKey = async (pem) => {
    // Fetch key from PEM
    const pemHeader = "-----BEGIN PUBLIC KEY-----";
    const pemFooter = "-----END PUBLIC KEY-----";
    const pemContents = pem.substring(
      pem.indexOf(pemHeader) + pemHeader.length,
      pem.indexOf(pemFooter)
    ).replace(/(\r\n|\n|\r)/gm, "");

    // Base64 decode
    const binaryDerString = window.atob(pemContents);
    const binaryDer = new Uint8Array(binaryDerString.length);
    for (let i = 0; i < binaryDerString.length; i++) {
      binaryDer[i] = binaryDerString.charCodeAt(i);
    }

    return await window.crypto.subtle.importKey(
      "spki",
      binaryDer.buffer,
      {
        name: "RSA-OAEP",
        hash: "SHA-256"
      },
      true,
      ["encrypt"]
    );
  };

  const encryptVote = async (data) => {
    try {
      // Fetch System Key
      const keyRes = await axios.get('/api/security/system-key', {
        headers: { Authorization: `Bearer ${localStorage.getItem('authToken')}` }
      });
      const publicKeyPem = keyRes.data.public_key;
      const publicKey = await importPublicKey(publicKeyPem);

      const encoder = new TextEncoder();
      const encodedData = encoder.encode(data);

      const encryptedBuffer = await window.crypto.subtle.encrypt(
        { name: "RSA-OAEP" },
        publicKey,
        encodedData
      );

      // Convert to Base64
      const encryptedArray = new Uint8Array(encryptedBuffer);
      let binary = '';
      for (let i = 0; i < encryptedArray.length; i++) {
        binary += String.fromCharCode(encryptedArray[i]);
      }
      return window.btoa(binary);
    } catch (e) {
      log(`Encryption failed: ${e.message}`);
      throw e;
    }
  };

  const buildVoteSubmission = async () => {
    // Task 4c: Fix client-side encryption using RSA-OAEP
    const voteData = JSON.stringify({
      candidate_id: selectedCandidate,
      timestamp: Date.now()
    });

    // Encrypt using System Public Key (RSA-OAEP)
    // This creates an opaque ciphertext that the backend cannot inspect validation on directly 
    // until Tally phase (or if backend has private key to peek).
    const votePayload = await encryptVote(voteData);

    const nonce = `${Date.now()}-${Math.floor(Math.random() * 1000000)}`;
    const voteProof = await hashProof(`${electionId}|${nonce}|${votePayload}`);
    return { votePayload, nonce, voteProof };
  };


  // Real MFA Setup
  const setupMfa = async () => {
    log("Setting up MFA...");
    try {
      const res = await axios.post(
        '/auth/mfa/setup',
        {},
        { headers: { Authorization: `Bearer ${localStorage.getItem('authToken')}` } }
      );
      setMfaData(res.data);
      log("MFA Setup initiated. Scan QR code (URI provided).");
    } catch (err) {
      log(`MFA Setup Error: ${err.response?.data?.detail || err.message}`);
    }
  };

  // Real MFA Verification for Setup
  const verifyMfaSetup = async () => {
    log(`Verifying OTP: ${otp}`);
    try {
      const res = await axios.post(
        '/auth/mfa/verify',
        { token: otp },
        { headers: { Authorization: `Bearer ${localStorage.getItem('authToken')}` } }
      );
      setOtp('');
      setMfaData(null);
      log(res.data.message ? `MFA Setup Complete: ${res.data.message}` : "MFA Verified.");
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
        { headers: { Authorization: `Bearer ${localStorage.getItem('authToken')}` } }
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
        { headers: { Authorization: `Bearer ${localStorage.getItem('authToken')}` } }
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
      setVoteError(null);
      setRetryCount(0);
      const { votePayload, nonce, voteProof } = await buildVoteSubmission();

      const res = await axios.post('/api/voter/vote', {
        election_id: electionId,
        token: blindedToken, // The token we got signed
        signature: signature,
        vote_ciphertext: votePayload,
        nonce,
        vote_proof: voteProof,
        client_integrity: 'demo-build-1',
        version: 'v1'
      });

      setVoteReceipt(res.data);
      setStep('voted');
      log(`Vote Cast Successfully! Receipt: ${res.data.receipt_hash.substring(0, 15)}...`);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message;
      setVoteError(errorMessage);
      setRetryCount((count) => count + 1);
      log(`Vote Error: ${errorMessage}`);
    }
  };

  const retryVote = async () => {
    if (!selectedCandidate || !blindedToken || !signature) {
      return;
    }
    try {
      setVoteError(null);
      const { votePayload, nonce, voteProof } = await buildVoteSubmission();
      const res = await axios.post('/api/voter/vote', {
        election_id: electionId,
        token: blindedToken,
        signature: signature,
        vote_ciphertext: votePayload,
        nonce,
        vote_proof: voteProof,
        client_integrity: 'demo-build-1',
        version: 'v1'
      });
      setVoteReceipt(res.data);
      setStep('voted');
      log(`Vote Cast Successfully! Receipt: ${res.data.receipt_hash.substring(0, 15)}...`);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message;
      setVoteError(errorMessage);
      setRetryCount((count) => count + 1);
      log(`Vote Error: ${errorMessage}`);
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

  // Restricted access if not voter
  if (!authRole) {
    return (
      <div className="voter-access project-box">
        <h2>👤 Voter Access</h2>
        <div className="login-card" style={{ maxWidth: '500px', margin: '2rem auto', textAlign: 'center' }}>
          <Lock size={48} color="#6b7280" style={{ marginBottom: '1rem' }} />
          <h3>Authentication Required</h3>
          <p>Please log in via the main menu to access voting tools.</p>
        </div>
      </div>
    );
  }

  if (authRole !== 'voter') {
    return (
      <div className="voter-access project-box">
        <h2>👤 Voter Access</h2>
        <div className="login-card" style={{ maxWidth: '500px', margin: '2rem auto', textAlign: 'center' }}>
          <AlertCircle size={48} color="#b45309" style={{ marginBottom: '1rem' }} />
          <h3>Restricted Access</h3>
          <p>Voting tools are available to the voter role only. You are currently logged in as <strong>{authRole}</strong>.</p>
        </div>
      </div>
    );
  }

  // Dashboard View for Voter
  return (
    <div className="voter-access project-box">
      <h2>👤 Voter Access & Credentials</h2>

      <div className="dashboard-controls">
        <div className="status-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Fingerprint size={16} />
            <span>Logged in as: <strong>Voter</strong></span>
          </div>
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
                <button className="auth-btn" style={{ marginTop: '10px' }} onClick={verifyMfaSetup}>Activate 2FA</button>
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
                {!electionData && (
                  <p style={{ marginTop: '0.5rem', color: '#b45309', fontSize: '0.85rem' }}>
                    Election details not loaded yet. Scroll down to retry loading the ballot.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Voting Booth - Visible only after getting signature */}
      {signature && (
        <div className="voting-booth" style={{ marginTop: '2rem', padding: '1.5rem', background: 'white', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          {electionData ? (
            <>
              <h2 style={{ borderBottom: '2px solid #3b82f6', paddingBottom: '0.5rem' }}>🗳️ {uiText[language]?.votingBooth || uiText.en.votingBooth}: {electionData.title}</h2>
              <p style={{ color: '#666', marginBottom: '1rem' }}>{uiText[language]?.selectCandidate || uiText.en.selectCandidate}</p>

              <div className="language-row" style={{ marginBottom: '1.5rem' }}>
                <label className="input-label" style={{ marginRight: '0.5rem' }}>{uiText[language]?.languageLabel || uiText.en.languageLabel}:</label>
                <select className="input-field" value={language} onChange={(e) => setLanguage(e.target.value)} style={{ maxWidth: '220px' }}>
                  <option value="en">English</option>
                  <option value="ta">Tamil</option>
                </select>
              </div>

              {resolveCandidates().length > 0 ? (
                <div className="candidates-list" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
                  {resolveCandidates().map(c => (
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
                        aria-label={`Select ${c.name}`}
                        style={{ marginRight: '10px' }}
                      />
                      <strong>{c.name}</strong>
                      <div style={{ fontSize: '0.8rem', color: '#888' }}>{c.party}</div>
                    </label>
                  ))}
                </div>
              ) : (
                <p style={{ color: '#b45309' }}>No candidates available for this election.</p>
              )}

              {!showPreview && (
                <button
                  className="auth-btn"
                  style={{ marginTop: '2rem', background: '#2563eb', fontSize: '1.05rem' }}
                  onClick={() => setShowPreview(true)}
                >
                  🔎 {uiText[language]?.review || uiText.en.review}
                </button>
              )}

              {showPreview && (
                <div className="preview-box" style={{ marginTop: '1.5rem' }}>
                  <h4>Review Selection</h4>
                  <p>
                    Selected Candidate:{' '}
                    <strong>
                      {resolveCandidates().find((c) => c.id === selectedCandidate)?.name || 'Unknown'}
                    </strong>
                  </p>
                  <div className="preview-actions">
                    <button className="btn-secondary" onClick={() => setShowPreview(false)}>
                      {uiText[language]?.back || uiText.en.back}
                    </button>
                    <button className="auth-btn" style={{ background: '#ec4899' }} onClick={castVote}>
                      🔒 {uiText[language]?.confirmVote || uiText.en.confirmVote}
                    </button>
                  </div>
                </div>
              )}

              {voteError && (
                <div className="preview-box" style={{ marginTop: '1.25rem' }}>
                  <p style={{ color: '#b45309' }}>Vote error: {voteError}</p>
                  {retryCount < 3 && (
                    <button className="btn-secondary" onClick={retryVote}>
                      {uiText[language]?.retry || uiText.en.retry}
                    </button>
                  )}
                </div>
              )}
            </>
          ) : (
            <>
              <h2 style={{ borderBottom: '2px solid #3b82f6', paddingBottom: '0.5rem' }}>🗳️ Voting Booth</h2>
              <p style={{ color: '#666', marginBottom: '1rem' }}>Election details could not be loaded yet.</p>
              {electionError && <p style={{ color: '#b45309', marginBottom: '1rem' }}>{electionError}</p>}
              <button className="auth-btn" onClick={handleElectionReload}>
                Reload Ballot
              </button>
            </>
          )}
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

