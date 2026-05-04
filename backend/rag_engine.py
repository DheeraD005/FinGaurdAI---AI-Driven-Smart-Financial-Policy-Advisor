"""
RAG Engine — LangChain + ChromaDB + HuggingFace Embeddings
"""
import os, re
from pathlib import Path
from typing import Optional

import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR   = Path(__file__).parent.parent
CHROMA_DIR = Path("/Users/sowmyasree/Desktop/chroma_store")

# ── Built-in financial knowledge ────────────────────────────────────────────
FINANCE_SEED = [
    "A stock (equity) represents ownership in a company. Shareholders earn returns through price appreciation and dividends.",
    "A bond is a fixed-income instrument where an investor loans money to an entity. Bonds pay periodic interest (coupon) and return principal at maturity.",
    "Mutual funds pool money from many investors to purchase a diversified portfolio of stocks, bonds, or other securities, managed by a professional fund manager.",
    "ETFs (Exchange-Traded Funds) trade on exchanges like stocks but track an index, commodity, or basket of assets, offering low-cost diversification.",
    "SIP (Systematic Investment Plan) allows investors to invest a fixed sum regularly in mutual funds, benefiting from rupee-cost averaging over time.",
    "Finance is the management of money, including activities such as investing, borrowing, lending, budgeting, saving, and forecasting. It covers personal finance, corporate finance, and public finance.",
    "Personal finance involves managing an individual's money, including budgeting, saving, investing, insurance, and planning for retirement.",
    "P/E ratio (Price-to-Earnings) measures how much investors pay per rupee of earnings. A high P/E may signal overvaluation; a low P/E may signal undervaluation.",
    "Debt-to-Equity ratio compares a company's total debt to shareholders' equity. A ratio above 2 is generally considered high risk.",
    "ROE (Return on Equity) measures net income as a percentage of shareholders' equity. Higher ROE indicates more efficient use of equity capital.",
    "EBITDA (Earnings Before Interest, Taxes, Depreciation, Amortization) is a proxy for operating cash flow and profitability.",
    "Current ratio = Current Assets / Current Liabilities. A ratio above 1 means the company can cover short-term obligations.",
    "The 50-30-20 rule suggests spending 50% of income on needs, 30% on wants, and 20% on savings/investments.",
    "Emergency fund: Financial advisors recommend keeping 3-6 months of living expenses in a liquid, low-risk account.",
    "Compound interest formula: A = P(1 + r/n)^(nt), where P is principal, r is annual rate, n is compounds per year, t is time in years.",
    "SIP return formula: FV = P x [((1 + r)^n - 1) / r] x (1 + r), where r = monthly rate, n = months, P = monthly investment.",
    "EMI formula: EMI = [P x r x (1+r)^n] / [(1+r)^n - 1], where P = principal, r = monthly interest rate, n = total months.",
    "LTCG (Long-Term Capital Gains) tax on equity mutual funds and stocks held more than 1 year is 10% above Rs 1 lakh gains in India.",
    "STCG (Short-Term Capital Gains) tax on equity sold within 1 year is 15% in India.",
    "ELSS (Equity Linked Savings Scheme) funds offer tax deduction up to Rs 1.5 lakh under Section 80C of the Income Tax Act.",
    "PPF (Public Provident Fund) offers tax-free returns with a 15-year lock-in period. Current interest rate is around 7.1% per annum.",
    "NPS (National Pension System) provides tax benefits under 80C and 80CCD(1B) — additional Rs 50,000 deduction available.",
    "Diversification reduces unsystematic (company-specific) risk by spreading investments across different assets, sectors, and geographies.",
    "Beta measures a stock's volatility relative to the market. Beta greater than 1 means more volatile; Beta less than 1 means less volatile.",
    "Alpha is the excess return of an investment relative to a benchmark index, representing the fund manager's value-add.",
    "Standard deviation measures the dispersion of returns around the mean — a higher value indicates higher risk.",
    "Sharpe ratio = (Portfolio Return - Risk-Free Rate) / Standard Deviation. Higher is better; greater than 1 is good, greater than 2 is excellent.",
    "Cryptocurrency is a decentralized digital asset secured by cryptography. Major coins include Bitcoin (BTC) and Ethereum (ETH).",
    "Gold is a traditional inflation hedge. In India, Sovereign Gold Bonds (SGBs) offer 2.5% annual interest plus price appreciation.",
    "Real estate investment trusts (REITs) allow investing in income-generating real estate without directly buying property.",
    "Zero-based budgeting assigns every rupee a purpose so income minus expenditures equals zero, eliminating wasteful spending.",
    "Credit score (CIBIL in India) ranges 300-900. A score above 750 is considered good and improves loan approval chances.",
    "Inflation erodes purchasing power over time. At 6% inflation, money loses half its value in about 12 years.",
]

