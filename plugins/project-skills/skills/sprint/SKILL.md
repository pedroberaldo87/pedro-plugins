---
name: sprint
description: Modo de execução contínua — executa um plano ou tarefa multi-etapa do começo ao fim sem pausas, sem checkpoints e sem perguntas, decidindo o que precisar e anotando cada decisão para o relatório final. Use quando o usuário disser "sprint", "sovai", "sova", "executa até o fim", "vai sem parar", "não me consulte", "eu não estarei disponível", "modo autônomo". Não dispare para tarefa curta que acaba num turno.
---

# Sprint — Execução Contínua

O usuário vai ficar indisponível. Reconheça com uma linha (`modo sprint ativo, começando`) e comece. Daqui em diante, silêncio até o relatório final.

## Contrato

**Faz:**
- Executa o plano (ou a tarefa) do começo ao fim, sem pausar — através do **motor decompõe→executa→revisa** (Workflow; ver _Execução_)
- Toma todas as decisões necessárias para seguir e **anota cada uma**
- Verifica antes de declarar feito — regras globais do CLAUDE.md continuam valendo
- Ao final, atualiza a doc (`doc-touch`, que escala pro FULL sozinho se precisar) e faz commit + push do trabalho — ver **Persistência**

**Não faz:**
- Pergunta de confirmação no meio ("posso seguir?", "X ou Y?")
- Checkpoint intermediário pedindo aval
- Reporte de progresso parcial — silêncio é o esperado
- Ação destrutiva ou irreversível fora do escopo do plano (drop de banco em produção, force push em main, rotação de credencial real, deploy fora do combinado) — registra como pendência

## Bloqueios

Se um item não puder ser feito como pedido, **não invente workaround silencioso**. Pula o item, anota o bloqueio com o que faltou, e segue para o próximo. A regra global "Entrega 100% ou Para e Conversa" continua valendo — o "Para e Conversa" vira "Pula e Anota" porque o usuário está indisponível, mas a entrega ainda precisa ser honesta.

## Execução — motor decompõe → executa → revisa (Workflow)

A execução do plano **não roda solo no loop principal** — roda como **um Workflow determinístico** (a tool `Workflow`), mesmo padrão do `/qa-loop`: **motor = Workflow, casca = esta skill**. Três papéis, cada um no **tier certo pra etapa** (R8 — mesma tabela do `/qa-loop`, mesmos nomes de knob), e os freios (parada, paralelismo, fidelidade) são **lógica do script (JS)** — não "o Opus lembrar a regra a cada volta". É um **pipeline fechado**, por isso Workflow e não Agent Team.

### O preâmbulo: a régua e os princípios (obrigatório, antes de QUALQUER etapa)

Antes de armar a missão — e vale para especificar, planejar, implementar, testar e
revisar — rode o par, nesta ordem:

1. **`/doc-load`** (skill `doc-load`, deste plugin) — carrega a documentação canônica do
   projeto e diz o que vale como RÉGUA hoje. A saída vai no `args` do Workflow como
   `regua` (a lista de arquivos que valem) e `marcaRegua` (a marca que o motor congela
   na primeira volta): `python3 "$(bash "<plugin project-skills>/lib/resolve-plugin.sh" project-skills lib/doc_load.py)" --project-root "$PWD" --json`
2. **`/principles`** (skill `principles`, quando instalada) — os princípios genéricos
   aplicados ao contexto da missão. Ausente na máquina: avise no relatório e siga.

Em conflito, **a régua do projeto ganha** — princípio genérico não revoga a lei da casa.
É este par que substitui a prosa antiga "leia a constituição e o quality-goals": a regra
de quem vale (lei `ready`/`approved` · acordo só `approved` · minerado nunca) agora é
programa, e as quatro cópias dela em prosa divergiam.

### O sinal que arma o gate (obrigatório, e é a PRIMEIRA coisa)

Antes de disparar o Workflow, acenda o sinal; ao entregar o relatório, apague. É ele que faz o gate existir:

```bash
SPRINT_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/andamento"
mkdir -p "$SPRINT_DIR"
printf 'sprint\n' > "$SPRINT_DIR/ativo-$CLAUDE_CODE_SESSION_ID"   # ao armar a missão
SPRINT_MOTOR_ID="motor-$(date -u +%Y%m%dT%H%M%SZ)-$$"    # id DESTE motor na sessão
# ao entregar, a receita do passo 3 (apaga o CONJUNTO do estado, não só o sinal):
python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/andamento.py)" encerra "$CLAUDE_CODE_SESSION_ID" sprint
```

**O nome vai DENTRO do sinal** porque é ele que a barra de status lê para dizer quem acendeu (`lib/andamento.py:_motor`). Sinal vazio não é motor anônimo: cai no rótulo genérico, e foi assim que a barra chamou de `sprint` toda missão desta skill mesmo depois de o plugin `sprint` deixar de existir.

O `SPRINT_MOTOR_ID` vai no `args` do Workflow como `motorId` (junto com `sessionId` = `$CLAUDE_CODE_SESSION_ID`): é com ele que o motor **reserva os arquivos da onda antes de soltar executor** (`hooks/reserva-de-arquivos.sh reservar`, ver o esqueleto) e os **libera** ao entregar. Dois motores da mesma sessão com o mesmo id se enxergariam como um só, e a reserva nunca recusaria nada.

Enquanto o sinal está aceso, `hooks/pretooluse-motor-arma.sh` do plugin `sprint` **nega** todo disparo de sub-agente e manda rodar o Workflow. Fora do sprint ele é mudo. Desligamento: `SPRINT_GATE=0`.

⚠️ **Esqueceu de apagar o sinal, a sessão inteira fica sem despachar sub-agente.** Apagar é parte da entrega, não faxina opcional.

⚠️ **Com o motor VIVO, a casca não edita o repositório.** A reserva de arquivos só enxerga
motores — a casca escrevendo direto passa por fora dela, e o trabalho aparece na árvore
sem pertencer a passo nenhum. Medido em 2026-08-09: um patch feito pela casca durante a
corrida fez a conferência final acusar *"a árvore suja carrega trabalho fora dos passos
desta decomposição"* sobre três arquivos que nenhuma tarefa tocou. Conserto que nasce no
meio da missão espera o relatório (e entra no relançamento), ou vira passo no plano — as
duas coisas que o motor sabe julgar. A única exceção é destravar **porta fechada** que o
próprio motor apontou, porque sem ela nenhuma onda sai — e aí o conserto é commitado na
hora, por caminho nomeado, antes do relançamento.

**A rede embaixo do esquecimento (desde 2026-08-06):** o sinal **expira por idade**. Passado `SPRINT_TTL_MIN` (default 720 min = 12h) sem ser apagado, a primeira consulta do gate o **remove** — junto com o contador de bloqueios dele — e registra a linha em `expirados.log`. Isso não te dispensa do `encerra`: a janela é de 12h porque a missão que o gate protege é longa por definição, e encurtá-la mataria sinal de execução legítima em andamento.

### Por que o gate precisou nascer

A frase que ficou aqui de 2026-08-01 até 2026-08-02 dizia que *"o guard `PreToolUse(Agent)` acorda a cada disparo"*. **Não acordava.** O guard que existe é o do `guardrails`, e ele foi escrito para **proteger** Agent Teams — a regra 3 dele libera explicitamente *"tarefa one-off sem team_name"*, que é exatamente a forma pela qual o `/sprint` descambava. A skill se apoiava numa proteção inexistente, e ninguém tinha como saber: prosa descrevendo mecanismo ausente não dá erro.

**O gate degrada, não trava.** Depois de 3 negações na mesma sessão ele desiste, libera e grava a desistência em `desistencias.log`. O motivo é o cenário: missão longa, dono ausente. Se a inferência de que o Workflow não passa por aqui estiver errada, a missão continua manca em vez de morrer parada.

## Modelo & effort por etapa (R8) — contrato em `references/r8-tiers.md`

O tier de cada etapa (modelo · effort · knob) e a semântica dos knobs são o **contrato R8 compartilhado** com o `/qa-loop`, vendorado em **`references/r8-tiers.md`** (fonte: `_shared/r8-tiers.md` — não editar a cópia à mão; `scripts/sync-shared.sh --check` pega drift). A tabela completa (Etapa · Modelo · Effort · Knob + o que cada knob significa + a regra de tier por rodada) está lá.

**É TUDO Opus 5** (contrato R8 desde 2026-07-26, vale pros dois motores): os seis knobs rodam `model: 'opus'` e só o **`effort`** varia por etapa. Aqui isso pesa dobrado — o `/sprint` roda com o usuário indisponível, sem checkpoint humano pra pegar execução rasa.

Abaixo, **onde cada knob entra NESTE motor** (decompõe→executa→revisa):

| Knob | Onde no motor |
|---|---|
| `decompose_model` | OPUS #1, **rodada 1** — quebra o plano inteiro em tarefas. |
| `coordinate_model` | OPUS #1 nas **rodadas 2+** (só o delta) + OPUS #2 nas rodadas normais. |
| `executor_model` | EXECUTORES — tarefa padrão (`complexity` ausente ou `'standard'`). |
| `mechanical_model` | EXECUTORES — tarefa marcada `complexity: 'mechanical'` (renomear, mover arquivo, 1 config, 1 valor — sem julgamento amplo). |
| `diagnose_model` | Tarefa reaparece em `missingTasks`/`gaps` por ≥ `churn_threshold` rodadas → diagnóstico de raiz antes de mandar o executor tentar de novo. |
| `finalize_model` | **Não consumido no caminho feliz** — a confirmação independente da obra é o `/qa-loop --headless` da etapa seguinte (que mantém o confirm-pass DELE). Só é consumido aqui pela **guarda**: sem `/qa-loop` na máquina, o motor roda um confirm-pass neste tier antes de declarar `built`. |

### Como o tier chega ao motor (obrigatório, antes de disparar o Workflow)

O valor do `effort` **não vive nesta skill** — e desde 2026-08-09 você também **não o
transporta**: a constante `T` já está escrita em `references/motor.js`, o arquivo que o
disparo passa ao `Workflow` (ver _O motor do disparo_). Quem cobra que ela continue igual
a `_shared/r8-tiers.json` é `lib/test_motor_js.py`, que roda na suíte do plugin.

O motivo de ser constante escrita — **não leia de `args.tiers`** em tempo de execução —
é medido: o canal que levava esse valor até o script **falhava** — `args.tiers`
chegava `undefined`, e isso matava o motor na primeira volta. Trocar um tier é editar
`_shared/r8-tiers.json`, rodar `scripts/sync-shared.sh`, espelhar a constante no
`motor.js` — e o teste reprova se o espelho ficar para trás.

### Os ids do plano vão no `args` (obrigatório, antes de disparar o Workflow)

A trava que impede o orquestrador de forjar tarefa compara o id contra os ids REAIS. Ela
não lê disco — o script não abre arquivo —, então a casca extrai a lista e a passa como
**`planIds`**, ao lado dos outros parâmetros.

O comando: leia o `.plan.json` e imprima a lista dos ids de todos os passos, em JSON.

Sem `planIds` a trava sai de cena inteira, e o motor volta ao comportamento medido em
2026-08-08: **oito ids inventados** pelo orquestrador (o sufixo `-R`, de "revisada"),
**seis tarefas executadas** com esses ids, e nenhuma delas marcável — a marcação recusou
uma a uma com *"passo 'F21.5-R' não existe no plano"*, e o trabalho ficou no disco com o
plano dizendo que não.

### A compilação cara é paga UMA vez, pela casca (obrigatório, antes de disparar o Workflow)

Projeto que compila em minutos cobra esse preço **de cada executor** quando ninguém compila antes: numa execução real, **dez minutos de compilação por tarefa** foi o que empurrou o agente para o segundo plano — e processo em segundo plano que morre não avisa. A compilação é paga **aqui, uma vez**, e o que os executores herdam é o **cache quente** no disco do repositório.

`SPRINT_REPO_ROOT` = a raiz do repositório e `SPRINT_BUILD_CMD` = o comando de compilação do projeto, **o mesmo que o executor rodaria** (`npm run build`, `cargo build`, `go build ./...`, `make`); projeto que não compila deixa vazio e o passo não faz nada.

```bash
SPRINT_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/andamento"
mkdir -p "$SPRINT_DIR"
BUILD_LOG="$SPRINT_DIR/build-$CLAUDE_CODE_SESSION_ID.log"
# NUNCA limpe antes nem depois: `clean`, `rm -rf <dir de build>` e `--no-cache` aqui
# devolvem o cache frio ao executor e a compilação cara volta a ser por tarefa.
if [ -n "$SPRINT_BUILD_CMD" ] && ( cd "$SPRINT_REPO_ROOT" && sh -c "$SPRINT_BUILD_CMD" ) >"$BUILD_LOG" 2>&1
then BUILD_WARM=true
else BUILD_WARM=false
fi
echo "buildWarm=$BUILD_WARM"
```

O resultado vai no `args` do Workflow como **`buildWarm`**, e de lá para **todo** `execPrompt` — cache quente que ninguém avisa ao executor é cache que ele derruba com um `clean` de rotina. **Fail-open:** compilação que falha devolve `buildWarm=false` e a missão segue — o erro real chega ao executor pelo próprio build dele, e travar a missão por causa do aquecimento é pior que aquecimento nenhum. O log fica em `~/.claude/andamento/`, fora do repositório.

### Knobs deste motor (a casca passa em `args`)

