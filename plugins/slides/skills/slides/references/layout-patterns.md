# Padrões de layout — keynote, não dashboard

A diferença entre "slide bonito" e "tela de app": slide usa **tipografia grande, muito respiro, separação por filetes e espaço** — nunca caixas com fundo/borda, chips, ou grids densos. Cor é acento pontual, não preenchimento. Escolha o componente pelo **tipo de conteúdo**, não pela aparência.

Cada slide é uma `<section class="slide">` com um `<div class="inner">` dentro. Entrada animada: adicione `class="reveal"` e `style="--d:NNNms"` (escalonado: 40, 120, 240, 360, 480...) aos blocos para revelar em cascata.

Destaque de palavra no título: envolva com `<span class="hl">palavra</span>` (gradiente azul→violeta). Não muda o texto, só pinta.

---

## Mapa: tipo de conteúdo → componente

| O conteúdo é... | Use | Por quê |
|:--|:--|:--|
| Abertura de uma seção/fase | **section divider** | Número gigante + título = marco visual de virada |
| Lista de passos/itens recorrentes (3-6) | **numlist** | Números grandes dão ritmo e leitura vertical |
| Conjunto de categorias/conceitos paralelos (2-3) | **cols** | Filete vertical separa sem encaixotar |
| Índice de tópicos com exemplos (4-8) | **idx** | Linhas horizontais = sumário de revista |
| Progressão/escada (Prompt→Skill→...) | **steps** | Números + setas mostram evolução |
| Frase de impacto ou negação ("X não existe mais") | **statement** | Tipografia enorme; `.strike` risca em vermelho |
| Um número que pula (10→40, 3x, 80%) | **metric** | Número-herói domina o slide |
| Itens com status (cancelado/ativo) | **saas** | Nome grande + status à direita, com strike |
| 2-3 destaques curtos com ícone | **feats** | Glyph grande sem caixa + título + 1 linha |
| Capa / fechamento | **cover** | Título gigante + índice/marca |
| Reforço/observação do autor | **pull** | Barra colorida à esquerda, sem caixa |

Um slide normalmente usa **um** componente principal. Misturar 3+ vira poluição.

---

## Snippets

### Section divider
```html
<section class="slide"><div class="inner">
    <div class="section-num reveal" style="--d:40ms">01</div>
    <div class="eyebrow reveal" style="--d:130ms"><span class="ln"></span> Fase 1</div>
    <h2 class="title reveal" style="--d:210ms">Título da <span class="hl">fase</span></h2>
</div></section>
```
Variante violeta do eyebrow: `class="eyebrow v"`.

### numlist
```html
<ul class="numlist reveal" style="--d:240ms">
    <li><span class="nn">01</span><span class="tx">Texto do item <small>(sub-detalhe opcional)</small></span></li>
    <li><span class="nn">02</span><span class="tx">Outro item</span></li>
</ul>
```

### cols (categorias / conceitos)
```html
<div class="cols mt"><!-- .cols.c2 para 2 colunas -->
    <div class="col reveal" style="--d:240ms;--cc:var(--primary-soft)">
        <div class="topbar"></div>
        <span class="tag">Rótulo</span>
        <h3>Subtítulo</h3>            <!-- opcional -->
        <ul style="margin-top:16px"><li>Item</li><li>Item</li></ul>
        <div class="ex">Ex: nota de rodapé da coluna.</div>   <!-- opcional -->
    </div>
    <!-- repita; alterne --cc: var(--primary-soft), var(--success), var(--accent-soft) -->
</div>
```

### idx (índice de tópicos)
```html
<div class="idx reveal" style="--d:240ms">
    <div class="row"><span class="n">01</span><span class="name">Tópico</span><span class="ex"><b>destaque</b> &nbsp;|&nbsp; contexto secundário</span></div>
    <!-- repita -->
</div>
```

### steps (progressão)
```html
<div class="steps reveal" style="--d:260ms">
    <div class="st"><div class="num">01</div><h4>Etapa</h4><p>nota</p></div>
    <div class="sep"><i class="fa-solid fa-angle-right"></i></div>
    <div class="st peak"><div class="num">04</div><h4>Final</h4></div>  <!-- .peak destaca o último -->
</div>
```

### statement (frase de impacto)
```html
<div class="statement reveal" style="--d:280ms">
    Frase forte <span style="color:var(--accent-soft)">aqui.</span>
</div>
<!-- negação/obsolescência: <span class="strike">não existe mais</span> -->
```

### metric (número-herói)
```html
<div class="metric reveal" style="--d:240ms">
    <span class="from">10</span>
    <span class="arr"><i class="fa-solid fa-arrow-right-long"></i></span>
    <span class="to">40+</span>
    <span class="unit">unidade · contexto</span>
</div>
```

### saas (lista com status)
```html
<div class="saas reveal" style="--d:240ms">
    <div class="s done"><span class="nm">Nome</span><span class="stt">cancelado</span></div>
    <div class="s next"><span class="nm">Nome</span><span class="stt">a fazer</span></div>
</div>
```

### feats (destaques com glyph)
```html
<div class="feats f2 mt"><!-- f2 ou f3 -->
    <div class="feat reveal" style="--d:260ms">
        <i class="fa-solid fa-water gi"></i>   <!-- .gi.v violeta, .gi.g verde, .gi.a âmbar -->
        <h3>Título</h3>
        <p>Uma linha de apoio.</p>   <!-- opcional -->
    </div>
</div>
```

### pull (observação)
```html
<div class="pull reveal" style="--d:420ms"><b>Destaque:</b> texto da observação.</div>
<!-- .pull.v para barra violeta; <span class="small">nota menor</span> -->
```

### cover (capa / fechamento)
```html
<section class="slide cover"><div class="inner">
    <div class="kicker reveal" style="--d:60ms"><span class="d"></span> Eyebrow</div>
    <h1 class="reveal" style="--d:150ms">Linha 1<br><span class="glass-text">Linha 2</span></h1>
    <div class="kvs reveal" style="--d:320ms"><!-- índice vertical
        <span class="kv"><span class="kn">Fase 1</span> Texto</span> -->
    </div>
</div></section>
```
Ícones inline na capa (fechamento): `<div class="kvs row3">` com `<span class="kv"><i class="fa-solid fa-circle"></i> Label</span>`.

---

## Regras de composição

- **Densidade:** se um slide tem mais de ~6 itens ou o texto não cabe sem rolar em 1440×900, **quebre em dois slides**. Respiro > completude.
- **Ícones FontAwesome 6** (`fa-solid`) são decorativos — escolha o que o conteúdo evoca. Nunca os coloque em quadradinhos com fundo.
- **Eyebrow** carrega a navegação mental: `Fase N · Subseção`. Mantém o público localizado.
- **Reveals** sempre escalonados de cima pra baixo. O primeiro bloco em ~40ms, cada seguinte +80–120ms.
