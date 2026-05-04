"""
Live market data using yfinance (no API key needed).
"""
import yfinance as yf
from typing import Optional

# Major indices + popular Indian stocks
INDICES = {
    "Nifty 50": "^NSEI",
    "Sensex": "^BSESN",
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Gold": "GC=F",
    "Crude Oil": "CL=F",
}

def get_stock_data(symbol: str) -> Optional[dict]:
    try:
        t = yf.Ticker(symbol)
        info = t.info
        hist = t.history(period="5d")
        if hist.empty:
            return None
        latest = hist["Close"].iloc[-1]
        prev   = hist["Close"].iloc[-2] if len(hist) > 1 else latest
        change = latest - prev
        pct    = (change / prev) * 100 if prev else 0
        return {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName", symbol),
            "price": round(float(latest), 2),
            "change": round(float(change), 2),
            "change_pct": round(float(pct), 2),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "volume": info.get("volume"),
            "currency": info.get("currency", "USD"),
            "sector": info.get("sector", "—"),
        }
    except Exception:
        return None


def get_market_summary() -> dict:
    result = {}
    for name, sym in INDICES.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="2d")
            if hist.empty:
                continue
            latest = float(hist["Close"].iloc[-1])
            prev   = float(hist["Close"].iloc[-2]) if len(hist) > 1 else latest
            change_pct = ((latest - prev) / prev * 100) if prev else 0
            result[name] = {
                "price": round(latest, 2),
                "change_pct": round(change_pct, 2),
                "symbol": sym,
            }
        except Exception:
            pass
    return result
