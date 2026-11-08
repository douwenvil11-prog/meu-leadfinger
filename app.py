import streamlit as st
import requests
import urllib.parse
import re

st.set_page_config(page_title="Prospecção Sênior - Douwen", page_icon="🔥", layout="centered")

st.title("🔥 Prospecção Sênior")
st.write("Busca rápida, com cache e mensagem pronta para enviar.")

# --- CONFIGURAÇÃO DA API ---
# Substitua "SUA_CHAVE_AQUI" pela sua chave real do Geoapify
API_KEY = "SUA_CHAVE_AQUI" 

# --- CACHE (Guarda os resultados para não gastar API) ---
@st.cache_data(ttl=3600)
def buscar_empresas(cidade, categoria, api_key):
    url_geo = f"https://api.geoapify.com/v1/geocode/search?text={urllib.parse.quote(cidade)}&type=city&format=json&limit=1&apiKey={api_key}"
    res_geo = requests.get(url_geo, timeout=10)
    if not res_geo.json().get('results'):
        return None, "Cidade não encontrada"
    
    place_id = res_geo.json()['results'][0]['place_id']
    
    url_places = f"https://api.geoapify.com/v2/places?categories={categoria}&filter=place:{place_id}&limit=50&apiKey={api_key}"
    res = requests.get(url_places, timeout=15)
    data = res.json()
    
    empresas = [p.get('properties', {}) for p in data.get('features', []) if 'website' not in p.get('properties', {})]
    return empresas, None

# --- INTERFACE ---
mapa_nichos = {
    "Barbearia / Salão": "service.beauty",
    "Restaurante": "catering.restaurant",
    "Hamburgueria / Lanches": "catering.fast_food",
    "Pet Shop": "commercial.pet",
    "Clínica de Estética": "service.beauty",
    "Academia": "sport.fitness",
    "Padaria": "commercial.food.bakery",
    "Oficina Mecânica": "service.vehicle.repair"
}

paises = ["Brasil", "Portugal", "Estados Unidos", "Espanha", "México"]

col1, col2 = st.columns(2)
with col1:
    pais = st.selectbox("País", paises)
    cidade = st.text_input("Cidade", placeholder="Ex: Lisboa, Miami...")
with col2:
    nicho = st.selectbox("Nicho", list(mapa_nichos.keys()))
    link_previa = st.text_input("Link da sua Prévia (Vercel)", placeholder="https://site.vercel.app")

if st.button("🔍 Buscar Empresas", type="primary", use_container_width=True):
    if not cidade:
        st.warning("Digite uma cidade.")
    elif "SUA_CHAVE_AQUI" in API_KEY:
        st.error("⚠️ Configure sua API Key no código (linha 12).")
    else:
        with st.spinner("Buscando..."):
            empresas, erro = buscar_empresas(cidade, mapa_nichos[nicho], API_KEY)
            
            if erro:
                st.error(erro)
            elif not empresas:
                st.warning("Nenhuma empresa sem site encontrada.")
            else:
                st.success(f"{len(empresas)} leads encontrados!")
                
                for i, props in enumerate(empresas):
                    nome = props.get('name', 'Sem nome')
                    tel_raw = props.get('contact', {}).get('phone', '') or props.get('phone', '')
                    
                    tel = re.sub(r'[^\d+]', '', tel_raw) if tel_raw else None
                    if tel and pais == "Brasil" and len(tel) >= 10 and not tel.startswith('55'):
                        tel = '55' + tel
                        
                    endereco = props.get('address_line2', 'Endereço não informado')
                    tem_telefone = tel is not None
                    
                    selo = "🔥 " if tem_telefone else "⚠️ "
                    
                    with st.expander(f"{selo}{nome}"):
                        st.write(f"📍 **Endereço:** {endereco}")
                        
                        if tem_telefone:
                            st.write(f"📞 **Telefone:** {tel}")
                        else:
                            st.write("📞 **Telefone:** Não informado")
                        
                        # --- AQUI ESTÁ A CORREÇÃO ---
                        # Agora usamos o Google para achar o Instagram oficial
                        query_insta_google = urllib.parse.quote(f'site:instagram.com "{nome}" "{cidade}"')
                        link_insta = f"https://www.google.com/search?q={query_insta_google}"
                        
                        col_b1, col_b2, col_b3 = st.columns(3)
                        termo_busca = urllib.parse.quote(f"{nome} {cidade}")
                        
                        with col_b1:
                            st.link_button("📷 Achar Insta", link_insta, use_container_width=True)
                        with col_b2:
                            if tem_telefone:
                                st.link_button("💬 WhatsApp", f"https://wa.me/{tel}", use_container_width=True)
                        with col_b3:
                            st.link_button("📍 Maps", f"https://www.google.com/maps/search/?api=1&query={termo_busca}", use_container_width=True)
                        
                        st.markdown("---")
                        st.markdown("**Mensagem Pronta (Copie):**")
                        
                        texto_link = f"\n\nDá uma olhada: {link_previa}" if link_previa else ""
                        
                        if pais == "Brasil":
                            msg = f"Oi, tudo bem? Meu nome é Douwen, trabalho criando sites. Vi o perfil do {nome} e reparei que vocês não têm um site próprio. Isso pode estar fazendo vocês perderem clientes. Posso te mostrar uma ideia?{texto_link}"
                        elif pais == "Portugal":
                            msg = f"Olá! O meu nome é Douwen, crio sites. Vi o perfil do {nome} e reparei que ainda não têm um site próprio. Posso mostrar uma ideia?{texto_link}"
                        elif pais in ["Espanha", "México"]:
                            msg = f"¡Hola! Mi nombre es Douwen, creo sitios web. Vi el perfil de {nome} y noté que no tienen sitio web. ¿Puedo mostrarles una idea?{texto_link}"
                        else:
                            msg = f"Hi! My name is Douwen, I build websites. I was looking at {nome} and noticed you don't have a website yet. Can I show you an idea?{texto_link}"

                        st.code(msg, language="text")
