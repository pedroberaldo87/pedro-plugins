---
name: bootstrap
description: Setup de máquina nova em um passo — instala, a partir do manifest, os marketplaces de terceiros e os plugins do próprio marketplace pedro-plugins (alguns desligados de fábrica — quem diz quais é o `enabled: false` do `config/manifest.json`), depois aplica a config global versionada (env vars, permissões, flags, CLAUDE.md global, output style, statusLine resolvido pra máquina) e confere a conformidade. Rode 1× por máquina depois de instalar o plugin bootstrap. Não gerencia secrets.
---

# Bootstrap Setup

Você está trazendo uma máquina pro baseline de Claude Code deste marketplace. Este plugin tem **duas camadas**:

1. **Sync de plugins** (automático, via hooks) — `config/manifest.json` é a fonte da verdade dos marketplaces de terceiros **e** dos plugins do próprio `pedro-plugins` (dois deles, `graphify-guard` e `intent-guard`, declarados desligados); os hooks SessionStart/PostToolUse convergem o estado local pra ele (pull → apply → snapshot → push). Você não dispara isso à mão; roda sozinho. **O hook só sincroniza o que já está instalado (liga e desliga).** Marketplace de terceiro ou plugin que o manifest tem e a máquina não tem fica **pendente**: o hook avisa o usuário e o modelo, e quem instala é o passo 1 abaixo, depois do sim do usuário.
2. **Camada de config** (sob demanda — esta skill) — aplica a config global versionada que um plugin não consegue carregar sozinho: env vars, permissões, flags de comportamento, o `CLAUDE.md` global, o `outputStyle` e um `statusLine` resolvido pros paths DESTA máquina.
3. **Contrato de forma** (passivo) — o plugin distribui o output style **Clean Style** (`output-styles/clean-style.md`), ligado por `force-for-plugin: true`. (Os hooks de Stop que julgavam a última resposta foram removidos a pedido do dono em 2026-08-09 — a forma é contrato do output style, não de gate.)

Este setup roda a camada de config (e cutuca o sync de plugins uma vez pra máquina ficar 100% provisionada). É **idempotente** e **nunca toca em `settings.local.json`** (que pode guardar secrets).

## Pré-requisitos

```bash
command -v jq >/dev/null || { echo "jq necessário — instale (brew install jq) e rode de novo"; exit 1; }
command -v claude >/dev/null || { echo "CLI claude necessária"; exit 1; }
```

`${CLAUDE_PLUGIN_ROOT}` é o dir do plugin `bootstrap` instalado. Resolva a partir do contexto da skill.

## Passos

### 1. Instalar marketplaces + plugins do manifest (terceiros e os do próprio repo)

Instalar marketplace de terceiro e plugin roda código de terceiros nesta máquina (hooks, servidores MCP, skills). Por isso é em duas etapas, e a segunda só vem com o sim do usuário.

**1a. Listar o que falta.** Sem flag, o script não instala nada: sincroniza o que já está instalado e imprime uma linha `pendente:` por marketplace e por plugin do manifest que a máquina ainda não tem.

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/apply.sh"
```

Mostre a lista ao usuário em linguagem humana: o nome de cada marketplace, a origem (URL) e quantos plugins vêm dele. As origens são repositórios de terceiros, seguidos no HEAD deles, sem versão fixada; diga isso.

**1b. Instalar, só depois do sim.**

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/apply.sh" --install-new   # artigo8-ok: o harness define CLAUDE_PLUGIN_ROOT ao rodar skill de plugin
```

Adiciona cada marketplace pendente e instala os plugins que o manifest lista — os de terceiros e os do próprio `pedro-plugins` —, deixando cada um ligado ou desligado conforme o `enabled` do manifest. É seguro re-rodar: converge, e marketplace que o manifest não declara nunca é tocado. Se o usuário recusar parte da lista, não rode: ele ajusta o `enabled` ou tira a entrada do manifest primeiro.

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

