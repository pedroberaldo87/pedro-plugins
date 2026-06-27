---
name: design-md
description: "Use quando o Pedro quer criar, editar ou validar um design system no formato DESIGN.md (o padrão aberto do Google — tokens de design em YAML + seções em markdown), ou exportar os tokens pra Tailwind/DTCG. Escreve o arquivo seguindo a spec, valida de verdade pelo CLI oficial @google/design.md via npx, e cai numa checagem manual pela spec quando o npx não está disponível. Trigger em /design-md, DESIGN.md, design system em markdown, design tokens, gera o DESIGN.md, valida o DESIGN.md, exporta os tokens pro Tailwind."
---

# design-md — Escrever, validar e exportar DESIGN.md

`DESIGN.md` é o formato aberto do Google pra representar um **design system em texto puro**: um arquivo auto-contido com **frontmatter YAML** (tokens de design — cores, tipografia, espaçamento, etc.) + um **corpo markdown** com as seções que explicam o racional. Os tokens são os valores normativos; a prosa dá o contexto de aplicação. É o mesmo arquivo que humano e agente leem e refinam entre sessões.

Esta skill **embrulha o CLI oficial** (`@google/design.md`) — não reimplementa o linter. Escreve o arquivo pela spec, valida pelo CLI, exporta os tokens. A spec completa está vendorada em **`${CLAUDE_PLUGIN_ROOT}/skills/design-md/references/spec.md`** — leia antes de escrever ou de validar manualmente.

## Quando usar
- Criar um `DESIGN.md` do zero pra um produto/marca.
- Editar/estender um `DESIGN.md` existente (novos tokens, nova seção, variante de componente).
- Validar um `DESIGN.md` (estrutura + contraste + refs).
- Exportar os tokens pra Tailwind (v3/v4) ou DTCG (W3C Design Tokens).

## Quando NÃO usar
- Gerar CSS/componentes finais de UI — DESIGN.md é a **fonte de tokens/diretrizes**, não o código da tela.
- Editar `tokens.json`/Figma direto — use o `export` pra derivar desses, não o contrário aqui.

## Pré-requisito (e o fallback)
O caminho titular usa o CLI via **npx** (precisa de `node`/`npx` no PATH). A versão é **pinada em `@0.3.0`** — a única testada; o formato é `alpha` e versões futuras podem mudar a sintaxe sem aviso:

```bash
npx --yes @google/design.md@0.3.0 <comando> ...
```

Se `node`/`npx` **não** existir no ambiente, NÃO trave: caia na **checagem manual pela spec** (`${CLAUDE_PLUGIN_ROOT}/skills/design-md/references/spec.md`) — valide as regras você mesmo (ordem de seções, `primary` presente, refs `{...}` resolvem, sem seção duplicada, contraste WCAG) e **avise explicitamente** que rodou em modo reserva (sem o linter oficial). O fallback é à altura: a spec vendorada tem as mesmas regras; só perde a checagem determinística de contraste.

## Fluxo

### 1. Escrever / editar o arquivo
Leia a spec (path acima) e siga a estrutura. Resumo operacional:

- **Duas partes:** frontmatter YAML (entre `---` … `---`) com os tokens + corpo markdown com as seções.
- **Seções (h2 `##`), nesta ordem**, omita as irrelevantes mas não reordene: **Overview** (ou "Brand & Style") · **Colors** · **Typography** · **Layout** · **Elevation & Depth** · **Shapes** · **Components** · **Do's and Don'ts**. Um `# h1` de título é opcional e não conta como seção. **Heading de seção duplicado** deveria ser erro pela spec — mas o lint v0.3.0 NÃO pega isso (confirmado por teste). **Cheque você mesmo:** nunca repita `## Colors`, `## Typography`, etc.
- **Tokens no frontmatter:** `name` (obrigatório), `version: alpha`, `description?`, e os grupos `colors` (mínimo `primary`), `typography`, `rounded`, `spacing`, `components`.
- **Referências entre tokens:** `"{colors.primary}"`, `"{rounded.md}"` — chaves apontam pra valores primitivos; em `components` pode referenciar composto (`{typography.label-md}`).
- **Cor:** qualquer CSS color válido (hex recomendado). **Dimension:** string com unidade `px`/`em`/`rem`.
- A prosa pode usar nomes descritivos ("Midnight Forest Green") que mapeiam pros tokens sistemáticos (`primary`). Nomes recomendados (não-normativos) estão no fim da spec.

Esqueleto mínimo válido:

```markdown
---
version: alpha
name: <Nome do Design System>
colors:
  primary: "#1A1C1E"
typography:
  body-md: { fontFamily: Public Sans, fontSize: 16px, fontWeight: 400, lineHeight: 1.6 }
---

## Overview
<personalidade da marca, público, sensação que a UI evoca>

## Colors
- **Primary (#1A1C1E):** <papel da cor>

## Typography
- **Body:** <família, peso, uso>

## Do's and Don'ts
- Do <regra>
- Don't <armadilha>
```

### 2. Validar (titular = CLI)
```bash
npx --yes @google/design.md@0.3.0 lint <arquivo> --format json
```
Use `-` no lugar do arquivo pra ler de stdin. **Na v0.3.0 só `--format json` produz saída estruturada** — `--format text` também devolve JSON (bug deles), então parseie o JSON.

Cada finding tem `severity` (`error` / `warning` / `info`) e o `summary` traz as contagens. Critério de "limpo": **`errors: 0` é obrigatório** (ref quebrada é error). **Warnings** (contraste abaixo de WCAG, seção fora de ordem, `primary` ausente, tokens órfãos) são **julgamento** — conserte ou justifique caso a caso; não são bloqueio absoluto. **Trabalhe a partir da saída real do lint — não presuma o formato.**

### 3. Exportar tokens (sob demanda)
```bash
npx --yes @google/design.md@0.3.0 export <arquivo> --format css-tailwind   # Tailwind v4 (@theme CSS)
npx --yes @google/design.md@0.3.0 export <arquivo> --format json-tailwind  # Tailwind v3 (theme.extend) — alias: tailwind
npx --yes @google/design.md@0.3.0 export <arquivo> --format dtcg           # W3C Design Tokens
```

### 4. Comparar versões (opcional)
```bash
npx --yes @google/design.md@0.3.0 diff <arquivo-antes> <arquivo-depois> --format json
```
Reporta `added` / `removed` / `modified` por grupo de token entre dois `DESIGN.md`.

## Notas de manutenção (honestas)
- **Versão pinada em `@0.3.0`** porque é a única que testei. Pra pegar correções futuras (ex: os bugs abaixo), rode com `@latest` e **re-teste** os comandos antes de confiar — não troque às cegas.
- **`design.md spec` está quebrado na v0.3.0** (`Failed to load spec.md` — o build não copia `docs/spec.md` pro pacote). Por isso a spec é **vendorada** em references/spec.md, não puxada do CLI. Quando o upstream consertar, dá pra trocar pra `npx @google/design.md spec`.
- **O que o lint v0.3.0 pega** (testado): ref quebrada (ERROR), contraste WCAG abaixo de 4.5:1 (WARNING), `primary` ausente, seção fora de ordem, tokens órfãos. **O que NÃO pega:** seção duplicada (contradiz a própria spec) — a checagem manual cobre.
- O formato é `alpha` — a seção Components é declaradamente instável upstream.
