---
generated: 2026-08-09
generated-commit: f45190d
project: pedro-plugins
scope:
  - .claude/hooks/release-gate.sh
  - .claude/settings.json
  - scripts/sync-shared.sh
  - _shared/green-cache.sh
  - plugins/project-skills/hooks/pretooluse-doc-guard.sh
  - plugins/project-skills/hooks/posttooluse-doc-read.sh
  - plugins/project-skills/hooks/doc-detect.sh
  - plugins/project-skills/hooks/lib-project-root.sh
  - plugins/project-skills/hooks/pretooluse-plan-gate.sh
  - plugins/project-skills/hooks/userpromptsubmit-plan-escape.sh
  - plugins/project-skills/hooks/test_plan_gate.sh
  - plugins/project-skills/lib/doc_lint.py
  - plugins/project-skills/lib/pattern_check.py
  - plugins/guardrails/lib/askq_lint.py
  - plugins/guardrails/hooks/scope-cop.sh
  - plugins/bootstrap/hooks/stop-prose-ceiling.py
  - plugins/bootstrap/hooks/stop-forma-relato.py
  - plugins/bootstrap/hooks/hooks.json
  - plugins/bootstrap/lib/conformance.py
  - plugins/context-guard/hooks/context-guard-writer.sh
  - plugins/ship/hooks/pre-deploy-test-check.sh
  - plugins/visual/lib/visual_page.py
  - plugins/project-skills/lib/plan_state.py
  - plugins/project-skills/lib/cobertura.py
  - _shared/regua-de-pergunta.md
  - _shared/contrato-familia.md
  - _shared/hook-json.sh
  - _shared/resolve-plugin.sh
  - _shared/sessionstart-deps.sh
  - scripts/desacoplamento_check.py
  - scripts/fiscal_de_bancada.py
  - scripts/vazamento_check.py
  - scripts/plano_vs_codigo.py
  - scripts/readme_counts_check.py
  - scripts/suites_orfas.py
  - plugins/visual/hooks/pre-exitplan-visualize.sh
  - plugins/handoff/skills/handoff/SKILL.md
  - plugins/slides/lib/md2deck.py
  - scripts/hook_contract.py
  - .claude-plugin/marketplace.json
verified-by:
  - plugins/bootstrap/lib/test_conformance.py
  - plugins/bootstrap/hooks/test_bootstrap_hooks.sh
  - plugins/project-skills/lib/test_doc_lint.py
  - plugins/project-skills/lib/test_pattern_check.py
  - plugins/guardrails/lib/test_askq_lint.py
  - plugins/guardrails/hooks/test_scope_cop.sh
  - plugins/graphify-guard/hooks/test_graphify_guard.sh
  - plugins/guardrails/hooks/test_setup_skill.sh
  - plugins/ship/hooks/test_pre_deploy.sh
  - plugins/visual/lib/test_visual_page.py
  - plugins/project-skills/lib/test_plan_state.py
  - plugins/project-skills/lib/test_cobertura.py
  - plugins/visual/hooks/test_exitplan_gate.sh
  - plugins/handoff/lib/test_handoff_skill.py
  - .claude/hooks/test_release_gate.sh
  - plugins/slides/lib/test_md2deck.py
