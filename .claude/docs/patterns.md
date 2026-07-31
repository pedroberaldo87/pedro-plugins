---
generated: 2026-07-31
generated-commit: a57ea6e
project: pedro-plugins
scope:
  - .claude/hooks/release-gate.sh
  - .claude/settings.json
  - scripts/sync-shared.sh
  - _shared/green-cache.sh
  - plugins/project-doc/hooks/pretooluse-doc-guard.sh
  - plugins/project-doc/hooks/posttooluse-doc-read.sh
  - plugins/project-doc/hooks/doc-detect.sh
  - plugins/project-doc/hooks/lib-project-root.sh
  - plugins/project-doc/hooks/pretooluse-plan-gate.sh
  - plugins/project-doc/hooks/userpromptsubmit-plan-escape.sh
  - plugins/project-doc/hooks/test_plan_gate.sh
  - plugins/project-doc/lib/doc_lint.py
  - plugins/project-doc/lib/pattern_check.py
  - plugins/ship/hooks/pre-deploy-test-check.sh
  - plugins/context-guard/hooks/context-guard-writer.sh
  - plugins/guardrails/hooks/scope-cop.sh
  - .claude-plugin/marketplace.json
  - plugins/visual/lib/visual_page.py
  - plugins/slides/lib/md2deck.py
  - plugins/guardrails/lib/askq_lint.py
  - plugins/bootstrap/hooks/stop-prose-ceiling.py
  - plugins/bootstrap/lib/conformance.py
verified-by:
  - .claude/hooks/release-gate.sh
  - plugins/ship/hooks/test_pre_deploy.sh
  - scripts/sync-shared.sh
  - plugins/project-doc/hooks/test_plan_gate.sh
  - plugins/project-doc/lib/test_doc_lint.py
  - plugins/project-doc/lib/test_pattern_check.py
  - plugins/visual/lib/test_visual_page.py
  - plugins/slides/lib/test_md2deck.py
  - plugins/guardrails/lib/test_askq_lint.py
  - plugins/guardrails/hooks/test_scope_cop.sh
  - plugins/graphify-guard/hooks/test_graphify_guard.sh
  - plugins/guardrails/hooks/test_setup_skill.sh
doc-sig: pedro-plugins/release-gate.sh@gen=3.8#68505712
---

# Patterns & Gotchas

Convenções deste marketplace. Tudo aqui é regra observada no código, não estilo sugerido.
Rótulos: **[confirmado]** = executado/lido nesta rodada · **[inferido]** = deduzido, não testado · **[relatado]** = veio do journal/memória.

---

## 1 · Shell (hooks)

### 1.1 Fail-open é lei

Hook que erra **libera a ação**. A frase aparece literal no cabeçalho de vários hooks — derivado mecanicamente neste run:

```bash
grep -rl -i 'fail-open\|fail open\|fail-OPEN' plugins/*/hooks/*.sh .claude/hooks/*.sh _shared/*.sh
# → 30 arquivos neste run; inclui as suítes test_*.sh, que herdam a convenção
```

Arquivos que **declaram** a regra no comentário de topo, entre eles [confirmado]:

- `.claude/hooks/release-gate.sh` — *"FAIL-OPEN em erro de infra (sem git/python3, fora do repo): só bloqueia com evidência concreta na mão."*
- `plugins/project-doc/hooks/doc-detect.sh` — *"Fail-open: any error → no output, exit 0. Never blocks the caller."*
- `plugins/project-doc/hooks/pretooluse-doc-guard.sh` — *"Fail-open: any error → exit 0 (action proceeds)."*
- `plugins/ship/hooks/pre-deploy-test-check.sh` — `command -v jq >/dev/null 2>&1 || exit 0`, com o comentário *"(marketplace convention)"*
- `_shared/green-cache.sh` — *"Fail-open na direção SEGURA: qualquer erro → MISS → a suite roda."*

**Nuance que NÃO é fail-open** [confirmado]: em `pretooluse-plan-gate.sh` o fail-open só cobre a borda de **infra** (sem `jq`, sem raiz resolvível, `doc-detect.sh` ilegível). Determinar que *não há documentação* é evidência concreta → nega. A guarda `[ -r "$SCRIPT_DIR/doc-detect.sh" ] || exit 0` existe exatamente porque um `chmod 000` no helper fazia um projeto documentado cair no caso "sem doc" e ser negado sem cap — regressão coberta pelo caso R7 de `test_plan_gate.sh`.

Corolário oposto em `green-cache.sh`: o lado seguro do cache é **MISS** (roda a suite de novo), não HIT. Fail-open sempre aponta para o lado que não mente.

### 1.2 Protocolo de saída de hook

Três canais, escolhidos por evento e por intenção:

- **`exit 0` mudo** — libera. É o default de todo hook fora do seu escopo (`case "$TOOL" in ... *) exit 0 ;;`). ⚠️ **"Mudo" é literal, e vale pra stderr também.** A doc do harness [confirmado — `code.claude.com/docs/en/hooks`, consultada em 2026-07-30]:

  > *"Exit 0 means success. Claude Code parses stdout for JSON output fields. JSON output is only processed on exit 0. **For most events, stdout is written to the debug log but not shown in the transcript.** The exceptions are `UserPromptSubmit`, `UserPromptExpansion`, and `SessionStart`, where stdout is added as context that Claude can see and act on."*

  **`PreToolUse` e `PostToolUse` NÃO estão entre as exceções.** Logo: `echo "aviso" >&2; exit 0` num hook desses não chega ao modelo **nem ao usuário** — vai pro debug log. Foi assim que os 4 avisos do gate de deploy do `ship` ficaram invisíveis por meses, **incluindo** `⚠️ nenhum test runner detectado — deploy permitido sem verificação`: o gate anunciava que estava desligado, para ninguém.

  **O canal certo pro caminho que LIBERA é JSON no stdout** — `additionalContext` entra no contexto do modelo (aparece ao lado do tool result) e `systemMessage` aparece pro usuário. Ver `ship/hooks/pre-deploy-test-check.sh:allow_with_notes` como referência: acumula em `NOTES` e emite um JSON só no fim, porque um `exit 0` pode ter vários avisos.

  **Exposição atual do repo** [confirmado, derivado nesta rodada]:

  ```
  arquivo                                        >&2  exit2  JSON   evento
  plugins/ship/hooks/pre-deploy-test-check.sh      5   sim    sim   PreToolUse   ← consertado v1.3.6
  plugins/visual/hooks/pre-exitplan-visualize.sh   4   sim    não   PreToolUse
  plugins/guardrails/hooks/lint-and-typecheck.sh   3   sim    não   PostToolUse
  plugins/intent-guard/hooks/plan-gate.sh          1   sim    não   PreToolUse
  plugins/bootstrap/hooks/post-plugin-command.sh   1   NÃO    não   PostToolUse  ← mudo
  plugins/bootstrap/hooks/session-sync.sh          1   NÃO    não   SessionStart ← mudo (a exceção do SessionStart é pro STDOUT, não pro stderr)
  plugins/bootstrap/hooks/stop-prose-ceiling.py    1   sim    não   Stop         ← .py, e o stderr é o canal CERTO aqui
  ```

  A última linha é o primeiro hook **não-`.sh`** do repo [confirmado — `find plugins -path '*/hooks/*' -type f ! -name '*.sh' ! -name '*.json' ! -name '*.md'` devolve **1** arquivo]. Ele é registrado com o interpretador embutido no `command` (`"python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/stop-prose-ceiling.py\""`, `timeout: 10`), e escreve em stderr **só** no caminho que sai 2 — que num hook de `Stop` é o canal que devolve o texto ao modelo. O uso está certo; o que quebra é a **auditoria** dele (§5.3).

  Os dois do `bootstrap` escrevem em stderr e **nunca** saem 2, então o aviso é mudo por construção. Os que têm `exit 2` podem estar corretos (stderr no bloqueio **é** devolvido ao modelo) — mas cada sítio precisa ser conferido um a um: o do `ship` tinha os dois usos misturados no mesmo arquivo. Régua mecânica:

  ```bash
  # aviso em hook que NÃO bloqueia: candidato a mudo
  grep -ln '>&2' plugins/*/hooks/*.sh | grep -v test_ | xargs grep -Ll 'exit 2'
  ```
- **`exit 2` + mensagem em stderr** — bloqueia de fato; o stderr vai pro modelo. Usado onde não há decisão estruturada a emitir. Arquivos com `exit 2` (derivado com `grep -rln 'exit 2' plugins/*/hooks/*.sh .claude/hooks/*.sh`): `.claude/hooks/release-gate.sh`, `plugins/guardrails/hooks/lint-and-typecheck.sh`, `plugins/intent-guard/hooks/plan-gate.sh`, `plugins/ship/hooks/pre-deploy-test-check.sh`, `plugins/visual/hooks/pre-exitplan-visualize.sh` (+ a suíte `plugins/intent-guard/hooks/test_plan_gate.sh`).
- **JSON no stdout** — o canal estruturado do PreToolUse/PostToolUse/UserPromptSubmit:

```bash
# DENY (PreToolUse) — pretooluse-doc-guard.sh, pretooluse-plan-gate.sh, askq-humanize.sh
jq -n --arg r "$MSG" \
  '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
exit 0

# INJETAR CONTEXTO (PostToolUse / UserPromptSubmit) — sem permissionDecision
jq -n --arg c "$MSG" \
  '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$c}}'
```

Regra de desenho por trás disso [confirmado, comentário em `posttooluse-doc-read.sh`]: **PostToolUse injeta, nunca nega** — é "estruturalmente incapaz de loopar", ao contrário de um deny no `Read`, que bloquearia justamente a ação que resolve o sentinel.

Note que **quem emite deny sai com `exit 0`**: o veredito vem do JSON, não do exit code. Misturar os dois (JSON + `exit 2`) não é praticado em nenhum hook lido aqui.

### 1.3 Contrato anti-loop: o cap de nudges

Gate degrada, nunca trava de verdade. Padrão repetido em `pretooluse-doc-guard.sh` e `pretooluse-plan-gate.sh`:

```bash
MAX_NUDGES=3
COUNT_FILE="/tmp/claude-doc-guard-count-${SESSION}-${PHASH}"
COUNT=0; [ -f "$COUNT_FILE" ] && COUNT="$(cat "$COUNT_FILE" 2>/dev/null)"
[ "$COUNT" -eq "$COUNT" ] 2>/dev/null || COUNT=0     # sanitiza lixo no arquivo
[ "$COUNT" -ge "$MAX_NUDGES" ] && exit 0             # desistiu → libera
echo $((COUNT + 1)) > "$COUNT_FILE"
```

**A chave do cap tem que ser mais grossa que a coisa que se repete** (intent-guard 0.5.0, 2026-07-30) [confirmado — `task-checkpoint.sh` linhas 24-39]. `task-checkpoint.sh` tinha cap **por task** (`/tmp/intent-guard-ckptblock-<sid>-<cksum(taskId)>`), o que parece certo: uma acusação por task. Só que quando a acusação é **falsa**, cada task nova ganha sentinela limpa e a mesma acusação volta pelo resto da sessão — o cap existia e não capava nada. O conserto foi somar um segundo teto, **por sessão** (`/tmp/intent-guard-ckptcap-<sid>`), com **o mesmo idioma e o mesmo número (2) do `delivery-audit.sh`** do mesmo plugin, e o comentário diz por quê: *"pra não inventar um segundo padrão"*. Régua: cap por unidade fina (task, arquivo, ferramenta) é **complemento**, nunca substituto do cap por sessão; e quando dois hooks do mesmo plugin capam, os dois usam a mesma forma e o mesmo número, senão o teto vira folclore por arquivo.

⚠️ **Cap novo obriga a reler a suíte que conta bloqueios.** O teto de sessão entrou sem que `test_task_checkpoint.sh` fosse ajustada, e a suíte encadeia **3** drifts na mesma sessão — o terceiro virou silêncio e ela está **vermelha** desde `a134e9c`. Pior: o `trap` dela limpa `/tmp/intent-guard-ckptblock-cksid-*` e **não** o `ckptcap`, então o contador sobrevive entre execuções. **Estado novo em `/tmp` entra no `trap` do teste no mesmo commit em que nasce.** `[confirmado — ver `runtime.md` cenário 14]`

**Exceção deliberada** [confirmado]: o CASO A do `pretooluse-plan-gate.sh` (projeto com zero documentação) **nega sempre, sem cap** — decisão de projeto registrada no cabeçalho do arquivo. O único escape é verbal, via `userpromptsubmit-plan-escape.sh`. Coberto pelo caso de teste `sem doc: nega nas 5 tentativas, sem cap de nudges`.

### 1.4 Estado mutável: `~/.claude/`, NUNCA dentro do plugin

O diretório do plugin (`${CLAUDE_PLUGIN_ROOT}`) é um **cache reescrito a cada bump de versão** — gravar estado lá o apaga sem aviso. O comentário está literal em `_shared/green-cache.sh`:

> Estado em `~/.claude/green-suite/` (NUNCA dentro do plugin — o cache `${CLAUDE_PLUGIN_ROOT}` é reescrito a cada bump de versão).

Locais de estado em uso hoje, por plugin [confirmado, `grep -rn 'HOME/\.claude'`]:

- `$HOME/.claude/green-suite/` — `_shared/green-cache.sh:GREEN_SUITE_DIR` (override por env de mesmo nome)
- `$HOME/.claude/guardrails/` — `plugins/guardrails/hooks/scope-cop.sh:HOOK_DIR` (`scope-cop.mode`, `scope-cop.log`, `scope-cop.blockstreak`)
- `$HOME/.claude/intent-guard/mode` — kill-switch do intent-guard (`capture-prompt.sh`, `plan-gate.sh`, `delivery-audit.sh`, `task-checkpoint.sh`, `mark-work.sh`)
- `$HOME/.claude/intent/<slug>` — `plugins/intent-guard/lib/ledger.py` (fallback fora de git)
- `$HOME/.claude/context-guard/mode` — kill-switch do context-guard
- `$HOME/.claude/plugins/…` — `plugins/bootstrap/hooks/session-sync.sh` (marketplace cache, lock, last-sync)
- `$HOME/.claude/state/prose-ceiling/` — `plugins/bootstrap/hooks/stop-prose-ceiling.py:ESTADO` (um arquivo-contador por `sha1(session_id + texto)` + o `bypass.log`)

Padrão derivado: **kill-switch = um arquivo de uma linha em `~/.claude/<plugin>/mode`** com `off`. Vale para guardrails, intent-guard e context-guard [confirmado].

⚠️ **Mas "ligado ou desligado" é pouco: o flag do scope-cop virou ternário `deny|warn|off`** (guardrails 1.4.0, 2026-07-30) [confirmado — `scope-cop.sh` lê `~/.claude/guardrails/scope-cop.mode` e faz `[ "$MODE" = "off" ] && exit 0`, depois `[ "$MODE" = "warn" ] || MODE="deny"`]. O motivo está literal no cabeçalho do arquivo e é a lição durável: o gate ficou em `off` **desde 02/07**, depois de 3 bloqueios seguidos, e o estado meio-ligado — plugin instalado, hook registrado, gate off — **faz parecer que existe trava de escopo onde não existe**. Um terceiro estado que só avisa é honesto; silêncio não. No `warn` o veredito `block` vira `additionalContext`, zera o `blockstreak` (não houve bloqueio a contar) e loga `WARN` em vez de `BLOCK`. **Gate que você vai acabar desligando devia nascer com o degrau do meio.**

✅ **A raiz do estado é `${CLAUDE_CONFIG_DIR:-$HOME/.claude}`, não `$HOME/.claude` cru — e os dois lados da mesma dupla divergiam. CONSERTADO em 2026-07-30** (bootstrap 1.4.0). `bootstrap/hooks/lib/apply-config.sh`, `bootstrap/config/settings-defaults.json` e `bootstrap/lib/conformance.py:CLAUDE_DIR` já respeitavam a env var; `stop-prose-ceiling.py:ESTADO` era `Path.home() / ".claude" / …` **fixo**, então o hook gravava o `bypass.log` num diretório e o `check_bypass_teto` lia de outro. A direção do erro era a ruim: log ausente ⇒ o relatório afirma *"nenhuma resposta furou o teto de prosa"* — "não sei" virando "zero", exatamente o que o §2.2 proíbe. Hoje o hook tem `CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))`, com o comentário apontando pro `conformance.py` como fonte da regra.

**A lição durável é sobre o TESTE, não sobre a env var: par escritor↔leitor precisa de um teste que rode OS DOIS programas.** Nenhuma suíte só do hook, nem só do conformance, pegaria isso — cada lado estava coerente consigo mesmo. `test_conformance.py:teste_escritor_e_leitor_concordam` roda o hook 3× com `CLAUDE_CONFIG_DIR` apontando pra um `mktemp`, exige o vetor `[2, 2, 0]` (bloqueia duas vezes e desiste), afirma que o `bypass.log` nasceu **dentro** do tmp, e só então roda o `conformance.py` e exige o desvio na saída. Um teste, os dois processos de verdade [confirmado — `python3 plugins/bootstrap/lib/test_conformance.py` → `52 ok · 0 FAIL` nesta rodada].

### 1.5 Estado por-sessão em `/tmp` tem que ser chaveado por `session_id`

Regra nascida de um bug real. Journal [confirmado contra o código atual]: `/tmp/claude-context-pct` era **global**; com ~20 sessões paralelas, a última statusLine a renderizar sobrescrevia o arquivo e uma sessão cheia (80%) fazia o guard bloquear todas — inclusive sessões a 15%.

Hoje o código está assim:

```bash
# plugins/context-guard/hooks/context-guard-writer.sh
[ -n "$PCT" ] && [ -n "$SID" ] && printf '%s' "$PCT" > "/tmp/claude-context-pct-${SID}"

# plugins/context-guard/hooks/context-guard.sh
STATE="/tmp/claude-context-pct-${SESSION_ID}"
SENTINEL="/tmp/claude-context-warned-${SESSION_ID}"
```

E `context-guard-reset.sh` remove **só os arquivos da própria sessão** (o glob `rm -f /tmp/claude-context-warned-*` era o amplificador do bug). A regra vale para todo hook do repo, não só esse.

### 1.6 PHASH: a chave dos sentinels precisa nascer da MESMA string

**A armadilha mais cara do repo.** Sentinel em `/tmp` é chaveado por `(session_id × projeto)`, e o projeto entra como `cksum` da string da raiz:

```bash
# plugins/project-doc/hooks/lib-project-root.sh
project_hash() { printf '%s' "$1" | cksum | cut -d' ' -f1; }
```

O helper existe **por causa do bug**, e o comentário dele explica [confirmado, citação literal]:

> `git rev-parse --show-toplevel` devolve o caminho FÍSICO (`/private/var/...`), enquanto o `posttooluse-doc-read.sh` deriva a raiz recortando a STRING do `file_path` (`/var/...`). No macOS `/var` é symlink de `/private/var` ⇒ hashes diferentes ⇒ o sentinel de leitura nunca resolveria o gate.
>
> REGRA: NUNCA canonicalize (nada de `git rev-parse`, `realpath`, `pwd -P`).

Quem escreve o sentinel é `posttooluse-doc-read.sh`, e ele **recorta a string**, sem tocar em git:

```bash
case "$FP" in
  */.claude/docs/*)    PROJ="${FP%%/.claude/docs/*}" ;;
  */.claude/CLAUDE.md) PROJ="${FP%/.claude/CLAUDE.md}" ;;
  */CLAUDE.md)         PROJ="${FP%/CLAUDE.md}" ;;
  *) exit 0 ;;
esac
PHASH=$(printf '%s' "$PROJ" | cksum | cut -d' ' -f1)
```

Duas normalizações — e só essas duas — são permitidas: **path relativo → absoluto** (`posttooluse-doc-read.sh`, senão o hash diverge) e **remover a barra final** (`lib-project-root.sh:project_root`, porque `/a/b` e `/a/b/` dão `cksum` diferente).

Consumidores da mesma chave hoje [confirmado]: `pretooluse-doc-guard.sh` (`find_doc_up` + `cksum` inline), `pretooluse-plan-gate.sh` e `userpromptsubmit-plan-escape.sh` (ambos via `. lib-project-root.sh`), `posttooluse-doc-read.sh` (recorte de string). **Se você adicionar um quinto hook que fale desses sentinels, ele tem que usar `project_root`/`project_hash` — não reimplemente a subida.**

O teste protege isso com dois casos E2E não-tautológicos (R9/R10 em `test_plan_gate.sh`): o sentinel é escrito rodando o `posttooluse-doc-read.sh` de verdade, e o gate tem que liberar. O comentário do teste registra por que: *"Recalcular a chave à mão aqui foi exatamente o que mascarou o bug de path na 1ª rodada."*

Nomes de sentinel em uso, com o dono de cada um [confirmado]:

- `/tmp/claude-doc-guard-${SESSION}-${PHASH}` — escrito por `posttooluse-doc-read.sh`; lido pelo doc-guard **e** pelo plan-gate (canal compartilhado, de propósito)
- `/tmp/claude-doc-guard-count-${SESSION}-${PHASH}` — contador do doc-guard
- `/tmp/claude-plan-gate-count-${SESSION}-${PHASH}` — contador do plan-gate
- `/tmp/claude-plan-gate-escape-${SESSION}-${PHASH}` — escape verbal, escrito por `userpromptsubmit-plan-escape.sh`

### 1.7 Regex de intenção: fronteira de palavra e o lado seguro

`userpromptsubmit-plan-escape.sh` é o caso de referência de como escrever matcher de linguagem natural neste repo [confirmado, três armadilhas documentadas no cabeçalho + cobertas por R1/R2/R4]:

- **Fronteira de palavra obrigatória** (`B='(^|[^[:alnum:]])'`) antes de todo verbo. Sem ela, `"esta**va** sem documentação"` e `"con**segue** sem doc"` — constatações, não ordens — liberavam o gate.
- **`EXTERNAL_RE`**: `doc do/da/de <coisa>` é doc de terceiro ("ignora a doc do React"), nunca ordem sobre a doc do projeto.
- **Ambiguidade resolve pro lado seguro**: casou escape *e* external ⇒ não libera. Quem quer liberar mesmo assim usa o token inequívoco `--sem-doc`.
- **Toda liberação tem revogação**: `REVOKE_RE` (`--com-doc`, "exige a doc") apaga o sentinel. Válvula obrigatória para o falso-positivo que sobrar.

**Corolário de 2026-07-30, do `askq_lint.py`: régua nova exige teste do lado que ela NÃO pode pegar.** O `CODE_TELLS` procura identificador de código no texto que o usuário lê, e o padrão de caminho nasceu como `/[\w.-]+/[\w.-]+` — que casa **`/07/2026`**. Toda pergunta citando uma data seria devolvida, e um gate que erra no primeiro dia é um gate desligado no segundo (a mesma razão pela qual as isenções do §5.3 existem: *"alarme falso em auditoria treina quem lê a ignorar a saída inteira"*). O conserto é um lookahead exigindo letra no primeiro segmento — `/(?=[\w.-]*[A-Za-z])[\w.-]+/[\w.-]+` — e a prova é o bloco `NÃO barra` de `test_askq_lint.py`, com caso para data, fração, `e/ou` e acento. **A suite de uma régua tem duas metades**, e a metade dos falso-positivos é a que mantém o gate vivo.

**E aconteceu de novo no dia seguinte, no mesmo arquivo — desta vez em produção** (guardrails 1.3.1, commit `73710f8`: *"o gate barrou a PRIMEIRA pergunta real, por causa de 'GitHub'"*). Os tells `camelCase` e `CamelCase` eram regex pura, e maiúscula no meio da palavra é ao mesmo tempo o sinal mais forte de identificador **e** a grafia normal de um monte de nome próprio. `askq_lint.py` hoje trocou os dois por `_MEIO_MAIUSCULO` + a allowlist `NOMES_PROPRIOS` (**52** entradas, comparação em minúsculas), via `camel_suspeitas()`. Verificado nesta rodada: `code_tells("o commit ja esta no GitHub")` → `[]`; `code_tells("mexer no askqLint")` → `["maiuscula_no_meio"]`.

**A lição nova é sobre a allowlist, não sobre a regex: allowlist precisa de teste que prove que é ELA que libera.** Um caso "GitHub passa" sozinho é satisfeito também por uma régua quebrada que não pega nada. `test_askq_lint.py` esvazia `NOMES_PROPRIOS` para `frozenset()`, reafirma que aí *"GitHub"* **barra**, e restaura — é a mesma disciplina da sabotagem anti-tautológica do `test_pre_deploy.sh` (§6), aplicada a um dado em vez de a um padrão.

### 1.8 Prelúdio, portabilidade e exit code

Três idiomas que valem para todo script novo:

- **`set` varia por TIPO de script, de propósito** [confirmado, `grep -n '^set '`]. O build usa `set -euo pipefail` (`scripts/sync-shared.sh`); hook de sync e gate usam `set -uo pipefail`, sem o `-e` (`plugins/bootstrap/hooks/session-sync.sh`, `plugins/bootstrap/hooks/lib/git-sync.sh`, `.claude/hooks/release-gate.sh`); e `plugins/guardrails/hooks/scope-cop.sh` **não declara `set` nenhum** (zero linhas `^set `). Motivo: com `-e`, um hook-trava abortaria no meio de uma checagem e viraria bloqueio acidental — o oposto do fail-open.
- **`stat` portátil mac↔linux é cadeia fixa**, nunca uma forma só: `stat -f %m … || stat -c %Y … || echo 0`. Ver `session-sync.sh` (idade do lock e `LAST_SYNC_MTIME`) e `plugins/graphify-guard/hooks/graphify-detect.sh` (mesma cadeia com `-f "%Sm"`). Uma forma sozinha quebra na outra plataforma.
- **Capture o exit code ANTES do pipe.** `$(cmd | head)` reporta o status do `head`, não do comando:

```bash
LINT_RAW=$(cd "$ESLINT_ROOT" && "$ESLINT_BIN" "$FILE_PATH" --no-warn-ignored 2>&1); RC=$?
LINT_OUTPUT=$(printf '%s\n' "$LINT_RAW" | head -30)
```

`plugins/guardrails/hooks/lint-and-typecheck.sh` repete a forma `RAW=$(… 2>&1); RC=$?` para eslint, tsc, ruff e mypy [confirmado].

### 1.9 Chamada interna de LLM tem que se auto-marcar

Os gates do intent-guard invocam `claude -p` como juiz — e essa sub-invocação dispara o `UserPromptSubmit` de novo, agora com o prompt do JUIZ. Sem marca, o caderno do usuário se auto-polui com prompt interno do plugin (sintoma visto no smoke E2E, comentado no próprio arquivo).

```bash
# plugins/intent-guard/hooks/capture-prompt.sh
[ -n "${INTENT_GUARD_INTERNAL:-}" ] && exit 0
```

Quem chama exporta antes [confirmado, `grep -rn INTENT_GUARD_INTERNAL plugins/`]: `plan-gate.sh`, `task-checkpoint.sh` e `delivery-audit.sh` fazem `export INTENT_GUARD_INTERNAL=1` antes do `claude -p`. Hook novo que chame LLM tem que fazer o mesmo.

### 1.10 Sidecar: quem SABE grava ao lado, em vez de pedir pro modelo ecoar

Padrão nascido em `delivery-audit.sh` (intent-guard 0.5.0, 2026-07-30) e generalizável a todo gate que faz uma pergunta agora e lê a resposta depois.

```bash
# plugins/intent-guard/hooks/delivery-audit.sh — antes de emitir o decision:block
OUTP="$D/audit-${TS}.json"                                  # o auditor vai escrever AQUI
printf '%s' "$LIVE" | "$JQ" -c '[.[] | .id]' > "${OUTP}.escopo" 2>/dev/null
```

O hook cola no prompt do auditor a lista de pedidos vivos **daquele instante**. O JSON de resposta só existe turnos depois, escrito por um subagente — então o hook **não pode** guardar o escopo dentro dele. Guarda ao lado, num arquivo irmão com sufixo, e `ledger.py:audit_check` lê o sidecar em vez de recalcular a lista na hora do consumo.

As três propriedades que fazem o padrão valer, e que valem para qualquer sidecar novo:

- **Grava quem sabe, no instante em que sabe.** A alternativa era instruir o modelo a repetir os ids na resposta. Repetir é exortação; escrever é mecanismo. O comentário no arquivo é a régua: *"depender do modelo ecoar a lista seria trocar mecanismo por exortação"*.
- **O nome do sidecar deriva do artefato**, não de sessão nem de timestamp próprio — `<artefato>.escopo`. Achar o par é `path + sufixo`, sem índice e sem convenção paralela para manter.
- **Ausência é um estado legítimo e tem que ser o CONSERVADOR.** Artefato anterior ao conserto não tem sidecar; `audit_check` cai no comportamento antigo (cobrar tudo) em vez de aprovar de graça. Sidecar que, faltando, afrouxa a trava, é pior que não ter sidecar.

**O que ainda falta:** ninguém apaga sidecar órfão. Se o padrão se repetir, o dono do diretório precisa de uma varredura — hoje `.claude/intent/` acumula `audit-*.json` e `audit-*.json.escopo` para sempre.

---

## 2 · Python

### 2.1 Stdlib puro, sem exceção observada

Não há `requirements.txt`, lockfile nem venv no repo. Verificação mecânica deste run:

```bash
grep -rhoE '^(import|from) +[a-zA-Z_][a-zA-Z0-9_]*' plugins/*/lib/*.py _shared/*.py | awk '{print $2}' | sort -u
# argparse askq_lint branch_state collections contextlib datetime difflib doc_lint fcntl
# glob graph_map hashlib html io journal json ledger math md2deck organism os pathlib
# pattern_check plan_state random re shutil string subprocess sys tempfile time visual_page
```

Tudo é stdlib ou módulo-irmão do próprio plugin (`askq_lint`, `branch_state`, `doc_lint`, `graph_map`, `journal`, `ledger`, `md2deck`, `organism`, `pattern_check`, `plan_state`, `visual_page`). **Por quê:** o plugin é copiado pro cache do Claude Code sem passo de instalação — não existe onde rodar `pip install`. Uma dependência externa quebra silenciosamente na máquina do cliente. `doc_lint.py` carrega isso na docstring: *"Stdlib-puro."*; `plugins/bootstrap/lib/conformance.py` repete a razão no topo (*"Python 3 stdlib apenas — convencao do repo (patterns.md)"*).

⚠️ **O grep acima varre `lib/`, e desde 2026-07-30 existe Python em `hooks/` também.** A varredura completa precisa do segundo glob — `grep -rhoE '^(import|from) +\w+' plugins/*/hooks/*.py` devolve `hashlib json os pathlib re sys` [confirmado], todos stdlib. Um `import requests` num hook `.py` passaria batido pela régua antiga.

### 2.2 Fail-open também vale no Python: "não sei" ≠ "zero"

O padrão mais sutil do repo, e o mais fácil de reintroduzir. Três exemplos literais de `plugins/project-doc/lib/doc_lint.py` [confirmado]:

- `_git_ls_files` devolve **`None`** (≠ `[]`) quando o git não responde. Com `[]`, o lint concluiria "nada existe no repo" e acusaria **todo** token e **todo** ponteiro. `None` desliga os checks 1 e 3.
- `_commit_batch_check` só conta a consulta como válida se o git respondeu **uma linha por token**; se `any_git_ok` for falso, devolve `{t: True for t in toks}` — não acusa ninguém. *"Um lint tem que falhar-ABERTO, nunca acusar por erro de ambiente."*
- `_nlines` devolve `None` em erro de I/O; sem isso, "não sei" viraria `0` e fabricaria *"ponteiro morto: tem 0 linhas"*.

Mesma postura no shell: `doc-detect.sh:doc_staleness` devolve o ternário `fresh|stale|unknown` — e a borda de erro cai em **`unknown` (fail-LOUD)**, nunca em `fresh`. Fingir "fresco" é o único resultado proibido.

### 2.3 CLI de lib: `--json` + exit code

Toda lib com CLI segue a mesma forma [confirmado em `doc_lint.py:main`, `pattern_check.py:main`]: `argparse`, flag `--project-root`, flag `--json`, saída humana legível por default, e **exit 1 quando há FAIL** (`return 1 if out["fails"] else 0`). Quem consome do shell precisa saber que `exit 1` é veredito, não crash — `doc-detect.sh:doc_out_of_pattern` comenta isso explicitamente: *"pattern_check.py exits 1 when out_of_pattern — that is not an error here; bail only if JSON is empty."*

---

## 3 · Vendoring de `_shared/` (o único "build")

Claude Code isola plugins na instalação: só `plugins/<nome>/` vai pro cache, sem variável cross-plugin. Logo, **código compartilhado é COPIADO antes do commit** — não importado em runtime.

- **Fonte-da-verdade:** `_shared/`. As cópias dentro dos plugins são derivadas. Decisão registrada no journal [relatado, e coerente com `scripts/sync-shared.sh`]: *"A fonte-da-verdade da engine de extração mora na pasta neutra `_shared/`."*
- **Mapa explícito, não glob** — `scripts/sync-shared.sh:SPECS`, formato `destino::arquivo` [confirmado, copiado literal]:

```bash
SPECS=(
  "plugins/handoff/lib::collect_engine.py"
  "plugins/project-doc/lib::collect_engine.py"
  "plugins/sovai/skills/sovai/references::r8-tiers.md"
  "plugins/qa-loop/skills/qa-loop/references::r8-tiers.md"
  "plugins/ship/hooks::green-cache.sh"
  "plugins/qa-loop/lib::green-cache.sh"
)
```

- **Comandos:** `bash scripts/sync-shared.sh` copia; `bash scripts/sync-shared.sh --check` não copia e sai 1 listando `DRIFT: <dest> difere de _shared/<arquivo>`.
- **Estado neste run** [confirmado, executado]: `OK: cópias vendored idênticas a _shared/` (exit 0).

**Regra:** fix de código compartilhado **nasce em `_shared/`**, nunca na cópia. Editar a cópia e commitar é pego pelo check A do release-gate — editar `_shared/` e esquecer o sync também.

---

## 4 · Green-cache (`_shared/green-cache.sh`)

Registro de "a suite passou verde neste estado exato da árvore". Feito pra ser **sourced**, não executado.

Semântica declarada como não-negociável no cabeçalho [confirmado]:

- Fail-open na direção segura: qualquer erro → **MISS** → a suite roda.
- **Gate vermelho NUNCA grava.**
- Chave = tree-hash do git **incluindo untracked**, via index temporário. `git stash create` e `HEAD + diff` não servem: ignoram untracked → falso HIT.
- TTL de 24h **por linha** (epoch gravado no registro, não mtime do arquivo — "um mark novo no mesmo arquivo não pode ressuscitar registro vencido"). Prune de arquivos com mais de 7 dias no `green_cache_mark`.

API (assinaturas literais):

```bash
green_tree_hash  <root>                   # imprime o sha; exit 1 em erro
green_cache_check <root> [scope]          # exit 0 = HIT (scope ou 'full')
green_cache_mark  <root> <scope> <writer> # TSV: scope\tepoch\tiso-ts\twriter
# scope: "full" ou "app:<nome>". "full" satisfaz qualquer consulta.
```

O tree-hash é calculado sem tocar index nem working tree: `GIT_INDEX_FILE` aponta pra um `mktemp`, `read-tree HEAD` + `add -A` + `write-tree`.

Consumidores hoje [confirmado, `grep -rln 'green_cache_check\|green_cache_mark\|green-cache.sh' plugins _shared`]:

- `_shared/green-cache.sh` (fonte)
- `plugins/ship/hooks/green-cache.sh` e `plugins/qa-loop/lib/green-cache.sh` (cópias vendoradas)
- `plugins/ship/hooks/pre-deploy-test-check.sh` — consulta e grava, por app (`app:$app`) no Modo 1 e `full` no Modo 2, com writer `ship-hook`
- `plugins/ship/skills/ship/SKILL.md` e `plugins/qa-loop/skills/qa-loop/SKILL.md` — a Fase Gate do qa-loop grava com writer `qa-loop-gate`

**Por que o cache é aceitável e "suite escopada por conserto" não** [relatado, memória de 2026-07-01 — confirmado no SKILL.md do qa-loop, que mantém suite inteira por conserto]: otimização de gate só entra quando é **determinística**. O green-cache é (tree-hash muda ⇒ invalida). Escopo decidido pelo modelo executor não é — foi explicitamente rejeitado.

---

## 5 · Release

### 5.1 As regras

1. **Bump da `version` em `plugins/<nome>/.claude-plugin/plugin.json` em TODA mudança.** É a única chave de propagação: o Claude Code trata manifests com `version` idêntica como idênticos e pula o update, mesmo com commits novos em `main` [relatado — memória `marketplace_release_flow`, checada por 2 fontes oficiais; o comportamento em si não foi reproduzido nesta rodada].
2. **Espelhe a `version` em `.claude-plugin/marketplace.json`.** As duas têm que bater.
3. **`claude plugin validate .` antes de publicar.** É o gate real de instalação.
4. **Rode as suites do plugin tocado** (§6) — o release-gate faz isso por você no commit.
5. **Publicar ≠ instalar.** O cache mora em `~/.claude/plugins/cache/pedro-plugins/<nome>/<versão>/` — uma pasta por versão, todas convivendo [confirmado 2026-07-30: `ls ~/.claude/plugins/cache/pedro-plugins/ | wc -l` → **19** plugins; `visual/` tem **12** diretórios de versão e `project-doc/` **9**; `du -sh ~/.claude/plugins/cache` → **103M**]. Depois de sincronizar o marketplace ainda é preciso `/reload-plugins`; e `/plugin` (update do marketplace) + `/reload-plugins` **não** instalam nem desinstalam nada — só `claude plugin install` / `claude plugin uninstall` mudam **quais** plugins carregam [relatado — comportamento do CLI, não reproduzido nesta rodada].

   ⚠️ **Mas o BUMP de um plugin já habilitado é outro caso, e ele se propaga sozinho** [confirmado 2026-07-30, observado, mecanismo NÃO identificado]. Minutos depois do push de `guardrails` 1.3.0, sem nenhum `claude plugin install` nem `update` rodado na sessão, o diretório `cache/pedro-plugins/guardrails/1.3.0/` já existia com o `askq-humanize.sh` dentro, e `claude plugin details guardrails@pedro-plugins` reportava `guardrails 1.3.0`. O que dispara a busca não foi isolado — candidatos não descartados: o `session-sync.sh` do `bootstrap`, ou o próprio `claude plugin validate` / `details` refrescando o marketplace de passagem. **Não construa procedimento sobre isso ainda**; o que a observação garante é só que "o cliente nunca refresca sem comando explícito" é forte demais como regra. O que segue valendo sem exceção é o **restart**: o harness tira o snapshot dos hooks na subida da sessão, então hook novo não entra na sessão em curso, com cache atualizado ou não.

