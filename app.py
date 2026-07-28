from __future__ import annotations

import hmac
import logging
import os
import secrets
from pathlib import Path
from typing import BinaryIO, Iterable

import numpy as np
import pandas as pd
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.exceptions import RequestEntityTooLarge

BASE_DIR = Path(__file__).resolve().parent
COLUNAS = ["Bola1", "Bola2", "Bola3", "Bola4", "Bola5", "Bola6"]
EXTENSOES_PERMITIDAS = {".csv", ".xlsx"}
QUANTIDADE_PADRAO_JOGOS = 5
MAX_TENTATIVAS_GERACAO = 10_000

logger = logging.getLogger(__name__)


def _valor_booleano(nome: str, padrao: bool = False) -> bool:
    valor = os.environ.get(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in {"1", "true", "yes", "on", "sim"}


def _obter_chave_secreta(instance_path: str) -> str:
    """Obtém uma chave estável para sessões, preferindo SECRET_KEY."""
    chave_ambiente = os.environ.get("SECRET_KEY")
    if chave_ambiente:
        return chave_ambiente

    diretorio = Path(instance_path)
    arquivo = diretorio / ".secret_key"

    try:
        diretorio.mkdir(parents=True, exist_ok=True)
        if arquivo.is_file():
            chave = arquivo.read_text(encoding="utf-8").strip()
            if chave:
                return chave

        chave = secrets.token_hex(32)
        try:
            descritor = os.open(
                arquivo,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError:
            return arquivo.read_text(encoding="utf-8").strip()

        with os.fdopen(descritor, "w", encoding="utf-8") as destino:
            destino.write(chave)
        return chave
    except OSError:
        logger.warning(
            "Não foi possível persistir a chave de sessão. Defina SECRET_KEY no ambiente."
        )
        return secrets.token_hex(32)


def encontrar_arquivo_historico(diretorio: Path | str = BASE_DIR) -> Path | None:
    base = Path(diretorio)
    for nome in ("resultados.csv", "resultados.CSV"):
        caminho = base / nome
        if caminho.is_file():
            return caminho
    return None


def _normalizar_e_validar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ValueError("O arquivo histórico está vazio.")

    df = df.copy()
    df.columns = [str(coluna).replace("\ufeff", "").strip() for coluna in df.columns]

    if list(df.columns) != COLUNAS:
        esperado = ", ".join(COLUNAS)
        recebido = ", ".join(map(str, df.columns))
        raise ValueError(
            f"Colunas inválidas. Esperado: {esperado}. Recebido: {recebido}."
        )

    try:
        numeros = df.apply(pd.to_numeric, errors="raise")
    except (TypeError, ValueError) as erro:
        raise ValueError("O histórico contém valores que não são números.") from erro

    matriz = numeros.to_numpy(dtype=float)
    if not np.isfinite(matriz).all():
        raise ValueError("O histórico contém valores vazios ou inválidos.")

    if not np.equal(matriz, np.floor(matriz)).all():
        raise ValueError("Todos os números do histórico devem ser inteiros.")

    numeros = numeros.astype("int64")

    if not ((numeros >= 1) & (numeros <= 60)).all().all():
        raise ValueError("Todos os números devem estar no intervalo de 1 a 60.")

    linhas_com_repeticao = numeros.nunique(axis=1).ne(6)
    if linhas_com_repeticao.any():
        posicao = int(np.flatnonzero(linhas_com_repeticao.to_numpy())[0]) + 2
        raise ValueError(f"Há números repetidos na linha {posicao}.")

    matriz_ordenada = np.sort(numeros.to_numpy(), axis=1)
    return pd.DataFrame(matriz_ordenada, columns=COLUNAS)


def carregar_dataframe(
    fonte: Path | str | BinaryIO,
    nome_arquivo: str | None = None,
) -> pd.DataFrame:
    nome = nome_arquivo or str(fonte)
    extensao = Path(nome).suffix.lower()

    if extensao not in EXTENSOES_PERMITIDAS:
        raise ValueError("Envie apenas arquivos CSV ou XLSX.")

    try:
        if extensao == ".csv":
            df = pd.read_csv(
                fonte,
                sep=None,
                engine="python",
                encoding="utf-8-sig",
            )
        else:
            df = pd.read_excel(fonte, engine="openpyxl")
    except (OSError, UnicodeError, ValueError) as erro:
        raise ValueError("Não foi possível ler o arquivo histórico.") from erro

    return _normalizar_e_validar_dataframe(df)


def carregar_dataframe_do_disco(caminho: Path | str) -> pd.DataFrame:
    return carregar_dataframe(caminho)


def calcular_frequencias(df: pd.DataFrame) -> pd.Series:
    frequencias = pd.Series(df.to_numpy().ravel()).value_counts().sort_index()
    return frequencias.reindex(range(1, 61), fill_value=0).astype(int)


def jogo_valido(jogo: Iterable[int]) -> bool:
    numeros = [int(numero) for numero in jogo]
    pares = sum(numero % 2 == 0 for numero in numeros)
    soma = sum(numeros)
    return pares not in (0, 6) and 120 <= soma <= 210


def _formatar_jogo(jogo: Iterable[int]) -> list[str]:
    return [f"{int(numero):02d}" for numero in sorted(jogo)]


def gerar_uniforme(qtd: int = QUANTIDADE_PADRAO_JOGOS) -> list[list[str]]:
    if qtd < 1:
        raise ValueError("A quantidade de jogos deve ser maior que zero.")

    rng = np.random.default_rng()
    jogos: list[list[str]] = []
    combinacoes: set[tuple[int, ...]] = set()

    while len(jogos) < qtd:
        jogo = tuple(sorted(int(n) for n in rng.choice(range(1, 61), 6, replace=False)))
        if jogo in combinacoes:
            continue
        combinacoes.add(jogo)
        jogos.append(_formatar_jogo(jogo))

    return jogos


def gerar_ponderado(
    freq: pd.Series,
    qtd: int = QUANTIDADE_PADRAO_JOGOS,
) -> list[list[str]]:
    if qtd < 1:
        raise ValueError("A quantidade de jogos deve ser maior que zero.")

    frequencias = freq.reindex(range(1, 61), fill_value=0).astype(float)
    pesos = frequencias + 1.0
    probabilidades = pesos / pesos.sum()

    rng = np.random.default_rng()
    jogos: list[list[str]] = []
    combinacoes: set[tuple[int, ...]] = set()
    tentativas = 0

    while len(jogos) < qtd and tentativas < MAX_TENTATIVAS_GERACAO:
        tentativas += 1
        jogo = tuple(
            sorted(
                int(n)
                for n in rng.choice(
                    frequencias.index.to_numpy(),
                    6,
                    replace=False,
                    p=probabilidades.to_numpy(),
                )
            )
        )
        if jogo in combinacoes or not jogo_valido(jogo):
            continue
        combinacoes.add(jogo)
        jogos.append(_formatar_jogo(jogo))

    if len(jogos) != qtd:
        raise RuntimeError("Não foi possível gerar a quantidade solicitada de jogos.")

    return jogos


def montar_estatisticas(df: pd.DataFrame) -> dict[str, object]:
    freq = calcular_frequencias(df)
    numeros_quentes = freq.sort_values(ascending=False, kind="stable").head(10).to_dict()
    numeros_frios = freq.sort_values(ascending=True, kind="stable").head(10).to_dict()

    return {
        "total_sorteios": len(df),
        "frequencias": freq,
        "numeros_quentes": numeros_quentes,
        "numeros_frios": numeros_frios,
        "freq_max": max(numeros_quentes.values()),
        "freq_min": min(numeros_frios.values()),
    }


def create_app(configuracao_teste: dict[str, object] | None = None) -> Flask:
    app = Flask(
        __name__,
        instance_path=str(BASE_DIR / "instance"),
        instance_relative_config=True,
    )
    app.config.from_mapping(
        SECRET_KEY=_obter_chave_secreta(app.instance_path),
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,
        HISTORY_DIR=BASE_DIR,
        CSRF_ENABLED=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=_valor_booleano("SESSION_COOKIE_SECURE", False),
    )

    if configuracao_teste:
        app.config.update(configuracao_teste)

    @app.context_processor
    def disponibilizar_token_csrf() -> dict[str, object]:
        def csrf_token() -> str:
            token = session.get("_csrf_token")
            if not token:
                token = secrets.token_urlsafe(32)
                session["_csrf_token"] = token
            return str(token)

        return {"csrf_token": csrf_token}

    @app.before_request
    def validar_csrf():
        if not app.config.get("CSRF_ENABLED", True) or request.method != "POST":
            return None

        esperado = session.get("_csrf_token")
        recebido = request.form.get("_csrf_token") or request.headers.get("X-CSRF-Token")

        if (
            not esperado
            or not recebido
            or not hmac.compare_digest(str(esperado), str(recebido))
        ):
            session.pop("_csrf_token", None)
            flash("A sessão do formulário expirou. Tente novamente.", "warning")
            return redirect(url_for("index"))

        return None

    @app.after_request
    def adicionar_cabecalhos_seguranca(resposta):
        resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
        resposta.headers.setdefault("X-Frame-Options", "DENY")
        resposta.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resposta.headers.setdefault(
            "Permissions-Policy",
            "camera=(), geolocation=(), microphone=()",
        )
        resposta.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "font-src 'self' data:; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        )
        return resposta

    def contexto_do_historico() -> tuple[dict[str, object], pd.DataFrame | None]:
        arquivo = encontrar_arquivo_historico(app.config["HISTORY_DIR"])
        contexto: dict[str, object] = {
            "historico_local_existe": bool(arquivo),
            "modo": "uniforme",
        }

        if not arquivo:
            return contexto, None

        try:
            df = carregar_dataframe_do_disco(arquivo)
            estatisticas = montar_estatisticas(df)
            contexto.update({k: v for k, v in estatisticas.items() if k != "frequencias"})
            return contexto, df
        except ValueError as erro:
            logger.warning("Histórico local inválido: %s", erro)
            flash(f"Erro ao carregar histórico local: {erro}", "danger")
            contexto["historico_local_existe"] = False
            return contexto, None
        except Exception:
            logger.exception("Falha inesperada ao carregar o histórico local")
            flash("Erro inesperado ao carregar o histórico local.", "danger")
            contexto["historico_local_existe"] = False
            return contexto, None

    @app.get("/")
    def index():
        contexto, _ = contexto_do_historico()
        return render_template("index.html", **contexto)

    @app.post("/gerar")
    def gerar():
        modo = request.form.get("modo", "uniforme")
        if modo not in {"uniforme", "ponderado"}:
            flash("Modo de geração inválido.", "danger")
            return redirect(url_for("index"))

        arquivo_hist = encontrar_arquivo_historico(app.config["HISTORY_DIR"])

        try:
            if arquivo_hist:
                df = carregar_dataframe_do_disco(arquivo_hist)
            else:
                arquivo = request.files.get("arquivo")
                if not arquivo or not arquivo.filename:
                    raise ValueError("Nenhum arquivo foi enviado.")
                df = carregar_dataframe(arquivo.stream, arquivo.filename)

            estatisticas = montar_estatisticas(df)
            freq = estatisticas.pop("frequencias")
            jogos = (
                gerar_ponderado(freq)
                if modo == "ponderado"
                else gerar_uniforme()
            )
        except ValueError as erro:
            flash(str(erro), "danger")
            return redirect(url_for("index"))
        except RuntimeError as erro:
            logger.error("Falha ao gerar jogos: %s", erro)
            flash("Não foi possível gerar os jogos. Tente novamente.", "danger")
            return redirect(url_for("index"))
        except Exception:
            logger.exception("Falha inesperada durante a geração")
            flash("Ocorreu um erro inesperado ao processar o histórico.", "danger")
            return redirect(url_for("index"))

        return render_template(
            "index.html",
            jogos=jogos,
            modo=modo,
            historico_local_existe=bool(arquivo_hist),
            **estatisticas,
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    @app.errorhandler(RequestEntityTooLarge)
    def arquivo_muito_grande(_erro):
        flash("O arquivo excede o limite de 10 MB.", "danger")
        return redirect(url_for("index"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5080, debug=False)
