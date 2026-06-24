---
name: handoff
description: 'Use pra preservar a sessão pra depois (antes de /clear, conversa longa, Pedro sinaliza uma pausa, depois de um marco) OU pra retomar o trabalho no começo de uma sessão nova/recém-limpa onde existe um .claude/HANDOFF*.md. Um comando, dois modos — detecta o estado do contexto (sessão cheia → salva, recém-limpa → retoma) e roteia. Workspace-aware: o handoff pertence ao projeto que a sessão tocou (resolve a fronteira .git dos arquivos editados), então funciona pra projeto avulso, monorepo (um HANDOFF-<módulo>.md por módulo) ou pasta guarda-chuva com projetos aninhados. Use também quando o Pedro disser "handoff", "salva a sessão", "retoma de onde paramos", ou rodar /handoff com argumento opcional [salvar|retomar].'
---

# Handoff — Salvar ou Retomar uma Sessão (auto-detectando)

## Visão Geral
Um único comando que preserva ou restaura a continuidade da sessão. Na invocação, detecta se você está numa **sessão cheia** (muito trabalho acumulado → **SALVA** um handoff) ou numa **sessão nova / recém-limpa** (→ **RETOMA** do último handoff). O objetivo é permitir `/clear` sem perda de sentido — não só o estado, mas o raciocínio, as decisões, o contexto e a intenção.

**Isto NÃO é uma todo list — mas É executável.** É um briefing pro próximo Claude, escrito como se o leitor tivesse zero contexto (porque vai ter mesmo). As duas metades carregam o mesmo rigor: o **retrospecto** (o que aconteceu e por quê) E o **prospecto** (o que falta — cada passo carrega o requisito que o torna executável, não um rótulo que aponta pra outro lugar). Briefing e plano executável não são rivais; um bom handoff é os dois.

**Isto NÃO é /wrapup.** Wrapup é um retrospecto pro Pedro (o que foi bem, fricção, lições — reflexão humana). Handoff é um briefing operacional pro próximo Claude (continuidade do trabalho e do entendimento).

## Detecção de Modo — rode isto PRIMEIRO, toda vez

Decida **SALVAR** vs **RETOMAR** usando estes sinais, em ordem de confiança:

1. **Histórico da conversa atual (primário — sempre disponível, garante um fallback 100%).** Há trabalho acumulado substancial *nesta* sessão?
   - Sim (decisões, edições, um thread longo) → tende a **SALVAR**.
   - Quase vazia (este `/handoff` é a primeira/precoce ação depois de um `/clear` ou numa sessão nova) → tende a **RETOMAR**.

2. **`/tmp/claude-context-pct` (reforço objetivo, quando presente).** Leia: `cat /tmp/claude-context-pct 2>/dev/null`.
   - Ausente ou baixo (mais ou menos abaixo da metade do `$CLAUDE_CONTEXT_THRESHOLD`, default 80) → recém-limpa → **RETOMAR**.
   - Alto → sessão cheia → **SALVAR**.
   - Nota: o hook de reset do context-guard deleta esse arquivo no `/clear`/SessionStart, então um arquivo *ausente* já é em si um sinal de "sessão nova".

3. **Existe um handoff pra retomar? (guardrail).** Esta detecção roda ANTES do extrator, então ainda não há `scope` — faça uma checagem barata: `ls -t {cwd}/.claude/HANDOFF*.md 2>/dev/null` (o nome é dinâmico em monorepo, por isso o glob). Se o cwd for uma pasta guarda-chuva (sem `.git`), essa checagem rápida pode não achar — tudo bem: o RETOMAR (passo 1) faz a varredura completa nos projetos aninhados.
   - Tendendo a RETOMAR mas **nenhum** handoff existe (nem no cwd nem, no RETOMAR, aninhado) → nada a retomar → muda pra SALVAR (ou pergunta).
   - O guardrail anti-sobrescrita (não salvar duas vezes em < 5 min) é aplicado no SALVAR, passo 3, depois que o `scope.handoff_path` já é conhecido.

**Override explícito (pula a detecção):**
- `/handoff salvar` (ou "salva") → força **SALVAR**.
- `/handoff retomar` (ou "retoma") → força **RETOMAR**.

**Sempre anuncie o modo detectado antes de agir**, ex: *"Contexto em 76% / sessão cheia → vou **salvar**"* ou *"Sessão limpa + HANDOFF.md de 8min atrás → vou **retomar**"*. Se for genuinamente ambíguo, mostre o estado detectado e pergunte qual modo o Pedro quer.

