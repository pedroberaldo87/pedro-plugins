---
generated: 2026-08-14
reviewed: 2026-08-14
project: pedro-plugins
authored-by: ex-post-rascunho
status: ready
approved:
scope: []
---

# Contexto e escopo

> Onde este sistema termina e o mundo começa.

## Atores
- **O dono** — escreve os plugins, aprova a doc, opera as missões; é também o primeiro usuário. [INFERIDO DO CÓDIGO: único autor do git]
- **As várias sessões simultâneas do dono** — ele trabalha em frentes paralelas na MESMA árvore; o estado do git muda embaixo de quem está agindo. Por isso: commit sempre cirúrgico por caminho (nunca `git add -A`), `git status` relido fresco antes de agir, e nenhum retrato inicial é confiável. [ESCRITO: os três arquivos de handoff no disco carregam o mesmo aviso ao longo de dois meses — registro de trabalho, fora do git de propósito]
- **Quem instala** — terceiro que adiciona o marketplace e instala plugins; recebe atualização por bump de versão. [ESCRITO: README/CLAUDE.md · Quick Commands]
- **Os agentes Claude** — consomem as skills, obedecem os hooks e rodam os motores; são o "usuário final" de todo comportamento. [INFERIDO DO CÓDIGO: skills falam com o agente, não com humano]

## Sistemas externos
- **Claude Code (CLI)** — entra: eventos de hook e invocação de skill · sai: comportamento (bloqueio, aviso, página) · protocolo: hooks.json + Skill tool
  - **Se cair:** nada roda — é o host de tudo.
  - **Evidência:** todo `hooks/hooks.json` rastreado (a contagem sai de `git ls-files 'plugins/*/hooks/hooks.json' | wc -l`)
- **GitHub** — entra: push · sai: distribuição aos clientes e o CI de portabilidade nos três sistemas · protocolo: git + Actions
  - **Se cair:** clientes não atualizam e o Windows fica sem prova; o trabalho local segue.
  - **Evidência:** .github/workflows/portability.yml
- **Node (stdlib)** — entra: estado das páginas do /visual · sai: live-sync em `~/.claude/visual-state/` · protocolo: daemon local na porta 7755
  - **Se cair:** a página degrada para copiar/colar — nunca trava.
  - **Evidência:** plugins/visual/server/visual_server.mjs
- **Python 3 do sistema** — entra: chamadas dos hooks e skills · sai: toda a mecânica (planos, gates, medidores)
  - **Se cair:** os motores param; skills de prosa seguem.
  - **Evidência:** patterns.md, convenção stdlib
- **iCloud** — entra: segredos capturados do dono · sai: o cofre replicado · protocolo: pasta sincronizada no disco
  - **Se cair:** máquina nova fica sem os secrets; é o único depósito com replicação real.
  - **Evidência:** data-stores.md (cofre) e durability.md (cobertura)

## Fora do escopo — explicitamente NÃO é nosso
- **Os hóspedes do host** — browser e MCPs de terceiros chegam pelo Claude Code; são fronteira dele, não peça nossa.
- **Os projetos onde os plugins rodam** — o plugin julga e cobra; a obra é de quem instala.
- **Os modelos de IA** — consumimos o agente como host; não treinamos nem hospedamos modelo.
- **O `settings.local.json` de cada máquina** — o bootstrap mergeia o `settings.json` em mão única (repo → máquina, com backup); o local é do dono da máquina e fica intocado. [INFERIDO DO CÓDIGO: bootstrap SKILL.md — merge de settings-defaults.json]

## Diagrama de contexto

```
                    ┌─────────────────┐
   dono ──escreve──▶│  pedro-plugins  │◀──instala── terceiros
                    │  (este repo)    │
                    └───┬─────────┬───┘
            hooks/skills│         │push
                        ▼         ▼
                 Claude Code    GitHub (distribuição + CI 3 OS)
                 (host de tudo)
```
