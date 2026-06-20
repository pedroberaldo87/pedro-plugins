<!--
EXEMPLO do JOURNAL AGÊNTICO do /qa-loop — dados fictícios mas realistas.
NÃO é pro Pedro ler como produto. É o agente passando informação pra ele-mesmo-do-futuro MELHORAR a skill.
Linguagem agêntica, verborrágica, à exaustão. Três camadas, três lugares. O relatório HUMANO (HTML) é OUTRO
artefato — ver EXAMPLE-REPORT.md.

Onde mora cada camada:
- (1) Telemetria JSONL  → <projeto>/.claude/qa-loop/telemetry.jsonl  (+ agregado ~/.claude/qa-loop/journal/telemetry.jsonl)
- (2) Aprendizado da SKILL → ~/.claude/qa-loop/journal/learnings.md  (cross-projeto, acumula, sobrevive a reinstalar)
- (3) Memória de QA do PROJETO → .claude/qa-loop.config.md (VERSIONADA, junto da config)

A skill LÊ (2) e (3) no início de cada sessão (passo 0) — é assim que "melhora com o uso".
-->

# Journal agêntico — exemplo das 3 camadas

## Camada 1 · Telemetria quantitativa (JSONL, 1 linha/sessão)

Append-only. Os números saem do `return` do Workflow — não é contabilidade extra. Tokens = número PASSIVO (R5),
nunca eixo de parada nem framing de custo. A mediana de `last_round_with_severe_finding` entre sessões
assintóticas é a resposta empírica ao "o nº ideal de loops é 3?".

```jsonl
{"ts":"2026-06-18T20:10:00Z","target":"src/scrub.py","domain":"asymptotic","severity_floor":"P1","max_rounds_config":6,"rounds_run":4,"corrections_per_round":[6,2,1,0],"last_round_with_severe_finding":3,"regressions_self_inflicted":2,"accepted_limits":1,"plan_flaw_alerts":1,"tokens_per_round":[52000,38000,29000,21000],"stop_reason":"no-severe-finding","pedro_score_0_10":7}
{"ts":"2026-06-19T15:42:00Z","target":"api/sync.ts","domain":"convergent","severity_floor":"P1","max_rounds_config":6,"rounds_run":2,"corrections_per_round":[3,0],"last_round_with_severe_finding":1,"regressions_self_inflicted":0,"accepted_limits":0,"plan_flaw_alerts":0,"tokens_per_round":[41000,18000],"stop_reason":"convergent-command-passed","pedro_score_0_10":9}
{"ts":"2026-06-20T22:14:03Z","target":"src/scrub.py","domain":"asymptotic","severity_floor":"P1","max_rounds_config":6,"rounds_run":3,"corrections_per_round":[5,1,0],"last_round_with_severe_finding":2,"regressions_self_inflicted":1,"accepted_limits":2,"plan_flaw_alerts":2,"tokens_per_round":[48000,31000,22000],"stop_reason":"no-severe-finding","pedro_score_0_10":null}
```

**Leitura agêntica destes 3 pontos (pra futuro-eu):** nas 2 sessões assintóticas sobre `scrub.py`,
`last_round_with_severe_finding` foi 3 e depois 2 — a curva está caindo com o uso (a memória do projeto está
semeando bem). A sessão convergente parou na rodada 2 pelo comando objetivo (esperado). Ainda n<10; NÃO cravar
teto. Continuar coletando.

---

## Camada 2 · Aprendizado da SKILL (`~/.claude/qa-loop/journal/learnings.md`, cross-projeto)

Findings exaustivos sobre onde o **próprio PROCESSO de QA** acertou/errou + **AÇÃO concreta pra futuro-eu**.
Registra o que ERROU (pra corrigir o prompt/rubrica) E o que FUNCIONOU (pra não regredir). Cada entrada é
datada e ancorada no alvo onde apareceu.

