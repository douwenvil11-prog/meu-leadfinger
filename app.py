import os, re, sqlite3, urllib.parse
from datetime import datetime
from pathlib import Path
import requests
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "leadfinder.db"

st.set_page_config(page_title="DN.Ia | Busca de empresas", page_icon="🎯", layout="centered")
st.markdown("""
<style>
.stApp{background:#090e16;color:#edf3fb}.block-container{max-width:900px;padding:1rem .8rem 4rem}
[data-testid="stSidebar"]{background:#101925;border-right:1px solid #263448}
div[data-testid="stMetric"]{background:#121d2b;border:1px solid #29394e;padding:13px;border-radius:13px}
div[data-testid="stForm"]{background:#101925;border:1px solid #29394e;padding:15px;border-radius:13px}
.stButton>button[kind="primary"]{background:#35d39a;color:#06140e;border:0;font-weight:800}
.stButton>button{border-radius:10px}a{color:#63ddb1!important}
</style>
""", unsafe_allow_html=True)

# Base nacional: capitais e centros regionais. Você pode adicionar qualquer cidade manualmente.
CIDADES = {
"Acre (AC)": ["Rio Branco", "Cruzeiro do Sul"], "Alagoas (AL)": ["Maceió", "Arapiraca"],
"Amapá (AP)": ["Macapá", "Santana"], "Amazonas (AM)": ["Manaus", "Parintins", "Itacoatiara"],
"Bahia (BA)": ["Salvador", "Feira de Santana", "Vitória da Conquista", "Itabuna", "Juazeiro", "Ilhéus", "Camaçari", "Barreiras", "Lauro de Freitas"],
"Ceará (CE)": ["Fortaleza", "Juazeiro do Norte", "Sobral", "Crato", "Maracanaú", "Iguatu"],
"Distrito Federal (DF)": ["Brasília"], "Espírito Santo (ES)": ["Vitória", "Vila Velha", "Serra", "Cariacica", "Cachoeiro de Itapemirim", "Linhares"],
"Goiás (GO)": ["Goiânia", "Aparecida de Goiânia", "Anápolis", "Rio Verde", "Catalão", "Luziânia", "Jataí"],
"Maranhão (MA)": ["São Luís", "Imperatriz", "Caxias", "Timon", "Bacabal"],
"Mato Grosso (MT)": ["Cuiabá", "Várzea Grande", "Rondonópolis", "Sinop", "Tangará da Serra", "Cáceres"],
"Mato Grosso do Sul (MS)": ["Campo Grande", "Dourados", "Três Lagoas", "Corumbá", "Ponta Porã"],
"Minas Gerais (MG)": ["Belo Horizonte", "Uberlândia", "Contagem", "Juiz de Fora", "Betim", "Montes Claros", "Uberaba", "Governador Valadares", "Ipatinga", "Divinópolis", "Poços de Caldas", "Pouso Alegre"],
"Pará (PA)": ["Belém", "Ananindeua", "Santarém", "Marabá", "Parauapebas", "Castanhal", "Altamira"],
"Paraíba (PB)": ["João Pessoa", "Campina Grande", "Santa Rita", "Patos"],
"Paraná (PR)": ["Curitiba", "Londrina", "Maringá", "Cascavel", "Foz do Iguaçu", "Ponta Grossa", "São José dos Pinhais", "Colombo", "Guarapuava", "Toledo", "Paranaguá", "Apucarana", "Umuarama", "Pato Branco", "Francisco Beltrão"],
"Pernambuco (PE)": ["Recife", "Jaboatão dos Guararapes", "Olinda", "Caruaru", "Petrolina", "Paulista", "Cabo de Santo Agostinho", "Garanhuns"],
"Piauí (PI)": ["Teresina", "Parnaíba", "Picos", "Floriano"],
"Rio de Janeiro (RJ)": ["Rio de Janeiro", "Niterói", "São Gonçalo", "Duque de Caxias", "Nova Iguaçu", "Petrópolis", "Campos dos Goytacazes", "Volta Redonda", "Macaé", "Cabo Frio"],
"Rio Grande do Norte (RN)": ["Natal", "Mossoró", "Parnamirim", "Caicó"],
"Rio Grande do Sul (RS)": ["Porto Alegre", "Caxias do Sul", "Pelotas", "Canoas", "Santa Maria", "Gravataí", "Novo Hamburgo", "Passo Fundo", "São Leopoldo", "Rio Grande", "Erechim"],
"Rondônia (RO)": ["Porto Velho", "Ji-Paraná", "Ariquemes", "Vilhena"], "Roraima (RR)": ["Boa Vista", "Rorainópolis"],
"Santa Catarina (SC)": ["Florianópolis", "Joinville", "Blumenau", "São José", "Chapecó", "Itajaí", "Criciúma", "Jaraguá do Sul", "Lages", "Balneário Camboriú", "Brusque"],
"São Paulo (SP)": ["São Paulo", "Campinas", "Guarulhos", "São Bernardo do Campo", "Santo André", "Osasco", "Sorocaba", "Ribeirão Preto", "Santos", "São José dos Campos", "Jundiaí", "Piracicaba", "Bauru", "Franca", "Marília", "Presidente Prudente", "Araraquara", "São Carlos", "Limeira", "Taubaté", "Barueri", "Mogi das Cruzes"],
"Sergipe (SE)": ["Aracaju", "Nossa Senhora do Socorro", "Itabaiana", "Lagarto"],
"Tocantins (TO)": ["Palmas", "Araguaína", "Gurupi", "Porto Nacional"]}

