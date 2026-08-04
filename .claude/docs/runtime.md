---
generated: 2026-08-04
generated-commit: cf642e4
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
  - plugins/visual/skills/visual/template.html
  - plugins/visual/hooks/pre-exitplan-visualize.sh
  - plugins/visual/hooks/sessionstart-plan.sh
  - plugins/visual/hooks/stop-plan-status.sh
  - plugins/visual/hooks/stop-anuncio-sem-acao.py
  - plugins/visual/hooks/hooks.json
  - plugins/visual/lib/plan_state.py
  - plugins/visual/lib/cobertura.py
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
  - plugins/visual/hooks/test_anuncio_sem_acao.py
  - scripts/test_hook_contract.py
  - plugins/visual/hooks/test_exitplan_gate.sh
  - plugins/visual/lib/test_plan_state.py
  - plugins/visual/lib/test_cobertura.py
  - plugins/ship/hooks/test_pre_deploy.sh
doc-sig: pedro-plugins/sessionstart-doc.sh@gen=3.8#a76b4e86
---

# Runtime — fluxos ponta-a-ponta

Este doc descreve **o que acontece em execução**. Estrutura do repo está em `architecture.md`; convenções de código, em `patterns.md`.

**Rótulos:** `[confirmado]` = lido ou executado neste run · `[inferido]` = deduzido do código, não executado · `[relatado]` = veio de comentário/doc do próprio repo e não foi executado aqui.

**Contagem de hooks (derivada mecanicamente neste run**, somando `len(b["hooks"])` sobre cada evento de todos os `plugins/*/hooks/hooks.json`):

```
SessionStart      8
PreToolUse       13
PostToolUse       7
Stop              8
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

> ✅ **A ponte foi LIGADA em 2026-08-02, e ela ficou quebrada 3 dias sem ninguém notar.** Até então `statusLine.command` apontava direto pro `claude-hud` e **não continha `context-guard-writer`**: sem o wrapper na cadeia ninguém escrevia `/tmp/claude-context-pct-<sid>`, e o único arquivo desse padrão em `/tmp` era `claude-context-pct-smoke-123` — **fixture de teste**, de 30/jul. O `context-guard.sh` saía em `[ -z "$PCT" ] && exit 0` toda vez.
>
> O conserto pôs o comando antigo **inteiro** em `CLAUDE_STATUSLINE_FORWARD` (preservando o cálculo de `COLUMNS`, que se perderia num forward remontado à mão) e o writer em `statusLine.command`. E2E com o payload do harness: writer gravou `73` e o hud renderizou `Context 73%` na mesma passada. `[confirmado nesta rodada]`
>
> 🔴 **A lição não é o conserto, é o tempo que levou.** Este bloco já descrevia o defeito **antes** desta rodada, e ele continuou lá — porque documentar um estado quebrado não conserta nem avisa de novo. Agora quem cobra é `conformance.py:check_statusline_meio_ligada`: plugin de statusLine habilitado e ausente da cadeia vira desvio a cada execução do verificador. Ver `patterns.md §1.14` — elo que produz dado para outro consumir sai de cena sem sintoma nenhum na tela.

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

**Passo 0, desde 2026-08-02: o spec passa pela régua de forma antes de virar HTML.** `visual_page.py:validate` roda `erros_de_estilo()` sobre todo campo de texto — título, corpo, pergunta, aviso, sumário — e devolve **todos** os erros de uma vez. Estourar é `exit 2` **sem escrever arquivo**, então o passo 1 nem começa. As quatro checagens e a calibração estão em `patterns.md §2.7`. Duas isenções declaradas: `evidencia.output` e `raw_html`. `[confirmado — `visual_page.py:validate`; `test_visual_page.py` cobre com 25 checks]`

⚠️ **A página aberta no navegador não sabe que ficou velha.** A aba mostra o arquivo de quando foi aberta, e nada na tela denuncia — em 2026-08-02 um bloco aparecia expandido numa aba de 8 horas antes, com o arquivo já corrigido no disco. O daemon sincroniza **browser → disco** (estado de rádio e textarea), nunca o contrário: **não há recarga automática**. Antes de tratar o que se vê na tela como defeito do gerador, confira o HTML no disco. `[confirmado — `restoreState()` no `template.html` mexe em rádios e textareas, nunca em `details.open`]`

### 4a · O gate do ExitPlanMode, condição por condição

`pre-exitplan-visualize.sh` — kill-switch `VISUAL_GATE=0` na primeira linha; `command -v jq` logo abaixo; sem `session_id` → `exit 0`. Cap de **3** devoluções por (sessão, projeto), chaveado por `${TMPDIR:-/tmp}/claude-visual-gate-$(id -u)-${SESSION_ID}-${PHASH}` com `PHASH` = `cksum` do diretório resolvido. `[confirmado]`

- **Procura o visual da sessão** — `find "$VISUAL_DIR" -maxdepth 1 -name "*sess-${SESSION_SHORT}*.html" -mmin -5`, com `SESSION_SHORT="${SESSION_ID:0:8}"`.
- **Gate de prova** — conta com `grep -c` os marcadores `class="decision-card`/`class="feedback-item` (DECIDE), `class="evidencia"`/`class="artefato"`/`<pre` (PROVA), `class="evidencia vazio` (VAZIO) e `visual-sem-evidencia:` (ISENTO). Bloqueia com `exit 2` se `DECIDE>0 && ISENTO==0 && (PROVA==0 || VAZIO>0)`.
  - ⚠️ **`class="feedback-item pt-phase` fica FORA da conta de DECIDE** (`grep … | grep -vc`). É o veredito de fase que o próprio `plan_state.py page --mode approve` desenha — controle de aprovação de trabalho que ainda **não** aconteceu, não conclusão afirmada. Contá-lo fazia o gate barrar exatamente a página que ele manda gerar duas telas abaixo, e o modelo ficava preso entre duas ordens do mesmo arquivo. `[confirmado — `pre-exitplan-visualize.sh`, e a suíte nova cobre o caso]`
  - ✅ **O marcador de PROVA sobreviveu à troca do bloco de prova para `<details>`**: `visual_page.py:r_evidencia` emite `<details class="evidencia">` (com ` open` quando cabe), e o `grep` do gate procura `class="evidencia"` — casa nas duas formas. `[confirmado — leitura do emissor e do gate nesta rodada]`
  - ⚠️ **O texto de conserto que o gate imprime passou a ensinar um JSON que o `init` ACEITA.** Ele mandava escrever fases e passos só com `desc`; o validador recusa o arquivo inteiro sem `requisito` e `pronto` em toda tarefa nova. Hoje os dois blocos de instrução (o caminho "sem plano em arquivo" e o "sem visual nenhum") trazem o exemplo com o bloco `requisitos` no topo e os quatro campos por passo. `[confirmado]`
- **Gate de arquivo de plano** — roda `plan_state.py --dir "$PLANS_DIR" open --json`; saída vazia ou `[]` → `HAS_PLAN_FILE=0` e `exit 2` mandando rodar `init`. Sem `python3` ou sem o script, `HAS_PLAN_FILE=1` (não cobra).
- **Sem visual nenhum** → `exit 2` com o conteúdo literal de `.tool_input.plan` no stderr e o filename sugerido `<YYYY-MM-DD>-sess-<8char>-plan.html`.

