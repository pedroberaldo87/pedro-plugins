# Banco de sugestões — Do's and Don'ts de interface

Sugestões para a seção `## Do's and Don'ts` de um `DESIGN.md`, colhidas de design systems públicos e
de pesquisa de usabilidade (leitura de 2026-09-24). Servem de **pista para a pergunta** "o que nunca
pode acontecer visualmente neste produto?" — nunca de resposta pronta. O dono escolhe quais valem;
item que ele não confirmou não entra no documento.

Como usar: filtre pelo tipo de produto (o banco foi colhido pensando em app de gestão com tabela,
formulário e número), leve à entrevista só os que tocam o que o produto faz, e junte a eles os
"nuncas" que o próprio projeto já provou (defeito achado, lei do projeto). Cada item traz a fonte;
ao citar, cite a fonte.

## Tabelas
- **Do** alinhar números à direita e usar algarismos de largura fixa. [GOV.UK table](https://design-system.service.gov.uk/components/table/) · [Primer data table](https://primer.style/product/components/data-table/guidelines/)
- **Do** mostrar com clareza quando um filtro está ativo. [NN/g data tables](https://www.nngroup.com/articles/data-tables/)
- **Do** paginar muito dado, com a paginação no rodapé; ~20 linhas por página para começar. [Primer](https://primer.style/product/components/data-table/guidelines/) · [Carbon v10](https://v10.carbondesignsystem.com/components/data-table/usage/)
- **Do** dar à ação de linha um rótulo único que cite a linha ("Editar V-0418", não "Editar"). [Atlassian dynamic table](https://atlassian.design/components/dynamic-table/usage)
- **Don't** usar o destaque da linha como único meio de dizer significado, seleção ou foco. [Atlassian](https://atlassian.design/components/dynamic-table/usage)
- **Don't** pôr caractere ou ícone em célula vazia. [Primer](https://primer.style/product/components/data-table/guidelines/)
- **Don't** misturar alturas de linha, nem pôr tabela densa dentro de modal ou caixa pequena. [Carbon v10](https://v10.carbondesignsystem.com/components/data-table/usage/)

## Formulários e entrada
- **Do** rótulo visível acima do campo, e ajuda que não some ao digitar. [NN/g placeholders](https://www.nngroup.com/articles/form-design-placeholders/) · [GOV.UK text input](https://design-system.service.gov.uk/components/text-input/)
- **Do** campo da largura do conteúdo esperado. [GOV.UK text input](https://design-system.service.gov.uk/components/text-input/)
- **Do** marcar "(opcional)" no rótulo do campo opcional. [GOV.UK question pages](https://design-system.service.gov.uk/patterns/question-pages/)
- **Don't** usar placeholder no lugar do rótulo ou da instrução. [GOV.UK](https://design-system.service.gov.uk/components/text-input/) · [NN/g](https://www.nngroup.com/articles/form-design-placeholders/)
- **Don't** usar controle deslizante para valor exato (peso, dinheiro, quantidade). [GOV.UK question pages](https://design-system.service.gov.uk/patterns/question-pages/) · [NN/g sliders](https://www.nngroup.com/articles/sliders-knobs/) · [NN/g steppers](https://www.nngroup.com/articles/input-steppers/)
- **Don't** usar `<input type="number">` sem motivo; prefira `inputmode="numeric"`. [GOV.UK text input](https://design-system.service.gov.uk/components/text-input/)
- **Don't** pular o foco sozinho entre campos (ex.: dia, mês, ano). [GOV.UK date input](https://design-system.service.gov.uk/components/date-input/)
- Divergência entre fontes: asterisco em campo obrigatório — GOV.UK proíbe, Atlassian recomenda. Decisão do dono.

## Erro, vazio, carregando, salvo
- **Do** erro perto de onde nasceu, dizendo o que houve e como corrigir, sem culpar a pessoa. [NN/g error messages](https://www.nngroup.com/articles/error-message-guidelines/) · [GOV.UK error message](https://design-system.service.gov.uk/components/error-message/)
- **Do** preservar tudo o que foi digitado quando algo falha. [NN/g](https://www.nngroup.com/articles/error-message-guidelines/) · [GOV.UK](https://design-system.service.gov.uk/components/error-message/)
- **Do** vazio que explica o que apareceria ali e leva à tarefa que o preenche. [NN/g empty states](https://www.nngroup.com/articles/empty-state-interface-design/)
- **Do** spinner para um bloco isolado, esqueleto para a tela inteira, barra de progresso acima de 10 s, nada abaixo de 1 s. [NN/g skeleton screens](https://www.nngroup.com/articles/skeleton-screens/)
- **Don't** mensagem genérica ("ocorreu um erro"). [NN/g](https://www.nngroup.com/articles/error-message-guidelines/)
- **Don't** esconder que algo quebrou, nem mostrar "vazio" quando o dado existe e falhou ao carregar. [Primer degraded experiences](https://primer.style/ui-patterns/degraded-experiences)
- **Don't** aviso que some sozinho para mensagem crítica. [Carbon v10 notifications](https://v10.carbondesignsystem.com/patterns/notification-pattern/)
- Lacuna: nenhuma fonte oficial encontrada sobre mostrar "salvo" antes da confirmação do servidor (interface otimista) — decisão do projeto.

## Ações destrutivas
- **Do** confirmar só o que é sério ou irreversível; para o resto, desfazer. [NN/g confirmation dialogs](https://www.nngroup.com/articles/confirmation-dialog/) · [Primer delete](https://primer.style/product/scenario-patterns/delete/)
- **Do** botão que nomeia o resultado ("Cancelar venda", "Estornar R$ 84,00"), nunca "Sim" ou "Confirmar". [NN/g](https://www.nngroup.com/articles/confirmation-dialog/) · [Smashing](https://www.smashingmagazine.com/2024/09/how-manage-dangerous-actions-user-interfaces/)
- **Do** peso da fricção proporcional ao dano: digitar o nome só para impacto amplo. [Primer delete](https://primer.style/product/scenario-patterns/delete/)
- **Do** dizer a consequência antes da ação. [GOV.UK warning text](https://components.publishing.service.gov.uk/component-guide/warning_text)
- **Don't** confirmação em ação rotineira — ela ensina a clicar sem ler. [NN/g](https://www.nngroup.com/articles/confirmation-dialog/) · [NN/g user mistakes](https://www.nngroup.com/articles/user-mistakes/)
- Divergência entre fontes: lado dos botões no rodapé do diálogo — Atlassian à direita, Smashing mostra à esquerda por proximidade. Decisão do dono.

## Cor de situação e acessibilidade
- **Do** cada cor de situação com um papel fixo, igual em todo o produto. [Primer color usage](https://primer.style/product/getting-started/foundations/color-usage/) · [Atlassian lozenge](https://atlassian.design/components/lozenge/examples)
- **Do** indicador de situação com texto junto da cor (e, se possível, forma ou símbolo). [Carbon v10 status indicators](https://v10.carbondesignsystem.com/patterns/status-indicator-pattern/) · [WCAG 1.4.1](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)
- **Do** contraste 4.5:1 no texto, 3:1 em etiqueta, ícone e indicador de estado. [WCAG 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) · [WCAG 1.4.11](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)
- **Do** foco de teclado visível e alvo de clique de pelo menos 24×24 px. [WCAG 2.4.13](https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html) · [WCAG 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
- **Don't** cor como único meio de informação. [WCAG 1.4.1](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)
- **Don't** mais de 5 ou 6 situações distintas. [Carbon v10](https://v10.carbondesignsystem.com/patterns/status-indicator-pattern/)
- **Don't** truncar o texto da etiqueta de situação. [Atlassian lozenge](https://atlassian.design/components/lozenge/examples)

## Números, unidades e datas
- **Do** formatar pela localidade (em pt-BR: vírgula decimal, ponto de milhar), nunca montar o número à mão. [MDN Intl.NumberFormat](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/NumberFormat)
- **Do** unidade sempre explícita, formatada pela mesma API. [MDN Intl.NumberFormat](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/NumberFormat)
- **Do** algarismos de largura fixa em dinheiro, e sinal de menos antes da moeda. [Polaris currency](https://polaris-react.shopify.com/foundations/formatting-localized-currency)
- **Do** mesmas casas decimais numa sequência de números. [ONS numbers](https://service-manual.ons.gov.uk/content/numbers/writing-numbers)
- **Do** zero antes da vírgula (0,5 e não ,5). [GOV.UK style guide](https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/style-guides/a-to-z-style-guide/)
- **Do** intervalo de datas com "a"/"até", sem travessão; sem ordinal em data. [GOV.UK style guide](https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/style-guides/a-to-z-style-guide/) · [Atlassian date and time](https://atlassian.design/content/date-time/)
- **Don't** fração no lugar de decimal. [Polaris currency](https://polaris-react.shopify.com/foundations/formatting-localized-currency)
- Divergência entre fontes: sinal de menos — GOV.UK usa, ONS evita em texto corrido. Decisão do dono.
