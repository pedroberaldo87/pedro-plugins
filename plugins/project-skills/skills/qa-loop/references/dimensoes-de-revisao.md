<!-- FONTE: _shared/dimensoes-de-revisao.md. NÃO editar as cópias vendoradas
     (plugins/*/skills/*/references/) — edite aqui e rode scripts/sync-shared.sh.
     Quem cobra o texto nas duas cópias, e que a skill aponte em vez de repetir:
     scripts/test_dimensoes_de_revisao.py. Estes caminhos são deste repositório e
     por isso vivem num comentário: na máquina de quem instala eles não existem,
     e comando que não roda como está escrito viola o Artigo 8. -->

# O tripé da revisão — o mínimo que toda revisão mede

> Contrato único. Quem revisa **aponta para este arquivo**; nenhum `SKILL.md` repete a
> lista, e nenhum enumera documento de projeto por nome.

Toda revisão deste marketplace — a do ciclo de implementação (por tarefa, por bloco, por
onda) e a do `/qa-loop` — mede **os três pés abaixo**. Não é ordem de preferência: é
mínimo. Revisão que não mediu um deles **declara que não mediu**; nunca passa calada.

O motivo de existirem três, e não um: cada pé enxerga um defeito que os outros dois
deixam passar inteiro.

---

## Pé 1 · Qualidade — o que está escrito está certo?

Bug, regressão, contrato quebrado entre as pontas, caso de borda, segurança. É o pé que
todo mundo lembra de medir.

**Checklist de dimensões** — um revisor cobre todas como lista, nunca um agente por
dimensão:

| # | Dimensão | A pergunta |
|---|---|---|
| 1 | arquitetura | as fronteiras que existem são as que a obra precisa? |
| 2 | backend | dado, estado, borda e falha |
| 3 | frontend | o que a pessoa vê, e o que acontece quando não carrega |
| 4 | contratos fullstack | as duas pontas concordam sobre o mesmo formato |
| 5 | correção | faz o que diz, inclusive no caminho infeliz |
| 6 | UX | o caminho da pessoa, não o caminho do código |
| 7 | **cobertura por finalidade** | ver o Pé 2 — é a dimensão que o Pé 2 injeta aqui |

**O que NÃO conta como este pé:** lint, type-check, teste vermelho. Isso é objetivo e
absoluto, vive no portão mecânico da própria skill, e tratá-lo como "achado de severidade
rebaixável" é o erro que o portão existe para matar.

---

## Pé 2 · Cobertura por finalidade — o que foi construído tem como falhar calado?

**Para cada finalidade que a spec pede, existe teste que MORDE** — que fica vermelho se
aquilo quebrar. A pergunta é sobre a finalidade, nunca sobre a linha ou a porcentagem:
cobertura de linha alta com finalidade descoberta é o retrato que engana.

Duas metades, e as duas são obrigatórias:

- **O teste que EXISTE serve?** Os cinco antipadrões (contrato em `antipadroes-de-teste.md`,
  ao lado deste arquivo) julgam isto — teste que passa com e sem a mudança, que espera
  texto que o código nunca escreve, que só anda no caminho feliz, que mede a coisa errada,
  ou que dispara em segundo plano e não espera o resultado.
- **O teste que NÃO existe.** Finalidade sem rede nenhuma **não cai em antipadrão** — não
  há teste para julgar. Sem este pé escrito, código sem teste algum atravessa a revisão
  inteira sem cair em dimensão nenhuma, e o portão mecânico confirma o engano: ele roda a
  suíte que há, e suíte que não cobre a finalidade nova fica verde **exatamente por não a
  cobrir**.

Finalidade sem rede é achado de **implementação** — o conserto é o teste, não o código — e
entra pela rubrica de severidade normal da skill, sem faixa própria.

**A prova de que o teste morde é a MUTAÇÃO, não a leitura.** Quando a trava é de segurança
(o que impede o pior desfecho do mecanismo), desligue-a numa cópia e exija que a suíte
acuse. Trava cuja remoção mantém a suíte verde é trava sem cobertura, e o defeito que ela
previne volta sem que nada perceba.

---

## Pé 3 · Coerência com a régua — a obra respeita o que o projeto acordou?

**Rode o `doc-load` e julgue contra TUDO que ele listar como régua**, citando o documento
e a passagem violada.

**Este arquivo não enumera documento de projeto, de propósito.** Quem sabe o que vale como
régua hoje é o programa (`lib/doc_load.py` do plugin `project-skills`), que distingue:

- **lei** — vale com `ready` **ou** `approved`; é o contrato permanente, não uma etapa;
- **acordo** — só com `approved`, e sai como *reaberto* quando o corpo mudou depois do
  de acordo (ninguém aprovou o texto que está lá);
- **mapa minerado** — serve para se situar, **nunca** para reprovar: descreve o que
  existe, não o que deveria existir.

Enumerar os arquivos em prosa foi o defeito que este marketplace carregou até 2026-08-12:
uma skill citava quatro documentos e o programa já listava onze. Nenhum dos dois lados
ficava errado sozinho — é a divergência silenciosa do `patterns.md` §1.6a, exatamente o
que o `doc-load` existe para matar.

**Ausência não é achado.** Projeto sem régua não tem este pé; o revisor diz isso e segue
com os outros dois. E **régua ausente nunca vira aprovação por omissão**.

**A lei é fixada na primeira volta.** Missão longa congela a marca que o `doc-load`
devolve e mede contra ela até o fim: lei alterada no meio do caminho vira aviso ao dono,
nunca troca silenciosa do critério do julgamento.

---

## Os três pés no artefato PLANO

Revisão não é só de código. Quando o que está sob julgamento é um **plano** — a spec
aprovada virada em tarefas ticáveis —, os três pés continuam sendo os mesmos três; o que
muda é o que cada um olha. Um plano defeituoso não acusa nada ao ser gravado: ele só cobra
o preço depois, quando a tarefa é executada e ninguém consegue dizer se ficou pronta.

| Pé | No plano, isto é |
|---|---|
| 1 · qualidade | cada tarefa tem `pronto` **verificável** (um comando, um arquivo, um número), a ordem das dependências existe de verdade, e nenhuma tarefa depende de coisa que nenhuma outra entrega |
| 2 · cobertura por finalidade | **todo requisito da spec tem tarefa**, e toda tarefa rastreia até um requisito. O que falta aqui é o análogo exato do teste que NÃO existe: requisito sem tarefa não cai em nenhum defeito de tarefa, porque não há tarefa para julgar |
| 3 · coerência com a régua | cada citação do plano (`ancora`, `jornada`, `peca`, `passo`) resolve num item que a régua de fato tem. Citação inventada é o defeito que a auditoria do plano já nomeia (`artigos_inexistentes`, `pecas_inexistentes`) |

**O `pronto` é literal, e proxy é o antipadrão daqui.** Critério que não pode ser cumprido
como está escrito não vira um substituto "equivalente" na hora da execução: trocar critério
é decisão do dono. O plano que aceita proxy fecha tarefa sem entregar o que pediu.

Vale a mesma regra do topo: revisão de plano que não mediu um dos pés **declara que não
mediu**.

---

## Como esta lista muda

Dimensão nova entra **na fonte**, e chega às skills pelo vendoring — nunca digitada na
cópia. Editar a cópia à mão é o drift que este arquivo existe para impedir, e há programa
cobrando os dois lados: que a cópia esteja idêntica à fonte, e que cada consumidor
**aponte** para o contrato em vez de repetir o texto. Os nomes desses cobradores estão no
comentário do topo — eles vivem no repositório do marketplace, não na sua máquina.
