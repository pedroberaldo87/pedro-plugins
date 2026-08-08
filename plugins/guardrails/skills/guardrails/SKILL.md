---
name: guardrails
description: Setup em um passo do plugin guardrails — seta a env var que o plugin não consegue carregar e remove os hooks globais hand-rolled antigos do settings.json pra não dispararem em dobro junto com os do plugin. Rode 1× por máquina depois de instalar.
---

# Guardrails Setup

Você está configurando o plugin **guardrails**. Os três hooks do plugin (lint & type-check pós-edição, scope-cop, guard de Agent Teams) vêm do próprio `hooks/hooks.json` dele e disparam automaticamente quando o plugin está instalado — você **NÃO** os registra aqui.

Este setup faz só as três coisas que um plugin **não consegue** fazer sozinho:

1. **Setar a env var** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` em `~/.claude/settings.json` (plugins não carregam env vars; o guard de Agent Teams é sobre um recurso que essa flag habilita).
2. **Remover os hooks globais hand-rolled antigos** de `~/.claude/settings.json` pra não dispararem **além dos** hooks idênticos do plugin. Sem isso, toda edição roda lint duas vezes e paga duas chamadas do juiz Haiku.
3. **Aposentar os arquivos de estado órfãos** que ficaram em `~/.claude/hooks/` junto com aqueles hooks. Eles têm o mesmo nome dos arquivos vivos do plugin (`scope-cop.mode` etc.), então editar o errado não muda nada e não avisa.

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

### 4. Aposentar os arquivos de estado órfãos

O hook antigo `~/.claude/hooks/pretooluse-scope-cop.sh` deixou os arquivos de estado dele em `~/.claude/hooks/` — com **exatamente os mesmos nomes** que o plugin usa em `~/.claude/guardrails/`. Duas armadilhas: (a) editar `~/.claude/hooks/scope-cop.mode` não muda nada e não avisa, porque o plugin lê o outro; (b) aquele script só conhece `off | deny` (testa `off` e logo depois faz `MODE=deny` incondicional), então um `warn` escrito ali significaria **deny** se ele voltasse a ser registrado.

Renomeia com sufixo `.obsoleto` — **não apaga** (é estado da máquina de quem instalou, não versionado) e não encosta no `~/.claude/guardrails/`, que é o estado vivo:

```bash
# guardrails-setup: aposenta-orfaos
# Raiz de config pela MESMA regra do lib/conformance.py e do scope-cop.sh — com $HOME
# fixo, numa máquina que seta CLAUDE_CONFIG_DIR a limpeza mexeria fora da config real.
#
# A lista abaixo é ENUMERADA, e o critério é HOMONÍMIA com o estado vivo do plugin em
# $CLAUDE_CONFIG_DIR/guardrails/: só entra o órfão cujo nome faz o usuário editar o
# arquivo inerte achando que edita o do plugin. `scope-cop.review-due` (órfão do
# sessionstart-scope-cop-review.sh.disabled) fica DE FORA de propósito: o plugin não
# tem nenhum arquivo com esse nome, então não há o que confundir, e o arquivo é estado
# de um script hand-rolled do usuário — mexer nele é decisão dele, igual ao próprio
# pretooluse-scope-cop.sh. Novo órfão só entra aqui se tiver homônimo vivo.
OLD_HOOKS="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks"
rc=0
for f in scope-cop.mode scope-cop.log scope-cop.blockstreak; do
  if [ -f "$OLD_HOOKS/$f" ]; then
    dest="$f.obsoleto"
    if [ -e "$OLD_HOOKS/$dest" ]; then
      n=1
      while [ -e "$OLD_HOOKS/$f.obsoleto.$n" ]; do n=$((n + 1)); done
      dest="$f.obsoleto.$n"
    fi
    # O "aposentado:" vira o relatório do passo 6, que o usuário lê como fato consumado —
    # então ele só pode sair se o mv realmente aconteceu, e um rename falho tem que
    # colorir a saída do bloco (senão o setup jura que desarmou uma armadilha que segue armada).
    if mv "$OLD_HOOKS/$f" "$OLD_HOOKS/$dest"; then
      echo "aposentado: $f → $dest"
    else
      echo "FALHOU aposentar: $f — segue órfão em $OLD_HOOKS" >&2
      rc=1
    fi
  fi
done
exit "$rc"
```

O bloco sai **≠ 0** se algum rename falhar (e nesse caso não imprime `aposentado:` pro arquivo que ficou) — se ele falhar, **não** reporte o passo como feito no item correspondente do passo 6: o órfão segue lá, com o mesmo nome do arquivo vivo.

Idempotente: numa segunda rodada os originais já não existem e o bloco é no-op. E se o hook antigo tiver voltado a rodar e recriado um órfão, o `.obsoleto` da rodada anterior **não** é sobrescrito — o novo vira `.obsoleto.1`, `.obsoleto.2`, … Renomear nunca pode apagar conteúdo (o `scope-cop.log` órfão real tem centenas de KB de auditoria).

### 5. Verificar

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

### 6. Recarregar e reportar

Diga ao usuário, em linguagem clara:

- Os três guardrails (lint/type-check, scope-cop, guard de Agent Teams) agora vêm do **plugin**, não de scripts soltos em `~/.claude/hooks/`. Esses scripts soltos ainda existem na máquina mas não estão mais conectados — seguro deletar depois se quiser.
- Os arquivos de estado velhos deles viraram `*.obsoleto` (renomeados, não apagados). Isso é o que impede confundir `~/.claude/hooks/scope-cop.mode` — inerte — com o que o plugin lê de verdade: `~/.claude/guardrails/scope-cop.mode`.
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` está setada.
- Um backup com timestamp do `settings.json` foi feito.
- Rode `/reload-plugins` (ou reinicie o Claude Code) pra os hooks do plugin carregarem e os hooks-settings removidos pararem de disparar.
- Check rápido de que estão vivos: `claude plugin details guardrails@pedro-plugins` deve mostrar **Hooks (2)**. Esse número conta TIPOS DE EVENTO (PostToolUse + PreToolUse), não hooks individuais — o plugin tem 3 hooks no total (1 PostToolUse + 2 PreToolUse), então **Hooks (2)** está correto e significa que carregaram. `Hooks (0)` indicaria problema (hooks.json não reconhecido).

**Não** delete os scripts antigos em `~/.claude/hooks/` automaticamente — deixe isso pro usuário.
