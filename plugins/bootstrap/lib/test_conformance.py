#!/usr/bin/env python3
"""Testes do conformance.py e do acordo escritor/leitor do bypass.log.

Roda tudo contra um CLAUDE_CONFIG_DIR temporario — nunca toca na config real.
Sem framework: assert + __main__, convencao do repo (patterns.md).

    python3 plugins/bootstrap/lib/test_conformance.py
"""
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BOOTSTRAP = AQUI.parent
CONFORMANCE = AQUI / "conformance.py"
SCOPE_COP = BOOTSTRAP.parent / "guardrails" / "hooks" / "scope-cop.sh"

ok = falhas = 0
_BASH = None


def bash_posix():
    """O caminho de um bash que RODA — não o primeiro que o PATH oferecer.

    No Windows o `bash` do PATH é o do WSL (`System32\\bash.exe`), e em máquina
    sem distro instalada ele responde `Windows Subsystem for Linux has no
    installed distributions.` em UTF-16 — o que chega ao Python como stdout
    VAZIO. O teste então reprovava com "o hook não bloqueou", que é a conclusão
    errada sobre o hook certo: quem não rodou foi o interpretador.

    Três tentativas de consertar isso pelo PATH do runner falharam (GITHUB_PATH
    não venceu o System32; `export PATH=/usr/bin:$PATH` também não). A decisão
    que sobrou é a honesta: **quem precisa do bash procura um que funcione**, e
    o critério é ele responder — não estar no PATH. Ordem: o do PATH, se
    responder; senão os lugares onde o Git Bash mora no Windows.

    Devolve `None` quando não há nenhum. Quem chama PULA o caso e diz isso em
    voz alta — hook shell sem shell não é falha do hook.
    """
    global _BASH
    if _BASH is not None:
        return _BASH or None
    candidatos = [shutil.which("bash")]
    if os.name == "nt":
        # Barra NORMAL de propósito: o Windows aceita as duas, e a invertida em
        # literal Python é campo minado (`\b` de `\bin` vira backspace).
        candidatos += ["C:/Program Files/Git/bin/bash.exe",
                       "C:/Program Files/Git/usr/bin/bash.exe",
                       "C:/Program Files (x86)/Git/bin/bash.exe"]
    for c in candidatos:
        if not c or not os.path.exists(c):
            continue
        try:
            r = subprocess.run([c, "-c", "echo VIVO"], capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=20, stdin=subprocess.DEVNULL,
                               start_new_session=True)
        except (OSError, subprocess.SubprocessError):
            continue
        if r.stdout.strip() == "VIVO":
            _BASH = c
            return c
    _BASH = ""
    return None


def check(nome, cond, detalhe=""):
    global ok, falhas
    if cond:
        ok += 1
        print(f"  ok   {nome}")
    else:
        falhas += 1
        print(f"  FAIL {nome}  {detalhe}")


def roda_conformance(config_dir, cfg_versionado):
    """Executa o conformance com um CLAUDE_CONFIG_DIR falso e devolve o JSON."""
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(config_dir),
               CLAUDE_PLUGIN_ROOT=str(cfg_versionado.parent))
    r = subprocess.run([sys.executable, str(CONFORMANCE), "--json"],
                       capture_output=True, text=True, encoding="utf-8", env=env,
                       stdin=subprocess.DEVNULL, start_new_session=True)
    try:
        return json.loads(r.stdout)
    except ValueError:
        raise AssertionError(f"conformance nao devolveu JSON: {r.stdout[:200]} {r.stderr[:200]}")


def areas(res):
    return {d["area"] for d in res["desvios"]}


def monta_mundo(raiz, *, plugin_ligado=True, style_setado=True, teto_duplicado=False):
    """Cria um par (config viva, config versionada) minimo e coerente."""
    cfg = raiz / "versionado" / "config"
    (cfg / ".." / "output-styles").resolve().mkdir(parents=True, exist_ok=True)
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg.parent / "output-styles" / "clean-style.md").write_text(
        "---\nname: Clean Style\nkeep-coding-instructions: true\nforce-for-plugin: true\n---\ncorpo\n")
    (cfg / "manifest.json").write_text(json.dumps({
        "marketplaces": [{"name": "mkt", "plugins": [{"name": "algum", "enabled": False}]}],
        "skills": {"permitidas": []},
    }))
    claude_md = "# t\n- regra sem numero\n"
    if teto_duplicado:
        claude_md = "# t\n- no maximo 3-4 linhas\n- nunca passar de 10 linhas\n"
    (cfg / "CLAUDE-global.md").write_text(claude_md)

    vivo = raiz / "vivo"
    (vivo / "skills").mkdir(parents=True, exist_ok=True)
    (vivo / "CLAUDE.md").write_text(claude_md)
    settings = {
        "enabledPlugins": {"bootstrap@pedro-plugins": plugin_ligado},
        "outputStyle": "Clean Style" if style_setado else None,
    }
    if not style_setado:
        del settings["outputStyle"]
    (vivo / "settings.json").write_text(json.dumps(settings))
    return vivo, cfg


def teste_mundo_conforme():
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = monta_mundo(Path(t))
        res = roda_conformance(vivo, cfg)
        check("mundo coerente nao inventa desvio de plugin/teto/style",
              not ({"plugins", "teto", "output style"} & areas(res)),
              str([d["o_que"] for d in res["desvios"]]))


def teste_plugin_religado_na_mao():
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = monta_mundo(Path(t))
        s = json.loads((vivo / "settings.json").read_text())
        s["enabledPlugins"]["algum@mkt"] = True     # manifest diz enabled: false
        (vivo / "settings.json").write_text(json.dumps(s))
        res = roda_conformance(vivo, cfg)
        check("acusa plugin ligado que o manifest manda desligar", "plugins" in areas(res))


