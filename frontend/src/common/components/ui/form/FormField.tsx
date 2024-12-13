// src/common/components/ui/form/FormField.tsx
import * as React from "react";
import { Controller, type Control } from "react-hook-form";

interface FormFieldProps {
  name: string;
  control: Control<any>;
  render: (props: { field: any }) => React.ReactElement;
}

export function FormField({ name, control, render, ...props }: FormFieldProps) {
  return (
    <Controller
      name={name}
      control={control}
      render={({ field }) => render({ field })}
      {...props}
    />
  );
}
