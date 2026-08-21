#!/usr/bin/env python3
"""O que a SKILL.md do handoff MANDA fazer com o arquivo de plano.

O handoff é o consumidor do `.claude/plans/*.plan.json`, e o defeito que ele
existe pra impedir é a sessão seguinte reescrever o que o arquivo já guarda. A
suíte cobra as duas pontas:
  - o comando prescrito na skill roda e mostra `pronto`/`pendencia` de verdade
  - a prosa manda COPIAR esses campos, não redigi-los de novo
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap

SKILL_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "skills", "handoff", "SKILL.md")

FAILS = []

# O bash que RESPONDE, não o do PATH (ver _shared/bash_posix.py).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bash_posix import bash_posix  # noqa: E402

BASH = None


def check(label, cond):
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s" % label)
        FAILS.append(label)


def blocos_bash(texto):
    """O bloco como quem copia recebe: sem a indentação do bullet que o aninha."""
    return [textwrap.dedent(b) for b in re.findall(r"```bash\n(.*?)```", texto, re.S)]


def secao_do_plano(texto):
    """O trecho do Processo que fala do arquivo de plano no disco."""
    ini = texto.find("existe arquivo de plano no disco?")
    fim = texto.find("Pré-preencha o prospecto", ini)
    return texto[ini:fim] if ini >= 0 else ""


def secao_do_worktree(texto):
    """O trecho do RETOMAR que decide entre handoffs de mesmo nome."""
    ini = texto.find("O projeto tem worktrees")
    fim = texto.find("O LOG verbatim fica em", ini)
    return texto[ini:fim] if ini >= 0 else ""


def secao_das_armadilhas(texto):
    """O trecho do RETOMAR que manda conferir o que o handoff declarou."""
    ini = texto.find("Toda armadilha declarada no handoff é CONFERIDA")
    fim = texto.find("### Regras do RETOMAR", ini)
    return texto[ini:fim] if ini >= 0 else ""


def git(cwd, *args, quando=None):
    env = dict(os.environ)
    if quando is not None:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = "%d +0000" % quando
    subprocess.run(["git", "-C", cwd] + list(args), check=True, env=env,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)


def escreve(caminho, texto, mtime):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as fh:
        fh.write(texto)
    os.utime(caminho, (mtime, mtime))


def sandbox_dois_worktrees(raiz):
    """Dois worktrees, o MESMO nome de handoff, e a armadilha do mtime:

    o worktree parado tem o arquivo mais NOVO (mtime de hoje) e o commit de 3
    dias atrás; o worktree onde o trabalho aconteceu tem o arquivo com mtime
    velho e o commit de agora. Ordenar por mtime escolhe o errado.
    """
    agora = 1754000000
    tres_dias = agora - 3 * 86400
    parado = os.path.join(raiz, "parado")
    os.makedirs(parado)
    git(parado, "init", "-q")
    git(parado, "config", "user.email", "t@t")
    git(parado, "config", "user.name", "t")
    escreve(os.path.join(parado, "a.txt"), "base\n", tres_dias)
    git(parado, "add", "a.txt")
    git(parado, "commit", "-qm", "base", quando=tres_dias)

    trabalhado = os.path.join(raiz, "trabalhado")
    git(parado, "worktree", "add", "-q", "-b", "frente", trabalhado)
    escreve(os.path.join(trabalhado, "b.txt"), "trabalho\n", agora)
    git(trabalhado, "add", "b.txt")
    git(trabalhado, "commit", "-qm", "trabalho de verdade", quando=agora)

    escreve(os.path.join(parado, ".claude", "HANDOFF-mod.md"), "# velho\n", agora)
    escreve(os.path.join(trabalhado, ".claude", "HANDOFF-mod.md"), "# novo\n", tres_dias)
    return parado, trabalhado


HANDOFF_COM_ARMADILHA = """\
# Session Handoff — PRD
Project: /tmp/sandbox

## Próximos Passos

### 1. Ligar o motor de coleta
- **Ação:** rodar o motor no projeto inteiro.

## Findings & Gotchas
- O motor morre com `OSError: too many open files` quando `collect_engine.py` abre os transcripts sem fechar.
- Armadilha sem alvo nenhum citado nesta linha.

