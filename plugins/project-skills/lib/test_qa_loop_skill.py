#!/usr/bin/env python3
"""A SKILL.md do qa-loop tem que ancorar o review em DUAS coisas, não em uma.

O defeito que isto impede: o revisor comparava só contra o plano, então código que
cumpria o plano e violava as metas de qualidade do projeto passava limpo. A suíte
cobra os dois pontos onde a âncora de constituição precisa aparecer — e cobra que
a régua fique NO PROJETO (arquivo lido na rodada), não copiada aqui dentro.
"""

import os
import re
import subprocess
import sys
import tempfile

SKILL_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "skills", "qa-loop", "SKILL.md")
SPRINT_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
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


def bloco_bash(secao_texto):
    """O primeiro bloco ```bash de uma seção — o comando que a skill manda rodar."""
    m = re.search(r"```bash\n(.*?)```", secao_texto, re.S)
    return m.group(1) if m else ""


def orfas(bloco, preenchidos):
    """Os nomes que o bloco USA e não nascem nele — o que quebra quando o agente
    roda o bloco sozinho, porque cada ```bash é uma chamada de ferramenta à parte."""
    posto = set(re.findall(
        r"(?:^|\bthen\b|\belse\b|\bdo\b|;|&&|\|\|)\s*(?:export\s+)?([A-Z_][A-Z0-9_]*)=",
        bloco, re.M))
    posto |= set(re.findall(r"\bfor\s+([A-Z_][A-Z0-9_]*)\s+in\b", bloco))
    usado = set(re.findall(r"\$\{?([A-Z_][A-Z0-9_]*)\}?", bloco))
    return sorted(u for u in usado - posto - preenchidos
                  if not u.startswith("CLAUDE")
                  and u not in ("HOME", "PWD", "PATH", "TMPDIR", "USER"))


def placeholders(bloco, slots_ok):
    """Os `<…>` de um bloco bash que o agente teria que adivinhar."""
    return [p for p in re.findall(r"<[^<>\n]{1,40}>", bloco) if p not in slots_ok]


