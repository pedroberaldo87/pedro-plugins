---
generated: 2026-07-31
generated-commit: a57ea6e
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
  - plugins/visual/server/visual_server.mjs
  - plugins/visual/server/start.sh
  - plugins/visual/skills/visual/resolve-dir.sh
  - plugins/visual/skills/visual/SKILL.md
  - plugins/visual/hooks/pre-exitplan-visualize.sh
  - plugins/visual/hooks/sessionstart-plan.sh
  - plugins/visual/hooks/stop-plan-status.sh
  - plugins/visual/lib/plan_state.py
  - plugins/guardrails/hooks/lint-and-typecheck.sh
  - plugins/guardrails/hooks/scope-cop.sh
  - scripts/hook_contract.py
  - plugins/visual/hooks/hooks.json
  - plugins/ship/hooks/pre-deploy-test-check.sh
  - plugins/ship/hooks/hooks.json
  - plugins/ship/skills/ship/SKILL.md
  - plugins/context-guard/hooks/context-guard.sh
  - plugins/context-guard/hooks/context-guard-writer.sh
  - plugins/context-guard/hooks/context-guard-reset.sh
  - plugins/context-guard/hooks/hooks.json
  - plugins/context-guard/skills/setup/SKILL.md
  - plugins/handoff/hooks/sessionstart-ata.sh
  - plugins/handoff/hooks/hooks.json
  - plugins/graphify-guard/hooks/sessionstart-graphify.sh
  - plugins/graphify-guard/hooks/hooks.json
  - plugins/slides/skills/slides/SKILL.md
  - plugins/slides/skills/slides/scripts/check_fidelity.py
  - AGENTS.md
  - GEMINI.md
  - .cursorrules
  - .windsurfrules
  - .github/copilot-instructions.md
  - plugins/graphify-guard/hooks/pretooluse-graphify-guard.sh
  - plugins/handoff/hooks/handoff-completeness-gate.sh
  - plugins/handoff/hooks/teamcreate-nudge.sh
  - plugins/project-doc/hooks/pretooluse-organism-gate.sh
  - plugins/visual/skills/visual/template.html
  - plugins/project-doc/hooks/lib-has-frontend.sh
  - plugins/visual/lib/visual_page.py
  - plugins/slides/lib/md2deck.py
  - plugins/guardrails/hooks/askq-humanize.sh
  - plugins/guardrails/lib/askq_lint.py
  - plugins/bootstrap/hooks/stop-prose-ceiling.py
  - plugins/bootstrap/lib/conformance.py
verified-by:
  - plugins/project-doc/hooks/test_plan_gate.sh
  - plugins/project-doc/hooks/test_sessionstart_doc.sh
  - plugins/visual/lib/test_visual_page.py
  - plugins/slides/lib/test_md2deck.py
  - plugins/guardrails/hooks/test_askq_gate.sh
  - plugins/guardrails/lib/test_askq_lint.py
doc-sig: pedro-plugins/sessionstart-doc.sh@gen=3.8#7b8c41aa
---

# Runtime — fluxos ponta-a-ponta

Este doc descreve **o que acontece em execução**, não a estrutura do repo (isso é `architecture.md`) nem as convenções de código (`patterns.md`). **Catorze** cenários, cada um com o gatilho, os passos com arquivo:símbolo, onde termina e o que fazer quando quebra.

**Rótulos:** `[confirmado]` = lido/executado neste run · `[inferido]` = deduzido do código, não executado · `[relatado]` = veio de journal/commit e não foi executado aqui.

**Aviso de fonte:** existe um diretório `pi-plugins/` **untracked e obsoleto** na raiz com cópias divergentes de vários plugins. Ele polui o grafo (ex.: `pi-plugins/project-doc/lib/journal.py` com fan-in 82). **Nada aqui foi documentado a partir dele** — a fonte é sempre `plugins/`. Trate `pi-plugins/` como lixo a apagar.

---

## 1 · Bootstrap Sync Cycle (pull → apply → snapshot → commit/push)

**Dispara quando:** SessionStart, via `plugins/bootstrap/hooks/hooks.json` → `${CLAUDE_PLUGIN_ROOT}/hooks/session-sync.sh` (sem `timeout` declarado). `[confirmado]`

**Passos:**

1. **Guarda de reentrância** — `session-sync.sh` sai imediatamente se `PEDRO_PLUGINS_HOOK_RUNNING` já está setada; senão exporta `PEDRO_PLUGINS_HOOK_RUNNING=session-sync`. Impede que o PostToolUse `post-plugin-command.sh` (matcher `Bash`) re-dispare o ciclo enquanto o próprio ciclo roda `claude plugin install`. `[confirmado]`
2. **Lock por diretório** — `mkdir "$LOCK_DIR"` em `$HOME/.claude/plugins/.pedro-plugins-sync.lock` (semântica atômica POSIX, sem `flock`). Lock com mais de 300s é quebrado com `rmdir`. `trap ... EXIT INT TERM` libera. Duas sessões abrindo juntas → a segunda sai calada. `[confirmado]`
3. **Checagem barata de remoto** — se `$PEDRO_PLUGINS_REPO/.git` existe (`HAS_SOURCE=1`), `git fetch --quiet` e compara `HEAD` com `@{u}`; só marca `REMOTE_ADVANCED=1` se `merge-base --is-ancestor` confirmar que o remoto está **à frente** (não meramente divergente). Sem repo-fonte, faz o mesmo no cache `~/.claude/plugins/marketplaces/pedro-plugins`. `[confirmado]`
4. **Throttle** — se o remoto não avançou, `PEDRO_PLUGINS_FORCE_SYNC` está vazia e o mtime de `~/.claude/plugins/.pedro-plugins-last-sync` tem menos de `PEDRO_PLUGINS_THROTTLE_SECONDS` (default `86400`), sai. `[confirmado]`
5. **Pull** — `git pull --rebase --autostash`. Conflito → aborta o rebase e sai. Falha não-conflito **com `REMOTE_ADVANCED=1`** → aborta **sem** tocar o timestamp, pra próxima sessão tentar de novo na hora. `[confirmado]`
6. **Apply** — `hooks/lib/apply.sh` localiza o manifest na primeira das 5 origens: repo-fonte → `$CLAUDE_PLUGIN_ROOT/config/manifest.json` → `../../config/manifest.json` relativo ao script → cache do marketplace → glob `~/.claude/plugins/cache/pedro-plugins/bootstrap/*/config/manifest.json`. Converge em 4 etapas: `claude plugin marketplace add` dos faltantes → `claude plugin install` → `claude plugin uninstall` (só de marketplaces gerenciados, **nunca** `pedro-plugins`) → `claude plugin enable/disable`. O estado atual vem de parsear `claude plugin list` com `awk` (blocos `❯ nome@mkt` + `Status:`), deduplicado por `sort -u`. `[confirmado]`

   **6a · A etapa 2 passou a instalar o PRÓPRIO repo** (`ff32947`). `pedro-plugins` é hoje o **primeiro** item de `.marketplaces` no manifest, com `source` HTTPS e os **19** plugins listados (17 `enabled: true`, `graphify-guard` e `intent-guard` `false`). Antes disso o ciclo instalava terceiros e deixava os 19 plugins de casa a cargo de 19 `claude plugin install` manuais. Consequência de runtime: numa máquina limpa, a etapa 1 adiciona 8 marketplaces em vez de 7, e a etapa 2 tem **48** entradas pra convergir em vez de 29. `[confirmado — `jq` no manifest nesta rodada: 8 marketplaces, 48 entradas, 31 ligadas e 17 desligadas]`

   **6b · A etapa 3 é OPT-IN e por default só FALA** (`ff32947`). O laço que decide o que remover foi partido em dois: primeiro uma passada **pura** monta `UNINSTALL_CANDIDATES`/`UNINSTALL_CANDIDATE_COUNT` sem efeito nenhum; só depois, dentro de `if [ "${BOOTSTRAP_UNINSTALL_UNMANAGED:-0}" = "1" ]`, os `claude plugin uninstall … --keep-data` rodam. Sem a variável, o script emite `ℹ desinstalação DESLIGADA — N plugin(s) seriam removidos: …` e **não mexe em nada**. O racional está no cabeçalho e é aritmético: *"a marketplace oficial da Anthropic entrega centenas de plugins enquanto o manifest declara um punhado"* — uma rodada sem guarda desinstalaria tudo que o manifest não nomeia, **a partir de um hook de `SessionStart`**, sem ninguém pedir. `[confirmado — `apply.sh` lido nesta rodada]`

   **6c · Operação que falha não conta mais como aplicada.** `run_claude()` passou a devolver `0`/`1` e a ecoar as últimas 5 linhas da saída capturada quando falha (antes o `>/dev/null 2>&1` engolia o erro real da CLI). Todos os contadores — `ADDED_MKT`, `INSTALLED`, `UNINSTALLED`, `ENABLED`, `DISABLED` — passaram a incrementar **dentro** de um `if run_claude …`, e o resumo final inverteu a prioridade: havendo `FAILURES > 0`, a primeira linha é `⚠ sync incompleto: N operações falharam`, e o `✓ sync aplicado` vira uma linha secundária. **Um resumo que abre com ✓ depois de falhar é pior que resumo nenhum** — quem lê para de ler na primeira linha. `[confirmado — `apply.sh`]`
7. **Portão anti-propagação** — `apply.sh` sai com o **número de operações falhas** (`255` = fatal, cap em `200`). `session-sync.sh` só continua com exit `0`. Qualquer falha → **pula o snapshot** e ainda assim `touch` no timestamp (pra não retentar a cada sessão). `[confirmado]` · racional original em commit `50563fb6` `[relatado]`
8. **Snapshot** — `hooks/lib/snapshot.sh` regenera `plugins/bootstrap/config/manifest.json` a partir de `claude plugin list` + `known_marketplaces.json`. Filtra `pedro-plugins` do bloco auto-gerado mas **preserva** a entrada `pedro-plugins` escrita à mão no manifest anterior. Compara com `jq -S` e imprime `unchanged` (stdout) se idêntico. `[confirmado]`

   **8a · Chave de topo escrita à mão sobrevive — por inversão da lista.** O script declara `GENERATED_KEYS='["version","description","marketplaces"]'` (o que ele **gera**) e preserva, com `with_entries(select(.key … | index($k) | not))`, **toda** chave de topo que não está nessa lista. A primeira versão (mesmo dia) listava o que *salvar* — `jq '{skills}'` — e consertava só o caso, deixando a classe viva: qualquer outra chave mantida à mão seguia sumindo em silêncio no primeiro `SessionStart`. Aconteceu com `skills`, minutos depois de ela ser criada. Hoje só mexe nessa lista quem passa a **gerar** uma chave nova. As **5** chaves do manifest atual são `description`, `ferramentas_externas`, `marketplaces`, `skills`, `version` (`jq keys`, rodado nesta rodada). ✅ **A quinta é a prova de que a inversão pegou:** `ferramentas_externas` entrou em `575c33e` **sem uma linha de mudança no `snapshot.sh`** e sobrevive por não estar em `GENERATED_KEYS`. `[confirmado — `snapshot.sh`, bloco `GENERATED_KEYS`; `test_bootstrap_hooks.sh` roda **19** checks, 19 ok · 0 FAIL neste run, dois deles "chave arbitraria sobrevive ao snapshot" e "skills sobrevive ao snapshot"]`

   **8b · A união de plugins é ADITIVA — o snapshot nunca remove entrada.** Depois de montar o manifest novo, o script faz `group_by(.name)` entre os plugins antigos e os da amostra atual (`if length > 1 then .[1] else .[0] end` — a amostra nova vence no estado `enabled`, a entrada ausente **fica**) e loga `warning: manifest encolheu X -> Y` se ainda assim diminuir. **Causa-raiz medida:** `claude plugin list` devolve saída **truncada de forma intermitente**. Seis chamadas seguidas neste run deram **49 · 47 · 49 · 21 · 26 · 37** linhas `Status:` — mesma máquina, mesmo minuto, nada instalado nem removido no meio. O snapshot antigo gravava fielmente a amostra da vez, então o manifest encolhia sozinho e voltava sozinho. Como não dá pra distinguir "desinstalado" de "a CLI não listou desta vez", a leitura aditiva é a única segura. **Consequência:** desinstalar de verdade passa a ser **edição explícita** do manifest — o snapshot não faz isso por você. O manifest atual tem **48 plugins distribuídos por 8 marketplaces**, sendo 19 entradas de `pedro-plugins` (escritas à mão, filtradas do bloco auto-gerado e recopiadas pelo passo 8) mais as **29** de terceiros, que são as únicas expostas à amostragem da CLI. `[confirmado — `snapshot.sh` + `jq` no manifest nesta rodada: 8 marketplaces, 19 + 29 = 48]`

   **8c · O passo 6b e o passo 8b são a mesma regra vista dos dois lados.** O snapshot nunca remove entrada do manifest porque a amostra da CLI é incompleta; o apply não remove plugin da máquina porque o manifest é incompleto **por construção** (declara um punhado, o marketplace oficial entrega centenas). Nos dois casos a lista disponível é **parcial**, e nos dois a resposta é a mesma: **ausência não autoriza remoção**. Remover fica sendo ato explícito — edição do manifest de um lado, `BOOTSTRAP_UNINSTALL_UNMANAGED=1` do outro.
9. **Commit + push** — só se `SNAPSHOT_STATUS = "changed"`. `hooks/lib/git-sync.sh` faz `git add` e `git commit --only` **apenas** de `plugins/bootstrap/config/manifest.json`, mensagem `chore(plugins): sync @ <hostname -s> <YYYY-MM-DD>`. Push rejeitado → `pull --rebase --autostash` + um retry. `[confirmado]`

