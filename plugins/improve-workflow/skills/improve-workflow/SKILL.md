---
name: improve-workflow
description: Autópsia de um run multi-agente que já terminou — lê o transcript inteiro, mede o que cada PAPEL custou (agentes, turnos, tokens, taxa de falha), acende os sinais de defeito por contagem e entrega um parecer com propostas para o dono aprovar. Ela INVESTIGA e PROPÕE, e é proibida de consertar o que achou. Use quando o usuário disser "/improve-workflow", "autópsia do run", "quanto custou essa missão", "por que essa rodada foi tão cara", ou ao fim de uma missão multi-agente. NÃO use para implementar melhoria pedida em tarefa — isso é da skill improve, a vizinha.
---

# Skill: improve-workflow — a autópsia investiga e propõe, e nunca conserta

Quem escreve a sentença não executa a sentença. Uma autópsia que sai consertando
perde a neutralidade na primeira rodada: ela passa a auditar código que ela mesma
escreveu, e o defeito que ela plantou é o único que ela nunca vai acusar.

## A PROIBIÇÃO (não é preferência, é a lei desta skill)

**Nenhum arquivo do projeto muda durante a apuração — só o passo 8 grava, e só o
aprovado.** Nem criado, nem editado, nem apagado, nem renomeado, nem movido. Isso vale
para código, doc, config e para o próprio texto desta skill; o plano do passo 8 é a
única exceção, declarada logo abaixo.

Concretamente, dentro de uma rodada de autópsia estão PROIBIDOS:

- as ferramentas de escrita (Edit, Write, NotebookEdit) sobre qualquer caminho do projeto;
- `git commit`, `git add`, `git checkout`, `git stash`, `git worktree remove` e qualquer
  comando que mexa na árvore ou no índice;
- redirecionar saída (`>`, `>>`, `tee`) para dentro da raiz do projeto;
- apagar a sobra que a varredura acusou — ela é ACHADO, não tarefa.

Durante a apuração (passos 1 a 7) a ÚNICA pasta em que esta skill escreve é
`~/.claude/improve-workflow/`, fora do projeto exatamente por causa desta lei: o registro
acumulado em `registro.jsonl` (`lib/registro.py`) e a página de parecer do passo 7.
Dentro do projeto, nada.

**A ÚNICA EXCEÇÃO, e ela tem hora marcada:** o passo 8 grava no projeto o plano com o
que o dono APROVOU (`.claude/plans/`). Motivo: a proposta só vira trabalho se virar
passo ticável, e o plano pertence ao projeto auditado, não ao lar de quem auditou. A
exceção vale DEPOIS do veredito e só sobre ele — antes do dono julgar, nada é escrito,
e o que ele descartou nunca é escrito.

Se o que você quer é aplicar um conserto proposto aqui: a proposta vira passo de plano
e o conserto é feito por outra rodada, com outro dono. Não por esta skill.

## A rodada

Os passos 1 a 7 são leitura; só o passo 8 escreve, e só o que o dono aprovou. Rode a
partir da raiz do projeto.

**1 · Medir.** O programa faz a conta; você não estima nada.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/medidor.py"            # o run mais recente
python3 "${CLAUDE_PLUGIN_ROOT}/lib/medidor.py" <run>      # um run nomeado
```

Sem run no disco ele diz isso e para — **avisando, e saindo ZERO**: num projeto
que nunca rodou missão não há defeito nenhum a acusar, só medição que não houve.
Run PEDIDO pelo nome e inexistente é outra coisa: aí é uso errado, e sai 2. A tabela sai por PAPEL — agentes, turnos,
turnos por agente, taxa de falha, cache_read, output — mais os seis sinais e, em
cada linha, o **trecho a abrir** (`agent-<id>.jsonl:<linha>`).

**Quem entra sozinho é só o passo 1.** O medidor roda ao fim de **toda** missão do `sovai`
(passo 5 da Persistência dele), em bash e sem agente. Os passos 2–6 são leitura cara, feita
por agente: eles só acontecem com **sinal aceso** na saída do medidor, ou porque o usuário
pediu a autópsia. `sinais — 0 dos 6 acesos` e ninguém pedindo ⇒ a rodada termina no passo 1,
e agente nenhum é disparado.

**2 · Ler o que o medidor apontou.** Abra SÓ os trechos que ele endereçou, começando
pelo agente mais caro do papel suspeito. O medidor entrega ponteiro, não conteúdo:
carregar o transcript inteiro é o gasto que esta skill existe para acusar.

**3 · Varrer a sobra do run.** Reserva de arquivos que ficou presa, e só a DESTE run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/sobras.py" --json          # o run mais recente
python3 "${CLAUDE_PLUGIN_ROOT}/lib/sobras.py" --run <run> --json
```

