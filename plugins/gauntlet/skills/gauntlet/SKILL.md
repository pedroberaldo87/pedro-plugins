---
name: gauntlet
description: Use quando o usuário quiser que agentes disputem contra um produto real que ele nomeia — site, jogo, tela de aplicativo, relatório, qualquer coisa que se possa construir, iterar e julgar. Dispara em "/gauntlet", "roda o gauntlet", "quero bater o site X", "isso tem que ganhar do Y", "monta um laço de crítica contra um benchmark". Quando o usuário chega sem alvos ou sem direção registrada, a abertura conduz uma descoberta curta com ele — intenção, moodboard, benchmarks — em vez de recusar e devolver o problema. O objetivo quebra em peças julgáveis, cada peça ganha um construtor e um juiz cego separado, e o juiz só aprova quando fica BOQUIABERTO diante do alvo inteiro — nunca o que apenas cumpre o pedido, e ganho pequeno não fecha nada: força caminho novo. A disputa roda como EQUIPE VISÍVEL na conversa - o dono vê cada agente, dirige em voo, veta e para; nada roda em caixa fechada. Nada do que foi construído se julga sozinho, e quem orquestra também não julga. Cada veredito é um arquivo em disco com o par de observações que o prova; uma trava de PreToolUse impede despacho novo enquanto houver entrega sem juiz; e o fecho é recusado por programa quando falta algum. Nasceu de uma falha real - sete construtores foram lançados prometendo um juiz em cada briefing, zero juízes foram lançados, e ninguém percebeu.
---

# Skill: /gauntlet

**A barra: iterar até um juiz que não construiu nada olhar a obra INTEIRA ao lado do
alvo INTEIRO e ficar BOQUIABERTO.** Não "cumprir o pedido", não "melhorar bastante",
não "bater o número" — impressionar. A resposta do juiz nasce "não", e só três coisas
fecham uma peça: ele declarar-se impressionado, o dono mandar parar, ou o orçamento
acabar. Ganho pequeno não encerra nada: ele manda propor um caminho NOVO.

A fonte, verbatim: *"Don't stop until each sub-agent is utterly wowed with the quality
when compared with the actual [target]. It should literally compare them side by side
blind and say which one looks better."* — Matt Shumer,
<https://somethingbig.ai/gauntlet-loop>. E o dono: *"juízes que devem ficar
incrivelmente impressionados (…) e conseguirem ENXERGAR e avaliar o que está sendo
feito."*

Quem cobra cada regra é programa — `lib/fecho_check.py` e a trava de
`hooks/pretooluse-gauntlet.sh`; a história medida de cada uma, `references/porque.md`.
**Você, que orquestra**: conduz a abertura, despacha e nomeia, grava decomposição e
vetos, repassa ordens do dono em voo, fecha quando a conferência passa — **e não
julga**: você escreveu os briefings, está contaminado.

## 1 · A abertura

Grave `.claude/gauntlet/<data>-<slug>/rito.json` com **cinco campos**:
`objetivo` (do dono) · `alvos` (dele — URLs concretas, você sugere e ele aprova) ·
`sonda` (você propõe pelo tipo de peça, receitas em `references/sondas.md`; testada
antes, com `teste_registro` no disco) · `eixos` (o recon propõe, ele aprova) ·
`orcamento` (`rodadas_por_peca`, `teto_de_pecas`). Opcionais: `lei` · `vetos` · `raiz`
· `intencao` · `criativo`.

**Descoberta** — dono sem alvos ou sem direção registrada: conduza antes do rito.
(1) **intenção** — o que é a obra, para quem, que sensação; respostas dele verbatim em
`intencao`; (2) **moodboard** — referências dele mais candidatas suas, cada uma ABERTA
no browser, nunca descrita por adjetivo; o aprovado é vibe, não forma; (3)
**benchmarks** — *"quem a gente quer BATER?"*: régua vira `alvos`, o resto vai ao
arsenal. Dono com tudo pronto pula a descoberta inteira.

**Lei** — antes de perguntar, rode a doc-load do projeto da obra
(`resolve-plugin.sh project-skills lib/doc_load.py`); documento-régua entra em `lei`, e
o programa ancora e reconfere sozinho. Sem lei, só o alvo manda.

**Arsenal** — `~/.claude/gauntlet/arsenal.md` + o do projeto; ofereça a seção do tipo
da missão. O aceito entra no rito e nos briefings de construtor e recon; biblioteca se
USA, referência visual é vibe; o juiz nunca o recebe; a entrega declara `arsenal_usado`.

**Diretor criativo** — missão estética: ofereça por `AskUserQuestion` ANTES de qualquer
despacho e espere. `criativo: true/false` no rito decide dali em diante; `false` vale a
missão inteira. O papel é de nascença ou não é.

A abertura só vale carimbada:
`python3 "${CLAUDE_PLUGIN_ROOT}/lib/fecho_check.py" rito "<a missão>" --sinal "<o sinal>"`

