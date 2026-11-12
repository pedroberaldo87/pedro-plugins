#!/usr/bin/env python3
"""test_vision_mcp.py — see_image só manda IMAGEM ao servidor de visão (P12).

A tool lia qualquer arquivo que o modelo nomeasse, codificava em base64 e fazia POST ao
endpoint configurado — as regras de leitura de arquivo do Claude Code não valem para uma
tool de MCP. Um agente induzido por texto de terceiros mandava `~/.ssh/id_*`, `.env` ou
um dump para fora. Agora: só extensão de imagem E assinatura (magic bytes) de imagem, com
teto de tamanho, e uma raiz opcional (`VISION_ROOT` ou "root" em vision.json) que confina o
caminho já resolvido (symlink não escapa).

Sem rede: o POST é trocado por um dublê que só registra o que receberia.

Roda com:  python3 plugins/vision/lib/test_vision_mcp.py
"""
import json
import os
import shutil
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, ".."))
os.environ["QWEN_BASE"] = "http://192.0.2.1:9/v1"       # TEST-NET: nada responde de verdade
os.environ["QWEN_MODEL"] = "modelo-de-teste"
os.environ.pop("VISION_ROOT", None)

import vision_mcp  # noqa: E402

PASSOU = 0
FALHAS = []
ENVIADOS = []


def check(nome, cond, detalhe=""):
    global PASSOU
    if cond:
        print("  ok · %s" % nome)
        PASSOU += 1
    else:
        print("  FALHOU · %s %s" % (nome, detalhe))
        FALHAS.append(nome)


class RespostaFalsa:
    def __init__(self, req):
        ENVIADOS.append(req.data)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return json.dumps({"choices": [{"message": {"content": "uma imagem de teste"}}]}).encode()


vision_mcp.urllib.request.urlopen = lambda req, timeout=None: RespostaFalsa(req)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
GIF = b"GIF89a" + b"\x00" * 32
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 32

BASE = tempfile.mkdtemp(prefix="vision-")


def arq(nome, conteudo):
    p = os.path.join(BASE, nome)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as fh:
        fh.write(conteudo)
    return p


def vai(caminho):
    """True se a imagem chegou ao POST; False se a tool recusou (e nada foi enviado)."""
    antes = len(ENVIADOS)
    r = vision_mcp.see_image({"path": caminho})
    mandou = len(ENVIADOS) > antes
    check("resposta coerente com o envio (%s)" % os.path.basename(caminho),
          mandou == (not r["isError"]), "— isError=%s, enviados=%d" % (r["isError"], len(ENVIADOS) - antes))
    return mandou


try:
    # ── o uso normal continua funcionando ────────────────────────────────────────
    for nome, corpo in (("a.png", PNG), ("b.jpg", JPG), ("c.jpeg", JPG), ("d.gif", GIF), ("e.webp", WEBP),
                        ("MAIUSCULA.PNG", PNG)):
        check("imagem normal passa: %s" % nome, vai(arq(nome, corpo)))

    # ── não-imagem é recusada, nada é enviado ────────────────────────────────────
    # montada em pedaços: o literal inteiro seria lido como chave privada por um detector
    segredo = (b"-----BEGIN " + b"OPENSSH PRIVATE KEY-----\nQUJD\n-----END " + b"OPENSSH PRIVATE KEY-----\n")
    check("chave privada sem extensão é recusada", not vai(arq("id_ed25519", segredo)))
    check(".env é recusado", not vai(arq(".env", b"API_TOKEN=exemplo\n")))
    check("texto com extensão .png (sem assinatura) é recusado", not vai(arq("falso.png", segredo)))
    check("PDF é recusado", not vai(arq("doc.pdf", b"%PDF-1.7\n")))
    check("PNG com extensão .txt é recusado", not vai(arq("imagem.txt", PNG)))
    check("arquivo vazio .png é recusado", not vai(arq("vazio.png", b"")))
    check("diretório é recusado", not vai(BASE))
    check("arquivo que não existe é recusado", not vai(os.path.join(BASE, "nao-existe.png")))

    alvo = arq("segredo.txt", segredo)
    if hasattr(os, "symlink"):
        elo = os.path.join(BASE, "elo.png")
        try:
            os.symlink(alvo, elo)
            check("symlink .png que aponta para texto é recusado", not vai(elo))
        except (OSError, NotImplementedError):
            print("  — sem symlink neste ambiente: caso pulado")

    # ── teto de tamanho ──────────────────────────────────────────────────────────
    velho = vision_mcp.MAX_BYTES
    vision_mcp.MAX_BYTES = 64
    try:
        check("imagem acima do teto é recusada", not vai(arq("grande.png", PNG + b"\x00" * 200)))
        check("imagem abaixo do teto passa", vai(arq("pequena.png", PNG[:12] + b"\x00" * 8)))
    finally:
        vision_mcp.MAX_BYTES = velho

    # ── raiz configurada confina o caminho ───────────────────────────────────────
    dentro = arq("projeto/img/ok.png", PNG)
    fora = os.path.join(tempfile.mkdtemp(prefix="vision-fora-"), "fora.png")
    with open(fora, "wb") as fh:
        fh.write(PNG)
    os.environ["VISION_ROOT"] = os.path.join(BASE, "projeto")
    try:
        check("com raiz: imagem dentro dela passa", vai(dentro))
        check("com raiz: imagem fora dela é recusada", not vai(fora))
        check("com raiz: caminho com .. que escapa é recusado",
              not vai(os.path.join(BASE, "projeto", "img", "..", "..", "a.png")))
        if hasattr(os, "symlink"):
            try:
                elo2 = os.path.join(BASE, "projeto", "escapa.png")
                os.symlink(fora, elo2)
                check("com raiz: symlink que sai dela é recusado", not vai(elo2))
            except (OSError, NotImplementedError):
                print("  — sem symlink neste ambiente: caso pulado")
        check("com raiz: pasta irmã de prefixo igual é recusada",
              not vai(arq("projeto-evil/x.png", PNG)))
    finally:
        os.environ.pop("VISION_ROOT", None)
        shutil.rmtree(os.path.dirname(fora), ignore_errors=True)
finally:
    shutil.rmtree(BASE, ignore_errors=True)

print("\nvision_mcp: %d ok, %d falha(s)" % (PASSOU, len(FALHAS)))
sys.exit(1 if FALHAS else 0)
