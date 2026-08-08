---
name: start-doc
description: "Conduz a concepção de um projeto em SEIS etapas de acordo, nesta ordem — autoral (metas de qualidade, restrições, contexto/fronteiras, estratégia, glossário), arquitetura (architecture-intent.md), interface (design.md, só para quem tem tela), jornadas (journeys.md), esquema de funcionamento (blueprint.md, o desenho de como o sistema funciona, com o diagrama do archify) e funcionalidades (features.md, a lista derivada do que já foi aprovado nas cinco anteriores — a skill propõe, o dono decide). Cada etapa tem documento próprio, é apresentada e REAPRESENTADA até o dono estar satisfeito, e só fecha com a aprovação dele gravada no frontmatter do documento. É a entrevista, não a mineração: a skill pergunta e grava a resposta do humano, NUNCA inventa conteúdo. Terceira skill do plugin project-doc, ao lado do /project-doc (minera tudo) e do /doc-touch (incremental). Use quando o usuário diz \"/start-doc\", \"vamos conceber\", \"começando um projeto novo\", \"documenta a intenção\", \"quais são as metas do sistema\", \"esse projeto não tem doc nenhuma\". Dispare PROATIVAMENTE quando: o projeto não tem CLAUDE.md nem .claude/docs/; o projeto está nascendo (repositório novo, poucos commits); existe doc minerada mas os documentos autorais estão ausentes ou com lacunas; ou o gate de plano barrou um plano por falta de documentação. A entrevista vem SEMPRE antes da mineração — o porquê guia tudo que vem depois."
---

# start-doc — a documentação que só o humano tem

## O que é

O `/project-doc` minera: lê arquivos, git log, transcripts e grafo, e escreve o que o código já sabe.
Existe uma classe de documentação que **nenhuma mineração produz**, porque a informação não está em
arquivo nenhum — está na cabeça de quem decidiu:

- o que o sistema **prioriza** quando não dá para ter tudo;
- o que é **inegociável**, e por quê;
- onde o sistema **termina** e o mundo começa;
- as poucas decisões que explicam o **formato** de tudo;
- o vocabulário que **só a equipe** usa.

Esta skill produz esses cinco — e mais o desenho da arquitetura, a personalidade da interface, as
jornadas, o esquema de como o sistema funciona e a lista de funcionalidades derivada de tudo isso.
Ela **entrevista**.

## As seis etapas de acordo

Concepção não é uma entrevista só. São **seis acordos, nesta ordem**, e a ordem é o próprio
argumento: arquitetura decidida sem as metas fechadas é palpite, jornada desenhada sem a interface
acordada é ficção, e lista de funcionalidade antes dos cinco acordos é palpite outra vez.

| # | Etapa | Documento em `.claude/docs/` | Quando |
|---|---|---|---|
| 1 | **Autoral** | `quality-goals.md` · `constraints.md` · `context.md` · `solution-strategy.md` · `glossary.md` | sempre |
| 2 | **Arquitetura** | `architecture-intent.md` | sempre |
| 3 | **Interface** | `design.md` — escrito pela skill `design-md`, não por esta | só projeto com interface |
| 4 | **Jornadas** | `journeys.md` | sempre |
| 5 | **Esquema** | `blueprint.md` + o diagrama do `archify` | sempre — antes de a lista ser derivada |
| 6 | **Funcionalidades** | `features.md` — derivada das cinco acima | sempre |
| 5b | **Revisão do esquema** | o mesmo `blueprint.md` | sempre, depois da 6 |

**A etapa 6 não abre sem `blueprint.md` aprovado.** Antes de propor um único item de `features.md`,
confira no disco que `.claude/docs/blueprint.md` existe e traz `status: approved` + `approved:` no
frontmatter. Sem isso, **pare e conduza a etapa 5** — lista derivada de um entendimento em que
ninguém bateu o martelo custa a curadoria inteira, item a item, e o erro só aparece no fim.

**A 5b é a 5 reapresentada, não uma sétima etapa.** Depois que a lista foi curada, o `blueprint.md`
volta pra mesa — funcionalidade removida é caixa que sai do desenho. Ela roda **sempre**, mesmo
quando nada mudou.

