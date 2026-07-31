---
generated: 2026-07-31
generated-commit: a57ea6e
project: pedro-plugins
scope:
  - .claude/.project-doc/findings.jsonl
  - .claude/.project-doc/ledger.json
  - graphify-out/graph.json
  - .gitignore
  - plugins/project-doc/lib/journal.py
  - plugins/project-doc/lib/graph_map.py
  - plugins/intent-guard/lib/ledger.py
  - _shared/green-cache.sh
  - plugins/visual/server/visual_server.mjs
  - plugins/visual/lib/plan_state.py
  - .claude/hook-contract.baseline.json
  - scripts/hook_contract.py
  - plugins/branches/lib/branch_state.py
  - plugins/guardrails/hooks/scope-cop.sh
  - plugins/context-guard/hooks/context-guard.sh
  - plugins/context-guard/hooks/context-guard-reset.sh
  - graphify-out/.graphify_labels.json
  - graphify-out/GRAPH_REPORT.md
  - graphify-out/manifest.json
  - plugins/guardrails/hooks/askq-humanize.sh
  - plugins/bootstrap/hooks/stop-prose-ceiling.py
verified-by:
  - plugins/visual/lib/test_plan_state.py
  - plugins/project-doc/lib/test_journal.py
  - plugins/project-doc/lib/test_graph_map.py
  - plugins/intent-guard/lib/test_ledger.py
  - plugins/project-doc/lib/pattern_check.py
doc-sig: pedro-plugins/findings.jsonl@gen=3.8#1f2a8160
---

# Data Stores — onde o dado mora

Este repo **não tem banco, ORM, migrations nem `docker-compose`**. Os depósitos são arquivos. Eles se dividem em três regiões com garantias de durabilidade completamente diferentes:

- **(A) dentro do repo, versionado** — backup = git + GitHub. É o que viaja entre máquinas.
- **(B) fora do repo, em `~/.claude/`** — escrito por hooks/daemons dos plugins. **Zero backup.** Perder a máquina = perder tudo isso.
- **(C) dentro do repo, mas gitignored** — moram na árvore de trabalho e parecem protegidos, mas estão fora do índice do git. **Zero backup.**

⚠️ **A região (C) mudou de tamanho em 2026-07-31 e a mudança foi grande.** Cinco conjuntos que viviam em (A) saíram do índice (`git rm -r --cached`) e entraram no `.gitignore`: `graphify-out/`, `.claude/.project-doc/`, `.claude/ata/`, `.claude/plans/` e os três `.claude/HANDOFF*.md`. Nenhum arquivo foi apagado do disco — o que mudou foi só a garantia. **Cada um deles perdeu a única cobertura que tinha (git + o remote) e hoje existe apenas nesta máquina.** É perda de garantia decidida de propósito, não descuido; a contabilidade item a item está em `durability.md §3.15`.

Todas as medidas abaixo foram tiradas **em 2026-07-26, com `HEAD = 5ce0c1b`**, e cada uma vem com o comando que a produziu. [confirmado] As que um `/doc-touch` re-mediu — `graphify-out/` (A3), `.claude/plans/` (A4), o baseline dos hooks (A5), as tags de arquivo (A5b) e tudo em `~/.claude/` (B) — trazem **2026-07-30, `HEAD = 64acf18`** anotado no próprio item. Um segundo toque no mesmo dia, com **`HEAD = 781e923`**, re-mediu só o que mudou de natureza: `.claude/plans/` (A4), o vigia de escopo (B1) e o teto de prosa (B8).

**Em 2026-07-31, com `HEAD = ff32947`, foram re-medidos todos os depósitos que o destrack tocou** — A1, A2, A3, A4 e A6 — mais o índice do repo inteiro. O número que resume a mudança:

```bash
git ls-files -i -c --exclude-standard | wc -l   # 0   (era 35 antes do destrack)
git ls-files | wc -l                            # 251 (o HEAD ff32947 tinha 335)
```

A primeira linha é a que importa: **não há mais nenhum arquivo simultaneamente rastreado e ignorado.** Era exatamente essa a contradição que o inventário registrava como dívida em vários itens abaixo — "a regra existe no `.gitignore` mas o arquivo continua no índice". Ela acabou.

---

## (A) Dentro do repo — versionado

### A5 · `.claude/hook-contract.baseline.json` — o retrato do contrato dos hooks

- **Tipo:** JSON único, sobrescrito por `python3 scripts/hook_contract.py --json > …`.
- **Onde vive:** `.claude/hook-contract.baseline.json`, **tracked no git**.
- **Tamanho:** 38.035 bytes (40K). **5 chaves de topo, lidas do arquivo real:** `root` (o abspath da máquina que mediu), `entries` **31**, `scripts` **30**, `findings` **3**, `measured` **31**. ⚠️ **`entries` (31) > `scripts` (30) porque um mesmo script é registrado em mais de um evento** — contar entradas como "quantos hooks eu tenho" infla, exatamente como contar chaves do `manifest.json` como "quantos arquivos" (A3). [re-medido 2026-07-30, `HEAD = 64acf18`; eram 29 na rodada anterior]
- ⚠️ **O `root` gravado é o caminho absoluto da máquina que mediu** (`/Users/<usuário>/…/pedro-plugins`). O arquivo é versionado, então esse campo viaja e não vale em outra máquina — é metadado de proveniência, não configuração.
- **Natureza: RECONSTRUÍVEL, mas com JULGAMENTO embutido.** Regerar o arquivo é um comando; o que **não** se regenera é a decisão de quais achados foram aceitos. Essa parte vive em prosa, em `patterns.md §5.3` ("As isenções — e por que cada uma existe"). O par funciona: o JSON é o estado, o `patterns.md` é o porquê.
- **Quem escreve:** um humano/agente rodando o comando acima, conscientemente. Nenhum hook o reescreve sozinho — de propósito: um baseline que se auto-atualiza aceita silenciosamente qualquer regressão.
- **Quem lê:** o **check E** do `.claude/hooks/release-gate.sh`, via `--baseline`. Ele barra só o que piorou em relação a este arquivo.

⚠️ **A armadilha:** recongelar o retrato sem escrever o motivo transforma o gate em carimbo. O comando está documentado junto da ordem de registrar o porquê (`patterns.md §5.3`).

**Três sentinelas em `/tmp` acompanham este depósito**, todas chaveadas por
`(uid, session_id, cksum do dir)` — a regra do repo pra estado por-sessão:
`claude-plan-mark-*` (marco do início da sessão, quem data o "encerrado agora"),
`claude-plan-nudge-*` (a cobrança já saiu nesta sessão) e `claude-plan-closed-*`
(quais encerramentos já foram confirmados). Sem a terceira, o 🏁 do resumo de
fim de turno repetia a cada turno até a sessão acabar. Efêmeras por definição.

### A5b · tags `archive/<branch>-<data>` — a rede do `/branches`

- **Tipo:** tag anotada leve do git, uma por branch apagada (`plugins/branches/lib/branch_state.py:cmd_prune`).
- **Onde vive:** no próprio repositório onde a branch foi apagada. **Versionada** como qualquer tag — mas note que tag só viaja com `git push --tags`.
- **Natureza: rede de resgate.** Apagar branch `equivalent` exige `git branch -D` (o git a considera não-mergeada), e é exatamente aí que um erro custa trabalho. A tag torna a volta um comando: `git branch <nome> archive/<branch>-<data>`.
- **Formato do nome:** `archive/<nome-da-branch>-<YYYYMMDD>` (`"archive/%s-%s" % (b["name"], dia)`, com `dia = time.strftime("%Y%m%d")`). Como o nome da branch entra cru, tag de branch com barra vira tag com barra: `archive/feat/design-md-plugin-20260728`.
- **Já existem 6 no repo** (`git tag -l 'archive/*' | wc -l` → 6, em 2026-07-30): `docs/readme-20260728`, `feat/design-md-plugin-20260728`, `feat/project-doc-organism-20260728`, `feat/project-doc-pattern-signature-20260728`, `feat/sovai-build-engine-20260728`, `project-doc-organism-conformance-20260728`. **Todas do mesmo dia** — foi uma faxina única, não um hábito contínuo. [confirmado]
- ✅ **A rede deixou de ser local — MEDIDO contra o remote.** `git ls-remote --tags origin | grep -c 'archive/'` → **6** nesta sessão, contra **6** locais. As seis foram empurradas em 2026-07-30, depois que uma auditoria mediu 0. ⚠️ O que segue aberto é o automatismo: `git push` normal não leva tag e o `cmd_prune` não empurra, então a **próxima** branch apagada volta a nascer só neste clone. Cobertura em `durability.md §2.8`.
- **Invariante:** o `prune` cria a tag **antes** de apagar e **aborta** se não conseguir criá-la — nunca apaga sem rede. Duas travas a mais no mesmo verbo: só nomes explícitos (nunca "todas as seguras") e recusa de branch com trabalho exclusivo sem `--force`.
- **Sem poda.** Uma tag por branch apagada, acumulando. Aceito: são bytes, e o valor é justamente durar.

### A5c · `plugins/bootstrap/config/manifest.json` — o depósito ESCRITO POR MÁQUINA que também é editado à mão

- **Tipo:** JSON versionado, **211 linhas / 5.326 bytes**, **20 commits no histórico** (`git log --follow`), o último sendo `575c33e` (2026-07-30). [confirmado — `wc -lc` + `git log` nesta rodada]
- **Por que ele está aqui e o `marketplace.json` não** (ver *Fora do inventário*): o catálogo é escrito só por humano; este é **regenerado por um hook a cada `SessionStart`** (`plugins/bootstrap/hooks/lib/snapshot.sh`, a partir de `claude plugin list`) e **commitado automaticamente** por `git-sync.sh`. É estado de máquina que mora no repo — a única coisa neste projeto com esse formato.
- **5 chaves de topo hoje** (`jq keys`, rodado nesta rodada): `description`, `ferramentas_externas`, `marketplaces`, `skills`, `version`. **Só as 3 primeiras da lista `GENERATED_KEYS` (`version`, `description`, `marketplaces`) são geradas** — as outras duas (`skills`, `ferramentas_externas`) são **mantidas à mão** e o snapshot as preserva por construção.
- ⚠️ **É um depósito com DOIS escritores de naturezas opostas, e é daí que saem os defeitos.** O snapshot escreve sem perguntar; o humano escreve chave que o snapshot não conhece. As duas guardas que fazem os dois conviverem (`architecture.md §10.1`):
  - **A união com o manifest anterior é ADITIVA** — entrada de plugin ausente da amostra **fica**, porque `claude plugin list` devolve saída incompleta de vez em quando (medido: 49/15/49/49/49 linhas em 5 chamadas seguidas). Desinstalar de verdade virou edição explícita do arquivo. Se o total encolher mesmo assim, o script loga `warning: manifest encolheu`.
  - **`GENERATED_KEYS` é a lista do que o script GERA, não do que preservar** — tudo fora dela sobrevive. ✅ **Isso foi exercitado de verdade em `575c33e`:** `ferramentas_externas` entrou **sem uma linha de mudança no `snapshot.sh`**. Com a lógica anterior (`jq '{skills}'`, lista do que salvar) seria a segunda chave manual a sumir sozinha no primeiro `SessionStart` — foi o que aconteceu com `skills`, minutos depois de ela ser criada.
