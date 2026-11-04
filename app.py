import os
import re
import sqlite3
import urllib.parse
from pathlib import Path

import requests
import streamlit as st

# ============================================================
# DN.Ia — Busca de empresas e CRM de oportunidades
# O DN.Ia encontra empresas; a criação dos sites é feita pelo usuário.
# ============================================================

st.set_page_config(
    page_title="DN.Ia | Busca de empresas",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = Path("dn_ia.db")

NICHOS = [
    "Hamburgueria", "Pizzaria", "Barbearia", "Sorveteria/Açaí",
    "Mecânica", "Lava Jato", "Buffet", "Academia", "Clínica",
    "Restaurante", "Loja de roupas", "Salão de beleza", "Pet shop",
    "Odontologia", "Imobiliária", "Hotel/Pousada", "Outro",
]

CIDADES_BR = {
    "Paraná": ["Cascavel", "Curitiba", "Londrina", "Maringá", "Foz do Iguaçu", "Toledo", "Ponta Grossa"],
    "São Paulo": ["São Paulo", "Campinas", "Santos", "Ribeirão Preto", "Sorocaba"],
    "Minas Gerais": ["Belo Horizonte", "Uberlândia", "Juiz de Fora", "Contagem"],
    "Santa Catarina": ["Florianópolis", "Joinville", "Blumenau", "Chapecó"],
    "Rio Grande do Sul": ["Porto Alegre", "Caxias do Sul", "Pelotas"],
    "Rio de Janeiro": ["Rio de Janeiro", "Niterói", "Petrópolis"],
    "Piauí": ["Teresina", "Parnaíba", "Picos"],
    "Outro": [],
}

STATUS = ["Novo Lead", "Contato realizado", "Interessado", "Fechado", "Sem interesse"]

# ---------------------------- Visual ----------------------------
st.markdown("""
<style>
.stApp { background: #0b0e14; color: #e7edf7; }
section[data-testid="stSidebar"] { background: #111827; border-right: 1px solid #263449; }
section[data-testid="stSidebar"] h1 { color: #60a5fa; font-weight: 800; }
h1, h2, h3 { color: #f8fafc !important; }
div[data-testid="stMetric"] { background: #121c2b; border: 1px solid #263449; padding: 15px; border-radius: 13px; }
.stButton > button, .stDownloadButton > button { border-radius: 9px; font-weight: 700; }
.stButton > button[kind="primary"] { background: #2563eb; border: 0; }
div[data-testid="stExpander"] { border: 1px solid #263449; border-radius: 12px; }
.small-muted { color: #94a3b8; font-size: .88rem; }
</style>
""", unsafe_allow_html=True)

# ---------------------------- Banco de dados ----------------------------
def db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    # Mantém a tabela leads já usada nas versões anteriores, sem apagar dados.
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                endereco TEXT,
                telefone TEXT,
                nicho TEXT,
                cidade TEXT,
                nota REAL DEFAULT 0,
                status TEXT DEFAULT 'Novo Lead',
                site_url TEXT,
                html_path TEXT,
                google_place_id TEXT,
                observacoes TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(leads)")}
        migrations = {
            "site_url": "ALTER TABLE leads ADD COLUMN site_url TEXT",
            "html_path": "ALTER TABLE leads ADD COLUMN html_path TEXT",
            "google_place_id": "ALTER TABLE leads ADD COLUMN google_place_id TEXT",
            "observacoes": "ALTER TABLE leads ADD COLUMN observacoes TEXT",
            "nota": "ALTER TABLE leads ADD COLUMN nota REAL DEFAULT 0",
            "status": "ALTER TABLE leads ADD COLUMN status TEXT DEFAULT 'Novo Lead'",
        }
        for column, sql in migrations.items():
            if column not in columns:
                conn.execute(sql)


init_db()

# ---------------------------- Configuração ----------------------------
def get_google_key():
    try:
        key = st.secrets.get("GOOGLE_API_KEY", "")
    except Exception:
        key = ""
    if not key:
        key = st.sidebar.text_input("Google Places API Key", type="password")
    return key.strip() if key else ""


google_api_key = get_google_key()
nome_agencia = st.sidebar.text_input("Nome da sua agência", "DN.Ia Digital")
st.sidebar.caption("DN.Ia • Business Finder")
st.sidebar.divider()
st.sidebar.info("O DN.Ia busca e organiza empresas. A criação e publicação dos sites ficam por sua conta.")

# ---------------------------- Google Places ----------------------------
def search_places(nicho, cidade, estado, nota_minima, max_results=20, somente_sem_site=True):
    if not google_api_key:
        raise RuntimeError("Configure sua GOOGLE_API_KEY na barra lateral ou em Secrets.")

    endpoint = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": google_api_key,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,"
            "places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri,"
            "places.rating,places.userRatingCount"
        ),
    }
    payload = {
        "textQuery": f"{nicho} em {cidade}, {estado}",
        "maxResultCount": max_results,
        "languageCode": "pt-BR",
        "regionCode": "BR",
    }
    response = requests.post(endpoint, headers=headers, json=payload, timeout=35)
    if not response.ok:
        try:
            detail = response.json().get("error", {}).get("message", response.text[:400])
        except Exception:
            detail = response.text[:400]
        raise RuntimeError(f"Google Places ({response.status_code}): {detail}")

    places = response.json().get("places", [])
    results = []
    for place in places:
        rating = float(place.get("rating", 0) or 0)
        has_site = bool(place.get("websiteUri"))
        if rating < nota_minima:
            continue
        if somente_sem_site and has_site:
            continue
        results.append(place)
    return results


