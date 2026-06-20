# BRIEFING — Tornar o handoff um PRD do "que falta", não só do "que aconteceu"

**Para:** o próximo Claude que vai mexer na skill `handoff` (assuma zero contexto — leia isto inteiro).
**De:** sessão RAIOX (`/Users/pedroberaldo/PROGRAMACAO/VIU/VIUSTUDIO-RAIOX`), 2026-06-18, onde o Pedro pediu uma avaliação meta do handoff.
**Gatilho:** Pedro perguntou "de 0 a 10, quanto o HANDOFF.md é um PRD do que tem que ser feito?". Veredito: **6/10 como PRD do trabalho restante · 9/10 como briefing de continuidade.** Este doc transforma esse veredito em ações.
**Arquivos da skill (verificados nesta sessão, com linha):** ver §6.

---

## 1. O problema, em uma frase

O handoff conta **o que aconteceu** com rigor (estado, decisões, armadilhas — verbatim), mas descreve **o que falta fazer** como um índice de rótulos que aponta pra fora ("ver plano v3"), sem o requisito que torna o trabalho executável. Quem retoma sabe *que* há trabalho, não *como* fazê-lo.

**Evidência viva:** ao retomar a sessão RAIOX, o "Próximos Passos" dizia só *"Rodada 2: #1 drivers de título, #2 receita usa era, #3/#4 diff-in-diff n=1, #10 degrau duração. Maioria = apresentação + radar; ver plano v3."* Pra executar, tive que disparar um workflow de recuperação. E o `plano v3` que o handoff manda consultar **também não tinha a spec** — os 4 confounds estavam como "pendente decisão"; o diagnóstico técnico vivia num terceiro doc (os "32 achados"). Seguir o ponteiro não bastava.

---

## 2. A causa-raiz é MECÂNICA, não de capricho de escrita (CONFIRMADO no código)

Não é que aquela sessão escreveu um handoff preguiçoso. O **formato e o mecanismo** empurram todo handoff a olhar pra trás:

**(a) O material-fonte só contém passado.** O `extract_ata.py` lê o transcript e classifica cada item em tipos (`extract_ata.py:208-212`). Só **três** recebem `gate:True` — ou seja, só esses o gate força a aparecerem no PRD:
- `user_directive` (fala do Pedro) — `extract_ata.py:175`
- `tool_rejection` (feedback numa rejeição) — `extract_ata.py:166`
- `ask_answer` (resposta de AskUserQuestion) — `extract_ata.py:171`

Os três são **retrospectivos por construção**: são coisas que já foram ditas/decididas. Plano, task, diagrama e texto do assistant entram com `gate:False` (`extract_ata.py:196,201,188`).

**(b) Não existe "item de trabalho futuro" em lugar nenhum.** Nenhum `kind` representa "o que falta fazer". O futuro só entra no PRD se o Claude o escrever de cabeça na seção "Próximos Passos" — que **nada força a ser completo**.

**(c) O gate protege o passado, não o futuro.** O `handoff-completeness-gate.sh:49-50` confere que cada `[id]` forte do manifest aparece no PRD, e que não sobraram placeholders (`:51-54`). Resultado: **todo direcionamento passado é garantido; o trabalho futuro é 100% discricionário e sem rede de proteção.**

```
 TRANSCRIPT (só passado)                         PRD
 ─────────────────────────                       ───
 user_directive  ─gate:True──┐
 tool_rejection  ─gate:True──┼──► gate FORÇA ──► "Discussões/Decisões/O Que Foi Feito"  ✅ coberto
 ask_answer      ─gate:True──┘
                                                 "Próximos Passos"  ⚠️ ninguém força → afina
 (nada representa o FUTURO)   ─────────X─────────►   (discricionário, sem campos, sem gate)
```

---

## 3. A decisão de design que vem ANTES dos actionables (cravar com o Pedro)

A skill se descreve em dois chapéus que brigam: o cabeçalho diz **"This is NOT a todo list. It's a briefing"** (continuidade de entendimento), mas o artefato se chama **PRD** ("a vista normativa do que fazer"). São objetivos diferentes:
- **Briefing** prioriza: entenda o estado e o porquê. (Hoje: nota 9.)
- **PRD** prioriza: execute o que falta com requisito claro. (Hoje: nota 6.)

