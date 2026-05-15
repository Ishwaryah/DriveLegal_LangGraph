"""
Legal Formatter
===============
Formats raw violation data (rule + fine dicts) into a structured markdown
string for display in the chatbot.  No heavy dependencies — stdlib only.
"""

from difflib import get_close_matches
from typing import Any, Dict, List, Optional


# ── Localised UI labels ────────────────────────────────────────────────────────

_LABELS: Dict[str, Dict[str, str]] = {
    "en": {
        "legal_ref":   "Legal Reference",
        "fine":        "Fine",
        "compound_y":  "Compoundable: Yes",
        "compound_n":  "Compoundable: No – court appearance mandatory",
        "settle":      "can be settled on-spot or online",
        "additional":  "Additional Penalty",
        "verify":      "Verify at official portal",
    },
    "hi": {
        "legal_ref":   "कानूनी संदर्भ",
        "fine":        "जुर्माना",
        "compound_y":  "समझौता योग्य: हाँ",
        "compound_n":  "समझौता योग्य: नहीं – अदालत में उपस्थिति अनिवार्य",
        "settle":      "– ऑन-स्पॉट या ऑनलाइन निपटाया जा सकता है",
        "additional":  "अतिरिक्त दंड",
        "verify":      "आधिकारिक पोर्टल पर सत्यापित करें",
    },
    "ta": {
        "legal_ref":   "சட்ட குறிப்பு",
        "fine":        "அபராதம்",
        "compound_y":  "சமரசம் செய்யலாம்: ஆம்",
        "compound_n":  "சமரசம் செய்யலாம்: இல்லை – நீதிமன்றத்தில் ஆஜராக வேண்டும்",
        "settle":      "– இடத்திலேயே அல்லது ஆன்லைனில் தீர்க்கலாம்",
        "additional":  "கூடுதல் தண்டனை",
        "verify":      "அதிகாரப்பூர்வ தளத்தில் சரிபார்க்கவும்",
    },
    "ar": {
        "legal_ref":   "المرجع القانوني",
        "fine":        "الغرامة",
        "compound_y":  "قابل للتسوية: نعم",
        "compound_n":  "غير قابل للتسوية – الحضور الإلزامي أمام المحكمة",
        "settle":      "يمكن تسويتها في الموقع أو عبر الإنترنت",
        "additional":  "عقوبة إضافية",
        "verify":      "تحقق من البوابة الرسمية",
    },
}

# Common violation name translations keyed by English title keywords
_VIOLATION_NAMES: Dict[str, Dict[str, str]] = {
    "hi": {
        "no helmet":      "हेलमेट न पहनना",
        "helmet":         "हेलमेट न पहनना",
        "drunk driving":  "नशे में गाड़ी चलाना",
        "drunk":          "नशे में गाड़ी चलाना",
        "overspeeding":   "तेज़ गति से वाहन चलाना",
        "speeding":       "तेज़ गति से वाहन चलाना",
        "no seatbelt":    "सीट बेल्ट न पहनना",
        "seatbelt":       "सीट बेल्ट न पहनना",
        "mobile phone":   "गाड़ी चलाते समय फोन का उपयोग",
        "phone":          "गाड़ी चलाते समय फोन का उपयोग",
        "no insurance":   "बीमा न होना",
        "insurance":      "बीमा न होना",
        "no license":     "बिना लाइसेंस के गाड़ी चलाना",
        "license":        "बिना लाइसेंस के गाड़ी चलाना",
        "signal jumping": "सिग्नल तोड़ना",
        "red light":      "लाल बत्ती पर रुकना",
    },
    "ta": {
        "no helmet":      "தலைக்கவசம் அணியாமல் இருத்தல்",
        "helmet":         "தலைக்கவசம் அணியாமல் இருத்தல்",
        "drunk driving":  "குடிபோதையில் வாகனம் ஓட்டுதல்",
        "drunk":          "குடிபோதையில் வாகனம் ஓட்டுதல்",
        "overspeeding":   "அதிவேகமாக வாகனம் ஓட்டுதல்",
        "speeding":       "அதிவேகமாக வாகனம் ஓட்டுதல்",
        "no seatbelt":    "சீட் பெல்ட் அணியாமல் இருத்தல்",
        "mobile phone":   "வாகனம் ஓட்டும்போது தொலைபேசி பயன்படுத்துதல்",
        "no insurance":   "காப்பீடு இல்லாமல் வாகனம் ஓட்டுதல்",
        "no license":     "உரிமம் இல்லாமல் வாகனம் ஓட்டுதல்",
        "signal jumping": "சிக்னல் மீறுதல்",
        "red light":      "சிவப்பு விளக்கு மீறுதல்",
        "juvenile":       "வயதுக்கு வராத நபர் வாகனம் ஓட்டுதல்",
    },
    "ar": {
        "no helmet":      "عدم ارتداء الخوذة",
        "helmet":         "عدم ارتداء الخوذة",
        "drunk driving":  "القيادة تحت تأثير الكحول",
        "drunk":          "القيادة تحت تأثير الكحول",
        "overspeeding":   "تجاوز السرعة المحددة",
        "speeding":       "تجاوز السرعة المحددة",
        "no seatbelt":    "عدم ارتداء حزام الأمان",
        "mobile phone":   "استخدام الهاتف أثناء القيادة",
        "no insurance":   "القيادة بدون تأمين",
        "no license":     "القيادة بدون رخصة",
        "signal jumping": "تجاوز إشارة المرور الحمراء",
        "red light":      "تجاوز الإشارة الحمراء",
        "reckless":       "القيادة المتهورة",
    },
}


