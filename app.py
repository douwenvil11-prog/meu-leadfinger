import streamlit as st
import requests
import re

st.set_page_config(page_title="LeadFinder PRO", layout="wide", page_icon="🚀")

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
st.write("Encontre empresas sem site, gere abordagens e crie prompts de design de alto nível.")

# --- LÓGICA DA CHAVE DE API (SALVA NOS SECRETS) ---
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = st.sidebar.text_input("Insira sua Google Maps API Key:", type="password")

if api_key:
    st.sidebar.markdown("### 🤖 Sua Agência")
    nome_agencia = st.sidebar.text_input("Nome da sua agência:", "Nexo Sites")
    
    st.sidebar.markdown("### 📍 Filtros de Busca")
    termo = st.sidebar.text_input("Nicho (Ex: barbearia, academia)", "barbearia")
    
    estado = st.sidebar.selectbox("Estado:", list(CIDADES_BR.keys()))
    if estado == "Outro":
        cidade = st.sidebar.text_input("Digite a cidade:", "Sua Cidade, UF")
    else:
        cidade = st.sidebar.selectbox("Cidade:", CIDADES_BR[estado])

    # Filtro para evitar empresas gigantes
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
                    # Filtra os que NÃO têm site
                    if 'websiteUri' not in p:
                        qtd_avaliacoes = p.get('userRatingCount', 0)
                        # Se o filtro estiver ativo, ignora empresas com mais de 300 avaliações
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
                        
                        # Validação WhatsApp (DDD + 9 + 8 dígitos)
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
                                texto_abordagem = f"Oi, {nome}! Tudo bem? Sou da {nome_agencia}. \n\nVi o perfil de vocês no Google (parabéns pelas avaliações!) e notei que ainda não têm um site próprio. \n\nCriei um modelo de site profissional especificamente para {termo}s. Posso te mandar o link para você ver como ficaria a sua marca na internet, sem compromisso?"
                                st.info("💡 Dica: Empresas com menos de 300 avaliações são mais fáceis de fechar contrato.")
                                st.text_area("Copie a mensagem:", texto_abordagem, height=150, key=f"msg_{nome}")
                            
                            with tab2:
                                prompt_site = f"""Você é um Web Designer Sênior de uma agência premium. Crie um site one-page de altíssimo nível para a empresa {nome} (Ramo: {termo}, Cidade: {cidade}).

DIRETRIZES DE DESIGN (Siga rigidamente):
- Estilo: Premium, moderno, imersivo e responsivo (Mobile-First).
- Tipografia: Use fontes grossas (Bold/Condensed) para os títulos principais.
- Cores: Tema escuro (Dark Mode) com cores de destaque vibrantes que combinem com o ramo de {termo}.
- Imagens: Use imagens de fundo em tela cheia (Unsplash) com um filtro escuro (overlay) para que o texto branco se destaque.

ESTRUTURA DA PÁGINA:
1. HERO SECTION (Topo):
   - Imagem de fundo impactante relacionada a {termo}.
   - Título enorme e chamativo (ex: "SEU ESTILO. NOSSO TRABALHO." ou "O MELHOR {termo.upper()} DA REGIÃO").
   - Subtítulo curto explicando o diferencial.
   - DOIS BOTÕES: Um verde grande "Chamar no WhatsApp" (link: https://wa.me/55{num_limpo}) e um secundário "Nossos Serviços".

2. BARRA DE DESTAQUES:
   - Uma faixa fina com 3 ou 4 itens (ex: "Atendimento Premium", "Profissionais Qualificados", "Nota {nota} no Google").

3. NOSSOS SERVIÇOS:
   - Grid de 3 ou 4 cards com fundo escuro e bordas sutis.
   - Cada card deve ter: Um ícone, Nome do Serviço, Descrição curta e Preço estimado.

4. SOBRE NÓS:
   - Layout dividido (texto de um lado, imagem do outro).
   - Texto focado em confiança e qualidade. Inclua o endereço: {endereco}.

5. DEPOIMENTOS (Prova Social):
   - 3 cards de depoimentos de clientes (invente nomes e textos realistas, destacando o atendimento e a qualidade).

6. FOOTER (Rodapé):
   - Informações de contato, endereço, e um mapa do Google embutido.
   - Link para o Instagram (use um placeholder).

TECNOLOGIA: Use React com Tailwind CSS. Garanta que o botão de WhatsApp esteja flutuante no canto inferior direito em dispositivos móveis."""

                                st.success("✅ Prompt atualizado com as melhores práticas de design.")
                                st.code(prompt_site, language="markdown")

                else:
                    st.warning("Nenhuma empresa encontrada com esses filtros. Tente desmarcar o filtro de tamanho ou mudar a cidade.")

            except Exception as e:
                st.error(f"Erro na busca: {e}")
else:
    st.info("👈 Insira sua Google Maps API Key na barra lateral esquerda.")
