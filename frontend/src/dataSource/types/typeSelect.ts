// frontend\src\dataSource\types\typeSelect.ts
import React from 'react';
import { Select } from '@/common/components/ui/inputs/select';

export enum DataSourceType {
  FILE = 'file',
  API = 'api',
  DATABASE = 'database',
  S3 = 's3',
  STREAM = 'stream'
}

interface DataSourceOption {
  value: DataSourceType;
  label: string;
}

interface DataSourceTypeSelectProps {
  value: DataSourceType | '';
  onChange: (value: DataSourceType) => void;
  disabled?: boolean;
  className?: string;
  placeholder?: string;
}

const DATA_SOURCE_OPTIONS: readonly DataSourceOption[] = [
  { value: DataSourceType.FILE, label: 'File Upload' },
  { value: DataSourceType.API, label: 'API' },
  { value: DataSourceType.DATABASE, label: 'Database' },
  { value: DataSourceType.S3, label: 'S3 Storage' },
  { value: DataSourceType.STREAM, label: 'Data Stream' },
] as const;

const DataSourceTypeSelect = React.forwardRef<HTMLSelectElement, DataSourceTypeSelectProps>(
  (props, ref) => {
    const { 
      value, 
      onChange, 
      disabled = false, 
      className, 
      placeholder = 'Select source type' 
    } = props;

    const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
      const newValue = event.target.value;
      if (Object.values(DataSourceType).includes(newValue as DataSourceType)) {
        onChange(newValue as DataSourceType);
      }
    };

    const selectProps = {
      ref,
      value,
      onChange: handleChange,
      disabled,
      className,
      'aria-label': 'Data source type selector'
    };

    return React.createElement(
      Select,
      selectProps,
      [
        React.createElement('option', { 
          key: 'placeholder', 
          value: '', 
          disabled: true 
        }, placeholder),
        ...DATA_SOURCE_OPTIONS.map(option => 
          React.createElement('option', {
            key: option.value,
            value: option.value
          }, option.label)
        )
      ]
    );
  }
);

DataSourceTypeSelect.displayName = 'DataSourceTypeSelect';

export { DataSourceTypeSelect };