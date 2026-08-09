#!/usr/bin/env python3
"""Bancada da proibição: a rodada de autópsia não altera arquivo do projeto.

A skill é texto, e texto some em reescrita. Então a bancada olha os dois lados da
lei: a parte EXECUTÁVEL da rodada (medidor, sobras, registro) roda de verdade sobre
uma fixture, com a árvore do projeto fotografada antes e depois; e o texto da skill
é lido atrás da proibição escrita e de qualquer comando de escrita nos blocos dela.

Fotografia = `git status --porcelain -uall`: pega arquivo modificado, apagado,
renomeado e criado. Se a rodada tocar qualquer um, as duas fotos divergem.
"""

import os
import re
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(AQUI)
RAIZ = os.path.dirname(os.path.dirname(PLUGIN))
SKILL = os.path.join(PLUGIN, "skills", "improve-workflow", "SKILL.md")
FIXTURE = os.path.join(PLUGIN, "fixtures", "run-exemplo")

FALHAS = []


def check(nome, cond, detalhe=""):
    print("  %s  %s%s" % ("ok  " if cond else "FAIL", nome,
                          "" if cond else "  → " + detalhe))
    if not cond:
        FALHAS.append(nome)


def foto():
    """O estado da árvore do projeto, em uma string."""
    return subprocess.run(["git", "-C", RAIZ, "status", "--porcelain", "-uall"],
                          capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, start_new_session=True).stdout


def rodar(*args, **kw):
    return subprocess.run([sys.executable] + list(args), cwd=RAIZ,
                          capture_output=True, text=True,
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
    for frase in ("Nenhum arquivo do projeto muda durante a rodada",
                  "proibida de consertar",
                  "registro.jsonl"):
        check("a skill diz: %r" % frase, frase in texto)


def caso_texto_de_quem_refuta():
    """As duas peças fixas do segundo agente: a ordem de derrubar e a trava."""
    texto = open(SKILL, encoding="utf-8").read()
    for nome, frase in (("a ordem de derrubar", "tente derrubar cada afirmação"),
                        ("a trava de robustez",
                         "reprove toda proposta que troque robustez por economia")):
        check("o texto de quem refuta traz %s" % nome, frase in texto.lower(), frase)


def caso_blocos_da_skill_sao_de_leitura():
    """Comando de escrita dentro de bloco executável da skill reprova."""
    texto = open(SKILL, encoding="utf-8").read()
    blocos = re.findall(r"```bash\n(.*?)```", texto, re.S)
    check("a skill tem bloco de comando", bool(blocos))
    # `>` só conta como redirecionamento quando vem depois de espaço — senão
    # `<run>` no exemplo de uso reprovaria a skill inteira.
    proibidos = ("git commit", "git add", "git checkout", "git stash",
                 "rm ", "mv ", "tee ", r"\s>>?\s*\S")
    sujos = [(b, p) for b in blocos for p in proibidos if re.search(p, b)]
    check("nenhum bloco escreve", not sujos, repr(sujos[:2]))


def caso_sem_sinal_nao_dispara_agente():
    """Run são: o medidor mede, não acende sinal, e ninguém sobe agente (F20.15)."""
    r = rodar(os.path.join(AQUI, "medidor.py"), os.path.join(PLUGIN, "fixtures", "run-sao"))
    check("o medidor roda sozinho no run são", r.returncode == 0, r.stderr[-300:])
    check("nenhum sinal aceso", "sinais — 0 dos 6 acesos" in r.stdout,
          r.stdout.splitlines()[-8:])
    # Os passos 2–6 são os que gastam agente. Sem sinal, o texto tem que barrar os dois
    # lados: quem chama (sovai) e quem seria chamado (esta skill).
    texto = open(SKILL, encoding="utf-8").read()
    check("a skill diz que sem sinal para no passo 1",
          "agente nenhum é disparado" in texto)
    sovai = os.path.join(RAIZ, "plugins", "project-skills", "skills", "sprint", "SKILL.md")
    if os.path.exists(sovai):
        t = open(sovai, encoding="utf-8").read()
        check("o sovai roda o medidor ao fim de toda missão", "lib/medidor.py" in t)
        check("o sovai não dispara agente sem sinal", "não dispare agente nenhum" in t)


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


if __name__ == "__main__":
    print("bancada da proibição — a autópsia não toca a árvore que audita")
    caso_chave_de_desligar()
    caso_sem_sinal_nao_dispara_agente()
    caso_rodada_nao_toca_a_arvore()
    caso_texto_declara_a_proibicao()
    caso_texto_de_quem_refuta()
    caso_blocos_da_skill_sao_de_leitura()
    print("\n%s" % ("tudo verde" if not FALHAS else "FALHOU: " + ", ".join(FALHAS)))
    sys.exit(1 if FALHAS else 0)
