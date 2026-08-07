# As sondas — como observar cada tipo de peça

A sonda é o que torna esta skill genérica sem torná-la vaga. Ela declara, na abertura,
**como observar** — e o método nunca mais fala em tipo de peça.

Este arquivo é **lista viva**: tipo novo é uma sonda nova escrita aqui e no rito da missão,
nunca uma emenda na skill. As receitas abaixo são ponto de partida, não catálogo fechado.

Toda sonda tem quatro campos, e o último é o que a prova:

```json
"sonda": {
  "preparar":  "o comando que põe a peça observável",
  "registrar": "o comando que produz o registro",
  "interagir": "os gestos que valem neste meio",
  "alvo":      "como observar o alvo pelo MESMO procedimento",
  "teste_registro": "o registro que ela produziu quando você a rodou uma vez"
}
```

**Sem `teste_registro` a missão não começa.** É o que faz "a sonda foi testada" ser fato, e
não promessa — o programa confere que o arquivo existe e não está vazio.

---

## Site ou aplicação que abre no navegador

```json
{
  "preparar":  "npx serve -l 4173 dist",
  "registrar": "npx playwright screenshot --viewport-size=1440,900 --full-page {url} {saida}",
  "interagir": "rolar até o fim · passar o mouse nos interativos · clicar · redimensionar para 390 e 1440",
  "alvo":      "a mesma captura, apontada para o endereço do alvo"
}
```

### As armadilhas deste meio — todas custaram tempo real

**O navegador é compartilhado.** Com vários agentes, a aba troca de dono no meio da leitura e
o número volta de outra página — aconteceu em três frentes numa rodada. A defesa é uma guarda
de origem dentro da própria leitura, que falha ruidosamente em vez de devolver número errado:

```js
if (!/o-dominio-esperado/.test(location.href)) return 'ABA ERRADA'
```

**O print mente, e a medição também.** Um teste numérico disse "zero sobreposição" enquanto
duas frases se empilhavam na tela; um navegador isolado mostrou texto vazando numa largura
que não existia. **Os dois, sempre** — e quando divergirem, o defeito está na ferramenta até
prova em contrário.

**Print de página inteira não serve com entrada por rolagem.** A captura não rola, as
entradas não disparam, e a página sai vazia. Dois alarmes falsos.

**Cortina de carregamento faz laboratório nascer invisível.** Uma regra que esconde tudo até
a página se declarar pronta produz layout perfeito e tinta zero — sintoma idêntico ao da aba
trocada, checagem oposta.

**Cache de folha de estilo.** Contornar o cache no endereço da página não invalida o da folha
ligada a ela; enganou quatro medições numa rodada. Sirva com cabeçalho que proíbe cache.

**Comentário mal fechado.** Quatro vezes. Em folha de estilo ele engole a regra seguinte sem
erro visível — uma vez matou a escala tipográfica inteira; em marcação, derrama na tela como
texto. Checagem barata: contar os abre contra os fecha.

**Transformações criam bloco de contenção.** Elemento fixo nasce com tamanho errado quando um
ancestral tem transformação — quatro defeitos que eram o mesmo.

**Endereço dentro de variável de estilo resolve contra quem consome**, não contra quem
declara. Fez acusar dezoito arquivos inexistentes que existiam.

---

## Aplicativo de desktop

```json
{
  "preparar":  "npm run tauri build && open ./target/release/bundle/macos/App.app",
  "registrar": "screencapture -l $(o id da janela) {saida}",
  "interagir": "percorrer o fluxo principal · redimensionar a janela · abrir o menu",
  "alvo":      "o mesmo, no aplicativo do alvo já instalado"
}
```

O registro é da **janela**, não da tela inteira: o resto da área de trabalho polui a
comparação e faz dois registros diferirem por motivo que não é a obra.

---

## Jogo

```json
{
  "preparar":  "o comando que sobe o jogo já numa fase determinística",
  "registrar": "a captura de N segundos de jogo, sempre do mesmo ponto de partida",
  "interagir": "jogar a fase 1 inteira · repetir a mesma sequência de comandos",
  "alvo":      "a captura equivalente do jogo de referência"
}
```

Aqui o registro é **movimento**, não quadro parado — e é onde eixos como resposta ao comando,
legibilidade do estado em movimento e retorno do acerto se expõem. O ponto de partida tem que
ser o mesmo nos dois, ou a comparação mede sorte.

---

## Documento, relatório, apresentação

```json
{
  "preparar":  "o comando que gera o arquivo final",
  "registrar": "a página N renderizada como imagem",
  "interagir": "abrir o sumário · procurar um dado específico e cronometrar",
  "alvo":      "a página equivalente do documento de referência"
}
```

Peça parada não tem gesto de interação obrigatório — o campo pode ficar vazio. O que a
substitui é o gesto de **busca**: procurar o mesmo dado nos dois expõe escaneabilidade melhor
do que olhar a página em repouso.

---

## Interface de linha de comando, ou serviço sem tela

```json
{
  "preparar":  "o comando que sobe o serviço",
  "registrar": "a saída crua do mesmo conjunto de entradas, gravada em arquivo",
  "interagir": "o roteiro fixo de entradas, na mesma ordem",
  "alvo":      "o mesmo roteiro, contra o serviço de referência"
}
```

O registro é **texto**, e vale igual: o par continua sendo par, e a régua continua sendo o
alvo. Eixos típicos aqui são clareza da mensagem de erro, tempo até a primeira resposta útil,
e o que o programa faz quando a entrada está errada.
