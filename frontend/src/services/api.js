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
  getIncidents: () => api.get('/ops/incidents'),
  createIncident: (data) => api.post('/ops/incidents', data, { headers: { 'X-User-Role': 'admin' } }),
  updateIncident: (id, data) => api.put(`/ops/incidents/${id}`, data, { headers: { 'X-User-Role': 'admin' } }),
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
  simulateThreat: (data) => api.post('/security/simulate', data, { headers: { 'X-User-Role': 'admin' } }),
  replayLedger: (electionId) => api.post('/security/replay-ledger', { election_id: electionId }),
  getAnomalies: () => api.get('/security/anomalies'),
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
