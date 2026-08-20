#!/usr/bin/env bash
# test_sessionstart_doc.sh — cobre o achado F1 (sessão 871f9573): o hook só
# contava documento autoral no ramo "sem doc nenhuma"; um projeto já minerado
# e com ZERO autorais passava batido. Ver .claude/docs/patterns.md §5.3 pro
# contrato (canal/cap/kill-switch/fail-open) que o achado F1.2 aplicou aqui.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$(cd "$(dirname "$0")" && pwd)/lib-tmpdir.sh"
HOOK="$HERE/sessionstart-doc.sh"
# Fingir o lar é receita única (lib-lar-fingido.sh, contrato em lar-fingido.md).
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib-lar-fingido.sh"

trap 'rm -rf "${MINERADO:-}" "${COMPLETO:-}" "${PARCIAL:-}" "${VAZIO:-}" "${NOVO:-}" "${FAKEHOME:-}"; rm -f /tmp/claude-doc-autoral-nudge-*' EXIT

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
# O temporário vem de `td_tmpdir`, nunca de `/tmp` cravado: no Git Bash do
# Windows `/tmp` é caminho do SHELL, e o `ledger.py`/`python3` que recebe esse
# `cwd` é o Python nativo — ele resolve `/tmp/x` como `C:\tmp\x`, que não
# existe. O ledger nascia noutro lugar e o `grep` do teste não achava nada.
MINERADO="$(mktemp -d "$(td_tmpdir)"/pd-ck-min-XXXXXX)"
mkdir -p "$MINERADO/.claude/docs"
printf '# arch\n' > "$MINERADO/.claude/docs/architecture.md"
printf '<!-- project-doc:v2 -->\narch\n' > "$MINERADO/.claude/CLAUDE.md"

# --- fixture: doc minerada + os 6 autorais completos ---
COMPLETO="$(mktemp -d "$(td_tmpdir)"/pd-ck-full-XXXXXX)"
mkdir -p "$COMPLETO/.claude/docs"
printf '# arch\n' > "$COMPLETO/.claude/docs/architecture.md"
for f in constituicao quality-goals constraints context solution-strategy glossary; do
  printf 'x\n' > "$COMPLETO/.claude/docs/${f}.md"
done
printf '<!-- project-doc:v2 -->\narch\n' > "$COMPLETO/.claude/CLAUDE.md"

# --- fixture: sem doc nenhuma ---
VAZIO="$(mktemp -d "$(td_tmpdir)"/pd-ck-vazio-XXXXXX)"
git -C "$VAZIO" init -q

# 1. minerado + zero autorais → avisa (o buraco original)
OUT="$(mkin "$MINERADO" sess-1 | bash "$HOOK")"
ctxq "$OUT" "ZERO dos 6 autorais"
echo "1. minerado-sem-autoral avisa: OK"

# 2. mesma sessão de novo → cap, cala a linha do autoral (o resto do hook continua falando)
OUT="$(mkin "$MINERADO" sess-1 | bash "$HOOK")"
! ctxq "$OUT" "ZERO dos 6 autorais"
echo "2. cap 1x/sessão: OK"

# 3. sessão nova → avisa de novo (cap é por sessão, não permanente)
OUT="$(mkin "$MINERADO" sess-2 | bash "$HOOK")"
ctxq "$OUT" "ZERO dos 6 autorais"
echo "3. sessão nova reavisa: OK"

# 4. kill-switch DOC_AUTORAL_GATE=0 → cala mesmo em sessão nova
IN4="$(mkin "$MINERADO" sess-3)"
OUT="$(printf '%s' "$IN4" | DOC_AUTORAL_GATE=0 bash "$HOOK")"
! ctxq "$OUT" "ZERO dos 6 autorais"
echo "4. kill-switch DOC_AUTORAL_GATE=0: OK"

# 5. os 6 autorais completos → nunca fala (não pode cobrar quem já tem)
OUT="$(mkin "$COMPLETO" sess-4 | bash "$HOOK")"
! ctxq "$OUT" "ZERO dos 6 autorais"
echo "5. autorais completos, silêncio: OK"

# 6. sem doc nenhuma → ramo antigo intacto, sem menção a "ZERO dos 6 autorais"
#    (esse ramo já tem sua própria contagem de autoral, mensagem diferente)
OUT="$(mkin "$VAZIO" sess-5 | bash "$HOOK")"
! ctxq "$OUT" "tem doc minerada mas ZERO"
ctxq "$OUT" "não tem documentação nenhuma"
echo "6. sem doc nenhuma, ramo antigo intacto: OK"