Processo de pé, árvore de trabalho parada e higiene de máquina não são daqui —
são de `/faxina`, `/branches` e `/fallow`. Sobra de outro run também não é desta
autópsia. Acusar é o serviço completo: quem limpa é o dono, depois de aprovar.

**4 · Registrar, com o que foi consertado desde a última rodada.** Fora do projeto, para
a rodada seguinte ter com o que comparar. Um `--conserto` por conserto que alguém aplicou
entre a rodada anterior e esta — `PAPEL:metrica:o que foi feito`, e a métrica é uma de
`turnos_por_agente`, `taxa_falha`, `turnos`, `agentes`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/registro.py" gravar <run> \
  --conserto "EXECUTOR:turnos_por_agente:teto de 1 turno por executor"
```

A saída traz `contra_a_anterior.consertos`: cada conserto nomeado, o número que ele
mirava nos dois lados, e o veredito (`melhorou`, `piorou`, `igual`, `sem_medida`).
Nenhum conserto anotado ⇒ a lista sai vazia, e a resposta honesta é "não dá para saber".

**A retenção: ficam as 50 rodadas mais novas.** Toda gravação apaga do arquivo o que
passar disso — a comparação usa a rodada anterior, e histórico velho não responde
pergunta nenhuma enquanto o arquivo cresceria para sempre. Quem aplica é o próprio
`registro.py` (`RETENCAO`), não o agente: não há passo manual de limpeza aqui.

**5 · Parecer.** Abra dizendo se o conserto da rodada passada funcionou — nome do
conserto, o número dos dois lados, o veredito do programa. Depois, cada afirmação
carrega a prova colada — o número cru do medidor e a
linha do transcript de onde ele veio. Sinal aceso é hipótese endereçada, não causa
declarada: rotule CONFIRMADO (você abriu o trecho e viu) ou INFERIDO (só a contagem).

**6 · Refutar, com um segundo par de olhos.** A autópsia tem DOIS agentes: o que
apurou os passos 1–5 e um segundo, que só existe para derrubar o primeiro. Abra o
segundo com um subagente e entregue a ele a saída crua do medidor, do `sobras.py` e do
`registro.py` mais a lista de afirmações — **nunca a narrativa de quem apurou**, que é
justamente o que se quer testar. O texto de quem refuta é este, fixo, e vai palavra por
palavra (redigitar por rodada é como ele desaparece):

**A ordem de derrubar** — tente derrubar cada afirmação: aponte o número que a
contradiz, a leitura alternativa que explica o mesmo dado, ou diga que ela se sustenta.
Afirmação rotulada CONFIRMADO sem trecho de transcript aberto volta para INFERIDO.

**A trava de robustez** — reprove toda proposta que troque robustez por economia:
menos verificação, menos teste, menos retentativa, menos prova em troca de turno,
token ou tempo. Barato que quebra não é conserto.

O que não sobreviver ao segundo agente não entra no parecer.

**7 · Propor.** Uma proposta por defeito, cada uma com o número que ela mira e como
esse número será conferido na rodada seguinte. A proposta não sai em prosa no chat:
ela chega pela superfície de aprovação do `/visual`, com **um item por proposta** —
um veredito por defeito, e não um "aprovado" único para a lista toda.

```bash
PAGINA="$(bash "${CLAUDE_PLUGIN_ROOT}/skills/improve-workflow/resolve-plugin.sh" visual lib/visual_page.py)"
PARECER="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/improve-workflow/parecer-$(date +%Y%m%d-%H%M%S).html"
SPEC="$(python3 "${CLAUDE_PLUGIN_ROOT}/lib/proposta.py" propostas.json)" || exit 2
if [ -z "$PAGINA" ]; then
  echo "sem o visual nesta máquina: nada é apresentado — as propostas ficam no propostas.json"
