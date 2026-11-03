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

# ============================================================
# LEADFINDER OS 2.0 — painel de prospecção, CRM e geração de sites
# ============================================================

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "leadfinder.db"
HTML_DIR = APP_DIR / "generated_sites"
HTML_DIR.mkdir(exist_ok=True)

st.set_page_config(
    page_title="LeadFinder OS 2.0",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------- VISUAL -------------------------
st.markdown("""
<style>
    :root { color-scheme: dark; }
    .stApp { background: #0b0e14; }
    [data-testid="stSidebar"] { background: #10151f; border-right: 1px solid #252c39; }
    .block-container { padding-top: 1.5rem; max-width: 1500px; }
    div[data-testid="stMetric"] {
        background: #141b27; border: 1px solid #273244;
        padding: 14px 16px; border-radius: 14px;
    }
    div[data-testid="stForm"] {
        background: #111824; border: 1px solid #273244;
        padding: 16px; border-radius: 14px;
    }
    .small-muted { color: #9aa7ba; font-size: .88rem; }
    .lead-card {
        background: #121925; border: 1px solid #293447;
        padding: 14px; border-radius: 12px; margin-bottom: 10px;
    }
    .stButton > button[kind="primary"] {
        background: #e63946; border: 0; color: white; font-weight: 700;
        border-radius: 9px;
    }
    .stButton > button { border-radius: 9px; }
    a { color: #72d6b2; }
</style>
""", unsafe_allow_html=True)

# ---------------------------- CONFIG -------------------------
def secret_or_env(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, os.getenv(name, default)))
    except Exception:
        return os.getenv(name, default)

# ---------------------------- DATABASE -----------------------
def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            place_id TEXT UNIQUE,
            name TEXT NOT NULL,
            category TEXT,
            city TEXT,
            address TEXT,
            phone TEXT,
            website TEXT,
            maps_url TEXT,
            rating REAL,
            reviews INTEGER,
            instagram_url TEXT,
            score INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Novo',
            notes TEXT DEFAULT '',
            created_at TEXT,
            updated_at TEXT
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            business_name TEXT NOT NULL,
            category TEXT,
            city TEXT,
            phone TEXT,
            address TEXT,
            html TEXT,
            hosted_url TEXT,
            created_at TEXT,
            FOREIGN KEY(lead_id) REFERENCES leads(id)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            action TEXT,
            details TEXT,
            created_at TEXT,
            FOREIGN KEY(lead_id) REFERENCES leads(id)
        )
        """)
        conn.commit()

init_db()

def add_activity(lead_id, action, details=""):
    with db() as conn:
        conn.execute(
            "INSERT INTO activities (lead_id, action, details, created_at) VALUES (?, ?, ?, ?)",
            (lead_id, action, details, datetime.now().isoformat(timespec="seconds"))
        )
        conn.commit()

def upsert_leads(leads):
    now = datetime.now().isoformat(timespec="seconds")
    with db() as conn:
        for item in leads:
            conn.execute("""
                INSERT INTO leads (
                    place_id, name, category, city, address, phone, website,
                    maps_url, rating, reviews, score, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(place_id) DO UPDATE SET
                    name=excluded.name, address=excluded.address, phone=excluded.phone,
                    website=excluded.website, maps_url=excluded.maps_url,
                    rating=excluded.rating, reviews=excluded.reviews,
                    score=excluded.score, updated_at=excluded.updated_at
            """, (
                item.get("place_id"), item.get("name", "Empresa sem nome"),
                item.get("category"), item.get("city"), item.get("address"),
                item.get("phone"), item.get("website"), item.get("maps_url"),
                item.get("rating"), item.get("reviews"), item.get("score", 0),
                now, now
            ))
        conn.commit()

def get_leads(status=None, search=""):
    sql = "SELECT * FROM leads WHERE 1=1"
    params = []
    if status and status != "Todos":
        sql += " AND status=?"
        params.append(status)
    if search:
        sql += " AND (name LIKE ? OR city LIKE ? OR category LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])
    sql += " ORDER BY score DESC, updated_at DESC"
    with db() as conn:
        return conn.execute(sql, params).fetchall()

def get_lead(lead_id):
    with db() as conn:
        return conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()

def update_lead(lead_id, **fields):
    allowed = {"status", "notes", "instagram_url", "phone"}
    clean = {k: v for k, v in fields.items() if k in allowed}
    if not clean:
        return
    clean["updated_at"] = datetime.now().isoformat(timespec="seconds")
    cols = ", ".join([f"{k}=?" for k in clean])
    with db() as conn:
        conn.execute(
            f"UPDATE leads SET {cols} WHERE id=?",
            list(clean.values()) + [lead_id]
        )
        conn.commit()

def save_project(lead_id, business_name, category, city, phone, address, html, hosted_url=None):
    with db() as conn:
        cur = conn.execute("""
            INSERT INTO projects
            (lead_id, business_name, category, city, phone, address, html, hosted_url, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lead_id, business_name, category, city, phone, address, html,
            hosted_url, datetime.now().isoformat(timespec="seconds")
        ))
        conn.commit()
        return cur.lastrowid

