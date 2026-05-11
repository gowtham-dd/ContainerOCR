# BuildBridge — Logistics Document AI

> **Logistics AI** · FastAPI · Groq LLaMA-3.3-70B · Google Vision API · Cargo/Container Extraction

---

## 🚀 Live Demo
- **API:** `https://buildbridgehackathon.onrender.com/api/document-analyze`
- **Web UI:** `https://buildbridgehackathon.onrender.com/`
- **Swagger Docs:** `https://buildbridgehackathon.onrender.com/docs`

---

## 📐 Architecture & Approach

```
Request (File Upload — PDF / DOCX / Image)
        │
        ▼
┌──────────────────────┐
│   Auth Middleware    │  x-api-key header validation
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│                    Extraction Layer                          │
│                                                              │
│  PDF   → Google Vision API (pages rendered as PNG → OCR)    │
│           └─ Fallback: PyMuPDF text extraction               │
│  DOCX  → python-docx  (.doc auto-converted via LibreOffice)  │
│  Image → Google Vision API (document_text_detection)        │
└──────────┬───────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│               Monte Carlo AI Pipeline                        │
│                                                              │
│  Small docs  → 3 Groq LLaMA-3.3-70B passes                  │
│                Temperature ladder: [0.0, 0.2, 0.4]          │
│  Large docs  → 1 pass per chunk (4000 chars, 200 overlap)    │
│                                                              │
│  Aggregation:                                                │
│    summary      → most detailed across runs                 │
│    key_points   → union across chunks, deduplicated         │
│    cargo_details→ field-level merging and validation         │
│    document_type→ majority vote                             │
└──────────┬───────────────────────────────────────────────────┘
           │
           ▼
    Structured JSON response (Cargo + Containers)
```

### Why Monte Carlo?
Single LLM calls are stochastic, especially with complex logistics forms. Running multiple passes at varying temperatures:
- **Cargo Fields** — field-level merging ensures high accuracy for B/L and Container numbers
- **Reliability** — majority vote reduces single-pass hallucinations of dates and weights
- **Summary** — the most detailed successful output is selected
- **Large docs** — chunked processing means no page is ever truncated or skipped

---

## 📦 Tech Stack

| Layer | Technology |
|---|---|
| Web Framework | FastAPI + Uvicorn |
| LLM | Groq · `llama-3.3-70b-versatile` |
| LLM Orchestration | LangChain + langchain-groq |
| PDF Extraction | Google Vision API (page-by-page PNG OCR) |
| PDF Fallback | PyMuPDF (fitz) |
| DOCX Extraction | python-docx |
| .doc Conversion | LibreOffice headless |
| Image OCR | Google Vision API |
| Deployment | Render (Docker runtime) |
| Validation | Pydantic v2 |

---

## 📁 Project Structure

```
doc-analyzer/
├── main.py                    # FastAPI app entry point
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container build (LibreOffice + Python 3.11)
├── render.yaml                # Render deployment config (Docker runtime)
├── README.md
│
├── routers/
│   └── analyze.py             # POST /api/document-analyze + auth + file upload
│
├── models/
│   ├── request.py             # (legacy — endpoint now uses UploadFile directly)
│   ├── response.py            # AnalyzeResponse schema
│   └── entities.py            # EntitiesModel — 10 entity categories
│
├── services/
│   ├── extractor.py           # PDF / DOCX / Image extraction (Google Vision)
│   └── ai_pipeline.py         # Monte Carlo LLM orchestration + chunking + aggregation
│
├── prompts/
│   └── analysis_prompt.py     # System + user prompt builders
│
└── static/
    └── index.html             # Web UI (Chart.js — doughnut + bar charts + entity grid)
```

---

## 🛠 Local Setup

Follow these steps to get the project running on your local machine:

### 1. Create a Virtual Environment
```bash
# Windows
python -m venv venv

# macOS/Linux
python3 -m venv venv
```

### 2. Activate the Virtual Environment
```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory (you can copy `.env.example` as a template) and add your keys:
```env
GROQ_API_KEY=your_groq_key
API_KEY=mysecretkey123
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/gcp-key.json
```

### 5. Run the Application
```bash
uvicorn main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

---

## 🔌 API Reference

### `POST /api/document-analyze`

Accepts a file directly as **multipart/form-data** — no base64 encoding needed.

**Headers**

| Key | Value |
|---|---|
| `x-api-key` | `mysecretkey123` |

**Body**

| Key | Type | Value |
|---|---|---|
| `file` | File | your document (pdf / docx / doc / png / jpg / jpeg / webp / tiff / bmp / gif) |

