import streamlit as st
import googlemaps
import pandas as pd

# Configuração da página (igual ao layout do seu print)
st.set_page_config(page_title="LeadFinder Brasil", layout="wide")
st.title("🔍 LeadFinder - Empresas sem Site no Brasil")

# Campo para colocar a chave da API do Google
api_key = st.sidebar.text_input("Insira sua Google Maps API Key:", type="password")

if api_key:
    gmaps = googlemaps.Client(key=api_key)

    # Campos de busca
    st.sidebar.markdown("### Filtros de Busca")
    termo = st.sidebar.text_input("O que você procura? (Ex: barbearia)", "barbearia")
    local = st.sidebar.text_input("Onde? (Ex: São Paulo, SP)", "São Paulo, SP")
    
    if st.sidebar.button("Pesquisar Empresas"):
        with st.spinner('Buscando empresas no Google Maps...'):
            try:
                # Faz a busca no Google Places
                resultados = gmaps.places(query=f"{termo} em {local}")
                
                leads = []
                
                # Filtra apenas as empresas que NÃO têm site
                for empresa in resultados.get('results', []):
                    nome = empresa.get('name')
                    endereco = empresa.get('formatted_address')
                    telefone = empresa.get('formatted_phone_number', 'Não informado')
                    tem_site = 'website' in empresa
                    
                    # O pulo do gato: só adiciona na lista se NÃO tiver site
                    if not tem_site:
                        leads.append({
                            "Nome da Empresa": nome,
                            "Endereço": endereco,
                            "Telefone": telefone,
                            "Possui Site?": "❌ Não"
                        })
                
                # Exibe os resultados na tela igual ao seu print
                st.subheader(f"Resultados da busca: {termo} em {local}")
                st.write(f"**{len(leads)} empresas encontradas sem site.**")
                
                if leads:
                    df = pd.DataFrame(leads)
                    st.dataframe(df, use_container_width=True)
                    
                    # Botão para baixar os leads
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
