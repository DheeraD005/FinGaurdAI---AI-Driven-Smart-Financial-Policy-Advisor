"""
Pure-Python financial calculators.
"""
import math

def calculate_sip(monthly: float, annual_rate: float, years: int) -> dict:
    r = annual_rate / 100 / 12
    n = years * 12
    if r == 0:
        fv = monthly * n
    else:
        fv = monthly * (((1 + r) ** n - 1) / r) * (1 + r)
    invested = monthly * n
    gains    = fv - invested
    return {
        "monthly_investment": monthly,
        "annual_rate": annual_rate,
        "years": years,
        "total_invested": round(invested, 2),
        "estimated_returns": round(gains, 2),
        "maturity_value": round(fv, 2),
        "wealth_gained_pct": round((gains / invested) * 100, 2),
    }

def calculate_emi(principal: float, annual_rate: float, years: int) -> dict:
    r = annual_rate / 100 / 12
    n = years * 12
    if r == 0:
        emi = principal / n
    else:
        emi = (principal * r * (1 + r) ** n) / ((1 + r) ** n - 1)
    total_payment = emi * n
    total_interest = total_payment - principal
    return {
        "principal": principal,
        "annual_rate": annual_rate,
        "years": years,
        "emi": round(emi, 2),
        "total_payment": round(total_payment, 2),
        "total_interest": round(total_interest, 2),
        "interest_pct": round((total_interest / principal) * 100, 2),
    }

def calculate_compound_interest(principal: float, annual_rate: float, years: int, n: int = 12) -> dict:
    r = annual_rate / 100
    amount = principal * (1 + r / n) ** (n * years)
    interest = amount - principal
    return {
        "principal": principal,
        "annual_rate": annual_rate,
        "years": years,
        "compounds_per_year": n,
        "final_amount": round(amount, 2),
        "interest_earned": round(interest, 2),
        "effective_annual_rate": round(((1 + r / n) ** n - 1) * 100, 4),
    }
