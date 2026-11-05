# DN.Ia — Prospecção nacional 3.1

Aplicativo Streamlit para encontrar empresas em cidades brasileiras, organizar leads e priorizar oportunidades sem site cadastrado.

## Atualização no Streamlit Cloud
1. Substitua o `app.py` e o `requirements.txt` no repositório GitHub pelos arquivos desta pasta.
2. Faça Commit.
3. No Streamlit Cloud, aguarde o app reiniciar. Não apague `leadfinder.db`.
4. Mantenha `GOOGLE_API_KEY` nos Secrets.

## Google Places
Ative Places API (New), configure faturamento e confira as cotas de `SearchTextRequest`. O erro 429 `Quota exceeded` significa que a cota disponível foi atingida. O app agora interrompe a rodada ao detectar esse erro, em vez de continuar repetindo chamadas. O cache reduz chamadas repetidas idênticas por até 24 horas, mas não aumenta a cota do Google.

## Filtro de WhatsApp
O app só salva e mostra telefones celulares brasileiros no formato DDD + 9 dígitos, com o primeiro dígito do número sendo 9. Linhas fixas (inclusive as iniciadas por 3) e números incompletos são descartados. A validação do formato não garante que a conta esteja ativa no WhatsApp.

## Nichos
Inclui categorias para alimentação, beleza, saúde, automotivo, casa/construção, comércio, lutas/artes marciais, esportes, eventos, turismo, educação e serviços profissionais.

## Banco de dados
O app mantém as tabelas e os registros existentes em `leadfinder.db`; não exclua esse arquivo. Faça backup antes de alterações.

## Observação
“Sem site cadastrado” significa que o Google Places não retornou um website; confirme manualmente antes de abordar. A busca usa a lista de cidades disponível no app e não cobre todos os municípios do Brasil.
