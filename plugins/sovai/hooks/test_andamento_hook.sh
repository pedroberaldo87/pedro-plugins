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

# 4c · O CRITÉRIO DE F9.23: a MESMA narração na barra de status, que é a única
#      superfície que fica quando o dono volta ao terminal uma hora depois.
BARRA="$(cd "$(dirname "$0")" && pwd)/statusline-motor.sh"
HUD="$TMP/hud-falso.sh"
cat > "$HUD" <<'EOF'
#!/bin/sh
cat > /dev/null
printf '  projeto | main | 42%%'
EOF
chmod +x "$HUD"
HUD_CRU=$(printf '' | sh "$HUD")

barra() { # $1 = session_id
  printf '{"session_id":"%s","workspace":{"current_dir":"/projeto/exemplo"}}' "$1" \
    | CLAUDE_CONFIG_DIR="$CFG" TMPDIR="$TMP" sh "$BARRA" "sh $HUD" 2>/dev/null
}

# sem motor vivo (não há ativo-<sid>): a barra é EXATAMENTE a do renderizador
OUT=$(barra sem-motor)
check "sem motor vivo a linha não sai — a barra fica idêntica ao hud" \
  "$([ "$OUT" = "$HUD_CRU" ] && echo 1 || echo 0)" "saiu: [$OUT] esperado: [$HUD_CRU]"

# com motor vivo: a linha do motor sai ACIMA, e o hud continua byte a byte
python3 -c 'import os,sys,time; p=sys.argv[1]; open(p,"w").close(); os.utime(p,(time.time()-600,time.time()-600))' "$CFG/sovai/ativo-sess-teste"
sinal_ha 70
OUT=$(barra sess-teste)
PRIMEIRA=$(printf '%s' "$OUT" | head -1)
RESTO=$(printf '%s' "$OUT" | tail -n +2)
check "com motor vivo a PRIMEIRA linha é a do motor (acima do hud)" \
  "$(printf '%s' "$PRIMEIRA" | grep -q '^sovai · missão há' && echo 1 || echo 0)" "saiu: [$PRIMEIRA]"
check "a linha vem do estado em disco (a idade da missão)" \
  "$(printf '%s' "$PRIMEIRA" | grep -q 'missão há 10min' && echo 1 || echo 0)" "saiu: [$PRIMEIRA]"
check "a linha traz o silêncio lido do sinal em disco" \
  "$(printf '%s' "$PRIMEIRA" | grep -q 'último sinal há 70s' && echo 1 || echo 0)" "saiu: [$PRIMEIRA]"
check "o hud continua idêntico embaixo da linha do motor" \
  "$([ "$RESTO" = "$HUD_CRU" ] && echo 1 || echo 0)" "saiu: [$RESTO] esperado: [$HUD_CRU]"

# 4c-bis · O CRITÉRIO DE F9.24 NA BARRA: o mesmo silêncio de 20 min sai como
#          'rodando há N min' quando há comando de pé, e como travamento quando
#          não há. O que muda entre os dois cenários é UM arquivo — o de trabalho
#          vivo, que o hook escreve ao disparar e apaga ao voltar.
trabalho_ha() { python3 -c 'import time,sys; open(sys.argv[1],"w").write(str(time.time()-float(sys.argv[2])))' "$CFG/sovai/trabalho-sess-teste" "$1"; }

rm -f "$CFG/sovai/trabalho-sess-teste"
sinal_ha 1200
BARRA_TRAVADA=$(barra sess-teste | head -1)
check "silêncio longo SEM trabalho vivo sai na barra como SEM SINAL" \
  "$(printf '%s' "$BARRA_TRAVADA" | grep -q 'SEM SINAL' && echo 1 || echo 0)" "saiu: [$BARRA_TRAVADA]"

# o hook DE VERDADE, em modo marca, é quem deixa o trabalho vivo em disco
rm -f "$TMP/sovai-andamento-sess-teste"
CLAUDE_CONFIG_DIR="$CFG" TMPDIR="$TMP" sh "$HOOK" marca <<< "$(paylo 'bash suite-longa.sh' '')" >/dev/null 2>&1
check "o disparo grava o trabalho vivo onde a BARRA lê (fora do /tmp da sessão)" \
  "$([ -s "$CFG/sovai/trabalho-sess-teste" ] && echo 1 || echo 0)"