NICHOS = {
"Alimentação": ["Pizzaria", "Hamburgueria", "Restaurante", "Lanchonete", "Açaíteria", "Sorveteria", "Espetaria", "Churrascaria", "Pastelaria", "Cafeteria", "Padaria", "Confeitaria", "Marmitaria", "Comida japonesa", "Bar e petiscaria", "Delivery de comida", "Food truck"],
"Beleza e estética": ["Barbearia", "Salão de beleza", "Clínica de estética", "Esmalteria", "Depilação", "Studio de sobrancelhas", "Bronzeamento", "Massoterapia", "Studio de tatuagem", "Spa", "Maquiadora"],
"Saúde e bem-estar": ["Clínica médica", "Clínica odontológica", "Consultório odontológico", "Fisioterapia", "Psicologia", "Nutricionista", "Pilates", "Academia", "Personal trainer", "Clínica veterinária", "Laboratório de análises", "Ótica"],
"Automotivo": ["Oficina mecânica", "Auto center", "Auto elétrica", "Lava-jato", "Estética automotiva", "Funilaria e pintura", "Loja de pneus", "Autopeças", "Revenda de carros", "Concessionária", "Oficina de motos", "Moto peças", "Som automotivo"],
"Casa e construção": ["Material de construção", "Marcenaria", "Marmoraria", "Vidraçaria", "Serralheria", "Empresa de reformas", "Construtora", "Imobiliária", "Ar-condicionado", "Dedetizadora", "Desentupidora", "Energia solar", "Paisagismo", "Móveis planejados", "Limpeza de estofados", "Encanador", "Eletricista"],
"Comércio": ["Loja de roupas", "Loja de calçados", "Loja de móveis", "Loja de celulares", "Assistência técnica de celulares", "Loja de informática", "Papelaria", "Floricultura", "Joalheria", "Loja de presentes", "Pet shop", "Loja de suplementos", "Loja de colchões", "Loja de decoração", "Loja de brinquedos"],
"Lutas e artes marciais": ["Academia de luta", "Academia de boxe", "Boxe", "Muay Thai", "Jiu-jitsu", "MMA", "Kickboxing", "Karatê", "Taekwondo", "Judô", "Capoeira", "Wrestling", "Defesa pessoal", "Escola de artes marciais", "Academia de kickboxing"],
"Esportes e atividades": ["Academia", "Crossfit", "Funcional", "Personal trainer", "Escola de futebol", "Escolinha de futebol", "Quadra society", "Arena esportiva", "Clube esportivo", "Natação", "Dança", "Ginástica", "Pilates", "Yoga", "Beach tennis", "Futevôlei", "Tênis"],
"Eventos, lazer e turismo": ["Buffet", "Casa de festas", "Fotógrafo", "Filmagem de eventos", "Hotel", "Pousada", "Agência de turismo", "Salão de eventos", "Espaço de recreação", "Parque de diversão", "Escola de dança"],
"Educação e profissionais": ["Escola de idiomas", "Escola particular", "Curso profissionalizante", "Escola de música", "Escritório de contabilidade", "Advocacia", "Despachante", "Consultoria empresarial", "Agência de marketing", "Empresa de segurança", "Transportadora", "Gráfica", "Corretora de seguros", "Coworking"]}
STATUS = ["Novo", "Pesquisado", "Abordado", "Respondeu", "Interessado", "Orçamento enviado", "Fechado", "Perdido"]