**Três gates disputam o `ExitPlanMode`** neste marketplace, cada um em seu `hooks.json`: `visual/hooks/pre-exitplan-visualize.sh`, `intent-guard/hooks/plan-gate.sh` e `project-doc/hooks/pretooluse-plan-gate.sh` (que também cobre `EnterPlanMode`). O registro dos três é `[confirmado]`; a ordem de execução entre plugins **não é determinável a partir deste repo**.

**Verificado:** `bash plugins/visual/hooks/test_plan_hooks.sh` → **OK (33 checks)** neste run, e a suíte nova do próprio gate, `bash plugins/visual/hooks/test_exitplan_gate.sh` → **OK (12 checks)** — ela fecha com kill-switch e fail-open (*"VISUAL_GATE=0 cala tudo"*, *"sem session_id, não bloqueia"*). `[confirmado]`

---

## 5 · Ciclo de vida de um plano de implementação

**Onde mora:** `<raiz-do-projeto>/.claude/plans/<id>.plan.json`, versionado no git de propósito — `/tmp` e `${CLAUDE_PLUGIN_ROOT}` morrem no `/clear` e no bump de versão. `[confirmado — docstring de `plan_state.py`]`

**A regra estrutural:** o Claude **autora** o plano uma vez (`init`) e daí em diante só **marca** (`tick`). Quem desenha a árvore é o programa, lendo o arquivo — por isso o título não deriva entre renders. `[confirmado]`

**Duas portas cobram o plano, e desde 2026-08-02 elas cobrem casos opostos** `[confirmado — `plugins/visual/hooks/`]`:

- **Antes do plano existir** — `PreToolUse[ExitPlanMode]` (`pre-exitplan-visualize.sh`) exige arquivo de plano + HTML com prova. Só arma **se você entrar em plan mode**.
- **Depois do trabalho acontecer** — `Stop` (`stop-plan-status.sh:155-191`) cobra o plano **ausente**: sessão que editou ≥ `PISO` arquivos **distintos** e não tem nenhum plano ativo recebe o aviso uma vez, com sentinela própria (`claude-plan-missing-…`).

O segundo nasceu de um buraco medido: **7 commits em 2026-08-02 sem plano nenhum, e nada acusou** — porque o gate antigo só dispara em plan mode, e trabalho feito direto nunca passa por lá.

⚠️ **A métrica é ARQUIVO distinto, não chamada de edição** (`arquivos_editados()`, linha 82, compartilhada pelas duas cobranças). O caminho antigo contava `"name":"Edit"` no transcript e a frase dizia *"editou N arquivos"* — 6 edições no mesmo arquivo imprimiam *"editou 6 arquivos"*. A mensagem mentia. `[confirmado — `test_plan_hooks.sh` → `OK (46 checks)`, com o caso "6 edições no MESMO arquivo não cobram" e três sabotagens]`

**Verbos** (os **11** subparsers de `plan_state.py:build_parser`): `init`, `tick`, `state`, `render`, `page`, `brief`, `cobertura`, `reabrir`, `open`, `close`, `reopen`. Os dois últimos a entrar são `cobertura` (o mapa entre requisito e tarefa, nos dois sentidos) e `reabrir` (derruba uma decisão que o agente tomou no lugar do dono). `[confirmado — leitura de `build_parser` nesta rodada]`

**As duas árvores.** `render` e `page` aceitam `--vista execucao|valor`. A de execução é fase → tarefa, a de sempre; a de **valor** é épico → requisito → grupo → tarefa e é **derivada em tempo de render**, não guardada — o arquivo só conhece fase→tarefa, e os dois níveis de cima vêm do documento de requisitos. A vista entra no nome do arquivo da página (`plano-<id>-<modo>-valor.html`), então as duas convivem sem uma sobrescrever a outra. `[confirmado — `plan_state.py:cmd_render`, `cmd_page` e `_html_valor`]`

**De onde vêm os requisitos** — cascata de `plan_state.py:_requisitos_do_projeto`, nesta ordem: bloco `requisitos` no topo do próprio plano → variável `PLAN_REQS` apontando um arquivo → `<raiz>/docs/PRD.md` → `<raiz>/docs/REQUISITOS.md` → nenhum. **Nenhum não é erro**: sem documento, a checagem de citação simplesmente não roda. O bloco no plano vem primeiro por ser o mais específico. `[confirmado]`

### Os quatro símbolos de maior fan-in

- **`PlanError`** — a exceção única do módulo. `main()` a captura, escreve a mensagem no stderr e devolve **2**; qualquer outra exceção sobe como traceback. Todo caminho de recusa do módulo passa por ela: JSON inválido, plano inexistente, `resolve-dir.sh` ausente ou mudo, `template.html` não encontrado, tique de fase, tique sem prova, `state … done`, renomear sem `--rename`. É o motivo de um hook conseguir tratar "plano recusado" por exit code, sem parsear texto. `[confirmado]`
- **`resolve_dir(cwd=None)`** — delega ao `skills/visual/resolve-dir.sh` com o 2º argumento `plans`, **em vez de reimplementar a cascata em Python**. Se o script sumir ou não devolver caminho, levanta `PlanError` mandando passar `--dir`. É essa delegação que garante que `/visual` e o store de planos nunca resolvam projetos diferentes. `[confirmado]`
- **`pick_plan(directory, plan_id=None)`** — resolve *qual* plano. Com id, abre `<id>.plan.json` ou levanta `PlanError`. Sem id, exige exatamente **um** plano com `status == "active"`: zero levanta `nenhum plano ativo`, dois ou mais levanta `há N planos ativos (…) — diga qual`. Adivinhar aqui é como o plano se perde, e o código recusa adivinhar. Chamado por `tick`, `state`, `render`, `page`, `close` e `reopen`. `[confirmado]`
- **`plan_progress(plan)`** — percorre `iter_items` e devolve `(feitos, total)` contando `status == "done"`. É a métrica única: alimenta o texto do `tick`, o `close` (que decide entre `done` e `abandoned`), o `summary`, os bullets do `brief`, a barra `.pt-fill` do HTML e os chips da página. Fase **não tem estado próprio** — `phase_status` também é derivada dos passos, porque estado duplicado é estado que diverge. `[confirmado]`

### Travas do arquivo

