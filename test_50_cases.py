"""
DriveLegal AI Agent - 50 Test Cases Runner
Sends each question to /query endpoint and captures structured results.
"""

import json
import requests
import time

BASE_URL = "http://localhost:8001"

TEST_CASES = [
    # Category 1: Basic Fine Lookups (India)
    {"id": 1, "cat": "Basic Fine Lookups (India)", "q": "What is the fine for driving without a helmet in Tamil Nadu?"},
    {"id": 2, "cat": "Basic Fine Lookups (India)", "q": "Fine for not wearing a seatbelt in Delhi for a car."},
    {"id": 3, "cat": "Basic Fine Lookups (India)", "q": "How much do I pay for overspeeding a car in Maharashtra?"},
    {"id": 4, "cat": "Basic Fine Lookups (India)", "q": "What is the penalty for jumping a red light in Karnataka?"},
    {"id": 5, "cat": "Basic Fine Lookups (India)", "q": "Fine for driving without insurance in Uttar Pradesh."},
    {"id": 6, "cat": "Basic Fine Lookups (India)", "q": "What is the challan for no PUC (pollution certificate) in Kerala?"},
    {"id": 7, "cat": "Basic Fine Lookups (India)", "q": "Fine for triple riding on a bike in Andhra Pradesh."},
    {"id": 8, "cat": "Basic Fine Lookups (India)", "q": "Penalty for using a mobile phone while driving in Telangana."},
    {"id": 9, "cat": "Basic Fine Lookups (India)", "q": "How much is the fine for drunk driving in West Bengal?"},
    {"id": 10, "cat": "Basic Fine Lookups (India)", "q": "Fine for wrong-way driving in Gujarat for a truck."},

    # Category 2: Repeat Offences & Edge Cases
    {"id": 11, "cat": "Repeat Offences & Edge Cases", "q": "What is the fine for a second offense of drunk driving in TN?"},
    {"id": 12, "cat": "Repeat Offences & Edge Cases", "q": "Fine for not wearing a helmet. What if it is my 3rd time?"},
    {"id": 13, "cat": "Repeat Offences & Edge Cases", "q": "Is the fine for no seatbelt different for a second time?"},
    {"id": 14, "cat": "Repeat Offences & Edge Cases", "q": "Overspeeding fine for a commercial truck vs a private car."},
    {"id": 15, "cat": "Repeat Offences & Edge Cases", "q": "What if a minor is caught driving without a license?"},
    {"id": 16, "cat": "Repeat Offences & Edge Cases", "q": "Fine for driving without a license plate."},

    # Category 3: International Traffic Fines
    {"id": 17, "cat": "International Traffic Fines", "q": "What is the fine for running a red light in Dubai UAE?"},
    {"id": 18, "cat": "International Traffic Fines", "q": "Fine for speeding in Abu Dhabi."},
    {"id": 19, "cat": "International Traffic Fines", "q": "How much is the penalty for texting and driving in the UK?"},
    {"id": 20, "cat": "International Traffic Fines", "q": "Fine for driving without insurance in California USA."},
    {"id": 21, "cat": "International Traffic Fines", "q": "What is the demerit point penalty for speeding in Singapore?"},
    {"id": 22, "cat": "International Traffic Fines", "q": "Fine for parking in a disabled spot in Saudi Arabia."},
    {"id": 23, "cat": "International Traffic Fines", "q": "Penalty for driving under the influence in New York."},
    {"id": 24, "cat": "International Traffic Fines", "q": "Fine for not wearing a seatbelt in London UK."},

    # Category 4: Rule Explanations & Legal Sections
    {"id": 25, "cat": "Rule Explanations & Legal Sections", "q": "Under what section of the Motor Vehicles Act is drunk driving penalized?"},
    {"id": 26, "cat": "Rule Explanations & Legal Sections", "q": "Explain Section 194D of the Motor Vehicles Act."},
    {"id": 27, "cat": "Rule Explanations & Legal Sections", "q": "What are the rules for tinted windows on cars?"},
    {"id": 28, "cat": "Rule Explanations & Legal Sections", "q": "Is it legal to modify the exhaust of my motorcycle?"},
    {"id": 29, "cat": "Rule Explanations & Legal Sections", "q": "What are the rules regarding high-beam headlights in city limits?"},
    {"id": 30, "cat": "Rule Explanations & Legal Sections", "q": "Does a pillion rider need to wear a helmet by law?"},
    {"id": 31, "cat": "Rule Explanations & Legal Sections", "q": "What is the legal blood alcohol limit for driving in India?"},
    {"id": 32, "cat": "Rule Explanations & Legal Sections", "q": "Are physical documents required, or is DigiLocker valid?"},

    # Category 5: Geofencing & Location-Based Queries
    {"id": 33, "cat": "Geofencing & Location-Based", "q": "I am at 13.01, 80.23. What are the traffic rules here?", "gps": {"lat": 13.01, "lon": 80.23}},
    {"id": 34, "cat": "Geofencing & Location-Based", "q": "Am I currently in a school zone?", "gps": {"lat": 13.01, "lon": 80.23}},
    {"id": 35, "cat": "Geofencing & Location-Based", "q": "What is the speed limit in a hospital zone?"},
    {"id": 36, "cat": "Geofencing & Location-Based", "q": "Are there any fine multipliers for violations inside a school zone?"},
    {"id": 37, "cat": "Geofencing & Location-Based", "q": "Can I honk in a hospital zone?"},

    # Category 6: Challan Calculation & Management
    {"id": 38, "cat": "Challan Calculation & Management", "q": "Can you check pending challans for vehicle TN01AB1234?"},
    {"id": 39, "cat": "Challan Calculation & Management", "q": "How do I pay my traffic fine online?"},
    {"id": 40, "cat": "Challan Calculation & Management", "q": "What happens if I don't pay my e-challan?"},
    {"id": 41, "cat": "Challan Calculation & Management", "q": "Can my license be suspended for unpaid fines?"},
    {"id": 42, "cat": "Challan Calculation & Management", "q": "How many points until my driving license is revoked in the UAE?"},

    # Category 7: Conversational & Multi-Turn Context
    {"id": 43, "cat": "Conversational & Multi-Turn", "q": "What is the fine for no helmet?"},
    {"id": 44, "cat": "Conversational & Multi-Turn", "q": "What about in Delhi?"},
    {"id": 45, "cat": "Conversational & Multi-Turn", "q": "And for a car? (Note: helmets apply to bikes, not cars)"},
    {"id": 46, "cat": "Conversational & Multi-Turn", "q": "Hi there! How can you help me today?"},
    {"id": 47, "cat": "Conversational & Multi-Turn", "q": "Thanks for the information!"},

    # Category 8: Irrelevant & Out-of-Scope Queries
    {"id": 48, "cat": "Out-of-Scope / Safety Fallback", "q": "Give me a recipe for chocolate cake."},
    {"id": 49, "cat": "Out-of-Scope / Safety Fallback", "q": "Write a Python script to scrape the Parivahan website."},
    {"id": 50, "cat": "Out-of-Scope / Safety Fallback", "q": "What is the capital of France?"},
]


