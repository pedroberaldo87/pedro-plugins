#!/usr/bin/env python3
"""Suite do gate do anuncio sem acao.

O que importa aqui nao e o caso que ARMA — e a lista dos que NAO podem armar. Gate de
fim de turno que devolve turno legitimo treina o dono a desliga-lo, e gate desligado
nao protege ninguem. Por isso os casos negativos sao a maioria da suite.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
# Fingir o lar é receita única (_shared/lar-fingido.md): trocar só HOME deixa o
# filho escrever no lar REAL no Windows, que lê USERPROFILE primeiro.
sys.path.insert(0, AQUI)
from lar_fingido import ambiente  # noqa: E402
HOOK = os.path.join(AQUI, "stop-anuncio-sem-acao.py")
PLAN_STATE = os.path.join(AQUI, os.pardir, os.pardir, "project-skills", "lib", "plan_state.py")

FALHAS = []
TOTAL = 0


def check(nome, cond):
    global TOTAL
    TOTAL += 1
    if cond:
        print("  ok   %s" % nome)
    else:
        print("  FAIL %s" % nome)
        FALHAS.append(nome)


def monta_projeto(raiz, com_plano_aberto=True, tudo_feito=False):
    """Um projeto de mentira com marcador, pra `resolve-dir` nao cair no Desktop."""
    open(os.path.join(raiz, "CLAUDE.md"), "w", encoding="utf-8").close()
    planos = os.path.join(raiz, ".claude", "plans")
    os.makedirs(planos, exist_ok=True)
    if not com_plano_aberto:
        return planos
    st = "done" if tudo_feito else "todo"
    plano = {"id": "2026-08-02-frente", "title": "A frente em curso", "status": "active",
             "phases": [{"id": "F1", "title": "Primeira fase", "items": [
                 {"id": "F1.1", "title": "passo um", "desc": "a linha didatica",
                  "status": "done", "evidence": "prova"},
                 {"id": "F1.2", "title": "passo dois", "desc": "a linha didatica",
                  "status": st, "evidence": "prova" if tudo_feito else ""}]}]}
    with open(os.path.join(planos, "2026-08-02-frente.plan.json"), "w",
              encoding="utf-8") as fh:
        json.dump(plano, fh, ensure_ascii=False)
    return planos


def roda(raiz, texto, sessao="s1", stop_hook_active=False, env_extra=None):
    """Escreve o transcript, chama o hook, devolve (bloqueou, motivo).

    O HOME de mentira fica FORA do projeto de propósito: a busca por marcador em
    `resolve-dir.sh` para ao chegar no HOME, então projeto igual a HOME cai no
    fallback do Desktop e o gate nunca enxerga plano nenhum.
    """
    lar = os.path.join(os.path.dirname(raiz), os.path.basename(raiz) + "-home")
    os.makedirs(lar, exist_ok=True)
    trans = os.path.join(raiz, "t-%s.jsonl" % sessao)
    with open(trans, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "assistant", "message": {
            "role": "assistant",
            "content": [{"type": "tool_use", "name": "Edit",
                         "input": {"file_path": "/x/a.py"}}]}}) + "\n")
        fh.write(json.dumps({"type": "assistant", "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": texto}]}}) + "\n")
    payload = json.dumps({"session_id": sessao, "cwd": raiz,
                          "transcript_path": trans,
                          "stop_hook_active": stop_hook_active})
    env = ambiente(lar, CLAUDE_CONFIG_DIR=os.path.join(lar, ".claude"),
                   CLAUDE_PROJECT_DIR=raiz, TMPDIR=raiz,
                   ANUNCIO_ACAO_STATE=os.path.join(raiz, "estado"))
    env.pop("ANUNCIO_ACAO", None)
    env.update(env_extra or {})
    r = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=env, cwd=raiz, timeout=30, start_new_session=True)
    saida = (r.stdout or "").strip()
    if not saida:
        return False, ""
    try:
        d = json.loads(saida)
    except ValueError:
        return False, ""
    return d.get("decision") == "block", d.get("reason", "")


def main():
    raiz = tempfile.mkdtemp(prefix="anuncio-")
    try:
        monta_projeto(raiz)

        print("ARMA — a promessa que encerra o turno com trabalho em aberto")
        for i, frase in enumerate([
            "Fase 1 fechada, 5 de 41 passos. Sigo para F2.",
            "Tudo verde por aqui. Vou seguir com a próxima fase agora.",
            "F2 concluída com prova em cada passo. Em seguida, vou abrir o F3.",
            "Os testes passaram. Agora vou implementar a validação do formulário.",
            "Terminei a limpeza. Prossigo com a migração do endpoint.",
            "Commit feito. Parto para a fase de testes de integração.",
        ]):
            bloqueou, _ = roda(raiz, frase, sessao="arma-%d" % i)
            check("devolve: %s" % frase[-42:], bloqueou)

        print()
        print("NÃO ARMA — o turno que espera o usuário")
        for i, frase in enumerate([
            "Fase 1 fechada. Sigo para F2 ou você prefere revisar antes?",
            "Terminei. Posso seguir para a próxima fase?",
            "Vou seguir com a migração assim que você confirmar o caminho.",
            "Está tudo verde. Sigo para o deploy quando você mandar.",
            "Vou aplicar a mudança — me diga se prefere a variante B.",
            "Sigo para F3. Aguardo sua ordem de commit.",
        ]):
            bloqueou, _ = roda(raiz, frase, sessao="espera-%d" % i)
            check("deixa passar: %s" % frase[-42:], not bloqueou)

        print()
        print("NÃO ARMA — o texto que descreve em vez de prometer")
        for i, frase in enumerate([
            "O próximo passo é migrar o endpoint. Deixei anotado no plano.",
            "Sobrou uma pendência: a próxima fase depende de uma decisão sua.",
            "O relatório lista o que falta; a próxima etapa está descrita nele.",
            "Fechei tudo que dependia de mim.",
        ]):
            bloqueou, _ = roda(raiz, frase, sessao="descreve-%d" % i)
            check("deixa passar: %s" % frase[-46:], not bloqueou)

        print()
        print("NÃO ARMA — quando não há trabalho pendente")
        vazio = tempfile.mkdtemp(prefix="anuncio-sem-plano-")
        cheio = tempfile.mkdtemp(prefix="anuncio-plano-feito-")
        try:
            monta_projeto(vazio, com_plano_aberto=False)
            bloqueou, _ = roda(vazio, "Sigo para a próxima fase.", sessao="v1")
            check("projeto sem plano nenhum não é cobrado", not bloqueou)

            monta_projeto(cheio, tudo_feito=True)
            bloqueou, _ = roda(cheio, "Sigo para a próxima fase.", sessao="c1")
            check("plano com todos os passos feitos não é cobrado", not bloqueou)

            # o log destes dois casos mora no diretório deles, não no do projeto base
            log_vazio = os.path.join(vazio, "estado", "batidas.log")
            motivos = set()
            if os.path.isfile(log_vazio):
                with open(log_vazio, encoding="utf-8") as fh:
                    motivos = {json.loads(x).get("motivo") for x in fh if x.strip()}
            check("registra que passou por falta de plano", "sem plano aberto" in motivos)
        finally:
            shutil.rmtree(vazio, ignore_errors=True)
            shutil.rmtree(cheio, ignore_errors=True)

        print()
        print("As saídas de emergência")
        bloqueou, _ = roda(raiz, "Sigo para F2.", sessao="ks",
                           env_extra={"ANUNCIO_ACAO": "0"})
        check("o interruptor desliga o gate", not bloqueou)

        print()
        print("O vizinho de evento não cala este gate")
        # `stop_hook_active` é do EVENTO Stop, não deste hook: qualquer outro guarda do
        # mesmo evento que devolva o turno (o delivery-audit do intent-guard devolve)
        # faz o campo chegar `true` aqui. Enquanto isso era uma saída antecipada, este
        # gate passava sessões inteiras sem ler uma frase sequer.
        bloqueou, motivo = roda(raiz, "Fase 1 fechada. Sigo para F2.", sessao="sha",
                                stop_hook_active=True)
        check("com outro guarda já tendo falado, ainda devolve o anúncio", bloqueou)
        check("e o que ele devolve é o texto que LEU", "Sigo para F2" in motivo)
        # ler é julgar dos dois lados: sob a mesma bandeira, o turno que espera passa
        bloqueou, _ = roda(raiz, "Sigo para F2. Aguardo sua ordem.", sessao="sha-espera",
                           stop_hook_active=True)
        check("sob a mesma bandeira, julga de verdade: o que espera passa", not bloqueou)

        print()
        print("O teto de devoluções")
        r1, _ = roda(raiz, "Sigo para F2.", sessao="cap")
        r2, _ = roda(raiz, "Sigo para F2.", sessao="cap")
        r3, _ = roda(raiz, "Sigo para F2.", sessao="cap")
        check("devolve na 1ª", r1)
        check("devolve na 2ª", r2)
        check("desiste na 3ª — nunca vira laço", not r3)

        outra, _ = roda(raiz, "Sigo para F2.", sessao="cap-outra")
        check("o teto é por sessão, não global", outra)

        print()
        print("O que a devolução diz")
        _, motivo = roda(raiz, "Fase 1 fechada. Sigo para F2.", sessao="msg")
        check("mostra o trecho que o agente escreveu", "Sigo para F2" in motivo)
        check("nomeia o plano em aberto", "A frente em curso" in motivo)
        check("diz quantos passos faltam", "1 passo(s) em aberto" in motivo)
        check("aponta o próximo passo pelo id", "F1" in motivo)
        check("manda executar no mesmo turno", "neste mesmo turno" in motivo)
        check("oferece a saída legítima de perguntar", "pergunte" in motivo)

        print()
        print("O registro — gate que arma em silêncio não se audita")
        log = os.path.join(raiz, "estado", "batidas.log")
        check("existe log de batidas", os.path.isfile(log))
        if os.path.isfile(log):
            with open(log, encoding="utf-8") as fh:
                linhas = [json.loads(x) for x in fh if x.strip()]
            motivos = {ln.get("motivo") for ln in linhas}
            check("registra quando devolve", "devolveu" in motivos)
            check("registra quando desiste pelo teto", "desistiu" in motivos)
            check("registra quando o usuário é quem tem a bola",
                  "espera o usuario" in motivos)
            check("a devolução guarda o trecho, não só o veredito",
                  any(ln.get("motivo") == "devolveu" and ln.get("trecho")
                      for ln in linhas))

        print()
        print("Fail-open — infra quebrada nunca prende a sessão")
        r = subprocess.run([sys.executable, HOOK], input="isto nao e json",
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20, start_new_session=True)
        check("payload ilegível sai calado e com sucesso",
              r.returncode == 0 and not (r.stdout or "").strip())

        trans_sumido = json.dumps({"session_id": "x", "cwd": raiz,
                                   "transcript_path": os.path.join(raiz, "nao-existe")})
        r = subprocess.run([sys.executable, HOOK], input=trans_sumido,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20, start_new_session=True)
        check("transcript ausente sai calado", r.returncode == 0
              and not (r.stdout or "").strip())
    finally:
        shutil.rmtree(raiz, ignore_errors=True)

    print()
    if FALHAS:
        print("FALHOU: %d de %d" % (len(FALHAS), TOTAL))
        for f in FALHAS:
            print("  - %s" % f)
        sys.exit(1)
    print("OK — %d checks" % TOTAL)


if __name__ == "__main__":
    main()
