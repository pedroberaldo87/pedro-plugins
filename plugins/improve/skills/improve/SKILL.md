---
name: improve
description: Implementador genérico de auto-melhoria pra qualquer app usando a metodologia de ML autoresearch. Lê o IMPROVEMENT_PROGRAM.md do app pra contexto, busca propostas de GitHub Issues (label 'autoresearch'), implementa as mudanças. Use com "improve", "melhoria", "rodada de improvement".
---

# Improve — Implementador Genérico de Auto-Melhoria

## Visão Geral

Uma skill genérica que implementa propostas de melhoria pra QUALQUER app seguindo a metodologia de ML autoresearch. A skill sabe COMO implementar — o `IMPROVEMENT_PROGRAM.md` do app sabe O QUE implementar.

**Esta skill é agnóstica de app.** Todo conhecimento específico do app vive na documentação do app.

## Como Funciona

```
┌──────────────────────────────┐     ┌──────────────────────────────┐
│  /improve (esta skill)       │     │  IMPROVEMENT_PROGRAM.md do app│
│  ─────────────────────       │     │  ─────────────────────────── │
│  Implementador genérico:     │────▶│  Contexto específico do app: │
│  • Ler docs                  │     │  • Objetivos por etapa       │
│  • Buscar GitHub Issues      │     │  • O que é ajustável         │
│  • Implementar mudanças      │     │  • O que é imutável           │
│  • Lint, commit, deploy      │     │  • Endpoints da API          │
│  • Fechar issues             │     │  • Como diagnosticar         │
└──────────────────────────────┘     │  • Como avaliar              │
                                     │  • Regras de segurança       │
                                     └──────────────────────────────┘
```

## Processo

### 1. Achar o Program do App

Procure `IMPROVEMENT_PROGRAM.md` no diretório de trabalho atual ou em qualquer subdir `apps/*/`. Este arquivo é OBRIGATÓRIO — se não existe, diga ao usuário que ele precisa criar um pro app dele.

```bash
# Procura os arquivos de program
find . -name "IMPROVEMENT_PROGRAM.md" -maxdepth 3
```

Se vários forem achados (monorepo), pergunte ao usuário qual app melhorar. Se só um, use ele.

**Leia o IMPROVEMENT_PROGRAM.md inteiro antes de fazer qualquer coisa.** Ele contém:
- Os objetivos e métricas do app
- Quais arquivos podem ser modificados e quais são IMUTÁVEIS
- Endpoints da API pra health/status
- Como diagnosticar problemas
- Como gerar propostas
- Regras de segurança

### 2. Buscar o Status

Use os endpoints de health/status documentados no program file pra mostrar o estado atual:
- Score geral / métrica de saúde
- Scores por etapa ou por componente
- Tendência (melhorando / piorando / estável)
- Status de proposta ativa (se houver)

Apresente um resumo conciso ao usuário.

### 3. Checar GitHub Issues

```bash
gh issue list --repo {repo} --label autoresearch --state open --json number,title,body,labels
```

Onde `{repo}` é determinado pelo git remote (`git remote get-url origin`).

**Se houver issues abertas:** Liste com número + título. Pergunte ao usuário qual implementar.

**Se não houver issues abertas:** Ofereça duas opções:
- Gerar uma proposta nova: chame o endpoint de geração de proposta do program file. A resposta da API inclui um campo `github_issue` com `title` e `body` pré-formatados. Use `gh issue create` pra criar a issue a partir desses dados.
- Deixar o usuário descrever o que quer melhorar manualmente

### 4. Implementar a Mudança

Leia o corpo da GitHub Issue selecionada. Issues seguem esta estrutura:

```markdown
## Diagnosis
- **Target:** {component/stage}
- **Current score:** {score}
- **Hypothesis:** {what we think will improve}

## Change Type
config | code

## Config Changes
| Parameter | Current | Proposed |
|-----------|---------|----------|
| key | old | new |

## Code Changes
{description of what to change}

---
*App: {app_name}*
*Proposal ID: {id}*
```

