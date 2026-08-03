---
generated: 2026-08-02
generated-commit: b0beda4
project: pedro-plugins
scope:
  - .gitignore
  - .claude/.project-doc/findings.jsonl
  - .claude/.project-doc/ledger.json
  - .claude/hook-contract.baseline.json
  - graphify-out/graph.json
  - graphify-out/manifest.json
  - graphify-out/.graphify_labels.json
  - graphify-out/GRAPH_REPORT.md
  - plugins/project-doc/lib/journal.py
  - plugins/project-doc/lib/graph_map.py
  - plugins/intent-guard/lib/ledger.py
  - _shared/green-cache.sh
  - plugins/visual/server/visual_server.mjs
  - plugins/visual/lib/plan_state.py
  - plugins/visual/lib/cobertura.py
  - plugins/visual/lib/visual_page.py
  - plugins/visual/hooks/stop-plan-status.sh
  - plugins/handoff/skills/handoff/SKILL.md
  - scripts/hook_contract.py
  - plugins/branches/lib/branch_state.py
  - plugins/guardrails/hooks/scope-cop.sh
  - plugins/guardrails/hooks/askq-humanize.sh
  - plugins/context-guard/hooks/context-guard.sh
  - plugins/context-guard/hooks/context-guard-reset.sh
  - plugins/context-guard/hooks/context-guard-writer.sh
  - plugins/bootstrap/hooks/stop-prose-ceiling.py
  - plugins/bootstrap/hooks/stop-forma-relato.py
  - plugins/bootstrap/hooks/hooks.json
  - plugins/bootstrap/lib/conformance.py
  - plugins/project-doc/hooks/stop-doc-touch.sh
verified-by:
  - plugins/visual/lib/test_plan_state.py
  - plugins/visual/lib/test_cobertura.py
  - plugins/visual/lib/test_visual_page.py
  - plugins/handoff/lib/test_handoff_skill.py
  - plugins/intent-guard/lib/test_ledger.py
  - plugins/branches/lib/test_branch_state.py
  - plugins/project-doc/lib/test_journal.py
  - plugins/project-doc/lib/test_graph_map.py
doc-sig: pedro-plugins/.gitignore@gen=3.8#72453ace
---

# Data Stores — onde o dado mora

Sem banco, sem ORM, sem migrations, sem `docker-compose`. Todo depósito é arquivo. O que separa um depósito do outro não é o formato — é **quem faz backup dele**:

- **(A) no repo e rastreado** — cobertura = git + `origin`. É o que viaja pra outra máquina.
- **(B) fora do repo, em `~/.claude/`** — escrito por hooks e pelo daemon do `/visual`. Zero backup.
- **(C) no repo, mas gitignorado** — mora na árvore de trabalho, parece protegido, está fora do índice. Zero backup.
- **(D) o cofre** — fora do repo, no iCloud. É o único depósito de (B)/(C)/(D) com cobertura de terceiro.

⚠️ **O repositório foi recriado hoje como história nova de UM commit órfão.** Isso mudou o que a região (A) protege, e mudou de um jeito que não aparece no `git status`: [confirmado]

```bash
git rev-parse HEAD                              # 2587006652a46b1c53272ccf53f117be8d6c634f
git ls-files | wc -l                            # 252
git ls-files -i -c --exclude-standard | wc -l   # 0   (nada rastreado E ignorado)
git ls-remote origin
#   2587006652a46b1c53272ccf53f117be8d6c634f	HEAD
#   2587006652a46b1c53272ccf53f117be8d6c634f	refs/heads/main
```

Duas consequências que valem para tudo abaixo:

- **`git log` não é mais fonte de história.** Qualquer medida do tipo "N commits neste arquivo" devolve 1 — a história antiga não é ancestral desta.
- **O remote tem exatamente duas refs e nenhuma tag.** Tudo que era protegido por tag (A5b) hoje existe só neste clone. [confirmado — a saída acima é a resposta inteira do `ls-remote`]

E a região (C) é grande: cinco conjuntos que já foram rastreados vivem hoje só no disco, mais um que entrou nela nesta rodada (`.claude/hook-contract.baseline.json`, `.gitignore:45`).

---

## O critério, escrito no próprio `.gitignore`

O arquivo é organizado por **motivo**, não por ferramenta, e o cabeçalho dele é a régra do repo (copiado literal): [confirmado]

```
# Este repositório é PÚBLICO e é instalado por terceiros. A pergunta que decide se um
# arquivo entra não é "isso é útil?" — é "isso pertence a QUEM INSTALA, ou pertence a
# QUEM ESCREVEU?". Só o primeiro sobe.
#
# Ignorar NÃO destrackeia: arquivo já rastreado sai com `git rm --cached`.
# Régua: `git ls-files -i -c --exclude-standard` tem que devolver zero.
```

As cinco seções e as linhas que decidem cada depósito deste doc:

```
1 · REGISTRO DE TRABALHO   .claude/ata/ · .claude/plans/ · .claude/HANDOFF*.md
                           .claude/BRIEFING-*.md · .claude/.project-doc/ · .claude/intent/
                           docs/superpowers/
2 · SEGREDO                scripts/public_repo_terms · .claude/secrets/ · .env · .env.*
                           *.pem · *.key · *.p12 · id_rsa* · .netrc
3 · RETRATO DESTA MÁQUINA  graphify-out/ · .claude/hook-contract.baseline.json
                           .claude/qa-loop/ · .claude/visual/ · .playwright-mcp/
4 · LIXO DE FERRAMENTA     .DS_Store · __pycache__/ · *.bak · *.tmp · …
5 · CÓPIA LOCAL DEFASADA   pi-plugins/
```

A régua fecha: `git ls-files -i -c --exclude-standard` → **0**. [confirmado]

---

## (A) Dentro do repo — versionado

### A5c · `plugins/bootstrap/config/manifest.json` — escrito por máquina, editado à mão

- **Tipo:** JSON rastreado, **293 linhas / 7.161 bytes** (`wc -lc` nesta rodada). [confirmado]
- **Por que ele é o único depósito de máquina que mora no git:** é regenerado a cada `SessionStart` por `plugins/bootstrap/hooks/lib/snapshot.sh` (a partir do `claude plugin list`) e commitado automaticamente pelo `git-sync.sh`. O `marketplace.json`, ao lado, é escrito só por humano.
- **Chaves de topo hoje** (`jq keys`): `description`, `ferramentas_externas`, `marketplaces`, `skills`, `version`. **Só três são geradas** — a lista está literal no script: [confirmado]

  ```
  snapshot.sh:140   GENERATED_KEYS='["version","description","marketplaces"]'
  ```

  `skills` e `ferramentas_externas` são mantidas à mão e sobrevivem por construção: a lista diz o que o script **gera**, não o que preservar, então tudo fora dela passa incólume.
- **Conteúdo medido nesta rodada:** 8 marketplaces · 48 entradas de plugin (31 ligadas) · 18 itens em `skills.permitidas` · 1 item em `ferramentas_externas.itens`. [confirmado]
- **Dois escritores de naturezas opostas.** O snapshot escreve sem perguntar; o humano escreve chave que o snapshot não conhece. A guarda que os faz conviver é a união **aditiva** com o manifest anterior — entrada ausente da amostra fica, porque `claude plugin list` devolve saída incompleta de vez em quando; desinstalar de verdade virou edição explícita do arquivo.
- **Perder o arquivo não perde trabalho** (a próxima sessão o regenera da máquina viva). **Perder as chaves manuais, sim** — `skills.permitidas` e `ferramentas_externas` não têm origem nenhuma além do próprio arquivo.
- ⚠️ **Ele NÃO guarda versão de plugin, e é por isso que bump não o toca.** Cada entrada é `{"name": …, "enabled": …}` e nada mais — verificável com `grep -c '[0-9]\+\.[0-9]\+\.[0-9]\+' plugins/bootstrap/config/manifest.json`, que devolve **0** nesta rodada [confirmado]. Consequência prática, apurada em 2026-08-02: subir a versão de um plugin exige mexer em `plugin.json` e `marketplace.json`, **nunca** aqui. O que toca este arquivo é plugin **novo** (ou ligar/desligar um), e aí quem cobra é `conformance.py:check_catalogo` — **não** o release-gate —, então o commit passa e o desvio só aparece no próximo `bootstrap:setup`.

### Sementes versionadas (o resto de (A) que é depósito)

- `plugins/visual/skills/visual/config.default.json` — semente do `config.json` do `/visual`, que vive em (B2). O default sobe; a escolha do usuário, não.
- `.claude-plugin/marketplace.json` — catálogo da distribuição, escrito só por humano.

Fora esses, **(A) é código e prosa**, não depósito de estado.

---

## (B) Fora do repo, em `~/.claude/` — sem backup nenhum

A regra está escrita no cabeçalho de `_shared/green-cache.sh`, copiada literal: [confirmado]

```
# Estado em ~/.claude/green-suite/ (NUNCA dentro do plugin — o cache
# ${CLAUDE_PLUGIN_ROOT} é reescrito a cada bump de versão).
```

⚠️ **"`~/.claude/`" é o valor efetivo nesta máquina, não o caminho literal de todos.** Parte destes depósitos resolve a pasta por `CLAUDE_CONFIG_DIR` e cai em `~/.claude/` só quando a env var está unset — que é o caso aqui (`echo "${CLAUDE_CONFIG_DIR:-unset}"` → `unset`). **A regra ao mexer em qualquer depósito de (B): escritor e leitor têm que resolver o diretório pela MESMA expressão.** Quando não resolvem, o sintoma não é erro — é o leitor dizendo "está tudo bem" sobre uma pasta vazia que ninguém escreve.

Volumes desta rodada:

```bash
du -sh ~/.claude/plans ~/.claude/visual-state ~/.claude/guardrails ~/.claude/intent \
       ~/.claude/green-suite ~/.claude/context-guard ~/.claude/intent-guard ~/.claude/state
# 2,3M  plans        1,3M  visual-state   680K  guardrails    264K  intent
# 140K  green-suite    0B  context-guard    0B  intent-guard  204K  state

du -sh ~/.claude/state/*
# 104K  state/forma-relato    4,0K  state/intent-guard    96K  state/prose-ceiling
```

⚠️ **`~/.claude/state/` quadruplicou nesta rodada (48K → 204K)** e ganhou um terceiro subdiretório. O crescimento não é lixo: é o juiz de forma que **começou a julgar de verdade** (B9) e uma marca de leitura nova (B10).

### B1 · `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/guardrails/` — 680K · os dois vigias

