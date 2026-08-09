---
generated: 2026-08-08
generated-commit: 8acbe9e
project: pedro-plugins
scope:
  - .gitignore
  - .git/info/exclude
  - plugins/project-skills/lib/plan_state.py
  - plugins/project-skills/lib/cobertura.py
  - .claude/suite-congela.baseline.json
  - .claude/fio-morto.baseline.json
  - .claude/custo-gatilho.baseline.json
  - .claude/desacoplamento.baseline.json
  - plugins/project-skills/lib/andamento.py
  - plugins/sovai/hooks/posttooluse-andamento.sh
  - plugins/handoff/skills/handoff/SKILL.md
  - _shared/green-cache.sh
  - plugins/project-doc/lib/journal.py
  - plugins/bootstrap/hooks/hooks.json
  - plugins/bootstrap/hooks/session-sync.sh
  - plugins/bootstrap/hooks/lib/snapshot.sh
  - plugins/bootstrap/hooks/lib/git-sync.sh
  - plugins/bootstrap/hooks/stop-prose-ceiling.py
  - plugins/bootstrap/hooks/stop-forma-relato.py
  - plugins/bootstrap/lib/conformance.py
  - plugins/intent-guard/lib/ledger.py
  - plugins/context-guard/hooks/context-guard-reset.sh
  - plugins/guardrails/hooks/scope-cop.sh
  - plugins/guardrails/hooks/askq-humanize.sh
  - plugins/visual/server/visual_server.mjs
  - plugins/visual/skills/visual/config.default.json
  - .claude/hook-contract.baseline.json
verified-by:
  - plugins/bootstrap/hooks/test_bootstrap_hooks.sh
  - plugins/bootstrap/lib/test_conformance.py
  - plugins/intent-guard/lib/test_ledger.py
  - plugins/project-doc/lib/test_journal.py
  - plugins/project-skills/lib/test_plan_state.py
  - plugins/project-skills/lib/test_cobertura.py
  - plugins/handoff/lib/test_handoff_skill.py
doc-sig: pedro-plugins/.gitignore@gen=3.8#6a71bd62
---

# Durabilidade

Par obrigatório de **data-stores.md**: cada depósito listado lá tem um bloco aqui — inclusive (e principalmente) os que não têm cobertura nenhuma.

Cobertura, neste documento, significa uma coisa só: **está rastreado pelo git E existe no remote**. Nada mais protege nada aqui.

🔴 **Leia o §0 antes de qualquer outra seção.** Hoje o repositório trocou de história, e o efeito é maior que o de qualquer regra de `.gitignore` já escrita aqui.

---

## 0 · O corte de hoje: a história anterior não está no remote

[confirmado, rodado nesta sessão] O repo foi recriado como **um commit órfão**, sem ancestral comum com a história anterior. A história antiga continua no disco desta máquina, alcançável por refs locais — e **só por elas**.

```bash
$ git log --format='%H %cI %s' | head -1
2587006652a46b1c53272ccf53f117be8d6c634f 2026-07-31T18:45:43-03:00 pedro-plugins: marketplace de plugins para Claude Code

$ git rev-list --count HEAD          # alcançável do HEAD/remote
1
$ git rev-list --count --all         # alcançável de QUALQUER ref local
396
$ git rev-list --count --all --not 2587006652a46b1c53272ccf53f117be8d6c634f
395

$ git ls-remote --heads origin
2587006652a46b1c53272ccf53f117be8d6c634f	refs/heads/main
$ git ls-remote --tags origin
(nenhuma saída)
```

- [confirmado] O remote tem **uma** branch (`main`) e **zero** tags.
- [confirmado] `git merge-base HEAD archive/docs/readme-20260728` devolve **vazio** — não há ancestral comum entre a história nova e a antiga.
- [confirmado] A história antiga vive em `refs/heads/main` (local, `f1ba311`, **291** commits, o mais antigo `d743f10` de `2026-04-07T23:51:34-03:00`) e nas **6** tags `archive/*`, todas com o objeto presente localmente (`git cat-file -e` OK nas seis).
- [confirmado] O working tree atual está limpo e a branch de trabalho é `publicar`, apontando para o mesmo commit do remote:
  ```bash
  $ git status -sb
  ## publicar...origin/main
  ```

**Consequência de durabilidade, sem maquiagem:** [confirmado] **395 commits** — toda a história de 2026-04-07 até 2026-07-31 10:10, mais as 6 tags de resgate do `/branches` — passaram de *cobertos* para *existentes em uma única máquina*. Nenhum `git push` da configuração atual os leva: o push empurra `publicar → origin/main`, e nada mais. Perder este Mac hoje perde a história inteira e mantém só o retrato de hoje.

⚠️ [inferido] `git gc` agressivo depois de `refs/heads/main` e as tags saírem do caminho apagaria esses objetos sem aviso — objeto não alcançável por ref nenhuma é lixo do ponto de vista do git. Enquanto as refs locais existirem, os objetos ficam.

---

## 1 · O mecanismo: git + o remote no GitHub. Só isso.

[confirmado] Não há camada de backup própria. O que protege o que está rastreado é o histórico do git local mais o remote `origin`:

```bash
$ git remote -v
origin	git@github.com:pedroberaldo87/pedro-plugins.git (fetch)
origin	git@github.com:pedroberaldo87/pedro-plugins.git (push)
```

- **Quem copia:** o próprio `git push`, manual na esmagadora maioria dos casos (a exceção é o §1.1).
- **Para onde:** GitHub, `pedroberaldo87/pedro-plugins`, via SSH.
- **Offsite:** sim — o remote está fora da máquina de trabalho.
- **Frequência:** a cada push. Não há agendamento (§1.2).
- **Retenção:** [confirmado] hoje o remote retém **1** commit. A frase "histórico completo do git" deixou de valer nesta rodada — ver §0.
- **Tamanho:** [confirmado, HEAD = `2587006`] `du -sh .git` → **39M**; `git ls-files | wc -l` → **252** arquivos rastreados.
  ⚠️ **Os 39M são majoritariamente objetos que o remote não tem.** O `.git` grande não é sinal de cobertura — é sinal do oposto: história local guardada e não empurrada.
- [confirmado] `git ls-files -i -c --exclude-standard | wc -l` → **0**: nenhum arquivo ignorado ficou rastreado por engano. Essa é a régua escrita no cabeçalho do próprio `.gitignore`.

Distribuição do que está rastreado hoje (derivado mecanicamente no run):

```bash
$ git ls-files | awk -F/ '{print $1}' | sort | uniq -c | sort -rn
 225 plugins
   9 .claude
   7 scripts
   3 _shared
   1 README.md   (+ GEMINI.md, AGENTS.md, .windsurfrules, .cursorrules,
                   .gitignore, .github, .claude-plugin — 1 cada)
```

### 1.1 · O único push automático cobre um arquivo só

[confirmado] Existe **um** caminho de commit+push automático, e ele é deliberadamente estreito.

- **Ativação (não só existência):** `plugins/bootstrap/hooks/hooks.json` registra o hook `SessionStart` apontando para `${CLAUDE_PLUGIN_ROOT}/hooks/session-sync.sh`, e o plugin está ligado na máquina:
  ```bash
  $ python3 -c "import json;print(json.load(open('~/.claude/settings.json'.replace('~','$HOME')))['enabledPlugins']['bootstrap@pedro-plugins'])"
  True
  ```
  Versão em `plugins/bootstrap/.claude-plugin/plugin.json`: **1.8.5**.
- **Cadeia:** `session-sync.sh` → fetch barato → `pull --rebase --autostash` → `lib/apply.sh` → `lib/snapshot.sh` → `lib/git-sync.sh`.
- **Throttle:** `session-sync.sh` define `THROTTLE_SECONDS="${PEDRO_PLUGINS_THROTTLE_SECONDS:-86400}"` e pula o ciclo se o último sync foi há menos que isso **e** o remote não avançou. Bypass literal do arquivo: `PEDRO_PLUGINS_FORCE_SYNC`.
- **O que ele empurra:** `lib/git-sync.sh` define `MANIFEST_REL="plugins/bootstrap/config/manifest.json"` e commita com `git commit --only "$MANIFEST_REL"`. Nenhum outro arquivo é estagiado, por desenho. Trabalho não commitado nunca é salvo por este caminho.
- **Guarda anti-propagação:** em `session-sync.sh`, se `apply.sh` sai com código ≠ 0 o snapshot é pulado inteiro — senão um manifest regenerado a partir de estado degradado viraria "nova verdade" para as outras máquinas. O script ainda assim dá `touch "$LAST_SYNC_FILE"` para não repetir a tentativa a cada sessão.
- **Snapshot preserva chave mantida à mão, por REGRA e não por enumeração.** `lib/snapshot.sh` regenera o manifest com `jq -n` e depois relê o arquivo do disco:
  ```bash
  GENERATED_KEYS='["version","description","marketplaces"]'
  PRESERVED_KEYS="$(jq --argjson gen "$GENERATED_KEYS" \
    'with_entries(select(.key as $k | $gen | index($k) | not))' "$MANIFEST_PATH")"
  ```
  A lista é do que o script **gera**; o filtro é o complemento. Chave nova mantida à mão sobrevive sem ninguém lembrar de editar a lista.
