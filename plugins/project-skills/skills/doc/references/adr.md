# Log de decisões (ADR) + declarações executáveis — gen 3.8

> Referência dos itens 4 e 6 do kit canônico. Consultada ao gerar `.claude/docs/decisions/`
> e `.claude/docs/declarations/`. O `/start` escreve o **primeiro** ADR (a partir da
> entrevista de estratégia); o `/doc` **detecta candidatos** e nunca escreve a decisão.

## 1 · `decisions/` — o log de decisões

Um arquivo por decisão, numerado, em **`.claude/docs/decisions/NNNN-<slug>.md`**.

### A regra de escopo — decisão mora na RAIZ

**Decisão que cruza módulos vive na raiz do projeto. Na dúvida, raiz.** Só decisão puramente
interna a um módulo (que ninguém de fora precisa saber para trabalhar) fica no módulo.

O caso real que justifica: uma decisão travada — "o escopo de escrita pela interface é apenas os
canais de notificação" — estava dentro do plano de um módulo. Um agente trabalhando no assunto
não a encontrou e propôs exatamente o contrário. Decisão enterrada é decisão que não existe.

### Molde

```markdown
---
generated: {YYYY-MM-DD}
project: {nome}
authored-by: human
status: proposto | aceito | substituído-por-NNNN | revogado
---

# NNNN · {título — o que foi decidido, em linguagem de negócio}

## Contexto
{a situação que forçou a decisão. O que estava em jogo, que restrição apertava.}

## Decisão
{o que foi decidido. Uma frase, na voz ativa: "Vamos usar X".}

## Alternativas descartadas
- **{alternativa}** — descartada porque {motivo}

## Consequências
- **Boas:** {o que isso destrava}
- **Ruins:** {o preço que a gente aceitou pagar — esta lista NÃO pode ficar vazia;
  decisão sem custo é decisão não examinada}

## Serve à meta
{qual atributo do quality-goals.md esta decisão prioriza}
```

### Regras duras

- **Decisão substituída NÃO se apaga.** Muda `status` para `substituído-por-NNNN` e aponta para a
  sucessora. O log é histórico; apagar destrói a razão de a coisa ter sido feita assim um dia.
- **Numeração nunca é reutilizada**, mesmo que um ADR seja revogado.
- **`authored-by: human`** — vale a mesma trava dos autorais: o FULL não reescreve ADR.
- **Consequências ruins obrigatórias.** ADR só com o lado bom é propaganda, não registro.

### Detecção de candidatos (isto o `/doc` FAZ)

A skill **não escreve a decisão** — ela aponta onde falta uma. Sinal: mudança estrutural no
histórico do git **sem ADR correspondente** no mesmo intervalo.

O que conta como mudança estrutural (todos observáveis no diff, sem LLM):
- serviço adicionado ou removido do `docker-compose*.yml`
- diretório top-level criado ou removido
- troca de dependência central (framework, ORM, biblioteca de auth) no manifesto
- mudança em `datasource`/engine de banco
- deploy mudando de alvo (novo host, novo provedor, novo pipeline)

Para cada candidato, reporte: **o commit, o que mudou, e a pergunta que um ADR responderia.**
Nunca invente o contexto ou o motivo — quem sabe é o humano. Ofereça `/start` para registrar.

**Critério de pronto:** toda decisão estruturante listada em `solution-strategy.md` tem ADR.

## 2 · `declarations/` — a superfície que a máquina lê

**Escopo honesto:** este é o item mais caro do kit e **só compensa em projeto que já tem
verificadores executáveis**. Sem leitor, é um arquivo bonito que ninguém abre — e o próprio kit
proíbe criar documento sem leitor.

**Portanto:** gere `declarations/` **apenas quando** o projeto tem ao menos um verificador
detectado (mesma detecção do `verified-by`). Sem verificador ⇒ **não gere**, e não é violação.

### O que é

Dado estruturado — **JSON, não prosa** — derivado mecanicamente do `data-stores.md` e do
`durability.md`. Uma superfície única lida por todos os verificadores do projeto, no lugar de cada
um manter sua própria lista de exceções embutida no código.

O problema que resolve, medido no caso real: 12 verificadores declaravam exceções em **7 formatos
diferentes** — 6 listas dentro de arquivos Python e 1 arquivo JSON, sem nenhuma biblioteca comum.
Adicionar uma dimensão nova (backup) criaria um oitavo formato.

### Formato

`.claude/docs/declarations/data-assets.json`:

```json
{
  "generated": "{YYYY-MM-DD}",
  "derived_from": [".claude/docs/data-stores.md", ".claude/docs/durability.md"],
  "assets": [
    {
      "id": "{identificador estável}",
      "kind": "database | volume | bucket | queue | cache",
      "nature": "irreplaceable | reconstructible | disposable",
      "location": "{host/container/provedor}",
      "backup": { "covered": true, "mechanism": "{script/timer}", "frequency": "{cron}", "retention": "{prazo}" }
    },
    {
      "id": "{outro}",
      "kind": "volume",
      "nature": "disposable",
      "backup": { "covered": false, "justification": "{obrigatória e NÃO-VAZIA}" }
    }
  ]
}
```

### Regras duras

- **Derivado, nunca fonte.** O `.md` é a verdade; o JSON é projeção. Editar o JSON à mão é drift.
- **`covered: false` exige `justification` não-vazia.** É a regra que transforma esquecimento em
  decisão registrada. Justificativa vazia ⇒ o gate de cobertura (verification #24) falha.
- **O verificador VARRE, não enumera.** Verificador que confere uma lista fixa envelhece no instante
  em que nasce algo novo, e a falha é **sempre silenciosa**: nada quebra, o item novo só nunca entra.
  A declaração existe para ser **comparada** contra a varredura da realidade, não para substituí-la.
- **Uma superfície só.** Dimensão nova entra como campo aqui, nunca como oitavo formato.
