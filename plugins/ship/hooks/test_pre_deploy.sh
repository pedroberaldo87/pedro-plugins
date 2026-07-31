#!/bin/bash
# test_pre_deploy.sh — suíte do gate de pré-deploy (pre-deploy-test-check.sh).
# Roda isolado em mktemp; não toca projeto nenhum. Uso: bash test_pre_deploy.sh
#
# Por que ela existe: as regressões deste hook nasceram TODAS em mexida de regex
# sem rede. Cada caso abaixo é uma regressão nomeada — a foto do "antes".
#
# Como um caso mede detecção sem rodar suite de verdade: o fixture PROBE é um
# projeto cujo `make test` falha DE PROPÓSITO. Aí o exit code do hook responde
# uma pergunta só:
#     detectou deploy  -> roda a suite -> vermelho -> exit 2
#     não detectou     -> exit 0
# Sem esse truque, "não detectou" e "detectou e passou" seriam os dois exit 0.
#
# HOOK_UNDER_TEST=<path>  testa uma CÓPIA do hook (usado pela prova anti-tautologia)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="${HOOK_UNDER_TEST:-$SCRIPT_DIR/pre-deploy-test-check.sh}"
PASS=0; FAIL=0

ok()  { PASS=$((PASS+1)); printf '  ✓ %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  ✗ %s\n     esperado: %s\n     obtido:   %s\n' "$1" "$2" "$3"; }

command -v jq >/dev/null 2>&1 || { echo "jq ausente — o hook é fail-open sem ele e a suíte não mede nada"; exit 1; }

TMP=$(mktemp -d)
# Cache verde ISOLADO: sem isto um registro verde do projeto real poderia dar HIT
# e liberar um deploy que a suíte espera ver bloqueado.
export GREEN_SUITE_DIR="$TMP/green-suite"
trap 'rm -rf "$TMP"' EXIT

# --- fixtures -------------------------------------------------------------
PROBE="$TMP/probe"                      # projeto sem gate por-app; `make test` falha
mkdir -p "$PROBE"
(cd "$PROBE" && git init -q . && git commit -q --allow-empty -m x 2>/dev/null)
printf 'test:\n\t@exit 1\n' > "$PROBE/Makefile"

MODE1="$TMP/mode1"                      # projeto COM gate por-app, e nenhum app com teste
mkdir -p "$MODE1/scripts"
(cd "$MODE1" && git init -q . && git commit -q --allow-empty -m x 2>/dev/null)
printf '#!/bin/bash\nexit 0\n' > "$MODE1/scripts/run_app_tests.sh"
chmod +x "$MODE1/scripts/run_app_tests.sh"

MONO="$TMP/mono"                        # monorepo: gate por-app em tools/, 2 apps COM teste
mkdir -p "$MONO/tools/scripts" "$MONO/tools/tests/crm" "$MONO/tools/tests/web"
(cd "$MONO" && git init -q . && git commit -q --allow-empty -m x 2>/dev/null)
printf '#!/bin/bash\nexit 0\n' > "$MONO/tools/scripts/run_app_tests.sh"
chmod +x "$MONO/tools/scripts/run_app_tests.sh"

MONO_RED="$TMP/mono-red"                # idem, mas o gate por-app REPROVA: o caminho vermelho
mkdir -p "$MONO_RED/tools/scripts" "$MONO_RED/tools/tests/crm"
(cd "$MONO_RED" && git init -q . && git commit -q --allow-empty -m x 2>/dev/null)
printf '#!/bin/bash\nexit 1\n' > "$MONO_RED/tools/scripts/run_app_tests.sh"
chmod +x "$MONO_RED/tools/scripts/run_app_tests.sh"

