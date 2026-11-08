import streamlit as st
import googlemaps
import urllib.parse

# Configuração da página (Mobile Friendly)
st.set_page_config(page_title="Prospecção Global - Douwen", page_icon="🌎", layout="centered")

st.title("🌎 Prospecção Inteligente")
st.write("Busca empresas no Google Maps e filtra APENAS as que NÃO têm site.")

# --- CONFIGURAÇÃO DA API (Barra Lateral) ---
st.sidebar.header("⚙️ Configuração")
api_key = st.sidebar.text_input("Insira sua Google Maps API Key", type="password")

# --- OPÇÕES DE BUSCA ---
st.subheader("1. Escolha o Alvo")

paises = ["Brasil", "Portugal", "Espanha", "Estados Unidos", "México", "Itália", "França"]
nichos = ["Barbearia", "Restaurante", "Hamburgueria", "Pet Shop", "Clínica de Estética", "Academia", "Padaria", "Lanchonete", "Salão de Beleza", "Oficina Mecânica"]

col1, col2 = st.columns(2)
with col1:
    pais = st.selectbox("País", paises)
    nicho = st.selectbox("Nicho", nichos)
with col2:
    # Campo de texto livre para a cidade, permitindo buscar em qualquer lugar
    cidade = st.text_input("Cidade", placeholder="Ex: Miami, Lisboa, São Paulo...")

# --- BOTÃO DE BUSCA ---
if st.button("🔍 Buscar Empresas SEM Site", type="primary", use_container_width=True):
    
    if not api_key:
        st.error("⚠️ Por favor, insira sua Google Maps API Key na barra lateral esquerda para buscar.")
    elif not cidade:
        st.warning("⚠️ Por favor, digite o nome da cidade.")
    else:
        try:
            with st.spinner(f"Buscando {nicho}s em {cidade}..."):
                gmaps = googlemaps.Client(key=api_key)
                # Monta a query de busca (ex: "Barbearia in Miami, Estados Unidos")
                query = f"{nicho} in {cidade}, {pais}"
                
                # Faz a busca na API do Google
                places_result = gmaps.places(query=query)
                
                empresas_encontradas = 0
                
                if places_result['results']:
                    # Aqui está o segredo: Filtra apenas quem NÃO tem website
                    for place in places_result['results']:
                        if 'website' not in place:
                            empresas_encontradas += 1
                            nome_empresa = place.get('name')
                            endereco = place.get('formatted_address', 'Endereço não informado')
                            telefone = place.get('formatted_phone_number', 'Sem telefone')
                            
                            # Criação dos Links (Instagram e Maps)
                            termo_busca = urllib.parse.quote(f"{nome_empresa} {cidade}")
                            link_insta = f"https://www.instagram.com/explore/search/keyword/?q={termo_busca}"
                            link_maps = f"https://www.google.com/maps/search/?api=1&query={termo_busca}"

                            # --- CRIAÇÃO DA MENSAGEM HUMANIZADA (POR IDIOMA) ---
                            if pais == "Brasil":
                                msg_gancho = f"Oi, tudo bem? Meu nome é Douwen, trabalho criando sites. Vi o perfil do {nome_empresa} e reparei que vocês não têm um site próprio. Isso pode estar fazendo vocês perderem clientes no Google. Posso te mostrar uma ideia em 1 minuto?"
                            elif pais == "Portugal":
                                msg_gancho = f"Olá! O meu nome é Douwen, crio sites para empresas. Vi o perfil da {nome_empresa} e reparei que ainda não têm um site próprio. Isso pode estar a fazer-vos perder clientes. Posso mostrar uma ideia em 1 minuto?"
                            elif pais in ["Espanha", "México"]:
                                msg_gancho = f"¡Hola! Mi nombre es Douwen, creo sitios web. Vi el perfil de {nome_empresa} y noté que no tienen sitio web. Esto podría hacerles perder clientes. ¿Puedo mostrarles una idea en 1 minuto?"
                            else: # Inglês (EUA, Itália, França, etc. se for falar inglês)
                                msg_gancho = f"Hi! My name is Douwen, I build websites. I was looking at {nome_empresa} and noticed you don't have a website yet. This might be costing you customers. Can I show you an idea in 1 minute?"

                            # --- EXIBIÇÃO DO CLIENTE NA TELA ---
                            with st.expander(f"🏢 {nome_empresa}", expanded=True):
                                st.write(f"📍 **Endereço:** {endereco}")
                                st.write(f"📞 **Telefone:** {telefone}")
                                
                                # Botões lado a lado (Não recarregam a página)
                                col_btn1, col_btn2 = st.columns(2)
                                with col_btn1:
                                    st.link_button("📷 Buscar no Instagram", link_insta, use_container_width=True)
                                with col_btn2:
                                    st.link_button("📍 Ver no Maps", link_maps, use_container_width=True)
                                
                                st.markdown("---")
                                st.markdown("**Mensagem de Abordagem (Clique no ícone de copiar):**")
                                # Caixa de texto com botão de copiar nativo
                                st.code(msg_gancho, language="text")
                                
                if empresas_encontradas == 0:
                    st.warning("Nenhuma empresa sem site foi encontrada nessa busca. Tente outro nicho ou cidade.")
                else:
                    st.success(f"Busca concluída! Encontramos {empresas_encontradas} empresas sem site.")

        except Exception as e:
            st.error(f"Erro na busca: Verifique se sua API Key está correta e se o Google Places API está ativado. Detalhe do erro: {e}")
