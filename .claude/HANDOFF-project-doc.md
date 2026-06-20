# Session Handoff — PRD
Date: 2026-06-20 23:05
Project: /Users/pedroberaldo/PROGRAMACAO/PEDRO/pedro-plugins
Frente: project-doc (v3.1 IMPLEMENTADO no working tree + v3.2 PLANEJADO)
Session: 8fda82c3-6298-4aeb-8f0f-86972dab5a2c
LOG (ata verbatim): /Users/pedroberaldo/PROGRAMACAO/PEDRO/pedro-plugins/.claude/ata/LOG-8fda82c3-6298-4aeb-8f0f-86972dab5a2c.md

> ⚠️ Este repo tem MÚLTIPLAS frentes paralelas em sessões simultâneas. Este handoff é da frente **project-doc**. O `HANDOFF.md` (sem sufixo) é de OUTRA frente — **qa-loop** (sessão `d2b3016f`, concluída). NÃO confundir, NÃO sobrescrever um com o outro.

## Resumo
Sessão de duas metades. **(1) IMPLEMENTADO e verificado — project-doc "v3.1"** (workflow): o `/project-doc` full/`--deep` passa a minerar via **Workflow** (fan-out por concern) pra acabar com o "tira o pé" sob volume de contexto; mais **checagem ativa** do estado da doc, sequência **melhor-dos-dois-mundos** (backup→garimpo de nuances), subcomando **`journal.py adopt`**, e um **check de git-tracking** (#16) que garante que o journal não caia no gitignore. 117 testes verdes, ruff limpo, validate ok. **NÃO commitado.** **(2) PLANEJADO — "v3.2"** (grafo): o grafo vira documentação obrigatória (sempre gerado/atualizado, sem opção) e dirige a **leitura profunda do código** por concern. Plano salvo em `/Users/pedroberaldo/.claude/plans/o-seguinte-a-floofy-haven.md`. ⚠️ **Colisão de versão:** a outra sessão já commitou project-doc **3.2.0** (frente doc-guard) — a numeração do plano está obsoleta.

## Contexto e Propósito
A sessão abriu em **RESUME** do project-doc [d1][d2] (sessão limpa, `/tmp/claude-context-pct`=6). O Pedro mandou "commit push" [d3] e isso destravou uma confusão de estado que ocupou a 1ª metade: o working tree estava cheio de frentes de OUTRAS sessões (qa-loop, guardrails, grafo), o estado do git **mudou embaixo de mim 3× durante a sessão** (outras sessões commitando em paralelo), e a premissa "aqui é o project doc" [d4] teve que ser reconciliada. Verificou-se: o project-doc (plugin+doc) já estava 100% no remote [d5]; o **cache local está defasado** (scrubber ~300 linhas atrás do repo) [d6]. A 2ª metade começou com a pergunta-chave **"hoje o project-doc faz um workflow por definição?"** [d7] — resposta: **não, é pipeline single-agent**. Isso abriu o tema central [d8]: em codebase grande o agente "tira o pé" (segue a doc existente em vez de minerar). Daí saíram o v3.1 (implementado) e o v3.2 (planejado).

## Discussões e Decisões
- **O "tira o pé" e o workflow [d8].** Premissa do Pedro (verbatim): *"quando ele está dentro de um codebase grande, ele tirou o pé. Em vez de fazer o rastreio linha por linha... ele se poupou. Pegou o caminho fácil e seguiu a documentação que já existia. Sendo que a nossa proposta é minerar."* CONFIRMADO no código: a COLETA (Python, tiers 2-4) é determinística e não tira o pé; quem tira é a **projeção na janela única** (Tier 1 scan + Reconciliação). O fan-out por concern mata isso (working-set pequeno por agente).
- **Gatilho do workflow = por MODO [a1].** FULL e `--deep` → workflow; modos leves (incremental/index/pointers/`--rebuild`/migrate/verify/clean) → single-agent. Descartado "detectar tamanho" — a escala só dimensiona o fan-out, não decide se usa. Flag `--solo` de escape.
- **Reintegração de nuances = automática [a2].** O garimpeiro valida cada nuance da doc antiga contra o código: confirmadas reintegram sozinhas, não-confirmáveis → `[relatado]`, contraditas → `invalidate`. Sem checkpoint humano no meio.
- **Checagem ativa [d9].** Verbatim: *"caso já tenha documentação existente e não esteja no padrão atual, disparar a sequencia de backup do atual documentação full."* Classifica a doc (ausente / fora-do-padrão / no-padrão); fora-do-padrão (markers v1, sem markers, **v2-sem-journal**, ou `gen` antigo) → força backup + deep + garimpo. O marker passa a gravar `gen=<versão do motor>`.
- **Check de git-tracking [d10].** O Pedro pediu (verbatim): *"adiciona uma checagem ao final do project-doc que os documentos importantes tem que estar presentes no git. no tools o journal tinha ficado no gitignore."* Virou o **check #16** da Verification. Na mesma fala perguntou se a codebase é escaneada inteira ou "só índices preguiçosos" → resposta: **só índices** (allowlist + ls), não o código.
- **"Então regredimos?" [d11] — NÃO.** O Pedro suspeitou que a versão antiga lia tudo. CONFIRMADO no git: **nenhuma versão (v1/v2/v3) jamais leu o código de verdade** — a v1 diz literal *"scan these files (read only those that exist)"*. A leitura profunda é capacidade NOVA, não recuperação de regressão.
- **Ordem do grafo [d12].** O Pedro propôs grafo-primeiro + leitura + repasse, e perguntou qual ordem é melhor. Decidido: **grafo nas duas pontas** — mapa no início (orienta a leitura por fan-in), auditoria no fim (completude). A leitura profunda é o miolo. "Leitura cega primeiro" desperdiça contexto.
- **Grafo é documentação, obrigatório [d13] (a decisão-chave do v3.2).** Verbatim: *"grafo é documentação, tem que assumir que faz parte, não tem que ser opcional. Faz o grafo sempre que for documentar. Se não tiver atualizado, atualiza. É isso por padrão e acabou. Nem dá opção pro usuário."* Muda a postura atual do project-doc (SKILL.md:824: "só SUGERE, NÃO roda"). Viável via `graphify update . --force` (AST, sem LLM, ~30s, não-interativo).
- **Incorporar + planejar [d14][d15][d16][d17].** "e sim quero que incorpore" [d14] → o desenho entrou no plano v3.2. "Quer fazer um plano?" [d15] → sim. "monta o plano, compara com o que conversamos, revisa, corrige, salva, /handoff" [d16][d17] → feito (plano com seção de comparação explícita + correção da lacuna arquivo→concern).

## O Que Foi Feito
**v3.1 — IMPLEMENTADO E VERIFICADO nesta sessão (NÃO commitado). É registro, não ordem de refazer.**
- **`plugins/project-doc/lib/journal.py`** (+47): subcomando **`run_adopt()` + CLI `adopt --text --raw-kind`** — injeta uma nuance da doc antiga (que nunca foi minerada) como evento `discovered` de 1ª classe, passando pelo MESMO scrubber, id estável → idempotente. Reusa `_candidate`/`scrub`/`stash_secrets`/`append_events`/`fold`/`live_findings`. Também: split dos imports da linha 31 (lint do hook). **CONFIRMADO:** unit (8 checks, 109→117) + CLI E2E real (`new:true`→`new:false`, scrubbed:true, secret não vaza).
- **`plugins/project-doc/lib/test_journal.py`** (+55): `test_adopt()` + correção de lints pré-existentes (E401/E702/E741/F841) que o hook do guardrails passou a bloquear. **117 checks passam.**
- **`plugins/project-doc/skills/project-doc/SKILL.md`** (+121): seção nova **`## Workflow Engine`** (fronteira de modos, checagem ativa passo 0.1, casca↔fases A/B/C, script-molde estilo qa-loop, sequência melhor-dos-dois-mundos, schemas DOC_SECTION/NUANCE_CANDIDATES/STITCH_RESULT, gates JS); Invocation Modes (+`--solo`); marker **`gen=3.1`** nos 2 templates + Update Mechanism; **check #16** (git-tracking) na Verification.
- **`.gitignore`** (+3): `.claude/.project-doc/backups/` (efêmero; journal/ledger SÃO versionados).
- **`plugins/project-doc/PRD-v3.md`** (+21): addenda v3.1 (RF9 fronteira, RF10 checagem ativa, RF11 melhor-dos-dois-mundos).
- **Verificações verdes:** 117 testes · `ruff check` limpo · `sync-shared.sh --check` (não toquei collect_engine) · `claude plugin validate` passa (1 warning de versão, pré-existente).

## Em Andamento
**Nada pendente do v3.1** — está implementado, testado e coerente; falta só commitar (decisão do Pedro). O **v3.2 (grafo) é PLANO, não foi implementado** — é o próximo passo.

## Próximos Passos

### 1. Coordenar VERSÃO e COMMIT do v3.1 (bloqueia o resto)
- **Ação:** decidir o número de versão do v3.1 (workflow+adopt) e commitar os 5 arquivos meus (`journal.py`, `test_journal.py`, `SKILL.md`, `.gitignore`, `PRD-v3.md`). Commit cirúrgico (`git commit --only <meus paths>`) pra NÃO arrastar o que é de outra frente no working tree (README.md +202 é da frente qa-loop/doc-guard).
- **Critério de pronto:** commit com só os 5 arquivos do project-doc workflow; `gen` no SKILL.md batendo com a versão escolhida.
- **Problema:** ⚠️ a outra sessão (doc-guard) **já commitou project-doc 3.2.0** (`3e396ed`, `989cdb7`). A numeração do plano (v3.1=3.1.0, v3.2=3.2.0) está **OBSOLETA**. O v3.1 workflow provavelmente vira **3.3.0**; o v3.2 grafo, **3.4.0**. Confirmar com o Pedro.
- **Arquivos prováveis:** `plugins/project-doc/.claude-plugin/plugin.json` (HEAD=3.2.0), os 5 arquivos meus, e o `gen=3.x` na SKILL.md (3 lugares: 2 templates + Update Mechanism).
- **Decisão em aberto:** versão exata (3.3.0?) e se o bump entra no mesmo commit do workflow.

### 2. Sincronizar o cache local do project-doc (trivial)
Copiar `plugins/project-doc/` do repo por cima de `~/.claude/plugins/cache/pedro-plugins/project-doc/<versão>/` e `/reload-plugins`. O cache roda um scrubber ~300 linhas defasado (gotcha confirmado [d6]). Fazer quando a versão for commitada.

### 3. E2E real do workflow v3.1 (a prova que falta)
- **Ação:** rodar `/project-doc` full num repo de teste com doc **fora do padrão** (v2 sem journal) e observar: backup criado; N agentes (1/concern); doc nova minerada do código (não cópia da antiga); nuance verdadeira só-da-antiga reintegrada; nuance contradita invalidada; `findings.jsonl` sem secret cru.
- **Critério de pronto:** os 6 pontos observados (reproduzir a jornada, não só ler o DOM).
- **Problema:** o workflow foi desenhado e os blocos testados isoladamente (adopt unit+E2E), mas o fluxo full-via-workflow nunca rodou ponta-a-ponta.
- **Arquivos prováveis:** SKILL.md (Workflow Engine), um repo de teste sintético.
- **Decisão em aberto:** nenhuma.

### 4. Implementar o v3.2 (grafo obrigatório + leitura profunda)
- **Ação:** executar o plano em `/Users/pedroberaldo/.claude/plans/o-seguinte-a-floofy-haven.md`. Em resumo: (A) passo 0 do full/`--deep` **garante o grafo sempre** via `graphify update . --force` (vira a postura SKILL.md:824 de "só sugere" pra "roda sempre, sem opção"); (B) a casca lê `graph.json`+`.graphify_labels.json` → arquivos por concern ranqueados por fan-in + god nodes + módulos/hyperedges → **mapa que dirige a leitura**; (C) cada agente-concern **lê o código-fonte real** da sua fatia na ordem do fan-in (caminho 1); (D) gate de **auditoria grafo×doc** (god node/comunidade sem cobertura → WARN). Mapeamento concern↔arquivo continua pela Detection Matrix; o grafo entra por dentro (ranking+relações).
- **Critério de pronto:** os 6 itens da "Verificação E2E" do plano — sobretudo: grafo recriado sozinho sem prompt; gotcha que só existe no CORPO de uma função é capturado (prova de leitura profunda).
- **Problema:** leitura profunda do código nunca existiu; é a entrega-fim que o Pedro quer.
- **Arquivos prováveis:** `SKILL.md` (Workflow Engine + seção graphify + Detection Matrix), `PRD-v3.md` (RF12-14), `plugin.json` (bump), talvez um helper de parsing do grafo na casca.
- **Decisão em aberto:** grafo novo sem labels (criação inicial AST não nomeia comunidades — nomear é LLM, upgrade opcional); a versão do bump.

## Findings & Gotchas
<!-- verbatim -->
- **GOTCHA — o estado do git muda embaixo de você, várias vezes, porque há sessões paralelas no mesmo repo.** Nesta sessão o `git status`/`git log` mudou **3×**: a frente qa-loop commitou `2a16391` no meio; depois `727362f`; depois a frente doc-guard commitou `3e396ed`+`989cdb7` (project-doc 3.2.0). **SEMPRE rode `git status`/`git log` frescos antes de commitar/versionar — nunca confie no snapshot inicial nem no handoff.**
- **GOTCHA — `journal.py` NÃO é vendored; só `collect_engine.py` é.** O plano v3.1 dizia errado ("journal.py vendored, 2 cópias byte-idênticas"). Verificado: `find` mostra journal.py só em `plugins/project-doc/lib/`; collect_engine.py em `_shared/` + 2 plugins. O `adopt` (em journal.py) NÃO cria drift de vendoring.
- **GOTCHA — o lint hook do guardrails (`lint-and-typecheck.sh`) roda ruff no ARQUIVO INTEIRO a cada edit e BLOQUEIA o PostToolUse.** Editar um arquivo com lints legados (`;` múltiplos, imports juntos, `l` ambíguo) faz o hook bloquear por erros pré-existentes que não são seus. Tive que limpar E401/E702/E741/F841 do `test_journal.py` e a linha 31 do `journal.py` pra destravar — fixes de estilo seguros, mas tocam código alheio. Esperado, não é bug.
- **GOTCHA — `gen` (versão do motor no marker) vive na SKILL.md, não no journal.py.** O plano dizia "journal.py registrar gen" — mas a versão é do plugin (plugin.json) e o marker é escrito pela skill. O `gen` é a "versão do motor"; bump quando o motor muda de forma que a doc anterior deva ser reconstruída.
- **FINDING — `adopt`: id estável no texto RAW (antes do scrub), igual ao `run_update`.** Idempotência funciona no texto cru; 2ª adoção do mesmo texto → `new:false`, não duplica. `source.type="curated_from_doc"`.
- **FINDING — a doc do project-doc NUNCA leu o código de verdade (v1/v2/v3).** Tier 1 = Detection Matrix (allowlist: manifestos/configs/schemas/rotas) + `ls` pra estrutura. Confirmado no git: v1 = *"read only those that exist"*, *"list key files read"*. A leitura profunda (v3.2) é capacidade nova.
- **FINDING — `graphify update . --force` é AST puro, sem LLM, não-interativo, ~30s, idempotente** (`update.md:50-65`: pula a parte semântica se code-only). É o que torna "grafo sempre por padrão" viável sem queimar token. O labeling de comunidades (nomes) é LLM (skill `/graphify` completa), upgrade opcional.
- **DIVERGÊNCIA doc-vs-código — o PRD lista `graphify-out/` no tier 2, mas o `journal.py` não tem coletor pra ele.** O grafo NUNCA foi consumido como fonte. O v3.2 fecha isso.

## Detalhes Técnicos
- **Formato do grafo** (de exploração real, não chutado): `graph.json` nó = `{id, label, source_file, source_location:"L<n>", file_type, community, norm_label}`; aresta = `{source, target, relation, confidence:EXTRACTED|INFERRED, confidence_score, weight}`; `hyperedges` = workflows multi-nó. 2967 nós · 3084 arestas · 222 comunidades. **Fan-in NÃO é campo** — computar `in_degree[id]=count(edges where target==id)`. Comunidades nomeadas em `.graphify_labels.json` (ignorar "Community NNN"). Binário `graphify` em `~/.local/bin/`.
- **Onde o agente tirava o pé:** Tier 1 scan (`SKILL.md` ~:244-255, regra "no shortcuts") + Reconciliação (`SKILL.md` ~:291). O motor de coleta (`journal.py run_update`) retorna `{live[], stale_ids, ...}`.
- **Molde do Workflow:** `plugins/qa-loop/skills/qa-loop/SKILL.md` (casca faz toques humanos; Workflow roda em background, gates em JS).
- **Plano v3.2 completo:** `/Users/pedroberaldo/.claude/plans/o-seguinte-a-floofy-haven.md`. Visual: `.claude/visual/2026-06-20-sess-8fda82c3-plan.html`.
- **Commits relevantes no HEAD:** `3e396ed`/`989cdb7` (project-doc 3.2.0 doc-guard, frente alheia), `2a16391`/`727362f` (qa-loop, frente alheia), `ebc3b91`/`2f6594e` (project-doc v3 lote 1, base).

## Contexto Extra
- **Frentes paralelas no mesmo repo (CRÍTICO):** project-doc (esta), qa-loop (`HANDOFF.md`, sessão d2b3016f), doc-guard (commitou 3.2.0). O working tree mistura as três — ao commitar, use `git commit --only` nos paths do project-doc. NÃO sobrescrever o `HANDOFF.md` (é da qa-loop).
- O Pedro sobe/commita/versiona ele mesmo — por isso o v3.1 NÃO foi commitado nesta sessão (ele não mandou; mandou implementar + planejar + handoff).
- Modo da sessão: **i-have-adhd** (output enxuto) + explanatory + **xhigh effort**.
- A numeração "v3.1"/"v3.2" deste handoff é conceitual (workflow / grafo); os números de plugin reais a definir (3.2.0 já foi consumida pela frente doc-guard).
