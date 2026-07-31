---
name: context-guard:setup
description: Configura o plugin context-guard — registra o wrapper de statusLine e as env vars no settings.json (os hooks de reset/guarda vêm do próprio plugin via hooks.json). Rode 1× após instalar o plugin.
---

# Setup do Context Guard

Você está configurando o plugin context-guard, que interrompe o workflow quando o uso do context window passa de um threshold, avisando pra preservar o estado da sessão.

## Arquitetura

São três componentes — e **só um precisa de setup manual**:

1. **Wrapper de statusLine** (`hooks/context-guard-writer.sh`) — intercepta o JSON de stdin do Claude Code, extrai `context_window.used_percentage` + `session_id`, grava em `/tmp/claude-context-pct-<session_id>` (**por sessão**, v1.3.0) e encaminha pro statusLine que já existia (via `CLAUDE_STATUSLINE_FORWARD`). **Precisa do setup** — statusLine não pode ser um hook de plugin, então tem que ir no `settings.json`.
2. **Hook PostToolUse** (`hooks/context-guard.sh`) — lê o arquivo DA PRÓPRIA sessão após cada tool call e bloqueia com `{"decision":"block"}` se passar do threshold. **Vem do plugin** (`hooks/hooks.json`) — NÃO registre à mão.
3. **Hook SessionStart** (`hooks/context-guard-reset.sh`) — limpa o sentinel e o estado **só da própria sessão** pra guarda poder disparar de novo em sessão nova. **Vem do plugin** (`hooks/hooks.json`) — NÃO registre à mão.

> **Por que por-sessão (v1.3.0):** antes o estado era um arquivo global (`/tmp/claude-context-pct`). Com várias sessões paralelas, a última statusLine a renderizar sobrescrevia o arquivo, então UMA sessão a 80% fazia o guard bloquear TODAS — falso-positivo em massa. Agora cada sessão só lê o próprio contexto.

**Por que só o statusLine vai no settings.json:** os hooks de reset/guarda já são entregues pelo `hooks/hooks.json` do plugin e disparam sozinhos quando o plugin está instalado — registrá-los de novo no `settings.json` seria redundante (o sentinel por sessão neutraliza o disparo duplo, mas é peso à toa, e dois registros do mesmo hook é exatamente o tipo de coisa que o plugin `guardrails` existe pra desfazer). O **statusLine**, ao contrário, não existe como hook de plugin — é o único que precisa entrar no `settings.json`. Por isso o setup faz só isso (+ env vars).

> **Caso directory-source (sem cache):** se o plugin vier de um marketplace de diretório local cujo cache não existe, o `hooks.json` (que usa `${CLAUDE_PLUGIN_ROOT}`) também não carrega — nem os hooks de reset/guarda. Aí instale via marketplace **git** (gera cache) pra os hooks funcionarem; o setup cobre só o que o `settings.json` sempre suporta (statusLine + env).

## Passos

### 1. Resolver o caminho do plugin

Ache a raiz do context-guard dinamicamente:

```bash
# Instalado de marketplace git
PLUGIN_PATH=$(ls -d ~/.claude/plugins/cache/*/context-guard/*/ 2>/dev/null | tail -1)
```

Valide que o caminho existe e contém `hooks/context-guard-writer.sh`. Guarde como `PLUGIN_PATH`.

### 2. Ler o settings atual

Leia `~/.claude/settings.json`. Cheque o que já existe:
- Tem `statusLine.command`? (salve o original — vamos preservá-lo via forward)
- `CLAUDE_CONTEXT_THRESHOLD` no `env`?
- `CLAUDE_STATUSLINE_FORWARD` no `env`?

### 3. Configurar o statusLine

Se já houver um `statusLine.command`, salve-o como `CLAUDE_STATUSLINE_FORWARD` no `env` pra o wrapper encaminhar pra ele.

Então defina `statusLine.command`:
```json
"statusLine": {
  "type": "command",
  "command": "bash <PLUGIN_PATH>/hooks/context-guard-writer.sh"
}
```

O wrapper extrai o context% E encaminha o stdin pro comando original — qualquer statusLine que já existia (claude-hud ou outro) continua funcionando.

### 4. Adicionar env vars

Adicione ao `env` do settings.json (se ainda não estiver):
```json
"CLAUDE_CONTEXT_THRESHOLD": "80"
```

Se havia um statusLine original (passo 3), adicione também:
```json
"CLAUDE_STATUSLINE_FORWARD": "<comando original do statusLine>"
```

### 5. Verificar

Confirme que o wrapper extrai o context% e que o guard do plugin dispara como esperado:

O estado é **por sessão** (`/tmp/claude-context-pct-<session_id>`) — cada sessão só lê o próprio contexto (ver Arquitetura). Nos testes, use um session_id fixo:

```bash
SID=test-0000; rm -f /tmp/claude-context-pct-$SID /tmp/claude-context-warned-$SID
# Wrapper extrai o context% pro arquivo DA SESSÃO
echo "{\"session_id\":\"$SID\",\"context_window\":{\"used_percentage\":45,\"context_window_size\":200000}}" | bash <PLUGIN_PATH>/hooks/context-guard-writer.sh > /dev/null 2>&1
cat /tmp/claude-context-pct-$SID  # deve imprimir: 45

# Guard NÃO dispara abaixo do threshold
echo "{\"session_id\":\"$SID\"}" | CLAUDE_CONTEXT_THRESHOLD=80 bash <PLUGIN_PATH>/hooks/context-guard.sh   # sem saída

# Guard DISPARA acima do threshold
printf '85' > /tmp/claude-context-pct-$SID
echo "{\"session_id\":\"$SID\"}" | CLAUDE_CONTEXT_THRESHOLD=80 bash <PLUGIN_PATH>/hooks/context-guard.sh   # {"decision":"block","reason":"⚠️ CONTEXTO EM …%"}

rm -f /tmp/claude-context-pct-$SID /tmp/claude-context-warned-$SID
```

Valide a sintaxe do settings.json:
```bash
jq . ~/.claude/settings.json > /dev/null
```

Confirme que os hooks do plugin carregaram:
```bash
claude plugin details context-guard@pedro-plugins   # deve mostrar Hooks (2)
```
`Hooks (2)` conta tipos de evento (SessionStart + PostToolUse) — correto. `Hooks (0)` = o `hooks.json` não foi reconhecido (problema — provável caso directory-source sem cache).

### 6. Reportar

Diga ao usuário:
- Context guard ativo, threshold em X%.
- Os hooks de reset/guarda vêm do **plugin** (`hooks.json`) — o setup registrou só o statusLine + env vars no `settings.json` (sem duplicar hooks).
- Pra mudar o threshold: edite `CLAUDE_CONTEXT_THRESHOLD` no `env` do `~/.claude/settings.json`.
- A guarda dispara UMA vez por sessão, depois deixa continuar (pra você rodar /handoff).
- **Kill-switch:** `echo off > ~/.claude/context-guard/mode` desliga o guard **globalmente na hora** (sem editar settings nem reload); apague o arquivo (ou `echo on`) pra religar. Útil quando você roda muitas sessões paralelas e quer silêncio.
- **Estado por sessão:** o context% de cada sessão vive em `/tmp/claude-context-pct-<session_id>` — uma sessão cheia NÃO bloqueia as outras (bug corrigido na v1.3.0, quando o estado era global).
- Se havia statusLine antes, foi preservado via `CLAUDE_STATUSLINE_FORWARD`.
- Rode `/reload-plugins` ou reinicie o Claude Code pra recarregar a config.
