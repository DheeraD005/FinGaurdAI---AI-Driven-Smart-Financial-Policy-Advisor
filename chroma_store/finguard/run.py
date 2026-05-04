#!/usr/bin/env python3
"""
Start FinGuard AI server.
Run from the finguard/ directory:  python3 run.py
"""
import sys, os, subprocess
from pathlib import Path

MINICONDA_PYTHON = "/Users/sowmyasree/miniconda3/bin/python3"
backend = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend))
os.chdir(backend)

# Use miniconda python (where packages are installed)
python = MINICONDA_PYTHON if Path(MINICONDA_PYTHON).exists() else sys.executable

subprocess.run([
    python, "-m", "uvicorn", "main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--reload",
], check=True)