def get_projects():
    with db() as conn:
        return conn.execute("SELECT * FROM projects ORDER BY id DESC").fetchall()

# ---------------------------- HELPERS ------------------------
NICHOS = [
    "Hamburgueria", "Pizzaria", "Barbearia", "Sorveteria/Açaí",
    "Mecânica", "Lava-jato", "Buffet", "Academia", "Clínica",
    "Pet shop", "Loja de roupas", "Restaurante", "Outro"
]
ESTADOS = {
    "Paraná": ["Foz do Iguaçu", "Cascavel", "Curitiba", "Londrina", "Maringá", "Ponta Grossa"],
    "São Paulo": ["São Paulo", "Campinas", "Santos", "Ribeirão Preto", "Sorocaba"],
    "Minas Gerais": ["Belo Horizonte", "Uberlândia", "Juiz de Fora", "Contagem"],
    "Rio de Janeiro": ["Rio de Janeiro", "Niterói", "Petrópolis"],
    "Santa Catarina": ["Florianópolis", "Joinville", "Blumenau", "Chapecó"],
    "Rio Grande do Sul": ["Porto Alegre", "Caxias do Sul", "Pelotas"],
    "Bahia": ["Salvador", "Feira de Santana", "Vitória da Conquista"],
    "Outro": []
}
STATUS = ["Novo", "Pesquisado", "Abordado", "Respondeu", "Interessado", "Orçamento enviado", "Fechado", "Perdido"]

def digits(value):
    return re.sub(r"\D", "", value or "")

def whatsapp_number(phone):
    n = digits(phone)
    if not n:
        return ""
    if n.startswith("55") and len(n) in (12, 13):
        return n
    if len(n) in (10, 11):
        return "55" + n
    return ""

def score_lead(place):
    score = 0
    if not place.get("website"):
        score += 30
    if place.get("phone"):
        score += 15
    if place.get("rating", 0) >= 4.0:
        score += 10
    if place.get("reviews", 0) >= 10:
        score += 10
    if place.get("reviews", 0) >= 50:
        score += 5
    if place.get("address"):
        score += 10
    # Instagram não é presumido: a confirmação é feita manualmente no CRM.
    return min(score, 100)

def instagram_search_url(name, city):
    q = urllib.parse.quote_plus(f'{name} {city} Instagram')
    return f"https://www.google.com/search?q={q}"