| Knob | Default | O que faz |
|---|---|---|
| `maxRounds` | `12` | **Trava de incêndio, não meta.** Teto de voltas do #1↔#2; estourou, o que faltou vira Bloqueio. O dono recusou o teto baixo em 2026-08-09: missão de implementação é longa, e cortar a volta cedo devolve trabalho pela metade. |
| `severityFloor` | `P1` | Gap abaixo do floor não segura a obra de pé (vira nota no relatório, não nova rodada). |
| `churnThreshold` | `2` | Mesma tarefa reaparecendo N rodadas **seguidas** → escala pro `diagnose_model`. |
| `hasQaLoop` | detectado | `false` liga o **confirm-pass** em `finalize_model` antes de declarar `built` (ver a guarda no #2). A casca detecta se a skill `qa-loop` está disponível e passa o booleano — nunca deixa `undefined`, senão a guarda nunca arma. |
| `tokenBudget` | `null` | **Disjuntor por consumo.** Teto de tokens de saída da missão inteira. Estourou, o motor **se desliga** e relata quanto gastou. `null` = sem teto (o comportamento antigo). |
| `sessionId` | — | `$CLAUDE_CODE_SESSION_ID`. É a chave da **reserva de arquivos**: a disputa que existe é entre motores da MESMA sessão, e reserva global recusaria toda sessão paralela nos arquivos dela. |
| `motorId` | — | Identifica ESTE motor dentro da sessão (carimbo de arranque serve). Dois motores com o mesmo id se enxergariam como um só e a reserva nunca recusaria nada. |
| `silenceLimitMin` | `12` | **Vigia por tempo.** Minutos de registro parado que fazem o vigia acender o sinal. Só derruba se **não houver trabalho vivo** — ver `F9.24` abaixo. As DUAS metades falam na tela: o gancho de andamento (`hooks/posttooluse-andamento.sh` → `lib/andamento.py:linha_silencio`) narra o silêncio longo com trabalho vivo como **`rodando ha N min`** e o silêncio sem sinal de vida como **`travamento`**, no mesmo `systemMessage` do relógio. |
| `buildWarm` | `false` | **Cache de compilação já quente.** `true` = a casca compilou os alvos antes de disparar o motor (passo acima), e o valor chega a todo executor no `execPrompt` — é o que o proíbe de recompilar do zero. Ausente/`false` = ninguém aqueceu, e cada executor compila como antes. |
| `blocoMax` | `4` | **O grão do ciclo curto.** A onda sai em blocos desse tamanho, e CADA bloco fecha o ciclo inteiro: revisor por tarefa → revisão do bloco → suíte → marcação → commit → doc → colheita (decisão do dono, 2026-08-09). O primeiro bloco que traz falha **fecha a onda ali**: o resto volta pro orquestrador sem ser despachado. Bloco maior = menos ciclos e mais trabalho perdido quando a premissa fura cedo. |
| `tetoExecutorMin` | `20` | **Teto de um executor só.** Minutos que um executor tem para entregar; passou disso, ele devolve `espera: true` e a rodada fecha com quem voltou. É teto **por agente**, não da onda — o vigia acima olha o motor inteiro e não enxerga um agente ciclando dentro de uma onda viva. |

Precedência: flag da invocação > default acima. A casca **sempre** materializa os quatro primeiros antes de disparar o Workflow — `maxRounds` ausente faz o `while` do motor não rodar nenhuma volta e devolver "pronto" sem ter construído nada.

### Os dois freios que olham a EXECUÇÃO, não a obra

`maxRounds` conta voltas e `severityFloor` mede gaps — nenhum dos dois enxerga a missão gastando três vezes o previsto nem parada há vinte minutos. Foi assim que uma execução em 2026-08-06 disparou **72 agentes para 25 tarefas** sem nada perceber.

- **Disjuntor (de dentro).** O motor soma o que gastou a cada onda; passou de `tokenBudget`, para e relata. É a única trava que enxerga custo, e ela é do script — o `budget.remaining()` do runtime existe, mas quem decide parar é o motor, para o relatório saber dizer **onde** parou.
- **Vigia (de fora).** Motor parado não se denuncia: quem trava não escreve "travei". Por isso o sinal de vida é o **registro** (o histórico de ondas), e quem o lê é um passo separado. Sem isso, "rodando" e "morto" são a mesma tela.

### O que o vigia narra na tela principal

O dono está fora do browser e olhando o terminal. **Toda mudança de estado vira uma linha; rodada sem mudança fica calada** — silêncio significa "nada mudou", e é isso que faz a narração não virar ruído. Isto é régua, não lista de eventos: evento novo que mude estado também fala, sem precisar entrar numa enumeração aqui.

As linhas de ferramenta longa saem de `lib/andamento.py`, e o contrato dele é o seguinte:

- **Relógio sempre.** Ver o agente em idle não diz **quando** ele parou. Toda linha de disparo abre com a hora local.
- **Estimativa só por memória deste projeto.** `andamento.estimativa()` devolve a mediana das últimas 5 execuções **daquele mesmo comando, neste projeto**, e `None` quando ele nunca rodou aqui. Comando novo sai **sem número**.
- **Nunca estime por média global nem por "complexidade".** Medido em 299 transcritos de agente deste repositório: `Bash` tem mediana **0,7s**, p90 **19,1s** e máximo **660,4s**. Com dispersão de quase mil vezes, número inferido é chute com cara de dado — e chute cria expectativa que ninguém sabe que foi chutada.
- **Progresso vem do placar que a ferramenta imprime**, não de perguntar ao modelo como vai. `andamento.placar()` lê a saída crua nos três formatos medidos (`139 passou · 0 falhou` · `OK (56 checks)` · `17 ok / 0 falhas`, mais o do pytest) <!-- acopla-ok: são EXEMPLOS do formato de placar que o parser reconhece, não contagem deste repositório -->, e `andamento.avanco()` compara com o anterior.
- **Dois placares iguais seguidos = `sem avanço`.** Esse é o sinal de "está em círculos", e ele vale porque o outro candidato foi medido e **não pega nada**: 0 de 282 agentes repetiram o mesmo comando 4 vezes ou mais. Detector de repetição de comando seria decoração.

A linha real, gerada pelo módulo:

```
21:40:22 · python3 …/test_plan_state.py · primeira vez aqui, sem estimativa
21:40:22 · python3 …/test_plan_state.py · ~1min35s (das 3 vezes anteriores aqui)
rodando há 70s  · usual ~1min35s           · 62 passou · 12 falhou — sem avanço
rodando há 4min · passou do dobro do usual · 74 passou ·  0 falhou — avançou
```

Registrar a duração ao fim de cada ferramenta longa (`andamento.registrar(repoRoot, cmd, seg)`) é o que alimenta a estimativa da próxima vez. Suíte roda várias vezes na mesma missão — é dessa repetição que a memória vive.

**E o relógio e a estimativa também chegam à BARRA** (`hooks/statusline-motor.sh` → `lib/andamento.py:linha_motor`), que é a única superfície que fica: `systemMessage` rola com a conversa, e quem volta ao terminal uma hora depois não vê nenhuma das linhas acima. A barra é desenhada por outro processo e **não adivinha nada** — ela sai como `ferramenta há 70s · usual ~1min35s` porque **quem executa gravou o disparo**: o gancho de andamento em `marca` (PreToolUse de Bash, o mesmo que roda dentro de cada executor da onda) escreve em `~/.claude/andamento/trabalho-<sid>` o instante, o **comando** e o **projeto**, e apaga o arquivo quando o comando volta. Sem comando e projeto no disco não há como chamar `estimativa()`, e a barra volta a ter só a idade da missão. Comando sem histórico aqui sai **sem número**, pela mesma regra de sempre.

### A janela de tempo da sessão NÃO dá para observar

Duas coisas diferentes foram confundidas, e a confusão fazia o motor planejar contra um número que não existe:

- **O quanto de conversa já foi usado** — isso **dá** para ver, e é o que o `context-guard` mostra na barra de status.
- **Quanto tempo falta na janela da sessão** — isso **não** dá para ver de dentro. Não há chamada que responda, e estimar pela hora do relógio é chute.

**A estratégia de parada, então, não é temporal.** O motor para pelo que ele consegue medir: `maxRounds`, `tokenBudget`, o freio de severidade, e o vigia. Quem escrever passo que dependa de "quanto falta de sessão" está escrevendo contra um dado inexistente — e o sintoma é a missão morrer no meio sem checkpoint, que é exatamente o que `F9.14` cobre.

- **OPUS #1 — Orquestrador.** O nome é decisão do dono (2026-08-09): o papel que abre o motor **orquestra**, não só decompõe — antes de montar a onda ele recebe e considera o **ledger da corrida** (o que já foi julgado, consertado e confirmado), as **causas confirmadas com escopo**, e a **lista de antipadrões conhecidos** (seção própria abaixo, viva — cada autópsia aprovada acrescenta o padrão novo). É dele a vigilância do PARA-ou-PULA: etapa que não pode concluir **para** (Bloqueio com prova) ou **é pulada** (declarada, com motivo) — nunca re-tentada como se repetir consertasse. NÃO planeja do zero. Pega o **plano que você deixou** e o quebra em tarefas de implementação, marcando para cada uma os **arquivos que toca**, se é **paralelizável**, de quais tarefas **depende**, e se é `complexity: 'mechanical'` (operação bem delimitada) ou `'standard'`. Cada tarefa carrega também o **`requisito`** que ela atende e o **`pronto`** que a declara feita — **os dois saem da spec, copiados; nunca redigidos aqui**. Executor não cumpre critério que não recebeu, e critério inventado pelo orquestrador faz o revisor medir contra a régua errada. Item da spec que não traz os dois **não vira tarefa: vira Bloqueio** (`whyNeedsYou` = qual dos dois falta). **Passo que espera um ato do dono chega declarado, e você só transporta:** o `espera_dono` do passo no `.plan.json` vira `esperaDono` na tarefa, **copiado literal**. Não é seu julgamento — não marque tarefa por achar que ela "depende do usuário", e não desmarque a que o plano marcou. É esse campo que tira a tarefa da fila (e, por dependência, quem depende dela): sem ele o motor solta executor num passo que não tem como funcionar, ele volta falhando, e a falha vira churn como se fosse executor incompetente.

  **E o `pronto` é JULGADO antes de virar tarefa, não só copiado — e quem julga é o script, não você.** Critério que só se cumpre **fabricando valor dentro de um entregável** vira `blocker` de `kind: 'criterio'` — nunca tarefa. O motor roda `lib/regua_pronto.py` (do plugin project-skills, a mesma régua que o `plan_state.py` cobra ao gravar o plano) sobre o `pronto` de **cada** tarefa decomposta, logo depois desta etapa e **antes de soltar qualquer executor**: reprovado sai da lista e vira Bloqueio. Enquanto isto era só instrução em prosa, bastou o julgamento não acontecer para o critério-armadilha chegar inteiro a quem executa. A régua, e ela é sobre a **origem do valor**, não sobre o caminho do arquivo:

  - **Pode:** regerar o entregável a partir do dado real. É operação do produto.
  - **Não pode:** injetar valor inventado dentro do entregável para o critério fechar. Isso é bancada, e bancada não entra em coisa que vale.

  **E o `pronto` que só fecha editando arquivo SOB TRANCA vira tarefa `protegido`.** Esta mesma skill proíbe o motor de reescrever documento de concepção aprovado (`status: approved` no frontmatter) — nem o corpo, nem o frontmatter. O orquestrador lia o plano sem olhar isso e fabricava tarefa cujo `pronto` só se cumpre justamente ali: **a tranca mandava o executor a uma porta que ela mesma trancou**, e sobravam dois caminhos, os dois ruins — desobedecer (derrubando a marca do de acordo) ou voltar falhando rodada após rodada até virar churn e queimar o diagnóstico caro. A régua é de **disco, não de julgamento**: arquivo que a tarefa toca e que traz `status: approved` no frontmatter é arquivo sob tranca → a tarefa nasce com **`protegido`** = o caminho do arquivo + por que ele está trancado. Ela **continua entrando na fila** (diferente do `esperaDono`, que tira da fila), mas o entregável dela é uma **proposta**, e o critério do revisor **inverte**: `git diff` vazio naquele arquivo é o resultado **certo**.

  O caso que originou: um critério mandava o número aparecer no documento, o executor **obedeceu** e escreveu o número na mão. Quem errou não foi quem executou — foi o critério, e ninguém o julgou antes de soltar o executor. Critério ruim solto vira trabalho errado com todo mundo cumprindo o combinado. Rodada 1 = `decompose_model` (plano inteiro); rodadas 2+ (re-decompõe só o delta do feedback do #2) = `coordinate_model`. Re-arquitetar é proibido (mesma regra do "não replanejar no headless"); buraco no plano que exija decisão de arquitetura vira **Bloqueio**, nunca invenção silenciosa.
- **EXECUTORES (Opus 5) — Implementam as tarefas.** Tarefa padrão = `executor_model`; `complexity: 'mechanical'` = `mechanical_model`. Independentes rodam **em paralelo**; dependentes, **em série** na ordem do #1. Tarefa única ou missão sequencial pura → o Workflow degenera pra um executor por vez, sem cerimônia (o fan-out é ganho só quando há independência real).

**O texto que o executor recebe abre assim, e a primeira linha é literal — `PAPEL: EXECUTOR` sozinha, antes de qualquer prosa (a regra vale para todo prompt do motor; a tabela `prompt → PAPEL` está na seção dos prompts):**

```
PAPEL: EXECUTOR
Você é EXECUTOR. Implemente esta tarefa no repositório <raiz>.
```

**Depois da declaração vêm as regras, e elas não são conselho — cada uma nasceu de trabalho perdido:**

1. **CONFIRA NO DISCO ANTES DE IMPLEMENTAR.** O primeiro passo é abrir o arquivo do `pronto` e ver se ele já está cumprido. Agente que morre **depois** de escrever some do registro, e a tarefa dele volta como faltante — sem esta checagem, o trabalho é refeito por cima do que já estava lá. Já cumprido: devolve `done: true` com o `arquivo:linha` que prova, e não reescreve nada.
2. **FORMATAR O PROJETO INTEIRO É PROIBIDO.** Nada de `prettier --write .`, `ruff format .`, `black .`, `eslint --fix .` sem caminho, nem equivalente que varra a árvore. Formatador sem escopo **reformatou 18 arquivos de outros agentes** numa execução real e quase apagou trabalho paralelo. Formate **só os arquivos que esta tarefa tocou**, nomeados um a um.
3. **SONDA DE DEPURAÇÃO NASCE FORA DO ALCANCE DA SUÍTE.** Precisou de script temporário para investigar? Ele vai para o diretório de rascunho da sessão, **nunca** com nome que a suíte colete (`test_*.py`, `*.spec.ts`, `*_test.go`). Sonda esquecida dentro do alvo da suíte derruba a suíte de todo mundo e some do radar — quem varre depois é o fiscal de bancada (`F8.3`).
4. **PASSOU DO TETO, PARE E DEVOLVA `espera: true`.** O texto da tarefa traz `tetoMin` — os minutos que você tem. Marque a hora ao começar; chegou no teto sem ter fechado o `pronto`, **pare onde está**, deixe no disco o que já funciona e devolva `{ done: false, espera: true, note: <em que ponto parou e o que falta> }`. Isso **não** é falha: a tarefa volta pro orquestrador na rodada seguinte com a sua nota. Ficar mais que o teto tentando terminar é o que segurou **21 agentes já entregues por 2 horas** numa execução real — a onda só fecha quando o último volta, e quem cicla nunca volta.
5. **ARQUIVO SOB TRANCA: O ENTREGÁVEL É A PROPOSTA, NÃO A EDIÇÃO.** Tarefa que chega com `protegido` toca arquivo que este motor **não pode reescrever** (documento de concepção aprovado). **Não edite o arquivo** — nem o corpo, nem o frontmatter. Devolva `proposta: { arquivo, antes, depois }` com os **dois lados literais**: `antes` = o trecho que está no disco hoje, copiado caractere por caractere; `depois` = o texto que deve entrar no lugar, pronto pro dono colar. Descrição do que mudar **não serve** — quem aplica é o dono, e resumo obriga ele a reescrever do zero. Aqui `done: true` significa **proposta entregue**, e **`git diff` vazio naquele arquivo é o resultado CERTO**, não a falha.

6. **CACHE QUENTE: NÃO RECOMPILE DO ZERO.** A tarefa chega com `buildWarm` — `true` significa que os alvos **já foram compilados** pela casca antes de o motor começar, e o cache está no disco do repositório. Compile **incremental**, e só o que a sua mudança exige: `clean`, `rm -rf` de diretório de build, `--no-cache` e recompilação do zero estão **proibidos** com `buildWarm: true`. Foram **dez minutos de compilação por tarefa** que empurraram o agente para o segundo plano numa execução real — e agente em segundo plano que morre não avisa ninguém.

7. **O `pronto` É LITERAL — PROXY É PROIBIDO.** Se o critério não pode ser cumprido **como escrito** (pré-condição ausente, medição que não existe, decisão congelada do dono), o executor **não inventa um substituto "equivalente"** nem troca o número medido por outro: devolve `impossivel` com o motivo, e a alegação segue o caminho do auditor. Medido em 2026-08-09: um critério pedia a soma de fichas REAIS (~4-6 mil palavras) contra 77 mil; as fichas não existiam porque o dono congelou o gerador delas, e o executor trocou a medição por um proxy (`TETO_SOMA * 10 <= textos`, ~126 palavras de fixture) — **documentou a troca honestamente no código e a auto-concedeu**. O passo fechou como `done` com o critério original jamais medido, e só a conferência final pegou. Documentar a troca não a autoriza: trocar critério é do dono. O revisor por tarefa reprova entrega que cumpre critério reescrito (`kind: 'spec'`, ≥ P1).

⚠️ **`isolation: 'worktree'` é PROIBIDO neste motor.** A regra anterior mandava isolar em worktree duas tarefas paralelas que tocassem o mesmo arquivo, e ela **queimou uma execução inteira em 2026-08-06**: 72 agentes para 25 tarefas, 15 delas executadas **3 vezes cada**, 8 diagnósticos de tarefa-presa, e 49 worktrees com trabalho dentro que ninguém leu.

O mecanismo da falha, e ele é estrutural, não um deslize: o executor termina dentro da cópia isolada, **e nada traz a cópia de volta**. O revisor (#2) confere no repositório de verdade, não encontra o trabalho, marca a tarefa como não-feita, e o orquestrador (#1) manda refazer — para sempre, porque refazer também vai para uma cópia nova. O motor não tem como perceber: o sintoma que ele vê ("essa tarefa não sai do lugar") é indistinguível de executor incompetente, e por isso ele escala para o `diagnose_model` — gastando ainda mais.

**Colisão de arquivo se resolve dividindo o LOTE, nunca dividindo o repositório.** Dentro de uma onda, quem colide vai em sub-lotes seriais; todo mundo escreve no mesmo repo, e o revisor enxerga tudo. É mais lento só no caso raro de colisão real, e é sempre correto.

A regra geral que sobrou disto: **isolamento sem fusão declarada é dívida com cara de cuidado.** Se um dia este motor voltar a isolar, o passo que traz de volta nasce no mesmo commit — e o revisor precisa saber onde olhar.
- **OPUS #2 — Revisor de construção.** Julga a obra **contra a spec** — o plano que a casca passou em `planPath`/`planText`, e que o motor entrega ao #2 igual como entrega ao #1. A decomposição do #1 é **meio**, não fonte da verdade: revisar contra ela é circuito fechado, onde quem decompõe errado é aprovado errado. Cinco eixos: **spec** (a spec saiu, mesmo no que a decomposição não previu?) · **constituição** (o que saiu respeita as metas de qualidade autorais do projeto?) · **rastreio** (toda tarefa decomposta trouxe `requisito` e `pronto`?) · **completude** (toda tarefa decomposta saiu?) · **coesão** (as peças paralelas integram, sem se contradizer?). Desvio de spec vira gap de `kind: 'spec'` e **nasce em severidade ≥ floor**; se vier abaixo, o script o segura assim mesmo — senão sairia do filtro de severidade e passaria calado. **Eixo de rastreio:** tarefa decomposta sem `requisito` ou sem `pronto` **reprova** — vira gap de `kind: 'rastreio'`, que nasce em severidade ≥ floor e é segurado pelo script igual ao de spec. Tarefa sem requisito não tem contra o que ser medida, e sem `pronto` quem executa decide sozinho o que é "feito": nenhuma das duas passa calada. **Eixo de constituição:** o revisor **lê `.claude/docs/constituicao.md` e `.claude/docs/quality-goals.md` do projeto onde a missão está rodando** e sinaliza onde a implementação VIOLA o que está escrito lá. **O desenho aprovado entra na mesma régua:** quando o projeto tem `.claude/docs/blueprint.md` (o esquema de funcionamento) e `.claude/docs/features.md` (a lista de funcionalidades) com `status: approved` no frontmatter, o revisor os lê junto e sinaliza onde a obra **contradiz o que foi acordado ali** — `problem` cita o documento e a passagem contradita, senão o dono não sabe qual etapa está em jogo. Documento sem `status: approved` não é régua: é rascunho, e medir contra rascunho reprova obra certa. O arquivo é aberto na rodada, **nunca copiado para dentro desta skill** — a régua é a do projeto que instalou, e cópia em prosa defasa. Violação vira gap de `kind: 'constituicao'` pela rubrica de severidade normal, sem faixa própria. **A marca da lei é congelada na primeira volta:** o revisor devolve em `lawMark` a marca do texto que leu — a **saída literal de um comando que o motor escreve no prompt** (`cat <arquivos da régua> | cksum`, montado da lista `regua` que a casca passou), nunca uma receita que o revisor interpreta. A receita em prosa ("o cksum do corpo dos dois arquivos") produziu, medido em 2026-08-09, **quatro marcas diferentes do mesmo disco na mesma corrida** (com/sem frontmatter, concatenado/somado, com/sem o tamanho) e dois avisos falsos de "a lei mudou". O motor fixa a da rodada 1 e passa ela de volta nas seguintes — o #2 mede contra a lei fixada, nunca contra o texto novo. Lei editada no meio da missão vira **aviso no relatório** (Bloqueio "precisa de você"), porque as rodadas anteriores foram medidas contra o texto antigo; o que não pode acontecer é a régua trocar calada e duas rodadas da mesma missão medirem contra textos diferentes. **Projeto sem esse arquivo: o eixo simplesmente não roda** e a revisão segue com os outros quatro — ausência de constituição não é gap. **Quando a concepção está errada, e não o código:** o mesmo eixo cobre o caso em que o que a execução descobriu contradiz um documento de concepção já aprovado (`status: approved`) — a entrevista errou, o código está certo. Vira gap de `kind: 'concepcao'`, e o revisor **nunca reescreve documento aprovado** — nem o corpo (mexer nele reabre a etapa pela marca do de acordo) nem o frontmatter. O gap sobe como **aviso no relatório** (Bloqueio "precisa de você") propondo **reabrir a etapa**: nomeia o documento, a passagem contradita e a linha `correcao-pendente: {o que precisa mudar}` que o dono grava no frontmatter e cobra até reapresentar e reaprovar. Propor é do motor, escrever é do dono. Continua **não** caçando bug sutil nem rodando a suíte — profundidade de correção é do `/qa-loop` (etapa seguinte). Roda em `coordinate_model`; quando os cinco eixos batem, declara `built=true` **direto** — quem re-checa do zero é o `/qa-loop --headless` que roda logo em seguida (Fase Gate + confirm-pass dele). **Guarda (armada no script, não só na prosa):** com `hasQaLoop=false` o motor roda um **confirm-pass dedicado** em `finalize_model` antes de declarar `built` — sem `/qa-loop` adiante, fechar no veredito de `coordinate_model` seria declarar pronto sem nenhuma segunda checagem. Devolve **feedback estruturado pro #1**, que re-decompõe **só o delta** (o que faltou / precisa refazer) na volta seguinte. A seta de volta #2→#1 é o coração do motor.
**Onde cada documento de projeto mora, e quem tem direito de escrevê-lo** — as pastas, o
frontmatter e a tabela de quem escreve e quem lê — está em `contrato-familia.md`, ao lado deste
arquivo (fonte: `_shared/contrato-familia.md`). O motor **lê** a lei e a concepção aprovada; nunca
as escreve.

**O revisor manda a sonda dele para fora do alvo da suíte, pela mesma regra do executor.** É a metade de instrução do problema que o fiscal varre depois — quem planta a sonda tem que saber onde ela pode nascer, senão o fiscal vira faxina permanente em vez de rede.

**O juiz prova que leu a coisa inteira.** Todo veredito — do #2, do confirm-pass, do auditor — devolve a **âncora do fim**: a última linha não vazia do que ele julgou, literal. Sem ela o veredito é **recusado** e o papel roda de novo. Nasceu de um caso medido: um juiz aprovou uma página em 36 segundos tendo lido só por busca, e só admitiu quando confrontado. Leitura por amostragem é indistinguível de leitura inteira no texto do parecer — a âncora é a única diferença observável.

**Tarefa sob tranca INVERTE o critério do revisor.** O motor entrega ao #2 a lista `protegidas` — os `task_id` das tarefas que tocam arquivo trancado. Nelas o que se julga é a **proposta**, não a obra: **`git diff` vazio no arquivo protegido é o resultado CERTO**, e o revisor só reprova quando falta `antes` ou `depois` literal. O contrário também vale — arquivo protegido que **aparece** no `git diff` é gap de `kind: 'spec'`: o executor furou a tranca e derrubou a marca do de acordo do dono. Sem esta inversão o #2 media a tarefa pela régua normal, via arquivo intocado, reprovava por não-feita e devolvia ao #1 exatamente a tarefa que ninguém tem permissão de fazer.

- **AUDITOR — a segunda opinião antes de derrubar qualquer coisa.** Executor que declara impossível **não encerra nada sozinho**: bloqueio repetido na mesma tarefa convoca um auditor, e é ele que decide. Aconteceu de verdade — um executor declarou impossível o que ele conseguia fazer com a ferramenta que já tinha na mão.

  O auditor recebe a **lente invertida**: o ônus é dele provar que **não dá**, não do executor provar que dá. E recebe, junto, a **lista do que havia à mão** — as ferramentas disponíveis naquele contexto —, tendo que dizer **quais o executor nem tentou**. Foi essa pergunta que faltou no caso real: o diagnóstico dizia "exige navegador contra produção", o agente **tinha** navegador, e a causa verdadeira era outra (uma dependência não declarada: publicar exigia o aval do dono, e as jornadas de tela dependiam de estar publicado).

  Dois desfechos, e os dois são do script: auditor que **derruba** a alegação devolve a tarefa ao loop com o que ele apontou; auditor que **confirma** encerra a tarefa como impedimento real, com o motivo escrito. Encerrar direto no "impossível" do executor é o que esta peça existe para impedir.

- **DIAGNÓSTICO — escalada de tarefa-presa.** Se a MESMA tarefa reaparece em `missingTasks`/`gaps` por ≥ `churn_threshold` rodadas seguidas (default 2, mesmo limiar do `/qa-loop`), o motor escala ANTES de mandar o executor tentar de novo: um diagnóstico dedicado em `diagnose_model` (R8, "diagnóstico após falhas repetidas") investiga a causa raiz (dependência não mapeada, arquivo errado, premissa furada) em vez de repetir o mesmo pedido esperando resultado diferente. O diagnóstico entra no `feedback` da próxima rodada do #1.

  **A causa apontada não entra sem sobreviver ao desafio (2026-08-09).** Ao detectar o problema, o investigador **para e investiga a causa REAL** — nunca descreve o sintoma e manda consertar ali mesmo. A causa que ele apontar vai a um **desafiador** (`desafioCausaPrompt`, mesmo `diagnose_model`) com a lente invertida do auditor: o papel dele é **provar que a causa está errada** — apontar o fato que ela não explica, o caminho que ela ignora, a causa concorrente mais simples. Os dois **loopam**: o desafio da volta volta ao investigador na seguinte, até um referendar o outro. Acordo em até 3 voltas → o diagnóstico entra no `feedback` marcado `desafiada: true`. Três voltas sem acordo → **ninguém vence no cansaço**: vira Bloqueio `kind: 'causa-em-disputa'` com as duas versões escritas, porque conserto em cima de causa disputada é o conserto de sintoma com etiqueta nova. Desafiador mudo não referenda — a causa sem veredito NÃO passa como consenso. Nasceu de regressão medida em 2026-08-08: um conserto pontual, feito onde o defeito apareceu, reabriu o mesmo problema em outro arquivo — *"para de fazer remendo"*.

### Fronteira com o `/qa-loop` (a spec é comum; o ângulo, não)

Os dois loops leem a **mesma spec** e perguntam coisas **diferentes** — e isso vai **escrito no prompt de cada papel** pra não duplicarem trabalho:

- **Este loop (#1↔#2) garante que está CONSTRUÍDO** — spec + constituição + rastreio + completude + coesão de montagem, medidas **contra a spec** e contra a `constituicao.md` e o `quality-goals.md` do projeto; a decomposição do #1 entra como meio (previu tudo? saiu tudo?), nunca como contrato final. Pergunta: _"a spec virou código inteiro e coerente?"_. **NÃO** caça bug sutil, **NÃO** roda a suíte, **NÃO** mexe em lint/type.
- **O `/qa-loop` (etapa seguinte) garante que está CORRETO** — bug, regressão, lint/type/test, segurança, e fidelidade ao plano com **profundidade de correção** (os 3 buckets dele). Pergunta: _"o código construído tem defeito?"_.

Resumo: **#2 = "está de pé, e é o que a spec pediu?" · qa-loop = "está certo?"**. O motor de implementação fecha quando a obra está de pé; o qa-loop entra **depois** pra procurar defeito. A spec é o eixo dos dois — o que muda é montagem aqui, defeito lá.

### O ciclo curto é por BLOCO; a onda é a passada geral

Três grãos, cada um com a pergunta própria (decisão do dono, 2026-08-09):

| Grão | Quem julga | A pergunta |
|---|---|---|
| **tarefa** | revisor por tarefa (`TAREFA_REVIEW`) | esta entrega cumpriu o `pronto` dela, com teste que morde e dentro da régua? |
| **bloco** | revisão do bloco (`BUILD_REVIEW`) | as entregas juntas se sustentam — os mesmos eixos, mais coesão? Só o de acordo dela + suíte verde liberam marcação, commit e doc |
| **onda** | revisão geral da obra + revisão geral da doc | o que está NO REPOSITÓRIO (escopo: os arquivos da onda) é o que a spec e a régua pedem? A doc inteira ainda descreve o repo de agora? |

A revisão de cima **nunca herda** o veredito da de baixo — reabre os eixos no grão maior.
Achado da revisão geral sobre passo **já marcado** vira conserto com **RE-TICK** do mesmo
id (regrava a prova), nunca tarefa nova com id forjado. E o custo é conhecido: a suíte
inteira custa ~147s medidos, pagos uma vez POR BLOCO — é o preço de nada entrar no
histórico sem teste verde.

**A suíte é a MESMA em toda rodada, e roda uma vez na LARGADA (2026-08-09).** Duas regras
que nasceram da mesma corrida: (1) o conjunto de testes é **enumerado por comando** — o
`runSuitePrompt` escreve o `find` no texto —, nunca "os diretórios do trabalho desta
missão", porque esse recorte fez a rodada 1 rodar 43 testes e a rodada 2 rodar 120; (2) a
suíte roda **uma vez na rodada 1, antes de qualquer executor** (`suite:largada`), e
vermelho ali é **porta fechada**, não obra desta missão — o teste que já estava quebrado
antes da largada apareceu no meio do bloco 1 da rodada 2, matou o salvamento e queimou
três rodadas em cima de um defeito que não era da obra.

### A volta ao #1 é por BLOCO, não por onda inteira

O laço era **decompor tudo → executar tudo → revisar tudo**: numa onda de vinte tarefas, quem falhava na primeira só era notado depois que a vigésima voltasse — e as dezenove seguintes já tinham sido construídas em cima de uma premissa furada. Agora a onda sai em **blocos de `blocoMax`**, e o **primeiro bloco que traz falha** (`done: false` ou executor que não voltou) **fecha a onda ali**: os blocos seguintes **não são despachados**, entram no `missing` da volta seguinte, e o orquestrador re-decompõe o delta já sabendo o que quebrou.

Quem não foi despachado **não é tarefa presa**: entra na mesma isenção de churn do `esperaDono` (`F9.56`) — contador de reincidência é de quem falhou, e ninguém tentou essas.

**O laço é fechado, e é o MESMO das duas receitas.** Aqui (implementação) e no `/qa-loop` (revisão) vale a mesma regra: **feito o conserto, quem revisa reabre sobre ele** — o #2 julga de novo a obra depois de cada volta de execução, e o laço só fecha quando uma rodada vem **limpa** (`complete && cohesive` e zero gap acima do floor). Conserto que sai sem re-revisão declara pronto o que ninguém reconferiu, e é assim que o resíduo do próprio conserto — o caso que o fix deixou de fora — atravessa a missão inteira sem ninguém ver. O que cada laço reabre muda (lá é o delta dos arquivos tocados, aqui é a obra contra a spec); o fechamento por rodada limpa, não.

### Freio do loop (não é "até o #2 ficar feliz")

Revisão é poço sem fundo (mesma disciplina do review-loop: parada por retorno decrescente, não "até zero"). O loop #1↔#2 para no **primeiro** que ocorrer:
- **[primário]** #2 reporta `complete && cohesive` e **zero gap** acima do floor de severidade — gap de spec e de rastreio contam sempre, estejam onde estiverem na escala → obra de pé, segue pro QA.
- **[trava]** atingiu `maxRounds` (safety-cap, **não** meta) → o que faltou vira **Bloqueio (precisa de você)** no relatório.

### Nada que o motor usa para si mesmo é escrito à mão — nem caminho, nem nome de skill

Duas formas do mesmo defeito, as duas medidas neste repositório, as duas silenciosas:

- **Caminho de arquivo por posição.** O `F14.2` moveu `plan_state.py` de plugin e o script
  seguiu apontando a pasta antiga: 47 agentes de marcação falharam no primeiro comando e
  gastaram **8,45M de tokens** redescobrindo o rename, cada um por conta própria. Quem
  resolve é `lib/resolve-plugin.sh <plugin> <caminho>`.
- **Nome de skill com o plugin dentro.** Uma skill é invocada por `<plugin>:<skill>`, então
  o nome completo é um ponteiro para o plugin. Sete skills mudaram de casa no mesmo `F14.2`,
  e o motor continuou pedindo `project-doc:doc-touch` — que não existe mais. **Quatro ondas
  fecharam verdes e nenhuma produziu documentação**, sem que nada acusasse: o agente recebe
  um nome inválido e segue. Quem resolve é `lib/resolve-skill.sh <skill>`, que devolve
  `<plugin>:<skill>` olhando **só a versão ativa** de cada plugin.

A regra vale para os dois: **descubra em tempo de execução, nunca escreva o nome completo
no script nem nesta skill.** Escrito à mão, ele fica certo até alguém mover a peça — e o dia
em que ficar errado, ninguém vai saber.

### O motor do disparo é COPIADO daqui, não reescrito a partir daqui

🔴 **Esta seção já se chamou "referência — o princípio, não código imutável", e essa frase
custou uma missão inteira.** Em 2026-08-08 a casca leu o esqueleto e escreveu um script
"equivalente" à mão. O que aconteceu, medido comparando os dois arquivos:

```bash
# as peças que o esqueleto tinha e o script disparado NÃO tinha
blocoMax · naoDespachadas · blocoQueFalhou      → 0 ocorrências no script
```

Eram as travas do `F9.57` — o retorno ao orquestrador **por bloco**, que outro passo da
mesma missão tinha acabado de implementar. Sem elas o motor voltava ao orquestrador só ao
fim da onda inteira, e o resultado foi: **as ondas 4 e 5 executaram zero tarefas**, 41
tarefas reapareceram como faltantes em 3+ rodadas, e 604k tokens saíram sem trabalho.

**A regra desde 2026-08-09: o script NÃO é montado no disparo — ele é um ARQUIVO do
plugin.** Os prompts dos papéis e os schemas só existiam em prosa aqui, a casca os
traduzia em 436 linhas de código a cada disparo, e uma dessas traduções foi guardada em
rascunho e rodou DEPOIS do rename do plugin com o nome morto (`meta.name` velho na tela),
sem nada acusar. O executável agora é **`references/motor.js`**, resolvido por nome e
passado direto ao `Workflow`:

```bash
MOTOR="$(bash "$(dirname "<skill_dir>")/../../lib/resolve-plugin.sh" project-skills skills/sprint/references/motor.js)"
# Workflow({ scriptPath: MOTOR, args: {...} })
```

Nunca copie o `motor.js` para rascunho, nunca o redigite, nunca "melhore" na hora. A casca
só monta os `args` — e passa também **`resolvePlugin`**, **`resolveSkill`** e
**`resolveSprintPlugin`** (os caminhos absolutos dos três resolvedores, descobertos por
`resolve-plugin.sh`), porque instalado numa máquina de terceiro o repositório da missão
não é este marketplace e o motor não tem como adivinhar onde o plugin mora.

O esqueleto abaixo continua sendo a FONTE documentada do laço — quem muda comportamento
edita os DOIS (o esqueleto aqui e o `motor.js`), e quem pega divergência é
`lib/test_motor_js.py`: as peças nomeadas, a tabela `prompt → PAPEL` e a constante `T`
contra `r8-tiers.json`, tudo conferido na suíte do plugin.

**Como conferir antes de disparar** — se alguma peça do esqueleto não estiver no motor.js,
o arquivo não é o desta versão:

```bash
for peca in blocoMax naoDespachadas idsDoPlano congeladas esperaChain saudePrompt ledgerCorrida impressaoTarefa emCirculo paraPorCausaGlobal; do
  printf '%-16s esqueleto=%s motor.js=%s\n' "$peca" \
    "$(grep -c "$peca" <SKILL.md>)" "$(grep -c "$peca" <references/motor.js>)"
done
```

Os três schemas (`DECOMP`, `TASK_RESULT`, `BUILD_REVIEW`) são o que torna os gates
determinísticos: o script lê campos estruturados, não texto solto.

```javascript
export const meta = {
  name: 'sprint-build-engine',
  description: 'Motor de implementação: tier por etapa (R8) — decompose/coordinate/executor/mechanical/diagnose/finalize',
  phases: [{ title: 'Decompor' }, { title: 'Diagnose' }, { title: 'Executar' },
           { title: 'Revisar' }, { title: 'Confirmar' }],
}

// args (da casca): { planPath, planText, planIds, maxRounds, severityFloor, repoRoot,
//                    churnThreshold, hasQaLoop, sessionId, motorId }
// `planIds` = TODOS os ids que existem no arquivo do plano. Sem ele a trava de id
// inventado nunca arma, e o orquestrador volta a forjar tarefa que ninguem consegue
// marcar. A casca o extrai antes de disparar (ver o passo na secao acima).
// O parâmetro pode chegar TEXTO (JSON serializado) em vez de objeto — quando isso
// aconteceu, todo campo lido dele virou undefined e o motor morreu na 1ª volta sem
// dizer por quê. Converte ANTES de usar, e o resto do script só fala com ARGS.
const ARGS = typeof args === 'string' ? JSON.parse(args) : args
const sevRank = s => ({ P0:3, P1:2, P2:1, P3:0 }[s] ?? 0)
const floor = sevRank(ARGS.severityFloor || 'P1')
// default DENTRO do motor: sem isso, ARGS.maxRounds undefined faz `r < undefined` ser
// false na 1ª volta — o motor devolveria "nada construído" em silêncio.
const maxRounds = ARGS.maxRounds || 12
const churnThreshold = ARGS.churnThreshold || 2
// 'shared' = a tarefa colide em arquivo com OUTRA do MESMO lote → vai em sub-lote SERIAL.
// NUNCA em worktree: o trabalho ficaria na cópia e o revisor confere no repo real (ver acima).
const touchesShared = (t, lote) => lote.some(o => o.id !== t.id && o.files?.some(f => t.files?.includes(f)))
const rounds = []; const blockers = []
let built = false, r = 0
// DISJUNTOR e VIGIA — os dois freios que olham a EXECUÇÃO, não a obra. Sem eles o
// motor gastou 3x o previsto numa execução real (72 agentes p/ 25 tarefas) sem nada
// perceber, e ficou parado sem se denunciar: quem trava não escreve "travei".
const tokenBudget = ARGS.tokenBudget || null
const silenceLimitMs = (ARGS.silenceLimitMin || 12) * 60 * 1000
// TETO POR EXECUTOR (F9.29) — o vigia acima olha o MOTOR; este olha UM agente. Onda com
// trabalho vivo não acorda o vigia, então um executor ciclando dentro dela é invisível
// pros dois freios de cima.
const tetoExecutorMin = ARGS.tetoExecutorMin || 20
// CACHE QUENTE (F9.34) — a casca já pagou a compilação; `=== true` porque o valor ausente
// tem que virar `false`, e não `undefined` chegando ao executor como se fosse aviso.
const buildWarm = ARGS.buildWarm === true
let ultimoSinalDeVida = ARGS.now      // carimbo passado pela casca (Date.now() não roda em script)
let ultimaSuiteMissao = null          // a última suíte da MISSÃO: rodada sem suíte não apaga o trabalho-vivo
let desligadoPor = null               // 'orcamento' | 'vigia' — vira stopReason
const gastoAgora = () => budget.spent()
const gastoInicial = budget.spent()
let feedback = null   // do #2 pro #1 na volta seguinte (a seta de volta)
let lawMark = null    // marca da lei do projeto, CONGELADA na rodada 1 (ver o pino abaixo)
const taskChurn = {}  // { task_id: nº de rodadas seguidas reaparecendo em missingTasks/gaps }
const impossivelChurn = {}  // { task_id: nº de rodadas seguidas em que o executor alegou impossível }
const marcadosNaMissao = new Set()   // o que os blocos já gravaram no plano — a revisão geral usa pro re-tick

// ── O LEDGER DA CORRIDA (autópsia 2026-08-09, decisão do dono) ───────────────
// Revisor e auditor chegavam cegos: re-julgavam o já julgado e re-consertavam o já
// consertado, cada um pagando a própria redescoberta. Todo veredito, causa confirmada
// e marcação entram aqui na hora, e quem julga RECEBE o trilho antes de julgar.
const ledgerCorrida = []   // { r, tipo: 'veredito'|'causa'|'marcado'|'auditoria', taskId, resumo }
const trilho = () => ledgerCorrida.slice(-30)

// ── REPETIR SEM MUDANÇA DE ESTADO É PROIBIDO (autópsia 2026-08-09) ───────────
// Etapa que não conclui tem DOIS desfechos e só dois: PARA (bloqueio com prova) ou
// PULA (declarado, com motivo). Re-tentar como se repetir consertasse é o que queimou
// 43% da frota numa corrida real. A impressão é do que a tarefa RECEBE — se nada
// mudou desde a última tentativa, o resultado seria o mesmo pelo mesmo preço.
const impressaoTarefa = {}   // task_id -> impressão da última tentativa
const estouraramTeto = new Set()   // quem devolveu espera: re-tentar é legítimo
let fpRodadaAnterior = null  // detector de corrida em círculo (rodada inteira)

// ── O CACHE DE CAUSA (decisão do dono, 2026-08-09) ────────────────────────────
// A investigação de causa passou a disparar também por GRAVIDADE (achado P0/P1 na
// primeira aparição), além da reincidência. Sem esta trava, um bloco com dois achados
// graves por tarefa viraria dezenas de investigações no tier caro — várias sobre a
// MESMA raiz. A chave é o conjunto de arquivos da tarefa: causa referendada não
// reabre na mesma missão, e a camada de cima recebe a causa pronta.
const causaCache = {}
const chaveDeCausa = t => ((t?.files || []).join('|') || t?.id || '?')
// ── TODA CAUSA GANHA ESCOPO, E ESCOPO DE REPOSITÓRIO PARA O MOTOR (autópsia) ──
// A porta do commit fechada gerou 30 investigações da MESMA raiz porque a chave do
// cache era por tarefa. Agora o par investigador+desafiador declara o ESCOPO no
// referendo — 'tarefa' ou 'repositorio' — e causa de repositório: (1) mora numa chave
// única do cache, valendo pra TODAS as tarefas; (2) para o motor no MESMO turno, pelo
// helper abaixo. O rótulo nasce do par em acordo, nunca do motor sozinho.
const paraPorCausaGlobal = (d, taskId) => {
  desligadoPor = 'causa-global'
  blockers.push({ taskId, kind: 'causa-global',
    what: `causa confirmada com escopo de REPOSITÓRIO: ${String(d.causa).slice(0, 300)}`,
    whyNeedsYou: 'todo trabalho novo morreria na mesma porta — o motor parou no mesmo turno; destrave e relance' })
}
const investigaCausa = async (task, attempts) => {
  const chave = causaCache['@repositorio'] ? '@repositorio' : chaveDeCausa(task)
  if (causaCache[chave]) return { ...causaCache[chave], deCache: true }
  let causa = null, desafio = null, acordo = false
  for (let volta = 1; volta <= 3 && !acordo; volta++) {
    causa = await agent(diagnoseStuckTaskPrompt({ task, attempts,
        desafioAnterior: desafio?.motivo || null }),
      { model: ARGS.model, effort: T.diagnose.effort, phase: 'Diagnose',
        label: `causa:${task?.id || '?'} v${volta}` })   // diagnose_model
    if (!causa) break
    desafio = await julga(desafioCausaPrompt({ task, causa }),
      { model: ARGS.model, effort: T.diagnose.effort, phase: 'Diagnose',
        label: `desafia:${task?.id || '?'} v${volta}`, schema: DESAFIO })
    // desafiador mudo não referenda: sem veredito, a causa NÃO entra como consenso
    acordo = desafio ? desafio.procede === true : false
  }
  const escopo = desafio?.escopo === 'repositorio' ? 'repositorio' : 'tarefa'
  const out = acordo ? { causa, desafiada: true, escopo }
                     : { causa: null, disputa: { investigador: String(causa || 'sem resposta').slice(0, 200),
                                                 desafiador: String(desafio?.motivo || 'sem veredito').slice(0, 200) } }
  if (acordo) {
    causaCache[escopo === 'repositorio' ? '@repositorio' : chave] = out
    ledgerCorrida.push({ r, tipo: 'causa', taskId: task?.id, escopo,
                         resumo: String(causa).slice(0, 160) })
  }
  return out
}

// Tier por rodada (R8): rodada 1 = decompose_model (planejamento inicial); rodadas 2+
// = coordinate_model (coordenação rotineira). O bloco abaixo é ESCRITO no texto do
// script na hora de compor a chamada — gerado pelo r8_tiers.py, nunca digitado à mão e
// nunca lido dos parâmetros em tempo de execução: por ali o valor chegava indefinido e
// matava o motor na 1ª volta. Trocar tier = editar `_shared/r8-tiers.json` e re-gerar.
const T = { decompose: {effort:'high'}, coordinate: {effort:'medium'},
            executor: {effort:'medium'}, mechanical: {effort:'low'},
            diagnose: {effort:'medium'}, finalize: {effort:'medium'} }
const tierFor = round => ({ model: ARGS.model,
  effort: round === 1 ? T.decompose.effort : T.coordinate.effort })

// ── VEREDITO SEM A ÂNCORA DO FIM É RECUSADO (F9.16 · S-24) ──────────────────
// A regra "o juiz prova que leu a coisa inteira" já estava na prosa e o campo já estava
// no schema — e nada derrubava: parecer sem `anchor` entrava como parecer bom, e leitura
// por amostragem seguia indistinguível de leitura inteira. Todo veredito passa por aqui:
// sem a âncora ele é RECUSADO e o papel roda DE NOVO, agora sabendo por que voltou.
// Duas recusas seguidas devolvem null — a mesma porta do juiz que não respondeu, porque
// quem não prova que leu não aprovou nada.
const julga = async (prompt, opts) => {
  for (let tentativa = 1; tentativa <= 2; tentativa++) {
    // o rótulo da 2ª volta diz POR QUE ela existe: sem isso a tela mostra o mesmo
    // nome duas vezes e a recusa por âncora fica indistinguível de trabalho repetido.
    const v = await agent(tentativa === 1 ? prompt : { ...prompt,
      recusado: 'o veredito anterior voltou SEM a âncora do fim e foi recusado — devolva em `anchor` a última linha não vazia do que você julgou, literal' },
      tentativa === 1 ? opts : { ...opts, label: `${opts?.label || 'juiz'} ↻ sem âncora` })
    if (!v) return null
    if (v.anchor) return v
  }
  return null
}

while (!built && r < maxRounds) {
  r++; phase(`Rodada ${r}`)
  const tier = tierFor(r)

  // ── GUARDA CATCHALL DE SAÚDE (autópsia 2026-08-09, decisão do dono) ─────────
  // A porta do commit fechada queimou 43% de uma corrida em investigação. A regra
  // agora é genérica: na largada de TODA rodada os checks determinísticos da casa
  // rodam UMA vez; porta fechada — qualquer porta — vira parada na hora, com a
  // saída crua colada. Fail-open: check quebrado ou agente mudo não fecha nada.
  const saude = await agent(saudePrompt({ repoRoot: ARGS.repoRoot, round: r }),
    { model: ARGS.model, effort: T.mechanical.effort, phase: 'Decompor',
      label: `saude:r${r}`, schema: SAUDE })
  if (saude?.fechada) {
    desligadoPor = 'porta-fechada'
    blockers.push({ what: `a porta do repositório está fechada: ${saude.motivo}`,
                    whyNeedsYou: `nenhuma onda sai com a porta fechada — todo trabalho novo morreria nela. Prova:\n${saude.saida || '(sem saída)'}` })
    break
  }

  // ── SUÍTE NA LARGADA: vermelho PRÉ-EXISTENTE aparece na PORTA (2026-08-09) ──
  // A suíte que os blocos vão cobrar roda UMA vez aqui, ANTES de qualquer executor:
  // vermelha na largada é porta fechada com a lista colada, nunca descoberta no meio
  // da onda. Fail-open: agente mudo não fecha nada.
  if (r === 1) {
    const base = await agent(runSuitePrompt({ repoRoot: ARGS.repoRoot, round: r, bloco: 0 }),
      { model: ARGS.model, effort: T.mechanical.effort, phase: 'Decompor',
        label: 'suite:largada', schema: SUITE_RESULT })
    if (base?.heartbeat) ultimoSinalDeVida = base.heartbeat
    if (base && base.green === false) {
      desligadoPor = 'porta-fechada'
      blockers.push({ what: `a suíte do repositório JÁ está vermelha antes da missão: ${(base.failing || []).join(' · ') || base.placar || 'sem lista'}`,
                      whyNeedsYou: 'o vermelho é pré-existente, não desta obra — conserte esses testes e relance o /sprint; o motor não tem lista de teste ignorado, e nenhum bloco fecha verde em cima de suíte que já nasceu vermelha' })
      break
    }
  }

  // ORQUESTRAR — Opus #1, no tier da rodada. r==1: decompõe o plano inteiro; r>1: só o
  // DELTA do feedback. NUNCA re-arquiteta; buraco que exige decisão de arquitetura
  // vira blocker (não vira tarefa). Recebe o LEDGER: quem monta a onda sabe o que já
  // foi julgado, consertado e confirmado — e vigia os antipadrões conhecidos.
  const decomp = await agent(orquestradorPrompt({ planPath: ARGS.planPath, planText: ARGS.planText, round: r, feedback,
                                                  ledger: trilho() }),
    { model: tier.model, effort: tier.effort, phase: 'Decompor',
      label: r === 1 ? 'orquestrar:r1 (plano inteiro)' : `orquestrar:r${r} (delta)`, schema: DECOMP })
  // Orquestrador morto derruba a rodada inteira (não há tarefa a executar). Sai do laço em
  // vez de estourar — o que já foi construído nas rodadas anteriores continua valendo.
  if (!decomp) {
    blockers.push({ what: `orquestrador da rodada ${r} não respondeu`,
                    whyNeedsYou: 'sem decomposição não há o que executar nesta volta' })
    break
  }
  if (decomp.blockers?.length) blockers.push(...decomp.blockers)

  // ── O ID DA TAREFA TEM QUE EXISTIR NO PLANO (F9.58) ─────────────────────────
  // Medido em 2026-08-08: o orquestrador inventou OITO ids que o plano não tem —
  // `F21.5-R`, `F16.6-R`, `F11.1-R` e cia., o sufixo que ele criou para "a mesma
  // tarefa, revisada". Seis delas foram EXECUTADAS e o trabalho ficou órfão: a
  // marcação recusou uma a uma com "passo 'F21.5-R' não existe no plano", e o
  // resultado é o pior dos dois mundos — o disco mudou e o plano diz que não.
  //
  // A regra é do SCRIPT porque o orquestrador já foi instruído em prosa a copiar o
  // id, e inventou assim mesmo. Aqui o id é conferido contra o arquivo: o que não
  // existe não vira tarefa, vira Bloqueio nomeado, e ninguém é solto nele.
  const idsDoPlano = new Set(ARGS.planIds || [])
  if (idsDoPlano.size) {
    const forjados = decomp.tasks.filter(t => !idsDoPlano.has(t.id))
    for (const t of forjados) {
      blockers.push({ taskId: t.id, kind: 'id-inexistente',
        what: `o orquestrador criou a tarefa ${t.id}, que não existe no plano`,
        whyNeedsYou: `nenhum executor foi solto nela — se o trabalho é real, ele precisa de um passo no plano com id próprio` })
    }
    decomp.tasks = decomp.tasks.filter(t => idsDoPlano.has(t.id))
  }

  // ── QUEM ESPERA O DONO SAI DA DECOMPOSIÇÃO, NÃO SÓ DA FILA (F9.59) ──────────
  // O `esperaDono` tirava a tarefa da FILA e a deixava na decomposição — então ela
  // voltava a ser decomposta em toda rodada, entrava em `missingTasks` do revisor
  // em toda rodada, e o dono a via cinco vezes no relatório. Medido em 2026-08-08:
  // 41 tarefas listadas como faltantes em 3+ rodadas, e as 10 congeladas entre elas.
  // Decompor custa o tier caro; decompor o que ninguém vai executar é gasto puro.
  const congeladas = decomp.tasks.filter(t => t.esperaDono)
  if (congeladas.length) {
    log(`${congeladas.length} tarefa(s) esperam você e saíram da decomposição desta rodada`)
  }

  // ── A RÉGUA DO `pronto` É COBRADA POR CÓDIGO, NÃO SÓ NA PROSA (F8.2 · S-14) ──
  // O julgamento do critério existia só como instrução ao #1, e instrução em prosa não
  // recusa nada: bastou o orquestrador não julgar para o critério-armadilha chegar
  // inteiro ao executor, que o cumpriu escrevendo o valor à mão dentro do entregável.
  // Aqui o script roda a MESMA régua do plano (`regua_pronto.py`, do plugin project-skills) sobre
  // o `pronto` de CADA tarefa, ANTES de qualquer executor sair. Reprovado não vira tarefa:
  // sai de `decomp.tasks` e vira Bloqueio de `kind: 'criterio'` — o passo da spec é que
  // precisa reescrever o critério, e isso é do dono.
  // Agente mudo NÃO recusa nada (fail-open, mesma direção da reserva): travar a missão
  // por infra de gate é pior que gate nenhum, e o gate real do critério é o revisor.
  const regua = await agent(reguaPrompt({ repoRoot: ARGS.repoRoot,
                                          criterios: decomp.tasks.map(t => ({ id: t.id, pronto: t.pronto })) }),
    { model: ARGS.model, effort: T.mechanical.effort, phase: 'Decompor',
      label: `regua:r${r} (${decomp.tasks.length} criterios)`, schema: REGUA })
  const bancada = new Map((regua?.reprovados || []).map(x => [x.task_id, x.motivo]))
  for (const t of decomp.tasks.filter(t => bancada.has(t.id))) {
    blockers.push({ taskId: t.id, kind: 'criterio',
                    what: `o critério de aceite de ${t.id} é bancada: ${bancada.get(t.id)}`,
                    whyNeedsYou: `nenhum executor foi solto nesta tarefa — reescreva o \`pronto\` do passo "${t.requisito || t.id}" na spec para dizer o que REGERA o artefato a partir do dado real, e rode o motor de novo` })
  }
  decomp.tasks = decomp.tasks.filter(t => !bancada.has(t.id))

  // DIAGNÓSTICO de tarefa-presa — antes de tentar de novo, escala quem já reaparece
  // ≥ churnThreshold rodadas seguidas pro diagnose_model (medium): causa raiz, não repetição.
  //
  // ── A CAUSA APONTADA NÃO ENTRA SEM SOBREVIVER AO DESAFIO (autópsia 2026-08-09) ──
  // Diagnóstico solto vira conserto de sintoma: a primeira explicação plausível entra no
  // feedback, o executor conserta ONDE o defeito apareceu, e os outros pontos com a mesma
  // causa ficam de pé — foi a regressão medida na sessão de 2026-08-08. Agora quem
  // investiga PARA na causa, e um desafiador recebe a causa com a ordem de PROVAR QUE ELA
  // ESTÁ ERRADA. Os dois trocam até concordarem (o desafio da volta anterior vai junto na
  // seguinte); três voltas sem acordo não escolhem vencedor — viram Bloqueio "precisa de
  // você" com as duas versões escritas, porque causa em disputa não é causa.
  const diagnoses = []
  for (const t of decomp.tasks) {
    if (taskChurn[t.id] >= churnThreshold) {
      const d = await investigaCausa(t, taskChurn[t.id])
      if (d.causa) {
        diagnoses.push({ task_id: t.id, diagnosis: d.causa, desafiada: true, deCache: !!d.deCache })
        // causa de REPOSITÓRIO para o motor no MESMO turno: nada mais é despachado
        // para morrer na mesma porta (autópsia 2026-08-09).
        if (d.escopo === 'repositorio') { paraPorCausaGlobal(d, t.id); break }
      } else {
        blockers.push({ taskId: t.id, kind: 'causa-em-disputa',
          what: `a causa de ${t.id} não sobreviveu ao desafio: investigador diz "${d.disputa?.investigador || 'sem resposta'}" · desafiador diz "${d.disputa?.desafiador || 'sem veredito'}"`,
          whyNeedsYou: 'três voltas de investigação e desafio sem acordo — causa em disputa não vira conserto; decida qual versão vale ou aponte a terceira' })
      }
    }
  }
  if (desligadoPor === 'causa-global') break

  // EXECUTAR — Opus 5 em todo tier (R8). executor_model (padrão) ou mechanical_model
  // (tarefa marcada complexity:'mechanical' — operação bem delimitada, sem julgamento
  // amplo). Só o effort varia; o modelo é sempre opus.
  // QUEM DEPENDE DE PASSO PARADO NASCE PARADO (F9.20). Sem isto o motor tentava a cada
  // rodada o que não tinha como funcionar, falhava igual, e a tarefa entrava no churn como
  // se fosse executor incompetente — gastando o diagnose_model caro pra redescobrir a
  // dependência. Bloqueio se propaga por transitividade: quem depende de quem espera, espera.
  const parado = new Set(blockers.map(b => b.taskId).filter(Boolean))
  for (const t of decomp.tasks) if (t.esperaDono) parado.add(t.id)
  let cresceu = true
  while (cresceu) {
    cresceu = false
    for (const t of decomp.tasks) {
      if (!parado.has(t.id) && (t.dependsOn || []).some(d => parado.has(d))) {
        parado.add(t.id); cresceu = true
      }
    }
  }
  const todo = decomp.tasks.filter(t => !t.done && !parado.has(t.id))

  // ── PARA OU PULA — repetir sem mudança de estado é proibido (autópsia) ──────
  // A impressão é do que a tarefa RECEBE: o critério, os arquivos e os achados que
  // voltaram sobre ela. Impressão igual à da última tentativa = o mesmo trabalho
  // pelo mesmo preço — a tarefa é PULADA, declarada, e o dono decide o que muda.
  const fpDe = t => JSON.stringify([t.pronto, (t.files || []).slice().sort(),
    (feedback?.gaps || []).filter(g => g.task_id === t.id).map(g => g.problem).sort()])
  const puladas = []
  const fpNova = {}   // a comparação é contra a RODADA anterior, nunca dentro da mesma
  for (const t of [...todo]) {
    const fp = fpDe(t)
    // quem está numa ESCALADA declarada (alegação repetida a caminho do auditor,
    // reincidência a caminho do diagnóstico) não é pulado: a escalada É a mudança
    // de estado, e pular aqui mataria o caminho que o motor mesmo abriu. Quem parou
    // no TETO também não: "não deu tempo" sai com mais rodada por definição.
    if ((taskChurn[t.id] || 0) > 0 || (impossivelChurn[t.id] || 0) > 0 ||
        estouraramTeto.has(t.id)) {
      fpNova[t.id] = fp
      continue
    }
    if (impressaoTarefa[t.id] === fp) {
      puladas.push(t.id)
      todo.splice(todo.indexOf(t), 1)
      blockers.push({ taskId: t.id, kind: 'pulada',
        what: `a tarefa ${t.id} voltou com a MESMA impressão de estado da tentativa anterior e foi PULADA`,
        whyNeedsYou: 'repetir sem mudança de estado não conserta nada — mude o que a tarefa recebe (spec, conserto, destrava) e relance' })
    } else fpNova[t.id] = fp
  }
  Object.assign(impressaoTarefa, fpNova)
  if (puladas.length) log(`puladas por estado repetido: ${puladas.join(' · ')}`)

  // ESPERA APARECE COMO ESPERA, NÃO COMO FALHA (F8.4 · S-23). Sair da fila não basta:
  // sem esta lista o passo que espera um ato SEU some do relatório — nem feito, nem
  // faltando, nem bloqueado — e você não descobre que a missão parou esperando você.
  // A cadeia é semeada SÓ pelo `esperaDono`: tarefa parada por `blocker` já sai em
  // `impedidos`, e repeti-la aqui mandaria você agir duas vezes pelo mesmo motivo.
  const esperaChain = new Map(decomp.tasks.filter(t => t.esperaDono)
    .map(t => [t.id, `espera um ato seu: ${t.esperaDono}`]))
  let herdou = true
  while (herdou) {
    herdou = false
    for (const t of decomp.tasks) {
      const de = (t.dependsOn || []).filter(d => esperaChain.has(d))
      if (!esperaChain.has(t.id) && de.length) {
        // quem depende espera JUNTO, e o motivo nomeia de quem: sem o nome, o recado
        // vira "espera" sem dizer o que destrava.
        esperaChain.set(t.id, `depende de ${de.join(' · ')}, que espera você`); herdou = true
      }
    }
  }
  const esperandoVoce = decomp.tasks.filter(t => !t.done && esperaChain.has(t.id))
    .map(t => ({ taskId: t.id, motivo: esperaChain.get(t.id) }))

  // ── ONDA ESTÉRIL ENCERRA A CORRIDA (autópsia 2026-08-09) ────────────────────
  // Medido na corrida wf_5438d704: as ondas 4 e 5 decompuseram 40 e 30 tarefas e
  // executaram ZERO — a fila inteira estava parada por blocker ou espera, e o motor
  // seguiu pagando a decomposição (a parte cara) para não despachar ninguém. Onda que
  // separa e não tem UM executável não melhora com mais rodada: ou o que trava é seu
  // (esperandoVoce), ou é impedimento confirmado (impedidos) — os dois já estão no
  // relatório. Rodar de novo é o mesmo resultado pelo mesmo preço.
  if (decomp.tasks.length && !todo.length) {
    desligadoPor = 'onda-esteril'
    rounds.push({ r, decomp, results: [], review: null, esperandoVoce })
    blockers.push({ what: `onda ${r} estéril: ${decomp.tasks.length} tarefa(s) separadas e nenhuma executável — tudo parado por blocker ou espera`,
                    whyNeedsYou: 'mais rodada repete o mesmo vazio pelo mesmo preço — destrave o que espera você, ou recorte a missão' })
    break
  }

  // ── RESERVA DE ARQUIVOS ENTRE MOTORES (F9.2) ────────────────────────────────
  // Mais de um motor pode estar vivo na MESMA sessão, e dois motores escrevendo o
  // MESMO arquivo é um apagando o trabalho do outro — com o dono ausente, ninguém
  // vê acontecer. Por isso o motor REGISTRA a lista da onda ANTES de soltar
  // executor, rodando `hooks/reserva-de-arquivos.sh reservar <sessão> <motor> <arquivos>`.
  // Lista que CRUZA com a de um motor vivo volta RECUSADA, e aí esta onda não sai.
  // Lista disjunta passa: o gate separa quem se encosta, não serializa a sessão.
  // `touchesShared` acima resolve colisão DENTRO deste motor (sub-lote serial); isto
  // aqui é a colisão com OUTRO motor, que nenhuma das duas ondas enxerga sozinha.
  const arquivosDaOnda = [...new Set(todo.flatMap(t => t.files || []))]
  if (arquivosDaOnda.length) {
    const reserva = await agent(reservaPrompt({ verbo: 'reservar', sessionId: ARGS.sessionId,
                                                motorId: ARGS.motorId, files: arquivosDaOnda }),
      { model: ARGS.model, effort: T.mechanical.effort, phase: 'Executar',
        label: `reserva:r${r} (${arquivosDaOnda.length} arquivos)`, schema: RESERVA })
    // Fail-open, mesma direção do hook: quem foi consultar e não voltou não recusa nada.
    // Travar a missão por infra de gate é pior que gate nenhum.
    if (reserva?.recusado) {
      desligadoPor = 'reserva'
      blockers.push({ what: `outro motor desta sessão já reservou: ${(reserva.arquivos || []).join(' · ')}`,
                      whyNeedsYou: 'dois motores no mesmo arquivo é um apagando o trabalho do outro — espere o outro terminar (ele libera ao sair) ou recorte a missão para arquivos que não encostem nos dele' })
      break
    }
  }
  const execTier = t => ({ model: ARGS.model,
    effort: t.complexity === 'mechanical' ? T.mechanical.effort : T.executor.effort })
  // ── O RETORNO AO ORQUESTRADOR É POR BLOCO, NÃO POR ONDA INTEIRA (F9.57 · S-141) ──
  // O laço era decompor-tudo → executar-tudo → revisar-tudo: quem falhava no primeiro
  // executor só era notado depois que o último dos vinte voltasse. A onda segue saindo
  // em blocos de `blocoMax`, e o PRIMEIRO bloco que traz falha (`done: false` ou
  // `impossivel`) FECHA a onda ali: os blocos seguintes não são despachados, entram no
  // `missing` da volta seguinte, e o orquestrador re-decompõe o delta já sabendo o que
  // quebrou. Falha cedo com onda longa era trabalho jogado em cima de premissa furada.
  const blocoMax = ARGS.blocoMax || 4
  const blocos = []
  for (let i = 0; i < todo.length; i += blocoMax) blocos.push(todo.slice(i, i + blocoMax))
  const respostas = []
  const naoDespachadas = []
  let blocoQueFalhou = null
  // o estado do ciclo por bloco — consolidado no registro da onda, lá embaixo
  let b = 0, ultimaSuite = null
  const blocosVerdes = [], marcadosDaOnda = [], reprovadasNosBlocos = [], docsDaOnda = []
  for (const bloco of blocos) {
    // bloco depois da falha não sai: é este `continue` que faz o motor reagir ANTES de a
    // onda terminar. Eles voltam pro #1 como faltantes, não como fracasso de ninguém.
    if (blocoQueFalhou) { naoDespachadas.push(...bloco.map(t => t.id)); continue }
    const par = bloco.filter(t => t.parallelizable && !(t.dependsOn?.length))
    const seq = bloco.filter(t => !t.parallelizable || (t.dependsOn?.length))
    // quem NÃO colide vai junto; quem colide vai depois, um de cada vez, no MESMO repo
    const livres = par.filter(t => !touchesShared(t, par))
    const colidem = par.filter(t => touchesShared(t, par))
    // `tetoMin` vai em TODO execPrompt: o teto tem que chegar a quem tem relógio. O script
    // não tem (ver o vigia), então teto que ficasse só aqui não seria teto de ninguém.
    // `buildWarm` vai junto, pelo mesmo motivo: quem compila é o executor, e cache quente
    // que não chega a ele é cache que ele derruba com um `clean` de rotina.
    const builtPar = await parallel(livres.map(t => () =>
      agent(execPrompt({ task: t, tetoMin: tetoExecutorMin, buildWarm }), {
        model: execTier(t).model, effort: execTier(t).effort, phase: 'Executar', label: `exec:${t.id}`, schema: TASK_RESULT })))
    for (const t of colidem.concat(seq)) builtPar.push(await agent(execPrompt({ task: t, tetoMin: tetoExecutorMin, buildWarm }),
      { model: execTier(t).model, effort: execTier(t).effort, phase: 'Executar', label: `exec:${t.id}`, schema: TASK_RESULT }))
    // Filtra AQUI, dos dois lados: `parallel()` devolve null pra thunk que falhou, e o
    // executor sequencial devolve null pelo mesmo motivo (agente morto). Um `null` em
    // `results` vira `TypeError` no revisor — a tarefa some do relato em vez de reaparecer
    // em `missingTasks`, que é o caminho que a manda de volta pro #1.
    const doBloco = builtPar.filter(Boolean)
    respostas.push(...doBloco)
    // Agente morto conta como falha do bloco: ele não voltou, e seguir despachando em
    // cima disso é o mesmo trabalho jogado fora que a falha declarada causa.
    const falhou = doBloco.filter(x => x.done === false || x.impossivel)
    if (falhou.length || doBloco.length < bloco.length) {
      blocoQueFalhou = falhou.map(x => x.task_id)
    }

    // ── O CICLO CURTO FECHA NO BLOCO (decisão do dono, 2026-08-09) ────────────
    // Antes, revisão, suíte, marcação, commit, doc e colheita eram UMA vez por onda:
    // o trabalho de doze tarefas ficava fora do histórico até a última voltar, e o
    // defeito descoberto no fim já era fundação das tarefas seguintes — F11.15 foi
    // devolvida TRÊS vezes pela revisão de onda antes desta mudança. Agora cada
    // bloco fecha o ciclo inteiro, e a onda vira a passada GERAL (ver abaixo).
    b++
    const entregues = [...new Map(doBloco.filter(x => x?.done && !x.espera && x.task_id)
      .map(x => [x.task_id, x])).values()]
    if (!entregues.length) continue

    // 1 · REVISOR POR TAREFA — fidelidade ao `pronto`, cobertura e qualidade, um
    // agente por entrega, independente de quem executou. O escopo é UMA tarefa;
    // defeito que só existe no par é do revisor do bloco, logo abaixo.
    const porTarefa = await parallel(entregues.map(x => () =>
      julga(revisorTarefaPrompt({ task: decomp.tasks.find(t => t.id === x.task_id),
                                  entrega: x, round: r, bloco: b, ledger: trilho() }),
        { model: ARGS.model, effort: T.coordinate.effort, phase: 'Revisar',
          label: `rev-tarefa:${x.task_id}`, schema: TAREFA_REVIEW })))
    const reprovadasNaTarefa = new Set()
    for (let i = 0; i < entregues.length; i++) {
      const v = porTarefa[i]
      // veredito mudo não aprova nem reprova: a tarefa segue pro revisor do bloco
      // SEM o carimbo — degradar para um julgamento só é melhor que travar o bloco.
      if (!v) continue
      if (!v.aprova) {
        reprovadasNaTarefa.add(entregues[i].task_id)
        // achado GRAVE investiga a causa ANTES de voltar ao orquestrador (decisão
        // do dono: severidade também dispara, não só reincidência) — com o cache.
        if ((v.gaps || []).some(g => sevRank(g.severity) >= floor)) {
          const d = await investigaCausa(decomp.tasks.find(t => t.id === entregues[i].task_id), 1)
          if (d.causa && d.escopo === 'repositorio') paraPorCausaGlobal(d, entregues[i].task_id)
          if (d.causa) diagnoses.push({ task_id: entregues[i].task_id, diagnosis: d.causa,
                                        desafiada: true, deCache: !!d.deCache })
          else if (d.disputa) blockers.push({ taskId: entregues[i].task_id, kind: 'causa-em-disputa',
            what: `a causa do achado grave de ${entregues[i].task_id} não sobreviveu ao desafio: investigador diz "${d.disputa.investigador}" · desafiador diz "${d.disputa.desafiador}"`,
            whyNeedsYou: 'causa em disputa não vira conserto — decida qual versão vale ou aponte a terceira' })
        }
      }
    }
    for (let i = 0; i < entregues.length; i++) if (porTarefa[i])
      ledgerCorrida.push({ r, tipo: 'veredito', taskId: entregues[i].task_id,
                           resumo: `revisor-tarefa r${r}b${b}: ${porTarefa[i].aprova ? 'aprovou' : 'reprovou'}` })
    if (desligadoPor === 'causa-global') break
    const aprovadasTarefa = entregues.filter(x => !reprovadasNaTarefa.has(x.task_id))
    reprovadasNosBlocos.push(...reprovadasNaTarefa)
    if (!aprovadasTarefa.length) { blocoQueFalhou = [...reprovadasNaTarefa]; continue }

    // 2 · REVISÃO DO BLOCO — os MESMOS eixos, sobre as entregas JUNTAS, mais
    // COESÃO. Não herda o veredito por tarefa: dois arquivos que se contradizem, ou
    // a cobertura que uma tarefa achou que a outra faria, só existem no conjunto.
    const revBloco = await julga(revisorBlocoPrompt({ planPath: ARGS.planPath, repoRoot: ARGS.repoRoot,
        tasks: aprovadasTarefa.map(x => decomp.tasks.find(t => t.id === x.task_id)),
        entregas: aprovadasTarefa, round: r, bloco: b, lawMark, ledger: trilho() }),
      { model: ARGS.model, effort: T.coordinate.effort, phase: 'Revisar',
        label: `rev-bloco:r${r}b${b}`, schema: BUILD_REVIEW })
    if (revBloco) ledgerCorrida.push({ r, tipo: 'veredito', taskId: null,
      resumo: `revisor-bloco r${r}b${b}: ${(revBloco.gaps || []).length} gap(s), ${(revBloco.missingTasks || []).length} faltante(s)` })
    // revisor de bloco mudo não aprova NINGUÉM — as entregas voltam pro orquestrador
    const reprovadasNoBloco = new Set(revBloco
      ? [...(revBloco.gaps || []).map(g => g.task_id), ...(revBloco.missingTasks || [])].filter(Boolean)
      : aprovadasTarefa.map(x => x.task_id))
    reprovadasNosBlocos.push(...[...reprovadasNoBloco].filter(id => !reprovadasNaTarefa.has(id)))
    const aprovadas = aprovadasTarefa.filter(x => !reprovadasNoBloco.has(x.task_id))
    if (!aprovadas.length) continue

    // 3 · SUÍTE INTEIRA — 147s por bloco, medidos; é o que separa "preservado" de
    // "gravei a quebra". Vermelha fecha a onda aqui, e nada deste bloco é marcado.
    const suiteB = await agent(runSuitePrompt({ repoRoot: ARGS.repoRoot, round: r, bloco: b }),
      { model: ARGS.model, effort: T.mechanical.effort, phase: 'Suíte', label: `suite:r${r}b${b}`, schema: SUITE_RESULT })
    if (suiteB?.heartbeat) ultimoSinalDeVida = suiteB.heartbeat
    ultimaSuite = suiteB; ultimaSuiteMissao = suiteB
    if (!suiteB || !suiteB.green) {
      blockers.push({ what: `a suíte quebrou no bloco ${b} da rodada ${r}: ${suiteB?.failing?.join(' · ') || 'sem veredito'}`,
                      whyNeedsYou: 'bloco vermelho não vira ponto de salvamento — o conserto volta pelo orquestrador' })
      blocoQueFalhou = aprovadas.map(x => x.task_id)
      continue
    }

    // 4 · MARCAÇÃO + COMMIT + DOC + COLHEITA — a trava de 2026-08-09 (revisor de
    // acordo + suíte verde) agora no grão do bloco, não da onda.
    if (ARGS.planPath?.endsWith('.plan.json')) {
      const tick = await agent(tickPlanPrompt({ planPath: ARGS.planPath,
        passos: aprovadas.map(t => ({ taskId: t.task_id,
          evidencia: `${t.summary} · ${(t.files_touched || []).join(' ')}` })) }),
        { model: ARGS.model, effort: T.mechanical.effort, phase: 'Marcar',
          label: `marcar r${r}b${b} (${aprovadas.length})`, schema: TICK_RESULT })
      const vistos = new Map((tick?.marcados || []).map(m => [m.task_id, m]))
      for (const t of aprovadas) {
        const v = vistos.get(t.task_id)
        if (!v) blockers.push({ taskId: t.task_id,
          what: `o passo ${t.task_id} foi ENTREGUE mas não voltou no veredito da marcação`,
          whyNeedsYou: 'o trabalho está no disco e o plano diz que não — marque à mão com a prova do executor' })
        else if (!v.ok) blockers.push({ taskId: t.task_id,
          what: `a marcação de ${t.task_id} foi recusada: ${v.motivo || 'sem motivo'}`,
          whyNeedsYou: 'recusa por decisão em aberto é legítima — resolva a pendência do passo e marque' })
        else {
          marcadosNaMissao.add(t.task_id)
          ledgerCorrida.push({ r, tipo: 'marcado', taskId: t.task_id,
                               resumo: `marcado no plano r${r}b${b}` })
        }
      }
      marcadosDaOnda.push(...(tick?.marcados || []))
    }
    await agent(checkpointPrompt({ repoRoot: ARGS.repoRoot, round: r, bloco: b, results: aprovadas, planPath: ARGS.planPath }),
      { model: ARGS.model, effort: T.mechanical.effort, phase: 'Salvar', label: `commit r${r}b${b}` })
    blocosVerdes.push({ bloco: b, feitos: aprovadas.map(x => x.task_id), placar: suiteB.placar })
    const tocadosB = [...new Set(aprovadas.flatMap(x => x?.files_touched || []))]
    if (tocadosB.length) {
      // TODOS os documentos afetados, a cada bloco — decisão do dono (2026-08-09),
      // ciente do custo: doc grande pode ser reescrito mais de uma vez na onda, e o
      // conflito disso é achado da revisão geral de doc, não deste passo.
      const doc = await agent(docTouchPrompt({ repoRoot: ARGS.repoRoot, round: r, files: tocadosB, sessionId: ARGS.sessionId }),
        { model: ARGS.model, effort: T.mechanical.effort, phase: 'Doc', label: `doc r${r}b${b}`, schema: DOC_TOUCH })
      docsDaOnda.push(...(doc?.docs || []))
      if (!(doc?.docs || []).length) blockers.push({
        what: `a doc do bloco ${b} da rodada ${r} não foi confirmada no disco`,
        whyNeedsYou: 'o próximo bloco vai decidir por um mapa vencido — re-projete a doc destes arquivos' })
    }
    // colheita a cada bloco — decisão do dono: a máquina fica limpa o tempo todo
    await agent(colheitaPrompt({ repoRoot: ARGS.repoRoot, round: r }),
      { model: ARGS.model, effort: T.mechanical.effort, phase: 'Limpeza', label: `limpeza r${r}b${b}` })
  }

  // ── UM EXECUTOR LENTO NÃO SEGURA A RODADA (F9.29) ───────────────────────────
  // Medido em 2026-08-06: 21 agentes já entregues esperaram 2 HORAS por um só que
  // ciclava, e a rodada não fechou pra ninguém — a onda só termina quando o último
  // volta. O teto está no texto do executor (regra 4); o que é do SCRIPT é o que
  // fazer com quem estourou: `espera: true` NÃO é resultado. Sai de `results` (o
  // revisor não recebe meia obra como obra), entra no `missing` do #1 na volta
  // seguinte, e a rodada FECHA com quem voltou. Sem esta separação, o teto do
  // executor seria só um jeito mais educado de perder o trabalho da onda.
  // a parada por causa global registra a rodada antes de sair: os blocos que já
  // fecharam verdes ficam no retrato, e o relatório sabe ONDE a corrida parou.
  if (desligadoPor === 'causa-global') {
    rounds.push({ r, decomp, results: respostas.filter(x => !x.espera), review: null,
                  diagnoses, checkpoint: blocosVerdes.length > 0, blocos: blocosVerdes,
                  feitos: blocosVerdes.flatMap(x => x.feitos),
                  marcados: marcadosDaOnda, doc: docsDaOnda })
    break
  }

  const esperaIds = respostas.filter(x => x.espera).map(x => x.task_id)
  for (const id of esperaIds) estouraramTeto.add(id)
  const results = respostas.filter(x => !x.espera)

  // ── BLOQUEIO REPETIDO CONVOCA O AUDITOR (F9.18 · S-26) ──────────────────────
  // Executor que declara impossível NÃO encerra nada sozinho — aconteceu de um executor
  // declarar impossível o que ele conseguia fazer com a ferramenta que já tinha na mão.
  // A alegação que SE REPETE na mesma tarefa (≥ churnThreshold rodadas seguidas) convoca
  // o auditor, com a lente invertida: o ônus é dele provar que NÃO dá, e ele recebe a
  // lista do que havia à mão pra dizer o que o executor nem tentou. Dois desfechos, e os
  // dois são do script: derruba devolve a tarefa ao loop com o que ele apontou; confirma
  // encerra como impedimento real, com o motivo escrito.
  const devolvidasPeloAuditor = []
  const alegam = new Set(results.filter(x => x.impossivel).map(x => x.task_id))
  for (const t of todo) impossivelChurn[t.id] = alegam.has(t.id) ? (impossivelChurn[t.id] || 0) + 1 : 0
  for (const x of results.filter(x => x.impossivel && impossivelChurn[x.task_id] >= churnThreshold)) {
    const parecer = await julga(auditorPrompt({ task: decomp.tasks.find(t => t.id === x.task_id),
                                                ledger: trilho(),
                                                alegacao: x.impossivel, ferramentas: x.ferramentas || [],
                                                onus: 'invertido — cabe a VOCÊ provar que não dá; o executor não precisa provar que dá',
                                                cobra: 'diga em naoTentou quais das ferramentas acima o executor nem tentou',
                                                tentativas: impossivelChurn[x.task_id] }),
      { model: ARGS.model, effort: T.diagnose.effort, phase: 'Diagnose', label: `auditor:${x.task_id}`, schema: AUDITOR })   // diagnose_model
    x.done = false
    // Auditor mudo NÃO encerra nada: quem não respondeu não confirmou impedimento nenhum,
    // e encerrar no silêncio dele seria voltar a encerrar no "impossível" do executor.
    if (!parecer || parecer.derruba) {
      impossivelChurn[x.task_id] = 0
      devolvidasPeloAuditor.push({ taskId: x.task_id,
        motivo: parecer ? `o auditor derrubou a alegação: ${parecer.motivo}` : 'o auditor não respondeu — a alegação não foi confirmada',
        naoTentou: parecer?.naoTentou || [] })
    } else {
      blockers.push({ taskId: x.task_id, kind: 'impedimento',
        what: `impedimento real em ${x.task_id}, confirmado pelo auditor: ${parecer.motivo}`,
        whyNeedsYou: 'a alegação do executor foi auditada com a lente invertida e confirmada — não sai com mais uma rodada' })
    }
  }

  // ── ARQUIVO SOB TRANCA: O ENTREGÁVEL É A PROPOSTA (F8.5) ────────────────────
  // Esta skill proíbe reescrever documento aprovado, e o orquestrador continuava
  // fabricando tarefa cujo `pronto` só fecha editando um. A tranca mandava o agente a
  // uma porta que ela mesma trancou. Tarefa `protegido` entrega PROPOSTA com antes e
  // depois LITERAIS, e o critério inverte: arquivo intocado é o resultado CERTO.
  const protegidas = new Set(decomp.tasks.filter(t => t.protegido).map(t => t.id))
  for (const x of results.filter(x => protegidas.has(x.task_id))) {
    if (!x.proposta?.antes || !x.proposta?.depois) {
      // Sem os dois lados literais não há o que o dono aplique: descrição obriga ele a
      // reescrever do zero. Não conta como entregue — e como vira blocker COM taskId, a
      // tarefa nasce parada na volta seguinte em vez de ser tentada de novo contra a tranca.
      x.done = false
      blockers.push({ taskId: x.task_id,
                      what: `a tarefa ${x.task_id} toca arquivo sob tranca e voltou sem proposta com antes e depois literais`,
                      whyNeedsYou: 'sem o texto literal dos dois lados não há o que aplicar — o arquivo continua intocado, que é o certo' })
    } else {
      blockers.push({ taskId: x.task_id,
                      what: `proposta para ${x.proposta.arquivo} (sob tranca): ${x.summary}`,
                      whyNeedsYou: `nenhum arquivo foi alterado — git diff vazio aqui é o resultado CERTO; aplicar é seu, porque o de acordo é seu.\nANTES:\n${x.proposta.antes}\nDEPOIS:\n${x.proposta.depois}` })
    }
  }

  // REVISÃO GERAL DA OBRA — Opus #2, no tier da rodada. Os blocos já revisaram por
  // tarefa e por lote; aqui a pergunta muda de fonte: julga O QUE ESTÁ NO REPOSITÓRIO,
  // no escopo dos arquivos desta onda — nunca o repo inteiro (outros trabalhos escrevem
  // nele, e achado sobre trabalho alheio vira conserto que ninguém pediu). Eixos: spec +
  // constituição (pelo doc-load: julga contra o que ele lista como régua, citando a
  // passagem) + rastreio + completude + COESÃO DO CONJUNTO. A decomposição entra como
  // meio, não como contrato — a régua de hoje é a que o doc-load lista (a lei:
  // constituicao.md, quality-goals.md, constraints.md; o acordo aprovado: blueprint.md,
  // features.md e irmãos). Fail-open: régua ausente = eixo não roda, e isso NÃO é gap.
  // NÃO roda a suíte nem caça bug — isso é o /qa-loop depois.
  // `lawMark` vai junto: na rodada 1 é null (o #2 calcula e devolve); nas seguintes é a
  // marca FIXADA, contra a qual ele mede — não contra o texto que estiver no disco agora.
  // `protegidas` vai junto: nelas o critério do #2 é o INVERSO do normal — proposta com
  // antes/depois literais aprova, e arquivo protegido aparecendo no git diff reprova.
  const filesDaOnda = [...new Set(results.flatMap(x => x?.files_touched || []))]
  const review = await julga(reviewBuildPrompt({ planPath: ARGS.planPath, planText: ARGS.planText, repoRoot: ARGS.repoRoot, decomp, results, round: r, lawMark, protegidas: [...protegidas], files: filesDaOnda, ledger: trilho() }),
    { model: tier.model, effort: tier.effort, phase: 'Revisar', label: `rev-geral:r${r}`, schema: BUILD_REVIEW })

  // AGENTE MORTO NÃO PODE DERRUBAR O MOTOR. `agent()` devolve null quando o subagente
  // morre por erro terminal (limite de sessão, erro de API depois dos retries) ou quando o
  // usuário o pula. Sem esta guarda, `review.gaps` levanta TypeError e o script inteiro
  // aborta — perdendo TODAS as rodadas já concluídas. Medido em 2026-08-02: uma execução
  // deste motor morreu exatamente assim, com 8 dos 12 agentes já entregues, e o resultado
  // veio como falha total em vez de "faltaram 4".
  //
  // A direção segura é NÃO declarar built: revisor que não respondeu não aprovou nada.
  // Vira blocker e o loop segue — a missão degrada, não morre.
  if (!review) {
    blockers.push({ what: `revisor da rodada ${r} não respondeu, ou voltou duas vezes sem a âncora do fim`,
                    whyNeedsYou: 'a obra desta rodada ficou SEM revisão — trate como não verificada' })
    rounds.push({ r, decomp, results, review: null, diagnoses, espera: esperaIds, esperandoVoce,
                  devolvidas: devolvidasPeloAuditor, naoDespachadas })
    feedback = { gaps: [], missing: [...esperaIds, ...naoDespachadas, ...devolvidasPeloAuditor.map(d => d.taskId)],
                 diagnoses, devolvidas: devolvidasPeloAuditor, blocoQueFalhou }
    continue
  }

  // MARCA DA LEI — congelada na 1ª volta. Sem o pino, cada rodada media contra o
  // arquivo que estivesse no disco naquele instante: editar a constituição no meio da
  // missão trocava a régua CALADA, e a rodada 1 e a 4 aprovavam coisas diferentes sem
  // ninguém saber. O pino é do motor, não da memória do revisor.
  if (review.lawMark) {
    if (lawMark === null) lawMark = review.lawMark
    else if (review.lawMark !== lawMark) {
      // Não troca o pino: a missão segue medindo contra a lei fixada, e a mudança vira
      // aviso no relatório pro dono julgar o que fazer com as rodadas já aprovadas.
      blockers.push({ what: `a lei do projeto mudou durante a missão (marca ${lawMark} → ${review.lawMark}, rodada ${r})`,
                      whyNeedsYou: 'as rodadas anteriores foram medidas contra o texto antigo — confira o que mudou antes de aceitar a obra' })
    }
  }

  // ── ACHADO SOBRE PASSO JÁ MARCADO → RE-TICK, NUNCA ID NOVO (furo 1) ─────────
  // O bloco marcou; a revisão geral achou defeito. Sem esta regra o plano diria
  // "feito" com a revisão dizendo "defeituoso" — a contradição de 2026-08-09 por
  // outra porta. O conserto volta ao loop e, quando fechar num bloco futuro, o tick
  // REGRAVA a prova do MESMO id; id novo é recusado pela trava de id inexistente.
  const reticks = [...new Set((review.gaps || []).map(g => g.task_id)
    .filter(id => id && marcadosNaMissao.has(id)))]
  if (reticks.length) log(`revisão geral reabriu passo já marcado: ${reticks.join(' · ')} — o conserto regrava a prova do mesmo id`)

  // ── REVISÃO GERAL DA DOC (decisão do dono, 2026-08-09) ──────────────────────
  // O doc-touch por bloco atualiza o delta; aqui os documentos afetados são relidos
  // INTEIROS contra o estado de agora — inclusive o conflito de dois blocos que
  // reescreveram o mesmo documento. O papel CONSERTA doc minerada na hora; doc
  // autoral (a marca `authored-by: human`) ele nunca toca — vira aviso ao dono.
  if (filesDaOnda.length) {
    const revDoc = await julga(revisaoDocPrompt({ repoRoot: ARGS.repoRoot, files: filesDaOnda, round: r }),
      { model: ARGS.model, effort: T.coordinate.effort, phase: 'Revisar',
        label: `rev-doc:r${r}`, schema: DOC_REVIEW })
    if (revDoc) {
      rounds.length && (void 0)   // (registro entra no rounds.push desta rodada, abaixo)
      for (const g of (revDoc.gaps || []).filter(g => g.autoral)) {
        blockers.push({ what: `a doc AUTORAL contradiz o repositório: ${g.problem} (${g.arquivo})`,
                        whyNeedsYou: 'documento seu — nenhum agente o corrige; atualize ou grave correcao-pendente: no frontmatter' })
      }
    } else {
      blockers.push({ what: `a revisão geral da doc da rodada ${r} não respondeu`,
                      whyNeedsYou: 'os documentos desta onda ficaram sem a releitura inteira — confira antes de confiar neles' })
    }
  }

  // A CONCEPÇÃO ERROU — a execução descobriu algo que contradiz um documento já
  // aprovado. O motor NÃO reescreve documento do dono: o gap vira aviso no relatório
  // propondo reabrir a etapa (a linha `correcao-pendente:` que ELE grava), e não volta
  // pro #1 — não há o que o executor conserte no código.
  for (const g of (review.gaps || []).filter(g => g.kind === 'concepcao')) {
    blockers.push({ what: `a concepção está errada: ${g.problem}`,
                    whyNeedsYou: 'reabra a etapa — grave `correcao-pendente:` no frontmatter do documento e reaprove; nenhum documento foi alterado aqui' })
  }

  // Executor morto entra pela mesma porta: `results` já vem filtrado com `.filter(Boolean)`,
  // então a tarefa dele reaparece como faltante no próximo `missingTasks` e volta pro #1.

  // churn de tarefa — conta rodadas SEGUIDAS, não acumuladas. Set por rodada: 2 gaps na
  // mesma tarefa contam 1, e quem NÃO reapareceu ZERA. Sem o zerar, uma tarefa resolvida
  // na rodada 3 ainda dispararia o diagnóstico caro na 5 por causa do placar antigo.
  //
  // ── QUEM NUNCA FOI TENTADO NÃO REINCIDE (F9.56) ─────────────────────────────
  // O contador media "reapareceu como faltante", e faltante é o que o REVISOR não viu
  // sair — o que inclui quem nunca entrou na fila. O passo com `esperaDono` sai de
  // `todo` corretamente, mas volta em `missingTasks` na volta seguinte, reincide, e na
  // segunda dispara o `diagnose_model` (o tier caro) perguntando "por que essa tarefa
  // não sai do lugar?" sobre uma tarefa que o próprio motor decidiu não executar.
  // Medido em 2026-08-08: 13 diagnósticos assim, 22,7M tokens — 59% do gasto do papel.
  // A régua: o contador é de QUEM FALHOU, e quem nem foi tentado não falhou.
  // `naoDespachadas` entra pela mesma porta (F9.57): bloco que não saiu porque um anterior
  // falhou não é tarefa presa — ninguém a tentou nesta volta.
  const naoTentado = new Set([...parado, ...esperaChain.keys(), ...naoDespachadas])
  const stuck = new Set([...(review.missingTasks || []), ...(review.gaps || []).map(g => g.task_id)]
                        .filter(id => id && !naoTentado.has(id)))
  for (const t of decomp.tasks) taskChurn[t.id] = stuck.has(t.id) ? (taskChurn[t.id] || 0) + 1 : 0
  ledgerCorrida.push({ r, tipo: 'veredito', taskId: null,
    resumo: `revisão geral r${r}: ${(review.gaps || []).length} gap(s), ${(review.missingTasks || []).length} faltante(s)` })

  // ── CORRIDA EM CÍRCULO — o detector genérico (autópsia 2026-08-09) ──────────
  // Blindagem além da porta do commit: QUALQUER trava futura com o mesmo padrão —
  // rodadas que giram sem o estado mudar — cai aqui, sem precisar de causa nomeada.
  // A impressão inclui as INVESTIGAÇÕES da rodada: repetição antes do diagnóstico
  // não é círculo (a escada do motor ainda tem degrau); repetição DEPOIS dele é.
  const fpRodada = JSON.stringify([[...stuck].sort(),
    (review.gaps || []).map(g => `${g.task_id || '-'}:${g.kind}`).sort(),
    diagnoses.map(d => d.task_id).sort()])
  // bloco verde fechado é AVANÇO (commit, marcação): rodada com verde não é círculo
  // mesmo que os faltantes se repitam — o círculo é girar sem mover nada. Rodada
  // com verde também não ARMA a comparação: círculo é sequência de rodadas estéreis.
  const emCirculo = stuck.size > 0 && blocosVerdes.length === 0 && fpRodada === fpRodadaAnterior
  fpRodadaAnterior = blocosVerdes.length === 0 ? fpRodada : null

  rounds.push({ r, decomp, results, review, diagnoses, espera: esperaIds, esperandoVoce,
                devolvidas: devolvidasPeloAuditor, naoDespachadas })

  // ── O SALVAMENTO ACONTECEU POR BLOCO — a onda só CONSOLIDA o registro ───────
  // Suíte, marcação, commit, doc e colheita rodaram dentro de cada bloco (o ciclo
  // curto, acima). O que a onda grava aqui é o retrato: quantos blocos fecharam
  // verdes, o que cada um marcou, e o último placar — é dele que `andamento.avanco`
  // deriva o "sem avanço" entre ondas.
  rounds[rounds.length - 1].placar = ultimaSuite?.placar
  rounds[rounds.length - 1].checkpoint = blocosVerdes.length > 0
  rounds[rounds.length - 1].blocos = blocosVerdes
  rounds[rounds.length - 1].feitos = blocosVerdes.flatMap(x => x.feitos)
  rounds[rounds.length - 1].marcados = marcadosDaOnda
  rounds[rounds.length - 1].doc = docsDaOnda
  rounds[rounds.length - 1].reticks = reticks
  if (reprovadasNosBlocos.length) {
    rounds[rounds.length - 1].naoMarcados = { motivo: 'reprova do revisor de tarefa ou de bloco',
                                              ids: [...new Set(reprovadasNosBlocos)] }
    log(`não marcados por reprova nos blocos: ${[...new Set(reprovadasNosBlocos)].join(' · ')}`)
  }

  // a parada do detector de círculo: depois do registro da rodada, antes dos freios
  // de consumo — o que parou aqui fica no retrato, e o motivo sai nomeado.
  if (emCirculo) {
    desligadoPor = 'corrida-em-circulo'
    blockers.push({ what: `corrida em círculo: a rodada ${r} terminou com a MESMA impressão de estado da rodada anterior`,
                    whyNeedsYou: 'mais rodada repete o mesmo resultado pelo mesmo preço — destrave o que os achados apontam e relance' })
    break
  }

  // ── DISJUNTOR POR CONSUMO (F9.12) ───────────────────────────────────────────
  // Conta o que ESTA missão gastou (spent() é do turno inteiro, então mede o delta) e
  // desliga por conta própria. Quem para é o motor, não o runtime, pra o relatório poder
  // dizer ONDE parou — "acabou o orçamento" sem a rodada não ajuda ninguém.
  const gasto = gastoAgora() - gastoInicial
  if (tokenBudget && gasto >= tokenBudget) {
    desligadoPor = 'orcamento'
    blockers.push({ what: `disjuntor: a missão gastou ${gasto} de ${tokenBudget} tokens e se desligou na rodada ${r}`,
                    whyNeedsYou: 'o que faltou está nas tarefas abertas do plano — relance com teto maior se valer' })
    break
  }

  // ── VIGIA POR TEMPO (F9.13 + F9.24) ─────────────────────────────────────────
  // Registro mudo por tempo demais é travamento, e de DENTRO ninguém enxerga isso. O
  // sinal de vida é a onda ter fechado; quem não fechou nada há silenceLimitMin está
  // parado. MAS parada com trabalho vivo NÃO é travamento: agente rodando uma suíte de
  // 11 minutos parece agente morto, e os dois calam igual. Por isso a condição é dupla.
  const agora = ARGS.now + (rounds.length ? 0 : 0)   // a casca reinjeta o relógio por rodada
  // o sinal de vida vem da ÚLTIMA suíte de bloco — foi ela que atualizou o relógio no ciclo
  const mudo = agora - ultimoSinalDeVida
  if (mudo > silenceLimitMs && !ultimaSuiteMissao?.trabalhoVivo) {
    desligadoPor = 'vigia'
    blockers.push({ what: `vigia: nada mudou no registro há ${Math.round(mudo / 60000)} min e não há trabalho vivo`,
                    whyNeedsYou: 'travamento, não demora — o último estado salvo é o checkpoint da rodada anterior' })
    break
  }

  // desvio de spec e falta de requisito/pronto seguram a obra SEMPRE: nascem em severidade
  // >= floor, e se o revisor devolver abaixo o script os mantém no filtro. Sem isso um gap
  // de spec P2/P3 sairia da conta e passaria calado — o freio é do script, não da memória
  // do revisor.
  // gap de concepção sai do filtro por decisão: ele já virou aviso acima, e segurar a obra
  // por ele empurraria o motor a "consertar" código que está certo.
  const holdsBuild = g => g.kind !== 'concepcao' && (g.kind === 'spec' || g.kind === 'rastreio' || sevRank(g.severity) >= floor)
  const gaps = (review.gaps || []).filter(holdsBuild)

  // BUILT — no caminho feliz a confirmação independente é o /qa-loop --headless da etapa
  // seguinte (Fase Gate + confirm-pass DELE), então aqui declara direto. SEM qa-loop na
  // máquina (hasQaLoop=false) não existe segunda checagem lá na frente: o motor NÃO pode
  // fechar no veredito barato da rodada — roda o confirm-pass dedicado em finalize_model.
  if (review.complete && review.cohesive && gaps.length === 0) {
    if (ARGS.hasQaLoop === false) {
      const confirm = await julga(confirmBuildPrompt({ planPath: ARGS.planPath, planText: ARGS.planText, repoRoot: ARGS.repoRoot, decomp, results, lawMark }),
        { model: ARGS.model, effort: T.finalize.effort, phase: 'Confirmar',
          label: `confirmar:r${r}`, schema: BUILD_REVIEW })   // finalize_model
      rounds[rounds.length - 1].confirm = confirm
      // Mesma guarda do revisor, e aqui a direção segura é mais dura ainda: este pass é a
      // ÚNICA segunda checagem que existe quando não há /qa-loop adiante. Ele não responder
      // significa que ninguém confirmou nada — declarar `built` seria dar por pronto no
      // veredito de um agente que morreu.
      if (!confirm) {
        blockers.push({ what: 'o confirm-pass não respondeu, ou voltou duas vezes sem a âncora do fim',
                        whyNeedsYou: 'sem /qa-loop e sem confirm, NADA checou a obra — não considere entregue' })
        break
      }
      const confirmGaps = (confirm.gaps || []).filter(holdsBuild)
      if (!confirm.complete || !confirm.cohesive || confirmGaps.length) {
        // o confirm achou o que a rodada barata perdeu — processa, não ignora
        feedback = { gaps: confirm.gaps.filter(g => g.kind !== 'concepcao'), missing: confirm.missingTasks, diagnoses }
        continue
      }
    }
    built = true; break
  }
  // sem o gap de concepção: ele é aviso pro dono, não tarefa pro #1 re-decompor.
  // quem parou no teto entra no `missing` mesmo que o revisor não o tenha listado: ele não
  // falhou, só não coube na onda — e sem isto a tarefa sumiria do delta da próxima volta.
  // a tarefa que o auditor DERRUBOU volta pro loop mesmo que o revisor não a tenha listado:
  // o desfecho "derruba" é justamente devolvê-la, e sem isto ela sumiria do delta da volta.
  // o bloco que não foi despachado entra no `missing` mesmo sem o revisor listá-lo: ele não
  // falhou nem sumiu, foi o motor que fechou a onda cedo por causa da falha do bloco anterior.
  feedback = { gaps: review.gaps.filter(g => g.kind !== 'concepcao'),
               missing: [...new Set([...(review.missingTasks || []), ...esperaIds,
                                     ...naoDespachadas, ...reprovadasNosBlocos,
                                     ...devolvidasPeloAuditor.map(d => d.taskId)])],
               reticks,   // conserto de passo já marcado REGRAVA a prova do mesmo id
               diagnoses, devolvidas: devolvidasPeloAuditor, blocoQueFalhou }   // alimenta o DECOMPOR da próxima volta
}

