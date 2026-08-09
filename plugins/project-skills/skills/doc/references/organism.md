# Organismo — de-silo por costuras (o gate invertido)

Referência do suporte a **organismos** do project-doc. Carregue quando: a invocação
menciona organismo/monorepo-de-módulos, existe um `.claude/organism.yaml` no projeto,
ou ao curar/estender as costuras.

## O problema que isto resolve

Um **organismo** é um monorepo de módulos que se integram (ex.: um `.git` com
`tools/`, `mcp/`, `brain/`… que se chamam entre si). O risco não é técnico, é de
**atenção**: um agente trabalhando num módulo trata-o como ilha e ignora o blast-radius
nos demais — mesmo com a doc do todo carregada. Isto é **alocação de atenção**: o frame
da tarefa domina o processamento e contexto adicional não compete com ele. **Nenhum
texto/doc/grafo muda isso** — é como o modelo funciona.

Portanto a pergunta não é "como faço o agente enxergar o organismo" e sim **"como faço
o organismo não depender de o agente enxergar"**. A resposta é **mitigação em camadas
com checkpoints determinísticos**, não mais texto. Teto assumido: pega blast-radius de
módulo (forma grande); não pega violação semântica fina nem costura que ainda não existe.

## O princípio central: o SISTEMA afirma, o AGENTE refuta

Pedir ao agente que **produza** o mapa de impacto é teatro — o mesmo modelo ancorado no
módulo preenche o formulário a partir da mesma âncora (racionalização pós-conclusão). Só
a **assimetria** resiste:

- o sistema (o gate, a partir do `organism.yaml`) **afirma** as arestas: *"você toca
  `usuarios_acesso` → mcp e servico herdam"*;
- o agente só pode **aceitar** (endereçar a outra ponta) ou **refutar com citação
  verificável** (`arquivo:linha` que o gate confere por grep).

Refutar uma afirmação concreta é cognitivamente diferente de gerar um mapa em aberto —
não dá pra carimbar "não toca ninguém" porque o formulário já vem preenchido com quem toca.

## `organism.yaml` — o registro curado de costuras

Vive em `<raiz-do-organismo>/.claude/organism.yaml`. É **dado curado por humano** — a fonte
de precisão é a curadoria (globs cirúrgicos), NÃO um grafo bruto (que over-conecta por
transitividade e vira fadiga terminal). A skill pode **propor** entradas (ver "2ª projeção"),
mas o que entra é decisão humana.

```yaml
name: MEU-MONOREPO                 # nome do organismo
root_doc: .claude/CLAUDE.md        # doc-mestra do todo
canonical_graph: graphify-out/     # grafo canônico da raiz (cobre tudo)
modulos: [tools, mcp, brain, ...]  # os módulos que formam o organismo
golden_rule: >                     # regra de ouro comprimida (injetada no SessionStart)
  Isto é UM organismo, não N ilhas. Toda ação num módulo considera os demais.

defaults:
  exclude:                         # nunca casar aqui (worktrees/legado duplicam matches)
    - "**/.claude/worktrees/**"
    - "_repos-antigos/**"

costuras:
  - id: identidade-rbac            # slug estável (usado no state/log do gate)
    severidade: block              # block = deny 1x/sessão no 1º toque | warn = só loga
    grep_verificavel: true         # false p/ segredo que só vive em .env (refutação por grep impossível)
    aresta_msg: >                  # CURADA por humano — o gate imprime literal, nunca gera prosa
      Identidade/RBAC nasce no tools (usuarios_acesso). mcp e servico HERDAM.
      Mexeu em acesso → reavalie os dois.
    pontas:                        # tocar o glob de uma ponta afirma os módulos das OUTRAS
      - modulo: tools
        globs: ["tools/apps/hub/**", "tools/migrations/*access*"]
        simbolos: ["usuarios_acesso", "/api/exemplo/apps"]
      - modulo: mcp
        globs: ["mcp/access.py", "mcp/access.yaml"]
        simbolos: ["usuarios_acesso"]
      - modulo: servico
        globs: ["servico/overlay/src/acesso.py"]
        simbolos: ["usuarios_acesso"]
```

Regras de curadoria (não-negociáveis, aprendidas com o Fable):
- **Globs cirúrgicos — arquivos, não módulos.** `tools/**` faria todo edit no tools disparar
  (fadiga terminal). Aponte os arquivos que REALMENTE são a costura.
