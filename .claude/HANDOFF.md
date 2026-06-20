# Session Handoff — PRD
Date: 2026-06-20 17:42
Project: /Users/pedroberaldo/PROGRAMACAO/PEDRO/pedro-plugins
Session: d2b3016f-25aa-4f66-96fb-e82a957f669a
LOG (ata verbatim): /Users/pedroberaldo/PROGRAMACAO/PEDRO/pedro-plugins/.claude/ata/LOG-d2b3016f-25aa-4f66-96fb-e82a957f669a.md

## Resumo
Sessão **concluída**. Retomou a frente **qa-loop** (refinamentos R1–R7 estavam desenhados mas não implementados) e entregou tudo: (1) **v1.1** — reescreveu o motor de "6 lentes voltagent" para um **Workflow determinístico 2-Opus + Sonnet** (commit `2a16391`); (2) limpou os plugins legados (`qa`/`rev6`/`iterate`) e o `bootstrap-third-party` que não existem mais; (3) **v1.2** — transformou o relatório humano num **gerador de actionables** (4 categorias + seleção live + gráfico de severidade), reusando o `/visual` (commit `727362f`). Ambos pushados na branch `feat/guardrails-plugin`, instalados e carregados nesta máquina. **Nada pendente** — só o merge na `main` (opcional) sobrou.

## Contexto e Propósito
A sessão abriu retomando o `HANDOFF.md` anterior (sessão `1203e8d2`): o `/qa-loop` v1 estava no disco mas rodava o motor antigo de **6 lentes voltagent** (sub-agentes), e os refinamentos do grill (R1–R7) estavam aprovados no mérito mas não implementados. O Pedro entrou com a pergunta que destravou tudo: **"como o qa-loop executa pelos Sonnets? Serão sub-agentes?"** [d1] — e logo depois **"quero saber do plano, como vai ficar"** [d2]. Isso expôs que o R1 antigo definia os papéis só por *modelo* (opus/sonnet), nunca por *mecânica de spawn* — o buraco real.

## Discussões e Decisões

- **Mecânica do motor = um Workflow (a decisão-chave) [d1][d2][a1].** O Pedro perguntou se os Sonnets seriam sub-agentes [d1]. CONFIRMADO lendo o plano + SKILL.md: o plano só cravava os papéis por modelo, não como o Sonnet é invocado; a v1 usava sub-agentes voltagent. Apresentei 3 topologias (sub-agente Task / Agent Team / Workflow) via AskUserQuestion [a1]. O Pedro bateu o martelo (notes + "tudo é um workflow? Sim"): **o motor inteiro — Review + Plan + Exec — roda como UM Workflow determinístico**, os Sonnets ficam dentro do script (não Task ad-hoc). Resolve a regra dele (nada de sub-agente solto, que o guard `PreToolUse(Agent)` vigia) e o gate/churn/parada viram código JS, não "o Opus lembrar de aplicar".
- **Concessão honesta — casca interativa fora do Workflow.** O Workflow roda em background e não faz `AskUserQuestion` no meio. Logo os 2 toques humanos (classificar domínio 1× se ambíguo; nota 0-10 no fim) ficam na casca da skill.
- **Plano final v1.1 [p1][p2] + "retomar" [d3].** Escrevi o plano (motor Workflow + R2–R7), o Pedro disse "retomar" [d3] e aprovou via ExitPlanMode. (p1→p2 foi a reescrita após o visual gate exigir o HTML do plano.)
- **E2E primeiro, antes de commitar [a2].** Perguntei como seguir; o Pedro escolheu **rodar o E2E do motor antes do commit** [a2]. Rodei um Workflow real (fixture `slugify`) — confirmou que o Planejador adversarial REJEITA um falso accepted-limit e REBAIXA picuinha pra P2.
- **Bug de instalação na máquina [d8][d9][d10][d11][d12][g1].** Depois do commit, o `/qa-loop` não aparecia e os legados continuavam. O Pedro cobrou: "ta com que nome? /qa ou /qa-loop?" [d8], "não deu certo, onde você ta commitando?" [d9], "skills legados ainda lá" [d10], "confirma se carregado" [d11] "e se limpou" [d12]. Diagnóstico CONFIRMADO e resolvido [g1]: `/plugin` (update) + `/reload` NÃO instalam — só `install`/`uninstall`; e as legadas tinham DUAS fontes (plugin do marketplace **+** skills soltas em `~/.claude/skills/`).
- **Limpar o bootstrap-third-party [d13].** "esse bootstrap third party não existe mais" — foi renomeado pra `bootstrap`. Instalei o `bootstrap` novo + desinstalei o velho + limpei o cache.
- **Relatório vira gerador de actionables [d14].** O Pedro pediu discriminar os alertas em 4 categorias (Importantes-recomendação / Sugestões / Limitações / Extras) + um botão live pra selecionar → gerar novo plano, "como a interatividade do /visual" [d14].
- **Identidade visual: revertida [a3][d15][d16].** Recomendei "identidade própria" via /frontend-design [a3]; o Pedro questionou o porquê [d15] e decidiu **reusar o /visual** ("já temos premissas e referências maduras… você pode usar a skill /visual como parceira, não?") [d16]. ACOLHIDO — e melhor: dá pra reusar SEM modificar o /visual (feedback-item relabelável + daemon já fazem tudo). Plano do relatório [p3][p4] aprovado.
- **Gráfico [d17][d18].** Pediu o gráfico mostrar a severidade por rodada [d17]; primeiro fiz 2 gráficos lado a lado, ele disse **"coloca os dois"** [d18] e depois (na imagem) pediu manter SÓ o de barras empilhadas (2 apertariam com 4-5 rodadas) + polir.
- **Ship [d19].** "tá lindo. commit push bump bora bora" — commit cirúrgico v1.2.0.
- **Verificação de update [d20].** "teoricamente atualizei, veja se deu" — CONFIRMADO: cache em 1.2.0 (autoUpdate pegou o bump).
- `[d4][d5]` = ajustes de `/effort` (config), sem impacto no trabalho. `[d6]` "ta fazendo?" = pedido de status no meio do E2E. `[d7]` "commit push" = ship da v1.1.