**Antes de aplicar os actionables, o Pedro decide o alvo:** empurrar a skill pra ser também um PRD executável (mexe na identidade dela), ou mantê-la como briefing e só reforçar o prospecto o suficiente pra ele não afinar. Os actionables abaixo servem aos dois alvos; o que muda é o quanto do A3/gate é obrigatório. **Não comece a editar sem essa resposta.**

---

## 4. Actionables (priorizados — cada um no formato que estamos propondo)

### A0 · O MOLDE LITERAL do item — o contrato que A1+A3+A4 compartilham (defina ANTES de tudo) — **PRIORIDADE 0**

A1 (template), A3 (regex do gate) e A4 (lista de placeholders) dependem da **mesma forma exata**. O gate casa placeholder por **substring literal** (`handoff-completeness-gate.sh:55`, `p in prd`), então a grafia (acento, chaves `{}`) tem que bater **byte-a-byte** entre o template do SKILL.md e a lista `PLACEHOLDERS` do hook. Cravar o molde errado quebra os três actionables. Defina, no SKILL.md, o **item vazio** (com placeholders entre `{}`) e um **item preenchido** de exemplo.

Molde proposto do item vazio (cada item de "Em Andamento" / "Próximos Passos"):

```text
### N. {título curto do passo}
- **Problema:** {1 linha humana — o que está faltando ou errado}
- **Ação:** {o que fazer concretamente}
- **Critério de pronto:** {como sei que terminou}
- **Arquivos prováveis:** {paths}
- **Decisão em aberto:** {as opções — ou "nenhuma"}
```

Strings que entram na lista `PLACEHOLDERS` do gate (substring, COM as chaves): `{1 linha humana`, `{o que fazer concretamente}`, `{como sei que terminou}`, `{paths}`, `{as opções`. **Toda divisão de trabalho posterior cita "o molde de A0".**

### A1 · "Próximos Passos" e "Em Andamento" passam a carregar requisito por item — **PRIORIDADE 1**
- **Problema:** hoje cada próximo passo é uma frase solta. Falta o que torna executável.
- **Ação:** no SKILL.md, seção **"HANDOFF.md (PRD) Format"**, reescrever os blocos `## Em Andamento` e `## Próximos Passos` usando **o molde literal de A0** (item vazio + exemplo preenchido). Espelha o rigor que "O Que Foi Feito" já tem. **Defina A0 primeiro — é o contrato.**
- **Critério de pronto:** o template no SKILL.md mostra o item vazio (com `{}`) E um exemplo preenchido; um handoff novo gerado a partir dele tem Próximos Passos que um terceiro executa sem abrir outro doc.
- **Arquivos:** `skills/handoff/SKILL.md` (seção "HANDOFF.md (PRD) Format" e "SAVE Rules").
- **Decisão em aberto:** os 5 campos são obrigatórios sempre, ou só quando há ≥1 item aberto? (Recomendo: obrigatórios quando "Em Andamento" ou "Próximos Passos" não está vazio — e essa é a mesma condição que gateia A3.)

### A2 · Regra "puxar a spec pra dentro; se não existe, o passo é destilá-la" — **PRIORIDADE 1**
- **Problema:** o PRD linka outro doc ("ver plano v3") em vez de conter o essencial — e às vezes o doc linkado *também* não tem a spec (foi o caso da Rodada 2).
- **Ação:** adicionar uma **SAVE Rule** no SKILL.md: *"Se um próximo passo referencia outro documento, transcreva o essencial inline. Se o documento referenciado também não especifica a ação (só lista/menciona), o próximo passo honesto é **'destilar a spec primeiro'** — não 'ver doc X'."*
- **Critério de pronto:** a regra existe nas SAVE Rules; um exemplo mostra a forma "destilar primeiro".
- **Arquivos:** `skills/handoff/SKILL.md` (seção "SAVE Rules").
- **Decisão em aberto:** nenhuma.

