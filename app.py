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

# --- LISTA DE SERVIDORES ALTERNATIVOS (A CORREÇÃO DO ERRO 502) ---
LISTA_ENDPOINTS = [
    "https://overpass.private.coffee/api/interpreter", # Preferido: mais estável
    "https://overpass-api.de/api/interpreter",         # Servidor principal
    "https://overpass.kumi.systems/api/interpreter",   # Alternativo
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter" # Último recurso
]

# --- INTERFACE DE BUSCA ---
st.subheader("1. Escolha o Alvo")

col1, col2 = st.columns(2)
with col1:
    pais = st.selectbox("País", list(cidades_por_pais.keys()))
    cidade_opcoes = cidades_por_pais[pais] + ["Outra (Digitar)"]
    cidade_selecionada = st.selectbox("Cidade", cidade_opcoes)
    
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
    tel_limpo = re.sub(r'[^\d+]', '', tel)
    if tel_limpo.startswith('0'):
        tel_limpo = tel_limpo[1:]
    # Adiciona 55 se for Brasil e o número parecer local
    if pais == "Brasil" and len(tel_limpo) >= 10 and not tel_limpo.startswith('55'):
        tel_limpo = '55' + tel_limpo
    return tel_limpo

# --- BOTÃO DE BUSCA ---
if st.button("🔍 Buscar Empresas SEM Site", type="primary", use_container_width=True):
    if not cidade:
        st.warning("⚠️ Por favor, selecione ou digite uma cidade.")
    else:
        tag_nicho = mapa_nichos[nicho]
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
        
        # --- LÓGICA DE TENTATIVA E ERRO (RETRY) ---
        dados = None
        erro_final = None
        
        with st.spinner(f"Buscando {nicho}s em {cidade}... (tentando servidores alternativos se necessário)"):
            for endpoint in LISTA_ENDPOINTS:
                try:
                    resposta = requests.post(endpoint, data={"data": query}, headers=headers, timeout=30)
                    # Se o servidor retornar 502, 503 ou 504, a exceção é lançada e passamos para o próximo
                    resposta.raise_for_status()
                    dados = resposta.json()
                    break # Se funcionou, sai do loop
                except Exception as e:
                    erro_final = e
                    # Continua para o próximo endpoint da lista
                    continue
            
            if dados is None:
                st.error(f"Todos os servidores falharam. Último erro: {erro_final}. Tente novamente em alguns minutos.")
            else:
                elementos = dados.get("elements", [])
                
                if not elementos:
                    st.warning("Nenhuma empresa sem site encontrada. Tente outra cidade ou nicho.")
                else:
                    st.success(f"Encontramos {len(elementos)} empresas sem site!")
                    
                    for el in elementos:
                        tags = el.get("tags", {})
                        nome = tags.get("name", "Nome não informado")
                        telefone_raw = tags.get("phone", tags.get("contact:phone", ""))
                        telefone = limpar_telefone(telefone_raw)
                        
                        rua = tags.get("addr:street", "")
                        numero = tags.get("addr:housenumber", "")
                        endereco = f"{rua}, {numero}" if rua else "Endereço não informado"
                        
                        termo_busca = urllib.parse.quote(f"{nome} {cidade}")
                        link_insta = f"https://www.instagram.com/explore/search/keyword/?q={termo_busca}"
                        link_maps = f"https://www.google.com/maps/search/?api=1&query={termo_busca}"
                        
                        if pais == "Brasil":
                            msg = f"Oi, tudo bem? Meu nome é Douwen, trabalho criando sites. Vi o perfil do {nome} e reparei que vocês não têm um site próprio. Isso pode estar fazendo vocês perderem clientes no Google. Posso te mostrar uma ideia em 1 minuto?"
                        elif pais == "Portugal":
                            msg = f"Olá! O meu nome é Douwen, crio sites. Vi o perfil da {nome} e reparei que ainda não têm um site próprio. Isso pode estar a fazer-vos perder clientes. Posso mostrar uma ideia em 1 minuto?"
                        elif pais in ["Espanha", "México"]:
                            msg = f"¡Hola! Mi nombre es Douwen, creo sitios web. Vi el perfil de {nome} y noté que no tienen sitio web. Esto podría hacerles perder clientes. ¿Puedo mostrarles una idea en 1 minuto?"
                        else:
                            msg = f"Hi! My name is Douwen, I build websites. I was looking at {nome} and noticed you don't have a website yet. This might be costing you customers. Can I show you an idea in 1 minute?"

                        with st.expander(f"🏢 {nome}"):
                            st.write(f"📍 **Endereço:** {endereco}")
                            st.write(f"📞 **Telefone:** {telefone if telefone else 'Não informado no mapa'}")
                            
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
