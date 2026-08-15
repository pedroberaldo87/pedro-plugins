---
name: slides
description: 'Gera uma apresentação HTML de slides — single-file, navegável por teclado, em linguagem keynote (tipografia grande, muito respiro, sem cara de dashboard), tema VIU Studio por padrão. Tem DOIS modos. (A) TRANSCRIÇÃO: renderiza fiel um .md já redigido — REGRA DE OURO: usa o texto literal, nunca inventa frases, callouts ou conclusões. (B) EXPLICADOR: quando pedem um deck pra ENSINAR/explicar um conceito, a própria skill dirige a didática (estrutura narrativa, nível do público, granular vs resumo, infográficos), com grounding factual e atualizado, nunca da cabeça do modelo. Use sempre que o usuário pedir "/slides", "monta esse md numa apresentação", "transforma isso em slides", "faz um deck", "vira slides", ou apontar um .md e pedir pra apresentar (→ transcrição); ou "monta um deck pra me explicar X", "explica X em slides", "cria um deck didático sobre Y", "me ensina Z em slides" (→ explicador) — mesmo sem dizer a palavra "slides". Suporta temas nomeados (sufixo): /slides arquivo.md [tema]. O deck é ADAPTATIVO num arquivo só: apresentação navegável no desktop e documento scroll (tudo na tela, sem depender de JavaScript) no celular e no thumbnail do WhatsApp. NÃO use para editar .pptx/Keynote existentes nem para gerar PDF.'
---

# Slides — deck keynote (transcrição ou explicador)

Gera uma apresentação HTML que abre no navegador e se apresenta em tela cheia. A engine, os componentes visuais e os infográficos já estão prontos em `assets/template.html`. A skill tem **dois modos**, com contratos de conteúdo opostos — decida qual ANTES de tudo.

## Dois modos de uso (despacho)

| O pedido é... | Modo | O que a skill faz |
|:--|:--|:--|
| apontar um `.md` já redigido e pedir pra "virar slides / apresentação / deck" | **A · Transcrição** | renderiza **fiel**, sem inventar texto (regra de ouro). É o **Workflow A** abaixo. |
| "monta um deck pra me **explicar** X" / "me ensina Y em slides" / dar um tema ou material e pedir pra ENSINAR | **B · Explicador** | **autora a didática** — estrutura, nível do público, granular vs resumo, infográficos — com grounding. É o **Workflow B** abaixo. |
| ambíguo (aponta um `.md` **e** pede pra "explicar/ensinar") | — | **pergunte** qual modo antes de montar. Não chute. |

**Por onde a pergunta chega quem escolhe é o usuário** — a régua dos dois canais (página de
decisão em múltipla escolha, ou a ferramenta nativa uma por vez) está em
**`regua-de-pergunta.md`**, ao lado deste arquivo (fonte: `_shared/regua-de-pergunta.md`, cópia
derivada; não editar à mão).

Os dois compartilham a mesma engine/template/temas e o mesmo cuidado de não-regressão (no-JS, thumbnail WhatsApp, 4 cenários de verificação).

## A regra de ouro (modo A · transcrição): o texto é do autor

Este é o eixo da skill, não uma preferência de estilo: **não invente texto.** O conteúdo dos slides sai literal do `.md`.

**Desde 2026-07-29 isso deixou de ser uma instrução pra você seguir e passou a ser
propriedade da construção:** quem transcreve é o `lib/md2deck.py`, e o texto de corpo sai
dos tokens do `.md` sem passar por geração nenhuma. Você não digita slide. As únicas
strings que o compilador cria são enumeradores (`01`, `02`) e o eyebrow derivado dos
headings — e é justamente isso que o `check_fidelity.py` isenta, porque derivar título de
heading é licença explícita desta skill.

O que continua valendo pra você:

- **Títulos de slide** podem encurtar/derivar de um heading do `.md`. O compilador usa o
  heading como está; se você quiser encurtar, **edite o heading no `.md`** — não reescreva
  no HTML.
- **Correções de ortografia/typo** ("dia-a-dia"→"dia a dia", "10token/sec"→"10 tokens/seg")
  são correção, não invenção — e também vão **no `.md`**, na fonte, onde ficam.
- Na dúvida entre encurtar e ser fiel, **seja fiel.** Se algo do `.md` está confuso e você
  acha que falta contexto, pergunte — não preencha por conta própria.