def escreve_instalados(vivo, refs):
    """installed_plugins.json no formato v2 real: ref -> lista de instalacoes."""
    (vivo / "plugins").mkdir(parents=True, exist_ok=True)
    (vivo / "plugins" / "installed_plugins.json").write_text(json.dumps({
        "version": 2,
        "plugins": {r: [{"scope": "user", "installPath": f"/cache/{r}"}] for r in refs}}))


def manifest_quer_ligado(cfg):
    """O plugin 'algum@mkt' do mundo minimo passa a ser um que o contrato quer LIGADO."""
    man = json.loads((cfg / "manifest.json").read_text())
    man["marketplaces"][0]["plugins"][0]["enabled"] = True
    (cfg / "manifest.json").write_text(json.dumps(man))


def teste_plugin_ausente_manda_instalar_e_nao_habilitar():
    """F6.1: lendo so o enabledPlugins, plugin que nem esta na maquina virava
    'devia estar LIGADO e esta desligado' com conserto `claude plugin enable`, que
    falha. Ausente pede install; ausente que o manifest quer desligado nao e desvio."""
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = monta_mundo(Path(t))
        escreve_instalados(vivo, ["bootstrap@pedro-plugins"])   # 'algum@mkt' ausente
        res = roda_conformance(vivo, cfg)
        check("ausente que o manifest quer DESLIGADO nao vira desvio",
              "plugins" not in areas(res),
              str([d["o_que"] for d in res["desvios"] if d["area"] == "plugins"]))

        manifest_quer_ligado(cfg)
        res = roda_conformance(vivo, cfg)
        d = [x for x in res["desvios"] if x["area"] == "plugins"]
        check("plugin ausente e acusado como nao instalado",
              bool(d) and "nao instalado" in d[0]["o_que"], str(d[:1]))
        check("e o conserto e install, nao enable",
              bool(d) and d[0]["conserto"] == "claude plugin install algum@mkt", str(d[:1]))


def teste_plugin_instalado_porem_desligado_pede_enable():
    """A outra metade da F6.1: instalado e desligado continua sendo `plugin enable`,
    e instalado+ligado nao acusa nada."""
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = monta_mundo(Path(t))
        manifest_quer_ligado(cfg)
        escreve_instalados(vivo, ["bootstrap@pedro-plugins", "algum@mkt"])
        res = roda_conformance(vivo, cfg)
        d = [x for x in res["desvios"] if x["area"] == "plugins"]
        check("instalado porem desligado pede enable",
              bool(d) and d[0]["conserto"] == "claude plugin enable algum@mkt", str(d[:1]))
        check("e nao acusa ausencia de quem esta instalado",
              bool(d) and "nao instalado" not in d[0]["o_que"], str(d[:1]))

        s = json.loads((vivo / "settings.json").read_text())
        s["enabledPlugins"]["algum@mkt"] = True
        (vivo / "settings.json").write_text(json.dumps(s))
        res = roda_conformance(vivo, cfg)
        check("instalado e ligado quando o manifest quer ligado e conforme",
              "plugins" not in areas(res),
              str([x["o_que"] for x in res["desvios"] if x["area"] == "plugins"]))


def teste_output_style_nao_setado():
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = monta_mundo(Path(t), style_setado=False)
        res = roda_conformance(vivo, cfg)
        check("acusa outputStyle ausente", "output style" in areas(res))


def teste_teto_duplicado():
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = monta_mundo(Path(t), teto_duplicado=True)
        res = roda_conformance(vivo, cfg)
        check("acusa mais de uma regra numerica de linhas", "teto" in areas(res))


def teste_skill_nao_declarada():
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = monta_mundo(Path(t))
        (vivo / "skills" / "intrusa").mkdir()
        res = roda_conformance(vivo, cfg)
        check("acusa skill fora da lista do manifest", "skills" in areas(res))


AVISA = "#!/bin/bash\n# conformance: default-warn\necho oi\n"
NEGA = '#!/bin/bash\nprintf \'{"hookSpecificOutput":{"permissionDecision":"deny"}}\'\n'


def monta_cache(vivo, plugins, onde="hooks/guard.sh"):
    """plugins = [(nome, matcher, comando, corpo)] -> escreve o cache e habilita cada um.

    'onde' e o caminho do script DENTRO da raiz do plugin (a raiz tambem e layout valido).
    """
    s = json.loads((vivo / "settings.json").read_text())
    for nome, matcher, comando, corpo in plugins:
        raiz = vivo / "plugins" / "cache" / "mkt" / nome / "1.0.0"
        (raiz / "hooks").mkdir(parents=True, exist_ok=True)
        (raiz / "hooks" / "hooks.json").write_text(json.dumps({
            "hooks": {"PreToolUse": [{"matcher": matcher, "hooks": [
                {"type": "command", "command": comando}]}]}}))
        script = raiz / onde
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(corpo)
        s["enabledPlugins"][f"{nome}@mkt"] = True
    (vivo / "settings.json").write_text(json.dumps(s))


def teste_redirecionamento_nao_vira_script_fantasma():
    """F5: '<script>.sh 2>/dev/null' partia em dois tokens; o fantasma '2>/dev/null'
    nao existia, caia no except OSError (= assume o pior) e anulava o default-warn."""
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = monta_mundo(Path(t))
        cmd = "${CLAUDE_PLUGIN_ROOT}/hooks/guard.sh 2>/dev/null"
        monta_cache(vivo, [("um", "Grep", cmd, AVISA), ("dois", "Grep", cmd, AVISA)])
        res = roda_conformance(vivo, cfg)
        check("redirecionamento no comando nao vira script fantasma que bloqueia",
              "hooks" not in areas(res),
              str([d["o_que"] for d in res["desvios"] if d["area"] == "hooks"]))


