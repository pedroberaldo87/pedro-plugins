---
name: sovai
description: Modo de execução contínua — Claude executa um plano ou tarefa multi-etapa do começo ao fim sem pausas, sem checkpoints, sem perguntas de confirmação. Toma as decisões necessárias para seguir e anota cada uma. O usuário estará indisponível durante a execução; ele revisa tudo no relatório final e refatora se necessário. Use quando o usuário disser "sovai", "sova", "executa até o fim", "vai sem parar", "não me consulte", "eu não estarei disponível", "modo autônomo", ou variação clara de "executa sozinho enquanto eu não tô". Não disparar para tarefas curtas que terminam num turno — a skill existe para missões em que interrupção custa caro porque o usuário não está disponível para responder.
---

# Sovai — Execução Contínua

O usuário vai ficar indisponível. Reconheça com uma linha (`modo sovai ativo, começando`) e comece. Daqui em diante, silêncio até o relatório final.

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

### O sinal que arma o gate (obrigatório, e é a PRIMEIRA coisa)

Antes de disparar o Workflow, acenda o sinal; ao entregar o relatório, apague. É ele que faz o gate existir:

```bash
SOVAI_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sovai"
mkdir -p "$SOVAI_DIR"
: > "$SOVAI_DIR/ativo-$CLAUDE_CODE_SESSION_ID"          # ao armar a missão
SOVAI_MOTOR_ID="motor-$(date -u +%Y%m%dT%H%M%SZ)-$$"    # id DESTE motor na sessão
rm -f "$SOVAI_DIR"/{ativo,bloqueios}-"$CLAUDE_CODE_SESSION_ID"   # ao entregar
```

O `SOVAI_MOTOR_ID` vai no `args` do Workflow como `motorId` (junto com `sessionId` = `$CLAUDE_CODE_SESSION_ID`): é com ele que o motor **reserva os arquivos da onda antes de soltar executor** (`hooks/reserva-de-arquivos.sh reservar`, ver o esqueleto) e os **libera** ao entregar. Dois motores da mesma sessão com o mesmo id se enxergariam como um só, e a reserva nunca recusaria nada.

Enquanto o sinal está aceso, `plugins/sovai/hooks/pretooluse-sovai-motor.sh` **nega** todo disparo de sub-agente e manda rodar o Workflow. Fora do sovai ele é mudo. Desligamento: `SOVAI_GATE=0`.

⚠️ **Esqueceu de apagar o sinal, a sessão inteira fica sem despachar sub-agente.** Apagar é parte da entrega, não faxina opcional.

**A rede embaixo do esquecimento (desde 2026-08-06):** o sinal **expira por idade**. Passado `SOVAI_TTL_MIN` (default 720 min = 12h) sem ser apagado, a primeira consulta do gate o **remove** — junto com o contador de bloqueios dele — e registra a linha em `expirados.log`. Isso não te dispensa do `rm`: a janela é de 12h porque a missão que o gate protege é longa por definição, e encurtá-la mataria sinal de execução legítima em andamento.

### Por que o gate precisou nascer

A frase que ficou aqui de 2026-08-01 até 2026-08-02 dizia que *"o guard `PreToolUse(Agent)` acorda a cada disparo"*. **Não acordava.** O guard que existe é o do `guardrails`, e ele foi escrito para **proteger** Agent Teams — a regra 3 dele libera explicitamente *"tarefa one-off sem team_name"*, que é exatamente a forma pela qual o `/sovai` descambava. A skill se apoiava numa proteção inexistente, e ninguém tinha como saber: prosa descrevendo mecanismo ausente não dá erro.

**O gate degrada, não trava.** Depois de 3 negações na mesma sessão ele desiste, libera e grava a desistência em `desistencias.log`. O motivo é o cenário: missão longa, dono ausente. Se a inferência de que o Workflow não passa por aqui estiver errada, a missão continua manca em vez de morrer parada.

## Modelo & effort por etapa (R8) — contrato em `references/r8-tiers.md`

O tier de cada etapa (modelo · effort · knob) e a semântica dos knobs são o **contrato R8 compartilhado** com o `/qa-loop`, vendorado em **`references/r8-tiers.md`** (fonte: `_shared/r8-tiers.md` — não editar a cópia à mão; `scripts/sync-shared.sh --check` pega drift). A tabela completa (Etapa · Modelo · Effort · Knob + o que cada knob significa + a regra de tier por rodada) está lá.

**É TUDO Opus 5** (contrato R8 desde 2026-07-26, vale pros dois motores): os seis knobs rodam `model: 'opus'` e só o **`effort`** varia por etapa. Aqui isso pesa dobrado — o `/sovai` roda com o usuário indisponível, sem checkpoint humano pra pegar execução rasa.

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

O valor do `effort` **não vive nesta skill**. Rode isto e passe o resultado dentro do
`args` do Workflow, junto com os outros parâmetros:

```bash
python3 "<skill_dir>/references/r8_tiers.py" args
# -> { "model": "opus", "tiers": { "decompose": {"effort": "high"}, ... } }
```

⚠️ **O bloco de esforço vai ESCRITO DENTRO do texto do script, não lido de `args` em tempo de execução.** Gere a saída do comando acima como uma constante literal no topo do script que você passa ao `Workflow`:

```javascript
// gerado por references/r8_tiers.py args — não digite à mão, não leia de args.tiers
const T = { decompose: {effort:'high'}, coordinate: {effort:'medium'}, /* … */ }
```

O motivo é medido: o canal que levava esse valor até o script **falhava**, e `args.tiers` chegava `undefined` — o que matava o motor na primeira volta. A régua continua a mesma (o valor **nasce** em `_shared/r8-tiers.json`, nunca é inventado aqui); o que muda é **quando** ele entra: na composição do script, não na execução dele. Trocar um tier segue sendo editar o JSON compartilhado e rodar `scripts/sync-shared.sh` — nenhum `SKILL.md` muda.

Ler de `args.tiers` em tempo de execução é a versão que este passo **substitui**: um canal a mais entre o valor e quem o usa, e cada canal a mais é um lugar a mais para o valor sumir em silêncio.

### A compilação cara é paga UMA vez, pela casca (obrigatório, antes de disparar o Workflow)

Projeto que compila em minutos cobra esse preço **de cada executor** quando ninguém compila antes: numa execução real, **dez minutos de compilação por tarefa** foi o que empurrou o agente para o segundo plano — e processo em segundo plano que morre não avisa. A compilação é paga **aqui, uma vez**, e o que os executores herdam é o **cache quente** no disco do repositório.

`SOVAI_BUILD_CMD` = o comando de compilação do projeto, **o mesmo que o executor rodaria** (`npm run build`, `cargo build`, `go build ./...`, `make`); projeto que não compila deixa vazio e o passo não faz nada.

```bash
SOVAI_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sovai"
mkdir -p "$SOVAI_DIR"
BUILD_LOG="$SOVAI_DIR/build-$CLAUDE_CODE_SESSION_ID.log"
# NUNCA limpe antes nem depois: `clean`, `rm -rf <dir de build>` e `--no-cache` aqui
# devolvem o cache frio ao executor e a compilação cara volta a ser por tarefa.
if [ -n "$SOVAI_BUILD_CMD" ] && ( cd "$SOVAI_REPO_ROOT" && sh -c "$SOVAI_BUILD_CMD" ) >"$BUILD_LOG" 2>&1
then BUILD_WARM=true
else BUILD_WARM=false
fi
echo "buildWarm=$BUILD_WARM"
```

O resultado vai no `args` do Workflow como **`buildWarm`**, e de lá para **todo** `execPrompt` — cache quente que ninguém avisa ao executor é cache que ele derruba com um `clean` de rotina. **Fail-open:** compilação que falha devolve `buildWarm=false` e a missão segue — o erro real chega ao executor pelo próprio build dele, e travar a missão por causa do aquecimento é pior que aquecimento nenhum. O log fica em `~/.claude/sovai/`, fora do repositório.

### Knobs deste motor (a casca passa em `args`)

