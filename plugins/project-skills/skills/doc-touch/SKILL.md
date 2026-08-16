---
name: doc-touch
description: Atualização INCREMENTAL da documentação project-doc — mapeia o diff do trabalho recente pros docs afetados (via scope inverso) e re-projeta SÓ eles, sem re-mineração completa. Use quando o usuário diz "/doc-touch", "atualiza a doc do que eu mexi", "toca a doc", "atualiza a documentação disso que fizemos", ou após um ciclo de código quando a doc dos arquivos tocados precisa acompanhar. NÃO substitui o /doc FULL (mineração completa) — é o complemento frequente entre FULLs.
---

# doc-touch — atualização incremental da doc

## Antes de tudo — a régua e os princípios (o par obrigatório)

Antes de re-projetar qualquer doc, rode o par, nesta ordem — é ele que substitui a antiga instrução em
prosa "leia a constituição e o quality-goals do projeto":

1. **A régua do projeto** — a skill `doc-load` (invoque pela Skill tool; fora dela:
   `python3 "$(bash "<plugin project-skills>/lib/resolve-plugin.sh" project-skills lib/doc_load.py)" --project-root "$PWD"`).
   Ela diz o que vale como régua HOJE — a lei com `ready`/`approved`, o acordo só com
   `approved`, o minerado como mapa — e o que está ausente, sem fingir.
2. **Os princípios genéricos** — a skill `principles`, quando instalada
   na máquina. Ausente: siga sem ela, dizendo isso no relato.

Em conflito, **a régua do projeto ganha** — princípio genérico não revoga a lei da casa.

Irmã do `/doc` (mesmo plugin, mesma estrutura de doc, mesmos invariantes). O FULL minera tudo e re-projeta tudo; o **touch** atualiza só os docs cujo `scope:` intersecta o diff do trabalho recente. Mexeu → tocou a doc. O FULL vira evento raro.

## Fluxo (5 passos)

### 1 · Grafo fresco + plano determinístico
```bash
graphify update "<root>" --force    # AST, ZERO LLM, segundos, idempotente. Ausente → cria; fresco → no-op.
python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/pattern_check.py)" --project-root "<root>" --touch-plan --json
```
O touch **documenta** ⇒ é modo PESADO na regra do grafo (canônica: `skills/doc/SKILL.md` → Workflow Engine → Passo 0): doc nova nunca sai de grafo velho. Rode sem anunciar custo nem pedir confirmação — só informe o status. `graphify` não instalado ⇒ **avise e siga** (a re-projeção vem do diff, não do mapa; o touch não consome `graph_map`).
Devolve `{changed, docs:{doc:{files, already_current}}, pending_docs, seam_review, unscoped_new, dead_scope, ledger_last_commit, last_full_age_days}`. O `changed` = working tree ∪ staged ∪ `ledger.last_commit..HEAD` (mesma janela do backward-delta do journal, **lida read-only**). ⚠️ `git diff` **não lista untracked** — arquivo novo só entra no `changed` depois do `git add`.

**Escalada touch → FULL: decida AQUI, antes de re-projetar nada.** Quem chama o touch (o usuário, ou a `/sprint`) não tem como saber se o caso pede FULL — a informação nasce neste passo. Um sinal só, e ele é mecânico:

- **`last_full_age_days > 30`** (ou `null` — ledger ausente/ilegível/SHA órfão, ou seja "não sei") ⇒ **escale pro FULL**. Em modo autônomo (`/sprint`, headless) escale **e siga**, sem perguntar: sugerir não serve pra quem não está lendo. Em modo interativo, diga o número e pergunte.
- Caso contrário ⇒ **touch**, que é o caminho normal.

O campo existe porque **o FULL é o único que avança `ledger.last_commit`** (o touch é read-only nele), então a data desse commit *é* a data do último FULL.