doc-sig: pedro-plugins/release-gate.sh@gen=3.8#19f52e0c
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
# a contagem sai deste comando, nunca de um número escrito aqui — ela sobe a cada plugin
# novo e a cada fusão que muda hook de casa
```

Arquivos que **declaram** a regra no cabeçalho, entre eles [confirmado]:

- `.claude/hooks/release-gate.sh` — *"FAIL-OPEN em erro de infra (sem git/python3, fora do repo): só bloqueia com evidência concreta na mão."*
- `plugins/project-skills/hooks/doc-detect.sh` — *"Fail-open: any error → no output, exit 0. Never blocks the caller."*
- `plugins/project-skills/hooks/posttooluse-doc-read.sh` — *"Fail-open: any error → exit 0. Never blocks."*
- `plugins/ship/hooks/pre-deploy-test-check.sh` — `command -v jq >/dev/null 2>&1 || exit 0`, com o comentário *"(marketplace convention)"*
- `_shared/green-cache.sh` — *"Fail-open na direção SEGURA: qualquer erro → MISS → a suite roda."*
- `plugins/bootstrap/hooks/stop-forma-relato.py` — *"FAIL-OPEN em tudo que nao for reprovacao explicita … Guarda que trava a sessao por infra e pior que guarda nenhum."*

**A direção segura muda por gate** [confirmado]:

- `green-cache.sh` → o lado seguro é **MISS** (roda a suite de novo), nunca HIT.
- `doc-detect.sh:doc_staleness` → o ternário é `fresh|stale|unknown`, e a borda de erro cai em **`unknown`** (fail-LOUD). Fingir "fresco" é o único resultado proibido.
- `pretooluse-plan-gate.sh` → o fail-open cobre **só** a borda de infra (sem `jq`, sem raiz resolvível, `doc-detect.sh` ilegível). Determinar que *não há documentação* é evidência concreta ⇒ nega. A guarda `[ -r "$SCRIPT_DIR/doc-detect.sh" ] || exit 0` existe porque um `chmod 000` no helper fazia projeto documentado cair no caso "sem doc" — regressão coberta pelo caso R7 de `test_plan_gate.sh` [confirmado, suíte verde nesta rodada: 49 passou · 0 falhou].

⚠️ **Fail-open MUDO é o único proibido — e isso vale também para o hook que lê o payload com Python próprio, sem `jq` e sem a biblioteca comum.** Em 2026-08-09 três hooks que fazem a leitura assim (`plugins/intent-guard/hooks/capture-prompt.sh`, `plugins/handoff/hooks/handoff-completeness-gate.sh`, `plugins/handoff/hooks/sessionstart-ata.sh`) saíam calados quando faltava `python3`; hoje os três chamam `hj_avisa` do `hook-json.sh` antes de liberar — o que obrigou a vendorar a biblioteca também em `plugins/handoff/hooks/` [confirmado, `sed -n '/^SPECS=(/,/^)/p' scripts/sync-shared.sh | grep 'hook-json.sh'` traz a linha do handoff; `bash scripts/sync-shared.sh --check` → `OK: cópias vendored idênticas a _shared/`]. **Ter leitor próprio dispensa a biblioteca para LER, nunca para AVISAR** — quem cobra é `bash scripts/test_sem_jq.sh` (*"todo hook da classe B avisa quando não há leitor nenhum"*, verde nesta rodada).

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

- **`exit 2` + mensagem em stderr** — bloqueia de fato; o stderr volta pro modelo. Quem usa esse canal se descobre com o comando, nunca com a lista escrita aqui (as suítes entram no resultado porque exercitam o canal):

  ```bash
  grep -rln 'exit 2' plugins/*/hooks/*.sh .claude/hooks/*.sh
  ```
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

**Hooks Python existem, e hoje são CINCO** [confirmado — `find plugins -path '*/hooks/*' -type f -name '*.py' ! -name 'test_*'`]:

```
plugins/bootstrap/hooks/stop-forma-relato.py
plugins/bootstrap/hooks/stop-prose-ceiling.py
plugins/bootstrap/hooks/stop-regua-relato.py            ← novo em 2026-08-03
plugins/guardrails/hooks/pretooluse-artefato-regua.py   ← novo em 2026-08-03
plugins/visual/hooks/stop-anuncio-sem-acao.py
```

Quatro são de `Stop` e escrevem em stderr **só** no caminho que sai 2 — que num `Stop` é o canal que devolve o texto ao modelo. O quinto é `PreToolUse[Edit|Write]` e usa o canal estruturado (`permissionDecision:"deny"` no stdout), porque em `PreToolUse` stderr com `exit 0` é mudo. O uso está certo; o que quebra é a **auditoria** deles (§5.3).

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

**Terceira reincidência, 2026-08-03, e ela é o inverso das duas: o estado era COMPARTILHADO onde precisava ser por-sessão.** O resumo de fim de turno escolhia qual plano mostrar pela data de escrita do arquivo — e `mtime` diz que **alguém** mexeu, nunca **quem**. Com 6 sessões abertas no mesmo repositório, a vizinha marcando um passo empurrava o plano dela para o topo do fim de turno de todas. Foi relatado com print de produção **duas vezes** antes de virar código, e a primeira vez eu registrei o teto no comentário e adiei: *"o conserto de verdade é registrar QUAL plano esta sessão marcou — estado novo por sessão, que só se paga se o caso aparecer"*.

Três lições, e a terceira é a que dói:

1. **Atributo de arquivo nunca identifica autor.** `mtime`, tamanho, ordem no diretório — todos respondem "mudou", nenhum responde "quem mudou". Quando a pergunta é de autoria, quem escreve tem que assinar: aqui, `save()` grava o id do plano num sentinel chaveado pela sessão que o escreveu.
2. **A assinatura vai no ponto de escrita COMUM, não em cada comando.** A marca mora em `save()`, por onde `tick`, `state`, `init` e `close` já passam — pendurar em cada verbo deixaria o próximo verbo novo de fora, em silêncio.
3. **Com o id da sessão em mãos, ausência de marca também é informação.** Não é "não sei": é "nada liga esta sessão a estes planos", e a saída honesta é relatar em vez de afirmar. Foi isso que separou o cabeçalho `📍 Onde estamos` (afirma) do `📋 Plano aberto no projeto` (relata).

**O ponto de escrita comum também é onde o CAMPO AUSENTE vira valor** — segunda aplicação da lição 2, medida em 2026-08-09. Tarefa de plano gravada sem `status` some das contagens: não é feita, não é pendente, e a soma por fora erra — **duas tarefas sem o campo fizeram 218 virar 217**. O conserto não foi validar na entrada de cada verbo; foi `plan_state.py:save()` fazer `it.setdefault("status", "todo")` **antes** de escrever, varrendo `phases[].items[]`. O comentário registra a razão de morar ali: *"Toda escrita passa por aqui, então a normalização mora aqui: o campo ausente vira `todo` ANTES de ir ao disco, não importa quem esqueceu."* [confirmado, li a função]

**Régua durável: dado que a contagem lê precisa de valor no disco, não de default no leitor.** Default no leitor é um por leitor — e o próximo leitor conta diferente do anterior, sem nada ficar vermelho.

**Régua que sai daqui: `ponytail:` que adia um conserto tem que nomear o SINTOMA que autoriza pagá-lo.** O comentário dizia "se o caso aparecer" sem dizer como o caso se pareceria — então ele apareceu duas vezes antes de alguém reconhecer. Escreva o gatilho observável: *"se o resumo mostrar a frente de outra sessão, pague isto"*.

### 1.5a Canal de saída manda na FORMA — e `systemMessage` é texto puro

**Novo em 2026-08-03**, relatado com print de produção. O `systemMessage`/`reason` de hook chega **literal** no terminal: `**negrito**` e `` `crase` `` não renderizam, viram ruído na tela. Três emissores escreviam markdown ali — o resumo de plano, a cobrança do tique e o aviso de push de branch —, e o dono leu `• **Feito:** 0 de 32 passos` na tela `[confirmado]`.

O que substitui, sem perder o destaque:

| markdown que não renderiza | o que dá o mesmo destaque |
|---|---|
| `**Título**` | posição (1ª linha) + emoji de estado |
| `**Rótulo:**` no bullet | emoji + `Rótulo:` — `✅ Feito` · `🔄 Agora` · `⬜ Falta` |
| `` `comando` `` | o comando cru |

⚠️ **Reuse o vocabulário de emoji que o projeto já tem.** Os três acima são os mesmos do `MARK` da árvore de plano (`done ✅ · doing 🔄 · todo ⬜`), então quem lê a árvore já sabe ler o resumo. Emoji novo por bloco novo vira dialeto.

⚠️ **A exceção que confirma:** o `handoff-completeness-gate.sh` mantém `**Ação:**` e companhia — mas ali os `**` são o que ele **procura dentro de um arquivo `.md`**, e markdown em arquivo markdown é markdown. A régua é do canal de saída, não do texto em si.

⚠️ **Linha em branco de abertura é do CANAL.** O harness prefixa `Stop says: ` na primeira linha; sem duas linhas em branco na frente, o cabeçalho gruda no prefixo. Elas ficam no **hook**, nunca no gerador de texto — quem chama o gerador na mão não quer abertura vazia. Não custam orçamento: o medidor só conta linha com conteúdo.

**Régua que sai daqui: teste de artefato de leitura casa CONTEÚDO, nunca POSIÇÃO.** Sete checks do resumo liam `L[1]`, `L[2]`, `L[3]`, e quebraram **duas vezes no mesmo dia** sem que comportamento nenhum tivesse mudado — só porque o layout ganhou emoji e uma linha em branco. Um helper que acha o bullet pelo rótulo (`bullet(linhas, "Falta")`) mata a classe inteira. `[confirmado — `test_plan_state.py`]`

### 1.6 PHASH: a chave dos sentinels precisa nascer da MESMA string

**A armadilha mais cara do repo.** Sentinel em `/tmp` é chaveado por `(session_id × projeto)`, e o projeto entra como `cksum` da string da raiz:

```bash
# plugins/project-skills/hooks/lib-project-root.sh
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

### 1.6a A generalização do §1.6: regra que vale nos DOIS lados vira UMA função

O caso do `cksum` é o mais caro, mas não é o único — a família é **toda regra que dois pontos
do código precisam responder igual**. Quando a regra é copiada, os dois começam iguais e
divergem no primeiro conserto, e a divergência é silenciosa porque nenhum dos dois está
errado sozinho.

O segundo caso medido, em 2026-08-08 [confirmado]: a regra *"pendência com decisão gravada
não trava mais"* vivia em `plan_state.py:cmd_tick` (quem RECUSA o tique) e foi copiada para
`_detalhe` (quem DESENHA a linha de baixo do item). O `tick` aprendeu a olhar o campo
`decidido`; o renderizador continuou olhando só a `pendencia` — e a árvore passou a anunciar
**⛔ falta decidir** em três passos que estavam destravados desde o dia anterior. **A árvore é
o que o motor de execução contínua lê como fila**, então ele gastou o tier caro
diagnosticando por que passos com resposta gravada "não saíam do lugar".

Hoje a regra é `plan_state.py:pendencia_viva`, chamada pelos dois. A docstring dela carrega o
porquê, e a suíte varre a fronteira inteira (`decidido` ausente, texto, lista, dicionário
vazio, `escolha` nula, vazia, só espaço, preenchida) — **8 casos, porque o defeito estava
justamente numa borda**: `str(None)` devolve a palavra `"None"`, que é texto não-vazio, então
gravar "não escolhi" liberava o tique.

**O sinal de que você está criando o defeito:** você acabou de escrever, num segundo lugar,
uma condição que já existe no primeiro. Extraia antes de seguir — depois a divergência já
aconteceu e ninguém a vê.

⚠️ **Quando os dois lados falam LINGUAGENS diferentes, "uma função" é impossível — e aí a
costura é um teste que roda os DOIS programas.** É o caso da marca de documento, nascido em
2026-08-09: a receita (`cksum` POSIX do CORPO do arquivo, sem o frontmatter) vive em
`plugins/project-skills/hooks/lib-doc-mark.sh:doc_marca`, que é shell chamado por hook, e
precisou ser reimplementada em Python em `plugins/project-skills/lib/doc_load.py:cksum`,
que é o programa que decide o que vale como régua. Copiar a receita é exatamente o defeito
desta seção — o que impede a divergência é a asserção que calcula a marca pelos dois
caminhos e exige o mesmo número [confirmado, `plugins/project-skills/lib/test_doc_load.py`
roda `sh -c '. …/lib-doc-mark.sh && doc_marca …'` e compara com a saída do módulo Python;
`python3 plugins/project-skills/lib/test_doc_load.py` → `29 passou · 0 falhou` nesta rodada].
**Régua durável: reimplementação cross-linguagem só é legítima com o teste de identidade
junto** — sem ele, o que existe são duas receitas que ninguém sabe se ainda concordam.

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

- 🔴 **E aqui está o limite da âncora: prefixo enumerado só cobre o que alguém lembrou de enumerar.** O `release-gate.sh` usava a mesma ideia (`(^|[;&|]|&&)[[:space:]]*git[[:space:]]+.*commit`) e **quatro formas legítimas passavam caladas** — `env FOO=1 git commit`, `(git commit …)`, `bash -c "git commit …"` e `VAR=x git commit` — enquanto `git log --grep commit` disparava à toa. O conserto trocou o casamento de forma por **parse**: o comando é quebrado em tokens (o split inclui `(`, `)`, `;`, `&`, `|`, `<`, `>`, aspas e crase) e o subcomando do git é lido pulando as opções globais e os valores delas (§5.2). **Quando o alvo é um comando de verdade, tokenize e leia o subcomando; regex de forma é para texto, não para linha de comando.** [confirmado — `.claude/hooks/test_release_gate.sh` → `OK (30 checks)`, com um caso por forma]

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

### 1.11 Skill que se diz protegida por um guard: cheque o guard

**Novo em 2026-08-02**, e o defeito era invisível por construção. A skill do motor de execução contínua (hoje `plugins/project-skills/skills/sprint/SKILL.md`) afirmava, em prosa, que *"o guard `PreToolUse(Agent)` acorda a cada disparo"* — justificando por que a skill não precisava de mecanismo próprio contra descambar pra sub-agente. O guard existia mesmo, mas fazia o **oposto** [confirmado — `plugins/guardrails/hooks/hooks.json`, prompt do classificador, copiado literal]:

```
1. tem 'team_name'                         → ALLOW  (é Agent Teams)
2. sem team_name E prompt cita Agent Teams → DENY
3. tarefa one-off sem team_name            → ALLOW   ← o caso do motor
4. na dúvida                               → ALLOW
```

Ele foi escrito pra **proteger** Agent Teams de serem substituídos por sub-agente avulso. A regra 3 libera exatamente a forma pela qual o motor descambava.

Por que ninguém viu: **prosa que descreve mecanismo ausente não dá erro**. Não é ponteiro morto (o arquivo citado existe), não é classe CSS inexistente (o `doc_lint` pegaria), não é teste vermelho. É uma afirmação sobre comportamento, e a única forma de checá-la é ler o outro arquivo.

**Régua durável: toda vez que um documento dispensa mecanismo alegando que outro componente já cobre, abra o componente e leia a regra dele na mesma passada.** O custo é um `grep`; o custo de não fazer é uma proteção que só existe no texto. Corolário para quem escreve: cite o arquivo **e a regra**, não só o nome — "o guard `X` acorda" é inauditável; "a regra 3 de `X` libera one-off, então **não** cobre este caso" é.

Dois guards podem coexistir no mesmo matcher respondendo a perguntas opostas — é o caso de `Agent` hoje (§6 do `architecture.md`). Coexistir não é conflito; **presumir** que o do vizinho cobre o seu caso é.

**Sequela em 2026-08-02: o gate nasceu apoiado numa segunda afirmação não medida, e desta vez ela foi medida.** O hook declarava, no próprio cabeçalho, que era **INFERIDO** — não confirmado — que a tool `Workflow` não spawna os agentes dela por `PreToolUse[Agent]`. Se passasse, o gate mataria o motor que existe para proteger, numa missão longa com o dono ausente. Medição, com o sinal aceso: um Workflow de um agente **completou** (11 chamadas de ferramenta, 117s) e o contador `bloqueios-<sid>` **não se moveu**. `[confirmado]`

Duas lições, e a segunda vale mais que a primeira:

1. **Rotular INFERIDO no código funciona.** O comentário trazia o experimento escrito (*"com o sinal ligado, rode um Workflow de um agente só e veja se ele completa"*), então medir custou minutos em vez de arqueologia. Hipótese com o próprio teste ao lado é dívida que se paga; hipótese sem teste vira folclore.
2. **A medição não removeu o cap, e não deveria.** O cap de 3 negações cobre o runtime do `Workflow` mudar de caminho numa versão futura — risco que a medição de hoje não elimina, só data. Medir uma inferência autoriza **parar de temê-la agora**, nunca desmontar a rede que existe para quando ela mudar.

### 1.12 Motor de agentes: quem revisa precisa de âncora FORA do que foi construído

**Novo em 2026-08-02**, e vale para os dois motores do marketplace — hoje as skills `sprint` e `qa-loop`, ambas do `project-skills`. O revisor de construção do motor de execução contínua julgava a obra contra a **decomposição do próprio orquestrador**, declarado literal na skill até esta rodada: *"Trata a decomposição do #1 como **contrato** e só checa se ele foi **cumprido**"* + *"**Não julga se a decomposição é fiel ao plano-macro**"*.

**É circuito fechado: quem decompõe errado é aprovado errado.** A decomposição sai do mesmo motor que produz o código, então revisar contra ela mede coerência interna, nunca cumprimento. O sintoma no repo: 7 commits em 2026-08-02 sem plano nenhum, e nenhum revisor acusou — porque nenhum tinha a spec em mãos.

A correção tem três partes, e a ordem importa:

- **A spec vai ao revisor como vai ao decompositor.** O motor passa `planPath`/`planText` aos dois; a decomposição vira **meio**, não régua. Desvio de spec vira gap mesmo com a decomposição 100% cumprida.
- **Gap de spec e de rastreio não podem cair no filtro de severidade.** Os dois **nascem** em severidade ≥ floor e o script os segura mesmo se o revisor devolver abaixo — senão o gap sai da conta e passa calado. É lógica de script (`holdsBuild`), não memória do revisor.
- **A constituição é lida do projeto, nunca copiada pra dentro da skill.** O eixo abre `.claude/docs/quality-goals.md` do projeto onde a missão roda. Projeto sem o arquivo: o eixo não roda e **isso não é gap** — mesmo fundo-vazio do §2.6.

**Régua durável: revisor cuja única referência é o artefato do próprio motor não revisa, confere. Toda revisão precisa de pelo menos uma âncora que o motor não escreveu.**

### 1.13 Agente que morre não pode derrubar o motor

Corolário medido na mesma rodada. `agent()` devolve **`null`** quando o subagente morre por erro terminal (limite de sessão, erro de API após os retries) ou quando o usuário o pula. O esqueleto do motor lia `review.gaps` direto.

O resultado, com saída crua desta sessão:

```
Dynamic workflow failed: Error: null is not an object (evaluating 'review.gaps')
[exec:T8] failed: You've hit your session limit · resets 3:40pm
[exec:T9] failed · [exec:T10] failed · [revisar:r1] failed
agent_count 12 · agents_done 8 · agents_error 4
```

**8 de 12 agentes tinham entregue, e o motor devolveu falha total.** O trabalho existia em disco; o que se perdeu foi o relato dele.

As quatro portas, e a direção segura de cada uma [confirmado — o `SKILL.md` do motor, esqueleto]:

- **decompositor morto** → `break`. Sem decomposição não há o que executar; o que as rodadas anteriores construíram continua valendo.
- **revisor morto** → `continue` com blocker. A direção segura é **não** declarar `built`: revisor que não respondeu não aprovou nada.
- **confirm-pass morto** → `break` com blocker. É a única segunda checagem quando não há `/qa-loop` adiante; sem ele ninguém conferiu.
- **executor morto** → `.filter(Boolean)` **nos dois lados** (paralelo e sequencial). Filtrar só o paralelo deixava `null` entrar em `results` e estourar no revisor — e a tarefa **sumia do relato** em vez de reaparecer em `missingTasks`, que é o caminho que a manda de volta pro decompositor.

**Régua durável: em motor de agentes, toda chamada que pode devolver `null` precisa de porta declarada — e a porta nunca é "declara pronto". Falha de infra tem que degradar a missão, nunca fabricar aprovação.**

### 1.14 Componente que produz dado para OUTRO consumir sai de cena sem sintoma

Terceira variação do mesmo defeito nesta rodada, e a mais silenciosa das três. O §1.11 tratou de prosa que descreve mecanismo ausente; o §1.13, de agente que morre; este trata do elo que some de uma cadeia **sem quebrar nada visível**.

Medido em 2026-08-02: a `statusLine` desta máquina chamava o `claude-hud` direto, e o writer do `context-guard` estava fora da cadeia. Resultado [confirmado]:

```
único /tmp/claude-context-pct-* no disco:  claude-context-pct-smoke-123
mtime:                                     30/jul 22:22  ← fixture de TESTE
sessões reais que gravaram em 3 dias:      zero
context-guard@pedro-plugins:               enabled = True
```

**A barra de status continuou perfeita o tempo todo.** Quem sumiu foi o elo que grava dado para outro consumir — o guarda do context-guard, que sem esse arquivo simplesmente nunca dispara. Não há tela em branco, não há erro, não há log.

Como distinguir os dois tipos de elo, e por que importa:

- **Elo de saída visível** (renderizador): sumiu, você vê. O próprio uso é o teste.
- **Elo de efeito colateral** (escritor): sumiu, nada muda na tela. **Só um check que cruza "está habilitado" com "está na cadeia" pega.**

Três regras que caíram daí:

- **Cadeia se verifica inteira, nunca por um elo.** `check_statusline_meio_ligada` procura no `statusLine.command` **e** no `CLAUDE_STATUSLINE_FORWARD`: olhar só o comando acusaria o renderizador toda vez que ele fosse o forward, que é o arranjo normal.
- **Substituir um elo é mover o anterior, não sobrescrever.** O conserto pôs o comando antigo **inteiro** no forward — inclusive o cálculo de `COLUMNS`, que se perderia num forward remontado à mão.
- **Fixture de teste no mesmo diretório do estado real é armadilha.** O `smoke-123` de 30/jul fazia `ls /tmp/claude-context-pct-*` parecer saudável. Só o `mtime` e o nome denunciavam.

**Régua durável: componente cujo produto é consumido por terceiro precisa de check de PRESENÇA na cadeia — o uso normal não o testa, porque o uso normal não olha para o que ele produz.**

### 1.15 Componente que encolhe conteúdo tem que emitir a SAÍDA junto

Par do §1.14, do outro lado: lá o elo sumia sem sintoma, aqui o conteúdo fica visível mas **inalcançável**. Mesmo desenho de conserto — a garantia é do programa, não da lembrança de quem escreve.

O `.artefato` embute o artefato real num quadro pequeno, e pequeno é a escolha certa: em tamanho natural ele quebra a leitura do documento e empurra a decisão pra fora da tela. O que faltava não era tamanho, era **saída** — não havia como olhar de perto sem sair da página. Desde 2026-08-02 `r_artefato()` emite dois botões, e eles não são redundantes [confirmado — `visual_page.py`, `test_visual_page.py` com 11 checks]:

- **tela cheia** — ler agora **sem perder o lugar** no documento (`Esc` volta).
- **nova janela** — deixar aberto e **comparar** com o resto.

Três decisões de implementação, cada uma amarrada a um modo de falha concreto:

- **`<a target="_blank">`, nunca `window.open()`.** Bloqueador de popup mata o segundo e não o primeiro, e a página abre em `file://`, onde a política é mais restritiva ainda.
- **`.artefato:fullscreen` precisa de `background` próprio.** O navegador pinta branco por padrão em fullscreen; sem a regra, o tema escuro pisca na moldura ao redor.
- **Sem Fullscreen API, cai em abrir-em-aba.** Clique que não faz nada é pior que botão ausente — o usuário conclui que a página está quebrada.

Detalhe que decide o resto: **a moldura INTEIRA entra em fullscreen, não só o quadro.** Levando a barra junto, a procedência continua visível lá dentro e o caminho de volta fica na mão. Ampliar só o conteúdo tiraria da tela exatamente o que prova de onde ele veio.

**Régua durável: todo componente que encolhe conteúdo para caber no fluxo deve emitir a saída para vê-lo inteiro, e essa saída é parte do componente — não enfeite opcional de quem escreve o spec.**

### 1.16 Teto por unidade não é teto do conjunto

Quarta variação da mesma família nesta rodada. O resumo de fim de turno prometia *"1-3 bullets"* e entregava **3×N** [confirmado — `plan_state.py`]:

```
brief_lines()  → TETO DE 3 BULLETS ... por PLANO
cmd_brief()    → for plan in list_plans(): if active: blocks.append(...)
                 nenhum teto no NÚMERO de planos

medido: 4 planos ativos = 16 linhas.  Depois do conserto: 6.
```

Cada peça estava dentro do que prometia. **O conjunto é que não tinha dono** — e é a forma mais comum do defeito, porque cada autor confere o próprio limite e nenhum confere a soma.

O mesmo vale um nível acima: seis hooks disputam o `Stop`, cada um com o próprio teto, e `6/9 · 35s · 773 tokens` foi o que o dono viu. Daí nasceu `hook_contract.py --stop-budget` (ver `runtime.md §10a`), que não barra nada — **só torna a soma visível**, que era o que faltava.

Três regras que caíram daí:

- **Cortar não pode ser sumir.** O excedente vira contagem visível (*"⋯ e mais 3 plano(s) aberto(s)"*), nunca omissão. Trocar excesso de ruído por perda de informação é trocar um defeito por um pior.
- **Nem tudo no lote tem a mesma natureza.** O teto corta os planos **ativos**; a confirmação de plano **encerrado** fica fora, porque ela acontece uma vez e some — cortá-la engoliria o *"🏁 acabou"* que o hook existe pra dar. Esse caso reprovou na primeira versão e é por isso que os dois grupos viraram listas separadas.
- **Testar a função não é testar o caminho.** A primeira suíte chamava o cortador direto, e sabotar a chamada dentro do emissor deixava tudo verde. Só o E2E pelo comando real pegou.

**Régua durável: quando N unidades com teto próprio desembocam na mesma saída, o teto que importa é o da saída — e ele precisa de dono, de número e de um medidor que mostre a soma.**

### 1.17 PORTA e REDE: dois hooks para a mesma regra, porque nenhum alcança os dois canais

**Novo em 2026-08-03**, e não é redundância. A régua de forma (§2.7) passou a ser cobrada por **dois** hooks, e os cabeçalhos dos dois explicam por que um só deixaria metade descoberta [confirmado, citação literal de `pretooluse-artefato-regua.py`]:

> A rede pega o relatório que eu DIGITO no terminal e nunca vê arquivo; esta porta pega o arquivo e nunca vê o terminal.

- **PORTA — `plugins/guardrails/hooks/pretooluse-artefato-regua.py`** (`PreToolUse[Edit|Write]`). Nega escrever `.md`/`.html` dentro de `.claude/visual/` ou `.claude/reports/` quando o texto sai em prosa corrida. **Alcance deliberadamente estreito**: documentação, código e config ficam fora — *"a régua governa artefato de LEITURA, não todo texto do repositório"*. Kill-switch `ARTEFATO_REGUA=0`, impresso na própria mensagem de recusa. [confirmado — `test_artefato_regua.py` → `artefato-regua: 23 checks ok, 0 falhas`]
- **REDE — `plugins/bootstrap/hooks/stop-regua-relato.py`** (`Stop`). Mede os bullets do relato digitado na resposta. **Divisão de trabalho escrita no arquivo, pra não haver guarda em dobro**: `stop-prose-ceiling.py` cobra o **VOLUME** (quantas linhas), esta régua cobra os **BULLETS** (as linhas que abrem com `•`, `-` ou `*`). Cap `MAX_BLOQUEIOS = 2`, kill-switch `REGUA_RELATO=0`, estado em variável própria `REGUA_RELATO_STATE` (§1.4).

Duas decisões que valem copiar:

- **O perfil sai por DERIVAÇÃO, não por escolha.** A rede usa `pagina` — e o comentário dá o raciocínio: o `regua_texto.py` define esse perfil como *"pagina, relatorio, diagnostico"*, e relato de fim de turno é relatório. **Não** é o perfil `hook`, porque aquele proíbe `**` e crase por causa de um canal que não renderiza markdown, e **o canal do CLI renderiza**. Escolher perfil pelo *nome do hook* teria pego o errado.
- **Fora do alcance, em ambos: bloco de código.** Prova é literal por obrigação — `linhas_de_redacao()` na porta e a mesma exclusão na rede. Medir dentro de ``` reprovaria a saída crua que o artefato existe pra carregar.

🔴 **Gotcha medido nesta sessão: hook que EXISTE mas não está no `hooks.json` nunca dispara — e nada acusa.** O `stop-regua-relato.py` nasceu como arquivo antes de entrar no array `Stop` do `plugins/bootstrap/hooks/hooks.json`; os dois entraram no mesmo commit (`1e59b55`) só porque alguém foi conferir. Não há erro, não há log, `claude plugin validate` passa, e `claude plugin details` mostra `Hooks (N)` **contando EVENTOS, não scripts** — um `Stop` novo no array já povoado não mexe no N. É a mesma família do §1.14 (elo que sai da cadeia sem sintoma), com um agravante: aqui o componente nunca chegou a entrar. **Hook novo se prova pelo `hooks.json`, nunca pela existência do arquivo.**

## 2 · Python

### 2.1 Stdlib puro, sem exceção observada

Não há `requirements.txt`, lockfile nem venv no repo. Duas varreduras neste run, porque **existe Python em `hooks/` além de `lib/`**:

```bash
grep -rhoE '^(import|from) +[a-zA-Z_][a-zA-Z0-9_]*' plugins/*/lib/*.py _shared/*.py | awk '{print $2}' | sort -u
# argparse askq_lint branch_state cobertura collections contextlib datetime difflib doc_lint
# fcntl glob graph_map hashlib html io journal json ledger math md2deck organism os pathlib
# pattern_check plan_state random re regua_audit regua_texto report shlex shutil string
# subprocess sys tempfile textwrap time visual_page

grep -rhoE '^(import|from) +[a-zA-Z_][a-zA-Z0-9_]*' plugins/*/hooks/*.py | awk '{print $2}' | sort -u
# hashlib importlib io json os pathlib re shutil subprocess sys tempfile time
```

Tudo é stdlib ou módulo-irmão do próprio plugin (`askq_lint`, `branch_state`, `cobertura`, `doc_lint`, `graph_map`, `journal`, `ledger`, `md2deck`, `organism`, `pattern_check`, `plan_state`, `regua_audit`, `regua_texto`, `report`, `visual_page`). ⚠️ **`importlib` nos hooks é consequência do vendoring, não sofisticação**: `pretooluse-artefato-regua.py` carrega a régua por caminho (`importlib.util.spec_from_file_location` sobre `../lib/regua_texto.py`) porque um hook não tem o `lib/` do próprio plugin no `sys.path` — e se a cópia não estiver lá, ele sai 0 mudo (§1.17). ⚠️ **`cobertura` entrou nesta rodada e o import dele é LOCAL, dentro da função** (`plan_state.py:_requisitos_do_projeto` e `cmd_cobertura` fazem `import cobertura` no corpo, não no topo) — os dois moram na mesma pasta, e o import no topo obrigaria quem só usa `tick` a carregar o módulo do fio. **Por quê:** o plugin é copiado pro cache sem passo de instalação — não existe onde rodar `pip install`. `doc_lint.py` carrega isso na docstring (*"Stdlib-puro."*), `conformance.py` repete no topo (*"Python 3 stdlib apenas — convencao do repo (patterns.md)"*), `askq_lint.py` explica a consequência (*"o plugin é copiado pro cache sem passo de instalação, não existe onde rodar pip install"*), e `visual_page.py`/`md2deck.py` fecham com *"stdlib only (requisito do repo)"* [confirmado, os cinco arquivos].

### 2.2 Fail-open também vale no Python: "não sei" ≠ "zero"

O padrão mais sutil do repo. Exemplos literais de `plugins/project-skills/lib/doc_lint.py` [confirmado]:

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

### 2.5a O gate de julgamento tem duas forças: o que RECUSA e o que AVISA

Irmão do §2.5, na direção do *conteúdo* em vez da forma. O `visual_page.py` chama o
`clareza.py` **duas vezes, com pesos diferentes** [confirmado — `visual_page.py`, o import de
topo e o fim de `cmd_build`]:

| chamada | quando | força | por quê |
|---|---|---|---|
| `erros_de_clareza(spec)` | dentro do `validate` | **recusa**, exit 2, não escreve | é lista de termos que um juiz externo JÁ reprovou — não há julgamento a fazer |
| `revisao_do_spec(spec)` | depois de escrever, no stderr | **avisa** | são padrões estruturais, e cada um tem exceção legítima — quantos, o próprio código diz: `grep -c '^    # [0-9] · ' plugins/visual/lib/clareza.py` |

A régua que separa as duas: **recuse o que já foi julgado; avise o que ainda precisa de
julgamento.** A `.evidencia` que fecha um capítulo dispara a conferência "prova sem o
estrago" e está certa; recusá-la ensinaria a contornar o cobrador — e *"falso positivo ensina
a contornar, e contornar desliga tudo"* (§5.2). Já um termo que reprovou com um leitor real
não tem contexto que o salve.

**E as duas rodam no BUILD, não num passo escrito na skill.** É a lição que gerou o padrão:
em 2026-08-08 uma página reprovou nas três decisões do juiz de clareza, e **duas das quatro
lições que a reprovaram já estavam no banco** — lidas no começo da rodada e não conferidas no
fim. Regra em prosa não pega, inclusive quando a prosa é a instrução do próprio agente.

⚠️ **O cobrador estreitou duas vezes na primeira hora de uso, e as duas por falso positivo:**
a conferência de custo passou a medir **por página** em vez de por frase (dizer uma vez que o
custo é dinheiro basta), e a de sinônimos passou a **isentar a abertura** (é lá que se
apresenta "plugin, ou pacote, é a caixa que se instala"). Cobrador de julgamento nasce largo
e é estreitado com caso real; nascer estreito é o que o torna ignorável.

🔴 **O terceiro estreitamento apagou uma conferência inteira — e a lição é sobre QUEM é o
leitor imaginado.** Em 2026-08-09 a conferência "palavra da casa usada sem ser aberta antes
da primeira pergunta" saiu do `revisao_do_spec`, e o termo banido `jargao-sem-glosa` trocou
de lista: `banido` virou `[]` e o teste virou uma pergunta. A numeração dos comentários no
código guarda o buraco (`1 · … 3 · 4 · 5 ·`), então a conferência que sumiu é rastreável
sem arqueologia. [confirmado — `clareza.py:revisao_do_spec` e `SEMENTE`, os dois lidos nesta
rodada] O motivo está na docstring nova, e ele separa **duas réguas que estavam coladas numa
só** [confirmado, citação literal]:

- **REPERTÓRIO** — *"um programador experiente que nunca viu ESTE projeto nem ESTA conversa.
  Ele já sabe o vocabulário corrente da área: contexto, agente, barra de status, plugin,
  hook."*
- **PACIÊNCIA** — *"uma criança de 5 anos. Frase que precisa de duas leituras já falhou."*

Aplicar a criança aos dois fazia a página abrir com um glossário do óbvio: *"definir
trivialidade adia a decisão em vez de destravá-la"*. O que continua precisando de
apresentação mudou de natureza — metáfora, apelido, referência indireta (*"o motor"*, *"a
régua"*) e peça deste código com sentido só local —, **e o que falta nelas não é definição de
dicionário, é CONTEXTO**: onde entra, o que faz, para que serve. Por isso a régua saiu da
lista de palavras e voltou para o juiz: lista fechada não sabe distinguir "hook" de "o
motor".

**Régua durável: cobrador de clareza precisa declarar o leitor em dois eixos separados —
o que ele já SABE e a paciência que ele TEM.** Colar os dois num só faz o gate cobrar
explicação de vocabulário corrente, que é ruído, e deixar passar o apelido da casa, que é o
defeito real. Corolário do §2.5a: o eixo do repertório não cabe em lista fechada de termos —
ele é julgamento, então é do juiz, não do `check`.

🔴 **O veredito do juiz virou PÁGINA, e o `validate` impede que ela se misture com a página
julgada.** Desde 2026-08-09 o `visual_page.py` reconhece a página de parecer pelo **slug**
(`e_parecer(spec)` → `slug` começando em `parecer-`) e faz duas coisas com ela: recusa o spec
que traga bloco `aprovacao` ou `decision` do trabalho julgado (*"o parecer é aprovado
sozinho; leve o bloco pra página julgada"*) e força `item_labels` para os rótulos de
aprovação, ignorando o que o spec pediu. **É o programa mandando, não a receita**: rótulo de
"manter/mudar" numa página de parecer convidaria a editar o apontamento em vez de aprová-lo,
e aprovação do trabalho na mesma página faria um veredito valer pelo outro. A régua durável:
**quando duas decisões diferentes cabem na mesma tela, quem separa é o build — não a
instrução de quem monta.** `[confirmado — `visual_page.py:e_parecer`/`validate`/`build_body` e
`test_visual_page.py`]`

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

### 2.7 Régua de forma: onde há teto mecânico a prosa não cresce

**Mora em `_shared/regua_texto.py` desde 2026-08-03** — nasceu dentro do `visual_page.py` em 2026-08-02 e saiu de lá porque os outros geradores (plano, slide, texto de hook) emitem texto que o mesmo humano lê com a mesma pressa, *"e cada um ficava livre para inventar a própria forma"* [confirmado, docstring literal]. Ela nasceu de uma comparação medida entre dois artefatos do mesmo autor [confirmado]:

```
campos do PLANO (teto de 140 cobrado por plan_state desde sempre)
   desc   n=171  mediana=100  p90=128  máx=137     ← nunca encostou no teto
parágrafos das PÁGINAS HTML (nenhum teto)
   n=1624  p50=140  p90=272  p95=330  máx=2182     ← 24% acima de 200
```

**Mesmo autor, mesma sessão, uma ordem de grandeza de diferença.** O que separa os dois não é cuidado — é a existência de um número cobrado por programa. É o mesmo achado do §5.1 (o bump que "todo mundo lembra" foi contornado 7 vezes) e do `stop-prose-ceiling.py` (*"premissa que nasce desligada não é premissa — é comentário"*), agora aplicado a texto.

As quatro checagens, e por que nenhuma sozinha resolve [confirmado, `_shared/test_regua_texto.py` → `71 passou · 0 falhou`]:

- **≤ 140 caracteres por bullet** (`BULLET_MAX`). O número **não** foi calibrado do zero: é o teto que `plan_state` já cobra no `desc`, com máximo real de 137. Reusar número provado em produção é mais barato que justificar um novo.
- **Uma frase por bullet** (`_DUAS_FRASES`, ponto seguido de espaço). O teto sozinho produz *enjambment*: a prosa de 600 caracteres vira 8 bullets de 75 que se leem em sequência, passa no teto e continua prosa.
- **Sem conectivo de continuação abrindo bullet** (`_CONECTIVO`: `e`, `mas`, `que`, `porque`, `então`, `ou seja`, `além disso`). Pega o que as duas primeiras deixam passar.
- **Máximo 6 bullets por bloco** (`BULLETS_MAX`). Acima disso é prosa picada, ou são dois itens.

**A calibração foi feita contra o corpus, não no chute** [confirmado — medido sobre `ul.bullets` reais, n=145, mediana 117]: teto 120 reprovava 59%, teto 140 reprova 48%. Bullet autoral típico já cabe; o que reprova é a cauda.

#### As quatro checagens são as mesmas; o PERFIL declara o que, naquele artefato, não é redação

O contrato está na docstring, e ele fecha a saída de emergência óbvia [confirmado, citação literal]: *"Perfil não é exceção. Não existe perfil frouxo: os quatro cobram as quatro checagens."* Um nome desconhecido levanta `ValueError` em `perfil()` — *"nome errado não vira o perfil frouxo por engano"*.

**Cinco perfis hoje** [confirmado — derivado com `python3 -c "…; print(r.PERFIS)"` sobre `_shared/regua_texto.py`]:

| perfil | bullet | bullets | extra |
|---|---|---|---|
| `pagina` | 140 | 6 | página, relatório, diagnóstico — o de origem |
| `plano` | 140 | 6 | a árvore desenhada pelo programa fica fora |
| `slide` | 140 | 6 | ≤ 20 palavras por bullet (`md2deck.STATEMENT_WORDS`) |
| `hook` | 140 | 6 | sem markdown; cabeçalho tem que abrir com emoji |
| `contexto` | **200** | **20** | árvore fora; markdown permitido |

⚠️ **O perfil `contexto` é o único cujos números sobem, e o motivo é o LEITOR.** Ele serve o canal `additionalContext`, que é *"lido pelo MODELO, não pela tela"* — então markdown é legítimo (o modelo o interpreta) e cabeçalho com emoji não faz sentido, *"ninguém está olhando"*. O teto de bullets é 20 porque **o canal carrega inventário** (lista de docs, de planos, de gotchas), e o comentário nomeia a consequência de aplicar o 6: *"cortar inventário em 6 esconde item — o oposto do que ele existe pra fazer"*. O que continua valendo é uma frase por bullet, sem prosa fatiada.

**Régua durável: régua por artefato se declara por PERFIL, e perfil declara o que não é redação — nunca qual checagem cai.** Perfil que desliga checagem é exceção com outro nome, e exceção nomeada vira o caminho preferido.

⚠️ **O escopo da régua é o REGIME, não o arquivo.** Ela vale para tudo que sai de gerador (regime "informação rápida"); `SKILL.md` e `.claude/docs/` são constituição, admitem nuance e **não** passam por ela. A fronteira é o pipeline — **não existe campo `regime` no spec**, de propósito: campo declarável viraria a saída de emergência universal.

Duas isenções escritas no código, as duas por natureza do conteúdo e válidas em **todo** perfil: `evidencia.output` (saída crua é literal por obrigação — parafrasear a prova é o defeito original com outra roupa) e `raw_html` (a válvula de layout). Linha de árvore de plano fica fora nos perfis que declaram `arvore_fora`: é gerada por programa, não é redação.

**Duas frentes cobram a régua hoje**, e nenhuma sozinha fecha: o check I do release-gate barra **gerador de HTML que não a chama** (§5.2), e os dois hooks do §1.17 pegam o texto já escrito — o arquivo na porta, o relato na rede.

**Régua durável: teto de tamanho não mata prosa — mata a metade fácil. Quem quer bullet de verdade precisa cobrar também a ESTRUTURA da frase, senão o texto se refatora pra caber e volta igual.**

### 2.7a A prova de um passo também sai em bullets — e o `tick` recusa o bloco corrido

Aplicação da mesma régua no `plan_state.py`, novo em 2026-08-03. `prova_bullets()` quebra a prova **só onde quem a escreveu já separou** — `\n`, ` · `, `; ` ou ` + ` — e a docstring é explícita sobre o limite [confirmado, citação literal]: *"Não inventa corte … Prova de um segmento só continua um bullet."*

Quem barra é o `tick`, no momento de gravar, não o renderizador [confirmado, `plan_state.py:cmd_tick`]:

```python
if len(ev) > BULLET_MAX and len(prova_bullets(ev)) < 2:
    raise PlanError("⛔ tick recusado: a prova de %s tem %d caracteres num bloco só.…")
```

Três propriedades que fazem isso não virar atrito:

- **A mensagem de recusa traz o exemplo pronto**, com os separadores aceitos e uma linha copiável (`--evidencia "$ pytest -q → 62 ok · sync-shared --check OK · a1b2c3d"`). <!-- lint:ignore a1b2c3d --> Gate que só diz "não" ensina a contornar.
- **Saída crua de um comando passa inteira** — a isenção do §2.7 vale aqui: *"o teto só vale pro texto que VOCÊ redigiu"*.
- **Quem separa é quem escreve, o programa só verifica.** Cortar sozinho num limite de caracteres partiria a prova no meio de um sha ou de um caminho.

**Por que no `tick` e não no render:** é o mesmo desenho do §2.5 — a validação mora na **porta de escrita**, porque texto gravado torto é lido por todo consumidor dali em diante, e o renderizador não tem como consertá-lo sem inventar.

### 2.8 Colapso que não vira ocultação: derive tudo que fica visível

Par do §2.7, mesma rodada. O corpo do problema passou a nascer dobrado, e a pergunta que isso abre é quem garante que dobrar não é esconder — sendo que **quem escreve o artefato é quem executou o trabalho** [confirmado, `visual_page.py:_tri`]. O `.tri` de DECISÃO estende o mesmo princípio sem furar a régua: `r_tri` emite feedback-item com veredito (radios + textarea) e o problema vira o título — o problema continua visível, nunca engolido pelo veredito [confirmado, `visual_page.py:r_tri`].

O desenho recusado, e o motivo, ficam registrados porque a tentação volta: **gravidade decidindo o colapso** (item grave nasce aberto, o resto fechado) é o mesmo problema mudado de lugar — quem preenche a gravidade é a parte interessada, e o campo manipulável ganharia o poder novo de **fechar**. Regra final não tem ramo: nível 0 visível, resto fechado, para todo item.

O que sobra é derivação, não disciplina:

- **O rótulo do que está fechado é promoção de conteúdo**, não campo à parte: sai o primeiro bullet da consequência (já sob a régua do §2.7) mais a contagem do resto. Rótulo livre seria o novo lugar de amaciar; etiqueta fixa foi tentada (*"o que isso causa · como resolver"*) e rejeitada — a mesma linha em todo bloco não ajuda a decidir se vale abrir.
- **Placar agregado no topo, sempre aberto**, computado do spec (`_placar`): esconder um item passa a exigir omiti-lo por inteiro.
- **Colapsar não é amputar:** o validador continua exigindo as três partes do `tri` — mudou onde ele procura, não o que ele exige.
- **A válvula só abre.** `"aberto": true` fica na mão de quem escreve porque **revelar mais nunca esconde**; o simétrico (um campo que feche) não existe.

**O que fica declaradamente fora do alcance:** omissão total de um item. Nenhum validador de página pega o que nunca entrou nela — colapso sempre foi o vetor secundário. Onde existe fonte estruturada (o registro do `/qa-loop`) dá pra cruzar contagem; onde não existe, o vetor está escrito no `quality-goals.md` em vez de fingido.

### 2.8a O discriminador `.tri` vs `.decision-card`: a pergunta que muda a ação manda

**Emenda no `plugins/visual/skills/visual/SKILL.md` (não commitada nesta rodada)** [confirmado — li o diff do working tree]: a tabela "What to render" mandava *"Diagnostic → cada item em `.tri`"* sem ressalva, e a regra *"Max 1 main decision"* foi lida como **teto total** — resultado medido: **3 pontos de decisão saíram como `.tri`** num relatório do motor de execução contínua [relatado — texto da própria emenda]. O discriminador operacional que a emenda introduz:

- Item carrega **pergunta cuja resposta muda a próxima ação** de quem lê ("mantém as capas ou reverte?", "prova em tela ou descreve a falha?") → **`.decision-card`**, com as opções autorais.
- Item **só informa** uma pendência ou risco, sem resposta que mude o que fazer em seguida ("o total está em caixa preta", "a procedência é desconhecida") → **`.tri`**.
- **O teste é a existência da escolha, não a confiança nela** — *"na dúvida, se há uma pergunta com resposta que altera a ação, vire decision-card — cair no tri por 'não ter certeza' foi o defeito medido"* [confirmado — citação literal da emenda].

E a hierarquia 1 corrige a outra leitura: **"Max 1 main decision" é teto de POSIÇÃO, não de quantidade** — só uma decisão dominante no topo; sub-decisões adicionais têm os próprios cards abaixo [confirmado — emenda].

**Régua durável: regra de render em tabela precisa da RESSALVA que diz quando a linha não vale — a tabela "Diagnostic → cada item em `.tri`" sem a exceção virou o caminho preferido do modelo, e teto lido como total rebaixou escolha a `.tri`.**

### 2.9 Plugin que expõe MCP server: `.mcp.json` na raiz, endpoint fora do repo

**Padrão novo com o `vision` (v0.1.0, commit `4a4b59d`)** [confirmado — li `plugins/vision/` por inteiro]: um plugin pode entregar **tools MCP ao Claude sem hooks e sem skill** — só o `.mcp.json` na **raiz** do plugin:

```json
{"mcpServers": {"vision": {"type": "stdio",
  "command": "python3",
  "args": ["${CLAUDE_PLUGIN_ROOT}/vision_mcp.py"]}}}
```

- **`${CLAUDE_PLUGIN_ROOT}` resolve pro cache do plugin instalado** — o mesmo placeholder que os hooks usam; nunca um caminho do repo.
- **O server é stdlib puro** (`base64`, `json`, `os`, `sys`, `urllib`), coerente com o §2.1 — transporte MCP stdio = JSON-RPC 2.0 newline-delimited no stdin/stdout [confirmado — `vision_mcp.py:main`].
- **O endpoint NÃO mora no arquivo** [confirmado — `vision_mcp.py:_config`, citação literal da docstring]: *"O ENDPOINT NÃO vive neste arquivo — ele é infraestrutura privada de quem instala."* Cascata: env `QWEN_BASE`/`QWEN_MODEL`/`QWEN_TIMEOUT` → `~/.claude/vision.json` (`{"base":…, "model":…}`) → **falha com mensagem clara pedindo a config — nunca um endpoint chutado**.

**Régua durável: integração que depende de infra privada de quem instala deixa o endpoint como DADO de config (env ou `~/.claude/`), nunca literal no repo público — e a ausência vira mensagem que ensina a configurar, não fallback que inventa.**

### 2.10 Disparar processo sem deixar filho para trás

Nasceu do defeito mais caro medido até hoje: uma máquina acumulou **2125 processos `python3`
órfãos** (todos com pai `1`) em 2026-08-08. A causa imediata foi um ciclo — `scripts/plano_vs_codigo.py`
executa os comandos que aparecem entre crases nos campos `pronto` do plano, o `pronto` de um passo
mandava rodar `plugins/vistoria/lib/medidor.py`, e o medidor consolida nove cobradores, **um deles
sendo o próprio `plano_vs_codigo.py`**. Volta ao topo, sem fundo.

**O ciclo só conseguiu multiplicar porque cada disparo individual já vazava.** Três defeitos, e cada
um tapa uma porta diferente [confirmado — os três estão no `finally` de `plano_vs_codigo.py:cumprido_comando`]:

```python
p = subprocess.Popen(cmd, shell=True, cwd=root, env=filho,
                     stdin=subprocess.DEVNULL,      # sem isto o filho HERDA o terminal
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)        # sem isto o NETO sobrevive ao teto
p.wait(timeout=TIMEOUT)
...
finally:
    if p is not None and p.poll() is None:
        os.killpg(os.getpgid(p.pid), signal.SIGKILL)   # cobre também o cancelamento do PAI
```

- **stdin herdado não estoura teto.** Comando que resolve perguntar algo — `git` pedindo credencial é
  o caso real — fica esperando **para sempre**, e o `timeout` não o alcança: ele não estourou, está parado.
- **`timeout` mata o filho, não o neto.** Quando o filho é um shell, o `python3` que ele abriu fica órfão.
  Sem grupo de processos próprio não há como alcançá-lo.
- **Cancelamento não passa pelo `except`.** Ctrl-C, workflow morto, sessão encerrada: nada disso é
  `TimeoutExpired`. É o `finally` que fecha essa porta.

**A trava do ciclo é dos DOIS lados, e ela mora no ambiente** — o que se repete são processos NETOS
criados por `sh -c`, e variável de módulo não atravessa `fork`:

```bash
grep -n "PLANO_VS_CODIGO_RODANDO" scripts/plano_vs_codigo.py plugins/vistoria/lib/medidor.py
```

**Os padrões são servidos de uma fonte só** (`_shared/padroes_vazamento.py`, vendorado — §3.1), porque
três programas cobram este mesmo defeito e **eles já divergiram no dia em que nasceram**: um tinha
`disown` na lista, outro não. Quem consome:

```bash
grep -rln "padroes_vazamento" scripts plugins --include=*.py | grep -v test_
```

**Régua durável: todo disparo de processo fecha a entrada e nasce em grupo próprio, e quem tem teto
mata o GRUPO no `finally` — não o filho. Programa que executa comando vindo de DADO (plano, config,
texto de terceiro) acende marca de reentrância no ambiente, e quem ele pode chamar de volta a lê.**
Quem cobra é o check **P** do gate (§5.2), com isenção `vaza-ok: <motivo>` na linha.

---

## 3 · Vendoring de `_shared/` (o único "build")

Claude Code isola plugins na instalação: só `plugins/<nome>/` vai pro cache, sem variável cross-plugin. Logo, **código compartilhado é COPIADO antes do commit** [confirmado, cabeçalho de `scripts/sync-shared.sh`].

- **Fonte-da-verdade:** `_shared/`. As cópias dentro dos plugins são derivadas.
- **Mapa explícito, não glob** — `scripts/sync-shared.sh:SPECS`, formato `destino::arquivo` [confirmado, copiado literal]:

```bash
sed -n '/^SPECS=(/,/^)/p' scripts/sync-shared.sh          # o mapa inteiro, sem cópia aqui
sed -n '/^SPECS=(/,/^)/p' scripts/sync-shared.sh | grep -c '::'                    # nº de cópias
sed -n '/^SPECS=(/,/^)/p' scripts/sync-shared.sh | grep '::' \
  | sed 's/.*"\(.*\)::.*/\1/' | sort -u | wc -l                                    # nº de pastas
