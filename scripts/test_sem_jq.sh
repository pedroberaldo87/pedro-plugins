#!/bin/bash
# test_sem_jq.sh — o requisito W-2: em máquina SEM `jq` o gate ainda decide.
#
# O inventário (.claude/docs/jq-pontos-de-decisao.md) separa os hooks que leem o
# payload em duas naturezas:
#   A  — o `jq` só formata a saída ou lê config → fail-open é aceitável
#   B  — o hook lê o campo que DECIDE (tool_input.command, session_id,
#        stop_hook_active). Aqui a falta do `jq` calava o gate (issue #5).
#
# Esta suíte faz três coisas:
#   1. re-deriva os conjuntos do código e compara com o que a doc afirma;
#   2. prova, arquivo a arquivo, que todo hook da classe B lê pelo `hook-json.sh`
#      (o leitor com fallback em python3) e não bail-a mais por falta de `jq`;
#   3. RODA hooks da classe B com o `jq` fora do PATH e exige que a decisão
#      aconteça — deny continua deny, allow continua allow — e que sem `jq` NEM
#      `python3` o hook AVISE em vez de sair calado.
#
# Rodar da raiz do repositório:  bash scripts/test_sem_jq.sh

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RAIZ" || exit 1
source "$RAIZ/_shared/lib-casa-da-doc.sh"
DOC=$(casa_da_doc "$RAIZ" jq-pontos-de-decisao.md)
FAIL=0

ok()   { echo "ok   $1"; }
bad()  { echo "FAIL $1"; FAIL=1; }

# `git ls-files` não serve: hook novo ainda não staged também tem que ser medido.
#
# HOOK É O QUE ESTÁ REGISTRADO em algum `hooks/hooks.json` — não é todo `.sh` que
# mora em `hooks/`. O filtro antigo tirava só as bibliotecas de `_shared/`, e por
# isso toda biblioteca que nascia DENTRO de `hooks/` entrava na conta como se fosse
# hook de produção: medido em 2026-08-08, `lib-rodada.sh` nasceu e a contagem foi de
# 48 para 49 sem nenhum hook novo existir. O retrato ficava vencido e a suíte
# vermelha, num documento autoral que ninguém pode reescrever automaticamente.
#
# O registro é a fonte da verdade porque é ele que o harness lê: `.sh` que nenhum
# `hooks.json` cita não roda em evento nenhum, seja ele vendorado ou local.
# Quem resolve o registro é o medidor oficial (`scripts/hook_contract.py`), que lê
# cada `hooks.json` e devolve o CAMINHO de cada script — comparar por nome de arquivo
# não serve, porque `lib-tmpdir.sh` existe em sete plugins e um registro num deles
# faria os outros seis passarem por registrados.
LISTA_PROD="$(python3 scripts/hook_contract.py --scripts 2>/dev/null | sort)"
# A exclusão de biblioteca vendorada era CÓDIGO MORTO: $VENDORADOS nunca era atribuído,
# e os dois grep -vE viravam regex vazia (achado do auditor de 2026-08-09). Derivado de
# _shared/, como a prosa do doc sempre prometeu.
VENDORADOS="$(ls _shared/*.sh 2>/dev/null | xargs -n1 basename | paste -sd'|' -)"
[ -n "$VENDORADOS" ] || VENDORADOS="hook-json.sh"
if [ -z "$LISTA_PROD" ]; then
  # Fail-open com aviso: sem o medidor não há como separar hook de biblioteca, e
  # medir errado é pior que não medir. O aviso impede que isso passe por "está tudo
  # certo" — a régua da casa para gate mudo.
  echo "AVISO: scripts/hook_contract.py --scripts não respondeu; o inventário não foi conferido" >&2
  exit 0
fi

