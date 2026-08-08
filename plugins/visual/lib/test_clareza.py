#!/usr/bin/env python3
"""Suíte do banco de lições de clareza. `python3 test_clareza.py` → 0 = tudo verde."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clareza  # noqa: E402

OK = []


def check(nome, cond):
    OK.append((nome, bool(cond)))
    print("%s %s" % ("✅" if cond else "❌", nome))


BANCO_TESTE = {
    "versao": 1,
    "licoes": [{
        "id": "termo-vago-meu",
        "nome": "nome inventado",
        "erro": "…",
        "regra": "Nome que eu inventei se troca pelo que a coisa FAZ.",
        "banido": ["impressão digital", "sistema pai"]
    }]
}


def t_pega_termo_banido():
    spec = {"title": "A impressão digital do texto", "sections": []}
    errs = clareza.erros_de_clareza(spec, BANCO_TESTE)
    check("termo banido no título é acusado", len(errs) == 1)
    check("o erro traz a regra que o baniu", "se troca pelo que a coisa FAZ" in errs[0])


def t_acha_no_fundo_do_spec():
    spec = {"sections": [{"blocks": [{"kind": "decision", "options": [
        {"title": "ok", "body": "herdado do sistema pai"}]}]}]}
    errs = clareza.erros_de_clareza(spec, BANCO_TESTE)
    check("acha termo dentro de opção de decisão", len(errs) == 1)


def t_isenta_prova_crua():
    # A saída crua de um comando é literal por obrigação — se ela citar o termo,
    # não é o autor escrevendo mal, é a máquina falando. Isentar é o ponto.
    spec = {"sections": [{"blocks": [
        {"kind": "evidencia", "src": "cmd", "output": "sistema pai encontrado em foo.py"}]}]}
    check("evidencia.output é isenta", clareza.erros_de_clareza(spec, BANCO_TESTE) == [])
    spec2 = {"sections": [{"blocks": [{"kind": "raw_html", "html": "<b>sistema pai</b>"}]}]}
    check("raw_html é isento", clareza.erros_de_clareza(spec2, BANCO_TESTE) == [])


def t_nao_pega_pedaco_de_palavra():
    # "impressão digital" não pode disparar em "impressões digitalizadas"
    spec = {"title": "sistema paisagem", "sections": []}
    check("não dispara no meio de outra palavra",
          clareza.erros_de_clareza(spec, BANCO_TESTE) == [])


def t_spec_limpo_passa():
    spec = {"title": "A marca do texto aprovado", "sections": [
        {"blocks": [{"kind": "text", "text": "copia o que já foi escrito"}]}]}
    check("spec sem termo banido passa", clareza.erros_de_clareza(spec, BANCO_TESTE) == [])


def t_registrar_funde_sem_duplicar():
    tmp = tempfile.mkdtemp()
    antigo_dir, antigo_banco = clareza.STATE_DIR, clareza.BANCO
    clareza.STATE_DIR = tmp
    clareza.BANCO = os.path.join(tmp, "licoes.json")
    try:
        clareza.grava({"versao": 1, "licoes": [
            {"id": "a", "nome": "A", "erro": "e", "regra": "r", "banido": ["um"]}]})
        novo = os.path.join(tmp, "novas.json")
        with open(novo, "w", encoding="utf-8") as f:
            json.dump({"licoes": [
                {"id": "a", "nome": "A2", "erro": "e", "regra": "r2", "banido": ["dois"]},
                {"id": "b", "nome": "B", "erro": "e", "regra": "r"}]}, f)

        class A:
            json = novo
        clareza.cmd_registrar(A())
        banco = clareza.carrega()
        ids = [x["id"] for x in banco["licoes"]]
        check("id repetido atualiza em vez de duplicar", ids.count("a") == 1)
        check("id novo entra", "b" in ids)
        a = [x for x in banco["licoes"] if x["id"] == "a"][0]
        check("termo banido só ENTRA, nunca sai", a["banido"] == ["dois", "um"])
        check("a regra é atualizada pela versão nova", a["regra"] == "r2")
    finally:
        clareza.STATE_DIR, clareza.BANCO = antigo_dir, antigo_banco


def t_banco_corrompido_nao_derruba():
    tmp = tempfile.mkdtemp()
    antigo = clareza.BANCO
    clareza.BANCO = os.path.join(tmp, "quebrado.json")
    try:
        with open(clareza.BANCO, "w", encoding="utf-8") as f:
            f.write("{isto não é json")
        # Fail-open é deliberado: banco quebrado NÃO pode impedir a página de existir.
        check("banco corrompido cai na semente", len(clareza.carrega()["licoes"]) > 0)
    finally:
        clareza.BANCO = antigo


def t_semente_tem_as_licoes_de_fabrica():
    ids = {x["id"] for x in clareza.SEMENTE["licoes"]}
    check("a semente traz as 5 lições das duas reprovações",
          {"referente-pendurado", "referencia-recursiva", "termo-vago-meu",
           "jargao-sem-glosa", "escolha-sem-diferenca"} <= ids)


def t_o_build_do_visual_usa_o_banco():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import visual_page
    spec = {"title": "t", "ident": {"projeto": "p", "artefato": "a"},
            "sections": [{"blocks": [{"kind": "text", "text": "o sistema pai decide"}]}]}
    errs = visual_page.validate(spec)
    check("visual_page.validate consulta o banco",
          any("sistema pai" in e for e in errs))


"""As 5 conferências do `revisar` — o cobrador que nasceu em 2026-08-08.

