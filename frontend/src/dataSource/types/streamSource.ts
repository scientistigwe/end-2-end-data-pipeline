// src/dataSource/types/streamSource.ts

import type { BaseDataSourceConfig, BaseMetadata, DataSourceType } from './base';

export interface StreamSourceConfig extends BaseDataSourceConfig {
    type: DataSourceType.STREAM;
    config: {
        protocol: 'kafka' | 'rabbitmq' | 'mqtt' | 'redis';
        connection: {
            hosts: string[];
            port?: number;
            options?: {
                keepAlive?: boolean;
                connectTimeout?: number;
                requestTimeout?: number;
                reconnectInterval?: number;
                maxRetries?: number;
            };
        };
        auth?: {
            username?: string;
            password?: string;
            ssl?: boolean;
            certificates?: {
                ca?: string;
                cert?: string;
                key?: string;
                passphrase?: string;
            };
        };
        topics?: string[];
        consumer?: {
            groupId?: string;
            autoCommit?: boolean;
            maxBatchSize?: number;
            maxWaitTime?: number;
            fromBeginning?: boolean;
            partitionAssignment?: 'range' | 'roundrobin';
        };
        producer?: {
            acks?: number;
            compression?: 'none' | 'gzip' | 'snappy' | 'lz4';
            batchSize?: number;
            retries?: number;
            idempotent?: boolean;
        };
        schema?: {
            registry?: string;
            format?: 'avro' | 'json' | 'protobuf';
            definition?: string;
            version?: number;
        };
    };
}

export interface StreamMetadata extends BaseMetadata {
    type: DataSourceType.STREAM;
    stats: {
        protocol: string;
        topicCount: number;
        connectedTime: string;
        metrics: {
            messagesPerSecond: number;
            bytesPerSecond: number;
            totalMessages: number;
            errorRate: number;
            latency: number;
            consumerLag?: number;
            partitions?: {
                total: number;
                active: number;
            };
        };
        health: {
            status: 'healthy' | 'degraded' | 'unhealthy';
            lastCheck: string;
            issues?: Array<{
                type: string;
                message: string;
                severity: 'warning' | 'error';
            }>;
        };
    };
}

export interface StreamMessage {
    key?: string | Buffer;
    value: unknown;
    topic: string;
    partition: number;
    offset: string | number;
    timestamp: string;
    headers?: Record<string, string>;
}

export interface TopicInfo {
    name: string;
    partitions: number;
    replicas: number;
    configs: Record<string, string>;
    metrics: {
        messagesPerSecond: number;
        bytesPerSecond: number;
        retentionMs: number;
        sizeBytes: number;
    };
}

export interface ConsumerGroupInfo {
    groupId: string;
    members: number;
    topics: string[];
    status: 'stable' | 'rebalancing' | 'dead';
    lag?: Record<string, number>;
}

// Component Props Types
export interface StreamSourceFormProps {
    onSubmit: (config: StreamSourceConfig) => Promise<void>;
    onCancel: () => void;
    initialData?: Partial<StreamSourceConfig>;
    isLoading?: boolean;
    onTest?: (config: Partial<StreamSourceConfig>) => Promise<void>;
}

export interface StreamSourceCardProps {
    id: string;
    metadata: StreamMetadata;
    config: StreamSourceConfig;
    onEdit?: (id: string) => void;
    onDelete?: (id: string) => void;
    onViewMetrics?: (id: string) => void;
}

export interface StreamMonitorProps {
    connectionId: string;
    metadata: StreamMetadata;
    refreshInterval?: number;
    onRefresh?: () => void;
}

export interface MessageViewerProps {
    connectionId: string;
    topic: string;
    onMessageReceived?: (message: StreamMessage) => void;
    filter?: {
        startTime?: string;
        endTime?: string;
        keyPattern?: string;
        valuePattern?: string;
        limit?: number;
    };
}

export interface TopicManagerProps {
    connectionId: string;
    topics: TopicInfo[];
    onCreateTopic?: (name: string, config: Record<string, unknown>) => Promise<void>;
    onDeleteTopic?: (name: string) => Promise<void>;
    onUpdateConfig?: (topic: string, configs: Record<string, string>) => Promise<void>;
}