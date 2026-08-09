---
name: doc-load
description: "Carrega a documentação canônica do projeto e diz o que vale como RÉGUA — a lei (constituição, metas de qualidade, restrições), o que foi acordado com o dono (blueprint, funcionalidades, jornadas, desenho) e o mapa minerado, cada um com a marca do texto e o motivo de valer ou não. Substitui a instrução em prosa que estava copiada dentro de cada skill que julga alguma coisa. Roda no começo de TODA etapa que especifica, planeja, implementa, testa ou revisa — e logo depois dela roda a skill principles. Use quando o usuário disser /doc-load, 'carrega a doc', 'qual é a régua deste projeto', ou quando qualquer skill precisar julgar obra contra o que o projeto acordou."
---

# doc-load — a régua do projeto, carregada por programa

Toda skill que julga alguma coisa precisava saber a mesma coisa: **quais documentos deste
projeto valem como régua hoje, e quais são só mapa.** Até aqui essa resposta estava
escrita em prosa dentro de cada uma delas — *"leia `.claude/docs/constituicao.md` e
`quality-goals.md` do projeto onde a missão roda; se houver `blueprint.md` e `features.md`
com `status: approved`, entram na mesma régua; arquivo ausente não é achado"* — copiada
quatro vezes, com quatro redações diferentes.

Prosa copiada diverge no primeiro conserto, e a divergência é **silenciosa**: nenhum dos
lados fica errado sozinho (`patterns.md` §1.6a). Aqui a regra é uma, e é programa.

## O comando

```bash
python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/doc_load.py)" \
  --project-root "$PWD"
```

- `--json` devolve o estado inteiro, para quem vai processar em vez de ler.
- `--marca` imprime só a marca da régua — o número que uma missão longa congela na
  primeira volta para perceber a lei mudando no meio do caminho.

Fora deste repositório o resolvedor acha o programa pelo nome do plugin; dentro dele, o
caminho direto é `plugins/project-skills/lib/doc_load.py`.

## O que ele devolve, e o que cada parte significa

**VALE COMO RÉGUA** — julgue a obra contra estes, e **cite a passagem** que ela viola.
Duas naturezas, com exigências diferentes:

- **Lei** (`constituicao.md`, `quality-goals.md`, `constraints.md`) — vale com `ready`
  **ou** `approved`. Só rascunho fica de fora. A lei não passa pelo rito de aprovação
  porque ela não é uma etapa de concepção: é o contrato permanente do projeto.
- **Acordo** (`context.md`, `solution-strategy.md`, `glossary.md`,
  `architecture-intent.md`, `design.md`, `journeys.md`, `blueprint.md`, `features.md`) —
  **só** com `approved`. Medir obra contra rascunho reprova obra certa. E acordo cujo
  corpo mudou depois do de acordo sai como **reaberto**: a marca gravada não bate com o
  texto de hoje, então ninguém aprovou o que está lá.

**MAPA** — `architecture.md`, `patterns.md`, `data-stores.md`, `durability.md`,
`runtime.md`. Documento minerado do código: serve para **se situar**, nunca para
reprovar. Ele descreve o que existe, não o que deveria existir.

**AUSENTES** — dito em voz alta, e **ausência não é achado**. Projeto sem
`constituicao.md` não tem o eixo de constituição; isso não é violação de nada.

**DISPENSA** — `dispensa.md` com `motivo:` preenchido é a decisão declarada de viver sem a
fundação. Dispensa sem motivo escrito não vale: é ausência com um arquivo em cima.

**CORREÇÃO PENDENTE** — o `correcao-pendente:` que o dono gravou no frontmatter quando a
execução descobriu que a concepção errou. Enquanto ele estiver lá, aquele documento tem
uma dívida declarada, e quem julga precisa saber disso antes de medir.

## A marca, e por que ela é a mesma do shell

A marca de cada documento é o `cksum` POSIX do **corpo** — o frontmatter fica de fora,
porque ele carrega a própria marca e incluí-lo faria a marca mudar ao ser gravada.

É a **mesma receita** de `hooks/lib-doc-mark.sh`, reimplementada em Python para rodar onde
não há shell. Duas receitas dariam dois números para o mesmo texto, e aí a comparação
nunca fecharia — que é o defeito do §1.6a com outro nome. Confira quando desconfiar:

```bash
. plugins/project-skills/hooks/lib-doc-mark.sh
doc_marca .claude/docs/constituicao.md                       # o shell
python3 plugins/project-skills/lib/doc_load.py --marca       # o programa
```

## Onde isto roda — e o par obrigatório com `/principles`

**`/doc-load` roda no COMEÇO de toda etapa que especifica, planeja, implementa, testa ou
revisa. Logo depois dele, roda `/principles`.** Os dois juntos formam o preâmbulo, e a
ordem importa:

1. **`/doc-load`** — o que **ESTE** projeto acordou. Específico, e manda em conflito.
2. **`/principles`** — os princípios que valem em **QUALQUER** sistema, aplicados ao
   contexto de agora. Genérico, e nunca decide o que este sistema tem que ser.

Onde há conflito entre os dois, **ganha o `/doc-load`**: princípio genérico não revoga a
lei do projeto. A skill `principles` já diz isso de si mesma — *"Não decide o que ESTE
sistema tem que ser: isso é da constituição do projeto"* —, e este parágrafo é o outro
lado da mesma costura.

O modo do `/principles` muda com a etapa:

| Etapa | Preâmbulo |
|---|---|
| especificação · concepção | `/doc-load` → `/principles` |
| planejamento (o plano ticável) | `/doc-load` → `/principles` |
| implementação (a onda, o bloco) | `/doc-load` → `/principles` |
| teste · revisão · auditoria | `/doc-load` → `/principles review` |

**Por que no começo, e não quando der na telha:** julgar obra sem a régua carregada é
julgar contra a memória de quem julga. Foi assim que um revisor aprovou o que a
constituição proíbe — ele não tinha lido a constituição, e nada na receita dele o obrigava
a ler naquele momento.

## Fail-open, na direção honesta

- Projeto sem `.claude/docs/` → lista vazia, saída 0, e a frase que diz isso. Não é erro.
- Documento ilegível → fica fora da régua, e o motivo aparece. Nunca vira régua por
  omissão.
- O programa **não** escreve nada, em lugar nenhum. Ele lê.

## Suíte

```bash
python3 plugins/project-skills/lib/test_doc_load.py
```
