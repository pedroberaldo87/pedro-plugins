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

O gate só diz "OK" quando mediu. Códigos de saída:
  0  mediu tudo e nada achou (ou: só as regras estruturais, avisando em voz alta que os
     termos NÃO rodaram — local, sem scripts/public_repo_terms)
  1  achou dado pessoal
  2  NÃO MEDIDO — git falhou ou não listou arquivo nenhum (varredura cheia), arquivo
     rastreado que existe mas não abriu, ou arquivo de termos ilegível (UTF-8 inválido)
  3  os termos não rodaram e o ambiente não aceita isso: variável CI definida, a menos
     que se peça `--so-estruturais`
Os termos "não rodaram" quando scripts/public_repo_terms está ausente, vazio, sem nenhuma
seção válida (cabeçalho errado) ou tem linha de termo fora de seção válida. O BOM de
UTF-8 (Notepad) é aceito: o arquivo é lido como `utf-8-sig`. `--so-estruturais` é pedido explícito de quem sabe
que não tem a lista (o CI do repositório público, que por desenho nunca a recebe): passa,
mas a saída continua dizendo que os termos NÃO rodaram.

Arquivo rastreado que não é UTF-8 não é pulado: UTF-16 com BOM é decodificado; o resto cai
para latin-1 e é varrido; só binário de verdade (byte NUL) é ignorado. A saída conta os
três casos. `--staged` lê o conteúdo do ÍNDICE (`git show :caminho`), não o da pasta.

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


def carrega_termos_estado():
    """Lê scripts/public_repo_terms (gitignorado) → (regras, estado, linhas).

    Formato: `# <secao>` abre um bloco, um termo por linha. Termo com `!` no fim
    vira exceção (`Fulano!-plugins` = pega "Fulano" mas nao "Fulano-plugins").

    `estado`: "ok" | "ausente" | "ilegivel" (não abre ou não é UTF-8) | "sem-regras"
    (existe mas nenhuma seção válida: vazio, cabeçalho errado) | "parcial" (há regra, mas
    sobrou linha de termo fora de seção válida). `linhas`: números das linhas de termo
    ignoradas — só o número, nunca o conteúdo. Só "ok" conta como termos rodados.
    """
    if not os.path.exists(TERMS_FILE):
        return [], "ausente", []
    secao, por_secao, ignoradas = None, {}, []
    try:
        with open(TERMS_FILE, encoding="utf-8-sig") as fh:  # BOM do Notepad é do arquivo, não do cabeçalho
            for n, linha in enumerate(fh, 1):
                linha = linha.strip()
                if not linha:
                    continue
                if linha.startswith("#"):
                    cand = linha.lstrip("#").strip()
                    secao = cand if cand in SECOES else None
                    continue
                if secao:
                    por_secao.setdefault(secao, []).append(linha)
                else:
                    ignoradas.append(n)
    except (OSError, UnicodeDecodeError):
        return [], "ilegivel", []
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
    if not regras:
        return [], "sem-regras", ignoradas
    return regras, ("parcial" if ignoradas else "ok"), ignoradas


def carrega_termos():
    """→ (regras, rodaram). `rodaram` só é True quando o arquivo deu regra para valer."""
    regras, estado, _ = carrega_termos_estado()
    return regras, estado == "ok"


REGRAS_TERMOS, ESTADO_TERMOS, LINHAS_TERMOS_IGNORADAS = carrega_termos_estado()
TEM_TERMOS = ESTADO_TERMOS == "ok"
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


def le_bytes(path, staged):
    """Os bytes do que seria publicado, ou levanta OSError.

    --staged lê o ÍNDICE (`git show :caminho`): arquivo parcialmente staged (`git add -p`)
    é julgado pelo que vai no commit, não pelo que está na pasta. Symlink vira o texto do
    alvo: o git só guarda isso, e seguir o link leria arquivo de fora do repositório.
    """
    if staged:
        r = subprocess.run(["git", "show", ":" + path], cwd=ROOT, capture_output=True,
                           stdin=subprocess.DEVNULL, start_new_session=True)
        if r.returncode != 0:
            raise OSError("git show falhou")
        return r.stdout
    full = os.path.join(ROOT, path)
    if os.path.islink(full):
        return os.fsencode(os.readlink(full))
    with open(full, "rb") as fh:
        return fh.read()


def decodifica(dados):
    """→ (texto, como) | (None, "binario"). `como`: utf-8 | utf-16 | latin-1.

    Pular o arquivo não-UTF-8 deixava passar UTF-16 (o que editor de Windows grava) e
    latin-1. Agora: UTF-16 com BOM decodifica; o resto cai para latin-1 (nunca falha) e é
    varrido; só byte NUL sem BOM (binário de verdade) é ignorado — e contado.
    """
    if dados[:2] in (b"\xff\xfe", b"\xfe\xff"):
        try:
            return dados.decode("utf-16"), "utf-16"
        except UnicodeDecodeError:
            pass
    try:
        return dados.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    if b"\0" in dados:
        return None, "binario"
    return dados.decode("latin-1"), "latin-1"


