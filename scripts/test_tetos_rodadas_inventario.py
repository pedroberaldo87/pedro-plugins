#!/usr/bin/env python3
"""Testes do inventário de tetos por rodada (F16.3) — falha se a lógica quebrar."""
import os
import subprocess
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "_shared"))
sys.path.insert(0, AQUI)
import caminho_igual as ci  # noqa: E402
import tetos_rodadas_inventario as inv  # noqa: E402


class TestInventario(unittest.TestCase):
    def test_universo_vem_do_git_e_exclui_teste(self):
        arquivos = inv.universo()
        self.assertIn("plugins/project-skills/skills/sprint/references/motor.js", arquivos)
        self.assertFalse([a for a in arquivos if "test_" in os.path.basename(a)])
        self.assertFalse([a for a in arquivos
                          if os.path.basename(a) == "tetos_rodadas_inventario.py"])

    def test_todo_teto_achado_tem_veredito(self):
        itens, sem_veredito, orfaos = inv.julga(inv.varre(inv.universo()))
        self.assertEqual(sem_veredito, [], "teto novo sem veredito")
        self.assertEqual(orfaos, [], "veredito órfão")
        self.assertGreaterEqual(len(itens), 6)
        for i in itens:
            self.assertIn(i["situacao"], ("MIGRADO", "FICA"))
            self.assertTrue(i["justificativa"].strip())

    def test_maxrounds_do_sprint_esta_migrado(self):
        itens, _, _ = inv.julga(inv.varre(inv.universo()))
        sprint = [i for i in itens
                  if ci.termina_em(i["arquivo"], "sprint/references/motor.js")
                  and i["ident"] == "maxrounds"]
        self.assertEqual(len(sprint), 1)
        self.assertEqual(sprint[0]["situacao"], "MIGRADO")

    def test_definicao_pega_atribuicao_e_ignora_comparacao(self):
        self.assertTrue(inv.DEFINICAO.search("const maxRounds = ARGS.maxRounds || 12"))
        self.assertTrue(inv.DEFINICAO.search("def converge(dead, max_rounds=12):"))
        self.assertFalse(inv.DEFINICAO.search("if (rodadasMudas >= rodadasMudasMax)"))
        self.assertFalse(inv.DEFINICAO.search("while r < maxRounds:"))
        self.assertFalse(inv.DEFINICAO.search("if maxRounds == 3:"))

    def test_teto_sem_veredito_reprova(self):
        achado = [{"arquivo": "plugins/x/novo.py", "ident": "max_rounds",
                   "linha": 1, "texto": "max_rounds = 5"}]
        _, sem_veredito, _ = inv.julga(achado)
        self.assertEqual(len(sem_veredito), 1)

    def test_check_verde_no_repo_atual(self):
        r = subprocess.run([sys.executable, inv.__file__, "--check"],
                           capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, start_new_session=True)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