⚠️ **Não invente um segundo critério.** `unscoped_new` e "arquivo fora do scope de todo doc" **não** servem de gatilho, e a tentação é real: o primeiro exige, por definição, que o arquivo esteja num diretório **já coberto** (então acusaria FULL a cada `test_*.sh` novo), e o segundo é alto num repo **saudável** (os `scope:` são seletivos de propósito — medido: 41 de 79 arquivos mudados neste repo, com o touch sendo claramente a escolha certa). Mecanizar "isso é estrutural?" produz heurística com cara de determinismo — o precedente do repo é o `commits_after > 0 or edits_after >= 3`, que era código e carimbava plano de 10 fases como executado.

**Trabalhe sobre `pending_docs`, não sobre `docs`.** `docs` lista tudo que o diff toca; `pending_docs` exclui os que já absorveram a mudança (doc mais novo que os arquivos). Sem isso o touch repetido vira no-op — enquanto o trabalho não é commitado, o `git diff` segue mostrando os mesmos arquivos. `pending_docs` vazio → reporte "nada a tocar" e pare.

### 2 · Re-projeção escopada, por doc
Para cada doc do plano (sequencial se ≤3; subagentes paralelos se mais): o agente recebe **o doc atual + SÓ os arquivos mudados do scope + o diff deles** (`git diff <ledger_last_commit> -- <files>` + working tree) e:
- Atualiza **apenas as seções afetadas pelo diff**; preserva o resto intocado (não reescreve, não "melhora").
- Obedece as **Regras de escrita assertiva** do SKILL grande (`skills/doc/SKILL.md` → Rules): nome/número/lista só por derivação mecânica no run; ponteiro = arquivo+símbolo; "ativa" exige evidência de wiring; costura citada existe nos dois lados.
- Fato durável genuinamente NOVO que entrou na doc → anotar para o passo 4.

### 2b · Diagramas das camadas atingidas (o `/archify` acompanha a doc)

Texto e desenho descrevem a mesma coisa; deixar um se atualizar sem o outro é como o
diagrama envelhece até virar mentira ilustrada. O gatilho é **o doc que foi re-projetado no
passo 2**, não uma varredura nova — o escopo inverso já fez o trabalho:

| Doc re-projetado | Diagrama a re-renderizar |
|---|---|
| `architecture.md` | `organismo.html` |
| `runtime.md` | os `fluxo-<slug>.html` dos fluxos cujos títulos o diff tocou — re-renderizados em **`.claude/docs/fluxos/`**, a casa canônica VERSIONADA (decisão do dono em 2026-08-13): fluxo é doc, entra no commit de conteúdo do passo 5, nunca em pasta de sessão |
| doc de um aplicativo (monorepo) | `app-<nome>.html` daquele aplicativo |

Para cada um, o ciclo da skill `archify` (invoque-a com a Skill tool — as camadas, os nomes
estáveis e o destino estão lá; não os redigite aqui):

```bash
ARCHIFY_DIR=$(bash <plugin archify>/skills/archify/resolve-dir.sh "$PWD" archify)
node <plugin archify>/skills/archify/bin/archify.mjs render architecture <entrada>.json "$ARCHIFY_DIR/organismo.html"

# Fluxo tem casa própria e versionada — o resolve-dir aceita subdir com barra:
FLUXOS_DIR=$(bash <plugin archify>/skills/archify/resolve-dir.sh "$PWD" docs/fluxos)
node <plugin archify>/skills/archify/bin/archify.mjs render workflow <entrada>.json "$FLUXOS_DIR/fluxo-<slug>.html"
```

⚠️ O HTML que nasce em `.claude/docs/fluxos/` é **rastreado no git** — vale a régua do repo
público: sem caminho absoluto de máquina dentro dele (a checagem H do release-gate reprova).

**O JSON de entrada é derivado do doc que acabou de ser re-projetado**, não do código cru: o
doc é a leitura já curada da arquitetura, e desenhar direto do código reintroduz o palpite
que o doc existe para evitar.

`archify` ausente (o plugin não está instalado) ⇒ **avise e siga**, mesmo padrão do
`graphify` no passo 1. Diagrama é camada a mais sobre a doc, nunca pré-requisito dela.

Nome estável significa **sobrescrever**: um assunto, um arquivo, sempre o atual. Não
versione diagrama de documentação viva por data — ver a tabela de nomes na skill do archify.

