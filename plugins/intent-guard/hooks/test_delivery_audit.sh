#!/usr/bin/env bash
# Gate de entrega — GATILHO = COMMIT NOVO (decisão de projeto, 2026-07-24).
# A primeira passada de cada sessão só registra o HEAD de partida; a cobrança
# acontece quando aparece commit novo. Antes o gatilho era "mexeu em arquivo",
# o que fazia um agente caro rodar a cada turno.
set -euo pipefail
# ── REPROVAR SEM DIZER POR QUÊ É METADE DE UM MEDIDOR ─────────────────────────
# As asserções aqui são `[ -z "$OUT" ]` e `grep -q` nus: com `set -e`, falhar
# derruba o script SEM imprimir nada. Medido em 2026-08-14: a esteira acusou esta
# suíte com "(sem detalhe impresso)", e descobrir a linha exigiu rodá-la à mão
# várias vezes. Este trap troca o silêncio pela linha e pelo comando que caíram —
# é a mesma régua que o resto do repositório cobra dos gates.
trap 'c=$?; [ "$c" -ne 0 ] && printf "FALHOU na linha %s: %s (exit %s)\n" "$LINENO" "$BASH_COMMAND" "$c" >&2; exit $c' ERR
# O hook grava no temporário DO SISTEMA — a suíte pergunta pelo mesmo caminho
# que ele, em vez de assumir /tmp.
# shellcheck source=/dev/null
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib-tmpdir.sh"
TMPD=$(td_tmpdir)
# ── O LAR É FINGIDO, E POR ISSO ESTA SUÍTE PODE RODAR EM PARALELO ────────────
# O `delivery-audit.sh` lê `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/intent-guard/mode`
# e escreve estado por sessão. Sem fingir o lar, esta suíte usava o lar REAL de
# quem a roda — e, com ids de sessão fixos, ela e a `test_task_checkpoint.sh`
# pisavam uma na outra quando a esteira as disparava ao mesmo tempo. Medido em
# 2026-08-14: em série as duas passam (150s e 235s); em paralelo, as duas caem.
# Foi a guarda de saúde do motor que pegou, na primeira largada em que a esteira
# realmente rodou — antes disso o comando media zero suítes e dizia verde.
# shellcheck source=/dev/null
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib-lar-fingido.sh"
LAR_DA="$(mktemp -d "$TMPD"/ig-da-lar-XXXXXX)"
lar_fingido_exporta "$LAR_DA"
export CLAUDE_CONFIG_DIR="$LAR_DA/.claude"
HERE="$(cd "$(dirname "$0")" && pwd)"
export CLAUDE_PLUGIN_ROOT="$(dirname "$HERE")"
L="$CLAUDE_PLUGIN_ROOT/lib/ledger.py"

REPO_SPACE=""
# Mocks do juiz em temporário POR EXECUÇÃO — ver test_task_checkpoint.sh.
MOCKD="$(mktemp -d "$(td_tmpdir)"/ig-da-mock-XXXXXX)"

# ── O JUIZ É MOCK DESDE A PRIMEIRA LINHA, NUNCA O MODELO DE VERDADE ──────────
# Sem `INTENT_GUARD_JUDGE_CMD` o hook chama `claude -p --model haiku` (linha 85
# do delivery-audit.sh) para classificar o cru. Os casos 1 a 7 desta suíte não
# definiam o mock, então mediam o veredito de um MODELO: lento, pago, e — o que
# importa aqui — não-determinístico. Medido em 2026-08-14: rodando em paralelo
# com as vizinhas, a suíte caía ora na linha 60, ora na 70, ora passava. Teste
# que muda de resposta sem o código mudar não é teste, é sorteio.
# O mock sai NÃO-ZERO de propósito: é o caminho do "juiz indisponível", que o
# hook trata como fail-open ("segue com o que já estava classificado"). É esse o
# comportamento que os casos 1-7 sempre mediram — só que por acidente, quando a
# chamada real ao modelo falhava ou demorava. Agora é escolha declarada, e o
# resultado não depende mais de quem responde do outro lado da rede.
cat > "$MOCKD/mock_classify_mudo.sh" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null
exit 1
EOF
chmod +x "$MOCKD/mock_classify_mudo.sh"
export INTENT_GUARD_JUDGE_CMD="$MOCKD/mock_classify_mudo.sh"
trap 'rm -rf "${REPO:-}" "${REPO2:-}" "${REPO3:-}" "${REPO4:-}" "$REPO_SPACE" "${BARE:-}" "$MOCKD" "${LAR_DA:-}";
      rm -f "$TMPD"/intent-guard-{work,stopdeny,seenhead}-{dasid,spacesid,pendsid,convsid,escsid}' EXIT
