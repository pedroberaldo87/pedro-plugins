---
generated: 2026-08-21
generated-commit: b7f4dd6
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
  - plugins/project-skills/lib/journal.py
  - plugins/project-skills/lib/graph_map.py
  - plugins/intent-guard/lib/ledger.py
  - _shared/green-cache.sh
  - plugins/visual/server/visual_server.mjs
  - plugins/project-skills/lib/plan_state.py
  - plugins/project-skills/lib/cobertura.py
  - .claude/suite-congela.baseline.json
  - .claude/fio-morto.baseline.json
  - .claude/custo-gatilho.baseline.json
  - .claude/desacoplamento.baseline.json
  - .claude/decisoes-seladas.md
  - plugins/project-skills/lib/decisoes_seladas.py
  - plugins/project-skills/lib/andamento.py
  - plugins/project-skills/hooks/posttooluse-andamento.sh
  - plugins/visual/lib/visual_page.py
  - plugins/project-skills/hooks/stop-plan-status.sh
  - plugins/handoff/skills/handoff/SKILL.md
  - scripts/hook_contract.py
  - plugins/branches/lib/branch_state.py
  - plugins/guardrails/hooks/scope-cop.sh
  - plugins/guardrails/hooks/askq-humanize.sh
  - plugins/context-guard/hooks/context-guard.sh
  - plugins/context-guard/hooks/context-guard-reset.sh
  - plugins/context-guard/hooks/context-guard-writer.sh
  - plugins/bootstrap/hooks/hooks.json
  - plugins/bootstrap/lib/conformance.py
  - plugins/project-skills/hooks/stop-doc-touch.sh
  - plugins/improve-workflow/lib/registro.py
  - plugins/improve-workflow/lib/medidor.py
  - plugins/improve-workflow/lib/plano_saida.py
verified-by:
  - plugins/project-skills/lib/test_plan_state.py
  - plugins/project-skills/lib/test_cobertura.py
  - plugins/visual/lib/test_visual_page.py
  - plugins/handoff/lib/test_handoff_skill.py
  - plugins/intent-guard/lib/test_ledger.py
  - plugins/branches/lib/test_branch_state.py
  - plugins/project-skills/lib/test_journal.py
  - plugins/project-skills/lib/test_graph_map.py
  - plugins/improve-workflow/lib/test_registro.py
  - plugins/improve-workflow/lib/test_medidor.py
  - plugins/improve-workflow/lib/test_plano_saida.py
doc-sig: pedro-plugins/.gitignore@gen=3.8#9089becd
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

E a região (C) é grande: cinco conjuntos que já foram rastreados vivem hoje só no disco. O `.claude/hook-contract.baseline.json` esteve nessa região e **voltou** — perdeu o campo `root` (o caminho absoluto da máquina que mediu), saiu do `.gitignore` e é rastreado. [confirmado: `git ls-files .claude/hook-contract.baseline.json` devolve o caminho, e `grep -c '/Users/'` no arquivo devolve 0]

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
1 · REGISTRO DE TRABALHO   .claude/ata/ · .claude/plans/ · .claude/specs/
                           .claude/vistoria/ · .claude/gauntlet/ · .claude/reports/
                           .claude/prints/ · .claude/HANDOFF*.md
                           .claude/RETOMAR-*.md · .claude/BRIEFING-*.md
                           .claude/.project-doc/ · .claude/intent/ · .claude/.sprint/
                           docs/superpowers/
2 · SEGREDO                scripts/public_repo_terms · .claude/secrets/ · .env · .env.*
                           *.pem · *.key · *.p12 · id_rsa* · .netrc
3 · RETRATO DESTA MÁQUINA  graphify-out/ · .claude/qa-loop/ · .claude/visual/
                           .playwright-mcp/
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

### A7 · `_shared/r8-tiers.json` — o contrato de tier virou DADO

- **Nasceu em 2026-08-03** (commit `5288bc5`). **JSON rastreado, 2.856 bytes.** [confirmado — `ls -la` + `git ls-files`]
- **Por que é depósito e não código:** é a fonte da verdade dos valores de esforço que os motores do `/sprint` (ex-`/sovai`) e do `/qa-loop` passam ao Workflow. Antes o número morava no texto das skills, e o próprio cabeçalho do módulo mede o estrago: *"trocar seis valores custou 45 substituições em dois SKILL.md, três saíram invertidas e duas sobreviveram a dois verificadores. A causa não era descuido — era o número morar em quinze lugares."* [confirmado, `_shared/r8_tiers.py`]
- **Sete chaves de topo** (`_comment`, `revised`, `model`, `api_default_effort`, `tiers`, `regra_por_rodada`, `fundamento`). O `tiers` é o coração: um objeto por etapa (`decompose`, `coordinate`, `executor`, `mechanical`, `diagnose`, …), cada um com `effort`, `etapa`, `quando` e **`porque`** — o motivo escrito ao lado do valor, que é a parte que nenhum literal em SKILL.md carregava. [confirmado, `json.load` nesta rodada]
- **Três consumos, todos lendo o mesmo arquivo** (`_shared/r8_tiers.py`): `args` monta o dicionário que a casca passa ao Workflow; `render` gera o `r8-tiers.md`; `check` falha se o markdown divergir do JSON **ou** se um `SKILL.md` voltar a carimbar um valor literal. Rodado nesta rodada: `OK: R8 servido de _shared/r8-tiers.json, sem cópia carimbada em SKILL.md`. [confirmado]
- **Quem cobra:** o check **E3** do `.claude/hooks/release-gate.sh` (linhas 83-89), que roda `r8_tiers.py check` e barra o commit com a mensagem *"o valor vive em `_shared/r8-tiers.json` e chega ao motor por args; o SKILL.md cita o KNOB, nunca o número"*. Isenção explícita: `r8-ok: <motivo>` na linha. [confirmado nos dois lados]
- ⚠️ **É vendorado, então tem as MESMAS armadilhas de `_shared/`:** `scripts/sync-shared.sh` copia o `.json` e o `.md` gerado para dentro do `project-skills` — as skills `sprint` (o antigo `/sovai`) e `qa-loop`, que se fundiram nele em 2026-08-09. A lista viva das cópias sai do índice, não daqui: `git ls-files | grep r8-tiers`. Editar a cópia em vez da fonte reintroduz exatamente o drift que o arquivo existe pra matar. [confirmado]
- **Natureza: fonte versionada, coberta pelo git.** Perder o arquivo é perder um arquivo do repo — volta com `git checkout`. O que **não** volta por comando é o `porque` de cada tier, que é julgamento escrito, não valor derivável.

### A8 · `.claude/limites-aceitos.md` — o registro do que a régua reprova e não vai ser consertado

- **Nasceu em 2026-08-03** (commit `1e59b55`). **Markdown rastreado, 2.091 bytes.** [confirmado — `git ls-files .claude/limites-aceitos.md`]
- **Por que existe, copiado do próprio arquivo:** *"Sem este arquivo o desacordo vira ou dívida esquecida ou conserto reflexo — os dois piores que a decisão registrada."*
- **Cada item traz quatro coisas:** o que a régua reprova, a data e o plano em que foi decidido, o **motivo** de não consertar, e o **comando de reconferência** com a saída daquele dia colada. Sem o comando, o limite vira folclore — ninguém sabe medir se ainda vale.
- **Dois itens hoje:** as **82 páginas** de `.claude/visual/` geradas antes da régua existir (ver a seção de (C) abaixo), e três geradores (`fallow/lib/report.py`, `slides/lib/md2deck.py`, `branches/lib/branch_state.py`) marcados em desacordo por **ausência de amostra no disco**, não por violação de forma.
- **Cada item declara o que o REVOGA**, não só o que o justifica. Para as 82 páginas: *"uma página antiga voltar a ser lida para decidir alguma coisa. Aí ela é regenerada, não lida como está."*
- **Natureza: julgamento escrito, coberto pelo git — e insubstituível dentro disso.** O número de violações é remedível por um comando; a **decisão de aceitá-las** não sai de lugar nenhum além deste arquivo. É a mesma classe do "julgamento embutido" dos baselines A5/A5a, com a diferença de que aqui o julgamento é o arquivo inteiro, não um metadado dele.
- ⚠️ **Nenhum verificador o lê.** Diferente do A5, cujo baseline o release-gate compara, este arquivo é lido por humano. Um limite que deixou de valer não é acusado por ninguém — quem revoga é quem lembra.

### A9 · `docs/fluxos/` — o diagrama como DOCUMENTO, dentro do clone

- **Nasceu em 2026-08-16.** Hoje **1 arquivo rastreado, 512K** — o número sai do comando, nunca daqui: `git ls-files docs/fluxos/ | wc -l` e `du -sh docs/fluxos/` (a doc desceu para `docs/` na raiz em 2026-08-20; o número foi remedido lá). [confirmado nesta rodada]
- **Por que é depósito e não artefato de sessão:** até aqui todo desenho nascia em `.claude/archify/`, que é pasta de sessão como `.claude/visual/` — e desenho que mora em pasta de sessão morre no `/clear` sem ninguém notar. A decisão do dono (2026-08-13) foi promover fluxo, arquitetura e desenho de módulo a **documento versionado**: nascem aqui, entram no commit de conteúdo, e defasam junto com o texto.
- **Quem escreve:** o passo 2b do `/doc-touch` (`plugins/project-skills/skills/doc-touch/SKILL.md`), que re-renderiza pelo `archify` a camada de todo doc re-projetado — `architecture.md` puxa o `organismo.html`, `runtime.md` puxa os `fluxo-<slug>.html`, doc de módulo puxa o `app-<nome>.html`. Os três dividem **esta** casa; um destino só evita que o mesmo tipo de artefato viva em duas pastas. [confirmado — `plugins/project-skills/lib/test_doc_touch_skill.py`]
- ⚠️ **É rastreado, então vale a regra do repositório público:** HTML com caminho absoluto de máquina dentro é reprovado pela checagem H do gate de commit (`scripts/public_repo_check.py`).
- **Natureza: derivado, e por isso remediável** — sai de novo do doc curado a cada touch. O que não se recupera é o **doc que o originou**, não o desenho.

### A10 · `docs/prototipo/` — a lei do sidecar e a casa do protótipo aprovado

- **Hoje 1 arquivo rastreado** (`git ls-files docs/prototipo/` devolve `FORMATO.md` — casa nova desde a descida da doc para `docs/`); os HTMLs do protótipo e os `<etapa>.prototipo.md` entram aqui quando um projeto tem interface aprovada.
- **`FORMATO.md` é a parte NORMATIVA**, e mora dentro do que o clone recebe **porque o cobrador a lê em qualquer máquina** (`plugins/project-skills/lib/test_sidecar_prototipo.py`). A spec de concepção discute o porquê; aqui está a lei.
- **O sidecar é ANEXO, não régua** — `plugins/project-skills/lib/doc_load.py:le_anexos` o lê fora da lista que julga obra, e a marca do CONJUNTO (`conjunto-sig`) reabre o anexo quando alguém mexe no protótipo depois do de acordo.
- **Natureza: acordo com o dono, sob tranca.** O corpo aprovado não se toca sem novo de acordo — o que se grava é `correcao-pendente:` no frontmatter, que não reabre a etapa.

### A12 · `.claude/decisoes-seladas.md` — a decisão do dono que mata a pergunta repetida

- **Nasceu em 2026-08-20**, com `plugins/project-skills/lib/decisoes_seladas.py`. **Markdown rastreado quando existe** — não está no `.gitignore`, e o próprio módulo declara por quê: *"é doc: entra no commit"*. **Neste repositório o arquivo já existe e está POVOADO** — `grep -c '^- \[' .claude/decisoes-seladas.md` → **34** linhas seladas, todas da corrida de agosto/2026: o mecanismo está de pé e o registro é usado. [confirmado nesta rodada]
- **Uma linha por decisão**, no formato `- [data] "fala literal do dono" — fonte: <onde foi dita>`. A frase-chave mora **inteira numa linha só** — partida em duas, o `grep` não a acha, e foi assim que a mesma pergunta parou quatro corridas em dias diferentes com a resposta já dita.
- **Quem lê e escreve é um programa, nunca prosa:** `decisoes_seladas.py consultar <raiz> "<pergunta>"` devolve as linhas que já respondem (saída **1** = nenhuma cobre, e aí a pergunta segue ao dono) e `selar <raiz> --fala … --fonte …` grava a resposta nova **na mesma volta** em que ela é dada. O casamento é por frase inteira ou por radical de 4 letras, para que a pergunta reescrita ache a mesma decisão.
- **Quem manda consultar** é a régua única `_shared/regua-de-pergunta.md`, vendorada ao lado de cada skill que pergunta (nove cópias hoje) — o pré-check de largada, o motor do `/sprint` e a casca consultam **antes** de levar qualquer coisa ao dono.
- **Natureza: acordo com o dono, coberto pelo git.** É a mesma classe do A8 (`limites-aceitos.md`): o que se perde ao apagá-lo não é dado remedível por comando, é a fala de quem decidiu. **Registro ausente não trava nada** — sem arquivo a consulta devolve vazio e a pergunta segue; é o caminho fail-open, que neste repo já não é o exercitado.
- ⚠️ **Ninguém cobra que a decisão seja SELADA.** `test_decisoes_seladas.py` (20 ok nesta rodada) cobra o módulo e o texto da régua; que um papel tenha de fato gravado a fala do dono depois de perguntar, nada verifica — a mesma dívida declarada do A8.

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
  scope-cop.sh:51      HOOK_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/guardrails"
  askq-humanize.sh:58  HOOK_DIR="$HOME/.claude/guardrails"
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
- **O `state` ganhou a nota da própria página em 2026-08-08**, e ela viaja pelo mesmo `POST /state`: `state.qualidade = {votos: {clareza|escaneabilidade|detalhamento: "bom"|"ok"|"ruim"}, livre: "<texto>"}`. É opcional e nasce vazia — nenhum voto é obrigatório, porque caixa que exige voto vira clique automático. **O daemon não tem lista de campos permitidos**, então o campo novo não exigiu mexer nele: ele grava o objeto `state` inteiro como veio. [confirmado — `visual_server.mjs` e o `saveState` do `template.html`]
- **Hóspedes que não são do daemon, e são DOIS.** [confirmado]
  - `config.json` (173 bytes) — a preferência do `/visual` (`auto_mode` + os `auto_triggers`), escrita pela **skill**. Semente versionada em `plugins/visual/skills/visual/config.default.json`.
  - `licoes-clareza.json` — o banco de regras de escrita das páginas, escrito por `plugins/visual/lib/clareza.py` (`registrar`) e lido por ele (`licoes`, `check`) e pelo `visual_page.py` (que **recusa** a página com termo já reprovado). O caminho sai de `clareza.py:BANCO`, sobre `STATE_DIR = ${CLAUDE_CONFIG_DIR:-~/.claude}/visual-state` — este hóspede **respeita** a env var, ao contrário do daemon que é dono da pasta. Quantas regras há agora:

    ```bash
    python3 -c "import json,os;print(len(json.load(open(os.path.expanduser('~/.claude/visual-state/licoes-clareza.json')))['licoes']))"
    ```

    As de fábrica moram no código (`clareza.py:SEMENTE`) e voltam sozinhas; as demais, não. Os dois hóspedes moram aqui pelo mesmo motivo: `${CLAUDE_PLUGIN_ROOT}` é cache reescrito a cada bump, e lição perdida no bump é o mesmo que lição nenhuma.