# Classe B medida: linha que lê um dos três campos de decisão, fora de comentário,
# seja pelo leitor novo (`hj_campo`…) ou pelo `jq` cru de antes.
LISTA_B="$( { grep -rn -e 'jq' -e 'JQ' -e 'hj_campo' -e 'hj_eh_falso' plugins/*/hooks/*.sh 2>/dev/null \
  | grep -v '/test_' | grep -vE "/($VENDORADOS):" \
  | grep -vE '^[^:]+:[0-9]+:[[:space:]]*#' \
  | grep -E '(jq|JQ|hj_campo|hj_campo_ou|hj_eh_falso)[^#]*(tool_input\.command|session_id|stop_hook_active)' \
  | cut -d: -f1
    # A TERCEIRA forma de leitura (emenda de 2026-08-09): Python embutido no .sh, fora
    # da biblioteca comum — `data.get("session_id")` e afins. Sem esta linha o derivador
    # era cego a ela, e o hook que lê assim ficava fora do inventário sem ninguém acusar.
    # As QUATRO grafias medidas pelo auditor de 2026-08-09: com e sem default, aspas
    # simples e duplas, e o acesso por colchete — `data.get("x")` sozinho deixou o
    # sessionstart-ata.sh (que usa default) invisível na primeira medição.
    grep -rlnE 'data(\.get\(|\[)["'"'"'](session_id|prompt|stop_hook_active|transcript_path|tool_input)' plugins/*/hooks/*.sh 2>/dev/null \
  | grep -v '/test_' | grep -vE "/($VENDORADOS)$" ; } | sort -u)"
# Classe A: o que sobrou citando `jq` — ali ele só formata a saída ou lê config.
LISTA_A="$(comm -23 <(printf '%s\n' "$LISTA_PROD") <(printf '%s\n' "$LISTA_B") \
  | xargs grep -l '\bjq\b' 2>/dev/null | sort)"

conta() { printf '%s\n' "$1" | grep -c . ; }
N_PROD=$(conta "$LISTA_PROD"); N_B=$(conta "$LISTA_B"); N_A=$(conta "$LISTA_A")

[ -f "$DOC" ] || { bad "$DOC não existe — o inventário do requisito W-2 sumiu"; exit 1; }

# --- 1) o retrato é IMPRESSO, não cobrado -----------------------------------
# Até 2026-08-09 esta seção grepava os três números dentro do doc e reprovava quando
# não achava. Era a peça mais frágil da suíte, e o motivo é estrutural: o número vive
# num documento AUTORAL, que nenhum mecanismo pode reescrever, e vence sozinho toda vez
# que um hook nasce — o conserto exigia a mão de um humano para um dado que a máquina
# mede em milissegundos. Trocado pela regra de desacoplamento da casa: o doc carrega o
# COMANDO, e quem imprime o número é quem sabe medir. O que continua cobrado abaixo é o
# que tem conteúdo humano dentro — a LISTA, porque cada linha dela diz o que se perde
# sem `jq`, e isso nenhum comando deriva.
echo "retrato de agora — produção: $N_PROD · classe B: $N_B · classe A: $N_A"

# --- 2) o inventário lista exatamente os arquivos medidos -------------------
tabela() { grep -E "^\| $1 \| \`plugins/" "$DOC" | sed -E 's/^\| [AB12]+ \| `([^`]+)`.*/\1/' | sort -u; }
DOC_A="$(tabela A)"
DOC_B="$(printf '%s\n%s\n' "$(tabela B1)" "$(tabela B2)" | grep . | sort -u)"

if [ "$DOC_A" = "$LISTA_A" ]; then
  ok "classe A do doc == classe A medida"
else
  bad "classe A divergiu:"; diff <(printf '%s\n' "$DOC_A") <(printf '%s\n' "$LISTA_A") | sed 's/^/     /'
fi
if [ "$DOC_B" = "$LISTA_B" ]; then
  ok "classe B (B1+B2) do doc == classe B medida"
else
  bad "classe B divergiu:"; diff <(printf '%s\n' "$DOC_B") <(printf '%s\n' "$LISTA_B") | sed 's/^/     /'
fi

# --- 3) B1 realmente bloqueia ----------------------------------------------
BLOQUEIA='permissionDecision"?[[:space:]]*:[[:space:]]*"deny|hj_deny|decision"?[[:space:]]*:[[:space:]]*"block|hj_block|^[[:space:]]*exit 2'
SEM_CANAL=""
for f in $(tabela B1); do
  grep -v '^[[:space:]]*#' "$f" 2>/dev/null | grep -qE "$BLOQUEIA" || SEM_CANAL="$SEM_CANAL $f"
done
if [ -z "$SEM_CANAL" ]; then
  ok "todo B1 tem canal de bloqueio (deny, block ou exit 2)"
else
  bad "B1 sem canal de bloqueio — classificar como B2:$SEM_CANAL"
fi

