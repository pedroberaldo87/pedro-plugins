# Briefing — Skill de Loop de Revisão Disciplinado

> Base empírica: a sessão de 2026-06-20 rodou um loop `/goal` ("code-review e conserte até zero erros") por **13 rodadas** sobre o scrubber de secret do project-doc v3. Rendeu **4/10**: as 3 primeiras rodadas acharam bugs reais, o resto foi cauda longa + **5 regressões auto-infligidas**. Este briefing destila o que deu errado num design de skill reutilizável, universal (qualquer codebase). Não é a skill — é a especificação pra criá-la.

---

## Parte 1 — A anatomia das regressões (o que as produziu, e como evitar)

O Pedro pediu pra detalhar o mecanismo. O achado central: **as regressões NÃO foram aleatórias — são 5 padrões nomeáveis, e 4 dos 5 têm a MESMA contramedida barata.** Cada uma abaixo é um caso real desta sessão.

### Mecanismo A — Alargamento de escopo (consertar recall quebra precision)
- **O que houve:** pra pegar `SECRETVALUE=` (chave colada que o match-por-token perdia), troquei o matcher de chave de exato → substring. Substring pegou `AUTHOR` (contém AUTH), `COMPASS` (PASS), `CHAVEIRO` (CHAVE) → passou a redigir valores benignos.
- **Padrão geral:** consertar um falso-negativo **alargando** uma regra genérica quase sempre cria falsos-positivos em outro canto. Precision e recall puxam em direções opostas.
- **Contramedida:** prefira **extensão enumerada** (lista de casos conhecidos — `STRONG_SECRET` com as formas coladas explícitas) a **alargamento de regra**. Extensão tem blast radius ZERO; alargamento tem blast radius difuso. E rode os casos benignos (negative tests) logo após alargar.

### Mecanismo B — Ordem de curto-circuito (exceção antes da regra)
- **O que houve:** pra preservar `PUBLIC_KEY`, pus `if 'PUBLIC' in key: return False` no topo de `_is_secret_key`. `PUBLIC_SECRET` bateu no PUBLIC e saiu **antes** de checar SECRET → vazou.
- **Padrão geral:** um early-return de exceção colocado ANTES da regra principal engole casos que deviam cair na regra. A exceção tem que ser a mais ESPECÍFICA, não a primeira.
- **Contramedida:** ordene checagens positivas fortes ("é segredo") ANTES de exceções ("mas é público"); ou a exceção só vale se a regra positiva não disparar. Teste o caso de **interseção** (PUBLIC + SECRET) explicitamente.

### Mecanismo C — Proxy sintático grosseiro (uma propriedade superficial usada como semântica, e ela vale pros dois lados)
- **O que houve:** pra preservar path de código (`src/x.ts`), tratei "tem `/`" como "é contexto, não redija". Mas secret com `/` (`wJalr/K7.../...`) também tem `/` → não foi redigido.
- **Padrão geral:** usar uma feature sintática barata (tem `/`, é numérico, tem `.ext`) como proxy de uma classe semântica (é path) é frágil quando a feature aparece nos DOIS lados da fronteira.
- **Contramedida:** não decida por UMA propriedade — combine sinais (tem `/` **E** baixa entropia **E** longe de palavra-sinal). Na zona de dúvida, inverta o default pro lado seguro (redige/marca, não preserva).

### Mecanismo D — Conflito entre correções (heurística nova viola invariante de correção anterior)
- **O que houve:** pra impedir o roubo do valor do par JSON vizinho, adicionei um flag que parava no 1º placeholder. Isso **quebrou** o par AWS (corrigido numa rodada anterior), cuja correção EXIGIA atravessar o placeholder pra achar o secret real.
- **Padrão geral:** cada correção estabelece uma invariante implícita. A correção K+n viola a invariante da correção K sem perceber — porque as invariantes não estão escritas em lugar nenhum, só (talvez) nos testes.
- **Contramedida:** cada correção vira um **teste nomeado com a invariante no nome** ("atravessa placeholder pro par AWS"). Rodar a suíte INTEIRA a cada edição transforma violação-silenciosa em falha-imediata. (Foi exatamente assim que peguei 2 regressões na hora — o teste acusou `FALHOU` no mesmo instante.)

