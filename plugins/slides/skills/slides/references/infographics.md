# Infográficos — editorial, nunca dashboard

Esta referência é do **modo explicador**. Ela governa como o dado e os conceitos viram visual sem cair em dashboard. Todos os componentes renderizam em **HTML estático (SVG/CSS, zero JS)** — aparecem no thumbnail do WhatsApp e no modo documento.

---

## A fronteira: infográfico ≠ dashboard (Alberto Cairo)

A diferença não é "tem gráfico ou não". É de **propósito**:

- **Infográfico** = o comunicador **autora** a história. Seleciona o dado, sequencia, usa hierarquia pra levar o leitor a **UMA conclusão**. Estático, com ponto de vista.
- **Dashboard / information-visualization** = **ferramenta de exploração**. Muitas métricas de uma vez, filtro, interação — pro leitor achar as próprias histórias.

**Uma apresentação é sempre infográfico.** Se você se pegar montando uma grade de métricas pra alguém "monitorar", parou: isso é dashboard, não apresentação.

## As 3 leis (toda viz obedece)

1. **Um slide, um gráfico, uma ideia.** O título do slide **afirma a conclusão** (Assertion-Evidence); o gráfico é a **evidência**, não um enigma. Nunca empilhe 2+ gráficos num slide.
2. **Data-ink máximo (Tufte) + foco (Knaflic).** Apague tudo que não é dado. **Cinza o contexto, cor só no que importa** — use `.hl` no único item que carrega o ponto; o resto fica `var(--text-dim)`/`var(--hair)`. Eixo é filete (`.axis`) ou nada. Rótulo **direto no dado**, nunca legenda separada pra caçar.
3. **Sem moldura.** O gráfico flutua no respiro como os outros componentes — nunca dentro de card/caixa/borda/fundo. (A classe `.fig` não desenha caixa de propósito.)

## Proibido — os "tells" de dashboard

- Grade de cartõezinhos de métrica (KPI tiles) · caixa/borda/fundo atrás do gráfico · chips/badges
- Legenda separada quando dá pra rotular no dado · gridline pesada · eixo carregado
- Paleta arco-íris (cor vira decoração, não foco) · 3D · sombra · gradiente de preenchimento que não significa nada
- Pizza com muitas fatias · mais de um gráfico por slide

---

## Mapa 1 — dado quantitativo: a MENSAGEM escolhe o gráfico (FT Visual Vocabulary)

Pergunte "qual relação no dado é a mais importante pra história?" e escolha pela linha:

| A mensagem é... | Família FT | Componente |
|:--|:--|:--|
| Comparar/ordenar itens (quem é maior) | Ranking / Magnitude | **bars**, **lollipop** (enxuto), **pairbars** (2 séries) |
| Comparar categorias ou ao longo do tempo (poucos pontos) | Magnitude / Mudança | **colchart** |
| Tendência ao longo do tempo (muitos pontos) | Mudança no tempo | **trend** (SVG) |
| Comparar 2 estados ponta a ponta (antes→depois por item) | Ranking / Mudança | **slope** (SVG) |
| Como um todo se divide | Parte-do-todo | **part** (barra), **donut** (parcimônia), **waffle** (isotype) |
| Como o total é construído/reduzido (entra/sai) | Parte-do-todo cumulativo | **waterfall** |
| Desvio acima/abaixo de uma base (meta, zero, média) | Desvio | **diverge** |
| Distribuição / amplitude de valores | Distribuição | **dots** (SVG) |
| Relação entre 2 variáveis | Correlação | **scatter** (SVG, com moderação) |
| Um número que pula (10→40, 3×) | Magnitude | **metric** (já existe) |

## Mapa 2 — conceito (não-numérico): a PERGUNTA escolhe o diagrama (Dan Roam, 6 Ws)

