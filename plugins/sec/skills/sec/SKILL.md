---
name: sec
description: Use quando o usuário diz "/sec", "verifica a segurança", "tô protegido?", "tem pacote envenenado aqui", "confere as vulnerabilidades", "saiu notícia de pacote comprometido, me afeta?", ou quando uma notícia de ataque de cadeia de suprimentos (npm, PyPI, ação do GitHub, servidor MCP) levanta a dúvida se o projeto ou a máquina foram atingidos. Faz o inventário do que vem de FORA — pacotes do projeto, ações do CI, servidores MCP, plugins do Claude Code, pacotes globais, Node — e confere cada item contra bases públicas (OSV e a lista de malware da Aikido Intel). Não revisa o código do usuário. Entrega um relatório com checkbox, e corrige só o que o usuário marcar. Fonte que não respondeu sai como NÃO VERIFICADO, nunca como verde.
---

# Skill: /sec

A pergunta é uma só: **o que eu baixo de fora está limpo?**

O ataque de cadeia de suprimentos não mexe no código do usuário. Ele entra pelo que
é instalado: alguém toma a conta do autor de um pacote popular e publica uma versão
envenenada. Quem instala naquela janela leva o veneno junto.

Por isso o /sec não lê o código do projeto. Ele lista tudo que vem de fora e confere.

## O que é conferido

| Frente | Itens | Contra o quê |
|---|---|---|
| Projeto | `package-lock.json`, `pnpm-lock.yaml` (9.x), `yarn.lock` (v1 e berry), `uv.lock`, `poetry.lock`, `requirements*.txt` | OSV + Aikido Intel |
| Projeto | ações em `.github/workflows/*.yml` | dump de GitHub Actions do OSV + tag móvel |
| Projeto | `.mcp.json` | versão fixa + OSV/Aikido do pacote |
| Máquina | Claude Code, plugins instalados, servidores MCP do `~/.claude.json`, `npm -g`, `pipx`, Node, Homebrew | OSV, Aikido, lista de bloqueio do Claude Code, nodejs.org |
| Máquina e projeto pnpm | a **quarentena de versão nova** do pnpm (`minimumReleaseAge`) e do npm (`min-release-age`) | ligada ou não |

A quarentena é a defesa mais forte contra pacote envenenado recente: a maioria é derrubada
em horas, então não instalar versão com menos de um dia fecha a janela antes de existir
registro em qualquer base. Por isso ela entra como 🟡 mesmo sem nada acusado.

## Os quatro níveis

| Nível | O que é | O que fazer |
|---|---|---|
| 🔴 **malicioso** | versão envenenada (MAL-, CWE-506, Aikido MALWARE, bloqueio do Claude Code) | remover **e trocar senhas e tokens** |
| 🟠 **falha** | falha conhecida, com a versão que corrige | atualizar |
| 🟡 **cadeia** | porta aberta: tag móvel, sem versão fixa, sem lockfile, plugin de terceiro com hook, quarentena desligada | fechar quando der |
| ⚪ **velho** | só desatualizado | atualizar quando der |

## Fluxo

<pasta-da-skill> é o caminho que o Claude Code mostra como *Base directory for this skill*
quando carrega esta skill; o motor mora duas pastas acima, em `lib/`.

```bash
SEC="<pasta-da-skill>/../../lib/sec.py"

# 1. medir (só lê; projeto atual + máquina)
python3 $SEC scan                       # JSON
python3 $SEC scan --sem-maquina         # só o projeto
python3 $SEC scan --sem-projeto         # só a máquina

# 2. relatório com checkbox, em <raiz>/.claude/visual/
open "$(python3 $SEC report)"
```

`open` é o do macOS; no Linux é `xdg-open`, no Windows é `start`.

Código de saída: `0` = tudo conferido, `2` = alguma fonte não respondeu (o relatório
diz qual), `1` = erro do próprio /sec.

