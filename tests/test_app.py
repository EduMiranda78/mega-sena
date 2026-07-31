import io
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from app import (
    COLUNAS,
    calcular_frequencias,
    carregar_dataframe,
    create_app,
    gerar_ponderado,
    gerar_uniforme,
    jogo_valido,
)


class MegaSenaTestCase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "CSRF_ENABLED": False,
                "HISTORY_DIR": Path(self.tempdir.name),
                "SECRET_KEY": "test-secret-key",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.tempdir.cleanup()

    @staticmethod
    def csv_bytes(linhas: list[list[int]]) -> io.BytesIO:
        df = pd.DataFrame(linhas, columns=COLUNAS)
        conteudo = df.to_csv(index=False, sep=";").encode("utf-8")
        return io.BytesIO(conteudo)

    def test_carrega_csv_valido_e_ordena_dezenas(self):
        df = carregar_dataframe(self.csv_bytes([[60, 1, 20, 15, 8, 42]]), "dados.csv")
        self.assertEqual(df.iloc[0].tolist(), [1, 8, 15, 20, 42, 60])

    def test_rejeita_numero_repetido_na_mesma_linha(self):
        with self.assertRaisesRegex(ValueError, "números repetidos"):
            carregar_dataframe(self.csv_bytes([[1, 1, 2, 3, 4, 5]]), "dados.csv")

    def test_rejeita_numero_fora_do_intervalo(self):
        with self.assertRaisesRegex(ValueError, "intervalo de 1 a 60"):
            carregar_dataframe(self.csv_bytes([[0, 2, 3, 4, 5, 6]]), "dados.csv")

    def test_frequencias_contem_todas_as_dezenas(self):
        df = pd.DataFrame([[1, 2, 3, 4, 5, 6]], columns=COLUNAS)
        frequencias = calcular_frequencias(df)
        self.assertEqual(len(frequencias), 60)
        self.assertEqual(frequencias.loc[1], 1)
        self.assertEqual(frequencias.loc[60], 0)

    def test_geracao_uniforme_cria_jogos_unicos(self):
        jogos = gerar_uniforme(20)
        self.assertEqual(len(jogos), 20)
        self.assertEqual(len({tuple(jogo) for jogo in jogos}), 20)
        for jogo in jogos:
            numeros = [int(numero) for numero in jogo]
            self.assertEqual(len(set(numeros)), 6)
            self.assertTrue(all(1 <= numero <= 60 for numero in numeros))

    def test_geracao_ponderada_cria_jogos_validos_e_unicos(self):
        frequencias = pd.Series(1, index=range(1, 61))
        jogos = gerar_ponderado(frequencias, 10)
        self.assertEqual(len(jogos), 10)
        self.assertEqual(len({tuple(jogo) for jogo in jogos}), 10)
        for jogo in jogos:
            self.assertTrue(jogo_valido(int(numero) for numero in jogo))

    def test_pagina_inicial_responde(self):
        resposta = self.client.get("/")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"Mega Sena Master", resposta.data)
        self.assertIn(b"/static/styles.css", resposta.data)

    def test_folha_de_estilos_responde(self):
        resposta = self.client.get("/static/styles.css")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"--primary", resposta.data)

    def test_upload_csv_gera_cinco_jogos(self):
        dados = {
            "modo": "uniforme",
            "arquivo": (self.csv_bytes([[1, 2, 3, 4, 5, 6]]), "dados.csv"),
        }
        resposta = self.client.post("/gerar", data=dados, content_type="multipart/form-data")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Seus 5 Jogos".encode("utf-8"), resposta.data)

    def test_healthcheck(self):
        resposta = self.client.get("/health")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
