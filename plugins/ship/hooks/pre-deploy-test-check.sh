#!/bin/bash
# PreToolUse hook: blocks deploy commands if the relevant tests fail.
# Fires on every Bash tool call; only acts when the command looks like a deploy.
# Exit 0 = allow, Exit 2 = block (message shown to Claude)
#
# Two modes:
#   1. Per-app gate (preferred) — if the project has scripts/run_app_tests.sh,
#      run it for the app(s) being deployed. That script owns venv + scope +
#      e2e exclusion, so a monorepo deploy of one app only runs that app's
#      tests in the right interpreter (not the whole repo on the system python).
#   2. Legacy whole-suite — projects without that script keep the old behavior.

# Fail-open if jq is missing (marketplace convention — patterns.md:28). Resolve
# via PATH instead of a hardcoded Homebrew path so the gate actually fires on
# Intel macs / Linux / fresh bootstrap machines, not just this one.
# Kill-switch (2026-07-27, contrato dos hooks): quando este gate atrapalha
# num momento ruim, a saída não pode ser editar o script.
[ "${SHIP_GATE:-1}" = "0" ] && exit 0

command -v jq >/dev/null 2>&1 || exit 0

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

if [ -z "$COMMAND" ]; then
  exit 0
fi
# `.cwd` ausente NÃO pode apagar o gate. Era `[ -z "$CWD" ] && exit 0`: um payload
# sem o campo fazia o gate de produção desaparecer em silêncio absoluto.
# ponytail: cai pro $PWD. Teto conhecido: se o $PWD do hook não for o projeto, o
# Modo 2 pode achar o test runner errado — mas isso é falha VISÍVEL (bloqueio com
# mensagem), e falha visível é estritamente melhor que gate invisível.
[ -z "$CWD" ] && CWD="$PWD"

# ============================================================
# Detect if this is a deploy command
# ============================================================
is_deploy=false

# Prefixo que pode vir ANTES do comando sem que ele deixe de ser o comando.
# Existe por uma regressão MEDIDA (2026-07-30): a âncora de posição-de-comando —
# que é o que impede MENÇÃO de disparar o gate — cortou junto o prefixo legítimo.
# `nohup bash deploy.sh &` dava exit 2 no 823fbd3 e passou a dar exit 0; e
# `ENV=prod ./deploy.sh` / `sudo ./deploy.sh` nunca foram vistos. Nada exótico:
# é como se destaca um deploy longo do terminal e como se parametriza um.
# ENUMERADO de propósito, nunca "qualquer palavra antes" — senão a âncora deixa
# de existir e a menção volta a disparar (o contrapeso está na suíte:
# `echo sudo ./deploy.sh` e `git commit -m "sudo ./deploy.sh quebrou"` seguem 0).
# Teto conhecido: flag COM VALOR no lançador (`sudo -u deploy ./deploy.sh`) não
# casa — o valor não é lançador nem atribuição, e a corrente para nele.
CMDPFX='([A-Za-z_][A-Za-z0-9_]*=[^[:space:];&|]*[[:space:]]+|(sudo|nohup|env|time|exec|command)([[:space:]]+-[^[:space:];&|]+)*[[:space:]]+)*'

# ============================================================
# Canal de saída dos avisos que NÃO bloqueiam
# ============================================================
# `exit 0` + stderr é MUDO. A doc do harness é explícita: no exit 0 a saída do
# hook "is written to the debug log but not shown in the transcript", e as únicas
# exceções são UserPromptSubmit, UserPromptExpansion e SessionStart — PreToolUse
# NÃO está entre elas. Ou seja: os avisos deste gate não chegavam a ninguém, nem
# ao modelo nem ao usuário. Incluindo o pior deles, "deploy permitido sem
# verificação" — o gate avisava que estava desligado, para o debug log.
# No exit 0 o canal é JSON no stdout: `additionalContext` entra no contexto do
# modelo (ao lado do tool result) e `systemMessage` aparece pro usuário. Os dois,
# porque um deploy sem gate interessa aos dois públicos.
# ⚠️ Isto vale só pro caminho que LIBERA. Bloqueio segue `exit 2` + stderr, que é
# o canal documentado pra ele (nesse caso o stderr É devolvido ao modelo).
NOTES=""
note() { NOTES="${NOTES:+$NOTES
}$1"; }
allow_with_notes() {
  [ -n "$NOTES" ] && jq -n --arg m "$NOTES" \
    '{systemMessage:$m, hookSpecificOutput:{hookEventName:"PreToolUse", additionalContext:$m}}'
  exit 0
}