else
  printf '%s' "$SPEC" | python3 "$PAGINA" build --spec - --out "$PARECER"
fi
```

O destino é OBRIGATÓRIO e fica fora do projeto: sem `--out`, a página cai na cascata do
`/visual` e nasce em `.claude/visual/` do projeto auditado — escrita na árvore que esta
rodada jurou não tocar. O caminho a mostrar para o dono é o que o programa imprime.

O irmão entra pelo NOME, não pela posição no disco: **sem o `visual` na máquina** o
resolvedor sai calado e a rodada termina dizendo que a superfície de aprovação não
existe aqui — as propostas ficam no `propostas.json` e nada é apresentado no chat.

O `propostas.json` está no cabeçalho do `proposta.py`; proposta sem o número que
mira ou sem como conferir sai recusada ali, antes de virar item.

**8 · Colher o veredito, e gravar SÓ o aprovado.** O julgamento volta pelo disco, em
`~/.claude/visual-state/latest.json` (`state.feedback`), um veredito por item: `keep`
vira passo com o título da proposta, `change` vira passo com o texto que o dono
escreveu, `remove` não vira passo nenhum. Quem grava é o programa — a skill não
escreve plano à mão:

```bash
RETORNO="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/visual-state/latest.json"
printf '%s' "$SPEC" | python3 "${CLAUDE_PLUGIN_ROOT}/lib/plano_saida.py" \
  --retorno "$RETORNO" --proposta - --dir .claude/plans --run <run>
```

**Espere o dono julgar.** Rodar isto antes recusa a gravação inteira e diz o nome do
item em branco: rádio não tocado chega no retorno como `keep`, e gravar isso seria
transformar silêncio em aprovação. Descartou tudo, também não há plano.

O `--dir` é obrigatório de propósito, e o programa RECUSA sem ele: destino adivinhado
a partir da posição do programa cai dentro do cache do plugin na máquina de quem
instalou — o plano do dono nasceria na pasta do autor da skill.

Aqui a rodada ACABA. O plano fica ticável para outra rodada, com outro dono; esta
skill não aplica nada do que gravou.

## A chave de desligar

Todo automatismo da casa tem chave, e a desta mora fora do plugin — dentro dele
seria cache reescrito a cada bump, e a chave voltaria a ligar sozinha:

a palavra `off` dentro de `~/.claude/improve-workflow/mode` cala a autópsia; apagar
esse arquivo (ou escrever qualquer outra coisa nele) devolve a voz. Quem liga e desliga
é o dono, na mão — esta skill não escreve a chave, porque não escreve nada.

Com `off` ali, o medidor sai calado e com código zero — o fim de missão do `sovai`
não imprime nada, e nenhum passo desta skill dispara sozinho.

## A fronteira

`improve` implementa melhoria vinda de tarefa. `improve-workflow` audita execução que
já aconteceu e não implementa nada. Se o pedido é "conserta isso", é da vizinha.

## O check

`python3 "${CLAUDE_PLUGIN_ROOT}/lib/test_improve_workflow_skill.py"` roda a parte
executável da rodada sobre uma fixture e compara a árvore do projeto antes e depois:
qualquer arquivo alterado reprova.