| A pergunta é... | Visual | Componente |
|:--|:--|:--|
| **Quem / o quê** (retrato, atores) | retrato / categorias | **cols** (já existe), **feats** |
| **Quando** (cronologia, marcos) | timeline | **timeline** |
| **Como** (processo, passos) | fluxograma | **steps** (já existe) |
| **Como** (processo cíclico) | ciclo | **cycle** (SVG) |
| Estrutura / quem-contém-quem | hierarquia | **tree** |
| Posição em 2 eixos (trade-off, estratégia) | quadrante | **matrix** |
| Afunilamento / camadas | funil/pirâmide | **funnel** (`.pyr` p/ pirâmide) |
| Interseção de conceitos | sobreposição | **venn** (SVG) |
| A vs B (escolha, antes/depois) | comparação | **versus** |
| Detalhar as partes de uma figura | diagrama anotado | **annotated** |

## Narrar o dado (Dykes, Rosling, Jobs)

- **Marque o ponto de virada.** Num `trend`/`slope`, destaque (`.hl`) o ponto onde a história acontece — não deixe o leitor procurar.
- **Torne o número humano** (Jobs: "1.000 músicas no bolso"). "42% a mais" > "de 0,71 pra 1,01". Coloque a tradução humana no título ou no `.cap`.
- **Uma sequência conta a história** (Shneiderman linear): resumo primeiro, depois o gráfico granular, depois o apêndice. Ver `explainer-method.md`.

---

## Snippets

Toda viz vai num bloco `.fig` (sem moldura) e ganha `reveal` + `--d` escalonado. `.cap` é a fonte/nota de rodapé (e ancora o grounding — todo número rastreia à fonte).

### bars — comparação / ranking / magnitude
```html
<div class="fig bars reveal" style="--d:240ms">
    <div class="b"><span class="lbl">2023</span><div class="track"><div class="fill" style="--v:42%"></div></div><span class="val">42</span></div>
    <div class="b hl"><span class="lbl">2024</span><div class="track"><div class="fill" style="--v:88%"></div></div><span class="val">88</span></div>
    <div class="cap">Fonte: <b>relatório anual</b></div>
</div>
```
`--v` é a largura proporcional (0–100%). `.hl` pinta a barra que carrega o ponto.

### colchart — colunas sobre categorias/tempo
```html
<div class="fig colchart reveal" style="--d:240ms">
    <div class="c"><div class="bar" style="--v:35%"><span class="n">35</span></div><span class="k">Q1</span></div>
    <div class="c"><div class="bar" style="--v:52%"><span class="n">52</span></div><span class="k">Q2</span></div>
    <div class="c hl"><div class="bar" style="--v:90%"><span class="n">90</span></div><span class="k">Q4</span></div>
</div>
```

### trend — tendência no tempo (SVG inline)
Geometria escrita à mão; o CSS dá a linguagem visual (`.ln`, `.area`, `.pt`, `.axis`, `.albl`, `.vlbl`). Coordenadas no `viewBox` (ex: 0 0 600 240).
```html
<div class="fig reveal" style="--d:240ms">
    <svg viewBox="0 0 600 240" role="img" aria-label="Tendência de X subindo após 2023">
        <line class="axis" x1="40" y1="210" x2="590" y2="210"/>
        <path class="area" d="M40,180 L160,170 L300,150 L440,90 L560,40 L560,210 L40,210 Z"/>
        <path class="ln" d="M40,180 L160,170 L300,150 L440,90 L560,40"/>
        <circle class="pt hl" cx="560" cy="40" r="6"/>
        <text class="vlbl" x="540" y="28">88</text>
        <text class="albl" x="40" y="228">2021</text>
        <text class="albl" x="540" y="228">2025</text>
    </svg>
    <div class="cap">O ponto de virada é <b>2023</b> — daí a curva dispara.</div>
</div>
```

### slope — comparação ponta a ponta (SVG inline)
```html
<div class="fig reveal" style="--d:240ms">
    <svg viewBox="0 0 600 260" role="img" aria-label="Antes e depois por item">
        <line class="axis" x1="120" y1="20" x2="120" y2="240"/>
        <line class="axis" x1="480" y1="20" x2="480" y2="240"/>
        <path class="ln muted" d="M120,80 L480,120"/>
        <path class="ln" d="M120,200 L480,40"/>
        <text class="albl" x="60" y="205">Item A · 70</text>
        <text class="vlbl" x="490" y="45">A · 95</text>
        <text class="albl" x="110" y="14">Antes</text>
        <text class="albl" x="470" y="14">Depois</text>
    </svg>
</div>
```