# Gêmeo VERDE do PROBE: mesmo Modo 2, mas `make test` PASSA. Sem ele o eixo
# "detectou e LIBEROU" é estruturalmente inalcançável — com uma fixture vermelha só,
# exit 0 significa as duas coisas ("não detectou" e "liberou"), e a suíte nunca mede
# a segunda. Foi essa cegueira que deixou a mutação `if [ $TEST_EXIT -ne 0 ]` -> `if
# true` (o hook bloqueando TODO deploy de Modo 2 com a suite verde) passar com 73 ok.
GREEN="$TMP/green"
mkdir -p "$GREEN"
(cd "$GREEN" && git init -q . && git commit -q --allow-empty -m x 2>/dev/null)
printf 'test:\n\t@exit 0\n' > "$GREEN/Makefile"

NORUNNER="$TMP/norunner"                # nenhum test runner: o caminho do aviso sem gate
mkdir -p "$NORUNNER"
(cd "$NORUNNER" && git init -q . && git commit -q --allow-empty -m x 2>/dev/null)

hook() { # hook <command> [cwd] -> imprime o exit code do hook
  local cmd="$1" cwd="${2:-$PROBE}"
  printf '{"cwd":%s,"tool_input":{"command":%s}}' \
    "$(printf '%s' "$cwd" | jq -Rs .)" "$(printf '%s' "$cmd" | jq -Rs .)" \
    | bash "$HOOK" >/dev/null 2>&1
  echo $?
}
hook_err() { # hook_err <command> <cwd> -> STDERR do hook (canal do BLOQUEIO, exit 2)
  printf '{"cwd":%s,"tool_input":{"command":%s}}' \
    "$(printf '%s' "$2" | jq -Rs .)" "$(printf '%s' "$1" | jq -Rs .)" \
    | bash "$HOOK" 2>&1 >/dev/null
}
# Canal do caminho que LIBERA (exit 0): JSON no stdout. `exit 0` + stderr é MUDO —
# a doc do harness diz que no exit 0 a saída vai só pro debug log, e PreToolUse não
# está entre as exceções (UserPromptSubmit/UserPromptExpansion/SessionStart). Ler
# stderr aqui era medir um canal que não chega a ninguém: o teste ficava verde com o
# aviso invisível, que é o oposto do que o F2.7 do plano queria garantir.
hook_json() { # hook_json <command> <cwd> -> STDOUT cru do hook
  printf '{"cwd":%s,"tool_input":{"command":%s}}' \
    "$(printf '%s' "$2" | jq -Rs .)" "$(printf '%s' "$1" | jq -Rs .)" \
    | bash "$HOOK" 2>/dev/null
}
hook_note() { # hook_note <command> <cwd> -> só o additionalContext, extraído por jq
  hook_json "$1" "$2" | jq -r '.hookSpecificOutput.additionalContext // empty' 2>/dev/null
}
gateia() { # gateia <command> <cwd> <app...> -> exige exit 0 + a linha POSITIVA citando CADA app
  local cmd="$1" cwd="$2"; shift 2
  local err line a missing="" e
  err=$(hook_note "$cmd" "$cwd")
  # O EXIT entra no assert junto da mensagem: lendo só o stderr, trocar o `exit 0` final
  # do Modo 1 por `exit 2` — gate que roda o teste, vê VERDE e bloqueia o deploy — não
  # pintava nada de vermelho (medido: 73 ok, 0 falhas). Mensagem certa com exit errado é
  # exatamente o bloqueio espúrio que ensina a desligar o gate.
  e=$(hook "$cmd" "$cwd")
  # Só a linha do "✅ Gate de testes ok:" conta como prova de execução. Procurar o nome do
  # app em QUALQUER lugar do stderr fazia o AVISO de app-sem-teste ("⚠️ app crm deployado
  # SEM gate", que também cita o nome) satisfazer o assert: com `app_has_tests` sempre
  # falso — o gate rodando ZERO teste — esta seção inteira continuava verde (medido: 55 ok,
  # 0 falhas). A rede media a presença do nome, não que o teste do app tinha rodado.
  line=$(printf '%s\n' "$err" | grep -F '✅ Gate de testes ok:')
  for a in "$@"; do
    case "$line" in *"$a"*) ;; *) missing="$missing $a" ;; esac
  done
  [ -z "$missing" ] && [ "$e" = 0 ] && ok "gateia [$*] · $cmd" \
    || bad "gateia [$*] · $cmd" "exit 0 + '✅ Gate de testes ok:' citando $*" \
           "exit $e — faltou${missing:- nada} — stderr: '${err:-<vazio>}'"
}
detecta() { local e; e=$(hook "$1")
  [ "$e" = 2 ] && ok "detecta  · $1" || bad "detecta  · $1" "exit 2 (deploy bloqueado)" "exit $e"; }
