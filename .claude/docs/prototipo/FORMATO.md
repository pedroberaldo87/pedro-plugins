# O FORMATO do sidecar de protótipo

Esta é a parte NORMATIVA da §2b da concepção de prototipagem, e mora aqui — dentro do que
o clone recebe — porque o cobrador (`plugins/project-skills/lib/test_sidecar_prototipo.py`)
lê este arquivo em qualquer máquina. A spec de concepção discute o porquê; aqui está a lei.

Esta pasta é a CASA: `.claude/docs/prototipo/`. Os arquivos do protótipo moram aqui,
rastreados no git, e o sidecar mora aqui junto, um por etapa (`<etapa>.prototipo.md`).
Caminho fora dessa casa é erro de formato, não variação de gosto: é o que amarra a tranca
por herança e o que a conferência por onda sabe olhar sem procurar.

Exemplo COMPLETO e válido — `.claude/docs/prototipo/interface.prototipo.md`:

```markdown
---
natureza: anexo
anexo-de: design.md
design-sig: 1836471203
status: approved
conjunto-sig: 2374981110
marcador-ficticio: DADO-FICTICIO
---

## Arquivos

- .claude/docs/prototipo/painel.html
- .claude/docs/prototipo/entrada.html

## Superfícies

- Painel do dia — jornada: acompanhar a obra — procedência: blueprint.md §3
- Entrada de pedido — jornada: registrar um pedido — procedência: blueprint.md §4
- lacuna: governança — jornada: acompanhar a obra — motivo: sem papel de admin neste sistema
```

Os campos, um a um:

- `natureza: anexo` — a natureza PRÓPRIA do anexo, fora de `regua`/`marca_regua`.
- `anexo-de` — o documento que sustenta o de acordo (`design.md`; no Momento B, o próprio
  documento sob tranca). `design-sig` é a marca dele no dia da aprovação: reaprovar o
  design diverge essa marca e reabre o anexo junto.
- `status` — `approved` ou `ready`; `ready` EXIGE `correcao-pendente: <o que muda>`.
- `conjunto-sig` — a marca do CONJUNTO: o `cksum` POSIX da emenda dos arquivos listados,
  na ordem do corpo. Conferível na mão, sem programa nenhum:
  `cat .claude/docs/prototipo/painel.html .claude/docs/prototipo/entrada.html | cksum`.
  Só o rito de aprovação GRAVA; fora dele o comando imprime.
- `marcador-ficticio` — a palavra que marca dado inventado. O valor é o token literal
  `DADO-FICTICIO`, sempre (decisão do dono, 2026-08-13: zero ocorrência no repositório de
  quem instala, grep sem falso-positivo) — o campo existe para a conferência por onda ler
  DAQUI o que grepar, nunca de cor. Toda tela do protótipo escreve o token ao lado de cada
  dado inventado; a conferência por onda do sprint grepa o token nos arquivos de PRODUTO da
  onda (tudo fora desta casa), e achado ali é fictício vazando para produção.
- `## Arquivos` — uma linha `- <caminho>` por arquivo, todos dentro da casa e existindo em
  disco. É este corpo que o carregador lê.
- `## Superfícies` — uma linha por superfície, com a jornada e a procedência. **As
  superfícies obrigatórias — erro, vazio, carregando, configuração e governança — são
  cobradas POR JORNADA**: é o que a prática sempre ignora, e por isso cada jornada do
  `journeys.md` ou as tem cobertas por linha de superfície, ou declara a lacuna com motivo:
  `- lacuna: <superfície> — jornada: <a jornada> — motivo: <por que fica de fora>`.
  Lacuna sem `motivo:` é erro de formato — a checagem RECALCULA toda vez (superfícies do
  sidecar × jornadas), nunca guarda "já cobrado".

Cobrador: `plugins/project-skills/lib/test_sidecar_prototipo.py` monta este exemplo num
diretório temporário (lar fingido pela receita de `_shared/lar-fingido.md`), confere campo
a campo, confere o `conjunto-sig` contra o `cat | cksum` de verdade, confere que trocar uma
tela diverge a marca — e confere que este arquivo aqui existe e escreve o formato inteiro.
Arquivo ausente REPROVA a suíte; não há caminho de pulo.
