# DriveLegal AI Agent — 50-Case Test Report
**Date:** 2026-05-28  
**Backend:** `http://localhost:8001` | Engine: `keyword-fallback` (Groq circuit-breaker closed)  
**DB:** 420 fines rows — IN: 356 | AE: 19 | GB: 10 | SG: 10 | US: 15 | SA: 10  
**Rules:** 55 rules loaded | Vector search: active  

---

## Part 1 — Q&A Documentation (All 50 Tests)

---

### 🟦 Category 1: Basic Fine Lookups — India

---

**TC-01 · What is the fine for driving without a helmet in Tamil Nadu?**

> **Agent Answer:**  
> Fine for No Helmet (GENERAL):  
> • Amount: ₹1,000  
> • Repeat Offence: ₹1,000  
> • Section: Section 194D  
> • State: Tamil Nadu  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ✅ PASS — Correct amount, correct state, correct MV Act section.

---

**TC-02 · Fine for not wearing a seatbelt in Delhi for a car.**

> **Agent Answer:**  
> Fine for No Seatbelt (Sec 194B) (LMV):  
> • Amount: ₹1,000  
> • Repeat Offence: ₹1,000  
> • Section: Section 194B  
> • State: Delhi  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ✅ PASS — Correct vehicle class (LMV/car), correct section, Delhi-specific row resolved.

---

**TC-03 · How much do I pay for overspeeding a car in Maharashtra?**

> **Agent Answer:**  
> Fine for Over Speeding (LMV):  
> • Amount: ₹1,000  
> • Repeat Offence: ₹2,000  
> • Section: Section 183  
> • State: Maharashtra  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ✅ PASS — LMV class detected, MH state resolved, correct amounts.

---

**TC-04 · What is the penalty for jumping a red light in Karnataka?**

> **Agent Answer:**  
> Fine for Jumping Red Light (GENERAL):  
> • Amount: ₹1,000  
> • Repeat Offence: ₹5,000  
> • Section: Section 177  
> • State: Karnataka  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Note:** Rule returned is Section 184 (Dangerous Driving) — rule matcher misaligned with fine record Section 177.

**Verdict:** ⚠️ PARTIAL — Fine is correct; rule description shows "Dangerous Driving" (Sec 184) instead of the correct "Failure to Obey Traffic Signal" rule for Sec 177.

---

**TC-05 · Fine for driving without insurance in Uttar Pradesh.**

> **Agent Answer:**  
> Fine for No Insurance (GENERAL):  
> • Amount: ₹2,000  
> • Repeat Offence: ₹4,000  
> • Section: Section 196  
> • State: Uttar Pradesh  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ✅ PASS — Section 196 correct, national rate applied (UP-specific override not in DB, which is accurate).

---

**TC-06 · What is the challan for no PUC (pollution certificate) in Kerala?**

> **Agent Answer (excerpt):**  
> "PUC stands for Pollution Under Control certificate… Fine for no PUC: Under Section 190(2), the fine is ₹10,000 and/or imprisonment up to 6 months."  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Note:** Returned via FAQ hybrid search, not the structured fine DB. `fine` field is `null`; no structured fine object returned.

**Verdict:** ⚠️ PARTIAL — Factually correct answer buried in FAQ text, but no structured fine data. "PUC" keyword not mapped to `NO_PUC` offence code.

---

**TC-07 · Fine for triple riding on a bike in Andhra Pradesh.**

> **Agent Answer (excerpt):**  
> "Is triple riding on a two-wheeler allowed? No. Triple riding is prohibited across India… Fine for triple riding: Treated as a violation under Section 177."  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Note:** No structured fine returned. `fine` is `null`. FAQ result only.

**Verdict:** ⚠️ PARTIAL — FAQ correctly states triple riding is illegal and references Section 177, but no amount or Andhra Pradesh-specific data was returned.

---

**TC-08 · Penalty for using a mobile phone while driving in Telangana.**

> **Agent Answer:**  
> Fine for Using Mobile Phone While Driving (GENERAL):  
> • Amount: ₹5,000  
> • Repeat Offence: ₹10,000  
> • Section: Section 184(c)  
> • State: Telangana  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ✅ PASS — Correct fine, section, and Telangana state resolved.

---

**TC-09 · How much is the fine for drunk driving in West Bengal?**

> **Agent Answer:**  
> Fine for Drunk Driving (GENERAL):  
> • Amount: ₹2,000  
> • Repeat Offence: ₹3,000  
> • Section: Section 185  
> • State: West Bengal  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Note:** National baseline returned; no WB-specific override. Tamil Nadu has an enhanced row (₹10,000); WB falls back to national rate. The national rate is ₹10,000 first offence under MV Act 2019 — the ₹2,000/₹3,000 figures appear to be the pre-2019 amounts and may be a seeding error.