- **Conteúdo hoje** (lido do JSON nesta rodada): 7 marketplaces · 29 entradas de plugin (14 ligadas, 15 desligadas) · 19 skills em `skills.permitidas` · **1** item em `ferramentas_externas.itens` (o binário `graphify`, pacote `graphifyy`, exigido pelo `graphify-guard`).
- **Quem lê:** `hooks/lib/apply.sh` (converge a máquina) e `lib/conformance.py` (`check_plugins`, `check_skills`, `check_ferramentas_externas` — as três chaves não-geradas mais a de plugins). **Nenhuma das três últimas instala nada**: declaram o esperado pra o verificador poder acusar a diferença.
- **Perder este arquivo** não perde trabalho: a próxima sessão o regenera a partir da máquina viva. **Perder as chaves manuais, sim** — `skills.permitidas` e `ferramentas_externas` não têm origem nenhuma além do próprio arquivo.

---

## (B) Fora do repo, em `~/.claude/` — sem backup nenhum

Regra do repo, escrita literalmente no cabeçalho de `_shared/green-cache.sh`: *"Estado em `~/.claude/green-suite/` (NUNCA dentro do plugin — o cache `${CLAUDE_PLUGIN_ROOT}` é reescrito a cada bump de versão)."* É por isso que estes depósitos existem — e é por isso que **nenhum deles tem backup**: eles são por-máquina de propósito.

⚠️ **"`~/.claude/`" é o valor efetivo nesta máquina, não o caminho literal de todos eles.** Desde 2026-07-30 pelo menos um depósito desta região (B8) resolve a pasta por `CLAUDE_CONFIG_DIR`, caindo em `~/.claude/` só quando a env var está unset — que é o caso aqui. **A regra ao mexer em qualquer depósito de (B): escritor e leitor têm que resolver o diretório pela MESMA expressão.** Quando não resolvem, o sintoma não é erro, é o leitor reportando "está tudo bem" sobre uma pasta vazia que ninguém escreve (B8).

Medidas desta rodada [2026-07-30, `HEAD = 64acf18`]:

```bash
du -sh ~/.claude/plans ~/.claude/visual-state ~/.claude/guardrails ~/.claude/intent \
       ~/.claude/green-suite ~/.claude/context-guard ~/.claude/intent-guard ~/.claude/state
# 2,7M  plans        1,3M  visual-state   384K  guardrails
# 264K  intent       192K  green-suite      0B  context-guard      0B  intent-guard
#  36K  state        ← diretório NOVO nesta rodada (B8)
```

Re-medidos no toque seguinte do mesmo dia [`HEAD = 781e923`]: `guardrails` **388K** (+4K, o crescimento do `scope-cop.log` ao voltar a logar) e `state` **0B** — os 9 contadores do teto de prosa sumiram (B8).

Terceiro toque, mesma noite [`HEAD = a134e9c`]: `guardrails` **464K** (+76K em poucas horas — o `scope-cop.log` foi de 847 para **916** linhas e o modo `warn` virou o regime corrente, B1) e `.claude/intent/` **420K** (o depósito de (D), fora desta região). O `guardrails` é hoje o que mais rápido cresce em (B), e cresce **porque o gate voltou a logar** — o oposto do silêncio do modo `off`.

### B1 · `$CLAUDE_CONFIG_DIR/guardrails/` — 464K · estado operacional dos vigias de edição e de pergunta

- **Escrito por dois hooks:** `plugins/guardrails/hooks/scope-cop.sh` (os quatro arquivos `scope-cop.*` abaixo) e, desde 2026-07-30, `plugins/guardrails/hooks/askq-humanize.sh` (`askq.log` + `askq.count.<session_id>`).
- ⚠️ **Os dois escritores da MESMA pasta resolvem o caminho por expressões DIFERENTES, e isso é divergência viva.** [confirmado — `grep -n "HOOK_DIR=" plugins/guardrails/hooks/*.sh` nesta rodada]

  ```
  scope-cop.sh:39      HOOK_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/guardrails"
  askq-humanize.sh:45  HOOK_DIR="$HOME/.claude/guardrails"
  ```

  O `scope-cop.sh` migrou na v1.5.0 para a **mesma expressão** do `lib/conformance.py:CLAUDE_DIR` e do `hooks/lib/apply-config.sh`; o `askq-humanize.sh` ficou para trás. O comentário do `scope-cop.sh` diz o que a divergência custa: *"o hook lendo o modo numa pasta e o conformance varrendo `**/*.mode` noutra: o gate que o auditor acusa não seria o que o hook obedece, e cada lado ficaria coerente sozinho"* — e classifica como *"o mesmo defeito silencioso do `bypass.log` do `stop-prose-ceiling`"* (B8). **Nesta máquina `CLAUDE_CONFIG_DIR` está unset, então as duas expressões dão a mesma pasta e a divergência é invisível** — é exatamente a condição em que ela sobrevive. Numa máquina com a env var setada, `scope-cop.*` e `askq.*` se separam em dois diretórios.
- ✅ **O `~/.claude/hooks/scope-cop.mode` inerte foi aposentado** no `32cfe28` [confirmado — `ls` nesta rodada: *No such file or directory*]. Ele era um homônimo em pasta errada: o hook nunca o leu, editá-lo não mudava nada e não avisava. O `conformance.py:check_gates_enganosos` ganhou no mesmo commit a checagem que acusa `.mode` homônimo em pastas distintas — **o defeito é a existência do duplicado, não o valor dele**.
- **Quatro arquivos, quatro naturezas** (conferidos no disco e no script). ⚠️ Desde 2026-07-27 o streak e o bypass são **por sessão** (`scope-cop.blockstreak.<session_id>`), com poda de 1 dia: o arquivo único fazia os BLOCKs de uma sessão contarem pro freio da outra, liberando edição sem julgar o escopo:
  - `scope-cop.log` — 398.909 bytes, **916 linhas** [re-medido 2026-07-30 à noite; eram 370.884 / 847]. Trilha de auditoria **delimitada por `|`** (não TSV — `log_line` usa `printf '%s | %s | …'` e ainda troca qualquer `|` do pedido/diff por `/` justamente pra não quebrar as colunas): `ts · modo · veredito · streak · tem-plano · arquivo · req · diff`. **Descartável** (histórico de decisão, não entrada de nada).
  - `scope-cop.mode` — **não é mais um kill-switch de dois estados: desde 2026-07-30 o vocabulário tem TRÊS valores** — `deny` (default), `warn` e `off`. O hook lê `[ "$MODE" = "off" ] && exit 0` e depois `[ "$MODE" = "warn" ] || MODE="deny"`, ou seja **qualquer valor que não seja exatamente `off` ou `warn` cai em `deny`** — inclusive lixo ou erro de digitação, o que é a direção segura. **Configuração.** [confirmado no código, `plugins/guardrails/hooks/scope-cop.sh`, o bloco logo após `MODE_FILE`]
    ✅ **Na v1.5.0 o conjunto virou FECHADO e o valor inválido deixou de ser silencioso.** Um `case` explícito aceita `off | deny | warn | ""` (vazio/ausente = default de máquina nova) e manda qualquer outro valor para `MODE_IGNORADO`, que vira uma linha `MODE:invalido | valor ignorado="…"` no `scope-cop.log`. O motivo escrito no arquivo é a consequência de ter três estados: *"errar a grafia entrega o gate MAIS severo justamente a quem pediu o mais brando, que é o que o `warn` nasceu pra evitar"*. **Onde o rastro é escrito importa para este depósito:** ele sai *depois* dos filtros baratos, não na leitura do modo — o matcher é `Edit|Write`, e registrar cedo daria uma linha por edição de qualquer arquivo, afogando a auditoria num log que rotaciona em 5000 linhas.
    Um segundo interruptor nasceu junto e **não é arquivo**: `SCOPE_COP_GATE=0` (env var, avaliada antes de ler o stdin) desliga o hook sem tocar neste depósito. É a propriedade 3 do contrato de hook, no mesmo molde do `GRAPHIFY_GATE`. Consequência para quem lê o disco: **`scope-cop.mode` deixou de ser a única forma de o gate estar desligado** — o arquivo pode dizer `deny` e o gate estar mudo.
  - `scope-cop.blockstreak` — contador de BLOCKs seguidos; ao atingir `MAX_STREAK=3` o circuit-breaker libera 1 edição e zera. **Estado efêmero.**
  - `scope-cop.bypass` — registro da última liberação por circuit-breaker. **Descartável.**
- 🟡 **O valor no disco hoje é `warn`, e o log conta a história inteira desse arquivo de 5 bytes.** [confirmado nesta rodada] `cat ~/.claude/guardrails/scope-cop.mode` → `warn`. A distribuição `modo/veredito` das 916 linhas mostra por quê:
  ```bash
  awk -F' \\| ' '{print $2"/"$3}' ~/.claude/guardrails/scope-cop.log | sort | uniq -c | sort -rn
  #  455 deny/PASS   ·  191 deny/SKIP:no-ui-request  ·  158 deny/BLOCK
  #   21 deny/PASS:circuit-breaker · 9 deny/SKIP:parse-error · 9 deny/SKIP:judge-error
  #    1 deny/SKIP:no-request
  #   52 warn/PASS  ·  11 warn/SKIP:no-request  ·  5 warn/WARN  ·  4 warn/SKIP:no-ui-request
  ```
  ⚠️ **As linhas em `warn` saltaram de 3 para 72 em poucas horas** (as 4 categorias `warn/*` acima). O modo deixou de ser uma anotação e virou o regime corrente do depósito.
  As três **últimas** linhas em `deny` são três `BLOCK` seguidos, em `2026-07-02` 10:04:34, 10:05:13 e 10:06:38 — e depois disso **o log fica 28 dias em silêncio**, até `2026-07-30 17:14:34`, quando volta já em `warn`. O silêncio é a assinatura do `off`: nesse modo o hook sai antes de logar, então *ausência de linha* é o único registro que o `off` deixa. **Consequência para quem lê este depósito: um `scope-cop.log` parado não significa "nenhuma edição aconteceu", significa "o gate estava desligado".**
- ⚠️ **Em `warn` o `blockstreak` para de acumular.** O ramo novo faz `echo 0 > "$STREAK_FILE"` antes de logar (*"em aviso não há streak: nada foi bloqueado"*), então o circuit-breaker de `MAX_STREAK=3` fica inerte enquanto o modo for `warn` — não porque nada dispare, mas porque o contador é zerado a cada aviso. ✅ **O ramo de aviso deixou de ser teórico: `grep -c "| WARN"` → 5** [confirmado nesta rodada; era 0 na rodada anterior, quando havia 3 linhas em `warn` e nenhuma delas era `WARN`]. Ou seja, cinco edições que em `deny` teriam sido bloqueadas passaram com aviso — e o `blockstreak` foi zerado cinco vezes. **O depósito hoje registra exatamente o que o modo `off` apagava.**
  ⚠️ **E o aviso passou a sair por DOIS canais.** Na v1.5.0 o ramo `warn` emite `systemMessage` **junto** com o `additionalContext`, com o motivo escrito no hook: *"o transcript filtra `hook_additional_context` da renderização — sozinho ele deixaria o usuário no mesmo silêncio do modo `off`"*. As 5 linhas `WARN` no log são a prova de que o gate observou; o `systemMessage` é o que faz o usuário ver.
