import os
import re
import json
import time
import sqlite3
import urllib.parse
from pathlib import Path
from datetime import datetime

import requests
import streamlit as st
import streamlit.components.v1 as components
from groq import Groq

# ============================================================
# DN.Ia 4.1 — Prospecção, CRM e Studio de criação de sites
# ============================================================

st.set_page_config(
    page_title="DN.Ia 4.1",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = Path("dn_ia.db")
SITES_DIR = Path("sites_gerados")
SITES_DIR.mkdir(exist_ok=True)

NICHOS = [
    "Hamburgueria", "Pizzaria", "Barbearia", "Sorveteria/Açaí",
    "Mecânica", "Lava Jato", "Buffet", "Academia", "Clínica",
    "Restaurante", "Loja de roupas", "Salão de beleza", "Outro"
]

CIDADES_BR = {
    "Minas Gerais": ["Belo Horizonte", "Uberlândia", "Cataguases", "Juiz de Fora"],
    "São Paulo": ["São Paulo", "Campinas", "Santos"],
    "Paraná": ["Curitiba", "Londrina", "Maringá", "Cascavel"],
    "Piauí": ["Teresina", "Parnaíba", "Picos"],
    "Outro": ["Digitar manualmente"],
}

ESTILOS = [
    "Automático — a IA escolhe a melhor combinação",
    "Agência profissional — sofisticado e elegante",
    "SaaS premium — moderno e tecnológico",
    "Editorial — visual marcante e fotografia em destaque",
    "Minimalista — limpo, direto e elegante",
]

# Imagens de demonstração. Troque por imagens licenciadas/fornecidas pelo cliente
# antes de publicar projetos comerciais.
IMAGENS_NICHO = {
    "Hamburgueria": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=1800&auto=format&fit=crop",
    "Pizzaria": "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=1800&auto=format&fit=crop",
    "Barbearia": "https://images.unsplash.com/photo-1585747860715-2ba37e788b70?w=1800&auto=format&fit=crop",
    "Academia": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1800&auto=format&fit=crop",
    "Mecânica": "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=1800&auto=format&fit=crop",
    "Sorveteria/Açaí": "https://images.unsplash.com/photo-1501446529957-6226bd447c46?w=1800&auto=format&fit=crop",
    "Restaurante": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1800&auto=format&fit=crop",
    "Loja de roupas": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1800&auto=format&fit=crop",
    "Salão de beleza": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=1800&auto=format&fit=crop",
    "Outro": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1800&auto=format&fit=crop",
}

# ---------------------------- CSS ----------------------------

st.markdown("""
<style>
.stApp { background: #0b0e14; color: #e2e8f0; }
section[data-testid="stSidebar"] { background: #121620; border-right: 1px solid #263244; }
section[data-testid="stSidebar"] h1 { color: #60a5fa; font-weight: 800; }
h1, h2, h3 { color: #f8fafc !important; }
div[data-testid="stMetric"] {
    background: #121a27; border: 1px solid #263244;
    padding: 16px; border-radius: 12px;
}
.stButton > button {
    background: #2563eb; color: white; border: 0;
    border-radius: 8px; font-weight: 700; padding: 0.55rem 1rem;
}
.stButton > button:hover { background: #1d4ed8; color: white; }
div[data-testid="stExpander"] { border: 1px solid #263244; border-radius: 10px; }
div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea {
    background: #172033; color: #f8fafc;
}
.small-muted { color: #94a3b8; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)


# ------------------------- Banco de dados -------------------------

def db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
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
        # Migração segura para bancos criados em versões anteriores.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(leads)")}
        migrations = {
            "html_path": "ALTER TABLE leads ADD COLUMN html_path TEXT",
            "google_place_id": "ALTER TABLE leads ADD COLUMN google_place_id TEXT",
            "observacoes": "ALTER TABLE leads ADD COLUMN observacoes TEXT",
        }
        for column, sql in migrations.items():
            if column not in columns:
                conn.execute(sql)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                nome_projeto TEXT,
                html_path TEXT NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(lead_id) REFERENCES leads(id)
            )
        """)


init_db()


# ---------------------- Configuração das APIs ----------------------

def get_secret(name, sidebar_label):
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    if not value:
        value = st.sidebar.text_input(sidebar_label, type="password", key=f"key_{name}")
    return value.strip() if value else ""


google_api_key = get_secret("GOOGLE_API_KEY", "Google Places API Key")
groq_api_key = get_secret("GROQ_API_KEY", "Groq API Key")
groq_model = st.sidebar.text_input(
    "Modelo Groq",
    value=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
    help="Use um modelo disponível na sua conta Groq."
).strip()

nome_agencia = st.sidebar.text_input("Nome da sua agência", "DN.Ia Digital")
st.sidebar.caption("DN.Ia 4.1 • Smart Website Studio")


# -------------------------- Funções IA --------------------------

def groq_chat(system_prompt, user_prompt, temperature=0.7, max_tokens=8000):
    if not groq_api_key:
        raise RuntimeError("Adicione sua GROQ_API_KEY na barra lateral ou em st.secrets.")
    client = Groq(api_key=groq_api_key)
    response = client.chat.completions.create(
        model=groq_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()


def strip_code_fence(text):
    text = text.strip()
    text = re.sub(r"^```(?:html)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def save_site(lead_id, html):
    filename = f"site_lead_{lead_id}_{int(time.time())}.html"
    path = SITES_DIR / filename
    path.write_text(html, encoding="utf-8")
    return str(path)


def validate_html(html):
    errors = []
    low = html.lower()
    if "<!doctype html" not in low:
        errors.append("Está faltando <!DOCTYPE html>.")
    if "<html" not in low or "</html>" not in low:
        errors.append("Estrutura HTML incompleta.")
    if "<head" not in low or "<body" not in low:
        errors.append("Verifique as tags head e body.")
    if "viewport" not in low:
        errors.append("Está faltando a configuração viewport para celular.")
    if len(html) < 2500:
        errors.append("O HTML parece curto demais para um site completo.")
    return errors


def create_site_prompt(data, style, briefing, extra_instructions):
    hero_image = data.get("img_hero") or IMAGENS_NICHO.get(
        data.get("nicho", "Outro"), IMAGENS_NICHO["Outro"]
    )
    niche = data.get("nicho", "Outro")
    niche_guidance = {
        "Hamburgueria": "Direção gastronômica urbana: fotografia apetitosa em close, textura, contraste e cardápio visual.",
        "Pizzaria": "Direção gastronômica: fotografia de pizza em destaque, tons quentes, composição artesanal e cardápio organizado.",
        "Barbearia": "Direção masculina/editorial: tons escuros ou terrosos, fotografia de ambiente e detalhes, tipografia forte e serviços bem apresentados.",
        "Sorveteria/Açaí": "Direção fresca e vibrante: cores próprias da marca, fotografia colorida de produtos e composição leve.",
        "Mecânica": "Direção técnica e confiável: contraste alto, fotos reais de oficina/veículos, serviços organizados e CTA de orçamento.",
        "Lava Jato": "Direção automotiva premium: fotos de veículos em destaque, brilho, superfícies escuras e serviços em blocos visuais.",
        "Buffet": "Direção de eventos sofisticada: fotografia ampla, elegância, paleta refinada e galeria de experiências.",
        "Academia": "Direção esportiva: títulos fortes, fotografia de treino, contraste e chamadas para conhecer planos.",
        "Clínica": "Direção clean e acolhedora: bastante respiro, cores suaves, fotografia humana e hierarquia clara.",
        "Restaurante": "Direção editorial gastronômica: fotografia de pratos e ambiente, composição elegante e menu bem organizado.",
        "Loja de roupas": "Direção fashion/e-commerce editorial: campanha visual, fotos grandes, tipografia de revista, categorias e coleções em destaque.",
        "Salão de beleza": "Direção beauty premium: fotografia de beleza, paleta sofisticada, serviços e galeria visual.",
        "Outro": "Escolha uma direção de arte específica para o ramo, sem recorrer a um template genérico.",
    }.get(niche, "Escolha uma direção visual específica para o ramo.")

    return f"""
Você é um estúdio digital premiado, com diretor de arte, UX designer, copywriter e engenheiro front-end.
Sua tarefa é criar um WEBSITE DE VERDADE, com acabamento visual de agência de alto padrão.
As referências de qualidade são sites editoriais e comerciais sofisticados como Vicolo, Gucci Osteria,
portfólios de agências criativas e sites premium de marcas. Use isso como referência de qualidade,
NUNCA copie marcas, textos, logotipos ou layouts exatos.

DADOS DO PROJETO
- Marca: {data.get('nome', 'Marca')}
- Segmento: {niche}
- Cidade: {data.get('cidade', '')}
- Endereço: {data.get('endereco', '')}
- Telefone: {data.get('telefone', '')}
- Imagem principal sugerida: {hero_image}
- Briefing real: {briefing or 'Não informado'}
- Estilo escolhido: {style}
- Orientações adicionais: {extra_instructions or 'Nenhuma'}
- Direção específica do segmento: {niche_guidance}

OBJETIVO VISUAL
O resultado não pode parecer um template pronto, dashboard, landing page genérica ou site escolar.
Crie uma composição com personalidade de marca. Pense primeiro na direção de arte e na hierarquia visual.
Alterne layouts entre seções: blocos assimétricos, imagens full-bleed, colunas editoriais, grids,
sobreposições, fundos alternados e áreas de respiro. Não use a mesma estrutura repetidamente.

REQUISITOS DE DESIGN
1. Hero de impacto: altura generosa, imagem fotográfica forte, título curto e memorável, texto conciso
   e CTA destacado. A composição pode ser assimétrica/editorial, não precisa centralizar tudo.
2. Header refinado com marca tipográfica, navegação clara e CTA. Menu mobile funcional.
3. Crie entre 7 e 10 seções úteis e diferentes, escolhidas conforme o negócio:
   manifesto/apresentação, serviços ou coleções, produtos/destaques, história, diferenciais,
   galeria, processo/experiência, depoimentos somente se fornecidos, FAQ e contato.
4. Use uma seção visual de destaque com imagem grande e texto sobreposto ou ao lado.
5. Use cards somente quando fizer sentido. Evite transformar todo o site em uma grade de cards.
6. Tipografia com contraste de personalidade: serif editorial combinada com sans moderna quando
   combinar com a marca; use fontes via Google Fonts com fallback. Defina escala tipográfica clara.
7. Paleta consistente e sofisticada. Não escolha automaticamente preto e dourado para todos os nichos.
8. Detalhes de acabamento: linhas finas, microtextos, números de seção, etiquetas, estados hover,
   transições suaves e pequenos elementos gráficos. Sem exagerar nos efeitos.
9. Rodapé completo, elegante e organizado.
10. O site precisa parecer uma marca real e exclusiva, não uma apresentação de IA.

IMPLEMENTAÇÃO
- Retorne APENAS um documento HTML5 completo, começando por <!DOCTYPE html>.
- CSS dentro de <style>; JavaScript vanilla pequeno, sem frameworks pesados.
- Responsivo de verdade em 360px, tablet e desktop. Inclua menu mobile acessível.
- Use CSS Grid/Flexbox, variáveis CSS, estados hover/focus, prefers-reduced-motion.
- Imagens: use URLs diretas de imagens Unsplash relevantes e diferentes entre si; não repita a imagem hero
  em todas as seções. Use object-fit, proporções intencionais, alt descritivo e loading="lazy".
  A imagem principal sugerida pode ser usada no hero. Não invente imagens com URLs aleatórias:
  prefira IDs conhecidos de images.unsplash.com ou imagens já fornecidas no briefing.
- Inclua favicon simples em SVG data URI ou omita.
- CTAs devem funcionar: telefone/WhatsApp apenas se o número informado for válido; links internos devem
  apontar para IDs existentes; formulário deve ter comportamento claro (mailto ou WhatsApp quando possível).
- Se houver endereço, crie link de rota do Google Maps usando o endereço codificado.
- Não invente preços, horários, avaliações, prêmios, certificações, anos de mercado, equipe,
  redes sociais, endereços ou números. Não crie depoimentos fictícios.
- Não use lorem ipsum, textos genéricos, placeholders ou dados falsos.
- Escreva em português brasileiro natural, com copy específica para o segmento.
- Inclua meta description, title, viewport e HTML semântico.
- Garanta contraste, foco visível, labels acessíveis e navegação por teclado.
- Evite dependências desnecessárias. O site deve continuar apresentável se uma fonte externa falhar.

CHECKLIST FINAL
Antes de retornar, revise mentalmente o resultado em desktop e mobile. Confira se:
header e menu funcionam; hero é realmente marcante; cada seção tem composição diferente;
as imagens são coerentes; não há conteúdo inventado; botões e âncoras funcionam;
não existe overflow horizontal no celular; o rodapé fecha o projeto com qualidade.
Se algum item falhar, corrija antes de responder.
"""


def audit_and_repair(html, data):
    system = (
        "Você é um engenheiro front-end sênior e auditor de qualidade. "
        "Corrija o HTML sem remover funcionalidades importantes. "
        "Retorne somente o HTML completo final."
    )
    user = f"""
Revise e melhore este site para a empresa {data['nome']} ({data['nicho']}).

Verifique especialmente:
- responsividade real em telas pequenas;
- menu mobile e funcionamento dos CTAs;
- contraste, legibilidade e hierarquia;
- consistência de cores, fontes e espaçamentos;
- qualidade de direção de arte e personalidade visual;
- variedade de composição entre as seções (não transformar tudo em cards);
- força do hero, hierarquia editorial e equilíbrio de espaços;
- imagens, alt text e carregamento;
- seções repetidas, textos genéricos e elementos quebrados;
- erros de HTML, CSS e JavaScript;
- links de contato e mapa, sem inventar dados.

Não invente informações comerciais. Preserve o conteúdo correto e melhore o acabamento.
Retorne o documento HTML completo, começando por <!DOCTYPE html>.

HTML PARA AUDITAR:
{html}
"""
    return strip_code_fence(groq_chat(system, user, temperature=0.25, max_tokens=10000))


# ---------------------- Google Places / prospecção ----------------------

def search_places(nicho, cidade, estado, nota_minima, max_results=20):
    if not google_api_key:
        raise RuntimeError("Configure a Google Places API Key.")
    endpoint = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": google_api_key,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,"
            "places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri,places.rating"
        ),
    }
    payload = {
        "textQuery": f"{nicho} em {cidade}, {estado}",
        "maxResultCount": max_results,
        "languageCode": "pt-BR",
        "regionCode": "BR",
    }
    response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
    if not response.ok:
        raise RuntimeError(f"Google Places retornou {response.status_code}: {response.text[:500]}")
    places = response.json().get("places", [])
    return [
        place for place in places
        if not place.get("websiteUri") and float(place.get("rating", 0) or 0) >= nota_minima
    ]


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
            (nome, endereco, telefone, nicho, cidade, nota, status, google_place_id)
            VALUES (?, ?, ?, ?, ?, ?, 'Novo Lead', ?)
        """, (
            nome,
            place.get("formattedAddress", ""),
            place.get("nationalPhoneNumber", ""),
            nicho,
            cidade,
            float(place.get("rating", 0) or 0),
            place_id,
        ))
    return True


def make_outreach_message(lead, agency, site_url=""):
    phone_note = ""
    if site_url:
        return (
            f"Olá! Tudo bem? Sou da {agency}. Estava conhecendo empresas de "
            f"{lead['nicho'] or 'seu segmento'} em {lead['cidade'] or 'sua região'} "
            f"e preparei uma demonstração de site para {lead['nome']}. "
            f"Você pode visualizar por aqui: {site_url}. "
            "Se fizer sentido para vocês, posso explicar como personalizar e publicar."
        )
    return (
        f"Olá! Tudo bem? Sou da {agency}. Conheci a {lead['nome']} e gostaria "
        "de apresentar uma ideia de site para ajudar a empresa a divulgar seus "
        "produtos e facilitar o contato com clientes. Posso enviar uma demonstração?"
    )


# --------------------------- Estado da sessão ---------------------------

defaults = {
    "radio_menu": "Dashboard",
    "temp_leads": [],
    "lead_id_ativo": None,
    "studio_data": {},
    "studio_step": 1,
    "generated_html": "",
    "last_saved_path": "",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ------------------------------- Sidebar -------------------------------

st.sidebar.title("🧠 DN.Ia 4.1")
st.sidebar.caption("SMART WEBSITE ENGINE")
menu_items = ["Dashboard", "Prospecção", "CRM", "Studio IA", "Projetos", "Relatórios"]
menu = st.sidebar.radio("Navegação", menu_items, key="radio_menu")
st.sidebar.divider()
st.sidebar.caption("Dica: guarde suas chaves em `.streamlit/secrets.toml`.")
st.sidebar.code('GOOGLE_API_KEY = "sua-chave"\nGROQ_API_KEY = "sua-chave"', language="toml")


# ================================ DASHBOARD ================================

if menu == "Dashboard":
    st.title("Dashboard")
    st.write("Visão geral da sua operação comercial.")
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        demos = conn.execute("SELECT COUNT(*) FROM leads WHERE html_path IS NOT NULL OR site_url IS NOT NULL").fetchone()[0]
        fechados = conn.execute("SELECT COUNT(*) FROM leads WHERE status = 'Fechado'").fetchone()[0]
        novos = conn.execute("SELECT COUNT(*) FROM leads WHERE status = 'Novo Lead'").fetchone()[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads cadastrados", total)
    c2.metric("Sites/demonstrações", demos)
    c3.metric("Contratos fechados", fechados)
    c4.metric("Novos leads", novos)

    st.subheader("Comece por aqui")
    a, b, c = st.columns(3)
    with a:
        st.markdown("### 🔎 Prospecção")
        st.write("Encontre empresas e identifique oportunidades.")
        if st.button("Abrir prospecção", use_container_width=True):
            st.session_state.radio_menu = "Prospecção"
            st.rerun()
    with b:
        st.markdown("### 🧩 Studio IA")
        st.write("Crie e revise sites personalizados.")
        if st.button("Abrir Studio IA", use_container_width=True):
            st.session_state.radio_menu = "Studio IA"
            st.rerun()
    with c:
        st.markdown("### 📇 CRM")
        st.write("Organize contatos e acompanhe negociações.")
        if st.button("Abrir CRM", use_container_width=True):
            st.session_state.radio_menu = "CRM"
            st.rerun()


# ================================ PROSPECÇÃO ================================

elif menu == "Prospecção":
    st.title("Prospecção")
    st.write("Encontre empresas que podem se beneficiar de um site.")

    col1, col2, col3 = st.columns(3)
    with col1:
        nicho = st.selectbox("Segmento", NICHOS)
    with col2:
        estado = st.selectbox("Estado", list(CIDADES_BR.keys()))
    with col3:
        if estado == "Outro":
            cidade = st.text_input("Cidade")
        else:
            cidade = st.selectbox("Cidade", CIDADES_BR[estado])

    nota_minima = st.slider("Nota mínima no Google", 0.0, 5.0, 4.0, 0.1)
    quantidade = st.select_slider("Quantidade máxima", options=[5, 10, 15, 20], value=20)

    if st.button("🔎 Buscar empresas", type="primary"):
        if not cidade.strip():
            st.warning("Informe uma cidade.")
        else:
            try:
                with st.spinner("Consultando empresas no Google Places..."):
                    st.session_state.temp_leads = search_places(
                        nicho, cidade, estado, nota_minima, quantidade
                    )
                st.success(f"{len(st.session_state.temp_leads)} oportunidade(s) encontrada(s).")
            except Exception as exc:
                st.error(str(exc))

    if st.session_state.temp_leads:
        st.subheader("Oportunidades encontradas")
        for idx, place in enumerate(st.session_state.temp_leads):
            nome = place.get("displayName", {}).get("text", "Empresa sem nome")
            endereco = place.get("formattedAddress", "Endereço não informado")
            nota = place.get("rating", "Sem nota")
            telefone = place.get("nationalPhoneNumber", "Telefone não informado")
            with st.container(border=True):
                info, action = st.columns([4, 1])
                with info:
                    st.markdown(f"**{nome}**  ⭐ {nota}")
                    st.caption(f"📍 {endereco}")
                    st.caption(f"☎️ {telefone}")
                with action:
                    if st.button("Adicionar ao CRM", key=f"add_{idx}", use_container_width=True):
                        try:
                            added = add_lead(place, nicho, cidade)
                            if added:
                                st.success("Lead adicionado!")
                            else:
                                st.info("Essa empresa já está cadastrada.")
                        except Exception as exc:
                            st.error(f"Não foi possível cadastrar: {exc}")


# ================================= CRM =================================

elif menu == "CRM":
    st.title("CRM")
    st.write("Gerencie seus contatos e oportunidades.")

    with st.expander("➕ Cadastrar lead manualmente"):
        with st.form("manual_lead"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome da empresa")
            telefone = c2.text_input("Telefone")
            endereco = c1.text_input("Endereço")
            cidade_manual = c2.text_input("Cidade")
            nicho_manual = st.selectbox("Segmento", NICHOS, key="manual_nicho")
            submitted = st.form_submit_button("Salvar lead")
            if submitted:
                if not nome.strip():
                    st.error("Informe o nome da empresa.")
                else:
                    with db() as conn:
                        conn.execute("""
                            INSERT INTO leads (nome, telefone, endereco, cidade, nicho, status)
                            VALUES (?, ?, ?, ?, ?, 'Novo Lead')
                        """, (nome.strip(), telefone.strip(), endereco.strip(),
                              cidade_manual.strip(), nicho_manual))
                    st.success("Lead cadastrado.")
                    st.rerun()

    with db() as conn:
        leads = conn.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()

    if not leads:
        st.info("Nenhum lead cadastrado. Use a Prospecção ou cadastre manualmente.")
    else:
        filter_status = st.selectbox(
            "Filtrar por status",
            ["Todos", "Novo Lead", "Demonstração Criada", "Abordado", "Fechado", "Perdido"]
        )
        for lead in leads:
            if filter_status != "Todos" and lead["status"] != filter_status:
                continue
            with st.expander(f"🏢 {lead['nome']} — {lead['status']}"):
                st.write(f"📍 {lead['endereco'] or 'Endereço não informado'}")
                st.write(f"☎️ {lead['telefone'] or 'Telefone não informado'}")
                st.write(f"Segmento: {lead['nicho'] or 'Não informado'} • ⭐ {lead['nota'] or 0}")

                c1, c2, c3 = st.columns([2, 1, 1])
                status_options = ["Novo Lead", "Demonstração Criada", "Abordado", "Fechado", "Perdido"]
                current_index = status_options.index(lead["status"]) if lead["status"] in status_options else 0
                new_status = c1.selectbox(
                    "Status", status_options, index=current_index, key=f"status_{lead['id']}"
                )
                if c1.button("Atualizar status", key=f"update_{lead['id']}"):
                    with db() as conn:
                        conn.execute("UPDATE leads SET status = ? WHERE id = ?",
                                     (new_status, lead["id"]))
                    st.success("Status atualizado.")
                    st.rerun()

                if c2.button("Criar site", key=f"site_{lead['id']}", use_container_width=True):
                    st.session_state.lead_id_ativo = lead["id"]
                    st.session_state.studio_data = {
                        "nome": lead["nome"],
                        "nicho": lead["nicho"] or "Outro",
                        "cidade": lead["cidade"] or "",
                        "endereco": lead["endereco"] or "",
                        "telefone": lead["telefone"] or "",
                        "nota": lead["nota"] or 0,
                        "img_hero": IMAGENS_NICHO.get(lead["nicho"], IMAGENS_NICHO["Outro"]),
                    }
                    st.session_state.studio_step = 1
                    st.session_state.radio_menu = "Studio IA"
                    st.rerun()

                if c3.button("Mensagem", key=f"msg_{lead['id']}", use_container_width=True):
                    st.session_state["message_lead_id"] = lead["id"]

                if lead["site_url"]:
                    st.markdown(f"[🌐 Abrir demonstração publicada]({lead['site_url']})")
                if lead["html_path"] and Path(lead["html_path"]).exists():
                    st.download_button(
                        "Baixar HTML",
                        data=Path(lead["html_path"]).read_bytes(),
                        file_name=f"site_{lead['id']}.html",
                        mime="text/html",
                        key=f"download_{lead['id']}",
                    )

                if st.session_state.get("message_lead_id") == lead["id"]:
                    msg = make_outreach_message(lead, nome_agencia, lead["site_url"] or "")
                    st.text_area("Mensagem sugerida", msg, key=f"message_text_{lead['id']}")
                    digits = re.sub(r"\D", "", lead["telefone"] or "")
                    if digits:
                        if digits.startswith("55"):
                            whatsapp_number = digits
                        else:
                            whatsapp_number = "55" + digits
                        wa_url = "https://wa.me/" + whatsapp_number + "?text=" + urllib.parse.quote(msg)
                        st.link_button("Abrir WhatsApp", wa_url)


# ============================== STUDIO IA ==============================

elif menu == "Studio IA":
    st.title("Studio IA")
    st.caption("Smart Website Engine • briefing, direção de arte, geração e auditoria")

    if st.session_state.lead_id_ativo is None:
        st.info("Abra um lead no CRM para iniciar um projeto. Você também pode cadastrar um lead manualmente.")
        if st.button("Ir para o CRM"):
            st.session_state.radio_menu = "CRM"
            st.rerun()
    else:
        data = st.session_state.studio_data
        step = st.session_state.studio_step

        steps = [
            "Briefing", "Direção de arte", "Geração", "Auditoria",
            "Prévia", "Salvar projeto"
        ]
        st.progress(step / len(steps))
        st.caption(f"Etapa {step} de {len(steps)} — {steps[step - 1]}")

        with st.container(border=True):
            st.markdown(f"### {data['nome']}")
            st.caption(f"{data['nicho']} • {data.get('cidade', '')}")

        if step == 1:
            st.subheader("1. Briefing inteligente")
            st.write("Confira os dados e acrescente informações reais para deixar o site mais convincente.")
            with st.form("studio_briefing"):
                c1, c2 = st.columns(2)
                nome_edit = c1.text_input("Nome da empresa", data["nome"])
                nicho_edit = c2.selectbox(
                    "Segmento", NICHOS,
                    index=NICHOS.index(data["nicho"]) if data["nicho"] in NICHOS else len(NICHOS)-1
                )
                cidade_edit = c1.text_input("Cidade", data.get("cidade", ""))
                telefone_edit = c2.text_input("Telefone/WhatsApp", data.get("telefone", ""))
                endereco_edit = st.text_input("Endereço", data.get("endereco", ""))
                descricao = st.text_area(
                    "O que a empresa oferece? Diferenciais, produtos e serviços",
                    data.get("briefing", ""),
                    placeholder="Ex.: hamburguer artesanal, ingredientes selecionados, delivery e atendimento no local."
                )
                estilo = st.selectbox("Direção visual", ESTILOS)
                extra = st.text_area(
                    "Detalhes adicionais (opcional)",
                    placeholder="Ex.: usar tons terrosos, destacar delivery, botão de orçamento..."
                )
                if st.form_submit_button("Salvar briefing e continuar", type="primary"):
                    if not nome_edit.strip():
                        st.error("O nome da empresa é obrigatório.")
                    else:
                        data.update({
                            "nome": nome_edit.strip(),
                            "nicho": nicho_edit,
                            "cidade": cidade_edit.strip(),
                            "telefone": telefone_edit.strip(),
                            "endereco": endereco_edit.strip(),
                            "briefing": descricao.strip(),
                            "estilo": estilo,
                            "extra": extra.strip(),
                        })
                        st.session_state.studio_data = data
                        st.session_state.studio_step = 2
                        st.rerun()

        elif step == 2:
            st.subheader("2. Direção de arte")
            st.write("A IA vai propor uma identidade visual coerente com o negócio.")
            if st.button("✨ Criar direção de arte", type="primary"):
                try:
                    with st.spinner("Analisando segmento, público e identidade visual..."):
                        prompt = f"""
Atue como diretor de criação de uma agência digital de alto padrão.
Crie um briefing de direção de arte que será usado por um desenvolvedor para construir
um site original, visualmente marcante e comercialmente útil.

MARCA: {data['nome']}
SEGMENTO: {data['nicho']}
CIDADE: {data.get('cidade', '')}
BRIEFING: {data.get('briefing', '')}
PREFERÊNCIA: {data.get('estilo', ESTILOS[0])}
INSTRUÇÕES: {data.get('extra', '')}

Entregue uma especificação prática com:
1. Conceito criativo e personalidade da marca em 3 a 5 linhas.
2. Paleta com HEX: fundo, superfície, texto, texto secundário, destaque e cor de apoio.
3. Combinação tipográfica: fonte de títulos, fonte de textos e pesos.
4. Direção de fotografia: assunto, luz, enquadramento, textura e tratamento.
5. Layout do hero: posição do texto, imagem, CTA e composição.
6. Plano de 8 seções, cada uma com estrutura visual diferente.
7. Componentes: header, botões, links, cards quando necessários, galeria e rodapé.
8. Regras para mobile: o que empilha, o que vira carrossel e como manter hierarquia.
9. Três detalhes de acabamento que deem identidade ao projeto.
Use referências de qualidade editorial e de agência premium, sem copiar sites existentes.
Não invente informações comerciais. Seja específico para este segmento.
"""
                        art = groq_chat(
                            "Você é diretor de criação e designer de produtos digitais de uma agência premium.",
                            prompt, temperature=0.65, max_tokens=1800
                        )
                    data["direcao_arte"] = art
                    st.session_state.studio_data = data
                    st.session_state.studio_step = 3
                    st.rerun()
                except Exception as exc:
                    st.error(f"Falha ao criar direção de arte: {exc}")

            if data.get("direcao_arte"):
                st.markdown("#### Direção salva")
                st.write(data["direcao_arte"])

        elif step == 3:
            st.subheader("3. Geração do site")
            st.write("O motor vai criar uma página completa com identidade visual e conteúdo específico.")
            st.image(data.get("img_hero", IMAGENS_NICHO["Outro"]), width=360,
                     caption="Imagem sugerida para o destaque — pode ser substituída no HTML depois.")
            if st.button("🚀 Gerar site profissional", type="primary"):
                try:
                    with st.spinner("Desenvolvendo layout, conteúdo, CSS e interações..."):
                        prompt = create_site_prompt(
                            data,
                            data.get("estilo", ESTILOS[0]) + "\n" + data.get("direcao_arte", ""),
                            data.get("briefing", ""),
                            data.get("extra", ""),
                        )
                        html = strip_code_fence(groq_chat(
                            "Você é uma equipe de agência digital premium: diretor de arte, UX/UI designer, copywriter e engenheiro front-end sênior. Construa um site completo, original e visualmente sofisticado. Siga o briefing e retorne somente HTML válido.",
                            prompt,
                            temperature=0.82,
                            max_tokens=12000,
                        ))
                    data["html"] = html
                    data["validation_errors"] = validate_html(html)
                    st.session_state.studio_data = data
                    st.session_state.studio_step = 4
                    st.rerun()
                except Exception as exc:
                    st.error(f"Não foi possível gerar o site: {exc}")

        elif step == 4:
            st.subheader("4. Auditoria e correção automática")
            html = data.get("html", "")
            errors = validate_html(html)
            if errors:
                st.warning("A validação inicial encontrou pontos para revisar:")
                for error in errors:
                    st.write(f"- {error}")
            else:
                st.success("Estrutura básica do HTML aprovada.")

            st.write("A auditoria com IA revisa responsividade, acessibilidade, links e consistência visual.")
            if st.button("🔧 Auditar e melhorar o site", type="primary"):
                try:
                    with st.spinner("Revisando e corrigindo o código..."):
                        repaired = audit_and_repair(html, data)
                    data["html"] = repaired
                    data["validation_errors"] = validate_html(repaired)
                    data["audit_done"] = True
                    st.session_state.studio_data = data
                    st.success("Auditoria concluída.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Falha na auditoria: {exc}")

            if data.get("audit_done"):
                if data.get("validation_errors"):
                    st.warning("Ainda existem avisos estruturais:")
                    for error in data["validation_errors"]:
                        st.write(f"- {error}")
                else:
                    st.success("Validação estrutural aprovada.")
                if st.button("Continuar para prévia"):
                    st.session_state.studio_step = 5
                    st.rerun()

            with st.expander("Ver/editar código HTML"):
                edited_html = st.text_area("HTML completo", value=html, height=350)
                if st.button("Salvar edição do HTML"):
                    data["html"] = edited_html
                    data["validation_errors"] = validate_html(edited_html)
                    st.session_state.studio_data = data
                    st.success("Código atualizado.")

        elif step == 5:
            st.subheader("5. Prévia responsiva")
            html = data.get("html", "")
            mode = st.radio("Tamanho da prévia", ["Desktop", "Celular"], horizontal=True)
            width = 390 if mode == "Celular" else 1100
            st.caption("A prévia é renderizada em um iframe do Streamlit. Teste os botões e navegação.")
            components.html(html, height=760, width=width, scrolling=True)
            with st.expander("Ver código-fonte"):
                st.code(html, language="html")
            if st.button("Continuar para salvar projeto", type="primary"):
                st.session_state.studio_step = 6
                st.rerun()

        elif step == 6:
            st.subheader("6. Salvar projeto")
            st.write("Salve o HTML no seu ambiente e, se desejar, baixe o arquivo para publicar em uma hospedagem.")
            html = data.get("html", "")
            if not html:
                st.error("Não há HTML gerado. Volte e gere o site novamente.")
            else:
                if st.button("💾 Salvar projeto no DN.Ia", type="primary"):
                    try:
                        path = save_site(st.session_state.lead_id_ativo, html)
                        with db() as conn:
                            conn.execute("""
                                UPDATE leads
                                SET html_path = ?, status = 'Demonstração Criada'
                                WHERE id = ?
                            """, (path, st.session_state.lead_id_ativo))
                            conn.execute("""
                                INSERT INTO projects (lead_id, nome_projeto, html_path)
                                VALUES (?, ?, ?)
                            """, (st.session_state.lead_id_ativo, data["nome"], path))
                        data["html_path"] = path
                        st.session_state.studio_data = data
                        st.session_state.last_saved_path = path
                        st.success("Projeto salvo no DN.Ia.")
                    except Exception as exc:
                        st.error(f"Erro ao salvar: {exc}")

                if data.get("html_path") and Path(data["html_path"]).exists():
                    st.download_button(
                        "⬇️ Baixar site em HTML",
                        data=Path(data["html_path"]).read_bytes(),
                        file_name=f"{re.sub(r'[^a-zA-Z0-9_-]', '_', data['nome'].lower())}.html",
                        mime="text/html",
                        use_container_width=True,
                    )

                # Integração opcional. Só será usada se o endpoint e formato estiverem válidos.
                st.divider()
                st.markdown("#### Publicação externa (opcional)")
                st.caption("A publicação depende de um serviço de hospedagem e de uma API válida. O salvamento/HTML para download funciona independentemente disso.")
                publish_url = st.text_input(
                    "Endpoint de publicação compatível (opcional)",
                    value=os.getenv("DNIA_PUBLISH_ENDPOINT", ""),
                    help="Deixe em branco se ainda não configurou um serviço de hospedagem."
                )
                if st.button("Publicar pelo endpoint configurado", disabled=not publish_url.strip()):
                    try:
                        response = requests.post(
                            publish_url.strip(),
                            json={"content": html},
                            headers={"Content-Type": "application/json"},
                            timeout=45,
                        )
                        response.raise_for_status()
                        result = response.json()
                        link = result.get("link") or result.get("url")
                        if not link:
                            st.error("O serviço respondeu, mas não retornou um campo 'link' ou 'url'.")
                        else:
                            with db() as conn:
                                conn.execute(
                                    "UPDATE leads SET site_url = ? WHERE id = ?",
                                    (link, st.session_state.lead_id_ativo)
                                )
                            st.success("Publicação concluída.")
                            st.markdown(f"[Abrir site publicado]({link})")
                    except Exception as exc:
                        st.error(f"Falha na publicação: {exc}")

                lead = None
                with db() as conn:
                    lead = conn.execute(
                        "SELECT * FROM leads WHERE id = ?",
                        (st.session_state.lead_id_ativo,)
                    ).fetchone()
                if lead:
                    message = make_outreach_message(lead, nome_agencia, lead["site_url"] or "")
                    st.text_area("Mensagem sugerida para apresentar a demonstração", message, height=130)
                    digits = re.sub(r"\D", "", lead["telefone"] or "")
                    if digits:
                        number = digits if digits.startswith("55") else "55" + digits
                        wa = "https://wa.me/" + number + "?text=" + urllib.parse.quote(message)
                        st.link_button("Abrir conversa no WhatsApp", wa)

                if st.button("Finalizar e voltar ao CRM"):
                    st.session_state.lead_id_ativo = None
                    st.session_state.studio_data = {}
                    st.session_state.studio_step = 1
                    st.session_state.radio_menu = "CRM"
                    st.rerun()

        nav1, nav2 = st.columns(2)
        with nav1:
            if step > 1 and st.button("← Voltar uma etapa"):
                st.session_state.studio_step -= 1
                st.rerun()
        with nav2:
            if step < 6 and st.button("Reiniciar projeto"):
                st.session_state.studio_step = 1
                st.session_state.studio_data = {
                    **data,
                    "html": "",
                    "direcao_arte": "",
                    "audit_done": False,
                }
                st.rerun()


# ================================ PROJETOS ================================

elif menu == "Projetos":
    st.title("Projetos")
    st.write("Sites e demonstrações salvos no DN.Ia.")
    with db() as conn:
        projects = conn.execute("""
            SELECT p.*, l.nome AS lead_nome, l.site_url
            FROM projects p
            JOIN leads l ON l.id = p.lead_id
            ORDER BY p.id DESC
        """).fetchall()

    if not projects:
        st.info("Nenhum projeto salvo ainda. Gere um site no Studio IA.")
    else:
        for project in projects:
            with st.container(border=True):
                st.markdown(f"**{project['nome_projeto'] or project['lead_nome']}**")
                st.caption(f"Criado em {project['criado_em']}")
                path = Path(project["html_path"])
                if path.exists():
                    st.download_button(
                        "Baixar HTML",
                        data=path.read_bytes(),
                        file_name=f"projeto_{project['id']}.html",
                        mime="text/html",
                        key=f"project_download_{project['id']}",
                    )
                if project["site_url"]:
                    st.markdown(f"[Abrir site publicado]({project['site_url']})")


# ================================ RELATÓRIOS ================================

elif menu == "Relatórios":
    st.title("Relatórios")
    st.write("Indicadores simples da operação.")
    with db() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS total FROM leads GROUP BY status"
        ).fetchall()
    counts = {row["status"]: row["total"] for row in rows}
    order = ["Novo Lead", "Demonstração Criada", "Abordado", "Fechado", "Perdido"]
    total = sum(counts.values())
    if total == 0:
        st.info("Cadastre leads para começar a visualizar os relatórios.")
    else:
        cols = st.columns(5)
        for col, status in zip(cols, order):
            col.metric(status, counts.get(status, 0))
        closed = counts.get("Fechado", 0)
        st.metric("Conversão em contratos", f"{(closed / total * 100):.1f}%")
        st.caption("A taxa acima considera contratos fechados divididos pelo total de leads cadastrados.")
