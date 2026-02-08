import React, { useState, useEffect } from 'react';
import { trusteesAPI, tallyingAPI, mockDataAPI } from '../services/api';
import CryptoVisualizer from './CryptoVisualizer';
import './TrusteePanel.css';

function TrusteePanel() {
  const [trustees, setTrustees] = useState([]);
  const [tallyStatus, setTallyStatus] = useState(null);
  const [electionId, setElectionId] = useState(null);
  const [loading, setLoading] = useState({});
  const [message, setMessage] = useState(null);
  const [decryptedTrustees, setDecryptedTrustees] = useState(new Set());
  const [showVisualizer, setShowVisualizer] = useState(false);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    await Promise.all([loadTrustees(), loadElectionInfo()]);
  };

  const loadTrustees = async () => {
    try {
      const response = await trusteesAPI.getAll();
      setTrustees(response.data);
    } catch (err) {
      console.error('Failed to load trustees:', err);
    }
  };

  const loadElectionInfo = async () => {
    try {
      const stats = await mockDataAPI.getElectionStats();
      setElectionId(stats.data.election?.id);
      
      if (stats.data.tallying?.started) {
        const status = await tallyingAPI.getStatus(stats.data.election.id);
        setTallyStatus(status.data);
      }
    } catch (err) {
      console.error('Failed to load election info:', err);
    }
  };

  const handlePartialDecrypt = async (trusteeId, trusteeName) => {
    if (!electionId) {
      setMessage({ type: 'error', text: 'No election found. Please generate votes first.' });
      return;
    }

    setLoading(prev => ({ ...prev, [trusteeId]: true }));
    setMessage(null);

    try {
      await tallyingAPI.partialDecrypt(trusteeId, electionId);
      setMessage({ type: 'success', text: `${trusteeName} completed partial decryption!` });
      setDecryptedTrustees(prev => new Set([...prev, trusteeId]));
      await loadElectionInfo();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Decryption failed';
      setMessage({ type: 'error', text: `${trusteeName}: ${errorMsg}` });
    }
    
    setLoading(prev => ({ ...prev, [trusteeId]: false }));
  };

  const getProgress = () => {
    const completed = tallyStatus?.completed_trustees || 0;
    const required = tallyStatus?.required_trustees || 3;
    return { completed, required, percentage: (completed / required) * 100 };
  };

  const progress = getProgress();

  return (
    <div className="trustee-panel-v2">
      {/* Header */}
      <div className="panel-header">
        <div className="header-content">
          <h2>🔐 Trustee Decryption Panel</h2>
          <p>Threshold cryptography: 3 of 5 trustees required for decryption</p>
        </div>
      </div>

      {/* Message Display */}
      {message && (
        <div className={`alert alert-${message.type}`}>
          <span className="alert-icon">{message.type === 'success' ? '✅' : '❌'}</span>
          <span className="alert-text">{message.text}</span>
          <button className="alert-close" onClick={() => setMessage(null)}>×</button>
        </div>
      )}

      {/* Status Card */}
      <div className="status-card">
        <div className="status-header">
          <h3>📊 Decryption Progress</h3>
          <span className={`status-badge ${tallyStatus?.status === 'completed' ? 'complete' : tallyStatus?.started ? 'active' : 'pending'}`}>
            {tallyStatus?.status || 'Waiting for Tally'}
          </span>
        </div>
        
        <div className="progress-section">
          <div className="progress-info">
            <span className="progress-label">Trustees Completed</span>
            <span className="progress-count">{progress.completed} / {progress.required}</span>
          </div>
          <div className="progress-bar-container">
            <div 
              className="progress-bar-fill" 
              style={{ width: `${progress.percentage}%` }}
            >
              {progress.percentage > 0 && (
                <span className="progress-text">{Math.round(progress.percentage)}%</span>
              )}
            </div>
          </div>
          {progress.completed >= progress.required && (
            <div className="progress-complete">
              ✅ Threshold reached! Ready to finalize results.
            </div>
          )}
        </div>
      </div>

      {/* Trustees Grid */}
      <div className="trustees-section">
        <h3>👥 Registered Trustees</h3>
        
        {trustees.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">👤</div>
            <p>No trustees registered yet</p>
            <span>Go to Testing tab and click "Setup Trustees"</span>
          </div>
        ) : (
          <div className="trustees-grid">
            {trustees.slice(0, 5).map((trustee, index) => {
              const isDecrypted = decryptedTrustees.has(trustee.trustee_id);
              const isLoading = loading[trustee.trustee_id];
              const colors = ['#667eea', '#48bb78', '#ed8936', '#9f7aea', '#38b2ac'];
              const color = colors[index % colors.length];

              return (
                <div 
                  key={trustee.trustee_id} 
                  className={`trustee-card ${isDecrypted ? 'decrypted' : ''}`}
                >
                  <div className="trustee-avatar" style={{ background: color }}>
                    {trustee.name.charAt(0)}
                  </div>
                  
                  <div className="trustee-info">
                    <h4>{trustee.name}</h4>
                    <span className="trustee-email">{trustee.email}</span>
                    <span className={`trustee-status ${trustee.status}`}>
                      {trustee.status === 'active' ? '🟢 Active' : '⚪ Inactive'}
                    </span>
                  </div>

                  <div className="trustee-actions">
                    {isDecrypted ? (
                      <div className="decrypted-badge">
                        <span className="badge-icon">✅</span>
                        <span className="badge-text">Decrypted</span>
                      </div>
                    ) : (
                      <button
                        className="btn btn-decrypt"
                        onClick={() => handlePartialDecrypt(trustee.trustee_id, trustee.name)}
                        disabled={isLoading || !tallyStatus}
                      >
                        {isLoading ? (
                          <>
                            <span className="spinner"></span>
                            Decrypting...
                          </>
                        ) : (
                          <>🔓 Decrypt</>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Info Card */}
      <div className="info-card">
        <div className="info-icon">💡</div>
        <div className="info-content">
          <h4>How Threshold Decryption Works</h4>
          <p>
            The election results are encrypted with a shared key. Each trustee holds a piece 
            of the decryption key (Shamir's Secret Sharing). At least 3 trustees must provide 
            their partial decryptions to reveal the final vote counts. This ensures no single 
            party can see results alone.
          </p>
        </div>
      </div>

      {/* Crypto Visualizer Toggle */}
      <div className="visualizer-toggle-section">
        <button 
          className="btn-toggle-visualizer"
          onClick={() => setShowVisualizer(!showVisualizer)}
        >
          {showVisualizer ? '🔼 Hide' : '🔽 Show'} Cryptographic Process Visualization
        </button>
      </div>

      {/* Crypto Visualizer */}
      {showVisualizer && (
        <div className="embedded-visualizer">
          <CryptoVisualizer />
        </div>
      )}
    </div>
  );
}

export default TrusteePanel;