- ~~⚠️ **Existe um SEGUNDO `scope-cop.mode` no disco, em `~/.claude/hooks/`, e ele é inerte.**~~ **RESOLVIDO em `32cfe28`** — o arquivo foi apagado [confirmado nesta rodada: `ls ~/.claude/hooks/scope-cop.mode` → *No such file or directory*] e a **classe** virou checagem no `conformance.py:check_gates_enganosos`, que agora acusa `.mode` homônimo em pastas distintas. O relato original, mantido porque explica a checagem: `~/.claude/hooks/scope-cop.mode` também continha `warn` (5 bytes, mesmo horário), mas pertencia ao hook global hand-rolled antigo (`~/.claude/hooks/pretooluse-scope-cop.sh`, de 19/jun) que **não está registrado em nenhum lugar**: `grep -c "claude/hooks" ~/.claude/settings.json` → **0**, e a única chave em `.hooks` do `settings.json` é `UserPromptSubmit`. Pior: aquele script só conhece `off | deny`, então `warn` ali seria lido como `deny`. **Editar o arquivo errado não muda nada e não avisa** — o que o plugin lê é `~/.claude/guardrails/scope-cop.mode` (`plugins/guardrails/hooks/scope-cop.sh`, variável `HOOK_DIR`). [confirmado]
- **Mais dois arquivos, do vigia da pergunta** (`askq-humanize.sh`, 2026-07-30):
  - `askq.log` — **4.762 bytes, EXISTE desde 2026-07-30 10:28.** Uma entrada por invocação, limpa ou suja: `=== ts · session · rc` + o `tool_input` cru (`jq -c`, cortado em 4000 chars) + as violações. Rotação no molde do scope-cop (acima de 3000 linhas mantém as últimas 1000).
  - `askq.count.<session_id>` — cap de devoluções da sessão (teto 3, poda de 1 dia via `find -mtime +1`). **Estado efêmero**, escopado por sessão pela regra do §1.5 do `patterns.md`. **Nenhum no disco agora** — a poda de 1 dia já levou os das sessões de ontem.
- ✅ **O wiring do `PreToolUse` no `AskUserQuestion` deixou de ser inferência — está MEDIDO.** Até a rodada anterior este doc dizia que o `askq.log` não existia e que o disparo era hipótese tirada da doc do harness. O log agora prova o disparo **e** prova que o gate julga: **5 invocações registradas, 3 com `rc=1` (devolvidas) e 2 com `rc=0` (passaram)**. Não é um gate que só loga: ele reprovou a maioria das perguntas reais que viu. [confirmado]
  ```bash
  grep -c '^=== ' ~/.claude/guardrails/askq.log            # 5
  grep -o 'rc=[0-9]*' ~/.claude/guardrails/askq.log | sort | uniq -c
  #   2 rc=0      (limpo)
  #   3 rc=1      (violou → deny)
  ```
- ⚠️ **Os `scope-cop.blockstreak`/`.bypass` SEM sufixo de sessão ficaram órfãos.** Desde a mudança pra por-sessão, o hook só escreve `scope-cop.blockstreak.<session_id>`; os dois arquivos sem sufixo no disco são de **2 jul** e ninguém mais os lê nem os apaga (a poda `find -name 'scope-cop.blockstreak.*'` exige o ponto, então não casa com eles). **Lixo estável, não estado.** Hoje há **1** arquivo com sufixo de sessão (`scope-cop.blockstreak.b3e7c7b7…`, de hoje 17:16) — os de ontem já foram pela poda de 1 dia. Note a coincidência de data dos órfãos: eles congelaram em **2 jul**, o mesmo dia dos três `BLOCK` finais que motivaram desligar o gate. [confirmado] <!-- lint:ignore commit-hash — b3e7c7b7 e prefixo de session_id, nao de commit: existe o .jsonl correspondente em ~/.claude/projects/ no disco -->
- **Natureza global: descartável.** Perder tudo isso reseta os dois guards para o default (`MODE="deny"`, streak 0, cap 0) — nenhum conhecimento se perde. O `askq.log` é o único com valor além do histórico: é o insumo bruto pra afinar as réguas do `askq_lint.py` sobre pergunta real em vez de suposição de formato.
- **Costura verificada nos dois lados:** `scope-cop.sh` lê `VISUAL_STATE="$HOME/.claude/visual-state/latest.json"` para reconhecer plano aprovado via `/visual`; e `visual_server.mjs` de fato escreve esse `latest.json`. [confirmado]

### B2 · `~/.claude/visual-state/` — 1,3M · estado de UI do daemon do /visual

- **Escrito por:** `plugins/visual/server/visual_server.mjs`. `STATE_DIR = path.join(os.homedir(), '.claude', 'visual-state')` (criado com `fs.mkdir(..., {recursive:true})` na subida). O `POST /state` grava **dois** arquivos: `<session>.json` e `latest.json` (este último é o mesmo record + a chave `stateFile` apontando para o per-sessão).
- **Conteúdo:** `{session, timestamp, docTitle, state}` — a seleção que o usuário fez na página HTML (aprovar/ajustar/descartar), que a skill lê de volta quando ele digita "ok".
- **Hóspede novo desde 2026-07-28 — `config.json`, e ele NÃO é do daemon.** É a preferência do
  `/visual` (`auto_mode` + os quatro `auto_triggers`), que antes morava **dentro do plugin**, em
  `plugins/visual/skills/visual/config.json`. Mudou de casa porque `${CLAUDE_PLUGIN_ROOT}` é cache
  reescrito a cada bump, então a escolha do usuário sumia em silêncio na atualização
  (`architecture.md §11`). Quem escreve é a **skill**, não o `visual_server.mjs` — o daemon nunca
  toca nele. Semente versionada: `plugins/visual/skills/visual/config.default.json`. Ver
  `durability.md §3.9`.
- **Tamanho / volume:** 1,3M, **276 entradas** (`ls ~/.claude/visual-state | wc -l`, medido neste
  run — eram 255 na rodada anterior e 239 na anterior a essa: **+37 em duas rodadas de doc**),
  incluindo um `.daemon.log`.
- **Natureza: estado de UI, descartável** — com uma exceção de grau: o `config.json` acima é
  preferência, não sessão, e por isso não deve entrar num eventual prune por idade. O daemon
  aceita `session` só se casar `SESSION_RE = /^[a-zA-Z0-9_-]{4,64}$/`, corpo limitado a
  `MAX_BODY_SIZE = 256 * 1024`, liga só em `127.0.0.1` e se auto-mata após
  `IDLE_TIMEOUT_MS = 30 min`. Nada aqui é entrada de outro sistema além do handshake da sessão
  corrente. **Não há prune** — o acúmulo é desde abr/2026. [confirmado]

### B3 · `~/.claude/green-suite/` — 192K · cache de "suite verde"

- **Escrito por:** `_shared/green-cache.sh` (fonte-da-verdade) e suas cópias vendoradas `plugins/ship/hooks/green-cache.sh` e `plugins/qa-loop/lib/green-cache.sh`. Função `green_cache_mark`.
- **Chave:** `<cksum(root)>-<tree_hash>`, onde `tree_hash` é o `git write-tree` sobre um **index temporário** com `read-tree HEAD` + `add -A` — ou seja, inclui untracked. Qualquer edição/criação/remoção muda a chave e invalida o hit.
- **Formato:** TSV, uma linha por marca — `scope \t epoch \t iso-ts \t writer`.
- **Natureza: CACHE PURO, descartável por design.** As três garantias estão no cabeçalho do arquivo: fail-open na direção segura (qualquer erro → MISS → a suite roda), **gate vermelho nunca grava**, e TTL de 24h **por linha** (`GREEN_SUITE_TTL_SECS=86400`, epoch da linha e não mtime do arquivo). Ele mesmo se poda: `green_cache_mark` roda `find "$GREEN_SUITE_DIR" -type f -mtime +7 -delete`. Apagar a pasta inteira só faz as suites rodarem de novo.
- **Volume:** 48 arquivos (`ls ~/.claude/green-suite | wc -l`, 2026-07-30 — eram 34), 42–106 bytes cada. É o único depósito de (B) que **se poda sozinho**, e ainda assim cresceu: a poda é de 7 dias e o ritmo de gates recentes é maior que isso.

### B4 · `~/.claude/intent-guard/` — 0B · só o kill-switch

- **Único arquivo previsto:** `mode`. Cinco hooks o leem com o mesmo `MODE_FILE="$HOME/.claude/intent-guard/mode"`: `plan-gate.sh`, `mark-work.sh`, `capture-prompt.sh`, `delivery-audit.sh`, `task-checkpoint.sh`. `plugins/intent-guard/hooks/test_hooks_capture.sh` faz backup/restore dele durante o teste.
- **Estado atual: o diretório existe e está VAZIO (0B)** — nenhum `mode` gravado, logo o guard opera no default. **Configuração, descartável.** [confirmado]

### B5 · `~/.claude/context-guard/` — 0B · nada mora aqui

- O único vínculo é um **comentário** em `plugins/context-guard/hooks/context-guard.sh`: *"Kill-switch: crie `~/.claude/context-guard/mode` com 'off' pra desligar o guard globalmente"*. O diretório existe (criado em 2/jul) e está vazio.
- **O estado real do context-guard NÃO mora aqui — mora em `/tmp`, chaveado por sessão:** `STATE="/tmp/claude-context-pct-${SESSION_ID}"` e `SENTINEL="/tmp/claude-context-warned-${SESSION_ID}"` (`context-guard.sh`). O `context-guard-reset.sh` apaga os dois da sessão e ainda faz prune dos órfãos: `find /tmp -maxdepth 1 -name 'claude-context-pct-*' -mtime +1 -delete`. **Efêmero por definição** — `/tmp` some no boot. [confirmado; casa com o histórico de que o estado global entre sessões era o bug corrigido na v1.2.0]
- ⚠️ **Desde 2026-07-30 os dois scripts abortam sem `jq`** (`command -v jq >/dev/null 2>&1 || exit 0`, primeira linha executável de cada um). É fail-open **na direção do depósito**, não só do usuário: sem `jq` o `session_id` sai vazio, e aí `context-guard.sh` leria o contador da sessão errada e `context-guard-reset.sh` apagaria o sentinel de **outra** sessão. A guarda existe pra proteger a chave do estado, não pra evitar erro na tela. Mesma classe do bug de estado global da v1.2.0. [confirmado no código]

### B6 · `~/.claude/intent/` — 264K · **fallback**, não o depósito principal

⚠️ Correção importante de premissa: o ledger do intent-guard **deste projeto NÃO está em `~/.claude/intent/`**. `plugins/intent-guard/lib/ledger.py:intent_dir` resolve assim:

```python
root = project_root(cwd)                       # git rev-parse --show-toplevel, ou markers
if root: return os.path.join(root, ".claude", "intent")
slug = re.sub(r"[^a-zA-Z0-9]+", "-", os.path.abspath(cwd)).strip("-")
return os.path.join(os.path.expanduser("~/.claude/intent"), slug)
```

- Como este repo é git, o caderno vive em **`.claude/intent/`** (ver C2 abaixo). O `~/.claude/intent/` só recebe os cwd **sem** raiz de projeto — e é exatamente o que o disco mostra: as entradas são slugs de paths de outros projetos (`Users-<usuario>-PROGRAMACAO`, `…-<outro-projeto>`, `tmp`, …), **nenhuma de pedro-plugins**.
- **Natureza: histórico de intenção, insubstituível dentro do seu escopo, sem backup.** Vale para os projetos que caem no fallback, não para este.
- Provado por `plugins/intent-guard/lib/test_ledger.py`: o teste roda `ledger.py resolve-dir` num repo git temporário e afirma `== os.path.join(repo, ".claude", "intent")`. [confirmado]

### B7 · `~/.claude/plans/` — 2,7M, 213 arquivos · o dos PLANOS DO HARNESS (≠ A4)

