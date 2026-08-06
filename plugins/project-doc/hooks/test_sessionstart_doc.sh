#!/usr/bin/env bash
# test_sessionstart_doc.sh — cobre o achado F1 (sessão 871f9573): o hook só
# contava documento autoral no ramo "sem doc nenhuma"; um projeto já minerado
# e com ZERO autorais passava batido. Ver .claude/docs/patterns.md §5.3 pro
# contrato (canal/cap/kill-switch/fail-open) que o achado F1.2 aplicou aqui.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
HOOK="$HERE/sessionstart-doc.sh"
trap 'rm -rf "${MINERADO:-}" "${COMPLETO:-}" "${VAZIO:-}" "${NOVO:-}" "${FAKEHOME:-}"; rm -f /tmp/claude-doc-autoral-nudge-*' EXIT

mkin() { python3 -c 'import json,sys; print(json.dumps({"cwd":sys.argv[1],"session_id":sys.argv[2]}))' "$@"; }
ctx() { python3 -c 'import json,sys; print(json.load(sys.stdin)["hookSpecificOutput"]["additionalContext"])'; }

# ⚠️ NUNCA ponha o `ctx` (um python3) upstream de `grep -q`: o grep sai no PRIMEIRO
# match e fecha o pipe, o python leva SIGPIPE e morre com BrokenPipeError no flush do
# stdout — exit 120. Com o `set -euo pipefail` do topo, o `pipefail` propaga esse 120 e
# o `-e` derruba a suite inteira. É uma CORRIDA (o python normalmente termina de
# escrever antes), então falhava ~1 em 8 rodadas — e como o check F do release-gate roda
# esta suite, o gate de commit ficava vermelho por sorteio, num commit que não tinha
# nada a ver. Gate intermitente é pior que gate nenhum: ensina a reexecutar até passar.
# NÃO basta materializar a saída do python numa variável e continuar pipando pro grep:
# a 1ª tentativa de conserto fez isso e só MOVEU o SIGPIPE do python pro `printf` do
# shell (`printf: write error: Broken pipe`), piorando a taxa pra 20 em 40. Quem fecha o
# pipe é o `grep -q`, então a única correção é **não ter pipe** — here-string alimenta o
# grep por fd, sem processo upstream pra matar. [medido em 2026-07-29: 1 falha em 8 antes,
# 20 em 40 com o conserto errado, 0 em 60 com este]
ctxq() { grep -q -- "$2" <<< "$(printf '%s' "$1" | ctx)"; }

# --- fixture: doc minerada (architecture.md), ZERO autorais ---
MINERADO="$(mktemp -d /tmp/pd-ck-min-XXXXXX)"
mkdir -p "$MINERADO/.claude/docs"
printf '# arch\n' > "$MINERADO/.claude/docs/architecture.md"
printf '<!-- project-doc:v2 -->\narch\n' > "$MINERADO/.claude/CLAUDE.md"

# --- fixture: doc minerada + os 5 autorais completos ---
COMPLETO="$(mktemp -d /tmp/pd-ck-full-XXXXXX)"
mkdir -p "$COMPLETO/.claude/docs"
printf '# arch\n' > "$COMPLETO/.claude/docs/architecture.md"
for f in quality-goals constraints context solution-strategy glossary; do
  printf 'x\n' > "$COMPLETO/.claude/docs/${f}.md"
done
printf '<!-- project-doc:v2 -->\narch\n' > "$COMPLETO/.claude/CLAUDE.md"

# --- fixture: sem doc nenhuma ---
VAZIO="$(mktemp -d /tmp/pd-ck-vazio-XXXXXX)"
git -C "$VAZIO" init -q

# 1. minerado + zero autorais → avisa (o buraco original)
OUT="$(mkin "$MINERADO" sess-1 | bash "$HOOK")"
ctxq "$OUT" "ZERO dos 5 autorais"
echo "1. minerado-sem-autoral avisa: OK"

# 2. mesma sessão de novo → cap, cala a linha do autoral (o resto do hook continua falando)
OUT="$(mkin "$MINERADO" sess-1 | bash "$HOOK")"
! ctxq "$OUT" "ZERO dos 5 autorais"
echo "2. cap 1x/sessão: OK"

# 3. sessão nova → avisa de novo (cap é por sessão, não permanente)
OUT="$(mkin "$MINERADO" sess-2 | bash "$HOOK")"
ctxq "$OUT" "ZERO dos 5 autorais"
echo "3. sessão nova reavisa: OK"

# 4. kill-switch DOC_AUTORAL_GATE=0 → cala mesmo em sessão nova
IN4="$(mkin "$MINERADO" sess-3)"
OUT="$(printf '%s' "$IN4" | DOC_AUTORAL_GATE=0 bash "$HOOK")"
! ctxq "$OUT" "ZERO dos 5 autorais"
echo "4. kill-switch DOC_AUTORAL_GATE=0: OK"

# 5. os 5 autorais completos → nunca fala (não pode cobrar quem já tem)
OUT="$(mkin "$COMPLETO" sess-4 | bash "$HOOK")"
! ctxq "$OUT" "ZERO dos 5 autorais"
echo "5. autorais completos, silêncio: OK"

