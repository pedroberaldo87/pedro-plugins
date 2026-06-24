---
name: guardrails:setup
description: Setup em um passo do plugin guardrails — seta a env var que o plugin não consegue carregar e remove os hooks globais hand-rolled antigos do settings.json pra não dispararem em dobro junto com os do plugin. Rode 1× por máquina depois de instalar.
---

# Guardrails Setup

Você está configurando o plugin **guardrails**. Os três hooks do plugin (lint & type-check pós-edição, scope-cop, guard de Agent Teams) vêm do próprio `hooks/hooks.json` dele e disparam automaticamente quando o plugin está instalado — você **NÃO** os registra aqui.

Este setup faz só as duas coisas que um plugin **não consegue** fazer sozinho:

1. **Setar a env var** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` em `~/.claude/settings.json` (plugins não carregam env vars; o guard de Agent Teams é sobre um recurso que essa flag habilita).
2. **Remover os hooks globais hand-rolled antigos** de `~/.claude/settings.json` pra não dispararem **além dos** hooks idênticos do plugin. Sem isso, toda edição roda lint duas vezes e paga duas chamadas do juiz Haiku.

É **idempotente**: rodar de novo seta uma env var já setada e acha os hooks antigos já removidos — sem dano.

## O que são "os hooks antigos"

Três entradas em `~/.claude/settings.json` → `.hooks`, todas apontando pra scripts em `~/.claude/hooks/` (ou inline):

| Evento | Matcher | Como identificar |
|---|---|---|
| `PostToolUse` | `Edit\|Write` | um hook cujo `command` contém `.claude/hooks/lint-and-typecheck` |
| `PreToolUse` | `Edit\|Write` | um hook cujo `command` contém `.claude/hooks/pretooluse-scope-cop` |
| `PreToolUse` | `Agent` | um hook `type: "prompt"` cujo `prompt` contém `substitute for Agent Teams` |

**Tem que preservar:** o hook `SessionStart` que aponta pra `sessionstart-adhd-mode.sh` (o auto-ativador do i-have-adhd — deliberadamente fora de escopo), e qualquer outro hook não-relacionado que o usuário tenha.

## Passos

### 1. Pré-requisito + sanity-check

Exige `jq` no PATH (`brew install jq` no macOS). Garanta que `~/.claude` existe e que o settings é JSON válido:

```bash
command -v jq >/dev/null || { echo "jq não encontrado — instale (brew install jq) e rode de novo"; exit 1; }
mkdir -p "$HOME/.claude"
SETTINGS="$HOME/.claude/settings.json"
[ -f "$SETTINGS" ] && { jq . "$SETTINGS" > /dev/null || { echo "settings.json não é JSON válido — abortando"; exit 1; }; }
```

### 2. Fazer backup

```bash
cp "$SETTINGS" "$SETTINGS.bak.$(date +%Y%m%d%H%M%S)"
```

### 3. Aplicar a transformação com jq

Rode este programa jq contra `~/.claude/settings.json`. Ele (a) seta a env var, (b) descarta as três entradas de hook antigas casando pelo path do command / texto do prompt, e (c) deleta os arrays `PostToolUse` / `PreToolUse` só se ficarem vazios (pra hooks não-relacionados sobreviverem).

```bash
jq '
  def strip(pred): map(select(pred | not));

  .env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = "1"

  | if .hooks.PostToolUse then
      .hooks.PostToolUse |= strip(
        ((.hooks // []) | any(.[]; (.command // "") | test("\\.claude/hooks/lint-and-typecheck")))
      )
    else . end

  | if .hooks.PreToolUse then
      .hooks.PreToolUse |= strip(
        ((.hooks // []) | any(.[];
          ((.command // "") | test("\\.claude/hooks/pretooluse-scope-cop"))
          or ((.prompt // "") | test("substitute for Agent Teams"))
        ))
      )
    else . end

  | if (.hooks.PostToolUse // []) == [] then del(.hooks.PostToolUse) else . end
  | if (.hooks.PreToolUse  // []) == [] then del(.hooks.PreToolUse)  else . end
' "$SETTINGS" > "$SETTINGS.tmp" && mv "$SETTINGS.tmp" "$SETTINGS" || { rm -f "$SETTINGS.tmp"; echo "transform falhou — settings.json intacto, .tmp removido"; exit 1; }
```

> Nota sobre `any/2`: `any(generator; condition)` roda `condition` contra cada saída de `generator`. Aqui a entrada é o array `.hooks` da entrada, o generator `.[]` produz cada objeto-hook, e a condition inspeciona o `.command` / `.prompt` daquele hook. Então uma entrada é descartada quando **qualquer** dos seus `hooks[]` parece um dos hooks antigos migrados. (Usar `.command` direto como generator tentaria indexar o array em si — errado.)

### 4. Verificar

```bash
# JSON válido?
jq . "$SETTINGS" > /dev/null && echo "settings.json OK"

# Env var setada?
jq -r '.env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS' "$SETTINGS"   # → 1

# Hooks antigos sumiram? (os três greps não devem imprimir nada)
jq -r '.hooks' "$SETTINGS" | grep -E 'lint-and-typecheck|pretooluse-scope-cop|substitute for Agent Teams' || echo "hooks antigos removidos"

# SessionStart do adhd preservado?
jq -r '.hooks.SessionStart' "$SETTINGS" | grep -q 'sessionstart-adhd-mode' && echo "hook adhd preservado"
```

### 5. Recarregar e reportar

Diga ao usuário, em linguagem clara:

- Os três guardrails (lint/type-check, scope-cop, guard de Agent Teams) agora vêm do **plugin**, não de scripts soltos em `~/.claude/hooks/`. Esses scripts soltos ainda existem na máquina mas não estão mais conectados — seguro deletar depois se quiser.
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` está setada.
- Um backup com timestamp do `settings.json` foi feito.
- Rode `/reload-plugins` (ou reinicie o Claude Code) pra os hooks do plugin carregarem e os hooks-settings removidos pararem de disparar.
- Check rápido de que estão vivos: `claude plugin details guardrails@pedro-plugins` deve mostrar **Hooks (2)**. Esse número conta TIPOS DE EVENTO (PostToolUse + PreToolUse), não hooks individuais — o plugin tem 3 hooks no total (1 PostToolUse + 2 PreToolUse), então **Hooks (2)** está correto e significa que carregaram. `Hooks (0)` indicaria problema (hooks.json não reconhecido).

**Não** delete os scripts antigos em `~/.claude/hooks/` automaticamente — deixe isso pro usuário.