**Response**
```json
{
  "status": "success",
  "fileName": "bill_of_lading.pdf",
  "document_type": "Bill of Lading",
  "summary": "This document is a Bill of Lading for shipping...",
  "key_points": [
    "Vessel: EVER GIVEN Voyage: 064W",
    "Port of Loading: Shanghai, China",
    "Port of Discharge: Rotterdam, Netherlands"
  ],
  "cargo_details": {
    "bill_of_lading_number": "MAEU123456789",
    "shipper": "Global Trading Co.",
    "consignee": "Retail Logistics Ltd.",
    "vessel": "EVER GIVEN",
    "voyage": "064W",
    "port_of_loading": "Shanghai",
    "port_of_discharge": "Rotterdam",
    "total_gross_weight": "24,500 KG",
    "containers": [
      {
        "container_number": "MSKU9876543",
        "seal_number": "SL123456",
        "type": "40' HIGH CUBE",
        "gross_weight": "24,500 KG",
        "description": "Electronics and machinery parts"
      }
    ]
  },
  "usage": {
    "vision_units": 1,
    "total_cost": 0.015
  }
}
```

**Error responses**

| Code | Meaning |
|---|---|
| 401 | Invalid or missing x-api-key |
| 400 | Unsupported file type or empty file |
| 413 | File too large (max 20 MB) |
| 422 | No text could be extracted from the document |
| 500 | Internal server error |

---

## 🧪 Testing the API with Postman

### Step 1 — Create a new request
- Method: **POST**
- URL: `https://buildbridgehackathon.onrender.com/api/document-analyze`

### Step 2 — Add the API key header
Go to the **Headers** tab and add:

| Key | Value |
|---|---|
| `x-api-key` | `mysecretkey123` |

### Step 3 — Attach your file
Go to **Body** tab → select **form-data**

Add a row:

| Key | Type | Value |
|---|---|---|
| `file` | **File** ← change the dropdown from Text to File | click Select Files → pick your document |

> ⚠️ The Type column defaults to `Text` — you **must** switch it to **File** or the upload won't work.

### Step 4 — Hit Send

You will get back a full JSON response with summary, key points, cargo/container details, and document type.

---

## 🌐 Testing via Swagger UI

Visit [`https://buildbridgehackathon.onrender.com/docs`](https://buildbridgehackathon.onrender.com/docs) in your browser.

1. Click `POST /api/document-analyze` → **Try it out**
2. Enter `mysecretkey123` in the `x-api-key` field
3. Click **Choose File** and select your document
4. Click **Execute**

---

## 📦 Extracted Cargo Fields

| Field | Description |
|---|---|
| `bill_of_lading_number` | The unique B/L or tracking number |
| `shipper` | The company sending the goods |
| `consignee` | The company receiving the goods |
| `vessel / voyage` | Vessel name and voyage identification |
| `ports` | Port of Loading and Port of Discharge |
| `containers` | List of all containers found in the document |
| `container_number` | Standard 4-letter + 7-digit container ID |
| `seal_number` | Security seal identifier |
| `type` | Container size/type (e.g., 20' Dry, 40' HC) |
| `gross_weight` | Total weight including packaging |

Plus `document_type` (Bill of Lading / Invoice / Packing List) and a high-level `summary`.

---

## 🖥 Web UI

Visit [`https://buildbridgehackathon.onrender.com`](https://buildbridgehackathon.onrender.com) for the visual interface.

- Drag & drop or browse to upload any supported file
- Enter `mysecretkey123` in the API Key field
- Visualizations include:
  - **Cargo Summary** — Quick overview of shipper, consignee, and vessel
  - **Container Grid** — Detailed list of all containers, seals, and weights
  - **Key points** — numbered bullet findings from the document
  - **Raw JSON toggle** — view the full API response inline

---

## ⚙️ Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Your key from [console.groq.com](https://console.groq.com) |
| `API_KEY` | Secret key for endpoint auth (`mysecretkey123`) |
| `GOOGLE_CREDENTIALS_JSON` | Full JSON string from your GCP service account key file |
| `MC_RUNS` | Monte Carlo passes for small docs (default: `3`) |
| `CHUNK_SIZE` | Characters per chunk for large docs (default: `4000`) |
| `CHUNK_OVERLAP` | Overlap between chunks (default: `200`) |
| `CALL_DELAY` | Seconds between Groq calls to avoid rate limits (default: `3.0`) |

---

## 🧪 Running Tests Locally

### Unit tests (no API key required)
```bash
pytest tests/test_unit.py -v
```

### Full eval suite
```bash
# Against the live deployed URL
python tests/test_api.py --url https://buildbridgehackathon.onrender.com --key mysecretkey123
```

Results saved to `test_report.json` with per-test scoring breakdown.

---

## 🌍 Language Support

Google Vision API auto-detects the document language — no configuration needed. Supports 100+ languages including Tamil, Hindi, Telugu, Arabic, Chinese, Japanese, French, German and more. The API response (summary, entities, key points) is always returned in **English** regardless of the source document language. The `language` field in the response indicates what language the original document was written in.