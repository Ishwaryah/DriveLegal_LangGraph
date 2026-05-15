import json
import os

RULES_PATH = r"c:\Users\USER\Downloads\DriveLegal-main\DriveLegal-main\backend\data\rules.json"

NEW_RULES = [
    # ACCIDENT LAW & MACT
    {
        "rule_id": "ACC_001",
        "section": "Section 161",
        "act": "Motor Vehicles (Amendment) Act 2019",
        "title": "Compensation in Hit-and-Run Cases",
        "description": "Under Section 161, victims of hit-and-run accidents are entitled to compensation. For death, the compensation is ₹2,00,000. For grievous hurt, it is ₹50,000.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["accident", "hit and run", "compensation", "MACT"]
    },
    {
        "rule_id": "ACC_002",
        "section": "Section 166",
        "act": "Motor Vehicles Act 1988",
        "title": "Application for Compensation (MACT)",
        "description": "An application for compensation can be filed in the Motor Accident Claims Tribunal (MACT) by the person who sustained the injury, the owner of the property, or the legal representatives of the deceased.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["MACT", "compensation", "claims", "legal"]
    },
    {
        "rule_id": "ACC_003",
        "section": "Section 134",
        "act": "Motor Vehicles Act 1988",
        "title": "Duty of Driver in Case of Accident",
        "description": "The driver must take all reasonable steps to secure medical help for the injured person and inform the nearest police station within 24 hours.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["accident", "duty of driver", "first aid", "police report"]
    },
    # INSURANCE CLAIMS
    {
        "rule_id": "INS_001",
        "section": "Section 146",
        "act": "Motor Vehicles Act 1988",
        "title": "Mandatory Third Party Insurance",
        "description": "No person shall use a motor vehicle in a public place without a valid third-party insurance policy. This covers liability for death, bodily injury, or property damage to third parties.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["insurance", "third party", "mandatory"]
    },
    {
        "rule_id": "INS_002",
        "section": "Insurance Procedure",
        "act": "IRDAI Guidelines",
        "title": "How to Claim Insurance After an Accident",
        "description": "1. Inform the insurance company immediately.\n2. File an FIR at the local police station.\n3. Take photos of the damage and the accident scene.\n4. Submit the claim form with RC, DL, FIR copy, and repair estimates.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["insurance claim", "accident", "procedure"]
    },
    # RTO PROCEDURES
    {
        "rule_id": "RTO_001",
        "section": "Section 8",
        "act": "Motor Vehicles Act 1988",
        "title": "Grant of Learner's License",
        "description": "Any person who is not disqualified under Section 4 and has passed the preliminary test on road signs and traffic rules can apply for a learner's license.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["RTO", "learner license", "DL application"]
    },
    {
        "rule_id": "RTO_002",
        "section": "Section 47",
        "act": "Motor Vehicles Act 1988",
        "title": "Re-registration of Vehicle (State Transfer)",
        "description": "If a vehicle is kept in another state for more than 12 months, the owner must apply for a new registration mark (re-registration) in that state after obtaining an NOC from the original RTO.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["RTO", "vehicle transfer", "re-registration", "NOC"]
    },
    {
        "rule_id": "RTO_003",
        "section": "Section 50",
        "act": "Motor Vehicles Act 1988",
        "title": "Transfer of Ownership",
        "description": "The transfer of ownership must be reported to the RTO within 14 days if the transfer is within the same state, and within 45 days if it is to another state.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["RTO", "ownership transfer", "sale of vehicle"]
    }
]

def add_rules():
    if not os.path.exists(RULES_PATH):
        print(f"File not found: {RULES_PATH}")
        return

    with open(RULES_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    data['rules'].extend(NEW_RULES)

    with open(RULES_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f"Added {len(NEW_RULES)} new rules for Accident Law, Insurance, and RTO.")

if __name__ == "__main__":
    add_rules()
