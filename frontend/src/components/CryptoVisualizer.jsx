import React, { useState, useEffect } from 'react';
import { Lock, Unlock, BarChart2, Plus, Users, CheckCircle, Target, Calculator, Play, GraduationCap, ShieldCheck, FileText, User } from 'lucide-react';
import { mockDataAPI, tallyingAPI, trusteesAPI, resultsAPI } from '../services/api';
import './CryptoVisualizer.css';

/**
 * Cryptographic Process Visualizer
 * Shows real-time encryption, aggregation, and decryption workflow
 */
function CryptoVisualizer() {
  const [stats, setStats] = useState(null);
  const [trustees, setTrustees] = useState([]);
  const [tallyStatus, setTallyStatus] = useState(null);
  const [results, setResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [logs, setLogs] = useState([]);
  const [electionId, setElectionId] = useState(null);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const statsRes = await mockDataAPI.getElectionStats();
      setStats(statsRes.data);
      setElectionId(statsRes.data.election?.id);

      if (statsRes.data.election?.id) {
        const trusteesRes = await trusteesAPI.getAll();
        setTrustees(trusteesRes.data);

        if (statsRes.data.tallying?.started) {
          const statusRes = await tallyingAPI.getStatus(statsRes.data.election.id);
          setTallyStatus(statusRes.data);
        }

        try {
          const resultsRes = await resultsAPI.getByElectionId(statsRes.data.election.id);
          setResults(resultsRes.data);
        } catch (err) {
          // Results not available yet
        }
      }
    } catch (err) {
      console.error('Failed to load data:', err);
    }
  };

  const addLog = (message, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [...prev, { timestamp, message, type, id: Date.now() }]);
  };

  // Step 1: Generate and encrypt votes
  const handleGenerateVotes = async () => {
    setIsLoading(true);
    addLog('[LOCK] Starting vote encryption process...', 'info');

    try {
      addLog('Generating Paillier keypair for election...', 'info');
      addLog('Splitting private key using Shamir Secret Sharing (3-of-5)...', 'info');

      const response = await mockDataAPI.generateVotes(20, electionId);

      addLog(`[SUCCESS] Successfully encrypted ${response.data.votes_generated} votes`, 'success');
      addLog('Each vote encrypted as: E(v) = gᵐ · rⁿ mod n²', 'info');

      await loadData();
    } catch (err) {
      addLog(`[ERROR] Encryption failed: ${err.response?.data?.detail || err.message}`, 'error');
    }
    setIsLoading(false);
  };

  // Step 2: Aggregate encrypted votes
  const handleStartTally = async () => {
    if (!electionId) return;

    setIsLoading(true);
    addLog('[INFO] Starting homomorphic aggregation...', 'info');

    try {
      addLog('Multiplying ciphertexts: E(Σvᵢ) = ∏ E(vᵢ) mod n²', 'info');

      const response = await tallyingAPI.start(electionId);



      addLog('[SUCCESS] Votes aggregated without decryption!', 'success');
      addLog(`Session ID: ${response.data.session_id}`, 'info');

      await loadData();

    } catch (err) {
      addLog(`[ERROR] Aggregation failed: ${err.response?.data?.detail || err.message}`, 'error');
    }
    setIsLoading(false);
  };

  // Step 3: Partial decryptions by trustees
  const handleTrusteeDecrypt = async (trusteeId, trusteeName) => {
    if (!electionId) return;

    setIsLoading(true);
    addLog(`[INFO] ${trusteeName} computing partial decryption...`, 'info');

    try {
      await tallyingAPI.partialDecrypt(trusteeId, electionId);



      addLog(`[SUCCESS] ${trusteeName} completed! (Share ${trustees.filter(t => t.has_decrypted).length + 1}/5)`, 'success');

      await loadData();

      if (tallyStatus?.partial_decryptions >= 3) {
        addLog('[TARGET] Threshold reached! 3/5 trustees completed', 'success');
      }
    } catch (err) {
      addLog(`[ERROR] ${trusteeName} failed: ${err.response?.data?.detail || err.message}`, 'error');
    }
    setIsLoading(false);
  };

  // Step 4: Finalize with Lagrange interpolation
  const handleFinalize = async () => {
    if (!electionId) return;

    setIsLoading(true);
    addLog('[INFO] Combining partial decryptions using Lagrange interpolation...', 'info');

    try {
      const response = await tallyingAPI.finalize(electionId);



      addLog('[SUCCESS] Tally finalized! Results revealed:', 'success');
      Object.entries(response.data.final_tally || {}).forEach(([candidate, count]) => {
        addLog(`  ${candidate}: ${count} votes`, 'info');
      });

      await loadData();

    } catch (err) {
      addLog(`[ERROR] Finalization failed: ${err.response?.data?.detail || err.message}`, 'error');
    }
    setIsLoading(false);
  };

  // Clear logs
  const clearLogs = () => setLogs([]);

  return (
    <div className="crypto-visualizer">
      {/* Header */}
      <div className="viz-header">
        <h2>Cryptographic Process Visualization</h2>
        <p>Real-time privacy-preserving tallying workflow</p>
      </div>

      {/* Current Status */}
      <div className="status-overview">
        <div className="status-card">
          <span className="status-label"> Total Votes</span>
          <span className="status-value">{stats?.votes?.total || 0}</span>
        </div>
        <div className="status-card">
          <span className="status-label"> Encrypted</span>
          <span className="status-value">{stats?.votes?.total || 0}</span>
        </div>
        <div className="status-card">
          <span className="status-label"> Aggregated</span>
          <span className="status-value">{tallyStatus?.aggregated ? 'Yes' : 'No'}</span>
        </div>
        <div className="status-card">
          <span className="status-label"> Trustees</span>
          <span className="status-value">{tallyStatus?.partial_decryptions || 0}/5</span>
        </div>
        <div className="status-card">
          <span className="status-label"> Finalized</span>
          <span className="status-value">{results ? 'Yes' : 'No'}</span>
        </div>
      </div>

      {/* Main Workflow Panel */}
      <div className="workflow-container">
        <div className="workflow-left">
          <h3>Workflow Steps</h3>

          {/* Step 1: Encryption */}
          <div className="workflow-step">
            <div className="step-header">
              <span className="step-number">1</span>
              <h4>Paillier Encryption</h4>
            </div>
            <p>Generate and encrypt votes using homomorphic encryption</p>
            <button
              className="step-btn"
              onClick={handleGenerateVotes}
              disabled={isLoading || stats?.votes?.total > 0}
            >
              {stats?.votes?.total > 0 ? <> Votes Generated</> : <> Generate Votes</>}
            </button>
            {stats?.votes?.total > 0 && (
              <div className="step-info">
                <span> {stats.votes.total} votes encrypted</span>
                <span>E(v) = gᵐ · rⁿ mod n²</span>
              </div>
            )}
          </div>

          {/* Step 2: Aggregation */}
          <div className="workflow-step">
            <div className="step-header">
              <span className="step-number">2</span>
              <h4>Homomorphic Aggregation</h4>
            </div>
            <p>Multiply encrypted votes to add plaintexts without decryption</p>
            <button
              className="step-btn"
              onClick={handleStartTally}
              disabled={isLoading || !stats?.votes?.total || tallyStatus?.aggregated}
            >
              {tallyStatus?.aggregated ? <> Aggregated</> : <> Start Aggregation</>}
            </button>
            {tallyStatus?.aggregated && (
              <div className="step-info">
                <span> All votes combined</span>
                <span>E(Σvᵢ) = ∏ E(vᵢ)</span>
              </div>
            )}
          </div>

          {/* Step 3: Threshold Decryption */}
          <div className="workflow-step">
            <div className="step-header">
              <span className="step-number">3</span>
              <h4>Threshold Decryption (3-of-5)</h4>
            </div>
            <p>At least 3 trustees must provide partial decryptions</p>

            <div className="trustees-grid">
              {trustees.map((trustee, idx) => (
                <button
                  key={trustee.id}
                  className={`trustee-btn ${trustee.has_decrypted ? 'completed' : ''}`}
                  onClick={() => handleTrusteeDecrypt(trustee.id, `Trustee ${idx + 1}`)}
                  disabled={isLoading || !tallyStatus?.aggregated || trustee.has_decrypted || tallyStatus?.finalized}
                >
                  <span className="trustee-icon"></span>
                  <span>Trustee {idx + 1}</span>
                  {trustee.has_decrypted && <span className="check"></span>}
                </button>
              ))}
            </div>

            {tallyStatus?.partial_decryptions >= 3 && !tallyStatus?.finalized && (
              <div className="threshold-alert">
                Threshold reached! Ready to finalize
              </div>
            )}
          </div>

          {/* Step 4: Finalization */}
          <div className="workflow-step">
            <div className="step-header">
              <span className="step-number">4</span>
              <h4>Lagrange Interpolation</h4>
            </div>
            <p>Combine partial decryptions to reveal final tally</p>
            <button
              className="step-btn"
              onClick={handleFinalize}
              disabled={isLoading || tallyStatus?.partial_decryptions < 3 || tallyStatus?.finalized}
            >
              {tallyStatus?.finalized ? <> Finalized</> : <> Finalize Tally</>}
            </button>
            {tallyStatus?.finalized && (
              <div className="step-info">
                <span> Results computed</span>
                <span>m = L(∏ Dᵢ^λᵢ) · μ mod n</span>
              </div>
            )}
          </div>

          {/* Results Display */}
          {results && (
            <div className="results-panel">
              <h3>Final Results</h3>
              <div className="results-bars">
                {Object.entries(results.results || {}).map(([candidate, count]) => {
                  const maxVotes = Math.max(...Object.values(results.results || {}));
                  const percentage = (count / maxVotes) * 100;

                  return (
                    <div key={candidate} className="result-row">
                      <span className="candidate-name">{candidate}</span>
                      <div className="bar-container">
                        <div
                          className="bar-fill"
                          style={{ width: `${percentage}%` }}
                        ></div>
                      </div>
                      <span className="vote-count">{count} votes</span>
                    </div>
                  );
                })}
              </div>
              <div className="privacy-notice">
                Individual votes remain cryptographically hidden
              </div>
            </div>
          )}
        </div>

        {/* Console Logs */}
        <div className="workflow-right">
          <div className="console-header">
            <h3>Live Console</h3>
            <button className="clear-btn" onClick={clearLogs}>Clear</button>
          </div>
          <div className="console-logs">
            {logs.length === 0 ? (
              <div className="console-empty">
                No activity yet. Start the workflow above!
              </div>
            ) : (
              logs.map(log => (
                <div key={log.id} className={`log-entry log-${log.type}`}>
                  <span className="log-time">[{log.timestamp}]</span>
                  <span className="log-message">{log.message}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Info Section */}
      <div className="info-panel">
        <div className="info-card">
          <h4>How It Works</h4>
          <ul>
            <li><strong>Paillier Encryption:</strong> Homomorphic cryptosystem allows computing on encrypted data (E(a) × E(b) = E(a+b))</li>
            <li><strong>Zero-Knowledge Proofs:</strong> Each vote includes proof of validity without revealing the choice</li>
            <li><strong>Shamir Secret Sharing:</strong> Private key split into 5 shares, any 3 can reconstruct</li>
            <li><strong>Threshold Decryption:</strong> Multiple trustees prevent single point of trust</li>
            <li><strong>Lagrange Interpolation:</strong> Mathematically combines partial decryptions into final result</li>
          </ul>
        </div>
        <div className="info-card">
          <h4>Privacy Guarantees</h4>
          <ul>
            <li>Individual votes are never revealed, even after tallying</li>
            <li>Only aggregate totals can be computed</li>
            <li>No single party can decrypt alone (threshold security)</li>
            <li>Cryptographic proofs ensure correctness without inspection</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default CryptoVisualizer;