- **Snapshot é ADITIVO — nunca remove entrada.** A união por `name` dentro de cada marketplace está no mesmo arquivo:
  ```bash
  ($antigos + $m.plugins) | group_by(.name) | map(if length > 1 then .[1] else .[0] end)
  ```
  O comentário no código dá o motivo: não há como distinguir *desinstalado* de *a CLI não listou desta vez*, então a leitura segura é a que nunca remove. Rede sobre a rede: se o total ainda assim encolher, o script loga `warning: manifest encolheu N -> M (não deveria: a união é aditiva)` — alarme, não bloqueio.
- **Coberto por teste** [confirmado, rodado nesta sessão]:
  ```
  $ bash plugins/bootstrap/hooks/test_bootstrap_hooks.sh
  -- snapshot preserva chave mantida a mao
    ok   chave arbitraria sobrevive ao snapshot
    ok   skills sobrevive ao snapshot
  -- round-trip: o snapshot devolve o manifest inteiro
    ok   2a rodada e idempotente
  36 ok · 0 FAIL
  ```

**Consequência de durabilidade:** para todo o resto do repo (código dos plugins, docs, scripts) o push é **manual**. E para os depósitos do §3 não é que o push seja manual — é que **não há push a dar**: eles não estão no índice.

### 1.2 · O que NÃO existe (verificação mecânica negativa)

Rodado nesta sessão, na raiz do repo:

```bash
$ crontab -l
crontab: no crontab for <usuario>

$ find . -name "*.plist" -o -name "*.timer" -o -name "*.service"
(nenhuma saída)

$ grep -rniE "crontab|systemd|launchd|launchctl|pg_dump|mysqldump|restic|borg|rsync" \
    --include="*.sh" --include="*.py" plugins/ _shared/ scripts/ .claude/hooks/ | wc -l
7
```

[confirmado] As **7** ocorrências são todas prosa em `plugins/fallow/lib/audit.py` e `plugins/fallow/lib/report.py`, que citam cron/systemd como *gatilhos externos que a análise estática não enxerga*. Nenhuma configura cópia.

**Não há crontab, unit/timer de systemd, plist de launchd, nem script de dump/rsync/restic/borg. A única cópia é o push.**

---

## 2 · Ativos COM cobertura

### 2.1 · Código dos plugins — `plugins/**`

- [confirmado] **225** arquivos rastreados sob `plugins/`, presentes no commit que o remote tem.
- Inclui os hooks, as skills, as libs Python e a fonte compartilhada `_shared/`, que passou de **3** para **7** arquivos rastreados nesta rodada: `collect_engine.py`, `green-cache.sh`, `r8-tiers.md`, mais `r8-tiers.json` (§2.5), `r8_tiers.py`, `regua_texto.py` e `test_regua_texto.py`. [confirmado, `git ls-files _shared`]
- Cobertura real: perder a máquina e clonar de novo devolve o código dos plugins tal como está hoje.

### 2.2 · Catálogo do marketplace — `.claude-plugin/marketplace.json`

- [confirmado] Rastreado. É a fonte da verdade da distribuição: **19 entradas**. Nesta rodada quatro subiram — `sovai` **1.9.0 → 1.11.0**, `visual` **1.11.1 → 1.12.0**, `qa-loop` **1.7.2 → 1.8.0** e `bootstrap` **1.8.5 → 1.9.0** —, que são exatamente os plugins cujo estado mudou aqui. As demais seguem: `project-doc` 3.18.4, `intent-guard` 0.6.0, `guardrails` 1.5.2, `context-guard` 1.3.3.
- [confirmado, derivado nesta rodada] O espelho `plugin.json` ↔ `marketplace.json` fecha nas **19** entradas — nenhuma diverge. É o check B do release-gate, e ele passa hoje.
- Cobertura real: quem instala pelo marketplace só depende deste arquivo e do `plugins/**` — ambos no remote.

### 2.3 · Documentação gerada — `.claude/docs/*.md` e `.claude/CLAUDE.md`

- [confirmado, nesta rodada] Sob `.claude/` há exatamente **13** arquivos rastreados — eram 9 na rodada anterior:
  ```bash
  $ git ls-files .claude
  .claude/CLAUDE.md
  .claude/LIMITES-CONHECIDOS.md
  .claude/docs/architecture.md
  .claude/docs/data-stores.md
  .claude/docs/durability.md
  .claude/docs/patterns.md
  .claude/docs/quality-goals.md
  .claude/docs/runtime.md
  .claude/hooks/release-gate.sh
  .claude/hooks/test_release_gate.sh
  .claude/limites-aceitos.md
  .claude/settings.json
  .claude/stop-budget.baseline.json
  ```
  Os quatro que entraram não são todos da mesma natureza: `quality-goals.md` e `stop-budget.baseline.json` já tinham bloco próprio aqui (§3.6a) ou no `data-stores.md`; `limites-aceitos.md` é o depósito novo do §2.6, e `test_release_gate.sh` é teste, não depósito.
- Tudo o mais que o `.claude/` do repo carrega hoje está no §3 — a assimetria é o ponto do `.gitignore`, seção 1 (*registro de trabalho pertence a quem escreveu, não a quem instala*).

### 2.4 · O manifest do bootstrap — `plugins/bootstrap/config/manifest.json`

- [confirmado] É o **único** artefato com push automático (§1.1) e o único caminho de recuperação da *lista de terceiros* numa máquina nova. `plugins/**` cobre o código; só o manifest cobre quais marketplaces de terceiros existiam e quais plugins estavam ligados.

### 2.5 · Contrato de tier dos motores — `_shared/r8-tiers.json`

Depósito **novo em 2026-08-03** (commit `5288bc5`). Ver `data-stores.md §A7` para a anatomia.

- 🟢 **Coberto.** [confirmado] `git ls-files` encontra a fonte (`_shared/r8-tiers.json`, 2.856 bytes) **e** as duas cópias vendoradas (`plugins/{sovai,qa-loop}/skills/*/references/r8-tiers.json`). Nenhuma delas carrega caminho de máquina nem segredo — é valor de configuração, viaja limpo.
- **Consequência de durabilidade: a cobertura melhorou por conta da mudança, não apesar dela.** O mesmo dado antes vivia disperso no texto de dois `SKILL.md` — versionado, mas sem lugar único de verdade, e o cabeçalho de `_shared/r8_tiers.py` mede o custo disso: *"trocar seis valores custou 45 substituições em dois SKILL.md, três saíram invertidas"*. Um valor em quinze lugares está tecnicamente coberto e praticamente irrecuperável, porque restaurar exige saber qual das cópias estava certa.
- **O que a redundância é hoje, e por que ela é segura:** três cópias idênticas por construção (`md5` igual nas três nesta rodada), com um verificador que acusa divergência — `scripts/sync-shared.sh --check` para o vendoring e o check **E3** do release-gate (`r8_tiers.py check`) para o markdown gerado e para literal reaparecendo em `SKILL.md`. Rodado nesta sessão: `OK: R8 servido de _shared/r8-tiers.json, sem cópia carimbada em SKILL.md`. [confirmado]
- ⚠️ **O que a cobertura do git NÃO devolve:** o campo `porque` de cada tier é julgamento escrito à mão. `git checkout` traz o arquivo de volta; um arquivo regenerado do zero traria os `effort` e não os motivos.

### 2.6 · Registro de limites aceitos — `.claude/limites-aceitos.md`

Depósito **novo em 2026-08-03** (commit `1e59b55`). Ver `data-stores.md §A8` para a anatomia.

- 🟢 **Coberto.** [confirmado] Rastreado (2.091 bytes), e entra na lista de arquivos sob `.claude/` que estão no índice (§2.3).
- **Por que ele merece cobertura e a saída que ele descreve não:** as 82 páginas de `.claude/visual/` que ele isenta são gitignoradas e regeneráveis (§3.19). O que não é regenerável é a **decisão de não consertá-las**, com o motivo e o comando de reconferência ao lado. Perder as páginas custa nada; perder este arquivo faz o mesmo desacordo voltar como dívida esquecida ou como conserto reflexo — o texto do próprio arquivo nomeia os dois.
- **Mesma classe dos baselines A5/A5a (§3.6, §3.6a): julgamento embutido.** A diferença é o sentido — o baseline é um retrato regenerável com uma decisão implícita no ato de recongelar; aqui a decisão é o conteúdo inteiro, e nenhum comando a produz.
- ⚠️ **Nenhum verificador o lê** [confirmado — nenhum hook nem script do repo o referencia]. O arquivo declara o que revoga cada limite, mas quem confere é humano. Um limite vencido continua no arquivo até alguém rodar o comando que ele mesmo prescreve — e a §3.19 abaixo já mostra um número que saiu do lugar.

