#!/bin/bash
# stop-plan-status.sh — "onde nós estamos", ao fim de cada turno.
#
# Emite 1-3 bullets curtos com o progresso do plano ativo, e — quando tudo
# fechou — uma confirmação INEQUÍVOCA de conclusão. O texto NÃO mora aqui:
# vem de `plan_state.py brief`, porque texto em heredoc de shell não é testável
# e este mesmo texto precisa servir pro hook e pra quem chamar na mão.
#
# Dobra também a cobrança do tique (era o stop-plan-nudge.sh): quando a sessão
# escreveu código e não marcou nada, entra UM bullet a mais, 1× por sessão.
# Um hook só em vez de dois — dois `systemMessage` no mesmo Stop competiriam.
#
# CONTRATO DE GATE (patterns.md, na casa da doc, → §5.3):
#   canal      systemMessage (informa, não bloqueia — nunca emite decision:block)
#   cap        n/a (não bloqueia); a COBRANÇA é 1× por (sessão, projeto)
#   desligar   PLAN_STATUS=0  (e PLAN_NUDGE=0 desliga as duas cobranças)
#   fail-open  sem jq, sem python3, sem transcript → exit 0 calado
#
# Sem plano ativo o silêncio continua sendo o normal — com UMA exceção: se a
# sessão editou 3+ arquivos distintos e não há plano nenhum aberto, isso é dito
# uma vez (ver "plano AUSENTE" no fim do arquivo).

[ "${PLAN_STATUS:-1}" = "0" ] && exit 0
# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# Sem os dois o gate não julga — e aí ele AVISA, nunca sai calado (issue #5).
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_SELF="$(printf '%s' "$0" | tr '\\' /)"   # \ -> / : no Windows $0 vem com barra invertida
HJ_DIR="${HJ_SELF%/*}"; [ "$HJ_DIR" = "$HJ_SELF" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
type hj_campo >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "stop-plan-status"; exit 0; }
PY3=$(command -v python3 2>/dev/null)
"$PY3" --version >/dev/null 2>&1 || exit 0
[ -z "$PY3" ] && exit 0

INPUT=$(cat 2>/dev/null)
# Stop disparado por stop_hook já ativo → sai (anti-loop).
ACTIVE=$(hj_campo "$INPUT" stop_hook_active)
[ "$ACTIVE" = "true" ] && exit 0

SESSION=$(hj_campo_ou "$INPUT" session_id "")
# payload sem sessão: liberado — o sentinela "unknown" seria compartilhado entre sessões (o defeito do context-guard v1.1)
[ -n "$SESSION" ] || exit 0
TRANSCRIPT=$(hj_campo "$INPUT" transcript_path)
CWD=$(hj_campo "$INPUT" cwd)
[ -z "$CWD" ] && CWD="$PWD"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# O programa do plano mora no plugin `project-skills` — achado pelo NOME, nunca
# por caminho relativo, que o cache do harness quebra. Ausente = sai calado.
PLAN_STATE=$(CLAUDE_PLUGIN_ROOT="$SCRIPT_DIR/.." bash "$SCRIPT_DIR/resolve-plugin.sh" project-skills lib/plan_state.py 2>/dev/null)
[ -n "$PLAN_STATE" ] || exit 0

# `$?` = 3 → o diretório veio da RESERVA (~/Desktop), não deste projeto. O texto
# do aviso morre no 2>/dev/null desta linha; o código de saída é o que sobrevive.
PLANS_DIR=$(bash "$SCRIPT_DIR/../lib/resolve-dir.sh" "$CWD" plans 2>/dev/null); DE_RESERVA=$?
[ -d "$PLANS_DIR" ] || exit 0
RESERVA_AVISO=""
[ "$DE_RESERVA" = "3" ] && RESERVA_AVISO="⚠️ Este resumo é da RESERVA ($PLANS_DIR), não deste diretório — '$CWD' não tem marcador de projeto."

# A régua do canal (perfil `hook` de `lib/regua_texto.py`, vinda de quality-goals.md):
# sem markdown, cabeçalho com emoji, uma ideia por linha, 6 linhas de orçamento. São
# DOIS textos saindo daqui (o resumo e o aviso de plano ausente), por isso a função.
# Defeito de forma não cala um aviso: o motivo vai pro stderr (debug log do harness) e
# o texto sai assim mesmo. Régua ausente → silêncio, nunca queda.
REGUA="$SCRIPT_DIR/../lib/regua_texto.py"
regua_hook() {   # $1 = texto, $2 = rótulo
  [ -f "$REGUA" ] && printf '%s\n' "$1" | "$PY3" "$REGUA" --perfil hook --onde "$2" - || :
}

PHASH=$(printf '%s' "$PLANS_DIR" | cksum | cut -d' ' -f1)
MARK="${TMPDIR:-/tmp}/claude-plan-mark-$(id -u)-${SESSION}-${PHASH}"