def teste_variavel_sem_chaves_tambem_resolve():
    """F5: o split hardcoded era 'CLAUDE_PLUGIN_ROOT}/' — a forma sem chaves nao casava
    e o alvo resolvia 100% fantasma."""
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = monta_mundo(Path(t))
        cmd = "$CLAUDE_PLUGIN_ROOT/hooks/guard.sh"
        monta_cache(vivo, [("um", "Grep", cmd, AVISA), ("dois", "Grep", cmd, AVISA)])
        res = roda_conformance(vivo, cfg)
        check("$CLAUDE_PLUGIN_ROOT sem chaves resolve pro script real",
              "hooks" not in areas(res),
              str([d["o_que"] for d in res["desvios"] if d["area"] == "hooks"]))


def teste_aspa_simples_no_comando_resolve_como_o_shell_resolveria():
    """R8: a tokenizacao so tirava aspa DUPLA, entao um comando com aspa simples
    (forma valida e comum) deixava a aspa colada no token, nada resolvia e o plugin
    caia no ramo conservador — o falso-positivo que esta rodada veio matar."""
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = monta_mundo(Path(t))
        cmd = "'${CLAUDE_PLUGIN_ROOT}/hooks/guard.sh'"
        monta_cache(vivo, [("um", "Grep", cmd, AVISA), ("dois", "Grep", cmd, AVISA)])
        res = roda_conformance(vivo, cfg)
        check("script entre aspas simples resolve igual ao shell",
              "hooks" not in areas(res),
              str([d["o_que"] for d in res["desvios"] if d["area"] == "hooks"]))


def teste_aspas_desbalanceadas_nao_derrubam_o_conformance():
    """R8: shlex levanta ValueError em aspa sem fechamento. O conformance nao pode
    morrer por causa de um hooks.json torto — cai no comportamento antigo."""
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = monta_mundo(Path(t))
        cmd = "${CLAUDE_PLUGIN_ROOT}/hooks/guard.sh 'sem-fechar"
        monta_cache(vivo, [("um", "Grep", cmd, AVISA), ("dois", "Grep", cmd, AVISA)])
        res = roda_conformance(vivo, cfg)
        check("aspa desbalanceada nao derruba o conformance",
              "hooks" not in areas(res),
              str([d["o_que"] for d in res["desvios"] if d["area"] == "hooks"]))


def teste_token_absoluto_fora_da_raiz_nao_decide():
    """F15: 'raiz / tok' com token absoluto descarta a raiz (pathlib), entao um arquivo
    de fora do plugin passava a ditar o veredito de bloqueio."""
    with tempfile.TemporaryDirectory() as t:
        raiz = Path(t)
        vivo, cfg = monta_mundo(raiz)
        fora = raiz / "fora" / "wrapper.sh"
        fora.parent.mkdir(parents=True, exist_ok=True)
        fora.write_text("#!/bin/bash\nexit 2\n")
        cmd = f"{fora} ${{CLAUDE_PLUGIN_ROOT}}/hooks/guard.sh"
        monta_cache(vivo, [("um", "Grep", cmd, AVISA), ("dois", "Grep", cmd, AVISA)])
        res = roda_conformance(vivo, cfg)
        check("arquivo fora da raiz do plugin nao decide o veredito de bloqueio",
              "hooks" not in areas(res),
              str([d["o_que"] for d in res["desvios"] if d["area"] == "hooks"]))


def teste_nenhum_token_resolve_conta_como_disputante():
    """Ramo conservador: se nada resolve pra script real, nao da pra afirmar que so avisa."""
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = monta_mundo(Path(t))
        cmd = "${CLAUDE_PLUGIN_ROOT}/hooks/nao-existe.sh"
        monta_cache(vivo, [("um", "Grep", cmd, AVISA), ("dois", "Grep", cmd, AVISA)])
        res = roda_conformance(vivo, cfg)
        check("comando que nao resolve pra script real segue contando como disputante",
              "hooks" in areas(res),
              str([d["o_que"] for d in res["desvios"]]))


def teste_caminho_relativo_sem_a_variavel_nao_vira_alvo():
    """R-A8: so a marca ${CLAUDE_PLUGIN_ROOT}/ (ou sem chaves) adota um token. Caminho
    relativo puro nao e resolvido pela raiz do plugin em runtime — o cwd do hook nao e
    a raiz —, entao adotar 'hooks/guard.sh' era ler um script que o Claude Code nunca
    executaria daquele jeito. Token sem a marca cai no ramo conservador."""
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = monta_mundo(Path(t))
        cmd = "hooks/guard.sh"
        monta_cache(vivo, [("um", "Grep", cmd, AVISA), ("dois", "Grep", cmd, AVISA)])
        res = roda_conformance(vivo, cfg)
        check("caminho relativo sem ${CLAUDE_PLUGIN_ROOT} nao vira alvo de bloqueio",
              "hooks" in areas(res),
              str([d["o_que"] for d in res["desvios"]]))


def teste_script_na_raiz_do_plugin_tambem_resolve():
    """F-DELTA-2: o descarte de token sem '/' rodava DEPOIS de arrancar a marca
    ${CLAUDE_PLUGIN_ROOT}/, entao '${CLAUDE_PLUGIN_ROOT}/guard.sh' virava 'guard.sh',
    era jogado fora por nao ter barra, e um hook na RAIZ do plugin nunca resolvia:
    alvos ficava vazio e o plugin caia no ramo conservador mesmo marcado
    '# conformance: default-warn'. A marca + arquivo existente sob a raiz basta."""
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = monta_mundo(Path(t))
        cmd = "${CLAUDE_PLUGIN_ROOT}/guard.sh"
        monta_cache(vivo, [("um", "Grep", cmd, AVISA), ("dois", "Grep", cmd, AVISA)],
                    onde="guard.sh")
        res = roda_conformance(vivo, cfg)
        check("script na RAIZ do plugin resolve e o default-warn vale",
              "hooks" not in areas(res),
              str([d["o_que"] for d in res["desvios"] if d["area"] == "hooks"]))


