# Método do explicador — como ensinar um conceito

Esta referência é o **motor do modo explicador**. Quando alguém pede um deck **pra explicar algo** (não transcrever um `.md` pronto), a skill **dirige a didática** — mas nunca calada: faz o intake, **propõe uma abordagem comparada com alternativas (prós/contras)** e **confirma** antes de montar.

Tudo aqui é cânone documentado (Minto, Duarte, Heath, Mayer, Jobs/Gallo, Kalyuga, Feynman, Medina, Shneiderman), **não palpite do modelo**.

---

## 0. Intake — pergunte só o que não veio no pedido

Antes de propor qualquer coisa, resolva (use o que está explícito; **pergunte o que faltar**):

1. **Público & nível** — pra quem é? Novato no tema, intermediário, ou expert? (Define o "dial" da família C.)
2. **Profundidade** — deck de **um nível** ou **progressivo** (abre acessível e aprofunda)?
3. **Altitude do dado** — resumo (executivo) ou granular (técnico)? Pode ser os dois via apêndice (ver §Granularidade).
4. **O trabalho do deck** — ensinar um conceito? defender uma mudança? apresentar uma análise? (Escolhe a arquitetura da família A.)

Se isso está claro no pedido, não pergunte — proponha direto.

---

## 1. Propor-e-confirmar (o protocolo)

Depois do intake, **antes de montar**, apresente uma proposta curta assim:

- **Abordagem recomendada**: qual arquitetura (A), como cada slide carrega a ideia (B), onde calibra pro público (C), quanto granular.
- **Alternativas**: 1–2 caminhos diferentes, com **prós/contras** de cada, pra a pessoa julgar.
- **Confirma ou ajusta.** Só monta depois do ok.

Isso respeita o "explicar o que aprovar": a pessoa vê a abordagem e os trade-offs antes de você gastar.

---

## 2. Família A — arquitetura narrativa (sequenciar o deck)

Escolha **uma** espinha pelo trabalho do deck. Não misture; uma história tem uma forma.

| Arquitetura | Use quando o deck... | Forma | Prós / contras |
|:--|:--|:--|:--|
| **Minto + SCQA** | apresenta análise / recomendação | Resposta primeiro → 3 argumentos → evidência. Entrada: Situação→Complicação→Pergunta→Resposta | + clareza executiva, vai direto · − pouca tensão emocional |
| **Sparkline (Duarte)** | precisa engajar / convencer | oscila "o que é ↔ o que poderia ser"; público é o herói, você é o mentor; termina na nova realidade | + emoção e contraste · − exige material pra contrastar |
| **5-partes (Raskin)** | defende uma mudança / pitch | nomeia a mudança → o que está em jogo → terra prometida → "presentes mágicos" → evidência | + urgência, foca no ganho · − formato de venda, nem todo tema cabe |
| **Story Spine (Pixar)** | conta causa-e-efeito / jornada | "era uma vez… todo dia… até que um dia… por causa disso… até que enfim" | + memorável, natural · − pode parecer informal demais |
| **Through-line (TED)** | ensina UMA ideia central | uma frase-âncora que costura tudo; cada slide serve a ela | + foco brutal · − exige cortar o que não serve à ideia |

Em todas: **regra de 3** (3 argumentos/blocos), e abertura que responde **"por que eu me importo?"** (Jobs) — benefício antes de mecânica. Aristóteles no fundo: equilibre **ethos** (fonte/credibilidade), **pathos** (por que importa) e **logos** (o dado).

---

## 3. Família B — o slide (uma ideia por slide)

- **Assertion-Evidence** (a espinha): o **título é uma frase-afirmação com a conclusão**, e o corpo é **um visual que prova**. Não use título-rótulo ("Resultados"); use a afirmação ("As vendas dobraram após o lançamento"). Comprovado: + compreensão, − carga cognitiva, + retenção.
- **Economia (Jobs / Presentation Zen)**: uma ideia por slide; pouquíssima palavra; **zero bullet decorativo**; muito respiro (kanso — beleza pela eliminação). O número vira humano ("1.000 músicas no bolso").
- Mapeia direto nos componentes existentes: a afirmação vai no `h2.title`; a prova vira o componente certo (infográfico, `statement`, `metric`, etc. — ver `infographics.md` e `layout-patterns.md`).

