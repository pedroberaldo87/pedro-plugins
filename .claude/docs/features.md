---
generated: 2026-08-14
reviewed: 2026-08-14
project: pedro-plugins
authored-by: ex-post-rascunho
status: approved
approved: 2026-08-16
scope: []
approved-sig: 1827305419
---

# Funcionalidades

> O que este sistema faz, derivado das etapas anteriores. Nada entra aqui sem origem
> apontável — funcionalidade sem origem é ideia que entrou pela janela.

## As funcionalidades

### F-1 · Instalar a casa inteira num comando
- **O que faz:** replica marketplaces, plugins e terceiros numa máquina nova pelo manifest.
- **Origem:** jornada "Instalar a casa numa máquina nova" · peça Bootstrap
- **Passagem que a motivou:** "a casa inteira veio num comando"

### F-2 · Barrar release fora do padrão no commit
- **O que faz:** o portão confere bump, espelho no catálogo, vendoring e a regra do repo público antes de deixar o commit sair.
- **Origem:** jornada "Publicar uma mudança de plugin" · Art. 4 · Rigor (constituicao.md)
- **Passagem que a motivou:** "o portão recusa o commit e diz o quê"

### F-3 · Medir o repositório inteiro por uma casa só
- **O que faz:** a esteira seleciona e roda todas as suítes; o CI roda o mesmo bloco nos três sistemas.
- **Origem:** decisão "O gate local e o CI rodam o MESMO bloco" (solution-strategy.md)
- **Passagem que a motivou:** "veredito que muda entre a máquina e o CI é veredito em que ninguém confia"

### F-4 · Compartilhar código sem quebrar a instalação avulsa
- **O que faz:** `_shared/` é a fonte; o sync vendora as cópias e acusa drift.
- **Origem:** decisão "Código compartilhado nasce em `_shared/` e viaja vendorado"
- **Passagem que a motivou:** "plugin instalado tem que ser autocontido"

### F-5 · Conceber um projeto em seis acordos
- **O que faz:** `/start` entrevista (ou infere ex-post) e cada etapa só fecha com aprovação gravada com marca.
- **Origem:** jornada "Conceber um projeto com a metodologia"
- **Passagem que a motivou:** "a régua existe e o /doc-load a carrega"

### F-6 · Carregar a régua por programa
- **O que faz:** `/doc-load` diz o que vale como lei, o que é acordo e o que é só mapa — com a lacuna gritada primeiro.
- **Origem:** jornada "Conceber um projeto com a metodologia" · fronteira "Skill → motor de skill"
- **Passagem que a motivou:** "contagem nunca sai do olho do modelo"

### F-7 · Plano que não se perde
- **O que faz:** o plano vira arquivo com id fixo; marcar passo exige prova; a página é desenhada pelo programa.
- **Origem:** jornada "Executar um plano noite adentro"
- **Passagem que a motivou:** "tique com prova"

### F-8 · Executar sozinho a noite inteira
- **O que faz:** o `/sprint` arma sinal e reserva, despacha ondas com revisor por tarefa e entrega relatório em página em todo desfecho — concluída, parada ou derrubada. [PENDENTE: a regra do relatório em todo desfecho é obra do plano aberto (fase F6)]
- **Origem:** jornada "Executar um plano noite adentro"
- **Passagem que a motivou:** "passos marcados com prova e commits publicados"

### F-9 · Revisar até valer a pena, nunca até zero
- **O que faz:** `/qa-loop` para por retornos decrescentes, com regression gate por conserto e gate absoluto no fim.
- **Origem:** jornada "Revisar até valer a pena"
- **Passagem que a motivou:** "loop até zero — proibido de propósito"

### F-10 · Toda decisão chega como página com prova
- **O que faz:** o `/visual` monta a página com o artefato e a saída crua embutidos; o construtor recusa decisão sem prova.
- **Origem:** jornada "Ser consultado numa rodada de decisões" · blueprint.md · "Onde o humano entra" · decisão "Toda decisão chega como página com prova" (solution-strategy.md)
- **Passagem que a motivou:** "Dá o veredito nas páginas de decisão — manter, mudar, remover" (blueprint.md)

### F-11 · Medir a completude da cadeia
- **O que faz:** `/completude` mede feature → requisito → tarefa → prova e nomeia o elo furado.
- **Origem:** peça "Motor de skill" · constituicao.md · Artigo 4 · Rigor
- **Passagem que a motivou:** "Gate que não consegue medir tem que **dizer que não mediu**" (constituicao.md, Artigo 4)

