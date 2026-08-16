---
generated: 2026-08-14
reviewed: 2026-08-14
project: pedro-plugins
authored-by: ex-post-rascunho
status: approved
approved: 2026-08-16
scope: []
approved-sig: 1066034391
---

# Jornadas

> O percurso da pessoa, não o do código. Se um passo aqui não tem onde acontecer
> na interface nem quem o execute na arquitetura, achamos um buraco.

## Instalar a casa numa máquina nova
- **Ator:** quem instala (o dono numa máquina nova, ou um terceiro)
- **Gatilho:** máquina limpa, e o trabalho precisa dos mesmos comportamentos de sempre
- **Percurso:** `claude plugin marketplace add` → `bootstrap:setup` lê o manifest → plugins instalados → restart
- **Fim feliz:** os hooks disparam em qualquer projeto; a casa inteira veio num comando.
- **Onde quebra:** o sync sobrescreve idioma, tema, compactação automática e estilo de saída, e vence nas variáveis de ambiente que ele define (as suas próprias sobrevivem; permissão é união) — regra nessas chaves sobrescritas precisa subir ao repositório para durar. E plugin instalado não atualiza sozinho (`install` diz "already installed") e versão nova exige update + restart. [ESCRITO: CLAUDE.md · Quick Commands]
- **Toca as peças:** Catálogo, Bootstrap, Plugin

## Publicar uma mudança de plugin
- **Ator:** o dono
- **Gatilho:** consertou ou evoluiu um comportamento e quer que chegue aos clientes
- **Percurso:** edita → bump no `plugin.json` espelhado no catálogo → `sync-shared` se tocou fonte → **a esteira roda e grava a prova** → **`/doc-touch`** → commit (o portão confere a prova e barra o que estiver fora) → push com fetch e avanço rápido, nunca forçado
- **Fim feliz:** o cliente roda `plugin update` e recebe; o CI prova que roda fora desta máquina, e a doc acompanha o código.
- **Onde quebra:** pular a esteira antes do commit — aí o portão re-mede tudo e o canal morre no tempo. Esquecer o bump ou o espelho o portão recusa e diz o quê. [DITO POR VOCÊ: 17 datas entre 07-24 e 08-14 — "faz um doc touch, commita e pusha"]
- **Toca as peças:** Portão de release, Esteira, CI de portabilidade, Catálogo

## Conceber um projeto com a metodologia
- **Ator:** o dono, num projeto qualquer da casa
- **Gatilho:** projeto sem régua — sem lei, sem acordo, ou com etapa aberta
- **Percurso:** `/start` (ou `ex-post` no maduro) → os acordos na ordem, cada um sabatinado e aprovado com marca → entre a concepção e o plano, a pesquisa de referências em duas frentes (código aberto para aproveitar solução pronta, produto fechado para amadurecer jornada) → o protótipo, que cobre também erro, configuração e governança [PENDENTE: etapa ainda não construída no /start — é obra do plano aberto]
- **A pauta transversal é perguntada por programa, nunca por lembrança:** topologia do repositório, integrações, abstração de IA, controle de acesso, governança e registro de log. "Não se aplica" é resposta válida; faltar a pergunta, não. [PENDENTE: o programa que pergunta ainda não existe no /start — é obra do plano aberto]
- **Fim feliz:** a régua existe e o `/doc-load` a carrega em toda etapa que julga.
- **Onde quebra:** etapa escrita sem aprovação — o gate de plano trata como aberta e cobra. [INFERIDO DO CÓDIGO: pretooluse-plan-gate.sh]
- **Toca as peças:** Skill, Motor de skill, Hook

## Executar um plano noite adentro
- **Ator:** o dono (decide) e o motor (executa)
- **Gatilho:** plano ticável aberto e uma noite disponível
- **Percurso:** o plano é varrido em quatro passadas atrás do que travaria (item a item · sequência encadeada · portas medidas por comando · vizinhança da árvore) [PENDENTE: o pré-check de largada é obra do plano aberto (fase F22)] → o que sobrou vira página de decisão → `/sprint` arma o sinal e a reserva → ondas de agentes com revisor por tarefa → tique com a prova que o critério pede → relatório de manhã
- **Fim feliz:** passos marcados com prova e commits publicados; o que travou virou pendência nomeada.
- **Onde quebra:** decisão do dono não tomada antes da largada — o passo volta recusado de madrugada. [DITO POR VOCÊ: plano F22, colheita das corridas paradas por pergunta]
- **Toca as peças:** Motor, Portão de release, Esteira

