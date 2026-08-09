---
name: branches
description: Use quando o usuário diz "/branches", "limpa as branches", "quais branches dá pra apagar", "tem branch sobrando", "o deploy tá reclamando de branch aberta", ou quando um projeto acumulou branches de trabalho já terminado. Classifica cada branch em três categorias por CONTEÚDO (não por ancestralidade), entrega um relatório com checkbox pro usuário escolher, e apaga só o marcado — sempre criando uma tag de resgate antes. O ponto que justifica o plugin é este - o comando `git branch --merged`, que todo mundo usa, mente por omissão, porque squash-merge e rebase produzem sha novo e a branch aparece como não-mergeada mesmo com o conteúdo inteiro no tronco. É por isso que a pilha cresce até o deploy reclamar de 15 branches abertas. Roda em qualquer projeto e também varre uma pasta inteira de projetos de uma vez.
---

# Skill: /branches

O problema nunca foi apagar branch. É saber **quais**.

## A razão de existir, em um número

Medido no `pedro-plugins` em 2026-07-28:

```
BRANCH          git branch --merged     conteúdo já está na main?
docs/readme     NÃO                     SIM — entrou por squash
```

O `--merged` só enxerga merge por **ancestralidade**. Squash-merge (o botão
padrão do GitHub) e rebase reescrevem os commits com sha novo — a branch
original fica órfã e o comando a declara não-mergeada. Quem confia nele nunca
apaga nada, porque a lista mistura "já foi" com "ainda não foi" sem distinção.

Este plugin compara por **conteúdo** (patch-id, via `git cherry`). É a
diferença entre uma lista em que se confia e uma que se ignora.

## As três categorias

| categoria | o que é | o que fazer |
|---|---|---|
| **merged** | o git já reconhece o merge | apagar é seguro |
| **equivalent** | o conteúdo está no tronco, mas com sha novo (squash/rebase) | apagar é seguro — **e é o que o `--merged` perde** |
| **unique** | tem commit que só existe ali | **NÃO é lixo, é trabalho** |

A terceira é a razão de nada aqui apagar sozinho. Uma limpeza em bloco mataria
justamente o que o usuário esqueceu de mergear — que é o caso que dói.

## Fluxo

```bash
BS="${CLAUDE_PLUGIN_ROOT}/lib/branch_state.py"

# 1. medir (só lê — nunca escreve no repositório)
python3 $BS list                      # o projeto atual
python3 $BS list --scan ~/PROGRAMACAO # uma pasta inteira de projetos
python3 $BS list --json               # pra processar

# 2. relatório com checkbox, escrito em <raiz>/.claude/visual/
open "$(python3 $BS report)"

# 3. apagar SÓ o que o usuário marcou, por nome
python3 $BS prune docs/readme feat/sprint-build-engine
python3 $BS prune --dry-run <nomes>   # mostra o que faria
```

O usuário marca no HTML e clica **Copiar as marcadas**; o bloco vem com o marcador
`<!-- branches-apagar v1 -->` e a lista de nomes. Passe esses nomes pro `prune`
— **um a um, literais**. Nunca monte a lista você mesmo a partir da categoria.

## Regras não-negociáveis

1. **Nunca apague sem o usuário marcar.** Nem as "seguras". O relatório pré-marca
   as seguras pra poupar clique, mas o gesto de confirmar é dele. Mesmo desenho
   do `/fallow`.
2. **Nunca chame `prune` com branch da categoria `unique`.** O comando já
   recusa e mostra o que seria perdido. Se o usuário insistir, ele decide com
   `--force`, e mesmo aí a tag de resgate sai.
3. **Toda branch apagada vira `archive/<branch>-<data>`.** Voltar atrás é
   `git branch <nome> <tag>` — um comando, não arqueologia no reflog. Se a tag
   não puder ser criada, o `prune` aborta **antes** de apagar.
4. **O relatório mostra o que seria perdido.** Toda branch `unique` traz o
   assunto e os arquivos dos commits que só existem nela, à vista, antes da
   decisão. Pedir pra decidir sem mostrar é o defeito que a skill `/visual`
   proíbe — vale aqui igual.
5. **Branch remota é outro assunto.** Este plugin mexe só em branch **local**.
   Apagar no remoto é `git push origin --delete <b>`, e é decisão separada.

## Os dois avisos (hooks)

| Evento | Script | Quando fala |
|---|---|---|
| `PostToolUse[Bash]` | `posttooluse-push-branch.sh` | depois de um `git push` que deu certo, numa branch com trabalho que ainda não está no tronco. 1× por (branch, sessão). |
| `SessionStart` | `sessionstart-branches.sh` | quando há branch parada há mais de 30 dias. Só a contagem e os nomes — o relatório é o `/branches`. |

Os dois **informam, nunca bloqueiam**. Kill-switch dos dois: `BRANCHES_GATE=0`.
Limiar de "parada": `BRANCHES_DIAS=<n>`.

O do push existe porque a pilha não se forma por preguiça — se forma porque
merge não é o último passo do ciclo. A pergunta tem que cair quando o usuário
**ainda lembra** do que a branch era; um mês depois, olhando quinze nomes,
ninguém sabe.

## Quando o usuário pedir a limpeza

1. Rode `list` (ou `list --scan` se ele falou em vários projetos).
2. Gere o relatório e abra. **Não** despeje a lista no CLI — o HTML é a lista.
3. Espere ele marcar e colar o bloco.
4. Rode `prune` com os nomes literais que vieram.
5. Reporte em 2-3 linhas: quantas apagadas, e a tag de resgate de cada uma.

Se o `list` não achar nada, diga isso em uma linha e pare — não gere relatório
vazio.
