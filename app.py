import streamlit as st
import requests
import pandas as pd
import re

st.set_page_config(page_title="LeadFinder Brasil", layout="wide")
st.title("🔍 LeadFinder - Empresas sem Site no Brasil")

api_key = st.sidebar.text_input("Insira sua Google Maps API Key:", type="password")

if api_key:
    st.sidebar.markdown("### Filtros de Busca")
    termo = st.sidebar.text_input("O que você procura? (Ex: pizzaria, barbearia)", "barbearia")
    local = st.sidebar.text_input("Onde? (Ex: São Paulo, SP)", "São Paulo, SP")

    if st.sidebar.button("Pesquisar Empresas"):
        with st.spinner('Buscando empresas no Google Maps...'):
            try:
                url = "https://places.googleapis.com/v1/places:searchText"
                headers = {
                    'Content-Type': 'application/json',
                    'X-Goog-Api-Key': api_key,
                    'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri,places.currentOpeningHours.openNow'
                }
                payload = {
                    "textQuery": f"{termo} em {local}",
                    "maxResultCount": 20
                }

                response = requests.post(url, json=payload, headers=headers)
                data = response.json()

                leads = []
                places = data.get('places', [])

                for empresa in places:
                    nome = empresa.get('displayName', {}).get('text', 'Sem nome')
                    endereco = empresa.get('formattedAddress', 'Endereço não informado')
                    telefone = empresa.get('nationalPhoneNumber', 'Não informado')
                    tem_site = 'websiteUri' in empresa
                    
                    maps_link = empresa.get('googleMapsUri', '')
                    
                    open_now = empresa.get('currentOpeningHours', {}).get('openNow')
                    if open_now is True:
                        status = "🟢 Aberto"
                    elif open_now is False:
                        status = "🔴 Fechado"
                    else:
                        status = "⚪ N/D"

                    # Cria o link do WhatsApp
                    if telefone != 'Não informado':
                        num_limpo = re.sub(r'\D', '', telefone)
                        whatsapp_link = f"https://wa.me/{num_limpo}"
                    else:
                        whatsapp_link = ""

                    # Cria link de busca no Google para achar o Instagram
                    insta_search = f"https://www.google.com/search?q=instagram+{nome.replace(' ', '+')}+{local.replace(' ', '+')}"

                    if not tem_site:
                        leads.append({
                            "Nome": nome,
                            "Status": status,
                            "Telefone": telefone,
                            "WhatsApp": whatsapp_link,
                            "Buscar Insta": insta_search,
                            "Maps": maps_link,
                            "Endereço": endereco
                        })

                st.subheader(f"Resultados: {len(leads)} empresas sem site encontradas.")
                
                if leads:
                    df = pd.DataFrame(leads)
                    
                    # Tabela formatada
                    st.dataframe(
                        df,
                        use_container_width=True,
                        column_config={
                            "WhatsApp": st.column_config.LinkColumn("WhatsApp", display_text="Chamar no Zap"),
                            "Buscar Insta": st.column_config.LinkColumn("Instagram", display_text="Achar Insta"),
                            "Maps": st.column_config.LinkColumn("Maps", display_text="Ver no Maps")
                        }
                    )

                    # --- ÁREA DE ABORDAGEM (TEMPLATES) ---
                    st.markdown("---")
                    st.subheader("🎯 Gerador de Abordagem Rápida")
                    st.write("Selecione o nicho da empresa para gerar a mensagem perfeita para copiar e colar no WhatsApp/Instagram:")
                    
                    nicho = st.selectbox(
                        "Qual o nicho dessas empresas?", 
                        ["Genérico", "Barbearia", "Pizzaria", "Açaí/Sorveteria", "Restaurante", "Pet Shop", "Clínica/Consultório"]
                    )
                    
                    nome_exemplo = leads[0]['Nome'] if leads else "[Nome da Empresa]"

                    if nicho == "Pizzaria":
                        texto = f"Olá, tudo bem? Falo com o responsável pela {nome_exemplo}? \nVi que a pizzaria de vocês tem ótimas avaliações no Google, mas notei que vocês ainda não têm um site para pedidos online. \nHoje, a maioria dos clientes busca o cardápio no celular antes de pedir. Eu crio sites rápidos e bonitos para pizzarias, com botão direto pro WhatsApp. Posso te mostrar um exemplo sem compromisso?"
                    elif nicho == "Açaí/Sorveteria":
                        texto = f"Oi, tudo bom? Sou eu quem fala com a {nome_exemplo}? \nEstava procurando a loja de vocês no Google e vi que não tem um site oficial. \nCom um site simples, dá pra colocar o cardápio completo, fotos das delícias de vocês e um botão de pedido no WhatsApp, o que ajuda a vender muito mais. Posso te mostrar como fica?"
                    elif nicho == "Barbearia":
                        texto = f"E aí, beleza? Falo com o dono da {nome_exemplo}? \nVi que a barbearia de vocês tem nota top no Google! Só senti falta de um site para agendamento. \nHoje em dia o cliente gosta de ver os cortes e já marcar o horário direto pelo celular. Eu desenvolvo sites para barbearias com essa função. Topa ver um exemplo?"
                    elif nicho == "Restaurante":
                        texto = f"Olá, boa tarde! Falo com a gerência do {nome_exemplo}? \nEncontrei o restaurante de vocês no Google, mas vi que o cardápio não está disponível em um site próprio. \nCrio sites para restaurantes onde o cliente vê o menu atualizado e já faz a reserva ou pede no WhatsApp. Faria sentido para vocês?"
                    elif nicho == "Pet Shop":
                        texto = f"Olá, tudo bem? Falo com o responsável pelo {nome_exemplo}? \nEncontrei vocês no Google Maps e vi que são muito bem avaliados. \nPercebi que não têm um site para mostrar os serviços (banho, tosa, ração). Um site ajuda a passar mais confiança e a fechar mais agendamentos. Posso te mandar um modelo?"
                    elif nicho == "Clínica/Consultório":
                        texto = f"Olá, boa tarde. Falo com o(a) administrador(a) do {nome_exemplo}? \nEstava buscando opções na região e vi que vocês têm ótimas avaliações, mas não encontrei um site oficial. \nPara clínicas, um site passa muita credibilidade para novos pacientes. Desenvolvo páginas profissionais com agendamento facilitado. Posso apresentar uma proposta?"
                    else:
                        texto = f"Olá, tudo bem? Falo com o responsável pela {nome_exemplo}? \nEncontrei a empresa de vocês no Google Maps e vi que ainda não possuem um site. \nHoje, ter um site passa muita credibilidade e ajuda a captar mais clientes todos os dias. Eu crio sites profissionais e rápidos. Posso te mostrar como ficaria para o seu negócio, sem compromisso?"

                    # O st.code cria um bloco com um botão de "Copiar" no canto
                    st.code(texto, language="text")
                    
                    # --- FIM DA ÁREA DE ABORDAGEM ---
                    
                    # Botão de download (opcional agora, já que pode copiar da tabela)
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Baixar Planilha Completa (CSV)",
                        data=csv,
                        file_name='leads_sem_site.csv',
                        mime='text/csv',
                    )
                else:
                    st.warning("Nenhuma empresa sem site encontrada nessa busca.")

            except Exception as e:
                st.error(f"Erro na busca: Verifique sua API Key. Detalhes: {e}")
else:
    st.info("👈 Insira sua Google Maps API Key na barra lateral esquerda.")
