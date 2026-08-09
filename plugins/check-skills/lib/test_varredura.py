#!/usr/bin/env python3
"""Bancada do varredor das cinco lentes. Cada caso reproduz um atropelo real medido.

    python3 test_varredura.py     # verde = 0
"""

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import varredura as C  # noqa: E402

FALHAS = []
TOTAL = [0]


def check(nome, cond):
    TOTAL[0] += 1
    print("  %s   %s" % ("ok " if cond else "FAIL", nome))
    if not cond:
        FALHAS.append(nome)


def monta(raiz, arvore):
    """arvore = {"market/plugin/versao": {"skills": {...}, "hooks_json": {...}}}

    `hooks_json` é o CONTEÚDO INTEIRO do arquivo, com o embrulho `{"hooks": …}` que o
    Claude Code exige. A primeira versão desta bancada chamava a chave de `hooks` e
    gravava o valor cru — o arquivo saía sem o embrulho, o varredor lia zero hook, e o
    caso vermelho acusava o programa por um defeito que era da bancada.
    """
    for caminho, conteudo in arvore.items():
        base = os.path.join(raiz, *caminho.split("/"))
        for nome, desc in (conteudo.get("skills") or {}).items():
            d = os.path.join(base, "skills", nome)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as fh:
                fh.write("---\nname: %s\ndescription: %s\n---\n\n# %s\n"
                         % (nome, desc, nome))
        hk = conteudo.get("hooks_json")
        if hk is not None:
            d = os.path.join(base, "hooks")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "hooks.json"), "w", encoding="utf-8") as fh:
                json.dump(hk, fh)
        os.makedirs(base, exist_ok=True)


def com_script(raiz, caminho, corpo):
    f = os.path.join(raiz, *caminho.split("/"))
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, "w", encoding="utf-8") as fh:
        fh.write(corpo)
    return f


