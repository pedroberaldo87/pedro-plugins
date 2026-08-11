#!/usr/bin/env bash
# cache-parado.sh — as versões que ficaram no disco depois de um `claude plugin`.
#
# POR QUE EXISTE: o cache é chaveado por versão
# (`~/.claude/plugins/cache/<marketplace>/<plugin>/<versão>/`) e o repositório exige
# bump em TODA mudança — é o número que faz o cliente receber a atualização. Junte os
# dois e cada instalação deixa a pasta anterior no disco, para sempre. Nenhum comando
# do Claude Code limpa isso: `plugin update` só acrescenta.
#
# O CUSTO MEDIDO, e ele não é de espaço: em 2026-08-08 uma skill foi movida de plugin,
# o repositório ficou certo, e a MÁQUINA continuou rodando a versão errada — porque a
# errada era a mais alta do disco. O comando apareceu duas vezes e ninguém sabia por quê.
#
# Duas funções, e a segunda nunca roda sozinha:
#
#   cp_parados          conta e lista o que sobrou (só lê)
#   cp_limpar           apaga tudo que não é a versão mais alta (destrói)
#
# FAIL-OPEN em toda borda: sem cache, sem python3, sem nada — devolve zero e cala.

CP_CACHE="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/cache"

# Devolve uma linha por plugin com sobra:  <marketplace>/<plugin> <roda> <n> <paradas…>
cp_parados() {
  [ -d "$CP_CACHE" ] || return 0
  command -v python3 >/dev/null 2>&1 || return 0
  python3 - "$CP_CACHE" <<'PY' 2>/dev/null
import os, re, sys
cache = sys.argv[1]

def ver(t):
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.\-]", t)[:4])

for market in sorted(os.listdir(cache)):
    dm = os.path.join(cache, market)
    if not os.path.isdir(dm):
        continue
    for plug in sorted(os.listdir(dm)):
        dp = os.path.join(dm, plug)
        if not os.path.isdir(dp):
            continue
        vs = sorted((v for v in os.listdir(dp) if os.path.isdir(os.path.join(dp, v))),
                    key=ver)
        # `.in_use` e afins não são versão: entram na lista e seriam apagados.
        vs = [v for v in vs if not v.startswith(".")]
        if len(vs) > 1:
            print("%s/%s %s %d %s" % (market, plug, vs[-1], len(vs) - 1,
                                      " ".join(vs[:-1])))
PY
}

# Quantas versões paradas existem no total. Vazio conta como 0.
cp_total() {
  cp_parados | awk '{s+=$3} END {print s+0}'
}

# Apaga o que não é a versão mais alta. NUNCA é chamado por hook: quem chama é o
# dono, depois de ver a lista. Imprime cada pasta removida — apagar calado é o
# defeito que a lista existe para evitar.
cp_limpar() {
  local linha market_plug roda n paradas v alvo
  cp_parados | while read -r market_plug roda n paradas; do
    for v in $paradas; do
      alvo="$CP_CACHE/$market_plug/$v"
      [ -d "$alvo" ] || continue
      # Apagar CALADO é o defeito que a lista existe para evitar — e falhar calado
      # é o mesmo defeito virado do avesso. O `rm -rf` pode não remover (pasta em
      # uso, permissão, sistema de arquivos que segura o descritor), e até aqui a
      # única pista era o teste dizendo que a versão velha continuava lá, sem uma
      # linha explicando por quê. Agora quem não apagou diz que não apagou.
      if rm -rf "$alvo" 2>/dev/null && [ ! -d "$alvo" ]; then
        echo "apagado: $market_plug/$v"
      else
        echo "NÃO apagado (segue no disco): $market_plug/$v" >&2
      fi
    done
  done
}
