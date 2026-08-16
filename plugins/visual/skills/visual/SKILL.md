---
name: visual
description: Use when the user invokes `/visual` (with or without flags like `-auto-off`, `-auto-on`, `-status`), asks to "ver isso no HTML", wants a visual presentation of a plan/diagnostic/question, or when the PreToolUse hook `pre-exitplan-visualize.sh` on ExitPlanMode blocks. ALSO invoke PROACTIVELY when auto mode is on (read the current value in `~/.claude/visual-state/config.json`) and you're about to emit a plan with 3+ items, a decision with 2+ options, a diagnostic with 3+ problems, or a long explanation (40+ lines / 3+ sections). The page MUST carry the evidence, not the account of it — the real artifact embedded, the raw output verbatim, the provenance of every number. Generates a dark-theme HTML inside the project's `.claude/visual/` (falls back to `~/Desktop/claude-visual/` outside a project), spawns a local daemon for live-sync back to Claude (the user types "ok" and Claude reads state from disk — no copy/paste), and opens it in the browser. Replaces 20-page CLI dumps with scannable visual surfaces — artifact and evidence first, decision on top of the fold, technical details collapsed below. PLANO/PRD/roadmap tem caminho próprio e obrigatório: o plano vira ARQUIVO em `.claude/plans/<id>.plan.json` (ids fixos, uma linha didática por passo), é apresentado como ÁRVORE desenhada pelo programa (`lib/plan_state.py page`), e daí em diante só é MARCADO (`tick`, que exige prova) — nunca reescrito nem renomeado. Um hook de SessionStart ressuscita o plano aberto depois do /clear e do handoff.
---

# Skill: /visual

Turn walls of CLI text into a scannable HTML surface. Dark theme, opens in browser.

## Passo 0 — INEGOCIÁVEL: leia as lições, e faça o juiz ler a página

Você **não é juiz confiável da clareza da própria página.** Isso foi medido, duas vezes na
mesma sessão (2026-08-06): a primeira versão pediu decisão sobre quatro peças sem mostrar
nenhuma delas — *"você só me pediu pra decidir coisa com base em bola de cristal"* —, e a
segunda, escrita para consertar a primeira, empilhou referência sobre referência — *"uma
coisa recursiva a outra, recursiva a outra, e num português filho da puta de
incompreensível"*. Nas duas você tinha lido e concluído que estava claro.

Daí as duas metades, e **as duas são obrigatórias**:

**(a) ANTES de escrever o spec, leia o banco de lições:**

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/lib/clareza.py licoes
```

São os erros que um leitor externo já reprovou nas suas páginas, cada um com a regra que
o impede e o teste que você aplica sozinho. Os termos marcados como recusados o
`visual_page.py build` **rejeita** — o resto é julgamento seu, e é onde você erra.

**(b) DEPOIS de construir e ANTES do `open`, mande um juiz ler.** Um subagente **Haiku**
(barato de propósito), com esta instrução: *você é um programador experiente que nunca viu
este projeto nem esta conversa, e só tem esta página. Você já sabe o vocabulário corrente
da área; o que você não sabe é nada do que foi construído aqui. Leia com a paciência de
uma criança de 5 anos: frase que você precisa reler duas vezes já falhou.* Para **cada**
decisão ele responde: o que estou sendo pedido para escolher · qual a diferença entre as
opções · **ENTENDI ou PERDIDO**, e qual trecho exato o perdeu.

Qualquer **PERDIDO** ⇒ a página **não abre**. Conserte e mande de volta ao mesmo juiz.

Ele julga **dois eixos**, e reprova em qualquer um dos dois.

**Eixo 1 · o que a página deixou de contar.** A falta é sempre a mesma, o CONTEXTO, nunca
a definição de dicionário:

- **Identificador no lugar da coisa** — passo, requisito, artigo, arquivo ou achado citado
  pelo nome curto sem dizer, na mesma linha, o que ele é. Pediram para dizer o que falta e a
  página respondeu "falta o passo 3": o endereço, não a coisa.
- **Metáfora, apelido ou nome batizado** usado como se explicasse a coisa.
- **Referência indireta** — "o motor", "a régua", "aquela ponte", "o approach atual" — sem
  dizer que coisa concreta é essa.
- **Peça deste código** (arquivo, comando, campo, etapa) citada sem dizer **onde ela entra
  no fluxo, o que ela faz e para que existe**. O nome dela não é a explicação dela.
- **Escolha que exige saber algo que não está na própria página.**

**Eixo 2 · como a página está escrita.** Aqui a criança de 5 anos manda por inteiro, e a
régua é a frase simples: sujeito, verbo, complemento, nessa ordem, uma ideia por frase.

- **Frase truncada** — sem sujeito, sem verbo, ou cortada no meio para caber.
- **Texto que parece equação** — `A → B → falha`, `x = y`, seta, barra e sinal fazendo o
  trabalho que a palavra devia fazer.
- **Ordem invertida** — o predicado antes do sujeito, a oração encaixada no meio, a
  condição pendurada no fim.
- **Abreviação e sigla** que economizam letra e cobram releitura.
- **Período longo demais** — duas ou mais orações empilhadas onde caberiam duas frases.

**O que NÃO reprova**, e o juiz é instruído a deixar passar sem comentar: vocabulário
corrente de programação e de agentes de IA. Contexto, agente, subagente, plugin, skill,
hook, barra de status, commit, log — quem lê a página já usa essas palavras todo dia.
Pedir definição delas foi o defeito da régua anterior, que aplicava a criança de 5 anos ao
vocabulário também: a página passou a abrir com uma lista definindo o óbvio antes de
chegar à pergunta. A criança continua valendo para a FORMA; ela nunca valeu para o
repertório.

**A prova crua é isenta do eixo 2.** Saída de comando, `arquivo:linha` e trecho de código
entram literais — "humanizar" a prova é falsificá-la.

**(b2) Terminada a leitura, o parecer do juiz vira PÁGINA PRÓPRIA — gere sem perguntar.**
Não pergunte se o dono quer ver; não despeje o veredito no chat. Monte um spec com um item
por decisão (o que foi pedido para escolher · a diferença entre as opções · ENTENDI ou
PERDIDO · a palavra que perdeu) e rode `visual_page.py build --spec <f>` com `slug` próprio
(`parecer-<slug-da-página>`), depois `open`. A página julgada e a página do parecer são
duas: misturar as duas esconde a reprovação dentro do que ela reprovou.

**(c) Aprovou? Registre o que ele ensinou**, para o erro não voltar na página seguinte:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/lib/clareza.py registrar --json licoes-novas.json
```

Peça ao juiz, junto do veredito, os **padrões** por trás dos erros (não os erros um a um):
`{"licoes": [{"id": "...", "nome": "...", "erro": "...", "regra": "...", "teste": "...",
"banido": ["..."]}]}`. Em `banido` entra **só o que é jargão seu ou palavra de dois
sentidos** — termo que o dono usa no dia a dia vira regra de julgamento, não recusa
automática, senão o gate começa a reprovar o vocabulário dele.

Sem (a) o juiz reprova o mesmo erro toda vez. Sem (b) ninguém pega o erro que ainda não
está no banco. Sem (c) o veredito morre no chat. Suíte: `python3 lib/test_clareza.py`.

## Mostrar, não descrever — a regra que manda em todas as outras

A página **carrega a prova, não o relato da prova.** O usuário tem que ver na própria página as mesmas coisas que você olhou quando formou a conclusão. Dito do lado de quem decide:

> Ele precisa ver **o que você viu** que te fez pensar o que você pensou e que está te fazendo pedir pra ele decidir uma coisa. Se você não mostrar — não é explicar, nem descrever, é **MOSTRAR** o que você viu durante a tua análise — ele não tem como fazer nada.

**Referente pendurado é o defeito.** Toda vez que a página se apoia em algo — uma coisa que existe, uma coisa em discussão, uma premissa, uma conclusão anterior, "o approach atual" — esse algo é um ponteiro. Ponteiro sem alvo na página é pedir bola de cristal. Três classes e o que "mostrar" significa em cada uma:

- **Coisa que existe** (slide, tela, deck, arquivo, código) → embutida (`.artefato` + `<iframe src="file:///caminho/real">`) ou citada literal com `arquivo:linha`. Testado: caminho absoluto cross-dir renderiza no Chrome.
- **Número ou afirmação medida** → o output cru que a produziu, verbatim, em `.evidencia`, com o comando que gerou. Não "medi e deu +155%": as linhas que você leu, com n, com as duas amostras.
- **Premissa, conclusão anterior, coisa em discussão** → a passagem literal (quem disse, onde), o commit, o trecho do plano. Sem fonte no disco, rotule **INFERIDO** — nunca apresente como fato.

### Pediram para DIZER o que é — então diga o que é, não o nome dela

**Menção não é apresentação.** Quando o pedido é dizer o que alguma coisa é, explicar
alguma coisa ou apresentar alguma coisa, cumprir é **mostrar a coisa** — nunca devolver o
identificador dela e seguir em frente. Perguntaram o que falta no plano: *"falta o passo 3"*
não responde nada; responde *"falta o passo 3, que é escrever o cobrador dos três desfechos
do relatório"*.

Vale para tudo que tem nome curto e conteúdo longo — passo de plano, requisito, artigo da
lei, achado, arquivo, decisão, comando. O identificador é o endereço, não a coisa: quem lê
não tem como abrir o endereço enquanto lê a página.

**A régua, e ela é a mesma na elaboração e no julgamento:** todo identificador aparece com
o que ele é, em palavras de gente, **na mesma linha**, na primeira vez que aparece. O teste
é o de sempre — tape o resto da página; a frase sozinha diz o que aquilo é, ou só diz como
aquilo se chama?

Isto é o **referente pendurado** aplicado ao ato de responder: a lista dos itens é o
esqueleto, e o esqueleto sem a carne obriga o leitor a ir buscar em outro lugar o que a
página existia para trazer.

### A forma da página de decisão

Dez linhas de leitura até a decisão. Nessa ordem:

1. **Faixa de identidade** (`.ident-strip`) — projeto, artefato **pelo título visível** (nunca por id interno), e o **estado** dele: rascunho, gerado, no ar, já apresentado.
2. **O artefato**, embutido.
3. **4-5 bullets** — do que se trata e o que ele afirma.
4. **A evidência crua** (`.evidencia`) — com procedência: comando · arquivo · quando.
5. **2-3 bullets** — qual é o problema.
6. **A decisão**.

O aprofundamento vai em `<details>`: disponível, não empurrado. Se ele quiser mais, pede.

**Não é concisão, é especificidade.** Os dois extremos reprovam igual: o textão que enterra o insumo, e o lacônico que não deixa decidir. O critério é o insumo crucial da decisão estar lá, e nada além.

### Ordem de construção: pergunta primeiro, prova filtrada depois

A causa da recaída é a ordem. Você termina a análise, tem a conclusão na cabeça, e escreve a página de trás pra frente — a evidência fica no scrollback e parece "trabalho já feito", então vira resumo.

Inverta: **escreva a pergunta da decisão antes de qualquer coisa**, liste o que muda a resposta dela, e só isso entra na página. Se não há prova pra colar, não há decisão a pedir — há investigação a fazer.

### Proibido fabricar o "depois"

Se a versão corrigida não existe, **não monte uma** por find-and-replace, mock-up ou edição manual. Mostre o artefato **real de hoje** + a medição do que seria, rotulada como **sua medição**, nunca como saída do motor/sistema. Artefato fabricado ao lado do real é indistinguível pra quem lê.

### Afirmação que cria pressa tem que ser checada

"Já foi apresentado ao cliente", "está no ar", "o cliente viu", "isso quebra em produção" — toda afirmação que cria urgência enquadra a decisão inteira. Cheque no disco **nesta sessão** antes de escrever, ou rotule INFERIDO. No caso que originou esta regra, a afirmação era falsa e era ela que criava a urgência.

### A página apresenta o que é daqui, e só isso (non-negotiable)

**Glossário de abertura está proibido.** Definir "plugin", "agente", "hook" ou "barra de
status" antes da pergunta não ajuda ninguém: quem lê usa essas palavras todo dia, e a lista
só empurra a decisão para baixo da dobra.

O que precisa de apresentação é o que **só existe aqui**: metáfora, apelido batizado,
referência indireta, e peça deste código. E a apresentação não é a definição — é o
**contexto**, na primeira vez que a coisa aparece, na mesma frase ou logo abaixo dela:
**onde ela entra no fluxo · o que ela faz · para que existe**. Dizer que o arquivo se chama
`clareza.py` não apresenta o `clareza.py`; dizer que ele é o passo que roda antes de gerar a
página e recusa termo já reprovado, sim.

**E uma palavra por coisa.** Escolhida a palavra, varra o spec inteiro e mate as
concorrentes — a única exceção é a primeira menção, onde apresentar as duas juntas
("plugin, ou pacote, é a caixa que se instala") é a forma certa. Depois dela, alternar
entre sinônimos faz o leitor procurar uma diferença que não existe.

### As 4 conferências mecânicas — o build as roda sozinho

Ele **não julga clareza** — isso continua sendo do juiz externo. Ele procura os quatro
defeitos que já reprovaram páginas e que dá para achar por programa: dois nomes para a
mesma coisa · apoio em escolha que não está na página · custo sem dizer custa o quê ·
prova colada sem dizer o que ela estraga.

**Você não precisa lembrar de chamá-lo**: o `visual_page.py build` o roda em toda página e
imprime os pontos no stderr. Eles **avisam, não recusam** — a `.evidencia` que fecha um
capítulo, por exemplo, é legítima, e o julgamento continua seu. Para conferir antes de
gastar um build:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/lib/clareza.py revisar --spec pagina.json
```

Por que ele existe, se as lições já existem e o juiz já lê: em 2026-08-08 uma página
reprovou nas três decisões, e **duas das quatro lições que a reprovaram já estavam no
banco**. Ler 60 lições no começo não é conferir 60 lições no fim. E por que o **build** o
chama, em vez de um passo escrito aqui: pela mesma lição — regra em prosa não pega.

### Autoteste antes de abrir o browser

Releia como se nunca tivesse visto a conversa:

1. **Cadê o artefato?** A coisa de que a página fala está embutida ou citada literal? "Eu descrevi" reprova.
2. **Cadê a saída?** Todo número aponta pra um bloco de evidência **nesta mesma página**? Número sem origem reprova.
3. **Cadê o endereço?** A página nomeia projeto, artefato pelo título visível, e o estado dele?
4. **A urgência foi checada?** Toda afirmação que cria pressa foi verificada nesta sessão?
5. **Dá pra decidir sem jargão?** Você consegue dizer o que aprova, por quê, e o que cada caminho custa — só pelo card?

O teste de aceitação real: se a primeira reação do usuário for **"do que você está falando?"**, "onde?", "qual?" ou "me mostra" — a página falhou, por melhor escrita que esteja.

## When to invoke

- **Explicit**: the user types `/visual`, says "faz visual disso", "preciso ver no HTML", "joga pro browser".
- **Toggle commands** (handled inside this skill, NOT regenerating):
  - `/visual -auto-off` — disables auto mode. Writes `auto_mode: false` to config.json.
  - `/visual -auto-on` — re-enables auto mode. Writes `auto_mode: true`.
  - `/visual -status` — prints current config and returns.
  When the user passes any of these flags, DO NOT generate a visual — just update config and confirm in CLI.
- **Auto mode** — **leia o `config.json`, não presuma o valor** (o default de fábrica é `true`, mas o usuário liga e desliga; hoje pode estar `false`). Se `~/.claude/visual-state/config.json` tem `auto_mode: true`, invoque esta skill sozinho sempre que for emitir:
  - A plan (numbered items, 3+ steps)
  - A decision with ≥2 options
  - A diagnostic with 3+ problems
  - A long explanation (≥40 lines of prose or ≥3 sections)
  Threshold numbers come from `auto_triggers` in config.json. The user can tune them by editing the file directly or by saying "aumenta o threshold pra X".
- **Auto-triggered (gate-blocked)**: the PreToolUse hook `pre-exitplan-visualize.sh` on `ExitPlanMode` blocks with exit code 2 and tells you to render the plan as HTML before the plan is shown to the user. The plan is meant to be READ in the browser, not in the CLI. This hook fires regardless of auto mode (plan mode is always visualized).
- **Explicit override when auto is off**: if `auto_mode: false`, wait for the user to type `/visual` or ask explicitly. Do NOT proactively generate.

**Decision tree at start of skill invocation:**

```
1. Read ~/.claude/visual-state/config.json (seed it from the default if missing — see below)
2. Parse args from the /visual command:
   - If "-auto-off" → update config, write, confirm, STOP.
   - If "-auto-on"  → update config, write, confirm, STOP.
   - If "-status"   → print config, STOP.
3. Otherwise → generate visual as normal.
```

**O arquivo vive FORA do plugin**, em `~/.claude/visual-state/config.json`, porque
`${CLAUDE_PLUGIN_ROOT}` é cache reescrito a cada bump — estado mutável ali dentro some
silenciosamente na atualização (regra do repo, `architecture.md §11`).

Ausente? Semeie a partir do default versionado, que é a **única** fonte dos valores de
fábrica (não redigite os números aqui):

```bash
mkdir -p ~/.claude/visual-state
cp "${CLAUDE_PLUGIN_ROOT}/skills/visual/config.default.json" ~/.claude/visual-state/config.json
```

## Plano, PRD, roadmap → o arquivo do plano manda (non-negotiable)

Esta é a regra que ataca a perda relatada pelo usuário em uso real: *"os planos eram dados como concluídos e não tinham sido concluídos de fato… a gente teve que reminerar as sessões anteriores dezenas de vezes"*.

A causa não é falta de disciplina, é arquitetural: até aqui o plano só existia na **conversa**, e todo consumidor (o `/handoff`, o próximo `/visual`, a próxima sessão) o **re-derivava por LLM**. Re-derivação por LLM encurta, renomeia fase e chuta conclusão. O `/handoff` guardava `txt[:1200]` e decidia "já executado" com `commits_after > 0 or edits_after >= 3` — 1 commit carimbava um plano de 10 fases como pronto.

**A correção: o plano vira ARQUIVO, e você o escreve UMA VEZ.**

### O ciclo, inteiro

```bash
PS="<plugin project-skills>/lib/plan_state.py"

# 1. na APRESENTAÇÃO do plano — grava o arquivo (uma vez) e monta a página
python3 $PS init --file plano.json
python3 $PS page --mode approve          # imprime o caminho do HTML
open "$(python3 $PS page --mode approve)"

# 2. a CADA passo concluído — só marca. A prova é obrigatória.
python3 $PS tick F2.3 --evidencia "python3 lib/test_x.py -> 12 OK · a1b2c3d"
python3 $PS state F3.1 doing            # opcional: sinaliza o que está em curso

# 3. mostrar onde a execução está — a MESMA página, reescrita
python3 $PS page --mode track

# 4. no fim
python3 $PS close

