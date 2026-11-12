#!/usr/bin/env python3
"""A única porta por onde o /fallow chama o `npx` — versão fixada, fora do projeto.

Por que existe (P7 · achado 4). `npx -y fallow` com o projeto analisado como diretório
de trabalho deixava o repositório escolher o binário: o npm lê o `.npmrc` DO PROJETO
(registro, escopos) e prefere um `node_modules/.bin/fallow` que o projeto traga. Um
repositório clonado de terceiro rodava código dele com os poderes do dono da sessão.
Três travas, todas aqui:

  versão exata        `fallow@X.Y.Z`, nunca "a última". Subir a versão é um commit
                      deste arquivo (e do SKILL.md, que o teste mantém igual).
  fora do projeto     o `npx` roda num diretório vazio e novo; o projeto entra só como
                      argumento `-r <raiz>`. O `.npmrc` do usuário (~/.npmrc) segue
                      valendo — é dele, e tirar quebraria registro privado e login.
  sem scripts         `--ignore-scripts`: nenhum `postinstall` de pacote baixado roda.

stdlib only.
"""
import subprocess
import tempfile

# Versão auditada do analisador. O SKILL.md cita a mesma — `test_fallow_pin.py` confere.
FALLOW_VERSION = "3.42.0"


def npx_argv(args):
    """O argv completo do `npx` para `fallow <args>`."""
    return ["npx", "--yes", "--ignore-scripts", "fallow@" + FALLOW_VERSION] + list(args)


def run_fallow(args, timeout):
    """Roda `fallow <args>` num diretório vazio; devolve o CompletedProcess.

    `args` já leva o `-r <raiz absoluta>`. Levanta o que o `subprocess.run` levantar
    (timeout, binário ausente) — quem chama decide o que fazer.
    """
    with tempfile.TemporaryDirectory(prefix="fallow-run-") as neutro:
        return subprocess.run(
            npx_argv(args), cwd=neutro, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
            stdin=subprocess.DEVNULL, start_new_session=True)
