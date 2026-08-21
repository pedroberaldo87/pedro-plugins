---
generated: 2026-08-16
generated-commit: 7793362
project: pedro-plugins
scope:
  - plugins/project-skills/hooks/sessionstart-doc.sh
  - plugins/project-skills/hooks/sessionstart-organism.sh
  - plugins/project-skills/hooks/pretooluse-plan-gate.sh
  - plugins/project-skills/hooks/userpromptsubmit-plan-escape.sh
  - plugins/project-skills/hooks/posttooluse-doc-read.sh
  - plugins/project-skills/hooks/lib-project-root.sh
  - plugins/project-skills/hooks/doc-detect.sh
  - plugins/project-skills/hooks/hooks.json
  - plugins/bootstrap/hooks/session-sync.sh
  - plugins/bootstrap/hooks/lib/apply.sh
  - plugins/bootstrap/hooks/lib/apply-config.sh
  - plugins/bootstrap/lib/cfgjson.py
  - plugins/bootstrap/hooks/lib/snapshot.sh
  - plugins/bootstrap/hooks/lib/git-sync.sh
  - plugins/bootstrap/hooks/hooks.json
  - plugins/bootstrap/lib/conformance.py
  - plugins/bootstrap/config/manifest.json
  - plugins/visual/server/visual_server.mjs
  - plugins/visual/server/start.sh
  - plugins/visual/skills/visual/resolve-dir.sh
  - plugins/visual/skills/visual/SKILL.md
  - plugins/visual/skills/visual/template.html
  - plugins/visual/hooks/pre-exitplan-visualize.sh
  - plugins/project-skills/hooks/sessionstart-plan.sh
  - plugins/project-skills/hooks/stop-plan-status.sh
  - plugins/visual/hooks/stop-anuncio-sem-acao.py
  - plugins/visual/hooks/hooks.json
  - plugins/project-skills/lib/plan_state.py
  - plugins/project-skills/lib/cobertura.py
  - plugins/project-skills/lib/doc_load.py
  - plugins/project-skills/hooks/lib-doc-mark.sh
  - plugins/project-skills/skills/doc-load/SKILL.md
  - plugins/project-skills/skills/start/SKILL.md
  - plugins/project-skills/skills/sprint/SKILL.md
  - plugins/guardrails/hooks/lint-and-typecheck.sh
  - plugins/guardrails/hooks/scope-cop.sh
  - plugins/guardrails/hooks/hooks.json
  - scripts/hook_contract.py
  - plugins/ship/hooks/pre-deploy-test-check.sh
  - plugins/ship/hooks/hooks.json
  - plugins/ship/skills/ship/SKILL.md
  - plugins/context-guard/hooks/context-guard.sh
  - plugins/context-guard/hooks/context-guard-writer.sh
  - plugins/context-guard/hooks/context-guard-reset.sh
  - plugins/context-guard/hooks/hooks.json
  - plugins/handoff/hooks/sessionstart-ata.sh
  - plugins/handoff/hooks/hooks.json
  - plugins/graphify-guard/hooks/sessionstart-graphify.sh
  - plugins/graphify-guard/hooks/pretooluse-graphify-guard.sh
  - plugins/graphify-guard/hooks/hooks.json
  - _shared/sessionstart-deps.sh
  - plugins/bootstrap/hooks/sessionstart-deps.sh
  - plugins/project-skills/hooks/posttooluse-andamento.sh
  - plugins/project-skills/lib/andamento.py
  - plugins/gauntlet/hooks/hooks.json
  - plugins/gauntlet/hooks/pretooluse-gauntlet.sh
  - plugins/lixeiro/hooks/hooks.json
  - .claude/stop-budget.baseline.json
  - plugins/slides/skills/slides/SKILL.md
  - plugins/slides/skills/slides/scripts/check_fidelity.py
  - AGENTS.md
  - GEMINI.md
  - .cursorrules
  - .windsurfrules
  - .github/copilot-instructions.md
verified-by:
  - plugins/bootstrap/hooks/test_bootstrap_hooks.sh
  - plugins/bootstrap/lib/test_conformance.py
  - plugins/project-skills/hooks/test_plan_gate.sh
  - plugins/project-skills/hooks/test_plan_hooks.sh
  - plugins/visual/hooks/test_anuncio_sem_acao.py
  - scripts/test_hook_contract.py
  - plugins/visual/hooks/test_exitplan_gate.sh
  - plugins/project-skills/lib/test_plan_state.py
  - plugins/project-skills/lib/test_cobertura.py
  - plugins/project-skills/lib/test_doc_load.py
  - plugins/project-skills/lib/test_spec_to_plan_skill.py
  - plugins/project-skills/lib/test_start_doc_skill.py
  - plugins/project-skills/lib/test_travas_motor.py
  - plugins/project-skills/lib/test_motor_bancada.py
  - plugins/ship/hooks/test_pre_deploy.sh
  - plugins/project-skills/lib/test_andamento.py
  - plugins/project-skills/hooks/test_andamento_hook.sh
  - plugins/project-skills/skills/sprint/references/motor.js
  - plugins/project-skills/lib/test_motor_js.py
  - plugins/gauntlet/hooks/test_gauntlet_hooks.sh
  - plugins/lixeiro/hooks/test_lixeiro_hooks.sh
doc-sig: pedro-plugins/sessionstart-doc.sh@gen=3.8#14bde3c1

# Runtime — fluxos ponta-a-ponta

Este doc descreve **o que acontece em execução**. Estrutura do repo está em `architecture.md`; convenções de código, em `patterns.md`.

**Rótulos:** `[confirmado]` = lido ou executado neste run · `[inferido]` = deduzido do código, não executado · `[relatado]` = veio de comentário/doc do próprio repo e não foi executado aqui.

**Contagem de hooks — DERIVE, não copie.** O número muda a cada plugin tocado; o que vale é o comando, não o dígito de ontem:

```bash
python3 - <<'EOF'
import json, glob, collections
ev = collections.Counter(); scripts = set()
for f in sorted(glob.glob('plugins/*/hooks/hooks.json')):
    for e, bl in json.load(open(f))['hooks'].items():
        for b in bl:
            for h in b['hooks']:
                ev[e] += 1; scripts.add(h.get('command', ''))
print(dict(ev), 'TOTAL', sum(ev.values()), '·', len(scripts), 'comandos distintos')
EOF
```

⚠️ **Registro ≠ script ≠ execução, e os três números divergem de propósito.** Um script pode estar em dois eventos (`project-skills/hooks/posttooluse-andamento.sh` está em `Pre` **e** `PostToolUse`), e os scripts viram muito menos execuções úteis: a maioria dos registros de `SessionStart` chama o mesmo `sessionstart-deps.sh`, que fala **uma vez por sessão** e sai calado nas outras — ver fluxo 7.0.

⚠️ Isso mede o que o repo **oferece**. O que **roda** é a interseção com `enabledPlugins` do `~/.claude/settings.json`, e quem desliga de fábrica é o manifest — a lista sai dele, nunca de prosa (o comando está no fluxo 7). `[confirmado — varredura dos hooks.json e leitura do manifest nesta rodada]`
---

## 1 · Ciclo de sync do bootstrap (pull → apply → snapshot → commit/push)

**Dispara quando:** `SessionStart`, via `plugins/bootstrap/hooks/hooks.json` → `${CLAUDE_PLUGIN_ROOT}/hooks/session-sync.sh`, **sem `timeout` declarado**. `[confirmado]`

**Passos** (todos em `session-sync.sh` salvo indicação):

1. **Guarda de reentrância** — sai calado se `PEDRO_PLUGINS_HOOK_RUNNING` já está setada; senão exporta `PEDRO_PLUGINS_HOOK_RUNNING=session-sync`. Impede que o PostToolUse `post-plugin-command.sh` (matcher `Bash`) re-dispare o ciclo enquanto ele roda `claude plugin install`. `[confirmado]`
2. **Lock por diretório** — `mkdir "$LOCK_DIR"` em `$HOME/.claude/plugins/.pedro-plugins-sync.lock` (atômico via POSIX, sem `flock`). Lock com mais de 300s é quebrado com `rmdir`. `trap … EXIT INT TERM` libera. Segunda sessão concorrente sai calada. `[confirmado]`
3. **Checagem barata de remoto** — com `$PEDRO_PLUGINS_REPO/.git` presente (`HAS_SOURCE=1`): `git fetch --quiet`, compara `HEAD` com `@{u}` e só marca `REMOTE_ADVANCED=1` se `merge-base --is-ancestor` provar que o remoto está **à frente**, não meramente divergente. Sem repo-fonte, faz o equivalente no cache `~/.claude/plugins/marketplaces/pedro-plugins`. `[confirmado]`
4. **Throttle** — se o remoto não avançou, `PEDRO_PLUGINS_FORCE_SYNC` está vazia e o mtime de `~/.claude/plugins/.pedro-plugins-last-sync` é mais novo que `PEDRO_PLUGINS_THROTTLE_SECONDS` (default `86400`), sai. `[confirmado]`
5. **Pull** — `git pull --rebase --autostash`. Saída casando `conflict|cannot pull` → `rebase --abort` e sai. Falha não-conflito **com `REMOTE_ADVANCED=1`** → aborta **sem** tocar o timestamp, pra próxima sessão tentar na hora. `[confirmado]`
6. **Apply** — `hooks/lib/apply.sh`. Localiza o manifest na primeira das 5 origens: repo-fonte → `${CLAUDE_PLUGIN_ROOT}/config/manifest.json` → `../../config/manifest.json` relativo ao script → cache do marketplace → glob `~/.claude/plugins/cache/pedro-plugins/bootstrap/*/config/manifest.json`. Converge em 4 etapas: `claude plugin marketplace add` dos faltantes → `claude plugin install` → `claude plugin uninstall` → `claude plugin enable/disable`. O estado atual vem de parsear `claude plugin list` com `awk` (blocos `❯ nome@mkt` + `Status:`), deduplicado por `sort -u`. `[confirmado]`
7. **Portão anti-propagação** — `apply.sh` sai com o **número de operações falhas** (`255` = fatal, cap em `200`). Qualquer exit ≠ 0 → `session-sync.sh` **pula o snapshot** e ainda assim faz `touch` no timestamp. `[confirmado]`
8. **Snapshot** — `hooks/lib/snapshot.sh` regenera `plugins/bootstrap/config/manifest.json` a partir de `claude plugin list` + `known_marketplaces.json`, imprime `unchanged`/`changed` no stdout e log no stderr. `[confirmado]`
9. **Commit + push** — só com `SNAPSHOT_STATUS = "changed"`. `hooks/lib/git-sync.sh` faz `git add` e `git commit --only` **apenas** de `plugins/bootstrap/config/manifest.json`, mensagem `chore(plugins): sync <YYYY-MM-DD>`. Push rejeitado (`rejected|non-fast-forward`) → `pull --rebase --autostash` + um retry. `[confirmado]`

**Termina em:** `touch ~/.claude/plugins/.pedro-plugins-last-sync` e `exit 0`. Neste run o arquivo existe com mtime de hoje 18:56 — o ciclo rodou. `[confirmado — `ls -la`]`

### 1a · A remoção é opt-in dos dois lados

- **`apply.sh`, etapa 3** — o laço que decide o que remover é **puro**: monta `UNINSTALL_CANDIDATES`/`UNINSTALL_CANDIDATE_COUNT` sem efeito nenhum. Os `claude plugin uninstall … --keep-data` só rodam dentro de `if [ "${BOOTSTRAP_UNINSTALL_UNMANAGED:-0}" = "1" ]`. Sem a variável, imprime `ℹ desinstalação DESLIGADA — N plugin(s) seriam removidos: …` e não mexe em nada. Racional no cabeçalho do arquivo: a marketplace oficial entrega centenas de plugins e o manifest declara um punhado — sem guarda, um `SessionStart` desinstalaria tudo que o manifest não nomeia. `[confirmado]`
- **`snapshot.sh`, união aditiva** — depois de montar o manifest novo, faz `group_by(.name)` entre plugins antigos e a amostra atual (`if length > 1 then .[1] else .[0] end`: a amostra nova vence no `enabled`, a entrada ausente **fica**) e loga `warning: manifest encolheu X -> Y` se ainda assim diminuir. O comentário do bloco registra a causa: `claude plugin list` devolve saída incompleta de forma intermitente. `[confirmado — código lido; a intermitência é `[relatado]`, não remedida neste run]`
- Consequência prática: desinstalar de verdade é **edição explícita** do manifest de um lado, `BOOTSTRAP_UNINSTALL_UNMANAGED=1` do outro.

### 1b · Chave de topo escrita à mão sobrevive por inversão da lista

`snapshot.sh` declara `GENERATED_KEYS='["version","description","marketplaces"]'` — o que ele **gera** — e preserva com `with_entries(select(.key … | index($k) | not))` toda chave de topo fora dessa lista. As chaves do manifest atual, listadas mecanicamente por `jq -r 'keys[]'`: `description`, `ferramentas_externas`, `marketplaces`, `skills`, `version`. `[confirmado]`

### 1c · Números do manifest (jq neste run)

```
marketplaces ................. 8
entradas de plugin ........... 48   (31 enabled · 17 disabled)
entradas de pedro-plugins .... 19
desligadas em pedro-plugins .. graphify-guard, intent-guard
```

`[confirmado — `jq` sobre plugins/bootstrap/config/manifest.json nesta rodada]`

### Se falhar no passo N

- **2** (outro sync ativo) → sai calado; só aparece com `PEDRO_PLUGINS_VERBOSE`.
- **5** (conflito de pull) → log em stderr mandando `cd $PEDRO_PLUGINS_REPO && git status`; nada mais roda.
- **6** (`jq` ou `claude` ausentes, manifest inválido/ausente) → `exit 255`; `session-sync` loga "apply teve erro fatal — snapshot pulado".
- **7** (N operações falharam) → estado local preservado, sem snapshot e sem push. Retry: `PEDRO_PLUGINS_FORCE_SYNC=1 bash plugins/bootstrap/hooks/session-sync.sh`.
- **9** (push rejeitado ou sem rede) → commit local fica. `git-sync.sh` sai **sempre** 0 — erro de git aqui nunca derruba a sessão. `[confirmado]`

> ⚠️ O ciclo roda `git pull --rebase --autostash` no repo-fonte **em toda abertura de sessão**. Trabalho não-commitado em `pedro-plugins` passa pelo autostash. `[inferido — não reproduzido neste run]`

**Verificado:** `bash plugins/bootstrap/hooks/test_bootstrap_hooks.sh` → **70 ok · 0 FAIL** neste run, incluindo o round-trip do snapshot ("pedro-plugins continua com N plugins", "graphify-guard continua desligado", "2a rodada e idempotente"). `[confirmado]`

---

## 2 · Roteamento cross-tool para o CLAUDE.md

**Dispara quando:** outra ferramenta de IA (Codex, Gemini CLI, Cursor, Windsurf, Copilot) abre o repo e carrega o arquivo de instrução que ela conhece.

**Os ponteiros na raiz deste repo**, listados por `ls -a`: `AGENTS.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules`, `.github/copilot-instructions.md`. `[confirmado]`

**Conteúdo real, copiado literal:**

```
AGENTS.md / GEMINI.md  (mesmo bloco de 3 passos)
  1. Read `CLAUDE.md` for the project index — it contains the stack, critical
     gotchas, and a documentation routing table
  2. Based on your current task, read the relevant docs from `docs/` …
  3. Each doc entry includes "→ read when" hints …

.cursorrules / .windsurfrules / .github/copilot-instructions.md  (par de 2 linhas)
  Read `CLAUDE.md` at the project root for the project index and documentation routing table.
  Detailed docs by concern are in `docs/` — load only what's relevant to the current task.
```

O índice carrega o marker `<!-- project-doc:v2 gen=3.8 -->` na primeira linha. `[confirmado — `head -1 .claude/CLAUDE.md`]`

> ⚠️ **Os 5 ponteiros mandam ler `CLAUDE.md` "at the project root", e este repo NÃO tem `CLAUDE.md` na raiz** — o índice vive em `.claude/CLAUDE.md`. `[confirmado — `ls CLAUDE.md` → "No such file or directory"]`
>
> O Claude Code acha o índice sozinho (`.claude/CLAUDE.md` é convenção nativa). Cursor/Copilot/Codex/Gemini seguem a instrução literal, não acham nada na raiz e caem em varredura. **Os ponteiros estão inertes fora do Claude Code neste repo.** Correção: criar `CLAUDE.md` na raiz — `doc-detect.sh:find_claude_md` já prefere a raiz quando ela carrega o marker — ou reescrever os 5 ponteiros pro caminho real.

---

## 3 · Ponte StatusLine ↔ arquivo de estado do context-guard

**Dispara quando:** o Claude Code renderiza a statusLine e, do outro lado, em **todo** `PostToolUse` (o `hooks.json` do context-guard não declara `matcher`). Ambos com `timeout 5`. `[confirmado]`

**Passos:**

1. **Escrita** — `context-guard-writer.sh` recebe o JSON da statusLine em stdin, extrai `.context_window.used_percentage` e `.session_id` via `jq` e grava o percentual cru em `/tmp/claude-context-pct-<session_id>`. Sem `session_id` → não grava (fail-safe). `[confirmado]`
2. **Encaminhamento** — com `CLAUDE_STATUSLINE_FORWARD` setada, repassa o mesmo stdin: `printf '%s' "$INPUT" | eval "$CLAUDE_STATUSLINE_FORWARD"`. `[confirmado]`
3. **Leitura** — `context-guard.sh` lê `/tmp/claude-context-pct-<session_id>`, trunca o decimal (`PCT_INT="${PCT%.*}"`) e compara com `CLAUDE_CONTEXT_THRESHOLD` (default `80`). `[confirmado]`
4. **Disparo** — acima do threshold, emite `{"decision":"block","reason":"⚠️ CONTEXTO EM N%. Rode o /handoff AGORA …"}` e cria o sentinel `/tmp/claude-context-warned-<session_id>` (1× por sessão). `[confirmado]`
5. **Não interromper handoff em curso** — antes de tudo, testa `(.tool_input // {} | tostring) | test("handoff"; "i")`; casando, marca o sentinel e sai. `[confirmado]`
6. **Kill-switch** — `~/.claude/context-guard/mode` contendo `off` desliga o guard globalmente. `[confirmado]`
7. **Reset** — `context-guard-reset.sh` (SessionStart) apaga **só** os dois arquivos da própria sessão e faz prune de órfãos com `find /tmp -maxdepth 1 -name 'claude-context-pct-*' -mtime +1 -delete` (idem `-warned-`). `[confirmado]`

> ✅ **A ponte foi LIGADA em 2026-08-02, e ela ficou quebrada 3 dias sem ninguém notar.** Até então `statusLine.command` apontava direto pro `claude-hud` e **não continha `context-guard-writer`**: sem o wrapper na cadeia ninguém escrevia `/tmp/claude-context-pct-<sid>`, e o único arquivo desse padrão em `/tmp` era `claude-context-pct-smoke-123` — **fixture de teste**, de 30/jul. O `context-guard.sh` saía em `[ -z "$PCT" ] && exit 0` toda vez.
>
> O conserto pôs o comando antigo **inteiro** em `CLAUDE_STATUSLINE_FORWARD` (preservando o cálculo de `COLUMNS`, que se perderia num forward remontado à mão) e o writer em `statusLine.command`. E2E com o payload do harness: writer gravou `73` e o hud renderizou `Context 73%` na mesma passada. `[confirmado nesta rodada]`
>
> 🔴 **A lição não é o conserto, é o tempo que levou.** Este bloco já descrevia o defeito **antes** desta rodada, e ele continuou lá — porque documentar um estado quebrado não conserta nem avisa de novo. Agora quem cobra é `conformance.py:check_statusline_meio_ligada`: plugin de statusLine habilitado e ausente da cadeia vira desvio a cada execução do verificador. Ver `patterns.md §1.14` — elo que produz dado para outro consumir sai de cena sem sintoma nenhum na tela.

- **Passo 3, `jq` ausente** → `command -v jq … || exit 0` no topo: o guard nem lê o stdin. `[confirmado]`

---

## 4 · Live-sync do /visual e o gate no ExitPlanMode

**Dispara quando:** (a) o usuário invoca `/visual`, ou (b) o portão único de `ExitPlanMode` (fluxo 8) **chama** `plugins/visual/hooks/pre-exitplan-visualize.sh` e ele bloqueia um plano. ⚠️ **O `visual` deixou de se registrar nesse evento** — `plugins/visual/hooks/hooks.json` declara hoje apenas `Stop` e `SessionStart`, e o script do gate segue no disco como **peça chamada**, não como hook. Quem prova é `python3 scripts/hook_contract.py --responde ExitPlanMode`. `[confirmado]`

**Passos:**

1. **Resolução do diretório** — `plugins/visual/skills/visual/resolve-dir.sh` aplica uma cascata de 3: raiz git (`git rev-parse --show-toplevel`) → ancestral com marcador, parando antes de `$HOME` e de `/` → **reserva** `~/Desktop/claude-<sub>/<pasta-de-origem>-<cksum-do-caminho>`. Os marcadores, copiados literal do script: `package.json`, `CLAUDE.md`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `graphify-out/`, `.git`. O alvo é `<dir>/.claude/<sub>`, onde `<sub>` é o **2º argumento** (default `visual`; o motor de plano passa `plans`; a skill do `/archify` passa `archify`). O diretório é criado com `mkdir -p` antes de imprimir. **Duas regras que só existem por causa da reserva:** a gaveta é POR PASTA DE ORIGEM — sem o `<pasta>-<id>` toda pasta sem marcador caía no mesmo pote e uma sessão via o plano de outro projeto como se fosse dela —, e o aviso viaja no **código de saída 3** (0 = veio de projeto), porque todo consumidor chama com `2>/dev/null` e avisar só no stderr é avisar no vazio. **O `<sub>` pode ter barra** (`docs/fluxos` → `<raiz>/.claude/docs/fluxos`); na reserva a barra vira traço (`claude-docs-fluxos`), senão a gaveta por origem se parte em duas e `claude-docs` volta a ser pote comum. `[confirmado — `_shared/resolve-dir.sh` e `plugins/visual/skills/visual/test_resolve_dir.sh`]` **Fonte única: `_shared/resolve-dir.sh`**, vendorada — quem chama sempre chama uma cópia dela (a skill do `/visual` a sua; `plan_state.py:resolve_dir` a irmã em `plugins/project-skills/lib/resolve-dir.sh`, resolvida por `dirname(__file__)`). Editar a cópia em vez do original é o drift que `scripts/sync-shared.sh --check` acusa. `[confirmado — `diff` entre as cópias e leitura de `resolve_dir`]`
2. **Token de sessão** — a página injeta `<script>window.VISUAL_SESSION = "<token>";</script>` logo depois de `<body>`; o servidor valida contra `SESSION_RE = /^[a-zA-Z0-9_-]{4,64}$/`. `[confirmado — `visual_server.mjs`; formato do token em `SKILL.md`, seção "Live sync via claude-visual-server"]`
3. **Subir o daemon** — `${CLAUDE_PLUGIN_ROOT}/server/start.sh` pinga `http://127.0.0.1:$PORT/ping` com `curl -sf --max-time 1`; respondeu, sai. Senão exige `node` no PATH e sobe `nohup env CLAUDE_VISUAL_PORT="$PORT" node visual_server.mjs &` + `disown`, esperando até 8 × `sleep 0.25`. Porta: `CLAUDE_VISUAL_PORT`, default `7755`. `[confirmado]`
4. **Daemon** — `plugins/visual/server/visual_server.mjs`, Node stdlib puro, escuta em `127.0.0.1`. Rotas: `GET /ping` → `{status,pid,port}`; `POST /state` com body `{session, docTitle?, state}`; `GET /state?session=<id>`. Corpo acima de `MAX_BODY_SIZE` (256 KB) → HTTP 413. `EADDRINUSE` → `process.exit(0)` silencioso. Auto-desligamento por ociosidade em `IDLE_TIMEOUT_MS` (30 min), checado a cada minuto. `[confirmado]`
5. **Escrita de estado** — no `POST /state`, valida a sessão, monta `{session, timestamp, docTitle, state}` e grava `~/.claude/visual-state/<session>.json` **e** `~/.claude/visual-state/latest.json` (mesmo registro + campo `stateFile`). Sessão fora do regex → HTTP 400 `invalid-session`, nada gravado, sem path traversal. `[confirmado]`
6. **Leitura pelo Claude** — o Claude lê `~/.claude/visual-state/latest.json`; ausente ou com mais de 30 min → volta pro copy/paste. `[confirmado — regra na SKILL.md, seção de live sync]`

**Estado nesta máquina:** o daemon **não está no ar** agora (`curl http://127.0.0.1:7755/ping` falhou) e `latest.json` existe com mtime de 30/jul 22:32. **Implementado, ocioso.** `[confirmado]`

**Passo 0, desde 2026-08-02: o spec passa pela régua de forma antes de virar HTML.** `visual_page.py:validate` roda `erros_de_estilo()` sobre todo campo de texto — título, corpo, pergunta, aviso, sumário — e devolve **todos** os erros de uma vez. Estourar é `exit 2` **sem escrever arquivo**, então o passo 1 nem começa. As quatro checagens e a calibração estão em `patterns.md §2.7`. Três isenções declaradas: `evidencia.output`, `raw_html` e o texto de dentro do bloco `esquema` (o desenho é do programa; o spec traz só o conteúdo, e aí o que se cobra é a FORMA do dado — tipo conhecido, lista cheia, seta apontando pra caixa que existe). `[confirmado — `visual_page.py:validate`; `test_visual_page.py` cobre com 27 checks na seção "régua de estilo — prosa proibida"]`

