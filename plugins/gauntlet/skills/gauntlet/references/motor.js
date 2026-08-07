// motor.js — o laço do gauntlet, como script determinístico da tool Workflow.
//
// A falha que este arquivo existe para tornar impossível: uma sessão real lançou sete
// construtores prometendo um juiz em cada briefing, lançou zero juízes, e ninguém
// percebeu — porque o spawn do juiz era um evento SEM GATILHO, e o estado default do
// sistema ("nenhum juiz existe") é indistinguível de "tudo aprovado".
//
// A correção é estrutural, não disciplinar: aqui o juiz é o `await` seguinte ao do
// construtor. Não existe caminho da entrega ao fecho que o pule, porque quem lança não
// é quem orquestra — é este script.
//
// A skill passa este arquivo à tool Workflow. O bloco de esforço por etapa entra como
// constante literal, gerado do contrato compartilhado — nunca lido de args em tempo de
// execução, porque esse canal já falhou e o valor chegou indefinido.

export const meta = {
  name: 'gauntlet-engine',
  description: 'Constrói e julga peça a peça contra um alvo real, e nada se julga sozinho',
  phases: [
    { title: 'Reconhecer' },
    { title: 'Decompor' },
    { title: 'Construir' },
    { title: 'Julgar' },
    { title: 'Fechar' },
  ],
}

// gerado do contrato de esforço por etapa — não digite à mão
const T = {
  decompose: { effort: 'high' },
  coordinate: { effort: 'medium' },
  executor: { effort: 'medium' },
  mechanical: { effort: 'low' },
  diagnose: { effort: 'medium' },
  finalize: { effort: 'medium' },
}
const MODEL = 'opus'

// O parâmetro pode chegar como texto em vez de objeto; quando isso aconteceu noutro
// motor, todo campo lido virou indefinido e ele morreu na primeira volta sem dizer
// por quê. Converte ANTES de usar, e o resto do script só fala com ARGS.
const ARGS = typeof args === 'string' ? JSON.parse(args) : args
const MISSAO = ARGS.missao
const RITO = ARGS.rito || {}
const TETO_RODADAS = ARGS.tetoRodadas || 4
const TETO_GASTO = ARGS.tetoGasto || null
const TETO_PECAS = ARGS.tetoPecas || 8
const CHECK = `python3 "${ARGS.pluginRoot}/lib/fecho_check.py"`

const gastoInicial = budget.spent()
const gasto = () => budget.spent() - gastoInicial

// ─────────────────────────────────────────────────────────────────────────────
// Os esquemas. É o que torna os gates determinísticos: o script lê campo, não texto.
// ─────────────────────────────────────────────────────────────────────────────

const EIXOS = {
  type: 'object', additionalProperties: false, required: ['eixos'],
  properties: {
    eixos: { type: 'array', minItems: 1, items: {
      type: 'object', additionalProperties: false,
      required: ['nome', 'gesto', 'registro'],
      properties: { nome: { type: 'string' }, gesto: { type: 'string' },
                    registro: { type: 'string' }, porque: { type: 'string' } } } },
  },
}

const DECOMP = {
  type: 'object', additionalProperties: false, required: ['pecas'],
  properties: {
    pecas: { type: 'array', minItems: 1, items: {
      type: 'object', additionalProperties: false,
      required: ['id', 'eixos', 'arquivos', 'gesto'],
      properties: {
        id: { type: 'string' },
        desc: { type: 'string' },
        eixos: { type: 'array', minItems: 1, items: { type: 'string' } },
        arquivos: { type: 'array', minItems: 1, items: { type: 'string' } },
        gesto: { type: 'string' },
        exploratoria: { type: 'boolean' },
      } } },
    eixos_do_diretor: { type: 'array', items: { type: 'string' } },
  },
}

const ENTREGA = {
  type: 'object', additionalProperties: false,
  required: ['peca', 'rodada', 'resumo', 'artefatos'],
  properties: {
    peca: { type: 'string' }, rodada: { type: 'number' }, resumo: { type: 'string' },
    artefatos: { type: 'array', minItems: 1, items: {
      type: 'object', additionalProperties: false, required: ['caminho', 'marca'],
      properties: { caminho: { type: 'string' }, marca: { type: 'string' } } } },
    descartes: { type: 'array', items: {
      type: 'object', additionalProperties: false, required: ['o_que', 'visto_na_tela'],
      properties: { o_que: { type: 'string' }, visto_na_tela: { type: 'string' } } } },
  },
}

