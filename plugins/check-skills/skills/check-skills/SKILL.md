---
name: check-skills
description: Confere a saúde do que está instalado na máquina — nome de skill repetido, hooks de origens diferentes no mesmo evento, descrições que disputam o mesmo assunto, versões paradas no cache, processo que a skill abre e não fecha, citação de plugin irmão que não está instalado, e as contradições de instrução que nenhuma varredura pega. Use quando o usuário disser "/check-skills", "meus plugins brigam?", "tem conflito entre as skills?", "instalei um plugin novo, confere aí", "por que ele escolheu a skill errada?", "o fim de turno está travando", "a máquina está cheia de processo aberto". Dispare também DEPOIS de instalar ou atualizar plugin de terceiro, e antes de publicar skill nova — é aí que o atropelo nasce. A varredura mecânica é do programa; o julgamento das contradições é seu, e ele exige LER as descrições.
---

# Skill: /check-skills

Dois plugins nunca se apresentam um ao outro. Cada um foi escrito sozinho, e o que
acontece quando eles convivem não está escrito em lugar nenhum — nem no `plugin list`,
que diz o que existe, nem no `plugin details`, que olha um de cada vez.

Esta skill responde a pergunta que falta: **o que se atropela?**

## As sete naturezas de atropelo, e por que elas são diferentes

Confundir as sete é o erro que faz o relatório virar ruído. Cada uma tem sintoma
próprio, e só as seis primeiras dão para varrer.

| # | Natureza | O sintoma que o usuário sente |
|---|---|---|
| 1 | **Nome repetido** | ele digita `/setup` e não sabe qual das três responde |
| 2 | **Evento disputado** | o fim de turno trava, e nada diz qual dos doze hooks travou |
| 3 | **Gatilho disputado** | ele pede "revisa isso" e vem a skill errada |
| 4 | **Cache inchado** | ele conserta um arquivo e o conserto não aparece |
| 5 | **Vazamento de processo** | a máquina fica lenta e cheia de processo que ninguém abriu |
| 6 | **Irmão ausente** | ele instalou uma skill sozinha e parte dela não faz nada, sem erro |
| 7 | **Instrução contraditória** | uma skill manda o oposto da outra, e as duas estão certas |

**A sétima é a única que nenhum programa acha.** As seis primeiras são forma; a sétima é
conteúdo, e mora nas descrições.

**A quinta nasceu de um caso medido em 2026-08-08:** uma máquina acumulou **2125
processos `python3` órfãos**, e nenhuma ferramenta ligava aquilo a quem os tinha aberto.
O `plugin list` não vê processo, e o `ps` não vê skill.

## 1 · A varredura mecânica

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/varredura.py"          # relatório humano
python3 "${CLAUDE_PLUGIN_ROOT}/lib/varredura.py" --json   # para consumir
```

Ele lê `~/.claude/plugins/cache/`, e **só a versão mais alta de cada plugin** — que é a
que roda. Ler todas conta a mesma colisão uma vez por versão, e num cache real isso são
dezessete repetições do mesmo achado.

O que cada balde devolve:

- **`nome_repetido`** — skills com nome idêntico, com o plugin de cada uma.
- **`evento_disputado`** — só quando os hooks vêm de **marketplaces diferentes**. Dois
  hooks seus no mesmo evento é desenho, não conflito. Dentro dele, `barram` é a lista
  dos que podem **recusar** — o subconjunto que trava de verdade.
- **`gatilho_disputado`** — assuntos que mais de um marketplace reivindica na descrição.
  A busca é por **palavra inteira**: sem isso `ui` casa dentro de *constrUI* e o
  relatório sai com dezenas de falsos positivos.
- **`cache_inchado`** — versões paradas no disco, que confundem quem for ler o código.
- **`vazamento_codigo`** — o defeito **antes de rodar**, no código de toda skill
  instalada: `python3` disparado sem fechar a entrada (o filho herda o terminal e espera
  para sempre) ou sem grupo próprio (o teto mata o filho e o **neto** sobrevive), `node`
  com `stdio: 'inherit'`, `shell` com `nohup`/`disown`. Isenção: `vaza-ok: <motivo>` na
  linha de cima.
- **`irmao_ausente`** — a skill instalada cita um plugin **irmão** (`resolve-plugin.sh
  <nome>`, `${CLAUDE_PLUGIN_ROOT}/../<nome>`, `plugins/<nome>/lib/…`) que **não está no
  cache desta máquina**. O cobrador do repositório vê o texto; só aqui se sabe se resolve.
  Quando não resolve nada estoura — o resolvedor devolve vazio e o hook sai calado —, então
  o achado nomeia as duas pontas: quem depende do ausente e **que arquivo fica mudo**.
  Bancada e `fixtures/` ficam de fora: elas citam plugin de mentira de propósito.
- **`vazamento_vivo`** — o que **já vazou**, ligado ao dono: processo órfão (pai `1`)
  cujo comando carrega o caminho de instalação de um plugin. Processo com pai vivo NÃO
  entra — tem dono, e encerrá-lo mataria trabalho em curso.

- **`nome_de_fabrica`** — a skill se chama como um **comando do próprio Claude Code**:
  quem digita o nome recebe o harness, e a skill nunca é chamada. A lista de fábrica não
  está escrita dentro do cobrador — mora em `lib/comandos-de-fabrica.txt`, com a fonte e
  a data da extração; lista escrita a mão no código envelhece sem ninguém ver. Disputa já
  **decidida** ganha `isento <nome>: <motivo>` no mesmo arquivo e sai no relatório com o
  motivo colado; sem motivo escrito a isenção não conta, e o achado volta como descuido.

**As duas metades da quinta lente não se substituem.** No caso de 2026-08-08 o código
tinha 155 pontos defeituosos *e* 2125 órfãos de pé: só o estático não diria que a
máquina já estava cheia, e só o dinâmico não diria onde consertar.

Bancada: `python3 "${CLAUDE_PLUGIN_ROOT}/lib/test_varredura.py"`.

## 2 · A sétima natureza — a que você lê, porque nenhum programa lê

Contradição de instrução não tem forma detectável: as duas skills estão bem escritas,
e o conflito só aparece quando as duas entram no mesmo prompt. **Leia as descrições**
dos grupos que o `gatilho_disputado` devolveu, e procure estes quatro padrões.

### (a) Uma manda fazer, a outra manda não fazer

O caso medido neste marketplace, e ele é literal:

```
superpowers/subagent-driven-development
  "Use when executing implementation plans with independent tasks in the current session"
  → o método dela É disparar sub-agentes