### 3 · Gate doc-lint (determinístico, antes do re-stamp)
```bash
python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/doc_lint.py)" --project-root "<root>" --docs <docs tocados> --json
```
FAIL → corrigir com a evidência que o próprio lint dá e re-rodar (máx 2 iterações; persiste → reportar FAIL, não silenciar). Falso-positivo legítimo (var dinâmica, config externa) → `<!-- lint:ignore TOKEN -->` ou `.claude/.project-doc/lint-allow.txt`, com justificativa no report.

### 4 · Journal
- Journal (disciplina do FULL, nunca relaxar): `journal.py adopt` **só** de fato durável genuinamente novo (nunca adopt do que já está vivo); `journal.py invalidate` **só** contradição frontal com evidência arquivo:linha.
- **PROIBIDO rodar `journal.py update`** — avançaria `ledger.last_commit` e queimaria o backward-delta do próximo FULL. O ledger pertence ao FULL; o touch é read-only nele.
- **NÃO carimbe nada aqui.** O carimbo é o passo 5, e ele vem **depois** do commit — pelo motivo do ovo-e-galinha abaixo.

### 5 · Report + o rito de DOIS commits (não é opcional)

Report curto primeiro: docs tocados (com o quê) · `seam_review` (costuras tocadas — verificar se o claim do OUTRO módulo mudou) · `unscoped_new` (arquivos novos em dirs cobertos — oferecer adicionar ao `scope:` do doc certo, **ou ao `verified-by:` se for suíte de teste**) · `dead_scope` (renames) · **idade do último FULL** (`last_full_age_days`, já decidida no passo 1 — aqui é só relatar o número).

**Por que dois commits, e por que não dá pra ser um:** o carimbo `generated-commit:` diz "esta doc vale pro estado do código no commit X". Quando código e doc entram no **mesmo** commit, X ainda não existe no momento de escrever o frontmatter — então o carimbo aponta pro commit anterior, a janela de staleness enxerga a mudança que a **própria doc acabou de descrever**, e o hook do SessionStart passa a gritar "⚠️ DEFASADA" sobre doc recém-nascida. **Um doc não consegue citar o commit que o contém.** Este repo pagou isso 3× (`16211ae`, `b9028c3`, `8d7a5a0`) antes de virar comando.

```bash
PC="$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/pattern_check.py)"

# 1º commit — o CONTEÚDO (código, se houver, + os docs re-projetados + journal + grafo)
git add <arquivos tocados> .claude/docs/<tocados> .claude/docs/fluxos/<re-renderizados> .claude/.project-doc/findings.jsonl graphify-out/
git commit -m "..."          # nunca `git add -A`

# 2º commit — o CARIMBO, apontando pro commit que acabou de nascer
python3 $PC --project-root . --restamp .claude/docs/<tocados>
git add .claude/docs/<tocados> && git commit -m "docs: re-stamp pro commit do conteúdo"

# confira: os dois medidores têm que concordar em `fresh`
python3 $PC --project-root . --project-staleness .
```

O `--restamp` faz o que antes era receita de `sed` pra lembrar: `generated:` = hoje, `generated-commit:` = HEAD, `doc-sig:` recomputada **do corpo final** e **preservando a gen do doc-set** (lida do marker do `CLAUDE.md`, não o `CURRENT_GEN` do código — o `--sig` cru bumpa a gen e viola o invariante "Gen NÃO bumpa"). Ele **pula** doc autoral (`authored-by: human`) e arquivo sem frontmatter, e **falha sem escrever nada** se não resolver o HEAD — carimbo pela metade é pior que carimbo velho. Passe **só os docs que você re-projetou**: carimbar doc que ninguém tocou escreveria `generated: hoje` sobre trabalho que não aconteceu.

Push seguro: `git fetch` antes, confirme fast-forward (`git merge-base --is-ancestor origin/<branch> HEAD`), **nunca `--force`** — o `session-sync` do bootstrap disputa esse push.

