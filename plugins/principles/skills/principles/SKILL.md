---
name: principles
description: "Princ\xEDpios de sistema contextuais para planejamento e review. L\xEA PRINCIPIOS SISTEMAS.md, mapeia categorias relevantes ao contexto atual, e gera guia contextual com WHY + HOW. Dois modos — planning (gera se\xE7\xE3o pro plano) e review (audita implementa\xE7\xE3o). Trigger em \"/principles\", \"princ\xEDpios de sistema\", \"checa os princ\xEDpios\"."
---

# Princ\xEDpios de Sistema

Conecta o documento de refer\xEAncia de princ\xEDpios ao fluxo de trabalho. Em vez de esperar que princ\xEDpios sejam lembrados, esta skill mapeia os relevantes ao contexto e gera orienta\xE7\xE3o pr\xE1tica.

## Documento Fonte

Path: `/Users/pedroberaldo/Library/Mobile Documents/iCloud~md~obsidian/Documents/ObsidianPedro/DEV/PRINCIPIOS SISTEMAS.md`

Este path cont\xE9m espa\xE7os. No Bash, sempre usar aspas duplas. No Read tool, passar o path como est\xE1.

## Modos

### Planning (default) — `/principles`

Gera uma se\xE7\xE3o "Princ\xEDpios de Sistema" para incorporar ao plano.

**Processo:**

1. Ler `${CLAUDE_PLUGIN_ROOT}/skills/principles/index.md` (\xEDndice leve, ~150 linhas)
2. Analisar o contexto atual:
   - O que est\xE1 sendo constru\xEDdo/modificado?
   - Que infraestrutura est\xE1 envolvida? (filas, bancos, APIs, caches, etc.)
   - Qual a escala esperada?
   - Se o contexto n\xE3o est\xE1 claro, perguntar ao Pedro em 1-2 frases
3. Cruzar com as categorias:
   - Percorrer os triggers de cada categoria no index.md
   - Selecionar 3-7 categorias onde o trigger bate com o contexto
   - Se menos de 3 batem, o task provavelmente n\xE3o precisa de princ\xEDpios de sistema — dizer explicitamente
4. Para cada categoria selecionada:
   - Ler a se\xE7\xE3o correspondente do documento fonte (usar Read com offset/limit baseado nos line ranges do index.md)
   - Escolher 2-5 princ\xEDpios espec\xEDficos diretamente relevantes
   - Para cada: 1 linha WHY (por que se aplica AQUI) + 1 linha HOW (como endere\xE7ar)
5. Gerar output no formato abaixo

**Formato de output (planning):**

```
## Princ\xEDpios de Sistema

**Contexto analisado:** [1 linha descrevendo o que est\xE1 sendo constru\xEDdo]

### [Nome da Categoria]
- **[Princ\xEDpio]** — [Por que se aplica neste caso espec\xEDfico]
  - *Como:* [Dire\xE7\xE3o concreta de como endere\xE7ar]

### [Outra Categoria]
- **[Princ\xEDpio]** — [WHY]
  - *Como:* [HOW]

### N/A (descartados intencionalmente)
[Lista de categorias consideradas e por que n\xE3o se aplicam aqui. 1 linha cada.]
```

**Regras do output:**
- M\xE1ximo 7 categorias. Se mais parecem relevantes, priorizar por impacto.
- M\xE1ximo 5 princ\xEDpios por categoria. Nem todo princ\xEDpio de uma categoria relevante se aplica.
- WHY antes de HOW. Cada entry come\xE7a com por que importa AQUI, n\xE3o o que o princ\xEDpio \xE9.
- Sem teoria. Pedro tem o documento de refer\xEAncia. Esta skill APLICA, n\xE3o ensina.
- Se\xE7\xE3o N/A \xE9 obrigat\xF3ria. Mostra o que foi considerado e descartado.
- Linguagem: mesmo idioma da conversa (geralmente pt-BR). Nomes de princ\xEDpios no original.

