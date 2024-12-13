// src/common/components/ui/form/FormMessage.tsx
import * as React from "react"
import { cn } from "@/common/utils/cn"

export interface FormMessageProps extends React.HTMLAttributes<HTMLParagraphElement> {}

export const FormMessage = React.forwardRef<HTMLParagraphElement, FormMessageProps>(
  ({ className, children, ...props }, ref) => {
    if (!children) return null

    return (
      <p
        ref={ref}
        className={cn("text-sm font-medium text-red-500", className)}
        {...props}
      >
        {children}
      </p>
    )
  }
)

FormMessage.displayName = "FormMessage"