# Mega Sena Master

Aplicação Flask para analisar um histórico de concursos e gerar cinco combinações de seis dezenas.

## Aviso

A aplicação não prevê resultados e não aumenta a probabilidade matemática de acerto. O modo ponderado apenas usa a frequência observada no arquivo histórico. Jogue com responsabilidade.

## Requisitos

- Python 3.12 ou superior
- Arquivo histórico CSV ou XLSX

## Instalação

```bash
cd ~/mega-sena
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Estrutura esperada do histórico

O arquivo deve conter exatamente estas colunas:

```text
Bola1;Bola2;Bola3;Bola4;Bola5;Bola6
```

Cada linha deve ter seis números inteiros, distintos, entre 1 e 60. CSV com vírgula ou ponto e vírgula é aceito. Arquivos XLSX também são aceitos.

Quando `resultados.csv` estiver na raiz do projeto, ele será carregado automaticamente. Sem esse arquivo, a interface solicitará um upload.

## Executar para desenvolvimento

```bash
source .venv/bin/activate
python app.py
```

A aplicação ficará disponível em:

```text
http://IP-DA-VPS:5080
```

## Executar com Gunicorn

Defina uma chave de sessão própria e inicie o servidor:

```bash
cd ~/mega-sena
source .venv/bin/activate
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
gunicorn --workers 2 --bind 0.0.0.0:5080 --access-logfile - --error-logfile - app:app
```

Sem `SECRET_KEY`, a aplicação cria uma chave local em `instance/.secret_key`. Esse diretório não deve ser enviado ao Git.

Para uso atrás de HTTPS, configure também:

```bash
export SESSION_COOKIE_SECURE=true
```

## Verificação de funcionamento

```bash
curl -fsS http://127.0.0.1:5080/health
```

Resposta esperada:

```json
{"status":"ok"}
```

## Testes

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
```

## Principais proteções

- limite de upload de 10 MB
- validação de colunas, tipos, faixa e repetições
- proteção CSRF no formulário
- cookies de sessão protegidos
- cabeçalhos HTTP de segurança
- mensagens de erro sem detalhes internos
- jogos gerados sem duplicidade na mesma execução