## O Que Foi Feito
Implementação concluída — os planos [p1–p4] viraram código e commits (`likely_executed: true`). NÃO há nada pra reimplementar.

**qa-loop v1.1 — motor Workflow (commit `2a16391`):**
- `plugins/qa-loop/skills/qa-loop/SKILL.md` reescrito: motor = `Workflow` (Opus Revisor independente → Opus Planejador adversarial árbitro único → Sonnet Executor; gate de regressão, gate de severidade, churn e parada como lógica do script; schemas `FINDINGS`/`PLAN`/`EXEC_RESULT`). Casca (domínio + nota) explicitamente fora do Workflow. R2 (rubrica 3 faixas + árbitro único), R3 (config 3 camadas), R4 (drift restaura+sinaliza), R5 (vale-a-pena = retornos+regressão, nunca tokens), R6 (accepted-limit proposto), R7 (relatório humano ≠ journal agêntico). Zero menção a "6 lentes"/voltagent/subagent_type.
- `plugin.json` 1.0.0→1.1.0; `marketplace.json` (tag voltagent→workflow, alinhou raiox 0.2.0 e visual 1.2.0); `architecture.md`; `EXAMPLE-REPORT.md` re-gerado; `EXAMPLE-JOURNAL.md` novo (3 camadas).
- **E2E do motor CONFIRMADO** com Workflow real (fixture `/tmp/qa-loop-e2e2/` slugify): Planejador rejeitou o falso-limite (acento ancorado no plano) + rebaixou picuinha; regression gate verde; `slugify("Ação")` "ao"→"acao", suíte 4→9.

**Limpeza de plugins (via CLI):**
- `claude plugin install qa-loop@pedro-plugins` + `uninstall qa@/rev6@` + removeu `qa`/`rev6` do cache `~/.claude/plugins/cache/pedro-plugins/`.
- Moveu `~/.claude/skills/{qa,rev6,iterate}` (skills globais soltas, fonte paralela) pra `/tmp/claude-legacy-skills-backup/`.
- `install bootstrap@` + `uninstall bootstrap-third-party@` + limpou o cache do bootstrap-third-party.

