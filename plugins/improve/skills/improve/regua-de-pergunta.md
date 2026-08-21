<!-- FONTE: _shared/regua-de-pergunta.md. NÃO editar as cópias vendoradas que
     moram ao lado de cada SKILL.md — edite aqui e rode scripts/sync-shared.sh.
     Quem cobra o texto em todas as cópias: _shared/test_regua_de_pergunta.py. -->

# Por onde a pergunta chega — régua única de toda skill que pergunta ao dono

A instrução da skill diz **o que** perguntar. Quem escolhe **por onde** é o usuário, e são dois canais:

- **Padrão — a rodada inteira numa página, em múltipla escolha.** A rodada de perguntas vira uma
  página de decisão: cada pergunta é um item, com as opções em rádio e **um campo livre embaixo**
  para o que não cabe nas opções. A recomendação entra marcada como sugestão, nunca como
  resposta dada. É um canal só de ida e volta: o usuário responde a rodada inteira de uma vez,
  em vez de gastar um turno por pergunta.
  - **Como montar:** se a skill de apresentação visual estiver entre as suas skills disponíveis,
    invoque-a **pelo nome** e peça uma página de decisão com um item por pergunta. Não monte
    caminho de arquivo para dentro de outro plugin, e não rode programa de outro plugin: se a
    skill não estiver disponível na máquina, o canal padrão simplesmente não existe ali — caia
    no canal alternativo e siga.
  - **Como colher:** a resposta volta pelo estado que o daemon dessa página grava em disco, em
    `~/.claude/visual-state/latest.json`. Leia de lá; não peça ao usuário para copiar e colar.
  - **Pergunta sem apoio não vale.** Toda opção mostra o conteúdo concreto de que ela fala — o
    trecho literal, o número com procedência. O usuário não adivinha o seu contexto.

- **Alternativa — uma por vez, na ferramenta nativa de pergunta.** Mesma fila, mesma ordem,
  só que servida pergunta a pergunta no próprio CLI.

**Quem escolhe é o usuário.** Na primeira rodada, ofereça os dois e use o que ele pedir; ele pode
trocar de canal a qualquer momento, e a troca vale da rodada seguinte em diante. Sem escolha dita,
use o padrão.

## Antes de perguntar: o registro de decisões já seladas

**Pergunta repetida é falha do processo, não pedido novo.** A mesma pergunta parou quatro corridas
em dias diferentes, e a resposta ("tudo que puder decidir no final, decido no final") já estava dita.
Por isso **todo papel que vai perguntar — o pré-check de largada, o motor do /sprint, a casca —
consulta o registro ANTES de levar qualquer coisa ao dono**, e a linha achada É a resposta: a
pergunta morre ali, com a fala dele citada literal e a data.

O registro é `.claude/decisoes-seladas.md` na raiz do projeto: uma linha por decisão, com a
frase-chave inteira NA MESMA LINHA (partida em duas, o `grep` não acha). Quem lê e escreve é
`lib/decisoes_seladas.py` do plugin **project-skills**:

`<resolve-plugin>` é o caminho do `resolve-plugin.sh` vendorado no plugin que carregou ESTA
skill — procure o arquivo com esse nome na pasta do próprio plugin (`hooks/` ou a pasta da
skill). Vazio ou ausente = project-skills fora desta máquina: siga sem o registro, dizendo isso.

```bash
SELADAS="$(bash "<resolve-plugin>" project-skills lib/decisoes_seladas.py)"
python3 "$SELADAS" consultar <raiz> "<a pergunta que você ia fazer>"   # saída 1 = nenhuma, pergunte
python3 "$SELADAS" indice    <raiz>                                    # o registro inteiro
```

**Decisão nova entra no registro na hora em que o dono responde** — na mesma volta, não no fim:

```bash
python3 "$SELADAS" selar <raiz> --fala "<a fala literal dele>" --fonte "<onde foi dita>"
```

Registro ausente não trava nada: sem arquivo, a consulta devolve vazio e a pergunta segue.

## A aposta que vai junto com a pergunta

Campo em branco obriga o dono a compor a resposta do zero; palpite errado ele derruba numa linha, e
derrubar é mais rápido e mais honesto do que redigir. Por isso **toda pergunta vai com o palpite na
mesa e a confiança em percentual** — como cada skill nomeia e formata esse palpite é dela, mas estas
três travas valem em todas:

- **O `%` é obrigatório** — "confiança alta" e "meio certo" não são confiança, são impressão. O
  número existe para dizer ao dono onde gastar atenção: **abaixo de 50%** é chute que ele precisa
  corrigir; **acima de 80%** é conferência rápida. Sem número, ele lê tudo com a mesma desconfiança.
- **Palpite sem pista visível não existe.** Ele nasce do insumo que você já leu, e a pista vai junto
  — `arquivo:linha`, ou o trecho literal.
- **Confiança de 95% não vira resposta do dono.** Palpite que ele não confirmou continua sendo
  palpite: silêncio nunca é aprovação, e o que fica registrado é o que ELE respondeu, não o que você
  apostou. Se não há pista para apostar, pergunte em branco e diga que não tem palpite.
