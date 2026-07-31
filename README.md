<div align="center">

# Mega Sena Master

Aplicação web em Flask para validar históricos de concursos, analisar frequências e gerar cinco combinações de seis dezenas.

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-3.0-150458?logo=pandas&logoColor=white)
![Tests](https://img.shields.io/badge/Testes-unittest-08783f)

</div>

> A aplicação não prevê resultados e não aumenta a probabilidade matemática de acerto. O modo ponderado utiliza somente a frequência observada no arquivo histórico. Jogue com responsabilidade.

## Visão geral

O Mega Sena Master recebe um arquivo CSV ou XLSX com concursos anteriores, valida o conteúdo, calcula a frequência das 60 dezenas e apresenta dois métodos para gerar jogos:

- **Distribuição uniforme:** todas as dezenas possuem a mesma probabilidade de seleção.
- **Frequência histórica:** dezenas mais frequentes recebem pesos maiores durante a geração.

Cada execução produz cinco jogos únicos. No modo ponderado, também são aplicados filtros básicos de equilíbrio entre números pares e ímpares e soma total das dezenas.

## Funcionalidades

- Upload de históricos nos formatos CSV e XLSX.
- Leitura automática de `resultados.csv` na raiz do projeto.
- Validação de colunas, tipos, valores vazios, faixa numérica e repetições.
- Ordenação das seis dezenas de cada concurso.
- Cálculo de frequência para todas as dezenas de 1 a 60.
- Exibição das dez dezenas mais frequentes e das dez menos frequentes.
- Geração uniforme de cinco combinações.
- Geração ponderada com base na frequência histórica.
- Proteção CSRF no formulário.
- Limite de upload de 10 MB.
- Cabeçalhos HTTP de segurança.
- Cookies de sessão configuráveis para HTTPS.
- Healthcheck em `/health`.
- Interface responsiva para desktop e celular.
- Testes automatizados com `unittest`.
- Execução automática dos testes no GitHub Actions.

## Tecnologias

- Python 3.12 ou superior
- Flask
- Gunicorn
- Pandas
- NumPy
- OpenPyXL
- HTML e CSS

## Estrutura principal

```text
mega-sena/
├── .github/
│   └── workflows/
│       └── tests.yml
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
├── resultados.csv          # opcional, não incluído no repositório
├── instance/               # criado localmente e ignorado pelo Git
├── static/
│   └── styles.css
├── templates/
│   └── index.html
└── tests/
    └── test_app.py
```

## Requisitos

- Python 3.12 ou superior
- `pip`
- Ambiente virtual recomendado
- Arquivo histórico CSV ou XLSX para análise

## Instalação

Clone o repositório:

```bash
git clone https://github.com/EduMiranda78/mega-sena.git
cd mega-sena
```

Crie e ative um ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

No Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instale as dependências:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configuração

A aplicação lê as seguintes variáveis de ambiente:

| Variável | Obrigatória | Padrão | Finalidade |
| --- | --- | --- | --- |
| `SECRET_KEY` | Recomendada | Chave local em `instance/.secret_key` | Assinatura segura da sessão e do token CSRF |
| `SESSION_COOKIE_SECURE` | Não | `false` | Envia o cookie de sessão somente por HTTPS |

Gere uma chave para produção:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Exporte as variáveis no Linux:

```bash
export SECRET_KEY="cole_a_chave_gerada_aqui"
export SESSION_COOKIE_SECURE=false
```

Em um servidor com HTTPS:

```bash
export SESSION_COOKIE_SECURE=true
```

O arquivo `.env.example` serve como referência. A aplicação não carrega arquivos `.env` automaticamente. Use variáveis do sistema, do serviço ou do contêiner.

## Formato do histórico

O arquivo deve conter exatamente estas colunas:

```text
Bola1;Bola2;Bola3;Bola4;Bola5;Bola6
```

Exemplo válido:

```csv
Bola1;Bola2;Bola3;Bola4;Bola5;Bola6
4;12;23;31;45;57
2;9;18;34;41;60
7;16;25;38;49;53
```

Regras aplicadas:

- Cada linha deve conter seis números.
- Os valores devem ser inteiros entre 1 e 60.
- Uma linha não pode repetir a mesma dezena.
- CSV com vírgula ou ponto e vírgula é aceito.
- Arquivos XLSX são lidos pela primeira planilha disponível.
- O arquivo pode ter no máximo 10 MB.

Quando um arquivo chamado `resultados.csv` estiver na raiz do projeto, ele será carregado automaticamente. Sem esse arquivo, a página solicitará o upload.

## Execução local

```bash
source .venv/bin/activate
python app.py
```

No Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python app.py
```

A aplicação ficará disponível em:

```text
http://127.0.0.1:5080
```

Em outra máquina da mesma rede, use o endereço IP do computador que executa o Flask:

```text
http://IP-DO-SERVIDOR:5080
```

## Execução com Gunicorn

```bash
source .venv/bin/activate
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
gunicorn --workers 2 --bind 0.0.0.0:5080 --access-logfile - --error-logfile - app:app
```

Para exposição pública, use Nginx ou outro proxy reverso, HTTPS e `SESSION_COOKIE_SECURE=true`.

## Como usar

1. Abra a página inicial.
2. Envie um histórico CSV ou XLSX, caso `resultados.csv` não esteja disponível.
3. Escolha distribuição uniforme ou frequência histórica.
4. Clique em **Gerar 5 jogos**.
5. Consulte o resumo das frequências e as combinações geradas.

## Verificação de funcionamento

```bash
curl -fsS http://127.0.0.1:5080/health
```

Resposta esperada:

```json
{"status":"ok"}
```

## Testes

Execute a suíte completa:

```bash
python -m unittest discover -s tests -v
```

O mesmo comando é executado automaticamente pelo workflow `.github/workflows/tests.yml` em pushes para `main`, branches `agent/**` e pull requests destinados à `main`.

Os testes cobrem:

- leitura e normalização de CSV;
- rejeição de dezenas repetidas;
- rejeição de valores fora da faixa;
- cálculo de frequências;
- geração de jogos únicos;
- filtros do modo ponderado;
- resposta da página inicial;
- carregamento da folha de estilos;
- upload e geração de jogos;
- healthcheck.

## Segurança

- O token CSRF é validado em todas as requisições `POST`.
- A sessão usa cookie `HttpOnly` e `SameSite=Lax`.
- O cookie pode ser limitado a HTTPS pela variável `SESSION_COOKIE_SECURE`.
- A aplicação envia Content Security Policy e outros cabeçalhos de proteção.
- Arquivos acima de 10 MB são recusados.
- O conteúdo do histórico é validado antes de qualquer cálculo.
- Erros internos são registrados no servidor sem exposição de detalhes ao usuário.
- A chave de sessão local fica em `instance/.secret_key`, diretório ignorado pelo Git.

Nunca publique chaves, arquivos `.env`, históricos privados ou o conteúdo do diretório `instance/`.

## Limitações

- Frequência histórica não indica maior chance de ocorrência futura.
- Nenhum filtro estatístico altera a probabilidade oficial do concurso.
- A aplicação não consulta resultados oficiais automaticamente.
- Os jogos não são registrados em loterias nem enviados para serviços externos.
- O usuário continua responsável pela conferência e pelo uso das combinações.

## Melhorias previstas

- Exportação dos jogos gerados em texto e CSV.
- Gráficos de frequência por dezena.
- Histórico local das últimas gerações.
- Quantidade configurável de jogos.
- Containerização com Docker.
- Configuração pronta para serviço `systemd` e Nginx.

## Autor

Desenvolvido por [Eduardo Miranda](https://github.com/EduMiranda78).

## Licença

Este repositório ainda não possui uma licença definida. Até que uma licença seja adicionada, o código permanece protegido pelos direitos autorais do autor.
