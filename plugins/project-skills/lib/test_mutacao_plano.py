#!/usr/bin/env python3
"""test_mutacao_plano.py — prova que as travas do PLANO e da COMPLETUDE mordem.

Para cada trava nascida na rodada: desliga SÓ ela numa cópia do plugin,
roda a suíte que deve acusá-la, e exige que ela acuse. Trava cuja remoção
mantém tudo verde é trava sem cobertura — o defeito que ela previne voltaria sem que
nenhum teste percebesse. Molde: o harness de mutação do lixeiro.  <!-- acopla-ok: citação de MOLDE em prosa, não dependência executável — este arquivo não lê nem importa nada do plugin vizinho -->

⚠️ **Cada mutação declara a suíte que a cobre, e o veredito NEGATIVO ainda roda tudo.**
Rodar a suíte inteira em toda mutação custava 12 cópias × 20 suítes e a esteira matou este
arquivo no teto de 300s (medido em 2026-08-13, `run_suites.py` → `TIMEOUT 300.0s`). Com o
alvo declarado o caso comum roda UMA suíte; quando ela NÃO acusa, o harness roda a suíte
inteira antes de declarar sem cobertura — assim o barato é o caminho feliz e o rigor fica
onde ele importa, que é a hora de dizer "esta trava não tem quem a pegue". Alvo `None`
significa a suíte inteira, e é o que o CONTROLE usa.


A cópia é do REPOSITÓRIO INTEIRO, não só da pasta do plugin: várias suítes leem a
lei em `.claude/docs/` e as pastas dos plugins vizinhos, e numa cópia parcial elas  # casa-ok: prosa que descreve a casa velha, nao um caminho usado
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
     "import plan_state as c", "import plan_state as k",
     ("test_spec_to_plan_skill.py",)),
    ("B) nível 3 sem os três pés nomeados",
     "lib/auditoria_plano.py",
     '"pes": [{"pe": nome, "reprova": criterio}\n'
     '                               for nome, criterio in NIVEL3]},',
     '"pes": []},',
     ("test_auditoria_plano.py",)),
    ("C) sem o cruzamento artigo→tarefa",
     "lib/cobertura.py",
     '    faltando = [a for a in (artigos or [])\n'
     '                if reqs and _num_artigo(a) not in representados]',
     '    faltando = []',
     ("test_cobertura.py", "test_completude.py")),
    ("D) artigo sem tarefa de volta ao nível 1",
     "lib/auditoria_plano.py",
     '    ("sem_artigo", "não nasce de artigo nenhum da lei"),\n',
     '    ("sem_artigo", "não nasce de artigo nenhum da lei"),\n'
     '    ("artigos_sem_tarefa", "artigo da lei que nenhuma tarefa representa"),\n',
     ("test_auditoria_plano.py",)),
    ("E) init aceita status fora do vocabulário",
     "lib/plan_state.py",
     "if pst is not None and pst not in PLAN_STATUSES:", "if False:",
     ("test_plan_state.py",)),
    ("F) features.md ausente não vira lacuna",
     "lib/completude.py",
     "if not cobertura._texto(features).strip():", "if False:",
     ("test_completude.py",)),
    ("G) lacuna não derruba o veredito de completa",
     "lib/completude.py",
     '"completa": not falta_doc and all', '"completa": all',
     ("test_completude.py",)),
    ("H) o resumo esconde o que depende de julgamento",
     "lib/completude.py",
     'for k, v in e.get("declarado", {}).items():', "for k, v in ():",
     ("test_completude.py",)),
    ("I) tique com prova curta passa por provado",
     "lib/completude.py",
     "if len(prova) < plan_state.EVIDENCE_MIN:", "if False:",
     ("test_completude.py",)),
    ("J) só o primeiro plano entra no cruzamento",
     "lib/completude.py",
     "    out = []\n    for p in planos:",
     "    out = []\n    for p in planos[:1]:",
     ("test_completude.py",)),
    ("J2) plano encerrado volta a creditar tudo",
     "lib/completude.py",
     'parcial = p.get("status") in ("abandoned", "done")', "parcial = False",
     ("test_completude.py",)),
    ("J3) só o abandonado credita parcial — o concluído volta a creditar inteiro",
     "lib/completude.py",
     'parcial = p.get("status") in ("abandoned", "done")',
     'parcial = p.get("status") == "abandoned"',
     ("test_completude.py",)),
    ("J4) a pendência do plano concluído volta a contar no elo 3",
     "lib/completude.py",
     'elif p.get("status") not in ("done", "abandoned"):',
     'elif p.get("status") != "abandoned":',
     ("test_completude.py",)),
    ("K) a skill da completude mede a olho",
     "skills/completude/SKILL.md",
     "lib/completude.py", "a medição",
     ("test_completude_skill.py",)),
    ("L) a gravação do plano antes da ida ao mapa",
     "skills/plan/SKILL.md",
     "## Passo 3 — monte o mapa da régua",
     "```bash\npython3 <plugin project-skills>/lib/plan_state.py init --file <arquivo.json>\n"
     "```\n\n## Passo 3 — monte o mapa da régua",
     ("test_spec_to_plan_skill.py",)),
    ("M) a frente grava pela metade",
     "lib/plan_state.py",
     "    errs.extend(_erros_da_frente(plan))\n", "",
     ("test_plan_state.py",)),
    ("N) o close cala sobre a frente que ficou viva",
     "lib/plan_state.py",
     '    if fr.get("branch"):\n        print("   🌿 frente ainda aberta',
     '    if False:\n        print("   🌿 frente ainda aberta',
     ("test_plan_state.py",)),
    ("N2) a página cala sobre a frente do plano",
     "lib/plan_state.py",
     '    if fr.get("branch"):\n        b, w = _e(fr["branch"])',
     '    if False:\n        b, w = _e(fr["branch"])',
     ("test_plan_state.py",)),
    ("O) o plano se grava 'done' com passo sem prova",
     "lib/plan_state.py",
     '    if pst == "done":\n', '    if False:\n',
     ("test_plan_state.py",)),
    ("CONTROLE (nenhuma mutação)", None, None, None, None),
]


def suites(lib, alvos):
    """Os arquivos de suíte a rodar: os declarados, ou todos quando `alvos` é None."""
    todos = [f for f in sorted(os.listdir(lib))
             if f.startswith("test_") and f.endswith(".py")
             and f != os.path.basename(__file__)]
    if alvos is None:
        return todos
    # alvo que não existe mais na pasta é defeito desta lista, não do repositório:
    # devolvê-lo faria a mutação "não acusar" por arquivo ausente e o veredito mentiria.
    faltando = [a for a in alvos if a not in todos]
    if faltando:
        raise SystemExit("alvo declarado que não existe em lib/: %s" % ", ".join(faltando))
    return list(alvos)


def roda(rel, de, para, alvos):
    """Aplica a mutação numa cópia e devolve o conjunto de suítes VERMELHAS.

    Roda primeiro só as suítes declaradas. Se NENHUMA acusar, roda a pasta inteira antes
    de deixar o harness declarar a trava sem cobertura — barato no caminho feliz, completo
    na hora de acusar.
    """
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
    for lote in ([suites(lib, alvos)] if alvos is None
                 else [suites(lib, alvos), suites(lib, None)]):
        for f in lote:
            out = subprocess.run([sys.executable, f], cwd=lib, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                 stdin=subprocess.DEVNULL, start_new_session=True)
            if out.returncode != 0:
                vermelhas.add(f)
        if vermelhas:
            break
    shutil.rmtree(base, ignore_errors=True)
    return vermelhas


sem_cobertura = []
for nome, rel, de, para, alvos in MUTACOES:
    acusaram = roda(rel, de, para, alvos)
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