### A3 · Gate PROSPECTIVO — de **forma**, não de cobertura — **PRIORIDADE 2 (depende de §3)**
- **Problema:** sem rede, A1/A2 viram opcionais na prática e o handoff volta a afinar no futuro.
- **⚠️ Correção a uma proposta anterior:** *não* dá pra "espelhar o gate_items" aqui. O `gate_items` confere cobertura de itens do **manifest**, e o manifest só tem passado (§2). Um item futuro **não existe** no manifest — não há o que cobrir. O gate prospectivo certo é uma checagem **estrutural/de forma**: *"se a seção 'Próximos Passos' não está vazia, cada item tem os campos do molde A0?"*.
- **Ação:** estender `handoff-completeness-gate.sh`, **dentro do bloco condicional que já existe** (depois das guardas `prd_mtime >= man_mtime-1` em `:36` e do sentinel `okflag` em `:38-42`) — **NÃO** como verificação independente, senão dispara em TODO Stop (inclusive sessões que nada têm a ver com handoff). Recortar a seção por regex multiline (ex: `r'## Próximos Passos\n(.*?)(?=\n## |\Z)'`, DOTALL); se houver itens (linhas `### N.`/numeradas) mas faltar algum rótulo do molde A0 → `decision:block` (mesma emissão de `:72`).
- **⚠️ Regra da seção vazia:** seção vazia OU só com texto tipo "nada pendente" → **NÃO bloqueia** (senão todo handoff de "acabei tudo" trava). Distinguir item real (header/linha numerada) de prosa solta.
- **Complementaridade com A4:** A3 (parse) detecta "campo presente porém **vazio**"; A4 (substring) detecta "molde **não-substituído**" (a string `{}` ainda lá). São coisas diferentes — precisa dos dois.
- **Critério de pronto:** escrever um HANDOFF.md com Próximos Passos sem "Critério de pronto" → finalizar → o Stop hook bloqueia; preencher → libera. **Pré-condições do teste (senão fail-open dá falso "liberou"):** existir um `manifest-*.json` mais antigo que o PRD em `.claude/ata/`, e **reescrever o PRD** (muda o mtime) pra invalidar o `okflag` antes de cada re-teste. Testar caminho positivo E negativo.
- **Arquivos:** `hooks/handoff-completeness-gate.sh` (novo bloco entre `:42` e o `if not missing and not placeholders` de `:57`, reaproveitando o gatilho).
- **Decisão em aberto:** o gate prospectivo é hard-block (como hoje) ou só aviso? Depende do alvo de §3.

### A4 · RECONCILIAR a lista de PLACEHOLDERS do gate com o template — **PRIORIDADE 2**
- **Problema:** o gate detecta template não-preenchido por uma lista fixa de substrings (`handoff-completeness-gate.sh:51-54`, casamento por `p in prd` em `:55`). Três falhas, **todas confirmadas por grep nesta sessão**: (a) os campos novos do molde A0 não estão na lista → molde não-substituído passaria batido; (b) **órfã morta** — a lista contém `"{What was discussed"` (0 ocorrências no template; a seção "Discussões" usa `"{Por tema"`, que já está na lista); (c) **as duas seções prospectivas já não têm placeholder coberto hoje** — `"{What was left"` (Em Andamento, `SKILL.md:101`) e `"{Step with"` (Próximos Passos, `SKILL.md:104`) existem no template mas **faltam** na lista. O prospecto não é protegido nem no nível básico.
- **⚠️ Escopo:** A4 só pega o **molde-não-substituído** (a string `{...}` literal ainda no PRD). "Campo presente porém vazio" NÃO é A4 — é parse, escopo de A3. Logo os placeholders do A0 **precisam ter chaves `{}`** e grafia idêntica (byte-a-byte, com acento) ao template.
- **Ação:** **reconciliar 1:1** (não só adicionar): (1) remover a órfã `"{What was discussed"`; (2) adicionar os faltantes pré-existentes `"{What was left"` e `"{Step with"`; (3) adicionar as strings-com-chaves do molde A0.
- **Critério de pronto:** cada item da lista `PLACEHOLDERS` mapeia a uma chave que de fato existe no template, e cada chave do template tem sua string na lista (1:1, sem órfãs nem faltantes); um PRD com qualquer molde de A0 não-substituído é bloqueado.
- **Arquivos:** `hooks/handoff-completeness-gate.sh:51-54` + `skills/handoff/SKILL.md`.
- **Decisão em aberto:** nenhuma.