// ── A CONFERÊNCIA FINAL RODA MESMO NA PARADA (autópsia 2026-08-09) ────────────
// O confirm só existia no caminho feliz sem /qa-loop, e o /qa-loop da etapa seguinte só
// roda depois de built=true — parada por teto, vigia ou onda estéril deixava TUDO sem
// segunda checagem. Foi assim que 17 passos ficaram marcados sem conferência válida na
// corrida wf_5438d704. Agora quem para sem terminar confere o que as ondas entregaram,
// e o relatório diz QUAL conferência rodou (`conferidoPor`).
// Exceção única: parada por ORÇAMENTO não confere — o disjuntor é teto duro, e gastar
// um agente a mais depois dele é o disjuntor deixando de ser disjuntor. O relatório
// carrega o motivo em `conferidoPor`, então a ausência não passa calada.
let conferidoPor = built ? (ARGS.hasQaLoop === false ? 'confirm-pass' : 'qa-loop da etapa seguinte') : 'nenhuma'
const entregouAlgo = rounds.some(x => (x.feitos || []).length)
if (!built && entregouAlgo && desligadoPor !== 'orcamento') {
  const ultima = rounds[rounds.length - 1]
  const confirmFinal = await julga(confirmBuildPrompt({ planPath: ARGS.planPath, planText: ARGS.planText,
      repoRoot: ARGS.repoRoot, decomp: ultima.decomp,
      results: rounds.flatMap(x => x.results || []).filter(Boolean), lawMark }),
    { model: ARGS.model, effort: T.finalize.effort, phase: 'Confirmar', label: 'confirm-na-parada', schema: BUILD_REVIEW })
  rounds[rounds.length - 1].confirmFinal = confirmFinal
  if (!confirmFinal) {
    blockers.push({ what: 'a missão parou no meio e a conferência final não respondeu',
                    whyNeedsYou: 'nada checou o que as ondas entregaram — trate os passos marcados como não conferidos' })
  } else {
    conferidoPor = 'confirm-na-parada'
    // gap achado aqui não volta pro loop — a missão já parou. Vira aviso NOMEADO, para o
    // conserto entrar como tarefa no plano em vez de morrer no relatório.
    for (const g of (confirmFinal.gaps || [])) {
      blockers.push({ taskId: g.task_id || undefined,
        what: `a conferência final da parada achou defeito${g.task_id ? ` em ${g.task_id}` : ''}: ${g.problem}`,
        whyNeedsYou: 'a missão já parou — este conserto vira tarefa no plano, não sai sozinho' })
    }
  }
}