### part — parte-do-todo (barra de proporção)
```html
<div class="fig reveal" style="--d:240ms">
    <div class="part">
        <div class="seg a" style="--v:62%">62%</div>
        <div class="seg b" style="--v:28%">28%</div>
        <div class="seg c" style="--v:10%">10%</div>
    </div>
    <div class="part-key"><span class="a">Direto</span><span class="b">Parceiros</span><span class="c">Outros</span></div>
</div>
```

### donut — parte-do-todo (use com parcimônia)
```html
<div class="fig donut reveal" style="--d:240ms;--p:72%">
    <div class="ring"><span class="ctr">72%</span></div>
    <div class="leg"><span><b>72%</b> ativos</span><span>28% inativos</span></div>
</div>
```
`--p` é a fatia destacada (0–100%).

### waffle — isotype (parte-do-todo "humana"), 100 células
```html
<div class="fig reveal" style="--d:240ms">
    <div class="waffle">
        <!-- 100 <i>; as primeiras N com class="on" representam N% -->
        <i class="on"></i><i class="on"></i><i></i><!-- ...repita até 100 --></div>
    <div class="cap"><b>34 em 100</b> pessoas.</div>
</div>
```

### diverge — desvio acima/abaixo de uma base
```html
<div class="fig diverge reveal" style="--d:240ms">
    <div class="d"><span class="lbl">Norte</span><div class="neg"></div><div class="pos"><i style="--v:70%"></i></div><span class="val">+12</span></div>
    <div class="d"><span class="lbl">Sul</span><div class="neg"><i style="--v:45%"></i></div><div class="pos"></div><span class="val">−8</span></div>
</div>
```

### timeline — quando (marcos)
```html
<div class="fig timeline reveal" style="--d:240ms">
    <div class="ev"><div class="when">2019</div><h4>Fundação</h4><p>Nota do marco.</p></div>
    <div class="ev hl"><div class="when">2024</div><h4>Virada</h4><p>O ponto que importa.</p></div>
</div>
```

### matrix — quadrante 2×2
```html
<div class="fig reveal" style="--d:240ms">
    <div class="matrix">
        <div class="q"><div class="qt">Alto custo, baixo valor</div><div class="qd">evitar</div></div>
        <div class="q hl"><div class="qt">Alto valor, baixo custo</div><div class="qd">priorizar</div></div>
        <div class="q"><div class="qt">Baixo/baixo</div></div>
        <div class="q"><div class="qt">Alto custo, alto valor</div><div class="qd">cuidado</div></div>
        <span class="ax-x">Custo →</span><span class="ax-y">Valor →</span>
    </div>
</div>
```

### funnel — funil (ou pirâmide com `.pyr`)
```html
<div class="fig funnel reveal" style="--d:240ms">
    <div class="st" style="--w:100%">Visitantes <small>10.000</small></div>
    <div class="st" style="--w:70%">Cadastros <small>3.200</small></div>
    <div class="st" style="--w:40%">Clientes <small>480</small></div>
</div>
```

### tree — hierarquia
```html
<div class="fig tree reveal" style="--d:240ms">
    <div class="root">Sistema</div>
    <div class="branch"></div>
    <div class="kids"><div class="node">Módulo A</div><div class="node">Módulo B</div><div class="node">Módulo C</div></div>
</div>
```

### versus — A vs B
```html
<div class="fig versus reveal" style="--d:240ms">
    <div class="side"><h3>Hoje</h3><ul><li>Manual</li><li>Lento</li></ul></div>
    <div class="vs">vs</div>
    <div class="side win"><h3>Proposto</h3><ul><li>Automático</li><li>Instantâneo</li></ul></div>
</div>
```

