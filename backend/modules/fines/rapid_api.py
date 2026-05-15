import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class RapidAPIChallanProvider:
    """
    Integration with RapidAPI for live RTO/Challan data.
    Uses 'RTO Vehicle Information' or similar APIs available on RapidAPI.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://rto-vehicle-information-verification-india.p.rapidapi.com"
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": "rto-vehicle-information-verification-india.p.rapidapi.com",
            "Content-Type": "application/json"
        }

    def get_challans(self, vehicle_number: str) -> Dict[str, Any]:
        """
        Fetch pending challans for a given vehicle registration number.
        """
        # Note: Endpoint and payload structure depend on the specific RapidAPI provider chosen.
        # This implementation assumes a common structure for RTO/Challan APIs.
        endpoint = f"{self.base_url}/api/v1/challan"
        payload = {"reg_no": vehicle_number}
        
        try:
            response = requests.post(endpoint, json=payload, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    return {
                        "status": "success",
                        "challans": data.get("result", {}).get("challans", []),
                        "vehicle_details": data.get("result", {}).get("vehicle_details", {})
                    }
                return {"status": "error", "message": data.get("message", "API returned failure status")}
            elif response.status_code == 401:
                return {"status": "error", "message": "Invalid RapidAPI Key"}
            elif response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "unknown")
                return {"status": "error", "message": f"RapidAPI rate limit hit — retry after {retry_after}s. Upgrade plan if quota is exhausted."}
            elif response.status_code >= 500:
                return {"status": "provider_down", "message": "RapidAPI provider is temporarily unavailable (5xx). Try again shortly."}
            else:
                return {"status": "error", "message": f"API Error: {response.status_code}"}
        except requests.exceptions.Timeout:
            return {"status": "error", "message": "RapidAPI Request Timed Out"}
        except Exception as e:
            logger.error(f"RapidAPI request failed: {e}")
            return {"status": "error", "message": str(e)}
