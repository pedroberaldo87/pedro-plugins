---
name: faxina
description: Use quando o usuário disser "/faxina", "faz uma faxina", "limpa os processos", "o que está aberto aí", "tá pesado, vê o que dá pra fechar", ou quando quiser encerrar servidores, suítes e outros processos de desenvolvimento que ficaram de pé ocupando memória. É o irmão MANUAL do lixeiro automático — o lixeiro colhe sozinho só o que a sessão anotou ter aberto; a faxina mostra TUDO que está de pé, com ou sem procedência, e encerra apenas o que o usuário marcar. Use também quando um aviso de fim de turno mencionar processos parados.
---

# /faxina — a limpeza que você comanda

O lixeiro automático colhe sozinho, mas só o que **esta sessão anotou ter aberto**. Sobra
tudo que nasceu antes do mecanismo existir, o que outra ferramenta abriu, e o que o próprio
usuário subiu à mão. Essa faixa nunca é encerrada sozinha — é o que a faxina resolve.

**A regra que manda:** aqui você não decide o que morre. Você **mostra** e o usuário
escolhe. Um processo encerrado sem ele mandar é trabalho perdido que ninguém pediu.

## O passo a passo

### 1. Levante o que está de pé

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/lixeiro.py" inventario --idade-min 300
```

Devolve um JSON por processo com `pid`, `cmd`, `rss_mb`, `idade_min`, `cpu_s`, `classe`
(`efemero` · `servico` · `intocavel`) e `procedencia` (`anotado` ou `sem dono conhecido`).
O `--idade-min` é em segundos e corta o ruído: processo recém-nascido não é lixo.

Nada é encerrado por este comando. Ele só lê.

### 2. Some, agrupe e traga o contexto de memória

Antes de mostrar, junte o que o usuário precisa para decidir:

```bash
# quanto a máquina ainda tem                       (macOS)
vm_stat | awk '/page size/{ps=$8} /Pages free/{f=$3} /Pages inactive/{i=$3} \
  END{printf "livre+inativa: %.1f GB\n", (f+i)*4096/1073741824}'
# quanto a máquina ainda tem                       (Linux)
free -m 2>/dev/null | awk '/Mem:/{printf "livre: %.1f GB\n", $7/1024}'
```

Agrupe por projeto (a pasta que aparece no comando) — dois servidores do mesmo projeto em
portas diferentes é o padrão mais comum, e ver isso junto muda a decisão.

### 3. Mostre no navegador e deixe o usuário marcar

Invoque a skill **`visual`** (Skill tool, `skill: "visual"`) e monte a página com um
**item revisável por processo**, rótulos `["✓ Encerrar", "✏️ Deixar", "✗ Nunca mais"]`.

Cada item traz, no corpo: o que o processo é em linguagem humana, há quanto tempo está de
pé, quanta memória ocupa, de que pasta veio, e se alguém anotou tê-lo aberto. A saída crua
do inventário vai num bloco de evidência — o usuário tem que ver a mesma lista que você viu.

**Os intocáveis aparecem na página, marcados como tal, e sem controle de veredito.** Máquina
virtual, serviço de contêiner e os serviços do próprio programa são mostrados para o usuário
saber que estão lá, nunca para serem encerrados por aqui.

Sem a skill `visual` disponível: liste no terminal, agrupado por projeto, e pergunte com uma
única `AskUserQuestion` cujas opções carreguem a lista concreta no `preview`.

### 4. Encerre só o que foi marcado

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/lixeiro.py" encerra 41633 41835 75831
```

Pede para terminar, espera três segundos, e só então força. Devolve JSON do que morreu, e
grava tudo em `~/.claude/lixeiro/colhido.jsonl` para auditoria. As travas continuam valendo
mesmo aqui: ancestral do próprio processo e intocável são recusados em silêncio, mesmo que
o número tenha sido passado.

Para ver o que aconteceria sem encerrar nada, acrescente `--dry-run`.

### 5. Diga o que foi liberado

Uma linha, com a soma real:

```
🧹 Encerrei 4 processos e liberei 231 MB.
```

Se algum sobreviveu (recusado por trava ou por já ter morrido), diga qual e por quê — nunca
declare um número que não corresponde ao que aconteceu.

## O que a faxina NÃO faz

- **Não encerra nada sem escolha explícita.** Nem "os óbvios", nem "os muito velhos".
- **Não toca em máquina virtual nem em serviço de contêiner.** Eles guardam estado, sobem
  devagar e costumam servir a outros trabalhos abertos.
- **Não mata por nome de programa.** A lista de processos sob `node` numa máquina de
  desenvolvimento inclui o próprio programa que está rodando esta conversa.

## O irmão automático

O plugin `lixeiro` traz quatro hooks que trabalham sozinhos, sobre o mesmo motor:

- **Ao fim de cada comando** anota o que abriu processo — comando, pasta, hora, sessão.
- **Ao fim de cada turno** encerra suíte e compilação que ficaram penduradas, e servidor
  cuja CPU não subiu desde o turno anterior; servidor em uso sobrevive.
- **Ao fim da sessão** encerra tudo que aquela sessão anotou.
- **Na abertura** recolhe o que sessões mortas deixaram de pé.

Desligar tudo: `LIXEIRO=0`. Só a coleta do turno: `LIXEIRO_TURNO=0`. Só a varredura de
órfãos: `LIXEIRO_ORFAOS=0`. Só o aviso: `LIXEIRO_AVISO=0`. Teto do aviso:
`LIXEIRO_TETO_N` (default 4) e `LIXEIRO_TETO_MB` (default 400).
