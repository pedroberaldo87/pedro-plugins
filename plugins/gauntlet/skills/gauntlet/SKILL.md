---
name: gauntlet
description: Use quando o usuário quiser que agentes disputem contra um produto real que ele nomeia — site, jogo, tela de aplicativo, relatório, qualquer coisa que se possa construir, iterar e julgar. Dispara em "/gauntlet", "roda o gauntlet", "quero bater o site X", "isso tem que ganhar do Y", "monta um laço de crítica contra um benchmark". Quando o usuário chega sem alvos ou sem direção registrada, a abertura conduz uma descoberta curta com ele — intenção, moodboard, benchmarks — em vez de recusar e devolver o problema. O objetivo quebra em peças julgáveis, cada peça ganha um construtor e um juiz cego separado, e o juiz só aprova o que for MELHOR que o alvo — nunca o que apenas cumpre o pedido. A disputa roda como EQUIPE VISÍVEL na conversa - o dono vê cada agente, dirige em voo, veta e para; nada roda em caixa fechada. Nada do que foi construído se julga sozinho, e quem orquestra também não julga. Cada veredito é um arquivo em disco com o par de observações que o prova; uma trava de PreToolUse impede despacho novo enquanto houver entrega sem juiz; e o fecho é recusado por programa quando falta algum. Nasceu de uma falha real - sete construtores foram lançados prometendo um juiz em cada briefing, zero juízes foram lançados, e ninguém percebeu.
---

# Skill: /gauntlet

A essência, nas palavras do dono (2026-08-09):

> *"É você dar uma missão, dar um benchmark que a gente quer bater, decompor a tarefa em
> pedaços, fazer um fanout de sub-agentes para cada um atacar esse pedaço, e colocar um ou
> mais juízes que devem ficar incrivelmente impressionados no final do processo e concordar
> que a gente ganhou do benchmark. Isso inclui esses juízes estarem presentes, serem de fato
> os juízes do negócio e conseguirem enxergar e avaliar o que está sendo feito."*

