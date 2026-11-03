
import os
import re
import json
import sqlite3
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st
from groq import Groq

# ==========================================================
# LEADFINDER OS 3.0
# Prospecção + CRM + Gerador de Sites com IA
# ==========================================================

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "leadfinder.db"
HTML_DIR = APP_DIR / "generated_sites"
HTML_DIR.mkdir(exist_ok=True)

st.set_page_config(
    page_title="LeadFinder OS",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# DESIGN SYSTEM — ESTILO SAAS PREMIUM
# ==========================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    color-scheme: dark;
    --bg: #090b12;
    --surface: #111522;
    --surface2: #171c2b;
    --border: #252b3c;
    --primary: #8b5cf6;
    --secondary: #6366f1;
    --text: #f5f5fa;
    --muted: #9299ad;
    --green: #35d39a;
}

.stApp {
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Sans', sans-serif;
}

header[data-testid="stHeader"] {
    background: rgba(9,11,18,.85);
}

.block-container {
    max-width: 1450px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

[data-testid="stSidebar"] {
    background: #0d101a;
    border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] > div {
    padding-top: 1.5rem;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label {
    background: transparent;
    border-radius: 10px;
    padding: 8px 12px;
}

h1, h2, h3 {
    font-family: 'Space Grotesk', sans-serif !important;
    letter-spacing: -0.7px;
}

h1 {
    font-size: 2.15rem !important;
    font-weight: 700 !important;
}

h2 {
    font-size: 1.55rem !important;
}

p, label, span {
    font-family: 'DM Sans', sans-serif;
}

.stCaption, [data-testid="stCaptionContainer"] {
    color: var(--muted);
}

div[data-testid="stMetric"] {
    background: linear-gradient(145deg,#171c2b,#111522);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 20px;
    transition: .2s ease;
}

div[data-testid="stMetric"]:hover {
    border-color: #7654d8;
    transform: translateY(-2px);
}

[data-testid="stMetricValue"] {
    font-family: 'Space Grotesk', sans-serif;
    font-weight
