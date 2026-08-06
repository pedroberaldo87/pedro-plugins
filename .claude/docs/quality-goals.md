---
generated: 2026-08-01
reviewed: 2026-08-01
project: pedro-plugins
authored-by: human
status: ready
scope: []
doc-sig: pedro-plugins/quality-goals@gen=3.8#d9d6f245
---

# Metas de qualidade

> Ordem de prioridade deste sistema quando não dá para ter tudo. É o critério que resolve
> as decisões dos outros documentos — quando houver conflito, ganha quem está mais acima.

Este marketplace não entrega dado nem uptime: entrega **artefatos que um humano lê para
decidir**. Relatório, plano, página de aprovação, resumo de fim de turno. Por isso a ordem
abaixo é sobre **fricção de leitura**, e ela manda em toda skill que produz texto ou HTML.

## A ordem

1. **Escaneabilidade** — quem lê pula o que não interessa. Percorre-se pelos títulos; o
   corpo só é lido por escolha.
2. **Drill-down opcional, em níveis** — nada é apagado, tudo é rebaixado.
3. **Completude** — nenhuma informação some para caber. Muda de nível, nunca de existência.
4. **Elegância / densidade visual** — cai primeiro. Feio e escaneável vence bonito e corrido.

## Os dois regimes

Nem todo documento tem o mesmo rigor. São dois, e a fronteira **não é declarada** — é o
caminho que o texto percorre:

- **Informação rápida** — tudo que sai do gerador de página (`plugins/visual/lib/visual_page.py`):
  relatório, plano, página de aprovação, diagnóstico. Volumoso por natureza, lido com pressa.
  **Prosa proibida.** Bullets, sempre.
- **Constituição** — contrato de skill (`SKILL.md`), doc de arquitetura (`.claude/docs/`),
  premissa. Escrito à mão, lido devagar, uma vez. Admite nuance e argumento. Continua
  enxuto e escaneável; não admite prolixidade.

**Por que não existe campo `regime` no spec:** a fronteira já é o pipeline. Constituição
nunca passa pelo gerador. Sem campo declarável, não há saída de emergência para declarar
o regime frouxo e escapar da régua.

## Regime "informação rápida" — os três níveis

- **Nível 0 · título** — sempre visível. Diz **que tipo de coisa aconteceu e qual foi a
  providência**. Uma linha.
- **Nível 1 · corpo** — nasce fechado. Abre com um clique. Em bullets.
- **Nível 2 · prova** — nasce fechado dentro do nível 1. A saída crua, o `arquivo:linha`,
  o comando e o resultado.

## A régua de estilo — quatro checagens, cobradas por programa

Vale para **todo campo de texto que o gerador emite**, não só para consequência e proposta:

- **≤ 140 caracteres por bullet.** É o teto que o plano já cobra hoje (`desc` ≤ 140, máximo
  real medido: 137). Número provado em produção vale mais que número novo.
- **Uma frase por bullet.** Ponto seguido de espaço dentro do bullet = parágrafo disfarçado.
- **Bullet não abre com conectivo de continuação** (`e`, `mas`, `que`, `porque`, `então`,
  `ou seja`, `além disso`). Pega a prosa fatiada, que passa no teto e continua prosa.
- **Máximo 6 bullets por bloco.** Acima disso é prosa picada, ou são dois itens.

**Fora da régua:** saída crua dentro do bloco de prova, e as linhas de árvore de plano
geradas pelo programa. Prova é literal por obrigação; linha de árvore não é redação.

### Os campos cobertos

```
título e corpo de item          title · body · summary · paragraphs
caixa de decisão                question · context · title · body · tradeoff
balão de aviso                  text
problema / consequência / proposta   problema · consequencia · proposta
texto solto e lista             text · items
legenda de artefato e gráfico   procedencia · alt · title
```

## Nada nasce aberto por ser curto

O nível 1 fecha **sem exceção de tamanho**. Prova curta, bloco de três linhas, item de
gravidade baixa: tudo fecha. A exceção "isso é pequeno, não atrapalha" reaparece toda vez
que alguém mede a tela e conta blocos abertos que ninguém pediu para ver.

- **A única válvula é abrir, nunca fechar.** `"aberto": true` num bloco de prova continua
  valendo, porque **revelar mais nunca esconde** — é seguro deixar na mão de quem escreve.
- **O simétrico não existe.** Não há campo que feche o que a regra manda mostrar. Fosse
  possível, seria o lugar de esconder.

