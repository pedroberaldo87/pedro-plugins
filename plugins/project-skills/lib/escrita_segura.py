"""Escrita de arquivo de estado que NÃO segue symlink (hsf_38d27434 · cf35688f).

O estado do plano, do journal e do precheck mora em caminhos previsíveis DENTRO do repositório
(`.claude/neblina.md`, `.claude/.sprint/precheck.json`, `.claude/.project-doc/ledger.json`…). Num
clone, um symlink versionado com esse nome faz um `open(caminho, "w")` gravar fora do projeto,
com o texto que o repositório escolheu. Este módulo é o único lugar que sabe gravar sem seguir:

- `grava_texto_seguro` — temporário aleatório (`mkstemp`, O_EXCL) na mesma pasta + `os.replace`;
  um destino que JÁ é symlink é recusado, dito em voz alta;
- `anexa_texto_seguro` — append com O_NOFOLLOW;
- `raiz=` (opcional) — recusa também quando a PASTA do destino sai da raiz do projeto por um
  symlink de diretório (`.claude/.sprint -> /fora`).

Só stdlib e sem import do resto do `lib/`: é carregável por qualquer motor, inclusive os que
rodam sem o `plan_state`.
"""
import os
import tempfile


class EscritaRecusada(OSError):
    """O destino é um symlink, ou a pasta dele sai da raiz do projeto."""


_O_NOFOLLOW = os.O_NOFOLLOW if hasattr(os, "O_NOFOLLOW") else 0   # Windows não tem


def _dentro(raiz, pasta):
    r = os.path.realpath(raiz)
    p = os.path.realpath(pasta)
    try:
        return os.path.commonpath([r, p]) == r
    except ValueError:                       # unidades diferentes (Windows)
        return False


def _confere(path, raiz):
    if os.path.islink(path):
        raise EscritaRecusada("⛔ %s é um symlink — não grava através dele. O arquivo é um\n"
                              "   arquivo comum do projeto; troque o link por um arquivo." % path)
    if raiz is not None and not _dentro(raiz, os.path.dirname(os.path.abspath(path))):
        raise EscritaRecusada("⛔ %s fica fora de %s (um symlink de pasta aponta para fora do\n"
                              "   projeto) — não grava." % (path, raiz))


def grava_texto_seguro(path, texto, raiz=None, modo_novo=0o644):
    """Substitui `path` por `texto` (str, UTF-8) sem seguir symlink. O modo antigo é preservado."""
    _confere(path, raiz)
    try:
        modo = os.stat(path).st_mode & 0o777
    except OSError:
        modo = modo_novo
    fd, tmp = tempfile.mkstemp(prefix=".%s." % os.path.basename(path), suffix=".tmp",
                               dir=os.path.dirname(path) or ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(texto)
        os.chmod(tmp, modo)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def anexa_texto_seguro(path, texto, raiz=None, modo_novo=0o644):
    """Acrescenta `texto` ao fim de `path`; o arquivo é criado se faltar. Não segue symlink."""
    _confere(path, raiz)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | _O_NOFOLLOW, modo_novo)
    with os.fdopen(fd, "a", encoding="utf-8") as fh:
        fh.write(texto)
