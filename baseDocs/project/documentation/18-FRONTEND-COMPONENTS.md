# 18 — Frontend Components

## UI Component Library

The application uses **shadcn/ui** — a collection of reusable components built on top of **Radix UI** primitives, styled with **Tailwind CSS**.

Configuration: `royalties/frontend/components.json`

---

## shadcn/ui Primitives

### Alert (`ui/alert.tsx`)

Displays a callout message with an icon and description.

**Variants**: `default`, `destructive`

```tsx
<Alert variant="destructive">
  <AlertTitle>Error</AlertTitle>
  <AlertDescription>Something went wrong</AlertDescription>
</Alert>
```

### Badge (`ui/badge.tsx`)

Small label for status indicators.

**Variants**: `default`, `secondary`, `destructive`, `outline`

```tsx
<Badge variant="destructive">3 Errors</Badge>
<Badge variant="secondary">5 Warnings</Badge>
```

### Button (`ui/button.tsx`)

Primary interactive element.

**Variants**: `default`, `destructive`, `outline`, `secondary`, `ghost`, `link`
**Sizes**: `default`, `sm`, `lg`, `icon`

```tsx
<Button variant="outline" size="sm">Download PDF</Button>
```

### Card (`ui/card.tsx`)

Container for content sections.

**Parts**: `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter`

```tsx
<Card>
  <CardHeader>
    <CardTitle>Summary</CardTitle>
  </CardHeader>
  <CardContent>...</CardContent>
</Card>
```

### DropdownMenu (`ui/dropdown-menu.tsx`)

Context/action menu triggered by a button.

**Parts**: `DropdownMenu`, `DropdownMenuTrigger`, `DropdownMenuContent`, `DropdownMenuItem`, `DropdownMenuSeparator`

### Input (`ui/input.tsx`)

Text input field extending native `<input>`.

### Label (`ui/label.tsx`)

Form label extending Radix `Label`.

### ScrollArea (`ui/scroll-area.tsx`)

Custom scrollable container (Radix ScrollArea).

### Separator (`ui/separator.tsx`)

Visual divider line (horizontal or vertical).

### Sheet (`ui/sheet.tsx`)

Slide-out panel (used for `HistorySheet`).

**Parts**: `Sheet`, `SheetTrigger`, `SheetContent`, `SheetHeader`, `SheetTitle`, `SheetDescription`

### Spinner (`ui/spinner.tsx`)

Custom loading indicator (animated SVG).

### Tooltip (`ui/tooltip.tsx`)

Hover tooltip (Radix Tooltip).

**Parts**: `Tooltip`, `TooltipTrigger`, `TooltipContent`, `TooltipProvider`

---

## Application Components

### Layout (`Layout.tsx`)

App shell wrapping all routes. Contains:
- Header with logo, navigation links, user info
- Theme toggle (`ThemeToggle`)
- Logout button
- `<Outlet />` for route content

### ProtectedRoute (`ProtectedRoute.tsx`)

Route guard component:
- Shows `<Spinner>` while verifying auth token
- Redirects to `/login` if user is not authenticated
- Renders children if authenticated

### AuthContext (`AuthContext.tsx`)

React Context provider for authentication state.

**Exported**:
- `AuthProvider` — wraps the app
- `useAuth()` — hook returning `{ user, token, loading, login, register, logout }`

### ThemeProvider (`ThemeProvider.tsx`)

Dark/light/system theme management.

**Exported**:
- `ThemeProvider` — wraps the app
- `useTheme()` — hook returning `{ theme, setTheme, resolvedTheme }`

### ThemeToggle (`ThemeToggle.tsx`)

Cycling button: dark → light → system. Displays current theme icon.

### AuthBackground (`AuthBackground.tsx`)

Animated mesh-gradient background used on login and register pages. Creates a cinematic visual effect.

### DocumentChat (`DocumentChat.tsx`)

AI chat sidebar for the Results page. Injected with the full document content as context.

**Props**:
- `filename: string`
- `content: string`
- `uploadId: string`

Uses `useChat` from TanStack AI with `fetchServerSentEvents`.

### DocumentPreview (`DocumentPreview.tsx`)

File content preview component with three modes:
1. **Table view**: Renders parsed data as an HTML table
2. **Raw text**: Shows raw file content
3. **PDF iframe**: Renders PDF files in an iframe

**Props**:
- `uploadId: string`
- `fileFormat: string`

### HistorySheet (`HistorySheet.tsx`)

Slide-out panel showing past uploads and validations. Uses the `Sheet` component.

- Lists uploads ordered by newest first
- Shows validation run status per upload
- Click to navigate to results page

---

## Design Tokens

### Color System (OKLCH)

CSS variables defined in `index.css`:

```css
/* Light mode */
:root {
  --background: 0.98 0.005 285;
  --foreground: 0.15 0.01 285;
  --primary: 0.65 0.18 45;         /* Warm amber */
  --primary-foreground: 0.98 0.005 45;
  --secondary: 0.93 0.01 285;
  --destructive: 0.55 0.22 25;     /* Red */
  --muted: 0.93 0.005 285;
  --accent: 0.93 0.01 285;
  --card: 0.98 0.005 285;
  --border: 0.88 0.01 285;
  --ring: 0.65 0.18 45;
  --radius: 0.625rem;
}

/* Dark mode */
.dark {
  --background: 0.12 0.01 285;
  --foreground: 0.92 0.01 285;
  --primary: 0.7 0.18 45;
  --card: 0.15 0.01 285;
  --border: 0.25 0.01 285;
  /* ... */
}
```

### Custom Palettes

```javascript
// tailwind.config.js
brand: {
  50: '...', 100: '...', ..., 900: '...'  // Warm amber scale
},
ink: {
  50: '...', 100: '...', ..., 900: '...'  // Neutral gray scale
}
```

### Font Stack

```javascript
// tailwind.config.js
fontFamily: {
  display: ['Outfit', ...],                          // Headings
  body: ['Plus Jakarta Sans', 'Inter Variable', ...], // Body text
  mono: ['JetBrains Mono', ...],                     // Code
}
```

### Custom CSS Utilities

```css
.text-gradient {
  background: linear-gradient(...);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.surface-elevated {
  box-shadow: var(--elevated-shadow);
  background: var(--card);
}

.noise-overlay {
  background-image: url("data:image/svg+xml,...");
  opacity: 0.03;
}
```

---

## Icon Library

Uses **Lucide React** (v0.577) — a fork of Feather Icons with 1000+ icons.

Import pattern:
```tsx
import { Upload, FileText, AlertCircle, CheckCircle } from 'lucide-react'
```

Common icons used:
| Icon | Usage |
|------|-------|
| `Upload` | Upload button/area |
| `FileText` | File references |
| `AlertCircle` | Error indicators |
| `AlertTriangle` | Warning indicators |
| `CheckCircle` | Success/passed indicators |
| `Info` | Info indicators |
| `Download` | Download buttons |
| `Send` | Chat send button |
| `X` | Close/remove buttons |
| `Sun`, `Moon`, `Monitor` | Theme toggle |
| `ChevronDown`, `ChevronRight` | Expandable sections |
| `FileSpreadsheet` | CSV/Excel files |
| `Archive` | ZIP/archive files |

---

## Animation Library

Uses **Motion** (Framer Motion v12) for:

- Page transitions
- Component mount/unmount animations
- Hover and tap effects
- Layout animations

```tsx
import { motion, AnimatePresence } from 'motion/react'

<AnimatePresence>
  {isVisible && (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
    >
      Content
    </motion.div>
  )}
</AnimatePresence>
```
