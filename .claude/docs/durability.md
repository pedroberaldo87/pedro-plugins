---
generated: 2026-07-31
generated-commit: a57ea6e
project: pedro-plugins
scope:
  - .gitignore
  - plugins/visual/lib/plan_state.py
  - .claude/hook-contract.baseline.json
  - .git/info/exclude
  - _shared/green-cache.sh
  - plugins/project-doc/lib/journal.py
  - plugins/bootstrap/hooks/hooks.json
  - plugins/bootstrap/hooks/session-sync.sh
  - plugins/bootstrap/hooks/lib/snapshot.sh
  - plugins/bootstrap/hooks/lib/git-sync.sh
  - plugins/intent-guard/lib/ledger.py
  - plugins/intent-guard/skills/intent-guard/SKILL.md
  - plugins/guardrails/hooks/scope-cop.sh
  - plugins/qa-loop/skills/qa-loop/SKILL.md
  - plugins/visual/server/visual_server.mjs
  - plugins/visual/skills/visual/config.default.json
  - plugins/visual/skills/visual/SKILL.md
  - plugins/context-guard/hooks/context-guard-reset.sh
  - plugins/guardrails/hooks/askq-humanize.sh
  - plugins/bootstrap/hooks/stop-prose-ceiling.py
doc-sig: pedro-plugins/.gitignore@gen=3.8#fab56966
---

# Durabilidade

Par obrigatório de **data-stores.md**: todo ativo listado lá tem um bloco aqui — inclusive (e principalmente) os que **não têm cobertura nenhuma**.

Leia a primeira seção antes de qualquer outra: o mecanismo de backup deste repo é uma coisa só, e ela cobre menos do que parece.

🔴 **Leia também esta advertência antes de usar qualquer seção do §2.** Em **2026-07-31**, cinco conjuntos de arquivos saíram do controle de versão (`git rm -r --cached` + regra no `.gitignore`) e **perderam a única cobertura que tinham**. Nenhum arquivo foi apagado: eles continuam no disco desta máquina, e só nela. As seções **§2.2, §2.4, §2.5 e §2.6 descreviam quatro deles como cobertos** — hoje descrevem o que eles *eram*, e apontam para **§3.15**, onde está a contabilidade de hoje. Foi decisão deliberada, não descuido; o preço está medido lá, sem maquiagem.

---

## 1 · O mecanismo: git + o remote no GitHub. Só isso.

[confirmado] Não há camada de backup própria. O que protege os ativos versionados é o **histórico do git local + o remote `origin`**:

```bash
$ git remote -v
origin	git@github.com:pedroberaldo87/pedro-plugins.git (fetch)
origin	git@github.com:pedroberaldo87/pedro-plugins.git (push)
```

- **Quem copia:** o próprio `git push` (manual, na maior parte dos casos — ver §1.1).
- **Para onde:** GitHub, repositório privado `pedroberaldo87/pedro-plugins`, via SSH.
- **Offsite:** **SIM.** O remote está fora da máquina de quem trabalha aqui. Perder o Mac não perde o que já foi pushado.
- **Frequência:** **a cada push.** Não há agendamento — a cópia acontece quando (e só quando) alguém empurra.
- **Retenção:** **histórico completo do git.** Nada é podado. [confirmado] `git rev-list --count HEAD` → **286** commits; o primeiro é `d743f10` de `2026-04-07T23:51:34-03:00` e continua alcançável.
- **Tamanho do que viaja:** [confirmado, 2026-07-31, `HEAD = ff32947`] `du -sh .git` → **37M**; `git ls-files | wc -l` → **251** arquivos rastreados.
  ⚠️ **Estes dois números andaram em direções opostas na mesma semana, e isso é o retrato exato do que o destrack faz.** Os rastreados caíram de **286** (2026-07-26) → **328** (2026-07-30) → **251**, porque **84** arquivos saíram do índice em 2026-07-31 (`HEAD` ainda carrega **335**). O `.git` subiu de **11M** → **31M** → **37M** no mesmo período. **Destrackear reduz o que o próximo commit leva; não reduz um byte do que o histórico já guarda.** Quem ler "o repo está mais leve" a partir do `ls-files` vai concluir o contrário do que o `du` mostra.

### 1.1 · O único push automático cobre um arquivo só

[confirmado] Existe **um** caminho de commit+push automático, e ele é deliberadamente estreito.

- **Gatilho:** hook `SessionStart` do plugin **bootstrap**, registrado em `plugins/bootstrap/hooks/hooks.json` apontando para `${CLAUDE_PLUGIN_ROOT}/hooks/session-sync.sh`. Isso é evidência de **ativação**, não só de existência do código.
- **Cadeia:** `session-sync.sh` → *fetch* barato → *pull --rebase --autostash* → `lib/apply.sh` → `lib/snapshot.sh` → `lib/git-sync.sh`.
- **Throttle:** `session-sync.sh` pula o ciclo completo se o último sync bem-sucedido foi há menos de `THROTTLE_SECONDS` (default `86400`, ou seja 24h) **e** o remote não avançou. Bypass pela env `PEDRO_PLUGINS_FORCE_SYNC`.
- **O que ele empurra:** **apenas** `plugins/bootstrap/config/manifest.json`. `lib/git-sync.sh` define `MANIFEST_REL="plugins/bootstrap/config/manifest.json"` e commita com `git commit --only "$MANIFEST_REL"` — nenhum outro arquivo é estagiado, por design.
- **Guarda anti-propagação:** em `session-sync.sh`, se `apply.sh` sair com código ≠ 0, o snapshot é **pulado inteiro** — senão o manifest regenerado a partir de um estado degradado seria pushado como "nova verdade" para as outras máquinas.
- ✅ **O segundo modo de apagamento silencioso — chave de topo mantida à mão — foi fechado de vez, e a correção foi INVERTER a lista.** O `snapshot.sh` **regenera** `manifest.json` inteiro a partir do estado vivo (o `jq -n` monta `version`, `description`, `marketplaces` e nada mais), então qualquer chave de topo escrita à mão sumia na regeneração. Aconteceu com a chave `skills` em **2026-07-30, minutos depois de criada**. O bloco `PRESERVED_KEYS` (`plugins/bootstrap/hooks/lib/snapshot.sh`, imediatamente após o `jq -n` do `NEW_MANIFEST`) relê o manifest do disco e faz `. + $keep` no JSON regenerado — o valor antigo sobrevive.
  - [confirmado no código, commit `352e8d5`] **A primeira correção enumerava o que SALVAR (`jq '{skills}'`) e por isso consertava só o caso, deixando a classe viva** — qualquer outra chave mantida à mão seguia sumindo no primeiro `SessionStart`. Hoje a lista é `GENERATED_KEYS='["version","description","marketplaces"]'` e o filtro é o complemento dela: `with_entries(select(.key as $k | $gen | index($k) | not))`. **Consequência de durabilidade: a proteção deixou de ser por enumeração do protegido e passou a ser por regra** — chave nova mantida à mão sobrevive sem ninguém precisar lembrar de vir aqui; só quem passa a **gerar** uma chave nova precisa mexer na lista. A direção do default virou: o desconhecido agora é preservado, não apagado.
  - Estado hoje: [confirmado nesta sessão] `jq 'keys'` no manifest → `description`, `marketplaces`, `skills`, `version`; `marketplaces` tem **7** entradas e **29** plugins somados. A própria chave `skills` carrega a nota `"snapshot.sh preserva esta chave (ver o bloco PRESERVED_KEYS)"` — a justificativa viaja com o dado.
  - Coberto por teste: `plugins/bootstrap/hooks/test_bootstrap_hooks.sh` roda o snapshot contra um manifest com **uma chave inventada** e afirma que ela sobrevive, além da checagem específica de `skills`. O teste mira a regra, não o caso.
- ✅ **O furo que custou dado em 2026-07-30 foi fechado, e a causa-raiz é externa a este repo: `claude plugin list` devolve saída INCOMPLETA de forma intermitente.** A guarda anterior cobria *apply falhou*; não cobria *apply passou e a enumeração voltou incompleta* — foi assim que o commit `2bbc4ac` do próprio `session-sync` derrubou o manifest (o histórico do arquivo mostra a oscilação: **29 → 27 → 29** só entre `c723713` e `HEAD`, sem ninguém instalar ou desinstalar nada). **A flakiness é reprodutível — derivação rodada nesta sessão, cinco chamadas seguidas:**
  ```bash
  for i in 1 2 3 4 5; do claude plugin list 2>/dev/null | grep -c "Status:"; done
  # 49  32  21  49  49
  ```
  - **O conserto é mudar a NATUREZA do depósito: o snapshot passou a ser ADITIVO.** Depois de montar o manifest novo, `snapshot.sh` faz união com o manifest do disco por `name` dentro de cada marketplace (`group_by(.name) | map(if length > 1 then .[1] else .[0] end)`) — entrada nova entra, o `enabled` da amostra da vez vence, **entrada ausente FICA**. O comentário no código diz por quê: não há como distinguir *"desinstalado"* de *"a CLI não listou desta vez"*, então a única leitura segura é a que nunca remove. **Desinstalar de verdade virou edição explícita do manifest.**
  - Rede sobre a rede: o script compara os totais e, se o resultado ainda assim encolher, loga `warning: manifest encolheu N -> M (não deveria: a união é aditiva)`. É alarme, não bloqueio — a escrita segue.
  - **Consequência de durabilidade:** o manifest é o único artefato de recuperação de máquina nova (§2.1 cobre o *código*, não a *lista de terceiros*). Ele deixou de ser *regenerado do zero a cada sessão* e passou a ser *acumulado* — a diferença entre um retrato que só vale se a foto saiu inteira e um registro que só cresce. O modo de falha residual inverte de sinal: antes o risco era perder plugin de verdade; agora é o manifest reter plugin que já não existe. **Reter demais é o erro barato; apagar em silêncio era o caro.**