**Termina em:** `touch ~/.claude/plugins/.pedro-plugins-last-sync` e `exit 0`. Neste run o arquivo existe, com mtime de hoje 18:35 (`ls -la ~/.claude/plugins/.pedro-plugins-last-sync`) — o ciclo rodou. `[confirmado]`

**Se falhar no passo N:**
- **2** (outro sync ativo) → sai calado; só aparece com `PEDRO_PLUGINS_VERBOSE` setada.
- **5** (conflito de pull) → log em stderr mandando `cd $PEDRO_PLUGINS_REPO && git status`; nada mais roda.
- **6** (`jq` ou `claude` ausentes, manifest inválido/ausente) → `exit 255`, `session-sync` loga "erro fatal — snapshot pulado".
- **7** (N instalações falharam) → **estado local preservado**; sem snapshot, sem push. Retry manual: `PEDRO_PLUGINS_FORCE_SYNC=1 bash plugins/bootstrap/hooks/session-sync.sh`.
- **9** (push rejeitado ou sem rede) → commit local fica; o próximo ciclo tenta de novo. `git-sync.sh` **sempre** sai 0 — erro de git aqui nunca derruba a sessão.

> ⚠️ O ciclo mexe em `git pull`/`git push` do repo-fonte **em toda abertura de sessão**. Se você está no meio de um trabalho não-commitado em `pedro-plugins`, o `--autostash` do passo 5 vai mexer no seu working tree. `[inferido — não reproduzido neste run]`

**O vizinho que NÃO roda neste ciclo — `hooks/lib/apply-config.sh`.** Ele aplica a config global versionada (env, permissões, flags, `CLAUDE.md` global, `statusLine` resolvido) e é chamado **só** pela skill `plugins/bootstrap/skills/setup/SKILL.md`, 1× por máquina — `session-sync.sh` invoca apenas `apply.sh`, nunca ele. `[confirmado — grep de `apply-config` em todo `plugins/bootstrap/`: 2 ocorrências, ambas fora do ciclo]`

**Os passos da skill são 6, e em `ff32947` eles pararam de ter sufixo** `[confirmado — headers `###` de `skills/setup/SKILL.md` lidos nesta rodada]`: **1** `apply.sh` (instala/habilita o que o manifest lista — terceiros **e** os 19 do próprio repo) · **2** `conformance.py` (confere, não conserta) · **3** `apply-config.sh` (a config global) · **4** ferramentas externas · **5** recarregar · **6** reportar. Era `1 · 2 · 2b · 2c · 3 · 4`, com o verificador pendurado como sub-passo do `apply-config.sh` e um aviso em prosa mandando *"rode o `conformance.py` (2b) ANTES deste passo"*. **A ordem que só existia como aviso virou a ordem da lista**, e a razão continua a mesma: a cópia do `CLAUDE.md` é de mão única (repo → máquina), então o verificador é a **última** chance de ver o que só existe na máquina antes de o `apply-config.sh` sobrescrever. Instrução que depende de o leitor obedecer um aviso fora de ordem é instrução que vai ser lida na ordem escrita.

**Passo 4 — o que o marketplace NÃO instala.** Fecha o buraco que os passos 1 e 3 não alcançam: binário de fora exigido por um plugin daqui. Hoje há um, `graphify` (pacote `graphifyy`, MIT), exigido pelo `graphify-guard`; a checagem é uma linha (`command -v graphify >/dev/null || echo "uv tool install graphifyy …"`) e o passo 2 já teria acusado na área `dependencia`. O que faz o passo existir é a **ordem escrita nele**, não o comando: *"Não instale por conta própria. Ofereça o comando ao usuário e explique o que ele destrava"* — e a alternativa nomeada como igualmente correta: *"Se ele não usa grafo, o caminho certo é desligar o `graphify-guard` no manifest, não instalar o binário."* Mesma postura do verificador, dois passos antes: mostra, não conserta. **O passo 1 também mudou de texto**, e o que ele passou a dizer é a trava do passo 6b: *"Sem a variável o script apenas LISTA o que seria removido e não mexe em nada."*

Desde 2026-07-30 ele resolve `CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"` **uma vez** e usa essa variável nas 4 linhas que antes iam em `$HOME` fixo (`settings.json`, o `mkdir -p`, e o backup + a cópia do `CLAUDE.md`). Com `$HOME` cravado, quem setava `CLAUDE_CONFIG_DIR` — smoke de instalação limpa, sandbox, segunda config — fazia o script **escrever na config real** enquanto achava que estava mexendo noutra: o diretório-alvo ficava vazio e o `~/.claude` de verdade era sobrescrito. O `stop-prose-ceiling.py` ganhou a mesma regra no mesmo dia (cenário 12). `[confirmado — `apply-config.sh` + `stop-prose-ceiling.py`; `test_conformance.py` cobre com "o hook escreve o furo DENTRO de CLAUDE_CONFIG_DIR" e "o conformance LE o furo que o hook escreveu", 52 ok · 0 FAIL neste run]`

---

## 2 · Roteamento cross-tool para o CLAUDE.md

**Dispara quando:** outra ferramenta de IA (Codex, Gemini CLI, Cursor, Windsurf, Copilot) abre o repo e carrega o arquivo de instrução que ela conhece.

**Passos:**

1. O `/project-doc` FULL, no passo 10 do `plugins/project-doc/skills/project-doc/SKILL.md`, gera os **ponteiros finos** a partir dos moldes de `references/templates.md` → seção *Thin Pointer Templates*. `[confirmado]`
2. Os ponteiros existentes na raiz deste repo são 5, listados mecanicamente por `ls -a`: `AGENTS.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules`, `.github/copilot-instructions.md`. `[confirmado]`
3. Conteúdo real (copiado literal): `AGENTS.md` e `GEMINI.md` carregam o mesmo bloco de 3 passos — *"Read `CLAUDE.md` for the project index"* → *"read the relevant docs from `.claude/docs/`"* → *"Each doc entry includes '→ read when' hints"*. `.cursorrules`, `.windsurfrules` e `.github/copilot-instructions.md` carregam o par de 2 linhas — *"Read `CLAUDE.md` at the project root…"* + *"Detailed docs by concern are in `.claude/docs/`"*. `[confirmado]`
4. A ferramenta segue o ponteiro e lê o índice, que carrega o marker `<!-- project-doc:v2 gen=3.8 -->` na primeira linha e `<!-- project-doc:v2:end -->` no fim do bloco gerado. `[confirmado]`
5. Do índice, a *Documentation Index* roteia por concern para `.claude/docs/*.md`.

**Termina em:** a outra ferramenta carregando só os docs relevantes, em vez de varrer o repo.

**Se falhar no passo 3 — e ele FALHA neste repo:**

> ⚠️ **Os 5 ponteiros mandam ler `CLAUDE.md` "at the project root", e este repo NÃO tem `CLAUDE.md` na raiz.** O índice vive em `.claude/CLAUDE.md`. `[confirmado — `ls CLAUDE.md` → "No such file or directory"; `grep -n 'project-doc:v2' .claude/CLAUDE.md` → linha 1]`
>
> Consequência: o Claude Code acha o índice sozinho (`.claude/CLAUDE.md` é convenção nativa dele), mas Cursor/Copilot/Codex/Gemini seguem a instrução literal, não acham nada na raiz e caem no fallback de varredura. Os ponteiros estão **inertes fora do Claude Code** neste repo. Correção: criar `CLAUDE.md` na raiz (o `doc-detect.sh:find_claude_md` já prefere a raiz quando ela carrega o marker) ou reescrever os 5 ponteiros pro caminho real.

- **Passo 1** (ponteiro com conteúdo customizado) → o `/project-doc` **não sobrescreve**: detecta pela presença de "Read \`CLAUDE.md\`" e, se não bater, reporta *"Skipped {file} — has custom content"*. `[confirmado — templates.md, seção de ponteiros]`

---

## 3 · Ponte StatusLine ↔ arquivo de estado do context-guard

**Dispara quando:** o Claude Code renderiza a statusLine (a cada turno) e, do outro lado, em **todo** PostToolUse (o `hooks.json` do context-guard não declara `matcher`).

**Passos:**

1. **Escrita** — `plugins/context-guard/hooks/context-guard-writer.sh` recebe o JSON da statusLine em stdin, extrai `.context_window.used_percentage` e `.session_id` via `jq`, e grava o percentual cru em `/tmp/claude-context-pct-<session_id>`. Sem `session_id` → não grava (fail-safe deliberado). `[confirmado]`
2. **Encaminhamento** — se `CLAUDE_STATUSLINE_FORWARD` está setada, o wrapper repassa o mesmo stdin pro comando original (`printf '%s' "$INPUT" | eval "$CLAUDE_STATUSLINE_FORWARD"`), preservando qualquer statusLine que já existisse. `[confirmado]`
3. **Leitura** — `plugins/context-guard/hooks/context-guard.sh` (PostToolUse, timeout 5s) lê `/tmp/claude-context-pct-<session_id>`, trunca a parte decimal e compara com `CLAUDE_CONTEXT_THRESHOLD` (default `80`). `[confirmado]`
4. **Disparo** — acima do threshold, emite `{"decision":"block","reason":"⚠️ CONTEXTO EM N%. Rode o /handoff AGORA …"}` e cria o sentinel `/tmp/claude-context-warned-<session_id>` (uma vez por sessão). `decision:block` devolve o motivo ao modelo, que **executa** o handoff — ao contrário de `continue:false`, que só parava tudo. `[confirmado]`
5. **Não interromper handoff em curso** — antes de tudo, o guard testa `(.tool_input // {} | tostring) | test("handoff"; "i")`. Se a chamada de tool menciona handoff, marca o sentinel e sai: a missão já está sendo cumprida. `[confirmado]`
6. **Kill-switch** — `~/.claude/context-guard/mode` contendo `off` desliga o guard globalmente, sem editar settings nem reload. `[confirmado]`
7. **Reset** — `context-guard-reset.sh` (SessionStart, timeout 5s) apaga **só** os dois arquivos da própria sessão e faz prune de órfãos com `find /tmp -maxdepth 1 -name 'claude-context-pct-*' -mtime +1 -delete` (idem `-warned-`). O glob antigo `-warned-*` rearmava o bloqueio de sessões já abertas. `[confirmado]`

**Termina em:** o modelo recebendo a ordem de rodar `/handoff` uma única vez por sessão.

**Se falhar no passo 1 — e ele FALHA nesta máquina:**

> ⚠️ **A ponte está DESLIGADA nesta máquina.** `~/.claude/settings.json` tem `statusLine.command` apontando direto pro `claude-hud` (`.../claude-hud/*/dist/index.js`), sem passar pelo `context-guard-writer.sh`; e `env` está **vazio** (`sorted(d['env'].keys())` → `[]`), ou seja, nem `CLAUDE_STATUSLINE_FORWARD` nem `CLAUDE_CONTEXT_THRESHOLD` existem. Não há nenhum `/tmp/claude-context-pct-*`. `[confirmado — leitura de ~/.claude/settings.json neste run]`
>
> O plugin está **instalado e habilitado** (`enabledPlugins["context-guard@pedro-plugins"] = true`), os hooks disparam, mas `PCT` sai vazio e `context-guard.sh` sai em `[ -z "$PCT" ] && exit 0`. **Implementado, mas inativo aqui.** Ativar = rodar a skill `context-guard:setup`, que registra o wrapper como `statusLine.command` e move o comando antigo pra `CLAUDE_STATUSLINE_FORWARD`.

- **Passo 3** (`jq` ausente) → `SESSION_ID` vira `"unknown"`, o guard lê `/tmp/claude-context-pct-unknown` (inexistente) e sai calado.
- **Passo 7** (plugin instalado via marketplace de **diretório** sem cache) → `${CLAUDE_PLUGIN_ROOT}` não resolve e o `hooks.json` inteiro não carrega. Instale via marketplace **git**. `[relatado — skills/setup/SKILL.md]`

> ⚠️ **Doc do setup desatualizada:** `plugins/context-guard/skills/setup/SKILL.md`, no bloco de smoke test, diz que o guard emite `{"continue":false,...}`. O código emite `{"decision":"block","reason":...}` desde a v1.3.0. `[confirmado — comparação direta entre os dois arquivos neste run]`

---

## 4 · Pipeline de live-sync do /visual

**Dispara quando:** (a) o usuário invoca `/visual`, ou (b) o PreToolUse em `ExitPlanMode` de `plugins/visual/hooks/hooks.json` → `pre-exitplan-visualize.sh` (timeout 10s) bloqueia um plano.

**Passos:**

