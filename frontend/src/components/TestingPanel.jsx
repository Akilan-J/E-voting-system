
import React, { useState, useEffect } from 'react';
import { mockDataAPI, tallyingAPI, resultsAPI } from '../services/api';
import './TestingPanel.css';

function TestingPanel() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  // Modal state
  const [showResetConfirm, setShowResetConfirm] = useState(false);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const response = await mockDataAPI.getElectionStats();
      setStats(response.data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  };

  const handleAction = async (action, successMsg) => {
    setLoading(true);
    setMessage(null);
    try {
      await action();
      // Add a small delay to ensure loading state is visible
      await new Promise(resolve => setTimeout(resolve, 300));

      setMessage({ type: 'success', text: successMsg });
      await loadStats();

      // Auto-clear message after 5 seconds
      setTimeout(() => setMessage(null), 5000);
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Action failed' });
    }
    setLoading(false);
  };

  const generateVotes = () => handleAction(
    () => mockDataAPI.generateVotes(100),
    'Generated 100 mock votes successfully!'
  );

  const setupTrustees = () => handleAction(
    () => mockDataAPI.setupTrustees(),
    'Trustees setup complete!'
  );

  const startTallying = async () => {
    if (!stats) return;
    await handleAction(
      () => tallyingAPI.start(stats.election.id),
      'Tallying started! Trustees can now decrypt.'
    );
  };

  const finalizeTally = async () => {
    if (!stats) return;
    await handleAction(
      () => tallyingAPI.finalize(stats.election.id),
      'Tally finalized! Check results tab.'
    );
  };

  const publishToBlockchain = async () => {
    if (!stats) return;
    await handleAction(
      () => resultsAPI.publishToBlockchain(stats.election.id),
      'Results published to blockchain!'
    );
  };

  // Reset Logic with Modal
  const requestReset = () => {
    setMessage(null);
    setShowResetConfirm(true);
  };

  const confirmReset = async () => {
    setShowResetConfirm(false);
    await handleAction(
      () => mockDataAPI.resetDatabase(),
      'Database reset successfully!'
    );
  };

  const cancelReset = () => {
    setShowResetConfirm(false);
  };

  return (
    <div className="testing-panel">
      <div className="card">
        <h2>🧪 Testing & Development Tools</h2>
        <p>Quick actions for testing the tallying workflow</p>

        {message && (
          <div className={message.type === 'success' ? 'success' : 'error'}>
            {message.text}
          </div>
        )}

        {stats && (
          <div className="status-box">
            <h3>📊 Current Status</h3>
            <div className="status-grid">
              <div className="status-item">
                <p className="status-label">Election</p>
                <p className="status-value">{stats.election?.title || 'Not found'}</p>
              </div>
              <div className="status-item">
                <p className="status-label">Total Votes</p>
                <p className="status-value">{stats.votes?.total || 0}</p>
              </div>
              <div className="status-item">
                <p className="status-label">Tallying Status</p>
                <p className="status-value">{stats.tallying?.status || 'Not started'}</p>
              </div>
              <div className="status-item">
                <p className="status-label">Trustees Completed</p>
                <p className="status-value">
                  {stats.tallying?.trustees_completed || 0}/{stats.tallying?.required_trustees || 3}
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="workflow-section">
          <h3>🚀 Test Workflow</h3>
          <p>Follow these steps in order:</p>

          <div className="workflow-steps">
            <div className="workflow-step">
              <span className="step-number">1</span>
              <button
                className="btn btn-primary"
                onClick={setupTrustees}
                disabled={loading}
              >
                🔧 Setup Trustees with Key Shares
              </button>
            </div>

            <div className="workflow-step">
              <span className="step-number">2</span>
              <button
                className="btn btn-primary"
                onClick={generateVotes}
                disabled={loading}
              >
                🗳️ Generate 100 Mock Votes
              </button>
            </div>

            <div className="workflow-step">
              <span className="step-number">3</span>
              <button
                className="btn btn-success"
                onClick={startTallying}
                disabled={loading || !stats || stats.votes?.total === 0}
              >
                🔢 Start Tallying Process
              </button>
            </div>

            <div className="workflow-step">
              <span className="step-number">4</span>
              <div className="step-instruction">
                📍 Go to "Trustees" tab and click "Decrypt" for at least 3 trustees
              </div>
            </div>

            <div className="workflow-step">
              <span className="step-number">5</span>
              <button
                className="btn btn-success"
                onClick={finalizeTally}
                disabled={loading || !stats?.tallying?.started}
              >
                ✨ Finalize Tally & Compute Results
              </button>
            </div>

            <div className="workflow-step">
              <span className="step-number">6</span>
              <button
                className="btn btn-secondary"
                onClick={publishToBlockchain}
                disabled={loading}
              >
                ⛓️ Publish to Blockchain
              </button>
            </div>
          </div>
        </div>

        <div className="danger-zone">
          <h3>⚠️ Danger Zone</h3>
          <button
            className="btn btn-danger"
            onClick={requestReset}
            disabled={loading}
          >
            🗑️ Reset Database
          </button>
          <p>This will delete all votes, results, and tallying sessions</p>
        </div>

        <div className="utility-section">
          <button
            className="btn btn-secondary"
            onClick={loadStats}
            disabled={loading}
          >
            🔄 Refresh Status
          </button>
        </div>

        {/* Custom Confirmation Modal */}
        {showResetConfirm && (
          <div className="modal-overlay">
            <div className="modal-content">
              <h3>⚠️ Confirm Reset</h3>
              <p>Reset entire database? This will delete all votes and results.</p>
              <div className="modal-actions">
                <button className="btn btn-secondary" onClick={cancelReset}>Cancel</button>
                <button className="btn btn-danger" onClick={confirmReset}>Yes, Reset Everything</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default TestingPanel;
