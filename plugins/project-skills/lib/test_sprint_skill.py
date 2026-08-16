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
