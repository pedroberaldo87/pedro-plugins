---
generated: 2026-08-14
reviewed: 2026-08-14
project: pedro-plugins
authored-by: ex-post-rascunho
status: draft
approved:
scope: []
---

# Estratégia da solução

> As poucas decisões que explicam o formato de tudo. Uma página — se passar disso,
> tem detalhe aqui que pertence a um registro de decisão.

## As decisões estruturantes

### Regra vira programa que morde; prosa é exceção declarada
- **Por quê:** regra em prosa não pega — 368 ocorrências de nome próprio entraram enquanto a regra era um parágrafo. A medição de 2026-08-02 fecha a tese: mesmo autor, mesma sessão, o campo com teto cobrado por programa chegou a 137 caracteres em 171 amostras; o texto sem teto chegou a 2182.
- **Descartamos:** documentação como único mecanismo de disciplina.
- **A exceção, e ela é escolha sua:** a régua de texto do /visual ficou em prosa por decisão de 2026-07-30, contra a recomendação de recorte mecânico. Manter em prosa é decisão com data e gatilho de reversão escritos — se a prosa não pegar na próxima página, o recorte volta à mesa.
- **Serve ao artigo:** Art. 4 · Rigor (constituicao.md).
- **Detalhe em:** [ESCRITO: .claude/CLAUDE.md · Custom Rules; medição em findings 2026-08-02]

### Um marketplace monorepo, todos os plugins dentro
- **Por quê:** um `marketplace add` replica a casa inteira numa máquina nova; plugin avulso multiplicaria instalação e drift.
- **Descartamos:** um repositório por plugin.
- **Serve ao artigo:** [PENDENTE: "replicabilidade" — meta nova ou artigo existente com outro nome?]
- **Detalhe em:** [INFERIDO DO CÓDIGO: um repo, e o catálogo marketplace.json como fonte da contagem; o princípio "1 install replica tudo" foi dito a propósito do guardrails, journal 2026-06-20]

### Distribuição por git, com o catálogo como fonte da verdade
- **Por quê:** `marketplace.json` decide o que existe para o cliente; `ls plugins/` não.
- **Descartamos:** registry de pacotes (npm/pip).
- **Serve à restrição:** zero infraestrutura paga (constraints.md).
- **Detalhe em:** [ESCRITO: .claude/CLAUDE.md · Visão Geral]

### Código compartilhado nasce em `_shared/` e viaja vendorado
- **Por quê:** plugin instalado tem que ser autocontido; import em runtime quebraria fora desta máquina.
- **Descartamos:** biblioteca comum importada entre plugins.
- **Serve ao artigo:** Art. 3 · Portabilidade (constituicao.md).
- **Detalhe em:** [ESCRITO: patterns.md · vendoring; sync-shared.sh --check acusa drift]

### Comportamento em três camadas: skill julga, hook cobra, motor executa
- **Por quê:** o julgamento fica no Markdown (barato de mudar), a cobrança no evento (impossível de esquecer), a mecânica no Python (testável).
- **Descartamos:** skills gigantes que fazem tudo por prosa.
- **Serve ao artigo:** Art. 8 · Executabilidade por um agente (constituicao.md).
- **Detalhe em:** [INFERIDO DO CÓDIGO: os plugins com hooks/hooks.json + motores em lib/ com suíte própria — architecture.md]

### O gate local e o CI rodam o MESMO bloco
- **Por quê:** veredito que muda entre a máquina e o CI é veredito em que ninguém confia; a seleção de suítes tem uma casa só (`scripts/suite.sh`).
- **Descartamos:** pipelines separados por ambiente.
- **Serve ao artigo:** [PENDENTE: "CI verde com causa" — meta nova ou o Art. 4 · Rigor com outro nome?]
- **Detalhe em:** [ESCRITO: .claude/CLAUDE.md · Quick Commands; portability.yml chama a mesma casa]

### A disputa é equipe visível; a execução autônoma é motor com sinal
- **Por quê:** julgamento com iteração (gauntlet) roda como equipe visível na conversa, com trava dupla — o dono vê, dirige e veta; execução de plano (sprint) roda como motor com sinal de andamento visível.
- **Descartamos:** caixa preta na disputa — e também generalizar equipe visível ao sprint, que a obra desmente.
- **Serve ao artigo:** Art. 2 · Aplicabilidade (constituicao.md).
- **Detalhe em:** [DITO POR VOCÊ: 8 datas entre 08-04 e 08-13 — "é importante eu poder acompanhar a dinamica dos agentes aqui no CLI para poder acompanhar o que está sendo feito e steer/direcionar/parar o trabalho enquanto ele acontece (em vez da caixa preta que seria um workflow)"]

### Toda decisão chega como página com prova
- **Por quê:** decisão pedida no terminal enterra o insumo; a página carrega o artefato e a saída crua, e o construtor recusa decisão sem prova.
- **Descartamos:** pedir decisão por texto corrido no chat.
- **Serve à meta:** escaneabilidade (quality-goals.md) — o construtor exige prova por PÁGINA; a prova por opção é regra de julgamento da skill, não guarda de programa.
- **Detalhe em:** [DITO POR VOCÊ: 2026-06-20 — "Eu estou esperando você me mostrar o artefato exemplo do relatório final que eu te pedi"; 2026-07-11 — "Depois disso você me deixou confuso, eu não sei qual que vale, não sei que decisão que eu tomo"]