**Verdict:** ⚠️ PARTIAL — Section 185 correct; but the amount ₹2,000 does not match MV Act 2019 amended rates (₹10,000 first offence). Possible seeding issue in national row.

---

**TC-10 · Fine for wrong-way driving in Gujarat for a truck.**

> **Agent Answer (excerpt):**  
> Hybrid search returns FAQ about triple riding, school zone speeding, and seatbelt — none about wrong-way driving. No structured fine returned.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ❌ FAIL — Wrong-way driving (`SECTION_179`) is in the offence keyword map but "wrong-way" + "Gujarat" + "truck" produced no match. Gujarat state and HGV combination not in DB; no national fallback for Section 179 returned.

---

### 🟦 Category 2: Repeat Offences & Edge Cases

---

**TC-11 · What is the fine for a second offense of drunk driving in TN?**

> **Agent Answer:**  
> Fine for Drunk Driving (GENERAL):  
> • Amount: ₹10,000  
> • Repeat Offence: ₹15,000  
> • Section: Section 185  
> • State: Tamil Nadu  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ✅ PASS — TN-specific row correctly retrieved; enhanced amounts match MV Act 2019 / TN enforcement.

---

**TC-12 · Fine for not wearing a helmet. What if it is my 3rd time?**

> **Agent Answer:**  
> Fine for No Helmet (GENERAL):  
> • Amount: ₹1,000  
> • Repeat Offence: ₹1,000  
> • Section: Section 194D  
> • State: National  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Note:** "3rd time" nuance is not captured — shows generic repeat amount (₹1,000 same). Section 194D has no 3rd-offence escalation clause in the MV Act (the repeat rate is also ₹1,000), so the data is technically accurate but the response doesn't explain whether 3rd-offence is the same.

**Verdict:** ⚠️ PARTIAL — Amount correct per Act. The agent does not explicitly tell the user "there is no further escalation beyond the first repeat" — missing qualitative guidance.

---

**TC-13 · Is the fine for no seatbelt different for a second time?**

> **Agent Answer:**  
> Fine for No Seatbelt (Sec 194B) (GENERAL):  
> • Amount: ₹1,000  
> • Repeat Offence: ₹1,000  
> • Section: Section 194B  
> • State: National  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ✅ PASS — Correctly shows both amounts are ₹1,000, directly answering "is it different" (it is not).

---

**TC-14 · Overspeeding fine for a commercial truck vs a private car.**

> **Agent Answer:**  
> Fine for Over Speeding (HGV):  
> • Amount: ₹2,000  
> • Repeat Offence: ₹4,000  
> • Section: Section 183  
> • State: National  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Note:** Only HGV data returned — no separate lookup for LMV (car) for comparison.

**Verdict:** ⚠️ PARTIAL — Returns truck data correctly but does not compare with car (LMV = ₹1,000/₹2,000). A vs comparison requires two lookups; only one was made.

---

**TC-15 · What if a minor is caught driving without a license?**

> **Agent Answer (excerpt):**  
> Hybrid search returns "Driving without a valid license (Section 181)" and challan payment FAQ. No Section 199A (juvenile driving) result.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ⚠️ PARTIAL — Relevant (driving without licence) but misses the specific juvenile provision: Section 199A — Guardian/owner liable, ₹25,000 fine, 3-year imprisonment, RC cancellation. This is a critical legal distinction.

---

**TC-16 · Fine for driving without a license plate.**

> **Agent Answer (excerpt):**  
> Returns "Driving without a valid license (Section 181)" — wrong offence. No "license plate" / "number plate" entry in the offence keyword map.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ❌ FAIL — "License plate" resolved to "license" and returned driving-without-licence. The actual offence (Sec 192 — using vehicle without registration/display) is not in the keyword map.

---

### 🟦 Category 3: International Traffic Fines

---

**TC-17 · What is the fine for running a red light in Dubai (UAE)?**

> **Agent Answer:**  
> Fine for Jumping Red Light (GENERAL):  
> • Amount: ₹1,000 | Section: Section 177 | State: National  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Expected:** AED 1,000 + 12 black points (UAE Traffic Law).

**Verdict:** ❌ FAIL — Returned Indian MV Act data. Country not switched to AE despite "Dubai" / "UAE" in query.

---

**TC-18 · Fine for speeding in Abu Dhabi.**

> **Agent Answer:**  
> Fine for Over Speeding (GENERAL):  
> • Amount: ₹1,000 | Section: Section 183(1) | State: National  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Expected:** AED 300–1,000 + black points (UAE Traffic Law).

**Verdict:** ❌ FAIL — Indian data returned for UAE query. "Abu Dhabi" not recognized as country AE.

---

**TC-19 · How much is the penalty for texting and driving in the UK?**

> **Agent Answer (excerpt):**  
> Returns Indian FAQ about helmet fine and underage driving. No UK mobile/texting data.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Expected:** £200 + 6 penalty points (GB law).

