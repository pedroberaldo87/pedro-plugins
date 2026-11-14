#!/usr/bin/env python3
"""Segredos do journal (P12): o que o scrubber tira do texto não pode voltar por fora.

Cobre quatro furos do mesmo caminho (transcript → scrub → findings.jsonl versionado):
  1. o placeholder `‹cofre:LABEL:xxxxxxxx›` levava 32 bits de SHA-1 do valor — quem tem
     o journal testava palpites offline. Agora a etiqueta é HMAC com um sal por instalação;
  2. o sal fica em arquivo 0600 (e só nasce quando há segredo a etiquetar);
  3. o cofre (`<slug>.env`) e a pasta dele nasciam com o umask do processo;
  4. chaves `sk-ant-`, `sk-proj-` e `hf_` passavam: o `sk-` do padrão não aceita hífen.

Strings com cara de chave são MONTADAS por concatenação — nenhum literal aqui casa com um
detector de segredo.

Roda com:  python3 plugins/project-skills/lib/test_journal_segredos.py
"""
import hashlib
import os
import random
import shutil
import stat
import string
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

BASE = tempfile.mkdtemp(prefix="pdsegredos-")
COFRE = os.path.join(BASE, "cofre")
SAL = os.path.join(BASE, "estado", "journal.salt")
os.environ["PROJECT_DOC_COFRE_DIR"] = COFRE
os.environ["PROJECT_DOC_SALT_FILE"] = SAL
POSIX = os.name != "nt"          # no Windows o chmod só mexe no bit de leitura

import journal  # noqa: E402

PASSED = 0
FALHAS = []


def check(nome, cond, detalhe=""):
    global PASSED
    if cond:
        print("  ok · %s" % nome)
        PASSED += 1
    else:
        print("  FALHOU · %s %s" % (nome, detalhe))
        FALHAS.append(nome)


def modo(caminho):
    try:
        return stat.S_IMODE(os.stat(caminho).st_mode)
    except OSError:
        return -1          # ausente: o check reprova em vez de derrubar a suíte


def rand(n, seed):
    rnd = random.Random(seed)
    alfabeto = string.ascii_letters + string.digits
    return "".join(rnd.choice(alfabeto) for _ in range(n))


# Valores montados em pedaços: nenhum literal do arquivo é um segredo.
CHAVE_ANT = "sk" + "-ant-" + "api03-" + rand(90, 1)
CHAVE_PROJ = "sk" + "-proj-" + rand(60, 2) + "_" + rand(20, 3)
CHAVE_HF = "hf" + "_" + rand(34, 4)
CHAVE_SK = "sk" + "-" + rand(40, 5)            # o formato antigo continua pego