# a qualquer momento — os mesmos 1-3 bullets que o hook de fim de turno mostra
python3 $PS brief
```

### As três regras que fazem o plano não se perder

1. **Você escreve o plano UMA vez, no `init`.** Depois disso **nunca** redigita um título. O `init` num plano existente **recusa** título diferente para um id que já existe — renomear de propósito exige `--rename <id> "<novo>"`. É isso que impede a fase de mudar de nome entre uma sessão e a seguinte.
2. **Quem desenha a árvore é o programa**, lendo o arquivo. Nunca escreva `.plan-tree` à mão, nunca monte a página do plano splice-ando o template você mesmo — use `page`. Se você remontar o cabeçalho a cada rodada, o plano muda de aparência, que é metade da queixa original.
3. **`tick` exige prova.** Comando que rodou + saída, `arquivo:linha`, ou sha do commit. Sem isso o tique é recusado. "Concluído" sem prova é palpite, e palpite foi o que quebrou.

### O formato do arquivo

```json
{
  "id": "2026-07-27-slug-do-plano",
  "title": "O plano em uma linha",
  "requisitos": [
    {"id": "S-1.1", "titulo": "O que o sistema deve fazer",
     "ca": "como se sabe que ele faz"}
  ],
  "phases": [
    {
      "id": "F1",
      "title": "Nome da fase — humano, não técnico",
      "detail": ["🔧 Como: …", "💡 Por quê: …", "📁 Toca em: …"],
      "items": [
        {"id": "F1.1", "title": "o passo, pode ser técnico",
         "desc": "UMA linha didática do que ele faz — é o que aparece na árvore",
         "requisito": "S-1.1", "pronto": "`python3 lib/test_x.py` sai 0"}
      ]
    }
  ]
}
```

Este bloco grava como está: `requisito` e `pronto` são **obrigatórios** em toda tarefa
nova (ver "Os campos da tarefa"), e o id citado tem que existir na fonte de requisitos —
por isso o exemplo carrega o bloco `requisitos` junto. Onde os requisitos já moram noutro
lugar (`docs/PRD.md`), o bloco sai e o `requisito` cita o id de lá.

- `id` de fase casa `F<n>`; de passo, `F<n>.<m>` com o prefixo da própria fase. **O id é a identidade** — é por ele que se diz "tica o F2.3".
- `desc` é **obrigatório e no máximo 140 caracteres**. O título pode ser técnico; a linha de baixo, nunca. Um parágrafo ali é recusado pelo schema.
- `detail` é opcional e só aparece na página de **aprovação**, dentro do `<details>` da fase.
- Estado (`status`, `evidence`, `done_at`) é do programa — não escreva à mão.

### Duas páginas, nunca as duas juntas

| Modo | Quando | Forma |
|---|---|---|
| `--mode approve` | uma vez, quando o plano é apresentado | a árvore **é** a lista: cada fase é um `.feedback-item` com ✓/✏️/✗ |
| `--mode track` | a cada avanço | só leitura, zero rádios, a prova de cada passo feito |

Isso respeita a regra "existe exatamente UMA lista" (ver "Feedback channel" abaixo): **nunca** ponha uma árvore no topo e os itens revisáveis embaixo — são as duas tabelas proibidas. Aprovar e acompanhar são momentos diferentes, então são páginas diferentes.

### O plano sobrevive ao `/clear` e ao handoff

- `hooks/sessionstart-plan.sh` avisa no começo de toda sessão que há plano aberto, com o progresso e a fase em curso.
- `hooks/stop-plan-status.sh` resume o progresso ao fim de **cada turno** (1-3 bullets vindos de `plan_state.py brief`), e dá a confirmação inequívoca quando o plano fecha. Se a sessão editou 3+ arquivos e não marcou nada, a cobrança entra **no lugar** do bullet "Falta" — o teto de 3 bullets nunca é estourado. Nunca bloqueia. Desliga com `PLAN_STATUS=0` (tudo) ou `PLAN_NUDGE=0` (só a cobrança).
- O `/handoff` lê `.claude/plans/*.plan.json` **antes** do `last_plan` do transcript, e usa os ids e títulos exatos do arquivo.

**Retomando trabalho?** Rode `python3 $PS render --format text` antes de qualquer coisa. Não reconstrua o plano de memória.

## Os quatro níveis, e onde cada um mora

```
▸ E9  Cockpit                              13 req · 22 tarefas  6/22  ⛔2
    ▸ S-9.5  Central de integrações · Art. 12    6 tarefas  0/6  ⛔2
        ▸ Tela                                   3 tarefas  0/3  ⛔2
            ○ F5.1  registro declara as 6 fontes             ⛔
```

- **Épico e requisito** são do dono, no documento de requisitos (`docs/PRD.md`). O
  requisito carrega o **critério de aceite** e o **artigo da lei**.
- **Grupo e tarefa** são seus, no arquivo do plano. A tarefa carrega **como se prova**.
- Projeto **sem** documento de requisitos: declare-os num bloco `requisitos` no topo do
  próprio plano, ao lado de `phases`. O requisito é obrigatório; o lugar dele é opcional.

```json
{
  "id": "2026-08-01-meu-plano", "title": "…",
  "requisitos": [
    {"id": "S-1.1", "titulo": "O que o sistema deve fazer",
     "ca": "como se sabe que ele faz", "ancora": "Art. 6", "epico": "E1 — Base"}
  ],
  "phases": [ … ]
}
```

Onde os requisitos são procurados, nesta ordem: **o bloco no próprio plano** → `$PLAN_REQS`
→ `docs/PRD.md` → `docs/REQUISITOS.md` → nenhum (e nenhum **não é erro**).

**A árvore de valor é DERIVADA.** O arquivo guarda fase→tarefa; a vista de quatro níveis é
calculada juntando com os requisitos. Duas árvores sobre os mesmos itens.

**As duas vistas, e como pedir cada uma:**

```bash
plan_state.py render --format text                  # execução: fase › tarefa (o padrão)
plan_state.py render --format text --vista valor    # valor: épico › requisito › grupo › tarefa
plan_state.py page --mode track --vista valor       # a mesma árvore, dobrável, no browser
```

A vista entra no nome do arquivo (`plano-<id>-track-valor.html`), então as duas convivem
sem uma apagar a outra.

## Os campos da tarefa

| campo | obrigatório | o que é |
|---|---|---|
| `requisito` | **sim**, em tarefa nova | o id do requisito. **Exatamente um** — tarefa que atende dois são duas tarefas |
| `pronto` | **sim**, em tarefa nova | como se prova que terminou. Um comando, um `arquivo:linha`, uma tela |
| `grupo` | não | a natureza do trabalho (Backend · Tela · Teste). Você infere; o dono não escreve |
| `pendencia` | não | a decisão que falta. **Trava o tique** e vira ⛔ que sobe a árvore |

### A régua do `pronto` — a origem do valor, não o caminho do arquivo

Um critério mandava o número **aparecer no documento**. O executor obedeceu e escreveu o
número na mão. Quem errou foi o **critério**, não quem executou — e ninguém o julgou antes
de soltar o executor. Por isso a régua é sua, aqui, na hora de escrever o plano:

- **PODE** — regerar o entregável a partir do dado real. É operação do produto.
- **NÃO PODE** — injetar valor inventado dentro do entregável pra o critério fechar. Isso é bancada, e bancada não entra em coisa que vale.

Critério que pede **presença** de algo dentro de um artefato editável à mão (`.md`, `.html`,
relatório, página, planilha) só vale dizendo **de onde o valor vem** — o comando que gera,
regera, deriva ou extrai. Sem isso, escrever à mão cumpre o critério.

| ❌ bancada | ✅ origem declarada |
|---|---|
| `o número de nós aparece no CLAUDE.md` | `` `graphify update --force` regera o índice e o número de nós no CLAUDE.md sai dele `` |
| `o commit é feito, provado por um mock do git` | `` `git log -1 --format=%H` mostra o sha do commit no repositório de verdade `` |

**Efeito fora do processo não se prova fingindo a chamada.** Quando o `pronto` promete algo
que só acontece lá fora — commit, push, arquivo em outra máquina, skill invocada, processo
filho — e a única prova oferecida é o dublê (mock, stub, fake, monkeypatch, simulação), o
verde vem da bancada e o efeito nunca aconteceu. Diga o que **observa o efeito no mundo
real**.

**Critério que manda testar cita o comando e o que é vermelho.** "O teste passa" autoriza
os cinco antipadrões de teste — o contrato deles está em
**`references/antipadroes-de-teste.md`** (fonte: `_shared/antipadroes-de-teste.md` — não
editar a cópia à mão; `scripts/sync-shared.sh --check` pega drift), o **mesmo** arquivo que
o `/qa-loop` lê antes de revisar. Leia antes de escrever um `pronto` que mencione teste:
quem escreve o critério erra antes de quem escreve o teste.

Quem cobra: `lib/regua_pronto.py` (`erros_de_pronto`), chamado pela validação do plano
(`plan_state.py erros_do_plano`) — o `pronto` de bancada **recusa a gravação**, junto da
régua de estilo. Também por linha de comando, para conferir um critério antes de escrevê-lo:
`printf '%s' "$PRONTO" \| python3 lib/regua_pronto.py --onde F2.3 -` (exit 1 = é bancada).

## O fio — três estados, e um quarto que é erro

`plan_state.py cobertura` mostra os dois lados: requisito sem tarefa (pedido que ninguém
planejou) e tarefa sem requisito (trabalho que ninguém pediu). Tarefa citando requisito
inexistente **recusa gravar o plano quando o projeto tem fonte de requisitos** (o bloco no
plano, `$PLAN_REQS`, `docs/PRD.md` ou `docs/REQUISITOS.md`) — sem isso a citação apodrece
em silêncio. **Sem fonte de requisitos a checagem não roda**: o `init` grava, o `brief`
não acusa nada, e conferir vira trabalho seu — rode `plan_state.py cobertura` à mão, ou
declare o bloco `requisitos` no plano e ganhe a recusa de volta.

O número aparece sem ser pedido: na árvore, na tela, no início de sessão, no fim de turno.

### A jornada de origem — a linha `Jornada:` e o casamento com o journeys.md

Funcionalidade que não veio de nenhum caminho de pessoa é trabalho que ninguém pediu com
outro nome. Quem liga uma à outra é **uma linha no requisito**, e o nome tem que ser
**igual ao do título da jornada** no `journeys.md` (o `## <nome>` que a etapa 4 do
`/start-doc` escreve). A comparação ignora caixa e espaço a mais; o resto é literal.

No documento de requisitos, a linha vive ao lado do id, separada por ` · `:

```markdown
- **S-4.3 Orçamento de energia** · F1 · Jornada: Planejar o dia — custo 1-5 por tarefa.
  CA: dia com orçamento estourado retorna proposta de corte com impacto explícito.
```

No bloco `requisitos` do próprio plano, é o campo `"jornada": "Planejar o dia"`, ao lado
de `ca`, `ancora` e `epico`.

Onde as jornadas são procuradas, nesta ordem: `$PLAN_JORNADAS` → `.claude/docs/journeys.md`
→ `docs/journeys.md` → nenhuma. **Projeto sem journeys.md não é acusado**: sem documento
não há com o que cruzar, e acusar todo mundo seria ruído, não cobrança.

Com o documento, o cruzamento roda nas duas direções e aparece **sem ninguém pedir** —
no `cobertura`, no fim de turno, na vista de valor e na página:

- 🔴 **funcionalidade sem jornada** — não cita nenhuma, ou cita nome que o documento não tem
- 🔴 **épico sem jornada** — nenhuma funcionalidade dele veio de caminho de pessoa
- 🔵 **jornada sem funcionalidade** — caminho escrito que nada no plano atende

### A peça onde ela vive — a linha `Peça:` e o casamento com o architecture-intent.md

Do mesmo jeito que a jornada diz de onde a funcionalidade veio, a **peça** diz onde ela
vai morar. Sem essa linha o plano nasce contra a memória de quem o monta, e a contradição
entre o plano e a arquitetura pretendida não aparece em lugar nenhum.

O nome tem que ser **igual ao da peça** no `architecture-intent.md` — o item
`- **{peça}** —` sob a seção `## As peças` que a etapa 2 do `/start-doc` escreve. Só
aquela seção conta: fronteira e depósito de estado são escritos com o mesmo item em
negrito e **não** são peça. A comparação ignora caixa e espaço a mais; o resto é literal.

No documento de requisitos, a linha vive ao lado do id, separada por ` · `:

```markdown
- **S-4.3 Orçamento de energia** · F1 · Peça: Motor de plano — custo 1-5 por tarefa.
  CA: dia com orçamento estourado retorna proposta de corte com impacto explícito.
```

No bloco `requisitos` do próprio plano, é o campo `"peca": "Motor de plano"`.

Onde a arquitetura é procurada, nesta ordem: `$PLAN_ARQUITETURA` →
`.claude/docs/architecture-intent.md` → `docs/architecture-intent.md` → nenhuma.
**Projeto sem o documento não é acusado**, pela mesma regra das jornadas.

Com o documento, o cruzamento sai em duas listas próprias:

- 🔴 **funcionalidade sem peça da arquitetura** — não aponta peça nenhuma
- ⛔ **requisito citando peça que a arquitetura não tem** — aponta uma que o desenho não tem

## Motor de decisão — quando a pendência aparece na execução

| situação | o que fazer |
|---|---|
| interativo, sem parecer | pare e pergunte ao dono |
| interativo, com parecer | pare, **apresente o parecer** e pergunte |
| autônomo, conselho concorda | anote, prossiga, **relate depois** |
| autônomo, conselho diverge | ver "Empate" |
| autônomo, sem necessidade de conselho | decida e registre |

**Por onde a pergunta chega quem escolhe é o usuário** — a régua dos dois canais (página de
decisão em múltipla escolha, ou a ferramenta nativa uma por vez) está em
**`regua-de-pergunta.md`**, ao lado deste arquivo (fonte: `_shared/regua-de-pergunta.md`, cópia
derivada; não editar à mão).

### Régua de escalada — 3 perguntas, qualquer "sim" convoca

1. **É irreversível?** remoto publicado, migração de banco, apagar dado, envio a terceiro.
2. **Contradiz a lei?** bate de frente com o artigo que o requisito cita.
3. **O repositório não desempata?** as opções divergem e nenhuma evidência local decide.

### Empate — por natureza, nunca por contagem de votos

Nem terceiro parecerista, nem você como voto: você escreveu o plano e está implementando.

- **Discordam sobre FATO** → **meça**. Rode e cole a saída. `por: "medicao"`, saída em `prova`.
- **Discordam sobre MÉRITO** → interativo vai pro dono com os dois pareceres; autônomo segue
  a **mais reversível**, `por: "mais-reversivel"`, e a decisão vai pro **topo** do relatório.

### O registro

```json
"decidido": {
  "por": "eu | conselho | medicao | mais-reversivel",
  "quando": "2026-08-01T14:22:00",
  "escolha": "…", "porque": "…",
  "pergunta": "<a pendência original, pra o reabrir restaurar>",
  "parecer": "<resumo dos dois>", "prova": "<saída crua, quando por = medicao>"
}
```

Ao registrar, **apague a `pendencia`** — é ela que trava o tique. O dono derruba com
`plan_state.py reabrir <plano> <tarefa>`.

## A página é EMITIDA por programa, a partir de um spec (non-negotiable)

Mesma decisão do plano, agora pra todas as páginas: **você escreve um spec JSON, o
programa escreve o HTML.** Nunca digite a página inteira.

```bash
VP="${CLAUDE_PLUGIN_ROOT}/lib/visual_page.py"
python3 $VP schema                       # o contrato dos blocos — consulte, não decore
python3 $VP build --spec pagina.json     # imprime o caminho; --out pra forçar
open "$(python3 $VP build --spec pagina.json)"
```

O `schema` é a fonte da verdade dos campos. O resto desta skill governa **o que
entra** no spec — o julgamento —, nunca a forma do HTML.

**O que o programa garante, e você não precisa mais lembrar:** faixa de identidade ·
numeração e `name` único dos rádios · nenhum rádio pré-marcado · `.decisions-box`
quando há decisão e `.feedback-box` quando há item revisável, as duas **recortadas do
`template.html`** · a ordem das duas caixas · a 3ª opção "Outra — eu especifico" ·
escape de todo texto · token de sessão do live-sync.

**O que o programa RECUSA (exit 2, sem escrever arquivo):** decisão ou veredito sem
nenhuma prova na página · bloco de evidência vazio · decisão com 2 ou 4 opções · `tri`
incompleto · `estado` fora do vocabulário. Recusa é mensagem com a lista inteira de
erros de uma vez — conserte o spec e rode de novo.

**A ordem de grandeza, e como ela foi medida.** Numa página de auditoria específica
(2026-07-29), a versão escrita à mão gastava 12390 bytes de markup contra 3141 bytes de
sintaxe JSON no spec que a substituiu. **Não trate isso como fator fixo:** o ganho é só
na estrutura — prosa e saída crua pesam igual nos dois lados —, então página com muita
estrutura (árvore, cards de opção, lista de achados) economiza mais, e página quase toda
texto economiza menos. Se você precisar do número pra uma decisão, **meça a sua**.

O ganho que não varia é o outro: aquela versão à mão usava três classes que **não
existem** no CSS do template (`.exec-title`, `.label`, `.lead`) — defeito silencioso,
porque classe inexistente não dá erro, dá um bloco sem estilo que passa por escolha de
design.

**A válvula:** página excepcional (layout novo, SVG sob medida) usa o bloco
`raw_html`. Use pouco — cada uso é um pedaço que volta a não ter garantia.

Suite: `python3 plugins/visual/lib/test_visual_page.py` (60 checks). Toda regra de
forma que antes era prosa aqui tem um check lá.

## What to render

Detect the content type from the last substantial message or plan file:

| Content type | Shape |
|---|---|
| **Plano / PRD / roadmap** | **Sempre** o arquivo do plano + `plan_state.py page` — ver a seção acima. Nunca desenhe um plano à mão. |
| Plan (numbered items, exec summary) | Decision card + plan items as `<details>` + exec summary at bottom |
| Diagnostic / bloqueios (problems, pendências, riscos) | Cada item em `.tri` — problema · consequência · proposta — com `.sev` no título; "funcionando" section below. **Exceção que manda:** item cuja pendência é uma **pergunta com escolha** que muda a ação de quem lê → `.decision-card`, não `.tri` (ver o teste discriminador em "Bloqueio / problema apontado"). |
| Question with options | Decision card with selectable cards (A/B/C), recommendation highlighted |
| Mixed / generic | Hero + sections + exec summary, following same hierarchy |

## Output location

The visual is saved **inside the project**, not on the Desktop. The target directory is decided by a 3-level cascade (stops at the first that matches):

1. **Git root** — if the cwd is inside a git repo → `<repo-root>/.claude/visual/`
2. **Project marker** — else, walking up from the cwd (stopping before `$HOME`), the first dir holding `package.json` / `CLAUDE.md` / `pyproject.toml` / `Cargo.toml` / `go.mod` / `graphify-out/` / `.git` → `<dir>/.claude/visual/`
3. **Desktop fallback** — nothing found (e.g. running loose in a non-project dir or `$HOME`) → `~/Desktop/claude-visual/`

**Do not hardcode the directory.** Run the resolver and use its stdout:

```
bash ${CLAUDE_PLUGIN_ROOT}/skills/visual/resolve-dir.sh "$PWD"
```

It prints the absolute target dir and creates it (`mkdir -p`). The filename pattern is:

```
<resolved-dir>/YYYY-MM-DD-sess-<session8>-<slug>.html
```

**Session-scoped naming is mandatory when invoked by the pre-ExitPlanMode hook.** The `<session8>` is the first 8 characters of the Claude Code `session_id` that the hook passes to you via stderr. The hook finds the current session's visual by matching `*sess-<session8>*.html` **in the same resolved dir** — if the filename doesn't contain that token, the hook won't recognize it and will block again. When the hook blocks, it already prints the full resolved path in stderr — save exactly there.

For manual invocation (the user types `/visual` outside plan mode), session scoping is optional; a simpler `YYYY-MM-DD-<slug>.html` inside the resolved dir is fine.

Slug = kebab-case of main topic (e.g., `plan`, `diagnostico-cron`, `decisao-arquitetura`).

**Sister folders, same contract.** The page lives in `.claude/visual/`; a written report
(`.md`) goes to `.claude/reports/`, and a screen capture goes to `.claude/prints/`. These
houses are declared in one place only — the "As pastas" table of `contrato-familia.md`
(vendored into the `project-skills` skills). Never invent a folder, and never leave a
report or a capture in `/tmp`.

After writing, always run `open <path>` to show it.

## Hierarchy rules (non-negotiable)

0. **Antes de tudo: de que se trata.** A faixa de identidade + o artefato + a prova vêm antes da decisão. O mecanismo do erro é vívido pra quem acabou de investigar e **inexistente** pra quem vai decidir — nunca abra por ele. A decisão continua dominante, logo abaixo, não no fim da página.
1. **Top**: the decision the user must make. **Uma decisão DOMINANTE no topo** — a principal, grande e visível. "Max 1" é sobre a hierarquia (só uma no topo), **não** o total por página: sub-decisões adicionais têm os próprios cards abaixo (ver "Multiple sub-decisions"). Não reduza uma escolha a `.tri` por achar que há teto de decisões — o teto é de posição, não de quantidade. Every decision carries its own plain-language context line (`.decision-context`) — see "O pedido de aprovação tem que se explicar sozinho" below.
2. **Middle**: context + justification. 3-5 bullets max. Link to concrete data (friction counts, real metrics, file paths) when available. This is section-level background — it does NOT replace the per-decision context line. Both exist: the `.decision-context` says what's at stake for THAT decision; the middle bullets give the broader why.
3. **Bottom**: technical detail in `<details>` collapsed by default. User expands only if they want depth.
4. **Reviewable items carry their verdict INLINE**: every item the user decides on (plan step, benchmark finding, proposed feature) is a `.feedback-item` with its keep/change/remove radios in the item's own header — NOT re-listed in a separate box at the bottom. See "Feedback channel" below. This is non-negotiable: the old "second table of approval" is a forbidden anti-pattern.
5. **Before feedback**: executive summary with 🔧/💡/📁 labels per item.
6. **After `.exec` (when `.decision-card` is present)**: the **Decisions box** — live summary + comments + copy button. Mandatory whenever decision cards exist. See "Decisions channel" below.
7. **After `.exec` (when reviewable items exist)**: the **Feedback box is a CLOSING box only** — progress bar + general observation + the two action buttons. It NEVER re-lists the items. See "Feedback channel" below.
8. **When both exist**: decisions-box comes first (right after `.exec`), feedback-box is last. The CSS `:has()` rule automatically demotes the decisions-box sticky-actions to inline so the two sticky bars don't collide.

If there's no decision pending, skip the decision block — don't fake one.

## O pedido de aprovação tem que se explicar sozinho (non-negotiable)

This skill governs the *container* well (where boxes go, copy semantics, sync). This section governs the thing that was missing: **the language and self-sufficiency of what you're asking the user to approve.** The mechanics being perfect is worthless if the user reads the card and still can't tell what they're signing off on.

This is the most-violated rule. Read it before writing any decision, approval item, plan title, finding, or exec line.

### The reader test (altitude)

The user reads **only the HTML**. Never assume they read the CLI, the plan file, or the code — those don't exist for them at the moment of deciding. After reading a card, if they can't say **in their own words** (a) what they're approving, (b) why they're being asked, and (c) what changes with each choice — the card failed. Rewrite it.

### Every decision / approval item carries three things, in its own body

1. **O quê** — what's being approved or decided. One plain line. This is the title or the `.decision-q`.
2. **Por quê / a premissa** — what prompted it, what's at stake. 1-2 sentences. For a decision card this is the `.decision-context` line (see below). For a plan item it's the first line of the body.
3. **A consequência de cada opção** — what each choice actually causes. One plain line per option (the option's `<p>` or `.tradeoff`). "✔ Robusto · ✘ Polui Desktop" is a consequence; "Opção A" is not.

This mirrors the `perguntas-autocontidas` rule: every decision carries its premises and consequences **in its own body**. A bare label is rejected.

### Bloqueio / problema apontado → sempre `.tri` (problema · consequência · proposta)

**Antes de escolher o componente, o teste discriminador:** se o item carrega uma
**pergunta cuja resposta muda a próxima ação** de quem lê ("mantém as capas ou
reverte?", "prova em tela ou descreve a falha?") → é **`.decision-card`**, com as
opções autorais. Se o item **só informa** uma pendência ou um risco, sem resposta
que mude o que fazer em seguida ("o total está em caixa preta", "a procedência é
desconhecida") → é **`.tri`**. O teste é a existência da escolha, não a sua
confiança nela: na dúvida, se há uma pergunta com resposta que altera a ação,
vire decision-card — cair no tri por "não ter certeza" foi o defeito medido em
2026-08-03 (3 pontos de decisão renderizados como tri no relatório do sprint).

Quando a página aponta um **bloqueio, pendência, risco realizado ou problema** — bloco de bloqueios, seção de achados, relatório final de uma execução — cada item vem no componente **`.tri`**, com as três partes rotuladas, nesta ordem e sem pular nenhuma:

1. **🔴 O problema** — o que está errado ou em aberto, em uma ou duas frases. O fato, não a categoria.
2. **⚡ A consequência** — o que acontece se ficar assim. Concreto: o que quebra, quanto, para quem, com que frequência. Sem consequência, não é bloqueio — é observação.
3. **✅ A proposta** — o que você propõe fazer, e por quê. Se já implementou o caminho conservador, diga isso: "aprovar mantém o que está no código".

No spec é o bloco `tri` (solto) ou o campo `tri` de um `item`. As três partes são
obrigatórias — faltar uma é recusado pelo build.

**A posição é do programa, não sua** — e desde 2026-08-01 a posição mudou: **o problema
fica visível; consequência e proposta nascem FECHADAS**, num dobrador cujo rótulo o
programa escreve com a contagem dentro ("⚡ consequência · 3 bullets"). Você não escolhe o
que dobra e não escreve o rótulo — as duas coisas eram, juntas, o lugar de esconder.

**Consequência e proposta são LISTA de bullets**, não parágrafo. A régua de estilo abaixo
é cobrada pelo build. A prova continua indo no `detail`.

Por que mudou: a regra antiga mandava as três partes ficarem fora do `<details>` para
impedir que um problema fosse escondido. O efeito medido foi o oposto do pretendido —
**89% do último relatório vinha exposto de cara** e o dono não conseguiu ler. O que fica
atrás do clique é a explicação do problema, nunca a existência dele.

Complementos, não substitutos: `sev` (`high`/`med`/`low`) no item quando eles têm
gravidade diferente; o bloco `bullets` com `"problema": true` continua para os 2-3
bullets de "qual é o problema" da página como um todo — não para itens de bloqueio.

### Prosa é PROIBIDA — a régua de estilo, cobrada pelo build

Página gerada é lida com pressa e vem volumosa. **Bullets, nunca parágrafo.** Quatro
checagens, aplicadas a **todo campo de texto** do spec — título, corpo, pergunta,
consequência, proposta, aviso, sumário:

1. **≤ 140 caracteres por bullet.** Marcação (`` `code` ``, `**negrito**`) não conta.
2. **Uma frase por bullet.** Ponto seguido de espaço = parágrafo disfarçado.
3. **Não abra bullet com conectivo de continuação** (`e`, `mas`, `que`, `porque`, `então`,
   `ou seja`, `além disso`). É o parágrafo anterior fatiado — passa no teto e continua prosa.
4. **Máximo 6 bullets por bloco.** Acima disso é prosa picada, ou são dois itens.

**Fora da régua, de propósito:** `evidencia.output` (saída crua é literal por obrigação) e
`raw_html` (a válvula). Estourar não é aviso: o build sai 2 e **não escreve a página**.

O teto não existe para você encolher informação — existe para você **quebrar em bullets**.
Informação que não cabe no nível 0 desce para o nível 1; nada é apagado para caber.

### Human language — banned vocabulary

The text the user reads is for a human, not a log. Forbidden as the visible headline/title/option of what they approve:

- **Code identifiers** as the thing on display: `data-num`, `latest.json`, `postState()`, `state-change`, class names, function names.
- **Internal jargon / category codes**: `wrong_approach`, `buggy_code`, `over-planning`, error codes, enum values, ticket slugs.
- **Agentic / process talk**: "injeta o script após o body", "o parser detecta o marker", "o hook dispara exit 2", "fetch POST pro daemon". The user doesn't approve your process — they approve an outcome.

**Exceção que manda nesta seção: output cru dentro de `.evidencia` NÃO é jargão — é prova.** Esta regra proíbe jargão **no lugar da** prova, nunca a prova em si. Cole a saída literal do terminal, o stack trace, as linhas da query, o trecho de código com `arquivo:linha` — sem parafrasear, sem "humanizar", sem resumir. O que tem que estar em linguagem humana é o **título, a pergunta e as consequências**; o insumo é cru por obrigação.

Allowed: a path or command as **secondary** detail inside `code.inline` (e.g. "salvo em `~/Desktop/...`") — never as the title of what's being approved. If a technical term is genuinely unavoidable, gloss it in one plain phrase right after: "o daemon (o programinha que sincroniza em segundo plano)".

This mirrors the `sem-jargao-proprio` rule and the CLAUDE.md rule: *"Problemas devem ser explicados em 1-2 linhas, em linguagem humana e intuitiva"* — never "somente da forma técnica".

### The two failure modes — and the ruler between them

There's a chasm between two bad extremes, and the skill keeps falling into one or the other:

- **❌ The wall** — a giant paragraph re-explaining everything from zero, every caveat, the whole history. The user can't find the decision inside it.
- **❌ The bare label** — so terse they can't act: "Aprovar refactor?", "Opção A / B / C", a title that's just a code name.

The ruler: **enough to decide, nothing more.** Concretely — question in one plain line, premise in 1-2 sentences, one consequence line per option. If you wrote three paragraphs, cut to the premise. If you wrote four words, you owe the premise and the consequences.

### Afirmação, não narrativa — os quatro tells (2026-07-30)

O "wall" acima descreve o defeito por **tamanho**, e por isso não pegou: a página do
sprint num projeto real saiu com **3.646 palavras e 29 blocos acima de 200 caracteres**, sob esta
mesma seção. O vocabulário já estava humano ("bateria de testes", não "test suite"). O que
ficou robótico foi a **arquitetura da frase** — narrativa de processo onde cabia afirmação.

Régua numérica, conferível a olho antes de rodar o build:

- **Bloco `text`: no máximo ~200 caracteres** (2 linhas lidas). Passou disso, ou virou bullet, ou virou dois blocos.
- **Bullet: uma linha.** Bullet com ponto-e-vírgula no meio são dois bullets.
- **Página inteira: ~1.200 palavras** fora a prova crua. O dobro disso é o dump de CLI de volta, com CSS.

Os quatro tells de que você escreveu narrativa. Cada um tem conserto mecânico:

| Tell | O que é | Conserto |
|---|---|---|
| `;` costurando itens | "não rodei X; não existe Y; a trava compara Z" | é uma lista — vira `bullets` |
| `(1) … (2) … (3)` dentro de um parágrafo | você já enumerou, só não deixou o HTML enumerar | vira `bullets` |
| Narrativa de processo em 1ª pessoa | "Sequenciei: primeiro… depois… e só então…" | vira `bullets` na ordem, sem os advérbios de tempo |
| Oração explicativa entre travessões dentro de outra | "o conserto é uma linha — e não encosta na independência que faz a comparação valer (é ela que prova…) — mas você decidiu…" | duas afirmações separadas |

Antes e depois, de um arquivo gerado (`2026-07-30-sprint-app-exemplo.html`, bloco de 480 chars):

```
❌ (1) não rodei o loop de QA completo — troquei por uma revisão dedicada ao código
   que eu escrevi, então procurar defeito em código que eu NÃO toquei nesta sessão
   não aconteceu; (2) não existe teste de interface no repo (zero, e o plano
   quintuplica a superfície de tela) — o chip novo eu conferi com o olho, não com
   teste; (3) a trava do pacote compara data de modificação, que não sobrevive a um
   clone limpo — é guarda de máquina local, e a própria trava declara isso.

✅ bullets:
   - Revisei só o código que escrevi. Defeito em código que não toquei: não procurei.
   - Não existe teste de tela no repo. O chip novo eu conferi com o olho.
   - A trava do pacote compara data de arquivo — não sobrevive a um clone limpo.
```

**A exceção que manda:** dentro de `.evidencia` e `<pre class="raw">` nada disso vale. Saída
crua vai literal, do tamanho que for — parafrasear a prova é o defeito original com outra
roupa. Esta régua governa o que **você** escreve, nunca o que a máquina imprimiu.

### Self-check before opening the browser

Reread each decision/approval block as if you'd never seen the conversation. Can you state what it approves, why, and what each path costs — from the card alone, with zero jargon? If not, it's not ready to show.

## Decisions channel (for questions/decisions — non-negotiable when decision cards are present)

**Context:** when the HTML contains `.decision-card` blocks (main decision or sub-decisions), the user clicks to pick options but that state stays inside the browser. Without a feedback channel, Claude has no way to know what was chosen — the user would have to retype each answer in the CLI. This component bridges that gap.

**Nada disso é seu trabalho agora.** O `visual_page.py` emite a caixa sempre que o spec
tem um bloco `decision`, recortada do `template.html`, no lugar certo (depois do
sumário, antes da `.feedback-box`). Ela traz o painel que atualiza em tempo real, a
textarea de comentários e o botão de copiar.

Por que o programa e não você: **havia uma cópia deste bloco colada em prosa nesta skill
e ela já tinha divergido do template** — faltava o `.live-indicator`, então quem a
seguisse entregava a página sem o selo de sync. Regra em prosa apodrece; recorte não.

O que **continua** sendo seu trabalho é o conteúdo de cada decisão: a pergunta em uma
linha, o contexto em linguagem humana, e a consequência de cada opção.

**Copy output format (versioned, v1):**

The `copyDecisions` function emits a markdown block wrapped in versioned HTML comments:

```
<!-- visual-decisions v1 -->
📋 **Minhas escolhas:**

- **Decisão 1**: GitHub público · Como hospedar o marketplace?
- **Decisão 2**: Personalizada · Agrupamento
  - _Nota_: 2 plugins (handoff+wrapup juntos, carregar-handoff separado)

**Comentários / próximos passos:**
Quero pensar melhor na decisão 3.

<!-- /visual-decisions -->
```

Claude SHOULD detect the `<!-- visual-decisions v1 -->` marker when parsing pasted content — this is the signal that the user pasted a decisions block. Future format evolutions bump the version (`v2`, etc.) without breaking old-version detection.

Já implementado no template (não reescreva): aviso de `confirm()` quando ele copia com decisões faltando, e persistência em `localStorage` por arquivo (`claude-visual:<pathname>`), pra refresh ou fechada acidental não apagar o progresso.

## A nota desta página — o que fazer quando ela chega

Toda página sai com a caixa **"Como ficou esta página?"**: três eixos (clareza ·
escaneabilidade · detalhamento), três caras cada (👍 bom · 😐 dá pro gasto · 👎 ruim), e um
campo livre. O programa a emite sozinho — você não a escreve e não decide se ela entra.

Ela é **opcional e nasce neutra**, de propósito: o valor está no 👎 que o dono dá quando
algo irrita, nunca no 👍 de rotina. Caixa que exige voto vira atrito em toda página, e
atrito em toda página faz o voto virar clique automático.

Quando o estado chega (pelo botão de copiar ou pelo `latest.json`), o campo é `qualidade`:

```json
"qualidade": {"votos": {"clareza": "ruim", "escaneabilidade": "ok"}, "livre": ""}
```

O que você faz com ele, em ordem:

- **Nenhum voto** — não pergunte nada. Silêncio é a resposta normal de página boa.
- **Só 👍** — agradeça em meia linha e siga. Não vire isso em conversa.
- **Qualquer 😐 ou 👎 COM o campo livre preenchido** — a lição já está pronta. Escreva-a no
  formato do banco, **mostre ao dono antes de gravar**, e só então rode `clareza.py
  registrar`. Regra dele, de 2026-08-08: mudança na skill e no banco passa por ele.

  **E o "mostre" é PÁGINA, nunca texto no terminal (2026-08-09).** Toda proposta de
  mudança nesta skill, no banco de lições ou em qualquer regra de escrita das páginas
  nasce como página `/visual` — a lição candidata com o texto integral, e o antes/depois
  quando muda instrução. O terminal fica só com o endereço do arquivo. Motivo medido: o
  terminal rola, o texto sobe, e o dono aprova sem ver — ou não vê e a mudança morre.
- **Qualquer 😐 ou 👎 SEM o campo livre** — **pergunte**, e pergunte pelo eixo que ele
  reprovou, não em geral: *"a clareza ficou ruim — foi alguma palavra que eu não expliquei,
  ou a pergunta em si não deu pra entender?"*. Uma pergunta, com as duas hipóteses mais
  prováveis daquele eixo. Voto sem detalhe que não vira pergunta é voto que morre.

O eixo diz onde procurar: **clareza** → palavra sua, pergunta confusa · **escaneabilidade**
→ ordem dos blocos, o que ficou dobrado, tamanho · **detalhamento** → faltou prova, ou
sobrou texto que ninguém pediu.

## Live sync via `claude-visual-server`

O copy/paste é o fallback. O caminho normal é o daemon: o usuário mexe no browser, o daemon escreve em disco, o Claude lê quando ele diz "ok" / "pronto" / "lido".

**Files:**
- `${CLAUDE_PLUGIN_ROOT}/server/visual_server.mjs` — the daemon (Node stdlib only, zero deps). Binds `127.0.0.1:7755`.
- `${CLAUDE_PLUGIN_ROOT}/server/start.sh` — idempotent starter. Pings the port; if nothing responds, spawns `node visual_server.mjs` detached. Soft-fails if Node is missing.
- `~/.claude/visual-state/<session>.json` — per-session state file (rewritten on every POST from browser).
- `~/.claude/visual-state/latest.json` — always points to the most recently updated session. **Claude reads THIS file** to fetch the user's current state without needing to know the token.

**Endpoints:**
- `GET  /ping` — liveness probe (returns `{status,pid,port}`).
- `POST /state` — body `{session, docTitle?, state}`. Writes `<session>.json` + updates `latest.json`.
- `GET  /state?session=<id>` — reads a specific session (debugging).

**Skill workflow when generating an HTML (mandatory):**

1. Generate a unique session token. Format: short, matching `^[a-zA-Z0-9_-]{4,64}$`. Recommended: `<YYYYMMDDHHMM>-<rand6>` e.g. `202604201230-a3f2k9`.
2. Right after `<body>`, inject:
   ```html
   <script>window.VISUAL_SESSION = "<token>";</script>
   ```
3. Before `open "<path>"`, run `${CLAUDE_PLUGIN_ROOT}/server/start.sh`. Idempotent — if daemon already running, no-op.
4. Open the HTML.

**Behavior in the browser:**
- Every `saveState()` call (triggered on every click, key press, option-card change) also calls `postState()`, debounced at 400ms.
- `postState()` does `fetch POST http://127.0.0.1:7755/state` with `{session, docTitle, state}`.
- On success, the `.live-indicator` pill in the decisions-box turns green (`live sync`). On failure (daemon off), it turns amber (`copy manual`) — copy/paste button still works.

**How Claude reads state (the "tail" part):**

When the user signals completion via short triggers like **"ok"**, **"pronto"**, **"lido"**, **"tá bom"**, **"finalizei"**, Claude MUST:
1. Check `~/.claude/visual-state/latest.json` exists.
2. Read it, parse `state` field.
3. Act on the state the same way it would parse a pasted markdown block — decisions, comments, feedback items, general notes.
4. Respond.

If `latest.json` doesn't exist or is stale (>30min old), Claude falls back to asking the user to paste the copy/paste block.

**Security surface (deliberate):**
- Daemon binds **only** `127.0.0.1` (never `0.0.0.0`) — unreachable from the network.
- Session token is validated against `^[a-zA-Z0-9_-]{4,64}$` — no path traversal possible.
- Max body size 256KB — no DoS via huge uploads.
- 30-minute idle shutdown — daemon doesn't linger as zombie.
- CORS is `*` (needed for `file://` contexts which send origin `null`). Acceptable since daemon only binds local.

**Auto-shutdown:** daemon kills itself after 30 min of no requests. Next `/visual` invocation respawns.

**Graceful degradation:** HTMLs generated without `window.VISUAL_SESSION` (old files, or the user opens template.html directly) never try to sync — `postState()` is a no-op when the session is absent. Backward compatible.

## Feedback channel (verdict INLINE per item — the most important part)

Os controles de veredito por item são o canal canônico de feedback do usuário pro Claude.

### The verdict lives ON the item — never in a second table (non-negotiable)

**Por quê:** listar o conteúdo e depois re-listar tudo num menu de aprovação no fim obriga o usuário a rolar de volta (ou guardar de cabeça) o que era o item #1 quando decide o #50. Ele decide **enquanto lê**.

**Rule:** each reviewable item is a single `.feedback-item` that **contains** its own content. The keep/change/remove radios sit in the item's `.feedback-head` (right next to the title), and the depth goes in a `<details class="item-detail">` inside the same item. The user marks the verdict while reading the item. **Re-listing items with controls in a separate block at the bottom is a forbidden anti-pattern** — that is the "two tables" bug. There is exactly ONE list.

**When to render inline verdicts:** any list where the user decides item-by-item — plan tasks, benchmark/report findings, proposed features, schema choices. A purely informational diagnostic (nothing to approve/reject) gets no verdict controls.

**Como se constrói:** um bloco `item` no spec por item revisável. Numeração, `name`
único do rádio, ausência de pré-seleção, posição dos rádios fora do `<details>` e a
caixa de fechamento — tudo do programa.

Duas coisas continuam sendo escolha sua:

- **Os rótulos visíveis**, via `item_labels`. Um plano ou relatório de conclusão → "✓
  Manter / ✏️ Mudar / ✗ Remover"; achados ou features → "✓ Aprovar / ✏️ Ajustar / ✗
  Negar". **Os valores de
  máquina (`keep`/`change`/`remove`) nunca mudam** — o parser do clipboard e o live-sync
  dependem deles, e o programa não deixa você trocá-los.
- **Se o item merece veredito.** Diagnóstico puramente informativo (nada a aprovar ou
  rejeitar) não leva `item` — leva `text`, `bullets` ou `tri` solto.

Por que nada nasce pré-selecionado (decisão de 2026-06-20): um `<input checked>` nunca
dispara `onchange` no load, então o item **parece** escolhido e o contador lê 0 — o bug
"tenho que mudar e voltar pra contar". Item não tocado copia como "⚠️ sem veredito"; só
o **Aprovar tudo** trata não-tocado como ok. Isso hoje é check verde na suite, não
lembrete.

**Action buttons:** **"Aprovar tudo"** and **"Copiar feedback"**. Both — together with **"Copiar escolhas"** in the decisions-box — emit the **full user-input state** (decisions + dec-comments + feedback items + fb-general). They differ only in the leading verdict and trailing action cue, never in what they capture.

### Non-siloed copy semantics (mandatory)

**O botão final tem que resumir tudo que rolou ao longo do caminho.** Botão que captura só a própria caixa faz sumir comentário que o usuário escreveu em outro lugar.

**Rule:** every copy button calls `collectAllInput()` which concatenates decisions + `#dec-comments` + feedback items (with per-item `change` notes) + `#fb-general`. The buttons then wrap this body with a button-specific envelope:

| Button | Leading envelope | Trailing cue | Extra |
|---|---|---|---|
| `copyDecisions` ("Copiar escolhas") | `<!-- visual-decisions v1 -->` + `📋 Snapshot — escolhas e comentários` | `<!-- /visual-decisions -->` | confirm dialog if selections incomplete |
| `approveAll` ("Aprovar tudo") | `<!-- visual-approve v1 -->` + `✅ APROVADO — <title>` | `Pode prosseguir.` + `<!-- /visual-approve -->` | confirm dialog if any feedback item is `change`/`remove` (prevents accidental approval while asking for changes) |
| `copyFeedback` ("Copiar feedback") | `<!-- visual-feedback v1 -->` + `📝 Feedback no plano` | `Ajuste o plano e mostre de novo.` OR `Tudo certo — pode implementar.` + `<!-- /visual-feedback -->` | — |

**Parser implications for Claude:** the three markers (`visual-decisions`, `visual-approve`, `visual-feedback`) signal intent (snapshot vs approval vs rework), but the **body structure is identical**. When parsing pasted content, Claude should extract decisions + feedback together regardless of which marker wrapped them. The marker tells Claude what the user wants done with the information, not what fields to look for.

**How the user uses it:**

1. Plan mode prompt appears in the CLI with the plan.
2. The user reads it in the HTML (already open in browser).
3. The user fills out decisions + feedback + any comments in the HTML.
4. The user clicks whichever button matches the verdict: "Aprovar tudo" (approves, includes the observations), "Copiar feedback" (asks for changes, includes full state), or "Copiar escolhas" (snapshot at any point, full state).
5. The user goes to the CLI, pastes. Claude reads the marker + body and acts.

**Never** dump the plan text into the CLI response. The HTML IS the plan view. The CLI just handles the accept/reject mechanical step.

## Template — o vocabulário que o programa emite

O template canônico vive em **`${CLAUDE_PLUGIN_ROOT}/skills/visual/template.html`** e é
**o `visual_page.py` que o consome**, não você. Você não copia o template, não mexe no
CSS, não mexe no JS.

Esta lista existe por dois motivos: pra você saber **o que o spec consegue expressar**
(a coluna de bloco ao lado de cada componente), e pra quando você precisar da válvula
`raw_html` e tiver que usar as classes reais — inventar classe não dá erro, dá bloco sem
estilo. É **Variant B** (fundo indigo + acento pêssego + cards arredondados).

- **`.ident-strip`** — faixa de identidade no topo: projeto · artefato pelo título visível · o que gerou · `.estado` (`estado-rascunho`/`estado-gerado`/`estado-noar`/`estado-apresentado`). **Obrigatória em toda página que fala de algo que existe.**
- **`.artefato`** — moldura do artefato real: `.artefato-bar` (selo "artefato real" + procedência) + `<iframe src="file:///…">` ou `srcdoc` ou `<img>`. Nunca uma versão fabricada. **A barra sai com dois botões, emitidos pelo programa:** `⛶ tela cheia` (a moldura inteira, com a procedência junto; Esc volta) e `↗ nova janela`. Encolhido é certo no fluxo do documento — artefato em tamanho natural quebra a leitura —, mas **encolhido não pode ser a única forma de olhar**.
- **`.evidencia`** — a prova crua: `.evidencia-src` (comando · projeto · quando) + `<pre>` com scroll próprio e `max-height`. Use `<mark>` pra destacar a linha que decide. A variante `.evidencia.vazio` grita na tela quando não há prova colada — e o hook bloqueia antes de abrir. **Nasce SEMPRE fechada, sem exceção por tamanho** (o antigo "até 6 linhas abre" caiu em 2026-08-02): a única válvula é `"aberto": true` no bloco, porque revelar mais nunca esconde.
- **`.bullets`** / **`.bullets.problema`** — os 4-5 bullets do que se trata e os 2-3 do problema.
- **`.tri`** — problema (`.p`) · consequência (`.c`) · proposta (`.s`). **Obrigatório em todo bloqueio/problema apontado.** O problema fica visível; consequência e proposta nascem **fechadas** no `.tri-fold`, com rótulo derivado pelo programa. Dentro de `.feedback-item` vem logo após o `.feedback-head`. Demo: item 3 do template.
- **`.diagram`** — container de SVG/ASCII inline (com `figcaption`/`.cap` opcional)
- **`.opt-illustration`** — SVG dentro do card de opção (viewBox `0 0 100 60`, 64px de altura)
- **`.pill`** — label tags (kicker, decision-label, etc.)
- **`.tldr`** — one-sentence summary card with emoji
- **`h1`** + **`.subtitle`** — hero
- **`.meta-chips`** — reading-cost chips (time, items, decisions, date)
- **`.decision-card`** — wraps 3 option cards
- **`.decision-context`** — mandatory plain-language line right below `.decision-q`. One or two sentences saying what's at stake / what prompted the question, in human language (no code, no jargon). See "O pedido de aprovação tem que se explicar sozinho". Required on every decision card.
- **`.opt`** — option card (emoji + title + tradeoff). 3 per decision. 3rd is always `.opt-custom` with embedded `.opt-custom-input` textarea. Each option's `<p>`/`.tradeoff` states the consequence of picking it, in plain words.
- **`.feedback-item`** — the unified reviewable item: `.feedback-head` (num + title + keep/change/remove radios) + `.item-detail` (`<details>` with `.read-dot`/`.dchev`/`.detail-body` for depth) + inline `.feedback-textarea`. This is what carries the INLINE verdict. Use it for every plan step / finding / feature the user decides on. Demo: section 2 of the template.
- **`.sev`** — optional severity tag (`sev-high`/`sev-med`/`sev-low`) shown next to a finding's title
- **`.plan-tree`** (+ `.pt-phase` / `.pt-item` / `.pt-id` / `.pt-desc` / `.pt-evidence`) — a árvore do plano. **NÃO escreva este HTML à mão**: ele é emitido por `lib/plan_state.py render` a partir de `.claude/plans/<id>.plan.json`. Ver "Plano, PRD, roadmap" acima.
- **`.plan-item`** (`<details>`) — legacy collapsible block with `.read-dot` + `.plan-num` + `.plan-title`, for NON-reviewable read-only content only. For anything the user decides on, use `.feedback-item` instead.
- **`.card-tile`** — friction/metric grid cell
- **`.callout`** — side-ruled note (info/warn/danger/ok variants)
- **`.exec`** — exec summary card
- **`.feedback-box`** — CLOSING box only: progress + general observation + sticky action buttons. NEVER re-lists items (the verdicts live inline on each `.feedback-item`).
- **`.decisions-box`** — live summary of selected options + comments + copy button (mandatory when `.decision-card` is present)
- **`.sticky-actions`** — copy-feedback bar glued to bottom
- **`prefers-reduced-motion`** respected

Não invente classe. Se o que você quer não está nesta lista, ou não existe, ou é
`raw_html` usando as classes daqui.


## Ilustrar — mas ilustração não substitui prova

Imagem se lê muito mais rápido que texto. Conceito com ≥3 entidades ligadas (arquitetura, fluxo, antes/depois, árvore, quem-chama-quem) vai ilustrado, não em prosa densa.

**Atenção à ordem:** o diagrama explica o **mecanismo**; a `.evidencia` mostra o **fato**. Diagrama bonito no lugar da saída crua é o defeito original com outra roupa. Primeiro a prova, depois o desenho que a explica.

**Diagrama de arquitetura não se inventa aqui.** O molde com o vocabulário inteiro
(camadas, zonas, depósitos, filas, fronteiras de confiança, externos, protocolos) mora
numa fonte só, no plugin `archify`: `skills/archify/templates/arquitetura.template.json`,
com o exemplo renderizado ao lado (`arquitetura.template.html`). Copie o molde, troque os
rótulos, renderize pelo archify — o `/visual` embute o HTML resultante e **não** repete a
lista de peças, senão as duas versões divergem.

**Diagrama de fluxo, idem.** O molde é `skills/archify/templates/fluxo.template.json`,
com o exemplo renderizado em `fluxo.template.html` — passos, decisão com saídas nomeadas,
ramos paralelos, caminho de erro com retomada, atores e estados. A lista das peças e dos
recursos extras mora lá, nos cartões do próprio exemplo; aqui só o ponteiro.

**Como, em ordem de preferência:**

1. **SVG inline** dentro de `.diagram` — `viewBox`, `stroke="currentColor"`, formas simples, `<marker>` pra seta, traço 1.5–2px.
2. **ASCII** dentro de `<pre class="raw">` — pra fluxo e árvore quando SVG for exagero.
3. **Emoji em sequência** — micro-ilustração no meio do texto (`📥 input → 🔍 parse → 📤 output`).

**Imagens e artefatos — nada de rede, mas disco local pode:**

Nunca `<img src="https://...">`. A página não pode depender da internet.

- **Imagem** (screenshot, foto, figura de doc) → base64 inline: `base64 < image.png` → `<img src="data:image/png;base64,...">`. Imagem grande incha o arquivo; prefira recriar em SVG quando der.
- **Artefato que vive no disco** (o HTML de um slide, um PDF, uma página gerada) → `<iframe src="file:///caminho/absoluto">` dentro de `.artefato`. **Testado no Chrome:** renderiza, inclusive cross-dir com caminho absoluto; arquivo ausente vira caixa cinza (falha visível, não silenciosa).

Isso relaxa de propósito o "self-contained" antigo, e o teto é conhecido: o `iframe` mostra o arquivo **de agora**, não o de quando a decisão foi tomada, e quebra se o arquivo sumir. Aceito — a página de decisão vive horas, não anos, e apontar pro arquivo real torna impossível fabricar o "depois". Se o artefato for pequeno e a página precisar virar registro histórico, embuta uma cópia (`srcdoc` ou `<pre>`) em vez de referenciar.

**The rule is:** if you're rendering dense text and you thought for even a second "this could be a diagram", it SHOULD be a diagram.


## Multiple sub-decisions — each one gets its own option cards

**Rule:** if the content describes multiple sub-decisions the user has to make (e.g., "8 questions the plan needs to answer", "schema choices", "per-module configuration"), EACH sub-decision gets its own mini decision block with 3 option cards (including the mandatory `.opt.opt-custom` third card). Never reduce a decision to "my inclination" as read-only text.

**Detection heuristic:** if a plan section contains N items and each has a question mark, branching language ("ou", "entre X e Y"), or phrases like "decidir se", "escolher entre", "tag única vs múltipla" — that's N decisions, not N plan items.

**Como render:** um bloco `decision` no spec por sub-decisão. Cada um leva as **duas**
opções autorais — a terceira ("Outra — eu especifico", com a textarea de escape) é
acrescentada pelo programa, e ele **recusa** o spec que traz 2 ou 4. O usuário nunca fica
sem a saída.

Sua inclinação continua aparecendo: `"recommended": true` na opção que você recomenda —
como sugestão marcada com ★, nunca como a única resposta. Assim que ele escolhe, a
recomendação sai da frente.

**Ilustração (opcional, e vale a pena):** `"svg"` na opção, viewBox `0 0 100 60`,
`stroke="currentColor"`, formas geométricas simples. Conceito abstrato demais: pule a
ilustração **daquele** card e mantenha nos outros. Parcial é ok; ícone de banco de
imagem, não.

**Mistura de decisão com tarefa revisável:** as sub-decisões são blocos `decision` (o
usuário escolhe A/B/C, o painel de escolhas acompanha); as tarefas são blocos `item` com
veredito inline. As duas caixas saem juntas, na ordem certa, e o copy captura os dois.

## Content rules

- **Titles in bold, NOT backticks** (per CLAUDE.md). Backticks render azul claro — ruim no fundo claro no CLI, mas aqui a gente tá em HTML dark, ok usar `code.inline` para paths/commands.
- **No blockquotes (`>`)** in content rendering — in HTML they're fine but mimic the CLAUDE.md rule of keeping text readable.
- **No markdown tables inside `<details>`** — use the labels pattern (label-row with 🔧💡📁).
- **Svg inline** for diagrams — no external JS libs, no CDN. Nada de rede.
- **Max ~5 top-level `<section>`s** — if you need more, it's too dense for one visual; split into multiple files.
- **Output cru vai literal.** Dentro de `.evidencia`/`<pre class="raw">` não se parafraseia, não se resume e não se "humaniza" — escape só o que o HTML exige (`&lt;`, `&amp;`). Cortar linhas do meio é permitido se marcar com `…`; reescrever, não.

## Hook integration

O plugin registra **três** hooks (`hooks/hooks.json`):

| Evento | Script | O que faz |
|---|---|---|
| `PreToolUse[ExitPlanMode]` | `pre-exitplan-visualize.sh` | bloqueia a apresentação do plano no CLI até existir HTML COM prova |
| `SessionStart` | `sessionstart-plan.sh` | avisa que há plano aberto, com progresso e fase em curso |
| `Stop` | `stop-plan-status.sh` | **resume onde estamos em 1-3 bullets ao fim de cada turno** — e, quando tudo fecha, confirma a conclusão de forma inequívoca. A cobrança do tique entra no lugar do bullet "Falta" (1× por sessão), nunca como 4º. Nunca bloqueia. |

O hook `${CLAUDE_PLUGIN_ROOT}/hooks/pre-exitplan-visualize.sh` roda no `PreToolUse` de `ExitPlanMode` (registrado em `hooks/hooks.json`). Trabalho dele: **bloquear a apresentação do plano no CLI até o HTML existir E carregar prova**, pra o usuário ler no browser antes de aprovar.

Flow when the hook blocks (exit 2):

1. You (Claude) just called `ExitPlanMode` with a plan file.
2. `pre-exitplan-visualize.sh` runs → resolves the project's visual dir (cascade) and looks for a recent HTML matching this session in it.
3. Sem HTML recente **ou com HTML sem prova** → exits 2 with stderr instructions. The tool call is BLOCKED. The plan is NOT shown to the user.
5. You receive the stderr message and MUST:
   - Invoke this skill (Skill tool with `name: visual`)
   - Read the plan file named in the stderr
   - Se é plano/PRD/roadmap: `plan_state.py init` + `page` (ver a seção do plano). Qualquer
     outra coisa: escreva o spec e rode `visual_page.py build --spec`
   - Save to the **exact path suggested in stderr** (`--out` no build; o hook já resolveu o
     diretório do projeto pra você — não mude)
   - Open with `open "<path>"`
6. Retry `ExitPlanMode`. O hook acha o HTML fresco (< 5 min) **e com prova dentro** → exit 0, plan proceeds to the user in the CLI.
7. The user reads the HTML in the browser, approves or rejects in the CLI.

Critical behavior when the hook blocks:

- Do NOT try to present the plan as text in your response.
- Do NOT skip the skill — use o construtor, **nunca escreva o HTML você mesmo**.
- Do NOT summarize the plan to the user — the HTML IS the summary.
- Do the minimum: render, open, retry `ExitPlanMode`. One tight loop.

## Workflow when invoked

1. **`clareza.py licoes`** — os erros que já reprovaram antes (Passo 0a, inegociável)
2. Identify source content (last message, plan file, explicit content)
3. Detect type (plan / diagnostic / question with options / generic)
4. **Plano/PRD/roadmap → `plan_state.py`** (seção do plano). **Todo o resto → escreva o
   spec JSON**, abrindo as palavras da casa antes da primeira pergunta
5. `python3 ${CLAUDE_PLUGIN_ROOT}/lib/visual_page.py build --spec <f>` — ele resolve o
   diretório, nomeia o arquivo pelo `slug`, imprime o caminho e **roda as 4 conferências
   sozinho**. Os pontos que ele apontar: conserte o spec e rode de novo
6. Recusou? A mensagem lista todos os erros de forma de uma vez. Conserte o spec, não o HTML
7. *(opcional)* `clareza.py revisar --spec <f>` antes do build, se quiser conferir sem
   gastar uma geração
8. **Juiz de clareza (Haiku) lê a página** (Passo 0b). Qualquer PERDIDO ⇒ conserte e repita.
   Ao fim da leitura, **gere a página do parecer sem perguntar** (Passo 0b2)
9. Suba o daemon (`${CLAUDE_PLUGIN_ROOT}/server/start.sh`) e `open` o caminho impresso
10. **`clareza.py registrar`** com os padrões que o juiz apontou (Passo 0c) — **inclusive
    quando a última rodada passou limpa**: o que ensina é a rodada que REPROVOU, e ela some
    se você só registrar no fim
11. Tell the user in 1-2 lines: "Abri no browser: `<path>`"

Never render and then text-dump the same content in the CLI response. The whole point is: HTML replaces the textão, doesn't duplicate it.
