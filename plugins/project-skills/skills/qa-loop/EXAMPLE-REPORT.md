# /qa-loop — Relatório HUMANO (exemplo)

O exemplo **renderizado** vive em **`EXAMPLE-REPORT.html`** (gerado invocando a skill `/visual` como parceira).
Abra no browser pra ver o formato + polish:

- **Faixa de status da Fase Gate** (topo de tudo, read-only) — verde `100% — N checks` ou vermelho `GATE VERMELHO` (`gate-red`); se houve conserto repo-wide, separa "conserto da revisão" de "débito pré-existente zerado".
- **Curva de retornos decrescentes** (SVG) + **tabela por rodada** (colapsável).
- **4 categorias de actionable**, cada achado um item SELECIONÁVEL — **✓ Vira ação / ✏️ Ação c/ ajuste / ✗ Descartar**:
  1. Importantes — recomendação (plan-flaw) · 2. Sugestões de melhoria (drift + refators) ·
  3. Limitações atuais (accepted-limits + churn) · 4. Extras (P2/P3).
- **Gerar plano dos selecionados** — você marca, diz "ok", o Claude lê via daemon do `/visual`
  (`~/.claude/visual-state/latest.json`) e monta o próximo plano só com os marcados. Copy é o fallback.

O journal AGÊNTICO (telemetria + aprendizados) é outro artefato — ver **`EXAMPLE-JOURNAL.md`**.
