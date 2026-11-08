import streamlit as st
import urllib.parse

# Configuração da página (mobile friendly)
st.set_page_config(page_title="Prospecção Global - Douwen", page_icon="🌎", layout="centered")

st.title("🌎 Prospecção Global")
st.write("Painel rápido para buscar clientes e gerar abordagens.")

# --- DICIONÁRIOS DE CIDADES E NICHOS ---
cidades_por_pais = {
    "Brasil": ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba", "Porto Alegre", "Salvador", "Recife", "Fortaleza", "Brasília", "Goiânia"],
    "Estados Unidos": ["Miami", "New York", "Los Angeles", "Chicago", "Houston", "Orlando", "Boston"],
    "Portugal": ["Lisboa", "Porto", "Braga", "Coimbra", "Faro", "Funchal"],
    "Espanha": ["Madrid", "Barcelona", "Valencia", "Sevilha", "Bilbao"],
    "México": ["Cidade do México", "Guadalajara", "Monterrey", "Cancún"]
}

nichos = ["Barbearia", "Restaurante", "Hamburgueria", "Pet Shop", "Clínica de Estética", "Academia", "Padaria", "Lanchonete", "Salão de Beleza", "Oficina Mecânica"]

# --- FORMULÁRIO ---
st.subheader("1. Escolha o Alvo")

col1, col2 = st.columns(2)
with col1:
    pais = st.selectbox("País", list(cidades_por_pais.keys()))
    nicho = st.selectbox("Nicho", nichos)
with col2:
    cidade = st.selectbox("Cidade", cidades_por_pais[pais])
    nome_empresa = st.text_input("Nome da Empresa (Opcional)", placeholder="Ex: Novo Burguer")

st.subheader("2. Detalhes do Site")
link_site_gerado = st.text_input("Link do Site (Vercel)", placeholder="https://site.vercel.app")
numero_whatsapp = st.text_input("WhatsApp (só números com 55 e DDD)", placeholder="Ex: 5547992334700")

# --- PROCESSAMENTO ---
if st.button("Gerar Links e Abordagem", type="primary", use_container_width=True):
    
    # Monta o termo de busca (se não tiver nome da empresa, usa o nicho)
    termo_busca = f"{nome_empresa} {cidade}" if nome_empresa else f"{nicho} {cidade}"
    empresa_formatada = urllib.parse.quote(termo_busca)
    
    # Gera os links
    link_insta = f"https://www.instagram.com/explore/search/keyword/?q={empresa_formatada}"
    link_maps = f"https://www.google.com/maps/search/?api=1&query={empresa_formatada}"
    link_whatsapp = f"https://wa.me/{numero_whatsapp.replace(' ', '').replace('-', '')}" if numero_whatsapp else "https://wa.me"
    
    # Gera o nome do domínio sugerido
    nome_dominio = nome_empresa.lower().replace(" ", "") if nome_empresa else "seunegocio"

    # --- MENSAGENS POR IDIOMA ---
    if pais == "Brasil":
        msg_gancho = f"Oi, tudo bem? Meu nome é Douwen, trabalho criando sites. Vi o perfil do {nome_empresa or nicho} e achei muito bom! Notei uma coisa que pode estar fazendo vocês perderem clientes. Posso te mostrar em 1 minuto?"
        msg_link = f"Show! Como vocês não têm um site, quem pesquisa no Google vai pro concorrente. Eu montei uma prévia gratuita: {link_site_gerado}. Se curtir, coloco no ar com o domínio (www.{nome_dominio}.com.br)!"
    elif pais == "Estados Unidos":
        msg_gancho = f"Hi! My name is Douwen, I build websites for local businesses. I was looking at {nome_empresa or nicho}'s profile and loved your work! I noticed something that might be costing you customers online. Can I show you in 1 minute?"
        msg_link = f"Great! Since you don't have a website, customers searching on Google go to competitors. I made a free preview: {link_site_gerado}. If you like it, I can put it live with your own domain (www.{nome_dominio}.com)!"
    elif pais in ["Espanha", "México"]:
        msg_gancho = f"¡Hola! Mi nombre es Douwen, creo sitios web. Vi el perfil de {nome_empresa or nicho} y me encantó su trabajo. Noté algo que podría estar haciendo que pierdan clientes. ¿Puedo mostrárselo en 1 minuto?"
        msg_link = f"¡Genial! Como no tienen sitio web, los clientes buscan en Google y van a la competencia. Hice una vista previa gratuita: {link_site_gerado}. Si les gusta, ¡lo pongo en línea con su dominio (www.{nome_dominio}.com)!"
    elif pais == "Portugal":
        msg_gancho = f"Olá! O meu nome é Douwen, crio sites para empresas. Vi o perfil da {nome_empresa or nicho} e achei o vosso trabalho excelente! Reparei numa coisa que vos pode estar a fazer perder clientes. Posso mostrar em 1 minuto?"
        msg_link = f"Boa! Como não têm site, quem pesquisa no Google vai para a concorrência. Fiz uma prévia gratuita: {link_site_gerado}. Se gostarem, coloco no ar com o domínio próprio (www.{nome_dominio}.pt)!"

    st.success(f"Pronto! Alvo: {termo_busca}")
    
    # --- BOTÕES NATIVOS (NÃO RECARREGAM A PÁGINA) ---
    st.subheader("3. Links Rápidos")
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        st.link_button("📷 Instagram", link_insta, use_container_width=True)
    with col_btn2:
        st.link_button("💬 WhatsApp", link_whatsapp, use_container_width=True)
    with col_btn3:
        st.link_button("📍 Maps", link_maps, use_container_width=True)

    # --- MENSAGENS ---
    st.subheader("4. Abordagem (Copie e Cole)")
    
    st.info("💡 Mande esta primeiro (sem link):")
    st.code(msg_gancho, language="text")
    
    st.info("💡 Espere a resposta. Depois envie esta:")
    st.code(msg_link, language="text")

    # Botão para limpar o formulário e buscar outro
    if st.button("🔄 Limpar e Buscar Outro"):
        st.rerun()
