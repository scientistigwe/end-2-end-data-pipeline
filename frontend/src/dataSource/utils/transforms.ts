import type { 
  PreviewData, 
  SchemaInfo 
} from '../types/dataSources';

interface DataRow {
  [key: string]: unknown;
}

export const transformPreviewData = (data: DataRow[], schema: SchemaInfo): PreviewData => {
  const fields = schema.tables[0].columns.map(column => ({
    name: column.name,
    type: column.type
  }));

  return {
    fields,
    data: data.map(row => {
      const typedRow: Record<string, unknown> = {};
      fields.forEach(field => {
        const rawValue = row[field.name];
        typedRow[field.name] = transformValueByType(rawValue, field.type);
      });
      return typedRow;
    }),
    totalRows: data.length
  };
};

export const transformValueByType = (value: unknown, type: string): unknown => {
  if (value === null || value === undefined) return null;

  switch (type.toLowerCase()) {
    case 'number':
    case 'integer':
    case 'float':
    case 'double':
      return typeof value === 'number' ? value : Number(value);
    case 'boolean':
      return typeof value === 'boolean' ? value : Boolean(value);
    case 'date':
    case 'timestamp':
      return typeof value === 'string' 
        ? new Date(value).toISOString() 
        : new Date(String(value)).toISOString();
    default:
      return String(value);
  }
};

export const validateDataType = (value: unknown, type: string): boolean => {
  try {
    const transformed = transformValueByType(value, type);
    return transformed !== null && !Number.isNaN(transformed);
  } catch {
    return false;
  }
};