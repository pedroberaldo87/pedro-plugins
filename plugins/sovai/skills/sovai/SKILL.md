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

## QA final (antes do relatório)

Terminada a execução e **ANTES** de montar o relatório, rode a skill `/qa-loop` em **modo headless** sobre o que você implementou, passando o plano como âncora:

```
/qa-loop <mudanças desta sessão> --plan=<plano> --headless
```

Como o Pedro está indisponível, o headless nunca pergunta nada. Trate os 3 buckets assim:
- **Implementação** (bug / divergência do plano) → conserta no loop. Você já tem mandato de executar o plano; o regression gate por conserto é a rede que evita as regressões auto-infligidas.
- **Plan-drift** (um "fix" afastaria do plano em UX/backend/proposta) → **reverte pro plano**. Não "melhore" pra longe do combinado.
- **Plano/arquitetura falho** → **NÃO implemente**. Vira item de "Bloqueios (precisam de você)" no relatório. Headless **não** é licença pra re-planejar.

O relatório do `/qa-loop` (loops rodados, correções, regressões pegas, alertas de plano) vira a seção `### QA` do relatório final.

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

### QA (qa-loop)
- [loops rodados + critério de parada · correções aplicadas · regressões pegas na hora]
- [⚠️ alertas de plano/arquitetura que NÃO implementei — pra você julgar]
```

Detalhe técnico só se Pedro pedir depois.