# 4c-ter · F9.26 — O RELÓGIO E A ESTIMATIVA CHEGAM À BARRA, alimentados por QUEM
#           EXECUTA. A barra é desenhada por outro processo e não sabe qual comando
#           está de pé nem em que projeto: quem sabe é o disparo, e é por isso que
#           ele grava o comando e o projeto junto do instante.
check "o disparo grava o COMANDO junto do instante" \
  "$([ "$(sed -n 2p "$CFG/sovai/trabalho-sess-teste")" = 'bash suite-longa.sh' ] && echo 1 || echo 0)" \
  "saiu: [$(sed -n 2p "$CFG/sovai/trabalho-sess-teste")]"
check "o disparo grava o PROJETO, sem o qual não há estimativa" \
  "$([ "$(sed -n 3p "$CFG/sovai/trabalho-sess-teste")" = '/projeto/exemplo' ] && echo 1 || echo 0)" \
  "saiu: [$(sed -n 3p "$CFG/sovai/trabalho-sess-teste")]"

BARRA_EST=$(barra sess-teste | head -1)
check "a barra traz o tempo decorrido da ferramenta de pé" \
  "$(printf '%s' "$BARRA_EST" | grep -q 'ferramenta há' && echo 1 || echo 0)" "saiu: [$BARRA_EST]"
# este comando já rodou nesta suíte (seções acima), então a memória do projeto existe
check "com histórico, a barra traz a estimativa ao lado do relógio" \
  "$(printf '%s' "$BARRA_EST" | grep -q 'ferramenta há .*usual ~' && echo 1 || echo 0)" "saiu: [$BARRA_EST]"

# comando que nunca rodou aqui chega SEM número: relógio sozinho é honesto.
CLAUDE_CONFIG_DIR="$CFG" TMPDIR="$TMP" sh "$HOOK" marca <<< "$(paylo 'bash suite-inedita.sh' '')" >/dev/null 2>&1
BARRA_NOVA=$(barra sess-teste | head -1)
check "comando sem histórico neste projeto chega à barra sem número" \
  "$(printf '%s' "$BARRA_NOVA" | grep -q 'usual ~' && echo 0 || echo 1)" "saiu: [$BARRA_NOVA]"

trabalho_ha 1200
BARRA_VIVA=$(barra sess-teste | head -1)
check "demora legítima sai na barra como 'rodando há N min'" \
  "$(printf '%s' "$BARRA_VIVA" | grep -q 'rodando há 20 min' && echo 1 || echo 0)" "saiu: [$BARRA_VIVA]"
check "demora legítima NÃO sai na barra como SEM SINAL" \
  "$(printf '%s' "$BARRA_VIVA" | grep -q 'SEM SINAL' && echo 0 || echo 1)" "saiu: [$BARRA_VIVA]"
check "as duas barras são textos diferentes" \
  "$([ "$BARRA_VIVA" != "$BARRA_TRAVADA" ] && echo 1 || echo 0)" "iguais: [$BARRA_VIVA]"

# comando de pé há 3s não explica um silêncio de 20 min
trabalho_ha 3
BARRA_CURTA=$(barra sess-teste | head -1)
check "trabalho recente demais não vira álibi do silêncio longo na barra" \
  "$(printf '%s' "$BARRA_CURTA" | grep -q 'SEM SINAL' && echo 1 || echo 0)" "saiu: [$BARRA_CURTA]"

# o comando VOLTOU: o hook apaga o trabalho vivo, e a barra deixa de dizer 'rodando'
trabalho_ha 1200
marca_ha 1200
roda 'bash suite-longa.sh' "$SAIDA_COM_PLACAR" >/dev/null
check "voltando o comando, o trabalho vivo é apagado" \
  "$([ ! -f "$CFG/sovai/trabalho-sess-teste" ] && echo 1 || echo 0)"
sinal_ha 1200
BARRA_DEPOIS=$(barra sess-teste | head -1)
check "sem comando de pé a barra volta a chamar o silêncio de SEM SINAL" \
  "$(printf '%s' "$BARRA_DEPOIS" | grep -q 'SEM SINAL' && echo 1 || echo 0)" "saiu: [$BARRA_DEPOIS]"
