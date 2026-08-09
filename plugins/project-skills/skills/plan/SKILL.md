---
name: plan
description: Monta o plano de implementacao a partir da spec ja aprovada, e antes de criar qualquer plano novo IMPRIME os planos que ainda estao abertos no projeto. Use quando o usuario diz "/plan", "plano", "vira plano", "monta o plano da spec", "transforma a especificacao em plano", ou quando uma etapa de concepcao foi aprovada e o proximo passo e o plano ticavel. A palavra "plano" sozinha, sem mais nenhum contexto, JA E a invocacao — entre na skill em vez de pedir alvo ou vasculhar o repositorio, porque o passo 1 dela e justamente imprimir os planos abertos. Nao use para retomar plano existente, isso e tique, nao montagem.
---

# spec-to-plan — a spec aprovada vira plano ticável

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

## Passo 3 — grave o plano

Monte o JSON a partir da spec aprovada (requisitos com critério de aceite, fases, e uma
tarefa por unidade entregável, cada uma com `requisito` e `pronto`) e grave de uma vez:

```bash
python3 <plugin project-skills>/lib/plan_state.py init --file <arquivo.json>
```

O gravador recusa por forma antes de aceitar: `pronto` que não é verificável, passo sem
requisito, requisito sem critério de aceite. Recusa é resposta — conserte o JSON e grave
de novo; o `init` funde com o que já está no arquivo e preserva o que não veio no pacote.

## Passo 4 — quem monta não audita

O plano recém-montado vai para a auditoria (`lib/auditoria_plano.py`, neste mesmo
plugin), e **quem audita não é quem montou**. Nível 1 vermelho (o plano contradiz a
documentação canônica) para o laço; só com o nível 1 limpo a cobertura da spec é medida.
