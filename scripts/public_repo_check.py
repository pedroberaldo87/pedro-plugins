#!/usr/bin/env python3
"""public_repo_check.py — reprova dado pessoal em arquivo rastreado.

Este marketplace é PÚBLICO e é instalado por terceiros. Nada que identifique o dono,
a máquina dele, os clientes dele ou os sistemas privados dele pode entrar no índice
do git. Este script é o gate: ele varre `git ls-files` e falha se achar.

Uso:
    python3 scripts/public_repo_check.py              # varre tudo, exit 1 se achar
    python3 scripts/public_repo_check.py --staged     # só o que está staged (pre-commit)
    python3 scripts/public_repo_check.py --json

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
    Arquivo ausente → nenhuma regra de termo, e o gate avisa em vez de fingir que passou.
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


def arquivos(staged):
    cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"] if staged \
        else ["git", "ls-files"]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
    return [p for p in out.stdout.splitlines() if p]


def varre(staged=False):
    allow = carrega_allow()
    achados = []
    for path in arquivos(staged):
        if any(fnmatch.fnmatch(path, g) for g in allow):
            continue
        if path.lower().endswith(BINARIO):
            continue
        full = os.path.join(ROOT, path)
        if not os.path.isfile(full):
            continue
        try:
            with open(full, encoding="utf-8") as fh:
                linhas = fh.readlines()
        except (UnicodeDecodeError, OSError):
            continue
        for n, linha in enumerate(linhas, 1):
            if ISENCAO.search(linha):
                continue
            for rid, padrao, oque, conserto in REGRAS:
                m = re.search(padrao, linha)
                if m:
                    achados.append({
                        "file": path, "line": n, "rule": rid,
                        "match": m.group(0)[:40], "what": oque, "fix": conserto,
                        "excerpt": linha.strip()[:120],
                    })
                    break
    return achados


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    achados = varre(args.staged)

    if args.json:
        print(json.dumps({"ok": not achados, "count": len(achados),
                          "findings": achados}, ensure_ascii=False, indent=1))
        return 1 if achados else 0

    if not TEM_TERMOS:
        print("⚠️  scripts/public_repo_terms ausente — rodando SÓ as regras\n"
              "    estruturais. Nome de pessoa, de cliente e de máquina NÃO foram\n"
              "    procurados. Copie scripts/public_repo_terms.example e preencha.",
              file=sys.stderr)

    if not achados:
        print("public-repo-check: OK — nenhum dado pessoal em arquivo rastreado")
        return 0

    por_regra = {}
    for a in achados:
        por_regra.setdefault(a["rule"], []).append(a)

    print("public-repo-check: %d ocorrência(s) em %d arquivo(s)\n"
          % (len(achados), len({a["file"] for a in achados})))
    for rid, itens in sorted(por_regra.items(), key=lambda kv: -len(kv[1])):
        print("  %s — %s (%d)" % (rid, itens[0]["what"], len(itens)))
        print("    conserto: %s" % itens[0]["fix"])
        for a in itens[:5]:
            print("      %s:%d  %s" % (a["file"], a["line"], a["excerpt"]))
        if len(itens) > 5:
            print("      … mais %d" % (len(itens) - 5))
        print()
    print("Isenção legítima: acrescente `public-ok: <motivo>` na linha,")
    print("ou um glob de caminho em scripts/public_repo_allow.txt.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