**Passo 0b2, desde 2026-08-09: o parecer do juiz de clareza vira PÁGINA PRÓPRIA, e sai sem perguntar.** Terminada a leitura (passo 0b), a receita manda montar um spec com **um item por decisão julgada** — o que estava sendo pedido para escolher, a diferença entre as opções, ENTENDI ou PERDIDO, e a palavra que perdeu — buildar com `slug` `parecer-<slug-da-página-julgada>` e abrir. **São duas páginas, nunca uma:** despejar o veredito no chat o deixa sem onde ser aprovado, e misturá-lo com a página julgada esconde a reprovação dentro do que ela reprovou. Quem impede a mistura não é a receita e sim o build (`patterns.md §2.5a`). `[confirmado — `plugins/visual/skills/visual/SKILL.md`, passos 0b2 e 8 do checklist]`

**Passo 0c, desde 2026-08-21: página que pede aprovação de DOCUMENTO abre com desenho, não com texto.** A `SKILL.md` passou a exigir um bloco `esquema` **antes** do bloco `aprovacao`, e traz a tabela de qual dos seis tipos serve a cada documento da casa da doc (`quality-goals.md` → `escada`, `constraints.md` → `quadrantes`, `journeys.md` → `fluxo`, `glossary.md` → `glossario`, `features.md` e `constituicao.md` → `placar`, e assim por diante); documento fora da lista escolhe pela FORMA do conteúdo, nunca pelo nome. O `doc_integral` continua obrigatório — o de acordo é sobre o texto, e o desenho existe para que lê-lo seja conferência e não descoberta. ⚠️ **A regra é de PROSA, e o que o programa cobra é a presença dela**: `visual_page.py` não sabe qual documento está sendo aprovado, então quem vigia é `test_visual_page.py`, que exige a seção, a frase da ordem e o vocabulário de cada tipo e de cada documento mapeado — é a parte que some primeiro quando alguém reescreve a seção. `[confirmado — a seção "Página de aprovação de documento — o esquema vem ANTES do texto" em `plugins/visual/skills/visual/SKILL.md` e o bloco final de `test_visual_page.py`, que saiu `249 passou · 0 falhou` nesta rodada]`

⚠️ **A página aberta no navegador não sabe que ficou velha.** A aba mostra o arquivo de quando foi aberta, e nada na tela denuncia — em 2026-08-02 um bloco aparecia expandido numa aba de 8 horas antes, com o arquivo já corrigido no disco. O daemon sincroniza **browser → disco** (estado de rádio e textarea), nunca o contrário: **não há recarga automática**. Antes de tratar o que se vê na tela como defeito do gerador, confira o HTML no disco. `[confirmado — `restoreState()` no `template.html` mexe em rádios e textareas, nunca em `details.open`]`

### 4a · O gate do ExitPlanMode, condição por condição

`pre-exitplan-visualize.sh` — kill-switch `VISUAL_GATE=0` na primeira linha; `command -v jq` logo abaixo; sem `session_id` → `exit 0`. Cap de **3** devoluções por (sessão, projeto), chaveado por `${TMPDIR:-/tmp}/claude-visual-gate-$(id -u)-${SESSION_ID}-${PHASH}` com `PHASH` = `cksum` do diretório resolvido. `[confirmado]`

- **Procura o visual da sessão** — `find "$VISUAL_DIR" -maxdepth 1 -name "*sess-${SESSION_SHORT}*.html" -mmin -5`, com `SESSION_SHORT="${SESSION_ID:0:8}"`.
- **Gate de prova** — conta com `grep -c` os marcadores `class="decision-card`/`class="feedback-item` (DECIDE), `class="evidencia"`/`class="artefato"`/`<pre` (PROVA), `class="evidencia vazio` (VAZIO) e `visual-sem-evidencia:` (ISENTO). Bloqueia com `exit 2` se `DECIDE>0 && ISENTO==0 && (PROVA==0 || VAZIO>0)`.
  - ⚠️ **`class="feedback-item pt-phase` fica FORA da conta de DECIDE** (`grep … | grep -vc`). É o veredito de fase que o próprio `plan_state.py page --mode approve` desenha — controle de aprovação de trabalho que ainda **não** aconteceu, não conclusão afirmada. Contá-lo fazia o gate barrar exatamente a página que ele manda gerar duas telas abaixo, e o modelo ficava preso entre duas ordens do mesmo arquivo. `[confirmado — `pre-exitplan-visualize.sh`, e a suíte nova cobre o caso]`
  - ✅ **O marcador de PROVA sobreviveu à troca do bloco de prova para `<details>`**: `visual_page.py:r_evidencia` emite `<details class="evidencia">` (com ` open` quando cabe), e o `grep` do gate procura `class="evidencia"` — casa nas duas formas. `[confirmado — leitura do emissor e do gate nesta rodada]`
  - ⚠️ **O texto de conserto que o gate imprime passou a ensinar um JSON que o `init` ACEITA.** Ele mandava escrever fases e passos só com `desc`; o validador recusa o arquivo inteiro sem `requisito` e `pronto` em toda tarefa nova. Hoje os dois blocos de instrução (o caminho "sem plano em arquivo" e o "sem visual nenhum") trazem o exemplo com o bloco `requisitos` no topo e os quatro campos por passo. `[confirmado]`
- **Gate de arquivo de plano** — roda `plan_state.py --dir "$PLANS_DIR" open --json`; saída vazia ou `[]` → `HAS_PLAN_FILE=0` e `exit 2` mandando rodar `init`. Sem `python3` ou sem o script, `HAS_PLAN_FILE=1` (não cobra).
- **Sem visual nenhum** → `exit 2` com o conteúdo literal de `.tool_input.plan` no stderr e o filename sugerido `<YYYY-MM-DD>-sess-<8char>-plan.html`.

🔴 **Este gate deixou de ser um dos três que disputavam o `ExitPlanMode`.** Hoje ele é a **segunda peça** do portão único descrito no fluxo 8: quem se registra no evento é `plugins/project-skills/hooks/pretooluse-plan-gate.sh`, e é ele que chama este script por nome de plugin, depois do gate de pedido. Consequência prática para quem debuga: **`VISUAL_GATE=0` continua calando esta peça**, mas o portão inteiro só se desliga com `PLAN_PORTAO_UNICO=0` — e um `pre-exitplan-visualize.sh` que nunca fala pode estar mudo por não ter sido chamado, não por não ter achado defeito. `[confirmado — leitura do laço `for PECA` no portão]`

**Verificado nesta rodada:** `bash plugins/visual/hooks/test_exitplan_gate.sh` → **OK (12 checks)** — fecha com kill-switch e fail-open (*"VISUAL_GATE=0 cala tudo"*, *"sem session_id, não bloqueia"*). A suíte que exercita os dois hooks de plano mudou de casa junto com eles: `bash plugins/project-skills/hooks/test_plan_hooks.sh`. `[confirmado — as duas rodadas]`

---

## 5 · Ciclo de vida de um plano de implementação

**Onde mora:** `<raiz-do-projeto>/.claude/plans/<id>.plan.json`, versionado no git de propósito — `/tmp` e `${CLAUDE_PLUGIN_ROOT}` morrem no `/clear` e no bump de versão. `[confirmado — docstring de `plan_state.py`]`

**A regra estrutural:** o Claude **autora** o plano uma vez (`init`) e daí em diante só **marca** (`tick`). Quem desenha a árvore é o programa, lendo o arquivo — por isso o título não deriva entre renders. `[confirmado]`

**Duas portas cobram o plano, e elas cobrem casos opostos.** ⚠️ **As duas mudaram de dono nesta rodada** — a família de projeto (`plugins/project-skills/hooks/`) passou a ser a casa dos dois lados `[confirmado — `ls` do diretório e o `hooks.json` do plugin]`:

- **Antes do plano existir** — `PreToolUse[ExitPlanMode]`, hoje via o portão único (`pretooluse-plan-gate.sh`), que chama `visual/hooks/pre-exitplan-visualize.sh` e exige arquivo de plano + HTML com prova. Só arma **se você entrar em plan mode**.
- **Depois do trabalho acontecer** — `Stop` (`plugins/project-skills/hooks/stop-plan-status.sh`, no bloco da cobrança de plano ausente) cobra o plano **ausente**: sessão que editou ≥ `PISO` arquivos **distintos** e não tem nenhum plano ativo recebe o aviso uma vez, com sentinela própria (`claude-plan-missing-…`).

O segundo nasceu de um buraco medido: **7 commits em 2026-08-02 sem plano nenhum, e nada acusou** — porque o gate antigo só dispara em plan mode, e trabalho feito direto nunca passa por lá.

⚠️ **A métrica é ARQUIVO distinto, não chamada de edição** (`arquivos_editados()`, linha 82, compartilhada pelas duas cobranças). O caminho antigo contava `"name":"Edit"` no transcript e a frase dizia *"editou N arquivos"* — 6 edições no mesmo arquivo imprimiam *"editou 6 arquivos"*. A mensagem mentia. `[confirmado — `test_plan_hooks.sh` → `OK (57 checks)`, com o caso "6 edições no MESMO arquivo não cobram" e três sabotagens]`

**Verbos** (os **11** subparsers de `plan_state.py:build_parser`): `init`, `tick`, `state`, `render`, `page`, `brief`, `cobertura`, `reabrir`, `open`, `close`, `reopen`. Os dois últimos a entrar são `cobertura` (o mapa entre requisito e tarefa, nos dois sentidos) e `reabrir` (derruba uma decisão que o agente tomou no lugar do dono). `[confirmado — leitura de `build_parser` nesta rodada]`

**As duas árvores.** `render` e `page` aceitam `--vista execucao|valor`. A de execução é fase → tarefa, a de sempre; a de **valor** é épico → requisito → grupo → tarefa e é **derivada em tempo de render**, não guardada — o arquivo só conhece fase→tarefa, e os dois níveis de cima vêm do documento de requisitos. A vista entra no nome do arquivo da página (`plano-<id>-<modo>-valor.html`), então as duas convivem sem uma sobrescrever a outra. `[confirmado — `plan_state.py:cmd_render`, `cmd_page` e `_html_valor`]`

**De onde vêm os requisitos** — cascata de `plan_state.py:_requisitos_do_projeto`, nesta ordem: bloco `requisitos` no topo do próprio plano → variável `PLAN_REQS` apontando um arquivo → `<raiz>/docs/PRD.md` → `<raiz>/docs/REQUISITOS.md` → nenhum. **Nenhum não é erro**: sem documento, a checagem de citação simplesmente não roda. O bloco no plano vem primeiro por ser o mais específico. `[confirmado]`

### Os quatro símbolos de maior fan-in

- **`PlanError`** — a exceção única do módulo. `main()` a captura, escreve a mensagem no stderr e devolve **2**; qualquer outra exceção sobe como traceback. Todo caminho de recusa do módulo passa por ela: JSON inválido, plano inexistente, `resolve-dir.sh` ausente ou mudo, `template.html` não encontrado, tique de fase, tique sem prova, `state … done`, renomear sem `--rename`. É o motivo de um hook conseguir tratar "plano recusado" por exit code, sem parsear texto. `[confirmado]`
- **`resolve_dir(cwd=None)`** — delega ao `resolve-dir.sh` irmão (`os.path.dirname(__file__)`, hoje `plugins/project-skills/lib/`) com o 2º argumento `plans`, **em vez de reimplementar a cascata em Python**. Se o script sumir ou não devolver caminho, levanta `PlanError` mandando passar `--dir`. É essa delegação que garante que `/visual` e o store de planos nunca resolvam projetos diferentes — **enquanto as cópias vendoradas de `_shared/resolve-dir.sh` estiverem em dia**, o que `bash scripts/sync-shared.sh --check` responde. `[confirmado]`
- **`pick_plan(directory, plan_id=None)`** — resolve *qual* plano. Com id, abre `<id>.plan.json` ou levanta `PlanError`. Sem id, exige exatamente **um** plano com `status == "active"`: zero levanta `nenhum plano ativo`, dois ou mais levanta `há N planos ativos (…) — diga qual`. Adivinhar aqui é como o plano se perde, e o código recusa adivinhar. Chamado por `tick`, `state`, `render`, `page`, `close` e `reopen`. `[confirmado]`
- **`plan_progress(plan)`** — percorre `iter_items` e devolve `(feitos, total)` contando `status == "done"`. É a métrica única: alimenta o texto do `tick`, o `close` (que decide entre `done` e `abandoned`), o `summary`, os bullets do `brief`, a barra `.pt-fill` do HTML e os chips da página. Fase **não tem estado próprio** — `phase_status` também é derivada dos passos, porque estado duplicado é estado que diverge. `[confirmado]`

### Travas do arquivo

- **`erros_do_plano` acumula, `validate` levanta.** A checagem de forma é uma função que **devolve a lista** (`plan_state.py:erros_do_plano`) e uma casca fina que a transforma em `PlanError` único (`plan_state.py:validate`). A separação existe porque quem MARCA precisa distinguir defeito da própria tarefa de defeito alheio, e a exceção derruba tudo junto. Ids: fase casa `^F\d+$`, passo casa `^F\d+\.\d+$` e o prefixo tem que bater com a fase. `desc` é obrigatório em cada passo e tem teto de `DESC_MAX = 140` chars — é a linha didática que aparece na árvore. `STATUSES = ("todo","doing","blocked","done")`. `[confirmado]`
- **Dois campos são cobrados só em tarefa NOVA** — o parâmetro `exigir` de `erros_do_plano` recebe o conjunto de ids que estão entrando, e para esses exige `requisito` (o id do requisito que a tarefa atende, **exatamente um**) e `pronto` (como se prova que ela terminou). Tarefa que já existia no arquivo não é cobrada retroativamente, então o campo novo não invalida plano em andamento. `[confirmado]`
- **Citação a requisito inexistente RECUSA gravar.** `validate` recebe `reqs` e, para cada tarefa com `requisito` preenchido, exige que o id exista no documento — a mensagem de erro lista os ids conhecidos. `reqs` vazio **desliga a checagem**, porque projeto sem documento de requisitos é o caso comum, não um defeito. `[confirmado]`
- **A regra do destrave é UMA função, `plan_state.py:pendencia_viva`, e todo lado que julga pendência a chama** — quem RECUSA o tique (`cmd_tick`), quem DESENHA a linha de baixo do item (`_detalhe`) e, desde 2026-08-15, a varredura de largada do `/sprint`, que a **importa** em vez de reescrevê-la (a seção deste doc logo abaixo, "o plano é LIDO antes de a corrida acender"). Enquanto eram duas cópias, o renderizador olhava só a `pendencia` e anunciava **⛔ falta decidir sobre passo já destravado**; três passos do plano real (`F14.5`, `F16.6`, `F17.1`) apareciam travados com a decisão gravada desde o dia anterior. **É essa árvore que o motor lê como fila**, então ele gastava o tier caro diagnosticando por que passos com resposta "não saíam do lugar" — o mesmo padrão da chave de sentinel computada em dois lugares (`patterns.md` §1.6). ⚠️ **`escolha` nula não destrava**: `str(None)` devolve a palavra `"None"`, que é texto não-vazio, então gravar "não escolhi" liberava o tique — o `or ""` é o que separa ausência de escolha de escolha vazia. `[confirmado — `test_plan_state.py` → **367** asserções `ok` nesta rodada, com os 8 casos da fronteira]`
- **O tique de RETOMADA cobra mais prova que os outros (2026-08-20).** `tick … --retomada` é como se marca passo cujo trabalho já estava no disco antes da corrida — o que o detector de órfão achou na largada. Quem marca não estava lá quando aquilo saiu, então a `evidencia` tem de trazer as **duas** coisas do rito feito à mão: o veredito de quem revisou (a prova casa `revis…` e `aprov…`) e o **sha** do commit (7 a 40 hex). Faltando uma, `cmd_tick` recusa **dizendo qual falta** e dá o modelo da linha; sem a bandeira, o tique segue com o teto de sempre. É o único lugar do módulo em que o rigor da prova depende de QUEM viu o trabalho sair. `[confirmado — `plan_state.py:cmd_tick`, bloco `F18.3 · R-28`, e a bandeira `--retomada` no `build_parser`]`
- **A ordem entre passos virou ARESTA gravada, e ela é recusada na gravação (2026-08-21).** O campo `depende` do passo — lista de ids de PASSO ao lado de `requisito` (`"depende": ["F11.1"]`) — diz *o outro termina antes deste começar*. `plan_state.py:_erros_das_dependencias` entra em `erros_do_plano`, então id inexistente, auto-referência, id repetido e **ciclo** derrubam o `init` em vez de virar aviso: quem escreve o JSON é o modelo, e aresta apontando pro nada apodrece calada igual ao `requisito` inexistente. **Fase não entra**: `F1` é pasta, não trabalho — quem quer travar a fase lista os passos dela. O ciclo é a única guarda com algoritmo (varredura em profundidade com marca cinza/preto) e a recusa nomeia o **anel inteiro** (`ciclo — F1.1 → F2.1 → F1.2 → F1.1`), porque saber que há ciclo sem saber onde cortá-lo não conserta nada. Do outro lado, `cmd_tick` recusa marcar passo cuja dependência ainda não está `done`, nomeando o que falta — decisão do dono em 2026-08-16, *"Recusar, sempre"*. Plano sem `depende` grava exatamente como antes. `[confirmado — `test_plan_state.py` (bloco `R-36`) → `OK` nesta rodada; as duas travas têm mutação declarada em `test_mutacao_plano.py` (`P` e `Q`)]`
- **`pendencia` trava o tique, e quem destrava é o REGISTRO.** Enquanto a pergunta estiver em aberto, `cmd_tick` recusa com *"tem decisão em aberto"*. O que resolve é `decidido` com uma `escolha` preenchida — **apagar a `pendencia` deixou de ser o caminho**, e essa era a trava permanente: o `merge` preservava o campo omitido, então a pendência voltava no `init` seguinte e a tarefa nunca mais passava. A pergunta continua gravada de propósito; é dela que o `reabrir` vive. `plan_state.py:cmd_reabrir` faz o caminho de volta — devolve a pergunta ao campo `pendencia`, remove o `decidido` e joga a tarefa de volta pra `todo`, pra que toda decisão tomada na ausência do dono seja reversível por construção. `[confirmado — `plan_state.py:cmd_tick`, leitura nesta rodada]`
- **`merge`** mantém o que é **estado** (`status`, `evidence`, `done_at`) e trava o que é **identidade**: título diferente com o mesmo id é conflito e o `init` é recusado, salvo `--rename <id> "<título>"`. Nó que existia no arquivo e não veio no `init` é **mantido**, com aviso. `[confirmado]`
- **A regra do `merge` virou UMA só: o que o `init` não trouxe vem do arquivo.** Valia para uma lista fixa de campos no nó e para `created`/`status` no topo — e por isso o segundo `init` apagava, calado, o bloco `requisitos` (a fonte que as tarefas citam, e com ela o portão que recusa citação para o nada), o `closed_at` e o `detail` da fase. Hoje a preservação vale para **toda chave de topo** e inclui o `detail`, que é o único lugar do 🔧 Como / 💡 Por quê / 📁 Toca em. **Apagar de propósito é declarar a chave vazia** (`"requisitos": []`) — o merge só preenche o ausente. `[confirmado — `plan_state.py:merge`]`
- **`init` recusa `status: "done"` com prova abaixo de `EVIDENCE_MIN`.** Quem escreve o JSON do `init` é o modelo, e sem isso "concluído" entrava à mão com `evidence` nula — o mesmo palpite que o `tick` recusa. O teto da prova é o mesmo dos dois lados, senão há dois. `[confirmado — `plan_state.py:erros_do_plano`]`
- **Desde 2026-08-15, PLANO `done` com passo sem marcar também é recusado — e a recusa cospe os ids.** Plano encerrado some da listagem de planos abertos; gravado `done` à mão com passos que ninguém provou, ele leva esses passos junto para fora da vista, e nada mais os cobra. Quem encerra é `close`, que só escreve `done` quando todo passo está marcado com `tick <id> --evidencia`; à mão, `erros_do_plano` lista até 8 ids pendentes na mensagem. `[confirmado — `plan_state.py:erros_do_plano`, ramo `pst == "done"`]`
- **A branch e a worktree do trabalho passaram a MORAR no plano (`frente`), porque não pertenciam a nada.** Bloco opcional no topo, ao lado de `phases`: `{"branch": …, "worktree": …}`. Ele é **tudo ou nada** — meio-gravado (branch sem worktree, ou o contrário) daria uma frente que o fechamento não sabe encerrar, então `_erros_da_frente` cobra os dois campos juntos; projeto que trabalha na própria árvore grava a raiz do repositório como worktree. Quem consome são três superfícies: a árvore de texto (`render_text` abre com a linha `🌿 frente: …`), a página HTML (`render_html`, como **cartão de fechamento**, com `git worktree remove` e `git branch -d` já escritos) e o `close`, que avisa que **fechar o plano não fecha a branch** e nomeia qual. A frase da decisão é **uma constante única** (`FRENTE_DECIDA`), usada pelo aviso e pelo cartão — duas redações da mesma decisão envelheceriam separadas, que é a armadilha do §1.6 de `patterns.md`. Quem OFERECE a frente é o passo 4 da skill `plan`, e a recusa do dono se grava em `limites` para que a oferta se cale nas rodadas seguintes. **Desde 2026-08-15 o cartão chega também à página de fim de missão do `/sprint`, nos TRÊS desfechos** — a skill manda o relatório INCLUIR a árvore do plano (`plan_state.py page <planId>`) em vez de descrever o plano em prosa, justamente porque missão que **parou** é a que deixa a branch viva na máquina; plano sem `frente` gravada não ganha cartão e nada se inventa no lugar. **Desde 2026-08-20 (R-42) a frente ganhou escrivão e ciclo de vida próprios:** o comando `plan_state.py frente <plano> <branch> <worktree>` grava o par (cartório idempotente, tudo-ou-nada — a mesma régua de `_erros_da_frente`), e `frente <plano> --encerrar` o remove no passo (7) do rito de fechamento. Para missão de `/sprint` a frente **deixou de ser opcional**: a casca abre `frente/<id-do-plano>` a partir da main, monta a worktree em `~/.claude/worktrees/<repo>/<id>`, passa a **worktree como `repoRoot`** do motor (o plano e os tiques ficam na árvore principal — se morassem na worktree, fechar a frente descartaria o placar), fecha com o rito 2b (tag `rescue/`, merge da main na frente, suíte de novo, `--no-ff` na main, remove worktree e branch, `--encerrar`) e varre órfãs de missões passadas com `scripts/frente_orfa_check.py` (aviso, nunca bloqueio — de propósito fora do release-gate). ⚠️ A oferta do passo 4 do `plan` e a recusa gravada em `limites` continuam escritas na skill `plan`, mas a largada obrigatória do `/sprint` **não consulta essa recusa** — os dois contratos hoje dizem coisas diferentes sobre o mesmo plano. `[confirmado — `plan_state.py:_erros_da_frente`, `cmd_frente`, `cmd_close`, `render_text`, `render_html` (bloco `pt-frente-fechar`); `plugins/project-skills/skills/plan/SKILL.md` passo 4 e as seções "A frente da missão abre antes do primeiro executor", o rito 2b/2c da Persistência e "A frente aberta sai na página, nos três desfechos (R-20)" de `skills/sprint/SKILL.md`, nesta rodada]`
- **Plano ilegível DIZ qual arquivo e qual erro.** `plan_state.py:le_plano` é a única porta de leitura e converte `OSError`/JSON inválido em `PlanError` com o caminho e a causa, em vez de traceback com rc=1. Quem LISTA (`list_plans`) segue engolindo: um arquivo torto não pode derrubar a listagem dos outros. `[confirmado]`
- **`cmd_tick`** recusa tique de fase e recusa prova com menos de `EVIDENCE_MIN = 8` caracteres. `cmd_state` recusa o valor `done` — "done só via tick, que exige prova". `[confirmado]`
- **A prova também tem teto de FORMA, desde 2026-08-03: texto corrido é recusado.** `cmd_tick` barra quando `len(ev) > BULLET_MAX` (140) **e** `prova_bullets(ev)` devolve menos de 2 pedaços — ou seja, um parágrafo num bloco só. A mensagem manda separar com ` · `, `; `, ` + ` ou quebra de linha, e diz o que continua isento: **saída crua de um comando passa inteira**, porque o teto vale só para o texto redigido. `[confirmado — `plan_state.py:cmd_tick`, linha 594]`
- **`prova_bullets`** não inventa corte: quebra a prova **só** nos separadores que quem escreveu já usou (`\n`, ` · `, `; `, ` + `) e devolve os pedaços sem o marcador. Prova de um segmento só continua um bullet — quem barra a linha corrida longa é o `tick`, no momento de gravar, **não** o renderizador. `[confirmado — `plan_state.py:prova_bullets`]`
- **A prova sai em bullets nas três superfícies — e no HTML ela nasce FECHADA.** `_detalhe` devolve `prova:` mais uma linha `· <pedaço>` por bullet quando há mais de um; a árvore de texto imprime essas linhas, e `plan_state.py:_detalhe_html` embrulha **toda** prova num `<details class="pt-evidence-d">` sem `open` — o conteúdo só aparece com um clique, nas **duas** páginas (execução e valor). Com mais de um bullet o corpo é o `<ul class="pt-prova">` de antes; com um só, um `<span>`. **O rótulo do `<summary>` é DERIVADO do conteúdo, desde 2026-08-15**: o primeiro pedaço da prova (cortado em 88 caracteres) mais a contagem do que sobrou — `a suíte do gerador saiu OK · +2` — porque a etiqueta fixa `prova:` dava, num plano de 72 passos feitos, 72 linhas idênticas, e etiqueta que não muda não ajuda a decidir se vale abrir (`quality-goals.md:102`, autoral). Promoção, não campo à parte: o primeiro pedaço continua inteiro dentro do bloco fechado. É `<details>` nativo, sem JS, com o CSS em `plugins/visual/skills/visual/template.html` (`details.pt-evidence-d > summary`, que esconde o marcador padrão e gira a seta `.pt-chev`). Um plano de trinta passos com um parágrafo colado a cada título não se lê — foi essa a queixa que abriu o assunto, e a prova aberta por padrão a reabria em bullets. `[confirmado — `_detalhe_html` rodado nesta rodada devolve `<details class="pt-evidence-d">…` para prova de 1 e de N pedaços]`
- **O validador passou a morder no `tick`, mas só pela tarefa ticada.** Até então ele só rodava no `init`, e por isso um `desc` de 356 chars sobreviveu num plano cujo teto é 140. Agora `cmd_tick` chama `erros_do_plano`, filtra com `plan_state.py:_erro_e_do_no` os erros que citam **aquele** nó e **só esses bloqueiam**; defeito em outra tarefa vira aviso no stderr (os 3 primeiros). É fail-open deliberado: bloquear precisa de evidência sobre o alvo, senão uma tarefa torta congelaria o plano inteiro. A tradução posição↔id é necessária porque `erros_do_plano` prefixa com `fase[i] passo[j]`, que são posições, não ids. `[confirmado]`
- **`cmd_tick` fecha o requisito em RELATÓRIO, não em estado.** Quando a tarefa ticada era a última daquele `requisito`, o comando imprime o critério de aceite do documento e a ordem de conferir — mas o requisito **não ganha campo `status`**, pelo mesmo motivo pelo qual a fase não tem estado próprio: estado duplicado é estado que diverge. E o motor não verifica critério de aceite, ele **lembra**; quem confere é o usuário. `[confirmado]`
- **`cmd_page`** grava a página no **mesmo caminho** por (plano, modo, vista): `plano-<id>-<modo>.html` na vista de execução e `plano-<id>-<modo>-valor.html` na de valor, no diretório do `/visual`. O usuário dá refresh na aba, em vez de acumular arquivos — e o sufixo da vista existe porque sem ele as duas árvores do mesmo plano gravariam no mesmo arquivo e a última apagaria a outra em silêncio. `[confirmado]`
- **`--mode approve` só existe na vista de execução.** O veredito Manter/Mudar/Remover mora na FASE, e a vista de valor desenha épico › requisito › grupo: a página saía com a caixa de fechamento, os dois botões e **zero** item revisável, e o "Aprovar tudo" devolvia uma aprovação que ninguém deu. `cmd_page` recusa a combinação antes de montar qualquer coisa, dizendo onde aprovar (`--vista execucao`) e como só ler o eixo de valor (`--mode track`). `[confirmado]`
- **A vista de valor sem nenhum requisito declarado DIZ isso** em vez de sair em branco. `plan_state.py:_sem_eixo` reconhece a situação (há tarefa, não há citação a requisito nenhum — o estado de 14 de 14 planos reais medidos), a página abre com o aviso e as tarefas são desenhadas sob um nó **"sem requisito"**, agrupadas por `grupo`. A lista de ids "tarefas sem requisito" não se repete nesse caso: a árvore acima já é ela inteira. Sair vazia num plano de 157 tarefas afirmava, por omissão, que não havia trabalho. `[confirmado — `_render_valor` e `_html_valor`]`
- **A linha de baixo do item tem uma regra só, `plan_state.py:_detalhe`**, lida pelas duas vistas e pelos dois formatos: prova quando o passo está feito, `⛔ falta decidir: …` quando uma decisão trava o tique, linha didática no resto. Enquanto eram duas cópias, a pendência era invisível justo na vista em que o dono aprova — o motor recusava o tique por um bloqueio que a página nunca tinha mostrado. `[confirmado]`