- **Dois escritores, e eles resolvem o caminho por expressões DIFERENTES.** [confirmado — `grep -n "HOOK_DIR=" plugins/guardrails/hooks/*.sh` nesta rodada]

  ```
  scope-cop.sh:39      HOOK_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/guardrails"
  askq-humanize.sh:45  HOOK_DIR="$HOME/.claude/guardrails"
  ```

  Nesta máquina `CLAUDE_CONFIG_DIR` está unset, então as duas dão a mesma pasta e a divergência é invisível — é exatamente a condição em que ela sobrevive. Numa máquina que seta a var, `scope-cop.*` e `askq.*` se separam em dois diretórios e o auditor passa a varrer o lado errado.
- **`scope-cop.log`** — 420.133 bytes, **974 linhas**. Trilha delimitada por `|` (não TSV: o `log_line` troca qualquer `|` do pedido/diff por `/` pra não quebrar as colunas): `ts · modo · veredito · streak · tem-plano · arquivo · req · diff`. Rotação acima de 5000 linhas mantém as últimas 2000. **Descartável** — é histórico de decisão, não entrada de nada.

  ```bash
  awk -F' \\| ' '{print $2"/"$3}' ~/.claude/guardrails/scope-cop.log | sort | uniq -c | sort -rn
  #  455 deny/PASS   ·  191 deny/SKIP:no-ui-request  ·  158 deny/BLOCK
  #   60 warn/PASS   ·   41 warn/SKIP:no-request     ·   21 warn/SKIP:no-ui-request
  #   21 deny/PASS:circuit-breaker · 9 deny/SKIP:parse-error · 9 deny/SKIP:judge-error
  #    8 warn/WARN   ·    1 deny/SKIP:no-request
  ```

  O modo `warn` é o regime corrente: 130 das 974 linhas são `warn/*`, e **8 são `WARN`** — oito edições que em `deny` teriam sido bloqueadas e passaram com aviso. [confirmado]
- **`scope-cop.mode`** — 5 bytes, valor no disco hoje: `warn`. **Três valores, conjunto fechado:** um `case` aceita `off | deny | warn | ""` (vazio = default de máquina nova) e manda qualquer outro para `MODE_IGNORADO`, que vira uma linha `MODE:invalido` no log. O motivo de o conjunto ser fechado está no arquivo: errar a grafia entregaria o gate mais severo a quem pediu o mais brando. **Configuração.**
  ⚠️ **O arquivo deixou de ser a única forma de o gate estar desligado:** `SCOPE_COP_GATE=0` (linha 28, avaliada antes de ler o stdin) desliga o hook sem tocar no disco. O `.mode` pode dizer `deny` e o gate estar mudo.
- **`scope-cop.blockstreak.<session_id>` / `scope-cop.bypass.<session_id>`** — contador de BLOCKs seguidos (`MAX_STREAK=3` libera 1 edição e zera) e o registro da última liberação. **Por sessão** desde 2026-07-27: o arquivo único fazia os BLOCKs de uma sessão contarem pro freio da outra. Em `warn` o streak é zerado a cada aviso (`echo 0 > "$STREAK_FILE"`), então o circuit-breaker fica inerte enquanto esse for o modo. **Efêmero.**
  ⚠️ **Os dois SEM sufixo continuam no disco, órfãos e imortais** — `scope-cop.blockstreak` e `scope-cop.bypass`, ambos de **2 jul**. Ninguém mais os lê e a poda não os alcança (o padrão exige o ponto do sufixo). Hoje há 5 com sufixo de sessão. Lixo estável, não estado. [confirmado por `ls -la`]
- **`askq.log`** — 17.430 bytes / 48 linhas, do `askq-humanize.sh`. Uma entrada por invocação, limpa ou suja: `=== ts · session · rc` + o `tool_input` cru (`jq -c`, cortado em 4000 chars) + as violações. Rotação acima de 3000 linhas mantém 1000. **O gate julga, não só loga:** [confirmado]

  ```bash
  grep -c '^=== ' ~/.claude/guardrails/askq.log          # 10
  grep -o 'rc=[0-9]*' ~/.claude/guardrails/askq.log | sort | uniq -c
  #   6 rc=0   (limpo)
  #   4 rc=1   (violou → permissionDecision:deny)
  ```

  É o único arquivo desta pasta com valor além do histórico: é o insumo bruto pra afinar as réguas do `askq_lint.py` sobre pergunta real em vez de suposição de formato.
- **`askq.count.<session_id>`** — cap de 3 devoluções por sessão, poda `find -maxdepth 1 -name 'askq.count.*' -mtime +1 -delete`. **1 no disco agora.** Efêmero.
- **Costura verificada nos DOIS lados:** `scope-cop.sh:281` lê `VISUAL_STATE="$HOME/.claude/visual-state/latest.json"` pra reconhecer plano aprovado via `/visual`; `visual_server.mjs` de fato escreve esse `latest.json` no `POST /state`. [confirmado nos dois arquivos]
- **Natureza global: descartável.** Perder a pasta reseta os dois guards para o default (`MODE="deny"`, streak 0, cap 0). Nenhum conhecimento se perde.

### B2 · `~/.claude/visual-state/` — 1,3M · estado de UI do daemon do `/visual`

- **Escrito por** `plugins/visual/server/visual_server.mjs`: `STATE_DIR = path.join(os.homedir(), '.claude', 'visual-state')`, criado com `fs.mkdir(..., {recursive:true})` na subida. Note que **este é o único depósito de (B) que ignora `CLAUDE_CONFIG_DIR` por construção** — `os.homedir()` é fixo. [confirmado]
- **O `POST /state` grava dois arquivos:** `<session>.json` e `latest.json` (o mesmo record + a chave `stateFile` apontando pro per-sessão). Conteúdo: `{session, timestamp, docTitle, state}` — a seleção que o usuário fez na página (aprovar/ajustar/descartar), que a skill lê de volta quando ele digita "ok".
- **Limites do daemon, copiados do arquivo:** `SESSION_RE = /^[a-zA-Z0-9_-]{4,64}$/`, `MAX_BODY_SIZE = 256 * 1024`, `IDLE_TIMEOUT_MS = 30 * 60 * 1000`, `HOST = '127.0.0.1'`, `PORT = Number(process.env.CLAUDE_VISUAL_PORT || 7755)`. Porta ocupada → `EADDRINUSE` → sai com 0 em silêncio (outra instância já serve).
- **Hóspede que não é do daemon: `config.json`.** É a preferência do `/visual` (`auto_mode` + os `auto_triggers`), escrita pela **skill**; o daemon nunca a toca. Mudou de casa porque `${CLAUDE_PLUGIN_ROOT}` é cache reescrito a cada bump e a escolha do usuário sumia na atualização. Semente versionada em `plugins/visual/skills/visual/config.default.json`.
- **Volume:** 1,3M, **282 entradas** (`ls ~/.claude/visual-state | wc -l`), incluindo um `.daemon.log` e arquivos de teste (`test-live-abc123.json`, `test-session-abc123.json`). **Não há prune.** [confirmado]
- **Natureza: descartável**, com uma exceção de grau — o `config.json` é preferência, não sessão, e não deve entrar num eventual prune por idade.

### B3 · `~/.claude/green-suite/` — 140K · cache de "suite verde"

- **Escrito por** `_shared/green-cache.sh` (fonte-da-verdade) e suas cópias vendoradas em `plugins/ship/hooks/` e `plugins/qa-loop/lib/`. Função `green_cache_mark`.
- **Diretório e TTL vêm de env com default, copiados literal:** [confirmado]

  ```bash
  GREEN_SUITE_DIR="${GREEN_SUITE_DIR:-$HOME/.claude/green-suite}"
  GREEN_SUITE_TTL_SECS="${GREEN_SUITE_TTL_SECS:-86400}"
  ```
- **Chave:** `<cksum(root)>-<tree_hash>`, com `tree_hash` = `git write-tree` sobre um index temporário (`read-tree HEAD` + `add -A`) — inclui untracked. Qualquer edição, criação ou remoção muda a chave e invalida o hit. `git stash create` e `HEAD + diff` não serviriam: ignoram untracked → falso HIT.
- **Formato:** TSV, uma linha por marca — `scope \t epoch \t iso-ts \t writer`. `scope` é `full` ou `app:<nome>`; `full` satisfaz qualquer consulta.
- **Natureza: CACHE PURO.** As três garantias estão no cabeçalho: fail-open na direção segura (qualquer erro → MISS → a suite roda), **gate vermelho nunca grava**, e TTL **por linha** (epoch da linha, não mtime do arquivo — um mark novo não ressuscita registro vencido).
- **Único depósito de (B) que se poda sozinho:** `green_cache_mark` roda `find "$GREEN_SUITE_DIR" -type f -mtime +7 -delete`. Mesmo assim tem **35 arquivos** hoje — a poda é de 7 dias e o ritmo de gates é maior que isso.

### B4 · `~/.claude/intent-guard/` — 0B · só o kill-switch

- **Único arquivo previsto:** `mode`. **Seis scripts do plugin o mencionam pelo mesmo caminho** (`grep -rl 'intent-guard/mode' plugins/intent-guard/hooks/` → `capture-prompt.sh`, `delivery-audit.sh`, `mark-work.sh`, `plan-gate.sh`, `task-checkpoint.sh` e o teste `test_hooks_capture.sh`, que faz backup/restore dele). [confirmado]
- **Estado atual: o diretório existe e está VAZIO (0B)** — sem `mode`, o guard opera no default. Configuração, descartável.
- ⚠️ **Colisão de nome nova nesta rodada:** existe agora um `~/.claude/**state**/intent-guard/` (B10), que é outro diretório, com outro dono e outra natureza. `~/.claude/intent-guard/` é kill-switch e está vazio; `~/.claude/state/intent-guard/` é marca de leitura e tem conteúdo. Quem apagar "o diretório do intent-guard" pelo nome apaga o errado. [confirmado por `ls -la` nos dois]

### B5 · `~/.claude/context-guard/` — 0B · nada mora aqui

- O único vínculo é um **comentário** em `context-guard.sh`: *"Kill-switch: crie `~/.claude/context-guard/mode` com 'off' pra desligar o guard globalmente"*. O diretório existe e está vazio. [confirmado]
- **O estado real mora em `/tmp`, chaveado por sessão** — ver a seção de sentinelas abaixo.
- ⚠️ **Os dois scripts abortam sem `jq`** (`command -v jq >/dev/null 2>&1 || exit 0`, primeira linha executável de cada um). É fail-open **na direção do depósito**, não só do usuário: sem `jq` o `session_id` sai vazio, e aí o guard leria o contador da sessão errada e o reset apagaria o sentinel de **outra** sessão. A guarda protege a chave do estado, não a tela.

### B6 · `~/.claude/intent/` — 264K · **fallback**, não o depósito principal

O ledger do intent-guard **deste projeto não está aqui**. `plugins/intent-guard/lib/ledger.py:intent_dir` resolve assim: [confirmado, corpo lido]

