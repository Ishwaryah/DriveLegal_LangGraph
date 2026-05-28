import os
import sys
import calendar
from datetime import date, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.document_validator import DocumentValidator


def test_expired_puc():
    validator = DocumentValidator()
    target_expiry = date.today() - timedelta(days=30)
    year = target_expiry.year - (1 if target_expiry.month <= 6 else 0)
    month = (target_expiry.month - 6 - 1) % 12 + 1
    day = min(target_expiry.day, calendar.monthrange(year, month)[1])
    last_puc_date = date(year, month, day)

    result = validator.check_puc_validity(
        vehicle_type="Two-Wheeler",
        fuel_type="Petrol",
        vehicle_age_years=3,
        last_puc_date=last_puc_date,
    )
    fine = result.get("applicable_fine")
    assert result.get("is_valid") is False
    assert fine is not None
    assert fine.get("fine_amount") == 10000


def test_valid_insurance():
    validator = DocumentValidator()
    expiry_date = date.today() + timedelta(days=60)
    result = validator.check_insurance_validity(
        policy_expiry_date=expiry_date,
        company_code="ICICIL",
    )
    comp = result.get("company_info")
    assert result.get("is_valid") is True
    assert comp is not None
    assert comp.get("short_code") == "ICICIL"


def test_expired_fitness_certificate():
    validator = DocumentValidator()
    expiry_date = date.today() - timedelta(days=10)
    result = validator.check_fitness_validity(
        vehicle_category="Commercial Goods Vehicle",
        fitness_expiry_date=expiry_date,
    )
    fine = result.get("applicable_fine")
    assert result.get("is_valid") is False
    assert fine is not None
    assert fine.get("fine_amount") == 2000


def test_dl_category_mismatch():
    validator = DocumentValidator()
    result = validator.check_dl_category(
        dl_categories=["LMV"],
        vehicle_being_driven="HMV",
    )
    viol = result.get("violation_if_any")
    assert result.get("is_authorized") is False
    assert viol is not None
    assert "wrong category" in viol.get("scenario").lower()


def test_all_documents_valid():
    validator = DocumentValidator()
    vehicle_info = {
        "vehicle_type": "LMV",
        "fuel_type": "Petrol",
        "vehicle_age_years": 3,
        "last_puc_date": date.today() - timedelta(days=60),
        "policy_expiry_date": date.today() + timedelta(days=120),
        "insurance_company_code": "NIC",
        "vehicle_category": "Private Cars",
        "fitness_expiry_date": date.today() + timedelta(days=360),
        "dl_categories": ["LMV"],
        "vehicle_being_driven": "LMV",
    }
    result = validator.validate_all_documents(vehicle_info)
    assert result.get("all_clear") is True
    assert result.get("total_fine_inr") == 0
    assert len(result.get("violations_detected")) == 0


def test_delhi_banned_diesel_vehicle():
    validator = DocumentValidator()
    result = validator.check_puc_validity(
        vehicle_type="LMV",
        fuel_type="Diesel",
        vehicle_age_years=16,
        last_puc_date=date.today() - timedelta(days=30),
        state="DL",
    )
    assert result.get("banned") is True
    assert result.get("is_valid") is False


def test_delhi_stricter_puc_renewal():
    validator = DocumentValidator()
    last_puc_9m_ago = date.today() - timedelta(days=9 * 30)
    default_result = validator.check_puc_validity(
        vehicle_type="LMV", fuel_type="Petrol", vehicle_age_years=3,
        last_puc_date=last_puc_9m_ago, state="ALL",
    )
    delhi_result = validator.check_puc_validity(
        vehicle_type="LMV", fuel_type="Petrol", vehicle_age_years=3,
        last_puc_date=last_puc_9m_ago, state="DL",
    )
    assert default_result.get("is_valid") is True
    assert delhi_result.get("is_valid") is False
