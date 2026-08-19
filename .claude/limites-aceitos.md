# Limites aceitos

Cada item aqui é uma coisa que a régua reprova e que a gente decidiu **não**
consertar, com o motivo escrito. Sem este arquivo o desacordo vira ou dívida
esquecida ou conserto reflexo — os dois piores que a decisão registrada.

## As 82 páginas geradas antes da régua existir

**Decidido em 2026-08-03**, no fechamento do plano `2026-08-03-a-constituicao-se-cumpre`.

- A auditoria mede 100 páginas em `.claude/visual/` e reprova 82.
- As violações somam 1281 de duas-frases, 1042 de teto e 16 de conectivo.
- Nove delas foram digitadas à mão e nenhum gerador as alcança.
- A maioria é página de plano já encerrado, que ninguém vai reler.

**A régua passa a valer para página nova**, que é onde a constituição precisa
morder. As duas páginas do único plano aberto já passam limpas — verificado no
mesmo dia, então não sobrou nada a regenerar.

Como reconferir a qualquer momento:

```
$ python3 plugins/visual/lib/regua_audit.py paginas
📊 100 páginas · 82 com violação
    • duas-frases — duas frases no mesmo bullet: 1281
    • teto-140 — teto de 140 caracteres: 1042
    • conectivo — abre com conectivo de continuação: 16
    • ❔ 9 páginas sem perfil de gerador — digitada à mão, fora do alcance

✅ plano-2026-08-03-a-constituicao-se-cumpre-approve.html · árvore de plano
✅ plano-2026-08-03-a-constituicao-se-cumpre-track.html · árvore de plano
```

O que **revoga** este limite: uma página antiga voltar a ser lida para decidir
alguma coisa. Aí ela é regenerada, não lida como está.

⚠️ **O número aqui é um retrato, e retrato envelhece.** Em 2026-08-03 ele já
divergiu no mesmo dia: a auditoria passou a acusar 83 de 100, e a página a mais
era a gerada naquela tarde. Não era regressão — o auditor media o placeholder que
o próprio `visual_page.py` injeta na terceira opção de decisão, e esse texto era
duas frases. Corrigido em `visual_page.py:485`, o número voltou a 82 de 100.

**Nenhum verificador lê este arquivo.** Diferente dos retratos de `stop-budget` e
de vendoring, que o gate de commit compara, este só é lido por gente — um limite
vencido não é acusado por ninguém. É dívida conhecida, não descuido.

## Três geradores sem página no disco para medir

O veredito da auditoria marca `fallow/lib/report.py`, `slides/lib/md2deck.py` e
`branches/lib/branch_state.py` como em desacordo por motivos diferentes de prosa:

- Os dois primeiros não têm nenhuma página deste gerador no disco.
- O terceiro só tem página de 2026-07-28, anterior à mudança.

**Não é violação de forma — é ausência de amostra.** O conserto certo é gerar uma
página por esses caminhos e medir, não editar o gerador às cegas.

**O que revoga:** uma página nascer por qualquer um dos três caminhos — aí ela é medida
pela régua normal e o gerador sai desta lista.

## O histórico do git carrega tudo que já saiu da árvore

Limpar o índice não limpa os commits publicados — quem clona alcança as versões
anteriores. O que **revoga** este limite: o dono decidir reescrever o histórico,
o que segue não executado.

## Todo commit carrega o endereço do projeto

`git log --format='%ae' | sort -u` devolve a conta de contato do projeto em todos
os commits (não a pessoal). A régua da casa permite endereço de contato do projeto;
fica como registro. Lição para repositório novo: gravar a identidade local desejada
antes do primeiro commit. O que **revoga**: a mesma reescrita de histórico acima.

## Nota de reconferência (2026-08-14)

