# pedro-plugins

Marketplace público de plugins para [Claude Code](https://docs.claude.com/en/docs/claude-code). Monorepo — cada subdiretório em `plugins/` é um plugin independente (skills, hooks e automações), distribuído via `.claude-plugin/marketplace.json`.

**21 plugins · Markdown + Shell + Python · sem build, sem package manager.**

---

## Índice

- [Instalação](#instalação)
  - [Dependência externa](#dependência-externa)
- [Plugins](#plugins)
  - [Sessão & continuidade](#sessão--continuidade)
  - [Planejamento & review](#planejamento--review)
  - [Documentação & conhecimento](#documentação--conhecimento)
  - [Dev, deploy & limpeza](#dev-deploy--limpeza)
  - [Apresentação visual](#apresentação-visual)
  - [Setup de máquina](#setup-de-máquina)
- [Hooks automáticos](#hooks-automáticos)
- [Anatomia de um plugin](#anatomia-de-um-plugin)
- [Desenvolvendo localmente](#desenvolvendo-localmente)
- [Publicando uma mudança](#publicando-uma-mudança)
- [Licença](#licença)

---

## Instalação

### Pegar só o que quiser

```bash
# 1. Adicionar o marketplace (uma vez por máquina)
claude plugin marketplace add https://github.com/pedroberaldo87/pedro-plugins.git

# 2. Instalar os plugins desejados
claude plugin install visual@pedro-plugins
claude plugin install qa-loop@pedro-plugins
claude plugin install handoff@pedro-plugins
# ...
```

### Restaurar o setup inteiro (máquina nova)

```bash
# 1. Marketplace + bootstrap
claude plugin marketplace add https://github.com/pedroberaldo87/pedro-plugins.git
claude plugin install bootstrap@pedro-plugins

# 2. Instala marketplaces + plugins do manifest E aplica a config global
#    (env vars, permissões, flags, CLAUDE.md global, output style, statusLine)
/bootstrap:setup
```

Resultado esperado numa máquina zerada: **19 plugins ligados + 2 desligados de fábrica**
(`graphify-guard` e `intent-guard`), mais os marketplaces de terceiros do manifest.

> ⚠️ **Se aparecer `sync incompleto: N operações falharam`, rode `/bootstrap:setup` de novo.**
> Medido numa instalação limpa: a primeira rodada deixou um marketplace de terceiro para trás
> e a segunda o instalou. O script é convergente de propósito (re-rodar é seguro e nunca toca
> em marketplace que o manifest não declara), e o auto-sync do início de sessão faria isso
> sozinho — mas o aviso amarelo assusta antes disso acontecer.

> `bootstrap` substitui o antigo `bootstrap-third-party`.

**Antes de rodar, saiba o que ele sobrescreve.** O passo 2 copia o `CLAUDE.md` global
versionado por cima de `~/.claude/CLAUDE.md` (com backup datado ao lado) e fixa o
`outputStyle` como `Clean Style`. Se você já tem instruções globais suas, rode o
verificador antes — ele mostra o que existe só de um lado, sem prescrever direção:

```bash
python3 "$(ls -d ~/.claude/plugins/cache/pedro-plugins/bootstrap/*/ | tail -1)lib/conformance.py"
```

A cópia anda em **mão única, repo → máquina**: regra escrita direto no seu
`~/.claude/CLAUDE.md` some no próximo `/bootstrap:setup`. Para ela sobreviver, tem que
subir para `plugins/bootstrap/config/CLAUDE-global.md`.

### Dependência externa

Um plugin depende de um binário que o marketplace **não** instala:

| Plugin | Precisa de | Instalar |
|---|---|---|
| `graphify-guard` | `graphify` | `uv tool install graphifyy` (ou `pipx install graphifyy`) |
| 33 hooks — `grep -rl '\bjq\b' plugins/*/hooks/*.sh \| grep -v -e /test_ $(ls _shared/*.sh \| sed -E 's#.*/#-e /#') \| wc -l` | `jq` (**opcional**) | Nada a fazer: os 29 hooks que decidem — `grep -rlE '(jq\|hj_campo\|hj_eh_falso)[^#]*(tool_input\.command\|session_id\|stop_hook_active)' plugins/*/hooks/*.sh \| grep -v -e /test_ $(ls _shared/*.sh \| sed -E 's#.*/#-e /#') \| wc -l` — leem o payload por `python3` quando falta `jq`, e sem os dois eles avisam em vez de sair calados. Quem quiser a saída formatada: `brew install jq` (macOS) · `choco install jq` (Windows) |
| guards | Python 3 | macOS já traz · Windows: instale o real (o stub da Microsoft Store não executa) |

Sem ele o guarda procura um `graphify-out/graph.json` que nada cria — fica instalado,
calado e sem proteger. O verificador acusa isso na área `dependencia`, e só quando o
plugin que precisa está ligado. Se você não usa grafo, o caminho é desligar o
`graphify-guard` no manifest, não instalar o binário.

### Verificar estado

```bash
claude plugin list                       # plugins instalados
claude plugin marketplace list           # marketplaces conhecidos
claude plugin details <nome>@pedro-plugins   # diagnóstico canônico (mostra Hooks (N))
```

---

## Plugins

Plugins marcados com **⚙️** registram hooks que rodam **sozinhos** (sem slash command) — veja [Hooks automáticos](#hooks-automáticos). Os demais são invocados sob demanda via slash command / skill.

Dois vêm **desligados de fábrica** na receita do `bootstrap` e você liga se quiser:
`graphify-guard` (precisa de um binário externo, veja abaixo) e `intent-guard` (é experimental
e intercepta cada mensagem sua). Ligar: `claude plugin enable <nome>@pedro-plugins`.

### Sessão & continuidade

| Plugin | Trigger | O que faz |
|---|---|---|
| `handoff` ⚙️ | `/handoff` · override `/handoff salvar\|retomar` | Continuidade de sessão em um comando: detecta o estado e roteia — contexto cheio → salva um documento de transferência; sessão recém-limpa → retoma de onde parou. Workspace-aware: o handoff pertence ao projeto que a sessão tocou (resolve a fronteira `.git`), funciona em projeto único, monorepo (`HANDOFF-<módulo>.md`) ou pasta guarda-chuva. |
| `context-guard` ⚙️ | automático (PostToolUse) · setup `/context-guard:setup` | Auto-interrompe o workflow quando o context window passa de um threshold configurável (default 80%) e sugere `/handoff`. Agnóstico de statusLine — encaminha para qualquer comando existente via `CLAUDE_STATUSLINE_FORWARD`. **Use junto com `handoff`.** |
| `intent-guard` ⚙️ | automático (UserPromptSubmit + Stop + PreToolUse) | Caderno append-only dos pedidos **verbatim** do usuário. Classifica cada mensagem (pedido / correção / restrição / conversa) e mantém a lista de pedidos vivos. No fim do turno, bloqueia declarar entrega sem auditoria independente: despacha um auditor que julga cada pedido e grava veredito com prova. O gate carimba num sidecar `.escopo` **quais** pedidos ele perguntou — sem isso, mensagem nova chegando no meio fazia o veredito nascer impossível de aprovar. |
| `sovai` ⚙️ | `/sovai` · PreToolUse | Modo autônomo — executa um plano até o fim sem pausas, checkpoints ou confirmações. Pula bloqueios (sem workaround silencioso), registra cada decisão, roda um passe final headless de `qa-loop` e entrega relatório estruturado. O motor é um **Workflow determinístico** (decompõe → executa → revisa), e isso é **cobrado por hook**: enquanto a missão está armada, todo disparo de sub-agente é negado e mandado de volta pro Workflow. O gate degrada em vez de travar — desiste depois de 3 negações e grava a desistência, porque missão longa com o dono ausente não pode morrer parada. **O revisor julga contra a SPEC, nunca contra a decomposição do próprio motor** — revisar contra o que você mesmo quebrou é circuito fechado, onde quem decompõe errado é aprovado errado. Cinco eixos: spec · as metas de qualidade do projeto (lidas de `.claude/docs/quality-goals.md`, nunca copiadas) · rastreio (toda tarefa carrega seu requisito e seu critério de pronto) · completude · coesão. Agente que morre degrada a missão em vez de derrubar o motor. |

### Planejamento & review

| Plugin | Trigger | O que faz |
|---|---|---|
| `qa-loop` | `/qa-loop <alvo>` | Loop de review→conserto que **para por retornos decrescentes**, não por zero. Motor roda como **Workflow determinístico** (Opus revisa → Opus planeja/adjudica → Sonnet conserta; gate/churn/parada em código). Ancora no plano (3 buckets: implementação / plan-drift / plano-falho) **e nas metas de qualidade do projeto**, lidas de `.claude/docs/quality-goals.md` na hora da revisão em vez de copiadas pra dentro da skill. Regression gate por conserto, accepted-limits, relatório **humano** (HTML) + journal **agêntico**. Substitui `qa`, `rev6` e `iterate`. |
| `grill-me` | `/grill-me` | Entrevista implacável, uma pergunta por vez, sobre um plano/design até esgotar a árvore de decisões. *Por [Matt Pocock](https://github.com/mattpocock/skills).* |
| `grill-with-docs` | `/grill-with-docs` | Igual ao `grill-me`, mas confronta contra o domain model existente (CONTEXT.md, ADRs) e atualiza as docs inline conforme as decisões cristalizam. *Por [Matt Pocock](https://github.com/mattpocock/skills).* |
| `principles` | `/principles` | Carrega princípios de sistema do projeto (`PRINCIPIOS-SISTEMAS.md`), mapeia categorias relevantes ao contexto e gera um guia com WHY + HOW. Dois modos: planning e review. |

### Documentação & conhecimento

| Plugin | Trigger | O que faz |
|---|---|---|
| `project-doc` ⚙️ | `/project-doc` · SessionStart + PreToolUse | Gera um sistema de documentação a partir de **toda** a evidência do projeto (arquivos, handoffs, memória, grafo, git log, transcripts) num journal versionado append-only, projetado em índice `CLAUDE.md` + `.claude/docs/*.md` + ponteiros finos. Scrubber move segredos pra um vault (nunca pro git). Suporta delta/`--deep`/`--rebuild`, monorepo, guard hook doc-first e limpeza de artefatos. |
| `graphify-guard` ⚙️ | automático (SessionStart + PreToolUse) | Garante que os knowledge graphs do `graphify` sejam consultados quando relevante. Aviso no SessionStart quando há grafo; rede no PreToolUse redireciona grep/glob/find cego pra `graphify query` uma vez por sessão. Detecta grafo defasado e oferece `graphify --update`. Defense-in-depth, fail-open, monorepo-aware. |

### Dev, deploy & limpeza

| Plugin | Trigger | O que faz |
|---|---|---|
| `ship` ⚙️ | `/ship` · PreToolUse | Fluxo de deploy pra produção: lint → type-check → commit → push → deploy numa sequência disciplinada. |
| `guardrails` ⚙️ | automático (PostToolUse + PreToolUse) · setup `/guardrails:setup` | Guardrails globais de edição como hooks: lint & type-check pós-edição (JS/TS/Python), um scope-cop LLM que bloqueia edições de UI fora do plano aprovado e um guard de uso indevido de Agent Teams. Portável entre máquinas — substitui hooks hand-rolled no `~/.claude/settings.json`. Rode `/guardrails:setup` uma vez por máquina. |
| `fallow` | `/fallow` | Roda o Fallow (analisador estático JS/TS — código morto, duplicação, complexidade), classifica achados por tipo e confiança, audita o relatório pra pegar falsos-positivos (cron, rotas HTTP, imports dinâmicos) e entrega um relatório interativo onde você escolhe o que limpar. Limpeza com rede de segurança (preview + build/test). |
| `branches` ⚙️ | `/branches` · SessionStart | Relatório de branches paradas com prova: quantas, quais já estão contidas na base, e o que dá pra apagar. Antes de apagar, cria uma tag `archive/<branch>-<data>` como rede de resgate. Aviso silencioso no SessionStart quando não há branch parada. |
| `improve` | `/improve` | Implementa rodadas de melhoria iterativa lendo o `IMPROVEMENT_PROGRAM.md` do app + issues do GitHub com label `autoresearch`. Genérico — funciona com qualquer app que siga a metodologia. |
| `project-doc:design-md` | `/design-md` | Assistente de autoria pro formato `DESIGN.md` do Google (design-system-as-markdown — tokens em YAML + seções em markdown). Escreve seguindo a spec, valida de verdade pelo CLI oficial `@google/design.md` via `npx`, com fallback manual pela spec quando o `npx` não está disponível. Exporta tokens pra Tailwind/DTCG. **Skill do `project-doc`, não plugin separado** — vem junto com ele. |

### Apresentação visual

| Plugin | Trigger | O que faz |
|---|---|---|
| `visual` ⚙️ | `/visual` · automático em planos/diagnósticos (PreToolUse em ExitPlanMode) | Transforma textão do CLI em views HTML dark-theme interativas, abertas no browser com **live sync** de volta pro Claude via daemon local. Modo auto renderiza planos (3+ itens), decisões (2+ opções) e diagnósticos (3+ problemas) sem precisar invocar. **Prosa é recusada pelo programa**: todo campo de texto passa por quatro checagens (≤140 caracteres por bullet, uma frase por bullet, sem conectivo de continuação abrindo, no máximo 6 bullets por bloco) e estourar aborta sem escrever a página. O corpo de cada problema **nasce dobrado** — o título fica visível, a consequência e a proposta abrem com um clique cujo rótulo é derivado do conteúdo, nunca uma etiqueta fixa. |
| `archify` | `/archify` | Diagramas de arquitetura, fluxo, sequência e ciclo de vida como HTML explorável com SVG: profundidade progressiva de leitura, lente semântica, preview de rota entre dois pontos, navegação por capítulos e export pra PNG/SVG/WebM. Aceita descrição em linguagem natural ou Mermaid colado. |
| `slides` | `/slides <arquivo.md> [tema]` | Outline em markdown → deck HTML single-file nível keynote. Sistema de temas (VIU default), linguagem de apresentação com tipografia grande, fidelidade estrita ao texto (nunca inventa frase) e output ao lado do `.md` de origem. |

### Setup de máquina

| Plugin | Trigger | O que faz |
|---|---|---|
| `bootstrap` ⚙️ | `/bootstrap:setup` · automático no SessionStart + Stop | Prepara uma máquina nova: auto-sincroniza marketplaces e plugins via hooks **e** aplica a config global versionada (env, permissões, flags, `CLAUDE.md` global, output style, statusLine resolvido por máquina). Traz também o **Clean Style** (resultado na primeira linha, teto de prosa, prova colada sem teto) e um **verificador de conformidade** que compara a máquina viva contra o contrato versionado sem escrever nada. A qualidade do relato tem duas camadas no fim do turno: uma **mecânica** (conta linhas de prosa, exige veredito na 1ª linha quando a pergunta foi fechada — custo zero, roda sempre) e um **juiz** que chama modelo e só acorda quando a resposta é um relato com prova colada. Os dois são fail-open e têm desligamento visível (`PROSE_CEILING=0`, `FORMA_RELATO=0`). Rode `/bootstrap:setup` uma vez por máquina. |

---

## Hooks automáticos

12 plugins registram hooks que disparam sem slash command — 54 registros no total
(derivado neste run: `python3 scripts/hook_contract.py`; conferido no commit por
`python3 scripts/readme_counts_check.py`):

| Plugin | Eventos | Papel |
|---|---|---|
| `bootstrap` | SessionStart · PostToolUse · Stop×2 | Auto-sync de marketplaces/plugins + os dois guardas de forma do relato |
| `branches` | SessionStart · PostToolUse | Aviso de branch parada, silencioso quando não há |
| `context-guard` | SessionStart · PostToolUse | Vigia o context window, sugere handoff |
| `graphify-guard` | SessionStart · PreToolUse | Redireciona busca cega pro knowledge graph |
| `guardrails` | PreToolUse×3 · PostToolUse | Lint/type-check + scope-cop de UI + gate de pergunta |
| `handoff` | SessionStart · PreToolUse · Stop | Detecta retomada e salva continuidade |
| `intent-guard` | UserPromptSubmit · PreToolUse · PostToolUse×2 · Stop | Caderno de pedidos + gate de entrega (desligado de fábrica) |
| `lixeiro` | SessionStart×2 · PostToolUse · Stop · SessionEnd | Anota quem abriu processo e encerra o que a sessão esqueceu de pé |
| `project-doc` | SessionStart×2 · UserPromptSubmit · PreToolUse×3 · PostToolUse · Stop | Guard doc-first + aviso de doc defasada + gate de plano |
| `ship` | PreToolUse | Guarda o fluxo de deploy |
| `sovai` | PreToolUse | Mantém a missão autônoma no motor Workflow — nega sub-agente enquanto ela dura |
| `visual` | SessionStart · PreToolUse · Stop | Intercepta ExitPlanMode e ressuscita o plano aberto |

> ⚠️ **Hook de plugin vai em `hooks/hooks.json` (subpasta), nunca `hooks.json` na raiz.** Na raiz o Claude Code ignora silenciosamente — `claude plugin details` mostra `Hooks (0)` e nada dispara. `claude plugin validate` passa mesmo assim. Diagnóstico canônico = `claude plugin details <plugin>@pedro-plugins`.

---

## Anatomia de um plugin

```
plugins/<nome>/
├── .claude-plugin/
│   └── plugin.json          # Identidade: nome, versão, descrição, autor
├── hooks/                   # (opcional) automações
│   ├── hooks.json           #   ⚠️ AQUI, não na raiz do plugin
│   └── *.sh / *.py          #   scripts dos hooks
├── skills/<nome>/
│   └── SKILL.md             # Instrução completa da skill
└── lib/                     # (opcional) código auxiliar do plugin (Python stdlib)
```

O catálogo vive em `.claude-plugin/marketplace.json` na raiz — cada plugin tem uma entrada com `name`, `source`, `description`, `category`, `version` e `tags`.

### Código compartilhado entre plugins

Código realmente comum (ex.: `collect_engine.py` — leitura de transcripts, resolução de project-root, `collect()` de itens crus) mora em `_shared/` na raiz e é **vendorado** pra `lib/` de cada consumidor (`handoff`, `project-doc`) via `scripts/sync-shared.sh` — copiado, **não importado em runtime**, porque o Claude Code isola cada plugin no cache. `_shared/` é a fonte-da-verdade: edite lá e rode `scripts/sync-shared.sh` (o `--check` pega drift entre a fonte e as cópias).

---

## Desenvolvendo localmente

```bash
git clone https://github.com/pedroberaldo87/pedro-plugins.git ~/pedro-plugins
```

O `bootstrap` detecta se o repo está clonado localmente e adapta:
- **Com repo:** pode fazer `snapshot` (estado da máquina → manifest, commit, push).
- **Sem repo:** só `apply` (manifest → máquina).

Caminho alternativo:

```bash
export PEDRO_PLUGINS_REPO="/caminho/alternativo/pedro-plugins"
```

---

## Publicando uma mudança

> ⚠️ **Editar skill/hook sem bumpar `version` no `plugin.json` = clientes nunca recebem a atualização.**

1. Edite o plugin em `plugins/<nome>/`.
2. **Bumpe `version`** em `plugins/<nome>/.claude-plugin/plugin.json` (e espelhe em `marketplace.json`).
3. `claude plugin validate` — pega frontmatter inválido (`author` como string, `: `/`<>` em valores) que silenciosamente bloqueia o install.
4. Commit + push.
5. Nos clientes: `/plugin marketplace update` + `claude plugin install <nome>@pedro-plugins` (instalar ≠ atualizar índice).

---

## Licença

Projeto pessoal, publicado como está e sem licença pública.