**Cada etapa fecha do mesmo jeito, e só desse jeito:** o documento é apresentado inteiro, sabatinado
com `/grill-me`, corrigido e **reapresentado** quantas vezes for preciso, e o de acordo do dono é
gravado no frontmatter do próprio documento por `hooks/doc-aprovar.sh` (`status: approved` +
`approved: {data}` + `approved-sig:`, a marca do corpo aprovado). Etapa aberta
não deixa a próxima começar.

O contrato completo — nomes de arquivo, frontmatter, roteiro e molde de cada documento — está em
`references/authorial-kit.md`. É a fonte única; não duplique aqui.

### O trio

| Skill | O que faz | Quando |
|---|---|---|
| **`/start-doc`** | entrevista o humano e conduz as seis etapas de acordo | concepção, e sempre que uma etapa tiver lacuna ou seguir sem aprovação |
| **`/project-doc`** | minera tudo e re-projeta a doc inteira | mudança estrutural, drift amplo, doc nunca minerada |
| **`/doc-touch`** | re-projeta só os docs que o diff tocou | entre FULLs, depois de um ciclo de código |

**A entrevista vem primeiro.** Num projeto sem documentação, `/start-doc` roda antes da mineração —
mesmo num codebase grande e antigo. O motivo é que o resultado da entrevista **guia a sessão inteira**,
não só o arquivo: sem saber o que o sistema prioriza, toda decisão posterior recomeça do zero.

### Quando falta repertório — a pesquisa de referências

Etapa travada por falta de **opinião** se resolve com `[PENDENTE]`. Etapa travada por falta de
**material** não: "quais peças este sistema tem?" é impossível para quem nunca viu três sistemas
parecidos por dentro. Quatro delas travam assim, e são estas:

| Etapa | Documento | O que falta ver antes de responder |
|---|---|---|
| estratégia | `solution-strategy.md` | como outros projetos decidiram o mesmo trade-off |
| arquitetura | `architecture-intent.md` | que peças e fronteiras sistemas parecidos usam |
| interface | `design.md` | que personalidade e que tokens produtos do mesmo nicho adotam |
| jornadas | `journeys.md` | por onde o usuário passa em produtos que já resolvem isso |

Nesse caso **OFEREÇA `/pesquisa-referencias`** — ela declara o custo antes (quantos agentes, quanto
tempo, quantas fontes), só começa com o aceite do dono, e volta com um dossiê de achados com a fonte
de cada um. Ofereça; não dispare sozinho, porque o custo é dele.

**O dossiê é pista, não resposta:** o achado da pesquisa não preenche campo autoral nem entra em
documento aprovado — ele volta para a entrevista como insumo da pergunta, e quem responde continua
sendo o dono.

## A REGRA DURA — a skill pergunta, a skill não responde

**Nunca preencha um campo autoral com conteúdo inferido.** Documentação de intenção fabricada por
máquina é ficção com aparência de autoridade — é **pior** que arquivo ausente, porque ninguém
desconfia de um documento que parece completo.

Sem resposta ⇒ o campo fica `[PENDENTE]`, o documento fica `status: draft`, e o relatório cobra.
Isso não é falha da rodada; é o estado honesto.