### A5 · RESUME converte "Próximos Passos" em plano de execução — **PRIORIDADE 3**
- **Problema:** o modo RESUME hoje "apresenta o resumo e pede confirmação" (SKILL.md, seção "Mode: RESUME"), mas não diz pra transformar os próximos passos num plano acionável — fica na mão do Claude.
- **Ação:** no RESUME, adicionar passo: *"para cada item de Próximos Passos, valide que os 5 campos estão presentes; se faltar, faça a arqueologia ANTES de executar (não execute a partir de menção)."* Conecta com a regra do Pedro "recuperar decisões antes de decidir".
- **Critério de pronto:** a seção RESUME instrui explicitamente a validar campos e a recuperar contexto faltante antes de agir.
- **Arquivos:** `skills/handoff/SKILL.md` (seção "Mode: RESUME").
- **Decisão em aberto:** nenhuma.

---

## 5. Como verificar (smoke test do rito, ponta a ponta)

1. Rodar o extrator numa sessão real: `python3 lib/extract_ata.py --auto --cwd <projeto> --out-dir <projeto>/.claude/ata` → confere que gera LOG + manifest e imprime `gate_items`.
2. Escrever um HANDOFF.md de teste com "Próximos Passos" **sem** os campos de A1 → finalizar a sessão → o Stop hook (`handoff-completeness-gate.sh`) deve `decision:block` (depois de A3 implementado).
3. Preencher os campos → finalizar de novo → deve liberar (cria o sentinel `okflag`).
4. **Atenção (fail-open):** o gate engole qualquer erro e sai `exit 0` (`:7-8` e `:75`). Um bug no regex de A3 não trava ninguém — mas também não protege. Teste o caminho positivo E o negativo.

---

## 6. Mapa dos arquivos da skill (verificado em 2026-06-18)

- `skills/handoff/SKILL.md` (10 KB) — a skill: detecção SAVE/RESUME, o rito (LOG verbatim + PRD), o **template "HANDOFF.md (PRD) Format"**, as **SAVE Rules**, o RESUME. **É aqui que vivem A1, A2, A5.**
- `lib/extract_ata.py` (14 KB) — extrator read-only do transcript. Gera o LOG verbatim + manifest. `collect()` classifica os records; `KIND_PREFIX`/`KIND_LABEL` em `:208-212`; `gate:True` só nos 3 tipos retrospectivos. **Não precisa mudar pra A1-A5**, mas é a prova de §2.
- `hooks/handoff-completeness-gate.sh` — **Stop hook** (gate de completude). Confere `[id]` fortes + placeholders. **É aqui que vivem A3, A4.** Fail-open.
- `hooks/hooks.json` — registra: `SessionStart` → `sessionstart-ata.sh`; `Stop` → o gate; `PreToolUse(TeamCreate)` → nudge.
- `hooks/sessionstart-ata.sh` — discovery do transcript (grava o sentinel `/tmp/claude-ata-session-*` que o `--auto` lê).
- `hooks/teamcreate-nudge.sh` — nudge ao criar clã (agrega transcripts de teammates no LOG).

---

## 7. Armadilhas / o que NÃO fazer

- **Não** tente forçar o futuro via manifest/gate_items — o futuro não existe como item no transcript (§2). O gate prospectivo é de forma (A3), não de cobertura.
- **Não** quebre o `is_human_prompt`/`SYSTEM_TAG_PREFIXES` (`extract_ata.py:40-45,126-134`) — é o que separa fala real do Pedro de injeção de sistema (slash commands, system-reminders). Mexer ali contamina o LOG.
- **Não** edite o LOG à mão (regra do rito) — o LOG é da máquina; só o PRD é escrito pelo Claude.
- **Não** assuma que o gate roda sempre — ele é fail-open e tem sentinel anti-redisparo por mtime (`:38-42`). Pra re-testar, reescreva o PRD (muda o mtime).

---

## 8. Contexto extra

- **Régua do Pedro (por que isso importa pra ele):** ele NUNCA decide a partir de resumo comprimido — faz arqueologia do raciocínio antes de executar trabalho continuado. Um PRD com prospecto fraco força essa arqueologia a ser do zero; com A1-A2 ela vira só validação. O custo do prospecto fraco recai inteiro no RESUME.
- **O caso que originou:** RAIOX, deck Massini, "Rodada 2 dos confounds". O handoff dessa sessão é um bom espécime pra testar as melhorias (Próximos Passos real, magro).
- **Veredito quantificado:** forte → o bug pré-existente e os "Findings & Gotchas" (verbatim, com causa-raiz) eram executáveis. Fraco → a Rodada 2 (a maior frente) e o commit (objetivo dado, separação não-pronta).
