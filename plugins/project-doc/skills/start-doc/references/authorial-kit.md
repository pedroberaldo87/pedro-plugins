# Authorial Kit — os documentos que nenhuma mineração produz

> Banco de perguntas + moldes de saída dos documentos **autorais**. Fonte única, dois consumidores:
> a skill **`/start-doc`** (que os cria e evolui por entrevista) e o **Tier 5 do `/project-doc`**
> (que cobra o que ficou em branco durante a mineração). Se um mudar, é aqui.
>
> Derivado do kit canônico de documentação de arquitetura (Grupo A + glossário), que por sua vez
> mapeia o **arc42**. Os documentos 1-4 e o glossário são consenso de mercado; a decisão de
> **perguntar em vez de esqueletar** é nossa.

## As cinco etapas de acordo

A concepção não é uma entrevista só — são **cinco acordos**, nesta ordem, e cada um tem documento
próprio e aprovação própria. Etapa não aprovada não deixa a seguinte começar: arquitetura decidida
sem as metas fechadas é palpite, e jornada desenhada sem a interface acordada é ficção.

| # | Etapa | Documento | Quando entra |
|---|---|---|---|
| 1 | **Acordo autoral** | `quality-goals.md` · `constraints.md` · `context.md` · `solution-strategy.md` · `glossary.md` | sempre — são os 5 universais |
| 2 | **Acordo de arquitetura** | `architecture-intent.md` | sempre |
| 3 | **Acordo de interface** | `design.md` (escrito pela skill `design-md`) | só projeto com interface |
| 4 | **Acordo de jornadas** | `journeys.md` | sempre |
| 5 | **Acordo de funcionalidades** | `features.md` | sempre — é a última, porque é **derivada do que já foi aprovado** nas quatro |

**Os nomes de arquivo acima são o contrato.** Todos moram em `.claude/docs/`. Quem cobra lacuna lê
daqui — inventar outro nome quebra a cobrança em silêncio.

**Quem cobra, e com que marca.** O gate de plano (`hooks/pretooluse-plan-gate.sh`) recusa
`EnterPlanMode`/`ExitPlanMode` enquanto `quality-goals.md`, `architecture-intent.md` e `journeys.md`
— mais `design.md`, em projeto com interface — não estiverem com `status: approved` e sem
`[PENDENTE]`. `status: ready` **não** libera: o gate cobra o de acordo, e `ready` é só "escrito". A
cobrança vale **sempre**, inclusive para o projeto novo que ainda não abriu etapa nenhuma — era ele
que passava batido enquanto ela dependia de já existir um dos arquivos. Quem não quer o regime
autoriza com `--sem-doc`, que é decisão do usuário, não do agente.

**A numeração das seções abaixo é catálogo de documento, não ordem de etapa.** Cada seção diz a que
etapa pertence; a ordem em que as etapas fecham é a da tabela acima.

- **`architecture-intent.md` não é `architecture.md`.** O segundo é minerado pelo `/project-doc` e
  descreve o que o código **é**; o primeiro é autoral e diz o que a arquitetura **deve ser**.
- **`journeys.md` não é `runtime.md`.** O segundo é minerado e narra o fluxo que o código executa; o
  primeiro é autoral e narra o percurso que a **pessoa** faz.

## A regra que manda em todas as outras

**A skill pergunta. A skill não responde.**

Metas, restrições, fronteiras e vocabulário só existem na cabeça do humano. Preencher no lugar dele
produz *ficção com aparência de autoridade* — pior que arquivo ausente, porque ninguém desconfia de
um documento que parece completo. Se a resposta não veio, o campo fica `[PENDENTE]` e o relatório
avisa. Nunca "deduza" uma meta de qualidade a partir do código.

