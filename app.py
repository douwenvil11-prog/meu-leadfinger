import streamlit as st
import requests
import re
import urllib.parse
from groq import Groq

st.set_page_config(page_title="LeadFinder PRO", layout="wide", page_icon="🚀")

# --- CSS PERSONALIZADO ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    .stButton>button { background-color: #00FF00; color: black; font-weight: bold; border-radius: 8px; border: none; padding: 10px 24px; }
    .stButton>button:hover { background-color: #00CC00; color: black; }
    .stTextInput>div>div>input, .stSelectbox>div>div>select { background-color: #1E232F; color: white; border-radius: 8px; }
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
if 'link_site_gerado' not in st.session_state: st.session_state.link_site_gerado = None

# --- LISTAS ---
NICHOS = ["Hamburgueria", "Pizzaria", "Barbearia", "Sorveteria/Açaí", "Mecânica", "Lava Jato", "Buffet", "Academia", "Outro"]
CIDADES_BR = {
    "Minas Gerais": ["Belo Horizonte", "Uberlândia", "Cataguases", "Juiz de Fora", "Contagem"],
    "São Paulo": ["São Paulo", "Campinas", "Santos", "Ribeirão Preto"],
    "Piauí": ["Teresina", "Parnaíba", "Picos", "Timon"],
    "Maranhão": ["São Luís", "Imperatriz", "Timon", "Caxias"],
    "Outro": ["Digitar manualmente"]
}
IMAGENS_NICHO = {
    "Hamburgueria": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?q=80&w=2000&auto=format&fit=crop",
    "Pizzaria": "https://images.unsplash.com/photo-1513104890138-7c749659a591?q=80&w=2000&auto=format&fit=crop",
    "Barbearia": "https://images.unsplash.com/photo-1585747860715-2ba37e788b70?q=80&w=2000&auto=format&fit=crop",
    "Sorveteria/Açaí": "https://images.unsplash.com/photo-1497034825429-c343d7c6a68f?q=80&w=2000&auto=format&fit=crop",
    "Mecânica": "https://images.unsplash.com/photo-1520340356584-f9917d1eea6f?q=80&w=2000&auto=format&fit=crop",
    "Lava Jato": "https://images.unsplash.com/photo-1601362840469-51e4d8d58785?q=80&w=2000&auto=format&fit=crop",
    "Buffet": "https://images.unsplash.com/photo-1555244162-803834f70033?q=80&w=2000&auto=format&fit=crop",
    "Academia": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?q=80&w=2000&auto=format&fit=crop",
    "Outro": "https://images.unsplash.com/photo-1497366216548-37526070297c?q=80&w=2000&auto=format&fit=crop"
}

# --- CHAVE DE API ---
if "GOOGLE_API_KEY" in st.secrets: api_key = st.secrets["GOOGLE_API_KEY"]
else: api_key = st.sidebar.text_input("Insira sua Google Maps API Key:", type="password")

# --- FUNÇÕES ---
def gerar_mensagem_abordagem(nome, nicho, cidade, nota, link_site=None, nome_agencia="Minha Agência"):
    # Ajusta a palavra do nicho para a frase ficar perfeita
    termo_site = nicho.lower()
    if nicho == "Hamburgueria": termo_site = "hamburgueria"
    elif nicho == "Pizzaria": termo_site = "pizzaria"
    elif nicho == "Mecânica": termo_site = "mecânica"
    elif nicho == "Lava Jato": termo_site = "lava jato"
    elif nicho == "Academia": termo_site = "academia"
    
    if link_site:
        # Mensagem com o link
        msg = f"Olá, tudo bem? Sou o consultor da {nome_agencia}. Estava procurando {nicho.lower()}s em {cidade} e vi que a de vocês tem nota {nota}, parabéns! Notei que vocês não têm um site. Como eu ajudo empresas locais, eu já montei uma prévia de como ficaria o site da sua {termo_site}. Dá uma olhada nesse link: {link_site}. Se gostar, eu te explico como colocar no ar. O que achou?"
    else:
        # Mensagem inicial sem link
        msg = f"Olá, tudo bem? Sou o consultor da {nome_agencia}. Estava procurando {nicho.lower()}s em {cidade} e vi que a de vocês tem nota {nota}, parabéns! Notei que vocês não têm um site. Posso te mandar uma prévia de como ele ficaria?"
    return msg

def gerar_e_hospedar_site(prompt_usuario, api_key_groq, url_imagem):
    try:
        client = Groq(api_key=api_key_groq)
        instrucao_sistema = f"""
        Você é um Web Designer Sênior. Retorne APENAS um documento HTML completo e auto-contido.
        Inline todo o CSS (use Tailwind via CDN).
        NÃO crie um menu de navegação (Navbar). A primeira seção (Hero) deve ocupar 100% da tela (h-screen).
        Use esta imagem de fundo: {url_imagem}. Aplique um overlay escuro.
        Coloque o Nome da Empresa, subtítulo e botão de WhatsApp no centro. Abaixo, crie Serviços, Sobre e Depoimentos.
        """
        chat_completion = client.chat.completions.create(
            messages=[{"role": "system", "content": instrucao_sistema}, {"role": "user", "content": prompt_usuario}],
            model="openai/gpt-oss-120b",
        )
        codigo_html = re.sub(r"^```(?:html)?\s*|\s*```$", "", chat_completion.choices[0].message.content.strip())
        
        url_brewpage = "https://brewpage.app/api/html"
        resposta = requests.post(url_brewpage, json={'content': codigo_html}, headers={'Content-Type': 'application/json'})
        
        if resposta.status_code in [200, 201]:
            return resposta.json().get('link'), "Sucesso"
        return None, f"Erro: {resposta.text}"
    except Exception as e:
        return None, f"Erro: {e}"

# ==========================================
# BARRA LATERAL
# ==========================================
st.sidebar.title("⚡ LeadFinder OS")
if st.sidebar.button("🏠 Dashboard", use_container_width=True): st.session_state.pagina = 'dashboard'
if st.sidebar.button("🔍 Prospecção", use_container_width=True): st.session_state.pagina = 'prospeccao'
if st.sidebar.button("💼 Meus Projetos", use_container_width=True): st.session_state.pagina = 'projetos'
st.sidebar.markdown("---")
nome_agencia = st.sidebar.text_input("Nome da sua agência:", "Minha Agência")

# ==========================================
# PÁGINAS
# ==========================================
if st.session_state.pagina == 'dashboard':
    st.title("🏠 Dashboard")
    st.write("Bem-vindo ao seu centro de comando.")

elif st.session_state.pagina == 'projetos':
    st.title("💼 Meus Projetos")
    if st.session_state.empresa_selecionada:
        st.success(f"Projeto em andamento: **{st.session_state.empresa_selecionada.get('displayName', {}).get('text')}**")
        if st.button("Retomar Projeto"):
            st.session_state.pagina = 'prospeccao'
            st.session_state.etapa = 2
            st.rerun()

elif st.session_state.pagina == 'prospeccao':
    
    if st.session_state.etapa == 1:
        st.title("Encontre seus clientes")
        
        col1, col2, col3 = st.columns(3)
        with col1: nicho = st.selectbox("Setor:", NICHOS)
        with col2: estado = st.selectbox("Estado:", list(CIDADES_BR.keys()))
        with col3: cidade = st.text_input("Cidade:", "Sua Cidade") if estado == "Outro" else st.selectbox("Cidade:", CIDADES_BR[estado])
        
        nota_minima = st.slider("Mostrar apenas empresas com nota acima de:", 0.0, 5.0, 4.0, 0.1)
        filtro_tamanho = st.checkbox("Filtrar empresas pequenas (< 300 avaliações)", value=True)

        if st.button("🔍 Buscar Empresas sem Site", use_container_width=True):
            if not api_key: st.error("Chave do Maps não encontrada.")
            else:
                with st.spinner('Buscando...'):
                    try:
                        url = "https://places.googleapis.com/v1/places:searchText"
                        headers = {'Content-Type': 'application/json', 'X-Goog-Api-Key': api_key, 'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri,places.userRatingCount,places.rating'}
                        payload = {"textQuery": f"{nicho} em {cidade}, {estado}", "maxResultCount": 20}
                        response = requests.post(url, json=payload, headers=headers)
                        places = response.json().get('places', [])
                        
                        results = [p for p in places if 'websiteUri' not in p and p.get('rating', 0) >= nota_minima and (not filtro_tamanho or p.get('userRatingCount', 0) <= 300)]
                        
                        st.session_state.leads = results
                        st.session_state.nicho = nicho
                        st.session_state.cidade = cidade
                        if results: st.success(f"{len(results)} leads de ouro encontrados!")
                        else: st.warning("Nenhum lead com esses filtros.")
                    except Exception as e: st.error(f"Erro: {e}")

        if st.session_state.leads:
            st.markdown("### Selecione um lead:")
            for i, lead in enumerate(st.session_state.leads):
                nome = lead.get('displayName', {}).get('text')
                end = lead.get('formattedAddress', '')
                nota = lead.get('rating', 'N/A')
                tel = lead.get('nationalPhoneNumber', '')
                maps_link = lead.get('googleMapsUri', '#')
                
                num_limpo = re.sub(r'\D', '', tel) if tel else ""
                is_valido = len(num_limpo) == 11 and num_limpo[2] == '9'
                
                # MENSAGEM INICIAL (SEM LINK, POIS O SITE AINDA NÃO FOI GERADO)
                msg_inicial = gerar_mensagem_abordagem(nome, st.session_state.nicho, st.session_state.cidade, nota, link_site=None, nome_agencia=nome_agencia)
                msg_encoded = urllib.parse.quote(msg_inicial)
                whatsapp_link = f"https://wa.me/55{num_limpo}?text={msg_encoded}" if is_valido else "#"
                
                insta_link = f"https://www.google.com/search?q=instagram+{nome.replace(' ', '+')}+{st.session_state.cidade.replace(' ', '+')}"
                
                with st.container(border=True):
                    col_info, col_links, col_btn = st.columns([3, 2, 1])
                    with col_info:
                        st.markdown(f"**{nome}** ⭐ {nota}")
                        st.write(f"📍 {end}")
                    with col_links:
                        if is_valido: st.markdown(f'<a href="{whatsapp_link}" target="_blank" class="action-link">📱 WhatsApp (Mensagem Inicial)</a>', unsafe_allow_html=True)
                        st.markdown(f'<a href="{maps_link}" target="_blank" class="action-link">📍 Maps</a>', unsafe_allow_html=True)
                        st.markdown(f'<a href="{insta_link}" target="_blank" class="action-link">📸 Instagram</a>', unsafe_allow_html=True)
                    with col_btn:
                        if st.button("Iniciar", key=f"btn_{i}", use_container_width=True):
                            st.session_state.empresa_selecionada = lead
                            st.session_state.etapa = 2
                            st.session_state.link_site_gerado = None # Reseta o link ao iniciar um novo
                            st.rerun()

    elif st.session_state.etapa == 2:
        lead = st.session_state.empresa_selecionada
        nome = lead.get('displayName', {}).get('text')
        endereco = lead.get('formattedAddress', '')
        telefone = lead.get('nationalPhoneNumber', '')
        
        st.title("Conte sobre o negócio")
        with st.container(border=True):
            nome_site = st.text_input("Nome do Site", value=nome)
        with st.container(border=True):
            st.subheader("Identidade Visual")
            col_c1, col_c2 = st.columns(2)
            with col_c1: cor_primaria = st.color_picker("Cor Principal", "#FF5722")
            with col_c2: cor_secundaria = st.color_picker("Cor Secundária", "#212121")
        with st.container(border=True):
            st.text_input("Endereço", value=endereco, disabled=True)
            tel_limpo = re.sub(r'\D', '', telefone)
            st.text_input("Telefone/WhatsApp", value=telefone, disabled=True)
            
        col_voltar, col_avancar = st.columns(2)
        with col_voltar:
            if st.button("⬅️ Voltar", use_container_width=True):
                st.session_state.etapa = 1; st.rerun()
        with col_avancar:
            if st.button("Gerar Prompt ➡️", use_container_width=True):
                st.session_state.nome_site = nome_site
                st.session_state.cor1 = cor_primaria
                st.session_state.cor2 = cor_secundaria
                st.session_state.tel_limpo = tel_limpo
                st.session_state.endereco = endereco
                st.session_state.etapa = 3; st.rerun()

    elif st.session_state.etapa == 3:
        nicho = st.session_state.nicho
        cidade = st.session_state.cidade
        nome = st.session_state.nome_site
        lead = st.session_state.empresa_selecionada
        nota = lead.get('rating', 'N/A')
        tel_limpo = st.session_state.tel_limpo
        
        st.title("Criação do Site e Abordagem Final")
        
        tab1, tab2 = st.tabs(["💻 Gerar Site", "🚀 Enviar Abordagem com Link"])
        
        with tab1:
            url_imagem_fundo = IMAGENS_NICHO.get(nicho, IMAGENS_NICHO["Outro"])
            prompt = f"""Crie um site one-page premium para {nome} (Ramo: {nicho}, Cidade: {cidade}).
Cores: Fundo {st.session_state.cor1}, Texto {st.session_state.cor2}. Use Tailwind CSS."""
            st.code(prompt, language="markdown")

            if st.button("🚀 Gerar e Hospedar Site", use_container_width=True):
                if "GROQ_API_KEY" in st.secrets:
                    with st.spinner("Gerando site..."):
                        link, resultado = gerar_e_hospedar_site(prompt, st.secrets["GROQ_API_KEY"], url_imagem_fundo)
                        if link:
                            st.session_state.link_site_gerado = link
                            st.success("Site gerado com sucesso! Vá para a aba 'Enviar Abordagem'.")
                        else: st.error(resultado)
                else: st.warning("Configure GROQ_API_KEY.")

        with tab2:
            if st.session_state.link_site_gerado:
                st.success("✅ Site pronto! Envie a mensagem abaixo para o cliente.")
                # GERA A MENSAGEM FINAL COM O LINK
                msg_final = gerar_mensagem_abordagem(nome, nicho, cidade, nota, link_site=st.session_state.link_site_gerado, nome_agencia=nome_agencia)
                st.text_area("Mensagem pronta (copie se precisar):", msg_final, height=150)
                
                # BOTÃO DE WHATSAPP COM O LINK
                msg_encoded = urllib.parse.quote(msg_final)
                zap_final = f"https://wa.me/55{tel_limpo}?text={msg_encoded}"
                
                st.markdown(f"""
                <a href="{zap_final}" target="_blank" style="display: inline-block; background-color: #25D366; color: white; padding: 15px 30px; text-align: center; text-decoration: none; font-size: 18px; font-weight: bold; border-radius: 8px; width: 100%;">
                    📱 Enviar no WhatsApp agora
                </a>
                """, unsafe_allow_html=True)
                
            else:
                st.warning("⚠️ Gere o site primeiro na aba ao lado para liberar o link da abordagem.")

        if st.button("⬅️ Voltar", use_container_width=True):
            st.session_state.etapa = 2; st.rerun()
