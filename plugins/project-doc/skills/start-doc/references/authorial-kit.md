# Authorial Kit — os 5 documentos que nenhuma mineração produz

> Banco de perguntas + moldes de saída dos documentos **autorais**. Fonte única, dois consumidores:
> a skill **`/start-doc`** (que os cria e evolui por entrevista) e o **Tier 5 do `/project-doc`**
> (que cobra o que ficou em branco durante a mineração). Se um mudar, é aqui.
>
> Derivado do kit canônico de documentação de arquitetura (Grupo A + glossário), que por sua vez
> mapeia o **arc42**. Os documentos 1-4 e o glossário são consenso de mercado; a decisão de
> **perguntar em vez de esqueletar** é nossa.

## A regra que manda em todas as outras

**A skill pergunta. A skill não responde.**

Metas, restrições, fronteiras e vocabulário só existem na cabeça do humano. Preencher no lugar dele
produz *ficção com aparência de autoridade* — pior que arquivo ausente, porque ninguém desconfia de
um documento que parece completo. Se a resposta não veio, o campo fica `[PENDENTE]` e o relatório
avisa. Nunca "deduza" uma meta de qualidade a partir do código.

**Onde a mineração ENTRA:** ela levanta **pistas** para a pergunta ficar concreta ("vi versões
travadas no lockfile — isso é restrição dura ou só não foi atualizado?"). Pista alimenta a pergunta;
nunca vira a resposta.

## Contrato de saída (vale para os 5)

Frontmatter obrigatório:

```yaml
---
generated: {YYYY-MM-DD}          # quando o arquivo nasceu
reviewed: {YYYY-MM-DD}           # última vez que o humano confirmou/atualizou
project: {nome}
authored-by: human               # TRAVA — o motor de mineração NUNCA reescreve este arquivo
status: draft | ready            # ready = sem [PENDENTE] no corpo
scope: []                        # vazio de propósito: não é derivado de arquivo
---
```

- **`authored-by: human` é a trava.** O FULL do `/project-doc` lê estes arquivos e pode **citá-los**,
  mas não os regenera, não os sobrescreve e não os inclui no fan-out por concern. A única escrita
  automática permitida é o `reviewed:` e a promoção `draft → ready` quando o último `[PENDENTE]` sai.
- **`[PENDENTE]`** é o marcador de lacuna. Enquanto existir um, `status: draft` e o documento **não
  entra no índice** do CLAUDE.md — vira uma linha de cobrança no relatório. Some o último → entra.
- **Resposta do humano vai literal.** Não "melhore" a redação dele. Pode organizar em bullets e
  corrigir digitação; não pode trocar o julgamento por outro mais bonito.

## Como conduzir a entrevista

- **Uma pergunta por vez.** Nunca despeje as 5 de uma vez — a qualidade da resposta despenca.
- **Sempre com pista visível.** Traga o que você minerou junto da pergunta (lockfile, compose,
  git log). Pergunta sem insumo obriga o humano a adivinhar o seu contexto.
- **Aceite "não sei" e "depois".** Vira `[PENDENTE]` com a data. Insistir queima a sessão.
- **Ordem importa:** metas → restrições → contexto → estratégia → glossário. As metas são o critério
  que as outras consomem; se você inverter, a estratégia vira preferência pessoal.
- **Reaproveite o que já foi dito.** Se a resposta já apareceu nesta sessão, no `CLAUDE.md`, num
  handoff ou no journal, **não pergunte** — mostre o que achou e peça só a confirmação.

---

## 1 · `quality-goals.md` — Metas de qualidade

- **Pergunta que responde:** o que este sistema prioriza, em ordem, quando não dá para ter tudo?
- **Conteúdo mínimo:** 3 a 5 atributos de qualidade **ordenados**, cada um com uma frase dizendo o
  que significa **neste** sistema. Mais um exemplo concreto de trade-off já decidido segundo a ordem.
- **Por que é o primeiro:** é o critério objetivo que resolve toda discussão posterior. Sem ele, cada
  decisão recomeça do zero e vira preferência pessoal.
- **Critério de pronto:** dado um trade-off real do sistema, duas pessoas lendo o documento chegam à
  mesma conclusão.

**Pistas a minerar antes de perguntar:** presença de testes e cobertura (sinal de integridade),
réplicas/healthcheck no compose (disponibilidade), cache/CDN (velocidade), limites de recurso (custo).

**Roteiro:**
1. "Se você tivesse que sacrificar UMA destas para salvar as outras, qual cai primeiro: integridade
   do dado, o sistema estar no ar, velocidade de entrega de features, ou custo de infraestrutura?"
2. "E entre as que sobraram, qual é a próxima a cair?" (repita até ordenar 3-5)
3. Para cada uma: "o que **integridade do dado** significa aqui na prática — o que não pode acontecer?"
4. "Me dá um caso real em que você já decidiu assim, e o que foi sacrificado."

**Molde:**

```markdown
{frontmatter}

# Metas de qualidade

> Ordem de prioridade deste sistema quando não dá para ter tudo. É o critério que resolve
> as decisões dos outros documentos — quando houver conflito, ganha quem está mais acima.

## A ordem

1. **{atributo}** — {o que significa neste sistema, 1 frase}
2. **{atributo}** — {…}
3. **{atributo}** — {…}

## Trade-off já decidido por esta ordem

{o caso real: a situação, o que foi escolhido, o que foi sacrificado, e por quê}
```

---

## 2 · `constraints.md` — Restrições

- **Pergunta que responde:** o que não é negociável, e por quê?
- **Conteúdo mínimo:** restrições organizacionais (quantas pessoas mantêm? existe plantão?),
  técnicas (stack imposta, versões travadas), econômicas (orçamento de infra) e legais. Para cada
  uma: é **dura** (não muda) ou **datada** (revisar quando?).
- **Critério de pronto:** um recém-chegado entende por que soluções óbvias foram descartadas.

**Pistas a minerar antes de perguntar:** versões pinadas no lockfile/`requirements.txt`, `engines`
no `package.json`, limites de CPU/memória no compose, runtime antigo no Dockerfile, região de deploy.

**Roteiro:**
1. "Quantas pessoas mantêm isso hoje, e tem alguém de plantão?"
2. "Achei {versão pinada / limite de recurso} — isso é restrição de verdade ou só não foi atualizado?"
3. "Tem alguma tecnologia que você é obrigado a usar (ou proibido de usar), e por quê?"
4. "Tem teto de custo de infra? Tem exigência legal de onde o dado pode morar?"
5. Para cada restrição: "isso muda algum dia, ou é pra sempre? Se muda, quando revisar?"

**Molde:**

```markdown
{frontmatter}

# Restrições

> O que não é negociável neste sistema. Serve para o leitor entender por que soluções
> óbvias foram descartadas — sem isso, todo recém-chegado propõe a mesma coisa de novo.

## Organizacionais
- **{restrição}** — {por quê} · **{dura | datada, revisar em YYYY-MM}**

## Técnicas
- **{restrição}** — {por quê} · **{dura | datada}**

## Econômicas
- **{restrição}** — {por quê} · **{dura | datada}**

## Legais / regulatórias
- **{restrição}** — {por quê} · **{dura | datada}**

## Soluções descartadas por causa das restrições acima
- **{a solução óbvia}** — descartada por **{qual restrição}**
```

---

## 3 · `context.md` — Contexto e escopo

- **Pergunta que responde:** onde termina o nosso sistema e começa o mundo?
- **Conteúdo mínimo:** os atores humanos e os sistemas externos; o que entra e o que sai em cada
  fronteira; e o que explicitamente **não** é nosso. Mais um diagrama de contexto.
- **Critério de pronto:** toda dependência externa que, caindo, degrada o sistema está listada.

**Este é o mais minerável do grupo** — integrações externas aparecem em variáveis de ambiente,
clientes HTTP, webhooks e SDKs. **Minere primeiro, apresente a lista, peça curadoria.** Perguntar do
zero aqui é desperdício.

**Roteiro:**
1. Apresente a lista minerada: "achei estas integrações externas: {lista com a evidência de cada}.
   Está faltando alguma que não aparece em arquivo?"
2. "Quem usa este sistema? Tem mais de um tipo de usuário com necessidade diferente?"
3. Para cada externo: "se ele cair agora, o que para de funcionar?"
4. "Tem alguma coisa que as pessoas ACHAM que é nossa e não é?"

**Molde:**

```markdown
{frontmatter}

# Contexto e escopo

> Onde este sistema termina e o mundo começa.

## Atores
- **{quem}** — {o que faz aqui, o que precisa}

## Sistemas externos
- **{nome}** — entra: {o quê} · sai: {o quê} · protocolo: {como}
  - **Se cair:** {o que para de funcionar}
  - **Evidência:** {arquivo onde a integração aparece}

## Fora do escopo — explicitamente NÃO é nosso
- **{o quê}** — {de quem é, ou por que ninguém faz}

## Diagrama de contexto

```
{o desenho: nosso sistema no centro, os atores e externos ao redor, setas rotuladas}
```
```

---

## 4 · `solution-strategy.md` — Estratégia

- **Pergunta que responde:** quais são as poucas decisões que explicam o formato de tudo?
- **Conteúdo mínimo:** **uma página**. As decisões estruturantes — um repositório ou vários; monolito
  modular ou serviços; como se autentica; onde o estado mora — e a ligação de cada uma com as metas
  do documento 1.
- **Critério de pronto:** cada decisão listada aponta para o registro (ADR) que a detalha.

**Pistas a minerar antes de perguntar:** layout do repositório, serviços no compose, biblioteca de
auth, onde está o banco. A mineração dá o **o quê**; a entrevista dá o **por quê**.

**Roteiro:**
1. "Vi que {o sistema é um monorepo com N módulos / são serviços separados}. Foi escolha ou foi
   acontecendo?"
2. "Se foi escolha: o que te fez decidir assim, e o que você descartou?"
3. "Qual dessas decisões, se fosse revertida hoje, quebraria mais coisa?"
4. Para cada uma: "ela serve qual das suas metas de qualidade?" (amarra no documento 1)
5. "Alguma dessas você já sabe que foi errada e vai ter que trocar?" (vira risco, não estratégia)

**Molde:**

```markdown
{frontmatter}

# Estratégia da solução

> As poucas decisões que explicam o formato de tudo. Uma página — se passar disso,
> tem detalhe aqui que pertence a um registro de decisão.

## As decisões estruturantes

### {decisão, ex.: "um repositório só, módulos dentro"}
- **Por quê:** {o raciocínio}
- **Descartamos:** {a alternativa e o motivo}
- **Serve à meta:** {qual atributo do quality-goals.md}
- **Detalhe em:** {link para o ADR, ou `[PENDENTE: registrar ADR]`}
```

---

## 5 · `glossary.md` — Glossário

- **Pergunta que responde:** o que significa esse termo que só nós usamos?
- **Conteúdo mínimo:** termos de domínio e termos internos inventados pela equipe. **Uma linha cada.**
- **Por que importa:** vocabulário interno não documentado é a principal fonte de mal-entendido entre
  humano e agente — o agente adivinha e adivinha errado.
- **Critério de pronto:** todo termo inventado que aparece nos outros documentos está definido aqui.

**Este é semi-minerável.** Rode a detecção antes: identificadores recorrentes no código que **não**
são da linguagem nem das bibliotecas, nomes de tabela/modelo, e termos que aparecem nos outros docs
sem definição. Apresente a lista candidata; o humano define ou descarta.

**Roteiro:**
1. "Achei estes termos que parecem ser vocabulário de vocês: {lista}. Quais são de verdade?"
2. Para cada confirmado: "me define em uma linha, como você explicaria pra alguém no primeiro dia."
3. "Tem algum termo que vocês usam falando e que nunca virou código?" (esses são os piores — o
   agente nunca os encontra sozinho)
4. "Tem palavra que significa aqui uma coisa diferente do resto do mercado?"

**Molde:**

```markdown
{frontmatter}

# Glossário

> Termos de domínio e vocabulário interno. Uma linha cada. Se um termo aparece nos
> outros documentos e não está aqui, o glossário está incompleto.

## Domínio
- **{termo}** — {definição em uma linha}

## Interno (inventado pela equipe)
- **{termo}** — {definição} · {onde aparece no código, se aparecer}

## Falsos amigos — significam aqui algo diferente do usual
- **{termo}** — aqui: {o que é} · no mercado: {o que costuma ser}
```

---

## 6 · `design.md` — Design system (SÓ projeto com interface)

> **Condicional — os outros 5 são universais, este não.** Só entra na entrevista e na contagem de
> lacunas quando o projeto **tem interface** (frontend web ou mobile). Backend puro, CLI e biblioteca
> não têm tela — cobrar design deles é cobrança que não cabe, e cobrança que não cabe ensina a
> ignorar cobrança. A detecção é automática (ver `hooks/lib-has-frontend.sh`); não pergunte "isso tem
> interface?" — verifique antes.

- **Pergunta que responde:** qual é a personalidade visual deste produto, e quais são os tokens
  normativos (cor, tipografia, espaçamento) que a expressam?
- **Conteúdo mínimo:** a cor primária, a família tipográfica do corpo, e 1-2 frases de personalidade
  de marca — o mínimo que o formato `DESIGN.md` exige (`primary` em `colors`, ao menos `body-md` em
  `typography`).
- **Por que é diferente dos outros 5:** não é prosa livre — é o formato **`DESIGN.md`** (padrão aberto
  do Google: frontmatter YAML com tokens + corpo markdown com o racional), com **linter próprio**.
  É o único autoral com validação determinística.
- **Critério de pronto:** o CLI oficial roda limpo (`errors: 0`) sobre o arquivo escrito.

**Este documento NÃO é escrito por esta skill diretamente.** A spec completa do formato, o CLI de
validação/export e o fallback sem `npx` já vivem na skill **`design-md`** — não duplique aqui. O papel
do `/start-doc` é só a **entrevista** (a mesma disciplina dos outros 5: uma pergunta por vez, resposta
literal, `[PENDENTE]` é válido); depois de colher as respostas, **invoque a skill `design-md`** para
escrever `.claude/docs/design.md` no formato correto e validar.

**Roteiro:**
1. "Se este produto fosse uma pessoa, que 2-3 adjetivos descreveriam a personalidade dele?"
2. "Tem uma cor primária já decidida (hex, ou 'a cor da marca')? Se não tiver, qual sensação ela devia
   passar (sério, lúdico, premium, urgente)?"
3. "Qual família tipográfica o corpo do texto usa (ou deveria usar)?"
4. "Tem algo que NUNCA pode acontecer visualmente neste produto — um 'don't' que já causou problema?"

**Molde:** delegado à skill `design-md` (absorvida neste plugin — F3 do plano
`design-como-doc-autoral`) — ela escreve `.claude/docs/design.md` seguindo
`${CLAUDE_PLUGIN_ROOT}/skills/design-md/references/spec.md` e valida com o CLI oficial:

```bash
npx --yes @google/design.md@0.3.0 lint .claude/docs/design.md --format json
```

**Sem `npx`/`node` disponível:** a skill `design-md` já degrada pra checagem manual pela spec
vendorada — **diga isso em voz alta** no relatório (F2.4): "validado em modo reserva, sem o linter
oficial", nunca finja que rodou o CLI.

---

## Semente do log de decisões

Ao final da entrevista de **estratégia**, cada decisão estruturante vira candidata a registro em
`.claude/docs/decisions/`. Escreva o **primeiro** (`0001-*.md`) com o que o humano acabou de dizer —
os demais viram `[PENDENTE]` na lista. Formato em `references/adr.md` do `/project-doc`.

Decisão substituída **não se apaga**: muda de status e aponta para a que a substituiu.