---

## 3 · Ativos SEM cobertura

Cada bloco abaixo diz o mesmo em variações: existe no disco desta máquina, não existe em lugar nenhum além dela.

### 3.1 · A história anterior do repo — `refs/heads/main` local + as 6 tags `archive/*`

- [confirmado] **395** commits fora do alcance do remote; `refs/heads/main` local aponta para `f1ba311`, com **291** commits.
- [confirmado] As tags de resgate do `/branches` (`archive/<branch>-<data>`) existem localmente e **não** no remote. `plugins/branches/skills/branches/SKILL.md` documenta a rede como "toda branch apagada vira `archive/<branch>-<data>`" e é explícito que apagar no remoto é decisão separada — hoje a tag em si também é local-only.
- [confirmado] `git for-each-ref` ainda lista remote-tracking refs (`origin/feat/...`) que **o remote não tem mais**: são refs locais defasadas, não cobertura.
- Perder a máquina perde: o histórico de por que cada decisão foi tomada, e a única forma de ressuscitar as 6 branches arquivadas.

### 3.2 · Journal do project-doc — `.claude/.project-doc/`

- [confirmado] Ignorado por `.gitignore:21`. `du -sh` → **4,8M**; `findings.jsonl` com **1133** linhas; ao lado, `ledger.json`, `lint-allow.txt` e um diretório `backups/` (também local).
- Natureza (de `plugins/project-doc/lib/journal.py`): append-only. `append_events()` só escreve linhas novas; `fold()` reconstrói o estado vivo por id, em ordem cronológica — `discovered` cria, `invalidated` mata sem apagar, `curated` sobrepõe o texto; `live_findings()` filtra o que sobrou vivo e aplica a curadoria.
- Isso corta pela raiz a perda *parcial* (nada é reescrito) e não faz nada contra a perda *total* do arquivo.
- ⚠️ O docstring do módulo ainda descreve o journal como "versionado — é o veículo do conhecimento" (`state_dir()`); [confirmado] no `.gitignore` de hoje ele **não é**. A intenção do código e a regra do repo divergem, e a regra é que vale.
- O scrubber (`scrub()`) existe justamente porque o journal *era* a barreira para o git: ele move valor-secreto para o cofre (§3.11) e preserva nome/host/porta. Com o journal fora do índice, o scrubber virou defesa em profundidade, não a única barreira.

### 3.3 · Grafo do graphify — `graphify-out/`

- [confirmado] Ignorado por `.gitignore:44` (seção *retrato desta máquina — regenerável, e carimba caminho absoluto e hostname*). `du -sh` → **75M**, o maior depósito local do projeto.
- Regenerável por `graphify update . --force` (AST, sem LLM). A perda custa tempo de recomputação, não conhecimento — [inferido] a passada com LLM do `/graphify` é a parte cara, e essa sim não é reconstruída pelo `update`.

### 3.4 · Atas de sessão — `.claude/ata/`

- [confirmado] Ignorado por `.gitignore:17`. **32** arquivos, **1,9M**.
- Escritas pelo `/handoff` (`plugins/handoff/lib/extract_ata.py`). Nenhuma cópia.

### 3.5 · Planos ticáveis — `.claude/plans/*.plan.json` e `~/.claude/plans/`

- [confirmado] `.claude/plans/` ignorado por `.gitignore:18`. **13** arquivos no repo (**132K**, 115.686 bytes de JSON); `~/.claude/plans/` está em **2,3M**.
- ⚠️ **Costura desalinhada, verificada nos dois lados** [confirmado, reconferido nesta rodada]: o docstring de `plugins/project-skills/lib/plan_state.py` diz que o plano mora em `<raiz>/.claude/plans/<id>.plan.json` e é "VERSIONADO no git de propósito: a dor é perda". `git check-ignore -v .claude/plans/` devolve `.gitignore:18`. O motivo escrito no `.gitignore` (registro de trabalho, com nome de cliente e caminho de máquina) venceu; o comentário do código ficou para trás.
- 🔴 **O que está sem cobertura AUMENTOU nesta rodada, e não em bytes.** O arquivo passou a guardar cinco campos novos por tarefa (`requisito`, `pronto`, `grupo`, `pendencia`, `decidido`) e um bloco `requisitos` no topo do plano. O bloco é a **fonte de requisitos** para projeto sem documento separado — *"o caso deste repositório, que não tem PRD"* [confirmado, docstring de `_requisitos_do_plano`]. Ou seja: num projeto assim, o `.plan.json` deixa de ser só o registro do que foi feito e passa a ser **o único lugar onde o que o sistema deve fazer está escrito**. Perdê-lo passou a perder também o pedido, não só a execução. E a dependência ficou mais forte nesta rodada: a skill `handoff` passa a **copiar verbatim** o `pronto` e a `pendencia` do arquivo para o documento de retomada, em vez de redigi-los de novo — sem o arquivo, a sessão seguinte volta a inventar o critério de pronto. [confirmado — `plugins/handoff/skills/handoff/SKILL.md` + `plugins/handoff/lib/test_handoff_skill.py`]
- [confirmado, derivado nesta rodada] **Nenhum dos 13 planos no disco usa esses campos ainda** — as chaves de topo dos 13 são só `id`, `title`, `phases`, `created`, `status` e `closed_at`. A exposição descrita acima é do formato, não do conteúdo de hoje.
- O que o formato protege sozinho: `save()` escreve em `<path>.tmp` e faz `os.replace()` — escrita atômica, então falha no meio não corrompe o plano. `merge()` recusa renomear um id existente sem `--rename`, mantém nós que não vieram no `init` novo e **recarrega do arquivo tudo o que o `init` omitiu** — um init que esquece não apaga histórico, pelo mesmo motivo que não apaga a prova. `cmd_tick()` exige `--evidencia` com pelo menos `EVIDENCE_MIN = 8` caracteres e recusa tarefa com decisão em aberto; `erros_do_plano()` fecha a mesma porta no `init`, recusando `status: "done"` com prova abaixo do mesmo teto. `cmd_reabrir()` desfaz uma decisão registrada em `decidido`, devolvendo-a a `pendencia` — reversibilidade por construção, não por backup.
- 🔴 **A perda mais cara deste depósito não era o disco falhar: era o próprio programa apagar.** Até a rodada de consertos, `merge()` preservava uma lista fixa de campos no nó e apenas `created`/`status` no topo — então **o segundo `init` do mesmo plano apagava, calado, o bloco `requisitos`, o `closed_at` e o `detail` de toda fase**. Num projeto sem documento separado, o bloco `requisitos` é *o único lugar onde o que o sistema deve fazer está escrito* (parágrafo acima): perdê-lo não era só perder texto — desligava também o portão que recusa citação a requisito inexistente, porque sem fonte a checagem não roda. Os 13 planos no disco carregam **60 blocos `detail`** que estavam nessa exposição. Hoje a preservação vale para toda chave ausente, e apagar de propósito é declarar a chave **vazia**. [confirmado — `plan_state.py:merge`; os 60 derivados com `json.load` sobre os 13 arquivos nesta rodada]
- **Leitura tem porta única que nomeia o estrago:** `le_plano()` converte arquivo ilegível ou JSON inválido em erro com o CAMINHO e a CAUSA, dizendo que o conserto é à mão *"porque é o registro do que já foi feito, e nada aqui o reescreve"* — em vez do traceback que não dizia sequer qual arquivo estava torto. `list_plans()` segue engolindo o arquivo quebrado de propósito: um byte errado não pode derrubar a listagem dos outros 12. [confirmado]
- 🟡 **A `evidence` ganhou FORMA em 2026-08-03, e isso muda o que se perde junto com o arquivo.** `cmd_tick()` passou a recusar prova acima de `BULLET_MAX = 140` caracteres num bloco só — a condição é `len(ev) > BULLET_MAX and len(prova_bullets(ev)) < 2`, e `prova_bullets` quebra só onde quem escreveu já separou (`\n`, ` · `, `; `, ` + `). **Saída crua de comando passa inteira**, porque já vem quebrada; o teto morde o texto redigido pelo modelo. [confirmado, `plugins/project-skills/lib/plan_state.py:cmd_tick`]
- **Consequência de durabilidade: a prova ficou mais densa e continua sem cópia.** A recusa empurra a `evidence` para saída de comando e sha em vez de parágrafo — mais verificável e menos reescrevível de memória. Um plano perdido antes custava uma narrativa que alguém poderia recontar; hoje custa o registro literal do comando que rodou e do que ele devolveu, que ninguém reconstitui de cabeça.
- ⚠️ **O teto vem de fora do módulo** (`from regua_texto import BULLET_MAX`, e `DESC_MAX = BULLET_MAX`), da cópia vendorada em `plugins/visual/lib/` — uma das **9** que o `sync-shared.sh` mantém. Perder a cópia não perde plano, mas faz o `plan_state.py` parar de importar: a régua compartilhada virou dependência de execução do depósito, não só do renderizador. [confirmado]
- **A prova já gravada não é reavaliada** — a recusa é do momento de gravar. Os planos no disco com prova antiga em bloco único seguem válidos e nada os migra.
- [confirmado, medido nesta rodada] O depósito cresceu de 13 para **18** planos (**192K**, 163.576 bytes), e hoje há **um** plano ativo (`2026-08-03-a-constituicao-se-cumpre`) — o impasse dos dois ativos simultâneos deixou de ser o estado deste disco.
- Nada disso é cobertura: protege contra o plano *virar outro*, não contra o arquivo sumir.
- Coberto por teste [confirmado, rodado nesta sessão]: `python3 plugins/project-skills/lib/test_plan_state.py` → `OK` (173 asserções `ok`, contra 135 antes da rodada de consertos; a última impressa é `list_plans pula o corrompido`) e `python3 plugins/project-skills/lib/test_cobertura.py` → `OK` (13).

