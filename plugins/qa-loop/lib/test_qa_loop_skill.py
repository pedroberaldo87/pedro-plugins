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
                        "..", "..", "project-skills", "skills", "qa-loop", "SKILL.md")

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


def roda_trava(bloco, reserva_viva, alvos):
    """Executa o bloco da skill num estado de mentira: um motor vivo registrado
    em CLAUDE_CONFIG_DIR, e a lista `alvos` como o que a revisão ia ler."""
    with tempfile.TemporaryDirectory() as tmp:
        reservas = os.path.join(tmp, "sovai", "reservas")
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
                           capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True)
        return p.stdout


def main():
    texto = open(SKILL_MD, encoding="utf-8").read()

    review = secao(texto, "**REVIEW = 1 Opus Revisor", "**CONFIRM =")
    bucket1 = secao(texto, "## CONSTRAINT CENTRAL", "2. **Plan-drift")
    bucket3 = secao(texto, "3. **Plano/arquitetura falho", "> A skill **enforça**")

    print("o prompt do REVIEW carrega as duas ancoras")
    check("o REVIEW existe na skill", bool(review))
    check("manda comparar contra o PLANO", "PLANO" in review and "DIVERGE" in review)
    check("manda ler a lei no caminho que a concepcao produz",
          ".claude/docs/constituicao.md" in review)
    check("manda ler `.claude/docs/quality-goals.md` do projeto",
          ".claude/docs/quality-goals.md" in review)
    check("a regua e lida do projeto, nao copiada na skill",
          "nunca copiado" in review or "nunca copiada" in review)
    check("fail-open: sem o arquivo o eixo nao roda e nao vira finding",
          "não roda" in review and "não é finding" in review)

    print("o REVIEW mede a obra contra o desenho aprovado")
    check("manda ler o esquema aprovado `.claude/docs/blueprint.md`",
          ".claude/docs/blueprint.md" in review)
    check("manda ler a lista de funcionalidades `.claude/docs/features.md`",
          ".claude/docs/features.md" in review)
    check("o desenho so entra quando esta aprovado",
          "status: approved" in review)

    print("o bucket 1 aceita violacao de constituicao como conserto")
    check("a constraint central existe", bool(bucket1))
    check("bucket 1 cita a constituicao alem do plano",
          "constituição" in bucket1 and "quality-goals.md" in bucket1)

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
    check("o passo 0.0 traz o comando que reserva pelo mecanismo do /sovai",
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

    print("a regua do projeto nao foi copiada pra dentro da skill")
    # As quatro checagens de estilo vivem no quality-goals.md do projeto; se
    # aparecerem aqui, a skill passou a carregar uma cópia que defasa.
    check("nao ha copia do teto de 140 caracteres",
          not re.search(r"140 caracteres por bullet", texto))

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
