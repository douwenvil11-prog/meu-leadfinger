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
    termo = st.sidebar.text_input("Qual o nicho? (Ex: pizzaria, lava jato)", "lava jato")
    
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
                        
                        # Preparação dos Links
                        num_limpo = re.sub(r'\D', '', telefone) if telefone != 'Não informado' else ""
                        whatsapp_link = f"https://wa.me/{num_limpo}" if num_limpo else "#"
                        insta_search = f"https://www.google.com/search?q=instagram+{nome.replace(' ', '+')}+{cidade.replace(' ', '+')}"

                        # --- CARD DA EMPRESA ---
                        with st.expander(f"🏢 {nome} ({status})", expanded=False):
                            
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.write(f"📍 **Endereço:** {endereco}")
                                st.write(f"📞 **Telefone:** {telefone}")
                                st.write(f"🏷️ **Nicho:** {termo.title()}")
                            
                            with col2:
                                st.write("**Ações Rápidas:**")
                                st.markdown(f"[📱 Chamar no Zap]({whatsapp_link}) | [📍 Maps]({maps_link}) | [📸 Insta]({insta_search})")

                            st.markdown("---")
                            
                            tab1, tab2 = st.tabs(["💬 Mensagem de Abordagem", "💻 Criar Site com IA"])
                            
                            # ABA 1: ABORDAGEM PROFISSIONAL
                            with tab1:
                                texto_abordagem = f"Oi, {nome}! Tudo bem? Sou da {nome_agencia}. \n\nProcurei por {termo} em {cidade} no Google e encontrei vocês, mas notei que a empresa ainda não tem um site próprio. \n\nTenho uma ideia rápida de como um site simples pode trazer mais clientes direto para o WhatsApp de vocês. Posso te mostrar como ficaria sem compromisso?"
                                
                                st.info("💡 Abordagem curta e consultiva. Ideal para WhatsApp ou Instagram Direct.")
                                st.text_area("Copie a mensagem abaixo:", texto_abordagem, height=160, key=f"msg_{nome}")
                            
                            # ABA 2: PROMPT PARA CRIAR SITE
                            with tab2:
                                prompt_site = f"""Crie um site de uma página (one-page) para a empresa {nome}.
O objetivo é um só: fazer com que quem pesquisa {termo} na região de {cidade} entenda em segundos o que a empresa oferece e chame no WhatsApp ou vá até lá.

Aqui estão os dados da empresa:
- Nome: {nome}
- Ramo: {termo}
- Endereço: {endereco}
- Telefone/WhatsApp: {telefone}

O site deve ter:
1. Visual moderno, confiável e responsivo (Mobile First).
2. Uma seção Hero com o nome da empresa e um botão verde bem grande "Chamar no WhatsApp" (link: https://wa.me/{num_limpo}).
3. Seção de Serviços prestados (invente serviços comuns para {termo}).
4. Seção de depoimentos (invente 3 depoimentos positivos).
5. Rodapé com o endereço e link do mapa.
Use React com Tailwind CSS e cores que combinem com o ramo de {termo}."""
                                
                                st.info("💡 Copie o texto abaixo e cole no Lovable (lovable.dev) ou v0.dev para gerar o site.")
                                st.code(prompt_site, language="markdown")

                else:
                    st.warning("Nenhuma empresa sem site encontrada nessa busca. Tente outro nicho ou cidade.")

            except Exception as e:
                st.error(f"Erro na busca: Verifique sua API Key. Detalhes: {e}")
else:
    st.info("👈 Insira sua Google Maps API Key na barra lateral esquerda para começar.")