// O QUE FALTOU, SEPARADO POR MOTIVO (F9.19). Os dois chegavam misturados, e quem lê não
// sabia se esperava mais uma rodada ou se tinha que agir. São perguntas diferentes:
// impedimento não sai com mais tempo — falta de tempo sai.
const impedidos = blockers.filter(b => b.whyNeedsYou).map(b => ({ ...b, motivo: b.what }))
// quem parou no teto do executor é falta de tempo por definição — sai aqui, com o motivo,
// e NUNCA em `impedidos`: mandar o dono agir sobre uma tarefa que só precisava de outra
// volta é o mesmo erro que este par de listas existe pra desfazer.
const naoDeuTempo = rounds.length
  ? [...(rounds[rounds.length - 1].review?.missingTasks || []).map(id => ({ taskId: id })),
     ...(rounds[rounds.length - 1].espera || []).map(id => ({ taskId: id, motivo: `passou do teto de ${tetoExecutorMin} min do executor` }))]
  : []
// ESPERA NÃO É FALHA (F8.4). Terceira lista, e não um pedaço das outras duas: não sai com
// mais rodada (então não é `naoDeuTempo`) e não é impedimento descoberto no caminho (então
// não é `impedidos`) — é um ato SEU que o plano já declarava, e o dependente espera junto.
const esperandoVoce = rounds.length ? (rounds[rounds.length - 1].esperandoVoce || []) : []