6. **Plugin novo entra em TRÊS arquivos, não dois** (`ff32947`). Além do `plugin.json` e do
   `marketplace.json` das regras 1-2, ele tem que entrar em
   `plugins/bootstrap/config/manifest.json`, no marketplace `pedro-plugins` — a **receita**
   de instalação, que desde `ff32947` declara o próprio repo e lista os 19 plugins com
   `enabled` explícito. Catálogo diz *o que existe pra instalar*; receita diz *o que a
   máquina instala*. Plugin só no catálogo **nunca chega a máquina nenhuma**, e o modo de
   falha é o pior: os dois arquivos ficam individualmente corretos.
   Quem cobra é `conformance.py:check_catalogo` (§5.3), não o `release-gate.sh` — então o
   commit **passa** com a receita desatualizada, e o desvio só aparece no próximo
   `bootstrap:setup`. Régua de mão: **plugin novo nasce com `enabled: false`** se depender de
   binário externo (`graphify-guard`) ou se for experimental (`intent-guard`); instalar e
   deixar desligado é reversível por um comando, não instalar não é descobrível.

Duas falhas de `validate` que bloqueiam a instalação em silêncio, com o arquivo parecendo íntegro [relatado — memória, marcada STALE pelo coletor; **o estado atual do repo é consistente com o fix**: `.claude-plugin/marketplace.json` tem **19** plugins e os `author` presentes são todos objeto, verificado neste run]:

- `author` **tem que ser objeto**, não string. `"author": "Fulano (...)"` é rejeitado com `expected object, received string`. Use `{ "name": "...", "homepage": "..." }`.
- **`: ` (dois-pontos + espaço) e `<>` no `description:` de um SKILL.md** quebram o parser YAML → frontmatter vazio → skill rejeitada. Fix: aspas simples envolvendo a description inteira.

### 5.2 O gate mecânico de commit

`.claude/hooks/release-gate.sh`, registrado em `.claude/settings.json` como `PreToolUse` com `matcher: "Bash"`, `timeout: 60`, apontando para `$CLAUDE_PROJECT_DIR/.claude/hooks/release-gate.sh` [confirmado — li o settings.json; a ativação está wired]. <!-- lint:ignore CLAUDE_PROJECT_DIR -->

Ele intercepta `git commit`, checa os invariantes que antes só existiam como prosa, e sai `exit 2` com o relatório em stderr. Zero token.

**Dependência invertida:** ao contrário dos hooks de PreToolUse do repo, que assumem `jq`, o release-gate **não usa `jq` uma vez sequer** — faz todo o parse de `plugin.json`/`marketplace.json` com `python3 -c` [confirmado: `grep -c jq .claude/hooks/release-gate.sh` → 0; `grep -c python3` → 4]. Sem `python3` na máquina, ele cai no fail-open de infra e não checa nada.

**Como decide o que olhar:**

```bash
printf '%s' "$CMD" | grep -qE '(^|[;&|]|&&)[[:space:]]*git[[:space:]]+.*commit' || exit 0
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -f "$ROOT/.claude-plugin/marketplace.json" ] || exit 0   # não é este monorepo
FILES=$( { git -C "$ROOT" diff --cached --name-only
           git -C "$ROOT" diff --name-only; } 2>/dev/null | sort -u )
```

Os **sete checks** — as letras são as do próprio arquivo, e a ordem de declaração nele é
`A · B+C · D · E · G · F` (o G nasceu depois do F e foi inserido antes dele; a ordem de
execução não importa porque todos só acumulam em `VIOL`). **Continuam sete, e o arquivo não
mudou desde `f81c4e8`** [confirmado — `git diff 9e03fd9..HEAD -- .claude/hooks/release-gate.sh`
nesta rodada volta vazio; a limpeza de `ff32947` mexeu no que o gate MEDE, não no gate]:

- **A · vendoring** — roda `scripts/sync-shared.sh --check`. Drift ⇒ `❌ VENDORING EM DRIFT`, com a instrução de corrigir **na fonte** `_shared/<arquivo>` e re-rodar o sync.
- **B · espelho `plugin.json` ↔ `marketplace.json`** — para cada plugin tocado, compara `version` do manifesto com a entrada do marketplace. Divergiu ⇒ `❌ ESPELHO QUEBRADO`, com as duas versões impressas.
- **C · bump esquecido** — compara a `version` atual com a de `git show HEAD:<manifesto>`. Iguais ⇒ `❌ BUMP ESQUECIDO — <nome> mudou mas version continua <v>`.
- **D · testes Python** — roda todo `plugins/<nome>/lib/test_*.py` dos plugins tocados com `python3`. Vermelho ⇒ `❌ TESTE VERMELHO`, com as últimas 15 linhas da saída.
- **E · contrato dos hooks** — só quando o commit toca `plugins/*/hooks/`. Roda `python3 scripts/hook_contract.py --baseline .claude/hook-contract.baseline.json --fail-on high` e barra o que **piorou**. Achado que já existia no retrato não trava ninguém. Verificado nos dois sentidos neste run: com um hook de teste usando `/opt/homebrew/bin/jq` ⇒ `R4-binario-fixo`, exit 1; sem ele ⇒ *"Nenhum achado"*, exit 0.
- **F · testes shell** — roda `plugins/<nome>/hooks/test_*.sh` dos plugins tocados. Antes só as suites Python entravam no gate; as shell eram manuais e por isso apodreciam.

  ⚠️ **D e F são o único lugar em que "quantos checks a suíte tem" vira consequência de
  gate.** Os dois globs são por **plugin tocado**, não por repo: um commit que só mexe no
  `bootstrap` roda exatamente `plugins/bootstrap/lib/test_*.py` e
  `plugins/bootstrap/hooks/test_*.sh` e mais nada. Foi assim que `ff32947` — que reescreveu
  `apply.sh`, `stop-prose-ceiling.py`, `conformance.py` e `settings-defaults.json` de uma vez
  — teve as duas suítes do plugin executadas no próprio commit, hoje **52** e **19** checks
  (§6). Plugin sem suíte não é plugin sem teste: é plugin cujos checks D e F estão desligados.
- **G · gen defasado no marker do project-doc** (2026-07-29) — só quando o commit toca
  `plugins/project-doc/`. Lê `CURRENT_GEN` de `pattern_check.py` e varre
  `plugins/project-doc/skills/` procurando `gen=X.Y` **dentro de comentário HTML** — é o que
  vai carimbado na doc gerada. Divergiu ⇒ `❌ GEN DEFASADO NO MARKER`, com `arquivo:linha`.
  Existe porque a HARD RULE do bump de gen é um checklist de 5 passos feito à mão e **já
  falhou**: depois do bump 3.7→3.8 o `nested-pointers.md` seguiu carimbando `gen=3.7`. A
  skill oferecia o grep como "régua mecânica" opcional; o check tornou obrigatório.
  **Menção em prosa a um gen antigo NÃO é violação** (`"doc \`gen=3.6\` fica stale"`) — há 4
  dessas no repo hoje, e barrá-las ensinaria a ignorar o gate. Fail-open se `CURRENT_GEN`
  não for resolvível. Verificado nos dois sentidos em 2026-07-29: estado limpo ⇒ silêncio;
  marker sabotado pra `gen=3.7` ⇒ exit 2 com as duas linhas do `nested-pointers.md`.

Bloco de saída literal quando algo viola:

```
🚧 release-gate (pedro-plugins) BLOQUEOU o commit:
<violações>

Conserte e commite de novo. (Gate mecânico: .claude/hooks/release-gate.sh)
```

---

### 5.3 Contrato dos hooks — as 5 propriedades

Três gates disputam o `ExitPlanMode` e cada um resolvia por conta própria como
não travar quem está trabalhando, como ser desligado e como falar. **A divergência não foi
descuido de autor: não havia onde o contrato estivesse escrito.** Esta seção é o
lugar; `scripts/hook_contract.py` é quem mede, e o gate E é quem cobra.

| # | Propriedade | Regra |
|---|---|---|
| 1 | **canal** | Bloquear é `exit 2` **ou** `permissionDecision:"deny"` **ou** `decision:"block"`. Informar é `additionalContext` (SessionStart/UserPromptSubmit **e também `PreToolUse`** — ver §1.2 e `ship/hooks/pre-deploy-test-check.sh:allow_with_notes`, que emite `hookEventName:"PreToolUse"` com `additionalContext`) ou `systemMessage` (Stop). ⚠️ **`additionalContext` chega ao MODELO, não ao usuário** — aviso que o usuário precisa ver vai junto num `systemMessage`, os dois no mesmo JSON. A regra é **condicional, e a exceção está viva**: quando o destinatário do aviso é o próprio modelo, `additionalContext` sozinho é o certo — `graphify-guard/hooks/pretooluse-graphify-guard.sh` (ramo `else`) manda consultar o grafo, e quem roda `graphify query` é o modelo; um `systemMessage` ali seria um pop-up por sessão em todo projeto com grafo, sem nada pro usuário decidir. O contraste é o `guardrails/hooks/scope-cop.sh` no modo `warn`, que avisa sobre uma **edição fora de escopo** — essa o usuário precisa ver, e leva os dois canais. Quem escolher um canal só **registra o porquê no ramo**, senão a próxima leitura trata como esquecimento. Os três canais de bloqueio coexistem hoje e **não** foram normalizados — quem informa não precisa de nada do resto desta tabela. |
| 2 | **cap anti-loop** | Todo hook que bloqueia tem teto de devoluções, e a chave do teto é **escopada por sessão**. Depois do teto ele degrada pra aviso — nunca prende. |
| 3 | **kill-switch** | Toda trava se desliga por env var no formato `<NOME>_GATE=0`, sem editar o script. |
| 4 | **binário** | Ferramenta externa se resolve por `command -v`. **Nunca** caminho absoluto (`/opt/homebrew/bin/jq`): ele some fora do Mac com Homebrew e o hook cai no fail-open **em silêncio** — a trava fica destravada sem ninguém ver. |
| 5 | **fail-open** | Ferramenta ausente (`jq`, `python3`, `node`) ⇒ `exit 0` calado. Fail-open sempre na direção segura, e a direção muda por gate (ver §1.1). |

**Os kill-switches de hoje**, um por gate que bloqueia:

```
VISUAL_GATE     GRAPHIFY_GATE   HANDOFF_GATE   DOC_GUARD_GATE
ORGANISM_GATE   PLAN_DOC_GATE   SHIP_GATE      LINT_GATE
ASKQ_GATE       (o vigia da pergunta com opções, guardrails 1.3.0)
SCOPE_COP_GATE  (a trava de escopo de UI, guardrails 1.5.0 — convive com o
                arquivo de modo abaixo: o arquivo é a decisão durável, a env
                var é o interruptor do momento ruim)
BRANCHES_GATE   (informativo — os dois hooks do /branches)
PROSE_CEILING   ⚠️ FORA da convenção `<NOME>_GATE` — é `PROSE_CEILING=0`, e desliga
                o hook inteiro (bootstrap 1.3.x, `stop-prose-ceiling.py`)
PROSE_CEILING_MAX
                ⚠️ INVERTIDA como a `GRAPHIFY_DENY` — não desliga, LIGA. Desde
                `ff32947` **não há default**: `TETO = int(_TETO_ENV) if
                _TETO_ENV.isdigit() else None`, e sem a variável o hook não
                reprova por tamanho nenhuma vez. Retórica e menu de opções, que
                não dependem dela, seguem ligados sempre
GRAPHIFY_DENY   ⚠️ INVERTIDO — não desliga, LIGA. Default `0`. O guard do graphify
                passou a AVISAR (`additionalContext`) em 2026-07-30, e
                `GRAPHIFY_DENY=1` devolve o `permissionDecision:"deny"` de volta.
                `GRAPHIFY_GATE=0` continua desligando o hook inteiro, antes de
                tudo (graphify-guard 1.1.0)

Flag em arquivo ALÉM da env var — e com um degrau no meio:
`${CLAUDE_CONFIG_DIR:-$HOME/.claude}/guardrails/scope-cop.mode` aceita `deny`
(default) | `warn` | `off` (guardrails 1.4.0). Ver §1.4 para o porquê do estado
intermediário. O `SCOPE_COP_GATE=0` acima sai antes de tudo, sem depender do
arquivo — que mora fora do repo e não serve como interruptor de momento ruim.

Hook que só INFORMA não é gate, mas segue a mesma convenção de desligar:
`PLAN_STATUS=0` (o resumo de fim de turno), `PLAN_NUDGE=0` (só a cobrança do
tique, dentro dele), `BRANCHES_GATE=0` (os dois avisos do `/branches`; o
limiar de "branch parada" é `BRANCHES_DIAS`) e `DOC_AUTORAL_GATE=0` (a cobrança
de documento autoral faltante no `sessionstart-doc.sh`).
```
(o `intent-guard` tem os dele desde antes: `~/.claude/intent-guard/mode` e `<projeto>/.claude/intent/off`)

