---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me". With the argument com-docs, the same grilling also confronts the plan against the project's domain model (CONTEXT.md, ADRs) and updates it inline.
---

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled — the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Each question should be formatted like so:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Each round the user answers reshapes the tree — settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent to find it — don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report — ask the rest of the frontier now. The _decisions_ are the user's — put each to them and wait.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.

---

## Adição local — por onde a pergunta chega

*(Esta seção é do marketplace, não do autor original. O texto acima está verbatim.)*

A rodada acima diz **o que** perguntar. Quem escolhe **por onde** é o usuário, e a régua dos dois
canais (página de decisão em múltipla escolha como padrão, ferramenta nativa pergunta a pergunta
como alternativa) está em **`regua-de-pergunta.md`**, ao lado deste arquivo — leia antes de abrir a
rodada. A rodada aqui é a **fronteira**, e a recomendação que vira sugestão marcada na página é o
`➡️` de cada pergunta.

A régua é contrato de todas as skills que perguntam ao dono: a fonte é `_shared/regua-de-pergunta.md`
e a cópia local é derivada — não editar à mão; `scripts/sync-shared.sh` a regrava.

---

## Adição local — o modo com documento, que entra por argumento

*(Esta seção é do marketplace, não do autor original. O texto acima está verbatim.)*

São duas jornadas, e o argumento da invocação decide qual corre:

- **Sem argumento (`/grill-me`) — a jornada padrão.** A rodada de fronteira acima é tudo: sabatine o
  plano por ele mesmo, **não procure `CONTEXT.md` nem ADR** e não abra nenhum dos dois.
- **Com `/grill-me com-docs` — a jornada com documento.** A mesma rodada de fronteira corre, e por
  cima dela vale o bloco abaixo: o plano é confrontado contra o modelo de domínio já escrito.

### O que muda no modo `com-docs`

Na exploração do código, procure também a documentação de domínio. A forma usual é um `CONTEXT.md`
na raiz e um `docs/adr/` com as decisões numeradas. Se existir um `CONTEXT-MAP.md` na raiz, o repo
tem vários contextos e o mapa diz onde cada um mora (um `CONTEXT.md` e um `docs/adr/` por contexto,
mais o `docs/adr/` da raiz para as decisões do sistema inteiro). Crie arquivo **preguiçosamente** —
só quando houver o que escrever: o primeiro termo resolvido cria o `CONTEXT.md`, o primeiro ADR
necessário cria o `docs/adr/`.

Durante a sessão:

- **Confronte contra o glossário.** Quando o usuário usa um termo que conflita com a linguagem já
  registrada em `CONTEXT.md`, aponte na hora: "seu glossário define 'cancelamento' como X, mas você
  parece querer dizer Y — qual é?"
- **Afie linguagem frouxa.** Termo vago ou sobrecarregado ganha um termo canônico proposto: "você
  disse 'conta' — é o Cliente ou o Usuário? São coisas diferentes."
- **Discuta cenários concretos.** Relação de domínio se testa com caso específico, inventado para
  forçar precisão na fronteira entre os conceitos.
- **Cruze com o código.** Quando o usuário afirma como algo funciona, confira se o código concorda —
  e traga a contradição à tona quando não concordar.
- **Grave o termo resolvido na hora.** Resolveu um termo, atualize o `CONTEXT.md` ali mesmo, sem
  acumular lote, no formato de **`CONTEXT-FORMAT.md`** (ao lado deste arquivo). Não acople o
  `CONTEXT.md` a detalhe de implementação: só entram termos que significam algo para o especialista
  de domínio.
- **Ofereça ADR com parcimônia.** Só quando as três valem: **Difícil de reverter**, **surpreendente
  sem contexto** e resultado de um **trade-off real**. Faltando uma, não há ADR. O formato está em
  **`ADR-FORMAT.md`**, ao lado deste arquivo.

---

## Adição local — quando o chamador é o `/start-doc`

*(Esta seção é do marketplace, não do autor original. O texto acima está verbatim.)*

O `/start-doc` conduz a concepção em **cinco etapas de acordo** — autoral, arquitetura, interface,
jornadas, funcionalidades — e cada uma fecha com uma sabatina sua. Você é **como se chega ao acordo**, e é só isso:

- **Você não é juiz.** Não aprove, não reprove, não declare que o documento está bom o bastante.
  Sabatinar a constituição do projeto não é julgá-la — é o caminho de escrevê-la.
- **Quem aprova é o dono**, e a aprovação vive no frontmatter do documento
  (`status: approved` + `approved:`), nunca numa conclusão sua.
- **Objeção não resolvida volta pro documento**, e o documento é reapresentado. O loop fecha quando o
  dono diz que está satisfeito — não quando as perguntas acabam.
- **No modo `com-docs`, a atualização inline continua valendo**, mas o alvo aqui são os documentos da
  etapa em `.claude/docs/` — não abra um `CONTEXT.md` paralelo para guardar o que pertence a eles.