# Banco: conserva tabelas e dados antigos. Acrescenta apenas colunas ausentes.
def conn_db():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with conn_db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY AUTOINCREMENT, place_id TEXT, name TEXT, category TEXT, city TEXT, address TEXT, phone TEXT, website TEXT, maps_url TEXT, rating REAL, reviews INTEGER, instagram_url TEXT, score INTEGER DEFAULT 0, status TEXT DEFAULT 'Novo', notes TEXT DEFAULT '', created_at TEXT, updated_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, business_name TEXT, category TEXT, city TEXT, phone TEXT, address TEXT, html TEXT, hosted_url TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS activities (id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, action TEXT, details TEXT, created_at TEXT)")
        existing = {r[1] for r in c.execute("PRAGMA table_info(leads)").fetchall()}
        additions = {"place_id":"TEXT", "name":"TEXT", "category":"TEXT", "city":"TEXT", "address":"TEXT", "phone":"TEXT", "website":"TEXT", "maps_url":"TEXT", "rating":"REAL", "reviews":"INTEGER", "instagram_url":"TEXT", "score":"INTEGER DEFAULT 0", "status":"TEXT DEFAULT 'Novo'", "notes":"TEXT DEFAULT ''", "created_at":"TEXT", "updated_at":"TEXT"}
        for col, typ in additions.items():
            if col not in existing:
                c.execute(f"ALTER TABLE leads ADD COLUMN {col} {typ}")
        c.commit()
init_db()

def get_key(name):
    try: return str(st.secrets.get(name, os.getenv(name, "")))
    except Exception: return os.getenv(name, "")

def phone_digits(p): return re.sub(r"\D", "", p or "")
def is_whatsapp_mobile(p):
    """Aceita apenas celular brasileiro atual: DDD + 9 dígitos, com nono dígito 9."""
    n = phone_digits(p)
    if n.startswith("55") and len(n) == 13:
        n = n[2:]
    return len(n) == 11 and n[:2].isdigit() and n[2] == "9" and n.isdigit()
def wa_link(p):
    n = phone_digits(p)
    if n.startswith("55") and len(n) == 13 and is_whatsapp_mobile(n): return "https://wa.me/" + n
    if is_whatsapp_mobile(n): return "https://wa.me/55" + n
    return ""
def score(x):
    v = 0
    if not x.get("website"): v += 35
    if x.get("phone"): v += 20
    r, n = x.get("rating") or 0, x.get("reviews") or 0
    if r >= 4.5: v += 15
    elif r >= 4: v += 10
    elif r >= 3.8: v += 5
    if n >= 100: v += 15
    elif n >= 30: v += 10
    elif n >= 10: v += 5
    if x.get("address"): v += 5
    return min(v,100)

@st.cache_data(ttl=86400, show_spinner=False)
def google_search(api_key, query, pages):
    endpoint = "https://places.googleapis.com/v1/places:searchText"
    headers = {"Content-Type":"application/json", "X-Goog-Api-Key":api_key,
      "X-Goog-FieldMask":"places.id,places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri,places.userRatingCount,places.rating,places.businessStatus,nextPageToken"}
    results, token = [], None
    for _ in range(pages):
        payload = {"textQuery":query, "pageSize":20, "languageCode":"pt-BR", "regionCode":"BR"}
        if token: payload["pageToken"] = token
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=40)
        if resp.status_code >= 400:
            try: msg = resp.json().get("error",{}).get("message",resp.text)
            except Exception: msg = resp.text
            raise RuntimeError(f"Google Places {resp.status_code}: {msg}")
        data = resp.json(); results.extend(data.get("places",[])); token=data.get("nextPageToken")
        if not token: break
    return results

def normalize(p, niche, city):
    x = {"place_id":p.get("id"), "name":p.get("displayName",{}).get("text","Empresa sem nome"), "category":niche, "city":city,
         "address":p.get("formattedAddress",""), "phone":p.get("nationalPhoneNumber",""), "website":p.get("websiteUri",""),
         "maps_url":p.get("googleMapsUri",""), "rating":p.get("rating"), "reviews":p.get("userRatingCount",0),
         "business_status":p.get("businessStatus","")}
    x["score"] = score(x); return x

