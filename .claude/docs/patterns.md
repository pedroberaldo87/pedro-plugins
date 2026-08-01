---
generated: 2026-08-01
generated-commit: 73d2fce
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
  - plugins/guardrails/lib/askq_lint.py
  - plugins/guardrails/hooks/scope-cop.sh
  - plugins/bootstrap/hooks/stop-prose-ceiling.py
  - plugins/bootstrap/hooks/stop-forma-relato.py
  - plugins/bootstrap/hooks/hooks.json
  - plugins/bootstrap/lib/conformance.py
  - plugins/context-guard/hooks/context-guard-writer.sh
  - plugins/ship/hooks/pre-deploy-test-check.sh
  - plugins/visual/lib/visual_page.py
  - plugins/visual/lib/plan_state.py
  - plugins/visual/lib/cobertura.py
  - plugins/slides/lib/md2deck.py
  - scripts/hook_contract.py
  - .claude-plugin/marketplace.json
verified-by:
  - plugins/bootstrap/lib/test_conformance.py
  - plugins/bootstrap/hooks/test_bootstrap_hooks.sh
  - plugins/project-doc/hooks/test_plan_gate.sh
  - plugins/project-doc/lib/test_doc_lint.py
  - plugins/project-doc/lib/test_pattern_check.py
  - plugins/guardrails/lib/test_askq_lint.py
  - plugins/guardrails/hooks/test_scope_cop.sh
  - plugins/graphify-guard/hooks/test_graphify_guard.sh
  - plugins/guardrails/hooks/test_setup_skill.sh
  - plugins/ship/hooks/test_pre_deploy.sh
  - plugins/visual/lib/test_visual_page.py
  - plugins/visual/lib/test_plan_state.py
  - plugins/visual/lib/test_cobertura.py
  - plugins/slides/lib/test_md2deck.py
  - scripts/sync-shared.sh
  - scripts/hook_contract.py
doc-sig: pedro-plugins/release-gate.sh@gen=3.8#78273f87
---

# Patterns & Gotchas

Convenções deste marketplace. Tudo aqui é regra lida no código desta rodada, não estilo sugerido.
Rótulos: **[confirmado]** = li o arquivo ou rodei o comando nesta rodada · **[inferido]** = deduzido, não testado · **[relatado]** = veio de comentário/registro no próprio código.

---

## 1 · Shell (hooks)

### 1.1 Fail-open é lei

Hook que erra **libera a ação**. Derivado mecanicamente neste run:

```bash
grep -rli 'fail-open\|fail open' plugins/*/hooks/*.sh .claude/hooks/*.sh _shared/*.sh | wc -l
# → 41 arquivos (inclui as suítes test_*.sh, que herdam a convenção)
```

Arquivos que **declaram** a regra no cabeçalho, entre eles [confirmado]:

- `.claude/hooks/release-gate.sh` — *"FAIL-OPEN em erro de infra (sem git/python3, fora do repo): só bloqueia com evidência concreta na mão."*
- `plugins/project-doc/hooks/doc-detect.sh` — *"Fail-open: any error → no output, exit 0. Never blocks the caller."*
- `plugins/project-doc/hooks/posttooluse-doc-read.sh` — *"Fail-open: any error → exit 0. Never blocks."*
- `plugins/ship/hooks/pre-deploy-test-check.sh` — `command -v jq >/dev/null 2>&1 || exit 0`, com o comentário *"(marketplace convention)"*
- `_shared/green-cache.sh` — *"Fail-open na direção SEGURA: qualquer erro → MISS → a suite roda."*
- `plugins/bootstrap/hooks/stop-forma-relato.py` — *"FAIL-OPEN em tudo que nao for reprovacao explicita … Guarda que trava a sessao por infra e pior que guarda nenhum."*

**A direção segura muda por gate** [confirmado]:

- `green-cache.sh` → o lado seguro é **MISS** (roda a suite de novo), nunca HIT.
- `doc-detect.sh:doc_staleness` → o ternário é `fresh|stale|unknown`, e a borda de erro cai em **`unknown`** (fail-LOUD). Fingir "fresco" é o único resultado proibido.
- `pretooluse-plan-gate.sh` → o fail-open cobre **só** a borda de infra (sem `jq`, sem raiz resolvível, `doc-detect.sh` ilegível). Determinar que *não há documentação* é evidência concreta ⇒ nega. A guarda `[ -r "$SCRIPT_DIR/doc-detect.sh" ] || exit 0` existe porque um `chmod 000` no helper fazia projeto documentado cair no caso "sem doc" — regressão coberta pelo caso R7 de `test_plan_gate.sh` [confirmado, suíte verde nesta rodada: 49 passou · 0 falhou].

### 1.2 Protocolo de saída de hook

Três canais, escolhidos por evento e por intenção:

- **`exit 0` mudo** — libera. Default de todo hook fora do seu escopo (`case "$TOOL" in … *) exit 0 ;;`). ⚠️ **"Mudo" vale pra stderr também**: em `PreToolUse`/`PostToolUse` o stdout/stderr de um `exit 0` vai pro debug log, não pro transcript. É o que `pre-deploy-test-check.sh` documenta no bloco `allow_with_notes` [confirmado, comentário literal]: *"os avisos deste gate não chegavam a ninguém, nem ao modelo nem ao usuário. Incluindo o pior deles, 'deploy permitido sem verificação'"*.

  O canal certo pro caminho que **libera** é JSON no stdout — e o gate do ship emite os **dois** públicos de uma vez:

  ```bash
  allow_with_notes() {
    [ -n "$NOTES" ] && jq -n --arg m "$NOTES" \
      '{systemMessage:$m, hookSpecificOutput:{hookEventName:"PreToolUse", additionalContext:$m}}'
    exit 0
  }
  ```

- **`exit 2` + mensagem em stderr** — bloqueia de fato; o stderr volta pro modelo. Arquivos com `exit 2` neste run (`grep -rln 'exit 2' plugins/*/hooks/*.sh .claude/hooks/*.sh`): `.claude/hooks/release-gate.sh`, `plugins/guardrails/hooks/lint-and-typecheck.sh`, `plugins/intent-guard/hooks/plan-gate.sh`, `plugins/ship/hooks/pre-deploy-test-check.sh`, `plugins/visual/hooks/pre-exitplan-visualize.sh` (+ as suítes `intent-guard/hooks/test_plan_gate.sh` e `ship/hooks/test_pre_deploy.sh`).
- **JSON no stdout** — o canal estruturado:

```bash
# DENY (PreToolUse) — pretooluse-doc-guard.sh, pretooluse-plan-gate.sh
jq -n --arg r "$MSG" \
  '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
exit 0

# INJETAR CONTEXTO (PostToolUse / UserPromptSubmit) — sem permissionDecision
jq -n --arg c "$MSG" \
  '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$c}}'
```

Regra de desenho por trás [confirmado, comentário em `posttooluse-doc-read.sh`]: **PostToolUse injeta, nunca nega** — é *"estruturalmente incapaz de loopar (ao contrário de um deny no Read, que bloquearia a ação que libera o sentinel)"*.

**Quem emite deny sai com `exit 0`**: o veredito vem do JSON, não do exit code. Misturar os dois (JSON + `exit 2`) não aparece em nenhum hook lido aqui.

**Hooks Python existem, e são dois** [confirmado — `find plugins -path '*/hooks/*' -type f -name '*.py'` devolve exatamente `stop-prose-ceiling.py` e `stop-forma-relato.py`]. Os dois são de `Stop`, os dois escrevem em stderr **só** no caminho que sai 2 — que num `Stop` é o canal que devolve o texto ao modelo. O uso está certo; o que quebra é a **auditoria** deles (§5.3).

### 1.3 Contrato anti-loop: o cap

Gate degrada, nunca trava de verdade. No shell o padrão é o contador em `/tmp`, repetido em `pretooluse-doc-guard.sh` e `pretooluse-plan-gate.sh` [confirmado, copiado literal]:

```bash
MAX_NUDGES=3
COUNT_FILE="/tmp/claude-doc-guard-count-${SESSION}-${PHASH}"
COUNT=0; [ -f "$COUNT_FILE" ] && COUNT="$(cat "$COUNT_FILE" 2>/dev/null)"
[ "$COUNT" -eq "$COUNT" ] 2>/dev/null || COUNT=0     # sanitiza lixo no arquivo
[ "$COUNT" -ge "$MAX_NUDGES" ] && exit 0             # desistiu → libera
echo $((COUNT + 1)) > "$COUNT_FILE"
```

Nos hooks Python o cap é o mesmo desenho com outra grafia — um arquivo-contador por `sha1(session_id + texto)` [confirmado, os dois arquivos]:

```python
MAX_BLOQUEIOS = 2
chave = hashlib.sha1((str(sid) + texto).encode()).hexdigest()[:16]
contador = ESTADO / chave
n = int(contador.read_text()) if contador.exists() else 0
if n >= MAX_BLOQUEIOS: ...   # desiste
```

O `stop-prose-ceiling.py` explica por que o hash é do texto **inteiro** e não de um prefixo [confirmado, comentário literal]: *"com texto[:200] duas respostas diferentes que comecam igual dividiam o mesmo orcamento — e o output style manda a 1a linha ser estavel, entao a colisao era o caso comum, nao a excecao."*

**Desistir não pode ser silencioso.** Quando o teto de prosa desiste, ele grava uma linha em `bypass.log`; o `conformance.py:check_bypass_teto` transforma isso em número visível. Sidecar do mesmo raciocínio no juiz de forma: cada execução vira uma linha em `batidas.log` (§5.4).

**Exceção deliberada** [confirmado]: o CASO A do `pretooluse-plan-gate.sh` (projeto com zero documentação) **nega sempre, sem cap** — decisão registrada no cabeçalho do arquivo. O único escape é verbal, via `userpromptsubmit-plan-escape.sh`, e a suíte cobre com o caso `sem doc: nega nas 5 tentativas (sem cap de nudges)`.

### 1.4 Estado mutável: `~/.claude/`, NUNCA dentro do plugin

O diretório do plugin (`${CLAUDE_PLUGIN_ROOT}`) é **cache reescrito a cada bump de versão** — gravar estado lá o apaga sem aviso. Literal em `_shared/green-cache.sh`:

> Estado em `~/.claude/green-suite/` (NUNCA dentro do plugin — o cache `${CLAUDE_PLUGIN_ROOT}` é reescrito a cada bump de versão).

**A raiz é `${CLAUDE_CONFIG_DIR:-$HOME/.claude}`, não `$HOME/.claude` cru.** Os três lados que li nesta rodada respeitam a env var, e cada um aponta para o outro no comentário [confirmado]:

```python
# plugins/bootstrap/lib/conformance.py
CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", HOME / ".claude"))
# plugins/bootstrap/hooks/stop-prose-ceiling.py  (e stop-forma-relato.py, idêntico)
CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
```

```bash
# plugins/guardrails/hooks/scope-cop.sh
HOOK_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/guardrails"
```

O `scope-cop.sh` explica a razão melhor que qualquer regra abstrata [confirmado, citação literal]: *"o gate que o auditor acusa não seria o que o hook obedece, e cada lado ficaria coerente sozinho (o mesmo defeito silencioso do bypass.log do stop-prose-ceiling)"*.

Locais de estado em uso, entre eles [confirmado, `grep -rhoE` sobre hooks e libs nesta rodada]:

- `$HOME/.claude/green-suite/` — `_shared/green-cache.sh:GREEN_SUITE_DIR` (override por env de mesmo nome)
- `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/guardrails/` — `scope-cop.sh` (`scope-cop.mode`, `scope-cop.log`, `scope-cop.blockstreak.<sid>`, `scope-cop.bypass.<sid>`) e `askq.log`
- `$HOME/.claude/intent-guard/mode` — kill-switch do intent-guard
- `$HOME/.claude/context-guard/mode` — kill-switch do context-guard
- `$HOME/.claude/plugins/` — `session-sync.sh` (`.pedro-plugins-last-sync`, `.pedro-plugins-sync.lock`, `known_marketplaces.json`)
- `CLAUDE_DIR/state/prose-ceiling/` — `stop-prose-ceiling.py:ESTADO` (contador por resposta + `batidas.log` + `bypass.log`)
- `CLAUDE_DIR/state/forma-relato/` — `stop-forma-relato.py:ESTADO`, com **variável própria** `FORMA_RELATO_STATE`
- `CLAUDE_DIR/state/intent-guard/olhado` — `ledger.py:furos_da_regua`, **novo nesta rodada**. Um plugin lendo o estado que **outro** plugin escreve (`state/prose-ceiling/` e `state/forma-relato/`), e por isso ele copia a expressão de raiz literalmente igual à dos dois escritores. ⚠️ **Não confundir com `$HOME/.claude/intent-guard/mode`**, que é outro diretório, de outro dono: um é kill-switch, o outro é marca de leitura.

**Por que o juiz tem variável de estado separada** [confirmado, comentário literal em `stop-forma-relato.py`]: *"estado com var propria: isolar o teste via CLAUDE_CONFIG_DIR tirava a credencial do `claude -p` junto, e o juiz passava a aprovar tudo por fail-open."* Régua durável: **hook que chama binário autenticado não pode ter o isolamento do teste amarrado ao mesmo diretório da credencial.** A suíte confirma que o cuidado é real — `test_bootstrap_hooks.sh` roda o juiz com `env -u CLAUDE_CONFIG_DIR FORMA_RELATO_STATE="$TMP/forma-$2"`.

**Kill-switch = interruptor de uma linha, e ele nunca nasce ligado por padrão.** No shell é env var `<NOME>_GATE=0` (§5.3); nos hooks Python é `PROSE_CEILING=0` e `FORMA_RELATO=0` [confirmado, copiados dos dois arquivos]. Nenhuma dessas variáveis aparece em `plugins/bootstrap/config/settings-defaults.json` [confirmado, li o `env` do arquivo], então **os dois guardas nascem ligados** — que é a premissa que o `stop-prose-ceiling.py` registra no histórico:

> Historico, para nao reincidir: em 2026-07-30 este teto foi transformado em opt-in sob o argumento "e preferencia do dono, nao regra universal". A variavel nunca foi definida, entao o guarda ficou inerte e a primeira resposta seguinte ja estourou. Premissa que nasce desligada nao e premissa — e comentario.

⚠️ **"Ligado ou desligado" é pouco: o flag do scope-cop é ternário `deny|warn|off`** [confirmado — o cabeçalho lista os três, e o motivo está literal no arquivo]: o gate ficou em `off` depois de 3 bloqueios seguidos, e o estado meio-ligado *"faz parecer que existe trava de escopo onde não existe. Aviso é honesto; silêncio não."* **Gate que você vai acabar desligando devia nascer com o degrau do meio.** O `conformance.py:check_gates_enganosos` cobra esse estado dos dois jeitos: `.mode` valendo `off/0/disabled` com o plugin ainda habilitado, **e** `.mode` homônimo em duas pastas — *"o defeito e a EXISTENCIA do duplicado, nao o valor dele — editar o inerte nao muda comportamento nenhum e nao avisa"*.

### 1.5 Estado por-sessão em `/tmp` tem que ser chaveado por `session_id`

Regra nascida de bug real, documentada no cabeçalho de `context-guard-writer.sh` [confirmado, citação literal]:

> ⚠️ PER-SESSION state (não global): o statusLine de QUALQUER sessão renderiza no mesmo host; um arquivo global (`/tmp/claude-context-pct`) era sobrescrito pela última sessão a renderizar, então uma sessão cheia (80%) fazia o guard bloquear TODAS as outras.

```bash
[ -n "$PCT" ] && [ -n "$SID" ] && printf '%s' "$PCT" > "/tmp/claude-context-pct-${SID}"
```

Sem `session_id` o writer **não grava** — fail-safe declarado no arquivo: *"guard sem arquivo da sessão = não dispara"*.

A mesma classe de bug reapareceu no `scope-cop.sh` e foi consertada do mesmo jeito [confirmado, comentário literal]: *"Com duas sessões abertas no mesmo projeto, os BLOCKs de uma contavam pro freio da outra … É a mesma classe de bug que já mordeu o context-guard"*. O conserto acrescentou poda (`find … -mtime +1 -delete`) — **arquivo por sessão precisa de janela de expiração no mesmo commit em que nasce**.

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

