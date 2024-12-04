// src/components/forms/APISourceForm.tsx
import { useForm } from 'react-hook-form';
import { useApiSource } from '../../hooks/sources/useApiSource';

interface APISourceFormData {
  url: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  headers?: Record<string, string>;
  body?: string;
}

export const APISourceForm: React.FC = () => {
  const { connect } = useApiSource();
  const { register, handleSubmit } = useForm<APISourceFormData>();

  const onSubmit = (data: APISourceFormData) => {
    connect(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* Form fields */}
    </form>
  );
};