**qa-loop v1.2 — relatório gerador de actionables (commit `727362f`):**
- `SKILL.md` seção R7-A reescrita: o relatório INVOCA a skill `/visual` como parceira; 4 categorias como seções de `feedback-item` com labels "✓ Vira ação / ✏️ Ação c/ ajuste / ✗ Descartar"; seleção live → o Pedro marca, diz "ok", a casca lê o `latest.json` do daemon do /visual e monta o plano só dos marcados; gráfico único de findings por severidade.
- `EXAMPLE-REPORT.html` novo (HTML real, verificado E2E via Playwright: render + interação + live-sync + gráfico polido); `EXAMPLE-REPORT.md` virou ponteiro.
- bump 1.1.0→1.2.0 (plugin.json + marketplace + architecture). Commit cirúrgico com `git stash` pra isolar a frente `bootstrap` do marketplace.
- CONFIRMADO nesta máquina: cache em 1.2.0 (autoUpdate pegou o bump no reload) [d20].

## Em Andamento
Nada pendente na frente qa-loop. Tudo implementado, verificado, commitado e pushado (`feat/guardrails-plugin`).

## Próximos Passos

### 1. Merge na `main` (qa-loop v1.1 + v1.2)
- **Ação:** mergear os commits `2a16391` + `727362f` da branch `feat/guardrails-plugin` na `main` e push (como foi feito com o guardrails — fast-forward ou merge direto).
- **Critério de pronto:** `git log origin/main` mostra os 2 commits do qa-loop; outra máquina que puxe via git pega a v1.2.0.
- **Problema:** o trabalho está só na branch; o marketplace replica entre máquinas pelo que está na `main`. Esta máquina já funciona (lê o working tree local), mas outra máquina não pega.
- **Arquivos prováveis:** nenhum (operação git).
- **Decisão em aberto:** merge direto vs PR — o Pedro fez merge direto no guardrails; provável mesmo padrão. **Cuidado:** a branch tem OUTRAS frentes não-commitadas no working tree (não afetam o merge dos commits já feitos).

### 2. Limpar o resíduo da v1.1.0 no cache (trivial)
Sobrou a pasta `~/.claude/plugins/cache/pedro-plugins/qa-loop/1.1.0/` (o installed aponta pra 1.2.0, não atrapalha). Mover/remover quando quiser.

### 3. Não commitar as frentes paralelas junto com o qa-loop (trivial)
O working tree tem 3 frentes alheias não-commitadas, deixadas intactas — **bootstrap** (rename `bootstrap-third-party`→`bootstrap`: `plugins/bootstrap/` novo + delete do antigo + marketplace), **guardrails** (`M plugins/guardrails/*`, v1.1 em andamento), **graphify-out** (regeneração do grafo). Cada uma é commit próprio quando o Pedro decidir; não misturar com o qa-loop.

