Drop the two variable-font WOFF2 files here for fully-offline operation:

  Fraunces.woff2         — https://fonts.google.com/specimen/Fraunces
  GeistVariable.woff2    — https://vercel.com/font  (or Fontshare)

Until you do, the frontend pulls the same fonts from Google Fonts on first
load (see the <link> in index.html), so the Pi needs internet once to
populate the HTTP cache. Once the WOFF2 files are here, styles.css will
pick them up via the FrauncesLocal / GeistLocal @font-face entries and
no external fetch is needed.

File names matter — they're referenced verbatim from styles.css.
