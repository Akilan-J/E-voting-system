/**
 * Epic 3: Immutable Vote Ledger - Frontend Explorer
 * 
 * Displays blockchain blocks with hashes, Merkle roots, and timestamps.
 * Auto-refreshes every 10 seconds to show new blocks.
 */

import React, { useState, useEffect } from 'react';
import '../App.css';

function LedgerExplorer() {
    const [blocks, setBlocks] = useState([]);
    const [status, setStatus] = useState({ loading: true, error: null });
    const [lastUpdated, setLastUpdated] = useState(null);

    const fetchBlocks = async () => {
        setStatus({ loading: true, error: null });
        try {
            const response = await fetch('/api/ledger/blocks');
            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${response.statusText}`);
            }
            const data = await response.json();
            // Sort desc by height
            setBlocks(data.sort((a, b) => b.height - a.height));
            setStatus({ loading: false, error: null });
            setLastUpdated(new Date().toLocaleTimeString());
        } catch (err) {
            setStatus({ loading: false, error: err.message });
        }
    };

    useEffect(() => {
        fetchBlocks();
        // Auto-refresh every 10s
        const interval = setInterval(fetchBlocks, 10000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="dashboard-container">
            <div className="panel-header">
                <h2>🔗 Immutable Vote Ledger</h2>
                <div className="panel-controls">
                    <span className="last-updated">
                        {lastUpdated ? `Updated: ${lastUpdated}` : 'Connecting...'}
                    </span>
                    <button className="refresh-btn" onClick={fetchBlocks}>
                        🔄 Refresh
                    </button>
                </div>
            </div>

            <div className="ledger-content">
                {status.loading && blocks.length === 0 && (
                    <div className="loading-state">Loading Blockchain...</div>
                )}

                {status.error && (
                    <div className="error-state">
                        ⚠️ Connection Failed: {status.error}
                        <br />
                        <small>Is the backend running?</small>
                    </div>
                )}

                {blocks.length > 0 && (
                    <div className="blockchain-list">
                        {blocks.map((block) => (
                            <div key={block.height} className="block-card">
                                <div className="block-header">
                                    <span className="block-height">#{block.height}</span>
                                    <span className="block-timestamp">
                                        {new Date(block.timestamp).toLocaleString()}
                                    </span>
                                </div>

                                <div className="block-body">
                                    <div className="data-row">
                                        <strong>Block Hash:</strong>
                                        <code className="hash-code" title={block.block_hash}>
                                            {block.block_hash.substring(0, 16)}...
                                        </code>
                                    </div>
                                    <div className="data-row">
                                        <strong>Prev Hash:</strong>
                                        <code className="hash-code" title={block.prev_hash}>
                                            {block.prev_hash.substring(0, 16)}...
                                        </code>
                                    </div>
                                    <div className="data-row">
                                        <strong>Merkle Root:</strong>
                                        <code className="hash-code" title={block.merkle_root}>
                                            {block.merkle_root.substring(0, 8)}...
                                        </code>
                                    </div>
                                    <div className="data-row">
                                        <strong>Entries:</strong>
                                        <span className="entry-count">{block.entry_count}</span>
                                    </div>
                                </div>

                                {block.height === 0 && (
                                    <div className="genesis-badge">🌱 GENESIS</div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <style jsx>{`
        .blockchain-list {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
          padding: 1rem;
        }
        .block-card {
          background: white;
          border-radius: 8px;
          border-left: 5px solid #3498db;
          box-shadow: 0 2px 5px rgba(0,0,0,0.1);
          padding: 1rem;
          position: relative;
        }
        .block-card:before {
            content: '';
            position: absolute;
            left: 22px; /* Adjust based on padding */
            top: -20px;
            height: 20px;
            width: 2px;
            background: #cbd5e0;
            z-index: 0;
        }
        .block-card:first-child:before {
            display: none; /* No line above newest block (top of list) */
        }
        .block-header {
            display: flex;
            justify-content: space-between;
            border-bottom: 1px solid #eee;
            padding-bottom: 0.5rem;
            margin-bottom: 0.5rem;
        }
        .block-height {
            font-weight: bold;
            font-size: 1.2rem;
            color: #2c3e50;
        }
        .block-timestamp {
            color: #7f8c8d;
            font-size: 0.9rem;
        }
        .data-row {
            display: flex;
            justify-content: space-between;
            font-size: 0.9rem;
            margin-bottom: 0.25rem;
        }
        .hash-code {
            background: #f8f9fa;
            padding: 2px 5px;
            border-radius: 4px;
            font-family: monospace;
            color: #e74c3c;
            cursor: help;
        }
        .genesis-badge {
            background: #2ecc71;
            color: white;
            text-align: center;
            padding: 0.2rem;
            border-radius: 4px;
            margin-top: 0.5rem;
            font-weight: bold;
            font-size: 0.8rem;
        }
      `}</style>
        </div>
    );
}

export default LedgerExplorer;