# O marco da sessão também data o "encerrado AGORA": plano fechado depois dele
# merece a confirmação final; fechado semanas atrás, não. Sem marco, só o ativo.
# AUTO-CURA (2026-07-28): antes, sem marco este hook perdia a confirmação de
# conclusão e a cobrança — calados pra sempre naquela sessão. Acontecia sempre
# que o plugin era instalado ou atualizado NO MEIO da sessão: o SessionStart,
# que cria o marco, já tinha passado.
#
# Regra geral que saiu daqui: hook que depende de OUTRO hook ter rodado é
# frágil. Se o pré-requisito é um arquivo barato, crie-o você mesmo.
MARCO_NOVO=0
if [ ! -f "$MARK" ]; then
  touch "$MARK" 2>/dev/null
  MARCO_NOVO=1
  # Recém-criado: tudo que fechou ANTES deste instante fica de fora desta vez,
  # e é o certo — não dá pra afirmar que fechou "nesta sessão".
fi
# MARCO_NOVO=1 → o marco nasceu AGORA, e nenhum plano pode ser posterior a ele. O
# brief usa o marco pra decidir se algum plano é DESTA sessão; com marco recém-criado
# isso não é "nenhum é", é "não dá pra saber". Passar o marco aqui faria o primeiro
# turno de toda sessão trocar o resumo pela linha de "nenhum tocado nesta sessão" —
# mesmo raciocínio que já vale pra cobrança logo abaixo.
SINCE=""
[ -f "$MARK" ] && [ "$MARCO_NOVO" = "0" ] && \
  SINCE=$("$PY3" -c "import os,sys;print(os.path.getmtime(sys.argv[1]))" "$MARK" 2>/dev/null)

# O "já confirmei o encerramento" mora por (sessão, projeto): sem isso o 🏁
# reaparecia a cada turno até a sessão acabar.
SEEN="${TMPDIR:-/tmp}/claude-plan-closed-$(id -u)-${SESSION}-${PHASH}"

# ── quantos ARQUIVOS DISTINTOS esta sessão editou ────────────────────────────
# DISTINTOS, não chamadas. Até 2026-08-02 isto era `grep '"name":"Edit"' | wc -l`,
# e a frase que ele alimenta diz "arquivos": 6 edições no MESMO arquivo
# imprimiam "editou 6 arquivos", e o piso disparava por insistência em vez de
# por tamanho do trabalho. O formato abaixo é o real do transcript (JSONL, um
# bloco `tool_use` por chamada), lido de um transcript de verdade:
#   {"message":{"content":[{"type":"tool_use","name":"Edit",
#                           "input":{"file_path":"/caminho/absoluto"}}]}}
# Mesma leitura que `handoff/lib/collect_engine.py:collect_edited_paths`.
# Fail-open: linha corrompida, arquivo ilegível ou python3 caído → 0, e 0 nunca
# alcança o piso, então o hook cala.
arquivos_editados() {
  "$PY3" - "$1" <<'PY' 2>/dev/null
import json, sys

TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
vistos = set()
try:
    with open(sys.argv[1], encoding="utf-8", errors="replace") as fh:
        for linha in fh:
            try:
                rec = json.loads(linha)
            except ValueError:
                continue          # linha truncada no meio da escrita
            msg = rec.get("message") if isinstance(rec, dict) else None
            blocos = msg.get("content") if isinstance(msg, dict) else None
            if not isinstance(blocos, list):
                continue
            for b in blocos:
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                if b.get("name") not in TOOLS:
                    continue
                inp = b.get("input") or {}
                fp = inp.get("file_path") or inp.get("notebook_path")
                if fp:
                    vistos.add(fp)
except OSError:
    pass
print(len(vistos))
PY
}

# O piso das DUAS cobranças. Um número só: dois pisos divergentes no mesmo
# arquivo viram duas réguas, e ninguém sabe qual valeu.
PISO=3

