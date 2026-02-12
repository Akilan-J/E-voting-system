import React, { useState, useEffect } from 'react';
import { Link, Box, FileText, CheckCircle, AlertTriangle, RefreshCw, ClipboardList, AlertCircle, Lightbulb } from 'lucide-react';
import './LedgerExplorer.css';

function LedgerExplorer() {
  const [blocks, setBlocks] = useState([]);
  const [chainStatus, setChainStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Fetch blocks
      const blocksRes = await fetch('/api/ledger/blocks');
      if (!blocksRes.ok) throw new Error('Failed to fetch blocks');
      const blocksData = await blocksRes.json();
      setBlocks(blocksData.sort((a, b) => b.height - a.height));

      // Fetch chain verification status
      const verifyRes = await fetch('/api/ledger/verify-chain');
      if (verifyRes.ok) {
        const verifyData = await verifyRes.json();
        setChainStatus(verifyData);
      }

      setError(null);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  return (
    <div className="ledger-explorer">
      {/* Header */}
      <div className="explorer-header">
        <div className="header-content">
          <h2>Immutable Vote Ledger</h2>
          <p>Blockchain-based vote record with cryptographic integrity</p>
        </div>
        <div className="header-actions">
          <span className="last-updated">
            {lastUpdated ? `Updated: ${lastUpdated}` : 'Connecting...'}
          </span>
          <button className="btn btn-refresh" onClick={fetchData}>
            Refresh
          </button>
        </div>
      </div>

      {/* Chain Status */}
      <div className="status-row">
        <div className="status-card">
          <div className="status-icon"></div>
          <div className="status-info">
            <span className="status-value">{blocks.length}</span>
            <span className="status-label">Total Blocks</span>
          </div>
        </div>
        <div className="status-card">
          <div className="status-icon"></div>
          <div className="status-info">
            <span className="status-value">
              {blocks.reduce((sum, b) => sum + (b.entry_count || 0), 0)}
            </span>
            <span className="status-label">Total Entries</span>
          </div>
        </div>
        <div className={`status-card ${chainStatus?.valid ? 'valid' : 'warning'}`}>
          <div className="status-icon"></div>
          <div className="status-info">
            <span className="status-value">
              {chainStatus?.valid ? 'Valid' : chainStatus?.reason || 'Pending'}
            </span>
            <span className="status-label">Chain Integrity</span>
          </div>
        </div>
      </div>

      {/* Blocks List */}
      <div className="blocks-section">
        <h3>Block History</h3>

        {loading && blocks.length === 0 && (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading blockchain...</p>
          </div>
        )}

        {error && (
          <div className="error-state">

            <p>{error}</p>
            <span>Is the backend running?</span>
          </div>
        )}

        {!loading && blocks.length === 0 && !error && (
          <div className="empty-state">
            <div className="empty-icon"></div>
            <h4>No Blocks Yet</h4>
            <p>The blockchain will populate once election results are published.</p>
          </div>
        )}

        {blocks.length > 0 && (
          <div className="blocks-list">
            {blocks.map((block, index) => (
              <div
                key={block.height}
                className={`block-card ${block.height === 0 ? 'genesis' : ''}`}
              >
                <div className="block-connector">
                  {index < blocks.length - 1 && <div className="connector-line"></div>}
                </div>

                <div className="block-content">
                  <div className="block-header">
                    <div className="block-title">
                      <span className="block-height">Block #{block.height}</span>
                      {block.height === 0 && <span className="genesis-badge">GENESIS</span>}
                    </div>
                    <span className="block-time">
                      {new Date(block.timestamp).toLocaleString()}
                    </span>
                  </div>

                  <div className="block-body">
                    <div className="hash-row">
                      <span className="hash-label">Block Hash</span>
                      <code className="hash-value" title={block.block_hash}>
                        {block.block_hash?.substring(0, 20)}...
                      </code>
                    </div>
                    <div className="hash-row">
                      <span className="hash-label">Previous Hash</span>
                      <code className="hash-value prev" title={block.prev_hash}>
                        {block.prev_hash?.substring(0, 20)}...
                      </code>
                    </div>
                    <div className="hash-row">
                      <span className="hash-label">Merkle Root</span>
                      <code className="hash-value merkle" title={block.merkle_root}>
                        {block.merkle_root?.substring(0, 16)}...
                      </code>
                    </div>
                  </div>

                  <div className="block-footer">
                    <div className="entry-badge">
                      {block.entry_count || 0} entries
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Info Card */}
      <div className="info-card">
        <div className="info-icon"></div>
        <div className="info-content">
          <h4>About the Immutable Ledger</h4>
          <p>
            Each block contains a cryptographic hash linking it to the previous block,
            creating an immutable chain. The Merkle root summarizes all entries in the block.
            Any tampering would break the hash chain and be immediately detectable.
          </p>
        </div>
      </div>
    </div>
  );
}

export default LedgerExplorer;