**Onde a mineração ENTRA:** ela levanta **pistas** para a pergunta ficar concreta ("vi versões
travadas no lockfile — isso é restrição dura ou só não foi atualizado?"). Pista alimenta a pergunta;
nunca vira a resposta.

## Contrato de saída (vale para todos)

Frontmatter obrigatório:

```yaml
---
generated: {YYYY-MM-DD}          # quando o arquivo nasceu
reviewed: {YYYY-MM-DD}           # última vez que o humano confirmou/atualizou
project: {nome}
authored-by: human               # TRAVA — o motor de mineração NUNCA reescreve este arquivo
status: draft | ready | approved # draft = tem [PENDENTE] · ready = escrito · approved = o dono deu o de acordo
approved: {YYYY-MM-DD}           # a data do de acordo explícito. Ausente ou [PENDENTE] = etapa aberta
approved-sig: {marca do corpo}   # QUAL texto foi aprovado. Só `hooks/doc-aprovar.sh` escreve. Não bate com o corpo de hoje = etapa reaberta
correcao-pendente: {o que falta} # 0 ou mais linhas. Ajuste achado DEPOIS do de acordo — não reabre a etapa
scope: []                        # vazio de propósito: não é derivado de arquivo
---
```

- **`authored-by: human` é a trava.** O FULL do `/project-doc` lê estes arquivos e pode **citá-los**,
  mas não os regenera, não os sobrescreve e não os inclui no fan-out por concern. A única escrita
  automática permitida é o `reviewed:` e a promoção `draft → ready` quando o último `[PENDENTE]` sai.
- **`approved:` nenhuma máquina escreve sozinha.** Nem o FULL, nem esta skill por conta própria. Ela
  só grava a data quando o dono acabou de dizer, com todas as letras, que está satisfeito. Promover
  `ready → approved` sem essa fala é falsificar o registro.
- **`approved-sig:` diz QUAL texto foi aprovado**, e é a razão de a aprovação ser um comando
  (`hooks/doc-aprovar.sh`) e não três linhas digitadas: ele calcula a marca do **corpo** — o
  frontmatter fica de fora, senão gravar a marca mudaria a marca — e a grava junto do `approved:`.
  Quem cobra é o gate de plano, que recalcula: marca gravada diferente do corpo de hoje = alguém
  editou depois do de acordo, e a etapa **reabre**. Sem `approved-sig:` não há o que recalcular.
- **`[PENDENTE]`** é o marcador de lacuna. Enquanto existir um, `status: draft` e o documento **não
  entra no índice** do CLAUDE.md — vira uma linha de cobrança no relatório. Some o último → entra.
- **`correcao-pendente:` é o ajuste achado depois do de acordo**, e vive **no frontmatter, nunca no
  corpo**. Uma linha por correção. Ela **não reabre a etapa**: o de acordo continua valendo sobre o
  texto que o dono aprovou, e o gate de plano soma as correções abertas num aviso que não barra —
  cobrança visível em vez de planejamento congelado. Escrever a correção no corpo faria o oposto: o
  corpo é o que a marca do de acordo mede, e mexer nele reabre a etapa (`approved-sig`). A linha sai
  quando o corpo for corrigido, reapresentado e **reaprovado** — aí o par `approved:`/`approved-sig:`
  é regravado.
- **Resposta do humano vai literal.** Não "melhore" a redação dele. Pode organizar em bullets e
  corrigir digitação; não pode trocar o julgamento por outro mais bonito.

### O arquivo histórico — o canônico só guarda o que vale hoje

Todo documento autoral tem um irmão: **`<nome>.historico.md`, na mesma pasta** (`quality-goals.md`
→ `quality-goals.historico.md`). Ele **nasce na primeira reescrita**, não antes — arquivo vazio é
ruído no `ls`.

**Item reescrito não é apagado: é movido.** O canônico fica só com o que vale hoje; o texto anterior
sai de lá e entra no histórico com os **três dados**, e nenhum é opcional:

- **data** — quando a reescrita aconteceu (`YYYY-MM-DD`)
- **contexto** — o que estava acontecendo que trouxe o assunto de volta
- **decisão** — o que, decidido, mudou o item

Sem os três a entrada não é escrita. Histórico sem o porquê é entulho, e entulho ninguém lê — a
versão anterior sozinha já está no git; o que o git não guarda é a razão.

**Quem escreve é o programa, não a mão:** `lib/historico.py` (`reescrever`, `listar`). Ele recusa,
sem tocar em arquivo nenhum, o item que não está no documento e o item que aparece mais de uma vez
(qual dos dois?). Mexer no histórico à mão desalinha o formato que o `listar` lê de volta.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/historico.py" reescrever .claude/docs/quality-goals.md \
  --antigo "1. **velocidade** — …" --novo "1. **integridade do dado** — …" \
  --contexto "a entrevista de metas foi refeita depois do incidente de junho" \
  --decisao  "perder dado passou a doer mais que atrasar entrega"
```

- **Entrada de histórico não se apaga nem se corrige** — corrigir é escrever a próxima. Igual a
  decisão substituída em `decisions/`: muda de status, não some.
- **O histórico é autoral também** (`authored-by: human` no frontmatter dele): a mineração pode
  citá-lo, nunca reescrevê-lo.
- **Ele não entra no índice do CLAUDE.md.** Quem lê o documento acha o irmão na mesma listagem;
  quem lê o índice quer o que vale hoje.

**Exceção de forma no `design.md`:** o frontmatter dele é o do formato `DESIGN.md` (tokens), não este.
O par `status:` / `approved:` entra **por cima** dos tokens, e só ele — confirmado rodando o linter
oficial com os dois campos presentes: `errors: 0, warnings: 0`.

## Como uma etapa fecha — apresentar, sabatinar, ouvir o de acordo

Escrever o documento **não fecha** a etapa. O ciclo é este, e ele repete:

1. **Apresentar o documento inteiro** ao dono — o texto real, não um resumo dele. Ele não adivinha o
   que você escreveu.
2. **Sabatinar** com `/grill-me` (ou `/grill-with-docs`, quando já existe `CONTEXT.md` ou ADR para
   confrontar). É aqui que a coisa vira acordo de verdade.
3. **Corrigir e REAPRESENTAR.** Toda objeção volta pro documento e o documento volta pra tela. Não
   há teto de rodadas: o que fecha o loop é a fala do dono, não o cansaço.
4. **Conferir o que ficou sem dono** — `lib/rastreio_etapas.py`, rodado no fechamento e só nele.
5. **Gravar o de acordo** — `status: approved` + `approved: {data de hoje}` — só depois de ele dizer
   que está satisfeito.

**A conferência de rastreio acontece no fechamento, nunca no meio da entrevista.** Duas pontas
soltam sozinhas e nenhuma dói na hora: **funcionalidade sem origem** (item de `features.md` que não
aponta a jornada, a meta ou a peça que o pediu) e **jornada sem funcionalidade** (jornada de
`journeys.md` que nada realiza). Quem as conta é `lib/rastreio_etapas.py`, e ele **só conta — não
escreve em documento nenhum**: conferência que edita texto aprovado reabriria a etapa pela marca
(`approved-sig`), e é justamente o que o `correcao-pendente:` existe para evitar. A saída dele é
cobrança visível no relatório, não um gate — o de acordo do dono continua sendo dele.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/rastreio_etapas.py" .   # → JSON com as duas listas
```

**A sabatina não é juíza.** Ela não aprova, não reprova e não decide se o documento está bom: ela é o
**caminho** até o acordo. Quem aprova é o dono, e a aprovação dele mora no frontmatter do próprio
documento — não numa conclusão da sabatina, não numa nota da skill, não na sua memória da conversa.

**Silêncio não é aprovação.** Nem "tá bom", nem "pode seguir" dito no meio de outra pergunta. Se você
não consegue apontar a frase, a etapa continua aberta.

## Como conduzir a entrevista

- **Uma pergunta por vez.** Nunca despeje as 5 de uma vez — a qualidade da resposta despenca.
- **Sempre com pista visível.** Traga o que você minerou junto da pergunta (lockfile, compose,
  git log). Pergunta sem insumo obriga o humano a adivinhar o seu contexto.
- **Aceite "não sei" e "depois".** Vira `[PENDENTE]` com a data. Insistir queima a sessão.
- **Ordem importa** — dentro da etapa 1: metas → restrições → contexto → estratégia → glossário. As
  metas são o critério que as outras consomem; se você inverter, a estratégia vira preferência
  pessoal.
- **Reaproveite o que já foi dito.** Se a resposta já apareceu nesta sessão, no `CLAUDE.md`, num
  handoff ou no journal, **não pergunte** — mostre o que achou e peça só a confirmação.

### As decisões estruturais caras — só as que o projeto acendeu

Há decisões que custam reescrita quando decididas tarde (quem escreve em cada pedaço do dado, como
o formato do dado muda com gente usando, o que fazer quando o modelo devolve lixo). Elas **não** são
um questionário fixo: perguntar as dez em todo projeto ensina o dono a responder no automático, e aí
as que eram dele vêm no mesmo automático.

Quem decide quais entram é o próprio projeto minerado:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/lib/decisoes_estruturais.py <raiz-do-projeto>
```

- **Três são incondicionais** — como isso sobe, como se volta atrás, como se descobre que quebrou.
- **As outras sete têm gatilho**: guarda dado → as duas de dado; tem mais de um cliente → isolamento;
  usa modelo → resposta não confiável e teto de custo; tem trabalho em fila → entrega; cobra →
  cobrança repetida. **Pergunta sem sinal não é feita** — projeto sem banco, sem inteligência
  artificial e sem multi-cliente recebe três, não dez.
- **Cada gatilho vem com a pista** (arquivo e trecho). Leve a pista junto da pergunta, como manda a
  regra acima — e lembre que ela alimenta a pergunta, nunca vira a resposta.
- A resposta entra em `solution-strategy.md`, em **As decisões estruturantes**; sem resposta, fica
  `[PENDENTE]` como qualquer outra.

### As quatro de segurança — essas são sempre feitas, e cada uma vem com o dado

O mesmo comando imprime, embaixo, um bloco `seguranca:` com **quatro perguntas que não têm gatilho**:
quem acessa o quê · que dado de pessoa fica guardado · quanto pode cair · o que fica exposto.
Segurança adiada não é pergunta economizada, é dívida — por isso aqui a regra do "sem sinal não
pergunta" **não vale**.

O que o projeto minerado decide não é *se* a pergunta entra, é **com que dado ela entra**:

- `o projeto confirma: <arquivo> (<trecho>)` — achou no código o que a resposta afirmaria.
- `o projeto contradiz: <o que foi procurado e não existe>` — a ausência é o dado. Ela é a mais útil
  das duas: é ela que transforma "claro que tem controle de acesso" em divergência **visível**, na
  hora, com o dono na frente.

**Leve o dado junto da pergunta, sempre — inclusive quando ele contradiz.** Se a resposta bater com o
dado, escreva as duas coisas. Se divergir, não corrija o dono nem o dado: registre a divergência
literal (ele conhece intenção que o código ainda não tem — ou o código conhece um vazamento que ele
não sabia). As respostas entram em `solution-strategy.md`, em **As decisões estruturantes**; a de
dado de pessoa entra **também** em `constraints.md`, em *Legais / regulatórias*.

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

## 6 · `design.md` — Design system · **etapa 3, acordo de interface** (SÓ projeto com interface)

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

**O de acordo desta etapa** vai no frontmatter do próprio `design.md`, com o mesmo par dos outros
(`status: approved` + `approved:`). Linter limpo **não é aprovação** — ele diz que o arquivo é
válido, não que o dono concordou com a personalidade que está lá dentro.

---

## 7 · `architecture-intent.md` — Arquitetura pretendida · **etapa 2**

- **Pergunta que responde:** que desenho a solução vai ter — quais peças, com que fronteiras entre
  elas?
- **Não confunda com a estratégia (documento 4):** a estratégia diz **quais decisões** mandam no
  formato; a arquitetura pretendida **desenha o resultado** — as peças, quem fala com quem, e onde o
  estado mora.
- **Não confunda com `architecture.md`:** aquele é minerado pelo `/project-doc` e descreve o que o
  código **é**. Este é autoral e diz o que a arquitetura **deve ser**. Coexistem; divergência entre
  os dois é achado, não erro de arquivo.
- **Conteúdo mínimo:** as peças com a responsabilidade de cada uma, as fronteiras (quem pode chamar
  quem), onde o estado mora, e o que foi deliberadamente deixado de fora.
- **Critério de pronto:** toda peça nova proposta depois cai numa fronteira já descrita — ou o
  documento muda antes do código.

**Pistas a minerar antes de perguntar:** layout de pastas, serviços no compose, imports que cruzam
módulo, onde o banco mora, e o grafo do `graphify` se o projeto tiver um.

**Roteiro:**
1. "Quais são as peças deste sistema, e do que cada uma é responsável?"
2. "Achei {estas pastas / estes serviços} — cada uma é uma peça, ou tem peça que não virou pasta?"
3. "Quem pode chamar quem? Tem chamada que você quer proibir de propósito?"
4. "Onde o estado mora, e quem tem permissão de escrever nele?"
5. "O que você decidiu NÃO construir, mesmo sendo tentador?"
6. Para cada peça: "ela serve qual das metas do `quality-goals.md`?"

**Molde:**

```markdown
{frontmatter}

# Arquitetura pretendida

> O desenho acordado antes do código. Quando o código divergir daqui, um dos dois
> está errado — e a conversa começa por qual.

## As peças
- **{peça}** — responsável por {o quê} · **serve à meta:** {atributo do quality-goals.md}

## As fronteiras — quem pode chamar quem
- **{peça A} → {peça B}** — {por quê, e por qual porta}
- **PROIBIDO: {peça C} → {peça D}** — {o que isso quebraria}

## Onde o estado mora
- **{depósito}** — {o que guarda} · **escreve:** {quem} · **lê:** {quem}

## Deixado de fora de propósito
- **{o que não vai existir}** — {por quê}

## Desenho

```
{as peças e as setas entre elas}
```
```

---

## 8 · `journeys.md` — Jornadas · **etapa 4**

- **Pergunta que responde:** o que uma pessoa vem fazer aqui, do começo ao fim?
- **Não confunda com `runtime.md`:** aquele é minerado e narra o fluxo que o **código** executa. Este
  é autoral e narra o percurso que a **pessoa** faz — inclusive as partes que nenhum código toca.
- **Por que é a última etapa:** jornada escrita antes da interface acordada vira desenho de tela.
  Escrita depois, ela vira cobrança — sobre a interface e sobre a arquitetura.
- **Conteúdo mínimo:** 3 a 5 jornadas, cada uma com ator, gatilho, percurso, o que a pessoa leva
  embora quando dá certo, e onde ela costuma travar.
- **Critério de pronto:** toda jornada tem um fim declarado e um caminho de erro. Jornada sem fim é
  lista de funcionalidade disfarçada.

**Pistas a minerar antes de perguntar:** rotas e endpoints, telas versionadas, comandos e flags do
CLI, entradas de menu, jobs agendados (jornada sem humano também é jornada).

**Roteiro:**
1. "Quem abre isso, e o que aconteceu na vida dessa pessoa pra ela precisar abrir?"
2. "Me conta do começo ao fim o que ela faz até conseguir o que veio buscar."
3. "Onde ela trava, desiste ou faz errado?"
4. "O que ela leva embora quando dá certo — como ela sabe que terminou?"
5. "Tem jornada de alguém que não é o usuário principal?" (operação, suporte, um agente)

**Molde:**

```markdown
{frontmatter}

# Jornadas

> O percurso da pessoa, não o do código. Se um passo aqui não tem onde acontecer
> na interface nem quem o execute na arquitetura, achamos um buraco.

## {nome da jornada}
- **Ator:** {quem}
- **Gatilho:** {o que aconteceu pra ela começar}
- **Percurso:** {passo → passo → passo}
- **Fim feliz:** {o que ela leva embora, e como sabe que terminou}
- **Onde quebra:** {o ponto de desistência, e o que acontece então}
- **Toca as peças:** {peças do architecture-intent.md que essa jornada exercita}
```

---

## 9 · `features.md` — Funcionalidades · **etapa 5**

- **Pergunta que responde:** o que este sistema faz, item a item?
- **De onde a lista sai:** ela é **derivada do que já foi aprovado** nas quatro etapas anteriores —
  cada jornada de `journeys.md` pede o que a faz acontecer, cada meta de `quality-goals.md` e cada
  peça de `architecture-intent.md` podem exigir uma funcionalidade que nenhuma jornada nomeia. Por
  isso ela é a **última** etapa: antes dos quatro acordos, lista de funcionalidade é palpite.
- **A skill propõe, o dono decide.** A derivação é sua; o veredito de cada item é dele. Item que
  você derivou e ele não confirmou **não é funcionalidade acordada** — é proposta na tela.
- **Não confunda com `journeys.md`:** a jornada é o percurso da pessoa; a funcionalidade é a
  capacidade que aquele percurso consome. Jornada sem fim declarado, aliás, já é lista de
  funcionalidade disfarçada (ver documento 8).
- **Conteúdo mínimo:** cada funcionalidade com o que faz em uma frase, a **origem** (qual jornada,
  meta ou peça aprovada a pediu) e a **passagem literal** do documento aprovado que a motivou.
- **Critério de pronto:** toda funcionalidade da lista aponta uma origem, e toda jornada aprovada
  tem ao menos uma funcionalidade que a realiza.

**Pistas a minerar antes de perguntar:** nenhuma no código — o insumo desta etapa são os **documentos
já aprovados**. Releia `journeys.md`, `quality-goals.md` e `architecture-intent.md` com o `approved:`
gravado; documento ainda aberto não serve de origem.

**Roteiro:**
1. Apresente a lista derivada inteira, cada item com a passagem que o motivou ao lado: "destas
   funcionalidades, quais eu entendi errado?"
2. "Tem funcionalidade que você quer e que não sai de nenhuma jornada aprovada?" (se sair daqui,
   a origem é a fala dele — registre assim, não invente uma jornada)
3. "Tem alguma nessa lista que você NÃO quer construir?" (vai para a seção do que ficou de fora)
4. "Alguma jornada aprovada ficou sem nada que a realize?" (buraco entre as etapas, não item novo)

**Molde:**

```markdown
{frontmatter}

# Funcionalidades

> O que este sistema faz, derivado das etapas já aprovadas. Nada entra aqui sem origem
> apontável — funcionalidade sem origem é ideia que entrou pela janela.

## As funcionalidades

### F-{n} · {nome, na língua de quem usa}
- **O que faz:** {uma frase}
- **Origem:** {jornada de `journeys.md` · meta de `quality-goals.md` · peça de `architecture-intent.md` · decisão do dono}
- **Passagem que a motivou:** "{o trecho literal do documento aprovado, ou da fala do dono}"

## Deixado de fora de propósito
- **{a funcionalidade}** — {por que não vai existir}
```

**O de acordo desta etapa** é o mesmo dos outros: `status: approved` + `approved:` no frontmatter do
próprio `features.md`, depois de apresentar a lista inteira, sabatinar e reapresentar. Lista derivada
não é lista acordada.

---

## Semente do log de decisões

Ao final da entrevista de **estratégia**, cada decisão estruturante vira candidata a registro em
`.claude/docs/decisions/`. Escreva o **primeiro** (`0001-*.md`) com o que o humano acabou de dizer —
os demais viram `[PENDENTE]` na lista. Formato em `references/adr.md` do `/project-doc`.

Decisão substituída **não se apaga**: muda de status e aponta para a que a substituiu.
