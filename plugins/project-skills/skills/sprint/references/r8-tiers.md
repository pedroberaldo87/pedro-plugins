<!-- FONTE DOS DADOS: _shared/r8-tiers.json. Esta é a vista humana; a tabela abaixo é
     GERADA (`python3 _shared/r8_tiers.py check --fix`) e editá-la à mão não muda nada,
     só cria drift que o check acusa. NÃO editar as cópias vendoradas
     (plugins/*/skills/*/references/) — edite o JSON aqui e rode scripts/sync-shared.sh. -->

# Tier por etapa (R8) — contrato único dos motores `/sprint` e `/qa-loop`

Os dois motores (decompõe→executa→revisa do `/sprint`; revisa→planeja→conserta do
`/qa-loop`) usam **a mesma tabela de tier por etapa** e **os mesmos nomes de knob**.
Trocar o tier de uma etapa aqui vale pros dois — é um contrato, não duas listas.

**O valor não mora em nenhum SKILL.md.** Ele mora em `r8-tiers.json`, e chega ao motor
como dado: a casca roda `python3 <skill_dir>/references/r8_tiers.py args` e passa o
resultado no `args` do Workflow, que consulta `args.tiers.<knob>.effort` em vez de um
literal. Cada skill descreve **onde** cada knob entra no motor dela; nenhuma descreve
**quanto** ele vale.

Isso não é purismo — é conserto de um defeito medido. Em 2026-08-03 trocar seis valores
custou 45 substituições em dois arquivos: três saíram invertidas e duas sobreviveram a
dois verificadores, porque o comentário que dizia de qual knob era o número estava longe
demais do número. O check A2 do `release-gate.sh` agora barra literal de effort em
`SKILL.md`; a isenção é `r8-ok:` na linha, com o motivo escrito.

<!-- TABELA GERADA — r8_tiers.py render. Editar aqui não adianta. -->

| Etapa do fluxo | Modelo | Effort | Knob |
|---|---|---|---|
| Planejamento inicial e decomposição | Opus | `high` | `decompose_model` |
| Coordenação rotineira dos agentes | Opus | `medium` | `coordinate_model` |
| Execução das tarefas | Opus | `medium` | `executor_model` |
| Operações mecânicas e bem delimitadas | Opus | `low` | `mechanical_model` |
| Diagnóstico após falhas repetidas | Opus | `medium` | `diagnose_model` |
| Revisão final e integração | Opus | `medium` | `finalize_model` |

**Quando cada uma entra, e por quê:**

- **`decompose_model`** (Opus `high`) — rodada 1 — quebra o problema inteiro; o sweep mais pesado, uma vez. Decide o que todo o resto vai fazer, e um erro aqui se paga em cada tarefa depois.
- **`coordinate_model`** (Opus `medium`) — rodadas 2+ — processa só o delta do feedback. Não é mais decomposição inicial; o problema já está mapeado.
- **`executor_model`** (Opus `medium`) — tarefa padrão (complexity ausente ou 'standard'). Desvio deliberado de custo — a recomendação de partida da Anthropic para trabalho agentic é xhigh.
- **`mechanical_model`** (Opus `low`) — tarefa marcada complexity: 'mechanical' — renomear, mover arquivo, um valor. Não há julgamento amplo a fazer; o que cai é profundidade, não capacidade.
- **`diagnose_model`** (Opus `medium`) — a mesma tarefa reaparece falhando por churn_threshold rodadas seguidas. O que o separa da rodada não é esforço, é contexto limpo.
- **`finalize_model`** (Opus `medium`) — confirm-pass dedicado antes de declarar pronto ou limpo. O que o separa da rodada não é esforço, é reabrir o problema do zero.

**Regra por rodada:**

- Rodada 1 usa o tier de `decompose`.
- Rodadas 2+ usam o tier de `coordinate`, e processam só o delta.
- CONFIRM e DIAGNOSE são sempre agentes dedicados, em qualquer rodada.
- Nenhum dos dois pode ser dispensado por a rodada já ter passado no mesmo tier.

**Por que estes números:**

- É tudo Opus 5: nenhuma etapa roda em modelo mais barato, só o effort varia.
- Nenhum nível tem tarifa própria — o preço por token é o mesmo nos cinco.
- O anúncio do Opus 5 mede que no menor esforço ele já passa mais tarefas que qualquer outro modelo.
- O guia de migração manda varrer para baixo a partir do padrão da API, que é `high`.
- Effort não encurta resposta — o guia diz que mexer nele move raciocínio, não tamanho visível.

<!-- FIM DA TABELA GERADA -->

## Como o motor consome isto

```bash
# a casca, antes de disparar o Workflow
TIERS="$(python3 "<skill_dir>/references/r8_tiers.py" args)"
```

```javascript
// dentro do script: nenhum literal, nem no caminho de erro
const T = args.tiers   // veio do JSON, via a casca
const tierFor = round => ({ model: args.model, effort: round === 1
  ? T.decompose.effort : T.coordinate.effort })
const execTier = t => ({ model: args.model,
  effort: t.complexity === 'mechanical' ? T.mechanical.effort : T.executor.effort })
```

⚠️ **A casca sempre materializa `tiers` antes de disparar.** Se `args.tiers` chegar
`undefined`, o script morre na primeira volta — e essa é a falha certa: um default
carimbado no script seria a décima-sexta cópia do valor, exatamente o que este arquivo
existe pra impedir.