const VEREDITO = {
  type: 'object', additionalProperties: false,
  required: ['peca', 'rodada', 'status', 'entrega', 'registros'],
  properties: {
    peca: { type: 'string' }, rodada: { type: 'number' },
    status: { type: 'string', enum: ['aprovado', 'reprovado', 'marginal'] },
    entrega: { type: 'string' },
    registros: { type: 'object', additionalProperties: false, required: ['nosso', 'alvo'],
                 properties: { nosso: { type: 'string' }, alvo: { type: 'string' } } },
    eixo: { type: 'string' }, gap: { type: 'string' },
    eixo_novo: { type: 'object', additionalProperties: false,
                 required: ['nome', 'gesto', 'registro'],
                 properties: { nome: { type: 'string' }, gesto: { type: 'string' },
                               registro: { type: 'string' } } },
  },
}

const DIRETOR = {
  type: 'object', additionalProperties: false, required: ['status', 'viu'],
  properties: {
    status: { type: 'string', enum: ['aprovado', 'reprovado'] },
    viu: { type: 'object', additionalProperties: { type: 'string' } },
    gap: { type: 'string' },
  },
}

// ─────────────────────────────────────────────────────────────────────────────

const LEIA = `
Leia estes três antes de qualquer coisa, e leia inteiros:
  ${MISSAO}/rito.json          o que está congelado, o que está liberado, o material
  ${MISSAO}/recon/eixos.json   os eixos contra os quais tudo é medido
  ${MISSAO}/vetos.jsonl        o que o dono já matou — não volte com nada disso
`

const reconPrompt = () => `
Você é o RECONHECIMENTO. A nossa obra ainda não existe, e você não vai construir nada.

Vá ao alvo e diga o que o faz ser bom, item a item. Cada item é um EIXO, e cada eixo tem
três partes obrigatórias: o nome da qualidade · o gesto que a expõe · o registro que a prova.

Os alvos: ${JSON.stringify(RITO.alvos)}
A sonda:  ${JSON.stringify(RITO.sonda)}

Execute a sonda NO ALVO — rode o comando de preparar, faça os gestos, e produza os
registros com o comando de registrar. Grave-os em ${MISSAO}/recon/registros/ e cite o
caminho de cada um no eixo que ele prova.

Eixo sem registro no disco não vale: ele é o que transforma "melhor" de adjetivo em
comparação. E é contra estes eixos que TODAS as rodadas serão medidas, então erre por
excesso de especificidade: "resposta ao toque" serve; "qualidade geral" não.

Grave a lista em ${MISSAO}/recon/eixos.json no formato { "eixos": [...] }.
`

const decomporPrompt = ({ eixos, feedback }) => `
Você é o DECOMPOSITOR. Quebre o objetivo em peças julgáveis SEPARADAMENTE.
${LEIA}
Objetivo: ${RITO.objetivo}
Eixos disponíveis: ${eixos.map(e => e.nome).join(' · ')}

Peça julgável NÃO é seção nem tela — isso é unidade de layout, e foi o critério errado que
já custou uma sessão. Peça julgável é:
  1. um punhado de eixos do reconhecimento que ela atende;
  2. um gesto próprio, que produz registro onde ELA domina a cena;
  3. arquivos próprios, que não se cruzam com os de outra peça.

TODO eixo precisa de dono: ou uma peça, ou a lista eixos_do_diretor. Eixo sem dono é
defeito entre peças esperando para acontecer — foi assim que um juiz aprovou uma medida a
74% e outro a 62%, e a incoerência não morava em nenhuma das duas.

Teto: ${TETO_PECAS} peças. Funda o que não merece juiz próprio.
Marque como exploratória a peça em que vale explorar três caminhos antes de escolher.
${feedback ? `\nA volta anterior foi recusada por isto — conserte:\n${feedback}` : ''}
`

