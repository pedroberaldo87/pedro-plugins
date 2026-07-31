---
name: intent-guard
description: "Use quando o usuário digitar /intent-guard (status, baixa N, off, on, projeto-off, projeto-on), perguntar o que está no caderno de pedidos, pedir para arquivar um pedido, ou quando o gate de entrega do intent-guard bloquear o Stop. Mostra e opera o ledger de pedidos verbatim e a auditoria independente de entrega. Plugin EXPERIMENTAL — baixa automática por auditoria pode migrar para baixa manual."
---

# intent-guard — comandos e obrigações

O ledger fica em `<projeto>/.claude/intent/ledger.jsonl` (invisível pro git via
`.git/info/exclude`). Toda operação passa pelo CLI:
`python3 ${CLAUDE_PLUGIN_ROOT}/lib/ledger.py <cmd> --cwd <projeto>`.

## Comandos

| Pedido do usuário | Ação |
|---|---|
| `/intent-guard status` | Rode `ledger.py status --cwd $PWD` e mostre TUDO: vivos, resolvidos E os descartados como conversa (pra o usuário pescar erro de classificação). Passou de 10 linhas → renderize via /visual. |
| `/intent-guard baixa <n>` | `ledger.py baixa --cwd $PWD --id p-<n> --by usuario --reason "<motivo que ele deu>"`. Confirme em 1 linha o que foi arquivado. |
| `/intent-guard off` / `on` | Escreva `off` em `~/.claude/intent-guard/mode` (ou remova o arquivo). Vale pra TODAS as sessões e projetos, sem reload. |
| `/intent-guard projeto-off` / `projeto-on` | Crie/remova o arquivo `.claude/intent/off` no projeto atual. |

## Quando o gate de entrega bloquear o Stop

Siga as instruções do bloqueio À RISCA:
1. O prompt do auditor é `references/auditor-prompt.md` deste plugin — passe o
   texto VERBATIM ao subagente + o bloco DADOS do bloqueio. NÃO reescreva, NÃO
   resuma, NÃO acrescente contexto da conversa (o auditor é independente DE
   PROPÓSITO — qualquer contexto seu contamina a auditoria).
2. Depois do veredito, tente encerrar de novo — o hook valida e transcreve.
3. OBRIGATÓRIO: mostre a tabela de vereditos ao usuário (pedido → veredito →
   CONFIRMADO/INFERIDO → evidência). Mais de 10 linhas → /visual. "Entregue"
   sem mostrar a tabela é violação desta skill.

## Regras EXPERIMENTAIS (decisão de projeto, 2026-07-24)

Baixa automática: FEITO+CONFIRMADO arquiva sozinho. Se isso se mostrar
traiçoeiro, a migração é: remover o bloco de baixa em `apply_audit()` no
`lib/ledger.py` — os vereditos continuam, só a baixa vira manual.

Sem `claude` no PATH, sessão sem plan mode não classifica crus → gate de
entrega pode não cobrar (fail-open documentado).
