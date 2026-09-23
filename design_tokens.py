"""Shared design tokens for the local browser sites (scratch/build_site.py and
visibility/scripts/build_site.py), lifted from Ninety's actual Terra design system —
see /Users/chickenman/Ninety-Clone/product-design-shell/libs/shared/terra/src/lib/styles/core/
(colors/_colors.variables.scss, typography/_typography.variables.scss,
radius/_radius.variables.scss, elevation/_elevation.variables.scss).

Terra has no app-wide dark theme (only isolated on-dark-background component variants), so
this is a light-theme-only palette — faithful to the product rather than to this repo's
previous placeholder dark-mode media query.

Hex values below are HSL->hex conversions of Terra's literal Sass tokens (Terra itself stores
them as HSLA); the numbers are exact, just recorded in a different color-space notation.
"""

# <link> tags for the two Terra type families. Put inside <head>, before <style>.
FONT_LINKS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@400;600;700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
"""

# The :root token block. Variable NAMES are kept stable across the two sites; only these
# values should need to change if Terra's tokens change.
ROOT_CSS = """
:root{
  /* surfaces (Terra neutral-light / background scale) */
  --bg:#f2f2f2; --surface:#ffffff; --surface-2:#fafafa; --sink:#e6e6e6;
  /* text (Terra `text` token: black at fixed alphas) */
  --ink:rgba(0,0,0,.87); --ink-2:rgba(0,0,0,.6); --ink-3:rgba(0,0,0,.38);
  /* borders (Terra `border` token) */
  --border:#e0e0e0; --border-2:#f2f2f2;
  /* brand (Terra `ninety` token, hsl(195,57%,43%)) */
  --accent:#2f8dac; --accent-2:#256e86; --accent-soft:#e3eff2;
  /* semantic (Terra `red`/`orange`/`green`, used here for churn/strong/positive/negative) */
  --churn:#ce4651; --churn-bg:#f9e7e8;
  --strong:#e57424; --strong-bg:#fcece0;
  --mild:rgba(0,0,0,.6); --mild-bg:#f2f2f2;
  --pos:#48994b; --neg:#ce4651; --neu:rgba(0,0,0,.6);
  /* type (Terra: Poppins for headings, Nunito Sans for body, root size 14px) */
  --font-heading:'Poppins',sans-serif;
  --font-body:'Nunito Sans',sans-serif;
  --font-mono:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",Menlo,monospace;
  /* radius (Terra scale: none/small/medium/large/huge) */
  --radius-sm:4px; --radius-md:8px; --radius-lg:16px; --radius-pill:999px;
  /* elevation (Terra level 1 / level 3) */
  --shadow-1:0 1px 1px 1px rgba(0,0,0,.08);
  --shadow-3:0 2px 4px 1px rgba(0,0,0,.16);
}
"""
