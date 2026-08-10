#!/usr/bin/env python3
"""MCP server de visão — dá olhos ao Claude delegando a um modelo VL (Qwen3.6).

O modelo que o Claude usa pode não ter visão: ler uma imagem via Read devolve
"Unsupported Image". Este server expõe UMA tool, `see_image`, que o Claude chama
quando precisa entender uma imagem. O server codifica o arquivo em base64 e faz
POST ao servidor de visão (API no padrão OpenAI), que responde em texto.

O ENDPOINT NÃO vive neste arquivo — ele é infraestrutura privada de quem instala.
Três fontes, nesta ordem:
  1. Env var  QWEN_BASE        (ex: http://host:8000/v1)
             QWEN_MODEL       (ex: Jundot/Qwen3.6-35B-A3B-oQ4-fp16-mtp)
             QWEN_TIMEOUT      (segundos; o MoE frio demora a responder)
  2. Config   ~/.claude/vision.json  com {"base": "...", "model": "..."}
  3. Falha com mensagem clara pedindo a config — nunca um endpoint chutado.

Transporte: MCP stdio = JSON-RPC 2.0 newline-delimited no stdin/stdout, só stdlib.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

# CANAIS DE TEXTO EM UTF-8, SEMPRE. No Windows eles nascem na codificação do sistema
# (cp1252) e o payload do evento — que chega por stdin — é UTF-8: sem isto, todo
# acento do pedido do usuário chega corrompido ao gate, e emoji derruba a escrita.
for _canal in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_canal, "reconfigure"):
        try:
            _canal.reconfigure(encoding="utf-8")
        except Exception:
            pass

CONFIG_PATH = os.path.expanduser("~/.claude/vision.json")


def _config():
    base = os.environ.get("QWEN_BASE", "")
    model = os.environ.get("QWEN_MODEL", "")
    timeout = int(os.environ.get("QWEN_TIMEOUT", "180"))
    if not base or not model:
        try:
            with open(CONFIG_PATH, encoding="utf-8") as fh:
                cfg = json.load(fh)
            base = base or cfg.get("base", "")
            model = model or cfg.get("model", "")
            timeout = int(cfg.get("timeout", timeout))
        except (OSError, ValueError):
            pass
    return base, model, timeout


BASE, MODEL, TIMEOUT = _config()


def _mime(path):
    p = path.lower()
    if p.endswith(".png"):
        return "image/png"
    if p.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if p.endswith(".gif"):
        return "image/gif"
    if p.endswith(".webp"):
        return "image/webp"
    return "image/png"


TOOL = {
    "name": "see_image",
    "description": (
        "Describe what an image shows. Use when the user asks about a screenshot, "
        "image, or visual artifact and you cannot read it directly. Pass the "
        "absolute file path and, optionally, the question to answer about it."),
    "inputSchema": {
        "type": "object",
        "properties": {
            "path": {"type": "string",
                     "description": "Absolute path to the image file (png/jpg)."},
            "question": {"type": "string",
                         "description": "What to ask about the image. Defaults to "
                                        "a full description."},
        },
        "required": ["path"],
    },
}


def see_image(args):
    if not BASE:
        return _err(
            "servidor de visão não configurado. Defina QWEN_BASE/QWEN_MODEL no "
            "ambiente ou crie ~/.claude/vision.json com {\"base\": \"...\", "
            "\"model\": \"...\"}.")
    path = args.get("path", "")
    question = args.get(
        "question",
        "O que exatamente esta imagem mostra? Descreva em detalhe, "
        "transcrevendo o texto visível.")
    if not path or not os.path.isfile(path):
        return _err("arquivo não existe: %s" % path)
    try:
        b64 = base64.b64encode(open(path, "rb").read()).decode()
    except OSError as e:
        return _err("não consegui ler %s: %s" % (path, e))

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "image_url",
             "image_url": {"url": "data:%s;base64,%s" % (_mime(path), b64)}},
            {"type": "text", "text": question},
        ]}],
        "max_tokens": 1024,
    }
    req = urllib.request.Request(
        BASE.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"]
        return {"content": [{"type": "text", "text": text}], "isError": False}
    except urllib.error.HTTPError as e:
        return _err("servidor de visão respondeu %s: %s" % (e.code, e.read()[:200]))
    except Exception as e:
        return _err("falha ao chamar o servidor de visão: %s" % e)


def _err(text):
    return {"content": [{"type": "text", "text": "❌ " + text}], "isError": True}


def _send(msg_id, result):
    sys.stdout.write(json.dumps(
        {"jsonrpc": "2.0", "id": msg_id, "result": result}) + "\n")
    sys.stdout.flush()


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        method = msg.get("method")
        msg_id = msg.get("id")
        if method == "initialize":
            _send(msg_id, {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "vision-qwen", "version": "0.1.0"},
            })
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            _send(msg_id, {"tools": [TOOL]})
        elif method == "tools/call":
            params = msg.get("params", {}) or {}
            if params.get("name") == "see_image":
                _send(msg_id, see_image(params.get("arguments", {}) or {}))
            else:
                _send(msg_id, _err("tool desconhecida: %s" % params.get("name")))
        elif msg_id is not None:
            _send(msg_id, {})


if __name__ == "__main__":
    main()