```python
root = project_root(cwd)                       # git rev-parse --show-toplevel, ou MARKERS
if root:
    if os.path.realpath(cwd) == os.path.realpath(root):
        return os.path.join(cwd, ".claude", "intent")
    return os.path.join(root, ".claude", "intent")
slug = re.sub(r"[^a-zA-Z0-9]+", "-", os.path.abspath(cwd)).strip("-")
return os.path.join(os.path.expanduser("~/.claude/intent"), slug)
```

- Como este repo é git, o caderno vive em `.claude/intent/` (região C). O `~/.claude/intent/` só recebe os cwd **sem** raiz de projeto — e é o que o disco mostra: slugs de caminhos de outros projetos, nenhum de pedro-plugins.
- **Natureza: histórico de intenção, insubstituível dentro do seu escopo, sem backup.** Vale pros projetos que caem no fallback, não pra este.
- Provado por `plugins/intent-guard/lib/test_ledger.py`, que roda `ledger.py resolve-dir` num repo git temporário e afirma `== os.path.join(repo, ".claude", "intent")`. Suíte verde nesta rodada. [confirmado]

### B7 · `~/.claude/plans/` — 2,3M, 182 arquivos · os planos do HARNESS (≠ A4)

- **Nenhum escritor neste marketplace.** Só leitores (`qa-loop` procura `.claude/plans/*.md` como plano de implementação; `principles` procura a seção "Princípios de Sistema") e uma proibição explícita em `plugins/visual/hooks/pre-exitplan-visualize.sh`: *"não busque em `~/.claude/plans/`"*.
- **Quem escreve é o harness do Claude Code.** [inferido — verifiquei a ausência de escritor no repo; não inspecionei o harness]
- **Natureza: insumo insubstituível e sem backup**, e que **encolhe sozinho**: 182 arquivos hoje, contra 209 na rodada anterior, 213 na anterior a essa e 226 na anterior àquela — **27 sumiram em um dia**, a maior queda já registrada aqui. Um depósito insubstituível, sem backup, que diminui sem que nada neste repo apague nada é o pior par de propriedades do inventário. [medido; a causa da remoção é do harness — inferido]
- ⚠️ **A colisão de nome é a armadilha:** `~/.claude/plans/*.md` é do harness e não tem rede; `<repo>/.claude/plans/*.plan.json` é do marketplace (A4) e hoje **também** não tem — os dois caminhos parecidos apontam pra garantias diferentes, e nenhuma delas é backup.

### B8 · `${CLAUDE_CONFIG_DIR:-~/.claude}/state/prose-ceiling/` — o orçamento do teto de prosa

- **Escrito por** `plugins/bootstrap/hooks/stop-prose-ceiling.py`, hook de `Stop`. O caminho é resolvido por env, com a mesma linha do leitor: [confirmado nos dois arquivos]

  ```python
  # stop-prose-ceiling.py          e          lib/conformance.py
  CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
  ESTADO = CLAUDE_DIR / "state" / "prose-ceiling"
  ```

  O comentário no hook nomeia o defeito que essa igualdade conserta: com `Path.home()` fixo, quem usa `CLAUDE_CONFIG_DIR` fazia o hook escrever num lugar e o verificador ler noutro, e o relatório dizia "nenhuma resposta furou o teto" com o teto furado — *"Falha silenciosa."*
- **Três tipos de arquivo, e eles guardam coisas diferentes:**
  - `<sha1[:16]>` — **contador por resposta bloqueada**, 1 byte cada. Chave = `sha1(session_id + texto_INTEIRO_da_resposta)[:16]`; teto `MAX_BLOQUEIOS = 2`. A chave usa o texto inteiro de propósito: com `texto[:200]`, e com o output style mandando a primeira linha ser estável, duas respostas diferentes dividiam o mesmo orçamento — a colisão era o caso comum. **15 no disco hoje** (17 entradas no diretório, menos `batidas.log` e o `.DS_Store`).
  - **`batidas.log` — é o que faz o guarda ser auditável.** Uma linha JSON por **execução**, não só por bloqueio: `{ts, sessao (8 chars), motivo, linhas, teto}`. O comentário diz por que nasceu: sem ele, *"o guarda não rodou"* e *"o guarda rodou e aprovou"* eram indistinguíveis, e uma resposta de 9 linhas passou sem ninguém notar. **32.611 bytes / 341 linhas hoje**, contra 42 execuções na rodada anterior: [confirmado]

    ```
    motivos: "sem texto do assistente" 163 · aprovou 146 · stop_hook_active 25 · barrou 7
    ```

    **`barrou` 7 é a novidade que importa:** na rodada anterior o guarda tinha 0 bloqueios registrados. Ele passou a barrar de verdade.
  - `bypass.log` — JSONL, uma linha por desistência (`{session, linhas_prosa, problemas, trecho}`), gravado quando o contador bate em 2 e o hook para de bloquear pra não travar a sessão. **Continua sem existir no disco** — os 7 `barrou` nunca chegaram a duas reincidências na mesma resposta. [confirmado — `wc -l` devolve `No such file or directory`]
- **Quem lê — passaram a ser DOIS consumidores, e eles leem arquivos diferentes:** [confirmado]
  - `plugins/bootstrap/lib/conformance.py`, em duas checagens — `check_teto_rodou` lê o `batidas.log` (ausência = desvio *"o guarda de prosa nunca executou"*; última batida > 24h = desvio *"está mudo"*) e `check_bypass_teto` lê **só** o `bypass.log` (ausência = conforme). **Nenhuma das duas olha os contadores.**
  - **`plugins/intent-guard/lib/ledger.py:furos_da_regua` — NOVO.** Lê **só** o `bypass.log`, e trata **toda** linha dele como furo (`lambda d: True`). É o segundo lugar do repositório onde este arquivo vira número, e o primeiro que o mostra ao dono em vez de ao verificador de máquina — ver B10.
- ⚠️ **Nada poda os contadores.** Sem `find -mtime`, sem TTL, sem limpeza no `SessionStart`. O único `rm` do sistema é o que o `conformance.py` **sugere em texto**, e ele mira o `bypass.log`. Cada resposta reprovada deposita 1 byte que fica pra sempre.
- **O teto é premissa, não preferência:** `TETO_PADRAO = 6`, e `PROSE_CEILING_MAX` só **ajusta o número** (`0` ou lixo caem no padrão). Desligar exige `PROSE_CEILING=0`, que derruba o hook inteiro — e mesmo aí ele grava uma batida `kill-switch` antes de sair. Com o hook desligado o depósito não nasce.
- **Regra nova nesta rodada, e ela muda o que entra no log:** pergunta fechada do usuário passou a exigir **veredito na 1ª linha** da resposta. O hook lê a última fala do usuário, casa `PERGUNTA_FECHADA` na cauda (200 chars) e exclui as abertas via `PERGUNTA_ABERTA`; se a primeira linha não casar `ABRE_COM_VEREDITO`, o problema `"pergunta fechada sem veredito na 1a linha"` entra na lista e a resposta é barrada. [confirmado no código]

### B9 · `${CLAUDE_CONFIG_DIR:-~/.claude}/state/forma-relato/` — o juiz de forma do relato

Depósito **novo nesta rodada**, irmão do B8 e deliberadamente diferente dele: o teto de prosa é mecânico, roda todo turno e custa zero token; **este chama um modelo**, então só roda quando a resposta é um RELATO.

- **Escrito por** `plugins/bootstrap/hooks/stop-forma-relato.py`. O caminho tem **variável própria**, e o motivo está no comentário: [confirmado]

  ```python
  CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
  # estado com var propria: isolar o teste via CLAUDE_CONFIG_DIR tirava a credencial
  # do `claude -p` junto, e o juiz passava a aprovar tudo por fail-open.
  ESTADO = Path(os.environ.get("FORMA_RELATO_STATE", CLAUDE_DIR / "state" / "forma-relato"))
  ```
