/**
 * API Service for E-Voting System
 * Handles all HTTP requests to the backend
 */

import axios from 'axios';

// Use relative URL to leverage proxy configuration
const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 60 second timeout for long operations like vote encryption
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Trustees API
export const trusteesAPI = {
  getAll: () => api.get('/trustees'),
  getById: (id) => api.get(`/trustees/${id}`),
  register: (data) => api.post('/trustees/register', data),
  generateKeyShare: (trusteeId) => api.post(`/trustees/${trusteeId}/key-share`),
  getThresholdInfo: () => api.get('/trustees/threshold/info'),
};

// Tallying API
export const tallyingAPI = {
  start: (electionId) => api.post('/tally/start', { election_id: electionId }),
  partialDecrypt: (trusteeId, electionId) =>
    api.post(`/tally/partial-decrypt/${trusteeId}?election_id=${electionId}`),
  finalize: (electionId) => api.post('/tally/finalize', { election_id: electionId }),
  getStatus: (electionId) => api.get(`/tally/status/${electionId}`),
  getAggregationInfo: (electionId) => api.get(`/tally/aggregate-info/${electionId}`),

  // New Epic 4 Endpoints
  getBallotManifest: (electionId) => api.get(`/tally/manifest/${electionId}`),
  getCircuitBreaker: (electionId) => api.get(`/tally/circuit-breaker/${electionId}`),
  resetCircuitBreaker: (electionId) => api.post(`/tally/circuit-breaker/${electionId}/reset`),
  getTranscript: (electionId) => api.get(`/tally/transcript/${electionId}`),
  getReproducibilityReport: (electionId) => api.get(`/tally/reproducibility/${electionId}`),
  triggerRecount: (electionId) => api.post(`/tally/recount/${electionId}`),
  getTrusteeTimeout: (electionId) => api.get(`/tally/trustee-timeout/${electionId}`),
  getIsolationStatus: () => api.get('/tally/isolation-status'),
  getElectionTypes: () => api.get('/tally/election-types'),
};

// Results API
export const resultsAPI = {
  getAll: () => api.get('/results'),
  getByElectionId: (electionId) => api.get(`/results/${electionId}`),
  verify: (electionId) => api.post('/results/verify', { election_id: electionId }),
  getAuditLog: (electionId) => api.get(`/results/audit-log/${electionId}`),
  publishToBlockchain: (electionId) => api.post(`/results/publish/${electionId}`),

  getSummary: (electionId) => api.get(`/results/summary/${electionId}`),
};

// Ops API (US-65, US-66, US-70)
// Ops API (US-65, US-66, US-70)
export const opsAPI = {
  getDashboardMetrics: (electionId) => api.get(`/ops/dashboard/${electionId}`),
  downloadEvidence: (electionId) => api.get(`/ops/evidence/${electionId}`, { responseType: 'blob' }),
  downloadComplianceReport: (electionId) => api.get(`/ops/compliance-report/${electionId}`),
  getIncidents: () => api.get('/ops/incidents'),
  createIncident: (data) => api.post('/ops/incidents', data),
  updateIncident: (id, data) => api.put(`/ops/incidents/${id}`, data),
  getIncidentActions: (id) => api.get(`/ops/incidents/${id}/actions`),
  addIncidentAction: (id, data) => api.post(`/ops/incidents/${id}/actions`, data),
  downloadIncidentReport: (id) => api.get(`/ops/incidents/${id}/report`),
  getDisputes: () => api.get('/ops/disputes'),
  createDispute: (data) => api.post('/ops/disputes', data),
  updateDispute: (id, data) => api.put(`/ops/disputes/${id}`, data),
  getDisputeActions: (id) => api.get(`/ops/disputes/${id}/actions`),
  downloadDisputeReport: (id) => api.get(`/ops/disputes/${id}/report`),
};

// Verification API (US-62, US-63)
export const verificationAPI = {
  verifyReceipt: (receiptHash, electionId) =>
    api.post('/verify/receipt', { receipt_hash: receiptHash, election_id: electionId }),
  verifyZKProof: (proofBundle, electionId) =>
    api.post('/verify/zk-proof', { proof_bundle: proofBundle, election_id: electionId }),
};

// Security API (US-68, US-64, US-69)
export const securityAPI = {
  simulateThreat: (data) => api.post('/security/simulate', data),
  replayLedger: (electionId) => api.post('/security/replay-ledger', { election_id: electionId }),
  getAnomalies: () => api.get('/security/anomalies'),
  getAnomalyReport: () => api.get('/security/anomaly-report'),
  getReplayTimeline: (params) => api.get('/security/replay-timeline', { params }),
};

// Auth API (non /api prefix)
export const authAPI = {
  login: (credential) => axios.post('/auth/login', { credential }),
  me: () => axios.get('/auth/me', { headers: { Authorization: `Bearer ${localStorage.getItem('authToken')}` } }),
  listUsers: () => axios.get('/auth/users', { headers: { Authorization: `Bearer ${localStorage.getItem('authToken')}` } }),
  updateUserRole: (userId, data) => axios.put(`/auth/users/${userId}/role`, data, { headers: { Authorization: `Bearer ${localStorage.getItem('authToken')}` } }),
};


// Mock Data API
export const mockDataAPI = {
  generateVotes: (count, electionId) =>
    api.post(`/mock/generate-votes?count=${count}${electionId ? `&election_id=${electionId}` : ''}`),
  resetDatabase: () => api.post('/mock/reset-database?confirm=true'),
  getElectionStats: (electionId) =>
    api.get(`/mock/election-stats${electionId ? `?election_id=${electionId}` : ''}`),
  setupTrustees: () => api.post('/mock/setup-trustees'),
  generateZKProof: (electionId) => api.post(`/mock/generate-zk-proof?election_id=${electionId}`),
};

// Health Check
export const healthCheck = () => api.get('/health', { baseURL: '' });

export default api;