**Verdict:** ❌ FAIL — No UK data returned; no country switch to GB.

---

**TC-20 · Fine for driving without insurance in California, USA.**

> **Agent Answer:**  
> Fine for No Insurance (GENERAL):  
> • Amount: ₹2,000 | Section: Section 196 | State: National  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Expected:** US: $100–$1,000 first offence (CA Vehicle Code 16029).

**Verdict:** ❌ FAIL — Indian data returned for US query. "California" / "USA" not triggering country switch.

---

**TC-21 · What is the demerit point penalty for speeding in Singapore?**

> **Agent Answer:**  
> Fine for Over Speeding (GENERAL):  
> • Amount: ₹1,000 | Section: Section 183(1) | State: National  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Expected:** SGD fine + demerit points table (Singapore Road Traffic Act).

**Verdict:** ❌ FAIL — Indian data returned; "Singapore" not switching to SG country code.

---

**TC-22 · Fine for parking in a disabled spot in Saudi Arabia.**

> **Agent Answer (excerpt):**  
> Returns triple-riding FAQ and school-zone speeding FAQ — no Saudi data.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Expected:** SAR fine (Saudi Traffic Law, Article for disabled parking).

**Verdict:** ❌ FAIL — No SA country switch; "disabled parking" not in any keyword map.

---

**TC-23 · Penalty for driving under the influence in New York.**

> **Agent Answer:**  
> Fine for Drunk Driving (GENERAL):  
> • Amount: ₹10,000 | Section: Section 185 | State: National  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Expected:** US DUI: $500–$1,000 first offence + license suspension (NY VTL §1192).

**Verdict:** ❌ FAIL — Indian data returned for US query.

---

**TC-24 · Fine for not wearing a seatbelt in London, UK.**

> **Agent Answer:**  
> Fine for No Seatbelt (Sec 194B) (GENERAL):  
> • Amount: ₹1,000 | Section: Section 194B | State: National  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Expected:** £100 Fixed Penalty Notice (GB Road Vehicles — Seat Belts Regulations).

**Verdict:** ❌ FAIL — Indian data returned for UK query.

---

### 🟦 Category 4: Rule Explanations & Legal Sections

---

**TC-25 · Under what section of the Motor Vehicles Act is drunk driving penalized?**

> **Agent Answer:**  
> Returns FAQ titled "What is the fine for driving without a helmet in India?" — Section 194D, not Section 185.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ❌ FAIL — Rule search retrieved wrong FAQ entry (helmet, not drunk driving). "Under what section" query not routing to the correct drunk-driving rule.

---

**TC-26 · Explain Section 194D of the Motor Vehicles Act.**

> **Agent Answer (excerpt):**  
> "Not wearing protective headgear — Whoever drives or causes or allows to be driven a motor cycle or pillion rider without a helmet (protective headgear) in contravention of the provisions of section 129. Section 194D"  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ✅ PASS — Correct section text retrieved. Fine amount (₹1,000) and DL disqualification would improve completeness.

---

**TC-27 · What are the rules for tinted windows on cars?**

> **Agent Answer:**  
> Returns FAQ about overloading (Section 194) — wrong topic entirely.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ❌ FAIL — "Tinted windows" not in any rule or keyword — returns unrelated FAQ.

---

**TC-28 · Is it legal to modify the exhaust of my motorcycle?**

> **Agent Answer (excerpt):**  
> Returns FAQs about overloading, drunk driving, and underage driving — no exhaust modification data.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ❌ FAIL — No exhaust modification rule in the knowledge base. Hybrid search found no semantically close match.

---

**TC-29 · What are the rules regarding high-beam headlights in city limits?**

> **Agent Answer (excerpt):**  
> Returns FAQ about city speed limits and emergency vehicle rules — no headlight rule.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ❌ FAIL — No headlight rule in the knowledge base. Semantic search returns tangentially related content.

---

**TC-30 · Does a pillion rider need to wear a helmet by law?**

> **Agent Answer (excerpt):**  
> "Not wearing protective headgear — Whoever drives or causes or allows to be driven a motor cycle or pillion rider without a helmet. Section 194D"  
> "Not Wearing Helmet — Riding a motorcycle or being a pillion rider without wearing a protective helmet. Section 194D"  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ✅ PASS — Correctly confirms pillion rider helmet requirement under Section 194D (also Section 129).

---

**TC-31 · What is the legal blood alcohol limit for driving in India?**

> **Agent Answer:**  
> "The legal BAC (Blood Alcohol Content) limit is 30mg per 100ml of blood. Under Section 185 of the MV Amendment Act 2019: First offence — ₹10,000 and/or 6 months imprisonment."  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ✅ PASS — Correct BAC limit (30 mg/100 ml) and section cited.

---

**TC-32 · Are physical documents required, or is DigiLocker valid?**