- **O gatilho é medido no próprio texto:** é relato quando há pelo menos um bloco ` ``` ` **e** ≥ `MIN_PROSA = 2` linhas de prosa fora dos blocos. Resposta curta e conversa não chegam ao modelo — mandar cada turno custaria segundos em todos eles.
- **Dois tipos de arquivo, mesmo desenho do B8:**
  - `<sha1[:16]>` — contador anti-loop por resposta, `MAX_BLOQUEIOS = 2`, chave `sha1(session_id + texto)[:16]`. **20 no disco** (21 entradas menos o `batidas.log`) — eram **zero** na rodada anterior.
  - `batidas.log` — uma linha JSON por execução: `{ts, sessao, motivo, veredito}`. **104K de diretório, 228 linhas hoje** (eram 12).
- ✅ **O 🔴 da rodada anterior CAIU: o juiz passou a julgar.** [confirmado]

  ```
  motivos:    "nao e relato" 79 · "sem texto" 74 · julgou 50 · stop_hook_active 25
  vereditos:  passa 30 · reprova 20      (dos 50 `julgou`)
  ```

  Três coisas mudaram no que o depósito guarda: (1) `julgou` saiu de 0 para 50, então o modelo está sendo chamado; (2) `nao e relato` **79** apareceu como motivo — é o gatilho recusando gastar token em resposta que não é relato, e ele é hoje o motivo mais frequente; (3) **o campo `veredito` deixou de ser sempre nulo** — as 20 reprovações trazem o defeito em texto livre, do tipo *"Resultado no parágrafo 3, primeira linha não diz nada"*. Esse texto é o único registro do que a régua reprovou, e não existe em lugar nenhum além deste arquivo.
- **Wiring confirmado** em `plugins/bootstrap/hooks/hooks.json`, no mesmo array `Stop` do teto de prosa: [confirmado]

  ```json
  "Stop": [{ "hooks": [
     {"type":"command","command":"python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/stop-prose-ceiling.py\"","timeout":10},
     {"type":"command","command":"python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/stop-forma-relato.py\"","timeout":30}
  ]}]
  ```
- **Quem lê — também passaram a ser DOIS, e eles filtram o mesmo arquivo por regras diferentes:** [confirmado]
  - `plugins/bootstrap/lib/conformance.py:check_juiz_rodou`. Só cobra de quem tem o bootstrap habilitado (varre `enabledPlugins` do `settings.json` por `bootstrap@`), e então: arquivo ausente → desvio *"o juiz de forma nunca executou"*; `juiz sem resposta` > `julgou` → desvio *"o juiz está mudo"*, com a causa mais comum nomeada (`claude -p` sem credencial sai rc=1 e o fail-open aprova tudo); última batida > 24h → desvio; senão, conforme. **Com 50 `julgou` e 0 `juiz sem resposta`, o check passa por mérito agora** — o furo descrito na rodada anterior ("passa mesmo sem nunca ter julgado") continua existindo como furo, mas deixou de ser o caso deste disco.
  - **`plugins/intent-guard/lib/ledger.py:furos_da_regua` — NOVO.** Conta como furo **só** a linha que satisfaz `motivo == "julgou" and veredito != "passa"`; `passa`, `nao e relato`, `sem texto` e `stop_hook_active` não entram. É por isso que o mesmo arquivo de 228 linhas vira o número **20** — ver B10.
- **Kill-switch e modelo, copiados do arquivo:** `FORMA_RELATO=0` desliga (e grava a batida `kill-switch`); `FORMA_RELATO_MODEL` escolhe o modelo (default `haiku`); `TIMEOUT_S = 25`. O subprocesso herda `FORMA_RELATO="interno"` pra o juiz não chamar a si mesmo — e nesse modo nem batida grava.
- **Natureza: descartável, com uma ressalva nova.** O orçamento de bloqueio e o registro de execução se refazem. **O texto dos 20 vereditos de reprovação, não** — é a única lista escrita de onde a régua de forma falhou, e nada o regenera.

### B10 · `${CLAUDE_CONFIG_DIR:-~/.claude}/state/intent-guard/olhado` — 17 bytes · a marca de "até onde o dono já viu"

**Depósito novo nesta rodada**, e o menor do inventário: um arquivo, um número.

- **Escrito e lido por** `plugins/intent-guard/lib/ledger.py:furos_da_regua` e `cmd_status`. O caminho sai da mesma expressão dos B8/B9: [confirmado, copiado do arquivo]

  ```python
  claude = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
  marca = claude / "state" / "intent-guard" / "olhado"
  ```
- **Conteúdo: um epoch em texto, e só.** Valor no disco hoje: `1785538855.766836` (17 bytes, mtime de 31/jul 20:00). É a hora da última vez que o dono viu a contagem de furos.
- **Para que serve:** `furos_da_regua()` devolve `(total, novos, fontes, marca)`. O `total` sai do log inteiro; o `novos` conta só as linhas com `ts` maior que a marca. Os dois números saem do MESMO log append-only, então mostrar ambos *"não obriga a escolher entre perder o histórico e perder a leitura do que é novo"* [confirmado, docstring].
- **Quando a marca é reescrita:** dentro de `cmd_status`, e **só quando há cobrança permanente viva** (`if st["standing"]`) — restrição do dono que não conclui. Sem nenhuma restrição no caderno, a contagem não é exibida e a marca não avança.
- **Estado medido rodando o próprio código nesta rodada:** [confirmado]

  ```bash
  python3 -c "import sys; sys.path.insert(0,'plugins/intent-guard/lib'); import ledger; print(ledger.furos_da_regua())"
  # (20, 20, 1, PosixPath('~/.claude/state/intent-guard/olhado'))
  ```

  **`fontes = 1`, não 2** — o `bypass.log` do B8 não existe, então só o `batidas.log` do B9 respondeu. `novos == total` porque a marca é de 31/jul e as 20 reprovações são de hoje.
- ⚠️ **`fontes` existe justamente para log ausente não virar zero furo.** Quando as duas fontes faltam, o status escreve *"SEM REGISTRO nesta máquina — os guardas não deixaram rastro, e isso não quer dizer zero furo; quer dizer que ninguém sabe"*. É o mesmo defeito que já produziu o elogio *"nenhuma resposta furou o teto"* com o teto furado. [confirmado — o caso está no `test_ledger.py`, que afirma `(0, 0, 0)` sem fonte nenhuma e `fontes == 2` com as duas]
- **Natureza: descartável, com efeito visível.** Apagar não perde furo nenhum (o `total` continua exato); zera o `desde a última vez que você olhou`, e a próxima leitura mostra o histórico inteiro como novidade.
- **Fail-open na escrita:** `except OSError: pass` — *"não poder marcar nunca derruba o status"*. A consequência é silenciosa e vale saber: num disco somente-leitura o `novos` fica permanentemente igual ao `total` e ninguém é avisado.

### B11 · `${CLAUDE_CONFIG_DIR:-~/.claude}/sovai/` — 0B · o interruptor da missão autônoma

- **Nasceu em 2026-08-02**, com o gate que mantém o `/sovai` no motor Workflow.
- **Três arquivos, todos chaveados por sessão** [confirmado — `pretooluse-sovai-motor.sh`]:
  - `ativo-<session_id>` — **arquivo vazio; o que importa é existir.** Aceso pela casca da skill antes de disparar o Workflow, apagado na entrega. Enquanto existe, todo disparo de sub-agente naquela sessão é negado.
  - `bloqueios-<session_id>` — o contador do cap (3). Sanitizado na leitura: lixo no arquivo vira `0`, nunca erro de shell.
  - `desistencias.log` — append-only, uma linha por vez que o cap estourou. Existe porque *desistir em silêncio* é o defeito que o `bypass.log` do teto de prosa registrou primeiro.
- **Por sessão, nunca global** — mesma lição do `context-guard` e do `scope-cop` (§1.5 de `patterns.md`): marcador global faria uma sessão em sovai tirar de **todas** as outras o direito de despachar sub-agente.
- **Perder o diretório não perde trabalho.** É interruptor, não registro: some o `ativo-*` e o gate volta a ser mudo. O único conteúdo com valor histórico é o `desistencias.log`, e ele é diagnóstico, não dado.
- ⚠️ **O risco real é o oposto: o arquivo ficar aceso.** A casca apaga na entrega, mas missão interrompida no meio (sessão morta, `/clear`) deixa o sinal aceso e **a sessão inteira segue sem despachar sub-agente**, sem ninguém saber por quê. Não há poda por idade — diferente do `scope-cop`, que ganhou `find … -mtime +1 -delete` no mesmo commit em que nasceu. Diagnóstico: `ls ~/.claude/sovai/`.
- **Estado medido nesta rodada** [confirmado]:

  ```bash
  du -sh ~/.claude/sovai      # 4,0K
  ls -1 ~/.claude/sovai       # 4 arquivos
  # ativo-816f95e2-…   ativo-a5a22a2f-…   ativo-dc5e6c3a-…   bloqueios-a5a22a2f-…
  ```

  🔴 **O risco previsto acima se realizou, e está medido:** dos **três** sinais acesos, só um é desta sessão. Os outros dois pertencem a sessões de **outros projetos**, com transcript mexido há 2 e 10 minutos — ou seja, **vivas e sem poder despachar sub-agente**. O sinal é por sessão, então uma não contamina a outra: o estrago é local a cada uma. [confirmado — 2026-08-02, `find ~/.claude/projects -name '<sid>*.jsonl'` para cada sinal]

- ✅ **A inferência que justificava o cap foi MEDIDA em 2026-08-02, e ela valia** [confirmado]: com `ativo-<sid>` aceso, um Workflow de um agente completou (11 chamadas de ferramenta, 117s) e o contador `bloqueios-<sid>` **não se moveu** — os agentes de `Workflow` **não** passam por `PreToolUse[Agent]`, então o gate não mata o próprio motor. O cap de 3 permanece assim mesmo: ele é o contrato anti-loop do repo (`patterns.md` §1.3) e cobre o runtime do Workflow mudar de caminho numa versão futura.

### B11a · `${CLAUDE_CONFIG_DIR:-~/.claude}/state/anuncio-acao/` — o log do gate do anúncio

- **Nasceu em 2026-08-02** com `plugins/visual/hooks/stop-anuncio-sem-acao.py`. **Ainda não existe no disco**: o hook só cria o diretório quando arma pela primeira vez. [confirmado — `ls` devolve ausente]
- **Dois tipos de arquivo**, mesma família do `forma-relato` (B9) e do `prose-ceiling`:
  - `batidas.log` — uma linha JSON por **passagem**, não só por bloqueio: `{ts, sessao (8 chars), motivo, trecho}`. Os motivos são `kill-switch`, `stop_hook_active`, `espera o usuario`, `sem plano aberto`, `desistiu` e `devolveu` — e só o último carrega o `trecho` do que o agente escreveu.
  - `n-<sessao>-<sha1[:12] do cwd>` — contador anti-loop, teto `MAX_DEVOLUCOES = 2`. A chave usa digest do cwd, **não** `hash()` do Python: `hash()` de string é randomizado por processo, então a chave mudaria a cada turno e o cap nunca contaria.
- **Por que o log é o ativo:** a detecção é lexical e o teto é conhecido — promessa escrita fora dos padrões passa batido. O `batidas.log` é o único jeito de medir se o léxico está largo ou estreito demais, e de auditar falso positivo depois do fato.
- ⚠️ **Nenhum verificador o lê ainda.** Diferente do `forma-relato`, que o `conformance.py` cobra em duas checagens, este log nasce sem par: se o hook parar de rodar, nada acusa.

---

## (C) Dentro do repo, mas gitignorado — some se a máquina sumir

### A1 · `.claude/.project-doc/findings.jsonl` — o journal do conhecimento

- **Tipo:** JSONL append-only, 1 evento por linha. **3.353.192 bytes / 1.133 linhas.** [confirmado — `wc -lc` nesta rodada]
- **Fora do git**, com a pasta inteira ignorada:

  ```bash
  git check-ignore -v .claude/.project-doc/findings.jsonl
  #   .gitignore:21:.claude/.project-doc/	.claude/.project-doc/findings.jsonl
  git ls-files .claude/.project-doc/      # (vazio)
  ```
- **Natureza: INSUBSTITUÍVEL, e sem cópia nenhuma.** Não existe regenerador. A matéria-prima (transcripts `.jsonl` das sessões) é local à máquina e não viaja — a mineração vive em `journal.py:collect_transcripts`, que lê `discover_all_transcripts(project_root)`. **Perder este disco perde os 1.133 eventos.** [confirmado]
- ⚠️ **O código ainda afirma o contrário.** `journal.py`, no cabeçalho da seção de estado, diz literal: `# Estado: .claude/.project-doc/  (versionado — é o veículo do conhecimento)`. O `.gitignore:21` desmente. O comentário é de antes do destrack e não acompanhou. [confirmado nos dois arquivos]
- **Quem escreve:** `journal.py:append_events()` — abre em modo `"a"` e escreve `json.dumps(e) + "\n"`. **Não existe caminho de reescrita nem truncamento no arquivo.** Chamadores: `run_update`, `run_invalidate`, `run_curate`, `run_adopt`, `run_fuse`.
- **Quem lê:** `journal.py:read_events` → `journal.py:fold`; `plugins/project-doc/lib/doc_lint.py` (monta o caminho na linha 153); `plugins/project-doc/lib/pattern_check.py` (check `(c)`: falha se o journal não existir, linha 339). Costura confirmada nos dois lados. [confirmado]

**Formato — três eventos, e o estado vivo é o *fold* deles em ordem de append** (evidência: `journal.py:fold`, corpo lido):

```
{"ev":"discovered","id":<sha1[:16]>,"raw_kind":…,"text":…,"anchors":[…],"source":{…},"scrubbed":bool,"ts":epoch}
{"ev":"invalidated","target":<id>,"reason":"…","ts":epoch}
{"ev":"curated","target":<id>,"text":"…","ts":epoch}
```