def save_leads(items):
    items = [x for x in items if is_whatsapp_mobile(x.get("phone"))]
    now=datetime.now().isoformat(timespec="seconds")
    with conn_db() as c:
        for x in items:
            pid=x.get("place_id")
            old=c.execute("SELECT id,status,notes,instagram_url,created_at FROM leads WHERE place_id=?",(pid,)).fetchone() if pid else None
            vals=(x.get("name"),x.get("category"),x.get("city"),x.get("address"),x.get("phone"),x.get("website"),x.get("maps_url"),x.get("rating"),x.get("reviews"),x.get("score",0),now)
            if old:
                c.execute("UPDATE leads SET name=?,category=?,city=?,address=?,phone=?,website=?,maps_url=?,rating=?,reviews=?,score=?,updated_at=? WHERE id=?", vals+(old["id"],))
            else:
                c.execute("INSERT INTO leads (place_id,name,category,city,address,phone,website,maps_url,rating,reviews,score,status,notes,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,'Novo','',?,?)",(pid,)+vals[:-1]+(now,now))
        c.commit()

def leads_list(status="Todos", q="", no_site=False, min_score=0):
    sql="SELECT * FROM leads WHERE 1=1"; p=[]
    if status!="Todos": sql+=" AND status=?"; p.append(status)
    if q: sql+=" AND (name LIKE ? OR city LIKE ? OR category LIKE ?)"; t=f"%{q}%"; p += [t,t,t]
    if no_site: sql+=" AND (website IS NULL OR website='')"
    sql+=" AND COALESCE(score,0)>=? ORDER BY score DESC,COALESCE(reviews,0) DESC"; p.append(min_score)
    with conn_db() as c: rows = c.execute(sql,p).fetchall()
    return [r for r in rows if is_whatsapp_mobile(r["phone"])]

def update_lead(i,status,notes,instagram):
    with conn_db() as c:
        c.execute("UPDATE leads SET status=?,notes=?,instagram_url=?,updated_at=? WHERE id=?",(status,notes,instagram,datetime.now().isoformat(timespec="seconds"),i))
        c.execute("INSERT INTO activities (lead_id,action,details,created_at) VALUES (?,?,?,?)",(i,"Lead atualizado",f"Status: {status}",datetime.now().isoformat(timespec="seconds")))
        c.commit()

def instagram_search(name,city):
    q=urllib.parse.quote_plus(f"{name} {city} Instagram")
    return "https://www.google.com/search?q="+q

# UI
st.sidebar.title("🎯 DN.Ia")
st.sidebar.caption("Busca nacional de empresas")
page=st.sidebar.radio("Menu",["Buscar empresas","Minha lista","Painel","Configurações"])
api_key=get_key("GOOGLE_API_KEY")
if not api_key: api_key=st.sidebar.text_input("Google Places API Key",type="password")
st.sidebar.caption("A chave não deve ser publicada no código do GitHub.")

