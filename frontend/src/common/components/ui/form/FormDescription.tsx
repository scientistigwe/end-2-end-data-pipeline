// src/common/components/ui/form/FormDescription.tsx
import * as React from "react"
import { cn } from "@/common/utils/cn"

export interface FormDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {}

export const FormDescription = React.forwardRef<HTMLParagraphElement, FormDescriptionProps>(
  ({ className, ...props }, ref) => {
    return (
      <p
        ref={ref}
        className={cn("text-sm text-gray-500", className)}
        {...props}
      />
    )
  }
)

FormDescription.displayName = "FormDescription"