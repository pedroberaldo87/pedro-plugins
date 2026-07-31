---
name: bootstrap:setup
description: Setup de máquina nova em um passo — instala, a partir do manifest, os marketplaces de terceiros e os plugins do próprio marketplace pedro-plugins (dois deles desligados de fábrica), depois aplica a config global versionada (env vars, permissões, flags, CLAUDE.md global, output style, statusLine resolvido pra máquina) e confere a conformidade. Rode 1× por máquina depois de instalar o plugin bootstrap. Não gerencia secrets.
---

# Bootstrap Setup

Você está trazendo uma máquina pro baseline de Claude Code deste marketplace. Este plugin tem **duas camadas**:

1. **Sync de plugins** (automático, via hooks) — `config/manifest.json` é a fonte da verdade dos marketplaces de terceiros **e** dos plugins do próprio `pedro-plugins` (dois deles, `graphify-guard` e `intent-guard`, declarados desligados); os hooks SessionStart/PostToolUse convergem o estado local pra ele (pull → apply → snapshot → push). Você não dispara isso à mão; roda sozinho.
2. **Camada de config** (sob demanda — esta skill) — aplica a config global versionada que um plugin não consegue carregar sozinho: env vars, permissões, flags de comportamento, o `CLAUDE.md` global, o `outputStyle` e um `statusLine` resolvido pros paths DESTA máquina.
3. **Contrato de forma** (passivo) — o plugin distribui o output style **Clean Style** (`output-styles/clean-style.md`) e o Stop hook `stop-prose-ceiling.py`. Os dois nascem ligados: o style por `force-for-plugin: true`, o hook por estar em `hooks/hooks.json`.

Este setup roda a camada de config (e cutuca o sync de plugins uma vez pra máquina ficar 100% provisionada). É **idempotente** e **nunca toca em `settings.local.json`** (que pode guardar secrets).

## Pré-requisitos

```bash
command -v jq >/dev/null || { echo "jq necessário — instale (brew install jq) e rode de novo"; exit 1; }
command -v claude >/dev/null || { echo "CLI claude necessária"; exit 1; }
```

`${CLAUDE_PLUGIN_ROOT}` é o dir do plugin `bootstrap` instalado. Resolva a partir do contexto da skill.

## Passos

### 1. Instalar marketplaces + plugins do manifest (terceiros e os do próprio repo)

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/apply.sh"
```

Isso adiciona cada marketplace de `config/manifest.json` e instala os plugins que ele lista — os de terceiros e os do próprio `pedro-plugins` —, deixando cada um ligado ou desligado conforme o `enabled` do manifest. É seguro re-rodar: converge, e marketplace que o manifest não declara nunca é tocado.

**Desinstalar é opt-in.** Plugin que está num marketplace gerenciado mas não aparece no manifest só é removido quando o ambiente tem `BOOTSTRAP_UNINSTALL_UNMANAGED=1` (e aí com `--keep-data`). Sem a variável o script apenas **LISTA** o que seria removido e não mexe em nada. Plugin do `pedro-plugins` fica fora dessa varredura em qualquer caso.

**Cheque o exit code** — diferente de zero significa que alguma operação falhou; investigue antes de confiar no estado.

### 2. Conferir a conformidade

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/conformance.py"
```

Compara o estado VIVO da máquina contra o contrato versionado e **não escreve nada** —
decisão registrada em 2026-07-30: *"Mostra o desvio, você decide."* Sai `0` quando está
tudo conforme, `1` quando há desvio. Nunca bloqueia.

O que ele confere:

- **plugins** — `enabledPlugins` do `settings.json` contra o `manifest.json`. Pega o caso
  em que alguém religou na mão um plugin que o manifest manda desligar.
- **CLAUDE.md** — se a cópia da máquina divergiu do `CLAUDE-global.md`. Mostra o que só
  existe de cada lado e **não prescreve direção**: o sync só anda repo → máquina, então
  regra escrita direto na máquina some no próximo `apply-config.sh`.
- **teto de tamanho** — mais de uma regra numérica de linhas no CLAUDE.md. Foi a
  causa-raiz da verbosidade: três tetos válidos ao mesmo tempo, e o mais permissivo vence.
- **output style** — `output-styles/clean-style.md` presente, com `force-for-plugin: true` e
  `keep-coding-instructions: true`, e o plugin `bootstrap` habilitado (sem ele o estilo
  não carrega).
- **skills** — o que está em `~/.claude/skills` contra `skills.permitidas` do manifest.
  Acusa skill que apareceu sem ser declarada.
- **hooks** — ferramenta com `PreToolUse` de mais de um plugin habilitado. Compara por
  **ferramenta**, não pela string do matcher (`Grep|Glob|Bash` e `Grep|Glob|Bash|Agent`
  colidem em três ferramentas e a comparação textual não veria).
- **dependência externa** — plugin habilitado cujo binário exigido não está na
  máquina (ex: `graphify-guard` sem o comando `graphify`). Só cobra quando o plugin
  que precisa está LIGADO — quem não usa não é incomodado.