---

## Modo: SALVAR — Preservar a sessão

### Quando sugerir proativamente
- A conversa está ficando longa (risco de compactação perder nuance)
- Pedro sinaliza uma pausa ("vamos parar", "por hoje é isso", "depois a gente continua")
- Antes de `/clear`
- Depois de um marco grande (breakpoint natural)

Prompt: "Quer que eu rode o /handoff antes?"

### Por que isso importa
A compactação silenciosamente remove nuance. Preserva fatos mas perde cadeias de raciocínio. "Decidiu usar Redis" sobrevive à compactação. "Decidiu usar Redis porque avaliamos Memcached mas o Pedro prefere persistência de dados, a latência é aceitável pro nosso caso, e temos experiência prévia do projeto X" — isso morre.

Pro Pedro especificamente — alguém que aprende por colisão — a sessão não é só o output de trabalho. É uma jornada de aprendizado. As discussões, os caminhos errados, os momentos "aha" e as explicações do "porquê" SÃO o valor. O handoff preserva isso explicitamente.

### O rito: LOG (verbatim, gerado por máquina) + PRD (você escreve)

O handoff tem **dois produtos**, e a divisão de trabalho é a regra de ouro:

- **LOG** (`{project_root}/.claude/ata/LOG-<sessão>.md`) — a **ata verbatim, cronológica**. É gerada **mecanicamente pelo extrator**, NÃO por você. Cada item (fala do Pedro, decisão de AskUserQuestion, rejeição com instrução, plano, tarefa, diagrama) recebe um **ID estável** (`[d3]`, `[a1]`, `[r1]`...). É a prova: nada de julgamento, nada de resumo, nada filtrado.
- **PRD** (`{project_root}/.claude/HANDOFF.md`, ou `HANDOFF-<módulo>.md` num monorepo) — a **vista normativa, por tema**, que VOCÊ escreve a partir do LOG. É o que o RETOMAR lê. O caminho exato vem de `scope.handoff_path` (ver Processo).

Por que o extrator gera o LOG e não você: o Pedro foi explícito — *"E o seu julgamento não serve. Vai no meu julgamento. Vai anotar tudo, vai carregar tudo."* Se você escrevesse o LOG, você filtraria. Tirando você do caminho do LOG, o "anotar tudo sem julgamento" é garantido por construção.

### Processo

1. **Rode o extrator** (ele gera o LOG verbatim + um manifest dos itens — mecânico):
   ```bash
   python3 "<skill_dir>/../../lib/extract_ata.py" --auto --session "$CLAUDE_CODE_SESSION_ID" --cwd "$(pwd)"
   ```
   `<skill_dir>` é a "Base directory for this skill" injetada ao carregar a skill; o extrator vive em `lib/extract_ata.py` na raiz do plugin (dois níveis acima). O `--session "$CLAUDE_CODE_SESSION_ID"` identifica o transcript desta sessão de forma **determinística** (a env var é o nome do `.jsonl`), o que evita pegar a sessão errada quando há várias no mesmo cwd (monorepo). O `--auto` ainda **agrega os transcripts de teammates** se houver clã. **NÃO passe `--out-dir`** — o extrator deriva o destino do projeto-raiz que ele resolve.
   A saída JSON traz `gate_items` (os IDs que o PRD DEVE referenciar), **`scope`** (`project_root`, `module`, `multi`, `modules`, **`handoff_path`** — onde gravar o PRD), **`prospective`** (`open_tasks` + `last_plan`), `log_path` e `manifest_path`.

2. **Complemente com estado de código** — rode git **no projeto-raiz**, não no cwd: `git -C "<scope.project_root>" log` e `git -C "<scope.project_root>" diff --stat`. (No guarda-chuva o cwd nem é repositório; o `.git` que importa é o do projeto que o `scope` resolveu.)