### Quando a pendência aparece no meio da execução

A regra de quem decide é do modelo, não do programa: mora em `plugins/visual/skills/visual/SKILL.md`, seção "Motor de decisão". Em sessão **interativa** a pendência sempre para e vai ao usuário — com o parecer junto, quando há. Em execução **autônoma**, três perguntas convocam um segundo parecer, e qualquer "sim" basta: a ação é irreversível (remoto publicado, migração de banco, apagar dado, envio a terceiro); contradiz a norma que o requisito cita; ou o repositório não desempata sozinho. `[confirmado — leitura da seção nesta rodada]`

Empate se resolve **por natureza, nunca por contagem de votos** — quem escreveu o plano não vota. Divergência sobre **fato** vira medição: roda e cola a saída (`por: "medicao"`, saída crua no campo `prova`). Divergência sobre **mérito** vai ao usuário no modo interativo e, no autônomo, segue a opção **mais reversível** (`por: "mais-reversivel"`), com a decisão obrigatoriamente no topo do relatório final. O registro vai no campo `decidido` da tarefa e guarda a pergunta original, pra que `plan_state.py reabrir` consiga restaurá-la. `[confirmado]`

### Os dois hooks que costuram o plano à sessão

⚠️ **Os dois MUDARAM DE PLUGIN nesta rodada:** `sessionstart-plan.sh` e `stop-plan-status.sh` saíram do `visual` e passaram a morar — e a se registrar — em `plugins/project-skills/hooks/`. Junto com eles mudou o resolvedor que chamam: hoje é `"$SCRIPT_DIR/../lib/resolve-dir.sh"`, a cópia da própria família, e não mais o script dentro da skill do `/visual`. Quem cita o caminho velho está citando um arquivo que o hook não abre mais. `[confirmado — `grep -n resolve-dir` nos dois scripts e o `hooks.json` do `project-skills`]`

- **`sessionstart-plan.sh`** (SessionStart, timeout 10) — cria o marco `${TMPDIR:-/tmp}/claude-plan-mark-$(id -u)-${SESSION}-${PHASH}` **mesmo sem plano aberto**, e injeta `additionalContext` listando os planos abertos com `done/total`, o próximo passo e o caminho do arquivo. Desde esta rodada ele acrescenta uma linha `🔎 Cobertura requisito↔tarefa:` com as **duas primeiras linhas** de `plan_state.py --dir "$PLANS_DIR" cobertura` — o resumo e o aviso de "nenhum documento de requisitos encontrado". O comentário do arquivo dá o motivo de o número entrar aqui e não pelo `brief`: este hook monta o texto a partir do `open --json` e não passa pelo `brief`, e sem isso o número apareceria só no fim do turno, *"e não no começo da sessão, que é justamente quando o Claude novo decide o que fazer"*. O texto fixo que ele injeta ganhou, nesta rodada, a linha *"pré-check vencido → rode a caça antes de planejar ou executar por cima"* — o mesmo recado que o preâmbulo do `doc-load` carrega, para que a régua carregada não seja lida como dispensa da varredura do plano. Saída vazia (2+ planos ativos, nenhum plano) não acrescenta nada — fail-open como o resto do hook. `[confirmado — leitura do script nesta rodada]`
- **`stop-plan-status.sh`** (Stop, timeout 15) — emite `systemMessage` com os bullets de `plan_state.py brief`, nunca `decision:block`. Desliga com `PLAN_STATUS=0`; só a cobrança do tique desliga com `PLAN_NUDGE=0`. A cobrança entra 1× por (sessão, projeto), e **só** quando há marco antigo, nenhum `*.plan.json` foi tocado desde ele e o transcript mostra 3+ chamadas de `Edit|Write|MultiEdit|NotebookEdit`. Se o marco não existe, o hook **cria** o marco e não cobra naquele turno — o comentário registra a regra geral: hook que depende de outro hook ter rodado é frágil, então crie o pré-requisito você mesmo. `[confirmado]`

  ⚠️ **O marco também decide se o resumo pode AFIRMAR, e desde 2026-08-02 ele só é repassado ao `brief` quando é antigo.** Marco recém-criado significa "não sei", nunca "a sessão não tocou nada": nenhum plano pode ser posterior a um marco que acabou de nascer, então repassá-lo faria o primeiro turno de toda sessão cair no caminho errado. `[confirmado — `stop-plan-status.sh`, a guarda `[ "$MARCO_NOVO" = "0" ]`]`

  🔴 **A FORMA do resumo, canonizada em 2026-08-03 — o canal é TEXTO, não markdown.** `systemMessage` chega literal no terminal: `**` e crase viram ruído na tela, não destaque. Foi relatado com print, e valia para três emissores (o resumo do plano, a cobrança do tique e o aviso de push de branch). O que substitui cada um `[confirmado]`:

  | o que dava destaque | o que dá agora |
  |---|---|
  | `**Título**` | posição + emoji do estado (`📍` afirma · `📋` relata · `✅` conclui · `🏁` encerra) |
  | `**Feito:**` `**Agora:**` `**Falta:**` | `✅ Feito:` · `🔄 Agora:` · `⬜ Falta:` — o **mesmo** vocabulário do `MARK` da árvore |
  | `` `comando` `` | o comando cru, sem crase |

  ⚠️ **Duas linhas em branco abrem a mensagem, e elas são do CANAL, não do texto.** O harness prefixa `Stop says: ` na primeira linha: sem elas o cabeçalho grudava no prefixo, num nível diferente dos bullets. A primeira desce o cabeçalho, a segunda separa o bloco do texto do turno. Ficam no hook — `brief` chamado na mão não deve abrir em branco. **Não entram no orçamento**: `_linhas_visiveis` só conta linha com conteúdo, e o total segue em 6. `[confirmado — 57 checks em `test_plan_hooks.sh`]`

  ⚠️ **A suíte deste resumo não testa por ÍNDICE.** Sete checks liam `L[1]`, `L[2]`, `L[3]` e quebraram **duas vezes no mesmo dia** sem nenhuma mudança de comportamento — só porque o layout ganhou emoji e uma linha em branco. Agora procuram o bullet pelo rótulo (`bullet(linhas, "Falta")`). Regra geral: **teste de artefato de leitura casa CONTEÚDO, nunca posição.**

  🔴 **QUAL plano o resumo mostra: a marca de sessão, desde 2026-08-03.** O hook passa `--sessao "$SESSION"` ao `brief`, e é isso que faz o resumo ser **desta** sessão. Antes a escolha era por data de escrita do arquivo, e `mtime` diz que **alguém** mexeu, nunca **quem** — num projeto com frentes paralelas (6 sessões abertas no mesmo repositório em 2026-08-03) a vizinha marcando um passo empurrava o plano dela para o topo do fim de turno de todo mundo. Relatado com print de produção duas vezes antes de virar código. Três estados `[confirmado — 57 checks em `test_plan_hooks.sh`, e medição pelo hook real com duas sessões]`:

  | a sessão… | o cabeçalho | qual plano |
  |---|---|---|
  | marcou **este** plano | 📍 `Onde estamos` — afirma | o dela, no topo |
  | marcou **outro** | 📍 `Onde estamos` | o **dela**, não o mexido por último |
  | não marcou **nada** | 📋 `Plano aberto no projeto` — relata | o mais recente, sem afirmar |

  A marca vive em `plan_state.py:save()` — **não** em cada comando —, então `tick`, `state`, `init` e `close` já nascem cobertos e comando novo também. Formato: `<TMPDIR>/claude-plan-sessao-<uid>-<sid>-<sha1(abspath do dir de planos)[:12]>`, com o id do plano dentro. A chave é calculada por **uma** função (`_sentinel_sessao`), usada por quem escreve e por quem lê: chave computada em dois lugares diverge, e sentinel que nunca casa é pior que sentinel nenhum — a mesma armadilha do `cksum` sobre path canonicalizado que já mordeu este repo (§1.5 de `patterns.md`). Com o id em mãos, **ausência de marca também é informação**: nada liga a sessão àqueles planos, então o cabeçalho recua em vez de afirmar. Chamada sem `--sessao` (hook de versão antiga) cai no critério de marco, como antes.

- **`stop-anuncio-sem-acao.py`** (Stop, timeout 20) — **novo em 2026-08-02**, e o único do `visual` que emite `decision:block`. Devolve o turno que termina prometendo a próxima etapa sem executá-la. Três condições, todas necessárias: há plano ativo com passo em aberto, o texto final promete em 1ª pessoa (`sigo para`, `vou seguir`, `prossigo com`…) e **não** espera o usuário (pergunta no fim ou `posso seguir`/`quando você mandar` desarmam). Cap de 2 devoluções por (sessão, projeto) além do cap nativo do harness; kill-switch `ANUNCIO_ACAO=0`; toda passagem vira linha em `~/.claude/state/anuncio-acao/batidas.log`. `[confirmado — a contagem viva sai da suíte: `python3 plugins/visual/hooks/test_anuncio_sem_acao.py`, a maioria de casos que NÃO podem armar]`

  🔴 **`stop_hook_active` NÃO cala este gate (desde 2026-08-15).** O campo é do EVENTO, não deste hook: basta QUALQUER hook de Stop ter devolvido o turno (o `delivery-audit.sh` do intent-guard devolve) para ele chegar `true` — e o gate saía sem ler uma frase. Foi medido em produção: uma sessão inteira sem julgar nada, calado pelo vizinho. O anti-laço é o cap próprio por (sessão, projeto), que conta as devoluções DESTE gate. `[confirmado — comentário e fluxo em `stop-anuncio-sem-acao.py:main`]`

  ⚠️ **Windows entrou na conta na mesma rodada:** os três canais de texto são reconfigurados para UTF-8 na carga (senão acento corrompe e emoji derruba a escrita no cp1252); todo caminho passado ao bash vira barra normal (`_posix` — `C:\Users\…` chega ao Git bash sem barra nenhuma e o `resolve-dir.sh` resolvia a pasta de planos ERRADA, desarmando o gate em todo caso legítimo); e o próprio bash é achado pelo `bash_posix.py` vendorado (fonte em `_shared/`) — sem bash funcional, fail-open calado. O `plan_state.py` deixou de ser caminho relativo ao vizinho e passou a ser resolvido pelo NOME via `resolve-plugin.sh` — caminho relativo não vale no cache do harness. `[confirmado — `stop-anuncio-sem-acao.py:_plan_state` e `_posix`]`

  ⚠️ **Plano vindo da RESERVA ganha aviso no bloqueio.** O `resolve-dir.sh` sai com código 3 quando o cwd não tem marcador de projeto e a pasta de planos veio do fallback; o stderr dele é descartado pelo hook, então o sinal viaja pelo `returncode` e vira uma frase no `reason` — "confirme com o usuário que é o plano certo" — que é o que o modelo lê. `[confirmado — `stop-anuncio-sem-acao.py:planos_abertos`]`

  ⚠️ **O sinal NÃO é "o turno não chamou ferramenta".** No `Stop` isso é trivialmente verdade — o evento dispara porque a última mensagem foi texto. No caso que originou o hook o tique **aconteceu** (`plano 5/41`) e só depois veio o `Sigo para F2`. Medido nos transcripts de origem: 2 de 2 fechamentos com anúncio pararam, contra 0 de 42 sem anúncio. ⚠️ **Teto conhecido e deliberado:** a detecção é lexical, então promessa fora dos padrões passa — o falso NEGATIVO foi preferido, porque devolver turno legítimo custa mais caro. O `batidas.log` existe para medir se o léxico está largo ou estreito demais.

### O fio requisito↔tarefa — quatro estados, e onde cada um aparece

`plugins/project-skills/lib/cobertura.py` cruza o documento de requisitos com as tarefas do plano e nomeia quatro situações, nenhuma silenciosa: **coberto**, **tarefa sem requisito** (trabalho que ninguém pediu), **requisito sem tarefa** (pedido que ninguém planejou) e **citação a requisito que não existe**. Os três primeiros são relatório; o quarto é erro que recusa gravar. `[confirmado — `cobertura.py:mapa` e `plan_state.py:validate`]`

⚠️ **Esses quatro são o fio requisito↔tarefa; o mesmo módulo cruza hoje o plano contra os OUTROS documentos de régua** — lei (`le_artigos`), jornadas, peças da arquitetura pretendida e passos do ciclo. E o cruzamento com a lei corre **nas duas direções desde 2026-08-13**: além do requisito que cita artigo inexistente, o artigo que **nenhuma tarefa representa** sai nomeado (`artigos_sem_tarefa`, com número e nome, e uma linha própria no `resumo`). A lista viva dos baldes sai do programa, não desta prosa: `python3 -c "import cobertura; print(sorted(cobertura.mapa({}, {})))"` de dentro de `plugins/project-skills/lib/`. `[confirmado — comando rodado nesta rodada]`

O número **aparece sem ser pedido**, em quatro superfícies, todas lendo a mesma `cobertura.py:resumo` pra que um só programa calcule:

- no **começo da sessão**, pela linha que o `sessionstart-plan.sh` injeta;
- no **fim do turno**, por `plan_state.py:brief_lines` — e ali ele **toma o lugar** do bullet "Falta", nunca vira um 4º, porque o teto de 3 bullets é do pedido. Só entra quando há tarefa sem requisito ou citação inexistente; a cobrança do tique, quando existe, ganha o slot;
- no **cabeçalho da árvore de valor**, texto e HTML;
- sob demanda, em `plan_state.py cobertura` (com `--json` pra consumo por programa e `--reqs` pra apontar outro documento). `[confirmado — leitura das quatro chamadas]`

**Desde 2026-08-15 o plano é LIDO antes de a corrida acender — e as perguntas em aberto saem na tela.** Passo preso por decisão do dono não é tarefa: é pergunta. Antes de disparar o Workflow, `/sprint` abre o arquivo do plano mais recente (`.claude/plans/*.plan.json`), percorre o campo `pendencia` de cada passo e imprime uma linha `PRESO <id> · <pergunta>` por passo travado, fechando com `PENDENCIAS=<n>` — **em todos os casos, inclusive quando é zero**. Zero ⇒ dispara; qualquer outro número ⇒ **não dispara**, e as perguntas vão ao dono antes da largada. Quem julga se a pergunta ainda trava é `plan_state.py:pendencia_viva`, **importada** pelo bloco (o mesmo juiz que recusa o tique) — régua copiada diverge, e aí a varredura anunciaria preso o que o plano já destravou. Medida que originou a trava: **nove passos presos por decisão entraram numa corrida como se fossem trabalho**, os executores voltaram sem ter como concluir, e o que era uma pergunta antes da largada virou uma onda inteira de churn. `[confirmado — a seção "As pendências do plano são lidas e IMPRESSAS antes do disparo" em skills/sprint/SKILL.md e o bloco F12.4 de test_sprint_skill.py, que saiu OK nesta rodada]`

**E desde esta rodada a pendência declarada deixou de ser a única porta: o PRÉ-CHECK grava, e a casca CONFERE.** `plugins/project-skills/lib/precheck_largada.py` roda quatro passadas sobre os passos ABERTOS — o passo isolado (sete checagens mecânicas), a sequência, a casa medida por execução e a vizinhança — e `--relatorio` deixa o veredito, as decisões já tomadas, as propostas e a **marca do PLANO** em `.claude/.sprint/precheck.json` (fora do git, a mesma casa do ledger de corridas). ⚠️ **A árvore saiu da marca (R-32)**: cada tique mexe no disco, então o hash da árvore vencia o relatório por conta própria, a cada passo fechado. No bloco 1 do disparo, antes de armar o sinal do motor, `--confere` **recusa a largada e sai 3** em QUATRO casos: relatório ausente, vencido (o plano mudou desde a medição), com proposta pendente ou com decisão do dono em aberto — e nestes dois últimos ele nomeia a proposta e a pergunta que faltam. ⚠️ **Há uma quinta lista, e ela NÃO fecha a porta: `adiadas`** — o achado ADIÁVEL, o que não deu para medir (sem chave de prova da esteira, estabilidade não medida). Ele não recusa a largada, mas o texto do veredito `livre` o NOMEIA, porque quem larga tem que ler o que ficou sem medição. A marca cobre `id` + `pronto` + `desc` dos abertos mais o registro selado, então tique de passo não vence o relatório, mas passo reescrito, passo novo ou decisão nova selada vencem. **A rodada N+1 ganhou linha de comando** (`--respostas <json>`): o módulo relê as RESPOSTAS do dono — não o plano —, regrava o relatório com as propostas de reescrita/remoção (cada uma citando a resposta literal) e **nada escreve no `.plan.json`**; enquanto a proposta não for decidida, o `--confere` segura a largada. `[confirmado — a seção "O pré-check de largada grava, e a casca confere" em skills/sprint/SKILL.md, `python3 plugins/project-skills/lib/test_precheck_largada.py` → **93 ok · 0 falha**, e `test_sprint_skill.py` → **OK**, com a mutação "remover a conferência do pré-check deixa a suíte vermelha"]`

⚠️ **Não confundir com adiar decisão.** Nos dois lados do fio — a concepção (`/start`, fluxo 22) e a execução (`/sprint`) — falta de material é ordem de **investigar**, nunca licença para mandar a escolha ao dono: lê-se o código que a escolha toca, roda-se o comando que mede, abre-se o documento da régua, e só então ela vai para *decidida, com a razão* ou *esperando o dono, com o que foi investigado*. A racionalização *"falta material para decidir, deixo pendente"* está refutada por escrito nas duas skills. `[confirmado — "Decidir depois é opção, nunca necessidade" nos dois SKILL.md]`

### Quando quem marca é o MOTOR, e não uma pessoa

