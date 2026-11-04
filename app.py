import streamlit as st
import requests
import re
import urllib.parse
import sqlite3
import time
from groq import Groq

st.set_page_config(page_title="DN.Ia 3.0", layout="wide", page_icon="🧠")

# --- CSS PERSONALIZADO (Visual de Software Profissional) ---
st.markdown("""
    <style>
    /* Tema Dark Premium */
    .stApp { background-color: #0B0E14; color: #E2E8F0; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #121620; border-right: 1px solid #1E293B; }
    section[data-testid="stSidebar"] h1 { color: #3B82F6; font-size: 24px; font-weight: 800; letter-spacing: -0.5px; }
    
    /* Botões */
    .stButton>button {
        background-color: #3B82F6; color: white; font-weight: bold;
        border-radius: 6px; border: none; padding: 10px 24px; transition: all 0.2s;
    }
    .stButton>button:hover { background-color: #2563EB; color: white; transform: translateY(-1px); }
    
    /* Inputs */
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stSlider {
        background-color: #1E293B; color: white; border-radius: 6px; border: 1px solid #334155;
    }
    
    /* Cards */
    div[data-testid="stExpander"] { background-color: #121620; border-radius: 8px; border: 1px solid #1E293B; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: transparent; border-radius: 4px 4px 0 0; gap: 1px; padding-top: 10px; padding-bottom: 10px; }
    .stTabs [aria-selected="true"] { background-color: #1E293B; color: #3B82F6; border-bottom: 2px solid #3B82F6; }
    
    /* Links */
    .action-link { text-decoration: none; color: #10B981; margin-right: 15px; font-weight: bold; }
    .action-link:hover { color: #34D399; }
    
    h1, h2, h3 { color: #F8FAFC !important; }
    </style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS (SQLite) ---
def init_db():
    conn = sqlite3.connect('dn_ia.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT, endereco TEXT, telefone TEXT, 
                    nicho TEXT, cidade TEXT, nota REAL, 
                    status TEXT, site_url TEXT, data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('dn_ia.db')
    conn.row_factory = sqlite3.Row
    return conn

init_db()

# --- LISTAS ---
NICHOS = ["Hamburgueria", "Pizzaria", "Barbearia", "Sorveteria/Açaí", "Mecânica", "Lava Jato", "Buffet", "Academia", "Outro"]
CIDADES_BR = {
    "Minas Gerais": ["Belo Horizonte", "Uberlândia", "Cataguases", "Juiz de Fora"],
    "São Paulo": ["São Paulo", "Campinas", "Santos"],
    "Piauí": ["Teresina", "Parnaíba", "Picos", "Timon"],
    "Outro": ["Digitar manualmente"]
}
IMAGENS_NICHO = {
    "Hamburgueria": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?q=80&w=2000&auto=format&fit=crop",
    "Pizzaria": "https://images.unsplash.com/photo-1513104890138-7c749659a591?q=80&w=2000&auto=format&fit=crop",
    "Barbearia": "https://images.unsplash.com/photo-1585747860715-2ba37e788b70?q=80&w=2000&auto=format&fit=crop",
    "Academia": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?q=80&w=2000&auto=format&fit=crop",
    "Mecânica": "https://images.unsplash.com/photo-1520340356584-f9917d1eea6f?q=80&w=2000&auto=format&fit=crop",
    "Outro": "https://images.unsplash.com/photo-1497366216548-37526070297c?q=80&w=2000&auto=format&fit=crop"
}

# --- CHAVES DE API ---
if "GOOGLE_API_KEY" in st.secrets: api_key = st.secrets["GOOGLE_API_KEY"]
else: api_key = st.sidebar.text_input("Google Maps API Key:", type="password")

if "GROQ_API_KEY" in st.secrets: groq_key = st.secrets["GROQ_API_KEY"]
else: groq_key = st.sidebar.text_input("Groq API Key:", type="password")

# --- ESTADO DO STUDIO IA ---
if 'studio_step' not in st.session_state: st.session_state.studio_step = 1
if 'studio_data' not in st.session_state: st.session_state.studio_data = {}
if 'lead_id_ativo' not in st.session_state: st.session_state.lead_id_ativo = None

# --- FUNÇÕES AUXILIARES ---
def call_groq(system_prompt, user_prompt):
    client = Groq(api_key=groq_key)
    response = client.chat.completions.create(
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        model="openai/gpt-oss-120b",
    )
    return response.choices[0].message.content

def hospedar_brewpage(codigo_html):
    url_brewpage = "https://brewpage.app/api/html"
    resposta = requests.post(url_brewpage, json={'content': codigo_html}, headers={'Content-Type': 'application/json'})
    if resposta.status_code in [200, 201]:
        return resposta.json().get('link')
    return None

def gerar_mensagem_abordagem(nome, nicho, cidade, nota, link_site=None, nome_agencia="DN.Ia"):
    if link_site:
        return f"Olá, tudo bem? Sou o consultor da {nome_agencia}. Estava procurando {nicho.lower()}s em {cidade} e vi que a de vocês tem nota {nota}, parabéns! Notei que vocês não têm um site. Criei uma prévia de como ficaria o site da sua empresa. Dá uma olhada: {link_site}. Se gostar, eu te explico como colocar no ar."
    return f"Olá! Sou da {nome_agencia}. Notei que a {nome} tem nota {nota} no Google, mas não tem um site. Posso te mandar uma prévia?"

# ==========================================
# NAVEGAÇÃO LATERAL
# ==========================================
st.sidebar.title("DN.Ia 3.0")
st.sidebar.markdown("<p style='color: #64748B; font-size: 12px; margin-top: -15px;'>DIGITAL BUSINESS INTELLIGENCE</p>", unsafe_allow_html=True)

menu = st.sidebar.radio("Navegação", ["Dashboard", "Prospecção", "CRM", "Studio IA", "Projetos", "Relatórios"])

st.sidebar.markdown("---")
nome_agencia = st.sidebar.text_input("Nome da sua agência:", "Minha Agência Digital")

# ==========================================
# PÁGINAS
# ==========================================

# --- DASHBOARD ---
if menu == "Dashboard":
    st.title("Dashboard")
    st.write("Visão geral da operação.")
    
    conn = get_db_connection()
    total_leads = conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0]
    sites_gerados = conn.execute('SELECT COUNT(*) FROM leads WHERE site_url IS NOT NULL').fetchone()[0]
    fechados = conn.execute('SELECT COUNT(*) FROM leads WHERE status = "Fechado"').fetchone()[0]
    conn.close()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Leads Prospectados", total_leads)
    col2.metric("Demonstrações Criadas", sites_gerados)
    col3.metric("Contratos Fechados", fechados)

# --- PROSPECÇÃO ---
elif menu == "Prospecção":
    st.title("Prospecção")
    st.write("Encontrar oportunidades sem site.")
    
    col1, col2, col3 = st.columns(3)
    with col1: nicho = st.selectbox("Segmento:", NICHOS)
    with col2: estado = st.selectbox("Estado:", list(CIDADES_BR.keys()))
    with col3: cidade = st.text_input("Cidade:", "") if estado == "Outro" else st.selectbox("Cidade:", CIDADES_BR[estado])
    
    nota_minima = st.slider("Nota mínima no Google:", 0.0, 5.0, 4.0, 0.1)
    
    if st.button("Buscar Empresas"):
        if not api_key: st.error("Configure a Google API Key.")
        else:
            with st.spinner('Buscando...'):
                try:
                    url = "https://places.googleapis.com/v1/places:searchText"
                    headers = {'Content-Type': 'application/json', 'X-Goog-Api-Key': api_key, 'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri,places.rating'}
                    payload = {"textQuery": f"{nicho} em {cidade}, {estado}", "maxResultCount": 20}
                    response = requests.post(url, json=payload, headers=headers)
                    places = response.json().get('places', [])
                    
                    results = [p for p in places if 'websiteUri' not in p and p.get('rating', 0) >= nota_minima]
                    st.session_state.temp_leads = results
                except Exception as e: st.error(f"Erro: {e}")

    if 'temp_leads' in st.session_state and st.session_state.temp_leads:
        st.markdown("### Oportunidades Encontradas")
        for i, lead in enumerate(st.session_state.temp_leads):
            nome = lead.get('displayName', {}).get('text')
            end = lead.get('formattedAddress', '')
            nota = lead.get('rating', 0)
            tel = lead.get('nationalPhoneNumber', '')
            
            with st.container(border=True):
                col_info, col_btn = st.columns([4, 1])
                with col_info:
                    st.markdown(f"**{nome}** ⭐ {nota}")
                    st.write(f"📍 {end}")
                with col_btn:
                    if st.button("Adicionar ao CRM", key=f"add_{i}"):
                        conn = get_db_connection()
                        conn.execute('INSERT INTO leads (nome, endereco, telefone, nicho, cidade, nota, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
                                     (nome, end, tel, nicho, cidade, nota, "Novo Lead"))
                        conn.commit()
                        conn.close()
                        st.success("Adicionado ao CRM!")

# --- CRM ---
elif menu == "CRM":
    st.title("CRM")
    st.write("Organizar e fechar vendas.")
    
    conn = get_db_connection()
    leads = conn.execute('SELECT * FROM leads ORDER BY id DESC').fetchall()
    
    if not leads:
        st.info("Nenhum lead no CRM. Vá em 'Prospecção' para adicionar.")
    else:
        for lead in leads:
            with st.expander(f"🏢 {lead['nome']} - Status: {lead['status']}"):
                st.write(f"📍 {lead['endereco']} | 📞 {lead['telefone']} | ⭐ {lead['nota']}")
                
                col_status, col_acao = st.columns([2, 1])
                with col_status:
                    novo_status = st.selectbox("Status:", ["Novo Lead", "Demonstração Criada", "Abordado", "Fechado", "Perdido"], 
                                             index=["Novo Lead", "Demonstração Criada", "Abordado", "Fechado", "Perdido"].index(lead['status']), key=f"st_{lead['id']}")
                    if novo_status != lead['status']:
                        conn.execute('UPDATE leads SET status = ? WHERE id = ?', (novo_status, lead['id']))
                        conn.commit()
                        st.rerun()
                with col_acao:
                    if lead['site_url']:
                        st.markdown(f"🌐 [Ver Site]({lead['site_url']})")
                    if st.button("Abrir no Studio IA", key=f"studio_{lead['id']}"):
                        st.session_state.lead_id_ativo = lead['id']
                        st.session_state.studio_step = 1
                        st.session_state.studio_data = {'nome': lead['nome'], 'nicho': lead['nicho'], 'cidade': lead['cidade'], 'endereco': lead['endereco'], 'telefone': lead['telefone']}
                        # Mudar para o menu Studio IA programaticamente
                        st.session_state.radio_menu = "Studio IA"
                        st.rerun()
    conn.close()

# --- STUDIO IA (O Diferencial) ---
elif menu == "Studio IA":
    st.title("Studio IA")
    st.write("Criar sites profissionais com direção de arte.")
    
    if st.session_state.lead_id_ativo is None:
        st.warning("Selecione um lead no CRM para começar a criar.")
    else:
        data = st.session_state.studio_data
        step = st.session_state.studio_step
        
        # Barra de Progresso
        st.progress(step / 7)
        st.markdown(f"**Etapa {step} de 7**")
        
        # --- ETAPA 1: ANALISAR SEGMENTO ---
        if step == 1:
            st.subheader("1. Análise de Segmento e Identidade")
            st.write(f"Analisando o negócio: **{data['nome']}** ({data['nicho']}).")
            if st.button("Analisar com IA"):
                with st.spinner("Analisando..."):
                    prompt = f"Analise a empresa '{data['nome']}' do ramo de '{data['nicho']}' na cidade de '{data['cidade']}'. Descreva em 2 frases a identidade, o público-alvo e o tom de voz ideal para o site."
                    analise = call_groq("Você é um estrategista de marketing.", prompt)
                    st.session_state.studio_data['analise'] = analise
                    st.session_state.studio_step = 2
                    st.rerun()
            if 'analise' in data: st.info(data['analise'])

        # --- ETAPA 2: DIREÇÃO DE ARTE ---
        elif step == 2:
            st.subheader("2. Direção de Arte")
            st.write("Definindo cores, fontes e estilo visual.")
            if st.button("Definir Direção de Arte"):
                with st.spinner("Criando paleta de cores..."):
                    prompt = f"Com base nesta análise: '{data['analise']}', defina uma direção de arte para o site. Escolha: 1) Uma paleta de cores (fundo, texto, destaque) em HEX. 2) Uma fonte principal do Google Fonts. 3) O estilo visual (ex: minimalista, rústico, moderno)."
                    direcao = call_groq("Você é um Diretor de Arte Sênior.", prompt)
                    st.session_state.studio_data['direcao'] = direcao
                    st.session_state.studio_step = 3
                    st.rerun()
            if 'direcao' in data: st.info(data['direcao'])

        # --- ETAPA 3: SELEÇÃO DE IMAGENS ---
        elif step == 3:
            st.subheader("3. Seleção de Imagens")
            st.write("Escolhendo imagens coerentes com o negócio.")
            url_img = IMAGENS_NICHO.get(data['nicho'], IMAGENS_NICHO["Outro"])
            st.image(url_img, caption="Imagem principal selecionada", width=400)
            
            st.write("As imagens do cardápio/serviços serão geradas automaticamente com base no nicho.")
            if st.button("Confirmar Imagens"):
                st.session_state.studio_data['img_hero'] = url_img
                st.session_state.studio_step = 4
                st.rerun()

        # --- ETAPA 4: DESENVOLVIMENTO ---
        elif step == 4:
            st.subheader("4. Desenvolvimento do Site")
            st.write("A IA está escrevendo o código HTML/CSS com base na direção de arte.")
            if st.button("Desenvolver Site"):
                with st.spinner("Codificando o site... (Pode levar 30 segundos)"):
                    endereco_encoded = urllib.parse.quote(data['endereco'])
                    prompt = f"""
                    Crie um site premium para {data['nome']} (Ramo: {data['nicho']}, Cidade: {data['cidade']}).
                    Use esta Direção de Arte: {data['direcao']}.
                    Use a imagem de fundo: {data['img_hero']}.
                    
                    REGRAS CRÍTICAS:
                    1. Use Tailwind CSS via CDN.
                    2. NÃO crie menu de navegação no topo. Hero section full-screen.
                    3. Cardápio/Serviços com fotos do Unsplash (ex: hambúrguer, pizza).
                    4. Mapa usando iframe público: <iframe src="https://maps.google.com/maps?q={endereco_encoded}&t=&z=15&ie=UTF8&iwloc=&output=embed" width="100%" height="300" style="border:0;" allowfullscreen="" loading="lazy"></iframe>
                    5. Retorne APENAS o código HTML.
                    """
                    codigo = call_groq("Você é um Desenvolvedor Front-end Sênior.", prompt)
                    codigo = re.sub(r"^```(?:html)?\s*|\s*```$", "", codigo.strip())
                    st.session_state.studio_data['html'] = codigo
                    st.session_state.studio_step = 5
                    st.rerun()

        # --- ETAPA 5: VERIFICAÇÃO ---
        elif step == 5:
            st.subheader("5. Verificação e Correção")
            st.write("Verificando erros no código gerado...")
            
            html = st.session_state.studio_data.get('html', '')
            if '<html' not in html.lower():
                st.error("Erro: A IA não retornou um HTML válido. Tentando corrigir...")
                if st.button("Tentar Novamente"):
                    st.session_state.studio_step = 4
                    st.rerun()
            else:
                st.success("✅ Código HTML válido!")
                if st.button("Aprovar e Avançar"):
                    st.session_state.studio_step = 6
                    st.rerun()

        # --- ETAPA 6: PRÉVIA ---
        elif step == 6:
            st.subheader("6. Prévia do Site")
            st.write("Hospedando para você revisar...")
            if st.button("Gerar Link de Prévia"):
                with st.spinner("Hospedando no BrewPage..."):
                    link = hospedar_brewpage(st.session_state.studio_data['html'])
                    if link:
                        st.session_state.studio_data['link'] = link
                        st.session_state.studio_step = 7
                        st.rerun()
                    else:
                        st.error("Erro ao hospedar.")

        # --- ETAPA 7: ABORDAGEM ---
        elif step == 7:
            st.subheader("7. Hospedagem e Abordagem")
            st.success(f"✅ Site Pronto! Link: {st.session_state.studio_data['link']}")
            
            # Atualiza o banco de dados
            conn = get_db_connection()
            conn.execute('UPDATE leads SET site_url = ?, status = ? WHERE id = ?', 
                         (st.session_state.studio_data['link'], "Demonstração Criada", st.session_state.lead_id_ativo))
            conn.commit()
            conn.close()
            
            msg = gerar_mensagem_abordagem(data['nome'], data['nicho'], data['cidade'], 5.0, link_site=st.session_state.studio_data['link'], nome_agencia=nome_agencia)
            st.text_area("Mensagem de Abordagem:", msg, height=150)
            
            num_limpo = re.sub(r'\D', '', data['telefone'])
            if len(num_limpo) == 11:
                zap_link = f"https://wa.me/55{num_limpo}?text={urllib.parse.quote(msg)}"
                st.markdown(f'<a href="{zap_link}" target="_blank" style="display: block; background-color: #25D366; color: white; padding: 15px; text-align: center; font-weight: bold; border-radius: 8px; text-decoration: none; margin-top: 10px;">📱 Enviar no WhatsApp</a>', unsafe_allow_html=True)
            
            if st.button("Finalizar e Limpar Studio"):
                st.session_state.lead_id_ativo = None
                st.session_state.studio_step = 1
                st.session_state.radio_menu = "CRM"
                st.rerun()

# --- PROJETOS ---
elif menu == "Projetos":
    st.title("Projetos")
    st.write("Gerenciar demonstrações criadas.")
    conn = get_db_connection()
    projetos = conn.execute('SELECT * FROM leads WHERE site_url IS NOT NULL').fetchall()
    conn.close()
    
    if not projetos:
        st.info("Nenhum projeto criado ainda.")
    else:
        for p in projetos:
            st.markdown(f"**{p['nome']}** - [Abrir Site]({p['site_url']})")

# --- RELATÓRIOS ---
elif menu == "Relatórios":
    st.title("Relatórios")
    st.write("Acompanhar resultados.")
    st.info("Em breve: Gráficos de conversão e taxa de resposta.")