try:
    # ── 1. prefixos novos viram placeholder e vão para o cofre ──────────────────
    for nome, valor in (("sk-ant-", CHAVE_ANT), ("sk-proj-", CHAVE_PROJ),
                        ("hf_", CHAVE_HF), ("sk- (formato antigo)", CHAVE_SK)):
        texto, segredos = journal.scrub("colei isto no chat: %s e segui em frente" % valor)
        check("scrub: %s sai do texto" % nome, valor not in texto, "— veio %r" % texto)
        check("scrub: %s vai para o cofre" % nome, any(v == valor for _, v in segredos))

    # o que parece chave e não é continua intacto
    for banal in ("hf_hub_download", "use sk-learn para o modelo", "o commit 0123abc",
                  "10.0.0.7", "src/app/main.py", "hf_", "sk-ant-"):
        texto, segredos = journal.scrub(banal)
        check("scrub preserva %r" % banal, texto == banal and not segredos, "— veio %r" % texto)

    # ── 2. etiqueta: estável, e não reproduzível por SHA-1 do valor ─────────────
    valor = CHAVE_SK
    t1, _ = journal.scrub("a " + valor)
    t2, _ = journal.scrub("outra frase com " + valor)
    etiqueta = t1.split("‹cofre:TOKEN:")[1].split("›")[0]
    check("etiqueta estável para o mesmo valor", ("‹cofre:TOKEN:%s›" % etiqueta) in t2)
    sha1_8 = hashlib.sha1(valor.encode("utf-8")).hexdigest()[:8]
    check("etiqueta NÃO é o prefixo do SHA-1 do valor", etiqueta != sha1_8, "— é %s" % sha1_8)
    check("etiqueta NÃO é o prefixo do SHA-256 do valor",
          etiqueta != hashlib.sha256(valor.encode("utf-8")).hexdigest()[:8])
    check("etiqueta tem 8 hex", len(etiqueta) == 8 and all(c in "0123456789abcdef" for c in etiqueta))

    prog = ("import sys; sys.path.insert(0, %r); import journal; "
            "print(journal.scrub('a ' + %r)[0])") % (HERE, valor)
    env = dict(os.environ)
    saida = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True,
                           encoding="utf-8", env=env, timeout=60).stdout.strip()
    check("etiqueta estável entre processos (mesmo sal)", saida == t1, "— veio %r" % saida)

    env["PROJECT_DOC_SALT_FILE"] = os.path.join(BASE, "outro", "journal.salt")
    saida = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True,
                           encoding="utf-8", env=env, timeout=60).stdout.strip()
    check("outro sal → outra etiqueta para o mesmo valor", saida != t1 and "‹cofre:TOKEN:" in saida)

    # ── 3. o sal: arquivo 0600, criado só quando preciso, nunca regravado ───────
    check("o sal existe", os.path.isfile(SAL))
    if POSIX:
        check("sal com modo 0600", modo(SAL) == 0o600, "— é %o" % modo(SAL))
        check("pasta do sal sem acesso de grupo/outros", modo(os.path.dirname(SAL)) & 0o077 == 0,
              "— é %o" % modo(os.path.dirname(SAL)))
    antes = open(SAL, "rb").read()
    journal.scrub("mais um " + CHAVE_HF)
    check("o sal não muda entre usos", open(SAL, "rb").read() == antes)
    check("o sal tem entropia (≥ 16 bytes)", len(antes.strip()) >= 32)

    # sal ilegível/corrompido: o scrub NÃO volta ao SHA-1 nu — a etiqueta continua com sal
    texto, _ = journal.scrub("x " + CHAVE_HF)
    check("o scrub nunca cai no hash sem sal", ("‹cofre:TOKEN:%s›" % hashlib.sha1(
        CHAVE_HF.encode("utf-8")).hexdigest()[:8]) not in texto)

    # ── 4. o cofre: arquivo 0600, pasta 0700, e o arquivo velho é apertado ──────
    projeto = os.path.join(BASE, "projeto")
    os.makedirs(projeto)
    _, segredos = journal.scrub("a " + CHAVE_ANT)
    cofre_base, cofre = journal.cofre_paths(projeto)
    journal.stash_secrets(segredos, projeto)
    check("cofre foi escrito com o valor", os.path.isfile(cofre) and CHAVE_ANT in open(cofre).read())
    if POSIX:
        check("arquivo do cofre com modo 0600", modo(cofre) == 0o600, "— é %o" % modo(cofre))
        check("pasta do cofre com modo 0700", modo(cofre_base) == 0o700, "— é %o" % modo(cofre_base))

        os.chmod(cofre, 0o644)
        os.chmod(cofre_base, 0o755)
        _, mais = journal.scrub("b " + CHAVE_PROJ)
        journal.stash_secrets(mais, projeto)
        check("cofre 0644 pré-existente é apertado para 0600", modo(cofre) == 0o600,
              "— é %o" % modo(cofre))
        check("pasta 0755 pré-existente é apertada para 0700", modo(cofre_base) == 0o700,
              "— é %o" % modo(cofre_base))

        # umask frouxo do processo não vaza para o arquivo novo
        shutil.rmtree(cofre_base)
        antigo = os.umask(0o000)
        try:
            journal.stash_secrets(segredos, projeto)
        finally:
            os.umask(antigo)
        check("com umask 000 o cofre novo ainda nasce 0600", modo(cofre) == 0o600,
              "— é %o" % modo(cofre))
        check("com umask 000 a pasta nova ainda nasce 0700", modo(cofre_base) == 0o700,
              "— é %o" % modo(cofre_base))
    # ── 5. webhooks (o segredo mora no caminho da URL) e tokens npm_ ────────────
    # Montados em pedaços, como acima. Camadas 3 e 4 pulam tokens com `://`, então a URL
    # tem que ser pega pela camada de provider.
    SLACK = "https://" + "hooks.slack" + ".com/services/" + "T" + rand(10, 6) + "/B" + rand(10, 7) + "/" + rand(24, 8)
    DISCORD = "https://" + "discord" + ".com/api/webhooks/" + "1234567890123456789" + "/" + rand(68, 9)
    DISCORDAPP = "https://" + "discordapp" + ".com/api/v10/webhooks/" + "1234567890123456789" + "/" + rand(68, 10)
    NPM = "np" + "m_" + rand(36, 11)
    for nome, valor in (("webhook Slack", SLACK), ("webhook Discord", DISCORD),
                        ("webhook discordapp", DISCORDAPP), ("npm_", NPM)):
        texto, segredos = journal.scrub("o hook ficou assim: %s e fim" % valor)
        check("scrub: %s sai do texto" % nome, valor not in texto, "— veio %r" % texto)
        check("scrub: %s vai para o cofre" % nome, any(v == valor for _, v in segredos))
    # a parte secreta nunca sobra, nem quando o scrub pega só um pedaço da URL
    texto, _ = journal.scrub("curl -X POST " + SLACK + " -d '{}'")
    check("scrub: o segredo do webhook Slack não sobra no texto", SLACK.rsplit("/", 1)[1] not in texto,
          "— veio %r" % texto)
    texto, _ = journal.scrub("POST " + DISCORD)
    check("scrub: o segredo do webhook Discord não sobra no texto", DISCORD.rsplit("/", 1)[1] not in texto,
          "— veio %r" % texto)
    # URLs de docs e nomes parecidos seguem intactos
    for banal in ("https://api.slack.com/messaging/webhooks", "https://hooks.slack.com/services/",
                  "https://discord.com/developers/docs/resources/webhook", "npm_config_cache",
                  "rode npm_ e depois npm install", "https://www.npmjs.com/package/left-pad"):
        texto, segredos = journal.scrub(banal)
        check("scrub preserva %r" % banal, texto == banal and not segredos, "— veio %r" % texto)

    # ── 6. camada 4: token de alta entropia sem rótulo vai para o cofre (não fica com ‹revisar?›) ──
    # e o caminho/consulta de uma URL qualquer também é conferido (webhook de serviço que não
    # tem padrão próprio). Montados em pedaços, como acima.
    OPACO = rand(24, 20)                              # letras e dígitos, sem prefixo de provider
    AWSLIKE = rand(10, 21) + "/" + rand(12, 22) + "/" + rand(16, 23)
    for nome, texto_in, valor in (
            ("token solto na prosa", "blob aleatório %s no meio" % OPACO, OPACO),
            ("token solto com ponto final", "o valor era %s." % OPACO, OPACO),
            ("segredo com barras sem rótulo", "blob %s no fim" % AWSLIKE, AWSLIKE),
            ("segredo no caminho de uma URL",
             "https://" + "hooks.example" + ".com/services/" + OPACO + " fim", OPACO),
            ("segredo no caminho, entre segmentos banais",
             "curl https://" + "api.example" + ".com/v1/hooks/" + OPACO + "/trigger", OPACO),
            ("segredo na consulta de uma URL",
             "GET https://" + "api.example" + ".com/v1/x?key=" + OPACO + "&a=1", OPACO)):
        texto, segredos = journal.scrub(texto_in)
        check("camada 4: %s sai do texto" % nome, valor not in texto, "— veio %r" % texto)
        check("camada 4: %s vai para o cofre" % nome, any(v == valor for _, v in segredos))
        check("camada 4: %s não fica marcado ‹revisar?›" % nome, "‹revisar?›" not in texto,
              "— veio %r" % texto)
    # cara de código (pontuação fora do alfabeto de segredo): não vai para o cofre — no máximo ganha o aviso
    for codigo in ("dev.example.com:8443/path-numero-2", "veja ${CLAUDE_PLUGIN_ROOT}/lib/journal.py:12 ok",
                   "git@github.com:example/pedro-plugins.git", "lib getUserByAccountId2 chamada"):
        texto, segredos = journal.scrub(codigo)
        check("camada 4 não move %r para o cofre" % codigo, not segredos, "— veio %r" % texto)
    # `CHAVE=valor` sem palavra-sinal: o nome fica, o valor sai
    texto, segredos = journal.scrub("export SERVICE_REF=" + OPACO + " e rode")
    check("camada 4: CHAVE=valor — o valor vai para o cofre e o nome fica",
          OPACO not in texto and "SERVICE_REF=" in texto and any(v == OPACO for _, v in segredos),
          "— veio %r" % texto)
    # o resto da URL fica legível: só o segmento secreto sai
    texto, _ = journal.scrub("https://" + "hooks.example" + ".com/services/" + OPACO + " fim")
    check("camada 4: a URL mantém o host e o caminho banal",
          texto.startswith("https://hooks.example.com/services/") and texto.endswith(" fim"),
          "— veio %r" % texto)
    # o que NÃO é segredo segue intacto: sha, uuid, caminho, versão, URL comum
    SHA40 = "9f8c2a1b3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f80"
    UUID = "123e4567-e89b-12d3-a456-426614174000"
    for banal in ("commit " + SHA40 + " fechou", "abrev 9f8c2a1 fechou", "id " + UUID + " ok",
                  "veja src/components/Widget.tsx para detalhe",
                  "veja plugins/project-skills/lib/journal.py:620 agora",
                  "caminho ~/workspace/public-docs/pedro-plugins/docs/architecture.md ok",
                  "versão v1.2.3-rc.1+build.5678 saiu", "pacote 2026.11.14-build.20261114 ok",
                  "https://github.com/example/pedro-plugins/pull/24",
                  "https://github.com/example/pedro-plugins/commit/" + SHA40,
                  "https://example.com/docs/getting-started-with-the-journal-scrubber-2026",
                  "https://example.com/a/b/c?page=2&sort=name&q=journal+scrubber",
                  "https://example.com/files/relatorio-final-de-2026.pdf",
                  "http://127.0.0.1:8080/health", "mailto:ninguem@example.com",
                  # nomes e identificadores longos de texto corrente (antes só ganhavam um aviso)
                  "export MSYS2_ARG_CONV_EXCL=* e rode", "branch fix/sec-p11-p12-residuals saiu",
                  "advisory GHSA-abcd-1234-wxyz aberto",
                  "prazo TIMEOUT-600s estourou"):
        texto, segredos = journal.scrub(banal)
        check("camada 4 preserva %r" % banal, texto == banal and not segredos, "— veio %r" % texto)
finally:
    shutil.rmtree(BASE, ignore_errors=True)

print("\ntest_journal_segredos: %d ok, %d falha(s)" % (PASSED, len(FALHAS)))
sys.exit(1 if FALHAS else 0)