**Página gerada não avisa que ficou velha.** A aba do navegador continua mostrando o
arquivo de quando foi aberta, e nada na tela denuncia isso — em 2026-08-02 um bloco
aparecia aberto numa aba de 8 horas antes, com o arquivo já corrigido no disco. Antes de
tratar o que se vê na tela como defeito, confira o HTML no disco.

## Anti-ocultação: por derivação, não por disciplina

Colapsar não pode virar esconder. Quem escreve o artefato é quem executou o trabalho — é
parte interessada. A garantia não pode ser a honestidade dele:

- **Regra única de colapso, sem exceção por gravidade.** Nível 0 visível, resto fechado —
  para todo item. Se nada depende da gravidade declarada para decidir o que fecha, a
  gravidade declarada não esconde nada. Gravidade serve para ordenar e marcar, não para
  fechar.
- **O rótulo do que está fechado é derivado do conteúdo, nunca escrito à parte.** Ele
  promove o primeiro impacto — o texto real que está lá dentro, já sob a régua — e conta o
  que sobrou: *"⚡ 7 de 9 commits passaram sem bump · +2 · como resolver"*. Duas
  propriedades numa: **denuncia** (fala deste problema, não da categoria dele) e **não
  esconde** (é promoção de conteúdo, não campo separado, então não há onde amaciar).
- **Etiqueta fixa foi tentada e rejeitada.** *"⚡ o que isso causa · ✅ como resolver"* era
  a mesma linha em todo bloco da página, e etiqueta que não muda não ajuda a decidir se
  vale abrir. Rótulo livre seria pior — um data-loss vira *"impacto pontual"*. A palavra
  "detalhes" é proibida: não denuncia nada.
- **Placar agregado no topo, sempre aberto, computado do conteúdo.** *"7 bloqueios · 2
  graves"*. Esconder um item passa a exigir omiti-lo por inteiro.
- **Colapsar não é amputar.** O bloco continua trino: o validador cobra que consequência e
  proposta existam e não estejam vazias **dentro** do que está fechado.
- **O que fica fora do alcance, e é dito em vez de fingido:** omissão total de um item.
  Nenhum validador de página pega o que nunca entrou nela. Onde existe fonte estruturada
  (o registro do `/qa-loop`), o cruzamento de contagem pega; onde não existe, o vetor
  continua aberto e declarado.

## Os dois defeitos que esta ordem existe para matar

- **Foreshadowing no lugar do título.** *"Consertei um plural que um executor registrou e
  não tocou"* não é título — é detalhe de uma coisa que deveria ter título útil. *"Isso aí
  é foreshadowing, isso não é informação."*
- **Volume como objetivo.** *"Parece que você trabalha com o objetivo de criar um certo
  volume de texto, que é dar um relatório de um certo tamanho mínimo, e isso não faz
  sentido."* Escopo pequeno produz artefato pequeno. Depois de um prompt em que já se
  combinou o que seria feito, o relatório responde **se deu certo** — e só isso. *"O que
  não deu certo eu decido olhar."*

## Trade-off já decidido por esta ordem

**O caso:** o relatório final da sessão de 2026-08-01
(`.claude/visual/2026-08-01-sovai-formato-de-plano.html`). Medido:

```
caracteres de texto na página : 42863
dentro de algo que abre clicando: 4612  (11%)
exposto de cara                : 38251  (89%)
blocos problema/consequência/proposta: 2 — TODOS abertos por construção

parágrafos em todos os HTML de .claude/visual/ (n=1624)
   p50 140 · p75 197 · p90 272 · p95 330 · p99 531 · máx 2182
   acima de 200 caracteres: 383 (24%)

bullets autorais hoje (n=145): mediana 117 — o teto de 140 não espreme o normal,
corta a cauda
```

**O que foi escolhido:** a ordem acima passa a valer, e a regra que produziu o número foi
declarada errada. Ela aparece duas vezes no contrato do gerador —
`plugins/visual/skills/visual/SKILL.md:421` e `:658` — e obriga o bloco de
problema/consequência/proposta a nascer aberto.

**O que foi sacrificado:** a garantia de que o problema é lido sem clique. No lugar dela
fica uma garantia mais fraca e suficiente: o problema aparece **no título**, sempre
visível; atrás do clique vai a explicação dele, nunca a existência dele. O invariante da
regra antiga sobrevive — **a posição nunca foi escolha do redator, e continua não sendo**.

**Ainda não implementado.** Isto é a meta. O mecanismo que a cobra é trabalho a fazer.
