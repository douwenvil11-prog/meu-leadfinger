import streamlit as st
import requests
import re

st.set_page_config(page_title="LeadFinder PRO", layout="wide", page_icon="🚀")

# --- LISTA DE NICHOS ---
NICHOS = [
    "Hamburgueria", "Pizzaria", "Barbearia", "Sorveteria/Açaí", 
    "Restaurante", "Mecânica", "Lava Jato", "Pet Shop", 
    "Clínica/Consultório", "Academia", "Padaria", "Buffet", "Outro"
]

# --- LISTA DE ESTADOS E CIDADES ---
CIDADES_BR = {
    "São Paulo": ["São Paulo", "Campinas", "Santos"],
    "Minas Gerais": ["Belo Horizonte", "Uberlândia", "Cataguases"],
    "Piauí": ["Teresina", "Parnaíba", "Picos", "Timon"],
    "Maranhão": ["São Luís", "Imperatriz", "Timon", "Caxias"],
    "Outro": ["Digitar manualmente"]
}

st.title("🚀 LeadFinder PRO - Prospecção Premium")
st.write("Encontre empresas sem site, gere abordagens e crie sites com IA.")

# --- LÓGICA DA CHAVE DE API ---
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = st.sidebar.text_input("Insira sua Google Maps API Key:", type="password")

