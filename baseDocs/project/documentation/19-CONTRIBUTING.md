# 19 — Contributing

## Code Style & Conventions

### Backend (Python)

| Tool | Purpose | Config |
|------|---------|--------|
| **Ruff** | Linter + formatter | `pyproject.toml` |
| **Type hints** | All function signatures | Python 3.12+ syntax |
| **Async everywhere** | All DB and HTTP operations | `async`/`await` |
| **Pydantic** | Request/response validation | V2 schemas |

**Naming conventions**:
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- API routes: `kebab-case` URLs, `snake_case` handler functions

### Frontend (TypeScript/React)

| Tool | Purpose | Config |
|------|---------|--------|
| **ESLint** | Linting | `eslint.config.js` |
| **Prettier** | Formatting | Integrated |
| **TypeScript** | Strict mode | `tsconfig.app.json` |

**Naming conventions**:
- Files: `PascalCase.tsx` (components), `camelCase.ts` (utilities/hooks)
- Components: `PascalCase`
- Hooks: `useCamelCase`
- Types/Interfaces: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- CSS classes: Tailwind utility classes

### Import Organization

```typescript
// 1. React/library imports
import { useState, useEffect } from 'react'
import { motion } from 'motion/react'

// 2. Internal components
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

// 3. Local imports
import { useAuth } from '@/components/AuthContext'
import { formatSize } from './utils/file-helpers'

// 4. Types
import type { BatchFile } from './types'
```

---

## Adding a New Validation Rule

1. **Create the rule file**: `backend/app/validation/rules/my_rule.py`

```python
from app.validation.base_rule import BaseRule, ValidationIssue, Severity

class MyRule(BaseRule):
    @property
    def rule_id(self) -> str:
        return "my_rule"

    @property
    def description(self) -> str:
        return "What this rule checks"

    def validate(self, data: list[dict]) -> list[ValidationIssue]:
        issues = []
        for row in data:
            if self._has_problem(row):
                issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    rule_id=self.rule_id,
                    rule_description=self.description,
                    row_number=row.get("_row_number"),
                    field="field_name",
                    expected_value="expected",
                    actual_value=str(row.get("field_name")),
                    message="Human-readable message",
                ))
        return issues

    def _has_problem(self, row: dict) -> bool:
        # Check logic
        return False
```

2. **No registration needed** — the engine auto-discovers it.

3. **Add tests**: In `backend/tests/test_rules.py`:

```python
def test_my_rule_valid():
    rule = MyRule()
    issues = rule.validate([{"field_name": "good_value", "_row_number": 1}])
    assert len(issues) == 0

def test_my_rule_invalid():
    rule = MyRule()
    issues = rule.validate([{"field_name": "bad_value", "_row_number": 1}])
    assert len(issues) == 1
    assert issues[0].severity == Severity.WARNING
```

4. **Add a test fixture** (optional): Create a sample file in `backend/tests/fixtures/`.

5. **Update documentation**: Add the rule to `10-VALIDATION-RULES.md`.

---

## Adding a New API Endpoint

1. **Choose the right router**: `api/auth.py`, `api/uploads.py`, `api/validations.py`, or `api/chat.py`

2. **Add the route handler**:

```python
@router.get("/my-endpoint")
async def my_endpoint(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    # Logic here
    return {"result": "value"}
```

3. **Add Pydantic schemas** (if needed) in `schemas/`.

4. **Add tests** in `tests/test_api.py`.

---

## Adding a New Frontend Page

1. **Create the page**: `src/pages/MyPage.tsx`

```tsx
export default function MyPage() {
  return (
    <div className="container mx-auto p-6">
      <h1 className="text-2xl font-bold">My Page</h1>
    </div>
  )
}
```

2. **Add the route** in `App.tsx`:

```tsx
<Route
  path="/my-page"
  element={
    <ProtectedRoute>
      <MyPage />
    </ProtectedRoute>
  }
/>
```

3. **Add navigation** in `Layout.tsx` (if needed).

---

## Adding a New UI Component

For shadcn/ui components:

```bash
npx shadcn@latest add <component-name>
```

For custom components, create in `src/components/`.

---

## Git Workflow

### Branch Strategy

- `main` — production-ready code
- Feature branches: `feature/description`
- Bug fixes: `fix/description`

### Commit Messages

Follow conventional commits:

```
feat: add new validation rule for currency consistency
fix: correct amount tolerance in batch validation
docs: update API reference with new endpoint
test: add tests for date validation edge cases
refactor: extract parser logic into utility function
```

### Before Committing

```bash
# Backend
cd royalties/backend
ruff check app/
python -m pytest tests/ -v

# Frontend
cd royalties/frontend
npm run lint
npm run build
```

---

## Project Structure Conventions

### Backend

```
app/
├── api/           # Route handlers only (thin, delegate to services)
├── db/            # Database config + session factory
├── models/        # SQLAlchemy ORM models (one file per table)
├── schemas/       # Pydantic request/response models
├── services/      # Business logic (no HTTP concerns)
└── validation/    # Validation engine + rule plugins
    ├── rules/     # One file per rule
    ├── engine.py  # Rule discovery + execution
    ├── parser.py  # File format parsing
    └── base_rule.py  # Abstract base + dataclasses
```

### Frontend

```
src/
├── components/    # Shared components used across pages
│   └── ui/        # shadcn/ui primitives
├── pages/         # Route-level page components
├── features/      # Self-contained feature modules
│   ├── ai-chat/   # Chat components, hooks, types
│   └── uploads/   # Upload components, hooks, API, utils
├── lib/           # Utility functions
├── api.ts         # Centralized HTTP client
└── types.ts       # Shared TypeScript types
```

### Principles

1. **Route handlers are thin**: They validate input, call services, return responses
2. **Services contain business logic**: No HTTP concerns, no direct DB queries
3. **Rules are plugins**: Auto-discovered, no global registration
4. **Feature modules are self-contained**: Own components, hooks, types, API calls
5. **No global state library**: Use React Context for cross-cutting concerns, local hooks for feature state