0. **A página é EMITIDA, não digitada** (desde 2026-07-29, v1.8.0). Plano continua pelo `plan_state.py init` + `page`; **toda outra página** vem de `python3 ${CLAUDE_PLUGIN_ROOT}/lib/visual_page.py build --spec <json>`, que resolve o diretório (passo 1), injeta o token de sessão (passo 2), recorta `.decisions-box`/`.feedback-box` do `template.html` e imprime o caminho. Ele **recusa** (`exit 2`, nada escrito) spec que pede decisão ou veredito **sem nenhuma prova na página**, evidência de output vazio, decisão com 2 ou 4 opções, ou `tri` incompleto. O contrato dos blocos sai de `visual_page.py schema`. `[confirmado — 60 checks em `test_visual_page.py`; E2E nesta rodada: página gerada, aberta no browser, rádio clicado e o daemon registrou `touched` em `latest.json`]`
1. **Resolução do diretório** — `plugins/visual/skills/visual/resolve-dir.sh` aplica uma cascata de 3: raiz git (`git rev-parse --show-toplevel`) → ancestral com marcador (`package.json`, `CLAUDE.md`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `graphify-out/`, `.git`), parando antes de `$HOME` → fallback `~/Desktop/claude-visual`. Nos dois primeiros casos o alvo é `<dir>/.claude/<sub>`, onde `<sub>` é o **2º argumento** (default `visual`; o motor de plano passa `plans`, e o fallback vira `~/Desktop/claude-<sub>`). Fonte única: hook, skill e `plan_state.py` chamam **este** script. `[confirmado — `resolve-dir.sh` + `bash resolve-dir.sh "$PWD" plans` neste run]`
2. **Token de sessão** — a skill gera um token casando `^[a-zA-Z0-9_-]{4,64}$` (formato recomendado `<YYYYMMDDHHMM>-<rand6>`) e injeta `<script>window.VISUAL_SESSION = "<token>";</script>` logo depois de `<body>`. `[confirmado — SKILL.md, seção "Live sync via claude-visual-server"]`
3. **Subir o daemon** — antes do `open`, a skill roda `${CLAUDE_PLUGIN_ROOT}/server/start.sh`: pinga `http://127.0.0.1:7755/ping` com `curl -sf --max-time 1`; se responde, sai. Senão exige `node` no PATH e sobe `nohup env CLAUDE_VISUAL_PORT="$PORT" node visual_server.mjs &` + `disown`, esperando até 8 × 0.25s. `[confirmado]`
4. **Daemon** — `plugins/visual/server/visual_server.mjs` (Node stdlib puro) escuta em `127.0.0.1` na porta `process.env.CLAUDE_VISUAL_PORT || 7755`. Rotas: `GET /ping` → `{status,pid,port}`; `POST /state` com body `{session, docTitle?, state}`; `GET /state?session=<id>`. `EADDRINUSE` → `process.exit(0)` silencioso (outra instância já serve). `[confirmado]`
5. **Escrita de estado** — no `POST /state`, valida a sessão contra `SESSION_RE`, monta `{session, timestamp, docTitle, state}`, grava `~/.claude/visual-state/<session>.json` **e** `~/.claude/visual-state/latest.json` (mesmo registro + campo `stateFile`). `[confirmado]`
6. **Browser** — cada `saveState()` do HTML chama `postState()`, debounced a 400ms, com `fetch POST http://127.0.0.1:7755/state`. Sucesso pinta a pílula `.live-indicator` de verde (`live sync`); falha, de âmbar (`copy manual`). `[relatado — SKILL.md; não abri um HTML gerado neste run]`
7. **Leitura pelo Claude** — quando o usuário diz "ok"/"pronto"/"lido", o Claude lê `~/.claude/visual-state/latest.json` e parseia `state` do mesmo jeito que parsearia o bloco copiado. `latest.json` ausente ou com mais de 30 min → volta pro copy/paste. `[confirmado — regra em SKILL.md]`
8. **Gate na volta do ExitPlanMode** (reescrito em 2026-07-27 — ganhou teto de três devoluções por sessão e projeto, kill-switch `VISUAL_GATE=0`, `command -v jq` no lugar do caminho Homebrew fixo, e uma 3ª condição: **o plano tem que existir como arquivo** em `.claude/plans/`) — `pre-exitplan-visualize.sh` procura `*sess-${SESSION_ID:0:8}*.html` com `-mmin -5` no diretório resolvido. Achou → roda o **gate de prova**: conta `class="decision-card"|class="feedback-item"` (DECIDE), `class="evidencia"|class="artefato"|<pre` (PROVA), `class="evidencia vazio` (VAZIO) e o marcador de isenção `visual-sem-evidencia:` (ISENTO). Bloqueia com `exit 2` se `DECIDE>0 && ISENTO==0 && (PROVA==0 || VAZIO>0)`. Não achou visual → `exit 2` com o conteúdo literal do plano (`.tool_input.plan`) no stderr e o filename sugerido `<YYYY-MM-DD>-sess-<8char>-plan.html`. `[confirmado]`

**Termina em:** o daemon vivo e o estado do usuário em disco. Neste run: `curl http://127.0.0.1:7755/ping` → `{"status":"ok","pid":93387,"port":7755}` e `~/.claude/visual-state/latest.json` com mtime de hoje 20:38. **Ativo.** `[confirmado]`

**Se falhar no passo N:**
- **3** (sem `node` no PATH, ou daemon não sobe em 2s) → `start.sh` escreve em stderr e sai **0**. A skill continua; o HTML degrada pra copy/paste. Log em `~/.claude/visual-state/.daemon.log`.
- **4** (porta ocupada por outro processo qualquer) → o daemon sai 0 achando que é uma instância irmã; `start.sh` vai receber ping de quem quer que esteja ali. `[inferido]`
- **5** (token fora do regex) → HTTP 400 `invalid-session`; nada é gravado, sem path traversal possível.
- **6** (daemon caiu depois de aberta a página) → pílula âmbar; o botão de copiar continua funcionando.
- **8** (o HTML existe mas não tem prova) → `exit 2` com o texto do gate listando os 3 blocos obrigatórios (`.ident-strip`, `.artefato` com `<iframe src="file://…">`, `.evidencia` com `<pre>`). Escape legítimo: comentar `<!-- visual-sem-evidencia: <razão> -->` no HTML.

> ✅ **Corrigido em 2026-07-27** (era: `/opt/homebrew/bin/jq` hardcoded em 3 chamadas — fora do Mac com Homebrew o `SESSION_ID` saía vazio e o gate ficava destravado em silêncio). Hoje usa `command -v jq`, como o `ship` já fazia. O defeito virou a regra 4 do contrato dos hooks (`patterns.md §5.3`) e o **check E** do gate de commit barra qualquer reincidência. `[confirmado — grep `/opt/homebrew` no arquivo: 0 ocorrências]`

> **Três gates disputam o `ExitPlanMode`** neste marketplace, registrados em `hooks.json` distintos: `visual/hooks/pre-exitplan-visualize.sh`, `intent-guard/hooks/plan-gate.sh` (timeout 60s) e `project-doc/hooks/pretooluse-plan-gate.sh` (também em `EnterPlanMode`). O registro dos três é `[confirmado]`; a ordem em que o Claude Code os executa **não é determinável a partir deste repo**.

---

## 5 · Geração de deck pelo /slides

**Dispara quando:** o usuário pede `/slides`, aponta um `.md` e pede "vira slides", ou pede um deck didático. Sem hooks — é skill pura. `[confirmado — `plugins/slides/` não tem `hooks/`]`

**Passos (modo A · transcrição) — desde 2026-07-29 (v1.3.0) o deck é COMPILADO, não digitado:**

1. Ler o `.md` inteiro e escolher o tema (default `viu`). O `lib/md2deck.py` lê `references/themes/<tema>.md` sozinho — extrai `__FONT_LINKS__`/`__THEME_CSS__` das cercas de código e `__BRAND__`/`__THEME_COLOR__` dos valores em backtick; tema que não define os quatro ⇒ `exit 2` nomeando o que falta. `[confirmado]`
2. **Ver o storyboard:** `python3 ${CLAUDE_PLUGIN_ROOT}/lib/md2deck.py <fonte.md> --plan` devolve JSON com heading, nível, componente escolhido, nº de itens e quantos slides aquele heading gera. A escolha implementa o mapa de `references/layout-patterns.md`: `#` → `cover` (o 1º) ou `divider` · bullets curtos → `numlist` · `nome — descrição` → `idx` · 2-3 bullets com lead em negrito → `feats` · parágrafo curto solto → `statement` · `X → Y` → `metric`. `[confirmado]`
3. **Anotar só o que a heurística errou** — `--anota <json>`, chaveado pelo heading exato, com `component`, `hl` (palavra do título a pintar) e `split` (itens por slide, default 6). Componente fora dos 9 implementados ⇒ recusa listando os válidos. É aqui que entra o julgamento do modelo — componente e densidade —, e **só aqui**.
4. **Compilar:** `python3 <lib>/md2deck.py <fonte.md> [--tema T] [--anota a.json]`, que substitui os placeholders de `assets/template.html` (`__TITLE__`, `__OG_DESC__`, `__THEME_COLOR__`, `__FONT_LINKS__`, `__THEME_CSS__`, `__BRAND__`, `__SLIDES__`). Saída ao lado do `.md` de origem, mesmo nome-base + `.html`. `[confirmado]`
5. **Gate de fidelidade:** `python3 <skill>/scripts/check_fidelity.py <deck.html> <fonte.md>` — exatamente 2 argumentos (`len(sys.argv) != 3` → `sys.exit(2)`), sinaliza prosa que não existe na fonte e sai 1. Num deck compilado **passa por construção**: o texto de corpo sai dos tokens do `.md` sem passar por geração, e as únicas strings criadas pelo programa (enumeradores `01`/`02` e o eyebrow derivado dos headings) são exatamente as que o checker isenta. Virou check verde em `lib/test_md2deck.py`, que roda o checker real nos **dois** sentidos — deck limpo passa, deck com prosa injetada reprova. `[confirmado]`
6. Verificação visual dos 4 cenários com screenshot (desktop, mobile, sem-JS, thumbnail de WhatsApp).

No **modo B · explicador**, a skill autora a didática e o gate passa a ser `scripts/check_provenance.py <deck.html> <fonte1> [fonte2 ...]` (aceita N fontes: `sys.argv[2:]`). `[confirmado]` O caminho recomendado é autorar o `.md` e compilá-lo pelos passos 2-4; os **infográficos** não são cobertos pelo compilador e seguem montados à mão dentro do slide compilado.

**Termina em:** um `.html` single-file que é apresentação no desktop e documento scroll no celular — o conteúdo mora no markup estático, nunca injetado por JS.

**Se falhar no passo N:**
- **1** (tema inexistente ou incompleto) → `exit 2` listando os temas que existem, ou o que o tema não define; nada é escrito.
- **4** (destino read-only, ex. iCloud) → fallback pra `~/Desktop/<nome>.html`, avisando. Placeholder não substituído ⇒ `exit 2` nomeando qual.
- **4** (**o tema não fica ativo**) → `exit 2` com *"o CSS do tema não ficou ativo (caiu dentro de comentário?)"*. Essa guarda existe por um defeito real de 2026-07-29: o `template.html` **documenta** dois placeholders dentro de comentários (`<!-- __FONT_LINKS__ : … -->` e `/* __THEME_CSS__ : … */`), e o replace global injetava o `:root{…}` **dentro** do comentário — o primeiro `*/` do próprio tema (`/* fonts */`) o fechava no meio e matava paleta e fontes. O deck saía branco com fonte serif, passava no `check_fidelity.py` e no resto da suite. O conserto remove os dois comentários antes de substituir, e o build confere que `:root`/`--bg-body` sobrevivem fora de comentário dentro do `<style>`. `[confirmado — reproduzido e consertado na mesma rodada; só o print no browser pegou]`
- **5** (fidelidade pendente) → **não conserte o HTML**: num deck compilado isso é bug do compilador ou `.md` alterado depois de compilar.
- **6** (thumbnail preto no WhatsApp) → sinal de que conteúdo passou a depender de JS. Todo texto/figura tem que estar no markup do slide.

---

## 6 · Gate de testes pré-deploy do /ship

**Dispara quando:** PreToolUse com matcher `Bash`, via `plugins/ship/hooks/hooks.json` → `pre-deploy-test-check.sh`, **timeout 120s**. Roda em toda chamada de Bash; só age se o comando parecer deploy. `[confirmado]`

**Passos:**

