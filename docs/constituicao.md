---
generated: 2026-08-21
reviewed: 2026-08-21
project: pedro-plugins
authored-by: human
status: ready
scope:
  - .claude/hooks/release-gate.sh
  - scripts/hook_contract.py
  - scripts/regua_call_check.py
  - scripts/public_repo_check.py
  - .github/workflows/portability.yml
doc-sig: pedro-plugins/release-gate.sh@gen=3.8#2c86f1ea
---

# A constituição

> As dimensões em que este marketplace é julgado — quantas são hoje, diz
> `grep -c '^## Artigo ' .claude/docs/constituicao.md` — e **quem cobra cada uma**. Quando
> houver conflito com qualquer outro documento, ganha este. `quality-goals.md` continua
> mandando na *forma* do que se escreve; aqui está o que o sistema *tem que ser*.

O produto deste repositório não é código: é **comportamento de agente instalado na máquina
de um terceiro**. Isso muda o que significa "pronto". Um plugin que funciona aqui e morre
calado lá não está pronto — está mentindo.

## A cláusula que manda em todas

**Artigo sem cobrador é dívida declarada, não regra.** Cada artigo abaixo diz quem o
cobra. **E a lei entra a cada decisão, não uma vez por sessão:** quem decide qualquer
coisa julga contra ela na hora — carregá-la na largada e esquecê-la no meio é o mesmo
que não tê-la lido.
Onde está escrito *hoje não há quem cobre*, a frase é a admissão de que aquilo é intenção,
e o gate correspondente é trabalho em aberto — nunca se cita esse artigo para reprovar
alguém sem antes construir o cobrador.

O motivo está registrado no próprio repositório: regra em prosa não pegou, e **368
ocorrências do nome do dono entraram** enquanto a regra do repositório público era só um
parágrafo (`.claude/CLAUDE.md`, Custom Rules). Prosa não cobra. Programa cobra.

---

## Artigo 1 · Arquitetura

**O que exige** — Todo acoplamento entre plugins é declarado no catálogo, e degrada no
ponto de uso. Plugin que só funciona porque outro está instalado, sem declarar isso, não
entra no `marketplace.json`.

**Como se cobra** — Hoje não há quem cobre. O catálogo não tem campo de dependência. O gate
seria um `check_dependencias_plugin` em `plugins/bootstrap/lib/conformance.py`, irmão do
`check_ferramentas_externas` que já cobra binário externo por `requerido_por` — e a
cobrança de commit tem que morar no `release-gate.sh`, não só no `conformance.py`: o que só
o segundo cobra passa no commit e só aparece no próximo `bootstrap:setup`.

**Prova de que vale hoje** — As chaves de cada entrada do catálogo são `author`, `category`,
`description`, `name`, `source`, `tags`, `version` — nenhuma de dependência. E há skill
mandando rodar arquivo de outro plugin (`plugins/handoff/skills/handoff/SKILL.md:84`).

---

## Artigo 2 · Aplicabilidade

**O que exige** — Nada que sirva só à máquina de quem escreveu entra como padrão. Default
que toca o disco, o git ou as permissões de quem instala **nasce desligado**.

**Como se cobra** — Hoje não há quem cobre — e a exigência é do dono, dita e minerada
(*"nada que sirva só à máquina de quem escreveu"*), não inferência. Existe
`scripts/public_repo_check.py`
(checagem H do gate de commit), mas ele pega **dado pessoal**, não **default pessoal**. O
gate seria uma lista de padrões proibidos em `settings-defaults.json` e `manifest.json`:
permissão automática para comando destrutivo, plugin ligado de fábrica com dependência
externa não instalada, e caminho padrão apontando para uma pasta do autor.

**Prova de que vale hoje** — `plugins/bootstrap/config/settings-defaults.json` continua
ligando aprovação automática na máquina de quem instala: **121** permissões no `allow`
(`python3 -c "import json;print(len(json.load(open('plugins/bootstrap/config/settings-defaults.json'))['permissions']['allow']))"`).
O que saiu desse allow nesta rodada — `Bash(git push*)`, `Bash(ssh-add*)`, `Bash(supabase*)`
e os prefixos de atribuição com curinga (`Bash(TOKEN=*)`, `Bash(SUPABASE_*)`), que reabriam
qualquer comando — saiu por revisão manual, não por gate: nada impede a próxima entrada
igual. `plugins/bootstrap/skills/bootstrap/SKILL.md:88` hoje diz o que o setup de fato faz —
"Isso **liga aprovação automática**" — e enumera família por família o que entra.