**Consequência de durabilidade:** para **todo o resto do repo** (código dos plugins e docs), o push é **manual**. Não existe automação que salve trabalho não commitado. ⚠️ **Até 2026-07-30 esta frase incluía "journal, grafo" — e hoje não pode mais incluir:** para os depósitos de §3.15 não é que o push seja manual, é que **não há push nenhum a dar**. Eles saíram do índice; nenhum `git push`, manual ou automático, os leva.

[relatado — finding de handoff `bb980291af9d43a3`, coerente com o comportamento do git] "PRD é snapshot sobrescrito MAS untracked não tem rede": arquivo untracked não tem histórico nenhum. Desde 2026-07-28 os dois casos que ilustravam isto saíram: `pi-plugins/` passou a ser **ignorado de propósito** (`.gitignore:47` após a reescrita de 2026-07-31, ver `architecture.md §12.2`) e o `config.json` do `/visual` **mudou de casa** para `~/.claude/visual-state/` (§3.9). A regra segue valendo — untracked continua sem rede —, só não há mais anomalia neste repo ilustrando-a.

### 1.2 · O que NÃO existe (verificação mecânica negativa)

Rodado nesta sessão, na raiz do repo:

```bash
$ crontab -l
crontab: no crontab for <usuario>

$ find . -path ./pi-plugins -prune -o \( -name "*.plist" -o -name "*.timer" -o -name "*.service" \) -print
(nenhuma saída)

$ grep -rniE "crontab|systemd|launchd|launchctl|pg_dump|mysqldump|restic|borg" \
    --include="*.sh" --include="*.py" --include="*.json" --include="*.md" \
    plugins/ _shared/ scripts/ .claude/hooks/
```

[confirmado] **Não há crontab, nem unit/timer de systemd, nem plist do launchd, nem script de dump/rsync/restic/borg neste repo.** Todas as ocorrências dos termos acima no grep são *prosa*: `plugins/fallow/lib/audit.py` e `plugins/fallow/skills/fallow/SKILL.md` falam de cron/systemd como *gatilhos externos que a análise estática não enxerga*; `plugins/project-doc/skills/project-doc/references/detection-matrix.md` e `.../templates.md` listam esses termos como *o que a mineração de doc deve procurar em outros projetos*; `plugins/bootstrap/config/settings-defaults.json` tem `"Bash(rsync*)"` como **permissão** concedida ao agente, não como backup configurado.

Ou seja: **nenhuma cópia agendada. A única cópia é o push.**

---

## 2 · Ativos COM cobertura

Cobertura aqui significa exatamente uma coisa: *está rastreado pelo git e existe no remote*.

### 2.1 · Código dos plugins e catálogo do marketplace
`plugins/**`, `.claude-plugin/marketplace.json`, `scripts/sync-shared.sh`, `_shared/**`

- **Cobertura:** git + GitHub. [confirmado] `git ls-files | wc -l` → **251** arquivos.
- **Retenção:** histórico completo (**286** commits).
- **Insubstituível?** Sim — é o produto. Mas coberto. ✅ **É a única classe do §2 que atravessou 2026-07-31 intacta:** o destrack não tocou em `plugins/**`, `_shared/**` nem no catálogo. O que saiu foi memória de trabalho, não código.
- **RPO/RTO:** ver §4.

### 2.2 · ~~Journal do project-doc — `.claude/.project-doc/`~~ → **SAIU DESTA SEÇÃO em 2026-07-31**
`findings.jsonl`, `ledger.json`, `lint-allow.txt`

🔴 **Cobertura hoje: NENHUMA.** Os três arquivos foram destrackeados e a pasta inteira entrou no `.gitignore` (**linha 35**). A contabilidade da perda está em **§3.15**. [confirmado nesta rodada]

```bash
git ls-files .claude/.project-doc/ | wc -l                        # 0
git ls-tree -r --name-only HEAD -- .claude/.project-doc | wc -l   # 3
git check-ignore -v .claude/.project-doc/findings.jsonl
#   .gitignore:35:.claude/.project-doc/	.claude/.project-doc/findings.jsonl
```

- **O que valia até 2026-07-30, e por que a mudança dói:** `plugins/project-doc/lib/journal.py`, cabeçalho da seção de estado (acima de `state_dir()`), diz literalmente *"Estado: `.claude/.project-doc/` (versionado — é o veículo do conhecimento)"*. ⚠️ **Essa linha continua no código e hoje descreve algo que não é mais verdade** — o `.gitignore` a contradiz. Transcripts de sessão são locais e não viajam entre máquinas; o journal era o único carona do conhecimento minerado, e **agora não viaja com ninguém**.
- **Volume:** [confirmado 2026-07-31] `wc -l .claude/.project-doc/findings.jsonl` → **898** linhas; `du -sh .claude/.project-doc/` → **1,4M**.
- **Barreira de secret — esta continua de pé:** `journal.py:scrub()` (scorer em 4 camadas) roda na escrita de **todo** evento (`run_update`, `run_invalidate`, `run_curate`, `run_adopt`). Ela nunca dependeu do git; roda no append. Valor-secreto vai para o cofre (§3.8); o journal guarda só nome/host/contexto.
- **Nota de reconciliação, e ela girou 180°:** existe um finding antigo (`170c2284699295b0`) dizendo *"findings.jsonl cru = cache fora do git"*. Ele foi invalidado em 2026-07-26 por contradizer o `git ls-files` da época. **Desde 2026-07-31 a descrição dele voltou a bater com o disco** — não porque estivesse certo, mas porque a decisão mudou. Fica registrado como aviso: *finding morto que "volta a fazer sentido" não ressuscita; o que mudou foi o mundo, e a evidência tem que ser re-derivada.*

### 2.3 · Documentação gerada — `.claude/docs/*.md`, `.claude/CLAUDE.md`

- **Cobertura:** git + GitHub. [confirmado — `git ls-files .claude/docs/` devolve os cinco `.md` nesta rodada] **A doc atravessou 2026-07-31 coberta**; foi o insumo dela que não atravessou.
- 🔴 **Regenerável? A resposta MUDOU, e para pior.** Até 2026-07-30: *"parcialmente — `/project-doc` FULL re-minera, mas a curadoria vive no journal de §2.2, também versionado. O par funciona."* **O par quebrou:** o journal saiu do git (§2.2, §3.15). Hoje a doc é o **único** artefato coberto do sistema de documentação, e ela é a *saída*, não a *entrada*. Perder a máquina deixa um clone com toda a doc curada e **nenhuma das 898 falas de onde ela saiu** — a próxima re-mineração começaria do zero, sem as invalidações e curadorias acumuladas. **Estado versionado sem insumo versionado é uma foto sem o negativo.**
- **Backups locais da doc:** `.claude/.project-doc/backups/` continua fora do git — só que **agora pela regra do diretório inteiro** (`.gitignore:35`), não mais por uma linha própria. ⚠️ **A justificativa antiga citada aqui virou letra morta:** ela dizia *"o journal/ledger em .project-doc/ SÃO versionados; só os backups não"*, e essa distinção deixou de existir. O backup segue sendo rede de segurança de um run, não ativo; o que sumiu foi o contraste que dava sentido à frase.

### 2.4 · ~~Grafo do graphify — `graphify-out/`~~ → **SAIU DESTA SEÇÃO em 2026-07-31**

🔴 **Cobertura hoje: NENHUMA.** O diretório inteiro saiu do índice e o `.gitignore` ganhou uma linha só, sem exceções (**linha 28**, `graphify-out/`). Detalhe em **§3.15**. [confirmado nesta rodada]

```bash
git ls-files graphify-out/ | wc -l                        # 0
git ls-tree -r --name-only HEAD -- graphify-out/ | wc -l  # 40
find graphify-out -type f | wc -l                         # 1119  (no disco, intacto)
du -sh graphify-out                                       # 76M
```

