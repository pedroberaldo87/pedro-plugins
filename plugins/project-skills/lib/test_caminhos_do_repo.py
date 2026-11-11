#!/usr/bin/env python3
"""Caminhos que vêm do repositório são validados antes de virar caminho de arquivo (P6).

Um repositório clonado traz arquivos que o plugin LÊ e que escolhem onde o plugin ESCREVE ou
o que ele LÊ: o `para_o_plano` de um arquivo de entrada, o `id` dentro de um `.plan.json`, o
id de uma costura do `organism.yaml`, a lista de arquivos de um sidecar de protótipo, o
`anexo-de` do frontmatter. Aqui cada achado ganha um caso que o reproduz com arquivos de
verdade num repositório de mentira (tudo em tempdir, nunca no HOME), e um caso do caminho
honesto que tem que continuar andando.

    hsf_61796229  plan_entrada: `para_o_plano` com `..`, absoluto ou symlink
    hsf_f3e6b56f  plan_state: `plan['id']` nunca validado ao carregar
    hsf_38d27434  plan_state: gravação segue symlink (`<plano>.tmp` e o relatório)
    hsf_f23c89f7  organism-gate: id da costura vira nome de arquivo
    hsf_2a7e522a  doc_load: o sidecar lê qualquer caminho, sem teto
    hsf_263e796b  doc_load/casa(): `anexo-de` e as partes de `casa()` escapam da casa

    python3 plugins/project-skills/lib/test_caminhos_do_repo.py
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import bash_posix  # noqa: E402
import casa_da_doc  # noqa: E402
import doc_load as dl  # noqa: E402
import plan_state as ps  # noqa: E402

PLUGIN = os.path.dirname(AQUI)
FAILS = []
TETO_SIDECAR = getattr(dl, "TETO_ARQUIVO_SIDECAR", 8 * 1024 * 1024)
BASH = bash_posix.bash_posix() or "bash"


def check(nome, cond, detalhe=""):
    if cond:
        print("  ok   %s" % nome)
    else:
        print("  FAIL %s  %s" % (nome, detalhe))
        FAILS.append(nome)


def escreve(caminho, texto):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as fh:
        fh.write(texto)


def le(caminho):
    with open(caminho, encoding="utf-8") as fh:
        return fh.read()


def plano(plan_id="p-teste", fase_extra=False):
    return {"id": plan_id, "title": "plano de teste", "status": "active",
            "requisitos": [{"id": "S-1", "titulo": "t", "ca": "c"}],
            "phases": [{"id": "F1", "title": "f", "items": [
                {"id": "F1.1", "title": "i", "desc": "d", "requisito": "S-1",
                 "pronto": "p", "status": "todo"}]}]}


def entrada(para):
    return {"para_o_plano": para,
            "itens_novos": [{"id": "F1.2", "fase": "F1", "title": "novo", "desc": "d",
                             "requisito": "S-1", "pronto": "p"}]}


def roda_py(*args, **kw):
    return subprocess.run([sys.executable] + list(args), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                          timeout=60, **kw)


tmp = tempfile.mkdtemp(prefix="caminhos-repo-")
try:
    # ── hsf_61796229 · plan_entrada ────────────────────────────────────────────────
    print("hsf_61796229 — plan_entrada: `para_o_plano` não escolhe o arquivo")
    ENTRADA_PY = os.path.join(AQUI, "plan_entrada.py")
    projeto = os.path.join(tmp, "e1")
    plans = os.path.join(projeto, ".claude", "plans")
    escreve(os.path.join(plans, "p-teste.plan.json"), json.dumps(plano()))
    vitima = os.path.join(projeto, ".claude", "fora.plan.json")          # irmão de plans/
    vitima_abs = os.path.join(tmp, "absoluto.plan.json")
    for v in (vitima, vitima_abs):
        escreve(v, json.dumps(plano("fora-do-plans")))
    antes = {v: le(v) for v in (vitima, vitima_abs)}

    for rotulo, para in (("com ..", "../fora"), ("absoluto", vitima_abs[:-len(".plan.json")]),
                         ("com barra", "sub/p-teste"), ("com ponto-ponto", "..")):
        for v in antes:                       # cada caso parte das vítimas intactas
            escreve(v, antes[v])
        os.makedirs(os.path.join(plans, "entrada"), exist_ok=True)
        escreve(os.path.join(plans, "entrada", "x-%s.json" % rotulo.replace(" ", "-")),
                json.dumps(entrada(para)))
        r = roda_py(ENTRADA_PY, "--dir", plans)
        check("`para_o_plano` %s: o arquivo de fora NÃO é lido nem gravado" % rotulo,
              all(le(v) == antes[v] for v in antes), r.stdout[-300:])
        check("`para_o_plano` %s: recusado com rc=1 e o motivo dito" % rotulo,
              r.returncode == 1 and "⛔" in r.stdout, "rc=%d %r" % (r.returncode, r.stdout[-200:]))
        shutil.rmtree(os.path.join(plans, "entrada"), ignore_errors=True)

    # --plano na linha de comando passa pela mesma régua
    escreve(os.path.join(plans, "entrada", "y.json"), json.dumps({"itens_novos": entrada("x")["itens_novos"]}))
    r = roda_py(ENTRADA_PY, "--dir", plans, "--plano", "../fora")
    check("`--plano ../fora` também é recusado", r.returncode == 1 and le(vitima) == antes[vitima],
          r.stdout[-200:])
    shutil.rmtree(os.path.join(plans, "entrada"), ignore_errors=True)

    # plano que é symlink: a gravação não atravessa
    alvo_link = os.path.join(tmp, "alvo-do-link.json")
    escreve(alvo_link, json.dumps(plano("link-plano")))
    os.symlink(alvo_link, os.path.join(plans, "link-plano.plan.json"))
    escreve(os.path.join(plans, "entrada", "z.json"), json.dumps(entrada("link-plano")))
    antes_link = le(alvo_link)
    r = roda_py(ENTRADA_PY, "--dir", plans)
    check("plano que é symlink: o alvo do link NÃO é reescrito", le(alvo_link) == antes_link, r.stdout[-200:])
    check("plano que é symlink: recusado com motivo dito", r.returncode == 1 and "symlink" in r.stdout,
          r.stdout[-200:])
    shutil.rmtree(os.path.join(plans, "entrada"), ignore_errors=True)

    # `<plano>.tmp` plantado como symlink: o alvo do link não é escrito, e o caso honesto anda
    vit_tmp = os.path.join(tmp, "vitima-tmp.txt")
    escreve(vit_tmp, "intacta")
    os.symlink(vit_tmp, os.path.join(plans, "p-teste.plan.json.tmp"))
    escreve(os.path.join(plans, "entrada", "w.json"), json.dumps(entrada("p-teste")))
    r = roda_py(ENTRADA_PY, "--dir", plans)
    check("o caso honesto (id simples) segue incorporando", r.returncode == 0 and "F1.2" in le(
        os.path.join(plans, "p-teste.plan.json")), "rc=%d %r" % (r.returncode, r.stdout[-200:]))
    check("`<plano>.tmp` symlink: o alvo do link não foi escrito", le(vit_tmp) == "intacta")

    # ── hsf_f3e6b56f · plan_state: plan['id'] ──────────────────────────────────────
    print("hsf_f3e6b56f — plan_state: o id do plano tem de casar com o nome do arquivo")
    pasta = os.path.join(tmp, "ps1", ".claude", "plans")
    escreve(os.path.join(pasta, "honesto-um.plan.json"), json.dumps(plano("honesto-um")))
    escreve(os.path.join(pasta, "torto-dois.plan.json"), json.dumps(plano("../../escapou")))
    try:
        ps.pick_plan(pasta, "torto-dois")
        recusou = False
    except ps.PlanError as exc:
        recusou = "id" in str(exc)
    check("pick_plan(id): plano cujo `id` interno difere do nome do arquivo é recusado", recusou)
    check("list_plans: o plano de id torto não entra na listagem",
          [p["id"] for p in ps.list_plans(pasta)] == ["honesto-um"], repr(ps.list_plans(pasta)))
    try:
        sobra = ps.pick_plan(pasta)["id"]
    except ps.PlanError as exc:
        sobra = str(exc)
    check("pick_plan sem id: sobra só o honesto", sobra == "honesto-um", sobra)
    check("pick_plan(id) do honesto segue andando", ps.pick_plan(pasta, "honesto-um")["id"] == "honesto-um")

    for ruim in ("../fora", "/abs/fora", "a/b", "..", ""):
        try:
            ps.plan_path(pasta, ruim)
            recusou = False
        except ps.PlanError:
            recusou = True
        check("plan_path(%r) é recusado" % ruim, recusou)

    fora_ps = os.path.join(tmp, "ps1", ".claude", "escapou.plan.json")
    try:
        ps.save(pasta, plano("../escapou"))
    except ps.PlanError:
        pass
    check("save() com id `../escapou` não grava fora da pasta", not os.path.exists(fora_ps))

    # ── hsf_38d27434 · plan_state: gravação via symlink ────────────────────────────
    print("hsf_38d27434 — plan_state: a gravação não segue symlink")
    pasta2 = os.path.join(tmp, "ps2", ".claude", "plans")
    os.makedirs(pasta2)
    vit1 = os.path.join(tmp, "vit-tmp-ps.txt")
    escreve(vit1, "intacta")
    os.symlink(vit1, os.path.join(pasta2, "meu-plano.plan.json.tmp"))
    ps.save(pasta2, plano("meu-plano"))
    check("`<plano>.plan.json.tmp` symlink: o alvo do link não foi escrito", le(vit1) == "intacta")
    check("e o plano foi gravado de verdade, como arquivo comum",
          json.loads(le(os.path.join(pasta2, "meu-plano.plan.json")))["id"] == "meu-plano"
          and not os.path.islink(os.path.join(pasta2, "meu-plano.plan.json")))

    vit2 = os.path.join(tmp, "vit-plano-ps.json")
    escreve(vit2, json.dumps(plano("alvo-link")))
    os.symlink(vit2, os.path.join(pasta2, "alvo-link.plan.json"))
    antes2 = le(vit2)
    try:
        ps.save(pasta2, plano("alvo-link"))
        recusou = False
    except ps.PlanError as exc:
        recusou = "symlink" in str(exc)
    check("`<plano>.plan.json` symlink: save() recusa, dizendo symlink", recusou)
    check("`<plano>.plan.json` symlink: o alvo do link não foi reescrito", le(vit2) == antes2)

    # o relatório de pré-check que o tique resela
    raiz3 = os.path.join(tmp, "ps3")
    pasta3 = os.path.join(raiz3, ".claude", "plans")
    os.makedirs(pasta3)
    p3 = plano("plano-tres")
    import precheck_largada as pl  # noqa: E402
    rel = {"marca": pl.marca(p3, raiz3), "propostas": [], "abertas": []}
    alvo_rel = pl.casa_do_relatorio(raiz3)
    vit3 = os.path.join(tmp, "vit-relatorio.json")
    escreve(vit3, json.dumps(rel))
    os.makedirs(os.path.dirname(alvo_rel), exist_ok=True)
    os.symlink(vit3, alvo_rel)
    antes3 = le(vit3)
    with contextlib.redirect_stderr(io.StringIO()):
        ressela = ps._gate_precheck(pasta3, p3)
    p3["phases"][0]["items"][0]["status"] = "done"      # o tique fecha o passo aberto
    if ressela:
        ressela()
    check("o resselador do pré-check NÃO escreve através de symlink", le(vit3) == antes3)

    # ── hsf_f23c89f7 · organism-gate ───────────────────────────────────────────────
    print("hsf_f23c89f7 — organism-gate: o id da costura não escolhe o nome do arquivo")
    # O gate é bash com caminho POSIX (`case "$FP" in /*`); no Windows ele liberta (fail-open) por
    # desenho e a fixture não exercita o deny — o caso vale onde o gate de fato roda.
    if sys.platform != "win32":
        GATE = os.path.join(PLUGIN, "hooks", "pretooluse-organism-gate.sh")
        raiz4 = os.path.join(tmp, "g1")
        tmpd = os.path.join(raiz4, "t")
        os.makedirs(tmpd)
        escreve(os.path.join(raiz4, ".claude", "organism.yaml"), """
    name: GATE-TEST
    modulos: [alpha, beta]
    costuras:
      - id: "../../escapou-gate"
        severidade: block
        grep_verificavel: true
        aresta_msg: alpha muda, beta quebra
        pontas:
          - modulo: alpha
            globs: ["alpha/api.py"]
            simbolos: ["X"]
          - modulo: beta
            globs: ["beta/c.py"]
            simbolos: ["X"]
    """)
        escreve(os.path.join(raiz4, "alpha", "api.py"), "X = 1\n")
        payload = json.dumps({"tool_name": "Edit", "session_id": "sessgate", "cwd": raiz4,
                              "tool_input": {"file_path": os.path.join(raiz4, "alpha", "api.py")}})
        env = dict(os.environ, TMPDIR=tmpd, TMP=tmpd, TEMP=tmpd)
        env.pop("ORGANISM_GATE", None)
        r = subprocess.run([BASH, GATE], input=payload, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env, cwd=raiz4, timeout=60)
        achados = []
        for dp, _, fs in os.walk(raiz4):
            achados += [os.path.join(dp, f) for f in fs if f.endswith(".denied")]
        check("o gate negou na costura (a fixture exercita o caminho do deny)",
              "deny" in r.stdout, "rc=%d out=%r err=%r" % (r.returncode, r.stdout[:200], r.stderr[:200]))
        check("o marcador `.denied` nasce DENTRO do estado do gate, nunca fora dele",
              achados and all(os.sep + "claude-organism-gate-sessgate" + os.sep in a for a in achados),
              repr(achados))
        check("nada nasceu no pai do estado (`escapou-gate.denied`)",
              not any(os.path.basename(a).startswith("escapou-gate") and
                      os.path.dirname(a) != os.path.join(tmpd, "claude-organism-gate-sessgate")
                      for a in achados), repr(achados))

    # ── hsf_2a7e522a · doc_load: a lista de arquivos do sidecar ────────────────────
    print("hsf_2a7e522a — doc_load: a lista do sidecar fica dentro do projeto, é arquivo e tem teto")
    raiz5 = os.path.join(tmp, "d1")
    escreve(os.path.join(raiz5, "dentro.txt"), "dentro")
    fora_txt = os.path.join(tmp, "segredo-fora.txt")
    escreve(fora_txt, "fora do projeto")
    os.symlink(fora_txt, os.path.join(raiz5, "elo.txt"))
    os.makedirs(os.path.join(raiz5, "pasta"))
    check("o caso honesto: arquivo dentro do projeto tem marca",
          dl._conjunto_sig(raiz5, ["dentro.txt"]) is not None)
    check("`../segredo-fora.txt` (sai do projeto) não é lido",
          dl._conjunto_sig(raiz5, ["../segredo-fora.txt"]) is None)
    check("caminho absoluto não é lido", dl._conjunto_sig(raiz5, [fora_txt]) is None)
    check("symlink que aponta para fora não é lido", dl._conjunto_sig(raiz5, ["elo.txt"]) is None)
    check("pasta não é arquivo", dl._conjunto_sig(raiz5, ["pasta"]) is None)
    if hasattr(os, "mkfifo"):           # FIFO não existe no Windows
        fifo = os.path.join(raiz5, "cano")
        os.mkfifo(fifo)
        # Um FIFO sem escritor trava o `open()` para sempre: o teste roda num processo com prazo.
        codigo = ("import sys; sys.path.insert(0, %r); import doc_load as dl;"
                  "print(dl._conjunto_sig(%r, ['cano']))" % (AQUI, raiz5))
        try:
            r = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True,
                               timeout=8, stdin=subprocess.DEVNULL)
            check("dispositivo/FIFO não é aberto (a leitura não trava e devolve None)",
                  r.stdout.strip() == "None", r.stdout + r.stderr)
        except subprocess.TimeoutExpired:
            check("dispositivo/FIFO não é aberto (a leitura não trava e devolve None)", False,
                  "travou no open() de um FIFO")
    grande = os.path.join(raiz5, "grande.bin")
    with open(grande, "wb") as fh:
        fh.truncate(TETO_SIDECAR + 1)
    check("arquivo acima do teto não é lido", dl._conjunto_sig(raiz5, ["grande.bin"]) is None)

    # ── hsf_263e796b · casa() e `anexo-de` ─────────────────────────────────────────
    print("hsf_263e796b — casa() e `anexo-de` não saem da casa da doc")
    raiz6 = os.path.join(tmp, "c1")
    escreve(os.path.join(raiz6, "docs", "design.md"), "---\nproject: x\n---\n# d\n")
    check("casa(raiz, 'design.md') segue devolvendo o arquivo da casa",
          casa_da_doc.casa(raiz6, "design.md") == os.path.join(raiz6, "docs", "design.md"))
    check("casa(raiz, 'sub/arq.md') (barra interna) segue valendo",
          casa_da_doc.casa(raiz6, "sub/arq.md").replace("\\", "/").endswith("/".join(("docs", "sub", "arq.md"))))
    for ruim in ("../fora.md", "../../etc/passwd", "/etc/passwd", "a/../../b", "..\\fora.md", "C:\\x"):
        try:
            casa_da_doc.casa(raiz6, ruim)
            recusou = False
        except ValueError:
            recusou = True
        check("casa(raiz, %r) é recusado" % ruim, recusou)

    os.makedirs(os.path.join(raiz6, "docs", "prototipo"))
    escreve(os.path.join(raiz6, "docs", "prototipo", "painel.html"), "<p>painel</p>")
    escreve(os.path.join(tmp, "design-de-fora.md"), "segredo")
    sidecar = ("---\nnatureza: anexo\nanexo-de: %s\ndesign-sig: 1\nstatus: approved\n---\n\n"
               "## Arquivos\n\n- " + "/".join(("docs", "prototipo", "painel.html")) + "\n")
    escreve(os.path.join(raiz6, "docs", "prototipo", "x.prototipo.md"), sidecar % "../../../design-de-fora.md")
    try:
        anexos = dl.le_anexos(raiz6)
        err = ""
    except Exception as exc:     # a recusa de casa() não pode derrubar o /doc-load inteiro
        anexos, err = None, repr(exc)
    check("`anexo-de` com `..`: o /doc-load não cai", anexos is not None, err)
    check("`anexo-de` com `..`: o anexo não vale como acordo",
          anexos is not None and len(anexos) == 1 and anexos[0]["vale"] is False, repr(anexos))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if FAILS:
    print("FALHOU: %d" % len(FAILS))
    for f in FAILS:
        print("  - %s" % f)
    sys.exit(1)
print("OK")