| Knob | Default | O que faz |
|---|---|---|
| `maxRounds` | `5` | **Trava de incêndio, não meta.** Teto de voltas do #1↔#2; estourou, o que faltou vira Bloqueio. |
| `severityFloor` | `P1` | Gap abaixo do floor não segura a obra de pé (vira nota no relatório, não nova rodada). |
| `churnThreshold` | `2` | Mesma tarefa reaparecendo N rodadas **seguidas** → escala pro `diagnose_model`. |
| `hasQaLoop` | detectado | `false` liga o **confirm-pass** em `finalize_model` antes de declarar `built` (ver a guarda no #2). A casca detecta se a skill `qa-loop` está disponível e passa o booleano — nunca deixa `undefined`, senão a guarda nunca arma. |
| `tokenBudget` | `null` | **Disjuntor por consumo.** Teto de tokens de saída da missão inteira. Estourou, o motor **se desliga** e relata quanto gastou. `null` = sem teto (o comportamento antigo). |
| `sessionId` | — | `$CLAUDE_CODE_SESSION_ID`. É a chave da **reserva de arquivos**: a disputa que existe é entre motores da MESMA sessão, e reserva global recusaria toda sessão paralela nos arquivos dela. |
| `motorId` | — | Identifica ESTE motor dentro da sessão (carimbo de arranque serve). Dois motores com o mesmo id se enxergariam como um só e a reserva nunca recusaria nada. |
| `silenceLimitMin` | `12` | **Vigia por tempo.** Minutos de registro parado que fazem o vigia acender o sinal. Só derruba se **não houver trabalho vivo** — ver `F9.24` abaixo. As DUAS metades falam na tela: o gancho de andamento (`hooks/posttooluse-andamento.sh` → `lib/andamento.py:linha_silencio`) narra o silêncio longo com trabalho vivo como **`rodando ha N min`** e o silêncio sem sinal de vida como **`travamento`**, no mesmo `systemMessage` do relógio. |
| `buildWarm` | `false` | **Cache de compilação já quente.** `true` = a casca compilou os alvos antes de disparar o motor (passo acima), e o valor chega a todo executor no `execPrompt` — é o que o proíbe de recompilar do zero. Ausente/`false` = ninguém aqueceu, e cada executor compila como antes. |
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
- **Progresso vem do placar que a ferramenta imprime**, não de perguntar ao modelo como vai. `andamento.placar()` lê a saída crua nos três formatos medidos (`139 passou · 0 falhou` · `OK (56 checks)` · `17 ok / 0 falhas`, mais o do pytest), e `andamento.avanco()` compara com o anterior.
- **Dois placares iguais seguidos = `sem avanço`.** Esse é o sinal de "está em círculos", e ele vale porque o outro candidato foi medido e **não pega nada**: 0 de 282 agentes repetiram o mesmo comando 4 vezes ou mais. Detector de repetição de comando seria decoração.

A linha real, gerada pelo módulo:

```
21:40:22 · python3 …/test_plan_state.py · primeira vez aqui, sem estimativa
21:40:22 · python3 …/test_plan_state.py · ~1min35s (das 3 vezes anteriores aqui)
rodando há 70s  · usual ~1min35s           · 62 passou · 12 falhou — sem avanço
rodando há 4min · passou do dobro do usual · 74 passou ·  0 falhou — avançou
```

Registrar a duração ao fim de cada ferramenta longa (`andamento.registrar(repoRoot, cmd, seg)`) é o que alimenta a estimativa da próxima vez. Suíte roda várias vezes na mesma missão — é dessa repetição que a memória vive.

**E o relógio e a estimativa também chegam à BARRA** (`hooks/statusline-motor.sh` → `lib/andamento.py:linha_motor`), que é a única superfície que fica: `systemMessage` rola com a conversa, e quem volta ao terminal uma hora depois não vê nenhuma das linhas acima. A barra é desenhada por outro processo e **não adivinha nada** — ela sai como `ferramenta há 70s · usual ~1min35s` porque **quem executa gravou o disparo**: o gancho de andamento em `marca` (PreToolUse de Bash, o mesmo que roda dentro de cada executor da onda) escreve em `~/.claude/sovai/trabalho-<sid>` o instante, o **comando** e o **projeto**, e apaga o arquivo quando o comando volta. Sem comando e projeto no disco não há como chamar `estimativa()`, e a barra volta a ter só a idade da missão. Comando sem histórico aqui sai **sem número**, pela mesma regra de sempre.

### A janela de tempo da sessão NÃO dá para observar

Duas coisas diferentes foram confundidas, e a confusão fazia o motor planejar contra um número que não existe:

- **O quanto de conversa já foi usado** — isso **dá** para ver, e é o que o `context-guard` mostra na barra de status.
- **Quanto tempo falta na janela da sessão** — isso **não** dá para ver de dentro. Não há chamada que responda, e estimar pela hora do relógio é chute.

**A estratégia de parada, então, não é temporal.** O motor para pelo que ele consegue medir: `maxRounds`, `tokenBudget`, o freio de severidade, e o vigia. Quem escrever passo que dependa de "quanto falta de sessão" está escrevendo contra um dado inexistente — e o sintoma é a missão morrer no meio sem checkpoint, que é exatamente o que `F9.14` cobre.

- **OPUS #1 — Decompositor.** NÃO planeja do zero. Pega o **plano que você deixou** e o quebra em tarefas de implementação, marcando para cada uma os **arquivos que toca**, se é **paralelizável**, de quais tarefas **depende**, e se é `complexity: 'mechanical'` (operação bem delimitada) ou `'standard'`. Cada tarefa carrega também o **`requisito`** que ela atende e o **`pronto`** que a declara feita — **os dois saem da spec, copiados; nunca redigidos aqui**. Executor não cumpre critério que não recebeu, e critério inventado pelo decompositor faz o revisor medir contra a régua errada. Item da spec que não traz os dois **não vira tarefa: vira Bloqueio** (`whyNeedsYou` = qual dos dois falta). **Passo que espera um ato do dono chega declarado, e você só transporta:** o `espera_dono` do passo no `.plan.json` vira `esperaDono` na tarefa, **copiado literal**. Não é seu julgamento — não marque tarefa por achar que ela "depende do usuário", e não desmarque a que o plano marcou. É esse campo que tira a tarefa da fila (e, por dependência, quem depende dela): sem ele o motor solta executor num passo que não tem como funcionar, ele volta falhando, e a falha vira churn como se fosse executor incompetente.

  **E o `pronto` é JULGADO antes de virar tarefa, não só copiado — e quem julga é o script, não você.** Critério que só se cumpre **fabricando valor dentro de um entregável** vira `blocker` de `kind: 'criterio'` — nunca tarefa. O motor roda `lib/regua_pronto.py` (do plugin visual, a mesma régua que o `plan_state.py` cobra ao gravar o plano) sobre o `pronto` de **cada** tarefa decomposta, logo depois desta etapa e **antes de soltar qualquer executor**: reprovado sai da lista e vira Bloqueio. Enquanto isto era só instrução em prosa, bastou o julgamento não acontecer para o critério-armadilha chegar inteiro a quem executa. A régua, e ela é sobre a **origem do valor**, não sobre o caminho do arquivo:

  - **Pode:** regerar o entregável a partir do dado real. É operação do produto.
  - **Não pode:** injetar valor inventado dentro do entregável para o critério fechar. Isso é bancada, e bancada não entra em coisa que vale.

  **E o `pronto` que só fecha editando arquivo SOB TRANCA vira tarefa `protegido`.** Esta mesma skill proíbe o motor de reescrever documento de concepção aprovado (`status: approved` no frontmatter) — nem o corpo, nem o frontmatter. O decompositor lia o plano sem olhar isso e fabricava tarefa cujo `pronto` só se cumpre justamente ali: **a tranca mandava o executor a uma porta que ela mesma trancou**, e sobravam dois caminhos, os dois ruins — desobedecer (derrubando a marca do de acordo) ou voltar falhando rodada após rodada até virar churn e queimar o diagnóstico caro. A régua é de **disco, não de julgamento**: arquivo que a tarefa toca e que traz `status: approved` no frontmatter é arquivo sob tranca → a tarefa nasce com **`protegido`** = o caminho do arquivo + por que ele está trancado. Ela **continua entrando na fila** (diferente do `esperaDono`, que tira da fila), mas o entregável dela é uma **proposta**, e o critério do revisor **inverte**: `git diff` vazio naquele arquivo é o resultado **certo**.

  O caso que originou: um critério mandava o número aparecer no documento, o executor **obedeceu** e escreveu o número na mão. Quem errou não foi quem executou — foi o critério, e ninguém o julgou antes de soltar o executor. Critério ruim solto vira trabalho errado com todo mundo cumprindo o combinado. Rodada 1 = `decompose_model` (plano inteiro); rodadas 2+ (re-decompõe só o delta do feedback do #2) = `coordinate_model`. Re-arquitetar é proibido (mesma regra do "não replanejar no headless"); buraco no plano que exija decisão de arquitetura vira **Bloqueio**, nunca invenção silenciosa.
- **EXECUTORES (Opus 5) — Implementam as tarefas.** Tarefa padrão = `executor_model`; `complexity: 'mechanical'` = `mechanical_model`. Independentes rodam **em paralelo**; dependentes, **em série** na ordem do #1. Tarefa única ou missão sequencial pura → o Workflow degenera pra um executor por vez, sem cerimônia (o fan-out é ganho só quando há independência real).

**O texto que o executor recebe abre com três regras, e elas não são conselho — cada uma nasceu de trabalho perdido:**

1. **CONFIRA NO DISCO ANTES DE IMPLEMENTAR.** O primeiro passo é abrir o arquivo do `pronto` e ver se ele já está cumprido. Agente que morre **depois** de escrever some do registro, e a tarefa dele volta como faltante — sem esta checagem, o trabalho é refeito por cima do que já estava lá. Já cumprido: devolve `done: true` com o `arquivo:linha` que prova, e não reescreve nada.
2. **FORMATAR O PROJETO INTEIRO É PROIBIDO.** Nada de `prettier --write .`, `ruff format .`, `black .`, `eslint --fix .` sem caminho, nem equivalente que varra a árvore. Formatador sem escopo **reformatou 18 arquivos de outros agentes** numa execução real e quase apagou trabalho paralelo. Formate **só os arquivos que esta tarefa tocou**, nomeados um a um.
3. **SONDA DE DEPURAÇÃO NASCE FORA DO ALCANCE DA SUÍTE.** Precisou de script temporário para investigar? Ele vai para o diretório de rascunho da sessão, **nunca** com nome que a suíte colete (`test_*.py`, `*.spec.ts`, `*_test.go`). Sonda esquecida dentro do alvo da suíte derruba a suíte de todo mundo e some do radar — quem varre depois é o fiscal de bancada (`F8.3`).
4. **PASSOU DO TETO, PARE E DEVOLVA `espera: true`.** O texto da tarefa traz `tetoMin` — os minutos que você tem. Marque a hora ao começar; chegou no teto sem ter fechado o `pronto`, **pare onde está**, deixe no disco o que já funciona e devolva `{ done: false, espera: true, note: <em que ponto parou e o que falta> }`. Isso **não** é falha: a tarefa volta pro decompositor na rodada seguinte com a sua nota. Ficar mais que o teto tentando terminar é o que segurou **21 agentes já entregues por 2 horas** numa execução real — a onda só fecha quando o último volta, e quem cicla nunca volta.
5. **ARQUIVO SOB TRANCA: O ENTREGÁVEL É A PROPOSTA, NÃO A EDIÇÃO.** Tarefa que chega com `protegido` toca arquivo que este motor **não pode reescrever** (documento de concepção aprovado). **Não edite o arquivo** — nem o corpo, nem o frontmatter. Devolva `proposta: { arquivo, antes, depois }` com os **dois lados literais**: `antes` = o trecho que está no disco hoje, copiado caractere por caractere; `depois` = o texto que deve entrar no lugar, pronto pro dono colar. Descrição do que mudar **não serve** — quem aplica é o dono, e resumo obriga ele a reescrever do zero. Aqui `done: true` significa **proposta entregue**, e **`git diff` vazio naquele arquivo é o resultado CERTO**, não a falha.

6. **CACHE QUENTE: NÃO RECOMPILE DO ZERO.** A tarefa chega com `buildWarm` — `true` significa que os alvos **já foram compilados** pela casca antes de o motor começar, e o cache está no disco do repositório. Compile **incremental**, e só o que a sua mudança exige: `clean`, `rm -rf` de diretório de build, `--no-cache` e recompilação do zero estão **proibidos** com `buildWarm: true`. Foram **dez minutos de compilação por tarefa** que empurraram o agente para o segundo plano numa execução real — e agente em segundo plano que morre não avisa ninguém.

⚠️ **`isolation: 'worktree'` é PROIBIDO neste motor.** A regra anterior mandava isolar em worktree duas tarefas paralelas que tocassem o mesmo arquivo, e ela **queimou uma execução inteira em 2026-08-06**: 72 agentes para 25 tarefas, 15 delas executadas **3 vezes cada**, 8 diagnósticos de tarefa-presa, e 49 worktrees com trabalho dentro que ninguém leu.

O mecanismo da falha, e ele é estrutural, não um deslize: o executor termina dentro da cópia isolada, **e nada traz a cópia de volta**. O revisor (#2) confere no repositório de verdade, não encontra o trabalho, marca a tarefa como não-feita, e o decompositor (#1) manda refazer — para sempre, porque refazer também vai para uma cópia nova. O motor não tem como perceber: o sintoma que ele vê ("essa tarefa não sai do lugar") é indistinguível de executor incompetente, e por isso ele escala para o `diagnose_model` — gastando ainda mais.

**Colisão de arquivo se resolve dividindo o LOTE, nunca dividindo o repositório.** Dentro de uma onda, quem colide vai em sub-lotes seriais; todo mundo escreve no mesmo repo, e o revisor enxerga tudo. É mais lento só no caso raro de colisão real, e é sempre correto.

A regra geral que sobrou disto: **isolamento sem fusão declarada é dívida com cara de cuidado.** Se um dia este motor voltar a isolar, o passo que traz de volta nasce no mesmo commit — e o revisor precisa saber onde olhar.
- **OPUS #2 — Revisor de construção.** Julga a obra **contra a spec** — o plano que a casca passou em `planPath`/`planText`, e que o motor entrega ao #2 igual como entrega ao #1. A decomposição do #1 é **meio**, não fonte da verdade: revisar contra ela é circuito fechado, onde quem decompõe errado é aprovado errado. Cinco eixos: **spec** (a spec saiu, mesmo no que a decomposição não previu?) · **constituição** (o que saiu respeita as metas de qualidade autorais do projeto?) · **rastreio** (toda tarefa decomposta trouxe `requisito` e `pronto`?) · **completude** (toda tarefa decomposta saiu?) · **coesão** (as peças paralelas integram, sem se contradizer?). Desvio de spec vira gap de `kind: 'spec'` e **nasce em severidade ≥ floor**; se vier abaixo, o script o segura assim mesmo — senão sairia do filtro de severidade e passaria calado. **Eixo de rastreio:** tarefa decomposta sem `requisito` ou sem `pronto` **reprova** — vira gap de `kind: 'rastreio'`, que nasce em severidade ≥ floor e é segurado pelo script igual ao de spec. Tarefa sem requisito não tem contra o que ser medida, e sem `pronto` quem executa decide sozinho o que é "feito": nenhuma das duas passa calada. **Eixo de constituição:** o revisor **lê `.claude/docs/constituicao.md` e `.claude/docs/quality-goals.md` do projeto onde a missão está rodando** e sinaliza onde a implementação VIOLA o que está escrito lá. O arquivo é aberto na rodada, **nunca copiado para dentro desta skill** — a régua é a do projeto que instalou, e cópia em prosa defasa. Violação vira gap de `kind: 'constituicao'` pela rubrica de severidade normal, sem faixa própria. **A marca da lei é congelada na primeira volta:** o revisor devolve em `lawMark` a marca do texto que leu (o `cksum` do corpo dos dois arquivos, mesma receita da aprovação), o motor fixa a da rodada 1 e passa ela de volta nas seguintes — o #2 mede contra a lei fixada, nunca contra o texto novo. Lei editada no meio da missão vira **aviso no relatório** (Bloqueio "precisa de você"), porque as rodadas anteriores foram medidas contra o texto antigo; o que não pode acontecer é a régua trocar calada e duas rodadas da mesma missão medirem contra textos diferentes. **Projeto sem esse arquivo: o eixo simplesmente não roda** e a revisão segue com os outros quatro — ausência de constituição não é gap. **Quando a concepção está errada, e não o código:** o mesmo eixo cobre o caso em que o que a execução descobriu contradiz um documento de concepção já aprovado (`status: approved`) — a entrevista errou, o código está certo. Vira gap de `kind: 'concepcao'`, e o revisor **nunca reescreve documento aprovado** — nem o corpo (mexer nele reabre a etapa pela marca do de acordo) nem o frontmatter. O gap sobe como **aviso no relatório** (Bloqueio "precisa de você") propondo **reabrir a etapa**: nomeia o documento, a passagem contradita e a linha `correcao-pendente: {o que precisa mudar}` que o dono grava no frontmatter e cobra até reapresentar e reaprovar. Propor é do motor, escrever é do dono. Continua **não** caçando bug sutil nem rodando a suíte — profundidade de correção é do `/qa-loop` (etapa seguinte). Roda em `coordinate_model`; quando os cinco eixos batem, declara `built=true` **direto** — quem re-checa do zero é o `/qa-loop --headless` que roda logo em seguida (Fase Gate + confirm-pass dele). **Guarda (armada no script, não só na prosa):** com `hasQaLoop=false` o motor roda um **confirm-pass dedicado** em `finalize_model` antes de declarar `built` — sem `/qa-loop` adiante, fechar no veredito de `coordinate_model` seria declarar pronto sem nenhuma segunda checagem. Devolve **feedback estruturado pro #1**, que re-decompõe **só o delta** (o que faltou / precisa refazer) na volta seguinte. A seta de volta #2→#1 é o coração do motor.
**O revisor manda a sonda dele para fora do alvo da suíte, pela mesma regra do executor.** É a metade de instrução do problema que o fiscal varre depois — quem planta a sonda tem que saber onde ela pode nascer, senão o fiscal vira faxina permanente em vez de rede.

**O juiz prova que leu a coisa inteira.** Todo veredito — do #2, do confirm-pass, do auditor — devolve a **âncora do fim**: a última linha não vazia do que ele julgou, literal. Sem ela o veredito é **recusado** e o papel roda de novo. Nasceu de um caso medido: um juiz aprovou uma página em 36 segundos tendo lido só por busca, e só admitiu quando confrontado. Leitura por amostragem é indistinguível de leitura inteira no texto do parecer — a âncora é a única diferença observável.

**Tarefa sob tranca INVERTE o critério do revisor.** O motor entrega ao #2 a lista `protegidas` — os `task_id` das tarefas que tocam arquivo trancado. Nelas o que se julga é a **proposta**, não a obra: **`git diff` vazio no arquivo protegido é o resultado CERTO**, e o revisor só reprova quando falta `antes` ou `depois` literal. O contrário também vale — arquivo protegido que **aparece** no `git diff` é gap de `kind: 'spec'`: o executor furou a tranca e derrubou a marca do de acordo do dono. Sem esta inversão o #2 media a tarefa pela régua normal, via arquivo intocado, reprovava por não-feita e devolvia ao #1 exatamente a tarefa que ninguém tem permissão de fazer.

- **AUDITOR — a segunda opinião antes de derrubar qualquer coisa.** Executor que declara impossível **não encerra nada sozinho**: bloqueio repetido na mesma tarefa convoca um auditor, e é ele que decide. Aconteceu de verdade — um executor declarou impossível o que ele conseguia fazer com a ferramenta que já tinha na mão.

  O auditor recebe a **lente invertida**: o ônus é dele provar que **não dá**, não do executor provar que dá. E recebe, junto, a **lista do que havia à mão** — as ferramentas disponíveis naquele contexto —, tendo que dizer **quais o executor nem tentou**. Foi essa pergunta que faltou no caso real: o diagnóstico dizia "exige navegador contra produção", o agente **tinha** navegador, e a causa verdadeira era outra (uma dependência não declarada: publicar exigia o aval do dono, e as jornadas de tela dependiam de estar publicado).

  Dois desfechos, e os dois são do script: auditor que **derruba** a alegação devolve a tarefa ao loop com o que ele apontou; auditor que **confirma** encerra a tarefa como impedimento real, com o motivo escrito. Encerrar direto no "impossível" do executor é o que esta peça existe para impedir.

- **DIAGNÓSTICO — escalada de tarefa-presa.** Se a MESMA tarefa reaparece em `missingTasks`/`gaps` por ≥ `churn_threshold` rodadas seguidas (default 2, mesmo limiar do `/qa-loop`), o motor escala ANTES de mandar o executor tentar de novo: um diagnóstico dedicado em `diagnose_model` (R8, "diagnóstico após falhas repetidas") investiga a causa raiz (dependência não mapeada, arquivo errado, premissa furada) em vez de repetir o mesmo pedido esperando resultado diferente. O diagnóstico entra no `feedback` da próxima rodada do #1.

### Fronteira com o `/qa-loop` (a spec é comum; o ângulo, não)

Os dois loops leem a **mesma spec** e perguntam coisas **diferentes** — e isso vai **escrito no prompt de cada papel** pra não duplicarem trabalho:

- **Este loop (#1↔#2) garante que está CONSTRUÍDO** — spec + constituição + rastreio + completude + coesão de montagem, medidas **contra a spec** e contra a `constituicao.md` e o `quality-goals.md` do projeto; a decomposição do #1 entra como meio (previu tudo? saiu tudo?), nunca como contrato final. Pergunta: _"a spec virou código inteiro e coerente?"_. **NÃO** caça bug sutil, **NÃO** roda a suíte, **NÃO** mexe em lint/type.
- **O `/qa-loop` (etapa seguinte) garante que está CORRETO** — bug, regressão, lint/type/test, segurança, e fidelidade ao plano com **profundidade de correção** (os 3 buckets dele). Pergunta: _"o código construído tem defeito?"_.

Resumo: **#2 = "está de pé, e é o que a spec pediu?" · qa-loop = "está certo?"**. O motor de implementação fecha quando a obra está de pé; o qa-loop entra **depois** pra procurar defeito. A spec é o eixo dos dois — o que muda é montagem aqui, defeito lá.

### Freio do loop (não é "até o #2 ficar feliz")

Revisão é poço sem fundo (mesma disciplina do review-loop: parada por retorno decrescente, não "até zero"). O loop #1↔#2 para no **primeiro** que ocorrer:
- **[primário]** #2 reporta `complete && cohesive` e **zero gap** acima do floor de severidade — gap de spec e de rastreio contam sempre, estejam onde estiverem na escala → obra de pé, segue pro QA.
- **[trava]** atingiu `maxRounds` (safety-cap, **não** meta) → o que faltou vira **Bloqueio (precisa de você)** no relatório.

### Esqueleto do motor (referência — o princípio, não código imutável)

A casca dispara a tool `Workflow` com o script abaixo. Os três schemas (`DECOMP`, `TASK_RESULT`, `BUILD_REVIEW`) são o que torna os gates determinísticos: o script lê campos estruturados, não texto solto.

```javascript
export const meta = {
  name: 'sovai-build-engine',
  description: 'Motor de implementação: tier por etapa (R8) — decompose/coordinate/executor/mechanical/diagnose/finalize',
  phases: [{ title: 'Decompor' }, { title: 'Diagnose' }, { title: 'Executar' },
           { title: 'Revisar' }, { title: 'Confirmar' }],
}

// args (da casca): { planPath, planText, maxRounds, severityFloor, repoRoot,
//                    churnThreshold, hasQaLoop, sessionId, motorId }
// O parâmetro pode chegar TEXTO (JSON serializado) em vez de objeto — quando isso
// aconteceu, todo campo lido dele virou undefined e o motor morreu na 1ª volta sem
// dizer por quê. Converte ANTES de usar, e o resto do script só fala com ARGS.
const ARGS = typeof args === 'string' ? JSON.parse(args) : args
const sevRank = s => ({ P0:3, P1:2, P2:1, P3:0 }[s] ?? 0)
const floor = sevRank(ARGS.severityFloor || 'P1')
// default DENTRO do motor: sem isso, ARGS.maxRounds undefined faz `r < undefined` ser
// false na 1ª volta — o motor devolveria "nada construído" em silêncio.
const maxRounds = ARGS.maxRounds || 5
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
let desligadoPor = null               // 'orcamento' | 'vigia' — vira stopReason
const gastoAgora = () => budget.spent()
const gastoInicial = budget.spent()
let feedback = null   // do #2 pro #1 na volta seguinte (a seta de volta)
let lawMark = null    // marca da lei do projeto, CONGELADA na rodada 1 (ver o pino abaixo)
const taskChurn = {}  // { task_id: nº de rodadas seguidas reaparecendo em missingTasks/gaps }
const impossivelChurn = {}  // { task_id: nº de rodadas seguidas em que o executor alegou impossível }

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
    const v = await agent(tentativa === 1 ? prompt : { ...prompt,
      recusado: 'o veredito anterior voltou SEM a âncora do fim e foi recusado — devolva em `anchor` a última linha não vazia do que você julgou, literal' }, opts)
    if (!v) return null
    if (v.anchor) return v
  }
  return null
}

while (!built && r < maxRounds) {
  r++; phase(`Rodada ${r}`)
  const tier = tierFor(r)

  // DECOMPOR — Opus #1, no tier da rodada. r==1: decompõe o plano inteiro; r>1: só o
  // DELTA do feedback. NUNCA re-arquiteta; buraco que exige decisão de arquitetura
  // vira blocker (não vira tarefa).
  const decomp = await agent(decomposePrompt({ planPath: ARGS.planPath, planText: ARGS.planText, round: r, feedback }),
    { model: tier.model, effort: tier.effort, phase: 'Decompor', schema: DECOMP })
  // Decompositor morto derruba a rodada inteira (não há tarefa a executar). Sai do laço em
  // vez de estourar — o que já foi construído nas rodadas anteriores continua valendo.
  if (!decomp) {
    blockers.push({ what: `decompositor da rodada ${r} não respondeu`,
                    whyNeedsYou: 'sem decomposição não há o que executar nesta volta' })
    break
  }
  if (decomp.blockers?.length) blockers.push(...decomp.blockers)

  // ── A RÉGUA DO `pronto` É COBRADA POR CÓDIGO, NÃO SÓ NA PROSA (F8.2 · S-14) ──
  // O julgamento do critério existia só como instrução ao #1, e instrução em prosa não
  // recusa nada: bastou o decompositor não julgar para o critério-armadilha chegar
  // inteiro ao executor, que o cumpriu escrevendo o valor à mão dentro do entregável.
  // Aqui o script roda a MESMA régua do plano (`regua_pronto.py`, do plugin visual) sobre
  // o `pronto` de CADA tarefa, ANTES de qualquer executor sair. Reprovado não vira tarefa:
  // sai de `decomp.tasks` e vira Bloqueio de `kind: 'criterio'` — o passo da spec é que
  // precisa reescrever o critério, e isso é do dono.
  // Agente mudo NÃO recusa nada (fail-open, mesma direção da reserva): travar a missão
  // por infra de gate é pior que gate nenhum, e o gate real do critério é o revisor.
  const regua = await agent(reguaPrompt({ repoRoot: ARGS.repoRoot,
                                          criterios: decomp.tasks.map(t => ({ id: t.id, pronto: t.pronto })) }),
    { model: ARGS.model, effort: T.mechanical.effort, phase: 'Decompor', schema: REGUA })
  const bancada = new Map((regua?.reprovados || []).map(x => [x.task_id, x.motivo]))
  for (const t of decomp.tasks.filter(t => bancada.has(t.id))) {
    blockers.push({ taskId: t.id, kind: 'criterio',
                    what: `o critério de aceite de ${t.id} é bancada: ${bancada.get(t.id)}`,
                    whyNeedsYou: `nenhum executor foi solto nesta tarefa — reescreva o \`pronto\` do passo "${t.requisito || t.id}" na spec para dizer o que REGERA o artefato a partir do dado real, e rode o motor de novo` })
  }
  decomp.tasks = decomp.tasks.filter(t => !bancada.has(t.id))

  // DIAGNÓSTICO de tarefa-presa — antes de tentar de novo, escala quem já reaparece
  // ≥ churnThreshold rodadas seguidas pro diagnose_model (medium): causa raiz, não repetição.
  const diagnoses = []
  for (const t of decomp.tasks) {
    if (taskChurn[t.id] >= churnThreshold) {
      const diag = await agent(diagnoseStuckTaskPrompt({ task: t, attempts: taskChurn[t.id] }),
        { model: ARGS.model, effort: T.diagnose.effort, phase: 'Diagnose' })   // diagnose_model
      diagnoses.push({ task_id: t.id, diagnosis: diag })
    }
  }

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
      { model: ARGS.model, effort: T.mechanical.effort, phase: 'Executar', schema: RESERVA })
    // Fail-open, mesma direção do hook: quem foi consultar e não voltou não recusa nada.
    // Travar a missão por infra de gate é pior que gate nenhum.
    if (reserva?.recusado) {
      desligadoPor = 'reserva'
      blockers.push({ what: `outro motor desta sessão já reservou: ${(reserva.arquivos || []).join(' · ')}`,
                      whyNeedsYou: 'dois motores no mesmo arquivo é um apagando o trabalho do outro — espere o outro terminar (ele libera ao sair) ou recorte a missão para arquivos que não encostem nos dele' })
      break
    }
  }
  const par = todo.filter(t => t.parallelizable && !(t.dependsOn?.length))
  const seq = todo.filter(t => !t.parallelizable || (t.dependsOn?.length))
  const execTier = t => ({ model: ARGS.model,
    effort: t.complexity === 'mechanical' ? T.mechanical.effort : T.executor.effort })
  // quem NÃO colide vai junto; quem colide vai depois, um de cada vez, no MESMO repo
  const livres = par.filter(t => !touchesShared(t, par))
  const colidem = par.filter(t => touchesShared(t, par))
  // `tetoMin` vai em TODO execPrompt: o teto tem que chegar a quem tem relógio. O script
  // não tem (ver o vigia), então teto que ficasse só aqui não seria teto de ninguém.
  // `buildWarm` vai junto, pelo mesmo motivo: quem compila é o executor, e cache quente
  // que não chega a ele é cache que ele derruba com um `clean` de rotina.
  const builtPar = await parallel(livres.map(t => () =>
    agent(execPrompt({ task: t, tetoMin: tetoExecutorMin, buildWarm }), {
      model: execTier(t).model, effort: execTier(t).effort, phase: 'Executar', schema: TASK_RESULT })))
  for (const t of colidem) builtPar.push(await agent(execPrompt({ task: t, tetoMin: tetoExecutorMin, buildWarm }),
    { model: execTier(t).model, effort: execTier(t).effort, phase: 'Executar', schema: TASK_RESULT }))
  const builtSeq = []
  for (const t of seq) builtSeq.push(await agent(execPrompt({ task: t, tetoMin: tetoExecutorMin, buildWarm }),
    { model: execTier(t).model, effort: execTier(t).effort, phase: 'Executar', schema: TASK_RESULT }))
  // Os DOIS lados filtram: `parallel()` devolve null pra thunk que falhou, e o executor
  // sequencial devolve null pelo mesmo motivo (agente morto). Filtrar só o paralelo deixava
  // um `null` entrar em `results` e virar `TypeError` no revisor — a tarefa some do relato
  // em vez de reaparecer em `missingTasks`, que é o caminho que a manda de volta pro #1.
  const respostas = builtPar.filter(Boolean).concat(builtSeq.filter(Boolean))

  // ── UM EXECUTOR LENTO NÃO SEGURA A RODADA (F9.29) ───────────────────────────
  // Medido em 2026-08-06: 21 agentes já entregues esperaram 2 HORAS por um só que
  // ciclava, e a rodada não fechou pra ninguém — a onda só termina quando o último
  // volta. O teto está no texto do executor (regra 4); o que é do SCRIPT é o que
  // fazer com quem estourou: `espera: true` NÃO é resultado. Sai de `results` (o
  // revisor não recebe meia obra como obra), entra no `missing` do #1 na volta
  // seguinte, e a rodada FECHA com quem voltou. Sem esta separação, o teto do
  // executor seria só um jeito mais educado de perder o trabalho da onda.
  const esperaIds = respostas.filter(x => x.espera).map(x => x.task_id)
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
                                                alegacao: x.impossivel, ferramentas: x.ferramentas || [],
                                                onus: 'invertido — cabe a VOCÊ provar que não dá; o executor não precisa provar que dá',
                                                cobra: 'diga em naoTentou quais das ferramentas acima o executor nem tentou',
                                                tentativas: impossivelChurn[x.task_id] }),
      { model: ARGS.model, effort: T.diagnose.effort, phase: 'Diagnose', schema: AUDITOR })   // diagnose_model
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
  // Esta skill proíbe reescrever documento aprovado, e o decompositor continuava
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

  // REVISAR — Opus #2, no tier da rodada (coordinate_model). Contra a SPEC (o plano vai
  // junto, igual ao #1): spec + constituição + rastreio + completude + coesão. A decomposição
  // entra como meio, não como contrato. O eixo de rastreio reprova tarefa decomposta sem
  // `requisito` ou sem `pronto` (gap kind:'rastreio'). O eixo de constituição manda LER
  // `<repoRoot>/.claude/docs/constituicao.md` e o `quality-goals.md` na rodada (nunca
  // uma cópia daqui) e é
  // fail-open: arquivo ausente = eixo não roda, e isso NÃO vira gap.
  // NÃO roda a suíte nem caça bug — isso é o /qa-loop depois.
  // `lawMark` vai junto: na rodada 1 é null (o #2 calcula e devolve); nas seguintes é a
  // marca FIXADA, contra a qual ele mede — não contra o texto que estiver no disco agora.
  // `protegidas` vai junto: nelas o critério do #2 é o INVERSO do normal — proposta com
  // antes/depois literais aprova, e arquivo protegido aparecendo no git diff reprova.
  const review = await julga(reviewBuildPrompt({ planPath: ARGS.planPath, planText: ARGS.planText, repoRoot: ARGS.repoRoot, decomp, results, round: r, lawMark, protegidas: [...protegidas] }),
    { model: tier.model, effort: tier.effort, phase: 'Revisar', schema: BUILD_REVIEW })

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
                  devolvidas: devolvidasPeloAuditor })
    feedback = { gaps: [], missing: [...esperaIds, ...devolvidasPeloAuditor.map(d => d.taskId)],
                 diagnoses, devolvidas: devolvidasPeloAuditor }
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
  const stuck = new Set([...(review.missingTasks || []), ...(review.gaps || []).map(g => g.task_id)])
  for (const t of decomp.tasks) taskChurn[t.id] = stuck.has(t.id) ? (taskChurn[t.id] || 0) + 1 : 0

  rounds.push({ r, decomp, results, review, diagnoses, espera: esperaIds, esperandoVoce,
                devolvidas: devolvidasPeloAuditor })

  // ── PONTO DE SALVAMENTO POR ONDA (F9.14/F9.15) ──────────────────────────────
  // Até aqui o trabalho só era salvo no FIM: motor interrompido no meio deixava tudo
  // solto no disco e a sessão seguinte não sabia o que já tinha saído. Agora cada onda
  // que fecha VERDE vira ponto de salvamento — e onda VERMELHA não salva, senão o
  // checkpoint viraria "salvei a quebra".
  //
  // A suíte roda ao FIM DE CADA ONDA, não no fim da missão. Rodando só no fim, a quebra
  // chega com vinte tarefas empilhadas em cima dela e ninguém sabe qual a causou.
  const suite = await agent(runSuitePrompt({ repoRoot: ARGS.repoRoot, round: r }),
    { model: ARGS.model, effort: T.mechanical.effort, phase: 'Suíte', schema: SUITE_RESULT })
  if (!suite) {
    // Mesma porta das outras: quem não respondeu não aprovou. Sem veredito da suíte a
    // onda NÃO vira checkpoint — a direção segura é não salvar.
    blockers.push({ what: `a suíte da rodada ${r} não respondeu`,
                    whyNeedsYou: 'esta onda ficou SEM checkpoint — o trabalho está no disco, não no histórico' })
  } else if (suite.green) {
    // O PLACAR DA SUÍTE NÃO SE PERDE (F9.27). O campo era pedido ao papel da suíte e
    // descartado aqui — a comparação entre ondas, que é o único sinal medido de "está
    // em círculos", não chegava a tela nenhuma. Quem compara é `lib/andamento.py:avanco`,
    // pelo gancho de andamento (ele vê a saída crua da suíte), e o veredito sai no
    // cartão da onda e na barra. Guardar no registro é o que deixa o relatório contar
    // onda a onda o que a suíte fez.
    rounds[rounds.length - 1].placar = suite.placar
    await agent(checkpointPrompt({ repoRoot: ARGS.repoRoot, round: r, results }),
      { model: ARGS.model, effort: T.mechanical.effort, phase: 'Salvar' })
    rounds[rounds.length - 1].checkpoint = true

    // ── A DOC DA ONDA VERDE (F9.32) ───────────────────────────────────────────
    // O checkpoint só gravava CÓDIGO. Quem executava a onda seguinte lia a doc da
    // rodada anterior — e ela ainda descrevia o repo de antes. Por isso a onda verde
    // fecha com a doc dos arquivos que ELA tocou re-projetada, e nesta ordem: commit
    // primeiro (o trabalho no histórico não depende da doc dar certo), doc depois.
    // Onda vermelha não chega aqui: doc de repo quebrado documenta a quebra.
    const tocados = [...new Set(results.flatMap(x => x?.files_touched || []))]
    if (tocados.length) {
      await agent(docTouchPrompt({ repoRoot: ARGS.repoRoot, round: r, files: tocados }),
        { model: ARGS.model, effort: T.mechanical.effort, phase: 'Doc' })
      rounds[rounds.length - 1].doc = tocados
    }

    // ── O CAMINHÃO DO LIXO PASSA JUNTO DO CHECKPOINT (F9.38) ──────────────────
    // A onda abre suíte, build e servidor, e nada disso morria: ficava de pé até
    // alguém reclamar da máquina. Aqui a colheita é a SELETIVA do turno — efêmero
    // ainda vivo morre, serviço em uso sobrevive —, senão a onda seguinte perderia
    // o servidor que ela mesma ia usar.
    await agent(colheitaPrompt({ repoRoot: ARGS.repoRoot, round: r }),
      { model: ARGS.model, effort: T.mechanical.effort, phase: 'Lixo' })
  } else {
    // Onda vermelha: relata QUAL quebrou. "A suíte falhou" sem o nome manda a próxima
    // rodada procurar no escuro.
    blockers.push({ what: `a suíte quebrou na rodada ${r}: ${suite.failing?.join(' · ') || 'sem detalhe'}`,
                    whyNeedsYou: 'onda vermelha não vira ponto de salvamento — conserte antes de seguir' })
  }

  // ── O MOTOR ESCREVE NO PLANO O QUE ACABOU DE FAZER (F9.10) ──────────────────
  // Ele LIA o plano pra saber o que fazer e NUNCA escrevia de volta. Consequência medida:
  // a sessão seguinte não sabia o que já tinha saído e refazia — e uma auditoria inteira
  // foi gasta pra descobrir isso. Quem marca é o motor, com a prova do executor, porque
  // exigir que alguém marque à mão depois é a mesma promessa que já falhou.
  //
  // ── A CONTAGEM NÃO CONTA O MESMO PASSO DUAS VEZES (F9.35) ───────────────────
  // Retomar a missão REGRAVA veredito: o runtime replica do cache o que já tinha sido
  // entregue, e o mesmo `task_id` volta em mais de uma linha de `results` — junto com a
  // devolução do decompositor, que não é passo e vem SEM `task_id`. Quem contava linha
  // via cinco onde havia três, e o papel de marcação era disparado duas vezes pelo mesmo
  // passo. A conta é por `task_id` DISTINTO, e linha sem `task_id` não entra.
  const feitosDaOnda = [...new Map(results.filter(x => x?.done && x.task_id)
    .map(x => [x.task_id, x])).values()]
  rounds[rounds.length - 1].feitos = feitosDaOnda.map(x => x.task_id)
  if (ARGS.planPath?.endsWith('.plan.json')) {
    for (const t of feitosDaOnda) {
      await agent(tickPlanPrompt({ planPath: ARGS.planPath, taskId: t.task_id,
                                   evidencia: `${t.summary} · ${(t.files_touched || []).join(' ')}` }),
        { model: ARGS.model, effort: T.mechanical.effort, phase: 'Marcar' })
    }
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
  if (suite?.heartbeat) ultimoSinalDeVida = suite.heartbeat
  const mudo = agora - ultimoSinalDeVida
  if (mudo > silenceLimitMs && !suite?.trabalhoVivo) {
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
        { model: ARGS.model, effort: T.finalize.effort, phase: 'Confirmar', schema: BUILD_REVIEW })   // finalize_model
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
  feedback = { gaps: review.gaps.filter(g => g.kind !== 'concepcao'),
               missing: [...new Set([...(review.missingTasks || []), ...esperaIds,
                                     ...devolvidasPeloAuditor.map(d => d.taskId)])],
               diagnoses, devolvidas: devolvidasPeloAuditor }   // alimenta o DECOMPOR da próxima volta
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

return {
  rounds, built, blockers, lawMark,   // lawMark = a lei contra a qual a missão INTEIRA foi medida
  progresso: { feitos: passosFeitos.length, passos: passosFeitos },   // por tarefa distinta
  impedidos,          // não sai com mais rodada — precisa de você
  naoDeuTempo,        // sairia com mais rodada; o teto é que chegou antes
  esperandoVoce,      // nem falha nem falta de tempo: espera um ato seu, declarado no plano
  gasto: gastoAgora() - gastoInicial,
  stopReason: desligadoPor || (built ? 'build-complete' : 'max-rounds'),
  // `tasks` conta TAREFA distinta da onda, não linha de `results` (F9.35): linha repetida
  // pelo replay do cache e linha sem `task_id` (a da decomposição) não são passos.
  telemetry: rounds.map(x => ({ round: x.r,
                                tasks: new Set((x.results || []).filter(t => t?.task_id)
                                                               .map(t => t.task_id)).size,
                                gaps: x.review?.gaps.length ?? null,
                                checkpoint: !!x.checkpoint })),
}
```

**Schemas (JSON Schema, resumidos):**
- `DECOMP` — `{ tasks: [{ id, desc, requisito, pronto, files: [...], parallelizable: bool, dependsOn: [id...], done: bool, complexity?: 'standard'|'mechanical', esperaDono?: string, protegido?: string }], blockers: [{ what, whyNeedsYou }] }`. **`requisito` e `pronto` são obrigatórios** — `requisito` = o item da spec que a tarefa atende, `pronto` = o critério de feito dele, **os dois copiados da spec, não redigidos pelo decompositor** (o executor não tem como cumprir o que não recebe, e critério inventado aqui vira régua falsa no #2). Item da spec sem um dos dois vira `blocker`, não tarefa. `complexity: 'mechanical'` = operação bem delimitada (renomear, mover arquivo, 1 config, 1 valor); ausente/`'standard'` = tarefa normal. **`esperaDono`** = a frase do ato que só o dono pode fazer, **copiada do `espera_dono` do passo no `.plan.json`** — nunca inventada aqui, e nunca deduzida do texto da tarefa. Tarefa com `esperaDono` **não entra na fila do motor** (nenhum executor é solto nela), e quem `dependsOn` dela também não: os dois saem em `esperandoVoce`, com o motivo. Passo sem o campo no plano é tarefa normal. **`protegido`** = o arquivo sob tranca que a tarefa toca (o que traz `status: approved` no frontmatter) e o motivo da tranca, marcado pelo decompositor **por leitura do disco**, nunca por achismo. Tarefa `protegido` **entra na fila** — o que muda é o entregável: proposta, não edição, e o revisor a mede pelo critério invertido.
- `TASK_RESULT` — `{ task_id, files_touched: [...], summary, done: bool, note, anchor, espera: bool, impossivel?: string, ferramentas?: [...], proposta?: { arquivo, antes, depois } }`. **`impossivel`** = a alegação de que a tarefa não tem como sair, com o motivo; **`ferramentas`** = o que havia à mão no contexto dela. Alegar não encerra nada: repetida por `churnThreshold` rodadas seguidas na mesma tarefa, ela convoca o `AUDITOR`. **`proposta`** = o entregável da tarefa `protegido` (regra 5 do executor): `antes` e `depois` **literais**, o primeiro copiado do disco e o segundo pronto pra colar. O script cobra os dois — proposta sem um deles vira `done: false` e Bloqueio, porque descrição do que mudar deixa o trabalho todo pro dono. Com os dois, a proposta sai em **Bloqueios (precisam de você)** com o antes/depois inteiro, e `git diff` vazio no arquivo é o resultado certo. **`anchor`** = a última linha não vazia do que o executor leu para decidir que estava pronto — a prova de leitura inteira (ver "o juiz prova que leu"). **`espera`** = o executor bateu no `tetoMin` e parou por isso (regra 4 dele). O script tira essas do `results` — o revisor não recebe meia obra como obra — e as manda pro `missing` do #1 na volta seguinte; a rodada **fecha com quem voltou**. `espera: true` não é falha e não vira Bloqueio: sai em `naoDeuTempo`, com o teto no motivo.
- `AUDITOR` — `{ derruba: bool, motivo, naoTentou: [...], anchor }`, devolvido por `auditorPrompt` (`diagnose_model`). A lente é **invertida**: o ônus é do auditor provar que **não dá**, e ele recebe `ferramentas` — o que havia à mão — para dizer em `naoTentou` o que o executor nem tentou. `derruba: true` **devolve a tarefa ao loop** (ela entra no `missing` do #1 na volta seguinte, com o que o auditor apontou); `derruba: false` **encerra como impedimento real** — Bloqueio de `kind: 'impedimento'` com o `motivo` escrito. Auditor mudo não encerra nada: a tarefa volta pro loop, porque quem não respondeu não confirmou impedimento. Como todo veredito, sem `anchor` ele é recusado e o papel roda de novo.
- `SUITE_RESULT` — `{ green: bool, failing: [nome...], placar, heartbeat, trabalhoVivo: bool }`. **`placar`** = a linha crua que a suíte imprimiu (`139 passou · 0 falhou`, `OK (56 checks)`, `17 ok / 0 falhas`), lida por `lib/andamento.py:placar` e comparada com a da onda anterior por `lib/andamento.py:avanco` — dois placares iguais seguidos saem como `sem avanço`. O veredito aparece nas **duas** superfícies: no cartão que fecha a onda (`hooks/posttooluse-andamento.sh`, que vê a saída crua da suíte) e na **barra** (`hooks/statusline-motor.sh` → `linha_placar`), que é a que fica. O registro é um só, em `~/.claude/sovai/placar-<sid>` — o motor guarda o campo na onda (`rounds[].placar`) e não o descarta mais. **`trabalhoVivo`** separa demora de travamento: com ele `true`, o vigia **não** derruba, por mais silencioso que esteja o registro. **`heartbeat`** = o carimbo de tempo do último sinal de vida, que a casca reinjeta a cada rodada (o script não tem relógio próprio).
- `blocker` de `kind: 'criterio'` — critério de aceite que só se cumpre injetando valor inventado dentro de entregável. Não vira tarefa: vira Bloqueio, e o `whyNeedsYou` diz qual passo da spec precisa reescrever o `pronto`. **Quem o emite é o SCRIPT**, logo depois da decomposição e antes de qualquer executor sair (ver o bloco da régua no esqueleto) — não é julgamento do #1.
- `REGUA` — `{ reprovados: [{ task_id, motivo }] }`. O papel é **mecânico e só**: para cada `{ id, pronto }` recebido, rodar

  ```bash
  printf '%s' "<pronto>" | python3 <plugin visual>/lib/regua_pronto.py --onde <id> -
  ```

  e devolver em `reprovados` os que saíram com **exit 1**, com `motivo` = a linha que o programa imprimiu. Exit 0 não aparece na lista. **Sem julgamento próprio**: quem decide é o programa — a régua é uma só, a mesma que o `plan_state.py` cobra na gravação do plano, e re-julgar aqui por leitura faria o motor e o plano recusarem coisas diferentes. Programa ausente na máquina ou comando quebrado = `reprovados: []` (fail-open, como a reserva).
- `RESERVA` — `{ recusado: bool, arquivos: [caminho...] }`. O papel é **mecânico e só**: rodar `${CLAUDE_PLUGIN_ROOT}/hooks/reserva-de-arquivos.sh reservar <sessionId> <motorId> <arquivo>...` e devolver o veredito do JSON que saiu — `recusado: true` quando veio `permissionDecision: "deny"`, com `arquivos` = os caminhos em disputa que a recusa nomeou. Script mudo = `recusado: false` (reservou). Sem julgamento próprio: quem decide é o hook, o agente só transporta.
- `tickPlanPrompt` — **sem schema** (nada volta pro script). Papel **mecânico e só**: gravar no plano o passo que acabou de sair, rodando

  ```bash
  python3 <plugin visual>/lib/plan_state.py --dir <raiz>/.claude/plans tick <plano> <taskId> --evidencia "<evidencia>"
  ```

  A prova é **a do executor** (`summary` + `files_touched` do `TASK_RESULT`), nunca redigida por quem marca: o `tick` recusa marcação sem prova, e prova inventada aqui seria o carimbo sem a obra. Recusa do `tick` (decisão em aberto, passo fora do schema) **não derruba a onda** — o trabalho já está no disco, e perder a onda por causa do registro é pior que o registro faltando. Plano que não é arquivo (`planPath` sem `.plan.json`) não é marcado por ninguém: o script nem chama este papel.
- `checkpointPrompt` — **sem schema** (nada volta pro script). Papel **mecânico e só**: gravar no **histórico do git** o que a onda verde produziu, rodando

  ```bash
  git -C <raiz> add -A && git -C <raiz> commit -q -m "sovai: onda <r> verde" || true
  ```

  É este commit que faz motor interrompido no meio (vigia, disjuntor, sessão morta) deixar as ondas já fechadas **no histórico** em vez de soltas no disco — sem ele, quem chegar depois não tem como separar o que fechou verde do que ficou pela metade. Commit **local e só**: o push é uma vez, na persistência do fim. Árvore limpa faz o `commit` sair não-zero, e isso **não** é falha — o `|| true` é o fail-open, pela mesma regra do `tick`: perder a onda por causa do registro é pior que o registro faltando.
- `docTouchPrompt` — **sem schema** (nada volta pro script). Papel **mecânico e só**: invocar a skill **`project-doc:doc-touch`** (Skill tool, `skill: "project-doc:doc-touch"`) com a lista `files` — os arquivos que ESTA onda tocou (a união dos `files_touched` dos `TASK_RESULT`) — para que a doc deles seja re-projetada antes de a onda seguinte começar. Sem isso, quem executa a rodada seguinte lê a doc do repo de antes e decide por um mapa vencido. Roda **depois** do `checkpointPrompt` e só na onda verde: commit primeiro, porque o trabalho no histórico não pode depender de a doc dar certo; doc de repo quebrado documentaria a quebra. Onda sem arquivo tocado não chama este papel. Quem decide touch-vs-FULL é o próprio touch (mesma regra da Persistência) — aqui ele escala e segue, sem perguntar. Falha do touch **não derruba a onda**: o commit já está feito, e perder a onda por causa da doc é pior que a doc faltando.
- `colheitaPrompt` — **sem schema** (nada volta pro script). Papel **mecânico e só**: mandar o lixeiro colher o que ESTA sessão anotou ter aberto, rodando

  ```bash
  LIXEIRO="$(bash "${CLAUDE_PLUGIN_ROOT}/skills/sovai/resolve-plugin.sh" lixeiro lib/lixeiro.py)"
  if [ -n "$LIXEIRO" ]; then
    python3 "$LIXEIRO" colhe-turno --sessao "$CLAUDE_CODE_SESSION_ID" \
      || echo "sovai: a colheita falhou em $LIXEIRO — segue sem colher"
  fi
  ```

  **O lixeiro é procurado pelo NOME, nunca pela posição.** Quem resolve é o `resolve-plugin.sh` da própria pasta: rodando do repositório o lixeiro é irmão direto, e instalado pelo marketplace o cache guarda `<marketplace>/<plugin>/<versão>/` — dois níveis acima e atrás de um segmento de versão, com a versão mais alta escolhida quando o cache tem várias. Apontar a pasta vizinha na mão resolvia só o primeiro caso, e a colheita nunca acontecia em máquina instalada. Saída vazia = lixeiro fora desta máquina. As duas falhas ficam **separadas**: lixeiro não instalado (nenhum caminho existe) sai **calado**, que é a regra escrita; caminho resolvido e comando quebrado avisa em uma linha — fail-open igual, mas visível, senão o defeito some. Sempre `colhe-turno`, nunca `colhe-sessao`: o modo do turno é o **seletivo** — efêmero ainda vivo (suíte, build) morre, serviço com CPU parada desde a passada anterior morre, serviço em uso **sobrevive**. É isso que deixa a colheita rodar no meio da missão sem tirar da onda seguinte o servidor que ela ia usar. Só é candidato o processo cuja ABERTURA foi anotada — nome de programa nunca é critério, e é o motor do lixeiro que aplica as travas (ancestral, VM, contêiner), não este papel. No script ele roda **junto do `checkpointPrompt`**, em toda onda verde. A última passada não é papel de agente: é o **passo 4 da Persistência**, o mesmo comando em bash — porque a colheita por onda não alcança o motor que fechou vermelho, que o vigia derrubou ou que o disjuntor desligou, e agente disparado depois do disjuntor desfaria o desligamento. Lixeiro ausente na máquina (`lixeiro.py` não existe) **não é falha**: o papel devolve sem fazer nada e a missão segue — limpeza é camada a mais, nunca pré-requisito. Falha da colheita **não derruba a onda** nem a missão, pela mesma regra do `tick` e do `docTouch`.
- `BUILD_REVIEW` — `{ complete: bool, cohesive: bool, gaps: [{ task_id, kind: 'spec'|'constituicao'|'concepcao'|'rastreio'|'completude'|'coesao', severity: 'P0'|'P1'|'P2'|'P3', problem }], missingTasks: [id...], lawMark: string|null, anchor: string }`. **`anchor`** = a última linha não vazia do que o juiz julgou, literal — a prova de leitura inteira (ver "o juiz prova que leu"). **É o script que cobra**: veredito sem ela é RECUSADO, o papel roda de novo sabendo por quê, e duas recusas seguidas valem por juiz que não respondeu (não aprova nada). Vale para o revisor #2 e para o confirm-pass. **`lawMark`** = a marca da lei que ESTA rodada leu — o `cksum` do corpo de `.claude/docs/constituicao.md` + `.claude/docs/quality-goals.md` (mesma receita da marca de aprovação; corpo, sem frontmatter). Projeto sem esses arquivos devolve `null` e o pino nunca arma. O motor congela a marca da rodada 1 e a devolve ao revisor nas seguintes; marca diferente da fixada **não** troca a régua — vira aviso no relatório (Bloqueio "precisa de você"). `kind: 'rastreio'` = tarefa decomposta chegou **sem `requisito` ou sem `pronto`** — nasce em severidade **≥ `severityFloor`** e o script o segura no filtro mesmo se vier abaixo (mesmo tratamento do gap de spec), porque tarefa sem os dois campos não é medível por ninguém depois. `kind: 'spec'` = o que a spec pede não saiu (ou saiu diferente), **mesmo com a decomposição cumprida** — nasce em severidade **≥ `severityFloor`** (P1 por default) e o script o mantém no filtro mesmo se vier abaixo, senão o gap sai da conta e passa calado. `kind: 'constituicao'` = o que saiu viola a `.claude/docs/constituicao.md` ou o `.claude/docs/quality-goals.md` do projeto — severidade normal (o filtro de floor vale), e `problem` cita a passagem violada, porque a régua vive no arquivo lido na rodada, não aqui. Sem esse arquivo no projeto, este `kind` simplesmente não aparece. `kind: 'concepcao'` = o que a execução descobriu contradiz um documento de concepção já aprovado — **não segura a obra** (o executor não tem o que consertar no código), sai do filtro e vira aviso no relatório propondo reabrir a etapa, com a linha `correcao-pendente:` sugerida em `problem`. `task_id` de gap de spec ou de constituição pode ser `null`: o buraco que a decomposição não previu não tem tarefa a que pertencer.

O `stopReason`, o `gasto` (quanto a missão queimou — sem ele, "desliguei" não diz se foi caro ou barato), o `progresso` (**quantos passos DISTINTOS fecharam** — nunca linha de resultado somada: retomada regrava veredito do cache e a mesma tarefa volta em mais de uma linha, e a devolução do decompositor volta sem `task_id`), os `blockers` e a telemetria entram no relatório final (`### Verificação` e `### Bloqueios`); o `esperandoVoce` entra na seção `### Esperando você`, que é dele e de mais ninguém — despejá-lo em `### Bloqueios` é chamar de falha o que só espera a sua vez. Terminado o motor (`built` ou teto), segue direto pro **QA final** abaixo — que é onde defeito é caçado.

## QA final (antes do relatório)

Terminada a execução e **ANTES** de montar o relatório, rode a skill `/qa-loop` em **modo headless** sobre o que você implementou, passando o plano como âncora:

```
/qa-loop <mudanças desta sessão> --plan=<plano> --headless
```

Como o usuário está indisponível, o headless nunca pergunta nada. Trate os 3 buckets assim:
- **Implementação** (bug / divergência do plano) → conserta no loop. Você já tem mandato de executar o plano; o regression gate por conserto é a rede que evita as regressões auto-infligidas.
- **Plan-drift** (um "fix" afastaria do plano em UX/backend/proposta) → **reverte pro plano**. Não "melhore" pra longe do combinado.
- **Plano/arquitetura falho** → **NÃO implemente**. Vira item de "Bloqueios (precisam de você)" no relatório. Headless **não** é licença pra re-planejar.

O relatório do `/qa-loop` (loops rodados, correções, regressões pegas, alertas de plano) vira a seção `### QA` do relatório final.

**Se a skill `qa-loop` não estiver disponível** (foi o que você passou como `hasQaLoop=false` ao motor): o confirm-pass do motor já cobriu "está construído", mas **ninguém checou "está correto"**. Rode você mesmo o gate objetivo do projeto (lint · type · unit · integração, 100% verde no repo) e registre o resultado na `### Verificação`; o que não deu pra checar vai pra `### Bloqueios` dizendo **o que ficou sem cobertura** — nunca "QA ok".

## Persistência — doc + commit/push (antes do relatório)

Passada a QA e **ANTES** de montar o relatório, persista o trabalho. Esta é a última etapa de execução; o relatório só descreve o que já está salvo.

1. **Atualiza a doc.** Invoque a skill **`doc-touch`** (Skill tool, `skill: "project-doc:doc-touch"`) — **não** o `project-doc` FULL. Uma execução autônoma costuma mexer em arquivos, e a doc tem que refletir a realidade antes de você fechar; mas o caso comum é diff que cabe no `scope:` de 2-4 docs, e reminerar o repo inteiro pra isso é gasto puro. (Não "digite /doc-touch" — invoque a skill.)

   **Quem decide touch-vs-FULL é o próprio touch, não você.** O passo 1 dele calcula `last_full_age_days` (a data de `ledger.last_commit`, que só o FULL avança) e **escala pro FULL sozinho** se passou de 30 dias ou se o número não resolve. Aqui você está em modo autônomo: o touch escala **e segue**, sem perguntar. Não tente antecipar a decisão — a informação nasce lá, e mecanizar "isso é estrutural?" daqui é chutar.
2. **Commit + push.** Stage do que esta sessão mudou, commit com mensagem no padrão do repo (`feat(...)`/`fix(...)`/`docs(...)`, 1 linha) e push pra **branch atual**.
   - **Nunca** `--force`; **nunca** push direto numa branch protegida (`main`/`master`) — se a sessão estiver nela, crie uma branch de feature antes (mesma regra do "force push em main" do Contrato) e registre como decisão.
   - Árvore limpa (nada pra commitar) → pula e anota "nada a persistir".
   - Falha de push (sem remote, sem auth, rejeição) → **não force**; registra como `Bloqueio (precisa de você)` com o erro real e segue pro relatório (o commit local fica feito).

3. **Apaga o sinal do sovai e LIBERA os arquivos reservados.** É o par do `mkdir` da seção _Execução_ e da reserva que o motor fez antes de executar, e é obrigatório:

   ```bash
   rm -f "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sovai"/{ativo,bloqueios}-"$CLAUDE_CODE_SESSION_ID"
   bash "${CLAUDE_PLUGIN_ROOT}/hooks/reserva-de-arquivos.sh" liberar "$CLAUDE_CODE_SESSION_ID" "$SOVAI_MOTOR_ID"
   ```

   Reserva não liberada recusaria o próximo motor da sessão nos mesmos arquivos — é o mesmo esquecimento do sinal, com outro nome. (Há rede embaixo: a reserva expira por idade, mesma janela de 12h do sinal.)

   Deixar aceso faz a sessão inteira continuar sem poder despachar sub-agente **depois** de a missão acabar — o gate não sabe que você terminou, só sabe do arquivo.

4. **Passa o caminhão do lixo (F9.38).** A missão abriu suíte, build e servidor a cada onda, e nada disso morre sozinho: fica de pé até alguém reclamar da máquina. Última passada, e é obrigatória:

   ```bash
   LIXEIRO="$(bash "${CLAUDE_PLUGIN_ROOT}/skills/sovai/resolve-plugin.sh" lixeiro lib/lixeiro.py)"
   if [ -n "$LIXEIRO" ]; then
     python3 "$LIXEIRO" colhe-turno --sessao "$CLAUDE_CODE_SESSION_ID" \
       || echo "sovai: a colheita falhou em $LIXEIRO — segue sem colher"
   fi
   ```

   É o **mesmo** `colheitaPrompt` que roda junto do checkpoint de cada onda verde — aqui em bash, e por isso mesmo: esta passada tem que acontecer **aconteça o que acontecer com o motor**. A colheita por onda só alcança onda verde; motor que fechou vermelho, que o vigia derrubou ou que o disjuntor desligou não colheria nada — e pôr mais um agente no fim do script depois do disjuntor faria o desligamento por teto deixar de ser desligamento. O lixeiro é achado pelo **nome**, pelo `resolve-plugin.sh` da própria pasta — direto no repositório, e atrás de um segmento de versão no cache do marketplace (`<marketplace>/<plugin>/<versão>/`), que é o layout que o apontamento por posição não alcançava. Lixeiro não instalado (o resolvedor devolve vazio) → **pula e segue calado**, e é o `if` que garante isso: limpeza é camada a mais, nunca pré-requisito. Caminho resolvido e comando quebrado → também segue, mas **avisa** na saída do passo, e a linha do aviso vira item de `### Feito` dizendo que a colheita não passou; sem essa separação, defeito da colheita e ausência do lixeiro ficam com a mesma cara. O que foi encerrado vira item de `### Feito`; falha da colheita **não** vira Bloqueio.

O hash do commit + resultado do push entram na `### Verificação`; a doc regenerada é um item de `### Feito`.

## Relatório Final

O relatório é a única coisa que o usuário lê desta sessão — e ele lê **depois**, pra revisar tudo e refatorar. Por isso ele sai como uma **superfície de revisão em HTML**, não como textão no CLI.

### Conteúdo (backbone — sempre o mesmo)

Cinco seções. Monte este conteúdo PRIMEIRO; a forma de entrega (HTML ou markdown) vem depois.

```
## Sovai — terminei

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
- [⚠️ alertas de plano/arquitetura que NÃO implementei — pra você julgar]
```

### Entrega via /visual (titular)

Se a Skill **`visual`** estiver entre as suas skills disponíveis, **invoque-a** (Skill tool, `skill: "visual"`) e renderize o relatório como HTML. (Não "digite /visual" — invoque a skill.) `visual` é **dependência recomendada** do sovai; instale os dois juntos.

Por que HTML: o relatório é longo e completo, e o usuário vai **revisar item a item e refatorar**. O `/visual` tem o componente exato pra isso — veredito inline (`.feedback-item`: ✓ Manter / ✏️ Mudar / ✗ Remover) que ele marca enquanto lê.

**Mapeamento seção → componente** (instrua o /visual a montar a superfície de revisão):

No spec, **`item_labels: ["✓ Manter", "✏️ Mudar", "✗ Remover"]`** — NUNCA "✓ Vira ação" (esse é do relatório do /qa-loop: lá cada achado vira ação no próximo plano).

- **Bloqueios (precisam de você)** → **topo**, prioridade máxima. Default: `.callout` severidade alta (um bloqueio é "não consegui X porque faltou Y" — sem ramificação). **Só** vire `.decision-card` se houver escolha A/B **genuína** já clara — nunca fabrique duas opções pra preencher o card (regra anti-"chutar"). Os ⚠️ alertas de plano/arquitetura do qa-loop entram aqui (normalmente `.callout`; só decision-card se for binário de verdade).
- **Esperando você (não é falha)** → logo abaixo dos Bloqueios, `.callout` de severidade média — um por linha do `esperandoVoce`, com o `motivo` inteiro. Nunca misture com Bloqueios (lá é "não consegui"; aqui é "não tentei, porque é sua vez") nem com o que não deu tempo. Lista vazia: a seção não sai.
- **Feito** → cada item = `.feedback-item` com veredito inline + profundidade em `<details>`. O usuário revisa enquanto lê.
- **Decisões tomadas** → cada decisão = `.feedback-item` (o usuário aprova ou marca pra rever) + razão em 1 linha.
- **Verificação** → `.callout` (ok/danger): o que rodou + resultado. Read-only.
- **QA (qa-loop)** → `.callout`/seção: loops, correções, regressões, alertas. Read-only.
- `.exec` no fim + **caixa de fechamento**: no caso comum (feedback-items + callouts) só `feedback-box`; `decisions-box` só se houver decision-card de verdade. As caixas são **só fechamento** (progresso + observação + botões) — **nunca re-listam os itens** (anti-pattern "duas tabelas").

**Retorno do feedback é assíncrono.** O usuário está fora e esta sessão termina quando o relatório sai — então **não** conte com live-sync ("ele diz ok e o Claude lê"). O HTML guarda os vereditos em `localStorage`; quando ele voltar (provável sessão nova), clica "Copiar feedback"/"Copiar escolhas" e cola pra dirigir o refactor. O daemon do /visual pode subir (é inócuo), mas o caminho confiável é copy/paste.

**CLI mínimo** (o /visual proíbe duplicar o conteúdo no CLI): emita só

```
Sovai terminou. Relatório completo no browser: <path>
⚠️ Bloqueios (precisam de você): <título 1> · <título 2>   ← só os títulos, se houver
```

Os títulos dos bloqueios são um **índice** (não o conteúdo) — segurança, porque bloqueio é crítico e o usuário precisa vê-los mesmo sem abrir o browser. Nada além disso no CLI.

### Fallback (markdown)

Se a Skill `visual` **não** estiver disponível, emita o **relatório markdown completo** (o bloco de conteúdo acima, com as 6 seções preenchidas) direto no CLI. É um fallback à altura: entrega 100% da mesma informação — só a apresentação degrada, não o conteúdo.

Detalhe técnico só se o usuário pedir depois.
