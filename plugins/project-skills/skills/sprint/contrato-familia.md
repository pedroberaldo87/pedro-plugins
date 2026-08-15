# Contrato da família — onde cada documento mora, e quem escreve e lê cada um

As skills que conversam sobre a documentação de um projeto (`/start`, `/doc`,
`/doc-touch`, `/design-md`, `/sprint`, `/qa-loop` — a família do plugin project-skills) precisam concordar em três coisas: **em que pasta
o arquivo mora**, **qual é o frontmatter dele** e **quem tem direito de escrevê-lo**. Este arquivo
é o único lugar onde isso está dito. Skill que precisa da regra aponta pra cópia local dele; não
repete o texto.

## As pastas

| Pasta | O que mora nela | Vai pro git? |
|---|---|---|
| `.claude/docs/` | os documentos canônicos — autorais e minerados, lado a lado | sim |
| `.claude/docs/decisions/` | o log de decisões, `NNNN-<slug>.md`, um arquivo por decisão | sim |
| `.claude/plans/` | os planos de implementação, `<id>.plan.json`, ticáveis | conforme o projeto |
| `.claude/visual/` | a página de sessão — artefato, não documento | não |
| `.claude/prints/` | os prints de tela da validação visual, `<slug>.png` | não |
| `.claude/reports/` | os relatórios em texto — de execução, de varredura, de causa | não |
| `.claude/archify/` | o diagrama de sessão — artefato, não documento | não |
| `.claude/ata/` | as atas verbatim do `/handoff`, `LOG-<sessão>.md` + `INDEX.md` | não |
| `.claude/pesquisa/` | os dossiês de referência, `<slug>.md` | não |
| `.claude/specs/` | os arquivos de projeto que não são doc — especificação avulsa e export de ferramenta (`.claude/specs/checkout-v2.md`, `.claude/specs/tokens-figma.json`) | não |
| `.claude/vistoria/` | os relatórios de vistoria em HTML | não |
| `.claude/qa-loop/` | a telemetria do `/qa-loop` do projeto | não |
| `.claude/gauntlet/` | o rito e os vereditos de cada disputa, `<data>-<slug>/` | não |
| `.claude/intent/` | o ledger do `/intent-guard` e o desligador `off` | não |
| `.claude/.sprint/` | o ledger de corridas do `/sprint`, `corridas.jsonl`, e as largadas ainda em curso em `em-curso/` | não |
| `.claude/.project-doc/` | a máquina do `/doc` — journal, ledger e achados de mineração | não |
| `.claude/secrets/` | o elo para o cofre de valores-secreto, fora da árvore | não |
| `.claude/legacy-pre-migracao/` | a doc de antes de o projeto virar organismo — preservada, e invisível aos hooks | conforme o projeto |
| `.claude/hooks/` | os hooks do próprio projeto (não é pasta de trabalho de skill) | sim |

Esta tabela é a lista FECHADA das pastas de trabalho de um projeto. Pasta nova
citada por uma skill sem entrar aqui é acusada por `scripts/contrato_pastas_check.py`
— e a ordem é a inversa do costume: primeiro a casa é declarada aqui, depois a skill
a usa. Estado que atravessa projetos mora em `~/.claude/…` e não é assunto desta
tabela.

**A fixture de teste é a exceção e NÃO vai para `.claude/specs/`**: ela mora rastreada ao
lado da suíte que a lê (`fixtures/` junto do `test_*`), dentro do git. Fixture jogada numa
pasta ignorada some na máquina limpa e derruba o CI — o arquivo que um teste abre é código,
não registro de trabalho.

`CLAUDE.md` e os ponteiros finos de outras ferramentas (`AGENTS.md`, `GEMINI.md`, `.cursorrules`)
ficam na **raiz do projeto**, não em `.claude/docs/`.

## Os documentos

Três naturezas, e a natureza decide quem pode escrever.

