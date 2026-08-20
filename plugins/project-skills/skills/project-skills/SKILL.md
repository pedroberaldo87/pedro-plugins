---
name: project-skills
description: Indice da familia de skills de projeto, que ja mora aqui — documentacao, concepcao, plano, execucao e revisao. Use quando o usuario digitar "/project-skills", "quais skills de projeto", "que skill de projeto eu uso aqui", quando invocar este nome sem dizer o que quer, ou perguntar qual skill de projeto serve para a tarefa dele — a resposta e listar as skills da familia lidas do disco e apontar a certa.
---

# Skill: project-skills (índice da família)

Este arquivo é o índice da família. Quando alguém chega por aqui sem dizer o que quer,
liste as skills que moram no plugin e aponte a que serve à tarefa.

A lista se DESCOBRE, nunca se escreve de cor:

```bash
ls "${CLAUDE_PLUGIN_ROOT}/skills"
```

Cada uma se apresenta na própria `description` — leia a da candidata antes de indicá-la.

---

## A premissa anti-drift — vale para TODA skill desta família

**Nada que duas skills precisam saber é escrito em duas skills.** Regra que aparece em mais
de um lugar tem exatamente uma fonte, e os consumidores **apontam** para ela.

O motivo não é elegância, é que a duplicata falha **em silêncio**: prosa copiada diverge no
primeiro conserto, e nenhum dos dois lados fica errado sozinho (`patterns.md` §1.6a). Foi
assim que uma skill de revisão passou a listar quatro documentos de régua enquanto o
programa já listava onze — as duas "certas", a soma errada.

**Três formas, e qual usar quando:**

| O que é compartilhado | Onde mora a fonte | Como o consumidor chega nela |
|---|---|---|
| **Dado** (tier, limiar, tabela) | `_shared/<nome>.json` | a casca lê a cópia local e passa em `args` — nenhum `SKILL.md` carimba o valor |
| **Contrato em prosa** (régua, checklist, antipadrão) | `_shared/<nome>.md` | vendorado em `references/`, e o `SKILL.md` **cita o arquivo** em vez de repetir o texto |
| **Coisa que muda sozinha** (o que vale como régua hoje, quais skills existem) | um **programa** | o `SKILL.md` manda **rodar** o programa; nunca escreve a resposta de hoje |

A terceira é a mais fácil de errar: a resposta parece estável até o dia em que não é.
Lista de documento de projeto, de plugin instalado e de skill da família **sempre** cai
aqui — por isso este índice manda `ls` no disco em vez de enumerar as irmãs.

**Toda fonte compartilhada nasce com cobrador**, senão a premissa é intenção, não regra
(constituição, cláusula que manda em todas). Dois já existem e servem de molde:
`scripts/test_dimensoes_de_revisao.py` (o tripé da revisão) e
`scripts/test_regua_de_pergunta.py` (a régua de pergunta) — os dois exigem que a cópia
esteja idêntica à fonte **e** que o `SKILL.md` aponte em vez de repetir. Os destinos saem
de `scripts/vendoring.py`, que os lê do próprio `sync-shared.sh`: lista de caminho escrita
à mão é o mesmo defeito com outra roupa.

Ao criar ou editar skill desta família, a pergunta é uma: **isto que estou escrevendo já
está escrito em outro lugar?** Se estiver, apague e aponte.

---

## A casa da doc — onde a documentação de um projeto mora

Premissa desta casa, não gosto, e ela tem **duas metades que andam juntas**: **doc é
visível, segredo é escondido**. A doc canônica nasce em `docs/` na raiz, à vista de quem
abre o projeto; valor-secreto vai para `.claude/secrets/`, pasta escondida e **fora do git**
(a linha no `.gitignore` é o que a esconde de verdade), e a doc referencia o nome da
variável, nunca o valor.

O contrato inteiro — a cascata, a casa antiga que continua respondendo, o resolvedor
(`casa_da_doc.py` · `lib-casa-da-doc.sh`) e quem cobra — está em `_shared/casa-da-doc.md`.
Nenhuma skill desta família escreve o caminho de novo: **pergunta ao resolvedor**. Cravar
`.claude/docs/` na prosa é a duplicata da seção acima, com outra roupa.
