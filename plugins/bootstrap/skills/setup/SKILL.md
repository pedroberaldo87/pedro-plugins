---
name: bootstrap:setup
description: Setup de máquina nova em um passo — instala os marketplaces e plugins do Pedro a partir do manifest, depois aplica a config global versionada (env vars, permissões, flags de comportamento, CLAUDE.md global, statusLine resolvido pra máquina). Rode 1× por máquina depois de instalar o plugin bootstrap. Não gerencia secrets.
---

# Bootstrap Setup

Você está trazendo uma máquina pro baseline de Claude Code do Pedro. Este plugin tem **duas camadas**:

1. **Sync de plugins** (automático, via hooks) — `config/manifest.json` é a fonte da verdade dos marketplaces + plugins de terceiros; os hooks SessionStart/PostToolUse convergem o estado local pra ele (pull → apply → snapshot → push). Você não dispara isso à mão; roda sozinho.
2. **Camada de config** (sob demanda — esta skill) — aplica a config global versionada que um plugin não consegue carregar sozinho: env vars, permissões, flags de comportamento, o `CLAUDE.md` global e um `statusLine` resolvido pros paths DESTA máquina.

Este setup roda a camada de config (e cutuca o sync de plugins uma vez pra máquina ficar 100% provisionada). É **idempotente** e **nunca toca em `settings.local.json`** (que pode guardar secrets).

## Pré-requisitos

```bash
command -v jq >/dev/null || { echo "jq necessário — instale (brew install jq) e rode de novo"; exit 1; }
command -v claude >/dev/null || { echo "CLI claude necessária"; exit 1; }
```

`${CLAUDE_PLUGIN_ROOT}` é o dir do plugin `bootstrap` instalado. Resolva a partir do contexto da skill.

## Passos

### 1. Instalar marketplaces + plugins do manifest

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/apply.sh"
```

Isso adiciona cada marketplace de `config/manifest.json` e instala/habilita os plugins que ele lista. É seguro re-rodar (converge, nunca toca em plugins não-gerenciados). **Cheque o exit code** — diferente de zero significa que alguma operação falhou; investigue antes de confiar no estado.

### 2. Aplicar a camada de config global

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/apply-config.sh"
```

Isso faz merge de `config/settings-defaults.json` em `~/.claude/settings.json`:
- **env** — seta `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`, `CLAUDE_CONTEXT_THRESHOLD`, `CLAUDE_STATUSLINE_FORWARD` (os defaults vencem).
- **permissions** — UNIÃO do allow/deny existente da máquina com os defaults versionados (a máquina mantém os seus, ganha os compartilhados).
- **flags** — `language`, `theme`, `autoCompactEnabled`.
- **statusLine** — resolvido pro writer do `context-guard` instalado NESTA máquina (glob em runtime, sobrevive a bumps de versão). Exige `context-guard` instalado (o passo 1 instala).
- **CLAUDE.md** — copia `config/CLAUDE-global.md` pra `~/.claude/CLAUDE.md` (com backup).

Faz backup do `settings.json` antes e **não toca em `settings.local.json`**.

### 3. Recarregar

```bash
# Diga ao usuário pra rodar /reload-plugins (ou reiniciar o Claude Code) pra os hooks
# dos novos plugins carregarem e o settings mergeado entrar em vigor.
```

### 4. Reportar — e sinalizar o que o setup NÃO faz

Diga ao usuário, em linguagem clara:
- Quais marketplaces/plugins foram instalados e se algo falhou.
- Que o settings.json foi mergeado (env, permissões, flags, statusLine, CLAUDE.md) com backup feito.
- **Secrets NÃO são gerenciados.** Qualquer coisa máquina-específica ou secreta (passphrases de SSH, API keys, paths locais da máquina) vive em `settings.local.json` e tem que ser configurada à mão em cada máquina — ex: carregar a chave SSH no `ssh-agent`/Keychain (`ssh-add --apple-use-keychain ~/.ssh/<key>`) em vez de pôr uma passphrase na config.

## Atualizando a config versionada (a partir da máquina-fonte)

Quando o Pedro muda as permissões / env / CLAUDE.md global dele e quer propagar, re-snapshote os defaults pro repo:

```bash
# Regenera settings-defaults.json a partir do settings atual (descarta qualquer secret).
jq '{
  env: .env,
  permissions: {
    allow: [.permissions.allow[] | select(test("SSH_PASSPHRASE|PASSPHRASE";"i") | not)],
    deny: .permissions.deny,
    defaultMode: .permissions.defaultMode
  },
  language: .language, theme: .theme, autoCompactEnabled: .autoCompactEnabled
}' "$HOME/.claude/settings.json" > "$PEDRO_PLUGINS_REPO/plugins/bootstrap/config/settings-defaults.json"

cp "$HOME/.claude/CLAUDE.md" "$PEDRO_PLUGINS_REPO/plugins/bootstrap/config/CLAUDE-global.md"
```

Depois bumpe o `plugin.json`, faça commit e push — as outras máquinas pegam no próximo `/bootstrap:setup`.