# --- 4) o conserto do issue #5, arquivo a arquivo ---------------------------
SEM_LEITOR=""; COM_BAIL=""; COM_JQ=""; SEM_AVISO=""
for f in $LISTA_B; do
  grep -q 'hook-json.sh' "$f" || SEM_LEITOR="$SEM_LEITOR $f"
  grep -E '^[[:space:]]*(command -v jq[^|]*\|\| *exit|\[ -z "\$JQ" \])' "$f" >/dev/null 2>&1 \
    && COM_BAIL="$COM_BAIL $f"
  # `jq` invocado direto (fora de comentário) volta a amarrar o gate ao binário.
  grep -v '^[[:space:]]*#' "$f" | grep -qE '(^|[^_[:alnum:]])jq[[:space:]]+-' && COM_JQ="$COM_JQ $f"
  grep -qE 'hj_avisa|sem jq nem python3' "$f" || SEM_AVISO="$SEM_AVISO $f"
done
[ -z "$SEM_LEITOR" ] && ok "todo hook da classe B lê pelo hook-json.sh ($N_B)" \
  || bad "classe B sem o leitor com fallback:$SEM_LEITOR"
[ -z "$COM_BAIL" ] && ok "nenhum hook da classe B desiste por falta de jq" \
  || bad "classe B ainda com bail de jq:$COM_BAIL"
[ -z "$COM_JQ" ] && ok "nenhum hook da classe B invoca jq direto" \
  || bad "classe B ainda invoca jq direto:$COM_JQ"
[ -z "$SEM_AVISO" ] && ok "todo hook da classe B avisa quando não há leitor nenhum" \
  || bad "classe B sem canal de aviso (sairia calado):$SEM_AVISO"

# --- 5) o vendoring do leitor chegou em todo plugin que precisa dele --------
SEM_COPIA=""
for f in $LISTA_B; do
  d="$(dirname "$f")"
  [ -f "$d/hook-json.sh" ] || SEM_COPIA="$SEM_COPIA $d"
done
[ -z "$SEM_COPIA" ] && ok "hook-json.sh vendorado em toda pasta de hooks da classe B" \
  || bad "pasta de hooks sem a cópia do leitor:$(printf '%s' "$SEM_COPIA" | tr ' ' '\n' | sort -u | tr '\n' ' ')"

# ===========================================================================
# 6) A PROVA: rodar hook da classe B com o jq FORA do PATH
# ===========================================================================
# Onde `jq` NÃO existe (é o caso que este requisito protege), a prova roda com o
# PATH de verdade. Onde ele existe, monta-se um sandbox: uma pasta com link para
# todo executável do PATH, menos o `jq`. Mascarar por variável não provaria nada —
# quem o hook consulta é o `command -v jq`.
SANDBOX="${TMPDIR:-/tmp}/test-sem-jq-$$"
mkdir -p "$SANDBOX" 2>/dev/null
PROVA_PATH=""
if ! command -v jq >/dev/null 2>&1; then
  PROVA_PATH="$PATH"
  ok "esta máquina já não tem jq — a prova roda no PATH real"
