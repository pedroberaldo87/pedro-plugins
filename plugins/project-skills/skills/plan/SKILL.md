---
name: plan
description: Monta o plano de implementacao a partir da spec ja aprovada, e antes de criar qualquer plano novo IMPRIME os planos que ainda estao abertos no projeto. Use quando o usuario diz "/plan", "plano", "vira plano", "monta o plano da spec", "transforma a especificacao em plano", ou quando uma etapa de concepcao foi aprovada e o proximo passo e o plano ticavel. A palavra "plano" sozinha, sem mais nenhum contexto, JA E a invocacao — entre na skill em vez de pedir alvo ou vasculhar o repositorio, porque o passo 1 dela e justamente imprimir os planos abertos. Nao use para retomar plano existente, isso e tique, nao montagem.
---

# spec-to-plan — a spec aprovada vira plano ticável

## Antes de tudo — a régua e os princípios (o par obrigatório)

Antes de montar o plano, rode o par, nesta ordem — é ele que substitui a antiga instrução em
prosa "leia a constituição e o quality-goals do projeto":

1. **A régua do projeto** — a skill `doc-load` (invoque pela Skill tool; fora dela:
   `python3 "$(bash "<plugin project-skills>/lib/resolve-plugin.sh" project-skills lib/doc_load.py)" --project-root "$PWD"`).
   Ela diz o que vale como régua HOJE — a lei com `ready`/`approved`, o acordo só com
   `approved`, o minerado como mapa — e o que está ausente, sem fingir.
2. **Os princípios genéricos** — a skill `principles`, quando instalada
   na máquina. Ausente: siga sem ela, dizendo isso no relato.

Em conflito, **a régua do projeto ganha** — princípio genérico não revoga a lei da casa.

O plano não se escreve de memória: ele nasce da spec **aprovada** e vira arquivo em
`.claude/plans/<id>.plan.json`. Daí em diante ele só é MARCADO — quem desenha a árvore e
quem grava é o programa, nunca o modelo redigitando título.

## Passo 1 — imprima os planos abertos ANTES de criar o novo

Dois planos abertos sem aviso viram duas filas concorrentes: uma sessão marca numa, a
outra sessão marca na outra, e nenhuma das duas está completa. Então a primeira coisa
que esta skill faz — antes de escrever uma linha do plano novo — é **mostrar ao usuário
o que já está aberto**:

```bash
python3 <plugin project-skills>/lib/plan_state.py open
```

- **Saiu vazio** → siga para o passo 2.
- **Saiu um ou mais planos** → mostre a saída crua ao usuário e **pergunte** antes de
  seguir: o trabalho novo entra como fase do plano que já está aberto, ou nasce um plano
  separado de propósito? Não decida isso em silêncio. Plano aberto que ninguém vai
  retomar se encerra com `plan_state.py close <id>`.

## Passo 2 — o plano nasce com id próprio

O id é do plano, e é dele para sempre: `<AAAA-MM-DD>-<slug>`, onde o slug descreve o
assunto do plano em minúsculas com hífen. **Escolha um id que ainda não existe** — o
passo 1 já mostrou quais existem, e `ls .claude/plans/` mostra também os fechados.

Nunca reaproveite o id de outro plano para gravar assunto diferente: o `init` **recusa
renomear id existente** (ele acusa cada nó que já está gravado com outro título e não
grava nada), então reaproveitar id não sobrescreve — só devolve recusa e queima a rodada.

## Passo 3 — monte o mapa da régua ANTES de escrever a primeira tarefa

O `doc-load` diz QUAIS arquivos são a régua — só a lista, não o conteúdo dela. Escrever
tarefa com a lista na mão é escrever de memória. Então, antes da primeira tarefa, extraia
o que cada documento da régua de fato contém — os artigos da lei, as jornadas, as peças
da arquitetura pretendida e os passos do ciclo:

