---
name: gauntlet
description: Use quando o usuário quiser que agentes disputem contra um produto real que ele nomeia — site, jogo, tela de aplicativo, relatório, qualquer coisa que se possa construir, iterar e julgar. Dispara em "/gauntlet", "roda o gauntlet", "quero bater o site X", "isso tem que ganhar do Y", "monta um laço de crítica contra um benchmark". O objetivo quebra em peças julgáveis, cada peça ganha um construtor e um juiz cego separado, e o juiz só aprova o que for MELHOR que o alvo — nunca o que apenas cumpre o pedido. A disputa roda como EQUIPE VISÍVEL na conversa - o dono vê cada agente, dirige em voo, veta e para; nada roda em caixa fechada. Nada do que foi construído se julga sozinho, e quem orquestra também não julga. Cada veredito é um arquivo em disco com o par de observações que o prova; uma trava de PreToolUse impede despacho novo enquanto houver entrega sem juiz; e o fecho é recusado por programa quando falta algum. Nasceu de uma falha real - sete construtores foram lançados prometendo um juiz em cada briefing, zero juízes foram lançados, e ninguém percebeu.
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
herdados · `raiz` (onde a obra mora, se não for a própria missão).

**Os dois modos, decididos na abertura — e quem responde primeiro é programa.** Antes de
perguntar ao dono, tente a skill `doc-load` do projeto onde a missão roda:

```bash
python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/hooks/resolve-plugin.sh" project-skills lib/doc_load.py)" \
  --project-root "<raiz do projeto da obra>" --json
```

Ela diz **quais documentos valem como RÉGUA hoje** (lei + acordos aprovados) e quais são
só mapa. Com régua encontrada: os caminhos entram no campo `lei` do rito, e a saída de
`--marca` entra em `lei_marca` — é o congelamento da lei; a âncora do rito só pega o que
está DENTRO do `rito.json`, e a lei mora em documento de fora. No fecho, rode `--marca`
de novo: divergiu, a lei mudou no meio da missão — mostre ao dono antes de fechar.
Sem doc-load na máquina, ou sem documento aprovado no projeto, caia na pergunta: há
documento de regras (constituição, doc de marca, spec congelada)? **Com ele**, o caminho
entra em `lei`; **sem ele**, a disputa é livre — só o alvo manda.

O que a lei faz, nas palavras do dono: *"orienta pra evitar erros, e se fizerem cagada
ele reprova"* — ela entra no briefing de todo construtor como orientação, e o juiz
**reprova a peça que a viola de fato**, por mais bonita que esteja, **citando a
passagem violada**.

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
algumas negações na mesma sessão. Desligamento de emergência: `GAUNTLET_GATE=0`.

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

**O placar sai na conversa a cada rodada** — e é o programa que o desenha:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/fecho_check.py" mapa "<a missão>"
```

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
4. **Parar a disputa** é parar de despachar e dizer onde ficou (`mapa`). O dono revoga a
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

- **Não automatize o julgamento estético.** Toda medida tentada nas sessões de origem
  enganou pelo menos uma vez. Medida detecta regressão; não diz se está bom.
- **Relatório longo não é qualidade.** Responder "aceito" a um relatório bom *parece*
  julgar, quando é só avaliar a argumentação — foi a causa (a) da falha de origem.
- **Asset que não existe não se inventa.** Deixa-se um lugar honesto para ele, e aquele
  pedaço sai do julgamento.
- **Três propostas só na primeira rodada**, e só em peça exploratória. Rodada de conserto
  responde a um defeito nomeado.
- **Tipo novo de peça é sonda nova** escrita na abertura (`references/sondas.md`), nunca
  emenda nesta skill.
- **Não é o motor de execução autônoma deste marketplace.** Lá a pergunta é *"o combinado
  saiu?"* — conformidade, que sempre dá sim. Aqui é *"isso ganha do alvo?"*.