---

## Artigo 3 · Portabilidade

**O que exige** — Nenhum comando executado pelo harness pode depender de bash, de `open`,
de barra normal no caminho, ou de um `python3` que existe mas não executa. A régua vale nas
**três camadas**: o `hooks.json`, o script `.sh`, e o comando escrito dentro de um
`SKILL.md`.

**Como se cobra** — Cobrado. `scripts/test_crlf.sh`, `test_python_probe.sh`,
`test_paths_normalize.sh` e `test_bootstrap_aviso.sh` deixaram de ser só medidor: o check J
do `release-gate.sh` roda `scripts/test_*.sh` quando o commit toca hook, script ou
`.gitattributes` — o recorte existe porque o bloco leva ~100s e em todo commit seria
proibitivo — e `.github/workflows/portability.yml` roda tudo no push, nos três sistemas
operacionais.

**Prova de que vale hoje** — `bash scripts/test_paths_normalize.sh` sai 0, e entre os casos
verdes está "nenhum `hooks.json` depende de sintaxe exclusiva do bash": o `Bad substitution`
de `${var//x/y}` sob o shell POSIX do Linux não tem mais onde acontecer. `test_crlf.sh` e
`test_python_probe.sh` também saem 0.

---

## Artigo 4 · Rigor

**O que exige** — Gate que não consegue medir tem que **dizer que não mediu**. O
complemento disso: quem afirma **verificado** diz a amostra — "conferi os 23" vale,
"conferi" solto não.
Nada é removido sem a procedência anotada na origem (quem criou, por quê, e por que
morre). Anistia de dívida tem data e âncora de conteúdo — nunca imunidade permanente
por arquivo.

**Como se cobra** — Cobrado de verdade, com dois furos abertos. `scripts/hook_contract.py`
mede cinco propriedades de todo hook, e os checks E e E2 do `release-gate.sh` barram a
deriva contra o retrato. Os furos: retrato ausente faz o bloco inteiro ser pulado em
silêncio, e a chave da anistia não inclui a linha nem a citação, então um arquivo ganha
imunidade permanente à regra.

**Prova de que vale hoje** — Sem o retrato, o mesmo comando que hoje diz "nenhum achado"
devolve `Total: 3 achado(s) — 1 alta`, e sai 1.

---

## Artigo 5 · Funcionalidade

**O que exige** — Toda suíte rastreada roda em algum gate. Nenhum arquivo de teste fica
órfão de cobrador.

**Como se cobra** — Cobrado em duas camadas, com um furo de momento. No commit, os checks
D, D2 e F do `release-gate.sh` cobrem `plugins/<n>/lib/*.py`, `_shared/*.py` e
`plugins/<n>/hooks/*.sh` **do plugin tocado**, e o check J acrescentou
`plugins/*/hooks/test_*.py` e `scripts/test_*.sh` — os `.py` dentro de `hooks/` não estão
mais órfãos. No push, `.github/workflows/portability.yml` roda **todas** as suítes
rastreadas, nos três sistemas operacionais. Os dois lados têm asserção de quantidade: glob
que deixa de casar arquivo reprova em vez de ficar verde sem rodar nada, e
`scripts/suites_orfas.py` reprova o inverso — suíte rastreada que globo nenhum alcança. O furo que sobra é de
**momento**, não de cobertura: `scripts/test_*.py` e `.claude/hooks/test_release_gate.sh`
só têm a esteira, então uma quebra neles passa o commit e só aparece no push.

**Prova de que vale hoje** — ⚠️ **Este artigo não crava quantas suítes existem, de
propósito.** Até 2026-08-07 ele dizia "são 54, e a soma dos sete globos também dá 54" — e
no dia em que isso foi revisto a contagem real era **60**, com o texto ainda em 54. Número
escrito num documento envelhece em silêncio: ninguém revalida a frase quando acrescenta um
teste. O que este artigo exige é a **igualdade entre os dois lados**, e quem a confere é
`scripts/suites_orfas.py` — que lê a lista do git e os globos de `portability.yml` na hora,
sem cópia nenhuma:

```
$ python3 scripts/suites_orfas.py
suítes rastreadas: 60 · globos da esteira: 7
  plugins/*/lib/test_*.py            → 24
  _shared/test_*.py                  → 1
  scripts/test_*.py                  → 3
  plugins/*/hooks/test_*.py          → 2
  plugins/*/hooks/test_*.sh          → 21
  scripts/test_*.sh                  → 8
  .claude/hooks/test_*.sh            → 1
Nenhuma órfã: toda suíte rastreada casa algum globo da esteira.
```

Suíte rastreada que nenhum globo alcança sai como órfã e o comando devolve 1. O caminho
inverso — globo que deixou de casar arquivo — já reprova dentro da própria esteira. Os dois
juntos fecham a conta sem que exista um número escrito em lugar nenhum.

O furo de momento encolheu e continua verificável: o portão roda `scripts/test_*.py` no
commit (`grep -n "roda_suites python3 'scripts/test_" .claude/hooks/release-gate.sh` acha
a linha), e o que resta só na esteira do push é `.claude/hooks/test_*.sh` —
`grep -c '\.claude/hooks/test_' .claude/hooks/release-gate.sh` devolve 0. O vermelho antigo desta seção — o juiz de forma em
`plugins/bootstrap/hooks/test_bootstrap_hooks.sh` — não existe mais: a suíte fecha
`53 ok · 0 FAIL` e sai 0, numa máquina com `claude` no PATH.

---

## Artigo 6 · Estética

**O que exige** — Todo texto que um humano lê passa pela régua de `_shared/regua_texto.py`
antes de sair. Isso inclui a página gerada, o relatório, **e a mensagem que um hook emite**.

**Como se cobra** — Cobrado em duas frentes: a checagem I roda
`scripts/regua_call_check.py --staged` sobre os geradores Python, e
`scripts/test_regua_hook_msgs.py` (na esteira e no bloco de commit dos testes de scripts)
mede a linha EMITIDA de toda mensagem de hook shell — teto de 160, o 140 do perfil mais a
folga de marcação. O que segue em aberto: a checagem I casa a string do nome da régua,
então um comentário ainda isenta o arquivo.

**Prova de que vale hoje** — `python3 scripts/test_regua_hook_msgs.py` mede os hooks do
repositório e sai 0; uma linha de recusa acima do teto faz o mesmo comando sair 1 (o
autoteste embutido prova as duas direções).

---

## Artigo 7 · Clareza da instrução

**O que exige** — Duas skills não reivindicam o mesmo gatilho sem declarar a precedência
**nos dois lados**. Número afirmado em `SKILL.md` é derivável por um comando, ou não
existe.

**Como se cobra** — Gatilho cruzado tem cobrador desde 2026-08: a varredura do
check-skills (`plugins/check-skills/lib/varredura.py`), pelas lentes NOME REPETIDO,
GATILHO DISPUTADO, GATILHO MORTO e SEM SITUAÇÃO. `plugins/guardrails/lib/askq_lint.py`
segue cobrindo a linguagem das perguntas, e a checagem G o carimbo de geração defasado.
Número em prosa é coberto só onde o padrão casa (`scripts/desacoplamento_check.py`); o
teste dedicado a número dentro de `SKILL.md` continua dívida declarada.

