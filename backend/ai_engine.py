"""
AI Engine
─────────
• OCR extraction via pytesseract (fallback when OpenAI unavailable)
• Document validation via OpenAI GPT-4o
• Risk scoring & auto-approval recommendations
• Chatbot assistant (student & officer)
"""
import os, json, base64
from pathlib import Path
from typing import Optional
from PIL import Image
import pytesseract
from dotenv import load_dotenv

load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")

# Lazy import so the system works without the openai package installed
try:
    from openai import OpenAI
    _client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None
except ImportError:
    _client = None


# ── OCR ──────────────────────────────────────────────────────────────────

def extract_text(file_path: str) -> str:
    """Extract text from an image or PDF page using Tesseract OCR."""
    try:
        img = Image.open(file_path)
        return pytesseract.image_to_string(img)
    except Exception as exc:
        return f"[OCR error: {exc}]"


# ── Document Validation ──────────────────────────────────────────────────

VALIDATION_PROMPT = """
You are an AI document verification assistant for a university clearance system.
A student has uploaded a document. Your job is to:
1. Identify what type of document it appears to be (receipt, ID card, clearance form, etc.)
2. Check if required fields are present (student name, matric number, amount if receipt, date)
3. Flag any inconsistencies or suspicious patterns
4. Assign a risk score from 0 (clean) to 100 (high risk)
5. Give a brief recommendation: APPROVE, REVIEW, or REJECT

Respond ONLY with a valid JSON object in this exact shape:
{
  "document_type_detected": "...",
  "fields_present": ["name", "matric_number", ...],
  "fields_missing": ["..."],
  "flags": ["..."],
  "risk_score": 0-100,
  "recommendation": "APPROVE" | "REVIEW" | "REJECT",
  "summary": "One sentence explanation"
}
"""


def validate_document(file_path: str, document_type: str,
                       student_matric: str, student_name: str) -> dict:
    """
    Use AI to validate a document. Falls back to basic OCR heuristics
    if OpenAI is not configured.
    """
    extracted = extract_text(file_path)

    if _client:
        try:
            # Encode image for vision API
            with open(file_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            ext = Path(file_path).suffix.lower().strip(".")
            mime = f"image/{ext}" if ext in ("jpg", "jpeg", "png", "webp") else "image/jpeg"

            resp = _client.chat.completions.create(
                model="gpt-4o",
                max_tokens=600,
                messages=[
                    {"role": "system", "content": VALIDATION_PROMPT},
                    {"role": "user", "content": [
                        {"type": "text",
                         "text": (f"Document type expected: {document_type}\n"
                                  f"Student name: {student_name}\n"
                                  f"Matric number: {student_matric}\n"
                                  f"OCR text extracted:\n{extracted[:1500]}")},
                        {"type": "image_url",
                         "image_url": {"url": f"data:{mime};base64,{b64}",
                                       "detail": "low"}}
                    ]}
                ]
            )
            raw = resp.choices[0].message.content.strip()
            # Strip possible markdown fences
            raw = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
        except Exception as exc:
            # Fall through to heuristic
            print(f"[AI] OpenAI validation failed: {exc}")

    # ── Heuristic fallback ────────────────────────────────────────────
    text_lower = extracted.lower()
    missing = []
    present = []
    for field in [student_name.lower(), student_matric.lower(), "date"]:
        if field and field in text_lower:
            present.append(field)
        else:
            missing.append(field)

    risk = min(100, len(missing) * 25)
    rec = "APPROVE" if risk == 0 else ("REVIEW" if risk < 50 else "REJECT")
    return {
        "document_type_detected": document_type,
        "fields_present": present,
        "fields_missing": missing,
        "flags": ["OpenAI not configured — heuristic check only"] if not OPENAI_KEY else [],
        "risk_score": risk,
        "recommendation": rec,
        "summary": f"Heuristic check: {rec}. {len(missing)} required field(s) not found."
    }


# ── Chatbot ──────────────────────────────────────────────────────────────

CHAT_SYSTEM = """
You are a helpful university clearance assistant. You help students understand
their clearance status, what documents are needed, and how to resolve rejections.
You also help university officers quickly summarise pending workloads.
Be concise, warm, and professional. Do not make up information — if unsure, say so.
"""


def chat(messages: list) -> str:
    """
    Send a conversation history to OpenAI and return the assistant reply.
    Falls back to a canned response if OpenAI is not configured.
    """
    if _client:
        try:
            resp = _client.chat.completions.create(
                model="gpt-4o",
                max_tokens=500,
                messages=[{"role": "system", "content": CHAT_SYSTEM}] + messages
            )
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            return f"AI assistant unavailable: {exc}"

    return ("I'm a clearance assistant. "
            "Please configure OPENAI_API_KEY in your .env file to enable AI responses. "
            "For now, please check your clearance dashboard for status updates.")


# ── Bulk summary for officers ────────────────────────────────────────────

def summarise_queue(pending_list: list) -> str:
    """Generate an AI summary of an officer's pending review queue."""
    if not pending_list:
        return "Your queue is empty — no pending submissions."
    if _client:
        try:
            content = json.dumps(pending_list[:30])  # limit tokens
            resp = _client.chat.completions.create(
                model="gpt-4o",
                max_tokens=300,
                messages=[
                    {"role": "system",
                     "content": ("Summarise the following clearance queue for a university officer. "
                                 "Highlight high-risk submissions and totals. Be brief.")},
                    {"role": "user", "content": content}
                ]
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            pass
    total = len(pending_list)
    high  = sum(1 for x in pending_list if x.get("risk_score", 0) > 60)
    return (f"{total} submissions pending. "
            f"{high} flagged as high-risk. "
            "Configure OPENAI_API_KEY for detailed AI summaries.")
