---
name: reentrada
description: O caso da manhã — o dono volta, o run do /sprint morreu de madrugada, e um comando rearma o laço do ponto onde parou em vez de largar do zero. Lê o desfecho do último run no ledger, classifica pela lib de retomada (segue-no-motor, conserta-e-relança ou espera-dono) e aponta os blocos da skill do sprint que relançam. Use quando o usuário disser "/reentrada", "retoma o sprint", "o sprint morreu, continua", "rearma o laço", ou ao voltar a uma sessão cujo motor não está mais vivo.
---

# reentrada — rearmar o laço do ponto onde parou

O motor do `/sprint` morreu — de madrugada, por limite de sessão, por processo
derrubado — e o dono voltou. Largar do zero joga fora o que o ledger já sabe:
onde a corrida parou, em que pedra, e quantas vezes na mesma. Esta skill lê esse
saber do disco e devolve UMA ação. Ela não relança por conta própria coisa que é
do dono, e não decide de memória: todo campo sai de `lib/retomada.py` sobre o
último run do ledger.

**Pré-condição:** o motor NÃO está mais vivo. Motor de pé se observa com
`/monitorar`, não se reentra — reentrar com motor vivo é disparar dois motores
na mesma missão.

## 1) Um comando — o desfecho do último run vira ação

No bloco abaixo, `<a raiz do projeto>` é a raiz do repositório da missão (a
mesma que o sprint usou de `REPO_ROOT`) e `<o plano da missão>` é o caminho do
plano que o sprint recebeu (o `PLAN_PATH` — é a chave `missao` das linhas do
ledger). Cada bloco de comando é uma chamada à parte: o bloco define tudo que
usa, nada chega de outro bloco.

```bash
# A LEITURA DA MANHÃ — ledger → retomada.py → {desfecho, acao, causa, evidencia}
export REPO_ROOT="<a raiz do projeto>"
PLAN_PATH="<o plano da missão>"
LEDGER="$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/ledger_corridas.py)"   # artigo8-ok: o harness define CLAUDE_PLUGIN_ROOT ao rodar skill de plugin
RETOMADA="$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/retomada.py)"   # artigo8-ok: o harness define CLAUDE_PLUGIN_ROOT ao rodar skill de plugin

# O gate do relance vem ANTES: a mesma causa parando de novo é caso do dono (F23.6),
# e quem o declara ao classificador é o --caso — nunca o stopReason sozinho.
python3 "$LEDGER" relance --project-root "$REPO_ROOT" --missao "$PLAN_PATH"
RELANCE=$?
CASO=""
[ "$RELANCE" -eq 3 ] && CASO="causa-repetida"

# O último run do ledger vira a entrada do classificador. Largada pendurada em
# em-curso/ é corrida que morreu por fora e a colheita ainda não fechou (teto de
# 12h) — o desfecho dela é conhecido por observação, não por palpite.
python3 "$LEDGER" le --project-root "$REPO_ROOT" | python3 -c '
import glob, json, os, sys
runs = json.load(sys.stdin)
pend = glob.glob(os.path.join(os.environ["REPO_ROOT"], ".claude", ".sprint", "em-curso", "*.json"))
if pend:
    print(json.dumps({"stopReason": "morta-por-fora", "blockers": []}))
elif runs:
    u = runs[-1]
    causa = u.get("causa")
    print(json.dumps({"stopReason": u.get("desfecho"),
                      "blockers": [{"what": causa}] if causa else []}))
else:
    sys.exit("ledger vazio: nao ha run para retomar — largada nova e pela skill do sprint")
' | python3 "$RETOMADA" --run - ${CASO:+--caso "$CASO"}
```

A saída são os quatro campos — `desfecho`, `acao`, `causa`, `evidencia` — e a
`acao` é uma de três, lista fechada do classificador (F23.2/F23.5). Imprima os
quatro para o dono antes de agir.

## 2) As três ações — e os blocos do sprint que as cumprem

A skill do sprint é FONTE de leitura: os blocos abaixo vivem em
`skills/sprint/SKILL.md` e são apontados pelo título, nunca copiados — cópia
defasa no primeiro bump do sprint. Abra a seção citada e execute o bloco de lá.

**`segue-no-motor`** — a casca não conserta nada: relança igual, do ponto onde o
plano está. Relançar é a largada de sempre: a seção
"### O sinal que arma o gate (obrigatório, e é a PRIMEIRA coisa)" da SKILL.md do
sprint — o bloco 1 arma o sinal e grava a largada no ledger (a marca
"A LARGADA vai para o disco"), e no fim vale o bloco
"2) NO RETORNO da chamada", que apaga o estado
e solta a reserva. O motor acha sozinho as tarefas abertas do plano; ponto de
partida não se dita à mão.

**`conserta-e-relanca`** — relançar igual repete a mesma parada pelo mesmo
preço. Antes da largada: apurar a causa com prova de comando e desafiador (as
regras estão na mesma seção da largada do sprint, e nenhuma se afrouxa aqui),
consertar, commitar o conserto, gravar a parada pelo bloco
"A PARADA vai para o disco" da SKILL.md do sprint — e só então relançar pela
mesma largada do parágrafo acima. `morta-por-fora` e desfecho que o inventário
não conhece caem aqui de propósito: investigar antes de relançar, nunca inventar.

**`espera-dono`** — não relança. A decisão não é do laço: apresente ao dono a
`causa` e a `evidencia` que o comando imprimiu, como pendência, e pare. Se a
parada ainda não tem linha no ledger, grave-a antes de parar (o mesmo bloco
"A PARADA vai para o disco", com `sem-conserto` e `sem-commit` — parada do dono
não tem conserto para gravar).