# 6. sem doc nenhuma → ramo antigo intacto, sem menção a "ZERO dos 5 autorais"
#    (esse ramo já tem sua própria contagem de autoral, mensagem diferente)
OUT="$(mkin "$VAZIO" sess-5 | bash "$HOOK")"
! ctxq "$OUT" "tem doc minerada mas ZERO"
ctxq "$OUT" "não tem documentação nenhuma"
echo "6. sem doc nenhuma, ramo antigo intacto: OK"

# --- fixture: doc minerada, ZERO autorais, MAS com sinal de frontend (.tsx) ---
FRONTEND="$(mktemp -d /tmp/pd-ck-front-XXXXXX)"
mkdir -p "$FRONTEND/.claude/docs"
printf '# arch\n' > "$FRONTEND/.claude/docs/architecture.md"
printf '<!-- project-doc:v2 -->\narch\n' > "$FRONTEND/.claude/CLAUDE.md"
git -C "$FRONTEND" init -q
echo "export default 1" > "$FRONTEND/App.tsx"
git -C "$FRONTEND" add -A && git -C "$FRONTEND" -c user.email=t@t -c user.name=t commit -qm i

# 7. projeto COM interface + zero autorais → conta 6 (design entra), não 5 (F2.2)
OUT="$(mkin "$FRONTEND" sess-front | bash "$HOOK")"
ctxq "$OUT" "ZERO dos 6 autorais"
ctxq "$OUT" "design"
echo "7. projeto com interface conta design.md (6): OK"

# 8. lib-has-frontend.sh AUSENTE → o hook NÃO pode emudecer; só perde a contagem de
#    design.md. É a isenção "uso local já degradado dispensa guarda no topo" de
#    patterns.md §5.3 — um exit 0 no topo mataria trabalho que não depende da lib.
HOOKDIR="$(mktemp -d /tmp/pd-ck-nolib-XXXXXX)"
# `hook-json.sh` vai junto: é o leitor do payload (vendorado de _shared/), sem o qual
# o hook não lê nem o `cwd` — dependência da mesma natureza do doc-detect.sh.
cp "$HERE/sessionstart-doc.sh" "$HERE/doc-detect.sh" "$HERE/lib-project-root.sh" \
   "$HERE/hook-json.sh" "$HOOKDIR/" 2>/dev/null
# de propósito NÃO copia lib-has-frontend.sh
OUT="$(mkin "$FRONTEND" sess-nolib | bash "$HOOKDIR/sessionstart-doc.sh")"
ctxq "$OUT" "documentação project-doc"       # o heads-up sobrevive
ctxq "$OUT" "ZERO dos 5 autorais"            # cai pra 5: design não conta
rm -rf "$HOOKDIR"
echo "8. sem lib-has-frontend: hook não emudece, só perde design: OK"

rm -rf "$FRONTEND"

# --- F7.4: a oferta da metodologia é o PADRÃO de projeto novo -----------------
# Fixtures novas em vez de reusar o VAZIO: estes casos escrevem a recusa dentro
# de um HOME de mentira, e sujar o HOME real da máquina que roda a suíte não é
# opção. O HOME sobrescrito também mantém a subida do project_root intacta —
# as fixtures moram em /tmp, fora dele.
NOVO="$(mktemp -d /tmp/pd-ck-novo-XXXXXX)"
git -C "$NOVO" init -q
FAKEHOME="$(mktemp -d /tmp/pd-ck-home-XXXXXX)"
RECUSA="$FAKEHOME/.claude/project-doc/sem-metodologia-$(printf '%s' "$NOVO" | cksum | cut -d' ' -f1)"

# 9. projeto novo, nada recusado → a oferta sai por padrão, contando CINCO etapas
#    e mandando colher o de acordo na página (F7.1), não no chat.
OUT="$(mkin "$NOVO" sess-novo | HOME="$FAKEHOME" bash "$HOOK")"
ctxq "$OUT" "/start-doc"
ctxq "$OUT" "cinco etapas"
ctxq "$OUT" "página"
echo "9. projeto novo recebe a oferta por padrão (cinco etapas, de acordo na página): OK"

# 10. recusa explícita gravada → cala, e cala em QUALQUER sessão (a recusa é do
#     projeto, não da sessão: o usuário não repete a frase a cada /clear).
mkdir -p "$(dirname "$RECUSA")"
: > "$RECUSA"
OUT="$(mkin "$NOVO" sess-novo-2 | HOME="$FAKEHOME" bash "$HOOK")"
[ -z "$OUT" ]
echo "10. recusa explícita cala a oferta, em sessão nova: OK"

# 11. recusa apagada → a oferta volta (a recusa é reversível, não uma via só)
rm -f "$RECUSA"
OUT="$(mkin "$NOVO" sess-novo-3 | HOME="$FAKEHOME" bash "$HOOK")"
ctxq "$OUT" "cinco etapas"
echo "11. apagar a recusa devolve a oferta: OK"

echo "test_sessionstart_doc: OK"
