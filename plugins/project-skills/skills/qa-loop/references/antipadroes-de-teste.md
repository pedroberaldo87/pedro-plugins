<!-- FONTE: _shared/antipadroes-de-teste.md. NÃO editar as cópias vendoradas
     (plugins/*/skills/*/references/) — edite aqui e rode scripts/sync-shared.sh.
     Quem cobra o texto nas duas cópias: _shared/test_antipadroes_de_teste.py. -->

# Os cinco antipadrões de teste — contrato único de `/qa-loop` e `/visual`

Duas instruções mandam testar, e as duas erram pelo mesmo motivo. A do `/qa-loop` manda
**revisar e testar o que foi construído**. A do `/visual` manda escrever, no plano, **como
se prova que um passo terminou**. Quem escreve o critério erra antes de quem escreve o
teste: critério torto faz o teste nascer torto, e o teste só herda o defeito. Por isso a
lista é uma só, e as duas apontam pra ela.

Cada item abaixo já aconteceu neste repositório. Não é catálogo teórico.

## 1 · Passa com e sem a mudança

O teste fica verde antes do conserto e verde depois. Ele não mede nada — só acompanha.

**Como provar que morde:** sabote o código, veja o teste VERMELHO, restaure, veja VERDE.
Teste que nunca ficou vermelho não é prova de nada; é decoração que custa tempo de CI.

## 2 · Espera um texto que o código nunca escreve

A verificação compara com um literal que a implementação não produz — nem hoje, nem nunca.
Ela congela a expectativa de quem escreveu o teste, não o comportamento do programa.

**Caso real:** sete verificações esperavam a frase `3 plano aberto`. O programa não emitia
essa frase em lugar nenhum. **Como evitar:** todo literal comparado tem que existir no
código-alvo — procure a string lá antes de assertar contra ela.

## 3 · Só experimenta o caminho que dá certo

Só o caso feliz é exercitado. O guarda nunca é visto RECUSANDO, então ele pode estar
desligado que a suíte não percebe.

**Caso real:** sem o caso negativo, desligar o guarda passa calado. **Como evitar:** todo
teste de barreira tem par — uma entrada que passa e uma que é barrada, com a barrada
falhando se a barreira sumir.

## 4 · Mede a coisa errada

O teste observa um alvo vizinho do alvo verdadeiro. Verde e vermelho aparecem, mas por
motivo que não é o do requisito.

**Caso real:** um verificador media a biblioteca carregada, não o programa, e acusou quatro
vezes à toa. **Como evitar:** nomeie explicitamente o sujeito da medição e confira que é
ele que a mudança altera.

## 5 · Vai pro segundo plano com espera pelo resultado

O comando é disparado em background e logo em seguida alguém espera a saída dele. Não há
quem entregue essa saída, e a execução fica pendurada.

**Caso real:** já travou execução pra sempre. **Como evitar:** ou roda em primeiro plano
com teto de tempo, ou vai pro segundo plano e ninguém bloqueia esperando o retorno.

---

**Na hora de escrever o `pronto` de um passo** (`/visual`): o critério tem que dizer o
comando que produz o veredito e o que é vermelho — critério que só pede "o teste passa"
autoriza os cinco de cima.

**Na hora de revisar** (`/qa-loop`): cada um destes cinco é finding de implementação, não
observação de estilo. Teste que não morde é defeito, e o conserto é o teste, não o código.