ignora()  { local e; e=$(hook "$1")
  [ "$e" = 0 ] && ok "ignora   · $1" || bad "ignora   · $1" "exit 0 (não é deploy)" "exit $e"; }

echo "── Detecções que o gate JÁ acerta (travando o que funciona) ──"

detecta 'pm2 restart app'                       # R1
detecta 'docker compose up -d'                  # R2
detecta 'netlify deploy --prod'                 # R3
detecta 'vercel --prod'                         # R4  forma antiga: não pode regredir
detecta './deploy.sh'                           # R5
detecta 'bash tools/deploy.sh crm'              # R6  script pelo caminho, via interpretador
detecta 'cd tools && ./deploy.sh crm'           # R7  invocado da raiz do monorepo
detecta 'make deploy'                           # R8
detecta 'ssh vps pm2 restart app'               # R9  verbo com ESPAÇO antes (o caso que casa hoje)

echo "── Não-deploys: o gate tem que sair calado (o lado que regex gananciosa quebra) ──"

ignora 'grep foo tools/deploy.sh'               # R10 menção ao script não é invocação
ignora 'git status'                             # R11
ignora 'ls -la'                                 # R12
ignora 'echo "make it work"'                    # R13 make sem alvo de deploy
ignora 'docker compose logs'                    # R14 compose sem --build/-d

echo "── Contrato de entrada ──"

E=$(printf '{"cwd":"%s","tool_input":{}}' "$PROBE" | bash "$HOOK" >/dev/null 2>&1; echo $?)
[ "$E" = 0 ] && ok "comando vazio · sai 0 sem opinar" || bad "comando vazio · sai 0" "exit 0" "exit $E"

E=$(printf '{"cwd":"%s","tool_input":{"command":"pm2 restart app"}}' "$PROBE" | SHIP_GATE=0 bash "$HOOK" >/dev/null 2>&1; echo $?)
[ "$E" = 0 ] && ok "kill-switch SHIP_GATE=0 · desarma o gate" || bad "kill-switch SHIP_GATE=0" "exit 0" "exit $E"

echo "── Furos: a forma CANÔNICA de cada comando (é o que passava batido) ──"

