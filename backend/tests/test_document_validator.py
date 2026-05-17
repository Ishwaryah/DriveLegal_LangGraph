import os
import sys
from datetime import date, timedelta

# Ensure the workspace root is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.document_validator import DocumentValidator

def run_tests():
    print("=" * 80)
    print("RUNNING DRIVELEGAL DOCUMENT VALIDATION TEST SUITE")
    print("=" * 80)

    validator = DocumentValidator()
    success = True

    # -------------------------------------------------------------------------
    # SCENARIO 1: Expired PUC (Petrol two-wheeler, expired 30 days ago)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("SCENARIO 1: Expired PUC Certificate Check")
    print("Target: Petrol Two-Wheeler (1-15 years), PUC expired 30 days ago")
    print("-" * 60)

    # Expiry 30 days ago means we need a last_puc_date that is (6 months + 30 days) ago
    target_expiry = date.today() - timedelta(days=30)
    # Subtract 6 months:
    year = target_expiry.year - (1 if target_expiry.month <= 6 else 0)
    month = (target_expiry.month - 6 - 1) % 12 + 1
    import calendar
    day = min(target_expiry.day, calendar.monthrange(year, month)[1])
    last_puc_date = date(year, month, day)

    puc_res = validator.check_puc_validity(
        vehicle_type="Two-Wheeler",
        fuel_type="Petrol",
        vehicle_age_years=3,
        last_puc_date=last_puc_date
    )

    print(f"Input Last PUC Date : {last_puc_date.isoformat()}")
    print(f"Calculated Expiry   : {puc_res.get('expiry_date')}")
    print(f"Days Remaining      : {puc_res.get('days_remaining')}")
    print(f"Is Valid?           : {puc_res.get('is_valid')}")
    
    fine_info = puc_res.get("applicable_fine")
    if fine_info:
        print(f"Penalty Section     : {fine_info.get('section')}")
        print(f"Fine Amount         : INR {fine_info.get('fine_amount')}")
        print(f"Violation Reason    : {fine_info.get('reason')}")

    passed_s1 = (puc_res.get("is_valid") is False and 
                 fine_info is not None and 
                 fine_info.get("fine_amount") == 10000)
    
    print(f"STATUS: {'[PASSED]' if passed_s1 else '[FAILED]'}")
    if not passed_s1:
        success = False

    # -------------------------------------------------------------------------
    # SCENARIO 2: Valid Insurance (ICICI Lombard, expires in 60 days)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("SCENARIO 2: Valid Insurance Certificate Check")
    print("Target: ICICI Lombard Policy, expires in 60 days")
    print("-" * 60)

    expiry_date_ins = date.today() + timedelta(days=60)
    ins_res = validator.check_insurance_validity(
        policy_expiry_date=expiry_date_ins,
        company_code="ICICIL"
    )

    print(f"Input Expiry Date   : {expiry_date_ins.isoformat()}")
    print(f"Days Remaining      : {ins_res.get('days_remaining')}")
    print(f"Is Valid?           : {ins_res.get('is_valid')}")
    
    comp_info = ins_res.get("company_info")
    if comp_info:
        print(f"Insurer Registry    : {comp_info.get('company_name')} ({comp_info.get('short_code')})")
        print(f"Insurer Helpline    : {comp_info.get('helpline')}")
        print(f"Insurer Portal      : {comp_info.get('policy_verification_url')}")

    passed_s2 = (ins_res.get("is_valid") is True and 
                 comp_info is not None and 
                 comp_info.get("short_code") == "ICICIL")
    
    print(f"STATUS: {'[PASSED]' if passed_s2 else '[FAILED]'}")
    if not passed_s2:
        success = False

    # -------------------------------------------------------------------------
    # SCENARIO 3: Expired Fitness Certificate (Commercial Goods Vehicle, expired 10 days ago)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("SCENARIO 3: Expired Fitness Certificate Check")
    print("Target: Commercial Goods Vehicle, fitness certificate expired 10 days ago")
    print("-" * 60)

    expiry_date_fit = date.today() - timedelta(days=10)
    fit_res = validator.check_fitness_validity(
        vehicle_category="Commercial Goods Vehicle",
        fitness_expiry_date=expiry_date_fit
    )

    print(f"Input Expiry Date   : {expiry_date_fit.isoformat()}")
    print(f"Days Remaining      : {fit_res.get('days_remaining')}")
    print(f"Is Valid?           : {fit_res.get('is_valid')}")

    fine_info_fit = fit_res.get("applicable_fine")
    if fine_info_fit:
        print(f"Penalty Section     : {fine_info_fit.get('section')}")
        print(f"Fine Amount         : INR {fine_info_fit.get('fine_amount')}")
        print(f"Violation Reason    : {fine_info_fit.get('reason')}")

    passed_s3 = (fit_res.get("is_valid") is False and 
                 fine_info_fit is not None and 
                 fine_info_fit.get("fine_amount") == 2000)
    
    print(f"STATUS: {'[PASSED]' if passed_s3 else '[FAILED]'}")
    if not passed_s3:
        success = False

    # -------------------------------------------------------------------------
    # SCENARIO 4: LMV Driver Trying to Drive HMV (Category mismatch)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("SCENARIO 4: DL Endorsement Authorization Check")
    print("Target: LMV license holder driving heavy multi-axle freight truck (HMV)")
    print("-" * 60)

    dl_res = validator.check_dl_category(
        dl_categories=["LMV"],
        vehicle_being_driven="HMV"
    )

    print(f"Licensed Categories : {dl_res.get('held_categories')}")
    print(f"Vehicle Driven      : {dl_res.get('vehicle_driven')}")
    print(f"Is Authorized?      : {dl_res.get('is_authorized')}")

    viol_info = dl_res.get("violation_if_any")
    if viol_info:
        print(f"DL Violation Scenario: {viol_info.get('scenario')}")
        print(f"Penalty Section      : {viol_info.get('applicable_section')}")
        print(f"Fine Amount          : INR {viol_info.get('fine_inr')}")
        print(f"Possible Jail Term   : {viol_info.get('imprisonment_months')} months")

    passed_s4 = (dl_res.get("is_authorized") is False and 
                 viol_info is not None and 
                 "wrong category" in viol_info.get("scenario").lower())
    
    print(f"STATUS: {'[PASSED]' if passed_s4 else '[FAILED]'}")
    if not passed_s4:
        success = False

    # -------------------------------------------------------------------------
    # SCENARIO 5: All-Valid Scenario (Compliance check on all documents)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("SCENARIO 5: Complete Compliance Check - All Clear")
    print("Target: LMV Petrol, 3 years age, active PUC, active NIC Insurance, active Fitness, LMV DL")
    print("-" * 60)

    puc_date_valid = date.today() - timedelta(days=60)
    ins_date_valid = date.today() + timedelta(days=120)
    fit_date_valid = date.today() + timedelta(days=360)

    vehicle_info = {
        "vehicle_type": "LMV",
        "fuel_type": "Petrol",
        "vehicle_age_years": 3,
        "last_puc_date": puc_date_valid,
        "policy_expiry_date": ins_date_valid,
        "insurance_company_code": "NIC",
        "vehicle_category": "Private Cars",
        "fitness_expiry_date": fit_date_valid,
        "dl_categories": ["LMV"],
        "vehicle_being_driven": "LMV"
    }

    full_res = validator.validate_all_documents(vehicle_info)

    print(f"Overall Compliance Status : {'COMPLIANT' if full_res.get('all_clear') else 'VIOLATION DETECTED'}")
    print(f"Cumulative Fine Amount    : INR {full_res.get('total_fine_inr')}")
    print(f"Active Violations Count   : {len(full_res.get('violations_detected', []))}")

    passed_s5 = (full_res.get("all_clear") is True and 
                 full_res.get("total_fine_inr") == 0 and 
                 len(full_res.get("violations_detected")) == 0)
    
    print(f"STATUS: {'[PASSED]' if passed_s5 else '[FAILED]'}")
    if not passed_s5:
        success = False

    # -------------------------------------------------------------------------
    # EXTRA SCENARIO: Delhi NCR Overrides
    # -------------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("EXTRA SCENARIO: Delhi NCR Regional Overrides")
    print("Target 1: Diesel vehicle older than 15 years in Delhi NCR (BANNED)")
    print("Target 2: Petrol LMV in Delhi NCR checked after 9 months (Normally 12m, Delhi strictly 6m)")
    print("-" * 60)

    # 1. Banned check
    delhi_banned_res = validator.check_puc_validity(
        vehicle_type="LMV",
        fuel_type="Diesel",
        vehicle_age_years=16,
        last_puc_date=date.today() - timedelta(days=30),
        state="DL"
    )
    print(f"Target 1: Is Valid?      : {delhi_banned_res.get('is_valid')}")
    print(f"Target 1: Is Banned?     : {delhi_banned_res.get('banned', False)}")
    print(f"Target 1: Active Penalty : INR {delhi_banned_res.get('applicable_fine', {}).get('fine_amount')}")
    print(f"Target 1: Reason         : {delhi_banned_res.get('applicable_fine', {}).get('reason')}")

    # 2. Delhi 6-month strict renewal check vs central 12-month renewal
    last_puc_9m_ago = date.today() - timedelta(days=9*30)
    
    # Under default rules
    default_puc_res = validator.check_puc_validity(
        vehicle_type="LMV",
        fuel_type="Petrol",
        vehicle_age_years=3,
        last_puc_date=last_puc_9m_ago,
        state="ALL"
    )
    # Under Delhi rules
    delhi_puc_res = validator.check_puc_validity(
        vehicle_type="LMV",
        fuel_type="Petrol",
        vehicle_age_years=3,
        last_puc_date=last_puc_9m_ago,
        state="DL"
    )

    print(f"\nTarget 2 (Central Rule)  : Is Valid? : {default_puc_res.get('is_valid')} (Expiry: {default_puc_res.get('expiry_date')})")
    print(f"Target 2 (Delhi Rule)    : Is Valid? : {delhi_puc_res.get('is_valid')} (Expiry: {delhi_puc_res.get('expiry_date')})")

    passed_delhi = (delhi_banned_res.get("banned") is True and 
                    default_puc_res.get("is_valid") is True and 
                    delhi_puc_res.get("is_valid") is False)

    print(f"\nSTATUS: {'[PASSED]' if passed_delhi else '[FAILED]'}")
    if not passed_delhi:
        success = False

    # -------------------------------------------------------------------------
    # CONCLUSION
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    if success:
        print("ALL DOCUMENT VALIDATOR TEST SCENARIOS COMPLETED SUCCESSFULLY! [SUCCESS]")
    else:
        print("SOME DOCUMENT VALIDATOR TEST SCENARIOS FAILED! [FAILURE]")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
