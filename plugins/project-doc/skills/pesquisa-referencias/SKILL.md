---
name: pesquisa-referencias
description: "Pesquisa de referências para a concepção — muitos agentes lendo projetos abertos e produtos pagos em paralelo para levantar repertório sobre um assunto que travou uma etapa do /start-doc. O custo é declarado ANTES de qualquer leitura (quantos agentes, quanto tempo, quantas fontes) e a pesquisa só começa com o aceite do dono. Roda com travas de parada duras (teto de agentes, de fontes, de tempo e parada por saturação) e entrega um dossiê de achados com a fonte de cada um. Nada do que ela acha entra em documento autoral sozinho — achado é insumo de pergunta, nunca resposta. Quinta skill do plugin project-doc, ao lado do /project-doc, /doc-touch, /start-doc e /design-md. Use quando o usuário diz \"/pesquisa-referencias\", \"pesquisa referências\", \"como os outros resolvem isso\", \"o que o mercado faz aqui\", \"me traz repertório\", ou quando uma etapa do /start-doc empaca porque falta repertório para responder — e aí OFEREÇA, nunca dispare sozinho."
---

# pesquisa-referencias — o repertório que a concepção não tem

## O que é

A entrevista do `/start-doc` para quando o dono não tem repertório para responder. Não é falta de
opinião: é falta de **material**. "Que peças este sistema tem?" é uma pergunta impossível para quem
nunca viu três sistemas parecidos por dentro.

Esta skill vai buscar esse material: **muitos agentes lendo em paralelo** projetos abertos e produtos
pagos sobre o assunto que travou, e devolvendo um dossiê de achados com a fonte de cada um.

Ela **não responde a pergunta da entrevista**. Ela dá ao dono o que ler antes de responder.

## A oferta — o custo antes do trabalho

Pesquisa larga custa tempo e custa contexto. Custo descoberto no fim não é custo aceito — então ele
é declarado inteiro **antes da primeira leitura**, neste formato:

```
🔎 Pesquisa de referências — {assunto}
• {N} agentes em paralelo, ~{T} minutos
• {F} fontes no teto — {A} projetos abertos, {P} produtos pagos
• Volta como dossiê de achados com a fonte de cada um, para você ler antes de responder
• Nada disso entra em documento nenhum sozinho

Toco?
```

Os dois números saem da conta, nunca de chute: **`{N}` é uma frente de pesquisa por eixo do assunto**
(um agente por eixo, respeitando o teto de agentes), e **`{T}` é `{F}` fontes ÷ `{N}` agentes × 2
minutos por fonte**, arredondado para cima. Se você não consegue enumerar os eixos, o assunto ainda
não está recortado o bastante para pesquisar — recorte antes de ofertar.

**Sem o aceite explícito, a pesquisa não começa.** Nenhum agente é disparado antes de uma frase do
dono que você consiga apontar. **Silêncio não é aceite**, e "pode ser" dito no meio de outra resposta
também não.

Recusa é resultado legítimo: a etapa continua aberta com `[PENDENTE]`, e isso é o estado honesto.

**Mudou o escopo no meio? A oferta é refeita e reaceita.** Achou-se um eixo novo, o teto de fontes
ficou pequeno, o assunto virou outro — nada disso se resolve gastando mais por conta própria. Para,
mostra o que já tem, e oferta de novo com os números novos.

## O que se lê

- **Projetos abertos** — repositórios públicos, a documentação deles, os ADRs, o `README`, a forma
  das pastas. É a fonte que dá para ler por dentro; é dela que sai o "como eles resolveram".
- **Produtos pagos** — concorrentes e ferramentas fechadas, lidos **só pelo que é público**
  (documentação, changelog, página de preço, ajuda ao cliente). Nada de credencial, de conta de
  teste, de burlar paywall e de conteúdo atrás de login. Produto fechado entra pelo que ele **diz de
  si**, e o dossiê registra isso.

Cada fonte entra com URL, data da leitura e o trecho que sustenta o achado.

## As travas de parada

Pesquisa larga sem trava não termina — ela só é interrompida. As travas são números, decididos na
oferta e escritos no dossiê:

- **teto de agentes** — no máximo **6** em paralelo, um por eixo do assunto. Mais que isso não
  aprofunda: repete.
