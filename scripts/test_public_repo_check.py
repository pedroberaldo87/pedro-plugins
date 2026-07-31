#!/usr/bin/env python3
"""Checagem do public_repo_check.py — o gate que impede dado pessoal de subir.

Nenhum termo real aparece neste arquivo. Ele é versionado e público: escrever aqui
a lista de nomes que o gate procura seria o vazamento que o gate existe pra impedir.
Os termos de teste são fictícios, gravados num arquivo temporário e carregados dele.

As strings que casam as regras ESTRUTURAIS são montadas por concatenação — o gate lê
linha a linha, então "fulano@" + "g" + "mail.com" não dispara ao varrer este próprio arquivo.
"""
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import public_repo_check as G  # noqa: E402

ok = 0

TERMOS_FICTICIOS = """
# nome-proprio
Fulano!-plugins
Sobrenome

# cliente-ou-sistema-interno
cliente-alfa
SISTEMA-BETA
tabela_gama

# hostname-de-maquina
maquina-de-casa
"""


def check(nome, cond):
    global ok
    assert cond, "FALHOU: %s" % nome
    ok += 1


def casa(regras, rid, texto):
    for r, padrao, _, _ in regras:
        if r == rid:
            return bool(re.search(padrao, texto))
    raise AssertionError("regra inexistente: %s" % rid)


# ─── termos: carregados de arquivo, nunca do código ──────────────────────────
with tempfile.NamedTemporaryFile("w", suffix=".terms", delete=False,
                                 encoding="utf-8") as fh:
    fh.write(TERMOS_FICTICIOS)
    tmp_terms = fh.name

_orig = G.TERMS_FILE
G.TERMS_FILE = tmp_terms
regras_termo, tem = G.carrega_termos()
G.TERMS_FILE = _orig
regras = regras_termo + G.REGRAS_ESTRUTURAIS

check("arquivo de termos presente vira True", tem)
check("as 3 secoes viraram regra", {r[0] for r in regras_termo} == {
    "nome-proprio", "cliente-ou-sistema-interno", "hostname-de-maquina"})
check("nenhuma regra de termo no codigo versionado", G.REGRAS_ESTRUTURAIS and all(
    r[0] not in ("nome-proprio", "cliente-ou-sistema-interno", "hostname-de-maquina")
    for r in G.REGRAS_ESTRUTURAIS))

# ausente → nenhuma regra de termo, e o chamador sabe disso
G.TERMS_FILE = os.path.join(tempfile.gettempdir(), "nao-existe-mesmo.terms")
vazio, tem_nao = G.carrega_termos()
G.TERMS_FILE = _orig
check("sem arquivo, zero regra de termo", vazio == [])
check("sem arquivo, o flag avisa", tem_nao is False)

# ─── nome próprio: pega a pessoa, respeita a exceção ─────────────────────────
check("pega o nome", casa(regras, "nome-proprio", "veja se o Fulano perde informacao"))
check("pega o sobrenome", casa(regras, "nome-proprio", '"name": "Fulano Sobrenome"'))
check("case-insensitive", casa(regras, "nome-proprio", "o FULANO decide"))
check("excecao protege o projeto", not casa(regras, "nome-proprio", "instale o Fulano-plugins"))

# ─── cliente e máquina ───────────────────────────────────────────────────────
check("pega cliente", casa(regras, "cliente-ou-sistema-interno", "a grade do cliente-alfa"))
check("pega sistema", casa(regras, "cliente-ou-sistema-interno", "no SISTEMA-BETA isso quebra"))
check("pega tabela", casa(regras, "cliente-ou-sistema-interno", "a tabela_gama herda"))
check("pega hostname", casa(regras, "hostname-de-maquina", "commit @ maquina-de-casa"))
check("nao pega palavra alheia", not casa(regras, "cliente-ou-sistema-interno", "o cliente ligou"))

# ─── estruturais: valem sem saber nome de ninguém ────────────────────────────
U, H = "/Users/", "/home/"
check("pega conta em /Users", casa(regras, "caminho-de-maquina", 'root: "%sfulano/PROJ"' % U))
check("pega conta em /home", casa(regras, "caminho-de-maquina", "cd %sfulano/app" % H))
check("ignora var de ambiente", not casa(regras, "caminho-de-maquina", '"$TMP%s.claude/g"' % H))
check("ignora interpolacao", not casa(regras, "caminho-de-maquina", "${VAR}%sshare/x" % U))
check("ignora placeholder", not casa(regras, "caminho-de-maquina", "salvo em %s<usuario>/x" % U))

check("pega provedor pessoal", casa(regras, "email-pessoal", "owner: fulano@" + "g" + "mail.com"))
check("ignora dominio proprio", not casa(regras, "email-pessoal", "owner: tools" + "@empresa.com.br"))

check("pega token de host git", casa(regras, "credencial", "T=gh" + "p_" + "a" * 36))
check("pega chave privada", casa(regras, "credencial", "-----BEGIN RSA PRIVATE" + " KEY-----"))
check("pega senha em url", casa(regras, "credencial", "postgres://u:senha" + "@host/db"))
check("ignora o exemplo publicado pela AWS", not casa(regras, "credencial", "AKIA" + "IOSFODNN7EXAMPLE"))

# ─── isenção só vale com motivo escrito ──────────────────────────────────────
check("isencao com motivo isenta", G.ISENCAO.search("x = 1  # public" + "-ok: fixture"))
check("isencao em markdown isenta", G.ISENCAO.search("txt <!-- public" + "-ok: registro -->"))
check("isencao sem motivo NAO isenta", not G.ISENCAO.search("x = 1  # public" + "-ok:"))

# ─── o gate roda de verdade no repo ──────────────────────────────────────────
achados = G.varre()
check("varre() devolve lista", isinstance(achados, list))
if achados:
    check("achado tem os campos que o conserto exige",
          all(k in achados[0] for k in ("file", "line", "rule", "fix", "excerpt")))

os.unlink(tmp_terms)
print("test_public_repo_check: %d asserts ok ✓  (repo: %d ocorrência(s) hoje)"
      % (ok, len(achados)))
