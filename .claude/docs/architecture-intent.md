---
generated: 2026-08-14
reviewed: 2026-08-14
project: pedro-plugins
authored-by: ex-post-rascunho
status: approved
approved: 2026-08-16
scope: []
approved-sig: 1695528293
---

# Arquitetura pretendida

> O desenho acordado antes do código. Quando o código divergir daqui, um dos dois
> está errado — e a conversa começa por qual.

## As peças
- **Plugin** — a unidade instalável: skills, hooks e motores numa pasta, autocontida · **serve ao artigo:** [PENDENTE: "replicabilidade" — meta nova ou artigo existente com outro nome?] [INFERIDO DO CÓDIGO: a fonte da verdade da contagem é o marketplace.json, nunca o `ls plugins/`]
- **Skill** — o julgamento em Markdown que o agente carrega ao ser invocado · **serve ao artigo:** Art. 8 · Executabilidade por um agente (constituicao.md) [INFERIDO DO CÓDIGO: SKILL.md em todo plugin]
- **Hook** — a cobrança por evento, sempre fail-open · **serve ao artigo:** Art. 4 · Rigor (constituicao.md) [INFERIDO DO CÓDIGO: os plugins com hooks/hooks.json rastreado]
- **Motor** — o programa que executa uma missão sozinho, despachando agentes em ondas (o do sprint e o do qa-loop) · **serve ao artigo:** Art. 8 · Executabilidade por um agente (constituicao.md) [INFERIDO DO CÓDIGO: `references/motor.js` nas duas skills]
- **Motor de skill** — a mecânica em Python stdlib que a skill chama em vez de fazer por prosa · **serve ao artigo:** Art. 4 · Rigor (constituicao.md) [INFERIDO DO CÓDIGO: lib/*.py com suíte própria por plugin]
- **Fonte compartilhada (`_shared/`)** — o código que vale para vários plugins, vendorado em cópias · **serve ao artigo:** Art. 3 · Portabilidade (constituicao.md) [ESCRITO: patterns.md · vendoring]
- **Catálogo (`marketplace.json`)** — a fonte da verdade do que existe para quem instala · **serve ao artigo:** [PENDENTE: "replicabilidade" — meta nova ou artigo existente com outro nome?] [ESCRITO: CLAUDE.md · Visão Geral]
- **Portão de release** — o hook de commit que barra release fora do padrão (bump, espelho, vendoring, público) · **serve ao artigo:** Art. 4 · Rigor (constituicao.md) [INFERIDO DO CÓDIGO: .claude/hooks/release-gate.sh — a contagem de checks sai de `grep -cE '^# [A-Z0-9]+ · '` nele]
- **Esteira** — a seleção única de suítes que mede o repositório inteiro · **serve ao artigo:** [PENDENTE: "CI verde com causa" — meta nova ou o Art. 4 · Rigor com outro nome?] [ESCRITO: CLAUDE.md · Quick Commands, scripts/suite.sh]
- **CI de portabilidade** — a mesma esteira nos três sistemas, a cada push · **serve ao artigo:** Art. 3 · Portabilidade (constituicao.md) [ESCRITO: .github/workflows/portability.yml]
- **Vigia** — mede se o trabalho avança e derruba só o que travou de verdade; nunca corta por relógio · **serve ao artigo:** Art. 4 · Rigor [DITO POR VOCÊ: 2026-08-13 — "se a suíte está progredindo, tem que esperar"]
- **Juiz de clareza** — leitor externo que aprova a página antes de ela abrir, em dois eixos: repertório de programador experiente (define-se o contextual e o metafórico, nunca o trivial) e paciência de criança de cinco anos, este só para a forma da frase · **serve ao artigo:** Art. 7 · Clareza da instrução [DITO POR VOCÊ: 2026-08-06 e calibrado em 2026-08-09]
- **Bootstrap** — o replicador de máquina: marketplaces, plugins e terceiros pelo manifest · **serve ao artigo:** [PENDENTE: "replicabilidade" — meta nova ou artigo existente com outro nome?] [INFERIDO DO CÓDIGO: plugins/bootstrap/config/manifest.json]

## As fronteiras — quem pode chamar quem
- **Skill → motor de skill** — a skill julga e manda o programa medir; contagem nunca sai do olho do modelo. [INFERIDO DO CÓDIGO: skills chamam lib/*.py por resolve-plugin.sh]
- **Hook → cópia vendorada** — hook usa a cópia local do `_shared/`; nunca a fonte de outro plugin. [ESCRITO: patterns.md]
- **Portão → esteira** — o portão confere a prova gravada da esteira; quem mediu grava, quem barra confere. [INFERIDO DO CÓDIGO: green-cache no release-gate]
- **Plugin → plugin: por NOME, nunca por caminho** — alcançar o irmão pelo nome (com resolvedor) é o mecanismo oficial, e ele degrada no ponto de uso quando o irmão não está instalado. **PROIBIDO** é montar caminho para dentro de outro plugin ou importar código dele: quebra a instalação avulsa. O que é comum de verdade nasce em `_shared/`. [ESCRITO: régua de pergunta e patterns.md — quem usa o resolvedor sai de `grep -rl 'resolve-plugin.sh' plugins/ | cut -d/ -f2 | sort -u`]
- **PROIBIDO: escrever estado dentro do plugin** — o cache é reescrito a cada bump; estado mora em `~/.claude/`. [ESCRITO: CLAUDE.md · Gotchas]
- **PROIBIDO: depender de guarda alheio sem citar a regra dele** — presumir que a proteção do vizinho cobre o seu caso é o defeito; coexistir não é conflito. [INFERIDO DO CÓDIGO: commit de 2026-08-02 — uma skill afirmou por um mês uma proteção que não existia]
- **Execução → régua** — a doc canônica é premissa no planejamento e objeto de verificação no fluxo de aprovação; a prova do passo se confere contra ela. [DITO POR VOCÊ: 2026-08-08 — "na execução para ser usada como fio condutor e objeto inegociável de verificação"]
- **A fronteira do julgamento** — contagem, seleção e mecânica são do programa; qualidade e escopo são leitura do modelo. Trocar julgamento por limiar numérico é regressão. [DITO POR VOCÊ: 2026-06-20 — "não tem que cortar com base em limite de caracteres"]
- **PROIBIDO: construtor → juiz** — quem fez não julga o que fez, nem como saída quando não dá para lançar o outro agente; o juiz não recebe a conclusão de quem construiu. Foi essa saída silenciosa que produziu a falha. [ESCRITO: cinco documentos independentes — gauntlet, vistoria, autópsia e os dois pareceres]
- **PROIBIDO: agente manter estado legível à mão** — o mapa é derivado por programa dos julgamentos gravados; estado mantido por instrução é o arquivo que o contaminado carimba.
- **Na análise sobre volume, o programa aponta ONDE e o agente diz O QUE** — inverter põe um agente lendo milhões de linhas para achar o que um comando acha.

## Onde o estado mora
- **`~/.claude/andamento/`** — sinais de vida, reservas de arquivo e placar das corridas · **escreve:** casca e motor do sprint · **lê:** hooks de status e outras sessões
- **`~/.claude/visual-state/`** — estado das páginas e lições de clareza · **escreve:** daemon do visual e o construtor · **lê:** o agente quando o dono diz "ok"
- **`<projeto>/.claude/plans/`** — os planos ticáveis, um arquivo por plano · **escreve:** plan_state.py · **lê:** hooks de sessão, sprint, qa-loop
- **`<projeto>/.claude/docs/`** — a régua (lei + acordo) e o mapa minerado · **escreve:** /start (autoral) e /doc (minerado) · **lê:** doc-load e todo revisor · **um só documento vigente por assunto**; o texto substituído vai para o irmão `<nome>.historico.md` com data, contexto e a decisão que o mudou
- **`<projeto>/.claude/archify/`** — os diagramas, camada visual da doc · **escreve:** archify pelo doc curado (nunca pelo código cru) · **lê:** o humano e o agente
- **`<projeto>/.claude/ata/`** — as atas de sessão, com os blocos de direcionamento do dono · **escreve:** o hook de ata · **lê:** o ex-post e quem minera a voz do dono
- **`<projeto>/.claude/.project-doc/`** — o journal de achados e o ledger da doc minerada · **escreve:** /doc · **lê:** /doc-touch e o ex-post
- **`<projeto>/graphify-out/`** — o grafo de conhecimento do código · **escreve:** graphify · **lê:** quem analisa arquitetura

## Deixado de fora de propósito
- **Registry de pacotes** — a distribuição é git; publicar em npm/pip dobraria a manutenção sem ganho. [ESCRITO: solution-strategy.md]
- **Serviço hospedado / telemetria** — nada sai da máquina de quem instala; zero infra paga. [ESCRITO: constraints.md]
- **Import compartilhado em runtime** — vendoring existe justamente para o plugin viajar sozinho. [ESCRITO: patterns.md]

## Desenho

```
  dono ──escreve──▶ plugins/{skill,hook,lib}
                         │ vendoring (_shared/ → cópias)
                         ▼
      portão de release ──confere──▶ esteira (prova gravada)
                         │ commit+push
                         ▼
      GitHub ──▶ CI 3 OS ──▶ clientes (marketplace add / update)
                         ▼
      Claude Code (host) executa skill/hook/motor na máquina de cada um
```
