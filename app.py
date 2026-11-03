import streamlit as st
import requests
import re
import json
import urllib.parse
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

# --- CONTROLE DE ESTADO ---
if 'pagina' not in st.session_state: st.session_state.pagina = 'prospeccao'
if 'etapa' not in st.session_state: st.session_state.etapa = 1
if 'leads' not in st.session_state: st.session_state.leads = []
if 'empresa_selecionada' not in st.session_state: st.session_state.empresa_selecionada = None

# --- LISTAS ---
NICHOS = ["Hamburgueria", "Pizzaria", "Barbearia", "Sorveteria/Açaí", "Mecânica", "Lava Jato", "Buffet", "Outro"]

# --- CARREGAR ESTADOS DO IBGE (com cache) ---
@st.cache_data(ttl=86400) # Cache de 24 horas
def carregar_estados():
    try:
        url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        estados = response.json()
        # Ordena alfabeticamente pelo nome
        estados_ordenados = sorted([e['nome'] for e in estados])
        return estados_ordenados
    except Exception as e:
        st.error(f"Erro ao carregar estados do IBGE: {e}")
        # Fallback com os principais estados caso a API falhe
        return ["Minas Gerais", "São Paulo", "Rio de Janeiro", "Piauí", "Maranhão", "Bahia", "Paraná", "Ceará", "Goiás"]

# --- CARREGAR CIDADES DO IBGE (sob demanda, com cache) ---
@st.cache_data(ttl=86400)
def carregar_cidades(estado_nome):
    try:
        # Primeiro, precisamos da sigla (UF) do estado para a URL do IBGE
        url_estados = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
        response_estados = requests.get(url_estados, timeout=10)
        response_estados.raise_for_status()
        estados_data = response_estados.json()
        
        uf = None
        for e in estados_data:
            if e['nome'] == estado_nome:
                uf = e['sigla']
                break
        
        if not uf:
            return ["Erro: Estado não encontrado"]

        # Agora busca as cidades daquele estado
        url_cidades = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
        response_cidades = requests.get(url_cidades, timeout=10)
        response_cidades.raise_for_status()
        cidades = response_cidades.json()
        
        return sorted([c['nome'] for c in cidades])
    except Exception as e:
        st.error(f"Erro ao carregar cidades: {e}")
        return ["Digite a cidade manualmente"]

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
# FUNÇÕES DE IA E HOSPEDAGEM
# ==========================================
def gerar_imagem_pollinations(prompt):
    prompt_encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=1024&height=1024&nologo=true&model=flux"
    return url

def gerar_e_hospedar_site(prompt_usuario, api_key_groq):
    try:
        client = Groq(api_key=api_key_groq)
        
        instrucao_sistema = """
        Você é um Web Designer Sênior. Retorne APENAS um documento HTML completo e auto-contido.
        Inline todo o CSS (pode usar Tailwind via CDN). Não use markdown, não adicione explicações.
        O site deve ter um design premium e responsivo.
        """
        
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": instrucao_sistema},
                {"role": "user", "content": prompt_usuario}
            ],
            model="openai/gpt-oss-120b",
        )
        codigo_html = chat_completion.choices[0].message.content
        codigo_html = re.sub(r"^```(?:html)?\s*|\s*```$", "", codigo_html.strip())
        
        if "<html" not in codigo_html.lower():
            return None, "A IA não retornou um código HTML válido."

        # Hospedagem no BrewPage
        url_brewpage = "https://brewpage.app/api/html"
        headers = {'Content-Type': 'application/json'}
        payload = {'content': codigo_html}
        
        resposta = requests.post(url_brewpage, json=payload, headers=headers)
        
        if resposta.status_code == 200:
            dados = resposta.json()
            link_publico = dados.get('link') or dados.get('url')
            if link_publico:
                return link_publico, "Site gerado com sucesso!"
            else:
                return None, f"Resposta do BrewPage sem link: {dados}"
        else:
            return None, f"Erro no BrewPage (Status {resposta.status_code}): {resposta.text}"
            
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
        
        # Carrega a lista de estados uma vez
        estados_disponiveis = carregar_estados()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            nicho = st.selectbox("Qual o setor do negócio?", NICHOS)
        with col2:
            estado = st.selectbox("Estado:", estados_disponiveis)
        with col3:
            # Carrega as cidades apenas quando o estado é selecionado
            cidades_disponiveis = carregar_cidades(estado)
            cidade = st.selectbox("Cidade:", cidades_disponiveis)
                
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

            st.markdown("---")
            st.subheader("🚀 Gerar Site Automaticamente")
            
            prompt_imagem = st.text_input(
                "Descreva a imagem de fundo ideal para este site:", 
                value=f"Imagem realista e profissional de {nicho.lower()} de alta qualidade, estilo comercial, iluminação cinematográfica, fundo limpo"
            )
            
            if st.button("Gerar e Hospedar Site Agora", use_container_width=True):
                if "GROQ_API_KEY" in st.secrets:
                    with st.spinner("Gerando imagem, criando o código e hospedando o site..."):
                        url_imagem = gerar_imagem_pollinations(prompt_imagem)
                        prompt_final = prompt + f"\n\nUse esta imagem como plano de fundo da seção hero: {url_imagem}"
                        
                        link, resultado = gerar_e_hospedar_site(prompt_final, st.secrets["GROQ_API_KEY"])
                        
                        if link:
                            st.success("Site gerado e hospedado com sucesso!")
                            st.markdown(f"[**Clique aqui para ver o site do cliente**]({link})")
                            st.info("O link do BrewPage é válido por 15 dias. Se precisar de um link permanente, você pode baixar o HTML ou usar um domínio próprio.")
                        else:
                            st.error(resultado)
                else:
                    st.warning("⚠️ Configure a chave 'GROQ_API_KEY' nos Secrets do Streamlit para usar esta função.")
            
        if st.button("⬅️ Voltar para Configurações", use_container_width=True):
            st.session_state.etapa = 2
            st.rerun()
