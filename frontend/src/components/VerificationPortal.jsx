
import React, { useState, useEffect } from 'react';
import { verificationAPI, resultsAPI, mockDataAPI } from '../services/api';
import './VerificationPortal.css';

const VerificationPortal = () => {
    const authRole = localStorage.getItem('authRole');
    const canReceipt = authRole === 'voter' || authRole === 'admin';
    const canProof = authRole === 'auditor' || authRole === 'security_engineer' || authRole === 'admin';
    const [receiptHash, setReceiptHash] = useState('');
    const [verificationResult, setVerificationResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('receipt');
    const [proofJson, setProofJson] = useState('');
    const [electionId, setElectionId] = useState(null);

    useEffect(() => {
        // Fetch active election ID
        resultsAPI.getAll().then(res => {
            if (res.data && res.data.length > 0) {
                setElectionId(res.data[0].election_id);
            }
        });
    }, []);

    useEffect(() => {
        if (canReceipt && !canProof) {
            setActiveTab('receipt');
        } else if (!canReceipt && canProof) {
            setActiveTab('proof');
        }
    }, [canReceipt, canProof]);

    const handleReceiptVerify = async (e) => {
        e.preventDefault();
        if (!receiptHash || !electionId) return;

        setLoading(true);
        setVerificationResult(null);
        try {
            let receiptValue = receiptHash;
            if (receiptHash.trim().startsWith('{')) {
                try {
                    const parsed = JSON.parse(receiptHash);
                    receiptValue = parsed?.receipt_hash || parsed?.receiptHash || receiptHash;
                } catch (parseError) {
                    receiptValue = receiptHash;
                }
            }
            const res = await verificationAPI.verifyReceipt(receiptValue, electionId);
            setVerificationResult({
                type: 'receipt',
                data: res.data,
                success: res.data.status === 'verified'
            });
        } catch (err) {
            setVerificationResult({
                type: 'receipt',
                success: false,
                error: err.response?.data?.detail || "Verification failed"
            });
        }
        setLoading(false);
    };

    const handleGenerateProof = async () => {
        if (!electionId) return;
        setLoading(true);
        try {
            const res = await mockDataAPI.generateZKProof(electionId);
            const bundle = res.data?.proof_bundle || res.data;
            setProofJson(JSON.stringify(bundle, null, 2));
        } catch (err) {
            console.error(err);
            alert("Failed to generate proof. Ensure election is COMPLETED.");
        }
        setLoading(false);
    };

    const handleProofVerify = async () => {
        if (!proofJson || !electionId) return;

        setLoading(true);
        setVerificationResult(null);
        try {
            const parsed = JSON.parse(proofJson);
            const proofBundle = parsed?.proof_bundle || parsed;
            const res = await verificationAPI.verifyZKProof(proofBundle, electionId);
            setVerificationResult({
                type: 'proof',
                data: res.data,
                success: res.data.is_valid
            });
        } catch (err) {
            setVerificationResult({
                type: 'proof',
                success: false,
                error: "Invalid JSON or verification failure"
            });
        }
        setLoading(false);
    };

    return (
        <div className="verification-portal">
            <h2>Verification Center</h2>

            <div className="portal-grid">
                {/* Receipt Verifier */}
                {canReceipt && (
                    <div className={`verifier-card ${activeTab === 'receipt' ? 'ring-2' : ''}`}
                        onClick={() => setActiveTab('receipt')}>
                        <h3>Voter Receipt Validator</h3>
                        <p className="verifier-desc">
                            Paste your unique receipt hash to verify that your ballot was included in the ledger.
                        </p>

                        <form onSubmit={handleReceiptVerify}>
                            <div className="input-group">
                                <label className="input-label">Receipt Hash</label>
                                <input
                                    className="verification-input"
                                    placeholder="0x..."
                                    value={receiptHash}
                                    onChange={(e) => setReceiptHash(e.target.value)}
                                />
                            </div>
                            <button
                                className="verify-btn"
                                type="submit"
                                disabled={loading || !electionId}
                            >
                                {loading && activeTab === 'receipt' ? 'Verifying...' : 'Verify Receipt'}
                            </button>
                        </form>
                    </div>
                )}

                {/* ZK Proof Verifier */}
                {canProof && (
                    <div className={`verifier-card ${activeTab === 'proof' ? 'ring-2' : ''}`}
                        onClick={() => setActiveTab('proof')}>
                        <h3>Zero-Knowledge Proof Check</h3>
                        <p className="verifier-desc">
                            Independently audit the tally results by verifying the ZK proof bundle.
                        </p>

                        <div className="input-group">
                            <div className="proof-input-header">
                                <label className="input-label">Proof Bundle (JSON)</label>
                                <button
                                    type="button"
                                    onClick={(e) => { e.stopPropagation(); handleGenerateProof(); }}
                                    className="generate-proof-btn"
                                    disabled={loading || !electionId}
                                >
                                    <span></span> Generate Mock Proof
                                </button>
                            </div>
                            <textarea
                                className="verification-input"
                                rows="6"
                                placeholder='{"proof": "...", "public_inputs": "..."}'
                                value={proofJson}
                                onChange={(e) => setProofJson(e.target.value)}
                            />
                        </div>
                        <button
                            className="verify-btn"
                            onClick={handleProofVerify}
                            disabled={loading || !electionId}
                        >
                            {loading && activeTab === 'proof' ? 'Running Audit...' : 'Audit Tally Proof'}
                        </button>
                    </div>
                )}
            </div>

            {!canReceipt && !canProof && (
                <div className="verifier-card">
                    <p className="no-access-msg">Verification tools are not available for this role.</p>
                </div>
            )}

            {/* Verification Result */}
            {verificationResult && (
                <div className={`verification-result ${verificationResult.success ? 'result-valid' : 'result-invalid'}`}>
                    <div className="result-header">
                        <span className="result-icon"></span>
                        <span className={`result-text ${verificationResult.success ? 'valid-text' : 'invalid-text'}`}>
                            {verificationResult.success ? 'Verification Successful' : 'Verification Failed'}
                        </span>
                    </div>

                    {verificationResult.type === 'receipt' && verificationResult.data && (
                        <div className="result-details">
                            <div className="detail-row">
                                <span className="detail-label">Status</span>
                                <span className="detail-value">{verificationResult.data.status.toUpperCase()}</span>
                            </div>
                            <div className="detail-row">
                                <span className="detail-label">Block Height</span>
                                <span className="detail-value">#{verificationResult.data.block_index}</span>
                            </div>
                            <div className="detail-row">
                                <span className="detail-label">Timestamp</span>
                                <span className="detail-value">{new Date(verificationResult.data.timestamp).toLocaleString()}</span>
                            </div>
                        </div>
                    )}

                    {verificationResult.type === 'proof' && verificationResult.data && (
                        <div className="result-details">
                            <div className="detail-row">
                                <span className="detail-label">Evidence Hash</span>
                                <span className="detail-value">{verificationResult.data.evidence_hash.substring(0, 32)}...</span>
                            </div>
                            <div className="detail-row">
                                <span className="detail-label">Compute Time</span>
                                <span className="detail-value">{verificationResult.data.verification_time_ms.toFixed(2)} ms</span>
                            </div>
                            <div className="code-preview">
                                {JSON.stringify(verificationResult.data.details, null, 2)}
                            </div>
                        </div>
                    )}

                    {verificationResult.error && (
                        <p className="error-msg">{verificationResult.error}</p>
                    )}
                </div>
            )}
        </div>
    );
};

export default VerificationPortal;