SPLITTER = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=60)

class RAGEngine:
    def __init__(self):
        self.embed = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.vectordb = Chroma(
            client=client,
            collection_name="finguard_v2",
            embedding_function=self.embed,
        )
        self._seed_knowledge()

    # ── Seeding ──────────────────────────────────────────────────────────────
    def _seed_knowledge(self):
        col = self.vectordb._collection
        existing = col.count()
        if existing == 0:
            docs = SPLITTER.create_documents(FINANCE_SEED)
            for i, doc in enumerate(docs):
                doc.metadata = {"source": "builtin", "id": f"seed_{i}"}
            self.vectordb.add_documents(docs)

    # ── Ingest user file ─────────────────────────────────────────────────────
    def ingest_file(self, path: str, filename: str) -> int:
        suffix = Path(path).suffix.lower()
        raw_text = ""
        if suffix == ".pdf":
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                raw_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        elif suffix == ".txt":
            raw_text = Path(path).read_text(errors="ignore")
        elif suffix == ".csv":
            import pandas as pd
            df = pd.read_csv(path)
            raw_text = df.to_string()
        elif suffix == ".xlsx":
            import pandas as pd
            df = pd.read_excel(path)
            raw_text = df.to_string()

        if not raw_text.strip():
            return 0
        docs = SPLITTER.create_documents([raw_text])
        for i, doc in enumerate(docs):
            doc.metadata = {"source": filename, "chunk": i}
        self.vectordb.add_documents(docs)
        return len(docs)

    # ── Query ─────────────────────────────────────────────────────────────────
    def query(self, question: str, history: list) -> tuple[str, list]:
        retriever = self.vectordb.as_retriever(search_kwargs={"k": 5})
        docs = retriever.invoke(question)

        # Only show uploaded file sources — hide builtin
        sources = list({
            d.metadata.get("source", "")
            for d in docs
            if d.metadata.get("source", "builtin") != "builtin"
        })

        answer = self._generate(question, docs)
        return answer, sources

    # ── Answer generator ──────────────────────────────────────────────────────
    def _generate(self, question: str, docs: list) -> str:
        q_lower = question.lower()

        # Greeting
        if any(w in q_lower for w in ["hello", "hi ", "hey", "good morning", "good evening"]):
            return ("Hello! I'm FinGuard AI, your smart financial advisor. "
                    "Ask me about investments, SIP, EMI, tax-saving, market trends, budgeting, or upload your financial documents for analysis!")

        if not docs:
            return "I don't have enough information on that topic yet. Try uploading a relevant financial document!"

        # docs[0] is the most semantically similar chunk (ChromaDB ranks by similarity)
        primary = docs[0].page_content.strip()

        # Add 1-2 extra sentences from other docs only if genuinely different
        extras = []
        for doc in docs[1:]:
            for sent in re.split(r'(?<=[.!?])\s+', doc.page_content):
                sent = sent.strip()
                if len(sent) > 40 and sent not in primary and len(extras) < 2:
                    extras.append(sent)

        answer = primary
        if extras:
            answer += " " + " ".join(extras)

        # Clean up any leftover chunk separators
        answer = re.sub(r'\s*---+\s*', ' ', answer)
        answer = re.sub(r'\s+', ' ', answer).strip()

        # Cap length
        if len(answer) > 900:
            answer = answer[:900].rsplit(' ', 1)[0] + "..."

        # Contextual tips
        tips = {
            "sip":    "\n\nTip: Use the SIP Calculator in the Calculators tab to estimate your returns.",
            "emi":    "\n\nTip: Use the EMI Calculator in the Calculators tab to compare loan options.",
            "tax":    "\n\nTip: ELSS funds offer tax deduction plus equity returns — a dual benefit.",
            "invest": "\n\nTip: Diversify across equity, debt, and gold for balanced risk.",
            "crypto": "\n\nRisk Warning: Crypto is highly volatile. Never invest more than 5% of your portfolio.",
            "budget": "\n\nTip: The 50-30-20 rule is a great starting point for budgeting.",
            "mutual": "\n\nTip: Check your fund's expense ratio — lower is generally better for long-term returns.",
        }
        for kw, tip in tips.items():
            if kw in q_lower:
                answer += tip
                break

        return answer

    # ── Stats ─────────────────────────────────────────────────────────────────
    def get_stats(self) -> dict:
        col = self.vectordb._collection
        total = col.count()
        return {"total_chunks": total, "collection": "finguard_v2", "db_path": str(CHROMA_DIR)}

    def clear(self):
        col = self.vectordb._collection
        ids = col.get()["ids"]
        if ids:
            col.delete(ids=ids)
        self._seed_knowledge()