// A ÚLTIMA passada do caminhão do lixo NÃO é aqui (F9.38): ela é o passo 3 da
// Persistência, em bash. Aqui ela viraria mais um agente disparado DEPOIS do
// disjuntor — e o desligamento por teto deixaria de ser desligamento. Lá ela roda
// pelo mesmo motivo que o `rm` do sinal: aconteça o que acontecer com o motor.

// PROGRESSO DA MISSÃO (F9.35) — passos DISTINTOS fechados, nunca linhas de resultado.
// A mesma tarefa fecha em mais de uma onda quando a retomada regrava o veredito do cache;
// somar linha inflava o número que o relatório mostra ao dono.
const passosFeitos = [...new Set(rounds.flatMap(x => x.feitos || []))]

// VOLTAS POR PROBLEMA (F25.4) — o mesmo cálculo do motor de revisão (`/qa-loop`), sobre os
// gaps do #2: da volta em que o gap apareceu até a última em que ainda aparecia. É o laço
// fechado ficando legível — sem isto o relatório dizia quantas rodadas a MISSÃO levou, e
// nunca qual defeito foi reaberto volta após volta. Chave = tarefa + eixo do gap: o gap não
// tem id próprio, e só o `task_id` juntaria dois problemas diferentes da mesma tarefa.
const voltasPorProblema = []
const porGap = {}
for (const x of rounds)
  for (const g of (x.review?.gaps || [])) {
    const k = `${g.task_id || '-'}:${g.kind}`
    if (!porGap[k]) voltasPorProblema.push(porGap[k] =
      { taskId: g.task_id || null, kind: g.kind, problem: g.problem, primeira: x.r, voltas: 0 })
    porGap[k].voltas = x.r - porGap[k].primeira + 1
  }

