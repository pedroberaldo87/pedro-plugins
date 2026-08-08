#!/bin/bash
# sessionstart-deps.sh — avisa (systemMessage de topo, 1x/sessão) quando uma dependência
# de hook falta (jq/python3). Antes: fail-open mudo — o plugin fica 'enabled'
# sem proteger nada e ninguém sabe (issue 5). Avisar fecha o furo.
# Kill-switch: BOOTSTRAP_DEPS_GATE=0.
#
# ⚠️ Fonte da verdade: `_shared/sessionstart-deps.sh`, vendorada por
# `scripts/sync-shared.sh` numa cópia só — `plugins/bootstrap/hooks/`. Os outros  (acopla-ok: prosa que descreve o vendoring, não caminho executado)
# doze plugins que avisam NÃO carregam cópia: o hooks.json deles acha esta aqui
# por NOME de plugin (`resolve-plugin.sh bootstrap hooks/sessionstart-deps.sh`).
# O aviso continua saindo uma vez por sessão — o sentinel abaixo é o que garante.
[ "${BOOTSTRAP_DEPS_GATE:-1}" = "0" ] && exit 0

# O payload chega em stdin; ler antes de qualquer coisa evita ficar preso nele.
# `read` do próprio shell, não `cat`: aqui pode faltar até o PATH de ferramenta.
IFS= read -r -d '' ENTRADA 2>/dev/null || true

FALTAM=""
command -v jq >/dev/null 2>&1 || FALTAM="jq"
# python3 só conta como presente se EXECUTA — o stub da Microsoft Store existe
# mas não roda, e o aviso precisa pegá-lo (issue 1).
if ! { command -v python3 >/dev/null 2>&1 && python3 --version >/dev/null 2>&1; }; then
  FALTAM="${FALTAM:+$FALTAM e }python3"
fi
[ -z "$FALTAM" ] && exit 0

# Um aviso por sessão, não um por plugin instalado: o primeiro a rodar marca o
# sentinel e fala; os outros saem calados. Recorte do session_id só com expansão
# do shell (nada de jq, sed ou tr) — as ferramentas são justamente o que falta.
SID=""
case "$ENTRADA" in
  *'"session_id"'*)
    SID="${ENTRADA#*\"session_id\"}"   # o que vem depois da chave
    SID="${SID#*\"}"                   # pula até a aspa que abre o valor
    SID="${SID%%\"*}"                  # até a aspa que fecha
    ;;
esac
# Sem session_id no payload, o PPID é a chave: separa sessões sem calar o aviso.
[ -n "$SID" ] || SID="sem-id-$PPID"
# O valor vem do harness, mas a chave não pode virar caminho: qualquer caractere
# fora do conjunto de nome de arquivo descarta o id e cai no PPID.
case "$SID" in *[!A-Za-z0-9._-]*) SID="sem-id-$PPID" ;; esac
SENTINELA="${TMPDIR:-/tmp}/claude-deps-aviso-$SID"
# `noclobber` é o cria-se-não-existe atômico do próprio shell (os SessionStart
# podem correr juntos). Falhar sem o arquivo existir — /tmp somente leitura — é
# motivo para FALAR, nunca para calar.
set -C
if ! { : > "$SENTINELA"; } 2>/dev/null && [ -e "$SENTINELA" ]; then
  exit 0
fi
set +C

# JSON do SessionStart montado sem jq/python3 — eles podem ser justamente o que falta.
# A dica de instalação ramifica pela dependência que falta: só jq → brew/choco;
# só python3 → interpretador real (o stub da Store não executa).
case "$FALTAM" in
  jq) DICA="macOS: brew install jq · Windows: choco install jq" ;;
  python3) DICA="macOS: python.org ou brew install python3 · Windows: winget install Python.Python (o da Store não executa)" ;;
  *) DICA="macOS: brew install jq python3 · Windows: choco install jq e winget install Python.Python" ;;
esac
MSG="⚠️ Dependência ausente: ${FALTAM} — hook do marketplace fica mudo
• O plugin segue 'enabled' e não protege nada — instale antes de confiar nos gates
• Instalar: ${DICA}
• Desligar: BOOTSTRAP_DEPS_GATE=0"

# Uma linha = um bullet (é o contrato da régua, perfil `hook`); no JSON cada
# quebra vira o escape \n literal, porque montar isso com jq/python3 é o que
# justamente pode faltar aqui.
MSG_JSON="${MSG//$'\n'/\\n}"
# `systemMessage` no TOPO é o canal que o harness mostra ao humano — dentro de
# hookSpecificOutput ele é ignorado. O additionalContext leva o mesmo texto ao modelo.
printf '{"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}' "$MSG_JSON" "$MSG_JSON"
echo
exit 0
