---
name: sovai
description: Modo de execução contínua — Claude executa um plano ou tarefa multi-etapa do começo ao fim sem pausas, sem checkpoints, sem perguntas de confirmação. Toma as decisões necessárias para seguir e anota cada uma. Pedro estará indisponível durante a execução; ele revisa tudo no relatório final e refatora se necessário. Use quando Pedro disser "sovai", "sova", "executa até o fim", "vai sem parar", "não me consulte", "eu não estarei disponível", "modo autônomo", ou variação clara de "executa sozinho enquanto eu não tô". Não disparar para tarefas curtas que terminam num turno — a skill existe para missões em que interrupção custa caro porque Pedro não está disponível para responder.
---

# Sovai — Execução Contínua

Pedro vai ficar indisponível. Reconheça com uma linha (`modo sovai ativo, começando`) e comece. Daqui em diante, silêncio até o relatório final.

## Contrato

**Faz:**
- Executa o plano (ou a tarefa) do começo ao fim, sem pausar
- Toma todas as decisões necessárias para seguir e **anota cada uma**
- Verifica antes de declarar feito — regras globais do CLAUDE.md continuam valendo

**Não faz:**
- Pergunta de confirmação no meio ("posso seguir?", "X ou Y?")
- Checkpoint intermediário pedindo aval
- Reporte de progresso parcial — silêncio é o esperado
- Ação destrutiva ou irreversível fora do escopo do plano (drop de banco em produção, force push em main, rotação de credencial real, deploy fora do combinado) — registra como pendência

## Bloqueios

Se um item não puder ser feito como pedido, **não invente workaround silencioso**. Pula o item, anota o bloqueio com o que faltou, e segue para o próximo. A regra global "Entrega 100% ou Para e Conversa" continua valendo — o "Para e Conversa" vira "Pula e Anota" porque Pedro está indisponível, mas a entrega ainda precisa ser honesta.

## QA final (antes do relatório)

Terminada a execução e **ANTES** de montar o relatório, rode a skill `/qa-loop` em **modo headless** sobre o que você implementou, passando o plano como âncora:

```
/qa-loop <mudanças desta sessão> --plan=<plano> --headless
```

Como o Pedro está indisponível, o headless nunca pergunta nada. Trate os 3 buckets assim:
- **Implementação** (bug / divergência do plano) → conserta no loop. Você já tem mandato de executar o plano; o regression gate por conserto é a rede que evita as regressões auto-infligidas.
- **Plan-drift** (um "fix" afastaria do plano em UX/backend/proposta) → **reverte pro plano**. Não "melhore" pra longe do combinado.
- **Plano/arquitetura falho** → **NÃO implemente**. Vira item de "Bloqueios (precisam de você)" no relatório. Headless **não** é licença pra re-planejar.

O relatório do `/qa-loop` (loops rodados, correções, regressões pegas, alertas de plano) vira a seção `### QA` do relatório final.

## Relatório Final

O relatório é a única coisa que Pedro lê desta sessão — e ele lê **depois**, pra revisar tudo e refatorar. Por isso ele sai como uma **superfície de revisão em HTML**, não como textão no CLI.

### Conteúdo (backbone — sempre o mesmo)

Cinco seções. Monte este conteúdo PRIMEIRO; a forma de entrega (HTML ou markdown) vem depois.

```
## Sovai — terminei

### Feito
- [só o que foi verificado]

### Decisões tomadas
- [decisão]: [razão em 1 linha]

### Bloqueios (precisam de você)
- [item pulado]: [o que faltou]

### Verificação
- [o que rodou, e o resultado]

### QA (qa-loop)
- [loops rodados + critério de parada · correções aplicadas · regressões pegas na hora]
- [⚠️ alertas de plano/arquitetura que NÃO implementei — pra você julgar]
```

### Entrega via /visual (titular)

Se a Skill **`visual`** estiver entre as suas skills disponíveis, **invoque-a** (Skill tool, `skill: "visual"`) e renderize o relatório como HTML. (Não "digite /visual" — invoque a skill.) `visual` é **dependência recomendada** do sovai; instale os dois juntos.

Por que HTML: o relatório é longo e completo, e Pedro vai **revisar item a item e refatorar**. O `/visual` tem o componente exato pra isso — veredito inline (`.feedback-item`: ✓ Manter / ✏️ Mudar / ✗ Remover) que ele marca enquanto lê.

**Mapeamento seção → componente** (instrua o /visual a montar a superfície de revisão):

- **Bloqueios (precisam de você)** → **topo**, prioridade máxima. Default: `.callout` severidade alta (um bloqueio é "não consegui X porque faltou Y" — sem ramificação). **Só** vire `.decision-card` se houver escolha A/B **genuína** já clara — nunca fabrique duas opções pra preencher o card (regra anti-"chutar"). Os ⚠️ alertas de plano/arquitetura do qa-loop entram aqui (normalmente `.callout`; só decision-card se for binário de verdade).
- **Feito** → cada item = `.feedback-item` com veredito inline + profundidade em `<details>`. Pedro revisa enquanto lê.
- **Decisões tomadas** → cada decisão = `.feedback-item` (Pedro aprova ou marca pra rever) + razão em 1 linha.
- **Verificação** → `.callout` (ok/danger): o que rodou + resultado. Read-only.
- **QA (qa-loop)** → `.callout`/seção: loops, correções, regressões, alertas. Read-only.
- `.exec` no fim + **caixa de fechamento**: no caso comum (feedback-items + callouts) só `feedback-box`; `decisions-box` só se houver decision-card de verdade. As caixas são **só fechamento** (progresso + observação + botões) — **nunca re-listam os itens** (anti-pattern "duas tabelas").

**Retorno do feedback é assíncrono.** Pedro está fora e esta sessão termina quando o relatório sai — então **não** conte com live-sync ("ele diz ok e o Claude lê"). O HTML guarda os vereditos em `localStorage`; quando Pedro voltar (provável sessão nova), ele clica "Copiar feedback"/"Copiar escolhas" e cola pra dirigir o refactor. O daemon do /visual pode subir (é inócuo), mas o caminho confiável é copy/paste.

**CLI mínimo** (o /visual proíbe duplicar o conteúdo no CLI): emita só

```
Sovai terminou. Relatório completo no browser: <path>
⚠️ Bloqueios (precisam de você): <título 1> · <título 2>   ← só os títulos, se houver
```

Os títulos dos bloqueios são um **índice** (não o conteúdo) — segurança, porque bloqueio é crítico e Pedro precisa vê-los mesmo sem abrir o browser. Nada além disso no CLI.

### Fallback (markdown)

Se a Skill `visual` **não** estiver disponível, emita o **relatório markdown completo** (o bloco de conteúdo acima, com as 5 seções preenchidas) direto no CLI. É um fallback à altura: entrega 100% da mesma informação — só a apresentação degrada, não o conteúdo.

Detalhe técnico só se Pedro pedir depois.
