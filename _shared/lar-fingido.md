# Contrato do lar fingido — como uma suíte troca o "lar" do processo que ela roda

Suíte que roda um hook ou um bloco de skill precisa que ele escreva num lar de
mentira, nunca no lar de verdade de quem está rodando. Este é o único lugar onde
está dito **como** se finge o lar; quem precisa da regra aponta pra cá e usa a
receita, não reescreve o pedaço.

## O defeito que a receita existe pra impedir

Trocar só `HOME` finge o lar no macOS e no Linux — e **não finge no Windows**. Lá
o `expanduser` do Python decide o lar nesta ordem:

1. `USERPROFILE`
2. `HOMEDRIVE` + `HOMEPATH`
3. `HOME`

Ou seja: com `USERPROFILE` intacto, o filho ignora o `HOME` fingido e escreve no
lar REAL da máquina. O teste continua verde (ele não olha onde o arquivo caiu),
e o estado do dono é sujado pela suíte. As quatro variáveis andam juntas ou não
andam.

## A receita

| Onde | Arquivo | Como se usa |
|---|---|---|
| Python | `lar_fingido.py` | `env = ambiente(lar, CLAUDE_CONFIG_DIR=…)` → passa em `subprocess.run(..., env=env)` |
| bash | `lib-lar-fingido.sh` | `lar_fingido "$LAR" bash "$HOOK"` (roda um comando) · `lar_fingido_exporta "$LAR"` (vale do ponto em diante) |

As duas põem o mesmo conjunto: `HOME`, `USERPROFILE`, `HOMEDRIVE=""` e
`HOMEPATH`. O resto do ambiente do caso (`CLAUDE_CONFIG_DIR`, `PATH`, stubs) é
do chamador — a receita finge o lar e mais nada.

**O lar fingido nasce FORA do projeto de teste.** A cascata de `resolve-dir.sh`
para ao chegar no lar; com o lar dentro do sandbox do projeto, a busca por
marcador morre cedo e o hook cai no caminho errado (foi o defeito de
`hook_contract.py`, que hoje cria `sandbox/lar` ao lado de `sandbox/projeto`).

## Quem cobra

`_shared/test_lar_fingido.py` — roda com as demais suítes de `_shared/` na
esteira e no gate de commit. Ele confere os três arquivos deste contrato (prosa,
Python, bash) e varre as suítes atrás de quem finge o lar à mão: linha que
atribui `HOME=`, `USERPROFILE=` ou `HOMEPATH=` fora da receita reprova. Caso
legítimo isenta a linha com `lar-fingido: ok <motivo>`.