- Grep desta rodada em `plugins/`, `_shared/` e `.claude/hooks/`: **nenhum escritor**. Só leitores e uma proibição explícita:
  - `plugins/qa-loop/skills/qa-loop/SKILL.md` — `--plan` procura o plano de implementação (`.claude/plans/*.md`, `docs/specs/*.md`).
  - `plugins/principles/skills/principles/SKILL.md` — procura seção "Princípios de Sistema" em `.claude/plans/*.md`.
  - `plugins/visual/hooks/pre-exitplan-visualize.sh` — diz literalmente *"não busque em `~/.claude/plans/`"*.
- **Quem escreve é o harness do Claude Code** (fluxo de plano), não este marketplace. [inferido — verifiquei a ausência de escritor no repo; não inspecionei o harness]
- **Natureza: insumo insubstituível e sem backup.** É a âncora do `/qa-loop` (fidelidade ao plano) e é referenciado por caminho absoluto dentro de HANDOFFs versionados — ou seja, o repo aponta para um depósito que não protege.
- ⚠️ **Ele ENCOLHEU entre as duas rodadas: 226 → 213 arquivos, 2,9M → 2,7M.** É o único depósito deste inventário que perdeu conteúdo sem que nada neste repo tenha apagado nada (o grep acima confirma: zero escritores no marketplace). Um depósito insubstituível, sem backup, que diminui sozinho é o pior par de propriedades da tabela toda. [medido; a causa da remoção é do harness e não foi determinada — inferido]
- ✅ **Endereçado em parte pela A4.** O `visual` v1.5.0 passou a escrever o plano **dentro do repo** (`<raiz>/.claude/plans/<id>.plan.json`, versionado) justamente porque este depósito não protege nada. Os dois coexistem e **não se falam**: `~/.claude/plans/*.md` continua sendo do harness (e `pre-exitplan-visualize.sh` segue dizendo literalmente *"não busque em `~/.claude/plans/`"*), enquanto `.claude/plans/*.plan.json` é do marketplace. **A colisão de nome é a armadilha**: um caminho relativo `.claude/plans` e um `~/.claude/plans` apontam para garantias opostas. [confirmado]

### B8 · `$CLAUDE_CONFIG_DIR/state/prose-ceiling/` — o orçamento de bloqueio do teto de prosa

Depósito **novo em 2026-07-30**, e o primeiro deste repo a morar em `<config>/state/` (o diretório `state/` nasceu com ele: `ls ~/.claude/state` mostra `prose-ceiling` e nada mais).

- **Escrito por:** `plugins/bootstrap/hooks/stop-prose-ceiling.py`, um hook de `Stop`, criado com `mkdir(parents=True, exist_ok=True)` **só quando há problema a reportar**. Resposta aprovada não toca no disco.
- ⚠️ **O caminho NÃO é fixo em `~/.claude/` — é resolvido por `CLAUDE_CONFIG_DIR`, e essa mudança consertou uma falha silenciosa.** Desde 2026-07-30 o hook faz `CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))` e `ESTADO = CLAUDE_DIR / "state" / "prose-ceiling"`; antes era `Path.home()` fixo. O leitor deste depósito (`plugins/bootstrap/lib/conformance.py`, constante `CLAUDE_DIR`) **sempre** honrou a env var, com a linha idêntica. Numa máquina com `CLAUDE_CONFIG_DIR` setado, o escritor gravava num lugar e o verificador lia noutro — e o relatório dizia *"nenhuma resposta furou o teto"* com o teto furado. O comentário no código nomeia o defeito: *"Falha silenciosa."* **Nesta máquina `CLAUDE_CONFIG_DIR` está unset**, então o caminho efetivo continua sendo `~/.claude/state/prose-ceiling/` — a mudança não move nada aqui; ela só faz o par escritor/leitor concordar em qualquer máquina. [confirmado nos dois arquivos + `echo "${CLAUDE_CONFIG_DIR:-unset}"` nesta rodada]
- **Dois tipos de arquivo, e eles guardam coisas diferentes:**
  - `<sha1[:16]>` — **um contador por resposta bloqueada**. A chave é `sha1(session_id + texto_INTEIRO_da_resposta)[:16]`; o conteúdo é um único dígito ASCII (**1 byte**), o número de bloqueios já gastos naquela resposta. Teto `MAX_BLOQUEIOS = 2`.
    ⚠️ **A chave é o texto inteiro de propósito, e o comentário no código explica o defeito que isso conserta:** com `texto[:200]` duas respostas diferentes dividiam o mesmo orçamento — e como o output style manda a primeira linha ser estável, a colisão era o **caso comum**, não a exceção. Chave curta em depósito chaveado por conteúdo não é otimização, é bug.
  - `bypass.log` — **JSONL, uma linha por desistência.** Quando o contador chega a 2 o hook para de bloquear (bloquear pra sempre trava a sessão) e, em vez de desistir em silêncio, grava `{session (8 chars), linhas_prosa, problemas, trecho (120 chars)}`. **Não existe no disco nesta rodada.**
- **Volume hoje: 0B, ZERO arquivos** — `ls -a ~/.claude/state/prose-ceiling` devolve só `.` e `..`; `du -sh` → `0B`. Eram **9 contadores de 1 byte** na rodada anterior do mesmo dia. ⚠️ **E isso não é o sistema se podando.** Nada no código apaga contador (ver o item abaixo); o diretório esvaziou porque alguém apagou de fora. **É o modelo de retenção funcionando como documentado — à mão** [o esvaziamento é confirmado; a autoria do `rm` é inferida, já que não há escritor nem podador que remova].
- **Quem lê:** `plugins/bootstrap/lib/conformance.py:check_bypass_teto` — e ele lê **só o `bypass.log`**, nunca os contadores. Ausência do log = `conforme("teto", "nenhuma resposta furou o teto de prosa")`; presença = desvio com as 3 últimas linhas de amostra e a instrução `rm <log>`.
- ⚠️ **NADA poda os contadores.** Não há `find -mtime`, não há TTL, não há limpeza no `SessionStart`: o único `rm` do sistema inteiro é o que o `conformance.py` **sugere ao usuário em texto**, e ele mira o `bypass.log`, não os `<sha1>`. Cada resposta reprovada deposita um arquivo de 1 byte que fica pra sempre. **A retenção desejada é "zero depois de lido" e ela depende de o usuário dar o `rm` à mão** — mesma forma do `askq.log` (B1). Está declarado assim em `durability.md §3.13`, não é omissão.
- **Natureza: efêmero por intenção, permanente na prática — descartável.** Apagar o diretório inteiro devolve o orçamento de bloqueio a zero para todas as respostas (e perde a contagem de furos do teto, se algum dia houver). Nenhum conhecimento se perde. **Sem backup**, como todo o resto de (B).
- **Desligado por `PROSE_CEILING=0`; teto configurável por `PROSE_CEILING_MAX` (default 6).** Com o hook desligado o depósito simplesmente não nasce.
- **Cobertura de durabilidade: `durability.md §3.13`** — classificado *sem cobertura, com justificativa válida*, e com **duas** justificativas distintas para os dois arquivos (contador = orçamento de execução; `bypass.log` = medição de curto prazo cujo valor acaba quando o conformance a mostra). ✔ Regra da gen 3.8 satisfeita.

---

## (C) Dentro do repo, mas **gitignored** — some se a máquina sumir

Estes moram no repo e parecem protegidos, mas não estão no git.

### A1 · `.claude/.project-doc/findings.jsonl` — o journal do conhecimento

**Destrackeado em 2026-07-31** — saiu do índice do git (`git rm -r --cached`) e entrou no `.gitignore` (**linha 35**, `.claude/.project-doc/`); continua no disco desta máquina.

- **Tipo:** JSONL append-only (1 evento por linha).
- **Onde vive:** `.claude/.project-doc/findings.jsonl`, **fora do git desde 2026-07-31** — a pasta inteira é ignorada, com o comentário versionado *"journal, ledger e backups da doc: estado local da máquina, não distribuído"*.
- **Tamanho:** 1.176.651 bytes (1,1M no `du`), **898** linhas [re-medido 2026-07-31, `HEAD = ff32947` — byte a byte idêntico às duas rodadas anteriores, porque a adoção no journal não rodou nestes ciclos].
  ```bash
  du -h  .claude/.project-doc/findings.jsonl   # 1,1M
  wc -lc .claude/.project-doc/findings.jsonl   # 898  1176651
  git ls-files    .claude/.project-doc/        # (vazio — 0 arquivos rastreados)
  git ls-tree -r --name-only HEAD -- .claude/.project-doc | wc -l   # 3  (o que HEAD ainda carrega)
  git check-ignore -v .claude/.project-doc/findings.jsonl
  #   .gitignore:35:.claude/.project-doc/	.claude/.project-doc/findings.jsonl
  ```
- **Natureza: INSUBSTITUÍVEL, e desde 2026-07-31 insubstituível SEM CÓPIA NENHUMA.** Não existe regenerador. A matéria-prima (transcripts `.jsonl` das sessões) é **local à máquina e não viaja** [confirmado — a mineração vive em `journal.py:collect_transcripts`, que lê `discover_all_transcripts(project_root)`]. Até 2026-07-30 o journal era o veículo do conhecimento **entre** máquinas, e era o git que o carregava. 🔴 **Tirá-lo do git tirou o veículo:** o arquivo continua sendo a única forma persistida daquele conhecimento, só que agora existe num disco só. Perder este Mac perde os 898 eventos, e não há de onde restaurar. A decisão foi consciente (o `.gitignore` a documenta), mas o preço é este e está medido. Cobertura: `durability.md §3.15`.
- **Quem escreve:** `plugins/project-doc/lib/journal.py`, função `append_events()` — abre em modo `"a"` e escreve `json.dumps(e) + "\n"`. Não existe caminho de reescrita/truncamento no arquivo. Chamadores: `run_update`, `run_invalidate`, `run_curate`, `run_adopt`, `run_fuse`.
- **Quem lê:** `journal.py:read_events` → `journal.py:fold`; `plugins/project-doc/lib/doc_lint.py` (monta o caminho em `.claude/.project-doc/findings.jsonl`); `plugins/project-doc/lib/pattern_check.py` (check `(c)`: falha se o journal não existir).
- ⚠️ **Armadilha de ORDEM, e ela morde este doc especificamente.** `findings.jsonl` está no `scope:` deste arquivo, então **qualquer `journal.py adopt` rodado DEPOIS do `--restamp` deixa este doc `stale` na hora** — o `project_staleness` vê o arquivo de escopo mais novo que o carimbo e acusa, mesmo sem uma linha de conteúdo ter envelhecido. Aconteceu duas vezes em 2026-07-30, e a segunda foi o que expôs a regressão do manifest do bootstrap (§10.1 do `architecture.md`), porque investigar o `stale` em vez de re-carimbar por cima foi o que achou o defeito. **A ordem certa no `/doc-touch` é: adotar no journal PRIMEIRO, carimbar DEPOIS, e não adotar mais nada até o próximo ciclo.** Corolário: as medições de volume acima (linhas, bytes, composição) são as que envelhecem mais rápido de toda a doc — cada rodada de touch acrescenta eventos.

**Formato (evidência: `journal.py:fold`, corpo lido integralmente):** três tipos de evento, e o estado vivo é o *fold* deles em ordem de append.

```
{"ev":"discovered","id":<sha1[:16]>,"raw_kind":...,"text":...,"anchors":[...],"source":{...},"scrubbed":bool,"ts":epoch}
{"ev":"invalidated","target":<id>,"reason":"...","ts":epoch}
{"ev":"curated","target":<id>,"text":"...","ts":epoch}
```