sed -n '/^SPECS=(/,/^)/p' scripts/sync-shared.sh | grep '::' \
  | sed 's/.*::\(.*\)".*/\1/' | sort | uniq -c | sort -rn                          # fonte a fonte
```

  O comentário justifica o mapa explícito: *"consumidores diferentes vendoram arquivos diferentes"*.

- **A quantidade de cópias, de pastas e de fontes sai dos comandos acima, nunca de um número escrito aqui** — o mapa muda toda vez que um plugin nasce, morre ou é fundido. O `sync-shared.sh` imprime o total no fim: `OK: vendoring concluído (N cópia(s)).`
- 🔴 **Fusão de plugin reaponta o mapa, e os dois lados do erro falham de jeitos opostos.** Na rodada de 2026-08-09 três plugins foram extintos dentro do `project-skills`, e destinos como `plugins/sovai/hooks::…` e `plugins/qa-loop/lib::…` viraram `plugins/project-skills/…`. Os dois erros possíveis não se parecem [confirmado, lido o laço de `sync-shared.sh`]:
  - **Destino morto que ficou no mapa** — `--check` faz `cmp -s "$src" "$dst"` contra um arquivo que não existe mais, então ele acusa `DRIFT` e você é avisado. O perigo é o conserto reflexo: rodar `sync-shared.sh` sem `--check` executa `mkdir -p` e **ressuscita a pasta do plugin extinto**, com cópia nova dentro.
  - **Destino novo que faltou no mapa** — não há spec, não há `cmp`, não há linha de saída. O plugin de destino simplesmente roda em produção sem o arquivo compartilhado, e nada fica vermelho. É o lado silencioso, e é a razão de a fusão ser conferida por superfície e não por sensação. Ver o gotcha das **quatro superfícies** em §7.
- 🔴 **O vendoring deixou de carregar só PROGRAMA e passou a carregar INSTRUÇÃO.** Três das quinze fontes são markdown lido pelo modelo — `regua-de-pergunta.md` (9 cópias), `contrato-familia.md` (4) e `antipadroes-de-teste.md` (2). A consequência de release é a mesma do código, mas o modo de falhar é pior: uma cópia defasada de `.py` costuma quebrar um teste, enquanto uma cópia defasada de instrução **só faz o modelo se comportar diferente conforme o plugin de entrada**, sem nada ficar vermelho. Quem pega é o check A (`--check` com `cmp -s`), e ele é a única rede.
- ⚠️ **Régua de hook exige cópia mesmo quando quem chama é `.sh`.** Boa parte dos destinos do `regua_texto.py` são plugins que só emitem texto de hook, e o comentário do próprio `SPECS` diz por quê: *"o .sh chama a régua pela linha de comando, e o plugin instalado só enxerga a própria pasta — sem cópia aqui, a régua some em produção"*. Vendorar só quem faz `import` deixaria o gate mudo exatamente nos plugins que mais falam com o dono.
- ⚠️ **`sessionstart-deps.sh` é a exceção que confirma a regra: uma cópia só.** Ele mora em `plugins/bootstrap/hooks/` e os outros onze plugins o alcançam em runtime por `resolve-plugin.sh bootstrap hooks/sessionstart-deps.sh`. É a alternativa ao vendoring — funciona porque o `resolve-plugin.sh` acha o plugin irmão **pelo nome** no cache do harness, nunca por caminho relativo, e sai 0 calado se o irmão não estiver instalado. Custo: o `bootstrap` vira dependência silenciosa de doze plugins.
- 🔴 **Skill que alcança plugin irmão precisa do resolvedor DENTRO da pasta da skill — não basta ele existir no repositório.** O maior contribuinte do `SPECS` é o `resolve-plugin.sh` (`sed -n '/^SPECS=(/,/^)/p' scripts/sync-shared.sh | grep '::' | grep -c 'resolve-plugin.sh'` — o `grep '::'` é o que separa spec de comentário), e boa parte dos destinos é `plugins/<x>/skills/<y>/`, não `lib/` nem `hooks/`. A razão é o Artigo 8: comando de `SKILL.md` roda a partir de `${CLAUDE_PLUGIN_ROOT}`, e um caminho como `plugins/<irmão>/lib/…` **só resolve na árvore de quem escreveu** — na máquina de quem instala cada plugin tem pasta própria no cache. O par obrigatório é: a cópia do resolvedor ao lado da skill **mais** a chamada por NOME do irmão. Foi o que faltou no `improve-workflow` nesta rodada — a linha do `SPECS` `plugins/improve-workflow/skills/improve-workflow::resolve-plugin.sh` nasceu junto com a chamada `resolve-plugin.sh visual lib/visual_page.py` da `SKILL.md` [confirmado — as duas pontas lidas nesta rodada; `sync-shared.sh --check` → `OK: cópias vendored idênticas a _shared/`, rc=0].
- ✅ **Os números de vendoring que a doc publica ganharam cobrador.** `scripts/test_doc_vendoring_counts.py` refaz a conta a partir do `SPECS` e cobra que `architecture.md` traga cópias, pastas e os quatro maiores contribuintes com o valor de hoje — verde nesta rodada. É a esteira 3 do check J (§5.2), então o gate de commit o roda. Sem ele, "o comando produz o número" ficava valendo só para quem rodasse o comando.
- **Comandos:** `bash scripts/sync-shared.sh` copia; `--check` não copia e sai 1 listando `DRIFT: <dest> difere de _shared/<arquivo>`. Fonte ausente é **exit 2**, distinto de drift.
- **Estado neste run** [confirmado, executado]: `OK: cópias vendored idênticas a _shared/` (rc=0).

**Regra:** fix de código compartilhado **nasce em `_shared/`**, nunca na cópia. Editar a cópia e commitar é pego pelo check A do release-gate — editar `_shared/` e esquecer o sync também.

### 3.1 Contrato servido de uma fonte só: o número vira DADO, não texto de skill

**Novo em 2026-08-03**, e é a segunda coisa que o vendoring carrega além de código. O contrato de tier dos motores (hoje as skills `sprint` e `qa-loop`, ambas do `project-skills` — o dono se confere no índice, `.claude-plugin/marketplace.json`) morava em prosa nos `SKILL.md`, e o cabeçalho do check A2 traz a medida do estrago [confirmado, citação literal do `release-gate.sh`]:

> trocar seis tiers custou 45 substituições em dois SKILL.md, três saíram invertidas e duas passaram por dois verificadores — porque o número morava em quinze lugares.

O desenho tem três peças, e a separação entre elas é o ponto:

- **`_shared/r8-tiers.json`** — os DADOS. Fonte da verdade; um bloco por tier (`decompose`, `coordinate`, `executor`, `mechanical`, …) com `effort`, `etapa`, `quando` e `porque`.
- **`_shared/r8_tiers.py`** — o SERVIDOR. `carrega()` lê o JSON, `para_args()` monta o que vai na linha de comando, `render()` gera a tabela.
- **`_shared/r8-tiers.md`** — a VISTA HUMANA, **gerada** do JSON por `python3 _shared/r8_tiers.py check --fix`, entre marcadores. Editar o `.md` na mão é trabalho perdido: o `check` acusa a divergência e o `--fix` sobrescreve.

**A regra que faz o desenho valer: nenhum `SKILL.md` pode carimbar o valor do effort.** A casca lê o tier da cópia local e passa em `args`; a prosa cita o **KNOB**, nunca o número. Quem cobra é `r8_tiers.py check`, varrendo **todo** `SKILL.md` de `plugins/` atrás de effort literal e de nível solto ao lado de um knob [confirmado — rodado nesta passada: `OK: R8 servido de _shared/r8-tiers.json, sem cópia carimbada em SKILL.md`, rc=0]. É o check A2 do release-gate (§5.2).

**Isenção tem sintaxe e exige motivo escrito na linha:** `r8-ok: <motivo>`. Mesma família do `public-ok:` do check H — a linha isenta é pulada inteira, então o motivo é a única coisa que sobra pra auditar.

**Régua durável: valor que dois documentos precisam repetir não pertence a documento nenhum — vira dado, com um servidor que o entrega e um check que barra a cópia.** Prosa não tem como divergir de si mesma em silêncio se ela nunca chegou a conter o número.

✅ **A terceira forma da mesma régua: quando o que se repete é uma ORDEM, e não um número, a fonte única é uma SKILL — não um arquivo vendorado.** Em 2026-08-09 a instrução copiada *"leia a constituição e o quality-goals do projeto"* saiu das skills de etapa e virou um preâmbulo que invoca o par `doc-load` → `principles`. A diferença em relação ao vendoring de instrução (§3, terceiro alerta) é que a cópia deixa de existir: `plugins/project-skills/lib/doc_load.py` **lê a doc do projeto no momento da chamada** e devolve o que vale como régua HOJE — lei (`ready` ou `approved`), acordo (só `approved`, e REABERTO se o corpo mudou depois do de acordo) e minerado (nunca é régua, só mapa) —, com os ausentes declarados em vez de fingidos. Quem carrega o preâmbulo se conta pelo comando, nunca por uma lista escrita aqui:

```bash
grep -rl 'doc-load' plugins/*/skills/*/SKILL.md          # quem invoca o par
```

A prosa que sobrou nas skills é só a que **não** dá para servir: a ordem de precedência (*"em conflito, a régua do projeto ganha — princípio genérico não revoga a lei da casa"*) e o caminho de ausência (`principles` não instalado ⇒ segue sem ele, dizendo isso no relato) [confirmado, citação literal de `plugins/project-skills/skills/plan/SKILL.md`]. **Régua durável: instrução que manda LER algo não se copia — copia-se o convite a um programa que lê.** O texto copiado envelhece junto com o documento que ele mandava abrir; o programa não.

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

**Estado do catálogo** — a contagem e a lista saem do índice, nunca de um número escrito aqui (§3.1). O espelho do check B fecha quando a segunda linha não imprime nada:

```bash
python3 -c "import json;print(len(json.load(open('.claude-plugin/marketplace.json'))['plugins']),'entradas')"
python3 -c "
import json,glob
vs={json.load(open(f))['name']:json.load(open(f))['version'] for f in glob.glob('plugins/*/.claude-plugin/plugin.json')}
print([(p['name'],p.get('version'),vs.get(p['name'])) for p in json.load(open('.claude-plugin/marketplace.json'))['plugins'] if p.get('version')!=vs.get(p['name'])])"
```

Nesta rodada o espelho está fechado (a segunda linha não imprime nada) e o `author` presente é **objeto** — a forma que o `validate` aceita. A quantidade de entradas é o que a primeira linha devolve; escrevê-la aqui só cria um segundo lugar para envelhecer.

🔴 **Plugin também MORRE, e a morte toca as mesmas superfícies que o nascimento — mais três que ninguém cobra.** Em 2026-08-09 três plugins foram extintos por fusão dentro do `project-skills`. Sair do catálogo é o passo que o `claude plugin validate` confere; os outros três são silenciosos (mapa do vendoring, `CLAUDE_STATUSLINE_FORWARD`, `hooks.json` de destino) e estão detalhados no gotcha das quatro superfícies (§7). **Toda regra escrita aqui em cima que nomeia um plugin muda de dono numa fusão** — por isso a doc aponta para o índice em vez de listar nomes.

⚠️ **"Qual plugin não mudou desde a raiz" deixou de ser pergunta respondível**, e a doc anterior a respondia errado. O commit-raiz `2587006` **não traz nenhum `plugins/*/.claude-plugin/plugin.json`** — `git ls-tree 2587006 -r --name-only -- 'plugins/*/.claude-plugin/plugin.json' | wc -l` devolve **0**. Então todo manifesto de hoje aparece como "adicionado" no diff contra a raiz, e ordenar por isso não separa plugin parado de plugin ativo. Para achar o parado, use a data do último commit que tocou cada manifesto, não o diff contra a raiz.

