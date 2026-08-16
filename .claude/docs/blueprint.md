---
generated: 2026-08-14
reviewed: 2026-08-14
project: pedro-plugins
authored-by: ex-post-rascunho
status: approved
approved: 2026-08-16
scope: []
approved-sig: 3304081701
---

# Como o sistema funciona

> Nota desta rodada: as citações abaixo apontam rascunhos da MESMA rodada ex-post (draft
> citando draft, por ordem do dono). O critério "todo passo aponta documento aprovado" só
> fecha quando o referendo aprovar a cadeia inteira, na ordem das etapas.

## O ciclo, do começo ao fim
1. O dono concebe: seis acordos viram a régua do projeto.  ← journeys.md · "Conceber um projeto com a metodologia"
2. A régua vira plano ticável: requisito, tarefa e critério de pronto por passo.  ← architecture-intent.md · fronteira "Skill → motor de skill"
3. O motor executa em ondas, com revisor por tarefa e tique só com prova.  ← journeys.md · "Executar um plano noite adentro"
4. A esteira mede; o portão confere a prova e decide se o commit sai.  ← architecture-intent.md · fronteira "Portão → esteira"
5. O push leva ao CI nos três sistemas e aos clientes pelo catálogo.  ← journeys.md · "Publicar uma mudança de plugin"
6. O que a rodada ensinou vira lição, doc e grafo — e realimenta a próxima concepção.  ← solution-strategy.md · "Regra vira programa que morde"

## As peças que participam, e o que cada uma decide
- **Skill** — o julgamento: o que é bom, o que reprova  ← architecture-intent.md · As peças
- **Hook** — bloquear ou avisar no evento; nunca travar o dono  ← constraints.md · "Hook é fail-open"
- **Motor de skill** — a contagem e a mecânica; nenhum número sai do olho do modelo  ← architecture-intent.md · fronteira "Skill → motor de skill"
- **Portão de release** — se o commit sai, e por quê não  ← architecture-intent.md · As peças
- **Esteira** — o que é verde, com prova gravada  ← glossary.md · "verde"
- **Catálogo** — o que existe para quem instala  ← architecture-intent.md · As peças

## Onde o humano entra
- Aprova cada acordo da concepção — só a fala dele fecha etapa.  ← journeys.md · "Conceber"
- Decide as pendências de largada antes de o motor sair.  ← journeys.md · "Executar um plano noite adentro"
- Dá o veredito nas páginas de decisão — manter, mudar, remover.  ← solution-strategy.md · "Toda decisão chega como página com prova"
- Dirige, veta e para em voo o que envolve julgamento; veto que toca algo já aprovado pergunta antes de reabrir.
- Recebe o alerta de plano falho — desvio de plano e erro de arquitetura viram aviso, nunca conserto automático.
- Aprova o que a análise forense propõe; a skill que diagnostica não executa a sentença.
- Decide quando o modelo acha que "não vale a pena" — essa avaliação não é dele: ele oferece, o dono decide.

## O que este desenho NÃO mostra, de propósito
- O conteúdo de cada plugin, um a um — o desenho é do organismo, não do órgão; o catálogo em architecture.md (minerado) cobre um a um.
- As integrações de terceiros (MCPs, Node do visual) — são hóspedes do host, não peças deste ciclo.
- O fluxo interno do Claude Code — é o host; começa e termina fora da nossa fronteira. ← context.md · Sistemas externos