O ciclo acima descreve o tique feito à mão. Na execução contínua quem marca é um agente do motor (`plugins/project-skills/skills/sprint/SKILL.md`, o maior bloco ```javascript), e defeitos medidos em duas autópsias seguidas mudaram a forma desse papel. `[confirmado — leitura do SKILL.md e das duas bancadas nesta rodada]`

**Nesta rodada (2026-08-09) o marcar deixou de ser um ato solo — a palavra de quem executou não basta mais.** Duas travas, e as duas **nomeiam o que seguraram** em vez de calar:

- **O de acordo do revisor.** Passo que apareceu em `review.gaps` ou em `review.missingTasks` **não é marcado naquela onda** — ele volta ao laço pelo feedback normal e o trabalho fica no disco. Os ids segurados saem em `rounds[].naoMarcados = { motivo: 'reprova do revisor', ids }` e o `log()` os narra.
- **A onda verde.** `suite.green` falso ⇒ **nada é marcado**, e os entregues saem em `rounds[].naoMarcados = { motivo: 'onda vermelha', ids }`. O motivo escrito no código: marcar sem ponto de salvamento grava no plano um trabalho que não entrou no histórico. Medida que originou as duas: **17 passos marcados em ondas vermelhas, 9 deles com o defeito já escrito pelo revisor da mesma onda.**

**Ainda em 2026-08-09, o ciclo curto passou a fechar POR BLOCO, e a onda virou a PASSADA GERAL** (decisão do dono). Dentro do laço de blocos de `plugins/project-skills/skills/sprint/SKILL.md`, na ordem em que o script decide:

```
revisor POR TAREFA   revisorTarefaPrompt · schema TAREFA_REVIEW · um agente por entrega
  ↓                  fidelidade ao `pronto` · cobertura · qualidade — escopo de UMA tarefa
revisão DO BLOCO     revisorBlocoPrompt · schema BUILD_REVIEW · os MESMOS eixos sobre as
  ↓                  entregas juntas + COESÃO, sem herdar o veredito por tarefa
suíte inteira        SUITE_RESULT — vermelha ⇒ nada deste bloco é marcado
  ↓
commit (checkpointPrompt · schema CHECKPOINT_RESULT) → marcação → doc-touch → colheita
```

**O commit vem ANTES da marcação, e o gate recusado segura o tick** (0.22.53): o
checkpoint devolve `{committed, sha, motivo}`; `committed !== true` vira Bloqueio nomeado
com o motivo do gate e **nenhum passo do bloco é marcado** — a prova do tique carrega o
sha. Antes, o passo era marcado primeiro e o commit terminava em `|| true`: gate de
release recusado deixava passo `done` sem código no histórico.

**Antes de decompor, a rodada 1 pergunta ao DISCO o que já parece feito (2026-08-20).** Um papel mecânico (`orfaos:r1`) roda `plugins/project-skills/lib/orfaos.py`, que cruza `git status --porcelain -uall` e os commits desde o último tique com os passos **abertos** do plano — pelo arquivo que o passo nomeia e pelo id citado no assunto do commit — e devolve os ids. Nasceu de uma corrida que entregou 4 tarefas e 3 commits com **zero** passos marcados porque o bloco não fechou antes da parada: a retomada seguinte mandaria refazer tudo. ⚠️ **A lista é SUSPEITA, nunca veredito** — ela vai ao orquestrador (regra 9 do prompt dele), que despacha cada órfão como **tarefa normal** do bloco, com o mesmo `pronto` e o mesmo revisor por tarefa; refazer o que está pronto e marcar no escuro são os dois desfechos errados, e o executor que confere o `pronto` já cumprido devolve `done: true` adotando os caminhos. Só no fim o tique marca, e marca por **retomada** (`--retomada`, a trava do fluxo 5): a prova sai já com `revisor de órfão APROVOU` e o sha. Fail-open: detector ausente, comando != 0 ou saída ilegível ⇒ lista vazia e a rodada segue. `[confirmado — o bloco `TRABALHO ÓRFÃO NA LARGADA (F18.1 · R-28)` de `motor.js`, o `orfaosPrompt`, e `test_orfaos.py` → 9 ok nesta rodada]`

**E a mesma suíte roda UMA vez na largada** (`suite:largada`, rodada 1, antes de qualquer
executor): vermelho ali é porta fechada — defeito pré-existente do repositório, nunca
obra desta missão. A lista de testes é enumerada por comando escrito no prompt, igual em
toda rodada; "os diretórios do trabalho da missão" deixou de ser critério depois que uma
corrida rodou 43 testes na rodada 1 e 120 na rodada 2, descobrindo no meio do bloco um
vermelho que já existia antes da largada.

**Os papéis mecânicos (saúde e suíte) recebem o comando declarado da casa e um teto de
relógio próprios** (`suiteCmd` e `tetoMecanicoMin`, args da casca — 0.22.54): o `planText`
vai ao orquestrador e aos revisores e **nunca** chega a esses dois papéis, então sem
`suiteCmd` um agente de saúde improvisou o comando proibido do projeto e ficou 58 min num
log congelado — invisível para o vigia, que só conta rodadas FECHADAS. Com o teto, estourar
é parada com o motivo escrito: a saúde devolve fail-open (`fechada: false`), a suíte devolve
`green: false` com o placar dizendo onde travou.

As duas travas acima (de acordo do revisor + verde) passaram a valer **no grão do bloco**: bloco vermelho não vira ponto de salvamento, e as entregas voltam pelo decompositor. O `docTouchPrompt` roda **a cada bloco**, sobre TODOS os documentos afetados pelos arquivos daquele bloco — o comentário do código declara o custo aceito: documento grande pode ser reescrito mais de uma vez na mesma onda, e o conflito disso é achado da revisão geral de doc, não deste passo. `[confirmado — o laço `for` dos blocos, passos 1 a 4]`

**O ponto de salvamento diz QUAL bloco fechou e grava só o que ele tocou.** A mensagem é `"sprint: onda <r> bloco <b> verde"` — sem o bloco, dois salvamentos da mesma onda escreveriam a mesma linha e quem lê o histórico depois não os separaria. ⚠️ **E os arquivos são NOMEADOS: `git add -- <arquivo...>`, nunca `add -A`.** A lista é a união dos `files_touched` das tarefas que o bloco aprovou, mais o `planPath` quando ele é `.plan.json` (os passos que o `tick` acabou de marcar são obra desta onda). **O `commit` leva a MESMA lista de caminhos que o `add`** — `commit` sem pathspec grava o índice inteiro, e arquivo que outra sessão apenas stageou entrava no commit da onda mesmo com o `add` nomeado; agora ele segue staged e intacto para quem é dono dele. O `add` é um caminho de cada vez, para que caminho recusado (fora do repositório, ou que não existe mais) saia numa linha nomeando o arquivo em vez de derrubar o salvamento inteiro. Varrer a árvore engoliria trabalho de outra sessão aberta no mesmo repositório e o gravaria como se fosse da onda — inclusive o arquivo de uma tarefa REPROVADA no mesmo bloco. Arquivo que o executor não declarou fica de fora; se ele mexeu sem declarar, o defeito é do `TASK_RESULT`. `[confirmado — a linha `git -C <raiz> add -- <arquivo...>` da especificação do papel, o `planPath` passado na chamada, e os checks de `git show --stat` em `test_motor_bancada.py` — o que lista só os arquivos da onda, o que mantém fora o arquivo da tarefa reprovada, e o que mantém fora o que outra sessão apenas stageou]`

**O fim da onda é a passada GERAL, e ela tem duas metades.** A revisão geral da obra (`reviewBuildPrompt`) julga o que está NO REPOSITÓRIO com escopo na união dos `files_touched` da onda (`filesDaOnda`) — **nunca o repo inteiro**, porque achado sobre trabalho alheio vira conserto que ninguém pediu. Depois vem a revisão geral da doc (`revisaoDocPrompt`, schema `DOC_REVIEW`), que relê **inteiros** os documentos afetados contra o estado de agora, inclusive o conflito de dois blocos que reescreveram o mesmo arquivo: doc minerada errada ele conserta na hora (`consertados`), doc **autoral** (`authored-by: human`) ele nunca toca — vira gap `autoral: true` que o script transforma em aviso ao dono.

**Achado da revisão geral sobre passo JÁ MARCADO vira RE-TICK do mesmo id, nunca id novo** (`rounds[].reticks`). Sem essa regra o plano diria "feito" enquanto a revisão diz "defeituoso" — a mesma contradição que as duas travas fecharam, por outra porta. O conserto volta ao laço e, quando fechar num bloco futuro, o tique **regrava a prova do mesmo id**; id novo seria recusado pela trava de id inexistente. `[confirmado — o bloco `const reticks` e o `log()` que os narra]`

**O desafiador de causa passou a disparar também por GRAVIDADE.** Antes só a reincidência convocava a investigação; agora achado com severidade ≥ floor **na primeira aparição** já manda investigar a causa antes de a tarefa voltar ao decompositor. A trava que paga essa conta é o **`causaCache`**: causa referendada não reabre na mesma missão, e a resposta reusada volta marcada `deCache: true`. A chave muda com o motor — os arquivos da tarefa no `sprint`, `arquivo:função` no `qa-loop` (o mesmo par que o `churn` usa, porque só o nome da função colidiria entre arquivos). `[confirmado — `causaCache` nos dois `SKILL.md` e o `if ((v.gaps || []).some(g => sevRank(g.severity) >= floor))`]`

**A conferência final passou a rodar também na PARADA.** Antes, `confirm-pass` só existia no caminho feliz sem `/qa-loop`, e o `/qa-loop` da etapa seguinte só roda depois de `built=true` — quem parava por teto, por vigia ou por onda estéril entregava sem segunda checagem nenhuma. Hoje o relatório carrega **`conferidoPor`** com quatro valores possíveis: `qa-loop da etapa seguinte` · `confirm-pass` · `confirm-na-parada` · `nenhuma`. Gap achado na parada **não volta ao laço** (a missão já parou): vira aviso nomeado, para o conserto entrar como tarefa no plano. ⚠️ **Exceção única: parada por ORÇAMENTO não gasta a conferência** — o disjuntor é teto duro, e gastar um agente depois dele é o disjuntor deixando de ser disjuntor. A ausência não passa calada porque `conferidoPor` diz o que rodou. `[confirmado — o bloco `if (!built && entregouAlgo && desligadoPor !== 'orcamento')`]`

**Onda estéril ENCERRA a corrida.** Onda que decompõe e não tem **uma** tarefa executável sai com `stopReason: onda-esteril` e um Bloqueio dizendo quantas foram separadas sem sair. Medido: duas ondas seguidas separaram 40 e 30 tarefas e executaram zero, com a fila inteira parada por bloqueio ou espera — e o motor seguiu pagando a decomposição, que é a parte cara. O que trava já está no relatório (`esperandoVoce`, `impedidos`); rodar de novo é o mesmo resultado pelo mesmo preço. ⚠️ **Fila adiada pelo teto de leva não conta como estéril** (`!todo.length && !adiadas.length`): sem essa metade, a rodada em que a leva da vez foi toda pulada encerraria a corrida com dezenas de tarefas ainda esperando.

**O VIGIA DEIXOU DE MEDIR TEMPO — o script não tem relógio (2026-08-10).** `Date.now()` lança em script de Workflow (quebraria o resume), então o carimbo de hora vinha de um campo `heartbeat` no `SUITE_RESULT` que o **agente** preenchia — e numa corrida real ele devolveu `1`, o valor mais barato possível, porque o campo existia no schema e **não tinha linha correspondente no prompt**. A conta `ARGS.now - 1` deu 29.772.858 minutos (56 anos) de silêncio, e a missão foi derrubada no minuto seguinte a uma suíte verde de 374 testes, com 10 das 12 rodadas por usar. Hoje o sinal de vida é **avanço, medido pelo próprio motor**: `rodadasMudas` conta rodadas que fecharam sem nenhum bloco verde, e `rodadasMudasMax` (default 3) é o teto. A segunda metade da condição continua sendo o trabalho vivo, mas agora ele **protege só a rodada em que foi visto** (`trabalhoVivoEm < r`) — guardar a última suíte qualquer fazia a vermelha que fecha o bloco apagar a declaração da verde anterior. ⚠️ **A metade que fala em minutos ficou onde há relógio de verdade**: `lib/andamento.py:linha_silencio`, em Python (fluxo 19). A regra geral que sobrou da autópsia vale para todos os schemas do motor: **campo em schema sem linha correspondente no prompt é convite a valor inventado**. `[confirmado — `plugins/project-skills/skills/sprint/references/motor.js`, o bloco `VIGIA POR AVANÇO`, e os cenários F9.13/F9.24 de `test_motor_bancada.py`, que rodam o motor de verdade]`

**A LEVA TAMBÉM TEM TETO, e o excedente é fila — não falha.** `blocoMax` limitava o bloco e nada limitava a leva: numa corrida real ela teve 53 tarefas, o segundo bloco falhou, e a regra de falhar cedo cancelou 45 de uma vez — decompostas pelo papel mais caro do motor para nunca serem despachadas; 30 delas ainda voltaram **puladas por "estado repetido"** na rodada seguinte, sem uma tentativa, porque a impressão de quem ninguém tocou é idêntica por definição. Hoje: `levaMax` (default 12) corta a leva, o excedente sai em `rounds[].adiadas` (separado de `naoDespachadas`, que é o que o bloco cancelado engoliu), e os dois viajam juntos no `feedback.naoDespachadas` — que isenta ambos da regra de pular. ⚠️ **O corte vem DEPOIS do "para ou pula", não antes**: antes dele, a frente da fila já entregue (que o decompositor devolve de novo) ocuparia as vagas toda rodada e a fila adiada nunca andaria. E `built` passou a exigir leva inteira tentada (`!naoTentadasNaRodada.length && review.complete && …`): o revisor julga o que viu, e o que não foi despachado ele não viu. `[confirmado — `test_motor_bancada.py`, os dois cenários `F9.61`: o que afere a fila andando na rodada 2 reprovava com o corte na ordem anterior]`

**O diagnóstico de tarefa-presa virou LAÇO, não parecer único.** Quem investiga para na **causa** (nunca descreve o sintoma e manda consertar ali). A causa vai a um **desafiador** (`desafioCausaPrompt`, schema `DESAFIO = { procede, motivo, anchor }`, mesmo `diagnose_model`) com a lente invertida: o papel dele é **provar que a causa está errada**. Os dois iteram — o desafio da volta anterior volta ao investigador em `desafioAnterior` — até um referendar o outro; acordo entra no `feedback` marcado `desafiada: true`. **Desafiador mudo não referenda**, e três voltas sem acordo não escolhem vencedor: viram Bloqueio `kind: 'causa-em-disputa'` com as duas versões escritas. Nasceu de regressão medida: um conserto pontual, feito onde o defeito apareceu, reabriu o mesmo problema em outro arquivo. `[confirmado — o laço `for (let volta = 1; volta <= 3 && !acordo; volta++)`]`

**Nesta mesma rodada, mais três travas — e as três fecham o laço da missão em vez de abrir gate novo:**

- **Todo prompt do motor ABRE com `PAPEL: <NOME>` numa linha sozinha**, antes de qualquer prosa — e por isso é a primeira linha do transcript do agente, o único lugar de onde a autópsia (`plugins/improve-workflow/lib/medidor.py:papel_do_prompt`) consegue saber quem foi cada um. Antes o papel era **adivinhado pela frase** (*"Você é o EXECUTOR…"*): reescrever a prosa do motor faria dezenas de agentes virarem `DESCONHECIDO` na tabela, e a medição por papel deixaria de existir sem nada acusar. Quem cobra que a regra continue no texto é o bloco `S-123` de `plugins/project-skills/lib/test_travas_motor.py`, que **reescreve a prosa em volta da linha** e confere no medidor que a classificação fica de pé. `[confirmado — o bloco existe e a suíte saiu `OK` nesta rodada]`
- **Conserto sai com re-revisão, e o laço só fecha em rodada limpa.** É a mesma regra nas duas receitas — a de implementação (`sprint`) e a de revisão (`qa-loop`): quem revisa reabre sobre o conserto, e o fechamento é `complete && cohesive` com zero gap acima do floor. O que cada laço reabre muda (lá o delta dos arquivos tocados, aqui a obra contra a spec); o critério de fechar, não. Conserto sem re-revisão declara pronto o que ninguém reconferiu, e é assim que o resíduo do próprio conserto atravessa a missão inteira.
- **`voltasPorProblema` — o relatório passou a dizer QUAL defeito custou as rodadas.** Os dois motores devolvem, por problema, em que volta ele apareceu e quantas levou até sumir: no `qa-loop` a chave é o `id` do achado; no `sprint` é `task_id + kind` do gap, porque gap não tem id próprio e só o `task_id` juntaria dois problemas diferentes da mesma tarefa. O total de rodadas escondia a leitura para a qual o laço existe: três rodadas podem ser um defeito teimoso ou três defeitos de uma volta cada, e as duas pedem ação diferente.

**A frente ganhou uma TERCEIRA pergunta, e ela roda fora da missão.** O revisor de construção
(`#2` do `sprint`) pergunta *"a spec virou código inteiro e coerente?"* e o `qa-loop` pergunta *"o
código construído tem defeito?"* — as duas dentro da missão, contra o que foi decomposto. A skill
`completude` pergunta *"sobrou alguém de fora?"* sobre o **projeto inteiro**, em documento e por
programa: funcionalidade sem requisito, requisito sem tarefa, tarefa marcada sem prova, artigo da
lei que nenhuma tarefa carrega — e, desde 2026-08-16, requisito com jornada que nenhuma
superfície do protótipo cobre (`completude.py`, elo requisito → protótipo). É justamente o buraco que **nenhuma tarefa nomeou** — o que o `#2`
não tem como ver, porque ele julga a decomposição que existe. A fronteira está escrita nos três
lados (`skills/completude/SKILL.md` *"Fronteira — quando ela roda, e o que NÃO é dela"*,
`skills/qa-loop/SKILL.md` *"Fronteira com a `/completude`"*, e o terceiro pé no resumo de vias de
`skills/sprint/SKILL.md`), e **elo aberto lá não é finding do `qa-loop`**: não vira fix, não vira
plan-flaw, não entra como bloqueio daqui. A ordem usual é `qa-loop` primeiro, `completude` por
último, antes de declarar a frente pronta. `[confirmado — os cobradores `test_qa_loop_skill.py` e
`test_sprint_skill.py` prendem as duas pontas e saíram OK nesta rodada]`

**A medição de PROJETO saiu do julgamento de PLANO, e a fronteira agora está no código.**
`artigos_sem_tarefa` — o artigo da lei que nenhuma tarefa representa — nasceu dentro do
nível 1 da auditoria de plano, e o nível 1 é **curto-circuito**: a auditoria retorna ali,
sem sequer calcular os níveis 2 e 3. Como a conta mede a lei INTEIRA contra **um** plano, e
plano é fatia de trabalho, todo plano parcial ficava vermelho para sempre — e o laço era
mandado inventar tarefa para artigo que aquela missão nunca se propôs a tratar. Hoje a
conta de projeto é da `completude.py`, sobre a **união** dos planos, e o comentário do
`NIVEL1` diz por que ela não volta. `[confirmado — `auditoria_plano.py:18-21` e a suíte]`

**E a completude passou a contar só o que ainda está VIVO.** O elo tarefa→prova varria
todos os arquivos de plano, inclusive os encerrados — e `close` encerra deixando passo sem
marcar de propósito. Resultado medido: 71 das 96 pendências vinham de 9 planos já
encerrados, nenhuma podia ser fechada (o tique exige prova de trabalho que o dono decidiu
não fazer), e a medição **nunca podia dizer "fechou"** — exatamente o que a skill promete
medir. A regra ficou por EXCLUSÃO (`abandoned`/`done` saem), nunca por `status == "active"`:
plano sem status gravado é plano vivo. Desde 2026-08-16 o plano encerrado não sai INTEIRO:
as tarefas `done` dele seguem creditando requisito (só a pendência dele deixa de contar, e
`tique_sem_prova` conta em plano encerrado também — mentira é falsa em qualquer plano).
`[confirmado — `completude.py:_plano_unico` e o docstring do elo 3 em `cadeia`, lidos nesta rodada]`

**A missão passou a se MEDIR ao fim, e a medição tem freio.** Depois da persistência, o `sprint` roda `plugins/improve-workflow/lib/medidor.py` **em bash, sem agente nenhum** (achado por `resolve-plugin.sh improve-workflow`; ausente na máquina ⇒ pula calado, igual ao lixeiro). A tabela por papel e a linha `sinais — N dos 6 acesos` viram a ÚLTIMA seção do relatório, `### Custo`, com a tabela crua num drilldown fechado. ⚠️ **Desde 2026-08-15 essa seção não sai só do medidor:** duração, tokens e placar (`fechadas` de `total`) são lidos da linha DESTA corrida no ledger de corridas (`lib/ledger_corridas.py le`, o arquivo append-only em `.claude/.sprint/corridas.jsonl`), campo `nao-medido` entra como *não medido*, e a seção sai igual nos três desfechos — corrida que parou tem custo tanto quanto a que fechou, e é nele que se decide relançar. O medidor, por sua vez, só olha run **deste** projeto (`medidor.py:projeto_atual`): run de outra pasta traz números de trabalho que não é este. ⚠️ **`N` igual a zero ENCERRA ali**: nada de abrir transcript ou disparar agente para a autópsia — os passos de leitura dela são caros, e sem sinal aceso não há defeito endereçado a investigar. Só com pelo menos um sinal aceso (ou a pedido do dono) a skill `improve-workflow` é invocada, a partir do passo 2, recebendo a saída crua. `[confirmado — `plugins/project-skills/skills/sprint/SKILL.md`, passo 5 da persistência]`

**A missão ganhou VIGÍLIA, e ela nasce e morre com o sinal do motor.** No bloco 1, logo depois do `andamento.py arma` e **antes** de chamar o `Workflow`, a casca acende o `/goal` do harness com a condição desta missão (o plano fecha; cada parada é investigada, consertada e relançada por `lib/retomada.py`; só a lista fechada de casos do dono interrompe o laço); no bloco 2, junto do `encerra`, ela **apaga** — em todo desfecho de parada, obra pronta inclusive, porque vigília acesa depois do motor morto relança missão que já acabou. A vigília não é comando avulso nem opção do dono: *sprint que para na primeira parada não é sprint, é uma rodada só*. ⚠️ **E o laço não pode remendar antes de apurar:** a causa só existe com a **saída crua do comando** que a mostra, colada literal (memória do que aconteceu não é prova), e essa causa provada ainda vai a um **desafiador** com a ordem de derrubá-la — desafiador mudo não referenda, e três voltas sem acordo fazem o caso subir ao dono (`retomada.py --caso causa-repetida`), nunca ao remendo. Faltando qualquer um dos dois passos, o laço **não conserta e não relança**. `[confirmado — o bloco 1 e o bloco 2 de `skills/sprint/SKILL.md` e os checks `F23.3`/`F23.4` de `test_sprint_skill.py`, com mutação, → `OK` nesta revisão]`

**E desde 2026-08-21 a seção de problemas do relatório deixou de sair da memória da sessão.** Cada vez que o laço da missão para numa pedra, conserta e relança, a parada vira **uma linha em disco** — `ledger_corridas.py parada --project-root … --run-id … --desfecho … --causa … --conserto … --sha …`, append-only em `.claude/.sprint/paradas.jsonl`, ao lado do ledger de corridas. Os cinco campos são obrigatórios e o comando **sai 2 sem gravar** se algum vier vazio: é o par `conserto`+`sha` que separa "consertado" de "lembrado", e conserto que legitimamente não vira commit escreve `sem-commit` no `sha` — isso é medição, hash inventado não é. No fim da missão a skill lê o arquivo (`ledger_corridas.py paradas`) e daí monta `### Problemas (as paradas do laço)`; parada que ninguém gravou **não entra no relatório**, e o laço não relança sem a linha. Registro vazio ⇒ a seção não sai, porque o laço não parou nenhuma vez. `[confirmado — `ledger_corridas.py:registra_parada`/`le_paradas` e `python3 plugins/project-skills/lib/test_ledger_corridas.py` → `OK: ledger_corridas (2 corridas, 2 entradas)`, rodado nesta revisão]`

**E a rodada de autópsia não toca o projeto que audita — nem para mostrar o resultado.** Todo comando da skill sai de `${CLAUDE_PLUGIN_ROOT}` e não mais de `plugins/improve-workflow/…`, caminho que só resolve no repositório de quem escreveu. A única pasta em que ela escreve é `~/.claude/improve-workflow/`: o registro acumulado (`registro.jsonl`) e a página de parecer do passo 7, que vai com `--out` **obrigatório** — sem ele o `build` cai na cascata do `/visual` (fluxo 4, passo 1) e a página nasceria dentro do `.claude/visual/` do projeto auditado. O `/visual` entra pelo **nome**, por uma cópia vendorada de `resolve-plugin.sh` dentro da própria skill (declarada nos `SPECS` de `scripts/sync-shared.sh`); ausente na máquina, o resolvedor sai calado e a rodada termina dizendo que não há superfície de aprovação — as propostas ficam no `propostas.json` e nada é despejado no chat. Dois cobradores: `python3 plugins/improve-workflow/lib/test_improve_workflow_skill.py` executa os blocos sobre uma fixture e compara a árvore do projeto antes e depois, e `scripts/autopsia_check.py` confere que as frases da lei continuam no texto — este é o check **S** do `.claude/hooks/release-gate.sh`, e só roda quando o commit toca `plugins/improve-workflow/`. `[confirmado nesta rodada — a suíte fecha em "tudo verde", o check sai calado, `sync-shared.sh --check` responde "cópias vendored idênticas", e `CLAUDE_PLUGIN_ROOT=<raiz>/plugins/improve-workflow bash skills/improve-workflow/resolve-plugin.sh visual lib/visual_page.py` devolveu o caminho do irmão]`

**As três lições da autópsia anterior (2026-08-08) continuam valendo:**

- **O marcador é achado pelo NOME, nunca pela posição.** O passo `F14.2` desta mesma missão moveu `plan_state.py` de `plugins/visual/` para `plugins/project-skills/`, e o script do motor continuou apontando o caminho velho: **os 47 agentes de marcação falharam no primeiro comando e gastaram 8,45M de tokens redescobrindo o rename, cada um por conta própria**. Hoje o caminho sai de `resolve-plugin.sh project-skills lib/plan_state.py`. A régua é comparativa, e são dois comandos: `grep -c resolve-plugin plugins/project-skills/skills/sprint/SKILL.md` tem que ser > 0, e `grep -c 'plugins/visual/lib/plan_state' plugins/project-skills/skills/sprint/SKILL.md` tem que ser **0**. `[confirmado — os dois rodados nesta rodada]` A regra vale para todo caminho que o motor usa **para si mesmo**.
- **A onda inteira é marcada por UM agente, com N comandos em sequência** — não um agente por passo. A autópsia do run mediu a marcação em 7,1% do gasto, e o ganho de juntar em lote foi medido em 5%; o que decidiu não foi o número, foi que marcar é **operação já decidida**, sem julgamento a isolar. O critério ficou escrito: um agente por *tarefa de trabalho* é desenho, um agente por *operação já decidida* é desperdício.
- **O silêncio da marcação virou bloqueio nomeado.** O papel devolve `TICK_RESULT` — `{ marcados: [{ task_id, ok, motivo }] }`, uma entrada por passo tentado. `agent()` nulo, lista vazia, ou passo que o script mandou marcar e **não aparece no veredito** ⇒ Bloqueio com o id do passo. Antes disso o `agent()` do tique era chamado sem schema e sem atribuição, e o retorno era descartado: um agente gastou 127.924 tokens, fez 3 comandos, voltou com texto vazio e **nunca executou o tique** — o passo entregue ficou gravado como não feito, sem que nada acusasse. `SUITE_RESULT` e `RESERVA` sempre tiveram schema; o tique era a exceção.

**Verificado nesta rodada** — todas na casa nova, `plugins/project-skills/lib/`; o número de checks está na saída de cada uma, não aqui:

```bash
python3 plugins/project-skills/lib/test_plan_state.py     # o arquivo de plano
python3 plugins/project-skills/lib/test_cobertura.py      # o fio requisito↔tarefa
python3 plugins/project-skills/lib/test_motor_bancada.py  # roda o motor de verdade em Node
python3 plugins/project-skills/lib/test_travas_motor.py   # as travas acima, uma a uma
```

`[confirmado — as quatro saíram `OK` nesta rodada; a última fecha com *"sem a linha declarada, o mesmo texto vira DESCONHECIDO"*]`

---

## 6 · Gate de testes pré-deploy do /ship

**Dispara quando:** `PreToolUse` com matcher `Bash`, via `plugins/ship/hooks/hooks.json` → `pre-deploy-test-check.sh`, **timeout 120**. Roda em toda chamada de Bash; só age se o comando parecer deploy. `[confirmado]`

**Portas de entrada, na ordem do arquivo:**

1. `[ "${SHIP_GATE:-1}" = "0" ] && exit 0` — kill-switch.
2. `command -v jq >/dev/null 2>&1 || exit 0` — fail-open de infra, resolvido via PATH.
3. `.tool_input.command` vazio → `exit 0`. `.cwd` ausente → cai pro `$PWD` (era `exit 0`, o que fazia o gate de produção sumir em silêncio).

`[confirmado — cabeçalho e bloco de entrada lidos]`

**Detecção de deploy** — a lista de padrões é o teto real do gate. Duas invariantes de escrita que o cabeçalho documenta e a suíte trava:

- **Âncora de início-de-comando**, pra menção não disparar o gate.
- **`CMDPFX`**, o prefixo legítimo que atravessa a âncora, **enumerado** e não "qualquer palavra antes". Copiado literal do arquivo:

```
CMDPFX='([A-Za-z_][A-Za-z0-9_]*=[^[:space:];&|]*[[:space:]]+|(sudo|nohup|env|time|exec|command)([[:space:]]+-[^[:space:];&|]+)*[[:space:]]+)*'
```

Teto conhecido, escrito no próprio comentário: flag **com valor** no lançador (`sudo -u deploy ./deploy.sh`) não casa. `[confirmado]`

**Canal de saída** — o caminho que **libera** acumula avisos e emite JSON no stdout; o caminho que **bloqueia** usa `exit 2` + stderr. O comentário do arquivo cita a doc do harness: no `exit 0` a saída de um `PreToolUse` vai só pro debug log, e as exceções são `UserPromptSubmit`, `UserPromptExpansion` e `SessionStart`. `[confirmado — comentário lido; a doc do harness é `[relatado]` daqui]`

**A skill é o outro lado da costura:** `plugins/ship/skills/ship/SKILL.md` traz `### 2.5. Rodar Testes (Gate Duro)` e `### 157: Assimetria de enforcement — é DECISÃO, não buraco (2026-07-30)`. O hook é a rede no nível do harness; a skill, a regra no nível do modelo. `[confirmado — headers `###` lidos nesta rodada]`

**Verificado:** `bash plugins/ship/hooks/test_pre_deploy.sh` → **100 ok, 0 falhas** neste run, o último check sendo "hook sabotado (detecção do docker compose morta) · a suíte reprova". `[confirmado]`

---

## 7 · ARRANQUE — o que roda no SessionStart

**Quem responde ao `SessionStart` — DERIVE, não copie.** Plugin nasce e morre; a lista sai do disco:

```bash
python3 - <<'EOF'
import json, glob
for f in sorted(glob.glob('plugins/*/hooks/hooks.json')):
    for b in json.load(open(f))['hooks'].get('SessionStart', []):
        for h in b['hooks']:
            print(f.split('/')[1].ljust(16), h['command'][-60:], h.get('timeout'))
EOF
```

⚠️ **Os únicos com script PRÓPRIO no arranque, nesta rodada:** `bootstrap` (`session-sync.sh`, sem timeout), `branches`, `context-guard`, `graphify-guard`, `handoff`, `lixeiro`, `visual` (só o deps) e `project-skills`, que sozinho traz **três** — `sessionstart-organism.sh`, `sessionstart-doc.sh` e `sessionstart-plan.sh`. ⚠️ **O terceiro chegou nesta rodada**, vindo do `visual`. `[confirmado — saída do comando acima]`

⚠️ **O arranque tem muitos registros e pouco trabalho.** A maioria é o mesmo `sessionstart-deps.sh`, e ele é desenhado pra que **só a primeira execução faça algo**: ela cria um sentinel por sessão com `set -C` (o `noclobber` do shell, que é o cria-se-não-existe atômico) e as outras saem 0 caladas. O aviso sai **uma vez por sessão, não uma por plugin instalado**.

**Quantos rodam aqui: depende do que está ligado**, e a lista sai do manifesto, não de prosa:

```bash
python3 -c "
import json
def anda(o):
    if isinstance(o,dict):
        if 'name' in o and 'enabled' in o: yield o['name'],o['enabled']
        for v in o.values(): yield from anda(v)
    elif isinstance(o,list):
        for v in o: yield from anda(v)
print([n for n,e in anda(json.load(open('plugins/bootstrap/config/manifest.json'))) if not e])"
```

🔴 **Três voltaram a nascer ligados em 2026-08-08, e os três eram furos diferentes** `[confirmado — commit `4415b10`]`. O `project-skills` estava desligado depois de **receber sete skills** que mudaram de plugin (`doc`, `doc-touch`, `plan`, `qa-loop`, `sprint`, `start`, `project-skills`): quem instalasse não receberia nenhuma delas. A `vistoria` estava no mesmo caso. O `intent-guard` estava fora desde que a catraca de entrega crescia sozinha — o defeito fechou, e o religamento foi conferido antes: `claude plugin details intent-guard@pedro-plugins` mostra `Hooks (5)`, e as cinco suítes dele passam (`test_ledger`, `test_delivery_audit`, `test_hooks_capture`, `test_plan_gate`, `test_task_checkpoint`). ⚠️ **Quais da casa seguem `enabled: false` sai do comando acima cruzado com o índice da distribuição** (`.claude-plugin/marketplace.json`) — a lista em prosa envelhece a cada plugin que nasce ou morre.

⚠️ **Hook novo só entra em sessão NOVA.** `/reload-plugins` recarrega o que já está registrado; não instala nem ativa hook. O `intent-guard` foi religado no registro numa sessão e os hooks dele só passaram a rodar no arranque seguinte.

### 7.0 · O aviso de dependência ausente — o hook que os doze compartilham

`_shared/sessionstart-deps.sh` existe porque **fail-open mudo era indistinguível de "está protegendo"**: sem `jq` ou sem `python3`, o hook de plugin cai no `exit 0` de infra, o plugin segue `enabled`, e ninguém sabe que o guarda parou de guardar. O cabeçalho registra a lógica: *"O plugin segue 'enabled' e não protege nada — instale antes de confiar nos gates"*.

Três decisões de implementação que só fazem sentido juntas:

- **Ele não pode usar `jq` nem `python3`** — são exatamente o que pode faltar. Todo o parse do payload (recortar o `session_id`) é expansão de string do próprio shell, e o JSON de saída é montado à mão.
- **`python3` só conta como presente se EXECUTA**: `command -v python3 && python3 --version`. O stub da Microsoft Store existe no PATH e não roda — `command -v` sozinho o daria como instalado.
- **A chave do sentinel é sanitizada**: qualquer caractere fora de `[A-Za-z0-9._-]` no `session_id` descarta o valor e cai no `PPID`. Valor vindo do harness não vira caminho de arquivo sem passar por isso.

⚠️ **Falhar em criar o sentinel é motivo para FALAR, não para calar** — se `/tmp` estiver somente-leitura, o hook avisa de novo em vez de assumir que já avisou. Kill-switch: `BOOTSTRAP_DEPS_GATE=0`. `[confirmado — leitura do arquivo]`

### 7.0b · Como o hook acha o leitor de JSON ao lado de si — e como isso os matou todos no Windows

Todo hook de shell deste repositório carrega o `hook-json.sh` que está na mesma pasta, e
para isso precisa saber onde ele mesmo está. A receita era `HJ_DIR="${0%/*}"`, com `.` de
reserva. 🔴 **No Windows isso desinstalava o hook em silêncio, e valia para todos eles**
`[confirmado — trace de `bash -x` no runner, commit `7ae0d40`]`:

```
+ HJ_DIR='D:\a\...\hooks\scope-cop.sh'   ← ${0%/*} não cortou nada: não há '/' no caminho
+ HJ_DIR=.                                 ← caiu na reserva
+ . ./hook-json.sh ; type hj_campo ; exit 0 ← saiu calado, sem ler o evento
```

O corte no último `/` não encontra nada num caminho de barra invertida, o `$0` inteiro vira
o "diretório", o `.` de reserva não tem o arquivo, e o hook **sai 0 sem julgar nada** — o
fail-open que existe para não travar a sessão vira hook desinstalado. Nada acusa: o plugin
segue `enabled`, `claude plugin details` segue mostrando `Hooks (N)`, e a sessão inteira roda
sem guarda nenhum. É o mesmo perigo do §7.0 (fail-open mudo), agora por outro caminho.

O `$0` passa a ser normalizado antes do corte, com a mesma receita que o `hooks.json` já
aplicava no `CLAUDE_PLUGIN_ROOT` (`tr '\\' /`). Quem cobra é `scripts/test_paths_normalize.sh`,
e ele tem os dois lados — prova a normalização sob `sh`/`dash`/`bash`/`zsh` **e** reprova quem
voltar ao padrão velho. Quantos hooks já normalizam sai do disco, não daqui:

```bash
grep -rln "tr '\\\\\\\\' /" plugins/*/hooks/*.sh .claude/hooks/*.sh | wc -l
```

### Ordem

> A ordem de disparo **entre** plugins não é determinável a partir deste repositório: nenhum `hooks.json` declara prioridade e o harness não está aqui. O único ordenamento que o código fixa é **interno ao `project-skills`**: em `plugins/project-skills/hooks/hooks.json` o bloco de índice 1 do array `SessionStart` lista `sessionstart-organism.sh` **antes** de `sessionstart-doc.sh`, e o segundo depende disso — ele só reenquadra o texto para "módulos de um organismo" porque, no comentário literal, "o `sessionstart-organism.sh` já deu o banner". `[confirmado]` · Que o harness respeite a ordem do array é `[inferido]`.

### O que cada um injeta

1. **`bootstrap/session-sync.sh`** — não injeta contexto; imprime log de sync. É o cenário 1 inteiro. Todos os caminhos saem 0. `[confirmado]`
2. **`context-guard/context-guard-reset.sh`** — não injeta nada; apaga os dois arquivos `/tmp` da própria sessão e faz prune de órfãos com mais de 1 dia. `[confirmado]`
3. **`graphify-guard/sessionstart-graphify.sh`** — roda `graphify-detect.sh` e, havendo grafo, injeta `additionalContext` com cada projeto e sua frescura (`atualizado, build <data>` ou `⚠️ defasado: N arquivo(s) mudaram desde <data>`), mandando usar `graphify query` antes de grep/Explore. Grafo defasado acrescenta a ordem de oferecer `graphify --update`. Sem grafo, sai calado. **Não roda nesta máquina** (plugin desligado). `[confirmado — código lido; inatividade confirmada por `enabledPlugins`]`
4. **`handoff/sessionstart-ata.sh`** — não injeta contexto. Grava `/tmp/claude-ata-session-<sha1(cwd)[:12]>` com `{session_id, transcript_path, cwd, source}`, porque a skill `handoff` não recebe `session_id` (skill ≠ hook) e o `extract_ata.py --auto` precisa do sentinel pra achar o `.jsonl` certo. O hash tem que ser idêntico ao de `extract_ata.py`. `[confirmado]`
5. **`project-skills/sessionstart-organism.sh`** — exige `jq`, `python3` e `../lib/organism.py`. Roda `organism.py brief <cwd>`; com `.organism == true`, injeta o banner 🧬 com nome, número e nomes dos módulos, a `golden_rule` e as costuras (`• <id> (<severidade>): modA ↔ modB`). Fora de um organismo, sai calado. `[confirmado]`
6. **`project-skills/sessionstart-doc.sh`** — três saídas, todas via `additionalContext`:
   - **projeto documentado** → lista `CLAUDE.md` + nº de docs, com flag `⚠️ DEFASADA` (staleness `stale`) ou `⚠️ staleness indeterminado` (`unknown`) e `⚠️ fora do padrao atual (gen)` quando `pattern_check` reporta `in_pattern=false`;
   - **documentado mas com autoral FALTANDO** → nudge `/start gaps`, 1× por (sessão, projeto) via `${TMPDIR:-/tmp}/claude-doc-autoral-nudge-$(id -u)-${SID}-${PHASH}`, desligável com `DOC_AUTORAL_GATE=0`. ⚠️ **Lacuna parcial conta igual desde 2026-08-12**: o ramo dispara com qualquer nome em `FALTAM` (`ZERO dos N autorais` quando não há nenhum, `só K de N autorais` quando há alguns) e sempre nomeia os que faltam — antes ele só falava com zero autorais, e projeto com 2 de 6 passava calado, o que lia como conformidade;
   - **sem doc nenhuma** → oferta do `/start` mais o aviso de que o gate de plano vai barrar. Antes de afirmar ausência, o hook **reconsulta a raiz** com `doc-detect.sh --one "$PROJ"`, porque o modo descida não enxerga doc que vive acima do cwd. Os autorais cobrados são `constituicao quality-goals constraints context solution-strategy glossary` — a LEI entrou na lista em 2026-08-12, e o número impresso sai do tamanho da lista, não da mão —, mais `design` só quando `has_frontend` retorna verdadeiro. ⚠️ Não confundir com o gate de plano (fluxo 8.1), que segue contando **5** e sem `constituicao`. `[confirmado — `bash plugins/project-skills/hooks/test_sessionstart_doc.sh` → `14. a lei ausente aparece no aviso e a contagem bate com a lista (6): OK`]`
7. **`project-skills/sessionstart-plan.sh`** (⚠️ **saiu do `visual` nesta rodada**) — cenário 5. Injeta `additionalContext` com os planos abertos, o próximo passo, o caminho do arquivo e a linha de cobertura requisito↔tarefa; sem plano aberto sai calado, mas **o marco em `TMPDIR` é criado antes disso**. `[confirmado]`
8. **`branches/sessionstart-branches.sh`** — registrado no `hooks.json` do plugin `branches`. `[confirmado — registro; conteúdo não lido nesta rodada]`

9. **`lixeiro/sessionstart-orfaos.sh`** — varre o que ficou de pé de sessões anteriores. Ver o fluxo 18. `[confirmado — registro no `hooks.json`]`

**Quem pode bloquear no SessionStart:** nenhum registro, em nenhum plugin. Os que falam usam `hookSpecificOutput.additionalContext`, **com uma exceção de canal**: o `sessionstart-deps.sh` usa `systemMessage` no TOPO do JSON, porque o destinatário do aviso é o humano, não o modelo — dependência faltando é coisa que só quem está no teclado resolve. `[confirmado — leitura dos scripts desta fatia]`

---

## 8 · O PORTÃO ÚNICO DE `ExitPlanMode` — e a recusa por falta de documentação

**Dispara quando:** `PreToolUse` com matcher `EnterPlanMode|ExitPlanMode` → `plugins/project-skills/hooks/pretooluse-plan-gate.sh`, timeout 10. `[confirmado]`

### 8.0 · Um evento, um respondente

🔴 **Até esta rodada, TRÊS hooks respondiam ao mesmo `ExitPlanMode`, cada um em seu `hooks.json` e cada um com o próprio bloqueio** — três devoluções encadeadas para o mesmo plano, cada uma paga em um turno, e a ordem entre elas indeterminável. Hoje **só um se registra**, e a prova é mecânica:

```bash
python3 scripts/hook_contract.py --responde ExitPlanMode      # TOTAL: 1
```

O respondente é o gate da família de projeto. Ele **orquestra** os outros dois, que deixaram de se registrar e passaram a ser peças chamadas por **nome de plugin** (via `hooks/resolve-plugin.sh`), na ordem **pedido → página**: `intent-guard hooks/plan-gate.sh`, depois `visual hooks/pre-exitplan-visualize.sh`. `[confirmado — o laço `for PECA` em `pretooluse-plan-gate.sh`]`

Como a recusa de uma peça vira a recusa do portão:

- **`exit 2` da peça** → o portão imprime a saída dela no stderr e sai **2**. O motivo chega ao modelo palavra por palavra; nada é reescrito.
- **`permissionDecision…deny` ou `"decision"…block` no stdout** → o portão **repassa o JSON inteiro** e sai 0, porque nesse canal é o JSON que carrega a negativa.
- **Peça ausente na máquina** → `continue`. Fail-open **por peça**: quem não estiver instalado simplesmente não cobra, e o portão segue com as demais. Instalar menos plugins nunca derruba o planejamento.
- **Kill-switch da orquestração** — `PLAN_PORTAO_UNICO=0` pula o laço inteiro e deixa só o gate de documentação. Cada peça mantém o próprio interruptor (`VISUAL_GATE=0`, e o do `intent-guard`), então há dois níveis de desligamento e eles não se substituem.

⚠️ **A orquestração só vale para `ExitPlanMode`.** O `EnterPlanMode` continua chegando direto ao gate de documentação — é o momento certo, antes de o plano existir; o `ExitPlanMode` é a rede. `[confirmado — a guarda `[ "$TOOL" = "ExitPlanMode" ]`]`

**Verificado:** `bash plugins/project-skills/hooks/test_portao_unico.sh` → **6 passou · 0 falhou** nesta rodada, cobrindo os dois canais de bloqueio, o fail-open por peça ausente e o kill-switch. `[confirmado — saída da suíte]`

### 8.1 · A recusa por falta de documentação

**Portas antes de qualquer julgamento:** `PLAN_DOC_GATE=0` desliga; `command -v jq` fail-open; `project_root` não achou raiz → `exit 0`; **`doc-detect.sh` ilegível → `exit 0`** — helper ausente não é "projeto sem doc", é o gate cego (o comentário registra que um `chmod 000` fazia projeto documentado cair no caso A e ser negado sem cap). `[confirmado]`

**Os quatro desfechos:**

- **CLAUDE.md escrito à mão, sem `.claude/docs/`** → `deny` com cap de 3, mandando ler o arquivo que existe e oferecendo `/start` + `/doc` depois do plano (os nomes que a mensagem do hook realmente imprime). Repo alheio é o caso comum.
- **CASO A · nenhuma documentação** → `deny` **sempre**, sem cap. A mensagem muda conforme já haja autorais (`N de 5 documentos autorais`) ou nenhum.
- **CASO B · tem doc, não foi lida nesta sessão** → `deny` com cap `MAX_NUDGES=3`, listando os `.md` de `.claude/docs/` e acrescentando o aviso de staleness quando o caso.
- **CASO C · tem doc e já foi lida** → `exit 0`, silêncio.

`[confirmado]`

### O escape verbal

`userpromptsubmit-plan-escape.sh` (UserPromptSubmit, timeout 10) é quem ouve a frase, porque hook não lê conversa. Grava `/tmp/claude-plan-gate-escape-${SESSION}-${PHASH}` e injeta `additionalContext` avisando. Três travas escritas no cabeçalho e nas regex:

- **fronteira de palavra obrigatória** (`B='(^|[^[:alnum:]])'`) antes de todo verbo — sem ela, "esta**va sem documentação**" e "con**segue sem doc**" liberavam o gate, e são constatações, não ordens;
- **`EXTERNAL_RE`** descarta "doc **do/da/de** \<coisa\>" — doc de terceiro não é ordem sobre a nossa;
- **ambiguidade resolve pro lado seguro**: casou os dois, não libera; quem quer liberar mesmo assim usa o token inequívoco `--sem-doc` (ou `#sem-doc`). Revogação: `--com-doc` ou "exige a doc", que apaga o sentinel. `[confirmado]`

### O que libera de verdade (CASO B)

`posttooluse-doc-read.sh` (PostToolUse, matcher `Read`) escreve o sentinel `/tmp/claude-doc-guard-${SESSION}-${PHASH}` quando o Claude lê `*/.claude/docs/*`, `*/.claude/CLAUDE.md` ou `*/CLAUDE.md`. Ele também injeta o aviso **no momento do consumo** quando `pattern_check.py --project-staleness` devolve `stale` ou `unknown` — e é PostToolUse, sem `permissionDecision`, logo **estruturalmente incapaz de loopar**. `[confirmado]`

### Por que os dois lados casam: `lib-project-root.sh`

`project_root()` sobe do cwd procurando primeiro `CLAUDE.md`/`.claude/CLAUDE.md`, depois os marcadores `.git package.json pyproject.toml Cargo.toml go.mod .claude`, parando em `/` ou `$HOME`. `project_hash()` é `printf '%s' "$1" | cksum | cut -d' ' -f1`.

**A regra dura, escrita no cabeçalho: NUNCA canonicalize** — nada de `git rev-parse`, `realpath` ou `pwd -P`. `git rev-parse --show-toplevel` devolve `/private/var/…` enquanto o `posttooluse-doc-read.sh` recorta a string do `file_path` e obtém `/var/…`; no macOS isso dá `cksum` diferente e o sentinel de leitura nunca resolveria o gate. A única normalização permitida é remover a barra final, e pelo mesmo motivo. `[confirmado]`

**Verificado:** `bash plugins/project-skills/hooks/test_plan_gate.sh` → **117 passou · 0 falhou** nesta rodada. `[confirmado — saída da suíte]`

---

## 9 · ENCERRAMENTO — o que roda no `Stop`

**Quem emite no `Stop` — o inventário sai do medidor, não desta página:**

```bash
python3 scripts/hook_contract.py --stop-budget
```

Ele lista plugin, script, quantas linhas de tela o emissor produz e o `timeout`, e é a mesma varredura que o gate de deriva usa (§11a). ⚠️ **Dois emissores trocaram de dono nesta rodada:** `stop-doc-touch.sh` e `stop-plan-status.sh` respondem hoje por `plugins/project-skills/hooks/`, e o segundo veio do `visual` — que no `Stop` ficou só com `stop-anuncio-sem-acao.py`. `[confirmado — saída do medidor e o `hooks.json` dos dois plugins]`

⚠️ **O `Stop` é o único evento com ORÇAMENTO congelado, e o motivo é que ele é o mais caro em atenção humana.** `.claude/stop-budget.baseline.json` guarda, por emissor, quantas linhas ele cospe — e o total de referência é **6 linhas**, com `teto: 6`. Quem cobra é o check E2 do release-gate: um hook novo de `Stop` que fale demais reprova o commit. **Quais emissores gastam linha, e quantas, sai do `--stop-budget`** — os demais são mudos no caminho feliz. `[confirmado — leitura do baseline e a rodada do medidor]`

🔴 **O `bootstrap` não tem mais array de `Stop`** — a ordem que este parágrafo descrevia (o mecânico antes do que chama modelo) morreu junto com os três hooks apagados no `251d6ac`. Hoje o plugin registra `SessionStart×2` e `PostToolUse×1`, e nada no `Stop` [confirmado nesta rodada — o `hooks.json` do bootstrap devolve `{'SessionStart': 2, 'PostToolUse': 1}`]. O orçamento congelado do evento `Stop` (parágrafo acima) segue valendo para os emissores dos OUTROS plugins.

⚠️ **Hook Python registrado sem `python3` na frente depende do bit de execução sobreviver ao empacotamento**, e um `CLAUDE_PLUGIN_ROOT` com espaço no caminho o quebra em silêncio. Os três acima chamam o interpretador e citam o caminho entre aspas — é o padrão, não estilo. `[confirmado]`

### 9a · O teto de prosa — `stop-prose-ceiling.py`

🔴 **REMOVIDO em 2026-08-09, a pedido do dono.** Os três hooks de `Stop` do `bootstrap` (`stop-prose-ceiling.py`, `stop-forma-relato.py`, `stop-regua-relato.py`) saíram do disco e o array `Stop` do `hooks.json` deixou de existir [confirmado — `git show 251d6ac --stat` e `python3 -c "import json; print(list(json.load(open('plugins/bootstrap/hooks/hooks.json'))['hooks']))"` → `['SessionStart', 'PostToolUse']`]. O que segue é HISTÓRICO: descreve o que existiu, não o que roda. O estado em disco que eles escreviam continua lá e ninguém mais o lê.

Mecânico, roda em todo turno, custo zero de token. **Nasce ligado:** `TETO_PADRAO = 6`, e `PROSE_CEILING_MAX` só **ajusta** o número (`0` ou lixo cai no padrão). O único desligamento é `PROSE_CEILING=0`, que derruba o hook inteiro e é visível. O comentário registra por quê: em 2026-07-30 o teto virou opt-in, a variável nunca foi definida e a primeira resposta seguinte já estourou — "premissa que nasce desligada não é premissa, é comentário". `[confirmado]`

Conta linhas de prosa da última mensagem do assistente **descontando** blocos ``` (que são prova e não têm teto) e linhas de tabela/regra. Quatro problemas podem se acumular:

1. `len(prosa) > TETO`;
2. **retórica no meio** — a regex `RETORICA` nomeia os padrões da calibração (`vale notar`, `dito isso`, `em outras palavras`, `o que eu fiz foi`, `deixa eu explicar`, entre outros);
3. **menu de opções no fim** — bullet começando por `opção`/`alternativa`;
4. **NOVO · pergunta fechada sem veredito na 1ª linha.** Três regex trabalham juntas: `PERGUNTA_FECHADA` casa a cauda (últimos 200 chars) do último prompt do usuário; `PERGUNTA_ABERTA` **isenta** quando há pronome interrogativo (`como`, `por que`, `o que`, `qual`…), porque pergunta aberta pede explicação, não sim/não; `ABRE_COM_VEREDITO` exige que a primeira linha não-vazia da resposta comece por veredito — a lista literal inclui `sim`, `nao/não`, `confirmo`, `nenhum`, `zero`, `passou`, `falhou`, `funciona`, `resolvido`, `pronto`, `feito`, `em parte`, `parcial`, `ainda nao`, `confirmado`, `inferido`, `depende`. O comentário do bloco registra o caso real que a originou: a resposta trouxe a varredura inteira com prova, não dizia sim nem não, e a devolutiva foi "você não me respondeu". `[confirmado]`

**Saída:** `exit 2` com a mensagem no stderr. Anti-loop de `MAX_BLOQUEIOS = 2` por resposta, chaveado por `sha1(session_id + texto_inteiro)[:16]` — o hash é do texto **inteiro** porque o output style manda a 1ª linha ser estável, então colisão de prefixo era o caso comum. Estourado o teto de bloqueios, o hook **desiste** e registra em `bypass.log` em vez de travar a sessão. `[confirmado]`

**Rastro:** `batida()` grava **toda** execução, não só as que barram, em `CLAUDE_DIR/state/prose-ceiling/batidas.log`. `CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))` — mesma regra do `conformance.py:CLAUDE_DIR` e do `scope-cop.sh`. Sem isso, "não rodou" e "rodou e aprovou" eram indistinguíveis. `[confirmado]`

### 9b · O juiz de forma do relato — `stop-forma-relato.py` (novo nesta rodada)

🔴 **REMOVIDO em 2026-08-09, a pedido do dono.** Os três hooks de `Stop` do `bootstrap` (`stop-prose-ceiling.py`, `stop-forma-relato.py`, `stop-regua-relato.py`) saíram do disco e o array `Stop` do `hooks.json` deixou de existir [confirmado — `git show 251d6ac --stat` e `python3 -c "import json; print(list(json.load(open('plugins/bootstrap/hooks/hooks.json'))['hooks']))"` → `['SessionStart', 'PostToolUse']`]. O que segue é HISTÓRICO: descreve o que existiu, não o que roda. O estado em disco que eles escreviam continua lá e ninguém mais o lê.

Vizinho deliberadamente diferente do teto: **chama um modelo**, então só roda quando a resposta é um **relato**. Nenhum padrão distingue "6 linhas densas" de "6 linhas vazias" — para isso precisa de um leitor. `[confirmado — docstring]`

- **Gatilho (`e_relato`)** — precisa de pelo menos um bloco ``` **e** `len(prosa) >= MIN_PROSA` com `MIN_PROSA = 2`. O comentário justifica o 2: o relato canônico bom tem 2 linhas de prosa e 4 de prova; exigir 4 deixava passar justamente os relatos que dão certo. Resposta curta e conversa não chegam ao modelo — seriam a maioria dos turnos, a ~4,5s cada.
- **O que julga** — só a FORMA, em quatro critérios nomeados no `PROMPT`: limpeza, clareza, didática, escaneabilidade. Bloco de código é **prova**: não conta como excesso e a ausência dele não reprova.
- **Protocolo** — `claude -p --model <FORMA_RELATO_MODEL>` (default `haiku`), `timeout=TIMEOUT_S` (25s), entrada truncada em `texto[:6000]`. Espera uma linha: `PASSA` ou `REPROVA: <defeito em até 12 palavras>`.
- **Recursão** — o filho herda os hooks deste marketplace e chamaria o juiz de novo; o pai injeta `FORMA_RELATO="interno"` no ambiente do subprocesso, e o `main()` sai **sem nem gravar batida** nesse modo. `FORMA_RELATO=0` é o kill-switch do dono e **grava** batida.
- **Fail-open total** — `claude` ausente do PATH, `TimeoutExpired`, `OSError`, `returncode != 0`, saída vazia ou veredito ilegível: tudo devolve `(True, motivo)`. "Guarda que trava a sessão por infra é pior que guarda nenhum."
- **Anti-loop** — `MAX_BLOQUEIOS = 2` por resposta, contador em arquivo chaveado por `sha1(session_id + texto)[:16]`, verificado **antes** de gastar o modelo.
- **Estado com variável própria** — `ESTADO = FORMA_RELATO_STATE` ou `CLAUDE_DIR/state/forma-relato`. O comentário explica a separação: isolar o teste via `CLAUDE_CONFIG_DIR` tirava a credencial do `claude -p` junto, e o juiz passava a aprovar tudo por fail-open.
- **Bloqueio** — `exit 2` com "FORMA DO RELATO REPROVADA: \<motivo\>", mandando reescrever o relato inteiro (não anexar resumo no fim) e lembrando que o que não couber vira `/visual` em HTML.

