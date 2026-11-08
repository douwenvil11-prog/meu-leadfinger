import streamlit as st
import requests
import urllib.parse
import re

# Configuração da página
st.set_page_config(page_title="Prospecção Global - Douwen", page_icon="🌎", layout="centered")

st.title("🌎 Prospecção Inteligente")
st.write("Busca empresas sem site, com contato direto no WhatsApp e Instagram.")

# --- LISTA DE CIDADES POR PAÍS ---
cidades_por_pais = {
    "Brasil": ["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba", "Porto Alegre", "Salvador", "Recife", "Fortaleza", "Brasília", "Goiânia", "Campinas", "Manaus"],
    "Portugal": ["Lisboa", "Porto", "Braga", "Coimbra", "Faro", "Funchal"],
    "Estados Unidos": ["Miami", "New York", "Los Angeles", "Chicago", "Houston", "Orlando", "Boston"],
    "Espanha": ["Madrid", "Barcelona", "Valencia", "Sevilha", "Bilbao"],
    "México": ["Cidade do México", "Guadalajara", "Monterrey", "Cancún"]
}

# Mapeamento de Nicho para a "tag" do OpenStreetMap
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

# --- INTERFACE DE BUSCA ---
st.subheader("1. Escolha o Alvo")

col1, col2 = st.columns(2)
with col1:
    pais = st.selectbox("País", list(cidades_por_pais.keys()))
    # Opções de cidades baseadas no país escolhido
    cidade_opcoes = cidades_por_pais[pais] + ["Outra (Digitar)"]
    cidade_selecionada = st.selectbox("Cidade", cidade_opcoes)
    
    # Se escolher "Outra", mostra o campo de texto
    if cidade_selecionada == "Outra (Digitar)":
        cidade = st.text_input("Digite a cidade", placeholder="Ex: Santos")
    else:
        cidade = cidade_selecionada

with col2:
    nicho = st.selectbox("Nicho", list(mapa_nichos.keys()))

# --- FUNÇÃO PARA LIMPAR O TELEFONE ---
def limpar_telefone(tel):
    if not tel:
        return None
    # Remove tudo que não for número ou o sinal de +
    tel_limpo = re.sub(r'[^\d+]', '', tel)
    # Se o número começar com 0, remove (padrão de algumas regiões)
    if tel_limpo.startswith('0'):
        tel_limpo = tel_limpo[1:]
    # Se for Brasil e não tiver o 55, adiciona (heurística simples)
    if pais == "Brasil" and len(tel_limpo) >= 10 and not tel_limpo.startswith('55'):
        tel_limpo = '55' + tel_limpo
    return tel_limpo

# --- BOTÃO DE BUSCA ---
if st.button("🔍 Buscar Empresas SEM Site", type="primary", use_container_width=True):
    if not cidade:
        st.warning("⚠️ Por favor, selecione ou digite uma cidade.")
    else:
        tag_nicho = mapa_nichos[nicho]
        # Query: Busca empresas na cidade com o nicho e SEM website
        query = f"""
        [out:json][timeout:60];
        area["name"="{cidade}"]->.a;
        (
          nwr[{tag_nicho}][!"website"][!"contact:website"](area.a);
        );
        out center tags 50;
        """
        
        headers = {
            "User-Agent": "ProspeccaoDouwen/1.0 (contato: seu-email@exemplo.com)"
        }
        
        with st.spinner(f"Buscando {nicho}s em {cidade}..."):
            try:
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
                        
                        # Pega o telefone (tenta várias tags comuns do OSM)
                        telefone_raw = tags.get("phone", tags.get("contact:phone", ""))
                        telefone = limpar_telefone(telefone_raw)
                        
                        # Endereço
                        rua = tags.get("addr:street", "")
                        numero = tags.get("addr:housenumber", "")
                        endereco = f"{rua}, {numero}" if rua else "Endereço não informado"
                        
                        # Links
                        termo_busca = urllib.parse.quote(f"{nome} {cidade}")
                        link_insta = f"https://www.instagram.com/explore/search/keyword/?q={termo_busca}"
                        link_maps = f"https://www.google.com/maps/search/?api=1&query={termo_busca}"
                        
                        # Mensagem (Lógica por país)
                        if pais == "Brasil":
                            msg = f"Oi, tudo bem? Meu nome é Douwen, trabalho criando sites. Vi o perfil do {nome} e reparei que vocês não têm um site próprio. Isso pode estar fazendo vocês perderem clientes no Google. Posso te mostrar uma ideia em 1 minuto?"
                        elif pais == "Portugal":
                            msg = f"Olá! O meu nome é Douwen, crio sites. Vi o perfil da {nome} e reparei que ainda não têm um site próprio. Isso pode estar a fazer-vos perder clientes. Posso mostrar uma ideia em 1 minuto?"
                        elif pais in ["Espanha", "México"]:
                            msg = f"¡Hola! Mi nombre es Douwen, creo sitios web. Vi el perfil de {nome} y noté que no tienen sitio web. Esto podría hacerles perder clientes. ¿Puedo mostrarles una idea en 1 minuto?"
                        else:
                            msg = f"Hi! My name is Douwen, I build websites. I was looking at {nome} and noticed you don't have a website yet. This might be costing you customers. Can I show you an idea in 1 minute?"

                        # --- EXIBIÇÃO DO CLIENTE ---
                        with st.expander(f"🏢 {nome}"):
                            st.write(f"📍 **Endereço:** {endereco}")
                            st.write(f"📞 **Telefone:** {telefone if telefone else 'Não informado no mapa'}")
                            
                            # Criando 3 colunas para os botões
                            col_btn1, col_btn2, col_btn3 = st.columns(3)
                            
                            with col_btn1:
                                st.link_button("📷 Instagram", link_insta, use_container_width=True)
                            
                            with col_btn2:
                                if telefone:
                                    link_whatsapp = f"https://wa.me/{telefone}"
                                    st.link_button("💬 WhatsApp", link_whatsapp, use_container_width=True)
                                else:
                                    st.button("💬 Sem Zap", disabled=True, use_container_width=True, help="Telefone não encontrado no mapa")
                            
                            with col_btn3:
                                st.link_button("📍 Maps", link_maps, use_container_width=True)
                            
                            st.markdown("---")
                            st.markdown("**Mensagem de Abordagem (Copie e Cole):**")
                            st.code(msg, language="text")
                            
            except Exception as e:
                st.error(f"Erro na busca: {e}")