- `discovered` cria (só a **primeira** ocorrência de um id conta — `if fid and fid not in state`).
- `invalidated` mata sem apagar o `discovered`; a morte é **definitiva** até uma curadoria/rediscovery explícita (docstring de `fold` diz literalmente: "Um id invalidado permanece morto mesmo que re-apareça num discovered posterior").
- `curated` sobrepõe o texto exibido (`live_findings` troca `text` por `curated` quando presente).
- `id` = `sha1(texto_normalizado + "|" + raw_kind)[:16]` (`journal.py:finding_id`) → append idempotente: re-minerar a mesma fala não duplica.

**Composição real do arquivo hoje** (derivado mecanicamente nesta rodada):

```bash
python3 -c "
import json,collections
c=collections.Counter(); k=collections.Counter(); scr=0
for ln in open('.claude/.project-doc/findings.jsonl',encoding='utf-8'):
    if not ln.strip(): continue
    e=json.loads(ln); c[e.get('ev')]+=1
    if e.get('ev')=='discovered': k[e.get('raw_kind')]+=1
    if e.get('scrubbed'): scr+=1
print(dict(c)); print(dict(k)); print('scrubbed:',scr)"
```
```
eventos:   discovered 885 · invalidated 11 · curated 2         (= 898 linhas)
raw_kind:  user_directive 380 · commit 212 · handoff 129 · ask_answer 112
           gotcha 26 · doc_nuance 14 · memory 9 · tool_rejection 3
scrubbed:  23
```

**Por que um arquivo cheio de conversa verbatim podia ser versionado — e por que a barreira continua valendo mesmo agora que ele não é:** todo texto passa pelo scrubber antes do append — `run_update` chama `scrub(c["text"])` e, se houver captura, `stash_secrets(secrets, project_root)` **antes** de montar o evento. O mesmo acontece em `run_invalidate` (o `reason`), `run_curate` e `run_adopt`. O valor-secreto sai do arquivo e vira o placeholder `‹cofre:LABEL:8hex›`; nome, host, porta e contexto ficam. Os 23 eventos com `scrubbed: true` são exatamente os que tiveram captura. [confirmado] ⚠️ **O destrack não afrouxa nada aqui:** o scrubber roda na escrita, não no `git add`, então ele segue sendo a barreira mesmo com o arquivo fora do índice — e continua sendo o que impede que um `git add -f` acidental publique um segredo.

### A2 · `.claude/.project-doc/ledger.json` — o que faz a rodada ser delta

**Destrackeado em 2026-07-31** — saiu do índice junto com o resto de `.claude/.project-doc/` (`.gitignore:35`); continua no disco desta máquina.

- **Tipo:** JSON único, sobrescrito a cada rodada (`journal.py:save_ledger`, modo `"w"` + `json.dump`).
- **Onde vive:** `.claude/.project-doc/ledger.json`, **fora do git desde 2026-07-31**.
- **Tamanho:** 8,0K — `du -h .claude/.project-doc/ledger.json` [re-medido 2026-07-31, `HEAD = ff32947`]. A pasta inteira: **1,4M**.
- **Natureza: RECONSTRUÍVEL, com custo — e é o único dos cinco destrackeados que sai barato dessa mudança.** Perdê-lo não perde conhecimento (o journal é a verdade); só força uma rodada de cold-start — re-mineração de todas as sessões e do histórico de commits (com teto de 1000, ver `collect_commits`, constante `CAP`). O journal deduplica por `finding_id`, então nada duplica.
- **Quem escreve:** `journal.py:save_ledger`, chamado no fim de `run_update`.

**Conteúdo (3 chaves, lidas de `journal.py:load_ledger` e conferidas no arquivo real):**

```bash
python3 -c "
import json;d=json.load(open('.claude/.project-doc/ledger.json'))
print(list(d.keys()), len(d['mined_sessions']), d['last_commit'], len(d['distilled_hashes']))"
# ['mined_sessions','last_commit','distilled_hashes'] 113 5ce0c1bc34018ed2e894f5aaeac263e4141d2410 0
```

- `mined_sessions` — **mapa `{session_id: mtime_do_jsonl}`**, hoje com 113 entradas. Não é "lista de vistas": `collect_transcripts` re-minera quando `mtime > mined_sessions.get(sid, -1.0)`, o que recupera falas acrescentadas a uma sessão depois que ela deixou de ser a ativa. `load_ledger` migra o formato antigo (lista) para `{sid: 0}`, forçando re-mineração.
- `last_commit` — SHA do HEAD da última rodada **completa** de `journal.py update`; hoje `5ce0c1bc…`, que **não** é o `HEAD` desta rodada (`ff32947`): os `/doc-touch` seguintes re-projetaram doc sem re-minerar, e é por isso que o ledger ficou para trás. É a base do range `last..HEAD` do forward delta **e** do backward delta (`git diff last_commit..HEAD --name-only`). Se a história for reescrita (rebase/amend/reset), `_commit_reachable` detecta o SHA órfão e degrada para cold-start em vez de deixar `git log` sair 128 e perder todos os commits do range.
- `distilled_hashes` — **presente no schema e vazio (0 chaves)**. `load_ledger` só faz `setdefault("distilled_hashes", {})`; não há nenhuma escrita nessa chave em `plugins/` (grep desta rodada só acha o setdefault, a fixture em `test_journal.py`, o `PRD-v3.md` e a menção no SKILL.md). Campo **declarado e não usado**. [confirmado]

### A3 · `graphify-out/graph.json` — o knowledge graph

🔴 **Destrackeado em 2026-07-31, e aqui não foi um arquivo que saiu do git: foi o diretório inteiro.** `git rm -r --cached graphify-out/` tirou os **40** arquivos que `HEAD = ff32947` ainda carrega, e o `.gitignore` ganhou a linha **28** — `graphify-out/`, sem exceção nenhuma —, com o comentário versionado *"o diretório INTEIRO saiu do controle de versão nesta limpeza (regenerável com `graphify update`)"*. Nada foi apagado do disco: são **76M** e **1119** arquivos ali agora, todos invisíveis para o git.

- **Tipo:** JSON node-link (formato NetworkX): `nodes[]`, `links[]`, `hyperedges[]`.
- **Onde vive:** `graphify-out/graph.json`, **fora do git desde 2026-07-31**.
- **Tamanho:** 3.178.225 bytes (3,0M) — `du -h graphify-out/graph.json` [re-medido 2026-07-31, `HEAD = ff32947`; eram 5.696.943 bytes / 5,4M em 2026-07-30]. **A queda de 2,5M não é poda: é o plugin de terceiro que saiu do repo** — o corpus encolheu junto.
- **Natureza: RECONSTRUÍVEL, e é isso que torna este destrack o mais barato dos cinco.** `graphify update . --force` re-extrai por AST, sem LLM, em segundos; perder o diretório custa CPU, não conhecimento. A camada que **custa LLM** é o nome de comunidade (`graphify-out/.graphify_labels.json`, 10.939 bytes, **403 chaves** [re-medido nesta rodada; eram 14.537 bytes / 542 chaves]) — essa sim vale ouro relativo, porque `/graphify` cobra tokens pra recriar, e ⚠️ **ela saiu do git junto com o resto**: é o único pedaço de `graphify-out/` cuja perda não se resolve com um comando. Cobertura: `durability.md §3.15`.
- **Quem escreve:** a CLI externa `graphify` (não é código deste repo). O `/project-doc` FULL e o `/doc-touch` a invocam antes de escrever doc.
- **Quem lê:** `plugins/project-doc/lib/graph_map.py` — `graph_paths()` monta os dois caminhos canônicos (`graphify-out/graph.json` + `graphify-out/.graphify_labels.json`), `load_graph()` degrada para `(None, None)` se ausente/ilegível, e `build_map()` destila em `files` (ranking por fan-in), `god_nodes`, `communities` e `hyperedges`. O fan-in **semântico** exclui as relações estruturais `{"contains","defines","method"}` (constante `STRUCTURAL_RELATIONS`) — sem isso o `contains` domina o ranking. Saída desta rodada (`python3 plugins/project-doc/lib/graph_map.py --project-root .`): **3920 nós, 5039 links, 6 hyperedges (de 12 no cru), 30 comunidades nomeadas, 60 god nodes**, com `god_min: 3` e `hyper_min: 0.85` — medido em **2026-07-31** contra o commit que o próprio `GRAPH_REPORT.md` carimba (*"Built from commit: `ff329471`"*, = `HEAD`). ⚠️ **A queda de 6797/7737 para 3920/5039 NÃO é perda de código deste marketplace** — é o plugin de terceiro que foi removido do repo por inteiro; o corpus encolheu, e o grafo com ele. É a mesma classe do que aconteceu quando `pi-plugins/` saiu do corpus em 2026-07-28 (de 7219/8167 para 6423/7271): **queda no grafo depois de uma limpeza mede a limpeza, não uma regressão.** ⚠️ **`god_nodes: 60` é TETO, não medição** — `build_map()` corta em `top_gods=60` (a linha `god_nodes = god_nodes[:top_gods]` vem com o comentário de que o corte é ANTES de derivar `god_ids`). O número não sobe nem que o repo dobre; tratá-lo como grandeza medida é ler um limite como resultado. ⚠️ **Não cite o `manifest.json` como "quantos arquivos"** — ele tem **435** chaves, **106** delas entradas mortas de `pi-plugins/` e mais **4** do plugin de terceiro já removido; o número que o grafo realmente cobre é **287** (`source_file` distinto nos nós, e **zero** deles em `pi-plugins/`). ⚠️ **A gordura do manifest não encolhe nem quando o corpus encolhe: as chaves foram de 422 → 430 → 435 enquanto os nós caíam pela metade** — o manifest só cresce, nunca reconcilia, e a remoção do plugin de terceiro é a demonstração mais limpa disso (4 chaves mortas novas, criadas por uma remoção). Ver o item de reconciliação nas Pendências. ⚠️ Os `hyperedges` caíram de 12 para 6 porque `build_map()` **filtra** — o `graph.json` cru segue com 12; citar um número sem dizer qual instrumento mediu é como os dois divergem. [confirmado]

**O que de `graphify-out/` é versionado hoje: NADA.** O `.gitignore` foi reescrito em 2026-07-31 e a lista de cinco exceções que existia aqui **deixou de existir** — no lugar dela ficou uma linha só, lida integralmente do arquivo real nesta rodada:

```
27:# graphify — o diretório INTEIRO saiu do controle de versão nesta limpeza (regenerável com `graphify update`)
28:graphify-out/
```

Comparação com a regra anterior, que este doc descrevia até 2026-07-30: havia cinco padrões (`​.graphify_python`, `.graphify_root`, `cache/`, `20*/`, `graph.html`) e cinco arquivos tracked na raiz (`graph.json`, `manifest.json`, `GRAPH_REPORT.md`, `cost.json`, `.graphify_labels.json`). **A regra nova engole as duas listas.** Verificado nos dois sentidos:

```bash
git ls-files graphify-out/ | wc -l                          # 0
git ls-tree -r --name-only HEAD -- graphify-out/ | wc -l     # 40   (o que HEAD ainda carrega)
git check-ignore -v graphify-out/graph.json
#   .gitignore:28:graphify-out/	graphify-out/graph.json
find graphify-out -type f | wc -l                            # 1119 (no disco, intacto)
du -sh graphify-out                                          # 76M
```

✅ **A dívida dos backups datados acabou — e acabou por inclusão, não por decisão sobre ela.** Até 2026-07-30 este bloco trazia o gotcha *"20M de backups datados continuam TRACKED apesar da regra `graphify-out/20*/`"*: a regra valia pra frente e era inerte pra trás, porque `.gitignore` não destrackeia o que já entrou. O `git rm -r --cached` fez o que a regra não podia fazer. Medido:

```bash
git ls-tree -r --name-only HEAD -- graphify-out/ | grep -c '^graphify-out/20'  # 35  (ainda no HEAD)
git ls-files graphify-out/ | grep -c '^graphify-out/20'                        # 0   (fora do índice)
find graphify-out -maxdepth 1 -type d -name '20*' | wc -l                      # 13  (no disco)
du -ch graphify-out/20*/ | tail -1                                             # 56M
```

⚠️ **Mas o histórico não encolheu, e é aí que mora a leitura correta.** Destrackear tira do índice e do próximo commit; **não** tira do passado. O `.git` continua carregando tudo o que já entrou:

```bash
du -sh .git             # 37M  (era 11M em 2026-07-26 e 31M em 2026-07-30)
git count-objects -vH   # size: 31.30 MiB · size-pack: 4.67 MiB
git rev-list --objects HEAD -- graphify-out/graph.json \
  | git cat-file --batch-check='%(objecttype) %(objectsize) %(rest)' \
  | awk '$1=="blob"{s+=$2;n++} END{print n" blobs, "s" bytes"}'   # 32 blobs, 153936130 bytes
```

**32 blobs distintos de `graph.json`, 153.936.130 bytes brutos somados** — quatro a mais que na medição de 2026-07-30, porque cada rodada de doc rodava um `graphify update --force` e reescrevia o arquivo inteiro. O destrack **para o sangramento pra frente** (não entra blob novo) e **não devolve** um byte do que já entrou; para isso seria preciso reescrever a história. É a diferença entre fechar a torneira e esvaziar a banheira, e só a primeira aconteceu. [confirmado]

### A4 · `<repo>/.claude/plans/*.plan.json` — os planos de implementação ticáveis

🔴 **Destrackeado em 2026-07-31** — `.gitignore:39` (`.claude/plans/`), sob o comentário versionado *"Memória de sessão — pertence a esta cópia de trabalho, não ao marketplace"*. Continua no disco desta máquina.

> ⚠️ **Não confundir com `~/.claude/plans/` (B7).** Mesmo nome, depósitos diferentes: aquele é global, do harness; este é do marketplace, dentro do repo. **Até 2026-07-30 a diferença que importava era a cobertura** — o de lá sem backup, este versionado. **Essa diferença acabou:** desde o destrack os dois estão igualmente sem cobertura, e o que ainda os separa é só quem escreve. O argumento que criou este depósito no `visual` v1.5.0 (*"o de lá não protege nada"*) deixou de valer para ele mesmo.

- **Tipo:** um JSON por plano, sobrescrito por `os.replace` de um `.tmp` (escrita atômica — `plan_state.py:save`).
- **Onde vive:** `<raiz-do-projeto>/.claude/plans/<id>.plan.json`, **fora do git desde 2026-07-31**.
  ```bash
  git ls-files    .claude/plans/ | wc -l                          # 0
  git ls-tree -r --name-only HEAD -- .claude/plans | wc -l        # 8   (o que HEAD ainda carrega)
  ls -1 .claude/plans/*.plan.json | wc -l                         # 9   (no disco)
  git check-ignore -v .claude/plans
  #   .gitignore:39:.claude/plans/	.claude/plans
  ```
- **Tamanho hoje:** 92K, **9 arquivos**, 1476 linhas (`du -sh .claude/plans` · `wc -l .claude/plans/*.plan.json`) — eram 1 arquivo / 159 linhas em 2026-07-27 e 6 / 938 em 2026-07-30. **O depósito nonuplicou em quatro dias e continua sem prune** — só que agora cresce fora de qualquer cópia.
- **Natureza: INSUBSTITUÍVEL, e desde 2026-07-31 insubstituível sem cópia nenhuma.** Não existe regenerador. A alternativa — reconstruir o plano do transcript — é exatamente o mecanismo lossy que o depósito veio substituir (ver B7 e o cabeçalho de `plan_state.py`), e o transcript é local. 🔴 **O que se perde junto não é o plano, é a prova:** cada passo `done` carrega o `evidence` que o `tick` exigiu, e essa é a parte que nenhuma releitura de transcript devolve. Cobertura: `durability.md §3.15`.
- **Quem escreve:** `plugins/visual/lib/plan_state.py` — verbos `init` (autoria, uma vez), `tick` (marca com prova), `state`, `close`/`reopen`. Estado (`status`, `evidence`, `done_at`) é do programa; o modelo não escreve esses campos à mão.
- **Quem lê:** o próprio `plan_state.py` (`render`/`page`/`open`), `plugins/visual/hooks/sessionstart-plan.sh` e `plugins/visual/hooks/stop-plan-status.sh` (o primeiro via `open --json`, o segundo via `brief`), e a skill `handoff` (que passa a preferi-lo ao `last_plan` do transcript).
- **Onde o diretório é resolvido:** `plugins/visual/skills/visual/resolve-dir.sh <cwd> plans` — a mesma cascata do `/visual` (raiz git → marcador de projeto → `~/Desktop/claude-plans`), com o subdiretório como 2º argumento.

**Formato (evidência: `plan_state.py:validate`, lido integralmente):**

```
{"id":<slug>, "title":..., "created":"YYYY-MM-DD", "status":"active|done|abandoned",
 "phases":[{"id":"F1","title":...,"detail":[<linhas>]?,
            "items":[{"id":"F1.1","title":...,"desc":<=140 chars,
                      "status":"todo|doing|blocked|done","evidence":...,"done_at":...}]}]}
```

- `id` de fase casa `^F\d+$`; de passo, `^F\d+\.\d+$` **com o prefixo da própria fase**. O id é a identidade — `merge()` recusa id existente que venha com outro `title`.
- `desc` é obrigatório e limitado a `DESC_MAX = 140`. É a linha didática que aparece na árvore; parágrafo é rejeitado pelo schema.
- **Fase não tem `status` próprio** — `phase_status()` deriva dos passos. Não existe onde gravar a contradição "fase pronta com passo pendente".
- `evidence` só entra por `tick --evidencia` (mínimo `EVIDENCE_MIN = 8` chars); `state` não consegue marcar `done`.

**Estado real dos 6 arquivos deste repo hoje** (derivado nesta rodada):

```bash
python3 -c "
import json,os
for f in sorted('.claude/plans/'+x for x in os.listdir('.claude/plans') if x.endswith('.json')):
    d=json.load(open(f)); it=[i for p in d['phases'] for i in p['items']]
    print(os.path.basename(f), d['status'], len(d['phases']),'fases', len(it),'passos',
          sum(1 for i in it if i['status']=='done'),'feitos',
          sum(1 for i in it if i.get('evidence')),'com prova')"
```
```
2026-07-27-arvore-do-plano-no-visual         done    5 fases · 15 passos · 15 feitos · 15 com prova
2026-07-28-design-como-doc-autoral           done    3 fases ·  9 passos ·  9 feitos ·  9 com prova
2026-07-28-plugin-branches                   done    4 fases · 12 passos · 12 feitos · 12 com prova
2026-07-28-varredura-de-contrato-dos-plugins done    5 fases · 20 passos · 20 feitos · 20 com prova
2026-07-29-furos-do-gate-de-deploy           active  3 fases · 12 passos · 11 feitos · 11 com prova
2026-07-30-bootstrap-instalacao-nova         done    6 fases · 10 passos · 10 feitos · 10 com prova
2026-07-30-intent-guard-catraca              done    5 fases ·  9 passos ·  9 feitos ·  9 com prova
2026-07-30-marketplace-presenteavel          done    6 fases · 15 passos · 15 feitos · 15 com prova
2026-07-31-repo-limpo-do-zero                active  5 fases · 18 passos ·  0 feitos ·  0 com prova
```

- **A invariante "feito ⇒ com prova" vale nos 9**: em cada arquivo o nº de `done` é idêntico ao nº de `evidence`, sem uma única exceção. Não é disciplina do autor — é o schema: `evidence` só entra por `tick --evidencia` e `state` não consegue marcar `done`. O depósito não tem onde gravar "feito sem prova". ⚠️ **O `2026-07-31-repo-limpo-do-zero` com 0/18 é o caso-limite que confirma a regra pelo outro lado:** um plano recém-aberto satisfaz a invariante trivialmente (0 = 0). "Invariante satisfeita" não quer dizer "trabalho feito".
- **Exatamente 2 planos `active`** (`2026-07-29-furos-do-gate-de-deploy`, 11 de 12; e `2026-07-31-repo-limpo-do-zero`, 0 de 18) — são os que o `sessionstart-plan.sh` ressuscita depois do `/clear`. Os 7 `done` ficam no disco e somem do `open`.
- ⚠️ **Fase não é unidade de trabalho neste schema, é agrupamento** — `phase_status()` deriva o estado dos passos e a fase não guarda status próprio. O par mais extremo hoje é `bootstrap-instalacao-nova` (6 fases / 10 passos) contra `varredura-de-contrato` (5 fases / 20 passos): mesma ordem de grandeza de moldura, o dobro de conteúdo. Contar fases pra estimar tamanho de plano mede a moldura, não o conteúdo.

**Custo de crescimento:** ≈ 10 KB por plano na média de hoje (92K / 9). Não há prune nem arquivamento; plano encerrado (`status != "active"`) some do `open` mas fica no disco. Ao ritmo de 8 planos em 4 dias, este é o depósito deste repo que **mais rápido** ganha arquivos. ⚠️ **Até 2026-07-30 a frase aqui era "fica no git para sempre … o preço aceito de viajar entre máquinas". As duas metades caíram junto com o destrack:** não fica no git, e não viaja. O que sobrou do custo é só o disco local.

### A6 · `.claude/ata/` — logs de sessão (30 arquivos, 1,8M)

🔴 **Destrackeado em 2026-07-31** — `.gitignore:38` (`.claude/ata/`), sob o comentário versionado *"Memória de sessão — pertence a esta cópia de trabalho, não ao marketplace"*. Continua no disco desta máquina.

```bash
git ls-files    .claude/ata | wc -l                        # 0
git ls-tree -r --name-only HEAD -- .claude/ata | wc -l     # 30   (o que HEAD ainda carrega)
ls -1 .claude/ata | wc -l                                  # 30   (no disco)
du -sh .claude/ata                                         # 1,8M
```

Os 30 se dividem em **14 `LOG-<uuid>.md` + 14 `manifest-<uuid>.json` + 1 `INDEX.md` + 1 handoff legado**. São transcrições/atas narrativas de sessões (eram 24 / 1,4M em 2026-07-26 e 28 / 1,6M em 2026-07-30). 🔴 **Insubstituível** pelo mesmo motivo do journal — o transcript-fonte é local e não viaja —, **e desde o destrack é insubstituível sem cópia nenhuma**: era a única classe deste inventário cuja proteção não tinha ressalva alguma, e passou direto de "coberta" para "só nesta máquina". Não passam pelo scrubber do `journal.py` — são escritos por fluxo humano/skill, não por `append_events` [inferido — não localizei nesta rodada o escritor exato desses arquivos]. Cobertura: `durability.md §3.15`.