else
  mkdir -p "$SANDBOX/bin" 2>/dev/null
  OLD_IFS="$IFS"; IFS=:
  for d in $PATH; do
    [ -d "$d" ] || continue
    for exe in "$d"/*; do
      n="$(basename "$exe")"
      [ "$n" = "jq" ] && continue
      [ -e "$SANDBOX/bin/$n" ] || ln -s "$exe" "$SANDBOX/bin/$n" 2>/dev/null
    done
  done
  IFS="$OLD_IFS"
  if [ -x "$SANDBOX/bin/sed" ] && ! PATH="$PROVA_PATH" command -v jq >/dev/null 2>&1; then
    PROVA_PATH="$SANDBOX/bin"
    ok "PATH sem jq montado ($SANDBOX/bin)"
  fi
fi

if [ -z "$PROVA_PATH" ]; then
  # Sem sandbox e com jq instalado não há como provar nada — e isso se DIZ. O
  # sistema que não faz link simbólico (Git Bash com winsymlinks=copy) cai aqui.
  echo "pulado  a prova de execução: não deu para montar um PATH sem jq nesta máquina"
else

  # Projeto de mentira: documentação project-doc presente = o doc-guard tem o que cobrar.
  PROJ="$SANDBOX/proj"
  mkdir -p "$PROJ/.claude/docs"
  printf '# Project Reference\n' > "$PROJ/CLAUDE.md"
  printf '# arquitetura\n' > "$PROJ/.claude/docs/architecture.md"

  GUARD="plugins/project-skills/hooks/pretooluse-doc-guard.sh"
  paylod_bash() { printf '{"tool_name":"Bash","session_id":"%s","cwd":"%s","tool_input":{"command":"%s"}}' "$1" "$PROJ" "$2"; }

  # (a) DENY continua deny: busca cega num projeto com doc não lida.
  SAIDA="$(paylod_bash sessao-deny 'grep -r foo .' | PATH="$PROVA_PATH" bash "$GUARD" 2>/dev/null)"
  if printf '%s' "$SAIDA" | grep -q '"permissionDecision":"deny"'; then
    ok "sem jq, o doc-guard ainda BLOQUEIA a busca cega"
  else
    bad "sem jq, o doc-guard não bloqueou — saída: [$(printf '%s' "$SAIDA" | head -c 200)]"
  fi

  # (b) ALLOW continua allow: comando que não é busca cega passa calado.
  SAIDA="$(paylod_bash sessao-allow 'ls -la' | PATH="$PROVA_PATH" bash "$GUARD" 2>/dev/null)"
  RC=$?
  if [ "$RC" = "0" ] && [ -z "$SAIDA" ]; then
    ok "sem jq, o doc-guard ainda LIBERA o comando que não é busca cega"
  else
    bad "sem jq, o doc-guard falou no caminho que devia liberar (rc=$RC): [$SAIDA]"
  fi

  # (c) o gate de deploy: sem jq ele ainda enxerga o comando e ainda barra o
  #     deploy com teste vermelho. `make` é o runner mais universal dos que ele
  #     detecta; onde não houver, o caso é PULADO com aviso (nunca calado).
  SHIP="plugins/ship/hooks/pre-deploy-test-check.sh"
  if command -v make >/dev/null 2>&1; then
    APP="$SANDBOX/app"; mkdir -p "$APP"
    printf 'test:\n\t@exit 1\n' > "$APP/Makefile"
    printf '#!/bin/sh\necho deploy\n' > "$APP/deploy.sh"; chmod +x "$APP/deploy.sh"
    PAY="$(printf '{"session_id":"s","cwd":"%s","tool_input":{"command":"bash deploy.sh"}}' "$APP")"
    printf '%s' "$PAY" | PATH="$PROVA_PATH" bash "$SHIP" >/dev/null 2>&1
    if [ "$?" = "2" ]; then
      ok "sem jq, o gate de deploy ainda BARRA deploy com teste vermelho (exit 2)"
    else
      bad "sem jq, o gate de deploy deixou passar deploy com teste vermelho"
    fi
    printf 'test:\n\t@exit 0\n' > "$APP/Makefile"
    printf '%s' "$PAY" | PATH="$PROVA_PATH" bash "$SHIP" >/dev/null 2>&1
    [ "$?" = "0" ] && ok "sem jq, o gate de deploy ainda LIBERA com teste verde" \
      || bad "sem jq, o gate de deploy bloqueou um deploy com teste verde"
  else
    echo "pulado  gate de deploy: este sistema não tem \`make\` para servir de runner"
  fi

  # (d) sem jq E sem python3 não há como julgar — e aí o hook tem que FALAR.
  # O caminho de python3 sai do PATH da prova — no sandbox basta apagar o link;
  # no PATH real, monta-se uma pasta vazia (nada de jq, nada de python3).
  if [ "$PROVA_PATH" = "$SANDBOX/bin" ]; then
    rm -f "$SANDBOX/bin/python3" "$SANDBOX/bin/python" 2>/dev/null
  else
    mkdir -p "$SANDBOX/vazio"; PROVA_PATH="$SANDBOX/vazio"
  fi
  SAIDA="$(paylod_bash sessao-mudo 'grep -r foo .' | PATH="$PROVA_PATH" bash "$GUARD" 2>&1)"
  if [ -n "$SAIDA" ]; then
    ok "sem jq nem python3, o hook AVISA em vez de sair calado"
  else
    bad "sem jq nem python3 o hook saiu calado — é exatamente o issue #5"
  fi
fi
rm -rf "$SANDBOX" 2>/dev/null

echo "---"
[ "$FAIL" = 0 ] && echo "verde" || echo "vermelho"
exit $FAIL
