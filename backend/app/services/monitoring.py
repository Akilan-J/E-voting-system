
import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

class LoggingService:
    """
    Centralized logging service for the election system (US-67).
    Provides structured logging and severity levels.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("evoting_ops")
        self.logger.setLevel(logging.INFO)
        
        # Console handler with JSON formatting
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        self.state_file = Path(__file__).resolve().parents[2] / "data" / "monitoring_chain.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True) # Ensure dir exists

        self.last_hash = self._load_last_hash()
    
    def _load_last_hash(self) -> str:
        if self.state_file.exists():
            try:
                import json
                data = json.loads(self.state_file.read_text())
                return data.get("last_hash", "GENESIS_HASH")
            except Exception:
                pass
        return "GENESIS_HASH"

    def _save_last_hash(self, current_hash: str):
        try:
            import json
            self.state_file.write_text(json.dumps({"last_hash": current_hash}))
        except Exception as e:
            # Fallback but don't crash
            pass

    def log_event(
        self, 
        event_type: str, 
        severity: str, 
        details: Dict[str, Any], 
        user_id: Optional[str] = None
    ):
        """
        Log a structured system event.
        """
        # US-67: Hash Chaining for Tamper Evidence
        import hashlib
        
        # In a real app, strict ordering requires database/blockchain, 
        # but for this file-based logger we chain locally.
        payload = json.dumps(details, sort_keys=True)
        prev_hash = self.last_hash
        chain_input = f"{prev_hash}|{severity}|{event_type}|{payload}"
        current_hash = hashlib.sha256(chain_input.encode()).hexdigest()
        
        # Persist state
        self.last_hash = current_hash
        self._save_last_hash(current_hash)

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "severity": severity.upper(),  # INFO, WARNING, ERROR, CRITICAL
            "user_id": user_id,
            "details": details,
            "trace_hash": current_hash,
            "prev_hash": prev_hash # Points to previous state
        }
        
        # In a real system, you might send this to ELK/Splunk
        self.logger.info(json.dumps(log_entry))

# Global instance
logging_service = LoggingService()
