---
generated: 2026-07-31
generated-commit: 2587006
project: pedro-plugins
scope:
  - plugins/project-doc/hooks/sessionstart-doc.sh
  - plugins/project-doc/hooks/sessionstart-organism.sh
  - plugins/project-doc/hooks/pretooluse-plan-gate.sh
  - plugins/project-doc/hooks/userpromptsubmit-plan-escape.sh
  - plugins/project-doc/hooks/posttooluse-doc-read.sh
  - plugins/project-doc/hooks/lib-project-root.sh
  - plugins/project-doc/hooks/doc-detect.sh
  - plugins/project-doc/hooks/hooks.json
  - plugins/bootstrap/hooks/session-sync.sh
  - plugins/bootstrap/hooks/lib/apply.sh
  - plugins/bootstrap/hooks/lib/snapshot.sh
  - plugins/bootstrap/hooks/lib/git-sync.sh
  - plugins/bootstrap/hooks/hooks.json
  - plugins/bootstrap/hooks/stop-prose-ceiling.py
  - plugins/bootstrap/hooks/stop-forma-relato.py
  - plugins/bootstrap/lib/conformance.py
  - plugins/bootstrap/config/manifest.json
  - plugins/visual/server/visual_server.mjs
  - plugins/visual/server/start.sh
  - plugins/visual/skills/visual/resolve-dir.sh
  - plugins/visual/skills/visual/SKILL.md
  - plugins/visual/hooks/pre-exitplan-visualize.sh
  - plugins/visual/hooks/sessionstart-plan.sh
  - plugins/visual/hooks/stop-plan-status.sh
  - plugins/visual/hooks/hooks.json
  - plugins/visual/lib/plan_state.py
  - plugins/guardrails/hooks/lint-and-typecheck.sh
  - plugins/guardrails/hooks/scope-cop.sh
  - plugins/guardrails/hooks/hooks.json
  - scripts/hook_contract.py
  - plugins/ship/hooks/pre-deploy-test-check.sh
  - plugins/ship/hooks/hooks.json
  - plugins/ship/skills/ship/SKILL.md
  - plugins/context-guard/hooks/context-guard.sh
  - plugins/context-guard/hooks/context-guard-writer.sh
  - plugins/context-guard/hooks/context-guard-reset.sh
  - plugins/context-guard/hooks/hooks.json
  - plugins/handoff/hooks/sessionstart-ata.sh
  - plugins/handoff/hooks/hooks.json
  - plugins/graphify-guard/hooks/sessionstart-graphify.sh
  - plugins/graphify-guard/hooks/pretooluse-graphify-guard.sh
  - plugins/graphify-guard/hooks/hooks.json
  - plugins/slides/skills/slides/SKILL.md
  - plugins/slides/skills/slides/scripts/check_fidelity.py
  - AGENTS.md
  - GEMINI.md
  - .cursorrules
  - .windsurfrules
  - .github/copilot-instructions.md
verified-by:
  - plugins/bootstrap/hooks/test_bootstrap_hooks.sh
  - plugins/bootstrap/lib/test_conformance.py
  - plugins/project-doc/hooks/test_plan_gate.sh
  - plugins/visual/hooks/test_plan_hooks.sh
  - plugins/visual/lib/test_plan_state.py
  - plugins/ship/hooks/test_pre_deploy.sh
doc-sig: pedro-plugins/sessionstart-doc.sh@gen=3.8#5ff772c3
---

# Runtime — fluxos ponta-a-ponta

Este doc descreve **o que acontece em execução**. Estrutura do repo está em `architecture.md`; convenções de código, em `patterns.md`.

**Rótulos:** `[confirmado]` = lido ou executado neste run · `[inferido]` = deduzido do código, não executado · `[relatado]` = veio de comentário/doc do próprio repo e não foi executado aqui.

**Contagem de hooks (derivada mecanicamente neste run**, somando `len(b["hooks"])` sobre cada evento de todos os `plugins/*/hooks/hooks.json`):

```
SessionStart      8
PreToolUse       11
PostToolUse       7
Stop              6
UserPromptSubmit  2
```

⚠️ Isso mede o que o repo **oferece**. O que **roda** é a interseção com `enabledPlugins` do `~/.claude/settings.json` — e nesta máquina `graphify-guard` e `intent-guard` **não estão ligados** (ausentes de `enabledPlugins`), o que bate com o manifest, que os traz `enabled: false`. `[confirmado — leitura de settings.json e jq no manifest nesta rodada]`

---

## 1 · Ciclo de sync do bootstrap (pull → apply → snapshot → commit/push)

**Dispara quando:** `SessionStart`, via `plugins/bootstrap/hooks/hooks.json` → `${CLAUDE_PLUGIN_ROOT}/hooks/session-sync.sh`, **sem `timeout` declarado**. `[confirmado]`

**Passos** (todos em `session-sync.sh` salvo indicação):

1. **Guarda de reentrância** — sai calado se `PEDRO_PLUGINS_HOOK_RUNNING` já está setada; senão exporta `PEDRO_PLUGINS_HOOK_RUNNING=session-sync`. Impede que o PostToolUse `post-plugin-command.sh` (matcher `Bash`) re-dispare o ciclo enquanto ele roda `claude plugin install`. `[confirmado]`
2. **Lock por diretório** — `mkdir "$LOCK_DIR"` em `$HOME/.claude/plugins/.pedro-plugins-sync.lock` (atômico via POSIX, sem `flock`). Lock com mais de 300s é quebrado com `rmdir`. `trap … EXIT INT TERM` libera. Segunda sessão concorrente sai calada. `[confirmado]`
3. **Checagem barata de remoto** — com `$PEDRO_PLUGINS_REPO/.git` presente (`HAS_SOURCE=1`): `git fetch --quiet`, compara `HEAD` com `@{u}` e só marca `REMOTE_ADVANCED=1` se `merge-base --is-ancestor` provar que o remoto está **à frente**, não meramente divergente. Sem repo-fonte, faz o equivalente no cache `~/.claude/plugins/marketplaces/pedro-plugins`. `[confirmado]`
4. **Throttle** — se o remoto não avançou, `PEDRO_PLUGINS_FORCE_SYNC` está vazia e o mtime de `~/.claude/plugins/.pedro-plugins-last-sync` é mais novo que `PEDRO_PLUGINS_THROTTLE_SECONDS` (default `86400`), sai. `[confirmado]`
5. **Pull** — `git pull --rebase --autostash`. Saída casando `conflict|cannot pull` → `rebase --abort` e sai. Falha não-conflito **com `REMOTE_ADVANCED=1`** → aborta **sem** tocar o timestamp, pra próxima sessão tentar na hora. `[confirmado]`
6. **Apply** — `hooks/lib/apply.sh`. Localiza o manifest na primeira das 5 origens: repo-fonte → `${CLAUDE_PLUGIN_ROOT}/config/manifest.json` → `../../config/manifest.json` relativo ao script → cache do marketplace → glob `~/.claude/plugins/cache/pedro-plugins/bootstrap/*/config/manifest.json`. Converge em 4 etapas: `claude plugin marketplace add` dos faltantes → `claude plugin install` → `claude plugin uninstall` → `claude plugin enable/disable`. O estado atual vem de parsear `claude plugin list` com `awk` (blocos `❯ nome@mkt` + `Status:`), deduplicado por `sort -u`. `[confirmado]`
7. **Portão anti-propagação** — `apply.sh` sai com o **número de operações falhas** (`255` = fatal, cap em `200`). Qualquer exit ≠ 0 → `session-sync.sh` **pula o snapshot** e ainda assim faz `touch` no timestamp. `[confirmado]`
8. **Snapshot** — `hooks/lib/snapshot.sh` regenera `plugins/bootstrap/config/manifest.json` a partir de `claude plugin list` + `known_marketplaces.json`, imprime `unchanged`/`changed` no stdout e log no stderr. `[confirmado]`
9. **Commit + push** — só com `SNAPSHOT_STATUS = "changed"`. `hooks/lib/git-sync.sh` faz `git add` e `git commit --only` **apenas** de `plugins/bootstrap/config/manifest.json`, mensagem `chore(plugins): sync <YYYY-MM-DD>`. Push rejeitado (`rejected|non-fast-forward`) → `pull --rebase --autostash` + um retry. `[confirmado]`