**Pra mudanças de config:**
1. Mostre as mudanças propostas
2. Confirme com o usuário
3. Aplique via o endpoint da API documentado no program file
4. Sem deploy necessário (config é lida do DB em runtime)

**Pra mudanças de código:**
1. Leia o IMPROVEMENT_PROGRAM.md pra entender quais arquivos são editáveis
2. Leia os arquivos-fonte relevantes
3. Implemente a mudança descrita na issue
4. **NUNCA modifique arquivos listados como IMUTÁVEIS no program**
5. Mostre o diff ao usuário
6. Confirme antes de commitar
7. Lint usando as ferramentas de lint do projeto (leia de CLAUDE.md ou pyproject.toml)
8. Commit: `improve({app}): {short description} (closes #{issue_number})`
9. Push + deploy usando o método de deploy do projeto

### 5. Fechar a Issue

- Mudanças de código: a mensagem de commit `closes #N` auto-fecha
- Mudanças de config: feche manualmente com um comentário descrevendo o que foi aplicado

```bash
gh issue close {N} --comment "Aplicado via /improve. {resumo da mudança}"
```

### 6. Pós-Implementação

Lembre o usuário com base no que o program file diz sobre avaliação:
- Quantas runs são necessárias antes da avaliação
- Como disparar runs (se documentado)
- Como checar resultados depois (`/improve status`)

## Subcomandos

### `/improve` (default)
Ciclo completo: ler program → mostrar status → escolher issue → implementar → deploy

### `/improve status`
Ler program → mostrar scores atuais + progresso da proposta ativa. Sem implementação.

### `/improve history`
Mostrar rodadas de melhoria passadas do endpoint de histórico do app.

## Criando uma GitHub Issue a partir de uma Proposta

Quando o app gera uma proposta (via API), crie uma GitHub Issue:

```bash
gh issue create \
  --repo {repo} \
  --title "[improve:{app}:{stage}] {short hypothesis}" \
  --label autoresearch \
  --body "$(cat <<'EOF'
## Diagnosis
- **Target:** {stage} (score: {score})
- **Combined score:** {combined}
- **Trend:** {trend}

## Change Type
{config|code}

## Proposal
**Hypothesis:** {hypothesis}

### Config Changes
| Parameter | Current | Proposed |
|-----------|---------|----------|
{param_table}

### Code Changes
{code_description}

---
*App: {app_name}*
*Proposal ID: {proposal_id}*
*Run `/improve` in Claude Code CLI to implement*
EOF
)"
```

## O Que Esta Skill NÃO Faz

- NÃO contém lógica específica de app — todo contexto vem do program file
- NÃO modifica arquivos marcados como IMUTÁVEIS no program
- NÃO auto-implementa sem confirmação do usuário
- NÃO pula verificação de lint ou deploy
- NÃO avalia resultados — o pipeline do app faz isso automaticamente

## Escrevendo um IMPROVEMENT_PROGRAM.md

Pra devs de app que querem usar esta skill, seu `IMPROVEMENT_PROGRAM.md` tem que incluir:

1. **Arquitetura** — o que executa vs o que avalia (separação de responsabilidades)
2. **Arquivos editáveis** — lista de arquivos que o agente de melhoria PODE modificar
3. **Arquivos imutáveis** — lista de arquivos que NÃO PODEM ser modificados (avaliador, scorecard, etc.)
4. **Endpoints da API** — URLs de health, propostas, params, approve/reject
5. **Objetivos por etapa/componente** — o que cada parte deve alcançar
6. **Métricas** — como o sucesso é medido (por componente)
7. **Parâmetros ajustáveis** — qual config pode ser mudada sem mudança de código
8. **Método de deploy** — como deployar depois de mudanças de código
9. **Avaliação** — quantas runs são necessárias, como os resultados são avaliados
10. **Regras de segurança** — quais constraints nunca podem ser violadas
