# projeto-alheio — o projeto de quem INSTALOU o plugin

Esta fixture é um projeto qualquer, e a graça dela é o que NÃO tem:

- nenhuma missão no disco (usada como `CLAUDE_CONFIG_DIR`, não há `projects/`);
- nenhum plano em `.claude/plans/`;
- nenhum dos plugins irmãos (`project-skills/lib/plan_state.py`, o `visual`).

A autópsia nasceu neste repositório, onde os três existem. Rodada aqui, ela tem
que dizer em voz alta o que não pôde medir e sair ZERO — travar a rodada de quem
instalou seria acusar defeito onde não houve nem medição.

Quem cobra: `caso_projeto_alheio` em `lib/test_medidor.py`.
