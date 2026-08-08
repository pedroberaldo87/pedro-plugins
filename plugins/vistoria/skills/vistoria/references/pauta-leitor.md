# Pauta do leitor — perguntas fechadas, prova colada

Um leitor recebe **um pedaço de leitura** (os arquivos de instrução de um plugin) e esta
pauta. Ele não opina: ele responde SIM ou NÃO a cada pergunta e, quando responde SIM, cola
o par de trechos literais com `arquivo:linha`. Achado sem o par é rejeitado pelo validador
(`lib/achado.py`) antes de chegar na página — não vira achado fraco, vira nada.

**Regra de forma da pauta.** Nenhuma pergunta usa verbo aberto — os proibidos são
*avalie*, *considere*, *analise a coerência*, *reflita*, *julgue*, *opine*. Verbo aberto
devolve ensaio; pergunta fechada devolve prova. Quem cobra isso é `lib/test_pauta.py`, que
lê este arquivo e reprova a pergunta que escorregar.

**Como responder.** Para cada pergunta: `P<n>: NAO` ou `P<n>: SIM` seguido do achado no
formato de `lib/achado.py` (campos `cobrador`, `regra`, `gravidade`, `onde`, `o_que`,
`prova`). O campo `prova` carrega os trechos colados, cada um com `arquivo:linha`.

---

### P1 · [a] A instrução manda algo que um programa deste repositório recusa?

Existe frase de instrução que ordena um comportamento que um hook, guard ou script deste
mesmo repositório bloqueia? Se SIM, **cole as duas**: a frase da instrução com
`arquivo:linha` e a linha do programa que a recusa com `arquivo:linha`.

### P2 · [a] Dois arquivos do mesmo plugin mandam o oposto sobre o mesmo objeto?

Existe objeto (arquivo, comando, diretório, campo) sobre o qual um arquivo manda fazer e
outro manda não fazer? Se SIM, **cole as duas** frases com `arquivo:linha`.

### P3 · [b] Algum gatilho declarado nunca casa a entrada real do harness?

Para cada `matcher`, padrão ou condição de disparo declarado: ele casa a entrada que o
harness entrega de verdade? Onde a resposta for NÃO, **cole as duas**: a linha do padrão
com `arquivo:linha` e a linha da entrada real (a amostra do evento) com `arquivo:linha`.

### P4 · [b] A instrução condiciona um passo a um texto que o harness nunca envia?

Existe passo cuja execução depende de uma string, campo ou variável que não aparece na
entrada real? Se SIM, **cole as duas**: a condição com `arquivo:linha` e a entrada real com
`arquivo:linha`.

### P5 · [c] A instrução promete um passo que não existe em lugar nenhum?

Existe promessa de comando, arquivo ou etapa que não tem correspondente no disco? Se SIM,
**cole as duas**: a promessa com `arquivo:linha` e o comando de busca que voltou vazio,
com a saída literal.

### P6 · [d] A instrução enumera casos e deixa algum sem tratamento?

Existe lista de estados, tipos ou situações em que algum item enumerado não recebe
tratamento no texto? Se SIM, **cole as duas**: a linha da enumeração com `arquivo:linha` e
a linha onde os tratamentos terminam com `arquivo:linha`, nomeando os itens que ficaram de
fora.

### P7 · [d] Alguma opção documentada (flag, argumento, modo) fica sem caminho escrito?

Para cada opção que a instrução documenta: existe passo que diga o que acontece quando ela
é usada? Onde a resposta for NÃO, **cole as duas**: a linha que documenta a opção e a linha
final da seção que deveria tratá-la, ambas com `arquivo:linha`.

### P8 · [e] Uma instrução depende de outra e não a cita pelo nome?

Existe passo que só funciona se outro plugin ou outra skill estiver presente, sem que o
texto cite esse outro nominalmente? Se SIM, **cole as duas**: a linha que depende com
`arquivo:linha` e a linha do arquivo dependido com `arquivo:linha`.

### P9 · [e] Um arquivo aponta para outro que mudou de nome ou de lugar?

Existe citação a caminho, comando ou símbolo que não resolve mais? Se SIM, **cole a linha**
da citação com `arquivo:linha` e a saída literal do comando que a procurou.

### P10 · [i] Alguma passagem repete o que outra já disse no mesmo pedaço?

Existe trecho cujo conteúdo já está escrito antes no mesmo pedaço de leitura? Se SIM,
**cole as duas** passagens com `arquivo:linha`, e informe a contagem de palavras do arquivo.

---

## O molde da ficha

Além dos achados, cada leitor devolve uma **ficha** do que leu — curta de propósito: é ela
que a lente cruzada consome, nunca os textos inteiros. A ficha é JSON com estes campos:

```json
{
  "pedaco": "<nome do plugin>",
  "arquivos": ["<arquivo:linhas>", "..."],
  "palavras": 0,
  "manda": ["<uma ordem por linha, no imperativo, ≤120 caracteres>"],
  "proibe": ["<uma proibição por linha, ≤120 caracteres>"],
  "objetos": ["<arquivo, diretório, comando ou evento que este pedaço toca>"],
  "eventos": ["<evento de hook em que este plugin registra algo>"],
  "depende_de": ["<outro plugin ou skill citado>"],
  "respostas": {"P1": "NAO", "P2": "SIM", "...": "..."}
}
```

Teto da ficha: **300 palavras por pedaço**. Ficha que passa disso está copiando o texto em
vez de resumi-lo, e derruba o ganho da lente cruzada.

## As fixtures — os arquivos de mentira congelados

Ficam em `plugins/vistoria/fixtures/<letra>/`, um diretório por letra do gabarito, com o
defeito plantado dentro. São **congelados**: ninguém conserta o defeito deles.

| Letra | Diretório | O defeito plantado | Pergunta que deve pegar |
|---|---|---|---|
| a | `fixtures/a/` | o `SKILL.md` manda esperar a suíte; o `guard.sh` ao lado recusa a espera | P1 |
| b | `fixtures/b/` | o `matcher` do `hooks.json` nunca casa a entrada real de `entrada-real.json` | P3 |
| d | `fixtures/d/` | o `SKILL.md` enumera os estados de um passo e trata só parte deles | P6 |
| f | `fixtures/f/` | duas instruções mandam o oposto sobre o mesmo arquivo de handoff; `ordem-de-registro.json` diz quem ganha | lente cruzada |

A fixture `f` não é da pauta do leitor: ela existe para a lente **cruzada**, que consome as
fichas de dois pedaços. O leitor sozinho vê um lado só — e é exatamente esse o ponto.
