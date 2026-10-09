"""Todo hook `type: "prompt"` do marketplace pede ao avaliador o esquema de resposta documentado.

Hook de prompt responde `{"ok": true}` para liberar ou `{"ok": false, "reason": "..."}` para
bloquear (doc oficial de hooks, "Prompt-based hooks" → "Response schema"). O guarda de Agent
Teams pedia o JSON de hook de COMANDO (`hookSpecificOutput.permissionDecision`); o avaliador
respondia fora do esquema e o harness tratava como bloqueio — barrava TODO agente, inclusive
quando a própria conclusão era "allow" (medido em 2026-10-09).
"""
import glob
import json
import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
falhas = []
vistos = 0
for caminho in sorted(glob.glob(os.path.join(RAIZ, 'plugins', '*', 'hooks', 'hooks.json'))):
    dados = json.load(open(caminho, encoding='utf-8'))
    for evento, grupos in dados.get('hooks', {}).items():
        for grupo in grupos:
            for hook in grupo.get('hooks', []):
                if hook.get('type') != 'prompt':
                    continue
                vistos += 1
                texto = hook.get('prompt', '')
                onde = f"{os.path.relpath(caminho, RAIZ)} · {evento} · {grupo.get('matcher', '*')}"
                if '"ok"' not in texto:
                    falhas.append(f'{onde}: não pede o campo "ok" do esquema de resposta')
                if 'hookSpecificOutput' in texto or 'permissionDecision' in texto:
                    falhas.append(f'{onde}: pede o JSON de hook de comando, que o hook de prompt não lê')

if vistos == 0:
    falhas.append('nenhum hook de prompt encontrado — o glob não achou o marketplace')
for f in falhas:
    print('FAIL', f)
print(f'{vistos} hook(s) de prompt conferido(s), {len(falhas)} falha(s)')
sys.exit(1 if falhas else 0)
