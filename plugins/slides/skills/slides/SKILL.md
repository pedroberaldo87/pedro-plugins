---
name: slides
description: 'Transforma um arquivo markdown (outline de fala, notas, roteiro) numa apresentação HTML de slides — single-file, navegável por teclado, em linguagem keynote (tipografia grande, muito respiro, sem cara de dashboard), tema VIU Studio por padrão. REGRA DE OURO: usa o texto literal do .md, nunca inventa frases, callouts ou conclusões. Use sempre que Pedro pedir "/slides", "monta esse md numa apresentação", "transforma isso em slides", "faz um deck", "apresentação a partir desse markdown", "vira slides", ou apontar um .md e pedir pra apresentar — mesmo que não diga a palavra "slides". Suporta temas nomeados (sufixo): /slides arquivo.md [tema]. O deck é ADAPTATIVO num arquivo só: apresentação navegável no desktop e documento scroll (tudo na tela, sem depender de JavaScript) no celular e no thumbnail do WhatsApp. NÃO use para editar .pptx/Keynote existentes nem para gerar PDF.'
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

## Um arquivo, dois modos (desktop + mobile/WhatsApp)

O deck é **adaptativo por progressive enhancement** — o mesmo `.html` serve os dois sem gerar nada a mais:

- **Desktop (mouse + tela larga):** o JS ativa o modo apresentação — slide a slide, `← →`, `F`, swipe, reveals.
- **Celular / sem-JS / thumbnail do WhatsApp:** a página é um **documento scroll vertical** com todos os slides empilhados e visíveis. O conteúdo está no HTML estático; **nada depende do JS** pra aparecer.

Por que importa: Pedro manda o `.html` por WhatsApp, que gera o thumbnail renderizando o arquivo **sem garantir JS** — se o conteúdo dependesse de JS, o preview sairia preto. O template já resolve (estado base = documento). Seu único cuidado ao montar: **não reintroduzir dependência de JS no conteúdo** — todo texto/figura vai no markup do slide, nunca injetado por script.

Nota: isso é o thumbnail de **anexo** (renderiza o arquivo). É diferente do preview de **link** (Open Graph / `og:image`), que exigiria hospedar numa URL pública — fora do escopo. As tags `og:title`/`og:description` entram só de brinde.

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

## Referências
- `references/layout-patterns.md` — mapa tipo-de-conteúdo → componente, snippets de cada um, regras de composição. **Leia antes de montar os slides.**
- `references/themes/viu.md` — o tema canônico e o contrato de variáveis para criar temas novos.
- `assets/template.html` — engine (navegação, reveals, progress) + CSS dos componentes. Parametrizado só por `var()` do tema.
- `scripts/check_fidelity.py` — verificação anti-invenção.
