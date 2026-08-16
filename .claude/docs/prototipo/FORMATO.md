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
marcador-ficticio: FICTICIO
---

## Arquivos

- .claude/docs/prototipo/painel.html
- .claude/docs/prototipo/entrada.html

## Superfícies

- Painel do dia — jornada: acompanhar a obra — procedência: blueprint.md §3
- Entrada de pedido — jornada: registrar um pedido — procedência: blueprint.md §4
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
- `marcador-ficticio` — a palavra que marca dado inventado, a que a conferência por onda
  grepa nos arquivos de produto.
- `## Arquivos` — uma linha `- <caminho>` por arquivo, todos dentro da casa e existindo em
  disco. É este corpo que o carregador lê.
- `## Superfícies` — uma linha por superfície, com a jornada e a procedência.

Cobrador: `plugins/project-skills/lib/test_sidecar_prototipo.py` monta este exemplo num
diretório temporário (lar fingido pela receita de `_shared/lar-fingido.md`), confere campo
a campo, confere o `conjunto-sig` contra o `cat | cksum` de verdade, confere que trocar uma
tela diverge a marca — e confere que este arquivo aqui existe e escreve o formato inteiro.
Arquivo ausente REPROVA a suíte; não há caminho de pulo.