if page=="Buscar empresas":
    st.title("🎯 Encontrar empresas")
    st.caption("Escolha onde procurar, selecione os nichos e receba somente empresas com celular válido para WhatsApp.")
    todos=sorted({city for arr in CIDADES.values() for city in arr})
    with st.container(border=True):
        st.subheader("1. Onde procurar")
        modo=st.radio("Abrangência",["Brasil inteiro","Por estado","Escolher cidades"],horizontal=False)
        if modo=="Brasil inteiro":
            st.info(f"Base: {len(CIDADES)} estados/DF · {len(todos)} cidades. Selecione uma lista menor por rodada para não estourar a cota.")
            default=["São Paulo","Campinas","Rio de Janeiro","Curitiba","Foz do Iguaçu","Cascavel"]
            cities=st.multiselect("Cidades desta rodada",todos,default=default)
        elif modo=="Por estado":
            states=st.multiselect("Estados",list(CIDADES.keys()),default=["Paraná (PR)"])
            options=sorted({x for state in states for x in CIDADES[state]})
            cities=st.multiselect("Cidades",options,default=options[:5])
        else:
            cities=st.multiselect("Cidades",todos,default=["Foz do Iguaçu","Cascavel","Curitiba"])
    with st.container(border=True):
        st.subheader("2. O que procurar")
        groups=st.multiselect("Categorias",list(NICHOS.keys()),default=["Alimentação","Beleza e estética","Lutas e artes marciais"])
        available=[n for g in groups for n in NICHOS[g]]
        niches=st.multiselect("Nichos",available,default=available[:5],help="Você pode marcar vários nichos dentro das categorias escolhidas.")
    with st.expander("3. Filtros da busca (recomendado manter simples)",expanded=False):
        pages=st.selectbox("Resultados por pesquisa",[1,2,3],index=0,help="Cada página pode trazer até 20 empresas. Mais páginas consomem mais cota.")
        min_rating=st.slider("Nota mínima",0.0,5.0,3.8,0.1)
        max_queries=st.select_slider("Consultas nesta rodada",options=[3,5,8,10,15,20,30],value=5)
        only_no_site=st.checkbox("Somente empresas sem site cadastrado",value=True)
    require_phone=True
    combos=[(n,city) for city in cities for n in niches][:int(max_queries)]
    st.metric("Pesquisas nesta rodada",len(combos))
    st.caption("O filtro de telefone é obrigatório: celulares com 9 após o DDD. Telefones fixos começados por 2, 3, 4 ou 5 são descartados.")
    if st.button("🔎 Buscar empresas",type="primary",use_container_width=True,disabled=not combos):
        if not api_key:
            st.error("Adicione sua Google Places API Key nos Secrets do Streamlit.")
        else:
            found={}; errors=[]; quota_error=False; bar=st.progress(0); status=st.empty()
            for i,(n,city) in enumerate(combos,1):
                status.write(f"Pesquisando {n} · {city} ({i}/{len(combos)})")
                try:
                    for place in google_search(api_key,f"{n} em {city}, Brasil",pages):
                        if place.get("businessStatus") not in (None,"OPERATIONAL"): continue
                        x=normalize(place,n,city)
                        if not is_whatsapp_mobile(x.get("phone")): continue
                        found[x.get("place_id") or f"{x['name']}|{city}"]=x
                except Exception as e:
                    msg=str(e)
                    errors.append(f"{n} / {city}: {msg}")
                    if "429" in msg or "quota" in msg.lower() or "exceeded" in msg.lower():
                        quota_error=True
                        break
                bar.progress(i/len(combos))
            all_items=list(found.values())
            filtered=[x for x in all_items if (not only_no_site or not x["website"]) and (x["rating"] or 0)>=min_rating]
            save_leads(filtered); status.empty(); bar.empty()
            if quota_error:
                st.error("O Google bloqueou a busca porque a cota diária de SearchTextRequest foi atingida (erro 429). O app parou automaticamente para não repetir 14 erros nem gastar mais consultas.")
                st.markdown("**Como resolver:** abra Google Cloud Console → APIs e serviços → Places API (New) → Cotas. Confira o limite diário de SearchTextRequest e a conta de faturamento. Se o limite for fixo do plano/projeto, aguarde a renovação da cota ou solicite aumento. Reduzir pesquisas no app ajuda a evitar novos bloqueios, mas não libera uma cota já esgotada.")
            st.success(f"{len(filtered)} empresas com celular válido salvas de {len(all_items)} resultados recebidos.")
            st.info("‘Sem site cadastrado’ significa que o Google não retornou um site. Confirme manualmente antes de abordar.")
            if errors and not quota_error:
                with st.expander(f"Ver {len(errors)} erros"):
                    for e in errors: st.warning(e)
    st.divider(); st.subheader("📌 Empresas prontas para abordar")
    q=st.text_input("Buscar empresa, cidade ou nicho")
    quality=st.selectbox("Potencial mínimo",["Todos","50+","70+","85+"])
    no_site=st.checkbox("Mostrar somente sem site cadastrado",True)
    minscore={"Todos":0,"50+":50,"70+":70,"85+":85}[quality]
    rows=leads_list(q=q,no_site=no_site,min_score=minscore)
    if not rows: st.info("Nenhuma empresa com celular válido salva ainda. Faça uma busca ou ajuste os filtros.")
    for r in rows[:100]:
        with st.container(border=True):
            st.markdown(f"**{r['name']}**")
            st.caption(f"{r['category'] or 'Empresa'} · {r['city'] or 'Cidade não informada'} · ⭐ {r['rating'] or '—'} ({r['reviews'] or 0} avaliações)")
            st.write(f"**Potencial:** {r['score'] or 0}/100")
            st.write(f"**WhatsApp:** {r['phone']}")
            st.write(f"**Site:** {r['website'] or 'Não cadastrado no Google'}")
            st.link_button("Abrir WhatsApp",wa_link(r['phone']),use_container_width=True)
            st.link_button("Pesquisar Instagram",instagram_search(r['name'],r['city'] or ''),use_container_width=True)
            if r['maps_url']: st.link_button("Ver no Google Maps",r['maps_url'],use_container_width=True)
            st.caption(f"Status: {r['status']} · {r['address'] or 'Endereço não informado'}")