- **`erros_do_plano` acumula, `validate` levanta.** A checagem de forma é uma função que **devolve a lista** (`plan_state.py:erros_do_plano`) e uma casca fina que a transforma em `PlanError` único (`plan_state.py:validate`). A separação existe porque quem MARCA precisa distinguir defeito da própria tarefa de defeito alheio, e a exceção derruba tudo junto. Ids: fase casa `^F\d+$`, passo casa `^F\d+\.\d+$` e o prefixo tem que bater com a fase. `desc` é obrigatório em cada passo e tem teto de `DESC_MAX = 140` chars — é a linha didática que aparece na árvore. `STATUSES = ("todo","doing","blocked","done")`. `[confirmado]`
- **Dois campos são cobrados só em tarefa NOVA** — o parâmetro `exigir` de `erros_do_plano` recebe o conjunto de ids que estão entrando, e para esses exige `requisito` (o id do requisito que a tarefa atende, **exatamente um**) e `pronto` (como se prova que ela terminou). Tarefa que já existia no arquivo não é cobrada retroativamente, então o campo novo não invalida plano em andamento. `[confirmado]`
- **Citação a requisito inexistente RECUSA gravar.** `validate` recebe `reqs` e, para cada tarefa com `requisito` preenchido, exige que o id exista no documento — a mensagem de erro lista os ids conhecidos. `reqs` vazio **desliga a checagem**, porque projeto sem documento de requisitos é o caso comum, não um defeito. `[confirmado]`
- **`pendencia` trava o tique, e quem destrava é o REGISTRO.** Enquanto a pergunta estiver em aberto, `cmd_tick` recusa com *"tem decisão em aberto"*. O que resolve é `decidido` com uma `escolha` preenchida — **apagar a `pendencia` deixou de ser o caminho**, e essa era a trava permanente: o `merge` preservava o campo omitido, então a pendência voltava no `init` seguinte e a tarefa nunca mais passava. A pergunta continua gravada de propósito; é dela que o `reabrir` vive. `plan_state.py:cmd_reabrir` faz o caminho de volta — devolve a pergunta ao campo `pendencia`, remove o `decidido` e joga a tarefa de volta pra `todo`, pra que toda decisão tomada na ausência do dono seja reversível por construção. `[confirmado — `plan_state.py:cmd_tick`, leitura nesta rodada]`
- **`merge`** mantém o que é **estado** (`status`, `evidence`, `done_at`) e trava o que é **identidade**: título diferente com o mesmo id é conflito e o `init` é recusado, salvo `--rename <id> "<título>"`. Nó que existia no arquivo e não veio no `init` é **mantido**, com aviso. `[confirmado]`
- **A regra do `merge` virou UMA só: o que o `init` não trouxe vem do arquivo.** Valia para uma lista fixa de campos no nó e para `created`/`status` no topo — e por isso o segundo `init` apagava, calado, o bloco `requisitos` (a fonte que as tarefas citam, e com ela o portão que recusa citação para o nada), o `closed_at` e o `detail` da fase. Hoje a preservação vale para **toda chave de topo** e inclui o `detail`, que é o único lugar do 🔧 Como / 💡 Por quê / 📁 Toca em. **Apagar de propósito é declarar a chave vazia** (`"requisitos": []`) — o merge só preenche o ausente. `[confirmado — `plan_state.py:merge`]`
- **`init` recusa `status: "done"` com prova abaixo de `EVIDENCE_MIN`.** Quem escreve o JSON do `init` é o modelo, e sem isso "concluído" entrava à mão com `evidence` nula — o mesmo palpite que o `tick` recusa. O teto da prova é o mesmo dos dois lados, senão há dois. `[confirmado — `plan_state.py:erros_do_plano`]`
- **Plano ilegível DIZ qual arquivo e qual erro.** `plan_state.py:le_plano` é a única porta de leitura e converte `OSError`/JSON inválido em `PlanError` com o caminho e a causa, em vez de traceback com rc=1. Quem LISTA (`list_plans`) segue engolindo: um arquivo torto não pode derrubar a listagem dos outros. `[confirmado]`
- **`cmd_tick`** recusa tique de fase e recusa prova com menos de `EVIDENCE_MIN = 8` caracteres. `cmd_state` recusa o valor `done` — "done só via tick, que exige prova". `[confirmado]`
- **A prova também tem teto de FORMA, desde 2026-08-03: texto corrido é recusado.** `cmd_tick` barra quando `len(ev) > BULLET_MAX` (140) **e** `prova_bullets(ev)` devolve menos de 2 pedaços — ou seja, um parágrafo num bloco só. A mensagem manda separar com ` · `, `; `, ` + ` ou quebra de linha, e diz o que continua isento: **saída crua de um comando passa inteira**, porque o teto vale só para o texto redigido. `[confirmado — `plan_state.py:cmd_tick`, linha 594]`
- **`prova_bullets`** não inventa corte: quebra a prova **só** nos separadores que quem escreveu já usou (`\n`, ` · `, `; `, ` + `) e devolve os pedaços sem o marcador. Prova de um segmento só continua um bullet — quem barra a linha corrida longa é o `tick`, no momento de gravar, **não** o renderizador. `[confirmado — `plan_state.py:prova_bullets`]`
- **A prova sai em bullets nas três superfícies.** `_detalhe` devolve `prova:` mais uma linha `· <pedaço>` por bullet quando há mais de um; a árvore de texto imprime essas linhas e `plan_state.py:_detalhe_html` as converte em `<ul class="pt-prova">` nas **duas** páginas (execução e valor), em vez de colapsar tudo num `<span>`. Um plano de trinta passos com um parágrafo colado a cada título não se lê — foi essa a queixa que abriu o assunto. `[confirmado — `_detalhe`, `_detalhe_html` e as duas chamadas no montador de HTML]`
- **O validador passou a morder no `tick`, mas só pela tarefa ticada.** Até então ele só rodava no `init`, e por isso um `desc` de 356 chars sobreviveu num plano cujo teto é 140. Agora `cmd_tick` chama `erros_do_plano`, filtra com `plan_state.py:_erro_e_do_no` os erros que citam **aquele** nó e **só esses bloqueiam**; defeito em outra tarefa vira aviso no stderr (os 3 primeiros). É fail-open deliberado: bloquear precisa de evidência sobre o alvo, senão uma tarefa torta congelaria o plano inteiro. A tradução posição↔id é necessária porque `erros_do_plano` prefixa com `fase[i] passo[j]`, que são posições, não ids. `[confirmado]`
- **`cmd_tick` fecha o requisito em RELATÓRIO, não em estado.** Quando a tarefa ticada era a última daquele `requisito`, o comando imprime o critério de aceite do documento e a ordem de conferir — mas o requisito **não ganha campo `status`**, pelo mesmo motivo pelo qual a fase não tem estado próprio: estado duplicado é estado que diverge. E o motor não verifica critério de aceite, ele **lembra**; quem confere é o usuário. `[confirmado]`
- **`cmd_page`** grava a página no **mesmo caminho** por (plano, modo, vista): `plano-<id>-<modo>.html` na vista de execução e `plano-<id>-<modo>-valor.html` na de valor, no diretório do `/visual`. O usuário dá refresh na aba, em vez de acumular arquivos — e o sufixo da vista existe porque sem ele as duas árvores do mesmo plano gravariam no mesmo arquivo e a última apagaria a outra em silêncio. `[confirmado]`
- **`--mode approve` só existe na vista de execução.** O veredito Manter/Mudar/Remover mora na FASE, e a vista de valor desenha épico › requisito › grupo: a página saía com a caixa de fechamento, os dois botões e **zero** item revisável, e o "Aprovar tudo" devolvia uma aprovação que ninguém deu. `cmd_page` recusa a combinação antes de montar qualquer coisa, dizendo onde aprovar (`--vista execucao`) e como só ler o eixo de valor (`--mode track`). `[confirmado]`
- **A vista de valor sem nenhum requisito declarado DIZ isso** em vez de sair em branco. `plan_state.py:_sem_eixo` reconhece a situação (há tarefa, não há citação a requisito nenhum — o estado de 14 de 14 planos reais medidos), a página abre com o aviso e as tarefas são desenhadas sob um nó **"sem requisito"**, agrupadas por `grupo`. A lista de ids "tarefas sem requisito" não se repete nesse caso: a árvore acima já é ela inteira. Sair vazia num plano de 157 tarefas afirmava, por omissão, que não havia trabalho. `[confirmado — `_render_valor` e `_html_valor`]`
- **A linha de baixo do item tem uma regra só, `plan_state.py:_detalhe`**, lida pelas duas vistas e pelos dois formatos: prova quando o passo está feito, `⛔ falta decidir: …` quando uma decisão trava o tique, linha didática no resto. Enquanto eram duas cópias, a pendência era invisível justo na vista em que o dono aprova — o motor recusava o tique por um bloqueio que a página nunca tinha mostrado. `[confirmado]`

