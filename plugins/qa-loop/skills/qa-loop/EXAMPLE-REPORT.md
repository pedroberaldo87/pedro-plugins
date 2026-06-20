<!--
EXEMPLO do RELATÓRIO HUMANO do /qa-loop — dados fictícios mas realistas.
É a referência de CONTEÚDO + ESTRUTURA. O relatório real é renderizado como HTML pelo template/daemon
da skill /visual (NÃO markdown no chat): dark-theme, escaneável, abre no browser. Este .md descreve cada
seção do HTML pra quem for renderizar. O journal AGÊNTICO (telemetria + aprendizados) é OUTRO artefato —
ver EXAMPLE-JOURNAL.md.

Mapa das seções do HTML:
- HERO + meta-chips (domínio · plano-âncora · rede · critério de parada).
- GRÁFICO (SVG inline): a curva de retornos decrescentes (findings de severidade real por rodada).
- TABELA por rodada: cada linha tem as considerações da rodada DENTRO dela (<details> colapsável), não um listão depois.
- Seção de ALERTAS (plan-flaw + candidatos a mudança-de-plano).
- Seção VISUAL de recados/sugestões pra futuro planejamento.
- Recomendação final.
-->

# /qa-loop — Relatório · `src/scrub.py` (scrubber de secret do project-doc)

**Domínio:** assintótico (heurística de redação — espaço de input infinito)
**Plano-âncora:** `.claude/plans/scrubber-v3.md`
**Rede de regressão:** suíte de testes (completa — `pytest tests/test_scrub.py`, 41 testes)
**Critério de parada que disparou:** rodada limpa na **rodada 3** (zero finding de severidade real fora dos accepted-limits)
**Motor:** Workflow · Revisor=opus/high · Planejador=opus/high (árbitro único) · Executor=sonnet/high · floor=P1 · teto=6 (trava)

---

## Curva de retornos decrescentes (o gráfico, no HTML é SVG)

```
findings de severidade real
 5 ┤ ●
 4 ┤ │
 3 ┤ │
 2 ┤ │
 1 ┤ └──● 
 0 ┤      └──●   ← rodada limpa, PARA
   └──┬──┬──┬──
      1  2  3   rodada
```

`5 → 1 → 0` findings de severidade real. **Última rodada que valeu a pena: 2.** A rodada 3 só achou P2/P3 e
accepted-limits → foi a **confirmação da parada** (re-rodou o checklist completo do Revisor pra não parar numa
rodada magra).

---

## Por rodada (no HTML cada linha tem suas considerações colapsáveis)

| Rodada | Findings novos (P0/P1/P2/P3) | Correções aplicadas | Taxa de retorno (sev. real) | Regressões pegas | Tokens |
|--------|------------------------------|---------------------|-----------------------------|------------------|--------|
| 1      | 2 / 3 / 4 / 6                | 5                   | **5**                       | 0                | 48k    |
| 2      | 0 / 1 / 2 / 3                | 1                   | **1**                       | 1                | 31k    |
| 3      | 0 / 0 / 1 / 2                | 0                   | **0** → rodada limpa, PARA  | 0                | 22k    |

> Considerações da rodada 1 (colapsável): sweep completo do checklist (6 dimensões). 2 P0 de secret-leak são a raiz do valor.
> Considerações da rodada 2 (colapsável): caça-regressão + `PUBLIC_SECRET`. 1 regressão auto-infligida pega na hora.
> Considerações da rodada 3 (colapsável): só P2/P3 e limites → confirma a parada.

---

## O que foi consertado (bucket 1 · implementação)

Cada conserto passou pelo regression gate (test-first → suíte inteira → aceito só se nada quebrou). Quem decidiu
keep/revert foi o Opus, não o Sonnet.