- **O que era rastreado até 2026-07-30:** `graph.json`, `manifest.json`, `GRAPH_REPORT.md`, `cost.json`, `.graphify_labels.json`, na raiz de `graphify-out/`. Os cinco saíram juntos.
- ✅ **A pegadinha que esta seção denunciava foi resolvida — e por acidente feliz.** O texto anterior media que os snapshots datados estavam no `.gitignore` **e mesmo assim rastreados** (`graphify-out/20*/` não desrastreia o que já entrou), produzindo retenção histórica **acidental, não desenhada**. O `git rm -r --cached` do diretório inteiro varreu isso junto: `git ls-files graphify-out/ | grep -c '^graphify-out/20'` → **0**, contra **35** que o `HEAD` ainda carrega. **A retenção acidental acabou; nenhuma retenção desenhada tomou o lugar dela.**
- **Regenerável?** Sim: `graphify update . --force` (extração AST, sem LLM). É por isso que este é **o único dos cinco destracks cuja perda custa CPU, não conhecimento**. ⚠️ **Com uma exceção nomeada:** os *labels de comunidade* (`.graphify_labels.json`, **403** chaves, 10.939 bytes) só se regeneram com LLM — e saíram do git junto com o resto. Dentro de um depósito descartável, esse arquivo é a parte que não é.
- **Consequência de retenção:** o que era protegido por acidente virava histórico permanente; agora **nem por acidente**. Do ponto de vista de restauração, o caminho de recuperação deixou de ser `git checkout` e passou a ser rodar o `graphify` de novo — o que só funciona porque o *corpus* (o código) segue coberto por §2.1.

---

### 2.5 · ~~`.claude/ata/` — atas de sessão~~ → **SAIU DESTA SEÇÃO em 2026-07-31**

🔴 **Cobertura hoje: NENHUMA.** `.gitignore:38` (`.claude/ata/`). Contabilidade em **§3.15**. [confirmado nesta rodada]

```bash
git ls-files .claude/ata | wc -l                        # 0   (eram 24 em 2026-07-26, 28 em 2026-07-30)
git ls-tree -r --name-only HEAD -- .claude/ata | wc -l  # 30
ls -1 .claude/ata | wc -l                               # 30  (no disco)
du -sh .claude/ata                                      # 1,8M
```

- **Natureza:** insubstituível — o transcript de origem é local e não viaja. 🔴 **Era o item mais simples desta seção: coberto, sem ressalva, sem pegadinha.** Passou direto de "protegido pelo git" para "existe num disco só", sem estado intermediário. **Dos cinco destracks, é o que tem a leitura de risco mais limpa e mais dura.**
- **Quem copia hoje:** **ninguém.** Não há push, não há cópia agendada (§1.2), não há regenerador.
- **Restauração testada em:** NUNCA TESTADA — e agora não há de onde restaurar.

### 2.6 · ~~`<repo>/.claude/plans/*.plan.json` — planos de implementação ticáveis~~ → **SAIU DESTA SEÇÃO em 2026-07-31**

🔴 **Cobertura hoje: NENHUMA.** `.gitignore:39` (`.claude/plans/`). Contabilidade em **§3.15**. [confirmado nesta rodada]

```bash
git ls-files .claude/plans/ | wc -l                        # 0   (eram 6 em 2026-07-30)
git ls-tree -r --name-only HEAD -- .claude/plans | wc -l   # 8
ls -1 .claude/plans/*.plan.json | wc -l                    # 9   (no disco)
du -sh .claude/plans                                       # 92K
wc -l .claude/plans/*.plan.json | tail -1                  # 1476 total
```

- ⚠️ **Este item era, até 2026-07-30, o contraste didático deste doc: "não confundir com `~/.claude/plans/` (§3.3) — mesmo nome, cobertura oposta". O contraste ACABOU.** Os dois depósitos homônimos têm hoje a mesma cobertura: nenhuma. O `visual` v1.5.0 criou este justamente porque o de lá não protegia nada (§3.3), e o argumento deixou de valer para ele mesmo.
- **Volume:** **9 arquivos**, 92K, 1476 linhas — eram 1 arquivo / 8,0K em 2026-07-27 e 6 / 60K em 2026-07-30. Sem poda nem arquivamento; plano encerrado sai do `plan_state.py open` mas fica no disco. **Ao ritmo de 8 planos em 4 dias, é o depósito que mais rápido ganha arquivos neste repo — e agora cresce fora de qualquer cópia.**
- 🔴 **O que a perda custa não é o plano, é a PROVA.** Nos 9 arquivos o nº de passos `done` é idêntico ao nº de `evidence` (derivado nesta rodada, arquivo a arquivo). Isso era o que dava valor ao backup: o que estava no git não era lista de intenções, era registro do que foi feito **com a prova junto**. Reconstruir o plano do transcript é o mecanismo lossy que este depósito veio substituir — em `extract_ata.py`, `last_plan` guarda só `"excerpt": txt[:1200]` —, e **o transcript não guarda `evidence` nenhum**.
- **Insubstituível?** Sim, e agora **sem a ressalva "mas coberto"** que esta linha carregava.
- **Restauração testada em:** NUNCA TESTADA — e agora não há de onde restaurar.

---

### 2.7 · `.claude/hook-contract.baseline.json` — retrato do contrato dos hooks

- **Quem copia:** o próprio git. [confirmado — `git ls-files .claude/` inclui o arquivo nesta rodada]
- **Para onde:** `origin` (GitHub). **Offsite:** sim. **Frequência:** a cada push · **Retenção:** histórico completo.
- **Regenerável?** O JSON, sim (`python3 scripts/hook_contract.py --json > …`). O **julgamento** que ele carrega — quais achados foram aceitos e por quê — **não**: vive em `patterns.md §5.3`, também versionado. Perder um sem o outro deixa o gate sem critério ou sem memória.
- **Restauração testada em:** NUNCA TESTADA.

---

### 2.8 · tags `archive/<branch>-<data>` — a rede do `/branches`
**Era a exceção desta seção; deixou de ser.** Corresponde a `data-stores.md §A5b`.

- **O que é:** uma tag por branch apagada, criada por `plugins/branches/lib/branch_state.py:cmd_prune` **antes** do `git branch -D` (e o prune aborta se não conseguir criá-la). É o que torna a volta um comando: `git branch <nome> archive/<branch>-<data>`.
- ✅ **Cobertura real: as 6 estão no remote. Medido nesta sessão, não inferido.**
  ```bash
  git tag -l 'archive/*' | wc -l                    # 6   (local)
  git ls-remote --tags origin | grep -c 'archive/'  # 6   (remote)
  ```
  As 6 foram empurradas em 2026-07-30, depois que uma auditoria mediu 0 no remote. O buraco que esta seção descrevia está fechado.
- ⚠️ **O que continua aberto é o automatismo:** `git push` sem `--tags` não leva tag, e o `cmd_prune` não empurra — ele cria a tag e para aí. As 6 de hoje só estão lá porque alguém empurrou à mão. A **próxima** branch apagada volta a nascer só local.
- **Consequência:** enquanto o `cmd_prune` não empurrar sozinho (`--follow-tags` ou um push explícito), toda tag nova é local até alguém lembrar. Perder este Mac entre o prune e o push perde a rede daquela branch — e ela cobre exatamente o caso em que o erro custa trabalho (branch `equivalent`, que o git considera não-mergeada e só sai com `-D`).
- **Insubstituível?** Sim, dentro do seu escopo: a tag aponta para um commit que, sem ela, fica órfão e some no `gc`. Não há regenerador.
- **Retenção própria:** nenhuma — uma tag por branch apagada, acumulando. Aceito: são bytes, e o valor é durar.
- **Restauração testada em:** NUNCA TESTADA.
- **O conserto é de um comando** (`git push --tags`, ou `--follow-tags` no fluxo do prune). Fica registrado aqui como decisão pendente, não como justificativa: **não existe nenhum arquivo deste repo dizendo por que a rede de resgate pode ficar só local.**

---

## 3 · Ativos SEM cobertura

Nenhum dos itens abaixo está no git nem em qualquer cópia agendada. A distinção que importa é entre **justificativa registrada no código** e **ausência de justificativa**.

### 3.1 · `~/.claude/green-suite/` — cache de suite verde
**SEM COBERTURA — justificativa VÁLIDA (regenerável, com TTL).**

- **O que é:** registro TSV `scope\tepoch\tiso-ts\twriter` por (projeto × tree-hash), dizendo "a suite passou verde neste estado exato da árvore".
- **Justificativa registrada:** `_shared/green-cache.sh`, cabeçalho — *"Fail-open na direção SEGURA: qualquer erro → MISS → a suite roda"*. Perder o cache **não perde informação**: custa uma rodada de teste.
- **Retenção própria:** `GREEN_SUITE_TTL_SECS` default `86400` (24h) aplicado **por linha** (epoch gravado no registro, não mtime do arquivo), mais poda de arquivos com mais de 7 dias em `green_cache_mark()`: `find "$GREEN_SUITE_DIR" -type f -mtime +7 -delete`.
- **Onde mora:** `GREEN_SUITE_DIR` default `$HOME/.claude/green-suite`. [confirmado] `du -sh` → **136K**.
- **Restauração:** não se aplica — o dado expira por design.

### 3.2 · `<projeto>/.claude/intent/` — ledger do intent-guard
**SEM COBERTURA — sem justificativa registrada.** ⚠️ **Insubstituível.**