**Prova de que vale hoje** — Os dois exemplos que este artigo carregava foram consertados:
as duas skills que disputavam "projeto sem CLAUDE.md" hoje declaram a precedência nos dois
lados (`start` na seção "Convivência com o /doc", `doc` na seção "Documentos autorais —
território do /start"), e nenhum `SKILL.md` afirma contagem de checks divergente. A dívida
que resta é a mesma declarada acima: número cravado fora do padrão do cobrador só cai por
leitura — três foram achados e consertados no pente fino de 2026-08-21.

---

## Artigo 8 · Executabilidade por um agente

**O que exige** — Todo comando dentro de um `SKILL.md` roda **como está escrito**, a partir
da pasta do projeto de quem instalou. Sem placeholder para o agente adivinhar, sem caminho
relativo à raiz deste repositório, sem variável que chega vazia.

**Como se cobra** — Cobrado desde 2026-08-21: `scripts/artigo8_check.py` varre os `.md`
executáveis das skills (SKILL.md, references e cópias vendoradas) e reprova os três
padrões — caminho `plugins/<x>/...`, placeholder órfão, e a variável de raiz do plugin em
comando de agente. O check V do `release-gate.sh` barra o que PIORA contra o retrato
`.claude/artigo8.baseline.json`; a dívida congelada é paga por passo de plano, como no
Artigo 9. Isenção ganha `artigo8-ok: <motivo>` na linha.

**Prova de que vale hoje** — `python3 scripts/artigo8_check.py --json` devolve o placar
contra o retrato; apagado o retrato, o mesmo comando lista as centenas de achados
congelados em vez de dizer 'nenhum'.

---

## O placar de hoje

- **Com cobrador real:** Artigos 3, 4, 5, 6, 7, 8, 9 e 13 — o 5 com o furo de momento
  reduzido (só `.claude/hooks/test_*.sh` fica sem gate de commit); o 6 cobrado em duas
  frentes (gerador Python pela checagem I, mensagem de hook shell por
  `scripts/test_regua_hook_msgs.py`); o 7 com o teste dedicado a número em `SKILL.md`
  ainda como dívida; o 8 e o 9 nascem com a dívida congelada como linha de base.
- **Com cobrador parcial e furo declarado no próprio artigo:** Artigos 10, 11 e 12.
- **Sem cobrador:** Artigos 1 e 2.

Este placar é parte da lei, não nota de rodapé. Ele é o que impede a constituição de virar
o parágrafo que não pegou.

## Como um artigo muda

Artigo novo ou emenda entra com as três partes preenchidas — o que exige, quem cobra, a
prova — e a parte "quem cobra" cita o gate por nome. Emenda que não consegue nomear o
cobrador entra com *hoje não há quem cobre* escrito, e vira dívida no placar acima.

---

## Artigo 9 · Desacoplamento

**O que exige** — Nenhum arquivo deste marketplace amarra **o nome** ou **a quantidade** de
outro. Skill não cita plugin irmão por caminho; documento não crava quantos plugins,
skills, hooks ou suítes existem. Onde a informação é necessária, o arquivo diz **o comando
que a descobre** — nunca a resposta de hoje.

Três formas proibidas, e o defeito de cada uma:

- **Irmão por posição** (`${CLAUDE_PLUGIN_ROOT}/../<outro>/…`) — o cache do harness instala
  cada plugin em pasta própria, com a versão no nome; `../<irmão>` não resolve na máquina
  de quem instalou. Não é risco futuro: em 2026-08-07 havia quatro ocorrências e **duas já
  estavam quebradas** (`qa-loop` apontando para o `sovai`, `start-doc` apontando para o
  `visual`).
- **Lista de nomes em prosa** — enumerar os plugins que existem, ou os que uma skill
  conversa com, cria um retrato que só quem escreveu sabe atualizar. Plugin novo entra e a
  lista fica errada em silêncio.
- **Contagem cravada** — "os 21 plugins", "as 54 suítes". Envelhece sem avisar, e ninguém
  revalida a frase ao acrescentar um arquivo. Foi o defeito que este documento carregou até
  2026-08-07, dizendo **54** quando a medição devolvia **60** (ver Artigo 5).

**O que substitui cada uma:**

- irmão por posição → um **resolvedor** que acha o plugin instalado pelo nome dele, e
  degrada com aviso quando ele não está na máquina;
- lista em prosa → o **índice que já existe** (`.claude-plugin/marketplace.json` para o que
  é distribuído, `hooks/hooks.json` para o que escuta evento);
- contagem cravada → o **comando** que a produz, ao lado do número, quando o número ajudar
  a ler.

**Como se cobra** — `scripts/desacoplamento_check.py`, que varre os arquivos rastreados e
reprova as três formas. Isenção legítima ganha `acopla-ok: <motivo>` na linha — o mesmo
molde do `public-ok` do Artigo 2. Duas isenções nascem com o gate: o **próprio índice**
(que existe para listar) e a **narrativa histórica** (contar que uma contagem estava errada
não é cravar contagem).

**Prova de que vale hoje** — ⚠️ Este artigo nasce com dívida medida, e ela é o número
inicial do gate, não a meta:

```
$ python3 scripts/desacoplamento_check.py
75 citações cruzadas de nome de plugin, em 14 skills
 4 caminhos de irmão por posição — 2 deles já quebrados no disco
 8 contagens cravadas em documento
```

O gate nasce com esse retrato como linha de base, do mesmo jeito que o contrato dos hooks
(`.claude/hook-contract.baseline.json`): ele reprova o que **piora**, e a dívida existente é
paga por passo de plano, não por bloqueio de commit. Gate que nasce reprovando tudo é gate
desligado no primeiro dia.

---

## Artigo 10 · Replicabilidade

**O que exige** — Uma máquina nova fica pronta com um gesto: o bootstrap replica
marketplaces, plugins e terceiros pelo manifest, sem passo manual além de instalá-lo.
Tudo que o ambiente precisa para existir está declarado em arquivo versionado — nada
mora só na memória de quem configurou.

**Como se cobra** — `conformance.py:check_catalogo` confere que todo plugin do
catálogo está no manifest do bootstrap. O furo aberto: terceiros e settings não têm
check de ida-e-volta (instalado ⇄ declarado) — construí-lo é trabalho em aberto.

**Prova de que vale hoje** — `plugins/bootstrap/config/manifest.json` lista os
plugins por nome; a última máquina nova montada por ele está registrada no journal.

---

## Artigo 11 · CI verde com causa

**O que exige** — CI vermelho é evento com dono, nunca estado permanente. Toda falha
tem a causa escrita antes do conserto, e o desacordo entre a régua e a obra tem três
destinos e só três: conserto, revogação da régua, ou limite aceito com motivo e
condição de revogação escritos — nunca silêncio.

**Como se cobra** — A esteira local é a mesma do CI (`scripts/suite.sh`), o portão de
commit confere a prova dela, e a vigília do sprint — o laço que investiga a causa de
cada parada e relança a execução — completa o circuito. O furo aberto: nenhum gate
cobra hoje que um run vermelho de CI gere causa escrita, e construí-lo é trabalho
em aberto, já planejado.

**Prova de que vale hoje** — `.claude/limites-aceitos.md` carrega um limite aceito
com causa medida e condição de revogação — o formato que este artigo exige.

---

## Artigo 12 · Cobertura visual

**O que exige** — Todo fluxo nomeado na documentação tem diagrama, e todo módulo tem
o seu — a tabela de níveis de detalhe, aprovada por você antes de qualquer desenho,
decide o grão de cada um, nunca a existência. Diagrama é camada da documentação
canônica: nasce dela, atualiza com ela, e divergência entre o desenho e o código é
corrigida como a do texto.

**Como se cobra** — O `doc-touch` re-renderiza o diagrama de toda camada cujo doc foi
re-projetado. O furo aberto: não há cobrador de cobertura (fluxo sem diagrama passa
calado) — construí-lo é trabalho em aberto, já planejado.

**Prova de que vale hoje** — `docs/fluxos/` guarda as três camadas com nome estável
(`organismo.html`, `app-<nome>.html`, `fluxo-<slug>.html`) e é versionada — a casa
canônica desde o commit `1e0bb99`; `.claude/archify/` ficou para desenho avulso de
sessão. O passo 2b do doc-touch as regenera.

---

## Artigo 13 · Toda obra é julgada contra uma régua escrita

**O que exige** — Nenhuma obra é aprovada de memória: quem julga carrega a régua do
projeto (lei, acordo aprovado) antes de julgar, e cita a passagem que a obra viola.
Projeto sem régua não tem julgamento pleno — e viver sem ela é decisão declarada
(dispensa com motivo), nunca esquecimento.

**Como se cobra** — `doc_load.py` lista o que vale como régua e grita a lacuna; o
gate de plano barra plano sem documentação nem dispensa; os motores de sprint e
qa-loop tiram uma impressão do texto dos documentos no início da execução — um número
curto que muda se qualquer letra mudar — e a conferem a cada rodada, para que documento
alterado no meio do caminho vire aviso, nunca troca silenciosa.

**Prova de que vale hoje** — os três cobradores acima existem e têm suíte, e a impressão
descrita acima é registrada a cada execução; a dos três documentos da lei, nesta sessão,
é `2396033228+2813587699+881584814`.