**Termina em:** `touch ~/.claude/plugins/.pedro-plugins-last-sync` e `exit 0`. Neste run o arquivo existe com mtime de hoje 18:56 — o ciclo rodou. `[confirmado — `ls -la`]`

### 1a · A remoção é opt-in dos dois lados

- **`apply.sh`, etapa 3** — o laço que decide o que remover é **puro**: monta `UNINSTALL_CANDIDATES`/`UNINSTALL_CANDIDATE_COUNT` sem efeito nenhum. Os `claude plugin uninstall … --keep-data` só rodam dentro de `if [ "${BOOTSTRAP_UNINSTALL_UNMANAGED:-0}" = "1" ]`. Sem a variável, imprime `ℹ desinstalação DESLIGADA — N plugin(s) seriam removidos: …` e não mexe em nada. Racional no cabeçalho do arquivo: a marketplace oficial entrega centenas de plugins e o manifest declara um punhado — sem guarda, um `SessionStart` desinstalaria tudo que o manifest não nomeia. `[confirmado]`
- **`snapshot.sh`, união aditiva** — depois de montar o manifest novo, faz `group_by(.name)` entre plugins antigos e a amostra atual (`if length > 1 then .[1] else .[0] end`: a amostra nova vence no `enabled`, a entrada ausente **fica**) e loga `warning: manifest encolheu X -> Y` se ainda assim diminuir. O comentário do bloco registra a causa: `claude plugin list` devolve saída incompleta de forma intermitente. `[confirmado — código lido; a intermitência é `[relatado]`, não remedida neste run]`
- Consequência prática: desinstalar de verdade é **edição explícita** do manifest de um lado, `BOOTSTRAP_UNINSTALL_UNMANAGED=1` do outro.

### 1b · Chave de topo escrita à mão sobrevive por inversão da lista

`snapshot.sh` declara `GENERATED_KEYS='["version","description","marketplaces"]'` — o que ele **gera** — e preserva com `with_entries(select(.key … | index($k) | not))` toda chave de topo fora dessa lista. As chaves do manifest atual, listadas mecanicamente por `jq -r 'keys[]'`: `description`, `ferramentas_externas`, `marketplaces`, `skills`, `version`. `[confirmado]`

### 1c · Números do manifest (jq neste run)

```
marketplaces ................. 8
entradas de plugin ........... 48   (31 enabled · 17 disabled)
entradas de pedro-plugins .... 19
desligadas em pedro-plugins .. graphify-guard, intent-guard
```

`[confirmado — `jq` sobre plugins/bootstrap/config/manifest.json nesta rodada]`

### Se falhar no passo N

- **2** (outro sync ativo) → sai calado; só aparece com `PEDRO_PLUGINS_VERBOSE`.
- **5** (conflito de pull) → log em stderr mandando `cd $PEDRO_PLUGINS_REPO && git status`; nada mais roda.
- **6** (`jq` ou `claude` ausentes, manifest inválido/ausente) → `exit 255`; `session-sync` loga "apply teve erro fatal — snapshot pulado".
- **7** (N operações falharam) → estado local preservado, sem snapshot e sem push. Retry: `PEDRO_PLUGINS_FORCE_SYNC=1 bash plugins/bootstrap/hooks/session-sync.sh`.
- **9** (push rejeitado ou sem rede) → commit local fica. `git-sync.sh` sai **sempre** 0 — erro de git aqui nunca derruba a sessão. `[confirmado]`

> ⚠️ O ciclo roda `git pull --rebase --autostash` no repo-fonte **em toda abertura de sessão**. Trabalho não-commitado em `pedro-plugins` passa pelo autostash. `[inferido — não reproduzido neste run]`

**Verificado:** `bash plugins/bootstrap/hooks/test_bootstrap_hooks.sh` → **36 ok · 0 FAIL** neste run, incluindo o round-trip do snapshot ("pedro-plugins continua com 19 plugins", "graphify-guard continua desligado", "2a rodada e idempotente"). `[confirmado]`

---

## 2 · Roteamento cross-tool para o CLAUDE.md

**Dispara quando:** outra ferramenta de IA (Codex, Gemini CLI, Cursor, Windsurf, Copilot) abre o repo e carrega o arquivo de instrução que ela conhece.

**Os ponteiros na raiz deste repo**, listados por `ls -a`: `AGENTS.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules`, `.github/copilot-instructions.md`. `[confirmado]`

**Conteúdo real, copiado literal:**

```
AGENTS.md / GEMINI.md  (mesmo bloco de 3 passos)
  1. Read `CLAUDE.md` for the project index — it contains the stack, critical
     gotchas, and a documentation routing table
  2. Based on your current task, read the relevant docs from `.claude/docs/` …
  3. Each doc entry includes "→ read when" hints …

.cursorrules / .windsurfrules / .github/copilot-instructions.md  (par de 2 linhas)
  Read `CLAUDE.md` at the project root for the project index and documentation routing table.
  Detailed docs by concern are in `.claude/docs/` — load only what's relevant to the current task.
```

O índice carrega o marker `<!-- project-doc:v2 gen=3.8 -->` na primeira linha. `[confirmado — `head -1 .claude/CLAUDE.md`]`

> ⚠️ **Os 5 ponteiros mandam ler `CLAUDE.md` "at the project root", e este repo NÃO tem `CLAUDE.md` na raiz** — o índice vive em `.claude/CLAUDE.md`. `[confirmado — `ls CLAUDE.md` → "No such file or directory"]`
>
> O Claude Code acha o índice sozinho (`.claude/CLAUDE.md` é convenção nativa). Cursor/Copilot/Codex/Gemini seguem a instrução literal, não acham nada na raiz e caem em varredura. **Os ponteiros estão inertes fora do Claude Code neste repo.** Correção: criar `CLAUDE.md` na raiz — `doc-detect.sh:find_claude_md` já prefere a raiz quando ela carrega o marker — ou reescrever os 5 ponteiros pro caminho real.

---

## 3 · Ponte StatusLine ↔ arquivo de estado do context-guard

**Dispara quando:** o Claude Code renderiza a statusLine e, do outro lado, em **todo** `PostToolUse` (o `hooks.json` do context-guard não declara `matcher`). Ambos com `timeout 5`. `[confirmado]`

**Passos:**

