import os
import json
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional

logger = logging.getLogger("drivelegal.document_validator")

class DocumentValidator:
    """
    Fine calculation and document validity engine under the Motor Vehicles Act 1988 (amended 2019).
    Loads structured reference JSON datasets to apply document renewal timelines,
    exemption criteria, RTO guidelines, and corresponding violation penalties.
    """
    def __init__(self, data_dir: str = None):
        self.backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if data_dir is None:
            data_dir = os.path.join(self.backend_dir, "data", "drivelegal_dataset", "json")
        self.data_dir = data_dir
        
        self.puc_rules = self._load_json("puc_validity_rules.json")
        self.insurance_rules = self._load_json("insurance_company_codes.json")
        self.fitness_rules = self._load_json("fitness_certificate_rules.json")
        self.dl_rules = self._load_json("dl_endorsement_codes.json")

    def _load_json(self, filename: str) -> Dict[str, Any]:
        path = os.path.join(self.data_dir, filename)
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                logger.warning("JSON file not found: %s", path)
        except Exception as e:
            logger.error("Failed to load JSON file %s: %s", filename, e)
        return {}

    def _parse_date(self, val: Any) -> date:
        """
        Robustly parses various date formats and datetime types into standard datetime.date object.
        """
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, date):
            return val
        if isinstance(val, str):
            val = val.strip()
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ", "%d-%m-%Y", "%Y/%m/%d"):
                try:
                    return datetime.strptime(val, fmt).date()
                except ValueError:
                    pass
        raise ValueError(f"Unable to parse date: '{val}'")

    def _normalize_vehicle_age(self, age: Any) -> str:
        """
        Maps numeric or string vehicle ages into reference JSON bracket keys: "0-1", "1-15", "15+".
        """
        if isinstance(age, (int, float)):
            if age <= 1.0:
                return "0-1"
            elif age < 15.0:
                return "1-15"
            else:
                return "15+"
        if isinstance(age, str):
            age_str = age.strip()
            if age_str in ["0-1", "1-15", "15+"]:
                return age_str
            try:
                val = float(age_str)
                return self._normalize_vehicle_age(val)
            except ValueError:
                pass
        return "1-15"  # Standard default fallback

    def check_puc_validity(self, vehicle_type: str, fuel_type: str, vehicle_age_years: Any, last_puc_date: Any, state: str = "ALL") -> dict:
        """
        Validates PUC status considering vehicle details, fuel type, and regional/state overrides (like Delhi).
        
        Returns:
            dict: {
                "is_valid": bool,
                "days_remaining": int,
                "expiry_date": str (ISO date),
                "notes": str,
                "applicable_fine": dict or None
            }
        """
        try:
            puc_date = self._parse_date(last_puc_date)
        except Exception as e:
            return {
                "is_valid": False,
                "error": f"Invalid last_puc_date: {e}",
                "days_remaining": 0,
                "applicable_fine": {
                    "fine_amount": self.puc_rules.get("default_fine_inr", 10000),
                    "section": self.puc_rules.get("fine_section", "Section 190(2) MV Act"),
                    "reason": f"Malformed or missing PUC date: {e}"
                }
            }

        age_bracket = self._normalize_vehicle_age(vehicle_age_years)
        state_code = state.upper() if state else "ALL"
        
        # Check for state override
        rules_list = []
        is_override = False
        
        if state_code != "ALL" and "state_overrides" in self.puc_rules:
            state_data = self.puc_rules["state_overrides"].get(state_code)
            if state_data:
                rules_list = state_data.get("rules", [])
                is_override = True

        if not rules_list:
            rules_list = self.puc_rules.get("rules", [])
            is_override = False

        # Find matching rule in dataset
        matched_rule = None
        for r in rules_list:
            if (r.get("vehicle_type", "").lower() == vehicle_type.lower() and 
                r.get("fuel_type", "").lower() == fuel_type.lower() and 
                r.get("vehicle_age_years") == age_bracket):
                matched_rule = r
                break

        # Fallback to default central rules if not matched in state override
        if not matched_rule and is_override:
            for r in self.puc_rules.get("rules", []):
                if (r.get("vehicle_type", "").lower() == vehicle_type.lower() and 
                    r.get("fuel_type", "").lower() == fuel_type.lower() and 
                    r.get("vehicle_age_years") == age_bracket):
                    matched_rule = r
                    break

        if not matched_rule:
            return {
                "is_valid": False,
                "error": f"No PUC rule matched for type={vehicle_type}, fuel={fuel_type}, age={age_bracket}",
                "days_remaining": 0,
                "applicable_fine": {
                    "fine_amount": self.puc_rules.get("default_fine_inr", 10000),
                    "section": self.puc_rules.get("fine_section", "Section 190(2) MV Act"),
                    "reason": "Missing or non-compliant PUC details"
                }
            }

        # Check for bans (e.g. older combustion engines in Delhi)
        if matched_rule.get("is_banned", False):
            return {
                "is_valid": False,
                "days_remaining": 0,
                "banned": True,
                "notes": matched_rule.get("notes", "Vehicle is banned in this state."),
                "applicable_fine": {
                    "fine_amount": self.puc_rules.get("default_fine_inr", 10000),
                    "section": self.puc_rules.get("fine_section", "Section 190(2) MV Act"),
                    "reason": f"BANNED VEHICLE: {matched_rule.get('notes')}"
                }
            }

        # Check for exemption (e.g. Electric vehicles)
        if matched_rule.get("exempt", False):
            return {
                "is_valid": True,
                "days_remaining": 99999,
                "exempt": True,
                "notes": matched_rule.get("notes", "Exempt from emissions testing."),
                "applicable_fine": None
            }

        # Calculate expiry date
        validity_months = matched_rule.get("renewal_validity_months", 6)
        if age_bracket == "0-1":
            validity_months = matched_rule.get("initial_validity_months", 12)

        # Handle calendar month arithmetic
        year = puc_date.year + (puc_date.month + validity_months - 1) // 12
        month = (puc_date.month + validity_months - 1) % 12 + 1
        
        # Prevent month day overflows (e.g. Jan 31st + 1 month != Feb 31st)
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        day = min(puc_date.day, last_day)
        expiry_date = date(year, month, day)

        current_date = date.today()
        days_remaining = (expiry_date - current_date).days
        is_valid = days_remaining >= 0

        applicable_fine = None
        if not is_valid:
            applicable_fine = {
                "fine_amount": self.puc_rules.get("default_fine_inr", 10000),
                "section": self.puc_rules.get("fine_section", "Section 190(2) MV Act"),
                "reason": "PUC Certificate has expired"
            }

        return {
            "is_valid": is_valid,
            "days_remaining": days_remaining,
            "expiry_date": expiry_date.isoformat(),
            "notes": matched_rule.get("notes", ""),
            "applicable_fine": applicable_fine
        }

    def check_insurance_validity(self, policy_expiry_date: Any, company_code: str = None) -> dict:
        """
        Validates insurance validity status and pulls matching insurer details using IIB registry codes.
        
        Returns:
            dict: {
                "is_valid": bool,
                "days_remaining": int,
                "expiry_date": str (ISO date),
                "company_info": dict or None,
                "applicable_fine": dict or None
            }
        """
        try:
            expiry_date = self._parse_date(policy_expiry_date)
        except Exception as e:
            fine_config = self.insurance_rules.get("fine_for_no_insurance", {})
            return {
                "is_valid": False,
                "error": f"Invalid policy_expiry_date: {e}",
                "days_remaining": 0,
                "company_info": None,
                "applicable_fine": {
                    "fine_amount": fine_config.get("first_offence_inr", 2000),
                    "section": fine_config.get("section", "Section 196 MV Act"),
                    "reason": f"Malformed or missing policy expiry date: {e}"
                }
            }

        current_date = date.today()
        days_remaining = (expiry_date - current_date).days
        is_valid = days_remaining >= 0

        # Insurer verification lookup (matches IIB code or Company short-code)
        company_info = None
        if company_code:
            code_str = str(company_code).strip()
            for comp in self.insurance_rules.get("companies", []):
                if (comp.get("iib_code") == code_str or 
                    comp.get("short_code", "").lower() == code_str.lower()):
                    company_info = comp
                    break

        applicable_fine = None
        if not is_valid:
            fine_config = self.insurance_rules.get("fine_for_no_insurance", {})
            applicable_fine = {
                "fine_amount": fine_config.get("first_offence_inr", 2000),
                "section": fine_config.get("section", "Section 196 MV Act"),
                "imprisonment_possible": fine_config.get("imprisonment_possible", True),
                "subsequent_offence_fine": fine_config.get("subsequent_offence_inr", 4000),
                "reason": "Vehicle insurance policy has expired"
            }

        return {
            "is_valid": is_valid,
            "days_remaining": days_remaining,
            "expiry_date": expiry_date.isoformat(),
            "company_info": company_info,
            "applicable_fine": applicable_fine
        }

    def check_fitness_validity(self, vehicle_category: str, fitness_expiry_date: Any) -> dict:
        """
        Validates commercial or private fitness certificates based on vehicle categories.
        
        Returns:
            dict: {
                "is_valid": bool,
                "days_remaining": int,
                "expiry_date": str (ISO date),
                "notes": str,
                "applicable_fine": dict or None
            }
        """
        try:
            expiry_date = self._parse_date(fitness_expiry_date)
        except Exception as e:
            return {
                "is_valid": False,
                "error": f"Invalid fitness_expiry_date: {e}",
                "days_remaining": 0,
                "applicable_fine": {
                    "fine_amount": self.fitness_rules.get("fine_inr", 2000),
                    "section": self.fitness_rules.get("fine_section", "Section 190(2) MV Act"),
                    "reason": f"Malformed or missing fitness expiry date: {e}"
                }
            }

        # Substring/fuzzy match category name
        matched_rule = None
        category_lower = vehicle_category.lower().replace(" ", "").replace("-", "")
        for r in self.fitness_rules.get("rules", []):
            rule_cat = r.get("vehicle_category", "").lower().replace(" ", "").replace("-", "")
            if rule_cat in category_lower or category_lower in rule_cat:
                matched_rule = r
                break

        if not matched_rule:
            matched_rule = {
                "vehicle_category": vehicle_category,
                "exempt": False,
                "notes": "Custom vehicle class"
            }

        # Check exemption (e.g. Two-Wheelers are exempt from standard commercial fitness certificate rules)
        if matched_rule.get("exempt", False):
            return {
                "is_valid": True,
                "days_remaining": 99999,
                "exempt": True,
                "notes": matched_rule.get("notes", "Exempt from commercial annual fitness certification."),
                "applicable_fine": None
            }

        current_date = date.today()
        days_remaining = (expiry_date - current_date).days
        is_valid = days_remaining >= 0

        applicable_fine = None
        if not is_valid:
            applicable_fine = {
                "fine_amount": self.fitness_rules.get("fine_inr", 2000),
                "section": self.fitness_rules.get("fine_section", "Section 190(2) MV Act"),
                "reason": "Fitness certificate has expired"
            }

        return {
            "is_valid": is_valid,
            "days_remaining": days_remaining,
            "expiry_date": expiry_date.isoformat(),
            "notes": matched_rule.get("notes", ""),
            "applicable_fine": applicable_fine
        }

    def check_dl_category(self, dl_categories: list, vehicle_being_driven: str) -> dict:
        """
        Checks if a driver's licensed endorsements authorize driving a specific vehicle class.
        
        Returns:
            dict: {
                "is_authorized": bool,
                "vehicle_driven": str,
                "held_categories": list,
                "violation_if_any": dict or None
            }
        """
        held = [str(cat).strip().upper() for cat in dl_categories]
        v_driven = str(vehicle_being_driven).strip().upper()

        # Authorization mapping matrix
        required_codes = []
        if v_driven in ["MCWOG", "SCOOTER", "GEARLESS MOTORCYCLE", "TWO-WHEELER (AUTOMATIC)"]:
            required_codes = ["MCWOG", "MCWG"]
        elif v_driven in ["MCWG", "MOTORCYCLE", "TWO-WHEELER (GEAR)"]:
            required_codes = ["MCWG"]
        elif v_driven in ["LMV", "PRIVATE CAR", "CAR", "JEEP", "SUV"]:
            required_codes = ["LMV", "LMV-TR", "TRANSPORT", "MGV", "HMV", "HGMV", "HPMV"]
        elif v_driven in ["LMV-TR", "TAXI", "CAB", "COMMERCIAL CAR", "DELIVERY VAN"]:
            required_codes = ["LMV-TR", "TRANSPORT", "MGV", "HMV", "HGMV", "HPMV"]
        elif v_driven in ["MGV", "MEDIUM GOODS VEHICLE", "TEMPO", "TRUCK (MEDIUM)"]:
            required_codes = ["MGV", "TRANSPORT", "HMV", "HGMV"]
        elif v_driven in ["HMV", "HEAVY MOTOR VEHICLE", "HEAVY TRUCK", "BUS"]:
            required_codes = ["HMV", "TRANSPORT", "HGMV", "HPMV"]
        elif v_driven in ["HGMV", "HEAVY GOODS MOTOR VEHICLE", "CARGO TRUCK"]:
            required_codes = ["HGMV", "HMV", "TRANSPORT"]
        elif v_driven in ["HPMV", "HEAVY PASSENGER MOTOR VEHICLE", "PASSENGER BUS"]:
            required_codes = ["HPMV", "HMV", "TRANSPORT"]
        elif v_driven in ["ARTICULATED VEHICLE", "TRAILER TRUCK"]:
            required_codes = ["ARTICULATED VEHICLE", "TRANSPORT"]
        else:
            required_codes = [v_driven]

        is_authorized = False
        for code in required_codes:
            if code in held:
                is_authorized = True
                break

        violation_if_any = None
        if not is_authorized:
            violation_list = self.dl_rules.get("violation_implications", [])
            matched_violation = None
            
            # Scenario keyword matching logic
            keyword = "without licence"
            if len(held) > 0:
                keyword = "wrong category"
                
            for viol in violation_list:
                scenario_lower = viol.get("scenario", "").lower()
                if keyword in scenario_lower:
                    matched_violation = viol
                    break
                    
            if not matched_violation and violation_list:
                matched_violation = violation_list[0]

            violation_if_any = {
                "scenario": matched_violation.get("scenario", f"Driving {vehicle_being_driven} without proper endorsement") if matched_violation else f"Driving {vehicle_being_driven} without proper endorsement",
                "applicable_section": matched_violation.get("applicable_section", "Section 3 / Section 181") if matched_violation else "Section 3 / Section 181",
                "fine_inr": matched_violation.get("fine_inr", 5000) if matched_violation else 5000,
                "imprisonment_months": matched_violation.get("imprisonment_months", 3) if matched_violation else 3,
                "notes": matched_violation.get("notes", "No valid DL category covers the vehicle driven.") if matched_violation else "No valid DL category covers the vehicle driven."
            }

        return {
            "is_authorized": is_authorized,
            "vehicle_driven": vehicle_being_driven,
            "held_categories": dl_categories,
            "violation_if_any": violation_if_any
        }

    def validate_all_documents(self, vehicle_info: dict) -> dict:
        """
        Runs comprehensive validation checks for PUC, Insurance, Fitness, and Driving License.
        
        Returns:
            dict: Master compliance ledger with aggregate fine and detailed report.
        """
        vehicle_type = vehicle_info.get("vehicle_type", "LMV")
        fuel_type = vehicle_info.get("fuel_type", "Petrol")
        vehicle_age_years = vehicle_info.get("vehicle_age_years", 1.0)
        state = vehicle_info.get("state", "ALL")

        # 1. PUC Verification
        last_puc_date = vehicle_info.get("last_puc_date")
        if last_puc_date:
            puc_check = self.check_puc_validity(
                vehicle_type=vehicle_type,
                fuel_type=fuel_type,
                vehicle_age_years=vehicle_age_years,
                last_puc_date=last_puc_date,
                state=state
            )
        else:
            puc_check = {
                "is_valid": False,
                "days_remaining": 0,
                "error": "No PUC date provided",
                "applicable_fine": {
                    "fine_amount": self.puc_rules.get("default_fine_inr", 10000),
                    "section": self.puc_rules.get("fine_section", "Section 190(2) MV Act"),
                    "reason": "Missing PUC certificate"
                }
            }

        # 2. Insurance Verification
        policy_expiry_date = vehicle_info.get("policy_expiry_date")
        company_code = vehicle_info.get("insurance_company_code")
        if policy_expiry_date:
            insurance_check = self.check_insurance_validity(
                policy_expiry_date=policy_expiry_date,
                company_code=company_code
            )
        else:
            fine_config = self.insurance_rules.get("fine_for_no_insurance", {})
            insurance_check = {
                "is_valid": False,
                "days_remaining": 0,
                "error": "No insurance policy expiry date provided",
                "applicable_fine": {
                    "fine_amount": fine_config.get("first_offence_inr", 2000),
                    "section": fine_config.get("section", "Section 196 MV Act"),
                    "imprisonment_possible": fine_config.get("imprisonment_possible", True),
                    "reason": "Missing insurance certificate"
                }
            }

        # 3. Fitness Verification
        fitness_expiry_date = vehicle_info.get("fitness_expiry_date")
        vehicle_category = vehicle_info.get("vehicle_category", vehicle_type)
        if fitness_expiry_date:
            fitness_check = self.check_fitness_validity(
                vehicle_category=vehicle_category,
                fitness_expiry_date=fitness_expiry_date
            )
        else:
            is_exempt = False
            for r in self.fitness_rules.get("rules", []):
                if r.get("vehicle_category", "").lower() == vehicle_category.lower() and r.get("exempt", False):
                    is_exempt = True
                    break
            
            if is_exempt:
                fitness_check = {
                    "is_valid": True,
                    "days_remaining": 99999,
                    "exempt": True,
                    "applicable_fine": None
                }
            else:
                fitness_check = {
                    "is_valid": False,
                    "days_remaining": 0,
                    "error": "No fitness expiry date provided",
                    "applicable_fine": {
                        "fine_amount": self.fitness_rules.get("fine_inr", 2000),
                        "section": self.fitness_rules.get("fine_section", "Section 190(2) MV Act"),
                        "reason": "Missing fitness certificate"
                    }
                }

        # 4. Driver License Endorsement Verification
        dl_categories = vehicle_info.get("dl_categories", [])
        vehicle_being_driven = vehicle_info.get("vehicle_being_driven")
        if vehicle_being_driven:
            dl_check = self.check_dl_category(
                dl_categories=dl_categories,
                vehicle_being_driven=vehicle_being_driven
            )
        else:
            dl_check = {
                "is_authorized": True,
                "notes": "No vehicle being driven specified, skipping DL authorization check."
            }

        # Combine checks
        detailed_checks = {
            "puc": puc_check,
            "insurance": insurance_check,
            "fitness": fitness_check,
            "driving_license": dl_check
        }

        # Aggregate total fine and violation list
        violations = []
        total_fine_inr = 0

        if not puc_check.get("is_valid", False):
            fine_info = puc_check.get("applicable_fine")
            if fine_info:
                violations.append({
                    "document": "PUC",
                    "reason": fine_info.get("reason", "Expired or missing PUC"),
                    "section": fine_info.get("section"),
                    "fine_inr": fine_info.get("fine_amount", 0)
                })
                total_fine_inr += fine_info.get("fine_amount", 0)

        if not insurance_check.get("is_valid", False):
            fine_info = insurance_check.get("applicable_fine")
            if fine_info:
                violations.append({
                    "document": "Insurance",
                    "reason": fine_info.get("reason", "Expired or missing Insurance"),
                    "section": fine_info.get("section"),
                    "fine_inr": fine_info.get("fine_amount", 0)
                })
                total_fine_inr += fine_info.get("fine_amount", 0)

        if not fitness_check.get("is_valid", False):
            fine_info = fitness_check.get("applicable_fine")
            if fine_info:
                violations.append({
                    "document": "Fitness",
                    "reason": fine_info.get("reason", "Expired or missing Fitness"),
                    "section": fine_info.get("section"),
                    "fine_inr": fine_info.get("fine_amount", 0)
                })
                total_fine_inr += fine_info.get("fine_amount", 0)

        if not dl_check.get("is_authorized", True):
            viol_info = dl_check.get("violation_if_any")
            if viol_info:
                violations.append({
                    "document": "Driving License",
                    "reason": viol_info.get("scenario", "Unauthorized driving category"),
                    "section": viol_info.get("applicable_section"),
                    "fine_inr": viol_info.get("fine_inr", 0)
                })
                total_fine_inr += viol_info.get("fine_inr", 0)

        all_clear = len(violations) == 0

        return {
            "all_clear": all_clear,
            "total_fine_inr": total_fine_inr,
            "violations_detected": violations,
            "detailed_checks": detailed_checks
        }
