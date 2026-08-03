# Limites aceitos

Cada item aqui é uma coisa que a régua reprova e que a gente decidiu **não**
consertar, com o motivo escrito. Sem este arquivo o desacordo vira ou dívida
esquecida ou conserto reflexo — os dois piores que a decisão registrada.

## As 82 páginas geradas antes da régua existir

**Decidido em 2026-08-03**, no fechamento do plano `2026-08-03-a-constituicao-se-cumpre`.

- A auditoria mede 100 páginas em `.claude/visual/` e reprova 82.
- As violações somam 1281 de duas-frases, 1042 de teto e 16 de conectivo.
- Nove delas foram digitadas à mão e nenhum gerador as alcança.
- A maioria é página de plano já encerrado, que ninguém vai reler.

**A régua passa a valer para página nova**, que é onde a constituição precisa
morder. As duas páginas do único plano aberto já passam limpas — verificado no
mesmo dia, então não sobrou nada a regenerar.

Como reconferir a qualquer momento:

```
$ python3 plugins/visual/lib/regua_audit.py paginas
📊 100 páginas · 82 com violação
    • duas-frases — duas frases no mesmo bullet: 1281
    • teto-140 — teto de 140 caracteres: 1042
    • conectivo — abre com conectivo de continuação: 16
    • ❔ 9 páginas sem perfil de gerador — digitada à mão, fora do alcance

✅ plano-2026-08-03-a-constituicao-se-cumpre-approve.html · árvore de plano
✅ plano-2026-08-03-a-constituicao-se-cumpre-track.html · árvore de plano
```

O que **revoga** este limite: uma página antiga voltar a ser lida para decidir
alguma coisa. Aí ela é regenerada, não lida como está.

⚠️ **O número aqui é um retrato, e retrato envelhece.** Em 2026-08-03 ele já
divergiu no mesmo dia: a auditoria passou a acusar 83 de 100, e a página a mais
era a gerada naquela tarde. Não era regressão — o auditor media o placeholder que
o próprio `visual_page.py` injeta na terceira opção de decisão, e esse texto era
duas frases. Corrigido em `visual_page.py:485`, o número voltou a 82 de 100.

**Nenhum verificador lê este arquivo.** Diferente dos retratos de `stop-budget` e
de vendoring, que o gate de commit compara, este só é lido por gente — um limite
vencido não é acusado por ninguém. É dívida conhecida, não descuido.

## Três geradores sem página no disco para medir

O veredito da auditoria marca `fallow/lib/report.py`, `slides/lib/md2deck.py` e
`branches/lib/branch_state.py` como em desacordo por motivos diferentes de prosa:

- Os dois primeiros não têm nenhuma página deste gerador no disco.
- O terceiro só tem página de 2026-07-28, anterior à mudança.

**Não é violação de forma — é ausência de amostra.** O conserto certo é gerar uma
página por esses caminhos e medir, não editar o gerador às cegas.