const construirPrompt = ({ peca, rodada, gap, exploratoria }) => `
Você é o CONSTRUTOR da peça "${peca.id}". Você não julga o que constrói.
${LEIA}
O que ela é: ${peca.desc || peca.id}
Os eixos dela: ${peca.eixos.join(' · ')}
Os arquivos dela: ${peca.arquivos.join(' · ')} — não toque em arquivo de outra peça.

${exploratoria && rodada === 1 ? `
PRIMEIRA RODADA, PEÇA EXPLORATÓRIA. Não escolha um caminho e defenda.
Faça TRÊS propostas diferentes de verdade — não três variações da mesma —, monte lado a
lado, e OLHE. Escolha com o olho, não com o argumento. Descartar as três e montar uma
quarta com o que sobreviveu de cada é o melhor resultado possível, e já aconteceu duas vezes.
` : gap ? `
RODADA DE CONSERTO. O juiz devolveu UM defeito, e é só nele que você mexe:
  eixo: ${gap.eixo}
  o que ele viu: ${gap.gap}
Não explore alternativas aqui — responda ao defeito.

E MEÇA A ACUSAÇÃO ANTES DE OBEDECER. Duas vezes, numa sessão real, o defeito apontado não
existia, e o agente que mediu antes salvou o que estava certo. Se a medição contradisser a
acusação, devolva a medição em vez do conserto.
` : ''}

REGISTRE OS DESCARTES. O que você NÃO escolheu, e o que você viu na tela que o matou. É o
que impede a próxima rodada de repetir uma alternativa já reprovada — e nos melhores
relatórios daquelas sessões, o descarte era o argumento inteiro.

Ao terminar, grave ${MISSAO}/pecas/${peca.id}/r${rodada}/entrega.json com o manifesto: o
caminho e a marca de cada artefato que você tocou. A marca é
  python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest()[:16])" <arquivo>
O manifesto é ALEGAÇÃO: o programa recomputa cada marca contra o disco no fecho.
`

const julgarPrompt = ({ peca, rodada, eixos }) => `
Você é o CRÍTICO da peça "${peca.id}". Você NÃO construiu nada e não vai construir.

NÃO ACEITE DE NINGUÉM UMA LISTA DE DEFEITOS — nem do construtor, nem de quem te lançou. Se
alguém te mandar uma, ignore e diga que ignorou. Medido: de três defeitos que um
orquestrador passou a um crítico, DOIS não se sustentaram na medição, e o crítico que veio
sem lista achou sete coisas que ninguém tinha visto.

ANTES de ler qualquer relatório do construtor, observe e forme o seu juízo. Ler a
justificativa primeiro faz você julgar o argumento em vez de julgar a obra.

CONFIRA QUE A OBRA PAROU. Leia ${MISSAO}/pecas/${peca.id}/r${rodada}/entrega.json e
recompute a marca de cada artefato. Divergiu, a obra ainda estava mudando: devolva nulo.

OBSERVE OS DOIS pelo MESMO procedimento — a sonda:
${JSON.stringify(RITO.sonda, null, 1)}
Gesto desta peça: ${peca.gesto}
Grave o registro do nosso em r${rodada}/nosso.<ext> e o do alvo em r${rodada}/alvo.<ext>.

JULGUE COM DUAS RÉGUAS AO MESMO TEMPO:
  1. os eixos — em cada um, o nosso ganha ou empata do alvo?
     ${eixos.filter(e => peca.eixos.includes(e.nome)).map(e => `• ${e.nome} (${e.gesto})`).join('\n     ')}
  2. o congelado — isto viola algo que o dono trancou?

SEU MANDATO: só passa se for MELHOR que o alvo. Não "bom". Melhor.

Se não passar, devolva O MAIOR GAP — um só, o que mais separa — nomeando o EIXO. Se você
vir algo que os eixos não cobrem, pode abrir um eixo novo, pagando o mesmo preço: nome,
gesto e registro.
Se o que sobra for ganho pequeno demais para valer outra rodada, devolva status marginal.

Veredito sem os dois registros é NULO e a rodada não conta.
Você não está aqui para ser justo com o esforço de ninguém.
`

const dirigirPrompt = ({ pecas, eixosDoDiretor, eixos }) => `
Você é o DIRETOR. As peças já passaram, cada uma pelo seu crítico. Você olha o CONJUNTO.

Duas coisas, e só duas:

1. OS EIXOS QUE NENHUMA PEÇA POSSUI: ${(eixosDoDiretor || []).join(' · ') || 'nenhum'}
   ${eixos.filter(e => (eixosDoDiretor || []).includes(e.nome)).map(e => `• ${e.nome} (${e.gesto})`).join('\n   ')}
   São os transversais, e são invisíveis a todo juiz de peça — um aprovou uma medida a 74%,
   outro a 62%, e a incoerência não morava em nenhuma das duas.

2. A PERGUNTA DO CONJUNTO: isto parece feito pela mesma mão?

Observe pela sonda, nos dois. Devolva em "viu" a marca da entrega de cada peça que você
olhou — é o que prova que você não julgou uma versão superada:
${pecas.map(p => `  "${p.id}": <a marca de ${MISSAO}/pecas/${p.id}/r<última>/entrega.json>`).join('\n')}
`

