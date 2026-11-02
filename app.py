import streamlit as st
import requests
import re

st.set_page_config(page_title="LeadFinder PRO", layout="wide", page_icon="🚀")

# --- LISTA DE ESTADOS E CIDADES ---
CIDADES_BR = {
    "São Paulo": ["São Paulo", "Campinas", "Santos", "Ribeirão Preto"],
    "Rio de Janeiro": ["Rio de Janeiro", "Niterói", "Nova Iguaçu", "Campos dos Goytacazes"],
    "Minas Gerais": ["Belo Horizonte", "Uberlândia", "Contagem", "Juiz de Fora"],
    "Piauí": ["Teresina", "Parnaíba", "Picos", "Timon"],
    "Maranhão": ["São Luís", "Imperatriz", "Timon", "Caxias"],
    "Bahia": ["Salvador", "Feira de Santana", "Vitória da Conquista", "Camaçari"],
    "Paraná": ["Curitiba", "Londrina", "Maringá", "Ponta Grossa"],
    "Ceará": ["Fortaleza", "Caucaia", "Juazeiro do Norte", "Sobral"],
    "Goiás": ["Goiânia", "Aparecida de Goiânia", "Anápolis"],
    "Outro": ["Digitar manualmente"]
}

st.title("🚀 LeadFinder PRO - Prospecção Inteligente")
st.write("Encontre empresas sem site, gere abordagens perfeitas e crie sites com Inteligência Artificial.")

# --- BARRA LATERAL ---
api_key = st.sidebar.text_input("Insira sua Google Maps API Key:", type="password")

