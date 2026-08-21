---
generated: 2026-08-16
generated-commit: 7793362
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
  - plugins/bootstrap/hooks/hooks.json
  - plugins/bootstrap/lib/conformance.py
  - plugins/context-guard/hooks/context-guard-writer.sh
  - plugins/ship/hooks/pre-deploy-test-check.sh
  - plugins/visual/lib/visual_page.py
  - plugins/project-skills/lib/plan_state.py
  - plugins/project-skills/lib/cobertura.py
  - docs/prototipo/FORMATO.md
  - _shared/regua-de-pergunta.md
  - _shared/contrato-familia.md
  - _shared/hook-json.sh
  - _shared/resolve-plugin.sh
  - _shared/sessionstart-deps.sh
  - scripts/desacoplamento_check.py
  - scripts/custo_check.py
  - scripts/fiscal_de_bancada.py
  - scripts/vazamento_check.py
  - scripts/plano_vs_codigo.py
  - scripts/readme_counts_check.py
  - scripts/suites_orfas.py
  - scripts/anti_slop_inventario.py
  - scripts/cobertura_visual_check.py
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
  - plugins/project-skills/lib/test_sidecar_prototipo.py
  - scripts/test_custo_check.py
  - plugins/project-skills/skills/sprint/references/motor.js
  - plugins/project-skills/lib/test_motor_js.py
  - plugins/visual/hooks/test_exitplan_gate.sh
  - plugins/handoff/lib/test_handoff_skill.py
  - .claude/hooks/test_release_gate.sh
  - plugins/slides/lib/test_md2deck.py
doc-sig: pedro-plugins/release-gate.sh@gen=3.8#b67a8d9e
---

# Patterns & Gotchas

Convenções deste marketplace. Tudo aqui é regra lida no código desta rodada, não estilo sugerido.
Rótulos: **[confirmado]** = li o arquivo ou rodei o comando nesta rodada · **[inferido]** = deduzido, não testado · **[relatado]** = veio de comentário/registro no próprio código.

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

**A direção segura muda por gate** [confirmado]:

- `green-cache.sh` → o lado seguro é **MISS** (roda a suite de novo), nunca HIT.
- `doc-detect.sh:doc_staleness` → o ternário é `fresh|stale|unknown`, e a borda de erro cai em **`unknown`** (fail-LOUD). Fingir "fresco" é o único resultado proibido.
- `pretooluse-plan-gate.sh` → o fail-open cobre **só** a borda de infra (sem `jq`, sem raiz resolvível, `doc-detect.sh` ilegível). Determinar que *não há documentação* é evidência concreta ⇒ nega. A guarda `[ -r "$SCRIPT_DIR/doc-detect.sh" ] || exit 0` existe porque um `chmod 000` no helper fazia projeto documentado cair no caso "sem doc" — regressão coberta pelo caso R7 de `test_plan_gate.sh` [confirmado, suíte verde nesta rodada: `bash plugins/project-skills/hooks/test_plan_gate.sh` → `117 passou · 0 falhou`].

⚠️ **Fail-open MUDO é o único proibido — e isso vale também para o hook que lê o payload com Python próprio, sem `jq` e sem a biblioteca comum.** Em 2026-08-09 três hooks que fazem a leitura assim (`plugins/intent-guard/hooks/capture-prompt.sh`, `plugins/handoff/hooks/handoff-completeness-gate.sh`, `plugins/handoff/hooks/sessionstart-ata.sh`) saíam calados quando faltava `python3`; hoje os três chamam `hj_avisa` do `hook-json.sh` antes de liberar — o que obrigou a vendorar a biblioteca também em `plugins/handoff/hooks/` [confirmado, `sed -n '/^SPECS=(/,/^)/p' scripts/sync-shared.sh | grep 'hook-json.sh'` traz a linha do handoff; `bash scripts/sync-shared.sh --check` → `OK: cópias vendored idênticas a _shared/`]. **Ter leitor próprio dispensa a biblioteca para LER, nunca para AVISAR** — quem cobra é `bash scripts/test_sem_jq.sh` (*"todo hook da classe B avisa quando não há leitor nenhum"*).

🔴 **Esse cobrador ficou VERMELHO em 2026-08-09 e o conserto rendeu duas lições de naturezas diferentes.** A primeira era defeito de código: `FAIL classe B sem canal de aviso (sairia calado): plugins/gauntlet/hooks/sessionstart-lembra-missao.sh` — hook que decide pelo payload e saía mudo quando não há leitor, exatamente o que o parágrafo acima proíbe. Consertado com a guarda de `jq`/`python3` + `hj_avisa` que o vizinho `pretooluse-gauntlet.sh` já tinha. **A suíte fez o trabalho dela: o hook novo nasceu fora da regra e ela acusou.**

✅ **A segunda não tinha conserto de código, e virou uma régua: número medido não mora em doc AUTORAL.** Os outros três `FAIL` só diziam que `.claude/docs/jq-pontos-de-decisao.md` congelava três contagens que a medida de hoje desmentia. O doc tem `authored-by: human`, e o invariante do `/doc-touch` proíbe re-projetá-lo — então o cobrador exigia a mão de um humano para um dado que a máquina mede em milissegundos, e ficava vermelho a cada hook que nascia. O próprio comentário da suíte já nomeava a dor: *"o retrato ficava vencido e a suíte vermelha, num documento autoral que ninguém pode reescrever automaticamente"*. A saída foi a regra de desacoplamento da casa aplicada ao par inteiro — **o doc passou a carregar o COMANDO em vez do número, e a suíte passou a IMPRIMIR o retrato em vez de cobrá-lo** [confirmado — `bash scripts/test_sem_jq.sh` → `retrato de agora — produção: 41 · classe B: 36 · classe A: 5` seguido de `verde`]. **Régua durável: cobrar de um humano a atualização de um número que um comando deriva é fabricar vermelho recorrente.** O que continua cobrado é a LISTA, e por um motivo que se checa: cada linha dela diz o que se perde sem `jq`, e isso nenhum comando deriva — hook novo na classe B ainda reprova até ganhar a sua linha, que é conteúdo faltando, não número vencido.

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

**Hooks Python existem, e a lista sai do comando, nunca de um número escrito aqui** [confirmado — `find plugins -path '*/hooks/*' -type f -name '*.py' ! -name 'test_*'` devolve **dois** nesta rodada]:

```
plugins/guardrails/hooks/pretooluse-artefato-regua.py
plugins/visual/hooks/stop-anuncio-sem-acao.py
```

🔴 **Eram cinco até 2026-08-09; os três de `Stop` do `bootstrap` saíram do disco a pedido do dono** (§1.17, §5.6), e com eles saiu a maior parte do que esta seção media. Dos dois que sobraram, o de `Stop` escreve em stderr **só** no caminho que sai 2 — que num `Stop` é o canal que devolve o texto ao modelo; o de `PreToolUse[Edit|Write]` usa o canal estruturado (`permissionDecision:"deny"` no stdout), porque em `PreToolUse` stderr com `exit 0` é mudo. O uso está certo; o que quebra é a **auditoria** deles (§5.3).

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

Nos hooks Python o cap é o mesmo desenho com outra grafia — um arquivo-contador por `sha1(session_id + texto)`. 🔴 **Os dois arquivos que carregavam este trecho literal saíram do disco em 2026-08-09** (§1.2), então o bloco abaixo é **histórico**, não ponteiro; o que sobrevive dele é o desenho, e o parente vivo mais próximo é `plugins/visual/hooks/stop-anuncio-sem-acao.py`, que chaveia o estado por `sha1` do `cwd` em `ANUNCIO_ACAO_STATE` [confirmado, li a linha]:

```python
MAX_BLOQUEIOS = 2
chave = hashlib.sha1((str(sid) + texto).encode()).hexdigest()[:16]
contador = ESTADO / chave
n = int(contador.read_text()) if contador.exists() else 0
if n >= MAX_BLOQUEIOS: ...   # desiste
```

O `stop-prose-ceiling.py` explica por que o hash é do texto **inteiro** e não de um prefixo [confirmado, comentário literal]: *"com texto[:200] duas respostas diferentes que comecam igual dividiam o mesmo orcamento — e o output style manda a 1a linha ser estavel, entao a colisao era o caso comum, nao a excecao."*

**Desistir não pode ser silencioso.** Quando o teto de prosa desistia, ele gravava uma linha em `bypass.log`, e o `conformance.py:check_bypass_teto` transformava isso em número visível. 🔴 **As três checagens que liam esses logs foram removidas junto com os hooks** — `grep -oE '^def check_[a-z_]+' plugins/bootstrap/lib/conformance.py` não devolve mais `check_teto_rodou`, `check_juiz_rodou` nem `check_bypass_teto` [confirmado, rodado nesta passada]. A régua continua de pé (§5.4); o par escritor↔leitor que a provava, não.

**Exceção deliberada** [confirmado]: o CASO A do `pretooluse-plan-gate.sh` (projeto com zero documentação) **nega sempre, sem cap** — decisão registrada no cabeçalho do arquivo. O único escape é verbal, via `userpromptsubmit-plan-escape.sh`, e a suíte cobre com o caso `sem doc: nega nas 5 tentativas (sem cap de nudges)`.

### 1.4 Estado mutável: `~/.claude/`, NUNCA dentro do plugin

O diretório do plugin (`${CLAUDE_PLUGIN_ROOT}`) é **cache reescrito a cada bump de versão** — gravar estado lá o apaga sem aviso. Literal em `_shared/green-cache.sh`:

> Estado em `~/.claude/green-suite/` (NUNCA dentro do plugin — o cache `${CLAUDE_PLUGIN_ROOT}` é reescrito a cada bump de versão).

**A raiz é `${CLAUDE_CONFIG_DIR:-$HOME/.claude}`, não `$HOME/.claude` cru.** Os três lados que li nesta rodada respeitam a env var, e cada um aponta para o outro no comentário [confirmado]:

```python
# plugins/bootstrap/lib/conformance.py
CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", HOME / ".claude"))
# plugins/visual/hooks/stop-anuncio-sem-acao.py
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
- `CLAUDE_DIR/state/anuncio-acao/` — `stop-anuncio-sem-acao.py:ESTADO`, com **variável própria** `ANUNCIO_ACAO_STATE` [confirmado, li a linha]
- `CLAUDE_DIR/state/intent-guard/olhado` — `ledger.py:furos_da_regua`. Um plugin lendo o estado que **outro** plugin escrevia (`state/prose-ceiling/bypass.log` e `state/forma-relato/batidas.log`), e por isso ele copia a expressão de raiz literalmente igual à dos escritores. ⚠️ **Não confundir com `$HOME/.claude/intent-guard/mode`**, que é outro diretório, de outro dono: um é kill-switch, o outro é marca de leitura.

🔴 **E este par virou o exemplo mais limpo do §1.14 ao contrário: o ESCRITOR foi removido e o LEITOR ficou.** Os dois logs que `furos_da_regua` abre eram escritos pelos hooks de `Stop` do `bootstrap`, que saíram do disco em 2026-08-09; a função continua no repositório, apontando para caminhos que ninguém mais alimenta [confirmado — `grep -rn 'furos_da_regua' plugins/*/lib/*.py` só devolve `plugins/intent-guard/lib/ledger.py:furos_da_regua` e o consumidor dela no mesmo arquivo; nenhum arquivo do repositório escreve mais em `bypass.log` ou `batidas.log`]. **O que a salva de mentir é uma decisão de desenho, não sorte**: o `except OSError: continue` traz o comentário *"log ausente ≠ zero furo — quem conta as fontes é `fontes`"*, então o leitor devolve "não sei" em vez de "zero furo". **Régua durável: leitor que trata ausência de fonte como zero vira mentira no dia em que o escritor morre — e o escritor morre sem avisar o leitor.**

**Por que um juiz que chama binário autenticado tem variável de estado separada** [relatado — o comentário literal vivia em `stop-forma-relato.py`, hoje removido]: *"estado com var propria: isolar o teste via CLAUDE_CONFIG_DIR tirava a credencial do `claude -p` junto, e o juiz passava a aprovar tudo por fail-open."* Régua durável: **hook que chama binário autenticado não pode ter o isolamento do teste amarrado ao mesmo diretório da credencial.**

**Kill-switch = interruptor de uma linha, e ele nunca nasce ligado por padrão.** No shell é env var `<NOME>_GATE=0` (§5.3); no único hook Python que ainda o traz é `ARTEFATO_REGUA=0`. Ele não aparece em `plugins/bootstrap/config/settings-defaults.json` [confirmado, li o `env` do arquivo, que hoje traz só `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`, `CLAUDE_CONTEXT_THRESHOLD` e `CLAUDE_STATUSLINE_FORWARD`], então **o guarda nasce ligado** — que é a premissa que o teto de prosa registrava no histórico:

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

Hoje a regra é `plan_state.py:pendencia_viva`, chamada pelos dois — e, desde que a largada do
`/sprint` passou a varrer pendência antes de disparar, pelos três, sempre por importação. A docstring dela carrega o
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
roda `bash -c '. …/lib-doc-mark.sh && doc_marca …'` e compara com a saída do módulo Python;
`python3 plugins/project-skills/lib/test_doc_load.py` → `50 passou · 0 falhou` nesta rodada].
**Régua durável: reimplementação cross-linguagem só é legítima com o teste de identidade
junto** — sem ele, o que existe são duas receitas que ninguém sabe se ainda concordam.

🔴 **E a divergência apareceu justamente onde o teste não olhava: o fim de linha do Windows.**
O mesmo documento chega lá com `\r\n`, e o Python corta o `\r` sozinho ao separar as linhas
(`splitlines()`), enquanto o `awk` do shell não cortava — um byte a mais por linha, duas marcas
para um texto só, e de quebra o `---\r` deixava de ser reconhecido como cerca do frontmatter.
O conserto é uma linha em `doc_corpo` (`{ sub(/\r$/, "") }` antes de qualquer outra regra), e a
lição de método é a que interessa: **teste de identidade só vale se rodar com o dado do OUTRO
sistema também** — hoje `test_doc_load.py` grava o documento em CRLF de propósito e exige o
mesmo número das duas receitas [confirmado, caso *"documento em CRLF: as duas receitas continuam
dando a mesma marca"*; verde no Windows na CI de portabilidade, run `31860821914`, job
`checks (windows-latest)` → `ok  1.1s  plugins\project-skills\lib\test_doc_load.py`].

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

### 1.7a A mesma expressão em outro CAMPO é outra expressão — reuso exige reconferir o vocabulário

Medido em 2026-08-10, no `gauntlet` 0.10.0 → 0.10.1. `MEDIDA_NO_NOME`
(`plugins/gauntlet/lib/fecho_check.py`) nasceu para recusar medida em **nome de eixo** —
texto curto, nomeado, vocabulário de CSS — e a v0.10.0 a reusou, verbatim, sobre a **prosa
livre** do veredito (`gap` e `frase` do juiz e do diretor). Errou nos dois sentidos ao
mesmo tempo:

```
"1 em cada 3 cartões repete o mesmo gesto"   → RECUSADO como medida   (em = português, não unidade)
"a nossa pesa 4 MB, metade do alvo"          → passou batido          (lista parava em kB)
```

O primeiro é o mais caro, e é o que o §1.7 já ensina com outra roupa (*"falso-positivo que
treinaria o usuário a desligar o gate no primeiro dia"*): aqui ele travava o fecho da missão
até alguém reescrever a frase de um juiz que estava certo. O segundo é a doença voltando uma
ordem de grandeza acima — peso e tempo eram justamente o material da régua de 18 medidas que
a versão existia para banir. O conserto separa as duas classes de unidade: letra ambígua
(`em`, `s`) só vale **colada** no dígito, unidade inequívoca vale com ou sem espaço, e a
lista alcança `MB`, `GB`, `min` [confirmado — `python3 plugins/gauntlet/lib/test_fecho_check.py`
→ *"tudo verde"*, com os três casos novos do bloco *"O NÚMERO SÓ ENTRA PELA MÃO DO DONO"*].

**Régua durável: quando um padrão migra de campo, o intuito viaja e o VOCABULÁRIO não.
Identificador não tem preposição; prosa em português tem — e `em`, `s`, `a`, `há` são
palavras antes de serem unidades. Reuso de regex pede o mesmo par de testes do §1.7: um que
prove que ela pega o que deve, e um que prove que ela NÃO pega o legítimo do novo campo.**

### 1.8 Prelúdio, portabilidade e exit code

- **`set` varia por TIPO de script, de propósito** [confirmado]. Build usa `set -euo pipefail` (`scripts/sync-shared.sh`); gate usa `set -uo pipefail` sem o `-e` (`.claude/hooks/release-gate.sh`); e `plugins/guardrails/hooks/scope-cop.sh` **não declara `set` nenhum** (`grep -c '^set ' plugins/guardrails/hooks/scope-cop.sh` → 0). Motivo: com `-e`, um hook-trava abortaria no meio de uma checagem e viraria bloqueio acidental — o oposto do fail-open. ⚠️ **E a SUÍTE do gate largou o `pipefail` em 2026-08-20, de propósito** (`.claude/hooks/test_release_gate.sh`): quase toda asserção dela é `printf '%s' "$out" | grep -q …`, o `grep -q` sai no primeiro casamento e fecha o cano, o `printf` leva SIGPIPE — e com `pipefail` o status da pipeline vira o do `printf`, ou seja, a asserção **reprova por ter acertado cedo demais**. Falha ora num check ora noutro, conforme quem termina primeiro. **Régua: em pipeline cuja pergunta é do comando da DIREITA, `pipefail` mede o mensageiro.** ⚠️ **E o mesmo cano quebrou de novo em 2026-08-21, no outro remédio possível**: `plugins/project-skills/hooks/test_stop_doc_touch.sh` era a única suíte que caía sob carga (1 de 155) — sob CPU disputada o `grep -q` fecha o cano antes de o `printf` terminar, o `printf` morre com 141 e o check vira 0, **reprovando um comportamento que estava certo**. Ali o conserto foi tirar o escritor em vez de desligar o `pipefail`: os 13 checks passaram a casar por here-string (`grep -q … <<<"$M"`), que não tem processo à esquerda para morrer, e os dois checks da régua trocaram `printf | sed` por substituição do próprio shell. **Os dois caminhos valem; o que não vale é ler o veredito de um cano como veredito do programa.** A mesma suíte desliga também o freio de relógio do portão (`PORTAO_DEADLINE_S=0`): o prazo existe para o gate recusar em voz alta quando o harness o mata em produção, e numa bancada com a máquina ocupada ele derrubava os checks do fim — o que se mede ali é o VEREDITO do portão, nunca quanto ele demora.
- **Binário se resolve por `command -v`, nunca por caminho absoluto** [confirmado, `scope-cop.sh`]: `JQ="$(command -v jq)"`, `PY="$(command -v python3)"`, `CLAUDE_BIN="$(command -v claude 2>/dev/null)"`, com o comentário *"Sem path hardcoded de app específico — isso amarrava o hook a uma máquina/app."* No Python o equivalente é `shutil.which`, hoje em `conformance.py:check_ferramentas_externas`. ⚠️ **`command -v` sozinho responde a pergunta errada** — ver §1.8a, primeiro item.
- **`.cwd` ausente não pode apagar o gate** [confirmado, `pre-deploy-test-check.sh`]: era `[ -z "$CWD" ] && exit 0`, hoje é `[ -z "$CWD" ] && CWD="$PWD"`, com a justificativa *"falha VISÍVEL (bloqueio com mensagem) … é estritamente melhor que gate invisível"*.
- **Âncora de posição-de-comando na detecção**, e prefixo **enumerado**, nunca "qualquer palavra antes" [confirmado, `pre-deploy-test-check.sh:CMDPFX`]:

```bash
CMDPFX='([A-Za-z_][A-Za-z0-9_]*=[^[:space:];&|]*[[:space:]]+|(sudo|nohup|env|time|exec|command)([[:space:]]+-[^[:space:];&|]+)*[[:space:]]+)*'
```

  O comentário nomeia o contrapeso: *"senão a âncora deixa de existir e a menção volta a disparar (o contrapeso está na suíte: `echo sudo ./deploy.sh` e `git commit -m "sudo ./deploy.sh quebrou"` seguem 0)"* [confirmado — `test_pre_deploy.sh` nesta rodada: `pre-deploy-test-check: 105 ok, 0 falhas`].

- 🔴 **E aqui está o limite da âncora: prefixo enumerado só cobre o que alguém lembrou de enumerar.** O `release-gate.sh` usava a mesma ideia (`(^|[;&|]|&&)[[:space:]]*git[[:space:]]+.*commit`) e **quatro formas legítimas passavam caladas** — `env FOO=1 git commit`, `(git commit …)`, `bash -c "git commit …"` e `VAR=x git commit` — enquanto `git log --grep commit` disparava à toa. O conserto trocou o casamento de forma por **parse**: o comando é quebrado em tokens (o split inclui `(`, `)`, `;`, `&`, `|`, `<`, `>`, aspas e crase) e o subcomando do git é lido pulando as opções globais e os valores delas (§5.2). **Quando o alvo é um comando de verdade, tokenize e leia o subcomando; regex de forma é para texto, não para linha de comando.** [confirmado — `bash .claude/hooks/test_release_gate.sh` → `OK (45 checks)` nesta rodada, com um caso por forma]

### 1.8a Os quatro defeitos que só aparecem no OUTRO sistema

Todos foram achados de uma vez em 2026-08-10, com a esteira vermelha em Linux e Windows e
verde no macOS. O padrão comum: **o comando não falha — ele responde outra coisa**, e o
script segue com um valor plausível e errado.

- 🔴 **`command -v` mede presença; o que importa é execução** [confirmado, issue #1]. O
  Windows instala um `python3` de mentira, da loja da Microsoft, que responde uma
  propaganda em vez de rodar. O arquivo existe, `command -v` aprova, o guard passa e o hook
  só quebra na chamada real. O resolvedor certo tenta rodar: `hj_py` (`_shared/hook-json.sh`)
  percorre `python3` e `python` e só aceita quem responde a `--version`; o equivalente para
  o interpretador é `bash_posix` — hoje em `_shared/bash_posix.py`, vendorado
  (`test_conformance.py` o importa da cópia local). Medida de hoje: `grep`ando os hooks de
  produção, **nenhum** decide por presença — 16 usam o resolvedor.

- 🔴 **`stat -f` não falha no GNU: ele imprime e SÓ ENTÃO sai com erro** [confirmado,
  `graphify-detect.sh`]. O encadeamento `stat -f … || stat -c …` somava as duas saídas, a
  data virava texto de duas linhas, o TSV quebrava no meio e `cut -f3` devolvia `stale`
  colado com a linha seguinte — o alerta de grafo defasado sumia em **todo** Linux. A regra
  que sobra: **encadear com `||` só é seguro quando o lado que falha não escreve no stdout**;
  quando escreve, ordene GNU primeiro e **valide o formato do resultado** antes de aceitá-lo.

- 🔴 **O Windows codifica a saída em cp1252, e `→` não existe lá** [confirmado,
  `conformance.py`]. O programa morria de `UnicodeEncodeError` antes de escrever o JSON, e
  quem o chamava recebia stdout vazio — o teste acusava "não devolveu JSON" sem dizer por
  quê. Todo Python que imprime não-ASCII e é lido por outro processo reconfigura os canais
  para UTF-8 na entrada do `main()`. Reproduz-se em qualquer máquina com
  `PYTHONIOENCODING=cp1252`.

- 🔴 **No Linux cada argumento isolado tem teto de 128 KB** (`MAX_ARG_STRLEN`), enquanto o
  macOS aceita ~1 MB [confirmado, `intent-guard/hooks/test_hooks_capture.sh`]. O caso que
  existia para provar que "prompt grande não se perde" mandava 500 KB por `argv` e morria de
  `Argument list too long` — só no Linux. Conteúdo grande vai por **stdin**; `printf` é
  embutido no shell e não passa por essa porta.

- 🔴 **`chmod(0o755)` não cria bit de execução no Windows** [confirmado, mesma revisão]. Uma
  fixture que montava um juiz falso no PATH ficava invisível para o hook, o hook fazia o que
  devia (sem juiz não há veredito: fail-open) e o teste lia isso como "o hook não bloqueou"
  — **reprovando hook certo por fixture quebrada**. O conserto é a fixture se medir antes de
  cobrar: `test_conformance.py:juiz_falso_visivel` pergunta ao mesmo shell se o juiz é
  enxergado, e o caso **pula declarando** quando não é. Mesma família do `bash_posix`: gate
  que não consegue medir diz que não mediu, nunca reprova por omissão.

### 1.8b A campanha do Windows: seis classes, e o que cada uma ensina

Entre 2026-08-10 e 11 a esteira ficou vermelha em quinze pushes seguidos, **sempre só no
Windows**. Não era um defeito com quinze sintomas: eram seis classes distintas, cada uma
escondida atrás da anterior. O padrão que une todas: **a API existe no POSIX e some no
Windows, e o programa que a chama não trata a ausência como caso possível.**

- 🔴 **`${0%/*}` não corta barra invertida — 33 hooks estavam MORTOS.** <!-- acopla-ok: 33 é a medição HISTÓRICA do conserto (commit 7ae0d40), não uma contagem viva; o número de hoje sai do comando no fim do bullet --> Lá o `$0` chega como
  `D:\a\…\hooks\scope-cop.sh`; o corte no último `/` não acha nada, o `$0` inteiro vira o
  "diretório", o hook não encontra o leitor de JSON ao lado de si e **desiste em silêncio** —
  fail-open por desenho, hook desinstalado na prática. Todo hook instalado em toda máquina
  Windows, sem julgar nada, sem nada acusar. O conserto normaliza o `$0` com a mesma receita
  que o `hooks.json` já usava no `CLAUDE_PLUGIN_ROOT` (`tr '\\' /`). Quem cobra hoje é
  `scripts/test_paths_normalize.sh`, e ele tem **os dois lados**: prova que a normalização
  funciona sob `sh`/`dash`/`bash`/`zsh`, e reprova quem voltar ao padrão velho. Confira com
  `for f in $(grep -rln '${0%/\*}' plugins/*/hooks/*.sh .claude/hooks/*.sh); do grep -q "tr '\\\\\\\\' /" "$f" || echo "$f"; done`
  — hoje devolve vazio [confirmado nesta rodada].

- 🔴 **`import fcntl` no topo do módulo derruba o módulo INTEIRO.** O `fcntl` é POSIX e não
  existe no Windows: o `import` estourava antes de qualquer função ser definida, e com ele
  **todo comando do intent-guard** — não o travamento, o plugin. A regra que sobra vale para
  qualquer dependência só-POSIX: **`import` de módulo de sistema vai em `try`, com o caminho
  alternativo escrito**, nunca no topo nu. A trava ganhou a segunda implementação (diretório
  criado com `os.mkdir`, atômico em qualquer sistema de arquivos).

- 🔴 **Ausência de função é `AttributeError`, e `except OSError` não pega.** `signal.SIGKILL`,
  `os.killpg` e `os.getpgid` não existem no Windows. Os três chamadores tinham fallback
  escrito — `except OSError: p.kill()` — que **nunca era alcançado**, porque o erro é de outra
  família. Proteção contra ausência de API se escreve com `getattr(mod, "NOME", alternativa)`
  ou `except (OSError, AttributeError)`; `try` que só espera falha de execução não cobre
  função que não nasceu. No Windows o `SIGTERM` já é encerramento forçado, então o segundo
  golpe do lixeiro é o mesmo sinal.

- 🔴 **`os.path.dirname("D:\\")` devolve `"D:\\"` — para sempre.** A busca da raiz do projeto
  subia diretório por diretório e parava em `home` ou em `"/"` literal; na raiz de um drive
  do Windows nenhum dos dois chega, e o laço **girava sem fim**. Isso pendurou o job da
  esteira por mais de dez minutos, três vezes seguidas, e foi lido como defeito da trava do
  ledger — dois consertos foram feitos no lugar errado antes de alguém medir. O que agrava:
  o temp do runner é `C:\Users\RUNNER~1\…` (nome curto de oito caracteres), que **nunca**
  casa com o `home` `C:\Users\runneradmin`, então a caminhada passava direto pela única
  parada que existia. **A raiz se testa por `os.path.dirname(d) == d`**, que vale nos dois
  mundos; comparar com `"/"` é premissa de POSIX escrita como se fosse universal.

- 🔴 **Ler texto sem declarar a codificação é apostar no console de quem roda.** O Windows
  abre arquivo em cp1252, e todo acento do repositório chega corrompido — ou estoura. A
  varredura fechou a classe em produção: hoje são **0** chamadas de `open()` de texto sem
  `encoding=` fora das suítes, contra 24 ainda nas suítes (ASCII, então não quebram — mas a
  classe não está fechada lá). Conte com o mesmo AST que produziu esse número:
  `python3 -c "import ast,glob;…"` sobre `plugins/*/lib/*.py`, `plugins/*/hooks/*.py`,
  `_shared/*.py` e `scripts/*.py` [confirmado nesta rodada — 164 arquivos varridos]. O mesmo
  vale para a saída de `subprocess`: `text=True` sozinho herda a codificação do sistema — e
  **essa metade não estava fechada**, porque a varredura contava só `open()`. Em 2026-08-15 o
  cano do caderno do `intent-guard` (`hooks/capture-prompt.sh`) mandava o pedido do usuário por
  `text=True` sem `encoding=`: saía em cp1252, o `ledger.py` do outro lado — que reconfigura os
  canais dele para UTF-8 — recebia byte inválido, o `read()` estourava e o `except` de fail-open
  engolia. **Nada era gravado, exit 0, nenhum sinal**; a suíte do Windows morreu no primeiro
  grep (`ledger.jsonl: No such file or directory`). Regra que sobra: **`encoding=` explícito nos
  DOIS lados do cano**, não só em quem lê. E em 2026-08-21 a classe mordeu de novo, pelo lado
  que ninguém tinha fechado — **o PAI que LÊ**: o filho já escrevia UTF-8 (`PYTHONIOENCODING`
  do job da esteira), mas o pré-check da largada abria o cano de leitura na codificação do
  sistema, e no Windows isso é cp1252 — `UnicodeDecodeError` no primeiro acento da saída da
  suíte [confirmado, commit `bb24bb7`, `plugins/project-skills/lib/precheck_largada.py`]. A
  forma FECHADA da regra, medida em runs do CI de 21/08: **`text=True` SEMPRE acompanhado de
  `encoding="utf-8", errors="replace"`** — o `errors=` existe porque byte estranho derrubar o
  medidor inteiro é pior que um `�` no relatório. Hoje a varredura de
  `text=True`/`universal_newlines=` sem `encoding=` devolve **3** ocorrências em produção
  (`_shared/grao-de-modulo.py:_arquivos`, `scripts/anti_slop_inventario.py:universo`,
  `scripts/tetos_rodadas_inventario.py:universo`), as três lendo `git ls-files` — só caminhos, então
  não quebram, mas a classe não está fechada ali [confirmado nesta rodada — mesmo AST, 115
  arquivos fora das suítes; a contagem sai do AST, nunca deste número].

- 🔴 **Teste que compara caminho por texto reprova caminho certo.** No Windows o
  `os.path.expanduser("~/.claude/intent/")` sai com `/` e o `os.path.join` do programa devolve
  `\` — o mesmo diretório, escrito de dois jeitos, e o `startswith` nega. **Comparação de
  caminho passa por `os.path.normpath` nos dois lados**, sempre. Foi o último defeito da
  campanha, e o mais barato de confundir com defeito de produto.

  🔴 **E a mesma classe em PRODUÇÃO tem sintoma pior: chave de retrato que muda de texto muda
  de IDENTIDADE.** Medido nos runs do CI de 2026-08-21: o `who` do cobrador do artigo 8 e o do
  contrato de hooks entravam na chave do retrato com o separador do sistema — no Windows
  `plugins\x` não casa com o `plugins/x` gravado, e **dívida ACEITA virava "achado novo"**;
  no desduplicador do contrato, o mesmo script resolvido por dois caminhos virava dois textos
  e **a cópia única virava duas** (run `32496524302`). Conserto padrão, nos dois cobradores:
  **toda chave que se grava, compara ou desduplica nasce de
  `os.path.relpath(...).replace(os.sep, "/")`** (`scripts/hook_contract.py:_rel`,
  `scripts/artigo8_check.py:varre`; o resolvedor ganhou `os.path.normpath` —
  `hook_contract.py:resolve_script`, commit `3385424`). O mesmo gesto vale para **caminho
  EMBUTIDO em comando ou ambiente de shell POSIX**, que só entende `/`:
  `raiz.replace(os.sep, "/")` antes de entrar no comando
  (`plugins/project-skills/lib/precheck_largada.py`, commit `42cc412`) [confirmado, li as
  linhas].

**A lição de método, e ela é maior que as seis:** cada conserto revelava o próximo, porque a
suíte para no primeiro erro. Quinze pushes a três minutos cada é o preço de descobrir de um
em um o que uma varredura estática acha de uma vez —
`grep -rn "signal\.SIG\|os\.getuid\|os\.killpg\|os\.getpgid\|os\.fork\|import pwd\|os\.statvfs"`
sobre todo o Python do repositório levou segundos e fechou as três últimas classes juntas.
**Quando o sintoma é "só falha no outro sistema", varra a classe antes de consertar a
ocorrência.**

⚠️ **Job sem `timeout-minutes` transforma travamento em job de seis horas.** Enquanto a busca
de raiz girava, o job não falhava — ele *continuava*, e a leitura de fora era "ainda
rodando". `.github/workflows/portability.yml` corta em 45 min — o teto subiu de 30 porque o maior job
legítimo, o do Windows, foi medido subindo a cada rodada (23m42s → 25m01s → 26m28s, os
números estão no comentário do próprio arquivo) e a folga tinha caído para três minutos: teto
abaixo do job legítimo deixa de acusar travamento e passa a causar um. Travamento tem que ter
cor. [confirmado — `grep -n timeout-minutes .github/workflows/portability.yml` → `45`]

### 1.8c As classes de defeito de portabilidade — defeito, causa e cobrador

Cada classe daqui tem **causa medida**, não suspeita: alguém rodou, viu o número errado e
escreveu por quê. Classe cuja causa ainda é palpite **não entra** — fica declarada no fim,
para não virar régua antes de ser verdade.

- 🔴 **O lar fingido que não finge nada no Windows** [confirmado, `_shared/lar-fingido.md`].
  **Defeito:** a suíte troca `HOME` por um diretório de mentira, roda o hook, e ele escreve no
  lar REAL da máquina — sujando o estado do dono. O teste segue verde, porque ele confere o que
  o hook respondeu, nunca onde o arquivo caiu. **Causa:** o `expanduser` do Python decide o lar
  nesta ordem — `USERPROFILE`, depois `HOMEDRIVE`+`HOMEPATH`, e só então `HOME`. Com
  `USERPROFILE` intacto, o `HOME` fingido é ignorado. **As quatro variáveis andam juntas ou não
  andam.** **Cobrador:** `_shared/test_lar_fingido.py` — confere as duas metades da receita
  (`lar_fingido.py` e `lib-lar-fingido.sh`, vendoradas) e **varre as suítes** atrás de quem
  atribui `HOME=`, `USERPROFILE=` ou `HOMEPATH=` fora dela; caso legítimo isenta a linha com
  `lar-fingido: ok <motivo>`. Régua: `python3 _shared/test_lar_fingido.py` → `12 passou · 0
  falhou` [confirmado nesta rodada]. Corolário que veio junto: **o lar fingido nasce FORA do
  projeto de teste** — dentro dele, a cascata de `resolve-dir.sh` para cedo e o hook cai no
  caminho errado. A receita fechou verde **no Windows de verdade**, não só no varredor: as
  oito suítes da família adotaram-na (commit `172703f`) e os runs filtrados `31960762453`
  (as três Python) e `31960895417` (as quatro de shell + o próprio cobrador) saíram verdes
  em `windows-latest` em 2026-08-16 [confirmado, jobs lidos nesta rodada].

- 🔴 **O `/tmp` do Git Bash não é o temporário que o Python nativo enxerga** [confirmado,
  runs `31761090697` (vermelho) → `31890249824` (`ok 8.4s`), commit `ca721e9`]. **Defeito:**
  a suíte cria a pasta de trabalho com `mktemp -d` pelado, escreve o arquivo por um lado e o
  programa não o acha pelo outro — `FileNotFoundError` em quatro checks de
  `test_entrada_no_arranque.sh`, só no Windows. **Causa:** o `mktemp -d` devolve `/tmp/x`, que
  existe **dentro do shell**; o `python3` do Windows resolve esse mesmo texto como `C:\tmp\x`,
  que não existe. E o Git Bash só traduz caminho que vai como **argumento** — embutido no texto
  de um `python3 -c "... '$PASTA/arquivo' ..."` não há o que traduzir, e é por isso que a mesma
  suíte tinha checks verdes ao lado dos vermelhos. **Cobrador:** `_shared/lib-tmpdir.sh ::
  td_tmpdir` (cascata `TMPDIR`/`TMP`/`TEMP` + `cygpath -m`), vendorado por
  `scripts/sync-shared.sh` nos consumidores, e `scripts/test_tmpdir.sh`, que varre os hooks
  atrás de quem ainda escreve `/tmp` literal. Régua: `bash scripts/test_tmpdir.sh` → `VERDE —
  TMPDIR honrado pelos hooks` [confirmado nesta rodada]. **Receita:** `mktemp -d` vira
  `mktemp -d "$(td_tmpdir)/nome-XXXXXX"`.

- 🔴 **O `bash` cru que o Windows entrega é o do WSL, não um shell que roda**
  [confirmado, commits `a6c85c8` e `e2b7734`, doc em `_shared/bash_posix.py`]. **Defeito:**
  qualquer chamada pelada — `subprocess.run(["bash", …])` ou `shutil.which("bash")` — resolve
  `System32\bash.exe`; em runner sem distro ele responde *"Windows Subsystem for Linux has no
  installed distributions."* **em UTF-16 e com código 0**. Em teste, isso reprova código certo
  pelo interpretador ("não imprimiu nada" e "não existe" ficam indistinguíveis); em produção
  foi pior: nove chamadas guardavam `out.stdout.strip()` como caminho do plugin irmão, e a
  reclamação do WSL **virava o caminho**. **Causa:** o critério "estar no PATH" não mede o que
  importa — três tentativas de arrumar pelo PATH do runner falharam (`GITHUB_PATH` não vence o
  `System32`; `export PATH=/usr/bin:$PATH` idem). A régua é o candidato **RESPONDER**.
  **Cobrador:** `_shared/bash_posix.py` — prova cada candidato com um `echo VIVO` (o `which`,
  depois os caminhos do Git Bash) e devolve `None` quando nenhum responde; quem chama **pula
  declarando**, nunca reprova por omissão. Vendorado nos consumidores (a contagem sai do mapa:
  `sed -n '/^SPECS=(/,/^)/p' scripts/sync-shared.sh | grep -c '::bash_posix.py'`), drift pego
  pelo check A do vendoring. Em 2026-08-21 a régua ganhou o corolário do `shell=True`: no
  Windows ele cai no **cmd.exe**, onde `;` não separa comandos e não há `grep` — o `_roda` do
  pré-check devolvia "verde" para uma esteira vermelha, porque a resposta plausível do shell
  errado virava o dado [confirmado, commits `42cc412` e `f742a7e`]. **Comando de shell POSIX
  roda pelo executável que `bash_posix()` devolveu, nunca por `shell=True` nem por `"bash"`
  cru** (`plugins/project-skills/lib/precheck_largada.py:_roda`, que também pula declarando
  quando o resolvedor devolve `None`). **Declarado:** não existe varredura que acuse chamada pelada
  NOVA — quem escreve `["bash", …]` hoje só descobre no vermelho do Windows.

- 🔴 **O `ps` do Windows não entrega a lista com argumentos — e o medidor DECLARA que não
  mediu** [confirmado, commit `01040fb`, CI de 2026-08-21]. **Defeito:** a checagem de
  exclusividade do pré-check pergunta `ps -eo pid=,args=`; no runner do Windows o comando
  falha ou volta vazio, e seguir com a lista vazia responderia "nenhum vizinho" — verde por
  omissão. **Causa:** o `ps` que existe lá não implementa `-eo` com `args=`; não é erro do
  programa, é ausência de instrumento. **Cobrador:** `rc != 0` ou saída vazia vira achado
  ADIÁVEL — *"a vizinhança de processos NÃO foi medida; confere à mão antes de largar?"* — que
  é o Artigo 4 da constituição em código (`plugins/project-skills/lib/precheck_largada.py`), e a
  suíte cobre o caso: *"sem ps utilizável, a passada DECLARA que não mediu a vizinhança"*
  (`test_precheck_largada.py`). Mesma família do `bash_posix` e do `juiz_falso_visivel`
  (§1.8a): quem não consegue medir diz que não mediu, nunca decide por omissão.

⚠️ **A colheita do lixeiro no Windows tem causa medida e conserto BLOQUEADO por falta de dado**
[confirmado em 2026-08-15, run `31890249824`]. Quatro checks de `test_lixeiro_hooks.sh` seguem
vermelhos só lá — **nada é encerrado porque o motor não descobre a pasta de trabalho do
processo**: `lixeiro.py:_carrega_cwds` pergunta ao `lsof`, que não existe no Windows, `cwd_de`
devolve `None`, e `casa` recusa. Reproduz-se aqui com um `lsof` postiço que só sai 1 —
`printf '#!/bin/sh\nexit 1\n' > <rascunho>/lsof && chmod +x <rascunho>/lsof && PATH=<rascunho>:$PATH
bash plugins/lixeiro/hooks/test_lixeiro_hooks.sh` derruba **as mesmas quatro** (macOS com `lsof`:
`26 ok, 0 falhas`). Descartados por medição, não por palpite: o formato do caminho (o `td_tmpdir`
entrou e as quatro continuaram, run `31870181027`), o `$!` do Git Bash (nunca chega ao motor) e
casar pelo TEXTO do comando (o teste vizinho sobe o mesmo `python3 -m http.server 0` em outra
pasta — casar por texto encerraria processo de projeto alheio). **Falta uma segunda fonte de
pasta de trabalho para onde não há `lsof`**, e nem `wmic` nem `tasklist` a devolvem: escrever
leitura de saída de ferramenta sem dado real é o que a régua da casa proíbe.

**Ainda sem causa medida, e por isso fora desta seção** [declarado]: o motor da bancada que
não carrega no node, a divergência entre as duas receitas de `cksum`, os dois caminhos de
binário (`/usr/bin/grep` cravado e binário ausente) e o byte nulo do `ExitPlanMode`. Cada uma
entra aqui **quando** o run que a mediu existir, com o id citado — não antes. ⚠️ **"O ledger que não é achado" saiu desta lista em 2026-08-15**: a
causa foi medida (o cano sem `encoding=` do `capture-prompt.sh`) e está no bullet de codificação
do §1.8b, com o conserto no commit `b1d6f97`.

### 1.9 Chamada interna de LLM tem que se auto-marcar

Gate que invoca modelo dispara os hooks do próprio marketplace de novo, agora com o prompt do juiz. A marca viva hoje é a do intent-guard [confirmado, li o arquivo]:

```bash
# plugins/intent-guard/hooks/capture-prompt.sh
[ -n "${INTENT_GUARD_INTERNAL:-}" ] && exit 0
# quem chama exporta antes: plan-gate.sh, task-checkpoint.sh, delivery-audit.sh
```

🔴 **A segunda marca saiu do disco com o juiz de forma em 2026-08-09** (§1.2), e a distinção que ela carregava vale guardar mesmo sem o código [relatado — comentário literal do arquivo removido]: *"'interno' e desligamento silencioso, '0' e o kill-switch do dono"* — a marca de reentrância e o kill-switch do dono compartilhavam a variável, com valores distintos, e o subprocesso do próprio juiz saía **sem nem registrar batida**, para não poluir a auditoria com execuções que ele mesmo causou.

### 1.10 Sidecar: quem SABE grava ao lado

Padrão de `delivery-audit.sh`, generalizável a todo gate que pergunta agora e lê a resposta depois: o hook cola no prompt do auditor a lista de pedidos vivos **daquele instante** e grava essa lista num arquivo irmão `<artefato>.escopo`, porque o JSON de resposta só existe turnos depois. As três propriedades [relatado — comentários do arquivo, lido por grep nesta rodada]: **grava quem sabe, no instante em que sabe**; **o nome deriva do artefato**, não de sessão nem de timestamp; **ausência é estado legítimo e tem que ser o conservador** (artefato sem sidecar cai no comportamento antigo, que cobra tudo).

O mesmo raciocínio aparecia nos hooks Python de `Stop` como `batidas.log` — o gate registrava o que sabia no instante em que sabia, e o `conformance.py` lia depois. 🔴 **Os dois lados desse par foram removidos em 2026-08-09** (§5.4); o padrão fica, o exemplo não roda mais.

---

### 1.10a A NORMA que um cobrador lê tem que viajar no clone

**Novo em 2026-08-16.** O formato do sidecar de protótipo é lei escrita em
`.claude/docs/prototipo/FORMATO.md` — um arquivo rastreado no git, dentro da mesma pasta
que guarda os arquivos do protótipo. A discussão que o originou fica na spec
(`.claude/specs/concepcao-prototipagem.md` §2b, fora do git); a lei fica no clone. Em
divergência entre os dois, o `FORMATO.md` ganha, e a spec diz isso por escrito.

O motivo é mecânico, não estético: quem cobra o formato é
`plugins/project-skills/lib/test_sidecar_prototipo.py`, e ele **abre esse arquivo** —
`FORMATO` é montado com `os.pardir` a partir do próprio `__file__` e conferido com
`os.path.isfile` [confirmado — constante `FORMATO` e os `check(...)` do arquivo, lidos nesta rodada]. Norma
que mora só na spec ignorada pelo git some no clone de terceiro e o cobrador reprova sem ter
o que ler. As três propriedades: **a lei viaja onde o cobrador procura**; **a casa é uma só**
(caminho fora de `.claude/docs/prototipo/` é erro de formato, não gosto — é o que a
conferência por onda sabe olhar sem procurar); **ausência REPROVA, não pula** — a suíte não
tem caminho de escape para o arquivo faltando.

A bancada não confere só a presença: ela monta o exemplo escrito no `FORMATO.md` num lar
fingido (receita de `_shared/lar-fingido.md`, cópia vendorada em
`plugins/project-skills/lib/lar_fingido.py`), confere campo a campo, confere o `conjunto-sig`
contra o `cat … | cksum` de verdade e confere que trocar uma tela diverge a marca — o teto
verde sai do próprio arquivo: `python3 plugins/project-skills/lib/test_sidecar_prototipo.py`.
É o §2.12 aplicado: exemplo que ninguém executa é prosa, e prosa não reprova.

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

**Terceira sequela, 2026-08-09: o gate sequestrava missão de outra skill, porque o sinal é compartilhado e ele não conferia de quem era.** Três skills do marketplace gravam o **mesmo arquivo** `~/.claude/andamento/ativo-<sid>`, cada uma com o próprio nome na primeira linha — quem escreve o quê se confere nos `SKILL.md` delas (`grep -rn 'ativo-\$' plugins/*/skills/*/SKILL.md`). O gate do motor lia só a existência do arquivo:

```bash
SINAL="$ESTADO/ativo-$SESSION"
[ -f "$SINAL" ] || exit 0          # ← nada olhava a linha 1
```

O efeito medido: acender o sinal do `gauntlet` armava o gate do `sprint`, e o `gauntlet` ficava proibido de despachar os próprios juízes — que é o mecanismo inteiro dele, numa skill que existe justamente porque juiz esquecido já custou uma sessão de 14 horas. A correção é o leitor conferir o dono antes de agir (`DONO=$(head -n 1 "$SINAL")`, `[ "$DONO" = "sprint" ] || exit 0`), e não renomear o arquivo: o compartilhamento é de propósito, porque a barra de status lê a linha 1 de qualquer um deles. `[confirmado — dois checks novos em test_motor_gate.sh, um por skill vizinha, e a suíte inteira verde: 26 checks]`

**A régua durável: arquivo de estado compartilhado entre plugins precisa de DONO declarado no conteúdo, e de leitor que o confira.** Nome de arquivo por sessão isola sessão de sessão — não isola skill de skill. A suíte do gate escondia o defeito porque criava o sinal vazio (`: > "$ESTADO/ativo-$SID"`), e sinal vazio nunca é o que o produto grava: **teste que fabrica o estado de um jeito que a produção não fabrica é teste que não vê a colisão.**

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

As quatro portas, e a direção segura de cada uma [confirmado — o esqueleto do `SKILL.md` do motor e o executável `plugins/project-skills/skills/sprint/references/motor.js`, que desde 2026-08-09 carregam as mesmas quatro guardas]:

- **decompositor morto** → `break`. Sem decomposição não há o que executar; o que as rodadas anteriores construíram continua valendo.
- **revisor morto** → `continue` com blocker. A direção segura é **não** declarar `built`: revisor que não respondeu não aprovou nada.
- **confirm-pass morto** → `break` com blocker. É a única segunda checagem quando não há `/qa-loop` adiante; sem ele ninguém conferiu.
- **executor morto** → `.filter(Boolean)` **nos dois lados** (paralelo e sequencial). Filtrar só o paralelo deixava `null` entrar em `results` e estourar no revisor — e a tarefa **sumia do relato** em vez de reaparecer em `missingTasks`, que é o caminho que a manda de volta pro decompositor.

**Régua durável: em motor de agentes, toda chamada que pode devolver `null` precisa de porta declarada — e a porta nunca é "declara pronto". Falha de infra tem que degradar a missão, nunca fabricar aprovação.**

### 1.13b Instrução em prosa que vira código a cada disparo envelhece em rascunho

O esqueleto do motor de `/sprint` sempre viveu no `SKILL.md` e era **copiado** no disparo. O que
não vivia lá eram os prompts dos papéis e os schemas de resposta: eles estavam descritos em
prosa — tabela de papéis, campos obrigatórios, o que cada schema recusa — e quem disparava os
**traduzia em JavaScript na hora**. Medido em 2026-08-09, comparando o esqueleto com o script
realmente disparado:

```
esqueleto no SKILL.md : 947 linhas
script disparado      : 1016 linhas
  580 copiadas do esqueleto
  436 traduzidas da prosa: 18 construtores de prompt + 14 schemas
```

O defeito não é o custo da tradução — é onde ela pousa. O resultado foi guardado no diretório
de rascunho da sessão, sobreviveu ao rename do plugin (`sovai` → `sprint`) e **rodou depois
dele com o `meta.name` morto na tela**. A varredura do rename cobria `plugins/`, `scripts/` e o
`README.md`; rascunho de sessão não é território de varredura, e cópia velha roda igual — só
carrega o texto errado.

**A correção foi mudar o que é copiado:** o executável virou
`plugins/project-skills/skills/sprint/references/motor.js`, arquivo do plugin, e o disparo passa
o **caminho** dele ao `Workflow` em vez de montar texto. Duas consequências que valem além deste
caso:

- **O que é arquivo do plugin entra em toda varredura** — rename, `grep`, gate de commit, release.
- **A prosa que sobrou vira contrato conferível.** `plugins/project-skills/lib/test_motor_js.py`
  casa o `motor.js` com as três fontes que o definem: as peças nomeadas do esqueleto, a tabela
  `prompt → PAPEL` e a constante de esforço contra `_shared/r8-tiers.json`
  [confirmado — `python3 plugins/project-skills/lib/test_motor_js.py` → `test_motor_js: 196 checagens verdes` nesta rodada; o número cresce com a suíte, o que vale é o comando]. <!-- acopla-ok: saida crua de comando citada como prova, e o proprio texto diz que o que vale e o comando -->

**Régua durável: instrução que alguém traduz em código a cada uso é código sem endereço. Ou ela vira arquivo versionado, ou a cópia de ontem volta amanhã sem nada acusar.**

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

O `.artefato` embute o artefato real num quadro pequeno, e pequeno é a escolha certa: em tamanho natural ele quebra a leitura do documento e empurra a decisão pra fora da tela. O que faltava não era tamanho, era **saída** — não havia como olhar de perto sem sair da página. Desde 2026-08-02 `r_artefato()` emite dois botões, e eles não são redundantes [confirmado — `visual_page.py`; `python3 plugins/visual/lib/test_visual_page.py` → `227 passou · 0 falhou` nesta rodada]:

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

🔴 **REMOVIDO em 2026-08-09, a pedido do dono** — os hooks de `Stop` do `bootstrap` saíram do disco e o array `Stop` do `hooks.json` deixou de existir [confirmado — `git show 251d6ac --stat`]. A lição de padrão abaixo continua valendo; o mecanismo que a ilustrava, não roda mais.

**Novo em 2026-08-03**, e não é redundância. A régua de forma (§2.7) passou a ser cobrada por **dois** hooks, e os cabeçalhos dos dois explicam por que um só deixaria metade descoberta [confirmado, citação literal de `pretooluse-artefato-regua.py`]:

> A rede pega o relatório que eu DIGITO no terminal e nunca vê arquivo; esta porta pega o arquivo e nunca vê o terminal.

- **PORTA — `plugins/guardrails/hooks/pretooluse-artefato-regua.py`** (`PreToolUse[Edit|Write]`). Nega escrever `.md`/`.html` dentro de `.claude/visual/` ou `.claude/reports/` quando o texto sai em prosa corrida. **Alcance deliberadamente estreito**: documentação, código e config ficam fora — *"a régua governa artefato de LEITURA, não todo texto do repositório"*. Kill-switch `ARTEFATO_REGUA=0`, impresso na própria mensagem de recusa. [confirmado — `test_artefato_regua.py` → `artefato-regua: 23 checks ok, 0 falhas`]
- **REDE — `plugins/bootstrap/hooks/stop-regua-relato.py`** (`Stop`). Mede os bullets do relato digitado na resposta. **Divisão de trabalho escrita no arquivo, pra não haver guarda em dobro**: `stop-prose-ceiling.py` cobra o **VOLUME** (quantas linhas), esta régua cobra os **BULLETS** (as linhas que abrem com `•`, `-` ou `*`). Cap `MAX_BLOQUEIOS = 2`, kill-switch `REGUA_RELATO=0`, estado em variável própria `REGUA_RELATO_STATE` (§1.4).

Duas decisões que valem copiar:

- **O perfil sai por DERIVAÇÃO, não por escolha.** A rede usa `pagina` — e o comentário dá o raciocínio: o `regua_texto.py` define esse perfil como *"pagina, relatorio, diagnostico"*, e relato de fim de turno é relatório. **Não** é o perfil `hook`, porque aquele proíbe `**` e crase por causa de um canal que não renderiza markdown, e **o canal do CLI renderiza**. Escolher perfil pelo *nome do hook* teria pego o errado.
- **Fora do alcance, em ambos: bloco de código.** Prova é literal por obrigação — `linhas_de_redacao()` na porta e a mesma exclusão na rede. Medir dentro de ``` reprovaria a saída crua que o artefato existe pra carregar.

🔴 **Gotcha medido nesta sessão: hook que EXISTE mas não está no `hooks.json` nunca dispara — e nada acusa.** O `stop-regua-relato.py` nasceu como arquivo antes de entrar no array `Stop` do `plugins/bootstrap/hooks/hooks.json`; os dois entraram no mesmo commit (`1e59b55`) só porque alguém foi conferir. Não há erro, não há log, `claude plugin validate` passa, e `claude plugin details` mostra `Hooks (N)` **contando EVENTOS, não scripts** — um `Stop` novo no array já povoado não mexe no N. É a mesma família do §1.14 (elo que sai da cadeia sem sintoma), com um agravante: aqui o componente nunca chegou a entrar. **Hook novo se prova pelo `hooks.json`, nunca pela existência do arquivo.**

### 1.18 Estado compartilhado por SESSÃO enquanto quem o usa é por EXECUÇÃO

**Medido em 2026-08-12.** O sinal que anuncia missão de pé é chaveado por sessão
(`~/.claude/andamento/ativo-<sid>`); a reserva de arquivos que o mesmo motor usa é chaveada
por sessão **e** execução (`reservas/<sid>__<motor>.files`). Duas chaves diferentes para o
mesmo ciclo de vida, e a mais grossa ganha na hora de apagar.

O que aconteceu: um motor morreu na largada, o relançamento herdou a sessão, e o
`encerra:barra` do motor morto apagou o sinal do motor vivo. **A barra ficou muda com
trabalho rodando, e o gate que nega despacho de sub-agente por fora desarmou junto** — os
dois leem o mesmo arquivo. Nada acusou; o dono descobriu perguntando.

A conferência que existia **não** pegava: o `encerra` já comparava o **dono** na linha 1
(`sprint` × `qa-loop` × `gauntlet`), o que separa plugins diferentes e **não** separa duas
execuções do mesmo plugin. Guarda certa, granularidade errada.

- **A regra:** estado compartilhado se apaga por **contagem de quem está de pé**, nunca por
  "o último que falou". Quem arma se registra, quem sai se remove, e o estado cai quando a
  lista esvazia. Em `andamento.py`: `arma <sid> <dono> <motor>` e
  `encerra <sid> <dono> <motor>`, com a lista em `motorid-<sid>`.
- **O agravante que vale a lição inteira:** o `motorid-<sid>` **já era apagado em dois
  lugares e nunca era escrito por ninguém** — o desenho previa o registro e a implementação
  não veio. Campo fantasma não dá erro: ele é lido como lista vazia, e a lista vazia
  concorda com "pode apagar". `grep -rn motorid plugins/project-skills/ | grep -v /test_`
  devolvia só as duas linhas que apagavam. **Prefixo em rotina de limpeza sem escritor
  correspondente é sintoma, não sobra.**
- **Consertar a porta não alcança quem já passou por ela.** O `encerra` corrigido evita o
  caso novo e não devolve o sinal que já caiu, nem alcança o motor que morre sem chamar
  encerramento nenhum. Por isso a rede: `ressuscita_sinais`, no mesmo desenho da barra,
  reacende sinal ausente com motor registrado vivo — e a ordem contra `expira_sinais`
  importa (expirar primeiro, para não ressuscitar o que a outra acabou de matar).

## 2 · Python

### 2.1 Stdlib puro, sem exceção observada

Não há `requirements.txt`, lockfile nem venv no repo. Duas varreduras neste run, porque **existe Python em `hooks/` além de `lib/`**:

```bash
grep -rhoE '^(import|from) +[a-zA-Z_][a-zA-Z0-9_]*' plugins/*/lib/*.py _shared/*.py | awk '{print $2}' | sort -u
# achado argparse askq_lint ast auditoria_plano branch_state causa clareza cobertura
# collections contextlib curadoria_features datetime decisoes_estruturais difflib doc_lint
# fcntl fecho_check fio_morto glob graph_map hashlib historico html importlib inspect
# inventario io journal json ledger lixeiro math md2deck medidor organism os
# padroes_vazamento pagina pathlib pattern_check plan_entrada plan_state plano_saida
# proposta random rastreio_etapas re registro regua_audit regua_pronto regua_texto report
# shlex shutil signal sobras string subprocess suite_congela sys tempfile test_verificador
# textwrap time unicodedata varredura visual_page

grep -rhoE '^(import|from) +[a-zA-Z_][a-zA-Z0-9_]*' plugins/*/hooks/*.py | awk '{print $2}' | sort -u
# hashlib importlib io json os pathlib re shutil subprocess sys tempfile time
```

Tudo é stdlib ou módulo-irmão do próprio plugin — **a lista de irmãos passou de 15 para 39** (`achado`, `askq_lint`, `auditoria_plano`, `branch_state`, `causa`, `clareza`, `cobertura`, `curadoria_features`, `decisoes_estruturais`, `doc_lint`, `fecho_check`, `fio_morto`, `graph_map`, `historico`, `inventario`, `journal`, `ledger`, `lixeiro`, `md2deck`, `medidor`, `organism`, `padroes_vazamento`, `pagina`, `pattern_check`, `plan_entrada`, `plan_state`, `plano_saida`, `proposta`, `rastreio_etapas`, `registro`, `regua_audit`, `regua_pronto`, `regua_texto`, `report`, `sobras`, `suite_congela`, `test_verificador`, `varredura`, `visual_page`), e as quatro entradas novas de stdlib desta passada — `ast`, `inspect`, `signal`, `unicodedata` — seguem todas na biblioteca padrão: **nenhuma dependência externa apareceu**. ⚠️ **`importlib` nos hooks é consequência do vendoring, não sofisticação**: `pretooluse-artefato-regua.py` carrega a régua por caminho (`importlib.util.spec_from_file_location` sobre `../lib/regua_texto.py`) porque um hook não tem o `lib/` do próprio plugin no `sys.path` — e se a cópia não estiver lá, ele sai 0 mudo (§1.17). ⚠️ **`cobertura` entrou nesta rodada e o import dele é LOCAL, dentro da função** (`plan_state.py:_requisitos_do_projeto` e `cmd_cobertura` fazem `import cobertura` no corpo, não no topo) — os dois moram na mesma pasta, e o import no topo obrigaria quem só usa `tick` a carregar o módulo do fio. **Por quê:** o plugin é copiado pro cache sem passo de instalação — não existe onde rodar `pip install`. `doc_lint.py` carrega isso na docstring (*"Stdlib-puro."*), `conformance.py` repete no topo (*"Python 3 stdlib apenas — convencao do repo (patterns.md)"*), `askq_lint.py` explica a consequência (*"o plugin é copiado pro cache sem passo de instalação, não existe onde rodar pip install"*), e `visual_page.py`/`md2deck.py` fecham com *"stdlib only (requisito do repo)"* [confirmado, os cinco arquivos].

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
- **Quem calcula não guarda.** `cobertura.py` (o tamanho sai de `wc -l < plugins/project-skills/lib/cobertura.py`, hoje **394** — nasceu com 79) lê, cruza e devolve; a vista "épico › requisito › grupo › tarefa" é **derivada em toda leitura**, nunca gravada — mesmo princípio de `phase_status`, que deriva o estado da fase dos passos porque *"estado duplicado é estado que diverge"*.

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

Três isenções escritas no código, as três por natureza do conteúdo e válidas em **todo** perfil: `evidencia.output` (saída crua é literal por obrigação — parafrasear a prova é o defeito original com outra roupa), `raw_html` (a válvula de layout) e o texto de dentro do bloco `esquema` (legenda de caixa de desenho não vira frase — forçar prosa ali empurraria o autor de volta pro `raw_html`) [confirmado — `visual_page.py:_validate_block`, ramo `esquema`]. Linha de árvore de plano fica fora nos perfis que declaram `arvore_fora`: é gerada por programa, não é redação.

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

⚠️ **O check não distingue produção de SUÍTE, e é isso que o torna útil.** Em 2026-08-09 ele
barrou o repositório inteiro por causa de uma linha de teste: `test_motor_js.py` disparava
`subprocess.run(["node", "--check", MOTOR])` sem `stdin=` nem `start_new_session=`, e o conserto
foi acrescentar os dois [confirmado — `git show 3dd62a5 -- plugins/project-skills/lib/test_motor_js.py`].
Duas coisas caem daí: a régua vale para `subprocess.run` igual a `Popen` (quem tem teto tem filho),
e **suíte que dispara processo é produção do ponto de vista da máquina** — o `node` esquecido por um
teste ocupa a mesma memória que o esquecido por um hook.

⚠️ **E o check varre o repositório INTEIRO, não o que está staged — então dívida alheia barra o
commit de qualquer um.** Aconteceu de novo em 2026-08-10: três disparos das suítes do `bootstrap`
(duas em `lib/test_cfgjson.py`, uma em `lib/test_conformance.py`) tinham `stdin=subprocess.DEVNULL`
e **não** tinham `start_new_session=True`, e barraram um commit que só tocava o `gauntlet`. O
conserto foi o argumento que faltava nas três, com bump do `bootstrap` para 1.17.1 por consequência
[confirmado — `python3 scripts/vazamento_check.py` → *"nenhum disparo de processo pode deixar filho
para trás"*, contra 3 achados antes]. **A metade fácil é a que se esquece**: `stdin=` é a que se
lembra porque o sintoma é visível (o processo trava esperando o terminal), enquanto `start_new_session=`
só falha quando alguém aplica um teto — e aí o neto sobrevive em silêncio.

### 2.11 Dado que vem de arquivo escrito à mão se valida na ENTRADA, nunca onde ele estoura

Medido em cinco rodadas de revisão sobre o cobrador de gasto do `gauntlet` (2026-08-12). O
teto de crédito é lido de `rito.json`, que uma pessoa escreve — então ele pode vir como
texto, lista, número solto, ou não vir. O mesmo `TypeError` foi consertado **quatro vezes**,
sempre no lugar onde ele tinha aparecido daquela vez:

```
1ª  na validação      → estourou depois na impressão do comando
2ª  na impressão      → estourou depois em toda leitura do disco
3ª  na leitura        → estourou antes dela, no primeiro `.get` de quem chamava
4ª  na ENTRADA        → parou
```

O terceiro conserto foi o pior: `--abre` gravava um estado envenenado e, como reabrir é
recusado por outra regra, **consertar o rito não destravava mais nada**. A quarta versão faz
a abertura passar pela mesma validação do rito e não gravar quando recusa, e cada camada se
defende de *não ser bloco* antes de perguntar chave a ela [confirmado — a suíte cobre teto
como texto, como lista e como número, e o bloco `gasto` inteiro não sendo bloco].

**Régua durável: remendo no ponto onde o erro aparece muda o ENDEREÇO do erro, não o erro.
Dado de fora entra por uma porta só, e é nela que se valida — depois disso todo consumidor
confia. E quando o programa recusa, ele não pode ter gravado nada: estado meio-escrito com
recusa por cima é o que transforma um erro de digitação em beco sem saída.**

### 2.12 Teste que passa pelo motivo errado é pior que teste ausente

Da mesma revisão, e é o achado mais caro dela. Um caso novo afirmava *"com o teto estourado
o comando sai 1"*, e passava — mas não pelo motivo escrito:

```
o comando refaz a leitura do provedor
  → em máquina SEM o provedor (as três da esteira), o estado vira `nao-sei`
  → `nao-sei` também sai 1
  → o teste passa mesmo se o ramo do estouro for apagado
  → e QUEBRA numa máquina onde o provedor responde com a conta cheia
```

Ele dava cobertura falsa nos três sistemas e era instável no quarto. O conserto tem duas
partes, e a segunda é a que fecha: **substituir a fonte externa** (aqui, a função que lê o
saldo) e **escrever o contraditório** — com folga o comando sai 0, então o 1 vem do estouro
e não do acaso.

**Régua durável: todo caso cujo resultado dependa de algo FORA do repositório precisa (a)
substituir essa fonte e (b) provar o contrário também. Sem o contraditório, um verde
constante e um verde correto são indistinguíveis — e o ambiente da esteira, onde a
ferramenta externa nunca existe, é exatamente onde o falso verde se instala.**

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
- 🔴 **O vendoring deixou de carregar só PROGRAMA e passou a carregar INSTRUÇÃO.** Parte das fontes é markdown lido pelo modelo — a lista e a contagem de cada uma saem do próprio mapa (`sed -n '/^SPECS=(/,/^)/p' scripts/sync-shared.sh | grep -oE '::[a-z0-9_-]+\.md' | sort | uniq -c`), nunca de um número escrito aqui. **A mais nova é o TRIPÉ da revisão** (`dimensoes-de-revisao.md`, 2026-08-12): o mínimo que toda revisão mede — qualidade, cobertura por finalidade e coerência com a régua —, servido a `/qa-loop` e `/sprint` de uma fonte só. Ela nasceu de um drift consumado: as duas skills descreviam os eixos por conta própria, uma listava seis dimensões e a outra cinco eixos, **nenhuma media cobertura**, e a lista de documentos de régua estava escrita à mão num lado e vinha do `doc_load.py` no outro. A consequência de release é a mesma do código, mas o modo de falhar é pior: uma cópia defasada de `.py` costuma quebrar um teste, enquanto uma cópia defasada de instrução **só faz o modelo se comportar diferente conforme o plugin de entrada**, sem nada ficar vermelho. Quem pega é o check A (`--check` com `cmp -s`), e ele é a única rede.
- ⚠️ **Régua de hook exige cópia mesmo quando quem chama é `.sh`.** Boa parte dos destinos do `regua_texto.py` são plugins que só emitem texto de hook, e o comentário do próprio `SPECS` diz por quê: *"o .sh chama a régua pela linha de comando, e o plugin instalado só enxerga a própria pasta — sem cópia aqui, a régua some em produção"*. Vendorar só quem faz `import` deixaria o gate mudo exatamente nos plugins que mais falam com o dono.
- 🔴 **A regra do NOME vale para a SUÍTE também, e foi ali que ela furou.** `plugins/visual/skills/visual/test_resolve_dir.sh` alcançava `sessionstart-plan.sh` por caminho relativo (`$(dirname $0)/../../hooks/`); o hook mudou para `project-skills` na fusão da família (`1f575e9`) e o teste passou a reprovar **em silêncio** — o bloco caía num `falha "hook ou plan_state.py ausente"` que parecia ambiente incompleto, não regressão. Ele ficou vermelho até 2026-08-10, e o que o revelou não foi ninguém rodar a suíte: foi o motor do `/sprint` passar a **enumerar os testes por comando** em vez de recortar "os diretórios do trabalho da missão" — a rodada 1 daquela corrida rodou 43 testes e a rodada 2 rodou 120, e o vermelho apareceu no meio de um bloco como se fosse da obra. Conserto: o teste procura os dois por `find … -name` a partir da raiz [confirmado — `bash plugins/visual/skills/visual/test_resolve_dir.sh` → `TODOS OS TESTES PASSARAM`, e a suíte inteira fecha 120/120].
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

✅ **As três formas viraram premissa escrita, com cobrador — 2026-08-12.** O que estava disperso em três alertas deste documento agora é a **premissa anti-drift** no cardápio da família (a skill-índice `project-skills`), na forma de tabela: **dado** vira `_shared/<nome>.json` que a casca lê e passa em `args`; **contrato em prosa** vira `_shared/<nome>.md` vendorado, com o `SKILL.md` citando o arquivo em vez de repetir; **coisa que muda sozinha** vira um programa que se roda, nunca a resposta de hoje. A terceira é a que mais se erra, porque a resposta parece estável até o dia em que não é — lista de documento de projeto, de plugin instalado e de skill da família sempre cai nela. E a premissa fecha com a pergunta operacional: *isto que estou escrevendo já está escrito em outro lugar?* Quem a cobra é `scripts/test_dimensoes_de_revisao.py` (oito checagens sobre o cardápio, mais a exigência de que cada consumidor aponte em vez de repetir), porque premissa sem cobrador é intenção — a cláusula que manda em todas, na constituição.

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

1. **Bump em TODA mudança, por UM comando: `python3 scripts/bump.py <plugin>`** (`--minor`, `--major`, `--para X.Y.Z`). Ele sobe o `plugin.json`, espelha o `.claude-plugin/marketplace.json` e a tabela de `architecture.md` no mesmo gesto — a mão esquece o terceiro. É a chave de propagação [relatado — comportamento do harness, não reproduzido nesta rodada]. ⚠️ **O bump roda num comando e o `git commit` noutro**: o gate é `PreToolUse` (§5.2), então ele julga o disco ANTES de o comando Bash executar — `bump.py … && git commit` num comando só é avaliado com a versão velha e barra como `BUMP ESQUECIDO` [inferido do mecanismo do §5.2, não reproduzido nesta rodada].
2. **O espelho `plugin.json` ↔ `marketplace.json` é cobrado pelo check B**, e a tabela por `scripts/test_doc_catalogo_plugins.py` (que tem `--fix`).
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

`.claude/hooks/release-gate.sh`, registrado em `.claude/settings.json` como `PreToolUse` com `matcher: "Bash"` e `timeout: 60`, apontando para `$CLAUDE_PROJECT_DIR/.claude/hooks/release-gate.sh`. <!-- lint:ignore CLAUDE_PROJECT_DIR --> Desde 2026-08-09 ele **deixou de ser o único** hook do projeto: entrou um `SessionStart` → `sessionstart-avisa-cadeia.sh` (10s), que avisa quando o plugin instalado nesta máquina ficou atrás do repositório (§5.2b). Os dois lados da mesma pergunta — o gate barra o commit que rompe a cadeia de entrega, o aviso conta que a máquina já está rodando código velho. [confirmado — `python3 -c "…json.load…"` sobre o settings devolve `['PreToolUse', 'SessionStart']`]

**Dependência invertida:** ao contrário dos hooks de plugin, que preferem `jq` quando ele existe, o release-gate **não usa `jq` uma vez sequer** — faz todo o parse com `python3 -c` [confirmado nesta rodada: `grep -c jq .claude/hooks/release-gate.sh` → **1**, e a única ocorrência é um comentário que fala *sobre* jq, não uma chamada — `grep -n jq` mostra a linha inteira; `grep -c python3` → **38**]. Sem `python3`, ele cai no fail-open de infra e não checa nada.

**Desde 2026-08-10 o caminho de INSTALAÇÃO segue a mesma inversão, e por um motivo medido:** o `jq` não acompanha o Windows nem o macOS de fábrica, e era ele que fazia o primeiro comando do marketplace morrer — `apply.sh` saía 255 e `apply-config.sh` saía 1, deixando a máquina sem configuração nenhuma. As 13 chamadas de `apply.sh`, `apply-config.sh` e `session-sync.sh` viraram `plugins/bootstrap/lib/cfgjson.py`, **um subcomando por programa `jq` que existia** — não uma imitação genérica de `jq`, que seria superfície nova para manter. A escolha entre os dois caminhos foi feita uma vez, no desenho: **um caminho só**, porque dois códigos para a mesma conta divergem com o tempo (a regra do fallback que precisa estar à altura do titular). Quem prova a equivalência é `lib/test_cfgjson.py`, que roda cada subcomando **contra o `jq` de verdade executando o programa original** onde há `jq` na máquina, e contra o valor esperado onde não há — inclusive nas três pegadinhas que separam os dois: `//` tratando `false` como ausente, `unique` que também ordena, e `del` quando o campo é nulo. O `jq` sobrevive só em `snapshot.sh`, que roda apenas com `HAS_SOURCE=1` (existe `~/pedro-plugins/.git`) — fluxo de quem clona o repositório, nunca de quem instala.

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
grep -cE '^# [A-Z0-9-]+ · ' .claude/hooks/release-gate.sh
```

A rodada anterior trouxe **seis de uma vez** — `J`, `K`, `L`, `M`, `N` e `O` —, o maior
salto que o gate já teve; depois dela entraram `P` e `Q`. Todos vêm da mesma frente:
transformar em cobrador mecânico o que antes era artigo escrito na constituição
[confirmado, derivado nesta rodada]:

```bash
grep -oE '^[[:space:]]*# [A-Z][0-9+C-]* · ' .claude/hooks/release-gate.sh | grep -oE '[A-Z][0-9+C-]*'
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

  🔴 **A lente isenta quem o modelo NÃO pode invocar, e a isenção é do mecanismo declarado no arquivo** (2026-08-13). `disable-model-invocation: true` no frontmatter tira a description do contexto do modelo: ela deixa de ser insumo de decisão e vira ajuda de quem digita a barra. Cobrar dessa skill a frase escrita *para o modelo decidir se invoca* é cobrar frase sem leitor — foi assim que as três do `2op` reprovaram tendo o único leitor possível já nomeado na própria description. `varredura.py:_so_do_usuario` lê a marca **dentro do frontmatter** e `sem_situacao` a pula; sem a linha de fecho `---` a marca não vale e a lente continua cobrando, senão bastaria mencionar o campo no corpo para escapar. ⚠️ **A asserção do repo tira as isentas da CONTA, não só da lista** (`test_varredura.py`): dizer *"as 35 declaram situação"* quando três nem são cobradas é o teste passando por isenção em vez de por mérito — hoje ele afirma o número das **cobradas** e nomeia as isentas ao lado. É a mesma família do `public-ok:` e do `r8-ok:`, com uma diferença que importa: aqui a isenção não é um comentário escrito à mão, é um campo que **muda o comportamento real do harness**, então não há como isentar sem pagar o preço.
- **Q · cópia de trabalho parada no disco** — **novo em 2026-08-08**. Roda `python3 scripts/worktree_orfao_check.py` ⇒ `❌ CÓPIA DE TRABALHO PARADA — quem busca arquivo pelo nome acha ela antes do original`. Nasceu de defeito medido: *"14 de 41 marcações do motor rodaram binário que não era o da árvore"* — os agentes procuraram o arquivo pelo NOME e o `find` alcançou as cópias em `.claude/worktrees/`; sete passaram por um validador 548 linhas mais velho, **sem as funções de recusa**. O comentário registra a causa de fundo: *"as cópias nasceram antes de a regra proibi-las — a regra proibiu criar novas e não varreu as velhas"*. ⚠️ **Segundo check SEM recorte por arquivo tocado, pelo mesmo motivo do O**: *"a cópia não aparece no diff de commit nenhum"*. Fail-open declarado: sem `scripts/worktree_orfao_check.py` o bloco inteiro é pulado.
- **O · plano e código discordando** — roda `python3 scripts/plano_vs_codigo.py` e barra passo **aberto** cujo critério de pronto o disco já cumpre ⇒ `❌ PLANO ATRASADO`. ⚠️ **É o único check SEM recorte por arquivo tocado, e de propósito**: `.claude/plans/` é gitignorado, então plano nenhum aparece em `$FILES` — recortar por arquivo o deixaria calado para sempre. Custo medido: ~0,6s. O comentário registra que ele existia e ninguém o consultava: *"ele rodava e acusava sem que portão nenhum o consultasse"*.
- **S · a lei da autópsia virando cobrança** — **novo em 2026-08-09**. Roda `python3 scripts/autopsia_check.py`, e só quando o commit toca `plugins/improve-workflow/` ⇒ `❌ LEI DA AUTÓPSIA FURADA`. Ele mede **texto**, não código: as três frases fixas que a skill `improve-workflow` tem que continuar carregando (a trava de robustez — *"reprove toda proposta que troque robustez por economia"*; a ordem de derrubar — *"tente derrubar cada afirmação"*; a proibição — *"nenhum arquivo do projeto muda durante a apura"*), e nenhum bloco executável do `SKILL.md` escrevendo na árvore (`git commit`/`git add`/`rm `/`mv `/`tee `/redirecionamento). O motivo está no cabeçalho do próprio script: *"prosa some numa reescrita e nada acusa — a rodada seguinte fica sem refutador e com licença para editar"*. ⚠️ **As três frases são o texto exato que o script exige, e a skill reescreve o vocabulário dela de vez em quando** — em 2026-08-09 a terceira trocou *"durante a rodada"* por *"durante a apura"*, e a doc que as citava passou a citar frase morta. O par vivo sai do próprio cobrador: `python3 -c "import sys;sys.path.insert(0,'scripts');import autopsia_check as a;print(a.FRASES)"`. É a régua de que **regra que só existe em prosa não é regra**, aplicada à skill que audita as outras. Fail-open declarado: sem `scripts/autopsia_check.py` o bloco inteiro é pulado. Suíte própria: `scripts/test_autopsia_check.py` (verde nesta rodada; `python3 scripts/autopsia_check.py` → rc=0).

  🔴 **O eixo de placeholder mudo entrou depois, e a lição é sobre a FORMA da isenção.** A primeira versão isentava o **operador**: `>` só contava como redirecionamento quando vinha depois de espaço (`\s>>?\s*\S`), para que `<run>` nos exemplos de uso não reprovasse a skill inteira. Afrouxar o operador abriu o buraco — `<plugin visual>` passava calado, e o shell lê aquilo como par de redirecionamentos, num bloco que quem copia vai executar. O conserto trocou o eixo: a isenção passou a ser do **token declarado** (`DECLARADOS = ("<run>",)`, apagado do bloco antes da varredura, preservando as posições para a linha do achado continuar certa), e o operador voltou a ser cobrado inteiro (`>>?\s*\S`). O que sobra de `<…>` vira o segundo achado, *"nomeia por placeholder mudo"*. **Régua durável: isenção de gate se escreve como lista fechada do que é legítimo, nunca como afrouxamento da regra** — afrouxar o operador isenta tudo que se parecer com o caso conhecido; nomear o token isenta só ele. É a mesma família do `public-ok:`, `r8-ok:`, `vaza-ok:` e `custo-ok:`, que também isentam a **linha nomeada**, não o padrão.
- **R-19 · pasta de trabalho sem casa declarada** — **novo em 2026-08-15**. Roda `python3 scripts/contrato_pastas_check.py` quando o commit traz um `SKILL.md` ou o próprio `contrato-familia.md` ⇒ `❌ PASTA DE TRABALHO SEM CASA`. A lista fechada é a tabela *"As pastas"* de `_shared/contrato-familia.md` (18 pastas declaradas nesta rodada — o número sai da execução: o script imprime `contrato: N pastas declaradas`), e a ordem é a inversa do costume: **declara-se a casa primeiro, a skill a usa depois**. Nasceu de skill que escolhia sozinha onde gravar — cada uma criava mais uma pasta em `.claude/` e ninguém tinha a lista. Estado que atravessa projetos (`~/.claude/…`) está fora do alcance dele. Suíte própria: `scripts/test_contrato_pastas_check.py` (13 checks, verde nesta rodada). ⚠️ **O rótulo dele furou a contagem publicada, e o conserto foi na RÉGUA, não no rótulo**: a classe `[A-Z0-9]+` não casa `# R-19 · ` (o hífen está de fora), então o comando devolvia o mesmo 21 de antes e este check era invisível para quem contava. A classe publicada aqui, no `glossary.md` e no índice passou a ser `[A-Z0-9-]+`. **Régua durável: comando de contagem publicado em doc é um cobrador como outro qualquer — rótulo novo que ele não casa some em silêncio, e o número segue parecendo certo.**
- **R-25 · reincidência anti-slop** — roda `python3 scripts/anti_slop_inventario.py --check` quando o commit traz `.md`/`.sh`/`.py`/`.js`/`.mjs`/`.json` ⇒ `❌ REINCIDÊNCIA ANTI-SLOP`. Igual ao N: dívida antiga passa (teto por classe medido no próprio inventário), ocorrência NOVA de classe já inventariada reprova — e o teto só desce, quem o abaixa é o conserto. O braço **R-25b** roda `python3 scripts/casa_da_doc_check.py` quando o commit traz código executável ⇒ `❌ CAMINHO DE DOC CRAVADO`: quem escreve o lugar da doc como texto, fora do resolvedor único (`_shared/casa_da_doc.py` / `_shared/lib-casa-da-doc.sh`), fica para trás no dia em que a casa mudar — que é exatamente o que aconteceu em 2026-08-20 (`docs/` na raiz).
- **P2 · suíte que compara CAMINHO como TEXTO** — roda `python3 scripts/caminho_como_texto_check.py` quando o commit traz suíte Python (`test_*.py`) ⇒ `❌ CAMINHO COMPARADO COMO TEXTO`. Essa suíte não deixa passar defeito: ela INVENTA defeito, reprovando código certo onde a barra do sistema é a outra — seis suítes fizeram isso no Windows em 2026-08-11, cada uma lida como "o programa quebrou". Suíte própria: `scripts/test_caminho_como_texto_check.py`.
- **R-27 · cobrador que não mediu vira linha no veredito** — **novo em 2026-08-20**, e é a exceção declarada ao "todos só acumulam em `VIOL`": ele **nunca bloqueia**. Cada bloco do gate só roda se o arquivo do cobrador existe (`[ -f ]`) — apagado ou renomeado, o check deixava de medir e nada registrava. Agora a ausência sai em stderr como lista `⚠️ NÃO MEDIDO`, check por check, com o caminho que faltou. O segundo braço pega o cobrador **presente que confessou**: `scripts/regua_call_check.py` é fail-open (erro de infra não trava commit), mas a confissão em stderr evaporava porque o gate só lê exit code e stdout — desde esta rodada o `cli()` dele imprime o marcador `NÃO MEDIDO` **no stdout**, e o gate o põe na mesma lista. Régua durável: fail-open sem confissão que alguém lê é guarda desinstalado com aparência de verde (§5.2 já tinha a lição no `custo_check`; aqui ela entrou no próprio portão).
- **F · testes shell** — roda `plugins/<nome>/hooks/test_*.sh` dos plugins tocados.
- **O bump agora tem cobrador que compara NÚMERO, e não presença de arquivo** (2026-08-13, `scripts/test_bump_propagado.py`). Ele pergunta, plugin a plugin, se a version de hoje é diferente da que valia no último commit que tocou a pasta. A primeira versão perguntava outra coisa — se o `plugin.json` aparecia entre os arquivos daquele commit —, e isso é proxy: commit que mexe só na `description` toca o arquivo sem subir número nenhum e passava. Nasceu de caso medido: `d7d48c2` acrescentou a entrada do `2op` em `plugins/bootstrap/config/manifest.json` e deixou a version do bootstrap em `1.17.10`, então quem já tinha o plugin instalado nunca receberia a receita nova. ⚠️ **`git rev-parse <raiz>^` não devolve vazio: sai 128 e ECOA o argumento no stdout** — sem conferir que a saída tem forma de sha, o commit raiz virava um pai falso e o plugin era pulado em silêncio, que é o mesmo defeito de proxy com outra roupa. É o **oitavo** episódio da mesma família do §5.1: o bump que "todo mundo lembra" foi contornado sete vezes pelo gatilho do gate, e a oitava foi o próprio cobrador aceitando prova fraca.
- **J · as suítes que nenhum glob de plugin casa** — o check que cresce por descoberta de buraco. Nasceu de um declarado: *"`grep -n 'scripts/test_' .claude/hooks/release-gate.sh` não devolvia nada, e as suítes de portabilidade tinham medidor sem cobrador no commit"*. Escopo: commit que toca `scripts/`, `plugins/*/hooks/`, `.claude/hooks/` ou `.gitattributes`. Custo medido em 2026-08-06: **~100s**, dos quais 80s são de `scripts/test_bootstrap_aviso.sh` — é o check mais caro do gate, e o recorte existe porque em todo commit seria proibitivo.
  - **Quantas esteiras ele tem hoje**: `grep -n 'roda_suites' .claude/hooks/release-gate.sh`. Cada uma existe porque um tipo de suíte estava caindo no vão entre os globs D e F.
  - 🔴 **A esteira `scripts/test_*.py` é nova em 2026-08-09, e o buraco que ela fechou tinha três suítes vermelhas dentro.** O gate rodava só as `.sh` de `scripts/` — as `.py` de lá **não tinham cobrador nenhum**, e ficaram vermelhas por dias sem nada acusar. O sintoma que denunciou não veio de um commit barrado: veio da corrida de 2026-08-08, em que **as mesmas quatro conferências reprovaram nas cinco ondas seguidas**. Suíte sem cobrador não fica vermelha em lugar nenhum que alguém olhe — ela só reaparece como trabalho repetido.
  - **A esteira `plugins/*/lib/test_*.sh` cobre o outro vão**: o D varre `lib/test_*.py` e o F varre `hooks/test_*.sh`; suíte **shell dentro de `lib/`** não casava com nenhum dos dois. Foi o que aconteceu com a do resolvedor de skill, que o `scripts/suites_orfas.py` acusou como órfã **no dia em que nasceu**.
  - ⚠️ **Ele é o único que reprova por AUSÊNCIA de arquivo**: `❌ GLOB VAZIO` dispara quando um padrão deixa de casar qualquer coisa, *"suíte renomeada ou apagada deixaria o gate verde sem rodar nada"*. É a mesma asserção de quantidade de `.github/workflows/portability.yml`. **É também o que torna renome de suíte uma mudança de duas pontas**: a rodada de 2026-08-09 renomeou `test_sovai_gate.sh` → `test_motor_gate.sh` e `test_sovai_skill.{sh,py}` → `test_sprint_skill.{sh,py}`, e são os globs — não os nomes — que continuam casando.

  **Régua durável, e ela é a lição do J inteiro: glob de cobrador é a superfície mais fácil de furar sem sintoma.** Suíte que nenhum glob casa não fica vermelha, não fica verde — fica ausente, e ausência não tem cor. Quem mede isso de fora é `scripts/suites_orfas.py`; quando ele acusar uma órfã, o conserto é uma esteira nova aqui, não um lembrete.

- **T · a cadeia de entrega rompida** — **novo em 2026-08-09**. Roda `python3 scripts/cadeia_check.py --repo` quando o commit toca `plugins/` ou o catálogo ⇒ `❌ CADEIA DE ENTREGA ROMPIDA`. Ele confere as fronteiras que fazem o código escrito virar comportamento na máquina de quem instala: **escrito** (`plugins/<nome>/`) → **publicado** (`.claude-plugin/marketplace.json`) → **mandado instalar** (a receita do `bootstrap`). Plugin que nasce em `plugins/` e não entra no catálogo não chega a máquina nenhuma, **e as skills dele somem junto** — por isso o recado conta quantas skills ficam de fora, com o nome delas: é assim que o defeito se apresenta a quem o vive ("desenvolvi e não aparece"). O elo publicado→receita também é cobrado pelo `conformance.py:check_catalogo`, mas só quando alguém roda o setup do `bootstrap`; aqui o commit já responde. ⚠️ **Só o lado REPOSITÓRIO entra no gate**: comparar com o que está instalado nesta máquina reprovaria o commit de quem apenas ainda não rodou o `update`, e isso é assunto de aviso de arranque (§5.2b), nunca de impedimento de commit. Suíte própria: `scripts/test_cadeia_check.py`.

- **U · a lei da COBERTURA VISUAL sumindo do texto** — **novo em 2026-08-19**. Roda `python3 scripts/cobertura_visual_check.py` quando o commit toca `docs/constituicao.md` ou o próprio cobrador ⇒ `❌ COBERTURA VISUAL SEM LEI`. ⚠️ **Ele guarda o TEXTO da regra, não a cobertura**: confere que o artigo `## Artigo N · Cobertura visual` ainda existe e ainda fala de diagrama, fluxo e módulo — fluxo sem diagrama continua passando calado, e o próprio artigo declara esse furo. A razão de existir é a de sempre por aqui: regra decidida pelo dono mora num arquivo que todo re-projeto de doc reescreve, e some sem nada ficar vermelho. O caminho da lei **não é cravado** — sai da cascata `docs/` → `.claude/docs/` do próprio script. Suíte própria: `scripts/test_cobertura_visual_check.py` [confirmado nesta rodada — `python3 scripts/cobertura_visual_check.py` → `cobertura visual — a regra está na lei (docs/constituicao.md)`, rc=0 (remedido em 2026-08-20, após a descida da doc para `docs/`); a suíte → `10 checks, 0 falha(s)`].

- **V · o comando da skill que só roda NESTE repositório (Artigo 8)** — **novo em 2026-08-21**, e fecha o artigo que a constituição listava como o único sem cobrador. Roda `python3 scripts/artigo8_check.py --check` quando o commit traz um `SKILL.md` ou o próprio cobrador ⇒ `❌ COMANDO DE SKILL QUE NÃO RODA FORA DAQUI`. Ele varre só os blocos de comando marcados `bash`, `sh` ou `shell` (bloco `python` e bloco `json` não são comando de terminal) e acusa três padrões: `A1-caminho-local` (`plugins/<x>/…`, caminho que só existe na árvore de quem escreveu), `A2-placeholder` (`<algo>` que o próprio arquivo nunca define) e `A3-variavel-vazia` (`$VAR` que ninguém deriva no bloco — a raiz do plugin chega vazia e o comando vira `python3 /lib/plan_state.py`). ⚠️ **Mesma disciplina do E: barra o que PIOROU contra `.claude/artigo8.baseline.json`**, porque a dívida de hoje é grande (algumas centenas de achados congelados — quantos, e quantas skills a varredura alcança, saem da execução, nunca daqui: `python3 scripts/artigo8_check.py --check` imprime as duas coisas) e reprovar dívida antiga travaria trabalho alheio. Isenção na linha: `artigo8-ok: <motivo>` — a mesma família do `public-ok:`, `r8-ok:`, `vaza-ok:`, `custo-ok:` e `casa-ok:`, que isentam a LINHA nomeada, nunca o padrão. Recongelar é rodar o script sem flag. **Duplo fail-open declarado**: sem `scripts/artigo8_check.py` o bloco é pulado (e a ausência sai no `⚠️ NÃO MEDIDO` do R-27, que já o registra), e com o retrato ausente ou ilegível o `--check` imprime *"retrato ausente ou ilegível … nada a comparar"* e sai 0. Suíte própria: `scripts/test_artigo8_check.py`, que entra na esteira pelo glob `scripts/test_*.py` do check J [confirmado nesta rodada — `python3 scripts/artigo8_check.py --check` → `Artigo 8 — … skills varridas, 0 achado(s) NOVO(s) vs o retrato`, rc=0; a suíte → `30 asserts ok`].

- **Fora do gate, e a doc diz que está fora: `scripts/custo_check.py`** — **novo em 2026-08-16**. Ele reprova afirmação de custo em hook que não diz **quando** foi medida nem **sobre quanto** ("~50ms", "~100s" sem data e sem amostra viram número que envelhece sozinho). Isenção na linha: `# custo-ok: <motivo>` — é a quarta da família do `public-ok:`. ⚠️ **Nenhum bloco do `release-gate.sh` o chama** (`grep -n custo_check .claude/hooks/release-gate.sh` não devolve nada nesta rodada): hoje ele é **régua manual** — `python3 scripts/custo_check.py` → `custo-check: OK — nenhuma afirmação de custo sem data e sem amostra`, com 8 afirmações conformes [confirmado — rodado nesta passada, rc=0]. O que tem cobrador é só a suíte dele, `scripts/test_custo_check.py`, que entra na esteira pelo glob `scripts/test_*.py` do check J. Medidor sem cobrador é dívida declarada, não regra (a cláusula que manda em todas, na constituição).

- **`scripts/anti_slop_inventario.py`** — **novo em 2026-08-19**, e desde 2026-08-20 é a régua do check R-25 acima (`--check`: teto por classe que só desce). Sem flag ele MEDE e LISTA, não conserta: varre o que o git rastreia (menos `graphify-out/`, menos `.claude/reports/` e menos ele mesmo, porque medir o próprio relatório faria a contagem se citar) e devolve o inventário das quatro classes da mesma doença — **caminho de doc cravado em código executável**, **lista duplicada**, **contagem escrita à mão**, **valor copiado** —, cada classe com contagem, dono (a fonte única que deveria mandar) e de-para. Cada classe traz o comando que reconta a si mesma, então o inventário não vira número envelhecendo na prosa [confirmado nesta rodada — `python3 scripts/anti_slop_inventario.py` → `varredura: 663 arquivos rastreados`, com `A · caminho de doc cravado em código executável` em `394 ocorrências em 103 arquivos`, rc=0]. ⚠️ **A classe A conta só `.py`/`.sh`/`.js`/`.mjs` desde 2026-08-20**: com prosa e retrato de baseline dentro ela dava 718 pontos e o zero exigido era inalcançável por construção — a doc que ENSINA onde a documentação mora precisa escrever o lugar. O recorte mudou o ESCOPO, não a régua, e a isenção pontual é `casa-ok: <motivo>` na linha, **com motivo escrito** (marcador pelado continua contando). Suíte própria: `scripts/test_anti_slop_inventario.py` (entra na esteira pelo glob `scripts/test_*.py` do check J), que desde 2026-08-20 também EXECUTA o comando de conferência de cada classe — as classes B e D crashavam em `--classe X`, prometendo uma conferência que morria com `ValueError`. Cobrador as classes ganharam em 2026-08-20 — o R-25 barra o ponto novo de qualquer classe, e a classe A tem o braço dedicado R-25b (`casa_da_doc_check.py`); o relatório da varredura segue em `.claude/reports/`, que é gitignorado (registro de trabalho não é produto). Vizinho do mesmo desenho, ainda SEM porta no gate: `scripts/tetos_rodadas_inventario.py` (R-26) — inventaria todo teto por contagem de rodadas (`max_rounds` e afins) e exige veredito MIGRADO/FICA por escrito; hoje só a suíte `scripts/test_tetos_rodadas_inventario.py` o roda (glob `scripts/test_*.py` do check J).

⚠️ **Dois checks varrem o repo inteiro, e os dois pelo mesmo motivo**: o alvo deles não aparece em diff nenhum. O `O` porque `.claude/plans/` é gitignorado; o `Q` porque cópia de trabalho parada não é arquivo rastreado. Recortar por arquivo tocado deixaria os dois calados para sempre.

⚠️ **D e F são por plugin TOCADO, não por repo.** Um commit que só mexe no `bootstrap` roda exatamente `plugins/bootstrap/lib/test_*.py` e `plugins/bootstrap/hooks/test_*.sh` e mais nada. **Plugin sem suíte não é plugin sem teste: é plugin cujos checks D e F estão desligados.**

Bloco de saída literal quando algo viola:

```
🚧 release-gate (pedro-plugins) BLOQUEOU o commit:
<violações>

Conserte e commite de novo. (Gate mecânico: .claude/hooks/release-gate.sh)
```

### 5.2b O outro lado da cadeia: a máquina que roda código velho

**Novo em 2026-08-09**, e nasceu do defeito mais caro da rodada. O dono passou uma sessão
inteira revisando, testando e aprovando a v0.4.0 do `gauntlet`; **o que rodava na máquina
dele era a 0.3.2**, instalada dias antes, sem nenhum dos consertos. A descoberta foi por
acaso, cavando o cache do cliente à mão [confirmado — o `installPath` do
`installed_plugins.json` apontava para `…/gauntlet/0.3.2`, e `grep -c` naquele arquivo
devolvia zero para os três símbolos novos].

**A causa é estrutural, não descuido:** editar `plugins/<nome>/` não muda o que o harness
carrega. Ele lê o cache em `~/.claude/plugins/`, e o cache só troca com
`claude plugin update` **mais um reinício da sessão** — os dois passos, sempre (§7).

Quem avisa é `.claude/hooks/sessionstart-avisa-cadeia.sh`, um `SessionStart` do **projeto**,
não de plugin. O público explica a escolha: só quem tem o repositório na mão pode comparar
as duas versões; para quem apenas instalou o marketplace, o `claude plugin update` normal
já resolve. Ele fala uma vez por sessão (sentinel em `$TMPDIR`, chaveado por `session_id`),
nunca bloqueia, e o recado vai aos **dois** públicos por `hj_msg_ctx` — ao dono, que decide
atualizar, e ao modelo, que senão passa a sessão testando código que não é o que roda. A
frase que fecha o aviso é a lição: *"teste no repositório vale como leitura de código, nunca
como prova de comportamento"*. Kill-switch: `CADEIA_GATE=0`. Suíte:
`.claude/hooks/test_sessionstart_avisa_cadeia.sh`.

⚠️ **Ele avisa e não conserta, de propósito** — o cabeçalho registra: *"o estrago de um
instalador automático errado é maior que o do aviso que ele evita"*.

### 5.3 Contrato dos hooks — as 6 propriedades

Quem mede é `scripts/hook_contract.py`; quem cobra é o check E. As seis propriedades, copiadas da docstring do medidor [confirmado]:

1. **canal de saída** — como o hook fala (bloqueia? informa? só loga?). Os três canais de bloqueio coexistem e **não** foram normalizados: `exit 2`, `permissionDecision:"deny"`, `decision:"block"` — *"Não normalizo: só meço."*
2. **cap anti-loop** — quem bloqueia tem teto de devoluções, e a chave do teto é **por sessão** (`SESSION_SCOPED`).
3. **kill-switch** — dá pra desligar sem editar o arquivo.
4. **binário fixo** — caminho absoluto de ferramenta (`/opt/homebrew/bin/…`) é achado de gravidade **high**: some fora do Mac com Homebrew e o hook cai no fail-open em silêncio.
5. **fail-open** — guarda a ausência das ferramentas que usa (`EXTERNAL_TOOLS = ("jq", "python3", "node", "graphify")`).
6. **o NOME diz quando roda e se barra** — regra `R6`, nova nesta rodada. O molde é `<evento>-<verbo>-<assunto>.<sh|py>`: o prefixo é o evento em que o script está **registrado**, e o verbo declara o poder. Verbos que barram: `barra`, `exige`, `trava`, `recusa`. Verbos que só avisam: `avisa`, `anota`, `mede`, `lembra`, `resume`, `sincroniza`, `colhe`, `abre`. ⚠️ **O verbo não é decorativo: é conferido contra o canal MEDIDO no script**, então um `-avisa-` que sai com `exit 2` reprova igual a um nome fora do molde. Um script registrado em dois eventos passa se o prefixo casar com **um** deles. O defeito que a motivou está no comentário: *"`scope-cop.sh`, `mark-work.sh` e `delivery-audit.sh` são o mesmo problema: pra saber quando cada um roda e se ele trava o agente era preciso abrir os três"*.

⚠️ **A R6 é a razão de o número de achados ter explodido — e a maioria é DÍVIDA DECLARADA, não regressão.** Sem baseline, o medidor devolve **42 achados (40 alta · 2 média)** neste run — **39 deles `R6-*`** [confirmado, derivado do `--json` desta rodada] — em hooks que já existiam com o nome antigo. Como o check E só barra o que **piorou** contra `.claude/hook-contract.baseline.json`, o commit passa — a regra vale para hook novo, e os velhos entram quando forem renomeados.

**Todo achado sai com o PAR DE CITAÇÕES — `who` que resolve como arquivo, `line` real e `quote` literal** (decisão do dono, 2026-08-09). Antes disso o medidor devolvia o veredito sem a prova: **41 dos 42 achados saíam com `quote` vazio e `line` 0, e nenhum dos 42 `who` resolvia como caminho** (era o apelido `plugin/basename`) [confirmado — medido antes do conserto]. Quem consumia isso era a vistoria, que **recusa na porta** achado sem par de citações — e o tradutor dela repetia a própria mensagem como "prova" para preencher o campo. A escolha entre consertar na fonte ou no tradutor foi do dono, e ele escolheu a **fonte**: o tradutor inventar a citação é exatamente o que a barreira existe para impedir.

Duas regras saíram disso, e as duas valem para qualquer cobrador que a vistoria leia:

- **A prova de um veredito sobre o NOME é a linha do REGISTRO**, não do corpo do script — quem diz em que evento o script roda é o `hooks.json`. Por isso `who` do `R6-*` e do `R0-script-ausente` aponta o `hooks.json` com a linha do registro, e o nome do script foi para dentro do `msg`.
- **A prova de um veredito sobre o CORPO é a linha do corpo** — `R5-sem-failopen` passou a citar a primeira linha que usa a ferramenta desguardada.

Quem cobra que não regrida é `scripts/test_hook_contract.py`, com um repro que gera um achado de cada família e exige os quatro: trecho literal, linha não-zero, `who` que existe no disco, e `quote` diferente do `msg` (prova, não eco) [confirmado — os checks reprovam quando o campo volta a nascer vazio].

O próprio script se declara falível [confirmado, citação literal]: *"⚠️ **Isto é grep sofisticado, não verdade.** O script diz ONDE OLHAR."* E a escolha de calibração tem direção declarada: *"Detectar um cap que não existe é o erro CARO … Detectar de menos só gera um falso alarme que a conferência derruba."*

**Os kill-switches de hoje**, derivados mecanicamente (`grep -rhoE '\$\{[A-Z_]+_GATE:-[01]\}' plugins/*/hooks/*.sh | sort -u`) [confirmado]: `ASKQ_GATE`, `BOOTSTRAP_DEPS_GATE`, `BRANCHES_GATE`, `DOC_AUTORAL_GATE`, `DOC_GUARD_GATE`, `GAUNTLET_GATE`, `GRAPHIFY_GATE`, `HANDOFF_GATE`, `LINT_GATE`, `ORGANISM_GATE`, `PLAN_DOC_GATE`, `SCOPE_COP_GATE`, `SHIP_GATE`, `SPRINT_GATE`, `VISUAL_GATE` — **quinze**. Os dois novos são `GAUNTLET_GATE` (o gate de `Agent` do gauntlet) e `BOOTSTRAP_DEPS_GATE` (o `sessionstart-deps.sh` compartilhado). Os hooks Python usam a mesma ideia com outra grafia, e hoje sobrou **um**: `ARTEFATO_REGUA=0` [confirmado — os outros três (`PROSE_CEILING`, `FORMA_RELATO`, `REGUA_RELATO`) saíram com os hooks de `Stop` do `bootstrap` em 2026-08-09, §1.2].

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

### 5.4 O ponto cego atual: o medidor enxerga o Python pela metade

🔴 **O que ele deixa passar hoje é o CAP.** Os dois hooks Python vivos (§1.2) são medidos assim [confirmado — `python3 scripts/hook_contract.py --json` desta rodada, campo `measured`]:

```
plugins/guardrails/hooks/pretooluse-artefato-regua.py
  blocking: []              informing: []
  cap: counter 0 · sentinel 0 · session_scoped False
  killswitch: 'if os.environ.get("ARTEFATO_REGUA") == "0":'

plugins/visual/hooks/stop-anuncio-sem-acao.py
  blocking: ['decisionBlock']   informing: []
  cap: counter 0 · sentinel 0 · session_scoped False
  killswitch: 'if os.environ.get("ANUNCIO_ACAO") == "0":'
```

O `resolve_script` **acha** o arquivo (o regex aceita o comando com o interpretador na frente) e os padrões de kill-switch e de bloqueio já reconhecem grafia Python — mas os de cap continuam shell-shaped, `CAP_COUNTER` procurando `-ge …]` [confirmado, li as constantes]. **Consequência: um hook `.py` que bloqueie sem teto passa pelo check E sem um achado de cap sequer** — é exatamente o que o retrato mostra para o hook de `Stop` do `visual`, que bloqueia por `decisionBlock` com `cap.counter` zerado. É medição ausente, não conformidade.

🔴 **E o contrapeso que existia aqui foi embora inteiro.** Até 2026-08-09 o `conformance.py` cobria o vão medindo **execução** em vez de código, com três checagens em cadeia (`check_teto_rodou`, `check_juiz_rodou`, `check_bypass_teto`) que liam os `batidas.log`/`bypass.log` dos hooks de `Stop` do `bootstrap`. Com os hooks removidos, as três saíram junto — `grep -oE '^def check_[a-z_]+' plugins/bootstrap/lib/conformance.py` devolve hoje dez checagens e nenhuma delas [confirmado, rodado nesta passada]. **O ponto cego do medidor ficou sem rede.**

**Régua durável, e ela é o que sobra de tudo isso: guarda instalado que não EXECUTA é pior que guarda desligado — parece protegido.** Por isso o padrão certo é registrar **toda** execução, não só as que barram: sem log de aprovação, "não rodou" e "rodou e aprovou" são indistinguíveis, e foi assim que uma checagem chegou a carimbar *"nenhuma resposta furou o teto"* com o guarda mudo [relatado — docstring do `check_teto_rodou` removido].

### 5.5 O juiz de forma: quando vale chamar modelo dentro de um hook

🔴 **REMOVIDO em 2026-08-09, a pedido do dono** — `plugins/bootstrap/hooks/stop-forma-relato.py` saiu do disco junto com os outros hooks de `Stop` do `bootstrap`, e o `hooks.json` do plugin hoje registra só `SessionStart` e `PostToolUse` [confirmado — `python3 -c "import json;print(list(json.load(open('plugins/bootstrap/hooks/hooks.json'))['hooks']))"` → `['SessionStart', 'PostToolUse']`]. **O critério abaixo continua sendo a régua de quando um hook pode pagar token; o hook que a ilustrava, não roda mais.**

Ele foi o primeiro hook do repo que **pagava token por turno**, e a docstring dele é o critério de quando isso se justifica [relatado, citação literal do arquivo removido]:

> Divisao de trabalho com o stop-prose-ceiling.py, que e vizinho e deliberadamente diferente: aquele e mecanico, roda em todo turno e custa zero token; este chama um modelo, entao SO roda quando a resposta e um RELATO. Nenhum padrao distingue "6 linhas densas" de "6 linhas vazias" — para isso precisa de um leitor.

As decisões que fazem o desenho fechar:

- **O gatilho é medido no próprio texto, não configurado** — `e_relato()` exige *"prosa suficiente E prova colada"*: pelo menos um bloco ``` e `MIN_PROSA = 2` linhas de prosa fora dele. O comentário registra a calibração: *"Exigir 4 de prosa deixava passar exatamente os relatos que dao certo."*
- **Mas medir no texto não é escopo: quem delimita é o turno.** O teste de relato dizia *como* julgar e nunca *quando*, então o juiz rodava em todo fim de turno — 463 chamadas em 9 dias por um veredito de uma palavra. `usou_visual()` fecha o escopo antes do modelo: só o turno que passou pelo `/visual` é julgado. **Gate que só sabe reconhecer o objeto certo gasta em tudo que se parece com ele.**
- **O anti-loop vem ANTES do gasto** — o contador é consultado antes de `julga()`, com o comentário *"anti-loop antes de gastar o modelo"*.
- **Fail-open em tudo que não for reprovação explícita** — `julga()` devolve `(True, motivo)` para `claude` ausente no PATH, timeout, `returncode != 0`, saída vazia e veredito ilegível.
- **O modelo é barato e trocável** — `FORMA_RELATO_MODEL`, default `haiku`; `TIMEOUT_S = 25`; o prompt corta a entrada em `texto[:6000]`.
- **O contrato de resposta é de uma linha só** — `PASSA` ou `REPROVA: <defeito em até 12 palavras>`, e o parser lê **só a primeira linha**.

O wiring era o par no mesmo array `Stop`, na ordem prosa → juiz, com `timeout` 10 e 30 [relatado — o array não existe mais no `hooks.json` do `bootstrap`]:

```json
"Stop": [{"hooks": [
  {"type":"command","command":"python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/stop-prose-ceiling.py\"","timeout":10},
  {"type":"command","command":"python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/stop-forma-relato.py\"","timeout":30}
]}]
```

⚠️ **A lição de ordem sobrevive à remoção: o mecânico vem antes do que paga token.** O gate barato é quem tem a chance de encerrar o turno sem que o caro chegue a rodar — inverter a ordem faria o repo pagar modelo para reprovar o que um `wc -l` já reprovava.

### 5.6 A regra nova do teto de prosa: pergunta fechada exige veredito na 1ª linha

🔴 **REMOVIDO em 2026-08-09, a pedido do dono** — os hooks de `Stop` do `bootstrap` saíram do disco e o array `Stop` do `hooks.json` deixou de existir [confirmado — `git show 251d6ac --stat`]. A lição de padrão abaixo continua valendo; o mecanismo que a ilustrava, não roda mais.

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

⚠️ **Há UMA esteira, e ela é de portabilidade** — `.github/workflows/portability.yml`, nos três sistemas, no push para `main`, no pull request e sob disparo manual. ⚠️ **Push de branch de trabalho não acorda nada desde 2026-08-19** (`branches: [main]`): quem está no laço de conserto mede pelo `workflow_dispatch` filtrado, e o preço de esquecer isso é descobrir a quebra só no merge. A `constituicao.md` (Artigo 3) se apoia nela para declarar o rigor cobrado; então esteira vermelha não é chateação de CI, é a lei sem cobrador. **Ela ficou vermelha por dias em 2026-08-10**, e as três causas valem como padrão para qualquer suíte que rode no Windows:

- 🔴 **`bash` no Windows é o WSL, não o Git Bash.** `subprocess.run(["bash", …])` resolve `System32\bash.exe`, e o runner não tem distro instalada: a resposta é `Windows Subsystem for Linux has no installed distributions.` em UTF-16, o que chega ao Python como **stdout vazio** — e o `json.loads` estoura três camadas acima, num teste que não tem nada a ver com o defeito. O conserto ficou no workflow (o Git Bash entra na frente do `PATH`, e é o mesmo interpretador que o `shell: bash` dos steps já usa), não nos dez arquivos que chamam `bash`: o binário é do AMBIENTE, e mascarar isso em cada chamador espalharia a mesma decisão por dez lugares.
- 🔴 **Separador de `PATH` é `os.pathsep`, nunca `:` cravado.** No Windows é `;`, e com dois-pontos o `PATH` inteiro vira uma entrada só de lixo — todo binário some, inclusive o que o teste acabou de montar. Estava em `plugins/bootstrap/lib/test_conformance.py:358`.
- 🔴 **Matriz sem `fail-fast: false` mente sobre portabilidade.** O padrão cancela os outros sistemas quando um falha, e o log deles sai como `The operation was canceled` — indistinguível de falha real. O Windows quebrou, macOS e Linux apareceram vermelhos por cancelamento, e a leitura de fora foi "os três estão falhando". Uma esteira que existe para dizer **em quais sistemas** o problema está não pode cancelar os outros dois.

⚠️ **E os três primeiros escondiam mais três** — cada rodada de conserto revelava o defeito seguinte, todos do mesmo padrão: *o teste passava na máquina de quem escreveu por causa de algo que só existe lá*.

- **`git commit` sem `GIT_AUTHOR_*` sai 128 em runner limpo.** O `~/.gitconfig` global preenchia a outra ponta na máquina do dono. `test_doc_lint.py` tinha TRÊS chamadas em três formas; consertar uma por vez fez a esteira quebrar duas vezes seguidas no mesmo arquivo, com a segunda ocorrência vinte linhas abaixo da primeira. Viraram uma receita só (`git_commit`).
- **Teste que mede regra usando artefato IGNORADO pelo git.** `test_docguard_scope.sh` media o escopo dos dois gêmeos com o `graphify-out/` do próprio repositório — que está no `.gitignore`. Sem ele o hook sai calado (o comportamento CERTO dele) e os 17 casos de "busca cega tem que bloquear" reprovavam com `0 denies`, sem nada dizer que a causa era artefato ausente. O teste passou a montar o projeto de mentira com os dois pré-requisitos.
- **Nome de projeto VAZIO quebra a página do plano.** `plan_state.py:cmd_page` deriva o nome do diretório dois níveis acima de `.claude/plans`; com o plano a menos de dois níveis da raiz, `basename('/')` é `''`, o `visual` recusa o spec e a página não nasce. Um plano em `/tmp/<algo>` quebrava no **Linux** e passava no **macOS** — lá `/tmp` é atalho para `/private/tmp` e sobra um nível. Este é defeito de PRODUTO, não de teste, e foi a esteira que o encontrou.

🔴 **A esteira parava na PRIMEIRA suíte que falhasse, e é por isso que "cada rodada revelava
o defeito seguinte" aparece duas vezes nesta seção.** O passo era um laço de shell sob
`set -e`: a primeira reprovação matava o passo e as outras nunca rodavam, então **uma rodada
de ~4 minutos entregava exatamente um defeito**. Entre 10 e 11 de agosto foram quinze pushes
para achar seis coisas. E suíte que **pendura** era pior: o log de um job em andamento não
sai, então ninguém sabia sequer **qual** estava presa — a única saída era cancelar às cegas.

Desde 2026-08-11 quem roda é `scripts/run_suites.py`: teto por suíte, segue depois da falha,
e devolve o placar inteiro com o tempo de cada uma. A primeira execução dele achou **três**
problemas de uma vez, dois dos quais eram invisíveis no modelo antigo. **Cobrador que para
no primeiro achado não é cobrador: é uma fila de rodadas.**

⚠️ **E ele nasceu com o defeito que existia para evitar — capturar por CANO pendura.**
Com `stdout=PIPE`, a leitura só termina quando o último descendente que herdou o descritor o
fecha; suíte que deixa um neto vivo pendura a captura **depois** de já ter terminado. Duas
suítes de 46 s e 2 s apareceram como `TIMEOUT 180s`. A saída passou a ir para arquivo
temporário, que não tem escritor a esperar. **Quando o filho pode deixar neto, capture em
arquivo, nunca em cano.**

⚠️ **Trocar o formato dos globos quebra quem os lê.** `scripts/suites_orfas.py` lia os padrões
da linha `roda <runner> '<glob>'` do workflow — e um leitor que não reconhece o formato novo
não devolve erro: devolve **zero globo**, e aí toda suíte do repositório vira órfã. Ele
reconhece as duas formas hoje, de propósito. Vale como regra: **leitor de formato entende o
antigo e o novo; quebrar no dia da troca é acoplar a doc ao workflow por outro caminho.**

**A decisão que fechou o caso do `bash` no Windows: quem precisa dele PROCURA um que rode.** Três tentativas de arrumar pelo PATH do runner falharam (`GITHUB_PATH` não venceu o `System32`; `export PATH=/usr/bin:$PATH` também não). O critério de um bash servir passou a ser **ele responder**, não estar no PATH — `bash_posix` (hoje em `_shared/bash_posix.py`, vendorado; `test_conformance.py` o importa) testa o candidato com um `echo` e, sem nenhum que responda, os casos que exercitam hook shell **pulam em voz alta** (49 ok em vez de 57). Hook shell sem shell não é falha do hook, e fingir que é foi o que manteve a esteira vermelha.

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

⚠️ **Harness de mutação cresce por MULTIPLICAÇÃO, e o teto da esteira é por suíte.** Em
2026-08-13 o harness do plano foi de 6 para 12 entradas, e cada uma copia o repositório e roda
**todas** as suítes de `lib/` — a conta é `mutações × suítes`, não `mutações + suítes`. A esteira
o matou com `TIMEOUT 300.0s` (`run_suites.py`), e o arquivo que existe para provar que as travas
mordem virou o **único** vermelho de 130 suítes. O conserto foi cada mutação declarar a suíte que
deve acusá-la, rodando a pasta inteira **só quando essa suíte não acusa**: 32,9 s medidos, com o
rigor intacto — o veredito "trava sem cobertura" continua nascendo de uma passada completa.
**Régua durável: em cobrador cujo custo é um produto, acrescentar uma linha na lista é
acrescentar uma coluna na conta** — é o §1.16 outra vez, com o teto do lado de fora.

⚠️ **A suíte mede a FUNÇÃO, e o defeito mora na COSTURA — foi assim que a esteira inteira,
verde, deixou passar dois defeitos graves.** Medido em 2026-08-13: o cruzamento
artigo→tarefa ganhou o parâmetro que exclui artigo sem cobrador, `completude.py` passava o
parâmetro, e a entrada de linha de comando do plano **não passava** — o mesmo fato saía com
dois vereditos conforme a porta de entrada, e o veredito errado era o que bloqueava. A suíte
do cruzamento chamava a função direto, com os argumentos certos, e ficava verde. **Régua
durável: teste que só chama a função prova que o motor SABE fazer, nunca que alguém PEDE —
todo mecanismo com mais de uma porta de entrada precisa de um caso que atravesse a porta de
produção.** É o antipadrão "mede a coisa errada", na variante mais cara de achar.

⚠️ **Suíte de hook não escreve arquivo dentro da própria pasta rastreada.** Duas suítes
rodando ao mesmo tempo gravam o mesmo `mock_*.sh` na pasta do plugin, e o `trap` de uma
apaga o mock da outra: a esteira fica vermelha **por sorteio de paralelismo**, e é debaixo
desse ruído que defeito de verdade passa despercebido — três suítes do `intent-guard`
faziam isso. Pior num repositório público: processo morto deixa mock órfão no working tree.
Arquivo temporário de suíte nasce em diretório temporário **por execução**. Quem cobra é
`scripts/test_suites_nao_escrevem_no_plugin.py`, que varre as grafias de escrita em `$HERE`.

⚠️ **A disputa se conserta na CASA, não na ordem — e desde 2026-08-20 a esteira tem uma fase só.**
Três suítes do `intent-guard` rodavam em série numa segunda fase do `scripts/suite.sh`, porque
gravam estado por sessão no temporário do sistema com ids **cravados no código** (`dasid`,
`cksid`, `pgsid`…). Serializar era remendo: a colisão é da CHAVE, não da ordem — duas esteiras de
pé (duas sessões de agente no mesmo repositório, ou o CI ao lado do terminal) continuavam pisando
uma na outra, e a **suíte acusada mudava a cada rodada**, que é a assinatura de disputa e não de
defeito. Hoje `scripts/run_suites.py:roda` dá a cada suíte um temporário próprio (`TMPDIR`, `TMP` e
`TEMP` juntos — o Windows não lê `TMPDIR`), apagado só depois de a árvore de processos morrer, e
com casa própria o id fixo deixa de importar. A lista das seriais encolheu a zero e a segunda fase
saiu junto; o `SUITE_PULA` do rodador segue de pé para o dia em que voltar a existir suíte que
dispute recurso de verdade. ⚠️ **Trocar os ids cravados por nome sorteado seria o mesmo conserto
repetido em cinco arquivos e esquecido no sexto** — regra da casa: disputa de estado se mata onde
todas as suítes passam, nunca em cada uma delas.

⚠️ **E instabilidade virou coisa MEDIDA, não impressão.** `bash scripts/suite.sh --flake` roda a
mesma seleção **duas vezes ao mesmo tempo, no mesmo pool**, e reprova só quem responde coisas
diferentes nas duas — passou numa e falhou na outra. Suíte que falha nas duas não é assunto dele
(é obra ruim, e quem a acusa é a esteira normal). ⚠️ **`--flake` NÃO grava prova no green-cache**:
verde ali significa *"nenhuma suíte instável"*, não *"a esteira passou"* — emprestar verde a partir
dele seria a mesma mentira do glob vazio (F17.2). Quem cobra o cobrador é
`scripts/test_paralelismo_check.py`, que monta uma suíte propositalmente instável (duas cópias
disputando um arquivo de chave fixa) e exige que ela seja **nomeada**, mais uma esteira estável
exigindo silêncio.

**As disciplinas de teste que este repo cobra**, todas com o sítio que as prova:

- **Teste E2E não-tautológico.** R9/R10 de `test_plan_gate.sh` escrevem o sentinel **rodando o hook escritor de verdade**, nunca recalculando a chave à mão — *"Recalcular a chave à mão aqui foi exatamente o que mascarou o bug de path na 1ª rodada."*
- **Par escritor↔leitor precisa de um teste que rode OS DOIS programas.** `test_conformance.py` roda o hook com `CLAUDE_CONFIG_DIR` num `mktemp`, exige que o log nasça **dentro** dele e só então roda o `conformance.py` [confirmado — a suíte tem função dedicada ao juiz, `teste_juiz_de_forma_mudo`, com os quatro casos: nunca executou · fail-open por juiz sem resposta · parado há mais de 24h · não cobra de quem não instalou o bootstrap].
- **Sabotagem da allowlist.** `test_askq_lint.py` esvazia `NOMES_PROPRIOS` e reafirma que aí *"GitHub"* barra — um caso "GitHub passa" sozinho seria satisfeito também por uma régua quebrada que não pega nada.
- **Verde por fail-open não conta como verde.** `test_bootstrap_hooks.sh` não aceita o exit code do juiz sem conferir o motivo no log: `grep -q '"motivo": "julgou"'` — *"fail-open por juiz mudo aprova tudo: so vale como verde se ele REALMENTE julgou"* [confirmado, citação literal].
- **Teste de hook de detecção precisa distinguir os dois `exit 0`.** No gate do ship, "não detectou deploy" e "detectou e a suíte passou" são ambos 0; a suíte resolve com um fixture cujo alvo de teste falha de propósito, e aí o exit code responde uma pergunta só.
- **Prosa que dá ordem operacional pode ser testada — e ela também apodrece.** `plugins/handoff/lib/test_handoff_skill.py` trata a `SKILL.md` do handoff como código: extrai os blocos ```` ```bash ```` do markdown (com `textwrap.dedent`, *"o bloco como quem copia recebe"*), **executa** o comando prescrito contra um plano de fixture e confere que ele imprime `pronto` e `pendencia` de verdade; depois lê a prosa e cobra que ela mande **copiar** esses campos, não redigi-los. É o mesmo princípio do `visual_page.py` (*"prosa apodrece"*) aplicado a instrução que o modelo vai seguir. [confirmado — docstring e execução]
- **Suíte que DERIVA o inventário só enxerga as grafias que conhece — e a exclusão que ninguém atribui é regex vazia.** `scripts/test_sem_jq.sh` classifica cada hook em classe A (jq só formata) ou B (jq decide) varrendo o texto dos `.sh`. Dois furos medidos em 2026-08-09, e ambos passavam por verde: (1) `$VENDORADOS` era usado em dois `grep -vE "/($VENDORADOS):"` **sem nunca ter sido atribuído** — a exclusão de biblioteca vendorada que a prosa prometia era um filtro que casava tudo; hoje ela é derivada de `ls _shared/*.sh`. (2) A varredura conhecia duas formas de ler o payload (o `jq` cru e o `hj_campo` do `hook-json.sh`) e era **cega à terceira**, Python embutido dentro do `.sh` — e reconhecer só `data.get("x")` ainda deixava invisível quem escreve com default, com aspas simples ou com colchete, de modo que as quatro grafias tiveram que entrar juntas. **Régua durável: derivador que classifica por FORMA de escrita mede o que ele sabe procurar, não o que existe** — quando a medição casa com o esperado, confira se o filtro está mesmo filtrando antes de comemorar. **E há um terceiro furo, de outra família: o derivador cobrava do doc um número que ele mesmo sabia medir.** Três dos quatro `FAIL` da rodada de 2026-08-09 eram só o retrato congelado num doc autoral tendo vencido — reprovação que nenhum código conserta, só a mão de um humano. Hoje o doc traz o comando e a suíte imprime a medida (§1.1). [confirmado, executado nesta rodada: `bash scripts/test_sem_jq.sh` → `retrato de agora — produção: 41 · classe B: 36 · classe A: 5` e `verde`]

---

## 7 · Gotchas

### Hooks & plugins

- ⚠️ **Hook de plugin vai em `hooks/hooks.json` (subpasta), NUNCA na raiz.** Na raiz é ignorado em silêncio e `validate` passa mesmo assim. ⚠️ **O ponteiro que a doc trazia aqui morreu**: o texto de conserto que repetia o aviso vivia no `conformance.py:check_juiz_rodou`, checagem removida em 2026-08-09 (§5.4). Hoje quem prova o wiring é o `hooks.json` e a suíte `scripts/test_paths_normalize.sh`.
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
- 🔴 **Régua que casa o ARQUIVO INTEIRO acusa por vizinhança, e o falso positivo fecha a porta do repositório.** Medido em 2026-08-16: `scripts/test_dimensoes_de_revisao.py:enumera` proibia skill de listar os documentos de régua na prosa, e media assim — `".claude/docs" in txt and doc in txt`, sem nenhuma noção de proximidade. Uma linha nova sobre `.claude/docs/prototipo/` (a casa do protótipo, **não** a pasta da régua) fez duas menções legítimas a **58 linhas** dela reprovarem, a esteira saiu vermelha, e a execução do plano parou por defeito do medidor com a obra inteira sã. **Conserto: a pasta só conta quando é ela que está sendo apontada** — solta (aspas, parêntese, espaço) ou colada ao documento, nunca quando o caminho segue para uma subpasta que aponta outra coisa (`APONTA_A_REGUA`, um lookahead negativo). Os quatro testes negativos da própria régua seguiram verdes, que é o que separa conserto de afrouxamento.
- **A régua da regra vale para a régua também:** quando uma proibição é medida por presença de string, pergunte *"que outra coisa legítima contém essa string?"* antes de escrever o cobrador — a resposta costuma ser "uma subpasta com outro assunto".

### Release

- ⚠️ **Bump em toda mudança e espelho no marketplace** — o gate avalia **staged ∪ tracked-modificados**, então mudança solta em OUTRO plugin bloqueia o seu commit [confirmado, `FILES` do release-gate].
- ⚠️ **Plugin novo entra em três arquivos** — e quem cobra o terceiro é o `conformance.py`, depois do commit (§5.1).
- ⚠️ **`author` tem que ser objeto** no `marketplace.json`; string é rejeitada pelo `validate` [relatado; o estado atual é consistente — os dois `author` presentes hoje são objeto, verificado neste run].
- 🔴 **O release-gate só existe para commit feito pela ferramenta Bash** (`matcher: "Bash"`). Commit por outro caminho não o dispara e nem precisa de `--no-verify` pra isso. **Bump esquecido não deixa rastro** — quem quiser saber se aconteceu tem que reconstruir commit a commit.
- 🔴 **Cobrador de CONTAGEM não pega NOME errado, e o número certo dá a impressão contrária.** O README afirmava a quantidade certa de plugins desligados de fábrica e nomeava dois errados; o check K passava verde e quem instala ligava o plugin errado. Toda afirmação que é `<número> + <lista>` precisa das duas conferências — a segunda entrou em `readme_counts_check.py:_confere_nomes` (§5.2).
- ⚠️ **Isenção de gate se escreve como token declarado, nunca como operador afrouxado** — o `autopsia_check.py` afrouxou o `>` para deixar passar `<run>` e abriu passagem para `<plugin visual>` (§5.2). `public-ok:`, `r8-ok:`, `vaza-ok:`, `custo-ok:` e `casa-ok:` são a forma certa: isentam a linha nomeada, com motivo escrito — e no `casa-ok:` o motivo é obrigatório por programa, marcador pelado não isenta.
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