# PM2
# `pm2` tem que ser o COMANDO, igual ao make/vercel/bash. Com `\s` antes, a palavra
# dentro de PROSA disparava a suíte inteira: `git commit -m "conserta o pm2 restart do
# crm"` e `echo "no servidor: pm2 restart api"` vinham exit 2 — o pm2 era o único dos
# cinco padrões sem âncora, e bloqueio espúrio em `git commit` é o que ensina a
# desligar o gate. `ssh vps pm2 restart app` e `ssh vps "pm2 restart app"` seguem
# casando: quem os pega é o padrão de ssh (l.145), não este.
if echo "$COMMAND" | grep -qE '(^|[;&|][[:space:]]*)'"$CMDPFX"'pm2[[:space:]]+(restart|reload|deploy|start)'; then
  is_deploy=true
fi

# Docker compose (build + up implies deploy)
if echo "$COMMAND" | grep -qE '(docker-compose|docker compose).*(--build|-d)'; then
  is_deploy=true
fi

# Vercel / Netlify / Fly
# `vercel deploy --prod` é a forma que a CLI DOCUMENTA, e o padrão antigo
# (`vercel\s+--prod`) não casava o subcomando — o caminho canônico passava batido.
# O `.*` até o `--prod` era guloso e atravessava token: `git commit -m "vercel
# deploy --prod agora casa"` e `rg "vercel deploy --prod" .` disparavam a suíte
# inteira, e `vercel logs api --prod` também. Agora o binário tem que ser o
# COMANDO (âncora de início, igual ao make) e o `--prod` tem que pertencer à MESMA
# invocação — só flags e o subcomando `deploy` entre um e outro.
# Dois furos que a âncora + o clamp deixaram, os dois medidos com payload real:
#   · o LANÇADOR: quem não instala a CLI global roda `npx vercel deploy --prod` (é a
#     forma dos próprios guias), e a âncora de início de comando cegava todas. Prefixo
#     ENUMERADO (npx/pnpm dlx/yarn dlx/bunx), não "qualquer palavra antes".
#   · flag COM VALOR SEPARADO: o clamp só aceitava tokens começando com `-`, então
#     `netlify deploy --site my-project --prod` cortava a corrente no valor e o deploy
#     de produção passava batido. O valor não pode COMEÇAR com hífen (senão vira flag),
#     mas hífen no MEIO é livre — foi `my-project` que provou isso.
# O contrapeso segue de pé: `vercel logs api --prod` não casa, porque entre o binário e
# o `--prod` só se admite o subcomando `deploy` e flags — `logs` não é nem um nem outro.
if echo "$COMMAND" | grep -qE '(^|[;&|][[:space:]]*)'"$CMDPFX"'((npx|pnpm[[:space:]]+dlx|yarn[[:space:]]+dlx|bunx)[[:space:]]+)?(vercel([[:space:]]+deploy)?(([[:space:]]+--?[^[:space:];&|]+)([[:space:]]+[^-[:space:];&|][^[:space:];&|]*)?)*[[:space:]]+--prod|netlify[[:space:]]+deploy(([[:space:]]+--?[^[:space:];&|]+)([[:space:]]+[^-[:space:];&|][^[:space:];&|]*)?)*[[:space:]]+--prod|fly(ctl)?[[:space:]]+deploy)'; then
  is_deploy=true
fi

# Deploy via script de package.json — `npm run deploy` é a forma mais comum em
# projeto Node e não tinha padrão nenhum aqui.
if echo "$COMMAND" | grep -qE '(^|[;&|][[:space:]]*)'"$CMDPFX"'(npm|pnpm|yarn|bun)[[:space:]]+(run[[:space:]]+)?deploy'; then
  is_deploy=true
fi