def add_lead(place, nicho, cidade):
    nome = place.get("displayName", {}).get("text", "Empresa sem nome")
    place_id = place.get("id", "")
    with db() as conn:
        if place_id:
            exists = conn.execute(
                "SELECT id FROM leads WHERE google_place_id = ?", (place_id,)
            ).fetchone()
            if exists:
                return False
        conn.execute("""
            INSERT INTO leads
            (nome, endereco, telefone, nicho, cidade, nota, status, google_place_id, site_url)
            VALUES (?, ?, ?, ?, ?, ?, 'Novo Lead', ?, ?)
        """, (
            nome,
            place.get("formattedAddress", ""),
            place.get("nationalPhoneNumber", ""),
            nicho,
            cidade,
            float(place.get("rating", 0) or 0),
            place_id,
            place.get("websiteUri", ""),
        ))
    return True


def make_message(lead, agency):
    return (
        f"Olá! Tudo bem? Sou da {agency}. Conheci a {lead['nome']} e trabalho "
        "com criação de sites profissionais para empresas. Tenho uma ideia de "
        "como a presença online pode ajudar a apresentar melhor os serviços e "
        "facilitar o contato com clientes. Posso explicar como funcionaria?"
    )


def whatsapp_link(phone, message):
    digits = re.sub(r"\D", "", phone or "")
    if not digits:
        return ""
    if not digits.startswith("55"):
        digits = "55" + digits
    return "https://wa.me/" + digits + "?text=" + urllib.parse.quote(message)

# ---------------------------- Navegação ----------------------------
st.sidebar.title("🔎 DN.Ia")
st.sidebar.caption("BUSINESS FINDER")
menu = st.sidebar.radio("Menu", ["Dashboard", "Buscar empresas", "CRM de leads"], key="menu_nav")

