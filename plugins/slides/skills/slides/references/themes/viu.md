# Tema: VIU (default)

Identidade VIU Studio: dark-only, Slate & Blue, ação em azul, destaque em violeta. Tipografia **Outfit** (headings) + **Inter** (corpo) + **JetBrains Mono** (rótulos/números). É o tema canônico — derivado do `STYLE_GUIDE.md` dos VIU Studio Tools, mas em **linguagem keynote** (tipografia grande, respiro), não densidade de dashboard.

## `__FONT_LINKS__`

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
```

## `__THEME_CSS__`

```css
:root{
    /* fonts — fallback de sistema garante que nada fique em branco sem internet (Google Fonts off) */
    --font-head:'Outfit',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
    --font-body:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
    --font-mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
    /* backgrounds */
    --bg-body:#0f172a; --bg-surface:#1e293b;
    /* action / accent */
    --primary:#3b82f6; --primary-soft:#60a5fa;
    --accent:#8b5cf6; --accent-soft:#a78bfa;
    /* status */
    --success:#22c55e; --warning:#f59e0b; --danger:#ef4444;
    /* text */
    --text-main:#f1f5f9; --text-muted:#94a3b8; --text-dim:#64748b;
    /* lines */
    --border:rgba(96,165,250,.35); --hair:rgba(255,255,255,0.07);
    /* atmosphere */
    --glow-a:rgba(59,130,246,.14); --glow-b:rgba(139,92,246,.10);
    --glass-grad:linear-gradient(135deg,#fff 0%,#94a3b8 100%);
}
```

## `__BRAND__`

`VIU Studio` — texto da marca no rodapé (canto inferior esquerdo).

## `__THEME_COLOR__`

`#0f172a` — valor **literal** de `--bg-body` (a tag `<meta name="theme-color">` não lê CSS var). Pinta a barra do navegador no celular. Num tema novo, repita a mesma cor do `--bg-body`.

---

## Como criar um tema novo

Um tema é só este arquivo com outros valores. Para um tema nomeado (ex: nome de cliente/projeto), copie `viu.md` → `<nome>.md` e troque:

- **As 3 fontes** (`--font-head/body/mono`) e o `__FONT_LINKS__` correspondente. Fuja de Inter/Roboto/Arial genéricos — escolha um par com personalidade. **Mantenha o fallback de sistema** (`system-ui,-apple-system,…`) no fim de cada `--font-*`: sem internet, o deck não pode ficar em branco.
- **A paleta** (`--bg-*`, `--primary*`, `--accent*`, `--text-*`). Mantenha contraste alto: texto principal claro sobre fundo escuro (ou o inverso, num tema claro).
- **`--glow-a/b`**: versões `rgba()` translúcidas das cores `--primary`/`--accent` (alpha ~.08–.15).
- **`--glass-grad`**: gradiente do título de capa. Num tema escuro, `#fff → --text-muted`; num claro, inverta.
- **`--border`**: cor da linha quando um item está em foco/hover (derive de `--primary`).
- **`--hair`**: filete divisor quase invisível (~7% de contraste com o fundo).
- **`__THEME_COLOR__`**: valor literal igual ao `--bg-body` (barra do navegador no celular).

O contrato de variáveis acima é **fechado**: o `template.html` só usa essas vars (mais os placeholders `__TITLE__`, `__OG_DESC__`, `__THEME_COLOR__`, `__FONT_LINKS__`, `__THEME_CSS__`, `__BRAND__`, `__SLIDES__`). Se definir todas, o tema funciona. Não invente vars novas sem adicionar uso no template.
