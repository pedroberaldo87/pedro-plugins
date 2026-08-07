# Por que cada peça desta skill existe

Nenhuma trava aqui é precaução contra risco imaginado. Cada uma tem uma falha medida atrás,
em duas sessões reais de ~14 horas, e este arquivo é onde elas ficam — fora do corpo da
skill, porque quem a executa precisa da regra, não da história.

---

## A falha central: sete construtores, zero juízes

O orquestrador escreveu, em **todos os sete** briefings de construtor:

> *"Um juiz separado vai abrir os alvos ao vivo e comparar. Ele não recebe lista de defeitos
> de ninguém — nem sua, nem minha."*

**Lançou zero juízes.** Leu os relatórios, olhou os registros que os próprios construtores
produziram, e aceitou tudo. O dono descobriu olhando o produto:

> *"não é possível que esses layouts básicos, sem animação e sem recursos nem sofisticação
> ganharam o gauntlet e alguém julgou 'surpreendente' e digno de ganhar da apple. Como isso é
> possível?"*

Não houve julgamento nenhum. Ninguém disse "surpreendente" — o orquestrador simplesmente
aceitou. E não foi lapso isolado: **a mesma falha já tinha acontecido antes, na mesma
sessão**, e só foi corrigida porque o dono perguntou *"quem está responsável pelo loop
crítico?"*.

### As quatro causas, e a última é a que a skill ataca

**(a) Relatório bom parece trabalho bom.** Os construtores escreveram relatórios excelentes —
tabelas, medições, alternativas descartadas, defeitos próprios confessados. Responder
"aceito" a um relatório desses *parece* julgar. O que se avaliava era a qualidade da
argumentação, não a da obra. É o que Shumer chama de *"a bar it can't talk its way around"*: a
régua existia no papel e era contornável na conversa.

**(b) A régua errada é a mais fácil de pegar.** Julgava-se *"isso resolveu o que o dono
pediu?"*. O gauntlet exige *"isso ganha do alvo?"*. A primeira é conformidade, e sempre dá sim.

**(c) Quem orquestra está contaminado.** Escreveu os briefings, escolheu as restrições,
decidiu impasses. Quando o trabalho chegou, já tinha investido nele. *"Never let the builder
grade itself"* — **e o orquestrador também não pode**, e essa segunda metade não está na fonte
original.

**(d) O spawn do juiz era um evento SEM GATILHO.** O construtor entrega, chega a notificação,
o orquestrador lê o relatório — e nada dispara o juiz. O estado default do sistema é "zero
juízes", e ele parece normal em qualquer foto que se tire. **Não é falta de disciplina: é
ausência de gatilho.**

→ É por isso que, no motor, o juiz é o `await` seguinte ao do construtor. Não existe
caminho da entrega ao fecho que o pule, porque quem lança não é quem orquestra.

---

## A descoberta que muda o diagnóstico

**Mesmo quando os juízes existiram e reprovaram, nenhum laço fechou.**

```
juiz do hero        REPROVADO — 2 artigos congelados + 8 itens de acabamento
juiz das marcas     REPROVADO — composição
juiz do contato     REPROVADO — 11 itens com prova
reconhecimento      REPROVADO
fundação            3 aprovados · 3 reprovados · 1 parcial

APROVADO de juiz de peça na sessão inteira:  ZERO
```

O que matou os laços não foi declaração indevida de "pronto". Foi **interrupção**: o dono
mandou ~35 direcionamentos em duas horas, vetou dois gestos estéticos, chamou o resultado de
"AI Slop" e disparou uma redução de 46% do produto — tudo isso com vereditos REPROVADO em
aberto. O estado *"o hero ainda está reprovado"* evaporou porque **vivia na conversa, e a
conversa foi atropelada**.

→ É por isso que todo veredito é arquivo em disco, e por isso o subcomando `mapa` existe:
ele é o que ressuscita a missão depois de um `/clear`.

---

## O juiz cego, medido contra o ancorado

O orquestrador deu ao crítico do hero a própria lista de três defeitos. Depois lançou um
segundo crítico **sem lista nenhuma**, na mesma peça:

```
o crítico ANCORADO achou 7 defeitos: 1 veio da lista, 6 achou sozinho
dos 3 da lista, DOIS não se sustentaram na medição:
  "lead quebra em 3 linhas, 60% vazio"  →  em 1440 são 2 linhas, razão 0,944
                                           (a do alvo é 0,873 — o nosso é melhor)
  "indicador a 8px do canto"             →  está a 63px; o do alvo a 20px

o crítico CEGO achou coisas que nenhum dos dois teria achado —
  entre elas a cauda de uma letra invadindo a linha de baixo
```

**Crítico que recebe lista procura aquilo e para.**

→ É por isso que o briefing do juiz manda ignorar qualquer lista e declarar que ignorou.

---

## O construtor que mediu a acusação antes de obedecer

Duas vezes o orquestrador mandou corrigir um defeito, e o agente voltou com a prova de que
ele não existia:

```
orquestrador:  "a coluna tem muito ar embaixo do parágrafo, meça"
agente:        vão da régua ao fecho = 44px · um respiro de bloco = 58,5px
               coluna 373px com 296px de conteúdo — os 77px são os dois vãos internos
               "não há um pixel de vazio solto"
```

Se ele tivesse obedecido, teria estragado o que estava certo.

→ É por isso que o briefing de conserto manda medir antes, **inclusive contra quem orquestra**.

---

## O descarte é o argumento

Os melhores relatórios não explicavam por que a escolha era boa. Explicavam por que as outras
eram ruins, com o motivo visto na tela:

```
A · o alvo ao pé da letra   repouso e apontado ficaram INDISTINGUÍVEIS no registro
B · canto reto              o botão vazado passa a ler como campo de formulário
C · acento só na aresta     ao lado do vazado viram dois anéis de mesma silhueta
```

→ É por isso que a entrega exige os descartes, com o que se viu na tela.

---

## Três propostas de verdade

A instrução que produziu o melhor trabalho das duas sessões:

> *"Não escolha um design e defenda. Faça três propostas diferentes de verdade — não três
> variações da mesma —, monte lado a lado, e OLHE. Escolha com o olho, não com o argumento."*

Em dois casos o resultado foi melhor que as três: o agente descartou todas e montou uma quarta
com o que sobreviveu de cada uma.

→ E **só vale na primeira rodada**: nas rodadas de conserto o construtor responde a um defeito
nomeado, e explorar ali é desperdício.

---

## O eixo que ninguém possuía

O crítico do hero viu uma medida em 74% e aprovou. O do contato viu 62% e aprovou. **A
incoerência não morava em nenhuma das duas peças** — e nenhum juiz de peça tinha como vê-la.

→ É por isso que a decomposição exige dono para todo eixo, e que o diretor existe: ele é o
dono dos que sobram.

---

## O caderno de vetos

Da sessão anterior:

> *"O veredito do seu moodboard anterior foi para dentro do prompt de cada uma, para não
> voltarem com o que você já matou"* — os 12 rejeitados listados como proibidos, e as notas de
> gosto do dono como calibragem.

E na sessão do gauntlet: uma lei foi escrita 40 minutos depois da ordem que a originou, e
**dois agentes já a tinham violado sem saber**.

→ É por isso que todo veto entra em todo briefing das rodadas seguintes. E por isso a lei nova
chega à **rodada seguinte**, não aos agentes já disparados — prometer o contrário seria
descrever proteção inexistente.

---

## O dono revoga a própria lei

Duas vezes ele pediu algo que contrariava lei que ele mesmo ditara. O que funcionou: mostrar a
lei com a fala de origem citada literal, perguntar, e registrar a revogação com data e motivo.
A resposta dele:

> *"Então, muda a lei, ok? Eu pedi, eu escrevo a lei. Obrigado por avisar."*

---

## O que a skill NÃO tem, e por quê

**Métrica estética automática.** Toda medida tentada — saturação, pixels em cor forte,
densidade — enganou pelo menos uma vez. Serve para detectar regressão, não para dizer se está
bom.

**Dois ou três juízes por peça.** Não foi testado, multiplica o custo da parte que já não
acontecia por ser cara, e a fonte original resolve leniência com a régua — *"the bar is the
most important part"* — não com mais juízes.

**Um custo grande.** A matemática que a primeira versão do briefing tinha — sete peças × três
propostas × N rodadas × dois a três juízes × laço sem fim — é teatro de processo: ninguém
paga, e o orquestrador volta a cortar exatamente o pedaço que a skill existe para proteger.
**Skill cara demais reproduz a causa (d) dentro de si mesma.**