- **`.claude/intent/` — 476K.** O caderno append-only do intent-guard **deste projeto**: `ledger.jsonl` (**460 linhas** em 2026-07-31 — eram 409 na noite anterior, 377 poucas horas antes disso e 155 em 2026-07-26, **+197% em cinco dias**; era o depósito que mais crescia em proporção neste inventário e o único desse ritmo sem backup — hoje divide essa condição com os cinco destrackeados), `ledger.lock` (arquivo de `fcntl.flock` de `ledger.py:locked`), **27** `audit-<epoch>.json`, **16** marcadores `.applied` (`ledger.py:apply_audit` grava o marker para não re-aplicar), **1** `.escopo` e um `ledger.jsonl.poluido.bak`.
  Não está no `.gitignore` do repo — está em **`.git/info/exclude`** (linha 18: `.claude/intent/`), escrito por `ledger.py:ensure_exclude`, cuja docstring explica a escolha: *"Ignore LOCAL (.git/info/exclude) — nunca toca arquivo versionado do repo."*
  Eventos: `raw` / `classify` / `verdict` / `baixa` (docstring do módulo). Estado vivo = `ledger.py:fold`, que **filtra por `session`** — sem esse filtro, sessões paralelas no mesmo projeto compartilhavam a lista de vivos e uma auditoria cobrava frentes de outra.
  **Natureza: histórico de intenção — insubstituível e sem backup.** [confirmado]

  🔴 **A contagem de arquivos aqui não é volumetria — é a medição de um defeito, e ela está na diferença entre dois números.** Derivado nesta rodada:

  ```bash
  ls -1 .claude/intent/audit-*.json  | wc -l     # 27  auditorias geradas
  ls -1 .claude/intent/*.applied     | wc -l     # 16  transcritas pro ledger
  ls -1 .claude/intent/*.escopo      | wc -l     #  1
  wc -l .claude/intent/ledger.jsonl              # 460 eventos
  # fold(load(dir), session=None) → live 42 · pending 17 · faixa p-12 … p-75
  # eventos por tipo: raw 200 · classify 183 · verdict 44 · baixa 33
  ```

  **11 das 27 auditorias nunca viraram `.applied`** — foram geradas, custaram um subagente cada, e o veredito nunca chegou ao caderno. É a mesma assinatura do defeito relatado de fora em 30/07 (*"3 auditorias geradas, só 1 transcrita"*), e a razão está do outro lado da conta: **42 pedidos vivos** acumulados de `p-12` a `p-75`, contra **44 `verdict`** e **33 `baixa`** em 460 eventos. O gate cobrava veredito de todo pedido vivo **no instante da leitura**, mas o auditor só fora encarregado dos vivos **no instante do bloqueio** — e cada mensagem entre um e outro criava pedido novo. Reproduzido nesta sessão contra a auditoria mais recente:

  ```bash
  python3 plugins/intent-guard/lib/ledger.py audit-check --cwd . \
    --file .claude/intent/audit-1785436084.json
  # {"ok": false, "why": ["pedido vivo p-12 sem veredito", … 34 linhas …]}
  # o arquivo julgou UM pedido: p-62
  ```

- **`<auditoria>.escopo` — o depósito de NATUREZA NOVA (intent-guard v0.5.0), 1 arquivo hoje.** Companheiro de cada `audit-<epoch>.json`, mora no mesmo `.claude/intent/` e herda o mesmo `.git/info/exclude`.
  - **Tipo:** array JSON de ids numa linha, escrito por `jq -c '[.[] | .id]'`. O único que existe hoje é `audit-1785466744.json.escopo`, conteúdo `["p-74","p-75"]` [lido nesta rodada].
  - **Quem escreve — e este é o ponto:** o **hook**, `plugins/intent-guard/hooks/delivery-audit.sh`, na linha `> "${OUTP}.escopo"`, **no instante do bloqueio**. Não o auditor. É o único arquivo deste diretório que nasce antes do artefato que ele acompanha: quando o gate roda, o `audit-<epoch>.json` **ainda não existe** — quem vai escrevê-lo é o subagente. O comentário do hook nomeia a alternativa recusada: *"Depender do modelo ecoar a lista seria trocar mecanismo por exortação."*
  - **Quem lê:** `ledger.py:audit_check`, que abre `path + ".escopo"` e reduz o conjunto cobrado a `perguntados ∩ vivos` — *"só cobra o que foi perguntado E continua vivo"*.
  - **Natureza: registro de um INSTANTE, não regenerável.** Ele grava quem estava vivo às 21h06 de um dia específico; o ledger de amanhã não sabe reconstruir isso. Ver `durability.md §3.14`.
  - **O primeiro sidecar apareceu:** o mecanismo nasceu em `a134e9c` e o primeiro bloqueio de entrega desde então produziu o par `audit-1785466744.json` + `.escopo`. As 26 auditorias anteriores continuam sem sidecar **de propósito** — sem ele, `audit_check` cai no comportamento anterior (cobra todos os vivos). Nada retroage.
  ⚠️ **Nada apaga `.escopo`.** Como o `.applied`, ele acumula um arquivo minúsculo por bloqueio, para sempre. Mesma forma de retenção do resto do diretório: nenhuma.
- **`.claude/visual/` — 3,9M.** As páginas HTML geradas pelo `/visual`. Gitignored (`.gitignore:44`). **Descartável** (é apresentação). ⚠️ **A ressalva que existia aqui — "note que os HANDOFFs versionados referenciam arquivos daqui por nome" — mudou de forma:** os três `.claude/HANDOFF*.md` saíram do git em 2026-07-31 (`.gitignore:40`). Não é mais um arquivo coberto apontando para um descoberto; agora **as duas pontas estão descobertas**, o que remove a inconsistência e aumenta a exposição.
- **`.claude/.project-doc/backups/` — 248K, 5 snapshots** (`20260621T002445Z` … `20260726T235657Z`). Cópia de `CLAUDE.md` + `.claude/docs/` antes de cada re-mineração, + `MANIFEST.json`. ⚠️ **Até 2026-07-30 esta pasta era o caso interessante do diretório — a única parte ignorada de um `.project-doc/` versionado, e o `.gitignore` explicava a distinção com todas as letras (*"o journal/ledger em .project-doc/ SÃO versionados; só os backups não"*). A distinção sumiu:** a regra de hoje é `.claude/.project-doc/` inteiro (`.gitignore:35`), backups e journal no mesmo saco. **Descartável** (rede de segurança de uma rodada) — o que mudou não foi a natureza dela, foi a dos vizinhos.
- **`.claude/.project-doc/.run-*.json` — ausentes agora, ~1,2M quando existem.** Snapshots de uma rodada de doc: `.run-collect.json` (~1.224.983 bytes, a coleta) e `.run-graphmap.json` (~11.572 bytes, o mapa do grafo). **Descartáveis / regeneráveis** — são o insumo do run corrente, e por isso só existem *durante* uma rodada: `ls .claude/.project-doc/` hoje mostra apenas `backups/`, `findings.jsonl`, `ledger.json` e `lint-allow.txt`. A linha própria que o `.gitignore` tinha para eles deixou de ser necessária — a regra do diretório inteiro já os cobre.
- **`.claude/qa-loop/telemetry.jsonl` — 3 linhas** (4,0K na pasta). Telemetria de sessões de review. Gitignored (`.gitignore:32`). **Descartável.**

---

## Fora do inventário — verificado e não guarda dado

Checado mecanicamente nesta rodada; nada aqui é depósito:

```bash
git ls-files | grep -Ei 'docker-compose|Dockerfile|\.sql$|migrations?/|prisma|package-lock|yarn\.lock|pnpm-lock|poetry\.lock|requirements.*\.txt|\.env$|\.db$|\.sqlite'
# → plugins/archify/skills/archify/package-lock.json   (e nada mais)
git ls-files | wc -l   # 251 arquivos versionados no total
```

⚠️ **Os 251 são MENOS do que os 286 de 2026-07-26 e do que os 328 de 2026-07-30, e a queda não é código apagado.** `HEAD = ff32947` ainda carrega **335** arquivos (`git ls-tree -r --name-only HEAD | wc -l`); os **84** que faltam no índice são as remoções deste destrack, ainda não commitadas. Ler "o repo encolheu" a partir daqui é ler errado: **o índice encolheu, o disco não.**

- **Nenhum banco de dados.** Sem SQLite, sem Postgres, sem Redis, sem Mongo. As únicas ocorrências das strings `sqlite`/`redis` em código são: a lista de extensões conhecidas `KNOWN_EXT` do scrubber (`journal.py`) e sua fixture de teste. Nada abre conexão.
- **Sem `docker-compose.yml`, sem `Dockerfile`, sem migrations, sem ORM.**
- **Sem lockfile de projeto.** O único `package-lock.json` tracked pertence a um plugin (`archify`) — é dependência de renderer, não depósito de dado.
- **Sem `.env` versionado.** `.env` e `.env.local` estão no `.gitignore` e não há nenhum tracked.
- **`.claude-plugin/marketplace.json` e os `plugins/*/.claude-plugin/plugin.json`** são **manifesto/catálogo**, não depósito: descrevem plugins e versões, nenhum estado de runtime é acumulado neles, e **só humano escreve neles**. ⚠️ **Não confunda com `plugins/bootstrap/config/manifest.json`**, que tem nome parecido e é o oposto: um hook o reescreve a cada `SessionStart` e o commita sozinho. Esse é depósito e está inventariado em **A5c**.
- **`pi-plugins/` (raiz, GITIGNORED desde 2026-07-28)** — cópia obsoleta e já divergente de plugins do marketplace. **Não é depósito, é lixo a limpar.** ✅ **Deixou de poluir o grafo:** a regra `pi-plugins/` está no `.gitignore` (**linha 47** após a reescrita de 2026-07-31, com o comentário *"cópia local defasada de plugins/ (não é fonte, ver architecture.md §12)"*, commit `1f80b3b`), e o `graph.json` de hoje tem **zero** nós com `source_file` em `pi-plugins/` — o fan-in inflado que induzia a erro no ranking sumiu na raiz. ⚠️ **Mas o `manifest.json` do graphify ainda carrega as 106 entradas mortas** (A3): o corpus foi limpo, o índice não. E em 2026-07-31 as entradas mortas ganharam companhia — as do plugin de terceiro removido, morrendo pela mesma mecânica.
- **`~/.claude/plugins/`** — cache de instalação de plugin gerido pelo Claude Code; o `bootstrap` lê/sincroniza (`plugins/bootstrap/hooks/session-sync.sh`, `lib/apply.sh`, `lib/snapshot.sh`), mas nenhum dado de projeto mora lá. Reconstruído por `claude plugin install`. **103M** hoje, em **13** marketplaces — **8 nomeados** (`agent-browser`, `claude-hud`, `claude-plugins-official`, `obsidian-skills`, `openai-codex`, `pedro-plugins` com 19 plugins, `ponytail`, `voltagent-subagents`) e **5** `temp_git_*` [confirmado, `du -sh` + `ls` nesta rodada].
  ⚠️ **Contar pastas aqui dá número errado, e o erro é sempre pra CIMA — uma pasta por versão, todas convivendo.** Hoje `visual` tem **12** diretórios de versão e `project-doc` **9**. O caso que expôs isso: varrer `~/.claude/plugins/cache/*/*/*/hooks/hooks.json` procurando hooks de `Stop` devolve **28**; os ativos são **6**, um por plugin distinto (`handoff`, `intent-guard`, `project-doc`, `visual` do `pedro-plugins`, mais `security-guidance` e `codex` de marketplaces de terceiros). A pergunta *"quantos hooks de Stop eu tenho?"* só tem resposta certa por **plugin distinto**, nunca por arquivo em cache. Mesma família do erro de contar as chaves do `manifest.json` como "quantos arquivos" (A3). [confirmado nesta rodada]

---

## Resumo por natureza

⚠️ **Leia esta lista sabendo o que mudou em 2026-07-31:** até 2026-07-30, três das linhas abaixo traziam "protegido por git ✔". Hoje sobra **uma**. Não foi o dado que mudou de natureza — foi a garantia que saiu de baixo dele.

