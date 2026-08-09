---
name: monitorar
description: Imprime o andamento AGORA de toda missão de workflow que está de pé — relógio da missão, ferramenta em execução com a estimativa de sempre, silêncio e placar da última onda — lendo o estado do disco, sem perguntar nada a ninguém. Use quando o usuário disser "/monitorar", "como vai o workflow", "tem coisa rodando aí?", "cadê o andamento", ou quando voltar ao terminal depois de um tempo e a barra de status não estiver à vista.
---

# monitorar — o andamento do workflow, agora

A barra de status só fala da sessão em que ela está desenhada, e o `systemMessage` do vigia
rola junto com a conversa: quem volta ao terminal uma hora depois não vê nenhum dos dois.
Esta skill é a pergunta "como vai?" virada comando.

## O comando

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/andamento.py"
```

Mostre a **saída crua** ao usuário. Cada linha é uma missão de pé:

```
<sessão> · <motor> · missão há 12min03s · ferramenta há 70s · usual ~1min35s · último sinal há 8s · 139 passou · 0 falhou
```

- **`nenhuma missão de pé`** → não há workflow rodando. Diga isso e pare; não invente
  investigação sobre processo nenhum.

## O que ele NÃO faz

- **Não pergunta a ninguém como vai.** Tudo que sai vem de `~/.claude/andamento/`, escrito
  por quem executa: `ativo-<sid>` (a missão e o nome do motor), `trabalho-<sid>` (o comando
  de pé), `sinal-<sid>` (o último sinal de vida), `placar-<sid>` (a última onda).
- **Não estima comando sem histórico neste projeto.** Sai sem número, de propósito —
  relógio sozinho é honesto, número inventado não.
- **Não apaga nem acende sinal.** Quem acende é o motor que dispara o workflow; sinal
  esquecido aparece aqui como missão velha, e quem o apaga é a skill que o acendeu.