# ⚠️ E LIMPA ANTES TAMBÉM, não só na saída. O caso 1 mede "a PRIMEIRA passada da
# sessão", e os ids aqui são fixos: um `seenhead-dasid` sobrando de uma execução
# anterior — que morreu no meio, ou que o trap não alcançou — faz a primeira
# passada não ser a primeira, e o caso cai. Medido em 2026-08-14: rodando três
# vezes seguidas em paralelo, a 1ª caía e as duas seguintes passavam. Suíte que
# depende de não ter sobrado nada da anterior é suíte que dá resultado por sorte.
rm -f "$TMPD"/intent-guard-{work,stopdeny,seenhead}-{dasid,spacesid,pendsid,convsid,escsid}

commit_new() {  # commit_new <repo> <marca> — cria um commit novo de verdade
  echo "$2" >> "$1/work.txt"
  git -C "$1" add -A
  git -C "$1" -c user.email=t@t -c user.name=t commit -qm "$2"
}

# O temporário vem de `td_tmpdir`, nunca de `/tmp` cravado: no Git Bash do
# Windows `/tmp` é caminho do SHELL, e o `ledger.py`/`python3` que recebe esse
# `cwd` é o Python nativo — ele resolve `/tmp/x` como `C:\tmp\x`, que não
# existe. O ledger nascia noutro lugar e o `grep` do teste não achava nada.
REPO="$(mktemp -d "$(td_tmpdir)"/ig-da-XXXXXX)"; git -C "$REPO" init -q
touch "$REPO/f"; git -C "$REPO" add -A; git -C "$REPO" -c user.email=t@t -c user.name=t commit -qm i
mkin() { printf '{"session_id":"dasid","cwd":"%s"}' "$REPO"; }

printf 'faz X' | python3 "$L" record-raw --cwd "$REPO" --session dasid --text-stdin
printf '%s' '{"ev":"classify","raw":"r-1","class":"pedido","resumo":"X","substitui":null}' | python3 "$L" apply --cwd "$REPO"

# 1. primeira passada da sessão → só registra o HEAD de partida, não cobra
OUT="$(mkin | bash "$HERE/delivery-audit.sh")"; [ -z "$OUT" ]
[ -f "$TMPD"/intent-guard-seenhead-dasid ]

# 2. NOVO GATILHO: sem commit novo não cobra, por mais que haja pedido vivo
echo "rascunho" > "$REPO/rascunho.txt"
OUT="$(mkin | bash "$HERE/delivery-audit.sh")"; [ -z "$OUT" ]

# 3. commit novo + vivo sem audit → decision:block com o fluxo do auditor
commit_new "$REPO" c1
OUT="$(mkin | bash "$HERE/delivery-audit.sh")"
grep -q '"decision"' <<< "$OUT"
grep -q 'auditor-prompt.md' <<< "$OUT"
grep -q 'tree_hash:' <<< "$OUT"
grep -q 'saida:' <<< "$OUT"
grep -q 'faz X' <<< "$OUT"