### Quando a pendência aparece no meio da execução

A regra de quem decide é do modelo, não do programa: mora em `plugins/visual/skills/visual/SKILL.md`, seção "Motor de decisão". Em sessão **interativa** a pendência sempre para e vai ao usuário — com o parecer junto, quando há. Em execução **autônoma**, três perguntas convocam um segundo parecer, e qualquer "sim" basta: a ação é irreversível (remoto publicado, migração de banco, apagar dado, envio a terceiro); contradiz a norma que o requisito cita; ou o repositório não desempata sozinho. `[confirmado — leitura da seção nesta rodada]`

Empate se resolve **por natureza, nunca por contagem de votos** — quem escreveu o plano não vota. Divergência sobre **fato** vira medição: roda e cola a saída (`por: "medicao"`, saída crua no campo `prova`). Divergência sobre **mérito** vai ao usuário no modo interativo e, no autônomo, segue a opção **mais reversível** (`por: "mais-reversivel"`), com a decisão obrigatoriamente no topo do relatório final. O registro vai no campo `decidido` da tarefa e guarda a pergunta original, pra que `plan_state.py reabrir` consiga restaurá-la. `[confirmado]`

### Os dois hooks que costuram o plano à sessão

- **`sessionstart-plan.sh`** (SessionStart, timeout 10) — cria o marco `${TMPDIR:-/tmp}/claude-plan-mark-$(id -u)-${SESSION}-${PHASH}` **mesmo sem plano aberto**, e injeta `additionalContext` listando os planos abertos com `done/total`, o próximo passo e o caminho do arquivo. Desde esta rodada ele acrescenta uma linha `🔎 Cobertura requisito↔tarefa:` com as **duas primeiras linhas** de `plan_state.py --dir "$PLANS_DIR" cobertura` — o resumo e o aviso de "nenhum documento de requisitos encontrado". O comentário do arquivo dá o motivo de o número entrar aqui e não pelo `brief`: este hook monta o texto a partir do `open --json` e não passa pelo `brief`, e sem isso o número apareceria só no fim do turno, *"e não no começo da sessão, que é justamente quando o Claude novo decide o que fazer"*. Saída vazia (2+ planos ativos, nenhum plano) não acrescenta nada — fail-open como o resto do hook. `[confirmado — leitura do script nesta rodada]`
- **`stop-plan-status.sh`** (Stop, timeout 15) — emite `systemMessage` com os bullets de `plan_state.py brief`, nunca `decision:block`. Desliga com `PLAN_STATUS=0`; só a cobrança do tique desliga com `PLAN_NUDGE=0`. A cobrança entra 1× por (sessão, projeto), e **só** quando há marco antigo, nenhum `*.plan.json` foi tocado desde ele e o transcript mostra 3+ chamadas de `Edit|Write|MultiEdit|NotebookEdit`. Se o marco não existe, o hook **cria** o marco e não cobra naquele turno — o comentário registra a regra geral: hook que depende de outro hook ter rodado é frágil, então crie o pré-requisito você mesmo. `[confirmado]`

  ⚠️ **O marco também decide se o resumo pode AFIRMAR, e desde 2026-08-02 ele só é repassado ao `brief` quando é antigo.** Marco recém-criado significa "não sei", nunca "a sessão não tocou nada": nenhum plano pode ser posterior a um marco que acabou de nascer, então repassá-lo faria o primeiro turno de toda sessão cair no caminho errado. `[confirmado — `stop-plan-status.sh`, a guarda `[ "$MARCO_NOVO" = "0" ]`]`

  🔴 **A FORMA do resumo, canonizada em 2026-08-03 — o canal é TEXTO, não markdown.** `systemMessage` chega literal no terminal: `**` e crase viram ruído na tela, não destaque. Foi relatado com print, e valia para três emissores (o resumo do plano, a cobrança do tique e o aviso de push de branch). O que substitui cada um `[confirmado]`:

  | o que dava destaque | o que dá agora |
  |---|---|
  | `**Título**` | posição + emoji do estado (`📍` afirma · `📋` relata · `✅` conclui · `🏁` encerra) |
  | `**Feito:**` `**Agora:**` `**Falta:**` | `✅ Feito:` · `🔄 Agora:` · `⬜ Falta:` — o **mesmo** vocabulário do `MARK` da árvore |
  | `` `comando` `` | o comando cru, sem crase |

  ⚠️ **Duas linhas em branco abrem a mensagem, e elas são do CANAL, não do texto.** O harness prefixa `Stop says: ` na primeira linha: sem elas o cabeçalho grudava no prefixo, num nível diferente dos bullets. A primeira desce o cabeçalho, a segunda separa o bloco do texto do turno. Ficam no hook — `brief` chamado na mão não deve abrir em branco. **Não entram no orçamento**: `_linhas_visiveis` só conta linha com conteúdo, e o total segue em 6. `[confirmado — 49 checks em `test_plan_hooks.sh`]`

  ⚠️ **A suíte deste resumo não testa por ÍNDICE.** Sete checks liam `L[1]`, `L[2]`, `L[3]` e quebraram **duas vezes no mesmo dia** sem nenhuma mudança de comportamento — só porque o layout ganhou emoji e uma linha em branco. Agora procuram o bullet pelo rótulo (`bullet(linhas, "Falta")`). Regra geral: **teste de artefato de leitura casa CONTEÚDO, nunca posição.**

  🔴 **QUAL plano o resumo mostra: a marca de sessão, desde 2026-08-03.** O hook passa `--sessao "$SESSION"` ao `brief`, e é isso que faz o resumo ser **desta** sessão. Antes a escolha era por data de escrita do arquivo, e `mtime` diz que **alguém** mexeu, nunca **quem** — num projeto com frentes paralelas (6 sessões abertas no mesmo repositório em 2026-08-03) a vizinha marcando um passo empurrava o plano dela para o topo do fim de turno de todo mundo. Relatado com print de produção duas vezes antes de virar código. Três estados `[confirmado — 48 checks em `test_plan_hooks.sh`, e medição pelo hook real com duas sessões]`:

  | a sessão… | o cabeçalho | qual plano |
  |---|---|---|
  | marcou **este** plano | 📍 `Onde estamos` — afirma | o dela, no topo |
  | marcou **outro** | 📍 `Onde estamos` | o **dela**, não o mexido por último |
  | não marcou **nada** | 📋 `Plano aberto no projeto` — relata | o mais recente, sem afirmar |

  A marca vive em `plan_state.py:save()` — **não** em cada comando —, então `tick`, `state`, `init` e `close` já nascem cobertos e comando novo também. Formato: `<TMPDIR>/claude-plan-sessao-<uid>-<sid>-<sha1(abspath do dir de planos)[:12]>`, com o id do plano dentro. A chave é calculada por **uma** função (`_sentinel_sessao`), usada por quem escreve e por quem lê: chave computada em dois lugares diverge, e sentinel que nunca casa é pior que sentinel nenhum — a mesma armadilha do `cksum` sobre path canonicalizado que já mordeu este repo (§1.5 de `patterns.md`). Com o id em mãos, **ausência de marca também é informação**: nada liga a sessão àqueles planos, então o cabeçalho recua em vez de afirmar. Chamada sem `--sessao` (hook de versão antiga) cai no critério de marco, como antes.