1. **Fail-open de infra** — `command -v jq >/dev/null 2>&1 || exit 0`. Resolvido via PATH, não por caminho Homebrew fixo. `[confirmado]`
2. **Detecção de deploy** — o comando é testado contra os padrões (lista literal do arquivo): `pm2 (restart|reload|deploy|start)`; `docker-compose`/`docker compose` com `--build` ou `-d`; `vercel [deploy] … --prod` e `netlify deploy … --prod` (aceitando prefixo `npx`/`pnpm dlx`/`yarn dlx`/`bunx`); `fly`/`flyctl deploy`; `(npm|pnpm|yarn|bun) [run] deploy`; `deploy.sh` **como comando** (direto ou via `bash`/`sh`, com ou sem caminho); `make (deploy|prod|release)`; `ssh … <AÇÃO remota>`. Nada casou → `exit 0`. `[confirmado]`

   Três invariantes de escrita dessas regex, todas nascidas de furo medido com payload real na rodada de 2026-07-29 (`v1.3.4`/`v1.3.5`) e travadas em `plugins/ship/hooks/test_pre_deploy.sh`:
   - **Âncora de início-de-comando** (`(^|[;&|][[:space:]]*)`) em `pm2`, `make`, `vercel`, `npm` e `deploy.sh`. Sem ela a *menção* dispara o gate: `git commit -m "make deploy target fixed"` e `rg "vercel deploy --prod" .` rodavam a suíte inteira. Bloqueio espúrio é o que ensina a desligar o gate.
   - **O terminador aceita fechamento de string** (`[[:space:]"'`;&|)]`), porque o deploy remoto fecha com aspa: `ssh vps "cd /app && ./deploy.sh"`.
   - **O prefixo legítimo tem que atravessar a âncora** (`CMDPFX`, v1.3.6). A âncora que impede a menção de disparar cegava junto `sudo ./deploy.sh`, `nohup bash deploy.sh &` e `ENV=prod ./deploy.sh` — e o primeiro **era detectado** antes dela existir (regressão medida). O grupo é **enumerado** (atribuição de variável + `sudo|nohup|env|time|exec|command`), nunca "qualquer palavra antes", senão a âncora deixa de existir. Teto: flag com valor no lançador (`sudo -u deploy ./deploy.sh`) não casa.
   - **O nome do arquivo tem que ser `deploy.sh`, não terminar em `deploy.sh`** (v1.3.6). `[^…]*deploy\.sh` casava `test_pre_deploy.sh` — ou seja **rodar a suíte deste gate disparava o gate**, e o release-gate a roda a cada commit. Hoje antes do nome só se admite caminho (`([^…]*/)?`).
   - **No `ssh`, casa-se a AÇÃO, não o nome da ferramenta.** `pm2` cru pegava `ssh vps "pm2 logs api"` — inspeção que a própria SKILL.md do ship manda rodar no rollback. Hoje exige o verbo (`pm2 (restart|reload|deploy|start)`, `docker (restart|start|run|compose up)`, `git pull`, `deploy`) e proíbe o verbo seguido de `@` (senão `ssh -t deploy@vps ls` casa no *username*). ⚠️ O meio do padrão é `.*` **de propósito**: um clamp `[^;&|]*` parava a busca no primeiro `&&` e cegava `ssh vps "cd /app && git pull"` — a forma mais comum de deploy remoto que existe.
3. **Cache verde** — `source` de `plugins/ship/hooks/green-cache.sh` (cópia vendorada de `_shared/green-cache.sh` via `scripts/sync-shared.sh`; as 3 cópias fora de `pi-plugins/` são `_shared/`, `plugins/ship/hooks/` e `plugins/qa-loop/lib/`, listadas por `find . -name green-cache.sh -not -path "./pi-plugins/*"`). `[confirmado]`
4. **Resolver o diretório do projeto** — `resolve_proj_dir()` extrai o diretório **do comando**, não do `cwd`: primeiro de `cd <dir> && … deploy.sh`, depois do caminho explícito do script. Só aceita o candidato se `<cand>/scripts/run_app_tests.sh` for executável; senão devolve o `cwd`. `[confirmado]`
5. **Modo 1 — gate por-app** (quando `$PROJ/scripts/run_app_tests.sh` é executável **e** o comando cita `deploy.sh`): extrai os apps dos argumentos após `deploy.sh`. Sem argumentos → `discover_apps()` varre `tests/*/`, `apps/*/tests` e `apps/*/package.json` com script `test` real, filtrando não-apps por `is_app_like()` (`_*`, `.*`, `__*`, `e2e`, `fixtures`, `helpers`, `utils`, `conftest`, `contracts`, `smoke`). Para cada app: `app_has_tests` falso → **avisa no stderr** (`⚠️ app <x> deployado SEM gate`) e pula; senão `green_cache_check "$PROJ" "app:$app"` → HIT pula; MISS roda `cd "$PROJ" && bash scripts/run_app_tests.sh "$app"` e, verde, `green_cache_mark`. `[confirmado]`

   ⚠️ **O parsing de `ARGS` é onde o gate desaparecia sem ninguém ver** — três furos medidos em 2026-07-29, todos com a mesma forma: *token que não é nome de app sobrevive ao filtro, `ARGS` fica não-vazio, `discover_apps()` nunca roda, e o deploy inteiro passa com ZERO teste* — reportando o token intruso como se fosse app.
   - **Redireção não é app.** Em `./deploy.sh > /tmp/dep.log`, o filtro só descartava token começando com `-`, então `>` e `/tmp/dep.log` viravam "apps".
   - **Valor de flag não é app.** Em `deploy.sh --env prod`, o `prod` sobrevivia e era o único "app". Hoje o filtro descarta o token seguinte a uma flag **quando ele não está na lista de apps conhecidos** — o que preserva `deploy.sh --env prod crm` (o `crm` é conhecido, entra).
   - **Deploy encadeado gateava só o ÚLTIMO.** O recorte `.*deploy\.sh` é guloso e cortava no último script, então em `./deploy.sh crm && ./deploy.sh web` o `crm` subia sem teste e sem aviso.
   O contrapeso que proíbe o conserto ingênuo (fallback cego pro `discover_apps()`): **deploy de UM app não pode virar deploy full** — super-gatear o monorepo é a dor que o Modo 1 existe pra evitar. Os dois lados estão travados na suíte.
6. **Escape do Modo 1** — projeto **com** gate por-app mas comando que **não** é `deploy.sh` (migração via `ssh`, `docker compose up -d <svc>`) → `exit 0` com aviso, sem cair na suíte legada. O projeto declarou o gate por-app como seu contrato. `[confirmado]`
7. **Modo 2 — suíte inteira legada** (projetos sem `run_app_tests.sh`): sobe a árvore a partir do `cwd` procurando, nesta ordem por diretório, `package.json` com script `test` real → `pyproject.toml`/`pytest.ini`/`setup.cfg` → `Cargo.toml` → `go.mod` → `Makefile` com alvo `test:`. Para pytest a ordem de interpretador é **`.venv/bin/pytest` local > `uv run --all-extras pytest` > `pytest` do PATH** — `pytest` puro num projeto uv/venv acha o Python global e reprova uma suíte que está verde. `[confirmado — v1.3.1]`
8. **Bloqueio** — falhas no Modo 1 → `exit 2` listando os apps. Falhas no Modo 2 → `exit 2` com as últimas 40 linhas da saída.

**Termina em:** `exit 0` (deploy liberado) ou `exit 2` (deploy bloqueado, motivo devolvido ao modelo pelo stderr).

**O canal de saída do caminho que LIBERA mudou na v1.3.6, e o antigo era MUDO.** Até então os avisos saíam por `echo … >&2` com `exit 0` — e a doc do harness diz que no exit 0 a saída de um `PreToolUse` vai só pro debug log (as exceções são `UserPromptSubmit`, `UserPromptExpansion` e `SessionStart`). Os **4** avisos deste gate nunca chegaram a ninguém, incluindo `⚠️ nenhum test runner detectado — deploy permitido sem verificação`: **o gate anunciava que estava desligado, para o debug log.** Hoje o caminho de liberação acumula em `NOTES` e emite **um** JSON no stdout via `allow_with_notes()` — `additionalContext` (contexto do modelo, ao lado do tool result) + `systemMessage` (visível pro usuário). O caminho de **bloqueio** segue `exit 2` + stderr, que é o canal documentado pra ele. `[confirmado — doc oficial + o aviso observado chegando ao modelo em 2026-07-30]`

**Se falhar no passo N:**
- **1** (sem `jq`) → fail-open: o deploy passa **sem verificação**. É a convenção do marketplace, mas aqui significa trava destravada.
- **2** (deploy por um caminho não coberto — ex. `kubectl apply`, `terraform apply`, `git push heroku`, ou `ENV=prod ./deploy.sh` com prefixo de variável) → passa batido. **A lista de padrões é o teto real do gate**, e o teto é conhecido: a rodada de 2026-07-29 fechou `fly deploy` e os scripts de `package.json`, mas prefixo de env var / `sudo` antes do comando **continua** cegando as âncoras. `[confirmado — medido com payload real]`
- **5** (app sem testes) → `app_has_tests` retorna falso, o app é **pulado** (não bloqueado) e desde `v1.3.4` o gate **avisa no stderr** em vez de sair `exit 0` com zero output. Foi o silêncio que deixou um app Node com 17 vitest quebrados subir. `[relatado — commit `131e588a`]` ⚠️ **O aviso só existe no caminho de app NOMEADO.** No deploy **full**, `APPS` vem de `discover_apps()`, que só enumera app que **tem** teste — logo app sem teste é invisível ali e segue passando calado. Limitação aberta.
- **7** (nenhum runner detectado) → `⚠️ nenhum test runner detectado — deploy permitido sem verificação`, `exit 0`.

> A skill `plugins/ship/skills/ship/SKILL.md` §2.5 declara o mesmo gate no nível do modelo ("este gate não pode ser burlado", com a exceção explícita do cache verde) e §2.6 descreve o piso determinístico por-app + a avaliação LLM que só pode **ampliar** o escopo, nunca estreitar. O hook é a rede no nível do harness. `[confirmado]`

---

## 7 · ARRANQUE — o que roda no SessionStart

**Dispara quando:** o Claude Code abre uma sessão neste (ou em qualquer) projeto.

**Quantos são:** **8 comandos de hook `SessionStart`, distribuídos por 7 plugins.** Derivado mecanicamente neste run — soma de `len(b['hooks'])` sobre `hooks.SessionStart` de cada `plugins/*/hooks/hooks.json`:

```
plugins/bootstrap/hooks/hooks.json        1  session-sync.sh
plugins/branches/hooks/hooks.json         1  sessionstart-branches.sh
plugins/context-guard/hooks/hooks.json    1  context-guard-reset.sh
plugins/graphify-guard/hooks/hooks.json   1  sessionstart-graphify.sh
plugins/handoff/hooks/hooks.json          1  sessionstart-ata.sh
plugins/project-doc/hooks/hooks.json      2  sessionstart-organism.sh, sessionstart-doc.sh
plugins/visual/hooks/hooks.json           1  sessionstart-plan.sh
TOTAL 8
```

Os 7 plugins estão **habilitados nesta máquina** (`enabledPlugins` em `~/.claude/settings.json` traz `bootstrap@`, `branches@`, `context-guard@`, `graphify-guard@`, `handoff@`, `project-doc@`, `visual@`, todos `true`). `[confirmado — soma de `len(b['hooks'])` sobre `hooks.SessionStart` dos 10 `hooks.json` nesta rodada: 8]`

⚠️ **"8 nesta máquina" ≠ "8 numa máquina nova", desde `ff32947`.** O arranque de quem instala o marketplace hoje é o que a **receita** monta (cenário 1, passo 6a), e ela traz `graphify-guard` com `enabled: false` — logo, **7 hooks de `SessionStart` em 6 plugins** numa máquina recém-bootstrapada, sem o `sessionstart-graphify.sh` do item 3 abaixo. Esta máquina tem 8 porque o plugin está ligado aqui **contra** o que o manifest pede, e é exatamente isso que o `conformance.py` acusa: *"graphify-guard@pedro-plugins devia estar DESLIGADO e esta ligado"* `[confirmado — o verificador rodado nesta rodada sai `1` com esse desvio]`. **A régua que vale além do caso:** contar hook varrendo `plugins/*/hooks/hooks.json` mede o que o repo **oferece**; o que **roda** é a interseção com `enabledPlugins`, e o default dessa interseção agora mora no manifest, não na máquina de quem escreveu.

### Ordem

> **A ordem de disparo entre plugins NÃO é determinável a partir deste repositório.** Nenhum `hooks.json` declara prioridade, e o repo não contém a implementação do harness que resolve a ordem. O único ordenamento que o código deste repo fixa é **interno ao `project-doc`**: em `plugins/project-doc/hooks/hooks.json`, o array `SessionStart[0].hooks` lista `sessionstart-organism.sh` **antes** de `sessionstart-doc.sh` — e o `sessionstart-doc.sh` depende disso, porque só reenquadra o texto para "módulos de um organismo" assumindo que *"o `sessionstart-organism.sh` já deu o banner"* (comentário literal no arquivo). `[confirmado]` · Que o harness respeite a ordem do array é `[inferido]`.

### O que cada um injeta

1. **`bootstrap/hooks/session-sync.sh`** — sem timeout declarado. Não injeta contexto: imprime log de sync em stdout/stderr. É o cenário 1 inteiro. **Nunca bloqueia** (`exit 0` em todos os caminhos). `[confirmado]`
2. **`context-guard/hooks/context-guard-reset.sh`** — timeout 5s. Não injeta nada; apaga `/tmp/claude-context-pct-<sid>` e `/tmp/claude-context-warned-<sid>` da própria sessão e faz prune de órfãos com mais de 1 dia. `[confirmado]`
3. **`graphify-guard/hooks/sessionstart-graphify.sh`** — timeout 10s. Roda `graphify-detect.sh` e, se houver grafo, injeta `additionalContext` listando cada projeto com grafo e sua frescura (`atualizado, build <data>` ou `⚠️ defasado: N arquivo(s) mudaram desde <data>`), mandando usar `graphify query` antes de grep/Explore. Grafo defasado acrescenta a ordem de oferecer `graphify --update`. Sem grafo → sai calado. `[confirmado]`
4. **`handoff/hooks/sessionstart-ata.sh`** — timeout 10s. Não injeta contexto. Grava `/tmp/claude-ata-session-<sha1(cwd)[:12]>` com `{session_id, transcript_path, cwd, source}`, porque a skill `handoff` **não recebe `session_id`** (skill ≠ hook) e precisa desse sentinel pro `extract_ata.py --auto` achar o `.jsonl` certo. O hash tem que ser idêntico ao de `extract_ata.py`. `[confirmado]`
5. **`project-doc/hooks/sessionstart-organism.sh`** — timeout 10s. Exige `jq`, `python3` e `../lib/organism.py`. Roda `organism.py brief <cwd>`; se `.organism == true`, injeta o banner 🧬 com nome do organismo, número e nomes dos módulos, a `golden_rule` e a lista de costuras (`• <id> (<severidade>): modA ↔ modB`). Fora de um organismo, sai calado. `[confirmado]`
6. **`project-doc/hooks/sessionstart-doc.sh`** — timeout 10s. Três saídas:
   - **Tem doc** (`doc-detect.sh <cwd>`, modo descida até 3 níveis) → injeta 📚 listando cada `CLAUDE.md` + nº de docs, com flag `⚠️ DEFASADA` / `⚠️ staleness indeterminado` / `⚠️ fora do padrão atual (gen)` conforme as colunas 4 e 5 do TSV, e a ordem de ler o índice antes de grep/Glob/Explore. Dentro de um organismo, o header é reescrito pra "Docs por módulo do organismo `<nome>`". **Desde 2026-07-28, este ramo também cobra o autoral:** se o projeto tem doc minerada mas **ZERO** documentos autorais, entra uma linha `⚠️ … ZERO dos N autorais` mandando OFERECER `/start-doc gaps`. Antes disso a contagem de autoral só existia no terceiro ramo — ou seja, **projeto já minerado nunca era cobrado**, que é o caso da maioria (este repo incluído). Cap de **1× por (sessão, projeto)** via `${TMPDIR}/claude-doc-autoral-nudge-<uid>-<sid>-<cksum(proj)>`; kill-switch `DOC_AUTORAL_GATE=0`. O `N` é **6** quando `has_frontend` (`hooks/lib-has-frontend.sh`) acha sinal de interface (`.tsx`/`.jsx`/`.vue`/`.svelte`/`index.html`/`.swift`/`.kt` versionado, ou framework de UI no `package.json`) — aí `design.md` entra na conta —, e **5** quando não acha. Backend puro, CLI e este próprio marketplace ficam de fora de propósito: cobrança que não cabe ensina a ignorar cobrança. `[confirmado — `test_sessionstart_doc.sh`, 8 casos]`
   - **Não achou descendo, mas a raiz tem doc** → reconsulta `doc-detect.sh --one <raiz>` e cai no fluxo normal. Esse ramo existe porque `doc-detect.sh <dir>` só **desce** e `project_root` **sobe**: com o cwd numa subpasta, a versão antiga declarava "não tem documentação nenhuma" sobre um repo documentado, contradizendo o plan-gate no mesmo turno. `[confirmado — comentário e código, achado da revisão de 2026-07-26]`
   - **Nem raiz nem descida têm doc** → conta quantos dos documentos autorais existem (`quality-goals`, `constraints`, `context`, `solution-strategy`, `glossary`, mais `design` quando `has_frontend`), conta `git ls-files | wc -l`, e injeta 📐 mandando OFERECER `/start-doc` — com o aviso explícito de que **o gate de plano vai barrar** neste projeto.

   **Degradação sem a lib:** se `hooks/lib-has-frontend.sh` não puder ser carregada, o hook define `has_frontend() { return 1; }` e **segue** — perde só a contagem de `design.md`, nunca o heads-up da doc. Um `exit 0` no topo mataria trabalho que não depende dela, que é exatamente a isenção "uso local já degradado dispensa guarda no topo" de `patterns.md §5.3`. `[confirmado — `test_sessionstart_doc.sh` caso 8, roda o hook num dir sem a lib]`

7. **`visual/hooks/sessionstart-plan.sh`** — timeout 10s. Exige `jq` e `python3`. Resolve `<raiz>/.claude/plans` por `resolve-dir.sh <cwd> plans`, **sempre** deixa o marco da sessão em `${TMPDIR}/claude-plan-mark-<uid>-<sid>-<cksum(dir)>` (mesmo sem plano — é o que o `Stop` compara depois) e roda `plan_state.py open --json`. Havendo plano ativo, injeta 📋 com título, `X/Y passos`, a próxima fase não fechada e o caminho do arquivo, mais a ordem de **não reconstruir o plano de memória nem renomear fases**. Sem plano ativo, sai calado. `[confirmado — `test_plan_hooks.sh`, checks "sem plano nenhum, não fala nada" e "mesmo sem plano, deixa o marco da sessão"]`

8. **`branches/hooks/sessionstart-branches.sh`** — timeout 15s, matcher `*`. Roda `lib/branch_state.py --repo <git root> stale --dias ${BRANCHES_DIAS:-30}` e injeta 🌿 só com a **contagem** de branches paradas (mais quantas já estão contidas na base e os nomes), mandando rodar `/branches` pro relatório com prova. Sem branch parada, fora de repo git, sem `jq`/`python3` ou com `BRANCHES_GATE=0` → sai calado. `[confirmado]`

### Quem pode bloquear

**Nenhum dos 8 deste repo.** (Fora dele, `codex` e `superpowers` também registram `SessionStart` e estão habilitados — 9 plugins no total varrendo o cache; nenhum deles é analisado aqui.) Todos terminam em `exit 0` e o único canal de saída usado é `hookSpecificOutput.additionalContext` (nunca `permissionDecision`, nunca `decision:block`). `[confirmado — grep de `permissionDecision`/`decision` nos 8 arquivos: zero ocorrências]` O bloqueio no `project-doc` acontece **depois**, no `PreToolUse` (cenário 8) — o SessionStart só enquadra.

**Se falhar no passo N (qualquer um):** todos são fail-open por construção — `command -v jq || exit 0`, `command -v python3 || exit 0`, `[ -f "$ORGANISM_PY" ] || exit 0`, `2>/dev/null || true`. Um hook quebrado silencia a si mesmo; a sessão abre normalmente. O custo é a perda silenciosa do enquadramento, não uma falha visível.

---

## 8 · FALHA — o gate de plano nega um plano por falta de documentação

**Dispara quando:** PreToolUse com matcher `EnterPlanMode|ExitPlanMode` → `plugins/project-doc/hooks/pretooluse-plan-gate.sh`, timeout 10s. `EnterPlanMode` é o momento certo (antes de o plano existir); `ExitPlanMode` é a rede, e ainda dá tempo porque o deny volta pro modelo antes de o plano chegar ao usuário. `[confirmado]`

### O caminho da negação

1. **Fail-open de infra, em três guardas** — sem `jq` → `exit 0`; sem conseguir `source` do `lib-project-root.sh` ou sem raiz resolvida → `exit 0`; **`doc-detect.sh` ilegível** → `exit 0`. Essa terceira existe porque um `chmod 000 doc-detect.sh` fazia um projeto totalmente documentado cair no CASO A e ser negado **sem cap**. `[confirmado — achado da revisão de 2026-07-26; coberto pelo teste "doc-detect ilegível: fail-OPEN"]`
2. **Chave dos sentinels** — `lib-project-root.sh:project_root()` sobe procurando `CLAUDE.md`/`.claude/CLAUDE.md` e, se não achar, marcador de projeto (`.git`, `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `.claude`), parando antes de `$HOME`. `project_hash()` é `printf '%s' "$1" | cksum | cut -d' ' -f1`. **Nunca canonicalize** (`git rev-parse`, `realpath`, `pwd -P`): no macOS `/var` é symlink de `/private/var`, e o `posttooluse-doc-read.sh` deriva a raiz **recortando a string** do `file_path` — dois métodos diferentes geram PHASH diferentes e o sentinel nunca casa. `[confirmado]`
3. **Três desfechos:**
   - **CASO A — nenhuma documentação:** nega **sempre**, sem cap de nudges. Decisão explícita de projeto (2026-07-26): nega sempre, a não ser que o usuário verbalize que é para ignorar.
   - **CASO B — tem doc, não foi lida nesta sessão:** nega com cap de 3, contador em `/tmp/claude-plan-gate-count-<session>-<phash>`.
   - **CASO C — tem doc e já foi lida** (`/tmp/claude-doc-guard-<session>-<phash>` existe): `exit 0`, silêncio.
   - **Ramo extra — `CLAUDE.md` escrito à mão sem `.claude/docs/`:** tratado como CASO B (leia, com cap), **não** como CASO A. Antes, repo alheio com CLAUDE.md manual era negado pra sempre com uma mensagem que **mentia** ("sem CLAUDE.md") sobre um arquivo que estava lá. `[confirmado]`

### O que o agente vê

No CASO A sem nenhum documento autoral, o `permissionDecisionReason` é (texto literal do arquivo, com `${PROJ}` substituído):

> 📐 `<PROJ>` NÃO tem documentação nenhuma — sem CLAUDE.md, sem .claude/docs/. Antes de planejar, rode `/start-doc`: ele entrevista o usuário sobre o que o sistema prioriza, o que é inegociável, onde ele termina, as decisões que explicam o formato e o vocabulário interno. É essa entrevista que guia tudo que vem depois — inclusive este plano. Se houver código, depois dela rode `/project-doc` pra minerar o resto. **Este gate nega SEMPRE enquanto não houver doc. O escape é o usuário autorizar explicitamente — o token garantido é `--sem-doc` (frases como "ignora a doc" também valem, mas o token é inequívoco). Ele revoga com `--com-doc`.**

Com 1–4 dos 5 autorais presentes, a mensagem muda para *"tem N de 5 documentos autorais, mas ainda não tem índice CLAUDE.md nem doc minerada"*. No CASO B, a mensagem lista os docs reais (`basename` de `.claude/docs/*.md`), o caminho do índice, o aviso de staleness quando a coluna 4 do TSV é `stale`/`unknown`, o aviso de `out_of_pattern` quando a coluna 5 é `1`, e fecha com *"(aviso N/3 — depois disso silencio)"*. `[confirmado]`

Formato de saída, nos dois casos:

```json
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"…"}}
```

### O escape verbal

`plugins/project-doc/hooks/userpromptsubmit-plan-escape.sh` (UserPromptSubmit, timeout 10s) é quem **ouve a frase** — hook não lê a conversa, então quem escuta é este.

- **Regex de escape** (`ESCAPE_RE`, montado no arquivo): imperativo + doc — `ignor(a|ar|e)`, `pul(a|ar|e)`, `dispens(a|ar|e)`, `desconsider(a|ar|e)`, `esquec(e|er|a)`, `deixa` seguido de artigo opcional + `doc|docs|documentação|documentacao`; **ou** verbo de andamento + `sem` + doc — `planej(a|ar|e)`, `faz(er) o plano`, `seg(ue|uir)`, `vai`, `toca`, `manda`; **ou** os tokens literais `--sem-doc` / `#sem-doc`.
- **Fronteira de palavra obrigatória** — `B='(^|[^[:alnum:]])'` antes de todo verbo. Sem ela, `"esta**va sem** documentação"` e `"con**segue sem** doc"` liberavam o gate. São constatações, não ordens.
- **Doc de terceiro** — `EXTERNAL_RE` casa `doc(umentação) (do|da|dos|das|de) <coisa>`. `"ignora a doc do React"` é frase banal em qualquer sessão de código e liberava o gate do **projeto**.
- **Ambiguidade resolve pro lado seguro** — casou escape **e** external → **não** libera, a menos que o prompt traga `--sem-doc`/`#sem-doc`.
- **Efeito** — grava `/tmp/claude-plan-gate-escape-<session>-<phash>` (conteúdo: o path da raiz) e injeta 🔓 avisando que o escape está ativo, com a ordem de **registrar no plano que ele foi feito sem doc** e oferecer `/start-doc` no fim. Já liberado → sai calado, pra não poluir todo prompt seguinte.
- **Escopo** — por sessão × projeto, e vale o resto da sessão. Chaveado por `session_id` porque arquivo global vaza entre sessões concorrentes (foi o bug do context-guard).
- **`--com-doc` revoga** — `REVOKE_RE` = `--com-doc` ou `exig(e|ir)`/`volta a exigir`/`restaura` + doc. Apaga o sentinel e injeta 🔒 *"Escape do gate de documentação REVOGADO para `<PROJ>`"*. Não estava liberado → sai calado, nada a revogar.
- **Só vale pro CASO A.** O `[ -f "$ESCAPE" ] && exit 0` está **dentro** do bloco "nenhuma documentação". Projeto **com** doc não lida (CASO B) continua nudgeando até o cap de 3, escape ou não. `[confirmado — posição da linha no arquivo]`

### O que libera de verdade (CASO B)

`plugins/project-doc/hooks/posttooluse-doc-read.sh` (PostToolUse, matcher `Read`): normaliza `file_path` para absoluto, recorta a raiz por padrão (`*/.claude/docs/*` → prefixo; `*/.claude/CLAUDE.md`; `*/CLAUDE.md`) e faz `touch` em `/tmp/claude-doc-guard-<session>-<phash>`. Um `Read` real em qualquer doc — inclusive no `CLAUDE.md` da raiz — silencia o gate. Se o doc lido está `stale`/`unknown` segundo `pattern_check.py --project-staleness`, ele **ainda** injeta um aviso `additionalContext` no momento exato do consumo (PostToolUse não tem `permissionDecision`, logo é estruturalmente incapaz de loopar). `[confirmado]`

### Quando falta `jq` (fail-open)

Sem `jq` no PATH, **os dois lados** morrem calados na primeira linha:

- `pretooluse-plan-gate.sh` → `command -v jq >/dev/null 2>&1 || exit 0` → **o plano passa sem nenhuma exigência de doc**.
- `userpromptsubmit-plan-escape.sh` → mesma guarda → o escape **não é gravado**.

Ou seja: sem `jq` o gate está desligado, e nada no CLI diz isso. É o contrato "fail-open" do repo levado ao limite — a trava fica destravada sem ninguém ver. O mesmo padrão apareceu no `ship` (corrigido trocando o caminho Homebrew fixo por `command -v`) e **ainda existe** no `visual/hooks/pre-exitplan-visualize.sh` (cenário 4). `[confirmado]`

### Prova

`bash plugins/project-doc/hooks/test_plan_gate.sh` rodou neste run: **49 passou · 0 falhou**. Entre os checks verdes: *"constatação NÃO libera: 'o time não consegue sem documentação'"*, *"doc de terceiro NÃO libera: 'ignora a doc do React, usa o código real'"*, *"`--sem-doc` vence a ambiguidade"*, *"`--com-doc` revoga e avisa"*, *"após revogar, o gate volta a barrar"*, *"doc-detect ilegível: fail-OPEN (não nega às cegas)"*, *"cwd com barra final: sentinel ainda casa"*, *"E2E: Read real → posttooluse escreve → gate libera"*. `[confirmado]`

---

## 9 · Ciclo de vida de um plano de implementação (`/visual` v1.5.0)

**Dispara quando:** o Claude vai apresentar um plano, PRD ou roadmap; e depois, a cada passo concluído.

**Por que existe:** até a v1.4.0 o plano só existia no transcript e cada consumidor o re-derivava por LLM. Em `plugins/handoff/lib/extract_ata.py`, a montagem de `last_plan` guarda `"excerpt": txt[:1200]` e a de `last_plan["likely_executed"]` avalia `commits_after > 0 or edits_after >= 3` — 1 commit carimbava um plano de 10 fases como executado. `[confirmado — leitura das duas atribuições neste run]`

**Passos:**

1. **Autoria, uma vez** — a skill escreve o plano em JSON e chama `python3 ${CLAUDE_PLUGIN_ROOT}/lib/plan_state.py init --file <f>`. `plan_state.py:validate` exige `id` de fase casando `^F\d+$`, de passo `^F\d+\.\d+$` com prefixo da própria fase, `title` não-vazio e **`desc` de no máximo 140 chars** (a linha didática que aparece na árvore). Devolve **todos** os erros de forma de uma vez. Grava em `<raiz>/.claude/plans/<id>.plan.json` via `os.replace` de um `.tmp`. `[confirmado]`
2. **Re-`init` num plano existente** — `plan_state.py:merge` preserva `status`/`evidence`/`done_at` do arquivo, acrescenta nó novo (já com estado default), **mantém** nó que sumiu do input (com aviso) e **RECUSA** id existente cujo `title` mudou, listando `no arquivo:` vs `no init:`. Renomear de propósito exige `--rename <id> "<novo>"`. `[confirmado — executado contra o plano real desta sessão: `⛔ init recusado: 1 nó(s) já existem com outro título`, exit 2, arquivo intacto]`
3. **Apresentação** — `plan_state.py page --mode approve` lê `skills/visual/template.html`, injeta `window.VISUAL_SESSION`, o cabeçalho **fixo** (`PAGE_COPY`) e a árvore de `render_html`, e grava em `<dir do /visual>/plano-<id>-<modo>.html`. Modo `approve` faz de cada fase um `.feedback-item` com os rádios `keep/change/remove`; modo `track` não emite rádio nenhum. Título e descrição passam por `html.escape` — o texto vem de prosa livre do modelo. `[confirmado]`
4. **Marcação** — `plan_state.py tick <id> --evidencia "<prova>"` recusa: prova com menos de 8 chars, id de **fase** (`"tique os passos… a fase fecha sozinha"`) e id inexistente. Aceito, grava `status: done`, `evidence` e `done_at`. **A fase não tem estado próprio** — `phase_status()` deriva de seus passos, então não existe onde gravar "fase pronta com passo pendente". `[confirmado]`
5. **Acompanhamento** — `page --mode track` reescreve o **mesmo** caminho a cada vez; a aba aberta só precisa de refresh. `render --format text` dá a mesma árvore pro CLI e pro handoff.
6. **Sobrevivência** — `SessionStart` → `sessionstart-plan.sh` (cenário 7, item 7) ressuscita o plano e deixa o marco da sessão. `Stop` → `stop-plan-status.sh` (v1.7.x; desde a v1.7.3 ele **cria o marco da sessão** se não achar, porque plugin instalado no meio da sessão perde o `SessionStart` e o hook ficava mudo pra sempre naquela sessão) **resume o progresso ao fim de CADA turno**: 1-3 bullets vindos de `plan_state.py brief` — 📍 *Feito · Agora · Falta* em andamento, ✅ **CONCLUÍDO** quando todos os passos fecharam, 🏁 **PLANO ENCERRADO** uma vez após o `close`. O texto mora no Python, não no hook, porque bullet em heredoc de shell não é testável. Quando o marco existe, nenhum `*.plan.json` é mais novo que ele e o transcript tem ≥3 edições, a cobrança do tique **toma o lugar do bullet 'Falta'** (1× por sessão × projeto) — nunca vira um 4º, porque o teto de 3 é do próprio pedido. **Nunca bloqueia**; kill-switch `PLAN_STATUS=0` (tudo) ou `PLAN_NUDGE=0` (só a cobrança). `[confirmado — `test_plan_hooks.sh`, 30 checks]`
7. **Handoff** — `plugins/handoff/skills/handoff/SKILL.md` manda checar `ls <project_root>/.claude/plans/*.plan.json` **antes** de olhar `last_plan`; havendo arquivo, ele manda e os títulos/ids vão exatos pro PRD. `[confirmado — o bloco existe no SKILL.md; o comportamento do agente que o obedece não foi exercitado neste run]`

**Termina em:** `.claude/plans/<id>.plan.json` versionado no git com o estado passo a passo, e uma página HTML regenerável a partir dele.

**Se falhar no passo N:**
- **1** (JSON inválido / `desc` de parágrafo / id fora do padrão) → `exit 2` com a lista completa de erros; nada é gravado.
- **2** (rename não autorizado) → `exit 2`; o arquivo **não** é tocado.
- **3** (`template.html` ausente, diretório do `/visual` não resolvível) → `PlanError` → `exit 2` com o caminho que faltou.
- **4** (sem `--evidencia`) → `exit 2` com o texto que explica por que a prova é exigida.
- **6** (sem `jq`, sem `python3`, sem plano ativo, plano encerrado já confirmado) → **todos** saem `exit 0` calados. Sem marco de sessão o resumo ainda sai; o que não sai é a cobrança (não dá pra saber o que foi marcado nesta sessão). O caso "sem marco" é deliberado: um falso *"você não marcou nada"* ensina a ignorar o aviso. `[confirmado — 6 checks de silêncio em `test_plan_hooks.sh`]`

> Os dois hooks novos usam `command -v jq` (não o `/opt/homebrew/bin/jq` hardcoded do `pre-exitplan-visualize.sh` — ver Pendências). `[confirmado]`

---

## 10 · Varredura de contrato dos hooks (o gate de commit, check E)

**Dispara quando:** um `git commit` cujo conjunto de arquivos toca `plugins/*/hooks/`.

**Passos:**

1. `.claude/hooks/release-gate.sh` (PreToolUse[Bash]) já intercepta o `git commit`; o check E só entra se `FILES` casar `^plugins/[^/]+/hooks/`. `[confirmado]`
2. Roda `python3 scripts/hook_contract.py --baseline .claude/hook-contract.baseline.json --fail-on high`.
3. O checker lê os **33 registros dos 10 `hooks.json`** (contagem derivada nesta rodada; a saída do próprio checker diz *"33 registros, 32 scripts distintos"* — 33 e não 32 desde que o `bootstrap` ganhou o `Stop` do cenário 12), resolve `${CLAUDE_PLUGIN_ROOT}` pro caminho real e mede 5 propriedades por script (canal, cap, kill-switch, binário fixo, fail-open). Regras `R0`–`R5`.
4. `--baseline` subtrai o que já estava no retrato: **só o que piorou** vira achado. `--fail-on high` devolve exit 1 nesse caso, e o gate transcreve o bloco no motivo do bloqueio.

**Termina em:** exit 0 silencioso (o caso comum) ou `🚧 release-gate BLOQUEOU o commit` com `❌ CONTRATO DE HOOK`.

**Verificado nos dois sentidos neste run:** com um hook de teste usando `/opt/homebrew/bin/jq`, saiu `R4-binario-fixo` + exit 1; removido o hook, `Nenhum achado` + exit 0. `[confirmado]`

**Se falhar:** `scripts/hook_contract.py` ou o baseline ausentes → o check é pulado (o `if [ -f … ]` guarda os dois). Fail-open, como o resto do gate.

> O mesmo commit acrescentou o **check F**: as suites `plugins/<nome>/hooks/test_*.sh` dos plugins tocados passam a rodar no gate. Antes só as `.py` entravam — as shell eram manuais e por isso apodreciam. `[confirmado — `patterns.md §5.2`]`

---

## 11 · A pergunta com opções é devolvida por não se explicar (guardrails 1.3.0)

**Dispara quando:** o modelo chama `AskUserQuestion`. ⚠️ **Que este evento dispare nesse tool é `[inferido]`** — a doc oficial do harness diz *"PreToolUse matchers support all tool names"* (consultada 2026-07-30), e nenhuma invocação real foi observada. O `askq.log` vazio em `~/.claude/guardrails/` é o marcador dessa pendência.

**Por que existe:** a pergunta com opções é o único ponto em que o modelo escreve direto na tela do usuário sem passar por doc, plano ou HTML — e era o único sem gate. A regra contra a pergunta sem contexto existia só em prosa no `CLAUDE.md` ("PERGUNTAR SEM ARTEFATO DE APOIO") e não pegava.

**Passos:**

1. `plugins/guardrails/hooks/askq-humanize.sh` (PreToolUse[AskUserQuestion], 10s). Sai calado se `ASKQ_GATE=0`, se faltar `jq`/`python3`, se não houver `session_id`, ou se `lib/askq_lint.py` não for legível. `[confirmado — os 4 casos de fail-open em test_askq_gate.sh]`
2. **Loga sempre, antes de julgar:** `askq.log` recebe `ts · session · rc` + o `tool_input` cru (`jq -c`, cortado em 4000 chars). Vale para pergunta limpa também — é o que fecha a lacuna de verificação do gatilho.
3. `python3 lib/askq_lint.py` mede **três** coisas, e só as que são medíveis: nome de código em `question`/`header` (`CODE_TELLS`), `description` de opção com menos de `MIN_DESC=30` chars, e `question` com menos de `MIN_Q=80` chars **e** zero `preview`. Exit 1 = violou; qualquer outro código ⇒ fail-open. `[confirmado — 40 checks em test_askq_lint.py]`

   **Maiúscula no meio da palavra saiu do regex e virou lista de exceção** (2026-07-30). As duas regras `camelCase`/`CamelCase` de `CODE_TELLS` foram removidas e substituídas por `_MEIO_MAIUSCULO` + `camel_suspeitas()`, que descarta o que estiver em `NOMES_PROPRIOS` (frozenset com `github`, `javascript`, `macos`, `postgresql`, `whatsapp`, `vscode`…, comparação em minúsculas) e só então acusa `maiuscula_no_meio`. Motivo medido: a **primeira pergunta real** que passou pelo gate foi barrada por *"o commit já está no GitHub"* — grafia normal de nome próprio tratada como identificador. `[confirmado — `plugins/guardrails/lib/askq_lint.py`, `NOMES_PROPRIOS`/`camel_suspeitas`]`
4. Cap de `MAX_NUDGES=3` em `askq.count.<session_id>`; estourado, o hook libera. Sessão nova começa do zero — a chave é por sessão pela regra do `patterns.md §1.5`. `[confirmado — os 5 casos de cap em test_askq_gate.sh]`
5. Violou e há cap: emite `permissionDecision:"deny"` em JSON no stdout com **as violações concretas** no motivo, e sai `exit 0` (o veredito vem do JSON, não do exit code — convenção do repo).

**Termina em:** o modelo recebe a lista do que faltou e reescreve a pergunta. **O hook nunca reescreve** — decisão de projeto de 2026-07-30: reescritor por LLM custaria espera antes da tela abrir e poderia inventar contexto que o modelo nunca teve.

**O que ele NÃO faz:** julgar se a premissa está clara. Isso não é régua, é julgamento, e continua com o modelo.

**Se falhar:** toda borda é fail-open (nunca prende a pergunta). Para desligar na sessão: `ASKQ_GATE=0`. Para afrouxar as réguas, os dois números vivem juntos no topo de `askq_lint.py`.

---

## 12 · ENCERRAMENTO — o que roda no `Stop` (e o teto de prosa)

**Dispara quando:** o Claude termina um turno.

**Quantos são:** **5 deste repo — e 6 no total que roda de fato.** O glob `plugins/*/hooks/hooks.json` só enxerga o pedro-plugins; varrendo `~/.claude/plugins/cache/*/*/*/hooks/hooks.json` cruzado com `enabledPlugins` aparece um sexto, `codex@openai-codex` (`stop-review-gate-hook.mjs`, timeout declarado **900s** — o maior de todos, e **teto de um caminho que não roda**; ver a correção logo abaixo do quadro). Contar só o repo subestima o pedágio do fim de turno:

```
plugins/bootstrap/hooks/hooks.json     stop-prose-ceiling.py           timeout 10
plugins/handoff/hooks/hooks.json       handoff-completeness-gate.sh    timeout 30
plugins/intent-guard/hooks/hooks.json  delivery-audit.sh               timeout 60
plugins/project-doc/hooks/hooks.json   stop-doc-touch.sh               timeout 15
plugins/visual/hooks/hooks.json        stop-plan-status.sh             timeout 15
TOTAL 5 neste repo

(fora do repo, também habilitado:)
codex/scripts/stop-review-gate-hook.mjs      timeout 900
TOTAL REAL 6
```

Nenhum declara `matcher` útil (`visual` traz `"*"`), então **todos os 6 rodam em todo fim de turno**. A ordem entre plugins **não é determinável a partir deste repo** — mesma limitação do cenário 7. `[confirmado]`

**Correção (2026-07-30): os 900s do codex são teto, não custo.** O `stop-review-gate-hook.mjs` sai **antes** de qualquer review — `main()` lê o config e faz `if (!config.stopReviewGate) { logNote(runningTaskNote); return; }` na linha 154, e o default é `stopReviewGate: false` (no cache do plugin de terceiro, fora deste repo: `~/.claude/plugins/cache/openai-codex/codex/<versao>/scripts/lib/state.mjs`, linha 23, dentro de `defaultState()`). Só `/codex:setup` liga a flag, e o único workspace com estado gravado nesta máquina (`~/.claude/plugins/data/codex-openai-codex/state/<workspace>/state.json`) traz `{'stopReviewGate': False}`. Medido neste run com payload de `Stop` real: **0,44s · 0,62s · 0,31s** em 3 execuções. Os 900s são o orçamento do caminho ligado, que hoje não existe. `[confirmado — leitura dos dois arquivos + o `jq` no state + as 3 medições]`

### Quem bloqueia e quem só fala

**3 podem bloquear** (`decision:block` ou `exit 2`, o que devolve o motivo ao modelo e o mantém trabalhando), **2 são informativos puros**:

- **`stop-prose-ceiling.py`** — canal `exit 2` + stderr · trava: 2 bloqueios por (sessão, texto da resposta).
- **`handoff-completeness-gate.sh`** — canal `decision:block` · trava: o cap nativo `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` mais a flag `/tmp/claude-ata-gate-ok-<sha1(prd|sessão|mtime)>` que não re-julga um PRD já aprovado · kill-switch `HANDOFF_GATE=0`.
- **`delivery-audit.sh`** — canal `decision:block` · trava: 2 bloqueios por sessão em `/tmp/intent-guard-stopdeny-<sid>` · kill-switch `~/.claude/intent-guard/mode` = `off`. **Antes de bloquear ele tenta LIBERAR**: varre os `audit-*.json` do diretório do caderno (`ledger.py resolve-dir`) do mais novo pro mais velho, e o primeiro que passa no `audit-check` é transcrito (`apply-audit`) e fecha a cobrança. O ciclo inteiro — como o veredito é pedido, validado e consumido — está no cenário 14.
- **`stop-doc-touch.sh`** — canal `systemMessage`, nunca bloqueia · trava: 1× por (sessão × projeto), e o sentinel é marcado **antes** dos gates porque o caso comum é "nada a sugerir" · kill-switch `DOC_TOUCH_SUGGEST=0`.
- **`stop-plan-status.sh`** — canal `systemMessage`, nunca bloqueia · trava: 1× por (sessão × projeto) só para a cobrança de tique · kill-switch `PLAN_STATUS=0` (tudo) ou `PLAN_NUDGE=0` (só a cobrança). Detalhado no cenário 9, passo 6.

Os três que bloqueiam têm **gatilho estreito**, e é isso que impede o fim de turno de virar pedágio: o `handoff` só age quando um `HANDOFF.md` foi (re)escrito **depois** do manifest da mesma sessão; o `intent-guard` só age quando há **commit novo** desde a última cobrança (decisão de projeto de 2026-07-24 — *turno é a unidade do Claude, commit é o marco em que o trabalho virou entrega*); o teto de prosa age em **toda** resposta, mas só reprova o que estoura a régua. `[confirmado]`

### O teto de prosa, passo a passo

`plugins/bootstrap/hooks/stop-prose-ceiling.py` é o **mecanismo** por trás do que o output style `plugins/bootstrap/output-styles/clean-style.md` (`name: Clean Style`; era um style com o nome do dono do repo até `1999796`) pede em prosa (*"até 6 linhas de prosa no total"*). Os dois nascem ligados — o style por `force-for-plugin: true`, o hook por estar em `hooks/hooks.json`. `[confirmado — `plugins/bootstrap/skills/setup/SKILL.md`, item 3 "Contrato de forma"]`

1. **Kill-switch e fail-open** — `PROSE_CEILING=0` sai na primeira linha; stdin que não parseia como JSON sai `0`; `stop_hook_active` verdadeiro sai `0` (não re-entra no próprio bloqueio).
2. **Achar a resposta** — `ultima_msg_assistente()` lê o `.jsonl` de `transcript_path` **de trás pra frente**, pula linha com `isSidechain` (saída de subagente não é a resposta ao usuário) e devolve o primeiro texto de `role: assistant`, concatenando os blocos `type: "text"`. Transcript ilegível ou sem texto → `exit 0`.
3. **Contar prosa — e desde `ff32947` isso é OPT-IN.** `linhas_de_prosa()` apaga os blocos ```` ``` … ``` ```` (**prova, e prova não tem teto**) e as linhas de tabela/régua (`^\s*(?:\||\+?-{3,})`), depois conta o que sobra sem linha em branco. Mas o teto só existe se o ambiente trouxer `PROSE_CEILING_MAX` numérico: `TETO = int(_TETO_ENV) if _TETO_ENV.isdigit() else None`, e a reprovação está atrás de `if TETO is not None and len(prosa) > TETO`. **Sem a variável, nenhuma resposta é barrada por tamanho** — as reprovações do passo 4 que não dependem dela continuam ligadas. A docstring dá a razão: contar linha *"e preferencia de estilo do dono, nao regra universal"*, e o marketplace vai pra máquina de outra pessoa. `[confirmado — smoke desta rodada, hook real com transcript sintético: 9 linhas de prosa **sem** a variável → `exit 0` mudo; as **mesmas** 9 com `PROSE_CEILING_MAX=6` → `exit 2` com *"9 linhas de prosa, o teto e 6"*]`
4. **Três reprovações possíveis, e só uma é opt-in**, acumuladas numa lista: passar do teto (só com `PROSE_CEILING_MAX`); casar `RETORICA` (*"vale notar/lembrar/ressaltar"*, *"importante notar/destacar"*, *"cabe destacar"*, *"dito isso"*, *"em outras palavras"*, *"ou seja,"*, *"o que eu fiz foi"*, *"deixa eu explicar/contextualizar"*, *"antes de mais nada/continuar"*, *"para contextualizar/ficar claro"*, *"como eu mencionei/falei/expliquei/disse antes/acima/anteriormente"*); ou abrir um item de lista com `opção`/`alternativa` — *"menu de opções — decida e diga qual escolheu"*. **Estas duas rodam sempre**, e é a diferença entre elas e o teto que carrega o desenho: retórica de ligação e menu de opções são defeitos de forma que qualquer leitor reconhece; "quantas linhas cabem" é gosto de quem escreveu o hook. `[confirmado — smoke desta rodada: uma resposta de UMA linha com *"Vale notar"* → `exit 2` **sem** `PROSE_CEILING_MAX` no ambiente]`
5. **Trava anti-loop** — chave `sha1(session_id + texto INTEIRO)[:16]`, contador em `$CLAUDE_DIR/state/prose-ceiling/<chave>`, onde `CLAUDE_DIR = os.environ.get("CLAUDE_CONFIG_DIR", ~/.claude)` — **a mesma linha de `lib/conformance.py:26`**, e é dessa igualdade que depende o passo 6. Antes de 2026-07-30 o hook cravava `Path.home()`: com `CLAUDE_CONFIG_DIR` setada, ele escrevia num lugar e o verificador lia noutro, e o relatório dizia *"nenhuma resposta furou o teto"* com o teto furado. Falha silenciosa, não erro. Do 3º bloqueio da **mesma** resposta em diante o hook desiste. O hash usa o texto inteiro **de propósito**: com `texto[:200]` duas respostas diferentes dividiam o mesmo orçamento, e como o output style exige primeira linha estável, a colisão era o caso comum. `[confirmado — comentário no arquivo + os 3 runs do smoke abaixo]`
6. **Desistir não pode ser silencioso** — ao desistir, grava uma linha JSON em `$CLAUDE_DIR/state/prose-ceiling/bypass.log` com `session` (8 chars), `linhas_prosa`, `problemas` e o `trecho` inicial. `plugins/bootstrap/lib/conformance.py:check_bypass_teto` lê **esse mesmo caminho** (`CLAUDE_DIR / "state" / "prose-ceiling" / "bypass.log"`, linha 317) e transforma em desvio visível (*"N resposta(s) furaram o teto de prosa"*, com as 3 últimas amostras e o `rm` pra zerar). `[confirmado — `test_conformance.py` fecha o par com "o hook escreve o furo DENTRO de CLAUDE_CONFIG_DIR" + "o conformance LE o furo que o hook escreveu"; 52 ok · 0 FAIL neste run]`
7. **O que o modelo recebe** no `exit 2`: as violações concretas, o teste de corte (*"apague cada linha e veja se quem le perde informacao"*), um exemplo de resposta que passa, e a ordem de **reescrever a resposta inteira** em vez de acrescentar um resumo — mais o desvio: *"o que não couber vira `/visual` em HTML"*. `ff32947` tirou daqui a citação verbatim da reprovação do dono do repo e trocou a frase que nomeava o leitor por *"quem le perde informacao"*: mensagem de hook distribuído é lida por quem instalou o plugin, e nome próprio ali é ruído, não autoridade.

**Termina em:** o turno fecha (caso comum) ou o modelo reescreve a resposta.

**Smoke E2E** — hook real, transcript sintético, payload de `Stop`. O bloco abaixo é de
2026-07-30, quando o teto de 6 ainda era default; hoje ele só reproduz **com
`PROSE_CEILING_MAX=6` no ambiente** (passo 3):

```
--- run 1: exit=2 stderr='PROSA REPROVADA: 9 linhas de prosa, o teto e 6 …'
--- run 2: exit=2 stderr='PROSA REPROVADA: 9 linhas de prosa, o teto e 6 …'
--- run 3: exit=0 stderr=''            # desistiu, gravou no bypass.log
curto: 0
bloco de codigo grande: 0              # 40 linhas dentro de ``` não contam
retorica: 2  PROSA REPROVADA: retorica no meio: 'Vale notar'
kill-switch: 0                         # PROSE_CEILING=0
```

**Re-smoke desta rodada, medindo o opt-in** — mesmas 9 linhas de prosa, um transcript por
caso, `CLAUDE_CONFIG_DIR` num `mktemp -d`:

```
--- 9 linhas de prosa, SEM PROSE_CEILING_MAX:      exit=0  stderr=(vazio)
--- as mesmas 9 linhas, COM PROSE_CEILING_MAX=6:   exit=2  stderr=PROSA REPROVADA: 9 linhas de prosa, o teto e 6
--- retorica ('Vale notar'), SEM PROSE_CEILING_MAX: exit=2 stderr=PROSA REPROVADA: retorica no meio: 'Vale notar'
```

A terceira linha é a que fecha o desenho: **desligar o teto de tamanho não desligou o hook.**

E a linha que o run 3 acrescentou ao log:

```json
{"session": "SMOKE1", "linhas_prosa": 9, "problemas": ["9 linhas de prosa, o teto e 6"], "trecho": "linha de prosa numero 1"}
```

`[confirmado por smoke — o hook executa e retorna exit 2. NÃO confirmado que já disparou em turno real: no fim desta rodada o `bypass.log` tinha 1 registro e ele era do próprio smoke (`"session": "SMOKE1"`). Hook de plugin só carrega no SessionStart, então sessão aberta antes da instalação fica descoberta até o /clear]`

**Se falhar no passo N:**
- **1/2** (payload quebrado, transcript ausente, resposta sem texto) → `exit 0`. Um hook de forma que trava o usuário por bug próprio é pior que a prosa longa.
- **3** (bloco de código não fechado) → o `re.sub` guloso come do primeiro ```` ``` ```` até o último; a contagem sai **menor** que a real. Fail-open na direção certa. `[inferido — não reproduzido]`
- **5** (a mesma resposta reprova 3×) → o hook desiste e o turno fecha com a prosa fora do teto. **Teto conhecido e assumido**, não bug.

> ⚠️ **Sessão aberta antes da instalação fica descoberta.** Como todo hook de plugin, o `hooks.json` só é carregado no `SessionStart` — instalar o `bootstrap` no meio de uma sessão não liga o teto naquela sessão até o próximo `/clear`. `[relatado — docstring do próprio arquivo, medido por auditoria independente em 2026-07-30]`

---

## 13 · AVISO EM VEZ DE BLOQUEIO — a primeira busca e a primeira edição da sessão

**Dispara quando:** qualquer `PreToolUse` de `Grep`/`Glob`/`Bash`/`Agent` (busca) ou de `Edit`/`Write` (edição). Os dois casos mudaram em `781e923` (2026-07-30) na mesma direção: **um gate que bloqueia sem acrescentar informação é pedágio, não trava.** `[confirmado]`

### A busca: dois hooks registrados, um único `deny`

Dois plugins habilitados registram `PreToolUse` sobre a mesma ferramenta de busca:

```
plugins/project-doc/hooks/hooks.json     Grep|Glob|Bash|Agent  pretooluse-doc-guard.sh
plugins/graphify-guard/hooks/hooks.json  Grep|Glob|Bash        pretooluse-graphify-guard.sh  timeout 10
```

O `doc-guard` **nega** (`permissionDecision:"deny"`, linha 214 do arquivo) e tem o matcher mais largo. O `graphify-guard` mandava uma mensagem quase idêntica — *leia o grafo/a doc antes de sair grepando* — e negava também: **dois `deny` e dois round-trips antes de qualquer trabalho começar**, duas vezes na mesma sessão. Hoje ele emite `hookSpecificOutput.additionalContext`: o enquadramento chega inteiro, o segundo bloqueio some. **Voltar a bloquear:** `GRAPHIFY_DENY=1` — o ramo de `deny` continua no arquivo, só ficou atrás da flag. `[confirmado — os dois `hooks.json` + o `if` no fim de `pretooluse-graphify-guard.sh`]`

### A edição: `scope-cop` ganhou um terceiro modo

`plugins/guardrails/hooks/scope-cop.sh` (matcher `Edit|Write`, timeout 25, wired em `plugins/guardrails/hooks/hooks.json`; `guardrails@pedro-plugins=true` em `enabledPlugins`). Lê **uma linha** de `$HOME/.claude/guardrails/scope-cop.mode`:

- **`deny`** (default — `[ "$MODE" = "warn" ] || MODE="deny"`) → bloqueia e manda repensar; incrementa `scope-cop.blockstreak`, que libera 1 edição a cada `MAX_STREAK=3` bloqueios seguidos.
- **`warn`** (novo) → a edição **passa**; grava `0` no streak (*em aviso não há streak: nada foi bloqueado*), loga `WARN` e devolve `additionalContext` com o motivo e a receita de religar.
- **`off`** → `exit 0` na hora.

O modo `warn` existe porque o gate estava em `off` desde 02/07 depois de 3 bloqueios seguidos, e **plugin habilitado + gate `off` faz parecer que existe trava de escopo onde não existe** — exatamente o desvio que `conformance.py:check_gates_enganosos` acusa varrendo `CLAUDE_DIR/**/*.mode` atrás de `off`/`0`/`disabled` com o plugin correspondente vivo. **Nesta máquina o arquivo lido contém `warn`** (`cat ~/.claude/guardrails/scope-cop.mode`). `[confirmado]`

### E o verificador aprendeu a diferença

`conformance.py:check_hooks_duplicados` contava **registro** de `PreToolUse` por ferramenta. Depois que o `graphify-guard` virou aviso, isso acusava colisão inexistente. Agora ele resolve o caminho do script de cada entrada e chama `bloqueia()`: retorna `False` se o arquivo traz o marcador literal `# conformance: default-warn`, `True` se casa `permissionDecision` + `"deny"` ou `exit 2`, e `True` também quando **não consegue ler** (assume o pior). Entrada em que nenhum alvo bloqueia é pulada — só avisa, não disputa a ferramenta. A mensagem do desvio passou a dizer `N ferramenta(s) BLOQUEADA por mais de um plugin habilitado` e a remediação virou julgamento explícito: colisão só é defeito quando os gates têm o **mesmo propósito**; propósitos distintos no mesmo evento são camadas. `[confirmado — `conformance.py:check_hooks_duplicados`; `test_conformance.py` 52 ok · 0 FAIL neste run]`

