# pedro-plugins

Marketplace privado de plugins Claude Code do Pedro. Monorepo — cada subdiretório em `plugins/` é um plugin independente distribuído via este marketplace.

## Plugins disponíveis

| Plugin | Descrição |
|---|---|
| `bootstrap-third-party` | Sincroniza automaticamente marketplaces e plugins de terceiros entre todas as máquinas do Pedro via git |

## Instalação (em qualquer máquina)

```bash
# 1. Adicionar o marketplace
claude plugin marketplace add git@github.com:pedroberaldo87/pedro-plugins.git

# 2. Instalar o plugin que você quiser
claude plugin install bootstrap-third-party@pedro-plugins
```

Se você for desenvolver o marketplace nessa máquina, clone o repo também:

```bash
git clone git@github.com:pedroberaldo87/pedro-plugins.git ~/PROGRAMACAO/PEDRO/pedro-plugins
```

Os hooks detectam automaticamente se o repo está clonado localmente e adaptam o comportamento (escreve/push se tem repo, só lê se não tem).

## Convenção de path

Por padrão, hooks esperam o repo em `~/PROGRAMACAO/PEDRO/pedro-plugins`. Pra usar outro caminho, defina a env var:

```bash
export PEDRO_PLUGINS_REPO="/caminho/alternativo/pedro-plugins"
```

## Estrutura

```
pedro-plugins/
├── .claude-plugin/
│   └── marketplace.json       # Manifest do marketplace
├── plugins/
│   └── bootstrap-third-party/
│       ├── .claude-plugin/plugin.json
│       ├── hooks.json
│       ├── hooks/             # Bash scripts dos hooks
│       ├── skills/            # Skills do plugin
│       └── README.md
└── README.md
```

## Licença

Uso pessoal do Pedro. Sem licença pública.
