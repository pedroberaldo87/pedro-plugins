---
name: slides
description: 'Transforma um arquivo markdown (outline de fala, notas, roteiro) numa apresentação HTML de slides — single-file, navegável por teclado, em linguagem keynote (tipografia grande, muito respiro, sem cara de dashboard), tema VIU Studio por padrão. REGRA DE OURO: usa o texto literal do .md, nunca inventa frases, callouts ou conclusões. Use sempre que Pedro pedir "/slides", "monta esse md numa apresentação", "transforma isso em slides", "faz um deck", "apresentação a partir desse markdown", "vira slides", ou apontar um .md e pedir pra apresentar — mesmo que não diga a palavra "slides". Suporta temas nomeados (sufixo): /slides arquivo.md [tema]. NÃO use para editar .pptx/Keynote existentes nem para gerar PDF.'
---

# Slides — markdown → deck keynote

Converte um outline em markdown numa apresentação HTML que se abre no navegador e se apresenta em tela cheia. A engine e os componentes visuais já estão prontos em `assets/template.html`; seu trabalho é **mapear o conteúdo do autor para os componentes certos** sem distorcer o texto.

## A regra de ouro: o texto é do autor

Pedro reportou isso explicitamente e é o eixo da skill: **não invente texto.** O conteúdo dos slides sai literal do `.md`. Concretamente:

- **Corpo (listas, leads, callouts, parágrafos):** copie a frase do `.md` palavra por palavra. Não crie observações, fechamentos, "ganchos" ou reescritas "mais bonitas".
- **Títulos de slide:** podem encurtar/derivar de um heading do `.md` (ex: heading longo → título curto). Só os títulos têm essa licença — e ainda assim, fique o mais perto possível do original.
- **Correções permitidas:** ortografia/acentuação óbvia ("dia-a-dia"→"dia a dia"), typos claros ("Agentico"→"Agêntico", "10token/sec"→"10 tokens/seg", "Macbook Max M1"→"MacBook M1 Max"). Isso é correção, não invenção.
- Na dúvida entre encurtar e ser fiel, **seja fiel.** Se algo do `.md` está confuso e você acha que falta contexto, pergunte — não preencha por conta própria.

O script `scripts/check_fidelity.py` faz cumprir isso automaticamente (passo 5).

## Workflow

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
- Leia `assets/template.html`. Substitua os placeholders: `__TITLE__`, `__FONT_LINKS__`, `__THEME_CSS__`, `__BRAND__`, `__SLIDES__` (a sequência de `<section class="slide">`).
- Reveals escalonados em cada slide (`--d:40ms`, `120ms`, `240ms`...). Destaque palavras-chave do título com `<span class="hl">`.
- **Saída: ao lado do `.md` de origem** — mesmo diretório, mesmo nome-base + `.html`. (Se o `.md` está num caminho read-only/sync como iCloud e a escrita falhar, caia para `~/Desktop/<nome>.html` e avise.)

### 5. Verifique fidelidade (obrigatório)
```bash
python3 <skill>/scripts/check_fidelity.py <deck.html> <fonte.md>
```
Se sinalizar trechos: cada um é prosa que não existe na fonte. Troque pelo texto literal do `.md` ou remova o acréscimo. Re-rode até `✓`. Não entregue com fidelidade pendente.

### 6. Verifique o visual
- `file://` é bloqueado no Playwright. Sirva o diretório e abra via localhost:
  ```bash
  (cd <dir-do-deck> && python3 -m http.server 8899 >/dev/null 2>&1 &)
  ```
  Navegue `http://localhost:8899/<deck>.html`, pule para os slides mais densos (via `show(n)` no console / `browser_evaluate`) e tire screenshot. Confirme que cabem sem estourar e que o tema renderiza. Ajuste o que vazar. Encerre o server depois.
- Sem browser disponível: ao menos abra com `open <deck>.html` pro Pedro ver, e cheque o console por erros.

### 7. Entregue
- Informe o caminho do `.html`, total de slides, e os controles: **← / →** ou espaço (navegar), clique nas bordas, **F** (tela cheia).
- Sinalize qualquer micro-decisão de título/encurtamento que tenha tomado, pra Pedro validar.

## Referências
- `references/layout-patterns.md` — mapa tipo-de-conteúdo → componente, snippets de cada um, regras de composição. **Leia antes de montar os slides.**
- `references/themes/viu.md` — o tema canônico e o contrato de variáveis para criar temas novos.
- `assets/template.html` — engine (navegação, reveals, progress) + CSS dos componentes. Parametrizado só por `var()` do tema.
- `scripts/check_fidelity.py` — verificação anti-invenção.