---

## 4. Família C — calibração por público (o "dial")

O **Expertise Reversal Effect** é a base científica: scaffolding (texto extra, passo a passo, exemplo resolvido) **ajuda o novato e ATRAPALHA o expert** (pro expert vira redundância que rouba memória de trabalho). Mesma matéria, tratamento oposto:

| Lever | Novato | Expert |
|:--|:--|:--|
| Analogia / metáfora | sim, abre com ela (Feynman) | dispensa, vai ao ponto |
| Exemplo trabalhado | passo a passo | só o resultado / caso-limite |
| Jargão | traduz na hora | usa direto (é vocabulário comum) |
| Densidade por slide | menos, mais respiro | mais densa, mais granular |
| O básico | explica | pula |
| Pré-requisito | ativa conhecimento prévio ("lembra de X?") | assume |

**Maldição do Conhecimento (Heath)**: quem é expert no tema esquece como é não saber. Ao montar pra novato, **descomprima de propósito** — o que é "óbvio" pra fonte não é pro público.

**Feynman** pra checar a explicação: se não dá pra explicar simples (analogia + exemplo concreto), o buraco é de entendimento — volte ao grounding.

**Progressivo** (quando o público é misto): abra no nível do novato e **aprofunde em camadas** — os primeiros slides acessíveis, os de detalhe/granular depois (o expert pula a abertura, o novato acompanha). Ver §Granularidade.

---

## 5. Família D — limites de processamento (quanto cabe)

- **CLT + Mayer (12 princípios multimídia)**: corte o supérfluo (coerência); destaque o essencial (sinalização — `.hl`); fatie em pedaços (segmentação → quebre slides densos); não narre e despeje o mesmo texto (redundância); rótulo **junto** do dado (contiguidade).
- **Miller / chunking**: a memória de trabalho segura ~4 chunks. **≤3–5 itens por slide.** Mais que isso, agrupe ou quebre.
- **Knaflic**: cada elemento é carga cognitiva. Cinza o contexto, cor só no ponto.

---

## 6. Família E — memória e impacto (o que gruda)

- **Superioridade da imagem (Medina)**: só ouvir/ler = ~10% de retenção em 3 dias; **com imagem relevante = ~65%**. Visualize tudo que dá (dual coding) — daí a biblioteca de infográficos.
- **Regra de 3** (Jobs/Gallo): agrupe em três.
- **STAR moment (Duarte)**: plante **um** "Something They'll Always Remember" — uma estatística chocante, um visual marcante, um contraste. Jobs chama de "holy smokes".
- **Atenção cai a cada ~10 min (Medina)**: num deck longo, plante um contraste/STAR periodicamente pra reengajar.

---

## 7. Granularidade — resumo e granular num deck linear (Shneiderman)

Sem JS/interação, "details on demand" vira **estrutura**: **overview primeiro → slides de detalhe → apêndice com o mais granular.**

- **Resumo-led** (executivo): a história inteira em overview; o granular fica no apêndice pra quem quiser.
- **Granular** (técnico): mais slides de detalhe na linha principal.
- **Os dois**: linha principal resumida + apêndice granular — um deck serve "me dá o panorama" e "me mostra os números".

A altitude é **proposta no intake** e confirmada.

---

## 8. Grounding — factual E atualizado, nunca só do modelo

O conteúdo do explicador é **reescrito/autorado** a partir de material real — então a regra de ouro da transcrição (texto literal) não se aplica, mas **uma trava equivalente sim**:

- **Ancore no material existente** (o que foi produzido) + **pesquise** pra ampliar o entorno e **manter atualizado** (a info não pode ser velha do treino do modelo).
- **Cite as fontes** — inline ou num apêndice; nos gráficos, no `.cap`.
- **Nunca afirme o que não está no material/fonte.** Todo número rastreia à origem (`scripts/check_provenance.py`, passo de verificação).
- Se só veio o tema (sem material), **a passada de grounding é obrigatória antes de autorar** — pesquisa real, depois escreve. Nunca solta da cabeça do modelo.
