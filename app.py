import streamlit as st
import requests
import urllib.parse

st.set_page_config(page_title="Prospecção OSM - Douwen", page_icon="🌎", layout="centered")
st.title("🌎 Prospecção Global (OpenStreetMap)")
st.write("Busca empresas sem site usando dados abertos e gratuitos.")

# Mapeamento de Nicho para a "tag" do OpenStreetMap
# O OSM usa tags específicas. Ex: Restaurante = amenity=restaurant
mapa_nichos = {
    "Barbearia": 'shop="hairdresser"',
    "Restaurante": 'amenity="restaurant"',
    "Hamburgueria": 'amenity="fast_food"',
    "Pet Shop": 'shop="pet"',
    "Clínica de Estética": 'shop="beauty"',
    "Academia": 'leisure="fitness_centre"',
    "Padaria": 'shop="bakery"',
    "Salão de Beleza": 'shop="hairdresser"',
    "Oficina Mecânica": 'shop="car_repair"'
}

pais = st.selectbox("País", ["Brasil", "Portugal", "Espanha", "Estados Unidos", "México"])
nicho = st.selectbox("Nicho", list(mapa_nichos.keys()))
cidade = st.text_input("Cidade", placeholder="Ex: São Paulo, Lisboa, Miami...")

if st.button("🔍 Buscar Empresas SEM Site", type="primary", use_container_width=True):
    if not cidade:
        st.warning("Digite uma cidade.")
    else:
        # Monta a query do Overpass. 
        # A linha principal é: (node ou way ou relation) com a tag do nicho e SEM a tag "website"
        tag_nicho = mapa_nichos[nicho]
        # O [!"website"] significa "não tem o campo website"
        query = f"""
        [out:json][timeout:60];
        area["name"="{cidade}"]->.a;
        (
          nwr[{tag_nicho}][!"website"][!"contact:website"](area.a);
        );
        out center tags 50;
        """
        
        # A Overpass exige um User-Agent identificável
        headers = {
            "User-Agent": "ProspeccaoDouwen/1.0 (contato: seu-email@exemplo.com)"
        }
        
        with st.spinner(f"Buscando {nicho}s em {cidade}..."):
            try:
                # Faz a requisição POST para a Overpass API
                resposta = requests.post(
                    "https://overpass-api.de/api/interpreter",
                    data={"data": query},
                    headers=headers,
                    timeout=90
                )
                resposta.raise_for_status()
                dados = resposta.json()
                
                elementos = dados.get("elements", [])
                
                if not elementos:
                    st.warning("Nenhuma empresa sem site encontrada. Tente outra cidade ou nicho.")
                else:
                    st.success(f"Encontramos {len(elementos)} empresas sem site!")
                    
                    for el in elementos:
                        tags = el.get("tags", {})
                        nome = tags.get("name", "Nome não informado")
                        telefone = tags.get("phone", tags.get("contact:phone", "Sem telefone"))
                        
                        # Monta um endereço simples a partir das tags
                        rua = tags.get("addr:street", "")
                        numero = tags.get("addr:housenumber", "")
                        endereco = f"{rua}, {numero}" if rua else "Endereço não informado"
                        
                        # Links
                        termo_busca = urllib.parse.quote(f"{nome} {cidade}")
                        link_insta = f"https://www.instagram.com/explore/search/keyword/?q={termo_busca}"
                        link_maps = f"https://www.google.com/maps/search/?api=1&query={termo_busca}"
                        
                        # Mensagem (mesma lógica de país que você já tem)
                        msg = f"Oi, tudo bem? Meu nome é Douwen, trabalho criando sites. Vi o perfil do {nome} e reparei que vocês não têm um site próprio. Isso pode estar fazendo vocês perderem clientes no Google. Posso te mostrar uma ideia em 1 minuto?"
                        
                        with st.expander(f"🏢 {nome}"):
                            st.write(f"📍 **Endereço:** {endereco}")
                            st.write(f"📞 **Telefone:** {telefone}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.link_button("📷 Instagram", link_insta, use_container_width=True)
                            with col2:
                                st.link_button("📍 Maps", link_maps, use_container_width=True)
                            
                            st.markdown("**Mensagem:**")
                            st.code(msg, language="text")
                            
            except Exception as e:
                st.error(f"Erro na busca: {e}")