### lollipop — ranking enxuto (variação de bars)
```html
<div class="fig lollipop reveal" style="--d:240ms">
    <div class="l"><span class="lbl">A</span><div class="stem"><i style="--v:40%"></i><b></b></div><span class="val">40</span></div>
    <div class="l hl"><span class="lbl">B</span><div class="stem"><i style="--v:88%"></i><b></b></div><span class="val">88</span></div>
</div>
```
`--v` posiciona a bolinha (0–100%). `.hl` destaca a que importa. Use no lugar de `bars` quando há muitos itens (menos tinta).

### pairbars — barra pareada (2 séries por categoria)
```html
<div class="fig pairbars reveal" style="--d:240ms">
    <div class="pb"><span class="lbl">2023</span><div class="set">
        <span class="bar a" style="--v:60%"><b>60</b></span>
        <span class="bar b" style="--v:42%"><b>42</b></span></div></div>
    <div class="pb"><span class="lbl">2024</span><div class="set">
        <span class="bar a" style="--v:90%"><b>90</b></span>
        <span class="bar b" style="--v:70%"><b>70</b></span></div></div>
    <div class="part-key" style="margin-top:18px"><span class="a">Meta</span><span class="b">Real</span></div>
</div>
```

### waterfall — como o total é construído (cumulativo)
O autor calcula `--o` (offset acumulado) e `--v` (largura) de cada passo. `.up` verde (entra), `.down` vermelho (sai), `.base` neutro (início/fim).
```html
<div class="fig waterfall reveal" style="--d:240ms">
    <div class="w"><span class="lbl">Início</span><div class="track"><i class="base" style="--o:0%;--v:60%"></i></div><span class="val">60</span></div>
    <div class="w"><span class="lbl">+ Vendas</span><div class="track"><i class="up" style="--o:60%;--v:30%"></i></div><span class="val">+30</span></div>
    <div class="w"><span class="lbl">− Custos</span><div class="track"><i class="down" style="--o:70%;--v:20%"></i></div><span class="val">−20</span></div>
    <div class="w"><span class="lbl">Final</span><div class="track"><i class="base" style="--o:0%;--v:70%"></i></div><span class="val">70</span></div>
</div>
```

### annotated — diagrama anotado (rótulos sobre uma figura/SVG)
Qualquer figura (SVG inline ou outro componente) com rótulos-callout posicionados por `--x`/`--y` (% do container). `.anno.r` inverte o lado da bolinha.
```html
<div class="fig annotated reveal" style="--d:240ms">
    <svg viewBox="0 0 600 280" role="img" aria-label="Diagrama do fluxo">
        <rect x="40" y="110" width="140" height="60" rx="10" fill="none" stroke="var(--primary-soft)" stroke-width="1.5"/>
        <path class="ln" d="M180,140 L420,140"/>
        <rect x="420" y="110" width="140" height="60" rx="10" fill="none" stroke="var(--accent-soft)" stroke-width="1.5"/>
    </svg>
    <span class="anno" style="--x:18%;--y:30%">Entrada</span>
    <span class="anno r" style="--x:82%;--y:30%">Saída</span>
</div>
```

### cycle / venn / dots / scatter (SVG inline)
Use a mesma convenção do `trend` (`.ln`, `.pt`, `.albl`). Ciclo = círculo com setas entre estágios; venn = 2–3 `<circle>` translúcidos (`fill:var(--glow-a)`) com rótulos. dots = `<circle>` posicionados em eixo horizontal (ou beeswarm) com `.albl` para outliers. scatter = `<circle>` em `viewBox` XY com `.albl` nos pontos de interesse. Escreva a geometria à mão no `viewBox` — não há CSS dedicado nem snippet; a convenção `.fig svg` se aplica a todos os quatro.

---

## Regras de composição

- **Densidade:** se um gráfico tem mais de ~7 itens ou não cabe em 1440×900 sem rolar, ou **agregue** (top-N + "outros"), ou **quebre** (overview num slide, granular noutro). Respiro > completude.
- **Proveniência:** todo número que entra num gráfico tem que existir no material de origem / fonte citada. O `.cap` carrega a fonte. O `scripts/check_provenance.py` cobra isso (passo de verificação do explicador).
- **Cor:** acento só no foco. Se tudo está colorido, nada está em foco.