- **gates meio-ligados** — arquivo `.mode` marcado `off` com o plugin dele ainda
  habilitado. Faz parecer que existe trava onde não existe.

Reporte os desvios ao usuário em linguagem humana e **espere a decisão dele** — este passo
nunca conserta sozinho.

### 3. Aplicar a camada de config global

⚠️ **A cópia do CLAUDE.md é de mão única, repo → máquina.** O `snapshot.sh` regenera o
manifest mas **não** traz o CLAUDE.md de volta. Regra escrita direto em `~/.claude/CLAUDE.md`
some aqui — foi o que quase custou 4 regras em 2026-07-30. O `conformance.py` (passo 2)
roda ANTES deste passo: ele mostra o que só existe de cada lado, sem prescrever direção.

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/apply-config.sh"
```

Isso faz merge de `config/settings-defaults.json` em `~/.claude/settings.json`:
- **env** — seta `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`, `CLAUDE_CONTEXT_THRESHOLD`, `CLAUDE_STATUSLINE_FORWARD` (os defaults vencem).
- **permissions** — UNIÃO do allow/deny existente da máquina com os defaults versionados (a máquina mantém os seus, ganha os compartilhados). O `defaultMode` **não** vem nos defaults: o modo de aprovação continua o que já estava nesta máquina, e o setup nunca liga aprovação automática.
- **flags** — `language`, `theme`, `autoCompactEnabled`, `outputStyle` (fixa `"Clean Style"`; sem
  isso o teto de prosa não entra no prompt de sistema e só o Stop hook barra, depois do fato).
- **statusLine** — resolvido pro writer do `context-guard` instalado NESTA máquina (glob em runtime, sobrevive a bumps de versão). Exige `context-guard` instalado — ele é uma das entradas do marketplace `pedro-plugins` no manifest, então o passo 1 instala. Se mesmo assim não achar, o script avisa e deixa o `statusLine` como está.
- **CLAUDE.md** — copia `config/CLAUDE-global.md` pra `~/.claude/CLAUDE.md` (com backup).

Faz backup do `settings.json` antes e **não toca em `settings.local.json`**.

### 4. Ferramentas externas dos plugins

Alguns plugins deste marketplace dependem de binário que o marketplace **não** instala.
O passo 2 já acusa (área `dependencia`) quando o plugin está ligado e o comando falta.

Hoje há um: **`graphify`** (pacote `graphifyy`, MIT), exigido pelo `graphify-guard`.

```bash
command -v graphify >/dev/null || echo "uv tool install graphifyy   # ou: pipx install graphifyy"
```

Sem ele o `graphify-guard` fica **decorativo**: ele procura `graphify-out/graph.json` pra
redirecionar busca cega, e nada na máquina cria esse diretório. O guarda existe, não
reclama, e não protege — o mesmo tipo de estado meio-ligado que o passo 2 caça.

**Não instale por conta própria.** Ofereça o comando ao usuário e explique o que ele
destrava; quem decide o que entra na máquina é ele. Se ele não usa grafo, o caminho certo
é desligar o `graphify-guard` no manifest, não instalar o binário.

### 5. Recarregar

```bash
# Diga ao usuário pra rodar /reload-plugins (ou reiniciar o Claude Code) pra os hooks
# dos novos plugins carregarem e o settings mergeado entrar em vigor.
```

### 6. Reportar — e sinalizar o que o setup NÃO faz

Diga ao usuário, em linguagem clara:
- Quais marketplaces/plugins foram instalados e se algo falhou.
- Que o settings.json foi mergeado (env, permissões, flags, statusLine, CLAUDE.md) com backup feito.
- **Secrets NÃO são gerenciados.** Qualquer coisa máquina-específica ou secreta (passphrases de SSH, API keys, paths locais da máquina) vive em `settings.local.json` e tem que ser configurada à mão em cada máquina — ex: carregar a chave SSH no `ssh-agent`/Keychain (`ssh-add --apple-use-keychain ~/.ssh/<key>`) em vez de pôr uma passphrase na config.

## Atualizando a config versionada (a partir da máquina-fonte)

Quando o usuário muda as permissões / env / CLAUDE.md global da máquina-fonte e quer propagar, re-snapshote os defaults pro repo:

```bash
# Regenera settings-defaults.json a partir do settings atual (descarta qualquer secret).
# defaultMode fica DE FORA de propósito: modo de aprovação é escolha de cada máquina,
# não contrato versionado.
jq '{
  env: .env,
  permissions: {
    allow: [.permissions.allow[] | select(test("SSH_PASSPHRASE|PASSPHRASE";"i") | not)],
    deny: .permissions.deny
  },
  language: .language, theme: .theme, autoCompactEnabled: .autoCompactEnabled,
  outputStyle: .outputStyle
}' "$HOME/.claude/settings.json" > "$PEDRO_PLUGINS_REPO/plugins/bootstrap/config/settings-defaults.json"

cp "$HOME/.claude/CLAUDE.md" "$PEDRO_PLUGINS_REPO/plugins/bootstrap/config/CLAUDE-global.md"
```

Depois bumpe o `plugin.json`, faça commit e push — as outras máquinas pegam no próximo `/bootstrap:setup`.
