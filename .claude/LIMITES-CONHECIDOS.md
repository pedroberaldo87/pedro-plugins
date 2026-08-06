# Limites conhecidos

## Limpeza de dados de terceiros na árvore — 2026-07-30

O que saiu da árvore de trabalho nas etapas F1.1 e F1.2, em ~26 arquivos
(docs, skills, hooks, testes e config de permissão):

nomes reais de projetos e clientes usados como exemplo, referências a serviços
externos e a arquivos de configuração local de outro repositório, e entradas de
permissão que só faziam sentido naquele contexto.

A remoção incluiu também um plugin inteiro — diretório, skill e referências —,
feito sob medida para o trabalho de um cliente específico e sem uso fora dele.
Ele já não constava do catálogo de distribuição; agora também não está mais na
árvore.

**O histórico do git ainda contém as versões anteriores desses arquivos.** Remover
conteúdo da árvore não remove o conteúdo dos commits já publicados, e este
repositório é público — qualquer pessoa com o clone alcança as versões antigas.

### Uma entrada de config ficou de propósito

O `plugins/bootstrap/config/manifest.json`, na linha 271, continua listando em
`skills.permitidas` uma skill com o mesmo nome daquele plugin. É outra coisa:
essa entrada descreve a skill standalone instalada na pasta pessoal do usuário,
não o plugin que saiu daqui. Foi mantida intacta de propósito — o `check_skills`
do conformance acusa como desvio toda skill instalada que não esteja na lista,
então tirar a entrada faria o relatório passar a reclamar de uma skill que está
instalada e é legítima.

## Até onde a limpeza foi

A limpeza cobriu o material **distribuído** — `plugins/` e `_shared/`, que é o que chega
na máquina de quem instala — e, nesta rodada, também o registro de trabalho que o repo
carregava rastreado: as atas de sessão em `.claude/ata/`, os handoffs na raiz de
`.claude/`, o histórico de achados em `.claude/.project-doc/`, os planos em
`.claude/plans/` e a saída do grafo em `graphify-out/`.

Esses arquivos **continuam no disco** de quem trabalha aqui; o que mudou é que saíram do
índice do git e entraram no `.gitignore`. São 84 no total — 30 atas, 40 arquivos de
`graphify-out/`, 8 planos, 3 handoffs e 3 arquivos de `.claude/.project-doc/`:

```
$ git ls-tree -r --name-only ff32947 | wc -l     # antes
     335
$ git ls-files | wc -l                          # depois
     251
$ git ls-tree -r --name-only ff32947 | grep -cE '^(\.claude/(ata|plans|\.project-doc)/|\.claude/HANDOFF.*\.md|graphify-out/)'
84
```

**Por que a decisão inverteu:** a versão anterior deste documento mantinha esses
diretórios rastreados de propósito, como registro de como as decisões foram tomadas.
Isso valia enquanto o repo era só do dono. Ata de sessão, handoff e grafo carregam nome
de projeto e de cliente, e quem instala não ganha nada com eles — então, num repo que
sai da mão do dono, deixaram de ser limite aceitável e passaram a ser conteúdo a
destrackear.

### O que sobrou — medido depois da remoção

```
# 1º padrão: os 3 nomes de cliente/sistema privado + o caminho absoluto da máquina do dono
$ git grep -nliE '<nomes-de-cliente>|/Users/<conta-do-dono>' -- .claude/
.claude/LIMITES-CONHECIDOS.md
.claude/docs/data-stores.md
.claude/docs/runtime.md
# (o .claude/hook-contract.baseline.json saía aqui; hoje não sai — o campo `root`,
#  que gravava o caminho absoluto da máquina, foi removido e o arquivo voltou ao git)

# 2º padrão: o nome do plugin que era feito sob medida para um cliente
$ git grep -ciE '<nome-do-plugin-de-cliente>' -- .claude/ graphify-out/
.claude/LIMITES-CONHECIDOS.md:1
```

Antes da remoção eram 34 e 15 arquivos (`git grep -l … HEAD -- .claude/`, contra o
commit `ff32947`). Do que restou:

- **LIMITES-CONHECIDOS.md** é este arquivo. Ele casava nos dois greps porque os comandos
  colados acima traziam os termos literais — aqui eles estão mascarados, e não tem nada de
  terceiro nele.
- **docs/data-stores.md** casa só pelo caminho absoluto da máquina do dono
  (`/Users/<conta-do-dono>/…`), citado como proveniência dos hooks.
- **hook-contract.baseline.json** saiu desta lista: o campo `root`, que gravava esse
  caminho, foi removido do arquivo, e com isso ele voltou a ser rastreado.
  [confirmado: `grep -c '/Users/' .claude/hook-contract.baseline.json` → 0]
- **docs/runtime.md** casa pelo caminho e por uma menção a um diretório de estado de
  outro workspace, dentro de uma nota de medição do plugin do codex.

`graphify-out/` não aparece mais em nenhum dos dois: saiu inteiro do índice.

**O histórico do git continua carregando tudo.** Sair do índice não sai dos commits já
publicados — quem clonar este repositório alcança todas as versões anteriores dos 84
arquivos. Está registrado aqui como limite aceito, não como descuido.

## Decisão pendente

Reescrever histórico de repo público é decisão do dono; não executada.

### Definir o autor do git antes do primeiro commit do repo novo

Não executado aqui de propósito: o repositório novo ainda não existe, e `git config`
sem repositório só teria efeito global. Fica registrado como pendência.

Neste repositório, praticamente todo commit nasceu com o endereço pessoal nos
metadados de autoria:

```
$ git rev-list --count HEAD
286
$ git log --format=%ae | sort | uniq -c | sort -rn
 285 <e-mail pessoal do dono>
   1 <id>+<conta>@users.noreply.github.com
```

Não foi escolha: não há identidade local no repo, então ele herda a do
`~/.gitconfig` da máquina — e o repositório novo herdaria a mesma:

```
$ git config --local user.email    # sem saída, sai 1 — nenhuma sobrescrita local
$ git config --global user.email
<e-mail pessoal do dono>
```

O endereço foi mascarado de propósito nas duas saídas acima: a saída crua é real,
só o endereço não é reproduzido aqui.

Autoria fica gravada no objeto do commit; mudar depois exige reescrever o
histórico — que é exatamente a decisão pendente registrada acima. Então, **antes
do primeiro commit** do repositório novo, dentro dele:

```
git config user.email tools@viustudio.com.br
git config user.name  "<nome a usar no repo público>"
```

Feito depois do commit inicial, o defeito de hoje volta a existir e volta a ser
irremovível sem reescrever histórico.
