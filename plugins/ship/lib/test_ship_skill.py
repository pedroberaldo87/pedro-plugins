#!/usr/bin/env python3
"""Suíte do texto da skill /ship — o fechamento do repositório privado (dual git, F3.4).

    python3 plugins/ship/lib/test_ship_skill.py
"""
import os
import sys

SKILL_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "ship", "SKILL.md")
FAILS = []


def check(label, cond):
    print("  %s %s" % ("ok  " if cond else "FAIL", label))
    if not cond:
        FAILS.append(label)


def main():
    t = open(SKILL_MD, encoding="utf-8").read()
    check("a publicação nunca pula a trava (--no-verify proibido)", "Nunca `--no-verify`, nem no commit nem no push." in t)
    check("o privado fecha por devgit fechar, resolvido pelo nome do plugin",
          'command -v devgit >/dev/null && devgit fechar "ship:' in t)
    check("o fechamento vem depois de verificar o deploy e antes de finalizar a branch",
          t.index("### 5. Verificar o Deploy") < t.index("### 5.5. Fechar o Privado") < t.index("### 6. Finalizar a Branch"))
    print("\nship skill: %d falha(s)" % len(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