Quem sabe ONDE cada documento mora é o programa, não esta página: o `plan_state.py`
resolve cada um por cascata (variável de ambiente → a pasta de doc do projeto → a raiz),
e é por isso que o trecho abaixo não escreve nome de arquivo nenhum. Escrever a lista
aqui já custou caro — projeto que guarda a doc fora do lugar padrão via `artigos (0)` neste
passo e era reprovado depois pela auditoria, que ACHA a lei.

```bash
PS="$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/plan_state.py)"
python3 -c 'import sys, os
sys.path.insert(0, os.path.dirname(sys.argv[1]))
import plan_state as c
d = c.resolve_dir()
for rotulo, ler in (("artigos", c._artigos_do_projeto), ("jornadas", c._jornadas_do_projeto),
                    ("pecas", c._pecas_do_projeto), ("passos", c._passos_do_projeto)):
    itens = ler(d)
    print("%s (%d)" % (rotulo, len(itens)))
    for i in itens:
        print("   -", i)' "$PS"
```

Cada requisito do plano cita daí: `ancora` sai da lista de artigos, `jornada` da lista de
jornadas, `peca` das peças, `passo` dos passos. Lista vazia é resposta — documento que o
projeto não tem não vira citação inventada, e o campo correspondente fica de fora. Citação
que não está na lista é recusada depois pela auditoria (`artigos_inexistentes`,
`pecas_inexistentes`), então conferir aqui é mais barato que descobrir no passo 5.

## Passo 4 — grave o plano

Monte o JSON a partir da spec aprovada (requisitos com critério de aceite, fases, e uma
tarefa por unidade entregável, cada uma com `requisito` e `pronto`) e grave de uma vez:

```bash
python3 <plugin project-skills>/lib/plan_state.py init --file <arquivo.json>
```

O gravador recusa por forma antes de aceitar: `pronto` que não é verificável, passo sem
requisito, requisito sem critério de aceite. Recusa é resposta — conserte o JSON e grave
de novo; o `init` funde com o que já está no arquivo e preserva o que não veio no pacote.

## Passo 5 — quem monta não audita

O plano recém-montado é julgado pelos **mesmos três pés de toda revisão deste
marketplace** — a seção *"Os três pés no artefato PLANO"* de `references/dimensoes-de-revisao.md`,
ao lado desta skill, diz o que cada pé olha num plano. O texto mora lá e não se repete
aqui (a fonte é `_shared/dimensoes-de-revisao.md`, vendorada): leia a cópia local antes
de mandar para a auditoria. O Pé 2 aponta para os cinco antipadrões de teste, que moram
em `references/antipadroes-de-teste.md` (fonte: `_shared/antipadroes-de-teste.md`) —
também ao lado desta skill, para o apontamento não morrer na máquina instalada.


O plano recém-montado vai para a auditoria (`lib/auditoria_plano.py`, neste mesmo
plugin), e **quem audita não é quem montou**. Nível 1 vermelho (o plano contradiz a
documentação canônica) para o laço; só com o nível 1 limpo a cobertura da spec é medida.

## Racionalizações — a desculpa refutada antes de você dá-la

Todo plano torto deste repositório começou com uma destas frases:

- **"o pedido está claro, escrevo o plano direto"** → sem a régua e sem os planos abertos
  na mesa, o plano novo nasce duplicando ou contradizendo o que já existe.
- **"esse passo é óbvio, o `pronto` pode ser genérico"** → `pronto` que ninguém consegue
  reprovar não é critério, é desejo. O gravador recusa por forma, e recusa é resposta.
- **"eu montei e sei que está bom, dispenso a auditoria"** → quem monta não audita.
- **"a auditoria reclamou de detalhe, sigo assim mesmo"** → nível 1 vermelho (o plano
  contradiz a documentação canônica) para o laço. Não há cobertura a medir antes disso.
- **"o passo é grande, mas quem executar se vira"** → tarefa que não cabe num executor
  volta como espera. Quebrar agora é mais barato que descobrir no meio da noite.