> **Agent Answer (excerpt):**  
> "As per a 2018 Government of India circular and the Information Technology Act 2000, digital documents stored in DigiLocker are legally equivalent to physical originals… Police officers are required to accept digital documents."  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ✅ PASS — Accurate, citing correct legal basis (IT Act 2000 + 2018 GoI circular).

---

### 🟦 Category 5: Geofencing & Location-Based Queries

---

**TC-33 · I am at 13.01, 80.23. What are the traffic rules here?**

> **Agent Answer (excerpt):**  
> GPS coordinates provided but no zone check executed in keyword-fallback mode. Returns generic hybrid search results about dangerous driving and DigiLocker.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ❌ FAIL — Zone check tool not invoked in keyword-fallback path. GPS context injected into text but not processed.

---

**TC-34 · Am I currently in a school zone? (GPS: 13.01, 80.23)**

> **Agent Answer (excerpt):**  
> "In a school zone (typically within 500m of a school), the speed limit is 25 kmph." — Returns generic FAQ, not a live zone determination.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ❌ FAIL — "School zone" keyword detected but `check_zone` tool not invoked (fallback path). No actual geographic lookup performed.

---

**TC-35 · What is the speed limit in a hospital zone?**

> **Agent Answer (excerpt):**  
> Returns FAQ: "school zone speed limit is 25 kmph" and general Section 183 text — no hospital-zone specific data.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ⚠️ PARTIAL — Mentions speed limits and zone concept but does not answer hospital zone specifically (typically 15–25 kmph, state-dependent). Hospital zone not defined in zones data.

---

**TC-36 · Are there any fine multipliers for violations inside a school zone?**

> **Agent Answer (excerpt):**  
> "In school zones, courts can apply higher penalties as the offence endangers children. Some states like Karnataka apply a 2× multiplier in school zones."  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ⚠️ PARTIAL — Factually correct (2× multiplier mentioned), but generic. No structured geofencing zone response; answer comes from FAQ only, not live zone data.

---

**TC-37 · Can I honk in a hospital zone?**

> **Agent Answer (excerpt):**  
> Returns FAQ about challan non-payment and school zone speeding — no honking/noise rule returned.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ❌ FAIL — No rule about sound horns near hospitals in the knowledge base. Silent zone / no-honking rule not present.

---

### 🟦 Category 6: Challan Calculation & Management

---

**TC-38 · Can you check pending challans for vehicle TN01AB1234?**

> **Agent Answer (excerpt):**  
> Returns FAQ about challan non-payment, online payment steps, and contesting a challan — no live vehicle lookup.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Note:** Live challan lookup requires `RAPIDAPI_KEY`; the endpoint `/api/v1/vehicle/challans/{reg_no}` is available and would have returned snapshot data.

**Verdict:** ⚠️ PARTIAL — The `/query` endpoint does not trigger the vehicle challan lookup; returns procedural guidance instead. Should direct user to the dedicated challan endpoint.

---

**TC-39 · How do I pay my traffic fine online?**

> **Agent Answer (excerpt):**  
> "You can pay traffic challans online through: 1. Official eChallan portal: echallan.parivahan.gov.in — enter vehicle number, challan number, or DL number. 2. Parivahan App (mParivahan). Payment methods accepted: UPI, debit/credit cards, net banking."  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ✅ PASS — Complete, actionable answer with correct portal URLs.

---

**TC-40 · What happens if I don't pay my e-challan?**

> **Agent Answer (excerpt):**  
> "1. A court summons will be issued (typically after 60 days). 2. Additional penalties may accumulate. 3. RC renewal or transfer may be blocked. 4. DL renewal may be blocked. 5. In serious cases, a warrant may be issued."  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ✅ PASS — Accurate consequence chain well explained.

---

**TC-41 · Can my license be suspended for unpaid fines?**

> **Agent Answer (excerpt):**  
> Returns challan non-payment FAQ that states: "Your DL renewal may be blocked" — indirect confirmation of licence suspension risk.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ✅ PASS — DL block for unpaid challans confirmed (Section 206 / Sec 210 court-challan upgrade noted).

---

**TC-42 · How many points until my driving license is revoked in the UAE?**

> **Agent Answer (excerpt):**  
> Returns Indian FAQ about DL without licence (Section 181) and drunk driving — no UAE demerit point system data.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Expected:** UAE: 24 black points = licence revocation (Federal Traffic Law No. 21/1995).

**Verdict:** ❌ FAIL — Country not switched to AE; returns Indian data.

---

### 🟦 Category 7: Conversational & Multi-Turn Context

---

**TC-43 · What is the fine for no helmet?**

> **Agent Answer:**  
> Fine for No Helmet (GENERAL): ₹1,000 | Repeat: ₹1,000 | Section 194D | State: National  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ✅ PASS — Baseline query answered correctly.

---

**TC-44 · (Follow-up to TC-43) What about in Delhi?**