### Mecanismo E — Interação entre estágios (um estágio deixa resíduo que outro consome)
- **O que houve:** o passo de JSON redigiu o VALOR mas deixou a CHAVE visível; o estágio de prosa seguinte disparou nessa chave, viu o próprio valor já coberto, e pegou o valor do par SEGUINTE.
- **Padrão geral:** num pipeline de estágios sobre estado compartilhado (o mesmo texto), a saída de um é input do próximo; um resíduo (palavra-chave não consumida) vira gatilho inesperado.
- **Contramedida:** cada estágio **consome/neutraliza** o que processou (mascarar a chave também, não só o valor); estágios sobre estado compartilhado devem enxergar explicitamente o que já foi tocado. Teste a **interação** entre estágios, não só cada estágio isolado.

### O fio comum (diagnóstico-raiz)
**Todas as 5 são edições numa ÚNICA função grande (`scrub`, 875 linhas) com camadas acopladas sobre estado compartilhado (o mesmo texto/spans).** Quando os casos não são independentes, cada correção tem blast radius sobre os outros.
- **Defesa estrutural (cara):** detectores independentes que não compartilham mutação — cada um recebe o texto, devolve spans a redigir; merge no fim. Só vale se o churn persistir.
- **Defesa barata (paga sempre):** **regression gate** — rodar a suíte INTEIRA a cada conserto. Converte 4 dos 5 mecanismos de "regressão descoberta 3 rodadas depois" em "falha na mesma edição". É o maior ROI deste briefing.

---

## Parte 2 — O que o Pedro JÁ tem (reusar, não reinventar)

A skill nova **não nasce do zero** — casa peças existentes + adiciona os 3 guard-rails que faltam.

- **`/iterate`** — JÁ tem o que MAIS faltou nesta sessão: contrato duro (resultado verificável + meio de verificar), **snapshot de baseline lint/typecheck**, e **para em regressão**. O loop desta sessão foi um `/goal` cru — não usou nada disso. → **reusar o regression gate e o baseline do /iterate.**
- **`/qa`** — JÁ é o loop de review multi-agente (4 specialists, a partir da 2ª rodada cada um recebe os findings anteriores pra verificar+achar-novos). MAS roda `/goal` com a condição que FALHOU ("zero findings P0/P1") e não tem classificação de domínio nem accepted-limits. → **reusar o esqueleto multi-agente; trocar o critério de parada.**
- **`/code-review`** — rodada ÚNICA multi-ângulo (finders por dimensão → verify → sweep). → **reusar como a "rodada" interna do loop.**
- **`/goal`** — loop genérico até condição + Stop-hook. → é o motor; o problema não é o /goal, é a CONDIÇÃO que se passa pra ele ("zero" em domínio assintótico).

**Decisão de design recomendada:** a skill nova é uma **evolução do `/qa`** (que já é "loop de review até critério") com 3 adições: (1) classificação de domínio, (2) regression gate emprestado do `/iterate`, (3) accepted-limits + churn detector. Avaliar se vira `/qa v2` ou skill separada (`/review-loop`).

---

## Parte 3 — Os 3 guard-rails que faltam (o núcleo da skill)

### Guard-rail 1 — Classificação de domínio (a decisão mais importante, feita ANTES da rodada 1)
O alvo tem **estado-alvo binário alcançável**?
- **Convergente** (testes passam · build verde · lint/types zero · um comando de verificação objetivo) → pode loopar até atingir. Critério de parada = o alvo. (É o território do `/iterate`/`/qa`.)
- **Assintótico** (heurística: scrubber · parser · ranker · prompt · classificador · regex · detecção fuzzy · "achar todos os bugs") → "perfeito" NÃO existe; o espaço de input é infinito; um finder adversarial SEMPRE acha mais um. → teto rígido + corte por severidade.

**O erro-raiz desta sessão:** tratar um problema assintótico (scrubber) com critério convergente ("até zero erros"). Por isso nunca parava — o Pedro teve que matar na mão.

### Guard-rail 2 — Regression gate por conserto (a contramedida de 4 dos 5 mecanismos)
Para CADA finding aceito:
1. **Test-first:** escrever o teste que reproduz o finding (red) ANTES de consertar.
2. Consertar.
3. **Rodar a suíte INTEIRA** (não só o teste novo).
4. Se algo que passava quebrou → **regressão auto-infligida**: reverter e refazer com mudança mais cirúrgica (extensão enumerada > alargamento). Registrar no churn counter.

Empresta o baseline-snapshot + para-em-regressão do `/iterate`. É o que converte "descobrir a regressão 3 rodadas depois" em "pegar na hora".

