# DriveLegal Demo Script — IIT Madras Road Safety Hackathon 2026

## 30-Second Elevator Pitch

Most drivers discover traffic fines only after receiving a challan — by then it's too late. DriveLegal is an offline-first mobile app that puts every country's traffic law in a driver's pocket, with an AI legal assistant that cites exact MV Act sections and calculates multi-violation fines instantly. Unlike generic legal apps, DriveLegal works without internet, covers India, UAE, Singapore, and the UK in a single interface, and is built for accessibility — because road safety should have no barriers.

---

## 5-Minute Demo Flow

### Step 1: Open app — show location auto-detection in TN
- Launch the app; the Home dashboard shows the user's detected state (Tamil Nadu).
- The "Most Common Violations" cards populate from the local SQLite DB for TN.
- Point out the **location card** showing state-aware data without any manual input.

### Step 2: Challan Calculator — India demo (2-wheeler, helmet + phone = ₹2,500)
- Tap **Challan Calculator** tab.
- Country is already set to 🇮🇳 India; state defaults to Tamil Nadu.
- Select **Two Wheeler** as vehicle type.
- Check **No Helmet** (Sec 129, ₹1,000) and **Using Phone while Driving** (Sec 184, ₹1,500).
- Tap **Calculate 2 Violations**.
- Result modal shows: **Total Fine ₹2,500** with compounding eligibility and individual section citations.

### Step 3: Switch to UAE — show AED amounts
- Tap 🇦🇪 UAE pill in the country selector.
- Violations list refreshes: overspeeding fines appear in **AED**, not INR.
- Select **Overspeeding (>60 km/h)** (AED 1,000 + 8 black points + 60-day license confiscation).
- Calculate — modal shows **AED 1,000**, confirming currency is correct.

### Step 4: Chatbot — ask about juvenile driving (shows ₹25,000 + Section 199A)
- Tap **Ask** (chatbot) tab.
- Type: *"what is the fine for juvenile driving in India"*
- Response cites **Section 199A, MV Act 2019**: ₹25,000 + 3-year imprisonment for guardian + RC cancellation.
- Follow up: *"what about drunk driving"* → cites **Section 185**: ₹10,000 first offense.

### Step 5: Disconnect WiFi — show offline mode badge, calculator still works
- In browser DevTools, go to **Network** tab → set throttle to **Offline**.
- Return to Challan Calculator — observe the **🔴 Offline – Cached** badge in the header.
- Select India > Two Wheeler > No Helmet → Calculate.
- Fine still shows ₹1,000 from the local SQLite DB — no network needed.
- In the chatbot, type *"helmet fine"* → offline fallback shows the rule from local `rules.json`.

### Step 6: Settings — show high contrast mode
- Tap **Settings** tab.
- Toggle **High Contrast Mode** ON.
- The entire app switches to #000 background with #FFF text and gold accent — WCAG AA compliant.
- Toggle back to demonstrate the transition is instant and persistent.

---

## Evaluation Criteria Mapping

| Criterion | Feature | Demo Proof |
|-----------|---------|------------|
| Legal accuracy | MV Act section citations (Sec 129, 185, 199A, etc.) | Chatbot responses + Calculator violation cards |
| Challan calculator | Vehicle-type and state-specific fine computation | Calculator demo (TN + two_wheeler → exact ₹ amounts) |
| Multi-country | IN + AE + SG + GB data (520 fines, 4 currencies) | Country switcher in Calculator and Chatbot |
| UI/Accessibility | High contrast mode, `accessibilityLabel` on all interactive elements | Settings toggle + screen reader pass |
| Offline-first | SQLite sync, offline badge, fallback calculation | DevTools Network → Offline test |
| AI Chatbot | Section citations, multi-turn context, country-aware | Chatbot tab — juvenile + drunk driving queries |

---

## Judges' Likely Questions + Answers

**Q1: How do you ensure the fine amounts are legally accurate?**
All India fines are sourced directly from the Motor Vehicles (Amendment) Act 2019 gazette notification. UAE fines are from Federal Traffic Law No. 21 of 1995. Singapore fines from Road Traffic Act Cap 276. UK fines from the Road Traffic Act 1988 and Road Traffic Offenders Act 1988. Each row in the database carries the exact section reference. A disclaimer is shown on every result directing users to verify at official portals (echallan.parivahan.gov.in for India).

**Q2: What happens when the user is in an area with no internet?**
The app syncs the complete fine schedule to a local SQLite database on first load. When offline is detected (via `@react-native-community/netinfo`), the Challan Calculator reads from SQLite, the chatbot falls back to keyword search on the locally bundled `rules.json`, and an "🔴 Offline – Cached" badge is shown. The user experience degrades gracefully — calculation still works, only the AI-generated natural language summary is unavailable.

**Q3: Why did you choose Expo / React Native over a native app?**
Expo gives us a single codebase for iOS, Android, and Web — critical for a hackathon timeline. Expo Router (file-based navigation) and Expo SQLite give us the offline-first architecture without writing separate native bridges. For production, we can eject to bare React Native for performance-critical paths.

**Q4: How does the app know which state the user is in?**
`expo-location` requests foreground permission to get GPS coordinates. The coordinates are reverse-geocoded using an offline GeoJSON of Indian state boundaries (no API key needed). The detected state code is then used to pre-filter violations in the Challan Calculator, showing only state-relevant fines.

**Q5: Does this handle repeat offenses and compounding?**
Yes. The database schema stores both `min_fine_local` and `max_fine_local`, which represent first-offense and repeat-offense amounts respectively. Compounding eligibility (`compounding_eligible` flag) and the compounding fee are stored per violation per state. The Calculator UI has a "Repeat Offense" toggle that switches to the higher fine, and the result modal shows compounding options when available.

**Q6: Can this scale to more countries?**
Absolutely. The data model is country-agnostic — the `fines` table has a `country` column and `currency` column. Adding a new country is a single INSERT batch in `migrate_db.py`. The mobile UI automatically picks up new countries from the `/api/v1/fines/countries` endpoint at runtime and adds them to the country selector.

**Q7: What's the AI chatbot actually doing? Is it just a lookup?**
It's a hybrid NLP pipeline. The query goes through: (1) text normalization, (2) intent classification (fine query vs. rule explanation vs. zone alert), (3) entity extraction (vehicle type, violation, state), (4) country detection, (5) BM25 + ChromaDB vector search over the rules corpus, and (6) optionally, Groq LLaMA 3 for natural language generation. The result is grounded in the local rules database, so hallucinations about specific fine amounts are prevented.

**Q8: What would you build next with more time?**
Three things: (1) Live e-Challan lookup via the Parivahan API (the endpoint exists, it just needs an API key). (2) Push notifications for zone alerts when the user enters a speed camera zone or school zone. (3) Multi-language support — the settings infrastructure already has a `t()` translation function; we'd add Tamil, Hindi, and Arabic translation strings.