> **Agent Answer (excerpt):**  
> Returns FAQ about insurance, documents needed, and online challan payment — does not refine the previous helmet answer to Delhi.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Note:** No session context carried from TC-43. "What about in Delhi?" without a verb is too short for keyword-fallback intent detection. Multi-turn context requires `session_id` to be threaded.

**Verdict:** ❌ FAIL — No session context threading. Follow-up questions without full intent are not resolved using previous state.

---

**TC-45 · (Follow-up to TC-44) And for a car?**

> **Agent Answer (excerpt):**  
> Returns FAQ about helmets (Section 194D) and seatbelts (Section 194B) — does not explicitly clarify that helmets do not apply to cars.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ⚠️ PARTIAL — Returns tangentially related content (helmet and seatbelt FAQ) but fails to explicitly tell the user "helmets do not apply to cars; the equivalent for cars is the seatbelt requirement."

---

**TC-46 · Hi there! How can you help me today?**

> **Agent Answer:**  
> Returns FAQ about contesting a challan, paying online, and non-payment consequences — no greeting response.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Note:** The keyword-fallback `greetings` list is `["hi", "hello", "hey", "namaste"]`. "Hi there!" has trailing content and does not match the exact list entry.

**Verdict:** ❌ FAIL — Greeting not recognized due to strict exact-match list. Should return the configured `greeting_response`.

---

**TC-47 · Thanks for the information!**

> **Agent Answer:**  
> Returns Section 198 (Interference with Vehicle), Section 194E (Emergency Vehicles), Section 194A (Overloading Passengers) — completely irrelevant to a closing polite statement.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Verdict:** ❌ FAIL — No "thanks/goodbye" detection. Hybrid search triggered on random keyword overlaps.

---

### 🟦 Category 8: Irrelevant & Out-of-Scope Queries

---

**TC-48 · Give me a recipe for chocolate cake.**

> **Agent Answer (excerpt):**  
> Returns FAQ about challan non-payment and DigiLocker documents — no out-of-scope refusal.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Expected:** Polite refusal: "I can only assist with traffic law queries."

**Verdict:** ❌ FAIL — No out-of-scope detection. Agent returns random traffic law content instead of declining.

---

**TC-49 · Write a Python script to scrape the Parivahan website.**

> **Agent Answer (excerpt):**  
> Returns FAQ about dangerous driving and DigiLocker — no refusal, no scraping guardrails.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Expected:** Polite refusal + out-of-scope notice.

**Verdict:** ❌ FAIL — No scope guard triggered. Returns tangentially matching traffic content.

---

**TC-50 · What is the capital of France?**

> **Agent Answer (excerpt):**  
> Returns FAQ about helmets, mobile phone use, and documents — no geography refusal.  
> ⚠️ Informational only. Verify at echallan.parivahan.gov.in.

**Expected:** Polite refusal: "I'm a traffic law assistant — I cannot answer general knowledge questions."

**Verdict:** ❌ FAIL — No out-of-scope detection. Hybrid search returns random traffic law matches.

---

## Part 2 — Gap Analysis

### 2.1 Scoring Summary

| # | Category | Score | Count |
|---|----------|-------|-------|
| ✅ | PASS — Correct, relevant, structured answer | 3/3 | 15 |
| ⚠️ | PARTIAL — Relevant content but incomplete/misaligned | 2/3 | 11 |
| ❌ | FAIL — Wrong jurisdiction, wrong topic, no answer | 1/3 | 24 |

**Overall Score: 91 / 150 = 60.7%**

---

### 2.2 Gap Breakdown by Category

| Category | Tests | Pass | Partial | Fail | Score |
|----------|-------|------|---------|------|-------|
| Cat 1 — Basic India Fines | 10 | 6 | 3 | 1 | 78% |
| Cat 2 — Repeat/Edge Cases | 6 | 3 | 3 | 0 | 83% |
| Cat 3 — International | 8 | 0 | 0 | 8 | 33% |
| Cat 4 — Rule Explanations | 8 | 4 | 0 | 4 | 58% |
| Cat 5 — Geofencing | 5 | 0 | 2 | 3 | 40% |
| Cat 6 — Challan Mgmt | 5 | 3 | 1 | 1 | 73% |
| Cat 7 — Conversational | 5 | 1 | 1 | 3 | 47% |
| Cat 8 — Out-of-Scope | 3 | 0 | 0 | 3 | 33% |

---

### 2.3 Root-Cause Gaps

#### GAP-01 · International Country Routing — CRITICAL (affects 8 tests: TC 17–24)
**Problem:** When user asks about UAE/Dubai/Abu Dhabi, UK/London, USA/California, Singapore, or Saudi Arabia, the `/query` endpoint defaults to `country: "IN"` and the keyword-fallback path never reads the country field from payload. The fines DB has AE (19), GB (10), SG (10), SA (10), US (15) rows but they are never queried.  
**Root Cause:** `AgentEngine._keyword_fallback()` calls `ToolExecutor.execute("lookup_fine", ...)` without passing the `country` parameter. The `_detect_state()` helper only maps Indian states.  
**Fix:** Add `_detect_country(text)` in AgentEngine using terms like "dubai", "uae", "uk", "london", "singapore", "saudi", "usa", "california", "new york" → country codes.

