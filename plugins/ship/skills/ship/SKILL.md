---
name: ship
description: Use quando o código está pronto pra ir pra produção — roda lint, type-check, commit, push e deploy num fluxo disciplinado. Dispara em "ship", "manda", "deploya tudo". No fim de um ciclo de implementação, OFEREÇA pra dar ship — nunca deploye por conta própria sem o Pedro pedir.
---

# Ship — Lint, Commit, Push, Deploy

## Visão Geral
Um comando pra levar código verificado do local pra produção. Aplica gates de qualidade em cada passo — se algum falha, para e conserta antes de continuar.

## Fluxo

Detectar ferramentas → lint/type-check até zerar → testes (gate duro) → commit + push → deploy → verificar. Qualquer gate vermelho para o fluxo e conserta antes de avançar.

## Processo

### 1. Detectar as ferramentas do projeto

Cheque os arquivos de config do projeto pra identificar a ferramenta certa. NÃO assuma — leia os configs.

| Procure por | Ferramenta |
|----------|------|
| **eslint.config.***, **.eslintrc.*** | ESLint |
| **biome.json** | Biome |
| **tsconfig.json** | tsc |
| **pyproject.toml** (ruff/mypy/pyright) | ruff, mypy, pyright |
| **setup.cfg**, **tox.ini** | flake8, mypy |

Se o projeto tem um script `lint` ou `check` no **package.json** ou **Makefile**, prefira ele — já está configurado.

### 2. Lint + Type-Check (Conserte TODOS os erros)

**Atalho de delta:** se a sessão passou pelo guardrails (lint/type por-edit a cada arquivo salvo) **e** a Fase Gate do qa-loop fechou verde neste tree-hash (`green_cache_check` HIT — ver §2.5), rode lint/type **só nos arquivos do diff** (`git diff --name-only` + staged). Qualquer erro no delta, ou sem HIT no cache → o loop completo abaixo.

Rode lint e type-check. Conserte TODOS os erros achados — incluindo pré-existentes nos arquivos que você tocou ou perto deles. Zero erros é a meta.

**Loop até limpar:**
1. Rode o linter com flag de auto-fix se houver (`--fix`, `--unsafe-fix`)
2. Rode o type-checker
3. Se sobrar erro, conserte à mão
4. Re-rode os dois até zero erros

**NÃO pule erros pré-existentes.** Se o linter reporta, conserte.

### 2.5. Rodar Testes (Gate Duro)

**Cache verde primeiro:** `source "${CLAUDE_PLUGIN_ROOT}/hooks/green-cache.sh"`. Monorepo com gate por-app → consulte `green_cache_check <repo-root> app:<alvo>` (um por app do deploy); senão `green_cache_check <repo-root> full`. **HIT** → pule a suíte e **reporte**: "suite verde via cache (tree `<hash>`, gravado por `<writer>` às `<ts>`)" — nunca pule em silêncio. **MISS** → rode como abaixo; ao fechar 100% verde, `green_cache_mark <repo-root> <escopo-que-rodou> ship`. Suite vermelha nunca grava.

Detecte e rode a suíte de testes antes de commitar qualquer coisa. Num monorepo com gate por-app (`scripts/run_app_tests.sh`), rode a suíte do app relevante por §2.6 — não o repo inteiro no interpretador errado. Senão, rode a suíte completa.

| Procure por | Ferramenta |
|----------|------|
| script `test` no **package.json** | `npm test` (ou `yarn test` / `pnpm test`) |
| `jest` / `vitest` / `mocha` em devDependencies | rode direto se não houver script |
| `pytest` em **pyproject.toml** / **setup.cfg** | `pytest` |
| **Cargo.toml** | `cargo test` |
| **go.mod** | `go test ./...` |
| target `test` no **Makefile** | `make test` |

**Se nenhum test runner for achado**, registre um aviso e continue — mas anote a ausência.

**Loop até todos passarem:**
1. Rode a suíte de testes completa
2. Se todos passam → avança pro Commit + Push
3. Se algum falha → **para aqui**
   - Reporte quais testes falharam e os erros exatos
   - Conserte as falhas — falhas pré-existentes **não são aceitáveis** pra deploy
   - Re-rode até zero falhas
   - Só então avance

**Este gate não pode ser burlado.** Mesmo que o Pedro mande seguir com testes falhando, não avance. O caminho certo é: consertar as falhas, re-rodar a suíte, então retomar o fluxo de ship. (Cache HIT não é burla — é a MESMA suíte, verde, no mesmo estado exato da árvore; qualquer edição muda o tree-hash e invalida o hit.)

> O hook `pre-deploy-test-check` (incluído neste plugin) aplica esse gate no nível do harness — intercepta comandos de deploy e os bloqueia se a suíte falha.

#### 2.6 Gate por-app + avaliação LLM de escopo (monorepos)

