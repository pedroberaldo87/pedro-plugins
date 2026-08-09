# Pauta da lente cruzada — o defeito que só aparece com dois pedaços juntos

O leitor lê **um** pedaço e vê um lado só. A lente cruzada é outro agente, e ela não lê
texto nenhum: ela recebe as **fichas** dos leitores (o molde está em `pauta-leitor.md`,
seção *O molde da ficha* — `manda`, `proibe`, `objetos`, `eventos`, teto de 300 palavras
por pedaço) e cruza uma contra a outra.

**O que a lente recebe.** Só duas coisas:

1. as fichas dos pedaços, uma por plugin;
2. quando a resposta é SIM, as **linhas citadas** em `arquivos` da ficha — abertas do disco
   naquele momento, para colar a prova literal. Nunca o texto inteiro do pedaço.

Ler os textos inteiros derrubaria o passo: são dezenas de milhares de palavras contra
alguns milhares de fichas. O teto dessa soma é declarado por programa em
`lib/test_pauta.py`, e a suíte reprova a ficha que estourar.

**A correspondência evento → pedaços sai do campo `eventos` da ficha** — e, quando ela
precisa ser conferida contra o disco, de `lib/inventario.py` (`tabela_de_hooks`), que lê os
`hooks.json` de verdade. O que segue congelado por decisão do dono é o **leitor por agente**:
esta pauta não lê o texto dos pedaços. Onde a ordem entre dois registros importa, ela vale
DENTRO de um mesmo `hooks.json` (ordem de registro); entre plugins diferentes o inventário
sai rotulado `ordem_entre_plugins: "nao-medida"`, e afirmar quem bloqueia primeiro a partir
dele é achado inválido.

**Regra de forma.** Igual à do leitor: nenhuma pergunta usa verbo aberto (*avalie*,
*considere*, *analise*, *reflita*, *julgue*, *opine*), e toda pergunta exige o **par** de
citações literais com `arquivo:linha`. Achado sem o par é rejeitado por `lib/achado.py`
antes de chegar na página. Quem cobra a forma é `lib/test_pauta.py`.

**Como responder.** Para cada pergunta: `X<n>: NAO`, ou `X<n>: SIM` seguido do achado no
formato de `lib/achado.py` (`cobrador`, `regra`, `gravidade`, `onde`, `o_que`, `prova`),
com `cobrador: "cruzamento"`. O achado cruzado vai depois para o verificador
(`pauta-verificador.md`), que tenta derrubá-lo como qualquer outro.

---

### X1 · [f] Duas fichas mandam o oposto sobre o mesmo objeto?

Existe objeto que aparece em `objetos` das duas fichas, com uma entrada de `manda` numa e
uma entrada de `proibe` na outra? Se SIM, **cole as duas**: a linha da ordem com
`arquivo:linha` e a linha da proibição com `arquivo:linha`.

### X2 · [f] Dois pedaços registram no mesmo evento e agem sobre o mesmo objeto?

Existe evento que aparece em `eventos` das duas fichas, com o mesmo objeto em `objetos` das
duas? Se SIM, **cole as duas** linhas de registro no evento, cada uma com `arquivo:linha`,
na ordem em que o arquivo de ordem de registro as lista — e nomeie qual delas roda por
último.

### X3 · [f] Um pedaço proíbe o objeto de que outro declara depender?

Existe item de `depende_de` de uma ficha cujo objeto aparece em `proibe` da outra? Se SIM,
**cole as duas**: a linha da dependência com `arquivo:linha` e a linha da proibição com
`arquivo:linha`.

### X4 · [f] Duas fichas respondem o oposto sobre o mesmo objeto na mesma pergunta?

Existe pergunta do leitor (`respostas`) em que uma ficha responde SIM e a outra NAO, com o
mesmo objeto em `objetos` das duas? Se SIM, **cole as duas** linhas que sustentam cada
resposta, com `arquivo:linha`.

---

## As fichas congeladas da fixture `f`

A fixture `plugins/vistoria/fixtures/f/` é a rodada de referência da lente: `skill-um.md`
manda apagar o arquivo de handoff, `skill-dois.md` manda preservá-lo, e
`ordem-de-registro.json` diz quem roda por último no evento `Stop`. Estas são as duas
fichas que os leitores devolveriam — são elas que `lib/test_pauta.py` lê do disco, mede com
`wc -w` e cruza:

```json
{
  "pedaco": "exemplo-f-um",
  "arquivos": ["fixtures/f/skill-um.md:1-12", "fixtures/f/ordem-de-registro.json:3-6"],
  "palavras": 62,
  "manda": ["apague .claude/HANDOFF.md no fim do turno"],
  "proibe": ["deixar rascunho de turno fechado para trás"],
  "objetos": [".claude/HANDOFF.md"],
  "eventos": ["Stop"],
  "depende_de": [],
  "respostas": {"P1": "NAO", "P2": "NAO"}
}
```

```json
{
  "pedaco": "exemplo-f-dois",
  "arquivos": ["fixtures/f/skill-dois.md:1-12", "fixtures/f/ordem-de-registro.json:3-6"],
  "palavras": 64,
  "manda": ["preserve .claude/HANDOFF.md intacto no fim do turno"],
  "proibe": ["apagar .claude/HANDOFF.md no fim do turno"],
  "objetos": [".claude/HANDOFF.md"],
  "eventos": ["Stop"],
  "depende_de": [],
  "respostas": {"P1": "NAO", "P2": "NAO"}
}
```

Cruzadas, elas respondem `X1: SIM` e `X2: SIM` sobre `.claude/HANDOFF.md`, e o achado sai
com as duas linhas de instrução e as **duas linhas do evento `Stop`** coladas, mais a
ordem de registro que decide quem ganha. Nenhum dos textos inteiros entra na lente.