def google_places_search(api_key, query, max_pages=3):
    endpoint = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,"
            "places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri,"
            "places.userRatingCount,places.rating,nextPageToken"
        )
    }
    all_places, page_token = [], None
    for _ in range(max_pages):
        payload = {"textQuery": query, "pageSize": 20, "languageCode": "pt-BR"}
        if page_token:
            payload["pageToken"] = page_token
        response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        all_places.extend(data.get("places", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return all_places

def normalize_place(p, category, city):
    name = p.get("displayName", {}).get("text", "Empresa sem nome")
    item = {
        "place_id": p.get("id"),
        "name": name,
        "category": category,
        "city": city,
        "address": p.get("formattedAddress", ""),
        "phone": p.get("nationalPhoneNumber", ""),
        "website": p.get("websiteUri", ""),
        "maps_url": p.get("googleMapsUri", ""),
        "rating": p.get("rating"),
        "reviews": p.get("userRatingCount", 0),
    }
    item["score"] = score_lead(item)
    return item

# ---------------------------- AI SITE ENGINE ------------------
def call_groq(client, model, system_prompt, user_prompt, temperature=0.7, max_tokens=12000):
    result = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return result.choices[0].message.content.strip()

def extract_html(raw):
    raw = raw.strip()
    match = re.search(r"```(?:html)?\s*(.*?)```", raw, flags=re.I | re.S)
    if match:
        raw = match.group(1).strip()
    start = raw.lower().find("<!doctype")
    if start == -1:
        start = raw.lower().find("<html")
    if start > 0:
        raw = raw[start:]
    return raw

def validate_html(html):
    errors = []
    lower = html.lower()
    if len(html) < 1200:
        errors.append("O HTML retornado parece curto demais.")
    for tag in ("<html", "<head", "<body", "</html>"):
        if tag not in lower:
            errors.append(f"Está faltando a estrutura {tag}.")
    if "viewport" not in lower:
        errors.append("Falta a configuração de viewport para celular.")
    if not ("tailwindcss" in lower or "<style" in lower):
        errors.append("Não encontrei CSS ou Tailwind no documento.")
    return errors

def build_site(client, model, business, design_notes, image_urls, agency_name):
    # Etapa 1: direção de arte estruturada
    art_system = """
Você é diretor de arte sênior de uma agência digital premium.
Crie um briefing visual objetivo em JSON válido, sem markdown.
Defina: brand_personality, color_palette (hex), typography, visual_direction,
hero_layout, section_order, image_strategy, conversion_strategy e mobile_rules.
Não invente fatos sobre a empresa. Diferencie dados fornecidos de sugestões.
O projeto deve ter identidade própria, não copiar um template genérico.
"""
    art_user = f"""
DADOS DA EMPRESA:
{json.dumps(business, ensure_ascii=False, indent=2)}

PREFERÊNCIAS DO CLIENTE/OPERADOR:
{design_notes or "Escolha a direção visual mais adequada ao segmento."}

IMAGENS DISPONÍVEIS:
{json.dumps(image_urls, ensure_ascii=False)}

Crie uma direção de arte com qualidade visual comparável a uma agência premium.
"""
    art_raw = call_groq(client, model, art_system, art_user, temperature=0.65, max_tokens=2500)
    try:
        art_json = re.search(r"\{.*\}", art_raw, flags=re.S).group(0)
        art = json.loads(art_json)
    except Exception:
        art = {"visual_direction": art_raw, "note": "Briefing em texto; interpretar como direção de arte."}

    # Etapa 2: desenvolvimento do site com briefing fechado
    dev_system = """
Você é um engenheiro front-end sênior e designer UI/UX de uma agência premium.
Retorne APENAS um documento HTML completo. Sem markdown, sem explicações.
Requisitos técnicos:
- HTML5 semântico, CSS responsivo e Tailwind via CDN.
- Inclua meta viewport, title, description e favicon simples em SVG/data URI se apropriado.
- Código auto-contido; não dependa de build, npm ou arquivos locais.
- Design realmente elaborado: hierarquia tipográfica, grid, espaçamento, contraste,
  superfícies, detalhes gráficos e estados hover/focus.
- Hero com composição editorial/publicitária e imagem grande, com overlay legível quando necessário.
- Use imagens reais fornecidas quando houver URLs. Não invente URLs.
- Se não houver imagens suficientes, use imagens remotas coerentes do Unsplash Source URLs fornecidas.
- Botões e links devem funcionar. Não deixe href="#" em CTAs.
- WhatsApp deve usar o número fornecido, se válido.
- Não invente preços, avaliações, depoimentos, prêmios, anos de experiência,
  quantidade de clientes, horários ou serviços. Se faltar informação, use CTA para consultar.
- Não apresente a demonstração como site oficial nem afirme que a empresa aprovou o conteúdo.
- Evite aparência de template genérico e evite excesso de gradientes, emojis e cards iguais.
- Mobile-first, menu acessível, contraste e foco visível.
- Inclua aviso discreto "Demonstração conceitual — conteúdo sujeito à confirmação da empresa".
- Use português brasileiro natural.
"""
    dev_user = f"""
Crie o site para esta empresa:

{json.dumps(business, ensure_ascii=False, indent=2)}

DIREÇÃO DE ARTE DEFINIDA:
{json.dumps(art, ensure_ascii=False, indent=2)}

IMAGENS:
{json.dumps(image_urls, ensure_ascii=False)}

AGÊNCIA/CRIADOR DA DEMONSTRAÇÃO: {agency_name}

Crie uma landing page completa e convincente, adequada ao segmento.
A primeira dobra deve ser memorável. O site precisa parecer um projeto real de agência,
não um exemplo escolar. Priorize conversão com WhatsApp e contato.
Não invente informações ausentes. Use texto neutro ou convide o visitante a consultar.
"""
    raw_html = call_groq(client, model, dev_system, dev_user, temperature=0.55, max_tokens=12000)
    html = extract_html(raw_html)
    errors = validate_html(html)
    return html, art, errors

def host_html(html, endpoint, token=""):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.post(endpoint, json={"content": html}, headers=headers, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data.get("link") or data.get("url")

def make_outreach(name, category, city, agency, demo_url=None):
    if demo_url:
        return (
            f"Oi, tudo bem? Encontrei a {name} enquanto conhecia alguns negócios de {city}. "
            f"Preparei uma demonstração conceitual de como a presença online da empresa poderia ficar. "
            f"Fiz pensando no segmento de vocês. Posso te mandar o link para olhar, sem compromisso?\n\n"
            f"{demo_url}\n\n"
            f"— {agency}"
        )
    return (
        f"Oi, tudo bem? Encontrei a {name} enquanto pesquisava empresas de {category} em {city}. "
        f"Estou desenvolvendo sites para negócios locais e tive uma ideia de como poderia apresentar "
        f"melhor a empresa pela internet. Posso te mandar uma demonstração, sem compromisso?"
    )

# ---------------------------- SIDEBAR -------------------------
st.sidebar.title("🚀 LeadFinder OS")
st.sidebar.caption("Prospecção • CRM • Sites")
page = st.sidebar.radio(
    "Navegação",
    ["Dashboard", "Prospecção", "CRM de vendas", "Gerador de sites", "Meus projetos", "Configurações"],
    label_visibility="collapsed",
)
st.sidebar.divider()
agency_name = st.sidebar.text_input("Nome da sua agência", value=st.session_state.get("agency_name", "Minha Agência"))
st.session_state["agency_name"] = agency_name

# Keys: secrets first, then sidebar input for local testing.
maps_key = secret_or_env("GOOGLE_API_KEY")
groq_key = secret_or_env("GROQ_API_KEY")
if page == "Configurações":
    st.sidebar.subheader("Chaves de API")
    maps_key = st.sidebar.text_input("Google Maps / Places API Key", value=maps_key, type="password")
    groq_key = st.sidebar.text_input("Groq API Key", value=groq_key, type="password")
    st.sidebar.caption("Em produção, prefira configurar as chaves em .streamlit/secrets.toml.")
else:
    if not maps_key:
        maps_key = st.sidebar.text_input("Google Places API Key", type="password")
    if not groq_key:
        groq_key = st.sidebar.text_input("Groq API Key", type="password")

# ---------------------------- DASHBOARD -----------------------
if page == "Dashboard":
    st.title("Painel de controle")
    st.caption("Visão geral da sua operação comercial.")
    leads = get_leads()
    projects = get_projects()
    counts = {s: sum(1 for x in leads if x["status"] == s) for s in STATUS}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads salvos", len(leads))
    c2.metric("Demonstrações", len(projects))
    c3.metric("Interessados", counts.get("Interessado", 0))
    c4.metric("Fechados", counts.get("Fechado", 0))
    st.subheader("Funil comercial")
    funnel = ["Novo", "Abordado", "Respondeu", "Interessado", "Orçamento enviado", "Fechado"]
    cols = st.columns(len(funnel))
    for col, status in zip(cols, funnel):
        col.metric(status, counts.get(status, 0))
    st.info("Dica: atualize o status de cada empresa no CRM depois de cada contato. Isso mantém seu funil confiável.")

# ---------------------------- PROSPECTION ---------------------
elif page == "Prospecção":
    st.title("Encontrar empresas")
    st.caption("Busque empresas pelo Google Places e salve oportunidades no seu CRM.")
    with st.form("search_form"):
        a, b, c = st.columns(3)
        category = a.selectbox("Segmento", NICHOS)
        state = b.selectbox("Estado", list(ESTADOS.keys()))
        if ESTADOS[state]:
            city = c.selectbox("Cidade", ESTADOS[state])
        else:
            city = c.text_input("Digite a cidade")
        d, e, f = st.columns(3)
        min_rating = d.slider("Nota mínima", 0.0, 5.0, 3.8, 0.1)
        max_reviews = e.number_input("Máximo de avaliações (0 = sem limite)", min_value=0, value=500, step=50)
        pages = f.selectbox("Profundidade da busca", [1, 2, 3], index=1, help="Cada página pode trazer até 20 resultados.")
        include_with_site = st.checkbox("Incluir empresas que já têm site", value=False)
        submitted = st.form_submit_button("🔎 Buscar oportunidades", type="primary", use_container_width=True)
    if submitted:
        if not maps_key:
            st.error("Configure a chave Google Places API em Configurações ou em secrets.toml.")
        elif not city.strip():
            st.error("Informe uma cidade.")
        else:
            try:
                with st.spinner("Consultando empresas..."):
                    raw = google_places_search(maps_key, f"{category} em {city}, {state}", pages)
                    normalized = [normalize_place(x, category, city) for x in raw]
                    filtered = [
                        x for x in normalized
                        if (include_with_site or not x["website"])
                        and (x["rating"] or 0) >= min_rating
                        and (max_reviews == 0 or (x["reviews"] or 0) <= max_reviews)
                    ]
                    upsert_leads(filtered)
                    st.session_state["last_search_count"] = len(filtered)
                    st.session_state["last_search_city"] = city
                    st.session_state["last_search_category"] = category
                st.success(f"{len(filtered)} oportunidades encontradas e salvas. Resultados do Google podem incluir empresas sem site cadastrado, mas isso deve ser confirmado.")
            except requests.HTTPError as ex:
                st.error(f"Erro da API Google Places: {ex}. Confira chave, faturamento, permissões e Field Mask.")
            except Exception as ex:
                st.error(f"Falha na busca: {ex}")

    st.subheader("Resultados salvos")
    search_filter = st.text_input("Filtrar por nome, cidade ou segmento", key="lead_search")
    rows = get_leads(search=search_filter)
    if not rows:
        st.info("Faça uma busca para começar a montar sua lista de empresas.")
    for row in rows[:100]:
        with st.container(border=True):
            left, mid, right = st.columns([3, 2, 1])
            with left:
                st.markdown(f"**{row['name']}**")
                st.caption(f"{row['category'] or 'Segmento'} • {row['city'] or ''} • {row['address'] or 'Endereço não informado'}")
                st.caption(f"Nota: {row['rating'] or '—'} | Avaliações: {row['reviews'] or 0} | Pontuação: {row['score']}/100")
            with mid:
                st.write(f"**Status:** {row['status']}")
                wa = whatsapp_number(row["phone"])
                if wa:
                    st.markdown(f"[Abrir WhatsApp](https://wa.me/{wa})")
                st.markdown(f"[Pesquisar Instagram]({instagram_search_url(row['name'], row['city'] or '')})")
                if row["maps_url"]:
                    st.markdown(f"[Google Maps]({row['maps_url']})")
            with right:
                if st.button("Abrir no CRM", key=f"crm_{row['id']}", use_container_width=True):
                    st.session_state["selected_lead_id"] = row["id"]
                    st.session_state["page_override"] = "CRM de vendas"
                    st.rerun()

# ---------------------------- CRM -----------------------------
elif page == "CRM de vendas":
    st.title("CRM de vendas")
    st.caption("Acompanhe cada oportunidade até o fechamento.")
    search = st.text_input("Buscar empresa")
    status_filter = st.selectbox("Filtrar status", ["Todos"] + STATUS)
    rows = get_leads(status_filter, search)
    if not rows:
        st.info("Nenhum lead encontrado. Faça uma busca na página Prospecção.")
    else:
        labels = {f"{r['name']} — {r['city']} — #{r['id']}": r["id"] for r in rows}
        default_idx = 0
        selected_id = st.session_state.get("selected_lead_id")
        if selected_id and selected_id in [r["id"] for r in rows]:
            default_idx = [r["id"] for r in rows].index(selected_id)
        chosen = st.selectbox("Selecione uma empresa", list(labels.keys()), index=default_idx)
        lead_id = labels[chosen]
        lead = get_lead(lead_id)
        col1, col2, col3 = st.columns(3)
        col1.metric("Pontuação", f"{lead['score']}/100")
        col2.metric("Avaliação Google", lead["rating"] or "—")
        col3.metric("Avaliações", lead["reviews"] or 0)
        st.write(f"**Endereço:** {lead['address'] or 'Não informado'}")
        st.write(f"**Telefone:** {lead['phone'] or 'Não informado'}")
        if lead["website"]:
            st.warning(f"Site cadastrado no Google: {lead['website']}")
        else:
            st.success("Nenhum site informado no cadastro do Google. Confirme manualmente antes de abordar.")
        with st.form(f"edit_lead_{lead_id}"):
            new_status = st.selectbox("Etapa da negociação", STATUS, index=STATUS.index(lead["status"]) if lead["status"] in STATUS else 0)
            insta = st.text_input("Instagram confirmado (URL)", value=lead["instagram_url"] or "")
            notes = st.text_area("Notas / histórico", value=lead["notes"] or "", height=110)
            save = st.form_submit_button("Salvar alterações", type="primary")
            if save:
                update_lead(lead_id, status=new_status, instagram_url=insta, notes=notes)
                add_activity(lead_id, "Atualização CRM", f"Status: {new_status}")
                st.success("Lead atualizado.")
                st.rerun()
        wa = whatsapp_number(lead["phone"])
        msg = make_outreach(lead["name"], lead["category"] or "empresa", lead["city"] or "", agency_name)
        st.text_area("Mensagem inicial sugerida", value=msg, height=120)
        if wa:
            st.link_button("Abrir conversa no WhatsApp", f"https://wa.me/{wa}?text={urllib.parse.quote(msg)}")
        else:
            st.caption("Telefone não reconhecido como número brasileiro válido para link automático. Confira manualmente.")
        with db() as conn:
            activities = conn.execute("SELECT * FROM activities WHERE lead_id=? ORDER BY id DESC LIMIT 20", (lead_id,)).fetchall()
        if activities:
            st.subheader("Atividades recentes")
            for act in activities:
                st.caption(f"{act['created_at']} — **{act['action']}**: {act['details']}")

# ---------------------------- SITE GENERATOR ------------------
elif page == "Gerador de sites":
    st.title("Gerador de sites premium")
    st.caption("Briefing visual + desenvolvimento + validação + demonstração.")
    saved_leads = get_leads()
    if not saved_leads:
        st.warning("Primeiro encontre e salve uma empresa na página Prospecção.")
    else:
        options = {f"{x['name']} — {x['city']} (#{x['id']})": x["id"] for x in saved_leads}
        selected = st.selectbox("Empresa", list(options.keys()))
        lead = get_lead(options[selected])
        with st.expander("Dados identificados", expanded=True):
            st.write(f"**Nome:** {lead['name']}")
            st.write(f"**Segmento:** {lead['category']}")
            st.write(f"**Cidade:** {lead['city']}")
            st.write(f"**Telefone:** {lead['phone'] or 'Não informado'}")
            st.write(f"**Endereço:** {lead['address'] or 'Não informado'}")
        with st.form("site_brief"):
            site_name = st.text_input("Nome exibido no site", value=lead["name"])
            design_notes = st.text_area(
                "Direção visual (opcional)",
                placeholder="Ex.: visual escuro e premium, vermelho como destaque, fotografia cinematográfica...",
                height=90
            )
            image_urls_text = st.text_area(
                "URLs de imagens (uma por linha, opcionais)",
                placeholder="Cole URLs diretas de imagens autorizadas. Deixe vazio para a IA planejar imagens ilustrativas.",
                height=90
            )
            extra_info = st.text_area(
                "Informações confirmadas da empresa",
                placeholder="Cardápio, serviços, horários, diferenciais e links confirmados. Não inclua dados que não foram verificados.",
                height=100
            )
            create = st.form_submit_button("✨ Gerar demonstração premium", type="primary", use_container_width=True)
        if create:
            if not groq_key:
                st.error("Configure GROQ_API_KEY em Configurações ou secrets.toml.")
            else:
                client = Groq(api_key=groq_key)
                model = secret_or_env("GROQ_MODEL", "openai/gpt-oss-120b")
                phone = whatsapp_number(lead["phone"])
                business = {
                    "name": site_name,
                    "category": lead["category"],
                    "city": lead["city"],
                    "address": lead["address"],
                    "phone_original": lead["phone"],
                    "whatsapp_e164_digits": phone,
                    "rating": lead["rating"],
                    "review_count": lead["reviews"],
                    "verified_business_information": extra_info,
                    "instagram_confirmed_url": lead["instagram_url"],
                    "google_maps_url": lead["maps_url"],
                }
                image_urls = [x.strip() for x in image_urls_text.splitlines() if x.strip().startswith("https://")]
                with st.spinner("Etapa 1/2: criando direção de arte. Etapa 2/2: desenvolvendo e validando o site..."):
                    try:
                        html, art, errors = build_site(
                            client, model, business, design_notes, image_urls, agency_name
                        )
                        st.session_state["latest_html"] = html
                        st.session_state["latest_art"] = art
                        st.session_state["latest_lead_id"] = lead["id"]
                        st.session_state["latest_business"] = business
                        st.session_state["latest_errors"] = errors
                        st.success("Demonstração gerada.")
                    except Exception as ex:
                        st.error(f"Não foi possível gerar o site: {ex}")

        if st.session_state.get("latest_html") and st.session_state.get("latest_lead_id") == lead["id"]:
            html = st.session_state["latest_html"]
            errors = st.session_state.get("latest_errors", [])
            st.subheader("Resultado")
            if errors:
                st.warning("A validação encontrou pontos para revisar:\n- " + "\n- ".join(errors))
            else:
                st.success("Estrutura básica do HTML aprovada. Isso não substitui teste visual em navegador.")
            with st.expander("Direção de arte criada pela IA"):
                st.json(st.session_state.get("latest_art", {}))
            st.download_button(
                "⬇️ Baixar HTML da demonstração",
                data=html,
                file_name=f"demo_{re.sub(r'[^a-zA-Z0-9_-]+','_',lead['name'].lower())}.html",
                mime="text/html",
                use_container_width=True
            )
            host_endpoint = secret_or_env("HOSTING_ENDPOINT", "https://brewpage.app/api/html")
            host_token = secret_or_env("HOSTING_TOKEN", "")
            if st.button("🌐 Hospedar demonstração", type="primary", use_container_width=True):
                try:
                    with st.spinner("Enviando HTML para hospedagem..."):
                        hosted = host_html(html, host_endpoint, host_token)
                    if hosted:
                        st.session_state["latest_hosted_url"] = hosted
                        st.success(f"Demonstração hospedada: {hosted}")
                    else:
                        st.error("A hospedagem respondeu, mas não retornou um campo link/url.")
                except Exception as ex:
                    st.error(f"Falha ao hospedar: {ex}")
            hosted_url = st.session_state.get("latest_hosted_url", "")
            if hosted_url:
                st.markdown(f"[Abrir demonstração em nova aba]({hosted_url})")
                business = st.session_state["latest_business"]
                outreach = make_outreach(
                    business["name"], business["category"], business["city"], agency_name, hosted_url
                )
                st.text_area("Abordagem com demonstração", value=outreach, height=140)
                wa = business.get("whatsapp_e164_digits")
                if wa:
                    st.link_button("Enviar abordagem pelo WhatsApp", f"https://wa.me/{wa}?text={urllib.parse.quote(outreach)}")
                if st.button("Salvar projeto no histórico"):
                    project_id = save_project(
                        st.session_state["latest_lead_id"], business["name"], business["category"],
                        business["city"], business["phone_original"], business["address"],
                        html, hosted_url
                    )
                    add_activity(st.session_state["latest_lead_id"], "Demonstração criada", f"Projeto #{project_id}: {hosted_url}")
                    st.success(f"Projeto #{project_id} salvo.")
            st.caption("Antes de enviar ao estabelecimento, revise imagens, textos, links, direitos de uso e informações comerciais.")

# ---------------------------- PROJECTS ------------------------
elif page == "Meus projetos":
    st.title("Meus projetos")
    projects = get_projects()
    if not projects:
        st.info("Seus projetos salvos aparecerão aqui.")
    for p in projects:
        with st.container(border=True):
            st.markdown(f"**{p['business_name']}** — {p['category'] or ''} • {p['city'] or ''}")
            st.caption(f"Criado em {p['created_at']}")
            if p["hosted_url"]:
                st.markdown(f"[Abrir demonstração]({p['hosted_url']})")
            st.download_button(
                "Baixar HTML",
                data=p["html"] or "",
                file_name=f"projeto_{p['id']}.html",
                mime="text/html",
                key=f"download_project_{p['id']}"
            )

# ---------------------------- SETTINGS -----------------------
elif page == "Configurações":
    st.title("Configurações")
    st.markdown("""
**Configuração recomendada para uso contínuo**

Crie o arquivo `.streamlit/secrets.toml` na pasta do projeto:

```toml
GOOGLE_API_KEY = "sua-chave-google"
GROQ_API_KEY = "sua-chave-groq"
GROQ_MODEL = "openai/gpt-oss-120b"
HOSTING_ENDPOINT = "https://brewpage.app/api/html"
HOSTING_TOKEN = ""
```

Ative a Google Places API (New), configure faturamento e restrinja a chave por API e ambiente.
Nunca publique suas chaves em repositórios públicos ou dentro do HTML gerado.
""")
    st.warning("O custo do Google Places depende do uso e dos campos solicitados. Configure limites e alertas de orçamento no Google Cloud.")
    st.markdown("""
**Sobre os dados:** leads, notas e projetos são armazenados em `leadfinder.db`, no disco do ambiente onde o Streamlit está rodando. Em hospedagens com disco efêmero, configure armazenamento persistente ou migre para PostgreSQL.
""")

# ---------------------------- FOOTER -------------------------
st.divider()
st.caption("LeadFinder OS 2.0 • Ferramenta de apoio à prospecção. Confirme dados das empresas antes do contato e respeite políticas de privacidade e comunicação.")