- `discovered` cria, e **só a primeira ocorrência de um id conta** (`if fid and fid not in state`).
- `invalidated` mata sem apagar o `discovered`. A docstring de `fold` é explícita: *"Um id invalidado permanece morto mesmo que re-apareça num discovered posterior"* — a morte é definitiva até uma curadoria/rediscovery.
- `curated` sobrepõe o texto exibido; `live_findings` troca `text` por `curated` quando presente, filtra o que não está `live` e ordena por `source.ts`.
- `id = sha1(texto_normalizado + "|" + raw_kind)[:16]` (`finding_id`) → append idempotente: re-minerar a mesma fala não duplica.

**Composição real hoje** (derivada mecanicamente nesta rodada):

```
eventos:   discovered 1120 · invalidated 11 · curated 2        (= 1133 linhas)
raw_kind:  user_directive 584 · commit 213 · handoff 154 · ask_answer 117
           gotcha 26 · doc_nuance 14 · memory 9 · tool_rejection 3
scrubbed:  60
```

**Por que um arquivo cheio de conversa verbatim pode existir num repo público:** todo texto passa pelo scrubber **na escrita**, não no `git add`. `run_update` chama `scrub(c["text"])` e, havendo captura, `stash_secrets(secrets, project_root)` **antes** de montar o evento; o mesmo vale para `run_invalidate` (o `reason`), `run_curate` e `run_adopt`. O valor-segredo sai do arquivo e vira o placeholder `‹cofre:LABEL:8hex›`; nome, host, porta e contexto ficam. Os **60** eventos com `scrubbed: true` são os que tiveram captura. O scrubber segue sendo a barreira mesmo com o arquivo fora do índice — é o que impede que um `git add -f` acidental publique um valor. [confirmado]

O `scrub()` é um scorer em **quatro camadas**, cada span redigido sendo pulado pelas seguintes (ordem lida do corpo): (1) estruturado — PEM → connection string → JWT → prefixos de provider; (1.5) par JSON/dict aninhado; (2) `chave=valor` de uma linha; (3) prosa — palavra-sinal perto de token de alta entropia; (4) na dúvida — token de alta entropia vira `‹revisar?›`, preservado e sinalizado. Política: **nomes e contexto sim, valores não**; host, IP, porta, path, sha e uuid são preservados de propósito.

⚠️ **Armadilha de ordem, e ela morde este doc especificamente.** `findings.jsonl` está no `scope:` deste arquivo, então **qualquer `journal.py adopt` rodado depois do carimbo deixa este doc `stale` na hora** — o arquivo de escopo fica mais novo que o carimbo, sem uma linha de conteúdo ter envelhecido. A ordem certa: **adotar no journal primeiro, carimbar depois.** Corolário: as medições de volume acima são as que envelhecem mais rápido de toda a doc.

### A2 · `.claude/.project-doc/ledger.json` — o que faz a rodada ser delta

- **Tipo:** JSON único, sobrescrito a cada rodada (`journal.py:save_ledger`, modo `"w"` + `json.dump`). **17.111 bytes.** Gitignorado pela mesma `.gitignore:21`.
- **Três chaves, lidas do arquivo real:** [confirmado]

  ```
  mined_sessions     dict com 267 entradas   {session_id: mtime_do_jsonl}
  last_commit        "2587006652a46b1c53272ccf53f117be8d6c634f"
  distilled_hashes   {}  (vazio)
  ```
- **`mined_sessions` guarda mtime, não "já vista"** — e isso é o que permite re-minerar uma sessão que **cresceu** depois de deixar de ser a ativa. `load_ledger` migra o formato antigo (lista) para `mtime 0`, forçando re-mineração.
- **`last_commit` é a base do delta forward e do backward.** Há uma guarda explícita: `_commit_reachable()` verifica se o sha ainda existe, porque *"um rebase/amend/reset órfã o last_commit do ledger; usá-lo como base de range (`orfão..HEAD`) faz o git sair 128 e perderíamos TODOS os commits"*. ✅ **Essa guarda é exatamente o que salvou esta rodada:** o repo virou história órfã hoje, e o `last_commit` gravado já é o `2587006` novo. [confirmado]
- **Natureza: RECONSTRUÍVEL, com custo.** Perder o ledger não perde conhecimento — perde a memória de "o que já foi minerado", e a próxima rodada vira um cold-start (que `collect_commits` trunca em `CAP = 1000` commits, com aviso em stderr, nunca em silêncio).
- **`backups/`** ao lado: 712K, 6 diretórios datados (`20260621T002445Z` … `20260731T221815Z`), o mais recente de hoje. Também gitignorado.

### A3 · `graphify-out/` — 75M · o knowledge graph desta máquina

- **Gitignorado desde sempre nesta história** (`.gitignore:44`, seção "RETRATO DESTA MÁQUINA — regenerável, e carimba caminho absoluto e hostname. Sobe o gerador, nunca a saída").
- **`graph.json`** — 3.107.545 bytes. Chaves de topo: `built_at_commit`, `directed`, `graph`, `hyperedges`, `links`, `multigraph`, `nodes`. Medido nesta rodada: [confirmado]

  ```
  nodes 3791 · links 4961 · hyperedges 12
  source_file distinto: 259        communities: 376
  built_at_commit: 2587006652a46b1c53272ccf53f117be8d6c634f   (== HEAD)
  relações: contains 3078 · calls 1193 · rationale_for 260 · imports 162
            defines 133 · references 61 · method 28 · imports_from 21
  ```

  ⚠️ **Estes números valem para este commit e só.** Todo modo que escreve doc roda `graphify update --force` antes; o que é utilizável é o par número + `built_at_commit`, nunca o número solto.
- **`.graphify_labels.json`** — 10.227 bytes, **376 labels, dos quais 50 são nomeados** (o resto é o placeholder `Community NNN`, que `graph_map._is_named` descarta). [confirmado]
- **`manifest.json`** — 73.403 bytes, **439 chaves**, das quais **106 são de `pi-plugins/`**, que não está no grafo. Contar o manifest é medir o índice, não o mapa: o grafo enxerga 259 arquivos-fonte distintos. [confirmado]
- **`GRAPH_REPORT.md`** — 84.095 bytes, relatório humano gerado junto. O cabeçalho dele traz a contagem de corpus (`252 files · ~643.929 words`) e o `Built from commit: 25870066`.
- **Como o project-doc consome:** `plugins/project-doc/lib/graph_map.py` destila o grafo num mapa compacto. O que ele muda em relação ao arquivo cru — e o que é **teto**, não medida: [confirmado, saída real do run]

  ```bash
  python3 plugins/project-doc/lib/graph_map.py --project-root .
  # stats: nodes 3791 · links 4961 · hyperedges_total 12
  #        communities_named 30 · god_nodes 60
  # files listados: 40      hyperedges retidas: 6
  # comunidade genérica descartada: "Plugin Manifest Metadata" (18 comunidades)
  ```

  - **`god_nodes: 60` é o corte `top_gods=60`, não uma contagem** — não sobe nem que o repo dobre.
  - **`communities_named: 30` ≠ os 50 labels nomeados** do arquivo: o mapa deduplica por nome e joga fora quem aparece em ≥ `GENERIC_COMMUNITY_MIN = 4` comunidades (metadado repetido, não módulo).
  - **`hyperedges: 6` de 12** — o filtro é `confidence_score >= 0.85`.
  - **Fan-in semântico exclui `STRUCTURAL_RELATIONS = {"contains", "defines", "method"}`**; `contains` sozinho é 3078 das 4961 arestas, e sem a exclusão o ranking viraria "quem tem mais símbolos", não "quem importa".
  - Degrada gracioso: sem grafo, `run()` devolve `{"available": false}` e o exit code continua 0 — ausência de grafo não é erro.
- **Natureza: RECONSTRUÍVEL por comando** (`graphify update . --force`, AST, sem LLM). É o depósito mais pesado do repo (75M com os snapshots datados de junho e julho) e o mais barato de perder.

### A4 · `<repo>/.claude/plans/*.plan.json` — os planos ticáveis

- **13 planos, 132K** (115.686 bytes de JSON). Gitignorado por `.gitignore:18` (seção "REGISTRO DE TRABALHO"). [confirmado — `git check-ignore -v .claude/plans/` → `.gitignore:18`]
- ⚠️ **A docstring do módulo ainda afirma o contrário**, e é a segunda contradição código-vs-gitignore deste doc: `plan_state.py` diz literal *"`<raiz-do-projeto>/.claude/plans/<id>.plan.json` — VERSIONADO no git de propósito: a dor é perda, e /tmp ou `${CLAUDE_PLUGIN_ROOT}` morrem no /clear e no bump"*. **A dor citada continua real; a cobertura que a resolvia não existe mais.** [confirmado nos dois arquivos]
- **Estado hoje**, derivado dos arquivos: [confirmado]

  ```
  2026-07-27-arvore-do-plano-no-visual         done       15/15
  2026-07-28-design-como-doc-autoral           done         9/9
  2026-07-28-plugin-branches                   done       12/12
  2026-07-28-varredura-de-contrato-dos-plugins done       20/20
  2026-07-29-furos-do-gate-de-deploy           abandoned  11/12
  2026-07-30-bootstrap-instalacao-nova         done       10/10
  2026-07-30-intent-guard-catraca              done         9/9
  2026-07-30-marketplace-presenteavel          done       15/15
  2026-07-31-fechar-a-regua-e-publicar         active      10/11
  2026-07-31-fechar-os-14-pedidos-abertos      abandoned    0/10
  2026-07-31-repo-limpo-do-zero                abandoned  13/18
  2026-08-01-formato-de-plano                  abandoned    0/10
  2026-08-01-formato-de-plano-hierarquico      active       0/20
  ```

  ⚠️ **Dois planos ATIVOS ao mesmo tempo.** `pick_plan` recusa adivinhar nessa situação (*"há %d planos ativos (…) — diga qual"*), então todo comando sem `--plan` explícito falha até um deles ser encerrado. [confirmado — a recusa está em `plan_state.py:pick_plan`]

**O QUE O ARQUIVO GUARDA mudou nesta rodada — a tarefa ganhou cinco campos e o plano ganhou um bloco.** [confirmado, lidos em `plan_state.py:erros_do_plano` e `plan_state.py:_requisitos_do_plano`]

Por tarefa, ao lado de `id`/`title`/`desc`/`status`/`evidence`/`done_at`:

```
requisito   obrigatório em tarefa NOVA · ≤ 40 chars · o id do requisito que ela atende,
            EXATAMENTE UM ("tarefa que atende dois requisitos são duas tarefas")
pronto      obrigatório em tarefa NOVA · ≤ 140 chars · COMO se prova que terminou
grupo       opcional · ≤ 40 chars · a natureza do trabalho (Backend · Tela · Teste)
pendencia   opcional · ≤ 140 chars · a decisão que falta. TRAVA o tick enquanto existir
decidido    opcional · objeto {escolha, pergunta, porque} · a decisão tomada sem o dono
```

No topo do plano, ao lado de `phases`:

```json
"requisitos": [{"id": "S-1.1", "titulo": "...", "ca": "...",
                "ancora": "Art. 6", "epico": "E1 — Base"}]
```

- **Por que o bloco existe no próprio plano:** o requisito é obrigatório, mas o *lugar* dele é opcional. Projeto com documento de requisitos aponta pra lá; projeto sem documento — *"o caso deste repositório, que não tem PRD"* — declara aqui. Sem essa porta, todo projeto sem PRD voltaria a ter tarefa que não rastreia pra nada. [confirmado, docstring de `_requisitos_do_plano`]
- **Nenhum dos 13 planos no disco usa qualquer um desses campos hoje.** As chaves de topo presentes nos 13 arquivos são só `id`, `title`, `phases`, `created`, `status` e `closed_at` (11 destes); `requisito`, `pronto`, `grupo`, `pendencia`, `decidido` e o bloco `requisitos` aparecem **zero** vezes. O schema é novo, os arquivos são anteriores a ele — e é exatamente esse o desenho: a exigência só morde tarefa que **nasce agora**. [confirmado — derivado com `json.load` sobre os 13 arquivos nesta rodada]
- **O que protege o registro histórico:** `merge()` recarrega do arquivo o que o `init` novo omitiu, pelo mesmo motivo que não apaga a prova. **A regra passou a ser uma só e a valer para o plano inteiro** [confirmado, `plan_state.py:merge`]:
  - **No nó**, os cinco campos da tarefa **mais o `detail`** — que mora na FASE e é o único lugar do 🔧 Como / 💡 Por quê / 📁 Toca em. Ele estava fora da lista antiga e era apagado no `init` seguinte; **os 13 planos no disco carregam 60 blocos `detail`** hoje. [confirmado — derivado com `json.load` sobre os 13 arquivos nesta rodada]
  - **No topo do plano**, TODA chave que o `init` não trouxe, e não mais só `created` e `status`. O que morria na lista fixa era justamente o bloco `requisitos` — a fonte que as tarefas citam — e o `closed_at`. Perder `requisitos` no segundo `init` desligava, em silêncio, o portão que recusa citação para o nada: sem fonte, `reqs` fica vazio e a checagem não roda.
  - **Apagar de propósito continua possível e agora é uniforme: declare a chave VAZIA** (`"requisitos": []`), porque o merge só preenche o ausente. É a mesma regra que já valia para a `pendencia`.
- **`cmd_reabrir` é o caminho de volta:** desfaz uma `decidido`, devolve o texto dela para `pendencia` e a tarefa para `todo`, zerando `evidence` e `done_at`. Existe porque *"toda decisão tomada na ausência do dono seja reversível por construção"* — sem ele, `decidido` seria fato consumado. [confirmado]
- **Quem calcula em cima disso NÃO guarda nada:** `plugins/visual/lib/cobertura.py` é arquivo novo e **não é depósito** — lê os requisitos de um markdown (`le_requisitos`), cruza com o plano (`mapa`) e devolve a linha única (`resumo`). Zero escrita em disco. A vista "épico › requisito › grupo › tarefa" é **derivada, não armazenada**, pelo mesmo princípio que faz a fase não ter estado próprio. [confirmado — o arquivo tem 79 linhas e nenhuma abre arquivo para escrita]
- **Por que o arquivo existe:** antes disto o plano só vivia no transcript e todo consumidor o **re-derivava por LLM** — lossy: encurta, renomeia fase, chuta se já foi executado. O caso concreto está citado na docstring (`extract_ata.py`: `excerpt: txt[:1200]` e `likely_executed = commits_after > 0 or edits_after >= 3` — um plano de 10 fases + 1 commit virava "concluído").
- **A correção é estrutural:** o modelo **autora uma vez** (`init`) e daí em diante só **marca** (`tick`). Quem desenha a árvore é o programa lendo o arquivo. Como o modelo nunca redigita um título, não há de onde a mudança de nome vir.
- **As travas do schema, lidas de `validate()`:** `id` slug minúsculo; fase casa `F<n>`, passo casa `F<n>.<m>` com prefixo batendo com a fase; `desc` obrigatório e ≤ `DESC_MAX = 140` chars (*"é UMA linha, não um parágrafo"*); `status` ∈ `("todo","doing","blocked","done")`. Erros saem **todos de uma vez**, pra o autor não gastar N rodadas.
- **A trava nova: citação órfã não grava.** Quando há requisitos conhecidos, `validate()` recusa o `init` inteiro se alguma tarefa citar um id que não existe na lista. Não é aviso — é erro. O comentário traz a medida que originou a regra: *"7 de 154 itens de um plano real citaram artigo de lei sem ninguém nunca conferir se o artigo existia"*. `reqs` vazio desliga a checagem, porque projeto sem documento de requisitos é o caso comum, não defeito. [confirmado, `plan_state.py:validate`]
- **Quatro recusas que protegem o depósito:**
  - `tick` exige `--evidencia` com ≥ `EVIDENCE_MIN = 8` chars: *"Sem isso, 'concluído' é palpite — foi assim que planos foram dados como prontos sem estar."* `done` só existe via `tick`; `cmd_state` recusa explicitamente `done`.
  - **`init` fecha a mesma porta pelo outro lado:** `status: "done"` escrito à mão com `evidence` abaixo de `EVIDENCE_MIN` recusa o arquivo. O teto da prova é o mesmo dos dois lados, senão há dois — quem escreve o JSON do `init` é o modelo, e por ali "concluído" entrava sem prova nenhuma. [confirmado, `plan_state.py:erros_do_plano`]
  - `tick` **também recusa tarefa com decisão em aberto** — e o que fecha a decisão é o REGISTRO: `decidido` com uma `escolha` preenchida. **Apagar a `pendencia` não é mais o caminho**, porque o `merge` preserva o campo que o `init` omite e a pergunta voltava, travando a tarefa pra sempre. A `pendencia` continua gravada de propósito: é dela que o `reabrir` vive. [confirmado, `plan_state.py:cmd_tick`]
  - `merge()` **trava a identidade**: título divergente do que está no arquivo aborta o `init` inteiro, e renomear exige `--rename <id> "<novo título>"`. Nó que sumiu do `init` novo é **mantido**, não apagado.
  - Escrita é atômica: `save()` grava em `.tmp` e faz `os.replace`.
- **Leitura tem porta única, e ela nomeia o estrago:** `plan_state.py:le_plano`. Arquivo que não abre ou não é JSON vira `PlanError` com o CAMINHO e a CAUSA (*"o arquivo existe e não é JSON válido. Conserte-o à mão — é o registro do que já foi feito, e nada aqui o reescreve"*), em vez de traceback. Quem LISTA (`list_plans`) segue engolindo o arquivo torto de propósito: um byte errado num plano não pode apagar os outros 12 da listagem. [confirmado, e a suíte fecha com a asserção `list_plans pula o corrompido`]
- **Quem lê no fim do turno:** `plugins/visual/hooks/stop-plan-status.sh`, via `plan_state.py brief`. Canal `systemMessage` (informa, nunca bloqueia), desligável por `PLAN_STATUS=0` / `PLAN_NUDGE=0`. Costura confirmada nos dois lados. [confirmado] O resumo que ele mostra **parou de afirmar prova sem olhar a prova**: o trecho *"cada um com prova anexada"* era escrito por construção e hoje só entra depois de `plan_state.py:_com_prova` conferir a `evidence` de cada passo feito. [confirmado]
- **Quem lê na hora de guardar a sessão:** a skill `handoff`. Ela passou a **ler os campos do arquivo em vez de pedir que sejam reinventados** — a árvore de `render --format text` é a vista de execução e não mostra `pronto`, `pendencia` nem `requisito`, que são justamente os três que a sessão seguinte ia redigir de cabeça. A `SKILL.md` traz o comando que os imprime e manda copiá-los **verbatim**: o `pronto` vira o "Critério de pronto" e a `pendencia` vira "Decisão em aberto", com o passo marcado como **bloqueado** — listar como executável um passo cuja `pendencia` trava o tique manda a próxima sessão bater na mesma parede sem saber qual é a pergunta. [confirmado — `plugins/handoff/skills/handoff/SKILL.md`, e a suíte `plugins/handoff/lib/test_handoff_skill.py` executa o comando prescrito e cobra a prosa]
- **Natureza: registro de trabalho, insubstituível, sem cobertura.** Verde em `plugins/visual/lib/test_plan_state.py` nesta rodada.

### A5 · `.claude/hook-contract.baseline.json` — o retrato do contrato dos hooks

🔴 **Mudou de região nesta rodada: era rastreado, hoje é ignorado** (`.gitignore:45`, seção "RETRATO DESTA MÁQUINA"). [confirmado por `git check-ignore -v`]

- **Tipo:** JSON único, sobrescrito por `python3 scripts/hook_contract.py --json > …`. **38.035 bytes.**
- **Cinco chaves de topo, lidas do arquivo real:** `root` (abspath da máquina que mediu), `entries` **31**, `scripts` **30**, `findings` **3**, `measured` **31**. ⚠️ **`entries` (31) > `scripts` (30) porque um mesmo script é registrado em mais de um evento** — contar entradas como "quantos hooks eu tenho" infla, do mesmo jeito que contar chaves do `manifest.json` como "quantos arquivos" (A3).
- ⚠️ **O `root` gravado é o caminho absoluto desta máquina.** Era metadado de proveniência inútil quando o arquivo viajava; agora que ele não viaja mais, é coerente — e é justamente por carregar isso que ele saiu do índice.
- **O que o script mede** (`scripts/hook_contract.py`, cabeçalho): as 5 propriedades que separam um gate saudável de um que trava ou se desliga sozinho — canal de saída, cap anti-loop escopado por sessão, kill-switch, binário fixo, fail-open. O aviso do próprio arquivo: *"Isto é grep sofisticado, não verdade."* Por isso a saída traz sempre a linha e o trecho que dispararam o achado.
- **Natureza: RECONSTRUÍVEL, mas com JULGAMENTO embutido.** Regerar é um comando; o que **não** se regenera é quais achados foram aceitos — essa parte vive em prosa (`patterns.md`, "As isenções"). O JSON é o estado, o `patterns.md` é o porquê.
- **Quem lê:** o check E do `.claude/hooks/release-gate.sh` (linhas 99-107), via `--baseline`, barrando só o que **piorou**. Costura confirmada nos dois lados. [confirmado]
- ⚠️ **mtime de 28/jul.** O retrato não foi refeito depois da recriação do repo: o gate compara o presente contra uma medida de três dias atrás, e o baseline agora nem viaja mais para outra máquina reproduzir a comparação.
- **Nenhum hook o reescreve sozinho, de propósito** — baseline que se auto-atualiza aceita silenciosamente qualquer regressão.