- **`stop-anuncio-sem-acao.py`** (Stop, timeout 20) — **novo em 2026-08-02**, e o único do `visual` que emite `decision:block`. Devolve o turno que termina prometendo a próxima etapa sem executá-la. Três condições, todas necessárias: há plano ativo com passo em aberto, o texto final promete em 1ª pessoa (`sigo para`, `vou seguir`, `prossigo com`…) e **não** espera o usuário (pergunta no fim ou `posso seguir`/`quando você mandar` desarmam). Cap de 2 devoluções por (sessão, projeto) além do cap nativo do harness; kill-switch `ANUNCIO_ACAO=0`; toda passagem vira linha em `~/.claude/state/anuncio-acao/batidas.log`. `[confirmado — 38 checks em `test_anuncio_sem_acao.py`, a maioria de casos que NÃO podem armar]`

  ⚠️ **O sinal NÃO é "o turno não chamou ferramenta".** No `Stop` isso é trivialmente verdade — o evento dispara porque a última mensagem foi texto. No caso que originou o hook o tique **aconteceu** (`plano 5/41`) e só depois veio o `Sigo para F2`. Medido nos transcripts de origem: 2 de 2 fechamentos com anúncio pararam, contra 0 de 42 sem anúncio. ⚠️ **Teto conhecido e deliberado:** a detecção é lexical, então promessa fora dos padrões passa — o falso NEGATIVO foi preferido, porque devolver turno legítimo custa mais caro. O `batidas.log` existe para medir se o léxico está largo ou estreito demais.

### O fio requisito↔tarefa — quatro estados, e onde cada um aparece

`plugins/visual/lib/cobertura.py` cruza o documento de requisitos com as tarefas do plano e nomeia quatro situações, nenhuma silenciosa: **coberto**, **tarefa sem requisito** (trabalho que ninguém pediu), **requisito sem tarefa** (pedido que ninguém planejou) e **citação a requisito que não existe**. Os três primeiros são relatório; o quarto é erro que recusa gravar. `[confirmado — `cobertura.py:mapa` e `plan_state.py:validate`]`

O número **aparece sem ser pedido**, em quatro superfícies, todas lendo a mesma `cobertura.py:resumo` pra que um só programa calcule:

- no **começo da sessão**, pela linha que o `sessionstart-plan.sh` injeta;
- no **fim do turno**, por `plan_state.py:brief_lines` — e ali ele **toma o lugar** do bullet "Falta", nunca vira um 4º, porque o teto de 3 bullets é do pedido. Só entra quando há tarefa sem requisito ou citação inexistente; a cobrança do tique, quando existe, ganha o slot;
- no **cabeçalho da árvore de valor**, texto e HTML;
- sob demanda, em `plan_state.py cobertura` (com `--json` pra consumo por programa e `--reqs` pra apontar outro documento). `[confirmado — leitura das quatro chamadas]`

**Verificado:** `python3 plugins/visual/lib/test_plan_state.py` → **OK** (252 asserções `ok`, contra 173 na rodada anterior — a diferença é a prova em bullets, com o último check sendo "prova de um segmento continua span") e `python3 plugins/visual/lib/test_cobertura.py` → **OK** (13), ambas nesta rodada. `[confirmado — `grep -c '^  ok'` sobre a saída de cada uma]`

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
7. **`visual/sessionstart-plan.sh`** — cenário 5. Injeta `additionalContext` com os planos abertos, o próximo passo, o caminho do arquivo e a linha de cobertura requisito↔tarefa; sem plano aberto sai calado, mas **o marco em `TMPDIR` é criado antes disso**. `[confirmado]`
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

**Os 8 comandos, derivados mecanicamente** neste run:

```
plugins/bootstrap/hooks/hooks.json    python3 "${CLAUDE_PLUGIN_ROOT}/hooks/stop-prose-ceiling.py"      10s
plugins/bootstrap/hooks/hooks.json    python3 "${CLAUDE_PLUGIN_ROOT}/hooks/stop-regua-relato.py"       10s
plugins/bootstrap/hooks/hooks.json    python3 "${CLAUDE_PLUGIN_ROOT}/hooks/stop-forma-relato.py"       30s
plugins/handoff/hooks/hooks.json      ${CLAUDE_PLUGIN_ROOT}/hooks/handoff-completeness-gate.sh         30s
plugins/intent-guard/hooks/hooks.json ${CLAUDE_PLUGIN_ROOT}/hooks/delivery-audit.sh                    60s
plugins/project-doc/hooks/hooks.json  ${CLAUDE_PLUGIN_ROOT}/hooks/stop-doc-touch.sh                    15s
plugins/visual/hooks/hooks.json       ${CLAUDE_PLUGIN_ROOT}/hooks/stop-plan-status.sh                  15s
plugins/visual/hooks/hooks.json       python3 "${CLAUDE_PLUGIN_ROOT}/hooks/stop-anuncio-sem-acao.py"   20s
```

`intent-guard` não está ligado nesta máquina, então **7 rodam aqui**. `[confirmado]`

⚠️ **A ordem DENTRO do array do `bootstrap` é deliberada:** `stop-regua-relato.py` (mecânico, custo zero) vem **antes** de `stop-forma-relato.py` (que chama modelo). Barrar por forma dos bullets não deve custar uma chamada de LLM. `[confirmado — `plugins/bootstrap/hooks/hooks.json`]` · Que o harness respeite a ordem do array é `[inferido]`, como em todo lugar deste doc.

⚠️ **Hook Python registrado sem `python3` na frente depende do bit de execução sobreviver ao empacotamento**, e um `CLAUDE_PLUGIN_ROOT` com espaço no caminho o quebra em silêncio. Os três acima chamam o interpretador e citam o caminho entre aspas — é o padrão, não estilo. `[confirmado]`

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

### 11a · `--stop-budget` — o custo somado do fim de turno

**Novo em 2026-08-02.** As 5 propriedades acima medem cada hook **isolado**; nenhuma mede o CONJUNTO. **Oito** hooks disputam o `Stop` neste marketplace, cada um respeitando o próprio teto, e o dono viu na tela `6/9 · 35s · ↓773 tokens` com quatro blocos de progresso de plano. Todo emissor estava dentro do que prometia — **o conjunto é que não tinha dono**.

```bash
python3 scripts/hook_contract.py --stop-budget       # humano
python3 scripts/hook_contract.py --stop-budget --json
python3 scripts/hook_contract.py --stop-budget --baseline .claude/stop-budget.baseline.json
```

Saída desta rodada `[confirmado]`:

```
bootstrap     stop-prose-ceiling.py            0 linha(s)   timeout=10s
bootstrap     stop-regua-relato.py             0 linha(s)   timeout=10s
bootstrap     stop-forma-relato.py             0 linha(s)   timeout=30s
handoff       handoff-completeness-gate.sh     0 linha(s)   timeout=30s
intent-guard  delivery-audit.sh                1 linha(s)   timeout=60s
project-doc   stop-doc-touch.sh                0 linha(s)   timeout=15s
visual        stop-plan-status.sh              5 linha(s)   timeout=15s
visual        stop-anuncio-sem-acao.py         0 linha(s)   timeout=20s
TOTAL: 6 linha(s) · teto de referência: 6

Instalados nesta máquina, FORA do gate:
claude-plugins-official  security-guidance 2.0.6     0 linha(s)
impeccable               impeccable 4.0.4            0 linha(s)   timeout=30s
openai-codex             codex 1.0.6                 0 linha(s)   timeout=900s

SOMADO ao que a máquina realmente paga: 6 linha(s)
```

