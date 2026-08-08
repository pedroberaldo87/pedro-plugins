#!/bin/sh
# posttooluse-andamento.sh — o andamento de cada comando longo, escrito na tela
# principal.
#
# Por que existe: `lib/andamento.py` sabia montar a linha (relógio, estimativa
# pela memória do próprio comando, placar da suíte e se ela andou) e ninguém a
# chamava — o dono ausente continuava sem saber se a missão está rodando uma
# suíte de 11 minutos ou travada. Peça sem chamador é peça que não existe.
#
# Dois momentos, um arquivo só, porque a duração precisa dos dois:
#
#   marca (PreToolUse em Bash)   — grava o instante do disparo e sai calado.
#   narra (PostToolUse em Bash)  — mede o decorrido REAL contra aquela marca,
#                                  guarda na memória do projeto e IMPRIME.
#
# Sem a marca não há duração medida, e aí a linha não sai: número de duração
# sem lastro é pior que silêncio.
#
# ONDE A LINHA SAI: `systemMessage` — o canal que o dono LÊ. O `stderr` de hook
# é descartado por quem chama (é o defeito que a checagem M do release-gate
# persegue), e um aviso que ninguém lê é um aviso que não existe.
#
# ESCOPO: só DENTRO de uma missão do /sovai (o mesmo sinal `ativo-<sid>` que os
# gates vizinhos consultam). Fora dela o dono está na frente do terminal e vê a
# saída do próprio comando; narrar ali seria só ruído.
#
# FAIL-OPEN em toda borda de infra: narrador que atrapalha é pior que narrador
# nenhum.

# Kill-switch (contrato dos hooks deste repo).
[ "${SOVAI_ANDAMENTO:-1}" = "0" ] && exit 0

