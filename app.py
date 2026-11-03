import streamlit as st
import requests
import re
import time

st.set_page_config(page_title="LeadFinder PRO", layout="wide", page_icon="🚀")

# --- CSS PERSONALIZADO (Para ficar com cara de Valy OS) ---
st.markdown("""
    <style>
    /* Fundo escuro */
    .stApp { background-color: #0E1117; }
    /* Botões verdes */
    .stButton>button {
        background-color: #00FF00;
        color: black;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
    }
    .stButton>button:hover { background-color: #00CC00; color: black; }
    /* Inputs escuros */
    .stTextInput>div>div>input, .stSelectbox>div>div>select {
        background-color: #1E232F;
        color: white;
        border-radius: 8px;
    }
    /* Caixas de conteúdo */
    div[data-testid="stExpander"] { background-color: #1E232F; border-radius: 10px; border: 1px solid #333; }
    </style>
""", unsafe_allow_html=True)

# --- CONTROLE DE ESTADO DO APP ---
if 'etapa' not in st.session_state: st.session_state.etapa = 1
if 'leads' not in st.session_state: st.session_state.leads = []
if 'empresa_selecionada' not in st.session_state: st.session_state.empresa_selecionada = None

# --- LISTAS ---
NICHOS = ["Hamburgueria", "Pizzaria", "Barbearia", "Sorveteria/Açaí", "Mecânica", "Lava Jato", "Buffet", "Outro"]
CIDADES_BR = {
    "Minas Gerais": ["Belo Horizonte", "Uberlândia", "Cataguases"],
    "São Paulo": ["São Paulo", "Campinas"],
    "Piauí": ["Teresina", "Parnaíba", "Timon"],
    "Outro": ["Digitar manualmente"]
}

# --- CHAVE DE API ---
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = st.sidebar.text_input("Insira sua Google Maps API Key:", type="password")

st.sidebar.title("⚡ LeadFinder OS")
st.sidebar.markdown("---")
st.sidebar.button("🏠 Dashboard (Visual)", disabled=True)
st.sidebar.button("🔍 Prospecção", disabled=True, help="Você está aqui")
st.sidebar.button("💼 Projetos", disabled=True)
st.sidebar.markdown("---")
nome_agencia = st.sidebar.text_input("Nome da sua agência:", "Minha Agência")