✅ **O emissor novo entrou sem custo de tela.** `stop-regua-relato.py` mede **0 linha** — ele só fala quando barra, e barrar sai por `exit 2` no stderr, fora do orçamento de `systemMessage`. O total continua **6 de 6**, e por isso o gate de deriva não acusou. `[confirmado — `--stop-budget` rodado nesta rodada]`

⚠️ **Plugin de OUTRO marketplace também emite no `Stop`, e até 2026-08-03 não aparecia aqui.** Quem paga o fim de turno é a máquina, não o repositório — instalar o `impeccable` (que registra `PostToolUse` + `Stop`) deixou o buraco visível. Eles entram no relatório e ficam **fora do total gateado**, de propósito: o retrato viaja no git, o que cada máquina instala não, e um total que os incluísse faria o mesmo commit passar numa máquina e barrar noutra. Dois detalhes que só apareceram medindo `[confirmado]`:

- **Mede pelo COMANDO registrado, não por caminho de script.** O hook do `impeccable` é um one-liner de shell que chama `node`, e o regex de `.sh|.py` do laço principal não o alcança. `CLAUDE_PLUGIN_ROOT` é interpolado por eles, então o sandbox aponta essa var para a raiz do plugin instalado — sem isso o hook não acha o próprio script e mede zero pelo motivo errado.
- **Só a versão VIVA entra.** O cache guarda toda versão já instalada; sem filtro o `codex` aparecia duas vezes (1.0.3 e 1.0.6) e o relatório media código morto. O índice vivo está em `installed_plugins.json → ["plugins"]`, **não** na raiz do arquivo. Sem o índice, mede a mais em vez de a menos — esconder emissor é o defeito que este medidor existe pra evitar.

Roda cada emissor num sandbox (`HOME`, `CLAUDE_CONFIG_DIR`, `TMPDIR` e `cwd` temporários) porque emissor de `Stop` escreve estado, e medir não pode sujar a máquina de quem mede.

⚠️ **Ele contava o ENVELOPE, não o texto — corrigido em 2026-08-02.** Emissor de `Stop` imprime `{"systemMessage": "…"}`, e contar a saída crua media três linhas de JSON com o texto inteiro dentro. Um resumo de 5 linhas na tela era reportado como 3, e o teto estava sendo comparado contra um número menor que o real. `_linhas_visiveis()` desembrulha `systemMessage`/`reason`/`additionalContext` antes de contar; texto puro em stderr cai no caminho de baixo, inalterado. **O total no mesmo cenário foi de 4 para 6** — não sobrava, encostava. `[confirmado]`

⚠️ **O sandbox precisa de marcador de projeto, e o `HOME` tem que ficar FORA dele.** `resolve-dir.sh` aplica a cascata raiz-git → marcador → `~/Desktop`, e a busca por marcador **para ao chegar no `HOME`**. Com `HOME` == sandbox a cascata caía no Desktop e o medidor lia os planos reais do dono; depois de plantar um `CLAUDE.md`, ela ainda caía no fallback, e os 4 planos que o próprio medidor criava **nunca eram lidos** — o que ele reportava era o aviso de plano AUSENTE, o cenário oposto ao que declara medir. Hoje são dois diretórios irmãos, `lar/` e `projeto/`. `[confirmado]`

⚠️ **Sandbox vazio mede o caso trivial.** Emissor calado num projeto sem nada é o esperado; o que interessa é o pior caso realista. O sandbox nasce povoado com **4 planos ativos e um transcript com 5 edições** — que é o gatilho das cobranças.

**Virou gate em 2026-08-02, e barra a DERIVA, não o número.** `--stop-budget --baseline <retrato>` sai 1 quando o total **sobe** em relação a `.claude/stop-budget.baseline.json`, nomeando quem subiu e quem é emissor novo. Teto absoluto não serviria: o total já está em 6 de 6, então exigir um número barraria o próximo commit que tocasse hook sem nada ter piorado. Retrato ilegível **não** barra. Pendurado no check **E2** do `release-gate.sh`, no mesmo gatilho do E (só quando o commit toca `plugins/*/hooks/`). Recongelar é explícito: `--stop-budget --json > .claude/stop-budget.baseline.json`. `[confirmado — retrato magro devolve rc=1; 6 checks em test_hook_contract.py]`

Uso: `--json` para a medida crua, `--fail-on high` para virar gate (exit 1), `--baseline f.json` para ver só o que piorou. ⚠️ O próprio cabeçalho classifica: **isto é grep sofisticado, não verdade** — o achado vem com linha e trecho para a conferência custar segundos. `[confirmado — cabeçalho e blocos de regex lidos; script não executado nesta rodada]`

⚠️ **O detector de kill-switch só conhecia shell até 2026-08-02.** Os quatro padrões eram todos de `[ "${X:-1}" = "0" ]` e parentes, então **todo guarda escrito em Python era acusado de não ter interruptor que tem** — a regra R3 disparava em falso. Um quinto padrão lê `os.environ.get("X") == "0"`. Alarme falso importa porque treina a ignorar o relatório. `[confirmado — 2 checks em test_hook_contract.py]`

---

## 12 · Guardrails: o que acontece a cada Edit/Write

`plugins/guardrails/hooks/hooks.json` registra 5 hooks — 4 em `PreToolUse` e 1 em `PostToolUse`:

- **`PostToolUse` `Edit|Write` → `lint-and-typecheck.sh`** (30s). Kill-switch `LINT_GATE=0`; `jq` via PATH com fail-open. JS/TS: sobe a árvore procurando `node_modules/.bin/eslint` e depois `tsconfig.json`/`jsconfig.json` — buscas **independentes**, porque em monorepo as raízes podem diferir. O comentário registra a armadilha corrigida: capturar o exit code **antes** do pipe, porque `$(cmd | head)` reporta o status do `head` e o bloco de erro nunca disparava. Python: `ruff` + `mypy`, ambos opcionais. `[confirmado — cabeçalho e bloco JS/TS lidos; corpo Python não lido]`
- **`PreToolUse` `Edit|Write` → `scope-cop.sh`** (25s). Kill-switch `SCOPE_COP_GATE=0` **antes de ler o stdin**. Decisão durável em `$CFG/guardrails/scope-cop.mode` com conjunto **fechado** `deny | warn | off` (vazio = default `deny`); grafia errada cai no default e vai pro log, porque errar a grafia entregaria o gate mais severo a quem pediu o mais brando. `CFG = ${CLAUDE_CONFIG_DIR:-$HOME/.claude}` — mesma regra do `conformance.py` e do `stop-prose-ceiling.py`, e o comentário explica: com `$HOME` cravado, o hook leria o modo numa pasta e o conformance varreria `**/*.mode` noutra. Circuit breaker `MAX_STREAK=3` **por sessão** (`scope-cop.blockstreak.<session_id>`), com poda de arquivos de sessões mortas com mais de 1 dia. Filtro barato antes de chamar modelo: só julga `*.html *.htm *.svelte *.css *.scss *.sass *.less *.tsx *.jsx *.vue *.astro`. `[confirmado — primeiras ~110 linhas lidas]`
- **`PreToolUse` `Agent` → hook do tipo `prompt`** — é o único hook `type: "prompt"` deste marketplace: um classificador que **permite** o spawn quando o input tem `team_name` (é Agent Teams), **nega** quando não tem e o prompt exige Agent Teams/TeamCreate/waves/swarm, e **permite** na dúvida. `[confirmado — prompt lido literal no hooks.json]`
- **`PreToolUse` `AskUserQuestion` → `askq-humanize.sh`** (10s). `[confirmado — registro; conteúdo não lido nesta rodada]`
- **`PreToolUse` `Edit|Write` → `pretooluse-artefato-regua.py`** (10s) — **novo em 2026-08-03**, e é a PORTA da régua de forma. Bloco próprio no `hooks.json`, com o mesmo matcher do `scope-cop.sh`: são dois julgamentos diferentes sobre a mesma escrita. Detalhe no cenário 15. `[confirmado]`

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

