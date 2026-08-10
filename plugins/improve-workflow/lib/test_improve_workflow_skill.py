#!/usr/bin/env python3
"""Bancada da proibição: a rodada de autópsia não altera arquivo do projeto.

A skill é texto, e texto some em reescrita. Então a bancada olha os dois lados da
lei: a parte EXECUTÁVEL da rodada (medidor, sobras, registro) roda de verdade sobre
uma fixture, com a árvore do projeto fotografada antes e depois; e o texto da skill
é lido atrás da proibição escrita e de qualquer comando de escrita nos blocos dela.

Fotografia = `git status --porcelain -uall`: pega arquivo modificado, apagado,
renomeado e criado. Se a rodada tocar qualquer um, as duas fotos divergem.
"""

import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

# O bash que RESPONDE, não o do PATH: no Windows o do PATH é o do WSL, que sem
# distro fala UTF-16 e chega como stdout vazio — a suíte reprovaria o comando
# certo por causa do interpretador. Módulo compartilhado (_shared/bash_posix.py).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bash_posix import bash_posix  # noqa: E402

BASH = bash_posix() or "bash"


AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(AQUI)
RAIZ = os.path.dirname(os.path.dirname(PLUGIN))
SKILL = os.path.join(PLUGIN, "skills", "improve-workflow", "SKILL.md")
FIXTURE = os.path.join(PLUGIN, "fixtures", "run-exemplo")

FALHAS = []

# Placeholder que a PROSA da skill declara (o run pedido pelo nome). Qualquer
# outro `<…>` dentro de bloco executável é comando mudo, e reprova.
DECLARADOS = ("<run>",)


def check(nome, cond, detalhe=""):
    print("  %s  %s%s" % ("ok  " if cond else "FAIL", nome,
                          "" if cond else "  → %s" % (detalhe,)))
    if not cond:
        FALHAS.append(nome)