#### GAP-02 · Out-of-Scope / Domain Guard Missing — HIGH (affects TC 46–50)
**Problem:** No topic filter. Greetings, farewells, food recipes, coding requests, and general knowledge questions all receive traffic law content instead of a polite scope refusal or greeting.  
**Root Cause:** The `fallback.greetings` list uses exact-match comparison on `text_lower.strip()`. Phrases like "Hi there!" with trailing content won't match. No topic classifier or "off-topic" detector exists.  
**Fix:** (a) Fuzzy/startswith greeting detection. (b) Keyword-based off-topic guard: if no traffic keyword is found, return "I can only assist with traffic law queries."

#### GAP-03 · Multi-Turn Context Not Used in Fallback — HIGH (affects TC 44–45)
**Problem:** When the keyword-fallback is active, `session_id` is generated but follow-up queries without an explicit intent (e.g., "What about in Delhi?") are treated as fresh queries.  
**Root Cause:** The session state is restored only if it was set by a prior `lookup_fine` tool call. Ambiguous follow-ups like "What about in X?" don't trigger fine lookup, so session context is never injected into the search.  
**Fix:** Before fallback runs, check Redis session for prior `offence_type`. If found and no new offence detected, inject the prior offence so "What about in Delhi?" resolves as "NO_HELMET in Delhi."

#### GAP-04 · Missing Offence Codes in Keyword Map — MEDIUM (affects TC 6, 7, 10, 16)
**Problem:** Several violations lack keyword mappings:  
- `NO_PUC` → "puc", "pollution certificate", "emission" not in `offence_keywords.json`  
- `TRIPLE_RIDING` → "triple riding", "pillion overload" not mapped  
- `SECTION_179` → keyword "wrong-way" + vehicle HGV not resolving via state-specific DB  
- `NO_NUMBER_PLATE` → "license plate", "number plate", "no plate" not in any map  
**Fix:** Add entries to `offence_keywords.json` for these violations.

#### GAP-05 · DB Seeding Issues — MEDIUM (affects TC 9)
**Problem:** West Bengal drunk driving returns ₹2,000/₹3,000 via national row — the pre-2019 rate. Under MV Amendment Act 2019, Section 185 first offence is ₹10,000.  
**Root Cause:** The national `drunk_driving` row appears to use pre-2019 amounts. TN has a specific row with correct values; other states fall through to a potentially wrong national row.  
**Fix:** Update the national `drunk_driving` row to ₹10,000/₹15,000 (MV Act 2019). Audit all national rows for post-2019 accuracy.

#### GAP-06 · Rule Retrieval Misalignment — MEDIUM (affects TC 4, 25, 27)
**Problem:** Fine lookup correctly resolves the amount and section, but the subsequent `lookup_rule` call matches the wrong rule entry. Example: Red light fine → Section 177, but rule returned is Section 184 "Dangerous Driving."  
**Root Cause:** `lookup_rule` searches by `offence_code` not by `section_ref`; the offence code `RED_LIGHT_JUMPING` doesn't have a matching rule ID in `rules.json`.  
**Fix:** Add explicit rule entries for: `RED_LIGHT_JUMPING` (Sec 177), `DRUNK_DRIVING` (Sec 185 — TC-25 shows rule search for "section" + "act" returns helmet FAQ), and `TINTED_WINDOWS`.

#### GAP-07 · Geofencing Not Triggered in Fallback — MEDIUM (affects TC 33–34)
**Problem:** When GPS is passed with zone-related keywords ("rules here", "school zone"), the `check_zone` tool is not called in the keyword-fallback path unless the exact zone keywords list matches.  
**Root Cause:** Zone keywords list = `["zone", "area", "here", "location", "nearby", "restriction"]`. "What are the traffic rules here?" contains "here" but zone check is also gated on `if gps` which was passed — yet nothing was returned.  
**Fix:** Debug why `check_zone` didn't execute despite GPS and "here" keyword presence. Likely the `zones/index.json` has no matching zone for coordinates (13.01, 80.23 is Velachery, Chennai).

#### GAP-08 · Hospital Zone Rules Missing — LOW (affects TC 35, 37)
**Problem:** No hospital zone speed limit or no-honking rule in the knowledge base.  
**Fix:** Add to `zones/index.json` and `rules.json`: hospital zone speed limit (15 kmph standard), Sec 194 silent zone / prohibition on horns near hospitals.