- **`severidade` começa quase toda `warn`.** `block` só para 2-3 costuras mais perigosas —
  senão você treina o agente a refutar no automático. Suba para `block` com base no log.
- **`aresta_msg` é humana e específica** ("mexeu em access → reavalie mcp e servico"),
  nunca genérica. É o payload acionável que muda a decisão.
- **`grep_verificavel: false`** para costuras cujo símbolo só vive fora do git (segredo em
  `.env`) — a refutação por citação não se aplica; documente evidência alternativa.
- **Valor com `: ` ou caractere especial → use bloco `>` ou aspas.** Um scalar plain com dois
  pontos no meio (`aresta_msg: mexeu no name: do compose`) é YAML inválido. Envolva em `>`
  (o padrão das `aresta_msg`) ou aspas. O parser stdlib toleraria, mas o PyYAML não — e a
  divergência entre máquinas é justamente o que queremos evitar. O `pattern_check` reporta
  `organism.yaml ilegível` se você errar isso.

**Parser stdlib (sem PyYAML):** o kit é stdlib-puro; se PyYAML faltar, `lib/organism.py` usa um
parser embutido que cobre o subconjunto do `organism.yaml` (mappings/listas por indentação,
inline lists `[a,b]`, block scalars `>`/`|` com chomping `-`/`+`, bool/null YAML 1.1, comentários),
com **paridade estrita testada contra PyYAML**. Construção fora do subconjunto → levanta erro
(nunca parse errado silencioso), e o hook faz fail-open. Ao estender o formato, adicione o caso ao
teste de paridade em `lib/test_organism.py`.

## As camadas (o que roda)

1. **Gate invertido (`pretooluse-organism-gate.sh`)** — o checkpoint ativo. No 1º `Edit`/`Write`
   de um arquivo-ponta de costura `block`, o gate DENY afirmando a aresta + blast-radius.
   **Anti-loop inegociável: 1 deny por (costura, sessão)** — o 2º toque passa (um gate
   bloqueante idêntico no ExitPlanMode já morreu por loop infinito; por isso o gate nasce no
   pré-Edit, com input estruturado, e degrada). Refutação: `echo 'arquivo:linha' >
   /tmp/claude-organism-gate-<sessão>/<costura_id>.cite` e repita — o gate valida por grep.
   **Log jsonl** de todo disparo desde o dia 1 (sem métrica não se distingue "gate funciona"
   de "agente aprendeu a ackar").
2. **Consciência (`sessionstart-organism.sh`)** — o enquadramento passivo. Em qualquer cwd
   dentro do organismo (sobe a árvore até o `organism.yaml`), injeta "1 organismo, N módulos,
   não N ilhas" + a regra de ouro + as costuras. **Cobre o pertencimento sem materializar
   routers** — app novo sem doc própria herda automaticamente.
3. **2ª projeção (a skill, ao gerar `architecture.md`)** — o passo de síntese que já mapeia
   "quem chama quem" **propõe** costuras candidatas ao `organism.yaml` (com o grafo canônico
   detectando cruzamentos de fronteira). O humano cura. Artefato de build; zero manutenção manual.
4. **Não vazar pros subagentes (convenção)** — ao delegar (Agent/Workflow) uma tarefa que toca
   costura, o blast-radius **viaja no prompt do subagente** (ele nunca viu a doc do organismo).
   Validável no script do Workflow (gate programático, não "lembrar a regra").
5. **Ratchets anti-decaimento** — o registro protege só o que existe; costura **nova** no diff
   exige entrada (senão congela) e todo silo pego na revisão humana vira entrada obrigatória
   (o gate ganha regression test de si mesmo, e a vigilância humana é amplificada, não substituída).

## O engine — `lib/organism.py`

Consumido pelos hooks (bash → JSON). Comandos:
- `match <abs_path>` → `{organism, root, hits:[{id, severidade, aresta_msg, grep_verificavel, ponta_tocada, blast_radius}]}`
- `marker <start>` → `{organism, root, name, modulos}` (está dentro de um organismo?)
- `brief <start>` → marker + `golden_rule` + `costuras` (pro SessionStart)
- `verify-cite <root> <id> <arquivo:linha>` → `{valid, reason}` (a refutação cita algo real?)