- **O que é:** caderno **append-only** dos pedidos **verbatim** do usuário. Eventos `raw` / `classify` / `verdict` / `baixa` em `ledger.jsonl`, mais os arquivos `audit-<epoch>.json`, seus marcadores `.applied` e — desde o intent-guard v0.5.0 — o sidecar `<auditoria>.escopo`, que tem cobertura própria em **§3.14** (regra da gen 3.8: depósito listado em `data-stores.md` tem bloco aqui).
- **Onde mora:** `plugins/intent-guard/lib/ledger.py:intent_dir()` → `<git-root>/.claude/intent/`. Neste repo: `.claude/intent/`. Só cai no fallback `~/.claude/intent/<slug>/` quando não há project root.
- **Por que está fora do git:** `ledger.py:ensure_exclude()` grava a linha `.claude/intent/` em `.git/info/exclude` (ignore **local**, para nunca tocar o `.gitignore` versionado do repo). [confirmado] `git check-ignore -v .claude/intent/ledger.jsonl` → `.git/info/exclude:18:.claude/intent/`.
- **Justificativa:** **não há.** O comentário de `ensure_exclude()` explica *por que usa `.git/info/exclude` em vez do `.gitignore`* — mecânica, não política. `plugins/intent-guard/skills/intent-guard/SKILL.md` afirma que o ledger é *"invisível pro git via `.git/info/exclude`"* e para por aí. Nenhum arquivo deste repo diz por que o verbatim do usuário pode ser perdido.
- **Por que é insubstituível:** a fonte original do texto é o transcript da sessão (`~/.claude/projects/…/*.jsonl`), que é **local e não viaja**. O ledger é a única forma persistida do que foi pedido, e os `verdict`/`baixa` (o que foi entregue e com que evidência) **não têm outra fonte**.
- **Volume:** [re-medido 2026-07-31, `HEAD = ff32947`] `du -sh .claude/intent` → **476K**; `ledger.jsonl` com **460** linhas; **27** `audit-*.json`, **16** `.applied` e **1** `.escopo`. O fallback global `~/.claude/intent` (de outros projetos) segue em 264K.
- ⚠️ **O par 27/16 é sinal de durabilidade, não só de volume.** **11 auditorias nunca viraram `.applied`** — o veredito foi produzido, custou um subagente, e nunca chegou ao ledger. O que se perde ali não é arquivo (os 11 `.json` estão no disco): é o **elo** entre o pedido e o julgamento dele. O ledger acumula **42 pedidos vivos** (`p-12` … `p-75`) contra 44 `verdict` e 33 `baixa`. Perder este diretório hoje perderia, além do verbatim, a única evidência de que aquelas 11 auditorias aconteceram. [confirmado — contagens e `fold()` executados nesta rodada]
- **Retenção própria:** nenhuma — o diretório só cresce, nos três tipos de arquivo.
- **Restauração:** **NUNCA TESTADA** (§5). Vai para o resumo de exposição.

### 3.3 · `~/.claude/plans/` — planos de implementação
**SEM COBERTURA — sem justificativa registrada.** ⚠️ **Insubstituível.**

- **Volume:** [confirmado 2026-07-31] `find ~/.claude/plans -maxdepth 1 -type f | wc -l` → **213** arquivos; `du -sh` → **2,7M**. Eram 226 / 2,9M em 2026-07-26 — encolheu sozinho, ver o TODO em `data-stores.md`.
- **Quem escreve:** [confirmado] **ninguém neste repo.** `grep -rn "claude/plans" plugins/ scripts/ _shared/ .claude/hooks/` devolve **três** ocorrências, todas de **leitura ou de instrução para não ler**: `plugins/qa-loop/skills/qa-loop/SKILL.md` (a flag `--plan` procura `.claude/plans/*.md`), `plugins/principles/skills/principles/SKILL.md` (procura a seção "Princípios de Sistema" em `.claude/plans/*.md`) e `plugins/visual/hooks/pre-exitplan-visualize.sh` (*"não busque em `~/.claude/plans/`"*). [inferido] O produtor é o próprio harness do Claude Code, fora do escopo deste repo — ver `todos`.
- **Por que é insubstituível:** o plano aprovado é a **âncora** contra a qual o `/qa-loop` classifica findings em *implementação / plan-drift / plano-falho*. Sem o plano, o loop cai em "review sem plano" — o próprio SKILL.md avisa que fica *"sem âncora"*. Perder os 213 planos degrada permanentemente a capacidade de auditar o que já foi entregue.
- **Justificativa:** **não há** — nem podia haver: este repo não é dono do diretório.
- **Retenção própria:** desconhecida (produtor não identificado). Nenhuma poda observada.
- **Restauração:** **NUNCA TESTADA** (§5). Vai para o resumo de exposição.
- 🔴 **A mitigação parcial que existia aqui foi REVERTIDA em 2026-07-31.** Desde o `visual` v1.5.0, o plano que ESTE marketplace escreve morava em `<repo>/.claude/plans/*.plan.json`, versionado — precisamente porque `~/.claude/plans/` não tem cobertura. **Esse depósito foi destrackeado** (§2.6, §3.15): `git ls-files .claude/plans/ | wc -l` → **0** nesta rodada. Os **213** arquivos do harness continuam expostos e agora os **9** planos do marketplace estão expostos junto. **Não sobrou nenhum plano de implementação coberto neste repo.** [confirmado]

### 3.4 · `~/.claude/qa-loop/journal/` — aprendizado cross-projeto do qa-loop
**SEM COBERTURA — sem justificativa registrada.** ⚠️ **Insubstituível.**

- **Arquivos:** `learnings.md` e `telemetry.jsonl`, ambos citados em `plugins/qa-loop/skills/qa-loop/SKILL.md` §Journal AGÊNTICO e em `EXAMPLE-JOURNAL.md`.
- **O que é:** `telemetry.jsonl` = 1 linha append-only por sessão de QA, agregado **cross-projeto**, para calibrar nº de loops e a rubrica. `learnings.md` = onde o **processo** de QA acertou/errou, com AÇÃO concreta para "futuro-eu"; acumula ao longo do tempo.
- **A única coisa registrada:** o SKILL.md diz que o agregado *"sobrevive a reinstalar o plugin"* — isso justifica **morar em `~/.claude/` em vez de dentro do plugin** (a regra do repo), **não** justifica ausência de backup. As duas coisas são diferentes e só a primeira está escrita.
- **Por que é insubstituível:** é conhecimento destilado ao longo de muitas sessões, sem fonte upstream. A camada por-projeto (`<projeto>/.claude/qa-loop/`) é gitignored (`.gitignore`: *"relatórios e telemetria de sessões de review (local, regenerável)"*) — mas a **camada agregada** não tem essa justificativa.
- **Volume:** [confirmado] `du -sh ~/.claude/qa-loop` → 64K.
- **Restauração:** **NUNCA TESTADA** (§5). Vai para o resumo de exposição.

### 3.5 · `~/.claude/visual-state/` — estado do live-sync do /visual
**SEM COBERTURA — justificativa VÁLIDA (efêmero por sessão, regenerável).**

- **O que é:** `<session>.json` por sessão, reescrito a cada POST do browser, mais `latest.json` apontando para a sessão mais recente. Escrito por `plugins/visual/server/visual_server.mjs` (`STATE_DIR = path.join(os.homedir(), '.claude', 'visual-state')`).
- **Justificativa:** é o canal de ida-e-volta browser→Claude de **uma sessão viva**. Terminada a sessão, o valor é zero; a página HTML de origem mora em `.claude/visual/` (também gitignored, com a justificativa *"Artefatos efêmeros de sessão (regeneráveis, local only)"*).
- **Volume:** [confirmado] `du -sh` → 1,2M — acumula porque nada poda.
- **Retenção própria:** nenhuma. [inferido] Isso é acúmulo, não risco: os arquivos antigos não guardam nada que alguém precise recuperar.

### 3.6 · `~/.claude/guardrails/` — logs e freios dos vigias de edição e de pergunta
**SEM COBERTURA — justificativa PARCIAL (retenção deliberada, mas de tamanho, não de durabilidade).**

