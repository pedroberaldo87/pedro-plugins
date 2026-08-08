#!/bin/bash
# resolve-skill.sh — descobre COMO invocar uma skill, dado só o nome dela.
#
# O DEFEITO QUE ELE MATA. Uma skill é invocada por `<plugin>:<skill>`, então o nome de
# invocação carrega o plugin dentro dele. Quando a skill muda de plugin — o que este
# repositório fez com sete delas no F14.2 —, todo lugar que escreveu o nome completo à
# mão passa a pedir uma skill que não existe, e o pedido falha **em silêncio**: o agente
# recebe um nome inválido e segue.
#
# Medido em 2026-08-08: o motor de execução contínua pedia `project-doc:doc-touch` desde
# que a skill mudou para `project-skills`. Quatro ondas fecharam verdes e NENHUMA
# produziu documentação — `git log --grep 'sovai: onda'` mostra zero doc em três delas, e
# na quarta o único arquivo era um doc autoral que a skill nem pode tocar.
#
# É o irmão do `resolve-plugin.sh`, na outra direção: aquele acha o ARQUIVO dado o
# plugin; este acha o PLUGIN dado a skill.
#
# Uso:   resolve-skill.sh <nome-da-skill>
#        ex.: resolve-skill.sh doc-touch  →  project-skills:doc-touch
# Saída: `<plugin>:<skill>` no stdout e código 0 quando existe;
#        NADA no stdout e código 3 quando nenhuma versão ativa a serve.
#
# Ausência não é erro — mesmo contrato do `resolve-plugin.sh`: stdout é o dado, `$?` é o
# sinal, e quem chama testa a saída vazia e segue.
#
# ⚠️ SÓ A VERSÃO MAIS ALTA DE CADA PLUGIN CONTA. O cache guarda todas as versões já
# instaladas, e as antigas do `project-doc` ainda trazem `skills/doc-touch/` — procurar
# em qualquer versão devolveria os DOIS plugins, e o nome velho voltaria a ser escolhido.
# A versão mais alta é a que o harness carrega, e é a única que responde de verdade.

SKILL="${1:?uso: resolve-skill.sh <nome-da-skill>}"
CACHE="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/cache"

for plugdir in "$CACHE"/*/*/; do
  [ -d "$plugdir" ] || continue
  # a versão ativa é a mais alta que existe no disco (mesma regra do resolve-plugin.sh)
  ativa=$(ls -d "$plugdir"*/ 2>/dev/null | sort -V | tail -1)
  [ -n "$ativa" ] || continue
  if [ -f "$ativa/skills/$SKILL/SKILL.md" ]; then
    plugin=$(basename "${plugdir%/}")
    printf '%s:%s\n' "$plugin" "$SKILL"
    exit 0
  fi
done

exit 3
