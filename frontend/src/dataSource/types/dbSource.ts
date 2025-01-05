// src/dataSource/types/dbSource.ts

import type { BaseDataSourceConfig, BaseMetadata, DataSourceType } from './base';

export interface DBSourceConfig extends BaseDataSourceConfig {
    type: DataSourceType.DATABASE;
    config: {
        type: 'postgresql' | 'mysql' | 'mongodb' | 'oracle';
        host: string;
        port: number;
        database: string;
        username: string;
        password: string;
        ssl?: boolean;
        schema?: string;
        options?: {
            timezone?: string;
            connectionTimeout?: number;
            queryTimeout?: number;
            poolSize?: number;
            maxConnections?: number;
            keepAlive?: boolean;
            enableSsl?: boolean;
            sslMode?: 'disable' | 'require' | 'verify-ca' | 'verify-full';
            sslCert?: string;
            sslKey?: string;
            sslRootCert?: string;
        };
    };
}

export interface DBMetadata extends BaseMetadata {
    type: DataSourceType.DATABASE;
    stats: {
        tableCount: number;
        schemaCount: number;
        size: number;
        lastSync: string;
        connectionStatus: string;
        version?: string;
        uptime?: number;
        activeConnections?: number;
        deadlockCount?: number;
        cacheHitRatio?: number;
    };
}

export interface DBSchema {
    tables: Array<{
        name: string;
        schema: string;
        type: string;
        columns: Array<{
            name: string;
            type: string;
            nullable: boolean;
            primaryKey: boolean;
            defaultValue?: string;
            description?: string;
        }>;
        foreignKeys: Array<{
            columnNames: string[];
            referencedTable: string;
            referencedColumns: string[];
            onDelete?: string;
            onUpdate?: string;
        }>;
        indexes: Array<{
            name: string;
            columns: string[];
            unique: boolean;
            type?: string;
        }>;
        rowCount?: number;
        sizeBytes?: number;
    }>;
    views: Array<{
        name: string;
        schema: string;
        definition: string;
        materialized: boolean;
    }>;
    functions: Array<{
        name: string;
        schema: string;
        returnType: string;
        arguments: Array<{
            name: string;
            type: string;
            defaultValue?: string;
        }>;
    }>;
}

export interface QueryResult {
    rows: unknown[];
    rowCount: number;
    fields: Array<{
        name: string;
        type: string;
        nullable: boolean;
    }>;
    execution: {
        duration: number;
        startTime: string;
        endTime: string;
        status: 'success' | 'error' | 'cancelled';
    };
}

export interface DBConnectionDetails {
    id: string;
    status: 'connected' | 'disconnected' | 'error';
    connectedAt: string;
    disconnectedAt?: string;
    error?: string;
    metrics?: {
        queryCount: number;
        activeQueries: number;
        avgQueryTime: number;
        slowQueries: number;
    };
}

// Component Props Types
export interface DBSourceFormProps {
    onSubmit: (config: DBSourceConfig) => Promise<void>;
    onCancel: () => void;
    initialData?: Partial<DBSourceConfig>;
    isLoading?: boolean;
}

export interface DBSourceCardProps {
    id: string;
    metadata: DBMetadata;
    config: DBSourceConfig;
    onEdit?: (id: string) => void;
    onDelete?: (id: string) => void;
    onConnect?: (id: string) => void;
    onDisconnect?: (id: string) => void;
}

export interface QueryEditorProps {
    connectionId: string;
    initialQuery?: string;
    schema?: DBSchema;
    onExecute: (query: string) => Promise<QueryResult>;
    onError?: (error: Error) => void;
}

export interface SchemaExplorerProps {
    connectionId: string;
    schema: DBSchema;
    onTableSelect?: (tableName: string) => void;
    onRefresh?: () => void;
}