3. **Escreva SÓ o PRD** no caminho que o extrator resolveu (`scope.handoff_path`) — você **não toca no LOG**. O handoff **pertence ao projeto** que a sessão tocou (não ao cwd):
   - `scope.multi == false` → `{project_root}/.claude/HANDOFF.md` (projeto avulso — igual a sempre).
   - `scope.multi == true` com um `scope.module` → `{project_root}/.claude/HANDOFF-<módulo>.md` (monorepo: um por módulo).
   - **Antes de sobrescrever, cheque o escopo** (não escreva cego):
     - Se `scope.from_edits == false` (a sessão não editou arquivos — planejamento puro), o projeto-raiz foi **chutado pelo cwd**, não inferido do trabalho. **Confirme o destino com o Pedro** antes de gravar — sobretudo se `scope.project_root_is_boundary == false` (o cwd é uma pasta guarda-chuva, então o handoff cairia nela, não num projeto real).
     - Se `scope.module` é `null` mas `scope.multi == true` (monorepo sem edits claros num módulo), **ou** `scope.module_ambiguous == true` (empate de edits entre dois módulos) → **pergunte** ao Pedro a qual módulo este handoff pertence.
     - **Guardrail anti-sobrescrita:** se o `scope.handoff_path` já existe e foi escrito **< 5 min atrás** (ou é de uma frente claramente diferente do mesmo módulo) → suspeito (Pedro nunca salva dois seguidos) → **confirme** antes de sobrescrever.
   - O PRD agrupa por tema o que está no LOG. Para CADA id em `gate_items`, referencia `[id]` no ponto onde aquela fala/decisão é tratada (o gate confirma que nada se perdeu). Findings e gotchas entram **verbatim** — não parafraseie.
   - **Pré-preencha o prospecto a partir de `prospective`** (não escreva do zero quando há material): cada `open_tasks[i]` vira um passo de `## Próximos Passos` com os 5 campos. O `last_plan` depende do flag `likely_executed`:
     - `likely_executed: true` (houve commits/edits depois do plano) → **o plano JÁ foi executado nesta sessão.** Ele vira REGISTRO em `## O Que Foi Feito`, **NÃO** entra em `## Próximos Passos`. (Senão o próximo Claude acha que tem de reimplementar tudo.)
     - `likely_executed: false` → é candidato a próximos passos; refine-o como tal.
     - Refine o que o extrator deu; não o ignore.

4. **Atualize o índice** no MESMO projeto-raiz do LOG/PRD — `<scope.project_root>/.claude/ata/INDEX.md` (não no cwd) — uma linha por sessão: data, `<sid>`, módulo (se houver), link pro `LOG-<sid>.md`, e uma frase do que foi a sessão.

5. **Mostre o resumo ao Pedro.** O gate de completude verifica o PRD contra o manifest; se faltar algum `gate_items`, ele te diz e você completa antes de declarar pronto.

### Formato do HANDOFF.md (PRD)

```markdown
# Session Handoff — PRD
Date: {{AAAA-MM-DD HH:MM}}
Project: {{caminho absoluto do projeto-raiz — scope.project_root}}
Module: {{scope.module, ou omita a linha se for projeto avulso}}
Session: {{$CLAUDE_CODE_SESSION_ID}}
LOG (ata verbatim): {{project_root}}/.claude/ata/LOG-{{sessão}}.md

## Resumo
{{1-3 frases: do que foi a sessão e onde ela parou}}

## Contexto e Propósito
{{por que a sessão aconteceu, o objetivo macro; cada afirmação que veio do Pedro cita o id do LOG, ex: "...montar o rito [d1]"}}

## Discussões e Decisões
{{por tema; cada decisão com o "porquê", citando o id do LOG: "decidiu-se X [a1] porque Y, descartando Z [d6]". TODO id em gate_items aparece referenciado em alguma seção}}

## O Que Foi Feito
{{ações concretas: arquivos criados/modificados, commits, configs — com o contexto do porquê}}

## Em Andamento
{{o que ficou pela metade e exatamente onde parou; estado atual — ou "nada pendente" se a sessão fechou tudo}}

## Próximos Passos
<!-- Um passo = um bloco "### N." com os 5 campos abaixo. O extrator pré-preenche aqui as
     tarefas abertas + o último plano (campo `prospective` do JSON). Passo trivial (deploy quando
     o Pedro mandar, etc.): marque "(trivial)" no fim do título e use UMA linha, sem os 5 campos. -->

### 1. {{título curto do passo}}
- **Ação:** {{o que fazer concretamente}}
- **Critério de pronto:** {{como sei que terminou}}
- **Problema:** {{1 linha humana — o que falta ou está errado}}
- **Arquivos prováveis:** {{paths}}
- **Decisão em aberto:** {{as opções — ou "nenhuma"}}

### 2. {{título do passo trivial}} (trivial)
{{uma linha — passos triviais dispensam os 5 campos}}

## Findings & Gotchas
{{VERBATIM — descobertas técnicas e armadilhas, transcritas literais (não parafraseadas). Cite o id quando vier de uma fala/decisão}}

## Detalhes Técnicos
{{arquitetura, padrões, configs, paths, dependências, integrações}}

## Contexto Extra
{{preferências, constraints, domain insights que se perderiam sem registro}}
```

