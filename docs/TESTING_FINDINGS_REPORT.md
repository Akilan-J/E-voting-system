# E-Voting System - Testing Findings & Resolutions Report

COMMAND:
PYTHONPATH=backend pytest backend/tests/test_all_implemented_features.py -v

EXPECTED OUTPUT:
============================= test session starts ==============================
platform darwin -- Python 3.12.0, pytest-7.4.4, pluggy-1.6.0 -- /Library/Frameworks/Python.framework/Versions/3.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/akilan/Documents/E-voting-system
configfile: pytest.ini
plugins: anyio-4.12.1, asyncio-0.23.3, cov-4.1.0, web3-6.15.1
asyncio: mode=Mode.STRICT
collecting ... collected 41 items

backend/tests/test_all_implemented_features.py::TestEpic1Authentication::test_us1_voter_login_with_valid_credential PASSED [  2%]
backend/tests/test_all_implemented_features.py::TestEpic1Authentication::test_login_with_invalid_credential PASSED [  4%]
backend/tests/test_all_implemented_features.py::TestEpic1Authentication::test_admin_login PASSED [  7%]
backend/tests/test_all_implemented_features.py::TestEpic1Authentication::test_trustee_login PASSED [  9%]
backend/tests/test_all_implemented_features.py::TestEpic1Authentication::test_auditor_login PASSED [ 12%]
backend/tests/test_all_implemented_features.py::TestEpic1Authentication::test_security_engineer_login PASSED [ 14%]
backend/tests/test_all_implemented_features.py::TestEpic2BallotSubmission::test_mock_votes_generation PASSED [ 17%]
backend/tests/test_all_implemented_features.py::TestEpic3Ledger::test_ledger_blocks_listing PASSED [ 19%]
backend/tests/test_all_implemented_features.py::TestEpic3Ledger::test_ledger_chain_verification PASSED [ 21%]
backend/tests/test_all_implemented_features.py::TestEpic4APIEndpoints::test_get_trustees PASSED [ 24%]
backend/tests/test_all_implemented_features.py::TestEpic4APIEndpoints::test_start_tallying PASSED [ 26%]
backend/tests/test_all_implemented_features.py::TestEpic4Encryption::test_keypair_generation PASSED [ 29%]
backend/tests/test_all_implemented_features.py::TestEpic4Encryption::test_encrypt_decrypt_roundtrip PASSED [ 31%]
backend/tests/test_all_implemented_features.py::TestEpic4Encryption::test_public_key_loading PASSED [ 34%]
backend/tests/test_all_implemented_features.py::TestEpic4Encryption::test_private_key_loading PASSED [ 36%]
backend/tests/test_all_implemented_features.py::TestEpic4ThresholdCrypto::test_threshold_configuration PASSED [ 39%]
backend/tests/test_all_implemented_features.py::TestEpic4ThresholdCrypto::test_secret_splitting PASSED [ 41%]
backend/tests/test_all_implemented_features.py::TestEpic4ThresholdCrypto::test_share_indices_are_unique PASSED [ 43%]
backend/tests/test_all_implemented_features.py::TestEpic4ThresholdCrypto::test_minimum_shares_required PASSED [ 46%]
backend/tests/test_all_implemented_features.py::TestEpic4VoteAggregation::test_aggregate_empty_list_raises_error PASSED [ 48%]
backend/tests/test_all_implemented_features.py::TestEpic4VoteAggregation::test_aggregate_single_vote PASSED [ 51%]
backend/tests/test_all_implemented_features.py::TestEpic4TallyingService::test_service_initialization PASSED [ 53%]
backend/tests/test_all_implemented_features.py::TestEpic4ErrorHandling::test_decrypt_without_private_key_raises_error PASSED [ 56%]
backend/tests/test_all_implemented_features.py::TestEpic4ErrorHandling::test_partial_decrypt_without_key_raises_error PASSED [ 58%]
backend/tests/test_all_implemented_features.py::TestEpic4ErrorHandling::test_invalid_candidate_id_handled PASSED [ 60%]
backend/tests/test_all_implemented_features.py::TestEpic4KeyConsistency::test_same_key_used_for_encrypt_decrypt PASSED [ 63%]
backend/tests/test_all_implemented_features.py::TestEpic4KeyConsistency::test_full_encryption_workflow PASSED [ 65%]
backend/tests/test_all_implemented_features.py::TestEpic4KeyConsistency::test_key_mismatch_scenario PASSED [ 68%]
backend/tests/test_all_implemented_features.py::TestEpic4KeyConsistency::test_multiple_vote_encryption PASSED [ 70%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us62_receipt_verification PASSED [ 73%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us63_zk_proof_verification PASSED [ 75%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us64_ledger_replay_audit PASSED [ 78%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us65_transparency_dashboard PASSED [ 80%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us66_evidence_download PASSED [ 82%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us68_threat_simulation PASSED [ 85%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us69_anomaly_detection PASSED [ 87%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us70_incident_workflow PASSED [ 90%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us71_dispute_workflow PASSED [ 92%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us72_compliance_report PASSED [ 95%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us74_replay_timeline PASSED [ 97%]
backend/tests/test_all_implemented_features.py::TestIntegration::test_full_election_workflow PASSED [100%]

============================= 41 passed in 24.88s ==============================

---

ERRORS FOUND:
akilan@Akilans-MacBook-Air E-voting-system %  PYTHONPATH=backend pytest backend/tests/test_all_implemented_f
eatures.py -v
=========================================== test session starts ============================================
platform darwin -- Python 3.12.0, pytest-7.4.4, pluggy-1.6.0 -- /Library/Frameworks/Python.framework/Versions/3.12/bin/python3
cachedir: .pytest_cache
rootdir: /Users/akilan/Documents/E-voting-system
configfile: pytest.ini
plugins: anyio-4.12.1, asyncio-0.23.3, cov-4.1.0, web3-6.15.1
asyncio: mode=Mode.STRICT
collected 23 items                                                                                         

backend/tests/test_all_implemented_features.py::TestEpic1Authentication::test_us1_voter_login_with_valid_credential FAILED [  4%]
backend/tests/test_all_implemented_features.py::TestEpic1Authentication::test_login_with_invalid_credential PASSED [  8%]
backend/tests/test_all_implemented_features.py::TestEpic1Authentication::test_admin_login PASSED     [ 13%]
backend/tests/test_all_implemented_features.py::TestEpic1Authentication::test_trustee_login PASSED   [ 17%]
backend/tests/test_all_implemented_features.py::TestEpic1Authentication::test_auditor_login PASSED   [ 21%]
backend/tests/test_all_implemented_features.py::TestEpic1Authentication::test_security_engineer_login PASSED [ 26%]
backend/tests/test_all_implemented_features.py::TestEpic2BallotSubmission::test_mock_votes_generation PASSED [ 30%]
backend/tests/test_all_implemented_features.py::TestEpic3Ledger::test_ledger_blocks_listing PASSED   [ 34%]
backend/tests/test_all_implemented_features.py::TestEpic3Ledger::test_ledger_chain_verification PASSED [ 39%]
backend/tests/test_all_implemented_features.py::TestEpic4Tallying::test_get_trustees FAILED          [ 43%]
backend/tests/test_all_implemented_features.py::TestEpic4Tallying::test_start_tallying PASSED        [ 47%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us62_receipt_verification PASSED [ 52%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us63_zk_proof_verification PASSED [ 56%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us64_ledger_replay_audit PASSED [ 60%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us65_transparency_dashboard PASSED [ 65%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us66_evidence_download PASSED [ 69%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us68_threat_simulation PASSED [ 73%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us69_anomaly_detection PASSED [ 78%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us70_incident_workflow PASSED [ 82%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us71_dispute_workflow PASSED [ 86%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us72_compliance_report PASSED [ 91%]
backend/tests/test_all_implemented_features.py::TestEpic5Verification::test_us74_replay_timeline PASSED [ 95%]
backend/tests/test_all_implemented_features.py::TestIntegration::test_full_election_workflow FAILED  [100%]



