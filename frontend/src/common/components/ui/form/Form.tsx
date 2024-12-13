// src/common/components/ui/form/Form.tsx
import * as React from "react"
import type { UseFormReturn } from "react-hook-form"
import { cn } from "@/common/utils/cn"

interface FormProps<TFormValues extends Record<string, unknown>>
  extends Omit<React.ComponentProps<'form'>, 'onSubmit'> {
  form: UseFormReturn<TFormValues>
  onSubmit: (values: TFormValues) => void
}

export const Form = <TFormValues extends Record<string, unknown>>({
  form,
  onSubmit,
  children,
  className,
  ...props
}: FormProps<TFormValues>) => {
  return (
    <form 
      className={cn(className)}
      {...props} 
      onSubmit={form.handleSubmit(onSubmit)}
    >
      {children}
    </form>
  )
}