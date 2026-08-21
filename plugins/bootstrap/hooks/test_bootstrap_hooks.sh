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

  na_maquina_falsa "$REPO3" "$APPLY" > "$TMP/apply.out" 2>&1
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

allow_proibidas() { # -> entradas proibidas que estao no allow, separadas por espaco
  python3 - "$AQUI/../config/settings-defaults.json" <<'PY'
import json, re, sys
allow = json.load(open(sys.argv[1]))["permissions"]["allow"]
# a CLASSE que o SKILL.md:88 recusa, nao a lista das entradas ja removidas: uma
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
print(" ".join(sorted(x for x in allow
                      if re.search(remoto, x) or re.search(remoto_sub, x) or re.search(prefixo, x))))
PY
}
check "nenhum comando remoto nem atribuicao de variavel no allow padrao" "" "$(allow_proibidas)"

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
touch "$CP/pedro-plugins-permissions-ok"
env CLAUDE_CONFIG_DIR="$CP" CLAUDE_PLUGIN_ROOT="$AQUI/.." \
  bash "$AQUI/lib/apply-config.sh" >/dev/null 2>&1
check "com a marca, o allow dos defaults entra inteiro" "$ESPERADO" \
  "$(python3 -c "import json,sys; print(len(json.load(open(sys.argv[1]))['permissions']['allow']))" \
     "$CP/settings.json" 2>/dev/null)"

echo
echo "$OK ok · $FAIL FAIL"
[ "$FAIL" -eq 0 ]