**O que a mineração PODE fazer aqui:** levantar **pistas** para a pergunta ficar concreta ("achei
versões travadas no lockfile — restrição dura ou só desatualizado?"). Pista alimenta a pergunta.
Pista nunca vira resposta.

## Quando dispara

**Explícito:** `/start-doc`, "vamos conceber", "documenta a intenção", "esse projeto não tem doc".

**Proativo (ofereça, não execute sem aval):**
- Projeto sem `CLAUDE.md` e sem `.claude/docs/` — não importa o tamanho do codebase.
- Repositório recém-criado / poucos commits — está nascendo, não há o que minerar ainda.
- Doc minerada existe, mas falta o documento de alguma etapa, algum tem `[PENDENTE]` aberto, ou
  algum está escrito e **sem `approved:`** — etapa escrita e não aprovada é etapa aberta.
- O gate de plano barrou um plano por falta de documentação (ver `hooks/pretooluse-plan-gate.sh`).
- Passaram-se meses do último `reviewed:` e o projeto mudou de forma — as metas envelheceram.

## Modos

- `/start-doc` — **concepção completa**: as seis etapas, na ordem, uma de cada vez, cada uma
  fechada com o de acordo do dono antes da seguinte. A etapa 3 (interface) só entra **se o projeto
  tiver interface** (ver `hooks/lib-has-frontend.sh` — não pergunte, verifique).
- `/start-doc <doc>` — só um. Nomes válidos: `quality-goals`, `constraints`, `context`,
  `solution-strategy`, `glossary`, `architecture-intent`, `journeys`, `blueprint`, `features`,
  `design` (este último só se houver interface). `features` exige as cinco etapas anteriores
  aprovadas — sem elas não há de onde derivar.
- `/start-doc blueprint` — **só a etapa 5**: o esquema de como o sistema funciona, em
  `.claude/docs/blueprint.md`, com o diagrama do `archify`. Serve tanto para a primeira rodada
  quanto para a revisão 5b, depois que a lista foi curada. Exige as etapas 1, 2 e 4 aprovadas — o
  ciclo é montado das passagens delas, e desenhar sem elas é o palpite que a regra dura proíbe.
- `/start-doc review` — **revisita**: lê os que já existem, mostra o que envelheceu (`reviewed:`
  antigo, `approved:` ausente, `[PENDENTE]` aberto, decisão citada que não existe mais) e pergunta só
  o que mudou. Nunca reescreve resposta do humano sem ele mandar.
- `/start-doc gaps` — **read-only**: lista as lacunas e para. Não pergunta nada. É o que o
  `/project-doc` chama no Tier 5 para saber o que cobrar. **Etapa escrita e não aprovada conta como
  lacuna** — `approved:` vazio é etapa aberta.

Prosa livre junto da invocação é contexto e vale como resposta antecipada — se o humano já disse
"o que importa aqui é não perder dado", **não pergunte a meta 1 de novo**: mostre o que entendeu e
peça confirmação.

## Fluxo

### 1 · Situar
Identifique a raiz do projeto (git root ou cwd). Detecte o que já existe: `.claude/docs/*.md`
autorais, `CLAUDE.md`, journal do project-doc, handoffs. **Nada é perguntado antes disso** — perguntar
o que já está escrito queima a sessão e irrita.

**Também decida aqui se `design.md` entra na entrevista** — o projeto tem interface? (`bash
hooks/lib-has-frontend.sh` expõe `has_frontend <dir>`; sinais: `.tsx`/`.jsx`/`.vue`/`.svelte`
versionado, `index.html`, framework de UI no `package.json`, ou `.swift`/`.kt`). Sem esses sinais, não
pergunte sobre design — a pergunta sem pista visível é o mesmo erro que perguntar o que já está
escrito.

**E a PRIMEIRA coisa da abertura: este projeto está dentro de um organismo maior?** Se estiver, o
que a raiz já decidiu vale aqui — perguntar de novo o que o dono já respondeu lá é o mesmo erro de
perguntar o que já está escrito. Rode, antes de qualquer pergunta:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/organism.py" inherited <raiz-do-projeto> --apresentar
```

A saída **já vem item a item, uma linha por item herdado, cada uma com a fonte** (`arquivo:linha`
do documento da raiz que decidiu aquilo) — quem monta a lista é o programa, a partir do organismo
real, nunca a sua memória. **Apresente essa saída literal** e percorra **um item por vez**: vale
aqui, vale com ressalva, ou não se aplica? A resposta do dono item a item entra nos documentos desta
etapa; o que ele confirmou herdado **não vira pergunta de novo**. Saída vazia (fora de organismo, ou
na própria raiz) → siga direto, sem mencionar herança.

### 2 · Minerar as pistas (barato, sem LLM)
Colha só o que serve de insumo para as perguntas:

```bash
git log --oneline | wc -l                     # o projeto está nascendo ou é antigo?
ls -d */ 2>/dev/null                          # forma do repositório
grep -rhoE '^[A-Z_]+(_URL|_KEY|_TOKEN|_HOST)=' .env.example 2>/dev/null | sort -u   # integrações externas
```

Mais: versões pinadas (lockfile, `engines`), limites de recurso e serviços (compose), biblioteca de
auth, onde o banco mora. Cada pista entra na pergunta **com a evidência** — o humano confirma ou
corrige, não adivinha o seu contexto.

E rode o motor das decisões caras, que na mesma saída entrega **as quatro perguntas de segurança**
— quem acessa o quê, que dado de pessoa fica guardado, quanto pode cair, o que fica exposto:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/decisoes_estruturais.py" <raiz-do-projeto>
```

As decisões caras são **condicionais** (só entram as que o projeto acendeu); as quatro de segurança
são **sempre as quatro**, e cada uma vem com o dado do projeto que a **confirma** (arquivo e trecho)
ou a **contradiz** (o que foi procurado e não existe). Ausência é dado: leve junto da pergunta.
A régua está em `references/authorial-kit.md`, em *Como conduzir a entrevista*.

### 3 · Entrevistar — uma pergunta por vez, uma etapa por vez
Siga o roteiro de `references/authorial-kit.md`. Dentro da etapa 1, **nesta ordem**: metas →
restrições → contexto → estratégia → glossário. A ordem não é estética: as metas são o critério que
os outros consomem. Entre as etapas, a ordem é a da tabela acima — e a próxima só abre com a
anterior aprovada.

- Use `AskUserQuestion` quando as opções forem enumeráveis (ordenar atributos, dura vs datada);
  pergunta aberta em texto quando for narrativa (o trade-off já decidido, o porquê de uma decisão).
- **Toda pergunta carrega a pista visível.** Sem insumo à vista, não pergunte — minere antes.
- **Por onde a pergunta chega quem escolhe é o usuário** — régua em **`regua-de-pergunta.md`**, ao
  lado deste arquivo (fonte: `_shared/regua-de-pergunta.md`, cópia derivada; não editar à mão).
- "Não sei" e "depois" são respostas válidas ⇒ `[PENDENTE]`. Não insista.
- Grave a resposta **literal**. Organizar em bullets e corrigir digitação é permitido; trocar o
  julgamento do humano por uma redação mais bonita, não.

**A etapa 5 (esquema) você abre com o ciclo montado, não com uma pergunta em branco.** Monte o
ciclo passo a passo a partir dos documentos **aprovados** (`architecture-intent.md`, `journeys.md`,
`quality-goals.md`), cada passo com a passagem que o originou ao lado — `arquivo:linha` —, e a
primeira pergunta é "deste ciclo, o que eu entendi errado?". O roteiro e o molde de `blueprint.md`
estão em `references/authorial-kit.md`; o diagrama é do `archify`, e a ausência dele **degrada em
voz alta no relatório**, nunca trava a etapa. **Só com essa etapa aprovada a 6 abre.**

**A etapa 6 (funcionalidades) é a única em que você fala primeiro.** A lista de `features.md` é
**derivada** dos documentos já aprovados — cada item nasce de uma jornada, de uma meta ou de uma peça,
e vai para a tela com a **passagem literal** que o motivou ao lado. Isso não afrouxa a regra dura:
**A skill propõe, o dono decide** — item que ele não confirmou é proposta, não funcionalidade
acordada, e não entra no documento aprovado.

#### A curadoria da etapa 6 — item a item, com a passagem ao lado

A lista derivada **não vai para o documento antes de passar item a item pelo dono**. Ela vai para
uma página do `/visual`, e lá cada funcionalidade é **um bloco `item`** — o componente de veredito
já existe, não invente outro. O contrato está no `visual_page.py` do plugin `visual`, achado pelo
nome — `python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/skills/start-doc/resolve-plugin.sh" visual lib/visual_page.py)" schema`
imprime o schema.

- **Um bloco `item` por funcionalidade.** No `title`, o que ela faz em uma linha; no `detail`, a
  **passagem literal** do documento aprovado que a motivou, com o arquivo de onde ela saiu — a
  procedência fica visível na hora de decidir, não depois.
- **Os três vereditos são os do spec, em valor de máquina: `keep`, `change`, `remove`.** O parser do
  outro lado depende deles; valor novo não existe. O que dá para trocar é só o rótulo humano, por
  `item_labels` — para esta etapa, `["✓ Manter", "✏️ Mudar", "✗ Remover"]`.
- **`keep` entra em `features.md`.** `remove` vai para a seção "Deixado de fora de propósito", com o
  motivo dele. `change` entra com o texto que **ele** escreveu no campo aberto do item, literal.
- **Item sem veredito não grava.** Rádio em branco não é `keep`: a funcionalidade fica de fora do
  documento e vira linha de cobrança no relatório do Passo 3. Silêncio nunca vira aprovação — nem
  aqui, item a item, nem na etapa inteira.

**Quem grava `features.md` é o programa, nunca você à mão.** Ele lê o retorno da página e é ele
que RECUSA o item sem veredito, dizendo qual é pelo nome — no JSON, rádio em branco chega como
`val: "keep"` com `touched: false`, e é exatamente esse par que a sua leitura a olho deixaria passar:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/curadoria_features.py" \
  --retorno  ~/.claude/visual-state/latest.json \
  --saida    .claude/docs/features.md \
  --proposta {spec.json da página}
```

Ele sai **2 sem escrever nada** enquanto houver item sem veredito — leve os que ele nomear de volta
pro dono e rode de novo. Quando todos têm veredito: `keep` entra pelo título, `change` entra pelo
texto que ele escreveu (literal), `remove` vai pra "Deixado de fora de propósito" com o motivo, e a
**Origem** de cada item sai do `detail` do bloco `item` — por isso o `--proposta` é o mesmo
spec.json que construiu a página. Frontmatter de um `features.md` que já existe é preservado.

**O que ele mudou fica registrado.** Quando o `change` recai sobre um item que **já está gravado** em
`features.md` (recuradoria, `/start-doc features`, `/start-doc review`), a troca não é edição no
arquivo: é `lib/historico.py`, que move o texto anterior para `features.historico.md` com data,
contexto e decisão.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/historico.py" reescrever .claude/docs/features.md \
  --antigo "### F-3 · {texto anterior, recortado único}" \
  --novo   "### F-3 · {o texto que o dono escreveu}" \
  --contexto "curadoria da lista de funcionalidades derivada das cinco etapas aprovadas" \
  --decisao  "{a fala dele, literal, que mudou o item}"
```

Na primeira gravação o item ainda não existe no documento — proposta corrigida antes de nascer não
tem o que arquivar, e o `historico.py` recusaria (item não encontrado). Aí grava direto; o histórico
começa a valer da segunda rodada em diante. Não escreva no `.historico.md` à mão: o formato é o que
o `listar` lê de volta.

#### A revisão 5b — o esquema volta pra mesa assim que a lista fecha

**Ela roda SEMPRE**, logo depois de `features.md` gravado, e não depende de você achar que mudou
alguma coisa: curar a lista muda o entendimento — funcionalidade removida é caixa que sai do desenho,
`change` reescrito é passo do ciclo que passou a fazer outra coisa. Rodar só "quando parece
necessário" é o mesmo que não rodar: quem acabou de derivar a lista é a pior pessoa para julgar se o
desenho dela ainda vale.

1. **Reapresente `blueprint.md` inteiro** pelo mesmo caminho do Passo 5 — página do `/visual`, bloco
   `aprovacao`, `doc_integral` com o corpo verbatim —, e junto dele a lista curada: quais itens
   saíram como `remove`, quais entraram por `change`. A pergunta é "com esta lista, o que o desenho
   passou a dizer errado?".
2. **Nada mudou ⇒ a etapa fecha sem tocar o arquivo.** O veredito `keep` no disco encerra a 5b, e o
   `approved:` que já estava lá continua valendo — reaprovar texto idêntico só trocaria a data.
3. **Mudou ⇒ a troca passa pelo histórico, nunca por edição direta no corpo.** O trecho anterior é
   texto que o dono aprovou; sobrescrever apaga o desenho em que ele bateu o martelo e ninguém
   consegue mais dizer o que mudou nem por quê:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/lib/historico.py" reescrever .claude/docs/blueprint.md \
     --antigo "{o trecho aprovado, recortado único}" \
     --novo   "{o trecho como ele ficou}" \
     --contexto "revisão 5b do esquema, depois da curadoria de features.md" \
     --decisao  "{o que na lista curada mudou o desenho — a fala dele, literal}"
   ```

   Ele grava a entrada em `blueprint.historico.md` (data, contexto e decisão) e **reabre a etapa
   sozinho**: `status:` volta a `ready` e `approved:`/`approved-sig:` saem, porque as três linhas
   falavam do texto que acabou de sair. O retorno traz `reabriu_aprovacao: true` — quando ele vier
   `true`, a 5b só fecha com a reapresentação e um `doc-aprovar.sh` novo.
4. **Grave o de acordo de novo** com `bash "${CLAUDE_PLUGIN_ROOT}/hooks/doc-aprovar.sh"
   .claude/docs/blueprint.md`, e só então rode o `rastreio_etapas.py` do Passo 4 — a lista de passos
   do desenho sem funcionalidade agora é sobre o desenho que sobreviveu à curadoria.

### 4 · Escrever
Um arquivo por documento em `.claude/docs/`, com o frontmatter do contrato (`authored-by: human`,
`status`, `reviewed`, `approved`) e o molde de `references/authorial-kit.md`. Nasce
`status: draft | ready` e `approved:` vazio — a aprovação é o passo seguinte, nunca a mesma escrita.

**Exceção: `design.md`.** Não escreva este à mão — depois de colher as respostas do roteiro
(personalidade, cor primária, tipografia, "don'ts"), **invoque a skill `design-md`** para formatar e
gravar `.claude/docs/design.md` no padrão `DESIGN.md` e validar pelo CLI oficial (`npx --yes
@google/design.md@0.3.0 lint`). Sem `node`/`npx`, ela já degrada pra checagem manual — diga isso em
voz alta no relatório, nunca finja que o CLI rodou.

### 5 · Apresentar, sabatinar e colher o de acordo — por etapa
Escrever **não fecha** a etapa. O ciclo é este, e ele repete até o dono estar satisfeito:

1. **Monte a página do `/visual` com o documento inteiro embutido — não apresente o texto no chat.**
   É o mesmo caminho da curadoria da etapa 6, com **um bloco `aprovacao`** no spec: `etapa` é o nome
   do que está sendo aprovado, `doc_integral` recebe o **corpo do arquivo verbatim** (o texto real,
   não um resumo dele) e `cards` é o índice, cada um ancorado num trecho literal desse corpo.

   ```bash
   PAGINA="$(bash "${CLAUDE_PLUGIN_ROOT}/skills/start-doc/resolve-plugin.sh" visual lib/visual_page.py)"
   [ -n "$PAGINA" ] && python3 "$PAGINA" build --spec {spec.json}
   ```

   - **Aprovação sem o texto integral na página o programa RECUSA** (sai 2, não escreve arquivo) —
     resumo de documento é a forma mais barata de comprar aprovação que não existe.
   - **O veredito volta pelo disco, não pelo chat.** Quando ele disser "ok"/"pronto"/"lido", leia
     `~/.claude/visual-state/latest.json` e pegue em `state.feedback` a entrada cujo `title` é a
     etapa: `val` vem nos valores de máquina `keep` | `change` | `remove` e `note` traz o que ele
     escreveu. `keep` fecha a etapa; `change` e `remove` voltam pro passo 3.
   - **Etapa sem veredito no disco continua aberta.** Rádio em branco não é `keep` aqui também, e
     página que você montou mas ele não respondeu não aprova nada.
2. **Sabatine** com `/grill-me` — ou `/grill-with-docs` quando já houver `CONTEXT.md` ou ADR para
   confrontar. É a sabatina que transforma texto escrito em acordo.
3. **Corrija e REAPRESENTE.** Cada objeção volta pro documento e o documento volta pra tela. Não há
   teto de rodadas: quem fecha o loop é a fala do dono, não o seu cansaço.
4. **Confira o que a etapa deixou sem dono** — antes de gravar. Rode, sem ninguém pedir:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/lib/rastreio_etapas.py" .
   ```

   Ele lê `journeys.md`, `features.md` e `blueprint.md` e devolve as listas do que ficou sem dono: **funcionalidade
   sem origem**, **jornada sem funcionalidade** e **passo do desenho sem funcionalidade** (passo do
   ciclo de `blueprint.md` que nenhum item de `features.md` atende). Ele **só conta — não escreve em documento nenhum**, e é por isso
   que roda aqui: conferência que edita texto aprovado reabriria a etapa pela marca
   (`approved-sig`). O que ele acusar entra no Passo 5 do relatório e vira pergunta ao dono; não
   conserte sozinho, e não segure o de acordo por causa dele — a lista é cobrança visível, não gate.
5. **Grave o de acordo** — só depois de ele dizer que está satisfeito — com o comando, nunca à mão:

   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/hooks/doc-aprovar.sh" .claude/docs/journeys.md
   ```

   Ele grava as três linhas de uma vez: `status: approved`, `approved: {data de hoje}` e
   **`approved-sig:`, a marca do CORPO aprovado** (`doc_marca`, de `hooks/lib-doc-mark.sh`).
   Aprovação digitada à mão nasce sem marca, e aí o de acordo volta a ser sobre um nome de
   arquivo em vez de sobre um texto: qualquer edição posterior no corpo passaria despercebida.
   O comando não toca o corpo — se tocasse, a marca mediria outro texto que ninguém aprovou.

**A sabatina não julga o documento.** Ela não aprova, não reprova e não decide se ficou bom o
bastante: ela é **como se chega** ao acordo. Quem aprova é o dono, e a aprovação mora no frontmatter
— nunca numa conclusão da sabatina, numa nota sua ou na sua memória da conversa.

**Silêncio não é aprovação**, e "tá bom" dito no meio de outra pergunta também não. Sem uma frase que
você consiga apontar, a etapa continua aberta e a próxima não começa.

**Correção achada DEPOIS do de acordo: registre, não reabra a etapa.** Grave uma linha
`correcao-pendente: {o que precisa mudar}` no frontmatter do documento e siga. Não escreva a correção
no corpo e não rebaixe o `status:` — o corpo é o texto que o dono aprovou, e mexer nele reabre a
etapa pela marca (`approved-sig`) e trava todo plano até uma nova aprovação. A correção fica cobrada:
o gate de plano soma as abertas num aviso que não barra. Ela só sai quando o corpo for corrigido,
reapresentado e reaprovado — aí `approved:` e `approved-sig:` são regravados e a linha é apagada.

### 6 · Semear o log de decisões
Cada decisão estruturante que apareceu na estratégia vira candidata a registro em
`.claude/docs/decisions/`. Escreva o **primeiro** (`0001-<slug>.md`) com o que o humano acabou de
dizer; os demais entram como `[PENDENTE]` na lista da estratégia.

### 7 · Fechar
**Se já existe um `CLAUDE.md` com os markers `project-doc:v2`:** atualize o índice — documento com
`status: ready` entra no roteamento; `draft` **não entra**, vira linha de cobrança no relatório.

**Se NÃO existe `CLAUDE.md`** (o cenário-bandeira desta skill — projeto virgem): **não crie o
índice.** Liste os documentos escritos no relatório e diga que o `/project-doc` vai criá-lo. Criar
markers `v2` à mão deixaria o projeto `in_pattern==false` na hora (o contrato exige também journal e
`doc-sig`, que só a mineração produz) — e todo hook do plugin passaria a acusar "fora do padrão".

Depois, ofereça o próximo passo:

- Projeto com código e sem doc minerada → "agora dá pra rodar `/project-doc` e minerar o resto."
- Projeto nascendo → "quando tiver código, `/project-doc` documenta o como."

## Output Protocol

```
**Passo 1/7:** Raiz → `/path` · docs de etapa existentes → {N dos que a tabela de etapas lista, contando `design.md` só se houver interface} · minerada → {sim | não}
**Passo 2/7:** Pistas → {N integrações · M versões travadas · K commits}
**Passo 3/7:** Entrevista → {doc}: {respondido | PENDENTE} … (uma linha por documento)
**Passo 4/7:** Escrito → {lista de arquivos com status draft|ready}
**Passo 5/7:** De acordo → {etapa}: {aprovada em YYYY-MM-DD | ABERTA, {N} reapresentações} … (uma linha por etapa)
             Esquema → `blueprint.md`: {aprovado em YYYY-MM-DD | ABERTO} · diagrama → {caminho em `.claude/archify/` | `archify` ausente, DEGRADADO} · revisão 5b → {rodada | pendente}
             Sem dono → {N} funcionalidades sem origem · {M} jornadas sem funcionalidade · {K} passos do desenho sem funcionalidade (saída de `rastreio_etapas.py`)
**Passo 6/7:** Decisões → `decisions/0001-{slug}.md` + {N} candidatas pendentes
**Passo 7/7:** Índice → {N docs promovidos} · Pendências → {lista de [PENDENTE] por doc} · Correções pendentes → {N, com o doc de cada uma}
```

Ao final, sempre: **o que ficou pendente, que etapa segue aberta, e o que destrava quando fechar.**

## Convivência com o `/project-doc`

- **O FULL nunca reescreve estes arquivos.** `authored-by: human` é a trava. Ele lê, cita, e cobra —
  não regenera, não sobrescreve, e não os inclui no fan-out por concern.
- **A única escrita automática permitida** ao FULL é atualizar `reviewed:` e promover `draft → ready`
  quando o último `[PENDENTE]` sai. **`approved:` está fora do alcance dele** — só o dono aprova, e
  `ready → approved` sem a fala dele é registro falso.
- **O Tier 5 do FULL chama `/start-doc gaps`** para saber o que perguntar. Uma fonte de perguntas,
  dois pontos de entrada — o banco vive em `references/authorial-kit.md` e não é duplicado.
- **Ordem num projeto virgem:** `/start-doc` (entrevista) → `/project-doc` (mineração). Nunca o
  inverso: minerar primeiro produz um "como" sem "por quê", e o humano perde a chance de enquadrar.

## Rules

- **NUNCA preencha conteúdo autoral por inferência.** É a regra que justifica a skill existir.
- **Uma pergunta por vez.** Despejar as cinco de uma vez derruba a qualidade da resposta.
- **Nenhuma pergunta sem pista visível** — mostre o que minerou junto. O humano não adivinha o seu
  contexto, e pergunta sem apoio custa uma rodada de re-pergunta.
- **`[PENDENTE]` é resultado legítimo**, não fracasso. Documento honesto e incompleto vale mais que
  documento completo e inventado.
- **Resposta do humano é literal.** Não reescreva o julgamento dele.
- **Nunca apague resposta anterior.** `review` propõe atualização e pede aval; decisão substituída
  muda de status e aponta para a sucessora, nunca some.
- **Documento `draft` não entra no índice** do `CLAUDE.md` — evita cinco linhas mortas no arquivo que
  carrega em toda sessão. Entra quando vira `ready`.
- **Nenhuma etapa fecha sem aprovação explícita gravada no documento.** `status: approved` +
  `approved:` no frontmatter, e nunca por inferência: sem uma frase do dono que você consiga apontar,
  a etapa está aberta.
- **Reapresente quantas vezes ele quiser.** Não existe rodada final decidida por você.
- **A sabatina não é juíza.** `/grill-me` e `/grill-with-docs` são o caminho até o acordo, não o
  veredito sobre ele — nem sobre a constituição do projeto, que é justamente o que elas ajudam a
  escrever.
- **Não invente estrutura nova** — os documentos das seis etapas, os moldes e o frontmatter estão em
  `references/authorial-kit.md`. Se precisar de mais um, é mudança de contrato, não improviso.
- **A etapa 6 não abre sem `blueprint.md` aprovado.** Sem o desenho acordado, a lista de
  funcionalidades sai de um entendimento em que ninguém bateu o martelo — e o erro só aparece
  depois da curadoria inteira.
- **Funcionalidade sem origem não entra.** Todo item de `features.md` aponta a jornada, a meta ou a
  peça aprovada que o pediu — ou a fala do dono, registrada como tal. Lista derivada de nada é a
  mesma ficção que a regra dura proíbe.
- **`design.md` nunca escrito à mão.** A entrevista é sua; a escrita e a validação são da skill
  `design-md` — não duplique a spec do formato aqui.