# 4. audit válido no tree atual → libera, TRANSCREVE e avança o marco
H="$(python3 "$L" tree-hash --cwd "$REPO")"
python3 - "$REPO" "$H" <<'EOF'
import json, sys
json.dump({"tree_hash": sys.argv[2], "generated_ts": 1, "verdicts": [
  {"entry": "p-1", "verdict": "feito", "mode": "confirmado",
   "evidence": "rodei X e conferi a saída real"}]},
  open(sys.argv[1] + "/.claude/intent/audit-t.json", "w"))
EOF
OUT="$(mkin | bash "$HERE/delivery-audit.sh")"; [ -z "$OUT" ]
python3 "$L" state --cwd "$REPO" | grep -q 'baixado:auditor'
[ "$(cat "$TMPD"/intent-guard-seenhead-dasid)" = "$(git -C "$REPO" rev-parse HEAD)" ]

# 5. cap de stop-denies: pedido vivo novo + commit novo + contador em 2 → libera
printf 'faz Y' | python3 "$L" record-raw --cwd "$REPO" --session dasid --text-stdin
printf '%s' '{"ev":"classify","raw":"r-2","class":"pedido","resumo":"Y","substitui":null}' | python3 "$L" apply --cwd "$REPO"
commit_new "$REPO" c2
echo 2 > "$TMPD"/intent-guard-stopdeny-dasid
OUT="$(mkin | bash "$HERE/delivery-audit.sh")"; [ -z "$OUT" ]
rm -f "$TMPD"/intent-guard-stopdeny-dasid

# 6. ESCADA DE CUSTO: pedido com receita mecânica é resolvido SEM agente
REPO4="$(mktemp -d "$(td_tmpdir)"/ig-da4-XXXXXX)"; BARE="$(mktemp -d "$(td_tmpdir)"/ig-bare4-XXXXXX)"
git -C "$REPO4" init -q; git init -q --bare "$BARE"
touch "$REPO4/f"; git -C "$REPO4" add -A
git -C "$REPO4" -c user.email=t@t -c user.name=t commit -qm i
git -C "$REPO4" remote add origin "$BARE"; git -C "$REPO4" push -q -u origin HEAD
printf 'commit push' | python3 "$L" record-raw --cwd "$REPO4" --session escsid --text-stdin
printf '%s' '{"ev":"classify","raw":"r-1","class":"pedido","resumo":"commit push","substitui":null,"verify":"git_synced"}' | python3 "$L" apply --cwd "$REPO4"
ESC() { printf '{"session_id":"escsid","cwd":"%s"}' "$REPO4"; }
OUT="$(ESC | bash "$HERE/delivery-audit.sh")"; [ -z "$OUT" ]   # marca o HEAD de partida
echo "x" >> "$REPO4/f"; git -C "$REPO4" add -A
git -C "$REPO4" -c user.email=t@t -c user.name=t commit -qm c1
git -C "$REPO4" push -q origin HEAD                            # sincronizado de novo
OUT="$(ESC | bash "$HERE/delivery-audit.sh")"
[ -z "$OUT" ] || { echo "FALHA: receita mecânica devia ter resolvido sem bloquear"; exit 1; }
python3 "$L" state --cwd "$REPO4" | grep -q 'baixado:receita' \
  || { echo "FALHA: o pedido não foi baixado pela receita"; exit 1; }