🔴 **A regra 1 ("bump em TODA mudança") foi contornada 7 vezes nesta rodada, e o gate mecânico que a cobra não reclamou.** Derivado commit a commit: [confirmado]

```bash
# para cada commit que tocou plugins/visual/, o plugin.json entrou no diff?
e692e1e BUMPOU     649d737 BUMPOU
11c18fa sem bump   52baade sem bump   8941271 sem bump   e03ac98 sem bump
4395447 sem bump   65fe78d sem bump   892d146 sem bump
```

**Nove commits tocaram `plugins/visual/`; apenas dois mexeram na `version`** (1.8.6 → 1.9.0 → 1.9.1). Pelo texto do check C, os outros sete deviam ter sido barrados — ele acusa `BUMP ESQUECIDO` para todo plugin tocado cuja `version` é idêntica à do `HEAD`, e sem o `plugin.json` no diff ela é idêntica por construção [confirmado, `.claude/hooks/release-gate.sh`]:

```python
touched = sorted({m.group(1) for m in (re.match(r"plugins/([^/]+)/", f) for f in files) if m})
old = head_json(mf)
if old is not None and old.get("version") == pver:
    viol.append("❌ BUMP ESQUECIDO — %s mudou mas version continua %s\n"…)
```

✅ **A causa foi achada e consertada, e não era a que estava escrita aqui.** A hipótese anterior — commits fora da ferramenta Bash — foi substituída: o gate **disparava** pela ferramenta Bash, mas o **gatilho era um `grep` na FORMA do comando** e deixava passar `env FOO=1 git commit`, `(git commit)`, `bash -c "git commit"` e `VAR=x git commit`. Com o gatilho mudo, os oito checks saíam calados. O gatilho hoje quebra o comando em tokens e lê o subcomando do git de verdade (§5.2). [confirmado — o comentário do próprio arquivo nomeia as quatro formas e a suíte `.claude/hooks/test_release_gate.sh` cobre cada uma]

