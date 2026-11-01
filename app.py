import streamlit as st
import requests
import pandas as pd
import re

st.set_page_config(page_title="LeadFinder Brasil", layout="wide")
st.title("🔍 LeadFinder - Empresas sem Site no Brasil")

api_key = st.sidebar.text_input("Insira sua Google Maps API Key:", type="password")

if api_key:
    st.sidebar.markdown("### Filtros de Busca")
    termo = st.sidebar.text_input("O que você procura? (Ex: barbearia)", "barbearia")
    local = st.sidebar.text_input("Onde? (Ex: São Paulo, SP)", "São Paulo, SP")

    if st.sidebar.button("Pesquisar Empresas"):
        with st.spinner('Buscando empresas no Google Maps...'):
            try:
                url = "https://places.googleapis.com/v1/places:searchText"
                headers = {
                    'Content-Type': 'application/json',
                    'X-Goog-Api-Key': api_key,
                    # Adicionamos googleMapsUri e currentOpeningHours aqui
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
                    
                    # Pega o link do Maps
                    maps_link = empresa.get('googleMapsUri', '')
                    
                    # Verifica se está aberto agora
                    open_now = empresa.get('currentOpeningHours', {}).get('openNow')
                    if open_now is True:
                        status = "🟢 Aberto agora"
                    elif open_now is False:
                        status = "🔴 Fechado agora"
                    else:
                        status = "⚪ Sem informação"

                    # Cria o link do WhatsApp (limpando o telefone para só números)
                    if telefone != 'Não informado':
                        num_limpo = re.sub(r'\D', '', telefone)
                        whatsapp_link = f"https://wa.me/{num_limpo}"
                    else:
                        whatsapp_link = ""

                    # Só adiciona se NÃO tiver site
                    if not tem_site:
                        leads.append({
                            "Nome": nome,
                            "Status": status,
                            "Telefone": telefone,
                            "WhatsApp": whatsapp_link,
                            "Google Maps": maps_link,
                            "Endereço": endereco
                        })

                st.subheader(f"Resultados da busca: {termo} em {local}")
                st.write(f"**{len(leads)} empresas encontradas sem site.**")

                if leads:
                    df = pd.DataFrame(leads)
                    
                    # Configurando as colunas para ficarem bonitas e clicáveis
                    st.dataframe(
                        df,
                        use_container_width=True,
                        column_config={
                            "WhatsApp": st.column_config.LinkColumn(
                                "WhatsApp",
                                display_text="Chamar no Zap"
                            ),
                            "Google Maps": st.column_config.LinkColumn(
                                "Maps",
                                display_text="Ver no Maps"
                            )
                        }
                    )

                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Baixar Leads em CSV",
                        data=csv,
                        file_name='leads_sem_site.csv',
                        mime='text/csv',
                    )
                else:
                    st.warning("Nenhuma empresa sem site encontrada nessa busca.")

            except Exception as e:
                st.error(f"Erro na busca: Verifique sua API Key. Detalhes: {e}")
else:
    st.info("👈 Por favor, insira sua Google Maps API Key na barra lateral esquerda para começar.")
