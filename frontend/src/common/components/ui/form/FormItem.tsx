// src/common/components/ui/form/FormItem.tsx
import * as React from "react"
import { cn } from "@/common/utils/cn"

export interface FormItemProps extends React.HTMLAttributes<HTMLDivElement> {}

export const FormItem = React.forwardRef<HTMLDivElement, FormItemProps>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn("space-y-2", className)}
        {...props}
      />
    )
  }
)

FormItem.displayName = "FormItem"