def foto(raiz=RAIZ):
    """O estado da árvore de um projeto, em uma string."""
    return subprocess.run(["git", "-C", raiz, "status", "--porcelain", "-uall"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          stdin=subprocess.DEVNULL, start_new_session=True).stdout


def rodar(*args, **kw):
    return subprocess.run([sys.executable] + list(args), cwd=RAIZ,
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          stdin=subprocess.DEVNULL, start_new_session=True, **kw)


def caso_rodada_nao_toca_a_arvore():
    """A rodada inteira, sobre a fixture, com a árvore antes e depois."""
    antes = foto()
    lar = tempfile.mkdtemp(prefix="autopsia-registro-")
    env = dict(os.environ, CLAUDE_CONFIG_DIR=lar)
    # Cada passo tem o seu código de saída: 0 é sucesso em todos, e só a varredura
    # de sobras usa 1 como recado ("achei sobra"). Aceitar 1 nos outros deixaria
    # medidor quebrado passar por "roda", e aí a foto da árvore fica igual porque o
    # programa não fez nada.
    passos = [
        ("medir", [os.path.join(AQUI, "medidor.py"), FIXTURE], (0,)),
        ("varrer sobras", [os.path.join(AQUI, "sobras.py"), "--run", FIXTURE, "--json"], (0, 1)),
        ("registrar", [os.path.join(AQUI, "registro.py"), "gravar", FIXTURE], (0,)),
    ]
    for nome, cmd, aceitos in passos:
        r = rodar(*cmd, env=env)
        check("passo roda: " + nome, r.returncode in aceitos,
              "saiu %d, esperado %s\n%s" % (r.returncode, aceitos, r.stderr[-300:]))
    depois = foto()
    check("a árvore do projeto é a mesma antes e depois", antes == depois,
          "diferença:\n" + "\n".join(
              sorted(set(depois.splitlines()) ^ set(antes.splitlines()))))
    # E a única escrita permitida aconteceu mesmo — fora do projeto.
    registro = os.path.join(lar, "improve-workflow", "registro.jsonl")
    check("o registro nasceu fora do projeto", os.path.exists(registro), registro)


def caso_texto_declara_a_proibicao():
    texto = open(SKILL, encoding="utf-8").read()
    # A lei não pode ser lida como proibição absoluta: ela mesma aponta o passo 8.
    for absoluta in ("Nenhum arquivo do projeto muda durante a rodada",
                     "Tudo abaixo é leitura"):
        check("a lei não se lê como proibição absoluta: %r" % absoluta,
              absoluta not in texto)
    for frase in ("Nenhum arquivo do projeto muda durante a apuração",
                  "só o passo 8 grava",
                  "Os passos 1 a 7 são leitura",
                  "proibida de consertar",
                  "registro.jsonl",
                  # A exceção é declarada, e o único que escreve no projeto é o
                  # programa do passo 8 — sem estas duas a etapa some da receita
                  # e o `plano_saida.py` volta a ser órfão.
                  "A ÚNICA EXCEÇÃO",
                  "lib/plano_saida.py"):
        check("a skill diz: %r" % frase, frase in texto)


def caso_texto_de_quem_refuta():
    """As duas peças fixas do segundo agente: a ordem de derrubar e a trava."""
    texto = open(SKILL, encoding="utf-8").read()
    for nome, frase in (("a ordem de derrubar", "tente derrubar cada afirmação"),
                        ("a trava de robustez",
                         "reprove toda proposta que troque robustez por economia")):
        check("o texto de quem refuta traz %s" % nome, frase in texto.lower(), frase)


def sujeira(bloco):
    """Achados de um bloco executável: escrita na árvore e placeholder mudo.

    A isenção é do TOKEN que a prosa declara (`<run>`), não do operador `>` —
    isentar o operador deixava passar `<plugin visual>`, que o shell lê como
    par de redirecionamentos. Mesma régua de `scripts/autopsia_check.py`.
    """
    limpo = bloco
    for token in DECLARADOS:
        limpo = limpo.replace(token, "")
    proibidos = ("git commit", "git add", "git checkout", "git stash",
                 "rm ", "mv ", "tee ", r">>?\s*\S", r"<[^<>\n]+>")
    return [p for p in proibidos if re.search(p, limpo)]


def caso_blocos_da_skill_sao_de_leitura():
    """Comando de escrita dentro de bloco executável da skill reprova."""
    texto = open(SKILL, encoding="utf-8").read()
    blocos = re.findall(r"```bash\n(.*?)```", texto, re.S)
    check("a skill tem bloco de comando", bool(blocos))
    sujos = [(b, s) for b in blocos for s in sujeira(b)]
    check("nenhum bloco escreve", not sujos, repr(sujos[:2]))


def caso_placeholder_nao_declarado_reprova():
    """A régua reprova placeholder que a prosa não declara — texto de ontem, fixado.

    A string abaixo é a linha que a skill carregava antes do conserto do irmão:
    fixada aqui, a prova nasce vermelha por si, sem depender do texto de hoje.
    """
    ontem = 'PAGINA="<plugin visual>/lib/visual_page.py"\n'
    check("o placeholder mudo do irmão reprova", bool(sujeira(ontem)))
    check("o placeholder que a prosa declara passa",
          not sujeira('python3 "${CLAUDE_PLUGIN_ROOT}/lib/medidor.py" <run>\n'))


def caso_a_receita_roda_fora_do_repositorio():
    """A linha ESCRITA na skill roda no projeto de quem instalou (S-132).

    Caminho relativo (`plugins/improve-workflow/lib/…`) só existe neste
    repositório: no projeto alheio o comando morre em "No such file". A prova
    executa o comando VERBATIM da skill a partir de um cwd que não é este repo,
    com `CLAUDE_PLUGIN_ROOT` apontando para o plugin — como no harness real.
    """
    texto = open(SKILL, encoding="utf-8").read()
    blocos = re.findall(r"```bash\n(.*?)```", texto, re.S)
    # Nenhuma linha pode se localizar pela posição no ESTE repositório.
    # Qualquer `plugins/<nome>/`, não só o do próprio plugin: apontar para o
    # irmão pela posição dele NESTE repo morre igual no projeto de quem instalou.
    relativas = [ln.strip() for b in blocos for ln in b.splitlines()
                 if re.search(r"(?<!\$\{)plugins/[A-Za-z0-9_-]+/", ln)]
    check("nenhum comando se localiza por caminho deste repositório",
          not relativas, repr(relativas[:2]))
    # E as que não têm placeholder DECLARADO rodam de verdade, lá fora — o não
    # declarado não ganha isenção nenhuma: quem o reprova é `sujeira`.
    linhas = [ln.strip() for b in blocos for ln in b.splitlines()
              if ln.strip().startswith("python3 ")
              and not any(d in ln for d in DECLARADOS)
              and not ln.rstrip().endswith("\\")]
    check("a skill tem linha executável sem placeholder", bool(linhas))
    alheio = tempfile.mkdtemp(prefix="autopsia-alheio-")
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=PLUGIN,
               CLAUDE_CONFIG_DIR=tempfile.mkdtemp(prefix="autopsia-lar-"))
    for linha in linhas:
        r = subprocess.run([BASH, "-c", linha], cwd=alheio, env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           stdin=subprocess.DEVNULL, start_new_session=True)
        # 0 e 1 são os códigos do próprio programa (medir / achei sobra); 2 do
        # python é o arquivo que não existe — é ele que esta prova caça.
        check("a receita roda de outro cwd: %s" % linha[:60],
              r.returncode in (0, 1) and "No such file" not in r.stderr,
              "saiu %d\n%s" % (r.returncode, r.stderr[-300:]))


