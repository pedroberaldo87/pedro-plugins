#!/usr/bin/env python3
"""
check_provenance.py — garante que o deck não inventou NÚMERO.

Modo explicador: o texto é autorado (a regra de ouro de texto literal não
vale), mas todo NÚMERO que entra num infográfico/métrica tem que rastrear ao
material de origem. Barra inventada é pior que prosa inventada.

Extrai os números do TEXTO dentro dos blocos de visualização do deck
(`.fig` e `.metric`) e confere se cada um aparece na(s) fonte(s). Números só
do markup de layout (ex: style="--v:88%") NÃO são checados — são largura
proporcional, não a afirmação; a afirmação é o rótulo de texto, que é checado.
Coordenadas de SVG (d=, cx=) também ficam de fora: são atributo, não texto.

Uso:
    python3 check_provenance.py <deck.html> <fonte1> [fonte2 ...]

Saída: lista de números do deck ausentes das fontes. Exit 1 se houver algum,
0 se limpo. É uma rede de proveniência (checagem grossa por sequência de
dígitos) — pega o número fabricado, não substitui a leitura do autor.
"""
import re
import sys
from html.parser import HTMLParser

# blocos cujo TEXTO carrega números-afirmação
VIZ_CLASSES = {"fig", "metric"}
# classes cujo texto é rótulo estrutural (eixo/categoria/marco), não valor-afirmação
STRUCTURAL_CLASSES = {"lbl", "k", "albl", "when"}
# token numérico: inteiro com separador de milhar, decimal, ou simples
NUM_RE = re.compile(r"\d{1,3}(?:[.,]\d{3})+|\d+[.,]\d+|\d+")


def canon(tok: str) -> str:
    """Canonicaliza um número pra comparação robusta a separador de locale.
    '1.000'->'1000' ; '3,5'->'3.5' ; '88'->'88'. Retorna '' se não-numérico."""
    t = tok.strip()
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", t):          # 1.000.000 / 1,000
        return re.sub(r"[.,]", "", t)
    m = re.fullmatch(r"(\d+)[.,](\d+)", t)                  # 3,5 / 3.5 (decimal)
    if m:
        return m.group(1) + "." + m.group(2)
    if re.fullmatch(r"\d+", t):
        return t
    return ""


def numbers(text: str) -> set:
    out = set()
    for m in NUM_RE.finditer(text):
        c = canon(m.group(0))
        if c:
            out.add(c)
    return out


def is_claim(c: str) -> bool:
    """Filtra ruído: dígito solto (0-9) coincide com qualquer fonte e costuma
    ser enumerador. Conta como afirmação se tem 2+ dígitos OU é decimal."""
    return "." in c or len(c.replace(".", "")) >= 2


class VizText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []        # [{tag, viz_self, struct_self}]
        self.skip = 0          # dentro de <style>/<script>
        self.buf = []          # texto de VALORES (números-afirmação)
        self.struct_buf = []   # texto de rótulos estruturais (eixo/categoria/marco)

    def _inside_viz(self):
        return any(f["viz_self"] for f in self.stack)

    def _inside_struct(self):
        return any(f["struct_self"] for f in self.stack)

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script"):
            self.skip += 1
            return
        cls = dict(attrs).get("class", "") or ""
        parts = cls.split()
        viz_self = any(c in VIZ_CLASSES for c in parts)
        struct_self = any(c in STRUCTURAL_CLASSES for c in parts)
        self.stack.append({"tag": tag, "viz_self": viz_self, "struct_self": struct_self})

    def handle_startendtag(self, tag, attrs):
        pass  # void/self-closing (line, circle, path...) — sem texto

    def handle_endtag(self, tag):
        if tag in ("style", "script") and self.skip:
            self.skip -= 1
            return
        for idx in range(len(self.stack) - 1, -1, -1):
            if self.stack[idx]["tag"] == tag:
                del self.stack[idx]
                break

    def handle_data(self, data):
        if self.skip or not self._inside_viz():
            return
        if data.strip():
            if self._inside_struct():
                self.struct_buf.append(data)
            else:
                self.buf.append(data)


def main():
    if len(sys.argv) < 3:
        print("uso: check_provenance.py <deck.html> <fonte1> [fonte2 ...]",
              file=sys.stderr)
        sys.exit(2)
    deck_path, src_paths = sys.argv[1], sys.argv[2:]

    try:
        with open(deck_path, encoding="utf-8") as f:
            html = f.read()
    except (FileNotFoundError, OSError, UnicodeDecodeError) as e:
        print(f"erro de ambiente: não foi possível ler o deck '{deck_path}': {e}",
              file=sys.stderr)
        sys.exit(2)
    src_text = ""
    for p in src_paths:
        try:
            with open(p, encoding="utf-8") as f:
                src_text += "\n" + f.read()
        except (FileNotFoundError, OSError, UnicodeDecodeError) as e:
            print(f"erro de ambiente: não foi possível ler a fonte '{p}': {e}",
                  file=sys.stderr)
            sys.exit(2)

    src_nums = numbers(src_text)

    p = VizText()
    p.feed(html)
    deck_nums = numbers(" ".join(p.buf))
    struct_nums = numbers(" ".join(p.struct_buf))

    missing = sorted(
        (c for c in deck_nums if is_claim(c) and c not in src_nums),
        key=lambda s: (len(s), s),
    )
    # rótulos estruturais ausentes: aviso não-bloqueante (eixo/categoria/marco)
    struct_warn = sorted(
        (c for c in struct_nums if is_claim(c) and c not in src_nums),
        key=lambda s: (len(s), s),
    )

    if missing:
        print(f"\n⚠️  {len(missing)} número(s) de gráfico/métrica NÃO "
              f"encontrado(s) na(s) fonte(s) (provável dado inventado):\n")
        for c in missing:
            print(f"  ✗ {c}")
        print("\nRevise: todo número de viz tem que rastrear ao material/fonte. "
              "Cite no .cap ou corrija o valor.\n")
        sys.exit(1)
    n = len([c for c in deck_nums if is_claim(c)])
    if struct_warn:
        sw = ", ".join(struct_warn)
        print(f"  ℹ  rótulos de eixo/categoria ausentes da fonte (aviso): {sw}")
    print(f"✓ Proveniência OK — os {n} número(s) de viz do deck existem na(s) fonte(s).")
    sys.exit(0)


if __name__ == "__main__":
    main()