O `scripts/check_fidelity.py` continua no fluxo como **rede**, não como portão do seu
julgamento: sobre um deck compilado ele passa por construção (é um check verde da suite
`lib/test_md2deck.py`). Se ele acusar, é bug do compilador ou o `.md` mudou depois — não
"o modelo inventou".

## Um arquivo, duas formas de abrir (desktop + mobile/WhatsApp)

Vale para os dois modos de uso. O deck é **adaptativo por progressive enhancement** — o mesmo `.html` serve os dois sem gerar nada a mais:

- **Desktop (mouse + tela larga):** o JS ativa o modo apresentação — slide a slide, `← →`, `F`, swipe, reveals.
- **Celular / sem-JS / thumbnail do WhatsApp:** a página é um **documento scroll vertical** com todos os slides empilhados e visíveis. O conteúdo está no HTML estático; **nada depende do JS** pra aparecer.

Por que importa: o `.html` costuma ser enviado por WhatsApp, que gera o thumbnail renderizando o arquivo **sem garantir JS** — se o conteúdo dependesse de JS, o preview sairia preto. O template já resolve (estado base = documento). Seu único cuidado ao montar: **não reintroduzir dependência de JS no conteúdo** — todo texto/figura vai no markup do slide, nunca injetado por script.

Nota: isso é o thumbnail de **anexo** (renderiza o arquivo). É diferente do preview de **link** (Open Graph / `og:image`), que exigiria hospedar numa URL pública — fora do escopo. As tags `og:title`/`og:description` entram só de brinde.

## Workflow A — transcrição (o `.md` já está pronto)

Quem monta o deck é o compilador. Seu trabalho é **ler a fonte, revisar o plano dele e
corrigir o que ele escolheu errado** — nunca digitar HTML.

### 1. Leia a fonte e escolha o tema
- Leia o `.md` inteiro. A estrutura de headings (`#`, `##`, `###`) e bullets é o esqueleto do deck — se ela está ruim, o deck sai ruim, e o conserto é **no `.md`**.
- Tema: padrão **viu**. Se o usuário passar um sufixo (`/slides arquivo.md <tema>`), use esse. O compilador lê `references/themes/<tema>.md` sozinho; tema inexistente → ele lista os que existem. Se o usuário pediu um que não existe, ofereça criar (a partir de `references/themes/viu.md`).

### 2. Veja o plano do compilador
```bash
MD2="${CLAUDE_PLUGIN_ROOT}/lib/md2deck.py"
python3 $MD2 <fonte.md> --plan
```
Devolve, slide a slide: heading, nível, componente escolhido, nº de itens e em quantos
slides aquele heading vai virar. **Leia isso como se fosse o storyboard.** A regra de
escolha é o mapa "tipo de conteúdo → componente" de `references/layout-patterns.md`,
implementada: `#` → capa (o 1º) ou section divider · bullets curtos → **numlist** ·
`nome — descrição` → **idx** · 2-3 bullets com lead em negrito → **feats** · parágrafo
curto solto → **statement** · `X → Y` → **metric**.

### 3. Anote só o que ele errou (é aqui que entra o seu julgamento)
Componente e ponto de quebra são julgamento; o resto não é. Corrija por anotação:
```json
{ "Os quatro pilares do método": { "component": "idx", "hl": "pilares" },
  "Lista longa demais pra um slide": { "split": 3 } }
```
Chaveado pelo **heading exato**. Campos: `component` (um de cover · divider · numlist ·
idx · feats · statement · metric · pull · cols — componente inexistente é recusado com a
lista), `hl` (palavra do título a pintar), `split` (itens por slide; default 6).

**Densidade:** um slide = uma ideia. O compilador já quebra em 6 itens; se ainda não
couber em 1440×900, baixe o `split` daquele heading. Não comprima a fala do autor pra
"caber em N slides".

### 4. Compile
```bash
python3 $MD2 <fonte.md> [--tema <tema>] [--anota anota.json]
```
Imprime o caminho. **Saída: ao lado do `.md` de origem**, mesmo nome-base + `.html`
(destino read-only tipo iCloud → cai pro `~/Desktop/` e avisa). Placeholder não
substituído ou tema que não ficou ativo → `exit 2` com a razão, e nada é escrito.

