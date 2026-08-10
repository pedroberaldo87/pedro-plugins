#!/usr/bin/env python3
"""A régua de estilo do regime "informação rápida" — uma por TIPO de artefato.

Fonte: `.claude/docs/quality-goals.md`, seção "A régua de estilo — quatro
checagens, cobradas por programa". As quatro nasceram dentro do
`visual_page.py` e valiam só para a página. Elas saíram de lá porque os outros
geradores (plano, slide, texto de hook) emitem texto que o mesmo humano lê com
a mesma pressa — e cada um ficava livre para inventar a própria forma.

Por que PERFIL e não régua única: as quatro checagens são as mesmas, mas o que
é texto autoral muda com o artefato. Linha de árvore de plano é desenho do
programa, não redação (quality-goals: "Fora da régua: … as linhas de árvore de
plano geradas pelo programa"). Slide é lido de longe, então o teto que decide
não é o de caracteres. Texto de hook sai num canal que NÃO renderiza markdown —
`**` e crase chegam literais na tela.

Perfil não é exceção. Não existe perfil frouxo: os quatro cobram as quatro
checagens. O que o perfil declara é o que, NAQUELE artefato, não é redação.

    perfil("pagina")   página, relatório, diagnóstico — o de hoje
    perfil("plano")    a árvore desenhada pelo programa fica fora da régua
    perfil("slide")    ≤ 20 palavras por bullet, além do resto
    perfil("hook")     sem markdown; cabeçalho começa com emoji

Uso:
    from regua_texto import erros_de_estilo
    errs = erros_de_estilo(campo, "seção 1 bloco 2: item.title", "pagina")

    printf '%s' "$MSG" | python3 regua_texto.py --perfil hook --onde "aviso" -

stdlib only (requisito do repo).
"""

import collections
import re
import sys

# CANAIS DE TEXTO EM UTF-8, SEMPRE. No Windows eles nascem na codificação do sistema
# (cp1252) e o payload do evento — que chega por stdin — é UTF-8: sem isto, todo
# acento do pedido do usuário chega corrompido ao gate, e emoji derruba a escrita.
for _canal in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_canal, "reconfigure"):
        try:
            _canal.reconfigure(encoding="utf-8")
        except Exception:
            pass

# ── os números, e de onde cada um veio ─────────────────────────────────────
BULLET_MAX = 140       # o teto que o `plan_state.DESC_MAX` já cobra (máx real medido: 137)
BULLETS_MAX = 6        # acima disso é prosa picada, ou são dois itens
SLIDE_PALAVRAS = 20    # o `md2deck.STATEMENT_WORDS`: o que cabe sozinho num slide
HOOK_LINHAS = 6        # o orçamento do fim de turno (`stop-plan-status.sh`)
# Canal `additionalContext`: lido pelo modelo, não pela tela. Mais folga em ambos os
# eixos porque ele carrega inventário — e inventário cortado esconde item.
CONTEXTO_MAX = 200
CONTEXTO_BULLETS = 20

# Ponto/!/? seguido de espaço = segunda frase. Ignora "..." e decimal ("1.500 itens").
_DUAS_FRASES = re.compile(r"(?<![.\d])[.!?](?=\s)(?!\s*$)")
# Bullet que abre continuando o anterior é parágrafo fatiado — passa no teto e segue prosa.
_CONECTIVO = re.compile(r"^(e|mas|que|porque|pois|ent[ãa]o|ou seja|al[ée]m disso|sendo que)\b", re.I)
# O que o canal de texto do hook NÃO renderiza — chega literal na tela.
_MARKDOWN = re.compile(r"\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)\s]+\)")
# Glifos que o próprio programa escreve na árvore do plano (plan_state.MARK/DOT).
_ARVORE = re.compile(r"^[✅🔄⛔⬜●◐✕○▸]")
# Linha de hook que é bullet; o resto da lista é cabeçalho.
_BULLET_HOOK = re.compile(r"^[•\-*]\s")
# Blocos Unicode de emoji — o cabeçalho de hook tem que abrir com um.
# O ponto solto é o ℹ️ (U+2139): emoji de verdade, fora dos blocos contíguos, e é o
# que o `ship/hooks/pre-deploy-test-check.sh` usa na nota informativa.
_FAIXAS_EMOJI = ((0x2139, 0x2139), (0x2600, 0x27BF), (0x2B00, 0x2BFF), (0x1F000, 0x1FAFF))


# ── perfis ─────────────────────────────────────────────────────────────────

Perfil = collections.namedtuple(
    "Perfil", "nome bullet_max bullets_max palavras_max sem_markdown "
              "cabecalho_com_emoji arvore_fora")

PERFIS = {
    # Página, relatório, diagnóstico: o que o gerador de página já cobrava.
    "pagina": Perfil("pagina", BULLET_MAX, BULLETS_MAX, None, False, False, False),
    # Plano: `desc`/`pronto`/`pendencia` são redação e entram na régua; a árvore
    # que o `plan_state.render_text` compõe (glifo + id + contagem) não é.
    "plano": Perfil("plano", BULLET_MAX, BULLETS_MAX, None, False, False, True),
    # Slide: o teto que decide é o de palavras — 140 caracteres cabem na página e
    # não cabem numa linha lida de longe.
    "slide": Perfil("slide", BULLET_MAX, BULLETS_MAX, SLIDE_PALAVRAS, False, False, False),
    # Texto de hook: canal de terminal, sem markdown; o destaque vem do emoji e da
    # posição, que foi a troca feita quando `**` começou a aparecer literal na tela.
    "hook": Perfil("hook", BULLET_MAX, HOOK_LINHAS, None, True, True, False),
    # Contexto de hook: o leitor é o MODELO, não a tela. Markdown aqui é legítimo
    # (o modelo o interpreta) e cabeçalho com emoji não faz sentido — ninguém está
    # olhando. O que continua valendo é o que a constituição pede de QUALQUER texto
    # que orienta uma decisão: uma frase por bullet, sem prosa fatiada. O teto de
    # bullets é maior porque este canal carrega inventário (lista de docs, de planos,
    # de gotchas), e cortar inventário em 6 esconde item — o oposto do que ele existe
    # pra fazer.
    "contexto": Perfil("contexto", CONTEXTO_MAX, CONTEXTO_BULLETS, None,
                       False, False, True),
}