// ── ÚLTIMO ATO: apagar o sinal da barra e soltar a reserva de arquivos ───────
// Vem DEPOIS de tudo e ANTES do return, então alcança TODO caminho de saída — obra
// pronta, teto, vigia, disjuntor, onda estéril, causa global. A casca continua
// apagando também (cinto e suspensório); e a barra varre o que passar dos dois
// (`andamento.py:expira_sinais`).
//
// UMA EXCEÇÃO, e só uma: o motor que a RESERVA recusou. `andamento.py encerra` apaga
// por SESSÃO, não por motor — quem sai por `reserva` nunca reservou nem acendeu nada,
// e encerrar aqui apagaria o sinal do OUTRO motor da mesma sessão, que segue vivo (a
// barra dele sumiria: `pretooluse-motor-arma.sh` desarma sem o sinal).
if (desligadoPor !== 'reserva')
  await agent(encerraPrompt({ sessionId: ARGS.sessionId, motorId: ARGS.motorId,
                              motivo: desligadoPor || (built ? 'obra de pé' : 'teto de rodadas') }),
    { model: ARGS.model, effort: T.mechanical.effort, phase: 'Limpeza', label: 'encerra:barra' })

return {
  rounds, built, blockers, lawMark,   // lawMark = a lei contra a qual a missão INTEIRA foi medida
  ledger: ledgerCorrida,   // o trilho da corrida: quem julgou o quê, quando — vai pro relatório
  voltasPorProblema,   // por gap: em que volta apareceu e quantas levou até a rodada limpa
  progresso: { feitos: passosFeitos.length, passos: passosFeitos },   // por tarefa distinta
  impedidos,          // não sai com mais rodada — precisa de você
  naoDeuTempo,        // sairia com mais rodada; o teto é que chegou antes
  esperandoVoce,      // nem falha nem falta de tempo: espera um ato seu, declarado no plano
  gasto: gastoAgora() - gastoInicial,
  stopReason: desligadoPor || (built ? 'build-complete' : 'max-rounds'),
  conferidoPor,       // qual segunda checagem rodou: qa-loop adiante · confirm-pass · confirm-na-parada · nenhuma
  // `tasks` conta TAREFA distinta da onda, não linha de `results` (F9.35): linha repetida
  // pelo replay do cache e linha sem `task_id` (a da decomposição) não são passos.
  telemetry: rounds.map(x => ({ round: x.r,
                                tasks: new Set((x.results || []).filter(t => t?.task_id)
                                                               .map(t => t.task_id)).size,
                                gaps: x.review?.gaps.length ?? null,
                                checkpoint: !!x.checkpoint })),
}
```

**TODO prompt do motor ABRE declarando o papel, em uma linha sozinha: `PAPEL: <NOME>`.** É a primeira linha do texto que o agente recebe, e por isso a primeira linha do transcript dele — que é o único lugar onde a autópsia (`improve-workflow/lib/medidor.py`) consegue saber quem foi cada um dos agentes do run. Sem a declaração, o papel era **adivinhado pela frase** ("Você é o EXECUTOR…"): bastava reescrever a prosa do motor para 50 agentes virarem `DESCONHECIDO` na tabela, e a medição por papel deixar de existir sem nada acusar. O nome é fixo por prompt, em caixa alta e sem acento:

| prompt | `PAPEL:` | prompt | `PAPEL:` |
|---|---|---|---|
| `orquestradorPrompt` | `ORQUESTRADOR` | `reguaPrompt` | `MECANICO` |
| `saudePrompt` | `MECANICO` | | |
| `execPrompt` | `EXECUTOR` | `reservaPrompt` | `MECANICO` |
| `reviewBuildPrompt` | `REVISOR` | `checkpointPrompt` | `MECANICO` |
| `confirmBuildPrompt` | `CONFIRMADOR` | `docTouchPrompt` | `MECANICO` |
| `auditorPrompt` | `AUDITOR` | `colheitaPrompt` | `MECANICO` |
| `diagnoseStuckTaskPrompt` | `DIAGNOSTICO` | `tickPlanPrompt` | `MARCAR` |
| `desafioCausaPrompt` | `DESAFIADOR` | `runSuitePrompt` | `SUITE` |

A declaração é a **primeira linha do corpo**, sozinha, antes de qualquer prosa — o corpo do `execPrompt` acima mostra a forma. Quem cobra que a regra continue no texto é `lib/test_travas_motor.py` (bloco `S-123`), que reescreve a prosa em volta da linha e confere no `medidor.py` que a classificação fica de pé.

### E TODA chamada leva `label` — o nome que o dono lê na tela

A declaração `PAPEL:` serve à autópsia, que lê transcript. Quem serve ao **dono olhando a
tela de andamento** é o `label` da chamada, e ele é **obrigatório em todas**. Sem ele a tela
nomeia o agente pelo começo do prompt — que agora é justamente `PAPEL: X`, seguido do corpo
cortado no meio. Medido em 2026-08-09: sete papéis apareceram como
`PAPEL: DIAGNOSTICO Repositório: /Users/…`, indistinguíveis entre si, e a pergunta que a tela
existe para responder — *qual tarefa está em diagnóstico, em que volta, qual rodada está
decompondo* — não tinha resposta.

O rótulo diz **o que** e **sobre o quê**, nunca o papel sozinho: `causa:F11.11 v2` é
governança, `DIAGNOSTICO` é ruído. A forma por etapa:

| etapa | rótulo | etapa | rótulo |
|---|---|---|---|
| saúde | `saude:r<N>` | suíte | `suite:r<N>b<B>` |
| orquestrador | `orquestrar:r1 (plano inteiro)` · `orquestrar:r<N> (delta)` | marcação | `marcar r<N>b<B> (<n>)` |
| régua do `pronto` | `regua:r<N> (<n> criterios)` | commit | `commit r<N>b<B>` |
| reserva | `reserva:r<N> (<n> arquivos)` | doc | `doc r<N>b<B>` |
| executor | `exec:<taskId>` | colheita | `limpeza r<N>b<B>` |
| revisor por tarefa | `rev-tarefa:<taskId>` | investigação de causa | `causa:<taskId> v<volta>` |
| revisão do bloco | `rev-bloco:r<N>b<B>` | desafio da causa | `desafia:<taskId> v<volta>` |
| revisão geral | `rev-geral:r<N>` | auditor | `auditor:<taskId>` |
| revisão da doc | `rev-doc:r<N>` | confirmação | `confirmar:r<N>` · `confirm-na-parada` |

Veredito recusado por falta da âncora sai com `↻ sem âncora` colado no mesmo rótulo — senão
a segunda volta aparece com o nome idêntico à primeira e a recusa fica indistinguível de
trabalho repetido.

Quem cobra é `lib/test_motor_js.py` (checagem D): toda linha com `phase:` tem que trazer
`label:` na mesma linha ou na de baixo. Regra em prosa não pegou — o motor rodou sete
chamadas sem rótulo com a instrução já escrita.

**Schemas (JSON Schema, resumidos):**
- `TAREFA_REVIEW` — `{ aprova: bool, gaps: [{kind, severity, problem}], anchor }`, devolvido por `revisorTarefaPrompt` (`coordinate_model`). O revisor POR TAREFA: abre o `pronto` da tarefa, o diff dos arquivos dela e julga três eixos — **fidelidade** (o critério foi cumprido de verdade, no disco?), **cobertura** (o teste morde? — os cinco antipadrões valem aqui) e **qualidade** (o que saiu respeita a régua que o `doc-load` do projeto lista). Independente de quem executou; escopo = UMA tarefa, nunca o par. Achado com severidade ≥ floor dispara a investigação de causa ANTES de a tarefa voltar ao orquestrador (com o cache — a mesma raiz não paga duas investigações). Como todo veredito, sem `anchor` é recusado e roda de novo.
- `revisorBlocoPrompt` — devolve `BUILD_REVIEW` (`coordinate_model`). A revisão FINAL do bloco: os MESMOS eixos do revisor por tarefa, sobre as entregas do bloco JUNTAS, mais **coesão** — dois arquivos que se contradizem, cobertura que uma tarefa achou que a outra faria. **Não herda o veredito por tarefa**: reabre os eixos sobre o conjunto. É o de acordo dele (junto com a suíte verde) que libera marcação, commit e doc do bloco.
- `DOC_REVIEW` — `{ ok: bool, consertados: [caminho...], gaps: [{arquivo, problem, autoral: bool}], anchor }`, devolvido por `revisaoDocPrompt` (`coordinate_model`), uma vez por onda. A revisão GERAL da doc: relê INTEIROS os documentos afetados pelos arquivos da onda — não só o delta pendente — procurando contradição com o repositório de agora e conflito entre reescritas de blocos. Doc minerada errada ele CONSERTA na hora e devolve em `consertados` (cada caminho conferido no disco); doc AUTORAL (`authored-by: human`) ele NUNCA toca — vira gap com `autoral: true`, que o script transforma em aviso ao dono. Como todo veredito, sem `anchor` é recusado.
- `DECOMP` — `{ tasks: [{ id, desc, requisito, pronto, files: [...], parallelizable: bool, dependsOn: [id...], done: bool, complexity?: 'standard'|'mechanical', esperaDono?: string, protegido?: string }], blockers: [{ what, whyNeedsYou }] }`. **`requisito` e `pronto` são obrigatórios** — `requisito` = o item da spec que a tarefa atende, `pronto` = o critério de feito dele, **os dois copiados da spec, não redigidos pelo orquestrador** (o executor não tem como cumprir o que não recebe, e critério inventado aqui vira régua falsa no #2). Item da spec sem um dos dois vira `blocker`, não tarefa. `complexity: 'mechanical'` = operação bem delimitada (renomear, mover arquivo, 1 config, 1 valor); ausente/`'standard'` = tarefa normal. **`esperaDono`** = a frase do ato que só o dono pode fazer, **copiada do `espera_dono` do passo no `.plan.json`** — nunca inventada aqui, e nunca deduzida do texto da tarefa. Tarefa com `esperaDono` **não entra na fila do motor** (nenhum executor é solto nela), e quem `dependsOn` dela também não: os dois saem em `esperandoVoce`, com o motivo. Passo sem o campo no plano é tarefa normal. **`protegido`** = o arquivo sob tranca que a tarefa toca (o que traz `status: approved` no frontmatter) e o motivo da tranca, marcado pelo orquestrador **por leitura do disco**, nunca por achismo. Tarefa `protegido` **entra na fila** — o que muda é o entregável: proposta, não edição, e o revisor a mede pelo critério invertido.
- `TASK_RESULT` — `{ task_id, files_touched: [...], summary, done: bool, note, anchor, espera: bool, impossivel?: string, ferramentas?: [...], proposta?: { arquivo, antes, depois } }`. **`impossivel`** = a alegação de que a tarefa não tem como sair, com o motivo; **`ferramentas`** = o que havia à mão no contexto dela. Alegar não encerra nada: repetida por `churnThreshold` rodadas seguidas na mesma tarefa, ela convoca o `AUDITOR`. **`proposta`** = o entregável da tarefa `protegido` (regra 5 do executor): `antes` e `depois` **literais**, o primeiro copiado do disco e o segundo pronto pra colar. O script cobra os dois — proposta sem um deles vira `done: false` e Bloqueio, porque descrição do que mudar deixa o trabalho todo pro dono. Com os dois, a proposta sai em **Bloqueios (precisam de você)** com o antes/depois inteiro, e `git diff` vazio no arquivo é o resultado certo. **`anchor`** = a última linha não vazia do que o executor leu para decidir que estava pronto — a prova de leitura inteira (ver "o juiz prova que leu"). **`espera`** = o executor bateu no `tetoMin` e parou por isso (regra 4 dele). O script tira essas do `results` — o revisor não recebe meia obra como obra — e as manda pro `missing` do #1 na volta seguinte; a rodada **fecha com quem voltou**. `espera: true` não é falha e não vira Bloqueio: sai em `naoDeuTempo`, com o teto no motivo.
- `AUDITOR` — `{ derruba: bool, motivo, naoTentou: [...], anchor }`, devolvido por `auditorPrompt` (`diagnose_model`). A lente é **invertida**: o ônus é do auditor provar que **não dá**, e ele recebe `ferramentas` — o que havia à mão — para dizer em `naoTentou` o que o executor nem tentou. `derruba: true` **devolve a tarefa ao loop** (ela entra no `missing` do #1 na volta seguinte, com o que o auditor apontou); `derruba: false` **encerra como impedimento real** — Bloqueio de `kind: 'impedimento'` com o `motivo` escrito. Auditor mudo não encerra nada: a tarefa volta pro loop, porque quem não respondeu não confirmou impedimento. Como todo veredito, sem `anchor` ele é recusado e o papel roda de novo.
- `SAUDE` — `{ fechada: bool, motivo, saida }`, devolvido por `saudePrompt` (`mechanical_model`), na largada de **toda** rodada. Papel **mecânico e só**: roda os checks determinísticos da casa a partir da raiz — os mesmos que o gate de commit consulta (`python3 scripts/desacoplamento_check.py` e vizinhos listados em `.claude/hooks/release-gate.sh`, quando existirem) — e devolve `fechada: true` com `motivo` (uma linha) e `saida` (a saída crua) quando **qualquer** um reprova o estado atual do repositório. É a guarda **catchall** da autópsia de 2026-08-09: a porta fechada de hoje era o commit; a de amanhã pode ser outra, e o que fecha o motor é o check reprovando, não o nome da doença. Fail-open nas duas pontas: projeto sem esses checks, check quebrado ou agente mudo ⇒ `fechada: false` — travar a corrida por infra de gate é pior que gate nenhum.
- `DESAFIO` — `{ procede: bool, motivo, escopo?, anchor }`, devolvido por `desafioCausaPrompt` (`diagnose_model`). **`escopo`** = `'tarefa'` ou `'repositorio'`, declarado **pelo par em acordo** — o desafiador que referenda diz até onde a causa alcança, e `'repositorio'` significa que ela mata QUALQUER trabalho novo, não só esta tarefa. É esse rótulo (nunca inferência do motor) que dispara a parada no mesmo turno e a chave global do cache de causa. Ausente ⇒ `'tarefa'`. O desafiador recebe a tarefa e a **causa** que o investigador apontou, com a ordem de **derrubá-la**: `procede: false` carrega em `motivo` o fato que a causa não explica ou a concorrente mais simples — e esse motivo volta ao investigador na volta seguinte (`desafioAnterior`). `procede: true` referenda, e só então o diagnóstico entra no `feedback` (`desafiada: true`). Três voltas sem acordo viram Bloqueio `kind: 'causa-em-disputa'` com as duas versões; desafiador mudo **não referenda**. Como todo veredito, sem `anchor` é recusado e roda de novo.
- `SUITE_RESULT` — `{ green: bool, failing: [nome...], placar, heartbeat, trabalhoVivo: bool }`. **`placar`** = a linha crua que a suíte imprimiu (`139 passou · 0 falhou`, `OK (56 checks)`, `17 ok / 0 falhas`), <!-- acopla-ok: exemplos do formato de placar reconhecido, não contagem deste repositório --> lida por `lib/andamento.py:placar` e comparada com a da onda anterior por `lib/andamento.py:avanco` — dois placares iguais seguidos saem como `sem avanço`. O veredito aparece nas **duas** superfícies: no cartão que fecha a onda (`hooks/posttooluse-andamento.sh`, que vê a saída crua da suíte) e na **barra** (`hooks/statusline-motor.sh` → `linha_placar`), que é a que fica. O registro é um só, em `~/.claude/andamento/placar-<sid>` — o motor guarda o campo na onda (`rounds[].placar`) e não o descarta mais. **`trabalhoVivo`** separa demora de travamento: com ele `true`, o vigia **não** derruba, por mais silencioso que esteja o registro. **`heartbeat`** = o carimbo de tempo do último sinal de vida, que a casca reinjeta a cada rodada (o script não tem relógio próprio).
- `blocker` de `kind: 'criterio'` — critério de aceite que só se cumpre injetando valor inventado dentro de entregável. Não vira tarefa: vira Bloqueio, e o `whyNeedsYou` diz qual passo da spec precisa reescrever o `pronto`. **Quem o emite é o SCRIPT**, logo depois da decomposição e antes de qualquer executor sair (ver o bloco da régua no esqueleto) — não é julgamento do #1.
- `REGUA` — `{ reprovados: [{ task_id, motivo }] }`. O papel é **mecânico e só**: para cada `{ id, pronto }` recebido, rodar

  ```bash
  printf '%s' "<pronto>" | python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/regua_pronto.py)" --onde <id> -
  ```

  ⚠️ **O caminho é RESOLVIDO POR NOME, nunca escrito à mão** — mesmo molde do `RESERVA` acima. Em 2026-08-08 um passo da própria missão moveu `plan_state.py` de plugin, o motor continuou apontando o lugar velho, e os 47 agentes de marcação **falharam no primeiro comando e gastaram 8,45M redescobrindo o rename**, cada um por conta própria. Pior: 14 deles acharam uma cópia errada (worktree antigo, cache) e gravaram no plano com um validador 548 linhas mais velho. **Todo caminho que o motor usa para si mesmo se resolve por nome.**

  e devolver em `reprovados` os que saíram com **exit 1**, com `motivo` = a linha que o programa imprimiu. Exit 0 não aparece na lista. **Sem julgamento próprio**: quem decide é o programa — a régua é uma só, a mesma que o `plan_state.py` cobra na gravação do plano, e re-julgar aqui por leitura faria o motor e o plano recusarem coisas diferentes. Programa ausente na máquina ou comando quebrado = `reprovados: []` (fail-open, como a reserva).
- `RESERVA` — `{ recusado: bool, arquivos: [caminho...] }`. O papel é **mecânico e só**: rodar `$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills hooks/reserva-de-arquivos.sh) reservar <sessionId> <motorId> <arquivo>...` e devolver o veredito do JSON que saiu — `recusado: true` quando veio `permissionDecision: "deny"`, com `arquivos` = os caminhos em disputa que a recusa nomeou. Script mudo = `recusado: false` (reservou). Sem julgamento próprio: quem decide é o hook, o agente só transporta.
- `tickPlanPrompt` — **com schema `TICK_RESULT`**, e a lista inteira da onda num agente só. Papel **mecânico e só**: gravar no plano os passos que acabaram de sair, rodando **um comando por passo, em sequência**:

  ```bash
  MARCADOR="$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/plan_state.py)"
  cd <raiz> && python3 "$MARCADOR" --dir <raiz>/.claude/plans tick <taskId> --evidencia "<evidencia>"
  ```

  **Um agente para a onda, não um por passo** — mas **N comandos em sequência**, nunca um julgamento em lote sobre N provas. A diferença é o que preserva as três coisas que o lote perderia, e as três foram medidas no run de 2026-08-08: o **isolamento de falha** (um `tick` morreu e os outros 45 seguiram), a **recusa individual** (um passo com decisão em aberto foi recusado pelo portão e os demais passaram), e a **fidelidade da prova** (ela é copiada do executor para dentro do comando, não redigida por quem marca).

  ⚠️ **O caminho é RESOLVIDO POR NOME.** Ver a nota do `REGUA` acima: caminho cravado aqui custou 8,45M numa única missão, e fez 14 marcações rodarem binário de outra árvore.

  ⚠️ **`cd <raiz>` antes do comando não é enfeite:** sem ele, a busca do agente por um arquivo com esse nome alcança as cópias em worktree e no cache do harness, que são versões antigas do mesmo programa — inclusive sem as funções de recusa.

  **Falha de um passo NÃO interrompe os seguintes.** Recusa do `tick` (decisão em aberto, passo fora do schema) é resultado legítimo e entra no veredito daquele passo; o agente segue para o próximo. Perder a onda por causa do registro é pior que o registro faltando.

  **O veredito de cada passo volta ao script, e o silêncio vira bloqueio.** Antes de 2026-08-08 este papel não tinha schema nem retorno guardado: um agente morreu com texto vazio, **nunca executou o tick**, e o passo entregue ficou gravado como não feito — sem que nada acusasse. Compare com `SUITE_RESULT` e `RESERVA`, que sempre tiveram schema e empurram blocker no nulo. Agora ele devolve `TICK_RESULT`, e o script trata: `agent()` nulo, lista vazia, ou passo entregue que não aparece no veredito ⇒ **Bloqueio nomeado**, com o id do passo.

  A prova é **a do executor** (`summary` + `files_touched` do `TASK_RESULT`), nunca redigida por quem marca: o `tick` recusa marcação sem prova, e prova inventada aqui seria o carimbo sem a obra. Plano que não é arquivo (`planPath` sem `.plan.json`) não é marcado por ninguém: o script nem chama este papel.

  **Terminada a marcação, registre a volta no disco** — um comando a mais, no fim:

  ```bash
  ANDAMENTO="$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/andamento.py)"
  python3 "$ANDAMENTO" onda <sessionId> <rodada> <planPath>
  ```

  É o que faz a **barra de status** dizer em que ponto a missão está (`lib/andamento.py:linha_onda` → `linha_motor`). A rodada só existe na memória do motor e o progresso só existe no arquivo do plano: sem este registro, quem volta ao terminal lê `missão há 2h14` sem saber se isso é a primeira volta ou a décima. **O total é contado pelo programa a partir do plano**, nunca pelo agente — quem marcou os passos acabou de gravá-los, e pedir a conta a quem marcou é o mesmo defeito do placar de suíte que o motor descartava. Falhar aqui **não** derruba nada: a barra volta a ser a de antes.

- `TICK_RESULT` — `{ marcados: [{ task_id, ok: bool, motivo }] }`. Uma entrada por passo que o agente tentou marcar, na ordem. `ok: false` carrega em `motivo` a linha que o `plan_state.py` imprimiu ao recusar — recusa legítima (decisão em aberto) e falha de comando chegam pelo mesmo campo, e quem separa é o script pela mensagem. **Passo que o script mandou marcar e não aparece na lista é tratado como perda silenciosa**, não como sucesso.
- `checkpointPrompt` — **sem schema** (nada volta pro script). Papel **mecânico e só**: gravar no **histórico do git** o que a onda verde produziu, rodando

  ```bash
  OK=""; for f in <arquivo...>; do git -C <raiz> add -- "$f" && OK="$OK $f" || echo "sprint: o git recusou $f — fica fora do ponto de salvamento da onda <r>"; done; [ -n "$OK" ] && git -C <raiz> commit -q -m "sprint: onda <r> bloco <b> verde" -- $OK || true
  ```

  ⚠️ **O `commit` também é por caminho, não só o `add`.** `git commit` sem pathspec grava o
  **índice inteiro** — arquivo que outra sessão apenas stageou no mesmo repositório entraria no
  commit da onda mesmo com o `add` nomeado (reproduzido: `git add outro.txt`, depois
  `git add -- a.py && git commit -m ...`, e `git show --stat` lista `outro.txt`). Por isso a
  mesma lista de arquivos aparece duas vezes na linha: uma para o `add`, outra para o `commit`.
  O que era de fora segue **staged e intacto**, para a sessão dona dele.

  ⚠️ **Caminho que o `git add` RECUSA não pode derrubar o salvamento.** Arquivo fora do
  repositório, ou que o executor declarou e não existe mais, faz o `add` sair não-zero — com um
  `&&` na frente do `commit`, a onda inteira ficava sem ponto de salvamento, e o `|| true` do
  fim engolia o erro sem ninguém ficar sabendo. Por isso o `add` é **um caminho de cada vez**: o
  que entrou vai para o commit, o que foi recusado sai numa linha nomeando o arquivo, e a onda
  ainda vira histórico com o resto. Nenhum caminho aceito ⇒ não há o que commitar, e aí sim o
  silêncio é o correto.

  ⚠️ **Os arquivos são NOMEADOS, nunca `add -A`.** A lista é a união dos `files_touched` dos
  `TASK_RESULT` que este bloco aprovou (chega no papel pelo `results`) — a mesma união que o
  `docTouchPrompt` recebe — **mais o `planPath`**, quando ele é `.plan.json`: os passos que o
  `tick` acabou de marcar são obra desta onda e sem ele o plano marcado ficaria fora do
  histórico. Varrer a árvore inteira engoliria trabalho de outra sessão aberta no mesmo
  repositório e o gravaria como se fosse da onda: `git show --stat` do commit tem que listar só
  o que o bloco tocou. Arquivo que o executor não declarou fica de fora — se ele mexeu sem
  declarar, isso é defeito do `TASK_RESULT`, não licença para varrer tudo.

  ⚠️ **O bloco entra na mensagem, e não é enfeite** (achado da re-projeção de 2026-08-09): o
  salvamento passou a ser POR BLOCO, então dois blocos da mesma onda escreveriam a mesma linha
  no histórico e ninguém saberia separar um do outro. O papel recebe `bloco` junto de `round`.

  É este commit que faz motor interrompido no meio (vigia, disjuntor, sessão morta) deixar os blocos já fechados **no histórico** em vez de soltas no disco — sem ele, quem chegar depois não tem como separar o que fechou verde do que ficou pela metade. Commit **local e só**: o push é uma vez, na persistência do fim. Árvore limpa faz o `commit` sair não-zero, e isso **não** é falha — o `|| true` é o fail-open, pela mesma regra do `tick`: perder a onda por causa do registro é pior que o registro faltando.
- `DOC_TOUCH` — `{ docs: [caminho...] }`, devolvido por `docTouchPrompt`. **`docs`** = os caminhos que a re-projeção TOCOU, e **só os que o disco confirma** (o papel confere cada um antes de devolver — caminho que ele não achou não entra na lista). Enquanto este papel não devolvia nada, "a doc foi re-projetada" era só a chamada ter saído: papel mudo, papel que invocou skill quebrada e papel que **mente ter feito** chegavam iguais ao script. **Lista vazia é Bloqueio** — não derruba a onda (o commit já está feito, mesma regra do `tick`), mas sai no relatório dizendo que a doc daquela rodada não foi confirmada, porque quem executar a onda seguinte vai ler a doc do repo de antes. O que fica registrado em `rounds[].doc` é o que o papel confirmou, nunca a lista que ele recebeu.
- `docTouchPrompt` — devolve `DOC_TOUCH`. Papel **mecânico e só**: **descobrir o nome de invocação** com `bash <raiz do project-skills>/lib/resolve-skill.sh doc-touch` e invocar a skill com o nome que sair (Skill tool), com a lista `files` — os arquivos que ESTA onda tocou (a união dos `files_touched` dos `TASK_RESULT`) — para que a doc deles seja re-projetada antes de a onda seguinte começar. Sem isso, quem executa a rodada seguinte lê a doc do repo de antes e decide por um mapa vencido. Roda **depois** do `checkpointPrompt` e só na onda verde: commit primeiro, porque o trabalho no histórico não pode depender de a doc dar certo; doc de repo quebrado documentaria a quebra. Onda sem arquivo tocado não chama este papel. Quem decide touch-vs-FULL é o próprio touch (mesma regra da Persistência) — aqui ele escala e segue, sem perguntar. Falha do touch **não derruba a onda**: o commit já está feito, e perder a onda por causa da doc é pior que a doc faltando. **Terminado o touch, devolva em `docs` os caminhos re-projetados** — cada um conferido no disco (`test -f`) antes de entrar na lista: caminho que você não achou fica de fora, mesmo que a skill diga ter escrito. **E grave essa mesma lista no disco** antes de devolver: `python3 <raiz do project-skills>/lib/andamento.py doc <sessionId> <rodada> <caminho...>`, que escreve `doc-<sid>` na casa do estado (`lib/andamento.py:doc_da_onda`) — ao lado do `placar-<sid>`, mesma chave por sessão e mesmo fail-open. Sem esse registro, `rounds[].doc` morre com o Workflow e ninguém consegue provar depois que a doc do commit seguinte saiu da onda em vez de uma passada manual. Falhar ao gravar **não** derruba a onda.
- `colheitaPrompt` — **sem schema** (nada volta pro script). Papel **mecânico e só**: mandar o lixeiro colher o que ESTA sessão anotou ter aberto, rodando

  ```bash
  LIXEIRO="$(bash "${CLAUDE_PLUGIN_ROOT}/skills/sprint/resolve-plugin.sh" lixeiro lib/lixeiro.py)"
  if [ -n "$LIXEIRO" ]; then
    python3 "$LIXEIRO" colhe-turno --sessao "$CLAUDE_CODE_SESSION_ID" \
      || echo "sprint: a colheita falhou em $LIXEIRO — segue sem colher"
  fi
  ```

  **O lixeiro é procurado pelo NOME, nunca pela posição.** Quem resolve é o `resolve-plugin.sh` da própria pasta: rodando do repositório o lixeiro é irmão direto, e instalado pelo marketplace o cache guarda `<marketplace>/<plugin>/<versão>/` — dois níveis acima e atrás de um segmento de versão, com a versão mais alta escolhida quando o cache tem várias. Apontar a pasta vizinha na mão resolvia só o primeiro caso, e a colheita nunca acontecia em máquina instalada. Saída vazia = lixeiro fora desta máquina. As duas falhas ficam **separadas**: lixeiro não instalado (nenhum caminho existe) sai **calado**, que é a regra escrita; caminho resolvido e comando quebrado avisa em uma linha — fail-open igual, mas visível, senão o defeito some. Sempre `colhe-turno`, nunca `colhe-sessao`: o modo do turno é o **seletivo** — efêmero ainda vivo (suíte, build) morre, serviço com CPU parada desde a passada anterior morre, serviço em uso **sobrevive**. É isso que deixa a colheita rodar no meio da missão sem tirar da onda seguinte o servidor que ela ia usar. Só é candidato o processo cuja ABERTURA foi anotada — nome de programa nunca é critério, e é o motor do lixeiro que aplica as travas (ancestral, VM, contêiner), não este papel. No script ele roda **junto do `checkpointPrompt`**, em toda onda verde. A última passada não é papel de agente: é o **passo 4 da Persistência**, o mesmo comando em bash — porque a colheita por onda não alcança o motor que fechou vermelho, que o vigia derrubou ou que o disjuntor desligou, e agente disparado depois do disjuntor desfaria o desligamento. Lixeiro ausente na máquina (`lixeiro.py` não existe) **não é falha**: o papel devolve sem fazer nada e a missão segue — limpeza é camada a mais, nunca pré-requisito. Falha da colheita **não derruba a onda** nem a missão, pela mesma regra do `tick` e do `docTouch`.
- `BUILD_REVIEW` — `{ complete: bool, cohesive: bool, gaps: [{ task_id, kind: 'spec'|'constituicao'|'concepcao'|'rastreio'|'completude'|'coesao', severity: 'P0'|'P1'|'P2'|'P3', problem }], missingTasks: [id...], lawMark: string|null, anchor: string }`. **`anchor`** = a última linha não vazia do que o juiz julgou, literal — a prova de leitura inteira (ver "o juiz prova que leu"). **É o script que cobra**: veredito sem ela é RECUSADO, o papel roda de novo sabendo por quê, e duas recusas seguidas valem por juiz que não respondeu (não aprova nada). Vale para o revisor #2 e para o confirm-pass. **`lawMark`** = a marca da lei que ESTA rodada leu — a **saída literal** do comando que o motor escreve no prompt (`cat <arquivos da régua> | cksum`, da lista `regua` da casca; ver `leiMarcaInstr` no motor.js). Receita interpretável está proibida aqui: quatro revisores da mesma corrida devolveram quatro marcas do mesmo disco. Projeto sem régua devolve `null` e o pino nunca arma. O motor congela a marca da rodada 1 e a devolve ao revisor nas seguintes; marca diferente da fixada **não** troca a régua — vira aviso no relatório (Bloqueio "precisa de você"). `kind: 'rastreio'` = tarefa decomposta chegou **sem `requisito` ou sem `pronto`** — nasce em severidade **≥ `severityFloor`** e o script o segura no filtro mesmo se vier abaixo (mesmo tratamento do gap de spec), porque tarefa sem os dois campos não é medível por ninguém depois. `kind: 'spec'` = o que a spec pede não saiu (ou saiu diferente), **mesmo com a decomposição cumprida** — nasce em severidade **≥ `severityFloor`** (P1 por default) e o script o mantém no filtro mesmo se vier abaixo, senão o gap sai da conta e passa calado. `kind: 'constituicao'` = o que saiu viola a `.claude/docs/constituicao.md` ou o `.claude/docs/quality-goals.md` do projeto — severidade normal (o filtro de floor vale), e `problem` cita a passagem violada, porque a régua vive no arquivo lido na rodada, não aqui. Sem esse arquivo no projeto, este `kind` simplesmente não aparece. `kind: 'concepcao'` = o que a execução descobriu contradiz um documento de concepção já aprovado — **não segura a obra** (o executor não tem o que consertar no código), sai do filtro e vira aviso no relatório propondo reabrir a etapa, com a linha `correcao-pendente:` sugerida em `problem`. `task_id` de gap de spec ou de constituição pode ser `null`: o buraco que a decomposição não previu não tem tarefa a que pertencer.

O `stopReason`, o `gasto` (quanto a missão queimou — sem ele, "desliguei" não diz se foi caro ou barato), o `progresso` (**quantos passos DISTINTOS fecharam** — nunca linha de resultado somada: retomada regrava veredito do cache e a mesma tarefa volta em mais de uma linha, e a devolução do orquestrador volta sem `task_id`), os `blockers` e a telemetria entram no relatório final (`### Verificação` e `### Bloqueios`); o `esperandoVoce` entra na seção `### Esperando você`, que é dele e de mais ninguém — despejá-lo em `### Bloqueios` é chamar de falha o que só espera a sua vez. Terminado o motor (`built` ou teto), segue direto pro **QA final** abaixo — que é onde defeito é caçado.