- **Arquivos do scope-cop:** `scope-cop.mode` (uma linha; **três valores desde 2026-07-30: `deny` default | `warn` | `off`**), `scope-cop.log` (auditoria), `scope-cop.blockstreak` (nº de BLOCKs seguidos), `scope-cop.bypass`. Todos declarados no cabeçalho de `plugins/guardrails/hooks/scope-cop.sh`.
- ⚠️ **O valor `warn` muda o que a AUSÊNCIA de log significa, e isso é fato de retenção.** [confirmado nesta rodada] O arquivo hoje contém `warn`; o log tem **847** linhas e as três últimas em modo `deny` são três `BLOCK` seguidos em **2026-07-02**, seguidas de **28 dias sem uma única linha** até `2026-07-30 17:14:34`, já em `warn`. Em `off` o hook sai antes de logar — então o `off` não deixa registro nenhum, e um log parado é indistinguível de "não houve edição". O modo `warn` existe justamente para trocar silêncio por linha: o gate segue observando e gravando mesmo sem bloquear. **Para quem lê este depósito: buraco no `scope-cop.log` é evidência de gate desligado, não de calmaria.**
- **Arquivos do vigia da pergunta** (`askq-humanize.sh`, guardrails 1.3.0, 2026-07-30): `askq.log` (input cru + violações, uma entrada por invocação) e `askq.count.<session_id>` (cap de 3 devoluções, poda de 1 dia). ✅ **O `askq.log` PASSOU a existir** — 4.762 bytes, **5** invocações, **3 com `rc=1`** (devolvidas) e **2 com `rc=0`** [confirmado nesta rodada]. Nenhum `askq.count.*` no disco: a poda de 1 dia já levou os de ontem.
- **Retenção própria registrada:** os dois scripts podam o log. O scope-cop: acima de 5000 linhas mantém as últimas 2000, com o comentário *"evita que o scope-cop.log cresça indefinidamente — chegou a passar de 450 KB"*. O `askq-humanize.sh` copia a forma com teto menor (3000 → últimas 1000). É decisão explícita de **descartar** histórico antigo; nesse sentido a perda já é aceita por design.
- **`mode` / `blockstreak` / `askq.count.*`:** recriáveis à mão em um comando. Sem exposição real. ⚠️ Uma nuance nova: perder o `mode` **não** devolve o estado atual, devolve o default `deny` — que é mais estrito que o `warn` de hoje. A perda é segura na direção certa, mas não é neutra.
- ⚠️ **O `askq.log` deixou de ser prova pendente — a medição foi feita.** Ele era a única evidência de que o `PreToolUse` dispara no `AskUserQuestion`; as 5 entradas de hoje provam o disparo **e** provam que o gate julga (3 de 5 devolvidas). Apagar `~/.claude/guardrails/` agora não custa mais verificação, só o insumo bruto pra afinar as réguas do `askq_lint.py`. Caiu na regra geral de descartável.
- ⚠️ **O diretório deixou de ter um caminho só, e os dois escritores discordam.** Na guardrails v1.5.0 o `scope-cop.sh` passou a resolver `HOOK_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/guardrails"` — a mesma expressão do `conformance.py:CLAUDE_DIR` —, enquanto o `askq-humanize.sh` continua em `$HOME/.claude/guardrails` fixo [confirmado — `grep -n "HOOK_DIR=" plugins/guardrails/hooks/*.sh` nesta rodada]. **Consequência de durabilidade:** numa máquina com `CLAUDE_CONFIG_DIR` setado, "fazer backup de `~/.claude/guardrails`" cobre o vigia da pergunta e **perde** o do scope-cop, sem nenhum sinal de erro. É a mesma armadilha de §3.13 (escritor e leitor em pastas diferentes não dá erro, dá relatório verde falso) — e aqui ela ainda está aberta, de um dos dois lados. Nesta máquina a env var está unset, então as duas expressões coincidem e a divergência é invisível.
- ✅ **O `.mode` homônimo inerte em `~/.claude/hooks/` foi apagado** no `32cfe28`, e a classe virou checagem (`conformance.py:check_gates_enganosos` acusa `.mode` de mesmo nome em pastas distintas). Para este doc importa o efeito: **sumiu um arquivo que parecia estado e não era** — quem o copiasse num backup estaria preservando lixo que não influencia comportamento nenhum.
- **Volume:** [re-medido 2026-07-30 à noite] `du -sh ~/.claude/guardrails` → **464K** (era 388K poucas horas antes, e 376K na rodada anterior). O `scope-cop.log` foi de **847 para 916 linhas**, com **5 linhas `WARN`** — as primeiras que o ramo de aviso produziu. **O depósito está crescendo porque o gate voltou a observar**, o que inverte a leitura de risco: aqui o crescimento é o sinal saudável, e o log parado é que era o problema.

### 3.7 · Kill-switches: `~/.claude/intent-guard/mode`, `~/.claude/context-guard/mode`
**SEM COBERTURA — justificativa VÁLIDA (trivialmente recriável).**

- Arquivo de uma linha cada. [confirmado] `du -sh` → **0B** em ambos hoje (ou seja, nem existem com conteúdo — o default vale).
- Perda = voltar ao default. Não há informação a recuperar.

### 3.8 · Cofre de secrets — iCloud
**COBERTURA PARCIAL: iCloud sim, git nunca (por design).**

- **Onde mora:** `plugins/project-doc/lib/journal.py:cofre_paths()` resolve, em ordem: env `PROJECT_DOC_COFRE_DIR` → `~/Library/Mobile Documents/com~apple~CloudDocs/Cofre` → fallback local `<projeto>/.claude/secrets/_local_cofre`. [confirmado] O diretório iCloud existe nesta máquina, e `.claude/secrets/ops.env` é um symlink para `…/Cofre/pedro-plugins-<hash8>.env`.
- **Nome do arquivo:** slug por **path completo** do projeto (`basename + sha1(abspath)[:8]`) — dois projetos homônimos não colidem.
- **Cobertura efetiva:** o iCloud sincroniza e replica offsite. [inferido] Não foi verificado nesta rodada se o iCloud está com sync ativo/saudável para essa pasta.
- **Fora do git por design:** `journal.py:stash_secrets()` chama `ensure_gitignore(project_root, ".claude/secrets/")` **antes** de escrever — a proteção precede o dado. `.gitignore` tem a linha `.claude/secrets/`.
- **Volume:** [confirmado] `wc -l` no arquivo do cofre → **15** linhas (só a contagem; o conteúdo **não foi lido**).
- **Justificativa registrada:** `journal.py` cabeçalho, RF5 — *"Scrubber + cofre: roda na escrita do journal (barreira p/ o git). Move o VALOR-secreto pro cofre (iCloud), preserva nome/host/porta/contexto."* Válida e correta.
- [relatado — findings `a8b071200fb5e891` e `2461e66fcb89ba7c`] A escolha do iCloud e da pasta dedicada `Cofre` veio de decisão do dono do repo em sessão; o código de hoje confirma ambas.

### 3.9 · `~/.claude/visual-state/config.json` — preferência do `/visual`
**SEM COBERTURA — justificativa VÁLIDA (preferência local, semeável do default versionado).**

**A anomalia anterior foi RESOLVIDA em 2026-07-28.** O arquivo morava em
`plugins/visual/skills/visual/config.json`, untracked **e** não-ignorado — nem versionado, nem
deliberadamente fora. Pior: era **estado mutável dentro do plugin**, o que a convenção do repo
proíbe (`architecture.md §11`), então o `auto_mode` voltava em silêncio para `true` a cada bump
do plugin, porque `${CLAUDE_PLUGIN_ROOT}` é cache reescrito.

- [confirmado neste run] `ls plugins/visual/skills/visual/config.json` → *No such file or
  directory*; o estado vive agora em `~/.claude/visual-state/config.json`, ao lado dos
  `<session>.json`/`latest.json` do daemon (§ do live-sync). `git status` não lista mais nada.
- **Semente:** `plugins/visual/skills/visual/config.default.json` **é versionado** e é a única
  fonte dos valores de fábrica (`auto_mode: true` + os quatro `auto_triggers`). O `SKILL.md`
  manda copiar dele quando o arquivo de estado não existe — não redigita os números.
- **Exposição:** perder o arquivo custa **um bit de preferência** (`auto_mode`), reconstruível
  em um `cp`. É por isso que "sem cobertura" aqui é válido e não anomalia: o dado insubstituível
  (o default) está no git; o mutável é regenerável.
- **Insubstituível?** Não.

### 3.10 · Estado por-sessão em `/tmp`
**SEM COBERTURA — justificativa VÁLIDA (efêmero, com poda).**

- `plugins/context-guard/hooks/context-guard-reset.sh` poda ativamente: `find /tmp -maxdepth 1 -name 'claude-context-pct-*' -mtime +1 -delete` e o mesmo para `claude-context-warned-*`.
- Chaveado por `session_id` (regra do repo contra vazamento entre sessões concorrentes). Nada a preservar.
- ⚠️ **A poda depende de `jq` estar instalado.** O script ganhou `command -v jq >/dev/null 2>&1 || exit 0` na **linha 6** — antes do reset e antes dos dois `find` das linhas 10-11. O motivo é correção (sem `jq` o `session_id` sai vazio e o `rm` acertaria sentinel de outra sessão), mas o **efeito colateral de retenção** é que numa máquina sem `jq` o `/tmp` acumula para sempre: ninguém mais poda. [confirmado] Nesta máquina `jq` existe (`/opt/homebrew/bin/jq`, 1.8.1) e há **34** arquivos `claude-context-*` vivos em `/tmp`. Continua sendo acúmulo, não risco — não há nada ali que alguém precise recuperar.

### 3.11 · `~/.claude/plugins/.pedro-plugins-last-sync` e `.pedro-plugins-sync.lock`
**SEM COBERTURA — justificativa VÁLIDA (timestamp/lock).**

- `session-sync.sh` usa o primeiro como marca de throttle (`touch` no fim) e o segundo como lock via `mkdir` atômico, com quebra de lock stale acima de 300s. Perder qualquer um dos dois só força um sync a mais.