# deploy.sh / Makefile deploy target
# Reconhece o script COM caminho (`bash tools/deploy.sh`, `cd x && ./deploy.sh`,
# `tools/deploy.sh`) e não só `./deploy.sh`/`bash deploy.sh`. Sem isto, invocar o deploy
# pelo caminho a partir da raiz do monorepo passava BATIDO pelo gate (deploy sem teste).
# Exige que o script seja o COMANDO — início da linha, depois de ;&| ou de bash/sh — para
# que uma menção como `grep foo tools/deploy.sh` não seja tratada como deploy.
# O terminador aceita todo DELIMITADOR de shell além de espaço/fim: o script pode estar
# colado no que fecha a invocação. Aceitar só espaço/fim/aspa-dupla deixava o gêmeo de
# cada forma detectada passar batido, e a assimetria foi medida com payload real:
#   · aspa SIMPLES — `ssh vps 'cd /app && ./deploy.sh'` saía exit 0 enquanto o mesmo
#     comando com aspa DUPLA saía exit 2; e a aspa simples é a forma idiomática de citar
#     comando remoto em ssh (a dupla deixa o shell local expandir `$`);
#   · `;` e `|` — `./deploy.sh; echo done` e `./deploy.sh|tee log` saíam exit 0 enquanto
#     `./deploy.sh && echo done` e `./deploy.sh > log` saíam exit 2;
#   · backtick e `)` — `(cd /app && ./deploy.sh)` e a forma com `` ` `` idem.
# Alargar o terminador é seguro porque ele só governa o que vem DEPOIS do token: a âncora
# de ABERTURA não muda, então `grep foo tools/deploy.sh` e a prosa que cita o script entre
# aspas (simples ou duplas) seguem exit 0.
# ⚠️ O nome do arquivo tem que ser `deploy.sh` — antes era `[^...]*deploy\.sh`, que aceita
# QUALQUER prefixo e portanto casa `test_pre_deploy.sh`, `predeploy.sh`, `undeploy.sh`.
# Consequência medida ao vivo em 2026-07-30: `bash plugins/ship/hooks/test_pre_deploy.sh`
# — RODAR A SUÍTE DESTE GATE — era classificado como deploy. Agora o que vem antes do
# nome só pode ser caminho (terminando em `/`). Custo aceito: script de deploy com nome
# COMPOSTO (`app-deploy.sh`) deixa de casar; nenhum teste cobria essa forma, e a
# alternativa era manter o gate disparando na própria suíte a cada commit.
# (a) script como comando direto: `./deploy.sh`, `tools/deploy.sh`, `cd x && ./deploy.sh`
if echo "$COMMAND" | grep -qE '(^|[;&|][[:space:]]*)[[:space:]]*'"$CMDPFX"'([^[:space:];&|]*/)?deploy\.sh([[:space:]"'\''`;&|)]|$)'; then
  is_deploy=true
fi
# (b) via interpretador: `bash tools/deploy.sh`, `... && sh deploy.sh`
# O `|[[:space:]]` na âncora aceitava o interpretador em QUALQUER posição, então prosa
# que só cita o comando disparava a suíte: `git commit -m "conserta o bash deploy.sh"`,
# `git commit -m "usa sh deploy.sh"` e `echo "roda o bash deploy.sh"` vinham exit 2.
# Agora `bash`/`sh` tem que ser o COMANDO (início ou depois de ;&|), igual ao make e ao
# vercel. O terminador largo FICA (mesmo do padrão (a)): é ele que faz `ssh vps "cd /app
# && ./deploy.sh"` casar, e `bash tools/deploy.sh; echo ok` / `ssh vps 'bash
# /app/deploy.sh'` — que saíam exit 0 — casarem aqui.
if echo "$COMMAND" | grep -qE '(^|[;&|][[:space:]]*)'"$CMDPFX"'(bash|sh)[[:space:]]+([^[:space:];&|]*/)?deploy\.sh([[:space:]"'\''`;&|)]|$)'; then
  is_deploy=true
fi
# `make` tem que ser o COMANDO. Sem âncora, a palavra dentro de uma mensagem de
# commit (`git commit -m "make deploy target fixed"`) disparava a suíte inteira.
if echo "$COMMAND" | grep -qE '(^|[;&|][[:space:]]*)'"$CMDPFX"'make[[:space:]]+(deploy|prod|release)'; then
  is_deploy=true
fi

# SSH-based deploy patterns
# Dois consertos num padrão só, os dois medidos com payload real:
#   · o separador antes do verbo era `\s`, mas a forma real é `ssh vps "pm2 ..."` —
#     a ASPA cola no verbo e o gate cegava no caso mais comum;
#   · `deploy` casava dentro do USERNAME (`ssh -t deploy@vps ls`), então exigimos
#     que o verbo não seja seguido de `@`.
# O meio voltou a ser `.*`: o `[^;&|]*` parava a busca no primeiro `&&`/`;`, e o
# deploy remoto real é justamente `ssh vps "cd /app && git pull"` — o gate cegava
# na forma MAIS comum. A precisão que o clamp tentava dar vem agora do outro eixo:
# casa-se a AÇÃO, não o nome da ferramenta. `ssh vps "docker ps"` e
# `ssh vps "pm2 logs api"` são inspeção remota do dia a dia; bloqueá-las é o que
# ensina a desligar o gate.
# A lista de ações estava ASSIMÉTRICA e o furo foi medido com payload real: `docker
# restart` casava, mas `docker start` e `docker compose restart` saíam exit 0 — e as
# três são a MESMA ação (subir a versão nova do container). `docker compose restart`
# escapa até do padrão local de compose (l.47), que exige `--build`/`-d`. A extensão é
# ENUMERADA de propósito: `stop` fica FORA (parar não é deployar) e `docker ps`/
# `pm2 logs` seguem ignorados.
# A assimetria se repetia um nível abaixo, e os dois furos foram medidos com payload real:
#   · a lista de ações valia só pra grafia com ESPAÇO: `docker compose restart` casava e
#     `docker-compose restart` (compose v1, a grafia instalada em VPS) saía exit 0 — e como
#     `restart` não leva `--build`/`-d`, o padrão local de compose (l.47) não pega nenhuma
#     das duas, então não sobrava rede nenhuma;
#   · `docker run` — subir container novo, a MESMA ação que o `start`/`restart` já
#     enumerados — também saía exit 0.
# Extensão ENUMERADA de novo (dois membros nomeados numa lista fechada): nenhuma regra
# genérica alarga, e `docker-compose ps`/`docker logs -f` seguem sendo inspeção ignorada.
if echo "$COMMAND" | grep -qE '(^|[;&|][[:space:]]*)ssh[[:space:]]+.*[^[:alnum:]_@./-](git pull|pm2[[:space:]]+(restart|reload|deploy|start)|docker[[:space:]]+(restart|start|run|compose[[:space:]]+(up|restart))|docker-compose[[:space:]]+(up|restart)|deploy)([^@]|$)'; then
  is_deploy=true