**Área nova na saída do verificador: `dependencia` (bootstrap 1.7.0).** `check_ferramentas_externas` lê `ferramentas_externas.itens` do manifest, cruza `requerido_por` com os `enabledPlugins` **ligados** e só então testa `shutil.which(comando)` — plugin desligado sai antes do `which`, porque desvio permanente em quem não usa o recurso ensina a ignorar o relatório inteiro. O desvio traz `which <cmd> -> nada` + o campo `porque` como evidência, e o `instalar`/`alternativa` como conserto.

Saída real desta máquina, rodada nesta rodada (`python3 plugins/bootstrap/lib/conformance.py`, exit `1`):

```
⚠ 3 desvio(s) — nada foi alterado.
1. [plugins] graphify-guard@pedro-plugins devia estar DESLIGADO e esta ligado
2. [plugins] intent-guard@pedro-plugins  devia estar DESLIGADO e esta ligado
3. [hooks]   5 ferramenta(s) BLOQUEADA por mais de um plugin habilitado
       Agent: guardrails, project-doc      Bash: project-doc, ship
       Edit: guardrails, project-doc       Write: guardrails, project-doc
       ExitPlanMode: intent-guard, project-doc, visual

conforme: claude.md · teto · output style · skills · gate · teto · dependencia · catalogo
```