## Guardar e retomar o trabalho
- **Ator:** o dono
- **Gatilho:** a sessão encheu, um ciclo fechou, ou é hora de parar — e o trabalho não pode se perder
- **Percurso:** `/handoff` grava o estado → `/clear` ou pausa → a sessão nova lê o handoff e o hook ressuscita o plano aberto
- **Fim feliz:** a retomada começa de onde parou, com os ids e títulos exatos do plano — nada reconstruído de memória.
- **Onde quebra:** plano dado como concluído sem estar — foi a perda que fez o plano virar arquivo com prova. [DITO POR VOCÊ: "os planos eram dados como concluídos e não tinham sido concluídos de fato"]
- **Toca as peças:** Skill, Motor de skill, Hook

## Manter a doc viva
- **Ator:** o dono (dispara) e os agentes (consomem)
- **Gatilho:** um ciclo de código terminou e a doc dos arquivos tocados ficou para trás
- **Percurso:** `/doc-touch` mapeia o diff para os docs afetados → re-projeta só eles → `/doc` FULL quando o drift é estrutural → o grafo se atualiza junto
- **Fim feliz:** a doc que os agentes leem descreve o código de hoje, e o aviso de DEFASADA some.
- **Onde quebra:** doc defasada tratada como verdade — o começo de sessão a rotula como hipótese. [INFERIDO DO CÓDIGO: aviso de defasagem no SessionStart]
- **Toca as peças:** Skill, Motor de skill

## Criar um aplicativo dentro de um organismo que já existe
- **Ator:** o dono
- **Gatilho:** o projeto novo nasce dentro de um repositório raiz que já tem lei, integrações e vizinhos
- **Percurso:** a herança é levantada por programa → apresentada item a item, cada um com a fonte → o dono confirma, ressalva ou dispensa cada um → só o que diverge vira acordo próprio do módulo
- **Fim feliz:** o módulo nasce sob a lei da raiz, e o que ele tem de diferente está escrito como diferença.
- **Onde quebra:** herdar em silêncio ou perguntar de novo o que a raiz já respondeu. [DITO POR VOCÊ: 2026-08-06 — "a palavra não é copia, a palavra é herda (…) me apresentar para conferir se mantém essas características ou se muda"]
- **Toca as peças:** Skill, Motor de skill

## Ser consultado numa rodada de decisões
- **Ator:** o dono
- **Gatilho:** qualquer skill precisa de escolha dele — na concepção, no plano, na disputa ou na revisão
- **Percurso:** a rodada inteira vira uma página de decisão por padrão → cada opção mostra o conteúdo concreto de que fala → há sempre o campo livre "outra — eu especifico" → a resposta volta pelo disco quando ele diz "ok"
- **Fim feliz:** ele decide vendo a prova, no canal que escolheu — e pode trocar de canal a qualquer momento.
- **Onde quebra:** pergunta sem apoio visível — pedir escolha sobre coisa que só existe no contexto do agente é reprovação. [DITO POR VOCÊ: 2026-08-06 — "você só me pediu pra decidir coisa com base em bola de cristal"]
- **Toca as peças:** Skill, Juiz de clareza

## Extinguir ou fundir um plugin
- **Ator:** o dono (decide) e o agente (varre)
- **Gatilho:** um plugin morre, funde com outro ou muda de nome
- **Percurso:** a lista de superfícies não se lembra, se DERIVA — o nome morto é procurado em todo formato que o repositório lê → cada acerto vira candidato, inclusive comentário → catálogo, manifest e docs saem no mesmo lote
- **Fim feliz:** nenhum resto do nome morto; nenhum check ficou inerte apontando para o que não existe.
- **Onde quebra:** o recorte de escopo com o nome morto vira check inerte em vez de check vermelho — parece protegido e não protege. [ESCRITO: patterns.md — a régua da fusão]
- **Toca as peças:** Catálogo, Portão de release, Bootstrap

## Revisar até valer a pena
- **Ator:** o dono
- **Gatilho:** um ciclo de implementação terminou e ele quer saber se está 100%
- **Percurso:** `/qa-loop` ancora no plano → achados viram conserto só quando são de implementação → regression gate por conserto → para por retornos decrescentes
- **Fim feliz:** repo com lint, type, unit e integração verdes, e um relatório do que ficou por design.
- **Onde quebra:** loop até zero — proibido de propósito: queima token e regride. [DITO POR VOCÊ: journal 2026-06-20]
- **Toca as peças:** Skill, Motor de skill, Esteira