### 3.12 · `pi-plugins/` — não é ativo, é lixo a limpar
[confirmado] `du -sh pi-plugins` → **1,7M**; contém **17** subdiretórios. É uma **cópia obsoleta e divergente** de plugins que vivem em `plugins/`. Aparece com fan-in alto no grafo (`pi-plugins/project-doc/lib/journal.py` fan_in=82, contra 89 do original em `plugins/`) e engana quem consulta o grafo sem olhar o path.

**Desde 2026-07-28 ele é ignorado de propósito, não mais untracked-e-solto.** [confirmado neste run] `git check-ignore -v pi-plugins/` → `.gitignore:47:pi-plugins/` (a linha mudou de número na reescrita de 2026-07-31), com a justificativa versionada *"cópia local defasada de plugins/ (não é fonte, ver architecture.md §12)"*. Ele **não aparece** em `git status --porcelain`, cuja saída de hoje tem **116** linhas — **84** remoções do destrack e **32** modificações, nenhuma untracked. O `?? pi-plugins/` que constava aqui era anterior a essa regra.

**Não precisa de backup. Precisa de `rm -rf`.** O `.gitignore` resolveu o ruído no grafo e no `status`; não resolveu os 1,7M no disco. Registrado aqui só para que ninguém o confunda com um ativo sem cobertura.

### 3.13 · `$CLAUDE_CONFIG_DIR/state/prose-ceiling/` — contadores do teto de prosa + `bypass.log`
**SEM COBERTURA — justificativa VÁLIDA, e são duas justificativas diferentes para dois arquivos diferentes.** Depósito novo (bootstrap 1.3.0, Stop hook registrado em `plugins/bootstrap/hooks/hooks.json`).

- **Quem escreve:** `plugins/bootstrap/hooks/stop-prose-ceiling.py`, que roda no evento `Stop` e barra (exit 2) a resposta que passa do teto de prosa (`PROSE_CEILING_MAX`, default **6** linhas).
- ⚠️ **O caminho é resolvido por `CLAUDE_CONFIG_DIR` desde 2026-07-30, e antes disso escritor e leitor discordavam.** O hook usava `Path.home()` fixo; o leitor (`plugins/bootstrap/lib/conformance.py`, constante `CLAUDE_DIR`) sempre usou `Path(os.environ.get("CLAUDE_CONFIG_DIR", HOME / ".claude"))`. Numa máquina com a env var setada, o hook gravava num diretório e o `check_bypass_teto` conferia outro — e como **ausência de `bypass.log` é o caminho feliz do check** (`rep.conforme("teto", "nenhuma resposta furou o teto de prosa")`), o verificador reportava conformidade sobre uma pasta que ninguém escrevia. Hoje as duas linhas são idênticas. **Consequência de durabilidade: num depósito cuja ausência SIGNIFICA algo, escritor e leitor discordando de caminho não dá erro — dá relatório verde falso.** [confirmado nos dois arquivos; nesta máquina `CLAUDE_CONFIG_DIR` está unset, então o caminho efetivo segue `~/.claude/state/prose-ceiling/`]
- **Os contadores — descartáveis, ponto.** Um arquivo por (sessão × resposta): nome = `sha1(session_id + texto)[:16]`, conteúdo = **1 byte**, o número de bloqueios já gastos (trava anti-loop `MAX_BLOQUEIOS = 2`). Perder tudo custa exatamente isto: o orçamento anti-loop volta a zero e uma resposta já bloqueada duas vezes poderia ser bloqueada de novo. Não há informação a recuperar. **Não precisa de backup.**
- **`bypass.log` — prova pendente com instrução de descarte no próprio código.** Append-only, uma linha JSON por vez que o hook **desistiu** de bloquear (`session[:8]`, `linhas_prosa`, `problemas`, `trecho[:120]`). É o registro de que o teto foi furado — o hook desiste depois de 2 bloqueios para não travar a sessão, e o comentário no código é explícito sobre por que registrar: *"O que NÃO pode acontecer é desistir em silêncio"*.
- **Quem lê:** `plugins/bootstrap/lib/conformance.py:check_bypass_teto` — abre o log, conta as linhas, mostra as **3 últimas** ao usuário como desvio `teto`, e termina com a instrução literal `Zere depois de olhar: rm <log>`. Sem o log, o mesmo check reporta *"nenhuma resposta furou o teto de prosa"*.
- **Retenção própria:** **nenhuma automática, nos dois casos.** Nada poda os contadores; o `bypass.log` só encolhe pelo `rm` manual que o conformance manda dar. A retenção desejada é justamente **zero depois de lido** — mesma forma do `askq.log` (§3.6).
- **Precisa de backup? NÃO** — e isto é afirmação, não omissão. Os contadores são orçamento de execução; o `bypass.log` é medição de curto prazo cujo valor acaba no instante em que o conformance a mostra. O que é insubstituível aqui é o *comportamento* (o teto e a redação do bloqueio), e esse mora no código versionado, não neste diretório.
- **Estado hoje:** [confirmado nesta rodada] `~/.claude/state/` contém **só** `prose-ceiling/`, e `prose-ceiling/` está **vazio** — `du -sh` → **0B**, `ls -a` devolve só `.` e `..`. Eram 9 contadores de 1 byte poucas horas antes. Nem o `bypass.log` existe. ⚠️ **Vazio aqui não é o sistema se limpando** [inferido — não há código que remova contador; a remoção veio de fora]: é a retenção manual desta seção funcionando. E é também o cenário em que a discordância de caminho acima passava despercebida — pasta vazia e "nenhuma resposta furou o teto" são a mesma imagem.

### 3.14 · `<projeto>/.claude/intent/<auditoria>.escopo` — o escopo da pergunta do gate
**SEM COBERTURA — justificativa PARCIAL: NÃO é regenerável, mas a perda degrada em vez de destruir.** Depósito novo (intent-guard v0.5.0, `a134e9c`). Inventariado em `data-stores.md`, região (C).

- **O que é:** um array JSON de ids numa linha (`["p-62"]`) ao lado de cada `audit-<epoch>.json`. Registra **quais pedidos o gate encarregou aquele auditor de julgar**, no instante em que bloqueou.
- **Quem escreve:** `plugins/intent-guard/hooks/delivery-audit.sh` — `printf '%s' "$LIVE" | jq -c '[.[] | .id]' > "${OUTP}.escopo"`. É o **hook**, não o auditor, e o comentário do arquivo explica por que tinha de ser assim: o `audit-<epoch>.json` *"ainda não existe quando o gate roda"*, e *"depender do modelo ecoar a lista seria trocar mecanismo por exortação"*.
- **Quem lê:** `plugins/intent-guard/lib/ledger.py:audit_check`, que troca "todo pedido vivo agora" por `perguntados ∩ vivos`.
- **É regenerável? NÃO.** E a razão é de natureza, não de custo: o conteúdo é uma **fotografia de um instante** — quem estava vivo às 21h06 de um dia específico. O ledger é append-only e não guarda "estado vivo em T"; ele guarda eventos, e `fold()` só sabe responder *agora*. Não existe comando, receita ou reconstrução por LLM que devolva o conjunto certo. É o oposto do `graph.json` (§2.4), que um comando recria.
- **Se o arquivo sumir, o que acontece com a auditoria correspondente?** Ela **sobrevive intacta e vira impossível de aprovar.** `audit_check` envolve a leitura do sidecar num `try/except Exception: pass`, então ausência não dá erro: o alvo volta a ser `[e["id"] for e in st["live"]]` — todos os vivos do momento da leitura. Ou seja, **a auditoria regride para o comportamento pré-v0.5.0, que é exatamente o defeito que a v0.5.0 consertou.** Medido nesta rodada, nos dois sentidos, sobre `.claude/intent/audit-1785436084.json` (uma auditoria real, que julgou **um** pedido, `p-62`):

  ```bash
  # com o sidecar correto
  echo '["p-62"]' > <copia>.escopo
  python3 plugins/intent-guard/lib/ledger.py audit-check --cwd . --file <copia>
  # {"ok": true, "why": []}

  # sidecar removido — mesmo arquivo, mesmo ledger
  rm <copia>.escopo
  python3 plugins/intent-guard/lib/ledger.py audit-check --cwd . --file <copia>
  # ok=False | reprovacoes=34
  ```

  **34 reprovações em vez de aprovação, e o gate de entrega não abre.** O trabalho perdido não é o dado: é o subagente de auditoria que terá de rodar de novo, e o bloqueio que persiste até lá.
