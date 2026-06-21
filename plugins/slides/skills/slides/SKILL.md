---
name: slides
description: 'Gera uma apresentação HTML de slides — single-file, navegável por teclado, em linguagem keynote (tipografia grande, muito respiro, sem cara de dashboard), tema VIU Studio por padrão. Tem DOIS modos. (A) TRANSCRIÇÃO: renderiza fiel um .md já redigido — REGRA DE OURO: usa o texto literal, nunca inventa frases, callouts ou conclusões. (B) EXPLICADOR: quando pedem um deck pra ENSINAR/explicar um conceito, a própria skill dirige a didática (estrutura narrativa, nível do público, granular vs resumo, infográficos), com grounding factual e atualizado, nunca da cabeça do modelo. Use sempre que Pedro pedir "/slides", "monta esse md numa apresentação", "transforma isso em slides", "faz um deck", "vira slides", ou apontar um .md e pedir pra apresentar (→ transcrição); ou "monta um deck pra me explicar X", "explica X em slides", "cria um deck didático sobre Y", "me ensina Z em slides" (→ explicador) — mesmo sem dizer a palavra "slides". Suporta temas nomeados (sufixo): /slides arquivo.md [tema]. O deck é ADAPTATIVO num arquivo só: apresentação navegável no desktop e documento scroll (tudo na tela, sem depender de JavaScript) no celular e no thumbnail do WhatsApp. NÃO use para editar .pptx/Keynote existentes nem para gerar PDF.'
---

# Slides — deck keynote (transcrição ou explicador)

Gera uma apresentação HTML que abre no navegador e se apresenta em tela cheia. A engine, os componentes visuais e os infográficos já estão prontos em `assets/template.html`. A skill tem **dois modos**, com contratos de conteúdo opostos — decida qual ANTES de tudo.

## Dois modos de uso (despacho)

| O pedido é... | Modo | O que a skill faz |
|:--|:--|:--|
| apontar um `.md` já redigido e pedir pra "virar slides / apresentação / deck" | **A · Transcrição** | renderiza **fiel**, sem inventar texto (regra de ouro). É o **Workflow A** abaixo. |
| "monta um deck pra me **explicar** X" / "me ensina Y em slides" / dar um tema ou material e pedir pra ENSINAR | **B · Explicador** | **autora a didática** — estrutura, nível do público, granular vs resumo, infográficos — com grounding. É o **Workflow B** abaixo. |
| ambíguo (aponta um `.md` **e** pede pra "explicar/ensinar") | — | **pergunte** qual modo antes de montar. Não chute. |

Os dois compartilham a mesma engine/template/temas e o mesmo cuidado de não-regressão (no-JS, thumbnail WhatsApp, 4 cenários de verificação).

## A regra de ouro (modo A · transcrição): o texto é do autor

Pedro reportou isso explicitamente e é o eixo da skill: **não invente texto.** O conteúdo dos slides sai literal do `.md`. Concretamente:

- **Corpo (listas, leads, callouts, parágrafos):** copie a frase do `.md` palavra por palavra. Não crie observações, fechamentos, "ganchos" ou reescritas "mais bonitas".
- **Títulos de slide:** podem encurtar/derivar de um heading do `.md` (ex: heading longo → título curto). Só os títulos têm essa licença — e ainda assim, fique o mais perto possível do original.
- **Correções permitidas:** ortografia/acentuação óbvia ("dia-a-dia"→"dia a dia"), typos claros ("Agentico"→"Agêntico", "10token/sec"→"10 tokens/seg", "Macbook Max M1"→"MacBook M1 Max"). Isso é correção, não invenção.
- Na dúvida entre encurtar e ser fiel, **seja fiel.** Se algo do `.md` está confuso e você acha que falta contexto, pergunte — não preencha por conta própria.

O script `scripts/check_fidelity.py` faz cumprir isso automaticamente (passo 5).

## Um arquivo, duas formas de abrir (desktop + mobile/WhatsApp)

Vale para os dois modos de uso. O deck é **adaptativo por progressive enhancement** — o mesmo `.html` serve os dois sem gerar nada a mais:

- **Desktop (mouse + tela larga):** o JS ativa o modo apresentação — slide a slide, `← →`, `F`, swipe, reveals.
- **Celular / sem-JS / thumbnail do WhatsApp:** a página é um **documento scroll vertical** com todos os slides empilhados e visíveis. O conteúdo está no HTML estático; **nada depende do JS** pra aparecer.

