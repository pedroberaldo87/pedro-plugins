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

→ Foi por isso que a primeira versão rodava num motor fechado (a tool `Workflow`), onde o
juiz era o `await` seguinte ao do construtor. **O dono derrubou a caixa fechada em
2026-08-09** — ele quer ver a equipe, dirigir em voo e parar quando quiser — e o gatilho
mudou de lugar sem deixar de ser mecânico: a trava de `hooks/pretooluse-gauntlet.sh`
consulta o disco (`fecho_check.py pendentes`) antes de todo despacho, e enquanto houver
entrega sem veredito só o juiz da peça pendente nasce. O esquecimento continua impossível;
o que mudou é que agora ele é impossível À VISTA.

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

## Os limites declarados da trava — o que ela barra, e o que ela não barra

**A trava barra ESQUECIMENTO, não disfarce.** O crachá do juiz é auto-declarado: ela lê
o marcador `[gauntlet:juiz:<peça>]` no texto do prompt, e qualquer prompt pode trazê-lo.
Um briefing de construtor colado com o marcador errado fura a trava sem ninguém ver. É
limite aceito: a falha medida foi omissão (zero juízes lançados), nunca fraude — e
validar o corpo do briefing custaria caro para proteger contra um defeito que não
aconteceu. O que sobra de rede é o fecho, que recusa veredito sem o par de registros.

**A desistência fala, e a paciência é de negações SEGUIDAS.** Depois do teto a trava
se desarma — decisão declarada: travar a missão longa com o dono fora custa mais que o
defeito. Dois furos vieram daí na revisão de 2026-08-09, e os dois estão consertados:

```
o teto de 3 era da SESSÃO INTEIRA, e nada zerava a conta. Medido:
  sete peças entregues, zero juízes, e três esquecimentos em peças diferentes
  [1o] NEGADO  [2o] NEGADO  [3o] NEGADO  →  [4o] PASSOU  [5o] PASSOU  [6o] PASSOU
  pendentes depois disso: p1 p2 p3 p4 p5 p6 p7
```

É a falha de origem inteira, com o guarda desligado por cansaço. O teto de 3 tinha sido
calibrado para a trava da v0.1, que negava TODO sub-agente; a trava de hoje só nega com
pendência real, e o mesmo número virou frouxo. **Agora o juiz que nasce zera o contador**
— três esquecimentos SEM nenhum juiz no meio ainda desarmam, que é o cenário que a
válvula existe para atender. E o desarme, que falava só com um log que ninguém abre,
hoje avisa na conversa nomeando as entregas sem veredito.

---

## A rodada intermediária — a entrega sem juiz que a rodada seguinte encobria

Medido na mesma revisão. O conferente olhava só a ÚLTIMA rodada de cada peça:

```
r1  entregue, SEM veredito        ← ninguém julgou
r2  entregue e aprovada
fecho:  "fecho liberado — todo pedaço julgado, com o par de registros."
```

A frase era falsa, e a falha de origem passava pela porta de trás. Hoje **toda rodada
com entrega tem que ter juiz**, no fecho e na lista que a trava consulta. No laço normal
isto nunca acusa nada: rodada anterior é rodada que o juiz reprovou, e reprovar é gravar
veredito.

---

## O código velho rodando enquanto se revisa o novo

O dono passou uma sessão inteira revisando, testando e aprovando a v0.4.0. **O que
rodava na máquina dele era a 0.3.2**, instalada dias antes — sem nenhum dos consertos.
Editar o repositório não muda o que o harness carrega: ele lê o cache de
`~/.claude/plugins/`, e o cache só troca com `claude plugin update` mais um reinício.

→ Daí o aviso de arranque do repositório (`.claude/hooks/sessionstart-avisa-cadeia.sh`,
apoiado em `scripts/cadeia_check.py`): quando a versão instalada fica atrás da escrita,
o arranque diz as duas, e diz que teste no repositório vale como leitura de código e não
como prova de comportamento. É a mesma lição de sempre — **o estado silencioso parece
normal em qualquer foto que se tire**.

---

## A régua do crescimento — recurso novo só entra com o cobrador junto

Revisão de 2026-08-09: entre a v0.1 e a v0.3.2 entraram a lei, a régua vinda do
doc-load e o arsenal — e **nenhum dos três chegou com conferência de programa junto**.
"Reconfira a lei no fecho" e "a entrega declara o que usou" eram prosa, a mesma classe
de furo que criou a skill (regra escrita em sete briefings, cumprida em zero).

