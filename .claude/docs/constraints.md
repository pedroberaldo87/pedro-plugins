---
generated: 2026-08-14
reviewed: 2026-08-14
project: pedro-plugins
authored-by: ex-post-rascunho
status: approved
approved: 2026-08-16
scope: []
approved-sig: 881584814
---

# Restrições

> O que não é negociável neste sistema. Serve para o leitor entender por que soluções
> óbvias foram descartadas — sem isso, todo recém-chegado propõe a mesma coisa de novo.

## Organizacionais
- **Um mantenedor só, sem plantão** — o dono escreve e o dono opera; nada pode exigir vigília humana. · **dura** · [INFERIDO DO CÓDIGO: git log com um autor]
- **Documentação canônica é pré-requisito de execução, não subproduto** — projeto sem régua não recebe plano nem código, e quando a doc existe, lê-la é obrigatório (o agente é bloqueado, não avisado). Não existe meia documentação. · **dura** · [DITO POR VOCÊ: 2026-07-26 — "qualquer projeto tem que ter documentação, isso é inegociável"; 2026-08-04 — "eu quero um bloqueio"]
- **O repositório é público e instalado por terceiros** — nome próprio, caminho de máquina, cliente e credencial nunca entram em arquivo rastreado. · **dura** · [ESCRITO: .claude/CLAUDE.md · Custom Rules, cobrado por scripts/public_repo_check.py]

## Técnicas
- **Python 3 stdlib only nos motores de skill** — quem instala não roda `pip install`; dependência externa quebraria a instalação silenciosamente. · **dura** · [INFERIDO DO CÓDIGO: nenhum requirements.txt no repo; patterns.md declara a convenção. A exceção declarada é o archify, que é Node e tem lockfile próprio rastreado]
- **O comando de hook roda sob shell POSIX, nos três sistemas** — não pode depender de bash (o Linux o executa sob `sh`); macOS, Linux e Windows Git-Bash rodam a mesma esteira no CI. · **dura** · [ESCRITO: portability.yml, matriz de 3 OS; test_paths_normalize.sh caça bashismo]
- **Hook é fail-open, e o motivo é comportamental** — travar commit por ferramenta ausente na máquina de quem instalou ensina a contornar, e contornar desliga o guarda inteiro. Degradar em voz alta, nunca em silêncio. · **dura** · [ESCRITO: inventário de medidores, 2026-08-14]
- **A suíte inteira roda a cada conserto** — escopar por julgamento de modelo é proibido; a única otimização permitida é determinística (a prova gravada da esteira). · **dura** · [DITO POR VOCÊ: veto ao escopo por julgamento no qa-loop]
- **Teste só vale depois de ter falhado** — teste que nasce verde não provou que mede; a mutação que o derruba entra junto com ele. · **dura** · [ESCRITO: relato da noite de 2026-08-14 — "o teste que nunca falhou não provou nada"]
- **Suíte monta o próprio repositório de mentira** — teste que escreve em arquivo de produção não tem restauração segura, porque outra sessão lê no meio. · **dura** · [ESCRITO: test_release_gate_prazo.sh:37 — o portão de produção foi de 565 para 1392 linhas, com 760 de lixo commitado]
- **Estado mutável fora do plugin** — o cache do plugin é reescrito a cada bump; estado vive em `~/.claude/`, e estado por sessão em `/tmp` chaveado por `session_id`. · **dura** · [ESCRITO: .claude/CLAUDE.md · Gotchas]
- **Sem build e sem lockfile nos plugins de comportamento** — o único passo de "compilação" é o vendoring de `_shared/`; a exceção declarada é o archify (Node, com `package-lock.json` rastreado). · **dura** · [ESCRITO: .claude/CLAUDE.md · Visão Geral]
- **Nenhum laço para por contagem de rodadas nem por relógio cego** — para por produtividade medida e julgada, ou por vigia que detecta travamento real; suíte que progride se espera. · **dura** · [DITO POR VOCÊ: 2026-08-13 e 2026-08-14 — "o critério não é número de rodadas, o critério é em produtividade" e "se a suíte está progredindo, tem que esperar"]
- **Qualidade nunca se troca por token, tempo ou turno — nem 1%** — decomposição que parece cara produz resultado mais limpo e auditável; custo não é critério de arquitetura. · **dura** · [DITO POR VOCÊ: 2026-08-08 — "nunca vamos sacrificar nem 1% dessa robustez a título de economizar token ou economizar tempo"]

## Econômicas
- **Zero infraestrutura paga** — distribuição por git, CI no plano grátis do GitHub Actions, nada hospedado. · **dura** · [INFERIDO DO CÓDIGO: nenhum compose/deploy/provider no repo]
- **Existe custo variável, e ele já doeu: geração de mídia** — provedor e teto de crédito são perguntados no início de TODA rodada que gera imagem ou vídeo, mesmo que já combinados numa rodada anterior do mesmo projeto. · **dura** · [DITO POR VOCÊ: 2026-08-11 — "derreti quase uma assinatura de um mês inteiro de um dia para o outro (…) tem que perguntar de novo"]

## Legais / regulatórias
- **Sem licença pública** — o repositório é público e publicado como está; nenhum direito de redistribuição foi concedido. · **dura** · [ESCRITO: README.md · Licença]
- **Registro de trabalho não é produto** — transcrição, plano em execução, handoff e saída de ferramenta ficam no disco e fora do git; foi por aí que nome de cliente vazou. · **dura** · [ESCRITO: .claude/CLAUDE.md · Custom Rules]
- **Nenhum dado de QUEM INSTALA sai da máquina dele** — a biblioteca opera local; segredo capturado do dono vai ao cofre local/iCloud, com scrubber na escrita. · **dura** · [ESCRITO: data-stores.md:65 (o cofre) e :592 (o scrubber na escrita)]

## Limites aceitos — o que a régua reprova e decidimos não consertar
> Desacordo entre a régua e a obra tem três destinos e só três: conserto, revogação da régua,
> ou limite aceito com motivo e condição de revogação escritos. Nunca silêncio.

A casa única dos limites é **.claude/limites-aceitos.md** — uma segunda lista aqui divergiria
dela (e já divergiu). A regra que vale: artefato antigo que se LÊ fica sob a régua nova do
próximo em diante; artefato antigo que ainda EXECUTA sai junto com a proibição, no mesmo lote.

## Soluções descartadas por causa das restrições acima
- **Publicar como pacote npm/pip** — descartada por **distribuição por git + zero infra**: o marketplace nativo do Claude Code instala direto do repositório.
- **Framework de teste (pytest e afins)** — descartada por **stdlib only**: as suítes são scripts `test_*.py`/`test_*.sh` que se bastam.
- **Biblioteca compartilhada importada em runtime** — descartada por **plugin autocontido**: `_shared/` é vendorado em cópias, com `sync-shared.sh` acusando drift.