Por que importa: Pedro manda o `.html` por WhatsApp, que gera o thumbnail renderizando o arquivo **sem garantir JS** — se o conteúdo dependesse de JS, o preview sairia preto. O template já resolve (estado base = documento). Seu único cuidado ao montar: **não reintroduzir dependência de JS no conteúdo** — todo texto/figura vai no markup do slide, nunca injetado por script.

Nota: isso é o thumbnail de **anexo** (renderiza o arquivo). É diferente do preview de **link** (Open Graph / `og:image`), que exigiria hospedar numa URL pública — fora do escopo. As tags `og:title`/`og:description` entram só de brinde.

## Workflow A — transcrição (o `.md` já está pronto)

### 1. Leia a fonte e escolha o tema
- Leia o `.md` inteiro. Entenda a estrutura de headings (`#`, `##`, `###`) e bullets — é o esqueleto do deck.
- Tema: padrão **viu**. Se Pedro passar um sufixo (`/slides arquivo.md <tema>`), use esse. Leia `references/themes/<tema>.md` para pegar `__FONT_LINKS__`, `__THEME_CSS__` e `__BRAND__`. Se o tema pedido não existir, diga e ofereça criar (a partir de `references/themes/viu.md`).

### 2. Mapeie estrutura → slides
- Cada `#` (fase/seção top-level) vira um **section divider** (`01`, `02`...). Cada `##`/`###` vira um slide de conteúdo (ou um divider, se for um marco sem bullets).
- Para cada slide, escolha o componente pelo **tipo de conteúdo**, consultando `references/layout-patterns.md` (tem o mapa tipo→componente e os snippets). Não decore por aparência — leia o conteúdo e pergunte "isso é uma progressão? um índice? categorias? um número que pula?".
- O eyebrow de cada slide carrega a navegação mental: `Seção · Subseção` (texto derivado dos headings).

### 3. Densidade — respiro acima de tudo
- Um slide = uma ideia. Se uma seção tem muitos bullets, **quebre em vários slides** em vez de espremer. O alvo é 1440×900 sem rolagem.
- Número de slides acompanha o número de seções/sub-seções do `.md`. Não comprima a fala para "caber em N slides".

### 4. Monte o HTML
- Leia `assets/template.html`. Substitua os placeholders: `__TITLE__`, `__OG_DESC__` (1 frase derivada do subtítulo da capa, p/ preview de link), `__THEME_COLOR__` (do tema, = `--bg-body`), `__FONT_LINKS__`, `__THEME_CSS__`, `__BRAND__`, `__SLIDES__` (a sequência de `<section class="slide">`).
- Reveals escalonados em cada slide (`--d:40ms`, `120ms`, `240ms`...). Destaque palavras-chave do título com `<span class="hl">`.
- **Saída: ao lado do `.md` de origem** — mesmo diretório, mesmo nome-base + `.html`. (Se o `.md` está num caminho read-only/sync como iCloud e a escrita falhar, caia para `~/Desktop/<nome>.html` e avise.)

### 5. Verifique fidelidade (obrigatório)
```bash
python3 <skill>/scripts/check_fidelity.py <deck.html> <fonte.md>
```
Se sinalizar trechos: cada um é prosa que não existe na fonte. Troque pelo texto literal do `.md` ou remova o acréscimo. Re-rode até `✓`. Não entregue com fidelidade pendente.

### 6. Verifique o visual — os 4 cenários (reproduza e OLHE o print)
Não basta inspecionar o DOM: tire screenshot e analise se está coerente com o esperado.

1. **Thumbnail do WhatsApp (sem JS):** reproduza com a engine WebKit do macOS —
   ```bash
   qlmanage -t -s 1200 -o /tmp "<deck>.html" && open "/tmp/<deck>.png"
   ```
   A **capa** tem que aparecer (não pode sair preto/vazio). É exatamente o que o WhatsApp mostra no anexo.
2. **Mobile:** Playwright a **390×844** → scroll vertical legível, **zero overflow horizontal**, fonte ok (fallback de sistema cobre sem internet).
3. **Desktop:** Playwright a **1440** → deck navegável `← → / F` intacto (não regrediu).
4. **Sem-JS desktop:** abra com JS desabilitado → slides empilham como documento.