### A5a · `.claude/stop-budget.baseline.json` — o retrato do CUSTO do fim de turno

- **Nasceu em 2026-08-02**, irmão do A5 e com a mesma mecânica de retrato — o que muda é o que ele mede. O A5 mede a **forma** de cada hook (canal, cap, kill-switch); este mede **quanto o conjunto cospe** no `Stop`.
- **Tipo:** JSON único, sobrescrito por `python3 scripts/hook_contract.py --stop-budget --json > …`. **908 bytes.**
- **Três chaves, lidas do arquivo real:** `total_linhas` **6**, `teto` **6**, `emissores` **7** (cada um com `plugin`, `script`, `linhas`, `timeout`).
- 🔴 **Diferente do A5, este é RASTREADO** — não carrega caminho absoluto de máquina, então viaja sem sujar o repositório público.
- **Quem lê:** o check **E2** do `.claude/hooks/release-gate.sh`, dentro do mesmo `if` do check E (só quando o commit toca `plugins/*/hooks/`). Sai 1 quando o total **sobe**, nomeando quem subiu e quem é emissor novo. Costura confirmada nos dois lados. [confirmado]
- ⚠️ **Barra a deriva, nunca o número.** O total está em **6 de um teto de 6** — um gate por número absoluto barraria o próximo commit que tocasse hook sem nada ter piorado. Retrato ilegível **não** barra (fail-open explícito, com 2 checks em `test_hook_contract.py`).
- **Natureza: RECONSTRUÍVEL, com julgamento embutido** — igual ao A5. Regerar é um comando; o que não se regenera é a decisão de aceitar uma piora, que é o próprio ato de recongelar.
- **Nenhum hook o reescreve sozinho**, pelo mesmo motivo do A5: baseline que se auto-atualiza aceita qualquer regressão em silêncio.

### A5b · tags `archive/<branch>-<data>` — a rede do `/branches`, e ela está rompida

- **Tipo:** tag do git, uma por branch apagada, criada por `plugins/branches/lib/branch_state.py:cmd_prune`. Formato `archive/<nome-da-branch>-<YYYYMMDD>` (`"archive/%s-%s" % (b["name"], dia)`) — como o nome da branch entra cru, branch com barra vira tag com barra.
- **Invariante forte, lido do corpo:** o `prune` cria a tag **antes** de apagar e **aborta** se não conseguir criá-la (*"não consegui criar a tag de resgate de '%s' — nada foi apagado"*). Duas travas a mais no mesmo verbo: só nomes explícitos (nunca "todas as seguras") e recusa de branch com trabalho exclusivo sem `--force`.
- 🔴 **A rede voltou a ser SÓ local, e desta vez o motivo não é `git push` esquecido — é história nova.** [confirmado]

  ```bash
  git tag -l 'archive/*' | wc -l          # 6
  git ls-remote --tags origin             # (saída vazia)
  git merge-base HEAD archive/docs/readme-20260728   # (saída vazia — sem ancestral comum)
  ```

  As seis tags **resolvem** localmente (os objetos ainda estão no `.git` deste clone) e apontam para commits da história antiga, que não é ancestral do `2587006`. O remote não tem nenhuma. Restaurar uma branch por `git branch <nome> archive/…` ainda funciona **aqui**; em qualquer outro clone, não existe.
- **Sem poda.** Uma tag por branch apagada, acumulando. Aceito: são bytes, e o valor é durar.
- Verde em `plugins/branches/lib/test_branch_state.py` nesta rodada.

### A6 · `.claude/ata/` — 1,9M, 32 arquivos · logs de sessão

- Gitignorado por `.gitignore:17`. Escrito pelo `/handoff` (`plugins/handoff/lib/extract_ata.py`), lido pelo `/project-doc` e pelo próprio `/handoff` na retomada.
- Conteúdo: `INDEX.md` + `LOG-<uuid>.md` por sessão + um `HANDOFF-legado-*.md`.
- **Natureza: registro de trabalho, insubstituível, sem cobertura.** É a mesma classe do journal — e a mesma razão de estar fora do git: é onde nome de cliente e caminho de máquina se acumulam sem ninguém revisar.

### `.claude/intent/` — 716K · o caderno de pedidos DESTE projeto

- Gitignorado por `.gitignore:22`, **e por um segundo mecanismo**: `ledger.py:ensure_exclude` escreve `.claude/intent/` no `.git/info/exclude` **local**, via `git rev-parse --git-path info/exclude` — nunca toca arquivo versionado do repo (e usa `--git-path` porque num worktree o `.git` é arquivo, não diretório). [confirmado]
- **`ledger.jsonl`** — 429.127 bytes, **622 linhas**. Composição derivada: [confirmado]

  ```
  raw 256 · classify 205 · verdict 92 · baixa 69
  ```
- **Quatro eventos, e o estado vivo é o `fold` deles** (docstring lida): `raw` (o pedido verbatim), `classify` (vira `pedido|correcao|restricao|conversa`; só os três primeiros viram entrada `p-N`), `verdict` (`feito|parcial|nao_feito` × `confirmado|inferido` + evidência) e `baixa` (`by: auditor|usuario|substituido|receita`).
- ⚠️ **`fold(evs, session)` filtra `pending`/`live` por sessão, e isso é conserto de bug medido:** sem o filtro, sessões paralelas no mesmo projeto compartilhavam a lista de vivos e *"uma única auditoria cobrou 3 frentes de 3 sessões"*. `entries` continua completo — o filtro é só para quem **cobra**.
- **Escrita concorrente é protegida:** `locked(d)` faz `fcntl.flock(LOCK_EX)` sobre `ledger.lock` pra `load+append` ser atômico — sem isso, hooks concorrentes geravam `r-N`/`p-N` duplicados. O `ledger.lock` (0 bytes) está no disco.
- **Arquivos satélites no mesmo diretório**, todos parte do protocolo de auditoria: `audit-*.json` (o veredito de uma rodada), `<audit>.applied` (marcador de idempotência — `apply_audit` sai cedo se existir), `<audit>.escopo` (a lista de ids que o gate **perguntou**, gravada no instante do bloqueio). O `.escopo` conserta uma catraca medida: sem ele, cada mensagem enviada entre auditar e consumir entrava na conta e o veredito nascia impossível de aprovar — *"33 pedidos vivos cobrados de uma auditoria que perguntou por 1"*.
- **O `tree_hash` protege o veredito de envelhecer**, e exclui `EXEC_ARTIFACTS` (`__pycache__`, `*.pyc`, `node_modules`, `*.log`, `dist`, `build`, `coverage`, …) porque a própria auditoria roda código e sujaria a árvore — *"o gate nunca fecha, bate o cap e libera SEM auditoria, o oposto do propósito"*.
- **Degradação declarada:** erro de I/O silencia os comandos de escrita e devolve fallback seguro nos de leitura — `verify` falhando devolve `remaining: -1`, jogando tudo pro auditor caro, porque *"degradar pro caro é seguro; pro barato não"*.
- **Natureza: histórico de intenção, insubstituível, sem backup.**

### Os outros de (C)

- **`.claude/visual/` — 4,1M, 84 entradas** (`.gitignore:47`). As páginas HTML que o `/visual` gera. Descartável: são a apresentação, não a fonte.
- **`.claude/qa-loop/telemetry.jsonl` — 3 linhas** (`.gitignore:46`). Uma linha por rodada de `/qa-loop`: `{ts, target, domain, severity_floor, max_rounds_config, rounds_run, corrections_per_round, …}`. É o insumo pra avaliar o número ideal de loops com o tempo — **insubstituível e minúsculo**, a pior combinação para ficar sem cópia.
- **`.claude/HANDOFF.md`, `HANDOFF-guardrails.md`, `HANDOFF-project-doc.md`, `BRIEFING-review-loop-skill.md`** (`.gitignore:19-20`). São **fonte de mineração** — `journal.py:collect_handoffs` lê os bullets das seções de conhecimento (`HANDOFF_SECTIONS`: "Findings & Gotchas", "Gotchas", "Discussões e Decisões", "Detalhes Técnicos", "Contexto Extra") e os transforma em findings `handoff` — que são **154** no journal de hoje.

---

## (D) O cofre — o único depósito com cobertura de terceiro

- **Onde:** `~/Library/Mobile Documents/com~apple~CloudDocs/Cofre/<projeto>-<8hex>.env`, resolvido por `journal.py:cofre_paths` nesta cascata: [confirmado]

  ```python
  env = os.environ.get("PROJECT_DOC_COFRE_DIR")     # override (testes / máquina sem iCloud)
  icloud = "~/Library/Mobile Documents/com~apple~CloudDocs"
  base = env or (icloud + "/Cofre" se existir) or "<repo>/.claude/secrets/_local_cofre"
  slug = "<basename>-<sha1(abspath)[:8]>"           # PATH completo, não só o nome
  ```

  O slug usa o caminho completo de propósito: **dois projetos de mesmo nome não colidem**.
- **O arquivo deste projeto tem 39 linhas.** Formato: uma linha `LABEL:8hex=valor` por segredo, com `\n` escapado (PEM é multilinha e quebraria o `.env`). O `8hex` é `sha1(valor)[:8]`, então o mapeamento placeholder→valor é sempre exato: mesma chave com dois valores não colide, mesmo valor dedupa. Os rótulos vistos são os das palavras-sinal que o scrubber usa (`token`, `tokens`, `secret`, `secrets`, `chaves`, `credenciais`, …). **Nenhum valor foi lido nem transcrito.**
- **A ordem de escrita importa:** `stash_secrets` chama `ensure_gitignore(project_root, ".claude/secrets/")` **antes** de escrever — porque no fallback local o cofre cai dentro do repo, e proteger depois seria tarde.
- **Ponte no repo:** `.claude/secrets/ops.env` é um **symlink** para o arquivo do iCloud, recriado se ficar stale. `.claude/secrets/` está no `.gitignore:31` (seção SEGREDO). [confirmado por `ls -la`]
- **Natureza: insubstituível e sincronizado.** É o único depósito fora de (A) que tem cópia em outro lugar — e a cópia é do iCloud, não deste projeto.

---

## Estado efêmero em `/tmp` — chaveado por sessão, some no boot

Regra do repo: estado por-sessão em `/tmp` **tem que** ser chaveado por `session_id`. As três famílias vivas:

