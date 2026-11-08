
import streamlit as st
import requests
import urllib.parse
import re
import csv
import io

# ==========================================
# CONFIGURAÇÃO
# ==========================================

st.set_page_config(
    page_title="Douwen Prospector",
    page_icon="🔥",
    layout="centered"
)

st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 760px;
    }
    div.stButton > button,
    div.stLinkButton > a {
        min-height: 45px;
        border-radius: 12px;
        font-weight: 600;
        width: 100%;
    }
    div[data-testid="stExpander"] {
        border-radius: 12px;
        border: 1px solid rgba(128,128,128,.25);
    }
</style>
""", unsafe_allow_html=True)

st.title("🔥 Douwen Prospector")
st.caption("Encontre empresas e descubra novas oportunidades de venda.")

# ==========================================
# API GEOAPIFY
# ==========================================

try:
    API_KEY = st.secrets["GEOAPIFY_KEY"]
except Exception:
    st.error("Chave GEOAPIFY_KEY não encontrada nos Secrets.")
    st.stop()

# ==========================================
# NICHOS E PAÍSES
# ==========================================

mapa_nichos = {
    "Barbearia": "service.beauty",
    "Salão de Beleza": "service.beauty",
    "Restaurante": "catering.restaurant",
    "Hamburgueria / Lanches": "catering.fast_food",
    "Pet Shop": "commercial.pet",
    "Clínica de Estética": "service.beauty",
    "Academia": "sport.fitness",
    "Padaria": "commercial.food.bakery",
    "Oficina Mecânica": "service.vehicle.repair",
}

paises = {
    "Brasil": "55",
    "Portugal": "351",
    "Estados Unidos": "1",
    "Espanha": "34",
    "México": "52"
}

# ==========================================
# ANÁLISE DE TELEFONES
# ==========================================

def analisar_telefone(telefone, pais):

    if not telefone:
        return None, "Sem telefone"

    numero = re.sub(r"\D", "", str(telefone))

    if not numero:
        return None, "Número inválido"

    if pais == "Brasil":

        if numero.startswith("55") and len(numero) == 13:
            numero = numero[2:]

        if len(numero) == 11 and numero[2] == "9":
            return "55" + numero, "Celular provável"

        if len(numero) == 10:
            return None, "Possível telefone fixo"

        if len(numero) == 11:
            return None, "Número fora do padrão de celular"

        return None, "Número inválido"

    codigo = paises[pais]

    if numero.startswith(codigo):
        internacional = numero
    else:
        internacional = codigo + numero.lstrip("0")

    if len(internacional) > len(codigo) + 5:
        return internacional, "Não verificado"

    return None, "Número inválido"


def obter_telefone(props):

    contato = props.get("contact", {})

    if not isinstance(contato, dict):
        contato = {}

    return (
        contato.get("phone")
        or props.get("phone")
        or props.get("contact:phone")
        or ""
    )


def possui_site(props):

    contato = props.get("contact", {})

    if not isinstance(contato, dict):
        contato = {}

    return bool(
        props.get("website")
        or props.get("contact:website")
        or contato.get("website")
    )


# ==========================================
# BUSCA GEOAPIFY
# ==========================================

@st.cache_data(ttl=1800)
def buscar_empresas(cidade, pais, categoria, api_key):

    try:

        local = f"{cidade}, {pais}"

        resposta_geo = requests.get(
            "https://api.geoapify.com/v1/geocode/search",
            params={
                "text": local,
                "type": "city",
                "format": "json",
                "limit": 1,
                "apiKey": api_key
            },
            timeout=15
        )

        resposta_geo.raise_for_status()

        resultados_geo = resposta_geo.json().get("results", [])

        if not resultados_geo:
            return None, "Cidade não encontrada."

        place_id = resultados_geo[0].get("place_id")

        resposta = requests.get(
            "https://api.geoapify.com/v2/places",
            params={
                "categories": categoria,
                "filter": f"place:{place_id}",
                "limit": 50,
                "apiKey": api_key
            },
            timeout=20
        )

        resposta.raise_for_status()

        dados = resposta.json()

        empresas = []

        for item in dados.get("features", []):

            props = item.get("properties", {})

            if possui_site(props):
                continue

            nome = props.get("name")

            if not nome:
                continue

            empresas.append(props)

        return empresas, None

    except requests.exceptions.Timeout:
        return None, "A busca demorou demais. Tente novamente."

    except requests.exceptions.RequestException:
        return None, "Erro ao conectar com a Geoapify. Verifique sua internet ou API."

    except Exception:
        return None, "Ocorreu um erro inesperado durante a busca."


# ==========================================
# SESSÃO
# ==========================================

if "empresas" not in st.session_state:
    st.session_state.empresas = []

if "cidade_busca" not in st.session_state:
    st.session_state.cidade_busca = ""

if "pais_busca" not in st.session_state:
    st.session_state.pais_busca = "Brasil"

if "link_previa" not in st.session_state:
    st.session_state.link_previa = ""

if "verificados" not in st.session_state:
    st.session_state.verificados = set()


# ==========================================
# FORMULÁRIO
# ==========================================

st.subheader("🔎 Encontrar empresas")

with st.form("form_busca"):

    pais = st.selectbox(
        "País",
        list(paises.keys())
    )

    cidade = st.text_input(
        "Cidade",
        placeholder="Ex: Cascavel, Curitiba, São Paulo..."
    )

    nicho = st.selectbox(
        "Tipo de empresa",
        list(mapa_nichos.keys())
    )

    link_previa = st.text_input(
        "Link do seu site de demonstração (opcional)",
        placeholder="https://seusite.vercel.app"
    )

    buscar = st.form_submit_button(
        "🔥 BUSCAR EMPRESAS",
        type="primary",
        use_container_width=True
    )


if buscar:

    if not cidade.strip():

        st.warning("Digite uma cidade para continuar.")

    else:

        with st.spinner("Procurando empresas..."):

            empresas, erro = buscar_empresas(
                cidade.strip(),
                pais,
                mapa_nichos[nicho],
                API_KEY
            )

        if erro:

            st.error(erro)

        else:

            st.session_state.empresas = empresas
            st.session_state.cidade_busca = cidade.strip()
            st.session_state.pais_busca = pais
            st.session_state.link_previa = link_previa.strip()
            st.session_state.verificados = set()

            st.success(
                f"{len(empresas)} empresas sem site cadastrado encontradas!"
            )


# ==========================================
# RESULTADOS
# ==========================================

if st.session_state.empresas:

    st.divider()

    st.subheader("📊 Seus resultados")

    leads = []

    for props in st.session_state.empresas:

        nome = props.get("name", "Empresa sem nome")
        telefone = obter_telefone(props)

        numero, status = analisar_telefone(
            telefone,
            st.session_state.pais_busca
        )

        endereco = (
            props.get("address_line2")
            or props.get("formatted")
            or "Endereço não informado"
        )

        identificador = str(
            props.get("place_id") or f"{nome}_{endereco}"
        )

        verificado = identificador in st.session_state.verificados

        prioridade = (
            "Alta" if numero and st.session_state.pais_busca == "Brasil"
            else "Média" if numero
            else "Baixa"
        )

        leads.append({
            "id": identificador,
            "nome": nome,
            "telefone": numero,
            "status": status,
            "endereco": endereco,
            "prioridade": prioridade,
            "verificado": verificado,
            "props": props
        })

    # GUARDA TODOS OS LEADS ANTES DOS FILTROS
    todos_leads = leads.copy()

    # ======================================
    # ESTATÍSTICAS
    # ======================================

    total = len(todos_leads)

    celulares = sum(
        1 for x in todos_leads
        if x["status"] == "Celular provável"
    )

    verificados = sum(
        1 for x in todos_leads
        if x["verificado"]
    )

    c1, c2 = st.columns(2)

    with c1:
        st.metric("Empresas encontradas", total)

    with c2:
        st.metric("Celulares prováveis", celulares)

    c3, c4 = st.columns(2)

    with c3:
        st.metric("Verificados por você", verificados)

    with c4:
        st.metric("Sem telefone válido", total - celulares)

    st.divider()

    # ======================================
    # FILTROS
    # ======================================

    st.subheader("🎯 Filtrar oportunidades")

    filtro = st.selectbox(
        "Mostrar:",
        [
            "Todas as empresas",
            "Somente celulares prováveis",
            "Somente verificados por mim",
            "Sem telefone válido"
        ]
    )

    if filtro == "Somente celulares prováveis":

        leads = [
            x for x in todos_leads
            if x["status"] == "Celular provável"
        ]

    elif filtro == "Somente verificados por mim":

        leads = [
            x for x in todos_leads
            if x["verificado"]
        ]

    elif filtro == "Sem telefone válido":

        leads = [
            x for x in todos_leads
            if not x["telefone"]
        ]

    else:
        leads = todos_leads.copy()

    st.caption(f"{len(leads)} empresas nesta visualização.")

    # ======================================
    # LISTA DE EMPRESAS
    # ======================================

    for i, lead in enumerate(leads):

        selo = (
            "🔥" if lead["prioridade"] == "Alta"
            else "🟡" if lead["prioridade"] == "Média"
            else "⚪"
        )

        nome = lead["nome"]

        with st.expander(f"{selo} {nome}"):

            st.write("📍 **Endereço:**")
            st.write(lead["endereco"])

            st.write("📞 **Telefone:**")

            if lead["telefone"]:

                st.code(lead["telefone"])

                if lead["status"] == "Celular provável":
                    st.success("Formato de celular brasileiro.")

                else:
                    st.warning("Número ainda não verificado para WhatsApp.")

                link_zap = "https://wa.me/" + lead["telefone"]

                st.link_button(
                    "💬 ABRIR NO WHATSAPP",
                    link_zap,
                    use_container_width=True
                )

                st.caption(
                    "Abrir o link não garante que o número esteja registrado no WhatsApp."
                )

                if lead["id"] in st.session_state.verificados:

                    st.success("Contato marcado como verificado por você.")

                else:

                    if st.checkbox(
                        "Confirmei que consegui abrir/contatar este número",
                        key=f"verificar_{lead['id']}"
                    ):
                        st.session_state.verificados.add(lead["id"])
                        st.rerun()

            else:

                st.warning(lead["status"])

            # ==================================
            # INSTAGRAM E MAPS
            # ==================================

            cidade_atual = st.session_state.cidade_busca

            busca_insta = urllib.parse.quote(
                f'site:instagram.com "{nome}" "{cidade_atual}"'
            )

            busca_maps = urllib.parse.quote(
                f"{nome} {cidade_atual}"
            )

            link_insta = (
                f"https://www.google.com/search?q={busca_insta}"
            )

            link_maps = (
                "https://www.google.com/maps/search/?api=1&query="
                + busca_maps
            )

            st.divider()

            st.write("**Encontrar redes sociais:**")

            st.link_button(
                "📷 Procurar Instagram",
                link_insta,
                use_container_width=True
            )

            st.link_button(
                "📍 Abrir no Google Maps",
                link_maps,
                use_container_width=True
            )

            # ==================================
            # MENSAGEM PRONTA
            # ==================================

            st.divider()

            st.write("**✉️ Mensagem de abordagem**")

            link_previa_atual = st.session_state.link_previa

            texto_link = (
                f"\n\nDá uma olhada: {link_previa_atual}"
                if link_previa_atual
                else ""
            )

            pais_atual = st.session_state.pais_busca

            if pais_atual == "Brasil":

                msg = (
                    f"Oi, tudo bem? Meu nome é Douwen, "
                    f"trabalho criando sites. Vi o perfil "
                    f"do {nome} e percebi que vocês não têm "
                    f"um site próprio cadastrado. "
                    f"Tenho uma ideia que pode ajudar a "
                    f"empresa a apresentar melhor seus serviços "
                    f"na internet. Posso te mostrar?"
                    f"{texto_link}"
                )

            elif pais_atual == "Portugal":

                msg = (
                    f"Olá! O meu nome é Douwen e crio sites. "
                    f"Vi o perfil da empresa {nome} e gostaria "
                    f"de apresentar uma ideia para melhorar "
                    f"a vossa presença online. Posso mostrar?"
                    f"{texto_link}"
                )

            elif pais_atual in ["Espanha", "México"]:

                msg = (
                    f"¡Hola! Mi nombre es Douwen y creo sitios web. "
                    f"Vi el perfil de {nome} y tengo una idea "
                    f"para mejorar su presencia en internet. "
                    f"¿Puedo mostrársela?"
                    f"{texto_link}"
                )

            else:

                msg = (
                    f"Hi! My name is Douwen and I build websites. "
                    f"I found {nome} and have an idea to improve "
                    f"your online presence. Can I show you?"
                    f"{texto_link}"
                )

            st.code(msg, language="text")

    # ======================================
    # EXPORTAÇÃO CSV
    # ======================================

    st.divider()

    st.subheader("📥 Exportar empresas")

    linhas_csv = []

    # EXPORTA TODOS OS LEADS, INDEPENDENTEMENTE DO FILTRO
    for lead in todos_leads:

        linhas_csv.append({
            "Empresa": lead["nome"],
            "Telefone": lead["telefone"] or "",
            "Status do telefone": lead["status"],
            "Prioridade": lead["prioridade"],
            "Verificado por mim": (
                "Sim" if lead["verificado"] else "Não"
            ),
            "Endereço": lead["endereco"]
        })

    if linhas_csv:

        arquivo = io.StringIO()

        escritor = csv.DictWriter(
            arquivo,
            fieldnames=linhas_csv[0].keys()
        )

        escritor.writeheader()
        escritor.writerows(linhas_csv)

        st.download_button(
            "📥 BAIXAR LISTA CSV",
            data=arquivo.getvalue().encode("utf-8-sig"),
            file_name="douwen_leads.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.caption(
        "Os dados são fornecidos pela Geoapify e podem estar incompletos. "
        "Sem site cadastrado não significa necessariamente sem site."
    )

else:

    st.info(
        "Digite uma cidade e escolha um nicho para começar sua prospecção."
    )

    st.markdown("""
    **Seu objetivo com o Douwen:**

    🔥 Encontrar empresas com potencial para receber um site.

    📱 Priorizar contatos de celular.

    💬 Facilitar a abordagem pelo WhatsApp.

    🚀 Transformar oportunidades em clientes.
    """)