- **Volume:** 1,8M, **394 entradas** (`ls ~/.claude/visual-state | wc -l`), incluindo um `.daemon.log` e arquivos de teste (`test-live-abc123.json`, `test-session-abc123.json`). **Não há prune.** [confirmado]
- **Natureza: descartável**, com duas exceções de grau — `config.json` é preferência e `licoes-clareza.json` é **conhecimento acumulado que não se regenera** (cada lição custou uma reprovação real de um leitor). Nenhum dos dois deve entrar num eventual prune por idade.

### B3 · `~/.claude/green-suite/` — 140K · cache de "suite verde"

- **Escrito por** `_shared/green-cache.sh` (fonte-da-verdade) e suas cópias vendoradas em `plugins/ship/hooks/` e `plugins/project-skills/lib/` (a cópia era do `qa-loop`, que se fundiu no `project-skills` em 2026-08-09). Função `green_cache_mark`.
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

🔴 **REMOVIDO em 2026-08-09, a pedido do dono.** Os três hooks de `Stop` do `bootstrap` (`stop-prose-ceiling.py`, `stop-forma-relato.py`, `stop-regua-relato.py`) saíram do disco e o array `Stop` do `hooks.json` deixou de existir [confirmado — `git show 251d6ac --stat` e `python3 -c "import json; print(list(json.load(open('plugins/bootstrap/hooks/hooks.json'))['hooks']))"` → `['SessionStart', 'PostToolUse']`]. O que segue é HISTÓRICO: descreve o que existiu, não o que roda. O estado em disco que eles escreviam continua lá e ninguém mais o lê.

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

🔴 **REMOVIDO em 2026-08-09, a pedido do dono.** Os três hooks de `Stop` do `bootstrap` (`stop-prose-ceiling.py`, `stop-forma-relato.py`, `stop-regua-relato.py`) saíram do disco e o array `Stop` do `hooks.json` deixou de existir [confirmado — `git show 251d6ac --stat` e `python3 -c "import json; print(list(json.load(open('plugins/bootstrap/hooks/hooks.json'))['hooks']))"` → `['SessionStart', 'PostToolUse']`]. O que segue é HISTÓRICO: descreve o que existiu, não o que roda. O estado em disco que eles escreviam continua lá e ninguém mais o lê.

Depósito **novo nesta rodada**, irmão do B8 e deliberadamente diferente dele: o teto de prosa é mecânico, roda todo turno e custa zero token; **este chama um modelo**, então só roda quando a resposta é um RELATO.

- **Escrito por** `plugins/bootstrap/hooks/stop-forma-relato.py`. O caminho tem **variável própria**, e o motivo está no comentário: [confirmado]

  ```python
  CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
  # estado com var propria: isolar o teste via CLAUDE_CONFIG_DIR tirava a credencial
  # do `claude -p` junto, e o juiz passava a aprovar tudo por fail-open.
  ESTADO = Path(os.environ.get("FORMA_RELATO_STATE", CLAUDE_DIR / "state" / "forma-relato"))
  ```