# --- fixture: doc minerada, ZERO autorais, MAS com sinal de frontend (.tsx) ---
FRONTEND="$(mktemp -d "$(td_tmpdir)"/pd-ck-front-XXXXXX)"
mkdir -p "$FRONTEND/.claude/docs"
printf '# arch\n' > "$FRONTEND/.claude/docs/architecture.md"
printf '<!-- project-doc:v2 -->\narch\n' > "$FRONTEND/.claude/CLAUDE.md"
git -C "$FRONTEND" init -q
echo "export default 1" > "$FRONTEND/App.tsx"
git -C "$FRONTEND" add -A && git -C "$FRONTEND" -c user.email=t@t -c user.name=t commit -qm i

# 7. projeto COM interface + zero autorais → conta 7 (design entra), não 6 (F2.2)
OUT="$(mkin "$FRONTEND" sess-front | bash "$HOOK")"
ctxq "$OUT" "ZERO dos 7 autorais"
ctxq "$OUT" "design"
echo "7. projeto com interface conta design.md (7): OK"

# 8. lib-has-frontend.sh AUSENTE → o hook NÃO pode emudecer; só perde a contagem de
#    design.md. É a isenção "uso local já degradado dispensa guarda no topo" de
#    patterns.md §5.3 — um exit 0 no topo mataria trabalho que não depende da lib.
HOOKDIR="$(mktemp -d "$(td_tmpdir)"/pd-ck-nolib-XXXXXX)"
# `hook-json.sh` vai junto: é o leitor do payload (vendorado de _shared/), sem o qual
# o hook não lê nem o `cwd` — dependência da mesma natureza do doc-detect.sh.
# A lista NÃO se escreve à mão: o hook ganha dependência nova (foi assim que
# `lib-casa-da-doc.sh` entrou na migração de 2026-08-20) e a lista escrita fica para
# trás — o ambiente mínimo nasce sem a lib, o hook não acha a doc, e o caso reprova
# por um motivo que não é o que ele mede. Copia TUDO e tira só a que o caso exclui.
cp "$HERE/sessionstart-doc.sh" "$HERE"/doc-detect.sh "$HERE"/lib-*.sh \
   "$HERE/hook-json.sh" "$HOOKDIR/" 2>/dev/null
# de propósito, a única ausente: é ela que este caso mede
rm -f "$HOOKDIR/lib-has-frontend.sh"
OUT="$(mkin "$FRONTEND" sess-nolib | bash "$HOOKDIR/sessionstart-doc.sh")"
ctxq "$OUT" "documentação project-doc"       # o heads-up sobrevive
ctxq "$OUT" "ZERO dos 6 autorais"            # cai pra 6: design não conta
rm -rf "$HOOKDIR"
echo "8. sem lib-has-frontend: hook não emudece, só perde design: OK"

rm -rf "$FRONTEND"

# --- F7.4: a oferta da metodologia é o PADRÃO de projeto novo -----------------
# Fixtures novas em vez de reusar o VAZIO: estes casos escrevem a recusa dentro
# de um HOME de mentira, e sujar o HOME real da máquina que roda a suíte não é
# opção. O HOME sobrescrito também mantém a subida do project_root intacta —
# as fixtures moram em /tmp, fora dele.
NOVO="$(mktemp -d "$(td_tmpdir)"/pd-ck-novo-XXXXXX)"
git -C "$NOVO" init -q
FAKEHOME="$(mktemp -d "$(td_tmpdir)"/pd-ck-home-XXXXXX)"
RECUSA="$FAKEHOME/.claude/doc/sem-metodologia-$(printf '%s' "$NOVO" | cksum | cut -d' ' -f1)"

# 9. projeto novo, nada recusado → a oferta sai por padrão, contando CINCO etapas
#    e mandando colher o de acordo na página (F7.1), não no chat.
OUT="$(mkin "$NOVO" sess-novo | lar_fingido "$FAKEHOME" bash "$HOOK")"
ctxq "$OUT" "/start"
ctxq "$OUT" "cinco etapas"
ctxq "$OUT" "página"
echo "9. projeto novo recebe a oferta por padrão (cinco etapas, de acordo na página): OK"

# 10. recusa explícita gravada → cala, e cala em QUALQUER sessão (a recusa é do
#     projeto, não da sessão: o usuário não repete a frase a cada /clear).
mkdir -p "$(dirname "$RECUSA")"
: > "$RECUSA"
OUT="$(mkin "$NOVO" sess-novo-2 | lar_fingido "$FAKEHOME" bash "$HOOK")"
[ -z "$OUT" ]
echo "10. recusa explícita cala a oferta, em sessão nova: OK"

# 11. recusa apagada → a oferta volta (a recusa é reversível, não uma via só)
rm -f "$RECUSA"
OUT="$(mkin "$NOVO" sess-novo-3 | lar_fingido "$FAKEHOME" bash "$HOOK")"
ctxq "$OUT" "cinco etapas"
echo "11. apagar a recusa devolve a oferta: OK"