### Exemplo de "Próximos Passos" preenchido (o alvo — sem `{{}}`)

```markdown
### 1. Migrar o endpoint /sync para cursor-based pagination
- **Ação:** trocar offset/limit por cursor em `api/sync.ts:120`; cursor = `updated_at` do último item.
- **Critério de pronto:** `npm test -- sync.spec` passa e 3 páginas devolvem 0 duplicatas.
- **Problema:** offset pula itens em insert concorrente — bug reportado em produção.
- **Arquivos prováveis:** `api/sync.ts`, `api/sync.spec.ts`, migration nova.
- **Decisão em aberto:** manter offset como fallback por 1 release, ou cortar direto?

### 2. Subir a doc atualizada pro Notion (trivial)
Rodar `npm run docs:push` quando o PR mergear.
```

### Regras do SALVAR
- **O LOG é da máquina; o PRD é seu.** Nunca edite o LOG à mão. No PRD, nunca corte um direcionamento, nunca reescreva uma decisão a ponto de mudar o sentido, nunca omita um finding/gotcha.
- **Todo `gate_items` referenciado.** Cada id forte (`d`/`a`/`r`) do manifest aparece citado `[id]` no PRD. O gate bloqueia se faltar.
- **Findings & gotchas verbatim** — transcrição literal, não paráfrase (direcionamento explícito do Pedro).
- **Próximos Passos executável, não ponteiro.** Se um passo referencia outro documento, transcreva o essencial inline. Se o documento referenciado **também** não especifica a ação (só lista/menciona), o passo honesto é **"destilar a spec primeiro"** — não "ver doc X". Cada passo não-trivial carrega os 5 campos do molde; passo trivial usa o escape `(trivial)`. O teste: um terceiro executa o passo sem abrir outro doc nem fazer arqueologia.
- **Handoff de implementação CONCLUÍDA é registro, não ordem de refazer.** Se a sessão terminou de implementar algo (sinal: `last_plan.likely_executed: true`, ou você sabe que o plano virou código/commits): o grosso vai pra `## O Que Foi Feito`; `## Em Andamento` = "nada pendente"; `## Próximos Passos` só os follow-ups REAIS que sobraram (deploy, testes, decisões abertas) — **nunca** o plano que você acabou de executar. O PRD + o LOG juntos são o REGISTRO do que foi feito; quem retomar não deve reimplementar.
- **Completude > brevidade** — o PRD é granular; melhor longo e completo que curto com lacunas.
- **PRD é snapshot, sobrescrito; o LOG é histórico, append-only por sessão.** O git guarda o histórico do PRD; os `LOG-<sid>.md` guardam cada sessão.
- **O handoff pertence ao projeto, não ao cwd.** Sempre grave em `scope.handoff_path` (o extrator resolve o projeto-raiz pelos arquivos que a sessão tocou — sobe até o `.git`). Num monorepo, um por módulo (`HANDOFF-<módulo>.md`); avulso, `HANDOFF.md`. NÃO grave no cwd quando ele é uma pasta guarda-chuva — grave dentro do projeto real. Um handoff por módulo (slug puro, sobrescreve o anterior daquele módulo); se houver outra frente recente do mesmo módulo, pergunte antes.
- **Salva primeiro, pergunta depois** — escreva, depois mostre o resumo. Pedro edita o PRD se quiser (o LOG, não).
- **Sem secrets** — nunca inclua API keys, senhas, tokens. Paths e nomes de variável ok.
- **Paths absolutos pra arquivos externos** — ao referenciar arquivos fora do projeto (`~/.claude/...`), use o caminho absoluto completo (`/Users/pedroberaldo/.claude/...`), nunca `~/.claude/...` ou `.claude/...`.

---

## Modo: RETOMAR — Pegar de onde o último handoff parou

Lê o documento de handoff de uma sessão anterior e apresenta ao Pedro pra confirmação antes de tomar qualquer ação.

### Processo