Quem escreve o sentinel é `posttooluse-doc-read.sh`, e ele **recorta a string**:

```bash
case "$FP" in
  */.claude/docs/*)    PROJ="${FP%%/.claude/docs/*}" ;;
  */.claude/CLAUDE.md) PROJ="${FP%/.claude/CLAUDE.md}" ;;
  */CLAUDE.md)         PROJ="${FP%/CLAUDE.md}" ;;
  *) exit 0 ;;
esac
PHASH=$(printf '%s' "$PROJ" | cksum | cut -d' ' -f1)
```

Duas normalizações — e só essas duas — são permitidas [confirmado nos dois arquivos]: **relativo → absoluto** (`posttooluse-doc-read.sh`, `case "$FP" in /*) : ;; *) FP="$CWD/$FP" ;; esac`) e **remover a barra final** (`lib-project-root.sh:project_root`, porque `/a/b` e `/a/b/` dão `cksum` diferente).

Consumidores da mesma chave hoje [confirmado]: `pretooluse-doc-guard.sh` (`find_doc_up` + `cksum` inline), `pretooluse-plan-gate.sh` e `userpromptsubmit-plan-escape.sh` (ambos via `. lib-project-root.sh`), `posttooluse-doc-read.sh` (recorte de string). **Hook novo que fale desses sentinels usa `project_root`/`project_hash` — não reimplemente a subida.**

O teste protege com dois casos E2E não-tautológicos (R9/R10 em `test_plan_gate.sh`): o sentinel é escrito rodando o `posttooluse-doc-read.sh` de verdade, e o gate tem que liberar. O comentário registra por quê [confirmado, literal]: *"Recalcular a chave à mão aqui foi exatamente o que mascarou o bug de path na 1ª rodada."*

Nomes de sentinel em uso, com o dono de cada um [confirmado]:

- `/tmp/claude-doc-guard-${SESSION}-${PHASH}` — escrito por `posttooluse-doc-read.sh`; lido pelo doc-guard **e** pelo plan-gate (canal compartilhado, de propósito)
- `/tmp/claude-doc-guard-count-${SESSION}-${PHASH}` — contador do doc-guard
- `/tmp/claude-plan-gate-count-${SESSION}-${PHASH}` — contador do plan-gate
- `/tmp/claude-plan-gate-escape-${SESSION}-${PHASH}` — escape verbal, escrito por `userpromptsubmit-plan-escape.sh`
- `/tmp/claude-context-pct-${SID}` — escrito pelo `context-guard-writer.sh`

### 1.7 Regex de intenção: fronteira de palavra e o lado seguro

`userpromptsubmit-plan-escape.sh` é o caso de referência [confirmado — três armadilhas listadas no cabeçalho e cobertas por R1/R2/R4 da suíte]:

```bash
B='(^|[^[:alnum:]])'                                   # fronteira de palavra à esquerda
DOC='(doc|docs|documenta[çc][ãa]o|documentacao)([^[:alnum:]]|$)'
EXTERNAL_RE="(doc|docs|documenta[çc][ãa]o|documentacao)[[:space:]]+(do|da|dos|das|de)[[:space:]]+[[:alnum:]]"
```

- **Fronteira obrigatória antes de todo verbo.** Sem ela, `"esta**va** sem documentação"` e `"con**segue** sem doc"` — constatações — liberavam o gate.
- **`EXTERNAL_RE`**: `doc do/da/de <coisa>` é doc de terceiro ("ignora a doc do React"), nunca ordem sobre a doc do projeto.
- **Ambiguidade resolve pro lado seguro**: casou escape *e* external ⇒ não libera; quem quer liberar usa o token inequívoco `--sem-doc`.
- **Toda liberação tem revogação**: `REVOKE_RE` (`--com-doc`, "exige a doc") apaga o sentinel.

**A régua nova exige teste do lado que ela NÃO pode pegar** [confirmado, `askq_lint.py`]. O padrão de caminho do `CODE_TELLS` carrega um lookahead exigindo letra no primeiro segmento — `/(?=[\w.-]*[A-Za-z])[\w.-]+/[\w.-]+` — e o comentário diz por quê: *"Sem ele, '30/07/2026' casa como caminho e o gate barra toda pergunta que cita uma data — falso-positivo que treinaria o usuário a desligar o gate no primeiro dia."*

**E a lição sobre allowlist: ela precisa de teste que prove que é ELA que libera.** Maiúscula no meio da palavra é ao mesmo tempo o sinal mais forte de identificador e a grafia normal de nome próprio; `askq_lint.py` resolve com `_MEIO_MAIUSCULO` + a allowlist `NOMES_PROPRIOS` (comparação em minúsculas), consumidas por `camel_suspeitas()`. O comentário registra o caso real: *"Sem esta lista, 'o commit já está no GitHub' é barrado (foi o que aconteceu na PRIMEIRA pergunta real, 2026-07-30)."* [confirmado — `test_askq_lint.py` verde nesta rodada: 47 passou · 0 falhou].

### 1.8 Prelúdio, portabilidade e exit code

- **`set` varia por TIPO de script, de propósito** [confirmado]. Build usa `set -euo pipefail` (`scripts/sync-shared.sh`); gate usa `set -uo pipefail` sem o `-e` (`.claude/hooks/release-gate.sh`); e `plugins/guardrails/hooks/scope-cop.sh` **não declara `set` nenhum** (`grep -c '^set ' plugins/guardrails/hooks/scope-cop.sh` → 0). Motivo: com `-e`, um hook-trava abortaria no meio de uma checagem e viraria bloqueio acidental — o oposto do fail-open.
- **Binário se resolve por `command -v`, nunca por caminho absoluto** [confirmado, `scope-cop.sh`]: `JQ="$(command -v jq)"`, `PY="$(command -v python3)"`, `CLAUDE_BIN="$(command -v claude 2>/dev/null)"`, com o comentário *"Sem path hardcoded de app específico — isso amarrava o hook a uma máquina/app."* No Python o equivalente é `shutil.which("claude")` em `stop-forma-relato.py:julga`.
- **`.cwd` ausente não pode apagar o gate** [confirmado, `pre-deploy-test-check.sh`]: era `[ -z "$CWD" ] && exit 0`, hoje é `[ -z "$CWD" ] && CWD="$PWD"`, com a justificativa *"falha VISÍVEL (bloqueio com mensagem) … é estritamente melhor que gate invisível"*.
- **Âncora de posição-de-comando na detecção**, e prefixo **enumerado**, nunca "qualquer palavra antes" [confirmado, `pre-deploy-test-check.sh:CMDPFX`]:

```bash
CMDPFX='([A-Za-z_][A-Za-z0-9_]*=[^[:space:];&|]*[[:space:]]+|(sudo|nohup|env|time|exec|command)([[:space:]]+-[^[:space:];&|]+)*[[:space:]]+)*'
```

  O comentário nomeia o contrapeso: *"senão a âncora deixa de existir e a menção volta a disparar (o contrapeso está na suíte: `echo sudo ./deploy.sh` e `git commit -m "sudo ./deploy.sh quebrou"` seguem 0)"* [confirmado — `test_pre_deploy.sh` nesta rodada: `100 ok, 0 falhas`].

### 1.9 Chamada interna de LLM tem que se auto-marcar

Gate que invoca modelo dispara os hooks do próprio marketplace de novo, agora com o prompt do juiz. Duas marcas coexistem hoje, com a mesma forma [confirmado]:

```bash
# plugins/intent-guard/hooks/capture-prompt.sh
[ -n "${INTENT_GUARD_INTERNAL:-}" ] && exit 0
# quem chama exporta antes: plan-gate.sh, task-checkpoint.sh, delivery-audit.sh
```

```python
# plugins/bootstrap/hooks/stop-forma-relato.py:julga
ambiente = dict(os.environ, FORMA_RELATO="interno")
r = subprocess.run([exe, "-p", "--model", modelo], input=PROMPT % texto[:6000], env=ambiente, ...)
```