HJ_DIR="${0%/*}"; [ "$HJ_DIR" = "$0" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
# shellcheck source=/dev/null
. "$HJ_DIR/lib-tmpdir.sh" 2>/dev/null
# Sem como IMPRIMIR não há o que narrar.
type hj_msg >/dev/null 2>&1 || exit 0
type td_tmpdir >/dev/null 2>&1 || exit 0
# O motor da linha é python (stdlib); sem ele não há linha a montar. Mas sair
# CALADO é o defeito que o hook-json existe para corrigir: quem não conseguiu
# ler o evento avisa que não leu, em vez de parecer que nada estava rodando.
PY=$(hj_py) || { hj_avisa "posttooluse-andamento"; exit 0; }

RAIZ="${CLAUDE_PLUGIN_ROOT:-$(cd "$HJ_DIR/.." && pwd)}"

INPUT=$(cat 2>/dev/null)
SESSION=$(hj_campo "$INPUT" session_id)
# Estado por-sessão em /tmp é chaveado por session_id: sessão paralela não pode
# herdar a marca da outra.
[ -n "$SESSION" ] || exit 0
MARCA="$(td_tmpdir)/sovai-andamento-$SESSION"
# O mesmo disparo, gravado onde a BARRA consegue ler: ela é desenhada por outro
# processo, que não enxerga o /tmp desta sessão. Existir = tem comando de pé;
# o instante lá dentro é o que separa "rodando há 20 min" de travamento.
# A casa do estado é NEUTRA: quatro plugins chamam o mesmo módulo, e a pasta com o
# nome de um deles fazia o estado dos outros parecer emprestado. O que NASCE vai
# pra `andamento/`; a pasta antiga só é LIDA, pra missão viva não perder o que já
# tinha.
ESTADO="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/andamento"
ESTADO_ANTIGO="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sovai"
mkdir -p "$ESTADO" 2>/dev/null
TRABALHO="$ESTADO/trabalho-$SESSION"

if [ "$1" = "marca" ]; then
  date +%s > "$MARCA" 2>/dev/null
  # Três linhas: o instante, o COMANDO e o PROJETO. As duas últimas são o que
  # deixa a barra chamar `estimativa()` — ela só responde por comando E projeto,
  # e a barra é desenhada por outro processo, que não tem como saber nenhum dos
  # dois. Quebra de linha vira espaço: o arquivo é lido por linha.
  {
    date +%s
    hj_campo "$INPUT" tool_input.command | tr '\n' ' ' | sed 's/ *$//'
    printf '\n%s\n' "$(hj_campo "$INPUT" cwd)"
  } > "$TRABALHO" 2>/dev/null
  exit 0
fi

# O comando VOLTOU: não há mais trabalho de pé. Apagar antes de qualquer saída
# antecipada — deixar o arquivo aí faria a barra dizer "rodando" para sempre.
# Nos DOIS caminhos: registro que ficou na pasta antiga faria a barra dizer
# "rodando" para sempre.
rm -f "$TRABALHO" "$ESTADO_ANTIGO/trabalho-$SESSION" 2>/dev/null

# Estado mutável mora fora do plugin: ${CLAUDE_PLUGIN_ROOT} é cache reescrito a
# cada bump de versão. Missão acesa na pasta antiga continua valendo.
[ -f "$ESTADO/ativo-$SESSION" ] || [ -f "$ESTADO_ANTIGO/ativo-$SESSION" ] || exit 0
[ -f "$MARCA" ] || exit 0

# O sinal de vida da missão: o instante em que o narrador falou pela última vez.
# É contra ele que se mede o silêncio, e é o silêncio que separa demora de
# travamento. Mora fora do plugin, junto do resto do estado da missão.
SINAL="$ESTADO/sinal-$SESSION"
# Missão que já estava de pé quando a pasta mudou: o sinal dela veio da casa
# antiga, e sem trazê-lo o silêncio acumulado seria zerado sem ter passado.
[ -f "$SINAL" ] || [ ! -f "$ESTADO_ANTIGO/sinal-$SESSION" ] \
  || cp "$ESTADO_ANTIGO/sinal-$SESSION" "$SINAL" 2>/dev/null

LINHA=$(printf '%s' "$INPUT" | "$PY" -c '
import json, os, sys, time

raiz, marca, sinal, sessao = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
sys.path.insert(0, os.path.join(raiz, "lib"))
import andamento

try:
    evento = json.loads(sys.stdin.read() or "{}")
except ValueError:
    raise SystemExit
comando = (evento.get("tool_input") or {}).get("command") or ""
if not comando:
    raise SystemExit
projeto = evento.get("cwd") or os.getcwd()

# A saída CRUA, que é de onde o placar sai. O harness entrega ora texto, ora um
# objeto com stdout/stderr — juntar as partes preserva as quebras de linha, que
# é o que `placar()` varre.
resposta = evento.get("tool_response")
if isinstance(resposta, dict):
    saida = "\n".join(str(resposta.get(k) or "")
                      for k in ("stdout", "stderr", "output", "content"))
else:
    saida = str(resposta or "")

try:
    with open(marca, encoding="utf-8") as fh:
        inicio = float(fh.read().strip())
except (OSError, ValueError):
    raise SystemExit
decorrido = time.time() - inicio
if decorrido < 0:
    raise SystemExit

# O PLACAR DA ONDA ANTERIOR (F9.27). Ele morava aqui no /tmp, e por isso só esta
# tela o enxergava — a barra é desenhada por outro processo. Agora o registro é um
# só, no estado da missão, e os dois leem dele.
anterior = andamento.ultimo_placar(sessao)

# A linha ANTES de registrar: a estimativa tem que vir das vezes anteriores,
# não desta.
linha = andamento.linha_andamento(comando, projeto, decorrido, saida, anterior)
andamento.registrar(projeto, comando, decorrido)

# Comando que imprimiu placar é a suíte de uma onda fechando: o placar dela vira o
# termo de comparação da onda seguinte, e chega à barra. Comando sem placar não é
# fim de onda e não escreve nada.
andamento.onda(sessao, saida)

# O SILÊNCIO desde a última vez que o narrador falou. Trabalho vivo é o próprio
# comando que acabou de rodar: se ELE ocupou o silêncio inteiro, a missão estava
# trabalhando — demora, não travamento. Se o silêncio é longo e o comando foi
# curto, ninguém estava trabalhando naquele tempo, e aí a palavra é travamento.
agora = time.time()
try:
    with open(sinal, encoding="utf-8") as fh:
        mudo = agora - float(fh.read().strip())
except (OSError, ValueError):
    mudo = None
silencio = andamento.linha_silencio(mudo, decorrido >= andamento.LIMITE_SILENCIO)
try:
    with open(sinal, "w", encoding="utf-8") as fh:
        fh.write(str(agora))
except OSError:
    pass

sys.stdout.write("\n".join(x for x in (linha, silencio) if x))
' "$RAIZ" "$MARCA" "$SINAL" "$SESSION" 2>/dev/null)

# A marca vale para UM comando: deixá-la de pé faria o próximo comando herdar
# uma duração que não é dele.
rm -f "$MARCA" 2>/dev/null

[ -n "$LINHA" ] || exit 0
hj_msg "⏱ $LINHA"
exit 0