## 2 · O sinal

```bash
GDIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/andamento"; mkdir -p "$GDIR"
printf 'gauntlet\n%s\n' "<caminho absoluto da missão>" > "$GDIR/ativo-$CLAUDE_CODE_SESSION_ID"
```

A linha 2 é onde a trava procura pendência. Quem apaga é o fecho verde (`--sinal`) ou o
`encerra`; ele expira por idade, e a trava desiste AVISANDO após negações seguidas.
Kill-switch: `GAUNTLET_GATE=0`. A missão sobrevive ao `/clear`: o hook de arranque
imprime o mapa e pergunta ao dono se retoma.

## 3 · A equipe e o laço

Todo agente nasce pela tool `Agent`, com `name` e o marcador no prompt. Os esqueletos
estão em **`references/briefings.md`** — é LÁ que a ambição mora; interpole os valores
da missão e não a dilua.

| papel | `name` | marcador |
|---|---|---|
| reconhecimento | `recon` | `[gauntlet:recon]` |
| decompositor | `decompositor` | `[gauntlet:decompositor]` |
| construtor da peça X | `construtor-X` | `[gauntlet:construtor:X]` |
| juiz da peça X | `juiz-X` | `[gauntlet:juiz:X]` |
| diretor | `diretor` | `[gauntlet:diretor]` |
| diretor criativo (opcional) | `criativo` | `[gauntlet:criativo]` |

1. **Decomposição** — o decompositor corta o TRABALHO em peças julgáveis; **a barra não
   se corta**: todo juiz confronta a obra inteira com o alvo inteiro, e os eixos da
   peça são lente de atenção. Grave `decomposicao.json`, mostre a lista, siga.
2. **Fanout** — um construtor por peça, em paralelo; rodada 1 de peça exploratória são
   três propostas de verdade, escolhidas pelo olho. O criativo (se `true`) nasce junto,
   palpita por arquivo (`criativo/palpites-r<N>.md`) e **nunca fala com juiz**.
3. **Juiz disparado pela entrega** — com entrega sem veredito no disco, a trava nega
   qualquer despacho que não seja o juiz dela. O veredito exige `impressionado` e a
   `frase` de gente; aprovar É declarar impressão.
4. **Reprovou** → o construtor seguinte responde ao gap nomeado. **Ganho pequeno
   (`marginal`)** → o construtor seguinte é proibido de refinar: caminho novo. O fecho
   recusa peça marginal com rodada sobrando.
5. **Fecha peça**: juiz boquiaberto · dono mandando parar (`encerra`) · orçamento
   esgotado. No fim, o **diretor** julga o conjunto — o defeito ENTRE peças é invisível
   aos juízes de peça.

O placar de cada rodada é `fecho_check.py mapa "<a missão>"` virando página `/visual` —
relato de parada nunca é textão no terminal.

## 4 · A obra ao vivo

Abra a obra no browser do dono desde a primeira versão (`open <url>`). Os juízes
observam pela MESMA sonda que todos — nunca pelo relatório de quem construiu.

## 5 · O dono em voo

Veto é registrado por programa: `fecho_check.py veto "<a missão>" --o-que "…"
--pecas "…"`. Ordem dele chega na hora aos agentes vivos por `SendMessage` e entra nos
briefings das rodadas seguintes. Veto que toca peça fechada: pergunte antes de reabrir.

## 6 · O fecho

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/fecho_check.py" fecho "<a missão>" --sinal "<o sinal>"
```

Verde apaga o sinal; vermelho imprime o que falta. O que ele confere mora na suíte
(`lib/test_fecho_check.py`), não em prosa.

## 7 · As armadilhas — cada uma já mordeu de verdade

- **Copiar o alvo.** Régua, nunca receita: o número do eixo prova o nível, e forma não
  se transporta — nem do alvo, nem do moodboard, nem do que já foi aprovado.
- **Fatiar a barra junto com o trabalho.** Peça é recorte de trabalho; a comparação é
  sempre obra inteira contra alvo inteiro.
- **Medir no lugar de olhar.** Medida detecta regressão; não diz se está bom. O juiz
  decide com o olho, às cegas.
- **Julgar o relatório em vez da obra.** Relatório bem argumentado convence sem
  qualidade; o juiz forma o juízo antes de ler qualquer relatório.
- **Fechar por cansaço.** Ganho pequeno não fecha peça — fecha juiz boquiaberto, dono
  ou orçamento, e o programa recusa o resto.
- **Falsificar asset.** Símbolo e textura se criam; o que se passaria por foto ou
  registro do que não aconteceu, nunca — asset real que falta ganha lugar honesto e sai
  do julgamento.

Tipo novo de peça é sonda nova em `references/sondas.md`, nunca emenda nesta skill. As
histórias por trás de cada regra: `references/porque.md`.