O que entra nos commits: só os artefatos de doc — docs tocados, `findings.jsonl` e **`graphify-out/` se existir** (o `.gitignore` do projeto é quem exclui `cache/` e os paths de máquina; o `graph.json` é versionado) — mais o código, se esta rodada mexeu em código. **Nunca `git add -A`.** O touch preserva o resto do doc, inclusive erro pré-existente: é complemento do FULL, não substituto.

## Invariantes (não-negociáveis)

- **Doc autoral é INTOCÁVEL.** Arquivo com `authored-by: human` no frontmatter (`quality-goals.md`,
  `constraints.md`, `context.md`, `solution-strategy.md`, `glossary.md`, `decisions/*.md` — território
  do `/start`) **nunca é re-projetado, nunca ganha `scope:`, nunca é re-stampado**. Se um aparecer
  no plano, **pule e reporte**. Hoje a proteção é indireta — o `scope: []` vazio o mantém fora do
  `touch-plan` —, mas o passo 5 manda corrigir `dead_scope` e adotar `unscoped_new` no `scope:` do doc
  certo: popular o scope de um autoral quebraria a trava **para sempre e em silêncio**. Antes de
  mexer no `scope:` de qualquer doc, cheque o `authored-by:`. (Achado da revisão de 2026-07-26.)
- **Ativo novo exige linha de durabilidade (gen 3.8).** Se `data-stores.md` está entre os docs
  tocados, confira que todo depósito nele tem bloco correspondente em `durability.md` — é a regra do
  check #24 do FULL, trazida pro touch porque senão um volume novo no compose entra no inventário e
  fica sem cobertura declarada até o próximo FULL (que pode demorar 30 dias). Sem bloco → escreva
  `[TODO: sem cobertura declarada]` e reporte. Silêncio sobre durabilidade é o que a gen 3.8 proíbe.
- **Gen NÃO bumpa.** O touch não invalida docs antigas nem cria campo obrigatório (`generated-commit:` é opcional — ausência não é violação).
- **Grafo em modo PESADO** — o touch escreve doc, então garante o grafo fresco (`graphify update --force`, passo 1), igual ao FULL. O que o touch NÃO faz é *consumir* o mapa: re-projeta do **diff**, sem `graph_map.py`/fan-out. Grafo e doc viajam juntos no commit.
- **Ledger read-only.** Ver passo 4.
- **Nunca re-projetar doc fora do plano.** O touch-plan é o contrato; doc não mapeado não é tocado (nem "aproveitando que estou aqui").
- Secret: as mesmas regras do FULL (nomes SIM, valores NUNCA).
- **Desacoplamento: as mesmas duas trocas do FULL** — contagem cravada sai e entra o **comando** que a
  produz (`grep -c …`, `wc -l`, `python3 …`); lista de nomes de plugin sai e entra o **índice** que os
  enumera (`.claude-plugin/marketplace.json`, `plugins/bootstrap/config/manifest.json`). <!-- acopla-ok: o manifest é citado como ÍNDICE a consultar, não como dependência executável --> A regra é
  escrita uma vez só, na seção **"Desacoplamento — duas trocas obrigatórias em TODO doc escrito"** do
  `SKILL.md` do `/doc`; leia lá antes de re-projetar. Quem cobra é
  `python3 scripts/desacoplamento_check.py`; a isenção é `acopla-ok: <motivo>` na linha. O touch toca
  poucos docs por rodada — é justamente onde a contagem velha sobrevive despercebida.

## Output Protocol

```
**Touch 1/5:** grafo {criado | atualizado | já fresco | graphify ausente} · plano → {N} arquivos mudados → {M} doc(s) afetado(s) [+ costuras: {ids}] · último FULL há {D} dias → **{touch | ESCALEI PRO FULL}**
**Touch 2/5:** re-projeção → {doc}: {seções atualizadas}
**Touch 3/5:** doc-lint → {ok | X FAILs corrigidos | FAIL persistente: ...}
**Touch 4/5:** journal ({adopts} adoções, {invs} invalidações) · ledger intocado
**Touch 5/5:** conteúdo <hash1> + carimbo <hash2> ({M} doc(s) via --restamp) · staleness: por-doc {X} · agregado {Y} · último FULL há {N} dias{ — sugerir /doc se >30}
```