# 7. sem session_id → não age (fail-open, nunca estado global)
[ -z "$(printf '%s' "{\"cwd\":\"$REPO\"}" | bash "$HERE/delivery-audit.sh")" ]

# 8. cru NUNCA classificado (sessão sem plan mode) + commit novo → classifica no
#    gate de entrega e BLOQUEIA citando o fluxo do auditor
REPO2="$(mktemp -d "$(td_tmpdir)"/ig-da2-XXXXXX)"; git -C "$REPO2" init -q
touch "$REPO2/f"; git -C "$REPO2" add -A; git -C "$REPO2" -c user.email=t@t -c user.name=t commit -qm i
printf 'faz W' | python3 "$L" record-raw --cwd "$REPO2" --session pendsid --text-stdin
cat > "$MOCKD/mock_classify_pedido.sh" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null
echo '{"classify":[{"ev":"classify","raw":"r-1","class":"pedido","resumo":"W","substitui":null,"verify":null}]}'
EOF
chmod +x "$MOCKD/mock_classify_pedido.sh"
export INTENT_GUARD_JUDGE_CMD="$MOCKD/mock_classify_pedido.sh"
P2() { printf '{"session_id":"pendsid","cwd":"%s"}' "$REPO2"; }
OUT="$(P2 | bash "$HERE/delivery-audit.sh")"; [ -z "$OUT" ]   # marca o HEAD
commit_new "$REPO2" c1
OUT="$(P2 | bash "$HERE/delivery-audit.sh")"
grep -q '"decision"' <<< "$OUT"
grep -q 'auditor-prompt.md' <<< "$OUT"

# 9. cru classificado como conversa → segue mudo mesmo com commit novo
REPO3="$(mktemp -d "$(td_tmpdir)"/ig-da3-XXXXXX)"; git -C "$REPO3" init -q
touch "$REPO3/f"; git -C "$REPO3" add -A; git -C "$REPO3" -c user.email=t@t -c user.name=t commit -qm i
printf 'kkk boa' | python3 "$L" record-raw --cwd "$REPO3" --session convsid --text-stdin
cat > "$MOCKD/mock_classify_conversa.sh" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null
echo '{"classify":[{"ev":"classify","raw":"r-1","class":"conversa","resumo":"","substitui":null}]}'
EOF
chmod +x "$MOCKD/mock_classify_conversa.sh"
export INTENT_GUARD_JUDGE_CMD="$MOCKD/mock_classify_conversa.sh"
P3() { printf '{"session_id":"convsid","cwd":"%s"}' "$REPO3"; }
OUT="$(P3 | bash "$HERE/delivery-audit.sh")"; [ -z "$OUT" ]
commit_new "$REPO3" c1
OUT="$(P3 | bash "$HERE/delivery-audit.sh")"; [ -z "$OUT" ]
unset INTENT_GUARD_JUDGE_CMD

# 10. path com espaço: while loop lê o audit sem word-splitting
REPO_SPACE="$(mktemp -d "/tmp/ig da XXXXXX")"; git -C "$REPO_SPACE" init -q
touch "$REPO_SPACE/f"; git -C "$REPO_SPACE" add -A
git -C "$REPO_SPACE" -c user.email=t@t -c user.name=t commit -qm i
printf 'faz Z' | python3 "$L" record-raw --cwd "$REPO_SPACE" --session spacesid --text-stdin
printf '%s' '{"ev":"classify","raw":"r-1","class":"pedido","resumo":"Z","substitui":null}' | python3 "$L" apply --cwd "$REPO_SPACE"
PS_() { printf '{"session_id":"spacesid","cwd":"%s"}' "$REPO_SPACE"; }
OUT="$(PS_ | bash "$HERE/delivery-audit.sh")"; [ -z "$OUT" ]
commit_new "$REPO_SPACE" c1
H="$(python3 "$L" tree-hash --cwd "$REPO_SPACE")"
python3 - "$REPO_SPACE" "$H" <<'EOF'
import json, sys
json.dump({"tree_hash": sys.argv[2], "generated_ts": 1, "verdicts": [
  {"entry": "p-1", "verdict": "feito", "mode": "confirmado",
   "evidence": "rodei Z com espaço no path e funcionou"}]},
  open(sys.argv[1] + "/.claude/intent/audit-space.json", "w"))
EOF
OUT="$(PS_ | bash "$HERE/delivery-audit.sh")"; [ -z "$OUT" ]
python3 "$L" state --cwd "$REPO_SPACE" | grep -q 'baixado:auditor'

echo "test_delivery_audit: OK"
exit 0   # o trap de limpeza roda depois; sem isto o exit vira o do último rm
