# Pauta do verificador — quem tenta derrubar o achado

O leitor acusa. O verificador é **outro agente**, e a tarefa dele é a oposta: tentar
DERRUBAR o achado. Achado que sobrevive a essa tentativa sai rotulado `CONFIRMADO`;
achado que cai sai `derrubado` com o motivo escrito.

**O que o verificador recebe.** Só duas coisas:

1. o achado, no formato de `lib/achado.py` (`cobrador`, `regra`, `gravidade`, `onde`,
   `o_que`, `prova`);
2. os arquivos citados nele, lidos do disco agora.

**O que o verificador NÃO recebe.** O contexto do leitor — o pedaço de leitura inteiro, a
ficha, as outras perguntas da pauta, o raciocínio que produziu o achado, o que o leitor
respondeu antes. Se o verificador enxergasse o contexto do leitor, ele herdaria a
convicção do leitor junto, e a segunda opinião viraria eco da primeira. Ele chega frio,
com a acusação e as provas na mão, e nada mais.

**Regra de forma.** O verificador não emite achado novo, não conserta o achado, não
melhora a redação. Ele devolve um veredito por achado, e nada além disso.

---

## Os três testes de derrubada

Aplicados nesta ordem. O primeiro que falhar já derruba — não se continua.

### V1 · A citação existe mesmo no arquivo citado?

Cada citação de `onde` e de `prova` vem no formato `arquivo:linha: <trecho literal>`.
Abra o arquivo, vá até aquela linha e compare o trecho. Se o arquivo não existe, se a
linha não existe, ou se o trecho não está nela, o veredito é **derrubado**, motivo
`citação não encontrada`, nomeando a citação que falhou. Achado bem formado — que passa
inteiro pelo validador de `lib/achado.py` — cai aqui do mesmo jeito: o schema garante que
existe prova colada, nunca que a prova é verdadeira.

### V2 · O programa acusado recusa mesmo?

Quando o achado acusa um programa (hook, guard, script) de bloquear o que a instrução
manda, não basta ler o programa: **rode-o** com a entrada que a instrução manda passar e
veja o código de saída. Saída zero — o programa deixa passar — derruba o achado, motivo
`o programa citado não recusa`. Saída diferente de zero confirma a recusa.

### V3 · As duas pontas falam do mesmo objeto?

O achado de incoerência cola duas linhas. Se elas tratam de objetos diferentes (arquivos,
comandos ou eventos distintos), não há contradição, e o veredito é **derrubado**, motivo
`pontas sobre objetos diferentes`.

---

## O molde do veredito

```json
{
  "regra": "<a regra do achado julgado>",
  "onde": "<o onde do achado julgado>",
  "veredito": "CONFIRMADO",
  "motivo": "<vazio quando CONFIRMADO; o motivo da queda quando derrubado>"
}
```

Quem cobra esta pauta é `lib/test_verificador.py`, que planta um achado com citação
inexistente (tem que cair em V1 com `citação não encontrada`) e submete o achado da
fixture `a` (tem que sobreviver como `CONFIRMADO`, com o `guard.sh` rodado de verdade).
