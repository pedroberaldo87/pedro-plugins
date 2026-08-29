# Contrato da casa da doc — onde a documentação canônica de um projeto mora

A doc canônica mora em **`docs/` na raiz**, visível a quem abre o projeto.
`.claude/docs/` continua respondendo, e só por isso: retrocompatibilidade com o
que já existe. Este é o único lugar onde está dito **como** se acha a casa; quem
precisa do caminho pergunta ao resolvedor, não escreve o caminho de novo.

## A outra metade — o que é segredo mora escondido

A premissa tem duas metades e elas andam juntas: **doc é visível, segredo é
escondido**. O que qualquer um pode ler fica em `docs/`, à vista de quem abre o
projeto; o que ninguém pode ler fica em **`.claude/secrets/`**, pasta escondida
e **fora do git** (a linha `.claude/secrets/` no `.gitignore` é o que a torna
escondida de verdade — pasta com ponto no nome só some do `ls`, não do commit).
Valor-secreto não é apagado, é desviado para lá, e a doc referencia o nome da
variável, nunca o valor.

Por isso a casa da doc não é `.claude/docs/`: quem esconde a documentação num
diretório de ferramenta acaba tratando doc e segredo com a mesma régua, e uma
das duas sai errada — ou o segredo vaza junto com a doc, ou a doc some junto
com o segredo.

## O defeito que o resolvedor existe pra impedir

O caminho estava cravado em mais de cem pontos — skill, hook, script e prosa,
cada um com a sua cópia de `.claude/docs/…`. Mudar a casa vira, com isso, uma
varredura de cem edições que ninguém termina, e cada arquivo novo copia o
caminho do vizinho. É a doença que o dono nomeou **AI slop**: duplicar,
hardcodar e espalhar até virar dívida, em vez de amarrar e tornar recursivo.

## A cascata (para no primeiro que bater)

1. `<raiz>/docs/` existe → é ela, **salvo pelas duas exceções abaixo**, que são
   as duas sobre a casa antiga estar habitada de verdade.
2. senão, `<raiz>/.claude/docs/` existe → é ela (a casa antiga).
3. nenhuma das duas existe → `<raiz>/docs/`, porque doc que ainda não nasceu
   nasce na casa canônica.

### Exceção 1 · a nova existe VAZIA e a antiga tem a doc

`<raiz>/docs/` sem nenhum `.md` no primeiro nível e `<raiz>/.claude/docs/` com:
a casa habitada responde. Caso medido num projeto real em 2026-08-26, onde uma
`docs/` de outro uso escondia a doc aprovada.

### Exceção 2 · as DUAS habitadas, cada uma com um tipo de documento

As duas com `.md`, a nova com a prosa que o dono escreveu à mão e a antiga com
os documentos das skills: responde **a que tem documento desta família** — o que
abre com frontmatter e traz `project:` no cabeçalho.

O desempate é **mecânico, não adivinhado**: prosa escrita à mão não tem
frontmatter, e frontmatter de outra ferramenta não traz `project:`. Lê-se o
cabeçalho, nunca o corpo, e nunca se pergunta ao modelo.

**O caso medido em 2026-08-28 e o estrago dele.** As duas pastas
habitadas — 26 documentos de prosa na nova, nenhum com `project:`; 20 na antiga,
9 com o frontmatter completo. A cascata dava a nova, as ferramentas não achavam
a marca que procuram, e concluíam que o projeto **não tinha documentação
nenhuma** — em silêncio, com cara de sucesso: o `/doc-touch` dizia "nada a
tocar" com 277 arquivos mudados, e o `doc-load` declarava a lei do projeto
AUSENTE com os 16 documentos no disco. Como o `doc-load` é o preâmbulo
obrigatório de toda skill que julga obra, todas julgavam **sem régua, achando
que régua não existia**.

Nenhuma das duas com documento da família ⇒ segue valendo a canônica: a regra
só desempata quando há o que desempatar.

## A receita

| Onde | Arquivo | Como se usa |
|---|---|---|
| Python | `casa_da_doc.py` | `casa(raiz)` → a pasta · `casa(raiz, "architecture.md")` → o arquivo dentro dela |
| bash | `lib-casa-da-doc.sh` | `casa_da_doc "$RAIZ"` · `casa_da_doc "$RAIZ" architecture.md` |

As duas fazem a mesma cascata e devolvem caminho **sem criar nada** — o
resolvedor responde onde é, quem escreve é o chamador.

## Quem cobra

`_shared/test_casa_da_doc.py` — roda com as demais suítes de `_shared/` na
esteira e no gate de commit. Ele confere os três arquivos deste contrato (prosa,
Python, bash), prova a cascata nos **dois cenários de casa** — projeto com
`docs/` e projeto só com `.claude/docs/` — e cobra que as **duas metades da
premissa** estejam escritas aqui. A pauta de concepção que leva a premissa ao
dono é cobrada pela suíte da skill de concepção, no plugin que a hospeda.