**Os dois desvios novos são a receita de `ff32947` chegando ao verificador, não uma regressão da máquina.** O manifest passou a declarar `graphify-guard` e `intent-guard` com `enabled: false` (cenário 1, passo 6a); a máquina os tem ligados desde antes. `check_plugins` compara os dois lados e mostra — é literalmente o trabalho dele. A área `plugins` saiu de `conforme` por isso, e a área `catalogo` **entrou** (checagem nova, §`architecture.md` §10.2): os 19 plugins publicados no `marketplace.json` estão todos na receita.

`dependencia` sai **conforme** aqui porque as duas pontas estão ligadas: `graphify-guard@pedro-plugins = true` em `enabledPlugins` **e** `command -v graphify` resolvendo pra um binário instalado em `~/.local/bin/`. `[confirmado — as duas checagens rodadas nesta rodada]` Note que a linha `conforme` repete `teto` (duas checagens diferentes usam a mesma etiqueta de área: `check_teto_unico` e `check_bypass_teto`) — a etiqueta não é chave única.

**Se falhar:**
- `graphify-guard` sem grafo ou já avisado nesta sessão → sai calado (o aviso é único por sessão).
- `scope-cop` sem `jq` **ou** sem `python3` no PATH → `exit 0` na linha 25. Fail-open: a trava fica destravada e nada no CLI diz isso — mesmo contrato do cenário 8.
- Marcador `# conformance: default-warn` esquecido num script que só avisa → o conformance volta a contá-lo como bloqueador e reporta uma colisão que não existe. O marcador é **texto**, não convenção de código: quem transformar um `deny` em aviso tem que escrevê-lo.

