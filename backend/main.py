import os, json, time, uuid
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag_engine import RAGEngine
from market_data import get_stock_data, get_market_summary
from financial_tools import calculate_sip, calculate_emi, calculate_compound_interest

BASE_DIR     = Path(__file__).parent
PROJECT_DIR  = BASE_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"

app = FastAPI(title="FinGuard AI", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

rag = RAGEngine()

static_dir = FRONTEND_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ── Models ───────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class SIPRequest(BaseModel):
    monthly_investment: float
    annual_rate: float
    years: int

class EMIRequest(BaseModel):
    principal: float
    annual_rate: float
    years: int

class CompoundRequest(BaseModel):
    principal: float
    annual_rate: float
    years: int
    compounds_per_year: int = 12

class BudgetItem(BaseModel):
    category: str
    amount: float

class BudgetRequest(BaseModel):
    income: float
    items: List[BudgetItem]

# ── Chat History (in-memory) ─────────────────────────────────────────────────
chat_sessions: dict = {}

# ── Routes ───────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    return HTMLResponse(content=(FRONTEND_DIR / "index.html").read_text(), status_code=200)

@app.post("/api/chat")
async def chat(req: ChatRequest):
    sid = req.session_id or str(uuid.uuid4())
    if sid not in chat_sessions:
        chat_sessions[sid] = []
    history = chat_sessions[sid]
    answer, sources = rag.query(req.message, history)
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": answer})
    chat_sessions[sid] = history[-20:]
    return {"answer": answer, "sources": sources, "session_id": sid}

@app.get("/api/kb/stats")
async def kb_stats():
    return rag.get_stats()

@app.delete("/api/kb/clear")
async def clear_kb():
    rag.clear()
    return {"message": "Knowledge base cleared."}

@app.get("/api/market/{symbol}")
async def stock_info(symbol: str):
    data = get_stock_data(symbol.upper())
    if not data:
        raise HTTPException(404, f"Symbol '{symbol}' not found.")
    return data

@app.get("/api/market/summary/indices")
async def market_summary():
    return get_market_summary()

@app.post("/api/tools/sip")
async def sip_calc(req: SIPRequest):
    return calculate_sip(req.monthly_investment, req.annual_rate, req.years)

@app.post("/api/tools/emi")
async def emi_calc(req: EMIRequest):
    return calculate_emi(req.principal, req.annual_rate, req.years)

@app.post("/api/tools/compound")
async def compound_calc(req: CompoundRequest):
    return calculate_compound_interest(req.principal, req.annual_rate, req.years, req.compounds_per_year)

@app.post("/api/tools/budget")
async def budget_analyze(req: BudgetRequest):
    total_spent = sum(i.amount for i in req.items)
    remaining   = req.income - total_spent
    savings_pct = round((remaining / req.income) * 100, 1) if req.income else 0
    items_out   = [
        {
            "category": i.category,
            "amount": i.amount,
            "pct": round((i.amount / req.income) * 100, 1) if req.income else 0,
        }
        for i in req.items
    ]
    rule_status = []
    needs  = sum(i.amount for i in req.items if i.category.lower() in ["rent","housing","groceries","utilities","transport","insurance","healthcare","food"])
    wants  = sum(i.amount for i in req.items if i.category.lower() in ["entertainment","dining","shopping","subscriptions","travel","hobbies"])
    needs_pct  = round(needs / req.income * 100, 1) if req.income else 0
    wants_pct  = round(wants / req.income * 100, 1) if req.income else 0
    return {
        "income": req.income,
        "total_spent": round(total_spent, 2),
        "remaining": round(remaining, 2),
        "savings_pct": savings_pct,
        "items": items_out,
        "rule_5030": {
            "needs_pct": needs_pct,
            "wants_pct": wants_pct,
            "savings_pct": savings_pct,
            "healthy": needs_pct <= 50 and wants_pct <= 30 and savings_pct >= 20,
        }
    }

@app.get("/api/chat/history/{session_id}")
async def get_history(session_id: str):
    return {"history": chat_sessions.get(session_id, [])}

@app.delete("/api/chat/history/{session_id}")
async def clear_history(session_id: str):
    chat_sessions.pop(session_id, None)
    return {"message": "Chat history cleared."}

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "kb_docs": rag.get_stats().get("total_chunks", 0)}
