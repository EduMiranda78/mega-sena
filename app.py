import os
from flask import Flask, render_template, request, flash, redirect, url_for
import pandas as pd
import numpy as np

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(32))

COLUNAS = ["Bola1", "Bola2", "Bola3", "Bola4", "Bola5", "Bola6"]

def encontrar_arquivo_historico():
    for nome in ["resultados.csv", "resultados.CSV"]:
        if os.path.isfile(nome):
            return nome
    return None

def carregar_dataframe_do_disco(caminho):
    ext = os.path.splitext(caminho.lower())[1]
    if ext == ".csv":
        df = pd.read_csv(caminho, sep=";")
    else:
        df = pd.read_excel(caminho)

    if list(df.columns) != COLUNAS:
        raise ValueError("Colunas inválidas")

    df = df.astype(int)
    if not ((df >= 1) & (df <= 60)).all().all():
        raise ValueError("Valores fora do intervalo 1–60")
    return df

def calcular_frequencias(df):
    return pd.Series(df.values.flatten()).value_counts().sort_index()

def jogo_valido(jogo):
    pares = sum(n % 2 == 0 for n in jogo)
    soma = sum(jogo)
    if pares in (0, 6):
        return False
    if not (120 <= soma <= 210):
        return False
    return True

def gerar_uniforme(qtd=5):
    rng = np.random.default_rng()
    jogos = []
    while len(jogos) < qtd:
        jogo = sorted(rng.choice(range(1, 61), 6, replace=False))
        if jogo_valido(jogo):
            jogos.append([f"{n:02d}" for n in jogo])
    return jogos

def gerar_ponderado(freq, qtd=5):
    rng = np.random.default_rng()
    pesos = freq / freq.sum()
    jogos = []
    while len(jogos) < qtd:
        jogo = sorted(rng.choice(freq.index, 6, replace=False, p=pesos.values))
        if jogo_valido(jogo):
            jogos.append([f"{n:02d}" for n in jogo])
    return jogos

@app.route("/")
def index():
    arquivo_hist = encontrar_arquivo_historico()
    contexto = {"historico_local_existe": bool(arquivo_hist)}

    if arquivo_hist:
        try:
            df = carregar_dataframe_do_disco(arquivo_hist)
            total_sorteios = len(df)
            freq = calcular_frequencias(df)
            numeros_quentes = freq.sort_values(ascending=False).head(10).to_dict()
            numeros_frios = freq.sort_values().head(10).to_dict()
            freq_max = max(numeros_quentes.values())
            freq_min = min(numeros_frios.values())

            contexto.update({
                "total_sorteios": total_sorteios,
                "numeros_quentes": numeros_quentes,
                "numeros_frios": numeros_frios,
                "freq_max": freq_max,
                "freq_min": freq_min,
            })
        except Exception as e:
            flash(f"Erro ao carregar histórico local: {str(e)}", "danger")
            contexto["historico_local_existe"] = False

    return render_template("index.html", **contexto)


@app.route("/gerar", methods=["POST"])
def gerar():
    modo = request.form.get("modo", "uniforme")
    arquivo_hist = encontrar_arquivo_historico()

    if arquivo_hist:
        # Usa o arquivo do disco sempre que disponível
        try:
            df = carregar_dataframe_do_disco(arquivo_hist)
        except Exception:
            flash("Erro ao ler o arquivo de histórico local.", "danger")
            return redirect(url_for("index"))
    else:
        # Caso contrário, exige upload
        arquivo = request.files.get("arquivo")
        if not arquivo or arquivo.filename == "":
            flash("Nenhum arquivo enviado", "danger")
            return redirect(url_for("index"))

        ext = os.path.splitext(arquivo.filename.lower())[1]
        if ext not in {".csv", ".xlsx"}:
            flash("Envie apenas arquivos CSV ou XLSX", "danger")
            return redirect(url_for("index"))

        try:
            if ext == ".csv":
                df = pd.read_csv(arquivo, sep=";")
            else:
                df = pd.read_excel(arquivo)

            if list(df.columns) != COLUNAS:
                raise ValueError("Colunas inválidas")
            df = df.astype(int)
            if not ((df >= 1) & (df <= 60)).all().all():
                raise ValueError("Valores fora do intervalo 1–60")
        except Exception:
            flash("Erro ao processar o arquivo", "danger")
            return redirect(url_for("index"))

    # Geração de jogos
    total_sorteios = len(df)
    freq = calcular_frequencias(df)

    if modo == "ponderado":
        jogos = gerar_ponderado(freq)
    else:
        jogos = gerar_uniforme()

    numeros_quentes = freq.sort_values(ascending=False).head(10).to_dict()
    numeros_frios = freq.sort_values().head(10).to_dict()
    freq_max = max(numeros_quentes.values())
    freq_min = min(numeros_frios.values())

    return render_template(
        "index.html",
        jogos=jogos,
        total_sorteios=total_sorteios,
        numeros_quentes=numeros_quentes,
        numeros_frios=numeros_frios,
        freq_max=freq_max,
        freq_min=freq_min,
        modo=modo,
        historico_local_existe=bool(arquivo_hist),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5080, debug=False)