### F-12 · Documentar o que o código já sabe
- **O que faz:** `/doc` minera a doc e o grafo é atualizado no mesmo gatilho, sem opção; os diagramas acompanham no `/doc-touch` (passo 2b) — camadas da mesma documentação, nunca acessório.
- **Origem:** peça "Motor de skill" · fronteira doc minerada vs autoral (glossary.md)
- **Passagem que a motivou:** [DITO POR VOCÊ] "grafo é documentação, tem que assumir que faz parte, não tem que ser opcional (…) nem dá opção pro usuário"

### F-15 · Prototipar antes de construir
- **O que faz:** o protótipo cobre a jornada padrão, a tela de erro, a de configuração e a de governança; aprovado, vale como documentação canônica e a implementação o segue à risca. [PENDENTE: a etapa de protótipo ainda não existe no /start — é obra do plano aberto (fase F13)]
- **Origem:** jornada "Conceber um projeto com a metodologia"
- **Passagem que a motivou:** [DITO POR VOCÊ] "os protótipos equivalem a documentação canônica (…) é um sistema, não é brincadeira de criança"

### F-16 · Disputar contra um produto real até passar da barra
- **O que faz:** o objetivo quebra em peças julgáveis, cada uma com construtor e juiz cego separados; nada fecha sem veredito gravado.
- **Origem:** decisão "A disputa é equipe visível" (solution-strategy.md)
- **Passagem que a motivou:** "o dono vê cada agente, dirige em voo, veta e para"

### F-17 · Vistoriar os arquivos de instrução procurando defeito
- **O que faz:** lê os arquivos de instrução inteiros por lentes (umas medidas por programa, outras lidas por agente) e devolve achados com prova para o dono marcar.
- **Origem:** peça "Skill" · Art. 7 · Clareza da instrução
- **Passagem que a motivou:** "ninguém nunca leu os arquivos de instrução deste marketplace inteiros procurando defeito"

### F-18 · Autopsiar uma missão que já terminou
- **O que faz:** mede o que cada papel custou em turnos, acende os sinais de defeito por contagem e entrega parecer — investiga e propõe, nunca conserta.
- **Origem:** decisão "Quem diagnostica propõe" (solution-strategy.md)
- **Passagem que a motivou:** "uma skill forense que também executa a sentença perde a neutralidade"

### F-13 · Guardar a sessão e retomar do mesmo ponto
- **O que faz:** `/handoff` grava o estado da sessão e a retomada lê o plano vivo do disco, nunca da memória.
- **Origem:** jornada "Guardar e retomar o trabalho"
- **Passagem que a motivou:** "a retomada começa de onde parou, com os ids e títulos exatos do plano"

### F-14 · Manter a doc viva entre ciclos
- **O que faz:** `/doc-touch` re-projeta só os docs que o diff tocou; `/doc` FULL re-minera quando o drift é estrutural.
- **Origem:** jornada "Manter a doc viva"
- **Passagem que a motivou:** "a doc que os agentes leem descreve o código de hoje"

### F-19 · Herdar do organismo na concepção do módulo novo
- **O que faz:** levanta por programa o que a raiz já decidiu e apresenta item a item, com fonte, para o dono confirmar, ressalvar ou dispensar.
- **Origem:** jornada "Criar um aplicativo dentro de um organismo que já existe"
- **Passagem que a motivou:** "a palavra não é copia, a palavra é herda"

### F-20 · Extinguir ou fundir plugin sem deixar resto
- **O que faz:** deriva por varredura a lista de superfícies do nome morto e as fecha no mesmo lote — nada fica inerte apontando para o que não existe.
- **Origem:** jornada "Extinguir ou fundir um plugin"
- **Passagem que a motivou:** "a lista de superfícies não se lembra, se DERIVA"

## Deixado de fora de propósito
- **Enumerar os plugins um a um aqui** — o inventário plugin a plugin é do architecture.md minerado; esta lista é das capacidades do organismo.
- **Registry de pacotes (npm/pip)** — a distribuição é git; ver constraints.md.
- **Telemetria e serviço hospedado** — nada sai da máquina de quem instala.
- **Auto-update silencioso** — atualizar é ato do dono da máquina; update forçado quebraria confiança e sessões abertas.