**Insubstituível (perder = perder conhecimento):**
- `.claude/.project-doc/findings.jsonl` — **desprotegido** ✗ (A1) — destrackeado em 2026-07-31, hoje ignorado por `.gitignore:35`. **898 eventos, 1,1M, zero cópias.**
- `.claude/ata/` — **desprotegido** ✗ (A6) — destrackeado em 2026-07-31, `.gitignore:38`. **30 arquivos, 1,8M, zero cópias.**
- `.claude/plans/*.plan.json` — **desprotegido** ✗ (A4) — destrackeado em 2026-07-31, `.gitignore:39`. **9 arquivos no disco, 92K; `git ls-files .claude/plans/` → 0.** É o que perde a prova junto com o plano.
- `.claude/HANDOFF*.md` — **desprotegido** ✗ — os **3** arquivos saíram do índice em 2026-07-31 (`.gitignore:40`). Insubstituíveis pelo mesmo motivo das atas: destilam sessões cujo transcript é local.
- `.claude/hook-contract.baseline.json` — **protegido por git ✔** (A5) — o único desta lista que ainda passa no teste [confirmado: `git ls-files .claude/hook-contract.baseline.json` devolve o arquivo nesta rodada]; o *julgamento* que ele carrega mora em `patterns.md §5.3`
- `.claude/intent/ledger.jsonl` — **desprotegido** ✗ (git-excluded local), **460 linhas**
- `.claude/intent/<auditoria>.escopo` — **desprotegido** ✗ e **não regenerável**: grava quem estava vivo no instante do bloqueio, e esse instante não volta. Perdê-lo não apaga conhecimento (o ledger e a auditoria continuam inteiros), mas **degrada a auditoria correspondente para o comportamento pré-v0.5.0** — ela volta a ser cobrada contra todos os vivos do momento da leitura, hoje **34 reprovações em vez de aprovação** (medido). Cobertura: `durability.md §3.14`
- `~/.claude/plans/` — **desprotegido** ✗ (do harness). ⚠️ **A consolação que este item trazia acabou:** dizia-se aqui que "o equivalente deste repo é a A4, versionada" — a A4 foi destrackeada em 2026-07-31 e hoje está tão desprotegida quanto. **213** arquivos, 2,7M, e **encolhendo**: eram 226 em 2026-07-26
- tags `archive/<branch>-<data>` — **protegidas** ✔ (A5b): **6 locais, 6 no remote** (`git ls-remote --tags origin | grep -c 'archive/'` medido nesta rodada; empurradas em 2026-07-30). ⚠️ Tag não sai em `git push` normal e o `cmd_prune` não empurra — a próxima nasce local. Cobertura: `durability.md §2.8`

**Reconstruível (custa tempo, não conhecimento):**
- `graphify-out/graph.json` — `graphify update . --force`, AST, segundos. Saiu do índice em 2026-07-31 (A3) — **e é o único destrack desta rodada sem consequência real**: o custo de perder é CPU, não conhecimento
- `.claude/.project-doc/ledger.json` — uma rodada de cold-start. Também saiu do índice em 2026-07-31 (A2), mesma leitura
- `graphify-out/.graphify_labels.json` — reconstruível **só com LLM** (`/graphify`); é o mais caro do grupo, **403 chaves** hoje. ⚠️ **Saiu do git junto com o diretório inteiro (`.gitignore:28`), e essa é a exceção dentro da exceção:** o resto de `graphify-out/` volta com um comando barato, este volta cobrando tokens
- `plugins/bootstrap/config/manifest.json` — **reconstruível só em PARTE** (A5c): as 3 chaves geradas voltam no próximo `SessionStart` a partir de `claude plugin list`; `skills.permitidas` e `ferramentas_externas` são escritas à mão e **não têm outra origem** — perdê-las é perder conhecimento, não tempo

**Descartável (cache / log / estado de UI):**
- `~/.claude/green-suite/` (TTL 24h + prune de 7d, self-managing — 48 arquivos)
- `~/.claude/guardrails/` (log, mode — hoje em `warn`, 3º valor do vocabulário desde 2026-07-30 —, streak, bypass do scope-cop + `askq.log`/`askq.count.*` do vigia da pergunta)
- `~/.claude/visual-state/` (280 arquivos, **sem prune**) — **menos o `config.json`**, que desde
  2026-07-28 mora ali e é preferência, não sessão (B2); um prune por idade teria que preservá-lo
- `$CLAUDE_CONFIG_DIR/state/prose-ceiling/` (contadores de 1 byte, **sem prune nenhum**; vazio agora — B8)
- `/tmp/claude-context-{pct,warned}-<session_id>` (prune de 1 dia)
- `.claude/visual/`, `.claude/qa-loop/`, `.claude/.project-doc/backups/`, `.claude/.project-doc/.run-*.json`

## Pendências

- ✅ **RESOLVIDO em 2026-07-31 — era o TODO dos 20M de `graphify-out/20*/` já tracked.** O `git rm -r --cached graphify-out/` que este item pedia foi dado, sobre o diretório inteiro: `git ls-files graphify-out/ | wc -l` → **0**, contra **40** que `HEAD = ff32947` ainda carrega. ⚠️ **O que ele NÃO resolveu, e o item fica registrado por isso:** o histórico não encolheu (`du -sh .git` → **37M**, `git count-objects -vH` → `size: 31.30 MiB`). Destrackear fecha a torneira; esvaziar a banheira exigiria reescrever a história — decisão que continua em aberto.
- [TODO: o preço do destrack — cinco depósitos (`graphify-out/`, `.claude/.project-doc/`, `.claude/ata/`, `.claude/plans/`, `.claude/HANDOFF*.md`) perderam a única cobertura que tinham e hoje existem só nesta máquina. **Quatro deles são insubstituíveis.** Decidir a rede de reposição: cópia agendada para fora da máquina, um segundo remote privado, ou registrar por escrito que a perda é aceita. Hoje não há nenhuma das três — ver `durability.md §3.15`]
- [TODO: `~/.claude/visual-state/` não tem prune e acumulou **280** arquivos desde abr/2026 (276 na rodada anterior, 255 na anterior a essa); o `green-cache.sh` tem `find -mtime +7 -delete`, o daemon não tem equivalente. ⚠️ Quando for escrito, o prune **tem que preservar `config.json`** — desde 2026-07-28 ele mora nesse mesmo diretório e é preferência do `/visual`, não estado de sessão (B2)]
- [TODO: `$CLAUDE_CONFIG_DIR/state/prose-ceiling/` acumula um arquivo de 1 byte por resposta reprovada e **nada o poda** — sem `find -mtime`, sem TTL, sem limpeza no `SessionStart`. O único `rm` que existe é uma sugestão em texto do `conformance.py`, e ela mira o `bypass.log`, não os contadores. A falta de backup já está justificada (`durability.md §3.13`); o que segue em aberto é o **prune**. Estado hoje: **0 arquivos** — mas o zero é prova do TODO, não do conserto, porque só um `rm` de fora do sistema poderia tê-lo produzido: 9 arquivos apareceram em 2h de uso e nenhuma linha de código os remove]
- [TODO: `~/.claude/plans/` **perdeu 13 arquivos** (226 → 213) entre 2026-07-26 e 2026-07-30 sem que nada neste repo escreva ou apague lá. Depósito insubstituível, sem backup, encolhendo sozinho — descobrir se o harness poda por idade e a partir de que janela]
- [TODO: o `.git` foi de 11M (2026-07-26) a **37M** (2026-07-31), com **32 blobs distintos de `graph.json`** somando **153.936.130** bytes brutos. Metade do TODO original foi decidida em 2026-07-31 — o grafo **deixou** de ser versionado —, mas isso só impede blob novo. **Continua em aberto o que fazer com os 32 que já entraram**: reescrever a história (`filter-repo`), aceitar o peso, ou rodar um `git gc --aggressive` que empacota mas não remove]
- [TODO: as 6 tags `archive/*` foram empurradas em 2026-07-30 (`git ls-remote --tags origin | grep -c 'archive/'` → **6**), mas à mão. Falta fazer o `cmd_prune` empurrar sozinho (`--follow-tags` ou push explícito depois de criar a tag) — sem isso a próxima branch apagada volta a nascer só neste clone. Ver `durability.md §2.8`]
- [TODO: confirmar quem escreve `.claude/ata/*.md` — não localizei o produtor nesta rodada]
- Reconciliado em 2026-07-31 (7ª vez): `.claude/CLAUDE.md` e este doc precisam citar os mesmos números — **3920 nós / 5039 arestas / 403 comunidades (30 nomeadas) / 60 god nodes (teto) / 12 hyperedges (6 sobrevivem ao filtro `hyper_min 0.85` do `graph_map.py`) / 14 edges INFERRED de 5039**, medidos por `graph_map.py --project-root .` + leitura direta do `graph.json`. Commit do build: **`ff329471`** (= `HEAD`), lido de *"Built from commit"* no `GRAPH_REPORT.md`. [confirmado neste run] ⚠️ **A queda em relação a 2026-07-30 (6797/7737/542) mede a remoção do plugin de terceiro, não uma regressão** — mesma classe da queda de 2026-07-28, quando `pi-plugins/` saiu do corpus.
  ⚠️ **`built_at_commit` NÃO existe dentro do `graph.json`** — as rodadas anteriores citavam esse nome de campo como se fosse chave do JSON; o `graph.json` só tem `hyperedges` no bloco `graph`. A procedência do build está no `GRAPH_REPORT.md`, seção *Graph Freshness*. Citar um campo que não existe é pior que citar um número velho: quem for conferir não acha.
- ⚠️ **Que esta reconciliação já esteja na 7ª vez é o sinal, não o conserto.** Os números mudam a cada `graphify update --force`, e **todo modo que escreve doc roda um** — então qualquer doc que cite a contagem nasce com prazo de validade de uma rodada. O que sobrevive é o **par número + `built_at_commit`**: com ele, quem lê sabe contra que estado o número valia e consegue re-medir. Número solto nesta doc é dívida, não fato.
- ⚠️ **"Quantos arquivos" tem TRÊS medidores que não concordam, e a doc citava o único inflado.** Até 2026-07-29 dizia-se **411 arquivos** — número que vinha de contar as chaves do `manifest.json`. Mas o manifest **retém entradas mortas**: das 416 chaves de hoje, **106 são de `pi-plugins/`**, gitignorado desde 2026-07-28 — e o grafo tem **zero** nós de lá. Os três medidores, re-lidos em 2026-07-31 com `HEAD = ff32947`: `manifest.json` **435** chaves (**329** fora de `pi-plugins/`) · `source_file` distinto nos nós **287** · `GRAPH_REPORT.md` **280 files**. **O número honesto é 287** — `source_file` distinto nos nós é o único que mede o que o grafo de fato cobre; citar a contagem do manifest é medir o índice, não o mapa. ⚠️ **O viés era estável e DEIXOU de ser, e é a limpeza que explica:** manifest−`source_file` era 112 em duas rodadas seguidas (422−310, 430−318) e saltou para **148** (435−287); `source_file`−report era 4 e virou 7. O manifest não só reteve as 106 entradas mortas de `pi-plugins/` como acrescentou as do plugin de terceiro removido — **cada limpeza no repo aumenta o erro desse medidor, porque ele conta o que já existiu**. Viés que muda com o tempo é o pior tipo: usar o medidor errado deixou de ter até uma correção fixa. ⚠️ Até 2026-07-30 este item dizia *"o número honesto é 304"* **na mesma frase em que declarava 305 como `source_file` distinto** — os dois não podiam estar certos juntos. Contradição interna dura mais que número velho, porque não dá pra saber qual metade confiar.