- **Por que "justificativa PARCIAL" e não "válida":** nenhum arquivo do repo diz que este sidecar pode ser perdido. O que existe é o desenho de **degradação segura** — a ausência cai no comportamento mais estrito, nunca no mais permissivo, que é a mesma direção do `_arquivos_mexidos() → None ⇒ reprova` do mesmo commit. Isso torna a perda **cara, não perigosa**: o sistema nunca aprova por falta de dado. É a justificativa de *segurança*; a de *durabilidade* continua sem estar escrita, exatamente como em §3.2.
- **Retenção própria:** **nenhuma.** Nada apaga `.escopo` — como o `.applied`, acumula um arquivo minúsculo por bloqueio, para sempre.
- **Volume hoje:** **1 arquivo** — `audit-1785466744.json.escopo`, conteúdo `["p-74","p-75"]` [confirmado nesta rodada]. O primeiro bloqueio de entrega desde `a134e9c` produziu o par auditoria+sidecar; as 26 auditorias anteriores continuam sem sidecar **de propósito**, porque sem ele nada retroage.
- **Restauração:** não se aplica — não há de onde restaurar, e é esse o ponto do item.

### 3.15 · Os cinco depósitos que PERDERAM cobertura em 2026-07-31
**SEM COBERTURA — decisão deliberada, justificativa registrada no `.gitignore`, e mesmo assim é perda real de garantia.** Corresponde a `data-stores.md` A1, A2, A3, A4, A6 e à região (C) inteira.

Esta seção existe porque o resto do doc não conseguiria contar a história: quatro depósitos **mudaram de §2 para §3** de uma vez. Não é o mesmo que nascer sem cobertura — é ter tido e perdido, com o histórico do git ainda guardando as versões antigas e nenhuma cópia guardando as próximas.

**O que aconteceu, mecanicamente.** `git rm -r --cached` sobre cinco caminhos + cinco regras novas no `.gitignore`. Nenhum arquivo foi apagado do disco. Medido nesta rodada, `HEAD = ff32947`:

```bash
git ls-files -i -c --exclude-standard | wc -l   # 0    (era 35 antes)
git status --porcelain | grep -c '^D '          # 84   (as remoções, ainda não commitadas)
git ls-tree -r --name-only HEAD | wc -l         # 335  (o que o último commit carrega)
git ls-files | wc -l                            # 251  (o que o próximo vai carregar)
```

| depósito | `.gitignore` | tracked antes (`HEAD`) | tracked agora | no disco | natureza |
|---|---|---|---|---|---|
| `graphify-out/` | linha 28 | 40 | **0** | 1119 arq · 76M | reconstruível (menos os labels) |
| `.claude/.project-doc/` | linha 35 | 3 | **0** | 1,4M | **insubstituível** (journal) + reconstruível (ledger) |
| `.claude/ata/` | linha 38 | 30 | **0** | 30 arq · 1,8M | **insubstituível** |
| `.claude/plans/` | linha 39 | 8 | **0** | 9 arq · 92K | **insubstituível** (o `evidence`) |
| `.claude/HANDOFF*.md` | linha 40 | 3 | **0** | 3 arq · 52K · 514 linhas | **insubstituível** |

- **Cobertura antes:** git + o remote `origin` (§1). **Cobertura agora: nenhuma, dos cinco.** Não há cópia agendada neste repo (§1.2 mede isso negativamente: sem crontab, sem launchd, sem systemd, sem script de dump), então "sair do git" e "ficar sem backup" são a mesma frase aqui.
- 🔴 **Quatro dos cinco são insubstituíveis, e a razão é sempre a mesma:** a matéria-prima é o transcript da sessão, que é local à máquina e não viaja. O journal, as atas, os handoffs e o `evidence` dos planos são as **únicas** formas persistidas daquele conhecimento. Perder este Mac hoje perde **898 eventos de journal, 30 atas, 9 planos e 3 handoffs**, e não há de onde restaurar nenhum deles.
- **A justificativa registrada é de PERTENCIMENTO, não de durabilidade** — e a distinção importa. O `.gitignore` diz, para as atas/planos/handoffs, *"Memória de sessão — pertence a esta cópia de trabalho, não ao marketplace"*; para o journal, *"estado local da máquina, não distribuído"*; para o grafo, *"regenerável com `graphify update`"*. **As três explicam por que o dado não deve ser DISTRIBUÍDO num marketplace público. Nenhuma delas diz que o dado pode ser PERDIDO.** São perguntas diferentes: a primeira é sobre o que vai no presente, a segunda é sobre o que sobra se o disco morrer. Só a do grafo responde às duas.
- ⚠️ **Este repo vai ser presenteado, e é isso que torna a decisão coerente apesar do custo.** Distribuir journal, atas e handoffs num repo público significaria distribuir conversa verbatim de sessões — o scrubber de secret (`journal.py:scrub`) cobre valor-secreto, não contexto. **O destrack acerta a pergunta que estava sendo feita.** O que ele não faz — e ninguém fez ainda — é responder à outra: uma cópia fora desta máquina que não passe pelo repo público.
- ⚠️ **O que o destrack NÃO desfaz: o histórico.** `HEAD` ainda carrega os 84 arquivos, e todo o conteúdo antigo segue no `.git` (**37M**, `size: 31.30 MiB` em objetos soltos). Quem clonar o repo depois do commit não recebe os arquivos na árvore, mas **recebe todas as versões passadas deles no histórico**. Para um repo que vai ser presenteado, isso é o ponto a verificar antes de publicar: *retirar do índice não é retirar do repositório.* [confirmado — `git ls-tree -r --name-only HEAD` ainda lista os cinco caminhos]
- **RPO:** **total.** Sem cópia, a perda é 100% do conteúdo no instante da falha.
- **RTO:** não se aplica aos quatro insubstituíveis (não há restauração). Para `graphify-out/`, é o tempo de um `graphify update . --force` — **exceto** `.graphify_labels.json`, que exige uma passada de LLM.
- **Restauração testada em:** NUNCA TESTADA — e, para quatro dos cinco, nunca poderá ser.
- **Retenção própria:** nenhuma, em nenhum dos cinco. Todos só crescem.

---

## 4 · RPO / RTO

Nenhum dos dois foi medido. Ambos são derivados do mecanismo.

**RPO (quanto de trabalho se perde) — ativos versionados**
- [inferido] **= tudo desde o último `git push`.** Não há outro mecanismo de cópia, então a janela de perda é exatamente a distância entre o working tree e o remote.
- [confirmado — re-medido em 2026-07-31] `git status --porcelain` → **116** linhas: **84** remoções estagiadas (o destrack de §3.15) e **32** rastreados modificados, entre eles o `.gitignore`, o `marketplace.json`, os `plugin.json` dos plugins e os `.claude/docs/*.md`. Zero untracked.
- ⚠️ **As 84 remoções NÃO são janela de perda — são o oposto, e confundir as duas é o erro fácil aqui.** Um `git status` com 84 `D` parece catástrofe pendente; na verdade é uma decisão pendente de commit. **Os arquivos estão todos no disco**; o que se perde se este working tree sumir agora é o *destrack*, não o *conteúdo*. A perda real de conteúdo dos cinco depósitos já aconteceu no plano da garantia (§3.15) e não aparece em `git status` nenhum.
- ⚠️ **Este número em particular não vale por mais que alguns minutos, e uma rodada anterior é a prova.** Entre duas medições da mesma sessão o `git status` foi de 4 rastreados + 2 untracked para 9 rastreados + 0 untracked, porque uma passada de doc estava escrevendo em paralelo e o par de mocks untracked em `plugins/intent-guard/hooks/` sumiu do disco no meio. **Untracked que some não deixa rastro nenhum** — nem no `reflog`, nem no índice. É a ilustração mais barata que este doc tem do que "sem cobertura" significa na prática.
- [inferido] Para `plugins/bootstrap/config/manifest.json` especificamente, o RPO é melhor: **≤ 24h**, pelo ciclo automático do `session-sync.sh` (throttle default `86400`s) — desde que uma sessão do Claude Code abra nesse intervalo. Sem sessão, não há sync. ✅ **E desde 2026-07-30 esse ciclo perdeu o modo de falha que o tornava perigoso:** com o snapshot aditivo (§1.1), um sync que rode sobre uma enumeração incompleta não destrói mais o que já estava no arquivo. O RPO do manifest deixou de embutir "o backup automático pode apagar o dado".

**RPO — ativos sem cobertura (§3)**
- [inferido] **Total.** Sem cópia nenhuma, a perda é de 100% do conteúdo no instante da falha. Vale para o ledger do intent-guard, `~/.claude/plans/`, o journal cross-projeto do qa-loop — **e, desde 2026-07-31, para os cinco depósitos de §3.15**, que até 2026-07-30 estavam na coluna de RPO "desde o último push".
- 🔴 **É a mudança de RPO mais grave que este doc já registrou, e ela foi de grau infinito:** quatro depósitos insubstituíveis saíram de *"perde-se o que não foi pushado"* para *"perde-se tudo"*. Não há gradação entre as duas.

**RTO (quanto tempo até voltar a operar)**
- [inferido] **≈ o tempo de um `git clone` + reinstalação dos plugins.** O clone move ~37M (`du -sh .git`), o que em rede doméstica é questão de segundos. Depois é preciso `claude plugin marketplace add git@github.com:pedroberaldo87/pedro-plugins.git` e reinstalar/reabilitar os plugins — o `bootstrap` automatiza isso a partir de `plugins/bootstrap/config/manifest.json`, mas o caminho **nunca foi percorrido** (§5).
- **Não há número medido.** Não invente um: o RTO real depende de um passo (reinstalação dos plugins via bootstrap) que nunca rodou em máquina limpa.