const gravaPrompt = (caminho, dado) => `
Papel MECÂNICO e só. Grave este conteúdo em ${caminho}, criando o diretório se preciso:

${JSON.stringify(dado, null, 1)}
`

// ─────────────────────────────────────────────────────────────────────────────

const bloqueios = []
phase('Reconhecer')

// RECONHECIMENTO — os eixos podem já ter vindo aprovados da abertura. Se vieram, o
// reconhecimento não roda de novo: ele é pago uma vez por missão.
let eixos = RITO.eixos || []
if (!eixos.length) {
  const recon = await agent(reconPrompt(),
    { model: MODEL, effort: T.decompose.effort, phase: 'Reconhecer',
      label: 'recon', schema: EIXOS })
  if (!recon) {
    return { erro: 'o reconhecimento não respondeu — sem eixos não há régua, e sem régua o juiz vira revisor de conformidade' }
  }
  eixos = recon.eixos
}
const nomesDeEixo = new Set(eixos.map(e => e.nome))

// DECOMPOSIÇÃO — com o gate ANTES de qualquer construtor sair. Decomposição ruim solta
// sete construtores em cima de recorte injulgável, e o custo disso é a missão inteira.
phase('Decompor')
let decomp = null, feedback = null
for (let tentativa = 1; tentativa <= 3 && !decomp; tentativa++) {
  const proposta = await agent(decomporPrompt({ eixos, feedback }),
    { model: MODEL, effort: T.decompose.effort, phase: 'Decompor',
      label: `decompor:${tentativa}`, schema: DECOMP })
  if (!proposta) break
  const furos = []
  const donos = new Set()
  for (const p of proposta.pecas) {
    for (const e of p.eixos) {
      donos.add(e)
      if (!nomesDeEixo.has(e)) furos.push(`a peça ${p.id} cita o eixo "${e}", que não existe`)
    }
  }
  for (const e of proposta.eixos_do_diretor || []) donos.add(e)
  const orfaos = [...nomesDeEixo].filter(e => !donos.has(e))
  if (orfaos.length) furos.push(`eixo sem dono: ${orfaos.join(' · ')} — dê a uma peça ou ao diretor`)
  if (proposta.pecas.length > TETO_PECAS) {
    furos.push(`${proposta.pecas.length} peças passam do teto de ${TETO_PECAS} — funda o que não merece juiz próprio`)
  }
  for (const a of proposta.pecas) {
    for (const b of proposta.pecas) {
      if (a.id >= b.id) continue
      const cruza = a.arquivos.filter(f => b.arquivos.includes(f))
      if (cruza.length) furos.push(`${a.id} e ${b.id} disputam ${cruza.join(' · ')}`)
    }
  }
  if (furos.length) { feedback = furos.join('\n'); continue }
  decomp = proposta
}
if (!decomp) {
  return { erro: 'a decomposição não passou no gate em três tentativas', feedback }
}
await agent(gravaPrompt(`${MISSAO}/decomposicao.json`, decomp),
  { model: MODEL, effort: T.mechanical.effort, phase: 'Decompor', label: 'gravar:decomp' })