1. **Escrita** — `context-guard-writer.sh` recebe o JSON da statusLine em stdin, extrai `.context_window.used_percentage` e `.session_id` via `jq` e grava o percentual cru em `/tmp/claude-context-pct-<session_id>`. Sem `session_id` → não grava (fail-safe). `[confirmado]`
2. **Encaminhamento** — com `CLAUDE_STATUSLINE_FORWARD` setada, repassa o mesmo stdin: `printf '%s' "$INPUT" | eval "$CLAUDE_STATUSLINE_FORWARD"`. `[confirmado]`
3. **Leitura** — `context-guard.sh` lê `/tmp/claude-context-pct-<session_id>`, trunca o decimal (`PCT_INT="${PCT%.*}"`) e compara com `CLAUDE_CONTEXT_THRESHOLD` (default `80`). `[confirmado]`
4. **Disparo** — acima do threshold, emite `{"decision":"block","reason":"⚠️ CONTEXTO EM N%. Rode o /handoff AGORA …"}` e cria o sentinel `/tmp/claude-context-warned-<session_id>` (1× por sessão). `[confirmado]`
5. **Não interromper handoff em curso** — antes de tudo, testa `(.tool_input // {} | tostring) | test("handoff"; "i")`; casando, marca o sentinel e sai. `[confirmado]`
6. **Kill-switch** — `~/.claude/context-guard/mode` contendo `off` desliga o guard globalmente. `[confirmado]`
7. **Reset** — `context-guard-reset.sh` (SessionStart) apaga **só** os dois arquivos da própria sessão e faz prune de órfãos com `find /tmp -maxdepth 1 -name 'claude-context-pct-*' -mtime +1 -delete` (idem `-warned-`). `[confirmado]`

> ⚠️ **A ponte segue DESLIGADA nesta máquina, e a metade que falta é a do meio.** As env vars **existem** — `sorted(settings['env'].keys())` devolve `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`, `CLAUDE_CONTEXT_THRESHOLD` (=`80`), `CLAUDE_STATUSLINE_FORWARD`. Mas `statusLine.command` **não contém `context-guard-writer`**: aponta direto pro `claude-hud`. Sem o wrapper na cadeia, ninguém escreve `/tmp/claude-context-pct-<sid>` — o único arquivo desse padrão em `/tmp` é `claude-context-pct-smoke-123`, de 30/jul. `context-guard.sh` sai em `[ -z "$PCT" ] && exit 0`. **Implementado e habilitado, mas inativo aqui.** `[confirmado — leitura de ~/.claude/settings.json e `ls /tmp/claude-context-pct-*` nesta rodada]`
>
> Ativar = rodar a skill `context-guard:setup`, que registra o wrapper como `statusLine.command` e move o comando antigo pra `CLAUDE_STATUSLINE_FORWARD`.

- **Passo 3, `jq` ausente** → `command -v jq … || exit 0` no topo: o guard nem lê o stdin. `[confirmado]`

---

## 4 · Live-sync do /visual e o gate no ExitPlanMode

**Dispara quando:** (a) o usuário invoca `/visual`, ou (b) o `PreToolUse` em `ExitPlanMode` de `plugins/visual/hooks/hooks.json` → `pre-exitplan-visualize.sh` (**timeout 10**) bloqueia um plano. `[confirmado]`

**Passos:**

1. **Resolução do diretório** — `plugins/visual/skills/visual/resolve-dir.sh` aplica uma cascata de 3: raiz git (`git rev-parse --show-toplevel`) → ancestral com marcador, parando antes de `$HOME` e de `/` → fallback `~/Desktop/claude-<sub>`. Os marcadores, copiados literal do script: `package.json`, `CLAUDE.md`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `graphify-out/`, `.git`. O alvo é `<dir>/.claude/<sub>`, onde `<sub>` é o **2º argumento** (default `visual`; o motor de plano passa `plans`). O diretório é criado com `mkdir -p` antes de imprimir. Fonte única: hook, skill e `plan_state.py` chamam **este** script. `[confirmado]`
2. **Token de sessão** — a página injeta `<script>window.VISUAL_SESSION = "<token>";</script>` logo depois de `<body>`; o servidor valida contra `SESSION_RE = /^[a-zA-Z0-9_-]{4,64}$/`. `[confirmado — `visual_server.mjs`; formato do token em `SKILL.md`, seção "Live sync via claude-visual-server"]`
3. **Subir o daemon** — `${CLAUDE_PLUGIN_ROOT}/server/start.sh` pinga `http://127.0.0.1:$PORT/ping` com `curl -sf --max-time 1`; respondeu, sai. Senão exige `node` no PATH e sobe `nohup env CLAUDE_VISUAL_PORT="$PORT" node visual_server.mjs &` + `disown`, esperando até 8 × `sleep 0.25`. Porta: `CLAUDE_VISUAL_PORT`, default `7755`. `[confirmado]`
4. **Daemon** — `plugins/visual/server/visual_server.mjs`, Node stdlib puro, escuta em `127.0.0.1`. Rotas: `GET /ping` → `{status,pid,port}`; `POST /state` com body `{session, docTitle?, state}`; `GET /state?session=<id>`. Corpo acima de `MAX_BODY_SIZE` (256 KB) → HTTP 413. `EADDRINUSE` → `process.exit(0)` silencioso. Auto-desligamento por ociosidade em `IDLE_TIMEOUT_MS` (30 min), checado a cada minuto. `[confirmado]`
5. **Escrita de estado** — no `POST /state`, valida a sessão, monta `{session, timestamp, docTitle, state}` e grava `~/.claude/visual-state/<session>.json` **e** `~/.claude/visual-state/latest.json` (mesmo registro + campo `stateFile`). Sessão fora do regex → HTTP 400 `invalid-session`, nada gravado, sem path traversal. `[confirmado]`
6. **Leitura pelo Claude** — o Claude lê `~/.claude/visual-state/latest.json`; ausente ou com mais de 30 min → volta pro copy/paste. `[confirmado — regra na SKILL.md, seção de live sync]`

**Estado nesta máquina:** o daemon **não está no ar** agora (`curl http://127.0.0.1:7755/ping` falhou) e `latest.json` existe com mtime de 30/jul 22:32. **Implementado, ocioso.** `[confirmado]`

### 4a · O gate do ExitPlanMode, condição por condição

`pre-exitplan-visualize.sh` — kill-switch `VISUAL_GATE=0` na primeira linha; `command -v jq` logo abaixo; sem `session_id` → `exit 0`. Cap de **3** devoluções por (sessão, projeto), chaveado por `${TMPDIR:-/tmp}/claude-visual-gate-$(id -u)-${SESSION_ID}-${PHASH}` com `PHASH` = `cksum` do diretório resolvido. `[confirmado]`

- **Procura o visual da sessão** — `find "$VISUAL_DIR" -maxdepth 1 -name "*sess-${SESSION_SHORT}*.html" -mmin -5`, com `SESSION_SHORT="${SESSION_ID:0:8}"`.
- **Gate de prova** — conta com `grep -c` os marcadores `class="decision-card`/`class="feedback-item` (DECIDE), `class="evidencia"`/`class="artefato"`/`<pre` (PROVA), `class="evidencia vazio` (VAZIO) e `visual-sem-evidencia:` (ISENTO). Bloqueia com `exit 2` se `DECIDE>0 && ISENTO==0 && (PROVA==0 || VAZIO>0)`.
- **Gate de arquivo de plano** — roda `plan_state.py --dir "$PLANS_DIR" open --json`; saída vazia ou `[]` → `HAS_PLAN_FILE=0` e `exit 2` mandando rodar `init`. Sem `python3` ou sem o script, `HAS_PLAN_FILE=1` (não cobra).
- **Sem visual nenhum** → `exit 2` com o conteúdo literal de `.tool_input.plan` no stderr e o filename sugerido `<YYYY-MM-DD>-sess-<8char>-plan.html`.