### 5. Verifique fidelidade (obrigatório, e agora é rede)
```bash
python3 <skill>/scripts/check_fidelity.py <deck.html> <fonte.md>
```
Num deck compilado isso passa por construção. Se acusar, **não conserte o HTML** —
é bug do compilador ou o `.md` mudou depois de compilar. Rode de novo; se persistir,
é conserto no `lib/md2deck.py` + um check em `lib/test_md2deck.py`.

### 6. Verifique o visual — os 4 cenários (reproduza e OLHE o print)
Não basta inspecionar o DOM: tire screenshot e analise se está coerente com o esperado.
Print tem casa declarada — `.claude/prints/` do projeto, pela tabela "As pastas" do
`contrato-familia.md`. Nada de `/tmp`: print fora da casa some sem ninguém ver.

1. **Thumbnail do WhatsApp (sem JS):** reproduza com a engine WebKit do macOS —
   ```bash
   mkdir -p .claude/prints
   qlmanage -t -s 1200 -o .claude/prints "<deck>.html" && open ".claude/prints/<deck>.png"
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
- Sinalize qualquer micro-decisão de título/encurtamento que tenha tomado, pro usuário validar.

## Workflow B — explicador (você vai ENSINAR um conceito)

O conteúdo aqui é **autorado**, não transcrito — a regra de ouro (texto literal) **não vale**; vale a **trava de grounding**. Leia `references/explainer-method.md` (a didática) e `references/infographics.md` (a viz) **antes de montar**.

### 1. Intake — pergunte só o que não veio
Resolva: **público & nível**, **profundidade** (um nível vs progressivo), **altitude do dado** (resumo/granular), e **o trabalho do deck** (ensinar / defender mudança / apresentar análise). Use o que está explícito no pedido; **pergunte o que faltar** antes de montar.

### 2. Grounding — factual E atualizado
Ancore no material fornecido + **pesquise** pra ampliar o entorno e **atualizar** (nada de info velha do treino). Cite as fontes. **Nunca afirme o que não está no material/fonte.** Se só veio o tema (sem material), a pesquisa é **obrigatória** antes de autorar — nunca solte da cabeça do modelo.

### 3. Proponha a abordagem e confirme
Escolha, pelo `explainer-method.md`: a **arquitetura narrativa** (família A), o slide didático (**Assertion-Evidence**, B), a **calibração pro público** (dial C), e a **granularidade**. **Apresente a abordagem comparada com 1–2 alternativas (prós/contras)** e **confirme** antes de montar. Não escolha a didática calada.

### 4. Monte o HTML
Aqui o conteúdo é **autorado**, então o caminho é diferente do Workflow A: escreva o `.md`
da sua didática primeiro e compile-o com o `md2deck.py` (passos 2-4 do Workflow A) —
assim a estrutura continua vindo do programa e o que você autora fica registrado na fonte,
revisável. Os **infográficos entram em peso** e hoje **não** são cobertos pelo compilador:
monte-os à mão, dentro do slide já compilado, escolhendo pelo `infographics.md`
(mensagem→gráfico / pergunta→diagrama) e usando as classes de `assets/template.html`.
**Título = a afirmação; o gráfico/visual = a prova.**

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
- `lib/md2deck.py` — **o compilador do modo A.** `--plan` mostra o storyboard, `--anota` recebe o seu julgamento. Suite: `lib/test_md2deck.py`.
- `references/layout-patterns.md` — mapa tipo-de-conteúdo → componente, snippets. O compilador implementa o mapa; leia pra entender a escolha dele e pra montar infográfico à mão no modo B.
- `references/explainer-method.md` — **modo B:** a didática (arquitetura narrativa, Assertion-Evidence, dial novato↔expert, limites, granularidade, grounding). Menu de prós/contras pra propor-e-confirmar.
- `references/infographics.md` — **modo B:** o ofício de viz (fronteira Cairo, leis de craft, tells proibidos, mapas FT/Roam, snippets de cada infográfico).
- `references/themes/viu.md` — o tema canônico e o contrato de variáveis para criar temas novos.
- `assets/template.html` — engine (navegação, reveals, progress) + CSS dos componentes **e dos infográficos**. Parametrizado só por `var()` do tema.
- `scripts/check_fidelity.py` — **modo A:** verificação anti-invenção (texto literal).
- `scripts/check_provenance.py` — **modo B:** verificação de proveniência numérica (todo número rastreia à fonte).
