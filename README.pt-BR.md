# pedro-plugins

Marketplace público de plugins para [Claude Code](https://code.claude.com/docs/en/overview): skills, hooks e automações em Markdown, Bash e Python, para quem usa o Claude Code no dia a dia e quer instalar só o que precisa.

[English](README.md) · **Português**

[![portability](https://github.com/pedroberaldo87/pedro-plugins/actions/workflows/portability.yml/badge.svg)](https://github.com/pedroberaldo87/pedro-plugins/actions/workflows/portability.yml)
![Plataformas: macOS, Linux e Windows](https://img.shields.io/badge/plataformas-macOS%20%C2%B7%20Linux%20%C2%B7%20Windows-informational)
![Roda no Claude Code](https://img.shields.io/badge/roda%20no-Claude%20Code-blueviolet)
[![Licença: MIT](https://img.shields.io/badge/Licen%C3%A7a-MIT-yellow.svg)](LICENSE)

Monorepo: cada subdiretório de `plugins/` é um plugin independente, distribuído pelo catálogo `.claude-plugin/marketplace.json`.

**24 plugins · Markdown + Shell + Python · sem build, sem package manager.**

Os 24 plugins somam **37 skills** — 19 trazem uma só, `visual` traz duas, `2op` traz três, `project-skills` traz treze, e `graphify-guard` e `vision` não trazem nenhuma.

Este é um repositório de ferramentas, sem interface gráfica, então não há screenshot. A instalação é um comando no terminal:

```console
$ claude plugin marketplace add pedroberaldo87/pedro-plugins
$ claude plugin install handoff@pedro-plugins
```

---

## Índice

- [Funcionalidades](#funcionalidades)
- [Instalação](#instalação)
  - [Escolher só o que quiser](#escolher-só-o-que-quiser)
  - [Restaurar o setup inteiro (máquina nova)](#restaurar-o-setup-inteiro-máquina-nova)
  - [Dependências externas](#dependências-externas)
  - [Conferir o estado](#conferir-o-estado)
- [Configuração](#configuração)
- [Uso: os plugins](#uso-os-plugins)
  - [project-skills — o ciclo inteiro de um projeto](#project-skills--o-ciclo-inteiro-de-um-projeto)
  - [Sessão e continuidade](#sessão-e-continuidade)
  - [Planejamento e revisão](#planejamento-e-revisão)
  - [Documentação e conhecimento](#documentação-e-conhecimento)
  - [Dev, deploy e limpeza](#dev-deploy-e-limpeza)
  - [Apresentação visual](#apresentação-visual)
  - [Setup de máquina](#setup-de-máquina)
- [Como funciona](#como-funciona)
  - [Hooks automáticos](#hooks-automáticos)
  - [Anatomia de um plugin](#anatomia-de-um-plugin)
  - [Código compartilhado entre plugins](#código-compartilhado-entre-plugins)
- [Desenvolvimento](#desenvolvimento)
  - [Testes e conferências](#testes-e-conferências)
  - [Publicar uma mudança](#publicar-uma-mudança)
- [Documentação do projeto](#documentação-do-projeto)
- [Segurança](#segurança)
- [Contribuindo](#contribuindo)
- [Licença](#licença)

---

## Funcionalidades

- **Instalação à la carte:** 24 plugins independentes; instale só os que quiser.
- **Ciclo de projeto (`project-skills`):** concepção, plano, execução autônoma, revisão por severidade e documentação.
- **Continuidade de sessão:** `handoff`, `context-guard` e `intent-guard` preservam o que importa entre sessões.
- **Revisão e segunda opinião:** `grill-me`, `2op`, `gauntlet`, `improve-workflow`, `vistoria`.
- **Higiene de desenvolvimento:** `ship`, `branches`, `lixeiro`, `fallow`, `guardrails` e `sec` (cadeia de suprimentos).
- **Saída visual:** `visual`, `archify` e `slides` geram HTML interativo, diagramas e apresentações.
- **Máquina nova em um comando:** `bootstrap` instala marketplaces e plugins e aplica a configuração global versionada.
- **Sem build:** Markdown, Bash e Python da biblioteca padrão (o daemon do `visual` usa Node).

---

## Instalação

Precisa do [Claude Code](https://code.claude.com/docs/en/overview) e de Python 3 no PATH. Os comandos abaixo usam a CLI `claude`; dentro de uma sessão, o equivalente é `/plugin marketplace add …` e `/plugin install …`.

### Escolher só o que quiser

```bash
# 1. Adicionar o marketplace (uma vez por máquina)
claude plugin marketplace add pedroberaldo87/pedro-plugins

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
claude plugin marketplace add pedroberaldo87/pedro-plugins
claude plugin install bootstrap@pedro-plugins
```

```text
# 2. Dentro de uma sessão do Claude Code: instala marketplaces + plugins do manifest
#    E aplica a config global (env vars, permissões, flags, CLAUDE.md global,
#    output style, statusLine)
/bootstrap:setup
```

Resultado esperado numa máquina zerada: **23 plugins ligados + 1 desligado de fábrica**
(`graphify-guard`), mais os marketplaces de terceiros do manifest.

> ⚠️ **Se aparecer `sync incompleto: N operações falharam`, rode `/bootstrap:setup` de novo.**
> Medido numa instalação limpa: a primeira rodada deixou um marketplace de terceiro para trás
> e a segunda o instalou. O script é convergente de propósito (re-rodar é seguro e nunca toca
> em marketplace que o manifest não declara). O sync do início de sessão não termina o
> serviço: ele só lista o que falta, e o `/bootstrap:setup` instala depois que você confirma
> a lista.

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

### Dependências externas

Um plugin depende de um binário que o marketplace **não** instala:

| Plugin | Precisa de | Instalar |
|---|---|---|
| `graphify-guard` | `graphify` | `uv tool install graphifyy` (ou `pipx install graphifyy`) |
| 35 hooks — `grep -rl '\bjq\b' plugins/*/hooks/*.sh \| grep -v -e /test_ $(ls _shared/*.sh \| sed -E 's#.*/#-e /#') \| wc -l` | `jq` (**opcional**) | Nada a fazer: os 33 hooks que decidem — `grep -rlE '(jq\|hj_campo\|hj_eh_falso)[^#]*(tool_input\.command\|session_id\|stop_hook_active)' plugins/*/hooks/*.sh \| grep -v -e /test_ $(ls _shared/*.sh \| sed -E 's#.*/#-e /#') \| wc -l` — leem o payload por `python3` quando falta `jq`, e sem os dois eles avisam em vez de sair calados. Quem quiser a saída formatada: `brew install jq` (macOS) · `choco install jq` (Windows) |
| guards | Python 3 | macOS já traz · Windows: instale o real (o stub da Microsoft Store não executa) |

**Instalar não precisa de `jq`.** O `/bootstrap:setup` roda inteiro sobre Python — as
leituras e o merge de configuração vivem em `plugins/bootstrap/lib/cfgjson.py`, e o teste
ao lado compara cada saída com a do `jq` de verdade para as duas não divergirem. O único
lugar que ainda usa `jq` é o `snapshot.sh`, e ele só roda em máquina que **clonou** o
repositório (grava o estado da máquina de volta no manifesto); quem instala pelo
marketplace nunca passa por ele.

**Windows:** instale o Python do site oficial, não o da Microsoft Store. O sistema traz um
`python3` de mentira que responde uma propaganda em vez de rodar, e por isso o marketplace
testa se o Python **executa**, em vez de só existir no caminho.

Sem o `graphify` o guarda procura um `graphify-out/graph.json` que nada cria — fica instalado,
calado e sem proteger. O verificador acusa isso na área `dependencia`, e só quando o
plugin que precisa está ligado. Se você não usa grafo, o caminho é desligar o
`graphify-guard` no manifest, não instalar o binário.

### Conferir o estado

```bash
claude plugin list                            # plugins instalados
claude plugin marketplace list                # marketplaces conhecidos
claude plugin details <nome>@pedro-plugins    # diagnóstico canônico (mostra Hooks (N))
```

---

## Configuração

Tudo é opcional; os padrões funcionam. Estas são as variáveis e os arquivos que o código lê de verdade:

| Variável / arquivo | Usado por | Padrão | O que faz |
|---|---|---|---|
| `PEDRO_PLUGINS_REPO` | `bootstrap` | `$HOME/pedro-plugins` | Onde fica o clone local do repositório. Com clone, o `bootstrap` também faz `snapshot` (máquina → manifest); sem, só `apply` (manifest → máquina). |
| `CLAUDE_STATUSLINE_FORWARD` | `context-guard`, `bootstrap` | definido pelo `bootstrap` | Comando de statusLine para onde o `context-guard` encaminha o JSON que recebe. Funciona com qualquer statusLine que você já tenha. |
| `CLAUDE_CONTEXT_THRESHOLD` | `context-guard` | `85` (também gravado pelo `bootstrap`) | Percentual do context window a partir do qual o guarda interrompe e sugere `/handoff`. |
| `CLAUDE_CONTEXT_TOKENS` | `context-guard` | `850000` | Mesmo corte, em tokens. O que estourar primeiro dispara. |
| `QWEN_BASE`, `QWEN_MODEL` | `vision` | sem padrão | Endereço e modelo do servidor de visão (API compatível com OpenAI). |
| `QWEN_TIMEOUT` | `vision` | `180` | Tempo máximo de espera, em segundos (modelo frio demora). |
| `~/.claude/vision.json` | `vision` | ausente | Alternativa às variáveis: `{"base": "...", "model": "..."}`. |

---

## Uso: os plugins

Plugins marcados com **⚙️** registram hooks que rodam **sozinhos** (sem slash command) — veja [Hooks automáticos](#hooks-automáticos). Os demais são invocados sob demanda via slash command / skill.

Um vem **desligado de fábrica** na receita do `bootstrap` e você liga se quiser:
`graphify-guard` (precisa de um binário externo, veja acima).
Ligar: `claude plugin enable <nome>@pedro-plugins`.

Dezenove plugins trazem **uma** skill cada (no `lixeiro` ela se chama `/faxina`). Dois não trazem
nenhuma — `graphify-guard` só tem hooks e `vision` só tem a ferramenta
`see_image`. `visual` traz duas e `2op` traz três. E `project-skills` traz treze, por isso ganha
seção própria logo abaixo.

### project-skills — o ciclo inteiro de um projeto

Um plugin só, **treze skills**, cobrindo a vida de um projeto do primeiro acordo
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
| `/reentrada` | Para quando o `/sprint` morreu de madrugada e você voltou de manhã: lê o desfecho da última corrida no ledger, classifica (segue no motor, conserta e relança, ou espera o dono) e **rearma o laço do ponto onde parou**, em vez de largar do zero. Também dispara em "retoma o sprint". |
| `/monitorar` | Imprime o andamento **agora** de toda missão de pé — relógio, o que está executando, quanto tempo de silêncio, placar da última rodada. Lê tudo do disco, sem perguntar nada a ninguém. Serve para quando você volta ao terminal e a barra de status não está contando a história. Também dispara em "tem coisa rodando aí?". |
| `/qa-loop` | Revisa código num laço que **fecha por SEVERIDADE, não por gasto**: acaba quando uma rodada completa não acha nada acima do piso de severidade, confirmada por um re-sweep independente — nunca por rodada, token ou tempo. Ancora no plano: cada achado é classificado em erro de implementação, desvio do plano ou falha do próprio plano — e só o primeiro vira conserto. Cada conserto passa pela suíte inteira antes do seguinte, e no fim um portão absoluto exige lint, tipos, unidade e integração verdes no repositório todo. Também dispara em "revisa isso", "tá 100%?". |
| `/completude` | Mede se o trabalho **fecha**, e devolve o que falta **nomeado item a item** — nunca porcentagem. Dois lados na mesma medição: a cadeia inteira (funcionalidade → requisito → tarefa → prova do tique) e os artigos da lei do projeto que nenhuma tarefa representa. Quem conta é o programa, não o olho, e documento que a medição não achou não vira verde. Também dispara em "o que falta pra fechar". |

**Documentar**

| Comando | O que faz |
|---|---|
| `/doc` | A rodada completa: minera **toda** a evidência do projeto (arquivos, handoffs, memória, grafo de conhecimento, histórico do git, transcripts) para um journal versionado que só cresce, e projeta em índice `CLAUDE.md` + um `.claude/docs/*.md` por assunto. Um limpador move segredo para um cofre, nunca para o git. Também dispara em "documenta o projeto". |
| `/doc-touch` | O complemento frequente do `/doc`: olha o que o seu diff tocou, descobre quais documentos aquilo afeta e **re-projeta só esses**, sem minerar tudo de novo. Também dispara em "atualiza a doc do que eu mexi". |
| `/doc-load` | Diz o que vale como **régua** hoje e por quê: a lei (constituição, metas de qualidade, restrições), o que foi acordado com você (blueprint, funcionalidades, jornadas, desenho) e o mapa minerado — cada um com a marca do texto e o motivo de valer ou não. Roda no começo de toda etapa que especifica, planeja, implementa, testa ou revisa. Também dispara em "qual é a régua deste projeto". |
| `/project-skills` | O índice da própria família: lê as skills do disco e aponta a certa para o que você quer fazer. Também dispara em "que skill de projeto eu uso aqui". |

### Sessão e continuidade

| Plugin | Trigger | O que faz |
|---|---|---|
| `handoff` ⚙️ | `/handoff` · override `/handoff salvar\|retomar` | Continuidade de sessão em um comando: detecta o estado e roteia — contexto cheio → salva um documento de transferência; sessão recém-limpa → retoma de onde parou. Workspace-aware: o handoff pertence ao projeto que a sessão tocou (resolve a fronteira `.git`), funciona em projeto único, monorepo (`HANDOFF-<módulo>.md`) ou pasta guarda-chuva. |
| `context-guard` ⚙️ | automático (PostToolUse) · setup `/context-guard:setup` | Auto-interrompe o workflow quando o context window passa de um threshold configurável (padrão 85%) e sugere `/handoff`. Agnóstico de statusLine — encaminha para qualquer comando existente via `CLAUDE_STATUSLINE_FORWARD`. **Use junto com `handoff`.** |
| `intent-guard` ⚙️ | automático (UserPromptSubmit + Stop + PreToolUse) | Caderno append-only dos pedidos **verbatim** do usuário. Classifica cada mensagem (pedido / correção / restrição / conversa) e mantém a lista de pedidos vivos. No fim do turno, bloqueia declarar entrega sem auditoria independente: despacha um auditor que julga cada pedido e grava veredito com prova. O gate carimba num sidecar `.escopo` **quais** pedidos ele perguntou — sem isso, mensagem nova chegando no meio fazia o veredito nascer impossível de aprovar. |

### Planejamento e revisão

| Plugin | Trigger | O que faz |
|---|---|---|
| `grill-me` | `/grill-me [com-docs]` | Entrevista implacável sobre um plano/design até esgotar a árvore de decisões. Sem argumento, sabatina o plano por ele mesmo; com `com-docs`, confronta contra o domain model existente (CONTEXT.md, ADRs) e atualiza as docs inline conforme as decisões cristalizam. *Por [Matt Pocock](https://github.com/mattpocock/skills).* |
| `principles` | `/principles [review]` | Carrega princípios de sistema genéricos (`PRINCIPIOS-SISTEMAS.md`), mapeia as categorias relevantes ao contexto e gera um guia com o porquê e o como. Dois modos: antes de implementar, e auditando o que já foi escrito. Nunca decide o que ESTE sistema tem que ser — isso é da constituição do projeto. |
| `gauntlet` ⚙️ | `/gauntlet` | Agentes disputam contra um produto real que você nomeia, e **nada do que foi construído se julga sozinho**: cada peça ganha um construtor e um juiz cego separado. **A barra é ficar BOQUIABERTO** — o juiz põe a obra inteira ao lado do alvo inteiro, decide qual metade é mais forte antes de conferir os rótulos, e a resposta dele nasce "não". Ganho pequeno não fecha nada: manda o construtor seguinte propor um caminho NOVO. Fecham peça só o juiz impressionado, a sua ordem, ou o orçamento esgotado — e o diretor cobra a mesma barra no conjunto. Roda como **equipe visível** na conversa: você vê cada agente, dirige em voo, veta e para. Cada veredito é arquivo em disco com o par de observações que o prova; uma trava de PreToolUse impede despacho novo enquanto houver entrega sem juiz, e o fecho é recusado por programa quando falta algum. Nasceu de uma falha real — sete construtores lançados prometendo um juiz em cada briefing, zero juízes lançados, ninguém percebeu. |
| `improve-workflow` | `/improve-workflow` | **Autópsia de uma corrida multi-agente que já terminou.** Lê o transcript inteiro, mede o que cada PAPEL custou (agentes, turnos, tokens, taxa de falha), acende sinais de defeito por contagem em vez de julgamento, e entrega um parecer para você aprovar item a item. Ela **investiga e propõe, e é proibida por desenho de consertar o que achou**. |
| `improve` | `/improve` | Rodadas de melhoria iterativa lendo o `IMPROVEMENT_PROGRAM.md` do app + issues do GitHub com a etiqueta `autoresearch`. Genérico — funciona com qualquer app que siga a metodologia. |
| `2op` | `/2op` · `/2op-opus` · `/2op-sonnet` | Segunda opinião de **outro modelo dentro da mesma sessão** — sem subagente, sem re-briefing, sem orquestração. O campo `model` do frontmatter troca o modelo pelo turno inteiro, com o contexto já carregado; o modelo da sessão volta sozinho no próximo prompt. O revisor abre com CONCORDO / CONCORDO COM RESSALVA / DISCORDO, rotula cada afirmação CONFIRMADO ou INFERIDO, e é proibido de editar arquivo. Um comando por cabeça porque o frontmatter não interpola argumento (`model: $0` reprova a invocação). |

### Documentação e conhecimento

| Plugin | Trigger | O que faz |
|---|---|---|
| `vistoria` | `/vistoria` | Revisa os **arquivos de instrução do próprio marketplace** — skills, hooks e cobradores — e devolve uma página de achados com a prova colada, onde você marca o que vira plano ticável. Roda os cobradores que já existem num comando só e soma as lentes medidas (afirmação de teste que congelou frase morta, script de hook que ninguém registra). **Achado sem prova é recusado na porta.** |
| `check-skills` | `/check-skills` | Confere a saúde do que está instalado na máquina em seis lentes: nome de skill repetido, hooks de origens diferentes no mesmo evento, descrições que disputam o mesmo assunto, versões paradas no cache, processo que a skill abre e não fecha, e citação de plugin irmão que não está instalado aqui. A varredura é de programa; o julgamento das contradições exige ler as descrições lado a lado. |
| `graphify-guard` ⚙️ | automático (SessionStart + PreToolUse) | Garante que os knowledge graphs do `graphify` sejam consultados quando relevante. Aviso no SessionStart quando há grafo; rede no PreToolUse redireciona busca cega para `graphify query` uma vez por sessão. Detecta grafo defasado e oferece atualizar. Defesa em profundidade, fail-open, ciente de monorepo. |
| `vision` | tool `see_image` | Dá olhos ao Claude delegando a um servidor de visão (API compatível com OpenAI). Quando ele precisa entender uma imagem que não lê, chama `see_image(caminho, pergunta)` e o servidor devolve a descrição em texto. O endpoint é configurado por `QWEN_BASE`/`QWEN_MODEL` ou `~/.claude/vision.json` — quem instala aponta para o próprio backend. |

### Dev, deploy e limpeza

| Plugin | Trigger | O que faz |
|---|---|---|
| `sec` | `/sec` | Confere a cadeia de suprimentos do projeto aberto e da máquina contra bases públicas (OSV e a lista de malware da Aikido Intel), **sem revisar o seu código**. Projeto: lockfiles de npm, pnpm, yarn, uv, poetry e pip, ações do GitHub e `.mcp.json`. Máquina: Claude Code, plugins, MCP, `npm -g`, pipx, Node e Homebrew. Separa pacote envenenado, falha conhecida, porta aberta e desatualizado; entrega um relatório com checkbox e corrige só o que você marcar. Fonte que não respondeu sai como NÃO VERIFICADO, nunca como verde. |
| `ship` ⚙️ | `/ship` · PreToolUse | Fluxo de deploy pra produção: lint → type-check → commit → push → deploy numa sequência disciplinada. |
| `guardrails` ⚙️ | automático (PostToolUse + PreToolUse) · setup `/guardrails:setup` | Guardrails globais de edição como hooks: lint & type-check pós-edição (JS/TS/Python), um scope-cop LLM que bloqueia edições de UI fora do plano aprovado e um guard de uso indevido de Agent Teams. Portável entre máquinas — substitui hooks hand-rolled no `~/.claude/settings.json`. Rode `/guardrails:setup` uma vez por máquina. |
| `fallow` | `/fallow` | Roda o Fallow (analisador estático JS/TS — código morto, duplicação, complexidade), classifica achados por tipo e confiança, audita o relatório pra pegar falsos-positivos (cron, rotas HTTP, imports dinâmicos) e entrega um relatório interativo onde você escolhe o que limpar. Limpeza com rede de segurança (preview + build/test). |
| `branches` ⚙️ | `/branches` · SessionStart | Relatório de branches paradas com prova: quantas, quais já estão contidas na base, e o que dá pra apagar. Antes de apagar, cria uma tag `archive/<branch>-<data>` como rede de resgate. Aviso silencioso no SessionStart quando não há branch parada. |
| `lixeiro` ⚙️ | `/faxina` · automático (SessionEnd + Stop) | Encerra os processos que a sessão abriu e esqueceu de pé — servidor de desenvolvimento, suíte em modo de observação, túnel. A parte automática colhe **só o que a sessão anotou ter aberto**; o comando `/faxina` é o irmão manual, que mostra **tudo** que está de pé, com ou sem procedência, e encerra apenas o que você marcar. |

### Apresentação visual

| Plugin | Trigger | O que faz |
|---|---|---|
| `visual` ⚙️ | `/visual` · `/andamento` · automático em planos/diagnósticos (PreToolUse em ExitPlanMode) | Transforma textão do CLI em views HTML dark-theme interativas, abertas no browser com **live sync** de volta pro Claude via daemon local. Modo auto renderiza planos (3+ itens), decisões (2+ opções) e diagnósticos (3+ problemas) sem precisar invocar. **Prosa é recusada pelo programa**: todo campo de texto passa por quatro checagens (≤140 caracteres por bullet, uma frase por bullet, sem conectivo de continuação abrindo, no máximo 6 bullets por bloco) e estourar aborta sem escrever a página. O corpo de cada problema **nasce dobrado** — o título fica visível, a consequência e a proposta abrem com um clique cujo rótulo é derivado do conteúdo, nunca uma etiqueta fixa. A segunda skill, `/andamento`, mostra no CLI, em árvore, onde está a implementação do plano atual. |
| `archify` | `/archify` | Diagramas de arquitetura, fluxo, sequência e ciclo de vida como HTML explorável com SVG: profundidade progressiva de leitura, lente semântica, preview de rota entre dois pontos, navegação por capítulos e export pra PNG/SVG/WebM. Aceita descrição em linguagem natural ou Mermaid colado. |
| `slides` | `/slides <arquivo.md> [tema]` | Outline em markdown → deck HTML single-file nível keynote. Sistema de temas (Slate default), linguagem de apresentação com tipografia grande, fidelidade estrita ao texto (nunca inventa frase) e output ao lado do `.md` de origem. |

### Setup de máquina

| Plugin | Trigger | O que faz |
|---|---|---|
| `bootstrap` ⚙️ | `/bootstrap:setup` · automático no SessionStart + PostToolUse | Prepara uma máquina nova: mantém em dia os marketplaces e plugins já instalados via hooks (nada novo é instalado sem a sua confirmação no `/bootstrap:setup`) **e** aplica a config global versionada (env, permissões, flags, `CLAUDE.md` global, output style, statusLine resolvido por máquina). Traz também o **Clean Style** (resultado na primeira linha, teto de prosa, prova colada sem teto) e um **verificador de conformidade** que compara a máquina viva contra o contrato versionado sem escrever nada. Rode `/bootstrap:setup` uma vez por máquina. Os defaults de permissão aprovam sozinhos o script de um plugin só quando ele é chamado pelo caminho literal do cache e não executa comando recebido; chamada montada com `$VAR` ou `$(…)` pede aprovação (rode `apply-config.sh` de novo depois de atualizar um plugin). |

---

## Como funciona

Cada plugin é uma pasta autocontida: o Claude Code lê o catálogo, copia a pasta do plugin para o cache da máquina e carrega as skills e os hooks que ela declara. Não há servidor nem etapa de compilação; o que roda são scripts Bash e Python (biblioteca padrão) que a própria pasta carrega.

### Hooks automáticos

12 plugins registram hooks que disparam sem slash command — 54 registros no total
(derivado neste run: `python3 scripts/hook_contract.py`; conferido no commit por
`python3 scripts/readme_counts_check.py`):

| Plugin | Eventos | Papel |
|---|---|---|
| `bootstrap` | SessionStart×2 · PostToolUse | Sync do que já está instalado, aviso do que o manifest tem de novo, e o aviso depois de um comando de plugin |
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

### Anatomia de um plugin

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

Alguns plugins têm mais pastas: `bootstrap` traz `config/` e `output-styles/`, `visual` traz `server/`, e `vision` é um servidor MCP (`.mcp.json` + `vision_mcp.py`).

O catálogo vive em `.claude-plugin/marketplace.json` na raiz — cada plugin tem uma entrada com `name`, `source`, `description`, `category`, `version` e `tags`.

### Código compartilhado entre plugins

Código realmente comum mora em `_shared/` na raiz e é **vendorado** pra dentro de cada consumidor via `scripts/sync-shared.sh` — copiado, **não importado em runtime**, porque o Claude Code isola cada plugin no cache. São 31 arquivos-fonte em `_shared/`, espalhados em 116 cópias em 46 pastas de destino: `resolve-plugin.sh` (acha a pasta de um plugin irmão) vive em 18 plugins; `hook-json.sh` (leitura do payload do hook sem depender de `jq`) e `regua_texto.py` (a régua que recusa prosa) em 12 cada; `collect_engine.py` (leitura de transcripts, resolução de project-root) em `handoff` e `project-skills`. `_shared/` é a fonte-da-verdade: edite lá e rode `scripts/sync-shared.sh` (o `--check` pega drift entre a fonte e as cópias).

---

## Desenvolvimento

Precisa de `git`, `bash` e Python 3 (o CI usa 3.12). `jq` e Node só são necessários para partes específicas (veja [Dependências externas](#dependências-externas)).

```bash
git clone https://github.com/pedroberaldo87/pedro-plugins.git ~/pedro-plugins
cd ~/pedro-plugins
```

O `bootstrap` detecta se o repo está clonado localmente e adapta:
- **Com repo:** pode fazer `snapshot` (estado da máquina → manifest, commit, push).
- **Sem repo:** só `apply` (manifest → máquina).

Para usar outro caminho: `export PEDRO_PLUGINS_REPO="/caminho/alternativo/pedro-plugins"`.

Para testar o catálogo local no Claude Code: `claude plugin marketplace add ./`, na raiz do clone.

### Testes e conferências

```bash
bash scripts/suite.sh                          # a esteira inteira, a mesma do CI
python3 scripts/readme_counts_check.py         # números e nomes dos README contra o repositório
python3 scripts/public_repo_check.py           # nenhum dado pessoal em arquivo rastreado
bash scripts/sync-shared.sh --check            # drift entre _shared/ e as cópias vendoradas
claude plugin validate .                       # valida o catálogo e os manifests
```

Suítes avulsas ficam ao lado do código: `python3 plugins/<nome>/lib/test_*.py` e `bash plugins/<nome>/hooks/test_*.sh`. Rode sempre `scripts/suite.sh`, nunca `scripts/run_suites.py` sem argumentos: sem globs ele roda zero suítes e sai verde.

O CI (`.github/workflows/portability.yml`) roda a esteira em Ubuntu, macOS e Windows a cada push em `main` e em todo pull request. O repositório também tem um portão de commit para quem trabalha dentro do Claude Code (`.claude/hooks/release-gate.sh`, ligado por `.claude/settings.json`).

### Publicar uma mudança

> ⚠️ **Editar skill/hook sem bumpar `version` no `plugin.json` = clientes nunca recebem a atualização.**

1. Edite o plugin em `plugins/<nome>/`.
2. **Bumpe `version`** com `python3 scripts/bump.py <nome>` (`--minor`, `--major` ou `--para X.Y.Z`): ele atualiza o `plugin.json`, espelha em `marketplace.json` e atualiza a tabela de versões do `docs/architecture.md`.
3. `claude plugin validate .` — pega frontmatter inválido (`author` como string, `: `/`<>` em valores) que silenciosamente bloqueia o install.
4. Commit + push.
5. Nos clientes: `/plugin marketplace update` + `claude plugin install <nome>@pedro-plugins` (instalar ≠ atualizar índice).

---

## Documentação do projeto

A pasta [`docs/`](docs/) descreve como o repositório funciona por dentro. Está em **português** e não tem versão em inglês. Por onde começar:

- [`architecture.md`](docs/architecture.md): a arquitetura, com a tabela de plugins e versões.
- [`constituicao.md`](docs/constituicao.md): as regras que os cobradores do repositório aplicam.
- [`blueprint.md`](docs/blueprint.md), [`solution-strategy.md`](docs/solution-strategy.md) e [`architecture-intent.md`](docs/architecture-intent.md): como o sistema funciona e a estratégia da solução.
- [`context.md`](docs/context.md), [`features.md`](docs/features.md), [`journeys.md`](docs/journeys.md), [`glossary.md`](docs/glossary.md) e [`constraints.md`](docs/constraints.md): contexto e escopo, funcionalidades, jornadas, glossário e restrições.
- [`jq-pontos-de-decisao.md`](docs/jq-pontos-de-decisao.md): onde a falta do `jq` calava um gate.

A pasta também traz os fluxos ponta a ponta, o mapa de onde cada dado mora, a durabilidade, as metas de qualidade e as armadilhas conhecidas. [`docs/fluxos/`](docs/fluxos/) tem diagramas em HTML. Cada plugin documenta o próprio comportamento no `SKILL.md` das suas skills (em português); só o `graphify-guard` tem um `README.md` próprio.

---

## Segurança

Para relatar uma vulnerabilidade, veja o [SECURITY.md](SECURITY.md) (em inglês). Em resumo: não abra uma issue pública com o detalhe.

---

## Contribuindo

Veja o [CONTRIBUTING.md](CONTRIBUTING.md) (em inglês). Em resumo: abra uma issue antes de uma mudança grande, e rode a esteira e o `claude plugin validate .` antes do pull request.

---

## Licença

[MIT](LICENSE) © 2026 Pedro Beraldo.

Plugins de terceiros mantêm a própria licença:
- `archify` — MIT, ver [`plugins/archify/skills/archify/LICENSE`](plugins/archify/skills/archify/LICENSE).
- `grill-me` — MIT © Matt Pocock, de [mattpocock/skills](https://github.com/mattpocock/skills); ver [`plugins/grill-me/LICENSE`](plugins/grill-me/LICENSE).
