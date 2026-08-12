#!/usr/bin/env python3
"""test_mutacao.py — prova que as travas do lixeiro têm teste que MORDE.

Para cada trava de segurança da colheita: desliga SÓ ela numa cópia do plugin,
roda a suíte inteira, e exige que ela acuse. Trava cuja remoção mantém a suíte
verde é trava sem cobertura — o defeito que ela previne voltaria sem que nenhum
teste percebesse. Nasceu do estrago de 2026-08-11 (suíte em andamento encerrada
pelo fim de turno): cada trava daqui é um jeito de aquele estrago renascer.
"""
import os
import shutil
import subprocess
import sys
import tempfile

# A raiz do plugin, relativa a este arquivo — nunca um caminho de máquina.
SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MUTACOES = [
    ("A) sem a trava de idade mínima",
     'if p["idade"] <= OCIOSO_MIN:', 'if False:'),
    ("B) sem a janela de relógio do ocioso",
     'if visto is None or agora - visto <= OCIOSO_MIN:', 'if False:'),
    ("C) CPU do processo em vez da ÁRVORE",
     'cpu_arvore.get(p["pid"], p["cpu"]) > antes + 0.5', 'p["cpu"] > antes + 0.5'),
    ("D) foto de CPU renovada todo turno",
     'if antes is None or trocou or agora_cpu > antes + 0.5 or anot.get("cpu_visto_em") is None:',
     'if True:'),
    ("E) regra VELHA de volta: efêmero vivo morre",
     '            antes = anot.get("cpu_ultimo_turno")\n',
     '            if anot.get("classe") == "efemero":\n'
     '                achados.append((anot, p, "suite/build que devia ter terminado"))\n'
     '                continue\n'
     '            antes = anot.get("cpu_ultimo_turno")\n'),
    ("F) fim de sessão sem medir quem trabalha",
     '        ocupados = trabalhando([p["pid"] for _, p, _ in alvos])', '        ocupados = set()'),
    ("G) foto comparada entre processos diferentes",
     'if antes is None or anot.get("cpu_pid") != p["pid"]:', 'if antes is None:'),
    ("H) foto não troca de dono ao mudar o pid",
     'trocou = anot.get("cpu_pid") != p["pid"]', 'trocou = False'),
    ("I) sem o pareamento 1:1 anotação↔processo",
     'if p["pid"] in tomados or not casa(anot, p):', 'if not casa(anot, p):'),
    ("J) sem a reivindicação da foto anterior",
     'if reivindica and anot.get("cpu_pid") != p["pid"]:', 'if False:'),
    ("K) sem a reconferência do pid antes do sinal",
     'if agora_cmd.get(p["pid"]) != p["cmd"]:', 'if False:'),
    ("L) órfã poupada perde o registro mesmo assim",
     'if not dry_run and not candidatos(sid, "sessao"):', 'if not dry_run:'),
    ("CONTROLE (nenhuma mutação)", None, None),
]


def roda(de_para):
    base = tempfile.mkdtemp(prefix="lixeiro-mut-")
    shutil.copytree(os.path.join(SRC, "lib"), os.path.join(base, "lib"))
    shutil.copytree(os.path.join(SRC, "skills"), os.path.join(base, "skills"))
    alvo = os.path.join(base, "lib", "lixeiro.py")
    if de_para[0]:
        s = open(alvo, encoding="utf-8").read()
        if de_para[0] not in s:
            return "PADRÃO NÃO ENCONTRADO — a mutação não testou nada"
        open(alvo, "w", encoding="utf-8").write(s.replace(de_para[0], de_para[1]))
    out = subprocess.run([sys.executable, os.path.join(base, "lib", "test_lixeiro.py")],
                         capture_output=True, text=True,
                         stdin=subprocess.DEVNULL, start_new_session=True)
    shutil.rmtree(base, ignore_errors=True)
    return (out.stdout.strip().splitlines() or ["(sem saída)"])[-1]


falhou_o_teste_de_mutacao = []
for nome, de, para in MUTACOES:
    linha = roda((de, para))
    controle = de is None
    verde = "0 falhas" in linha
    veredito = "ok" if (verde == controle) else "⚠️  TRAVA SEM COBERTURA"
    if verde != controle:
        falhou_o_teste_de_mutacao.append(nome)
    print("%-42s %-24s %s" % (nome, linha, veredito))

print()
print("travas sem cobertura: %d" % len(falhou_o_teste_de_mutacao))
sys.exit(1 if falhou_o_teste_de_mutacao else 0)
