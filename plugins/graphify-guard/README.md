# graphify-guard

Garante que os **knowledge graphs do graphify sejam consultados quando relevante** — em vez de ficarem parados enquanto o Claude faz grep/Explore cego.

## O problema

A skill `graphify` tem um "fast path" que consulta `graphify-out/graph.json` em vez de buscar cego — mas só roda quando a skill é invocada (`/graphify`). No começo de uma sessão o Claude não varre o filesystem, não descobre que há grafo, e responde arquitetura no grep. O grafo, mesmo fresco, nunca é usado.

CLAUDE.md/prosa não resolve: é best-effort e some sob pressão de contexto. Comportamento automático ("sempre que X") tem que ser **hook** — quem executa é o harness.

## Como funciona — defesa em profundidade

Três peças cobrindo falhas diferentes, com a detecção fatorada num helper único (DRY, fail-open):

| Peça | Evento | O que faz |
|------|--------|-----------|
| `graphify-detect.sh` | — (helper) | Acha `graphify-out/graph.json` no projeto (subindo ou descendo) e calcula freshness (mtime dos fontes vs grafo). Emite TSV. |
| `sessionstart-graphify.sh` | **SessionStart** | Se o projeto tem grafo(s), injeta um heads-up: "consulte `graphify query` antes de grep/Explore". Lista cada grafo e se está defasado. |
| `pretooluse-graphify-guard.sh` | **PreToolUse** (`Grep`/`Glob`/`Bash` com grep/rg/find) | Rede de segurança: na **1ª busca cega da sessão** dentro de um projeto com grafo, nega (`deny`) e redireciona pro `graphify query`. Uma vez por sessão (sentinel por `session_id`). |

**Camada 1 (SessionStart)** é o melhor caso: o Claude já sabe do grafo e vai nele proativamente. **Camada 2 (PreToolUse)** é a rede: pega quando o heads-up já apagou numa sessão longa e o Claude pega o grep.

## Freshness

O grafo é um snapshot. Quando arquivos-fonte são mais novos que `graph.json`, o plugin marca **defasado** e instrui o Claude a **oferecer** `graphify --update` (re-extrai só o que mudou, é barato). O `--update` nunca roda dentro do hook — quem roda é o Claude, depois do seu ok.

## Princípios de hook

- **Fail-open:** qualquer erro (sem `jq`, etc.) → `exit 0`, nunca bloqueia seu trabalho.
- **Barato:** o PreToolUse sai cedo em comando não-busca e no sentinel; o `find` de freshness roda no máximo 1x por sessão.
- **Monorepo-aware:** acha o grafo subindo a árvore (grep numa subpasta) e lista todos os grafos descendo (SessionStart num container como `VIU/`).
- **Não auto-dispara:** `graphify query` não casa o filtro de busca cega, então não há loop.

## Instalar

```
/plugin install graphify-guard@pedro-plugins
```

Sem comando, sem configuração. O grafo é criado/atualizado pela skill `graphify` (`/graphify`), não por este plugin — ele só garante que o grafo existente seja usado.