`file://` é bloqueado no Playwright. Sirva o diretório e use localhost:
```bash
(cd <dir-do-deck> && python3 -m http.server 8899 >/dev/null 2>&1 &)
```
Navegue `http://localhost:8899/<deck>.html`, pule pros slides mais densos e confira cabimento nos dois modos. Encerre o server depois. Sem browser: ao menos rode o `qlmanage` (cenário 1) + `open <deck>.html`.

### 7. Entregue
- Informe o caminho do `.html`, total de slides, e os controles do desktop: **← / →** ou espaço (navegar), clique nas bordas, **F** (tela cheia).
- Lembre que o **mesmo arquivo** pode ser enviado por WhatsApp / aberto no celular — lá ele vira documento scroll automaticamente, sem JS.
- Sinalize qualquer micro-decisão de título/encurtamento que tenha tomado, pra Pedro validar.

## Workflow B — explicador (você vai ENSINAR um conceito)

O conteúdo aqui é **autorado**, não transcrito — a regra de ouro (texto literal) **não vale**; vale a **trava de grounding**. Leia `references/explainer-method.md` (a didática) e `references/infographics.md` (a viz) **antes de montar**.

### 1. Intake — pergunte só o que não veio
Resolva: **público & nível**, **profundidade** (um nível vs progressivo), **altitude do dado** (resumo/granular), e **o trabalho do deck** (ensinar / defender mudança / apresentar análise). Use o que está explícito no pedido; **pergunte o que faltar** antes de montar.

### 2. Grounding — factual E atualizado
Ancore no material fornecido + **pesquise** pra ampliar o entorno e **atualizar** (nada de info velha do treino). Cite as fontes. **Nunca afirme o que não está no material/fonte.** Se só veio o tema (sem material), a pesquisa é **obrigatória** antes de autorar — nunca solte da cabeça do modelo.

### 3. Proponha a abordagem e confirme
Escolha, pelo `explainer-method.md`: a **arquitetura narrativa** (família A), o slide didático (**Assertion-Evidence**, B), a **calibração pro público** (dial C), e a **granularidade**. **Apresente a abordagem comparada com 1–2 alternativas (prós/contras)** e **confirme** antes de montar. Não escolha a didática calada.

### 4. Monte o HTML
Mesma engine do Workflow A (ver passo 4 acima): leia `assets/template.html`, substitua os placeholders, mapeie cada slide pro componente certo. Aqui os **infográficos entram em peso** — escolha pelo `infographics.md` (mensagem→gráfico / pergunta→diagrama). **Título = a afirmação; o gráfico/visual = a prova.** Saída ao lado da fonte (ou Desktop se read-only).

### 5. Verifique o grounding (obrigatório)
```bash
python3 <skill>/scripts/check_provenance.py <deck.html> <fonte1> [fonte2 ...]
```
Cobra que **todo número** dos gráficos/métricas exista no material/fonte. Barra inventada é pior que prosa inventada. Re-rode até `✓`.

### 6. Verifique o visual — os 4 cenários (reproduza e OLHE o print)
Igual ao Workflow A (passo 6). Além disso, garanta que os infográficos **aparecem no HTML estático** (no-JS), são **keynote-limpos** (passam nas leis de Cairo/Tufte — sem nenhum tell de dashboard do `infographics.md`), e **cabem** em 1440×900.

### 7. Entregue
Caminho do `.html`, total de slides, controles do desktop, e o lembrete do modo documento no celular. Sinalize a **abordagem escolhida** (arquitetura · nível · altitude) e as **fontes citadas**.

## Referências
- `references/layout-patterns.md` — mapa tipo-de-conteúdo → componente, snippets. **Leia antes de montar (os dois modos).**
- `references/explainer-method.md` — **modo B:** a didática (arquitetura narrativa, Assertion-Evidence, dial novato↔expert, limites, granularidade, grounding). Menu de prós/contras pra propor-e-confirmar.
- `references/infographics.md` — **modo B:** o ofício de viz (fronteira Cairo, leis de craft, tells proibidos, mapas FT/Roam, snippets de cada infográfico).
- `references/themes/viu.md` — o tema canônico e o contrato de variáveis para criar temas novos.
- `assets/template.html` — engine (navegação, reveals, progress) + CSS dos componentes **e dos infográficos**. Parametrizado só por `var()` do tema.
- `scripts/check_fidelity.py` — **modo A:** verificação anti-invenção (texto literal).
- `scripts/check_provenance.py` — **modo B:** verificação de proveniência numérica (todo número rastreia à fonte).