def run_test(tc):
    payload = {
        "text": tc["q"],
        "country": "IN",
        "session": {},
    }
    if tc.get("gps"):
        payload["gps"] = tc["gps"]
    try:
        r = requests.post(f"{BASE_URL}/query", json=payload, timeout=30)
        data = r.json()
        return {
            "id": tc["id"],
            "cat": tc["cat"],
            "question": tc["q"],
            "status": data.get("status", "unknown"),
            "intent": data.get("intent", ""),
            "response": data.get("response", data.get("text", "")),
            "fine": data.get("fine"),
            "rule": data.get("rule"),
            "agent_powered": data.get("agent_powered", False),
            "model": data.get("model", ""),
            "http_status": r.status_code,
            "error": None,
        }
    except Exception as e:
        return {
            "id": tc["id"],
            "cat": tc["cat"],
            "question": tc["q"],
            "status": "error",
            "intent": "",
            "response": "",
            "fine": None,
            "rule": None,
            "agent_powered": False,
            "model": "",
            "http_status": 0,
            "error": str(e),
        }


results = []
print("Running 50 DriveLegal test cases...\n")
for tc in TEST_CASES:
    print(f"  [{tc['id']:02d}] {tc['q'][:70]}...")
    result = run_test(tc)
    results.append(result)
    time.sleep(0.4)   # avoid Groq rate limits

with open("test_results_raw.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\nDone — {len(results)} results saved to test_results_raw.json")
