<!-- FONTE: _shared/regua-de-pergunta.md. NÃO editar as cópias vendoradas que
     moram ao lado de cada SKILL.md — edite aqui e rode scripts/sync-shared.sh.
     Quem cobra o texto em todas as cópias: _shared/test_regua_de_pergunta.py. -->

# Por onde a pergunta chega — régua única de toda skill que pergunta ao dono

A instrução da skill diz **o que** perguntar. Quem escolhe **por onde** é o usuário, e são dois canais:

- **Padrão — a rodada inteira numa página, em múltipla escolha.** A rodada de perguntas vira uma
  página de decisão: cada pergunta é um item, com as opções em rádio e **um campo livre embaixo**
  para o que não cabe nas opções. A recomendação entra marcada como sugestão, nunca como
  resposta dada. É um canal só de ida e volta: o usuário responde a rodada inteira de uma vez,
  em vez de gastar um turno por pergunta.
  - **Como montar:** se a skill de apresentação visual estiver entre as suas skills disponíveis,
    invoque-a **pelo nome** e peça uma página de decisão com um item por pergunta. Não monte
    caminho de arquivo para dentro de outro plugin, e não rode programa de outro plugin: se a
    skill não estiver disponível na máquina, o canal padrão simplesmente não existe ali — caia
    no canal alternativo e siga.
  - **Como colher:** a resposta volta pelo estado que o daemon dessa página grava em disco, em
    `~/.claude/visual-state/latest.json`. Leia de lá; não peça ao usuário para copiar e colar.
  - **Pergunta sem apoio não vale.** Toda opção mostra o conteúdo concreto de que ela fala — o
    trecho literal, o número com procedência. O usuário não adivinha o seu contexto.

- **Alternativa — uma por vez, na ferramenta nativa de pergunta.** Mesma fila, mesma ordem,
  só que servida pergunta a pergunta no próprio CLI.

**Quem escolhe é o usuário.** Na primeira rodada, ofereça os dois e use o que ele pedir; ele pode
trocar de canal a qualquer momento, e a troca vale da rodada seguinte em diante. Sem escolha dita,
use o padrão.
