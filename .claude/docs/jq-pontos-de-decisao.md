---
generated: 2026-08-06
project: pedro-plugins
authored-by: human
status: ready
requisito: W-2
scope:
  - plugins/*/hooks/*.sh
  - scripts/test_sem_jq.sh
---

# Onde a falta do `jq` calava um gate

> Inventário de todo hook que lê o payload do evento, separado por **o que ele faz com o
> campo lido**. A pergunta não é "usa jq?" — é "sem `jq`, o hook deixa de FALAR ou deixa de
> DECIDIR?". Quem cobra a validade deste inventário é `scripts/test_sem_jq.sh`.

## O retrato medido

| medida | valor | comando |
| --- | --- | --- |
| hooks de produção — o que algum `hooks/hooks.json` registra, resolvido pelo medidor oficial | **43** | `python3 scripts/hook_contract.py --scripts \| grep -c .` |
| destes, os que leem o campo que DECIDE — classe B | **32** | ver classe B abaixo |
| destes, os que só formatam a saída / leem config — classe A | **5** | ver classe A abaixo |

Toda biblioteca de `_shared/` fica fora dessa conta: a cópia em `plugins/*/hooks/` é vendoring
do mesmo arquivo, não um hook a mais. É por isso que o comando deriva os nomes a excluir de
`_shared/` em vez de listá-los — vendorar uma biblioteca nova não obriga a re-medir o retrato.
O aviso de dependência é o caso mais visível: treze plugins o disparam na abertura da sessão,
porque quem instala um plugin sozinho também precisa saber que o gate dele ficou mudo — mas o
script existe UMA vez só, em `plugins/bootstrap/hooks/sessionstart-deps.sh`, e os outros doze
o acham por NOME de plugin (`resolve-plugin.sh bootstrap hooks/sessionstart-deps.sh`) em vez
de carregar cópia. A fonte é `_shared/sessionstart-deps.sh`, ele é classe A por natureza (o
`jq` só monta a mensagem), e um sentinel por sessão garante um aviso, não um por plugin.

O campo que DECIDE é um destes três: `tool_input.command`, `session_id`, `stop_hook_active`.

## O que era o issue #5, e o que ficou no lugar

Todo hook da classe B calava sozinho quando o `jq` faltava, por um de dois mecanismos: o bail
explícito (`command -v jq >/dev/null 2>&1 || exit 0`, ou o par `JQ="$(command -v jq)"` +
`[ -z "$JQ" ] && exit 0`) e o engolimento (a chamada mandava o erro para `/dev/null` e o campo
vazio derrubava o hook na linha seguinte). O efeito era o mesmo: numa máquina sem `jq` o hook
**saía 0 antes de olhar o payload**, e para o harness isso é indistinguível de "o gate rodou e
liberou" — sem mensagem, sem registro, sem segunda chance.

Hoje os 29 leem pelo `_shared/hook-json.sh`, vendorado em cada pasta de hooks: ele usa `jq`
quando existe e o `python3` (só stdlib) quando não, tanto para LER o campo quanto para EMITIR
a decisão (`hj_deny`, `hj_block`, `hj_ctx`, `hj_msg`). Sem `jq` **e** sem `python3` não há como
julgar — e aí o hook chama `hj_avisa`, que fala pelos dois canais em vez de sair calado. O
`context-guard-writer.sh` é a exceção de canal, não de regra: o stdout dele é a statusLine do
usuário, então o aviso dele sai só pelo stderr.

Isso é diferente da classe A, onde o `jq` monta a string de saída. Sem `jq` ali, o hook deixa
de imprimir um aviso — perde-se informação, não se perde julgamento. Fail-open continua aceitável.

Dentro da classe B há ainda dois graus:

- **B1 — decide BLOQUEAR** (emite `permissionDecision: "deny"`, `decision:"block"` ou `exit 2`):
  sem o fallback, uma ação que seria barrada passava direto. É o dano máximo.
- **B2 — decide REGISTRAR** (chaveia estado por `session_id`, anota, injeta contexto):
  sem o fallback, o estado da sessão nunca era escrito — e o gate B1 que depende desse estado
  numa rodada seguinte também não disparava. O dano é diferido, não ausente.

---

## Classe A — o `jq` só formata a saída (fail-open aceitável)

| classe | arquivo | linha(s) | o que o `jq` faz ali |
| --- | --- | --- | --- |
| A | `plugins/bootstrap/hooks/session-sync.sh` | 150 | interroga `known_marketplaces.json` (arquivo de config, não o payload do evento) |
| A | `plugins/bootstrap/hooks/sessionstart-deps.sh` | 19 | só confere se o `jq` existe para avisar da falta — a mensagem sai sem ele |
| A | `plugins/branches/hooks/sessionstart-branches.sh` | 15, 21, 34, 44 | lê `.cwd` e serializa o `additionalContext` |
| A | `plugins/graphify-guard/hooks/sessionstart-graphify.sh` | 8, 11, 38 | lê `.cwd` e serializa o `additionalContext` |
| A | `plugins/project-skills/hooks/sessionstart-organism.sh` | 15, 21, 26, 28, 29, 30, 31, 33, 42 | lê `.cwd`, desmonta o brief do organismo e serializa a saída |

## Classe B1 — lê o campo que decide BLOQUEAR (o dano máximo do issue #5)

| classe | arquivo | linha(s) | campo | canal de bloqueio |
| --- | --- | --- | --- | --- |
| B1 | `plugins/gauntlet/hooks/pretooluse-gauntlet.sh` | 52 | `session_id` | `permissionDecision:"deny"` |
| B1 | `plugins/graphify-guard/hooks/pretooluse-graphify-guard.sh` | 29, 43 | `session_id`, `tool_input.command` | `permissionDecision:"deny"` |
| B1 | `plugins/guardrails/hooks/askq-humanize.sh` | 46 | `session_id` | `permissionDecision:"deny"` |
| B1 | `plugins/guardrails/hooks/lint-and-typecheck.sh` | 31 | `session_id` | `exit 2` |
| B1 | `plugins/guardrails/hooks/scope-cop.sh` | 77 | `session_id` | `permissionDecision: "deny"` |
| B1 | `plugins/intent-guard/hooks/delivery-audit.sh` | 25 | `session_id` | `decision:"block"` |
| B1 | `plugins/intent-guard/hooks/plan-gate.sh` | 24 | `session_id` | `exit 2` — sem registro próprio: chamado pelo portão único da família |
| B1 | `plugins/intent-guard/hooks/task-checkpoint.sh` | 24 | `session_id` | `decision:"block"` |
| B1 | `plugins/project-skills/hooks/pretooluse-doc-guard.sh` | 34, 47 | `session_id`, `tool_input.command` | `permissionDecision:"deny"` |
| B1 | `plugins/project-skills/hooks/pretooluse-organism-gate.sh` | 42 | `session_id` | `permissionDecision:"deny"` |
| B1 | `plugins/project-skills/hooks/pretooluse-plan-gate.sh` | 51 | `session_id` | `permissionDecision:"deny"` |
| B1 | `plugins/ship/hooks/pre-deploy-test-check.sh` | 27 | `tool_input.command` | `exit 2` |
| B1 | `plugins/project-skills/hooks/pretooluse-espera-com-guarda.sh` | 47, 53 | `session_id`, `tool_input.command` | `permissionDecision:"deny"` |
| B1 | `plugins/project-skills/hooks/pretooluse-motor-arma.sh` | 60 | `session_id` | `permissionDecision:"deny"` |
| B1 | `plugins/visual/hooks/pre-exitplan-visualize.sh` | 29 | `session_id` | `exit 2` — sem registro próprio: chamado pelo portão único da família |

## Classe B2 — lê o campo que decide REGISTRAR (o dano diferido do issue #5)

| classe | arquivo | linha(s) | campo | o que se perde sem `jq` |
| --- | --- | --- | --- | --- |
| B2 | `plugins/bootstrap/hooks/post-plugin-command.sh` | 57 | `tool_input.command` | mutação de plugin não é detectada; o snapshot/commit nunca roda |
| B2 | `plugins/branches/hooks/posttooluse-push-branch.sh` | 28, 39 | `tool_input.command`, `session_id` | push não é notado; o aviso de branch some |
| B2 | `plugins/context-guard/hooks/context-guard.sh` | 26 | `session_id` | o guard de contexto não abre |
| B2 | `plugins/context-guard/hooks/context-guard-reset.sh` | 11 | `session_id` | o sentinel da sessão nunca é limpo |
| B2 | `plugins/context-guard/hooks/context-guard-writer.sh` | 19 | `session_id` | o `%` de contexto nunca é gravado — e o guard depende desse arquivo |
| B2 | `plugins/intent-guard/hooks/mark-work.sh` | 15 | `session_id` | o trabalho da sessão não é marcado; `delivery-audit` fica sem base |
| B2 | `plugins/lixeiro/hooks/posttooluse-anota.sh` | 31, 34 | `tool_input.command`, `session_id` | artefato criado não é anotado |
| B2 | `plugins/lixeiro/hooks/sessionend-colhe.sh` | 28 | `session_id` | a colheita de fim de sessão não acontece |
| B2 | `plugins/lixeiro/hooks/sessionstart-orfaos.sh` | 29 | `session_id` | órfãos de sessões passadas não são cobrados |
| B2 | `plugins/lixeiro/hooks/stop-colhe-turno.sh` | 36, 37 | `stop_hook_active`, `session_id` | sem o `stop_hook_active` não há nem guarda de reentrância nem colheita |
| B2 | `plugins/project-skills/hooks/posttooluse-doc-read.sh` | 17 | `session_id` | a leitura de doc não é registrada; o `doc-guard` segue cobrando |
| B2 | `plugins/project-skills/hooks/sessionstart-doc.sh` | 25 | `session_id` | o briefing de doc não abre a sessão |
| B2 | `plugins/project-skills/hooks/posttooluse-andamento.sh` | 42, 47 | `session_id`, `tool_input.command` | a linha de andamento do motor nunca sai na barra |
| B2 | `plugins/project-skills/hooks/stop-doc-touch.sh` | 19, 21 | `session_id`, `stop_hook_active` | a cobrança de doc defasada não sai |
| B2 | `plugins/project-skills/hooks/userpromptsubmit-plan-escape.sh` | 39 | `session_id` | a escapatória do gate de plano não é registrada |
| B2 | `plugins/project-skills/hooks/sessionstart-plan.sh` | 25 | `session_id` | o plano aberto não ressuscita depois do `/clear` |
| B2 | `plugins/project-skills/hooks/stop-plan-status.sh` | 35, 38 | `stop_hook_active`, `session_id` | o status do plano não é cobrado no fim do turno |

---

## Como conferir

```bash
bash scripts/test_sem_jq.sh
```

A suíte re-deriva os números do retrato, confere que as tabelas listam exatamente os arquivos
medidos, prova arquivo a arquivo que todo integrante da classe B lê pelo `hook-json.sh` (sem
bail de `jq`, sem `jq` cru, com canal de aviso) — e então RODA hooks com o `jq` fora do PATH:
o `doc-guard` tem que continuar bloqueando a busca cega e continuar liberando o comando comum,
o gate de deploy tem que continuar barrando teste vermelho e liberando teste verde, e sem `jq`
nem `python3` o hook tem que falar em vez de calar.
