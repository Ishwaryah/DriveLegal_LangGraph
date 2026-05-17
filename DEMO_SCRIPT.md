# DriveLegal Demo Script — IIT Madras Road Safety Hackathon 2026

## ⏱️ The 30-Second Elevator Pitch
> "Most drivers discover traffic fines only after receiving a court summons — by then it's too late. **DriveLegal** is a premium, offline-first mobile legal companion that puts the complete traffic law in a driver's pocket. It features an **InLegalBERT-powered AI assistant** that cites exact Motor Vehicles Act sections, a state-aware geofencing engine, and an automated document validity vault. Designed for complete accessibility, DriveLegal works 100% offline using local SQLite and pre-embedded vector indices, supporting **6 regional languages** with an automated translation fallback. Road safety should have no language or connectivity barriers."

---

## 🗺️ Fixed 5-Step Demo Path (5–10 Minutes)

This path demonstrates the complete end-to-end capabilities of the DriveLegal platform, linking every front-end visual trigger to its robust back-end engineering engine.

### 🚗 Step 1 — Camera-Based Plate OCR & Instant RTO Lookup
* **Action**: Next to the input field, tap the **Camera Icon** and capture/select a photo of a license plate.
* **Visual Output**: 
  - The app executes high-fidelity **EasyOCR / PyTesseract OCR** on the backend, extracting **`TN09AB1234`** and placing it in the search input automatically.
  - The app then automatically triggers the RTO lookup:
  - The screen populates with the live vehicle registration details: **Maruti Suzuki Swift, LMV Petrol, Owner: Sripathi Rajan**.
  - A bright orange warning banner fires: **`⚠️ Document Alert: PUC Expired (30 days overdue)`**.
  - A second red warning banner pops up: **`⚠️ Outstanding Challan Detected: INR 1,000 pending under Section 129 (No Helmet)`**.
* **Under the Hood**:
  - The mobile app sends the camera image to the backend `/api/v1/cv/plate-ocr` endpoint.
  - The backend runs **EasyOCR** (with PyTesseract and simulator fallbacks) to parse the plate string, validating it against Indian vehicle plate formats.
  - The app then executes a lookup against the **Parivahan e-Challan Offline Snapshot** inside `fines.db`.
  - The **Document Validator** runs state-wise rules on the vehicle metadata, calculating time differentials and applying Delhi NCR diesel bans or Tamil Nadu state compounding fees dynamically.

---

### 📍 Step 2 — GPS Simulation & Reverse-Geofenced Zone Alert
* **Action**: Simulate a coordinate override to Connaught Place, Delhi by inputting GPS coordinates:
  - **`Latitude: 28.6315`**
  - **`Longitude: 77.2167`**
* **Visual Output**:
  - The top geofence status bar changes from green to emergency amber.
  - A persistent card fires: **`🚨 Active Boundary Alert: Connaught Place Odd-Even Restriction (Section 115)`**.
  - Displays compounding warning: **`Fine: INR 2,000 (Non-Compoundable, Immediate Court Clearance Required)`**.
* **Under the Hood**:
  - The mobile `useGeoFineAlert` hook coordinates with the backend `/query` endpoint.
  - The **Geofencing Engine** processes the simulated point against **102 active polygon boundaries** (school zones, silent zones, and high-speed corridors) using standard bounding box and ray-casting intersections, pre-filtering rules based on local time.

---

### 💬 Step 3 — Multilingual Chatbot Query (Tamil to InLegalBERT)
* **Action**: Navigate to the **Ask AI Chatbot** tab, select **Tamil** (or type in Tamil script), and enter:
  - **`ஹெல்மட் இல்லாமல் போனால் அபராதம் என்ன?`** *(What is the fine for going without a helmet?)*
* **Visual Output**:
  - The chatbot processes for a split second and replies with a pristine, localized legal answer:
    > "வண்டி ஓட்டும்போது தலைக்கவசம் அணியாவிடில் (No Helmet), **மோட்டார் வாகன சட்டம் பிரிவு 129 (Section 129)**-இன் படி **₹1,000 அபராதம்** விதிக்கப்படும். மேலும், 3 மாதங்களுக்கு ஓட்டுநர் உரிமம் இடைநிறுத்தம் செய்யப்படலாம்."