# --- F1.2: lacuna PARCIAL também é lacuna ------------------------------------
# O ramo da doc minerada só falava com AUTORAL -eq 0: projeto com 2 dos 6
# autorais passava calado, e o silêncio lia como conformidade. Este caso reprova
# o comportamento velho — sem o conserto, OUT não menciona os que faltam.
PARCIAL="$(mktemp -d "$(td_tmpdir)"/pd-ck-parc-XXXXXX)"
mkdir -p "$PARCIAL/.claude/docs"
printf '# arch\n' > "$PARCIAL/.claude/docs/architecture.md"
for f in quality-goals constraints; do printf 'x\n' > "$PARCIAL/.claude/docs/${f}.md"; done
printf '<!-- project-doc:v2 -->\narch\n' > "$PARCIAL/.claude/CLAUDE.md"

# 12. 2 de 6 autorais → avisa nomeando os 4 que faltam
OUT="$(mkin "$PARCIAL" sess-parc | bash "$HOOK")"
ctxq "$OUT" "só 2 de 6 autorais"
ctxq "$OUT" "falta: constituicao, context, solution-strategy, glossary"
echo "12. lacuna parcial avisa nomeando o que falta: OK"

# 13. o cap e o kill-switch valem igual na lacuna parcial
OUT="$(mkin "$PARCIAL" sess-parc | bash "$HOOK")"
! ctxq "$OUT" "só 2 de 6 autorais"
OUT="$(mkin "$PARCIAL" sess-parc-2 | DOC_AUTORAL_GATE=0 bash "$HOOK")"
! ctxq "$OUT" "só 2 de 6 autorais"
echo "13. parcial respeita cap e kill-switch: OK"

# --- F1.3: a LEI entra na conta ----------------------------------------------
# constituicao.md ficava fora da lista: o documento que a auditoria e o gate de
# plano abrem nunca era cobrado. Este caso reprova o comportamento velho — e
# confere que o número impresso sai do TAMANHO da lista, não da mão.
LEI="$(mktemp -d "$(td_tmpdir)"/pd-ck-lei-XXXXXX)"
mkdir -p "$LEI/.claude/docs"
printf '# arch\n' > "$LEI/.claude/docs/architecture.md"
for f in quality-goals constraints context solution-strategy glossary; do
  printf 'x\n' > "$LEI/.claude/docs/${f}.md"
done
printf '<!-- project-doc:v2 -->\narch\n' > "$LEI/.claude/CLAUDE.md"

# 14. só a lei faltando → aparece no aviso, e a contagem impressa bate com a lista
OUT="$(mkin "$LEI" sess-lei | bash "$HOOK")"
ctxq "$OUT" "falta: constituicao"
# A contagem tem que vir da lista que produziu ESTE número — a do ramo da doc
# minerada (a ÚLTIMA cópia no arquivo), não a do ramo "projeto sem doc nenhuma".
# Com `-m1` o teste lia a lista errada e só passava porque as duas coincidem.
N_LISTA=$(grep 'AUTORAIS_DOCS="constituicao' "$HOOK" | tail -1 | sed 's/.*="//; s/".*//' | wc -w | tr -d ' ')
ctxq "$OUT" "só 5 de ${N_LISTA} autorais"
rm -rf "$LEI"
echo "14. a lei ausente aparece no aviso e a contagem bate com a lista (${N_LISTA}): OK"

# 15. as DUAS cópias literais da lista (ramo sem-doc e ramo minerado) têm que ser
#     iguais — nada no hook impede que uma ganhe documento e a outra fique pra trás.
N_COPIAS=$(grep -c 'AUTORAIS_DOCS="constituicao' "$HOOK")
[ "$N_COPIAS" -eq 2 ]
[ "$(grep 'AUTORAIS_DOCS="constituicao' "$HOOK" | sed 's/.*="//; s/".*//' | sort -u | wc -l | tr -d ' ')" -eq 1 ]
echo "15. as 2 cópias de AUTORAIS_DOCS são idênticas: OK"

# 16. projeto com doc minerada e ZERO autorais → o aviso cita o modo ex-post.
#     É o caso do projeto maduro: obra minerada no disco prova que há de onde
#     inferir, e mandar o dono para a entrevista do zero desperdiça o que o
#     repositório já manifesta. Sem o conserto, OUT só oferecia /start gaps.
MADURO="$(mktemp -d "$(td_tmpdir)"/pd-ck-mad-XXXXXX)"
mkdir -p "$MADURO/.claude/docs"
printf '# arch\n' > "$MADURO/.claude/docs/architecture.md"
printf '<!-- project-doc:v2 -->\narch\n' > "$MADURO/.claude/CLAUDE.md"
OUT="$(mkin "$MADURO" sess-mad | bash "$HOOK")"
ctxq "$OUT" "start ex-post"
echo "16. projeto maduro sem autoral recebe a oferta do ex-post: OK"

echo "test_sessionstart_doc: OK"