Fail-open na borda: sem `organism.yaml`, `match` devolve `[]` e todo hook passa. Stdlib + PyYAML.
Regression test em `lib/test_organism.py`.

## Relação com `--nested` e a cobertura

O `sessionstart-organism.sh` torna a relocação de routers (mover `<módulo>/.claude/CLAUDE.md`
→ `<módulo>/CLAUDE.md` para o ancestor-walk enxergar) **largamente redundante** para o
problema de pertencimento: o hook injeta a consciência em qualquer cwd sem materializar
arquivo. Use routers relocados só se quiser a doc detalhada do módulo visível ao walk — não
para o "não trate como ilha", que o hook já cobre.

---

# Conformação de organismo (Caminho C) — o de-silo da própria doc

O problema que ISTO resolve é diferente do gate invertido (acima). O gate trata **atenção**
em runtime (blast-radius numa edição). Esta seção trata **drift de documentação**: num
organismo, cada módulo herdou da época de repo separado uma árvore `<módulo>/.claude/docs/`
própria que o `/doc` da raiz **nunca tocava** → defasava até o fim dos tempos e, pior,
os hooks a surfaceavam como se fosse fresca (o agente "acha que está em 2025"). A raiz e o
módulo viravam **dois donos do mesmo fato**, sem regra de precedência.

## A topologia-alvo (uma verdade só)

- **Raiz — costuras (inalterado):** `<root>/.claude/docs/*.md` por concern = o TODO e as
  integrações cross-módulo.
- **Raiz — miolo dos módulos (NOVO):** `<root>/.claude/docs/modules/{módulo}/*.md`, **granular
  por concern**, gerado **cross-aware** (o agente módulo×concern enxerga o grafo do organismo +
  as costuras da raiz → documenta o miolo SEM re-silar). Granular por concern porque 1 arquivo
  não segura 8 concerns sem inflar/perder detalhe.
- **Módulo — router fino gerado (NOVO):** `{módulo}/.claude/CLAUDE.md` = ~20 linhas com o marker
  `project-doc:module-router` (ver **Module Router Template** em `templates.md`). Preâmbulo do
  organismo + redirect pra `<root>/.claude/docs/modules/{módulo}/` + 3-5 gotchas de
  **sobrevivência inlined** (pra sobreviver a sparse-checkout / sessão offline no módulo). **Não
  há mais `{módulo}/.claude/docs/`.** NÃO é ponteiro-burro: é gerado no mesmo run, sig-carimbado
  e coberto pelo census. O tradeoff (conteúdo mínimo em 2 lugares) é NOMEADO e **detectável**.

## Census — o mundo-aberto (a régua anti-drift)

`python3 lib/organism.py census <root>` (ou `lib/pattern_check.py --census <root>` p/ anexar
staleness) varre TODA doc project-doc do repo — filtrando o ruído (`CENSUS_PRUNE`:
worktrees/_repos-antigos/.next/node_modules/backups; o filtro é **load-bearing** — furo aqui =
doc de 2025 com carimbo de fresco) — e classifica em **4 classes** (design com o Fable):

- **canonical** — a árvore viva da raiz (`.claude/docs/*.md` + `modules/{m}/`) + o router gerado.
- **legacy-archived** — sob `_archive/` ou `.claude/legacy-pre-migracao/` ou marker
  `project-doc:legacy`. Preservado, invisível aos hooks.
- **pending-migration** — doc de um MÓDULO listado no `organism.yaml` SEM contraparte em
  `modules/{m}/`. É o legado a **MIGRAR** — **nunca arquivar cego** (é a única doc que o módulo
  tem). Distinguir pending de órfão exige o `organism.yaml` como manifesto de módulos.
- **orphan** — doc project-doc fora do canônico e fora de módulo listado (ou leftover de um
  módulo já migrado). Candidato a arquivar.

`CLAUDE.md` **sem marker** project-doc = **autoral** → fora da jurisdição (info, NUNCA ação —
arquivar um CLAUDE.md escrito à mão é o pior bug possível da feature). Pattern-válido (gen ok)
NÃO é sinal de canônico — o legado passa nesse teste; **só a localização decide**.

## O fluxo da conformação (o que o FULL faz num organismo)

Dispara quando o FULL roda na raiz de um projeto com `.claude/organism.yaml`. Ordem:

1. **Dry-run primeiro (`--plan`, read-only):** `pattern_check.py --plan <root>` imprime o que
   MIGRARIA/arquivaria + staleness, sem escrever nada. É o smoke-test — inspecione a
   classificação de cada doc real ANTES de escrever.