**Régua durável, e ela vale para todo gate deste repositório: detecção que casa FORMA de comando não é detecção — quem escreve o comando de outro jeito, mesmo sem querer, desliga o gate inteiro em silêncio.** O sinal de que isso aconteceu não aparece em lugar nenhum; foi preciso reconstruir commit a commit para enxergar. O corolário anterior continua de pé: o gate segue amarrado ao `matcher: "Bash"`, então commit por outro caminho continua fora do alcance dele.

### 5.2 O gate mecânico de commit

`.claude/hooks/release-gate.sh`, registrado em `.claude/settings.json` como `PreToolUse` com `matcher: "Bash"` e `timeout: 60`, apontando para `$CLAUDE_PROJECT_DIR/.claude/hooks/release-gate.sh` [confirmado — li o settings.json inteiro; é o **único** hook declarado lá]. <!-- lint:ignore CLAUDE_PROJECT_DIR -->

**Dependência invertida:** ao contrário dos hooks de plugin, que assumem `jq`, o release-gate **não usa `jq` uma vez sequer** — faz todo o parse com `python3 -c` [confirmado: `grep -c jq` → 0; `grep -c python3` → 9]. Sem `python3`, ele cai no fail-open de infra e não checa nada.

**Como decide o que olhar** [confirmado, copiado literal]:

```bash
GATILHO=$(printf '%s' "$INPUT" | python3 -c '…' 2>/dev/null) || exit 0
[ -n "$GATILHO" ] || exit 0
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -f "$ROOT/.claude-plugin/marketplace.json" ] || exit 0   # não é este monorepo
FILES=$( { git -C "$ROOT" diff --cached --name-only
           git -C "$ROOT" diff --name-only; } 2>/dev/null | sort -u )
```

Untracked **não** entra, e o comentário diz por quê: *"sem `git add` ele não é commitado — incluí-lo dava falso-positivo com estado de runtime"*.

🔴 **O gatilho deixou de ser um `grep` na FORMA do comando, e essa era a origem do furo do §5.1.** A regex antiga (`(^|[;&|]|&&)[[:space:]]*git[[:space:]]+.*commit`) exigia que o `git` estivesse em início de linha ou logo depois de `;`/`&`/`|` — então **`env FOO=1 git commit`, `(git commit …)`, `bash -c "git commit …"` e `VAR=x git commit` passavam calados**, e com eles saíam os oito checks inteiros. No outro sentido ela disparava em `git log --grep commit`, que não commita nada, e *"falso positivo ensina a contornar, e contornar desliga tudo"*.

Hoje o comando é **quebrado em tokens** (o split inclui `(`, `)`, `;`, `&`, `|`, `<`, `>`, aspas e crase — é isso que recupera as quatro formas) e o **subcomando do git é lido de verdade**: para cada token `git` (ou `…/git`), o parser pula as opções globais e os valores delas (`-c`, `-C`, `--git-dir`, `--work-tree`, `--namespace`, `--exec-path`) e só age se o token seguinte for literalmente `commit`. [confirmado — li o bloco inteiro nesta rodada]

⚠️ **`--amend` é detectado, e ele muda o que o check C compara.** Como as aspas somem no split, a mensagem do commit vira token solto e um `--amend` escrito DENTRO dela passaria por flag; por isso só contam as opções **coladas ao subcomando** — o primeiro token que não é opção nem valor de opção encerra a varredura. Detectado o amend, o check C compara com **`HEAD~1:`** em vez de `HEAD:`, porque em amend o `HEAD` **é** o commit sendo reescrito e a comparação acusava `BUMP ESQUECIDO` de uma version que já estava dentro do próprio commit. Amend do commit raiz: `git show` falha e nada é acusado. [confirmado]