* **Under the Hood**:
  - The query triggers the **Multilingual Query Translation Fallback** in [hybrid_search.py](file:///c:/Users/USER/Downloads/DriveLegal-main/DriveLegal-main/backend/modules/nlp/hybrid_search.py).
  - Since `InLegalBERT` is English-pretrained, the preprocessor detects non-ASCII Tamil script, reverse-maps key phrases using the high-fidelity local vocabulary dictionary, translates the search token to `"no helmet fine"`, and executes a vector + lexical search. The response grounds the citation directly under **Section 129** to prevent hallucinations.

---

### 🚑 Step 4 — Emergency Dispatch & Good Samaritan Guard
* **Action**: Tap the prominent **`🚨 I witnessed an accident`** button on the home screen.
* **Visual Output**:
  - The Map instantly centers and highlights **`Government Royapettah Hospital, Chennai`** with an emergency route vector.
  - A high-visibility modal slides up showcasing the **`Good Samaritan Bill of Rights`**:
    > "🛡️ **Under Section 134A of the Motor Vehicles Act**: You are 100% immune from civil or criminal liability. No hospital or police officer can force you to reveal your identity or pay for emergency admissions."
* **Under the Hood**:
  - The app queries the reverse-geocoded state and resolves the nearest Level 1 Trauma Center coordinates from `emergency_contacts_statewise.json` (Royapettah: `13.0524, 80.2667`).
  - It fetches the exact legal immunity statements under **Section 134A** of the Central Motor Vehicles Rules to reassure the user.

---

### 📊 Step 5 — Analytics Dashboard & Climate Safety Trend
* **Action**: Navigate to the **Analytics Dashboard** tab.
* **Visual Output**:
  - **State Risk Ranking**: Shows Tamil Nadu highlighted with a **`Critical High Risk Score of 81.3/100`** due to high national two-wheeler density.
  - **Real-Time Weather Multiplier**: Displays: **`⛈️ Heavy Rain Detected in Region: 2.76x Risk Multiplier Active`** (suggesting a 30% speed reduction on major corridors).
  - **State-wise Comparison Chart**: Renders a beautiful visual bar chart comparing fine rates and compliance levels across 18 Indian states.
* **Under the Hood**:
  - Queries `/state-risk` and `/weather-risk` endpoints which pull statistics from our seeded SQLite databases.
  - The weather engine applies standard risk multipliers based on local climate data caches, calculating stopping distances dynamically.

---

## 📈 Evaluation Criteria Alignment (Why DriveLegal Wins)

| Evaluation Standard | Engineering Implementation | Demo Proof |
| :--- | :--- | :--- |
| **Legal Depth** | 12,050 pre-indexed acts, including 5 distinct State Motor Vehicles Acts. | Cites exact sections (Sec 129, 115, 134A) with compounding details. |
| **Offline Reliability** | Dynamic SQLite seeding and network detection caches. | Calculator works seamlessly when WiFi/mobile data is cut. |
| **Localization Depth** | 6-language dictionary mapping with translation fallbacks. | Instant Tamil translation to English vector query. |
| **Data Engineering Scale** | ~1.16 GB of structured traffic datasets cataloged and validated. | Dataset Catalog Card registered in project metadata. |

---

## 💬 Likely Judges Questions & Answers

#### Q1: How do you support 100% offline legal search?
We compile a complete structured rules database in `rules.json` and a lightweight Lexical BM25 search corpus. When the device loses internet connection, the system toggles an offline status state, rendering calculations from the local SQLite container and using the local BM25 engine for fast keywords fallback.

#### Q2: What is the status of the Computer Vision modules?
We present an honest, working hybrid system:

**Working end-to-end in live demo:**
* ✅ **Plate OCR** (PyTesseract OCR extracts "TN09AB1234") → RC lookup → document validation → fine calculation
* ✅ **GPS & Geofencing** → zone-specific regulations & alerts
* ✅ **Multilingual Chatbot** (6 languages, InLegalBERT-powered with translation fallback)
* ✅ **Good Samaritan Assist** → nearest trauma center & Section 134A immunity statements
* ✅ **Analytics Dashboard** + real-time risk scores & comparative charts
* ✅ **International Fines** (AE/SG/GB)

**Scaffolded, not demoed:**
* ⚙️ **Traffic Sign Recognition** (dataset registered, model pending training)
* ⚙️ **Driver Drowsiness Detection** (dataset registered, model pending training)
* ⚙️ **Pothole Reporting** (dataset registered, model pending training)

To prevent bloating our Git submission with over 4.2 GB of raw images, these scaffolded models are registered in `dataset_catalog.json` with active pipelines and MD5 hashes, ready to trigger training via `python setup_kaggle_datasets.py --download` with a valid Kaggle API key. This is standard ML practice.