**Três gates disputam o `ExitPlanMode`** neste marketplace, cada um em seu `hooks.json`: `visual/hooks/pre-exitplan-visualize.sh`, `intent-guard/hooks/plan-gate.sh` e `project-doc/hooks/pretooluse-plan-gate.sh` (que também cobre `EnterPlanMode`). O registro dos três é `[confirmado]`; a ordem de execução entre plugins **não é determinável a partir deste repo**.

**Verificado:** `bash plugins/visual/hooks/test_plan_hooks.sh` → **OK (33 checks)** neste run. `[confirmado]`

---

## 5 · Ciclo de vida de um plano de implementação

**Onde mora:** `<raiz-do-projeto>/.claude/plans/<id>.plan.json`, versionado no git de propósito — `/tmp` e `${CLAUDE_PLUGIN_ROOT}` morrem no `/clear` e no bump de versão. `[confirmado — docstring de `plan_state.py`]`

**A regra estrutural:** o Claude **autora** o plano uma vez (`init`) e daí em diante só **marca** (`tick`). Quem desenha a árvore é o programa, lendo o arquivo — por isso o título não deriva entre renders. `[confirmado]`

**Verbos** (subparsers de `plan_state.py:build_parser`): `init`, `tick`, `state`, `render`, `page`, `brief`, `open`, `close`, `reopen`.

### Os quatro símbolos de maior fan-in

- **`PlanError`** — a exceção única do módulo. `main()` a captura, escreve a mensagem no stderr e devolve **2**; qualquer outra exceção sobe como traceback. Todo caminho de recusa do módulo passa por ela: JSON inválido, plano inexistente, `resolve-dir.sh` ausente ou mudo, `template.html` não encontrado, tique de fase, tique sem prova, `state … done`, renomear sem `--rename`. É o motivo de um hook conseguir tratar "plano recusado" por exit code, sem parsear texto. `[confirmado]`
- **`resolve_dir(cwd=None)`** — delega ao `skills/visual/resolve-dir.sh` com o 2º argumento `plans`, **em vez de reimplementar a cascata em Python**. Se o script sumir ou não devolver caminho, levanta `PlanError` mandando passar `--dir`. É essa delegação que garante que `/visual` e o store de planos nunca resolvam projetos diferentes. `[confirmado]`
- **`pick_plan(directory, plan_id=None)`** — resolve *qual* plano. Com id, abre `<id>.plan.json` ou levanta `PlanError`. Sem id, exige exatamente **um** plano com `status == "active"`: zero levanta `nenhum plano ativo`, dois ou mais levanta `há N planos ativos (…) — diga qual`. Adivinhar aqui é como o plano se perde, e o código recusa adivinhar. Chamado por `tick`, `state`, `render`, `page`, `close` e `reopen`. `[confirmado]`
- **`plan_progress(plan)`** — percorre `iter_items` e devolve `(feitos, total)` contando `status == "done"`. É a métrica única: alimenta o texto do `tick`, o `close` (que decide entre `done` e `abandoned`), o `summary`, os bullets do `brief`, a barra `.pt-fill` do HTML e os chips da página. Fase **não tem estado próprio** — `phase_status` também é derivada dos passos, porque estado duplicado é estado que diverge. `[confirmado]`

### Travas do arquivo

- **`validate`** acumula **todos** os erros de forma e levanta um `PlanError` só. Ids: fase casa `^F\d+$`, passo casa `^F\d+\.\d+$` e o prefixo tem que bater com a fase. `desc` é obrigatório em cada passo e tem teto de `DESC_MAX = 140` chars — é a linha didática que aparece na árvore. `STATUSES = ("todo","doing","blocked","done")`. `[confirmado]`
- **`merge`** mantém o que é **estado** (`status`, `evidence`, `done_at`) e trava o que é **identidade**: título diferente com o mesmo id é conflito e o `init` é recusado, salvo `--rename <id> "<título>"`. Nó que existia no arquivo e não veio no `init` é **mantido**, com aviso. `[confirmado]`
- **`cmd_tick`** recusa tique de fase e recusa prova com menos de `EVIDENCE_MIN = 8` caracteres. `cmd_state` recusa o valor `done` — "done só via tick, que exige prova". `[confirmado]`
- **`cmd_page`** grava a página no **mesmo caminho** por (plano, modo): `plano-<id>-<modo>.html` no diretório do `/visual`. O usuário dá refresh na aba, em vez de acumular arquivos. `[confirmado]`

### Os dois hooks que costuram o plano à sessão

- **`sessionstart-plan.sh`** (SessionStart, timeout 10) — cria o marco `${TMPDIR:-/tmp}/claude-plan-mark-$(id -u)-${SESSION}-${PHASH}` **mesmo sem plano aberto**, e injeta `additionalContext` listando os planos abertos com `done/total`, o próximo passo e o caminho do arquivo. `[confirmado]`
- **`stop-plan-status.sh`** (Stop, timeout 15) — emite `systemMessage` com os bullets de `plan_state.py brief`, nunca `decision:block`. Desliga com `PLAN_STATUS=0`; só a cobrança do tique desliga com `PLAN_NUDGE=0`. A cobrança entra 1× por (sessão, projeto), e **só** quando há marco antigo, nenhum `*.plan.json` foi tocado desde ele e o transcript mostra 3+ chamadas de `Edit|Write|MultiEdit|NotebookEdit`. Se o marco não existe, o hook **cria** o marco e não cobra naquele turno — o comentário registra a regra geral: hook que depende de outro hook ter rodado é frágil, então crie o pré-requisito você mesmo. `[confirmado]`

**Verificado:** `python3 plugins/visual/lib/test_plan_state.py` → **OK** neste run. `[confirmado]`

---

## 6 · Gate de testes pré-deploy do /ship

**Dispara quando:** `PreToolUse` com matcher `Bash`, via `plugins/ship/hooks/hooks.json` → `pre-deploy-test-check.sh`, **timeout 120**. Roda em toda chamada de Bash; só age se o comando parecer deploy. `[confirmado]`

**Portas de entrada, na ordem do arquivo:**

1. `[ "${SHIP_GATE:-1}" = "0" ] && exit 0` — kill-switch.
2. `command -v jq >/dev/null 2>&1 || exit 0` — fail-open de infra, resolvido via PATH.
3. `.tool_input.command` vazio → `exit 0`. `.cwd` ausente → cai pro `$PWD` (era `exit 0`, o que fazia o gate de produção sumir em silêncio).

`[confirmado — cabeçalho e bloco de entrada lidos]`

**Detecção de deploy** — a lista de padrões é o teto real do gate. Duas invariantes de escrita que o cabeçalho documenta e a suíte trava:

- **Âncora de início-de-comando**, pra menção não disparar o gate.
- **`CMDPFX`**, o prefixo legítimo que atravessa a âncora, **enumerado** e não "qualquer palavra antes". Copiado literal do arquivo:

```
CMDPFX='([A-Za-z_][A-Za-z0-9_]*=[^[:space:];&|]*[[:space:]]+|(sudo|nohup|env|time|exec|command)([[:space:]]+-[^[:space:];&|]+)*[[:space:]]+)*'
```

Teto conhecido, escrito no próprio comentário: flag **com valor** no lançador (`sudo -u deploy ./deploy.sh`) não casa. `[confirmado]`

