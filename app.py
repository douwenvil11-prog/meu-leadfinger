import streamlit as st
import requests
import pandas as pd

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
                    'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri'
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

                    if not tem_site:
                        leads.append({
                            "Nome da Empresa": nome,
                            "Endereço": endereco,
                            "Telefone": telefone,
                            "Possui Site?": "❌ Não"
                        })

                st.subheader(f"Resultados da busca: {termo} em {local}")
                st.write(f"**{len(leads)} empresas encontradas sem site.**")

                if leads:
                    df = pd.DataFrame(leads)
                    st.dataframe(df, use_container_width=True)

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
                st.error(f"Erro na busca: {e}")
else:
    st.info("👈 Por favor, insira sua Google Maps API Key na barra lateral esquerda para começar.")