### Review — `/principles review`

Audita implementa\xE7\xE3o contra princ\xEDpios identificados no plano.

**Processo:**

1. Ler `${CLAUDE_PLUGIN_ROOT}/skills/principles/index.md`
2. Encontrar a se\xE7\xE3o de princ\xEDpios no plano atual:
   - Procurar em .claude/plans/*.md por se\xE7\xE3o "Princ\xEDpios de Sistema"
   - Se n\xE3o existe plano com princ\xEDpios, fazer an\xE1lise de contexto (mesmo processo do planning mode)
3. Analisar as mudan\xE7as de c\xF3digo:
   - `git diff HEAD` ou mudan\xE7as staged
   - Ler arquivos alterados
4. Para cada princ\xEDpio identificado:
   - Verificar se a implementa\xE7\xE3o honra o princ\xEDpio
   - ✅ = implementado, com 1 linha confirmando o que endere\xE7a
   - ❌ = n\xE3o implementado, com dire\xE7\xE3o concreta do que falta
   - 〜 = parcial, com o que est\xE1 feito e o que resta
5. Detectar princ\xEDpios novos que n\xE3o estavam no plano mas se aplicam ao c\xF3digo escrito
6. Gerar output no formato abaixo

**Formato de output (review):**

```
## Princ\xEDpios — Review de Implementa\xE7\xE3o

### Ader\xEAncia ao plano

- ✅ **[Princ\xEDpio]** — [O que no c\xF3digo endere\xE7a isso]. Ref: `arquivo:linha`
- ❌ **[Princ\xEDpio]** — [O que falta]
  - *Fix:* [Dire\xE7\xE3o concreta]
- 〜 **[Princ\xEDpio]** — [O que est\xE1 feito / o que resta]
  - *Fix:* [Dire\xE7\xE3o concreta pro que resta]

### Princ\xEDpios novos detectados (fora do plano)

- **[Princ\xEDpio]** — [Por que se aplica ao c\xF3digo escrito]
  - *Fix:* [Dire\xE7\xE3o]

### Veredicto

[N de M princ\xEDpios atendidos. K parciais. J pendentes. Recomenda\xE7\xE3o.]
```

**Regras do review:**
- Referenciar arquivos e linhas concretas quando flaggear viola\xE7\xF5es
- Review mode \xE9 advisory — advisa, n\xE3o bloqueia. Pedro decide
- Se o veredicto tem ❌ em princ\xEDpios cr\xEDticos, recomendar resolver antes de ship

## Quando N\xC3O usar

- UI/frontend puro sem backend, persist\xEAncia, ou rede — princ\xEDpios de design de software (cat 10) podem aplicar, mas os de sistema n\xE3o
- Mudan\xE7as s\xF3 de documenta\xE7\xE3o
- Refactoring que n\xE3o muda comportamento ou boundaries
- Quando Pedro diz "skip principles" ou "sem princ\xEDpios" — respeitar o override

## Integra\xE7\xE3o

### Com writing-plans
Quando invocado durante planejamento, o output vira se\xE7\xE3o do plano. N\xE3o duplicar — se o plano j\xE1 tem "Princ\xEDpios de Sistema", atualizar em vez de criar segunda se\xE7\xE3o.

### Com ship
Quando invocado como `/principles review` antes do ship, o output \xE9 pre-flight check.

### Standalone
Funciona independente de outras skills. Sem acoplamento. Pode ser invocado a qualquer momento.

## Manuten\xE7\xE3o

Quando PRINCIPIOS SISTEMAS.md for atualizado (novas categorias, novos princ\xEDpios):
1. Atualizar index.md com categorias novas, triggers, e lista de princ\xEDpios
2. Verifica\xE7\xE3o r\xE1pida: ler cada se\xE7\xE3o usando os ranges do index e confirmar que o conte\xFAdo correto carrega