- **teto de fontes por agente** — no máximo **8**. O agente lê as 8 melhores e para, não as que
  couberem.
- **teto de tempo** — o `{T}` da oferta. Estourou, para onde está e relata o que faltou.
- **parada por saturação** — três fontes seguidas sem achado novo encerram aquele eixo. Repertório
  satura rápido, e ler a quarta fonte que diz o mesmo é gasto sem retorno.

**Trava estourada PARA e relata** — nunca pede mais orçamento sozinha, nunca sobe o teto no meio.
O dossiê sai incompleto e diz onde parou; ampliar é uma oferta nova.

## A REGRA DURA — nada entra em documento aprovado sozinho

**Achado é insumo de pergunta. Achado nunca vira resposta.** O que a pesquisa traz volta para a
entrevista como pista visível — "três dos quatro projetos separam o worker do web; aqui é assim
também, ou você quer junto de propósito?" — e a resposta continua sendo do dono.

- **A pesquisa não escreve documento autoral.** Ela escreve o dossiê e para. Quem escreve
  `.claude/docs/*.md` é o `/start-doc`, com a fala do dono.
- **Documento com `status: approved` a pesquisa não toca**, nem para "complementar". Acordo fechado
  se reabre pela porta da frente — `/start-doc review`, nova apresentação, nova aprovação.
- **Todo achado carrega a fonte** — URL e trecho. Achado sem fonte é palpite com sotaque de pesquisa,
  e some do dossiê.
- **A pesquisa não aprova e não fecha etapa.** Ela não tem voto sobre o documento; quem aprova é o
  dono, no frontmatter, como sempre.
- **Convergência não é argumento de autoridade.** "Todo mundo faz assim" é um achado, não uma
  decisão — e o dossiê apresenta assim.

## Fluxo

### 1 · Recortar o assunto
Qual etapa travou, qual pergunta ficou sem resposta, e em que **eixos** ela se divide. Sem eixos não
há agentes — e sem agentes não há oferta com número.

### 2 · Ofertar e esperar
Emita o bloco da oferta com `{N}`, `{T}` e `{F}` preenchidos. Espere o aceite. Não adiante leitura
"só para calibrar" — leitura já é o custo que está sendo ofertado.

### 3 · Disparar as frentes
Um agente por eixo, cada um com o teto de fontes e a instrução de voltar com achado + fonte + trecho.
Nenhum agente escreve arquivo do projeto; todos devolvem texto.

### 4 · Consolidar o dossiê
Grave em `.claude/pesquisa/{slug}.md` — artefato de sessão, não documento do projeto. Um achado por
bullet, agrupado por eixo, cada um com a fonte. Contradição entre fontes fica **como contradição**,
não é resolvida por você.

### 5 · Devolver para a entrevista
Apresente o dossiê e volte a pergunta que travou, agora com as pistas à vista. A etapa fecha do jeito
de sempre — apresentação, sabatina, de acordo gravado no frontmatter.

## Output Protocol

```
**Passo 1/5:** Assunto → {assunto} · etapa travada → {doc} · eixos → {lista}
**Passo 2/5:** Oferta → {N} agentes · ~{T} min · {F} fontes → {aceita | recusada}
**Passo 3/5:** Frentes → {eixo}: {fontes lidas}/{teto} · {parada por saturação | teto | fim} …
**Passo 4/5:** Dossiê → `.claude/pesquisa/{slug}.md` · {N} achados · {M} contradições
**Passo 5/5:** Devolvido → {doc}: pergunta reaberta com {N} pistas · documento escrito → nenhum
```

Ao final, sempre: **o que ficou sem cobertura, que trava parou onde, e que pergunta volta para o dono.**

## Rules

- **Nunca comece sem aceite.** A oferta com número é o contrato; sem ela não há pesquisa.
- **Nunca suba um teto no meio.** Trava estourada vira relato e, se for o caso, oferta nova.
- **Nunca escreva documento autoral.** Nem `draft`, nem "só um rascunho para facilitar".
- **Nunca toque em documento aprovado.** Acordo fechado se reabre pelo `/start-doc review`.
- **Nunca apresente achado sem fonte.** URL, data e trecho, ou o achado não existe.
- **Nunca burle paywall nem login.** Produto pago entra pelo que é público, e só.
- **Nunca resolva contradição entre fontes.** Divergência é achado; escolher é do dono.