def roda_trava(bloco, reserva_viva, alvos):
    """Executa o bloco da skill num estado de mentira: um motor vivo registrado
    em CLAUDE_CONFIG_DIR, e a lista `alvos` como o que a revisão ia ler."""
    with tempfile.TemporaryDirectory() as tmp:
        reservas = os.path.join(tmp, "andamento", "reservas")
        os.makedirs(reservas)
        with open(os.path.join(reservas, "sessao-de-teste__motor-vivo.files"),
                  "w", encoding="utf-8") as fh:
            fh.write("\n".join(reserva_viva) + "\n")
        env = dict(os.environ)
        env.update({
            "CLAUDE_CONFIG_DIR": tmp,
            "CLAUDE_PLUGIN_ROOT": os.path.abspath(
                os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "..", "..", "project-skills")),
            "CLAUDE_SESSION_ID": "sessao-de-teste",
            "ARQUIVOS_DO_REVIEW": " ".join(alvos),
        })
        p = subprocess.run(["sh", "-c", bloco], env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
        return p.stdout


def main():
    texto = open(SKILL_MD, encoding="utf-8").read()

    review = secao(texto, "**REVIEW = 1 Opus Revisor", "**CONFIRM =")
    bucket1 = secao(texto, "## CONSTRAINT CENTRAL", "2. **Plan-drift")
    bucket3 = secao(texto, "3. **Plano/arquitetura falho", "> A skill **enforça**")

    print("o prompt do REVIEW carrega as duas ancoras")
    check("o REVIEW existe na skill", bool(review))
    check("manda comparar contra o PLANO", "PLANO" in review and "DIVERGE" in review)
    # Ate 2026-08-12 estes asserts cobravam a ENUMERACAO dos documentos de regua
    # dentro do prompt — e era isso que produzia o drift: a skill listava quatro
    # arquivos e o doc_load.py ja listava onze. Agora cobram o contrario: que a
    # skill NAO enumere, e mande rodar o programa que sabe a lista de hoje.
    check("manda RODAR o doc-load em vez de listar documento",
          "doc-load" in review)
    check("julga contra TUDO que o doc-load listar",
          "TUDO" in review and "régua" in review)
    check("a lista de documentos nao e escrita na skill",
          "não é escrita" in review or "não se escreve" in review)
    check("fail-open: sem o arquivo o eixo nao roda e nao vira finding",
          "não roda" in review and "não é finding" in review)

    print("o REVIEW nao enumera documento de regua (a premissa anti-drift)")
    for doc in ("constituicao.md", "quality-goals.md", "blueprint.md", "features.md"):
        check("o REVIEW nao carimba `.claude/docs/%s`" % doc,  # casa-ok: fixture de teste, o literal e o dado do caso
              ".claude/docs/%s" % doc not in review)  # casa-ok: fixture de teste, o literal e o dado do caso
    check("o REVIEW aponta pro contrato do tripe",
          "dimensoes-de-revisao.md" in texto)

    print("o bucket 1 aceita violacao de constituicao como conserto")
    check("a constraint central existe", bool(bucket1))
    check("bucket 1 cita a regua do doc-load alem do plano",
          "doc-load" in bucket1 and "régua" in bucket1)
    check("bucket 1 tambem acolhe finalidade sem teste que morda",
          "morda" in bucket1 or "sem teste" in bucket1)

    print("a execucao avisa que a entrevista errou, sem mexer no documento")
    check("o REVIEW manda subir o que contradiz a concepcao aprovada",
          "concepção" in review and "reabrir a etapa" in review)
    check("o bucket 3 existe", bool(bucket3))
    check("o alerta propoe reabrir a etapa", "reabrir a etapa" in bucket3)
    check("o alerta indica a linha correcao-pendente, gravada pelo dono",
          "correcao-pendente:" in bucket3)
    check("o loop nunca edita o documento de concepcao",
          "nunca edita o documento" in bucket3)

    print("a revisao recusa rodar com um motor vivo em cima dos mesmos arquivos")
    trava = secao(texto, "## CASCA — Passo 0.0", "## CASCA — Passo 0 ·")
    check("o passo 0.0 existe, antes do passo 0", bool(trava))
    check("ele explica por que revisar alvo em movimento e falso",
          "acusação falsa" in trava)
    check("manda PARAR e mostrar o motivo ao usuario",
          "PARE a skill" in trava and "permissionDecisionReason" in trava)
    check("libera a reserva no fim", "liberar" in trava)

    bloco = bloco_bash(trava)
    check("o passo 0.0 traz o comando que reserva pelo mecanismo do /sprint",
          "reserva-de-arquivos.sh" in bloco and "reservar" in bloco)
    # Não basta a prosa: o comando da skill é EXECUTADO contra um motor vivo
    # plantado, e tem que voltar recusa — e passar quando a lista é disjunta.
    saida_cruza = roda_trava(bloco, ["src/a.py", "src/b.py"],
                             ["src/b.py", "src/c.py"])
    check("lista que cruza com o motor vivo é recusada",
          '"permissionDecision":"deny"' in saida_cruza)
    check("a recusa nomeia o arquivo em disputa", "src/b.py" in saida_cruza)
    saida_disjunta = roda_trava(bloco, ["src/a.py"], ["src/z.py"])
    check("lista disjunta passa (o gate nao serializa a sessao)",
          '"deny"' not in saida_disjunta)

    print("nenhum bloco bash depende de variavel nascida em outro bloco")
    # Cada ```bash é um comando solto que o agente roda por si: variável posta
    # num bloco NÃO chega no seguinte. `python3 "$AND" encerra` virava
    # `python3 "" encerra` (rc=1) porque AND só existia no bloco de cima.
    # Só entra na lista o nome que a prosa manda o agente preencher.
    # A mesma regra vale pra SKILL.md do /sprint: `SPRINT_MOTOR_ID` nascia no bloco
    # da armação e era usado no bloco do passo 3, onde chegava VAZIO — a reserva de
    # arquivos nunca era liberada, e `liberar <sid> ''` sai 0 e mudo.
    PREENCHIDOS = {"ARQUIVOS_DO_REVIEW", "SPRINT_BUILD_CMD", "SPRINT_REPO_ROOT"}
    for skill, fonte in (("qa-loop", texto), ("sprint", open(SPRINT_MD, encoding="utf-8").read())):
        for bloco in re.findall(r"```bash\n(.*?)```", fonte, re.S):
            fora = orfas(bloco, PREENCHIDOS)
            check("%s · bloco '%s' nao usa variavel de fora: %s"
                  % (skill, bloco.strip().splitlines()[0][:48], fora or "nenhuma"),
                  not fora)
    check("um bloco que usa variavel de fora REPROVA (teste negativo)",
          orfas('echo "$VEM_DE_OUTRO_BLOCO"', PREENCHIDOS) == ["VEM_DE_OUTRO_BLOCO"])

    print("nenhum bloco bash manda o agente adivinhar um caminho")
    # `AND="$(bash "<plugin project-skills>/lib/resolve-plugin.sh" ...)"` procura um
    # arquivo com esse nome literal: AND sai vazio e a linha seguinte falha calada.
    # Só ficam de fora os dois slots que a prosa manda preencher: <rodada> (número da
    # volta) e <skill_dir>, que o harness injeta ao carregar a skill.
    SLOTS_OK = {"<rodada>", "<skill_dir>"}
    for bloco in re.findall(r"```bash\n(.*?)```", texto, re.S):
        check("bloco '%s' nao tem placeholder a adivinhar"
              % bloco.strip().splitlines()[0][:48],
              not placeholders(bloco, SLOTS_OK))
    check("um bloco com placeholder REPROVA (teste negativo)",
          placeholders('X="$(bash "<plugin project-skills>/lib/x.sh")"', SLOTS_OK)
          == ["<plugin project-skills>"])

    print("o teatro de duvida e sinal nomeado, com conduta escrita")
    # Sem NOME o padrao nao e reconhecivel na hora: o loop roda a terceira rodada
    # achando que esta convergindo, quando nenhuma das duas anteriores mexeu em nada.
    teatro = secao(texto, "### Teatro de dúvida", "\n---")
    check("a secao do sinal existe", bool(teatro))
    check("o sinal esta definido: duas rodadas, achado, zero acionavel",
          "duas rodadas" in teatro and "conserto" in teatro)
    check("nomeia o que o padrao e de verdade",
          "validação fantasiada de revisão" in teatro)
    check("a conduta manda PARAR antes da terceira rodada",
          "PARE o loop" in teatro and "terceira" in teatro)
    check("a conduta nega que isso seja sucesso",
          "não é sucesso" in teatro and "teatro-de-duvida" in teatro)

    print("a fronteira com a /completude esta escrita")
    # Sem isto a prosa some na proxima edicao e as duas skills voltam a se
    # sobrepor: gate verde daqui passa a ser lido como "a cadeia fecha".
    check("a skill nomeia a /completude", "/completude" in texto)
    check("tem secao de fronteira com a /completude",
          "## Fronteira com a `/completude`" in texto)
    # A frase quebra linha no arquivo — normaliza o branco antes de comparar,
    # senao o cobrador cai em "ausência não é finding", que e outro assunto.
    check("elo aberto la nao e finding daqui",
          "Elo aberto da `/completude` não é finding desta skill"
          in " ".join(texto.split()))

    print("a regua do projeto nao foi copiada pra dentro da skill")
    # As quatro checagens de estilo vivem no quality-goals.md do projeto; se
    # aparecerem aqui, a skill passou a carregar uma cópia que defasa.
    check("nao ha copia do teto de 140 caracteres",
          not re.search(r"140 caracteres por bullet", texto))

    # A seção de racionalizações: a desculpa fica REFUTADA no texto antes de o
    # modelo dá-la. Sem cobrador, a próxima edição a apaga e ninguém percebe.
    print("as racionalizações estão refutadas por escrito")
    rac = secao(texto, "## Racionalizações", "\n## ")
    check("a skill tem a seção de racionalizações", rac != "")
    check("a desculpa da rodada limpa está refutada",
          "a rodada veio limpa" in rac)
    check("a desculpa do P2 sobrando está refutada", "sobrou só P2" in rac)
    check("a desculpa do lint pré-existente está refutada",
          "já estava vermelho antes" in rac)
    check("a desculpa de conferir o próprio conserto está refutada",
          "eu mesmo confiro" in rac)

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