def _translate_title(title: str, lang: str) -> str:
    """Return a translated violation title for *lang*, or the original if no match."""
    if lang not in _VIOLATION_NAMES:
        return title
    title_lower = title.lower()
    for keyword, translation in _VIOLATION_NAMES[lang].items():
        if keyword in title_lower:
            return translation
    return title


# ── Public API ─────────────────────────────────────────────────────────────────

def format_legal_response(
    violation_row: Dict[str, Any],
    country: str = "IN",
    lang: str = "en",
) -> str:
    """
    Convert a merged violation dict into a rich markdown block.

    Expected keys in violation_row (all optional):
      title, section, act, min_fine, max_fine, vehicle_type,
      compoundable, compounding_fee, imprisonment, notes/description
    """
    lines: List[str] = []
    currency = _currency_symbol(country)
    lbl = _LABELS.get(lang) or _LABELS["en"]

    # ── Header ────────────────────────────────────────────────────────────────
    raw_title = violation_row.get("title") or "Traffic Violation"
    title = _translate_title(raw_title, lang) if lang != "en" else raw_title
    lines.append(f"🚦 **{title}**")

    # ── Legal reference ───────────────────────────────────────────────────────
    section = (
        violation_row.get("section")
        or violation_row.get("section_ref")
        or ""
    ).strip()
    act = violation_row.get("act") or "Motor Vehicles (Amendment) Act 2019"
    if section:
        lines.append(f"📋 {lbl['legal_ref']}: {act}, {section}")
    else:
        lines.append(f"📋 {lbl['legal_ref']}: {act}")

    # ── Fine range ────────────────────────────────────────────────────────────
    min_fine = (
        violation_row.get("min_fine")
        or violation_row.get("amount_inr")
        or violation_row.get("base_amount")
    )
    max_fine = (
        violation_row.get("max_fine")
        or violation_row.get("repeat_amount_inr")
        or min_fine
    )
    vehicle_type = (
        violation_row.get("vehicle_type")
        or violation_row.get("vehicle_class")
        or "All vehicles"
    )
    if min_fine is not None:
        if max_fine and max_fine != min_fine:
            lines.append(
                f"💰 {lbl['fine']}: {currency}{min_fine:,} – {currency}{max_fine:,}"
                f" ({vehicle_type})"
            )
        else:
            lines.append(f"💰 {lbl['fine']}: {currency}{min_fine:,} ({vehicle_type})")
    else:
        lines.append(f"💰 {lbl['fine']}: {lbl['verify']}")

    # ── Compoundable ──────────────────────────────────────────────────────────
    compoundable = violation_row.get("compoundable")
    compounding_fee = violation_row.get("compounding_fee")
    if compoundable is True:
        if compounding_fee is not None:
            lines.append(f"✅ {lbl['compound_y']} – {currency}{compounding_fee:,} {lbl['settle']}")
        else:
            lines.append(f"✅ {lbl['compound_y']} – {lbl['settle']}")
    elif compoundable is False:
        lines.append(f"❌ {lbl['compound_n']}")
    # omit if compoundable is None (status unknown)

    # ── Imprisonment / additional penalties ───────────────────────────────────
    imprisonment = violation_row.get("imprisonment")
    if imprisonment and imprisonment is not False:
        imp_text = _format_imprisonment(imprisonment)
        if imp_text:
            lines.append(f"⚖️ {lbl['additional']}: {imp_text}")

    # ── Notes / description ───────────────────────────────────────────────────
    notes = (violation_row.get("notes") or violation_row.get("description") or "").strip()
    if notes:
        lines.append(f"ℹ️ {notes[:2000]}")

    return "\n".join(lines)