detecta 'vercel deploy --prod'                  # a forma que a CLI da Vercel documenta
detecta 'fly deploy'
detecta 'flyctl deploy'
detecta 'ssh vps "pm2 restart app"'             # a aspa cola no verbo
detecta 'ssh vps "cd /app && ./deploy.sh"'      # a aspa FECHA depois do script
# O deploy remoto REAL quase nunca é um verbo só: é `cd <dir> && <verbo>`. O gate
# não pode parar de olhar no primeiro `&&`/`;` — é o deploy manual mais comum.
detecta 'ssh vps "cd /app && git pull"'
detecta 'ssh vps "cd /app; git pull; systemctl reload nginx"'
detecta 'ssh vps "docker compose up -d --build"'
# INVARIANTE: a lista de AÇÕES remotas do padrão de ssh tem que ser simétrica. `docker
# restart` estava enumerado e `docker start`/`docker compose restart` não — as três são
# a mesma ação (subir a versão nova do container), e as duas de fora passavam batido.
# Estes dois casos são EXCLUSIVOS do padrão de ssh: `docker compose restart` não leva
# `--build`/`-d`, então o padrão local de compose (l.47) não os alcança.
detecta 'ssh vps "docker compose restart api"'
detecta 'ssh vps "docker start api"'
# INVARIANTE: a simetria da lista de ações vale POR GRAFIA de compose. A rodada anterior
# fechou `docker compose restart` (com ESPAÇO) e deixou o hífen de fora — e `docker-compose`
# (compose v1) é justamente a grafia instalada em VPS. Medido no hook real, no mesmo run:
# `ssh vps "docker compose restart api"` saía exit 2 e `ssh vps "docker-compose restart api"`
# saía exit 0. Como `restart` não leva `--build`/`-d`, o padrão local de compose (l.47) não
# alcança nenhuma das duas: sem este caso não sobra rede nenhuma. Um `detecta` por grafia
# por ação, senão a assimetria volta na próxima mexida.
detecta 'ssh vps "docker-compose restart api"'
detecta 'ssh vps "cd /app && docker-compose restart"'
detecta 'ssh vps "cd /app && docker-compose up"'      # grafia com hífen da ação `up` (controle)
# INVARIANTE: `docker run` é subir container novo — a MESMA ação que `docker restart`/
# `docker start`, que já estavam enumerados. Medido: `ssh vps "docker run -d --name api
# myimg"` saía exit 0 enquanto `ssh vps "docker start api"` saía exit 2 no mesmo run.
detecta 'ssh vps "docker run -d --name api myimg"'
# INVARIANTE: o terminador do padrão de deploy.sh tem que aceitar TODO delimitador de
# shell, não só espaço/aspa-dupla/fim. Medido no hook real: o gêmeo com aspa DUPLA
# (l.123) detectava e o com aspa SIMPLES — a forma idiomática de citar comando remoto
# em ssh — saía exit 0 no mesmo run; idem `;`, `|`, backtick e `)` colados no script.
# São todos o MESMO deploy, e cada um passava batido.
detecta "ssh vps 'cd /app && ./deploy.sh'"          # aspa SIMPLES fecha depois do script
detecta './deploy.sh; echo done'                    # `;` cola no script
detecta './deploy.sh|tee /tmp/dep.log'              # pipe cola no script
detecta '(cd /app && ./deploy.sh)'                  # `)` de subshell cola no script
detecta 'ssh vps "cd /app && `./deploy.sh`"'        # backtick fecha depois do script
detecta 'bash tools/deploy.sh; echo ok'             # idem no padrão via interpretador
detecta "ssh vps 'cd / && bash /app/deploy.sh'"     # idem, aspa SIMPLES fechando
detecta 'npm run deploy'
detecta 'pnpm run deploy:prod'
detecta 'yarn deploy'
# INVARIANTE: a CLI de deploy chamada por LANÇADOR (npx/pnpm dlx/yarn dlx/bunx) é a
# mesma invocação — quem não instala a CLI global usa essa forma, e ela é a
# documentada nos guias. A âncora de início de comando, sozinha, cegava todas.
detecta 'npx vercel deploy --prod'
detecta 'npx netlify deploy --prod'
detecta 'pnpm dlx vercel deploy --prod'
detecta 'yarn dlx netlify deploy --prod'
detecta 'bunx vercel deploy --prod'
detecta 'npx fly deploy'
# INVARIANTE: flag COM VALOR SEPARADO entre o binário e o `--prod` continua sendo a
# mesma invocação. O clamp só aceitava tokens começando com `-`, então o valor
# (`my-project`, `my-team`) cortava a corrente e o deploy de produção passava batido.
detecta 'netlify deploy --site my-project --prod'
detecta 'vercel deploy --scope my-team --prod'

