import streamlit as st
import requests
import re

st.set_page_config(page_title="LeadFinder PRO", layout="wide", page_icon="🚀")

# --- LISTA DE NICHOS (Para não digitar) ---
NICHOS = [
    "Hamburgueria", "Pizzaria", "Barbearia", "Sorveteria/Açaí", 
    "Restaurante", "Mecânica", "Lava Jato", "Pet Shop", 
    "Clínica/Consultório", "Academia", "Padaria", "Outro"
]

# --- LISTA DE ESTADOS E CIDADES ---
CIDADES_BR = {
    "São Paulo": ["São Paulo", "Campinas", "Santos", "Ribeirão Preto"],
    "Rio de Janeiro": ["Rio de Janeiro", "Niterói", "Nova Iguaçu"],
    "Minas Gerais": ["Belo Horizonte", "Uberlândia", "Contagem"],
    "Piauí": ["Teresina", "Parnaíba", "Picos", "Timon"],
    "Maranhão": ["São Luís", "Imperatriz", "Timon", "Caxias"],
    "Bahia": ["Salvador", "Feira de Santana", "Vitória da Conquista"],
    "Paraná": ["Curitiba", "Londrina", "Maringá"],
    "Ceará": ["Fortaleza", "Caucaia", "Juazeiro do Norte"],
    "Goiás": ["Goiânia", "Aparecida de Goiânia", "Anápolis"],
    "Outro": ["Digitar manualmente"]
}

st.title("🚀 LeadFinder PRO - Prospecção Premium")
st.write("Encontre empresas sem site e gere prompts com design de alto padrão.")

# --- LÓGICA DA CHAVE DE API (SALVA NOS SECRETS) ---
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = st.sidebar.text_input("Insira sua Google Maps API Key:", type="password")

if api_key:
    st.sidebar.markdown("### 🤖 Sua Agência")
    nome_agencia = st.sidebar.text_input("Nome da sua agência:", "Nexo Sites")
    
    st.sidebar.markdown("### 📍 Filtros de Busca")
    
    nicho_selecionado = st.sidebar.selectbox("Qual o nicho?", NICHOS)
    if nicho_selecionado == "Outro":
        termo = st.sidebar.text_input("Digite o nicho:", "seu nicho aqui")
    else:
        termo = nicho_selecionado
    
    estado = st.sidebar.selectbox("Estado:", list(CIDADES_BR.keys()))
    if estado == "Outro":
        cidade = st.sidebar.text_input("Digite a cidade:", "Sua Cidade, UF")
    else:
        cidade = st.sidebar.selectbox("Cidade:", CIDADES_BR[estado])

    filtro_tamanho = st.sidebar.checkbox("Filtrar empresas médias/pequenas (< 300 avaliações)", value=True)

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
                                st.write(f"📞 **Telefone:** {telefone} - {'✅ WhatsApp Válido' if is_valido else '❌ Inválido/Fixo'}")
                                st.write(f"📊 **Google:** Nota {nota} com {avaliacoes} avaliações.")
                            
                            with col2:
                                if is_valido:
                                    st.markdown(f"[📱 Chamar no Zap]({whatsapp_link})")
                                st.markdown(f"[📍 Maps]({maps_link}) | [📸 Insta]({insta_search})")

                            st.markdown("---")
                            tab1, tab2 = st.tabs(["💬 Abordagem", "💻 Prompt do Site (Premium)"])
                            
                            with tab1:
                                texto_abordagem = f"Oi, {nome}! Tudo bem? Sou da {nome_agencia}. \n\nVi o perfil de vocês no Google e notei que ainda não têm um site próprio. \n\nCriei um modelo de site profissional para {termo}s. Posso te mandar o link para você ver como ficaria a sua marca na internet, sem compromisso?"
                                st.info("💡 Foco em empresas com menos de 300 avaliações.")
                                st.text_area("Copie a mensagem:", texto_abordagem, height=150, key=f"msg_{nome}")
                            
                            # --- PROMPT ATUALIZADO COM DESIGN DINÂMICO ---
                            with tab2:
                                prompt_site = f"""Você é um Web Designer Sênior especialista em landing pages de alta conversão. Crie um site one-page premium e extremamente bonito para a empresa {nome} (Ramo: {termo}, Cidade: {cidade}).

DIRETRIZES DE DESIGN (SIGA RIGIDAMENTE):
- **Estilo e Cores:** NÃO force um tema escuro. Analise o ramo "{termo}" e crie uma identidade visual que transmita a essência da empresa. (Ex: Padaria = cores quentes/aconchegantes; Clínica = tons claros/azulados e limpos; Hamburgueria = cores vibrantes ou estilo rústico/escuro; Pet Shop = cores alegres).
- **Tipografia:** Títulos em fontes Grossas (Bold/Black) para passar imponência. Corpo do texto em fonte legível (ex: Inter, Poppins).
- **Imagens:** Use imagens de fundo em tela cheia de alta qualidade (Unsplash) relacionadas ao nicho. Aplique um gradiente leve ou overlay para garantir que o texto seja perfeitamente legível.

ESTRUTURA OBRIGATÓRIA DA PÁGINA (Inspirada em sites premium):
1. NAVBAR (Topo):
   - Logo da empresa à esquerda.
   - Menu à direita com links: "Início", "Cardápio" (ou Serviços), "Sobre", "Contato".
   - Botão pequeno e destacado de "Pedir no WhatsApp" no canto direito.

2. HERO SECTION (Topo da página):
   - Imagem de fundo imersiva de alta qualidade.
   - Badge/Etiqueta pequena (ex: "Qualidade Premium").
   - Título gigante com duas cores que combinem com a paleta escolhida (ex: "SABOR QUE <span style='color:[cor_destaque]'>MARCA.</span>").
   - Subtítulo curto e persuasivo.
   - DOIS BOTÕES lado a lado: Um primário colorido "CONHECER" e um secundário verde "Pedir no WhatsApp" (link: https://wa.me/55{num_limpo}).

3. DESTAQUES / SERVIÇOS:
   - Grid com 3 ou 4 cards (fundo levemente sombreado ou com bordas elegantes).
   - Cada card: Ícone, Nome do Serviço/Produto, Descrição curta e Preço.
   - *Dica para {termo}: Se for comida, invente nomes de pratos suculentos. Se for serviço, invente pacotes.*

4. SOBRE NÓS:
   - Layout moderno. Texto contando a história da empresa. Inclua o endereço: {endereco}.

5. PROVA SOCIAL (Depoimentos):
   - 3 depoimentos de clientes reais com 5 estrelas.

6. FOOTER (Rodapé):
   - Logo, endereço, copyright e link para o Instagram.

TECNOLOGIA: React com Tailwind CSS. Site Mobile-First. O botão de WhatsApp deve flutuar na tela em dispositivos móveis."""
                                
                                st.success("✅ Prompt atualizado! Ele agora escolhe o melhor design para cada nicho.")
                                st.code(prompt_site, language="markdown")

                else:
                    st.warning("Nenhuma empresa encontrada com esses filtros.")

            except Exception as e:
                st.error(f"Erro na busca: {e}")
else:
    st.info("👈 Insira sua Google Maps API Key na barra lateral esquerda.")
