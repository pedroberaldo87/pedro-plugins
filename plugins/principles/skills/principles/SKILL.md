---
name: principles
description: "Princípios de sistema GENÉRICOS — os que valem em qualquer sistema — aplicados ao contexto atual. Lê PRINCIPIOS-SISTEMAS.md, mapeia categorias relevantes, e gera guia contextual com WHY + HOW. Dois modos — o padrão, que gera a seção de princípios antes de implementar, e review, que audita a implementação já escrita. Não decide o que ESTE sistema tem que ser: isso é da constituição do projeto. Trigger em /principles, princípios de sistema, checa os princípios."
---

# Princípios de Sistema

Conecta o documento de referência de princípios ao fluxo de trabalho. Em vez de esperar que princípios sejam lembrados, esta skill mapeia os relevantes ao contexto e gera orientação prática.

## Documento Fonte

Path: `${CLAUDE_PLUGIN_ROOT}/skills/principles/PRINCIPIOS-SISTEMAS.md`

Cópia canônica vive junto com a skill. Se o original no Obsidian for editado, copiar pra cá e atualizar o index.md.

## Modos

### Planning (default) — `/principles`

Gera uma seção "Princípios de Sistema" para incorporar ao plano.

**Processo:**

1. Ler `${CLAUDE_PLUGIN_ROOT}/skills/principles/index.md` (índice leve, ~150 linhas)
2. Analisar o contexto atual:
   - O que está sendo construído/modificado?
   - Que infraestrutura está envolvida? (filas, bancos, APIs, caches, etc.)
   - Qual a escala esperada?
   - Se o contexto não está claro, perguntar ao usuário em 1-2 frases
3. Cruzar com as categorias:
   - Percorrer os triggers de cada categoria no index.md
   - Selecionar 3-7 categorias onde o trigger bate com o contexto
   - Se menos de 3 batem, o task provavelmente não precisa de princípios de sistema — dizer explicitamente
4. Para cada categoria selecionada:
   - Ler a seção correspondente do documento fonte (grep para `## N ·` e ler a seção)
   - Escolher 2-5 princípios específicos diretamente relevantes
   - Para cada: 1 linha WHY (por que se aplica AQUI) + 1 linha HOW (como endereçar)
5. Gerar output no formato abaixo

**Formato de output (planning):**

```
## Princípios de Sistema

**Contexto analisado:** [1 linha descrevendo o que está sendo construído]

### [Nome da Categoria]
- **[Princípio]** — [Por que se aplica neste caso específico]
  - *Como:* [Direção concreta de como endereçar]

### [Outra Categoria]
- **[Princípio]** — [WHY]
  - *Como:* [HOW]

### N/A (descartados intencionalmente)
[Lista de categorias consideradas e por que não se aplicam aqui. 1 linha cada.]
```

**Regras do output:**
- Máximo 7 categorias. Se mais parecem relevantes, priorizar por impacto.
- Máximo 5 princípios por categoria. Nem todo princípio de uma categoria relevante se aplica.
- WHY antes de HOW. Cada entry começa com por que importa AQUI, não o que o princípio é.
- Sem teoria. O documento de referência já está à mão do usuário. Esta skill APLICA, não ensina.
- Seção N/A é obrigatória. Mostra o que foi considerado e descartado.
- Linguagem: mesmo idioma da conversa (geralmente pt-BR). Nomes de princípios no original.

### Review — `/principles review`

Audita implementação contra princípios identificados no plano.

**Processo:**

1. Ler `${CLAUDE_PLUGIN_ROOT}/skills/principles/index.md`
2. Encontrar a seção de princípios no plano atual:
   - Procurar em .claude/plans/*.md por seção "Princípios de Sistema"
   - Se não existe plano com princípios, fazer análise de contexto (mesmo processo do planning mode)
3. Analisar as mudanças de código:
   - `git diff HEAD` ou mudanças staged
   - Ler arquivos alterados
4. Para cada princípio identificado:
   - Verificar se a implementação honra o princípio
   - ✅ = implementado, com 1 linha confirmando o que endereça
   - ❌ = não implementado, com direção concreta do que falta
   - 〜 = parcial, com o que está feito e o que resta
5. Detectar princípios novos que não estavam no plano mas se aplicam ao código escrito
6. Gerar output no formato abaixo

**Formato de output (review):**

```
## Princípios — Review de Implementação

### Aderência ao plano

- ✅ **[Princípio]** — [O que no código endereça isso]. Ref: `arquivo:linha`
- ❌ **[Princípio]** — [O que falta]
  - *Fix:* [Direção concreta]
- 〜 **[Princípio]** — [O que está feito / o que resta]
  - *Fix:* [Direção concreta pro que resta]

### Princípios novos detectados (fora do plano)

- **[Princípio]** — [Por que se aplica ao código escrito]
  - *Fix:* [Direção]

### Veredicto

[N de M princípios atendidos. K parciais. J pendentes. Recomendação.]
```

**Regras do review:**
- Referenciar arquivos e linhas concretas quando flaggear violações
- Review mode é advisory — advisa, não bloqueia. Quem decide é o usuário
- Se o veredicto tem ❌ em princípios críticos, recomendar resolver antes de ship

## Fronteira com a constituição do projeto

Duas coisas parecidas que não se substituem:

- **Esta skill audita contra princípios GENÉRICOS** — os de `PRINCIPIOS-SISTEMAS.md`, que valem em
  qualquer sistema e não conhecem este projeto. Saída dela é conselho.
- **`.claude/docs/constituicao.md` manda no que ESTE sistema tem que ser** — os artigos que o dono
  enunciou, cada um com quem cobra. Saída dela é lei, e quem a escreve é `/start-doc constituicao`.

Em conflito, a constituição ganha. Esta skill nunca dá veredito sobre artigo da constituição e nunca
escreve artigo novo: princípio genérico que contradiz um artigo vira contradição RELATADA ao dono —
quem muda a lei é ele.

## Quando NÃO usar

- UI/frontend puro sem backend, persistência, ou rede — princípios de design de software (cat 10) podem aplicar, mas os de sistema não
- Mudanças só de documentação
- Refactoring que não muda comportamento ou boundaries
- Quando o usuário diz "skip principles" ou "sem princípios" — respeitar o override

## Integração

### Com writing-plans
Quando invocado durante planejamento, o output vira seção do plano. Não duplicar — se o plano já tem "Princípios de Sistema", atualizar em vez de criar segunda seção.

### Com ship
Quando invocado como `/principles review` antes do ship, o output é pre-flight check.

### Standalone
Funciona independente de outras skills. Sem acoplamento. Pode ser invocado a qualquer momento.

## Manutenção

Quando PRINCIPIOS-SISTEMAS.md for atualizado (novas categorias, novos princípios):
1. Copiar a versão atualizada do Obsidian pra cá
2. Atualizar index.md com categorias novas, triggers, e lista de princípios