def teste_dois_denies_na_mesma_ferramenta_ainda_acusam():
    """Rede: o conserto nao pode cegar a checagem pro caso que ela existe pra pegar."""
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = monta_mundo(Path(t))
        cmd = "${CLAUDE_PLUGIN_ROOT}/hooks/guard.sh"
        monta_cache(vivo, [("um", "Grep", cmd, NEGA), ("dois", "Grep", cmd, NEGA)])
        res = roda_conformance(vivo, cfg)
        check("dois plugins negando a MESMA ferramenta continuam sendo acusados",
              "hooks" in areas(res),
              str([d["o_que"] for d in res["desvios"]]))


def monta_scope_cop(raiz):
    """Fixture minima pro scope-cop.sh: juiz falso no PATH (o juiz real e um
    `claude -p`, caro e nao-deterministico), transcript com pedido de UI e um
    .tsx de verdade. Devolve (dir do bin falso, payload)."""
    binario = raiz / "bin"
    binario.mkdir(parents=True, exist_ok=True)
    juiz = binario / "claude"
    juiz.write_text('#!/bin/bash\n'
                    'echo \'{"verdict":"block","reason":"mexeu no container inteiro"}\'\n')
    juiz.chmod(0o755)
    transcript = raiz / "scope.jsonl"
    transcript.write_text(json.dumps(
        {"type": "user", "message": {"content": "muda a cor do botao do header"}}) + "\n")
    ui = raiz / "app.tsx"
    ui.write_text('export const App = () => <div className="header" />\n')
    payload = json.dumps({
        "session_id": "acordo-scope",
        "transcript_path": str(transcript),
        "tool_name": "Edit",
        "tool_input": {"file_path": str(ui),
                       "old_string": 'className="header"',
                       "new_string": 'className="header xl"'},
    })
    return str(binario), payload


