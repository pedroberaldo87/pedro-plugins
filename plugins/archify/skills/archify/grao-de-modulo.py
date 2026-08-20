#!/usr/bin/env python3
"""O grão de módulo de um projeto — a régua do survey de 2026-08-19, em programa.

Por que existe: a premissa "o grão é o plugin" era miopia deste repositório. O
survey de 25 repositórios reais achou 5 formas, e a decisão do dono (19/08) é
que A/B/C ganham diagrama por módulo e D/E só o organismo. Regra que decide
quantos diagramas existem não pode ser prosa dentro de skill — prosa se copia,
diverge e vira palpite. Aqui é o único lugar que classifica.

As 5 classes:
  A  coleção de unidades nomeadas   (plugins/, tools/apps/, canais/)
  B  monorepo declarado             (pnpm-workspace.yaml, "workspaces", turbo.json)
  C  dois lados que conversam       (backend/ + frontend/, src/ + src-tauri/)
  D  aplicativo único em camadas    (src/ único, >= 100 arquivos)
  E  projeto pequeno                (< 100 arquivos rastreados)

Precedência de sinais (a ordem É a regra — medível, nunca julgamento):
  1. manifesto de workspace presente                        -> B, grão = o pacote do manifesto
  2. tronco com >= 3 subpastas irmãs de tamanho comparável  -> A, grão = a subpasta
  3. >= 2 troncos que são processos distintos               -> C, grão = o lado
  4. < 100 arquivos rastreados                              -> E, sem diagrama de módulo
  5. senão                                                  -> D, o projeto inteiro

Uso:
    python3 grao-de-modulo.py <raiz>      # JSON: classe, grao, unidades, diagrama_por_modulo
    # ou, de Python (o hífen do nome pede importlib):
    #   spec = importlib.util.spec_from_file_location("grao", ".../grao-de-modulo.py")
"""

import json
import os
import subprocess
import sys

__all__ = ["classificar"]

IGNORAR = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}

# Nomes de tronco que denunciam um PROCESSO (um lado da conversa da classe C).
LADOS = {
    "backend", "frontend", "server", "servidor", "client", "cliente",
    "app", "api", "web", "mobile", "desktop", "src-tauri", "painel-do-servidor",
}
MANIFESTOS = ("package.json", "pyproject.toml", "go.mod", "Cargo.toml", "requirements.txt")

PEQUENO = 100          # corte da classe E, o mesmo do survey
MIN_UNIDADES = 3       # classe A exige >= 3 irmãs
COMPARAVEL = 20        # "tamanho comparável" = a maior irmã <= 20x a MEDIANA; max/min reprovava
                       # este próprio repositório (161 arquivos no maior plugin, 3 no menor)


def _arquivos(raiz):
    """Arquivos rastreados (git ls-files) ou, sem git, a árvore menos IGNORAR."""
    try:
        out = subprocess.run(
            ["git", "-C", raiz, "ls-files"],
            capture_output=True, text=True, timeout=30,
            stdin=subprocess.DEVNULL, start_new_session=True,
        )
        if out.returncode == 0:
            return [f for f in out.stdout.splitlines() if f]
    except Exception:
        pass
    achados = []
    for dirpath, dirnames, filenames in os.walk(raiz):
        dirnames[:] = [d for d in dirnames if d not in IGNORAR and not d.startswith(".")]
        rel = os.path.relpath(dirpath, raiz)
        for f in filenames:
            achados.append(f if rel == "." else os.path.join(rel, f))
    return achados