def varre_com_notas(staged=False):
    """→ (achados, notas). `notas` conta o que NÃO foi medido; nada some calado."""
    allow = carrega_allow()
    achados = []
    notas = {"lista": 0, "ilegiveis": [], "nao_utf8": 0, "binarios": 0, "ausentes": 0}
    lista = arquivos(staged)
    notas["lista"] = len(lista)
    for path in lista:
        if any(fnmatch.fnmatch(path, g) for g in allow):
            continue
        if path.lower().endswith(BINARIO):
            continue
        full = os.path.join(ROOT, path)
        if not staged:
            if not os.path.lexists(full):
                notas["ausentes"] += 1  # rastreado, apagado do disco: nada a ler
                continue
            if not os.path.islink(full) and not os.path.isfile(full):
                continue  # submódulo ou pasta: sem conteúdo próprio
        try:
            dados = le_bytes(path, staged)
        except OSError:
            notas["ilegiveis"].append(path)
            continue
        texto, como = decodifica(dados)
        if texto is None:
            notas["binarios"] += 1  # byte NUL, extensão que não está em BINARIO
            continue
        if como == "latin-1":
            notas["nao_utf8"] += 1  # varrido mesmo assim, só que como latin-1
        for n, linha in enumerate(re.split(r"\r\n|\r|\n", texto), 1):
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

# estado do arquivo de termos → o que dizer quando ele existe mas não valeu
MOTIVO_TERMOS = {
    "ausente": "scripts/public_repo_terms ausente.",
    "sem-regras": "scripts/public_repo_terms existe mas não tem nenhuma seção válida "
                  "(vazio ou cabeçalho fora de: %s)." % ", ".join(SECOES),
    "parcial": "scripts/public_repo_terms tem linha de termo fora de seção válida "
               "(cabeçalho errado?), que não foi procurada.",
    "ilegivel": "scripts/public_repo_terms não abriu ou não é UTF-8 válido.",
}


def aviso_termos():
    if ESTADO_TERMOS == "ausente":
        return AVISO_TERMOS
    linhas = ", ".join(str(n) for n in LINHAS_TERMOS_IGNORADAS[:20])
    return (
        "⚠️  TERMOS NÃO RODARAM — %s\n" % MOTIVO_TERMOS.get(ESTADO_TERMOS, ESTADO_TERMOS)
        + ("    Linhas de termo ignoradas (só o número): %s\n" % linhas if linhas else "")
        + "    Só as regras estruturais (caminho de máquina, e-mail pessoal, credencial)\n"
          "    foram aplicadas. Confira o formato em scripts/public_repo_terms.example."
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
        if args.json:
            print(json.dumps({"ok": False, "count": 0, "terms_checked": TEM_TERMOS,
                              "terms_state": ESTADO_TERMOS, "unreadable": [],
                              "error": seguro(str(e)), "findings": []},
                             ensure_ascii=False, indent=1))
        else:
            print("public-repo-check: NÃO MEDIDO — %s" % seguro(str(e)))
        return 2

    sem_lista = not args.staged and notas["lista"] == 0
    termos_ok = TEM_TERMOS
    termos_ilegiveis = ESTADO_TERMOS == "ilegivel"
    # exit 3 = a medição foi parcial e o ambiente (CI) não aceita parcial sem pedido
    exige_termos = em_ci() and not args.so_estruturais
    nao_medido = bool(notas["ilegiveis"]) or sem_lista or termos_ilegiveis

    if args.json:
        print(json.dumps({
            "ok": not achados and not nao_medido and (termos_ok or not exige_termos),
            "count": len(achados), "terms_checked": termos_ok, "terms_state": ESTADO_TERMOS,
            "unreadable": [seguro(p) for p in notas["ilegiveis"]],
            "non_utf8_scanned": notas["nao_utf8"], "binary_skipped": notas["binarios"],
            "findings": achados}, ensure_ascii=False, indent=1))
        if achados:
            return 1
        if nao_medido:
            return 2
        return 3 if (not termos_ok and exige_termos) else 0

    if not termos_ok:
        print(aviso_termos())
        if args.so_estruturais:
            print("    (pedido explícito: --so-estruturais)")
        print()

    if nao_medido:
        print("public-repo-check: NÃO MEDIDO por inteiro")
        for p in notas["ilegiveis"]:
            print("  arquivo rastreado que não abriu: %s" % seguro(p))
        if sem_lista:
            print("  git não listou arquivo nenhum")
        if termos_ilegiveis:
            print("  scripts/public_repo_terms ilegível: nenhuma regra de termo rodou")
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

    if nao_medido:
        return 2

    if notas["nao_utf8"]:
        print("nota: %d arquivo(s) não-UTF-8 lidos como latin-1 (varridos, mas acento "
              "em termo pode não casar)" % notas["nao_utf8"])
    if notas["binarios"]:
        print("nota: %d arquivo(s) com byte NUL tratados como binário (não varridos)"
              % notas["binarios"])
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
