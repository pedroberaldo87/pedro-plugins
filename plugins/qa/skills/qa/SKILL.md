---
name: qa
description: Audita implementação contra um plano até 100% aderente. Lança 4 agentes especialistas em paralelo, corrige divergências, repete até zero findings. Trigger em "/qa", "audita o plano", "tá 100%?".
---

# /qa — Auditoria de aderência ao plano

## Input

`/qa <path-do-plano>`

O argumento é o path de um plano (`.claude/plans/*.md`, `docs/specs/*.md`, ou qualquer arquivo markdown com o plano de implementação).

## Fluxo

1. **Ler o plano** — Read no path fornecido. Se path inválido, erro.
2. **Escolher 4 agentes** — Baseado no domínio do plano, escolher 4 voltagent specialists relevantes. Exemplos:
   - API/backend → backend-developer, api-designer, code-reviewer, test-automator
   - UI/frontend → frontend-developer, ui-designer, accessibility-tester, code-reviewer
   - Banco/data → database-optimizer, backend-developer, architect-reviewer, code-reviewer
   - Fullstack → fullstack-developer, architect-reviewer, code-reviewer, frontend-developer
   - Infra/deploy → architect-reviewer, performance-engineer, security-auditor, code-reviewer
3. **Rodar /goal** com condição: "Zero findings P0/P1 dos 4 auditores"
4. **Em cada turn do /goal:**
   - Despachar os 4 agentes em paralelo (single message, 4 Agent calls)
   - Cada agente recebe o plano completo + o código atual
   - **A partir da 2ª rodada:** cada agente também recebe os findings da rodada anterior e deve (a) verificar se foram resolvidos, (b) procurar novos problemas
   - Consolidar findings
   - Corrigir todos os P0/P1
   - Se ainda há P0/P1 (não resolvidos ou novos) → /goal continua
   - Se zero P0/P1 → /goal encerra

## Prompt dos agentes

Cada agente recebe:

```
Você é um auditor de implementação. Seu trabalho: comparar o código atual com o plano abaixo e reportar divergências.

## Plano
<PLANO COMPLETO>

## Sua lente
<LENTE ESPECÍFICA DO AGENTE>

## Findings da rodada anterior (se 2ª rodada em diante)
<FINDINGS ANTERIORES OU "Primeira rodada — não se aplica">

## O que fazer
Audite o código como se fosse a primeira rodada — leia o plano, compare com o código, reporte tudo que encontrar. Não se limite aos findings anteriores. Sua auditoria deve ser completa e independente.

Depois, como passo separado, cruze seus achados com os findings da rodada anterior:
- Se um finding anterior sumiu do seu report → foi resolvido (não precisa mencionar)
- Se um finding anterior ainda aparece → re-reporte como "NÃO RESOLVIDO"
- Novos findings que não existiam antes → reporte normalmente

## O que reportar
- P0: Bug crítico, feature do plano não implementada, comportamento quebrado
- P1: Divergência do plano (abordagem diferente, nome errado, estrutura diferente)
- P2: Code smell, melhoria possível (NÃO corrigir, só reportar)
- P3: Nit (ignorar)

## Formato
Para cada finding:
**P{N}** — {arquivo}:{linha} — {problema} — {direção de fix}

Para re-reports: **P{N} NÃO RESOLVIDO** — {arquivo}:{linha} — {problema original} — {por que não foi resolvido}

Se nada encontrado: "✅ Zero findings sob minha lente (anteriores resolvidos + zero novos)."
```

## Consolidação

Após os 4 agentes retornarem:
- P0/P1 → corrigir imediatamente (editar código)
- P2/P3 → listar ao final como sugestões, não corrigir
- Duplicatas entre agentes → deduplicar

## Quando encerra

/goal encerra quando **todos os 4 agentes reportam zero P0/P1** em uma rodada.

## Quando NÃO usar

- Não existe plano escrito → recuse, peça pra criar um plano primeiro
- Plano é vago demais (sem itens concretos) → recuse
- Código ainda não foi implementado (nada pra auditar) → recuse