**Convenção nova (`ff32947`): quando a trava é PREFERÊNCIA de quem escreveu, a env var LIGA
em vez de desligar.** O repo passou a ter duas dessas — `GRAPHIFY_DENY=1` e
`PROSE_CEILING_MAX=<n>` —, e as duas nasceram do mesmo raciocínio: o marketplace vai pra
máquina de outra pessoa, e um default que barra por gosto do autor é imposição. A régua pra
escolher a direção da variável:

- **Defeito** (o hook mede algo objetivamente errado — teste vermelho, retórica de ligação,
  edição fora do escopo aprovado) ⇒ **liga por default**, desliga por `<NOME>_GATE=0`.
- **Preferência** (o hook mede algo que o dono da máquina pode legitimamente querer
  diferente — quantas linhas de prosa cabem numa resposta) ⇒ **nasce desligado**, liga por
  variável explícita.

O teste que separa os dois: *se a pessoa que recebe o plugin discordar do critério, ela está
errada?* Se a resposta for "não necessariamente", é preferência. E preferência com default
ligado tem um custo específico e conhecido — a pessoa desliga o hook inteiro na segunda vez
que ele erra, e aí ele também não pega o que era defeito de verdade.

### As isenções — e por que cada uma existe

Isenção não escrita vira alarme falso, e **alarme falso em auditoria treina quem
lê a ignorar a saída inteira**. As quatro que valem hoje:

