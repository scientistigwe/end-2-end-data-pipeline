// src/dataSource/pages/DataSourceDetails/components.tsx
import React from "react";
import { useApiSource } from "../../hooks/useApiSource";
import { useDBSource } from "../../hooks/useDBSource";
import { useFileSource } from "../../hooks/useFileSource";
import { useS3Source } from "../../hooks/useS3Source";
import { useStreamSource } from "../../hooks/useStreamSource";
import type { ApiSourceConfig, ApiMetadata } from "../../types/apiSource";
import type { DBSourceConfig, DBMetadata } from "../../types/dbSource";
import type { FileSourceConfig, FileMetadata } from "../../types/fileSource";
import type { S3SourceConfig, S3Metadata } from "../../types/s3Source";
import type {
  StreamSourceConfig,
  StreamMetadata,
} from "../../types/streamSource";
import { formatBytes } from "@/dataSource/utils";

export const ApiSourceDetails: React.FC<{
  metadata: ApiMetadata;
  config: ApiSourceConfig;
}> = ({ metadata, config }) => {
  const { connect, disconnect, isConnecting, connectionId } = useApiSource();

  return (
    <section className="rounded-lg border bg-card p-6">
      <h2 className="text-lg font-semibold mb-4">API Configuration</h2>
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <dt className="text-sm font-medium text-muted-foreground">
            Endpoint URL
          </dt>
          <dd className="text-sm break-all">{config.config.url}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-muted-foreground">Method</dt>
          <dd className="text-sm">{config.config.method}</dd>
        </div>
        {config.config.auth && (
          <div>
            <dt className="text-sm font-medium text-muted-foreground">
              Authentication
            </dt>
            <dd className="text-sm capitalize">{config.config.auth.type}</dd>
          </div>
        )}
        {metadata.stats && (
          <>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">
                Last Response Status
              </dt>
              <dd className="text-sm">{metadata.stats.lastResponse?.status}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">
                Average Response Time
              </dt>
              <dd className="text-sm">
                {metadata.stats.averageResponseTime}ms
              </dd>
            </div>
          </>
        )}
      </dl>
    </section>
  );
};

export const DBSourceDetails: React.FC<{
  metadata: DBMetadata;
  config: DBSourceConfig;
}> = ({ metadata, config }) => {
  const { connect, disconnect, executeQuery, isConnecting, schema } =
    useDBSource();

  return (
    <section className="rounded-lg border bg-card p-6">
      <h2 className="text-lg font-semibold mb-4">Database Configuration</h2>
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <dt className="text-sm font-medium text-muted-foreground">
            Database Type
          </dt>
          <dd className="text-sm capitalize">{config.config.type}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-muted-foreground">Host</dt>
          <dd className="text-sm">
            {config.config.host}:{config.config.port}
          </dd>
        </div>
        {metadata.stats && (
          <>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">
                Table Count
              </dt>
              <dd className="text-sm">{metadata.stats.tableCount}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">
                Size
              </dt>
              <dd className="text-sm">{formatBytes(metadata.stats.size)}</dd>
            </div>
          </>
        )}
      </dl>
    </section>
  );
};

export const FileSourceDetails: React.FC<{
  metadata: FileMetadata;
  config: FileSourceConfig;
}> = ({ metadata, config }) => {
  const { upload, isUploading, uploadProgress } = useFileSource();

  return (
    <section className="rounded-lg border bg-card p-6">
      <h2 className="text-lg font-semibold mb-4">File Configuration</h2>
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <dt className="text-sm font-medium text-muted-foreground">
            File Type
          </dt>
          <dd className="text-sm uppercase">{config.config.type}</dd>
        </div>
        {metadata.stats && (
          <>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">
                File Name
              </dt>
              <dd className="text-sm">{metadata.stats.filename}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">
                Size
              </dt>
              <dd className="text-sm">{formatBytes(metadata.stats.size)}</dd>
            </div>
            {metadata.stats.rowCount && (
              <div>
                <dt className="text-sm font-medium text-muted-foreground">
                  Row Count
                </dt>
                <dd className="text-sm">
                  {metadata.stats.rowCount.toLocaleString()}
                </dd>
              </div>
            )}
          </>
        )}
      </dl>
    </section>
  );
};

export const S3SourceDetails: React.FC<{
  metadata: S3Metadata;
  config: S3SourceConfig;
}> = ({ metadata, config }) => {
  const { connect, disconnect, isConnecting, bucketInfo } = useS3Source();

  return (
    <section className="rounded-lg border bg-card p-6">
      <h2 className="text-lg font-semibold mb-4">S3 Configuration</h2>
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <dt className="text-sm font-medium text-muted-foreground">Bucket</dt>
          <dd className="text-sm">{config.config.bucket}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-muted-foreground">Region</dt>
          <dd className="text-sm">{config.config.region}</dd>
        </div>
        {metadata.stats && (
          <>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">
                Total Size
              </dt>
              <dd className="text-sm">
                {formatBytes(metadata.stats.totalSize)}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">
                Object Count
              </dt>
              <dd className="text-sm">
                {metadata.stats.objectCount.toLocaleString()}
              </dd>
            </div>
          </>
        )}
      </dl>
    </section>
  );
};

export const StreamSourceDetails: React.FC<{
  metadata: StreamMetadata;
  config: StreamSourceConfig;
}> = ({ metadata, config }) => {
  const { connect, disconnect, isConnecting, metrics } = useStreamSource();

  return (
    <section className="rounded-lg border bg-card p-6">
      <h2 className="text-lg font-semibold mb-4">Stream Configuration</h2>
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <dt className="text-sm font-medium text-muted-foreground">
            Protocol
          </dt>
          <dd className="text-sm uppercase">{config.config.protocol}</dd>
        </div>
        {metadata.stats && (
          <>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">
                Messages/Second
              </dt>
              <dd className="text-sm">
                {metadata.stats.messagesPerSecond.toFixed(2)}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">
                Bytes/Second
              </dt>
              <dd className="text-sm">
                {formatBytes(metadata.stats.bytesPerSecond)}/s
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-muted-foreground">
                Total Messages
              </dt>
              <dd className="text-sm">
                {metadata.stats.totalMessages.toLocaleString()}
              </dd>
            </div>
          </>
        )}
      </dl>
    </section>
  );
};