🔴 **O corpo de um heredoc não é comando — e ler como se fosse bloqueava a edição de quem só estava COLANDO texto.** Em 2026-08-09 o gate disparou três vezes sobre `python3 - <<CORPO … CORPO`, porque o texto dentro do heredoc continha as palavras do gatilho: o split não distingue comando de dado, então uma string escrita num script era tokenizada como se alguém fosse commitar. O conserto é um recorte ANTES da tokenização — `sem_heredoc()` em `.claude/hooks/release-gate.sh` acha `<<-? MARCADOR` (com ou sem aspas), remove tudo até a linha do marcador e devolve o resto; heredoc sem fechamento leva o corpo até o final do texto, e o comando real em volta continua inteiro [confirmado — `grep -n 'sem_heredoc' .claude/hooks/release-gate.sh` → definição na linha 33, chamada dentro do `re.split` na 46]. Dois casos novos em `test_release_gate.sh` fecham as duas pontas: o corpo não dispara, e um `git commit` escrito DEPOIS do marcador de fechamento continua disparando [confirmado, executado nesta rodada: `bash .claude/hooks/test_release_gate.sh` → `OK (45 checks)`].

**Régua durável: gate que lê a linha de comando precisa saber onde o comando termina e o DADO começa.** É o outro lado da régua do §5.1 — lá o gate ficava cego por casar forma de menos; aqui ele ficava cego pelo contrário, casando texto que nunca seria executado. Os dois erros têm o mesmo efeito prático: *"falso positivo ensina a contornar, e contornar desliga tudo"*.

**Suíte dedicada: `.claude/hooks/test_release_gate.sh`, verde nesta rodada** (ela imprime `OK (N checks)`; o N sai da execução, não daqui) — ela exercita as quatro formas que passavam, o falso positivo do `git log --grep commit`, o `--amend` dentro da mensagem (*"é texto, não amend"*) e o fail-open fora do monorepo. ⚠️ **Ela mora em `.claude/hooks/`, fora dos globs dos checks D e F**, então nenhum commit a dispara automaticamente — mesma exceção das duas suítes de `scripts/`.

**Quantos checks o gate tem hoje** — a contagem sai do próprio arquivo, nunca de um número escrito aqui:

```bash
grep -cE '^# [A-Z0-9]+ · ' .claude/hooks/release-gate.sh
```

A rodada anterior trouxe **seis de uma vez** — `J`, `K`, `L`, `M`, `N` e `O` —, o maior
salto que o gate já teve; depois dela entraram `P` e `Q`. Todos vêm da mesma frente:
transformar em cobrador mecânico o que antes era artigo escrito na constituição
[confirmado, derivado nesta rodada]:

```bash
grep -oE '^[[:space:]]*# [A-Z][0-9+C]* · ' .claude/hooks/release-gate.sh | grep -oE '[A-Z][0-9+C]*'
# → os rótulos, na ordem em que foram escritos. "B+C" é o cabeçalho do bloco que
#   contém C, B e B2, então os checks distintos são um a menos que os rótulos.
grep -oE '❌ [A-ZÁ-Ú ]+' .claude/hooks/release-gate.sh | sort -u
# → as mensagens de violação; são menos que os checks porque D, D2, F e J
#   compartilham "❌ TESTE VERMELHO"
grep -n 'roda_suites' .claude/hooks/release-gate.sh
# → quantos globs de suíte o check J varre hoje
```

⚠️ **As letras não seguem ordem alfabética no arquivo, e não são ordem de execução.** `O`
está registrado depois de `P`, `F` e `J` fecham o arquivo. A ordem em que aparecem é ordem
de quando foram escritas, e o gate acumula tudo em `VIOL` antes de decidir — então ler a
letra como "etapa N" leva a conclusão errada.

A ordem de execução não importa: todos só acumulam em `VIOL`.

- **A · vendoring** — roda `scripts/sync-shared.sh --check`. Drift ⇒ `❌ VENDORING EM DRIFT`, mandando corrigir **na fonte** `_shared/<arquivo>`.
- **A2 · contrato R8 servido de uma fonte só** — **novo em 2026-08-03**. Roda `python3 _shared/r8_tiers.py check`. Effort literal ou nível solto ao lado de um knob em qualquer `SKILL.md` ⇒ `❌ CONTRATO R8 FURADO`, com arquivo:linha e o texto do conserto: *"o valor vive em `_shared/r8-tiers.json` e chega ao motor por args; o SKILL.md cita o KNOB, nunca o número. Isenção: `r8-ok: <motivo>` na linha."* Fail-open declarado: se `_shared/r8_tiers.py` não existir, o bloco inteiro é pulado (§3.1).
- **B · espelho `plugin.json` ↔ `marketplace.json`** — divergiu ⇒ `❌ ESPELHO QUEBRADO`, com as duas versões impressas.
- **B2 · espelho da DESCRIPTION** — nasceu de erro medido em 2026-08-02 (commit `9f557ff`), e nunca esteve nesta lista: *"quatro descricoes foram reescritas SO no marketplace.json, e `claude plugin details` mostra a do plugin.json — a vitrine nova nunca chegaria a quem instala"*. ⇒ `❌ DESCRIPTION DIVERGENTE`, com o tamanho e os 60 primeiros chars de cada lado. **Só cobra o plugin TOCADO neste commit**, e o comentário diz por quê: *"6 dos 19 ja divergiam antes, e barrar divida antiga trava trabalho alheio (mesma regra do `public_repo_check --staged`)"*.
- **C · bump esquecido** — compara com `git show HEAD:<manifesto>`, ou com `HEAD~1:` quando o gatilho detectou `--amend`. Iguais ⇒ `❌ BUMP ESQUECIDO — <nome> mudou mas version continua <v>`.
- **D · testes Python** — roda `plugins/<nome>/lib/test_*.py` dos plugins tocados. Vermelho ⇒ `❌ TESTE VERMELHO` com as últimas 15 linhas.
- **D2 · suíte de `_shared/`** — só quando o commit toca `_shared/`. Roda `_shared/test_*.py`, a suíte da FONTE do código vendorado. Nasceu de um buraco entre D e F: nenhum dos dois globs (`plugins/<nome>/lib/` e `plugins/<nome>/hooks/`) casa com `_shared/`, então a suíte que define o comportamento do código compartilhado dependia de alguém lembrar de rodá-la à mão.
- **E · contrato dos hooks** — só quando o commit toca `plugins/*/hooks/`. Roda `python3 scripts/hook_contract.py --baseline .claude/hook-contract.baseline.json --fail-on high` e barra **o que piorou**. O comentário explica a escolha: *"Comparar com o baseline (e não exigir zero) é o que impede a regra de apodrecer"*.
- **E2 · orçamento do fim de turno** — mesma condição do E (commit que toca `plugins/*/hooks/`) e outra régua: roda `python3 scripts/hook_contract.py --stop-budget --baseline .claude/stop-budget.baseline.json`. Não mede a FORMA do hook, mede **quanto o conjunto cospe no `Stop`** — e o que barra é a deriva contra o retrato, não um teto absoluto, porque o total já encostou nas 6 linhas de referência.
- **G · gen defasado no marker das skills de documentação** — lê `CURRENT_GEN` de `plugins/project-skills/lib/pattern_check.py` (o valor se confere com `grep -n 'CURRENT_GEN' <o arquivo>`) e varre `plugins/project-skills/skills/` procurando `gen=X.Y` **dentro de comentário HTML**. ⚠️ **O recorte de escopo ficou apontando para o plugin extinto**: o `if` que decide se o bloco roda ainda testa `^plugins/project-doc/`, caminho que não existe mais no repositório — então o check está inerte hoje. É o quinto lugar que a fusão tocou, e o único que nem `validate` nem suíte nenhuma acusa: o corpo do check já fala os nomes vivos, só a porta de entrada ficou no nome morto. [confirmado — li o bloco e conferi que `plugins/project-doc/` não existe] Menção em prosa a um gen antigo **não** é violação — *"barrá-las ensinaria a ignorar o gate"*. Fail-open se `CURRENT_GEN` não resolver (`sys.exit(0)`).
- **H · dado pessoal em commit de repo público** — roda `python3 scripts/public_repo_check.py --staged`. Só olha o que **este** commit traz: *"dívida antiga não trava ninguém, mas ocorrência nova é barrada na porta"*. O comentário registra por que virou código: *"Regra em prosa não pega (o CLAUDE.md pedia isso e 368 ocorrências entraram assim mesmo)"*.
- **I · gerador de página fora da régua de estilo** — roda `python3 scripts/regua_call_check.py --staged`. Arquivo que monta HTML e **não** chama a régua de `_shared/regua_texto.py` é barrado. Mesma regra do H: só o que **este** commit traz, porque os geradores que já estavam fora não podem travar trabalho alheio.
- **P · disparo de processo que pode deixar filho para trás** — **novo em 2026-08-08**, e nasceu de uma máquina com **2125 processos `python3` órfãos**. Só quando o commit traz `.py`. Roda `python3 scripts/vazamento_check.py` e barra o disparo sem `stdin=` (o filho herda o terminal e espera para sempre — o teto **não** o alcança, porque ele não estourou) ou sem `start_new_session=` (o teto mata o filho e o **neto** sobrevive). Cobre também o lado Node, por regex: `stdio: 'inherit'`. Isenção: `vaza-ok: <motivo>` na linha. Ver §2.10.
- **K · número do README contra o repositório** — roda `python3 scripts/readme_counts_check.py` quando o commit toca o README ou uma das fontes que alimentam os números dele. Nasceu com as **cinco** afirmações da vitrine defasadas de uma vez (19→21, 17→19, 46→68, 10→12, 34→54) ⇒ `❌ README DEFASADO`. É a lei do desacoplamento aplicada ao único doc que quem instala lê primeiro: *"plugin novo entra e a prosa fica"*. 🔴 **Nesta rodada ele deixou de conferir só CONTAGEM e passou a conferir NOME**, porque o defeito medido tinha o número certo: o README dizia *"3 desligados"* — contagem correta — listando dois plugins que a receita do `bootstrap` **não** desliga. O cobrador de número passava verde e quem instala ligava o plugin errado. As duas passagens do README que listam os desligados são casadas por regex e comparadas com `_manifest_desligados_nomes()` (lê `enabled` em `plugins/bootstrap/config/manifest.json`), filtrando pelos nomes que existem no catálogo `.claude-plugin/marketplace.json`. Quantas afirmações ele confere hoje sai da própria execução: `python3 scripts/readme_counts_check.py` imprime `README em dia — N afirmação(ões) de contagem conferida(s).` [confirmado — rodado nesta passada, rc=0]. Suíte própria nova: `scripts/test_readme_counts_check.py`, verde nesta rodada.
- **L · função nova que ninguém invoca** — roda `python3 scripts/fiscal_de_bancada.py --motivo sem-chamador`, só quando o commit traz `.py` (é onde ele lê AST) ⇒ `❌ PEÇA SEM CHAMADOR`. O defeito medido que o gerou: *"de quatro passos reprovados numa rodada, TRÊS tinham código bom — bem escrito, com teste próprio — que nenhum lugar da árvore chamava"*. **Peça que nunca roda não deixa suíte vermelha**, então sem este check o defeito só aparecia na revisão humana. Só o eixo `sem-chamador` entra; `sonda` e `nao-declarado` acusam arquivo não rastreado e travariam trabalho alheio.
- **M · aviso escrito num canal que todo consumidor descarta** — mesmo cobrador do L, outro motivo (`--motivo aviso-no-vazio`), quando o commit traz `.py`/`.sh` ⇒ `❌ AVISO NO VAZIO`. Nasceu do irmão do defeito do L: a recusa era escrita em stderr e *"TODO caminho que chamava o script fechava a chamada com `2>/dev/null`"* — o aviso existia, tinha teste, e não chegava a ninguém.
- **N · acoplamento novo entre plugins** — roda `python3 scripts/desacoplamento_check.py` quando o commit traz `.md`/`.sh`/`.py`/`.json`/`.yml` ⇒ `❌ ACOPLAMENTO NOVO`. É o Artigo 9 virando cobrador: plugin que aponta pro irmão **por posição** (`<raiz>/../<irmão>`) quebra na máquina de quem instalou, porque o cache do harness dá pasta própria a cada plugin; e contagem cravada em prosa envelhece sem avisar. ⚠️ **Diferente do H e do I, este NÃO tem `--staged`**: varre todo arquivo rastreado e só reprova achado que está **fora** de `.claude/desacoplamento.baseline.json` — dívida antiga passa, acoplamento novo não.
- **R · description que só serve a quem já sabe que a skill existe** — **novo em 2026-08-08**, e nasceu do pedido de apelidos curtos. Roda `python3 plugins/check-skills/lib/varredura.py --situacao-repo .` quando o commit traz um `SKILL.md`. Apelido (`"/faxina"`, `"sovai"`) é achado por quem **lembra do nome**; quem não lembra que a skill existe só é atendido se a description disser em que **situação de trabalho** ela entra — o molde é o da `sprint` (*"Use quando o usuário disser…"*). O comentário do check registra a régua de desacoplamento na própria explicação: *"Quantas skills do marketplace ainda são só lista de gatilho se descobre com o próprio comando abaixo, nunca de memória"*.
- **Q · cópia de trabalho parada no disco** — **novo em 2026-08-08**. Roda `python3 scripts/worktree_orfao_check.py` ⇒ `❌ CÓPIA DE TRABALHO PARADA — quem busca arquivo pelo nome acha ela antes do original`. Nasceu de defeito medido: *"14 de 41 marcações do motor rodaram binário que não era o da árvore"* — os agentes procuraram o arquivo pelo NOME e o `find` alcançou as cópias em `.claude/worktrees/`; sete passaram por um validador 548 linhas mais velho, **sem as funções de recusa**. O comentário registra a causa de fundo: *"as cópias nasceram antes de a regra proibi-las — a regra proibiu criar novas e não varreu as velhas"*. ⚠️ **Segundo check SEM recorte por arquivo tocado, pelo mesmo motivo do O**: *"a cópia não aparece no diff de commit nenhum"*. Fail-open declarado: sem `scripts/worktree_orfao_check.py` o bloco inteiro é pulado.
- **O · plano e código discordando** — roda `python3 scripts/plano_vs_codigo.py` e barra passo **aberto** cujo critério de pronto o disco já cumpre ⇒ `❌ PLANO ATRASADO`. ⚠️ **É o único check SEM recorte por arquivo tocado, e de propósito**: `.claude/plans/` é gitignorado, então plano nenhum aparece em `$FILES` — recortar por arquivo o deixaria calado para sempre. Custo medido: ~0,6s. O comentário registra que ele existia e ninguém o consultava: *"ele rodava e acusava sem que portão nenhum o consultasse"*.
- **S · a lei da autópsia virando cobrança** — **novo em 2026-08-09**. Roda `python3 scripts/autopsia_check.py`, e só quando o commit toca `plugins/improve-workflow/` ⇒ `❌ LEI DA AUTÓPSIA FURADA`. Ele mede **texto**, não código: as três frases fixas que a skill `improve-workflow` tem que continuar carregando (a trava de robustez — *"reprove toda proposta que troque robustez por economia"*; a ordem de derrubar — *"tente derrubar cada afirmação"*; a proibição — *"nenhum arquivo do projeto muda durante a apura"*), e nenhum bloco executável do `SKILL.md` escrevendo na árvore (`git commit`/`git add`/`rm `/`mv `/`tee `/redirecionamento). O motivo está no cabeçalho do próprio script: *"prosa some numa reescrita e nada acusa — a rodada seguinte fica sem refutador e com licença para editar"*. ⚠️ **As três frases são o texto exato que o script exige, e a skill reescreve o vocabulário dela de vez em quando** — em 2026-08-09 a terceira trocou *"durante a rodada"* por *"durante a apura"*, e a doc que as citava passou a citar frase morta. O par vivo sai do próprio cobrador: `python3 -c "import sys;sys.path.insert(0,'scripts');import autopsia_check as a;print(a.FRASES)"`. É a régua de que **regra que só existe em prosa não é regra**, aplicada à skill que audita as outras. Fail-open declarado: sem `scripts/autopsia_check.py` o bloco inteiro é pulado. Suíte própria: `scripts/test_autopsia_check.py` (verde nesta rodada; `python3 scripts/autopsia_check.py` → rc=0).

  🔴 **O eixo de placeholder mudo entrou depois, e a lição é sobre a FORMA da isenção.** A primeira versão isentava o **operador**: `>` só contava como redirecionamento quando vinha depois de espaço (`\s>>?\s*\S`), para que `<run>` nos exemplos de uso não reprovasse a skill inteira. Afrouxar o operador abriu o buraco — `<plugin visual>` passava calado, e o shell lê aquilo como par de redirecionamentos, num bloco que quem copia vai executar. O conserto trocou o eixo: a isenção passou a ser do **token declarado** (`DECLARADOS = ("<run>",)`, apagado do bloco antes da varredura, preservando as posições para a linha do achado continuar certa), e o operador voltou a ser cobrado inteiro (`>>?\s*\S`). O que sobra de `<…>` vira o segundo achado, *"nomeia por placeholder mudo"*. **Régua durável: isenção de gate se escreve como lista fechada do que é legítimo, nunca como afrouxamento da regra** — afrouxar o operador isenta tudo que se parecer com o caso conhecido; nomear o token isenta só ele. É a mesma família do `public-ok:`, `r8-ok:` e `vaza-ok:`, que também isentam a **linha nomeada**, não o padrão.
