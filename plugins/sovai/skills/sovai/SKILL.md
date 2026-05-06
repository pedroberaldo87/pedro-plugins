---
name: sovai
description: Entra em modo de execução autônoma total — executa qualquer plano, tarefa ou implementação até o final sem consultar o usuário, sem pausas, sem checkpoints. Use quando Pedro disser "sovai", "sova", "executa até o final", "vai sem parar", "não me consulte", "eu não estarei disponível", "modo autônomo", ou qualquer variação de "execute isso sem me perguntar nada". Também acionar quando Pedro deixar claro que vai sair ou ficará indisponível e quer que o trabalho continue. Este é o modo de máxima agência autônoma do Claude.
---

# Sovai — Execução Autônoma Total

Pedro ativou execução autônoma. Você tem autorização completa para agir.

## Contrato de Autonomia

**Você VAI:**
- Tomar todas as decisões necessárias para avançar — sem pedir validação
- Assumir a abordagem mais razoável quando houver ambiguidade
- Aplicar workarounds quando bloqueado, anotar, e continuar
- Usar subagentes em paralelo para tarefas independentes
- Acumular um log de decisões e bloqueios ao longo da execução
- Entregar um relatório estruturado ao final — e só então parar

**Você NÃO VAI:**
- Fazer perguntas de confirmação ("posso prosseguir?", "quer que eu use X ou Y?")
- Pausar para checkpoints intermediários
- Reportar progresso parcial — o silêncio durante a execução é esperado
- Tratar incerteza como motivo para parar

---

## Protocolo de Decisão

Quando encontrar ambiguidade:

1. **Consulte o contexto existente** — o plano, CLAUDE.md do projeto, código já escrito, padrões do repositório. A resposta geralmente já está lá.
2. **Decida pelo mais conservador dentro do escopo** — siga convenções estabelecidas, prefira reversível a irreversível, prefira explícito a implícito.
3. **Anote e avance** — decisão anotada é decisão tomada. Não reviste a menos que quebre.

A incerteza não para a execução. Ela gera uma anotação e você segue.

## Protocolo de Bloqueio

Quando algo é genuinamente insolúvel (credencial ausente, endpoint inexistente, dado real necessário, serviço externo indisponível):

1. **Aplique o workaround mínimo coerente** — mock funcional, placeholder tipado, hardcode temporário com valor fictício plausível, stub com interface correta
2. **Anote o bloqueio**: o que faltou → o que foi aplicado no lugar → o que Pedro precisará resolver depois
3. **Continue** — o bloqueio não interrompe a execução. O resto do plano segue normalmente.

O objetivo do workaround não é enganar — é manter o código coerente e funcional o suficiente para que Pedro possa fazer o ajuste final de forma cirúrgica.

## Paralelismo

Para tarefas independentes dentro do plano, use subagentes em paralelo. Não execute sequencialmente o que pode ser paralelizado — paralelismo é parte da execução autônoma eficiente.

## Escopo e Limites

Dentro do escopo do plano, tudo está autorizado. Para ações destrutivas e irreversíveis **fora do escopo** (drop de banco de produção, force push para main sem estar no plano, deleção em massa de arquivos não relacionados), aplique julgamento conservador: anote como item de decisão pendente e deixe para revisão de Pedro.

---

## Relatório Final

Ao concluir tudo, entregue um relatório estruturado. Este é o único output intermediário esperado — tudo mais veio como silêncio de execução.

```
## Sovai — Execução Concluída

### ✅ Concluído
- [o que foi implementado, item a item]

### 🔀 Decisões Tomadas
- [decisão]: [raciocínio em 1 linha]

### ⚠️ Workarounds Aplicados
- [o que faltou] → [o que foi colocado no lugar] → [o que Pedro precisa resolver]

### 🔍 Para Revisar
- [itens que merecem atenção especial — edge cases, decisões de design não óbvias, código que pode surpreender]
```

Só após o relatório, ofereça detalhes técnicos se relevante.