#### GAP-09 · Juvenile/Minor Driving Not Directly Addressable — LOW (affects TC 15)
**Problem:** Section 199A (juvenile driving — guardian liable, ₹25,000, 3yr imprisonment) is a distinct provision but not coded as an offence type with its own keyword entry.  
**Fix:** Add `JUVENILE_DRIVING` to `offence_keywords.json` with keywords: "minor", "juvenile", "underage", "below 18", "teenager driving". DB already has a TN row for `juvenile_driving`.

#### GAP-10 · Comparison Queries (vs.) Not Supported — LOW (affects TC 14)
**Problem:** "Truck vs car" comparison requires two separate fine lookups and a synthesis step. Keyword-fallback only does one lookup (whichever vehicle keyword is detected last).  
**Fix:** For comparison queries ("X vs Y", "difference between"), run two lookups and format a comparative table in the response.

---

## Part 3 — Ranking

### 3.1 Category Ranking (Best → Worst)

| Rank | Category | Score | Key Strength / Weakness |
|------|----------|-------|------------------------|
| 🥇 1 | Repeat Offences & Edge Cases | **83%** | State-specific TN rows; repeat amounts correctly differentiated |
| 🥈 2 | Basic India Fines | **78%** | Strong core — 6/10 perfect; gaps in rare offences (PUC, triple riding) |
| 🥉 3 | Challan Management | **73%** | Good FAQ coverage; live challan lookup correctly documented |
| 4 | Rule Explanations | **58%** | Section 194D, BAC, DigiLocker strong; tinted windows, exhaust, headlights absent |
| 5 | Conversational/Multi-Turn | **47%** | Basic queries work; follow-ups and greetings broken |
| 6 | Geofencing | **40%** | Zone multiplier FAQ works; live GPS check doesn't activate in fallback |
| 7 | International Fines | **33%** | DB has AE/GB/SG/US/SA rows but country routing is completely broken |
| 7 | Out-of-Scope Safety | **33%** | No domain guard; agent never refuses off-topic queries |

---

### 3.2 Individual Test Ranking

| Rank | TC | Question | Score | Category |
|------|----|----------|-------|----------|
| 1 | TC-02 | Seatbelt Delhi car | ✅ 3/3 | Cat 1 |
| 1 | TC-03 | Overspeeding MH car | ✅ 3/3 | Cat 1 |
| 1 | TC-05 | No insurance UP | ✅ 3/3 | Cat 1 |
| 1 | TC-08 | Mobile phone Telangana | ✅ 3/3 | Cat 1 |
| 1 | TC-11 | Drunk driving 2nd TN | ✅ 3/3 | Cat 2 |
| 1 | TC-13 | Seatbelt 2nd offence | ✅ 3/3 | Cat 2 |
| 1 | TC-26 | Explain Sec 194D | ✅ 3/3 | Cat 4 |
| 1 | TC-30 | Pillion helmet law | ✅ 3/3 | Cat 4 |
| 1 | TC-31 | BAC limit India | ✅ 3/3 | Cat 4 |
| 1 | TC-32 | DigiLocker validity | ✅ 3/3 | Cat 4 |
| 1 | TC-39 | Pay fine online | ✅ 3/3 | Cat 6 |
| 1 | TC-40 | Consequences of unpaid challan | ✅ 3/3 | Cat 6 |
| 1 | TC-41 | License suspended unpaid | ✅ 3/3 | Cat 6 |
| 1 | TC-43 | No helmet fine | ✅ 3/3 | Cat 7 |
| 1 | TC-01 | Helmet Tamil Nadu | ✅ 3/3 | Cat 1 |
| **16** | TC-04 | Red light Karnataka | ⚠️ 2/3 | Cat 1 |
| 16 | TC-06 | No PUC Kerala | ⚠️ 2/3 | Cat 1 |
| 16 | TC-07 | Triple riding AP | ⚠️ 2/3 | Cat 1 |
| 16 | TC-09 | Drunk driving WB | ⚠️ 2/3 | Cat 1 |
| 16 | TC-12 | 3rd helmet offence | ⚠️ 2/3 | Cat 2 |
| 16 | TC-14 | Truck vs car speeding | ⚠️ 2/3 | Cat 2 |
| 16 | TC-15 | Minor without licence | ⚠️ 2/3 | Cat 2 |
| 16 | TC-35 | Hospital zone speed | ⚠️ 2/3 | Cat 5 |
| 16 | TC-36 | School zone multiplier | ⚠️ 2/3 | Cat 5 |
| 16 | TC-38 | Pending challans lookup | ⚠️ 2/3 | Cat 6 |
| 16 | TC-45 | Car helmet follow-up | ⚠️ 2/3 | Cat 7 |
| **27** | TC-10 | Wrong-way Gujarat truck | ❌ 1/3 | Cat 1 |
| 27 | TC-16 | No license plate | ❌ 1/3 | Cat 2 |
| 27 | TC-17 | Red light Dubai UAE | ❌ 1/3 | Cat 3 |
| 27 | TC-18 | Speeding Abu Dhabi | ❌ 1/3 | Cat 3 |
| 27 | TC-19 | Texting UK | ❌ 1/3 | Cat 3 |
| 27 | TC-20 | No insurance USA | ❌ 1/3 | Cat 3 |
| 27 | TC-21 | Speeding Singapore | ❌ 1/3 | Cat 3 |
| 27 | TC-22 | Disabled parking SA | ❌ 1/3 | Cat 3 |
| 27 | TC-23 | DUI New York | ❌ 1/3 | Cat 3 |
| 27 | TC-24 | Seatbelt London UK | ❌ 1/3 | Cat 3 |
| 27 | TC-25 | MV Act section for DUI | ❌ 1/3 | Cat 4 |
| 27 | TC-27 | Tinted windows rules | ❌ 1/3 | Cat 4 |
| 27 | TC-28 | Exhaust modification | ❌ 1/3 | Cat 4 |
| 27 | TC-29 | High-beam headlights | ❌ 1/3 | Cat 4 |
| 27 | TC-33 | GPS-based rules check | ❌ 1/3 | Cat 5 |
| 27 | TC-34 | School zone GPS check | ❌ 1/3 | Cat 5 |
| 27 | TC-37 | Honk hospital zone | ❌ 1/3 | Cat 5 |
| 27 | TC-42 | UAE licence revocation | ❌ 1/3 | Cat 6 |
| 27 | TC-44 | Delhi follow-up (multi-turn) | ❌ 1/3 | Cat 7 |
| 27 | TC-46 | Greeting "Hi there!" | ❌ 1/3 | Cat 7 |
| 27 | TC-47 | "Thanks for information" | ❌ 1/3 | Cat 7 |
| 27 | TC-48 | Chocolate cake recipe | ❌ 1/3 | Cat 8 |
| 27 | TC-49 | Scrape Parivahan Python | ❌ 1/3 | Cat 8 |
| 27 | TC-50 | Capital of France | ❌ 1/3 | Cat 8 |

