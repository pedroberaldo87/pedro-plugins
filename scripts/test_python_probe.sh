#!/bin/bash
# test_python_probe.sh — RED→GREEN da issue 1 (python3).
# Trava: todo guard que usa `command -v python3` TAMBÉM testa execução
# (python3 --version) — o stub da Microsoft Store engana só-presença.
# Red hoje: os guards usam só command -v.
FAIL=0
for f in $(grep -rl 'command -v python3' plugins/*/hooks/*.sh 2>/dev/null); do
  if ! grep -qE -- '--version >/dev/null 2>&1' "$f"; then
    echo "FAIL $f: só command -v, sem teste de execução"; FAIL=1
  fi
done
# Segunda camada: o comando escrito dentro de plugins/*/hooks/hooks.json.
# Guard em .sh não protege quem chama python3 direto do hooks.json — ali o stub
# que existe mas não executa quebra o hook sem aviso. Fail-open: sem python3 que
# rode, o bloco é pulado (o próprio bloco não pode ser a dependência que falta).
if python3 --version >/dev/null 2>&1; then
  JSON_OUT=$(python3 - <<'PY'
import glob, json, sys

achados = 0
for caminho in sorted(glob.glob('plugins/*/hooks/hooks.json')):
    try:
        bruto = open(caminho, encoding='utf-8').read()
        dados = json.loads(bruto)
    except Exception:
        continue  # fail-open: json ilegível não é o alvo desta régua
    linhas = bruto.splitlines()
    comandos = []

    def colher(no):
        if isinstance(no, dict):
            cmd = no.get('command')
            if isinstance(cmd, str):
                comandos.append(cmd)
            for v in no.values():
                colher(v)
        elif isinstance(no, list):
            for v in no:
                colher(v)

    colher(dados)
    for cmd in comandos:
        if 'python3' not in cmd:
            continue
        if '--version >/dev/null 2>&1' in cmd:
            continue
        limpar = lambda s: s.replace('\\', '').replace('"', '').replace("'", '')
        alvo = limpar(cmd.split('python3')[-1])[:40]
        linha = next((i for i, l in enumerate(linhas, 1) if alvo in limpar(l)), 0)
        print('FAIL %s:%d: chama python3 sem sondar execução' % (caminho, linha))
        achados += 1
sys.exit(1 if achados else 0)
PY
  ) || FAIL=1
  [ -n "$JSON_OUT" ] && echo "$JSON_OUT"
fi

# Terceira camada: interpretador que EXISTE e NÃO executa (o stub da Microsoft Store,
# que sai 9009). Com ele na frente do PATH, o comando do hooks.json tem que desistir
# em silêncio — sair 0 e não falar nada — em vez de estourar na cara de quem instalou.
# Fail-open: sem python3 de verdade não dá pra extrair o comando, então o caso é pulado.
if python3 --version >/dev/null 2>&1; then
  SPEC=$(python3 - <<'PY'
import glob, json, os

for caminho in sorted(glob.glob('plugins/*/hooks/hooks.json')):
    try:
        dados = json.load(open(caminho, encoding='utf-8'))
    except Exception:
        continue  # fail-open: json ilegível não é o alvo desta régua
    achado = []

    def colher(no):
        if isinstance(no, dict):
            cmd = no.get('command')
            if isinstance(cmd, str) and 'python3' in cmd:
                achado.append(cmd)
            for v in no.values():
                colher(v)
        elif isinstance(no, list):
            for v in no:
                colher(v)

    colher(dados)
    if achado:
        print(os.path.dirname(os.path.dirname(caminho)))
        print(achado[0])
        break
PY
  )
  RAIZ=$(printf '%s\n' "$SPEC" | head -n 1)
  CMD=$(printf '%s\n' "$SPEC" | tail -n 1)
  if [ -n "$CMD" ]; then
    FALSO=$(mktemp -d)
    printf '#!/bin/sh\nexit 9009\n' > "$FALSO/python3"
    chmod +x "$FALSO/python3"
    SAIDA=$(PATH="$FALSO:$PATH" CLAUDE_PLUGIN_ROOT="$PWD/$RAIZ" sh -c "$CMD" </dev/null 2>&1)
    CODIGO=$?
    rm -rf "$FALSO"
    if [ "$CODIGO" != "0" ] || [ -n "$SAIDA" ]; then
      echo "FAIL $RAIZ/hooks/hooks.json: com python3 falso (9009) saiu $CODIGO e disse: $SAIDA"
      FAIL=1
    fi
  fi
fi

[ "$FAIL" = "0" ] && echo "ok   todos os guards testam execução do python3"
exit $FAIL