fi

if [ "$is_deploy" = false ]; then
  exit 0
fi

# Cache verde (fail-open): suite já passou 100% neste exato tree-hash → pula a
# re-execução. Qualquer edição muda o hash e invalida; vermelho nunca grava.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/green-cache.sh" ] && . "$SCRIPT_DIR/green-cache.sh"

# ============================================================
# Mode 1 — per-app gate (preferred when the project provides it)
# ============================================================
# Num MONOREPO o gate (scripts/run_app_tests.sh) vive no MÓDULO (ex.: tools/), não na
# raiz — e o deploy é normalmente invocado da raiz (`cd tools && ./deploy.sh crm`,
# `bash tools/deploy.sh crm`). Com GATE fixo em "$CWD", cwd=raiz NÃO achava o gate e o
# fluxo caía no Modo 2, que subia a árvore, achava o pyproject.toml da RAIZ e rodava o
# pytest do repo INTEIRO — bloqueando o deploy com erros de apps sem relação (38
# ImportError num monorepo real). O deploy só passava com o cwd exatamente em tools/, o que
# obrigava a contornar o gate à mão. Agora o diretório do projeto vem do COMANDO.
resolve_proj_dir() {
  local cmd="$1" cwd="$2" cand d
  # 1) `cd <dir> && ... deploy.sh ...`
  cand=$(printf '%s' "$cmd" | sed -nE 's@.*(^|[;&|[:space:]])cd[[:space:]]+([^;&|[:space:]]+).*deploy\.sh.*@\2@p' | head -1)
  if [ -n "$cand" ]; then
    case "$cand" in /*) ;; *) cand="$cwd/$cand" ;; esac
    [ -x "$cand/scripts/run_app_tests.sh" ] && { printf '%s' "$cand"; return; }
  fi
  # 2) caminho explícito do script (`bash tools/deploy.sh`, `./deploy.sh`)
  cand=$(printf '%s' "$cmd" | sed -nE 's@.*[^[:alnum:]_/.-]([^[:space:];&|]*deploy\.sh).*@\1@p' | head -1)
  [ -z "$cand" ] && cand=$(printf '%s' "$cmd" | sed -nE 's@^([^[:space:];&|]*deploy\.sh).*@\1@p' | head -1)
  if [ -n "$cand" ]; then
    d=$(dirname "$cand")
    case "$d" in /*) ;; .) d="$cwd" ;; *) d="$cwd/$d" ;; esac
    [ -x "$d/scripts/run_app_tests.sh" ] && { printf '%s' "$d"; return; }
  fi
  printf '%s' "$cwd"
}
PROJ=$(resolve_proj_dir "$COMMAND" "$CWD")
GATE="$PROJ/scripts/run_app_tests.sh"
if [ -x "$GATE" ] && echo "$COMMAND" | grep -qE 'deploy\.sh'; then
  # Apps listed after deploy.sh, trimmed at the first shell separator; flags out.
  # O recorte antigo (`s/.*deploy\.sh//; s/[;&|].*//`) errava em dois casos MEDIDOS,
  # os dois terminando em deploy sem teste nenhum:
  #   · REDIREÇÃO virava nome de app: em `bash tools/deploy.sh > /tmp/dep.log` (deploy
  #     FULL) os tokens `>` e `/tmp/dep.log` sobreviviam ao filtro, ARGS ficava
  #     não-vazio, o discover_apps() nunca rodava e o gate liberava TODOS os apps
  #     avisando sobre '>' como se fosse app. Idem `... 2>&1 | tee log`.
  #   · `.*deploy\.sh` é GULOSO e cortava no ÚLTIMO script: em
  #     `bash tools/deploy.sh crm && bash tools/deploy.sh web` só o web era testado —
  #     o crm subia sem teste e sem aviso.
  # Agora: quebra o comando nos separadores, soma os args de CADA invocação do
  # deploy.sh e joga fora a redireção (`>`, `>>`, `2>`, `&>`, `<`) e o alvo dela.
  # As FLAGS ficam na lista aqui de propósito: quem separa app de VALOR-de-flag é a
  # passada abaixo, e ela precisa saber o que vinha antes de cada token.
  ARGS=$(printf '%s' "$COMMAND" | tr ';&|' '\n\n\n' \
    | grep 'deploy\.sh' | sed -E 's/.*deploy\.sh//; s/[0-9]*[<>].*//' | tr '\n' ' ')

  # An app "has tests" if it has a pytest dir OR is a Node app that declares a
  # real `test` script (vitest/jest) — those tests live in __tests__/colocated,
  # with no tests/ dir for the prober to find. run_app_tests.sh runs the right
  # runner per app; this just decides whether to invoke it.
  node_has_test_script() {
    [ -f "$1" ] || return 1
    local t
    t=$(jq -r '.scripts.test // empty' "$1" 2>/dev/null)
    [ -n "$t" ] && ! echo "$t" | grep -q 'no test specified'
  }
  app_has_tests() {
    [ -d "$PROJ/tests/$1" ] && return 0
    [ -d "$PROJ/apps/$1/tests" ] && return 0
    node_has_test_script "$PROJ/apps/$1/package.json"
  }
  # Diretórios sob tests/ que NÃO são app: cache, fixtures e suites transversais. Sem
  # este filtro o deploy full "descobria" __pycache__/e2e/fixtures/contracts como apps e
  # gastava uma rodada de pytest em cada um.
  is_app_like() {
    case "$1" in
      _*|.*|__*|e2e|fixtures|helpers|utils|conftest|contracts|smoke) return 1 ;;
    esac
    return 0
  }
  discover_apps() {
    { for d in "$PROJ"/tests/*/; do [ -d "$d" ] && basename "$d"; done
      for d in "$PROJ"/apps/*/tests; do [ -d "$d" ] && basename "$(dirname "$d")"; done
      for p in "$PROJ"/apps/*/package.json; do
        node_has_test_script "$p" && basename "$(dirname "$p")"
      done
    } | sort -u | while read -r a; do is_app_like "$a" && echo "$a"; done
  }

  # VALOR de flag não é nome de app. O filtro antigo só descartava o token que COMEÇA
  # com `-`, então em `bash tools/deploy.sh --env prod` (deploy FULL com flag) o `prod`
  # sobrevivia, virava o ÚNICO "app", não tinha teste — e o gate liberava o deploy
  # INTEIRO rodando ZERO teste, só com o aviso de app-sem-gate. Medido: `--env prod`,
  # `--tag v1` e `--site my-project` saíam exit 0 sem um único teste; a mesma família da
  # redireção virando nome de app. Regra: token DESCONHECIDO ao discover_apps() e
  # precedido de flag é valor de flag → descarta calado; se isso zerar a lista, é deploy
  # FULL. Token desconhecido SEM flag antes SEGUE sendo app e SEGUE avisando — é ele que
  # preserva o `./deploy.sh fantasma`. Não é fallback cego pro discover_apps(): app
  # nomeado tem que continuar escopando, senão o gate super-gateia o monorepo (l.135-141).
  KNOWN=$(discover_apps)
  CAND=""
  prev_flag=0
  for tok in $ARGS; do
    case "$tok" in -*) prev_flag=1; continue ;; esac
    if [ "$prev_flag" = 1 ] && ! printf '%s\n' "$KNOWN" | grep -qxF "$tok"; then
      prev_flag=0
      continue
    fi
    prev_flag=0
    CAND="$CAND $tok"
  done

  if [ -z "$(echo "$CAND" | tr -d '[:space:]')" ]; then
    APPS="$KNOWN"   # full deploy → gate every app that has tests
  else
    APPS="$CAND"
  fi

  FAILED=""
  RAN=""
  for app in $APPS; do
    # Pular app sem teste é o comportamento certo, mas pular CALADO não é: era
    # exit 0 com zero output — o mesmo silêncio que deixou 17 vitest quebrados
    # subirem (runtime.md §6). O gate não bloqueia aqui, mas fala.
    app_has_tests "$app" || {
      note "⚠️  app $app deployado SEM gate (nenhum teste achado)"
      continue
    }
    if type green_cache_check >/dev/null 2>&1 && green_cache_check "$PROJ" "app:$app"; then
      RAN="$RAN $app(cache)"
      continue
    fi
    RAN="$RAN $app"
    if ! ( cd "$PROJ" && bash scripts/run_app_tests.sh "$app" ); then
      FAILED="$FAILED $app"
    else
      type green_cache_mark >/dev/null 2>&1 && green_cache_mark "$PROJ" "app:$app" ship-hook
    fi
  done

  if [ -n "$FAILED" ]; then
    echo "🚫 Deploy bloqueado — testes do(s) app(s) falhando:$FAILED" >&2
    echo "" >&2
    echo "Rode local e corrija:  bash scripts/run_app_tests.sh <app>" >&2
    echo "(testes que precisam de produção ficam fora do gate via @pytest.mark.e2e)" >&2
    exit 2
  fi
  [ -n "$RAN" ] && note "✅ Gate de testes ok:$RAN"
  allow_with_notes
fi

# A project that ships a per-app gate has declared THAT as its contract. If we
# got here it's a deploy-ish command that isn't ./deploy.sh (a manual migration
# via ssh+docker, `docker compose up -d <svc>`, a NOTIFY, etc.) — not scopable
# to one app. Running the legacy whole-repo suite for it is wrong (and in a
# monorepo it fails on unrelated apps' stale tests). Real code deploys still go
# through ./deploy.sh → Mode 1. So: allow, don't fall through to the legacy run.
if [ -x "$GATE" ]; then
  note "ℹ️  Comando fora do ./deploy.sh; projeto usa gate por-app (scripts/run_app_tests.sh) — whole-suite legado pulado."
  allow_with_notes
fi

# ============================================================
# Mode 2 — legacy whole-suite runner (projects without the per-app gate)
# ============================================================
TEST_CMD=""
TEST_RUNNER=""
TEST_DIR=""
SEARCH_DIR="$CWD"

while [ "$SEARCH_DIR" != "/" ]; do
  # package.json with a real test script
  if [ -f "$SEARCH_DIR/package.json" ]; then
    HAS_TEST=$(jq -r '.scripts.test // empty' "$SEARCH_DIR/package.json" 2>/dev/null)
    if [ -n "$HAS_TEST" ] && ! echo "$HAS_TEST" | grep -q 'no test specified'; then
      TEST_CMD="CI=true npm test"
      TEST_RUNNER="npm test"
      TEST_DIR="$SEARCH_DIR"
      break
    fi
  fi

  # pytest — o interpretador tem que ser o DO PROJETO: .venv local > uv > pytest do PATH.
  # Bare `pytest` num app uv/venv acha o Python global (sem as deps) e falha com
  # ModuleNotFoundError, reprovando um gate que na verdade está verde.
  if [ -f "$SEARCH_DIR/pyproject.toml" ] || [ -f "$SEARCH_DIR/pytest.ini" ] || [ -f "$SEARCH_DIR/setup.cfg" ]; then
    if [ -x "$SEARCH_DIR/.venv/bin/pytest" ]; then
      TEST_CMD="./.venv/bin/pytest"
      TEST_RUNNER=".venv/bin/pytest"
    elif [ -f "$SEARCH_DIR/pyproject.toml" ] && command -v uv &>/dev/null; then
      TEST_CMD="uv run --all-extras pytest"
      TEST_RUNNER="uv run pytest"
    elif command -v pytest &>/dev/null; then
      TEST_CMD="pytest"
      TEST_RUNNER="pytest"
    fi
    if [ -n "$TEST_CMD" ]; then
      TEST_DIR="$SEARCH_DIR"
      break
    fi
  fi

  # Cargo
  if [ -f "$SEARCH_DIR/Cargo.toml" ]; then
    if command -v cargo &>/dev/null; then
      TEST_CMD="cargo test"
      TEST_RUNNER="cargo test"
      TEST_DIR="$SEARCH_DIR"
      break
    fi
  fi

  # Go
  if [ -f "$SEARCH_DIR/go.mod" ]; then
    if command -v go &>/dev/null; then
      TEST_CMD="go test ./..."
      TEST_RUNNER="go test"
      TEST_DIR="$SEARCH_DIR"
      break
    fi
  fi

  # Makefile with test target
  if [ -f "$SEARCH_DIR/Makefile" ] && grep -q '^test:' "$SEARCH_DIR/Makefile" 2>/dev/null; then
    TEST_CMD="make test"
    TEST_RUNNER="make test"
    TEST_DIR="$SEARCH_DIR"
    break
  fi

  SEARCH_DIR=$(dirname "$SEARCH_DIR")
done

if [ -z "$TEST_CMD" ]; then
  note "⚠️  pre-deploy-test-check: nenhum test runner detectado — deploy permitido sem verificação."
  allow_with_notes
fi

# Green cache: whole suite already passed at this exact tree state → allow.
if type green_cache_check >/dev/null 2>&1 && green_cache_check "$TEST_DIR" full; then
  note "✅ Cache verde: suite já passou 100% neste tree-hash — deploy liberado sem re-execução."
  allow_with_notes
fi

# Run the tests
TEST_OUTPUT=$(cd "$TEST_DIR" && eval "$TEST_CMD" 2>&1)
TEST_EXIT=$?

if [ $TEST_EXIT -ne 0 ]; then
  TRUNCATED=$(echo "$TEST_OUTPUT" | tail -40)
  echo -e "🚫 Deploy bloqueado — testes falhando ($TEST_RUNNER em $TEST_DIR)\n\nCorreja os testes antes de fazer deploy. Falhas:\n\n$TRUNCATED" >&2
  exit 2
fi

type green_cache_mark >/dev/null 2>&1 && green_cache_mark "$TEST_DIR" full ship-hook

exit 0