#### 3.5.1 · O calculador do fio — `plugins/project-skills/lib/cobertura.py`

- [confirmado] **Arquivo novo desta rodada, e NÃO é depósito.** 79 linhas, três funções (`le_requisitos`, `mapa`, `resumo`), nenhuma escrita em disco. Lê um markdown de requisitos, cruza com o plano e devolve os quatro estados do fio (coberta · sem requisito · requisito órfão · citação inexistente).
- **Consequência de durabilidade: nenhuma direta, e uma indireta que importa.** Perder o arquivo é perder código, que está no `plugins/**` coberto pelo remote (§2.1). Mas a saída dele — a cobertura entre requisito e tarefa — **é derivada em toda leitura, nunca armazenada**, então não há o que envelhecer nem o que restaurar: some junto com o plano e volta junto com ele.

### 3.6 · Retrato do contrato dos hooks — `.claude/hook-contract.baseline.json`

- [confirmado] Ignorado por `.gitignore:45`; `git ls-files --error-unmatch` confirma que não está no índice.
- Conteúdo (chaves de topo: `root`, `entries`, `scripts`, `findings`, `measured`) carrega **caminho absoluto da máquina** no campo `root` — que é exatamente o critério da seção 3 do `.gitignore`.
- Regenerável pela varredura de contrato; a perda é do *baseline de comparação*, não do contrato em si.

### 3.6a · Retrato do custo do fim de turno — `.claude/stop-budget.baseline.json`

Nasceu em 2026-08-02. Irmão do §3.6, e a diferença de cobertura entre os dois é toda a graça. Ver `data-stores.md §A5a` para a anatomia.

- 🟢 **Este é RASTREADO** — `git ls-files` o encontra. Ao contrário do §3.6, ele não carrega caminho absoluto de máquina (só `plugin`, `script`, `linhas`, `timeout`), então **viaja no repositório e está coberto pelo backup do git**.
- **Consequência prática:** o gate de deriva do fim de turno funciona em qualquer clone; o gate de contrato (§3.6) não, porque o baseline dele mora só nesta máquina.
- Regenerável por um comando (`--stop-budget --json`). O que a perda custa é a **decisão**: recongelar é o ato de aceitar uma piora, e um retrato regenerado do zero aceita silenciosamente o estado atual, seja ele qual for.

### 3.6b · Os quatro retratos novos — `desacoplamento`, `suite-congela`, `custo-gatilho`, `fio-morto`

Nasceram nesta rodada e levaram a família de baselines de dois para seis. Anatomia em `data-stores.md §A5d`. A lista viva sai de `git ls-files '.claude/*.baseline.json'`.

- 🟢 **Todos RASTREADOS, logo COBERTOS pelo backup do git** — mesma situação do §3.6a e diferente do §3.6, que carrega caminho absoluto de máquina e por isso não viaja.
- **Consequência prática:** os checks **N**, **J**, **K** e o do fio morto funcionam em qualquer clone; o check **E** (contrato dos hooks) continua sendo o único da família que depende de um baseline local.
- **RPO/RTO:** o mesmo do repositório — perde-se o que não foi commitado, e restaurar é um `git checkout`.
- ⚠️ **O que a perda custa é a DECISÃO, não o dado.** Regerar qualquer um é um comando; um retrato regenerado do zero aceita, em silêncio, o estado atual — inclusive a regressão que alguém tinha barrado ontem. Vale sobretudo para o `desacoplamento.baseline.json`, cujas 95 entradas são dívida que alguém leu e decidiu tolerar.

### 3.20 · Memória de duração dos comandos — `~/.claude/andamento/`

Nasceu nesta rodada. Anatomia em `data-stores.md §B13`.

- 🔴 **SEM COBERTURA NENHUMA** — mora fora do repositório, em `${CLAUDE_CONFIG_DIR:-~/.claude}/andamento/`, como todo o bloco (B). Nenhum mecanismo o copia.
- 🔴 **É o único ativo do inventário que NÃO é reconstruível nem por comando nem por um evento passado.** Grafo e baselines se regeneram; atas e journal registram algo que aconteceu e pode ser relido. Aqui o dado *é* a estatística acumulada: a mediana de uma suíte só existe porque ela rodou dezenas de vezes nesta máquina.
- **RPO: total. RTO: semanas de uso.** Apagar não quebra funcionalidade — o narrador do fluxo 19 volta a sair só com o relógio, sem estimativa —, mas a memória recomeça do zero e só volta com o tempo.
- **Nada acusa a perda.** Não há verificador que leia esta pasta; um `rm -rf` passaria despercebido até alguém notar que as estimativas sumiram. É lacuna declarada, não cobertura.

### 3.7 · Ledger do intent-guard — `<projeto>/.claude/intent/`

- [confirmado] Duplamente invisível: `.gitignore:22` **e** `.git/info/exclude:18` (`.claude/intent/`). O segundo é escrito pelo próprio código: `ensure_exclude()` em `plugins/intent-guard/lib/ledger.py` resolve `git rev-parse --git-path info/exclude` e acrescenta a linha — ignore **local**, nunca tocando arquivo versionado.
- [confirmado] **57** arquivos, **716K**: `ledger.jsonl`, os `audit-*.json` e seus marcadores `.applied`.
- Natureza: append-only com lock. `append()` só escreve; `fold()` deriva o estado vivo; `locked()` usa `fcntl.flock` para load+append atômico, evitando ids `r-N`/`p-N` duplicados quando hooks concorrentes chamam ao mesmo tempo.
- [confirmado] O plugin está **desligado** nesta máquina (`intent-guard@pedro-plugins: False` em `enabledPlugins`) — o ledger existente é histórico parado, não fluxo vivo.
- Coberto por teste [confirmado, rodado nesta sessão]: `python3 plugins/intent-guard/lib/test_ledger.py` → `test_ledger: OK`.

### 3.8 · Cache de suite verde — `~/.claude/green-suite/`

- [confirmado] Fora do repo por desenho: `_shared/green-cache.sh` define `GREEN_SUITE_DIR="${GREEN_SUITE_DIR:-$HOME/.claude/green-suite}"` com o motivo no cabeçalho — *NUNCA dentro do plugin, o cache `${CLAUDE_PLUGIN_ROOT}` é reescrito a cada bump de versão*.
- [confirmado] **35** arquivos, **140K** (eram 48 / 192K — a poda de 7 dias alcançou os mais velhos).
- **Perder isto não custa nada.** A semântica é fail-open na direção segura: qualquer erro vira MISS e a suite roda. TTL por linha em `GREEN_SUITE_TTL_SECS` (default `86400`), e `green_cache_mark()` faz `find "$GREEN_SUITE_DIR" -type f -mtime +7 -delete` — o próprio código já poda. É o único depósito deste documento cuja perda é um não-evento.
- Costura verificada nos dois lados [confirmado]: a fonte é `_shared/green-cache.sh`, as cópias vendoradas são `plugins/qa-loop/lib/green-cache.sh` e `plugins/ship/hooks/green-cache.sh`, e o consumidor concreto é `plugins/ship/hooks/pre-deploy-test-check.sh`.

### 3.9 · Aprendizado cross-projeto do qa-loop — `~/.claude/qa-loop/journal/`

- [confirmado] **76K**, **2** arquivos no diretório `journal/`. `plugins/qa-loop/skills/qa-loop/SKILL.md` nomeia `~/.claude/qa-loop/journal/telemetry.jsonl` ("sobrevive a reinstalar o plugin") e `~/.claude/qa-loop/journal/learnings.md` (cross-projeto, acumula).
- Sobreviver a reinstalar o plugin não é sobreviver a perder a máquina. Este é o depósito cuja perda é irrecuperável por natureza: acumulado ao longo de rodadas, não regenerável.

### 3.10 · Estado do live-sync do `/visual` — `~/.claude/visual-state/`