**Canal de saída** — o caminho que **libera** acumula avisos e emite JSON no stdout; o caminho que **bloqueia** usa `exit 2` + stderr. O comentário do arquivo cita a doc do harness: no `exit 0` a saída de um `PreToolUse` vai só pro debug log, e as exceções são `UserPromptSubmit`, `UserPromptExpansion` e `SessionStart`. `[confirmado — comentário lido; a doc do harness é `[relatado]` daqui]`

**A skill é o outro lado da costura:** `plugins/ship/skills/ship/SKILL.md` traz `### 2.5. Rodar Testes (Gate Duro)` e `### 157: Assimetria de enforcement — é DECISÃO, não buraco (2026-07-30)`. O hook é a rede no nível do harness; a skill, a regra no nível do modelo. `[confirmado — headers `###` lidos nesta rodada]`

**Verificado:** `bash plugins/ship/hooks/test_pre_deploy.sh` → **100 ok, 0 falhas** neste run, o último check sendo "hook sabotado (detecção do docker compose morta) · a suíte reprova". `[confirmado]`

---

## 7 · ARRANQUE — o que roda no SessionStart

**Os 8 comandos, derivados mecanicamente** dos `plugins/*/hooks/hooks.json` neste run:

```
plugins/bootstrap/hooks/hooks.json        1  session-sync.sh              (sem timeout)
plugins/branches/hooks/hooks.json         1  sessionstart-branches.sh
plugins/context-guard/hooks/hooks.json    1  context-guard-reset.sh       (5s)
plugins/graphify-guard/hooks/hooks.json   1  sessionstart-graphify.sh     (10s)
plugins/handoff/hooks/hooks.json          1  sessionstart-ata.sh          (10s)
plugins/project-doc/hooks/hooks.json      2  sessionstart-organism.sh, sessionstart-doc.sh  (10s cada)
plugins/visual/hooks/hooks.json           1  sessionstart-plan.sh         (10s)
TOTAL 8
```

**Quantos rodam aqui: 7.** `graphify-guard` não está em `enabledPlugins` desta máquina — nem no manifest, que o traz `enabled: false`. `[confirmado]`

### Ordem

> A ordem de disparo **entre** plugins não é determinável a partir deste repositório: nenhum `hooks.json` declara prioridade e o harness não está aqui. O único ordenamento que o código fixa é **interno ao `project-doc`**: em `plugins/project-doc/hooks/hooks.json` o array `SessionStart[0].hooks` lista `sessionstart-organism.sh` **antes** de `sessionstart-doc.sh`, e o segundo depende disso — ele só reenquadra o texto para "módulos de um organismo" porque, no comentário literal, "o `sessionstart-organism.sh` já deu o banner". `[confirmado]` · Que o harness respeite a ordem do array é `[inferido]`.

### O que cada um injeta

1. **`bootstrap/session-sync.sh`** — não injeta contexto; imprime log de sync. É o cenário 1 inteiro. Todos os caminhos saem 0. `[confirmado]`
2. **`context-guard/context-guard-reset.sh`** — não injeta nada; apaga os dois arquivos `/tmp` da própria sessão e faz prune de órfãos com mais de 1 dia. `[confirmado]`
3. **`graphify-guard/sessionstart-graphify.sh`** — roda `graphify-detect.sh` e, havendo grafo, injeta `additionalContext` com cada projeto e sua frescura (`atualizado, build <data>` ou `⚠️ defasado: N arquivo(s) mudaram desde <data>`), mandando usar `graphify query` antes de grep/Explore. Grafo defasado acrescenta a ordem de oferecer `graphify --update`. Sem grafo, sai calado. **Não roda nesta máquina** (plugin desligado). `[confirmado — código lido; inatividade confirmada por `enabledPlugins`]`
4. **`handoff/sessionstart-ata.sh`** — não injeta contexto. Grava `/tmp/claude-ata-session-<sha1(cwd)[:12]>` com `{session_id, transcript_path, cwd, source}`, porque a skill `handoff` não recebe `session_id` (skill ≠ hook) e o `extract_ata.py --auto` precisa do sentinel pra achar o `.jsonl` certo. O hash tem que ser idêntico ao de `extract_ata.py`. `[confirmado]`
5. **`project-doc/sessionstart-organism.sh`** — exige `jq`, `python3` e `../lib/organism.py`. Roda `organism.py brief <cwd>`; com `.organism == true`, injeta o banner 🧬 com nome, número e nomes dos módulos, a `golden_rule` e as costuras (`• <id> (<severidade>): modA ↔ modB`). Fora de um organismo, sai calado. `[confirmado]`
6. **`project-doc/sessionstart-doc.sh`** — três saídas, todas via `additionalContext`:
   - **projeto documentado** → lista `CLAUDE.md` + nº de docs, com flag `⚠️ DEFASADA` (staleness `stale`) ou `⚠️ staleness indeterminado` (`unknown`) e `⚠️ fora do padrao atual (gen)` quando `pattern_check` reporta `in_pattern=false`;
   - **documentado mas sem nenhum autoral** → nudge `/start-doc gaps`, 1× por (sessão, projeto) via `${TMPDIR:-/tmp}/claude-doc-autoral-nudge-$(id -u)-${SID}-${PHASH}`, desligável com `DOC_AUTORAL_GATE=0`;
   - **sem doc nenhuma** → oferta do `/start-doc` mais o aviso de que o gate de plano vai barrar. Antes de afirmar ausência, o hook **reconsulta a raiz** com `doc-detect.sh --one "$PROJ"`, porque o modo descida não enxerga doc que vive acima do cwd. Os autorais cobrados são `quality-goals constraints context solution-strategy glossary`, mais `design` só quando `has_frontend` retorna verdadeiro. `[confirmado]`
7. **`visual/sessionstart-plan.sh`** — cenário 5. `[confirmado]`
8. **`branches/sessionstart-branches.sh`** — registrado no `hooks.json` do plugin `branches`. `[confirmado — registro; conteúdo não lido nesta rodada]`

**Quem pode bloquear no SessionStart:** nenhum dos 8. Os que falam usam `hookSpecificOutput.additionalContext`; os demais só escrevem em disco ou em stdout/stderr. `[confirmado — leitura dos 6 scripts desta fatia]`

---

## 8 · FALHA — o gate de plano nega por falta de documentação

**Dispara quando:** `PreToolUse` com matcher `EnterPlanMode|ExitPlanMode` → `plugins/project-doc/hooks/pretooluse-plan-gate.sh`, timeout 10. `[confirmado]`

**Portas antes de qualquer julgamento:** `PLAN_DOC_GATE=0` desliga; `command -v jq` fail-open; `project_root` não achou raiz → `exit 0`; **`doc-detect.sh` ilegível → `exit 0`** — helper ausente não é "projeto sem doc", é o gate cego (o comentário registra que um `chmod 000` fazia projeto documentado cair no caso A e ser negado sem cap). `[confirmado]`

**Os quatro desfechos:**

- **CLAUDE.md escrito à mão, sem `.claude/docs/`** → `deny` com cap de 3, mandando ler o arquivo que existe e oferecendo `/start-doc` + `/project-doc` depois do plano. Repo alheio é o caso comum.
- **CASO A · nenhuma documentação** → `deny` **sempre**, sem cap. A mensagem muda conforme já haja autorais (`N de 5 documentos autorais`) ou nenhum.
- **CASO B · tem doc, não foi lida nesta sessão** → `deny` com cap `MAX_NUDGES=3`, listando os `.md` de `.claude/docs/` e acrescentando o aviso de staleness quando o caso.
- **CASO C · tem doc e já foi lida** → `exit 0`, silêncio.