O juiz de forma acrescenta uma distinção que vale copiar [confirmado, comentário literal]: *"'interno' e desligamento silencioso, '0' e o kill-switch do dono"* — o subprocesso do próprio juiz sai **sem nem registrar batida**, para não poluir a auditoria com execuções que ele mesmo causou.

### 1.10 Sidecar: quem SABE grava ao lado

Padrão de `delivery-audit.sh`, generalizável a todo gate que pergunta agora e lê a resposta depois: o hook cola no prompt do auditor a lista de pedidos vivos **daquele instante** e grava essa lista num arquivo irmão `<artefato>.escopo`, porque o JSON de resposta só existe turnos depois. As três propriedades [relatado — comentários do arquivo, lido por grep nesta rodada]: **grava quem sabe, no instante em que sabe**; **o nome deriva do artefato**, não de sessão nem de timestamp; **ausência é estado legítimo e tem que ser o conservador** (artefato sem sidecar cai no comportamento antigo, que cobra tudo).

O mesmo raciocínio aparece nos dois hooks Python de `Stop` como `batidas.log` — o gate registra o que sabe no instante em que sabe, e o `conformance.py` lê depois (§5.4).

---

## 2 · Python

### 2.1 Stdlib puro, sem exceção observada

Não há `requirements.txt`, lockfile nem venv no repo. Duas varreduras neste run, porque **existe Python em `hooks/` além de `lib/`**:

```bash
grep -rhoE '^(import|from) +[a-zA-Z_][a-zA-Z0-9_]*' plugins/*/lib/*.py _shared/*.py | awk '{print $2}' | sort -u
# argparse askq_lint branch_state cobertura collections contextlib datetime difflib doc_lint
# fcntl glob graph_map hashlib html io journal json ledger math md2deck organism os pathlib
# pattern_check plan_state random re shlex shutil string subprocess sys tempfile time visual_page

grep -rhoE '^(import|from) +[a-zA-Z_][a-zA-Z0-9_]*' plugins/*/hooks/*.py | awk '{print $2}' | sort -u
# hashlib json os pathlib re shutil subprocess sys time
```

Tudo é stdlib ou módulo-irmão do próprio plugin (`askq_lint`, `branch_state`, `cobertura`, `doc_lint`, `graph_map`, `journal`, `ledger`, `md2deck`, `organism`, `pattern_check`, `plan_state`, `visual_page`). ⚠️ **`cobertura` entrou nesta rodada e o import dele é LOCAL, dentro da função** (`plan_state.py:_requisitos_do_projeto` e `cmd_cobertura` fazem `import cobertura` no corpo, não no topo) — os dois moram na mesma pasta, e o import no topo obrigaria quem só usa `tick` a carregar o módulo do fio. **Por quê:** o plugin é copiado pro cache sem passo de instalação — não existe onde rodar `pip install`. `doc_lint.py` carrega isso na docstring (*"Stdlib-puro."*), `conformance.py` repete no topo (*"Python 3 stdlib apenas — convencao do repo (patterns.md)"*), `askq_lint.py` explica a consequência (*"o plugin é copiado pro cache sem passo de instalação, não existe onde rodar pip install"*), e `visual_page.py`/`md2deck.py` fecham com *"stdlib only (requisito do repo)"* [confirmado, os cinco arquivos].

### 2.2 Fail-open também vale no Python: "não sei" ≠ "zero"

O padrão mais sutil do repo. Exemplos literais de `plugins/project-doc/lib/doc_lint.py` [confirmado]:

- `_git_ls_files` devolve **`None`** (≠ `[]`) quando o git não responde: *"com [] o lint concluiria 'nada existe no repo' e acusaria TODO token e TODO ponteiro. None faz os checks 1 e 3 se calarem."*
- `_commit_batch_check` só conta a consulta como válida se o git respondeu **uma linha por token**; sem isso devolve `{t: True for t in toks}` — *"um lint tem que falhar-ABERTO, nunca acusar por erro de ambiente"*.
- `_nlines` devolve `None` em erro de I/O — *"'não sei' NÃO pode virar 0 e fabricar 'ponteiro morto: tem 0 linhas'"*.
- `_load_allowlist` usa `errors="replace"` porque *"arquivo salvo em latin-1 levantaria UnicodeDecodeError (que é ValueError, não OSError) e derrubaria o lint inteiro"*.

O mesmo em `pattern_check.py:scope_staleness`: sem `.git`, sem `generated:`, sem `scope:` ou com git mudo, o retorno fica em `unknown` — nunca `fresh` [confirmado, quatro `return res` distintos com esse comentário].

E em `conformance.py:main`, a versão do padrão para um relatório inteiro [confirmado]:

```python
for fn in CHECAGENS:
    try:
        fn(rep, cfg)
    except Exception as e:  # uma checagem quebrada nunca derruba o relatorio
        rep.desvio("interno", f"a checagem {fn.__name__} falhou", repr(e), ...)
```

### 2.3 CLI de lib: `--json` + exit code como veredito

Forma repetida [confirmado em `doc_lint.py:main`, `askq_lint.py:main`, `conformance.py:main`]: `argparse`, flag `--json`, saída humana por default, e **exit 1 quando há violação** (`return 1 if out["fails"] else 0` / `return 1 if viol else 0` / `return 1 if rep.desvios else 0`). Quem consome do shell precisa saber que `exit 1` é veredito, não crash — `doc-detect.sh:doc_out_of_pattern` comenta isso explicitamente: *"pattern_check.py exits 1 when out_of_pattern — that is not an error here; bail only if JSON is empty."*

### 2.4 Escapar é do programa, não do modelo

Duas libs geram HTML e as duas têm a mesma anatomia: escapa tudo, depois reabre um subconjunto **fechado** de markdown [confirmado].

```python
# plugins/visual/lib/visual_page.py
def _e(s):    return html.escape(str("" if s is None else s), quote=True)
def _rich(s): ...   # só `code` e **negrito**, sobre o texto JÁ escapado
```

`_e()` é o escape cru e `_rich()` é o único caminho por onde texto do spec vira HTML formatado. O motivo está na docstring: *"Existe pra o spec não precisar carregar tags HTML — se o modelo escrevesse HTML dentro do JSON, a gente teria trocado de sintaxe sem trocar de problema."* O `md2deck.py:inline` faz o par equivalente para o deck, com uma frase que é o contrato inteiro: *"Nada aqui cria ou remove palavra — é a mesma frase do .md com marcação."*

Corolário no `visual_page.py:extract_block`: bloco canônico é **extraído do template.html**, nunca redigitado — *"foi uma cópia redigitada em prosa que divergiu do template e produziu página sem `.live-indicator`"*.

### 2.5 Gate de duas camadas: valida nas duas pontas, bloqueia só pelo alvo

**Padrão novo nesta rodada**, nascido de um defeito medido. `plan_state.py` validava o plano só no `init`; quem editasse o arquivo à mão depois passava incólume. O comentário registra o resultado [confirmado, citação literal]:

> O validador passa a morder aqui: até 2026-08-01 ele só rodava no `init`, e por isso um `desc` de 356 chars sobreviveu num plano cujo teto é 140.

A correção **não** foi rodar o validador inteiro no `tick` e abortar em qualquer erro — isso congelaria o plano todo por causa de uma tarefa torta que ninguém está mexendo. A forma é esta [confirmado, `plan_state.py:cmd_tick`]:

```python
erros = erros_do_plano(plan)
do_alvo = [e for e in erros if _erro_e_do_no(e, plan, node_id)]
if do_alvo:
    raise PlanError("⛔ tick recusado: %s está fora do schema.…")
if erros:
    print("⚠️  %d defeito(s) em outras tarefas (não bloqueiam este tique):", file=sys.stderr)
```

As três propriedades que fazem o padrão fechar:

- **A validação roda nas duas portas de escrita** (`init` e `tick`). Gate que só mora na porta de entrada não protege arquivo que tem segunda porta.
- **O bloqueio exige evidência SOBRE O ALVO.** É o fail-open do §1.1 aplicado dentro do Python, com a direção segura escolhida por escopo em vez de por tipo de erro: *"bloquear precisa de evidência sobre o alvo"*. Defeito alheio vira aviso em stderr, cortado nos 3 primeiros.
- **Traduzir posição em identidade é parte do padrão, não detalhe.** `erros_do_plano` prefixa com `fase[i] passo[j]`, que são **posições**; `_erro_e_do_no()` existe só para casar essas posições com o `id` do nó ticado. Sem essa tradução não há como separar erro do alvo de erro alheio, e o gate volta a ser tudo-ou-nada.

**Régua durável: gate que valida no caminho de escrita tardio precisa dizer de QUEM é o defeito antes de decidir se bloqueia.** Bloquear por defeito alheio é como um arquivo com 154 tarefas fica impossível de tocar por causa da 37ª.

### 2.6 O dado é obrigatório; o LUGAR dele é opcional (cascata de fontes)

Também novo nesta rodada, e é o par do §2.5: o `requisito` virou campo obrigatório em tarefa nova, mas exigir também um *documento* de requisitos teria transformado a regra em bloqueio para todo projeto sem PRD — inclusive este repositório. A saída é uma cascata explícita [confirmado, `plan_state.py:_requisitos_do_projeto`]:

```
bloco `requisitos` no próprio plano  →  $PLAN_REQS  →  <raiz>/docs/PRD.md
                                    →  <raiz>/docs/REQUISITOS.md  →  {}
```

- **O mais específico vem primeiro**, e a docstring diz por quê: *"quem o declarou no plano quis aquele conjunto, não o do projeto inteiro"*.
- **O fim da cascata é `{}`, e `{}` não é erro.** *"Projeto sem documento de requisitos não é erro, é o caso comum"* — dicionário vazio **desliga** a checagem de citação órfã em vez de reprovar tudo. É a mesma escolha do §2.2: "não sei" ≠ "zero".
- **A checagem que o dicionário liga é dura.** Com requisitos conhecidos, tarefa que cita um id inexistente **recusa a gravação inteira** — não é aviso. O comentário traz a medida: *"7 de 154 itens de um plano real citaram artigo de lei sem ninguém nunca conferir se o artigo existia"*.
- **Quem calcula não guarda.** `cobertura.py` (79 linhas, arquivo novo) lê, cruza e devolve; a vista "épico › requisito › grupo › tarefa" é **derivada em toda leitura**, nunca gravada — mesmo princípio de `phase_status`, que deriva o estado da fase dos passos porque *"estado duplicado é estado que diverge"*.

**Régua durável: quando um campo passa a ser obrigatório, a fonte que o valida precisa de cascata com fundo vazio — senão a regra nova vira bloqueio para todo projeto que ainda não tem a estrutura que ela pressupõe.**

---

## 3 · Vendoring de `_shared/` (o único "build")

Claude Code isola plugins na instalação: só `plugins/<nome>/` vai pro cache, sem variável cross-plugin. Logo, **código compartilhado é COPIADO antes do commit** [confirmado, cabeçalho de `scripts/sync-shared.sh`].

- **Fonte-da-verdade:** `_shared/`. As cópias dentro dos plugins são derivadas.
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

  O comentário justifica o mapa explícito: *"consumidores diferentes vendoram arquivos diferentes"*.

- **Comandos:** `bash scripts/sync-shared.sh` copia; `--check` não copia e sai 1 listando `DRIFT: <dest> difere de _shared/<arquivo>`. Fonte ausente é **exit 2**, distinto de drift.
- **Estado neste run** [confirmado, executado]: `OK: cópias vendored idênticas a _shared/` (rc=0).

**Regra:** fix de código compartilhado **nasce em `_shared/`**, nunca na cópia. Editar a cópia e commitar é pego pelo check A do release-gate — editar `_shared/` e esquecer o sync também.

---

## 4 · Green-cache (`_shared/green-cache.sh`)

Registro de "a suite passou verde neste estado exato da árvore". Feito pra ser **sourced**, não executado. Semântica declarada como não-negociável no cabeçalho [confirmado, citação literal]:

- Fail-open na direção segura: qualquer erro → **MISS** → a suite roda.
- **Gate vermelho NUNCA grava.**
- Chave = tree-hash do git **incluindo untracked**, via index temporário — *"`git stash create` e `HEAD + diff` não servem: ignoram untracked → falso HIT"*.
- TTL 24h **por linha** (epoch gravado no registro, não mtime do arquivo — *"um mark novo no mesmo arquivo não pode ressuscitar registro vencido"*). Prune de arquivos com mais de 7 dias no `green_cache_mark`.

API (assinaturas literais do arquivo):

```bash
green_tree_hash  <root>                    # imprime o sha; exit 1 em erro
green_cache_check <root> [scope]           # exit 0 = HIT (scope ou 'full')
green_cache_mark  <root> <scope> <writer>  # TSV: scope\tepoch\tiso-ts\twriter
# scope: "full" ou "app:<nome>". "full" satisfaz qualquer consulta.
```

O tree-hash não toca index nem working tree: `GIT_INDEX_FILE` aponta pra um `mktemp`, `read-tree HEAD` + `add -A` + `write-tree`. E `_green_cache_file` chaveia por `(projeto × árvore)` — `cksum` da raiz + tree-hash [confirmado].

Consumidores declarados no próprio cabeçalho: *"Fase Gate do qa-loop (grava), ship §2.5 (consulta+grava), hook `pre-deploy-test-check.sh` do ship (consulta+grava)"*, mais as duas cópias vendoradas do §3 [confirmado].

---

## 5 · Release

### 5.1 As regras

1. **Bump da `version` em `plugins/<nome>/.claude-plugin/plugin.json` em TODA mudança.** É a chave de propagação [relatado — comportamento do harness, não reproduzido nesta rodada].
2. **Espelhe a `version` em `.claude-plugin/marketplace.json`.** As duas têm que bater — cobrado pelo check B.
3. **`claude plugin validate .` antes de publicar.**
4. **Rode as suites do plugin tocado** (§6) — os checks D e F do release-gate fazem isso no commit.
5. **Plugin novo entra em TRÊS arquivos**: `plugin.json`, `marketplace.json` e `plugins/bootstrap/config/manifest.json`. Catálogo diz *o que existe pra instalar*; receita diz *o que a máquina instala*. Quem cobra é `conformance.py:check_catalogo` [confirmado, li a função], **não** o `release-gate.sh` — então o commit **passa** com a receita desatualizada e o desvio só aparece no próximo `bootstrap:setup`. A docstring nomeia o modo de falha: *"Plugin que entra no catalogo e nao entra na receita nunca chega em maquina nenhuma — e ninguem descobre, porque nada mais compara os dois lados."*

**Estado do catálogo neste run** [confirmado — derivado com `python3` sobre `.claude-plugin/marketplace.json` e sobre os 19 `plugin.json`]: **19** entradas em `plugins`, e o espelho do check B **fecha nas 19** — nenhuma diverge. Dos 19, apenas `grill-me` e `grill-with-docs` trazem chave `author`, e nas duas ela é **objeto**, a forma que o `validate` aceita.

Duas versões subiram nesta rodada, e elas são exatamente os dois plugins tocados:

```
visual         1.8.6 → 1.9.1      (o fio requisito↔tarefa, a vista de valor, o motor de decisão)
intent-guard   0.5.4 → 0.6.0      (a contagem de furos da régua de forma)
```

As demais seguem onde estavam: `archify` 2.11.0 · `bootstrap` 1.8.5 · `branches` 1.0.2 · `context-guard` 1.3.3 · `fallow` 1.0.7 · `graphify-guard` 1.1.4 · `grill-me` 1.0.0 · `grill-with-docs` 1.0.0 · `guardrails` 1.5.2 · `handoff` 1.8.5 · `improve` 1.0.3 · `principles` 1.0.2 · `project-doc` 3.18.4 · `qa-loop` 1.7.2 · `ship` 1.3.9 · `slides` 1.3.2 · `sovai` 1.8.2.

⚠️ **O salto do `visual` foi de 1.8.6 para 1.9.1 — cinco bumps, não um.** É o que a regra 1 produz quando o trabalho sai em vários commits (`git log --oneline` mostra 5 commits do `visual` nesta rodada): **a `version` acompanha o COMMIT, não a entrega.** Quem lê o catálogo procurando "o que mudou" não acha a resposta no número; acha no diff.

