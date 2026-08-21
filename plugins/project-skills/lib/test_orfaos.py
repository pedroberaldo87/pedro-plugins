#!/usr/bin/env python3
"""O cobrador do detector de órfão (F18.1 · R-28).

O critério do passo, literal: com a árvore carregando o entregável de um passo
aberto, a rodada 1 devolve esse id na lista de órfãos; árvore limpa devolve lista
vazia. Aqui ele roda em repositório de verdade, criado na hora — `git status
--porcelain` sobre lar fingido é a única forma de provar o cruzamento.

    python3 plugins/project-skills/lib/test_orfaos.py
"""
import json
import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
DETECTOR = os.path.join(AQUI, "orfaos.py")

ok = falhas = 0


def checa(nome, cond, detalhe=""):
    global ok, falhas
    if cond:
        ok += 1
        print("  ok   %s" % nome)
    else:
        falhas += 1
        print("  FAIL %s  %s" % (nome, detalhe))


PLANO = {"id": "p", "items": [
    {"id": "F1.1", "title": "O primeiro passo",
     "desc": "Escreve o entregável em plugins/casa/lib/alvo.py.",  # acopla-ok: plugin fabricado de fixture
     "pronto": "o teste de plugins/casa/lib/alvo.py passa", "status": "todo"},  # acopla-ok: plugin fabricado de fixture
    {"id": "F1.2", "title": "O segundo passo",
     "desc": "Mexe em plugins/casa/lib/outro.py.",  # acopla-ok: plugin fabricado de fixture
     "pronto": "prosa sem caminho nenhum", "status": "todo"},
    {"id": "F1.3", "title": "O passo já marcado",
     "desc": "Também toca plugins/casa/lib/alvo.py, mas já está fechado.",  # acopla-ok: plugin fabricado de fixture
     "pronto": "irrelevante", "status": "done", "done_at": None},
]}


def git(root, *args):
    subprocess.run(("git",) + args, cwd=root, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   stdin=subprocess.DEVNULL, start_new_session=True)


def roda(root, plano_path):
    r = subprocess.run([sys.executable, DETECTOR, plano_path, "--root", root],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=60, stdin=subprocess.DEVNULL,
                       start_new_session=True)
    if r.returncode != 0:
        return None, r.stderr
    return json.loads(r.stdout)["orfaos"], r.stdout


def lar():
    d = tempfile.mkdtemp(prefix="orfaos-")
    git(d, "init", "-q")
    git(d, "config", "user.email", "t@t")
    git(d, "config", "user.name", "t")
    os.makedirs(os.path.join(d, "plugins", "casa", "lib"))
    with open(os.path.join(d, "base.txt"), "w", encoding="utf-8") as fh:
        fh.write("base\n")
    git(d, "add", "base.txt")
    git(d, "commit", "-qm", "base")
    plano_path = os.path.join(d, "plano.plan.json")
    with open(plano_path, "w", encoding="utf-8") as fh:
        json.dump(PLANO, fh, ensure_ascii=False)
    return d, plano_path


print("test_orfaos")

# 1 · ÁRVORE LIMPA (o plano vive fora da árvore conferida) ⇒ lista vazia.
raiz, plano_path = lar()
os.remove(plano_path)
plano_fora = os.path.join(tempfile.mkdtemp(prefix="orfaos-plano-"), "p.plan.json")
with open(plano_fora, "w", encoding="utf-8") as fh:
    json.dump(PLANO, fh, ensure_ascii=False)
vazio, cru = roda(raiz, plano_fora)
checa("árvore limpa devolve lista vazia", vazio == [], repr(cru))

# 2 · A ÁRVORE CARREGA O ENTREGÁVEL DE UM PASSO ABERTO ⇒ o id sai na lista.
with open(os.path.join(raiz, "plugins", "casa", "lib", "alvo.py"), "w",
          encoding="utf-8") as fh:
    fh.write("# entregue e não marcado\n")