echo "── Prefixo antes do comando: lançador e atribuição de variável ──"
# REGRESSÃO MEDIDA (2026-07-30): a âncora de posição-de-comando, que existe pra
# impedir que MENÇÃO dispare o gate, cortou junto o PREFIXO legítimo. Medido com
# payload real: `nohup bash deploy.sh &` dava exit 2 no 823fbd3 e passou a dar
# exit 0. Não é forma exótica — é como se destaca um deploy longo do terminal, e
# `VAR=valor` é a forma mais banal de parametrizar um.
detecta 'nohup bash deploy.sh &'
detecta 'sudo ./deploy.sh'
detecta 'ENV=prod ./deploy.sh'
detecta 'NODE_ENV=production npm run deploy'
detecta 'sudo make deploy'
detecta 'env FOO=bar bash tools/deploy.sh crm'
detecta 'sudo pm2 restart app'
# CONTRAPESO: o prefixo é ENUMERADO, não "qualquer palavra antes" — senão a
# âncora deixaria de existir e a menção volta a disparar.
ignora 'echo sudo ./deploy.sh'
ignora 'git commit -m "sudo ./deploy.sh quebrou"'
ignora 'grep -r nohup tools/deploy.sh'
# REGRESSÃO MEDIDA AO VIVO (2026-07-30): rodar a suíte DESTE gate disparava o gate,
# porque `test_pre_deploy.sh` termina em `deploy.sh` e o padrão aceitava qualquer
# prefixo. Só apareceu porque o canal do aviso foi consertado no mesmo turno — antes
# a mensagem ia pro debug log e ninguém veria.
ignora 'bash plugins/ship/hooks/test_pre_deploy.sh'
ignora './predeploy.sh'
ignora 'bash undeploy.sh'

echo "── Falsos-positivos: menção não é comando ──"

ignora 'git commit -m "make deploy target fixed"'   # make sem âncora de início
ignora 'ssh -t deploy@vps ls'                       # 'deploy' é o USERNAME
# Olhar log/estado remoto é o comando de ssh mais frequente do dia. Casar o NOME da
# ferramenta (docker/pm2) em vez da AÇÃO transforma inspeção em bloqueio espúrio —
# e bloqueio espúrio é o que ensina a desligar o gate.
ignora 'ssh vps "docker ps"'
# INVARIANTE (contrapeso de enumerar mais ações): a grafia com hífen também tem lado de
# inspeção. Enumerar `docker-compose restart` não pode arrastar `ps`/`logs` com ela.
ignora 'ssh vps "docker-compose ps"'
ignora 'ssh vps "docker logs -f api"'
ignora 'ssh vps "pm2 logs api --lines 50"'
ignora 'ssh prod "pm2 status"'
# INVARIANTE: `pm2` só conta se for o COMANDO (início, ou depois de ;&|) — igual ao make,
# ao vercel e ao bash/sh. O `pm2` era o ÚNICO dos cinco sem âncora, e a assimetria era
# medida no hook real: `git commit -m "conserta o pm2 restart do crm"` e `echo "no
# servidor: pm2 restart api"` saíam exit 2 (suíte inteira disparada por PROSA) enquanto
# `git commit -m "conserta o make deploy"` e `... "o npm run deploy"` saíam exit 0 no
# mesmo run. Bloqueio espúrio em `git commit` é o que ensina a desligar o gate.
ignora 'git commit -m "conserta o pm2 restart do crm"'
ignora 'echo "no servidor: pm2 restart api"'
ignora 'git commit -m "docs: como fazer pm2 reload api"'
# INVARIANTE (contrapeso da âncora): estreitar o pm2 não pode cegar o encadeamento — o
# `pm2 restart` depois de `&&`/`;` é invocação real e segue tendo que bloquear. É este
# caso que proíbe trocar a âncora por `^` puro. (R1 cobre o pm2 no início da linha; o
# padrão de ssh cobre `ssh vps pm2 ...`, com espaço ou com aspa.)
detecta 'cd /app && pm2 restart app'
ignora 'remake deployment'
ignora 'npm run build'
ignora 'git commit -m "vercel deploy --prod agora casa"'  # vercel sem âncora de início
ignora 'rg "vercel deploy --prod" .'                      # busca pelo comando não é o comando
# INVARIANTE (contrapeso do clamp): entre o binário e o `--prod` só pode haver o
# subcomando `deploy` e flags — `logs` é outro subcomando, e ler log de produção é
# comando do dia a dia. É este caso que proíbe alargar o clamp pra "qualquer token".
ignora 'vercel logs api --prod'
# INVARIANTE: `bash`/`sh` só conta se for o COMANDO (início, ou depois de ;&|) — igual
# ao make e ao vercel. Aceitar qualquer espaço antes do interpretador transformava
# prosa que cita "bash deploy.sh" em bloqueio de suite (commit e echo do dia a dia).
ignora 'git commit -m "conserta o bash deploy.sh"'
ignora 'git commit -m "usa sh deploy.sh"'
ignora 'echo "roda o bash deploy.sh"'
# INVARIANTE (contrapeso do terminador alargado): alargar o que pode vir DEPOIS do
# script não pode afrouxar a âncora de ABERTURA. Prosa entre aspas simples cita o
# script com `'` no lugar exato do novo terminador — e segue não sendo invocação.
ignora "git commit -m 'conserta o bash deploy.sh'"
ignora "echo 'roda o ./deploy.sh'"

