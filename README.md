# DN.Ia — Prospecção nacional

Aplicativo Streamlit para pesquisar empresas em cidades de todos os estados brasileiros, priorizando negócios com boas avaliações, telefone e sem site cadastrado no Google Places.

## Configuração no Streamlit Cloud
Em **App → Settings → Secrets**, adicione:

```toml
GOOGLE_API_KEY = "sua-chave-google"
```

Ative **Places API (New)** no Google Cloud, configure faturamento, restrições da chave e alertas de orçamento. A busca pode gerar custos conforme o uso e os campos solicitados.

## Executar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## O que o app faz
- Pesquisa empresas por nicho e cidade no Brasil.
- Inclui categorias amplas e cidades de todos os 26 estados e do Distrito Federal.
- Permite limitar consultas por rodada para controlar o volume.
- Prioriza empresas sem site cadastrado, com telefone e boas avaliações.
- Organiza leads em etapas comerciais e permite anotações e Instagram confirmado.
- Abre links de WhatsApp, Google Maps e pesquisa de Instagram.

## Importante
“Sem site cadastrado” significa que o Google Places não retornou um website. Isso não comprova que a empresa não tenha site. Confirme manualmente antes de abordar. O Google limita resultados por pesquisa; a opção “Brasil inteiro” usa a base de cidades listada no app e as cidades escolhidas na rodada, não faz um censo de todas as empresas brasileiras.

## Banco de dados
O app mantém o arquivo `leadfinder.db` e as tabelas antigas. Faça backup antes de atualizar. Em hospedagens com disco efêmero, use armazenamento persistente.