E o princípio herdado do Matt Shumer (<https://somethingbig.ai/gauntlet-loop>), verbatim:

> *"give the agent a bar it can't talk its way around, let it split the work, and never let
> the builder grade itself."*

A disputa roda como **equipe de agentes visível na conversa** — decisão do dono, que
derrubou o motor fechado (a tool `Workflow`) da versão anterior. O que não mudou: quem
constrói não se julga, quem orquestra não julga, e todo julgamento vive em arquivo. Os
motivos medidos de cada trava estão em `references/porque.md`.

## O contrato de quem orquestra (você)

**Faz:** conduz a abertura · despacha e nomeia os agentes · grava decomposição, vetos e
placar · repassa ordens do dono em voo · fecha quando a conferência passa.

**Não faz: não julga.** Você escreveu os briefings e escolheu as restrições — está
contaminado. Nem como saída quando não dá para lançar o juiz: essa saída silenciosa foi a
falha de origem. Quem cobra não é esta frase, é a trava de `hooks/pretooluse-gauntlet.sh`
e o fecho de `lib/fecho_check.py`.

## 1 · A abertura — enxuta, e ela recusa começar incompleta

Colha na conversa e grave em `.claude/gauntlet/<data>-<slug>/rito.json`. **Cinco campos
obrigatórios**, e mais nada — a ficha de 9 campos da versão anterior era ritual, e o dono
mandou enxugar:

| Campo | De onde vem |
|---|---|
| `objetivo` | o dono |
| `alvos` | o dono; você pode sugerir e ele aprova — URLs concretas, nunca adjetivos |
| `sonda` | **você propõe pelo tipo de peça**, ele aprova; receitas em `references/sondas.md` |
| `eixos` | o agente de reconhecimento propõe; o dono aprova a lista |
| `orcamento` | o dono; sugira padrões (`rodadas_por_peca`, `teto_de_pecas`) |

Opcionais que entram quando existem: **`lei`** (ver o modo com lei, abaixo) · `vetos`
herdados · `raiz` (onde a obra mora, se não for a própria missão) · **`intencao`**
(produzida pela descoberta, abaixo).

**A descoberta — quando o dono chega sem os insumos, a abertura os produz COM ele.**
A abertura recusa começar incompleta, mas recusar não é devolver o problema para o dono
resolver sozinho. Se ele não tem alvos concretos, ou a obra é estética (site, tela,
jogo) e não há direção registrada em lugar nenhum — doc-load vazio, arsenal sem a seção
do tipo, nada dito na conversa —, conduza este rito curto antes de gravar o `rito.json`:

1. **Intenção** — pergunte o que a obra é, para quem, e que sensação deve causar em quem
   a encontra. Poucas perguntas, e as respostas dele entram **verbatim** no campo
   `intencao` do rito — é dali que os briefings citam, nunca da sua paráfrase.
2. **Moodboard** — peça referências que ele admira; complete com candidatas suas (a
   seção de referência visual do arsenal e busca na web pelo tipo de obra). Candidata se
   apresenta ABERTA no browser dele (`open <url>`), nunca descrita por adjetivo — ele
   aprova olhando, não imaginando. As aprovadas são direcionamento de estética e vibe,
   pela regra de sempre: vibe se transporta, forma não.
3. **Benchmarks** — das aprovadas, e do que mais ele nomear, pergunte: *"quem a gente
   quer BATER?"* O que ele apontar como régua vira `alvos` e passa pela sonda; o resto é
   referência visual e vai para a seção de moodboard do arsenal do projeto (escreva a
   pedido dele — o arquivo é dele). A diferença importa: alvo é julgado eixo a eixo;
   referência só orienta o gosto.

Dono que já chega com tudo pula a descoberta inteira — ela existe para a missão que
nasceria manca, não como ritual de toda abertura. E projeto sem doc nenhuma merece, ao
fim da missão, a oferta da concepção completa (`/start` do project-skills, se
instalado): a descoberta serve a ESTA missão, não substitui documentação.

**O ALVO É RÉGUA DE NÍVEL — NUNCA RECEITA.** A fonte da skill diz isso com todas as
letras: *"not to copy his voice, but to make the critic ask whether every paragraph in
your piece is at least as clear"* — e a barra *"does not need to be realistically
reachable"*, o que só faz sentido para um nível, jamais para um desenho. O que se
transporta do alvo é o **quão bom** ele é em cada qualidade; o que NUNCA se transporta é
o valor, a medida, o layout, o componente, a paleta, a curva. Moodboard e referência
visual são direcionamento de **estética e vibe** — não são página a reproduzir. Uma peça
que fica PARECIDA com o alvo é defeito, não vitória (dono, 2026-08-09: *"NÃO é pra
copiar a porra da página que eu falei que gostei, a não ser que eu diga explicitamente
isso"*). A exceção é essa: cópia só com ordem explícita do dono, registrada no rito —
**explícita é a palavra**: escrita por ele, não deduzida de um elogio. O eixo carrega o
número do alvo como **prova do nível**, e o juiz pergunta "o nosso é tão bom ou melhor
NESTA qualidade?" — nunca "o nosso bate o número do alvo?".

**E APROVAÇÃO ANTERIOR NÃO CANONIZA RECEITA.** O que um juiz ou o dono aprovou numa
rodada ou sessão passada é obra aceita — não vira moodboard, não vira "padrão da casa",
não entra em briefing como coisa a reproduzir. Foi assim que a contaminação real
aconteceu: um orquestrador de sessão anterior decidiu que o aprovado "passou a ser
referência", e o construtor seguinte copiou. Do aprovado, como do alvo, transporta-se o
nível e a vibe; a forma de cada peça nasce na peça.

**Os dois modos, decididos na abertura — e quem responde primeiro é programa.** Antes de
perguntar ao dono, tente a skill `doc-load` do projeto onde a missão roda:

```bash
python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/hooks/resolve-plugin.sh" project-skills lib/doc_load.py)" \
  --project-root "<raiz do projeto da obra>" --json
```

Ela diz **quais documentos valem como RÉGUA hoje** (lei + acordos aprovados) e quais são
só mapa. Com régua encontrada: os caminhos entram no campo `lei` do rito. **Quem congela
e reconfere é o programa**: o `rito` verde ancora o conteúdo de cada documento de lei
(`lei-aprovada.marca` — a âncora do rito só pega o que está DENTRO do `rito.json`, e a
lei mora em documento de fora), e o fecho acusa sozinho a lei que mudou, entrou ou sumiu
no meio da missão — mostre a acusação ao dono antes de fechar.
Sem doc-load na máquina, ou sem documento aprovado no projeto, caia na pergunta: há
documento de regras (constituição, doc de marca, spec congelada)? **Com ele**, o caminho
entra em `lei`; **sem ele**, a disputa é livre — só o alvo manda (e se nem alvo há, a descoberta acima
o produz primeiro).

O que a lei faz, nas palavras do dono: *"orienta pra evitar erros, e se fizerem cagada
ele reprova"* — ela entra no briefing de todo construtor como orientação, e o juiz
**reprova a peça que a viola de fato**, por mais bonita que esteja, **citando a
passagem violada**.

**O arsenal — o repertório do dono entra como recurso de primeira classe.** Leia, se
existirem, `~/.claude/gauntlet/arsenal.md` (global, do dono) e
`.claude/gauntlet/arsenal.md` do projeto da obra (soma-se ao global). É a lista viva de
bibliotecas, efeitos e fontes de referência dele, por seção (`## website`,
`## moodboard / referência visual`, …). Na abertura, **ofereça ao dono** a seção que casa
com o tipo da missão: o que ele aceitar entra no campo `arsenal` do rito e vai no
briefing de todo **construtor** ("estes recursos existem — use antes de reinventar") e do
**recon** (as fontes de referência visual viram candidatas a alvo complementar). Recurso
do arsenal entra pela MESMA regra do alvo: biblioteca se USA como ferramenta; fonte de
referência visual se COLHE por estética e vibe — reproduzir a página, o componente ou o
asset de um item do arsenal é a mesma reprovação da cópia do alvo. Recurso
do arsenal pode virar dependência da obra; a **entrega declara qual usou** no campo
`arsenal_usado` (lista vazia = "não usei nada"), e o dono veta se não quiser — em missão
com arsenal, entrega sem esse campo é recusada pelo fecho. **O juiz nunca recebe o arsenal** — é munição, não régua; cobrar "usou a
biblioteca X" seria revisão de checklist, não julgamento contra o alvo. Arquivo ausente
ou sem a seção do tipo: siga sem ele, calado. Quando o dono disser "adiciona X ao
arsenal", acrescente a linha na seção certa do arquivo global — é dele, você só escreve
a pedido.

**A sonda é testada antes de começar** (`teste_registro` no disco), e o reconhecimento
executa a sonda **no alvo** antes de a obra existir, devolvendo os `eixos` — o que faz o
alvo ser bom, item a item, cada um com o registro que o prova. Sem alvo, sonda e eixos o
juiz vira revisor de conformidade, que sempre aprova. Quem recusa é o programa:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/fecho_check.py" rito "<a missão>" --sinal "<o sinal>"
```

## 2 · O sinal — duas linhas, e a segunda arma a trava

```bash
GDIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/andamento"
mkdir -p "$GDIR"
printf 'gauntlet\n%s\n' "<caminho absoluto da missão>" > "$GDIR/ativo-$CLAUDE_CODE_SESSION_ID"
```

A linha 1 é o nome que a barra de status lê; a **linha 2 é o diretório da missão — é por
ela que a trava dupla sabe onde procurar pendência.** Sinal sem a linha 2 deixa a trava
muda (fail-open declarado, não proteção imaginária).

⚠️ **Quem apaga o sinal é a conferência verde, não você** — passe `--sinal` no fecho.
Há rede embaixo do esquecimento: o sinal expira por idade, e a trava desiste depois de
algumas negações **seguidas** — **avisando na conversa** que a disputa segue sem guarda.
Um juiz que nasce zera essa conta: a paciência dela se gasta em esquecimento
consecutivo, não ao longo da missão inteira. Desligamento: `GAUNTLET_GATE=0`.

**A missão sobrevive ao fim da sessão.** No arranque seguinte, um hook lê o sinal,
imprime o mapa e nomeia as entregas sem juiz — a metade que faltava do "todo veredito
vive em arquivo". Ele não retoma nada sozinho: pergunte ao dono se retoma ou encerra.

## 3 · A equipe — visível, nomeada, dirigível

Todo agente da disputa nasce pela tool `Agent`, **com `name` e com o marcador no começo
do prompt** — o marcador é o crachá que a trava lê:

| Papel | `name` | Marcador no prompt |
|---|---|---|
| reconhecimento | `recon` | `[gauntlet:recon]` |
| decompositor | `decompositor` | `[gauntlet:decompositor]` |
| construtor da peça X | `construtor-X` | `[gauntlet:construtor:X]` |
| juiz da peça X | `juiz-X` | `[gauntlet:juiz:X]` |
| diretor | `diretor` | `[gauntlet:diretor]` |

Os briefings de cada papel estão em **`references/briefings.md`** — interpole os valores
da missão (objetivo, alvo, sonda, eixos, lei, vetos) no despacho. O briefing do juiz é
inegociável no que ele **não** recebe: lista de defeitos de ninguém.

**O laço, na ordem em que os despachos acontecem:**

1. **Decomposição** — o decompositor quebra o objetivo em peças julgáveis separadamente
   (quem decompõe é o agente, não o humano). Você grava `decomposicao.json` (peça → eixos
   → arquivos; eixo que não coube em peça vai em `eixos_do_diretor`), **mostra a lista na
   conversa e segue** — o dono veta quando quiser, sem a disputa esperar.
2. **Fanout de construtores** — um por peça, em paralelo. Rodada 1 de peça exploratória:
   três propostas de verdade, escolha pelo olho. Cada construtor grava a obra, os
   registros da sonda e `pecas/<X>/r<N>/entrega.json` (caminho + marca de cada artefato —
   é alegação; o fecho recomputa tudo).
3. **Juiz, disparado pela entrega** — quando um construtor termina, o próximo despacho
   daquela peça é o juiz dela. **Não é disciplina, é mecânica:** com entrega sem veredito
   no disco, a trava de PreToolUse nega qualquer agente que não seja `[gauntlet:juiz:<a
   peça pendente>]`. O juiz executa a sonda nos DOIS lados, forma juízo antes de ler o
   relatório do construtor, e grava `veredito.json` — nulo sem o par de registros.
4. **Reprovou** — o veredito nomeia UM gap, o maior, com o par de registros. O construtor
   da rodada seguinte responde a esse defeito nomeado, sem explorar.
5. **Para** por aprovação, por `marginal` (ganho pequeno declarado pelo juiz) ou pelo
   `orcamento`. **Diretor** passa no conjunto quando as peças fecham — o defeito ENTRE
   peças é invisível aos juízes de peça.

**O placar sai a cada rodada — e sai como PÁGINA, nunca como texto no terminal.** Ordem do
dono, 2026-08-09, verbatim: *"atualiza a skill gauntlet. esses relatos de parada a cada etapa
devem ser sempre apresentados com /visual"*. Quem desenha o conteúdo é o programa; quem o
apresenta é a skill `visual`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/fecho_check.py" mapa "<a missão>"   # a matéria-prima
```

A saída dele vira o spec da página (`kind: "evidencia"` com o mapa literal, mais um `item` por
peça quando houver veredito a mostrar), e a página abre no browser do dono. **Todo relato de
parada é assim** — a rodada que fecha, a peça que o juiz reprovou, o gap nomeado, a disputa
que você para por ordem dele e o fecho. O motivo é o mesmo que fez o dono cortar a auditoria
numérica na mesma sessão: **o terminal rola, o texto sobe, e o insumo da decisão se perde no
scrollback.** Placar em texto corrido é o formato que ele já recusou.

Duas exceções, e só elas: **uma linha** dizendo o que você vai fazer em seguida continua na
conversa (a página é para o relato, não para o aviso), e a pergunta que precisa de resposta
imediata dele continua sendo pergunta — com a página aberta ao lado, nunca no lugar dela.

## 4 · A obra ao vivo — o dono e os juízes enxergam a mesma coisa

Faz parte do mecanismo (palavras do dono): **quem julga precisa conseguir observar a
obra, e o dono também.** O `preparar` da sonda põe a peça observável; quando a obra abre
no browser (site, tela), **abra-a no browser do dono** assim que a primeira versão
existir (`open <url>`), e ela evolui ali enquanto os construtores trabalham. Os juízes
observam pela MESMA sonda — nunca pelo relatório de quem construiu. Peça que não abre em
browser se observa pelo `registrar` da sonda, e o registro vai na conversa.

## 5 · O dono entra quando quiser — e a ordem chega em voo

1. **Veto é registrado por programa**, nunca por você redigindo a linha:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/fecho_check.py" veto "<a missão>" \
  --o-que "<o que ele vetou>" --pecas "<as peças que isso toca>"
```

2. **A ordem chega na hora a quem já trabalha:** repasse-a por `SendMessage` aos agentes
   vivos que ela toca — decisão do dono; a rodada em curso pode ser invalidada, e isso é
   preferível a assistir um erro conhecido terminar. E ela entra no briefing de todo
   agente das rodadas seguintes, sempre.
3. **Se o veto tocar peça já fechada, o programa avisa e você PERGUNTA** antes de
   reabrir. Ele responde manter? A linha do veto ganha `"mantido": true`.
4. **Parar a disputa** é parar de despachar e mostrar onde ficou — o `mapa` vira PÁGINA
   (`/visual`), como todo relato de parada desta skill. O dono revoga a
   própria lei: mostre a lei com a fala de origem citada literal, pergunte, registre.

## 6 · O fecho

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/fecho_check.py" fecho "<a missão>" --sinal "<o sinal>"
```

Verde: ele apaga o sinal. Vermelho: imprime o que falta, e o `mapa` é o mesmo que
ressuscita a missão depois de um `/clear`. **O que a conferência olha está na suíte
dela** (`lib/test_fecho_check.py`), não escrito aqui — número cravado em prosa envelhece
sozinho.

## 7 · Fronteiras e armadilhas

- **Copiar o alvo é a armadilha número um, e ela mordeu de verdade.** Numa missão real
  (2026-08-09), o eixo descritivo "moldura de 32px" virou moldura de 32px na obra, a
  pílula do alvo virou pílula com as mesmas proporções, e um juiz chegou a cobrar que o
  nosso peso de rolagem BATESSE a constante física do alvo. O mecanismo do erro: quem
  orquestra interpola o número do eixo no briefing como meta, e o construtor obedece. O
  número do eixo é prova do NÍVEL do alvo; o briefing transporta a qualidade nomeada,
  nunca o número como alvo a atingir. Reveja cada briefing por isso antes de despachar.
- **Não automatize o julgamento estético.** Toda medida tentada nas sessões de origem
  enganou pelo menos uma vez. Medida detecta regressão; não diz se está bom.
- **Relatório longo não é qualidade.** Responder "aceito" a um relatório bom *parece*
  julgar, quando é só avaliar a argumentação — foi a causa (a) da falha de origem.
- **Criar asset é permitido; falsificar não.** Imagem simbólica, objeto, textura e
  representação se CRIAM à vontade (o critério é a pretensão: símbolo, sim; coisa que
  se passe por foto/registro do que não aconteceu, não). O que não se fabrica é o asset
  REAL que falta — pessoa, logotipo, foto de lugar: para esse, lugar honesto, e aquele
  pedaço sai do julgamento. A regra "asset não se inventa" sem essa distinção foi
  invenção de agente, corrigida pelo dono (2026-08-09).
- **Três propostas só na primeira rodada**, e só em peça exploratória. Rodada de conserto
  responde a um defeito nomeado.
- **Tipo novo de peça é sonda nova** escrita na abertura (`references/sondas.md`), nunca
  emenda nesta skill.
- **Não é o motor de execução autônoma deste marketplace.** Lá a pergunta é *"o combinado
  saiu?"* — conformidade, que sempre dá sim. Aqui é *"isso ganha do alvo?"*.