- **F · testes shell** — roda `plugins/<nome>/hooks/test_*.sh` dos plugins tocados.
- **J · as suítes que nenhum glob de plugin casa** — o check que cresce por descoberta de buraco. Nasceu de um declarado: *"`grep -n 'scripts/test_' .claude/hooks/release-gate.sh` não devolvia nada, e as suítes de portabilidade tinham medidor sem cobrador no commit"*. Escopo: commit que toca `scripts/`, `plugins/*/hooks/`, `.claude/hooks/` ou `.gitattributes`. Custo medido em 2026-08-06: **~100s**, dos quais 80s são de `scripts/test_bootstrap_aviso.sh` — é o check mais caro do gate, e o recorte existe porque em todo commit seria proibitivo.
  - **Quantas esteiras ele tem hoje**: `grep -n 'roda_suites' .claude/hooks/release-gate.sh`. Cada uma existe porque um tipo de suíte estava caindo no vão entre os globs D e F.
  - 🔴 **A esteira `scripts/test_*.py` é nova em 2026-08-09, e o buraco que ela fechou tinha três suítes vermelhas dentro.** O gate rodava só as `.sh` de `scripts/` — as `.py` de lá **não tinham cobrador nenhum**, e ficaram vermelhas por dias sem nada acusar. O sintoma que denunciou não veio de um commit barrado: veio da corrida de 2026-08-08, em que **as mesmas quatro conferências reprovaram nas cinco ondas seguidas**. Suíte sem cobrador não fica vermelha em lugar nenhum que alguém olhe — ela só reaparece como trabalho repetido.
  - **A esteira `plugins/*/lib/test_*.sh` cobre o outro vão**: o D varre `lib/test_*.py` e o F varre `hooks/test_*.sh`; suíte **shell dentro de `lib/`** não casava com nenhum dos dois. Foi o que aconteceu com a do resolvedor de skill, que o `scripts/suites_orfas.py` acusou como órfã **no dia em que nasceu**.
  - ⚠️ **Ele é o único que reprova por AUSÊNCIA de arquivo**: `❌ GLOB VAZIO` dispara quando um padrão deixa de casar qualquer coisa, *"suíte renomeada ou apagada deixaria o gate verde sem rodar nada"*. É a mesma asserção de quantidade de `.github/workflows/portability.yml`. **É também o que torna renome de suíte uma mudança de duas pontas**: a rodada de 2026-08-09 renomeou `test_sovai_gate.sh` → `test_motor_gate.sh` e `test_sovai_skill.{sh,py}` → `test_sprint_skill.{sh,py}`, e são os globs — não os nomes — que continuam casando.

  **Régua durável, e ela é a lição do J inteiro: glob de cobrador é a superfície mais fácil de furar sem sintoma.** Suíte que nenhum glob casa não fica vermelha, não fica verde — fica ausente, e ausência não tem cor. Quem mede isso de fora é `scripts/suites_orfas.py`; quando ele acusar uma órfã, o conserto é uma esteira nova aqui, não um lembrete.

⚠️ **Dois checks varrem o repo inteiro, e os dois pelo mesmo motivo**: o alvo deles não aparece em diff nenhum. O `O` porque `.claude/plans/` é gitignorado; o `Q` porque cópia de trabalho parada não é arquivo rastreado. Recortar por arquivo tocado deixaria os dois calados para sempre.

⚠️ **D e F são por plugin TOCADO, não por repo.** Um commit que só mexe no `bootstrap` roda exatamente `plugins/bootstrap/lib/test_*.py` e `plugins/bootstrap/hooks/test_*.sh` e mais nada. **Plugin sem suíte não é plugin sem teste: é plugin cujos checks D e F estão desligados.**

Bloco de saída literal quando algo viola:

```
🚧 release-gate (pedro-plugins) BLOQUEOU o commit:
<violações>

Conserte e commite de novo. (Gate mecânico: .claude/hooks/release-gate.sh)
```

### 5.3 Contrato dos hooks — as 6 propriedades

Quem mede é `scripts/hook_contract.py`; quem cobra é o check E. As seis propriedades, copiadas da docstring do medidor [confirmado]:

1. **canal de saída** — como o hook fala (bloqueia? informa? só loga?). Os três canais de bloqueio coexistem e **não** foram normalizados: `exit 2`, `permissionDecision:"deny"`, `decision:"block"` — *"Não normalizo: só meço."*
2. **cap anti-loop** — quem bloqueia tem teto de devoluções, e a chave do teto é **por sessão** (`SESSION_SCOPED`).
3. **kill-switch** — dá pra desligar sem editar o arquivo.
4. **binário fixo** — caminho absoluto de ferramenta (`/opt/homebrew/bin/…`) é achado de gravidade **high**: some fora do Mac com Homebrew e o hook cai no fail-open em silêncio.
5. **fail-open** — guarda a ausência das ferramentas que usa (`EXTERNAL_TOOLS = ("jq", "python3", "node", "graphify")`).
6. **o NOME diz quando roda e se barra** — regra `R6`, nova nesta rodada. O molde é `<evento>-<verbo>-<assunto>.<sh|py>`: o prefixo é o evento em que o script está **registrado**, e o verbo declara o poder. Verbos que barram: `barra`, `exige`, `trava`, `recusa`. Verbos que só avisam: `avisa`, `anota`, `mede`, `lembra`, `resume`, `sincroniza`, `colhe`, `abre`. ⚠️ **O verbo não é decorativo: é conferido contra o canal MEDIDO no script**, então um `-avisa-` que sai com `exit 2` reprova igual a um nome fora do molde. Um script registrado em dois eventos passa se o prefixo casar com **um** deles. O defeito que a motivou está no comentário: *"`scope-cop.sh`, `mark-work.sh` e `delivery-audit.sh` são o mesmo problema: pra saber quando cada um roda e se ele trava o agente era preciso abrir os três"*.

⚠️ **A R6 é a razão de o número de achados ter explodido — e a maioria é DÍVIDA DECLARADA, não regressão.** Sem baseline, o medidor devolve **47 achados (45 alta · 2 média)** neste run, quase todos `R6-*` em hooks que já existiam com o nome antigo. Como o check E só barra o que **piorou** contra `.claude/hook-contract.baseline.json`, o commit passa — a regra vale para hook novo, e os velhos entram quando forem renomeados.

O próprio script se declara falível [confirmado, citação literal]: *"⚠️ **Isto é grep sofisticado, não verdade.** O script diz ONDE OLHAR."* E a escolha de calibração tem direção declarada: *"Detectar um cap que não existe é o erro CARO … Detectar de menos só gera um falso alarme que a conferência derruba."*

**Os kill-switches de hoje**, derivados mecanicamente (`grep -rhoE '\$\{[A-Z_]+_GATE:-[01]\}' plugins/*/hooks/*.sh | sort -u`) [confirmado]: `ASKQ_GATE`, `BOOTSTRAP_DEPS_GATE`, `BRANCHES_GATE`, `DOC_AUTORAL_GATE`, `DOC_GUARD_GATE`, `GAUNTLET_GATE`, `GRAPHIFY_GATE`, `HANDOFF_GATE`, `LINT_GATE`, `ORGANISM_GATE`, `PLAN_DOC_GATE`, `SCOPE_COP_GATE`, `SHIP_GATE`, `SOVAI_GATE`, `VISUAL_GATE` — **quinze**. Os dois novos são `GAUNTLET_GATE` (o gate de `Agent` do gauntlet) e `BOOTSTRAP_DEPS_GATE` (o `sessionstart-deps.sh` compartilhado). Os hooks Python usam a mesma ideia com outra grafia, e hoje são **quatro**: `PROSE_CEILING=0`, `FORMA_RELATO=0`, `REGUA_RELATO=0` e `ARTEFATO_REGUA=0` (§1.17).

**O marcador que desarma um falso-positivo do medidor de colisão** [confirmado, costura verificada nos dois lados]: `conformance.py:check_hooks_duplicados` só conta como "disputante" o hook que **bloqueia**, e um script pode se declarar avisador com o comentário literal `# conformance: default-warn`. Hoje quem carrega a marca é `plugins/graphify-guard/hooks/pretooluse-graphify-guard.sh` (*"o caminho de deny existe, mas só com GRAPHIFY_DENY=1"*), e `plugins/graphify-guard/hooks/test_graphify_guard.sh` testa a presença dela [confirmado, os dois lados existem hoje].

**Estado do contrato neste run** [confirmado, executado]:

```bash
python3 scripts/hook_contract.py --baseline .claude/hook-contract.baseline.json --fail-on high
# → 1ª linha: "Contrato dos hooks — N registros, M scripts distintos"
#   Nenhum achado. Todos os hooks batem com o contrato.   (rc=0 nesta rodada)
python3 scripts/hook_contract.py --scripts | grep -c .    # os scripts de produção, sem as suítes
```

⚠️ **Registro e script são números diferentes, e nenhum dos dois vai escrito aqui**: o mesmo script registrado em dois eventos conta duas vezes como registro e uma como script. Os dois caem numa fusão de plugins — a rodada de 2026-08-09 tirou três `hooks.json` do repositório e juntou o conteúdo deles em um. **Números de contrato só são utilizáveis junto do comando que os produziu.**

Sem baseline os achados vivos são quase todos `R6` — a regra de nome recém-nascida, que reprova o nome de quase todo hook antigo —, e estão todos congelados no retrato. Os de gravidade que **não** são `R6` continuam sendo o `R1-cap-ausente` em `ship/pre-deploy-test-check.sh` e os dois `R5-sem-failopen` [confirmado, `--json` desta rodada]. ⚠️ **Renome de hook mexe no retrato**: `pretooluse-sovai-motor.sh` virou `pretooluse-motor-arma.sh` nesta rodada, e é o nome — não o conteúdo — que a `R6` julga.

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
- **Mas medir no texto não é escopo: quem delimita é o turno.** O teste de relato dizia *como* julgar e nunca *quando*, então o juiz rodava em todo fim de turno — 463 chamadas em 9 dias por um veredito de uma palavra. `usou_visual()` fecha o escopo antes do modelo: só o turno que passou pelo `/visual` é julgado. **Gate que só sabe reconhecer o objeto certo gasta em tudo que se parece com ele.**
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

**Onde cada família de suíte mora, e quem a roda no commit** — a contagem sai do `ls`, nunca de um número escrito aqui:

```bash
ls plugins/*/lib/test_*.py    | wc -l   # ← glob do check D
ls plugins/*/hooks/test_*.sh  | wc -l   # ← glob do check F
ls _shared/test_*.py          | wc -l   # ← glob do check D2 (só quando o commit toca _shared/)
ls scripts/test_*.sh          | wc -l   # ← esteira 2 do check J
ls scripts/test_*.py          | wc -l   # ← esteira 3 do check J, NOVA em 2026-08-09
ls plugins/*/hooks/test_*.py  | wc -l   # ← esteira 1 do check J
ls plugins/*/lib/test_*.sh    | wc -l   # ← esteira 4 do check J
ls .claude/hooks/test_*.sh    | wc -l   # ← sem cobrador: é a suíte do próprio gate
```

✅ **O vão que sobrava encolheu para um arquivo.** Na passada anterior três famílias inteiras rodavam só à mão: as `.py` de `scripts/`, as `hooks/test_*.py` e as `lib/test_*.sh`. As três viraram esteira do check J (§5.2). **A que continua descoberta é `.claude/hooks/test_release_gate.sh`** — e a ironia é a de sempre: é a suíte do próprio gate de commit, então o gate não roda o teste que o cobre.

🔴 **A prova de que "roda à mão" não é cobertura veio de dentro.** As `.py` de `scripts/` incluem os cobradores de portabilidade e de contrato — e **três delas ficaram vermelhas por dias** sem que nada acusasse, porque nenhum glob as alcançava. O sinal não apareceu num commit barrado: apareceu numa corrida de 2026-08-08, em que **as mesmas quatro conferências reprovaram nas cinco ondas seguidas**. Régua durável: **suíte cuja execução depende de alguém lembrar é suíte cujo resultado ninguém conhece.**

⚠️ **Não há lista de suítes escrita aqui, de propósito.** Nome de suíte muda de pasta quando um plugin é fundido — a rodada de 2026-08-09 moveu a família inteira de documentação e de motor para dentro do `project-skills`, e renomeou `test_sovai_gate.sh` → `test_motor_gate.sh` e `test_sovai_skill.{sh,py}` → `test_sprint_skill.{sh,py}`. **O inventário é o `ls` do bloco acima; o veredito é rodar.**

⚠️ **Duas grafias de "verde" convivem no repo, e isso importa pra quem lê o exit code.** A maioria imprime um placar (`N passou · 0 falhou`); as duas do `plan_state`/`cobertura` imprimem só `OK` no fim, com um `ok <descrição>` por asserção acima. As duas formas saem 0 quando verdes — mas **só a primeira permite ver, no log, que o número de casos não caiu**.