`[confirmado]`

### O escape verbal

`userpromptsubmit-plan-escape.sh` (UserPromptSubmit, timeout 10) é quem ouve a frase, porque hook não lê conversa. Grava `/tmp/claude-plan-gate-escape-${SESSION}-${PHASH}` e injeta `additionalContext` avisando. Três travas escritas no cabeçalho e nas regex:

- **fronteira de palavra obrigatória** (`B='(^|[^[:alnum:]])'`) antes de todo verbo — sem ela, "esta**va sem documentação**" e "con**segue sem doc**" liberavam o gate, e são constatações, não ordens;
- **`EXTERNAL_RE`** descarta "doc **do/da/de** \<coisa\>" — doc de terceiro não é ordem sobre a nossa;
- **ambiguidade resolve pro lado seguro**: casou os dois, não libera; quem quer liberar mesmo assim usa o token inequívoco `--sem-doc` (ou `#sem-doc`). Revogação: `--com-doc` ou "exige a doc", que apaga o sentinel. `[confirmado]`

### O que libera de verdade (CASO B)

`posttooluse-doc-read.sh` (PostToolUse, matcher `Read`) escreve o sentinel `/tmp/claude-doc-guard-${SESSION}-${PHASH}` quando o Claude lê `*/.claude/docs/*`, `*/.claude/CLAUDE.md` ou `*/CLAUDE.md`. Ele também injeta o aviso **no momento do consumo** quando `pattern_check.py --project-staleness` devolve `stale` ou `unknown` — e é PostToolUse, sem `permissionDecision`, logo **estruturalmente incapaz de loopar**. `[confirmado]`

### Por que os dois lados casam: `lib-project-root.sh`

`project_root()` sobe do cwd procurando primeiro `CLAUDE.md`/`.claude/CLAUDE.md`, depois os marcadores `.git package.json pyproject.toml Cargo.toml go.mod .claude`, parando em `/` ou `$HOME`. `project_hash()` é `printf '%s' "$1" | cksum | cut -d' ' -f1`.

**A regra dura, escrita no cabeçalho: NUNCA canonicalize** — nada de `git rev-parse`, `realpath` ou `pwd -P`. `git rev-parse --show-toplevel` devolve `/private/var/…` enquanto o `posttooluse-doc-read.sh` recorta a string do `file_path` e obtém `/var/…`; no macOS isso dá `cksum` diferente e o sentinel de leitura nunca resolveria o gate. A única normalização permitida é remover a barra final, e pelo mesmo motivo. `[confirmado]`

**Verificado:** `bash plugins/project-doc/hooks/test_plan_gate.sh` → **49 passou · 0 falhou** neste run, com o último check sendo "E2E: Read no CLAUDE.md da raiz também libera". `[confirmado]`

---

## 9 · ENCERRAMENTO — o que roda no `Stop`

**Os 6 comandos, derivados mecanicamente** neste run:

```
plugins/bootstrap/hooks/hooks.json    python3 "${CLAUDE_PLUGIN_ROOT}/hooks/stop-prose-ceiling.py"   10s
plugins/bootstrap/hooks/hooks.json    python3 "${CLAUDE_PLUGIN_ROOT}/hooks/stop-forma-relato.py"    30s
plugins/handoff/hooks/hooks.json      ${CLAUDE_PLUGIN_ROOT}/hooks/handoff-completeness-gate.sh      30s
plugins/intent-guard/hooks/hooks.json ${CLAUDE_PLUGIN_ROOT}/hooks/delivery-audit.sh                 60s
plugins/project-doc/hooks/hooks.json  ${CLAUDE_PLUGIN_ROOT}/hooks/stop-doc-touch.sh                 15s
plugins/visual/hooks/hooks.json       ${CLAUDE_PLUGIN_ROOT}/hooks/stop-plan-status.sh               15s
```

`intent-guard` não está ligado nesta máquina, então **5 rodam aqui**. `[confirmado]`

### 9a · O teto de prosa — `stop-prose-ceiling.py`

Mecânico, roda em todo turno, custo zero de token. **Nasce ligado:** `TETO_PADRAO = 6`, e `PROSE_CEILING_MAX` só **ajusta** o número (`0` ou lixo cai no padrão). O único desligamento é `PROSE_CEILING=0`, que derruba o hook inteiro e é visível. O comentário registra por quê: em 2026-07-30 o teto virou opt-in, a variável nunca foi definida e a primeira resposta seguinte já estourou — "premissa que nasce desligada não é premissa, é comentário". `[confirmado]`

Conta linhas de prosa da última mensagem do assistente **descontando** blocos ``` (que são prova e não têm teto) e linhas de tabela/regra. Quatro problemas podem se acumular:

1. `len(prosa) > TETO`;
2. **retórica no meio** — a regex `RETORICA` nomeia os padrões da calibração (`vale notar`, `dito isso`, `em outras palavras`, `o que eu fiz foi`, `deixa eu explicar`, entre outros);
3. **menu de opções no fim** — bullet começando por `opção`/`alternativa`;
4. **NOVO · pergunta fechada sem veredito na 1ª linha.** Três regex trabalham juntas: `PERGUNTA_FECHADA` casa a cauda (últimos 200 chars) do último prompt do usuário; `PERGUNTA_ABERTA` **isenta** quando há pronome interrogativo (`como`, `por que`, `o que`, `qual`…), porque pergunta aberta pede explicação, não sim/não; `ABRE_COM_VEREDITO` exige que a primeira linha não-vazia da resposta comece por veredito — a lista literal inclui `sim`, `nao/não`, `confirmo`, `nenhum`, `zero`, `passou`, `falhou`, `funciona`, `resolvido`, `pronto`, `feito`, `em parte`, `parcial`, `ainda nao`, `confirmado`, `inferido`, `depende`. O comentário do bloco registra o caso real que a originou: a resposta trouxe a varredura inteira com prova, não dizia sim nem não, e a devolutiva foi "você não me respondeu". `[confirmado]`

**Saída:** `exit 2` com a mensagem no stderr. Anti-loop de `MAX_BLOQUEIOS = 2` por resposta, chaveado por `sha1(session_id + texto_inteiro)[:16]` — o hash é do texto **inteiro** porque o output style manda a 1ª linha ser estável, então colisão de prefixo era o caso comum. Estourado o teto de bloqueios, o hook **desiste** e registra em `bypass.log` em vez de travar a sessão. `[confirmado]`

**Rastro:** `batida()` grava **toda** execução, não só as que barram, em `CLAUDE_DIR/state/prose-ceiling/batidas.log`. `CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))` — mesma regra do `conformance.py:CLAUDE_DIR` e do `scope-cop.sh`. Sem isso, "não rodou" e "rodou e aprovou" eram indistinguíveis. `[confirmado]`

### 9b · O juiz de forma do relato — `stop-forma-relato.py` (novo nesta rodada)

Vizinho deliberadamente diferente do teto: **chama um modelo**, então só roda quando a resposta é um **relato**. Nenhum padrão distingue "6 linhas densas" de "6 linhas vazias" — para isso precisa de um leitor. `[confirmado — docstring]`

- **Gatilho (`e_relato`)** — precisa de pelo menos um bloco ``` **e** `len(prosa) >= MIN_PROSA` com `MIN_PROSA = 2`. O comentário justifica o 2: o relato canônico bom tem 2 linhas de prosa e 4 de prova; exigir 4 deixava passar justamente os relatos que dão certo. Resposta curta e conversa não chegam ao modelo — seriam a maioria dos turnos, a ~4,5s cada.
- **O que julga** — só a FORMA, em quatro critérios nomeados no `PROMPT`: limpeza, clareza, didática, escaneabilidade. Bloco de código é **prova**: não conta como excesso e a ausência dele não reprova.
- **Protocolo** — `claude -p --model <FORMA_RELATO_MODEL>` (default `haiku`), `timeout=TIMEOUT_S` (25s), entrada truncada em `texto[:6000]`. Espera uma linha: `PASSA` ou `REPROVA: <defeito em até 12 palavras>`.
- **Recursão** — o filho herda os hooks deste marketplace e chamaria o juiz de novo; o pai injeta `FORMA_RELATO="interno"` no ambiente do subprocesso, e o `main()` sai **sem nem gravar batida** nesse modo. `FORMA_RELATO=0` é o kill-switch do dono e **grava** batida.
- **Fail-open total** — `claude` ausente do PATH, `TimeoutExpired`, `OSError`, `returncode != 0`, saída vazia ou veredito ilegível: tudo devolve `(True, motivo)`. "Guarda que trava a sessão por infra é pior que guarda nenhum."
- **Anti-loop** — `MAX_BLOQUEIOS = 2` por resposta, contador em arquivo chaveado por `sha1(session_id + texto)[:16]`, verificado **antes** de gastar o modelo.
- **Estado com variável própria** — `ESTADO = FORMA_RELATO_STATE` ou `CLAUDE_DIR/state/forma-relato`. O comentário explica a separação: isolar o teste via `CLAUDE_CONFIG_DIR` tirava a credencial do `claude -p` junto, e o juiz passava a aprovar tudo por fail-open.
- **Bloqueio** — `exit 2` com "FORMA DO RELATO REPROVADA: \<motivo\>", mandando reescrever o relato inteiro (não anexar resumo no fim) e lembrando que o que não couber vira `/visual` em HTML.

