---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me".
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

A rodada acima diz **o que** perguntar. Quem escolhe **por onde** é o usuário, e são dois canais:

- **Padrão — a rodada inteira numa página, em múltipla escolha.** A rodada da fronteira vira uma
  página de decisão: cada pergunta é um item, com as opções em rádio e **um campo livre embaixo**
  para o que não cabe nas opções. A recomendação (`➡️`) entra marcada como sugestão, nunca como
  resposta dada. É um canal só de ida e volta: o usuário responde a rodada inteira de uma vez,
  em vez de gastar um turno por pergunta.
  - **Como montar:** se a skill de apresentação visual estiver entre as suas skills disponíveis,
    invoque-a **pelo nome** e peça uma página de decisão com um item por pergunta. Não monte
    caminho de arquivo para dentro de outro plugin, e não rode programa de outro plugin: se a
    skill não estiver disponível na máquina, o canal padrão simplesmente não existe ali — caia
    no canal alternativo e siga.
  - **Como colher:** a resposta volta pelo estado que o daemon dessa página grava em disco, em
    `~/.claude/visual-state/latest.json`. Leia de lá; não peça ao usuário para copiar e colar.
  - **Pergunta sem apoio não vale.** Toda opção mostra o conteúdo concreto de que ela fala — o
    trecho literal, o número com procedência. O usuário não adivinha o seu contexto.

- **Alternativa — uma por vez, na ferramenta nativa de pergunta.** Mesma fronteira, mesma ordem,
  só que servida pergunta a pergunta no próprio CLI.

**Quem escolhe é o usuário.** Na primeira rodada, ofereça os dois e use o que ele pedir; ele pode
trocar de canal a qualquer momento, e a troca vale da rodada seguinte em diante. Sem escolha dita,
use o padrão.

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
