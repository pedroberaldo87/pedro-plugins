#!/usr/bin/env python3
"""public_repo_check.py — reprova dado pessoal em arquivo rastreado.

Este marketplace é PÚBLICO e é instalado por terceiros. Nada que identifique o dono,
a máquina dele, os clientes dele ou os sistemas privados dele pode entrar no índice
do git. Este script é o gate: ele varre `git ls-files` e falha se achar.

Uso:
    python3 scripts/public_repo_check.py              # varre tudo, exit 1 se achar
    python3 scripts/public_repo_check.py --staged     # só o que está staged (pre-commit)
    python3 scripts/public_repo_check.py --json
    python3 scripts/public_repo_check.py --so-estruturais   # CI público, sem lista de termos

A saída diz ONDE (arquivo:linha:coluna) e QUAL regra — nunca o trecho nem o casado. Um
gate que repete o segredo no log o espalha por onde o log for (transcrição, CI, chat).

O gate só diz "OK" quando mediu. Quando não mediu, ele fala:
  - git falhou ou não listou arquivo nenhum (varredura cheia)  → exit 2
  - arquivo rastreado que existe mas não abriu                  → exit 2, com o nome
  - scripts/public_repo_terms ausente (as regras de nome próprio, cliente e máquina
    NÃO rodaram):
      · com a variável CI definida → exit 3, a menos que se peça `--so-estruturais`;
      · local → aviso alto na saída padrão e exit 0 (a lista só mora na máquina do dono);
      · `--so-estruturais` → pedido explícito de quem sabe que não tem a lista (o CI do
        repositório público, que por desenho nunca recebe a lista): passa, mas a saída
        continua dizendo que os termos NÃO rodaram.

Isenção: uma linha ganha `# public-ok: <motivo>` (ou `<!-- public-ok: ... -->` em
markdown) e sai da conta. O motivo é obrigatório — isenção sem justificativa não vale.
Caminhos inteiros isentos vivem em scripts/public_repo_allow.txt, um glob por linha.
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOW_FILE = os.path.join(ROOT, "scripts", "public_repo_allow.txt")
TERMS_FILE = os.path.join(ROOT, "scripts", "public_repo_terms")

# ⚠️ NENHUM termo próprio (nome de pessoa, de cliente, de máquina, de sistema privado)
# mora neste arquivo — ele é VERSIONADO e público, e uma lista de clientes aqui dentro
# seria o vazamento que o gate existe pra impedir. Os termos vêm de `scripts/public_repo_terms`,
# que é gitignorado. Modelo: scripts/public_repo_terms.example.
#
# As regras abaixo são ESTRUTURAIS: valem para qualquer projeto, sem saber nome de ninguém.
REGRAS_ESTRUTURAIS = [
    # o lookbehind derruba $TMP/home/... e ${VAR}/Users/...; o (?![.<$]) derruba
    # /home/.claude (não é conta) e os placeholders /Users/<usuário>
    ("caminho-de-maquina",
     r"(?<![\w$}])/(?:Users|home)/(?![.<$])[A-Za-z0-9][A-Za-z0-9._-]*/"
     r"|C:\\\\Users\\\\[A-Za-z0-9][A-Za-z0-9._-]*",
     "caminho absoluto que revela o nome da conta",
     "usar ~ ou <raiz-do-projeto>"),
    ("email-pessoal",
     r"[A-Za-z0-9._%+-]+@(gmail|hotmail|outlook|yahoo|icloud|proton(mail)?)\.[A-Za-z.]{2,}",
     "e-mail pessoal",
     "usar o endereço de contato do projeto"),
    ("credencial",
     r"sk-ant-[A-Za-z0-9_-]{20,}|sk-proj-[A-Za-z0-9_-]{20,}|"
     r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|"
     r"AIza[0-9A-Za-z_-]{35}|xox[baprs]-[0-9A-Za-z-]{10,}|"
     r"-----BEGIN [A-Z ]*PRIVATE KEY|"
     r"(postgres|postgresql|mysql|mongodb\+srv|redis|amqp)://[^:/@ \n]+:[^@ \n]+@",
     "credencial",
     "nunca versionar — mover para o cofre"),
]

# ponytail: AKIA fora da lista de credencial — o exemplo publicado pela AWS
# (AKIAIOSFODNN7EXAMPLE) é fixture legítima do scrubber e daria falso positivo eterno.

ISENCAO = re.compile(r"public-ok:\s*(\S.*?)\s*(?:-->)?\s*$")
BINARIO = (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".ico", ".woff", ".woff2")

# Cada seção do arquivo de termos vira uma regra. O valor é (descrição, conserto).
SECOES = {
    "nome-proprio": ("nome próprio do dono", "trocar por 'o usuário' / 'quem instalou'"),
    "cliente-ou-sistema-interno": ("nome de cliente ou de sistema privado",
                                   "trocar por nome fictício"),
    "hostname-de-maquina": ("nome de máquina real", "usar host-a / host-b"),
}


def carrega_termos():
    """Lê scripts/public_repo_terms (gitignorado) → [(id, regex, oque, conserto)].

    Formato: `# <secao>` abre um bloco, um termo por linha. Termo com `!` no fim
    vira exceção (`Fulano!-plugins` = pega "Fulano" mas nao "Fulano-plugins").
    Arquivo ausente → nenhuma regra de termo, e o gate diz que elas NÃO rodaram (ver main).
    """
    if not os.path.exists(TERMS_FILE):
        return [], False
    secao, por_secao = None, {}
    with open(TERMS_FILE, encoding="utf-8") as fh:
        for linha in fh:
            linha = linha.strip()
            if not linha:
                continue
            if linha.startswith("#"):
                cand = linha.lstrip("#").strip()
                secao = cand if cand in SECOES else None
                continue
            if secao:
                por_secao.setdefault(secao, []).append(linha)
    regras = []
    for secao, termos in por_secao.items():
        alts = []
        for t in termos:
            corpo, _, excecao = t.partition("!")
            alt = re.escape(corpo)
            if excecao:
                alt += r"(?!%s)" % re.escape(excecao)
            alts.append(alt)
        oque, conserto = SECOES[secao]
        regras.append((secao, r"(?i)\b(?:%s)\b" % "|".join(alts), oque, conserto))
    return regras, True


REGRAS_TERMOS, TEM_TERMOS = carrega_termos()
REGRAS = REGRAS_TERMOS + REGRAS_ESTRUTURAIS


def carrega_allow():
    if not os.path.exists(ALLOW_FILE):
        return []
    globs = []
    with open(ALLOW_FILE, encoding="utf-8") as fh:
        for linha in fh:
            linha = linha.split("#")[0].strip()
            if linha:
                globs.append(linha)
    return globs


class ErroGit(Exception):
    """git não respondeu: sem lista de arquivos não há o que dizer, nem 'OK'."""


def arquivos(staged):
    # `-z`: sem ele o git CITA nome com não-ASCII, tab, aspas ou barra invertida
    # ("relat\\303\\263rio.md"), o isfile() falhava e o arquivo saía da conta sem aviso.
    cmd = ["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"] if staged \
        else ["git", "ls-files", "-z"]
    try:
        out = subprocess.run(cmd, cwd=ROOT, capture_output=True,
                             stdin=subprocess.DEVNULL, start_new_session=True)
    except OSError as e:
        raise ErroGit("não consegui rodar git: %s" % e)
    if out.returncode != 0:
        raise ErroGit("`%s` saiu com %d: %s" % (" ".join(cmd), out.returncode,
                      out.stderr.decode("utf-8", "replace").strip()[:200]))
    return [os.fsdecode(p) for p in out.stdout.split(b"\0") if p]


def varre_com_notas(staged=False):
    """→ (achados, notas). `notas` conta o que NÃO foi medido; nada some calado."""
    allow = carrega_allow()
    achados = []
    notas = {"lista": 0, "ilegiveis": [], "nao_utf8": 0, "ausentes": 0}
    lista = arquivos(staged)
    notas["lista"] = len(lista)
    for path in lista:
        if any(fnmatch.fnmatch(path, g) for g in allow):
            continue
        if path.lower().endswith(BINARIO):
            continue
        full = os.path.join(ROOT, path)
        if not os.path.lexists(full):
            notas["ausentes"] += 1  # rastreado, apagado do disco: nada a ler
            continue
        if not os.path.isfile(full):
            continue  # submódulo ou pasta: sem conteúdo próprio
        try:
            with open(full, encoding="utf-8") as fh:
                linhas = fh.readlines()
        except UnicodeDecodeError:
            notas["nao_utf8"] += 1  # binário com extensão que não está em BINARIO
            continue
        except OSError:
            notas["ilegiveis"].append(path)
            continue
        for n, linha in enumerate(linhas, 1):
            if ISENCAO.search(linha):
                continue
            for rid, padrao, oque, conserto in REGRAS:
                m = re.search(padrao, linha)
                if m:
                    # só o LUGAR e a regra: nem o casado nem a linha — ver o docstring
                    achados.append({
                        "file": path, "line": n, "col": m.start() + 1, "rule": rid,
                        "what": oque, "fix": conserto,
                    })
                    break
    return achados, notas


def varre(staged=False):
    return varre_com_notas(staged)[0]


def em_ci():
    return os.environ.get("CI", "").strip().lower() not in ("", "0", "false", "no")


def seguro(texto):
    """Caminho com byte inválido ou fora do console (cp1252) não pode derrubar o relatório."""
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    return texto.encode(enc, "backslashreplace").decode(enc)


AVISO_TERMOS = (
    "⚠️  TERMOS NÃO RODARAM — scripts/public_repo_terms ausente.\n"
    "    Só as regras estruturais (caminho de máquina, e-mail pessoal, credencial) foram\n"
    "    aplicadas. Nome de pessoa, de cliente e de máquina NÃO foram procurados.\n"
    "    Copie scripts/public_repo_terms.example e preencha."
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--so-estruturais", action="store_true",
                    help="não exige scripts/public_repo_terms (CI público, que nunca "
                         "recebe a lista); a saída continua dizendo que os termos não rodaram")
    args = ap.parse_args()

    try:
        achados, notas = varre_com_notas(args.staged)
    except ErroGit as e:
        print("public-repo-check: NÃO MEDIDO — %s" % seguro(str(e)))
        return 2

    sem_lista = not args.staged and notas["lista"] == 0
    termos_ok = TEM_TERMOS
    # exit 3 = a medição foi parcial e o ambiente (CI) não aceita parcial sem pedido
    exige_termos = em_ci() and not args.so_estruturais
    nao_medido = bool(notas["ilegiveis"]) or sem_lista

    if args.json:
        print(json.dumps({
            "ok": not achados and not nao_medido and (termos_ok or not exige_termos),
            "count": len(achados), "terms_checked": termos_ok,
            "unreadable": [seguro(p) for p in notas["ilegiveis"]],
            "findings": achados}, ensure_ascii=False, indent=1))
        if achados:
            return 1
        if nao_medido:
            return 2
        return 3 if (not termos_ok and exige_termos) else 0

    if not termos_ok:
        print(AVISO_TERMOS)
        if args.so_estruturais:
            print("    (pedido explícito: --so-estruturais)")
        print()

    if notas["ilegiveis"] or sem_lista:
        print("public-repo-check: NÃO MEDIDO por inteiro")
        for p in notas["ilegiveis"]:
            print("  arquivo rastreado que não abriu: %s" % seguro(p))
        if sem_lista:
            print("  git não listou arquivo nenhum")
        print()

    if achados:
        por_regra = {}
        for a in achados:
            por_regra.setdefault(a["rule"], []).append(a)

        print("public-repo-check: %d ocorrência(s) em %d arquivo(s)\n"
              % (len(achados), len({a["file"] for a in achados})))
        for rid, itens in sorted(por_regra.items(), key=lambda kv: -len(kv[1])):
            print("  %s — %s (%d)" % (rid, itens[0]["what"], len(itens)))
            print("    conserto: %s" % itens[0]["fix"])
            for a in itens[:5]:
                print("      %s:%d:%d" % (seguro(a["file"]), a["line"], a["col"]))
            if len(itens) > 5:
                print("      … mais %d" % (len(itens) - 5))
            print()
        print("O trecho não é repetido aqui (o log não pode virar cópia do segredo): abra o")
        print("arquivo na linha indicada.")
        print("Isenção legítima: acrescente `public-ok: <motivo>` na linha,")
        print("ou um glob de caminho em scripts/public_repo_allow.txt.")
        return 1

    if notas["ilegiveis"] or sem_lista:
        return 2

    if notas["nao_utf8"]:
        print("nota: %d arquivo(s) não-UTF-8 não foram lidos (tratados como binário)"
              % notas["nao_utf8"])
    if not termos_ok:
        if exige_termos:
            print("public-repo-check: FALHOU — a variável CI está definida e as regras de "
                  "termo não rodaram.")
            print("  Rode com --so-estruturais se este ambiente nunca recebe a lista.")
            return 3
        print("public-repo-check: estruturais OK — as regras de termo NÃO rodaram "
              "(não é um OK completo)")
        return 0
    print("public-repo-check: OK — nenhum dado pessoal em arquivo rastreado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