PROPOSTAS = {
    "run": "run-exemplo",
    "prova": {"src": "medidor.py run-exemplo",
              "output": "EXECUTOR  2 agentes  8 turnos  4.0 turnos/agente"},
    "propostas": [
        {"defeito": "EXECUTOR gasta 4 turnos por agente — 8 minutos de espera",
         "consequencia": ["cada tarefa espera 8 minutos por um agente que rende 1"],
         "proposta": ["teto de 1 turno por executor"],
         "mira": "EXECUTOR · turnos_por_agente 4.0",
         "confere": "registro.py compara turnos_por_agente na rodada seguinte",
         "sev": "high"}],
}

# Achados de clareza que dependem de COMO o programa monta o spec (e não das
# palavras que o dono escreve na proposta): estes têm que sair zerados.
ESTRUTURAIS = ("prova-sem-estrago", "apoio-fora", "custo-sem-unidade")


def caso_a_pagina_do_passo_7_nasce_fora_do_projeto():
    """O passo 7 é escrita, e escrita dentro do projeto auditado viola a lei.

    Sem destino explícito, o `visual_page.py` cai na cascata do /visual e grava em
    `<raiz-git>/.claude/visual/` — a rodada que jurou não tocar a árvore cria
    arquivo dentro dela. A prova roda o cano VERBATIM da skill num projeto git de
    mentira (o "projeto de quem instalou"), fotografa a árvore dele antes e depois,
    e passa o spec gerado pela régua do /visual.
    """
    texto = open(SKILL, encoding="utf-8").read()
    blocos = [b for b in re.findall(r"```bash\n(.*?)```", texto, re.S)
              if "proposta.py" in b]
    check("a skill tem o bloco do passo 7", len(blocos) == 1, repr(blocos[:2]))
    if len(blocos) != 1:
        return

    alheio = tempfile.mkdtemp(prefix="autopsia-passo7-")
    for cmd in (["git", "init", "-q"], ["git", "config", "user.email", "b@b"],
                ["git", "config", "user.name", "b"],
                ["git", "commit", "-q", "--allow-empty", "-m", "raiz"]):
        subprocess.run(cmd, cwd=alheio, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       stdin=subprocess.DEVNULL, start_new_session=True)
    with open(os.path.join(alheio, "propostas.json"), "w", encoding="utf-8") as f:
        json.dump(PROPOSTAS, f)
    subprocess.run(["git", "-C", alheio, "add", "propostas.json"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                   start_new_session=True)
    subprocess.run(["git", "-C", alheio, "commit", "-q", "-m", "propostas"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                   start_new_session=True)

    lar = tempfile.mkdtemp(prefix="autopsia-passo7-lar-")
    antes, antes_aqui = foto(alheio), foto()
    r = subprocess.run([BASH, "-c", blocos[0]], cwd=alheio,
                       env=dict(os.environ, CLAUDE_PLUGIN_ROOT=PLUGIN,
                                CLAUDE_CONFIG_DIR=lar, HOME=lar),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       stdin=subprocess.DEVNULL, start_new_session=True)
    check("o passo 7 roda de ponta a ponta", r.returncode == 0,
          "saiu %d\n%s" % (r.returncode, r.stderr[-400:]))
    depois, depois_aqui = foto(alheio), foto()
    check("o passo 7 não toca a árvore do projeto auditado", antes == depois,
          "diferença:\n" + "\n".join(
              sorted(set(depois.splitlines()) ^ set(antes.splitlines()))))
    check("o passo 7 não toca a árvore deste repositório", antes_aqui == depois_aqui)
    pagina = (r.stdout or "").strip().splitlines()[-1:] or [""]
    check("a página nasceu fora do projeto auditado",
          pagina[0] and os.path.isfile(pagina[0])
          and not os.path.abspath(pagina[0]).startswith(os.path.realpath(alheio))
          and not os.path.abspath(pagina[0]).startswith(alheio),
          repr(pagina[0]))

    # E o spec que foi por esse cano passa a régua do /visual.
    sys.path.insert(0, os.path.join(RAIZ, "plugins", "visual", "lib"))
    try:
        import clareza
    except ImportError:
        check("clareza.py ao lado (sem ele não há régua pra passar)", False)
        return
    gera = rodar(os.path.join(AQUI, "proposta.py"),
                 os.path.join(alheio, "propostas.json"))
    achados = [c for c, _m in clareza.revisao_do_spec(json.loads(gera.stdout))
               if c in ESTRUTURAIS]
    check("o spec do passo 7 não tem achado estrutural", not achados, repr(achados))


def caso_sem_o_irmao_a_rodada_pula_declarado():
    """Sem o `visual` na máquina, o passo 7 PULA a página — e não pula a recusa.

    O bloco antigo grudava as duas coisas num `[ -n "$PAGINA" ] && …`: sem irmão o
    `proposta.py` nem rodava (proposta mal formada passava batido) e o bloco saía
    calado com código 1, contra a prosa que promete pulo declarado. A prova roda o
    cano VERBATIM com um `CLAUDE_PLUGIN_ROOT` que não tem irmão nenhum ao lado nem
    cache de plugin no lar.
    """
    texto = open(SKILL, encoding="utf-8").read()
    blocos = [b for b in re.findall(r"```bash\n(.*?)```", texto, re.S)
              if "proposta.py" in b]
    if len(blocos) != 1:
        check("a skill tem o bloco do passo 7", False, repr(blocos[:2]))
        return

    sozinho = tempfile.mkdtemp(prefix="autopsia-sem-irmao-")
    raiz = os.path.join(sozinho, "improve-workflow")
    shutil.copytree(PLUGIN, raiz,
                    ignore=shutil.ignore_patterns("__pycache__", "fixtures"))
    lar = tempfile.mkdtemp(prefix="autopsia-sem-irmao-lar-")
    alheio = tempfile.mkdtemp(prefix="autopsia-sem-irmao-projeto-")
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=raiz, CLAUDE_CONFIG_DIR=lar, HOME=lar)

    def rodar_bloco(propostas):
        with open(os.path.join(alheio, "propostas.json"), "w", encoding="utf-8") as f:
            json.dump(propostas, f)
        return subprocess.run([BASH, "-c", blocos[0]], cwd=alheio, env=env,
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              stdin=subprocess.DEVNULL, start_new_session=True)

    boa = rodar_bloco(PROPOSTAS)
    check("sem o irmão o passo 7 termina em bem", boa.returncode == 0,
          "saiu %d\n%s" % (boa.returncode, boa.stderr[-300:]))
    check("sem o irmão o pulo sai declarado no stdout",
          "sem o visual nesta máquina" in boa.stdout, repr(boa.stdout[-300:]))

    ruim = dict(PROPOSTAS, propostas=[{"defeito": "sem mira nem como conferir"}])
    r = rodar_bloco(ruim)
    check("sem o irmão a proposta mal formada continua recusada",
          r.returncode != 0 and "✗" in r.stderr,
          "saiu %d\n%s" % (r.returncode, r.stderr[-300:]))


def caso_sem_sinal_nao_dispara_agente():
    """Run são: o medidor mede, não acende sinal, e ninguém sobe agente (F20.15)."""
    # Lar próprio: com a chave do ambiente em `off` o medidor sai mudo e com código 0,
    # e a bancada acusaria o run são de não medir. O caminho `off` tem bancada própria.
    lar = tempfile.mkdtemp(prefix="autopsia-sinal-")
    r = rodar(os.path.join(AQUI, "medidor.py"), os.path.join(PLUGIN, "fixtures", "run-sao"),
              env=dict(os.environ, CLAUDE_CONFIG_DIR=lar))
    check("o medidor roda sozinho no run são", r.returncode == 0, r.stderr[-300:])
    check("nenhum sinal aceso", "sinais — 0 dos 6 acesos" in r.stdout,
          r.stdout.splitlines()[-8:])
    # Os passos 2–6 são os que gastam agente. Sem sinal, o texto tem que barrar os dois
    # lados: quem chama (sprint) e quem seria chamado (esta skill).
    texto = open(SKILL, encoding="utf-8").read()
    check("a skill diz que sem sinal para no passo 1",
          "agente nenhum é disparado" in texto)
    sprint = os.path.join(RAIZ, "plugins", "project-skills", "skills", "sprint", "SKILL.md")
    if os.path.exists(sprint):
        t = open(sprint, encoding="utf-8").read()
        check("o sprint roda o medidor ao fim de toda missão", "lib/medidor.py" in t)
        check("o sprint não dispara agente sem sinal", "não dispare agente nenhum" in t)


def caso_relato_de_falha_aceita_detalhe_nao_texto():
    """Reprovar com detalhe em lista tem que sair FAIL nomeado, não traceback.

    A sonda roda com a saída desviada: quem lê o console de uma rodada verde não
    pode ver o FAIL de mentira da sonda — quem conta FAIL por grep leria falso
    positivo permanente.
    """
    marca = len(FALHAS)
    desviado = io.StringIO()
    with contextlib.redirect_stdout(desviado):
        check("sonda: detalhe não-texto", False, ["linha a", "linha b"])
    nomeou = FALHAS[marca:] == ["sonda: detalhe não-texto"]
    del FALHAS[marca:]
    check("o relato de falha aceita detalhe não-texto", nomeou)
    check("a sonda de reprovação não vaza FAIL pro console da rodada verde",
          "FAIL" in desviado.getvalue(), repr(desviado.getvalue()))


def caso_chave_de_desligar():
    """Os dois lados da chave (F20.19): ligada o medidor fala, `off` cala tudo."""
    lar = tempfile.mkdtemp(prefix="autopsia-chave-")
    env = dict(os.environ, CLAUDE_CONFIG_DIR=lar)
    cmd = (os.path.join(AQUI, "medidor.py"), FIXTURE)

    ligada = rodar(*cmd, env=env)
    check("sem chave no disco o medidor fala", ligada.returncode == 0 and ligada.stdout.strip(),
          "saiu %d, stdout %r" % (ligada.returncode, ligada.stdout[:200]))

    os.makedirs(os.path.join(lar, "improve-workflow"), exist_ok=True)
    with open(os.path.join(lar, "improve-workflow", "mode"), "w", encoding="utf-8") as f:
        f.write("off\n")
    calado = rodar(*cmd, env=env)
    check("com a chave desligada o fim de missão sai calado",
          calado.returncode == 0 and not calado.stdout and not calado.stderr,
          "saiu %d, stdout %r stderr %r"
          % (calado.returncode, calado.stdout[:200], calado.stderr[:200]))

    texto = open(SKILL, encoding="utf-8").read()
    check("a skill diz onde fica a chave",
          "~/.claude/improve-workflow/mode" in texto)


def caso_irmao_se_resolve_por_nome_nao_por_placeholder():
    """O plugin irmão entra pelo NOME, nunca por placeholder no bloco executável.

    `<plugin visual>` não é marcador inerte: dentro de ```bash o shell lê `<plugin`
    como redirecionamento de ENTRADA e `visual>` como de SAÍDA. A skill tem que
    achar o irmão por `resolve-plugin.sh <nome> <caminho>`, e a bancada roda esse
    resolvedor de verdade, de outro cwd.
    """
    texto = open(SKILL, encoding="utf-8").read()
    blocos = re.findall(r"```bash\n(.*?)```", texto, re.S)
    placeholders = [ln.strip() for b in blocos for ln in b.splitlines()
                    if "<plugin" in ln]
    check("nenhum bloco nomeia o irmão por placeholder", not placeholders,
          repr(placeholders[:2]))

    resolvedor = os.path.join(PLUGIN, "skills", "improve-workflow", "resolve-plugin.sh")
    check("o resolvedor está vendorado no plugin", os.path.isfile(resolvedor), resolvedor)
    check("a skill chama o resolvedor pelo nome do irmão",
          "resolve-plugin.sh\" visual lib/visual_page.py" in texto)
    check("a skill declara o pulo quando o irmão não está na máquina",
          "sem o `visual` na máquina" in texto)

    if os.path.isfile(resolvedor):
        alheio = tempfile.mkdtemp(prefix="autopsia-irmao-")
        r = subprocess.run([BASH, resolvedor, "visual", "lib/visual_page.py"],
                           cwd=alheio, env=dict(os.environ, CLAUDE_PLUGIN_ROOT=PLUGIN),
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           stdin=subprocess.DEVNULL, start_new_session=True)
        check("o resolvedor acha o visual de outro cwd",
              r.returncode == 0 and os.path.isfile(r.stdout.strip()),
              "saiu %d, stdout %r" % (r.returncode, r.stdout[:200]))


if __name__ == "__main__":
    print("bancada da proibição — a autópsia não toca a árvore que audita")
    caso_a_pagina_do_passo_7_nasce_fora_do_projeto()
    caso_sem_o_irmao_a_rodada_pula_declarado()
    caso_irmao_se_resolve_por_nome_nao_por_placeholder()
    caso_relato_de_falha_aceita_detalhe_nao_texto()
    caso_chave_de_desligar()
    caso_sem_sinal_nao_dispara_agente()
    caso_placeholder_nao_declarado_reprova()
    caso_a_receita_roda_fora_do_repositorio()
    caso_rodada_nao_toca_a_arvore()
    caso_texto_declara_a_proibicao()
    caso_texto_de_quem_refuta()
    caso_blocos_da_skill_sao_de_leitura()
    print("\n%s" % ("tudo verde" if not FALHAS else "FALHOU: " + ", ".join(FALHAS)))
    sys.exit(1 if FALHAS else 0)
