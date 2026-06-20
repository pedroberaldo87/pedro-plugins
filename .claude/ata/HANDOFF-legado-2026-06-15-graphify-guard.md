# Session Handoff
Date: 2026-06-15
Project: /Users/pedroberaldo/PROGRAMACAO/PEDRO/pedro-plugins

## Resumo
Sessão criou o plugin **graphify-guard** (garante que knowledge graphs do graphify sejam consultados), descobriu e corrigiu uma armadilha que mantinha os hooks de TODOS os 5 plugins do marketplace mortos, atualizou a documentação do pedro-plugins, tornou a sugestão de graphify na skill project-doc incondicional, e gerou o knowledge graph do próprio pedro-plugins. Tudo commitado e pushed; 4 dos 5 plugins com hook estão ativos.

## Contexto e Propósito
Começou com a pergunta do Pedro: "sabemos que não estamos usando os grafos do graphify nas nossas sessões. como garantir que seja usado quando relevante?" — no contexto do projeto VIU (cwd da sessão é `/Users/pedroberaldo/PROGRAMACAO/VIU`), que tem grafos graphify em subprojetos (VIUSTUDIO-TOOLS, VIUSTUDIO-FINANCE) que ficavam parados enquanto o Claude fazia grep/Explore cego.

A solução virou um **plugin** (graphify-guard) no marketplace pedro-plugins. No processo, descobrimos que NENHUM hook de plugin do marketplace funcionava (armadilha de localização), o que dominou a segunda metade da sessão.

## Discussões e Decisões
- **Plugin, não settings.json:** Pedro pediu para empacotar como plugin (versionável no git, sincronizável entre máquinas, ligável/desligável com `/plugin`) em vez de hooks soltos no `~/.claude/settings.json`.
- **Defense-in-depth (decisão de design):** o graphify-guard tem 3 camadas que cobrem falhas DIFERENTES — SessionStart (proativo: avisa que há grafo), PreToolUse (reativo: intercepta grep cego), helper detect (DRY). A sugestão original do Pedro era só interceptar o grep; elevei para defense-in-depth porque o interceptador sozinho não cobre quando o Claude responde arquitetura de memória sem nem buscar. Pedro reforçou: "não se limite ao que sugeri, faz best practices".
- **CAUSA-RAIZ da sessão (hooks mortos):** o Claude Code só carrega hooks de plugin de **`hooks/hooks.json`** (subpasta), NUNCA de `hooks.json` na raiz do plugin. Na raiz = ignorado silenciosamente (`claude plugin validate` passa, mas `claude plugin details` mostra `Hooks (0)` e nada dispara). Confirmado comparando `claude plugin details superpowers` (subpasta → Hooks(1)) vs os do pedro-plugins (raiz → Hooks(0)) + doc oficial. TODOS os 5 plugins com hook estavam com hooks.json na raiz.
- **O agente claude-code-guide alucinou:** quando os hooks não apareciam, consultei o subagent claude-code-guide, que inventou que "precisa reiniciar o Claude Code" (rotulando como não-documentado). Repassei isso ao Pedro com tom de certeza — ERRO. A causa real era a localização. Lição registrada: verificar na fonte (doc oficial, `claude plugin details`), não confiar em agent que preenche lacunas.
- **cwd container fix:** o guard, para comandos Bash, originalmente só subia a árvore do cwd. Como o Pedro abre o monorepo pela raiz (`/VIU`, sem grafo próprio), o guard ficava mudo. Adicionei: inspecionar paths dentro do comando + descer do cwd para achar grafos de subprojetos.
- **project-doc incondicional:** eu suprimi a oferta de `/graphify` no pedro-plugins ("baixo acoplamento, não compensa"), contrariando a regra da própria skill. Pedro mandou remover toda ressalva — a skill agora SEMPRE oferece grafo quando `graphify-out/` não existe; o modelo não julga "vale a pena". Lição: julgamento do modelo sobre "vale X" não é confiável; oferecer e deixar Pedro decidir.

## O Que Foi Feito
6 commits em `pedro-plugins` (main, tudo pushed):
- `dd75977` — cria graphify-guard, hooks em hooks/hooks.json, cobre cwd container.
- `c5c2e89` — move hooks.json → hooks/hooks.json em visual/ship/context-guard/bootstrap-third-party (a correção em massa).
- `0961f2d` — doc (CLAUDE.md + architecture.md + patterns.md) com a armadilha documentada + graphify-guard no catálogo.
- `1ae53d9` — sync automático do bootstrap (não-nosso).
- `6c7ad8e` — skill project-doc: sugestão de graphify INCONDICIONAL.
- `353924f` — knowledge graph do pedro-plugins (graph.json/html/REPORT) + seção Knowledge Graph fiada no CLAUDE.md.

Também (fora do repo): atualizei 2 memórias em `/Users/pedroberaldo/.claude/projects/-Users-pedroberaldo-PROGRAMACAO-VIU/memory/` — `pedro-plugins-cache-gotcha.md` (regra hooks/hooks.json + diagnóstico) e `feedback-sugestao-e-piso-nao-teto.md` (não suprimir ofertas com julgamento próprio). Plano da sessão em `/Users/pedroberaldo/.claude/plans/sabemos-que-n-o-estamos-kind-spindle.md`.

Sincronizei manualmente os caches em `~/.claude/plugins/cache/pedro-plugins/<nome>/<versão>/` para os hooks valerem nesta máquina já. Pedro rodou `/reload-plugins` (saltou para 13 hooks) e `/plugin install graphify-guard@pedro-plugins`.