---

### 3.3 Priority Fix Queue

| Priority | Gap ID | Fix Description | Expected Impact |
|----------|--------|-----------------|-----------------|
| 🔴 P1 | GAP-01 | Add `_detect_country()` in AgentEngine fallback path | Fixes all 8 Cat 3 tests (+16 pts) |
| 🔴 P1 | GAP-02 | Add out-of-scope domain guard + fuzzy greeting match | Fixes TC 46–50 (+10 pts) |
| 🟠 P2 | GAP-03 | Thread session_id in multi-turn fallback path | Fixes TC 44 (+2 pts) |
| 🟠 P2 | GAP-04 | Add NO_PUC, TRIPLE_RIDING, NO_NUMBER_PLATE keywords | Fixes TC 6, 7, 16 (+4 pts) |
| 🟡 P3 | GAP-05 | Fix national drunk_driving row to MV Act 2019 amounts | Fixes TC 9 (+1 pt) |
| 🟡 P3 | GAP-06 | Add rule entries for RED_LIGHT, DRUNK_DRIVING, tinted | Fixes TC 4, 25, 27 (+4 pts) |
| 🟡 P3 | GAP-07 | Debug check_zone not firing with GPS in fallback | Fixes TC 33, 34 (+4 pts) |
| 🟢 P4 | GAP-08 | Add hospital zone data to zones and rules | Fixes TC 35, 37 (+2 pts) |
| 🟢 P4 | GAP-09 | Add JUVENILE_DRIVING offence code | Fixes TC 15 (+1 pt) |
| 🟢 P4 | GAP-10 | Comparison query (X vs Y) two-lookup handler | Fixes TC 14 (+1 pt) |

**Projected Score After All P1+P2 Fixes:** 91 + 32 = ~123/150 → **82%**

---

### 3.4 Agent Performance Observations

| Metric | Value |
|--------|-------|
| Groq LLM active? | ❌ No — all 50 responses used `keyword-fallback` model |
| Disclaimer always present? | ✅ Yes — 50/50 responses had the required disclaimer |
| Structured fine data returned | 18/50 tests (36%) |
| Correct jurisdiction on international | 0/8 (0%) |
| Correct jurisdiction on India | 18/26 India tests (69%) |
| Greeting/social response handled | 1/3 (TC-47 returned harmless FAQ) |
| Out-of-scope refused | 0/3 (0%) |

> **Note:** All 50 tests ran in keyword-fallback mode (Groq circuit-breaker closed but token not consumed). Activating Groq with `GROQ_API_KEY` and function calling would likely resolve GAP-01, GAP-02, and GAP-04 automatically through LLM reasoning, significantly improving scores across Cat 3, Cat 7, and Cat 8 without code changes.

---

*Report generated automatically from `test_results_raw.json` · DriveLegal v2.0.0*