## Antipadrões conhecidos — a lista viva do Orquestrador

O Orquestrador recebe esta lista no contrato, e ela **cresce a cada autópsia aprovada**
(`/improve-workflow`): o padrão novo entra aqui, com a data e a corrida que o pagou.
Nenhum item sai — antipadrão não expira, ele espera a próxima chance.

- **Porta fechada do repositório** (wf_5d60f4c1, 2026-08-09) — um gate determinístico
  reprovando barra TODO salvamento, e cada tarefa paga a própria investigação da mesma
  raiz. Quem pega: a guarda de saúde (`SAUDE`) na largada de toda rodada.
- **Trabalho condenado despachado após causa global** (mesma corrida) — o motor sabia a
  causa e seguiu soltando agente para morrer nela. Quem pega: escopo `'repositorio'`
  referendado para o motor no mesmo turno.
- **Repetição como conserto** (mesma corrida) — a mesma etapa re-tentada com o mesmo
  estado, esperando resultado diferente. Quem pega: a impressão de estado por tarefa
  (PULA declarado) e o detector de corrida em círculo (parada da missão).
- **Julgamento cego do já julgado** (mesma corrida) — revisor e auditor sem o histórico
  re-julgam e re-consertam. Quem pega: o ledger da corrida, entregue a todo julgador.