// O LAÇO — um por peça, todos ao mesmo tempo. Dentro de cada um, o juiz é a linha
// seguinte à do construtor, e é isso que mata a falha de origem: não existe caminho
// da entrega ao fecho que não passe por ele.
const resultados = await parallel(decomp.pecas.map(peca => async () => {
  const historia = []
  for (let rodada = 1; rodada <= TETO_RODADAS; rodada++) {
    if (TETO_GASTO && gasto() >= TETO_GASTO) {
      bloqueios.push({ peca: peca.id, o_que: `o orçamento acabou na rodada ${rodada}` })
      return { peca: peca.id, status: 'orcamento', historia }
    }
    const anterior = historia[historia.length - 1]
    const entrega = await agent(
      construirPrompt({ peca, rodada, gap: anterior, exploratoria: peca.exploratoria }),
      { model: MODEL, effort: T.executor.effort, phase: 'Construir',
        label: `constroi:${peca.id}:r${rodada}`, schema: ENTREGA })
    if (!entrega) {
      bloqueios.push({ peca: peca.id, o_que: `o construtor da rodada ${rodada} não respondeu` })
      return { peca: peca.id, status: 'construtor-mudo', historia }
    }

    // ▼ ESTA LINHA É A SKILL INTEIRA. Não ponha branch entre ela e a de cima.
    const veredito = await agent(julgarPrompt({ peca, rodada, eixos }),
      { model: MODEL, effort: T.coordinate.effort, phase: 'Julgar',
        label: `julga:${peca.id}:r${rodada}`, schema: VEREDITO })

    if (!veredito) {
      // Juiz que não respondeu NÃO aprovou nada. A direção segura é não fechar.
      bloqueios.push({ peca: peca.id, o_que: `o juiz da rodada ${rodada} não respondeu — a obra ficou SEM julgamento` })
      return { peca: peca.id, status: 'juiz-mudo', historia }
    }
    if (veredito.status === 'reprovado' && veredito.eixo
        && !nomesDeEixo.has(veredito.eixo) && veredito.eixo_novo) {
      // O juiz pode ver o que o reconhecimento não viu, pagando o mesmo preço de prova.
      eixos.push(veredito.eixo_novo)
      nomesDeEixo.add(veredito.eixo_novo.nome)
      await agent(gravaPrompt(`${MISSAO}/recon/eixos.json`, { eixos }),
        { model: MODEL, effort: T.mechanical.effort, phase: 'Julgar', label: `eixo-novo:${peca.id}` })
    }
    historia.push(veredito)
    if (veredito.status === 'aprovado' || veredito.status === 'marginal') {
      return { peca: peca.id, status: veredito.status, rodadas: rodada, historia }
    }
    log(`${peca.id} r${rodada}: ${veredito.eixo} — ${veredito.gap}`)
  }
  bloqueios.push({ peca: peca.id, o_que: `passou de ${TETO_RODADAS} rodadas sem aprovar` })
  return { peca: peca.id, status: 'teto-de-rodadas', historia }
}))

// O DIRETOR — o conjunto, e os eixos que ninguém possui. Uma passada, no fecho: rodar
// a cada volta multiplicaria o custo da parte que já não acontecia por ser cara.
phase('Fechar')
const fechadas = resultados.filter(Boolean)
  .filter(r => r.status === 'aprovado' || r.status === 'marginal')
let diretor = null
if (fechadas.length === decomp.pecas.length) {
  diretor = await agent(dirigirPrompt({
    pecas: decomp.pecas, eixosDoDiretor: decomp.eixos_do_diretor, eixos }),
    { model: MODEL, effort: T.finalize.effort, phase: 'Fechar',
      label: 'diretor', schema: DIRETOR })
  if (diretor) {
    await agent(gravaPrompt(`${MISSAO}/diretor.json`, diretor),
      { model: MODEL, effort: T.mechanical.effort, phase: 'Fechar', label: 'gravar:diretor' })
  } else {
    bloqueios.push({ o_que: 'o diretor não respondeu — o conjunto ficou sem olhar' })
  }
} else {
  bloqueios.push({ o_que: `${decomp.pecas.length - fechadas.length} peça(s) não fecharam — o diretor não roda sobre obra pela metade` })
}

// A CONFERÊNCIA — e ela é quem apaga o sinal, não este script e não quem orquestra.
const conferencia = await agent(`
Papel MECÂNICO e só. Rode, e devolva a saída CRUA, sem interpretar:

  ${CHECK} fecho "${MISSAO}"
  ${CHECK} mapa "${MISSAO}"

Se o primeiro sair zero, a missão fechou e o sinal foi apagado por ele. Se sair um, NÃO
apague o sinal, NÃO conserte nada, e apenas devolva o que ele imprimiu.
`, { model: MODEL, effort: T.mechanical.effort, phase: 'Fechar', label: 'conferencia' })

return {
  pecas: resultados.filter(Boolean).map(r => ({
    peca: r.peca, status: r.status, rodadas: r.rodadas || (r.historia || []).length,
    ultimo_gap: (r.historia || []).slice(-1).map(v => v && v.gap).filter(Boolean)[0] || null,
  })),
  eixos: eixos.map(e => e.nome),
  diretor: diretor ? diretor.status : null,
  bloqueios,
  conferencia,
  gasto: gasto(),
}
