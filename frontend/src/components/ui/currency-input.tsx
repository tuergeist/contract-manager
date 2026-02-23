import * as React from "react"
import { cn } from "@/lib/utils"

interface CurrencyInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type' | 'value' | 'onChange'> {
  value: string
  onChange: (value: string) => void
}

/**
 * Currency input that displays/accepts comma as decimal separator (German format)
 * but emits dot-decimal string values for GraphQL compatibility.
 */
const CurrencyInput = React.forwardRef<HTMLInputElement, CurrencyInputProps>(
  ({ className, value, onChange, onBlur, ...props }, ref) => {
    const [displayValue, setDisplayValue] = React.useState(() =>
      dotToComma(value)
    )

    // Sync display when external value changes (e.g. reset)
    React.useEffect(() => {
      setDisplayValue(dotToComma(value))
    }, [value])

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const raw = e.target.value
      // Allow digits, comma, dot (as thousand sep or decimal), minus
      if (raw !== '' && !/^-?[\d.,]*$/.test(raw)) return
      setDisplayValue(raw)
      // Emit dot-decimal value
      onChange(commaToDot(raw))
    }

    const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
      // Normalize to 2 decimal places on blur
      const num = parseFloat(commaToDot(displayValue))
      if (!isNaN(num)) {
        const normalized = num.toFixed(2)
        setDisplayValue(dotToComma(normalized))
        onChange(normalized)
      }
      onBlur?.(e)
    }

    return (
      <input
        type="text"
        inputMode="decimal"
        className={cn(
          "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
          className
        )}
        ref={ref}
        value={displayValue}
        onChange={handleChange}
        onBlur={handleBlur}
        {...props}
      />
    )
  }
)
CurrencyInput.displayName = "CurrencyInput"

/** Convert dot-decimal to comma-decimal for display: "1234.56" → "1234,56" */
function dotToComma(value: string): string {
  if (!value) return ''
  return value.replace('.', ',')
}

/** Convert comma-decimal to dot-decimal for backend: "1234,56" → "1234.56" */
function commaToDot(value: string): string {
  // Remove thousand-separator dots, then convert decimal comma to dot
  return value.replace(/\./g, '').replace(',', '.')
}

export { CurrencyInput }
