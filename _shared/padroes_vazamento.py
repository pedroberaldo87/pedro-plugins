#!/usr/bin/env python3
"""Os padrões de disparo que deixam processo para trás. Uma fonte, três consumidores.

POR QUE ESTE ARQUIVO EXISTE, e não três listas parecidas: em 2026-08-08 o mesmo defeito
foi escrito em três lugares no mesmo dia — o cobrador do repositório, a lente do
`/check-skills` e a investigação do `/lixeiro` —, e **em horas eles já divergiam**: um
tinha `disown` na lista, outro não. Padrão de segurança que existe em três cópias vira,
em uma semana, três réguas diferentes cobrando coisas diferentes com o mesmo nome.

O DEFEITO QUE ELES ACHAM, e ele tem três formas:

  entrada herdada    Sem fechar o stdin, o filho recebe o terminal do pai. Comando que
                     resolve perguntar — `git` pedindo credencial é o caso real — espera
                     para sempre, e o teto NÃO o alcança: ele não estourou, está parado.

  neto sobrevivente  O `timeout` mata o filho direto. Se esse filho é um shell, o
                     `python3` que ele abriu fica órfão. Sem grupo próprio não há como
                     alcançá-lo.

  largado de propósito  `nohup`, `setsid` e `disown` soltam o processo do controle. Às
                     vezes é o que se quer (um servidor), e por isso a isenção existe.

CADA PADRÃO TEM DOIS RÓTULOS, e os dois são necessários:
  `curto`  para a lista de achados, onde cabe uma coluna
  `humano` para o relatório ao dono, onde a frase precisa explicar a consequência

    from padroes_vazamento import RISCO, ISENTO
    for padrao, curto, humano in RISCO: ...

FONTE: `_shared/padroes_vazamento.py`. As cópias são vendoradas por
`scripts/sync-shared.sh`; editar a cópia é o que este arquivo existe para impedir.
"""

import re

# `(?![^)]*stdin)` e `(?![^)]*input)`: a chamada que já passa um dos dois controla a
# entrada, e cobrá-la seria mandar escrever código que estoura (`input` e `stdin`
# juntos é ValueError no Python).
RISCO = (
    (re.compile(r"subprocess\.(?:run|Popen|call|check_output|check_call)\s*\("
                r"(?![^)]*stdin)(?![^)]*input)", re.S),
     "python sem fechar a entrada",
     "o disparo não fecha a entrada: o filho herda o terminal e espera para sempre"),

    (re.compile(r"subprocess\.(?:run|Popen)\s*\((?![^)]*start_new_session)", re.S),
     "python sem grupo próprio",
     "o disparo não cria grupo próprio: o teto mata o filho e o neto sobrevive"),

    (re.compile(r"\bos\.(?:system|popen)\s*\("),
     "os.system/os.popen",
     "os.system e os.popen não aceitam fechar a entrada nem criar grupo"),

    (re.compile(r"stdio\s*:[^,}]*['\"]inherit['\"]"),
     "node entrega o terminal",
     "o disparo em node entrega o terminal ao filho"),

    (re.compile(r"(?:^|\n)\s*(?:nohup|setsid)\s"),
     "shell larga o processo",
     "o shell larga o processo de propósito, e ninguém o colhe depois"),

    (re.compile(r"\bdisown\b"),
     "shell solta do controle",
     "o shell solta o processo do controle, e ele deixa de ter dono"),
)

# `['ignore', …]` ou `['pipe', …]` em node é o conserto — stdin fechado, saída visível.
# Sem esta exceção o cobrador acusaria justamente o código já corrigido.
NODE_OK = re.compile(r"stdio\s*:\s*\[\s*['\"](?:ignore|pipe)['\"]")

# A isenção, com o motivo escrito na linha de cima ou na própria linha.
ISENTO = re.compile(r"vaza-ok:")