# ── a cobrança do tique ──────────────────────────────────────────────────────
# Só entra quando: há marco, nenhum *.plan.json foi tocado nesta sessão, e o
# transcript mostra 3+ arquivos editados. 1× por (sessão, projeto) — cobrar
# todo turno transforma o aviso em ruído, e ruído a gente aprende a ignorar.
NUDGE=""
# MARCO_NOVO=1 → o marco nasceu AGORA, então "nada foi marcado desde o marco"
# é verdade vazia: não houve intervalo. Cobrar aqui seria acusar sem base.
# A partir do turno seguinte há intervalo de verdade e a cobrança volta.
if [ "${PLAN_NUDGE:-1}" != "0" ] && [ "$MARCO_NOVO" = "0" ] && [ -f "$MARK" ] \
   && [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
  SENTINEL="${TMPDIR:-/tmp}/claude-plan-nudge-$(id -u)-${SESSION}-${PHASH}"
  if [ ! -f "$SENTINEL" ]; then
    TICKED=0
    for f in "$PLANS_DIR"/*.plan.json; do
      [ -e "$f" ] || continue
      [ "$f" -nt "$MARK" ] && TICKED=1 && break
    done
    if [ "$TICKED" = "0" ]; then
      FILES=$(arquivos_editados "$TRANSCRIPT")
      case "$FILES" in ''|*[!0-9]*) FILES=0 ;; esac
      if [ "$FILES" -ge "$PISO" ]; then
        touch "$SENTINEL" 2>/dev/null
        NUDGE="⚠️ Nada marcado nesta sessão, que editou ${FILES} arquivos — marque o que terminou com tick <id> --evidencia, senão o plano herdado mente."
      fi
    fi
  fi
fi

# O brief compõe TUDO — inclusive a cobrança — porque o teto de 3 bullets é do
# pedido do usuário e precisa viver num lugar testável, não em concatenação aqui.
# `--sessao` é o que faz o resumo ser DESTA sessão: quem marca um passo deixa a marca,
# e o brief lê a dela em vez de adivinhar pelo arquivo mexido mais recentemente. Num
# projeto com frentes paralelas — 6 sessões abertas no mesmo repositório em 2026-08-03 —
# sem isto a sessão de uma frente recebia o progresso da frente da vizinha.
if [ -n "$SINCE" ]; then
  BRIEF=$("$PY3" "$PLAN_STATE" --dir "$PLANS_DIR" brief --closed-since "$SINCE" \
            --mark-seen "$SEEN" --sessao "$SESSION" ${NUDGE:+--nudge "$NUDGE"} 2>/dev/null)
else
  BRIEF=$("$PY3" "$PLAN_STATE" --dir "$PLANS_DIR" brief --sessao "$SESSION" \
            ${NUDGE:+--nudge "$NUDGE"} 2>/dev/null)
fi

# ── plano AUSENTE ────────────────────────────────────────────────────────────
# Sem plano ativo o `brief` devolve VAZIO — e até 2026-08-02 a linha acima
# engolia tudo, inclusive a cobrança montada lá em cima (ela é argumento do
# brief). Resultado: sessão grande sem plano nenhum passava calada; num único
# dia foram 7 commits assim, e nada acusou. O gate que exige plano só arma no
# ExitPlanMode, então quem nunca entra em plan mode nunca é cobrado.
#
# Canal próprio, mesma disciplina do resto do arquivo: systemMessage (não
# bloqueia), 1× por (sessão, projeto), kill-switch PLAN_NUDGE=0, fail-open.
# Sentinela SEPARADA da cobrança do tique: aquela já foi queimada lá em cima
# sem nada ter sido dito, e as duas cobram coisas diferentes.
if [ -z "$BRIEF" ]; then
  [ "${PLAN_NUDGE:-1}" = "0" ] && exit 0
  [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ] || exit 0
  MISSING="${TMPDIR:-/tmp}/claude-plan-missing-$(id -u)-${SESSION}-${PHASH}"
  [ -f "$MISSING" ] && exit 0

  # `open --json` imprime `[]` quando não há plano ativo. Exigir o `[]` LITERAL
  # é o que separa "não há plano" de "o motor quebrou": quebra dá saída vazia,
  # e aí o hook cala em vez de acusar plano ausente que talvez exista.
  OPEN=$("$PY3" "$PLAN_STATE" --dir "$PLANS_DIR" open --json 2>/dev/null)
  [ "$OPEN" = "[]" ] || exit 0

  # Mesma métrica e mesmo piso da cobrança do tique — o requisito fala em
  # "sessão que edita N arquivos", e ARQUIVO é o que `arquivos_editados` conta.
  ARQS=$(arquivos_editados "$TRANSCRIPT")
  case "$ARQS" in ''|*[!0-9]*) ARQS=0 ;; esac
  [ "$ARQS" -ge "$PISO" ] || exit 0

  touch "$MISSING" 2>/dev/null
  AUSENTE="⚠️ Sem plano aberto — esta sessão editou ${ARQS} arquivos
• Trabalho desse tamanho sem plano não deixa rastro: o próximo Claude não sabe o que ficou pela metade.
• Abra um com /visual (ele grava em .claude/plans/), ou siga sem — este aviso não volta nesta sessão."
  regua_hook "$AUSENTE" "aviso de plano ausente"
  hj_msg "$AUSENTE"
  exit 0
fi

# A linha em branco na FRENTE é do canal, não do texto: o harness prefixa
# "Stop says: " na primeira linha, e sem ela o cabeçalho fica grudado no prefixo, num
# nível diferente dos bullets que vêm abaixo. Com ela, o prefixo fica sozinho e o
# cabeçalho desce pro mesmo alinhamento dos três. Não entra no orçamento do Stop —
# `_linhas_visiveis` só conta linha com conteúdo.
# O aviso entra ANTES do resumo e dentro do mesmo texto: o systemMessage é o canal
# que o usuário lê de verdade, e a origem do plano muda o que o resumo significa.
[ -n "$RESERVA_AVISO" ] && BRIEF="${RESERVA_AVISO}
${BRIEF}"
regua_hook "$BRIEF" "resumo de fim de turno"
hj_msg "$(printf '\n\n%s' "$BRIEF")"
exit 0
