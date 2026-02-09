import React, { useState, useEffect, useRef } from 'react';
import { mockDataAPI, tallyingAPI, resultsAPI } from '../services/api';
import './TestingPanel.css';

// Step status constants
const STATUS = {
  PENDING: 'pending',
  RUNNING: 'running',
  SUCCESS: 'success',
  ERROR: 'error',
  SKIPPED: 'skipped'
};

function TestingPanel() {
  const authRole = localStorage.getItem('authRole');
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState([]);
  const [activeStep, setActiveStep] = useState(null);
  const [stepStatuses, setStepStatuses] = useState({
    setup: STATUS.PENDING,
    votes: STATUS.PENDING,
    ballots: STATUS.PENDING,
    tally: STATUS.PENDING,
    trustees: STATUS.PENDING,
    finalize: STATUS.PENDING,
    blockchain: STATUS.PENDING
  });
  const [expandedLogs, setExpandedLogs] = useState(true);
  const logContainerRef = useRef(null);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    loadStats();
  }, []);

  // Auto-scroll logs to bottom
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const addLog = (message, type = 'info', details = null) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prev => [...prev, { timestamp, message, type, details, id: Date.now() }]);
  };

  const clearLogs = () => setLogs([]);

  const loadStats = async () => {
    try {
      const response = await mockDataAPI.getElectionStats();
      setStats(response.data);
      updateStepStatusesFromStats(response.data);
      return response.data;
    } catch (err) {
      console.error('Failed to load stats:', err);
      return null;
    }
  };

  const updateStepStatusesFromStats = (data) => {
    if (!data) return;
    
    setStepStatuses(prev => ({
      ...prev,
      setup: data.tallying?.started !== undefined ? STATUS.SUCCESS : STATUS.PENDING,
      votes: data.votes?.total > 0 ? STATUS.SUCCESS : STATUS.PENDING,
      ballots: data.votes?.total > 0 ? STATUS.SUCCESS : STATUS.PENDING,
      tally: data.tallying?.started ? STATUS.SUCCESS : STATUS.PENDING,
      trustees: data.tallying?.trustees_completed >= 3 ? STATUS.SUCCESS : 
                data.tallying?.trustees_completed > 0 ? STATUS.RUNNING : STATUS.PENDING,
      finalize: data.tallying?.status === 'completed' ? STATUS.SUCCESS : STATUS.PENDING,
      blockchain: data.blockchain?.published ? STATUS.SUCCESS : STATUS.PENDING
    }));
  };

  const updateStepStatus = (step, status) => {
    setStepStatuses(prev => ({ ...prev, [step]: status }));
  };

  // Step 1: Setup Trustees
  const handleSetupTrustees = async () => {
    setActiveStep('setup');
    updateStepStatus('setup', STATUS.RUNNING);
    addLog('Starting trustee setup...', 'info');
    
    try {
      addLog('Generating 5 trustees with key shares...', 'info');
      const response = await mockDataAPI.setupTrustees();
      addLog('Trustees created successfully', 'success');
      addLog(`Response: ${JSON.stringify(response.data)}`, 'debug');
      updateStepStatus('setup', STATUS.SUCCESS);
      await loadStats();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message;
      addLog(`Failed to setup trustees: ${errorMsg}`, 'error', err.response?.data);
      updateStepStatus('setup', STATUS.ERROR);
    }
    setActiveStep(null);
  };

  // Step 2: Generate Votes
  const handleGenerateVotes = async (count = 100) => {
    setActiveStep('votes');
    updateStepStatus('votes', STATUS.RUNNING);
    addLog(`Starting vote generation (${count} votes)...`, 'info');
    
    try {
      addLog('Encrypting votes with Paillier homomorphic encryption...', 'info');
      addLog('This may take 15-30 seconds for 100 votes...', 'warning');
      
      const response = await mockDataAPI.generateVotes(count);
      addLog(`Generated ${count} encrypted votes`, 'success');
      addLog(`Response: ${JSON.stringify(response.data)}`, 'debug');
      updateStepStatus('votes', STATUS.SUCCESS);
      updateStepStatus('ballots', STATUS.SUCCESS);
      await loadStats();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message;
      addLog(`Failed to generate votes: ${errorMsg}`, 'error', err.response?.data);
      updateStepStatus('votes', STATUS.ERROR);
    }
    setActiveStep(null);
  };

  // Step 3: Start Tallying
  const handleStartTallying = async () => {
    if (!stats?.election?.id) {
      addLog('No election found. Please generate votes first.', 'error');
      return;
    }

    setActiveStep('tally');
    updateStepStatus('tally', STATUS.RUNNING);
    addLog('Starting tallying process...', 'info');
    
    try {
      addLog('Aggregating encrypted votes homomorphically...', 'info');
      const response = await tallyingAPI.start(stats.election.id);
      addLog('Tallying session created', 'success');
      addLog(`Session ready for trustee decryption`, 'info');
      addLog(`Response: ${JSON.stringify(response.data)}`, 'debug');
      updateStepStatus('tally', STATUS.SUCCESS);
      await loadStats();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message;
      addLog(`Failed to start tallying: ${errorMsg}`, 'error', err.response?.data);
      updateStepStatus('tally', STATUS.ERROR);
    }
    setActiveStep(null);
  };

  // Step 4: Finalize Results
  const handleFinalize = async () => {
    if (!stats?.election?.id) {
      addLog('No election found.', 'error');
      return;
    }

    setActiveStep('finalize');
    updateStepStatus('finalize', STATUS.RUNNING);
    addLog('Finalizing tally and computing results...', 'info');
    
    try {
      addLog('Combining partial decryptions from trustees...', 'info');
      const response = await tallyingAPI.finalize(stats.election.id);
      addLog('Results computed successfully!', 'success');
      addLog(`Response: ${JSON.stringify(response.data)}`, 'debug');
      updateStepStatus('finalize', STATUS.SUCCESS);
      await loadStats();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message;
      addLog(`Failed to finalize: ${errorMsg}`, 'error', err.response?.data);
      updateStepStatus('finalize', STATUS.ERROR);
    }
    setActiveStep(null);
  };

  // Step 5: Publish to Blockchain
  const handlePublishBlockchain = async () => {
    if (!stats?.election?.id) {
      addLog('No election found.', 'error');
      return;
    }

    setActiveStep('blockchain');
    updateStepStatus('blockchain', STATUS.RUNNING);
    addLog('Publishing results to blockchain...', 'info');
    
    try {
      addLog('Creating immutable record on ledger...', 'info');
      const response = await resultsAPI.publishToBlockchain(stats.election.id);
      addLog('Results published to blockchain!', 'success');
      addLog(`Transaction: ${JSON.stringify(response.data)}`, 'debug');
      updateStepStatus('blockchain', STATUS.SUCCESS);
      await loadStats();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message;
      addLog(`Failed to publish: ${errorMsg}`, 'error', err.response?.data);
      updateStepStatus('blockchain', STATUS.ERROR);
    }
    setActiveStep(null);
  };

  // Reset Everything
  const handleReset = async () => {
    if (!window.confirm('This will delete ALL data. Continue?')) return;
    
    addLog('Resetting database...', 'warning');
    try {
      await mockDataAPI.resetDatabase();
      addLog('Database reset complete', 'success');
      setStepStatuses({
        setup: STATUS.PENDING,
        votes: STATUS.PENDING,
        ballots: STATUS.PENDING,
        tally: STATUS.PENDING,
        trustees: STATUS.PENDING,
        finalize: STATUS.PENDING,
        blockchain: STATUS.PENDING
      });
      await loadStats();
    } catch (err) {
      addLog(`Reset failed: ${err.message}`, 'error');
    }
  };

  // Run Full Workflow
  const handleRunAll = async () => {
    addLog('═══ Starting Full Workflow ═══', 'info');
    
    await handleSetupTrustees();
    await new Promise(r => setTimeout(r, 500));
    
    await handleGenerateVotes(100);
    await new Promise(r => setTimeout(r, 500));
    
    await handleStartTallying();
    await new Promise(r => setTimeout(r, 500));
    
    addLog('⚠️ Manual Step Required: Go to Trustees tab and decrypt with 3 trustees', 'warning');
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case STATUS.SUCCESS: return '✅';
      case STATUS.ERROR: return '❌';
      case STATUS.RUNNING: return '⏳';
      case STATUS.SKIPPED: return '⏭️';
      default: return '○';
    }
  };

  const getStatusClass = (status) => {
    switch (status) {
      case STATUS.SUCCESS: return 'step-success';
      case STATUS.ERROR: return 'step-error';
      case STATUS.RUNNING: return 'step-running';
      default: return 'step-pending';
    }
  };

  if (authRole && authRole !== 'admin') {
    return (
      <div className="testing-panel-v2">
        <div className="section-card">
          <h3>Restricted Access</h3>
          <p>Workflow testing tools are available to administrators only.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="testing-panel-v2">
      {/* Header */}
      <div className="panel-header">
        <div className="header-content">
          <h2>🧪 Workflow Testing Console</h2>
          <p>Execute and monitor the privacy-preserving tallying workflow</p>
        </div>
        <div className="header-actions">
          <button className="btn-icon" onClick={loadStats} title="Refresh Status">
            🔄
          </button>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="panel-grid">
        {/* Left: Workflow Steps */}
        <div className="workflow-column">
          <div className="section-card">
            <h3>📋 Workflow Steps</h3>
            
            <div className="workflow-steps">
              {/* Step 1 */}
              <div className={`workflow-step ${getStatusClass(stepStatuses.setup)}`}>
                <div className="step-indicator">
                  <span className="step-icon">{getStatusIcon(stepStatuses.setup)}</span>
                  <span className="step-number">1</span>
                </div>
                <div className="step-content">
                  <h4>Setup Trustees</h4>
                  <p>Create 5 trustees with Shamir secret shares</p>
                  <button 
                    className="btn btn-primary"
                    onClick={handleSetupTrustees}
                    disabled={activeStep !== null}
                  >
                    {activeStep === 'setup' ? 'Running...' : 'Execute'}
                  </button>
                </div>
              </div>

              {/* Step 2 */}
              <div className={`workflow-step ${getStatusClass(stepStatuses.votes)}`}>
                <div className="step-indicator">
                  <span className="step-icon">{getStatusIcon(stepStatuses.votes)}</span>
                  <span className="step-number">2</span>
                </div>
                <div className="step-content">
                  <h4>Generate Encrypted Votes</h4>
                  <p>Create 100 mock votes with Paillier encryption</p>
                  <button 
                    className="btn btn-primary"
                    onClick={() => handleGenerateVotes(100)}
                    disabled={activeStep !== null}
                  >
                    {activeStep === 'votes' ? 'Encrypting...' : 'Execute'}
                  </button>
                </div>
              </div>

              {/* Step 3 */}
              <div className={`workflow-step ${getStatusClass(stepStatuses.tally)}`}>
                <div className="step-indicator">
                  <span className="step-icon">{getStatusIcon(stepStatuses.tally)}</span>
                  <span className="step-number">3</span>
                </div>
                <div className="step-content">
                  <h4>Start Tallying</h4>
                  <p>Aggregate votes homomorphically</p>
                  <button 
                    className="btn btn-primary"
                    onClick={handleStartTallying}
                    disabled={activeStep !== null || stepStatuses.votes !== STATUS.SUCCESS}
                  >
                    {activeStep === 'tally' ? 'Running...' : 'Execute'}
                  </button>
                </div>
              </div>

              {/* Step 4 - Manual */}
              <div className={`workflow-step ${getStatusClass(stepStatuses.trustees)}`}>
                <div className="step-indicator">
                  <span className="step-icon">{getStatusIcon(stepStatuses.trustees)}</span>
                  <span className="step-number">4</span>
                </div>
                <div className="step-content">
                  <h4>Trustee Decryption</h4>
                  <p>Go to Trustees tab → Click Decrypt on 3 trustees</p>
                  <div className="progress-indicator">
                    <span className="progress-text">
                      {stats?.tallying?.trustees_completed || 0}/3 completed
                    </span>
                    <div className="progress-bar">
                      <div 
                        className="progress-fill" 
                        style={{ width: `${((stats?.tallying?.trustees_completed || 0) / 3) * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Step 5 */}
              <div className={`workflow-step ${getStatusClass(stepStatuses.finalize)}`}>
                <div className="step-indicator">
                  <span className="step-icon">{getStatusIcon(stepStatuses.finalize)}</span>
                  <span className="step-number">5</span>
                </div>
                <div className="step-content">
                  <h4>Finalize Results</h4>
                  <p>Combine decryptions and compute final tally</p>
                  <button 
                    className="btn btn-success"
                    onClick={handleFinalize}
                    disabled={activeStep !== null || (stats?.tallying?.trustees_completed || 0) < 3}
                  >
                    {activeStep === 'finalize' ? 'Computing...' : 'Execute'}
                  </button>
                </div>
              </div>

              {/* Step 6 */}
              <div className={`workflow-step ${getStatusClass(stepStatuses.blockchain)}`}>
                <div className="step-indicator">
                  <span className="step-icon">{getStatusIcon(stepStatuses.blockchain)}</span>
                  <span className="step-number">6</span>
                </div>
                <div className="step-content">
                  <h4>Publish to Blockchain</h4>
                  <p>Create immutable record on ledger</p>
                  <button 
                    className="btn btn-secondary"
                    onClick={handlePublishBlockchain}
                    disabled={activeStep !== null || stepStatuses.finalize !== STATUS.SUCCESS}
                  >
                    {activeStep === 'blockchain' ? 'Publishing...' : 'Execute'}
                  </button>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="quick-actions">
              <button 
                className="btn btn-outline"
                onClick={handleRunAll}
                disabled={activeStep !== null}
              >
                ▶️ Run Steps 1-3 Automatically
              </button>
            </div>
          </div>
        </div>

        {/* Right: Status & Console */}
        <div className="status-column">
          {/* Current Status */}
          <div className="section-card status-card">
            <h3>📊 Current Status</h3>
            {stats ? (
              <div className="status-grid">
                <div className="status-item">
                  <span className="status-label">Election</span>
                  <span className="status-value">{stats.election?.title || 'None'}</span>
                </div>
                <div className="status-item">
                  <span className="status-label">Status</span>
                  <span className={`status-badge status-${stats.election?.status || 'pending'}`}>
                    {stats.election?.status || 'Pending'}
                  </span>
                </div>
                <div className="status-item">
                  <span className="status-label">Total Votes</span>
                  <span className="status-value">{stats.votes?.total || 0}</span>
                </div>
                <div className="status-item">
                  <span className="status-label">Tallied</span>
                  <span className="status-value">{stats.votes?.tallied || 0}</span>
                </div>
                <div className="status-item">
                  <span className="status-label">Trustees Done</span>
                  <span className="status-value">
                    {stats.tallying?.trustees_completed || 0}/{stats.tallying?.required_trustees || 3}
                  </span>
                </div>
                <div className="status-item">
                  <span className="status-label">Tally Status</span>
                  <span className="status-value">{stats.tallying?.status || 'Not started'}</span>
                </div>
              </div>
            ) : (
              <div className="loading-placeholder">Loading...</div>
            )}
          </div>

          {/* Console/Log */}
          <div className="section-card console-card">
            <div className="console-header">
              <h3>🖥️ Execution Log</h3>
              <div className="console-actions">
                <button 
                  className="btn-icon" 
                  onClick={() => setExpandedLogs(!expandedLogs)}
                  title={expandedLogs ? 'Collapse' : 'Expand'}
                >
                  {expandedLogs ? '▼' : '▶'}
                </button>
                <button className="btn-icon" onClick={clearLogs} title="Clear">
                  🗑️
                </button>
              </div>
            </div>
            
            {expandedLogs && (
              <div className="console-container" ref={logContainerRef}>
                {logs.length === 0 ? (
                  <div className="console-empty">
                    <span>No logs yet. Execute a step to see output.</span>
                  </div>
                ) : (
                  logs.map(log => (
                    <div key={log.id} className={`log-entry log-${log.type}`}>
                      <span className="log-time">{log.timestamp}</span>
                      <span className="log-message">{log.message}</span>
                      {log.details && (
                        <details className="log-details">
                          <summary>Details</summary>
                          <pre>{JSON.stringify(log.details, null, 2)}</pre>
                        </details>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Danger Zone */}
          <div className="section-card danger-card">
            <h3>⚠️ Danger Zone</h3>
            <p>This will delete all data and reset the system</p>
            <button 
              className="btn btn-danger"
              onClick={handleReset}
              disabled={activeStep !== null}
            >
              🗑️ Reset Database
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TestingPanel;