O usuário marca no HTML e clica **Copiar os marcados**. O bloco vem com o marcador
`<!-- sec-corrigir v1 -->` e uma linha por item, assim:
`[falha] npm lodash 4.17.15 — subir para 4.18.0 (em package-lock.json)`.

## Como corrigir o que veio marcado

Um item por vez, só os da lista colada. Nunca monte a lista a partir do nível.

- **Pacote npm direto** (está em `dependencies` do `package.json`): instalar a versão do conserto com o gerenciador do projeto (`npm install x@V`, `pnpm add x@V`, `yarn add x@V`).
- **Pacote npm indireto**: forçar a versão por `overrides` (npm), `pnpm.overrides` (pnpm) ou `resolutions` (yarn) no `package.json`, e reinstalar.
- **Pacote Python**: `uv lock --upgrade-package x` (uv), `poetry update x` (poetry), ou subir o `==` no `requirements.txt`.
- **Ação do GitHub**: trocar `@tag` pelo SHA do commit da versão segura, com a tag num comentário (`uses: dono/acao@<sha> # v46.0.1`). <tag> é a versão do conserto (ex.: `v46.0.1`) e <sha> é o hash que sai de `git ls-remote https://github.com/dono/acao refs/tags/<tag>`.
- **MCP sem versão**: acrescentar `@x.y.z` ao pacote no comando.
- **Plugin**: `claude plugin uninstall <nome>@<marketplace>` só se o usuário pediu (<nome>@<marketplace> é o texto depois de "plugin" no item). Plugin de terceiro com hook é decisão de confiança, não defeito.
- **Máquina**: `claude update`, `brew upgrade`, `npm install -g x@V`, `pipx upgrade x`, ou o instalador do Node.
- **Quarentena**: o comando que está no item. Atenção às unidades: o pnpm conta em **minutos** (`1440` = um dia) e o npm em **dias** (`1`). Pacote interno que precisa sair na hora vai na lista de exceção (`minimumReleaseAgeExclude` no pnpm, `min-release-age-exclude` no npm).

Depois de corrigir, rode o passo 1 do fluxo de novo e mostre que o item saiu.

## Regras não-negociáveis

1. **Nada é instalado, removido ou atualizado sem o usuário marcar.** O relatório
   pré-marca 🔴 e 🟠 para poupar clique, mas quem confirma é ele.
2. **🔴 malicioso vem sempre com o aviso de trocar segredos.** Se a versão envenenada
   chegou a ser instalada, o código dela já rodou: tokens de npm, GitHub, nuvem e as
   chaves em `.env` desta máquina têm que ser trocados. Remover o pacote não desfaz isso.
3. **NÃO VERIFICADO não é verde.** Se o código de saída for `2`, a primeira linha da
   resposta diz qual fonte não respondeu e que aquela parte ficou sem conferência.
4. **Não despeje a lista no terminal.** O HTML é a lista. Na resposta: quantos itens
   por nível, a fonte que falhou (se houver), e o caminho do relatório.
5. **Nenhum apontamento** se diz em uma linha, com o número de itens conferidos. Mesmo assim, gere o relatório.

## Limites (ditos ao usuário quando importarem)

- Go, Rust, Ruby e Java ainda não são lidos. A base OSV cobre esses ecossistemas, mas falta o leitor do arquivo de pacotes de cada um.
- `pnpm-lock.yaml` anterior à 9.x e `package-lock.json` do npm 6 saem como NÃO VERIFICADO, com o motivo.
- Ação fixada por SHA não é conferida na base de falhas (o OSV indexa por versão); ela só deixa de ser porta aberta.
- Pastas `fixtures/`, `__fixtures__/` e `testdata/` ficam fora da varredura: lockfile de exemplo de teste não é instalado, e acusá-lo seria alarme falso.
- A quarentena do npm é lida do `~/.npmrc`, porque há relato de `npm config get` devolver vazio com o valor gravado no arquivo.
- As listas ficam guardadas por 6 horas em `~/.claude/sec-cache/`. Para forçar uma busca nova, apague a pasta.
