import json
import os

RULES_PATH = r"c:\Users\USER\Downloads\DriveLegal-main\DriveLegal-main\backend\data\rules.json"

MORE_RTO_RULES = [
    {
        "rule_id": "RTO_004",
        "section": "DL Application Procedure",
        "act": "RTO Guidelines",
        "title": "Steps to Apply for a Permanent Driving License",
        "description": "1. Apply after 30 days but within 6 months of obtaining a Learner's License.\n2. Book a slot for the driving test at your local RTO via Parivahan portal.\n3. Bring your own vehicle of the relevant class for the test.\n4. Pass the driving test and provide biometric data (photo, signature).\n5. The DL will be sent to your registered address by post.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["RTO", "DL application", "driving test", "procedure"]
    },
    {
        "rule_id": "RTO_005",
        "section": "NOC Procedure",
        "act": "RTO Guidelines",
        "title": "How to Obtain a No Objection Certificate (NOC)",
        "description": "1. Fill Form 28 and submit it to the parent RTO.\n2. Attach copies of RC, Insurance, PUC, and ID proof.\n3. Pay the prescribed fee.\n4. The RTO will verify if there are any pending challans or criminal cases.\n5. If clear, the NOC is issued for a specific state/RTO.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["RTO", "NOC", "vehicle transfer", "procedure"]
    }
]

def add_more_rto_rules():
    if not os.path.exists(RULES_PATH):
        return

    with open(RULES_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    data['rules'].extend(MORE_RTO_RULES)

    with open(RULES_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f"Added {len(MORE_RTO_RULES)} more detailed RTO rules.")

if __name__ == "__main__":
    add_more_rto_rules()