---

## 14 · O VEREDITO DE ENTREGA — como o bloqueio nasce, é validado e é consumido (intent-guard 0.5.0)

**Dispara quando:** o `Stop` do cenário 12 encontra pedido vivo e commit novo. Mas o ciclo não cabe num turno: **quem bloqueia e quem consome o veredito são a mesma linha de código rodando em `Stop` DIFERENTES** — e é dessa distância que saem os dois defeitos consertados em `a134e9c` (2026-07-30).

**Os hooks do plugin** — `plugins/intent-guard/hooks/hooks.json` registra **5 hooks em 4 eventos** `[confirmado — leitura do arquivo nesta rodada]`:

```
UserPromptSubmit                          capture-prompt.sh     timeout 10
PreToolUse   ExitPlanMode                 plan-gate.sh          timeout 60
PostToolUse  TaskUpdate                   task-checkpoint.sh    timeout 60
PostToolUse  Edit|Write|MultiEdit|NotebookEdit  mark-work.sh    timeout 5
Stop                                      delivery-audit.sh     timeout 60
```

### O bloqueio de entrega, passo a passo

1. **Bloqueia e ANOTA a pergunta.** Antes de emitir o `decision:block`, `delivery-audit.sh` grava um **sidecar** `<arquivo-de-auditoria>.escopo` — o JSON `[ids]` dos pedidos vivos **daquele instante**, os mesmos que ele acabou de colar no bloco `DADOS` do prompt do auditor. Sidecar e não campo dentro do JSON porque **o JSON ainda não existe**: quem o escreve é o subagente auditor, no fim.
2. **O agente despacha o auditor** (subagente de contexto virgem, prompt canônico verbatim) e ele escreve `.claude/intent/audit-<ts>.json` com um veredito por pedido, cada um com `evidence`.
3. **O `Stop` seguinte consome.** `ledger.py:audit_check` lê o sidecar e valida **a interseção `perguntados ∩ vivos`** — não a lista de vivos do momento da leitura. Sem sidecar (auditoria anterior ao conserto), cai no comportamento antigo: cobra todos os vivos. `[confirmado — `test_ledger.py` afirma os dois lados: com sidecar o pedido que chegou depois não reprova; apagando o sidecar o mesmo arquivo volta a reprovar por `sem veredito`]`
4. **A checagem de frescor ficou seletiva.** `audit.tree_hash != tree_hash(cwd)` sozinho não vence mais o veredito: `_arquivos_citados` extrai do texto de `evidence` os tokens com cara de caminho, `_arquivos_mexidos` roda `git diff --name-only <hash_da_auditoria> <hash_atual>`, e só há reprovação se os dois conjuntos se cruzam. **Sem citação nenhuma, ou sem conseguir rodar o git, reprova** — `_arquivos_mexidos` devolve `None` e quem chama trata `None` como vencido. Não-saber nunca vira aprovação (a regra do `patterns.md §2.2`). O `tree_hash` dos dois lados já ignora lixo de execução (`ledger.py:EXEC_ARTIFACTS`), e a lista **deixou de ser só de Python** no mesmo commit: entraram `dist`, `build`, `.vite`, `.next`, `.turbo`, `playwright-report`, `test-results` e `coverage`, para que projeto JS/TS que versione build não vença o próprio veredito.
5. **Passou → transcreve e libera.** `apply-audit` baixa o que veio `feito`+`confirmado`, o marco avança pro commit auditado e o `/tmp/intent-guard-stopdeny-<sid>` é apagado.