`[confirmado — arquivo lido integralmente]`

**Teto conhecido, escrito na própria docstring:** com um `CLAUDE_CONFIG_DIR` sem credencial, `claude -p` sai com `rc=1` e "Not logged in", e o juiz cai no fail-open sem barrar nada. O motivo fica na batida como `juiz sem resposta`, e é assim que se descobre que ele está mudo em vez de aprovando. `[relatado — medição citada no arquivo, não reproduzida aqui]`

**Estado do rastro nesta máquina** (`~/.claude/state/`, contado mecanicamente por script neste run):

```
forma-relato/batidas.log   {'sem texto': 12}                              mtime 31/jul 18:46
prose-ceiling/batidas.log  {'aprovou': 6, 'sem texto do assistente': 36}
prose-ceiling/bypass.log   não existe
```

Ou seja: **os dois hooks estão executando**, o teto de prosa já aprovou 6 respostas e nunca precisou do bypass, e o juiz **ainda não julgou nenhum relato** — todas as 12 batidas dele são `sem texto`, o caminho em que `ultima_msg_assistente` não achou texto do assistente no transcript. Não há nenhuma batida `nao e relato` nem `julgou`. `[confirmado — contagem por script nesta rodada; a causa do `sem texto` não foi investigada aqui]`

---

## 10 · Conformidade: descobrir que um guarda está MUDO

**Dispara quando:** o passo 2 da skill `bootstrap:setup` roda `plugins/bootstrap/lib/conformance.py` — que **confere e não conserta**.

Dois checks fazem a mesma pergunta sobre guardas diferentes, e ambos só cobram de quem tem `bootstrap@…` ligado em `enabledPlugins` (numa máquina sem o plugin não há guarda pra rodar, e acusar ali seria desvio inventado):

- **`check_teto_rodou`** — lê `CLAUDE_DIR/state/prose-ceiling/batidas.log`. Arquivo ausente → desvio "o guarda de prosa nunca executou". Última batida com mais de 24h → desvio "está mudo há N h". Senão, conforme com o resumo por motivo. A docstring registra o caso que o originou: uma resposta de 9 linhas passou às 09:21 e o primeiro registro de bloqueio era das 09:36 — como só existia log de bloqueio, "não rodou" e "rodou e aprovou" eram indistinguíveis e o check chegou a carimbar "nenhuma resposta furou o teto" com o guarda mudo.
- **`check_juiz_rodou`** (novo nesta rodada) — lê `CLAUDE_DIR/state/forma-relato/batidas.log`. Tem **um modo de falha a mais** que o guarda mecânico, e é ele que o check existe pra pegar: soma as batidas cujo motivo começa com `juiz sem resposta` e, se esse total superar as batidas `julgou`, acusa **"o juiz está mudo: N execução(ões) sem resposta do modelo"**, com o conserto apontando a causa comum (credencial: `claude -p` sai com `rc=1` e 'Not logged in'; teste `claude -p --model haiku ok`). Arquivo ausente → desvio cujo conserto manda conferir se `stop-forma-relato.py` está no array `Stop` de `plugins/bootstrap/hooks/hooks.json`, "hook fora dele é ignorado em silêncio e `claude plugin validate` passa mesmo assim". Mais de 24h sem batida → "está mudo há N h".

Ambos usam o helper `le_batidas(log)`, que devolve `(contagem por motivo, idade da última em horas, resumo legível)`. `check_bypass_teto` lê o `bypass.log` e transforma o teto conhecido do hook — desistir após 2 bloqueios — em número visível. `[confirmado — `conformance.py` lido no bloco `le_batidas`…`check_bypass_teto`, e a lista de checks registrada no fim do arquivo]`

**Versão do plugin nesta rodada:** `bootstrap` em **1.8.5**. `[confirmado — `plugins/bootstrap/.claude-plugin/plugin.json`]`

**Verificado:** `python3 plugins/bootstrap/lib/test_conformance.py` → **59 ok · 0 FAIL** neste run. A suíte cobre o juiz em quatro checks nomeados: "acusa juiz que nunca executou", "acusa fail-open por juiz sem resposta", "acusa juiz parado ha mais de 24h" e "nao cobra juiz de quem nao instalou o bootstrap". `[confirmado]`

---

## 11 · Varredura de contrato dos hooks

`scripts/hook_contract.py` mede as **5 propriedades** que separam um gate saudável de um que trava ou se desliga sozinho, tal como enumeradas no cabeçalho:

```
1. canal de saída  — como o hook fala (bloqueia? informa? só loga?)
2. cap anti-loop   — quem bloqueia tem teto de devoluções, escopado por sessão?
3. kill-switch     — dá pra desligar sem editar o arquivo?
4. binário fixo    — usa caminho absoluto de ferramenta?
5. fail-open       — guarda a ausência das ferramentas que usa?
```

Os três canais de bloqueio coexistem hoje e o script **não normaliza, só mede**: `exit 2` (intent-guard, visual), `permissionDecision:"deny"` (project-doc, guardrails) e `"decision":"block"` (handoff). Cap conta em duas formas — contador (`-ge` perto de um `exit 0`, dentro de `CAP_ESCAPE_WINDOW = 8` linhas) e sentinela (`[ -f "$SENTINEL" ]` e variantes). O cabeçalho é explícito sobre a direção do erro: detectar um cap que não existe é o erro caro, porque o script deixaria de acusar um gate que trava de verdade.