Num monorepo onde cada app tem suas deps/venv, rodar a suíte inteira no Python do sistema colapsa em erros de import e bloqueia todo deploy. Use um **piso determinístico + avaliação LLM por cima**:

- **Piso (determinístico):** se o projeto tem `scripts/run_app_tests.sh`, o gate é `scripts/run_app_tests.sh <app>` — roda SÓ os testes do app deployado, na venv de teste do projeto (ex: `.venv-test`), excluindo `@pytest.mark.e2e` (testes que precisam de produção: IMAP/SSH/psql ao vivo). O hook `pre-deploy-test-check` chama isso por app automaticamente.
- **Avaliação LLM (você, na hora do ship):** identifique o(s) app(s)-alvo a partir do comando de deploy ou do diff. Você PODE **ampliar** o escopo — ex: se o diff toca `shared_lib/`, rode também os gates dos apps que dependem dele. Você NUNCA pode **estreitar** abaixo do piso: todo teste não-e2e do app-alvo tem que rodar. Reporte transparente o que rodou, o que foi excluído como e2e (e por quê) e o resultado.
- A avaliação decide o que ADICIONAR e confirma que os testes excluídos são genuinamente e2e — nunca é desculpa pra pular um teste relevante.

Isso satisfaz o gate duro sem o interpretador errado nem o escopo errado. Testes e2e / de integração-com-produção rodam à parte (CI ou manual), não no gate local de pré-deploy.

### 3. Commit + Push

Siga o fluxo de commit padrão:
1. `git status` — revise o que mudou
2. `git diff` — revise as mudanças reais
3. `git log --oneline -5` — case o estilo da mensagem de commit
4. Stage de arquivos específicos (sem `git add -A` — evita secrets/binários)
5. Escreva uma mensagem de commit concisa (foco no "porquê")
6. `git push` pra branch de tracking atual

**Se não houver branch de tracking**, pergunte ao Pedro antes de dar push pra uma branch remota nova.

### 4. Deploy

O método de deploy depende do projeto. Detecte a partir de:

| Procure por | Método de deploy |
|----------|--------------|
| **ecosystem.config.js**, PM2 nos scripts | `pm2 restart` ou `pm2 deploy` |
| **docker-compose.yml** | `docker compose up -d --build` |
| **Dockerfile** só | Build + deploy pela convenção do projeto |
| **vercel.json**, `.vercel` | `vercel --prod` |
| **netlify.toml** | `netlify deploy --prod` |
| **deploy.sh**, **Makefile deploy** | Rode o script de deploy do projeto |
| Padrão SSH/VPS nos scripts | Deploy SSH pela convenção do projeto |

**Se o método de deploy não estiver claro**, pergunte ao Pedro. NÃO chute.

### 5. Verificar o Deploy

Depois do deploy, verifique que o serviço está rodando:
- Cheque o status do processo (pm2 status, docker ps, curl no health endpoint)
- Verifique que os valores de config sobreviveram ao deploy (especialmente `.env` no VPS)
- Mostre a evidência ao Pedro

**Se a verificação falha**, capture a evidência primeiro, depois faça rollback antes de tentar de novo — não deixe a produção meio-deployada:
- **Capture os logs primeiro** (`pm2 logs`, `docker logs`, a resposta de health que falhou) pra a causa sobreviver ao rollback.
- **Gerenciador de processos** — restaure o último processo bom (`pm2 reload <app>` pro build anterior, ou `pm2 resurrect`).
- **Deploy via git** — `git revert` no commit de deploy (ou resete o servidor pra a última tag boa) e re-deploye o último bom-conhecido.
- Só tente o deploy de novo depois de entender a causa. Não reporte como pronto enquanto a produção está quebrada.

## Regras de Segurança

- **Nunca deploye sem passar lint + type-check primeiro**
- **Nunca deploye com testes falhando** — mesmo pré-existentes. Se testes falham no gate 2.5, conserte antes de continuar. Este gate não pode ser burlado.
- **Nunca force-push** sem permissão explícita
- **Cheque arquivos `.env`** — podem ser sobrescritos por operações git no VPS
- **Faça backup da config server-specific** antes de `git reset --hard` ou `git pull` num servidor
- **Pergunte antes de deployar pra produção** se houver um ambiente de staging disponível

**Assimetria de enforcement (saiba disso):** só o gate de teste (2.5) é respaldado por um hook do harness (`pre-deploy-test-check`). Lint + type-check acima são disciplina model-enforced — nenhum hook bloqueia um deploy com erros de lint. Trate "lint limpo" como responsabilidade sua, não garantia da máquina.

## Quando NÃO Usar

- Código ainda não foi testado/verificado — teste primeiro, ship depois
- Durante um merge freeze (cheque a memória do projeto)
- Quando só documentação mudou e não precisa de deploy — só commit+push, pule o deploy
