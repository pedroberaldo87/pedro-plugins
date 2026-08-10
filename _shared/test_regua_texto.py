#!/usr/bin/env python3
"""Suite da régua de texto — stdlib, sem framework (padrão do repo).

O que estes testes protegem: a régua vale para TODO gerador, e cada tipo de
artefato tem o que, nele, não é redação. Um perfil que não recusa nada é um
perfil frouxo — cada um abaixo tem pelo menos uma recusa que só ele faz.

    python3 _shared/test_regua_texto.py
"""

import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import regua_texto as R  # noqa: E402

PASS = FAIL = 0


def check(label, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  ok   %s" % label)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (label, extra))


# ── os cinco perfis existem e nenhum é frouxo ──────────────────────────────

print("\n[perfis — declarados, e nenhum deles é a saída de emergência]")

check("os cinco perfis estão declarados",
      sorted(R.PERFIS) == ["contexto", "hook", "pagina", "plano", "slide"], sorted(R.PERFIS))

# O perfil `contexto` cobre o canal additionalContext, cujo leitor é o MODELO.
# Markdown e ausência de emoji são legítimos ali; prosa fatiada não é.
check("contexto aceita markdown (o modelo o interpreta)",
      not R.erros_de_estilo(["Leia o **CLAUDE.md** antes de explorar"], "x", "contexto"))
check("contexto não exige emoji no cabeçalho",
      not R.erros_de_estilo(["Documentacao project-doc disponivel"], "x", "contexto"))
check("contexto recusa duas frases no mesmo bullet",
      bool(R.erros_de_estilo(["Uma frase. E a segunda no mesmo bullet."], "x", "contexto")))
check("contexto tem teto maior que o de página (carrega inventário)",
      R.perfil("contexto").bullet_max > R.perfil("pagina").bullet_max)
check("contexto cabe mais bullets que o canal de tela",
      R.perfil("contexto").bullets_max > R.perfil("hook").bullets_max)

# O textão real do relatório de 2026-08-01 (quality-goals.md, "Trade-off já decidido").
PROSA_REAL = ("Das cinco decisões que vazaram na sessão de ontem, quatro nasceram no meio "
              "da implementação — e nenhum campo do plano as teria capturado, porque elas "
              "não existiam quando o plano foi escrito. O que foi construído hoje resolve "
              "a decisão que o autor do plano JÁ SABIA que existia.")

for nome in sorted(R.PERFIS):
    e = R.erros_de_estilo(PROSA_REAL, "x", nome)
    check("perfil %s REPROVA o textão real" % nome, len(e) >= 2, e)
    check("perfil %s reprova por tamanho" % nome, any("caracteres" in x for x in e), e)
    check("perfil %s reprova por duas frases" % nome, any("duas frases" in x for x in e), e)
    check("perfil %s reprova bullet que abre com conectivo" % nome,
          any("conectivo" in x for x in R.erros_de_estilo(["ok", "e por isso caiu"], "x", nome)))

try:
    R.erros_de_estilo("ok", "x", "solto")
    check("perfil desconhecido levanta em vez de virar o frouxo", False)
except ValueError as ex:
    check("perfil desconhecido levanta em vez de virar o frouxo", "solto" in str(ex), ex)


# ── perfil pagina: o de hoje, byte a byte ──────────────────────────────────

print("\n[pagina — o comportamento que o gerador de página já tinha]")

check("140 passa", R.erros_de_estilo("a" * 140, "x") == [])
check("141 reprova", len(R.erros_de_estilo("a" * 141, "x")) == 1)
check("marcação não conta no teto", R.erros_de_estilo("`%s`" % ("a" * 140), "x") == [])
check("reticências não viram duas frases",
      R.erros_de_estilo("o gate desligou... e ninguém viu", "x") == [])
check("decimal não vira duas frases", R.erros_de_estilo("são 1.500 itens", "x") == [])
check("6 bullets passam", R.erros_de_estilo(["b%d" % i for i in range(6)], "x") == [])
check("7 bullets reprovam", any("teto é 6" in e
      for e in R.erros_de_estilo(["b%d" % i for i in range(7)], "x")))
check("o erro diz QUAL bullet",
      any("bullet 2" in e for e in R.erros_de_estilo(["ok", "a" * 200], "x")))
check("pagina é o default", R.erros_de_estilo("a" * 141, "x")
      == R.erros_de_estilo("a" * 141, "x", "pagina"))


# ── perfil plano: a árvore do programa fica fora, a redação não ────────────

print("\n[plano — linha de árvore é desenho do programa, não redação]")

# As linhas reais que `plan_state.render_text` compõe (glifos MARK e DOT).
ARVORE = ["✅ F1 · %s   (2/2)" % ("Fase com título muito longo " * 6),
          "     ○ T3  %s" % ("Tarefa de título comprido " * 6),
          "▸ %s   3 req · 9 tarefas  4/9" % ("Épico de nome comprido " * 6)]

for ln in ARVORE:
    check("árvore passa no perfil plano: %r" % ln[:22],
          R.erros_de_estilo(ln, "árvore", "plano") == [],
          R.erros_de_estilo(ln, "árvore", "plano"))
    check("a MESMA linha reprova no perfil pagina: %r" % ln[:22],
          R.erros_de_estilo(ln, "árvore", "pagina") != [])

check("desc de plano continua na régua (não é linha de árvore)",
      any("caracteres" in e for e in R.erros_de_estilo("a" * 200, "T1 desc", "plano")))
check("prosa que só PARECE árvore por dentro não escapa",
      R.erros_de_estilo("a tarefa ✅ ficou pronta. o resto não.", "T1 desc", "plano") != [])


# ── perfil slide: o teto que decide é o de palavras ────────────────────────

print("\n[slide — lido de longe; 140 caracteres cabem na página e não no slide]")

LONGA = ("o gate roda no commit e barra o bump que não veio, e o resto do time "
         "nem fica sabendo que já era")
check("a linha tem 23 palavras e cabe no teto de caracteres da página",
      len(LONGA.split()) == 23 and len(LONGA) < 140, (len(LONGA.split()), len(LONGA)))
check("a linha de 23 palavras PASSA na página", R.erros_de_estilo(LONGA, "x") == [],
      R.erros_de_estilo(LONGA, "x"))
check("e REPROVA no slide", any("palavras" in e
      for e in R.erros_de_estilo(LONGA, "x", "slide")),
      R.erros_de_estilo(LONGA, "x", "slide"))
check("20 palavras passam no slide",
      R.erros_de_estilo(" ".join("p%d" % i for i in range(20)), "x", "slide") == [])
check("o teto de bullets do slide é o mesmo 6 do md2deck",
      R.PERFIS["slide"].bullets_max == 6)


# ── perfil hook: canal de texto puro, destaque por emoji ───────────────────

print("\n[hook — o canal não renderiza markdown; cabeçalho se destaca por emoji]")

# O que os TRÊS emissores cuspiam antes do conserto de 2026-08-03 (commit c97813c).
EMISSORES = [
    ("resumo do plano", "📋 **Plano aberto no projeto — Video Review: fechar o ciclo**"),
    ("cobrança do tique", "• **Feito:** 0 de 2 passos — nenhuma fase fechou ainda."),
    ("aviso de push de branch", "⚠️ A branch `publicar` ainda não entrou no tronco."),
]
for quem, linha in EMISSORES:
    e = R.erros_de_estilo(linha, quem, "hook")
    check("markdown do emissor '%s' é RECUSADO" % quem, any("markdown" in x for x in e), e)
    check("a mesma linha PASSA no perfil pagina (lá markdown é legítimo)",
          not any("markdown" in x for x in R.erros_de_estilo(linha, quem, "pagina")))

# As linhas reais do fim de turno, já consertadas.
BRIEF = ["📋 Plano aberto no projeto — Video Review: fechar o ciclo",
         "• ✅ Feito: 0 de 2 passos — nenhuma fase fechou ainda.",
         "• 🔄 Agora: F1 · Fase — 0 de 2 passos.",
         "• ⬜ Falta: 2 passos."]
check("o resumo real de fim de turno passa inteiro",
      R.erros_de_estilo(BRIEF, "brief", "hook") == [],
      R.erros_de_estilo(BRIEF, "brief", "hook"))

check("cabeçalho sem emoji é RECUSADO",
      any("emoji" in e for e in R.erros_de_estilo("Plano aberto no projeto", "brief", "hook")),
      R.erros_de_estilo("Plano aberto no projeto", "brief", "hook"))
check("bullet sem emoji NÃO é cobrado (a regra é do cabeçalho)",
      R.erros_de_estilo(["📋 Cabeçalho", "• Falta: 2 passos."], "brief", "hook") == [])
check("cabeçalho sem emoji passa no perfil pagina",
      R.erros_de_estilo("Plano aberto no projeto", "x", "pagina") == [])
check("o teto de linhas do hook é o orçamento de 6 do fim de turno",
      R.PERFIS["hook"].bullets_max == R.HOOK_LINHAS == 6)
check("7 linhas estouram o orçamento do fim de turno",
      any("teto é 6" in e for e in R.erros_de_estilo(
          ["📋 h"] + ["• ✅ l%d" % i for i in range(6)], "brief", "hook")))


check("ℹ️ conta como emoji de cabeçalho (é o que o gate do ship usa)",
      R.erros_de_estilo("ℹ️  Comando fora do deploy.sh — whole-suite pulado.", "nota", "hook") == [],
      R.erros_de_estilo("ℹ️  Comando fora do deploy.sh — whole-suite pulado.", "nota", "hook"))


# ── a entrada de linha de comando: como um .sh cobra a MESMA régua ─────────

print("\n[cli — o hook é bash; sem esta entrada a régua seria redigitada em grep]")


def cli(texto, *args):
    """Roda a régua como um .sh roda. Devolve (rc, stderr)."""
    p = subprocess.run([sys.executable, os.path.join(AQUI, "regua_texto.py")] + list(args),
                       input=texto, capture_output=True, text=True, encoding="utf-8", errors="replace", start_new_session=True)
    return p.returncode, p.stderr


rc, err = cli("\n".join(BRIEF), "--perfil", "hook", "--onde", "brief", "-")
check("texto limpo: exit 0 e stderr vazio", rc == 0 and err == "", (rc, err))

rc, err = cli("📋 **Plano aberto**", "--perfil", "hook", "--onde", "brief", "-")
check("markdown: exit 1", rc == 1, (rc, err))
check("…e o motivo sai no stderr", "markdown" in err, err)

rc, err = cli("Plano aberto no projeto", "--perfil", "hook", "--onde", "brief", "-")
check("cabeçalho sem emoji: exit 1 com o motivo no stderr",
      rc == 1 and "emoji" in err, (rc, err))

rc, err = cli("📋 a\n\n• ✅ b\n", "--perfil", "hook", "-")
check("linha em branco não vira bullet vazio", rc == 0 and err == "", (rc, err))

rc, err = cli("\n".join(["📋 h"] + ["• ✅ l%d" % i for i in range(6)]), "--perfil", "hook", "-")
check("cada LINHA da stdin é um bullet (7 linhas estouram o teto)",
      rc == 1 and "teto é 6" in err, (rc, err))

rc, err = cli("a" * 200, "-")
check("sem --perfil o default é pagina", rc == 1 and "caracteres" in err, (rc, err))

rc, err = cli("ok", "--perfil", "solto", "-")
check("perfil desconhecido: rc 2, não vira o frouxo", rc == 2 and "solto" in err, (rc, err))

rc, err = cli("ok")
check("sem o `-` a chamada é recusada com o uso", rc == 2 and "uso:" in err, (rc, err))


print("\n%d passou · %d falhou" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