## 15 · A régua de forma recusa no ponto de uso — PORTA e REDE

**Novo em 2026-08-03.** A régua de estilo (`_shared/regua_texto.py`, vendorada; as quatro checagens e os perfis estão em `patterns.md §2.7`) deixou de valer só para quem passa pelo gerador de página. Dois hooks a cobram nos dois canais por onde o texto escapava. `[confirmado]`

**Por que DOIS, e não um** — o motivo está escrito na docstring da porta: *"a rede pega o relatório que eu DIGITO no terminal e nunca vê arquivo; esta porta pega o arquivo e nunca vê o terminal."* Nenhum dos dois alcança o alcance do outro. `[confirmado]`

### 15a · A PORTA — `guardrails/hooks/pretooluse-artefato-regua.py`

**Dispara quando:** `PreToolUse` com matcher `Edit|Write`, timeout 10. `[confirmado]`

1. **Kill-switch primeiro** — `ARTEFATO_REGUA=0` sai 0 antes de ler o stdin.
2. **Alcance deliberadamente estreito** — `alcanca()` exige extensão `.md`/`.html` **e** o caminho conter `/.claude/visual/` ou `/.claude/reports/`. Documentação, código e config ficam de fora: a régua governa artefato de **leitura**, não todo texto do repositório.
3. **De onde vem o texto** — `content` (o `Write` manda o arquivo inteiro) ou `new_string` (o `Edit` manda só o pedaço novo).
4. **Isenção da origem** — `.html` que contenha `visual_page.py` no corpo já passou pela régua no gerador; medir de novo seria cobrar duas vezes o mesmo texto.
5. **O que conta como redação** — `linhas_de_redacao()` descarta o que está dentro de ``` (prova é literal por obrigação), o vazio, e toda linha que abre com `$ # | < ! >`, que é comando, título, tabela, markup ou citação. O marcador de bullet sai com `lstrip("-*• ")`.
6. **A medida** — `erros_de_estilo(linhas, "o artefato", "pagina")`, perfil de página/relatório/diagnóstico.
7. **Recusa** — `exit 2` com até 6 problemas no stderr, mais a instrução de quebrar em bullets de uma frase e de pôr saída crua dentro de bloco de código.

**Fail-open em tudo que não é violação** — régua vendorada ausente, `exec_module` que levanta, JSON ilegível, caminho fora do alcance, texto vazio: sai 0 mudo. O comentário dá o motivo: *"gate de forma que derruba a escrita por causa da própria falha é pior que a prosa que ele evitaria."* `[confirmado — arquivo lido integralmente]`

**Verificado:** `python3 plugins/guardrails/hooks/test_artefato_regua.py` → **23 checks ok · 0 falhas** neste run, o último sendo "a PORTA (escrita de arquivo) está no disco". `[confirmado]`

### 15b · A REDE — `bootstrap/hooks/stop-regua-relato.py`

**Dispara quando:** `Stop`, timeout 10, **antes** do `stop-forma-relato.py` no mesmo array — o mecânico vem antes do que chama modelo. `[confirmado]`

**Divisão de trabalho com o vizinho, pra não haver guarda em dobro** (escrita na docstring): o `stop-prose-ceiling.py` mede **VOLUME** (quantas linhas de prosa); esta régua mede os **BULLETS** (as linhas que abrem com `•`, `-` ou `*` seguidos de espaço). `[confirmado]`