- [confirmado] `plugins/visual/server/visual_server.mjs` define `const STATE_DIR = path.join(os.homedir(), '.claude', 'visual-state')` e escreve `<session>.json` mais um `latest.json` a cada POST do browser.
- [confirmado] **282** arquivos, **1,3M**. Continua sem prune.
- Costura verificada nos dois lados [confirmado]: `visual_server.mjs` escreve `latest.json`; `plugins/guardrails/hooks/scope-cop.sh` lê o mesmo caminho — `VISUAL_STATE="$HOME/.claude/visual-state/latest.json"` — para descobrir se há plano em curso. Um lado escreve, o outro lê, hoje.
- Perda: o estado por sessão é descartável (o HTML é regerado); o `config.json` é o que dói menos e some mais fácil.

### 3.11 · Preferência do `/visual` — `~/.claude/visual-state/config.json`

- [confirmado] Estado real na máquina, lido nesta sessão:
  ```json
  { "auto_mode": false,
    "auto_triggers": { "plan_min_items": 3, "decision_min_options": 2,
                       "diagnostic_min_problems": 3, "explanation_min_lines": 40 } }
  ```
- [confirmado] O default de fábrica é o contrário: `plugins/visual/skills/visual/config.default.json` traz `"auto_mode": true`. O arquivo versionado é a **semente**, não o valor vivo — o `SKILL.md` manda explicitamente ler o `config.json` e não presumir.
- **Consequência de durabilidade:** perder `~/.claude/visual-state/config.json` não perde dado, mas **inverte comportamento** — a máquina volta a `auto_mode: true` na próxima semeadura. É a perda mais barata em bytes e a mais visível em uso.

### 3.11a · Banco de lições de clareza — `~/.claude/visual-state/licoes-clareza.json`

- [confirmado] **35 KB · 65 lições** nesta máquina. Escrito por `plugins/visual/lib/clareza.py` (`registrar`); lido por ele (`licoes`, `check`) e por `plugins/visual/lib/visual_page.py`, que **recusa a página** que traz um termo já reprovado.
- 🔴 **É o único depósito de (B) que NÃO se regenera.** Todos os outros são cache, sessão ou preferência: apagados, voltam sozinhos ou custam um comando. Este é **conhecimento acumulado com custo de aquisição real** — cada lição nasceu de uma reprovação de um leitor externo sobre uma página específica, e a reprovação não acontece de novo se o arquivo sumir. As 5 de fábrica voltam (moram no código, em `clareza.py:SEMENTE`); **as outras 60, não**.
- **Cobertura hoje: NENHUMA.** Ele mora em `~/.claude/`, fora de todo repositório, e nenhuma das rotinas da seção 2 o alcança. Perdê-lo é silencioso: o `carrega()` cai na semente sem erro, e a única pista é o contador do `licoes` voltar a 5.
- **Consequência prática:** o mesmo defeito de escrita volta a passar, e volta a ser descoberto pelo mesmo caminho caro — uma página inteira escrita, reprovada por um leitor, e reescrita.
- **Conserto barato, ainda não feito:** ele é um JSON pequeno e append-only por natureza; versioná-lo no repositório (ou copiá-lo junto do `config.json`) o levaria de "sem cobertura" a "coberto pelo git" sem nenhum mecanismo novo.

### 3.12 · Logs dos vigias de edição e de pergunta — `~/.claude/guardrails/`

- [confirmado] **680K**. `plugins/guardrails/hooks/scope-cop.sh` define `HOOK_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/guardrails"`, com `MODE_FILE="$HOOK_DIR/scope-cop.mode"` e `LOG_FILE="$HOOK_DIR/scope-cop.log"`; `plugins/guardrails/hooks/askq-humanize.sh` usa `HOOK_DIR="$HOME/.claude/guardrails"` e `LOG_FILE="$HOOK_DIR/askq.log"`.
- ⚠️ [confirmado] Os dois resolvem o diretório de forma **diferente**: o scope-cop respeita `CLAUDE_CONFIG_DIR`, o askq usa `$HOME` fixo. Numa máquina com `CLAUDE_CONFIG_DIR` setado, os dois logs caem em pastas distintas.
- Auto-poda embutida: ambos truncam o log (`tail -n 2000` no scope-cop, `tail -n 1000` no askq). O arquivo não cresce sem limite — e isso significa que **o registro antigo já é descartado por desenho**, antes de qualquer questão de backup.
- Ao lado dos logs há sentinelas por sessão (`scope-cop.blockstreak.<session-id>`, `askq.count.<session-id>`), descartáveis.

### 3.13 · Batidas do juiz de forma do relato — `~/.claude/state/forma-relato/`

**Código novo desta rodada.** `plugins/bootstrap/hooks/stop-forma-relato.py` é um hook `Stop` que chama um modelo (`claude -p --model` com `FORMA_RELATO_MODEL`, default `haiku`) e só roda quando a resposta é um **relato** — definido no próprio arquivo como *pelo menos um bloco de código E ≥ `MIN_PROSA = 2` linhas de prosa*.

- **Ativação confirmada** [confirmado]: está no array `Stop` de `plugins/bootstrap/hooks/hooks.json`, com `"timeout": 30`, ao lado do `stop-prose-ceiling.py`.
- **O que ele escreve:** `batida()` acrescenta uma linha JSON por execução em `<CLAUDE_CONFIG_DIR>/state/forma-relato/batidas.log`; e um arquivo-contador por (sessão + hash da resposta) para o anti-loop de `MAX_BLOQUEIOS = 2`. O diretório sai de `ESTADO`, que aceita override por `FORMA_RELATO_STATE` — [confirmado no comentário do código] a var própria existe porque isolar o teste via `CLAUDE_CONFIG_DIR` tirava a credencial do `claude -p` junto e o juiz passava a aprovar tudo por fail-open.
- **Por que o log é o ativo, e não subproduto:** o hook é fail-open em tudo que não seja reprovação explícita — sem `claude` no PATH, timeout, rc≠0 ou veredito ilegível, ele **passa**. Sem `batidas.log`, *"o juiz não está barrando"* e *"o juiz não está rodando"* são indistinguíveis. O log é a única prova de qual dos dois é o caso.
- **Estado real desta máquina** [confirmado, lido nesta sessão]:
  ```bash
  $ wc -l < ~/.claude/state/forma-relato/batidas.log
  228
  $ python3 -c "..."   # contagem por motivo, e veredito dos que julgaram
  {'sem texto': 74, 'nao e relato': 79, 'julgou': 50, 'stop_hook_active': 25}
  vereditos: {'passa': 30, <20 reprovações, cada uma com o defeito em texto livre>}
  ```
  ✅ **Mudou de estado nesta rodada.** Na anterior eram 12 batidas, todas `sem texto`, e o juiz nunca tinha chamado o modelo. Hoje ele julgou **50** vezes, aprovou 30 e reprovou 20. `~/.claude/state/` foi de 48K para **204K**, e o diretório do juiz responde por **104K** disso.
- 🔴 **A perda passou a ter conteúdo, não só contagem.** Cada uma das 20 reprovações grava o defeito em texto livre no campo `veredito` — frases como *"Resultado no parágrafo 3, primeira linha não diz nada"*. **Esse texto não existe em nenhum outro lugar**: não é derivável do transcript, não é regenerável (exigiria re-julgar cada resposta com o modelo), e é a única lista escrita de onde a régua de forma falhou na prática. Enquanto o log só tinha `sem texto`, apagá-lo custava um número; hoje custa o único corpus de calibração da régua.
- **Cobertura:** nenhuma. `~/.claude/` inteiro está fora de qualquer repo.
- Coberto por teste [confirmado, rodado nesta sessão] — `plugins/bootstrap/hooks/test_bootstrap_hooks.sh`:
  ```
  -- juiz de forma do relato
    ok   resposta curta nao gasta modelo
    ok   relato bom passa
    ok   relato ruim reprova
    ok   o juiz respondeu de verdade (nao foi fail-open)
    ok   FORMA_RELATO=0 desliga o juiz
    ok   transcript inexistente e fail-open
  ```
  O quarto caso existe porque os outros três verdes não valem se o juiz estiver mudo.

### 3.14 · Contadores e furos do teto de prosa — `~/.claude/state/prose-ceiling/`

`plugins/bootstrap/hooks/stop-prose-ceiling.py` é o vizinho mecânico: roda em todo turno, custa zero token, e nesta rodada ganhou **a regra do veredito na primeira linha**.

- **Ativação confirmada** [confirmado]: primeiro item do array `Stop` em `plugins/bootstrap/hooks/hooks.json`, `"timeout": 10`.
- **A regra nova, copiada do arquivo:** quando a última fala do usuário casa `PERGUNTA_FECHADA` e **não** casa `PERGUNTA_ABERTA` (pronome interrogativo abre pergunta que pede explicação), a primeira linha não-vazia da resposta tem que casar `ABRE_COM_VEREDITO` — senão entra o problema `"pergunta fechada sem veredito na 1a linha"`. O comentário registra o caso real que originou: a resposta trouxe a varredura inteira, com prova, e não dizia sim nem não.
- **O que ele escreve** em `<CLAUDE_CONFIG_DIR>/state/prose-ceiling/`:
  - `batidas.log` — uma linha por execução, inclusive as que aprovam;
  - `bypass.log` — uma linha por resposta que **furou** o teto (o hook desiste após `MAX_BLOQUEIOS = 2` para não travar a sessão);
  - um arquivo-contador por (sessão + hash do texto inteiro).