`[confirmado — arquivo lido integralmente]`

**Teto conhecido, escrito na própria docstring:** com um `CLAUDE_CONFIG_DIR` sem credencial, `claude -p` sai com `rc=1` e "Not logged in", e o juiz cai no fail-open sem barrar nada. O motivo fica na batida como `juiz sem resposta`, e é assim que se descobre que ele está mudo em vez de aprovando. `[relatado — medição citada no arquivo, não reproduzida aqui]`

**Estado do rastro nesta máquina** (`~/.claude/state/`, contado mecanicamente por script neste run):

```
forma-relato/batidas.log   {'sem texto': 12}                              mtime 31/jul 18:46
prose-ceiling/batidas.log  {'aprovou': 6, 'sem texto do assistente': 36}
prose-ceiling/bypass.log   não existe
```

Ou seja: **os dois hooks estão executando**, o teto de prosa já aprovou 6 respostas e nunca precisou do bypass, e o juiz **ainda não julgou nenhum relato** — todas as 12 batidas dele são `sem texto`, o caminho em que `ultima_msg_assistente` não achou texto do assistente no transcript. Não há nenhuma batida `nao e relato` nem `julgou`. `[confirmado — contagem por script nesta rodada; a causa do `sem texto` não foi investigada aqui]`

---