def main():
    print("varredor de conflitos — bancada\n")

    # ── 1 · SÓ A VERSÃO MAIS ALTA CONTA ──────────────────────────────────────
    # A varredura ingênua lia TODA versão do cache e contava a mesma colisão
    # dezoito vezes: o `bootstrap` sozinho tinha 17 versões paradas no disco.
    d = tempfile.mkdtemp(prefix="confl-ver-")
    try:
        monta(d, {"mkt/alfa/1.0.0": {"skills": {"x": "um"}},
                  "mkt/alfa/1.10.0": {"skills": {"x": "dez"}},
                  "mkt/alfa/1.9.0": {"skills": {"x": "nove"}}})
        inst = C.instalados(d)
        check("a versão que roda é a mais alta, e 1.10 > 1.9",
              inst[("mkt", "alfa")]["versao"] == "1.10.0")
        check("as paradas são contadas à parte",
              sorted(inst[("mkt", "alfa")]["outras"]) == ["1.0.0", "1.9.0"])
        check("a skill aparece UMA vez, não uma por versão",
              len(C.skills(inst)) == 1)
        r = C.varre(inst)
        check("cache inchado vira achado próprio", len(r["cache_inchado"]) == 1)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ── 2 · NOME REPETIDO ────────────────────────────────────────────────────
    d = tempfile.mkdtemp(prefix="confl-nome-")
    try:
        monta(d, {"mkt/alfa/1.0.0": {"skills": {"setup": "configura o alfa"}},
                  "mkt/beta/1.0.0": {"skills": {"setup": "configura o beta"}},
                  "outro/gama/1.0.0": {"skills": {"unico": "sozinho"}}})
        r = C.varre(C.instalados(d))
        check("duas skills com o mesmo nome são acusadas",
              len(r["nome_repetido"]) == 1 and r["nome_repetido"][0]["nome"] == "setup")
        check("nome único não é acusado",
              all(n["nome"] != "unico" for n in r["nome_repetido"]))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ── 3 · PALAVRA INTEIRA, NUNCA PEDAÇO DE OUTRA ───────────────────────────
    # A primeira varredura casou "ui" dentro de "constrUI" e devolveu 37 skills
    # como se todas fizessem interface. Falso positivo em massa mata o relatório.
    check("'ui' NÃO casa dentro de construir",
          not C._cita("a skill que vai construir o plano", "ui"))
    check("'ui' casa quando é a palavra",
          C._cita("desenha a ui do aplicativo", "ui"))
    check("'test' NÃO casa dentro de conteste",
          not C._cita("ninguém conteste isso", "test"))
    check("palavra com acento antes não abre fronteira falsa",
          not C._cita("a produção parou", "ução"))

    # ── 4 · SÓ CONTA EVENTO COM MAIS DE UM MARKETPLACE ───────────────────────
    # Dois hooks MEUS no mesmo evento não são conflito: é desenho. O que interessa
    # é quando a origem é diferente e ninguém combinou nada.
    d = tempfile.mkdtemp(prefix="confl-ev-")
    try:
        def H(s):
            return {"hooks_json": {"hooks": {"Stop": [{"hooks": [
                {"type": "command", "command": s}]}]}}}
        monta(d, {"mkt/alfa/1.0.0": H("bash ${CLAUDE_PLUGIN_ROOT}/hooks/a.sh"),
                  "mkt/beta/1.0.0": H("bash ${CLAUDE_PLUGIN_ROOT}/hooks/b.sh")})
        r = C.varre(C.instalados(d))
        check("mesmo marketplace no mesmo evento NÃO é conflito",
              not r["evento_disputado"])
        monta(d, {"outro/gama/1.0.0": H("bash ${CLAUDE_PLUGIN_ROOT}/hooks/c.sh")})
        r = C.varre(C.instalados(d))
        check("marketplaces diferentes no mesmo evento É conflito",
              len(r["evento_disputado"]) == 1
              and r["evento_disputado"][0]["evento"] == "Stop")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ── 5 · QUEM BARRA É LIDO DO SCRIPT, NÃO DO NOME ─────────────────────────
    # `handoff-completeness-gate` tem nome de portão e NÃO barra; `askq-humanize`
    # não tem, e barra. Julgar pelo nome erraria nos dois.
    d = tempfile.mkdtemp(prefix="confl-barra-")
    try:
        mudo = com_script(d, "s/mudo.sh", "#!/bin/sh\necho oi\nexit 0\n")
        duro = com_script(d, "s/duro.sh", '#!/bin/sh\nprintf \'{"permissionDecision":"deny"}\'\n')
        check("script que só fala não é marcado como barra", not C._barra(mudo))
        check("script que devolve recusa é marcado", C._barra(duro))
        check("caminho inexistente não estoura", not C._barra(os.path.join(d, "nao-existe")))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ── 6 · CACHE AUSENTE NÃO ESTOURA ────────────────────────────────────────
    check("cache que não existe devolve vazio, sem exceção",
          C.instalados("/caminho/que/nao/existe") == {})

    # ── 7 · VAZAMENTO NO CÓDIGO — a lente que nasceu dos 2125 órfãos ──────────
    # Um plugin de mentira com um defeito de cada linguagem. O caso que dá sentido
    # à lente é o ÚLTIMO: o disparo já consertado NÃO pode ser acusado, senão a
    # lista de achados nunca chega a zero e ninguém mais olha para ela.
    d = tempfile.mkdtemp(prefix="chk-vaza-")
    try:
        base = os.path.join(d, "market", "vazador", "1.0.0")
        os.makedirs(os.path.join(base, "lib"), exist_ok=True)
        os.makedirs(os.path.join(base, "skills", "s"), exist_ok=True)
        open(os.path.join(base, "skills", "s", "SKILL.md"), "w").write(
            "---\nname: s\ndescription: uma skill\n---\n")
        open(os.path.join(base, "lib", "a.py"), "w").write(
            "import subprocess\nsubprocess.run(['git', 'status'])\n")
        open(os.path.join(base, "lib", "b.mjs"), "w").write(
            "spawnSync('node', ['x.js'], { stdio: 'inherit' });\n")
        open(os.path.join(base, "lib", "c.sh"), "w").write(
            "#!/bin/sh\nnohup python3 servidor.py &\n")
        inst = C.instalados(d)
        v = C.vazamento_codigo(inst)
        riscos = {x["risco"] for x in v}
        check("acha o python que não fecha a entrada",
              any("fechar a entrada" in x for x in riscos))
        check("acha o python sem grupo próprio",
              any("grupo próprio" in x for x in riscos))
        check("acha o node que entrega o terminal",
              any("node entrega o terminal" in x for x in riscos))
        check("acha o shell que larga o processo",
              any("larga o processo" in x for x in riscos))
        check("todo achado diz de qual plugin é",
              all(x["plugin"] == "vazador" for x in v))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="chk-vaza-ok-")
    try:
        base = os.path.join(d, "market", "cuidadoso", "1.0.0")
        os.makedirs(os.path.join(base, "lib"), exist_ok=True)
        open(os.path.join(base, "lib", "a.py"), "w").write(
            "import subprocess\n"
            "subprocess.run(['git', 'status'], stdin=subprocess.DEVNULL,\n"
            "               start_new_session=True)\n")
        open(os.path.join(base, "lib", "b.mjs"), "w").write(
            "spawnSync('node', ['x.js'], { stdio: ['ignore','inherit','inherit'] });\n")
        check("disparo já consertado NÃO é acusado",
              C.vazamento_codigo(C.instalados(d)) == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="chk-vaza-isento-")
    try:
        base = os.path.join(d, "market", "isento", "1.0.0")
        os.makedirs(os.path.join(base, "lib"), exist_ok=True)
        open(os.path.join(base, "lib", "a.py"), "w").write(
            "import subprocess\n"
            "# vaza-ok: o comando é um literal que sempre termina\n"
            "subprocess.run(['true'])\n")
        check("a isenção escrita na linha de cima vale",
              C.vazamento_codigo(C.instalados(d)) == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ── 8 · VAZAMENTO VIVO — a metade que olha a máquina, não o código ────────
    # Sem processo plantado (plantar órfão numa bancada é pior que não testar), o
    # que se afirma é o CONTRATO: cada achado carrega o dono, e nada entra sem ele.
    vivos = C.vazamento_vivo()
    check("a leitura dos processos vivos não estoura", isinstance(vivos, list))
    check("todo processo vivo acusado tem plugin dono e pid",
          all(x.get("plugin") and x.get("pid") for x in vivos))
    check("cache vazio não acusa processo nenhum",
          C.vazamento_vivo({}) == [])

    # ── 9 · IRMÃO AUSENTE — a citação que não resolve NESTA máquina ───────────
    # O cobrador do repositório vê o texto e para aí. Aqui a pergunta é outra: o
    # irmão citado está no cache? Quando não está, `resolve-plugin.sh` devolve vazio
    # e o hook sai calado — e o achado tem que nomear QUEM depende e O QUE emudece.
    d = tempfile.mkdtemp(prefix="chk-irmao-")
    try:
        base = os.path.join(d, "mkt", "alfa", "1.0.0")
        os.makedirs(os.path.join(base, "hooks"), exist_ok=True)
        os.makedirs(os.path.join(base, "skills", "s"), exist_ok=True)
        open(os.path.join(base, "skills", "s", "SKILL.md"), "w").write(
            "---\nname: s\ndescription: uma skill\n---\n"
            "roda plugins/gama/lib/motor.py antes de tudo\n")  # acopla-ok: plugin de mentira, é o ausente que a bancada monta
        open(os.path.join(base, "hooks", "start.sh"), "w").write(
            '#!/bin/sh\n'
            'A=$("$CLAUDE_PLUGIN_ROOT"/hooks/resolve-plugin.sh beta hooks/aviso.sh)\n'
            'B=$("$CLAUDE_PLUGIN_ROOT"/hooks/resolve-plugin.sh gama lib/x.sh)\n')
        monta(d, {"mkt/beta/1.0.0": {"skills": {"b": "o irmão que está instalado"}}})
        r = C.varre(C.instalados(d))
        irm = r["irmao_ausente"]
        check("o irmão que ESTÁ no cache não é acusado",
              all(x["ausente"] != "beta" for x in irm))
        check("o irmão que NÃO está no cache é acusado",
              {x["ausente"] for x in irm} == {"gama"})
        check("o achado nomeia quem depende dele",
              all(x["plugin"] == "alfa" for x in irm))
        check("o achado nomeia o que fica mudo",
              sorted(x["mudo"] for x in irm) == ["lib/motor.py", "lib/x.sh"])
        check("o relatório humano nomeia o ausente",
              "gama não está instalado" in C.desenha(r))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ── 7 · GATILHO MORTO ────────────────────────────────────────────────────
    # Três skills da família de projeto continuavam se anunciando por /spec-to-plan,
    # /project-doc e /start-doc depois do rename: quem digitava o nome velho era
    # atendido por quem não se chama mais assim, e o novo não tinha gatilho nenhum.
    d = tempfile.mkdtemp(prefix="confl-morto-")
    try:
        monta(d, {"mkt/alfa/1.0.0": {"skills": {
            "plan": 'Use quando o usuario diz "/spec-to-plan", "vira plano" ou "/plan".',
            "doc": 'NAO substitui o /project-doc FULL. Roda /clear antes. '
                   # "alfa" é plugin INVENTADO da fixture, e o literal é o próprio caso
                   # de teste: caminho de arquivo não pode virar gatilho.
                   'Le plugins/alfa/lib/motor.py e .claude/docs/x.md.'}}})  # acopla-ok: fixture
        r = C.varre(C.instalados(d))
        mortos = r["gatilho_morto"]
        check("o gatilho que aponta pro nome morto é acusado",
              [(x["skill"], x["gatilho"]) for x in mortos]
              == [("doc", "/project-doc"), ("plan", "/spec-to-plan")])
        check("o gatilho que tem skill instalada não é acusado",
              all(x["gatilho"] != "/plan" for x in mortos))
        check("barra-nome solta em prosa, sem aspas, também é acusada",
              ("doc", "/project-doc") in [(x["skill"], x["gatilho"]) for x in mortos])
        check("comando de fábrica não é gatilho morto",
              all(x["gatilho"] != "/clear" for x in mortos))
        check("caminho de arquivo não vira gatilho",
              all(x["gatilho"] not in ("/lib", "/motor.py", "/docs", "/x.md")
                  for x in mortos))
        check("o relatório humano nomeia o gatilho morto",
              "/spec-to-plan aparece em" in C.desenha(r))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ── 8 · SEM SITUAÇÃO ─────────────────────────────────────────────────────
    # Apelido serve a quem lembra do nome da skill; frase de situação serve a quem
    # não lembra que ela existe. Lista de gatilho sem elo de situação — o caso real
    # era `Trigger em /principles, princípios de sistema` — não atende ninguém que
    # chegou pelo trabalho, e é exatamente o que esta lente separa.
    d = tempfile.mkdtemp(prefix="confl-situ-")
    try:
        monta(d, {"mkt/alfa/1.0.0": {"skills": {
            "molde": 'Modo de execução contínua. Use quando o usuário disser "sovai".',
            "apelido": 'Gera princípios. Trigger em /apelido, princípios de sistema.',
            "instala": 'Setup de máquina nova. Rode 1× depois de instalar o plugin.'}}})
        r = C.varre(C.instalados(d))
        sems = [x["skill"] for x in r["sem_situacao"]]
        check("a description que é só lista de apelido é acusada",
              sems == ["apelido"])
        check("o molde da skill de execução contínua passa",
              "molde" not in sems)
        check("situação escrita como 'depois de instalar' também passa",
              "instala" not in sems)
        check("o relatório humano nomeia quem não tem situação",
              "/apelido — só apelido" in C.desenha(r))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ── 9 · NOME DE FÁBRICA ──────────────────────────────────────────────────
    # Os dois lados: nome que disputa com um comando do harness sem isenção sai
    # acusado; nome que disputa COM isenção declarada sai com o motivo colado. E
    # quem não disputa nada não aparece — lente que acusa todo mundo ninguém abre.
    d = tempfile.mkdtemp(prefix="confl-fab-")
    try:
        lista = os.path.join(d, "fab.txt")
        with open(lista, "w", encoding="utf-8") as fh:
            fh.write("# comentário e linha vazia não viram nome\n\n"
                     "isento plan: decisão de 2026-08-08 — fica pelo apelido\n"
                     "isento mudo:\n"
                     "plan\ncompact\nmudo\n")
        nomes, isentos = C.fabrica(lista)
        check("a lista de fábrica sai do arquivo, sem comentário nem vazia",
              nomes == {"plan", "compact", "mudo"})
        check("isenção sem motivo escrito não conta",
              list(isentos) == ["plan"])

        monta(d, {"mkt/alfa/1.0.0": {"skills": {
            "plan": "Monta o plano. Use quando o usuário disser plano.",
            "compact": "Compacta. Use quando o usuário pedir.",
            "sozinha": "Nada disputa. Use quando o usuário pedir."}}})
        sk = C.skills(C.instalados(d))
        fab = C.nome_de_fabrica(sk, (nomes, isentos))
        porskill = {x["skill"]: x["motivo"] for x in fab}
        check("a disputa sem isenção é acusada", porskill.get("compact") == "")
        check("a disputa com isenção sai com o motivo escrito",
              "2026-08-08" in porskill.get("plan", ""))
        check("quem não disputa com a fábrica não aparece",
              "sozinha" not in porskill)
        check("sem disputa nenhuma a lente sai limpa",
              C.nome_de_fabrica([("m", "p", "sozinha", "")], (nomes, isentos)) == [])
        r = dict(C.varre(C.instalados(d)), nome_de_fabrica=fab)
        texto = C.desenha(r)
        check("o relatório humano nomeia a disputa sem isenção",
              "/compact — mkt/alfa disputa" in texto)
        check("o relatório humano mostra a isenção declarada",
              "/plan — mkt/alfa: isenção declarada" in texto)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # a lista de fábrica DE VERDADE, e as duas isenções decididas em 2026-08-08
    nomes_f, isentos_f = C.fabrica()
    check("a lista de fábrica declarada tem os comandos do harness: %d nomes"
          % len(nomes_f), {"plan", "compact", "clear", "init"} <= nomes_f)
    check("plan e start têm isenção com motivo escrito",
          all(len(isentos_f.get(n, "")) > 30 for n in ("plan", "start")))

    # as descriptions da família, lidas do REPOSITÓRIO — o cache pode estar
    # numa versão anterior à do disco, e é o disco que o commit publica
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    nomes, familia = set(), []
    for plug in sorted(os.listdir(os.path.join(raiz, "plugins"))):
        base = os.path.join(raiz, "plugins", plug, "skills")
        if not os.path.isdir(base):
            continue
        for nome in sorted(os.listdir(base)):
            sk = os.path.join(base, nome, "SKILL.md")
            if not os.path.isfile(sk):
                continue
            nomes.add(nome)
            if plug == "project-skills":
                familia.append((nome, C._descricao(sk)))
    sobrou = [(n, m.group(1)) for n, desc in familia
              for m in C.CITA_COMANDO.finditer(desc)
              if m.group(1).lstrip("/").split("/")[0] not in nomes]
    check("as %d descriptions da família não prometem gatilho sem skill: %s"
          % (len(familia), sobrou or "nenhum"), bool(familia) and not sobrou)

    # e a mesma leitura do disco cobra a situação em TODA skill do marketplace —
    # é este o número que o check L do release-gate segura
    dorepo = C.skills_do_repo(raiz)
    faltam = ["%s/%s" % (x["plugin"], x["skill"]) for x in C.sem_situacao(dorepo)]
    check("as %d skills do marketplace declaram situação de trabalho: %s"
          % (len(dorepo), faltam or "todas"), len(dorepo) > 20 and not faltam)

    print("\n%d checagem(ns) · %d falha(s)" % (TOTAL[0], len(FALHAS)))
    for f in FALHAS:
        print("   FALHOU: %s" % f)
    return 1 if FALHAS else 0


if __name__ == "__main__":
    sys.exit(main())
