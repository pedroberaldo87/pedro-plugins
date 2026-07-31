#!/usr/bin/env python3
"""
check_fidelity.py — garante que o deck não inventou texto.

Extrai cada bloco de texto dos slides do HTML gerado e confere se aparece,
literalmente (ignorando acento/pontuação/caixa), no .md de origem. Blocos
"de conteúdo" com 6+ palavras que NÃO existem na fonte são sinalizados como
provável invenção — a regra de ouro da skill: o texto é do autor, não do modelo.

Uso:
    python3 check_fidelity.py <deck.html> <fonte.md>

Saída: lista de trechos suspeitos. Exit 1 se houver algum, 0 se limpo.
Títulos de slide, rótulos e enumeradores curtos (<6 palavras) são ignorados
de propósito — derivam dos headings e não são "texto inventado".
"""
import re
import sys
import unicodedata
from html.parser import HTMLParser

# h1/h2 ficam de fora: títulos de slide derivam/encurtam os headings do .md
# por natureza. Verificamos a PROSA do corpo, onde mora o risco de invenção.
BLOCK_TAGS = {"li", "p", "h3", "h4"}
BLOCK_DIV_CLASSES = {"pull", "statement", "def", "ex", "lead", "sub"}
MIN_WORDS = 6  # abaixo disso é rótulo/título derivado, não prosa do autor


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def strip_enum(words):
    # remove enumeradores à esquerda ("01", "1", "—") que a skill injeta
    while words and re.fullmatch(r"\d+", words[0]):
        words = words[1:]
    return words


class SlideText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.frames = []          # pilha de buffers de bloco
        self.chunks = []          # (texto,) blocos coletados
        self.skip_depth = 0       # dentro de <style>/<script>

    def _is_block(self, tag, attrs):
        if tag in BLOCK_TAGS:
            return True
        if tag == "div":
            cls = dict(attrs).get("class", "")
            return any(c in BLOCK_DIV_CLASSES for c in cls.split())
        return False

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script"):
            self.skip_depth += 1
            return
        if self._is_block(tag, attrs):
            self.frames.append({"tag": tag, "buf": []})

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in ("style", "script") and self.skip_depth:
            self.skip_depth -= 1
            return
        # fecha o frame de bloco mais interno que casa com a tag
        for idx in range(len(self.frames) - 1, -1, -1):
            if self.frames[idx]["tag"] == tag:
                frame = self.frames.pop(idx)
                text = " ".join(frame["buf"]).strip()
                if text:
                    self.chunks.append(text)
                break

    def handle_data(self, data):
        if self.skip_depth or not self.frames:
            return
        if data.strip():
            self.frames[-1]["buf"].append(data.strip())


def main():
    if len(sys.argv) != 3:
        print("uso: check_fidelity.py <deck.html> <fonte.md>", file=sys.stderr)
        sys.exit(2)
    deck_path, md_path = sys.argv[1], sys.argv[2]
    with open(deck_path, encoding="utf-8") as f:
        html = f.read()
    with open(md_path, encoding="utf-8") as f:
        source = norm(f.read())

    p = SlideText()
    p.feed(html)

    suspicious = []
    seen = set()
    for chunk in p.chunks:
        words = strip_enum(norm(chunk).split())
        if len(words) < MIN_WORDS:
            continue
        key = " ".join(words)
        if key in seen:
            continue
        seen.add(key)
        if key not in source:
            suspicious.append(chunk.strip())

    if suspicious:
        print(f"\n⚠️  {len(suspicious)} trecho(s) NÃO encontrado(s) na fonte "
              f"(provável texto inventado):\n")
        for s in suspicious:
            print(f"  ✗ {s}")
        print("\nRevise: use o texto literal do .md ou remova o acréscimo.\n")
        sys.exit(1)
    print("✓ Fidelidade OK — todo bloco de conteúdo do deck existe na fonte.")
    sys.exit(0)


if __name__ == "__main__":
    main()
