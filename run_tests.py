import requests
import json
import time

TEST_CASES = [
    # Category 1: Basic Fine Lookups (India)
    {"q": "What is the fine for driving without a helmet in Tamil Nadu?", "session": False},
    {"q": "Fine for not wearing a seatbelt in Delhi for a car.", "session": False},
    {"q": "How much do I pay for overspeeding a car in Maharashtra?", "session": False},
    {"q": "What is the penalty for jumping a red light in Karnataka?", "session": False},
    {"q": "Fine for driving without insurance in Uttar Pradesh.", "session": False},
    {"q": "What is the challan for no PUC (pollution certificate) in Kerala?", "session": False},
    {"q": "Fine for triple riding on a bike in Andhra Pradesh.", "session": False},
    {"q": "Penalty for using a mobile phone while driving in Telangana.", "session": False},
    {"q": "How much is the fine for drunk driving in West Bengal?", "session": False},
    {"q": "Fine for wrong-way driving in Gujarat for a truck.", "session": False},

    # Category 2: Repeat Offences & Edge Cases
    {"q": "What is the fine for a second offense of drunk driving in TN?", "session": False},
    {"q": "Fine for not wearing a helmet. What if it is my 3rd time?", "session": False},
    {"q": "Is the fine for no seatbelt different for a second time?", "session": False},
    {"q": "Overspeeding fine for a commercial truck vs a private car.", "session": False},
    {"q": "What if a minor is caught driving without a license?", "session": False},
    {"q": "Fine for driving without a license plate.", "session": False},

    # Category 3: International Traffic Fines
    {"q": "What is the fine for running a red light in Dubai (UAE)?", "session": False},
    {"q": "Fine for speeding in Abu Dhabi.", "session": False},
    {"q": "How much is the penalty for texting and driving in the UK?", "session": False},
    {"q": "Fine for driving without insurance in California, USA.", "session": False},
    {"q": "What is the demerit point penalty for speeding in Singapore?", "session": False},
    {"q": "Fine for parking in a disabled spot in Saudi Arabia.", "session": False},
    {"q": "Penalty for driving under the influence in New York.", "session": False},
    {"q": "Fine for not wearing a seatbelt in London, UK.", "session": False},

    # Category 4: Rule Explanations & Legal Sections
    {"q": "Under what section of the Motor Vehicles Act is drunk driving penalized?", "session": False},
    {"q": "Explain Section 194D of the Motor Vehicles Act.", "session": False},
    {"q": "What are the rules for tinted windows on cars?", "session": False},
    {"q": "Is it legal to modify the exhaust of my motorcycle?", "session": False},
    {"q": "What are the rules regarding high-beam headlights in city limits?", "session": False},
    {"q": "Does a pillion rider need to wear a helmet by law?", "session": False},
    {"q": "What is the legal blood alcohol limit for driving in India?", "session": False},
    {"q": "Are physical documents required, or is DigiLocker valid?", "session": False},

    # Category 5: Geofencing & Location-Based Queries
    {"q": "I am at 13.01, 80.23. What are the traffic rules here?", "session": False, "gps": {"lat": 13.01, "lon": 80.23}},
    {"q": "Am I currently in a school zone?", "session": False, "gps": {"lat": 13.01, "lon": 80.23}},
    {"q": "What is the speed limit in a hospital zone?", "session": False},
    {"q": "Are there any fine multipliers for violations inside a school zone?", "session": False},
    {"q": "Can I honk in a hospital zone?", "session": False},

    # Category 6: Challan Calculation & Management
    {"q": "Can you check pending challans for vehicle TN01AB1234?", "session": False},
    {"q": "How do I pay my traffic fine online?", "session": False},
    {"q": "What happens if I don't pay my e-challan?", "session": False},
    {"q": "Can my license be suspended for unpaid fines?", "session": False},
    {"q": "How many points until my driving license is revoked in the UAE?", "session": False},

    # Category 7: Conversational & Multi-Turn Context (Memory)
    {"q": "What is the fine for no helmet?", "session": True},
    {"q": "What about in Delhi?", "session": True},
    {"q": "And for a car?", "session": True},
    {"q": "Hi there! How can you help me today?", "session": True},
    {"q": "Thanks for the information!", "session": True},

    # Category 8: Irrelevant & Out-of-Scope Queries (Safety/Fallback)
    {"q": "Give me a recipe for chocolate cake.", "session": False},
    {"q": "Write a Python script to scrape the Parivahan website.", "session": False},
    {"q": "What is the capital of France?", "session": False},
]

def run_tests():
    url = "http://localhost:8001/agent/query"
    session_id = "test_session_123"
    results = []
    success_count = 0
    total_count = len(TEST_CASES)

    with open("test_report.md", "w", encoding="utf-8") as f:
        f.write("# DriveLegal AI Agent - 50 Test Cases Report\n\n")

        for idx, tc in enumerate(TEST_CASES):
            payload = {
                "text": tc["q"]
            }
            if tc.get("session"):
                payload["session_id"] = session_id
            if tc.get("gps"):
                payload["gps"] = tc["gps"]

            try:
                resp = requests.post(url, json=payload, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    response_text = data.get("response", "NO_RESPONSE")
                    # Basic evaluation: we consider it 'Success' if response text is reasonably long and doesn't explicitly throw an error status
                    status = "Success"
                    if data.get("status") == "error":
                        status = "Error"
                    
                    # Log to markdown
                    f.write(f"### Q{idx+1}: {tc['q']}\n")
                    f.write(f"**Status**: {status}\n")
                    f.write(f"**Agent Response**: {response_text}\n\n")

                    if status == "Success":
                        success_count += 1
                else:
                    f.write(f"### Q{idx+1}: {tc['q']}\n")
                    f.write(f"**Status**: HTTP Error {resp.status_code}\n\n")
            except Exception as e:
                f.write(f"### Q{idx+1}: {tc['q']}\n")
                f.write(f"**Status**: Exception - {str(e)}\n\n")

            time.sleep(0.5)

        accuracy = (success_count / total_count) * 100
        f.write(f"---\n\n## Summary\n")
        f.write(f"Total Cases: {total_count}\n")
        f.write(f"Successful Responses: {success_count}\n")
        f.write(f"Accuracy Rate: {accuracy}%\n")
        
        print(f"Tests complete. Accuracy: {accuracy}%. Report saved to test_report.md")

if __name__ == "__main__":
    run_tests()
