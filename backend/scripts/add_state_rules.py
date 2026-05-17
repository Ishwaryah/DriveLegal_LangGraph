import json
import os

RULES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/rules.json"))

STATE_RULES = [
    # ── Tamil Nadu Rules ──────────────────────────────────────────────────────
    {
        "rule_id": "STATE_TN_PARKING",
        "section": "Section 122 read with Section 177 / TN compounding rules",
        "act": "Tamil Nadu Motor Vehicles Rules",
        "title": "Wrong Parking Fine in Tamil Nadu",
        "description": "Under the Tamil Nadu Motor Vehicles Rules, the compounding fee for wrong parking or parking in a 'No Parking' zone (Section 122 read with Section 177) is ₹500 for the first offence and ₹1,500 for subsequent offences.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["parking", "wrong parking", "no parking", "tamil nadu", "compounding"],
        "state_overrides": [{"state": "Tamil Nadu", "description": "Compounding fee for wrong parking is ₹500 (first) / ₹1,500 (repeat)."}]
    },
    {
        "rule_id": "STATE_TN_HELMET",
        "section": "Section 129 read with Section 194D / TN compounding rules",
        "act": "Tamil Nadu Motor Vehicles Rules",
        "title": "Driving Without Helmet in Tamil Nadu",
        "description": "Riding a two-wheeler without a protective helmet in Tamil Nadu is subject to a compounding fine of ₹1,000 and mandatory suspension of the driving license for a period of 3 months under Section 194D and state rules.",
        "applies_to": ["two_wheeler"],
        "vehicle_classes": ["two_wheeler", "TW"],
        "tags": ["helmet", "no helmet", "tamil nadu", "two wheeler", "compounding"],
        "state_overrides": [{"state": "Tamil Nadu", "description": "Fine of ₹1,000 and 3-month driving license suspension."}]
    },
    {
        "rule_id": "STATE_TN_SPEED",
        "section": "Section 112 read with Section 183 / TN compounding rules",
        "act": "Tamil Nadu Motor Vehicles Rules",
        "title": "Overspeeding / Speed Limits in Tamil Nadu",
        "description": "Overspeeding or exceeding speed limits in Tamil Nadu is compoundable at ₹1,000 for Light Motor Vehicles (LMV) and ₹2,000 for Medium or Heavy Passenger/Goods Vehicles (HMV).",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["speeding", "overspeeding", "speed limit", "tamil nadu", "compounding"],
        "state_overrides": [{"state": "Tamil Nadu", "description": "Compounding fee for overspeeding: ₹1,000 for LMV, ₹2,000 for HMV."}]
    },
    {
        "rule_id": "STATE_TN_DRUNK",
        "section": "Section 185 / TN compounding rules",
        "act": "Tamil Nadu Motor Vehicles Rules",
        "title": "Drunk Driving in Tamil Nadu",
        "description": "Drunk driving (driving under the influence of alcohol or drugs exceeding 30mg per 100ml of blood) in Tamil Nadu is non-compoundable and requires court trial. Subject to a fine of ₹10,000 and/or up to 6 months imprisonment for the first offence, and a minimum 6-month DL suspension.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["drunk", "drunken driving", "alcohol", "tamil nadu", "non-compoundable"],
        "state_overrides": [{"state": "Tamil Nadu", "description": "Fine of ₹10,000, possible 6 months jail term, and 6-month DL suspension."}]
    },
    # ── Maharashtra Rules ─────────────────────────────────────────────────────
    {
        "rule_id": "STATE_MH_PARKING",
        "section": "Section 122 read with Section 177 / MH Rules 1989",
        "act": "Maharashtra Motor Vehicles Rules 1989",
        "title": "Wrong Parking Compounding in Maharashtra",
        "description": "Wrong parking or creating traffic obstruction in Maharashtra carries a compounding fine of ₹500 for the first offence under the Maharashtra Motor Vehicles Rules 1989, plus an additional ₹200 tow charge if towed by police.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["parking", "wrong parking", "no parking", "maharashtra", "compounding"],
        "state_overrides": [{"state": "Maharashtra", "description": "Compounding fee: ₹500 for first offence plus ₹200 tow charge."}]
    },
    {
        "rule_id": "STATE_MH_HELMET",
        "section": "Section 129 read with Section 194D / MH Rules 1989",
        "act": "Maharashtra Motor Vehicles Rules 1989",
        "title": "Riding Without Helmet in Maharashtra",
        "description": "Riding a two-wheeler without a protective helmet in Maharashtra attracts a compounding fine of ₹500 and a compulsory suspension of the driving license for 3 months under Maharashtra compounding rules.",
        "applies_to": ["two_wheeler"],
        "vehicle_classes": ["two_wheeler", "TW"],
        "tags": ["helmet", "no helmet", "maharashtra", "two wheeler", "compounding"],
        "state_overrides": [{"state": "Maharashtra", "description": "Compounding fee: ₹500 and 3-month DL suspension."}]
    },
    {
        "rule_id": "STATE_MH_SPEED",
        "section": "Section 112 read with Section 183 / MH Rules 1989",
        "act": "Maharashtra Motor Vehicles Rules 1989",
        "title": "Overspeeding Penalties in Maharashtra",
        "description": "Overspeeding in Maharashtra attracts a compounding fine of ₹1,000 for Light Motor Vehicles (LMV) and ₹2,000 for Heavy Goods or Passenger Vehicles under the Maharashtra rules.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["speeding", "overspeeding", "speed limit", "maharashtra", "compounding"],
        "state_overrides": [{"state": "Maharashtra", "description": "Compounding fee: ₹1,000 for LMV, ₹2,000 for HMV/Transport."}]
    },
    {
        "rule_id": "STATE_MH_DRUNK",
        "section": "Section 185 / MH Rules 1989",
        "act": "Maharashtra Motor Vehicles Rules 1989",
        "title": "Drunk Driving Penalties in Maharashtra",
        "description": "Driving under the influence of alcohol (BAC exceeding 30mg/100ml) in Maharashtra is non-compoundable. Requires court appearance, fine of ₹10,000, and up to 6 months imprisonment for the first offence, plus license suspension.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["drunk", "drunken driving", "alcohol", "maharashtra", "non-compoundable"],
        "state_overrides": [{"state": "Maharashtra", "description": "Court fine: ₹10,000, possible 6 months jail term, and DL suspension."}]
    },
    # ── Delhi Rules ───────────────────────────────────────────────────────────
    {
        "rule_id": "STATE_DL_ODD_EVEN",
        "section": "Section 115 / Delhi Transport Notification",
        "act": "Delhi Motor Vehicle Rules 1993",
        "title": "Odd-Even Violation in Delhi NCR",
        "description": "Operating a four-wheeler in violation of the active Odd-Even scheme rules in Delhi NCR carries a compounding fine of ₹4,000 under Section 115 and matching state notifications aimed at pollution control.",
        "applies_to": ["lmv"],
        "vehicle_classes": ["lmv", "LMV"],
        "tags": ["odd-even", "pollution", "delhi", "compounding", "restriction"],
        "state_overrides": [{"state": "Delhi", "description": "Compounding fee of ₹4,000 for non-compliance."}]
    },
    {
        "rule_id": "STATE_DL_PARKING",
        "section": "Section 122 read with Section 177 / Delhi Rules 1993",
        "act": "Delhi Motor Vehicle Rules 1993",
        "title": "Wrong Parking Fine in Delhi NCR",
        "description": "Wrong parking or leaving a vehicle in an obstructing position in Delhi NCR attracts a compounding fine of ₹500 for the first offence under the Delhi Motor Vehicle Rules 1993, which can stack with additional municipal towing charges.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["parking", "wrong parking", "no parking", "delhi", "compounding"],
        "state_overrides": [{"state": "Delhi", "description": "Compounding fee: ₹500 for first offence plus tow charges."}]
    },
    {
        "rule_id": "STATE_DL_HELMET",
        "section": "Section 129 read with Section 194D / Delhi Rules 1993",
        "act": "Delhi Motor Vehicle Rules 1993",
        "title": "Riding Without Helmet in Delhi NCR",
        "description": "Riding a two-wheeler without a protective helmet in Delhi is compounded at ₹1,000 and is subject to a compulsory 3-month driving license suspension under Delhi Transport Department guidelines.",
        "applies_to": ["two_wheeler"],
        "vehicle_classes": ["two_wheeler", "TW"],
        "tags": ["helmet", "no helmet", "delhi", "two wheeler", "compounding"],
        "state_overrides": [{"state": "Delhi", "description": "Compounding fee: ₹1,000 and 3-month driving license suspension."}]
    },
    {
        "rule_id": "STATE_DL_POLLUTION",
        "section": "Section 190(2) / Delhi Transport Notification",
        "act": "Delhi Motor Vehicle Rules 1993",
        "title": "Air Pollution / Expired PUC in Delhi NCR",
        "description": "Operating a motor vehicle without a valid Pollution Under Control Certificate (PUCC) in Delhi NCR is strictly penalized with a compounding fine of ₹10,000 and a 3-month DL suspension under Section 190(2) and Supreme Court guidelines.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["puc", "pucc", "pollution", "expired puc", "delhi", "compounding"],
        "state_overrides": [{"state": "Delhi", "description": "Compounding fee of ₹10,000 and 3-month driving license suspension."}]
    },
    # ── Karnataka Rules ───────────────────────────────────────────────────────
    {
        "rule_id": "STATE_KA_PARKING",
        "section": "Section 122 read with Section 177 / KA Rules 1989",
        "act": "Karnataka Motor Vehicles Rules 1989",
        "title": "Wrong Parking Compounding in Karnataka",
        "description": "Wrong parking or creating a hazard/obstruction in Karnataka (especially in urban limits like Bengaluru) attracts a compounding fine of ₹1,000 under the Karnataka Motor Vehicles Rules 1989.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["parking", "wrong parking", "no parking", "karnataka", "compounding"],
        "state_overrides": [{"state": "Karnataka", "description": "Compounding fine: ₹1,000 for wrong parking."}]
    },
    {
        "rule_id": "STATE_KA_HELMET",
        "section": "Section 129 read with Section 194D / KA Rules 1989",
        "act": "Karnataka Motor Vehicles Rules 1989",
        "title": "Riding Without Helmet in Karnataka",
        "description": "Riding a two-wheeler without a protective helmet in Karnataka is subject to a compounding fine of ₹1,000 and a compulsory 3-month suspension of the driving license under Section 194D and state rules.",
        "applies_to": ["two_wheeler"],
        "vehicle_classes": ["two_wheeler", "TW"],
        "tags": ["helmet", "no helmet", "karnataka", "two wheeler", "compounding"],
        "state_overrides": [{"state": "Karnataka", "description": "Compounding fine: ₹1,000 and 3-month driving license suspension."}]
    },
    {
        "rule_id": "STATE_KA_MOBILE",
        "section": "Section 184(c) / KA Rules 1989",
        "act": "Karnataka Motor Vehicles Rules 1989",
        "title": "Using Mobile Phone While Driving in Karnataka",
        "description": "Using a handheld mobile communication device while driving or riding in Karnataka is subject to a compounding fine of ₹1,000 for two-wheelers and ₹2,000 for Light Motor Vehicles (LMV) and larger classes.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["mobile", "phone", "distracted driving", "karnataka", "compounding"],
        "state_overrides": [{"state": "Karnataka", "description": "Compounding fine: ₹1,000 for two-wheelers, ₹2,000 for four-wheelers."}]
    },
    {
        "rule_id": "STATE_KA_TRIPLE",
        "section": "Section 128 read with Section 194C / KA Rules 1989",
        "act": "Karnataka Motor Vehicles Rules 1989",
        "title": "Triple Riding on Two-Wheeler in Karnataka",
        "description": "Riding with more than one pillion rider (triple riding) on a two-wheeler in Karnataka is compounded at ₹1,000 under Section 194C and matching Karnataka compounding rules.",
        "applies_to": ["two_wheeler"],
        "vehicle_classes": ["two_wheeler", "TW"],
        "tags": ["triple riding", "pillion", "karnataka", "two wheeler", "compounding"],
        "state_overrides": [{"state": "Karnataka", "description": "Compounding fine: ₹1,000 for triple riding."}]
    },
    # ── Gujarat Rules ─────────────────────────────────────────────────────────
    {
        "rule_id": "STATE_GJ_PARKING",
        "section": "Section 122 read with Section 177 / GJ Rules 1989",
        "act": "Gujarat Motor Vehicles Rules 1989",
        "title": "Wrong Parking Fine in Gujarat",
        "description": "Wrong parking or blocking free passage in Gujarat attracts a compounding fine of ₹500 for LMV (cars) and ₹1,000 for larger transport/medium vehicles under the Gujarat state notifications.",
        "applies_to": ["ALL"],
        "vehicle_classes": ["ALL"],
        "tags": ["parking", "wrong parking", "no parking", "gujarat", "compounding"],
        "state_overrides": [{"state": "Gujarat", "description": "Compounding fee: ₹500 for LMV, ₹1,000 for larger vehicles."}]
    },
    {
        "rule_id": "STATE_GJ_HELMET",
        "section": "Section 129 read with Section 194D / GJ Rules 1989",
        "act": "Gujarat Motor Vehicles Rules 1989",
        "title": "Riding Without Helmet in Gujarat",
        "description": "Riding a two-wheeler without a protective helmet in Gujarat carries a compounding fine of ₹500 under Gujarat state compounding notifications.",
        "applies_to": ["two_wheeler"],
        "vehicle_classes": ["two_wheeler", "TW"],
        "tags": ["helmet", "no helmet", "gujarat", "two wheeler", "compounding"],
        "state_overrides": [{"state": "Gujarat", "description": "Compounding fee of ₹500."}]
    },
    {
        "rule_id": "STATE_GJ_SEATBELT",
        "section": "Section 194B / GJ Rules 1989",
        "act": "Gujarat Motor Vehicles Rules 1989",
        "title": "Driving Without Seatbelt in Gujarat",
        "description": "Driving a motor vehicle without wearing a seatbelt in Gujarat is compounded at ₹500 under Section 194B and the matching Gujarat state notifications.",
        "applies_to": ["lmv"],
        "vehicle_classes": ["lmv", "LMV"],
        "tags": ["seatbelt", "no seatbelt", "gujarat", "compounding"],
        "state_overrides": [{"state": "Gujarat", "description": "Compounding fee of ₹500."}]
    },
    {
        "rule_id": "STATE_GJ_TRIPLE",
        "section": "Section 128 read with Section 194C / GJ Rules 1989",
        "act": "Gujarat Motor Vehicles Rules 1989",
        "title": "Triple Riding Penalties in Gujarat",
        "description": "Triple riding on a two-wheeler in Gujarat attracts a compounding fee of ₹500 under Gujarat Transport Department compounding guidelines.",
        "applies_to": ["two_wheeler"],
        "vehicle_classes": ["two_wheeler", "TW"],
        "tags": ["triple riding", "pillion", "gujarat", "two wheeler", "compounding"],
        "state_overrides": [{"state": "Gujarat", "description": "Compounding fee of ₹500."}]
    }
]

def merge_state_rules():
    print(f"Loading rules database from {RULES_PATH}...")
    if not os.path.exists(RULES_PATH):
        print(f"Error: {RULES_PATH} does not exist!")
        return

    with open(RULES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    existing_rules = data.get("rules", [])
    existing_ids = {r.get("rule_id") for r in existing_rules}

    added_count = 0
    for rule in STATE_RULES:
        if rule["rule_id"] not in existing_ids:
            existing_rules.append(rule)
            added_count += 1
            existing_ids.add(rule["rule_id"])

    data["rules"] = existing_rules

    with open(RULES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Successfully injected {added_count} new state-specific rules into {RULES_PATH}.")
    print(f"Total rules now: {len(existing_rules)}")

if __name__ == "__main__":
    merge_state_rules()