def _workspace(raiz):
    """Classe B: unidades declaradas no manifesto de workspace, ou None."""
    globs = []
    pnpm = os.path.join(raiz, "pnpm-workspace.yaml")
    if os.path.isfile(pnpm):
        for linha in open(pnpm, encoding="utf-8", errors="replace"):
            linha = linha.strip()
            if linha.startswith("- "):
                globs.append(linha[2:].strip().strip("'\""))
    pkg = os.path.join(raiz, "package.json")
    if os.path.isfile(pkg):
        try:
            dados = json.load(open(pkg, encoding="utf-8"))
            ws = dados.get("workspaces")
            if isinstance(ws, dict):
                ws = ws.get("packages", [])
            globs.extend(ws or [])
        except Exception:
            pass
    if not globs and not os.path.isfile(os.path.join(raiz, "turbo.json")):
        return None
    if not globs:
        globs = ["apps/*", "packages/*"]  # convenção do turborepo quando só há turbo.json
    unidades = []
    import glob as _glob
    for g in globs:
        for p in sorted(_glob.glob(os.path.join(raiz, g))):
            if os.path.isdir(p) and any(
                os.path.isfile(os.path.join(p, m)) for m in MANIFESTOS
            ):
                unidades.append(os.path.relpath(p, raiz))
    return unidades or None


def _por_pasta(arquivos):
    """Contagem de arquivos por caminho de pasta (todos os níveis)."""
    contagem = {}
    for f in arquivos:
        partes = f.replace("\\", "/").split("/")[:-1]
        for i in range(1, len(partes) + 1):
            chave = "/".join(partes[:i])
            contagem[chave] = contagem.get(chave, 0) + 1
    return contagem


def _colecao(arquivos):
    """Classe A: (tronco, unidades) do primeiro tronco com >= 3 irmãs comparáveis."""
    contagem = _por_pasta(arquivos)
    troncos = sorted({f.replace("\\", "/").split("/")[0] for f in arquivos if "/" in f})
    for tronco in [t for t in troncos if t not in IGNORAR and not t.startswith(".")]:
        filhas = sorted(
            {c for c in contagem if c.startswith(tronco + "/") and c.count("/") == 1}
        )
        if len(filhas) < MIN_UNIDADES:
            continue
        tamanhos = sorted(contagem[c] for c in filhas)
        mediana = tamanhos[len(tamanhos) // 2]
        if max(tamanhos) <= COMPARAVEL * mediana:
            return tronco, [c.split("/", 1)[1] for c in filhas]
    return None


def _lados(raiz, arquivos):
    """Classe C: troncos que são processos distintos (>= 2), ou None."""
    troncos = sorted({f.replace("\\", "/").split("/")[0] for f in arquivos if "/" in f})
    achados = []
    for t in troncos:
        if t in IGNORAR or t.startswith("."):
            continue
        tem_manifesto = any(
            os.path.isfile(os.path.join(raiz, t, m)) for m in MANIFESTOS
        )
        if tem_manifesto or t.lower() in LADOS:
            achados.append(t)
    return achados if len(achados) >= 2 else None


def classificar(raiz):
    """Classe (A-E), grão e unidades da raiz — e se há diagrama por módulo.

    A precedência é a do survey; um projeto pode ser A DENTRO de C, mas este
    resolvedor responde pelo TRONCO da raiz pedida — recursão é chamar de novo
    com a subpasta.
    """
    raiz = os.path.abspath(str(raiz))
    arquivos = _arquivos(raiz)

    ws = _workspace(raiz)
    if ws:
        return _resposta("B", "o pacote do workspace, lido do manifesto", ws)

    col = _colecao(arquivos)
    if col:
        tronco, unidades = col
        return _resposta(
            "A", "a unidade nomeada dentro de %s/" % tronco,
            ["%s/%s" % (tronco, u) for u in unidades],
        )

    lados = _lados(raiz, arquivos)
    if lados:
        return _resposta("C", "o lado (o processo), nunca a pasta", lados)

    if len(arquivos) < PEQUENO:
        return _resposta("E", "nenhum diagrama de módulo — só o organismo", [])

    return _resposta("D", "o projeto inteiro num diagrama só", [])


def _resposta(classe, grao, unidades):
    return {
        "classe": classe,
        "grao": grao,
        "unidades": unidades,
        # A decisão do dono (19/08): A/B/C ganham diagrama por módulo, D/E não.
        "diagrama_por_modulo": classe in ("A", "B", "C"),
    }


if __name__ == "__main__":
    alvo = sys.argv[1] if len(sys.argv) > 1 else "."
    print(json.dumps(classificar(alvo), ensure_ascii=False, indent=2))
