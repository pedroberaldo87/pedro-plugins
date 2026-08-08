---
name: andamento
description: Mostra onde a implementação do plano atual está, no CLI, em forma de árvore escaneável. Use quando o usuário digitar `/andamento`, ou disser "onde a gente está", "como está o plano", "o que já foi feito", "o que falta", "andamento da implementação". Também vale durante a execução de um motor, para acompanhar o avanço sem abrir o browser.
---

# Skill: /andamento

Responde "onde a gente está?" em uma tela, direto no CLI. Não abre browser, não gera arquivo,
não escreve nada — só lê o arquivo do plano e desenha.

## O comando

```bash
python3 <plugin project-skills>/lib/plan_state.py render --format text --compacto
```

Se houver mais de um plano no projeto, o comando pede o id. Liste e escolha o mais recente:

```bash
ls -t .claude/plans/*.plan.json | head -3
python3 <plugin project-skills>/lib/plan_state.py render <id-do-plano> --format text --compacto
```

## Como ler a saída

```
📋 <o plano>  —  16/37 passos          ← o placar, na primeira linha

✅ F3 · <fase pronta>          (2/2)   ← fase inteira fechada
🔄 F1 · <fase em curso>        (2/5)   ← começou, não terminou
⬜ F8 · <fase não começada>    (0/3)
⛔ F5 · <fase travada>         (1/4)   ← algum passo dela tem decisão pendente

     ● F1.1  <passo feito, com prova gravada>
     ◐ F1.2  <passo em curso>
     ○ F1.4  <passo que ninguém começou>
     ✕ F1.5  <passo travado>
            ⛔ <a decisão que falta — é o que trava o tique>
```

O `⛔` é a única coisa que sobrevive ao modo curto, de propósito: ele é o "deu problema",
e esconder problema numa vista resumida seria o anti-padrão que o resto deste plugin
existe para impedir.

## O que emitir no CLI

A árvore, e mais nada. Ela já traz o placar na primeira linha e a marca em cada passo —
repetir isso em prosa embaixo é a segunda tabela que a régua da casa proíbe.

Duas exceções, cada uma de UMA linha, e só quando o caso ocorre:

- **Há passo travado** (`⛔`): repita os ids travados no fim, como índice. O usuário
  precisa vê-los mesmo se a árvore rolar a tela.
- **O usuário perguntou por um passo específico**: aí sim mostre a prova daquele passo,
  rodando o mesmo comando **sem** `--compacto` e recortando o trecho.

## Quando o usuário quiser mais

- **a prova de cada passo feito** → o mesmo comando sem `--compacto`
- **a vista por valor** (épico › requisito › tarefa) → acrescente `--vista valor`
- **a página no browser, para marcar veredito** → é o `/visual`, não esta skill
- **os dois lados do fio** (requisito sem tarefa, tarefa sem requisito) →
  `plan_state.py cobertura <id>`

## O que esta skill NÃO faz

Não marca passo, não fecha plano, não reescreve nada. É leitura pura — marcar exige prova
e é `plan_state.py tick`, que é outro rito. Nenhum plano no projeto: diga isso em uma linha
e ofereça o `/visual` para criar um.
