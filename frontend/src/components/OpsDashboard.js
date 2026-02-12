
import React, { useState, useEffect } from 'react';
import { opsAPI, resultsAPI, authAPI } from '../services/api';
import './OpsDashboard.css';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const OpsDashboard = () => {
    const [metrics, setMetrics] = useState(null);
    const [incidents, setIncidents] = useState([]);
    const [disputes, setDisputes] = useState([]);
    const [activeTab, setActiveTab] = useState('incidents'); // incidents | disputes
    const [loading, setLoading] = useState(true);
    const [electionId, setElectionId] = useState(null);

    // Modal State
    const [showIncidentModal, setShowIncidentModal] = useState(false);
    const [showReviewModal, setShowReviewModal] = useState(false);
    const [selectedIncident, setSelectedIncident] = useState(null);
    const [selectedDispute, setSelectedDispute] = useState(null);
    const [incidentActions, setIncidentActions] = useState([]);
    const [disputeActions, setDisputeActions] = useState([]);
    const [actionNote, setActionNote] = useState('');
    const [users, setUsers] = useState([]);
    const [userUpdate, setUserUpdate] = useState({});
    const authRole = localStorage.getItem('authRole');
    const canAccessControl = authRole === 'admin';
    const canDownloadArtifacts = authRole === 'admin' || authRole === 'auditor';
    const canReportIncident = authRole === 'security_engineer' || authRole === 'admin';
    const canUpdateIncidentStatus = authRole === 'admin' || authRole === 'auditor';
    const canViewDisputes = authRole === 'admin' || authRole === 'auditor';
    const canFileDisputes = authRole === 'auditor';

    // Form State
    const [newIncident, setNewIncident] = useState({ title: '', severity: 'low', description: '' });
    const [disputeForm, setDisputeForm] = useState({
        title: '',
        description: '',
        evidence: '',
        justification: '',
        category: 'Tally Mismatch'
    });

    useEffect(() => {
        resultsAPI.getAll().then(res => {
            if (res.data && res.data.length > 0) setElectionId(res.data[0].election_id);
        });
        loadIncidents();
        if (canViewDisputes) {
            loadDisputes();
        }
        if (canAccessControl) {
            loadUsers();
        }
    }, []);

    useEffect(() => {
        if (!canViewDisputes && activeTab === 'disputes') {
            setActiveTab('incidents');
        }
    }, [canViewDisputes, activeTab]);

    useEffect(() => {
        if (electionId) loadMetrics(electionId);
    }, [electionId]);

    const loadMetrics = async (id) => {
        try {
            const res = await opsAPI.getDashboardMetrics(id);
            setMetrics(res.data);
            setLoading(false);
        } catch (err) {
            console.error("Failed to load metrics", err);
            setLoading(false);
        }
    };

    const loadIncidents = async () => {
        try {
            const res = await opsAPI.getIncidents();
            setIncidents(res.data);
        } catch (err) {
            console.error("Failed to load incidents", err);
        }
    };

    const loadDisputes = async () => {
        try {
            const res = await opsAPI.getDisputes();
            setDisputes(res.data);
        } catch (err) {
            console.error("Failed to load disputes", err);
        }
    };

    const loadIncidentActions = async (id) => {
        try {
            const res = await opsAPI.getIncidentActions(id);
            setIncidentActions(res.data);
        } catch (err) {
            console.error("Failed to load incident actions", err);
        }
    };

    const loadDisputeActions = async (id) => {
        try {
            const res = await opsAPI.getDisputeActions(id);
            setDisputeActions(res.data);
        } catch (err) {
            console.error("Failed to load dispute actions", err);
        }
    };

    const loadUsers = async () => {
        try {
            const res = await authAPI.listUsers();
            setUsers(res.data);
        } catch (err) {
            console.error("Failed to load users", err);
        }
    };

    const handleUserUpdate = async (userId) => {
        try {
            const payload = userUpdate[userId];
            if (!payload) return;
            await authAPI.updateUserRole(userId, payload);
            await loadUsers();
        } catch (err) {
            alert(err.response?.data?.detail || 'Failed to update user');
        }
    };

    const handleDownloadEvidence = async () => {
        if (!electionId) return;
        try {
            const response = await opsAPI.downloadEvidence(electionId);
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `evidence_${electionId}.zip`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            console.error("Download failed", err);
        }
    };

    const handleDownloadCompliance = async () => {
        if (!electionId) return;
        try {
            const response = await opsAPI.downloadComplianceReport(electionId);
            const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `compliance_${electionId}.json`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            console.error("Compliance report download failed", err);
        }
    };

    const handleReportIncident = async (e) => {
        e.preventDefault();
        try {
            await opsAPI.createIncident({
                ...newIncident,
                reported_by: "DemoUser"
            });
            setNewIncident({ title: '', severity: 'low', description: '' });
            setShowIncidentModal(false);
            loadIncidents();
        } catch (err) {
            console.error("Failed to report incident", err);
        }
    };

    const handleFileDispute = async (e) => {
        e.preventDefault();
        try {
            const disputeData = {
                title: `${disputeForm.category}: ${disputeForm.title}`,
                description: `${disputeForm.description}\n\nJUSTIFICATION:\n${disputeForm.justification}`,
                evidence: [disputeForm.evidence],
                election_id: electionId,
                filed_by: "DemoUser"
            };
            await opsAPI.createDispute(disputeData);
            setDisputeForm({ title: '', description: '', evidence: '', justification: '', category: 'Tally Mismatch' }); // Reset
            loadDisputes();
            alert("Dispute Filed Successfully. Case assigned to Compliance.");
        } catch (err) {
            console.error("Failed to file dispute", err);
            alert("Error filing dispute: " + err.message);
        }
    };

    const handleUpdateIncidentStatus = async (status) => {
        if (!selectedIncident) return;
        try {
            await opsAPI.updateIncident(selectedIncident.incident_id, { status });
            setShowReviewModal(false);
            loadIncidents();
        } catch (err) {
            alert("Failed. Check permissions (Admin/Auditor only).");
        }
    };

    const handleUpdateDisputeStatus = async (status) => {
        if (!selectedDispute) return;
        try {
            await opsAPI.updateDispute(selectedDispute.dispute_id, { status });
            setShowReviewModal(false);
            loadDisputes();
        } catch (err) {
            alert("Failed. Check permissions (Admin/Auditor only).");
        }
    };

    const handleAddActionNote = async () => {
        if (!actionNote.trim()) return;
        try {
            if (selectedIncident) {
                await opsAPI.addIncidentAction(selectedIncident.incident_id, {
                    action_type: 'NOTE',
                    details: { note: actionNote }
                });
                loadIncidentActions(selectedIncident.incident_id);
            }
            if (selectedDispute) {
                await opsAPI.updateDispute(selectedDispute.dispute_id, {
                    evidence: [actionNote]
                });
                loadDisputeActions(selectedDispute.dispute_id);
            }
            setActionNote('');
        } catch (err) {
            alert("Failed to add action note");
        }
    };

    const handleDownloadIncidentReport = async () => {
        if (!selectedIncident) return;
        try {
            const response = await opsAPI.downloadIncidentReport(selectedIncident.incident_id);
            const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `incident_${selectedIncident.incident_id}.json`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            console.error("Incident report download failed", err);
        }
    };

    const handleDownloadDisputeReport = async () => {
        if (!selectedDispute) return;
        try {
            const response = await opsAPI.downloadDisputeReport(selectedDispute.dispute_id);
            const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `dispute_${selectedDispute.dispute_id}.json`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err) {
            console.error("Dispute report download failed", err);
        }
    };

    const roleOptions = ['voter', 'admin', 'trustee', 'auditor', 'security_engineer'];
    const selectedRecord = selectedIncident || selectedDispute;
    const isIncident = Boolean(selectedIncident);

    if (loading && !electionId) return <div className="loading"><div className="spinner"></div>Loading Dashboard...</div>;

    return (
        <div className="ops-dashboard">
            <div className="dashboard-header">
                <h2>Ops & Transparency Dashboard</h2>
                <div className="header-actions">
                    <button className="btn-secondary" onClick={() => loadIncidents()}>Refresh</button>
                </div>
            </div>

            {/* Top Metrics Section */}
            <div className="dashboard-grid">
                <div className="card pulse-card">
                    <h3>Election Pulse</h3>
                    {metrics ? (
                        <div className="stats-grid">
                            <div className="stat-item">
                                <span className="stat-label">Status</span>
                                <span className={`badge status-${metrics.election_status}`}>{metrics.election_status}</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-label">Turnout</span>
                                <span className="stat-value">{metrics.turnout_percentage.toFixed(1)}%</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-label">Trustees</span>
                                <span className="stat-value">{metrics.trustees_active}</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-label">Ledger Height</span>
                                <span className="stat-value">#{metrics.ledger_height || 0}</span>
                            </div>
                        </div>
                    ) : <p>Select an election to view metrics</p>}
                </div>

                <div className="card evidence-card">
                    <h3>Audit Artifacts</h3>
                    <div className="evidence-content">
                        <p className="description-text">
                            Verifiable evidence package including signed manifests, logs, and tally results.
                        </p>
                        {canDownloadArtifacts ? (
                            <>
                                <button
                                    onClick={handleDownloadEvidence}
                                    className="download-btn w-full justify-center"
                                    disabled={!electionId}
                                >
                                    Download Evidence ZIP
                                </button>
                                <button
                                    onClick={handleDownloadCompliance}
                                    className="download-btn w-full justify-center"
                                    disabled={!electionId}
                                    style={{ marginTop: '0.75rem' }}
                                >
                                    Download Compliance Report
                                </button>
                            </>
                        ) : (
                            <p className="text-xs text-gray-500">Artifacts are available to admin and auditor roles.</p>
                        )}
                    </div>
                </div>
            </div>

            {canAccessControl && (
                <div className="card access-card">
                    <h3>Access Control</h3>
                    <p className="description-text">Assign roles and set trustee verification limits.</p>
                    <div className="access-table">
                        <div className="access-row access-header">
                            <span>User ID</span>
                            <span>Role</span>
                            <span>Trustee Limit</span>
                            <span>Action</span>
                        </div>
                        {users.map(user => (
                            <div className="access-row" key={user.user_id}>
                                <span className="mono">{user.user_id}</span>
                                <select
                                    value={userUpdate[user.user_id]?.role || user.role}
                                    onChange={(e) =>
                                        setUserUpdate(prev => ({
                                            ...prev,
                                            [user.user_id]: {
                                                ...prev[user.user_id],
                                                role: e.target.value
                                            }
                                        }))
                                    }
                                >
                                    {roleOptions.map(role => (
                                        <option key={role} value={role}>{role}</option>
                                    ))}
                                </select>
                                <input
                                    type="number"
                                    placeholder="Limit"
                                    value={userUpdate[user.user_id]?.trustee_vote_limit ?? user.trustee_vote_limit ?? ''}
                                    onChange={(e) =>
                                        setUserUpdate(prev => ({
                                            ...prev,
                                            [user.user_id]: {
                                                ...prev[user.user_id],
                                                trustee_vote_limit: e.target.value === '' ? null : Number(e.target.value)
                                            }
                                        }))
                                    }
                                    disabled={(userUpdate[user.user_id]?.role || user.role) !== 'trustee'}
                                />
                                <button onClick={() => handleUserUpdate(user.user_id)}>Update</button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Main Content Area */}
            <div className="card main-content-card">
                <div className="tabs-container">
                    <button
                        className={`tab-btn ${activeTab === 'incidents' ? 'active' : ''}`}
                        onClick={() => setActiveTab('incidents')}
                    >
                        Incident Response (US-70)
                    </button>
                    {canViewDisputes && (
                        <button
                            className={`tab-btn ${activeTab === 'disputes' ? 'active' : ''}`}
                            onClick={() => setActiveTab('disputes')}
                        >
                            Dispute Resolution (US-71)
                        </button>
                    )}
                </div>

                {/* INCIDENTS TAB */}
                {activeTab === 'incidents' && (
                    <div className="incidents-container">
                        <div className="section-header">
                            <h4>Active Incidents</h4>
                            {canReportIncident && (
                                <button className="action-btn" onClick={() => setShowIncidentModal(true)}>
                                    Report Incident
                                </button>
                            )}
                        </div>

                        <div className="incidents-list">
                            {incidents.length === 0 ? (
                                <div className="empty-state">No open incidents. Systems nominal.</div>
                            ) : (
                                incidents.map(inc => (
                                    <div
                                        key={inc.incident_id}
                                        className={`incident-row severity-${inc.severity}`}
                                        onClick={() => {
                                            setSelectedIncident(inc);
                                            setSelectedDispute(null);
                                            setActionNote('');
                                            loadIncidentActions(inc.incident_id);
                                            setShowReviewModal(true);
                                        }}
                                    >
                                        <div className="incident-meta">
                                            <span className={`badge severity-${inc.severity}`}>{inc.severity}</span>
                                            <span className="timestamp">{new Date(inc.created_at).toLocaleTimeString()}</span>
                                        </div>
                                        <div className="incident-main">
                                            <div className="title">{inc.title}</div>
                                            <div className="desc-preview">{inc.description.substring(0, 60)}...</div>
                                        </div>
                                        <div className="incident-status">
                                            <span className={`status-dot status-${inc.status}`}></span> {inc.status}
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                )}

                {/* DISPUTES TAB */}
                {activeTab === 'disputes' && canViewDisputes && (
                    <div className="disputes-layout">
                        <div className="dispute-form-col">
                            <h4 className="section-title">File Formal Dispute</h4>
                            {canFileDisputes ? (
                                <form onSubmit={handleFileDispute} className="form-stack">
                                    <div>
                                        <label className="form-label">Nature of Dispute</label>
                                        <select className="form-select" value={disputeForm.category} onChange={e => setDisputeForm({ ...disputeForm, category: e.target.value })}>
                                            <option>Tally Mismatch</option>
                                            <option>Ledger Corruption</option>
                                            <option>Procedural Violation</option>
                                            <option>Other</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="form-label">Case Title</label>
                                        <input className="form-input" placeholder="Short summary" required value={disputeForm.title} onChange={e => setDisputeForm({ ...disputeForm, title: e.target.value })} />
                                    </div>
                                    <div>
                                        <label className="form-label">Evidence (Hash/URL)</label>
                                        <input className="form-input" placeholder="Artifact hash or link..." required value={disputeForm.evidence} onChange={e => setDisputeForm({ ...disputeForm, evidence: e.target.value })} />
                                    </div>
                                    <div>
                                        <label className="form-label">Formal Justification</label>
                                        <textarea className="form-textarea" placeholder="Explain why this dispute is valid..." required value={disputeForm.justification} onChange={e => setDisputeForm({ ...disputeForm, justification: e.target.value })} />
                                    </div>
                                    <div className="warning-box">
                                        False disputes may result in credential revocation.
                                    </div>
                                    <button className="btn-primary w-full">Submit Case</button>
                                </form>
                            ) : (
                                <p className="description-text">Dispute filing is restricted to auditors.</p>
                            )}
                        </div>

                        <div className="dispute-list-col">
                            <h4 className="section-title">Active Disputes</h4>
                            <div className="disputes-grid">
                                {disputes.map(dispute => (
                                    <div
                                        key={dispute.dispute_id}
                                        className="dispute-card"
                                        onClick={() => {
                                            setSelectedDispute(dispute);
                                            setSelectedIncident(null);
                                            setActionNote('');
                                            loadDisputeActions(dispute.dispute_id);
                                            setShowReviewModal(true);
                                        }}
                                    >
                                        <div className="dispute-header">
                                            <span className="case-id">CASE-{dispute.dispute_id.substring(0, 6)}</span>
                                            <span className={`badge status-${dispute.status}`}>{dispute.status}</span>
                                        </div>
                                        <h5 className="dispute-title">{dispute.title}</h5>
                                        <p className="dispute-desc">{dispute.description.split('\n')[0]}</p>
                                        <div className="review-link">Review Evidence</div>
                                    </div>
                                ))}
                                {disputes.length === 0 && (
                                    <div className="empty-state">No active disputes filed.</div>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* MODAL: Report Incident */}
            {showIncidentModal && canReportIncident && (
                <div className="modal-overlay">
                    <div className="modal-content">
                        <div className="modal-header">
                            <h3>Report Alert</h3>
                            <button onClick={() => setShowIncidentModal(false)} className="close-btn">Close</button>
                        </div>
                        <form onSubmit={handleReportIncident} className="form-stack">
                            <input className="form-input" placeholder="Title" value={newIncident.title} onChange={e => setNewIncident({ ...newIncident, title: e.target.value })} required />
                            <select className="form-select" value={newIncident.severity} onChange={e => setNewIncident({ ...newIncident, severity: e.target.value })}>
                                <option value="low">Low</option>
                                <option value="medium">Medium</option>
                                <option value="high">High</option>
                                <option value="critical">Critical</option>
                            </select>
                            <textarea className="form-textarea" placeholder="Details..." value={newIncident.description} onChange={e => setNewIncident({ ...newIncident, description: e.target.value })} required />
                            <button className="btn-primary w-full">Submit Report</button>
                        </form>
                    </div>
                </div>
            )}

            {/* MODAL: Review Incident/Dispute */}
            {showReviewModal && selectedRecord && (
                <div className="modal-overlay">
                    <div className="modal-content large-modal">
                        <div className="modal-header">
                            <div className="header-title-group">
                                <h3 className="m-0">{selectedRecord.title}</h3>
                                {selectedRecord.severity && (
                                    <span className={`badge severity-${selectedRecord.severity}`}>{selectedRecord.severity}</span>
                                )}
                            </div>
                            <button onClick={() => setShowReviewModal(false)} className="close-btn">Close</button>
                        </div>

                        <div className="modal-body mb-6">
                            <div className="detail-group">
                                <label>Description</label>
                                <div className="detail-content whitespace-pre-wrap">{selectedRecord.description}</div>
                            </div>
                            <div className="detail-flex-row">
                                <div className="detail-group w-1/2">
                                    <label>Reported By</label>
                                    <div className="font-mono text-sm">{selectedRecord.reported_by || selectedRecord.filed_by || 'System'}</div>
                                </div>
                                <div className="detail-group w-1/2">
                                    <label>Timestamp</label>
                                    <div className="font-mono text-sm">{new Date(selectedRecord.created_at).toLocaleString()}</div>
                                </div>
                            </div>
                        </div>

                        <div className="detail-group mb-4">
                            <label>Action Log</label>
                            <div className="detail-content">
                                {(isIncident ? incidentActions : disputeActions).length === 0 ? (
                                    <div className="text-gray-500">No actions recorded yet.</div>
                                ) : (
                                    (isIncident ? incidentActions : disputeActions).map((action) => (
                                        <div key={action.action_id} className="action-row">
                                            <span className="font-mono text-xs">{action.action_type}</span>
                                            <span className="text-xs text-gray-500">{new Date(action.created_at).toLocaleString()}</span>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        <div className="detail-group mb-6">
                            <label>Add Note / Evidence</label>
                            <div className="action-input-group">
                                <input
                                    className="form-input"
                                    placeholder="Add a note or evidence reference"
                                    value={actionNote}
                                    onChange={(e) => setActionNote(e.target.value)}
                                />
                                <button className="btn-secondary" onClick={handleAddActionNote}>Add</button>
                            </div>
                        </div>

                        <div className="modal-actions">
                            {isIncident && canUpdateIncidentStatus && (
                                <>
                                    <button className="btn-secondary" onClick={() => handleUpdateIncidentStatus('open')}>Mark Open</button>
                                    <button className="btn-secondary" onClick={() => handleUpdateIncidentStatus('triage')}>Triage</button>
                                    <button className="btn-secondary" onClick={() => handleUpdateIncidentStatus('mitigated')}>Mitigate</button>
                                    <button className="btn-primary success" onClick={() => handleUpdateIncidentStatus('resolved')}>Resolve</button>
                                    <button className="btn-secondary" onClick={handleDownloadIncidentReport}>Download Report</button>
                                </>
                            )}
                            {!isIncident && canUpdateIncidentStatus && (
                                <>
                                    <button className="btn-secondary" onClick={() => handleUpdateDisputeStatus('open')}>Mark Open</button>
                                    <button className="btn-secondary" onClick={() => handleUpdateDisputeStatus('triage')}>Triage</button>
                                    <button className="btn-secondary" onClick={() => handleUpdateDisputeStatus('investigating')}>Investigate</button>
                                    <button className="btn-primary success" onClick={() => handleUpdateDisputeStatus('resolved')}>Resolve</button>
                                    <button className="btn-secondary" onClick={handleDownloadDisputeReport}>Download Report</button>
                                </>
                            )}
                            {!canUpdateIncidentStatus && (
                                <span className="text-sm text-gray-500">Status updates are restricted to admin and auditor roles.</span>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default OpsDashboard;
