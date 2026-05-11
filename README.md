# BuildBridge — Logistics Document AI

> **Logistics AI** · FastAPI · Groq LLaMA-3.3-70B · Google Vision API · Cargo/Container Extraction

---

## 🚀 Live Demo
- **Swagger Docs:** `https://buildbridgehackathon.onrender.com/docs`
---

## Why Monte Carlo?
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
