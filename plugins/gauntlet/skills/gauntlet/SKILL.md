---
name: gauntlet
description: Use quando o usuário quiser que agentes disputem contra um produto real que ele nomeia — site, jogo, tela de aplicativo, relatório, qualquer coisa que se possa construir, iterar e julgar. Dispara em "/gauntlet", "roda o gauntlet", "quero bater o site X", "isso tem que ganhar do Y", "monta um laço de crítica contra um benchmark". O objetivo quebra em peças julgáveis, cada peça ganha um construtor e um juiz cego separado, e o juiz só aprova o que for MELHOR que o alvo — nunca o que apenas cumpre o pedido. Nada do que foi construído se julga sozinho, e quem orquestra também não julga. Cada veredito é um arquivo em disco com o par de observações que o prova, e o fecho é recusado por programa quando falta algum. Nasceu de uma falha real - sete construtores foram lançados prometendo um juiz em cada briefing, zero juízes foram lançados, e ninguém percebeu, porque um sistema sem gatilho é indistinguível de um sistema em que tudo foi aprovado.
---

# Skill: /gauntlet

Agentes disputando contra um produto real, com quem constrói separado de quem julga.

**A técnica é do Matt Shumer** (<https://somethingbig.ai/gauntlet-loop>), verbatim:

> *"give the agent a bar it can't talk its way around, let it split the work, and never let
> the builder grade itself."*

**O que esta skill acrescenta a ela**, e o motivo de cada um está em `references/porque.md`:
o julgamento vive em arquivo, porque a conversa é atropelável · o fecho é recusado por
programa, porque o estado sem juiz parece normal · existe um caderno de vetos, porque existe
um dono, e a técnica original não tem dono.

## O contrato

**Faz:** conduz a abertura até o rito estar completo · dispara o motor · registra os vetos do
dono · fecha quando a conferência passa.

**Não faz:** não julga. Quem orquestra está contaminado por ter escrito os briefings e
escolhido as restrições — **nem como saída quando não dá para lançar o juiz**, que foi
exatamente a saída silenciosa que produziu a falha de origem.

## 1 · A abertura — e ela recusa começar incompleta

Nada fica para ser resolvido durante a execução. Colha os nove, na conversa, e grave em
`.claude/gauntlet/<data>-<slug>/rito.json`:

| # | Campo | De onde vem |
|---|---|---|
| 1 | `objetivo` | o dono |
| 2 | `tipo` | o dono |
| 3 | `alvos` | o dono; você pode sugerir e ele aprova |
| 4 | `sonda` | **você propõe pelo tipo**, ele aprova |
| 5 | `eixos` | **você propõe pelo reconhecimento**, ele aprova a lista |
| 6 | `congelado` / `liberado` | o dono |
| 7 | `material` | o dono — o que pode ser gerado, o que não |
| 8 | `orcamento` | o dono; sugira padrões |
| 9 | `vetos` herdados | o dono, se houver |
| — | `raiz` | onde a obra mora, se não for a própria missão — sem isso o artefato relativo não é achado |

**Sem alvo, sonda e eixos não há gauntlet** — o juiz ficaria sem régua ou sem procedimento, e
viraria revisor de conformidade, que sempre aprova. Quem recusa é o programa:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/fecho_check.py" rito "<a missão>" --sinal "<o sinal>"
```

Ele também recusa abrir uma segunda missão com uma de pé.

### A sonda — o que torna a skill genérica sem virar vaga

A sonda é **como observar**, declarada por tipo de peça e testada antes de começar:

```json
"sonda": {
  "preparar":  "o comando que põe a peça observável",
  "registrar": "o comando que produz o registro",
  "interagir": "os gestos que valem neste meio",
  "alvo":      "como observar o alvo pelo MESMO procedimento",
  "teste_registro": "o registro que a sonda produziu quando você a rodou"
}
```

O último campo é o que faz "a sonda foi testada" ser fato e não promessa: o programa confere
que o arquivo existe e não está vazio. As receitas por tipo estão em `references/sondas.md` —
**tipo novo é sonda nova escrita na abertura, nunca emenda nesta skill.**

### Os eixos — o que "melhor" quer dizer

Um agente de contexto limpo executa a sonda **no alvo**, antes de a nossa obra existir, e
devolve o que faz o alvo ser bom, item a item:

```json
"eixos": [ { "nome": "a qualidade nomeada",
             "gesto": "qual gesto da sonda a expõe",
             "registro": "o registro DO ALVO que a prova" } ]
```

Com isso, "melhor que o alvo" para de ser adjetivo: **para cada eixo, o par de registros — o
nosso e o do alvo, produzidos pelo mesmo gesto — mostra o nosso ganhando.** Reprovar é nomear
o eixo onde o alvo mais ganha, com o par colado.

Qualidade que não cabe em medida não é proibida de julgar. O proibido é julgá-la sem âncora:
o programa confere que os dois registros existem, nunca o gosto.

## 2 · O sinal — e ele é a primeira coisa

Antes de disparar o motor, acenda; ao entregar, apague. É ele que faz o guarda existir:

```bash
GDIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/gauntlet"
mkdir -p "$GDIR"
: > "$GDIR/ativo-$CLAUDE_CODE_SESSION_ID"
```

Enquanto ele está aceso, `hooks/pretooluse-gauntlet.sh` **nega** todo disparo de sub-agente
fora do motor — a proibição de julgar na mão vira mecânica. Fora do gauntlet ele é mudo.
Desligamento: `GAUNTLET_GATE=0`.

⚠️ **Quem apaga o sinal é a conferência verde, não você** — e isso é uma linha de
`lib/fecho_check.py`, não uma regra de conduta: passe o caminho do sinal em `--sinal` no
comando de fecho, e ele o remove quando as conferências passam. Fecho vermelho não o toca.

Há rede embaixo do esquecimento: o sinal expira por idade, e o guarda desiste depois de
algumas negações na mesma sessão. Missão longa com o dono fora não pode travar por infra.

## 3 · O motor

O laço inteiro vive em **`references/motor.js`** — leia o arquivo e passe-o à tool `Workflow`.
Ele não está aqui de propósito: esqueleto dentro do arquivo de instrução é o grosso da maior
skill deste marketplace, e ele não precisa ocupar o contexto de quem orquestra.

Os parâmetros que a casca compõe e passa em `args`:

| Parâmetro | O que é |
|---|---|
| `missao` | o diretório em `.claude/gauntlet/` |
| `rito` | o conteúdo de `rito.json`, já aprovado |
| `pluginRoot` | a raiz deste plugin, para o motor chamar a conferência |
| `sinal` | `$GDIR/ativo-$CLAUDE_CODE_SESSION_ID` — o motor o repassa à conferência, que é quem o apaga |
| `tetoRodadas` · `tetoGasto` · `tetoPecas` | do `orcamento` do rito |

**O que o motor garante, e que não depende da memória de ninguém:** o juiz é o `await`
seguinte ao do construtor, sem desvio que o pule · veredito sem eixo ou sem os dois registros
é recusado e o papel roda de novo · a decomposição não passa com peça órfã nem eixo sem dono ·
o laço para por aprovação, por `marginal` do juiz, ou pelo orçamento.

Os quatro briefings — reconhecimento, construtor, juiz e diretor — são as funções `…Prompt`
do próprio `motor.js`. Eles não são texto estático: injetam o congelado, os vetos, a sonda e
os eixos da missão, e um arquivo separado interpolado à mão recriaria um canal frouxo entre
o valor e quem o usa — canal que já falhou noutro motor deste marketplace.

## 4 · Quando o dono entra no meio

A missão é autônoma; ele entra quando quer. Três coisas acontecem, e só três:

1. **O laço não tem como ser pausado em voo** — o que existe é parar o motor, e o que chega
   à rodada seguinte é o caderno. Se a intervenção for urgente, pare a missão; se puder
   esperar a volta, o caderno já a leva.
2. **O veto é registrado por programa**, nunca por você redigindo a linha:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/fecho_check.py" veto "<a missão>" \
  --o-que "<o que ele vetou>" --pecas "<as peças que isso toca>"
```

3. **Se o veto tocar coisa já fechada, o programa avisa e você PERGUNTA** antes de reabrir.
   Ele responde manter? A linha do veto ganha `"mantido": true`.

**Lei nova se escreve na hora**, e entra em todo briefing **da rodada seguinte** — agente já
disparado não recebe atualização, e dizer que recebe seria descrever proteção inexistente.

**O dono revoga a própria lei.** Aconteceu duas vezes na sessão de origem: mostre a lei com a
fala que a originou citada literal, pergunte, e registre a revogação com o motivo.

## 5 · O fecho

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/fecho_check.py" fecho "<a missão>"
```

Verde: ele apaga o sinal. Vermelho: ele imprime o que falta, e o mapa é o mesmo que ressuscita
a missão depois de um `/clear`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/fecho_check.py" mapa "<a missão>"
```

**O que a conferência olha está na suíte dela**, não escrito aqui — número cravado em prosa
envelhece sozinho. Rode `python3 "${CLAUDE_PLUGIN_ROOT}/lib/test_fecho_check.py"` para ver
cada caso com o nome da falha real que ele reproduz.

O relatório final vai para uma página no browser quando a skill de apresentação visual estiver
instalada; sem ela, sai em texto aqui — a informação é a mesma, só a forma degrada.

## 6 · Quem escreve cada arquivo

Arquivo de dono indefinido é arquivo que o interessado carimba. Por isso:

| Arquivo | Quem escreve | Quem valida |
|---|---|---|
| `rito.json` | você, com o dono aprovando cada campo | `fecho_check.py rito` |
| `recon/eixos.json` | o agente de reconhecimento; o dono aprova | `fecho_check.py rito` |
| `decomposicao.json` | o motor grava o que o decompositor devolveu | o motor, antes de soltar construtor |
| `entrega.json` | o construtor — é **alegação**, não carimbo | `fecho_check.py fecho`, recomputando a marca de cada artefato contra o disco |
| `veredito.json` | **o motor**, com o que o juiz devolveu | `fecho_check.py fecho` |
| `rito-aprovado.marca` | `fecho_check.py rito`, quando a abertura passa | `fecho_check.py fecho` |
| `vetos.jsonl` | `fecho_check.py veto` | `fecho_check.py fecho` |
| `MAPA.md` | `fecho_check.py mapa` — derivado | — |

O construtor escrever a própria entrega não reabre o problema do interessado que se carimba:
o manifesto só **aponta** para os arquivos, e nada nele é aceito sem recomputação.

**A marca de um arquivo é o conteúdo, nunca a data.** Data não sobrevive a um `git checkout`,
a um clone nem a uma cópia — e um julgamento legítimo passaria a ser recusado por uma operação
de git que ninguém associaria a esta skill.

## 7 · Fronteiras e armadilhas

**Não é o motor de execução autônoma deste marketplace.** Aquele amarra a execução de um plano
já decidido; este produz trabalho criativo contra uma régua externa. Os dois laços são
igualmente determinísticos — o que muda é a pergunta: lá é *"o combinado saiu?"*, e essa
sempre dá sim. É a régua de conformidade, e é a causa da falha de origem.

**Não automatize o julgamento estético.** Toda medida tentada nas duas sessões que originaram
esta skill enganou pelo menos uma vez. Medida detecta regressão; não diz se está bom.

**Relatório longo não é qualidade.** Os melhores relatórios daquelas sessões acompanhavam
trabalho que um juiz teria reprovado — e responder "aceito" a um relatório bom *parece*
julgar, quando é só avaliar a argumentação.

**Uma ressalva de momento, declarada em vez de escondida:** o esquema de resposta do juiz
valida a forma do veredito, não a existência dos arquivos que ele cita. Juiz que preenche
caminho de registro inexistente passa na rodada, e só o fecho o pega.

**Três propostas de verdade só valem na primeira rodada**, e só em peça marcada como
exploratória. Nas rodadas de conserto o construtor responde a um defeito nomeado — explorar
ali é desperdício.

**Peça sem material que não existe:** asset que não existe não se inventa. Deixa-se um lugar
honesto para ele, e aquele pedaço sai do julgamento.