achados, cru = roda(raiz, plano_fora)
ids = [a["id"] for a in (achados or [])]
checa("o passo aberto cujo entregável está na árvore vira órfão",
      ids == ["F1.1"], repr(cru))
checa("o órfão traz o caminho que o denunciou",
      bool(achados) and achados[0]["paths"] == ["plugins/casa/lib/alvo.py"], repr(cru))  # acopla-ok: plugin fabricado de fixture; caminho-ok: caminho RELATIVO fabricado pelo teste e devolvido cru pelo git — não há disco para normalizar
checa("passo aberto sem entregável mexido fica de fora", "F1.2" not in ids, repr(cru))
checa("passo JÁ MARCADO não vira órfão, mesmo tocando o arquivo",
      "F1.3" not in ids, repr(cru))

# 3 · COMMIT DESDE O ÚLTIMO TIQUE conta igual à árvore suja.
git(raiz, "add", "plugins/casa/lib/alvo.py")  # acopla-ok: plugin fabricado de fixture
git(raiz, "commit", "-qm", "entrega sem tique")
limpo, cru = roda(raiz, plano_fora)
checa("commitado, sem tique no plano, some da árvore suja",
      [a["id"] for a in (limpo or [])] == [], repr(cru))

PLANO_TICADO = json.loads(json.dumps(PLANO))
PLANO_TICADO["items"][2]["done_at"] = "1970-01-01T00:00:00"
with open(plano_fora, "w", encoding="utf-8") as fh:
    json.dump(PLANO_TICADO, fh, ensure_ascii=False)
achados, cru = roda(raiz, plano_fora)
checa("commit posterior ao último tique também denuncia o órfão",
      "F1.1" in [a["id"] for a in (achados or [])], repr(cru))

# 4 · COMMIT QUE CITA O ID do passo aberto denuncia sozinho.
git(raiz, "commit", "-q", "--allow-empty", "-m", "feat(F1.2): entregue e não marcado")
achados, cru = roda(raiz, plano_fora)
alvo = [a for a in (achados or []) if a["id"] == "F1.2"]
checa("commit que cita o id do passo aberto vira órfão", bool(alvo), repr(cru))
checa("o órfão por commit traz o assunto que o denunciou",
      bool(alvo) and alvo[0]["commits"] == ["feat(F1.2): entregue e não marcado"], repr(cru))

# 5 · O CAMPO `files` MANDA na prosa — o passo cujo texto não nomeia caminho nenhum
# ainda assim é pego, porque o entregável está declarado no campo.
PLANO_FILES = {"id": "p", "items": [
    {"id": "F2.1", "title": "Passo sem caminho no texto",
     "desc": "prosa sem caminho nenhum", "pronto": "o critério se cumpre",
     "status": "todo",
     "files": ["plugins/casa/lib/declarado.py"]},  # acopla-ok: plugin fabricado de fixture
]}
with open(plano_fora, "w", encoding="utf-8") as fh:
    json.dump(PLANO_FILES, fh, ensure_ascii=False)
antes, cru = roda(raiz, plano_fora)
checa("sem o entregável na árvore, o passo declarado por `files` não é órfão",
      [a["id"] for a in (antes or [])] == [], repr(cru))
with open(os.path.join(raiz, "plugins", "casa", "lib", "declarado.py"), "w",
          encoding="utf-8") as fh:
    fh.write("# entregue e nao marcado\n")
achados, cru = roda(raiz, plano_fora)
checa("o passo é pego pelo campo `files`, com a prosa sem caminho nenhum",
      [a["id"] for a in (achados or [])] == ["F2.1"], repr(cru))
checa("o órfão traz o caminho que veio do campo `files`",
      bool(achados) and achados[0]["paths"] == ["plugins/casa/lib/declarado.py"], repr(cru))  # acopla-ok: plugin fabricado de fixture; caminho-ok: caminho RELATIVO fabricado pelo teste e devolvido cru pelo git — não há disco para normalizar

print("test_orfaos: %d ok, %d falha(s)" % (ok, falhas))
sys.exit(1 if falhas else 0)