def perfil(nome):
    """O perfil declarado, ou erro. Nome errado não vira o perfil frouxo por engano."""
    try:
        return PERFIS[nome]
    except KeyError:
        raise ValueError("perfil de texto desconhecido: %r (use %s)"
                         % (nome, "|".join(sorted(PERFIS))))


# ── as checagens ───────────────────────────────────────────────────────────

def _cru(s):
    """Texto sem a marcação do `_rich` — o teto conta o que o olho lê, não a sintaxe."""
    t = re.sub(r"`([^`]+)`", r"\1", str(s or ""))
    return re.sub(r"\*\*([^*]+)\*\*", r"\1", t).strip()


def bullets_de(v):
    """Normaliza campo de texto em lista de bullets. String vira lista de um."""
    if isinstance(v, (list, tuple)):
        return [str(x or "").strip() for x in v if str(x or "").strip()]
    s = str(v or "").strip()
    return [s] if s else []


def _tem_emoji_inicial(s):
    if not s:
        return False
    cp = ord(s[0])
    return any(lo <= cp <= hi for lo, hi in _FAIXAS_EMOJI)


def erros_de_estilo(v, onde, nome_perfil="pagina"):
    """A régua, aplicada a QUALQUER campo de texto que um gerador emite.

    Fora do alcance de propósito, em todo perfil: saída crua de prova (é literal
    por obrigação) e a válvula de HTML. Ver quality-goals.md, "A régua de estilo".
    """
    p = perfil(nome_perfil)
    errs = []
    itens = bullets_de(v)
    lista = isinstance(v, (list, tuple))
    if lista and len(itens) > p.bullets_max:
        errs.append("%s: %d bullets, o teto é %d — acima disso é prosa picada, "
                    "ou são dois itens" % (onde, len(itens), p.bullets_max))
    for i, t in enumerate(itens, 1):
        alvo = "%s bullet %d" % (onde, i) if lista else onde
        nu = _cru(t)
        if p.arvore_fora and _ARVORE.match(t.strip()):
            # Linha desenhada pelo programa: glifo de status + id + contagem. Não é redação.
            continue
        if p.cabecalho_com_emoji and not _BULLET_HOOK.match(t) and not _tem_emoji_inicial(t):
            errs.append("%s: cabeçalho sem emoji — no canal de texto o destaque só "
                        "vem do emoji e da posição" % alvo)
        if p.sem_markdown and _MARKDOWN.search(str(t)):
            errs.append("%s: markdown num canal que não renderiza markdown — `**` e "
                        "crase chegam literais na tela" % alvo)
        if len(nu) > p.bullet_max:
            errs.append("%s: %d caracteres, o teto é %d — quebre em bullets, "
                        "não encolha a informação" % (alvo, len(nu), p.bullet_max))
        if p.palavras_max and len(nu.split()) > p.palavras_max:
            errs.append("%s: %d palavras, o teto é %d — slide é lido de longe, "
                        "não é parágrafo projetado" % (alvo, len(nu.split()), p.palavras_max))
        if _DUAS_FRASES.search(nu):
            errs.append("%s: duas frases no mesmo bullet — parágrafo disfarçado; "
                        "vire dois bullets" % alvo)
        if _CONECTIVO.match(nu):
            errs.append("%s: abre com conectivo de continuação — é o parágrafo "
                        "anterior fatiado, não um bullet" % alvo)
    return errs


# ── linha de comando: como um .sh cobra a MESMA régua ──────────────────────
# Os emissores de hook são bash e a régua é Python. Sem esta entrada cada .sh
# redigitaria as quatro checagens em `grep` — a segunda cópia, que diverge no
# primeiro ajuste. Contrato: o texto vem da stdin, UMA LINHA = um bullet (é
# assim que o canal de texto do terminal é lido), exit 0 calado quando passa,
# exit 1 com um motivo por linha no stderr.

_USO = "uso: regua_texto.py [--perfil NOME] [--onde ROTULO] -   (texto na stdin)\n"


def _main(argv):
    nome, onde, tem_stdin = "pagina", "texto", False
    it = iter(argv)
    for a in it:
        if a == "--perfil":
            nome = next(it, "")
        elif a == "--onde":
            onde = next(it, "")
        elif a == "-":
            tem_stdin = True
        else:
            sys.stderr.write(_USO)
            return 2
    if not tem_stdin:
        sys.stderr.write(_USO)
        return 2
    linhas = [ln for ln in sys.stdin.read().splitlines() if ln.strip()]
    try:
        errs = erros_de_estilo(linhas, onde, nome)
    except ValueError as e:
        sys.stderr.write("%s\n" % e)
        return 2
    for e in errs:
        sys.stderr.write("%s\n" % e)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