if api_key:
    st.sidebar.markdown("### 🤖 Sua Agência")
    nome_agencia = st.sidebar.text_input("Nome da sua agência:", "Nexo Sites")
    
    st.sidebar.markdown("### 📍 Filtros de Busca")
    nicho_selecionado = st.sidebar.selectbox("Qual o nicho?", NICHOS)
    termo = st.sidebar.text_input("Digite o nicho:", "seu nicho aqui") if nicho_selecionado == "Outro" else nicho_selecionado
    
    estado = st.sidebar.selectbox("Estado:", list(CIDADES_BR.keys()))
    cidade = st.sidebar.selectbox("Cidade:", CIDADES_BR[estado]) if estado != "Outro" else st.sidebar.text_input("Digite a cidade:", "Sua Cidade, UF")

    filtro_tamanho = st.sidebar.checkbox("Filtrar empresas pequenas (< 300 avaliações)", value=True)

    if st.sidebar.button("Pesquisar Empresas", type="primary", use_container_width=True):
        with st.spinner('Buscando empresas...'):
            try:
                url = "https://places.googleapis.com/v1/places:searchText"
                headers = {
                    'Content-Type': 'application/json',
                    'X-Goog-Api-Key': api_key,
                    'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri,places.currentOpeningHours.openNow,places.userRatingCount,places.rating'
                }
                payload = {"textQuery": f"{termo} em {cidade}, {estado}", "maxResultCount": 20}

                response = requests.post(url, json=payload, headers=headers)
                data = response.json()
                places = data.get('places', [])
                
                leads = []
                for p in places:
                    if 'websiteUri' not in p:
                        qtd_avaliacoes = p.get('userRatingCount', 0)
                        if filtro_tamanho and qtd_avaliacoes > 300:
                            continue
                        leads.append(p)

                st.subheader(f"Resultados: {len(leads)} empresas sem site encontradas.")

                if leads:
                    for empresa in leads:
                        nome = empresa.get('displayName', {}).get('text', 'Sem nome')
                        endereco = empresa.get('formattedAddress', 'Endereço não informado')
                        telefone = empresa.get('nationalPhoneNumber', 'Não informado')
                        maps_link = empresa.get('googleMapsUri', '')
                        avaliacoes = empresa.get('userRatingCount', 0)
                        nota = empresa.get('rating', 'N/A')
                        
                        open_now = empresa.get('currentOpeningHours', {}).get('openNow')
                        status = "🟢 Aberto" if open_now is True else "🔴 Fechado" if open_now is False else "⚪ N/D"
                        
                        num_limpo = re.sub(r'\D', '', telefone) if telefone != 'Não informado' else ""
                        is_valido = len(num_limpo) == 11 and num_limpo[2] == '9'
                        whatsapp_link = f"https://wa.me/55{num_limpo}" if is_valido else "#"

                        insta_search = f"https://www.google.com/search?q=instagram+{nome.replace(' ', '+')}+{cidade.replace(' ', '+')}"

                        with st.expander(f"🏢 {nome} ({status}) - ⭐ {nota} ({avaliacoes} avaliações)", expanded=False):
                            
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.write(f"📍 **Endereço:** {endereco}")
                                st.write(f"📞 **Telefone:** {telefone} - {'✅ WhatsApp Válido' if is_valido else '❌ Inválido'}")
                            
                            with col2:
                                if is_valido:
                                    st.markdown(f"[📱 Chamar no Zap]({whatsapp_link})")
                                st.markdown(f"[📍 Maps]({maps_link}) | [📸 Insta]({insta_search})")

                            st.markdown("---")
                            tab1, tab2 = st.tabs(["💬 Abordagem", "💻 Criar Site com IA"])
                            
                            with tab1:
                                texto_abordagem = f"Oi, {nome}! Tudo bem? Sou da {nome_agencia}. \n\nVi o perfil de vocês no Google e notei que ainda não têm um site próprio. \n\nCriei um modelo de site profissional para {termo}s. Posso te mandar o link para você ver como ficaria a sua marca na internet, sem compromisso?"
                                st.text_area("Copie a mensagem:", texto_abordagem, height=150, key=f"msg_{nome}")
                            
                            # --- NOVA ÁREA DE CRIAÇÃO DE SITE COM UPLOAD DE IMAGEM ---
                            with tab2:
                                st.write("🎨 **Personalize o Site Demonstrativo**")
                                
                                col_c1, col_c2 = st.columns(2)
                                with col_c1:
                                    cor_primaria = st.color_picker("Cor Primária (Fundo)", "#FF5722", key=f"c1_{nome}")
                                with col_c2:
                                    cor_secundaria = st.color_picker("Cor do Texto", "#FFFFFF", key=f"c2_{nome}")
                                
                                # NOVO: Upload de Imagem de Referência
                                imagem_ref = st.file_uploader("📸 Suba uma foto de referência ou do produto do cliente (opcional):", type=["jpg", "jpeg", "png"], key=f"img_{nome}")
                                
                                opcoes_servico = st.multiselect(
                                    "O que a empresa oferece?",
                                    ["Delivery", "Combo", "Artesanal", "Presencial", "Agendamento", "Retirada na loja"],
                                    default=["Delivery", "Artesanal"],
                                    key=f"serv_{nome}"
                                )

                                # --- LÓGICA DINÂMICA DO MENU ---
                                if termo in ["Hamburgueria", "Pizzaria", "Restaurante", "Buffet", "Sorveteria/Açaí", "Padaria"]:
                                    menu_itens = '"Início", "Cardápio", "Eventos", "Sobre", "Contato"'
                                elif termo in ["Mecânica", "Lava Jato"]:
                                    menu_itens = '"Início", "Serviços", "Sobre", "Contato"'
                                elif termo == "Barbearia":
                                    menu_itens = '"Início", "Serviços", "Galeria", "Avaliações", "Contato"'
                                else:
                                    menu_itens = '"Início", "Serviços", "Sobre", "Contato"'

                                # Prompt turbinado com as escolhas do usuário
                                prompt_site = f"""Você é um Web Designer Sênior especialista em landing pages de alta conversão. Crie um site one-page premium para a empresa {nome} (Ramo: {termo}, Cidade: {cidade}).

DIRETRIZES DE DESIGN OBRIGATÓRIAS (Siga à risca):
- **Layout Hero:** Use um layout em duas colunas. À ESQUERDA: textos gigantes empilhados e um botão em formato de pílula. À DIREITA: uma imagem de alta qualidade do produto/serviço principal, com fundo recortado (estilo imagem flutuante ou círculo).
- **Cores:** Use a cor primária {cor_primaria} como fundo principal da seção Hero. O texto deve ser {cor_secundaria}.
- **Selo:** Crie um selo circular giratório (estilo carimbo) no canto superior direito da imagem com a frase "SABOR EM CADA DETALHE" (ou algo equivalente ao ramo).
- **Tipografia:** Títulos em fontes Grossas (Black, ex: Poppins, Montserrat). Misture cores no mesmo título (ex: palavra 1 em branco, palavra 2 em amarelo, palavra 3 em branco).

ESTRUTURA OBRIGATÓRIA DA PÁGINA:
1. NAVBAR (Topo):
   - Logo da empresa à esquerda.
   - Menu à direita com links: {menu_itens}.
   - Botão em pílula "Solicitar Orçamento" no canto direito.

2. HERO SECTION:
   - Título gigante (ex: "COMIDA QUE JUNTA PESSOAS").
   - Subtítulo persuasivo e curto.
   - DOIS BOTÕES: Um primário "Solicitar Orçamento" e um secundário "Ver no WhatsApp" (link: https://wa.me/55{num_limpo}).
   - Imagem do produto em destaque à direita.

3. NOSSOS DIFERENCIAIS / SERVIÇOS:
   - Grid com 3 ou 4 cards.
   - Destaque os serviços: {', '.join(opcoes_servico)}.
   - Cada card: Ícone, Nome do Serviço, Descrição curta e Preço.

4. SOBRE NÓS:
   - Texto contando a história da empresa. Inclua o endereço: {endereco}.

5. PROVA SOCIAL:
   - 3 depoimentos de clientes com 5 estrelas.

6. FOOTER:
   - Logo, endereço e link para o Instagram.

TECNOLOGIA: React com Tailwind CSS. Site Mobile-First. O botão de WhatsApp deve flutuar na tela em dispositivos móveis."""

                                st.success("✅ Prompt gerado com sucesso! Copie e cole no Lovable ou v0.dev.")
                                st.code(prompt_site, language="markdown")

                else:
                    st.warning("Nenhuma empresa encontrada com esses filtros.")

            except Exception as e:
                st.error(f"Erro na busca: {e}")
else:
    st.info("👈 Insira sua Google Maps API Key na barra lateral esquerda.")
