import streamlit as st
import requests
import urllib.parse
import re

st.set_page_config(page_title="Prospecção Rápida - Douwen", page_icon="⚡", layout="centered")

st.title("⚡ Prospecção Rápida (Geoapify)")
st.write("Busca empresas sem site em segundos, sem travamentos.")

# --- CONFIGURAÇÃO DA API ---
st.sidebar.header("🔑 Configuração")
api_key = st.sidebar.text_input("Cole sua Geoapify API Key", type="password")
st.sidebar.markdown("[Pegue sua chave grátis aqui](https://www.geoapify.com/)")

# --- MAPEAMENTO DE NICHO ---
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

st.subheader("1. Escolha o Alvo")
col1, col2 = st.columns(2)
with col1:
    pais = st.selectbox("País", paises)
    cidade = st.text_input("Cidade", placeholder="Ex: Lisboa, Miami, Cascavel...")
with col2:
    nicho = st.selectbox("Nicho", list(mapa_nichos.keys()))

def limpar_telefone(tel, pais_atual):
    if not tel:
        return None
    tel_limpo = re.sub(r'[^\d+]', '', tel)
    if tel_limpo.startswith('0'):
        tel_limpo = tel_limpo[1:]
    if pais_atual == "Brasil" and len(tel_limpo) >= 10 and not tel_limpo.startswith('55'):
        tel_limpo = '55' + tel_limpo
    return tel_limpo

if st.button("🔍 Buscar Empresas SEM Site", type="primary", use_container_width=True):
    if not api_key:
        st.error("⚠️ Cole sua Geoapify API Key na barra lateral esquerda.")
    elif not cidade:
        st.warning("⚠️ Digite o nome da cidade.")
    else:
        categoria = mapa_nichos[nicho]
        
        with st.spinner(f"Buscando ID da cidade de {cidade}..."):
            try:
                # ETAPA 1: Geocodificar a cidade para obter o place_id
                url_geocode = f"https://api.geoapify.com/v1/geocode/search?text={urllib.parse.quote(cidade)}&type=city&format=json&limit=1&apiKey={api_key}"
                res_geo = requests.get(url_geocode, timeout=10)
                res_geo.raise_for_status()
                dados_geo = res_geo.json()
                
                if not dados_geo.get('results'):
                    st.error(f"Cidade '{cidade}' não encontrada. Verifique o nome.")
                    st.stop()
                
                place_id = dados_geo['results'][0]['place_id']
                
                # ETAPA 2: Buscar empresas usando o place_id
                st.spinner(f"Buscando {nicho}s em {cidade}...")
                url_places = f"https://api.geoapify.com/v2/places?categories={categoria}&filter=place:{place_id}&limit=50&apiKey={api_key}"
                
                response = requests.get(url_places, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                features = data.get('features', [])
                
                # Filtra APENAS quem não tem o campo 'website'
                empresas_sem_site = []
                for f in features:
                    props = f.get('properties', {})
                    if 'website' not in props:
                        empresas_sem_site.append(props)
                
                if not empresas_sem_site:
                    st.warning("Nenhuma empresa sem site encontrada nessa busca. Tente outra cidade ou nicho.")
                else:
                    st.success(f"Encontramos {len(empresas_sem_site)} empresas SEM SITE!")
                    
                    for props in empresas_sem_site:
                        nome = props.get('name', 'Nome não informado')
                        tel_raw = props.get('contact', {}).get('phone', '') or props.get('phone', '')
                        telefone = limpar_telefone(tel_raw, pais)
                        endereco = props.get('address_line2', 'Endereço não informado')
                        
                        termo_busca = urllib.parse.quote(f"{nome} {cidade}")
                        link_insta = f"https://www.instagram.com/explore/search/keyword/?q={termo_busca}"
                        link_maps = f"https://www.google.com/maps/search/?api=1&query={termo_busca}"
                        
                        # Mensagem
                        if pais == "Brasil":
                            msg = f"Oi, tudo bem? Meu nome é Douwen, trabalho criando sites. Vi o perfil do {nome} e reparei que vocês não têm um site próprio. Isso pode estar fazendo vocês perderem clientes no Google. Posso te mostrar uma ideia em 1 minuto?"
                        elif pais == "Portugal":
                            msg = f"Olá! O meu nome é Douwen, crio sites. Vi o perfil do {nome} e reparei que ainda não têm um site próprio. Isso pode estar a fazer-vos perder clientes. Posso mostrar uma ideia em 1 minuto?"
                        elif pais in ["Espanha", "México"]:
                            msg = f"¡Hola! Mi nombre es Douwen, creo sitios web. Vi el perfil de {nome} y noté que no tienen sitio web. Esto podría hacerles perder clientes. ¿Puedo mostrarles una idea en 1 minuto?"
                        else:
                            msg = f"Hi! My name is Douwen, I build websites. I was looking at {nome} and noticed you don't have a website yet. This might be costing you customers. Can I show you an idea in 1 minute?"

                        with st.expander(f"🏢 {nome}"):
                            st.write(f"📍 **Endereço:** {endereco}")
                            st.write(f"📞 **Telefone:** {telefone if telefone else 'Não informado'}")
                            
                            col_btn1, col_btn2, col_btn3 = st.columns(3)
                            with col_btn1:
                                st.link_button("📷 Instagram", link_insta, use_container_width=True)
                            with col_btn2:
                                if telefone:
                                    st.link_button("💬 WhatsApp", f"https://wa.me/{telefone}", use_container_width=True)
                                else:
                                    st.button("💬 Sem Zap", disabled=True, use_container_width=True)
                            with col_btn3:
                                st.link_button("📍 Maps", link_maps, use_container_width=True)
                            
                            st.markdown("---")
                            st.markdown("**Mensagem de Abordagem:**")
                            st.code(msg, language="text")
                            
            except Exception as e:
                st.error(f"Erro na busca: {e}. Verifique sua API Key e o nome da cidade.")