O comando de reconferência mudou de forma e de universo desde o retrato original:
hoje `python3 plugins/visual/lib/regua_audit.py paginas` devolve
"🔍 Régua de forma · 202 páginas · 2417 violações", sem a linha "N com violação"
nem a lista de páginas limpas. O retrato de "82 de 100" é histórico; a régua segue
valendo do artefato novo em diante, e o número vivo sai do comando acima.

## Dois falso-positivos do detector de ato-do-dono na auditoria do plano

**Decidido em 2026-08-16**, na revisão pré-largada da corrida 11. O detector
`ATO_DO_DONO` (`plugins/project-skills/lib/auditoria_plano.py`) casa por palavra
(`aprova|publica|…`) e acusa dois passos onde a palavra não é ato do dono:

- **F7.1** — o pronto diz "o push do conserto sai publicado"; o push é do motor,
  autorizado na largada de 2026-08-13, e o passo está `done` com prova. Reescrever
  pronto de passo fechado mudaria registro histórico.
- **F13.2** — "o doc-aprovar grava conjunto-sig" cita o programa do rito
  (`hooks/doc-aprovar.sh`) pelo nome; o pronto é provável por suíte, sem o dono.

**O que revoga:** o detector aprender a pular passo `done` e nome de programa —
aí os dois saem daqui e voltam a ser medidos.

## Duas jornadas que o plano dos quatro itens não se propõe a cobrir

**Decidido em 2026-08-16**, na mesma revisão. O nível 2 da auditoria acusa
"Criar um aplicativo dentro de um organismo que já existe" e "Extinguir ou fundir
um plugin" como jornadas que nenhuma funcionalidade atende. O plano
`2026-08-12-os-quatro-itens` é parcial por definição — tripé, rigor do plano,
completude e CI verde — e essas duas jornadas não pertencem a nenhum dos quatro.

**Quem cobra o todo é a completude da união dos planos** (`completude.py`), não a
auditoria de um plano só — a distinção está escrita no cabeçalho de
`auditoria_plano.py`. **O que revoga:** um plano futuro cobrir essas jornadas, ou
o dono cortá-las do `journeys.md` pelo rito.

## A colheita do lixeiro no Windows — 4 checks vermelhos, conserto bloqueado por falta de dado

`bash plugins/lixeiro/hooks/test_lixeiro_hooks.sh` fecha verde no macOS (26 ok) e reprova
no Windows em quatro checks do encerramento — medido no run 31890249824 do CI:

```
✗ o fim de sessão encerrou o servidor anotado
✗ o fim de verdade ainda encerra
✗ a suíte PARADA foi encerrada
✗ registro de auditoria
lixeiro-hooks: 16 ok, 7 falhas
```

**A causa está medida, e o conserto é que não está.** O lixeiro só encerra o processo cuja
pasta de trabalho anotada bate com a que o sistema reporta. No Windows as duas nunca casam:
a suíte anota o caminho do shell (`/tmp/tmp.X/projeto`) e o sistema reporta o do Windows
(`C:/Users/RUNNER~1/AppData/Local/Temp/tmp.X/projeto`). Zero candidatos ⇒ nada é encerrado
⇒ os quatro checks caem, e as vizinhas que exigem SOBREVIVÊNCIA passam de graça, o que é
pior: elas passam sem medir nada.

**Por que é limite e não conserto:** falta o dado, não a lógica. Casar os dois formatos
exige uma segunda fonte de pasta de trabalho no Windows, e qual deve ser é decisão de
arquitetura — o substituto testado nesta sessão reproduz três dos quatro checks, e o quarto
(*a suíte PARADA foi encerrada*) muda de resultado sem explicação medida. Consertar sem
essa decisão é chutar, e o chute já custou uma rodada.

**O que revoga:** o dono cravar de onde tirar a pasta de trabalho no Windows — e aí o
conserto é mecânico e os quatro fecham.

**Enquanto valer:** a colheita automática não é confiável no Windows. Quem roda lá encerra
processo aberto pelo agente à mão (`/faxina`), e a suíte segue vermelha lá de propósito, não
por descuido.