# ============================ DASHBOARD ============================
if menu == "Dashboard":
    st.title("DN.Ia")
    st.write("Encontre empresas, identifique oportunidades e organize seus contatos em um só lugar.")
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        novos = conn.execute("SELECT COUNT(*) FROM leads WHERE status = 'Novo Lead'").fetchone()[0]
        interessados = conn.execute("SELECT COUNT(*) FROM leads WHERE status = 'Interessado'").fetchone()[0]
        fechados = conn.execute("SELECT COUNT(*) FROM leads WHERE status = 'Fechado'").fetchone()[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Empresas salvas", total)
    c2.metric("Novos contatos", novos)
    c3.metric("Interessados", interessados)
    c4.metric("Fechados", fechados)

    st.subheader("Encontre novas oportunidades")
    st.write("Pesquise empresas por segmento e cidade. Você pode filtrar para encontrar negócios que ainda não possuem site.")
    if st.button("🔎 Começar busca", type="primary", use_container_width=True):
        st.session_state["menu_nav"] = "Buscar empresas"
        st.rerun()
    st.caption("O DN.Ia não cria sites nesta versão. Ele cuida da prospecção e da organização dos leads.")

# ============================ BUSCA ============================
elif menu == "Buscar empresas":
    st.title("Buscar empresas")
    st.write("Encontre negócios no Google e descubra possíveis clientes para sua agência.")

    col1, col2, col3 = st.columns(3)
    with col1:
        nicho = st.selectbox("Segmento", NICHOS)
    with col2:
        estado = st.selectbox("Estado", list(CIDADES_BR.keys()), index=0)
    with col3:
        if estado == "Outro":
            cidade = st.text_input("Digite a cidade")
        else:
            cidades = CIDADES_BR[estado]
            cidade = st.selectbox("Cidade", cidades) if cidades else st.text_input("Digite a cidade")

    c4, c5, c6 = st.columns([1, 1, 1])
    with c4:
        nota_minima = st.slider("Nota mínima no Google", 0.0, 5.0, 3.5, 0.1)
    with c5:
        quantidade = st.selectbox("Quantidade máxima", [5, 10, 15, 20], index=3)
    with c6:
        somente_sem_site = st.checkbox("Somente empresas sem site", value=True)

    if st.button("🔎 Buscar oportunidades", type="primary", use_container_width=True):
        if not cidade.strip():
            st.warning("Informe uma cidade para realizar a busca.")
        else:
            try:
                with st.spinner("Buscando empresas no Google Maps..."):
                    st.session_state["resultados_busca"] = search_places(
                        nicho, cidade.strip(), estado, nota_minima, quantidade, somente_sem_site
                    )
                    st.session_state["busca_nicho"] = nicho
                    st.session_state["busca_cidade"] = cidade.strip()
                st.success(f"Busca concluída: {len(st.session_state['resultados_busca'])} empresa(s) encontrada(s).")
            except Exception as exc:
                st.error(str(exc))

    resultados = st.session_state.get("resultados_busca", [])
    if resultados:
        st.subheader("Resultados encontrados")
        for i, place in enumerate(resultados):
            nome = place.get("displayName", {}).get("text", "Empresa sem nome")
            endereco = place.get("formattedAddress", "Endereço não informado")
            telefone = place.get("nationalPhoneNumber", "Telefone não informado")
            nota = place.get("rating", "Sem nota")
            site = place.get("websiteUri", "")
            maps = place.get("googleMapsUri", "")
            with st.container(border=True):
                info, actions = st.columns([4, 1.4])
                with info:
                    st.markdown(f"### {nome}")
                    st.caption(f"📍 {endereco}")
                    st.caption(f"☎️ {telefone}  •  ⭐ {nota}")
                    if site:
                        st.caption(f"🌐 Site: {site}")
                    else:
                        st.caption("🌐 Não foi encontrado um site oficial no Google Places")
                    if maps:
                        st.markdown(f"[Ver no Google Maps]({maps})")
                with actions:
                    if st.button("Salvar no CRM", key=f"save_{i}", use_container_width=True):
                        try:
                            added = add_lead(place, st.session_state.get("busca_nicho", nicho), st.session_state.get("busca_cidade", cidade))
                            if added:
                                st.success("Empresa salva!")
                            else:
                                st.info("Essa empresa já está no CRM.")
                        except Exception as exc:
                            st.error(f"Não foi possível salvar: {exc}")
                    link = whatsapp_link(telefone, f"Olá! Tudo bem? Conheci a {nome} e gostaria de apresentar uma ideia de site profissional para a empresa. Posso falar com vocês?")
                    if link:
                        st.link_button("WhatsApp", link, use_container_width=True)
    elif "resultados_busca" in st.session_state:
        st.info("Nenhuma empresa correspondeu aos filtros. Tente diminuir a nota mínima ou desmarcar o filtro de empresas sem site.")

# ============================ CRM ============================
elif menu == "CRM de leads":
    st.title("CRM de leads")
    st.write("Todas as empresas que você salvou nas buscas ficam organizadas aqui.")

    with st.expander("➕ Adicionar empresa manualmente"):
        with st.form("manual_lead"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome da empresa")
            telefone = c2.text_input("Telefone/WhatsApp")
            endereco = c1.text_input("Endereço")
            cidade_manual = c2.text_input("Cidade")
            nicho_manual = st.selectbox("Segmento", NICHOS, key="manual_nicho")
            salvar = st.form_submit_button("Salvar empresa")
            if salvar:
                if not nome.strip():
                    st.error("Informe o nome da empresa.")
                else:
                    with db() as conn:
                        conn.execute("""
                            INSERT INTO leads (nome, telefone, endereco, cidade, nicho, status)
                            VALUES (?, ?, ?, ?, ?, 'Novo Lead')
                        """, (nome.strip(), telefone.strip(), endereco.strip(), cidade_manual.strip(), nicho_manual))
                    st.success("Empresa cadastrada no CRM.")
                    st.rerun()

    filtro = st.selectbox("Filtrar por status", ["Todos"] + STATUS)
    with db() as conn:
        leads = conn.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()

    exibidos = [lead for lead in leads if filtro == "Todos" or lead["status"] == filtro]
    if not exibidos:
        st.info("Nenhuma empresa cadastrada com esse filtro. Faça uma busca ou adicione uma empresa manualmente.")

    for lead in exibidos:
        with st.expander(f"🏢 {lead['nome']}  •  {lead['status']}"):
            st.write(f"**Segmento:** {lead['nicho'] or 'Não informado'}")
            st.write(f"**Cidade:** {lead['cidade'] or 'Não informada'}")
            st.write(f"**Endereço:** {lead['endereco'] or 'Não informado'}")
            st.write(f"**Telefone:** {lead['telefone'] or 'Não informado'}")
            st.write(f"**Nota Google:** {lead['nota'] or 'Sem nota'}")
            if lead["site_url"]:
                st.write(f"**Site informado pelo Google:** {lead['site_url']}")

            novo_status = st.selectbox(
                "Etapa do contato", STATUS,
                index=STATUS.index(lead["status"]) if lead["status"] in STATUS else 0,
                key=f"status_{lead['id']}"
            )
            observacoes = st.text_area("Anotações", value=lead["observacoes"] or "", key=f"obs_{lead['id']}")
            a, b = st.columns(2)
            with a:
                if st.button("Salvar alterações", key=f"update_{lead['id']}", use_container_width=True):
                    with db() as conn:
                        conn.execute(
                            "UPDATE leads SET status = ?, observacoes = ? WHERE id = ?",
                            (novo_status, observacoes, lead["id"])
                        )
                    st.success("Lead atualizado.")
                    st.rerun()
            with b:
                message = make_message(lead, nome_agencia)
                link = whatsapp_link(lead["telefone"], message)
                if link:
                    st.link_button("Conversar no WhatsApp", link, use_container_width=True)
                else:
                    st.caption("Cadastre um telefone para abrir o WhatsApp.")

st.sidebar.divider()
st.sidebar.caption("DN.Ia • Busca de empresas e organização de leads")
