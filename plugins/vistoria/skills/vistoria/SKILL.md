---
name: vistoria
description: Revisa os arquivos de instrucao deste marketplace — skills, hooks e cobradores — e devolve uma pagina de achados com a prova colada, onde o dono marca o que vira plano. Roda os cobradores que ja existem no repo num comando so, soma as lentes medidas (assert que congela frase morta, script de hook que ninguem chama) e recusa na porta o achado sem prova. Use quando o usuario disser vistoria, pedir uma revisao dos arquivos de instrucao, perguntar o que esta apodrecido nas skills e hooks, ou quiser transformar os achados em passos ticaveis.
---

# Skill: vistoria

A vistoria olha para o próprio marketplace e pergunta uma coisa só: **onde a instrução
escrita já não corresponde ao programa que a cobra?** Ela não opina. Cada item que ela
devolve carrega o trecho cru que o cobrador viu — sem esse trecho o item não sai fraco,
não sai.

Rode sempre da raiz do repositório.

## 1 · Medir

```bash
python3 plugins/vistoria/lib/medidor.py            # resumo por cobrador
python3 plugins/vistoria/lib/medidor.py --json     # a lista de achados
```

Um comando roda os cobradores que já existem no repo e transforma as saídas diferentes
deles na MESMA coisa: uma lista de achados. Cobrador que quebra sai do JSON e aparece no
resumo como *não medido* — medição incompleta não derruba a rodada, mas também não some.

## 2 · As lentes medidas

Duas lentes não têm cobrador pronto e moram aqui. As duas comparam contra um retrato
(`--gravar-retrato` congela o estado de hoje) e reprovam o que PIORA:

```bash
python3 plugins/vistoria/lib/suite_congela.py   # assert que espera frase que nada escreve
python3 plugins/vistoria/lib/fio_morto.py       # script de hook que ninguém registra
```

Saiu item NOVO? Ele vira achado no formato de `lib/achado.py` — `cobrador` é
`suite-congela` ou `fio-morto`, `onde` é o `arquivo:linha` impresso e `prova` é o trecho
impresso, verbatim. Nada novo além do retrato: nada a acrescentar.

## 3 · A página

```bash
python3 plugins/vistoria/lib/medidor.py --json \
  | python3 plugins/vistoria/lib/pagina.py --dir .claude/vistoria
```

Sai o caminho de um HTML em `.claude/vistoria/` — nunca em `/tmp`. O `--dir` é obrigatório:
destino adivinhado cai no cache do plugin quando ele está instalado. Um checkbox por achado,
a prova colada embaixo dele. Abra e mostre ao dono: a decisão é dele, e decidir sem a prova
na frente é o que esta ferramenta não faz.

Se você juntou achados das lentes medidas, monte o JSON completo (medidor + lentes) e passe
esse arquivo pela `pagina.py` no lugar do pipe.

## 4 · Validar antes de mostrar

```bash
python3 plugins/vistoria/lib/achado.py --validar <arquivo.json>
```

Sai 0 e o lote é achado de verdade. Sai 1 e o stderr diz qual item está pela metade:
campo faltando, campo vazio, gravidade fora da escala — e, no achado de LEITURA, prova sem
o **par** de citações `arquivo:linha`. Página não abre com lote reprovado.

## 5 · Do checkbox ao plano

```bash
python3 plugins/vistoria/lib/plano_saida.py --dir .claude/plans < marcados.json
```

Os achados que o dono marcou entram, e sai um plano ticável em `.claude/plans/`, um passo
por achado, com o critério verificável escrito no `pronto`. Daí em diante o plano só é
marcado — nunca reescrito.

## As pautas

Em `references/`, para quando a leitura por agente for usada:

- `pauta-leitor.md` — as perguntas fechadas sobre um pedaço de leitura, cada SIM obrigando
  o par de trechos literais;
- `pauta-cruzamento.md` — o defeito que só aparece com dois pedaços juntos, cruzando as
  fichas dos leitores e nunca os textos inteiros;
- `pauta-verificador.md` — o outro agente, que recebe só o achado e os arquivos citados, e
  tenta DERRUBAR a acusação.

**O leitor por agente está congelado por decisão do dono.** A rodada de hoje é a das lentes
medidas: os cobradores mais as duas lentes acima. Não invente leitura por agente sem o dono
pedir.