pedro-plugins/sprint · SKILL.md:46
  "o hook pretooluse-motor-arma.sh NEGA todo disparo de sub-agente e manda rodar o Workflow"
  → com a missão de pé, o método da outra é mecanicamente impossível
```

As duas descrevem "executar um plano com trabalho independente". Com a missão armada,
seguir a primeira devolve recusa; sem ela, as duas competem pelo mesmo pedido.

### (b) Uma se declara obrigatória

Skill que diz **MUST**, **SEMPRE**, **ANTES DE QUALQUER COISA** ou **inegociável**
compete com toda skill do mesmo assunto — e vence por tom, não por adequação.
Procure o superlativo na descrição:

```bash
grep -l "MUST\|ABSOLUTELY\|SEMPRE\|INEGOCIÁVEL\|obrigatóri" \
  ~/.claude/plugins/cache/*/*/*/skills/*/SKILL.md | head
```

Quando duas se declaram obrigatórias para o mesmo momento, **a que estiver mais acima no
prompt ganha** — e essa ordem não é sua.

### (c) Duas cobrem o mesmo assunto com nomes que não se parecem

O nome esconde a sobreposição. `/fallow` (código morto), `/ponytail-review`
(over-engineering) e `/simplify` (reuso e simplificação) fazem coisas vizinhas com três
vocabulários. O usuário pede "limpa isso" e a escolha vira sorteio.

**Régua:** se você não consegue escrever, numa linha, o que decide entre as duas — o
usuário também não consegue, e a descrição precisa dizer o que **NÃO** é dela.

### (d) A instrução do harness contradiz a skill

O prompt de sistema da sessão também dá ordens, e elas ganham da skill. Se a sessão diz
*"não dispare agente sem o usuário pedir"* e a skill manda disparar, a skill é
inexecutável naquela sessão — e o modelo obedece a uma, calado.

## 3 · O que fazer com cada achado

Achado não é defeito. A saída é declarar, não necessariamente consertar.

| Achado | O conserto que costuma valer |
|---|---|
| nome repetido | renomear pelo plugin (`/bootstrap-setup`), ou um roteador único |
| evento disputado, sem ninguém barrando | nada — coexistem |
| evento disputado, dois ou mais barram | ler os dois e decidir a ordem; um pode virar aviso |
| gatilho disputado | acrescentar à descrição o que ela **não** faz, e apontar a vizinha |
| cache inchado | `claude plugin update`, e limpar o cache velho |
| nome de fábrica, sem isenção | renomear a skill, ou declarar a isenção com o motivo escrito |
| irmão ausente | instalar o irmão, ou o autor trocar a travessia por degradação declarada |
| instrução contraditória | uma das duas ganha um kill-switch, ou some da máquina |

⚠️ **Não conserte plugin de terceiro editando o cache** — ele é reescrito no próximo
update, e o conserto some sem avisar. O que dá para fazer é desinstalar, desligar por
env var, ou pedir ao autor.

## 4 · A entrega

O relatório sai como página no browser quando a skill de apresentação visual estiver
instalada; sem ela, sai em texto — a informação é a mesma, só a forma degrada.

**A prova vai junto, sempre:** o nome do arquivo e a linha de cada descrição citada. Um
conflito relatado sem as duas frases lado a lado é opinião, e opinião sobre a máquina de
outra pessoa não se confere.

## 5 · Quando rodar

- Depois de **instalar ou atualizar** plugin de terceiro — é quando o atropelo nasce.
- Antes de **publicar skill nova** — para ela nascer sabendo de quem ela encosta.
- Quando o usuário disser que **a skill errada respondeu**, ou que o **fim de turno travou**.
- Nunca em toda sessão: é conferência de mudança, não vigia contínuo.
