#!/usr/bin/env python3
"""Suite do plan_state.py. Stdlib pura, sem framework — o release-gate deste
repo roda `plugins/<nome>/lib/test_*.py` sozinho no commit.

O foco é o que o módulo PROMETE impedir:
  - o título de um nó mudar sozinho entre um init e o seguinte
  - um passo virar "concluído" sem prova
  - um nó sumir do arquivo porque o init seguinte esqueceu dele
"""

import json
import os
import re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_state as ps  # noqa: E402

FAILS = []


def _ns(**kw):
    import argparse
    return argparse.Namespace(**kw)


def check(label, cond):
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s" % label)
        FAILS.append(label)


def raises(label, fn, needle=None):
    try:
        fn()
    except ps.PlanError as exc:
        if needle and needle not in str(exc):
            print("  FAIL %s (mensagem sem %r: %s)" % (label, needle, exc))
            FAILS.append(label)
        else:
            print("  ok   %s" % label)
        return
    print("  FAIL %s (não levantou PlanError)" % label)
    FAILS.append(label)


def _levanta(fn):
    try:
        fn()
        return False
    except ps.PlanError:
        return True


def bullet(linhas, rotulo):
    """O bullet cujo rótulo casa, ou "" — busca por CONTEÚDO, nunca por índice.

    Índice quebra a cada mudança de layout (linha em branco nova, emoji novo) sem que
    nada de comportamento tenha mudado. Aconteceu duas vezes em 2026-08-03.
    """
    for ln in linhas:
        if ("%s:" % rotulo) in ln:
            return ln
    return ""


def sample(**over):
    plan = {
        "id": "2026-07-27-teste",
        "title": "Plano de teste",
        "phases": [
            {"id": "F1", "title": "Primeira fase", "items": [
                {"id": "F1.1", "title": "Passo um", "desc": "faz a primeira coisa"},
                {"id": "F1.2", "title": "Passo dois", "desc": "faz a segunda coisa"},
            ]},
            {"id": "F2", "title": "Segunda fase", "items": [
                {"id": "F2.1", "title": "Passo tres", "desc": "faz a terceira coisa"},
            ]},
        ],
    }
    plan.update(over)
    return plan


class Args(object):
    def __init__(self, **kw):
        self.dir = kw.pop("dir", None)
        self.plan = kw.pop("plan", None)
        for k, v in kw.items():
            setattr(self, k, v)


def completo(plan):
    """Preenche `pronto` e `requisito` em toda tarefa que não os declara.

    O `init` cobra os dois de tarefa que nasce agora, e num plano de teste TODAS
    nascem agora. Os casos que provam a cobrança passam os campos de propósito
    (ou os omitem de propósito) e chamam `ps.validate` direto; os outros usam
    isto pra não repetir o preenchimento em ~15 lugares.
    """
    declarados = {r["id"] for r in plan.get("requisitos") or []}
    citados = set()
    for ph in plan.get("phases") or []:
        for it in ph.get("items") or []:
            it.setdefault("pronto", "o comando roda e sai 0")
            it.setdefault("requisito", "S-0.1")
            citados.add(it["requisito"])
    # o bloco tem que cobrir TODO id citado, senão o próprio molde cai na recusa
    # por requisito inexistente — que é uma regra de verdade, não do molde
    faltam = sorted(citados - declarados)
    if faltam:
        plan.setdefault("requisitos", [])
        plan["requisitos"] += [{"id": r, "titulo": "Requisito do molde",
                                "ca": "o comando sai 0", "epico": "E0 — Molde"}
                               for r in faltam]
    return plan


SKILL_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "skills", "visual", "SKILL.md")


def planos_da_skill(texto):
    """Os blocos ```json da skill que são plano copiável.

    Bloco com `…` no meio é recorte de prosa, não exemplo — não parseia e fica
    de fora. O que sobra é exatamente o que alguém copia e cola no `init`.
    """
    achados = []
    for bloco in re.findall(r"```json\n(.*?)```", texto, re.S):
        try:
            obj = json.loads(bloco)
        except ValueError:
            continue
        if isinstance(obj, dict) and obj.get("phases"):
            achados.append(obj)
    return achados


def paragrafo_com(texto, agulha):
    for par in texto.split("\n\n"):
        if agulha in par:
            return par
    return ""