2. **Gerar o miolo:** para cada módulo `pending-migration`, fan-out por concern gera
   `modules/{m}/*.md` cross-aware, **minerando a doc legada do módulo como fonte (Tier 2)** —
   o miolo único (versões de deps, models, gotchas) é ABSORVIDO, não perdido.
3. **Gerar o router:** escreve `{m}/.claude/CLAUDE.md` (Module Router Template, com sig).
4. **Fundir os journals:** `journal.py fuse --project-root <root> --modules a,b,c` absorve os
   `<m>/.claude/.project-doc/findings.jsonl` no da raiz (dedup por `finding_id`, idempotente).
5. **Arquivar o legado:** move `<m>/.claude/docs/` (e o journal do módulo) para
   `_archive/legacy-module-docs-{m}-{data}/` com tarball de segurança. **Não deleta** (decisão
   do dono: absorver→arquivar). Reversível, não some do git.

## Gates da conformação (report+offer, hard-fail só em colisão)

- **Órfão distante que o run não toca → REPORTA loud + oferece arquivar** (com confirmação).
  **Nunca** hard-fail default: num repo com N módulos legados isso mataria o 1º run.
- **`--strict`** opt-in vira os reports em hard-fail (CI).
- **Hard-fail OBRIGATÓRIO (mesmo sem --strict): colisão direta com o output do run.** Se o run
  vai ESCREVER `modules/{m}/X.md` e existe `{m}/.claude/docs/X.md` não-conformado com conteúdo
  próprio ainda não absorvido → prosseguir cria dupla-verdade (o problema que a feature existe
  pra matar). Resolva inline. E router → doc canônica inexistente = bug → hard-fail sempre.

## Lazy com propagação (Fase 3 — custo)

Organismo FULL **não** regenera cego as 7 árvores. `organism.py dirty <root> <data>` devolve os
módulos SUJOS = (módulo cujos arquivos mudaram) ∪ (blast-radius das costuras que os arquivos
tocam) ∩ `modulos`. A **propagação pela costura é obrigatória**: mudar o `name:` da rede docker
no tools suja mcp+servico mesmo sem os arquivos deles mudarem — sem propagar, o lazy
reintroduz drift justo nas costuras (o que o organismo mais preza). `--deep`/flag explícito
força todos. `dirty` None (git falhou) → trate como TODOS sujos (fail-safe: nunca pula por
incerteza).

## Gen 3.7 + o census condicional (as duas camadas)

O `CURRENT_GEN` foi bumpado **3.6 → 3.7** (decisão do dono): toda doc `gen=3.6` fica
fora-do-padrão e re-roda o FULL. As duas camadas se complementam, não competem:

- **Gen 3.7 (global):** força o re-run de TODO projeto — é o gatilho de reconstrução. Projeto
  avulso re-roda o FULL normal (formato inalterado, só o carimbo de gen sobe).
- **Census (condicional a `organism.yaml`):** dentro desse re-run, num organismo, distingue o
  que **migrar** (`pending-migration`) do que **arquivar** (`orphan`) — o gate organismo-específico
  que o gen sozinho não sabe fazer. Reportado por `pattern_check.py --census`/`--plan`.

Trade-off assumido (o dono foi avisado): o bump global custa um re-run em todo projeto que usa a
skill, não só nos organismos. Em troca, nenhum organismo fica com doc `gen=3.6` silenciosamente
aceita — a régua "doc fora do padrão não é base confiável" vale para todos de uma vez.

## Loud sem quebrar o anti-loop (staleness)

O staleness virou TERNÁRIO por-scope (`pattern_check.py --project-staleness`): `stale` (arquivo
do `scope:` mudou desde `generated:`) · `fresh` · `unknown` (sem git/generated/scope —
**fail-LOUD**, nunca finge fresco). O "loud na leitura" vive no **`posttooluse-doc-read.sh`**
(PostToolUse injeta contexto, SEM `permissionDecision`) — quando o doc lido está vermelho,
avisa no momento do consumo. **NUNCA deny no Read de doc:** é a ação que libera o sentinel do
guard → um deny ali garante o loop que já matou o gate do ExitPlanMode. Block duro só DENTRO do
run da própria skill (código sob controle, sem interação com o harness).
