#!/usr/bin/env python3
"""Suíte da PORTA da régua (`pretooluse-artefato-regua.py`).

O que ela protege, em ordem de importância: o gate morde a prosa corrida num
artefato de leitura, e NÃO morde em mais nada. Um gate de forma que reprova saída
crua, código ou documentação vira ruído, e ruído se desliga — aí não sobra gate.
"""
import importlib.util
import io
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "porta", os.path.join(AQUI, "pretooluse-artefato-regua.py"))
porta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(porta)

FAILS = []


def ok(label, cond):
    print("  %s   %s" % ("ok  " if cond else "FAIL", label))
    if not cond:
        FAILS.append(label)


def roda(payload):
    """Chama o main() com o payload no stdin e devolve (rc, stderr)."""
    orig_in, orig_err = sys.stdin, sys.stderr
    sys.stdin = io.StringIO(payload if isinstance(payload, str) else json.dumps(payload))
    sys.stderr = io.StringIO()
    try:
        rc = porta.main()
        return rc, sys.stderr.getvalue()
    finally:
        sys.stdin, sys.stderr = orig_in, orig_err


def art(content, path="/p/.claude/visual/r.md", key="content"):
    return {"tool_input": {"file_path": path, key: content}}


# Precisa passar de 140 caracteres DEPOIS de tirar o "- ". A primeira versão
# desta constante media 133 e fazia três checks falharem por medir nada.
LONGO = ("- Este bullet é deliberadamente longo para estourar com folga o teto de "
         "cento e quarenta caracteres que a constituição do projeto estabelece "
         "para cada bullet de texto que um humano lê.")

print("o gate morde a prosa corrida")
rc, err = roda(art(LONGO))
ok("bullet acima do teto é recusado", rc == 2)
ok("a mensagem diz o que fazer", "quebre em bullets" in err.lower())
ok("a mensagem oferece a saída de emergência", "ARTEFATO_REGUA=0" in err)

rc, _ = roda(art("- Isto é uma frase. E esta é a segunda no mesmo bullet."))
ok("duas frases no mesmo bullet são recusadas", rc == 2)

rc, _ = roda(art("- porque o teste passou, o gate ficou verde."))
ok("bullet que abre com conectivo é recusado", rc == 2)

print("o gate NÃO morde o que não é redação")
ok("bullets curtos passam", roda(art("- A suíte passou.\n- O gate ficou verde."))[0] == 0)
ok("saída crua dentro de cerca passa",
   roda(art("- O teste rodou.\n\n```\n" + "x" * 300 + "\n```"))[0] == 0)
ok("linha de comando passa", roda(art("$ " + "y" * 300))[0] == 0)
ok("título passa", roda(art("# " + "z" * 300))[0] == 0)
ok("tabela passa", roda(art("| " + "w" * 300))[0] == 0)

print("o gate respeita o alcance")
ok("arquivo fora de .claude/visual passa",
   roda(art(LONGO, path="/p/src/README.md"))[0] == 0)
ok("extensão fora do alcance passa",
   roda(art(LONGO, path="/p/.claude/visual/x.py"))[0] == 0)
ok(".claude/reports também é alcançado",
   roda(art(LONGO, path="/p/.claude/reports/r.md"))[0] == 2)
ok("html do gerador passa (já mediu na origem)",
   roda(art(LONGO + "\n<!-- visual_page.py -->", path="/p/.claude/visual/r.html"))[0] == 0)

print("o gate falha aberto, nunca fechado")
ok("json quebrado passa", roda("isto não é json")[0] == 0)
ok("payload sem tool_input passa", roda({})[0] == 0)
ok("conteúdo vazio passa", roda(art("   "))[0] == 0)
ok("sem file_path passa", roda({"tool_input": {"content": LONGO}})[0] == 0)

os.environ["ARTEFATO_REGUA"] = "0"
ok("kill-switch desliga o gate", roda(art(LONGO))[0] == 0)
del os.environ["ARTEFATO_REGUA"]

print("o Edit é medido pelo pedaço novo")
ok("new_string acima do teto é recusado", roda(art(LONGO, key="new_string"))[0] == 2)

print("as duas camadas existem, e são arquivos distintos")
rede = os.path.join(os.path.dirname(os.path.dirname(AQUI)),
                    "bootstrap", "hooks", "stop-regua-relato.py")
ok("a REDE (fim de turno) está no disco", os.path.exists(rede))
ok("a PORTA (escrita de arquivo) está no disco",
   os.path.exists(os.path.join(AQUI, "pretooluse-artefato-regua.py")))

print()
if FAILS:
    print("FALHOU: %d" % len(FAILS))
    for f in FAILS:
        print("  - %s" % f)
    sys.exit(1)
print("artefato-regua: %d checks ok, 0 falhas" % (23 - len(FAILS)))
