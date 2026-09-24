# Ofertas de arquitetura — capacidades que a concepção deve oferecer

Capacidades que apps de gestão costumam precisar e que quase nunca aparecem na primeira conversa,
porque ninguém sente falta delas até o dia em que faltam. Nasceram de um caso real: um app de gestão
em produção que não tinha nenhuma das cinco, e cujo dono as pediu como "coisa importante que o app
não tinha" na concepção da reescrita (2026-09-24).

**Como usar:** na etapa 2 (arquitetura), depois da pergunta "o que você decidiu NÃO construir",
**ofereça** cada capacidade que for pertinente ao projeto — uma pergunta por vez, com o palpite e a
confiança, como toda pergunta da entrevista. Oferta não é resposta: o que o dono não confirmar não
entra no `architecture-intent.md`. "Não se aplica" é resposta válida e fica registrada.

**Quando é pertinente:** o projeto guarda dado que o dono não pode perder, tem mais de uma pessoa
operando, ou roda sem ninguém olhando. Script de uso único, protótipo e biblioteca não levam nenhuma.

## 1 · Backup com gestão completa na tela
- **O que é:** cópia automática dos bancos e dos arquivos anexos para um destino fora do servidor
  (ex.: Amazon S3), governada pela tela de configuração.
- **O que a tela oferece:** frequência, dias e horários num seletor completo; retenção; cópia fora de
  hora a qualquer momento; histórico de cada rodada (início, fim, tamanho, destino, resultado);
  acesso aos arquivos e download manual; alerta quando a cópia atrasa ou falha.
- **Por que oferecer:** a janela de perda aceitável muda com o negócio; se ela for configuração, e
  não código, encurtá-la no futuro é mudar um valor.
- **Pergunta de oferta:** "Com que frequência o sistema copia os dados, e você quer poder mudar isso
  pela tela, baixar as cópias e ver o histórico delas?"

## 2 · Registro completo do que acontece (logs)
- **O que é:** todo pedido ao servidor, comando, erro, entrada de conta, mudança de permissão,
  rodada de backup e chamada a integração deixa registro com quem, quando, o quê, resultado, duração
  e o código da requisição.
- **Onde se lê:** na tela de configuração, com filtro por período, pessoa, tipo e resultado; e no
  servidor, em formato estruturado, para depuração.
- **Cuidado obrigatório:** dado pessoal nunca entra no registro; o tempo de guarda é configurável.
- **Pergunta de oferta:** "Quando algo der errado, você quer achar o que aconteceu pela própria tela,
  sem abrir o servidor?"

## 3 · Desfazer em vários níveis
- **O que é:** cada pessoa tem uma pilha de desfazer com N níveis (N configurável), e refazer
  enquanto nada novo foi feito por cima.
- **Como convive com "nada se apaga":** desfazer nunca apaga — em livro de lançamentos vira
  estorno com motivo "desfeito"; em cadastro volta à versão anterior.
- **Pergunta de oferta:** "Errar um registro hoje custa quanto para consertar? Um botão de desfazer
  com vários níveis ajudaria?"

## 4 · Avisos por vários canais
- **O que é:** todo alerta do sistema sai pelos canais que o dono escolher: email, Telegram,
  notificação no navegador (web push). Cada canal é um encaixe trocável; cada entrega fica no
  registro.
- **Pergunta de oferta:** "Quando algo pede atenção, por onde você quer ser avisado?"

## 5 · WhatsApp pela Evolution API
- **O que é:** integração com WhatsApp por uma API aberta, para receber pedidos, enviar avisos ou
  atender clientes. Referência: [evolution-foundation/evolution-api](https://github.com/evolution-foundation/evolution-api)
  (conferido em 2026-09-24: repositório ativo, não arquivado, Node.js e TypeScript; suporta a
  WhatsApp Web API via Baileys e a WhatsApp Cloud API oficial).
- **Quando oferecer:** o negócio conversa com o cliente pelo WhatsApp e isso tem que entrar no
  sistema. Não é padrão: no caso de origem, o dono respondeu "não se aplica".
- **Cuidado:** a licença do repositório aparece como não declarada na API do GitHub
  (`NOASSERTION`) — confira a licença e os termos de uso do WhatsApp antes de propor.
- **Pergunta de oferta:** "Seus clientes falam com você pelo WhatsApp? Isso precisa entrar no
  sistema, ou fica fora?"
