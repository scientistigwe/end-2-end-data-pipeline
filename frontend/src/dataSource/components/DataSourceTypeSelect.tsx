// src/dataSource/components/DataSourceTypeSelect.tsx

import React from 'react';
import { Select } from '@/common/components/ui/inputs/select';
import { DataSourceType } from '../types/base';
import { DataSourceTypeSelectProps, DATA_SOURCE_OPTIONS } from './types';

export const DataSourceTypeSelect = React.forwardRef<HTMLSelectElement, DataSourceTypeSelectProps>(
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

    return (
      <Select
        ref={ref}
        value={value}
        onChange={handleChange}
        disabled={disabled}
        className={className}
        aria-label="Data source type selector"
      >
        <option key="placeholder" value="" disabled>
          {placeholder}
        </option>
        {DATA_SOURCE_OPTIONS.map(option => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>
    );
  }
);

DataSourceTypeSelect.displayName = 'DataSourceTypeSelect';