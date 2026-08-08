#!/bin/bash
# test_andamento_hook.sh — suíte do narrador de andamento.
#
# Roda o hook DE VERDADE, alimentando o payload pelo stdin, e olha o que sai no
# STDOUT — que é o canal que o harness lê e mostra ao dono. O que sai em stderr
# é descartado de propósito aqui, exatamente como quem chama o hook descarta.
#
#   bash plugins/sovai/hooks/test_andamento_hook.sh

HOOK="$(cd "$(dirname "$0")" && pwd)/posttooluse-andamento.sh"

OK=0
FALHA=0

check() {
  local nome="$1" cond="$2" extra="${3:-}"
  if [ "$cond" = "1" ]; then
    OK=$((OK + 1)); echo "  ok   $nome"
  else
    FALHA=$((FALHA + 1)); echo "  FALHA $nome ${extra}"
  fi
}

# Raiz de config e temporário falsos: a suíte nunca toca no ~/.claude real nem
# no /tmp da máquina.
CFG="$(mktemp -d -t andamento-cfg)"
TMP="$(mktemp -d -t andamento-tmp)"
trap 'rm -rf "$CFG" "$TMP"' EXIT
mkdir -p "$CFG/sovai"
: > "$CFG/sovai/ativo-sess-teste"

SAIDA_COM_PLACAR='rodando a suíte
139 passou · 0 falhou'

paylo() { # $1 = comando, $2 = saída crua, $3 = session_id
  python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","cwd":"/projeto/exemplo","tool_input":{"command":sys.argv[1]},"tool_response":{"stdout":sys.argv[2],"stderr":""},"session_id":sys.argv[3]}))' \
    "$1" "$2" "${3:-sess-teste}"
}

# marca com N segundos ATRÁS, para o decorrido ser controlado e conhecido.
marca_ha() { python3 -c 'import time,sys; open(sys.argv[1],"w").write(str(time.time()-float(sys.argv[2])))' "$TMP/sovai-andamento-${2:-sess-teste}" "$1"; }

roda() { # $1 = comando, $2 = saída, $3 = script (sabotado, opcional), $4 = sid
  CLAUDE_CONFIG_DIR="$CFG" TMPDIR="$TMP" sh "${3:-$HOOK}" <<< "$(paylo "$1" "$2" "${4:-sess-teste}")" 2>/dev/null
}

msg() { # o texto do systemMessage, ou vazio
  printf '%s' "$1" | python3 -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: raise SystemExit
sys.stdout.write(str(d.get("systemMessage") or ""))' 2>/dev/null
}

echo "[narrador de andamento do sovai]"

# 1 · modo marca (PreToolUse): grava o instante e sai calado
rm -f "$TMP/sovai-andamento-sess-teste"
OUT=$(CLAUDE_CONFIG_DIR="$CFG" TMPDIR="$TMP" sh "$HOOK" marca <<< "$(paylo 'npm test' '')" 2>/dev/null)
check "modo marca não imprime nada" "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"
check "modo marca grava o instante do disparo" \
  "$([ -s "$TMP/sovai-andamento-sess-teste" ] && echo 1 || echo 0)"

# 2 · O CRITÉRIO: a linha de andamento é IMPRESSA na tela principal
marca_ha 120
OUT=$(roda 'bash suite.sh' "$SAIDA_COM_PLACAR")
M=$(msg "$OUT")
check "a linha sai em systemMessage (o canal que o dono lê)" \
  "$([ -n "$M" ] && echo 1 || echo 0)" "saiu: $OUT"
check "a linha traz o relógio do que já rodou" \
  "$(printf '%s' "$M" | grep -q 'rodando há' && echo 1 || echo 0)" "saiu: $M"
check "a linha traz o placar cru que a suíte imprimiu" \
  "$(printf '%s' "$M" | grep -q '139 passou · 0 falhou' && echo 1 || echo 0)" "saiu: $M"
check "a linha traz o julgamento de avanço" \
  "$(printf '%s' "$M" | grep -q 'primeiro placar' && echo 1 || echo 0)" "saiu: $M"

# 2b · a duração medida foi REGISTRADA na memória do projeto (é a peça de
#      andamento.py que estava sem chamador)
check "a duração vai para a memória do projeto" \
  "$(ls "$CFG"/sovai/duracoes-*.json >/dev/null 2>&1 && echo 1 || echo 0)"
check "a memória guarda o comando que rodou" \
  "$(grep -q 'suite.sh' "$CFG"/sovai/duracoes-*.json 2>/dev/null && echo 1 || echo 0)"

# 2c · a marca é consumida — o próximo comando não herda a duração deste
check "a marca é apagada depois de narrada" \
  "$([ ! -f "$TMP/sovai-andamento-sess-teste" ] && echo 1 || echo 0)"

# 3 · segunda rodada com o MESMO placar: 'sem avanço' é o sinal que interessa
marca_ha 200
OUT=$(roda 'bash suite.sh' "$SAIDA_COM_PLACAR")
M=$(msg "$OUT")
check "placar repetido é narrado como 'sem avanço'" \
  "$(printf '%s' "$M" | grep -q 'sem avanço' && echo 1 || echo 0)" "saiu: $M"