⚠️ `plugins/guardrails/hooks/test_setup_skill.sh` leva minutos — é a única do repo que não roda em segundos; não foi executada nesta rodada.

Rodar tudo:

```bash
for t in plugins/*/lib/test_*.py plugins/*/hooks/test_*.py scripts/test_*.py _shared/test_*.py; do
  python3 "$t" || echo "RED: $t"; done
for t in plugins/*/hooks/test_*.sh plugins/*/lib/test_*.sh scripts/test_*.sh .claude/hooks/test_*.sh; do
  bash "$t" || echo "RED: $t"; done
```

**As disciplinas de teste que este repo cobra**, todas com o sítio que as prova:

- **Teste E2E não-tautológico.** R9/R10 de `test_plan_gate.sh` escrevem o sentinel **rodando o hook escritor de verdade**, nunca recalculando a chave à mão — *"Recalcular a chave à mão aqui foi exatamente o que mascarou o bug de path na 1ª rodada."*
- **Par escritor↔leitor precisa de um teste que rode OS DOIS programas.** `test_conformance.py` roda o hook com `CLAUDE_CONFIG_DIR` num `mktemp`, exige que o log nasça **dentro** dele e só então roda o `conformance.py` [confirmado — a suíte tem função dedicada ao juiz, `teste_juiz_de_forma_mudo`, com os quatro casos: nunca executou · fail-open por juiz sem resposta · parado há mais de 24h · não cobra de quem não instalou o bootstrap].
- **Sabotagem da allowlist.** `test_askq_lint.py` esvazia `NOMES_PROPRIOS` e reafirma que aí *"GitHub"* barra — um caso "GitHub passa" sozinho seria satisfeito também por uma régua quebrada que não pega nada.
- **Verde por fail-open não conta como verde.** `test_bootstrap_hooks.sh` não aceita o exit code do juiz sem conferir o motivo no log: `grep -q '"motivo": "julgou"'` — *"fail-open por juiz mudo aprova tudo: so vale como verde se ele REALMENTE julgou"* [confirmado, citação literal].
- **Teste de hook de detecção precisa distinguir os dois `exit 0`.** No gate do ship, "não detectou deploy" e "detectou e a suíte passou" são ambos 0; a suíte resolve com um fixture cujo alvo de teste falha de propósito, e aí o exit code responde uma pergunta só.
- **Prosa que dá ordem operacional pode ser testada — e ela também apodrece.** `plugins/handoff/lib/test_handoff_skill.py` trata a `SKILL.md` do handoff como código: extrai os blocos ```` ```bash ```` do markdown (com `textwrap.dedent`, *"o bloco como quem copia recebe"*), **executa** o comando prescrito contra um plano de fixture e confere que ele imprime `pronto` e `pendencia` de verdade; depois lê a prosa e cobra que ela mande **copiar** esses campos, não redigi-los. É o mesmo princípio do `visual_page.py` (*"prosa apodrece"*) aplicado a instrução que o modelo vai seguir. [confirmado — docstring e execução]
- **Suíte que DERIVA o inventário só enxerga as grafias que conhece — e a exclusão que ninguém atribui é regex vazia.** `scripts/test_sem_jq.sh` classifica cada hook em classe A (jq só formata) ou B (jq decide) varrendo o texto dos `.sh`. Dois furos medidos em 2026-08-09, e ambos passavam por verde: (1) `$VENDORADOS` era usado em dois `grep -vE "/($VENDORADOS):"` **sem nunca ter sido atribuído** — a exclusão de biblioteca vendorada que a prosa prometia era um filtro que casava tudo; hoje ela é derivada de `ls _shared/*.sh`. (2) A varredura conhecia duas formas de ler o payload (o `jq` cru e o `hj_campo` do `hook-json.sh`) e era **cega à terceira**, Python embutido dentro do `.sh` — e reconhecer só `data.get("x")` ainda deixava invisível quem escreve com default, com aspas simples ou com colchete, de modo que as quatro grafias tiveram que entrar juntas. **Régua durável: derivador que classifica por FORMA de escrita mede o que ele sabe procurar, não o que existe** — quando a medição casa com o esperado, confira se o filtro está mesmo filtrando antes de comemorar. [confirmado, executado nesta rodada: `bash scripts/test_sem_jq.sh` → `verde`, com `hooks de produção: 43 · classe B: 35 · classe A: 5`]

---

## 7 · Gotchas

### Hooks & plugins

- ⚠️ **Hook de plugin vai em `hooks/hooks.json` (subpasta), NUNCA na raiz.** Na raiz é ignorado em silêncio e `validate` passa mesmo assim — o `conformance.py:check_juiz_rodou` repete o aviso no texto do conserto [confirmado].
- 🔴 **Hook que EXISTE mas não está no `hooks.json` nunca dispara, e nada acusa.** Medido nesta sessão com o `stop-regua-relato.py`. `validate` passa, não há log, e `claude plugin details` mostra `Hooks (N)` contando **eventos**, não scripts — script novo num evento já povoado não mexe no N. Prove pelo `hooks.json`, nunca pela existência do arquivo (§1.17).
- ✅ **`hooks/test_*.py`, `lib/test_*.sh` e `scripts/test_*.py` já têm cobrador** — as três eram vãos entre os globs D e F e hoje são esteiras do check J (§5.2). A única suíte ainda descoberta é `.claude/hooks/test_release_gate.sh`.
- 🔴 **`hooks.json` que aponta para script inexistente NÃO é pego pelo `claude plugin validate`.** Quem pega é `scripts/test_paths_normalize.sh` (o passo 7 da suíte: para cada `hooks.json`, resolve `/hooks/<nome>.<sh|py>` contra `plugins/<plugin>/hooks/` e reprova o que não existe). Aconteceu em 2026-08-09: mover `sessionstart-plan.sh` do `visual` para o `project-skills` deixou o comando órfão no `hooks.json` do `visual`. **`validate` verde não é prova de que o hook roda** — o comando é uma string, e string que aponta pra nada falha em silêncio na máquina de quem instalou.
- 🔴 **Fusão de plugin exige reapontar QUATRO superfícies, e três são silenciosas.** Medido na rodada de 2026-08-09, ao fundir três plugins dentro do `project-skills`:
  1. **`scripts/sync-shared.sh`** — o mapa `SPECS`. Destino morto acusa `DRIFT`, mas o conserto reflexo (`sync-shared.sh` sem `--check`) faz `mkdir -p` e **ressuscita a pasta do plugin extinto**; destino novo que faltou não acusa nada (§3).
  2. **`CLAUDE_STATUSLINE_FORWARD`** em `plugins/bootstrap/config/settings-defaults.json` — ele resolve o caminho do plugin **pelo nome**, dentro do cache (`…/plugins/cache/pedro-plugins/<plugin>/…`). Nome errado ⇒ o `if [ -f … ]` cai no `else` e a barra segue perfeita, sem o elo (é o §1.14 outra vez). ⚠️ **E o `~/.claude/settings.json` da máquina NÃO é reescrito pelo `bootstrap` sozinho** — o default novo só chega a quem rodar o setup de novo.
  3. **`hooks.json` do plugin que RECEBE** — fundir dois arquivos soma os registros, e o aviso de dependência (`resolve-plugin.sh bootstrap hooks/sessionstart-deps.sh`) costuma existir nos dois: se as duas linhas entrarem, o `SessionStart` cospe o mesmo aviso duas vezes.
  4. **O catálogo** (`.claude-plugin/marketplace.json`) — **esta é a única que `claude plugin validate` pega.**

  **Régua durável: a lista de superfícies de uma fusão não se lembra, se deriva.** Procure o nome morto em todo formato que o repositório lê — `grep -rn '<nome-morto>' --include='*.json' --include='*.sh' --include='*.py' --include='*.md' .` — e trate cada acerto como candidato, inclusive comentário. **Um recorte de escopo com o nome morto vira check inerte, não check vermelho** (foi o que aconteceu com o check G, §5.2).
- ⚠️ **Hook novo não entra na sessão em curso.** `stop-prose-ceiling.py` registra o teto no topo: *"como todo hook de plugin, so carrega no SessionStart, entao sessao ja aberta no momento da instalacao fica descoberta ate o proximo /clear"* [confirmado].
- ⚠️ **MCP tools só entram no catálogo em SESSÃO NOVA** [relatado — medição reportada nesta rodada, não reproduzida aqui]. Igual ao hook acima: o `vision` expõe `see_image` via `.mcp.json` (§2.9), mas adicionar/recarregar o MCP no meio da sessão conecta o servidor sem pôr a tool na lista do modelo — o Claude tenta `Read`, falha e desiste. Precisa de sessão nova.
- ⚠️ **`exit 0` + stderr é mudo em PreToolUse/PostToolUse.** Use JSON no stdout (§1.2).
- ⚠️ **Estado global entre sessões é bug, não simplificação.** Já mordeu o context-guard e o scope-cop; os dois consertos são o mesmo (§1.5).
- ⚠️ **Nunca canonicalize path na chave de um sentinel** (§1.6).

### Regex de detecção em hook de gate

- Fronteira de palavra antes de todo verbo, senão constatação vira ordem (§1.7).
- Âncora de posição-de-comando, senão menção em `git commit -m "…"` dispara o gate (§1.8).
- Prefixo de lançador **enumerado**, nunca "qualquer palavra antes" — senão a âncora deixa de existir.
- 🔴 **Mas se o alvo é um comando, tokenize e leia o subcomando em vez de casar a forma** — o prefixo enumerado do release-gate deixou passar quatro formas comuns e disparou numa que não commita (§1.8, §5.2).
- **Gate não pode barrar o artefato que ele mesmo manda gerar.** O gate do `ExitPlanMode` contava o veredito de fase (`feedback-item pt-phase`) da página de aprovação como "decisão sem prova" e bloqueava exatamente a saída de `plan_state.py page --mode approve`, que o texto de conserto dele manda rodar. E o exemplo de JSON que ele ensinava era recusado pelo `init`, que exige `requisito` e `pronto` em toda tarefa nova. **Todo texto de conserto de um gate precisa ser executado pelo teste dele** (`plugins/visual/hooks/test_exitplan_gate.sh` → `OK (12 checks)`).
- Toda liberação precisa de revogação (`--com-doc` no plan-escape).

### Release

- ⚠️ **Bump em toda mudança e espelho no marketplace** — o gate avalia **staged ∪ tracked-modificados**, então mudança solta em OUTRO plugin bloqueia o seu commit [confirmado, `FILES` do release-gate].
- ⚠️ **Plugin novo entra em três arquivos** — e quem cobra o terceiro é o `conformance.py`, depois do commit (§5.1).
- ⚠️ **`author` tem que ser objeto** no `marketplace.json`; string é rejeitada pelo `validate` [relatado; o estado atual é consistente — os dois `author` presentes hoje são objeto, verificado neste run].
- 🔴 **O release-gate só existe para commit feito pela ferramenta Bash** (`matcher: "Bash"`). Commit por outro caminho não o dispara e nem precisa de `--no-verify` pra isso. **Bump esquecido não deixa rastro** — quem quiser saber se aconteceu tem que reconstruir commit a commit.
- 🔴 **Cobrador de CONTAGEM não pega NOME errado, e o número certo dá a impressão contrária.** O README afirmava a quantidade certa de plugins desligados de fábrica e nomeava dois errados; o check K passava verde e quem instala ligava o plugin errado. Toda afirmação que é `<número> + <lista>` precisa das duas conferências — a segunda entrou em `readme_counts_check.py:_confere_nomes` (§5.2).
- ⚠️ **Isenção de gate se escreve como token declarado, nunca como operador afrouxado** — o `autopsia_check.py` afrouxou o `>` para deixar passar `<run>` e abriu passagem para `<plugin visual>` (§5.2). `public-ok:`, `r8-ok:` e `vaza-ok:` são a forma certa: isentam a linha nomeada, com motivo escrito.
- ✅ **O furo que fez 7 de 9 commits passarem sem bump era o GATILHO, e ele foi consertado** (§5.1, §5.2): o `grep` na forma do comando deixava passar `env FOO=1 git commit`, `(git commit)`, `bash -c "git commit"` e `VAR=x git commit`. Hoje o comando é tokenizado e o subcomando do git é lido. **Detecção que casa forma de comando é gate desligável por acidente.**

### Código compartilhado

- ⚠️ **Editar `_shared/` sem rodar `scripts/sync-shared.sh`** deixa as cópias vendoradas defasadas (quantas, o comando do §3 responde). Fix nasce em `_shared/`, nunca na cópia.
- ⚠️ **Número que dois documentos repetem não pertence a documento nenhum** — vira JSON com servidor e check que barra a cópia. É o contrato R8 (§3.1), cobrado pelo check A2; isenção `r8-ok: <motivo>` na linha.
- ⚠️ **Plugin que só emite texto de hook também precisa da cópia da régua** — o `.sh` chama `regua_texto.py` pela linha de comando, e o plugin instalado só enxerga a própria pasta (§3).
- 🔴 **Comando de `SKILL.md` que aponta `plugins/<irmão>/lib/…` funciona no repositório e falha na instalação** — cada plugin ganha pasta própria no cache. O par é `resolve-plugin.sh` vendorado **na pasta da skill** + chamada pelo NOME do irmão (§3).

### Skills de documentação

- ⚠️ **`CURRENT_GEN` e os markers das skills andam juntos** — o check G existe porque o checklist manual já falhou uma vez. ⚠️ **Hoje o recorte de escopo dele aponta para um plugin extinto e o deixa inerte** (§5.2): o corpo do check já lê `plugins/project-skills/`, só a porta de entrada ficou em `plugins/project-doc/`.
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
python3 _shared/r8_tiers.py check              # contrato R8 sem cópia carimbada (§3.1)
python3 _shared/test_regua_texto.py            # a régua compartilhada (glob do check D2)
bash    scripts/test_paths_normalize.sh        # hooks.json apontando pra script que existe

# 3b. fundiu, extinguiu ou renomeou um plugin? as QUATRO superfícies (§7)
grep -rn '<nome-morto>' --include='*.json' --include='*.sh' --include='*.py' --include='*.md' .

# 4. commit — o release-gate roda os checks sozinho e sai 2 se algo violar
#    (quantos são: grep -oE '^[[:space:]]*# [A-Z][0-9+C]* · ' .claude/hooks/release-gate.sh)

# 5. hook novo? confirme que ele carregou (e lembre: só vale na PRÓXIMA sessão)
claude plugin details <nome>@pedro-plugins     # → "Hooks (N)"  ⚠️ N conta EVENTOS, não scripts
# dois hooks no mesmo evento não mudam o N — para provar um hook NOVO, compare o arquivo:
diff ~/.claude/plugins/cache/pedro-plugins/<plugin>/<versão>/hooks/hooks.json \
     plugins/<plugin>/hooks/hooks.json
python3 plugins/bootstrap/lib/conformance.py   # → desvios de máquina, inclusive guarda mudo
```