### Decisão de concepção passa por segunda cabeça, e o parecer vem traduzido
- **Por quê:** quem concebe não enxerga o próprio ponto cego; ao menos um conselheiro é adversarial, o advogado do diabo.
- **Descartamos:** repassar o parecer cru ao dono — quem convocou traduz, decide e entrega a solução pronta.
- **Serve ao artigo:** Art. 7 · Clareza da instrução (constituicao.md).
- **Detalhe em:** [DITO POR VOCÊ: 2026-08-06 — "talvez um deles seja adversarial para ser o advogado do diabo"; 2026-08-07 — "não dá para entender o que ele falou. Então, explica para mim o que ele quis dizer"]

### Informação que muda mora num resolvedor único, nunca amarrada por nome
- **Por quê:** nome e quantidade escritos à mão são armadilha para o futuro (o retrato da dívida sai de `python3 scripts/desacoplamento_check.py`); o que muda se pergunta a um lugar só, de forma recursiva.
- **Descartamos:** skill que lista outras skills pelo nome, contagem escrita à mão, caminho cravado.
- **Alcance:** vale para este marketplace **e** para os projetos que a metodologia produz.
- **Serve ao artigo:** Art. 9 · Desacoplamento (constituicao.md).
- **Detalhe em:** [DITO POR VOCÊ: 2026-08-07 — "eu nunca mais quero ter que te dizer isso"; 2026-08-13 — "isso devia estar em um lugar só, estruturado, canônico"]

### Antes de abrir um laço, classifique o domínio
- **Por quê:** domínio convergente tem estado-alvo alcançável e vai até atingir; domínio assintótico (raspador, classificador, "achar todos os defeitos") não tem perfeito, e ali a parada é por severidade e retorno decrescente.
- **Descartamos:** aplicar o critério de um no outro — em domínio convergente, parar por retorno decrescente é desistir.
- **Serve ao artigo:** Art. 4 · Rigor (constituicao.md).
- **Detalhe em:** [ESCRITO: briefing do laço de revisão — "o erro-raiz desta sessão: tratar um problema assintótico com critério convergente"]

### O conserto mora na fonte do comportamento, nunca no sintoma
- **Por quê:** o defeito que nasce de uma skill se corrige na skill, com bump de versão; remendar no projeto onde o sintoma apareceu faz o defeito renascer intacto no próximo projeto.
- **Descartamos:** esconder o sintoma, e hardcodar em doc de projeto o que é comportamento de skill.
- **Serve ao artigo:** Art. 2 · Aplicabilidade (constituicao.md).
- **Detalhe em:** [DITO POR VOCÊ: 2026-08-08 — "para de fazer remendo"; 2026-08-10 — "você escondeu a barra mas não corrigiu a causa"]

### Etapa condicional vira etapa incondicional barata
- **Por quê:** passo que só roda "quando precisa" é passo que ninguém dispara — o gatilho depende de alguém perceber a condição, e o estado normal de um sistema sem gatilho parece igual a "tudo aprovado".
- **Descartamos:** condição avaliada por julgamento na hora.
- **Serve ao artigo:** Art. 4 · Rigor (constituicao.md).
- **Detalhe em:** [ESCRITO: spec do esquema — "etapa que só roda 'quando precisa' é etapa que ninguém dispara"]

### Quem diagnostica propõe; aplicar depende do raio de impacto
- **Por quê:** a skill que investiga não sai consertando o que achou — um juiz independente mede o raio de impacto: baixo age na hora, médio ou maior vira página de decisão.
- **Descartamos:** conserto automático de achado de diagnóstico.
- **Serve ao artigo:** Art. 2 · Aplicabilidade (constituicao.md).
- **Detalhe em:** [DITO POR VOCÊ: 2026-08-08 — "não é para a skill sair implementando esses consertos. isso é constituição da skill"]

### O modelo do papel se escolhe pelo custo do retrabalho, não pelo do token
- **Por quê:** onde o humano está fora do laço, o executor é o modelo mais capaz e só o esforço varia por etapa; execução barata custa mais em retrabalho do que economiza.
- **Descartamos:** modelo barato como executor dos motores autônomos.
- **Onde o barato entra:** papel de exploração, em paralelo, onde o erro aparece na hora.
- **Serve ao artigo:** Art. 4 · Rigor (constituicao.md).
- **Detalhe em:** [DITO POR VOCÊ: 2026-07-27 — "não usaremos mais o sonnet para implementar"; contrato em `_shared/r8-tiers.md`]

### Duas máquinas que não se misturam: a revisão é assintótica, o gate é absolutista
- **Por quê:** julgamento de severidade variável (revisão de código, aderência ao escopo) para por retornos decrescentes; verificação binária (tipo, lint, teste de integração) só fecha em 100% — **inclusive erro que já estava lá antes**.
- **Descartamos:** loop até zero no lado assintótico, e qualquer escopo no lado absolutista.
- **O motivo da parada NÃO é economia:** é retorno decrescente e risco de regressão auto-infligida. Token, tempo e turno nunca justificam parar.
- **O critério de parada não é contagem:** teto por número de rodadas é proibido — mede-se a produtividade da rodada e um juiz isento decide seguir ou parar.
- **Serve ao artigo:** Art. 4 · Rigor (constituicao.md).
- **Detalhe em:** [DITO POR VOCÊ: 2026-06-21 — "é como se a skill QA tivesse DUAS FASES. uma fase assintótica e uma fase que é um gate" e "o critério é absolutista. só vai passar quando estiver 100%, incluindo erros pré-existentes. tipo tá errado, tá errado = tem que corrigir e fim"]