1. Kill-switch `REGUA_RELATO=0`, e `stop_hook_active` sai calado.
2. `ultima_msg_assistente()` lê o `.jsonl` de trás pra frente, pulando `isSidechain`.
3. `bullets_do_texto()` remove os blocos ``` com regex, casa `^([•\-*])\s+(.*)$` e descarta o que sobrar só de traço ou barra de tabela. O espaço exigido depois do marcador é o que separa `- item` de `**Gate verde**: …`, que abre com `*` e não é lista.
4. **A chamada é UMA, com a LISTA inteira:** `erros_de_estilo(itens, "relato", "pagina")`. Bullet a bullet, a quarta checagem — máximo 6 bullets por bloco — **nunca dispararia**, porque ela só arma quando o valor chega como lista (`lista = isinstance(v, (list, tuple))` no `regua_texto.py`); 20 bullets curtos passavam limpos. As outras três saem iguais nos dois modos, só o rótulo muda. `[confirmado — comentário do hook e o corpo de `erros_de_estilo`]`
5. **Perfil `pagina`, por derivação e não por escolha** — o `regua_texto.py` define esse perfil como «página, relatório, diagnóstico», e o relato de fim de turno é um relatório. **Não** é o perfil `hook`, que proíbe `**` e crase porque o canal do emissor de hook não renderiza markdown — e o canal do CLI renderiza.
6. **Rastro e anti-loop, no molde dos vizinhos** — `batida()` grava **toda** execução em `<estado>/batidas.log` (senão "não rodou" e "rodou e aprovou" são indistinguíveis); `MAX_BLOQUEIOS = 2` por resposta, chaveado por `sha1(session_id + texto)[:16]`, e o terceiro bloqueio vira linha em `bypass.log` em vez de travar a sessão. Estado em `REGUA_RELATO_STATE` ou `CLAUDE_DIR/state/regua-relato` — variável própria, pelo mesmo motivo do juiz de forma: dá pra isolar o teste sem mexer no `CLAUDE_CONFIG_DIR` real.

**Fail-open em tudo que é infra** — régua ausente do vendoring (`ImportError`), payload ilegível, transcript que não abre: sai 0, com a batida registrando o motivo. `[confirmado — arquivo lido integralmente]`

**Verificado:** `bash plugins/bootstrap/hooks/test_bootstrap_hooks.sh` → **52 ok · 0 FAIL** neste run (eram 36 antes), com a fatia nova cobrindo as quatro checagens uma a uma, o kill-switch, a isenção do bloco de prova, a linha em negrito que não é bullet e o bypass depois de 2 bloqueios. `[confirmado]`

---

## 16 · O tier do motor chega como DADO, não como número na skill

**Dispara quando:** a casca de `/sovai` ou de `/qa-loop` vai disparar o Workflow do motor. `[confirmado — `plugins/sovai/skills/sovai/SKILL.md:70-84` e `plugins/qa-loop/skills/qa-loop/SKILL.md:93-108`]`

**O drift que isto existe pra matar, medido em 2026-08-03:** trocar seis valores custou 45 substituições em dois `SKILL.md`, três saíram invertidas e duas sobreviveram a dois verificadores. A causa não era descuido — era o número morar em quinze lugares. `[relatado — docstring de `_shared/r8_tiers.py`]`

**Os passos:**

1. **A casca roda o script antes do Workflow** — `python3 "<skill_dir>/references/r8_tiers.py" args`.
2. **O script lê o JSON e devolve só o que o motor decide** — `para_args()` monta `{model, tiers: {<knob>: {effort}}}` a partir de `r8-tiers.json`. Saída medida nesta rodada: `model: "opus"` e os seis knobs `decompose`, `coordinate`, `executor`, `mechanical`, `diagnose`, `finalize`. `[confirmado — `python3 _shared/r8_tiers.py args`]`
3. **A casca passa isso dentro do `args` do Workflow**, junto com os outros parâmetros.
4. **O script do motor lê `args.tiers.<knob>.effort`, nunca um literal** — no esqueleto, `const T = args.tiers` e `tierFor` escolhe entre `T.decompose.effort` e `T.coordinate.effort` conforme a rodada. `[confirmado — `SKILL.md` do `/sovai`, bloco `sovai-build-engine`]`

⚠️ **`args.tiers` ausente MATA o motor na primeira volta, e isso é a falha certa.** Um default carimbado no script seria mais uma cópia do valor — exatamente o defeito que o contrato existe pra impedir. Contraste deliberado com o vizinho na mesma linha do código: `maxRounds` **tem** default dentro do motor (`args.maxRounds || 5`), porque ausente ele faria `r < undefined` ser falso e o motor devolveria "nada construído" **em silêncio**. Morrer alto é aceitável; passar calado, não. `[confirmado — as duas linhas convivem no mesmo bloco de `args`]`

**Os outros dois usos do mesmo módulo**, ambos lendo o mesmo JSON: `render` gera a tabela de `r8-tiers.md` (ninguém a digita), e `check` falha se o markdown divergir do JSON **ou** se algum `SKILL.md` voltar a carimbar um `effort` literal ao lado de um `model:`. A regex isenta a menção legítima ao nome do knob e o `effort: "low"` do relatório do `/fallow`, que não tem nada com o R8. `[confirmado — `r8_tiers.py:LITERAL` e `python3 _shared/r8_tiers.py demo` → "demo ok"]`

**Trocar um tier é editar `_shared/r8-tiers.json` e rodar `scripts/sync-shared.sh`** — nenhum `SKILL.md` muda. `[confirmado]`

---

## 17 · A ponte de visão por MCP — see_image quando o modelo não tem olhos

**Sem hooks — é MCP puro:** `plugins/vision/` contém apenas `vision_mcp.py`, `.mcp.json` e `.claude-plugin/plugin.json` (v0.1.0). O servidor entra no catálogo do Claude pelo `.mcp.json`: transporte `stdio`, `python3 ${CLAUDE_PLUGIN_ROOT}/vision_mcp.py`. `[confirmado — leitura dos três arquivos nesta rodada]`

**Dispara quando:** o modelo em uso não tem visão — ler a imagem via `Read` devolve "Unsupported Image" — e o Claude precisa do conteúdo dela. A docstring registra o caso: *"Este server expõe UMA tool, `see_image`, que o Claude chama quando precisa entender uma imagem."* `[confirmado — `vision_mcp.py:1-7`]`

**Passos:**

1. **O Claude chama `see_image(caminho, pergunta)`** — só `path` é obrigatório; sem `question`, o servidor pergunta *"O que exatamente esta imagem mostra? Descreva em detalhe, transcrevendo o texto visível."* `[confirmado — `vision_mcp.py:61-91`]`
2. **O servidor codifica e POSTa** — lê o arquivo, codifica em base64 e monta o payload no padrão OpenAI-compatible: `messages[0].content` com `image_url` (`data:<mime>;base64,…` — o mime por extensão: png/jpg/jpeg/gif/webp, default png) + a pergunta em texto, `max_tokens: 1024`. POST para `BASE.rstrip("/") + "/chat/completions"` com `timeout=TIMEOUT`. `[confirmado — `vision_mcp.py:48-120`]`
3. **O servidor VL responde em texto** — a descrição sai de `choices[0].message.content` e volta como `{content: [{type: "text", text}], isError: false}`. `[confirmado — `vision_mcp.py:112-116`]`
4. **O Claude usa a descrição** — o texto entra no contexto e ele segue a tarefa; é o contrato da tool. `[confirmado — docstring de `vision_mcp.py:2-7`]`

**De onde vem o endpoint — o servidor de visão NÃO mora no plugin** (é infra privada de quem instala). Três fontes, nesta ordem: env `QWEN_BASE`/`QWEN_MODEL`/`QWEN_TIMEOUT` (default 180s) → `~/.claude/vision.json` com `{"base": …, "model": …}` → falha com mensagem pedindo a config, **nunca um endpoint chutado**. `[confirmado — `vision_mcp.py:9-45`]`

**Falhas mapeadas** — todas devolvem `isError: true` com o texto prefixado `❌`: servidor não configurado, arquivo inexistente, leitura do arquivo falhou, `HTTPError` do servidor (com `e.read()[:200]`) e exceção genérica. `[confirmado — `vision_mcp.py:81-124`]`

⚠️ **A tool só entra no catálogo do modelo em SESSÃO NOVA.** Adicionar/recarregar o MCP no meio da sessão conecta o servidor, mas `see_image` não aparece na lista do modelo — ele tenta `Read`, falha e desiste. Precisa de sessão nova. `[relatado — medição reportada nesta rodada, não reproduzida aqui]`

**Verificado:** `vision_mcp.py` lido integralmente (165 linhas), `.mcp.json` e `plugin.json` conferidos, registro no `marketplace.json` (v0.1.0, categoria `productivity`) confirmado. `[confirmado]`

---

## Pendências

- **Ponteiros cross-tool inertes** (cenário 2): os 5 arquivos apontam pra um `CLAUDE.md` na raiz que não existe. `[confirmado]`
- **Ponte do context-guard desligada nesta máquina** (cenário 3): env vars presentes, `context-guard-writer.sh` fora do `statusLine.command`. `[confirmado]`
- **Juiz de forma sem nenhum julgamento registrado** (cenário 9b): 12 batidas, todas `sem texto`. O hook executa; o texto do assistente não está chegando a ele nas execuções registradas. Causa não investigada nesta rodada. `[confirmado — o fato; a causa é lacuna aberta]`
- **Ordem entre plugins no mesmo evento**: não determinável a partir deste repositório. Só a ordem **interna** ao array de um `hooks.json` é fixada aqui, e mesmo assim depender dela é `[inferido]`.
- **Conteúdo não lido nesta rodada**, citado só pelo registro: `plugins/branches/hooks/sessionstart-branches.sh`, `plugins/handoff/hooks/handoff-completeness-gate.sh`, `plugins/intent-guard/hooks/delivery-audit.sh`, `plugins/project-doc/hooks/stop-doc-touch.sh`, `plugins/guardrails/hooks/askq-humanize.sh`, `plugins/bootstrap/hooks/post-plugin-command.sh` e `plugins/bootstrap/hooks/lib/apply-config.sh`.