## 10 · Conformidade: descobrir que um guarda está MUDO

**Dispara quando:** o passo 2 da skill `bootstrap:setup` roda `plugins/bootstrap/lib/conformance.py` — que **confere e não conserta**.

Dois checks fazem a mesma pergunta sobre guardas diferentes, e ambos só cobram de quem tem `bootstrap@…` ligado em `enabledPlugins` (numa máquina sem o plugin não há guarda pra rodar, e acusar ali seria desvio inventado):

- **`check_teto_rodou`** — lê `CLAUDE_DIR/state/prose-ceiling/batidas.log`. Arquivo ausente → desvio "o guarda de prosa nunca executou". Última batida com mais de 24h → desvio "está mudo há N h". Senão, conforme com o resumo por motivo. A docstring registra o caso que o originou: uma resposta de 9 linhas passou às 09:21 e o primeiro registro de bloqueio era das 09:36 — como só existia log de bloqueio, "não rodou" e "rodou e aprovou" eram indistinguíveis e o check chegou a carimbar "nenhuma resposta furou o teto" com o guarda mudo.
- **`check_juiz_rodou`** (novo nesta rodada) — lê `CLAUDE_DIR/state/forma-relato/batidas.log`. Tem **um modo de falha a mais** que o guarda mecânico, e é ele que o check existe pra pegar: soma as batidas cujo motivo começa com `juiz sem resposta` e, se esse total superar as batidas `julgou`, acusa **"o juiz está mudo: N execução(ões) sem resposta do modelo"**, com o conserto apontando a causa comum (credencial: `claude -p` sai com `rc=1` e 'Not logged in'; teste `claude -p --model haiku ok`). Arquivo ausente → desvio cujo conserto manda conferir se `stop-forma-relato.py` está no array `Stop` de `plugins/bootstrap/hooks/hooks.json`, "hook fora dele é ignorado em silêncio e `claude plugin validate` passa mesmo assim". Mais de 24h sem batida → "está mudo há N h".

Ambos usam o helper `le_batidas(log)`, que devolve `(contagem por motivo, idade da última em horas, resumo legível)`. `check_bypass_teto` lê o `bypass.log` e transforma o teto conhecido do hook — desistir após 2 bloqueios — em número visível. `[confirmado — `conformance.py` lido no bloco `le_batidas`…`check_bypass_teto`, e a lista de checks registrada no fim do arquivo]`

**Versão do plugin nesta rodada:** `bootstrap` em **1.8.5**. `[confirmado — `plugins/bootstrap/.claude-plugin/plugin.json`]`

**Verificado:** `python3 plugins/bootstrap/lib/test_conformance.py` → **59 ok · 0 FAIL** neste run. A suíte cobre o juiz em quatro checks nomeados: "acusa juiz que nunca executou", "acusa fail-open por juiz sem resposta", "acusa juiz parado ha mais de 24h" e "nao cobra juiz de quem nao instalou o bootstrap". `[confirmado]`

---

## 11 · Varredura de contrato dos hooks

`scripts/hook_contract.py` mede as **5 propriedades** que separam um gate saudável de um que trava ou se desliga sozinho, tal como enumeradas no cabeçalho:

```
1. canal de saída  — como o hook fala (bloqueia? informa? só loga?)
2. cap anti-loop   — quem bloqueia tem teto de devoluções, escopado por sessão?
3. kill-switch     — dá pra desligar sem editar o arquivo?
4. binário fixo    — usa caminho absoluto de ferramenta?
5. fail-open       — guarda a ausência das ferramentas que usa?
```

Os três canais de bloqueio coexistem hoje e o script **não normaliza, só mede**: `exit 2` (intent-guard, visual), `permissionDecision:"deny"` (project-skills, guardrails) e `"decision":"block"` (handoff). Cap conta em duas formas — contador (`-ge` perto de um `exit 0`, dentro de `CAP_ESCAPE_WINDOW = 8` linhas) e sentinela (`[ -f "$SENTINEL" ]` e variantes). O cabeçalho é explícito sobre a direção do erro: detectar um cap que não existe é o erro caro, porque o script deixaria de acusar um gate que trava de verdade.

### 11a · `--stop-budget` — o custo somado do fim de turno

**Novo em 2026-08-02.** As 5 propriedades acima medem cada hook **isolado**; nenhuma mede o CONJUNTO. Vários hooks disputam o `Stop` neste marketplace (quantos, o próprio comando abaixo diz), cada um respeitando o próprio teto, e o dono viu na tela `6/9 · 35s · ↓773 tokens` com quatro blocos de progresso de plano. Todo emissor estava dentro do que prometia — **o conjunto é que não tinha dono**.

```bash
python3 scripts/hook_contract.py --stop-budget       # humano
python3 scripts/hook_contract.py --stop-budget --json
python3 scripts/hook_contract.py --stop-budget --baseline .claude/stop-budget.baseline.json
```

A saída traz uma linha por emissor (plugin · script · linhas · timeout), o `TOTAL` contra o teto de referência, e — em bloco separado — os plugins de **outros** marketplaces instalados na máquina. **Rode; não copie o número daqui.** `[confirmado — rodado nesta rodada]`

⚠️ **O total desta rodada CAIU, e a queda é informação, não folga.** O maior gastador do fim de turno era `stop-plan-status.sh`; ele mudou de plugin (do `visual` para o `project-skills`) e passou a medir bem menos linha na bancada do medidor. **Total que encolhe sem ninguém ter enxugado texto é sinal de emissor que deixou de falar** — o medidor roda cada emissor num sandbox povoado, e um hook que mudou de casa pode estar calando por não achar o que lê. Confira contra `.claude/stop-budget.baseline.json` antes de recongelar: o gate só barra a SUBIDA, então uma queda por defeito passa limpa por ele. `[inferido — a queda foi medida nesta rodada; que a causa seja a mudança de casa NÃO foi reproduzida, e é a primeira hipótese a testar]`

✅ **Emissor que só fala quando barra mede 0 linha** — `stop-regua-relato.py` é o caso: barrar sai por `exit 2` no stderr, fora do orçamento de `systemMessage`. `[confirmado — `--stop-budget` rodado nesta rodada]`

⚠️ **Plugin de OUTRO marketplace também emite no `Stop`, e até 2026-08-03 não aparecia aqui.** Quem paga o fim de turno é a máquina, não o repositório — instalar o `impeccable` (que registra `PostToolUse` + `Stop`) deixou o buraco visível. Eles entram no relatório e ficam **fora do total gateado**, de propósito: o retrato viaja no git, o que cada máquina instala não, e um total que os incluísse faria o mesmo commit passar numa máquina e barrar noutra. Dois detalhes que só apareceram medindo `[confirmado]`:

- **Mede pelo COMANDO registrado, não por caminho de script.** O hook do `impeccable` é um one-liner de shell que chama `node`, e o regex de `.sh|.py` do laço principal não o alcança. `CLAUDE_PLUGIN_ROOT` é interpolado por eles, então o sandbox aponta essa var para a raiz do plugin instalado — sem isso o hook não acha o próprio script e mede zero pelo motivo errado.
- **Só a versão VIVA entra.** O cache guarda toda versão já instalada; sem filtro o `codex` aparecia duas vezes (1.0.3 e 1.0.6) e o relatório media código morto. O índice vivo está em `installed_plugins.json → ["plugins"]`, **não** na raiz do arquivo. Sem o índice, mede a mais em vez de a menos — esconder emissor é o defeito que este medidor existe pra evitar.

Roda cada emissor num sandbox (`HOME`, `CLAUDE_CONFIG_DIR`, `TMPDIR` e `cwd` temporários) porque emissor de `Stop` escreve estado, e medir não pode sujar a máquina de quem mede.

⚠️ **Ele contava o ENVELOPE, não o texto — corrigido em 2026-08-02.** Emissor de `Stop` imprime `{"systemMessage": "…"}`, e contar a saída crua media três linhas de JSON com o texto inteiro dentro. Um resumo de 5 linhas na tela era reportado como 3, e o teto estava sendo comparado contra um número menor que o real. `_linhas_visiveis()` desembrulha `systemMessage`/`reason`/`additionalContext` antes de contar; texto puro em stderr cai no caminho de baixo, inalterado. **O total no mesmo cenário foi de 4 para 6** — não sobrava, encostava. `[confirmado]`

⚠️ **O sandbox precisa de marcador de projeto, e o `HOME` tem que ficar FORA dele.** `resolve-dir.sh` aplica a cascata raiz-git → marcador → `~/Desktop`, e a busca por marcador **para ao chegar no `HOME`**. Com `HOME` == sandbox a cascata caía no Desktop e o medidor lia os planos reais do dono; depois de plantar um `CLAUDE.md`, ela ainda caía no fallback, e os 4 planos que o próprio medidor criava **nunca eram lidos** — o que ele reportava era o aviso de plano AUSENTE, o cenário oposto ao que declara medir. Hoje são dois diretórios irmãos, `lar/` e `projeto/`. `[confirmado]`

⚠️ **Sandbox vazio mede o caso trivial.** Emissor calado num projeto sem nada é o esperado; o que interessa é o pior caso realista. O sandbox nasce povoado com **4 planos ativos e um transcript com 5 edições** — que é o gatilho das cobranças.

**Virou gate em 2026-08-02, e barra a DERIVA, não o número.** `--stop-budget --baseline <retrato>` sai 1 quando o total **sobe** em relação a `.claude/stop-budget.baseline.json`, nomeando quem subiu e quem é emissor novo. Teto absoluto não serviria: o total já está em 6 de 6, então exigir um número barraria o próximo commit que tocasse hook sem nada ter piorado. Retrato ilegível **não** barra. Pendurado no check **E2** do `release-gate.sh`, no mesmo gatilho do E (só quando o commit toca `plugins/*/hooks/`). Recongelar é explícito: `--stop-budget --json > .claude/stop-budget.baseline.json`. `[confirmado — retrato magro devolve rc=1; 6 checks em test_hook_contract.py]`

Uso: `--json` para a medida crua, `--fail-on high` para virar gate (exit 1), `--baseline f.json` para ver só o que piorou. ⚠️ O próprio cabeçalho classifica: **isto é grep sofisticado, não verdade** — o achado vem com linha e trecho para a conferência custar segundos. `[confirmado — cabeçalho e blocos de regex lidos; script não executado nesta rodada]`

⚠️ **O detector de kill-switch só conhecia shell até 2026-08-02.** Os quatro padrões eram todos de `[ "${X:-1}" = "0" ]` e parentes, então **todo guarda escrito em Python era acusado de não ter interruptor que tem** — a regra R3 disparava em falso. Um quinto padrão lê `os.environ.get("X") == "0"`. Alarme falso importa porque treina a ignorar o relatório. `[confirmado — 2 checks em test_hook_contract.py]`

---

## 12 · Guardrails: o que acontece a cada Edit/Write

`plugins/guardrails/hooks/hooks.json` registra 5 hooks — 4 em `PreToolUse` e 1 em `PostToolUse`:

- **`PostToolUse` `Edit|Write` → `lint-and-typecheck.sh`** (30s). Kill-switch `LINT_GATE=0`; `jq` via PATH com fail-open. JS/TS: sobe a árvore procurando `node_modules/.bin/eslint` e depois `tsconfig.json`/`jsconfig.json` — buscas **independentes**, porque em monorepo as raízes podem diferir. O comentário registra a armadilha corrigida: capturar o exit code **antes** do pipe, porque `$(cmd | head)` reporta o status do `head` e o bloco de erro nunca disparava. Python: `ruff` + `mypy`, ambos opcionais. `[confirmado — cabeçalho e bloco JS/TS lidos; corpo Python não lido]`
- **`PreToolUse` `Edit|Write` → `scope-cop.sh`** (25s). Kill-switch `SCOPE_COP_GATE=0` **antes de ler o stdin**. Decisão durável em `$CFG/guardrails/scope-cop.mode` com conjunto **fechado** `deny | warn | off` (vazio = default `deny`); grafia errada cai no default e vai pro log, porque errar a grafia entregaria o gate mais severo a quem pediu o mais brando. `CFG = ${CLAUDE_CONFIG_DIR:-$HOME/.claude}` — mesma regra do `conformance.py` e do `stop-prose-ceiling.py`, e o comentário explica: com `$HOME` cravado, o hook leria o modo numa pasta e o conformance varreria `**/*.mode` noutra. Circuit breaker `MAX_STREAK=3` **por sessão** (`scope-cop.blockstreak.<session_id>`), com poda de arquivos de sessões mortas com mais de 1 dia. Filtro barato antes de chamar modelo: só julga `*.html *.htm *.svelte *.css *.scss *.sass *.less *.tsx *.jsx *.vue *.astro`. `[confirmado — primeiras ~110 linhas lidas]`
- **`PreToolUse` `Agent` → hook do tipo `prompt`** — é o único hook `type: "prompt"` deste marketplace: um classificador que **permite** o spawn quando o input tem `team_name` (é Agent Teams), **nega** quando não tem e o prompt exige Agent Teams/TeamCreate/waves/swarm, e **permite** na dúvida. `[confirmado — prompt lido literal no hooks.json]`
- **`PreToolUse` `AskUserQuestion` → `askq-humanize.sh`** (10s). `[confirmado — registro; conteúdo não lido nesta rodada]`
- **`PreToolUse` `Edit|Write` → `pretooluse-artefato-regua.py`** (10s) — **novo em 2026-08-03**, e é a PORTA da régua de forma. Bloco próprio no `hooks.json`, com o mesmo matcher do `scope-cop.sh`: são dois julgamentos diferentes sobre a mesma escrita. Detalhe no cenário 15. `[confirmado]`

---

## 13 · Geração de deck pelo /slides

**Sem hooks — é skill pura:** `plugins/slides/` contém apenas `lib/` e `skills/`. `[confirmado — `ls plugins/slides/`]`

Dois modos com contratos de conteúdo **opostos**, e a skill manda decidir qual antes de tudo: **A · transcrição** (renderiza fiel um `.md` já redigido, regra de ouro "o texto é do autor") e **B · explicador** (a skill autora a didática). Pedido ambíguo → perguntar, não chutar. `[confirmado — `SKILL.md`, seção "Dois modos de uso (despacho)"]`

No modo A a regra de ouro deixou de ser instrução e virou propriedade da construção: quem transcreve é `lib/md2deck.py`, e o texto de corpo sai dos tokens do `.md` sem passar por geração. As únicas strings criadas pelo compilador são os enumeradores (`01`, `02`) e o eyebrow derivado dos headings. `[confirmado — SKILL.md]`

**Gate de fidelidade** — `scripts/check_fidelity.py <deck.html> <fonte.md>` extrai cada bloco de texto do deck e confere se aparece literalmente na fonte, normalizando acento, pontuação e caixa (`norm()` usa NFKD + remoção de combining chars). Só examina `BLOCK_TAGS = {"li","p","h3","h4"}` e as divs de classe `pull statement def ex lead sub`; `h1`/`h2` ficam de fora porque título de slide deriva do heading por natureza. `MIN_WORDS = 6` — abaixo disso é rótulo, não prosa do autor. Exit 1 se houver suspeita, 0 se limpo. É exatamente esse conjunto de isenções que faz um deck **compilado** passar por construção. `[confirmado — docstring e constantes de topo lidas]`

---

## 14 · graphify-guard: aviso no arranque, `deny` na primeira busca cega

**Registrado, desligado nesta máquina.** `plugins/graphify-guard/hooks/hooks.json` declara `SessionStart` → `sessionstart-graphify.sh` (10s) e `PreToolUse` com matcher `Grep|Glob|Bash` → `pretooluse-graphify-guard.sh` (10s). O plugin não está em `enabledPlugins` e o manifest o traz `enabled: false`. `[confirmado]`

O guard de busca: kill-switch `GRAPHIFY_GATE=0` antes do stdin; `command -v jq` fail-open. Monta a lista de diretórios candidatos a partir do `cwd` mais o `.tool_input.path` (Grep/Glob) ou os tokens que existem como caminho no comando (Bash). Em `Bash`, só intercepta busca cega de texto/arquivo — a regex exige `grep|egrep|fgrep|rg|ripgrep|ag|ack|find` com fronteira de palavra, e tudo o mais (inclusive `graphify …`) passa. Havendo grafo, nega uma vez por sessão e redireciona pro `graphify query`. `[confirmado — primeiras ~45 linhas lidas]`

O caso que o cabeçalho nomeia como coberto é o do monorepo-container: mesmo com o cwd num diretório sem grafo próprio, ele desce pelos tokens de caminho da busca até achar grafo em subprojeto. `[relatado — comentário do arquivo; não reproduzido]`

---

## 15 · A régua de forma recusa no ponto de uso — PORTA e REDE

**Novo em 2026-08-03.** A régua de estilo (`_shared/regua_texto.py`, vendorada; as quatro checagens e os perfis estão em `patterns.md §2.7`) deixou de valer só para quem passa pelo gerador de página. Dois hooks a cobram nos dois canais por onde o texto escapava. `[confirmado]`

**Por que DOIS, e não um** — o motivo está escrito na docstring da porta: *"a rede pega o relatório que eu DIGITO no terminal e nunca vê arquivo; esta porta pega o arquivo e nunca vê o terminal."* Nenhum dos dois alcança o alcance do outro. `[confirmado]`

### 15a · A PORTA — `guardrails/hooks/pretooluse-artefato-regua.py`

**Dispara quando:** `PreToolUse` com matcher `Edit|Write`, timeout 10. `[confirmado]`

1. **Kill-switch primeiro** — `ARTEFATO_REGUA=0` sai 0 antes de ler o stdin.
2. **Alcance deliberadamente estreito** — `alcanca()` exige extensão `.md`/`.html` **e** o caminho conter `/.claude/visual/` ou `/.claude/reports/`. Documentação, código e config ficam de fora: a régua governa artefato de **leitura**, não todo texto do repositório.
3. **De onde vem o texto** — `content` (o `Write` manda o arquivo inteiro) ou `new_string` (o `Edit` manda só o pedaço novo).
4. **Isenção da origem** — `.html` que contenha `visual_page.py` no corpo já passou pela régua no gerador; medir de novo seria cobrar duas vezes o mesmo texto.
5. **O que conta como redação** — `linhas_de_redacao()` descarta o que está dentro de ``` (prova é literal por obrigação), o vazio, e toda linha que abre com `$ # | < ! >`, que é comando, título, tabela, markup ou citação. O marcador de bullet sai com `lstrip("-*• ")`.
6. **A medida** — `erros_de_estilo(linhas, "o artefato", "pagina")`, perfil de página/relatório/diagnóstico.
7. **Recusa** — `exit 2` com até 6 problemas no stderr, mais a instrução de quebrar em bullets de uma frase e de pôr saída crua dentro de bloco de código.

**Fail-open em tudo que não é violação** — régua vendorada ausente, `exec_module` que levanta, JSON ilegível, caminho fora do alcance, texto vazio: sai 0 mudo. O comentário dá o motivo: *"gate de forma que derruba a escrita por causa da própria falha é pior que a prosa que ele evitaria."* `[confirmado — arquivo lido integralmente]`

**Verificado:** `python3 plugins/guardrails/hooks/test_artefato_regua.py` → **23 checks ok · 0 falhas** neste run, o último sendo "a PORTA (escrita de arquivo) está no disco". `[confirmado]`

### 15b · A REDE — `bootstrap/hooks/stop-regua-relato.py`

🔴 **REMOVIDO em 2026-08-09, a pedido do dono.** Os três hooks de `Stop` do `bootstrap` (`stop-prose-ceiling.py`, `stop-forma-relato.py`, `stop-regua-relato.py`) saíram do disco e o array `Stop` do `hooks.json` deixou de existir [confirmado — `git show 251d6ac --stat` e `python3 -c "import json; print(list(json.load(open('plugins/bootstrap/hooks/hooks.json'))['hooks']))"` → `['SessionStart', 'PostToolUse']`]. O que segue é HISTÓRICO: descreve o que existiu, não o que roda. O estado em disco que eles escreviam continua lá e ninguém mais o lê.

**Dispara quando:** `Stop`, timeout 10, **antes** do `stop-forma-relato.py` no mesmo array — o mecânico vem antes do que chama modelo. `[confirmado]`

**Divisão de trabalho com o vizinho, pra não haver guarda em dobro** (escrita na docstring): o `stop-prose-ceiling.py` mede **VOLUME** (quantas linhas de prosa); esta régua mede os **BULLETS** (as linhas que abrem com `•`, `-` ou `*` seguidos de espaço). `[confirmado]`