- **Estado real desta máquina** [confirmado]:
  ```bash
  $ wc -l < ~/.claude/state/prose-ceiling/batidas.log
  341
  $ python3 -c "..."   # contagem por motivo
  {'sem texto do assistente': 163, 'aprovou': 146, 'stop_hook_active': 25, 'barrou': 7}
  $ wc -l ~/.claude/state/prose-ceiling/bypass.log
  wc: .../bypass.log: open: No such file or directory
  ```
  O guarda **passou a barrar**: 7 bloqueios, contra 0 na rodada anterior. O `bypass.log` segue inexistente — nenhuma resposta reincidiu duas vezes na mesma chave, que é a condição para o hook desistir.
- **Consequência de durabilidade específica do `bypass.log`, e ela dobrou nesta rodada:** ele é o registro dos furos conhecidos, o próprio conserto sugerido pelo verificador é `rm` (§3.15), e agora **um segundo programa depende dele** — `ledger.py:furos_da_regua` conta cada linha do `bypass.log` como um furo e reporta ao dono (§3.14-b). Não há cópia; apagado é apagado, e o efeito deixou de ser só "o conformance esquece" para incluir "o dono passa a ver menos furos do que houve".
- **Volume dos três diretórios** [confirmado]: `du -sh ~/.claude/state` → **204K** (forma-relato 104K · prose-ceiling 96K · intent-guard 4,0K), contra 48K na rodada anterior.
- ⚠️ **Teto conhecido, documentado no cabeçalho do arquivo:** hook de plugin só carrega no `SessionStart` — sessão já aberta no momento da instalação fica descoberta até o próximo `/clear`.

### 3.14-b · A marca de "até onde o dono já viu" — `~/.claude/state/intent-guard/olhado`

Depósito **novo nesta rodada** (ver `data-stores.md` §B10), e o menor do inventário: um
arquivo com um número. Escrito e lido por `plugins/intent-guard/lib/ledger.py:furos_da_regua`.

- **Estado real desta máquina** [confirmado, medido nesta rodada]:
  ```bash
  $ ls -l ~/.claude/state/intent-guard/olhado
  -rw-r--r--  17 bytes
  $ python3 -c "…; print(ledger.furos_da_regua())"
  (20, 20, 1, PosixPath('~/.claude/state/intent-guard/olhado'))
  #  ↑ total, novos-desde-a-marca, nº de fontes que responderam
  ```
- **Cobertura: NENHUMA, e a perda é aceita** [confirmado — decisão desta rodada]. O arquivo
  vive fora do repositório, não entra em backup nenhum, e nada o replica.
- **O que se perde se sumir:** o "desde a última vez que você olhou" volta a valer o total
  inteiro — a contagem de furos aparece toda como nova. **O total não se perde**, porque ele
  é derivado dos logs do §3.13 e do §3.14, não deste arquivo.
- **Por que a perda é aceita:** o arquivo é um marcador de leitura, não um registro. O dano
  de perdê-lo é ver de novo um número que já tinha visto — enquanto o dado que importa (as
  linhas de furo) continua nos dois logs vizinhos. Recriar custa um `cmd_status`.
- ⚠️ **O que NÃO é aceito calado:** os logs de onde a contagem sai (§3.13, §3.14) continuam
  sem cópia, e ali a perda é real — o texto dos vereditos de reprovação não se regenera.

### 3.15 · Quem lê esses logs — `check_juiz_rodou` e `check_teto_rodou` no conformance

**Código novo desta rodada.** `plugins/bootstrap/lib/conformance.py` ganhou `check_juiz_rodou`, registrado ao lado de `check_teto_rodou` e `check_bypass_teto` na lista de checagens do módulo.

- **O que lê:** `check_juiz_rodou` monta `CLAUDE_DIR / "state" / "forma-relato" / "batidas.log"` e passa por `le_batidas()`, que devolve (contagem por motivo, idade da última em horas, resumo legível).
- **Como decide** (do próprio código):
  - arquivo ausente → desvio `"o juiz de forma nunca executou"`, com o conserto apontando para o array `Stop` de `plugins/bootstrap/hooks/hooks.json` — *hook fora dele é ignorado em silêncio e `claude plugin validate` passa mesmo assim*;
  - `mudo > julgou`, onde `mudo` soma os motivos que começam com `"juiz sem resposta"` → desvio `"o juiz esta mudo"`, com a causa comum nomeada: `claude -p` saindo com rc=1 e "Not logged in";
  - última batida com mais de 24h → desvio de silêncio;
  - senão → conforme.
- **Guarda de escopo:** as duas checagens saem cedo se `bootstrap@` não estiver ligado em `enabledPlugins` do `settings.json`. Acusar guarda ausente numa máquina que não instalou o guarda seria desvio inventado.
- ⚠️ **O furo do verificador continua no código, mas deixou de ser o caso deste disco** [confirmado]: com o `batidas.log` real de hoje (**228** linhas, `julgou` **50** e `juiz sem resposta` **0**), `mudo > julgou` é falso **por mérito** e a idade é recente — a checagem carimba "juiz de forma ativo" e desta vez ela está certa. O que não mudou: um log composto só de `sem texto` seguiria passando como saudável, porque o verificador cobre *não rodou* e *rodou e o modelo não respondeu*, e não cobre *rodou e nunca chegou ao modelo*.
- **Consequência de durabilidade:** esses `batidas.log` deixaram de ser log e viraram **entrada de um verificador**. Apagar `~/.claude/state/` não degrada só a auditoria retroativa — faz o conformance reportar "nunca executou" para um hook que está funcionando.
- 🔴 **E agora são DOIS verificadores lendo os mesmos dois arquivos, com filtros diferentes** [confirmado, li os dois]. O `conformance.py` conta **execuções** (`julgou` vs `juiz sem resposta`, para saber se o guarda está vivo); o `ledger.py:furos_da_regua` conta **reprovações** (`motivo == "julgou" and veredito != "passa"`, para dizer ao dono quantas vezes a régua foi furada). Mesmo arquivo de 228 linhas, respostas de naturezas distintas — "o guarda está ativo" e "20 furos". Apagar `~/.claude/state/` hoje quebra as duas leituras de uma vez, e cada uma falha de um jeito: uma acusa hook morto, a outra some com o histórico de furos (§3.14-b).
- Coberto por teste [confirmado, rodado nesta sessão]: `plugins/bootstrap/lib/test_conformance.py` traz `teste_juiz_de_forma_mudo()`, que semeia `state/forma-relato/batidas.log` num `CLAUDE_DIR` de mentira e afirma os dois desvios ("nunca executou" e "mudo"). Saída: `59 ok · 0 FAIL`.

### 3.15b · Interruptor da missão autônoma — `~/.claude/sovai/`

Nasceu em 2026-08-02 com o gate que mantém o `/sovai` no motor Workflow. Ver `data-stores.md §B11` para a anatomia.

- **Perder não perde trabalho, e isso é por desenho.** O conteúdo é interruptor (`ativo-<session_id>` é arquivo **vazio**; o que significa é existir) e contador (`bloqueios-<session_id>`). Sumindo o diretório, o gate volta a ser mudo e a próxima missão o recria.
- **O único conteúdo com valor de leitura é `desistencias.log`** — uma linha por vez que o cap de 3 estourou. É diagnóstico ("o gate desistiu N vezes, vá ver por quê"), não dado de trabalho. Sem cobertura, e a perda custa a série histórica dessas desistências. **Mesma classe do `bypass.log`** do teto de prosa (§3.14): log de desistência existe justamente para desistir não ser silencioso, então perdê-lo devolve o silêncio.
- ⚠️ **A exposição real aqui é a inversa da dos outros ativos: não é perder, é sobrar.** Missão interrompida antes da entrega (sessão morta, `/clear`, limite de sessão) deixa o `ativo-*` aceso, e **a sessão inteira segue sem despachar sub-agente** sem que nada explique. Não há poda por idade — o `scope-cop` ganhou `find … -mtime +1 -delete` no mesmo commit em que nasceu, e este não. `[confirmado — `pretooluse-sovai-motor.sh` não tem nenhuma chamada de poda]` Diagnóstico e conserto manual: `ls ~/.claude/sovai/` e `rm` do sinal órfão.
- 🔴 **O aviso acima deixou de ser hipótese em 2026-08-02** `[confirmado]`: dos **três** `ativo-*` no disco, dois eram de sessões de **outros projetos ainda vivas** (transcript mexido há 2 e 10 minutos). Elas seguiam sem despachar sub-agente sem que nada explicasse. O sinal é por sessão, então o estrago não se espalha — mas também nada o recolhe.
- ✅ **O que o cap cobria virou medição na mesma rodada** `[confirmado]`: com o sinal aceso, um Workflow de um agente completou e o `bloqueios-<sid>` não se moveu — o motor **não** passa pelo gate. O cap fica como rede contra mudança futura do runtime, não por dúvida sobre isto.
- 🔴 **A mesma classe de defeito reapareceu em 2026-08-08, por outro arquivo do diretório** `[confirmado]`: a `reservas/<sessão>__<motor>.files` de um motor morto ficou no disco, e o motor seguinte **recusou-se a executar qualquer passo** — os 54 caminhos que ele precisava tocar apareciam reservados por alguém que já não existia. Perder a pasta não custa nada; **sobrar custa a rodada inteira**. Diagnóstico: `ls ~/.claude/sovai/reservas/` — vazio é o normal.
- **Duas naturezas novas entraram sem cobertura, e uma delas tem valor de série** `[confirmado — `ls ~/.claude/sovai/`]`: `sinal-*`/`placar-*` são efêmeros de barra (perder não custa nada), mas **`duracoes-<projeto>.json` é a memória de quanto cada comando demora naquele projeto** — é dela que sai a estimativa mostrada ao dono. Perdê-la não quebra nada: a estimativa volta a ser *"primeira vez aqui, sem estimativa"* e a série se reconstrói sozinha com o uso. Sem cobertura, e o custo é aceitável por isso.