def suggest_violations(query: str, all_titles: List[str], n: int = 3) -> List[str]:
    """
    Return up to n closest violation title matches using difflib (stdlib only).
    cutoff=0.3 keeps suggestions broad enough to be useful for short misspellings.
    """
    if not query or not all_titles:
        return []

    q_lower = query.lower()
    lowered = [t.lower() for t in all_titles]

    matches = get_close_matches(q_lower, lowered, n=n, cutoff=0.3)

    # Map back to original casing
    title_map = {t.lower(): t for t in all_titles}
    return [title_map[m] for m in matches if m in title_map]


def build_violation_row(
    rule_data: Optional[Dict[str, Any]],
    fine_data: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Merge rule_data (from RulesLoader) and fine_data (from ResponseBuilder)
    into a flat violation_row suitable for format_legal_response().
    """
    row: Dict[str, Any] = {}

    if rule_data:
        row["title"] = rule_data.get("title")
        row["section"] = rule_data.get("section") or rule_data.get("section_ref")
        row["act"] = rule_data.get("act")
        row["compoundable"] = rule_data.get("compoundable")
        row["compounding_fee"] = rule_data.get("compounding_fee")
        row["imprisonment"] = rule_data.get("imprisonment")
        row["description"] = rule_data.get("description")
        row["vehicle_class"] = (rule_data.get("vehicle_classes") or ["All vehicles"])[0]

        # Extract fine range from national_fine (schema v2.0)
        nf = rule_data.get("national_fine")
        if nf and isinstance(nf, dict):
            fo = nf.get("first_offence") or {}
            su = nf.get("subsequent") or {}
            row["min_fine"] = fo.get("fine_min")
            row["max_fine"] = su.get("fine_max") or fo.get("fine_max")

    if fine_data:
        # Fine-db values override rule-derived values (more authoritative)
        if fine_data.get("amount_inr") is not None:
            row["amount_inr"] = fine_data["amount_inr"]
            row.setdefault("min_fine", fine_data["amount_inr"])
        if fine_data.get("repeat_amount_inr") is not None:
            row["repeat_amount_inr"] = fine_data["repeat_amount_inr"]
            row.setdefault("max_fine", fine_data["repeat_amount_inr"])
        if fine_data.get("section_ref"):
            row.setdefault("section", fine_data["section_ref"])
        row["vehicle_type"] = fine_data.get("vehicle_class") or row.get("vehicle_class")

    return row


# ── Helpers ────────────────────────────────────────────────────────────────────

def _currency_symbol(country: str) -> str:
    return {
        "IN": "₹",
        "AE": "AED ",
        "SG": "S$",
        "GB": "£",
        "US": "$",
    }.get((country or "IN").upper(), "₹")


def _format_imprisonment(imprisonment: Any) -> str:
    if isinstance(imprisonment, str):
        return imprisonment
    if isinstance(imprisonment, dict):
        parts: List[str] = []
        first = imprisonment.get("first_offence_months")
        sub   = imprisonment.get("subsequent_months")
        extra = imprisonment.get("note")
        if first:
            parts.append(f"up to {first} months (first offence)")
        if sub:
            parts.append(f"up to {sub} months (subsequent)")
        if extra:
            parts.append(extra)
        return "; ".join(parts)
    return ""