Uso: `--json` para a medida crua, `--fail-on high` para virar gate (exit 1), `--baseline f.json` para ver só o que piorou. ⚠️ O próprio cabeçalho classifica: **isto é grep sofisticado, não verdade** — o achado vem com linha e trecho para a conferência custar segundos. `[confirmado — cabeçalho e blocos de regex lidos; script não executado nesta rodada]`

---

## 12 · Guardrails: o que acontece a cada Edit/Write

`plugins/guardrails/hooks/hooks.json` registra 4 hooks — 3 em `PreToolUse` e 1 em `PostToolUse`:

- **`PostToolUse` `Edit|Write` → `lint-and-typecheck.sh`** (30s). Kill-switch `LINT_GATE=0`; `jq` via PATH com fail-open. JS/TS: sobe a árvore procurando `node_modules/.bin/eslint` e depois `tsconfig.json`/`jsconfig.json` — buscas **independentes**, porque em monorepo as raízes podem diferir. O comentário registra a armadilha corrigida: capturar o exit code **antes** do pipe, porque `$(cmd | head)` reporta o status do `head` e o bloco de erro nunca disparava. Python: `ruff` + `mypy`, ambos opcionais. `[confirmado — cabeçalho e bloco JS/TS lidos; corpo Python não lido]`
- **`PreToolUse` `Edit|Write` → `scope-cop.sh`** (25s). Kill-switch `SCOPE_COP_GATE=0` **antes de ler o stdin**. Decisão durável em `$CFG/guardrails/scope-cop.mode` com conjunto **fechado** `deny | warn | off` (vazio = default `deny`); grafia errada cai no default e vai pro log, porque errar a grafia entregaria o gate mais severo a quem pediu o mais brando. `CFG = ${CLAUDE_CONFIG_DIR:-$HOME/.claude}` — mesma regra do `conformance.py` e do `stop-prose-ceiling.py`, e o comentário explica: com `$HOME` cravado, o hook leria o modo numa pasta e o conformance varreria `**/*.mode` noutra. Circuit breaker `MAX_STREAK=3` **por sessão** (`scope-cop.blockstreak.<session_id>`), com poda de arquivos de sessões mortas com mais de 1 dia. Filtro barato antes de chamar modelo: só julga `*.html *.htm *.svelte *.css *.scss *.sass *.less *.tsx *.jsx *.vue *.astro`. `[confirmado — primeiras ~110 linhas lidas]`
- **`PreToolUse` `Agent` → hook do tipo `prompt`** — é o único hook `type: "prompt"` deste marketplace: um classificador que **permite** o spawn quando o input tem `team_name` (é Agent Teams), **nega** quando não tem e o prompt exige Agent Teams/TeamCreate/waves/swarm, e **permite** na dúvida. `[confirmado — prompt lido literal no hooks.json]`
- **`PreToolUse` `AskUserQuestion` → `askq-humanize.sh`** (10s). `[confirmado — registro; conteúdo não lido nesta rodada]`

---

## 13 · Geração de deck pelo /slides

**Sem hooks — é skill pura:** `plugins/slides/` contém apenas `lib/` e `skills/`. `[confirmado — `ls plugins/slides/`]`

Dois modos com contratos de conteúdo **opostos**, e a skill manda decidir qual antes de tudo: **A · transcrição** (renderiza fiel um `.md` já redigido, regra de ouro "o texto é do autor") e **B · explicador** (a skill autora a didática). Pedido ambíguo → perguntar, não chutar. `[confirmado — `SKILL.md`, seção "Dois modos de uso (despacho)"]`

No modo A a regra de ouro deixou de ser instrução e virou propriedade da construção: quem transcreve é `lib/md2deck.py`, e o texto de corpo sai dos tokens do `.md` sem passar por geração. As únicas strings criadas pelo compilador são os enumeradores (`01`, `02`) e o eyebrow derivado dos headings. `[confirmado — SKILL.md]`

**Gate de fidelidade** — `scripts/check_fidelity.py <deck.html> <fonte.md>` extrai cada bloco de texto do deck e confere se aparece literalmente na fonte, normalizando acento, pontuação e caixa (`norm()` usa NFKD + remoção de combining chars). Só examina `BLOCK_TAGS = {"li","p","h3","h4"}` e as divs de classe `pull statement def ex lead sub`; `h1`/`h2` ficam de fora porque título de slide deriva do heading por natureza. `MIN_WORDS = 6` — abaixo disso é rótulo, não prosa do autor. Exit 1 se houver suspeita, 0 se limpo. É exatamente esse conjunto de isenções que faz um deck **compilado** passar por construção. `[confirmado — docstring e constantes de topo lidas]`

---

## 14 · graphify-guard: aviso no arranque, `deny` na primeira busca cega

**Registrado, desligado nesta máquina.** `plugins/graphify-guard/hooks/hooks.json` declara `SessionStart` → `sessionstart-graphify.sh` (10s) e `PreToolUse` com matcher `Grep|Glob|Bash` → `pretooluse-graphify-guard.sh` (10s). O plugin não está em `enabledPlugins` e o manifest o traz `enabled: false`. `[confirmado]`

O guard de busca: kill-switch `GRAPHIFY_GATE=0` antes do stdin; `command -v jq` fail-open. Monta a lista de diretórios candidatos a partir do `cwd` mais o `.tool_input.path` (Grep/Glob) ou os tokens que existem como caminho no comando (Bash). Em `Bash`, só intercepta busca cega de texto/arquivo — a regex exige `grep|egrep|fgrep|rg|ripgrep|ag|ack|find` com fronteira de palavra, e tudo o mais (inclusive `graphify …`) passa. Havendo grafo, nega uma vez por sessão e redireciona pro `graphify query`. `[confirmado — primeiras ~45 linhas lidas]`

O caso que o cabeçalho nomeia como coberto é o do monorepo-container: mesmo com o cwd num diretório sem grafo próprio, ele desce pelos tokens de caminho da busca até achar grafo em subprojeto. `[relatado — comentário do arquivo; não reproduzido]`

---

## Pendências

- **Ponteiros cross-tool inertes** (cenário 2): os 5 arquivos apontam pra um `CLAUDE.md` na raiz que não existe. `[confirmado]`
- **Ponte do context-guard desligada nesta máquina** (cenário 3): env vars presentes, `context-guard-writer.sh` fora do `statusLine.command`. `[confirmado]`
- **Juiz de forma sem nenhum julgamento registrado** (cenário 9b): 12 batidas, todas `sem texto`. O hook executa; o texto do assistente não está chegando a ele nas execuções registradas. Causa não investigada nesta rodada. `[confirmado — o fato; a causa é lacuna aberta]`
- **Ordem entre plugins no mesmo evento**: não determinável a partir deste repositório. Só a ordem **interna** ao array de um `hooks.json` é fixada aqui, e mesmo assim depender dela é `[inferido]`.
- **Conteúdo não lido nesta rodada**, citado só pelo registro: `plugins/branches/hooks/sessionstart-branches.sh`, `plugins/handoff/hooks/handoff-completeness-gate.sh`, `plugins/intent-guard/hooks/delivery-audit.sh`, `plugins/project-doc/hooks/stop-doc-touch.sh`, `plugins/guardrails/hooks/askq-humanize.sh`, `plugins/bootstrap/hooks/post-plugin-command.sh` e `plugins/bootstrap/hooks/lib/apply-config.sh`.