echo "── Falhas silenciosas do gate ──"

# .cwd ausente não pode fazer o gate evaporar calado.
E=$(cd "$PROBE" && printf '{"tool_input":{"command":"pm2 restart app"}}' | bash "$HOOK" >/dev/null 2>&1; echo $?)
[ "$E" = 2 ] && ok 'payload sem .cwd · cai pro $PWD em vez de apagar o gate' \
             || bad 'payload sem .cwd · cai pro $PWD' "exit 2" "exit $E"

# App pulado por não ter teste tem que FALAR — era exit 0 com zero output.
ERR=$(hook_note "./deploy.sh fantasma" "$MODE1")
case "$ERR" in
  *fantasma*) ok "app sem teste · o gate avisa em vez de pular calado" ;;
  *)          bad "app sem teste · o gate avisa" "additionalContext citando 'fantasma'" "recebido: '${ERR:-<vazio>}'" ;;
esac

echo "── Escopo do Modo 1: quais apps o gate REALMENTE roda ──"

# Baseline: deploy full descobre os apps, deploy nomeado gateia os nomeados.
gateia 'bash tools/deploy.sh'           "$MONO" crm web
gateia 'bash tools/deploy.sh crm web'   "$MONO" crm web
# INVARIANTE: REDIREÇÃO não é nome de app. Os tokens `>` e `/tmp/dep.log` sobreviviam
# ao filtro de ARGS, então um deploy FULL redirecionado ficava com ARGS não-vazio, o
# discover_apps() nunca rodava e o gate liberava TODOS os apps sem um único teste —
# avisando sobre '>' como se fosse app.
gateia 'bash tools/deploy.sh > /tmp/dep.log'          "$MONO" crm web
gateia 'bash tools/deploy.sh 2>&1 | tee /tmp/dep.log' "$MONO" crm web
# INVARIANTE: VALOR de flag não é nome de app. O filtro só descartava o token que
# COMEÇA com `-`, então em `bash tools/deploy.sh --env prod` (deploy FULL com flag) o
# `prod` sobrevivia, virava o ÚNICO "app", não tinha teste — e o gate liberava o deploy
# INTEIRO rodando ZERO teste, só com o aviso de app-sem-gate. Mesma família da redeção.
# Controle no mesmo eixo: a flag com `=` (um token só) já gateava os dois apps.
gateia 'bash tools/deploy.sh --env prod'          "$MONO" crm web
gateia 'bash tools/deploy.sh --tag v1'            "$MONO" crm web
gateia 'bash tools/deploy.sh --site my-project'   "$MONO" crm web
gateia 'bash tools/deploy.sh --env=prod'          "$MONO" crm web
# INVARIANTE: descartar o valor da flag não pode levar o app NOMEADO junto.
gateia 'bash tools/deploy.sh --env prod crm'      "$MONO" crm
# INVARIANTE (contrapeso): deploy de UM app não pode virar deploy full. É o que proíbe
# consertar o caso acima com fallback cego pro discover_apps() — super-gatear o monorepo
# é a dor que o Modo 1 existe pra evitar (rodar suite de app sem relação com o deploy).
LINE=$(hook_note 'bash tools/deploy.sh crm' "$MONO" | grep -F '✅ Gate de testes ok:')
case "$LINE" in
  *crm*web*|*web*) bad "escopo · app nomeado não arrasta o resto do monorepo" \
                       "'✅ Gate de testes ok:' SEM citar web" "$LINE" ;;
  *crm*)           ok  "escopo · app nomeado não arrasta o resto do monorepo" ;;
  *)               bad "escopo · app nomeado não arrasta o resto do monorepo" \
                       "'✅ Gate de testes ok:' citando crm" "${LINE:-<ausente>}" ;;