### 3.15c · Log do gate do anúncio — `~/.claude/state/anuncio-acao/`

Nasceu em 2026-08-02 com `plugins/visual/hooks/stop-anuncio-sem-acao.py`. Ver `data-stores.md §B11a` para a anatomia. **Ainda não existe no disco** — o hook só cria o diretório quando arma pela primeira vez.

- **Sem cobertura**, mesma classe do `batidas.log` do juiz de forma (§3.14): fora do repo, fora de qualquer backup, e a perda custa a série histórica.
- **O que a perda custa aqui é específico:** a detecção do gate é lexical e o teto disso é conhecido — promessa escrita fora dos padrões passa batido. O `batidas.log` é o **único** instrumento para medir se o léxico está largo ou estreito demais, e para auditar falso positivo depois do fato. Sem ele, ajustar o gate vira palpite.
- ⚠️ **Diferente do §3.14, nenhum verificador o lê.** O `conformance.py` cobra o `forma-relato` em duas checagens (`check_teto_rodou`, `check_bypass_teto`); este log nasce sem par, então **hook mudo não é acusado por ninguém**. `[confirmado — `grep -c anuncio-acao plugins/bootstrap/lib/conformance.py` devolve 0]`

### 3.16 · Kill-switches e flags de modo

- [confirmado] `~/.claude/intent-guard/mode` e `~/.claude/context-guard/mode` existem como diretórios na máquina; o `SKILL.md` do intent-guard descreve `off`/`on` no arquivo `mode` (vale para todas as sessões, sem reload) e `.claude/intent/off` para desligar por projeto.
- Nomes de env var, copiados literalmente dos arquivos lidos: `PROSE_CEILING` (`=0` derruba o hook inteiro), `PROSE_CEILING_MAX` (só ajusta o número — `TETO_PADRAO = 6`; valor 0 ou lixo cai no padrão), `FORMA_RELATO` (`=0` kill-switch, `=interno` é o desligamento silencioso do subprocesso do próprio juiz), `FORMA_RELATO_MODEL`, `FORMA_RELATO_STATE`, `CLAUDE_CONFIG_DIR`, `GREEN_SUITE_DIR`, `GREEN_SUITE_TTL_SECS`, `PEDRO_PLUGINS_REPO`, `PEDRO_PLUGINS_FORCE_SYNC`, `PEDRO_PLUGINS_THROTTLE_SECONDS`, `PEDRO_PLUGINS_VERBOSE`, `PEDRO_PLUGINS_HOOK_RUNNING`, `PROJECT_DOC_COFRE_DIR`.
- Sem cobertura, e o efeito da perda é inverter comportamento em silêncio — não perder dado. Mesma classe do §3.11.

### 3.16b · Config do servidor de visão — `~/.claude/vision.json`

Nasceu em 2026-08-03 com o plugin `vision` (commit `4a4b59d`, v0.1.0). Ver `data-stores.md §B12` para a anatomia.

`[TODO: sem cobertura declarada]` — fora do repo, sem cópia, sem backup. Detalhe abaixo.

- **Sem cobertura.** Fora do repo, sem cópia, e — diferente do `config.json` do `/visual` (§3.11) — **sem semente versionada**: `plugins/vision/vision_mcp.py` declara *"nunca um endpoint chutado"*. O arquivo é a única fonte do endpoint além das env vars `QWEN_BASE`/`QWEN_MODEL`/`QWEN_TIMEOUT`.
- **O que se perde se sumir:** o endereço do servidor VL privado de quem instala. A tool `see_image` para e devolve *"servidor de visão não configurado… crie ~/.claude/vision.json"* — até alguém redigitar a config. É perda de **comportamento**, não de dado: o valor não é derivável do repo, mas vive na cabeça de quem administra o servidor.
- **Mesma classe do §3.11 e do §3.16:** config de máquina cuja perda não apaga conhecimento acumulado — desliga uma capacidade até ser reconfigurada. A diferença para o §3.16: aqui a falha não é silenciosa — a tool acusa com instrução.

### 3.17 · Cofre de secrets — iCloud

- [confirmado] `cofre_paths()` em `plugins/project-doc/lib/journal.py` resolve nesta ordem: `PROJECT_DOC_COFRE_DIR` (override explícito) → `~/Library/Mobile Documents/com~apple~CloudDocs/Cofre` → fallback local `<projeto>/.claude/secrets/_local_cofre`. O nome do arquivo é `<basename>-<8 hex do sha1 do path absoluto>.env`, para dois projetos homônimos não colidirem.
- [confirmado] O diretório do iCloud existe nesta máquina e tem **25** entradas.
- **É o único depósito deste documento com cópia offsite que não é o GitHub** — e é offsite por acidente de local, não por política de backup. `stash_secrets()` chama `ensure_gitignore(project_root, ".claude/secrets/")` **antes** de escrever, justamente porque no caminho de fallback o cofre cai dentro do repo.
- O símbolo `scrub()` é o que alimenta o cofre: scorer em camadas (PEM → connection string → JWT → prefixos de provider → par JSON → `chave=valor` → prosa perto de token de alta entropia → marcação `‹revisar?›` na dúvida). Política declarada no código: *nomes e contexto SIM, valores NÃO*.
- Coberto por teste [confirmado, rodado nesta sessão]: `python3 plugins/project-doc/lib/test_journal.py` → `TODOS OS 123 CHECKS PASSARAM`.

### 3.18 · Estado por-sessão em `/tmp` e sentinelas de sync

- [confirmado] `plugins/context-guard/hooks/context-guard-reset.sh` remove `/tmp/claude-context-pct-<session>` e `/tmp/claude-context-warned-<session>` da própria sessão e faz prune de órfãos com `-mtime +1`. O comentário guarda o defeito anterior: o glob antigo apagava o sentinel de **todas** as sessões e rearmava o bloqueio das já abertas.
- [confirmado] `session-sync.sh` usa `LAST_SYNC_FILE="$HOME/.claude/plugins/.pedro-plugins-last-sync"` (existe, vazio, mtime de hoje 18:56) e `LOCK_DIR="$HOME/.claude/plugins/.pedro-plugins-sync.lock"` (não existe agora — o lock é criado com `mkdir` e removido por `trap ... EXIT INT TERM`; lock com mais de 300s é quebrado).
- Perda: nula em conteúdo. O pior efeito de apagar o `last-sync` é um ciclo de sync extra.

### 3.19 · Saída do `/visual` e do qa-loop no repo — `.claude/visual/`, `.claude/qa-loop/`

