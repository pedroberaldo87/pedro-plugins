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
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_state as ps  # noqa: E402

FAILS = []


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


def init_into(d, plan, renames=None):
    path = os.path.join(d, "_in.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(plan, fh)
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
                   {"id": "F1.1", "title": "t", "desc": "a" * 200}]}])), "UMA linha")
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
              len(errs) == 1 and "UMA linha" in errs[0])
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

        print("init cobra só do item novo")
        d2 = tempfile.mkdtemp(prefix="plan-novo-")
        try:
            init_into(d2, magro)
            check("plano antigo entra sem os campos", load(d2) is not None)
            com_novo = sample(phases=[{"id": "F1", "title": "x", "items": [
                {"id": "F1.1", "title": "t", "desc": "d"},
                {"id": "F1.2", "title": "novo", "desc": "d"}]}])
            check("item NOVO sem pronto/requisito derruba o init",
                  _levanta(lambda: init_into(d2, com_novo)))
        finally:
            shutil.rmtree(d2, ignore_errors=True)

        print("init preserva os campos")
        d5 = tempfile.mkdtemp(prefix="plan-preserva-")
        try:
            init_into(d5, bom)
            init_into(d5, sample(phases=[{"id": "F1", "title": "x", "items": [
                {"id": "F1.1", "title": "t", "desc": "d"}]}]))
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
            check("o requisito NÃO virou estado no arquivo",
                  "requisitos" not in load(planos, "2026-07-27-teste"))
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

        print("brief — 'onde nós estamos' em 1-3 bullets")
        b = sample(id="2026-07-27-brief")
        init_into(d, b)
        pl = ps.pick_plan(d, "2026-07-27-brief")
        L = ps.brief_lines(pl)
        check("no começo: cabeçalho + 3 bullets", len(L) == 4 and L[0].startswith("📍"))
        check("diz quanto já foi", "0 de 3 passos" in L[1])
        check("diz onde estamos agora", L[2].startswith("• **Agora:** F1"))
        check("diz o que falta", L[3].startswith("• **Falta:** 3 passos"))
        check("nunca passa de 3 bullets", len([x for x in L if x.startswith("•")]) <= 3)

        ps.cmd_tick(Args(dir=d, plan="2026-07-27-brief", node="F1.1", evidencia="python3 t.py -> OK"))
        ps.cmd_tick(Args(dir=d, plan="2026-07-27-brief", node="F1.2", evidencia="commit a1b2c3d"))
        L = ps.brief_lines(ps.pick_plan(d, "2026-07-27-brief"))
        check("fase fechada aparece pelo id", "(F1)" in L[1] and "1 fase" in L[1])
        check("não repete em Falta a fase que já está em Agora",
              "· fase" not in L[3] and "· fases" not in L[3])
        tri = sample(id="2026-07-27-brief-tri")
        tri["phases"].append({"id": "F3", "title": "Terceira", "items": [
            {"id": "F3.1", "title": "t", "desc": "faz a terceira coisa"}]})
        init_into(d, tri)
        # fecha a F1 pra sobrar exatamente UMA fase além da atual (F2 é a atual, F3 a que falta)
        ps.cmd_tick(Args(dir=d, plan="2026-07-27-brief-tri", node="F1.1", evidencia="prova F1.1 ok"))
        ps.cmd_tick(Args(dir=d, plan="2026-07-27-brief-tri", node="F1.2", evidencia="prova F1.2 ok"))
        L3 = ps.brief_lines(ps.pick_plan(d, "2026-07-27-brief-tri"))
        check("com 1 fase além da atual, diz 'fase' no singular",
              "· fase F3" in L3[3] and "· fases" not in L3[3])

        ps.cmd_tick(Args(dir=d, plan="2026-07-27-brief", node="F2.1", evidencia="prova final"))
        L = ps.brief_lines(ps.pick_plan(d, "2026-07-27-brief"))
        check("tudo marcado -> mensagem INEQUÍVOCA de concluído", L[0].startswith("✅ **CONCLUÍDO"))
        check("o concluído diz o que prova", "com prova anexada" in L[1])
        check("o concluído manda encerrar", "close" in L[2])
        check("concluído também cabe em 3 bullets", len(L) == 3)

        ps.cmd_close(Args(dir=d, plan="2026-07-27-brief"))
        L = ps.brief_lines(ps.pick_plan(d, "2026-07-27-brief"))
        check("encerrado completo -> 🏁 inequívoco", L[0].startswith("🏁 **PLANO ENCERRADO —"))
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
              "Feito:" in comn[1] and "Agora:" in comn[2])

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
        check("o brief traz a cobertura", any("sem requisito" in x for x in b))
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

        print("arquivo corrompido não derruba a listagem")
        before = len(ps.list_plans(d))
        with open(os.path.join(d, "quebrado.plan.json"), "w") as fh:
            fh.write("{ isto não é json")
        check("list_plans pula o corrompido", len(ps.list_plans(d)) == before)
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
