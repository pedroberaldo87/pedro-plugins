---
name: sovai
description: Modo de execução contínua — Claude executa um plano ou tarefa multi-etapa do começo ao fim sem pausas, sem checkpoints, sem perguntas de confirmação. Toma as decisões necessárias para seguir e anota cada uma. Pedro estará indisponível durante a execução; ele revisa tudo no relatório final e refatora se necessário. Use quando Pedro disser "sovai", "sova", "executa até o fim", "vai sem parar", "não me consulte", "eu não estarei disponível", "modo autônomo", ou variação clara de "executa sozinho enquanto eu não tô". Não disparar para tarefas curtas que terminam num turno — a skill existe para missões em que interrupção custa caro porque Pedro não está disponível para responder.
---

# Sovai — Execução Contínua

Pedro vai ficar indisponível. Reconheça com uma linha (`modo sovai ativo, começando`) e comece. Daqui em diante, silêncio até o relatório final.

## Contrato

**Faz:**
- Executa o plano (ou a tarefa) do começo ao fim, sem pausar
- Toma todas as decisões necessárias para seguir e **anota cada uma**
- Verifica antes de declarar feito — regras globais do CLAUDE.md continuam valendo

**Não faz:**
- Pergunta de confirmação no meio ("posso seguir?", "X ou Y?")
- Checkpoint intermediário pedindo aval
- Reporte de progresso parcial — silêncio é o esperado
- Ação destrutiva ou irreversível fora do escopo do plano (drop de banco em produção, force push em main, rotação de credencial real, deploy fora do combinado) — registra como pendência

## Bloqueios

Se um item não puder ser feito como pedido, **não invente workaround silencioso**. Pula o item, anota o bloqueio com o que faltou, e segue para o próximo. A regra global "Entrega 100% ou Para e Conversa" continua valendo — o "Para e Conversa" vira "Pula e Anota" porque Pedro está indisponível, mas a entrega ainda precisa ser honesta.

## Relatório Final

Quando terminar, entregue **antes de qualquer outra coisa**:

```
## Sovai — terminei

### Feito
- [só o que foi verificado]

### Decisões tomadas
- [decisão]: [razão em 1 linha]

### Bloqueios (precisam de você)
- [item pulado]: [o que faltou]

### Verificação
- [o que rodou, e o resultado]
```

Detalhe técnico só se Pedro pedir depois.