- [confirmado] Ignorados por `.gitignore:47` e `.gitignore:46`, na seção *retrato desta máquina*. `.claude/visual/` tem **100** arquivos (**5,2M**) nesta rodada, contra 84 na anterior; `.claude/qa-loop/` tem **4,0K**.
- **Cobertura: NENHUMA, e é a resposta certa.** `git check-ignore -v .claude/visual/` devolve `.gitignore:47` — o diretório mora na árvore de trabalho, parece protegido e está fora do índice. Não há push a dar, não há cópia em lugar nenhum, e nenhum backup o alcança. [confirmado]
- **A perda continua barata, e agora dá pra dizer por quê com número.** São HTML de apresentação, não fonte: quem os produz é o `/visual` a partir do plano (§3.5) e do estado do disco, que são os depósitos que de fato importam. Perder as 100 páginas custa reapresentação, não conhecimento.
- 🟡 **O que MUDOU nesta rodada não é a cobertura — é que a ausência dela passou a ter consequência mensurável.** Desde 2026-08-03 o diretório é auditável por `python3 plugins/visual/lib/regua_audit.py paginas`, que mede cada página contra a régua de texto. Saída desta sessão: **100 páginas · 83 com violação** (1283 duas-frases · 1042 teto-140 · 16 conectivo · 9 páginas sem perfil de gerador). [confirmado, rodado nesta sessão]
- **A auditoria não é depósito** — é derivada a cada execução sobre os arquivos do disco. Não há o que envelhecer nem o que restaurar: some com as páginas e volta com elas.
- ⚠️ **O que ENVELHECE é o número congelado no `.claude/limites-aceitos.md` (§2.6), e ele já envelheceu.** O registro guarda **99 páginas · 82 com violação** do dia da decisão; a medição de hoje dá 100 · 83, e a página nova (`2026-08-03-status-consolidado.html`, de hoje 16:22) está entre as reprovadas — contra a premissa escrita do próprio limite, *"a régua passa a valer para página nova"*. **Consequência de durabilidade específica:** o arquivo coberto pelo git guarda a saída de um comando cujo alvo **não** é coberto e muda sozinho. A cobertura protege o registro da decisão, nunca a validade dela. [confirmado — as duas medições comparadas nesta sessão]

---

## 4 · RPO / RTO

Números por classe, todos derivados dos mecanismos acima. [inferido] onde não houve exercício de restauração.

- **Código dos plugins + catálogo + docs** — RPO = *desde o último push manual*. [confirmado] Não há automação que empurre esses arquivos; o único push automático leva um arquivo só (§1.1). RTO = tempo de um `git clone` [inferido, não exercitado nesta sessão].
- **Manifest do bootstrap** — RPO ≤ 24h enquanto uma sessão for aberta dentro da janela do throttle (`THROTTLE_SECONDS` default `86400`) e o apply passar limpo. RPO = ∞ se o apply falhar em toda tentativa (o snapshot é pulado, por desenho).
- **Contrato de tier e registro de limites (§2.5, §2.6)** — mesma classe acima: RPO = *desde o último push manual*, RTO = um `git clone`. Nenhum dos dois tem push automático; o `r8-tiers.json` tem, em compensação, dois verificadores que acusam divergência entre as cópias antes do commit.
- **História anterior do repo (§3.1)** — RPO = ∞. Não há segunda cópia. RTO = irrecuperável se a máquina morrer.
- **Journal, ledger, atas, planos, grafo, `~/.claude/**`** — RPO = ∞ para todos. Nenhum tem cópia.
- **Cofre (§3.17)** — RPO = latência de sincronização do iCloud [inferido, não medido nesta sessão]. É o único com replicação real.
- **Green-cache (§3.8)** — RPO irrelevante: a perda é um cache MISS e a suite roda.

## 5 · Restauração testada

[confirmado] **Nenhuma restauração de backup foi exercitada nesta sessão, e não há procedimento de restauração escrito no repo.** O que foi exercitado e passou:

```bash
$ bash plugins/bootstrap/hooks/test_bootstrap_hooks.sh      # 36 ok · 0 FAIL
$ python3 plugins/bootstrap/lib/test_conformance.py         # 59 ok · 0 FAIL
$ python3 plugins/intent-guard/lib/test_ledger.py           # test_ledger: OK
$ python3 plugins/project-doc/lib/test_journal.py           # TODOS OS 123 CHECKS PASSARAM
$ python3 plugins/project-skills/lib/test_plan_state.py             # OK
$ python3 plugins/project-skills/lib/test_cobertura.py              # OK
```

O `test_ledger.py` ganhou nesta rodada o caso que prova a regra de leitura da marca do §3.14-b — e ele é do tipo que protege contra o pior modo de falha: com o diretório de estado vazio, `furos_da_regua()` tem que devolver `(0, 0, 0)`, e o comentário nomeia o defeito histórico que a asserção fecha — *"foi assim que o `bypass.log` ausente virou o elogio 'nenhuma resposta furou o teto' com o teto furado"*. Com as duas fontes semeadas, `fontes == 2` e o total é 3 (2 furos do teto + 1 reprovação do juiz; `passa` e `nao e relato` não contam). [confirmado, li os três casos]

Esses testes provam **round-trip de estado** (o snapshot devolve o manifest inteiro e é idempotente; o fold do journal reconstrói o estado vivo; o ledger sobrevive a append concorrente) — não provam restauração a partir de cópia, porque cópia não existe.

O caso mais próximo de restauração exercitado é o round-trip do manifest: `plugins/bootstrap/hooks/test_bootstrap_hooks.sh` roda o snapshot duas vezes e afirma `pedro-plugins continua com N plugins`, `graphify-guard continua desligado`, `intent-guard continua desligado`, `2a rodada e idempotente` — **70 ok · 0 FAIL** neste run. É a prova de que uma máquina nova reconstruída pelo manifest chega ao mesmo estado — para os **terceiros**, que é o que o manifest cobre.

⚠️ **O `N` não está cravado no teste, e essa é a única razão de a asserção não ter apodrecido.** A suíte deriva o número do próprio manifest na hora (`jq "[…] | .plugins[] | length"`), então o catálogo pôde ir de 19 para 24 sem quebrar nada. Um teste que carimbasse `19` teria ficado vermelho no primeiro plugin novo — ou, pior, teria sido "consertado" trocando o número, que é a forma de a asserção deixar de medir o que dizia medir.

---

## Resumo de exposição

Ordenado por custo da perda, do pior para o mais barato:

- 🔴 **A história do repo até hoje** — 395 commits e 6 tags de resgate, só nesta máquina (§0, §3.1). Irrecuperável e sem substituto.
- 🔴 **Journal do project-doc** (4,8M, 1133 eventos) e **aprendizado cross-projeto do qa-loop** — conhecimento acumulado, não regenerável, zero cobertura (§3.2, §3.9).
- 🔴 **Atas, planos ticáveis e ledger do intent-guard** — registro de decisão com prova anexada; append-only protege contra corrupção, não contra sumiço (§3.4, §3.5, §3.7). ⚠️ **Os planos subiram de classe nesta rodada:** com o bloco `requisitos` no topo do arquivo, num projeto sem PRD o `.plan.json` passou a ser também o único lugar onde o *pedido* está escrito, não só a execução (§3.5).
- 🔴 **Os 20 vereditos de reprovação do juiz de forma** — texto livre descrevendo cada defeito, sem cópia e sem regenerador; era contagem na rodada anterior, virou corpus nesta (§3.13).
- 🟡 **Batidas do juiz de forma e do teto de prosa** — entrada de **dois** verificadores desde esta rodada (o conformance, que pergunta se o guarda está vivo, e o `furos_da_regua`, que conta furos pro dono); apagar faz um reportar "nunca executou" para hook que funciona e o outro perder o histórico de furos (§3.13, §3.14, §3.14-b, §3.15).
- 🟡 **Preferências e kill-switches** (`config.json` do `/visual`, arquivos `mode`, `vision.json`) — perder não custa dado, custa **inversão silenciosa de comportamento**; o `vision.json`, em vez de inverter, para a tool com mensagem pedindo reconfig (§3.11, §3.16, §3.16b).
- 🟢 **Grafo do graphify, saída do `/visual`, baseline de hooks** — regeneráveis por comando (§3.3, §3.6, §3.19).
  ⚠️ **Com uma ressalva desde 2026-08-03:** as 100 páginas de `.claude/visual/` seguem descartáveis, mas o que as isenta da régua (`.claude/limites-aceitos.md`, §2.6) é um arquivo **coberto** que guarda a medição de um alvo **não coberto** — e a medição já saiu do lugar (99·82 registrados contra 100·83 medidos hoje). Cobertura de git protege o registro da decisão, nunca a validade dela.
- 🟢 **Contrato de tier e registro de limites** (`_shared/r8-tiers.json`, `.claude/limites-aceitos.md`) — rastreados e cobertos pelo remote (§2.5, §2.6). O valor volta com um `git checkout`; o **julgamento escrito ao lado dele** (o `porque` de cada tier, o motivo de aceitar cada limite) não sai de comando nenhum.
- 🟢 **Green-cache e sentinelas de `/tmp`** — perda é não-evento; o próprio código já poda (§3.8, §3.18).
  ⚠️ **Com uma ressalva desde 2026-08-03:** a sentinela `claude-plan-sessao-*` guarda **conteúdo** (o id do plano daquela sessão), não um sim/não. Perdê-la não perde trabalho — o resumo de fim de turno apenas volta a **relatar** em vez de afirmar, e a marca renasce no próximo passo marcado. Degrada a precisão, nunca o dado. `[confirmado — `plan_state.py:_plano_da_sessao` devolve `None` em qualquer erro de leitura, e o `brief` trata `None` como "não sei"]`
- 🔵 **Cofre no iCloud** — único com replicação de verdade, e por acidente de local, não por política (§3.17).
