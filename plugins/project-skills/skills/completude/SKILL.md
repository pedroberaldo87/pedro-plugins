---
name: completude
description: Mede se o trabalho FECHA — a cadeia inteira de funcionalidade até a prova do tique, e os artigos da lei do projeto que nenhuma tarefa representa, com o que falta nomeado item a item. Não devolve porcentagem nem quase-lá, devolve o nome de cada elo que ficou aberto. Roda o programa, nunca o olho. Use quando o usuário disser "/completude", "o que falta pra fechar", "isso está completo?", "mede a completude", "faltou alguma coisa?", ou antes de declarar uma frente pronta.
---

# completude — o que falta para fechar, item a item

## O que é

Duas perguntas, uma medição só:

1. **A cadeia fecha?** Toda funcionalidade escrita virou requisito, todo requisito virou
   tarefa, toda tarefa marcada como feita tem prova.
2. **A lei foi representada?** Todo artigo da constituição do projeto tem tarefa que o
   carregue — e o artigo que a própria lei declara sem cobrador sai separado, porque ele
   não é furo nem verde: é o que o programa não sabe medir.

"Falta cobertura" sem dizer **em que ponto do fio** ela falta é o mesmo silêncio que a
medição existe para acabar. Aqui cada elo devolve o que falta NELE, com o identificador de
cada item.

## Como rodar

O motor é `lib/completude.py` do próprio plugin — nenhuma contagem sai do seu olho:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/completude.py" \
  <caminho>/features.md <caminho>/.claude/plans <caminho>/constituicao.md
```

Saída legível por padrão; `--json` devolve a estrutura inteira quando você precisa listar
os itens um a um. Sai com código 1 enquanto a cadeia não fecha — o código de saída é o
veredito, não a decoração.

Os três caminhos saem do `/doc-load`, nunca de cor: ele é quem diz qual documento vale como
régua neste projeto. **Documento que a medição não achou não vira verde** — sai nomeado em
`lacunas`, e sozinho já derruba o "completa".

## Como apresentar — os DOIS lados, sempre

Nunca só um. Mesmo quando um dos lados está limpo, ele aparece dizendo que está limpo:

**Lado 1 — a cadeia**, uma linha por elo (`feature → requisito`, `requisito → tarefa`,
`tarefa → prova`), verde ou vermelha, e abaixo da vermelha os itens que faltam **nomeados**:
a funcionalidade sem requisito pelo nome, o requisito sem tarefa pelo identificador, a
tarefa marcada sem prova pelo id.

**Lado 2 — a lei**: os artigos que nenhuma tarefa representa, cada um com número e título
(`6 · Estética`, não `6`). Logo abaixo, e visualmente separados, os artigos que a lei
declara sem cobrador — esses ficam **fora da conta**, marcados como dependentes de
julgamento. Esconder essa lista dentro do verde é fabricar o "cem por cento" que ela
desmente.

Regras da apresentação:

- **Item sem nome não conta.** "3 requisitos órfãos" sem os três identificadores é a mesma
  omissão que a medição veio consertar.
- **Nada de porcentagem.** Completude é binária por elo: ou o elo fecha, ou tem uma lista.
- **Não conserte nada aqui.** Esta skill mede e nomeia. Quem conserta é `/sprint`; quem
  revisa o construído é `/qa-loop`; quem replaneja é `/plan`.

## Fronteira — quando ela roda, e o que NÃO é dela

Roda **depois** que o construído fechou e **antes** de alguém dizer "pronto": é a última
pergunta da frente, não a primeira. O ângulo é a **cadeia de papel** — funcionalidade →
requisito → tarefa → prova —, medida por programa sobre documento, nunca sobre código.

- **Não é do `/qa-loop`.** Ele pergunta _"o código construído tem defeito?"_ — bug,
  regressão, lint/type/test. Ele lê código; esta medição lê documento. Elo aberto aqui não
  é defeito lá, e defeito lá não abre elo aqui.
- **Não é do revisor de construção (OPUS #2 do `/sprint`).** Ele pergunta _"a spec virou
  código inteiro e coerente?"_, contra a spec da missão, dentro da missão. Esta skill
  pergunta _"sobrou funcionalidade, requisito ou artigo sem ninguém?"_, no projeto inteiro,
  **fora** da missão — o buraco que nenhuma tarefa nomeou é justamente o que o #2 não tem
  como ver, porque ele julga a decomposição que existe.
- **Não conserta e não replaneja.** Ela mede e nomeia. Conserto é do `/sprint`, defeito é do
  `/qa-loop`, replanejamento é do `/plan`.

Resumo: **#2 = "está de pé, e é o que a spec pediu?" · qa-loop = "está certo?" ·
completude = "sobrou alguém de fora?"**.

## A régua que julga o que a medição achou

Os eixos de revisão **não são repetidos aqui** — eles moram em
`references/dimensoes-de-revisao.md` (fonte: `_shared/dimensoes-de-revisao.md` — não editar
a cópia à mão; `scripts/sync-shared.sh --check` pega drift), o mesmo contrato que `/plan`,
`/sprint` e `/qa-loop` leem. Duas cópias em prosa divergem, e foi exatamente isso que
aconteceu antes: uma skill listava seis dimensões, a outra cinco.

Leia aquele arquivo quando precisar julgar **se o que está marcado como feito realmente
fecha** — em especial o **Pé 2 (cobertura por finalidade)**, que é o pé de que esta
medição é a versão de programa. Esse pé aponta para os cinco antipadrões de teste, que
moram em `references/antipadroes-de-teste.md` (fonte: `_shared/antipadroes-de-teste.md`)
— também ao lado desta skill, para o apontamento não morrer na máquina instalada.

## Racionalizações — a desculpa refutada antes de você dá-la

A medição existe para desmentir o "cem por cento". As frases abaixo são as formas de
ressuscitá-lo, e todas já foram tentadas:

- **"a cadeia está verde, então não sobrou ninguém"** → verde mede o que alguém
  representou. Requisito que ninguém representou não aparece em teste nenhum.
- **"faltam dois, arredonda pra 100%"** → o número sai do programa. Arredondar é falsificar
  a medida, e o relatório mostra os DOIS lados justamente para impedir isso.
- **"esses órfãos são irrelevantes"** → órfão se nomeia pelo identificador. Relevância é
  decisão do dono, e ele só decide sobre o que enxerga.
- **"já que estou aqui, conserto o que achei"** → medir e consertar na mesma passada
  esconde o buraco. Conserto é do `/sprint`, defeito é do `/qa-loop`.
- **"contei de cabeça, dá no mesmo"** → sem `lib/completude.py` a contagem é opinião do
  modelo. O código de saída é o veredito.
