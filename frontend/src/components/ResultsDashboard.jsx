import React, { useState, useEffect } from 'react';
import { resultsAPI, mockDataAPI } from '../services/api';
import { BarChart2, RefreshCw, Box, Users, Trophy, Hash, CheckCircle, XCircle, Loader, Link, Search } from 'lucide-react';
import './ResultsDashboard.css';

const DEMO_ELECTION_ID = '00000000-0000-0000-0000-000000000001';

function ResultsDashboard() {
  const [results, setResults] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [verificationStatus, setVerificationStatus] = useState(null);

  useEffect(() => {
    loadResults();
  }, []);

  const loadResults = async () => {
    setLoading(true);
    setError(null);
    try {
      const resultData = await resultsAPI.getByElectionId(DEMO_ELECTION_ID);
      setResults(resultData.data);

      const summaryData = await resultsAPI.getSummary(DEMO_ELECTION_ID);
      setSummary(summaryData.data);
    } catch (err) {
      setError('No results yet. Complete the tallying workflow in the Testing tab.');
    }
    setLoading(false);
  };

  const verifyResults = async () => {
    if (!results?.election_id) return;

    setVerificationStatus({ loading: true });
    try {
      const verification = await resultsAPI.verify(results.election_id);
      setVerificationStatus({
        loading: false,
        valid: verification.data.is_valid,
        message: verification.data.message || (verification.data.is_valid ? 'Results verified successfully' : 'Verification failed')
      });
    } catch (err) {
      setVerificationStatus({
        loading: false,
        valid: false,
        message: err.response?.data?.detail || 'Verification failed'
      });
    }
  };

  // Calculate winner from tally
  const getWinner = () => {
    if (!summary?.results?.tally) return null;
    const entries = Object.entries(summary.results.tally);
    if (entries.length === 0) return null;
    return entries.reduce((max, curr) => curr[1].votes > max[1].votes ? curr : max);
  };

  const winner = getWinner();

  if (loading) {
    return (
      <div className="results-dashboard">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading results...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="results-dashboard">
        <div className="empty-state">
          <div className="empty-icon"><BarChart2 className="w-16 h-16 mx-auto" /></div>
          <h3>No Results Available</h3>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={loadResults}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="results-dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <div className="header-left">
          <h2>Election Results</h2>
          <p>{summary?.election?.title || 'Presidential Election 2026'}</p>
        </div>
        <div className="header-right">
          <span className={`status-pill status-${summary?.election?.status || 'pending'}`}>
            {summary?.election?.status || 'Pending'}
          </span>
          <button className="btn btn-icon" onClick={loadResults} title="Refresh">

          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-icon"></div>
          <div className="stat-content">
            <span className="stat-value">{summary?.results?.total_votes || 0}</span>
            <span className="stat-label">Total Votes</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon"></div>
          <div className="stat-content">
            <span className="stat-value">{Object.keys(summary?.results?.tally || {}).length}</span>
            <span className="stat-label">Candidates</span>
          </div>
        </div>
        <div className="stat-card highlight">
          <div className="stat-icon"></div>
          <div className="stat-content">
            <span className="stat-value">{winner ? winner[0] : '-'}</span>
            <span className="stat-label">Winner</span>
          </div>
        </div>
      </div>

      {/* Vote Distribution */}
      <div className="section-card">
        <h3>Vote Distribution</h3>
        <div className="candidates-grid">
          {summary && Object.entries(summary.results?.tally || {}).map(([candidate, data], index) => {
            const isWinner = winner && winner[0] === candidate;
            const colors = ['#667eea', '#48bb78', '#ed8936', '#9f7aea', '#38b2ac'];
            const color = colors[index % colors.length];

            return (
              <div key={candidate} className={`candidate-card ${isWinner ? 'winner' : ''}`}>
                {isWinner && <div className="winner-badge"> Winner</div>}
                <div className="candidate-header">
                  <div className="candidate-avatar" style={{ background: color }}>
                    {candidate.charAt(0)}
                  </div>
                  <div className="candidate-info">
                    <h4>{candidate}</h4>
                    <span className="vote-count">{data.votes} votes</span>
                  </div>
                  <div className="percentage-badge" style={{ background: color }}>
                    {data.percentage}%
                  </div>
                </div>
                <div className="vote-bar">
                  <div
                    className="vote-bar-fill"
                    style={{
                      width: `${data.percentage}%`,
                      background: `linear-gradient(90deg, ${color}, ${color}dd)`
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Verification Section */}
      <div className="section-card verification-section">
        <h3>Cryptographic Verification</h3>

        <div className="verification-grid">
          <div className="verification-item">
            <span className="ver-label">Verification Hash</span>
            <code className="ver-value hash">
              {results?.verification_hash || 'Not computed'}
            </code>
          </div>

          <div className="verification-item">
            <span className="ver-label">Election ID</span>
            <code className="ver-value">
              {results?.election_id?.substring(0, 16)}...
            </code>
          </div>

          {summary?.blockchain?.published && (
            <>
              <div className="verification-item">
                <span className="ver-label">Blockchain TX</span>
                <code className="ver-value hash">
                  {summary.blockchain.tx_hash?.substring(0, 32)}...
                </code>
              </div>
              <div className="verification-item">
                <span className="ver-label">Block Number</span>
                <code className="ver-value">
                  {summary.blockchain.block_number || 'N/A'}
                </code>
              </div>
            </>
          )}
        </div>

        {/* Verification Status */}
        {verificationStatus && !verificationStatus.loading && (
          <div className={`verification-result ${verificationStatus.valid ? 'valid' : 'invalid'}`}>
            <span className="ver-icon"></span>
            <span className="ver-message">{verificationStatus.message}</span>
          </div>
        )}

        <div className="verification-actions">
          <button
            className="btn btn-primary"
            onClick={verifyResults}
            disabled={verificationStatus?.loading}
          >
            {verificationStatus?.loading ? <> Verifying...</> : <> Verify Results</>}
          </button>
        </div>
      </div>

      {/* Blockchain Status */}
      {summary?.blockchain?.published ? (
        <div className="section-card blockchain-section">
          <h3>Blockchain Record</h3>
          <div className="blockchain-status published">
            <div className="blockchain-icon"></div>
            <div className="blockchain-info">
              <h4>Results Published to Blockchain</h4>
              <p>This election's results are immutably recorded on the ledger.</p>
              <span className="tx-hash">TX: {summary.blockchain.tx_hash}</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="section-card blockchain-section">
          <h3>Blockchain Record</h3>
          <div className="blockchain-status pending">
            <div className="blockchain-icon"></div>
            <div className="blockchain-info">
              <h4>Not Yet Published</h4>
              <p>Results can be published to the blockchain after tallying is complete.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ResultsDashboard;