- **Hook de `Stop` não precisa de cap próprio.** O harness tem o nativo
  (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`); ele não consegue prender pra sempre.
  Aplicado ao `handoff-completeness-gate.sh`.
- **Gate de segurança não leva cap.** No `ship`, um contador que liberasse o
  deploy na terceira tentativa com teste vermelho seria **pior** que o problema.
  Ele leva `SHIP_GATE=0` — ato humano explícito — e nunca teto. Decisão de projeto,
  2026-07-27. É por isso que `ship/pre-deploy-test-check.sh` segue no retrato com
  `R1-cap-ausente` e **não** deve ser "consertado".
- **Uso local já degradado dispensa guarda no topo.** `bootstrap/session-sync.sh`
  e `project-doc/sessionstart-doc.sh` chamam a ferramenta dentro de um `if` cujo
  ramo falso é o comportamento correto; um `exit 0` no topo mataria trabalho que
  não depende dela. Ficam no retrato com `R5` de propósito.
- **`command -v X` em qualquer lugar conta como guarda.** Exigir a forma exata
  `|| exit 0` gerava alarme falso nas outras formas legítimas (`if command -v`,
  variável + `[ -z ]`). Teto assumido e aceito.

### O ponto cego: `hook_contract.py` só entende SHELL

⚠️ **O checker não mede hook `.py`, e o silêncio dele parece aprovação** [confirmado
nesta rodada, com a medida crua na mão]. `BLOCK_PATTERNS` procura `^\s*exit\s+2`,
`KILL_PATTERNS` procura `${VAR:-1}" = "0`, `FAILOPEN_GUARD` procura `command -v` — todos
idiomas de shell. `plugins/bootstrap/hooks/stop-prose-ceiling.py` bloqueia com
`sys.exit(2)` (via `sair(msg, 2)`), desliga com `os.environ.get("PROSE_CEILING") == "0"` e
tem cap próprio (`MAX_BLOQUEIOS = 2`), e mesmo assim o `--json` do checker devolve pra ele:

```
"blocking": {}, "killswitch": [], "cap": {"counter": [], "sentinel": [], "session_scoped": false}
```

Ou seja: **zero achado, e zero achado por não ter olhado**. O `resolve_script` até resolve o
caminho (o regex de `${CLAUDE_PLUGIN_ROOT}` sobrevive ao prefixo `python3 "`), então o hook
entra na contagem — hoje *"33 registros, 32 scripts distintos"* — e some na medição. Regra:
**hook novo em Python se audita à mão** até o checker ganhar os idiomas equivalentes; e se
você somar as propriedades por cima da saída do checker, lembre que o denominador inclui um
script que ele não sabe ler.

### O outro medidor: `conformance.py`, e por que ele parte o matcher no `|`

`plugins/bootstrap/lib/conformance.py` mede a **máquina viva** (settings.json, cache,
skills, gates em disco), não o repo — relatório puro, nunca escreve, `exit 1` quando há
desvio. **São 10 checagens em `CHECAGENS`** [confirmado — lista lida nesta rodada]; duas
convenções novas entraram com `ff32947` e as duas valem além do caso:

- **"Não instalado" e "instalado e desligado" são estados DIFERENTES, e o conserto de um não
  serve pro outro.** `check_plugins` lia só `enabledPlugins`, onde os dois casos aparecem
  igual (a chave não está lá), e mandava `claude plugin enable` — comando que **falha** num
  plugin que nunca foi instalado. Hoje `_refs_instaladas()` lê
  `<config>/plugins/installed_plugins.json` (formato conferido na máquina:
  `{"plugins": {"<nome>@<mkt>": [ … ]}}`, chave com lista não-vazia = instalado) e o desvio
  passa a nomear qual dos dois é, com o conserto certo em cada um. **Fonte ausente ⇒ `None`
  ⇒ comportamento antigo** — a ferramenta é relatório, então falta de dado degrada pro que
  já existia, não pra acusação nova. Régua: *conserto que não roda é pior que desvio não
  reportado, porque queima a credibilidade do relatório inteiro.*
- **Dois artefatos que precisam concordar precisam de ALGUÉM que compare — e não era
  ninguém.** `check_catalogo` cruza o `marketplace.json` publicado com a lista
  `marketplaces → pedro-plugins → plugins` do `config/manifest.json`: plugin que entra no
  catálogo e não entra na receita **nunca chega a máquina nenhuma**, e falha em silêncio
  porque os dois arquivos estão individualmente corretos. É a mesma família do par
  escritor↔leitor do §1.4 e do `project_staleness` × `scope_staleness` do §7. Ele resolve
  onde o catálogo mora nesta máquina (`_catalogo_publicado`: registro vivo em
  `known_marketplaces.json` → clone em `plugins/marketplaces/` → fallback repo-relativo) e
  **sai calado** quando não acha — máquina sem o marketplace instalado não é desvio.

O achado de desenho mais antigo está no `check_hooks_duplicados`: matcher de
`PreToolUse` é uma **alternância**, então comparar a string inteira não acha colisão
parcial: `graphify-guard` declara `Grep|Glob|Bash` e `project-doc` declara
`Grep|Glob|Bash|Agent` — strings diferentes, **zero** colisão pela comparação ingênua, três
ferramentas em comum quando se parte no `|`. Ele também só olha a **versão mais alta** de
cada plugin no cache (`_versao`), porque o cache guarda toda versão já instalada e as
antigas não rodam — contar o cache inteiro contaria hooks mortos.

**Convenção nova (2026-07-30, bootstrap 1.5.0): o check conta quem BLOQUEIA, e quem
bloqueia se DECLARA.** Registrar `PreToolUse` só pra avisar não custa round-trip; dois
denies na mesma ferramenta custam dois — então contar por *registro* acusa colisão que não
existe. Mas inferir "bloqueia" do texto do script também erra, e errou: quando o
`pretooluse-graphify-guard.sh` virou aviso, o caminho de `deny` **continuou no arquivo**,
atrás de um `if [ "${GRAPHIFY_DENY:-0}" = "1" ]` desligado, e o grep por
`permissionDecision` + `"deny"` seguia acusando. O conserto é o hook declarar o próprio
default numa linha que o verificador lê:

```bash
# conformance: default-warn — o caminho de deny existe, mas só com GRAPHIFY_DENY=1
```

`conformance.py:bloqueia()` procura essa string **primeiro**; só na ausência dela cai no
grep (`permissionDecision` + `"deny"`, ou `exit 2`), e **erro de leitura ⇒ assume que
bloqueia** — o fail-open do §2.2 aplicado aqui ("não sei" nunca vira "não bloqueia").
Portador único hoje [confirmado — `grep -rn 'conformance: default-warn' plugins/` fora de
teste devolve o `pretooluse-graphify-guard.sh` e as duas menções dentro do próprio
`conformance.py`]. **Regra generalizável: quando o comportamento depende de um flag, grep no
código-fonte mede o que está escrito, não o que roda — faça o programa declarar.**

Por que o graphify-guard cedeu a vez [confirmado — motivo literal no cabeçalho do bloco]: o
`project-doc` já nega a primeira busca da sessão, com matcher **mais largo**
(`Grep|Glob|Bash|Agent` contra `Grep|Glob|Bash`) e mensagem quase idêntica. Eram dois denies
e dois round-trips antes de qualquer trabalho começar, duas vezes na mesma sessão. O
enquadramento continua chegando inteiro pelo `additionalContext`; o que sumiu foi o segundo
bloqueio. **Um gate por ferramenta.**

Efeito medido nesta rodada, na máquina viva (`python3 plugins/bootstrap/lib/conformance.py
--json`): **5** ferramentas bloqueadas por mais de um plugin habilitado — `Agent`
(guardrails, project-doc), `Bash` (project-doc, ship), `Edit` (guardrails, project-doc),
`ExitPlanMode` (intent-guard, project-doc, visual) e `Write` (guardrails, project-doc).
`Glob` e `Grep` saíram da lista quando o graphify-guard deixou de negar.

⚠️ **E o desvio deixou de ser ordem de conserto.** Colisão só é defeito quando os gates têm
o **mesmo propósito** — aí um vira aviso. Propósitos distintos no mesmo evento são
**camadas, não duplicatas**: os cinco acima são escopo × doc × teste-de-deploy × auditoria ×
render, e cada um pega um caso que os outros não pegam. O texto do `conserto` hoje diz isso
e manda julgar caso a caso, *"não cortar no automático"*.

### Dependência externa: declara no manifest, cobra só de quem usa

**Convenção nova (2026-07-30, bootstrap 1.7.0).** Plugin deste repo pode depender de binário
que o marketplace **não** instala. Antes isso não morava em lugar nenhum: o `graphify-guard`
procura `graphify-out/graph.json` pra redirecionar busca cega, e sem o comando `graphify` na
máquina ninguém cria esse diretório — o guarda instala, não reclama e não protege. É a
mesma classe do gate meio-ligado, com a peça faltando **fora** do repo.

A convenção tem duas metades e as duas importam:

1. **A declaração é dado, não código.** `config/manifest.json` ganhou a chave de topo
   `ferramentas_externas` (`_nota` + `itens`), e cada item traz `comando`, `pacote`,
   `instalar`, `alternativa`, `licenca`, `requerido_por` e `porque`. Acrescentar uma
   dependência nova é acrescentar um objeto — nenhuma linha de Python muda.
2. **A cobrança é condicional ao plugin estar LIGADO.**
   `conformance.py:check_ferramentas_externas` cruza `requerido_por` com os `enabledPlugins`
   verdadeiros de `settings.json` e **só então** chama `shutil.which(comando)`; plugin
   desligado sai antes do `which`. Sem esse filtro, quem não usa o recurso levaria um desvio
   permanente e aprenderia a ignorar o relatório inteiro — o custo real de um verificador é
   a confiança nele, não o tempo de execução.

O desvio sai na área `dependencia`, com `which <cmd> -> nada` + o `porque` como evidência e o
`instalar` (mais a alternativa) como conserto. **O verificador continua sem instalar nada** —
a `skills/setup/SKILL.md` recebeu um passo 2c dizendo em letra: *"Não instale por conta
própria. Ofereça o comando ao usuário e explique o que ele destrava"*, e nomeia a saída
oposta como igualmente válida: desligar o plugin em vez de instalar o binário.

O caso está fixado em `test_conformance.py:teste_dependencia_externa_de_plugin_ligado`, que
usa um comando propositalmente inexistente e cobra os dois lados da regra — desligado não
gera área `dependencia`; ligado gera, e o `conserto` carrega o comando de instalação
[confirmado — suíte executada nesta rodada, `52 ok · 0 FAIL`].

### Quando o checker acusar

Ele é **grep sofisticado, não verdade** — a mesma disciplina do knowledge graph.
Cada achado traz arquivo, linha e o trecho: **confira no código antes de
consertar.** Na varredura que criou esta seção, 5 das 12 acusações caíram na
conferência, e uma delas era o checker *inventando* um teto que não existia — o
erro caro, porque esconderia um gate que trava de verdade. Os 5 casos viraram
teste em `scripts/test_hook_contract.py` (28 checks).

Aceitou um achado conscientemente? Recongele o retrato e escreva o porquê aqui:

```bash
python3 scripts/hook_contract.py --json > .claude/hook-contract.baseline.json
```

---

## 6 · Testing

Não há runner nem CI: cada suite é um arquivo executável, stdlib/bash puro, que sai 0 quando verde.

**Suites Python** — `ls plugins/*/lib/test_*.py scripts/test_*.py` (**13 arquivos**; os 11 antigos verdes na varredura de 2026-07-29, os dois novos verdes em 2026-07-30):

- `plugins/bootstrap/lib/test_conformance.py` — **52 checks em 25 funções `teste_*`** (novo em 2026-07-30; 8 → 36 no `32cfe28`, 36 → 39 no `575c33e` com `check_ferramentas_externas`, 39 → 52 no `ff32947` com `check_catalogo` e a distinção ausente × desligado) `[confirmado — executada nesta rodada: 52 ok · 0 FAIL]`
- `plugins/branches/lib/test_branch_state.py`
- `plugins/guardrails/lib/test_askq_lint.py` — **47 checks** (novo em 2026-07-30; 40 → 47 no fix do `NOMES_PROPRIOS`, guardrails 1.3.1)
- `plugins/intent-guard/lib/test_ledger.py` — **59 asserts** (unidade diferente do resto desta lista de propósito: a suíte não imprime contagem, só `test_ledger: OK`; o número saiu de contar os nós `ast.Assert` do arquivo). **53 → 59** em `a134e9c`: os 6 novos cobrem o sidecar de escopo (com sidecar o pedido que chegou depois não reprova; sem sidecar o mesmo arquivo volta a reprovar) e o frescor seletivo do veredito (mexer em arquivo que a evidência **não** cita não vence o veredito; mexer no citado vence). `[confirmado — verde nesta rodada]`
- `plugins/project-doc/lib/test_doc_lint.py` — 35 checks
- `plugins/project-doc/lib/test_graph_map.py` — 23 checks
- `plugins/project-doc/lib/test_journal.py` — 123 checks
- `plugins/project-doc/lib/test_organism.py`
- `plugins/project-doc/lib/test_pattern_check.py` — 41 checks
- `plugins/slides/lib/test_md2deck.py` — **50 checks** (novo em 2026-07-29)
- `plugins/visual/lib/test_plan_state.py`
- `plugins/visual/lib/test_visual_page.py` — **60 checks** (novo em 2026-07-29)
- `scripts/test_hook_contract.py` — **fora de `plugins/`, logo fora do check D do gate**

✅ **O `bootstrap` era o único plugin com `lib/` e ZERO suite — CONSERTADO em 2026-07-30**
(1.4.0/1.5.0). A consequência era mecânica, não estética: os checks D e F do release-gate
iteram `plugins/<nome>/lib/test_*.py` e `plugins/<nome>/hooks/test_*.sh`, então commit que
tocasse **só** o bootstrap passava nos dois sem rodar teste algum — inclusive commit no
`stop-prose-ceiling.py`, que **bloqueia**. Hoje as duas famílias existem e as duas são
verdes [confirmado nesta rodada, as **duas** executadas]: `lib/test_conformance.py` →
`52 ok · 0 FAIL`; `hooks/test_bootstrap_hooks.sh` → `19 ok · 0 FAIL`. Régua para o próximo plugin: **plugin
sem suite não é "plugin sem teste", é plugin cujo gate de commit está desligado.**

**Suites shell** — `ls plugins/*/hooks/test_*.sh` (**15 arquivos**, contados nesta rodada):

- `plugins/bootstrap/hooks/test_bootstrap_hooks.sh` — nasceu com 9 checks em 2026-07-30 e está em **19 checks** desde `ff32947`, que acrescentou o opt-in da desinstalação e o do teto de prosa `[confirmado — executada nesta rodada: 19 ok · 0 FAIL]`
- `plugins/branches/hooks/test_branch_hooks.sh` — 22 checks
- `plugins/graphify-guard/hooks/test_graphify_guard.sh` — 37 checks
- `plugins/guardrails/hooks/test_askq_gate.sh` — **18 checks** (novo em 2026-07-30)
- `plugins/guardrails/hooks/test_scope_cop.sh` — 15 checks
- `plugins/guardrails/hooks/test_setup_skill.sh` — 29 checks (⚠️ leva mais de 2 min — a única do repo que não roda em segundos)
- `plugins/ship/hooks/test_pre_deploy.sh` — **87 checks** (novo em 2026-07-29)
- `plugins/intent-guard/hooks/test_delivery_audit.sh`
- `plugins/intent-guard/hooks/test_hooks_capture.sh`
- `plugins/intent-guard/hooks/test_plan_gate.sh`
- `plugins/intent-guard/hooks/test_task_checkpoint.sh` — 🔴 **VERMELHA desde `a134e9c`**: sai 1 na linha 72, depois de imprimir `drift block 1 OK`. O teto por sessão (§1.3) silencia o 3º bloqueio que a própria suíte exige. `[confirmado — `bash -x` nesta rodada mostra `OUT2=` vazio]`
- `plugins/project-doc/hooks/test_has_frontend.sh`
- `plugins/project-doc/hooks/test_plan_gate.sh` — 49 checks
- `plugins/project-doc/hooks/test_sessionstart_doc.sh` — 8 casos
- `plugins/visual/hooks/test_plan_hooks.sh` — 33 checks

Rodar tudo:

```bash
for t in plugins/*/lib/test_*.py scripts/test_*.py; do python3 "$t" || echo "RED: $t"; done
for t in plugins/*/hooks/test_*.sh;               do bash    "$t" || echo "RED: $t"; done
```

**Como testar um hook de DETECÇÃO sem rodar suíte de verdade** [confirmado — `plugins/ship/hooks/test_pre_deploy.sh`]. O problema: no gate do ship, "não detectou deploy" e "detectou e a suíte passou" são **os dois `exit 0`** — o exit code sozinho não distingue. A solução é o fixture `PROBE`: um projeto git cujo `Makefile` tem `test:` → `@exit 1`. Aí o exit code responde uma pergunta só:

```
detectou deploy  ->  roda a suíte  ->  vermelho  ->  exit 2
não detectou     ->  exit 0
```

Com isso cada forma de comando vira um `detecta '<cmd>'` / `ignora '<cmd>'` de uma linha, e a suíte cobre **os dois lados** de cada regex. É a resposta ao vício que produziu as regressões deste hook: travar só o lado que o conserto GANHOU, nunca o lado que ele pode perder. `GREEN_SUITE_DIR` isolado no `mktemp` é obrigatório — sem isso um registro verde do projeto real dá HIT e libera um deploy que a suíte espera ver bloqueado.

**Mutação como régua da suíte (não é o mesmo que anti-tautologia).** A prova anti-tautologia do `test_pre_deploy.sh` sabota **uma** detecção (`sed 's/)pm2/)pm2NUNCACASA/'`) e exige a suíte vermelha. Isso prova que ela afirma *algo* — não que ela afirma o **suficiente**. Sabotando alvo por alvo é que se descobre o buraco: neutralizar o bloqueio do **Modo 1** (`if ! ( cd $PROJ && bash scripts/run_app_tests.sh … )` → `if false`) mantinha a suíte **100% verde**, porque nenhum caso exercitava "app com teste vermelho → exit 2" no modo que roda de verdade no monorepo. Cobertura de 31 checks verdes não é cobertura do caminho que importa.

**Suite que testa o gate do próprio companheiro.** `plugins/slides/lib/test_md2deck.py`
roda o `scripts/check_fidelity.py` **de verdade** sobre um deck compilado, e depois injeta
prosa inventada no mesmo deck pra provar que o checker reprova. Sem o segundo caso, o
primeiro passaria com um checker cego e ninguém saberia. Padrão a copiar quando uma peça
existe pra fazer outra cumprir contrato.

**Teste de presença ≠ teste de efeito** [confirmado — defeito real de 2026-07-29]. A
primeira versão do `md2deck.py` gerava um deck que passava nos 47 checks e no
`check_fidelity.py`, e abria **branco com fonte serif**: o `template.html` documenta os
placeholders dentro de comentários (`/* __THEME_CSS__ : … */`), o replace global injetou o
`:root{…}` **dentro** do comentário, e o primeiro `*/` do próprio tema o fechou no meio. O
teste afirmava que a string `--bg-body:#0f172a` existia no arquivo — e existia, morta
dentro de um comentário. O check certo tira os comentários do `<style>` **antes** de
afirmar que a paleta está lá, e o `md2deck.py` passou a **recusar** (`exit 2`) o deck cujo
`:root` não sobrevive fora de comentário. Só o print no browser pegou.

**Smoke manual fora das suites** [confirmado]: o scrubber de segredos do journal tem modo próprio de CLI — `python3 plugins/project-doc/lib/journal.py scrub-test < arquivo` lê stdin e imprime o texto scrubado. Ver `journal.py:main` (o `scrub-test` está na lista de `choices` do argumento `mode`) e a linha de uso na docstring do topo.

**Convenções da suite shell** (modelo: `plugins/project-doc/hooks/test_plan_gate.sh`) [confirmado]:

- **Isolamento total em `/tmp`**: fixtures em `mktemp -d`, `SESSION="test-$$"`, `trap` que apaga o tmpdir **e** os sentinels `/tmp/claude-*-${SESSION}-*` no EXIT. Nenhum projeto real é tocado.
- **O teste usa o MESMO helper que o código** (`. lib-project-root.sh`; `phash()` chama `project_hash`). Recalcular a chave à mão foi o que mascarou o bug de path.
- **Bloco de regressões nomeadas** (`R1`…`R10`), cada um citando a data e o sintoma que ele impede de voltar.
- **Saída vazia = allow**: `decision()` trata stdin vazio como `allow`, porque `jq` sobre entrada vazia não emite nem o default.
- Contador `PASS`/`FAIL`, resumo `── N passou · M falhou ──`, e `[ "$FAIL" -eq 0 ]` como última linha (vira o exit code).
- **Nada de `python3 … | grep -q` sob `pipefail` — nem `printf … | grep -q`.** O `grep -q`
  sai no **primeiro match** e fecha o pipe; quem está upstream leva SIGPIPE e morre com
  `BrokenPipeError` no flush (python sai **120**; o `printf` do shell dá `write error:
  Broken pipe`). O `pipefail` propaga isso e o `-e` derruba a suite. É **corrida** — o
  upstream normalmente termina de escrever antes —, então falha às vezes. Medido em
  `test_sessionstart_doc.sh` (2026-07-29): **1 falha em 8**, com o agravante de o check F do
  release-gate rodar essa suite, ou seja **o gate de commit ficava vermelho por sorteio, num
  commit sem relação nenhuma com o defeito**. Gate intermitente é pior que gate nenhum:
  ensina a reexecutar até passar. ⚠️ **Materializar a saída numa variável e continuar
  pipando NÃO resolve** — a 1ª tentativa de conserto fez isso e só mudou quem morre (o
  `printf` em vez do python), piorando pra **20 em 40**. A correção é **não ter pipe**:
  `grep -q -- "$pat" <<< "$texto"` (here-string alimenta por fd, sem processo upstream).
  Depois: **0 em 60**. [confirmado — as três taxas medidas na mesma máquina]
  ⚠️ **Reincidiu em 2026-07-29, na suíte seguinte:** `plugins/visual/hooks/test_plan_hooks.sh`
  tinha **18** usos de `printf … | grep -q` sob `set -uo pipefail` e falhava **4 em 8** —
  pior taxa que a original, e com o agravante de as runs falharem em **checks diferentes do
  mesmo bloco** (o que faz parecer defeito de produto, não de suíte). Convertidos os 18 pra
  here-string: **0 em 36**. Dois `grep -qv` do arquivo viraram `! grep -q` no mesmo passo.
  **Risco latente medido, não consertado:** `plugins/branches/hooks/test_branch_hooks.sh`
  (9 usos, `pipefail`) e `plugins/intent-guard/hooks/test_task_checkpoint.sh` (4 usos,
  `set -euo pipefail` — a combinação pior) seguem com o padrão e deram **0 em 10** cada.
  10 rodadas não absolvem ninguém: se uma delas começar a piscar, o conserto é o mesmo.
  **Verificação mecânica antes de commitar suíte shell nova:**
  ```bash
  grep -c "printf.*| *grep -q\|echo.*| *grep -q" plugins/*/hooks/test_*.sh   # tem que ser 0
  ```
- **`grep -qv PADRÃO` NÃO é "não contém".** Ele sai 1 em entrada vazia (não há linha alguma), então o teste passa a afirmar o contrário do que quer quando o hook cala. O idioma correto é `grep -q PADRÃO && echo 0 || echo 1`. [confirmado — falso-negativo real em `test_branch_hooks.sh`, 2026-07-28]
- **Hook que depende de OUTRO hook ter rodado é frágil.** O `stop-plan-status.sh` só confirmava conclusão se o `sessionstart-plan.sh` tivesse deixado o marco da sessão — e quando o plugin é instalado ou atualizado NO MEIO da sessão, o `SessionStart` já passou e o marco nunca existe. Resultado: calado pra sempre naquela sessão, sem sinal nenhum de que estava quebrado. **Se o pré-requisito é um arquivo barato, o hook cria ele mesmo.** [confirmado — o defeito aconteceu de verdade em 2026-07-28, no turno em que o próprio hook nasceu]
- **No `jq`, `//` trata `false` como vazio.** `.tool_response.success // "true"` devolve `"true"` quando o campo é `false` — o hook do `/branches` perguntava depois de um `git push` que tinha FALHADO. Pra campo booleano, comparação explícita: `if .x == false then … else … end`.
- **Hook informativo: teste o SILÊNCIO, não só o aviso.** `plugins/visual/hooks/test_plan_hooks.sh` gasta 6 dos seus 18 checks fixando os caminhos em que o hook **não** pode falar (sem marco de sessão, poucas edições, já marcou, `stop_hook_active`, kill-switch, transcript ausente). O raciocínio está no cabeçalho do arquivo: *"Hook que cobra errado é hook que o usuário desliga, e aí ele não cobra nunca."* Falso-positivo em hook informativo custa mais que falso-negativo.

**As duas famílias entram no gate de commit** [confirmado — os dois loops em
`.claude/hooks/release-gate.sh`]: o check D itera `plugins/<nome>/lib/test_*.py` e o check F
itera `plugins/<nome>/hooks/test_*.sh`, ambos **só dos plugins tocados**. A exceção é
`scripts/test_hook_contract.py`: fora de `plugins/`, nenhum dos dois globs o alcança —
roda na mão (o que ele protege é coberto de outro jeito, pelo check E).

---

## 7 · Gotchas

Cada item aponta **arquivo:símbolo**, nunca número de linha.

### Hooks & plugins

- ⚠️ **Hook de plugin vai em `hooks/hooks.json` (subpasta), NUNCA na raiz do plugin.** Na raiz é ignorado em silêncio e `claude plugin validate` passa mesmo assim. Diagnóstico é `claude plugin details <nome>@pedro-plugins` → linha `Hooks (N)`. Estado atual [confirmado nesta rodada, `find plugins -name hooks.json`]: os **10** arquivos existentes estão todos em `plugins/<nome>/hooks/hooks.json` — bootstrap, branches, context-guard, graphify-guard, guardrails, handoff, intent-guard, project-doc, ship, visual. Zero na raiz.
- ⚠️ **Estado mutável dentro do plugin evapora.** `${CLAUDE_PLUGIN_ROOT}` é cache reescrito a cada bump — ver `_shared/green-cache.sh:GREEN_SUITE_DIR` e `plugins/guardrails/hooks/scope-cop.sh:HOOK_DIR` para o padrão correto.
- ⚠️ **Arquivo de estado global em `/tmp` vaza entre sessões concorrentes.** Sempre `-${SESSION_ID}` no nome. Ver `plugins/context-guard/hooks/context-guard-writer.sh` (o fix) e `context-guard-reset.sh` (limpar só a própria sessão, jamais glob).
- ⚠️ **Canonicalizar path quebra sentinel no macOS.** `git rev-parse --show-toplevel` → `/private/var/...`; recorte de string → `/var/...`; `cksum` diferente; o sentinel nunca casa. Use `plugins/project-doc/hooks/lib-project-root.sh:project_root` e `:project_hash`. Regressão coberta por R8/R9/R10 de `test_plan_gate.sh`.
- ⚠️ **Hook que chama `claude -p` sem se auto-marcar polui o próprio caderno.** A sub-invocação re-dispara o `UserPromptSubmit`. Ver §1.9 e `plugins/intent-guard/hooks/capture-prompt.sh` (o guard) + `plan-gate.sh` / `task-checkpoint.sh` / `delivery-audit.sh` (o `export`).
- ⚠️ **`set -f` antes de tokenizar comando de usuário.** `pretooluse-doc-guard.sh` desliga o glob antes de iterar `for tok in $CMD`, senão um `*.json` no comando expandiria no CWD do hook e fabricaria candidatos falsos.
- ⚠️ **Hook em Python é invisível pro `hook_contract.py`.** Ele mede idioma de shell (`exit 2`, `command -v`, `${VAR:-1}`), então `plugins/bootstrap/hooks/stop-prose-ceiling.py` mede como `blocking: {}` mesmo bloqueando. Ver §5.3. Audite à mão, e não leia o silêncio do checker como aprovação.
- ✅ **Hardcodar `Path.home()/".claude"` divergia do resto do repo — CONSERTADO em 2026-07-30.** A raiz de estado é `${CLAUDE_CONFIG_DIR:-$HOME/.claude}`, e hoje `bootstrap/lib/conformance.py:CLAUDE_DIR` e `stop-prose-ceiling.py:CLAUDE_DIR` derivam da mesma env var. Fica a régua que sobrou: **par escritor↔leitor só é provado por um teste que rode OS DOIS programas** — cada lado estava coerente sozinho. Ver §1.4 e `test_conformance.py:teste_escritor_e_leitor_concordam`.
- ⚠️ **Comparar matcher de `PreToolUse` como string inteira não acha colisão.** `Grep|Glob|Bash` vs `Grep|Glob|Bash|Agent` são strings diferentes e colidem em 3 ferramentas. Parta no `|` — ver `bootstrap/lib/conformance.py:check_hooks_duplicados`.
- ⚠️ **Grep no código mede o que está ESCRITO, não o que roda — quando há flag, faça o script DECLARAR.** O `deny` do `pretooluse-graphify-guard.sh` continua no arquivo atrás de `GRAPHIFY_DENY=1` (default `0`, logo desligado), e o `permissionDecision` + `"deny"` do verificador acusava um bloqueio que não acontece. A convenção do repo é o comentário `# conformance: default-warn` no próprio hook, lido por `bootstrap/lib/conformance.py:bloqueia()` **antes** de qualquer grep — e falha de leitura assume o pior (bloqueia). Ver §5.3.
- ⚠️ **Lista de exceção tem que ser do que o programa GERA, não do que preservar.** `bootstrap/hooks/lib/snapshot.sh` reescreve o `manifest.json` e apagava chave mantida à mão (aconteceu com `skills` em 2026-07-30, minutos depois de criada). O primeiro conserto foi uma **whitelist** (`jq '{skills}'`): consertava o caso e **deixava a classe viva** — qualquer outra chave manual sumiria em silêncio no `SessionStart` seguinte. Hoje é `GENERATED_KEYS='["version","description","marketplaces"]'` e preserva o **complemento** (`with_entries(select(.key as $k | $gen | index($k) | not))`), então chave nova sobrevive sem ninguém lembrar de vir aqui; só quem passa a GERAR chave mexe na lista. A régua do teste segue a mesma inversão: `test_bootstrap_hooks.sh` planta uma chave chamada `chave_que_ninguem_conhece` — nome que uma whitelist reprovaria por construção.
- ⚠️ **Contador anti-loop chaveado por PREFIXO do texto colide.** `stop-prose-ceiling.py` usava `sha1(session_id + texto[:200])`, e como o output style exige primeira linha estável, duas respostas diferentes dividiam o mesmo orçamento de bloqueio — colisão como caso comum, não como exceção. Hoje o hash é do texto **inteiro** (`stop-prose-ceiling.py:chave`). [confirmado — o motivo está literal no comentário, e o commit `7b0357d` registra a medida: A esgota `[2,2,0]`, B com o mesmo prefixo volta 2.]
- ⚠️ **Cap que desiste tem que desistir em VOZ ALTA.** Depois de `MAX_BLOQUEIOS`, o hook de prosa libera — e sem rastro isso é um gate que se apaga sozinho. O contrato é: quem desiste grava (`~/.claude/state/prose-ceiling/bypass.log`) e alguém lê (`conformance.py:check_bypass_teto`). Cap silencioso e gate desligado são indistinguíveis pra quem usa.
- ⚠️ **`CLAUDE.md` pode estar na raiz OU em `.claude/`.** Todo detector tem que aceitar os dois e preferir o que carrega o marcador `project-doc:v2` — ver `doc-detect.sh:find_claude_md`. Hardcodar `.claude/CLAUDE.md` fazia a detecção não achar nada em projeto com CLAUDE.md na raiz e escalar até um ancestral não-relacionado.

### Regex de detecção em hook de gate

Nascidos todos da rodada de 2026-07-29 no `ship/hooks/pre-deploy-test-check.sh`, cada um medido com payload real e travado em `test_pre_deploy.sh`. A classe é uma só: **regex escrita a partir de um exemplo digitado, não da gramática do shell.**

- ⚠️ **A forma CANÔNICA do comando é a que passa batido.** `vercel\s+--prod` nasceu de alguém que digitou `vercel --prod`; a forma que a CLI documenta (`vercel deploy --prod`) nunca foi testada. Idem `ssh\s+.*\s+pm2`, que exige espaço antes do verbo — mas o comando remoto real é `ssh vps "pm2 …"`, onde uma **aspa** cola no verbo. Regra: um caso de teste **por forma que a ferramenta documenta**, não por forma que você lembra de ter digitado.
- ⚠️ **Sem âncora de início-de-comando, MENÇÃO dispara o gate.** `make[[:space:]]+deploy` sem âncora casa dentro de `git commit -m "make deploy target fixed"`; `.*--prod` guloso casa dentro de `rg "vercel deploy --prod" .`. Falso-positivo em gate de produção é pior que parece: **ensina a desligar o gate** (aqui, `SHIP_GATE=0`), e aí ele não protege nunca mais.
- ⚠️ **Clampar o meio da regex pra ganhar precisão cega a forma mais comum.** Trocar `.*` por `[^;&|]*` no padrão de `ssh` fez a busca parar no primeiro `&&` — e `ssh vps "cd /app && git pull"` é *o* jeito de deployar VPS. A precisão vem do outro eixo: **casar a AÇÃO, não o nome da ferramenta** (`pm2 restart`, não `pm2` — senão `ssh vps "pm2 logs api"` vira bloqueio).
- ⚠️ **O furo não estava na regex, estava no PARSING DE ARGUMENTO.** Os três piores achados do gate não eram detecção de deploy — eram tokens que sobreviviam ao filtro de `ARGS` (redireção `>`, valor de flag, recorte guloso no deploy encadeado) e faziam o `discover_apps()` nunca rodar, liberando **todos** os apps sem um único teste. Ver `runtime.md §6` passo 5. Quando você audita um gate, leia o parsing — não só a regex, que é onde a atenção vai por default.
- ⚠️ **Casar o SUFIXO do nome de arquivo pega a suíte que testa o próprio gate.** `[^[:space:];&|]*deploy\.sh` aceita qualquer prefixo, então casa `test_pre_deploy.sh`, `predeploy.sh` e `undeploy.sh`. Consequência medida ao vivo em 2026-07-30: **rodar `bash plugins/ship/hooks/test_pre_deploy.sh` — a suíte deste gate — era classificado como deploy**, e o release-gate roda essa suíte a cada commit. O correto é `([^[:space:];&|]*/)?deploy\.sh`: antes do nome só caminho. Custo aceito e declarado: nome composto (`app-deploy.sh`) deixa de casar.
- ⚠️ **A âncora de posição-de-comando corta o PREFIXO legítimo junto com a menção.** A âncora existe pra impedir que prosa dispare o gate, mas ela também cega `sudo ./deploy.sh`, `nohup bash deploy.sh &` e `ENV=prod ./deploy.sh` — a forma banal de destacar e de parametrizar um deploy. `nohup bash deploy.sh &` **era detectado** antes da âncora entrar: regressão medida. Solução: um grupo de prefixo **ENUMERADO** (`pre-deploy-test-check.sh:CMDPFX` — atribuição de variável + `sudo|nohup|env|time|exec|command`), nunca "qualquer palavra antes", senão a âncora deixa de existir. Teto conhecido e escrito: flag **com valor** no lançador (`sudo -u deploy ./deploy.sh`) não casa.
- ⚠️ **O hook lê a STRING do comando, então escrever código sobre deploy dispara o gate.** Um heredoc que contenha `&& ./deploy.sh` é indistinguível de uma invocação sem parser de shell. Vive-se com isso (o kill-switch `SHIP_GATE=0` existe pra isso); só morde quem edita este arquivo, e foi observado várias vezes nesta rodada.
- ⚠️ **Sabotagem de teste acoplada ao TEXTO do que ela sabota apodrece em silêncio.** A prova anti-tautologia de `test_pre_deploy.sh` mirava `)pm2` (do padrão antigo `(^|\s)pm2`); o padrão foi reescrito, o `sed` **parou de alterar qualquer coisa**, a "cópia sabotada" virou o original — a suíte passava nela e o check acusava *"a suíte não afirma nada"*, que era verdade sobre uma cópia intacta. Modo de falha confuso: parece defeito da suíte, é defeito da sabotagem. Hoje há um `cmp -s "$HOOK" "$SAB"` que exige que a sabotagem tenha **alterado** o arquivo, com mensagem dizendo pra retargetar. Mesma família do `project_staleness` espelhando o `scope_staleness` (§7 project-doc): **verificador que duplica o verificado precisa de trava que compare os dois.**
- ⚠️ **`\s` não é POSIX em ERE.** O arquivo mistura `\s` (histórico) e `[[:space:]]` (correto). Em linha nova, use `[[:space:]]` — e prove que a detecção casa com um caso na suíte, porque `\s` que não funciona falha **abrindo** o gate, em silêncio.

### Release

- ⚠️ **O release-gate avalia `staged ∪ tracked-modificados`** (`FILES` em `.claude/hooks/release-gate.sh`), não só o que você deu `git add`. **Consequência prática: uma mudança solta e não-commitada em `plugins/OUTRO/` bloqueia o SEU commit** por bump/espelho/teste de um plugin que você nem tocou. [confirmado — o `FILES` deste run, com nada staged, já listava 7 caminhos vindos só de `git diff --name-only`.] Saída: `git stash` do alheio, ou commitar em conjunto.
- ⚠️ **Untracked NÃO entra no gate** — por decisão, comentada no próprio arquivo (estado de runtime como `plugins/visual/skills/visual/config.json` dava falso-positivo). Corolário: **plugin novo, ainda não `git add`-ado, passa sem bump e sem teste.**
- ⚠️ **O gate casa a string `git … commit`, não o repositório do comando.** O regex é `(^|[;&|]|&&)[[:space:]]*git[[:space:]]+.*commit`, e logo depois `ROOT=$(git rev-parse --show-toplevel)` roda **no cwd do hook**, sem `-C`. Ou seja: `cd /tmp/fixture-x && git commit -m x` dispara o gate **contra o pedro-plugins**, não contra a fixture. [confirmado neste run: o regex casa e `git rev-parse` devolve a raiz do pedro-plugins.] Isso atrapalha suítes que commitam em repo de teste dentro de `/tmp`.
- ⚠️ **Bump sem espelho (ou vice-versa) é erro em dois lugares.** `plugins/<nome>/.claude-plugin/plugin.json` **e** `.claude-plugin/marketplace.json`. Checks B e C do gate cobrem — mas só para plugin com arquivo no diff.
- ⚠️ **`author` como string em `marketplace.json` e `": "` / `<>` no `description:` de SKILL.md bloqueiam a instalação em silêncio** [relatado, memória marcada STALE — o repo hoje está consistente com o fix]. `claude plugin validate .` é o único diagnóstico.

### Código compartilhado

- ⚠️ **Editar a cópia vendorada em vez de `_shared/`.** O sync sobrescreve na próxima rodada e seu fix some. Fonte é `_shared/<arquivo>`; `scripts/sync-shared.sh:SPECS` diz para onde cada um vai.
- ⚠️ **Editar `_shared/` e esquecer o sync** deixa as 6 cópias defasadas — pego pelo check A no commit, e por `bash scripts/sync-shared.sh --check` na mão.

### project-doc

- ⚠️ **`pattern_check.py --sig` carimba sempre o `CURRENT_GEN` do CÓDIGO**, não a gen do doc-set — e isso é por construção, não bug: `sig()` interpola `CURRENT_GEN` incondicionalmente. Quem tem "gen não bumpa" como invariante (`/doc-touch`) **não deve chamar `--sig` direto.** Desde a v3.17.0 existe o verbo que faz certo:

```bash
python3 plugins/project-doc/lib/pattern_check.py --project-root . --restamp .claude/docs/<tocados>
```

  `restamp()` carimba `generated`, `generated-commit` e `doc-sig` de uma vez, lendo a gen do **doc-set** por `doc_set_gen()` (marker do `CLAUDE.md`), pula doc autoral (`authored-by: human`) e arquivo sem frontmatter, e **falha sem escrever nada** se não resolver o HEAD. A receita de `sed` que vivia aqui era o convite ao erro que o verbo eliminou. [confirmado — `test_pattern_check.py:test_restamp`, 16 checks, um deles fixando que o `--sig` cru **continua** carimbando a gen do código]

- ⚠️ **Um doc não consegue citar o commit que o contém — o rito é de DOIS commits.** O
  `generated-commit:` diz "esta doc vale pro estado do código no commit X". Se código e doc
  entram no **mesmo** commit, X ainda não existe quando o frontmatter é escrito; o carimbo
  aponta pro anterior, a janela de staleness enxerga a mudança que a **própria doc
  descreve**, e o hook grita "DEFASADA" sobre doc recém-nascida. Este repo fez o commit
  só-de-carimbo **3× antes de virar comando** (`16211ae`, `b9028c3`, `8d7a5a0`). Rito:
  commit do conteúdo → `--restamp` → commit do carimbo. Está no
  `skills/doc-touch/SKILL.md` §5.
- ⚠️ **`doc-sig` só depois do corpo estar final** — o `hash8` é `sha256(corpo)`; qualquer edição posterior deixa a sig mentindo. O `restamp()` respeita isso por construção (só mexe no frontmatter, e recomputa a sig do corpo).
- ✅ **Os dois medidores de staleness discordavam, e era o pior deles que falava com o
  usuário — CONSERTADO na v3.16.0 (2026-07-29).** Vale ler porque a **classe** do defeito é
  reincidente neste repo: uma função barata que duplica a lógica de uma caprichada e vai
  ficando atrás dela.
  `pattern_check.py:scope_staleness` (por doc) sempre honrou `generated-commit:`.
  `pattern_check.py:project_staleness` — o **agregado que os hooks consomem** — divergia em
  dois pontos, e os dois eram falha silenciosa:
  1. **ignorava `generated-commit`** e usava só `_git_log_since(min_date)`, janela com
     **granularidade de dia**: `/doc-touch` + commit no mesmo dia ⇒ hook do SessionStart
     gritando "⚠️ DEFASADA" sobre doc que acabou de nascer. Medido: os 5 docs deste repo
     davam `fresh` um por um e `stale` no agregado, no mesmo instante, porque commits do
     mesmo dia tocaram 13 arquivos de scope.
  2. **interseção crua de strings** em vez de `_scope_match` ⇒ doc policiada por
     **diretório** (`lib/`) ou glob **nunca** ficava stale ali. É a mesma sub-detecção que o
     `scope_staleness` já tinha consertado, com comentário e tudo, e que o agregado não
     recebeu.
  Hoje ele agrupa os docs por **base de comparação** (um bucket por `generated-commit`
  distinto, outro pela janela de data pros docs sem carimbo resolvível), gasta 1 git call
  por bucket — na prática 1, porque o touch carimba todos juntos — e casa com
  `_scope_match`. Fallbacks preservados: carimbo que não resolve cai pra data; git com erro
  ⇒ `unknown`, nunca `fresh`.
  **A lição, que é o que importa:** função barata que espelha uma caprichada precisa de
  teste que compare **as duas**, senão ela deriva em silêncio. Os 11 checks novos de
  `test_pattern_check.py` fazem isso — dois deles afirmam `agregado == por-doc` no mesmo
  fixture. [confirmado — os dois defeitos reproduzidos contra
  `git show HEAD:plugins/project-doc/lib/pattern_check.py` e ausentes no novo; auditoria
  independente injetou o payload real no `posttooluse-doc-read.sh` e viu o aviso falso
  aparecer no código antigo e sumir no novo]
- ⚠️ **Ponteiro por número de linha na doc gera WARN, e FAIL quando morre.** `doc_lint.py:POINTER_RE` valida `arquivo:N` contra o repo. Prefira **arquivo + símbolo** — é a razão de este documento não citar linha nenhuma.
- ⚠️ **`doc_lint.py` também confere contagens** (`COUNT_RE`): "N itens:" seguido de lista com M ≠ N vira WARN. Escreva a lista, ou derive o número mecanicamente.
- ⚠️ **`doc-detect.sh:DOC_FILES` tem um filtro de ruído LOAD-BEARING** (`node_modules`, `.git`, `_repos-antigos`, `.next`, `worktrees`, `backups`, `.project-doc`, `legacy-pre-migracao`). Sem podar, worktrees e backups duplicam a árvore de docs ~10× e o hook surfaceia uma cópia legada como projeto fresco. **O filtro espelha o `CENSUS_PRUNE` do `organism.py` — mudou um, alinhe o outro.**

### Ambiente

- ⚠️ **`rm -rf` é política negada, não preferência.** `Bash(rm -rf*)` e `Bash(rm -r*)` estão no bloco `permissions.deny` do `plugins/bootstrap/config/settings-defaults.json` versionado — a política do repo é remoção alvo. Os defaults versionados hoje são **141 entradas de `allow` e 19 de `deny`**, e a máquina desta rodada já as tem aplicadas (`~/.claude/settings.json`: 145 `allow`, 19 `deny`) `[confirmado — os dois JSON lidos aqui]`.
- ✅ **A config versionada parou de afrouxar aprovação — `ff32947`.** Duas mudanças no mesmo `settings-defaults.json`, e a segunda explica a primeira:
  - **`permissions.defaultMode` sumiu do arquivo.** Era `"auto"`; hoje `permissions` tem exatamente duas chaves, `allow` e `deny` `[confirmado — `sorted(permissions.keys())` nesta rodada devolve `['allow','deny']`]`. Sem a chave, o merge do `apply-config.sh` **não toca** o modo de aprovação da máquina — o dela continua valendo (aqui, `default`). A `skills/setup/SKILL.md` escreve o contrato: *"o modo de aprovação continua o que já estava nesta máquina, e o setup nunca liga aprovação automática."*
  - **Saíram da allowlist `Bash(eval*)`, `Bash(export*)`, `Bash(ssh*)` e `Bash(curl*)`.** A régua não é "comando perigoso" — é **escopo do padrão**: `eval` e `export` executam string arbitrária, e `ssh`/`curl` são a fronteira da máquina pra fora, então aprovar o prefixo aprova tudo que vier depois. Os específicos que não têm essa propriedade ficaram: `Bash(ssh-add*)` segue na allow. **Corolário pra quem for acrescentar entrada nova:** aprove o verbo com o objeto (`docker inspect*`), nunca a ferramenta sozinha quando o resto da linha é livre.
  - **A regra que as duas compartilham** (a mesma do opt-in de desinstalação, `architecture.md §10.4`): config versionada que roda por hook em máquina alheia **só pode adicionar**. Somar permissão que o dono conferiu é aditivo; baixar o modo de aprovação e desinstalar software não são.
- ⚠️ **`scope-cop` (guardrails) bloqueia `.html` fora dos paths-artefato** [relatado, memória — confirmado no código: `plugins/guardrails/hooks/scope-cop.sh` isenta `*/.claude/*`, `*/docs/*`, `*HANDOFF*`, `*PRD*`, `*plan*.html`, `*_archive/*`]. Um intermediário em `/tmp/algo.html` **não** casa a isenção e é negado. Monte o HTML direto em `.claude/visual/…html`; se precisar de corpo temporário, use extensão que não seja `.html`. Desde a 1.4.0 o flag `~/.claude/guardrails/scope-cop.mode` tem o degrau `warn` (avisa sem bloquear) além de `deny`/`off` — ver §1.4.
- ⚠️ **`session-sync` (bootstrap) corre com o `git push` manual** [relatado, memória — não reproduzido nesta rodada]. Depois de um `git add`, o hook auto-commita e empurra; o seu `push` volta `remote rejected` e o `commit` volta "nothing to commit". **Não é erro** — o remoto já está no seu commit. Faça `git fetch` e confira `HEAD == origin/<branch>`; nunca `--force`.
- ⚠️ **`pi-plugins/` na raiz é LIXO A LIMPAR**, não fonte. Cópia obsoleta e já divergente de vários plugins, que engana busca cega. **A fonte é sempre `plugins/`.** Ela **está gitignorada desde 2026-07-28** e por isso saiu do grafo e do `git status` [confirmado nesta rodada — `git check-ignore -v pi-plugins/` → `.gitignore:47:pi-plugins/`, e `git status --porcelain | grep -c pi-plugins` → `0`]. ⚠️ **Gitignorar não é apagar:** o diretório segue no disco, então `grep -r` e `find` da raiz continuam achando as cópias velhas — ancore a busca em `plugins/`.

---

## 8 · Fluxo de trabalho recomendado

```bash
# 1. mexeu em código compartilhado?
vim _shared/<arquivo>            # SEMPRE na fonte
bash scripts/sync-shared.sh      # vendora as cópias

# 2. mexeu num plugin?
vim plugins/<nome>/.claude-plugin/plugin.json      # bump da version
vim .claude-plugin/marketplace.json                # espelhe a mesma version

# 3. verifique antes de commitar
claude plugin validate .
for t in plugins/<nome>/lib/test_*.py; do python3 "$t"; done
bash scripts/sync-shared.sh --check

# 4. commit — o release-gate roda A–G sozinho e sai 2 se algo violar
git add -A plugins/<nome> .claude-plugin/marketplace.json
git commit -m "..."

# 5. hook novo? confirme que ele carregou
claude plugin details <nome>@pedro-plugins    # tem que mostrar Hooks (N>0)
/reload-plugins                                # o cache do cliente não auto-refresca
```
