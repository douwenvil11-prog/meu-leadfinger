# LeadFinder OS 2.0

Painel Streamlit para prospecção, CRM simples e geração de demonstrações de sites com Groq.

## 1. Instalação

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

## 2. Chaves

Crie `.streamlit/secrets.toml`:

```toml
GOOGLE_API_KEY = "SUA_CHAVE_GOOGLE_PLACES"
GROQ_API_KEY = "SUA_CHAVE_GROQ"
GROQ_MODEL = "openai/gpt-oss-120b"
HOSTING_ENDPOINT = "https://brewpage.app/api/html"
HOSTING_TOKEN = ""
```

A API do Google Places precisa estar habilitada e com faturamento configurado. Restrinja a chave no Google Cloud.

## 3. O que mudou

- Banco SQLite para leads, atividades e projetos.
- Busca paginada no Google Places (até 3 páginas por pesquisa).
- Filtros de nota, avaliações e empresas com/sem site cadastrado.
- Pontuação indicativa de leads.
- CRM com status e notas.
- Geração de sites em duas etapas: direção de arte e desenvolvimento.
- Validação estrutural básica do HTML.
- Download do HTML e hospedagem opcional.
- Histórico de projetos.

## 4. Limitações e cuidados

- `websiteUri` ausente no Google Places não prova que a empresa não tenha site. Confirme manualmente.
- A busca de Instagram é uma pesquisa, não uma confirmação automática de perfil.
- O HTML gerado por IA deve ser revisado visualmente e testado em navegador antes de ser enviado ao cliente.
- Confirme direitos de uso das imagens e veracidade de textos, serviços, preços e depoimentos.
- SQLite depende de armazenamento persistente no servidor. Em ambiente efêmero, os dados podem ser perdidos; use PostgreSQL ou disco persistente.
- Confira os termos e limites de uso do Google Places e do serviço de hospedagem.
- O código foi preparado como base inicial e precisa ser testado com suas chaves e contas reais.

## 5. Observação sobre o provedor de hospedagem

O endpoint e o formato de envio da Brewpage foram mantidos com base no código original. Se a API deles mudar, ajuste `host_html()` e as variáveis `HOSTING_ENDPOINT` / `HOSTING_TOKEN`.