```markdown
### 2026-06-20 · src/scrub.py (asymptotic)

- **PADRÃO (errou):** o Opus Revisor inflou um finding de `naming` pra P1 ("nome `_chk` é enganoso").
  O Planejador rebaixou pra P2 (sem bug concreto anexado). Aconteceu também em 2026-06-18.
  → **AÇÃO pra futuro-eu:** a rubrica (R2) já diz "naming só é P1 com bug concreto" — mas o REVISOR está
    pré-classificando severidade quando não devia. Reforçar no reviewPrompt: "você ACHA, não carimba P0/P1 —
    descreva o impacto, o Planejador decide a faixa." (gerar≠julgar; o Revisor invadindo o papel do juiz é a fonte.)

- **PADRÃO (errou):** uma regressão escapou do gate na rodada 2 porque o teste-red do Sonnet cobria o estágio
  isolado, não a INTERAÇÃO entre estágios (mecanismo E). Só foi pega quando a suíte inteira rodou — sorte de já
  existir um teste de interação de uma sessão anterior.
  → **AÇÃO pra futuro-eu:** o checklist do Revisor precisa de uma linha explícita sobre "interação entre estágios";
    e o execPrompt do Sonnet deve exigir, quando o alvo tem pipeline de estágios, um teste-red que cubra o par
    estágio-A-deixa-resíduo / estágio-B-consome, não só cada estágio.

- **FUNCIONOU (não regredir):** ordenar os fixes do bucket 1 por blast-radius (extensão-enumerada primeiro,
  alargamento por último) evitou 1 conflito que a sessão-base teria gerado. Manter essa sequência no planPrompt.

- **FUNCIONOU:** declarar a rede de regressão no header e baixar o teto na Camada 3 deixou o Pedro confiante de
  que nada foi "fingido". Manter a honestidade-da-rede como passo 1 obrigatório.

- **CALIBRAÇÃO de teto:** neste tipo de alvo (scrubber de heurística), o yield de severidade real secou na
  rodada 2-3 em 2 de 2 sessões. Evidência ACUMULANDO de que teto efetivo ~3 — mas n=2, não cravar. Re-checar aos n≥10.
```

---

## Camada 3 · Memória de QA do PROJETO (`.claude/qa-loop.config.md`, VERSIONADA)

Junto da config do projeto. A próxima QA do alvo já começa sabendo: invariantes vivas, accepted-limits
RATIFICADOS (movidos aqui pelo Pedro — R6), churn hotspots, plan-flaws recorrentes.

```markdown
# qa-loop · config + memória de QA · projeto project-doc

## Knobs (sobrescrevem o default)
severity_floor: P1
max_rounds: 6
churn_threshold: 2

## Rubrica do projeto (ajustes sobre a rubrica-base)
- "substring de palavra-sinal" → exige checagem de fronteira de palavra; sem isso é P1 (gera falso-positivo cross-fronteira).
- naming → P2 salvo bug concreto anexado.

## Invariantes vivas (o Revisor não pode violar; o Executor testa contra elas)
- atravessa_placeholder_pro_par_aws
- chave_tambem_mascarada
- public_secret_ainda_redige

## Accepted-limits RATIFICADOS (permanentes — não re-reportar)
- secret all-letter sem dígito a >160 chars — indistinguível de prosa sem classificador semântico (ratificado 2026-06-19).
- bytes de controle em mensagem de commit — fora do escopo do scrubber de texto (ratificado 2026-06-19).

## Churn hotspots (funções acopladas — candidatas a refator)
- _is_secret_key() — 3 regressões auto-infligidas acumuladas em 2 sessões. Se passar de novo, escalar pro re-plano (detectores independentes).

## Plan-flaws recorrentes (sobem pro alerta toda sessão até o plano mudar)
- estágios sobre estado mutável compartilhado (scrubber-v3.md) — raiz estrutural das regressões.
```

---

## O loop fecha

No início da próxima sessão (passo 0), a skill LÊ a Camada 3 (semeia accepted-limits + invariantes nos args do
Workflow) e a Camada 2 (afina os prompts do Revisor/Planejador). A Camada 1 alimenta a decisão humana sobre o
teto, periodicamente. **Zero auto-tuning automático no v1** — o ajuste é humano, informado pelo journal.