elif page=="Minha lista":
    st.title("Minha lista de empresas")
    q=st.text_input("Buscar nome, cidade ou nicho"); status=st.selectbox("Etapa",["Todos"]+STATUS); no_site=st.checkbox("Somente sem site cadastrado",False)
    rows=leads_list(status,q,no_site)
    if not rows: st.info("Sua lista ainda está vazia.")
    else:
        labels=[f"{r['name']} — {r['city']} — #{r['id']}" for r in rows]
        chosen=st.selectbox("Selecione uma empresa",range(len(rows)),format_func=lambda i:labels[i])
        r=rows[chosen]
        a,b,c=st.columns(3); a.metric("Potencial",f"{r['score'] or 0}/100"); b.metric("Nota",r['rating'] or "—"); c.metric("Avaliações",r['reviews'] or 0)
        st.write(f"**Endereço:** {r['address'] or 'Não informado'}")
        st.write(f"**Telefone:** {r['phone'] or 'Não informado'}")
        st.write(f"**Site:** {r['website'] or 'Não cadastrado no Google — confirmar manualmente'}")
        link=wa_link(r['phone'])
        if link: st.link_button("Abrir WhatsApp",link)
        st.link_button("Pesquisar Instagram",instagram_search(r['name'],r['city'] or ''))
        if r['maps_url']: st.link_button("Abrir Google Maps",r['maps_url'])
        with st.form(f"edit_{r['id']}"):
            status_new=st.selectbox("Etapa da prospecção",STATUS,index=STATUS.index(r['status']) if r['status'] in STATUS else 0)
            insta=st.text_input("Instagram confirmado (opcional)",value=r['instagram_url'] or "")
            notes=st.text_area("Anotações",value=r['notes'] or "")
            if st.form_submit_button("Salvar alterações",type="primary"):
                update_lead(r['id'],status_new,notes,insta); st.success("Lead atualizado."); st.rerun()
elif page=="Painel":
    st.title("Painel de prospecção"); rows=leads_list()
    counts={s:sum(1 for r in rows if r['status']==s) for s in STATUS}
    a,b,c,d=st.columns(4); a.metric("Empresas salvas",len(rows)); b.metric("Sem site cadastrado",sum(1 for r in rows if not r['website'])); c.metric("Interessados",counts['Interessado']); d.metric("Fechados",counts['Fechado'])
    st.subheader("Funil comercial")
    cols=st.columns(4)
    for col,s in zip(cols,["Novo","Abordado","Respondeu","Interessado"]): col.metric(s,counts[s])
    st.subheader("Melhores oportunidades")
    for r in rows[:15]: st.write(f"**{r['name']}** · {r['category']} · {r['city']} · potencial {r['score']}/100")
else:
    st.title("Configurações")
    st.markdown("No Streamlit Cloud, configure em **App → Settings → Secrets**:")
    st.code('GOOGLE_API_KEY = "sua-chave-google"',language="toml")
    st.markdown("Ative **Places API (New)** no Google Cloud, configure faturamento, restrinja a chave à API necessária e crie alertas de orçamento. Nunca publique a chave no GitHub.")
    st.warning("A API Google Places pode gerar custos. Limite de consultas no app ajuda a controlar o volume, mas não substitui os limites de orçamento do Google Cloud.")
    st.markdown("**Compatibilidade:** o app mantém o banco `leadfinder.db` e as tabelas antigas `leads`, `projects` e `activities`. Não apague esse arquivo ao atualizar.")

st.divider(); st.caption("DN.Ia · Busca e organização de oportunidades comerciais. Dados de site/Instagram devem ser confirmados antes do contato.")