## Findings & Gotchas
- **`/plugin` (marketplace update) + `/reload-plugins` NÃO instalam nem desinstalam plugin** — só `claude plugin install`/`uninstall` mexem no que carrega. Por isso o /qa-loop não aparecia e os legados ficavam, mesmo após o commit. [d8][d9]
- **Skills legadas tinham DUAS fontes paralelas:** o plugin do marketplace (`installed_plugins.json` + cache) **E** skills globais soltas em `~/.claude/skills/qa|rev6|iterate` (instaladas direto, fora do marketplace). Desinstalar o plugin não toca as soltas — tem que mover/apagar os dois. [d10]
- **`autoUpdate` do marketplace source-directory atualiza um plugin JÁ instalado quando a versão sobe** (1.1.0→1.2.0 pegou no reload), mas **não instala um plugin nunca-instalado** — esse precisa de `install` explícito (foi o caso do qa-loop na 1ª vez). [d20]
- **O marketplace `pedro-plugins` é `source: directory` apontando pro working tree local** (`/Users/pedroberaldo/PROGRAMACAO/PEDRO/pedro-plugins`, `installLocation` = o próprio path, `autoUpdate: true`). Ele LÊ os arquivos locais — não git, não branch, não main. Por isso esta máquina já enxerga a v1.2.0 mesmo sem merge na main; mas OUTRA máquina (que clona via git) só pega o que está na `main`. [d9]
- **`rm -rf` é bloqueado pela permissão** tanto em `~/.claude/` quanto no repo (a mesma trava que já salvou o Pedro de apagar algo errado). Usar `mv` pra `/tmp` (reversível) — foi o que destravou a limpeza das skills legadas.
- **"Hooks (N)" / cache não auto-refresca** continua valendo (gotcha do repo): bump obrigatório, e o cache local precisa de sync/reinstall após mudança.
- **O uninstall NÃO limpa a pasta do cache** — vira "slash fantasma" (a skill some de installed mas o dir do cache sobra, podendo confundir). Tem que mover/apagar o dir manualmente. [d10][g1]
- **Cuidado com o `marketplace.json` em commits cirúrgicos:** ele é o arquivo de convergência de TODAS as frentes + é reformatado por um linter (single-line → multi-line). Pra commitar SÓ o qa-loop, usei `git stash push -- .claude-plugin/marketplace.json` pra guardar a frente bootstrap, bumpei o qa-loop, commitei, e `git stash pop` pra devolver. Comparar o delta semântico (name+version) via python, não o diff textual.
- **Reusar o `/visual` sem modificá-lo é possível pro caso "categorias selecionáveis → gera plano":** os `feedback-item` (valores internos `keep`/`change`/`remove` fixos, labels relabeláveis) + o daemon `visual_server.mjs` (genérico, `~/.claude/visual-state/latest.json`) já fazem a seleção + live-sync. Zero blast radius no god-node. [d16]
- **Playwright bloqueia `file://`** — pra screenshot de HTML local, subir `python3 -m http.server` e navegar via `http://127.0.0.1`. O único console error no relatório era `favicon.ico 404` (benigno).

## Detalhes Técnicos
- **Motor qa-loop (a implementar pela skill em runtime):** a skill dispara a tool `Workflow` com um script cujo `meta.phases` declara Review/Plan/Exec, e o corpo é o loop `while (!cleanRound && r < maxRounds && !churnEscalated)`. Cada papel = `agent(prompt, {model:'opus'|'sonnet', schema})`. Args vindos da casca: target, planPath, severityFloor, maxRounds, domain, safetyLayer, acceptedLimits, invariants, learnings. Esqueleto de referência completo está na própria `SKILL.md`.
- **Relatório (R7-A):** invoca a skill `/visual`; 4 `<section>` (Importantes/Sugestões/Limitações/Extras), cada achado um `feedback-item`; gráfico = barras empilhadas P0/P1/P2/P3 por rodada (SVG, gradientes + topo arredondado + animação de entrada) com a linha de severidade real (P0+P1) sobreposta. Mapeamento: plan-flaw→Importantes, drift+refators→Sugestões, accepted-limits+churn→Limitações, P2/P3→Extras.
- **Commits:** `2a16391` (v1.1) e `727362f` (v1.2) na branch `feat/guardrails-plugin` (origin atualizado). `main` está em `94514ee` (guardrails) — NÃO tem o qa-loop ainda.
- **Fixtures de teste:** `/tmp/qa-loop-e2e/` (regression gate, v1) e `/tmp/qa-loop-e2e2/` (motor-Workflow, slugify). Backups da limpeza em `/tmp/claude-legacy-skills-backup/`.
- **Plano-fonte do design (grill):** `/Users/pedroberaldo/.claude/plans/o-seguinte-a-zippy-taco.md`. Plano desta sessão: `/Users/pedroberaldo/.claude/plans/zazzy-giggling-lynx.md`.

## Contexto Extra
- **Estilo do Pedro:** quer pushback honesto e o "porquê" da recomendação (questionou "por que recomendou identidade própria?" [d15] e reverteu a decisão); valoriza reuso de premissas maduras sobre reinventar [d16]; "validar olhando" (print + análise da tela, não só DOM) — segui isso no Playwright; rm -rf é tabu (usar mv). Lê de baixo pra cima; plano sempre vira /visual antes do CLI (hook de gate).
- **Memória atualizada:** `qa-loop-status.md` reflete v1.2 + o motor Workflow + o relatório-actionables; `MEMORY.md` index idem.
- **Nada de secrets** foi tocado.
