
import React, { useState, useEffect, useRef } from 'react';
import { securityAPI, resultsAPI } from '../services/api';
import './SecurityLab.css';

const SecurityLab = () => {
    const authRole = localStorage.getItem('authRole');
    const canOperate = authRole === 'security_engineer' || authRole === 'admin';
    const [logs, setLogs] = useState([]);
    const [anomalies, setAnomalies] = useState([]);
    const [scenario, setScenario] = useState('replay_attack');
    const [simulating, setSimulating] = useState(false);
    const [electionId, setElectionId] = useState(null);
    const [replayStats, setReplayStats] = useState(null);
    const [selectedAnomaly, setSelectedAnomaly] = useState(null);
    const [exporting, setExporting] = useState(false);

    const handleInvestigate = (anomaly) => {
        setSelectedAnomaly(anomaly);
    };

    const closeInvestigation = () => {
        setSelectedAnomaly(null);
    };

    const terminalRef = useRef(null);

    useEffect(() => {
        // Init: get active election and mock anomalies
        resultsAPI.getAll().then(res => {
            if (res.data && res.data.length > 0) setElectionId(res.data[0].election_id);
        });

        loadAnomalies();
    }, []);

    // Auto-scroll terminal
    useEffect(() => {
        if (terminalRef.current) {
            terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
        }
    }, [logs]);

    const loadAnomalies = async () => {
        try {
            const res = await securityAPI.getAnomalies();
            setAnomalies(res.data);
        } catch (err) {
            addLog("Error fetching anomalies: " + err.message, "error");
        }
    };

    const addLog = (msg, type = "info") => {
        const timestamp = new Date().toLocaleTimeString();
        setLogs(prev => [...prev, { msg, type, time: timestamp }]);
    };

    const handleSimulation = async () => {
        setSimulating(true);
        addLog(`Initiating scenario: ${scenario}...`, "warn");

        try {
            const res = await securityAPI.simulateThreat({
                scenario_type: scenario,
                intensity: "high",
                target_component: "api_gateway"
            });

            // Append simulation logs
            res.data.logs.forEach(log => {
                const type = log.includes("WARN") ? "warn" : log.includes("ALERT") ? "error" : "info";
                addLog(log, type);
            });

            if (res.data.detected_by_ids) {
                addLog("✅ Threat neutralized by IDS", "success");
            }

            // Refresh anomalies if new ones generated
            loadAnomalies();

        } catch (err) {
            addLog("Simulation failed to execute", "error");
        }
        setSimulating(false);
    };

    const handleDownloadAnomalyReport = async () => {
        setExporting(true);
        try {
            const res = await securityAPI.getAnomalyReport();
            const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'anomaly_report.json');
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            addLog("Failed to export anomaly report", "error");
        }
        setExporting(false);
    };

    const handleDownloadTimeline = async () => {
        if (!electionId) return;
        setExporting(true);
        try {
            const res = await securityAPI.getReplayTimeline({ election_id: electionId });
            const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `timeline_${electionId}.json`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            addLog("Failed to export replay timeline", "error");
        }
        setExporting(false);
    };

    const runLedgerAudit = async () => {
        if (!electionId) return;
        addLog("Starting full ledger replay & hash verification...", "info");
        setReplayStats({ progress: 0, status: 'Auditing...' });

        try {
            // Fake progress for visual effect
            let p = 0;
            const interval = setInterval(() => {
                p += 10;
                if (p > 90) clearInterval(interval);
                setReplayStats(prev => ({ ...prev, progress: p }));
            }, 200);

            const res = await securityAPI.replayLedger(electionId);

            clearInterval(interval);
            setReplayStats({
                progress: 100,
                status: res.data.status === 'clean' ? 'Integrity Verified' : 'Corruption Detected',
                data: res.data
            });

            if (res.data.status === 'clean') {
                addLog(`Audit Complete: ${res.data.total_blocks} blocks verified. Tip: ${res.data.tip_hash.substring(0, 10)}...`, "success");
            } else {
                addLog(`Audit Failed: ${res.data.invalid_blocks} corrupted blocks found!`, "error");
            }

        } catch (err) {
            addLog("Audit process failed connection", "error");
            setReplayStats(null);
        }
    };

    return (
        <div className="security-lab">
            <div className="security-header">
                <h2>🧪 Security & Threat Lab</h2>
                <div className="status-badge">System Status: <span>ARMED</span></div>
                <div className="header-actions">
                    <button
                        className="audit-btn"
                        onClick={handleDownloadAnomalyReport}
                        disabled={exporting}
                    >
                        📄 Export Anomaly Report
                    </button>
                    <button
                        className="audit-btn"
                        onClick={handleDownloadTimeline}
                        disabled={exporting || !electionId}
                    >
                        🧾 Export Replay Timeline
                    </button>
                </div>
            </div>

            <div className="lab-grid">
                {/* Threat Simulator */}
                <div className="security-card card-warning">
                    <h3>⚡ Threat Simulator</h3>
                    {canOperate ? (
                        <div className="simulation-controls">
                            <p className="card-description">Inject synthetic attacks to test system resilience.</p>
                            <div className="control-group">
                                <select
                                    className="scenario-select"
                                    value={scenario}
                                    onChange={(e) => setScenario(e.target.value)}
                                >
                                    <option value="replay_attack">Replay Attack</option>
                                    <option value="oversize_payload">Oversize Payload</option>
                                    <option value="invalid_proof">Invalid Proof Bundle</option>
                                    <option value="ddos">DDoS / Traffic Burst</option>
                                    <option value="consensus_stall">Consensus Liveness Stall</option>
                                </select>
                                <button
                                    className="trigger-btn"
                                    onClick={handleSimulation}
                                    disabled={simulating}
                                >
                                    {simulating ? 'Injecting...' : 'Inject Threat'}
                                </button>
                            </div>
                        </div>
                    ) : (
                        <p className="card-description">Simulation controls are restricted to security engineering.</p>
                    )}
                </div>

                {/* Ledger Audit */}
                <div className={`security-card card-audit ${replayStats?.status === 'Auditing...' ? 'audit-active' : ''}`}>
                    <h3>🔍 Deep Ledger Audit</h3>
                    <p className="card-description">Recompute cryptographic hash chain from genesis block to verify immutable integrity.</p>

                    {!replayStats || replayStats.status === 'Auditing...' ? (
                        <>
                            {canOperate ? (
                                <button
                                    className="audit-btn primary"
                                    onClick={runLedgerAudit}
                                    disabled={!electionId || (replayStats && replayStats.status === 'Auditing...')}
                                >
                                    {replayStats?.status === 'Auditing...' ? (
                                        <>
                                            <span className="spinner"></span> Auditing Ledger...
                                        </>
                                    ) : (
                                        <>
                                            🚀 Run Full Replay Audit
                                        </>
                                    )}
                                </button>
                            ) : (
                                <p className="card-description">Audit execution is restricted to security engineering.</p>
                            )}

                            {replayStats && replayStats.status === 'Auditing...' && (
                                <div className="progress-container">
                                    <div className="progress-header">
                                        <span>Scanning Blockchain...</span>
                                        <span>{replayStats.progress}%</span>
                                    </div>
                                    <div className="progress-bar">
                                        <div className="progress-fill" style={{ width: `${replayStats.progress}%` }}></div>
                                    </div>
                                    <div className="card-description" style={{ textAlign: 'center', marginTop: '0.5rem', marginBottom: 0 }}>Verifying Merkle Roots & Previous Hashes</div>
                                </div>
                            )}
                        </>
                    ) : (
                        <div className="audit-result-container">
                            {/* Result State */}
                            <div className={`verified-badge ${replayStats.status === 'Integrity Verified' ? '' : 'error'}`}>
                                {replayStats.status === 'Integrity Verified' ? '✅ Integrity Verified' : '❌ Corruption Detected'}
                            </div>

                            {replayStats.data && (
                                <div className="result-stats">
                                    <div className="result-row">
                                        <span className="label">Total Blocks Verified</span>
                                        <span className="value">{replayStats.data.total_blocks}</span>
                                    </div>
                                    <div className="result-row">
                                        <span className="label">Valid Transactions</span>
                                        <span className="value">{replayStats.data.valid_blocks}</span>
                                    </div>

                                    <div className="hash-box">
                                        <span className="hash-label">LATEST TIP HASH</span>
                                        <div className="hash-value">{replayStats.data.tip_hash}</div>
                                    </div>

                                    {canOperate && (
                                        <button
                                            className="audit-btn"
                                            style={{ marginTop: '1rem', color: '#8b5cf6', borderColor: 'transparent' }}
                                            onClick={() => setReplayStats(null)}
                                        >
                                            Run New Audit
                                        </button>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Anomaly Monitor */}
                <div className="security-card card-info">
                    <h3>📡 Active Anomalies</h3>
                    <div className="anomaly-list">
                        {anomalies.length === 0 ? (
                            <p className="card-description" style={{ textAlign: 'center', padding: '1rem' }}>No active anomalies detected.</p>
                        ) : (
                            anomalies.map((anom, i) => (
                                <div className="anomaly-item" key={i}>
                                    <div>
                                        <div className="anomaly-title">⚠️ {anom.type}</div>
                                        <div className="anomaly-meta">{new Date(anom.timestamp).toLocaleTimeString()} • {anom.severity.toUpperCase()}</div>
                                    </div>
                                    {canOperate && (
                                        <button
                                            className="investigate-btn"
                                            onClick={() => handleInvestigate(anom)}
                                        >
                                            Investigate
                                        </button>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>

            {/* Live Terminal */}
            <div className="terminal-section">
                <h3>🖥️ Security Event Stream</h3>
                <div className="terminal-window" ref={terminalRef}>
                    <div className="terminal-line log-info">System initialized. Monitoring active...</div>
                    {logs.map((log, i) => (
                        <div key={i} className={`terminal-line log-${log.type}`}>
                            <span className="log-timestamp">[{log.time}]</span> {log.msg}
                        </div>
                    ))}
                    {logs.length === 0 && <div className="terminal-line log-info">Waiting for events...</div>}
                    <div className="terminal-line log-info">_</div>
                </div>
            </div>

            {/* Investigation Modal */}
            {selectedAnomaly && (
                <div className="modal-overlay">
                    <div className="modal-content">
                        <div className="modal-header">
                            <h3>🕵️ Anomaly Investigation</h3>
                            <button onClick={closeInvestigation} className="close-btn">✕</button>
                        </div>

                        <div className="modal-body">
                            <div className="threat-level-box">
                                <div className="threat-label">Threat Level Detected</div>
                                <div className="threat-value">{selectedAnomaly.severity.toUpperCase()}</div>
                            </div>

                            <div className="detail-row">
                                <span className="detail-label">Anomaly Type</span>
                                <span className="detail-value mono">{selectedAnomaly.type}</span>
                            </div>

                            <div className="detail-row">
                                <span className="detail-label">Detected At</span>
                                <span className="detail-value">{new Date(selectedAnomaly.timestamp).toLocaleString()}</span>
                            </div>

                            {selectedAnomaly.details && (
                                <div className="detail-row">
                                    <span className="detail-label">Details</span>
                                    <span className="detail-value">{selectedAnomaly.details}</span>
                                </div>
                            )}

                            {selectedAnomaly.correlation_id && (
                                <div className="detail-row">
                                    <span className="detail-label">Correlation ID</span>
                                    <span className="detail-value mono">{selectedAnomaly.correlation_id}</span>
                                </div>
                            )}

                            {selectedAnomaly.evidence_hash && (
                                <div className="detail-row">
                                    <span className="detail-label">Evidence Hash</span>
                                    <span className="detail-value mono">{selectedAnomaly.evidence_hash.substring(0, 16)}...</span>
                                </div>
                            )}

                            <div className="detail-row">
                                <span className="detail-label">Source IP</span>
                                <span className="detail-value mono">192.168.1.X (Internal)</span>
                            </div>

                            <div className="auto-analysis">
                                {`> Analyzing traffic pattern...\n> Signature match: ${selectedAnomaly.type}\n> Action: Traffic throttled & IP flagged.\n> Recommendation: Review firewall rules.`}
                            </div>
                        </div>

                        <div className="modal-actions">
                            <button className="btn btn-secondary" onClick={closeInvestigation}>Dismiss</button>
                            {canOperate && (
                                <button className="btn btn-primary" onClick={() => {
                                    addLog(`Investigation case opened for ${selectedAnomaly.type}`, "info");
                                    closeInvestigation();
                                }}>Open Formal Case</button>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default SecurityLab;
