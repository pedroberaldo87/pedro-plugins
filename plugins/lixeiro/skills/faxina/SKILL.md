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

### 1. Levante o que está de pé — agrupado, no terminal

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/lixeiro.py" resumo --idade-min 300
```

Sai uma linha por **família** — processos idênticos (mesmo comando, mesma classe, mesma
procedência) contam como uma decisão só, com a contagem (`15×`), a soma da memória própria,
o peso da maior árvore, a idade do mais velho e a lista de pids. Numa máquina com centenas
de processos, isso é a diferença entre vinte linhas e vinte telas.

Precisa do dado cru (para montar página ou filtrar)? O mesmo inventário em JSON:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/lixeiro.py" inventario --idade-min 300
```

Devolve um JSON por processo com `pid`, `cmd`, `rss_mb`, `arvore_mb`, `idade_min`, `cpu_s`,
`classe` e `procedencia`. O `--idade-min` é em segundos e corta o ruído: processo
recém-nascido não é lixo.

A `classe` tem quatro valores. `efemero` e `servico` são o que o motor reconhece pelo
comando; `intocavel` é máquina virtual, contêiner e serviço do próprio programa, que aparece
só para o usuário saber que está lá. O quarto é `sem classe conhecida`: **o programa que
ninguém reconhece**, que entra na lista dizendo que não se sabe o que é, em vez de sumir dela.

A `procedencia` diz de onde veio a informação, e o que interessa é a faixa nova:

- `anotado` — a sessão registrou a abertura dele. É a única faixa que o lixeiro automático colhe.
- `órfão — rascunho de sessão que não existe mais` — tem classe, mas o dono morreu.
- `sem dono conhecido` — tem classe e nenhuma anotação o explica.
- `sem anotação — achado pela varredura` — **a faixa dos suspeitos**: processo de vida longa
  que nenhuma anotação explica e que a varredura achou por prova minerada (linhagem, pasta de
  trabalho, pai sumido ou rascunho morto), nunca por nome de programa. Vem com `classe`
  `suspeito` ou `sem classe conhecida`, e com um campo a mais, `pista`, que é a frase de por
  que ele foi parar na lista — mostre a pista junto, senão o usuário não tem como julgar.
  Esses só entram acima de `--idade-suspeito` (1 h por padrão): suspeito novo é trabalho em curso.

Essa faixa é o ponto da faxina. O lixeiro automático nunca a toca; se ela não for mostrada
aqui, ninguém vê o que ficou de pé sem dono.

Nada é encerrado por nenhum dos dois. Eles só leem.

### 2. Traga o contexto de memória

O agrupamento por família já veio pronto do passo 1. Falta o que o usuário precisa para
decidir se vale a pena encerrar:

```bash
# quanto a máquina ainda tem                       (macOS)
vm_stat | awk '/page size/{ps=$8} /Pages free/{f=$3} /Pages inactive/{i=$3} \
  END{printf "livre+inativa: %.1f GB\n", (f+i)*4096/1073741824}'
# quanto a máquina ainda tem                       (Linux)
free -m 2>/dev/null | awk '/Mem:/{printf "livre: %.1f GB\n", $7/1024}'
```

Se duas famílias forem do mesmo projeto (a pasta que aparece no comando), diga isso — dois
servidores do mesmo projeto em portas diferentes é o padrão mais comum, e ver isso junto
muda a decisão.

### 3. Mostre no terminal e deixe o usuário marcar

**O terminal é o caminho padrão.** Cole a saída do passo 1 como ela saiu — ela já é a lista
que o usuário precisa ver — e acrescente, por família, o que aquilo é em linguagem humana.
Depois pergunte com uma única `AskUserQuestion` cujas opções carreguem as famílias concretas
no `preview`: a resposta é por família, não por processo.

**Os intocáveis aparecem na lista, marcados como tal, e sem opção de encerrar.** Máquina
virtual, serviço de contêiner e os serviços do próprio programa são mostrados para o usuário
saber que estão lá, nunca para serem encerrados por aqui.

**A página é sob demanda.** Só monte HTML quando o usuário pedir para ver no navegador (ou
quando ele quiser marcar processo a processo dentro de uma família grande). Aí sim invoque a
skill **`visual`** (Skill tool, `skill: "visual"`), alimentada pelo JSON do `inventario`, com
um **item revisável por família**, rótulos `["✓ Encerrar", "✏️ Deixar", "✗ Nunca mais"]`, e a
saída crua do inventário num bloco de evidência. Com centenas de processos a página custa
caro para dizer o que já coube em vinte linhas — por isso ela se pede, não se impõe.

### 4. Encerre só o que foi marcado

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/lixeiro.py" encerra 41633 41835 75831
```

Os pids saem na linha `pids:` de cada família. Família grande vem cortada em oito, com
`… (+N)` — os que faltam estão no JSON do `inventario`, um objeto por processo.

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