def juiz_falso_visivel(bindir):
    """O juiz falso e um arquivo `claude` com shebang, marcado 755 pelo Python.

    NO WINDOWS ESSE chmod NAO CRIA BIT DE EXECUCAO — o sistema nao tem esse bit,
    e o `command -v claude` de dentro do hook nao acha nada. O hook entao faz o
    que deve (sem juiz, nao ha veredito: fail-open, nao bloqueia) e o teste lia
    isso como "o hook nao bloqueou", reprovando hook CERTO por fixture quebrada.
    Aqui a fixture se mede: pergunta ao mesmo bash que o hook usa se o juiz
    RODA. Falso => o caso pula declarando, em vez de reprovar.

    ⚠️ A pergunta era `command -v claude`, e ela mede a coisa ERRADA: o bash do
    Git para Windows ACHA o arquivo (o `-x` dele olha extensao e conteudo, nao o
    bit que o sistema nao tem) e devolve o caminho, entao a guarda dizia "da pra
    medir" — e na hora de EXECUTAR o mesmo arquivo o hook ficava sem veredito,
    reprovando os dois checks do ramo `deny` em toda esteira. Achar nao e rodar:
    o que decide agora e a SAIDA do juiz falso, que ele so produz executando.

    ⚠️ E o juiz falso e chamado pelo CAMINHO ABSOLUTO, nunca pelo nome. Pelo nome,
    a maquina de quem desenvolve — que TEM o `claude` de verdade no PATH — cairia
    no CLI real: uma chamada cara, lenta e nao-deterministica dentro da guarda que
    existe justamente para nao depender dele (medido: a suite travou em 2 min)."""
    b = bash_posix()
    if b is None:
        return False
    alvo = shlex.quote(os.path.join(bindir, "claude"))
    r = subprocess.run([b, "-c", f"{alvo} -p x 2>/dev/null"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
    return r.returncode == 0 and '"verdict"' in r.stdout


def roda_scope_cop(bindir, payload, home, config_dir, script=None, com_erro=False):
    """Devolve (stdout, returncode) — o rc importa porque hook AUSENTE tambem
    sai calado (bash 127) e sem ele o 'tem que calar' fica verde por acidente.
    `com_erro=True` devolve (stdout, rc, stderr): quando o hook sai calado, o
    MOTIVO nao esta no stdout — e sem ele a falha vira adivinhacao a 4 min por
    tentativa em runner que ninguem consegue abrir."""
    # O SEPARADOR DE PATH É DO SISTEMA, NÃO ':' CRAVADO. No Windows ele é ';', e
    # com dois-pontos o PATH inteiro vira uma entrada só de lixo — todo binário
    # some, inclusive o que este teste acabou de montar em `bindir`. Foi metade da
    # esteira vermelha de 2026-08-10 (a outra metade é o `bash` do WSL, abaixo).
    env = dict(os.environ, HOME=str(home), CLAUDE_CONFIG_DIR=str(config_dir),
               PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}")
    r = subprocess.run([bash_posix(), str(script or SCOPE_COP)], input=payload,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, start_new_session=True)
    if com_erro:
        return r.stdout.strip(), r.returncode, r.stderr.strip()
    return r.stdout.strip(), r.returncode


def trace_scope_cop(bindir, payload, home, config_dir):
    """As ultimas linhas do `bash -x` do hook — o ponto EXATO em que ele desistiu.

    Existe porque o Windows reprovava com "saida=" e mais nada: rc 0 e stdout vazio
    sao o contrato do fail-open, entao a mensagem de falha nao distinguia oito
    saidas diferentes. Sai so no caminho de falha, e cortado: o trace inteiro traz
    o payload e afogaria o log da esteira."""
    b = bash_posix()
    if b is None:
        return "(sem bash)"
    env = dict(os.environ, HOME=str(home), CLAUDE_CONFIG_DIR=str(config_dir),
               PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}")
    r = subprocess.run([b, "-x", str(SCOPE_COP)], input=payload, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=env, start_new_session=True)
    linhas = [ln for ln in r.stderr.strip().splitlines() if ln.strip()]
    return " ⏎ ".join(ln[:120] for ln in linhas[-12:]) or "(trace vazio)"


def teste_hook_ausente_nao_se_disfarca_de_hook_calado():
    """F-DELTA-4: 'gate desligado' e 'gate que nem rodou' precisam ser
    distinguiveis. O SCOPE_COP e montado por caminho relativo pra dentro de
    OUTRO plugin — se o arquivo sumir de lugar, o bash sai 127 com stdout
    vazio e o caso 'o hook tem que calar' fica VERDE por acidente. Silencio so
    prova obediencia junto com returncode 0."""
    # SEM BASH QUE RODE, ESTE CASO NÃO MEDE NADA — e dizer isso é mais honesto
    # que reprovar o hook. No Windows sem Git Bash o `bash` do PATH é o do WSL,
    # que responde em UTF-16 e chega como stdout vazio: o teste concluía "o hook
    # não bloqueou" sobre um hook que nunca chegou a rodar.
    if bash_posix() is None:
        print("  skip %s (nenhum bash funcional nesta máquina)" % "hook ausente x hook desligado")
        return
    with tempfile.TemporaryDirectory() as t:
        raiz = Path(t)
        bindir, payload = monta_scope_cop(raiz)
        fantasma = raiz / "hook-que-nao-existe.sh"
        saida, rc = roda_scope_cop(bindir, payload, raiz, raiz, script=fantasma)
        check("hook ausente cala igual a hook desligado", saida == "",
              f"saida={saida[:160]}")
        check("mas o returncode denuncia que ele nem rodou", rc != 0,
              f"rc={rc}")


def teste_scope_cop_e_conformance_olham_a_mesma_pasta():
    """Mesmo defeito do bypass.log, do outro lado: o scope-cop lia o modo em
    ~/.claude fixo enquanto o check_gates_enganosos varre **/*.mode sob
    CLAUDE_CONFIG_DIR. Com a env var setada, o gate que o auditor acusa nao e
    o gate que o hook obedece — e cada lado fica coerente sozinho."""
    # Mesma guarda do caso acima: sem bash que rode, o hook não chega a ser
    # exercitado e "não bloqueou" seria conclusão errada sobre hook certo.
    if bash_posix() is None:
        print("  skip scope-cop x conformance (nenhum bash funcional nesta máquina)")
        return
    with tempfile.TemporaryDirectory() as t:
        raiz = Path(t)
        vivo, cfg = monta_mundo(raiz)
        bindir, payload = monta_scope_cop(raiz)
        isca = raiz / "home-isca"          # HOME de mentira, sempre com o modo OPOSTO
        (isca / ".claude" / "guardrails").mkdir(parents=True)
        (vivo / "guardrails").mkdir(parents=True, exist_ok=True)

        # O caminho atravessa plugins (BOOTSTRAP.parent/guardrails): se o script
        # mudar de lugar, o resto do teste vira silencio verde.
        check("o scope-cop.sh esta onde o teste procura", SCOPE_COP.is_file(),
              f"nao achei {SCOPE_COP}")

        # A) 'off' onde o auditor le, 'deny' na isca → o hook tem que calar.
        (vivo / "guardrails" / "scope-cop.mode").write_text("off")
        (isca / ".claude" / "guardrails" / "scope-cop.mode").write_text("deny")
        saida, rc = roda_scope_cop(bindir, payload, isca, vivo)
        check("o hook obedece o modo que mora em CLAUDE_CONFIG_DIR",
              saida == "" and rc == 0, f"saida={saida[:160]} rc={rc}")

        res = roda_conformance(vivo, cfg)
        gate = [d for d in res["desvios"] if "scope-cop" in d["o_que"]]
        check("o conformance acusa o MESMO gate que o hook obedeceu", bool(gate),
              str([d["o_que"] for d in res["desvios"]]))

        # B) invertido: 'deny' onde o auditor le → bloqueia, e o rastro nasce la.
        # Este e o unico caso que precisa do JUIZ, e so ele pula quando a fixture
        # nao e enxergada (Windows): o caso A acima segue medindo, porque hook
        # calado com rc 0 nao depende de haver juiz.
        if not juiz_falso_visivel(bindir):
            print("  skip o ramo 'deny' (o juiz falso nao e executavel nesta maquina)")
            return
        (vivo / "guardrails" / "scope-cop.mode").write_text("deny")
        (isca / ".claude" / "guardrails" / "scope-cop.mode").write_text("off")
        saida, rc, erro = roda_scope_cop(bindir, payload, isca, vivo, com_erro=True)
        try:
            decisao = json.loads(saida).get("hookSpecificOutput", {}).get("permissionDecision", "")
        except ValueError:
            decisao = ""
        # O hook desiste calado em varios pontos (fail-open por desenho), e o rastro
        # de CADA um e o proprio log dele. Sem colar o log aqui, "saida=" vazio nao
        # distingue "leu o payload e nao julgou" de "nem leu o payload".
        log = vivo / "guardrails" / "scope-cop.log"
        rastro = log.read_text(encoding="utf-8", errors="replace").strip()[-300:] if log.exists() else "(log nao existe)"
        # Saida vazia + rc 0 + log inexistente = o hook desistiu ANTES de julgar, e
        # ha oito pontos de saida assim (por desenho, fail-open). Qual deles foi so
        # o proprio bash sabe dizer: com `-x` o trace nomeia a LINHA, e sem isso cada
        # hipotese custa uma rodada de esteira. So roda quando ja falhou.
        if decisao != "deny":
            rastro += " | trace=" + trace_scope_cop(bindir, payload, isca, vivo)
        check("com 'deny' em CLAUDE_CONFIG_DIR o hook bloqueia", decisao == "deny",
              f"saida={saida[:160]} rc={rc} stderr={erro[:200]} log={rastro}")
        check("o hook escreve o log DENTRO de CLAUDE_CONFIG_DIR",
              (vivo / "guardrails" / "scope-cop.log").is_file(),
              "log nao nasceu no config dir")
        check("nenhum estado vaza pro HOME quando a env var aponta noutro lugar",
              not (isca / ".claude" / "guardrails" / "scope-cop.log").exists(),
              "log vazou pro ~/.claude")


def teste_mode_homonimo_em_duas_pastas_e_acusado():
    """F-REV-2: o hook le SO o $CLAUDE_CONFIG_DIR/guardrails/scope-cop.mode. Um
    homonimo noutra pasta (o orfao de hooks/) e inerte — editar ele nao muda
    comportamento nenhum e nao avisa. O defeito e a EXISTENCIA do duplicado, nao
    o conteudo: por isso os dois aqui valem 'warn', valor que o check antigo (so
    'off') ignora de proposito, e o .mode sozinho em 'warn' segue sem desvio."""
    with tempfile.TemporaryDirectory() as t:
        raiz = Path(t)
        vivo, cfg = monta_mundo(raiz)
        (vivo / "guardrails").mkdir(parents=True, exist_ok=True)
        (vivo / "hooks").mkdir(parents=True, exist_ok=True)
        (vivo / "guardrails" / "scope-cop.mode").write_text("warn")

        res = roda_conformance(vivo, cfg)
        check("um .mode sozinho em 'warn' nao vira desvio",
              not [d for d in res["desvios"] if d["area"] == "gate"],
              str([d["o_que"] for d in res["desvios"]]))

        (vivo / "hooks" / "scope-cop.mode").write_text("warn")
        res = roda_conformance(vivo, cfg)
        dup = [d for d in res["desvios"] if d["area"] == "gate"]
        check("o homonimo em outra pasta e acusado mesmo os dois valendo 'warn'",
              bool(dup), str([d["o_que"] for d in res["desvios"]]))
        ev = dup[0]["evidencia"] if dup else ""
        check("a evidencia aponta qual e o vivo (o que o hook le)",
              f"{vivo / 'guardrails' / 'scope-cop.mode'} ← o hook LE este" in ev, ev)
        check("a evidencia aponta qual e o inerte",
              f"{vivo / 'hooks' / 'scope-cop.mode'} (inerte)" in ev, ev)


def teste_homonimo_fora_do_guardrails_nao_elege_vencedor():
    """F-REV-C: o rotulo '← o hook LE este' / '(inerte)' e o conserto que manda
    aposentar so valem quando UMA das copias mora em CLAUDE_DIR/guardrails/. Com
    dois homonimos noutras pastas, o codigo velho marcava AS DUAS de '(inerte)' e
    mandava consertar numa pasta que nem existe. Duplicidade segue sendo desvio;
    o que nao pode e eleger vencedor nem mandar aposentar um dono nao
    identificado."""
    with tempfile.TemporaryDirectory() as t:
        raiz = Path(t)
        vivo, cfg = monta_mundo(raiz)
        (vivo / "visualA").mkdir(parents=True, exist_ok=True)
        (vivo / "visualB").mkdir(parents=True, exist_ok=True)
        (vivo / "visualA" / "visual.mode").write_text("warn")
        (vivo / "visualB" / "visual.mode").write_text("warn")

        res = roda_conformance(vivo, cfg)
        dup = [d for d in res["desvios"] if d["area"] == "gate"]
        check("a duplicidade continua sendo acusada", bool(dup),
              str([d["o_que"] for d in res["desvios"]]))
        ev = dup[0]["evidencia"] if dup else ""
        conserto = dup[0]["conserto"] if dup else ""
        check("as duas copias sao nomeadas na evidencia",
              str(vivo / "visualA" / "visual.mode") in ev
              and str(vivo / "visualB" / "visual.mode") in ev, ev)
        check("nenhuma copia e eleita a que o hook le",
              "o hook LE este" not in ev, ev)
        check("nao rotula tudo de inerte", "(inerte)" not in ev, ev)
        check("nao manda aposentar dono nao identificado",
              "posent" not in conserto, conserto)
        check("diz que o dono nao foi identificado",
              "dono nao identificado" in conserto, conserto)
        check("nao manda consertar numa pasta que nem existe",
              str(vivo / "guardrails") not in conserto
              and not (vivo / "guardrails").exists(), conserto)


def teste_skill_declarada_e_nao_instalada_nao_e_desvio():
    """A lista de skills e RETRATO do dono do manifest, nao requisito. Numa maquina
    que nao e a dele, cobrar 'declarada mas nao instalada' seria uma acusacao por
    skill que ele nunca pediu — desvio permanente em quem nao usa ensina a ignorar
    o relatorio inteiro. A direcao que IMPORTA (skill que apareceu sem ser
    declarada) continua sendo cobrada."""
    with tempfile.TemporaryDirectory() as t:
        raiz = Path(t)
        vivo, cfg = monta_mundo(raiz)
        man = json.loads((cfg / "manifest.json").read_text())
        man["skills"] = {"permitidas": ["uma", "duas", "tres"]}
        (cfg / "manifest.json").write_text(json.dumps(man))

        # maquina limpa: nenhuma das 3 instalada
        res = roda_conformance(vivo, cfg)
        check("skill declarada e nao instalada NAO e desvio",
              "skills" not in areas(res),
              str([d["o_que"] for d in res["desvios"] if d["area"] == "skills"]))

        # mas skill que apareceu sem ser declarada continua sendo
        (vivo / "skills" / "nao-declarada").mkdir()
        res = roda_conformance(vivo, cfg)
        check("skill fora da lista continua sendo acusada", "skills" in areas(res))


def teste_dependencia_externa_de_plugin_ligado():
    """graphify-guard ligado + binario `graphify` fora do PATH -> acusa.
    E o mesmo mal do gate meio-ligado: o plugin instalado da a impressao de que a
    funcao existe. So cobra quando o plugin que PRECISA esta ligado."""
    with tempfile.TemporaryDirectory() as t:
        raiz = Path(t)
        vivo, cfg = monta_mundo(raiz)
        man = json.loads((cfg / "manifest.json").read_text())
        man["ferramentas_externas"] = {"itens": [
            {"comando": "binario-que-nao-existe-xyz", "pacote": "pkg",
             "instalar": "uv tool install pkg", "requerido_por": ["guarda"],
             "porque": "o guarda depende dele"}]}
        (cfg / "manifest.json").write_text(json.dumps(man))
        s = json.loads((vivo / "settings.json").read_text())

        # 1) o plugin que precisa esta DESLIGADO -> nao incomoda
        s["enabledPlugins"]["guarda@mkt"] = False
        (vivo / "settings.json").write_text(json.dumps(s))
        res = roda_conformance(vivo, cfg)
        check("plugin desligado nao cobra dependencia externa",
              "dependencia" not in areas(res),
              str([d["o_que"] for d in res["desvios"] if d["area"] == "dependencia"]))

        # 2) LIGADO e sem o binario -> acusa, com o comando de instalar
        s["enabledPlugins"]["guarda@mkt"] = True
        (vivo / "settings.json").write_text(json.dumps(s))
        res = roda_conformance(vivo, cfg)
        dep = [d for d in res["desvios"] if d["area"] == "dependencia"]
        check("plugin ligado sem o binario e acusado", bool(dep))
        check("o desvio traz o comando de instalar",
              bool(dep) and "uv tool install pkg" in dep[0]["conserto"],
              str(dep[:1]))


def monta_catalogo(vivo, raiz, nomes):
    """Marketplace 'pedro-plugins' de diretorio no registro vivo + o catalogo dele.

    Formato conferido na maquina: known_marketplaces.json aninha o "source"
    ({"source": {"source": "directory", "path": ...}}) e o catalogo e
    {"plugins": [{"name": ..., "version": ...}]}.
    """
    mkt = raiz / "marketplace-dir"
    (mkt / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (mkt / ".claude-plugin" / "marketplace.json").write_text(json.dumps({
        "name": "pedro-plugins",
        "plugins": [{"name": n, "source": f"./plugins/{n}", "version": "1.0.0"}
                    for n in nomes]}))
    (vivo / "plugins").mkdir(parents=True, exist_ok=True)
    (vivo / "plugins" / "known_marketplaces.json").write_text(json.dumps({
        "pedro-plugins": {"source": {"source": "directory", "path": str(mkt)},
                          "installLocation": str(mkt)}}))


def receita_pedro_plugins(cfg, nomes):
    """Troca o mundo minimo por um manifest com a entrada 'pedro-plugins'."""
    man = json.loads((cfg / "manifest.json").read_text())
    man["marketplaces"] = [{"name": "pedro-plugins",
                            "plugins": [{"name": n, "enabled": False} for n in nomes]}]
    (cfg / "manifest.json").write_text(json.dumps(man))


def teste_plugin_publicado_fora_da_receita():
    """F6.2: nada no bootstrap lia o marketplace.json, entao plugin que entrou no
    catalogo e nao entrou no manifest nunca chegava em maquina nenhuma — calado."""
    with tempfile.TemporaryDirectory() as t:
        raiz = Path(t)
        vivo, cfg = monta_mundo(raiz)
        receita_pedro_plugins(cfg, ["um", "dois"])
        monta_catalogo(vivo, raiz, ["um", "dois", "esquecido"])
        res = roda_conformance(vivo, cfg)
        cat = [d for d in res["desvios"] if d["area"] == "catalogo"]
        check("um plugin a mais no catalogo vira exatamente 1 desvio", len(cat) == 1,
              str([d["o_que"] for d in cat]))
        check("o desvio nomeia o plugin esquecido",
              bool(cat) and "esquecido" in cat[0]["o_que"], str(cat[:1]))
        check("e o conserto manda declarar no manifest",
              bool(cat) and cat[0]["conserto"] == "declare em config/manifest.json",
              str(cat[:1]))

        receita_pedro_plugins(cfg, ["um", "dois", "esquecido"])
        res = roda_conformance(vivo, cfg)
        check("catalogo igual a receita nao acusa nada",
              not [d for d in res["desvios"] if d["area"] == "catalogo"],
              str([d["o_que"] for d in res["desvios"] if d["area"] == "catalogo"]))


def teste_catalogo_ausente_nao_acusa():
    """Maquina sem o marketplace instalado nao e desvio: sem catalogo pra comparar,
    acusar seria acusar o vazio. Fail-open calado."""
    with tempfile.TemporaryDirectory() as t:
        raiz = Path(t)
        vivo, cfg = monta_mundo(raiz)
        receita_pedro_plugins(cfg, ["um", "dois"])
        res = roda_conformance(vivo, cfg)
        check("sem catalogo na maquina, zero desvio de catalogo",
              not [d for d in res["desvios"] if d["area"] == "catalogo"],
              str([d["o_que"] for d in res["desvios"] if d["area"] == "catalogo"]))


def _mundo_statusline(raiz, *, comando=None, forward=None, ligados=("context-guard", "claude-hud")):
    """Mundo minimo com a cadeia da statusLine montada a dedo."""
    vivo, cfg = monta_mundo(raiz)
    s = json.loads((vivo / "settings.json").read_text(encoding="utf-8"))
    for nome in ligados:
        s["enabledPlugins"]["%s@algum-marketplace" % nome] = True
    if comando is None:
        s.pop("statusLine", None)
    else:
        s["statusLine"] = {"type": "command", "command": comando}
    if forward is not None:
        s.setdefault("env", {})["CLAUDE_STATUSLINE_FORWARD"] = forward
    (vivo / "settings.json").write_text(json.dumps(s))
    return vivo, cfg


def _desvios_sl(res):
    return [d["o_que"] for d in res["desvios"] if d["area"] == "statusline"]


def teste_statusline_cadeia_inteira_nao_acusa():
    """Escritor no comando, renderizador no forward: a cadeia esta de pe, silencio."""
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = _mundo_statusline(
            Path(t),
            comando='bash ".../hooks/context-guard-writer.sh"',
            forward="node .../claude-hud/1.0.0/dist/index.js")
        res = roda_conformance(vivo, cfg)
        check("cadeia inteira nao vira desvio", not _desvios_sl(res), str(_desvios_sl(res)))
        check("e ela e reportada como conforme, na ordem",
              any(d["area"] == "statusline" and "context-guard → claude-hud" in d["o_que"]
                  for d in res["conforme"]),
              str([d["o_que"] for d in res["conforme"] if d["area"] == "statusline"]))


def teste_escritor_fora_da_cadeia_acusa():
    """O defeito real medido em 2026-08-02: statusLine so com o renderizador.

    A tela continua bonita — quem sumiu foi o elo que GRAVA dado pra outro consumir.
    E o sintoma nao aparece em lugar nenhum: nenhuma sessao real escreveu por 3 dias.
    """
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = _mundo_statusline(
            Path(t), comando="node .../claude-hud/1.0.0/dist/index.js")
        res = roda_conformance(vivo, cfg)
        d = _desvios_sl(res)
        check("escritor fora da cadeia vira desvio",
              any("context-guard" in x and "FORA" in x for x in d), str(d))
        check("o renderizador presente NAO vira desvio junto",
              not any("claude-hud" in x for x in d), str(d))


def teste_renderizador_fora_da_cadeia_acusa():
    """Simetrico: hud ligado, cadeia so com o escritor e nada desenhando."""
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = _mundo_statusline(
            Path(t), comando='bash ".../hooks/context-guard-writer.sh"')
        res = roda_conformance(vivo, cfg)
        d = _desvios_sl(res)
        check("renderizador fora da cadeia vira desvio",
              any("claude-hud" in x and "FORA" in x for x in d), str(d))


def teste_elo_no_forward_conta_como_dentro():
    """O elo pode morar no forward, e isso e o arranjo NORMAL do renderizador.

    Procurar so em statusLine.command acusaria o hud toda vez que ele fosse o forward —
    falso-positivo que ensina o dono a ignorar o check.
    """
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = _mundo_statusline(
            Path(t),
            comando='bash ".../hooks/context-guard-writer.sh"',
            forward="node .../claude-hud/9.9.9/dist/index.js")
        res = roda_conformance(vivo, cfg)
        check("elo que mora no forward nao e acusado", not _desvios_sl(res), str(_desvios_sl(res)))


def teste_sem_statusline_com_plugin_ligado_acusa():
    """Sem statusLine nenhuma e escolha legitima — mas nao com os plugins dela ligados."""
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = _mundo_statusline(Path(t), comando=None)
        res = roda_conformance(vivo, cfg)
        check("plugin de statusline ligado sem statusLine acusa",
              any("sem statusLine configurada" in x for x in _desvios_sl(res)),
              str(_desvios_sl(res)))


def teste_plugin_desligado_nao_acusa():
    """Fail-open na direcao certa: quem nao esta ligado nao e cobrado."""
    with tempfile.TemporaryDirectory() as t:
        vivo, cfg = _mundo_statusline(
            Path(t), comando="echo oi", ligados=())
        res = roda_conformance(vivo, cfg)
        check("nenhum elo ligado, nenhum desvio", not _desvios_sl(res), str(_desvios_sl(res)))


if __name__ == "__main__":
    print("test_conformance.py")
    for fn in (teste_mundo_conforme, teste_plugin_religado_na_mao,
               teste_plugin_ausente_manda_instalar_e_nao_habilitar,
               teste_plugin_instalado_porem_desligado_pede_enable,
               teste_output_style_nao_setado, teste_teto_duplicado,
               teste_skill_nao_declarada,
               teste_redirecionamento_nao_vira_script_fantasma,
               teste_variavel_sem_chaves_tambem_resolve,
               teste_aspa_simples_no_comando_resolve_como_o_shell_resolveria,
               teste_aspas_desbalanceadas_nao_derrubam_o_conformance,
               teste_token_absoluto_fora_da_raiz_nao_decide,
               teste_nenhum_token_resolve_conta_como_disputante,
               teste_caminho_relativo_sem_a_variavel_nao_vira_alvo,
               teste_script_na_raiz_do_plugin_tambem_resolve,
               teste_dois_denies_na_mesma_ferramenta_ainda_acusam,
               teste_hook_ausente_nao_se_disfarca_de_hook_calado,
               teste_scope_cop_e_conformance_olham_a_mesma_pasta,
               teste_mode_homonimo_em_duas_pastas_e_acusado,
               teste_homonimo_fora_do_guardrails_nao_elege_vencedor,
               teste_dependencia_externa_de_plugin_ligado,
               teste_skill_declarada_e_nao_instalada_nao_e_desvio,
               teste_plugin_publicado_fora_da_receita,
               teste_catalogo_ausente_nao_acusa,
               teste_statusline_cadeia_inteira_nao_acusa,
               teste_escritor_fora_da_cadeia_acusa,
               teste_renderizador_fora_da_cadeia_acusa,
               teste_elo_no_forward_conta_como_dentro,
               teste_sem_statusline_com_plugin_ligado_acusa,
               teste_plugin_desligado_nao_acusa):
        fn()
    print(f"\n{ok} ok · {falhas} FAIL")
    sys.exit(1 if falhas else 0)