if api_key:
    st.sidebar.markdown("### 🤖 Sua Agência")
    nome_agencia = st.sidebar.text_input("Nome da sua agência/nome:", "Minha Agência Digital")
    
    st.sidebar.markdown("### 📍 Filtros de Busca")
    termo = st.sidebar.text_input("Qual o nicho? (Ex: pizzaria, lava jato, barbearia)", "barbearia")
    
    estado = st.sidebar.selectbox("Selecione o Estado:", list(CIDADES_BR.keys()))
    
    if estado == "Outro":
        cidade = st.sidebar.text_input("Digite a cidade e o estado:", "Sua Cidade, UF")
    else:
        cidade = st.sidebar.selectbox("Selecione a Cidade:", CIDADES_BR[estado])

    # --- BOTÃO DE PESQUISA ---
    if st.sidebar.button("Pesquisar Empresas", type="primary", use_container_width=True):
        with st.spinner('Buscando empresas no Google Maps...'):
            try:
                url = "https://places.googleapis.com/v1/places:searchText"
                headers = {
                    'Content-Type': 'application/json',
                    'X-Goog-Api-Key': api_key,
                    'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri,places.currentOpeningHours.openNow'
                }
                payload = {"textQuery": f"{termo} em {cidade}, {estado}", "maxResultCount": 20}

                response = requests.post(url, json=payload, headers=headers)
                data = response.json()
                places = data.get('places', [])
                
                # Filtra apenas os que NÃO têm site
                leads = [p for p in places if 'websiteUri' not in p]

                st.subheader(f"Resultados: {len(leads)} empresas sem site em {cidade}")

                if leads:
                    for empresa in leads:
                        nome = empresa.get('displayName', {}).get('text', 'Sem nome')
                        endereco = empresa.get('formattedAddress', 'Endereço não informado')
                        telefone = empresa.get('nationalPhoneNumber', 'Não informado')
                        maps_link = empresa.get('googleMapsUri', '')
                        
                        # Status Aberto/Fechado
                        open_now = empresa.get('currentOpeningHours', {}).get('openNow')
                        status = "🟢 Aberto agora" if open_now is True else "🔴 Fechado agora" if open_now is False else "⚪ Status N/D"
                        
                        # --- NOVA LÓGICA DE VALIDAÇÃO DE WHATSAPP ---
                        # Remove tudo que não for número
                        num_limpo = re.sub(r'\D', '', telefone) if telefone != 'Não informado' else ""
                        
                        # Valida se é um celular brasileiro (DDD + 9 + 8 dígitos = 11 dígitos)
                        # Isso evita links de WhatsApp para telefones fixos (que começam com 2, 3, 4)
                        if len(num_limpo) == 11 and num_limpo[2] == '9':
                            whatsapp_link = f"https://wa.me/55{num_limpo}"
                            whatsapp_status = "✅ Válido"
                        else:
                            whatsapp_link = "#"
                            whatsapp_status = "❌ Inválido/Fixo"

                        insta_search = f"https://www.google.com/search?q=instagram+{nome.replace(' ', '+')}+{cidade.replace(' ', '+')}"

                        # --- CARD DA EMPRESA ---
                        with st.expander(f"🏢 {nome} ({status})", expanded=False):
                            
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.write(f"📍 **Endereço:** {endereco}")
                                st.write(f"📞 **Telefone:** {telefone}")
                                st.write(f"🏷️ **Nicho:** {termo.title()}")
                                st.write(f"📱 **Status do WhatsApp:** {whatsapp_status}")
                            
                            with col2:
                                st.write("**Ações Rápidas:**")
                                # Se o WhatsApp for inválido, o link não aparece
                                if whatsapp_link != "#":
                                    st.markdown(f"[📱 Chamar no Zap]({whatsapp_link})")
                                else:
                                    st.markdown("_WhatsApp indisponível_")
                                st.markdown(f"[📍 Maps]({maps_link}) | [📸 Insta]({insta_search})")

                            st.markdown("---")
                            
                            tab1, tab2 = st.tabs(["💬 Mensagem de Abordagem", "💻 Criar Site com IA"])
                            
                            # ABA 1: ABORDAGEM PROFISSIONAL
                            with tab1:
                                texto_abordagem = f"Oi, {nome}! Tudo bem? Sou da {nome_agencia}. \n\nProcurei por {termo} em {cidade} no Google e encontrei vocês, mas notei que a empresa ainda não tem um site próprio. \n\nTenho uma ideia rápida de como um site simples pode trazer mais clientes direto para o WhatsApp de vocês. Posso te mostrar como ficaria sem compromisso?"
                                
                                st.info("💡 Abordagem curta e consultiva. Ideal para WhatsApp ou Instagram Direct.")
                                st.text_area("Copie a mensagem abaixo:", texto_abordagem, height=160, key=f"msg_{nome}")
                            
                            # ABA 2: PROMPT PARA CRIAR SITE (NÍVEL PROFISSIONAL)
                            with tab2:
                                # Prompt reescrito seguindo as melhores práticas do Lovable
                                prompt_site = f"""
**Objetivo:** Crie um site one-page de alta conversão para a empresa **{nome}**, do ramo de **{termo}**, localizada em **{cidade}**.

**Público-alvo:** Clientes locais que buscam serviços de {termo} e valorizam qualidade, confiança e praticidade.

**Estilo Visual (Premium e Sleek):**
- **Paleta de Cores:** [Escolha uma paleta que combine com o ramo, ex: tons escuros e dourados para barbearia, ou cores quentes e vibrantes para pizzaria].
- **Tipografia:** Use uma fonte moderna e elegante (ex: "Inter" ou "Outfit").
- **Layout:** Estrutura de página única com seções bem definidas, espaçamento generoso (whitespace) e imagens de alta qualidade (use placeholders de imagens que representem o serviço).
- **Tom de Voz:** Profissional, acolhedor e persuasivo, como se fosse o próprio dono falando.

**Estrutura da Página (One-Page):**
1.  **Hero Section:** Título de impacto com a promessa principal (ex: "Seu estilo, nossa paixão"). Subtítulo com uma frase de apoio. Botão CTA verde e grande: **"Agendar Horário no WhatsApp"** (link: https://wa.me/55{num_limpo}).
2.  **Sobre Nós:** Um parágrafo curto contando a história da empresa e o que a torna especial.
3.  **Nossos Serviços:** Uma grade (grid) com 3 a 4 serviços principais. Cada serviço deve ter: Ícone, Nome do Serviço, Breve descrição, **Preço** e **Duração** (ex: "Corte Masculino - R$ 50 - 40 min").
4.  **Depoimentos:** Uma seção com 3 depoimentos de clientes reais (invente nomes e textos realistas que falem sobre a qualidade do atendimento).
5.  **Localização e Contato:** Endereço completo ({endereco}), link para o Google Maps e um botão de WhatsApp.
6.  **Rodapé:** Informações de copyright e links para redes sociais (use placeholders).

**Instruções Técnicas:**
- Use React com Tailwind CSS.
- O site deve ser **Mobile-First** (perfeito para celular).
- Garanta que todos os botões de CTA levem diretamente para o link do WhatsApp fornecido.
"""
                                
                                st.info("💡 Prompt profissional. Copie o texto abaixo e cole no Lovable (lovable.dev) ou v0.dev.")
                                st.code(prompt_site, language="markdown")

                else:
                    st.warning("Nenhuma empresa sem site encontrada nessa busca. Tente outro nicho ou cidade.")

            except Exception as e:
                st.error(f"Erro na busca: Verifique sua API Key. Detalhes: {e}")
else:
    st.info("👈 Insira sua Google Maps API Key na barra lateral esquerda para começar.")