Os dois ganharam cobrador na mesma revisão (`lei-aprovada.marca` e `arsenal_usado`,
ambos em `lib/fecho_check.py`). A régua que fica: **recurso novo nesta skill entra com
o programa que o cobra, ou com a ausência do cobrador escrita aqui, com o motivo** —
como fazem as duas seções acima.

---

## A percepção do dono é MEDÍVEL — e vira eixo, não só veto

Medido em 2026-08-09. Dez referências foram abertas de uma vez no navegador do dono, e ele
devolveu uma frase que parecia gosto: *"dragonfly, risk film, inspiring, izanami ficou muito
pesado"*, e depois *"sobre izanami ficou pesado na maquina. o site também precisa performar"*.

A sonda mediu os mesmos sites, pelo mesmo gesto, um de cada vez:

```
izanami-official.com     9,8 quadros por segundo   ·  quadro mediano  84,1ms
dragonfly.xyz            7,1                       ·                 150,0ms
verostudio.com          20,3                       ·                  50,0ms
apple.com/airpods-pro   60,3                       ·                  16,7ms   com 14.287kB
rocnation.com           60,3                       ·                  16,7ms   com    691kB
controle (8 divs)       60,3                       ·                  16,7ms
```

Ele acertou os dois que travavam, de olho, sem ferramenta nenhuma. Duas lições:

**A primeira:** quando o dono descreve uma sensação, procure a coluna que a mede antes de
tratá-la como gosto. A frase dele virou um eixo com registro — e um alvo que ele "não gostou"
virou **anti-alvo declarado no rito**, que é informação que nenhum veto sozinho carrega.

**A segunda:** a sonda da missão anterior media só composição, e por isso a disputa inteira
correu sem ninguém olhar o custo de rodar a obra. Não foi omissão do juiz: **o que a sonda não
observa, o juiz não julga.** Eixo sem coluna na sonda é eixo que não existe.

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

---

## A noite em que onze vereditos honestos aprovaram uma obra vergonhosa (2026-08-09)

A falha que motivou a versão 0.9.0. Uma missão real rodou a noite inteira em autonomia:
5 peças, 11 rodadas, 11 vereditos, 20 agentes, 417 capturas — e nenhuma reprovação em
aberto no fim. O veredito do dono ao ver o resultado, verbatim: *"Se você me perguntasse,
eu diria que o seu juiz DESISTIU em algum momento de fazer as coisas, e não que alguém
olhou e achou bom. porque tá simplesmente vergonhoso esse trabalho."*

O que o disco mostrou, e o que cada achado virou:

- **A rendição.** Duas peças fecharam na PRIMEIRA rodada de quatro por `marginal` — a
  disputa parou com 45% do orçamento intacto, e a skill autorizava por escrito ("para por
  aprovação, por marginal ou pelo orçamento"). Virou a regra nova: `marginal` é relato,
  nunca saída — fecha peça só juiz boquiaberto, dono, ou orçamento esgotado, e quem
  recusa é `fecho_check.py`.
- **A barra fatiada.** O reconhecimento devolveu 15 eixos, a decomposição os distribuiu
  2 a 4 por peça, e nenhuma peça jamais enfrentou o alvo inteiro — cada juiz só via o seu
  recorte. Virou: o trabalho se decompõe, a barra não; todo juiz confronta a obra inteira
  com o alvo inteiro, e os eixos são lente de atenção.
- **A medição no lugar do olho.** A pergunta operante era "é melhor naquela qualidade?",
  que se responde comparando grandezas; a da fonte é "don't stop until utterly wowed",
  que se responde olhando. Virou: o veredito declara `impressionado` (true/false) e uma
  `frase` de gente, e aprovar sem impressão é recusado por programa.
- **O falso "estou livre".** Dois agentes anunciaram disponibilidade com o disco vazio,
  sem dizer que travaram. Virou regra comum de todos os briefings: se travou, grave o que
  andou e diga o que travou.
- **O estouro sem mensagem.** Três vereditos gravaram lista ou bloco onde o programa
  esperava texto, e a resposta era exceção sem linha útil. Virou recusa nomeando o campo.

E o espírito, medido na fonte: o prompt original do Claude-of-Duty tem 149 palavras, das
quais 13 são ambição ("utterly perfect", "utterly wowed", "really harsh critic") e ZERO
são procedimento — nenhum arquivo, nenhum campo, nenhuma prova. A skill tinha 9.413
palavras com 288 termos de procedimento e 2 de ambição. O mecanismo de prova, funcionando
como projetado, premiou o mensurável e expulsou o estético — número é citável e sobrevive
ao fecho; "olhei e está feio" não era auditável. A correção de 0.9.0 tornou o olhar
auditável (o campo `impressionado` + a frase) em vez de acrescentar mais prosa.

## As histórias que saíram do corpo da skill no enxugamento (0.9.0)

O corpo passou a carregar só o procedimento; cada regra continua lá, em uma linha. As
origens, na íntegra:

- **Copiar o alvo mordeu de verdade.** Numa missão real, o eixo descritivo "moldura de
  32px" virou moldura de 32px na obra, a pílula do alvo virou pílula com as mesmas
  proporções, e um juiz chegou a cobrar que o peso de rolagem BATESSE a constante física
  do alvo. O mecanismo: quem orquestra interpola o número do eixo no briefing como meta,
  e o construtor obedece. Dono, verbatim: *"NÃO é pra copiar a porra da página que eu
  falei que gostei, a não ser que eu diga explicitamente isso."* Hoje quem recusa medida
  em nome de eixo é o `rito`, e a linha `RÉGUA, NUNCA RECEITA` é exigida pela trava em
  todo briefing de construtor e juiz.
- **Aprovação anterior não canoniza receita.** Um orquestrador de sessão anterior decidiu
  que o aprovado "passou a ser referência", e o construtor seguinte copiou. Do aprovado,
  como do alvo, transporta-se nível e vibe; a forma de cada peça nasce na peça.
- **A oferta do diretor criativo para o turno.** A primeira versão oferecia o papel de
  passagem, no meio de um parágrafo, e o dono passaria batido: *"o ideal seria oferecer o
  diretor criativo como uma pausa na skill (…) ele tem que ser de nascença senão fudeu."*
  Por isso a oferta é `AskUserQuestion` antes de qualquer despacho, e `false` vale a
  missão inteira.
- **O placar sai como página, nunca como texto no terminal.** Ordem do dono: *"esses
  relatos de parada a cada etapa devem ser sempre apresentados com /visual"* — o terminal
  rola, o texto sobe, e o insumo da decisão se perde no scrollback.
- **Criar asset é permitido; falsificar não.** Símbolo, textura e representação se criam
  à vontade; o que não se fabrica é o que se passaria por foto ou registro do que não
  aconteceu. Asset real que falta (pessoa, logotipo, lugar) ganha lugar honesto e sai do
  julgamento. A regra sem essa distinção era invenção de agente, corrigida pelo dono.

## As histórias das regras comuns dos briefings (movidas no enxugamento de 0.9.x)

- **Toda entrega é arquivo, nunca texto de retorno.** Medido em 2026-08-09: dois agentes
  terminaram o trabalho — um deles com 40 capturas e 40 medições ao lado —, avisaram três
  vezes que estavam livres, e nenhuma linha do retorno deles chegou a quem os despachou.
  O trabalho existia no disco e a leitura se perdeu no caminho: não é falha de agente, é
  o canal. Por isso cada papel grava em caminho fixo (`recon/eixos.json`,
  `decomposicao.json`, `pecas/<X>/r<N>/entrega.json`, `veredito.json`, `diretor.json`) e
  quem despacha confere o arquivo.
- **A fonte da régua anti-cópia**, verbatim: *"not to copy his voice, but to make the
  critic ask whether every paragraph in your piece is at least as clear."* E a ordem do
  dono que a selou: cópia só com ordem explícita dele, escrita — nunca deduzida de um
  elogio ou de uma aprovação anterior.
- **O diretor exigindo impressão no conjunto (0.9.x).** Com cada peça exigindo juiz
  boquiaberto, a última porta da barra fatiada era o conjunto fechar "no nível do alvo" —
  a pergunta de conformidade. O diretor agora declara `impressionado` e a frase, cobrados
  por `fecho_check.py`. O orgulho do construtor chegou a virar campo recusável e VOLTOU
  a ser aspiração de briefing — régua do original: "never let the builder grade
  itself"; a autoavaliação do autor não é contrato, e quem cobra qualidade é o crítico.