# ==========================================
# ETAPA 1: BUSCAR OS LEADS
# ==========================================
if st.session_state.etapa == 1:
    st.title("Novo Projeto: Encontre seus clientes")
    st.write("Selecione o nicho e a região para encontrar empresas sem site.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        nicho = st.selectbox("Qual o setor do negócio?", NICHOS)
    with col2:
        estado = st.selectbox("Estado:", list(CIDADES_BR.keys()))
    with col3:
        if estado == "Outro":
            cidade = st.text_input("Cidade:", "Sua Cidade")
        else:
            cidade = st.selectbox("Cidade:", CIDADES_BR[estado])
            
    filtro = st.checkbox("Filtrar empresas médias/pequenas (< 300 avaliações)", value=True)

    if st.button("🔍 Buscar Empresas sem Site", use_container_width=True):
        if not api_key:
            st.error("Chave de API não encontrada. Configure nos Secrets.")
        else:
            with st.spinner('Buscando no Google Maps...'):
                try:
                    url = "https://places.googleapis.com/v1/places:searchText"
                    headers = {
                        'Content-Type': 'application/json',
                        'X-Goog-Api-Key': api_key,
                        'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri,places.userRatingCount,places.rating'
                    }
                    payload = {"textQuery": f"{nicho} em {cidade}, {estado}", "maxResultCount": 20}
                    response = requests.post(url, json=payload, headers=headers)
                    places = response.json().get('places', [])
                    
                    results = [p for p in places if 'websiteUri' not in p and (not filtro or p.get('userRatingCount', 0) <= 300)]
                    
                    st.session_state.leads = results
                    st.session_state.nicho = nicho
                    st.session_state.cidade = cidade
                    if results:
                        st.success(f"{len(results)} leads encontrados!")
                    else:
                        st.warning("Nenhum lead encontrado com esses filtros.")
                except Exception as e:
                    st.error(f"Erro: {e}")

    # Mostrar os leads encontrados
    if st.session_state.leads:
        st.markdown("### Selecione um lead para iniciar o projeto:")
        for i, lead in enumerate(st.session_state.leads):
            nome = lead.get('displayName', {}).get('text')
            end = lead.get('formattedAddress')
            nota = lead.get('rating', 'N/A')
            
            with st.container(border=True):
                col_info, col_btn = st.columns([4, 1])
                with col_info:
                    st.markdown(f"**{nome}** ⭐ {nota}")
                    st.write(f"📍 {end}")
                with col_btn:
                    if st.button("Iniciar Projeto", key=f"btn_{i}"):
                        st.session_state.empresa_selecionada = lead
                        st.session_state.etapa = 2
                        st.rerun()

# ==========================================
# ETAPA 2: CONFIGURAR O DESIGN E INFORMAÇÕES
# ==========================================
elif st.session_state.etapa == 2:
    lead = st.session_state.empresa_selecionada
    nome = lead.get('displayName', {}).get('text')
    endereco = lead.get('formattedAddress', '')
    telefone = lead.get('nationalPhoneNumber', '')
    
    st.title("Conte sobre o negócio")
    st.write("Ajuste as informações que aparecerão no site demonstrativo.")
    
    with st.container(border=True):
        st.subheader("Identidade")
        nome_site = st.text_input("Nome do Site", value=nome)
        
    with st.container(border=True):
        st.subheader("Identidade Visual")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            cor_primaria = st.color_picker("Cor Principal", "#FF5722")
        with col_c2:
            cor_secundaria = st.color_picker("Cor Secundária", "#212121")
            
    with st.container(border=True):
        st.subheader("Contato e Localização")
        st.text_input("Endereço", value=endereco, disabled=True)
        tel_limpo = re.sub(r'\D', '', telefone)
        st.text_input("Telefone/WhatsApp", value=telefone, disabled=True)
        
    col_voltar, col_avancar = st.columns(2)
    with col_voltar:
        if st.button("⬅️ Voltar para Leads", use_container_width=True):
            st.session_state.etapa = 1
            st.rerun()
    with col_avancar:
        if st.button("Gerar Abordagem e Prompt ➡️", use_container_width=True):
            st.session_state.nome_site = nome_site
            st.session_state.cor1 = cor_primaria
            st.session_state.cor2 = cor_secundaria
            st.session_state.tel_limpo = tel_limpo
            st.session_state.endereco = endereco
            st.session_state.etapa = 3
            st.rerun()

# ==========================================
# ETAPA 3: ABORDAGEM E PROMPT DO SITE
# ==========================================
elif st.session_state.etapa == 3:
    st.title("Abordagem e Criação do Site")
    
    nicho = st.session_state.nicho
    cidade = st.session_state.cidade
    nome = st.session_state.nome_site
    agencia = nome_agencia
    
    # Abas separando Abordagem e Prompt
    tab1, tab2 = st.tabs(["💬 Abordagem de Vendas", "💻 Criar Site com IA"])
    
    with tab1:
        st.subheader("Sua abordagem profissional")
        st.write("Script de pré-venda em blocos.")
        
        # Bloco 1
        with st.container(border=True):
            st.markdown("🟢 **1. Abertura**")
            st.caption("Curta. Só confirme que está falando com quem decide.")
            texto1 = f"Olá! Tudo bem? Falo com o responsável pela {nome}?"
            st.code(texto1, language="text")
            
        # Bloco 2
        with st.container(border=True):
            st.markdown("🟣 **2. Apresentação**")
            st.caption("Quem você é, em uma frase.")
            texto2 = f"Meu nome é [Seu Nome]. Sou da {agencia} e crio sites para {nicho}s aqui em {cidade} — páginas feitas para o cliente achar e entrar em contato, não só um cartão de visitas online."
            st.code(texto2, language="text")
            
        # Bloco 3
        with st.container(border=True):
            st.markdown("🔴 **3. Diagnóstico**")
            st.caption("Mostre que você olhou o negócio deles.")
            texto3 = f"Procurei pela {nome} no Google e não achei um site — só o cadastro no Maps. Quem procura por {nicho} em {cidade} e não encontra uma página com serviços e contato acaba clicando em quem tem."
            st.code(texto3, language="text")
            
        # Bloco 4
        with st.container(border=True):
            st.markdown("🟡 **4. Solução**")
            st.caption("O que você pode fazer por eles.")
            texto4 = f"Eu montei uma prévia de como ficaria a {nome}: uma página com botão de WhatsApp em todos os pontos, fotos do local e depoimentos. O link é esse aqui: [LINK DO SITE]. Posso te mostrar em 5 minutos?"
            st.code(texto4, language="text")

    with tab2:
        st.subheader("Prompt para gerar o site")
        st.write("Copie o texto abaixo e cole no Lovable ou v0.dev.")
        
        if nicho in ["Hamburgueria", "Pizzaria", "Buffet", "Restaurante", "Sorveteria/Açaí"]:
            menu = '"Início", "Cardápio", "Eventos", "Sobre", "Contato"'
        else:
            menu = '"Início", "Serviços", "Sobre", "Contato"'
            
        prompt = f"""Crie um site one-page premium para a empresa {nome} (Ramo: {nicho}, Cidade: {cidade}).
Cores: Fundo {st.session_state.cor1}, Texto {st.session_state.cor2}.
Layout: Texto grande à esquerda, imagem do produto à direita (estilo recortado).
Menu: {menu}.
Botões: "Solicitar Orçamento" e "Chamar no WhatsApp" (link: https://wa.me/55{st.session_state.tel_limpo}).
Inclua seção de serviços, sobre nós, endereço ({st.session_state.endereco}) e depoimentos.
Use React e Tailwind CSS."""
        
        st.code(prompt, language="markdown")
        
    if st.button("⬅️ Voltar para Configurações", use_container_width=True):
        st.session_state.etapa = 2
        st.rerun()
