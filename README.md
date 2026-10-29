# FinanScope API

API de portfólio para organizar lançamentos financeiros importados de CSV e gerar relatórios mensais. O foco do projeto é transformar dados tabulares em informação consultável: validação de arquivos, prevenção de duplicatas, persistência relacional, filtros e análise de orçamento por categoria.

> Projeto demonstrativo para execução local. O CSV de exemplo contém apenas dados fictícios.

## Funcionalidades

- Importa arquivos CSV em UTF-8, com separador vírgula ou ponto e vírgula.
- Valida data, descrição, valor, tipo e categoria por linha; retorna um resumo de importados, duplicados e rejeitados.
- Evita importar o mesmo lançamento duas vezes usando uma assinatura SHA-256 dos campos normalizados.
- Lista lançamentos com filtros por período, tipo, categoria e texto, além de paginação.
- Registra orçamentos mensais por categoria.
- Gera resumo mensal com receitas, despesas, saldo e consumo de cada orçamento.
- Compara receitas e despesas ao longo dos últimos meses.
- Expõe documentação interativa em `/docs`.

## Tecnologias

Python 3.10+, FastAPI, Pydantic, SQLAlchemy 2, SQLite e `python-multipart` para upload de CSV.

## Executar localmente

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

### macOS ou Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abra `http://127.0.0.1:8000/docs`. O arquivo `finanscope.db` será criado automaticamente na primeira inicialização.

## Importar o CSV de exemplo

Com a API em execução, envie o arquivo `data/exemplo_lancamentos.csv`:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/importacoes/csv" \
  -F "file=@data/exemplo_lancamentos.csv"
```

O arquivo precisa ter as colunas `data`, `descricao`, `valor`, `tipo` e `categoria`. Use datas no formato `AAAA-MM-DD`, valores positivos e tipo `despesa` ou `receita`. Valores decimais podem usar ponto ou vírgula; o tipo de transação informa se o valor é entrada ou saída.

## Endpoints

| Método | Rota | Ação |
| --- | --- | --- |
| `GET` | `/health` | Verifica se a API está ativa |
| `POST` | `/api/v1/importacoes/csv` | Importa e valida lançamentos de um CSV |
| `GET` | `/api/v1/lancamentos` | Lista lançamentos com filtros e paginação |
| `GET` | `/api/v1/lancamentos/{id}` | Consulta um lançamento |
| `PUT` | `/api/v1/orcamentos` | Cria ou atualiza um orçamento mensal |
| `GET` | `/api/v1/orcamentos?ano=2026&mes=10` | Consulta orçamentos de um mês |
| `GET` | `/api/v1/relatorios/mensal?ano=2026&mes=10` | Resume receitas, despesas e orçamento do mês |
| `GET` | `/api/v1/relatorios/tendencia?meses=6` | Compara o saldo dos últimos meses |

### Exemplo de orçamento

```json
{
  "ano": 2026,
  "mes": 10,
  "categoria": "Alimentação",
  "limite": "900.00"
}
```

### Exemplo de consulta filtrada

`GET /api/v1/lancamentos?tipo=despesa&categoria=Alimenta%C3%A7%C3%A3o&data_de=2026-10-01&data_ate=2026-10-31&offset=0&limit=20`

## Estrutura do projeto

```text
app/
  main.py                  Inicialização da aplicação e rota de saúde
  database.py              Engine, sessão e dependência do banco
  enums.py                 Tipos de lançamento
  models.py                Modelos de lançamento e orçamento
  schemas.py               Contratos e validação da API
  routers/financeiro.py    Importação, consultas, orçamentos e relatórios
  services/csv_importer.py Validação, normalização e deduplicação do CSV
  services/reporting.py    Agregações mensais e tendência
data/
  exemplo_lancamentos.csv  Dados demonstrativos fictícios
```

## Descrição para currículo

Depois de revisar o código e conseguir explicar as decisões técnicas, uma descrição fiel ao projeto é:

> Desenvolvi uma API de análise financeira com FastAPI, SQLAlchemy e SQLite, incluindo importação e validação de CSV, deduplicação de lançamentos, filtros e paginação, orçamentos por categoria e relatórios mensais.

Personalize a descrição para refletir o que você estudou, modificou e consegue demonstrar.

## Referências técnicas

- [Upload de arquivos no FastAPI](https://fastapi.tiangolo.com/tutorial/request-files/)
- [Mapeamento declarativo no SQLAlchemy 2](https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html)