def init_into(d, plan, renames=None, crus=False):
    """Grava o plano. Por padrão completa `pronto`/`requisito` — `crus=True` pra
    os casos que provam justamente a recusa por falta deles."""
    path = os.path.join(d, "_in.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(plan if crus else completo(plan), fh)
    return ps.cmd_init(Args(dir=d, file=path, rename=renames))


def load(d, pid="2026-07-27-teste"):
    with open(ps.plan_path(d, pid), encoding="utf-8") as fh:
        return json.load(fh)


def main():
    d = tempfile.mkdtemp(prefix="plan-state-test-")
    try:
        print("schema")
        check("plano válido passa", ps.validate(sample()) is not None)
        raises("id de fase fora do padrão é recusado",
               lambda: ps.validate(sample(phases=[{"id": "fase1", "title": "x", "items": [
                   {"id": "F1.1", "title": "t", "desc": "d"}]}])), "F<n>")
        raises("passo sem desc é recusado",
               lambda: ps.validate(sample(phases=[{"id": "F1", "title": "x", "items": [
                   {"id": "F1.1", "title": "t", "desc": "  "}]}])), "linha didática")
        raises("desc de parágrafo é recusada",
               lambda: ps.validate(sample(phases=[{"id": "F1", "title": "x", "items": [
                   {"id": "F1.1", "title": "t", "desc": "a" * 200}]}])), "o teto é 140")
        # A régua inteira, não só o teto: um passo com DUAS FRASES cabe em 140
        # caracteres e passava. É o parágrafo disfarçado que a linha didática existe
        # pra não ser (quality-goals.md, "A régua de estilo").
        raises("passo com duas frases é recusado",
               lambda: ps.validate(sample(phases=[{"id": "F1", "title": "x", "items": [
                   {"id": "F1.1", "title": "t",
                    "desc": "O gate roda no commit. Sem bump ele barra."}]}])),
               "duas frases")
        raises("pronto que abre com conectivo de continuação é recusado",
               lambda: ps.validate(sample(phases=[{"id": "F1", "title": "x", "items": [
                   {"id": "F1.1", "title": "t", "desc": "d",
                    "pronto": "e o comando sai 0"}]}])), "conectivo")
        raises("prefixo do passo tem que bater com a fase",
               lambda: ps.validate(sample(phases=[{"id": "F1", "title": "x", "items": [
                   {"id": "F2.1", "title": "t", "desc": "d"}]}])), "prefixo")
        raises("id repetido é recusado",
               lambda: ps.validate(sample(phases=[{"id": "F1", "title": "x", "items": [
                   {"id": "F1.1", "title": "a", "desc": "d"},
                   {"id": "F1.1", "title": "b", "desc": "d"}]}])), "repetido")

        print("erros_do_plano")
        check("plano bom devolve lista vazia", ps.erros_do_plano(sample()) == [])
        errs = ps.erros_do_plano(sample(phases=[{"id": "F1", "title": "x", "items": [
            {"id": "F1.1", "title": "t", "desc": "a" * 200}]}]))
        check("plano ruim devolve mensagem sem levantar",
              len(errs) == 1 and "o teto é 140" in errs[0])
        check("validate continua levantando",
              _levanta(lambda: ps.validate(sample(phases=[{"id": "F1", "title": "x", "items": [
                  {"id": "F1.1", "title": "t", "desc": "a" * 200}]}]))))

        print("os quatro campos")
        bom = sample(phases=[{"id": "F1", "title": "x", "items": [
            {"id": "F1.1", "title": "t", "desc": "d", "pronto": "`pytest -q` passa",
             "requisito": "S-9.5", "grupo": "Tela", "pendencia": "qual o padrão da URL?"}]}])
        check("os quatro campos passam", ps.erros_do_plano(bom) == [])
        magro = sample(phases=[{"id": "F1", "title": "x", "items": [
            {"id": "F1.1", "title": "t", "desc": "d"}]}])
        check("sem exigir, item sem os campos passa", ps.erros_do_plano(magro) == [])
        errs = ps.erros_do_plano(magro, exigir={"F1.1"})
        check("exigido, falta pronto E requisito", len(errs) == 2)
        check("a mensagem do pronto diz COMO se prova",
              any("pronto" in e and "prova" in e for e in errs))
        check("a mensagem do requisito diz UM",
              any("requisito" in e and "um" in e.lower() for e in errs))

        # A cobrança pega TODA tarefa que nasce agora — num plano novo, todas.
        # Deixar o plano novo passar faria o portão morder só a partir da SEGUNDA
        # gravação, que é o caso raro. O que fica de fora é só o que JÁ ESTÁ no
        # disco: reescrever 295 itens não pode ser o preço de adotar a regra.
        print("init cobra de toda tarefa que nasce agora")
        d2 = tempfile.mkdtemp(prefix="plan-novo-")
        try:
            check("plano NOVO sem os campos é recusado",
                  _levanta(lambda: init_into(d2, sample(phases=[
                      {"id": "F1", "title": "x", "items": [
                          {"id": "F1.1", "title": "t", "desc": "d"}]}]), crus=True)))
            # nasce cru direto no disco: imita o plano anterior à regra
            os.makedirs(d2, exist_ok=True)
            with open(os.path.join(d2, "2026-07-27-teste.plan.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(dict(sample(phases=[{"id": "F1", "title": "x", "items": [
                    {"id": "F1.1", "title": "t", "desc": "d"}]}]),
                    created="2026-07-01", status="active"), fh)
            com_novo = sample(phases=[{"id": "F1", "title": "x", "items": [
                {"id": "F1.1", "title": "t", "desc": "d"},
                {"id": "F1.2", "title": "novo", "desc": "d"}]}])
            check("item NOVO num plano ANTIGO sem os campos derruba o init",
                  _levanta(lambda: init_into(d2, com_novo, crus=True)))
            so_o_velho = sample(phases=[{"id": "F1", "title": "x", "items": [
                {"id": "F1.1", "title": "t", "desc": "d"}]}])
            init_into(d2, so_o_velho, crus=True)
            check("o item que JÁ estava no disco continua entrando sem os campos",
                  load(d2) is not None)
        finally:
            shutil.rmtree(d2, ignore_errors=True)

        print("init preserva os campos")
        d5 = tempfile.mkdtemp(prefix="plan-preserva-")
        try:
            init_into(d5, bom)
            # crus=True: o 2o init OMITE os campos de propósito — é isso que o
            # caso prova, e o `completo()` os preencheria, matando o teste
            init_into(d5, sample(phases=[{"id": "F1", "title": "x", "items": [
                {"id": "F1.1", "title": "t", "desc": "d"}]}]), crus=True)
            it = load(d5, "2026-07-27-teste")["phases"][0]["items"][0]
            check("requisito sobrevive a init que o omitiu", it.get("requisito") == "S-9.5")
            check("grupo sobrevive", it.get("grupo") == "Tela")
            check("pronto sobrevive", it.get("pronto") == "`pytest -q` passa")
        finally:
            shutil.rmtree(d5, ignore_errors=True)

        print("init")
        init_into(d, sample())
        p = load(d)
        check("grava com status active", p["status"] == "active")
        check("todo passo nasce em todo",
              all(i.get("status") == "todo" for _, i in ps.iter_items(p)))
        check("3 passos gravados", ps.plan_progress(p) == (0, 3))

        print("tick")
        raises("tick sem prova é recusado",
               lambda: ps.cmd_tick(Args(dir=d, node="F1.1", evidencia="")), "precisa de --evidencia")
        raises("prova curta demais é recusada",
               lambda: ps.cmd_tick(Args(dir=d, node="F1.1", evidencia="ok")), "precisa de --evidencia")
        raises("tick em fase é recusado",
               lambda: ps.cmd_tick(Args(dir=d, node="F1", evidencia="python3 test.py -> 12 OK")),
               "fecha sozinha")
        raises("tick em id inexistente é recusado",
               lambda: ps.cmd_tick(Args(dir=d, node="F9.9", evidencia="python3 test.py -> 12 OK")),
               "não existe")
        ps.cmd_tick(Args(dir=d, node="F1.1", evidencia="python3 test_plan_state.py -> 12 OK"))
        p = load(d)
        _, it = ps.find_item(p, "F1.1")
        check("prova fica gravada no passo", "test_plan_state.py" in (it.get("evidence") or ""))
        check("data de conclusão gravada", bool(it.get("done_at")))
        check("progresso do plano vai a 1/3", ps.plan_progress(p) == (1, 3))
        check("fase parcial fica em doing", ps.phase_status(p["phases"][0]) == "doing")
        ps.cmd_tick(Args(dir=d, node="F1.2", evidencia="git show a1b2c3d"))
        p = load(d)
        check("fase fecha sozinha quando os passos fecham",
              ps.phase_status(p["phases"][0]) == "done")

        print("validate no tick + pendencia")
        d3 = tempfile.mkdtemp(prefix="plan-tick-")
        try:
            init_into(d3, sample(phases=[{"id": "F1", "title": "x", "items": [
                {"id": "F1.1", "title": "a", "desc": "d"},
                {"id": "F1.2", "title": "b", "desc": "d"},
                {"id": "F1.3", "title": "c", "desc": "d",
                 "pendencia": "zera quando ele olha, ou acumula?"}]}]))
            arq = ps.plan_path(d3, "2026-07-27-teste")
            plano = json.load(open(arq, encoding="utf-8"))
            plano["phases"][0]["items"][0]["desc"] = "a" * 356   # edição à mão
            json.dump(plano, open(arq, "w", encoding="utf-8"), ensure_ascii=False)

            check("tique da tarefa DEFEITUOSA é recusado",
                  _levanta(lambda: ps.cmd_tick(Args(dir=d3, node="F1.1",
                                                    evidencia="rodei e passou"))))
            ps.cmd_tick(Args(dir=d3, node="F1.2", evidencia="rodei e passou"))
            check("tique de OUTRA tarefa passa com o plano sujo",
                  load(d3, "2026-07-27-teste")["phases"][0]["items"][1]["status"] == "done")
            check("pendencia aberta recusa o tique",
                  _levanta(lambda: ps.cmd_tick(Args(dir=d3, node="F1.3",
                                                    evidencia="rodei e passou"))))
        finally:
            shutil.rmtree(d3, ignore_errors=True)

        print("o critério de aceite ecoa quando o requisito fecha")
        raiz = tempfile.mkdtemp(prefix="plan-ca-")
        try:
            import io
            import contextlib
            os.makedirs(os.path.join(raiz, "docs"))
            planos = os.path.join(raiz, ".claude", "plans")
            os.makedirs(planos)
            with open(os.path.join(raiz, "docs", "PRD.md"), "w", encoding="utf-8") as fh:
                fh.write("## E1 — Base\n\n"
                         "- **S-1.1 Eco do critério** · F1 — corpo. CA: o comando sai 0.\n")
            init_into(planos, sample(phases=[{"id": "F1", "title": "x", "items": [
                {"id": "F1.1", "title": "a", "desc": "d", "requisito": "S-1.1"},
                {"id": "F1.2", "title": "b", "desc": "d", "requisito": "S-1.1"}]}]))

            def tick_out(node):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    ps.cmd_tick(Args(dir=planos, node=node, evidencia="rodei e passou"))
                return buf.getvalue()

            check("com tarefa irmã em aberto, não ecoa nada", "S-1.1 fechou" not in tick_out("F1.1"))
            fim = tick_out("F1.2")
            check("na última tarefa, o requisito é anunciado", "S-1.1 fechou (2/2 tarefas)" in fim)
            check("e o critério de aceite vem junto", "o comando sai 0" in fim)
            # O eco é RELATÓRIO, não estado: o requisito não ganha `status`, senão
            # seria estado duplicado — o mesmo motivo pelo qual a fase também não
            # tem. (A chave `requisitos` PODE existir: é a fonte declarada, não
            # estado. O que não pode é status dentro dela.)
            salvo = load(planos, "2026-07-27-teste")
            check("o requisito NÃO ganhou status no arquivo",
                  all("status" not in r and "done_at" not in r
                      for r in salvo.get("requisitos") or []))
        finally:
            shutil.rmtree(raiz, ignore_errors=True)

        print("state")
        raises("done via state é recusado (só tick tem prova)",
               lambda: ps.cmd_state(Args(dir=d, node="F2.1", value="done")), "só via tick")
        ps.cmd_state(Args(dir=d, node="F2.1", value="blocked"))
        check("bloqueado deixa a fase em doing", ps.phase_status(load(d)["phases"][1]) == "doing")
        ps.cmd_state(Args(dir=d, node="F2.1", value="todo"))

        print("init de novo — a trava anti-drift")
        renamed = sample()
        renamed["phases"][0]["title"] = "Primeira fase (reescrita pelo modelo)"
        raises("init com título diferente é RECUSADO",
               lambda: init_into(d, renamed), "init recusado")
        check("o arquivo continua com o título original",
              load(d)["phases"][0]["title"] == "Primeira fase")
        init_into(d, renamed, renames=[["F1", "Primeira fase (reescrita pelo modelo)"]])
        check("--rename explícito passa",
              load(d)["phases"][0]["title"] == "Primeira fase (reescrita pelo modelo)")

        print("init preserva estado e não perde nó")
        again = sample()
        again["phases"][0]["title"] = "Primeira fase (reescrita pelo modelo)"
        again["phases"] = again["phases"][:1]  # o init "esqueceu" a F2
        init_into(d, again)
        p = load(d)
        check("a fase esquecida foi MANTIDA", any(ph["id"] == "F2" for ph in p["phases"]))
        _, it = ps.find_item(p, "F1.1")
        check("a prova de um passo já feito sobrevive ao re-init",
              "test_plan_state.py" in (it.get("evidence") or ""))
        check("o progresso sobrevive ao re-init", ps.plan_progress(p) == (2, 3))
        check("fases voltam ordenadas", [ph["id"] for ph in p["phases"]] == ["F1", "F2"])

        print("nó novo entra")
        grown = sample()
        grown["phases"][0]["title"] = "Primeira fase (reescrita pelo modelo)"
        grown["phases"][1]["items"].append(
            {"id": "F2.2", "title": "Passo quatro", "desc": "acrescentado depois",
             "pronto": "aparece na árvore", "requisito": "S-1.1"})
        init_into(d, grown)
        p = load(d)
        check("passo novo acrescentado", ps.find_item(p, "F2.2")[1] is not None)
        check("passo novo nasce em todo", ps.find_item(p, "F2.2")[1]["status"] == "todo")
        check("total sobe pra 4", ps.plan_progress(p) == (2, 4))

        print("open e close")
        check("o plano aparece como aberto",
              [s["id"] for s in map(ps.summary, ps.list_plans(d))] == ["2026-07-27-teste"])
        s = ps.summary(load(d))
        check("open aponta a próxima fase não fechada", s["next"]["id"] == "F2")
        ps.cmd_close(Args(dir=d))
        check("plano encerrado sai de ativo", load(d)["status"] == "abandoned")
        raises("sem plano ativo, pick_plan explica", lambda: ps.pick_plan(d), "nenhum plano ativo")
        ps.cmd_reopen(Args(dir=d))
        check("reopen devolve o plano pra ativo", load(d)["status"] == "active")
        check("reopen apaga a data de encerramento", "closed_at" not in load(d))
        check("reopen preserva o progresso", ps.plan_progress(load(d)) == (2, 4))
        raises("reopen num plano já ativo é recusado",
               lambda: ps.cmd_reopen(Args(dir=d, plan="2026-07-27-teste")), "já está ativo")
        raises("reopen sem plano encerrado diz isso, não 'diga qual'",
               lambda: ps.cmd_reopen(Args(dir=d)), "não há plano encerrado")

        print("dois planos ativos")
        other = sample(id="2026-07-27-outro")
        init_into(d, other)
        third = sample(id="2026-07-27-terceiro")
        init_into(d, third)
        raises("ambiguidade não é adivinhada", lambda: ps.pick_plan(d), "diga qual")
        check("com id explícito resolve", ps.pick_plan(d, "2026-07-27-outro")["id"] == "2026-07-27-outro")

        print("render")
        txt = ps.render_text(load(d))
        check("texto traz o progresso", "0/3 passos" in txt or "2/4 passos" in txt)
        p = load(d)
        html_track = ps.render_html(p, "track")
        check("html usa o componente da árvore", 'class="plan-tree"' in html_track)
        check("acompanhamento não tem rádio", "<input type=\"radio\"" not in html_track)
        check("acompanhamento mostra a linha didática", "pt-desc" in html_track)
        html_appr = ps.render_html(p, "approve")
        check("aprovação usa o item revisável", 'class="feedback-item pt-phase"' in html_appr)
        check("aprovação tem 3 rádios por fase",
              html_appr.count('name="fb-1"') == 3)
        check("aprovação não repete os passos como segunda lista",
              html_appr.count('class="pt-item') == html_track.count('class="pt-item'))

        print("detail da fase — só na aprovação, dentro do <details>")
        raises("detail que não é lista de strings é recusado",
               lambda: ps.validate(sample(phases=[{"id": "F1", "title": "x", "detail": "texto solto",
                                                   "items": [{"id": "F1.1", "title": "t", "desc": "d"}]}])),
               "lista de linhas")
        det = sample(id="2026-07-27-detalhe")
        det["phases"][0]["detail"] = ["🔧 Como: assim", "💡 Por quê: por isso"]
        init_into(d, det)
        p = ps.pick_plan(d, "2026-07-27-detalhe")
        check("acompanhamento NÃO mostra o detail",
              "item-detail" not in ps.render_html(p, "track"))
        ha = ps.render_html(p, "approve")
        check("aprovação mostra o detail", "item-detail" in ha and "🔧 Como: assim" in ha)
        check("fase sem detail não gera <details> vazio", ha.count("item-detail") == 1)

        print("vista de valor")
        reqs = {"S-4.3": {"titulo": "Orçamento de energia", "ca": "dia estourado corta",
                          "ancora": "Art. 6", "epico": "E4 — Planner"},
                "S-4.8": {"titulo": "Janela de medicação", "ca": "respeita horário",
                          "ancora": None, "epico": "E4 — Planner"}}
        p = sample(phases=[{"id": "F1", "title": "x", "items": [
            {"id": "F1.1", "title": "campo custo", "desc": "d",
             "requisito": "S-4.3", "grupo": "Backend"},
            {"id": "F1.2", "title": "tela do corte", "desc": "d",
             "requisito": "S-4.3", "grupo": "Tela", "pendencia": "qual cor?"},
            {"id": "F1.3", "title": "sem dono", "desc": "d"}]}])
        v = ps.render_text(p, reqs=reqs, vista="valor")
        check("mostra o épico", "E4 — Planner" in v)
        check("mostra o requisito com o artigo", "S-4.3" in v and "Art. 6" in v)
        check("agrupa por natureza", "Backend" in v and "Tela" in v)
        check("a pendência vira marca", "⛔" in v)
        check("tarefa sem requisito tem endereço próprio",
              "sem requisito" in v and "F1.3" in v)
        check("requisito sem tarefa aparece", "S-4.8" in v)

        e = ps.render_text(p)
        check("a vista de execução é o padrão", "F1 ·" in e and "E4 — Planner" not in e)
        limpo = ps.render_text(sample())
        check("plano antigo desenha igual a hoje", "⛔" not in limpo and "sem requisito" not in limpo)

        print("dobra no html")
        h = ps.render_html(p, mode="track", reqs=reqs, vista="valor")
        check("cada nível é um details", h.count("<details") >= 4)
        check("nasce fechado", " open" not in h)
        check("o resumo do nível está no summary", "<summary" in h and "S-4.3" in h)
        check("as marcas aparecem no summary fechado", "⛔" in h)
        check("continua escapando", "&lt;" in ps.render_html(sample(phases=[
            {"id": "F1", "title": "x", "items": [
                {"id": "F1.1", "title": "<script>", "desc": "d"}]}])))
        he = ps.render_html(p, mode="approve")
        check("a vista de aprovação não ganhou dobra nova",
              he.count("<details") == ps.render_html(sample(), mode="approve").count("<details"))

        # Nenhum plano real declara `requisito` ainda: a vista saía em branco num plano
        # de 157 tarefas — que é afirmar, por omissão, que não há trabalho nenhum.
        print("vista de valor num plano sem nenhum requisito")
        nada = sample(phases=[{"id": "F1", "title": "x", "items": [
            {"id": "F1.1", "title": "gravar o json", "desc": "init grava em .claude/plans"},
            {"id": "F1.2", "title": "ler de volta", "desc": "d", "grupo": "Backend"}]}])
        tv = ps.render_text(nada, reqs={}, vista="valor")
        check("o texto diz que ninguém declarou requisito", "declara requisito ainda" in tv)
        check("o texto desenha as tarefas assim mesmo", "F1.1" in tv and "F1.2" in tv)
        check("o texto agrupa pelo que sobrou", "Backend" in tv)
        hv0 = ps.render_html(nada, mode="track", reqs={}, vista="valor")
        check("o html diz que ninguém declarou requisito", "declara requisito ainda" in hv0)
        check("o html desenha as tarefas assim mesmo",
              'class="pt-item' in hv0 and "F1.1" in hv0 and "F1.2" in hv0)
        check("o html continua dobrável no fallback", hv0.count("<details") >= 2)
        check("a lista de ids não vem duas vezes", hv0.count(">F1.1<") == 1)

        print("a prova aparece na vista de valor")
        pr = sample(phases=[{"id": "F1", "title": "x", "items": [
            {"id": "F1.1", "title": "campo custo", "desc": "o que ainda seria feito",
             "requisito": "S-4.3", "grupo": "Backend",
             "status": "done", "evidence": "ls plano.json -> existe (sha 9f2a1)"}]}])
        tpv = ps.render_text(pr, reqs=reqs, vista="valor")
        check("texto: a prova entra no lugar da intenção", "prova: ls plano.json" in tpv)
        hpv = ps.render_html(pr, mode="track", reqs=reqs, vista="valor")
        check("html: a prova entra no lugar da intenção",
              "pt-evidence" in hpv and "9f2a1" in hpv)
        check("html: a descrição do que ainda seria feito sai",
              "o que ainda seria feito" not in hpv)

        print("a pendência aparece na vista de execução")
        pe = sample(phases=[{"id": "F1", "title": "x", "items": [
            {"id": "F1.1", "title": "decidir o formato", "desc": "faz a coisa",
             "pendencia": "A ou B?"}]}])
        tev = ps.render_text(pe)
        check("texto: a decisão em aberto aparece", "⛔ falta decidir: A ou B?" in tev)
        check("texto: a linha didática cede o lugar", "faz a coisa" not in tev)
        hev = ps.render_html(pe, mode="track")
        check("html: a decisão em aberto aparece", "⛔ falta decidir: A ou B?" in hev)
        check("aprovação: quem vai aprovar vê o bloqueio",
              "⛔ falta decidir: A ou B?" in ps.render_html(pe, mode="approve"))

        print("brief — 'onde nós estamos' em 1-3 bullets")
        b = sample(id="2026-07-27-brief")
        init_into(d, b)
        pl = ps.pick_plan(d, "2026-07-27-brief")
        L = ps.brief_lines(pl)
        check("no começo: cabeçalho + 3 bullets",
              len([x for x in L if x.startswith("•")]) == 3 and L[0].startswith("📍"))
        check("diz quanto já foi", "0 de 3 passos" in bullet(L, "Feito"))
        check("diz onde estamos agora", "F1" in bullet(L, "Agora"))
        check("diz o que falta", "3 passos" in bullet(L, "Falta"))
        check("os três rótulos entram com emoji — sem markdown, é o que dá contraste",
              all(e in "".join(L) for e in ("✅ Feito", "🔄 Agora", "⬜ Falta")))
        check("uma linha em branco separa o cabeçalho dos bullets", L[1] == "")
        # O canal do fim de turno é TEXTO no terminal: `**` e crase chegam literais e
        # viram ruído. Medido em produção (2026-08-03), com o dono lendo `**Feito:**` na tela.
        check("nenhuma linha do resumo emite markdown",
              not any("**" in x or "`" in x for x in L))
        check("nunca passa de 3 bullets", len([x for x in L if x.startswith("•")]) <= 3)

        # O teto de 3 é POR PLANO — e até 2026-08-02 era só isso que existia, então
        # N planos abertos davam 3×N bullets. Medido num projeto real: 4 planos
        # ativos renderam 16 linhas, num Stop que ja soma 6 hooks.
        print("brief — o teto vale para o CONJUNTO, não por plano")
        quatro = [ps.brief_lines(sample(id="p-%d" % i)) for i in range(4)]
        check("sem teto global, 4 planos dariam 20 linhas",
              sum(len(x) for x in quatro) == 20)
        cortado = ps._cabe_no_teto(quatro)
        check("com o teto, sobra 1 bloco + a linha da contagem", len(cortado) == 2)
        check("e o total cai de 20 para 6 linhas",
              sum(len(x) for x in cortado) == 6)
        check("o que foi cortado é CONTADO, não some em silêncio",
              "mais 3 plano(s) aberto(s)" in cortado[-1][0])
        check("a contagem diz como ver os outros",
              "plan_state.py open" in cortado[-1][0])
        check("um plano só não ganha linha de contagem",
              ps._cabe_no_teto(quatro[:1]) == quatro[:1])
        check("exatamente no teto também não ganha",
              len(ps._cabe_no_teto(quatro, teto=4)) == 4)

        # E2E pelo caminho REAL. Os checks acima chamam `_cabe_no_teto` direto, e
        # por isso não pegam quem tira a função do `print` do cmd_brief — sabotar
        # a chamada deixava a suíte verde. Testar a função não é testar o caminho.
        dbr = tempfile.mkdtemp(prefix="brief-teto-")
        try:
            for i in range(4):
                init_into(dbr, sample(id="cheio-%d" % i))
            import io
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ps.cmd_brief(Args(dir=dbr, nudge=None, closed_since=None, mark_seen=None))
            saida = buf.getvalue()
            check("E2E: com 4 planos, o comando sai com 1 bloco só",
                  saida.count("📍") == 1)
            check("E2E: e a contagem dos outros 3 aparece",
                  "mais 3 plano(s) aberto(s)" in saida)
            check("E2E: a saída inteira cabe em 6 linhas",
                  len([x for x in saida.strip().split("\n") if x.strip()]) <= 5)
        finally:
            shutil.rmtree(dbr, ignore_errors=True)

        # QUAL plano cabe no teto. `list_plans` entrega em ordem alfabética e o id
        # começa com a data de criação, então o único bloco que sobrava era o do
        # plano mais ANTIGO. Num projeto com frentes paralelas, a sessão que mexia
        # em Propostas recebia o "onde estamos" de PRISMA — e a frente dela ficava
        # escondida atrás do "e mais N".
        print("brief — o bloco que sobra é o da frente EM CURSO")
        dsel = tempfile.mkdtemp(prefix="brief-frente-")
        try:
            frentes = [("2026-06-01-prisma", "PRISMA"),
                       ("2026-07-15-video", "Video Review"),
                       ("2026-08-02-propostas", "Propostas")]
            for pid, titulo in frentes:
                init_into(dsel, sample(id=pid, title=titulo))
            # mtime crescente na ordem alfabética; depois a sessão toca o do MEIO,
            # que assim não é nem o primeiro nem o último por nome — só por recência.
            base = 1_700_000_000
            for i, (pid, _) in enumerate(frentes):
                os.utime(ps.plan_path(dsel, pid), (base + i, base + i))
            os.utime(ps.plan_path(dsel, "2026-07-15-video"), (base + 99, base + 99))

            import io
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ps.cmd_brief(Args(dir=dsel, nudge=None, closed_since=None, mark_seen=None))
            saida = buf.getvalue()
            check("o bloco é o do plano tocado por último", "Video Review" in saida)
            check("e não o do mais antigo por nome", "PRISMA" not in saida)
            check("nem o de nome mais recente", "Propostas" not in saida)
            check("os outros dois seguem contados", "mais 2 plano(s) aberto(s)" in saida)

            # Plano ilegível vai pro fim da fila em vez de derrubar a listagem.
            with open(ps.plan_path(dsel, "2026-08-02-propostas"), "w", encoding="utf-8") as fh:
                fh.write("{ nao e json")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ps.cmd_brief(Args(dir=dsel, nudge=None, closed_since=None, mark_seen=None))
            check("arquivo torto não derruba a escolha", "Video Review" in buf.getvalue())
        finally:
            shutil.rmtree(dsel, ignore_errors=True)

        # Medido em produção: a sessão mexia numa frente SEM plano próprio e o fim de
        # turno afirmava "Onde estamos" sobre a frente de outro plano, com progresso e
        # fase em curso. Ordenar por data não alcança — sem NENHUM plano tocado, o mais
        # recente ainda é de outra frente. O conteúdo continua saindo (orientação é o
        # que o hook existe pra dar); o que muda é o cabeçalho parar de AFIRMAR.
        print("brief — sem sinal da sessão, o cabeçalho relata em vez de afirmar")
        dses = tempfile.mkdtemp(prefix="brief-sessao-")
        try:
            for pid in ("2026-06-01-a", "2026-07-01-b", "2026-08-01-c"):
                init_into(dses, sample(id=pid, title="Frente " + pid[-1]))
            base = 1_700_000_000
            for pid in ("2026-06-01-a", "2026-07-01-b", "2026-08-01-c"):
                os.utime(ps.plan_path(dses, pid), (base, base))
            import io
            import contextlib

            def corre(marco, nudge=None):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    ps.cmd_brief(Args(dir=dses, nudge=nudge, closed_since=marco,
                                      mark_seen=None))
                return buf.getvalue()

            depois = corre(base + 500)          # marco POSTERIOR a todos os planos
            check("não afirma estar na frente que a sessão não tocou",
                  "Onde estamos" not in depois)
            check("relata a existência do plano em vez de situar quem lê nele",
                  "Plano aberto no projeto" in depois)
            check("o progresso continua saindo — o cabeçalho muda, o conteúdo não",
                  "de 3 passos" in depois and "Agora:" in depois)
            check("os outros planos seguem contados",
                  "mais 2 plano(s) aberto(s)" in depois)

            com_cobranca = corre(base + 500, nudge="⚠️ Nada marcado nesta sessão.")
            check("a cobrança do tique sobrevive à troca de cabeçalho",
                  "Nada marcado nesta sessão" in com_cobranca)

            antes = corre(base - 500)           # marco ANTERIOR: a sessão tocou os planos
            check("com plano tocado na sessão, a afirmação volta",
                  "Onde estamos" in antes)

            sem_marco = corre(None)             # sem marco não dá pra julgar
            check("sem marco da sessão, 'não sei' não vira 'não é desta sessão'",
                  "Onde estamos" in sem_marco)
        finally:
            shutil.rmtree(dses, ignore_errors=True)

        # Medido DUAS vezes em produção antes de virar código: num projeto com frentes
        # paralelas (6 sessões abertas no mesmo repositório em 2026-08-03), a vizinha
        # marcando um passo empurrava o plano DELA para o topo do fim de turno de todo
        # mundo. `mtime` diz que alguém mexeu, nunca QUEM — só a marca sabe.
        print("brief — cada sessão vê a frente que ELA marcou, não a da vizinha")
        dpar = tempfile.mkdtemp(prefix="brief-paralelo-")
        tmp_antigo = os.environ.get("TMPDIR")
        os.environ["TMPDIR"] = dpar
        try:
            init_into(dpar, sample(id="2026-08-01-propostas", title="Propostas"))
            init_into(dpar, sample(id="2026-08-02-videoreview", title="Video Review"))
            import io
            import contextlib
            import time

            def marca(sid, pid, node="F1.1"):
                antigo = os.environ.get("CLAUDE_CODE_SESSION_ID")
                os.environ["CLAUDE_CODE_SESSION_ID"] = sid
                try:
                    ps.cmd_state(Args(dir=dpar, plan=pid, node=node, value="doing"))
                finally:
                    if antigo is None:
                        os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
                    else:
                        os.environ["CLAUDE_CODE_SESSION_ID"] = antigo

            def brief_de(sid, marco):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    ps.cmd_brief(Args(dir=dpar, nudge=None, closed_since=marco,
                                      mark_seen=None, sessao=sid))
                return buf.getvalue()

            marca("sessao-A", "2026-08-01-propostas")
            marca("sessao-B", "2026-08-02-videoreview")   # a vizinha mexe DEPOIS

            futuro = time.time() + 60      # marco posterior a tudo: ninguém "tocou"
            a, b, c = (brief_de("sessao-A", futuro), brief_de("sessao-B", futuro),
                       brief_de("sessao-C", futuro))
            check("a sessão vê a frente que ela marcou, não a que mexeu por último",
                  "Propostas" in a and "Video Review" not in a.split("⋯")[0])
            check("a vizinha vê a dela", "Video Review" in b)
            check("quem marcou AFIRMA, mesmo com marco posterior — a marca é autoria",
                  "Onde estamos" in a)
            check("quem não marcou nada não afirma", "Onde estamos" not in c)
            check("e ainda assim recebe o resumo, sem sumir com o plano",
                  "Plano aberto no projeto" in c)

            # marca apontando pra plano encerrado não pode travar o resumo no passado
            ps.cmd_close(Args(dir=dpar, plan="2026-08-01-propostas"))
            depois = brief_de("sessao-A", futuro)
            check("marca de plano já encerrado cai no caminho sem marca",
                  "Onde estamos" not in depois)

            sem_arg = brief_de(None, futuro)
            check("chamada sem o id da sessão segue funcionando como antes",
                  "Plano aberto no projeto" in sem_arg)
        finally:
            if tmp_antigo is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = tmp_antigo
            shutil.rmtree(dpar, ignore_errors=True)

        ps.cmd_tick(Args(dir=d, plan="2026-07-27-brief", node="F1.1", evidencia="python3 t.py -> OK"))
        ps.cmd_tick(Args(dir=d, plan="2026-07-27-brief", node="F1.2", evidencia="commit a1b2c3d"))
        L = ps.brief_lines(ps.pick_plan(d, "2026-07-27-brief"))
        check("fase fechada aparece pelo id",
              "(F1)" in bullet(L, "Feito") and "1 fase" in bullet(L, "Feito"))
        check("não repete em Falta a fase que já está em Agora",
              "· fase" not in bullet(L, "Falta") and "· fases" not in bullet(L, "Falta"))
        tri = sample(id="2026-07-27-brief-tri")
        tri["phases"].append({"id": "F3", "title": "Terceira", "items": [
            {"id": "F3.1", "title": "t", "desc": "faz a terceira coisa"}]})
        init_into(d, tri)
        # fecha a F1 pra sobrar exatamente UMA fase além da atual (F2 é a atual, F3 a que falta)
        ps.cmd_tick(Args(dir=d, plan="2026-07-27-brief-tri", node="F1.1", evidencia="prova F1.1 ok"))
        ps.cmd_tick(Args(dir=d, plan="2026-07-27-brief-tri", node="F1.2", evidencia="prova F1.2 ok"))
        L3 = ps.brief_lines(ps.pick_plan(d, "2026-07-27-brief-tri"))
        check("com 1 fase além da atual, diz 'fase' no singular",
              "· fase F3" in bullet(L3, "Falta") and "· fases" not in bullet(L3, "Falta"))

        ps.cmd_tick(Args(dir=d, plan="2026-07-27-brief", node="F2.1", evidencia="prova final"))
        L = ps.brief_lines(ps.pick_plan(d, "2026-07-27-brief"))
        check("tudo marcado -> mensagem INEQUÍVOCA de concluído", L[0].startswith("✅ CONCLUÍDO"))
        check("o concluído diz o que prova", "com prova anexada" in L[1])
        check("o concluído manda encerrar", "close" in L[2])
        check("concluído também cabe em 3 bullets", len(L) == 3)

        ps.cmd_close(Args(dir=d, plan="2026-07-27-brief"))
        L = ps.brief_lines(ps.pick_plan(d, "2026-07-27-brief"))
        check("encerrado completo -> 🏁 inequívoco", L[0].startswith("🏁 PLANO ENCERRADO —"))
        check("encerrado aponta o arquivo de registro", ".plan.json" in L[2])

        inc = sample(id="2026-07-27-brief-inc")
        init_into(d, inc)
        ps.cmd_close(Args(dir=d, plan="2026-07-27-brief-inc"))
        L = ps.brief_lines(ps.pick_plan(d, "2026-07-27-brief-inc"))
        check("encerrado INCOMPLETO não finge conclusão", "incompleto" in L[0].lower())
        check("e diz quantos ficaram sem marcar", "sem marcar" in L[1])

        print("brief — o que ele NÃO fala")
        import io
        import contextlib

        def brief_out(**kw):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ps.cmd_brief(Args(dir=d, closed_since=kw.get("since"), mark_seen=None))
            return buf.getvalue()

        out = brief_out()
        check("plano encerrado não aparece sem --closed-since",
              "2026-07-27-brief" not in out and "ENCERRADO" not in out)
        out = brief_out(since=0)
        check("com --closed-since ele confirma o encerramento", "ENCERRADO" in out)
        print("brief — o teto de 3 bullets é do PEDIDO (achado da 2ª auditoria)")
        n = sample(id="2026-07-27-brief-nudge")
        init_into(d, n)
        pl = ps.pick_plan(d, "2026-07-27-brief-nudge")
        semn = ps.brief_lines(pl)
        comn = ps.brief_lines(pl, "⚠️ **Nada marcado nesta sessão**, e ela editou 4 arquivos.")
        check("sem cobrança: 3 bullets", len([x for x in semn if x.startswith("•")]) == 3)
        check("COM cobrança: continua 3 bullets, nunca 4",
              len([x for x in comn if x.startswith("•")]) == 3)
        check("a cobrança entra no lugar do 'Falta'",
              "Nada marcado" in comn[-1] and not any("Falta:" in x for x in comn))
        check("'Feito' e 'Agora' sobrevivem à cobrança",
              bullet(comn, "Feito") and bullet(comn, "Agora"))

        print("brief — o 🏁 sai UMA vez (achado da auditoria de 2026-07-27)")
        seen = os.path.join(d, "_seen.txt")

        def brief_seen():
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ps.cmd_brief(Args(dir=d, closed_since=0, mark_seen=seen))
            return buf.getvalue()

        primeiro = brief_seen()
        check("1ª chamada confirma o encerramento", "ENCERRADO" in primeiro)
        check("2ª chamada NÃO repete o mesmo encerramento",
              "2026-07-27-brief" not in brief_seen())
        outro = sample(id="2026-07-27-brief-outro")
        init_into(d, outro)
        ps.cmd_close(Args(dir=d, plan="2026-07-27-brief-outro"))
        check("mas um encerramento NOVO ainda é confirmado",
              "2026-07-27-brief-outro" in brief_seen() or "ENCERRADO" in brief_seen())
        check("o arquivo de vistos guarda os ids", "2026-07-27-brief" in open(seen).read())

        # O grupo dos encerrados não tinha teto NENHUM — "só o primeiro tem teto",
        # dizia o comentário. Com muito plano fechado desde o marco (limpeza de
        # diretório), o 🏁 inequívoco virava um despejo de 3 linhas por plano num
        # Stop que já soma 6 hooks. Agora ele tem teto próprio, e o que sobra é
        # CONTADO — que é a mesma garantia do grupo ativo.
        print("brief — o 🏁 também tem teto, e o cortado sai contado")
        denc = tempfile.mkdtemp(prefix="brief-encerrados-")
        try:
            for i in range(5):
                init_into(denc, sample(id="fechado-%d" % i))
                ps.cmd_close(Args(dir=denc, plan="fechado-%d" % i))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ps.cmd_brief(Args(dir=denc, nudge=None, closed_since=0, mark_seen=None))
            saida = buf.getvalue()
            check("5 encerrados dariam 5 blocos de 🏁; saem %d" % ps.BRIEF_MAX_ENCERRADOS,
                  saida.count("🏁") == ps.BRIEF_MAX_ENCERRADOS)
            check("os 3 cortados são contados, não somem em silêncio",
                  "mais 3 plano(s) encerrado(s)" in saida)
            check("a contagem diz onde ficou o registro de cada um",
                  ".claude/plans/" in saida)
            dois = [ps.brief_lines(ps.pick_plan(denc, "fechado-%d" % i)) for i in range(2)]
            check("dentro do teto, nenhum 🏁 é cortado e não há linha de contagem",
                  ps._cabe_no_teto(dois, ps.BRIEF_MAX_ENCERRADOS,
                                   ps.SOBRA_ENCERRADOS) == dois)
        finally:
            shutil.rmtree(denc, ignore_errors=True)

        # O teto é do CONJUNTO, e o caso que o quebrava era o volume: limpar o
        # diretório fecha dezessete planos de uma vez, e o grupo encerrado era
        # somado DEPOIS do corte do grupo ativo. Saíam dezessete blocos de 🏁 num
        # Stop que já soma 6 hooks. Cortar tudo junto engoliria o "acabou"; por
        # isso são dois tetos, e o excedente de cada um sai CONTADO.
        print("brief — 17 encerrados de uma vez não estouram o teto do conjunto")
        d17 = tempfile.mkdtemp(prefix="brief-17-")
        try:
            init_into(d17, sample(id="ainda-aberto"))
            for i in range(17):
                init_into(d17, sample(id="fechado-%02d" % i))
                ps.cmd_close(Args(dir=d17, plan="fechado-%02d" % i))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ps.cmd_brief(Args(dir=d17, nudge=None, closed_since=0, mark_seen=None))
            saida = buf.getvalue()
            linhas = [x for x in saida.strip().split("\n") if x.strip()]
            check("17 encerrados dariam 51 linhas de 🏁; a saída inteira sai com %d"
                  % len(linhas), len(linhas) <= 12)
            check("o 🏁 não foi engolido pelo teto", "🏁" in saida)
            check("saem %d blocos de 🏁, não 17" % ps.BRIEF_MAX_ENCERRADOS,
                  saida.count("🏁") == ps.BRIEF_MAX_ENCERRADOS)
            check("os 15 cortados saem contados, não somem em silêncio",
                  "mais 15 plano(s) encerrado(s)" in saida)
            check("e o plano que continua aberto não foi expulso pelos encerrados",
                  "ainda-aberto" in saida or "Plano de teste" in saida)
        finally:
            shutil.rmtree(d17, ignore_errors=True)

        # O resumo é o SÉTIMO emissor do canal de texto, e rodava sob o perfil da
        # PÁGINA — que não cobra markdown nem cabeçalho, porque HTML renderiza os
        # dois. O canal dele é o terminal do `stop-plan-status.sh`, onde `**` e
        # crase chegam literais e o destaque só vem do emoji. Os checks de markdown
        # logo acima eram a régua redigitada à mão aqui; agora quem cobra é o perfil.
        print("brief — o resumo roda sob o perfil do CANAL (hook), não o da página")
        check("o resumo declara o perfil do canal de texto", ps.PERFIL_BRIEF == "hook")
        dhk = tempfile.mkdtemp(prefix="brief-perfil-")
        try:
            init_into(dhk, sample(id="hook-1"))
            casos = [("em curso", ps.brief_lines(ps.pick_plan(dhk, "hook-1"))),
                     ("sem marca da sessão",
                      ps.brief_lines(ps.pick_plan(dhk, "hook-1"), desta_sessao=False)),
                     ("com cobertura",
                      ps.brief_lines(ps.pick_plan(dhk, "hook-1"), reqs=reqs)),
                     ("excedente de abertos", ps._cabe_no_teto([["a"], ["b"], ["c"]])[-1]),
                     ("excedente de encerrados",
                      ps._cabe_no_teto([["a"]] * 20, ps.BRIEF_MAX_ENCERRADOS,
                                       ps.SOBRA_ENCERRADOS)[-1])]
            for nid in ("F1.1", "F1.2", "F2.1"):
                ps.cmd_tick(Args(dir=dhk, plan="hook-1", node=nid,
                                 evidencia="rodou o teste e passou"))
            casos.append(("tudo marcado", ps.brief_lines(ps.pick_plan(dhk, "hook-1"))))
            ps.cmd_close(Args(dir=dhk, plan="hook-1"))
            casos.append(("encerrado", ps.brief_lines(ps.pick_plan(dhk, "hook-1"))))
            init_into(dhk, sample(id="hook-2"))
            ps.cmd_close(Args(dir=dhk, plan="hook-2"))
            casos.append(("encerrado incompleto",
                          ps.brief_lines(ps.pick_plan(dhk, "hook-2"))))
            for nome, linhas in casos:
                errs = ps.erros_do_brief(linhas, nome)
                check("resumo '%s' passa no perfil hook%s"
                      % (nome, (" — " + "; ".join(errs)) if errs else ""), errs == [])
            # Se o perfil não RECUSASSE o que o canal não renderiza, trocar de perfil
            # não teria mudado nada — o check tem que provar que ele morde.
            check("o perfil recusa markdown, que chega literal na tela",
                  any("markdown" in e
                      for e in ps.erros_do_brief(["• **Feito:** 2 de 3 passos"], "x")))
            check("o perfil recusa cabeçalho sem emoji",
                  any("emoji" in e
                      for e in ps.erros_do_brief(["Onde estamos — Plano de teste"], "x")))
            check("o MESMO texto passa na régua da página — quem manda é o canal",
                  ps.erros_de_estilo(["• **Feito:** 2 de 3 passos"], "x") == [])
        finally:
            shutil.rmtree(dhk, ignore_errors=True)

        # A régua vale pra TODO campo de texto que o gerador emite (quality-goals.md),
        # e até 2026-08-03 o validador só olhava campo vindo do spec: o literal que o
        # próprio programa escreve passava livre. Media 227 caracteres em 3 frases no
        # `.decisions-intro`, e 2 frases no `.feedback-intro` — em toda página que já
        # nasceu. A varredura audita o HTML PRONTO, que é onde o literal do programa e
        # o campo do spec ficam indistinguíveis — que é como o leitor os vê.
        print("régua — o literal que o próprio gerador escreve também é cobrado")
        import regua_audit as ra
        import visual_page as vp

        def viola(html, perfil_pag):
            ex = ra.Extrator(ra.PERFIS[perfil_pag]["fora"])
            ex.feed(html)
            return ra.violacoes_de(ex.eventos)

        def motivo(vs):
            return "" if not vs else " — " + "; ".join(
                "%s · %s" % (v["regra"], v["trecho"][:60]) for v in vs)

        with open(vp.TEMPLATE, encoding="utf-8") as fh:
            tpl_txt = fh.read()
        # Só estes dois blocos do template entram na página gerada (`extract_block`);
        # o resto do arquivo é demo e nunca é emitido — auditá-lo mediria o que
        # ninguém lê.
        for cls in ("decisions-box", "feedback-box"):
            vs = viola(vp.extract_block(tpl_txt, cls), "relatorio")
            check("literal do template .%s sob a régua%s" % (cls, motivo(vs)), vs == [])
        vs = viola(ps.CLOSING_BOX, "plano")
        check("literal da caixa de fechamento do plan_state sob a régua%s" % motivo(vs),
              vs == [])
        for chave, tupla in sorted(ps.PAGE_COPY.items()):
            for i, frase in enumerate(tupla):
                errs = ps.erros_de_estilo(frase, "PAGE_COPY[%s][%d]" % (chave, i))
                check("literal PAGE_COPY[%s][%d] sob a régua%s"
                      % (chave, i, (" — " + "; ".join(errs)) if errs else ""), errs == [])
        # E a página INTEIRA pelo caminho real: pega o literal que só existe montado,
        # e é o mesmo artefato que o `regua_audit.py` julga no disco.
        dlit = tempfile.mkdtemp(prefix="regua-literal-")
        try:
            init_into(dlit, sample(id="literal-1"))
            alvo = os.path.join(dlit, "pagina.html")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ps.cmd_page(Args(dir=dlit, plan="literal-1", mode="approve",
                                 vista="execucao", out=alvo))
            with open(alvo, encoding="utf-8") as fh:
                vs = viola(fh.read(), "plano")
            check("a página de aprovação inteira sai sem violação%s" % motivo(vs),
                  vs == [])
        finally:
            shutil.rmtree(dlit, ignore_errors=True)

        empty = tempfile.mkdtemp(prefix="plan-brief-vazio-")
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ps.cmd_brief(Args(dir=empty, closed_since=None, mark_seen=None))
            check("sem plano nenhum, cala", buf.getvalue() == "")
        finally:
            shutil.rmtree(empty, ignore_errors=True)

        print("o número aparece sem pedir")
        b = ps.brief_lines(p, reqs=reqs)
        check("o brief traz a cobertura",
              any(x.startswith("• 🎯 Cobertura:") and "requisito" in x for x in b))
        check("e ela cabe no teto do canal, com ou sem o ponteiro",
              all(len(x) <= ps.BULLET_MAX for x in b))
        check("a cobertura não vira um 4º bullet",
              len([x for x in b if x.startswith("•")]) == 3)
        b2 = ps.brief_lines(sample())
        check("plano sem os campos não ganha linha nova",
              not any("requisito" in x for x in b2))

        print("render escapa HTML (título vem de texto livre)")
        evil = sample(id="2026-07-27-escape", title="<script>alert(1)</script>")
        evil["phases"][0]["items"][0]["desc"] = 'aspas " e <b>tags</b>'
        init_into(d, evil)
        h = ps.render_html(ps.pick_plan(d, "2026-07-27-escape"))
        check("script no título vira texto", "<script>alert(1)</script>" not in h)
        check("tag na descrição vira texto", "<b>tags</b>" not in h)

        print("reabrir")
        d7 = tempfile.mkdtemp(prefix="plan-reabrir-")
        try:
            init_into(d7, sample(phases=[{"id": "F1", "title": "x", "items": [
                {"id": "F1.1", "title": "a", "desc": "d",
                 "decidido": {"por": "eu", "quando": "2026-08-01T10:00:00",
                              "escolha": "/app/{id}", "porque": "padrão das 3 telas",
                              "pergunta": "qual o padrão da URL?"}}]}]))
            ps.cmd_tick(Args(dir=d7, node="F1.1", evidencia="rodei e passou"))
            ps.cmd_reabrir(Args(dir=d7, node="F1.1"))
            it = load(d7, "2026-07-27-teste")["phases"][0]["items"][0]
            check("apaga a decisão", it.get("decidido") is None)
            check("restaura a pergunta", it.get("pendencia") == "qual o padrão da URL?")
            check("destica", it["status"] == "todo")
            check("limpa a prova", it.get("evidence") is None)
            check("sem decisão, não reabre",
                  _levanta(lambda: ps.cmd_reabrir(Args(dir=d7, node="F1.1"))))
        finally:
            shutil.rmtree(d7, ignore_errors=True)

        # O quarto estado do fio NÃO é aviso: citação que aponta pro nada recusa
        # gravar. Sem isto ela apodrece em silêncio — foi assim que 7 de 154 itens
        # de um plano real citaram artigo de lei sem ninguém conferir se existia.
        print("requisito inexistente recusa gravar")
        REQS = {"S-1.1": {"titulo": "Existe", "ca": "o comando sai 0",
                          "ancora": None, "epico": "E1 — Base"}}
        bom = sample(phases=[{"id": "F1", "title": "x", "items": [
            {"id": "F1.1", "title": "t", "desc": "d", "requisito": "S-1.1"}]}])
        check("requisito que existe passa", ps.validate(bom, reqs=REQS) is not None)
        ruim = sample(phases=[{"id": "F1", "title": "x", "items": [
            {"id": "F1.1", "title": "t", "desc": "d", "requisito": "S-99.9"}]}])
        check("requisito inexistente é recusado",
              _levanta(lambda: ps.validate(ruim, reqs=REQS)))
        check("sem reqs a checagem não roda (projeto sem documento não é erro)",
              ps.validate(ruim) is not None)

        # O requisito é obrigatório; o LUGAR dele é opcional. Sem esta porta, todo
        # projeto sem documento de requisitos volta a ter tarefa que não rastreia.
        print("requisitos declarados no próprio plano")
        com_bloco = dict(sample(phases=[{"id": "F1", "title": "x", "items": [
            {"id": "F1.1", "title": "t", "desc": "d", "requisito": "S-2.1"}]}]),
            requisitos=[{"id": "S-2.1", "titulo": "No plano", "ca": "sai 0",
                         "epico": "E2 — Aqui"}])
        lidos = ps._requisitos_do_plano(com_bloco)
        check("lê o bloco do plano", sorted(lidos) == ["S-2.1"])
        check("o bloco traz o critério de aceite", lidos["S-2.1"]["ca"] == "sai 0")
        check("plano sem bloco devolve vazio", ps._requisitos_do_plano(sample()) == {})
        check("o bloco do plano vence a cascata do projeto",
              sorted(ps._requisitos_do_projeto(d, com_bloco)) == ["S-2.1"])
        check("com o bloco, o requisito do plano é aceito",
              ps.validate(com_bloco, reqs=lidos) is not None)

        print("a vista não se sobrescreve nem é ignorada")
        pv = sample(phases=[{"id": "F1", "title": "x", "items": [
            {"id": "F1.1", "title": "t", "desc": "d", "requisito": "S-1.1"}]}])
        hv = ps.render_html(pv, mode="track", reqs=REQS, vista="valor")
        he = ps.render_html(pv, mode="track")
        check("as duas vistas produzem html diferente", hv != he)
        check("a vista de valor traz o épico", "E1 — Base" in hv)

        # O merge preservava com todo cuidado o campo `requisito` de CADA tarefa e
        # jogava fora o bloco pra onde esses campos apontam: sobravam os ponteiros e
        # sumia o destino — e como a checagem de citação órfã desliga quando não há
        # requisito nenhum, o mesmo init que apagava a fonte deixava de conferir.
        print("o merge não apaga o topo do plano")
        d8 = tempfile.mkdtemp(prefix="plan-topo-")
        try:
            v1 = dict(sample(id="2026-08-01-topo", phases=[
                {"id": "F1", "title": "x", "items": [
                    {"id": "F1.1", "title": "a", "desc": "d", "pronto": "sai 0",
                     "requisito": "S-1.1"}]}]),
                requisitos=[{"id": "S-1.1", "titulo": "Existe", "ca": "sai 0",
                             "epico": "E1 — Base"}])
            init_into(d8, v1, crus=True)
            v2 = sample(id="2026-08-01-topo", phases=[{"id": "F1", "title": "x", "items": [
                {"id": "F1.1", "title": "a", "desc": "d"},
                {"id": "F1.2", "title": "b", "desc": "d", "pronto": "sai 0",
                 "requisito": "S-1.1"}]}])
            init_into(d8, v2, crus=True)
            salvo = load(d8, "2026-08-01-topo")
            check("o bloco `requisitos` sobrevive ao init que o omitiu",
                  [r["id"] for r in salvo.get("requisitos") or []] == ["S-1.1"])
            orfa = sample(id="2026-08-01-topo", phases=[{"id": "F1", "title": "x", "items": [
                {"id": "F1.1", "title": "a", "desc": "d"},
                {"id": "F1.3", "title": "c", "desc": "d", "pronto": "sai 0",
                 "requisito": "S-9.9"}]}])
            check("com o bloco preservado, citação órfã continua sendo recusada",
                  _levanta(lambda: init_into(d8, orfa, crus=True)))
            ps.cmd_close(Args(dir=d8, plan="2026-08-01-topo"))
            init_into(d8, v2, crus=True)
            check("closed_at sobrevive ao init", "closed_at" in load(d8, "2026-08-01-topo"))
            vazio = dict(sample(id="2026-08-01-topo", phases=[
                {"id": "F1", "title": "x", "items": [
                    {"id": "F1.1", "title": "a", "desc": "d"},
                    {"id": "F1.2", "title": "b", "desc": "d"}]}]), requisitos=[])
            init_into(d8, vazio, crus=True)
            check("declarar o bloco vazio apaga de propósito",
                  load(d8, "2026-08-01-topo").get("requisitos") == [])
        finally:
            shutil.rmtree(d8, ignore_errors=True)

        # A caixa de fechamento entrava olhando só o `mode`, e a vista de valor não
        # desenha fase nenhuma: sobrava a página com os botões e ZERO veredito, e o
        # "Aprovar tudo" devolvia uma aprovação que ninguém tinha dado.
        print("aprovação não existe na vista de valor")
        d10 = tempfile.mkdtemp(prefix="plan-page-")
        try:
            init_into(d10, sample(id="2026-08-01-pagina"))
            alvo = os.path.join(d10, "p.html")
            raises("--mode approve --vista valor é recusado",
                   lambda: ps.cmd_page(Args(dir=d10, plan="2026-08-01-pagina",
                                            mode="approve", vista="valor", out=alvo)),
                   "execucao")
            check("nem o arquivo foi gravado", not os.path.exists(alvo))
            check("a mesma aprovação na vista de execução grava",
                  ps.cmd_page(Args(dir=d10, plan="2026-08-01-pagina", mode="approve",
                                   vista="execucao", out=alvo)) == 0
                  and '<strong id="fb-done">' in open(alvo, encoding="utf-8").read())
            check("track na vista de valor continua valendo",
                  ps.cmd_page(Args(dir=d10, plan="2026-08-01-pagina", mode="track",
                                   vista="valor", out=alvo)) == 0
                  and '<strong id="fb-done">' not in open(alvo, encoding="utf-8").read())
        finally:
            shutil.rmtree(d10, ignore_errors=True)

        print("o merge não apaga o `detail` da fase")
        d9 = tempfile.mkdtemp(prefix="plan-detail-")
        try:
            com = sample(id="2026-08-01-detail")
            com["phases"][0]["detail"] = ["🔧 Como: assim", "💡 Por quê: por isso"]
            init_into(d9, com)
            init_into(d9, sample(id="2026-08-01-detail"))   # o 2º init omite o detail
            check("detail da fase sobrevive ao init que o omitiu",
                  load(d9, "2026-08-01-detail")["phases"][0].get("detail")
                  == ["🔧 Como: assim", "💡 Por quê: por isso"])
        finally:
            shutil.rmtree(d9, ignore_errors=True)

        # Quem escreve o JSON do init é o modelo. Sem este portão, `status: "done"`
        # escrito à mão passava — e o brief anunciava "cada um com prova anexada".
        print("'done' escrito à mão sem prova é recusado")
        fraude = completo(sample(phases=[{"id": "F1", "title": "x", "items": [
            {"id": "F1.1", "title": "t", "desc": "d", "status": "done"}]}]))
        raises("done sem prova é recusado", lambda: ps.validate(fraude), "prova")
        curta = completo(sample(phases=[{"id": "F1", "title": "x", "items": [
            {"id": "F1.1", "title": "t", "desc": "d", "status": "done",
             "evidence": "ok"}]}]))
        check("prova curta demais também é recusada", _levanta(lambda: ps.validate(curta)))
        honesto = completo(sample(phases=[{"id": "F1", "title": "x", "items": [
            {"id": "F1.1", "title": "t", "desc": "d", "status": "done",
             "evidence": "python3 test_plan_state.py -> 12 OK"}]}]))
        check("done COM prova passa", ps.validate(honesto) is not None)

        print("o brief não afirma prova que não conferiu")
        semp = sample(phases=[{"id": "F1", "title": "x", "items": [
            {"id": "F1.1", "title": "t", "desc": "d", "status": "done"}]}])
        L = ps.brief_lines(semp)
        check("concluído sem prova não diz 'com prova anexada'",
              L[0].startswith("✅") and "prova anexada" not in L[1])
        meio = sample(phases=[
            {"id": "F1", "title": "x", "items": [
                {"id": "F1.1", "title": "t", "desc": "d", "status": "done"}]},
            {"id": "F2", "title": "y", "items": [
                {"id": "F2.1", "title": "t", "desc": "d"}]}])
        check("fase fechada sem prova não diz 'com prova em cada passo'",
              "prova em cada passo" not in ps.brief_lines(meio)[1])

        print("plano ilegível DIZ qual arquivo, em vez de estourar traceback")
        d10 = tempfile.mkdtemp(prefix="plan-ilegivel-")
        try:
            def erro(fn):
                try:
                    fn()
                    return "(não levantou nada)"
                except ps.PlanError as exc:
                    return str(exc)
                except Exception as exc:   # traceback bruto é exatamente o defeito
                    return "%s: %s" % (type(exc).__name__, exc)

            with open(ps.plan_path(d10, "2026-08-01-torto"), "w", encoding="utf-8") as fh:
                fh.write('{"id": "2026-08-01-torto", "phases": [')
            check("pick_plan com id explícito nomeia o arquivo torto",
                  "ilegível" in erro(lambda: ps.pick_plan(d10, "2026-08-01-torto")))
            check("init sobre arquivo torto explica em vez de estourar",
                  "ilegível" in erro(lambda: init_into(d10, sample(id="2026-08-01-torto"))))
        finally:
            shutil.rmtree(d10, ignore_errors=True)

        # A skill manda apagar a `pendencia` ao registrar a decisão, e o merge
        # ressuscitava o campo omitido. Quem resolve é a DECISÃO, não a ausência do
        # campo — assim o autor não precisa saber que existe um merge.
        print("decidir resolve a pendência")
        d11 = tempfile.mkdtemp(prefix="plan-decidido-")
        try:
            init_into(d11, sample(phases=[{"id": "F1", "title": "x", "items": [
                {"id": "F1.1", "title": "a", "desc": "d", "pendencia": "fila ou cron?"}]}]))
            check("sem decisão, a pendência trava o tique",
                  _levanta(lambda: ps.cmd_tick(Args(dir=d11, node="F1.1",
                                                    evidencia="rodei e passou"))))
            init_into(d11, sample(phases=[{"id": "F1", "title": "x", "items": [
                {"id": "F1.1", "title": "a", "desc": "d",
                 "decidido": {"por": "mais-reversivel", "quando": "2026-08-01T10:00:00",
                              "escolha": "cron", "porque": "menos peça nova",
                              "pergunta": "fila ou cron?"}}]}]), crus=True)
            ps.cmd_tick(Args(dir=d11, node="F1.1", evidencia="rodei e passou"))
            check("com a decisão registrada, o tique passa",
                  load(d11)["phases"][0]["items"][0]["status"] == "done")
            ps.cmd_reabrir(Args(dir=d11, node="F1.1"))
            check("reabrir volta a travar",
                  _levanta(lambda: ps.cmd_tick(Args(dir=d11, node="F1.1",
                                                    evidencia="rodei e passou"))))
        finally:
            shutil.rmtree(d11, ignore_errors=True)

        # O que a SKILL.md ENSINA tem que passar pelo próprio validador, e o que ela
        # PROMETE tem que ser o que o código faz. Exemplo que não grava e frase que
        # promete recusa onde não há recusa custam a mesma coisa: uma sessão perdida.
        print("a SKILL.md bate com o código")
        skill = open(SKILL_MD, encoding="utf-8").read()
        exemplos = planos_da_skill(skill)
        check("a skill tem exemplo de plano copiável", len(exemplos) >= 1)
        for n, ex in enumerate(exemplos):
            d12 = tempfile.mkdtemp(prefix="plan-skill-")
            try:
                path = os.path.join(d12, "_skill.json")
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(ex, fh)
                erro = None
                try:
                    ps.cmd_init(Args(dir=d12, file=path, rename=None))
                except ps.PlanError as exc:
                    erro = str(exc)
                check("exemplo %d da skill grava sem erro (%s)" % (n + 1, erro or "ok"),
                      erro is None)
            finally:
                shutil.rmtree(d12, ignore_errors=True)

        d13 = tempfile.mkdtemp(prefix="plan-sem-prd-")
        try:
            init_into(d13, sample(phases=[{"id": "F1", "title": "x", "items": [
                {"id": "F1.1", "title": "a", "desc": "d", "pronto": "roda o teste",
                 "requisito": "S-99.9"}]}]), crus=True)
            check("sem fonte de requisitos, citação inexistente GRAVA", True)
        except ps.PlanError:
            check("sem fonte de requisitos, citação inexistente GRAVA", False)
        finally:
            shutil.rmtree(d13, ignore_errors=True)
        frase = paragrafo_com(skill, "recusa gravar o plano")
        check("a frase da recusa diz que ela depende de haver fonte de requisitos",
              "quando o projeto tem fonte de requisitos" in frase.lower())
        check("a frase da recusa aponta o comando de quem não tem fonte",
              "cobertura" in frase)

        print("arquivo corrompido não derruba a listagem")
        before = len(ps.list_plans(d))
        with open(os.path.join(d, "quebrado.plan.json"), "w") as fh:
            fh.write("{ isto não é json")
        check("list_plans pula o corrompido", len(ps.list_plans(d)) == before)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ── F6 · a prova sai em bullets, e a linha corrida longa é recusada ──────
    print("F6: a prova do passo em bullets")
    pb = ps.prova_bullets
    check("quebra no separador de ponto", pb("a · b · c") == ["a", "b", "c"])
    check("quebra em ponto-e-virgula e em mais", pb("x; y + z") == ["x", "y", "z"])
    check("quebra na linha nova",
          pb("$ cmd\n  saida 1\n  saida 2") == ["$ cmd", "saida 1", "saida 2"])
    check("um segmento so continua um bullet", pb("pytest -q -> 62 ok") == ["pytest -q -> 62 ok"])
    check("prova vazia nao gera bullet", pb("") == [] and pb(None) == [])

    d = tempfile.mkdtemp()
    try:
        plano = {"id": "p-f6", "title": "t", "phases": [
            {"id": "F1", "title": "f", "items": [
                {"id": "F1.1", "title": "i", "desc": "d"},
                {"id": "F1.2", "title": "j", "desc": "o segundo passo"}]}]}
        with open(os.path.join(d, "p-f6.plan.json"), "w", encoding="utf-8") as fh:
            json.dump(plano, fh)

        raises("tick recusa prova longa num bloco so",
               lambda: ps.cmd_tick(_ns(dir=d, plan="p-f6", node="F1.1", evidencia="c" * 150)),
               "num bloco")
        ps.cmd_tick(_ns(dir=d, plan="p-f6", node="F1.1",
                        evidencia="$ pytest -q\n" + "x" * 150))
        check("saida crua multilinha passa inteira",
              ps.pick_plan(d, "p-f6")["phases"][0]["items"][0]["status"] == "done")

        ps.cmd_tick(_ns(dir=d, plan="p-f6", node="F1.2", evidencia="a rodou · b passou · c1d2e3f"))
        it = ps.pick_plan(d, "p-f6")["phases"][0]["items"][1]
        texto, classe = ps._detalhe(it)
        check("prova feita vira bloco multilinha",
              classe == "pt-evidence" and texto.startswith("prova:\n"))
        check("cada segmento vira um bullet", texto.count("\n· ") == 3)
        html = ps._detalhe_html(texto, classe)
        check("html da prova sai como lista",
              'ul class="pt-prova"' in html and html.count("<li>") == 3)
        check("prova de um segmento continua span",
              ps._detalhe_html("prova: x", "pt-evidence").startswith("<span"))
    finally:
        shutil.rmtree(d, ignore_errors=True)

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