- **[P0]** `scrub() L120` — segredo colado `SECRETVALUE=...` escapava ao match-por-token. Fix por **extensão enumerada** (forma colada adicionada à lista), blast radius zero. Teste `test_secret_colado_eh_redigido`.
- **[P0]** `_is_secret_key() L88` — `wJalr/K7.../...` (com `/`) vazava pela regra "tem barra = path". Fix: detecção do par chave=valor de segredo **antes** da exceção do `/`. Teste `test_secret_com_barra_redige`.
- **[P1]** `scrub() L210` — par JSON vizinho tinha o valor roubado pelo estágio de prosa. Fix: a chave também é mascarada (estágio neutraliza o que processou). Teste `test_estagio_json_neutraliza_chave`.
- **[P1] (rodada 2)** `_is_secret_key() L92` — `PUBLIC_SECRET` saía pela exceção `PUBLIC` antes de checar `SECRET`. Fix: regra positiva forte antes da exceção. Teste `test_public_secret_ainda_redige`.

**Invariantes vivas registradas** (viram teste nomeado — cada conserto futuro é checado contra elas):
`atravessa_placeholder_pro_par_aws` · `chave_tambem_mascarada` · `public_secret_ainda_redige`.

---

## Regressão auto-infligida pega na hora (rodada 2)

Ao consertar o `PUBLIC_SECRET`, a 1ª tentativa do Sonnet **alargou** a regra de exceção e quebrou
`test_atravessa_placeholder_pro_par_aws` (que um conserto da rodada 1 exigia). A suíte inteira acusou na MESMA
edição → o Opus reverteu → refez por extensão enumerada → verde. (Sem o gate, isso teria virado "10 bugs por
correção" 3 rodadas depois — o padrão que motivou a skill.) `churn(_is_secret_key) = 1` — abaixo do gatilho de
escalada (2).

---

## Accepted-limits PROPOSTOS (não são bug — limite inerente do domínio)

> Propostos pelo loop e adjudicados pelo Planejador. **Só viram permanentes quando você ratifica** movendo pra
> `.claude/qa-loop.config.md`. Até lá, são re-avaliados a cada sessão.

- Secret **all-letter sem sinal** (`apenasletrassemnenhumdigito`) a >160 chars — indistinguível de prosa longa sem um classificador semântico.
- Bytes de controle dentro de mensagem de commit — fora do escopo do scrubber de texto.

---

## ⚠️ Alertas de plano/arquitetura — NÃO implementados (pra você julgar)

> Estes findings expõem decisões do **plano**, não bugs de implementação. **Não toquei neles** — o loop enforça o plano, não o redesenha. Sobem aqui pra você decidir. "Apresento e julgamos."

- **[plan-flaw · P0]** Os 4 estágios do scrubber operam sobre **estado mutável compartilhado** (o mesmo texto/spans). Isso é a raiz estrutural das regressões: cada correção tem blast radius sobre as outras (4 das 5 regressões da sessão-base vieram daqui). É decisão de arquitetura do `scrubber-v3.md`, não caso novo.
  - **Sugestão pra re-planejamento futuro** (NÃO implementei): detectores independentes — cada um recebe o texto, devolve os spans a redigir, merge no fim. Blast radius isolado por detector. Só vale se o churn nesse arquivo persistir.

- **[plan-flaw · P1]** O plano especifica "redigir por substring de palavra-sinal", frágil por design (substring vale pros dois lados da fronteira — `AUTHOR` contém `AUTH`). A skill contornou caso a caso, mas a abordagem-base vai gerar cauda longa enquanto existir. **Decisão de método, sua.**

---

## 💬 Recados / sugestões pra futuro planejamento (seção visual)

- O churn está concentrado em `_is_secret_key()` — se voltar a aparecer numa próxima QA, é sinal forte pra adotar a arquitetura de detectores independentes.
- A rubrica deste projeto pode ganhar uma linha: "substring de palavra-sinal → exige checagem de fronteira" (vira invariante viva).

## Recomendação final

Convergiu em **3 rodadas** (gate de severidade, não o teto). **6 correções**, **1 regressão pega na hora**,
**2 limites inerentes** propostos. O código está aderente ao plano e sem regressão conhecida.

**Mas há 1 alerta P0 de arquitetura do plano** (estado compartilhado) que vai continuar gerando regressões a cada
manutenção futura — recomendo levar pro re-planejamento. Não é trabalho de QA; é decisão sua.
