"""
AI Analysis Pipeline
Uses Groq (LLaMA-3.3-70b-versatile) via LangChain.
Simplified to focus only on Cargo details.
"""

import asyncio
import json
import logging
import os
import re
from collections import Counter

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from models.response import AnalyzeResponse
from prompts.analysis_prompt import build_system_prompt, build_user_prompt

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
MC_RUNS         = int(os.getenv("MC_RUNS", "3"))
MC_TEMPERATURES = [0.0, 0.2, 0.4]
CHUNK_SIZE      = int(os.getenv("CHUNK_SIZE", "4000"))
CHUNK_OVERLAP   = int(os.getenv("CHUNK_OVERLAP", "200"))
CALL_DELAY      = float(os.getenv("CALL_DELAY", "3.0"))


def _get_llm(temperature: float = 0.1) -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable not set")
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=temperature,
        api_key=api_key,
        max_tokens=1200,
    )


# ── Chunking ───────────────────────────────────────────────────────────────────

def _split_into_chunks(text: str) -> list[str]:
    if len(text) <= CHUNK_SIZE:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        if end >= len(text):
            chunk = text[start:]
            chunks.append(chunk.strip())
            break
            
        chunk = text[start:end]
        break_at = chunk.rfind("\n\n")
        if break_at == -1 or break_at < CHUNK_SIZE // 2:
            break_at = chunk.rfind(". ")
            
        if break_at != -1 and break_at > CHUNK_SIZE // 2:
            chunk = chunk[:break_at + 1]
            
        chunks.append(chunk.strip())
        next_start = start + len(chunk) - CHUNK_OVERLAP
        if next_start <= start:
            start += CHUNK_SIZE // 2
        else:
            start = next_start
            
    logger.info(f"Split document into {len(chunks)} chunks")
    return chunks


# ── JSON parsing ───────────────────────────────────────────────────────────────

def _parse_llm_json(raw: str) -> dict | None:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    logger.warning(f"Could not parse LLM JSON: {raw[:300]}")
    return None


# ── Single LLM call with retry ─────────────────────────────────────────────────

async def _single_run(text: str, temperature: float) -> tuple[dict | None, int, int]:
    for attempt in range(4):
        try:
            llm = _get_llm(temperature)
            messages = [
                SystemMessage(content=build_system_prompt()),
                HumanMessage(content=build_user_prompt(text)),
            ]
            response = llm.invoke(messages)
            usage = response.response_metadata.get("token_usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            return _parse_llm_json(response.content), input_tokens, output_tokens
        except Exception as e:
            err = str(e)
            if "429" in err or "rate" in err.lower():
                wait = 8 * (attempt + 1)
                logger.warning(f"Rate limited (attempt {attempt+1}). Waiting {wait}s...")
                await asyncio.sleep(wait)
            else:
                logger.error(f"LLM run failed at temp={temperature}: {e}")
                return None, 0, 0
    return None, 0, 0


# ── Aggregation helpers ────────────────────────────────────────────────────────

def _majority_vote_str(values: list[str], fallback: str = "") -> str:
    valid = [v.strip() for v in values if v and v.strip()]
    return Counter(valid).most_common(1)[0][0] if valid else fallback


def _merge_summaries(summaries: list[str]) -> str:
    valid = [s.strip() for s in summaries if s and len(s.strip()) > 20]
    if not valid:
        return "Summary not available."
    if len(valid) == 1:
        return valid[0]
    combined = " ".join(valid)
    if len(combined) > 1200:
        combined = combined[:1200].rsplit(".", 1)[0] + "."
    return combined


def _merge_key_points(all_points: list[list]) -> list[str]:
    seen = set()
    result = []
    for points in all_points:
        if not isinstance(points, list): continue
        for p in points:
            if isinstance(p, str) and p.strip():
                key = p.strip().lower()
                if key not in seen:
                    seen.add(key)
                    result.append(p.strip())
    return result[:8]


def _merge_cargo_details(all_cargo: list[dict]) -> dict | None:
    if not all_cargo: return None
    base_fields = [
        "bill_of_lading_number", "shipper", "consignee", "notify_party",
        "vessel", "voyage", "port_of_loading", "port_of_discharge",
        "place_of_receipt", "place_of_delivery", "booking_reference",
        "shipped_on_board_date", "total_items", "total_gross_weight"
    ]
    merged: dict = {}
    for field in base_fields:
        vals = [c.get(field, "") for c in all_cargo if c.get(field)]
        merged[field] = Counter(vals).most_common(1)[0][0] if vals else ""
            
    all_containers: dict[str, dict] = {}
    for cargo in all_cargo:
        containers = cargo.get("containers", [])
        if isinstance(containers, list):
            for cont in containers:
                if not isinstance(cont, dict): continue
                cnum = cont.get("container_number", "").strip().upper()
                if not cnum: continue
                if cnum not in all_containers:
                    all_containers[cnum] = cont
                else:
                    for k, v in cont.items():
                        if v and not all_containers[cnum].get(k):
                            all_containers[cnum][k] = v
                            
    merged["containers"] = list(all_containers.values())
    return merged if any(merged.get(f) for f in base_fields) or merged["containers"] else None


# ── Main pipeline ──────────────────────────────────────────────────────────────

async def run_analysis(raw_text: str, file_name: str, vision_units: int = 0) -> AnalyzeResponse:
    from models.response import UsageInfo

    chunks = _split_into_chunks(raw_text)
    is_large_doc = len(chunks) > 1

    all_summaries:  list[str]  = []
    all_cargo_details: list[dict] = []
    all_key_points: list[list] = []
    all_doc_types:  list[str]  = []
    
    total_in_tokens = 0
    total_out_tokens = 0

    if is_large_doc:
        for i, chunk in enumerate(chunks):
            result, in_t, out_t = await _single_run(chunk, temperature=0.1)
            total_in_tokens += in_t
            total_out_tokens += out_t
            if result:
                all_summaries.append(result.get("summary", ""))
                all_cargo_details.append(result.get("cargo_details", {}))
                all_key_points.append(result.get("key_points", []))
                all_doc_types.append(result.get("document_type", ""))
            if i < len(chunks) - 1:
                await asyncio.sleep(CALL_DELAY)
    else:
        for i, t in enumerate(MC_TEMPERATURES[:MC_RUNS]):
            result, in_t, out_t = await _single_run(chunks[0], temperature=t)
            total_in_tokens += in_t
            total_out_tokens += out_t
            if result:
                all_summaries.append(result.get("summary", ""))
                all_cargo_details.append(result.get("cargo_details", {}))
                all_key_points.append(result.get("key_points", []))
                all_doc_types.append(result.get("document_type", ""))
            if i < MC_RUNS - 1:
                await asyncio.sleep(CALL_DELAY)

    if not all_summaries:
        raise RuntimeError("All LLM inference passes failed.")

    vision_cost = vision_units * 0.0015
    groq_cost = (total_in_tokens + total_out_tokens) * 0.0000006
    
    usage_info = UsageInfo(
        vision_units=vision_units,
        vision_cost=round(vision_cost, 6),
        groq_input_tokens=total_in_tokens,
        groq_output_tokens=total_out_tokens,
        groq_cost=round(groq_cost, 6),
        total_cost=round(vision_cost + groq_cost, 6)
    )

    return AnalyzeResponse(
        status="success",
        fileName=file_name,
        document_type=_majority_vote_str(all_doc_types, "Other"),
        summary=_merge_summaries(all_summaries),
        key_points=_merge_key_points(all_key_points),
        cargo_details=_merge_cargo_details(all_cargo_details),
        usage=usage_info,
    )