### Guard-rail 3 — Accepted-limits vivo + churn detector
- **Accepted-limits:** após a rodada 1, materializar a lista de "isto é limite inerente, não-bug" (ex: pro scrubber — "secret all-letter sem sinal a >160 chars", "bytes de controle em commit msg"). Toda rodada seguinte RECEBE a lista; os finders são instruídos a **não re-reportar**. Cresce a cada rodada. Mata o re-trabalho de re-julgar os mesmos edge-cases.
- **Churn detector:** rastrear por arquivo/função o nº de edições e de regressões auto-infligidas. Se a MESMA função teve **≥2 regressões auto-infligidas** → ESCALAR: parar de remendar, sinalizar "acoplamento alto; ou refatora pra detectores independentes, ou aceita os limites". Não mais rodadas de remendo na mesma função.

---

## Parte 4 — Fluxo concreto da skill

```
0. CLASSIFICAR DOMÍNIO → convergente | assintótico   (pergunta 1× se ambíguo)
1. DECLARAR CONTRATO    → teto de rodadas, régua de severidade (P0/P1?), budget de token (opcional)
                          [convergente: teto alto+sanidade · assintótico: teto ~3]
2. RODADA 1             → /code-review multi-ângulo → findings
3. POR FINDING (sev ≥ régua):
     a. test-first (red) → b. fix → c. SUÍTE INTEIRA →
     d. regrediu? → reverte + refaz cirúrgico + churn++   (Guard-rail 2)
4. MATERIALIZAR/ATUALIZAR accepted-limits               (Guard-rail 3)
5. CHECAR PARADA (qualquer um):
     - teto atingido
     - 1 rodada inteira só com findings dentro dos accepted-limits (zero de severidade real)
     - churn detector escalou
     - [convergente] o comando-alvo passou
   → se sim, vai pro passo 8
6. PRÓXIMA RODADA       → 1 finder focado nas MUDANÇAS da rodada anterior (caça-regressão)
                          + 1-2 ângulos frescos · TODOS recebem os accepted-limits
7. volta ao passo 3
8. VERIFICAÇÃO DE SAÍDA → suíte completa + checks de integração do projeto
   RELATÓRIO            → findings por severidade, regressões pegas, token acumulado,
                          accepted-limits documentados, recomendação final
```

**Regra de ouro:** para domínio assintótico, o critério de parada é **"uma rodada inteira sem finding de severidade real"** — NUNCA "zero findings". "Zero" é assíntota, não estado.

---

## Parte 5 — Parâmetros / config

- `domain`: `auto` | `convergent` | `asymptotic` (auto = inferir; perguntar se ambíguo)
- `max_rounds`: default `3` (assintótico) · `unlimited+sanity` (convergente)
- `severity_floor`: default `P1` (conserta P0/P1; P2+ vira candidato a accepted-limit)
- `regression_gate`: `on` (sempre — é o coração)
- `token_budget`: opcional; reportar gasto acumulado por rodada de qualquer jeito
- `finders_per_round`: 1 caça-regressão + 1-2 ângulos frescos (não re-varrer idêntico)

---

## Sumário Executivo

### 1 · O diagnóstico das regressões
- 🔧 **Como:** 5 mecanismos nomeáveis — (A) alargamento de escopo, (B) ordem de curto-circuito, (C) proxy sintático grosseiro, (D) conflito entre correções, (E) interação entre estágios.
- 💡 **Por quê importa:** 4 dos 5 têm a MESMA contramedida barata — **rodar a suíte inteira a cada conserto** (regression gate). O caro (refatorar) só vale se o churn persistir.
- 📁 **Origem:** todas foram edições numa função de 875 linhas com estado compartilhado — acoplamento alto.

---

### 2 · Reúso (não reinventar)
- 🔧 **Como:** evoluir o **/qa** (já é loop de review multi-agente) + emprestar o regression-gate/baseline do **/iterate** + usar **/code-review** como a rodada interna.
- 💡 **Por quê:** o `/iterate` já PÁRA EM REGRESSÃO — exatamente o que faltou nesta sessão (foi `/goal` cru). O esqueleto existe; falta a disciplina.
- 📁 **Toca em:** `plugins/qa/`, `plugins/iterate/`, `plugins/code-review/` (avaliar /qa v2 vs skill nova).

---

### 3 · Os 3 guard-rails novos
- 🔧 **Como:** (1) classificar domínio (convergente vs assintótico) ANTES de começar; (2) regression gate por conserto (test-first → suíte inteira → reverte se regrediu); (3) accepted-limits vivo + churn detector (escala pra "refatora" após 2 regressões na mesma função).
- 💡 **Por quê:** o erro-raiz foi tratar um problema assintótico (scrubber) com critério convergente ("zero"). Critério de parada certo = "1 rodada sem finding de severidade real", nunca "zero findings".
- 📁 **Toca em:** SKILL.md da skill nova (a definir nome: `/review-loop` ou `/qa` v2).
