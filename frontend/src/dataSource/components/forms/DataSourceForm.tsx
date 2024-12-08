// src/components/dataSource.tsx
import { useForm, UseFormRegister } from "react-hook-form";
import {
  Card,
  CardHeader,
  CardContent,
  CardFooter,
} from "../../../../components/ui/card";
import { Input } from "../../../../components/ui/input";
import { Button } from "../../../../components/ui/button";
import { Select } from "../../../../components/ui/select";
import { Textarea } from "../../../../components/ui/textarea";
import { Switch } from "../../../../components/ui/switch";
import type {
  DataSourceConfig,
  FileSourceConfig,
  ApiSourceConfig,
  DBSourceConfig,
  S3SourceConfig,
  StreamSourceConfig,
  DataSourceType,
} from "../../types/dataSources";

type SourceRegister<T extends DataSourceConfig> = UseFormRegister<T>;

const FileSourceFields = ({
  register,
}: {
  register: SourceRegister<FileSourceConfig>;
}) => (
  <div className="space-y-4">
    <Select {...register("config.type", { required: true })}>
      <option value="csv">CSV</option>
      <option value="json">JSON</option>
      <option value="parquet">Parquet</option>
      <option value="excel">Excel</option>
    </Select>
    <Input {...register("config.delimiter")} placeholder="," />
    <Input {...register("config.encoding")} defaultValue="utf-8" />
    <Switch {...register("config.hasHeader")} />
  </div>
);

const S3SourceFields = ({
  register,
}: {
  register: SourceRegister<S3SourceConfig>;
}) => (
  <div className="space-y-4">
    <Input {...register("config.bucket")} placeholder="Bucket name" />
    <Input {...register("config.region")} placeholder="Region" />
    <Input {...register("config.accessKeyId")} type="password" />
    <Input {...register("config.secretAccessKey")} type="password" />
    <Input {...register("config.prefix")} placeholder="Prefix (optional)" />
    <Switch {...register("config.sslEnabled")} />
  </div>
);

const DatabaseSourceFields = ({
  register,
}: {
  register: SourceRegister<DBSourceConfig>;
}) => (
  <div className="space-y-4">
    <Select {...register("config.type")}>
      <option value="postgresql">PostgreSQL</option>
      <option value="mysql">MySQL</option>
      <option value="mongodb">MongoDB</option>
      <option value="oracle">Oracle</option>
    </Select>
    <Input {...register("config.host")} placeholder="Host" />
    <Input {...register("config.port")} type="number" />
    <Input {...register("config.database")} placeholder="Database name" />
    <Input {...register("config.username")} placeholder="Username" />
    <Input {...register("config.password")} type="password" />
    <Input {...register("config.schema")} placeholder="Schema (optional)" />
    <Switch {...register("config.ssl")} />
  </div>
);

const StreamSourceFields = ({
  register,
}: {
  register: SourceRegister<StreamSourceConfig>;
}) => (
  <div className="space-y-4">
    <Select {...register("config.protocol")}>
      <option value="kafka">Kafka</option>
      <option value="rabbitmq">RabbitMQ</option>
      <option value="mqtt">MQTT</option>
      <option value="redis">Redis</option>
    </Select>
    <Input
      {...register("config.connection.hosts")}
      placeholder="host1:port,host2:port"
    />
    <Input {...register("config.topics")} placeholder="topic1,topic2" />
    <Input
      {...register("config.consumer.groupId")}
      placeholder="Consumer group ID"
    />
    <Input {...register("config.consumer.maxBatchSize")} type="number" />
    <Switch {...register("config.auth.ssl")} />
  </div>
);

const ApiSourceFields = ({
  register,
}: {
  register: SourceRegister<ApiSourceConfig>;
}) => (
  <div className="space-y-4">
    <Input {...register("config.url")} placeholder="API URL" />
    <Select {...register("config.method")}>
      <option value="GET">GET</option>
      <option value="POST">POST</option>
      <option value="PUT">PUT</option>
      <option value="DELETE">DELETE</option>
    </Select>
    <Textarea {...register("config.headers")} placeholder="Headers (JSON)" />
    <Select {...register("config.auth.type")}>
      <option value="basic">Basic</option>
      <option value="bearer">Bearer</option>
      <option value="oauth2">OAuth 2.0</option>
    </Select>
  </div>
);

const SourceFields = ({
  type,
  register,
}: {
  type: DataSourceType;
  register: UseFormRegister<DataSourceConfig>;
}) => {
  switch (type) {
    case "file":
      return (
        <FileSourceFields
          register={register as SourceRegister<FileSourceConfig>}
        />
      );
    case "api":
      return (
        <ApiSourceFields
          register={register as SourceRegister<ApiSourceConfig>}
        />
      );
    case "database":
      return (
        <DatabaseSourceFields
          register={register as SourceRegister<DBSourceConfig>}
        />
      );
    case "s3":
      return (
        <S3SourceFields register={register as SourceRegister<S3SourceConfig>} />
      );
    case "stream":
      return (
        <StreamSourceFields
          register={register as SourceRegister<StreamSourceConfig>}
        />
      );
    default:
      return null;
  }
};

export const DataSourceForm = ({
  initialData,
  onSubmit,
  onCancel,
  isLoading,
}: {
  initialData?: DataSourceConfig;
  onSubmit: (data: DataSourceConfig) => void;
  onCancel: () => void;
  isLoading?: boolean;
}) => {
  const form = useForm<DataSourceConfig>({ defaultValues: initialData });
  const { register, handleSubmit, watch } = form;
  const sourceType = watch("type") as DataSourceType;

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <Card>
        <CardHeader>
          <h3 className="text-lg font-medium">
            {initialData ? "Edit" : "New"} Data Source
          </h3>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input {...register("name")} placeholder="Name" />
          <Select {...register("type")} disabled={!!initialData}>
            <option value="file">File</option>
            <option value="api">API</option>
            <option value="database">Database</option>
            <option value="s3">S3</option>
            <option value="stream">Stream</option>
          </Select>
          <Textarea {...register("description")} placeholder="Description" />
          {sourceType && <SourceFields type={sourceType} register={register} />}
        </CardContent>
        <CardFooter className="flex justify-end space-x-4">
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={isLoading}>
            {isLoading ? "Saving..." : "Save"}
          </Button>
        </CardFooter>
      </Card>
    </form>
  );
};
