---
generated: 2026-08-14
reviewed: 2026-08-14
project: pedro-plugins
authored-by: ex-post-rascunho
status: ready
approved:
scope: []
---

# Glossário

> Termos de domínio e vocabulário interno. Uma linha cada. Se um termo aparece nos
> outros documentos e não está aqui, o glossário está incompleto.

## Domínio
- **plugin** — pacote de comportamento do Claude Code: skills, hooks e motores, instalável pelo marketplace.
- **skill** — instrução em Markdown que o agente carrega ao ser invocada (`/nome`).
- **hook** — script disparado por evento do Claude Code (commit, começo de sessão, fim de turno); aqui é sempre fail-open.
- **marketplace** — o repositório git catalogado em `marketplace.json`, de onde os clientes instalam.

## Interno (inventado pela equipe)
- **esteira** — a bateria completa de suítes do repositório · `scripts/suite.sh`.
- **portão / release-gate** — o hook de commit que barra release fora do padrão · `.claude/hooks/release-gate.sh` (a contagem de checks sai de `grep -cE '^# [A-Z0-9]+ · '` no próprio arquivo).
- **motor** — o programa que executa um plano sozinho, despachando agentes em ondas · `plugins/project-skills/skills/sprint/references/motor.js` · não confundir com **motor de skill**.
- **motor de skill** — a mecânica em Python que uma skill chama em vez de fazer por prosa · `lib/*.py` de cada plugin.
- **bump** — subir a versão no `plugin.json` (espelhada no catálogo); é o que faz o cliente receber a mudança.
- **manifest** — a lista de marketplaces e plugins que o bootstrap replica numa máquina nova · `bootstrap/config/manifest.json`.
- **ata** — o registro da sessão com os blocos de direcionamento do dono · `.claude/ata/`.
- **journal / ledger** — os achados datados da mineração e o registro do que a doc cobriu · `.claude/.project-doc/`.
- **handoff** — o documento que preserva a sessão para a próxima retomar do mesmo ponto · `/handoff`.
- **fail-open** — em falha, o hook libera em vez de travar; a degradação é em voz alta.
- **prova** — a saída crua, `arquivo:linha` ou sha que sustenta um tique, um veredito ou uma página.
- **casca** — a parte da skill que roda antes de armar o motor: pré-checagens, sinal, reserva.
- **onda / bloco** — uma rodada de despacho do motor, e o lote de passos que ela carrega.
- **régua** — os documentos que valem para julgar a obra (lei + acordo), carregados por `/doc-load`.
- **tique (tick)** — marcar um passo do plano como feito, sempre com prova · `plan_state.py tick`.
- **pronto** — o critério de aceitação escrito de um passo: como se prova que terminou.
- **vendoring** — copiar `_shared/` para dentro de cada plugin consumidor; a fonte é uma, as cópias viajam · `sync-shared.sh`.
- **green-cache** — a prova gravada de esteira verde que o portão reaproveita para não medir duas vezes.
- **sentinel** — arquivo-marca em disco que registra um estado entre eventos de hook.
- **lar fingido** — HOME falso montado por suíte para o teste não tocar a máquina real.
- **doc minerada** — a documentação extraída do código pelo `/doc`; vale como mapa, nunca como régua.
- **doc autoral** — a que só o humano pode responder (metas, restrições, lei); vale como régua.
- **2op** — segunda opinião: outra cabeça de modelo revisa sem receber a conclusão de quem pediu.
- **organismo** — repositório raiz com módulos dentro; a lei nasce na raiz e o módulo herda.
- **assintótico** — domínio sem estado perfeito alcançável (raspador, classificador, "achar todos os defeitos"); ali a parada é por severidade e retorno decrescente, nunca por zero.
- **convergente** — domínio com estado-alvo binário alcançável; ali o laço vai até atingir.
- **drill-down** — tudo nasce fechado e quem desce ao detalhe é o dono, perguntando; vale para página, relatório e resposta.
- **limite aceito** — desacordo entre a régua e a obra que o dono decidiu não consertar, com motivo e condição de revogação escritos.
- **medidor honesto** — o que diz "não medi" quando não conseguiu medir; o oposto é o que "pode mentir verde".
- **isenção declarada** — "não havia o que medir", que é diferente de "não consegui medir"; confundir os dois vira ruído e ensina a desligar o guarda.
- **doc derivada** — a que um programa produz a partir das outras (o índice, os ponteiros, o histórico); ninguém a escreve à mão.
- **sonda** — a checagem barata que dispara antes do trabalho caro.
- **barreira** — ponto onde seguir sem olhar custa refazer; não é parada de cortesia.
- **veto** — a palavra do dono que derruba algo já aprovado, gravada no caderno de vetos.
- **lente** — o eixo por onde uma revisão olha; umas são medidas por programa, outras lidas por agente.
- **sidecar** — o arquivo de aprovação que acompanha um artefato (o protótipo, por exemplo), sem ser o artefato.
- **conselheiro** — o modelo de fora que pondera com as decisões já travadas no pedido.
- **esteira de regressão (regression gate)** — a esteira que roda de novo depois de CADA conserto, para pegar o que o conserto quebrou.
- **sinal (de andamento)** — a batida de coração em disco, renovada a cada instante, que diz que uma corrida está viva.
- **reserva (de arquivos)** — a anotação dos arquivos que uma corrida vai mexer; outra que queira os mesmos é recusada enquanto ela viver.
- **vigia** — a peça que mede se o trabalho avança e derruba só o que travou de verdade; nunca corta por relógio.
- **ex-post** — inferir o documento do que já foi construído, com prova por artigo; o dono só referenda, nunca responde do zero.
- **juiz cego** — o que julga uma entrega sem receber a conclusão de quem a construiu; não confundir com o juiz de clareza, que lê páginas.
- **fio morto** — módulo com suíte verde que nenhum caminho executável alcança.
- **god node** — nó do grafo de conhecimento com grau altíssimo; os 60 do mapa são teto de exibição, não medição.

## Falsos amigos — significam aqui algo diferente do usual
- **CI** — aqui: uma única esteira de portabilidade em 3 sistemas · no mercado: pipeline de build/deploy.
- **bloqueio** — aqui: o que impede outra coisa de rodar (uso estrito) · no mercado: qualquer pendência.
- **verde** — aqui: medido verde por programa, com prova · no mercado: "parece ok".
