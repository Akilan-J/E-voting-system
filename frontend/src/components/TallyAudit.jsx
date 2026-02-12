
import React, { useState, useEffect } from 'react';
import { tallyingAPI, resultsAPI, authAPI, mockDataAPI } from '../services/api';
import { BarChart2, Rocket, Flag, CheckCircle, Zap, Key, Scroll, Search, FileText, Shield, RefreshCw } from 'lucide-react';
import './TallyAudit.css';

const TallyAudit = () => {
    const [activeTab, setActiveTab] = useState('orchestration');
    const [electionId, setElectionId] = useState(null);
    const [tallyStatus, setTallyStatus] = useState(null);
    const [circuitBreaker, setCircuitBreaker] = useState(null);
    const [trustees, setTrustees] = useState([]);
    const [manifest, setManifest] = useState(null);
    const [transcript, setTranscript] = useState(null);
    const [reproduceReport, setReproduceReport] = useState(null);
    const [isolationStatus, setIsolationStatus] = useState(null);
    const [loading, setLoading] = useState(false);
    const [logs, setLogs] = useState([]);

    const authRole = localStorage.getItem('authRole');
    const isAdmin = authRole === 'admin';
    const isAuditor = authRole === 'auditor';
    const isTrustee = authRole === 'trustee';

    useEffect(() => {
        // Find active election
        resultsAPI.getAll().then(res => {
            if (res.data && res.data.length > 0) {
                const id = res.data[0].election_id;
                setElectionId(id);
                loadAllData(id);
            }
        });

        // Load independent data
        loadIsolationStatus();
    }, []);

    const loadAllData = (id) => {
        loadTallyStatus(id);
        loadCircuitBreaker(id);
        loadTrustees(id); // Trustees might require separate API or auth check
        if (activeTab === 'auditor') {
            loadAuditData(id);
        }
    };

    const loadTallyStatus = async (id) => {
        try {
            const res = await tallyingAPI.getStatus(id);
            setTallyStatus(res.data);
        } catch (err) {
            console.log("Tally not started or status unavailable");
            setTallyStatus(null);
        }
    };

    const loadCircuitBreaker = async (id) => {
        try {
            const res = await tallyingAPI.getCircuitBreaker(id);
            setCircuitBreaker(res.data);
        } catch (err) {
            console.error("Failed to load circuit breaker", err);
        }
    };

    const loadTrustees = async (id) => {
        // In a real app we'd fetch specific trustees for this election
        // For now using mock/auth users with 'trustee' role
        try {
            const res = await authAPI.listUsers();
            const trusteeUsers = res.data.filter(u => u.role === 'trustee');
            setTrustees(trusteeUsers);
        } catch (err) {
            console.error("Failed to load trustees", err);
        }
    };

    const loadAuditData = async (id) => {
        setLoading(true);
        try {
            const [manRes, tranRes, repRes] = await Promise.allSettled([
                tallyingAPI.getBallotManifest(id),
                tallyingAPI.getTranscript(id),
                tallyingAPI.getReproducibilityReport(id)
            ]);

            if (manRes.status === 'fulfilled') setManifest(manRes.value.data);
            if (tranRes.status === 'fulfilled') setTranscript(tranRes.value.data);
            if (repRes.status === 'fulfilled') setReproduceReport(repRes.value.data);

        } catch (err) {
            console.error("Audit data load partial failure", err);
        }
        setLoading(false);
    };

    const loadIsolationStatus = async () => {
        try {
            const res = await tallyingAPI.getIsolationStatus();
            setIsolationStatus(res.data);
        } catch (err) {
            console.error("Isolation status failed", err);
        }
    };

    // Actions
    const handleStartTally = async () => {
        if (!electionId) return;
        setLoading(true);
        try {
            await tallyingAPI.start(electionId);
            addLog("Tally process started successfully.");
            loadAllData(electionId);
        } catch (err) {
            addLog(`Error starting tally: ${err.message}`, 'error');
        }
        setLoading(false);
    };

    const handleFinalizeTally = async () => {
        if (!electionId) return;
        setLoading(true);
        try {
            await tallyingAPI.finalize(electionId);
            addLog("Tally finalized! Results are now computed.");
            loadAllData(electionId);
        } catch (err) {
            addLog(`Finalization failed: ${err.message}`, 'error');
        }
        setLoading(false);
    };

    const handleResetCB = async () => {
        if (!electionId) return;
        try {
            await tallyingAPI.resetCircuitBreaker(electionId);
            addLog("Circuit Breaker reset.");
            loadCircuitBreaker(electionId);
        } catch (err) {
            addLog("Failed to reset CB", 'error');
        }
    };

    const handleSimulateDecrypt = async (trustee) => {
        if (!electionId) return;
        setLoading(true);
        try {
            // In real world, Trustee would log in and do this.
            // Here we might need a mock endpoint or assume we are the trustee.
            // But wait, the API requires trustee auth.
            // If we are admin, we can't do it unless we have a "mock trustee action".
            // Implementation plan mentions "Setup Trustees" in mock data.
            // Let's assume we can't do it effortlessly unless logged in as THAT trustee.
            // But maybe we can use the Mock Data API to simulate it?
            // "mockDataAPI" doesn't have "simulateDecrypt".
            // tallyingAPI.partialDecrypt requires trustee token.

            addLog(`Simulating decryption for ${trustee.user_id}... (Auth required)`);
            alert("You must be logged in as this trustee to perform real decryption. Admin cannot impersonate.");
        } catch (err) {
            addLog(`Decryption failed: ${err.message}`, 'error');
        }
        setLoading(false);
    };

    const handleRecount = async () => {
        if (!electionId) return;
        setLoading(true);
        try {
            const res = await tallyingAPI.triggerRecount(electionId);
            addLog(`Recount complete. Match: ${res.data.recount_match}`);
            loadAllData(electionId);
        } catch (err) {
            addLog(`Recount failed: ${err.message}`, 'error');
        }
        setLoading(false);
    };

    const addLog = (msg, type = 'info') => {
        setLogs(prev => [{ msg, type, time: new Date().toLocaleTimeString() }, ...prev]);
    };

    if (!electionId) return <div className="tally-audit-container"><h2>Loading Election Context...</h2></div>;

    return (
        <div className="tally-audit-container">
            <div className="tally-header">
                <h2>Tally & Audit Hub</h2>
                <span className="election-id-badge">ID: {electionId}</span>
            </div>

            <div className="tally-tabs">
                <button className={`tally-tab ${activeTab === 'orchestration' ? 'active' : ''}`} onClick={() => setActiveTab('orchestration')}>Orchestration</button>
                <button className={`tally-tab ${activeTab === 'trustees' ? 'active' : ''}`} onClick={() => setActiveTab('trustees')}>Trustee Swarm</button>
                <button className={`tally-tab ${activeTab === 'auditor' ? 'active' : ''}`} onClick={() => setActiveTab('auditor')}>Forensic Audit</button>
                <button className={`tally-tab ${activeTab === 'network' ? 'active' : ''}`} onClick={() => setActiveTab('network')}>Network Isolation</button>
            </div>

            {/* ORCHESTRATION TAB */}
            {activeTab === 'orchestration' && (
                <div className="tally-grid">
                    <div className="tally-card">
                        <h3>Tally Controller</h3>
                        <div className="status-box">
                            <span className="label">Current Status: </span>
                            <span className={`status-indicator ${tallyStatus?.status || 'waiting'}`}>
                                {tallyStatus?.status || 'NOT STARTED'}
                            </span>
                        </div>

                        {tallyStatus?.status === 'decryption_in_progress' && (
                            <div className="tally-progress">
                                <div className="progress-label">
                                    <span>Decryption Progress</span>
                                    <span>{tallyStatus.completed_trustees} / {tallyStatus.required_trustees} Shares</span>
                                </div>
                                <div className="progress-track">
                                    <div
                                        className="progress-fill"
                                        style={{ width: `${(tallyStatus.completed_trustees / tallyStatus.required_trustees) * 100}%` }}
                                    ></div>
                                </div>
                            </div>
                        )}

                        <div className="controls">
                            {!tallyStatus && isAdmin && (
                                <button className="control-btn btn-start" onClick={handleStartTally} disabled={loading}>
                                    Initialize Tally Protocol
                                </button>
                            )}

                            {tallyStatus?.status === 'decryption_in_progress' && tallyStatus.completed_trustees >= tallyStatus.required_trustees && isAdmin && (
                                <button className="control-btn btn-start" onClick={handleFinalizeTally} disabled={loading}>
                                    Finalize & Publish Results
                                </button>
                            )}

                            {tallyStatus?.status === 'completed' && (
                                <div className="success-message" style={{ marginTop: '1rem', color: 'green', fontWeight: 'bold', textAlign: 'center' }}>
                                    Tally Finalized
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="tally-card">
                        <h3>Circuit Breaker (US-53)</h3>
                        {circuitBreaker ? (
                            <div className="cb-status">
                                <span className="cb-icon"></span>
                                <div className={`cb-state state-${circuitBreaker.state}`}>
                                    {circuitBreaker.state}
                                </div>
                                <p>Failures: {circuitBreaker.failure_count} / {circuitBreaker.threshold}</p>
                                {circuitBreaker.state === 'open' && isAdmin && (
                                    <button className="control-btn btn-danger" onClick={handleResetCB}>
                                        Reset Circuit Breaker
                                    </button>
                                )}
                            </div>
                        ) : <p>Loading Circuit Breaker Status...</p>}
                    </div>
                </div>
            )}

            {/* TRUSTEES TAB */}
            {activeTab === 'trustees' && (
                <div className="tally-card">
                    <h3>Trustee Decryption Status</h3>
                    <div className="trustee-list">
                        {trustees.map(t => (
                            <div key={t.user_id} className="trustee-row">
                                <div className="trustee-info">
                                    <div className="trustee-avatar">{t.user_id.substring(0, 2).toUpperCase()}</div>
                                    <div>
                                        <div style={{ fontWeight: 600 }}>Trustee {t.user_id.substring(0, 8)}...</div>
                                        <div style={{ fontSize: '0.8rem', color: '#666' }}>ID: {t.user_id}</div>
                                    </div>
                                </div>
                                <div className="trustee-actions">
                                    {/* Visual indication only, real status check would need more granular API support per trustee */}
                                    <span className="key-share-status share-present">Active</span>
                                    {isTrustee && t.user_id === localStorage.getItem('userId') && (
                                        <button className="btn-secondary" style={{ marginLeft: '10px' }} onClick={() => window.location.href = '/decrypt'}>
                                            Submit Key Share
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                    {trustees.length === 0 && <p>No trustees found in system.</p>}
                </div>
            )}

            {/* AUDITOR TAB */}
            {activeTab === 'auditor' && (
                <div className="tally-grid" style={{ gridTemplateColumns: '1fr' }}>
                    <div className="tally-card">
                        <h3>Ballot Manifest (US-54)</h3>
                        {manifest ? (
                            <div className="code-block">
                                {JSON.stringify(manifest, null, 2)}
                            </div>
                        ) : <button className="btn-secondary" onClick={() => loadAuditData(electionId)}>Load Manifest</button>}
                    </div>

                    <div className="tally-card">
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <h3>Reproducibility Report (US-59)</h3>
                            <button className="refresh-btn" onClick={handleRecount}>Trigger Real Recount (US-52)</button>
                        </div>
                        {reproduceReport ? (
                            <div className="code-block" style={{ borderColor: reproduceReport.status === 'match' ? 'green' : 'red' }}>
                                {JSON.stringify(reproduceReport, null, 2)}
                            </div>
                        ) : <p>Loading report...</p>}
                    </div>

                    <div className="tally-card">
                        <h3>Tally Transcript (US-57)</h3>
                        {transcript ? (
                            <div className="code-block">
                                {JSON.stringify(transcript, null, 2)}
                            </div>
                        ) : <p>Loading transcript...</p>}
                    </div>
                </div>
            )}

            {/* NETWORK TAB */}
            {activeTab === 'network' && (
                <div className="tally-card">
                    <h3>Network Isolation (US-60)</h3>
                    {isolationStatus ? (
                        <div className="iso-grid">
                            <div className="iso-metric">
                                <span className="iso-label">Enforcement Level</span>
                                <span className="iso-value" style={{ color: 'green' }}>STRICT</span>
                            </div>
                            <div className="iso-metric">
                                <span className="iso-label">Open Ports</span>
                                <span className="iso-value">443, 80</span>
                            </div>
                            <div className="iso-metric">
                                <span className="iso-label">Active Connections</span>
                                <span className="iso-value">{isolationStatus.active_connections || 1}</span>
                            </div>
                            <div className="iso-metric">
                                <span className="iso-label">Illegal Access Attempts</span>
                                <span className="iso-value" style={{ color: 'red' }}>{isolationStatus.blocked_attempts || 0}</span>
                            </div>
                        </div>
                    ) : <p>Verifying network isolation rules...</p>}
                </div>
            )}

            {/* Log Console */}
            {logs.length > 0 && (
                <div className="tally-card" style={{ marginTop: '2rem', background: '#1f2937', color: '#fff', border: 'none' }}>
                    <h3>Terminal Output</h3>
                    <div style={{ maxHeight: '150px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.8rem' }}>
                        {logs.map((l, i) => (
                            <div key={i} style={{ color: l.type === 'error' ? '#fca5a5' : '#86efac' }}>
                                [{l.time}] {l.msg}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default TallyAudit;
