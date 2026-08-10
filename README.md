# pedro-plugins

Marketplace público de plugins para [Claude Code](https://docs.claude.com/en/docs/claude-code). Monorepo — cada subdiretório em `plugins/` é um plugin independente (skills, hooks e automações), distribuído via `.claude-plugin/marketplace.json`.

**22 plugins · Markdown + Shell + Python · sem build, sem package manager.**

Os 22 plugins somam **31 skills** — 20 trazem uma só, `visual` traz duas, `project-skills` traz onze, e `graphify-guard` e `vision` não trazem nenhuma.

---

## Índice

- [Instalação](#instalação)
  - [Dependência externa](#dependência-externa)
- [Plugins](#plugins)
  - [project-skills — o ciclo inteiro de um projeto](#project-skills--o-ciclo-inteiro-de-um-projeto)
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
claude plugin install project-skills@pedro-plugins
claude plugin install handoff@pedro-plugins
# ...
```

> ⚠️ **`qa-loop`, `project-doc` e `sovai` não são mais plugins** — viraram skills do
> `project-skills` na fusão de 2026-08-09. Instalar por esses nomes falha; o que você quer
> é `project-skills@pedro-plugins`, e os comandos (`/qa-loop`, `/doc`, `/sprint`) seguem
> iguais depois de instalado.

### Restaurar o setup inteiro (máquina nova)

```bash
# 1. Marketplace + bootstrap
claude plugin marketplace add https://github.com/pedroberaldo87/pedro-plugins.git
claude plugin install bootstrap@pedro-plugins

# 2. Instala marketplaces + plugins do manifest E aplica a config global
#    (env vars, permissões, flags, CLAUDE.md global, output style, statusLine)
/bootstrap:setup
```

Resultado esperado numa máquina zerada: **21 plugins ligados + 1 desligado de fábrica**
(`graphify-guard`), mais os marketplaces de terceiros do manifest.

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
| 35 hooks — `grep -rl '\bjq\b' plugins/*/hooks/*.sh \| grep -v -e /test_ $(ls _shared/*.sh \| sed -E 's#.*/#-e /#') \| wc -l` | `jq` (**opcional**) | Nada a fazer: os 33 hooks que decidem — `grep -rlE '(jq\|hj_campo\|hj_eh_falso)[^#]*(tool_input\.command\|session_id\|stop_hook_active)' plugins/*/hooks/*.sh \| grep -v -e /test_ $(ls _shared/*.sh \| sed -E 's#.*/#-e /#') \| wc -l` — leem o payload por `python3` quando falta `jq`, e sem os dois eles avisam em vez de sair calados. Quem quiser a saída formatada: `brew install jq` (macOS) · `choco install jq` (Windows) |
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

Um vem **desligado de fábrica** na receita do `bootstrap` e você liga se quiser:
`graphify-guard` (precisa de um binário externo, veja abaixo).
Ligar: `claude plugin enable <nome>@pedro-plugins`.

Vinte plugins trazem **uma** skill, com o nome do plugin. Dois não trazem
nenhuma — `graphify-guard` só tem hooks e `vision` só tem a ferramenta
`see_image`. E um traz onze, por isso ganha seção própria logo abaixo.

### project-skills — o ciclo inteiro de um projeto

Um plugin só, **onze skills**, cobrindo a vida de um projeto do primeiro acordo
até a revisão do que foi escrito. Elas conversam entre si por nome de plugin,
nunca por caminho para a pasta da vizinha, e todas julgam contra a lei e o
acordo do projeto — lidos do `.claude/docs/` na hora, nunca copiados para
dentro da skill.

Absorveu `project-doc`, `qa-loop` e `sovai` na fusão de 2026-08-09; os comandos
não mudaram.

**Conceber**

| Comando | O que faz |
|---|---|
| `/start` | Conduz a concepção em seis etapas de acordo — metas de qualidade, arquitetura, interface, jornadas, esquema de funcionamento e lista de funcionalidades —, cada uma num documento próprio, reapresentada até você aprovar, com a aprovação gravada. É **entrevista, não mineração**: pergunta e grava a sua resposta, nunca inventa conteúdo. Também dispara em "vamos conceber". |
| `/pesquisa-referencias` | Levanta repertório quando uma etapa do `/start` trava por falta dele — muitos agentes lendo projetos abertos e produtos pagos em paralelo. O **custo é declarado antes** de qualquer leitura (quantos agentes, quanto tempo, quantas fontes) e nada começa sem o seu aceite. Para por teto de agentes, de fontes, de tempo, ou quando as fontes novas param de trazer coisa nova. |
| `/design-md` | Autoria do `DESIGN.md` — o formato aberto do Google para descrever um design system (valores em YAML + seções em markdown). Valida de verdade pelo programa oficial via `npx`, e cai numa conferência manual pela especificação quando o `npx` não está disponível. Exporta os valores para Tailwind/DTCG. |

**Planejar e executar**

| Comando | O que faz |
|---|---|
| `/plan` | Vira a spec aprovada em plano ticável. **Antes de criar qualquer plano novo, imprime os que ainda estão abertos** no projeto. A palavra "plano" sozinha, sem mais contexto, já é a invocação — justamente para essa lista aparecer antes de você começar mais um. |
| `/sprint` | Executa um plano do começo ao fim **sem pausas, checkpoints ou perguntas**, decidindo o que precisar e anotando cada decisão para o relatório final. O motor é determinístico (decompõe → executa → revisa) e isso é cobrado por hook: enquanto a missão está armada, disparo solto de sub-agente é negado e mandado de volta. O gate **desiste depois de 3 negações** e grava a desistência, porque missão longa com o dono ausente não pode morrer parada. Também dispara em "sova", "não me consulte". |
| `/monitorar` | Imprime o andamento **agora** de toda missão de pé — relógio, o que está executando, quanto tempo de silêncio, placar da última rodada. Lê tudo do disco, sem perguntar nada a ninguém. Serve para quando você volta ao terminal e a barra de status não está contando a história. Também dispara em "tem coisa rodando aí?". |
| `/qa-loop` | Revisa código num laço que **para por retornos decrescentes, não por zero erros**. Ancora no plano: cada achado é classificado em erro de implementação, desvio do plano ou falha do próprio plano — e só o primeiro vira conserto. Cada conserto passa pela suíte inteira antes do seguinte, e no fim um portão absoluto exige lint, tipos, unidade e integração verdes no repositório todo. Também dispara em "revisa isso", "tá 100%?". |

**Documentar**

| Comando | O que faz |
|---|---|
| `/doc` | A rodada completa: minera **toda** a evidência do projeto (arquivos, handoffs, memória, grafo de conhecimento, histórico do git, transcripts) para um journal versionado que só cresce, e projeta em índice `CLAUDE.md` + um `.claude/docs/*.md` por assunto. Um limpador move segredo para um cofre, nunca para o git. Também dispara em "documenta o projeto". |
| `/doc-touch` | O complemento frequente do `/doc`: olha o que o seu diff tocou, descobre quais documentos aquilo afeta e **re-projeta só esses**, sem minerar tudo de novo. Também dispara em "atualiza a doc do que eu mexi". |
| `/doc-load` | Diz o que vale como **régua** hoje e por quê: a lei (constituição, metas de qualidade, restrições), o que foi acordado com você (blueprint, funcionalidades, jornadas, desenho) e o mapa minerado — cada um com a marca do texto e o motivo de valer ou não. Roda no começo de toda etapa que especifica, planeja, implementa, testa ou revisa. Também dispara em "qual é a régua deste projeto". |
| `/project-skills` | O índice da própria família: lê as skills do disco e aponta a certa para o que você quer fazer. Também dispara em "que skill de projeto eu uso aqui". |

### Sessão & continuidade

| Plugin | Trigger | O que faz |
|---|---|---|
| `handoff` ⚙️ | `/handoff` · override `/handoff salvar\|retomar` | Continuidade de sessão em um comando: detecta o estado e roteia — contexto cheio → salva um documento de transferência; sessão recém-limpa → retoma de onde parou. Workspace-aware: o handoff pertence ao projeto que a sessão tocou (resolve a fronteira `.git`), funciona em projeto único, monorepo (`HANDOFF-<módulo>.md`) ou pasta guarda-chuva. |
| `context-guard` ⚙️ | automático (PostToolUse) · setup `/context-guard:setup` | Auto-interrompe o workflow quando o context window passa de um threshold configurável (default 80%) e sugere `/handoff`. Agnóstico de statusLine — encaminha para qualquer comando existente via `CLAUDE_STATUSLINE_FORWARD`. **Use junto com `handoff`.** |
| `intent-guard` ⚙️ | automático (UserPromptSubmit + Stop + PreToolUse) | Caderno append-only dos pedidos **verbatim** do usuário. Classifica cada mensagem (pedido / correção / restrição / conversa) e mantém a lista de pedidos vivos. No fim do turno, bloqueia declarar entrega sem auditoria independente: despacha um auditor que julga cada pedido e grava veredito com prova. O gate carimba num sidecar `.escopo` **quais** pedidos ele perguntou — sem isso, mensagem nova chegando no meio fazia o veredito nascer impossível de aprovar. |

### Planejamento & review

| Plugin | Trigger | O que faz |
|---|---|---|
| `grill-me` | `/grill-me [com-docs]` | Entrevista implacável sobre um plano/design até esgotar a árvore de decisões. Sem argumento, sabatina o plano por ele mesmo; com `com-docs`, confronta contra o domain model existente (CONTEXT.md, ADRs) e atualiza as docs inline conforme as decisões cristalizam. *Por [Matt Pocock](https://github.com/mattpocock/skills).* |
| `principles` | `/principles [review]` | Carrega princípios de sistema genéricos (`PRINCIPIOS-SISTEMAS.md`), mapeia as categorias relevantes ao contexto e gera um guia com o porquê e o como. Dois modos: antes de implementar, e auditando o que já foi escrito. Nunca decide o que ESTE sistema tem que ser — isso é da constituição do projeto. |
| `gauntlet` ⚙️ | `/gauntlet` | Agentes disputam contra um produto real que você nomeia, e **nada do que foi construído se julga sozinho**: cada peça ganha um construtor e um juiz cego separado. **A barra é ficar BOQUIABERTO** — o juiz põe a obra inteira ao lado do alvo inteiro, decide qual metade é mais forte antes de conferir os rótulos, e a resposta dele nasce "não". Ganho pequeno não fecha nada: manda o construtor seguinte propor um caminho NOVO. Fecham peça só o juiz impressionado, a sua ordem, ou o orçamento esgotado — e o diretor cobra a mesma barra no conjunto. Roda como **equipe visível** na conversa: você vê cada agente, dirige em voo, veta e para. Cada veredito é arquivo em disco com o par de observações que o prova; uma trava de PreToolUse impede despacho novo enquanto houver entrega sem juiz, e o fecho é recusado por programa quando falta algum. Nasceu de uma falha real — sete construtores lançados prometendo um juiz em cada briefing, zero juízes lançados, ninguém percebeu. |
| `improve-workflow` | `/improve-workflow` | **Autópsia de uma corrida multi-agente que já terminou.** Lê o transcript inteiro, mede o que cada PAPEL custou (agentes, turnos, tokens, taxa de falha), acende sinais de defeito por contagem em vez de julgamento, e entrega um parecer para você aprovar item a item. Ela **investiga e propõe, e é proibida por desenho de consertar o que achou**. |
| `improve` | `/improve` | Rodadas de melhoria iterativa lendo o `IMPROVEMENT_PROGRAM.md` do app + issues do GitHub com a etiqueta `autoresearch`. Genérico — funciona com qualquer app que siga a metodologia. |

### Documentação & conhecimento

| Plugin | Trigger | O que faz |
|---|---|---|
| `vistoria` | `/vistoria` | Revisa os **arquivos de instrução do próprio marketplace** — skills, hooks e cobradores — e devolve uma página de achados com a prova colada, onde você marca o que vira plano ticável. Roda os cobradores que já existem num comando só e soma as lentes medidas (afirmação de teste que congelou frase morta, script de hook que ninguém registra). **Achado sem prova é recusado na porta.** |
| `check-skills` | `/check-skills` | Confere a saúde do que está instalado na máquina em seis lentes: nome de skill repetido, hooks de origens diferentes no mesmo evento, descrições que disputam o mesmo assunto, versões paradas no cache, processo que a skill abre e não fecha, e citação de plugin irmão que não está instalado aqui. A varredura é de programa; o julgamento das contradições exige ler as descrições lado a lado. |
| `graphify-guard` ⚙️ | automático (SessionStart + PreToolUse) | Garante que os knowledge graphs do `graphify` sejam consultados quando relevante. Aviso no SessionStart quando há grafo; rede no PreToolUse redireciona busca cega para `graphify query` uma vez por sessão. Detecta grafo defasado e oferece atualizar. Defesa em profundidade, fail-open, ciente de monorepo. |
| `vision` | tool `see_image` | Dá olhos ao Claude delegando a um servidor de visão (API compatível com OpenAI). Quando ele precisa entender uma imagem que não lê, chama `see_image(caminho, pergunta)` e o servidor devolve a descrição em texto. O endpoint é configurado por `QWEN_BASE`/`QWEN_MODEL` ou `~/.claude/vision.json` — quem instala aponta para o próprio backend. |

### Dev, deploy & limpeza

| Plugin | Trigger | O que faz |
|---|---|---|
| `ship` ⚙️ | `/ship` · PreToolUse | Fluxo de deploy pra produção: lint → type-check → commit → push → deploy numa sequência disciplinada. |
| `guardrails` ⚙️ | automático (PostToolUse + PreToolUse) · setup `/guardrails:setup` | Guardrails globais de edição como hooks: lint & type-check pós-edição (JS/TS/Python), um scope-cop LLM que bloqueia edições de UI fora do plano aprovado e um guard de uso indevido de Agent Teams. Portável entre máquinas — substitui hooks hand-rolled no `~/.claude/settings.json`. Rode `/guardrails:setup` uma vez por máquina. |
| `fallow` | `/fallow` | Roda o Fallow (analisador estático JS/TS — código morto, duplicação, complexidade), classifica achados por tipo e confiança, audita o relatório pra pegar falsos-positivos (cron, rotas HTTP, imports dinâmicos) e entrega um relatório interativo onde você escolhe o que limpar. Limpeza com rede de segurança (preview + build/test). |
| `branches` ⚙️ | `/branches` · SessionStart | Relatório de branches paradas com prova: quantas, quais já estão contidas na base, e o que dá pra apagar. Antes de apagar, cria uma tag `archive/<branch>-<data>` como rede de resgate. Aviso silencioso no SessionStart quando não há branch parada. |
| `lixeiro` ⚙️ | `/faxina` · automático (SessionEnd + Stop) | Encerra os processos que a sessão abriu e esqueceu de pé — servidor de desenvolvimento, suíte em modo de observação, túnel. A parte automática colhe **só o que a sessão anotou ter aberto**; o comando `/faxina` é o irmão manual, que mostra **tudo** que está de pé, com ou sem procedência, e encerra apenas o que você marcar. |

### Apresentação visual

| Plugin | Trigger | O que faz |
|---|---|---|
| `visual` ⚙️ | `/visual` · automático em planos/diagnósticos (PreToolUse em ExitPlanMode) | Transforma textão do CLI em views HTML dark-theme interativas, abertas no browser com **live sync** de volta pro Claude via daemon local. Modo auto renderiza planos (3+ itens), decisões (2+ opções) e diagnósticos (3+ problemas) sem precisar invocar. **Prosa é recusada pelo programa**: todo campo de texto passa por quatro checagens (≤140 caracteres por bullet, uma frase por bullet, sem conectivo de continuação abrindo, no máximo 6 bullets por bloco) e estourar aborta sem escrever a página. O corpo de cada problema **nasce dobrado** — o título fica visível, a consequência e a proposta abrem com um clique cujo rótulo é derivado do conteúdo, nunca uma etiqueta fixa. |
| `archify` | `/archify` | Diagramas de arquitetura, fluxo, sequência e ciclo de vida como HTML explorável com SVG: profundidade progressiva de leitura, lente semântica, preview de rota entre dois pontos, navegação por capítulos e export pra PNG/SVG/WebM. Aceita descrição em linguagem natural ou Mermaid colado. |
| `slides` | `/slides <arquivo.md> [tema]` | Outline em markdown → deck HTML single-file nível keynote. Sistema de temas (VIU default), linguagem de apresentação com tipografia grande, fidelidade estrita ao texto (nunca inventa frase) e output ao lado do `.md` de origem. |

### Setup de máquina

| Plugin | Trigger | O que faz |
|---|---|---|
| `bootstrap` ⚙️ | `/bootstrap:setup` · automático no SessionStart + PostToolUse | Prepara uma máquina nova: auto-sincroniza marketplaces e plugins via hooks **e** aplica a config global versionada (env, permissões, flags, `CLAUDE.md` global, output style, statusLine resolvido por máquina). Traz também o **Clean Style** (resultado na primeira linha, teto de prosa, prova colada sem teto) e um **verificador de conformidade** que compara a máquina viva contra o contrato versionado sem escrever nada. Rode `/bootstrap:setup` uma vez por máquina. |

---

## Hooks automáticos

12 plugins registram hooks que disparam sem slash command — 54 registros no total
(derivado neste run: `python3 scripts/hook_contract.py`; conferido no commit por
`python3 scripts/readme_counts_check.py`):

| Plugin | Eventos | Papel |
|---|---|---|
| `bootstrap` | SessionStart×2 · PostToolUse | Auto-sync de marketplaces e plugins, e o aviso depois de um comando de plugin |
| `branches` | SessionStart×2 · PostToolUse | Aviso de branch parada, silencioso quando não há |
| `context-guard` | SessionStart×2 · PostToolUse | Vigia o quanto da conversa já foi usado e sugere o handoff |
| `gauntlet` | SessionStart×2 · PreToolUse | Nega despacho novo enquanto houver entrega sem juiz, e reencontra a disputa no arranque |
| `graphify-guard` | SessionStart×2 · PreToolUse | Redireciona busca cega para o knowledge graph |
| `guardrails` | SessionStart · PreToolUse×4 · PostToolUse | Lint e type-check pós-edição, scope-cop de UI, e o gate de pergunta sem apoio |
| `handoff` | SessionStart×2 · PreToolUse · Stop | Detecta retomada e salva a continuidade da sessão |
| `intent-guard` | SessionStart · UserPromptSubmit · PostToolUse×2 · Stop | Caderno de pedidos verbatim e gate de entrega |
| `lixeiro` | SessionStart×2 · PostToolUse · Stop · SessionEnd | Anota quem abriu processo e encerra o que a sessão esqueceu de pé |
| `project-skills` | SessionStart×4 · UserPromptSubmit · PreToolUse×6 · PostToolUse×2 · Stop×2 | Guarda doc-first, aviso de doc defasada, gate de plano, e o motor autônomo na barra de status |
| `ship` | SessionStart · PreToolUse | Guarda o fluxo de deploy |
| `visual` | SessionStart · Stop | Intercepta a saída do modo de plano e ressuscita o plano aberto |

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

Código realmente comum mora em `_shared/` na raiz e é **vendorado** pra dentro de cada consumidor via `scripts/sync-shared.sh` — copiado, **não importado em runtime**, porque o Claude Code isola cada plugin no cache. São 12 arquivos compartilhados hoje, espalhados em 60 cópias: `collect_engine.py` (leitura de transcripts, resolução de project-root) vive em `handoff` e `project-skills`; `hook-json.sh` (leitura do payload do hook sem depender de `jq`) em 12 plugins; `regua_texto.py` (a régua que recusa prosa) em 10. `_shared/` é a fonte-da-verdade: edite lá e rode `scripts/sync-shared.sh` (o `--check` pega drift entre a fonte e as cópias).

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