- **Isolamento sem fusão declarada** (2026-08-06) — worktree que ninguém traz de volta;
  72 agentes para 25 tarefas. Quem pega: a proibição de `isolation: 'worktree'`.
- **Id forjado pelo planejador** (2026-08-08) — sufixo `-R` inventado, 6 tarefas órfãs.
  Quem pega: a trava de `planIds`.

## QA final (antes do relatório)

Terminada a execução e **ANTES** de montar o relatório, rode a skill `/qa-loop` em **modo headless** sobre o que você implementou, passando o plano como âncora:

```
/qa-loop <mudanças desta sessão> --plan=<plano> --headless
```

Como o usuário está indisponível, o headless nunca pergunta nada. Trate os 3 buckets assim:
- **Implementação** (bug / divergência do plano) → conserta no loop. Você já tem mandato de executar o plano; o regression gate por conserto é a rede que evita as regressões auto-infligidas.
- **Plan-drift** (um "fix" afastaria do plano em UX/backend/proposta) → **reverte pro plano**. Não "melhore" pra longe do combinado.
- **Plano/arquitetura falho** → **NÃO implemente**. Vira item de "Bloqueios (precisam de você)" no relatório. Headless **não** é licença pra re-planejar.

**Por onde a pergunta chega quem escolhe é o usuário** — a régua dos dois canais (página de
decisão em múltipla escolha, ou a ferramenta nativa uma por vez) está em
**`regua-de-pergunta.md`**, ao lado deste arquivo (fonte: `_shared/regua-de-pergunta.md`, cópia
derivada; não editar à mão).

O relatório do `/qa-loop` (loops rodados, correções, regressões pegas, alertas de plano) vira a seção `### QA` do relatório final.

**Se a skill `qa-loop` não estiver disponível** (foi o que você passou como `hasQaLoop=false` ao motor): o confirm-pass do motor já cobriu "está construído", mas **ninguém checou "está correto"**. Rode você mesmo o gate objetivo do projeto (lint · type · unit · integração, 100% verde no repo) e registre o resultado na `### Verificação`; o que não deu pra checar vai pra `### Bloqueios` dizendo **o que ficou sem cobertura** — nunca "QA ok".

## Persistência — doc + commit/push (antes do relatório)

Passada a QA e **ANTES** de montar o relatório, persista o trabalho. Esta é a última etapa de execução; o relatório só descreve o que já está salvo.

1. **Atualiza a doc.** Descubra o nome de invocação e use o que sair — **nunca escreva o prefixo à mão**:

   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-skill.sh" doc-touch    # → <plugin>:doc-touch
   ```

   Invoque com a Skill tool usando exatamente esse nome — **não** a skill de documentação completa. Uma execução autônoma costuma mexer em arquivos, e a doc tem que refletir a realidade antes de você fechar; mas o caso comum é diff que cabe no `scope:` de 2-4 docs, e reminerar o repo inteiro pra isso é gasto puro. (Não "digite /doc-touch" — invoque a skill.)

   **Quem decide touch-vs-FULL é o próprio touch, não você.** O passo 1 dele calcula `last_full_age_days` (a data de `ledger.last_commit`, que só o FULL avança) e **escala pro FULL sozinho** se passou de 30 dias ou se o número não resolve. Aqui você está em modo autônomo: o touch escala **e segue**, sem perguntar. Não tente antecipar a decisão — a informação nasce lá, e mecanizar "isso é estrutural?" daqui é chutar.
2. **Commit + push.** Stage do que esta sessão mudou, commit com mensagem no padrão do repo (`feat(...)`/`fix(...)`/`docs(...)`, 1 linha) e push pra **branch atual**.
   - **Nunca** `--force`; **nunca** push direto numa branch protegida (`main`/`master`) — se a sessão estiver nela, crie uma branch de feature antes (mesma regra do "force push em main" do Contrato) e registre como decisão.
   - Árvore limpa (nada pra commitar) → pula e anota "nada a persistir".
   - Falha de push (sem remote, sem auth, rejeição) → **não force**; registra como `Bloqueio (precisa de você)` com o erro real e segue pro relatório (o commit local fica feito).

3. **Apaga o sinal do sprint e LIBERA os arquivos reservados.** É o par do `mkdir` da seção _Execução_ e da reserva que o motor fez antes de executar, e é obrigatório:

   ```bash
   python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/andamento.py)" encerra "$CLAUDE_CODE_SESSION_ID" sprint
   # O id do motor nasceu em OUTRO bloco e não chega aqui — cada ```bash é uma chamada
   # à parte. Ele está gravado no NOME de cada reserva desta sessão, e é de lá que sai.
   for RESERVA in "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/andamento/reservas/$CLAUDE_CODE_SESSION_ID"__*.files; do
     [ -f "$RESERVA" ] || continue   # glob sem casar vem literal
     MOTOR="${RESERVA##*__}"
     bash "$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills hooks/reserva-de-arquivos.sh)" liberar "$CLAUDE_CODE_SESSION_ID" "${MOTOR%.files}"
   done
   ```

   Reserva não liberada recusaria o próximo motor da sessão nos mesmos arquivos — é o mesmo esquecimento do sinal, com outro nome. (Há rede embaixo: a reserva expira por idade, mesma janela de 12h do sinal.)

   Deixar aceso faz a sessão inteira continuar sem poder despachar sub-agente **depois** de a missão acabar — o gate não sabe que você terminou, só sabe do arquivo.

   ⚠️ **`encerra` no lugar do `rm` de antes, porque o estado da missão é mais que o sinal.** Onda, placar, doc e trabalho em curso morriam com a sessão e reapareciam na barra de quem reusasse o id. O comando apaga o conjunto, numa receita só — e é a mesma que o motor chama.

   **São TRÊS camadas, e as três existem porque cada uma falha sozinha:**

   | quem apaga | quando | o que ele não alcança |
   |---|---|---|
   | o **motor** (`encerra:barra`, último papel antes do `return`) | todo caminho de saída: obra pronta, teto, vigia, disjuntor, onda estéril, causa global | o motor que morreu de vez (erro terminal, sessão derrubada) |
   | a **casca** (este passo) | o caminho feliz, junto do resto da persistência | o turno interrompido antes de chegar aqui |
   | a **barra** (`andamento.py:expira_sinais`, no desenho) | qualquer sinal que passe de 12h, inclusive de sessão MORTA | nada — é a última rede |

   A terceira nasceu porque as duas primeiras não alcançam a sessão que morreu: o gate do motor já expirava sinal velho, mas **só quando alguém consultava**, e quem consulta é a sessão que acendeu. Medido em 2026-08-09: **cinco sinais órfãos vivos ao mesmo tempo, o mais velho de 75 horas**, todos anunciando "missão de pé" na barra. Quem varre agora é quem desenha a barra — o único processo que roda com frequência garantida em toda sessão viva.

4. **Passa o caminhão do lixo (F9.38).** A missão abriu suíte, build e servidor a cada onda, e nada disso morre sozinho: fica de pé até alguém reclamar da máquina. Última passada, e é obrigatória:

   ```bash
   LIXEIRO="$(bash "${CLAUDE_PLUGIN_ROOT}/skills/sprint/resolve-plugin.sh" lixeiro lib/lixeiro.py)"
   if [ -n "$LIXEIRO" ]; then
     python3 "$LIXEIRO" colhe-turno --sessao "$CLAUDE_CODE_SESSION_ID" \
       || echo "sprint: a colheita falhou em $LIXEIRO — segue sem colher"
   fi
   ```

   É o **mesmo** `colheitaPrompt` que roda junto do checkpoint de cada onda verde — aqui em bash, e por isso mesmo: esta passada tem que acontecer **aconteça o que acontecer com o motor**. A colheita por onda só alcança onda verde; motor que fechou vermelho, que o vigia derrubou ou que o disjuntor desligou não colheria nada — e pôr mais um agente no fim do script depois do disjuntor faria o desligamento por teto deixar de ser desligamento. O lixeiro é achado pelo **nome**, pelo `resolve-plugin.sh` da própria pasta — direto no repositório, e atrás de um segmento de versão no cache do marketplace (`<marketplace>/<plugin>/<versão>/`), que é o layout que o apontamento por posição não alcançava. Lixeiro não instalado (o resolvedor devolve vazio) → **pula e segue calado**, e é o `if` que garante isso: limpeza é camada a mais, nunca pré-requisito. Caminho resolvido e comando quebrado → também segue, mas **avisa** na saída do passo, e a linha do aviso vira item de `### Feito` dizendo que a colheita não passou; sem essa separação, defeito da colheita e ausência do lixeiro ficam com a mesma cara. O que foi encerrado vira item de `### Feito`; falha da colheita **não** vira Bloqueio.

5. **Mede a missão (F20.15).** O medidor da autópsia roda ao fim de **toda** missão, em bash, sem agente nenhum:

   ```bash
   MEDIDOR="$(bash "${CLAUDE_PLUGIN_ROOT}/skills/sprint/resolve-plugin.sh" improve-workflow lib/medidor.py)"
   if [ -n "$MEDIDOR" ]; then
     python3 "$MEDIDOR" || echo "sprint: a medição falhou em $MEDIDOR — segue sem medir"
   fi
   ```

   A tabela por papel e a linha `sinais — N dos 6 acesos` vão inteiras para a seção `### Custo` do relatório final — medir é barato e o número só existe se for guardado na hora.

   **`N` igual a zero ⇒ ACABOU AQUI.** Não invoque `improve-workflow`, não abra transcript, **não dispare agente nenhum**: os passos 2–6 da autópsia (ler o trecho, varrer sobra, refutar, propor) são leitura cara, e sem sinal aceso não há defeito endereçado a investigar. Com pelo menos um sinal aceso — ou se o usuário pediu a autópsia — aí sim invoque a skill `improve-workflow` a partir do passo 2, entregando a saída crua acima. Medidor ausente na máquina (resolvedor vazio) → pula calado, igual ao lixeiro.

O hash do commit + resultado do push entram na `### Verificação`; a doc regenerada é um item de `### Feito`.

## Relatório Final

O relatório é a única coisa que o usuário lê desta sessão — e ele lê **depois**, pra revisar tudo e refatorar. Por isso ele sai como uma **superfície de revisão em HTML**, não como textão no CLI.

### Conteúdo (backbone — sempre o mesmo)

Cinco seções fixas, mais a do custo quando houve medição. Monte este conteúdo PRIMEIRO; a forma de entrega (HTML ou markdown) vem depois.

```
## Sprint — terminei

### Feito
- [só o que foi verificado]

### Decisões tomadas
- [decisão]: [razão em 1 linha]

### Bloqueios (precisam de você)
- [item pulado]: [o que faltou]

### Esperando você (não é falha)
- [taskId]: [motivo — direto do `esperandoVoce` do motor]

### Verificação
- [passos fechados: `progresso.feitos` do motor — o número de tarefas DISTINTAS, nunca a soma das linhas de resultado]
- [o que rodou, e o resultado — incluindo doc atualizada (doc-touch ou FULL, e qual dos dois), commit e push]

### QA (qa-loop)
- [loops rodados + critério de parada · correções aplicadas · regressões pegas na hora]
- [uma linha por problema: o defeito, e quantas VOLTAS ele levou até a rodada limpa — do `voltasPorProblema` do motor e do mesmo campo do /qa-loop, os dois juntos]
- [⚠️ alertas de plano/arquitetura que NÃO implementei — pra você julgar]

### Custo (medidor da autópsia)
- [uma linha: quanto a missão custou por papel no que pesou, mais `sinais — N dos 6 acesos`]
- [drilldown fechado: a tabela crua do medidor inteira, e — só se N > 0 — o parecer da autópsia]
```

São **seis** seções quando houve medição. `### Custo` sai sempre que o medidor rodou (passo 5
acima), inclusive com zero sinal aceso: a visão geral é UMA linha, e a tabela crua mora num
drilldown fechado — mesma revelação progressiva das páginas do `/visual`. Medidor pulado
(ausente na máquina) ⇒ a seção não sai.

### Entrega via /visual (titular)

Se a Skill **`visual`** estiver entre as suas skills disponíveis, **invoque-a** (Skill tool, `skill: "visual"`) e renderize o relatório como HTML. (Não "digite /visual" — invoque a skill.) `visual` é **dependência recomendada** do sprint; instale os dois juntos. <!-- acopla-ok: invocação por NOME de skill, que é o caminho portátil; o passo é condicional e degrada sem ela -->

Por que HTML: o relatório é longo e completo, e o usuário vai **revisar item a item e refatorar**. O `/visual` tem o componente exato pra isso — veredito inline (`.feedback-item`: ✓ Manter / ✏️ Mudar / ✗ Remover) que ele marca enquanto lê.

**Mapeamento seção → componente** (instrua o /visual a montar a superfície de revisão):

No spec, **`item_labels: ["✓ Manter", "✏️ Mudar", "✗ Remover"]`** — NUNCA "✓ Vira ação" (esse é do relatório do /qa-loop: lá cada achado vira ação no próximo plano).

- **Bloqueios (precisam de você)** → **topo**, prioridade máxima. Default: `.callout` severidade alta (um bloqueio é "não consegui X porque faltou Y" — sem ramificação). **Só** vire `.decision-card` se houver escolha A/B **genuína** já clara — nunca fabrique duas opções pra preencher o card (regra anti-"chutar"). Os ⚠️ alertas de plano/arquitetura do qa-loop entram aqui (normalmente `.callout`; só decision-card se for binário de verdade).
- **Esperando você (não é falha)** → logo abaixo dos Bloqueios, `.callout` de severidade média — um por linha do `esperandoVoce`, com o `motivo` inteiro. Nunca misture com Bloqueios (lá é "não consegui"; aqui é "não tentei, porque é sua vez") nem com o que não deu tempo. Lista vazia: a seção não sai.
- **Feito** → cada item = `.feedback-item` com veredito inline + profundidade em `<details>`. O usuário revisa enquanto lê.
- **Decisões tomadas** → cada decisão = `.feedback-item` (o usuário aprova ou marca pra rever) + razão em 1 linha.
- **Verificação** → `.callout` (ok/danger): o que rodou + resultado. Read-only.
- **QA (qa-loop)** → `.callout`/seção: loops, correções, regressões, alertas. Read-only.
- **Custo (medidor da autópsia)** → `.callout` com a linha de visão geral + `<details>` fechado com a tabela crua (e o parecer, se houve). Read-only. Nunca a tabela aberta no corpo: custo é contexto, não decisão a tomar.
- `.exec` no fim + **caixa de fechamento**: no caso comum (feedback-items + callouts) só `feedback-box`; `decisions-box` só se houver decision-card de verdade. As caixas são **só fechamento** (progresso + observação + botões) — **nunca re-listam os itens** (anti-pattern "duas tabelas").

**Retorno do feedback é assíncrono.** O usuário está fora e esta sessão termina quando o relatório sai — então **não** conte com live-sync ("ele diz ok e o Claude lê"). O HTML guarda os vereditos em `localStorage`; quando ele voltar (provável sessão nova), clica "Copiar feedback"/"Copiar escolhas" e cola pra dirigir o refactor. O daemon do /visual pode subir (é inócuo), mas o caminho confiável é copy/paste.

**CLI mínimo** (o /visual proíbe duplicar o conteúdo no CLI): emita só

```
Sprint terminou. Relatório completo no browser: <path>
⚠️ Bloqueios (precisam de você): <título 1> · <título 2>   ← só os títulos, se houver
```

Os títulos dos bloqueios são um **índice** (não o conteúdo) — segurança, porque bloqueio é crítico e o usuário precisa vê-los mesmo sem abrir o browser. Nada além disso no CLI.

### Fallback (markdown)

Se a Skill `visual` **não** estiver disponível, emita o **relatório markdown completo** (o bloco de conteúdo acima, com as 6 seções preenchidas) direto no CLI. É um fallback à altura: entrega 100% da mesma informação — só a apresentação degrada, não o conteúdo.

Detalhe técnico só se o usuário pedir depois.