1. Kill-switch `REGUA_RELATO=0`, e `stop_hook_active` sai calado.
2. `ultima_msg_assistente()` lê o `.jsonl` de trás pra frente, pulando `isSidechain`.
3. `bullets_do_texto()` remove os blocos ``` com regex, casa `^([•\-*])\s+(.*)$` e descarta o que sobrar só de traço ou barra de tabela. O espaço exigido depois do marcador é o que separa `- item` de `**Gate verde**: …`, que abre com `*` e não é lista.
4. **A chamada é UMA, com a LISTA inteira:** `erros_de_estilo(itens, "relato", "pagina")`. Bullet a bullet, a quarta checagem — máximo 6 bullets por bloco — **nunca dispararia**, porque ela só arma quando o valor chega como lista (`lista = isinstance(v, (list, tuple))` no `regua_texto.py`); 20 bullets curtos passavam limpos. As outras três saem iguais nos dois modos, só o rótulo muda. `[confirmado — comentário do hook e o corpo de `erros_de_estilo`]`
5. **Perfil `pagina`, por derivação e não por escolha** — o `regua_texto.py` define esse perfil como «página, relatório, diagnóstico», e o relato de fim de turno é um relatório. **Não** é o perfil `hook`, que proíbe `**` e crase porque o canal do emissor de hook não renderiza markdown — e o canal do CLI renderiza.
6. **Rastro e anti-loop, no molde dos vizinhos** — `batida()` grava **toda** execução em `<estado>/batidas.log` (senão "não rodou" e "rodou e aprovou" são indistinguíveis); `MAX_BLOQUEIOS = 2` por resposta, chaveado por `sha1(session_id + texto)[:16]`, e o terceiro bloqueio vira linha em `bypass.log` em vez de travar a sessão. Estado em `REGUA_RELATO_STATE` ou `CLAUDE_DIR/state/regua-relato` — variável própria, pelo mesmo motivo do juiz de forma: dá pra isolar o teste sem mexer no `CLAUDE_CONFIG_DIR` real.

**Fail-open em tudo que é infra** — régua ausente do vendoring (`ImportError`), payload ilegível, transcript que não abre: sai 0, com a batida registrando o motivo. `[confirmado — arquivo lido integralmente]`

**Verificado:** `bash plugins/bootstrap/hooks/test_bootstrap_hooks.sh` → **70 ok · 0 FAIL** neste run (eram 52 antes), com a fatia nova cobrindo as quatro checagens uma a uma, o kill-switch, a isenção do bloco de prova, a linha em negrito que não é bullet e o bypass depois de 2 bloqueios. `[confirmado]`

---

## 16 · O tier do motor chega como DADO, não como número na skill

**Dispara quando:** a casca de `/sprint` (ex-`/sovai`) ou de `/qa-loop` vai disparar o Workflow do motor. ⚠️ **As duas skills moram hoje em `plugins/project-skills/skills/sprint/SKILL.md` e `plugins/project-skills/skills/qa-loop/SKILL.md`, e os plugins que as hospedavam foram EXTINTOS** — quem quiser conferir se um nome de plugin ainda existe consulta o índice da distribuição (`.claude-plugin/marketplace.json`), nunca uma lista escrita em doc. `[confirmado — `grep -n 'r8_tiers' plugins/project-skills/skills/*/SKILL.md` neste run e o índice lido]`

**O drift que isto existe pra matar, medido em 2026-08-03:** trocar seis valores custou 45 substituições em dois `SKILL.md`, três saíram invertidas e duas sobreviveram a dois verificadores. A causa não era descuido — era o número morar em quinze lugares. `[relatado — docstring de `_shared/r8_tiers.py`]`

**Os passos:**

1. **O script existe e é lido do disco** — `python3 "<skill_dir>/references/r8_tiers.py" args` monta `{model, tiers: {<knob>: {effort}}}` a partir de `r8-tiers.json`. Saída medida nesta rodada: `model: "opus"` e os seis knobs `decompose`, `coordinate`, `executor`, `mechanical`, `diagnose`, `finalize`. `[confirmado — `python3 _shared/r8_tiers.py args`]`
2. 🔴 **O passo em que o valor entra mudou DUAS vezes, e a segunda é de 2026-08-09.** Primeiro ele saiu de `args.tiers` lido em tempo de execução e virou constante literal escrita no texto do script. Agora ele nem é transportado: a constante já está **gravada no arquivo do motor**, `plugins/project-skills/skills/sprint/references/motor.js`, e a casca só passa o caminho.
3. **Quem impede a constante de envelhecer é teste, não lembrança** — `plugins/project-skills/lib/test_motor_js.py` lê `r8-tiers.json` e compara knob a knob com o que está escrito no `motor.js`; espelho defasado reprova a suíte do plugin. `[confirmado — `python3 plugins/project-skills/lib/test_motor_js.py` → "test_motor_js: 196 checagens verdes" nesta rodada; o número cresce com a suíte, o que vale é o comando]` <!-- acopla-ok: saida crua de comando citada como prova, e o proprio texto diz que o que vale e o comando -->

⚠️ **O motivo da primeira inversão é medido, e contradiz o que este doc afirmava antes:** *"o canal que levava esse valor até o script FALHAVA, e `args.tiers` chegava `undefined` — o que matava o motor na primeira volta"*. A versão anterior tratava essa morte como "a falha certa"; na prática ela acontecia por defeito de canal, não por contrato violado, e o motor morria sem que ninguém tivesse mexido em tier nenhum.

**A régua não mudou; o MOMENTO mudou duas vezes.** O valor continua nascendo em `_shared/r8-tiers.json` e nunca é inventado na skill. Trocar um tier é editar o JSON compartilhado, rodar `scripts/sync-shared.sh` e espelhar a constante no `motor.js` — o teste reprova se o espelho ficar para trás. `[confirmado — `plugins/project-skills/skills/sprint/SKILL.md`, seção R8]`

**Os outros dois usos do mesmo módulo**, ambos lendo o mesmo JSON: `render` gera a tabela de `r8-tiers.md` (ninguém a digita), e `check` falha se o markdown divergir do JSON **ou** se algum `SKILL.md` voltar a carimbar um `effort` literal ao lado de um `model:`. A regex isenta a menção legítima ao nome do knob e o `effort: "low"` do relatório do `/fallow`, que não tem nada com o R8. `[confirmado — `r8_tiers.py:LITERAL` e `python3 _shared/r8_tiers.py demo` → "demo ok"]`

**Trocar um tier é editar `_shared/r8-tiers.json` e rodar `scripts/sync-shared.sh`** — nenhum `SKILL.md` muda. `[confirmado]`

---

## 17 · A ponte de visão por MCP — see_image quando o modelo não tem olhos

**Sem hooks — é MCP puro:** `plugins/vision/` contém apenas `vision_mcp.py`, `.mcp.json` e `.claude-plugin/plugin.json` (v0.1.0). O servidor entra no catálogo do Claude pelo `.mcp.json`: transporte `stdio`, `python3 ${CLAUDE_PLUGIN_ROOT}/vision_mcp.py`. `[confirmado — leitura dos três arquivos nesta rodada]`

**Dispara quando:** o modelo em uso não tem visão — ler a imagem via `Read` devolve "Unsupported Image" — e o Claude precisa do conteúdo dela. A docstring registra o caso: *"Este server expõe UMA tool, `see_image`, que o Claude chama quando precisa entender uma imagem."* `[confirmado — `vision_mcp.py:1-7`]`

**Passos:**

1. **O Claude chama `see_image(caminho, pergunta)`** — só `path` é obrigatório; sem `question`, o servidor pergunta *"O que exatamente esta imagem mostra? Descreva em detalhe, transcrevendo o texto visível."* `[confirmado — `vision_mcp.py:61-91`]`
2. **O servidor codifica e POSTa** — lê o arquivo, codifica em base64 e monta o payload no padrão OpenAI-compatible: `messages[0].content` com `image_url` (`data:<mime>;base64,…` — o mime por extensão: png/jpg/jpeg/gif/webp, default png) + a pergunta em texto, `max_tokens: 1024`. POST para `BASE.rstrip("/") + "/chat/completions"` com `timeout=TIMEOUT`. `[confirmado — `vision_mcp.py:48-120`]`
3. **O servidor VL responde em texto** — a descrição sai de `choices[0].message.content` e volta como `{content: [{type: "text", text}], isError: false}`. `[confirmado — `vision_mcp.py:112-116`]`
4. **O Claude usa a descrição** — o texto entra no contexto e ele segue a tarefa; é o contrato da tool. `[confirmado — docstring de `vision_mcp.py:2-7`]`

**De onde vem o endpoint — o servidor de visão NÃO mora no plugin** (é infra privada de quem instala). Três fontes, nesta ordem: env `QWEN_BASE`/`QWEN_MODEL`/`QWEN_TIMEOUT` (default 180s) → `~/.claude/vision.json` com `{"base": …, "model": …}` → falha com mensagem pedindo a config, **nunca um endpoint chutado**. `[confirmado — `vision_mcp.py:9-45`]`

**Falhas mapeadas** — todas devolvem `isError: true` com o texto prefixado `❌`: servidor não configurado, arquivo inexistente, leitura do arquivo falhou, `HTTPError` do servidor (com `e.read()[:200]`) e exceção genérica. `[confirmado — `vision_mcp.py:81-124`]`

⚠️ **A tool só entra no catálogo do modelo em SESSÃO NOVA.** Adicionar/recarregar o MCP no meio da sessão conecta o servidor, mas `see_image` não aparece na lista do modelo — ele tenta `Read`, falha e desiste. Precisa de sessão nova. `[relatado — medição reportada nesta rodada, não reproduzida aqui]`

**Verificado:** `vision_mcp.py` lido integralmente (165 linhas), `.mcp.json` e `plugin.json` conferidos, registro no `marketplace.json` (v0.1.0, categoria `productivity`) confirmado. `[confirmado]`

---

## 18 · A colheita do fim de turno passa a dizer POR QUE sobrou

**Gatilho:** evento `Stop`, hook `plugins/lixeiro/hooks/stop-colhe-turno.sh`. `[confirmado — o hook foi lido e exercitado nesta rodada]`

Até 2026-08-08 o hook encerrava o que a sessão tinha aberto e parava aí. O efeito medido: a
máquina limpava, o defeito ficava, e no turno seguinte tudo voltava — foi por esse ciclo que uma
máquina chegou a **2125 processos órfãos**. Agora a colheita e a causa saem na **mesma** notícia.

### O que decide quem morre — e por que deixou de ser a classe do comando

Até a v1.3.8 a regra era "suíte viva no fim do turno é lixo certo": tudo classificado como
efêmero (`pytest`, `cargo test`, `vitest`, `tsc`…) morria sem nenhuma outra checagem. O fim do
turno, porém, é **exatamente** quando o agente estaciona um trabalho longo para continuar
conversando — então a regra matava a suíte que estava rodando. Medido no `colhido.jsonl` de
2026-08-11: `cargo test` lançado em segundo plano às 19:37:50 e encerrado às 19:38:51; relançado
às 19:40:02 e encerrado às 19:40:08, **seis segundos de vida**. Duas horas depois o agente
escreveu "a suíte segue rodando" e dois segundos mais tarde ela recebeu o sinal.
`[confirmado — `~/.claude/lixeiro/colhido.jsonl` cruzado com o transcript da sessão]`

Desde a v1.4.0 a decisão do turno é uma só, e vale igual para as duas classes:

```
morre  ⇔  tem foto de CPU do turno anterior           (senão: primeiro turno, sobrevive)
      ∧   a foto é DAQUELE processo (cpu_pid)          (senão: outro processo, sobrevive)
      ∧   a CPU da ÁRVORE não subiu desde a foto       (senão: está trabalhando)
      ∧   o processo tem mais de OCIOSO_MIN de vida
      ∧   a foto tem mais de OCIOSO_MIN de idade       (ocioso é relógio, não "turnos")
```

- **A CPU é da ÁRVORE, não do processo.** Quem lança (`cargo`, `npm exec`, o `zsh -c` que o
  harness usa) fica parado esperando enquanto o filho queima CPU; olhar só o lançador o faz
  parecer ocioso com a suíte a todo vapor. Reaproveita `peso_arvore(procs, campo)`, o mesmo
  somador que já pesava a memória. `[confirmado — `lixeiro.py:peso_arvore` + caso de bancada]`
- **A janela é de relógio** (`OCIOSO_MIN`, 120s, ajustável por `LIXEIRO_OCIOSO_MIN`). Dois turnos
  podem estar a três segundos um do outro, e "não gastou CPU desde o turno anterior" viraria "não
  gastou CPU em três segundos" — o que mata a suíte parada esperando o banco subir.
- **A foto só se renova quando a CPU sobe**, e cada processo é fotografado por **uma** anotação
  (pareamento 1:1 em `marca_cpu`). Renovar sempre zeraria o relógio do ocioso a cada mensagem;
  fotografar o mesmo processo duas vezes deixava a segunda suíte do projeto sem foto própria — e
  o que ela abriu nunca era colhido.
- **`SessionEnd` não é sempre fim.** `reason` igual a `clear` ou `resume` sai sem colher: o que
  acabou foi a conversa, e o trabalho de segundo plano continua sendo do usuário. Nos demais, a
  colheita mede a CPU **ao vivo** (duas leituras separadas por `OCIOSO_ESPERA`), porque ali não
  existe foto anterior para comparar. `[confirmado — `sessionend-colhe.sh` + `lixeiro.py:trabalhando`]`
- **O número do processo é reconferido antes do sinal.** Entre ler a tabela e sinalizar passa
  tempo, e mais ainda quando a medição ao vivo dorme no meio: se o alvo morreu sozinho, o sistema
  pode ter dado o número dele a outro programa. `colhe` relê e só sinaliza se o comando bater.

```bash
python3 plugins/lixeiro/lib/test_lixeiro.py        # a suíte do motor (a contagem sai dela)
python3 plugins/lixeiro/lib/test_mutacao.py        # desliga cada trava e exige que a suíte acuse
bash  plugins/lixeiro/hooks/test_lixeiro_hooks.sh  # dois turnos reais: a que trabalha vive
```

```
MORTOS ← lixeiro.py colhe-turno --sessao <sid>
  ↓ (só quando encerrou algo, e com LIXEIRO_CAUSA≠0)
causa.py:investiga(sobras, [raiz])
  ↓ liga o comando do processo ao ARQUIVO que o abriu, e lê o padrão de risco nele
PORQUE = "🔧 e o motivo de terem sobrado: <arquivo>:<linha> — <motivo humano>"
  ↓
