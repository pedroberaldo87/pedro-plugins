#!/usr/bin/env bash
# sessionstart-avisa-privado.sh — uma linha, no começo da sessão, com o estado do privado.
#
# Esquecer o privado sujo entre sessões é o defeito: a documentação fica escrita só neste
# disco, e a próxima máquina (ou o projeto estacionado) não a tem. A linha diz quantos
# arquivos de .claude/ estão sem commit e quantos commits estão sem push.
#
# Não busca o remoto (sem rede no começo da sessão); conta contra o que o disco sabe.
#   canal      systemMessage (você vê) + additionalContext (o agente lê) — informa, nunca bloqueia
#   desligar   DEVGIT_AVISO=0
#   fail-open  fora de repositório, projeto sem privado, git quebrado → exit 0 calado
[ "${DEVGIT_AVISO:-1}" = "0" ] && exit 0
# O harness roda o hook na pasta da sessão: o payload não traz nada que decida aqui.
cat >/dev/null 2>&1
DEVGIT="$(cd "$(dirname "$0")/../bin" && pwd)/devgit"

sujos=$("$DEVGIT" status --porcelain -- . 2>/dev/null) || exit 0
n=$(printf '%s' "$sujos" | grep -c .)
if "$DEVGIT" rev-parse -q --verify '@{u}' >/dev/null 2>&1; then
  p=$("$DEVGIT" rev-list --count '@{u}..HEAD' 2>/dev/null) || exit 0
  envio="$p commit(s) sem push"
else
  p=1; envio="sem remoto ligado"
fi
if [ "$n" -eq 0 ] && [ "$p" -eq 0 ]; then
  msg="devgit: privado em dia (0 arquivo(s) sem commit, 0 commit(s) sem push)"
else
  msg="devgit: privado com $n arquivo(s) sem commit e $envio — feche com: devgit fechar \\\"docs: ...\\\""
fi
printf '{"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$msg" "$msg"
exit 0
