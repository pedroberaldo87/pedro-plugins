#!/usr/bin/env python3
"""test_mutacao_plano.py — prova que as travas do caminho do PLANO mordem.

Para cada trava nascida na rodada do plano: desliga SÓ ela numa cópia do plugin,
roda a suíte INTEIRA do project-skills, e exige que ela acuse. Trava cuja remoção
mantém tudo verde é trava sem cobertura — o defeito que ela previne voltaria sem que
nenhum teste percebesse. Molde: o harness de mutação do lixeiro.  <!-- acopla-ok: citação de MOLDE em prosa, não dependência executável — este arquivo não lê nem importa nada do plugin vizinho -->


A cópia é do REPOSITÓRIO INTEIRO, não só da pasta do plugin: várias suítes leem a
lei em `.claude/docs/` e as pastas dos plugins vizinhos, e numa cópia parcial elas
ficam vermelhas por falta de arquivo — aí o CONTROLE acusa sujeira em vez de mutação
e todo veredito vira ruído. Fora ficam só `.git`, o grafo e os caches (0,7 s de cópia).
"""
import os
import shutil
import subprocess
import sys
import tempfile

# A raiz do plugin e a do repositório, relativas a este arquivo — nunca caminho de máquina.
SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAIZ = os.path.dirname(os.path.dirname(SRC))
IGNORA = shutil.ignore_patterns(".git", "graphify-out", "node_modules",
                                "__pycache__", ".ruff_cache", "*.pyc")

MUTACOES = [
    ("A) SKILL.md sem a linha da ida ao mapa da régua",
     "skills/plan/SKILL.md",
     "import cobertura as c", "import cobertura as k"),
    ("B) nível 3 sem os três pés nomeados",
     "lib/auditoria_plano.py",
     '"pes": [{"pe": nome, "reprova": criterio}\n'
     '                               for nome, criterio in NIVEL3]},',
     '"pes": []},'),
    ("C) sem o cruzamento artigo→tarefa",
     "lib/cobertura.py",
     '    faltando = [a for a in (artigos or [])\n'
     '                if reqs and _num_artigo(a) not in representados]',
     '    faltando = []'),
    ("D) artigo sem tarefa fora do nível 1",
     "lib/auditoria_plano.py",
     '    ("artigos_sem_tarefa", "artigo da lei que nenhuma tarefa representa"),\n', ''),
    ("E) init aceita status fora do vocabulário",
     "lib/plan_state.py",
     "if pst is not None and pst not in PLAN_STATUSES:", "if False:"),
    ("CONTROLE (nenhuma mutação)", None, None, None),
]


def roda(rel, de, para):
    """Aplica a mutação numa cópia e devolve o conjunto de suítes VERMELHAS."""
    base = tempfile.mkdtemp(prefix="plano-mut-")
    dest = os.path.join(base, "repo")
    shutil.copytree(RAIZ, dest, ignore=IGNORA, symlinks=True)
    dest = os.path.join(dest, "plugins", "project-skills")
    lib = os.path.join(dest, "lib")
    if rel:
        alvo = os.path.join(dest, *rel.split("/"))
        s = open(alvo, encoding="utf-8").read()
        if de not in s:
            shutil.rmtree(base, ignore_errors=True)
            return None
        open(alvo, "w", encoding="utf-8").write(s.replace(de, para))
    vermelhas = set()
    for f in sorted(os.listdir(lib)):
        if not (f.startswith("test_") and f.endswith(".py")) or f == os.path.basename(__file__):
            continue
        out = subprocess.run([sys.executable, f], cwd=lib, capture_output=True, text=True,
                             stdin=subprocess.DEVNULL, start_new_session=True)
        if out.returncode != 0:
            vermelhas.add(f)
    shutil.rmtree(base, ignore_errors=True)
    return vermelhas


sem_cobertura = []
for nome, rel, de, para in MUTACOES:
    acusaram = roda(rel, de, para)
    if acusaram is None:
        linha = "PADRÃO NÃO ENCONTRADO — a mutação não testou nada"
    else:
        linha = ", ".join(sorted(acusaram)) or "0 suítes vermelhas"
    # a mutação tem que deixar alguma suíte vermelha; o CONTROLE, nenhuma
    esperado_vermelho = rel is not None
    if bool(acusaram) != esperado_vermelho:
        sem_cobertura.append(nome)
        veredito = "⚠️  TRAVA SEM COBERTURA" if esperado_vermelho else "⚠️  CONTROLE VERMELHO"
    else:
        veredito = "ok"
    print("%-44s %-58s %s" % (nome, linha, veredito))

print()
print("travas sem cobertura: %d" % len(sem_cobertura))
sys.exit(1 if sem_cobertura else 0)