## Em Andamento
Nada pendente. Sessão fechou com tudo commitado, pushed, verificado e os hooks ativos. O `/project-doc` final rodou em modo verify (não-destrutivo) — a doc passou 8/8 checks, não precisou regenerar.

## Próximos Passos
1. (Opcional) Habilitar o bootstrap-third-party se quiser os hooks dele ativos: `/plugin enable bootstrap-third-party@pedro-plugins` + `/reload-plugins`. Hoje está `enabled: false` em `settings.local.json` (escolha do Pedro, não mexi).
2. (Opcional) Explorar o grafo: a pergunta sugerida mais interessante é "por que `Architecture Doc` faz ponte entre `Documentation System (CLAUDE.md)` e `Bootstrap & Marketplace Sync`?" — `cd pedro-plugins && graphify query "..."`.
3. (Opcional) Em OUTRAS máquinas, sincronizar: `/plugin marketplace update pedro-plugins` → `/plugin update <nome>@pedro-plugins` → `/reload-plugins`. As versões foram bumpadas (graphify-guard 1.0.1, visual 1.1.1, ship 1.0.1, context-guard 1.1.1, bootstrap 0.1.3, project-doc 2.2.1) justamente para forçar refresh do cache.

## Problemas Conhecidos
- **bootstrap-third-party desligado:** hooks corrigidos e reconhecidos (`Hooks (2)`), mas o plugin está `false` em `settings.local.json` → não dispara até habilitar.
- **Comportamento dormente que agora ATIVA** (ao dar reload): `visual` intercepta todo ExitPlanMode (auto-visual; desligar com `/visual -auto-off`); `context-guard` passa a interromper de verdade em 80% de contexto (antes só mostrava % no statusline); `ship` bloqueia deploy com teste quebrado (só em comandos de deploy reais). São features que o Pedro construiu mas estavam mortas — podem surpreender.
- **context-guard / setup:** os hooks dele agora vêm do plugin (`hooks/hooks.json`). NÃO rodar `/context-guard:setup` para os hooks — ela registraria no `settings.json` e duplicaria. O setup deve cuidar SÓ do statusLine wrapper.
- **Inconsistência de versão do cache project-doc (pré-existente, não crítica):** installPath do cache é `project-doc/2.3.0` mas o marketplace.json declara `2.2.1`. O SKILL.md editado foi sincronizado no installPath 2.3.0 (a regra incondicional já vale). Alinhar as versões um dia.
- **`claude ... --plugin-dir`** não existe como flag de `plugin details` (testei). Diagnóstico de hook = `claude plugin details <nome>@pedro-plugins` lendo do cache.

## Detalhes Técnicos
- **Anatomia de plugin (a regra de ouro):** `plugins/<nome>/` = `.claude-plugin/plugin.json` + `hooks/hooks.json` (NUNCA `hooks.json` na raiz) + `hooks/*.sh` (chmod +x) + `skills/<nome>/SKILL.md`. Scripts referenciados como `${CLAUDE_PLUGIN_ROOT}/hooks/<script>.sh`.
- **graphify-guard:** `hooks/graphify-detect.sh` (helper: acha grafo subindo/descendo + freshness por mtime; modo `--one <proj>` e modo descida), `hooks/sessionstart-graphify.sh` (additionalContext JSON), `hooks/pretooluse-graphify-guard.sh` (matcher `Grep|Glob|Bash`, deny 1x/sessão via sentinel `/tmp/claude-graphify-guard-<session_id>`, fail-open). PROVA DE VIDA: o PreToolUse interceptou um `grep` ao vivo nesta sessão e apontou VIUSTUDIO-TOOLS descendo de /VIU.
- **Cache do marketplace:** plugins carregam de `~/.claude/plugins/cache/pedro-plugins/<nome>/<versão>/`, não do source. Editar o source não basta nesta máquina — sincronizar o cache (cp por cima) + `/reload-plugins`. O cache só auto-refresca em outras máquinas com bump de versão.
- **Instalação:** `/plugin install <nome>@pedro-plugins` faz tudo (cache + installed_plugins.json + enabledPlugins + registra hooks). Instalação MANUAL dos 3 registros NÃO registra hooks — não gambiarrar. `/plugin marketplace update` só atualiza índice.
- **Grafo do pedro-plugins:** `graphify-out/` (graph.json/html/GRAPH_REPORT.md versionados; `cache/` + `.graphify_python` + `.graphify_root` gitignorados). 417 nós, 463 arestas, 50 comunidades (44 shell AST + 35 markdown semantic via 4 subagents). God nodes: PRINCIPIOS-SISTEMAS.md, visual skill, iterate skill, build_buckets() (fallow), SlideText (slides). Atualizar com `cd pedro-plugins && graphify . --update` após ciclo de mudanças.

## Contexto Extra
- **Preferências fortes do Pedro reafirmadas nesta sessão:** quando uma sugestão dele é dada, é piso (elevar com best practices), não teto. Não suprimir ofertas de ferramentas com julgamento próprio de "vale a pena" — oferecer e deixar ele decidir. Quando frustrado, exigiu: "pesquisa direito, investiga, implementa, resolve, testa, e SÓ ENTÃO entrega" — nada de chute, verificar na fonte. CONFIRMADO vs INFERIDO sempre.
- O graphify-guard ajuda em QUALQUER projeto com `graphify-out/`, não só pedro-plugins — inclusive o VIU (motivação original).
