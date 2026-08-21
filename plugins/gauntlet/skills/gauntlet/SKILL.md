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
blind and say which one looks better."* (<https://somethingbig.ai/gauntlet-loop>). E o
dono: *"juízes que devem ficar incrivelmente impressionados (…) e conseguirem ENXERGAR
e avaliar o que está sendo feito."*

Quem cobra cada regra é programa — `lib/fecho_check.py` e a trava de
`hooks/pretooluse-gauntlet.sh`; a história medida de cada uma, `references/porque.md`.
**Você, que orquestra**: conduz a abertura, despacha, grava decomposição e vetos, repassa
ordens do dono em voo, fecha — **e não julga**: escreveu os briefings, está contaminado.

## 1 · A abertura

**Duas referências, dois papéis — nunca misture.** Definição do dono, canônica:
`moodboard` dirige ESTILO (referências positivas e negativas, por aspecto do que se vai
fazer); `alvos` são os DESAFIADOS — referência da PERCEPÇÃO do público sobre qualidade e
relevância, e a pergunta contra eles é uma só e subjetiva: *"a nossa é mais foda?"*. O
desafiado nunca é literal (numérico), nunca é referência a seguir ou copiar, e nunca vira
régua tipo "ele faz 30fps, façamos mais". O gauntlet é *"vamos fazer um site MAIS FODA
que a Apple"* — **com toda a subjetividade que isso carrega**; é por isso que o prompt
original é curtinho.

Grave `.claude/gauntlet/<data>-<slug>/rito.json` com **cinco campos**: `objetivo` (do
dono) · `alvos` (os desafiados — URLs concretas, você sugere e ele aprova) · `sonda`
(você propõe pelo tipo de peça, receitas em `references/sondas.md`; testada antes,
`teste_registro` no disco) · `eixos` (o recon propõe, ele aprova) · `orcamento`
(`rodadas_por_peca`, `teto_de_pecas`). Opcionais: `lei` · `vetos` · `raiz` · `intencao`
· `criativo` · `moodboard` (as referências de estilo, positivas e negativas, por
aspecto) · `metricas` (SÓ o que o dono fornecer NESTE desafio, verbatim — é a única
porta por onde número entra em julgamento; sem o campo, o critério é impressionar, e o
fecho recusa veredito que julgue por medida).

**Descoberta** — dono sem alvos ou sem direção registrada: conduza antes do rito.
(1) **intenção** — o que é a obra, para quem, que sensação; respostas dele verbatim em
`intencao`; (2) **moodboard** — referências dele mais candidatas suas, cada uma ABERTA no
browser, nunca por adjetivo; o aprovado é vibe, não forma, e vai em `moodboard`;
(3) **desafiados** — *"quem a gente quer BATER?"*: esses viram `alvos`, o resto vai ao
arsenal. Com tudo pronto, pula-se.

**Lei** — antes de perguntar, rode a doc-load do projeto da obra
(`resolve-plugin.sh project-skills lib/doc_load.py`); documento-régua entra em `lei`, e
o programa ancora e reconfere sozinho. Sem lei, só o alvo manda.

**Arsenal** — `~/.claude/gauntlet/arsenal.md` + o do projeto; ofereça a seção do tipo
da missão. O aceito entra no rito e nos briefings de construtor e recon; o juiz nunca o
recebe; a entrega declara `arsenal_usado`. **Quatro naturezas, e as duas últimas mordem:**
biblioteca se USA · referência visual é vibe · **gerador PRODUZ asset que entra na obra**
· **método (skill de agente) muda como o construtor trabalha**.

Recurso generativo no rito ⇒ o briefing do construtor leva junto o que ele pode criar
(símbolo, textura, fundo, cena autoral) e o que não pode gerar nunca (o que se passaria
por registro do que não aconteceu: foto de cliente, de equipe, de lugar, de prêmio, rosto
ou marca de terceiro). O que falta de verdade ganha lugar honesto e sai do julgamento.
`arsenal_usado` nomeia o modelo, não só a ferramenta — é o que dá ao dono o que vetar.