rm -f "$CFG/sovai/sinal-sess-teste" "$CFG/sovai/trabalho-sess-teste"

# apagar o sinal da missão (o `rm` da entrega) faz a linha sumir na hora
rm -f "$CFG/sovai/ativo-sess-teste"
OUT=$(barra sess-teste)
check "apagado o sinal da missão, a linha some e a barra volta ao hud" \
  "$([ "$OUT" = "$HUD_CRU" ] && echo 1 || echo 0)" "saiu: [$OUT]"

: > "$CFG/sovai/ativo-sess-teste"
OUT=$(printf '{"session_id":"sess-teste"}' \
  | CLAUDE_CONFIG_DIR="$CFG" TMPDIR="$TMP" SOVAI_STATUSLINE=0 sh "$BARRA" "sh $HUD" 2>/dev/null)
check "SOVAI_STATUSLINE=0 desliga a linha sem desligar a barra" \
  "$([ "$OUT" = "$HUD_CRU" ] && echo 1 || echo 0)" "saiu: [$OUT]"
rm -f "$CFG/sovai/sinal-sess-teste"

# 4d · anti-tautologia da barra: sabotar a ORDEM (linha depois do hud) tem que
#      reprovar o teste do "acima".
SAB_BARRA="$TMP/statusline-sabotada.sh"
# O leitor de JSON viaja junto: sem ele ao lado, a cópia sabotada sairia muda por
# falta de dependência e o teste abaixo passaria por engano.
cp "$(dirname "$BARRA")/hook-json.sh" "$TMP/hook-json.sh"
python3 - "$BARRA" "$SAB_BARRA" <<'EOF'
import sys
alvo, destino = sys.argv[1], sys.argv[2]
texto = open(alvo, encoding="utf-8").read()
antes = '''  [ -n "$LINHA" ] && printf '%s\\n' "$LINHA"'''
assert antes in texto, "a linha que imprime o motor mudou de forma — atualize a sabotagem"
texto = texto.replace(antes, '  DEPOIS="$LINHA"')
# O `exit 0` FINAL mataria o rabo sabotado: só ele sai (os de dentro do `if` ficam,
# senão o bloco vira `then` vazio e o script inteiro morre calado).
linhas = texto.rstrip().splitlines()
assert linhas[-1].strip() == "exit 0", "o fim do script mudou — atualize a sabotagem"
linhas.pop()
linhas.append('[ -n "$DEPOIS" ] && printf \'\\n%s\' "$DEPOIS"')
open(destino, "w", encoding="utf-8").write("\n".join(linhas) + "\n")
EOF
: > "$CFG/sovai/ativo-sess-teste"
OUT=$(printf '{"session_id":"sess-teste"}' \
  | CLAUDE_CONFIG_DIR="$CFG" TMPDIR="$TMP" \
    CLAUDE_PLUGIN_ROOT="$(cd "$(dirname "$BARRA")/.." && pwd)" \
    sh "$SAB_BARRA" "sh $HUD" 2>/dev/null)
check "barra sabotada (linha ABAIXO do hud) reprova o critério do 'acima'" \
  "$(printf '%s' "$OUT" | head -1 | grep -q '^sovai · missão há' && echo 0 || echo 1)" \
  "a sabotada ainda saiu por cima — o teste do 'acima' é tautológico · saiu: [$OUT]"
check "a sabotada ainda IMPRIME a linha — o que mudou foi só a ordem" \
  "$(printf '%s' "$OUT" | grep -q 'sovai · missão há' && echo 1 || echo 0)" \
  "a sabotagem apagou a linha em vez de movê-la — o teste acima passa por engano · saiu: [$OUT]"
rm -f "$CFG/sovai/ativo-sess-teste"
: > "$CFG/sovai/ativo-sess-teste"

# 4e · quem prova que este elo está LIGADO no caminho do produto é a suíte do
#      bootstrap, que é dona da receita da statusLine (`config/settings-defaults.json`)
#      — olhar o arquivo de outro plugin daqui seria o acoplamento que o Artigo 9 recusa.

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
