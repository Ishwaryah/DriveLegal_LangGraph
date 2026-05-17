import os
import json
import math

# Get absolute path to backend directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EMERGENCY_CONTACTS_PATH = os.path.join(BASE_DIR, "data", "drivelegal_dataset", "json", "emergency_contacts_statewise.json")
GOOD_SAMARITAN_GUIDE_PATH = os.path.join(BASE_DIR, "data", "drivelegal_dataset", "json", "good_samaritan_guide.json")
TRAUMA_CENTERS_PATH = os.path.join(BASE_DIR, "data", "zones", "ALL", "india_trauma_centers.geojson")


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth's surface
    using the Haversine formula. Returns distance in kilometers.
    """
    R = 6371.0  # Earth's radius in kilometers

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class EmergencyService:
    def get_nearest_trauma_center(self, lat: float, lng: float, max_results: int = 3) -> list[dict]:
        """
        Uses the Haversine formula to find the nearest government trauma centers
        from the india_trauma_centers.geojson file.
        """
        if not os.path.exists(TRAUMA_CENTERS_PATH):
            return []

        with open(TRAUMA_CENTERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        results = []
        for feature in data.get("features", []):
            coords = feature["geometry"]["coordinates"]
            # GeoJSON coordinates order: [longitude, latitude]
            h_lng, h_lat = coords[0], coords[1]
            
            dist = haversine_distance(lat, lng, h_lat, h_lng)
            
            item = dict(feature["properties"])
            item["latitude"] = h_lat
            item["longitude"] = h_lng
            item["distance_km"] = round(dist, 2)
            results.append(item)

        # Sort by distance ascending
        results.sort(key=lambda x: x["distance_km"])
        return results[:max_results]

    def get_state_emergency_contacts(self, state_code: str) -> dict:
        """
        Returns the full emergency contacts and protection details block for a given state
        from emergency_contacts_statewise.json.
        """
        state_code = state_code.upper().strip()
        if not os.path.exists(EMERGENCY_CONTACTS_PATH):
            return {}

        with open(EMERGENCY_CONTACTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data.get("states", {}).get(state_code, {})

    def get_good_samaritan_rights(self, language: str = "en") -> dict:
        """
        Returns Good Samaritan rights and steps to help from good_samaritan_guide.json.
        Supports "hi" for Hindi translations of key rights and steps.
        """
        if not os.path.exists(GOOD_SAMARITAN_GUIDE_PATH):
            return {}

        with open(GOOD_SAMARITAN_GUIDE_PATH, "r", encoding="utf-8") as f:
            guide = json.load(f)

        if language.lower() == "hi":
            # Provide Hindi translations for rights and steps
            guide["rights_of_good_samaritan"] = [
                "पुलिस या अस्पताल अधिकारियों द्वारा रोका नहीं जा सकता।",
                "व्यक्तिगत पहचान या संपर्क विवरण प्रकट करने के लिए बाध्य नहीं किया जा सकता।",
                "गवाह बनने के लिए मजबूर नहीं किया जा सकता; गवाही पूरी तरह से स्वैच्छिक है।",
                "सद्भाव में मदद करने के लिए किसी भी नागरिक या आपराधिक कार्रवाई के लिए उत्तरदायी नहीं ठहराया जा सकता।",
                "पीड़ित के किसी भी चिकित्सा व्यय या उपचार लागत के लिए उत्तरदायी नहीं बनाया जा सकता।",
                "अनुरोध पर अस्पताल से एक मानक पावती (एक्नॉलेजमेंट) प्राप्त करने का हकदार।",
                "MoRTH योजना के तहत 5000 रुपये के नकद पुरस्कार और प्रशंसा पत्र के लिए पात्र।",
                "पुलिस पूछताछ (यदि गवाह का विकल्प चुना जाता है) एक ही बार, सुविधा के अनुसार (जैसे, घर या कार्यालय) और सादे कपड़ों में होनी चाहिए।"
            ]
            guide["steps_to_help"] = [
                {
                    "step": 1,
                    "action": "दृश्य सुरक्षा सुनिश्चित करें — आग, गैस रिसाव, आने वाले ट्रैफ़िक की जाँच करें और वाहन की हैज़र्ड लाइट चालू करें।",
                    "time_critical": False
                },
                {
                    "step": 2,
                    "action": "तुरंत 112 (राष्ट्रीय आपातकाल) या 108 (एम्बुलेंस) पर कॉल करें।",
                    "time_critical": True,
                    "note": "गोल्डन ऑवर — ऑक्सीजन के बिना 4 मिनट के बाद मस्तिष्क क्षति शुरू हो जाती है।"
                },
                {
                    "step": 3,
                    "action": "प्रतिक्रिया और सांस लेने की जाँच करें — कंधों को थपथपाएं और पूछें कि क्या वे ठीक हैं, छाती के उतार-चढ़ाव की जाँच करें।",
                    "time_critical": True
                },
                {
                    "step": 4,
                    "action": "दिखाई देने वाले रक्तस्राव को नियंत्रित करें — साफ कपड़े या पट्टी का उपयोग करके सीधा दबाव डालें।",
                    "time_critical": True
                },
                {
                    "step": 5,
                    "action": "पीड़ित को स्थिर और आरामदायक रखें — जब तक तत्काल खतरा न हो, उन्हें न हिलाएं।",
                    "time_critical": False
                },
                {
                    "step": 6,
                    "action": "परिवहन में सहायता करें या मदद की प्रतीक्षा करें — यदि एम्बुलेंस में देरी हो रही है, तो निकटतम स्तर 1/2 ट्रॉमा सेंटर में साथ जाएं।",
                    "time_critical": False
                }
            ]
        return guide

    def handle_accident_report(self, lat: float, lng: float) -> dict:
        """
        Combines the nearest trauma centers, state helplines, good samaritan guide, and
        nearest RTO into a single response object for the accident response flow.
        """
        # 1. Get 3 nearest trauma centers
        nearest_centers = self.get_nearest_trauma_center(lat, lng, max_results=3)

        # 2. Determine state code from the absolute closest trauma center, falling back to DL
        state_code = "DL"
        if nearest_centers:
            state_code = nearest_centers[0].get("state", "DL")

        # 3. Load contacts for that state
        state_contacts = self.get_state_emergency_contacts(state_code)

        # 4. Find the nearest RTO within that state
        rto_offices = state_contacts.get("rto_offices", [])
        nearest_rto = None
        min_rto_dist = float("inf")

        for rto in rto_offices:
            r_lat = rto.get("lat")
            r_lng = rto.get("lng")
            if r_lat is not None and r_lng is not None:
                dist = haversine_distance(lat, lng, r_lat, r_lng)
                if dist < min_rto_dist:
                    min_rto_dist = dist
                    nearest_rto = dict(rto)
                    nearest_rto["distance_km"] = round(dist, 2)

        # Fallback: scan all states for nearest RTO if none found in determined state
        if not nearest_rto:
            if os.path.exists(EMERGENCY_CONTACTS_PATH):
                with open(EMERGENCY_CONTACTS_PATH, "r", encoding="utf-8") as f:
                    all_data = json.load(f)
                for s_code, s_data in all_data.get("states", {}).items():
                    for rto in s_data.get("rto_offices", []):
                        r_lat = rto.get("lat")
                        r_lng = rto.get("lng")
                        if r_lat is not None and r_lng is not None:
                            dist = haversine_distance(lat, lng, r_lat, r_lng)
                            if dist < min_rto_dist:
                                min_rto_dist = dist
                                nearest_rto = dict(rto)
                                nearest_rto["state"] = s_code
                                nearest_rto["distance_km"] = round(dist, 2)

        # 5. Load Good Samaritan guide
        good_samaritan = self.get_good_samaritan_rights(language="en")

        # Clean lists from state_contacts to avoid bloated/duplicate responses
        clean_state_contacts = dict(state_contacts)
        if "rto_offices" in clean_state_contacts:
            del clean_state_contacts["rto_offices"]
        if "trauma_centers" in clean_state_contacts:
            del clean_state_contacts["trauma_centers"]

        return {
            "latitude": lat,
            "longitude": lng,
            "resolved_state": state_code,
            "nearest_trauma_centers": nearest_centers,
            "state_contacts": clean_state_contacts,
            "nearest_rto": nearest_rto,
            "good_samaritan_guide": good_samaritan
        }
