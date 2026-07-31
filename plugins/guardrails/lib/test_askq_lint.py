#!/usr/bin/env python3
"""Suite do askq_lint — cada régua nos DOIS lados.

A disciplina vem do test_pre_deploy.sh: travar só o lado que o conserto GANHOU
deixa o lado que ele pode PERDER descoberto. Então toda regra tem um caso que
barra e um caso que passa, e os falso-positivos conhecidos (data, sigla, prosa
normal em português) têm caso próprio.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import askq_lint  # noqa: E402

PASS = FAIL = 0


def check(nome, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        sys.stderr.write("  ✗ %s\n" % nome)


def viol(questions):
    """Roda o lint sobre uma lista de perguntas e devolve as violações."""
    return askq_lint.lint({"tool_input": {"questions": questions}})


def has(vs, agulha):
    return any(agulha in v for v in vs)


# Opção sadia reutilizável: consequência com folga acima do mínimo.
OK_OPT = [
    {"label": "Manter como está",
     "description": "Nada muda hoje e o problema volta na próxima rodada."},
    {"label": "Trocar agora",
     "description": "Custa uma hora e fecha o furo de uma vez, sem voltar."},
]
# Pergunta sadia: acima de MIN_Q, sem nome de código.
OK_Q = ("O relatório da semana deve sair com os números da semana passada ou "
        "esperar o fechamento de amanhã?")


# ── Régua 1 · nome de código na superfície ───────────────────────────────────
print("── régua 1 · nome de código ──")
for nome, texto in (
        ("underscore", "Qual o teto do plan_state pra essa rodada de trabalho aqui?"),
        ("camelCase",  "Devo mexer no postState agora ou depois do fechamento de hoje?"),
        ("CamelCase",  "O ExitPlanMode entra nesta rodada ou fica pra semana que vem?"),
        ("maiúsc.meio","Vou mexer no askqLint hoje ou deixo pro fechamento da semana?"),
        ("função",     "Chamo o collectAll() antes ou depois de fechar a semana toda?"),
        ("arquivo",    "O corte vai no visual_page.py ou fica só na instrução da skill?"),
        ("caminho",    "Guardo em ~/.claude/guardrails ou no diretório do projeto mesmo?"),
        ("backtick",   "Mexo no `validate` desta rodada ou deixo pra próxima semana?")):
    vs = viol([{"question": texto, "header": "Escopo", "options": OK_OPT}])
    check("barra %s: %r" % (nome, texto[:34]), has(vs, "nome de código"))

vs = viol([{"question": OK_Q, "header": "Números", "options": OK_OPT}])
check("passa pergunta humana, zero violação", vs == [])

# Os falso-positivos que matariam o gate no primeiro dia.
for nome, texto in (
        ("data",         "Uso os números de 30/07/2026 ou espero o fechamento de amanhã?"),
        ("fração",       "A meta é 1/3 do canal ou vale medir o mês inteiro de uma vez?"),
        ("alternativa",  "Publico hoje e/ou espero o retorno do cliente antes de mexer?"),
        ("acento",       "Você prefere a versão longa da peça ou a curta pro cliente ver?"),
        # R1 (2026-07-30): a PRIMEIRA pergunta real que o gate julgou foi BARRADA por
        # "GitHub" casar como CamelCase. Nome próprio com maiúscula interna é grafia
        # normal, não identificador — e um gate que erra na estreia é um gate desligado.
        ("GitHub",       "O commit disso já está no GitHub ou ainda falta empurrar hoje?"),
        ("JavaScript",   "A peça sai em JavaScript ou espero o fechamento de amanhã?"),
        ("macOS",        "Isso vale só no macOS ou tem que rodar no Linux também hoje?"),
        ("PostgreSQL",   "Guardo no PostgreSQL ou num arquivo solto até a semana virar?"),
        ("iPhone",       "A tela precisa caber no iPhone ou só no monitor grande mesmo?")):
    vs = viol([{"question": texto, "header": "Escopo", "options": OK_OPT}])
    check("NÃO barra %s: %r" % (nome, texto[:34]), not has(vs, "nome de código"))

vs = viol([{"question": OK_Q, "header": "plan_state", "options": OK_OPT}])
check("barra nome de código no header", has(vs, "o header traz nome de código"))

vs = viol([{"question": OK_Q, "header": "Escopo",
            "options": [dict(OK_OPT[0], label="visual_page.py"), OK_OPT[1]]}])
check("NÃO barra nome de código no LABEL (a description cobre)",
      not has(vs, "nome de código"))


# ── Régua 2 · opção sem consequência ────────────────────────────────────────
print("── régua 2 · consequência da opção ──")
vs = viol([{"question": OK_Q, "header": "Escopo",
            "options": [{"label": "Opção A", "description": ""},
                        {"label": "Opção B", "description": "Rápido"}]}])
check("barra description vazia", has(vs, "'Opção A'"))
check("barra description curta", has(vs, "'Opção B'"))
check("diz o que ACONTECE", has(vs, "não diz o que ACONTECE"))
check("mostra a contagem de chars", has(vs, "mínimo %d" % askq_lint.MIN_DESC))

vs = viol([{"question": OK_Q, "header": "Escopo", "options": OK_OPT}])
check("passa description com consequência real", vs == [])

limite = "x" * askq_lint.MIN_DESC
vs = viol([{"question": OK_Q, "header": "Escopo",
            "options": [dict(OK_OPT[0], description=limite), OK_OPT[1]]}])
check("MIN_DESC exato passa (fronteira, não off-by-one)", vs == [])


# ── Régua 3 · pergunta seca e nada pra olhar ────────────────────────────────
print("── régua 3 · premissa ou artefato ──")
CURTA = "Qual das duas?"
vs = viol([{"question": CURTA, "header": "Escopo", "options": OK_OPT}])
check("barra pergunta seca sem preview", has(vs, "sem premissa e sem nada pra olhar"))

vs = viol([{"question": CURTA, "header": "Escopo",
            "options": [dict(OK_OPT[0], preview="linha 1\nlinha 2"), OK_OPT[1]]}])
check("passa pergunta seca QUANDO há preview", vs == [])

vs = viol([{"question": CURTA, "header": "Escopo",
            "options": [dict(OK_OPT[0], preview="   "), OK_OPT[1]]}])
check("preview só com espaço não conta como artefato",
      has(vs, "sem premissa e sem nada pra olhar"))

vs = viol([{"question": OK_Q, "header": "Escopo", "options": OK_OPT}])
check("passa pergunta longa sem preview", vs == [])


# ── Fail-open · forma inesperada NUNCA acusa ────────────────────────────────
print("── fail-open ──")
check("payload não-dict", askq_lint.lint([]) == [])
check("sem tool_input", askq_lint.lint({}) == [])
check("tool_input não-dict", askq_lint.lint({"tool_input": "x"}) == [])
check("sem questions", askq_lint.lint({"tool_input": {}}) == [])
check("questions não-lista", viol("x") == [])
check("pergunta não-dict", viol(["x"]) == [])
check("options ausente", viol([{"question": CURTA}]) == [])
check("options não-lista", viol([{"question": CURTA, "options": "x"}]) == [])
check("options vazia", viol([{"question": CURTA, "options": []}]) == [])
check("opção não-dict é pulada, não acusa",
      viol([{"question": OK_Q, "options": ["x"]}]) == [])


# ── Anti-tautologia · o lint afirma ALGO ────────────────────────────────────
# Sabota a régua 2 e exige que a suite sinta. Sem isto, um lint que devolvesse
# sempre [] passaria em todos os casos "passa" acima.
print("── anti-tautologia ──")
_orig = askq_lint.MIN_DESC
askq_lint.MIN_DESC = 0
sabotado = viol([{"question": OK_Q, "header": "Escopo",
                  "options": [{"label": "Opção A", "description": ""},
                              {"label": "Opção B", "description": ""}]}])
askq_lint.MIN_DESC = _orig
check("com MIN_DESC=0 a régua 2 fica MUDA (prova que ela é ela que acusa)",
      not has(sabotado, "não diz o que ACONTECE"))

_np = askq_lint.NOMES_PROPRIOS
askq_lint.NOMES_PROPRIOS = frozenset()
sem_lista = viol([{"question": "O commit disso já está no GitHub ou ainda falta empurrar hoje?",
                   "header": "Escopo", "options": OK_OPT}])
askq_lint.NOMES_PROPRIOS = _np
check("esvaziar NOMES_PROPRIOS faz 'GitHub' barrar (prova que é a lista que libera)",
      has(sem_lista, "nome de código"))


# ── CLI · exit code é veredito ──────────────────────────────────────────────
print("── CLI ──")
import io  # noqa: E402
import contextlib  # noqa: E402

def run_cli(payload):
    buf = io.StringIO()
    stdin_bak = sys.stdin
    sys.stdin = io.StringIO(json.dumps(payload))
    try:
        with contextlib.redirect_stdout(buf):
            rc = askq_lint.main([])
    finally:
        sys.stdin = stdin_bak
    return rc, buf.getvalue()

rc, out = run_cli({"tool_input": {"questions": [
    {"question": CURTA, "options": [{"label": "A", "description": ""}]}]}})
check("exit 1 quando há violação", rc == 1)
check("imprime a violação no stdout", "não diz o que ACONTECE" in out)

rc, out = run_cli({"tool_input": {"questions": [
    {"question": OK_Q, "header": "Escopo", "options": OK_OPT}]}})
check("exit 0 quando está limpo", rc == 0)
check("silêncio quando está limpo", out.strip() == "")

sys.stdin_bak = None
rc, out = run_cli("nada disso")
check("JSON válido mas forma estranha: exit 0", rc == 0)


print("── %d passou · %d falhou ──" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