**O defeito que isso conserta (a catraca):** o bloqueio pergunta pelos vivos do instante T, o veredito só é lido em T+1, e **cada mensagem que o usuário manda no meio vira pedido vivo novo**. O veredito nascia impossível de aprovar, nunca era transcrito, e o pedido ficava vivo para sempre. Medido em 30/07: **33 pedidos vivos** cobrados de uma auditoria que tinha perguntado por **1**. `[relatado — o número está nos comentários de `delivery-audit.sh` e de `ledger.py:audit_check`, não foi remedido aqui]`

**O segundo defeito, mais sutil:** agir sobre um achado da própria auditoria vencia o veredito que acabara de chegar (o auditor aponta código morto, o agente remove, o tree muda, o veredito morre). Daí o passo 4 olhar **o que** mudou, não **se** mudou.

### O checkpoint de task

`task-checkpoint.sh` (PostToolUse `TaskUpdate`) julga por LLM se o trabalho recente derivou dos pedidos vivos quando uma task vira `completed`. Ele tinha teto de **1 bloqueio por task** (`/tmp/intent-guard-ckptblock-<sid>-<cksum(taskId)>`) — e teto por task não segura nada quando a acusação é falsa: **cada task nova ganha sentinela limpa e a mesma acusação volta indefinidamente**. Ganhou um segundo teto, **por sessão**, `/tmp/intent-guard-ckptcap-<sid>`, com **o mesmo mecanismo e o mesmo número (2) do `delivery-audit.sh`** — deliberadamente, para não inventar um segundo padrão de cap no mesmo plugin.

**Termina em:** o turno fecha e a auditoria some do caminho, ou o modelo recebe a lista de pedidos sem veredito e despacha o auditor.

**Se falhar:**
- Sem `jq`/`python3`, sem `session_id`, ou `mode=off` → `exit 0` calado, em todos os cinco hooks.
- `printf … > "${OUTP}.escopo"` falha (disco cheio, `/…/intent` sumiu) → o `2>/dev/null` engole e o `Stop` seguinte volta ao comportamento antigo: cobra todos os vivos. Fail-open na direção **estrita**, não na permissiva. `[inferido — não reproduzido]`
- Ninguém apaga os `.escopo` órfãos; eles se acumulam em `.claude/intent/` junto com os `audit-*.json`.

> ⚠️ **`plugins/intent-guard/hooks/test_task_checkpoint.sh` está VERMELHA desde `a134e9c`.** A suíte encadeia **3** bloqueios de drift na mesma sessão (`cksid`): caso 2 (`taskId 7`), caso 6a (`a.b`) e caso 6b (`a/b`, que existe para provar que sentinelas de `a.b` e `a/b` não colidem). O teto de sessão silencia o terceiro, o `grep -q '"decision"'` da linha 72 falha e o `set -e` derruba a suíte — os casos 7 (plano aberto no contexto do juiz) **nunca rodam**. `[confirmado nesta rodada: `bash -x` mostra `OUT2=` vazio na linha 72; a suíte imprime `drift block 1 OK` e sai 1]` Some com isso um segundo problema: o `trap` da linha 6 limpa `/tmp/intent-guard-ckptblock-cksid-*` mas **não** o `ckptcap`, então o contador sobrevive entre execuções e a suíte fica vermelha mesmo depois de consertada, até alguém apagar o arquivo à mão.

---

## Pendências

- [TODO: `plugins/intent-guard/hooks/test_task_checkpoint.sh` vermelha — o teto por sessão do cenário 14 corta o 3º bloqueio que a própria suíte exige, e o `trap` não limpa `/tmp/intent-guard-ckptcap-<sid>`.]
- [TODO: `plugins/intent-guard/hooks/mock_ck_drift.sh` e `mock_ck_ok.sh` são artefato de teste versionado em `a134e9c` — `test_task_checkpoint.sh` os escreve (linhas 25 e 41) e os apaga (linha 102), e o conteúdo versionado é byte a byte o do heredoc. Que tenham sobrado porque a suíte morre antes do `rm` é `[inferido]`; que sejam artefato e não fonte é `[confirmado]`.]
- [TODO: ordem de execução de hooks `SessionStart` entre plugins distintos — não determinável a partir deste repo; exigiria documentação ou instrumentação do harness do Claude Code.]
- [TODO: os 5 ponteiros cross-tool mandam ler `CLAUDE.md` na raiz, que não existe neste repo (o índice é `.claude/CLAUDE.md`).]
- [TODO: ponte statusLine do context-guard não está wired nesta máquina — rodar a skill `context-guard:setup`.]
- [TODO: `plugins/context-guard/skills/setup/SKILL.md` documenta a saída do guard como `{"continue":false,...}`; o código emite `{"decision":"block",...}` desde a v1.3.0.]
- [TODO: apagar `pi-plugins/` — cópia untracked e obsoleta que envenena o grafo.]