⚠️ **Método que EXTRAI identidade de uma referência é uma máquina de copiar, e a disputa
proíbe copiar.** Antes de aceitar um desses no arsenal, diga ao dono para onde ele pode
apontar: o nosso próprio material e o moodboard aprovado, nunca o ALVO — apontá-lo ao
alvo industrializa a violação central (`RÉGUA, NUNCA RECEITA`), e o que ele devolve é
especificação medida, que desde a 0.10.0 só julga se o dono forneceu `metricas`. Vale a
régua de sempre, e ela não muda por vir de ferramenta: nível e vibe se transportam, forma
não. Cópia só com ordem explícita do dono, escrita no rito.

**Gasto — DUAS perguntas ao dono, em TODA abertura, sem herdar resposta.** Aconteceu
(2026-08-11): uma disputa com gerador no arsenal queimou 1.183 créditos em dois dias e
derreteu a assinatura dele. *"Toda vez que iniciar um gauntlet, perguntar de novo, por
via das dúvidas"* — resposta de missão anterior, no mesmo projeto, NÃO vale.

1. **Quanto pode gastar** — dois números, não um: `imagem` e `video` separados. Um vídeo
   custa o que quinze imagens, então teto único morre em três vídeos sem gerar imagem.
2. **Quais provedores** valem nesta disputa. Lista vazia é resposta ("nenhum"); campo
   ausente é silêncio, e o programa recusa a abertura.

As duas respostas dele entram no **rito**, em `gasto` — e é de lá que o `--abre` tira o
teto, sem número digitado de novo: o briefing do construtor interpola esse mesmo campo, e
teto digitado à parte fazia o construtor ler um número e o programa cobrar outro.

