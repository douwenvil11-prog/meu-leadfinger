import streamlit as st
import requests
import re
import time
from groq import Groq

st.set_page_config(page_title="LeadFinder PRO", layout="wide", page_icon="🚀")

# --- CSS PERSONALIZADO ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    .stButton>button {
        background-color: #00FF00; color: black; font-weight: bold;
        border-radius: 8px; border: none; padding: 10px 24px;
    }
    .stButton>button:hover { background-color: #00CC00; color: black; }
    .stTextInput>div>div>input, .stSelectbox>div>div>select {
        background-color: #1E232F; color: white; border-radius: 8px;
    }
    div[data-testid="stExpander"] { background-color: #1E232F; border-radius: 10px; border: 1px solid #333; }
    .action-link { text-decoration: none; color: #00FF00; margin-right: 15px; font-weight: bold; }
    .action-link:hover { color: #FFFFFF; }
    </style>
""", unsafe_allow_html=True)

# --- CONTROLE DE ESTADO DO APP ---
if 'pagina' not in st.session_state: st.session_state.pagina = 'prospeccao'
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

# --- CHAVE DE API DO MAPS ---
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = st.sidebar.text_input("Insira sua Google Maps API Key:", type="password")

# ==========================================
# BARRA LATERAL (NAVEGAÇÃO)
# ==========================================
st.sidebar.title("⚡ LeadFinder OS")
st.sidebar.markdown("---")

if st.sidebar.button("🏠 Dashboard", use_container_width=True):
    st.session_state.pagina = 'dashboard'
if st.sidebar.button("🔍 Prospecção", use_container_width=True):
    st.session_state.pagina = 'prospeccao'
if st.sidebar.button("💼 Meus Projetos", use_container_width=True):
    st.session_state.pagina = 'projetos'

st.sidebar.markdown("---")
nome_agencia = st.sidebar.text_input("Nome da sua agência:", "Minha Agência")

# ==========================================
# FUNÇÃO DE GERAR E HOSPEDAR O SITE
# ==========================================
def gerar_e_hospedar_site(prompt_usuario, api_key_groq):
    try:
        # 1. Configura o cliente do Groq
        client = Groq(api_key=api_key_groq)
        
        # 2. Faz a chamada para gerar o código HTML
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Você é um Web Designer Sênior. Retorne APENAS um documento HTML completo e auto-contido. Inline todo o CSS (Tailwind via CDN é permitido). Não use markdown, não adicione explicações, não coloque ```html no início."
                },
                {
                    "role": "user",
                    "content": prompt_usuario
                }
            ],
            model="llama-3.3-70b-versatile", # Modelo gratuito e potente
        )
        
        codigo_html = chat_completion.choices[0].message.content
        
        # Limpa o código para garantir que é apenas HTML
        codigo_html = re.sub(r"^```(?:html)?\s*|\s*```$", "", codigo_html.strip())
        if "<html" not in codigo_html.lower():
            return None, "A IA não retornou um código HTML válido."

        # 3. Hospeda no PageDrop
        # O PageDrop usa um formato multipart/form-data para upload
        url_api_pagedrop = "https://pagedrop.dev/api/upload"
        
        # Cria o arquivo em memória para enviar
        files = {'file': ('index.html', codigo_html, 'text/html')}
        
        # Faz o POST para o PageDrop
        resposta = requests.post(url_api_pagedrop, files=files)
        
        # Verifica se deu certo e pega o link
        if resposta.status_code == 200:
            dados = resposta.json()
            link_publico = dados.get('url')
            return link_publico, "Site gerado com sucesso!"
        else:
            return None, f"Erro no PageDrop (Status {resposta.status_code}): {resposta.text}"
            
    except Exception as e:
        return None, f"Erro ao gerar com Groq: {e}"

# ==========================================
# PÁGINAS
# ==========================================
if st.session_state.pagina == 'dashboard':
    st.title("🏠 Dashboard")
    st.write("Bem-vindo ao seu centro de comando.")
    col1, col2, col3 = st.columns(3)
    col1.metric("Leads na Memória", len(st.session_state.leads))
    col2.metric("Projetos Iniciados", "1" if st.session_state.empresa_selecionada else "0")
    col3.metric("Créditos de IA", "∞")

elif st.session_state.pagina == 'projetos':
    st.title("💼 Meus Projetos")
    if st.session_state.empresa_selecionada:
        lead = st.session_state.empresa_selecionada
        nome = lead.get('displayName', {}).get('text')
        st.success(f"Projeto em andamento: **{nome}**")
        if st.button("Retomar Projeto"):
            st.session_state.pagina = 'prospeccao'
            st.session_state.etapa = 2
            st.rerun()
    else:
        st.write("Você ainda não iniciou nenhum projeto. Vá para a aba de Prospecção para começar.")

elif st.session_state.pagina == 'prospeccao':
    
    # --- ETAPA 1: BUSCAR OS LEADS ---
    if st.session_state.etapa == 1:
        st.title("Novo Projeto: Encontre seus clientes")
        col1, col2, col3 = st.columns(3)
        with col1:
            nicho = st.selectbox("Qual o setor do negócio?", NICHOS)
        with col2:
            estado = st.selectbox("Estado:", list(CIDADES_BR.keys()))
        with col3:
            cidade = st.text_input("Cidade:", "Sua Cidade") if estado == "Outro" else st.selectbox("Cidade:", CIDADES_BR[estado])
                
        filtro = st.checkbox("Filtrar empresas médias/pequenas (< 300 avaliações)", value=True)

        if st.button("🔍 Buscar Empresas sem Site", use_container_width=True):
            if not api_key:
                st.error("Chave do Google Maps não encontrada.")
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
                            st.warning("Nenhum lead encontrado.")
                    except Exception as e:
                        st.error(f"Erro: {e}")

        if st.session_state.leads:
            st.markdown("### Selecione um lead para iniciar o projeto:")
            for i, lead in enumerate(st.session_state.leads):
                nome = lead.get('displayName', {}).get('text')
                end = lead.get('formattedAddress', '')
                nota = lead.get('rating', 'N/A')
                tel = lead.get('nationalPhoneNumber', '')
                maps_link = lead.get('googleMapsUri', '#')
                
                num_limpo = re.sub(r'\D', '', tel) if tel else ""
                is_valido = len(num_limpo) == 11 and num_limpo[2] == '9'
                whatsapp_link = f"https://wa.me/55{num_limpo}" if is_valido else "#"
                insta_link = f"https://www.google.com/search?q=instagram+{nome.replace(' ', '+')}+{st.session_state.cidade.replace(' ', '+')}"
                
                with st.container(border=True):
                    col_info, col_links, col_btn = st.columns([3, 2, 1])
                    with col_info:
                        st.markdown(f"**{nome}** ⭐ {nota}")
                        st.write(f"📍 {end}")
                    with col_links:
                        st.markdown("**Ações Rápidas:**")
                        if is_valido:
                            st.markdown(f'<a href="{whatsapp_link}" target="_blank" class="action-link">📱 WhatsApp</a>', unsafe_allow_html=True)
                        st.markdown(f'<a href="{maps_link}" target="_blank" class="action-link">📍 Maps</a>', unsafe_allow_html=True)
                        st.markdown(f'<a href="{insta_link}" target="_blank" class="action-link">📸 Instagram</a>', unsafe_allow_html=True)
                    with col_btn:
                        if st.button("Iniciar", key=f"btn_{i}", use_container_width=True):
                            st.session_state.empresa_selecionada = lead
                            st.session_state.etapa = 2
                            st.rerun()

    # --- ETAPA 2: CONFIGURAR O DESIGN E INFORMAÇÕES ---
    elif st.session_state.etapa == 2:
        lead = st.session_state.empresa_selecionada
        nome = lead.get('displayName', {}).get('text')
        endereco = lead.get('formattedAddress', '')
        telefone = lead.get('nationalPhoneNumber', '')
        
        st.title("Conte sobre o negócio")
        
        # Galeria de Modelos
        st.subheader("Escolha um modelo de referência")
        modelos = {
            "Brasa Burger": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400",
            "Chapa Burger": "https://images.unsplash.com/photo-1550547660-d9450f859349?w=400",
            "Smash House": "https://images.unsplash.com/photo-1594212699903-ec8a3eca50f5?w=400",
        }
        cols = st.columns(3)
        for i, (nome_modelo, url_img) in enumerate(modelos.items()):
            with cols[i]:
                st.image(url_img, use_column_width=True)
                if st.button(f"Selecionar {nome_modelo}", key=f"mod_{i}"):
                    st.session_state.modelo_escolhido = nome_modelo
                    st.success(f"Modelo '{nome_modelo}' selecionado!")

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
            if st.button("⬅️ Voltar", use_container_width=True):
                st.session_state.etapa = 1
                st.rerun()
        with col_avancar:
            if st.button("Gerar Prompt ➡️", use_container_width=True):
                st.session_state.nome_site = nome_site
                st.session_state.cor1 = cor_primaria
                st.session_state.cor2 = cor_secundaria
                st.session_state.tel_limpo = tel_limpo
                st.session_state.endereco = endereco
                st.session_state.etapa = 3
                st.rerun()

    # --- ETAPA 3: ABORDAGEM E PROMPT DO SITE ---
    elif st.session_state.etapa == 3:
        st.title("Abordagem e Criação do Site")
        
        nicho = st.session_state.nicho
        cidade = st.session_state.cidade
        nome = st.session_state.nome_site
        agencia = nome_agencia
        
        tab1, tab2 = st.tabs(["💬 Abordagem de Vendas", "💻 Criar Site com IA"])
        
        with tab1:
            st.subheader("Sua abordagem profissional")
            with st.container(border=True):
                st.markdown("🟢 **1. Abertura**")
                st.code(f"Olá! Tudo bem? Falo com o responsável pela {nome}?", language="text")
            with st.container(border=True):
                st.markdown("🟣 **2. Apresentação**")
                st.code(f"Meu nome é [Seu Nome]. Sou da {agencia} e crio sites para {nicho}s aqui em {cidade}.", language="text")
            with st.container(border=True):
                st.markdown("🔴 **3. Diagnóstico**")
                st.code(f"Procurei pela {nome} no Google e não achei um site. Quem procura por {nicho} em {cidade} acaba clicando em quem tem.", language="text")
            with st.container(border=True):
                st.markdown("🟡 **4. Solução**")
                st.code(f"Montei uma prévia de como ficaria a {nome}. Posso te mostrar em 5 minutos?", language="text")

        with tab2:
            st.subheader("Prompt para gerar o site")
            
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
Use React e Tailwind CSS (via CDN). Retorne o HTML completo."""
            
            st.code(prompt, language="markdown")

            # --- BOTÃO MÁGICO: GERAR E HOSPEDAR ---
            st.markdown("---")
            st.subheader("🚀 Gerar Site Automaticamente")
            
            if st.button("Gerar e Hospedar Site Agora", use_container_width=True):
                if "GROQ_API_KEY" in st.secrets:
                    with st.spinner("A IA está desenhando o site e o PageDrop está hospedando... (Pode levar 30 segundos)"):
                        link, resultado = gerar_e_hospedar_site(prompt, st.secrets["GROQ_API_KEY"])
                        
                        if link:
                            st.success("Site gerado e hospedado com sucesso!")
                            st.markdown(f"[**Clique aqui para ver o site do cliente**]({link})")
                            st.info("Lembre-se: O PageDrop gratuito cria links temporários. Para o cliente ver depois, baixe o HTML ou use um domínio próprio.")
                        else:
                            st.error(resultado)
                else:
                    st.warning("⚠️ Configure a chave 'GROQ_API_KEY' nos Secrets do Streamlit para usar esta função.")
            
        if st.button("⬅️ Voltar para Configurações", use_container_width=True):
            st.session_state.etapa = 2
            st.rerun()
