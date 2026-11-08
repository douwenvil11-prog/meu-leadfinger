import streamlit as st
import requests
import urllib.parse
import re

st.set_page_config(page_title="Prospecção Sênior - Douwen", page_icon="🔥", layout="centered")

st.title("🔥 Prospecção Sênior")
st.write("Apenas números com WhatsApp (celular) e status da empresa.")

# --- CONFIGURAÇÃO DA API ---
try:
    API_KEY = st.secrets["GEOAPIFY_KEY"]
except KeyError:
    st.error("⚠️ Chave 'GEOAPIFY_KEY' não encontrada. Configure-a nos Secrets do Streamlit.")
    st.stop()

# --- CACHE ---
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

# --- FUNÇÃO PARA VALIDAR WHATSAPP (CORRIGIDA) ---
def validar_whatsapp(tel, pais_atual):
    if not tel:
        return None
    
    # Remove tudo que não é número
    num = re.sub(r'\D', '', tel)
    
    if pais_atual == "Brasil":
        # Regra de celular brasileiro: DDD (2) + 9 + 8 dígitos = 11 dígitos
        if len(num) == 11 and num[2] == '9':
            return f"55{num}"
        # Se já vier com 55 e for celular: 55 + DDD (2) + 9 + 8 = 13 dígitos
        elif len(num) == 13 and num.startswith('55') and num[4] == '9':
            return num
        else:
            # Se não começar com 9, é fixo ou inválido para WhatsApp
            return None 
    else:
        # Para fora, apenas devolve o número (sem validação rígida)
        return num if len(num) > 8 else None

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
                    
                    # Valida o número (só celular)
                    tel = validar_whatsapp(tel_raw, pais)
                    
                    endereco = props.get('address_line2', 'Endereço não informado')
                    tem_telefone = tel is not None
                    
                    # --- LÓGICA DE ABERTO / FECHADO ---
                    # Pega o horário de funcionamento. Se estiver vazio, coloca o ❌
                    horario_raw = props.get('opening_hours', '')
                    
                    if horario_raw:
                        status_horario = horario_raw
                        selo_aberto = ""
                    else:
                        status_horario = "Horário não informado (Fechado?)"
                        selo_aberto = "❌ "
                    
                    # Define o emoji baseado no telefone (premium ou não)
                    selo_tel = "🔥 " if tem_telefone else "⚠️ "
                    
                    # Título do expander
                    titulo_expander = f"{selo_aberto}{selo_tel}{nome}"
                    
                    with st.expander(titulo_expander, expanded=False):
                        st.write(f"📍 **Endereço:** {endereco}")
                        
                        # Mostra o horário (com o ❌ se não tiver)
                        if horario_raw:
                            st.write(f"🕒 **Horário:** {status_horario}")
                        else:
                            st.write(f"🕒 **Horário:** ❌ {status_horario}")
                        
                        if tem_telefone:
                            st.write(f"📞 **Telefone (WhatsApp):** {tel}")
                        else:
                            st.write("📞 **Telefone:** Sem celular válido")
                        
                        # Links
                        query_insta_google = urllib.parse.quote(f'site:instagram.com "{nome}" "{cidade}"')
                        link_insta = f"https://www.google.com/search?q={query_insta_google}"
                        
                        col_b1, col_b2, col_b3 = st.columns(3)
                        termo_busca = urllib.parse.quote(f"{nome} {cidade}")
                        
                        with col_b1:
                            st.link_button("📷 Achar Insta", link_insta, use_container_width=True)
                        with col_b2:
                            if tem_telefone:
                                st.link_button("💬 WhatsApp", f"https://wa.me/{tel}", use_container_width=True)
                            else:
                                # Se não tem celular, o botão fica desativado e com uma dica
                                st.button("💬 Sem Zap", disabled=True, use_container_width=True, key=f"sem_zap_{i}", help="Telefone fixo ou inválido para WhatsApp")
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
