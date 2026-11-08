import streamlit as st
import urllib.parse

# Configuração da página
st.set_page_config(page_title="Painel de Prospecção Global - Douwen", page_icon="🌎", layout="wide")

st.title("🌎 Painel de Prospecção Global")
st.write("Busque clientes no Brasil e no exterior.")

# --- ENTRADA DE DADOS ---
st.subheader("1. Dados do Cliente")

col1, col2 = st.columns(2)

with col1:
    # Seletor de País
    pais = st.selectbox(
        "País do Cliente",
        ["Brasil", "Estados Unidos (EUA)", "Espanha", "México", "Portugal"]
    )
    
    nome_empresa = st.text_input("Nome da Empresa", placeholder="Ex: Novo Burguer")
    cidade = st.text_input("Cidade", placeholder="Ex: Miami / Madrid")

with col2:
    numero_whatsapp = st.text_input("WhatsApp (só números com 55 e DDD)", placeholder="Ex: 5547992334700")
    link_site_gerado = st.text_input("Link do Site (Vercel)", placeholder="Ex: https://site.vercel.app")
    status_whats = st.selectbox("Status do WhatsApp", ["Não informado", "Aberto", "Fechado"])

if st.button("Gerar Links e Abordagem", type="primary"):
    if not nome_empresa or not cidade:
        st.warning("Por favor, preencha o Nome da Empresa e a Cidade.")
    else:
        # Formatação de URLs
        empresa_formatada = urllib.parse.quote(f"{nome_empresa} {cidade} {pais}")
        
        # Links
        link_insta = f"https://www.instagram.com/explore/search/keyword/?q={empresa_formatada}"
        link_maps = f"https://www.google.com/maps/search/?api=1&query={empresa_formatada}"
        link_whatsapp = f"https://wa.me/{numero_whatsapp.replace(' ', '').replace('-', '')}" if numero_whatsapp else "#"

        # --- MENSAGENS DE ABORDAGEM (POR PAÍS) ---
        if pais == "Brasil":
            msg_gancho = f"Oi, tudo bem? Meu nome é Douwen, trabalho criando sites. Vi o perfil do {nome_empresa} e achei muito bom! Notei uma coisa que pode estar fazendo vocês perderem clientes. Posso te mostrar em 1 minuto?"
            msg_link = f"Show! Como vocês não têm um site, quem pesquisa no Google vai pro concorrente. Eu montei uma prévia gratuita: {link_site_gerado}. Se curtir, coloco no ar com o domínio próprio!"
        
        elif pais == "Estados Unidos (EUA)":
            msg_gancho = f"Hi! My name is Douwen, I build websites for local businesses. I was looking at {nome_empresa}'s profile and loved your work! I noticed something that might be costing you customers online. Can I show you in 1 minute?"
            msg_link = f"Great! Since you don't have a website, customers searching on Google go to competitors. I made a free preview for {nome_empresa}: {link_site_gerado}. If you like it, I can put it live with your own domain!"
        
        elif pais == "Espanha" or pais == "México":
            msg_gancho = f"¡Hola! Mi nombre es Douwen, creo sitios web para empresas. Vi el perfil de {nome_empresa} y me encantó su trabajo. Noté algo que podría estar haciendo que pierdan clientes. ¿Puedo mostrárselo en 1 minuto?"
            msg_link = f"¡Genial! Como no tienen sitio web, los clientes buscan en Google y van a la competencia. Hice una vista previa gratuita para {nome_empresa}: {link_site_gerado}. Si les gusta, ¡lo pongo en línea con su propio dominio!"

        elif pais == "Portugal":
            msg_gancho = f"Olá! O meu nome é Douwen, crio sites para empresas. Vi o perfil da {nome_empresa} e achei o vosso trabalho excelente! Reparei numa coisa que vos pode estar a fazer perder clientes. Posso mostrar em 1 minuto?"
            msg_link = f"Boa! Como não têm site, quem pesquisa no Google vai para a concorrência. Fiz uma prévia gratuita para a {nome_empresa}: {link_site_gerado}. Se gostarem, coloco no ar com o domínio próprio!"

        st.success("Tudo gerado com sucesso!")
        
        # --- EXIBIÇÃO DOS STATUS E BOTÕES ---
        st.subheader("2. Status e Links Rápidos")
        
        if status_whats == "Aberto":
            st.markdown("<h3 style='color: #25D366;'>🟢 WhatsApp: ABERTO</h3>", unsafe_allow_html=True)
        elif status_whats == "Fechado":
            st.markdown("<h3 style='color: #FF0000;'>🔴 WhatsApp: FECHADO</h3>", unsafe_allow_html=True)
        else:
            st.markdown("<h3 style='color: #888888;'>⚪ WhatsApp: Status não informado</h3>", unsafe_allow_html=True)

        st.write("---")
        
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            st.markdown(f'<a href="{link_insta}" target="_blank" style="display: block; text-align: center; background: linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%); color: white; padding: 12px; text-decoration: none; border-radius: 8px; font-weight: bold;">📷 Instagram</a>', unsafe_allow_html=True)
            
        with col_btn2:
            st.markdown(f'<a href="{link_whatsapp}" target="_blank" style="display: block; text-align: center; background-color: #25D366; color: white; padding: 12px; text-decoration: none; border-radius: 8px; font-weight: bold;">💬 WhatsApp</a>', unsafe_allow_html=True)
            
        with col_btn3:
            st.markdown(f'<a href="{link_maps}" target="_blank" style="display: block; text-align: center; background-color: #EA4335; color: white; padding: 12px; text-decoration: none; border-radius: 8px; font-weight: bold;">📍 Google Maps</a>', unsafe_allow_html=True)

        # --- EXIBIÇÃO DAS MENSAGENS ---
        st.subheader("3. Mensagens Prontas")
        st.info("💡 Mande esta mensagem primeiro (SEM o link):")
        st.code(msg_gancho, language="text")
        st.info("💡 Depois que responderem, envie esta:")
        st.code(msg_link, language="text")
