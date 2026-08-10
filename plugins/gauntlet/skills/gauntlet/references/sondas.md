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

### O bloco de desempenho SÓ existe se o dono forneceu `metricas` neste desafio

**Por padrão a sonda não mede nada** — o stdout dela mostra o que interessa ao olho:
arquivo produzido, título da página, scrollY, altura, viewport. Medido em 2026-08-10:
a sonda imprimia fps, kB e LCP em toda rodada, e as tabelas mostradas ao dono eram cópia
desse stdout — o desafio subjetivo virou régua de 18 medidas sem ninguém decidir isso.
Número no stdout é empurrão para quem orquestra pensar e relatar em número.

O bloco abaixo entra **apenas** quando o rito traz `metricas` fornecidas pelo dono para
este desafio, e mede só o que elas nomeiam — pelo mesmo gesto, nos dois lados:

```
quadros por segundo   rolando uma distância FIXA num tempo FIXO (ex.: 2400px em 3s),
                      com o quadro mediano, o pior quadro e quantos passaram de 32ms
LCP + o elemento      não basta o número: guarde QUEM é o maior elemento pintado.
                      "LCP 2,3s numa <img>" e "LCP 2,3s no <h1>" são defeitos diferentes
CLS                   deslocamento de layout acumulado, ignorando o que veio de clique
tarefa mais longa     a maior longtask — é ela que engasga o dedo do usuário
kB e pedidos da rede  somando o que ATRAVESSOU o fio, não o tamanho descomprimido
nós de DOM            o tamanho da árvore que o navegador reflui a cada quadro
```

E ofereça um modo com o freio puxado (CPU 4× + rede lenta, por CDP:
`Emulation.setCPUThrottlingRate` e `Network.emulateNetworkConditions`). Sem ele, máquina de
desenvolvimento aprova qualquer coisa: página local não tem rede nem concorrência de CPU.

**Rode um CONTROLE antes de acreditar em quadro baixo.** Uma página estática de meia dúzia de
blocos tem que dar ~60 quadros por segundo na mesma sonda. Se der, o número baixo do alvo é
real; se não der, o defeito é da ferramenta — e a regra da casa é que a ferramenta é culpada
até prova em contrário.

**Peso em bytes não é o que trava.** Medido numa missão real: a Apple carregou 14.287kB e
3.749 nós de DOM rodando a 60,3 quadros por segundo, enquanto um site de 721kB rodava a 9,8.
O que trava é trabalho por quadro, não tamanho de download — e um eixo que confunde os dois
manda o construtor emagrecer a página errada.

### As armadilhas deste meio — todas custaram tempo real

**A página de bloqueio devolve número com cara de site.** O alvo pode recusar o robô e servir
um desafio ou um 403 — e a sonda registra os quadros e os bytes DAQUELA página, não do site.
Medido: `partizan.com` devolveu "NinjaFirewall 403 Forbidden" e a tabela quase ganhou uma linha
de 60 quadros por segundo e 6kB. Número de página de erro contaminando comparação é pior que
número nenhum: a sonda tem que **falhar alto** e não gravar nada.

```js
const status = resposta?.status() ?? 0
const titulo = await pagina.title()
if (status >= 400 || /403|forbidden|access denied|attention required|just a moment|firewall/i.test(titulo)) {
  console.error(`SONDA INVÁLIDA: ${url} respondeu ${status} — "${titulo}"`)
  process.exit(3)
}
```

**Medir dois sites ao mesmo tempo estraga os quadros dos dois.** A CPU é a mesma. A pesagem de
uma lista de alvos é sequencial, um de cada vez, ou a comparação mede concorrência.

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