```json
"gasto": {"modo": "real", "provedores": ["higgsfield"],
          "teto": {"imagem": 120, "video": 90}}
```

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/fecho_check.py" gasto "<a missão>" --abre
python3 "${CLAUDE_PLUGIN_ROOT}/lib/fecho_check.py" gasto "<a missão>"   # afere
```

A aferição **sai 1 em dois casos, e os dois mandam parar de gerar**: teto estourado, e
provedor que não respondeu. Silêncio não é permissão — quem gasta com o saldo ilegível
gasta às cegas. Sai 0 só quando o teto foi lido e ainda há folga.

Abrir duas vezes é recusado: reabrir apaga o consumido e faz o teto recomeçar do zero com
o dinheiro já gasto. Recomeçar de propósito é `--reabre`, dito em voz alta.

O `--abre` lê o saldo do provedor e o congela; a aferição de cada rodada lê de novo, e
**o consumido é a diferença de saldo, nunca a soma das estimativas** — a conta tem
estorno. Rode a aferição a cada rodada: ela avisa na metade e em 80%, e o mapa passa a
mostrar o custo por tipo. **Teto atingido DESLIGA a geração e a disputa continua** com
espaço reservado no lugar do asset — nunca para a missão. `--ensaio` roda tudo sem gerar
nada, e é o que se usa para ver composição antes de gastar. O campo `gasto` é exigido no
rito sempre que houver `arsenal`: é assim que a pergunta deixa de depender da sua memória.

**Diretor criativo** — missão estética: ofereça por `AskUserQuestion` ANTES de qualquer
despacho e espere. `criativo: true/false` no rito decide dali em diante; `false` vale a
missão inteira. O papel é de nascença ou não é.

Carimbo: `python3 "${CLAUDE_PLUGIN_ROOT}/lib/fecho_check.py" rito "<a missão>" --sinal "<o sinal>"`

## 2 · O sinal

```bash
GDIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/andamento"; mkdir -p "$GDIR"
printf 'gauntlet\n%s\n' "<caminho absoluto da missão>" > "$GDIR/ativo-$CLAUDE_CODE_SESSION_ID"
```

A linha 2 é onde a trava procura pendência. Quem apaga é o fecho verde (`--sinal`) ou o
`encerra`; expira por idade, e a trava desiste AVISANDO após negações seguidas. Kill-switch:
`GAUNTLET_GATE=0`. A missão sobrevive ao `/clear`: o hook de arranque imprime o mapa e pergunta.

## 3 · A equipe e o laço

Todo agente nasce pela tool `Agent`, com `name` e o marcador no prompt. Os esqueletos
estão em **`references/briefings.md`** — é LÁ que a ambição mora; interpole os valores
da missão e não a dilua.

```
recon → [gauntlet:recon]                decompositor → [gauntlet:decompositor]
construtor-X → [gauntlet:construtor:X]  juiz-X → [gauntlet:juiz:X]
diretor → [gauntlet:diretor]            criativo (opcional) → [gauntlet:criativo]
```

1. **Decomposição** — corta-se o TRABALHO em peças julgáveis; **a barra não se corta**: todo
   juiz confronta obra inteira com alvo inteiro. Grave `decomposicao.json`, mostre, siga.
2. **Fanout** — um construtor por peça; rodada 1 exploratória são três propostas de verdade.
   O criativo (se `true`) nasce junto, palpita por arquivo, **nunca fala com juiz**.
3. **Juiz disparado pela entrega** — com entrega sem veredito, a trava nega qualquer despacho
   que não seja o juiz dela. Aprovar É declarar impressão (`impressionado` + `frase`).
4. **Reprovou** → o construtor seguinte responde ao gap. **Ganho pequeno (`marginal`)** →
   proibido refinar: caminho novo; o fecho recusa peça marginal com rodada sobrando.
5. **Fecha peça**: juiz boquiaberto · ordem do dono · orçamento esgotado (parar a missão
   inteira é o `encerra`). No fim o **diretor** julga o conjunto — e também só aprova
   boquiaberto: `impressionado` + frase, cobrados pelo fecho.

O placar de cada rodada é `fecho_check.py mapa "<a missão>"` virando página `/visual` —
relato de parada nunca é textão no terminal. **Visual ausente na máquina**: o mapa do
`fecho_check.py` sai literal num arquivo em `.claude/reports/`, com o aviso de que a página não abriu. A obra abre no browser do dono desde a primeira
versão (`open <url>`); os juízes observam pela MESMA sonda, nunca por relatório de construtor.

## 4 · O dono em voo

Veto é registrado por programa: `fecho_check.py veto "<a missão>" --o-que "…"
--pecas "…"`. Ordem dele chega na hora aos agentes vivos por `SendMessage` e entra nos
briefings das rodadas seguintes. Veto que toca peça fechada: pergunte antes de reabrir.

## 5 · O fecho

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/fecho_check.py" fecho "<a missão>" --sinal "<o sinal>"
```

Verde apaga o sinal; vermelho imprime o que falta. O que ele confere mora na suíte
(`lib/test_fecho_check.py`), não em prosa.

## 6 · As armadilhas — cada uma já mordeu de verdade

- **Copiar o alvo.** O desafiado é percepção a bater, nunca fonte de especificação: eixo diz ONDE olhar e o print prova; forma não se transporta — nem do alvo, nem do moodboard, nem do já aprovado.
- **Fatiar a barra junto com o trabalho.** Peça recorta trabalho; a comparação é sempre obra inteira contra alvo inteiro.
- **Medir no lugar de olhar.** Medida serve a diagnóstico e regressão, nunca a julgamento; o juiz decide com o olho, às cegas — número só julga se o dono forneceu `metricas` neste desafio.
- **Converter sensação do dono em meta numérica.** "Ficou pesado" não vira gate de fps nem tabela — vira direção de trabalho e volta a ele como TELA, nunca como número; relatar a missão ao dono em métrica é a mesma armadilha, do lado de quem orquestra.
- **Julgar o relatório em vez da obra.** Argumentação convence sem qualidade; o juízo se forma antes de ler qualquer relatório.
- **Fechar por cansaço.** Ganho pequeno não fecha peça — fecha juiz boquiaberto, ordem do dono ou orçamento; o programa recusa o resto.
- **Falsificar asset.** Símbolo se cria; o que se passaria por registro do que não aconteceu, nunca — asset real que falta sai do julgamento.

Tipo novo de peça é sonda nova em `references/sondas.md`, nunca emenda nesta skill.
