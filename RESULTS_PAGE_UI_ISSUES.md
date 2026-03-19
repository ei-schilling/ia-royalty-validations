# Results Page — UI Issues Audit

> Audited on 2026-03-18 using Chrome DevTools MCP at 375px, 768px, 1024px, 1280px viewports.  
> Page: `/results/:validationId`  
> Files: `ResultsPage.tsx`, `Layout.tsx`, `DocumentPreview.tsx`, `DocumentChat.tsx`

---

## CRITICAL — Mobile (375px): Layout completely broken

- [x] **#1 No responsive stacking**  
  The `flex` layout with `w-[40%]` left + `flex-1` right renders side-by-side on 375px — neither panel usable. Should stack vertically on mobile or show one panel at a time with a toggle.

- [x] **#2 Stats cards overlap / truncate**  
  `grid-cols-5` forces 5 columns on all screens. At 375px the pass-rate circle overlaps the "Passed" card; labels get cut: "Passe", "Erro", "Warni". Need responsive grid: `grid-cols-2 sm:grid-cols-3 lg:grid-cols-5`.

- [x] **#3 PDF preview panel unusable**  
  Right panel takes ~60% of 375px width, PDF too small to read. Tied to #1 — stacking fix resolves this.

- [x] **#4 No mobile navigation**  
  `hidden sm:flex` hides nav links but no hamburger menu or bottom tab bar exists. Users cannot navigate to Upload or Help from mobile.

- [x] **#5 Heading overlaps Preview/AI Chat tabs**  
  Left heading and right tab bar collide visually at the panel boundary. Tied to #1.

---

## HIGH — Tablet (768px): usable but cramped

- [x] **#6 Left panel too narrow for content**  
  At 40% of 768px ≈ 307px, validation text wraps aggressively (3+ lines for error descriptions).

- [x] **#7 Stats cards squeezed**  
  5-column grid at 768px → each card ~55px wide; labels truncate. Tied to #2.

- [x] **#8 Subtitle descriptions overflow**  
  `"— Rules that found critical issues…"` wraps awkwardly next to the badge on section headers.

---

## MEDIUM — Desktop (1024-1280px): polish issues

- [x] **#9 Header max-w-6xl vs main max-w-full misalignment**  
  Header constrained to `max-w-6xl` with `px-6`; results main is `max-w-full px-6`. At wide viewports, content doesn't align with header.

- [x] **#10 Panel height calc fragile**  
  `h-[calc(100vh-8rem)]` is hardcoded; doesn't match actual header (h-14) + main padding (py-8) + footer. Can overflow or leave gap.

- [x] **#11 `-my-2` negative margin hack**  
  Root container uses `-my-2` to counteract parent py, fragile if Layout padding changes.

- [ ] **#12 PDF viewer sidebar thumbnails**  
  Chrome PDF viewer sidebar + thumbnails waste horizontal space. Low priority — browser-native behavior.

---

## LOW — General polish (all breakpoints)

- [x] **#13 No "Back to top" / scroll indicator**  
  Left panel (`overflow-y-auto`) with many sections; users lose context. Fixed: Added scroll-to-top button with AnimatePresence that appears after scrolling 300px.

- [x] **#14 Stats card click feedback**  
  Metric cards are clickable but lack focus ring / pressed state; feel unresponsive.

- [x] **#15 Section subtitle hidden on mobile**  
  `hidden sm:inline` hides subtitles, badge sits at line end with no context. Acceptable but could add tooltip.

- [x] **#16 Issue card metadata wraps inconsistently**  
  `flex-wrap` metadata row (Row, field, Expected, Actual) breaks unevenly at narrow widths.

- [x] **#17 Panel close button no label on mobile**  
  Floating reopen button is icon-only; tooltips don't work on touch.

- [x] **#18 Footer takes vertical space**  
  Footer pushes content up in height-constrained layout. Fixed: Compact `py-2` footer on results page.

- [x] **#19 Actions dropdown icon confusion**  
  `ChevronDown` icon on "Actions" button — not a standard dropdown affordance pattern.

- [x] **#20 Pass rate ring re-animates**  
  SVG circle `initial/animate` replays on every re-mount. Fixed: Uses `hasAnimated` ref to skip animation on subsequent renders.