hj_msg "$MSG\n$PORQUE"        ← uma mensagem só; separar faria ler duas vezes o mesmo assunto
```

- **O hook INVESTIGA e ANUNCIA; ele não conserta.** Propor patch, medir alcance e aplicar é o rito
  da `/faxina` (passos 6 e 7), e ele exige agente — hook não escreve código no repositório de
  ninguém sem que o dono tenha pedido. `[confirmado — `stop-colhe-turno.sh`, comentário do bloco]`
- **Só entra no aviso o que a leitura do código EXPLICA.** Sobra sem arquivo identificável aparece
  na `/faxina` (onde há humano lendo), não aqui: no fim do turno seria ruído a cada colheita.
- **Desligar a causa não desliga a colheita** (`LIXEIRO_CAUSA=0`) — são notícias diferentes, e quem
  só quer menos texto continua precisando saber que processos morreram. `[confirmado — caso de bancada]`

**O juiz que decide se o conserto é aplicado no ato é OUTRO agente, e a separação é o ponto:** o
programa mede o alcance (`causa.py alcance` → quantos arquivos, quais de plugin de terceiro, quais
rodam em hook, quais têm suíte), o agente julga com esse dígito à vista sem saber quem propôs, e
`baixo` só é aplicado se a suíte do arquivo tocado ficar verde — vermelho desfaz e sobe para o
`/visual`. `[confirmado — `causa.py:alcance`/`suite_verde` + a suíte `test_causa.py`]`

```bash
bash plugins/lixeiro/hooks/test_lixeiro_hooks.sh   # a colheita com causa tem 4 casos próprios
python3 plugins/lixeiro/lib/test_causa.py
```

---

## 19 · O narrador do comando longo — o dono ausente descobre se a missão anda

**Dispara quando:** `PreToolUse[Bash]` e `PostToolUse[Bash]` do `project-skills`, **o mesmo script nos dois** (`hooks/posttooluse-andamento.sh`), com o argumento `marca` na ida e sem argumento na volta. ⚠️ **O plugin que hospedava o vigia foi extinto nesta rodada** — hook e módulo estão na família de projeto. `[confirmado — `plugins/project-skills/hooks/hooks.json`]`

**O problema que ele resolve:** dentro de um Workflow o dono fica cego. O agente entra em `idle` e a tela não diz se ele está rodando uma suíte de 11 minutos ou travado — *"'Idle' não carrega hora nem progresso, então parada legítima e travamento se parecem"*.

**Por que são dois momentos e um arquivo só:** `marca` grava o instante do disparo e sai calado; `narra` mede o decorrido **real** contra aquela marca, guarda na memória do projeto e imprime. ⚠️ **Sem a marca, a linha não sai** — o comentário fixa o critério: *"número de duração sem lastro é pior que silêncio"*.

**As duas regras vieram de medição, não de intuição** (299 transcripts de agente de workflow deste projeto, 2026-08-06) `[confirmado — a tabela está na docstring de `plugins/project-skills/lib/andamento.py`]`:

- **Estimativa só pela memória do PRÓPRIO comando, neste projeto.** A dispersão de `Bash` é de quase mil vezes entre mediana (0,7s) e máximo (660,4s), então média global produziria *"número com cara de dado e sem lastro"*. Comando sem histórico aqui sai **sem** estimativa — só o relógio.
- **Repetição de comando NÃO é sintoma de círculo.** Medido: 0 de 282 agentes repetiram o mesmo comando 4× ou mais; um detector baseado nisso não pegaria nada. O sinal que existe é o **placar que a própria suíte imprime** (540 ocorrências na amostra, em três formatos) — placar igual duas vezes seguidas é o que significa "não andou".

**Onde a linha sai: `systemMessage`**, o canal que o dono lê. O `stderr` de hook é descartado por quem chama — é exatamente o defeito que o check M do release-gate persegue (`patterns.md` §5.2).

**Escopo: só DENTRO de uma missão do motor de execução contínua**, pelo mesmo sinal `ativo-<session_id>` que os gates vizinhos consultam. Fora dela o dono está no teclado e vê a saída do próprio comando; narrar ali seria ruído.

⚠️ **O estado NASCE numa pasta NEUTRA — `~/.claude/andamento/`** — e o comentário do módulo diz por quê: *"Quatro plugins já chamam este módulo; a pasta batizada com o nome de um deles fazia o estado dos outros parecer emprestado."* Os arquivos de lá são todos chaveados por sessão (`ls ~/.claude/andamento/ | sed 's/-[^-]*$//' | sort -u` lista as naturezas de uma máquina viva): `ativo-<sid>` (a missão está de pé, e a 1ª linha dele é o **nome do motor** que a barra lê — ⚠️ **e que todo leitor tem que conferir antes de agir**: três skills gravam esse mesmo arquivo com nomes diferentes na linha 1, então quem só testa a existência do arquivo arma o próprio gate com a missão de outra. Medido em 2026-08-09, o sinal do `gauntlet` armava o gate do `sprint` e proibia o `gauntlet` de despachar os próprios juízes; ver `patterns.md §1.11`), `sinal-<sid>` (quando o narrador falou pela última vez), `placar-<sid>` (o último placar impresso pela suíte), `trabalho-<sid>` (o comando em curso, escrito no disparo e apagado na volta), `onda-<sid>` (a rodada em curso, **o bloco e a etapa dentro dela**, e o progresso do plano) e `doc-<sid>` (os caminhos de doc que a onda re-projetou).

⚠️ **O sinal tem TRÊS quem-apaga, e a terceira nasceu de cinco órfãos vivos.** Até 2026-08-09 o `rm` era passo da casca (só o caminho feliz) e o gate do motor expirava por idade — mas **só quando alguém consultava**, e quem consulta é a sessão que acendeu. Sessão morta nunca mais pergunta: a barra tinha **cinco sinais órfãos ao mesmo tempo, o mais velho de 75 horas**, todos anunciando missão de pé. Hoje: (1) o **motor** apaga ao sair, num papel `encerra:barra` que roda antes do `return` e por isso alcança teto, vigia, disjuntor, onda estéril e causa global; (2) a **casca** apaga na persistência, com `andamento.py encerra <sid>` — que leva o estado inteiro junto, não só o sinal; (3) a **barra** varre o que passar das duas, em `andamento.py:expira_sinais`, chamada dentro do próprio `linha_motor` — ela é o único processo que roda com frequência garantida em toda sessão viva, inclusive nas que não têm motor nenhum. `[confirmado — os cinco órfãos morreram na primeira leitura e a expiração ficou registrada em `~/.claude/andamento/expirados.log` com o autor `barra`]`

🔴 **E o quem-apaga (2) apagava missão VIVA — a assimetria sessão × motor, medida em 2026-08-12.** O sinal é chaveado por **sessão** (`ativo-<sid>`) e a reserva de arquivos por **sessão E motor** (`reservas/<sid>__<motor>.files`). O `encerra` conferia só o **nome do motor** na linha 1, o que separa `sprint` de `qa-loop` e de `gauntlet` — mas **não separa dois motores do mesmo nome na mesma sessão**. Aconteceu numa corrida real: o primeiro motor morreu na largada (porta fechada), o relançamento herdou a sessão, e o `encerra:barra` do morto apagou o sinal do vivo — a barra ficou muda com trabalho de pé, e o gate que nega despacho por fora desarmou junto. O dono só descobriu perguntando. **Conserto em duas metades, as duas em `andamento.py`:** `arma <sid> <dono> <motor>` passa a gravar quem está de pé em `motorid-<sid>` (`dono\tmotor`, uma linha por motor) — arquivo que **já era apagado em dois lugares e nunca era escrito por ninguém** —, e `encerra <sid> <dono> <motor>` só derruba o sinal quando **não sobra ninguém**; quem chama são `skills/sprint/SKILL.md` (armar e persistir) e `motor.js:encerraPrompt`. A segunda metade é a rede para o que já caiu: **`ressuscita_sinais`, chamada no mesmo `linha_motor`, logo depois de `expira_sinais`** — motor registrado de pé sem sinal **reacende**, e registro mais velho que `SPRINT_TTL_MIN` é apagado em vez de reacender para sempre. A ordem entre as duas importa: expirar primeiro apaga o registro da sessão morta, então a ressurreição não devolve o sinal que a outra acabou de matar. `[confirmado — `test_andamento.py` cobre os dois lados; com o `encerra` de antes a mesma suíte sai `FALHOU: 3`]`

⚠️ **E a barra anda DENTRO da onda.** `marca_onda` aceita `--bloco` e `--etapa`, e o motor os grava na largada da rodada (`separando o trabalho`) e em cada bloco (`suíte`): a linha sai `🌊 Onda 2 bloco 3 · executando` em vez de ficar quinze minutos parada em `Onda 2` numa onda de três blocos. Quem só registra a rodada continua saindo como antes — os dois campos são opcionais. `[confirmado — `test_andamento.py`, bloco "a barra acompanha o bloco"]` ⚠️ **A pasta antiga com o nome do plugin extinto continua sendo LIDA como legado** — `andamento.py:ESTADO_LEGADO`, e o hook copia o sinal de lá na primeira passada —, **nunca escrita**: missão viva no momento da mudança não perde o que já tinha. `[confirmado — `andamento.py:ESTADO`/`ESTADO_LEGADO` e o bloco de cópia em `posttooluse-andamento.sh`]`

```bash
python3 plugins/project-skills/lib/test_andamento.py
bash plugins/project-skills/hooks/test_andamento_hook.sh
```

---

## 20 · Perguntar "como vai?" — o andamento que não depende de estar olhando

O vigia do motor já narrava o andamento em duas superfícies, e as duas **somem de quem não
está lá**: o `systemMessage` rola junto com a conversa, e a barra de status só existe na
sessão em que ela foi desenhada. Quem volta ao terminal uma hora depois não vê nenhuma das
duas — e a pergunta "isso ainda está rodando?" não tinha resposta. `[confirmado — leitura da
skill nesta rodada]`

O fluxo, que nasceu na onda de 2026-08-08 (`F17.1` + `F17.6`):

- **O módulo mudou de casa.** `andamento.py` saiu de `plugins/sovai/lib/` para
  `plugins/project-skills/lib/` — ele mede workflow, e workflow não é do motor de execução
  contínua. A suíte dele passa **sem o plugin do motor instalado**, que era o critério do
  passo. ⚠️ Três documentos ainda apontavam a casa velha depois da mudança, e quem acusou foi
  o `dead_scope` do próprio `touch-plan` — é para isso que ele existe.
- **A pergunta virou comando.** A skill `project-skills:monitorar` lê o estado do disco — o
  sinal da missão, o carimbo da ferramenta em curso, o placar da última onda — e imprime o
  andamento **agora**, sem perguntar nada a ninguém e sem depender de nenhum vigia estar
  aceso. ⚠️ **A casa desse estado mudou nesta rodada:** ele nasce em `~/.claude/andamento/`
  e a pasta com o nome do plugin extinto entrou como **legado somente-leitura** — `todas()`
  varre as duas bases, e é isso que faz uma missão que já estava de pé continuar visível.
  `[confirmado — `andamento.py`, a lista `bases` em `todas()`]`
- **Nada disso adivinha.** Quem grava é quem executa: o gancho de andamento
  (`plugins/project-skills/hooks/posttooluse-andamento.sh`) escreve o instante, o comando e o
  projeto quando o disparo sai, e apaga quando ele volta. Comando sem histórico neste projeto
  sai **sem estimativa** — a regra do §19 vale igual aqui.
- **A linha da barra diz EM QUE PONTO a missão está, não só há quanto tempo ela existe**
  (2026-08-09). `andamento.py:marca_onda` grava `onda-<sid>` com a rodada e — quando recebe o
  caminho do plano — o par feitos/total contado **pelo programa**, lendo o arquivo; `linha_onda`
  o devolve para `linha_motor`. Quem chama é o papel de marcação do motor, com um comando ao
  fim da lista de `tick` (`andamento.py onda <sid> <rodada> <planPath>`, contrato em
  `skills/sprint/SKILL.md`), porque a rodada só existe na memória do motor e o progresso só
  existe no arquivo do plano — nenhum dos dois chega sozinho a um processo que desenha barra.
  Falhar ali não derruba nada: a barra volta a ser a de antes.
  `[confirmado — `python3 plugins/project-skills/lib/test_andamento.py`, que cobre plano ilegível, sessão sem onda e a linha renderizada]`
- **O desenho da linha é ícone + separador vertical, e o motor se nomeia.** Cada pedaço abre com
  o ícone que o identifica (`🚀` missão · `🌊` onda · `🔧` ferramenta · `💬`/`⏳`/`🔇` sinal ·
  `⛔` bloqueio · `🧪` suíte) e os pedaços são separados por `│` em vez de ponto médio — a barra
  é lida de relance, e achar o silêncio no meio de seis frases separadas por ponto exigia ler a
  linha inteira. ⚠️ **O nome sai do PRÓPRIO sinal**: `skills/sprint/SKILL.md` passou a gravar
  `sprint` dentro do `ativo-<sid>` em vez de acendê-lo vazio, e o rótulo de fallback
  (`andamento.py:MOTOR_PADRAO`) deixou de ser o nome do plugin extinto — sinal vazio nomeava
  o nome do plugin extinto em toda missão, meses depois da fusão. Missão de mais de uma hora sai
  como `1h07`, não `67min00s`. `[confirmado — `linha_motor` renderizada nos três estados nesta rodada]`

**Verificado:** `python3 plugins/project-skills/lib/test_andamento.py` → **OK**, e
`ls plugins/project-skills/lib/andamento.py` confirma a casa nova. `[confirmado nesta rodada]`

---

## 21 · A trava dupla do gauntlet — o juiz deixa de depender de quem despacha

**Novo em 2026-08-09**, e é a troca de mecanismo que a v0.3.0 do `gauntlet` trouxe: o laço saiu de dentro de um `Workflow` fechado e passou a rodar como equipe de agentes visível na conversa. A garantia de que toda entrega ganha juiz mudou de lugar sem deixar de ser mecânica. `[confirmado]`

**O que dispara.** `plugins/gauntlet/hooks/hooks.json` registra `PreToolUse[Agent]` → `pretooluse-gauntlet.sh` (10s). O caminho, na ordem em que o arquivo decide:

```
GAUNTLET_GATE=0 ............................. exit 0 (kill-switch, antes de tudo)
hook-json.sh ausente / sem jq e sem python3 . exit 0 falando (hj_avisa)
session_id ausente (linha 59) ............... exit 0
andamento/ativo-<session_id> ausente ........ exit 0
1ª linha do sinal != "gauntlet" ............. exit 0 (a casa é compartilhada)
2ª linha ausente ou não é diretório ......... exit 0 (fail-open declarado)
sinal mais velho que GAUNTLET_TTL_MIN ....... remove o sinal, exit 0
prompt de construtor/juiz SEM "NUNCA RECEITA" deny (a trava do briefing, v0.5.0)
fecho_check.py pendentes <missão> == vazio .. exit 0 (equipe livre)
prompt contém [gauntlet:juiz:<peça pendente>] APAGA bloqueios-<sid>, exit 0 (o juiz passa)
bloqueios-<sid> >= GAUNTLET_MAX_BLOQUEIOS ... registra E AVISA a desistência, exit 0
senão ....................................... incrementa o contador e deny
```

**A trava do briefing contaminado (v0.5.0).** O degrau novo é o único que nega **sem
depender de pendência**: prompt com o crachá `[gauntlet:construtor:…]` ou
`[gauntlet:juiz:…]` que não carregue a linha `RÉGUA, NUNCA RECEITA` não parte. Ele nasceu
de uma missão real em que a regra existia só em prosa e não segurou — o orquestrador
interpolou o número medido no alvo como meta, um construtor reproduziu a moldura e a
pílula do alvo, e um juiz chegou a cobrar que a física da rolagem batesse a constante do
alvo. A negação ensina a linha que falta, em vez de só recusar. `[confirmado — `bash
plugins/gauntlet/hooks/test_gauntlet_hooks.sh` → bloco "RÉGUA, NUNCA RECEITA", com
"construtor sem a linha é negado, mesmo sem pendência de juiz", "juiz sem a linha também
é negado", "construtor com a linha passa" e "recon não precisa da linha"]`

**O sinal ganhou uma segunda linha.** A 1ª continua sendo o nome que a barra de status lê — `plugins/project-skills/lib/andamento.py:_motor` usa `readline()`, então enxerga só ela —, e a 2ª carrega o diretório da missão. É por ela que o guarda sabe onde procurar pendência, e sinal sem ela deixa o guarda mudo em vez de adivinhar. `[confirmado — leitura das duas funções]`

**A pergunta é do disco.** `fecho_check.py pendentes` percorre a decomposição e devolve a peça com **alguma** rodada que tem `entrega.json` e não tem `veredito.json` legível com status do vocabulário. Era "a última rodada" até 2026-08-09, e o recorte abria uma porta: com `r1` entregue e sem juiz e `r2` entregue e aprovada, a pendência de `r1` sumia e **o fecho declarava "todo pedaço julgado"**. Hoje toda rodada entregue tem que ter juiz, aqui e no fecho; no laço normal isso nunca acusa nada, porque rodada anterior é rodada que o juiz reprovou, e reprovar é gravar veredito. É a foto da falha de origem ("sete construtores, zero juízes") tirada em voo, e não no fecho. `[confirmado — `python3 plugins/gauntlet/lib/test_fecho_check.py` → *"fecho_check: tudo verde"*, com os casos de `pecas_pendentes`]`

**O desarme deixou de ser mudo (v0.4.0) e deixou de ser permanente (v0.4.1).** A trava desiste depois de `GAUNTLET_MAX_BLOQUEIOS` negações — decisão declarada no cabeçalho do arquivo, porque travar missão longa com o dono fora custa mais que o defeito. Dois furos vieram daí, e os dois estão fechados:

- **Ela desistia calada.** Falava só com `andamento/desistencias.log`, que ninguém abre. Hoje o mesmo ponto emite `hj_msg_ctx`, nomeando as entregas ainda sem veredito.
- **A conta era da SESSÃO INTEIRA e nada a zerava.** Três esquecimentos espalhados por peças diferentes desligavam o guarda pelo resto da missão. Medido com sete peças entregues e zero juízes — a falha de origem inteira, com a proteção desarmada por cansaço. O teto de 3 tinha sido calibrado para a trava da v0.1, que negava **todo** sub-agente; a trava de hoje só nega com pendência real, e o mesmo número virou frouxo. **Agora o juiz que passa apaga `bloqueios-<sid>`**, então a paciência se gasta em negações SEGUIDAS: três sem nenhum juiz no meio ainda desarmam, que é o cenário que a válvula existe para atender.

`[confirmado — `bash plugins/gauntlet/hooks/test_gauntlet_hooks.sh` cobre "o juiz que nasce zera o contador", "e depois dele a trava volta a NEGAR, em vez de já desistir" e "a desistência AVISA na conversa, não só no log"]`

**A trava anti-medida deixou de ser só do juiz (v0.10.0).** A linha `RÉGUA, NUNCA RECEITA` que o hook cobra no despacho é o guarda de **entrada**; ela impede o briefing de sair sem a regra, mas não olha o que volta. Faltava o guarda de **saída**, e é ele que a v0.10.0 acrescenta no `fecho_check.py`: quando o rito **não** traz o campo `metricas` — as medidas que o dono forneceu para aquele desafio específico —, veredito cujo `gap` ou `frase` julgue por medida é recusado, no juiz de peça e no diretor. Sem o campo, o critério é impressionar; com ele, a mesma frase passa. A expressão que decide é a mesma `MEDIDA_NO_NOME` que já recusava medida em nome de eixo na abertura, agora aplicada nos dois pontos do fecho. A ordem dos dois guardas importa para quem debuga: **o hook nega o despacho, o fecho nega o veredito** — um briefing sem a linha nunca chega a produzir arquivo, enquanto um veredito que mede produz arquivo e só é barrado no fim. `[confirmado — `python3 plugins/gauntlet/lib/test_fecho_check.py` → *"fecho_check: tudo verde"*, com o bloco "O NÚMERO SÓ ENTRA PELA MÃO DO DONO" e o contraditório *"o MESMO gap passa quando o dono forneceu `metricas` neste desafio"*]`

**O fecho ganhou dois cobradores na v0.4.0**, e os dois nasceram de uma revisão que mediu a mesma classe de furo que criou a skill — regra escrita em prosa, cumprida por ninguém:

- **A lei em documento.** `fecho_check.py:ancora_leis` grava `lei-aprovada.marca` quando o `rito` passa, e `erros_do_fecho` compara o conteúdo de cada documento de lei contra essa âncora. Lei que mudou, entrou ou sumiu no meio da missão vira furo nomeado, em vez de depender de quem orquestra lembrar de reconferir. A âncora do rito (`rito-aprovado.marca`) não cobria isso: ela congela o que está DENTRO do `rito.json`, e a lei mora em documento de fora.
- **O arsenal.** Em missão cujo rito traz `arsenal`, a entrega tem que declarar `arsenal_usado` — lista vazia é resposta ("não usei nada"), campo ausente é silêncio e recusa o fecho. É o que dá ao dono a chance de vetar uma dependência que a obra adotou.

**A abertura passou a recusar eixo-receita (v0.5.0).** `erros_do_rito` casa
`MEDIDA_NO_NOME` contra o nome de cada eixo e recusa o que traz medida ali — `px`, `ms`,
`fps`, `em`, `rem`, `vh`, `vw`, `%` ou `s` colados a um número. O nome do eixo é o que o
briefing interpola, então nome com medida é o vetor pelo qual o número do alvo vira meta:
numa missão real o eixo descritivo "moldura de 32px" virou moldura de 32px na obra. O
mesmo número continua aceito no campo `numero`, que é onde ele prova o NÍVEL do alvo.
`[confirmado — `python3 plugins/gauntlet/lib/test_fecho_check.py` → bloco "RÉGUA, NUNCA
RECEITA", com "o rito recusa o eixo com medida no nome" e "o mesmo número no campo
`numero` passa"]`

**Verificado:** `bash plugins/gauntlet/hooks/test_gauntlet_hooks.sh` → *"trava dupla do gauntlet: tudo verde"*, cobrindo o construtor negado, o juiz da pendente que passa, o juiz de peça já julgada que não fura a fila, a equipe livre sem pendência, a desistência que avisa, o juiz que rearma a trava, a missão órfã no arranque, a expiração, o kill-switch e as cinco bordas de fail-open; `python3 plugins/gauntlet/lib/test_fecho_check.py` → *"fecho_check: tudo verde"*, com os blocos "A LEI EM DOCUMENTO" (5 casos), "O ARSENAL" (2 casos) e "A RODADA INTERMEDIÁRIA" (3 casos). `[confirmado nesta rodada]`

**A missão sobrevive ao fim da sessão (v0.4.2).** O segundo hook de `SessionStart` do plugin (`sessionstart-lembra-missao.sh`, 10s) varre `andamento/ativo-*`, pega o primeiro sinal cujo nome de motor é `gauntlet` — dando a vez ao da própria sessão quando ele existe —, roda o `mapa` e imprime o estado com as entregas sem juiz nomeadas. Era a metade que faltava do "todo veredito vive em arquivo": o disco guardava e ninguém lia na volta, e o sinal expirava em 12h levando a missão junto, calado. ⚠️ **Ele não retoma nada** — o recado termina mandando perguntar ao dono se retoma ou encerra, porque motor que se reinicia sozinho no arranque é como se perde o controle de uma disputa que gasta agente. `[confirmado — a suíte cobre "o arranque encontra a missão de pé", "traz o gap aberto, que era o que evaporava na conversa" e "deixa a decisão com o dono, sem retomar sozinho"]`

---

## 22 · A régua do projeto chega por COMANDO — o preâmbulo `doc-load` → `principles`

**Novo em 2026-08-09.** Toda skill que julga alguma coisa precisava da mesma resposta — *quais documentos deste projeto valem como régua hoje, e quais são só mapa* — e essa resposta estava **copiada em prosa** dentro de cada uma, com redações diferentes. Agora ela é programa, e roda como preâmbulo: `doc-load` primeiro (a régua deste projeto), `principles` depois (os princípios genéricos). Em conflito, a régua do projeto ganha. `[confirmado — leitura da skill e do preâmbulo]`

⚠️ **A régua carregada aqui não substitui a varredura do plano.** A skill diz isso em uma linha — *"pré-check vencido → rode a caça antes de planejar ou executar por cima"* —, e o hook de arranque `sessionstart-plan.sh` repete a mesma frase no lembrete do plano aberto: o que o `doc-load` entrega é aquilo CONTRA o que a obra é julgada, não o exame do plano que vai rodar (fluxo 5). `[confirmado — o diff das duas fontes e os checks "o preâmbulo da skill carrega a linha do pré-check vencido" (test_doc_load.py) e "o lembrete de plano aberto carrega a linha do pré-check vencido" (test_plan_hooks.sh)]`

**Quem tem o preâmbulo sai do grep, não desta página:**

```bash
grep -rln 'doc-load' plugins/*/skills/*/SKILL.md    # 12 arquivos neste run, incluindo o próprio doc-load
```

**O que o programa responde.** `plugins/project-skills/lib/doc_load.py` (`--json` para consumo por programa, `--marca` para só o número) classifica cada documento canônico e diz o que vale como régua:

- **lei** — `constituicao.md`, `quality-goals.md`, `constraints.md`: valem com `ready` **ou** `approved`. A lei não passa pelo rito de aprovação porque não é etapa de concepção.
- **acordo** — `context.md`, `solution-strategy.md`, `glossary.md`, `architecture-intent.md`, `design.md`, `journeys.md`, `blueprint.md`, `features.md`: **só** com `approved`, e **REABRE** quando o corpo mudou depois do de acordo (a marca gravada não bate com o texto de hoje — ninguém aprovou o que está lá).
- **minerado** — este arquivo entre eles: serve para se situar, **nunca** para reprovar.

Campos da saída: `regua`, `marca_regua`, `ausentes` (e a mesma lista separada por natureza em `ausentes_lei`, `ausentes_acordo`, `ausentes_minerados`), `dispensa`, `reabertos`, `correcoes_pendentes` — e `anexos` (novo em 2026-08-16): os sidecars de protótipo (`.claude/docs/prototipo/*.prototipo.md`, `doc_load.py:le_anexos`), quarta natureza que **nunca** entra na régua nem na `marca_regua` — o protótipo muda de tela sem mudar a lei —, cada um com os dois gatilhos de reabertura nomeados (conjunto que diverge do `conjunto-sig` gravado · `design-sig` que não bate mais com o de acordo do `anexo-de`); a lei do formato é `.claude/docs/prototipo/FORMATO.md` (§1.10a de `patterns.md`). **Ausência é dita em voz alta e não é achado** — e desde 2026-08-12 ela é dita no ALTO: o bloco `⚠️ LACUNA — N de 16 documentos canônicos` abre o relatório, uma linha por natureza, cada uma com o comando que a resolve (`/start escreve` · `/doc extrai do código`). Só `dispensa.md` com `motivo:` escrito cala o bloco — projeto sem `constituicao.md` não tem o eixo de constituição, e isso não viola nada; `dispensa.md` sem `motivo:` escrito não vale.

**O bloco de lacuna PARA o preâmbulo.** A skill manda: saiu `⚠️ LACUNA`, o fluxo trava ali — nada de plano, código ou leitura de outro arquivo — o dono vê as linhas do programa coladas literalmente e escolhe entre preencher agora (`/start` para lei e acordo, `/doc` para o mapa, que a própria saída nomeia) ou seguir sem régua assumindo o risco. Silêncio não libera. **E desde 2026-08-13 o caminho de preencher bifurca pela idade do projeto**: nascendo → `/start` (entrevista do zero); maduro (código denso, doc minerada) → **`/start ex-post`** — o modo que infere o rascunho de cada documento do que já foi construído, com prova por artigo em três camadas (a fala do dono nas atas · doc escrita avulsa · padrão do código com contagem), e conduz o dono pelo referendo artigo a artigo. O rascunho inferido nunca nasce `authored-by: human` — a marca só vem do rito de aprovação. Quem oferece o modo além do `doc-load`: o hook de abertura (projeto >100 arquivos versionados sem autoral, e o ramo do minerado-sem-autoral) e o Tier 5 do `/doc`. `[confirmado — seção "O modo ex-post" em skills/start/SKILL.md, e as suítes test_start_doc_skill.py e test_sessionstart_doc.sh check 16]` ⚠️ **Menos no modo autônomo** — `/sprint`, headless, qualquer contrato que já se declara sem pausas: aí não há a quem oferecer, e esperar trava a missão inteira; a lacuna vira pendência do relatório final (o bloco literal, as naturezas que faltam e o comando de cada uma) e a missão segue sem régua para o que falta. `[confirmado — leitura da seção "A oferta" em plugins/project-skills/skills/doc-load/SKILL.md]`

**Desde 2026-08-15 a entrevista não faz mais pergunta em branco: vai com o palpite na mesa e a confiança em PERCENTUAL.** Campo vazio obriga o dono a compor a resposta do zero; palpite errado ele derruba numa linha. A forma é fixa — o palpite, o número com o símbolo (`confiança: 70%`) e a pista que o originou (`arquivo:linha`) —, e três travas impedem o palpite de virar resposta do dono: `%` é obrigatório (*"confiança alta"* é impressão, não confiança, e o número diz onde gastar atenção — abaixo de 50% é chute a corrigir, acima de 80% é conferência rápida); palpite sem pista visível não existe; e nem 95% dispensa a confirmação — o documento grava o que o dono respondeu, e silêncio nunca é aprovação. Sem pista para apostar, a pergunta vai em branco dizendo que não há palpite. Em `AskUserQuestion` o palpite é a opção marcada como aposta no texto, com o percentual ao lado, e as outras opções continuam inteiras. `[confirmado — seção "### 3 · Entrevistar" em skills/start/SKILL.md, e o bloco "palpite e confianca em percentual (F9.1)" de test_start_doc_skill.py]`

**E a etapa não fecha mais sem separar o que o dono decidiu do que ele NÃO decidiu.** Entre a sabatina e o de acordo entrou um passo obrigatório em TODA etapa, mesmo com lista vazia: releia a conversa e grave cada escolha que ficou em aberto como uma linha `decisao-pendente: {a decisão} — trava {o que não anda} — destrava com {o que falta}` **no frontmatter**, nunca no corpo — escrever no corpo reabriria a etapa pela marca (`approved-sig`), a mesma regra da `correcao-pendente:`. Não confundir com o `[PENDENTE]` da entrevista: aquele é resposta que faltou, este é escolha que ninguém fez. **Ela não segura o de acordo** — é cobrança visível, e o Passo 5 do relatório imprime a linha *"Por decidir"* por etapa, ou *"nenhuma decisão aberta"*. O motivo é o custo do lado de lá: decisão não declarada na concepção reaparece como bloqueio no meio da execução, com o executor parado. A mesma régua do outro lado do fio está no passo 5 da skill `plan` (a passada das cinco classes antes de gravar). `[confirmado — passo 5 da seção "### 5 · Apresentar, sabatinar e colher o de acordo" e o esqueleto do relatório em skills/start/SKILL.md]`

**A marca é a MESMA do shell, e é aí que o mecanismo se prova.** `doc_load.py:cksum` reimplementa em Python o `cksum` POSIX do **corpo** (sem frontmatter) que `plugins/project-skills/hooks/lib-doc-mark.sh:doc_marca` produz — duas receitas para o mesmo número divergem em silêncio (`patterns.md` §1.6), então a suíte compara as duas sobre o mesmo arquivo. Conferido naquela rodada sobre a constituição (então em `.claude/docs/`, hoje `docs/constituicao.md`): `1697768643` pelos dois lados, e `--marca` devolveu a emenda de **10** marcas coladas por `+` (as três leis e os sete acordos aprovados que valem como régua hoje — a cadeia cresce a cada de acordo novo, então o número de parcelas é deste run, nunca constante). ⚠️ O `lawMark` que a missão do motor congela (fluxo 5) usa outra receita desde 2026-08-09 — a saída literal de `cat <arquivos da régua> | cksum`, comando escrito no prompt pelo `motor.js:leiMarcaInstr` — porque a receita em prosa rendeu quatro marcas divergentes do mesmo disco numa corrida real. `[confirmado — os dois comandos rodados nesta rodada]`

**A ida ao mapa da régua, dentro da skill `plan`, ganhou cobrador em 2026-08-12.** O preâmbulo garante que a régua seja LIDA; o que faltava era garantir que o plano a CONSULTE antes de escrever a primeira tarefa — a linha que manda montar o mapa vivia só em prosa no `SKILL.md`, e prosa some numa edição sem ninguém notar. A suíte `plugins/project-skills/lib/test_spec_to_plan_skill.py` agora lê o texto da skill, extrai dele o módulo citado (`import <modulo> as c`, nada de caminho cravado), exige que esse arquivo exista ao lado dela, importa-o e confere que **toda** função de leitura que a skill manda chamar (`c.le_*`) realmente existe no módulo — mais a ordem: a ida vem **antes** da gravação do plano. Módulo resolvido neste run: `cobertura.py`, com `le_artigos`, `le_jornadas`, `le_pecas` e `le_passos`. `[confirmado — saída da suíte]`

**Verificado:** `python3 plugins/project-skills/lib/test_doc_load.py` → **51 passou · 0 falhou** nesta rodada · `python3 plugins/project-skills/lib/test_spec_to_plan_skill.py` → **52 ok · 0 falhas** · `python3 plugins/project-skills/lib/test_start_doc_skill.py` → **OK**, 191 checks (contagem deste run: `python3 … | grep -c '^  ok'`). `[confirmado — saída das suítes]`

---

## 23 · O arranque conta que esta máquina roda código velho

**Novo em 2026-08-09**, e nasceu do defeito mais caro daquela rodada: o dono revisou,
testou e aprovou a v0.4.0 do `gauntlet` durante uma sessão inteira **enquanto a máquina
dele rodava a 0.3.2**. Editar `plugins/<nome>/` não muda o que o harness carrega — ele lê
o cache de `~/.claude/plugins/`, e o cache só troca com `claude plugin update` mais um
reinício. Nada no repositório dizia isso, e a descoberta foi por acaso. `[confirmado — o
`installPath` do `installed_plugins.json` apontava para `…/gauntlet/0.3.2`]`

**O que dispara.** `.claude/settings.json` registra `SessionStart` →
`sessionstart-avisa-cadeia.sh` (10s). É hook do **projeto**, não de plugin, e o público
explica: só quem tem o repositório na mão consegue comparar as duas versões.

```
CADEIA_GATE=0 ............................... exit 0 (kill-switch)
sem scripts/cadeia_check.py no projeto ...... exit 0 (não é este repositório)
sem python3 que EXECUTE ..................... exit 0
sentinel $TMPDIR/cadeia-avisou-<sid> existe . exit 0 (uma vez por sessão)
cadeia_check.py --maquina --quieto sem saída  exit 0 (está tudo em dia)
senão ....................................... hj_msg_ctx com as duas versões
```

**Quem responde é `scripts/cadeia_check.py`**, e ele compara quatro estações: o que está
escrito (`plugins/<nome>/.claude-plugin/plugin.json`), o que é publicado
(`.claude-plugin/marketplace.json`), o que a receita manda instalar
(`plugins/bootstrap/config/manifest.json`) e o que a máquina roda (o `installPath` do
`installed_plugins.json` — o caminho do cache, porque é ele que aponta para os arquivos
que o harness de fato carrega). O modo `--repo` é o check T do gate de commit (§5.2 de
`patterns.md`); o `--maquina` é este aviso.

⚠️ **Ele avisa e não conserta**, e o cabeçalho registra o motivo: *"o estrago de um
instalador automático errado é maior que o do aviso que ele evita"*. O recado fecha com a
regra que faltava — *"teste no repositório vale como leitura de código, nunca como prova
de comportamento"* — e vai aos dois públicos, porque o modelo que não souber disso passa a
sessão testando o que não roda.

**Verificado:** `bash .claude/hooks/test_sessionstart_avisa_cadeia.sh` → *"aviso de cadeia:
tudo verde"*, com o caso de origem (repositório em 0.4.0, máquina em 0.3.2), o silêncio da
segunda chamada na mesma sessão, o aviso de novo numa sessão nova, o silêncio de quem está
em dia, o fallback para stderr sem o leitor de JSON e o kill-switch;
`python3 scripts/test_cadeia_check.py` → *"cadeia_check: tudo verde"*. `[confirmado nesta
rodada]`

---

## 24 · O diagrama vira DOCUMENTO — a camada visual que viaja no commit da doc

Até 2026-08-16 todo desenho nascia em `.claude/archify/`, gitignorado como `.claude/visual/`:
tinha a durabilidade de artefato de sessão, ou seja, **nenhuma**. O fluxo abaixo é a promoção a
documento — e o motivo é o mesmo que justifica versionar o texto: desenho e texto descrevem a
mesma coisa, e deixar um se atualizar sem o outro é como o diagrama envelhece até virar
mentira ilustrada.

1. **O gatilho é o doc re-projetado, não uma varredura nova.** O passo 2 do `/doc-touch`
   re-projeta os docs cujo `scope:` intersecta o diff; o passo 2b pega **esses** e re-renderiza a
   camada de cada um. `architecture.md` → `organismo.html` · `runtime.md` → os
   `fluxo-<slug>.html` dos fluxos que o diff tocou · doc de módulo → `app-<nome>.html`.
   `[confirmado — plugins/project-skills/skills/doc-touch/SKILL.md, passo 2b]`
2. **Os três dividem UMA casa, e ela é versionada:** hoje `docs/fluxos/` na raiz — a casa
   desceu junto com a doc em `98b712e` (2026-08-20); até então era `.claude/docs/fluxos/`,
   resolvida por `resolve-dir.sh "$PWD" docs/fluxos` (o resolvedor aceita subdir com barra
   desde o mesmo dia, § do cenário 1). ⚠️ O passo 2b do `doc-touch` ainda escreve
   `.claude/docs/fluxos/` na prosa e chama o `resolve-dir.sh` antigo — quem pergunta a casa
   ao resolvedor único (`casa_da_doc`) é a rodada que vem. Um destino só existe para o mesmo
   tipo de artefato não viver em duas pastas; foi o defeito que a rodada de 2026-08-16
   corrigiu, com o organismo ainda apontando para a pasta de sessão enquanto o fluxo já
   morava na casa nova.
   `[confirmado — `git ls-files docs/fluxos/` e plugins/project-skills/skills/doc-touch/SKILL.md, passo 2b]`
3. **O JSON de entrada sai do doc curado, nunca do código cru.** Desenhar direto do código
   reintroduz exatamente o palpite que a doc existe para evitar.
4. **O desenho entra no commit de CONTEÚDO** (passo 5 do touch), junto do texto que o originou —
   e o carimbo vem no segundo commit, pela regra do ovo-e-galinha que já governa a doc.
5. **Duas guardas que só existem porque agora é rastreado:** a régua do repositório público
   reprova caminho absoluto de máquina dentro do HTML (checagem H do gate de commit), e o
   `archify` ausente **degrada em voz alta** — avisa e segue, porque diagrama é camada a mais
   sobre a doc, nunca pré-requisito dela.

⚠️ **Nome estável significa sobrescrever:** um assunto, um arquivo, sempre o atual. Documentação
viva não se versiona por data — quem quer o desenho de ontem tem o git.

---

## Pendências

- **Ponteiros cross-tool inertes** (cenário 2): os 5 arquivos apontam pra um `CLAUDE.md` na raiz que não existe. `[confirmado]`
- **Ponte do context-guard desligada nesta máquina** (cenário 3): env vars presentes, `context-guard-writer.sh` fora do `statusLine.command`. `[confirmado]`
- **Juiz de forma sem nenhum julgamento registrado** (cenário 9b): 12 batidas, todas `sem texto`. O hook executa; o texto do assistente não está chegando a ele nas execuções registradas. Causa não investigada nesta rodada. `[confirmado — o fato; a causa é lacuna aberta]`
- **Queda do orçamento de `Stop`** (cenário 11a): o total medido caiu depois de dois emissores mudarem de plugin, sem que ninguém tenha enxugado texto. O gate só barra a subida, então isso passou limpo. `[inferido — causa não reproduzida]`
- **Ordem entre plugins no mesmo evento**: segue não determinável a partir deste repositório — **exceto no `ExitPlanMode`, que deixou de ser disputa**: um único hook se registra e chama os outros em ordem escrita no código (cenário 8.0). Fora dele, só a ordem **interna** ao array de um `hooks.json` é fixada aqui, e mesmo assim depender dela é `[inferido]`.
- **Conteúdo não lido nesta rodada**, citado só pelo registro: `plugins/branches/hooks/sessionstart-branches.sh`, `plugins/handoff/hooks/handoff-completeness-gate.sh`, `plugins/intent-guard/hooks/delivery-audit.sh`, `plugins/project-skills/hooks/stop-doc-touch.sh`, `plugins/guardrails/hooks/askq-humanize.sh`, `plugins/bootstrap/hooks/post-plugin-command.sh` e `plugins/bootstrap/hooks/lib/apply-config.sh`.