**As permissões pedem CONSENTIMENTO na primeira vez, sem exceção.** Sem a marca
`~/.claude/pedro-plugins-permissions-ok`, o apply aplica env, flags e barra de status e
**segura o allow/ask/deny** — default de risco não nasce ligado (Artigo 2 da constituição
deste marketplace). Não existe anistia: um texto parecido no `settings.json` não vale como
"sim", e só esta skill grava a marca. O rito: rode a listagem, que **não escreve nada** e
mostra, entrada por entrada, o que o merge acrescenta ao seu `settings.json`, com o caminho
já resolvido para esta máquina; leia a lista ao usuário; **só com o de acordo dele** grave a
marca e rode o apply de novo:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/apply-config.sh" --listar   # artigo8-ok: o harness define CLAUDE_PLUGIN_ROOT ao rodar skill de plugin
touch ~/.claude/pedro-plugins-permissions-ok   # SÓ depois do "sim" do usuário
```

Máquina que já recebeu os defaults de uma versão antiga passa pelo mesmo rito uma vez. O
que ela já tem no `settings.json` continua lá.

**Entradas largas de versões antigas.** Os defaults antigos aprovavam `python3*`, `node*`,
`env*`, `WebFetch` e outras que rodam qualquer comando ou chegam a qualquer endereço. Como o
merge é união, elas ficam na máquina depois da atualização. O apply avisa com uma linha
`retirada do padrão:` por entrada (a listagem também mostra) e **não remove sozinho**. Se o
usuário quiser tirá-las, rode `apply-config.sh --remover-retiradas` (backup antes; só sai a
entrada com texto idêntico ao dos defaults antigos, o que o usuário escreveu fica).

Isso faz merge de `config/settings-defaults.json` em `~/.claude/settings.json`:
- **env** — seta `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`, `CLAUDE_CONTEXT_THRESHOLD`, `CLAUDE_STATUSLINE_FORWARD` (os defaults vencem).
- **permissions** — UNIÃO do allow/ask/deny existente da máquina com os defaults versionados (a máquina mantém os seus, ganha os compartilhados). Isso **liga aprovação automática** só do que está no allow abaixo; o que a skill não lista continua pedindo aprovação. O que entra, o que não entra, e por quê:

  **Entra** — o `allow`, o `ask` e o `deny` inteiros dos defaults (a contagem de hoje sai do comando
  de consentimento acima, nunca deste texto): ferramentas nativas de leitura, edição, busca na web
  e subagente · comandos de shell · chamadas do Playwright que navegam e leem a página · padrões
  destrutivos no `deny`.

  Os de shell, por família:
  - **arquivo local, git sem publicar, teste e inspeção** — o grosso: ler e escrever arquivo, git **sem `push`** (`push --force` está no `deny`), test runner, linter, inspeção de container.
  - **instala dependência** — `pip install`, `brew`.
  - **pergunta à rede, sem agir nem levar credencial** — `ping`, `dig`, `nslookup`, `host`.
  - **roda script do repositório em que a sessão estiver** — `./scripts/*`, `.venv/*`.
  - **roda os scripts dos próprios plugins, e só eles** — `python3` e `node` com o caminho do script preso ao cache deste marketplace (a pasta `plugins/cache/pedro-plugins/` dentro da config do Claude Code). A regra casa pelo texto do comando, então ela fixa o interpretador **e** o caminho: o interpretador seguido do caminho de um script dentro desse cache roda; `python3 -c` e um script em `/tmp` pedem aprovação. Duas guardas no `ask` fecham os desvios: um `..` no caminho (que sairia do cache) e escrita dentro do cache (que plantaria um script e o deixaria aprovado). Foi medido num Claude Code real: o caminho direto roda, `..` e `$(…)` no argumento pedem aprovação.

  **Não entra, de propósito** — tudo que **age fora desta máquina, toca credencial ou roda código que o modelo escreveu na hora**; quem quiser aprova na hora:
  - **publica ou entrega** — `git push`, `scp`, `rsync`, `deploy.sh`.
  - **fala com serviço remoto usando o token já guardado** — `gh` (aprovaria `gh repo delete`), `npm` (aprovaria `npm publish` com a credencial do registry), `psql` (age em banco remoto), `ssh`.
  - **executa código arbitrário baixado na hora** — `npx`, `wget`, `curl`.
  - **grava credencial** — `ssh-add`, `supabase` (o CLI faz `login` e age no projeto remoto).
  - **interpretador solto** — `python*`, `node*`, `perl*`, `bun*`: `python3 -c` lê um segredo local e o envia com o cliente HTTP da própria linguagem, e nenhuma regra por nome de comando enxerga isso.
  - **embrulho que roda o argumento como comando** — `env*`, `printenv*` (lista as variáveis, tokens inclusos), `xargs*`, `timeout*`, e `find*`, `sed*`, `awk*` sem restrição.
  - **rede e código no navegador, sem destino fixo** — `WebFetch` (a busca na web, `WebSearch`, segue liberada) e, no Playwright, `browser_run_code`, `browser_evaluate` e `browser_file_upload`.

  **Não entra porque o casamento é por PREFIXO** — `source` e toda entrada que começa por atribuição de variável (`TOKEN=*`, `SKEY=*`, `URL=*`, `SUPABASE_*`, `PROJECT_REF=*`, `DOCKER_HOST=*`, `PYTHONPATH=*`). `Bash(source*)` aprova `source /qualquer/coisa`, e `Bash(TOKEN=*)` aprova **qualquer** comando escrito depois da atribuição — ou seja, reabre o allow inteiro. Medido em 2026-08-05 num allow que tinha `Bash(TOKEN=*)` e não tinha `sqlite3`: `sqlite3 --version` foi bloqueado e `TOKEN=x sqlite3 --version` rodou sem pedir aprovação.

  O teste `hooks/test_bootstrap_hooks.sh` reprova a volta de qualquer entrada dessas classes, não só das que já saíram.

  Confira os números antes de rodar:

  ```bash
  python3 -c "import json,sys;p=json.load(open(sys.argv[1]))['permissions'];a=p['allow'];print('allow',len(a),'| nativas',sum(1 for x in a if not x.startswith(('Bash(','mcp__'))),'| Bash',sum(1 for x in a if x.startswith('Bash(')),'| mcp',sum(1 for x in a if x.startswith('mcp__')),'| deny',len(p['deny']))" "${CLAUDE_PLUGIN_ROOT}/config/settings-defaults.json"
  ```

  O `defaultMode` **não** vem nos defaults: o modo de aprovação continua o que já estava nesta máquina.
- **flags** — `language`, `theme`, `autoCompactEnabled`, `outputStyle` (fixa `"Clean Style"`; sem
  isso o teto de prosa não entra no prompt de sistema e só o Stop hook barra, depois do fato).
- **statusLine — uma CADEIA de dois elos, não um comando.** O `statusLine.command` chama o **escritor** (`context-guard`, glob de versão em runtime), que grava o percentual de contexto da sessão e **encaminha** para o que estiver em `CLAUDE_STATUSLINE_FORWARD` — o **renderizador**, hoje o `claude-hud`. Os dois são entradas do manifest, então o passo 1 instala ambos. Se o writer não for achado, o script avisa e deixa o `statusLine` como está.

  ⚠️ **Trocar o `statusLine.command` sem mover o antigo para o forward mata o elo de trás em silêncio.** Foi o que aconteceu nesta máquina: o comando passou a chamar o `claude-hud` direto, o writer saiu da cadeia, e **nenhuma sessão real gravou o percentual por 3 dias** — o único `/tmp/claude-context-pct-*` existente era um fixture de teste. A tela continuava perfeita, porque quem sumiu foi o elo que produz dado para **outro** consumir: o guarda do context-guard, que sem esse arquivo nunca dispara.

  ⏱️ **A barra também ganha um relógio (`statusLine.refreshInterval: 10`).** Quem redesenha a barra é o harness, e por padrão ele só redesenha em **evento** (tecla, turno, troca de modelo): com o trabalho correndo em segundo plano e ninguém digitando, a linha do motor congela no valor da última tecla. Essa chave é a única alavanca do nosso lado — o próprio schema do `settings.json` a descreve como *"re-run the status line command every N seconds in addition to event-driven updates"*. 10 s porque a duração é contada em segundos, então ela muda visivelmente sem pôr a cadeia inteira de pé a cada segundo.

  Quem cobra isso agora é `conformance.py:check_statusline_meio_ligada` — plugin de statusLine habilitado e ausente da cadeia (comando **ou** forward) vira desvio nomeado, com o conserto junto. Mesma família do `check_gates_enganosos`.
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
# Regenera só env e flags a partir do settings atual (descarta qualquer secret).
# As PERMISSÕES NÃO são regeneradas: o settings da máquina carrega entradas que não podem
# virar padrão (interpretador solto, embrulho, WebFetch, git push, ssh-add, scp, rsync,
# supabase, npx, wget, atribuição de variável...) e o caminho absoluto desta máquina onde
# os defaults têm {{CLAUDE_DIR}}. O bloco `permissions` do arquivo versionado é editado à
# mão, e o teste de allow proibido (hooks/test_bootstrap_hooks.sh) cobra o resultado.
# defaultMode fica de fora de propósito: modo de aprovação é escolha de cada máquina.
DEFS="$PEDRO_PLUGINS_REPO/plugins/bootstrap/config/settings-defaults.json"   # artigo8-ok: PEDRO_PLUGINS_REPO é o clone do dono, documentado no README
jq --slurpfile cur "$DEFS" '{
  env: .env,
  permissions: $cur[0].permissions,
  language: .language, theme: .theme, autoCompactEnabled: .autoCompactEnabled,
  outputStyle: .outputStyle
}' "$HOME/.claude/settings.json" > "$DEFS.novo" && mv "$DEFS.novo" "$DEFS"

cp "$HOME/.claude/CLAUDE.md" "$PEDRO_PLUGINS_REPO/plugins/bootstrap/config/CLAUDE-global.md"
```

Depois bumpe o `plugin.json`, faça commit e push — as outras máquinas pegam no próximo `/bootstrap:setup`.
