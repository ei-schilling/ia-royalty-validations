import { Sun, Moon, Monitor } from 'lucide-react'
import { useTheme } from '@/components/ThemeProvider'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

const modes = [
  { value: 'light' as const, icon: Sun, label: 'Light' },
  { value: 'dark' as const, icon: Moon, label: 'Dark' },
  { value: 'system' as const, icon: Monitor, label: 'System' },
]

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  // Cycle: dark → light → system → dark
  function cycle() {
    const order = ['dark', 'light', 'system'] as const
    const idx = order.indexOf(theme)
    setTheme(order[(idx + 1) % order.length])
  }

  const current = modes.find((m) => m.value === theme) ?? modes[1]
  const Icon = current.icon

  return (
    <TooltipProvider delayDuration={300}>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={cycle}
            className="text-muted-foreground hover:text-foreground"
          >
            <Icon className="h-3.5 w-3.5" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="text-xs">
          {current.label} mode
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