- **context-guard** — `/tmp/claude-context-pct-<session_id>` (escrito pelo wrapper de statusLine `context-guard-writer.sh`) e `/tmp/claude-context-warned-<session_id>` (sentinel do disparo). O `context-guard-reset.sh` apaga **só os da própria sessão** e depois poda órfãos: `find /tmp -maxdepth 1 -name 'claude-context-pct-*' -mtime +1 -delete` (idem `-warned-`). O comentário registra o bug que motivou o per-sessão: um arquivo global era sobrescrito pela última statusLine a renderizar, e **uma** sessão a 80% fazia o guard bloquear **todas**. [confirmado]

  🔴 **Este depósito só existe se o writer estiver na cadeia da statusLine, e em 2026-08-02 ele não estava.** Medido: o único `/tmp/claude-context-pct-*` no disco era `claude-context-pct-smoke-123`, **fixture de teste** com mtime de 30/jul, enquanto o plugin aparecia habilitado. Nenhuma sessão real gravou por 3 dias, e a barra de status continuou perfeita — quem sumiu foi o elo que produz dado para **outro** consumir. Quem cobra agora é `conformance.py:check_statusline_meio_ligada` (ver `architecture.md §10.1` e `patterns.md §1.14`). ⚠️ **Fixture de teste no mesmo diretório do estado real é armadilha**: `ls` do glob parecia saudável, e só o nome e o mtime denunciavam.
  ⚠️ **A poda não está dando conta:** `ls /tmp | grep claude-context-warned` devolve mais de 20 sentinelas de sessões mortas. A poda só roda no `SessionStart` **de uma sessão que tenha `jq`** — sem ele o script sai na primeira linha, e a limpeza nunca acontece. [confirmado]
- **plano do `/visual`** — três sentinelas em `${TMPDIR:-/tmp}`, todas com a mesma chave `$(id -u)-${SESSION}-${PHASH}`, onde `PHASH` é o `cksum` do **diretório de planos resolvido** (não do cwd — canonicalizar path na chave é uma armadilha conhecida do repo): `claude-plan-mark-*` (marco do início da sessão, que data o "encerrado agora"), `claude-plan-nudge-*` (a cobrança já saiu nesta sessão) e `claude-plan-closed-*` (quais encerramentos já foram confirmados). Sem a terceira, o 🏁 repetia a cada turno até a sessão acabar. [confirmado em `stop-plan-status.sh` e `plan_state.py:_seen_ids`]
- **handoff / ata** — `/tmp/claude-ata-session-<h>`, `/tmp/claude-handoff-target-<sid>`, `/tmp/claude-ata-gate-ok-<h>`.

Efêmeras por definição. Nenhuma delas é entrada de nada — reconstroem-se sozinhas na sessão seguinte.

---

## Os símbolos que mais gente depende (e o que eles guardam)

- **`scrub()`** (`journal.py`) — a barreira entre conversa-verbatim e disco. Devolve `(texto_scrubbed, [(cofre_key, valor)])`. É o que decide se um segredo vira placeholder ou vaza. Roda na **escrita**, não no commit.
- **`fold()`** — existe em **duas encarnações independentes e com regras diferentes**: `journal.py:fold` (discovered/invalidated/curated; invalidação é definitiva) e `ledger.py:fold` (raw/classify/verdict/baixa; filtra vivos por sessão). Ambas seguem o mesmo princípio: **o estado vem do arquivo, nunca do julgamento do modelo.**
- **`live_findings()`** (`journal.py`) — projeta o fold: descarta o que não está `live`, troca `text` por `curated` quando há, ordena por `source.ts`. É o que a doc realmente lê.
- **`read_events()` / `append()` / `append_events()`** — as portas de I/O dos dois journals. Ambas só abrem em modo `"a"`; nenhuma tem caminho de truncamento. `ledger.py:append` ainda faz `ev.setdefault("ts", ...)` pra nenhum evento nascer sem relógio.
- **`load()`** (`ledger.py`) — leitura tolerante: linha ilegível é pulada (`continue`), arquivo ausente devolve `[]`. Um JSONL corrompido no meio degrada, não derruba.
- **`intent_dir()` / `resolve_dir()`** — os dois resolvedores de "onde este projeto guarda seu estado". `intent_dir` implementa a cascata em Python; `resolve_dir` (`plan_state.py`) **delega ao `skills/visual/resolve-dir.sh`** de propósito, *"pra não haver duas implementações da cascata que possam divergir"*.
- **`pick_plan()` / `plan_progress()`** — `pick_plan` recusa adivinhar: sem id, exige que haja **exatamente um** plano ativo, porque *"adivinhar aqui é como o plano se perde"*. `plan_progress` conta passos `done` sobre o total — o número que aparece em todo lugar.
- **`PlanError`** — a exceção única do `plan_state.py`. Toda recusa (título divergente, tick sem prova, plano ambíguo) sai por ela, com a mensagem já formatada pro usuário.
- **`git()`** — também em duas encarnações, e as duas escolheram a mesma direção: `journal.py:git` devolve `""` em qualquer erro (delta degrada, não quebra); `branch_state.py:git` levanta `BranchError` por padrão e devolve `None` com `ok_fail=True` (verbo que **apaga** não pode falhar em silêncio).
- **`classify()`** (`branch_state.py`) — a leitura pura do estado das branches (*"NÃO escreve nada"*). É o insumo do `prune`; usa o relógio real (`int(time.time())`) e não o último commit da base, porque com a base parada uma branch mais nova dava idade 0 e sumia do radar.
- **`_e()` / `_rich()`** (`visual_page.py`, e `_e` também em `plan_state.py` e `branch_state.py`) — `_e` é `html.escape(..., quote=True)`; `_rich` escapa **e depois** reabre um subconjunto mínimo de markdown (só `` `code` `` e `**negrito**`). Existe pra o spec JSON não precisar carregar HTML: *"se o modelo escrevesse HTML dentro do JSON, a gente teria trocado de sintaxe sem trocar de problema."*

---

## Fora do inventário — verificado e não guarda dado

- **Nenhum banco, ORM, migration ou `docker-compose`.** O único lockfile do repo é `plugins/archify/skills/archify/package-lock.json`.
- **`.claude-plugin/marketplace.json`** e os `plugin.json` — catálogo e metadado, escritos só por humano. Não são estado.
- **`_shared/`** — código vendorado para 6 cópias. Fonte, não depósito.
- **`pi-plugins/`** (`.gitignore:71`) — cópia local defasada de `plugins/`, explicitamente **não é fonte**. Continua fora do grafo; as 106 chaves dela que sobrevivem no `manifest.json` do graphify são entradas mortas do índice.

---

## Resumo por natureza

**Insubstituível e SEM cobertura nenhuma** (perder o disco = perder o conteúdo):

```
.claude/.project-doc/findings.jsonl   3,3M · 1133 eventos   (journal do conhecimento)
.claude/intent/ledger.jsonl           429K ·  622 eventos   (caderno de pedidos)
.claude/ata/                          1,9M ·   32 arquivos  (logs de sessão)
.claude/plans/*.plan.json             132K ·   13 planos    (o que foi feito, com prova)
.claude/qa-loop/telemetry.jsonl        3 linhas             (calibração do /qa-loop)
~/.claude/plans/                      2,3M                  (do harness; encolhe sozinho)
~/.claude/intent/                     264K                  (fallback de outros projetos)
~/.claude/state/forma-relato/         104K ·  20 vereditos  (o texto do que a régua reprovou)
```

**Reconstruível, com custo:**

```
.claude/.project-doc/ledger.json      re-minerar vira cold-start (CAP=1000 commits)
.claude/hook-contract.baseline.json   1 comando — mas o JULGAMENTO das isenções não volta
graphify-out/                         graphify update . --force (AST, sem LLM)
plugins/bootstrap/config/manifest.json  regenerado no SessionStart, MENOS as chaves manuais
```

**Descartável por desenho:**

```
~/.claude/green-suite/          cache puro, TTL 24h por linha, poda de 7 dias
~/.claude/visual-state/         estado de UI (exceto config.json, que é preferência)
~/.claude/guardrails/           logs e contadores dos dois vigias
~/.claude/state/prose-ceiling/  contadores + batidas + bypass do teto
~/.claude/state/intent-guard/   a marca `olhado`; apagar zera o "desde a última vez"
/tmp/claude-*                   sentinelas por sessão
.claude/visual/                 páginas HTML geradas
```

**Com cobertura de terceiro:** só o cofre, no iCloud.

---

## Pendências

1. **O baseline dos hooks (A5) é de 28/jul e agora é local.** O check E do release-gate compara o presente contra um retrato que não foi refeito depois da recriação do repo e que não viaja mais. Refazer ou aceitar explicitamente.
2. **As 6 tags `archive/*` apontam para história órfã e não existem no remote.** Decidir se são empurradas (dando ao remote novo a rede antiga) ou descartadas junto com a história velha. Hoje elas resgatam branch só neste clone.
3. **Dois comentários de código afirmam versionamento que o `.gitignore` desmente** — `journal.py` ("versionado — é o veículo do conhecimento") e `plan_state.py` ("VERSIONADO no git de propósito"). Quem ler o código antes do `.gitignore` conclui que há backup onde não há.
4. **`askq-humanize.sh` e `scope-cop.sh` resolvem a MESMA pasta por expressões diferentes.** Invisível aqui (`CLAUDE_CONFIG_DIR` unset), divergente em qualquer máquina que a sete.
5. ✅ **Resolvida: o juiz de forma (B9) passou a julgar** — 50 `julgou`, 30 `passa`, 20 reprovas, contra 12 batidas `sem texto` e zero julgamentos na rodada anterior. O furo do `check_juiz_rodou` (aprovar um log que nunca julgou) continua existindo no código; deixou de ser o estado deste disco.
6. **Nada poda os contadores de B8 e B9**, e agora são **35** deles (15 + 20, contra 9 + 0). Os órfãos sem sufixo de B1 (`scope-cop.blockstreak`, `scope-cop.bypass`, de 2/jul) seguem fora do alcance da poda por causa do padrão com ponto.
7. **Dois planos ativos ao mesmo tempo em A4** (`2026-07-31-fechar-a-regua-e-publicar` 10/11 e `2026-08-01-formato-de-plano-hierarquico` 0/20). `pick_plan` recusa adivinhar, então todo comando sem `--plan` explícito falha até um ser encerrado.
8. **O `bypass.log` do B8 nunca existiu, e agora isso tem consequência em dois lugares.** Para o `check_bypass_teto`, ausência = conforme; para o `furos_da_regua`, ausência = `fontes` 1 em vez de 2 — a contagem de furos que o dono vê é hoje meia fonte, e o programa diz isso, mas só quem lê a linha inteira percebe.
9. **Os cinco campos novos de A4 não existem em nenhum dos 13 planos no disco.** O schema exige `requisito` e `pronto` só de tarefa nova; até o próximo `init`, a cobertura entre requisito e tarefa é 0 de 0 e nada no repositório exercita o caminho em dado real.
