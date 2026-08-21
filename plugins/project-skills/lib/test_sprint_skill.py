#!/usr/bin/env python3
"""A SKILL.md do sprint tem que cobrar `requisito` e `pronto` em cada tarefa.

O defeito que isto impede: a decomposicao entregava tarefa sem dizer que requisito
ela atende nem o que conta como feito. O executor cumpria o que quisesse e o revisor
nao tinha regua — a falta passava calada. A suite cobra os tres pontos onde o par
precisa aparecer: o schema DECOMP (obrigatorio, copiado da spec), o prompt do #1
(campo da spec, nunca redigido pelo decompositor) e o BUILD_REVIEW (eixo de rastreio
que reprova, com o script segurando o gap acima do floor).
"""

import os
import sys

SKILL_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "skills", "sprint", "SKILL.md")

FAILS = []


def check(label, cond):
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s" % label)
        FAILS.append(label)


def secao(texto, inicio, fim):
    i = texto.find(inicio)
    if i < 0:
        return ""
    j = texto.find(fim, i)
    return texto[i:j if j > 0 else len(texto)]


def main():
    texto = open(SKILL_MD, encoding="utf-8").read()

    # O papel #1 virou ORQUESTRADOR (autopsia 2026-08-09, decisao do dono).
    decompositor = secao(texto, "- **OPUS #1 — Orquestrador.", "- **EXECUTORES")
    revisor = secao(texto, "- **OPUS #2 — Revisor de construção.", "- **DIAGNÓSTICO")
    schema_decomp = secao(texto, "- `DECOMP` —", "- `TASK_RESULT`")
    schema_review = secao(texto, "- `BUILD_REVIEW` —", "\n\nO `stopReason`")

    print("o schema DECOMP declara os dois campos como obrigatorios")
    check("o schema DECOMP existe", bool(schema_decomp))
    check("a tarefa carrega `requisito` e `pronto`",
          "requisito, pronto" in schema_decomp)
    check("os dois sao obrigatorios",
          "obrigatórios" in schema_decomp)
    check("sao copiados da spec, nao redigidos pelo decompositor",
          "copiados da spec" in schema_decomp and "não redigidos" in schema_decomp)

    print("o prompt do #1 manda copiar da spec e bloquear quando falta")
    check("o papel do #1 existe", bool(decompositor))
    check("o #1 marca `requisito` e `pronto` na tarefa",
          "`requisito`" in decompositor and "`pronto`" in decompositor)
    check("os dois saem da spec, nunca redigidos ali",
          "saem da spec" in decompositor and "nunca redigidos aqui" in decompositor)
    check("item da spec sem os dois vira Bloqueio, nao tarefa",
          "não vira tarefa" in decompositor and "Bloqueio" in decompositor)

    print("o BUILD_REVIEW carrega o eixo e a skill descreve a reprovacao")
    check("o schema BUILD_REVIEW existe", bool(schema_review))
    check("o kind 'rastreio' esta no schema", "'rastreio'" in schema_review)
    check("o gap de rastreio nasce >= severityFloor",
          "severityFloor" in secao(schema_review, "`kind: 'rastreio'`", "`kind: 'spec'`"))
    check("o revisor lista o eixo de rastreio", "rastreio" in revisor)
    check("a skill descreve a reprovacao da tarefa sem os campos",
          "sem `requisito` ou sem `pronto`" in revisor and "reprova" in revisor)
    check("o script segura o gap de rastreio no filtro (nao so a prosa)",
          "g.kind === 'rastreio'" in texto)

    # A armacao ensinava `rm -f {ativo,bloqueios}-$sid`, que alcanca 2 dos 8 prefixos
    # de estado — onda-, placar-, doc-, sinal-, trabalho- ficavam pra tras.
    armacao = secao(texto, "### O sinal que arma o gate", "### Por que o gate precisou nascer")
    print("a armacao do sinal ensina a MESMA receita de encerramento do passo 3")
    check("a secao de armacao existe", bool(armacao))
    check("a armacao nao ensina mais `rm -f` do sinal",
          "rm -f" not in armacao)
    check("a armacao manda `arma <sid> sprint <motor>`",
          'arma "$CLAUDE_CODE_SESSION_ID" sprint "$SPRINT_MOTOR_ID"' in armacao)
    check("a armacao nao acende o sinal com printf no arquivo",
          "printf" not in armacao.replace("`printf`", ""))
    check("a armacao manda `encerra <sid> sprint`",
          'encerra "$CLAUDE_CODE_SESSION_ID" sprint' in armacao)
    check("a prosa da expiracao cobra o `encerra`, nao o `rm`",
          "não te dispensa do `encerra`" in armacao)

    # F5.7 — o ciclo de vida do sinal e da CASCA, em volta da chamada. Medido pela
    # sessao irma: das 5 corridas, as 4 que sairam sozinhas apagaram o sinal e a
    # unica morta por fora (TaskStop) deixou aceso 4h — porque o ultimo ato vivia
    # dentro do script, que morreu junto. Sem estas assercoes a receita volta a
    # ensinar "apague ao entregar o relatorio", que nao roda quando a missao morre.
    print("o sinal nasce e morre em volta da CHAMADA do Workflow")
    check("a receita acende ANTES da chamada",
          "ANTES da chamada" in armacao)
    check("a receita apaga NO RETORNO da chamada",
          "NO RETORNO da chamada" in armacao)
    check("o acender vem antes do apagar na receita",
          0 < armacao.find('arma "$CLAUDE_CODE_SESSION_ID"')
          < armacao.find('encerra "$CLAUDE_CODE_SESSION_ID"'))
    check("apagar vale em qualquer desfecho, inclusive parada por fora",
          "qualquer desfecho" in armacao and "TaskStop" in armacao)
    check("apagar vem antes da QA, do commit e do relatorio",
          "antes da QA, do commit e do relatório" in armacao)

    # F5.8 — a MESMA receita do retorno solta a reserva de arquivos. TaskStop numa
    # corrida madura deixaria a reserva pendurada e o proximo motor da sessao seria
    # recusado por ate 12h. Sem estas assercoes, liberar volta a morar so no passo 3
    # da Persistencia, que a missao morta nunca alcanca.
    retorno = secao(armacao, "# 2) NO RETORNO da chamada", "```\n\n⚠️")
    print("o retorno da chamada tambem LIBERA as reservas de arquivos")
    check("o bloco do retorno existe", bool(retorno))
    check("o retorno roda o `liberar` do hook de reserva",
          'liberar "$CLAUDE_CODE_SESSION_ID" "$MOTOR_MORTO"' in retorno)
    check("o retorno solta a reserva do motor MORTO, nao a da sessao inteira",
          'reservas/$CLAUDE_CODE_SESSION_ID"__' not in retorno)
    check("o encerra e o liberar falam do MESMO motor",
          retorno.count('"$MOTOR_MORTO"') >= 2)
    check("a receita avisa que o motor vivo da sessao nao pode ser solto",
          "vivo escrevendo os mesmos arquivos" in retorno)
    check("o retorno resolve o hook da reserva pelo resolvedor",
          "project-skills hooks/reserva-de-arquivos.sh" in retorno)

    # F24.2 — a linha do ledger nasce no MESMO retorno, escrita pelo programa a
    # partir do JSON que o Workflow devolveu. Sem estas assercoes a receita volta a
    # deixar o numero da corrida na memoria da sessao, que e onde ele morre.
    print("o retorno da chamada tambem GRAVA a linha do ledger da corrida")
    check("o retorno chama o registrador do ledger",
          "ledger_corridas.py" in retorno and "registra-run" in retorno)
    check("o ledger e resolvido pelo resolvedor, sem caminho a mao",
          "project-skills lib/ledger_corridas.py" in retorno)
    check("a entrada sai do JSON que o Workflow devolveu, colado literal",
          "COLADO LITERAL" in retorno and "o JSON que o Workflow devolveu" in retorno)
    check("a receita nomeia os campos que saem do retorno do motor",
          "`progresso.feitos`" in retorno and "`gasto`" in retorno
          and "`stopReason`" in retorno)
    check("a receita proibe redigir o numero de memoria",
          "nunca da sua memória" in retorno)
    check("a receita diz que campo vazio o programa RECUSA",
          "Campo obrigatório vazio o programa RECUSA" in retorno)
    check("a corrida e identificada pelo mesmo motor que morreu",
          '--run-id "$MOTOR_MORTO"' in retorno)
    check("a largada e impressa pelo bloco 1, nao chutada no retorno",
          "$(date +%s)" in armacao and 'SPRINT_INICIO="…"' in retorno)

    # O passo 3 da Persistencia deixou de ser o lugar onde o sinal cai nem onde a
    # reserva e solta: la e repeticao idempotente do caminho feliz.
    passo3 = secao(texto, "3. **Confere o sinal apagado", "4. **Passa o caminhão do lixo")
    print("o passo 3 da Persistencia virou rede, nao o lugar do apagamento")
    check("o passo 3 existe com o novo titulo", bool(passo3))
    check("o passo 3 diz que o sinal ja caiu no retorno da chamada",
          "no retorno da chamada" in passo3)
    check("a tabela de camadas credita a casca em volta da chamada",
          "a **casca**, em volta da chamada" in passo3)

    # F6.2 — o cobrador da regra dos tres desfechos (F6.1). Regra em prosa sem
    # cobrador nao pega: a entrega em pagina era condicional e nenhum texto cobria a
    # missao que PARA, que e justamente quando o usuario mais precisa da superficie
    # de revisao para decidir se retoma.
    desfechos = secao(texto, "### Os três desfechos", "### Conteúdo")
    print("a skill nomeia os tres desfechos e o que lidera a pagina em cada um")
    check("a secao dos desfechos existe", bool(desfechos))
    for desfecho, lidera in (("obra pronta", "### Feito"),
                             ("parada", "### Bloqueios"),
                             ("espera", "### Esperando você")):
        check("o desfecho '%s' aparece com o que lidera a pagina" % desfecho,
              ("**%s**" % desfecho) in desfechos and lidera in desfechos)
    check("a espera NAO cai em Bloqueios (e a secao dela, nao a do que falhou)",
          "nunca** dentro de `### Bloqueios`" in desfechos)
    check("parada nao degrada o relatorio",
          "Parada NÃO degrada o relatório" in desfechos)
    check("proibido trocar a pagina por texto curto por causa da parada",
          "trocar a página por texto curto por causa da parada é proibido" in desfechos)
    check("o unico fallback continua sendo a skill visual ausente",
          "só quando a skill `visual` não existe na máquina" in desfechos)

    # F11.3 — o cartao de fechamento da frente (R-20). O programa ja emite o bloco
    # `pt-frente-fechar`, mas quem monta a pagina do relatorio e a casca: sem esta
    # secao a arvore ficava de fora, a branch continuava viva na maquina e ninguem
    # decidia nada sobre ela.
    frente = secao(texto, "### A frente aberta sai na página", "### Conteúdo")
    print("a skill manda o cartao de fechamento da frente sair na pagina do relatorio")
    check("a secao da frente existe", bool(frente))
    check("fechar o plano nao fecha a branch esta escrito",
          "Fechar o plano não fecha a branch" in frente)
    check("o cartao traz os comandos de fechamento",
          "git worktree remove" in frente and "git branch -d" in frente)
    check("a decisao do dono e mesclar, manter ou descartar",
          "mesclar, manter ou descartar" in frente)
    check("quem escreve o cartao e o programa, pelo bloco pt-frente-fechar",
          "pt-frente-fechar" in frente and "plan_state.py" in frente)
    check("a pagina inclui a arvore em vez de descrever o plano em prosa",
          "inclui a árvore do plano" in frente)
    check("o comando que monta a arvore esta no texto",
          "resolve-plugin.sh\" project-skills lib/plan_state.py" in frente
          and "page <planId>" in frente)
    check("vale nos tres desfechos, inclusive na missao que parou",
          "três desfechos" in frente and "parou" in frente)
    check("plano sem frente nao inventa cartao",
          "sem `frente` gravada" in frente)

    # F6.3 — a secao de custo deriva os tres numeros de programa. Sem cobrador, o
    # relatorio volta a dizer "levou umas tres horas e uns 8M de tokens" de memoria,
    # que e palpite com cara de medicao.
    custo = secao(texto, "### Custo (medidor da autópsia)", "### Entrega via /visual")
    print("a secao de custo deriva duracao, tokens e placar do medidor e do plano")
    check("a secao de custo existe", bool(custo))
    check("a duracao sai do tempo da linha do ledger",
          "`tempo.fim` − `tempo.inicio`" in custo)
    check("os tokens saem do custo da linha e a tabela do medidor",
          "`custo.tokens`" in custo and "tabela do medidor" in custo)
    check("o placar sai do progresso da linha, com o total do plano",
          "`progresso.fechadas`" in custo and "`progresso.total`" in custo
          and "tamanho da fila do plano" in custo)
    check("a memoria do modelo esta proibida como fonte",
          "nunca da sua memória do que aconteceu" in custo)
    check("o comando que le a linha desta corrida esta no texto",
          "ledger_corridas.py" in custo and "le --project-root" in custo)
    check("o que nao foi medido sai como nao medido, nunca inventado",
          "como `não medido`" in custo)
    check("a secao sai igual nos tres desfechos",
          "igual nos três desfechos" in custo)

    # F23.7 — a secao de problemas do relatorio final e DERIVADA do registro por
    # parada (desfecho, causa, conserto, sha), lido por comando. Sem cobrador, ela
    # volta a ser a memoria da sessao — e memoria da lembrado como consertado.
    prob = secao(texto, "São **sete** seções", "### Entrega via /visual")
    print("a secao de problemas deriva do registro por parada, nunca da memoria")
    check("a secao de problemas existe no backbone",
          "### Problemas (as paradas do laço)" in texto)
    check("o item da secao sai do registro, com os quatro campos",
          "subcomando `paradas`" in texto
          and "desfecho · causa · conserto · sha" in texto)
    check("a derivacao esta escrita, e a memoria da sessao esta proibida",
          bool(prob) and "derivada do registro por parada" in prob
          and "nunca da memória da sessão" in prob)
    check("o comando que le as paradas esta no texto",
          bool(prob) and "ledger_corridas.py" in prob
          and "paradas --project-root" in prob)
    check("parada que nao esta no registro nao entra na secao",
          bool(prob) and "não entra" in prob and "não a lembrança" in prob)
    check("registro vazio nao inventa secao",
          bool(prob) and "a seção não sai" in prob)


    # F6.4 — a proibicao do `plugin update` durante a missao. Sem cobrador, a frase
    # some na proxima edicao e a corrida volta a poder ficar meia nova, meia velha.
    update = secao(texto, "### `claude plugin update` está PROIBIDO",
                   "### Knobs deste motor")
    print("a skill proibe `claude plugin update` durante a missao, com o motivo")
    check("a secao da proibicao existe", bool(update))
    check("a proibicao alcanca casca, papel e executor",
          "nem a casca, nem" in update and "executor" in update)
    check("o motivo nomeia o resolvedor pegando a versao mais alta do cache",
          "versão mais alta" in update and "cache do marketplace" in update)
    check("o motivo diz que so vale depois de reiniciar",
          "depois de reiniciar" in update)
    check("o motivo nomeia a corrida meio nova, meio velha",
          "meio nova, meio velha" in update)
    check("a saida e terminar, atualizar, reiniciar e disparar de novo",
          "Termine a missão, atualize, reinicie" in update)

    # Sem isto o bullet da fronteira some na proxima edicao e o revisor de
    # construcao volta a tratar buraco de projeto inteiro como gap da missao.
    fronteira = secao(texto, "### Fronteira com o `/qa-loop`",
                      "### O ciclo curto é por BLOCO")
    print("a fronteira com a /completude esta escrita")
    check("a secao de fronteira existe", bool(fronteira))
    check("o bullet diz que a /completude cobre quem sobrou de fora",
          "**A `/completude` (fora da missão) garante que não SOBROU ninguém de fora**"
          in fronteira)
    check("o bullet nega que elo da /completude vire gap daqui",
          "Não é dele, e não vira gap aqui." in fronteira)
    check("o resumo tem a linha da /completude",
          'completude = "sobrou alguém de fora?"' in fronteira)

    # A seção de racionalizações: a desculpa fica REFUTADA no texto antes de o
    # modelo dá-la. Sem cobrador, a próxima edição a apaga e ninguém percebe.
    print("as racionalizações estão refutadas por escrito")
    rac = secao(texto, "## Racionalizações", "\n## ")
    check("a skill tem a seção de racionalizações", rac != "")
    check("a desculpa do resto trivial está refutada",
          "o que sobrou é trivial" in rac)
    check("a desculpa de decidir sem anotar está refutada",
          "o dono não está aqui" in rac)
    check("a desculpa do teto estourado está refutada", "passei do teto" in rac)
    check("a desculpa da troca de critério está refutada",
          "troquei por um equivalente" in rac)

    # F12.7 — o sprint decide sozinho por definicao; adiar por "falta material"
    # devolve ao dono uma espera que ninguem investigou.
    print("adiar decisao por falta de material esta proibido")
    check("a proibicao esta escrita",
          "Decidir depois é opção, nunca necessidade" in texto
          and "Falta de material não adia decisão" in texto)
    check("manda investigar ate a decisao ficar decidivel",
          "Investigar até a decisão ficar decidível" in texto)
    check("espera sem investigacao esta nomeada como etapa encoberta",
          "sem investigação é etapa encoberta" in texto)
    check("a desculpa de deixar pendente por falta de material esta refutada",
          "falta material para decidir, deixo pendente para o dono" in rac)

    # F12.4 — a varredura de pendencias LE o arquivo do plano e IMPRIME antes do
    # disparo. Sem cobrador, a casca volta a largar com passo preso por decisao do
    # dono na fila: nove deles entraram numa corrida como trabalho e voltaram como
    # churn. O bloco tem que nascer e morrer sozinho — foi variavel vinda de outro
    # bloco que quebrou a corrida 8.
    varredura = secao(texto, "### As pendências do plano são lidas",
                      "### Os ids do plano vão no `args`")
    print("a varredura le as pendencias do arquivo do plano e as imprime antes do disparo")
    check("a secao da varredura existe", bool(varredura))
    check("ela le o arquivo do plano, nao a memoria da conversa",
          ".claude/plans/*.plan.json" in varredura
          and "nunca a sua memória" in varredura)
    check("ela le o campo `pendencia` de cada passo",
          "`pendencia` de cada passo" in varredura)
    check("o programa abre o arquivo e varre os passos",
          "json.load(open(sys.argv[2]" in varredura
          and 'fase.get("items", [])' in varredura)
    check("quem julga se a pendencia trava e a funcao do plan_state, importada",
          "pendencia_viva" in varredura and "importada" in varredura)
    check("a varredura IMPRIME o que achou",
          'print("PRESO %s' in varredura and 'print("PENDENCIAS=%d' in varredura)
    check("pendencia aberta impede o disparo",
          "não dispare" in varredura)
    check("o bloco nasce e morre sozinho (as variaveis usadas sao definidas nele)",
          all(("%s=" % v) in varredura for v in ("PLAN_STATE", "PLANO")))
    check("a varredura vem ANTES do disparo do Workflow",
          0 < texto.find("### As pendências do plano são lidas")
          < texto.find("Workflow({ scriptPath: MOTOR"))

    # F13.8 — a fidelidade ao design aprovado em dois niveis. Sem cobrador, a
    # divisao some na proxima edicao e todo pixel fora do lugar volta a segurar a
    # obra em serie — ou pior, acabamento e estrutura viram a mesma coisa e o
    # revisor decide sozinho o que bloqueia.
    fidelidade = secao(texto, "### A fidelidade ao design aprovado tem DOIS níveis",
                       "**A suíte é a MESMA")
    print("a fidelidade ao aprovado tem dois niveis e a conferencia visual e por onda")
    check("a secao da fidelidade existe", bool(fidelidade))
    check("divergencia de estrutura segura a obra em >= P1",
          "Divergência de ESTRUTURA segura a obra" in fidelidade
          and "≥ P1" in fidelidade)
    check("o arquivo divergente entra nos arquivos da onda do revisor",
          "entra nos arquivos da onda que o\n  revisor recebe" in fidelidade
          or "entra nos arquivos da onda" in fidelidade)
    check("acabamento vira nota P3, nunca bloqueio",
          "ACABAMENTO vira NOTA" in fidelidade and "P3" in fidelidade
          and "nunca bloqueio" in fidelidade)
    check("a conferencia visual e 1x por onda, so superficies tocadas",
          "1× por ONDA" in fidelidade and "superfícies tocadas" in fidelidade)
    check("a conferencia olha o render, nao so o DOM",
          "print analisado" in fidelidade and "não leitura de DOM" in fidelidade)
    check("a data da conferencia vive no relatorio, nunca no artefato",
          "vive no relatório da onda, nunca no artefato" in fidelidade)

    # F13.13 — o marcador de dado ficticio se grepa por onda nos arquivos de
    # produto. Sem cobrador, o grep some da skill e o ficticio do prototipo vaza
    # para producao sem ninguem olhar.
    print("o marcador de dado ficticio e grepado por onda nos arquivos de produto")
    check("a skill escreve o token literal e o grep por onda",
          "marcador de dado fictício se grepa por ONDA" in fidelidade
          and 'grep -rn "DADO-FICTICIO"' in fidelidade)
    check("o token vem do frontmatter do sidecar, com a lei citada",
          "marcador-ficticio" in fidelidade and "FORMATO.md" in fidelidade)
    check("a casa do prototipo fica fora do grep, e achado nasce >= P1",
          "excluindo a casa do protótipo" in fidelidade
          and fidelidade.count("≥ P1") >= 2)

    # F31.1 — a casca abre a FRENTE da missao antes do primeiro executor (R-42).
    # Sem cobrador, a largada volta a trabalhar na main: a medicao de 2026-08-20
    # achou 7 branches locais e 5 remotas orfas, e uma worktree em /tmp de sessao
    # morta ha 3 dias. Os checks sao uma FUNCAO porque a mutacao abaixo os roda de
    # novo sobre um texto sem a abertura — e exige que fiquem vermelhos.
    def checks_frente_abre(txt, sec):
        return [
            ("a secao da abertura da frente existe", bool(sec)),
            ("a largada e idempotente e nao duplica nada",
             "idempotente" in sec and "não\nduplica nada" in sec),
            ("caminho 1: frente gravada e branch viva reusa, nada se cria",
             "reusa: nada se cria" in sec
             and 'git show-ref --verify --quiet "refs/heads/$BRANCH"' in sec),
            ("caminho 2: sem frente, a branch frente/<id> nasce da main, nunca do HEAD",
             "frente/$PLAN_ID" in sec
             and 'git branch "$BRANCH" "${MAIN:-main}"' in sec
             and "nunca do HEAD" in sec),
            ("a worktree mora em ~/.claude/worktrees/<repo>/<plan-id>",
             '$HOME/.claude/worktrees/' in sec
             and 'git worktree add "$WORKTREE" "$BRANCH"' in sec),
            ("caminho 3: branch gravada que sumiu renasce da main, com o mesmo nome",
             "branch sumiu" in sec and "recria da" in sec
             and "mesmo nome gravado" in sec),
            ("os dois se gravam no plano pelo comando frente do plan_state",
             'frente "$PLAN_ID" "$BRANCH" "$WORKTREE"' in sec),
            ("o repoRoot passado ao motor e a WORKTREE",
             "que a casca passa ao motor é a WORKTREE" in sec
             and "repoRoot: $WORKTREE" in sec),
            ("o plano e os tiques ficam na arvore principal",
             "plano e os tiques ficam na árvore principal" in sec),
            ("a abertura vem ANTES do disparo do Workflow",
             0 < txt.find("### A frente da missão abre")
             < txt.find("Workflow({ scriptPath: MOTOR")),
        ]

    sec_frente = secao(texto, "### A frente da missão abre",
                       "### `claude plugin update`")
    print("a casca abre a frente da missao antes do primeiro executor, idempotente")
    for label, cond in checks_frente_abre(texto, sec_frente):
        check(label, cond)

    # A MUTACAO: o texto sem a abertura tem que deixar estes checks vermelhos —
    # prova de que a suite seguraria a proxima edicao que apagar a secao.
    mutante = texto.replace(sec_frente, "")
    sec_mut = secao(mutante, "### A frente da missão abre",
                    "### `claude plugin update`")
    check("MUTACAO: remover a abertura da frente deixa a suite vermelha",
          bool(sec_frente)
          and not all(c for _, c in checks_frente_abre(mutante, sec_mut)))

    # O comando `frente` do plan_state grava o par de verdade (nao so prosa):
    # roda num plano descartavel e le o arquivo de volta. Meia frente e recusada.
    import json
    import subprocess
    import tempfile
    plan_state = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "plan_state.py")
    d = tempfile.mkdtemp(prefix="sprint-frente-")
    caminho = os.path.join(d, "2026-01-01-x.plan.json")
    with open(caminho, "w", encoding="utf-8") as fh:
        json.dump({"id": "2026-01-01-x", "title": "Plano de teste da frente",
                   "phases": [{"id": "F1", "title": "Fase um",
                               "items": [{"id": "F1.1", "status": "todo",
                                          "title": "Um passo qualquer de teste"}]}],
                   "created": "2026-01-01", "status": "active"}, fh)
    print("o comando frente do plan_state grava branch + worktree no plano")
    r = subprocess.run([sys.executable, plan_state, "--dir", d, "frente",
                        "2026-01-01-x", "frente/2026-01-01-x", d],
                       capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, start_new_session=True)
    gravado = json.load(open(caminho, encoding="utf-8")).get("frente") or {}
    check("o comando sai 0 e o plano carrega o par",
          r.returncode == 0
          and gravado == {"branch": "frente/2026-01-01-x", "worktree": d})
    r2 = subprocess.run([sys.executable, plan_state, "--dir", d, "frente",
                         "2026-01-01-x", "so-branch", ""],
                        capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, start_new_session=True)
    check("meia frente (sem worktree) e recusada",
          r2.returncode != 0 and "frente incompleta" in r2.stderr)

    # F31.2 — o fechamento da frente e rito da persistencia, na ordem numerada e
    # condicionado a entrega (R-42). Os checks sao uma FUNCAO porque as mutacoes
    # abaixo os rodam sobre textos sem a condicao, sem a tag e sem a sincronizacao
    # com a main — e exigem que cada um deixe a suite vermelha.
    def checks_frente_fecha(sec):
        return [
            ("o rito do fechamento existe na Persistencia", bool(sec)),
            ("a condicao esta escrita: so com QA verde E suite verde na worktree",
             "só com QA verde E suíte verde na worktree" in sec),
            ("(1) a tag de resgate rescue/<data>-<branch> vem primeiro",
             'git tag "rescue/' in sec and "vem primeiro de propósito" in sec),
            ("(2) a main entra NA frente antes de a frente entrar na main",
             "git merge main" in sec
             and "sincroniza a main NA frente" in sec),
            ("(2) conflito vira Bloqueio nomeado com a frente viva, nunca merge forcado",
             "conflito NÃO se resolve na força" in sec
             and "Bloqueio nomeado" in sec and "git merge --abort" in sec),
            ("(3) a suite roda DE NOVO pos-sincronizacao, e vermelho para o rito",
             "pós-sincronização" in sec
             and "suíte vermelha pós-sincronização" in sec),
            ("(4) o merge na main e --no-ff, com push",
             'git merge --no-ff "$BRANCH" && git push' in sec),
            ("(5) e (6): worktree remove e branch -d, nunca -D",
             'git worktree remove "$WORKTREE"' in sec
             and 'git branch -d "$BRANCH"' in sec and "nunca -D" in sec),
            ("(7) a frente sai do plano pelo cartorio, frente --encerrar",
             "frente <planId> --encerrar" in sec),
            ("qualquer outro desfecho deixa a frente VIVA e o cartao sai na pagina",
             "deixa a frente **VIVA**" in sec and "pt-frente-fechar" in sec),
        ]

    sec_fecha = secao(texto, "2b. **Fecha a frente", "3. **Confere o sinal apagado")
    print("o fechamento da frente e rito da persistencia, na ordem e condicionado")
    for label, cond in checks_frente_fecha(sec_fecha):
        check(label, cond)

    # AS MUTACOES do pronto: a condicao, a tag e a sincronizacao com a main — cada
    # uma removida do texto tem que deixar a suite vermelha, provando que o rito
    # nao pode ser desidratado numa edicao futura sem ninguem perceber.
    for nome, alvo in (
            ("a condicao", "só com QA verde E suíte verde na worktree"),
            ("a tag de resgate", 'git tag "rescue/'),
            ("a sincronizacao com a main", "git merge main")):
        assert alvo in sec_fecha, "a mutacao de %s nao acha o alvo" % nome
        mut = secao(texto.replace(alvo, ""),
                    "2b. **Fecha a frente", "3. **Confere o sinal apagado")
        check("MUTACAO: remover %s deixa a suite vermelha" % nome,
              not all(c for _, c in checks_frente_fecha(mut)))

    # E o passo (7) de verdade, nao so prosa: `frente --encerrar` tira o registro
    # do plano gravado acima — o cartao para de cobrar uma branch que ja morreu.
    r3 = subprocess.run([sys.executable, plan_state, "--dir", d, "frente",
                         "2026-01-01-x", "--encerrar"],
                        capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, start_new_session=True)
    depois = json.load(open(caminho, encoding="utf-8"))
    check("frente --encerrar sai 0 e o plano fica sem frente",
          r3.returncode == 0 and "frente" not in depois)

    # F31.3 — CI de codigo nao-mergeado se mede pela BRANCH DA FRENTE (R-42):
    # disparo manual com --ref na branch empurrada, e branch de sonda avulsa e
    # PROIBIDA — a frente E a sonda e morre no fechamento (rito 2b). Os checks
    # sao uma FUNCAO porque a mutacao abaixo os roda sobre o texto sem a regra.
    def checks_ci_frente(sec):
        return [
            ("a secao da medicao de CI da frente existe", bool(sec)),
            ("o disparo e gh workflow run portability.yml --ref na branch da frente",
             'gh workflow run portability.yml --ref "$BRANCH"' in sec),
            ("a skill registra que o --ref aceita branch empurrada, medido 2026-08-20",
             "`--ref` de branch empurrada" in sec and "medido 2026-08-20" in sec),
            ("a frente sobe antes do disparo, e push de branch nao dispara a esteira",
             'git push -u origin "$BRANCH"' in sec
             and "não dispara a esteira" in sec),
            ("branch de sonda avulsa e PROIBIDA",
             "sonda avulsa é PROIBIDA" in sec),
            ("a branch da frente E a sonda e morre no fechamento da frente",
             "a branch da frente É a sonda" in sec
             and "morre no fechamento" in sec),
        ]

    sec_ci = secao(texto, "### CI de código não-mergeado",
                   "### `claude plugin update`")
    print("CI de codigo nao-mergeado se mede pela frente, sem sonda avulsa")
    for label, cond in checks_ci_frente(sec_ci):
        check(label, cond)

    # A MUTACAO: o texto sem a regra tem que deixar estes checks vermelhos.
    check("MUTACAO: remover a regra do CI da frente deixa a suite vermelha",
          bool(sec_ci)
          and not all(c for _, c in checks_ci_frente(
              secao(texto.replace(sec_ci, ""),
                    "### CI de código não-mergeado",
                    "### `claude plugin update`"))))

    # F31.4 — a varredura de frente orfa roda na PERSISTENCIA (R-42): a chamada
    # a scripts/frente_orfa_check.py esta gravada na skill, guardada por [ -f ]
    # (projeto sem o varredor pula calado), achado e aviso e o check NAO mora no
    # release-gate — branch viva durante a missao e estado legitimo.
    def checks_frente_orfa(sec):
        return [
            ("o passo 2c da varredura de frente orfa existe", bool(sec)),
            ("a chamada ao varredor esta gravada na skill",
             'python3 "$MAIN_ROOT/scripts/frente_orfa_check.py" "$MAIN_ROOT"'
             in sec),
            ("projeto sem o script pula calado (guarda [ -f ])",
             '[ -f "$MAIN_ROOT/scripts/frente_orfa_check.py" ]' in sec),
            ("achado vira aviso no relatorio, nunca bloqueio",
             "aviso no relatório" in sec and "bloqueio" in sec),
            ("a skill registra que o check NAO mora no release-gate",
             "NÃO mora no release-gate" in sec),
        ]

    sec_orfa = secao(texto, "2c. **Varre as frentes órfãs",
                     "3. **Confere o sinal apagado")
    print("A varredura de frente orfa roda na persistencia, fora do release-gate")
    for label, cond in checks_frente_orfa(sec_orfa):
        check(label, cond)

    check("MUTACAO: remover a varredura de frente orfa deixa a suite vermelha",
          bool(sec_orfa)
          and not all(c for _, c in checks_frente_orfa(
              secao(texto.replace(sec_orfa, ""),
                    "2c. **Varre as frentes órfãs",
                    "3. **Confere o sinal apagado"))))

    # F22.5 — o relatorio do pre-check e conferido ANTES de armar o motor (R-32):
    # quem mediu grava, quem larga confere. A skill tem que apontar o passo, a casa
    # do artefato e os TRES motivos de recusa.
    def checks_precheck(sec, bloco):
        corrido = " ".join(sec.split())
        return [
            ("a secao do pre-check de largada existe", bool(sec)),
            ("a skill aponta o modulo do pre-check",
             "lib/precheck_largada.py" in sec),
            ("o relatorio e GRAVADO pelo --relatorio", "--relatorio" in sec),
            ("a casa do artefato e .claude/.sprint/, fora do plugin",
             ".claude/.sprint/precheck.json" in sec and "fora do git" in sec),
            ("a marca cobre os passos ABERTOS e o registro selado",
             "ABERTOS" in sec and "registro selado" in sec),
            ("os tres motivos de recusa estao escritos",
             "ausente" in sec and "vencido" in sec and "decisão em aberto" in sec),
            ("a recusa nomeia QUAL decisao esta em aberto",
             "nomeia a pergunta" in sec),
            ("a proposta pendente tambem recusa a largada",
             "proposta pendente" in sec),
            ("a aceitacao NOMEIA os achados adiados (Artigo 4)",
             "adiados" in sec and "adiável não fecha porta" in sec),
            # A agulha casa a prosa com os espaços COLAPSADOS: o texto do arquivo
            # quebra linha onde couber, e agulha presa à quebra fica vermelha em
            # qualquer reflow do parágrafo sem que a regra tenha mudado.
            ("a prova da esteira e MEDIDA aqui, e prova ausente nao fecha porta",
             "MEDIDA aqui, e a prova NÃO é gravada aqui" in corrido
             and "nunca fecha a porta" in corrido and "reaproveita" in corrido),
            ("a rodada N+1 ATUALIZA o relatorio, nunca o substitui",
             "nunca substitui o relatório das 4 passadas" in corrido),
            ("a rodada N+1 tem rota de linha de comando ate o dono (F22.8)",
             "--respostas" in sec and "nada é escrito no `.plan.json`" in sec),
            ("o bloco 1 confere ANTES de armar o motor",
             '--confere' in bloco
             and bloco.find("--confere") < bloco.find('"$ANDAMENTO" arma')),
        ]

    sec_pre = secao(texto, "### O pré-check de largada grava",
                    "### Por que o gate precisou nascer")
    bloco1 = secao(texto, "# 1) ANTES da chamada", "# 2) NO RETORNO")
    print("O pre-check de largada grava, e a casca confere antes de armar")
    for label, cond in checks_precheck(sec_pre, bloco1):
        check(label, cond)

    # A agulha da mutacao mora na LINHA sabotada: a secao entra INTACTA, so o
    # `--confere` do bloco 1 some. Passar sec="" tornava `not all(...)` verdadeiro
    # pela secao vazia, e a linha removida nunca era medida.
    check("MUTACAO: remover a conferencia do pre-check deixa a suite vermelha",
          bool(sec_pre) and bool(bloco1)
          and all(c for _, c in checks_precheck(sec_pre, bloco1))
          and not all(c for _, c in checks_precheck(
              sec_pre, bloco1.replace("--confere", "--nada"))))

    # F23.3 — a VIGILIA (`/goal` do harness) nasce e morre com o sinal do motor: acende
    # no bloco 1, logo depois do `arma`, e apaga no bloco 2, junto do `encerra`, em todo
    # desfecho de parada. Sem estas assercoes a vigilia volta a ser comando avulso que
    # alguem lembra de dar — e sprint que para na primeira parada nao e sprint.
    def corrido(bloco):
        # A agulha casa a prosa do comentario com o `# ` fora e os espacos colapsados:
        # a linha quebra onde couber, e agulha presa a quebra fica vermelha em qualquer
        # reflow do paragrafo sem que a regra tenha mudado.
        return " ".join(" ".join(x.lstrip("# ") for x in bloco.splitlines()).split())

    def checks_vigilia(b1, b2):
        c1, c2 = corrido(b1), corrido(b2)
        return [
            ("o bloco 1 acende o `/goal` do harness",
             "invoque o `/goal` do harness" in c1),
            ("a vigilia acende DEPOIS do arma e ANTES do Workflow",
             0 < b1.find('"$ANDAMENTO" arma') < b1.find("invoque o `/goal`")
             and "ANTES de chamar o Workflow" in c1),
            ("a vigilia nao e comando avulso nem opcao do dono",
             "não é comando avulso nem opção do dono" in c1
             and "nasce com o sinal do motor e morre com ele" in c1),
            ("o bloco 2 apaga o `/goal` junto do encerra",
             "apague o `/goal` do harness" in c2
             and 0 < b2.find('"$ANDAMENTO" encerra') < b2.find("apague o `/goal`")),
            ("o apagar vale em TODO desfecho de parada, um a um",
             "em TODO desfecho de parada" in c2
             and all(d in c2 for d in ("obra pronta", "teto de rodadas", "vigia",
                                       "disjuntor", "erro do `Workflow`", "TaskStop"))),
        ]

    bloco2 = secao(texto, "# 2) NO RETORNO da chamada", "# 3) A LINHA DO LEDGER")
    print("A vigilia do /goal nasce e morre com o sinal do motor")
    for label, cond in checks_vigilia(bloco1, bloco2):
        check(label, cond)

    # A MUTACAO mora na LINHA sabotada: o bloco entra intacto, so a linha que acende
    # (ou a que apaga) some — e os checks tem que ficar vermelhos.
    def sem_linha(bloco, agulha):
        return "\n".join(x for x in bloco.splitlines() if agulha not in x)

    check("MUTACAO: remover o acender da vigilia deixa a suite vermelha",
          bool(bloco1) and bool(bloco2)
          and all(c for _, c in checks_vigilia(bloco1, bloco2))
          and not all(c for _, c in checks_vigilia(
              sem_linha(bloco1, "invoque o `/goal`"), bloco2)))
    check("MUTACAO: remover o apagar da vigilia deixa a suite vermelha",
          bool(bloco2)
          and not all(c for _, c in checks_vigilia(
              bloco1, sem_linha(bloco2, "apague o `/goal`"))))

    # F23.4 — o rito da vigilia proibe remendo antes de apurar: a causa so vale com a
    # SAIDA CRUA do comando colada (nunca a memoria do que aconteceu) e so passa depois
    # de um DESAFIADOR tentar derruba-la. Sem os dois passos escritos, o laco volta a
    # consertar sintoma em cima de lembranca.
    def checks_apuracao(b1):
        c1 = corrido(b1)
        return [
            ("o rito proibe consertar antes de apurar",
             "CONSERTAR SEM APURAR É PROIBIDO" in c1
             and "antes de o laço remendar QUALQUER coisa" in c1),
            ("a proibicao vem DEPOIS de acender a vigilia, no mesmo rito",
             0 < b1.find("invoque o `/goal`") < b1.find("CONSERTAR SEM APURAR")),
            ("passo 1: a causa exige PROVA DE COMANDO com a saida crua colada",
             "PROVA DE COMANDO" in c1
             and "saída CRUA do comando" in c1
             and "COLADA literal" in c1),
            ("memoria do que aconteceu nao vale como prova",
             "memória do que aconteceu NÃO é prova" in c1),
            ("passo 2: a causa provada vai a um DESAFIADOR com ordem de derruba-la",
             "DESAFIADOR" in c1 and "ordem de DERRUBÁ-LA" in c1
             and "Desafiador mudo não referenda" in c1),
            ("sem os dois passos o laco nao conserta e nao relanca",
             "Sem os dois, o laço NÃO conserta e NÃO relança" in c1),
        ]

    print("O rito exige causa com prova de comando e desafiador antes do conserto")
    for label, cond in checks_apuracao(bloco1):
        check(label, cond)

    check("MUTACAO: tirar a exigencia da prova de comando deixa a suite vermelha",
          all(c for _, c in checks_apuracao(bloco1))
          and not all(c for _, c in checks_apuracao(
              sem_linha(bloco1, "PROVA DE COMANDO"))))
    check("MUTACAO: tirar o desafiador deixa a suite vermelha",
          not all(c for _, c in checks_apuracao(
              sem_linha(bloco1, "DESAFIADOR — a causa provada"))))

    # O laco escreve a linha na MESMA volta do conserto, e o programa recusa vazio:
    # sem o par conserto+sha a secao volta a nao distinguir consertado de lembrado.
    esc = corrido(bloco1)
    print("a vigilia grava a linha da parada a cada volta do laco")
    check("o bloco 1 manda gravar a parada a cada volta",
          "REGISTRO POR PARADA" in esc and "a cada volta do laço" in esc)
    # O comando mora num bloco PRÓPRIO, que deriva o que usa — cada bloco é uma
    # chamada à parte, e variável de outro bloco chega vazia (Artigo 8).
    bloco_parada = secao(texto, "# A PARADA vai para o disco", "```")
    pros_parada = corrido(secao(texto, "**A parada vai para o disco no seu próprio bloco.**",
                                "```bash"))
    check("o comando de gravar a parada esta num bloco proprio",
          '"$LEDGER" parada --project-root' in bloco_parada
          and all(f in bloco_parada
                  for f in ("--desfecho", "--causa", "--conserto", "--sha")))
    check("o bloco da parada deriva o que usa, sem herdar de outro bloco",
          'REPO_ROOT="' in bloco_parada and 'RUN_ID="' in bloco_parada
          and 'LEDGER="$(bash' in bloco_parada)
    check("campo vazio RECUSA, e a parada do dono tem valvula declarada",
          "cinco campos são obrigatórios e o comando recusa vazio" in pros_parada
          and "`sem-conserto` no conserto e `sem-commit` no sha" in pros_parada)
    check("parada sem linha gravada nao relanca",
          "NÃO relança sem ela" in esc)

    print()
    if FAILS:
        print("FALHOU: %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