- **O gatilho tem duas partes.** Primeiro `usou_visual()`: o turno precisa ter passado pelo `/visual` (skill, comando, ou escrita em `.claude/visual/`), senão sai na batida `sem /visual no turno` sem gastar modelo. Depois `e_relato()`: pelo menos um bloco ` ``` ` **e** ≥ `MIN_PROSA = 2` linhas de prosa fora dos blocos. A primeira parte entrou porque o juiz estava rodando em todo fim de turno — 463 julgamentos em 9 dias, ~25s e US$ 0,0416 cada.
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

### B11 · o interruptor da missão e a reserva — fundidos em `~/.claude/andamento/` (a casa antiga foi removida no rename de 2026-08-09)

- **Nasceu em 2026-08-02**, com o gate que mantém a missão autônoma no motor Workflow. **O plugin que a batizou não existe mais:** `sovai`, `qa-loop` e `project-doc` se fundiram no `project-skills` em 2026-08-09, e a skill de missão passou a se chamar `sprint`. **No rename de 2026-08-09 a pasta também mudou: tudo mora em `~/.claude/andamento/`** — quem a escreve mora em `plugins/project-skills/hooks/`. [confirmado — `plugins/` e `.claude-plugin/marketplace.json` não têm mais nenhum dos três]
- 🔴 **Em 2026-08-09 as duas casas viraram UMA:** interruptor, reserva e memória de andamento nascem todos em `~/.claude/andamento/`. A casa com o nome do plugin extinto foi removida do disco e do código no mesmo rename — não há mais cascata de leitura nem cópia velha para restaurar por engano.
- **O que AINDA nasce aqui** [confirmado — `plugins/project-skills/hooks/pretooluse-motor-arma.sh` e `reserva-de-arquivos.sh`, os dois resolvem `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/andamento`]:
  - `ativo-<session_id>` — **o que importa é existir.** Aceso pela casca da skill antes de disparar o Workflow, apagado na entrega. Enquanto existe, todo disparo de sub-agente naquela sessão é negado — e é o mesmo sinal que `pretooluse-espera-com-guarda.sh` consulta pra saber se o dono está ausente. Expira por idade (`SPRINT_TTL_MIN`, 12h), e a expiração vira linha em `expirados.log`.
    🔴 **A expiração era PASSIVA e por isso não alcançava quem mais precisava.** Quem a disparava era o gate do motor, no `pretooluse` — ou seja, só quando alguém da própria sessão consultava. **Sessão que morre nunca mais consulta**, e o sinal dela ficava para sempre: medido em 2026-08-10, **cinco sinais órfãos vivos ao mesmo tempo, o mais velho de 75 horas**, todos anunciando "missão de pé" na barra de qualquer projeto. Desde então a varredura também roda em **`andamento.py:expira_sinais`**, chamada de dentro do `linha_motor` — a barra é o único processo com frequência garantida em toda sessão viva, inclusive nas que não têm motor. Ela apaga o **conjunto** (`ativo-`, `bloqueios-`, `onda-`, `placar-`, `doc-`, `sinal-`, `trabalho-`, `motorid-`), porque estado sem dono reaparece na barra de quem reusar o id, e registra o autor `barra` no `expirados.log`. [confirmado — os cinco morreram na primeira leitura; `expira_sinais` tem seis checagens em `test_andamento.py`]
    O par de acender/apagar também virou **comando** — `andamento.py encerra <sid>` —, e ele é chamado de três lugares: o motor (papel `encerra:barra`, antes do `return`), a casca (passo 3 da persistência) e, por idade, a barra.
    🔴 **O sinal é por SESSÃO e a reserva é por sessão E MOTOR — a assimetria apagava missão viva (2026-08-12).** O `encerra` conferia só o **dono** (`sprint`/`qa-loop`/`gauntlet`, linha 1 do arquivo), então dois motores do MESMO dono na mesma sessão eram indistinguíveis: o primeiro a terminar apagava o sinal do segundo, que seguia rodando. Medido nesta sessão — um motor morreu na largada por porta fechada, o relançamento herdou a sessão, e a barra ficou muda com trabalho de pé enquanto o gate que nega despacho por fora desarmava junto. Conserto em `andamento.py`: `arma <sid> <dono> <motor>` grava a lista de quem está de pé em `motorid-<sid>` (uma linha `dono\tmotor` por motor), e `encerra <sid> <dono> <motor>` **só derruba o sinal quando não sobra ninguém**. [confirmado — `test_andamento.py` cobre os dois lados; com o `encerra` de antes a mesma suíte sai `FALHOU: 3`]
  - `motorid-<session_id>` — **quem está de pé nesta sessão**, uma linha `dono\tmotor` por motor vivo. ⚠️ **Ele era apagado em dois lugares (`expira_sinais` e `encerra`) e NUNCA era escrito por ninguém** — o desenho previa o registro desde 2026-08-09 e a implementação não veio, que é exatamente o que deixou a assimetria acima passar. Escrito por `andamento.py:arma` desde 2026-08-12. [confirmado — `grep -rn motorid plugins/project-skills/ | grep -v /test_` devolvia só as duas linhas que apagavam]
  - `onda-<session_id>` — **onde a missão está**: a rodada, e desde 2026-08-10 também o **bloco** e a **etapa** dentro dela (`{"rodada": 2, "bloco": 3, "etapa": "executando"}`). Sai na barra como `🌊 Onda 2 bloco 3 · executando`. Os dois campos novos são opcionais — quem só registra a rodada continua saindo como antes. Nasceram porque uma onda de três blocos deixava a barra quinze minutos no mesmo texto, e quem olha não sabia se avançou ou travou.
  - `bloqueios-<session_id>` — o contador do cap (3). Sanitizado na leitura: lixo no arquivo vira `0`, nunca erro de shell.
  - `desistencias.log` — append-only, uma linha por vez que o cap estourou. Existe porque *desistir em silêncio* é o defeito que o `bypass.log` do teto de prosa registrou primeiro.
  - `reservas/<session_id>__<motor_id>.files` — a lista de arquivos que um motor reservou antes de soltar executor. **O escritor mudou de casa nesta rodada** (`plugins/sovai/hooks/reserva-de-arquivos.sh` → `plugins/project-skills/hooks/reserva-de-arquivos.sh`); **o depósito, não** — mora em `~/.claude/andamento/reservas/`. Dois motores da mesma sessão no mesmo arquivo é um apagando o trabalho do outro. ⚠️ **Reserva não liberada recusa o motor seguinte**, e foi assim que uma rodada morreu antes de executar qualquer passo em 2026-08-08: o `liberar` falhou com `fork failed` e os 54 caminhos ficaram presos. Diagnóstico: `ls ~/.claude/andamento/reservas/`.
- ⚠️ **`ativo-<sid>` tem HOJE duas casas, e quem escreve decide qual** [confirmado — `grep -rn 'ativo-\$SESSION' plugins/*/hooks/*.sh`]: `pretooluse-motor-arma.sh` (project-skills) usa esta pasta; `pretooluse-gauntlet.sh` (gauntlet) usa `~/.claude/andamento/`, e distingue de quem é a missão pelo **nome do motor escrito dentro do arquivo**. `andamento.py:painel` varre as **duas** bases (`bases = [ESTADO, ESTADO_LEGADO]`) justamente por isso. Quem só olhar uma pasta conclui "nenhuma missão de pé" com uma missão de pé.
- **O que só é LIDO daqui** — `duracoes-*.json`, `placar-*`, `sinal-*`, `trabalho-*`. A cascata está em `andamento.py:_ler`: procura na casa nova, cai na antiga quando ela não tem, e **nunca escreve** na antiga. O hook faz o mesmo com o `sinal-*`, copiando o legado pra casa nova na primeira passagem. Missão que já estava de pé quando a pasta mudou não perde a memória.
- **Por sessão, nunca global** — mesma lição do `context-guard` e do `scope-cop` (§1.5 de `patterns.md`): marcador global faria uma sessão em missão tirar de **todas** as outras o direito de despachar sub-agente.
- **Perder o diretório não perde trabalho.** É interruptor, não registro: some o `ativo-*` e o gate volta a ser mudo. O único conteúdo com valor histórico é o `desistencias.log`, e ele é diagnóstico, não dado.
- ⚠️ **O risco real é o oposto: o arquivo ficar aceso.** A casca apaga na entrega, mas missão interrompida no meio (sessão morta, `/clear`) deixa o sinal aceso e **a sessão inteira segue sem despachar sub-agente**, sem ninguém saber por quê. Não há poda por idade — diferente do `scope-cop`, que ganhou `find … -mtime +1 -delete` no mesmo commit em que nasceu. Diagnóstico: `ls ~/.claude/andamento/`.
- **Como medir o estado agora** — o número sai do comando, nunca de uma contagem escrita aqui:

  ```bash
  du -sh ~/.claude/andamento
  ls -1 ~/.claude/andamento                    # `ativo-*` mora aqui, e só aqui
  ls -1 ~/.claude/andamento/reservas 2>/dev/null  # vazio é o normal; cheio trava o próximo motor
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

### B13 · `${CLAUDE_CONFIG_DIR:-~/.claude}/andamento/` — a memória de quanto cada comando demora, e o estado vivo da missão

- **Nasceu em 2026-08-08** com `plugins/project-skills/lib/andamento.py` + o gancho de andamento (runtime, fluxo 19). **O gancho mudou de casa em 2026-08-09**, junto com a fusão dos três plugins: `plugins/sovai/hooks/posttooluse-andamento.sh` → **`plugins/project-skills/hooks/posttooluse-andamento.sh`**. O depósito não se mexeu.
- ⚠️ **A pasta é NEUTRA, e isso é decisão, não descuido.** O comentário do módulo diz por quê: *"Quatro plugins já chamam este módulo; a pasta batizada com o nome de um deles fazia o estado dos outros parecer emprestado."*
- 🔴 **Em 2026-08-09 ela virou a casa de TUDO — a única.** O degrau de leitura da casa antiga saiu de `andamento.py` no rename [confirmado, `andamento.py:_ler`]:

  ```python
  ESTADO        = os.path.join(_CONFIG, "andamento")   # o que NASCE vai pra ca
  # (o degrau ESTADO_LEGADO foi removido no rename de 2026-08-09: a casa e uma so)
  ```

  `_ler(base, nome)` procura na casa nova e só cai na antiga quando a nova não tem o arquivo — e **só para a casa padrão**: quem passa `dir_estado` (a bancada de teste, ou um motor com casa própria) está dizendo exatamente onde olhar, e aí não há legado que valha.
- **Cada tipo de arquivo tem natureza própria** — a lista de naturezas de uma máquina viva sai do disco, nunca de um número escrito aqui [confirmado — `ls ~/.claude/andamento/ | sed 's/-[^-]*$//' | sort -u`]:
  - **`duracoes-<caminho-do-projeto-com-hifens>.json`** — o ativo de verdade. Dicionário `comando → [duração, duração, …]`. É a memória que faz a estimativa existir: comando sem histórico aqui sai **sem** número, e é o acúmulo que muda isso. Tamanho e nº de chaves saem do comando, nunca de um número escrito aqui:

    ```bash
    ls -la ~/.claude/andamento/duracoes-*.json
    python3 -c "import json,glob;print({f.split('duracoes-')[1][:40]: len(json.load(open(f))) for f in glob.glob('$HOME/.claude/andamento/duracoes-*.json')})"
    ```
  - **`ativo-<session_id>`** — o sinal da missão de pé. **Nasce aqui só quando o motor é o `gauntlet`** (`plugins/gauntlet/hooks/pretooluse-gauntlet.sh`); o motor do `sprint` acende o dele em `~/.claude/andamento/` (B11). O arquivo **deixou de ser vazio**: a primeira linha traz o **nome do motor**, porque a casa é compartilhada e a negação de um motor não pode sair com a mensagem do outro. ⚠️ **Em 2026-08-09 o motor do `sprint` passou a gravar o nome dele também**: sinal vazio não é motor anônimo — cai no rótulo de fallback de `andamento.py:_motor`, e por isso a barra de status nomeou `sovai` toda missão desta skill meses depois de o plugin ter sido fundido. O fallback deixou de ser o nome de um plugin. ⚠️ **Acender com `printf` direto no arquivo está APOSENTADO desde 2026-08-12**: quem acende é `andamento.py arma <sid> <dono> <motor>`, que grava a mesma primeira linha **e** registra o motor em `motorid-<sid>` (B11) — sem esse registro o `encerra` do primeiro motor apagava o sinal de outro motor vivo da mesma sessão. [confirmado — `skills/sprint/SKILL.md` (seção da armação, que proíbe o `printf`), `andamento.py:arma` e `andamento.py:MOTOR_PADRAO`]
  - **`sinal-<session_id>`** — o instante da última fala do narrador, que a barra de status lê pra dizer *"rodando há N min"* e *"sem avanço"*. O gancho **copia o do legado** na primeira passagem (`cp "$ESTADO_ANTIGO/sinal-$SESSION" "$SINAL"`), pra missão que já estava de pé não perder o relógio.
  - **`trabalho-<session_id>`** — o disparo que quem executa gravou: **três linhas**, o instante, o comando e o projeto. Existir já quer dizer *"tem comando rodando agora"* — por isso o gancho o apaga **antes de qualquer saída antecipada**, nas duas pastas: registro esquecido faz a barra dizer "rodando" para sempre. Os dois últimos campos existem porque `estimativa()` só responde por comando **E** projeto, e a barra é desenhada por outro processo, que não sabe nenhum dos dois. Formato antigo (só o carimbo) degrada pra relógio sem estimativa, não pra erro.
  - **`placar-<session_id>`** — efêmero, por sessão. Guarda o último placar lido da suíte (`{"placar": {...}, "linha": "..."}`) pra responder "andou ou não andou" no turno seguinte.
  - **`onda-<session_id>` — NOVO em 2026-08-09: onde a missão está, não só há quanto tempo ela existe.** JSON de até três chaves — `{"rodada": <r>, "feitos": <n>, "total": <n>}` —, escrito por `andamento.py:marca_onda` e lido por `andamento.py:linha_onda`, que devolve `onda 5 · 216/223` para a barra. **Quem grava é o papel de marcação do motor**, com um comando ao fim da lista de `tick` (`andamento.py onda <sessionId> <rodada> <planPath>`, contrato em `skills/sprint/SKILL.md`). ⚠️ **O par feitos/total é contado pelo PROGRAMA**, que abre o `.plan.json` e conta `status == "done"` — pedir a conta ao agente que acabou de marcar é o mesmo defeito do placar de suíte que o motor descartava. Plano ausente ou ilegível tira o par e mantém a rodada; sem `rodada`, `linha_onda` devolve `None` e a barra fica como era. [confirmado — `grep -rn 'andamento.py onda' plugins/` e 6 checks em `test_andamento.py`]
  - **`doc-<session_id>` — NOVO nesta rodada: a PROVA de que a doc do commit saiu da onda.** JSON de três chaves — `{"round": <rodada>, "docs": [<caminho>, …], "quando": <epoch>}` —, escrito por `plugins/project-skills/lib/andamento.py:doc_da_onda` e lido por `andamento.py:ultima_doc`. **Quem grava é o papel de doc do motor**: a `SKILL.md` da `sprint` manda o `docTouchPrompt` rodar `python3 <raiz do project-skills>/lib/andamento.py doc <sessionId> <rodada> <caminho...>` depois do touch, com cada caminho conferido no disco antes de entrar na lista. Costura verificada nos dois lados. [confirmado — `grep -rn 'andamento.py doc' plugins/`]
    - **Por que virou arquivo:** a lista confirmada pelo papel de doc só vivia na memória do motor (`rounds[].doc`), e *"terminada a missão, não sobrava como provar que a doc do commit seguinte saiu da onda e não de uma passada manual"* [confirmado, docstring].
    - **Mesmo desenho do `placar-<sid>`:** mesma pasta, mesma chave por sessão, mesmo fail-open — `except OSError: pass`, porque *"o commit da rodada já está feito quando este papel roda"*. Lista vazia não escreve arquivo nenhum. **Nenhum `doc-*` existe no disco hoje** (`ls ~/.claude/andamento/`). [confirmado]
  - `bloqueios-<session_id>`, `desistencias.log` e `expirados.log` também nascem aqui quando o motor é o `gauntlet` — os mesmos três nomes que o motor do `sprint` escreve em `~/.claude/andamento/`.
- 🔴 **A duração é o único depósito deste repositório cujo VALOR cresce com o tempo e não é reconstruível.** Todo o resto do inventário ou é regenerável por comando (grafo, baselines) ou é registro de um evento passado (atas, journal). Aqui não: a mediana de uma suíte só existe porque aquela suíte rodou 40 vezes nesta máquina. Apagar o arquivo não quebra nada — o narrador volta a sair sem estimativa —, mas a memória recomeça do zero e leva semanas de uso para voltar.
- ⚠️ **A chave é o comando LITERAL, aspas e quebras de linha inclusive** [confirmado — as chaves lidas do arquivo são o texto cru do Bash]. Consequência: a mesma suíte chamada com um espaço a mais é outro comando, e herda estimativa nenhuma.
- **Chaveamento por projeto está no NOME do arquivo**, não numa chave interna — o caminho do projeto vira sufixo com barras trocadas por hífen. Dois projetos não se contaminam.
- **Sem cobertura de backup**, como todo o bloco (B).

### B14 · `${CLAUDE_CONFIG_DIR:-~/.claude}/improve-workflow/` — o histórico das autópsias, e o run que elas leem

- **Nasceu em 2026-08-09** com o plugin `improve-workflow`. O caminho sai de `plugins/improve-workflow/lib/registro.py:caminho`, e ele **respeita a env var** (`CLAUDE_CONFIG_DIR` antes de `~/.claude`) — diferente do `visual-state` (B2) e do `vision.json` (B12), que fixam o `~`.
- **Por que fora do projeto, e não dentro dele:** a docstring do módulo dá o motivo, e ele não é conveniência — *"NUNCA dentro do projeto: escrever no projeto quebraria a proibição que impede esta skill de mexer na árvore que ela audita"*. A skill investiga e propõe; escrever no repositório auditado é exatamente o que ela não pode fazer.
- **Dois arquivos, e só um existe hoje:**
  - `registro.jsonl` — **append-only, uma linha por run medido**, escrita por `registro.py:gravar` (invocada pelo passo `registro.py gravar` da `skills/improve-workflow/SKILL.md`). O que a linha guarda são **só números**: as chaves lidas do arquivo real são `run`, `quando`, `total`, `papeis`, `sinais` e `consertos` — nenhum trecho de transcript entra aqui. [confirmado — as chaves saíram do arquivo, não do código]

    ```bash
    wc -l < ~/.claude/improve-workflow/registro.jsonl
    python3 -c "import json,os;p=os.path.expanduser('~/.claude/improve-workflow/registro.jsonl');\
    [print(json.loads(l)['run'], json.loads(l)['quando'], [x['papel'] for x in json.loads(l)['papeis']]) for l in open(p)]"
    ```
  - `mode` — o kill-switch, mesmo desenho de todo automatismo da casa: `off` escrito ali cala o medidor (`medidor.py:desligado`). **Não existe no disco** (`ls ~/.claude/improve-workflow/mode` → ausente), e ausência quer dizer ligado. A chave mora aqui, e não no plugin, pelo motivo de sempre: `${CLAUDE_PLUGIN_ROOT}` é cache reescrito a cada bump, e chave lá dentro voltaria a ligar sozinha na atualização seguinte.
- **Poda por contagem, não por idade:** `RETENCAO = 50` em `registro.py` — a gravação apaga o que passar das 50 rodadas mais novas (`registro.py:podar`). O comentário diz por quê: *"rodada de meio de ano não responde nenhuma pergunta e o arquivo cresce para sempre"*.
- ⚠️ **A poda reescreve o arquivo sem atomicidade** — `open(caminho, "w")` direto, sem o `.tmp` + `os.replace` que o `plan_state.py:save` usa (A4). Interrupção no meio da reescrita trunca o histórico. O amortecedor existe do lado da leitura, não da escrita: `registro.py:ler` pula linha que não é JSON (*"histórico truncado vale mais que nenhum"*). [confirmado nos dois pontos]
- **Para que serve guardar:** é o único lado "antes" da pergunta que a rodada seguinte faz — *o conserto que eu apliquei melhorou o número que ele mirava?*. `registro.py:anterior` devolve a última rodada que não é esta, e `registro.py:veredito` compara métrica a métrica (`melhorou` · `piorou` · `igual` · `sem_medida`). Sem o arquivo, a resposta volta a ser palpite de uma amostra só.
- **A matéria-prima NÃO mora aqui — é o transcript do harness, e ele é só de leitura.** `medidor.py:_base_runs` aponta para `${CLAUDE_CONFIG_DIR:-~/.claude}/projects`, e `runs_conhecidos` varre `<projeto>/<sessão>/subagents/workflows/<runId>/`, onde ficam um `agent-<id>.jsonl` por agente e o `journal.jsonl` do motor. ⚠️ **A varredura é presa a ESTE projeto desde 2026-08-15** — `medidor.py:projeto_atual` reconstrói o nome da pasta a partir do caminho absoluto do repositório (tudo que não é letra nem número vira `-`), e sem argumento o medidor pega o run mais recente **dessa** pasta, não do disco inteiro; id de run que só existe na pasta de outro projeto é **recusado**, nomeando o dono. O defeito que fechou: o mais recente do disco era de outra missão, e a autópsia falava de arquivos que não existem aqui. [confirmado — `runs_conhecidos`/`resolver_run` e `test_medidor.py`] **Nenhum plugin deste repositório escreve nesse caminho** — quem o escreve é o harness. Volume e quantidade saem do comando:

  ```bash
  ls -d ~/.claude/projects/*/*/subagents/workflows/*/ | wc -l
  du -sh ~/.claude/projects
  ```

  ⚠️ **É o maior depósito de (B) por ordens de grandeza, e é dele que a autópsia depende inteira.** Run apagado (rotação do harness, `/clear` de máquina limpa) não é remedível: o `registro.jsonl` guarda os números daquele run, nunca o transcript que os produziu.
- **O papel de cada agente é DADO no transcript, não inferência** — e a costura existe nos dois lados: o motor escreve `PAPEL: <NOME>` como primeira linha de todo prompt (`plugins/project-skills/skills/sprint/SKILL.md`, seção *"TODO prompt do motor ABRE declarando o papel"*) e o medidor a lê em `medidor.py:_DECLARADO` (`re.compile(r"PAPEL:\s*([A-Z][A-Z0-9_]{2,})")`). Os marcadores por frase continuam no código como **resgate de run antigo**, não como caminho principal: enquanto o papel era adivinhado pela prosa, reescrever o texto do motor fazia a tabela inteira virar `DESCONHECIDO` sem nada acusar. [confirmado nos dois arquivos]
- ⚠️ **O plugin nasce DESLIGADO de fábrica** — `{"name": "improve-workflow", "enabled": false}` em `plugins/bootstrap/config/manifest.json`. Numa instalação padrão a pasta nunca aparece; ela só existe em máquina que ligou o plugin à mão. Quem procurar o depósito para diagnosticar e não achar nada, ache primeiro a chave.
- **Natureza: histórico acumulado, reconstruível enquanto o run sobreviver** — remedir os runs ainda no disco regenera as linhas; run já rotacionado, não. **Sem cobertura de backup**, como todo o bloco (B).

### B12 · `~/.claude/vision.json` — o endpoint do servidor de visão

- **Nasceu em 2026-08-03** com o plugin `vision` (commit `4a4b59d`, v0.1.0). **112 bytes**, um arquivo único. [confirmado — `ls -la` + conteúdo lido]
- **Escrito à mão por quem instala — o plugin só lê.** `plugins/vision/vision_mcp.py:26` fixa `CONFIG_PATH = os.path.expanduser("~/.claude/vision.json")`, e `_config()` o consulta como **segunda fonte**: as env vars `QWEN_BASE`/`QWEN_MODEL`/`QWEN_TIMEOUT` vêm primeiro; o arquivo preenche o que faltar; e sem os dois a tool falha com a mensagem *"servidor de visão não configurado… crie ~/.claude/vision.json"*. [confirmado no corpo]
- ⚠️ **Caminho fixo, ignora `CLAUDE_CONFIG_DIR` por construção** — mesmo traço do `visual-state` (B2). `os.path.expanduser("~/.claude/…")` não consulta a env var, então numa máquina com `CLAUDE_CONFIG_DIR` setado o plugin leria uma pasta e o usuário escreveria noutra.
- **Não é dado do marketplace — é infraestrutura privada de quem instala.** O cabeçalho do script é explícito: *"O ENDPOINT NÃO vive neste arquivo — ele é infraestrutura privada de quem instala"* e *"nunca um endpoint chutado"*. Chaves no disco hoje: `base` (endpoint do servidor VL privado), `model`, `timeout`.
- **Natureza: config local, reconstruível à mão.** Perder o arquivo não perde conhecimento acumulado — perde o endereço do servidor, e o efeito é a tool `see_image` parar até alguém redigitar a config. Mesma classe do `config.json` do `/visual` (B2), com uma diferença: **não há semente versionada** — o default do `/visual` sobe no repo (`config.default.json`), o endpoint do servidor VL não sai de comando nenhum.

### B15 · `~/.claude/gauntlet/arsenal.md` — o repertório do dono, e o sinal órfão ao lado dele

- **Nasceu em 2026-08-09** com o `gauntlet` v0.3.2. **757 bytes / 21 linhas**, um arquivo Markdown por seções (`## website`, `## moodboard / referência visual`). [confirmado — `wc -lc` nesta rodada]
- **Escrito pelo dono, lido pela skill — e escrito por ela só a pedido.** O corpo do arquivo declara o contrato: *"Lista viva, editada por mim (o dono)"*. A skill acrescenta linha quando ele diz "adiciona X ao arsenal", nunca por conta própria.
- **Somável por projeto.** A abertura lê este e, se existir, o `.claude/gauntlet/arsenal.md` do projeto da obra; o segundo soma ao primeiro, sem substituir.
- ⚠️ **Caminho fixo, ignora `CLAUDE_CONFIG_DIR`** — mesmo traço do `visual-state` (B2) e do `vision.json` (B12). O **sinal** do mesmo plugin, que mora na pasta vizinha `andamento/` (B13), resolve por `${CLAUDE_CONFIG_DIR:-$HOME/.claude}`. Duas expressões diferentes no mesmo plugin: numa máquina com a env var setada, o arsenal seria lido de uma casa e o sinal escrito noutra.
- ⚠️ **Há um sinal órfão nesta pasta**, de quando o gauntlet ainda acendia em casa própria: `ativo-01dc346f-…` (0 bytes, 2026-08-07). A casa do sinal migrou para `andamento/` (B13) e este ficou. Não faz mal — o guarda lê a casa nova —, mas é resíduo. [confirmado — `ls -la ~/.claude/gauntlet/`]
- **Natureza: repertório curado, insubstituível por comando.** Perder o arquivo não quebra nada (a abertura segue calada), mas perde a lista que o dono montou à mão. Zero backup, como todo (B).

### B16 · `<projeto>/.claude/gauntlet/<data>-<slug>/` — a missão do gauntlet, e as duas âncoras dela

- **Fora do git** (`.gitignore` linha 21: `.claude/gauntlet/`), e é isso que impede o `rito.json` de levar caminho absoluto da máquina para um repositório público.
- **O que mora dentro**, e cada um tem dono declarado: `rito.json` (a ficha da missão, escrita com o dono aprovando campo a campo) · `decomposicao.json` (do agente decompositor) · `pecas/<id>/r<N>/entrega.json` (do construtor — é **alegação**, e o fecho recomputa a marca de cada artefato contra o disco) · `pecas/<id>/r<N>/veredito.json` (do juiz, e só dele) · `diretor.json` · `vetos.jsonl` (escrito pelo programa, nunca por quem orquestra) · `recon/registros/` (as observações do alvo) · `MAPA.md` (derivado, reescrito pelo `mapa`).
- **Duas âncoras congelam a régua, e elas cobrem coisas diferentes** [confirmado — `fecho_check.py:ancora_leis` e o bloco da âncora em `erros_do_fecho`]:
  - `rito-aprovado.marca` — o resumo do conteúdo do `rito.json` no momento em que a abertura passou. Tirar um eixo depois de julgamentos feitos rebaixaria a barra, e o fecho acusa.
  - `lei-aprovada.marca` — **novo em 2026-08-09** — o resumo de cada documento de lei citado no campo `lei`. Existe porque a âncora do rito só alcança o que está **dentro** do `rito.json`, e a lei mora em documento de fora; sem ela, "reconfira a lei no fecho" era instrução em prosa, e lei alterada no meio da missão passava calada.
- **A marca é o CONTEÚDO, nunca a data** (`fecho_check.py:marca`, sha256 truncado em 16). Data não sobrevive a clone, cópia nem `git checkout` — um julgamento legítimo passaria a ser recusado por uma operação de git que ninguém associaria a esta skill.
- **Natureza: registro de trabalho, insubstituível e não rastreado.** Perder a pasta perde a disputa inteira — os vereditos, as observações e o que já tinha sido aprovado. Zero backup, e é a mesma classe do `.claude/visual/`: artefato de sessão que o repositório público não carrega.

### B17 · `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/lixeiro/` — 108K · a procedência de quem pode ser encerrado

Estava fora do inventário até 2026-08-12. É o único depósito da casa cuja leitura decide
**matar processo**, então a natureza dele não é "cache": é prova de posse.

- **Três naturezas na mesma pasta** [confirmado — contado nesta rodada]:

```bash
ls -1 ~/.claude/lixeiro | sed 's/-[0-9a-f-]\{8\}.*//' | sort | uniq -c
#   74 avisado-*        marca de "esta sessão já ouviu o aviso" (0 bytes, uma por sessão)
#   20 sessao-*.json    o REGISTRO: quem abriu o quê, e qual processo é de quem
#    1 colhido.jsonl    o log de auditoria do que morreu — 79 linhas
```

- **O caminho sai de `lixeiro.py:state_dir`**, que resolve por `CLAUDE_CONFIG_DIR` — ao contrário
  do `visual-state` (B2), do `vision.json` (B12) e do `arsenal.md` (B15), que fixam `~/.claude`.
- **O registro é o que autoriza o sinal.** `sessao-<id>.json` guarda `session_id`, `dono_pid` e a
  lista de `anotacoes`; cada anotação tem `cmd`, `cwd`, `classe`, `em`, `rodadas_sem_processo` e —
  **novos na v1.4.0** — `cpu_ultimo_turno`, `cpu_visto_em` e `cpu_pid`, o trio que registra *a
  última vez que aquele processo foi visto trabalhando*. Sem ele o fim de turno não distingue a
  suíte em andamento da suíte esquecida, e mata as duas (ver `runtime.md` §18).
- ⚠️ **Apagar o registro de uma sessão VIVA não é inócuo:** o processo que ela abriu perde a
  procedência, e nenhuma colheita automática volta a reconhecê-lo — ele só sai pela `/faxina`
  manual. É por isso que, desde a v1.4.0, o arquivo só é removido quando não sobrou processo de
  pé (`lixeiro.py:colhe_orfaos` e o ramo `colhe-sessao` do `main`).
- **Natureza: estado operacional reconstruível, com um custo.** Perder a pasta não quebra nada e
  ela se refaz sozinha na primeira anotação; o que se perde é o histórico de auditoria
  (`colhido.jsonl`) e a procedência do que já estava de pé. Zero backup, como todo (B).

### B18 · `~/.claude/pedro-plugins-permissions-ok` — a marca de consentimento das permissões

- **Nasceu em 2026-08-21** (commit `bfbe936`, o pente fino). Um arquivo pequeno, e **o que importa é existir**: sem ele, o `apply-config.sh` do bootstrap aplica env, flags e barra de status a cada `SessionStart` e **segura o merge de `permissions`** — o allow dos defaults liga aprovação automática na máquina de quem instala, e default de risco não nasce ligado (Artigo 2 da constituição do marketplace).
- **Dois escritores, duas naturezas:** o `/bootstrap:setup` grava por `touch` **só depois do "sim" do dono**, com a lista do que o allow liga mostrada antes; e o próprio `apply-config.sh` grava por **anistia** quando detecta que o merge já aconteceu antes da regra existir (uma permissão distintiva dos defaults presente no `settings.json`) — o conteúdo aí é a linha `anistia: merge anterior detectado em <data>`, e o motivo é declarado no script: travar uma máquina que já vive nesse estado só a deixaria sem atualização. [confirmado — `plugins/bootstrap/hooks/lib/apply-config.sh` e `skills/bootstrap/SKILL.md`]
- **Um leitor:** o mesmo `apply-config.sh`, a cada `SessionStart`. Marca ausente não trava a sessão — o apply segue com o resto dos defaults e avisa que as permissões esperam o de acordo.
- ⚠️ **Nesta máquina o arquivo ainda NÃO existe**, embora a condição de anistia já seja verdadeira (`grep -c 'mcp__plugin_playwright_playwright__browser_navigate' ~/.claude/settings.json` → 2): a anistia só roda no próximo `SessionStart`, e nenhum aconteceu desde o commit. [confirmado nesta rodada]
- **Natureza: acordo com o dono, sem backup — e barato de refazer.** Apagá-lo não perde dado: re-trava o merge de permissões até um novo "sim" (ou até a anistia notar o settings já mesclado). É a versão de-máquina do que A12 é no repo: a fala do dono virando arquivo que um programa consulta.

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
- **Quem lê:** `journal.py:read_events` → `journal.py:fold`; `plugins/project-skills/lib/doc_lint.py` (monta o caminho na linha 153); `plugins/project-skills/lib/pattern_check.py` (check `(c)`: falha se o journal não existir, linha 339). Costura confirmada nos dois lados. [confirmado]

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

### A3 · `graphify-out/` — 140M · o knowledge graph desta máquina

- **Gitignorado desde sempre nesta história** (`.gitignore:44`, seção "RETRATO DESTA MÁQUINA — regenerável, e carimba caminho absoluto e hostname. Sobe o gerador, nunca a saída").
- **`graph.json`** — 5.560.257 bytes. Chaves de topo: `built_at_commit`, `directed`, `graph`, `hyperedges`, `links`, `multigraph`, `nodes`. Medido nesta rodada: [confirmado]

  ```
  nodes 6718 · links 8878 · hyperedges 12
  source_file distinto: 559        communities: 686
  built_at_commit: a7d58bdc59cc7794d66cdae059414c1693071d33
  relações: contains 4801 · calls 2453 · rationale_for 802 · defines 517
            imports 162 · references 60 · method 35 · imports_from 21
            inherits 12 · implements 8 · conceptually_related_to 4
            semantically_similar_to 2 · shares_data_with 1
  ```

  ⚠️ **Estes números valem para este commit e só.** Todo modo que escreve doc roda `graphify update --force` antes; o que é utilizável é o par número + `built_at_commit`, nunca o número solto.
- **`.graphify_labels.json`** — 18.281 bytes, **686 labels, dos quais 50 são nomeados** (o resto é o placeholder `Community NNN`, que `graph_map._is_named` descarta). ⚠️ O número de labels acompanha as comunidades (686), mas os **nomeados continuam 50** — a passada AST não nomeia comunidade nova; quem nomeia é a passada com LLM. [confirmado]
- **`manifest.json`** — 121.594 bytes, **734 chaves**, entre elas as de `pi-plugins/`, que não está no grafo. Contar o manifest é medir o índice, não o mapa: o grafo enxerga 559 arquivos-fonte distintos, contra 567 rastreados pelo git. [confirmado]
- **`GRAPH_REPORT.md`** — 142.834 bytes, relatório humano gerado junto. É a fonte oficial da taxa de extração: nesta rodada ele declara `99% EXTRACTED · 1% INFERRED`, **62 arestas inferidas** com confiança média 0.81 — a extração de 31/07 não tinha nenhuma, então aresta hoje pode ser palpite do extrator, e não leitura de AST.
- **Como o `/doc` consome:** `plugins/project-skills/lib/graph_map.py` destila o grafo num mapa compacto. O que ele muda em relação ao arquivo cru — e o que é **teto**, não medida: [confirmado, saída real do run]

  ```bash
  python3 plugins/project-skills/lib/graph_map.py --project-root .
  # stats: nodes 6718 · links 8878 · hyperedges_total 12
  #        communities_named 30 · god_nodes 60
  # files listados: 40      hyperedges retidas: 6
  # comunidade genérica descartada: "Plugin Manifest Metadata" (18 comunidades)
  ```

  - **`god_nodes: 60` é o corte `top_gods=60`, não uma contagem** — não sobe nem que o repo dobre.
  - **`communities_named: 30` ≠ os 50 labels nomeados** do arquivo: o mapa deduplica por nome e joga fora quem aparece em ≥ `GENERIC_COMMUNITY_MIN = 4` comunidades (metadado repetido, não módulo).
  - **`hyperedges: 6` de 12** — o filtro é `confidence_score >= 0.85`.
  - **Fan-in semântico exclui `STRUCTURAL_RELATIONS = {"contains", "defines", "method"}`**; `contains` sozinho é 4801 das 8878 arestas, e sem a exclusão o ranking viraria "quem tem mais símbolos", não "quem importa".
  - Degrada gracioso: sem grafo, `run()` devolve `{"available": false}` e o exit code continua 0 — ausência de grafo não é erro.
- **Natureza: RECONSTRUÍVEL por comando** (`graphify update . --force`, AST, sem LLM). É o depósito mais pesado do repo (140M com os snapshots datados de junho e julho) e o mais barato de perder.

### A4 · `<repo>/.claude/plans/*.plan.json` — os planos ticáveis

- **31 planos, 775K** (793.866 bytes de JSON) nesta rodada — eram 13 quando o estado abaixo foi tabulado, e 25 na rodada passada. Gitignorado por `.gitignore:18` (seção "REGISTRO DE TRABALHO"). [confirmado — `git check-ignore -v .claude/plans/` → `.gitignore:18`]
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

**Duas outras chaves de topo entraram depois, e as duas são opcionais** [confirmado — `plan_state.py:_erros_dos_limites` e `plan_state.py:_erros_da_frente`]:

```
limites   lista de {limite, motivo} · o que a rodada aceitou deixar de fora. É por aqui
          que a recusa da oferta de branch fica gravada, e é o que faz a oferta se calar
          nas rodadas seguintes. Funde por TEXTO do limite, nunca por posição
frente    objeto {branch, worktree} · a branch e a árvore em que este plano é trabalhado.
          TUDO OU NADA: meio-gravada daria uma frente que o fechamento não sabe encerrar,
          então os dois campos são cobrados juntos. Projeto que trabalha na própria árvore
          grava a raiz do repositório como worktree. Aparece na árvore de texto, vira
          cartão de fechamento na página HTML, e o `close` avisa que a branch continua viva.
          Desde 2026-08-20 (R-42) quem escreve é `plan_state.py:cmd_frente` (idempotente;
          `--encerrar` remove o bloco no fechamento), e a largada do /sprint grava a frente
          obrigatoriamente — a worktree dela mora em `~/.claude/worktrees/<repo>/<id>`,
          FORA do repositório: trabalho não-mesclado vive lá até o rito de fechamento,
          e frente órfã é o que `scripts/frente_orfa_check.py` varre (aviso, não gate)
```

- **Por que o bloco existe no próprio plano:** o requisito é obrigatório, mas o *lugar* dele é opcional. Projeto com documento de requisitos aponta pra lá; projeto sem documento — *"o caso deste repositório, que não tem PRD"* — declara aqui. Sem essa porta, todo projeto sem PRD voltaria a ter tarefa que não rastreia pra nada. [confirmado, docstring de `_requisitos_do_plano`]
- **Os campos deixaram de ser schema no papel: hoje são o dado no disco.** Os planos no disco são **31**, e neles **568 tarefas** trazem `requisito` e `pronto` (as duas juntas, sempre — é o par que `exigir` cobra; 744 tarefas no total), **17 arquivos** carregam o bloco `requisitos` no topo e **63 tarefas** têm `decidido`. ⚠️ **Os dois últimos campos saíram do zero nesta rodada:** `grupo` aparece em **58** tarefas e `pendencia` em **10** — o campo que RECUSA o tique deixou de existir só em teste, e o schema inteiro passou a ter prova de uso em dado real. As chaves de topo presentes são `id`, `title`, `phases`, `created`, `status`, `closed_at` e `requisitos`. **A exigência só morde tarefa que nasce agora**, e é por isso que a virada aparece por acúmulo: os arquivos anteriores ao schema seguem sem os campos e ninguém os migra. [confirmado — derivado com `json.load` sobre os 31 arquivos nesta rodada]
- **O que protege o registro histórico:** `merge()` recarrega do arquivo o que o `init` novo omitiu, pelo mesmo motivo que não apaga a prova. **A regra passou a ser uma só e a valer para o plano inteiro** [confirmado, `plan_state.py:merge`]:
  - **No nó**, os cinco campos da tarefa **mais o `detail`** — que mora na FASE e é o único lugar do 🔧 Como / 💡 Por quê / 📁 Toca em. Ele estava fora da lista antiga e era apagado no `init` seguinte; **os 31 planos no disco carregam 166 blocos `detail`** hoje. [confirmado — derivado com `json.load` sobre os 31 arquivos nesta rodada]
  - **No topo do plano**, TODA chave que o `init` não trouxe, e não mais só `created` e `status`. O que morria na lista fixa era justamente o bloco `requisitos` — a fonte que as tarefas citam — e o `closed_at`. Perder `requisitos` no segundo `init` desligava, em silêncio, o portão que recusa citação para o nada: sem fonte, `reqs` fica vazio e a checagem não roda.
  - **Apagar de propósito continua possível e agora é uniforme: declare a chave VAZIA** (`"requisitos": []`), porque o merge só preenche o ausente. É a mesma regra que já valia para a `pendencia`.
- **`cmd_reabrir` é o caminho de volta:** desfaz uma `decidido`, devolve o texto dela para `pendencia` e a tarefa para `todo`, zerando `evidence` e `done_at`. Existe porque *"toda decisão tomada na ausência do dono seja reversível por construção"* — sem ele, `decidido` seria fato consumado. [confirmado]
- **Quem calcula em cima disso NÃO guarda nada:** `plugins/project-skills/lib/cobertura.py` **não é depósito** — lê os requisitos de um markdown (`le_requisitos`) e os demais documentos de régua (`le_jornadas`, `le_artigos`, `le_pecas`, `le_passos`), cruza com o plano (`mapa`) e devolve a linha única (`resumo`). Zero escrita em disco. A vista "épico › requisito › grupo › tarefa" é **derivada, não armazenada**, pelo mesmo princípio que faz a fase não ter estado próprio. [confirmado — o arquivo tem 394 linhas nesta rodada (nasceu com 79) e nenhuma abre arquivo para escrita]
- **Por que o arquivo existe:** antes disto o plano só vivia no transcript e todo consumidor o **re-derivava por LLM** — lossy: encurta, renomeia fase, chuta se já foi executado. O caso concreto está citado na docstring (`extract_ata.py`: `excerpt: txt[:1200]` e `likely_executed = commits_after > 0 or edits_after >= 3` — um plano de 10 fases + 1 commit virava "concluído").
- **A correção é estrutural:** o modelo **autora uma vez** (`init`) e daí em diante só **marca** (`tick`). Quem desenha a árvore é o programa lendo o arquivo. Como o modelo nunca redigita um título, não há de onde a mudança de nome vir.
- **As travas do schema, lidas de `validate()`:** `id` slug minúsculo; fase casa `F<n>`, passo casa `F<n>.<m>` com prefixo batendo com a fase; `desc` obrigatório e ≤ `DESC_MAX = 140` chars (*"é UMA linha, não um parágrafo"*); `status` ∈ `("todo","doing","blocked","done")`. Erros saem **todos de uma vez**, pra o autor não gastar N rodadas.
- **A trava nova: citação órfã não grava.** Quando há requisitos conhecidos, `validate()` recusa o `init` inteiro se alguma tarefa citar um id que não existe na lista. Não é aviso — é erro. O comentário traz a medida que originou a regra: *"7 de 154 itens de um plano real citaram artigo de lei sem ninguém nunca conferir se o artigo existia"*. `reqs` vazio desliga a checagem, porque projeto sem documento de requisitos é o caso comum, não defeito. [confirmado, `plan_state.py:validate`]
- **Quatro recusas que protegem o depósito:**
  - `tick` exige `--evidencia` com ≥ `EVIDENCE_MIN = 8` chars: *"Sem isso, 'concluído' é palpite — foi assim que planos foram dados como prontos sem estar."* `done` só existe via `tick`; `cmd_state` recusa explicitamente `done`.
  - 🔴 **A `evidence` mudou de natureza em 2026-08-03: passou a ter FORMA, não só tamanho mínimo.** `tick` recusa prova acima de `BULLET_MAX = 140` caracteres **num bloco só** — a condição exata é `len(ev) > BULLET_MAX and len(prova_bullets(ev)) < 2`. O motivo está na recusa: a prova aparece colada ao título do passo, onde a constituição manda bullet, e *"um plano de trinta itens vira trinta parágrafos"*. [confirmado, `plan_state.py:cmd_tick`]
    - **O que passa inteiro: saída crua de comando.** `prova_bullets` quebra só onde quem escreveu já separou — `\n`, ` · `, `; ` ou ` + ` —, então um despejo de terminal com quebras de linha vira ≥ 2 bullets e nunca bate no teto. O teto vale para **o texto redigido pelo modelo**, que é onde o parágrafo nasce. É a mesma isenção que a régua dá à saída crua em qualquer artefato.
    - ⚠️ **O `BULLET_MAX` vem de `regua_texto.py`, não é constante local** (`from regua_texto import BULLET_MAX`, e `DESC_MAX = BULLET_MAX`). O teto do `desc` e o teto da prova são **o mesmo número por construção** — mudar a régua compartilhada muda os dois de uma vez, e o `plan_state.py` importa a cópia vendorada que mora ao lado dele, em `plugins/project-skills/lib/` (o `sys.path.insert` é do próprio diretório do módulo — não é mais a cópia do `plugins/visual/lib/`, de antes da mudança de plugin), uma das **10** que o `sync-shared.sh` mantém (`find plugins -path '*/lib/*' -name regua_texto.py | wc -l` nesta rodada).
    - **A prova já gravada não é reavaliada.** A recusa é do momento de gravar; os planos no disco com prova antiga em bloco único continuam válidos e nada os migra.
  - **`init` fecha a mesma porta pelo outro lado:** `status: "done"` escrito à mão com `evidence` abaixo de `EVIDENCE_MIN` recusa o arquivo. O teto da prova é o mesmo dos dois lados, senão há dois — quem escreve o JSON do `init` é o modelo, e por ali "concluído" entrava sem prova nenhuma. [confirmado, `plan_state.py:erros_do_plano`]
  - `tick` **também recusa tarefa com decisão em aberto** — e o que fecha a decisão é o REGISTRO: `decidido` com uma `escolha` preenchida. **Apagar a `pendencia` não é mais o caminho**, porque o `merge` preserva o campo que o `init` omite e a pergunta voltava, travando a tarefa pra sempre. A `pendencia` continua gravada de propósito: é dela que o `reabrir` vive. [confirmado, `plan_state.py:cmd_tick`]
  - `merge()` **trava a identidade**: título divergente do que está no arquivo aborta o `init` inteiro, e renomear exige `--rename <id> "<novo título>"`. Nó que sumiu do `init` novo é **mantido**, não apagado.
  - Escrita é atômica: `save()` grava em `.tmp` e faz `os.replace`.
  - **`save()` NORMALIZA o registro antes de gravar, desde 2026-08-09:** toda tarefa que chegar sem o campo `status` recebe `"todo"` (`it.setdefault("status", "todo")`) — então **nenhum arquivo no disco tem tarefa sem status**, independentemente de quem montou o JSON. O comentário traz a medida que originou a regra: *"Tarefa sem `status` some das contagens: não é feita, não é pendente, e a soma por fora erra (medido em 2026-08-09 — duas tarefas gravadas sem o campo fizeram 218 virar 217)"*. A normalização mora aqui, e não em cada comando, **porque toda escrita passa por aqui** — é a mesma razão pela qual a marca de sessão (`_marca_sessao`) também é pendurada neste ponto. [confirmado, `plan_state.py:save`]
- **Leitura tem porta única, e ela nomeia o estrago:** `plan_state.py:le_plano`. Arquivo que não abre ou não é JSON vira `PlanError` com o CAMINHO e a CAUSA (*"o arquivo existe e não é JSON válido. Conserte-o à mão — é o registro do que já foi feito, e nada aqui o reescreve"*), em vez de traceback. Quem LISTA (`list_plans`) segue engolindo o arquivo torto de propósito: um byte errado num plano não pode apagar os outros 12 da listagem. [confirmado, e a suíte fecha com a asserção `list_plans pula o corrompido`]
- **Um segundo programa passou a ESCREVER aqui em 2026-08-09, e ele mora noutro plugin:** `plugins/improve-workflow/lib/plano_saida.py:escreve` grava `<dir>/<id>.plan.json` a partir do veredito que o dono deu na página de propostas (`keep` vira passo, `change` vira passo com o texto do dono, `remove` não vira nada). Três traços importam para o depósito: [confirmado no módulo]
  - **Ele confere contra o schema antes de gravar, mas por caminho degradável.** `confere_com_plan_state` acha `plan_state.py` pelo NOME do plugin irmão — `acha_plan_state` chama `skills/improve-workflow/resolve-plugin.sh project-skills lib/plan_state.py` — e o carrega por `importlib`; quando o resolvedor sai vazio ou o arquivo não está na máquina, **o JSON sai igual** e o aviso vai só para o `stderr`. Ou seja: plano gravado por aqui nem sempre passou por `erros_do_plano`. [confirmado — `plano_saida.py:acha_plan_state`]
  - **Item sem veredito recusa a gravação inteira** — rádio em branco chega no retorno como `val: "keep"` com `touched: false`, e *"gravar isso seria transformar silêncio em aprovação"*.
  - **O destino deixou de ter padrão: `--dir` é obrigatório e o programa recusa sem ele.** O padrão antigo era derivado do `__file__` do módulo, não do projeto (`ROOT = os.path.dirname(×3)` sobre `plugins/improve-workflow/lib/`); dentro deste repositório dava a pasta certa, mas instalado `${CLAUDE_PLUGIN_ROOT}` é o cache do plugin e o plano do dono nasceria lá dentro. Recusar é a trava — quem chama passa o destino ou não grava. [confirmado — `plano_saida.py:main`, `--dir` com `required=True`]
  - **Quem chama é o passo 8 da `SKILL.md` do plugin**, que passa o spec pelo stdin (`--proposta -`) e `--dir .claude/plans`. [confirmado nos dois lados]
- **Quem lê no fim do turno:** `plugins/project-skills/hooks/stop-plan-status.sh`, via `plan_state.py brief`. Canal `systemMessage` (informa, nunca bloqueia), desligável por `PLAN_STATUS=0` / `PLAN_NUDGE=0`. Costura confirmada nos dois lados. [confirmado] O resumo que ele mostra **parou de afirmar prova sem olhar a prova**: o trecho *"cada um com prova anexada"* era escrito por construção e hoje só entra depois de `plan_state.py:_com_prova` conferir a `evidence` de cada passo feito. [confirmado]
- **Quem lê na hora de guardar a sessão:** a skill `handoff`. Ela passou a **ler os campos do arquivo em vez de pedir que sejam reinventados** — a árvore de `render --format text` é a vista de execução e não mostra `pronto`, `pendencia` nem `requisito`, que são justamente os três que a sessão seguinte ia redigir de cabeça. A `SKILL.md` traz o comando que os imprime e manda copiá-los **verbatim**: o `pronto` vira o "Critério de pronto" e a `pendencia` vira "Decisão em aberto", com o passo marcado como **bloqueado** — listar como executável um passo cuja `pendencia` trava o tique manda a próxima sessão bater na mesma parede sem saber qual é a pergunta. [confirmado — `plugins/handoff/skills/handoff/SKILL.md`, e a suíte `plugins/handoff/lib/test_handoff_skill.py` executa o comando prescrito e cobra a prosa]
- **Natureza: registro de trabalho, insubstituível, sem cobertura.** Verde em `plugins/project-skills/lib/test_plan_state.py` nesta rodada.

### A5 · `.claude/hook-contract.baseline.json` — o retrato do contrato dos hooks

🔴 **Voltou a ser rastreado nesta rodada** — saiu da seção "RETRATO DESTA MÁQUINA" do `.gitignore` quando perdeu o campo que o prendia a uma máquina. [confirmado: `git ls-files .claude/hook-contract.baseline.json` devolve o caminho]

- **Tipo:** JSON único, sobrescrito por `python3 scripts/hook_contract.py --json > …`. Tamanho: `wc -c .claude/hook-contract.baseline.json`.
- **Quatro chaves de topo, e elas não têm o mesmo tipo** — `entries` e `scripts` são números; `findings` e `measured` são listas. O comando que devolve os quatro: [confirmado]

  ```bash
  python3 -c "import json;d=json.load(open('.claude/hook-contract.baseline.json'));\
  print({k:(len(v) if isinstance(v,list) else v) for k,v in d.items()})"
  # {'entries': 56, 'scripts': 43, 'findings': 45, 'measured': 56}
  ```

  ⚠️ **`entries` > `scripts` porque um mesmo script é registrado em mais de um evento** — contar entradas como "quantos hooks eu tenho" infla, do mesmo jeito que contar chaves do `manifest.json` como "quantos arquivos" (A3).
- ⚠️ **`findings` não é "o que está errado hoje" — é o que foi CONGELADO como aceito.** As 45 linhas são o retrato refeito em 2026-08-09, e a maioria esmagadora é da régua de nome de hook (`R6-nome-fora-do-molde`, `R6-nome-verbo-errado`, `R6-nome-evento-errado`), com uma `R1-cap-ausente` e duas `R5-sem-failopen`. Por sev, `high` domina. Os números saem do arquivo, nunca de uma contagem escrita aqui: [confirmado]

  ```bash
  python3 -c "import json,collections;d=json.load(open('.claude/hook-contract.baseline.json'));\
  print(collections.Counter(f['rule'] for f in d['findings']), collections.Counter(f['sev'] for f in d['findings']))"
  ```

  É por isso que o gate segue verde com 45 achados dentro do baseline: `--baseline … --fail-on high` fecha com *"Nenhum achado. Todos os hooks batem com o contrato."* e sai 0 nesta rodada. [confirmado — comando rodado]
- ⚠️ **Não há mais chave `root`.** Ela gravava o caminho absoluto da máquina que mediu — metadado de proveniência que não serve a quem instala e que sujava um repositório público. Sem ela, o retrato viaja e outra máquina reproduz a comparação. [confirmado: `grep -c '/Users/'` no arquivo devolve 0]
- **O que o script mede** (`scripts/hook_contract.py`, cabeçalho): as 5 propriedades que separam um gate saudável de um que trava ou se desliga sozinho — canal de saída, cap anti-loop escopado por sessão, kill-switch, binário fixo, fail-open. O aviso do próprio arquivo: *"Isto é grep sofisticado, não verdade."* Por isso a saída traz sempre a linha e o trecho que dispararam o achado.
- **Natureza: RECONSTRUÍVEL, mas com JULGAMENTO embutido.** Regerar é um comando; o que **não** se regenera é quais achados foram aceitos — essa parte vive em prosa (`patterns.md`, "As isenções"). O JSON é o estado, o `patterns.md` é o porquê.
- **Quem lê:** o check E do `.claude/hooks/release-gate.sh` (linhas 99-107), via `--baseline`, barrando só o que **piorou**. Costura confirmada nos dois lados. [confirmado]
- **Refeito em 2026-08-09** (`git log -1 -- .claude/hook-contract.baseline.json` → `aa42385`), e é o mesmo `--baseline … --fail-on high` que a esteira `portability.yml` roda nos três sistemas.
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

### A5d · Os quatro retratos NOVOS — a família de baselines virou seis, e o sétimo entrou em 2026-08-21

Nesta rodada o repositório passou de dois retratos congelados (A5 e A5a) para **seis**, e todos seguem o mesmo contrato: JSON rastreado, regerado por comando, lido por um check do `release-gate.sh`, e **nunca reescrito por hook**. A lista vive no git, não aqui:

```bash
git ls-files '.claude/*.baseline.json'   # a família de hoje
wc -c .claude/*.baseline.json            # o tamanho de cada um
```

Os quatro que entraram, com o que cada um congela [confirmado — leitura dos arquivos e do `release-gate.sh` neste run]:

- **`.claude/desacoplamento.baseline.json`** — **95 entradas, 14K.** A dívida de acoplamento **já existente**: plugin que aponta pro irmão por posição, ou contagem cravada em prosa. Lido pelo check **N**, que reprova só o que aparece **fora** desta lista. É o único da família cujo cobrador não tem `--staged`: ele varre todo arquivo rastreado, e o baseline é o que impede a dívida antiga de travar trabalho novo.
- **`.claude/suite-congela.baseline.json`** — **273 entradas, 30K.** O maior da família. Congela o estado das suítes para que uma que deixe de rodar não passe despercebida.
- **`.claude/custo-gatilho.baseline.json`** — **550 bytes**, e é o único que não é lista: as chaves são `medido_em`, `como`, `por_skill` e `total_caracteres`. Congela **quanto texto de gatilho de skill entra no contexto** — o custo que toda sessão paga antes de a primeira palavra ser digitada. ⚠️ **`medido_em` e `como` estão dentro do dado de propósito**: número de custo sem a data e o método que o produziram não é comparável com o da próxima medição.
- **`.claude/fio-morto.baseline.json`** — **1 entrada, 74 bytes.** O menor da família. Congela o fio morto conhecido; a lista de uma entrada é o que diz que a régua está limpa hoje, não que ela nunca achou nada.

**O sétimo chegou em 2026-08-21 e JÁ ESTÁ RASTREADO: `.claude/artigo8.baseline.json`** — ~104K, o maior arquivo da família; quantos achados ele congela hoje sai do comando, nunca daqui (`python3 -c "import json;d=json.load(open('.claude/artigo8.baseline.json'));print(len(d['findings']))"` → **290** nesta rodada). Congela a dívida do Artigo 8 (comando de `SKILL.md` que só roda na árvore de quem escreveu), lido pelo check **V** do `release-gate.sh`, que reprova só o achado NOVO. As chaves são `skills` (quantas a varredura alcançou) e `findings`. ⚠️ **Ele muda a cada re-congelamento e o número envelhece sozinho**: mexer numa `SKILL.md` desloca as linhas citadas e o retrato é regravado inteiro — foi o que esta onda fez ao reescrever `skills/sprint/SKILL.md`. Num clone SEM o arquivo o `--check` sai 0 dizendo *"retrato ausente ou ilegível — nada a comparar"*, isto é, o check V passaria verde sem medir nada; é justamente esse buraco que o rastreamento fechou [confirmado nesta rodada — `git ls-files '.claude/*.baseline.json'` → **7** caminhos, o sétimo entre eles].

⚠️ **A natureza de todos é a mesma do A5, e ela é sutil: RECONSTRUÍVEL, com julgamento embutido.** Regerar qualquer um é um comando. O que **não** se regenera é a decisão de aceitar uma piora — e essa decisão *é* o ato de recongelar. Perder o arquivo não perde dado; perde o registro de que alguém olhou e disse "isto pode ficar".

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
- **Escrita concorrente é protegida, e a trava tem DUAS implementações** (mudou em 2026-08-10): com `fcntl`, `flock(LOCK_EX)` sobre `ledger.lock` — o caminho de sempre, e o do disco deste projeto (0 bytes, está lá). **Sem `fcntl`** — que é POSIX e não existe no Windows — a trava vira um **diretório** `ledger.lock.d`, criado com `os.mkdir`, que é atômico em qualquer sistema de arquivos: quem cria, entra; quem não cria, espera. Sem isso, hooks concorrentes geram `r-N`/`p-N` duplicados.
- ⚠️ **A espera pela trava tem teto absoluto, e passou do teto ela segue SEM a trava** (`ESPERA_TRAVA_S = 5.0`, e a trava tem idade máxima igual, para que processo morto no meio não trave todo mundo para sempre). A escolha é declarada no código: *id duplicado é incômodo visível, missão pendurada é dano*. O teto é conferido **no topo do laço**, não depois do `except` — com ele embaixo, o caminho "trava órfã removida" pulava a checagem e o laço girava sem limite. O invariante está em `test_ledger.py:test_concurrent_record_raw` (8 gravações concorrentes, 8 ids distintos).
- **Arquivos satélites no mesmo diretório**, todos parte do protocolo de auditoria: `audit-*.json` (o veredito de uma rodada), `<audit>.applied` (marcador de idempotência — `apply_audit` sai cedo se existir), `<audit>.escopo` (a lista de ids que o gate **perguntou**, gravada no instante do bloqueio). O `.escopo` conserta uma catraca medida: sem ele, cada mensagem enviada entre auditar e consumir entrava na conta e o veredito nascia impossível de aprovar — *"33 pedidos vivos cobrados de uma auditoria que perguntou por 1"*.
- **O `tree_hash` protege o veredito de envelhecer**, e exclui `EXEC_ARTIFACTS` (`__pycache__`, `*.pyc`, `node_modules`, `*.log`, `dist`, `build`, `coverage`, …) porque a própria auditoria roda código e sujaria a árvore — *"o gate nunca fecha, bate o cap e libera SEM auditoria, o oposto do propósito"*.
- **Degradação declarada:** erro de I/O silencia os comandos de escrita e devolve fallback seguro nos de leitura — `verify` falhando devolve `remaining: -1`, jogando tudo pro auditor caro, porque *"degradar pro caro é seguro; pro barato não"*.
- **Natureza: histórico de intenção, insubstituível, sem backup.**

### A11 · `.claude/.sprint/corridas.jsonl` — a SÉRIE de execuções da missão

- **Uma linha por execução do motor de plano, append-only, gitignorado.** Quantas hoje sai do comando: `wc -l < .claude/.sprint/corridas.jsonl`. [confirmado nesta rodada]
- **Cada linha traz** o id da execução, a missão (o caminho do plano), o progresso (`fechadas` de `total`), o custo em tokens, o par início/fim, o **desfecho** — o vocabulário medido até aqui inclui `onda-esteril`, `porta-fechada`, `causa-global`, `parada-pelo-dono` e `morta-por-fora` — e, desde 2026-08-20, a **`causa`**: o `what` do último blocker, normalizado e cortado em 160 chars (`_causa_de`). É o único campo legitimamente vazio — corrida que terminou limpa não bateu em pedra, e exigir uma inventaria a pedra. [confirmado — `ledger_corridas.py:CAMPOS`, `OPCIONAIS`]
- **Por que existe:** uma execução isolada não diz se a missão avança ou gira em falso; a **série** diz. É ela que o `relance` lê antes de relançar — relançar é apostar que a próxima passa onde a anterior parou, e na terceira vez a aposta já perdeu duas. ⚠️ **A pedra que o `relance` conta é a CAUSA, não o desfecho** (mudou em `498764e`): três corridas seguidas pararam com o mesmo desfecho (`porta-fechada`) e pedras distintas, cada uma consertada na raiz — contar desfecho barrou a quarta como se ninguém tivesse consertado nada. Linha antiga sem causa cai no desfecho, retrocompatível. [confirmado — `ledger_corridas.py`, verbos `abre`, `registra-run`, `serie`, `relance`]
- **Quem escreve é o programa, nunca a mão** — e a **largada** vai ao disco ANTES da chamada, porque execução que morre por fora não tem retorno: sem essa marca, a que fracassou é justamente a que sumiria da série.
- **A marca da largada tem casa própria: `.claude/.sprint/em-curso/<run_id>.json`** (`dir_largadas`). O `abre` grava `{run_id, missao, total, inicio}` antes da chamada; o `registra-run` solta a marca no retorno; o que sobrar sem sinal de vida por mais de 12h (`TETO_SEM_SINAL`) o `colhe` fecha como linha `morta-por-fora` na série, com o não-medido marcado `nao-medido` em vez de 0 — zero é medição, inventá-la é o defeito que o ledger existe para matar. Marca ilegível (processo morto no meio da escrita) entra pelo que o nome do arquivo diz, em vez de derrubar a leitura inteira. **Efêmero por desenho: vazio agora, e as 2 linhas `morta-por-fora` da série provam que a colheita já rodou de verdade.** [confirmado — `ledger_corridas.py:abre`, `colhe_orfas`, e `ls .claude/.sprint/em-curso/`]
- ⚠️ **Já foi truncado uma vez sem culpado conhecido** (2026-08-15: 4 linhas às 17h, 1 às 20h45, num arquivo append-only por desenho). As três foram restauradas com os números que o próprio programa tinha impresso, marcadas com `restaurado:`. **Causa desconhecida — pode voltar a acontecer.**
- **Natureza: histórico de medição, insubstituível.** O progresso se remede pelo plano; o **custo e o tempo de cada execução passada**, não.

### A11b · `.claude/.sprint/paradas.jsonl` — a PEDRA em que a missão bateu

- **Uma linha por PARADA do laço do `/sprint`, append-only, gitignorado** (mesma pasta do A11, mesma linha do `.gitignore:34`). Quantas hoje: `wc -l < .claude/.sprint/paradas.jsonl`.
- **Cinco campos, todos obrigatórios:** `run_id` (a corrida em que parou), `desfecho` (o `stopReason`), `causa` (a causa já referendada pelo desafiador), `conserto` e `sha` (o commit que aplicou o conserto, ou o literal `sem-commit`). Campo vazio **sai 2 e não grava**. [confirmado — `ledger_corridas.py:CAMPOS_PARADA` e `registra_parada`]
- **A parada do DONO tem válvula declarada:** `conserto: "sem-conserto"` (`SEM_CONSERTO`). A parada que só o dono resolve não tem conserto para gravar — e é a que mais interessa a ele; sem a válvula, era justamente essa que o registro recusava, e a seção "uma linha por parada" nascia incompleta. Medição declarada, não campo vazio: vazio continua reprovando. **Das 2 linhas no disco hoje, 1 usa a válvula.** [confirmado — `ledger_corridas.py:SEM_CONSERTO` + leitura do arquivo nesta rodada]
- **É outro GRÃO, não outra cópia do A11.** A corrida é a unidade do custo; a parada é a unidade do laço — a mesma corrida pode bater em várias pedras, e uma pedra pode voltar em corridas diferentes. Por isso mora em arquivo próprio, e não como campo da linha da corrida.
- **Por que existe:** a seção `### Problemas (as paradas do laço)` do relatório final é **derivada deste arquivo**, nunca da memória da sessão. É o par `conserto`+`sha` que separa "consertado" de "lembrado" — sem ele, problema resolvido pela metade saía no relatório como resolvido. [confirmado — a seção "Conteúdo (backbone)" de `skills/sprint/SKILL.md`]
- **Quem escreve é a vigília do sprint, a cada volta do laço, logo depois de o conserto virar commit** — e o laço não relança sem a linha gravada. [confirmado — `test_sprint_skill.py`, check *"parada sem linha gravada nao relanca"*]
- **Natureza: histórico de medição, insubstituível.** O conserto se relê no commit; a associação *pedra → conserto → corrida* não sai de lugar nenhum depois que a sessão fecha.

### A11c · `.claude/.sprint/precheck.json` — o relatório do pré-check de largada

- **Um arquivo por projeto, SOBRESCRITO a cada rodada** — ao contrário dos dois vizinhos append-only, aqui a pergunta não é de série: é "o motor pode largar AGORA?". Mesma pasta, mesma linha do `.gitignore:34`. [confirmado — `precheck_largada.py:grava_relatorio` abre com `"w"`]
- **Por que existe, copiado do comentário do módulo:** *"Sem isto o pré-check é conversa: as quatro passadas rodam, o dono lê na tela, e o motor larga sem que nada no disco diga que elas rodaram, ou que rodaram sobre ESTE plano."* Quem MEDIU grava (`grava_relatorio`), quem LARGA confere (`confere_largada`) — a mesma régua da prova da esteira.
- **O conteúdo:** `marca` + `gravado_em` + `passadas` + quatro listas — `abertas` (pergunta que ainda vai ao dono), `tomadas` (achado que o registro selado A12 já respondeu), `propostas` (a rodada N+1 pediu reescrita de um passo) e `adiadas` (o que não deu para medir; não fecha a porta, mas o `--confere` o NOMEIA no texto do "livre") — e o `veredito`: `livre` ou `em-aberto`.
- **A `marca` é o que faz o relatório VENCER na hora certa:** sha256 sobre `id`+`desc`+`pronto` dos passos **abertos** do plano + o texto do `decisoes-seladas.md` — e **nada da árvore**, porque cada tique mexe no disco e venceria o relatório por conta própria. Tique não vence; passo reescrito, passo novo e decisão selada nova vencem. [confirmado — `precheck_largada.py:marca`]
- **A conferência recusa a largada em quatro casos, nomeando qual:** relatório ausente, vencido (a marca divergiu), proposta pendente ou decisão em aberto. E a rodada N+1 **atualiza** o relatório em vez de substituí-lo (`aplica_rodada_seguinte`) — substituir era a porta escancarada: regravar o arquivo inteiro com o resultado da N+1 sumia com as `abertas` das 4 passadas, e um arquivo de respostas vazio bastava para o `--confere` deixar largar.
- **Natureza: derivado, remediável** — some, e as quatro passadas o refazem do plano e do registro selado. O que não volta sozinho é a **resposta do dono** às abertas, mas essa mora no A12 quando é selada, não aqui.

### Os outros de (C)

- **`.claude/visual/` — 5,2M, 100 entradas** (`.gitignore:47`). As páginas HTML que o `/visual` gera. Descartável: são a apresentação, não a fonte. [confirmado — `du -sh` + `ls | wc -l` nesta rodada]

  🔴 **O inventário deixou de ser opaco: desde 2026-08-03 ele é AUDITÁVEL, e a auditoria reprova a maioria.** `python3 plugins/visual/lib/regua_audit.py paginas` abre cada página, descobre por qual gerador ela passou e diz qual regra da régua de texto cada uma quebra. Saída desta rodada: [confirmado]

  ```
  📊 100 páginas · 83 com violação
      • duas-frases — duas frases no mesmo bullet: 1283
      • teto-140 — teto de 140 caracteres: 1042
      • conectivo — abre com conectivo de continuação: 16
      • ❔ 9 páginas sem perfil de gerador — digitada à mão, fora do alcance
  ```

  - **As 82 do registro de limites e as 83 de agora não são a mesma medida.** `.claude/limites-aceitos.md` (A8) congelou **99 páginas · 82 com violação** no dia da decisão; a página nº 100 (`2026-08-03-status-consolidado.html`, de hoje 16:22) entrou **depois** e traz 2 violações. ⚠️ Isso contradiz a premissa escrita do limite aceito — *"a régua passa a valer para página nova"* — e é o tipo de deriva que só aparece rodando o comando, porque o arquivo de limites guarda a saída daquele dia, não a de hoje.
  - **As 9 "sem perfil de gerador" são página digitada à mão.** Nenhum gerador as alcança, então consertá-las é editar HTML, não código — é por isso que elas entram no registro de limites em vez da fila de conserto.
  - **A auditoria não guarda nada.** É medição derivada, calculada a cada execução sobre os arquivos do disco: some junto com as páginas e volta junto com elas.
- **`.claude/vistoria/piloto-leitor-2026-08-09.json` — 3,2K** (`.gitignore:20`). **O único arquivo de `.claude/vistoria/` que nenhum comando refaz.** É a rodada-piloto de leitura por agente sobre três pedaços (duas fixtures e o plugin `graphify-guard`), e o próprio arquivo declara, no campo `_piloto`, que ela **não liga** o leitor por agente no caminho padrão da skill — que segue congelado (`skills/vistoria/SKILL.md:119`). Julgamento escrito à mão, na mesma classe dos vereditos do gauntlet (B16). A página irmã (`vistoria-2026-08-09-piloto-leitor.html`) sai dele pela `pagina.py --rodada` e essa, sim, volta. [confirmado — campo `_piloto` do JSON]
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

Regra do repo: estado por-sessão em `/tmp` **tem que** ser chaveado por `session_id` — e desde 2026-08-21 (commit `bfbe936`) a regra ganhou o complemento: **payload sem `session_id` sai liberado sem escrever nada**. O fallback antigo (`session_id` ausente virava a chave literal `unknown`) criava um sentinela compartilhado entre todas as sessões sem id — o mesmo defeito do estado global que motivou o per-sessão do context-guard v1.1, só que renomeado. São **12 hooks** com o ramo novo, e o número sai do comando, nunca daqui: `grep -rl 'payload sem sessão: liberado' plugins/*/hooks/*.sh | wc -l`. [confirmado nesta rodada]

As três famílias vivas:

- **context-guard** — `/tmp/claude-context-pct-<session_id>` (escrito pelo wrapper de statusLine `context-guard-writer.sh`) e `/tmp/claude-context-warned-<session_id>` (sentinel do disparo). O `context-guard-reset.sh` apaga **só os da própria sessão** e depois poda órfãos: `find /tmp -maxdepth 1 -name 'claude-context-pct-*' -mtime +1 -delete` (idem `-warned-`). O comentário registra o bug que motivou o per-sessão: um arquivo global era sobrescrito pela última statusLine a renderizar, e **uma** sessão a 80% fazia o guard bloquear **todas**. [confirmado]

  🔴 **Este depósito só existe se o writer estiver na cadeia da statusLine, e em 2026-08-02 ele não estava.** Medido: o único `/tmp/claude-context-pct-*` no disco era `claude-context-pct-smoke-123`, **fixture de teste** com mtime de 30/jul, enquanto o plugin aparecia habilitado. Nenhuma sessão real gravou por 3 dias, e a barra de status continuou perfeita — quem sumiu foi o elo que produz dado para **outro** consumir. Quem cobra agora é `conformance.py:check_statusline_meio_ligada` (ver `architecture.md §10.1` e `patterns.md §1.14`). ⚠️ **Fixture de teste no mesmo diretório do estado real é armadilha**: `ls` do glob parecia saudável, e só o nome e o mtime denunciavam.
  ⚠️ **A poda não está dando conta:** `ls /tmp | grep claude-context-warned` devolve mais de 20 sentinelas de sessões mortas. A poda só roda no `SessionStart` **de uma sessão que tenha `jq`** — sem ele o script sai na primeira linha, e a limpeza nunca acontece. [confirmado]
- **plano do `/visual`** — três sentinelas em `${TMPDIR:-/tmp}`, todas com a mesma chave `$(id -u)-${SESSION}-${PHASH}`, onde `PHASH` é o `cksum` do **diretório de planos resolvido** (não do cwd — canonicalizar path na chave é uma armadilha conhecida do repo): `claude-plan-mark-*` (marco do início da sessão, que data o "encerrado agora"), `claude-plan-nudge-*` (a cobrança já saiu nesta sessão) e `claude-plan-closed-*` (quais encerramentos já foram confirmados). Sem a terceira, o 🏁 repetia a cada turno até a sessão acabar. [confirmado em `stop-plan-status.sh` e `plan_state.py:_seen_ids`]
  - ⚠️ **Uma quarta entrou em 2026-08-03, e ela é de outra natureza: guarda CONTEÚDO, não um sim/não.** `claude-plan-sessao-<uid>-<sid>-<sha1(abspath do dir)[:12]>` guarda **o id do plano** que aquela sessão escreveu por último, e é o que faz o fim de turno mostrar a frente certa num projeto com sessões paralelas. Quem grava é `plan_state.py:save()` — todo caminho de escrita de plano passa por ali —, e quem lê é o `brief`, pela **mesma** função de chave (`_sentinel_sessao`). ⚠️ Note que a chave dela usa `sha1` do path absoluto, e as três acima usam `cksum` calculado pelo shell: são esquemas diferentes de propósito, porque a nova é calculada **só em Python**, nos dois lados. Misturar os dois é que reintroduziria a divergência. [confirmado — `plan_state.py:_sentinel_sessao`, e 7 checks em `test_plan_state.py`]
- **handoff / ata** — `/tmp/claude-ata-session-<h>`, `/tmp/claude-handoff-target-<sid>`, `/tmp/claude-ata-gate-ok-<h>`.

Efêmeras por definição. Nenhuma delas é entrada de nada — reconstroem-se sozinhas na sessão seguinte.

---

## Os símbolos que mais gente depende (e o que eles guardam)

- **`scrub()`** (`journal.py`) — a barreira entre conversa-verbatim e disco. Devolve `(texto_scrubbed, [(cofre_key, valor)])`. É o que decide se um segredo vira placeholder ou vaza. Roda na **escrita**, não no commit.
- **`fold()`** — existe em **duas encarnações independentes e com regras diferentes**: `journal.py:fold` (discovered/invalidated/curated; invalidação é definitiva) e `ledger.py:fold` (raw/classify/verdict/baixa; filtra vivos por sessão). Ambas seguem o mesmo princípio: **o estado vem do arquivo, nunca do julgamento do modelo.**
- **`live_findings()`** (`journal.py`) — projeta o fold: descarta o que não está `live`, troca `text` por `curated` quando há, ordena por `source.ts`. É o que a doc realmente lê.
- **`read_events()` / `append()` / `append_events()`** — as portas de I/O dos dois journals. Ambas só abrem em modo `"a"`; nenhuma tem caminho de truncamento. `ledger.py:append` ainda faz `ev.setdefault("ts", ...)` pra nenhum evento nascer sem relógio.
- **`load()`** (`ledger.py`) — leitura tolerante: linha ilegível é pulada (`continue`), arquivo ausente devolve `[]`. Um JSONL corrompido no meio degrada, não derruba.
- **`intent_dir()` / `resolve_dir()`** — os dois resolvedores de "onde este projeto guarda seu estado". `intent_dir` implementa a cascata em Python; `resolve_dir` (`plan_state.py`) **delega a um script de shell** de propósito, *"pra não haver duas implementações da cascata que possam divergir"*. ⚠️ **O script é o irmão de pasta, `plugins/project-skills/lib/resolve-dir.sh`** (`os.path.dirname(__file__)`), não o que mora na skill do `/visual` — os dois são cópias vendoradas do mesmo `_shared/resolve-dir.sh`; o docstring do módulo ainda cita o caminho velho. [confirmado — `plan_state.py:127`]
- **`pick_plan()` / `plan_progress()`** — `pick_plan` recusa adivinhar: sem id, exige que haja **exatamente um** plano ativo, porque *"adivinhar aqui é como o plano se perde"*. `plan_progress` conta passos `done` sobre o total — o número que aparece em todo lugar.
- **`PlanError`** — a exceção única do `plan_state.py`. Toda recusa (título divergente, tick sem prova, plano ambíguo) sai por ela, com a mensagem já formatada pro usuário.
- **`git()`** — também em duas encarnações, e as duas escolheram a mesma direção: `journal.py:git` devolve `""` em qualquer erro (delta degrada, não quebra); `branch_state.py:git` levanta `BranchError` por padrão e devolve `None` com `ok_fail=True` (verbo que **apaga** não pode falhar em silêncio).
- **`classify()`** (`branch_state.py`) — a leitura pura do estado das branches (*"NÃO escreve nada"*). É o insumo do `prune`; usa o relógio real (`int(time.time())`) e não o último commit da base, porque com a base parada uma branch mais nova dava idade 0 e sumia do radar.
- **`_e()` / `_rich()`** (`visual_page.py`, e `_e` também em `plan_state.py` e `branch_state.py`) — `_e` é `html.escape(..., quote=True)`; `_rich` escapa **e depois** reabre um subconjunto mínimo de markdown (só `` `code` `` e `**negrito**`). Existe pra o spec JSON não precisar carregar HTML: *"se o modelo escrevesse HTML dentro do JSON, a gente teria trocado de sintaxe sem trocar de problema."*

---

## Fora do inventário — verificado e não guarda dado

- **`.claude/vistoria/` — 108K, 5 arquivos** (`.gitignore:20`, seção *registro de trabalho*). A saída da `/vistoria`: as páginas `vistoria-<data>[-<rodada>].html` e o JSON de achados que as alimenta (`medidor.py --json | pagina.py --dir .claude/vistoria`, `SKILL.md:71-72`). **Elas se regeneram rodando o medidor de novo** — são retrato do repositório de hoje, não conhecimento. ⚠️ **Rodar de novo não apaga o que está aqui:** `pagina.py:_caminho_livre` nunca sobrescreve — sem `--rodada`, a segunda rodada do mesmo dia sai como `vistoria-<data>-2.html` com aviso no stderr, então o diretório CRESCE a cada rodada e a limpeza é manual. Foi uma sobrescrita assim que comeu a página do piloto. ⚠️ **Um dos cinco é exceção e está no inventário**, em *Os outros de (C)*: `piloto-leitor-2026-08-09.json`. [confirmado — `du -sh` + `ls | wc -l` + `git check-ignore -v` nesta rodada]
- **Nenhum banco, ORM, migration ou `docker-compose`.** O único lockfile do repo é `plugins/archify/skills/archify/package-lock.json`.
- **`.claude-plugin/marketplace.json`** e os `plugin.json` — catálogo e metadado, escritos só por humano. Não são estado.
- **`_shared/`** — código vendorado. Fonte, não depósito — **com uma exceção desde 2026-08-03**: `r8-tiers.json` é dado, não código, e está no inventário como A7.
- **`pi-plugins/`** (`.gitignore:71`) — cópia local defasada de `plugins/`, explicitamente **não é fonte**. Continua fora do grafo; as 106 chaves dela que sobrevivem no `manifest.json` do graphify são entradas mortas do índice.

---

## Resumo por natureza

**Insubstituível e SEM cobertura nenhuma** (perder o disco = perder o conteúdo):

```
.claude/.project-doc/findings.jsonl   3,3M · 1133 eventos   (journal do conhecimento)
.claude/intent/ledger.jsonl           429K ·  622 eventos   (caderno de pedidos)
.claude/ata/                          1,9M ·   32 arquivos  (logs de sessão)
.claude/plans/*.plan.json             775K ·   31 planos    (o que foi feito, com prova)
.claude/qa-loop/telemetry.jsonl        3 linhas             (calibração do /qa-loop)
.claude/vistoria/piloto-leitor-*.json 3,2K                  (a rodada-piloto do leitor por
                                      agente; julgamento escrito, sem comando que o refaça)
~/.claude/plans/                      1,1M                  (do harness; encolhe sozinho)
~/.claude/intent/                     264K                  (fallback de outros projetos)
~/.claude/state/forma-relato/         104K ·  20 vereditos  (o texto do que a régua reprovou)
~/.claude/andamento/duracoes-*.json                          (quanto cada comando demora;
                                      não se regenera por comando nenhum — só por uso)
~/.claude/visual-state/licoes-clareza.json                   (as regras de escrita das
                                      páginas; só as de fábrica voltam, as aprendidas não)
.claude/.sprint/corridas.jsonl        31 linhas             (custo e tempo de cada corrida)
.claude/.sprint/paradas.jsonl          2 linhas             (pedra → conserto → corrida)
```

**Reconstruível, com custo:**

```
.claude/limites-aceitos.md            2,1K · rastreado — o NÚMERO se remede por comando,
                                      a decisão de aceitar não sai de lugar nenhum
_shared/r8-tiers.json                 2,9K · rastreado — o valor volta com o git,
                                      o `porque` de cada tier é julgamento escrito
.claude/.project-doc/ledger.json      re-minerar vira cold-start (CAP=1000 commits)
.claude/hook-contract.baseline.json   1 comando — mas o JULGAMENTO das isenções não volta
graphify-out/                         graphify update . --force (AST, sem LLM)
plugins/bootstrap/config/manifest.json  regenerado no SessionStart, MENOS as chaves manuais
~/.claude/vision.json                  config do servidor VL — redigitar à mão, sem semente
~/.claude/improve-workflow/registro.jsonl  remedir os runs que ainda estiverem em
                                       ~/.claude/projects; run já rotacionado não volta
.claude/.sprint/precheck.json          as 4 passadas refazem do plano + registro selado;
                                       a resposta do dono, quando selada, mora no A12
~/.claude/pedro-plugins-permissions-ok  volta com um novo "sim" no /bootstrap:setup
                                       (ou pela anistia sobre settings já mesclado);
                                       sem ela o merge de permissões não roda
```

**Descartável por desenho:**

```
~/.claude/green-suite/          cache puro, TTL 24h por linha, poda de 7 dias
~/.claude/visual-state/         estado de UI (exceto os dois hóspedes: config.json,
                                que é preferência, e licoes-clareza.json, que não volta)
~/.claude/andamento/            interruptor + reserva + andamento, uma casa só
~/.claude/guardrails/           logs e contadores dos dois vigias
~/.claude/state/prose-ceiling/  contadores + batidas + bypass do teto
~/.claude/state/intent-guard/   a marca `olhado`; apagar zera o "desde a última vez"
/tmp/claude-*                   sentinelas por sessão
.claude/visual/                 100 páginas HTML geradas (83 reprovam a régua hoje)
.claude/vistoria/vistoria-*     3 páginas + JSON de achados; voltam com o medidor
```

**Com cobertura de terceiro:** só o cofre, no iCloud.

---

## Pendências

1. ✅ **Resolvida: o baseline dos hooks (A5) foi refeito e voltou a viajar.** Ele é rastreado (perdeu a chave `root`, que prendia o retrato a uma máquina) e o congelamento é de 2026-08-09 (`aa42385`). O que sobra de decisão é o conteúdo dele: **45 achados congelados como aceitos**, quase todos da régua de nome de hook — enquanto estiverem no baseline, o check E não os cobra de ninguém.
2. **As 6 tags `archive/*` apontam para história órfã e não existem no remote.** Decidir se são empurradas (dando ao remote novo a rede antiga) ou descartadas junto com a história velha. Hoje elas resgatam branch só neste clone.
3. **Dois comentários de código afirmam versionamento que o `.gitignore` desmente** — `journal.py` ("versionado — é o veículo do conhecimento") e `plan_state.py` ("VERSIONADO no git de propósito"). Quem ler o código antes do `.gitignore` conclui que há backup onde não há.
4. **`askq-humanize.sh` e `scope-cop.sh` resolvem a MESMA pasta por expressões diferentes.** Invisível aqui (`CLAUDE_CONFIG_DIR` unset), divergente em qualquer máquina que a sete.
5. ✅ **Resolvida: o juiz de forma (B9) passou a julgar** — 50 `julgou`, 30 `passa`, 20 reprovas, contra 12 batidas `sem texto` e zero julgamentos na rodada anterior. O furo do `check_juiz_rodou` (aprovar um log que nunca julgou) continua existindo no código; deixou de ser o estado deste disco.
6. **Nada poda os contadores de B8 e B9**, e agora são **35** deles (15 + 20, contra 9 + 0). Os órfãos sem sufixo de B1 (`scope-cop.blockstreak`, `scope-cop.bypass`, de 2/jul) seguem fora do alcance da poda por causa do padrão com ponto.
7. ✅ **Fechada de novo: hoje há UM só ativo.** Os planos que já disputaram o posto (`2026-07-31-fechar-a-regua-e-publicar`, `2026-08-01-formato-de-plano-hierarquico`, `2026-08-06-a-metodologia-vira-mecanismo`, `autopsia-2026-08-09`) estão `done` ou `abandoned`, e o único `status: "active"` no disco é `2026-08-12-os-quatro-itens` — comando sem `--plan` resolve sozinho. A recusa segue armada para quando dois voltarem a coexistir: `pick_plan` diz *"há N planos ativos — diga qual"* em vez de adivinhar (`plan_state.py:pick_plan`). ⚠️ **Mas quatro planos estão abertos SEM status nenhum** (`2026-08-05-constituicao-e-onda-0`, `2026-08-05-portabilidade-windows`, `2026-08-06-doc-em-apresentacao`, `2026-08-06-os-quatro-issues-que-sobraram`): `pick_plan` só enxerga `status == "active"`, então esses quatro são invisíveis para a resolução automática — e não foram eles que reabriram o impasse, foi o plano da autópsia nascer `active` ao lado do que já estava. [confirmado — `plan_state.py:pick_plan` e `json.load` sobre os 31 arquivos]
8. **O `bypass.log` do B8 nunca existiu, e agora isso tem consequência em dois lugares.** Para o `check_bypass_teto`, ausência = conforme; para o `furos_da_regua`, ausência = `fontes` 1 em vez de 2 — a contagem de furos que o dono vê é hoje meia fonte, e o programa diz isso, mas só quem lê a linha inteira percebe.
9. ✅ **Resolvida: os cinco campos novos de A4 vivem em dado real.** Sobre os 31 planos, `requisito` e `pronto` aparecem em 568 tarefas (de 744) e `decidido` em 63 — a cobertura entre requisito e tarefa deixou de ser 0 de 0. **E os dois que faltavam saíram do zero:** `grupo` em 58 tarefas e `pendencia` em 10 — o campo que RECUSA o tique já rodou fora de teste.
10. **A página nº 100 de `.claude/visual/` viola a régua, e o limite aceito (A8) diz que não deveria.** O registro congela 99 páginas · 82 violando e declara *"a régua passa a valer para página nova"*; `regua_audit.py paginas` mede hoje 100 · 83, com a página nova de hoje 16:22 entre as reprovadas. Ou o gerador dela escapa da régua, ou o limite precisa ser reescrito — decidir qual.
11. ✅ **Resolvida: o segundo escritor de A4 ganhou gatilho.** `plugins/improve-workflow/lib/plano_saida.py` agora é invocado pelo passo 8 da `SKILL.md` do próprio plugin, que colhe o veredito do dono em `~/.claude/visual-state/latest.json` e grava só o aprovado — `grep -rn 'plano_saida' plugins/ --include='*.md' --include='*.sh' --include='*.json'` devolve duas linhas, a do `improve-workflow` e a do homônimo do `vistoria`. O laço página → plano fechou. **O destino deixou de ser adivinhado:** `--dir` é obrigatório e o programa recusa sem ele, porque padrão calculado da posição do arquivo cai dentro do cache do plugin na máquina de quem instala — o plano do dono nasceria na pasta do autor da skill.
12. **Nenhum verificador lê o `.claude/limites-aceitos.md` (A8).** Limite que deixou de valer não é acusado por ninguém: o arquivo declara o que o revoga, e quem confere é quem lembrar de rodar o comando.