1. **Ache o handoff — o handoff pertence ao projeto, então onde procurar depende de onde você abriu:**
   - **cwd é uma fronteira de projeto** (tem `.git` — projeto avulso ou raiz de monorepo): procure `{cwd}/.claude/HANDOFF*.md`. Avulso → um `HANDOFF.md`. Monorepo → vários `HANDOFF-<módulo>.md`; liste-os (módulo · idade · 1ª linha do `## Resumo`) e use `git status`/`git diff --name-only` pra inferir qual módulo você mexia por último → esse é o palpite de topo.
   - **cwd é uma pasta guarda-chuva** (sem `.git` — ex: você abriu em `PROGRAMACAO`): os handoffs estão **dentro dos projetos aninhados**. Varra os projetos (dirs com `.git` até ~3 níveis, ignorando node_modules/.venv/etc.) por `.claude/HANDOFF*.md` recentes; use `git status`/`git diff` de cada um como pista do que você mexia; liste e proponha o mais provável.
   - O LOG verbatim fica em `{project_root}/.claude/ata/LOG-<sessão>.md` (índice em `INDEX.md`). O PRD referencia ids como `[d3]`; abra o LOG quando precisar do texto exato.
   - Se nada for encontrado, diga ao Pedro e peça contexto.
   - **Sempre confirme o handoff escolhido antes de agir** (especialmente se houver mais de um candidato).

2. **Apresente o resumo (com a idade dele):**
   - Mostre há quanto tempo o handoff foi escrito (pelo mtime)
   - Mostre o que foi concluído
   - Mostre o que está em andamento e onde parou
   - Mostre os próximos passos
   - Mostre os problemas conhecidos
   - Se o handoff é antigo (arquivos mudaram desde então, ou muitos dias passaram), sinalize

3. **Valide o prospecto e recupere o que falta — ANTES de pedir confirmação (ativo, não passivo).**
   - Para cada item de "Próximos Passos": tem os 5 campos preenchidos (ou é `(trivial)`)? Um terceiro executaria sem abrir outro doc?
   - Se algum passo está **magro** (aponta pra outro doc sem a spec inline, ou falta Ação/Critério de pronto): **NÃO execute a partir da menção.** Faça a arqueologia primeiro — abra o LOG pelos `[id]`, o `last_plan`, o doc referenciado, rode `git diff` — e **monte um plano de recuperação concreto** (o que abrir, o que inspecionar, qual a ação real). Converta o passo magro num passo executável você mesmo.
   - Isso é a régua do Pedro: recuperar decisões/contexto ANTES de decidir ou executar trabalho continuado. O custo do prospecto fraco recai no RETOMAR — pague-o aqui, não no meio da execução.

4. **Peça confirmação:**
   - "Esse é o estado da última sessão. Quer que eu continue de onde parou, ou tem alguma mudança de prioridade?"
   - Espere confirmação explícita antes de fazer qualquer coisa

5. **Reconcilie com o código real ANTES de executar — depois trabalhe.** Antes de tocar em qualquer "Próximo Passo", rode git **no projeto-raiz do handoff que você retomou** (`Project:` no header dele, não o cwd): `git -C "<project_root>" log --oneline -10` + `git -C "<project_root>" status`, e leia os arquivos que o passo cita. Se o que o passo descreve **já está no código / já foi commitado** (caso típico: o handoff foi tirado logo após uma implementação concluída), **NÃO reimplemente** — reconheça como feito e siga só pro que de fato falta. O handoff é um REGISTRO do que aconteceu, não uma ordem de refazer. Só então pegue de "Em Andamento" / "Próximos Passos".

### Regras do RETOMAR
- NUNCA comece a trabalhar antes do Pedro confirmar
- NUNCA reinterprete o handoff — siga o que está escrito
- Se o handoff parece desatualizado (arquivos mudaram desde então), sinalize ao Pedro
- Se o Pedro dá contexto adicional que conflita com o handoff, pergunte qual tem prioridade
- Leia o arquivo de handoff por completo — não passe o olho nem pule seções
- **Prospecto magro → arqueologia ativa, não pergunta passiva.** Se um próximo passo aponta pra fora ou falta campo, recupere o contexto (LOG, `last_plan`, doc referenciado, `git diff`) e monte o plano de recuperação ANTES de apresentar — não devolva a lacuna pro Pedro como pergunta.
- **NUNCA reimplemente o que já está feito.** Handoff de implementação concluída é registro. Sempre confira `git log`/`git status` e o código antes de executar um passo; se já existe, marque feito e siga. Na dúvida entre "refazer" e "já está pronto", leia o código — não refaça.
