import React from "react";
import { useForm } from "react-hook-form";
import { Card, CardContent, CardFooter, CardHeader } from "../ui/card";
import { Input } from "../ui/input";
import { Button } from "../ui/button";
import { Select } from "../ui/select";
import { Textarea } from "../ui/textarea";
import { useApiSource } from "../../dataSource/hooks/useApiSource";
import type { ApiSourceConfig } from "../../dataSource/types/dataSources";

type AuthType = "none" | "basic" | "bearer" | "oauth2";

interface APISourceFormData {
  url: string;
  method: "GET" | "POST" | "PUT" | "DELETE";
  headers?: string; // JSON string
  params?: string; // JSON string
  body?: string;
  auth: {
    type: AuthType;
    credentials?: {
      username?: string;
      password?: string;
      token?: string;
      clientId?: string;
      clientSecret?: string;
      tokenUrl?: string;
    };
  };
  rateLimit?: {
    requests: number;
    period: number;
  };
}

export const APISourceForm: React.FC = () => {
  const { connect, isConnecting } = useApiSource();
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<APISourceFormData>({
    defaultValues: {
      method: "GET",
      auth: {
        type: "none" as AuthType,
      },
    },
  });

  const authType = watch("auth.type");
  const method = watch("method");

  const onSubmit = (data: APISourceFormData) => {
    const config: ApiSourceConfig["config"] = {
      url: data.url,
      method: data.method,
      headers: data.headers ? JSON.parse(data.headers) : undefined,
      params: data.params ? JSON.parse(data.params) : undefined,
      body: data.body ? JSON.parse(data.body) : undefined,
      auth:
        data.auth.type !== "none"
          ? {
              type: data.auth.type,
              credentials: data.auth.credentials || {},
            }
          : undefined,
      rateLimit: data.rateLimit,
    };

    connect(config);
  };

  return (
    <Card>
      <CardHeader>
        <h3 className="text-lg font-medium">API Configuration</h3>
      </CardHeader>
      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-4">
          {/* URL Input */}
          <div className="space-y-2">
            <label className="text-sm font-medium">URL</label>
            <Input
              {...register("url", {
                required: "API URL is required",
                pattern: {
                  value: /^https?:\/\/.+/,
                  message:
                    "Must be a valid URL starting with http:// or https://",
                },
              })}
              placeholder="https://api.example.com/v1"
            />
            {errors.url && (
              <p className="text-sm text-red-500">{errors.url.message}</p>
            )}
          </div>

          {/* Method Select */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Method</label>
            <Select {...register("method", { required: true })}>
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="DELETE">DELETE</option>
            </Select>
          </div>

          {/* Headers */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Headers (JSON)</label>
            <Textarea
              {...register("headers", {
                validate: (value) => {
                  if (!value) return true;
                  try {
                    JSON.parse(value);
                    return true;
                  } catch {
                    return "Must be valid JSON";
                  }
                },
              })}
              placeholder='{"Content-Type": "application/json"}'
              rows={3}
            />
            {errors.headers && (
              <p className="text-sm text-red-500">{errors.headers.message}</p>
            )}
          </div>

          {/* Query Parameters */}
          <div className="space-y-2">
            <label className="text-sm font-medium">
              Query Parameters (JSON)
            </label>
            <Textarea
              {...register("params", {
                validate: (value) => {
                  if (!value) return true;
                  try {
                    JSON.parse(value);
                    return true;
                  } catch {
                    return "Must be valid JSON";
                  }
                },
              })}
              placeholder='{"key": "value"}'
              rows={3}
            />
            {errors.params && (
              <p className="text-sm text-red-500">{errors.params.message}</p>
            )}
          </div>

          {/* Request Body */}
          {(method === "POST" || method === "PUT") && (
            <div className="space-y-2">
              <label className="text-sm font-medium">Request Body (JSON)</label>
              <Textarea
                {...register("body", {
                  validate: (value) => {
                    if (!value) return true;
                    try {
                      JSON.parse(value);
                      return true;
                    } catch {
                      return "Must be valid JSON";
                    }
                  },
                })}
                placeholder='{"key": "value"}'
                rows={4}
              />
              {errors.body && (
                <p className="text-sm text-red-500">{errors.body.message}</p>
              )}
            </div>
          )}

          {/* Authentication */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Authentication</label>
            <Select {...register("auth.type")}>
              <option value="none">None</option>
              <option value="basic">Basic Auth</option>
              <option value="bearer">Bearer Token</option>
              <option value="oauth2">OAuth 2.0</option>
            </Select>
          </div>

          {/* Auth Type Specific Fields */}
          {authType === "basic" && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Username</label>
                <Input
                  {...register("auth.credentials.username", {
                    required: "Username is required for Basic Auth",
                  })}
                />
                {errors.auth?.credentials?.username && (
                  <p className="text-sm text-red-500">
                    {errors.auth.credentials.username.message}
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Password</label>
                <Input
                  type="password"
                  {...register("auth.credentials.password", {
                    required: "Password is required for Basic Auth",
                  })}
                />
                {errors.auth?.credentials?.password && (
                  <p className="text-sm text-red-500">
                    {errors.auth.credentials.password.message}
                  </p>
                )}
              </div>
            </div>
          )}

          {authType === "bearer" && (
            <div className="space-y-2">
              <label className="text-sm font-medium">Token</label>
              <Input
                {...register("auth.credentials.token", {
                  required: "Token is required for Bearer Auth",
                })}
                placeholder="Bearer token"
              />
              {errors.auth?.credentials?.token && (
                <p className="text-sm text-red-500">
                  {errors.auth.credentials.token.message}
                </p>
              )}
            </div>
          )}

          {authType === "oauth2" && (
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Client ID</label>
                <Input
                  {...register("auth.credentials.clientId", {
                    required: "Client ID is required for OAuth",
                  })}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Client Secret</label>
                <Input
                  type="password"
                  {...register("auth.credentials.clientSecret", {
                    required: "Client Secret is required for OAuth",
                  })}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Token URL</label>
                <Input
                  {...register("auth.credentials.tokenUrl", {
                    required: "Token URL is required for OAuth",
                  })}
                />
              </div>
            </div>
          )}

          {/* Rate Limiting */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Rate Limiting</label>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Requests</label>
                <Input
                  type="number"
                  {...register("rateLimit.requests", {
                    valueAsNumber: true,
                    min: { value: 1, message: "Must be at least 1" },
                  })}
                  placeholder="Requests per period"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Period (seconds)</label>
                <Input
                  type="number"
                  {...register("rateLimit.period", {
                    valueAsNumber: true,
                    min: { value: 1, message: "Must be at least 1" },
                  })}
                  placeholder="Time period in seconds"
                />
              </div>
            </div>
          </div>
        </CardContent>

        <CardFooter>
          <Button type="submit" disabled={isConnecting}>
            {isConnecting ? "Connecting..." : "Connect API"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};
