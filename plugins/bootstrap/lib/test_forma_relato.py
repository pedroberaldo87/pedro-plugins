"""O gatilho do juiz de forma: so o turno que passou pelo /visual chega ao modelo.

O caso que importa e o primeiro — antes deste gate, TODO fim de turno com prosa+prova
chamava `claude -p`: 463 julgamentos em 9 dias, ~25s cada, US$ 19,26.
"""
import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "stop-forma-relato.py"
RELATO = "Gate verde: unit 981.\nNao commitado.\n\n```\n$ pytest  981 passed\n```"

USUARIO = {"type": "user", "message": {"role": "user", "content": "faz o diagnostico"}}
ASSISTENTE = {"type": "assistant",
              "message": {"role": "assistant",
                          "content": [{"type": "text", "text": RELATO}]}}


def _tool(nome, entrada):
    return {"type": "assistant",
            "message": {"role": "assistant",
                        "content": [{"type": "tool_use", "name": nome, "input": entrada}]}}


def _roda(tmp_path, linhas):
    """Devolve os motivos batidos. Sem `claude` no PATH o juiz e fail-open, entao o
    que se mede aqui e so o gatilho: 'sem /visual no turno' vs. chegou a julgar."""
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("".join(json.dumps(x) + "\n" for x in linhas), encoding="utf-8")
    estado = tmp_path / "estado"
    subprocess.run([sys.executable, str(HOOK)],
                   input=json.dumps({"session_id": "teste",
                                     "transcript_path": str(transcript),
                                     "stop_hook_active": False}),
                   capture_output=True, text=True, start_new_session=True,
                   env={"PATH": "/usr/bin:/bin", "FORMA_RELATO_STATE": str(estado)})
    log = estado / "batidas.log"
    return [json.loads(x)["motivo"] for x in log.read_text(encoding="utf-8").splitlines()]


def test_turno_sem_visual_nao_gasta_modelo(tmp_path):
    assert _roda(tmp_path, [USUARIO, ASSISTENTE]) == ["sem /visual no turno"]


def test_skill_visual_chega_ao_juiz(tmp_path):
    linhas = [USUARIO, _tool("Skill", {"skill": "visual"}), ASSISTENTE]
    assert "sem /visual no turno" not in _roda(tmp_path, linhas)


def test_comando_visual_chega_ao_juiz(tmp_path):
    pedido = {"type": "user",
              "message": {"role": "user", "content": "<command-name>/visual</command-name>"}}
    assert "sem /visual no turno" not in _roda(tmp_path, [pedido, ASSISTENTE])


def test_pagina_escrita_chega_ao_juiz(tmp_path):
    escreve = _tool("Write", {"file_path": "/x/.claude/visual/plano.html"})
    assert "sem /visual no turno" not in _roda(tmp_path, [USUARIO, escreve, ASSISTENTE])


def test_visual_de_turno_anterior_nao_conta(tmp_path):
    """A varredura para no pedido humano: o /visual de ontem nao arrasta o turno de hoje."""
    linhas = [USUARIO, _tool("Skill", {"skill": "visual"}), ASSISTENTE,
              {"type": "user", "message": {"role": "user", "content": "e agora?"}},
              ASSISTENTE]
    assert _roda(tmp_path, linhas) == ["sem /visual no turno"]


if __name__ == "__main__":
    # O gate do repositorio roda `python3 <suite>`, nao pytest — sem este executor a
    # suite saia 0 SEM RODAR NENHUM CASO (o antipadrao "passa com e sem a mudanca").
    import tempfile
    falhas = 0
    casos = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for caso in casos:
        with tempfile.TemporaryDirectory() as d:
            try:
                caso(Path(d))
                print(f"  ok   {caso.__name__}")
            except AssertionError as e:
                falhas += 1
                print(f"  FAIL {caso.__name__} — {e}")
    print(f"\n{len(casos) - falhas} ok · {falhas} FAIL")
    sys.exit(1 if falhas else 0)