check "a segunda rodada já mostra a estimativa da memória" \
  "$(printf '%s' "$M" | grep -q 'usual ~' && echo 1 || echo 0)" "saiu: $M"

# 4 · mudo onde tem que ser mudo
marca_ha 3
OUT=$(roda 'echo oi' 'oi')
check "comando curto, sem placar e sem histórico, passa mudo" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"

marca_ha 120 sess-sem-missao
OUT=$(roda 'bash suite.sh' "$SAIDA_COM_PLACAR" "" sess-sem-missao)
check "SEM sinal de missão ativa o narrador passa mudo" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"

rm -f "$TMP/sovai-andamento-sess-teste"
OUT=$(roda 'bash suite.sh' "$SAIDA_COM_PLACAR")
check "SEM marca não há duração medida — passa mudo" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"

marca_ha 120
OUT=$(CLAUDE_CONFIG_DIR="$CFG" TMPDIR="$TMP" SOVAI_ANDAMENTO=0 sh "$HOOK" <<< "$(paylo 'bash suite.sh' "$SAIDA_COM_PLACAR")" 2>/dev/null)
check "SOVAI_ANDAMENTO=0 desliga o narrador" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"

# 4b · O CRITÉRIO DE F9.24: silêncio longo sai na tela, e os dois casos saem
#      DIFERENTES. Só o sinal de vida muda entre os dois cenários abaixo — o
#      arquivo de silêncio é o mesmo, com a mesma idade.
sinal_ha() { python3 -c 'import time,sys; open(sys.argv[1],"w").write(str(time.time()-float(sys.argv[2])))' "$CFG/sovai/sinal-sess-teste" "$1"; }

# com sinal de vida: o comando ocupou os 20 min de silêncio (demora legítima)
sinal_ha 1200
marca_ha 1200
OUT=$(roda 'bash suite-longa.sh' "$SAIDA_COM_PLACAR")
M=$(msg "$OUT")
check "demora legítima sai na tela como 'rodando há N min'" \
  "$(printf '%s' "$M" | grep -q 'rodando há 20 min' && echo 1 || echo 0)" "saiu: $M"
check "demora legítima NÃO é chamada de travamento" \
  "$(printf '%s' "$M" | grep -q 'não é travamento' && echo 1 || echo 0)" "saiu: $M"

# sem sinal de vida: mesmo silêncio de 20 min, mas nada estava rodando
sinal_ha 1200
marca_ha 2
OUT=$(roda 'echo oi' 'oi')
M2=$(msg "$OUT")
check "silêncio sem trabalho vivo sai na tela como travamento" \
  "$(printf '%s' "$M2" | grep -q 'travamento: nada mudou há 20 min' && echo 1 || echo 0)" "saiu: $M2"
check "travamento NÃO sai como 'rodando há N min'" \
  "$(printf '%s' "$M2" | grep -q 'rodando há 20 min' && echo 0 || echo 1)" "saiu: $M2"
check "as duas telas são diferentes" \
  "$([ "$M" != "$M2" ] && echo 1 || echo 0)" "iguais: $M"

# silêncio curto não vira ruído
sinal_ha 30
marca_ha 3
OUT=$(roda 'echo tudo-quieto' 'oi')
check "silêncio curto não narra nada" \
  "$([ -z "$(msg "$OUT")" ] && echo 1 || echo 0)" "saiu: $OUT"
rm -f "$CFG/sovai/sinal-sess-teste"

# 5 · o narrador está LIGADO no caminho do produto (hooks.json), não só no teste
HJ="$(cd "$(dirname "$0")" && pwd)/hooks.json"
check "hooks.json chama o narrador em PostToolUse(Bash)" \
  "$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))
for g in d["hooks"].get("PostToolUse", []):
    if g.get("matcher")=="Bash" and any("posttooluse-andamento.sh" in h.get("command","") for h in g["hooks"]):
        print(1); break
else: print(0)' "$HJ" 2>/dev/null)"
check "hooks.json marca o disparo em PreToolUse(Bash)" \
  "$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))
for g in d["hooks"].get("PreToolUse", []):
    if g.get("matcher")=="Bash" and any(h.get("command","").rstrip().endswith("marca") for h in g["hooks"]):
        print(1); break
else: print(0)' "$HJ" 2>/dev/null)"

# 6 · anti-tautologia: mandar a linha para o canal descartado (stderr) tem que
#     fazer o teste #2 reprovar. É a checagem M do release-gate em miniatura.
SAB="$(mktemp -t andamento-sabotado)"
trap 'rm -f "$SAB"; rm -rf "$CFG" "$TMP"' EXIT
sed 's/^hj_msg "⏱ \$LINHA"$/printf "%s\\n" "$LINHA" >\&2/' "$HOOK" > "$SAB"
marca_ha 120
OUT=$(roda 'bash outra-suite.sh' "$SAIDA_COM_PLACAR" "$SAB")
check "narrador sabotado (linha só no stderr) DEIXA de chegar à tela" \
  "$([ -z "$(msg "$OUT")" ] && echo 1 || echo 0)" "o sabotado ainda imprimiu — o teste #2 é tautológico"

echo
if [ "$FALHA" -eq 0 ]; then
  echo "OK ($OK checks)"
  exit 0
fi
echo "FALHOU ($FALHA de $((OK + FALHA)))"
exit 1