### 5.2 O gate mecânico de commit

`.claude/hooks/release-gate.sh`, registrado em `.claude/settings.json` como `PreToolUse` com `matcher: "Bash"` e `timeout: 60`, apontando para `$CLAUDE_PROJECT_DIR/.claude/hooks/release-gate.sh` [confirmado — li o settings.json inteiro; é o **único** hook declarado lá]. <!-- lint:ignore CLAUDE_PROJECT_DIR -->

**Dependência invertida:** ao contrário dos hooks de plugin, que assumem `jq`, o release-gate **não usa `jq` uma vez sequer** — faz todo o parse com `python3 -c` [confirmado: `grep -c jq` → 0; `grep -c python3` → 9]. Sem `python3`, ele cai no fail-open de infra e não checa nada.

**Como decide o que olhar** [confirmado, copiado literal]:

```bash
printf '%s' "$CMD" | grep -qE '(^|[;&|]|&&)[[:space:]]*git[[:space:]]+.*commit' || exit 0
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -f "$ROOT/.claude-plugin/marketplace.json" ] || exit 0   # não é este monorepo
FILES=$( { git -C "$ROOT" diff --cached --name-only
           git -C "$ROOT" diff --name-only; } 2>/dev/null | sort -u )
```

Untracked **não** entra, e o comentário diz por quê: *"sem `git add` ele não é commitado — incluí-lo dava falso-positivo com estado de runtime"*.

**Os checks são OITO**, com as letras do próprio arquivo e nesta ordem de declaração: `A · B+C · D · E · G · H · F` [confirmado — li o arquivo inteiro nesta rodada]. A ordem de execução não importa: todos só acumulam em `VIOL`.

- **A · vendoring** — roda `scripts/sync-shared.sh --check`. Drift ⇒ `❌ VENDORING EM DRIFT`, mandando corrigir **na fonte** `_shared/<arquivo>`.
- **B · espelho `plugin.json` ↔ `marketplace.json`** — divergiu ⇒ `❌ ESPELHO QUEBRADO`, com as duas versões impressas.
- **C · bump esquecido** — compara com `git show HEAD:<manifesto>`. Iguais ⇒ `❌ BUMP ESQUECIDO — <nome> mudou mas version continua <v>`.
- **D · testes Python** — roda `plugins/<nome>/lib/test_*.py` dos plugins tocados. Vermelho ⇒ `❌ TESTE VERMELHO` com as últimas 15 linhas.
- **E · contrato dos hooks** — só quando o commit toca `plugins/*/hooks/`. Roda `python3 scripts/hook_contract.py --baseline .claude/hook-contract.baseline.json --fail-on high` e barra **o que piorou**. O comentário explica a escolha: *"Comparar com o baseline (e não exigir zero) é o que impede a regra de apodrecer"*.
- **G · gen defasado no marker do project-doc** — só quando o commit toca `plugins/project-doc/`. Lê `CURRENT_GEN` de `pattern_check.py` (hoje **"3.8"** [confirmado, li a constante]) e varre `plugins/project-doc/skills/` procurando `gen=X.Y` **dentro de comentário HTML**. Menção em prosa a um gen antigo **não** é violação — *"barrá-las ensinaria a ignorar o gate"*. Fail-open se `CURRENT_GEN` não resolver (`sys.exit(0)`).
- **H · dado pessoal em commit de repo público** — roda `python3 scripts/public_repo_check.py --staged`. Só olha o que **este** commit traz: *"dívida antiga não trava ninguém, mas ocorrência nova é barrada na porta"*. O comentário registra por que virou código: *"Regra em prosa não pega (o CLAUDE.md pedia isso e 368 ocorrências entraram assim mesmo)"*.
- **F · testes shell** — roda `plugins/<nome>/hooks/test_*.sh` dos plugins tocados.

⚠️ **D e F são por plugin TOCADO, não por repo.** Um commit que só mexe no `bootstrap` roda exatamente `plugins/bootstrap/lib/test_*.py` e `plugins/bootstrap/hooks/test_*.sh` e mais nada. **Plugin sem suíte não é plugin sem teste: é plugin cujos checks D e F estão desligados.**

Bloco de saída literal quando algo viola:

```
🚧 release-gate (pedro-plugins) BLOQUEOU o commit:
<violações>

Conserte e commite de novo. (Gate mecânico: .claude/hooks/release-gate.sh)
```

### 5.3 Contrato dos hooks — as 5 propriedades

Quem mede é `scripts/hook_contract.py`; quem cobra é o check E. As cinco propriedades, copiadas da docstring do medidor [confirmado]:

1. **canal de saída** — como o hook fala (bloqueia? informa? só loga?). Os três canais de bloqueio coexistem e **não** foram normalizados: `exit 2`, `permissionDecision:"deny"`, `decision:"block"` — *"Não normalizo: só meço."*
2. **cap anti-loop** — quem bloqueia tem teto de devoluções, e a chave do teto é **por sessão** (`SESSION_SCOPED`).
3. **kill-switch** — dá pra desligar sem editar o arquivo.
4. **binário fixo** — caminho absoluto de ferramenta (`/opt/homebrew/bin/…`) é achado de gravidade **high**: some fora do Mac com Homebrew e o hook cai no fail-open em silêncio.
5. **fail-open** — guarda a ausência das ferramentas que usa (`EXTERNAL_TOOLS = ("jq", "python3", "node", "graphify")`).

O próprio script se declara falível [confirmado, citação literal]: *"⚠️ **Isto é grep sofisticado, não verdade.** O script diz ONDE OLHAR."* E a escolha de calibração tem direção declarada: *"Detectar um cap que não existe é o erro CARO … Detectar de menos só gera um falso alarme que a conferência derruba."*

**Os kill-switches de hoje**, derivados mecanicamente (`grep -rhoE '\$\{[A-Z_]+_GATE:-[01]\}' plugins/*/hooks/*.sh | sort -u`) [confirmado]: `ASKQ_GATE`, `BRANCHES_GATE`, `DOC_AUTORAL_GATE`, `DOC_GUARD_GATE`, `GRAPHIFY_GATE`, `HANDOFF_GATE`, `LINT_GATE`, `ORGANISM_GATE`, `PLAN_DOC_GATE`, `SCOPE_COP_GATE`, `SHIP_GATE`, `VISUAL_GATE`. Os hooks Python usam a mesma ideia com outra grafia: `PROSE_CEILING=0` e `FORMA_RELATO=0`.

**O marcador que desarma um falso-positivo do medidor de colisão** [confirmado, costura verificada nos dois lados]: `conformance.py:check_hooks_duplicados` só conta como "disputante" o hook que **bloqueia**, e um script pode se declarar avisador com o comentário literal `# conformance: default-warn`. Hoje quem carrega a marca é `plugins/graphify-guard/hooks/pretooluse-graphify-guard.sh` (*"o caminho de deny existe, mas só com GRAPHIFY_DENY=1"*), e `plugins/graphify-guard/hooks/test_graphify_guard.sh` testa a presença dela [confirmado, os dois lados existem hoje].

**Estado do contrato neste run** [confirmado, executado]:

```
python3 scripts/hook_contract.py --baseline .claude/hook-contract.baseline.json --fail-on high
# Contrato dos hooks — 34 registros, 33 scripts distintos
# Nenhum achado. Todos os hooks batem com o contrato.   (rc=0)
```

Sem baseline há **3** achados vivos, todos já congelados no retrato: `R1-cap-ausente` em `ship/pre-deploy-test-check.sh`, e `R5-sem-failopen` em `bootstrap/session-sync.sh` (jq) e `project-doc/sessionstart-doc.sh` (python3) [confirmado, `--json` desta rodada].

### 5.4 O ponto cego atual: o medidor só entende SHELL

🔴 **Os dois hooks Python de `Stop` são medidos como se não tivessem nada** [confirmado — `python3 scripts/hook_contract.py --json` desta rodada]:

```json
{"plugin":"bootstrap","event":"Stop","command":"python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/stop-prose-ceiling.py\"",
 "measure":{"lines":257,"blocking":{},"informing":{},"cap":{"counter":[],"sentinel":[],"session_scoped":false},
            "killswitch":[],"tools_used":[],"tools_unguarded":[]}}
```

O `resolve_script` **acha** o arquivo (o regex aceita o comando com o interpretador na frente), mas todos os padrões de `measure` são shell-shaped — `BLOCK_PATTERNS` procura `^\s*exit\s+2`, `CAP_COUNTER` procura `-ge …]`, `KILL_PATTERNS` procura `${X:-1}" = "0` [confirmado, li as constantes]. Os dois hooks bloqueiam (`sys.exit(2)` via `sair(msg, 2)`), têm cap (`MAX_BLOQUEIOS = 2`) e têm kill-switch — e **nada disso é visto**. Consequência: um hook `.py` novo que bloqueie sem teto passaria pelo check E sem um achado sequer. É medição ausente, não conformidade.

**O contrapeso que existe hoje é o `conformance.py`, e ele mede EXECUÇÃO, não código** — três checagens em cadeia [confirmado, li as três]:

- `check_teto_rodou` — lê `CLAUDE_DIR/state/prose-ceiling/batidas.log`. Ausente ⇒ desvio *"o guarda de prosa nunca executou"*; mais de 24h sem batida ⇒ desvio *"está mudo há N h"*. A docstring nomeia o defeito que motivou: *"Como so existia log de BLOQUEIO, 'nao rodou' e 'rodou e aprovou' eram indistinguiveis, e esta checagem chegou a carimbar 'nenhuma resposta furou o teto' com o guarda mudo."*
- `check_juiz_rodou` — **novo nesta rodada**, lê `CLAUDE_DIR/state/forma-relato/batidas.log`. Além do "nunca executou" e do "mudo há N h", ele tem um terceiro caso que é próprio do juiz: se as batidas com motivo `juiz sem resposta` superarem as `julgou`, vira desvio — *"fail-open aprovou tudo nessas vezes. Causa comum e credencial: `claude -p` sai com rc=1 e 'Not logged in'."* O conserto sugerido aponta pro `hooks.json`, não pro código: *"confira se stop-forma-relato.py esta no array Stop … hook fora dele e ignorado em silencio, e `claude plugin validate` passa mesmo assim."*
- `check_bypass_teto` — lê `bypass.log` e transforma "o hook desistiu" em número visível.

As três só cobram de quem tem o `bootstrap` habilitado (`if not any(ref.startswith("bootstrap@") and lig …): return`) — *"numa maquina sem o bootstrap ligado nao ha guarda pra rodar, e acusar ali seria desvio inventado"* [confirmado].

**Régua durável: guarda instalado que não EXECUTA é pior que guarda desligado — parece protegido.** Por isso `batida()` registra **toda** execução, não só as que barram [confirmado, docstring de `stop-prose-ceiling.py:batida`].

⚠️ **Limite conhecido do `check_juiz_rodou`, medido nesta rodada** [confirmado — contei os motivos do `~/.claude/state/forma-relato/batidas.log` da máquina]: as **12** batidas existentes têm todas o motivo `sem texto`; `julgou` = 0 e `juiz sem resposta` = 0. Com `mudo (0) > julgou (0)` falso e a última batida recente, a checagem carimba **`juiz de forma ativo`** — um juiz que nunca chegou a julgar em produção passa como conforme. O log de prosa da mesma máquina mostra o padrão análogo (`aprovou` 7 · `sem texto do assistente` 43, `bypass.log` inexistente). O sintoma é real e o caminho de investigação é `ultima_msg_assistente` devolvendo `None` no `Stop` real; a suíte, que monta transcript sintético, julga normalmente.

### 5.5 O juiz de forma: quando vale chamar modelo dentro de um hook

`plugins/bootstrap/hooks/stop-forma-relato.py` é o primeiro hook do repo que **paga token por turno**, e a docstring dele é o critério de quando isso se justifica [confirmado, citação literal]:

> Divisao de trabalho com o stop-prose-ceiling.py, que e vizinho e deliberadamente diferente: aquele e mecanico, roda em todo turno e custa zero token; este chama um modelo, entao SO roda quando a resposta e um RELATO. Nenhum padrao distingue "6 linhas densas" de "6 linhas vazias" — para isso precisa de um leitor.

As decisões que fazem o desenho fechar:

- **O gatilho é medido no próprio texto, não configurado** — `e_relato()` exige *"prosa suficiente E prova colada"*: pelo menos um bloco ``` e `MIN_PROSA = 2` linhas de prosa fora dele. O comentário registra a calibração: *"Exigir 4 de prosa deixava passar exatamente os relatos que dao certo."*
- **O anti-loop vem ANTES do gasto** — o contador é consultado antes de `julga()`, com o comentário *"anti-loop antes de gastar o modelo"*.
- **Fail-open em tudo que não for reprovação explícita** — `julga()` devolve `(True, motivo)` para `claude` ausente no PATH, timeout, `returncode != 0`, saída vazia e veredito ilegível.
- **O modelo é barato e trocável** — `FORMA_RELATO_MODEL`, default `haiku`; `TIMEOUT_S = 25`; o prompt corta a entrada em `texto[:6000]`.
- **O contrato de resposta é de uma linha só** — `PASSA` ou `REPROVA: <defeito em até 12 palavras>`, e o parser lê **só a primeira linha**.

Wiring [confirmado — li `plugins/bootstrap/hooks/hooks.json`]: os dois hooks estão no mesmo array `Stop`, na ordem prosa → juiz, com `timeout` 10 e 30:

```json
"Stop": [{"hooks": [
  {"type":"command","command":"python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/stop-prose-ceiling.py\"","timeout":10},
  {"type":"command","command":"python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/stop-forma-relato.py\"","timeout":30}
]}]
```

Ativação também confirmada no disco: `~/.claude/state/forma-relato/batidas.log` e `~/.claude/state/prose-ceiling/batidas.log` existem e têm escrita recente nesta máquina [confirmado].

### 5.6 A regra nova do teto de prosa: pergunta fechada exige veredito na 1ª linha

`stop-prose-ceiling.py` cobra quatro coisas hoje [confirmado, li `main()`]: teto de linhas (`TETO_PADRAO = 6`, ajustável por `PROSE_CEILING_MAX`, **nunca desligável** por ela), retórica no meio (`RETORICA`), menu de opções no fim, e — **novo nesta rodada** — veredito na primeira linha quando a última pergunta do usuário foi fechada.

O mecanismo são três regex com papéis distintos [confirmado, copiados do arquivo]:

- `PERGUNTA_FECHADA` — casada **no fim** do texto do usuário (`cauda = pergunta[-200:]`), porque o que decide é a última coisa perguntada.
- `PERGUNTA_ABERTA` — **exclusão** obrigatória: *"Pronome interrogativo abre pergunta ABERTA — 'como faz pra funcionar?' pede explicacao, nao sim/nao. Sem esta exclusao o guarda cobrava veredito de tudo."*
- `ABRE_COM_VEREDITO` — o que salva a resposta: `sim|nao|confirmo|nenhum|zero|passou|falhou|…|confirmado|inferido|depende`, ancorado em `^`.

A origem é caso real, registrada no comentário: *"a resposta trouxe a varredura inteira, com prova, e nao dizia sim nem nao — e a devolutiva foi 'voce nao me respondeu'."*

⚠️ **A régua exige o teste do lado que ela não pode pegar**, e aqui isso virou desenho de suíte [confirmado — `test_bootstrap_hooks.sh`, comentário literal]: as 4 perguntas abertas do teste *"tambem disparam a fechada de proposito: so passam se a exclusao de pergunta aberta estiver viva. Sem isso o caso passaria por nao casar nada."* [confirmado — suíte verde nesta rodada: `36 ok · 0 FAIL`].

`ultima_pergunta_usuario` também filtra o que **não** é pergunta: *"resultado de ferramenta e lembrete do sistema entram como 'user' e nao sao pergunta"* — descarta texto com `<system-reminder>` ou que comece com `<`.

---

## 6 · Testing

Não há runner nem CI: cada suite é um arquivo executável, stdlib/bash puro, que sai 0 quando verde.

Contagem de arquivos neste run [confirmado, `ls … | wc -l`]:

```bash
ls plugins/*/lib/test_*.py scripts/test_*.py | wc -l   # → 14
ls plugins/*/hooks/test_*.sh                 | wc -l   # → 15
```

⚠️ As duas de `scripts/` (`test_hook_contract.py`, `test_public_repo_check.py`) ficam **fora** de `plugins/`, logo fora do check D do gate.

Suites executadas nesta rodada, com o número que cada uma imprime [confirmado, todas verdes]:

- `plugins/bootstrap/lib/test_conformance.py` — `59 ok · 0 FAIL`
- `plugins/bootstrap/hooks/test_bootstrap_hooks.sh` — `36 ok · 0 FAIL`
- `plugins/project-doc/hooks/test_plan_gate.sh` — `49 passou · 0 falhou`
- `plugins/project-doc/lib/test_pattern_check.py` — `TODOS OS 84 CHECKS PASSARAM`
- `plugins/project-doc/lib/test_doc_lint.py` — `TODOS OS 35 CHECKS PASSARAM`
- `plugins/guardrails/lib/test_askq_lint.py` — `47 passou · 0 falhou`
- `plugins/guardrails/hooks/test_scope_cop.sh` — `15 passou · 0 falhou`
- `plugins/ship/hooks/test_pre_deploy.sh` — `100 ok, 0 falhas`
- `plugins/visual/lib/test_visual_page.py` — `60 passou · 0 falhou`
- `plugins/slides/lib/test_md2deck.py` — `50 passou · 0 falhou`

⚠️ `plugins/guardrails/hooks/test_setup_skill.sh` leva minutos — é a única do repo que não roda em segundos; não foi executada nesta rodada.

Rodar tudo:

```bash
for t in plugins/*/lib/test_*.py scripts/test_*.py; do python3 "$t" || echo "RED: $t"; done
for t in plugins/*/hooks/test_*.sh;               do bash    "$t" || echo "RED: $t"; done
```

**Cinco disciplinas de teste que este repo cobra**, todas com o sítio que as prova:

- **Teste E2E não-tautológico.** R9/R10 de `test_plan_gate.sh` escrevem o sentinel **rodando o hook escritor de verdade**, nunca recalculando a chave à mão — *"Recalcular a chave à mão aqui foi exatamente o que mascarou o bug de path na 1ª rodada."*
- **Par escritor↔leitor precisa de um teste que rode OS DOIS programas.** `test_conformance.py` roda o hook com `CLAUDE_CONFIG_DIR` num `mktemp`, exige que o log nasça **dentro** dele e só então roda o `conformance.py` [confirmado — a suíte tem função dedicada ao juiz, `teste_juiz_de_forma_mudo`, com os quatro casos: nunca executou · fail-open por juiz sem resposta · parado há mais de 24h · não cobra de quem não instalou o bootstrap].
- **Sabotagem da allowlist.** `test_askq_lint.py` esvazia `NOMES_PROPRIOS` e reafirma que aí *"GitHub"* barra — um caso "GitHub passa" sozinho seria satisfeito também por uma régua quebrada que não pega nada.
- **Verde por fail-open não conta como verde.** `test_bootstrap_hooks.sh` não aceita o exit code do juiz sem conferir o motivo no log: `grep -q '"motivo": "julgou"'` — *"fail-open por juiz mudo aprova tudo: so vale como verde se ele REALMENTE julgou"* [confirmado, citação literal].
- **Teste de hook de detecção precisa distinguir os dois `exit 0`.** No gate do ship, "não detectou deploy" e "detectou e a suíte passou" são ambos 0; a suíte resolve com um fixture cujo alvo de teste falha de propósito, e aí o exit code responde uma pergunta só.

---

## 7 · Gotchas

### Hooks & plugins

- ⚠️ **Hook de plugin vai em `hooks/hooks.json` (subpasta), NUNCA na raiz.** Na raiz é ignorado em silêncio e `validate` passa mesmo assim — o `conformance.py:check_juiz_rodou` repete o aviso no texto do conserto [confirmado].
- ⚠️ **Hook novo não entra na sessão em curso.** `stop-prose-ceiling.py` registra o teto no topo: *"como todo hook de plugin, so carrega no SessionStart, entao sessao ja aberta no momento da instalacao fica descoberta ate o proximo /clear"* [confirmado].
- ⚠️ **`exit 0` + stderr é mudo em PreToolUse/PostToolUse.** Use JSON no stdout (§1.2).
- ⚠️ **Estado global entre sessões é bug, não simplificação.** Já mordeu o context-guard e o scope-cop; os dois consertos são o mesmo (§1.5).
- ⚠️ **Nunca canonicalize path na chave de um sentinel** (§1.6).

### Regex de detecção em hook de gate

- Fronteira de palavra antes de todo verbo, senão constatação vira ordem (§1.7).
- Âncora de posição-de-comando, senão menção em `git commit -m "…"` dispara o gate (§1.8).
- Prefixo de lançador **enumerado**, nunca "qualquer palavra antes" — senão a âncora deixa de existir.
- Toda liberação precisa de revogação (`--com-doc` no plan-escape).

### Release

- ⚠️ **Bump em toda mudança e espelho no marketplace** — o gate avalia **staged ∪ tracked-modificados**, então mudança solta em OUTRO plugin bloqueia o seu commit [confirmado, `FILES` do release-gate].
- ⚠️ **Plugin novo entra em três arquivos** — e quem cobra o terceiro é o `conformance.py`, depois do commit (§5.1).
- ⚠️ **`author` tem que ser objeto** no `marketplace.json`; string é rejeitada pelo `validate` [relatado; o estado atual é consistente — os dois `author` presentes hoje são objeto, verificado neste run].

### Código compartilhado

- ⚠️ **Editar `_shared/` sem rodar `scripts/sync-shared.sh`** deixa as 6 cópias vendoradas defasadas. Fix nasce em `_shared/`, nunca na cópia.

### project-doc

- ⚠️ **`CURRENT_GEN` e os markers das skills andam juntos** — o check G existe porque o checklist manual já falhou uma vez.
- ⚠️ **Doc sem `generated:` ou sem `scope:` é `unknown`, não `fresh`** (§2.2).
- ⚠️ **Ler `verified-by:` usa o MESMO `_scope_entries(field="verified-by")`** — a docstring é explícita sobre o motivo: *"sem isso o consumidor teria que reimplementar o split + fallback de módulo, e é reimplementação de função barata que deriva em silêncio"* [confirmado].

### Ambiente

- ⚠️ **`${CLAUDE_CONFIG_DIR:-$HOME/.claude}` é a raiz do estado**, nos dois lados de qualquer par escritor↔leitor (§1.4).
- ⚠️ **Hook que chama binário autenticado precisa de variável de estado própria pro teste** — senão o isolamento derruba a credencial e o gate "passa" por fail-open (§1.4).

---

## 8 · Fluxo de trabalho recomendado

```bash
# 1. mexeu em código compartilhado?
bash scripts/sync-shared.sh            # copia _shared/ -> plugins
bash scripts/sync-shared.sh --check    # confirma que não há drift

# 2. mexeu num plugin?
#    - bump plugins/<nome>/.claude-plugin/plugin.json
#    - espelhe em .claude-plugin/marketplace.json
#    - plugin NOVO: declare também em plugins/bootstrap/config/manifest.json

# 3. verifique antes de commitar
claude plugin validate .
python3 plugins/<nome>/lib/test_*.py
bash    plugins/<nome>/hooks/test_*.sh
python3 scripts/hook_contract.py --baseline .claude/hook-contract.baseline.json --fail-on high
python3 scripts/public_repo_check.py --staged

# 4. commit — o release-gate roda A–H sozinho e sai 2 se algo violar

# 5. hook novo? confirme que ele carregou (e lembre: só vale na PRÓXIMA sessão)
claude plugin details <nome>@pedro-plugins     # → "Hooks (N)"
python3 plugins/bootstrap/lib/conformance.py   # → desvios de máquina, inclusive guarda mudo
```
