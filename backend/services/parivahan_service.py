import os
import json
import logging
from datetime import datetime
import difflib
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger("drivelegal.parivahan")

class ParivahanService:
    def __init__(self, config_path: str = None, snapshots_path: str = None):
        self.backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        if config_path is None:
            config_path = os.path.join(self.backend_dir, "data", "drivelegal_dataset", "json", "api_integration_config.json")
        if snapshots_path is None:
            snapshots_path = os.path.join(self.backend_dir, "data", "drivelegal_dataset", "json", "parivahan_snapshots.json")
            
        self.config_path = config_path
        self.snapshots_path = snapshots_path
        self.config = self._load_config()
        self.snapshots = self._load_snapshots()

    def _load_config(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error("Failed to load api_integration_config.json: %s", e)
        return {}

    def _load_snapshots(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.snapshots_path):
                with open(self.snapshots_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error("Failed to load parivahan_snapshots.json: %s", e)
        return {"rc_details": [], "dl_details": [], "echallan_pending": []}

    def _get_mode_and_endpoints(self, service_key: str) -> tuple:
        parivahan_config = self.config.get("parivahan", {})
        service_config = parivahan_config.get(service_key, {})
        mode = service_config.get("mode", "offline")
        live_endpoint = service_config.get("live_endpoint", "")
        return mode, live_endpoint

    def _fuzzy_match(self, query: str, records: list, key_name: str) -> Optional[Dict[str, Any]]:
        if not records or not query:
            return None
            
        def normalize(val):
            return str(val).replace(" ", "").replace("-", "").upper()
            
        norm_query = normalize(query)
        best_match = None
        best_score = -1.0
        
        for r in records:
            val = r.get(key_name, "")
            norm_val = normalize(val)
            score = difflib.SequenceMatcher(None, norm_query, norm_val).ratio()
            if score > best_score:
                best_score = score
                best_match = r
                
        if best_score >= 0.4:
            return best_match
        return None

    def get_rc_details(self, reg_no: str) -> dict:
        mode, live_endpoint = self._get_mode_and_endpoints("rc_verification")
        logger.info("RC details lookup for %s using %s mode", reg_no, mode)
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        if mode == "live":
            api_key = os.getenv("PARIVAHAN_API_KEY") or os.getenv("RAPIDAPI_KEY")
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}" if api_key else "",
                    "x-api-key": api_key or "",
                    "Content-Type": "application/json"
                }
                params = {"reg_no": reg_no}
                r = requests.get(live_endpoint, headers=headers, params=params, timeout=10)
                if r.status_code == 200:
                    return {
                        "success": True,
                        "data": r.json(),
                        "source": "live",
                        "timestamp": timestamp
                    }
                else:
                    return {
                        "success": False,
                        "data": None,
                        "source": "live",
                        "timestamp": timestamp,
                        "error": f"HTTP error {r.status_code}: {r.text}"
                    }
            except Exception as e:
                logger.error("Live RC details request failed: %s", e)
                return {
                    "success": False,
                    "data": None,
                    "source": "live",
                    "timestamp": timestamp,
                    "error": str(e)
                }
        else:
            rc_records = self.snapshots.get("rc_details", [])
            match = self._fuzzy_match(reg_no, rc_records, "reg_no")
            if match:
                return {
                    "success": True,
                    "data": match,
                    "source": "offline",
                    "timestamp": timestamp
                }
            else:
                return {
                    "success": False,
                    "data": None,
                    "source": "offline",
                    "timestamp": timestamp,
                    "error": "No matching vehicle registration found in snapshots"
                }

    def get_dl_details(self, dl_no: str) -> dict:
        mode, live_endpoint = self._get_mode_and_endpoints("dl_verification")
        logger.info("DL details lookup for %s using %s mode", dl_no, mode)
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        if mode == "live":
            api_key = os.getenv("PARIVAHAN_API_KEY") or os.getenv("RAPIDAPI_KEY")
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}" if api_key else "",
                    "x-api-key": api_key or "",
                    "Content-Type": "application/json"
                }
                params = {"dl_no": dl_no}
                r = requests.get(live_endpoint, headers=headers, params=params, timeout=10)
                if r.status_code == 200:
                    return {
                        "success": True,
                        "data": r.json(),
                        "source": "live",
                        "timestamp": timestamp
                    }
                else:
                    return {
                        "success": False,
                        "data": None,
                        "source": "live",
                        "timestamp": timestamp,
                        "error": f"HTTP error {r.status_code}: {r.text}"
                    }
            except Exception as e:
                logger.error("Live DL details request failed: %s", e)
                return {
                    "success": False,
                    "data": None,
                    "source": "live",
                    "timestamp": timestamp,
                    "error": str(e)
                }
        else:
            dl_records = self.snapshots.get("dl_details", [])
            match = self._fuzzy_match(dl_no, dl_records, "dl_no")
            if match:
                return {
                    "success": True,
                    "data": match,
                    "source": "offline",
                    "timestamp": timestamp
                }
            else:
                return {
                    "success": False,
                    "data": None,
                    "source": "offline",
                    "timestamp": timestamp,
                    "error": "No matching driving license found in snapshots"
                }

    def get_pending_challans(self, reg_no: str) -> dict:
        mode, live_endpoint = self._get_mode_and_endpoints("echallan")
        logger.info("Pending challan lookup for %s using %s mode", reg_no, mode)
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        if mode == "live":
            api_key = os.getenv("PARIVAHAN_API_KEY") or os.getenv("RAPIDAPI_KEY")
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}" if api_key else "",
                    "x-api-key": api_key or "",
                    "Content-Type": "application/json"
                }
                params = {"reg_no": reg_no}
                r = requests.get(live_endpoint, headers=headers, params=params, timeout=10)
                if r.status_code == 200:
                    return {
                        "success": True,
                        "data": r.json(),
                        "source": "live",
                        "timestamp": timestamp
                    }
                else:
                    return {
                        "success": False,
                        "data": None,
                        "source": "live",
                        "timestamp": timestamp,
                        "error": f"HTTP error {r.status_code}: {r.text}"
                    }
            except Exception as e:
                logger.error("Live pending challan request failed: %s", e)
                return {
                    "success": False,
                    "data": None,
                    "source": "live",
                    "timestamp": timestamp,
                    "error": str(e)
                }
        else:
            challan_records = self.snapshots.get("echallan_pending", [])
            unique_regs = list(set(r.get("reg_no", "") for r in challan_records if r.get("reg_no")))
            
            def normalize(val):
                return str(val).replace(" ", "").replace("-", "").upper()
                
            norm_query = normalize(reg_no)
            best_reg = None
            best_score = -1.0
            for ureg in unique_regs:
                score = difflib.SequenceMatcher(None, norm_query, normalize(ureg)).ratio()
                if score > best_score:
                    best_score = score
                    best_reg = ureg
                    
            if best_reg and best_score >= 0.4:
                matched_challans = [r for r in challan_records if r.get("reg_no") == best_reg]
                return {
                    "success": True,
                    "data": matched_challans,
                    "source": "offline",
                    "timestamp": timestamp
                }
            else:
                return {
                    "success": True,
                    "data": [],
                    "source": "offline",
                    "timestamp": timestamp
                }