## Detalhes Técnicos
- Nada de armadilha aqui: `arquivo_da_outra_secao.py` não deve vazar pra lista.
"""


PLANO = {
    "id": "2026-08-01-sandbox",
    "title": "Plano de sandbox",
    "status": "active",
    "phases": [{"id": "F1", "title": "Base", "items": [
        {"id": "F1.1", "title": "Endpoint de login", "desc": "abre a sessão",
         "requisito": "S-1.1", "pronto": "`curl -X POST /login` devolve 200",
         "status": "done", "evidence": "commit a1b2c3d · 4 testes OK"},
        {"id": "F1.2", "title": "Endpoint de logout", "desc": "derruba a sessão",
         "requisito": "S-1.2", "pronto": "`curl -X POST /logout` devolve 204",
         "pendencia": "cookie ou header? falta decidir", "status": "todo"},
    ]}],
}


def main():
    texto = open(SKILL_MD, encoding="utf-8").read()
    secao = secao_do_plano(texto)

    # Os três casos abaixo EXECUTAM o comando que a skill prescreve. Sem um bash
    # que responda, o que falha é o interpretador — e reprovar a skill por isso é
    # a conclusão errada. Pula declarando, como o test_conformance faz.
    global BASH
    BASH = bash_posix()
    if BASH is None:
        print("  skip os comandos prescritos (nenhum bash funcional nesta máquina)")

    print("o comando prescrito mostra os campos que a árvore esconde")
    candidatos = [b for b in blocos_bash(secao) if "pronto" in b]
    check("a skill prescreve um comando que lê `pronto` do arquivo", len(candidatos) == 1)
    if candidatos and BASH:
        raiz = tempfile.mkdtemp(prefix="handoff-skill-")
        try:
            plans = os.path.join(raiz, ".claude", "plans")
            os.makedirs(plans)
            with open(os.path.join(plans, "2026-08-01-sandbox.plan.json"),
                      "w", encoding="utf-8") as fh:
                json.dump(PLANO, fh, ensure_ascii=False)
            cmd = candidatos[0].replace("<project_root>", raiz)
            proc = subprocess.run([BASH, "-c", cmd], capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
            saida = proc.stdout
            check("o comando roda sem erro (%s)" % (proc.stderr.strip()[:80] or "ok"),
                  proc.returncode == 0)
            check("mostra o `pronto` do passo aberto",
                  "curl -X POST /logout` devolve 204" in saida)
            check("mostra a `pendencia` do passo aberto",
                  "cookie ou header? falta decidir" in saida)
            check("não repete o passo já marcado", "Endpoint de login" not in saida)
        finally:
            shutil.rmtree(raiz, ignore_errors=True)

    print("a prosa manda copiar, não redigir")
    check("o `pronto` do arquivo vira o 'Critério de pronto'",
          "Critério de pronto" in secao and "verbatim" in secao.lower())
    check("a `pendencia` vira 'Decisão em aberto' e bloqueia o passo",
          "pendencia" in secao and "bloquead" in secao.lower())

    print("com dois handoffs de mesmo nome, vence o do worktree com o trabalho")
    wsec = secao_do_worktree(texto)
    wcands = [b for b in blocos_bash(wsec) if "worktree list" in b]
    check("a skill prescreve um comando que ordena os worktrees", len(wcands) == 1)
    if wcands:
        # realpath: o git devolve o worktree canonicalizado (/private/var/…),
        # e o mkdtemp devolve /var/… — sem isto o caminho nunca casa.
        raiz = os.path.realpath(tempfile.mkdtemp(prefix="handoff-worktree-"))
        try:
            parado, trabalhado = sandbox_dois_worktrees(raiz)
            velho = os.path.join(parado, ".claude", "HANDOFF-mod.md")
            novo = os.path.join(trabalhado, ".claude", "HANDOFF-mod.md")
            check("a armadilha existe: o handoff do worktree PARADO é o mais novo por mtime",
                  os.path.getmtime(velho) > os.path.getmtime(novo))

            cmd = wcands[0].replace("<project_root>", parado)
            proc = subprocess.run([BASH, "-c", cmd], capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
            check("o comando roda sem erro (%s)" % (proc.stderr.strip()[:80] or "ok"),
                  proc.returncode == 0)
            # BARRA NORMALIZADA DOS DOIS LADOS: o `git worktree list` devolve o
            # caminho com '/' também no Windows, e o `os.path.join` do Python devolve
            # com '\\' — a comparação nunca casava lá, e o teste acusava a ORDEM do
            # comando quando o que divergia era o separador.
            barra = lambda x: x.replace("\\", "/")
            linhas = [barra(ln) for ln in proc.stdout.splitlines() if ln.strip()]
            check("lista os dois handoffs de mesmo nome", len(linhas) == 2)
            check("o escolhido (1ª linha) é o do worktree onde o trabalho aconteceu",
                  bool(linhas) and linhas[0].endswith("\t" + barra(novo)))
            check("o do worktree parado fica atrás",
                  len(linhas) > 1 and linhas[1].endswith("\t" + barra(velho)))
        finally:
            subprocess.run(["git", "-C", raiz, "worktree", "prune"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)
            shutil.rmtree(raiz, ignore_errors=True)

    print("a armadilha declarada no handoff é conferida, não só lida")
    asec = secao_das_armadilhas(texto)
    acands = [b for b in blocos_bash(asec) if "Findings & Gotchas" in b]
    check("a skill prescreve um comando que extrai as armadilhas do handoff",
          len(acands) == 1)
    if acands and BASH:
        raiz = tempfile.mkdtemp(prefix="handoff-armadilha-")
        try:
            hpath = os.path.join(raiz, "HANDOFF.md")
            with open(hpath, "w", encoding="utf-8") as fh:
                fh.write(HANDOFF_COM_ARMADILHA)
            cmd = acands[0].replace("<handoff_path>", hpath)
            proc = subprocess.run([BASH, "-c", cmd], capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
            saida = proc.stdout
            check("o comando roda sem erro (%s)" % (proc.stderr.strip()[:80] or "ok"),
                  proc.returncode == 0)
            check("a armadilha vira item numerado de checagem",
                  "[armadilha 1]" in saida and "[armadilha 2]" in saida)
            check("transcreve a armadilha declarada",
                  "OSError: too many open files" in saida)
            confs = [ln for ln in saida.splitlines() if "conferir em:" in ln]
            check("aponta ONDE conferir (o alvo citado na armadilha)",
                  bool(confs) and "collect_engine.py" in confs[0])
            check("armadilha sem alvo não passa calada",
                  "SEM ALVO CITADO" in saida)
            check("não arrasta a seção seguinte",
                  "arquivo_da_outra_secao.py" not in saida)
        finally:
            shutil.rmtree(raiz, ignore_errors=True)

    check("a prosa bloqueia o passo enquanto a armadilha não foi conferida",
          "bloquead" in asec.lower() and "não execute a partir da leitura" in asec)

    print("o extrator lê o estado das etapas de concepção do disco")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from extract_ata import estado_etapas
    raiz = tempfile.mkdtemp(prefix="handoff-concepcao-")
    try:
        docs = os.path.join(raiz, ".claude", "docs")
        os.makedirs(docs)
        escreve(os.path.join(docs, "constituicao.md"),
                "---\nstatus: approved\n---\n\nA lei do projeto.\n", 1754000000)
        escreve(os.path.join(docs, "blueprint.md"),
                "---\nstatus: ready\n---\n\nO desenho.\n", 1754000000)
        escreve(os.path.join(docs, "journeys.md"),
                "---\nstatus: approved\n---\n\n## Jornada\n[PENDENTE]\n", 1754000000)
        est = estado_etapas(raiz)
        check("a lei aprovada aparece como aprovada", est["aprovadas"] == ["lei"])
        check("o desenho escrito sem o de acordo é etapa aberta",
              "desenho" in est["abertas"])
        check("etapa com [PENDENTE] no corpo é etapa aberta, não aprovada",
              "jornadas" in est["abertas"] and "jornadas" not in est["aprovadas"])
        check("o que não existe no disco sai como ausente",
              "funcionalidades" in est["ausentes"] and "régua" in est["ausentes"])
        item = [e for e in est["etapas"] if e["etapa"] == "desenho"][0]
        check("cada etapa nomeia o arquivo e o status lido",
              item["arquivo"] == "blueprint.md" and item["status"] == "ready")
    finally:
        shutil.rmtree(raiz, ignore_errors=True)

    print("o extrator enxerga a casa NOVA da doc (docs/ na raiz)")
    raiz = tempfile.mkdtemp(prefix="handoff-casa-nova-")
    try:
        docs = os.path.join(raiz, "docs")
        os.makedirs(docs)
        escreve(os.path.join(docs, "constituicao.md"),
                "---\nstatus: ready\n---\n\nA lei do projeto.\n", 1754000000)
        est = estado_etapas(raiz)
        check("doc em docs/ na raiz não sai como ausente",
              "lei" not in est["ausentes"])
        check("o docs_dir resolvido aponta a casa nova",
              est["docs_dir"] == docs)
    finally:
        shutil.rmtree(raiz, ignore_errors=True)

    print("o PRD nasce com a seção do estado da concepção")
    check("o molde do HANDOFF.md tem a seção", "## Estado da Concepção" in texto)
    sec_conc = texto[texto.find("## Estado da Concepção"):texto.find("## Findings & Gotchas")]
    check("a seção manda COPIAR o que o extrator leu, não redigir de cabeça",
          "concepcao" in sec_conc and "COPIADO" in sec_conc)
    check("a seção nomeia etapa aberta, lei e desenho",
          "abertas" in sec_conc and "constituicao.md" in sec_conc and "blueprint.md" in sec_conc)

    print()
    if FAILS:
        print("FALHOU: %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