esac
# INVARIANTE: DUAS invocações no mesmo comando gateiam os DOIS apps. O recorte guloso
# (`.*deploy\.sh`) cortava no ÚLTIMO script: só `web` era testado e o crm subia sem
# teste e sem aviso.
gateia 'bash tools/deploy.sh crm && bash tools/deploy.sh web' "$MONO" crm web
# INVARIANTE: teste de app VERMELHO bloqueia o deploy (exit 2) e a mensagem de bloqueio diz
# QUAL app. É a razão de o hook existir e não tinha um único check: com o `exit 2` do Modo 1
# trocado por `exit 0` — gate que roda o teste, vê vermelho e libera — a suíte seguia
# inteira verde (medido: 55 ok, 0 falhas).
E=$(hook 'bash tools/deploy.sh crm' "$MONO_RED")
LINE=$(hook_err 'bash tools/deploy.sh crm' "$MONO_RED" | grep -F '🚫 Deploy bloqueado')
case "$E:$LINE" in
  2:*crm*) ok "Modo 1 vermelho · teste do app falhando bloqueia o deploy" ;;
  *)       bad "Modo 1 vermelho · teste do app falhando bloqueia o deploy" \
               "exit 2 + '🚫 Deploy bloqueado' citando crm" "exit $E — bloqueio: '${LINE:-<ausente>}'" ;;
esac

echo "── Caminhos de LIBERAÇÃO: todo exit do hook tem um check que fixa o exit code ──"

# INVARIANTE DA CLASSE: todo caminho de SAÍDA do hook precisa de um check que fixe o
# EXIT CODE, não só a mensagem. O idioma fundador desta suíte (fixture PROBE, `make
# test` falhando) mede um eixo só — detectou (exit 2) vs não detectou (exit 0) — então
# "detectou e LIBEROU" era inalcançável e as 4 saídas de liberação do hook não tinham
# um único check. Medido: mutar cada uma das 4 para `exit 2` deixava a suíte com 73 ok,
# 0 falhas, idêntico ao baseline. Check novo escrito no idioma PROBE volta a medir um
# eixo só — se ele mora num caminho de liberação, ASSERTE O EXIT.

# Modo 2 VERDE: suite passa -> deploy liberado. Par com R1 (`detecta 'pm2 restart app'`,
# que roda o MESMO comando contra o PROBE vermelho e exige exit 2): junto, os dois
# provam "detectou E liberou", que nenhum dos dois prova sozinho. O assert é sobre a
# AUSÊNCIA do 🚫 porque o caminho verde do Modo 2 sai calado (stderr vazio, medido).
E=$(hook 'pm2 restart app' "$GREEN")
ERR=$(hook_note 'pm2 restart app' "$GREEN")
case "$E:$ERR" in
  0:*🚫*) bad "Modo 2 verde · suite passando libera o deploy" "exit 0 sem '🚫'" "exit 0 mas bloqueou: '$ERR'" ;;
  0:*)    ok  "Modo 2 verde · suite passando libera o deploy" ;;
  *)      bad "Modo 2 verde · suite passando libera o deploy" "exit 0 (deploy liberado)" "exit $E — stderr: '${ERR:-<vazio>}'" ;;