Cada teste tem os DOIS lados: o spec que o defeito reprova e o spec limpo que
passa. Cobrador que só tem o lado vermelho vira cobrador que reprova tudo, e
falso-positivo ensina a contornar.
"""


def _spec(blocos, **extra):
    s = {"title": "t", "ident": {"projeto": "p", "artefato": "a"},
         "sections": [{"title": "s", "blocks": blocos}]}
    s.update(extra)
    return s


def _ids(spec):
    return [c for c, _m in clareza.revisao_do_spec(spec)]


def t_palavra_da_casa_sem_abrir():
    sujo = _spec([{"kind": "decision", "question": "qual plugin?",
                   "context": "c", "options": []}])
    check("palavra da casa usada sem ser aberta é acusada",
          "palavra-sem-abrir" in _ids(sujo))
    limpo = _spec([{"kind": "bullets", "items": ["Plugin é a caixa que se instala."]},
                   {"kind": "decision", "question": "qual plugin?",
                    "context": "c", "options": []}])
    check("definida antes da pergunta, passa", "palavra-sem-abrir" not in _ids(limpo))


def t_dois_nomes_para_a_mesma_coisa():
    sujo = _spec([{"kind": "bullets", "items": ["Plugin é a caixa que se instala.",
                                                "Pacote é a caixa que se instala."]},
                  {"kind": "decision", "question": "q", "context": "c", "options": []},
                  {"kind": "text", "text": "o plugin novo entra no pacote velho"}])
    check("duas palavras da mesma família depois da abertura é acusado",
          "dois-nomes" in _ids(sujo))


def t_a_abertura_pode_apresentar_as_duas():
    # É exatamente ali que se diz "plugin é o pacote" — acusar o glossário mataria
    # a única forma certa de apresentar a palavra.
    limpo = _spec([{"kind": "bullets",
                    "items": ["Plugin, ou pacote, é a caixa que se instala."]},
                   {"kind": "decision", "question": "q sobre plugin",
                    "context": "c", "options": []}])
    check("apresentar as duas NA ABERTURA não é acusado",
          "dois-nomes" not in _ids(limpo))


def t_apoio_em_escolha_fora_da_pagina():
    sujo = _spec([{"kind": "text", "text": "Como você já escolheu, seguimos assim."}])
    check("apoio em escolha que não está na página é acusado",
          "apoio-fora" in _ids(sujo))
    limpo = _spec([{"kind": "text", "text": "Você escolheu o nome plano, escrito aqui."}])
    check("escolha com o valor escrito na página passa",
          "apoio-fora" not in _ids(limpo))


def t_custo_sem_unidade():
    sujo = _spec([{"kind": "text", "text": "a leitura é cara e nem sempre vale"}])
    check("página que fala de custo sem dizer custa o quê é acusada",
          "custo-sem-unidade" in _ids(sujo))
    limpo = _spec([{"kind": "text", "text": "a leitura é cara: gasta dinheiro de verdade"}])
    check("com a unidade em qualquer lugar da página, passa",
          "custo-sem-unidade" not in _ids(limpo))


def t_custo_medido_por_pagina_e_nao_por_frase():
    # A régua é por PÁGINA: depois de dizer uma vez que o custo é dinheiro,
    # repetir "a leitura cara" é economia de palavra, não omissão.
    limpo = _spec([{"kind": "bullets", "items": ["Cada palavra lida custa dinheiro."]},
                   {"kind": "text", "text": "a leitura cara não compensa"},
                   {"kind": "text", "text": "o gasto foi alto"}])
    check("uma unidade na página basta para as menções seguintes",
          "custo-sem-unidade" not in _ids(limpo))


def t_prova_sem_estrago():
    sujo = _spec([{"kind": "evidencia", "src": "cmd", "output": "24 coisas"}])
    check("prova colada sem nada depois dela é acusada",
          "prova-sem-estrago" in _ids(sujo))
    limpo = _spec([{"kind": "evidencia", "src": "cmd", "output": "24 coisas"},
                   {"kind": "bullets", "items": ["Isso faz o disco encher todo mês."]}])
    check("prova seguida do estrago passa", "prova-sem-estrago" not in _ids(limpo))


def t_revisar_nao_julga_clareza():
    # O `revisar` procura o que é mecânico; clareza continua sendo do juiz externo.
    limpo = _spec([{"kind": "text", "text": "uma frase completamente obscura e ruim"}])
    check("texto obscuro sem defeito mecânico não é acusado", _ids(limpo) == [])


for t in (t_pega_termo_banido, t_acha_no_fundo_do_spec, t_isenta_prova_crua,
          t_nao_pega_pedaco_de_palavra, t_spec_limpo_passa,
          t_registrar_funde_sem_duplicar, t_banco_corrompido_nao_derruba,
          t_semente_tem_as_licoes_de_fabrica, t_o_build_do_visual_usa_o_banco,
          t_palavra_da_casa_sem_abrir, t_dois_nomes_para_a_mesma_coisa,
          t_a_abertura_pode_apresentar_as_duas, t_apoio_em_escolha_fora_da_pagina,
          t_custo_sem_unidade, t_custo_medido_por_pagina_e_nao_por_frase,
          t_prova_sem_estrago, t_revisar_nao_julga_clareza):
    t()

falhas = [n for n, ok in OK if not ok]
print("\n%d ok · %d falha(s)" % (len(OK) - len(falhas), len(falhas)))
sys.exit(1 if falhas else 0)