---

## 5 · Restauração testada

**NUNCA TESTADA — para todos os ativos, sem exceção.**

[relatado — resposta do dono do repo nesta sessão, verbatim: *"nunca testei"*]

Isso vale simultaneamente para:
- o repositório versionado (nunca houve um `git clone` de verificação a partir do remote);
- o ciclo de onboarding do bootstrap (`plugins/bootstrap/config/manifest.json` → `apply.sh`) em máquina limpa;
- o cofre no iCloud (nunca foi restaurado de outra máquina);
- 🔴 os cinco depósitos de §3.15 — e para quatro deles a restauração **não é só não-testada, é inexistente**: não há de onde restaurar;
- as tags `archive/*` (§2.8) — nunca se ressuscitou uma branch a partir de uma delas, e no remote não há nenhuma para tentar;
- todos os ativos de §3, que nem têm de onde restaurar.

Consequência prática: o RTO de §4 é uma **estimativa não validada**. A primeira restauração real será também o primeiro teste — o pior momento para descobrir um passo faltando.

---

## Resumo de exposição

**Insubstituíveis sem backup: 7 — eram 3 até 2026-07-30.** Os quatro que entraram não pioraram de natureza: pioraram de **garantia**, num único `git rm -r --cached`.

1. **`<projeto>/.claude/intent/ledger.jsonl` + `audit-*.json` + `.escopo`** (§3.2, §3.14) — verbatim dos pedidos e os vereditos de entrega. Fora do git por `.git/info/exclude:18`. A fonte original (transcript da sessão) é local e não viaja. **SEM justificativa registrada.** Hoje: **476K**, 460 eventos, **42 pedidos vivos**, 27 auditorias das quais **11 nunca foram transcritas**. O sidecar `.escopo` (§3.14) entra aqui com uma nuance própria: **não é regenerável por natureza** (fotografa um instante que o ledger não sabe reconstruir), mas sua perda **degrada em vez de destruir** — a auditoria sobrevive e vira impossível de aprovar, medido em **34 reprovações em vez de `{"ok": true}`**.
2. **`~/.claude/plans/`** (§3.3) — **213** arquivos, 2,7M. Âncora do `/qa-loop` para classificar plan-drift. Nenhum arquivo deste repo escreve lá, só lê. **SEM justificativa registrada.** 🔴 **A mitigação parcial que este item citava — o depósito coberto de §2.6 — deixou de existir em 2026-07-31.**
3. **`~/.claude/qa-loop/journal/learnings.md` + `telemetry.jsonl`** (§3.4) — aprendizado destilado cross-projeto sobre o próprio processo de QA. O que está escrito no SKILL.md justifica o *local* ("sobrevive a reinstalar o plugin"), não a *ausência de cópia*. **SEM justificativa registrada.**
4. 🔴 **`.claude/.project-doc/findings.jsonl`** (§3.15) — **898 eventos** de conhecimento minerado, 1,1M. Era o item 1 de §2 ("git + GitHub — é versionado"). **Justificativa de pertencimento registrada no `.gitignore`; de durabilidade, nenhuma.**
5. 🔴 **`.claude/ata/`** (§3.15) — **30 arquivos, 1,8M** de atas narrativas de sessão. Era §2.5, coberto sem ressalva. **Idem: a justificativa escrita diz por que não distribuir, não que pode perder.**
6. 🔴 **`.claude/plans/*.plan.json`** (§3.15) — **9 planos, 92K**, e com eles o `evidence` de cada passo `done`. Era §2.6. **A prova é a parte insubstituível, e é a que o transcript não devolve.**
7. 🔴 **`.claude/HANDOFF*.md`** (§3.15) — **3 arquivos, 52K, 514 linhas** de contexto destilado entre sessões. Era coberto. **Idem.**

⚠️ **Os quatro novos compartilham um traço que os três antigos não tinham: a justificativa EXISTE e mesmo assim não cobre o buraco.** O `.gitignore` responde *"por que isto não vai no marketplace público?"* com clareza. A pergunta de durabilidade — *"e se este disco morrer?"* — segue sem resposta escrita em nenhum arquivo do repo, exatamente como em §3.2 e §3.4. **Justificativa de escopo não é justificativa de durabilidade**, e é a confusão entre as duas que este resumo existe para impedir.

**Insubstituível, no git local e agora também no remote: 1.** As **6** tags `archive/<branch>-<data>` (§2.8) eram a única classe do inventário que passava no teste "está no git" e falhava no teste "existe no remote". Foram empurradas em 2026-07-30 e hoje `git ls-remote --tags origin | grep -c 'archive/'` devolve **6**. O que sobra aberto não é a cobertura destas seis, é o automatismo: `cmd_prune` cria a tag e não empurra, então a próxima nasce local de novo.

**Sem cobertura, mas com justificativa que se sustenta: 7.** `~/.claude/green-suite/` (cache com TTL 24h e poda de 7d), `~/.claude/visual-state/` (os `<session>.json`/`latest.json` do daemon são efêmeros por sessão; o `config.json` que passou a morar ali desde 2026-07-28 é preferência regenerável do default versionado — §3.9), os kill-switches `mode` (§3.7), `/tmp/claude-context-*` (podado a 1 dia — desde que `jq` exista, §3.10), os arquivos de throttle/lock do bootstrap (§3.11) e **`$CLAUDE_CONFIG_DIR/state/prose-ceiling/` (§3.13)** — contadores anti-loop de 1 byte e um `bypass.log` que o próprio `conformance.py` manda apagar depois de lido; **vazio hoje (0B)**. **Nenhum dos dois precisa de backup**, e isso está dito lá com todas as letras, não por omissão.

**Anomalia à parte: 0.** A única que existia — o `config.json` do `/visual`, untracked **e** não coberto pelo `.gitignore`, morando dentro do plugin — foi **resolvida em 2026-07-28** movendo o estado para `~/.claude/visual-state/` (§3.9). Verificado neste run: `git status` limpo do arquivo.

**Justificativa PARCIAL, e a parte que falta é a de durabilidade: 2.**
- `~/.claude/guardrails/` (§3.6) — a retenção é deliberada (rotação de log), mas os **dois escritores da mesma pasta resolvem o caminho por expressões diferentes** desde a v1.5.0: `scope-cop.sh` honra `CLAUDE_CONFIG_DIR`, `askq-humanize.sh` não. Num backup por caminho fixo, isso perde metade do depósito sem avisar.
- `<projeto>/.claude/intent/<auditoria>.escopo` (§3.14) — **não regenerável por natureza**, e é o primeiro item deste inventário cuja perda tem o efeito medido em número: a auditoria correspondente sai de `{"ok": true}` para **34 reprovações**. O que existe escrito é a garantia de **degradação segura** (ausência cai no comportamento mais estrito, nunca no mais permissivo); o que não existe é qualquer linha dizendo que o dado pode ser perdido.

**Cobertura parcial: 1.** Cofre de secrets no iCloud (§3.8) — replicado pelo iCloud, fora do git por design correto; a saúde do sync do iCloud não foi verificada nesta rodada.

**Restaurações nunca testadas: TODAS.** Zero ensaios de recuperação, em qualquer ativo — incluindo o caminho principal (clone do remote + bootstrap em máquina limpa). O RTO de §4 continua [inferido] enquanto isso não mudar.

**Risco imediato desta rodada:** [confirmado, `git status --porcelain` → **116** linhas] **32** rastreados modificados e não commitados, entre eles os `.claude/docs/*.md` — doc curada, sem regenerador barato — e **84** remoções estagiadas do destrack. ⚠️ **As duas metades têm risco oposto e não devem ser somadas:** as 84 remoções não perdem conteúdo (os arquivos estão no disco), perdem só a decisão se o working tree sumir; as 32 modificações são a janela de perda de verdade. **O risco maior desta rodada não está em `git status` nenhum** — está em §3.15, e já é permanente: quatro depósitos insubstituíveis ficaram sem cópia, e nenhum commit conserta isso.

**Fechado nesta rodada, e vale registrar o que mudou de forma:** as duas travas do `manifest.json` (§1.1) deixaram de ser enumerações do caso e viraram regras.
- A proteção de chave-de-topo passou a listar o que o script **gera** (`GENERATED_KEYS`) em vez do que ele **salva**; chave nova mantida à mão sobrevive sem ninguém lembrar de vir aqui.
- O snapshot passou a ser **aditivo**: nunca remove entrada de plugin, porque `claude plugin list` devolve saída incompleta de forma intermitente (reproduzido nesta sessão: 49, 32, 21, 49, 49 em cinco chamadas seguidas).
- **O que sobra pra vigiar é o outro lado da mesma moeda:** um manifest que nunca remove **acumula plugin já desinstalado**, e a única forma de tirar é edição explícita do arquivo. Isso é dívida de higiene, não de durabilidade — mas se ninguém a pagar, o artefato de recuperação de máquina nova passa a mandar instalar coisa que não se usa mais.