esac

# Nenhum test runner detectado: fail-open é LEI aqui (patterns.md §fail-open), e é uma
# LIBERAÇÃO — precisa do exit fixado junto do aviso, senão o projeto sem runner passa a
# ter todo deploy bloqueado e a rede não pisca.
E=$(hook 'pm2 restart app' "$NORUNNER")
ERR=$(hook_note 'pm2 restart app' "$NORUNNER")
case "$E:$ERR" in
  0:*"nenhum test runner detectado"*) ok "sem test runner · fail-open com aviso (exit 0)" ;;
  *) bad "sem test runner · fail-open com aviso (exit 0)" \
         "exit 0 + additionalContext citando 'nenhum test runner detectado'" "exit $E — recebido: '${ERR:-<vazio>}'" ;;
esac

# Comando deploy-ish FORA do ./deploy.sh em projeto com gate por-app: o hook libera de
# propósito (rodar a suite legada do repo inteiro num monorepo reprova por app sem
# relação — runtime.md). É liberação DELIBERADA, logo precisa do exit travado.
E=$(hook 'pm2 restart app' "$MONO/tools")
ERR=$(hook_note 'pm2 restart app' "$MONO/tools")
case "$E:$ERR" in
  0:*"Comando fora do ./deploy.sh"*) ok "fora do ./deploy.sh · projeto com gate por-app libera (exit 0)" ;;
  *) bad "fora do ./deploy.sh · projeto com gate por-app libera (exit 0)" \
         "exit 0 + additionalContext citando 'Comando fora do ./deploy.sh'" "exit $E — recebido: '${ERR:-<vazio>}'" ;;
esac

# --- prova anti-tautologia -------------------------------------------------
# Sabota UMA detecção numa cópia do hook e exige que a suíte REPROVE. Sem isto a
# suíte pode estar afirmando nada (o precedente: teste de presença que passava com
# o CSS morto dentro de um comentário). Guardado por env var pra não recursar.
if [ -z "${SUITE_SABOTAGE_RUN:-}" ]; then
  echo "── Prova anti-tautologia ──"
  SAB="$TMP/hook-sabotado.sh"
  # Alvo: o padrão de docker compose LOCAL, que é a única ocorrência da string no
  # arquivo — logo a sabotagem é cirúrgica sem depender de posição de linha.
  sed 's/docker-compose|docker compose/NUNCACASA1|NUNCACASA2/' "$HOOK" > "$SAB"
  # ⚠️ A sabotagem é acoplada ao TEXTO do que ela sabota, então ela apodrece em
  # silêncio quando a regex é reescrita: a versão anterior mirava `)pm2` (do
  # padrão antigo `(^|\s)pm2`), o padrão mudou, o sed parou de alterar QUALQUER
  # coisa, e a "cópia sabotada" virou o original — a suíte passava e o check
  # acusava "a suíte não afirma nada", que era verdade sobre uma cópia intacta.
  # Esta guarda transforma esse modo de falha confuso num erro que se explica.
  if cmp -s "$HOOK" "$SAB"; then
    bad "a sabotagem alterou o hook" "cópia DIFERENTE do original" \
        "sed não casou nada — o alvo da sabotagem saiu do arquivo; retargete-o"
  elif SUITE_SABOTAGE_RUN=1 HOOK_UNDER_TEST="$SAB" bash "${BASH_SOURCE[0]}" >/dev/null 2>&1; then
    bad "hook sabotado reprova a suíte" "suíte vermelha na cópia sabotada" "ela passou — a suíte não afirma nada"
  else
    ok "hook sabotado (detecção do docker compose morta) · a suíte reprova"
  fi
fi

echo ""
printf 'pre-deploy-test-check: %d ok, %d falhas\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
