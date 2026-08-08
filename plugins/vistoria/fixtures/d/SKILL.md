<!-- ARQUIVO DE MENTIRA CONGELADO — fixture da letra (d) do gabarito: cobertura parcial
     do escopo. A instrução enumera os estados abaixo e só trata parte deles.
     Não é plugin de verdade e nada aqui é distribuído. NÃO CONSERTAR. -->
---
name: exemplo-d
description: Fixture de cobertura parcial — a instrução enumera casos e trata só uma parte.
---

# Exemplo D

Um passo do plano está sempre em um destes estados:

- `todo` — ninguém pegou
- `doing` — alguém está nele agora
- `done` — fechou com prova
- `blocked` — parado esperando terceiro
- `cancelado` — saiu da fila

## O que fazer em cada estado

- Em `todo`: pegue o passo e passe para `doing`.
- Em `doing`: termine e passe para `done`.
- Em `done`: não toque; siga para o próximo.
