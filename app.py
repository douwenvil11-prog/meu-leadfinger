import streamlit as st
import requests
import re
import urllib.parse
import time
from groq import Groq

st.set_page_config(page_title="LeadFinder PRO - SaaS", layout="wide", page_icon="🚀")

# --- CSS PERSONALIZADO (Visual SaaS Premium) ---
st.markdown("""
    <style>
    .stApp { background-color: #0A0A0A; color: #FFFFFF; }
    .stButton>button {
        background-color: #00FF00; color: black; font-weight: bold;
        border-radius: 8px; border: none; padding: 10px 24px;
    }
    .stButton>button:hover { background-color: #00CC00; color: black; }
    .stTextInput>div>div>input, .stSelectbox>div>div>select {
        background-color: #1A1A1A; color: white; border-radius: 8px; border: 1px solid #333;
    }
    div[data-testid="stExpander"] { background-color: #1A1A1A; border-radius: 10px; border: 1px solid #333; }
    .action-link { text-decoration: none; color: #00FF00; margin-right: 15px; font-weight: bold; }
    .action-link:hover { color: #FFFFFF; }
    h1, h2, h3 { color: #FFFFFF !important; }
    </style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS SIMULADO (SESSION STATE) ---
if 'crm_db' not in st.session_state: st.session_state.crm_db = []
if 'pagina' not in st.session_state: st.session_state.pagina = 'dashboard'
if 'empresa_selecionada' not in st.session_state: st.session_state.empresa_selecionada = None
if 'link_site_gerado' not in st.session_state: st.session_state.link_site_gerado = None

# --- LISTAS ---
NICHOS = ["Hamburgueria", "Pizzaria", "Barbearia", "Sorveteria/Açaí", "Mecânica", "Lava Jato", "Buffet", "Academia", "Outro"]
CIDADES_BR = {
    "Minas Gerais": ["Belo Horizonte", "Uberlândia", "Cataguases", "Juiz de Fora"],
    "São Paulo": ["São Paulo", "Campinas", "Santos"],
    "Piauí": ["Teresina", "Parnaíba", "Picos", "Timon"],
    "Maranhão": ["São Luís", "Imperatriz", "Timon"],
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

# --- CHAVE DE API ---
if "GOOGLE_API_KEY" in st.secrets: api_key = st.secrets["GOOGLE_API_KEY"]
else: api_key = st.sidebar.text_input("Google Maps API Key:", type="password")

# --- FUNÇÕES ---
def gerar_mensagem_abordagem(nome, nicho, cidade, nota, link_site=None, nome_agencia="Minha Agência"):
    termo_site = nicho.lower()
    if nicho == "Hamburgueria": termo_site = "hamburgueria"
    elif nicho == "Pizzaria": termo_site = "pizzaria"
    
    if link_site:
        msg = f"Olá, tudo bem? Sou o consultor da {nome_agencia}. Estava procurando {nicho.lower()}s em {cidade} e vi que a de vocês tem nota {nota}, parabéns! Notei que vocês não têm um site. Como eu ajudo empresas locais, eu já montei uma prévia de como ficaria o site da sua {termo_site}. Dá uma olhada nesse link: {link_site}. Se gostar, eu te explico como colocar no ar. O que achou?"
    else:
        msg = f"Olá, tudo bem? Sou o consultor da {nome_agencia}. Estava procurando {nicho.lower()}s em {cidade} e vi que a de vocês tem nota {nota}, parabéns! Notei que vocês não têm um site. Posso te mandar uma prévia?"
    return msg

def gerar_e_hospedar_site(prompt_usuario, api_key_groq, url_imagem, endereco):
    try:
        client = Groq(api_key=api_key_groq)
        
        # Formatando o endereço para o link do mapa
        endereco_encoded = urllib.parse.quote(endereco)
        
        diretriz_master = f"""
        DIRETRIZ MASTER — DESENVOLVIMENTO DE SITES PROFISSIONAIS
        Atue como uma agência profissional premium. Crie sites com design moderno, identidade visual marcante, tipografia forte e imagens de alta qualidade.

        1. HERO SECTION: Imagem principal grande (Use esta: {url_imagem}), título impactante, dois botões de ação.
        2. IDENTIDADE: Cores e fontes escolhidas de acordo com o nicho.
        3. PROIBIDO: Layouts genéricos, emojis substituindo ícones, textos desalinhados.
        4. CONVERSÃO: Botão "Chamar no WhatsApp" em destaque.

        REGRAS CRÍTICAS PARA CORRIGIR ERROS ANTERIORES:
        
        A) CARDÁPIO / SERVIÇOS COM FOTOS OBRIGATÓRIAS:
        Na seção de cardápio/serviços, NÃO DEIXE NENHUM CARD SEM IMAGEM. Use imagens reais do Unsplash.
        Exemplos de URLs de imagens de comida que você DEVE usar nos cards:
        - Hambúrguer: https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&h=400&fit=crop
        - Pizza: https://images.unsplash.com/photo-1513104890138-7c749659a591?w=600&h=400&fit=crop
        - Batata Frita: https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=600&h=400&fit=crop
        - Bebida/Refri: https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=600&h=400&fit=crop
        (Se for outro nicho, use imagens do Unsplash relacionadas).

        B) MAPA DO GOOGLE (SEM ERRO DE API KEY):
        NÃO use chaves de API no mapa. Use o método de incorporação pública (iframe).
        Use exatamente este código na seção "Onde Estamos":
        <iframe src="https://maps.google.com/maps?q={endereco_encoded}&t=&z=15&ie=UTF8&iwloc=&output=embed" width="100%" height="300" style="border:0;" allowfullscreen="" loading="lazy"></iframe>

        INSTRUÇÃO TÉCNICA: Retorne APENAS o código HTML completo e auto-contido. Use Tailwind CSS via CDN. Não use markdown.
        """
        
        chat_completion = client.chat.completions.create(
            messages=[{"role": "system", "content": diretriz_master}, {"role": "user", "content": prompt_usuario}],
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
# BARRA LATERAL (NAVEGAÇÃO)
# ==========================================
st.sidebar.title("⚡ LeadFinder PRO")
st.sidebar.markdown("---")

if st.sidebar.button("📊 Dashboard", use_container_width=True): st.session_state.pagina = 'dashboard'
if st.sidebar.button("🔍 Prospecção", use_container_width=True): st.session_state.pagina = 'prospeccao'
if st.sidebar.button("💼 Meus Leads (CRM)", use_container_width=True): st.session_state.pagina = 'crm'

st.sidebar.markdown("---")
nome_agencia = st.sidebar.text_input("Nome da sua agência:", "Minha Agência")

# ==========================================
# PÁGINA: DASHBOARD
# ==========================================
if st.session_state.pagina == 'dashboard':
    st.title("📊 Dashboard de Vendas")
    st.write("Visão geral do seu negócio.")
    
    total_leads = len(st.session_state.crm_db)
    sites_gerados = len([l for l in st.session_state.crm_db if l.get('site_url')])
    fechados = len([l for l in st.session_state.crm_db if l.get('status') == 'Fechado'])
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Leads no CRM", total_leads)
    col2.metric("Sites Gerados", sites_gerados)
    col3.metric("Clientes Fechados", fechados)

# ==========================================
# PÁGINA: CRM (Gerenciar Leads)
# ==========================================
elif st.session_state.pagina == 'crm':
    st.title("💼 Meus Leads (CRM)")
    
    if not st.session_state.crm_db:
        st.warning("Nenhum lead no CRM ainda. Vá na aba de Prospecção para adicionar.")
    else:
        for i, lead in enumerate(st.session_state.crm_db):
            with st.expander(f"🏢 {lead['nome']} - Status: {lead['status']}"):
                st.write(f"📍 {lead['endereco']}")
                st.write(f"📞 {lead['telefone']}")
                
                novo_status = st.selectbox(
                    "Atualizar Status:", 
                    ["Novo Lead", "Site Criado", "Abordado", "Fechado", "Perdido"], 
                    index=["Novo Lead", "Site Criado", "Abordado", "Fechado", "Perdido"].index(lead['status']),
                    key=f"status_{i}"
                )
                if novo_status != lead['status']:
                    st.session_state.crm_db[i]['status'] = novo_status
                    st.rerun()
                
                if lead.get('site_url'):
                    st.markdown(f"🌐 **Site Gerado:** [Abrir Link]({lead['site_url']})")
                    msg = gerar_mensagem_abordagem(lead['nome'], lead['nicho'], lead['cidade'], lead['nota'], link_site=lead['site_url'], nome_agencia=nome_agencia)
                    st.text_area("Abordagem pronta:", msg, height=100, key=f"msg_{i}")
                
                num_limpo = re.sub(r'\D', '', lead['telefone'])
                if len(num_limpo) == 11 and num_limpo[2] == '9':
                    msg_encoded = urllib.parse.quote(gerar_mensagem_abordagem(lead['nome'], lead['nicho'], lead['cidade'], lead['nota'], link_site=lead.get('site_url'), nome_agencia=nome_agencia))
                    zap_link = f"https://wa.me/55{num_limpo}?text={msg_encoded}"
                    st.markdown(f'<a href="{zap_link}" target="_blank" class="action-link">📱 Enviar WhatsApp</a>', unsafe_allow_html=True)

# ==========================================
# PÁGINA: PROSPECÇÃO (A Busca)
# ==========================================
elif st.session_state.pagina == 'prospeccao':
    
    if st.session_state.empresa_selecionada is None:
        st.title("🔍 Encontre seus clientes")
        
        col1, col2, col3 = st.columns(3)
        with col1: nicho = st.selectbox("Setor:", NICHOS)
        with col2: estado = st.selectbox("Estado:", list(CIDADES_BR.keys()))
        with col3: cidade = st.text_input("Cidade:", "Sua Cidade") if estado == "Outro" else st.selectbox("Cidade:", CIDADES_BR[estado])
        
        nota_minima = st.slider("Nota mínima no Google:", 0.0, 5.0, 4.0, 0.1)
        
        if st.button("🔍 Buscar Empresas", use_container_width=True):
            if not api_key: st.error("Chave do Maps não encontrada.")
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
                        st.session_state.nicho = nicho
                        st.session_state.cidade = cidade
                    except Exception as e: st.error(f"Erro: {e}")

        if 'temp_leads' in st.session_state and st.session_state.temp_leads:
            st.markdown("### Resultados Encontrados:")
            for i, lead in enumerate(st.session_state.temp_leads):
                nome = lead.get('displayName', {}).get('text')
                end = lead.get('formattedAddress', '')
                nota = lead.get('rating', 'N/A')
                tel = lead.get('nationalPhoneNumber', '')
                
                with st.container(border=True):
                    col_info, col_btn = st.columns([4, 1])
                    with col_info:
                        st.markdown(f"**{nome}** ⭐ {nota}")
                        st.write(f"📍 {end}")
                    with col_btn:
                        if st.button("Selecionar", key=f"sel_{i}", use_container_width=True):
                            novo_lead = {
                                "nome": nome, "endereco": end, "telefone": tel, 
                                "nicho": st.session_state.nicho, "cidade": st.session_state.cidade, 
                                "nota": nota, "status": "Novo Lead", "site_url": None
                            }
                            st.session_state.crm_db.append(novo_lead)
                            st.session_state.empresa_selecionada = novo_lead
                            st.session_state.link_site_gerado = None
                            st.rerun()

    # --- TELA DE CRIAÇÃO DO SITE ---
    else:
        lead = st.session_state.empresa_selecionada
        st.title(f"🚀 Criar Site: {lead['nome']}")
        
        tab1, tab2 = st.tabs(["💻 Gerar Site", "📱 Enviar Abordagem"])
        
        with tab1:
            url_img = IMAGENS_NICHO.get(lead['nicho'], IMAGENS_NICHO["Outro"])
            st.image(url_img, caption="Imagem de Fundo Sugerida", use_column_width=True)
            
            if st.button("Gerar e Hospedar Site com IA", use_container_width=True):
                if "GROQ_API_KEY" in st.secrets:
                    with st.spinner("A Agência IA está desenhando o site..."):
                        prompt = f"""Crie um site para {lead['nome']} (Ramo: {lead['nicho']}).
                        Endereço: {lead['endereco']}. Botão WhatsApp: https://wa.me/55{re.sub(r'\D', '', lead['telefone'])}"""
                        
                        # Passamos o endereço para a função para consertar o mapa
                        link, erro = gerar_e_hospedar_site(prompt, st.secrets["GROQ_API_KEY"], url_img, lead['endereco'])
                        
                        if link:
                            st.session_state.link_site_gerado = link
                            for l in st.session_state.crm_db:
                                if l['nome'] == lead['nome']:
                                    l['site_url'] = link
                                    l['status'] = "Site Criado"
                            st.success("Site gerado com sucesso! Vá para a aba ao lado.")
                        else:
                            st.error(erro)
                else:
                    st.warning("Configure a GROQ_API_KEY nos Secrets.")

        with tab2:
            if st.session_state.link_site_gerado:
                msg = gerar_mensagem_abordagem(lead['nome'], lead['nicho'], lead['cidade'], lead['nota'], link_site=st.session_state.link_site_gerado, nome_agencia=nome_agencia)
                st.text_area("Mensagem pronta:", msg, height=150)
                
                num_limpo = re.sub(r'\D', '', lead['telefone'])
                zap_link = f"https://wa.me/55{num_limpo}?text={urllib.parse.quote(msg)}"
                
                st.markdown(f"""
                <a href="{zap_link}" target="_blank" style="display: block; background-color: #25D366; color: white; padding: 15px; text-align: center; font-weight: bold; border-radius: 8px; text-decoration: none;">
                    📱 Abrir WhatsApp e Enviar
                </a>
                """, unsafe_allow_html=True)
            else:
                st.warning("Gere o site primeiro.")
        
        if st.button("⬅️ Voltar para Prospecção", use_container_width=True):
            st.session_state.empresa_selecionada = None
            st.rerun()