**Autorais — nascem da entrevista do `/start` (o antigo `/start-doc`), nenhuma mineração os produz.** São as seis
etapas de acordo: `quality-goals.md`, `constraints.md`, `context.md`, `solution-strategy.md`,
`glossary.md` (etapa 1) · `architecture-intent.md` (2) · `design.md` (3, só projeto com interface,
escrito pela `design-md`) · `journeys.md` (4) · `blueprint.md` (5) · `features.md` (6). O roteiro,
o molde e a régua de cada um estão em `authorial-kit.md`, dentro da skill `start` — este
contrato diz **onde** eles moram e **quem** os toca, não o que escrever dentro deles.

**Minerados — o `/doc` FULL (o antigo `/project-doc`) os projeta do código, e o `/doc-touch` os re-projeta em
parte.** `architecture.md`, `patterns.md`, `data-stores.md`, `durability.md`, `runtime.md` e os
demais por concern. Não têm `authored-by: human`; são regeneráveis por definição.

**Derivados — o programa os produz a partir dos outros.** O índice `CLAUDE.md`, os ponteiros
finos, e o irmão histórico `<nome>.historico.md`, que mora **na mesma pasta do canônico** e nasce
na primeira reescrita (quem escreve nele é `lib/historico.py`, nunca a mão).

**A dispensa — `dispensa.md`, o único documento que diz que os outros não virão.** Projeto que
decide viver sem a fundação registra a decisão em `.claude/docs/dispensa.md`, com o **motivo no
frontmatter** (`motivo:`). É o que separa a dispensa deliberada da ausência silenciosa: o gate de
plano (`pretooluse-plan-gate.sh`) libera com ela e segue negando sem ela — e arquivo sem `motivo:`
preenchido não vale, porque dispensa sem motivo escrito é ausência com um arquivo em cima.

## O frontmatter

Todo documento **autoral** carrega:

```yaml
---
generated: {YYYY-MM-DD}
reviewed: {YYYY-MM-DD}
project: {nome}
authored-by: human
status: draft | ready | approved
approved: {YYYY-MM-DD}
approved-sig: {marca do corpo}
correcao-pendente: {o que falta}
scope: []
---
```

Três campos são o contrato inteiro, e o resto é conforto:

- **`authored-by: human` é a trava de escrita.** Quem minera lê e cita, nunca reescreve.
- **`approved:` + `approved-sig:` são o de acordo**, e só `hooks/doc-aprovar.sh` os grava. A marca
  mede o **corpo** (o frontmatter fica de fora): marca gravada diferente do corpo de hoje significa
  que alguém editou depois do de acordo, e a etapa **reabre**.
- **`status:` só chega a `approved` com fala do dono.** `ready` é "escrito"; não libera gate.

Documento minerado não usa `authored-by:` nem `approved:` — pedir de acordo a um arquivo que a
próxima rodada regenera é registro falso. A exceção de forma é o `design.md`, cujo frontmatter é o
do formato `DESIGN.md` (tokens), com o par `status:`/`approved:` por cima.

## Quem escreve e quem lê

| Quem | Escreve | Lê |
|---|---|---|
| `/start` | os autorais, `decisions/0001-*.md`, o índice mínimo | o que já existe em `.claude/docs/` |
| `/design-md` | `design.md` | os autorais da etapa 1 |
| `/doc` FULL | os minerados, `CLAUDE.md`, os ponteiros | os autorais (cita, não reescreve) |
| `/doc-touch` | os minerados tocados pelo diff | os autorais e o índice |
| `/sprint` | nenhum documento — plano e relatório | `constituicao.md`, `quality-goals.md`, o plano |
| `/qa-loop` | nenhum documento — relatório e journal | `constituicao.md`, `quality-goals.md`, o plano |

A regra que fecha a tabela: **quem lê a lei nunca a escreve, e quem a escreve é sempre o humano
pela mão do `/start`.** Motor que escreve o próprio critério de aprovação não é motor, é
carimbo.
