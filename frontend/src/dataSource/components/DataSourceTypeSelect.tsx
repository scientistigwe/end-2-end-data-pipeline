import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Settings,
  Trash2,
  RefreshCw,
  Database,
  FileText,
  Cloud,
  Network,
  Radio,
  ChevronRight,
  MoreHorizontal,
} from "lucide-react";
import { Card, CardContent, CardHeader } from "@/common/components/ui/card";
import { Badge } from "@/common/components/ui/badge";
import { Button } from "@/common/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/common/components/ui/dropdown-menu";
import { Dialog, DialogTrigger } from "@/common/components/ui/dialog";
import { ValidationDisplay } from "./validation";
import { formatBytes } from "@/dataSource/utils";
import { cn } from "@/common/utils";
import type {
  BaseMetadata,
  DataSourceStatus,
  DataSourceType,
} from "../types/base";

interface DataSourceListProps {
  sources: BaseMetadata[];
  onSelect: (id: string) => void;
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
  onSync: (id: string) => void;
  className?: string;
}

const STATUS_STYLES: Record<DataSourceStatus, string> = {
  active: "bg-green-100 text-green-800",
  error: "bg-red-100 text-red-800",
  connecting: "bg-blue-100 text-blue-800",
  inactive: "bg-gray-100 text-gray-800",
  processing: "bg-purple-100 text-purple-800",
  validating: "bg-yellow-100 text-yellow-800",
};

const TYPE_ICONS: Record<DataSourceType, React.ReactNode> = {
  database: <Database className="h-5 w-5" />,
  file: <FileText className="h-5 w-5" />,
  s3: <Cloud className="h-5 w-5" />,
  api: <Network className="h-5 w-5" />,
  stream: <Radio className="h-5 w-5" />,
};

export const DataSourceList: React.FC<DataSourceListProps> = ({
  sources,
  onSelect,
  onEdit,
  onDelete,
  onSync,
  className = "",
}) => {
  const [expandedSourceId, setExpandedSourceId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedSourceId((prev) => (prev === id ? null : id));
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className={cn("space-y-4", className)}
    >
      <AnimatePresence>
        {sources.map((source) => (
          <motion.div
            key={source.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <Card className="overflow-hidden hover:shadow-lg transition-shadow">
              <CardHeader
                onClick={() => onSelect(source.id)}
                className="cursor-pointer p-4 hover:bg-accent/5 transition-colors group"
              >
                <div className="flex justify-between items-center">
                  <div className="flex items-center space-x-3">
                    {TYPE_ICONS[source.type]}
                    <div>
                      <div className="flex items-center space-x-2">
                        <h3 className="text-lg font-medium">{source.name}</h3>
                        <Badge className={STATUS_STYLES[source.status]}>
                          {source.status}
                        </Badge>
                      </div>
                      {source.description && (
                        <p className="text-sm text-muted-foreground">
                          {source.description}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    {/* Dropdown Menu for Actions */}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onSelect={() => onSync(source.id)}
                          className="cursor-pointer"
                        >
                          <RefreshCw className="mr-2 h-4 w-4" />
                          Sync
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onSelect={() => onEdit(source.id)}
                          className="cursor-pointer"
                        >
                          <Settings className="mr-2 h-4 w-4" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onSelect={() => onDelete(source.id)}
                          className="text-destructive cursor-pointer focus:bg-destructive/10"
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>

                    {/* Expand/Collapse Button */}
                    <motion.button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleExpand(source.id);
                      }}
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                      className="text-muted-foreground hover:text-foreground"
                    >
                      <motion.div
                        animate={{
                          rotate: expandedSourceId === source.id ? 90 : 0,
                        }}
                      >
                        <ChevronRight className="h-5 w-5" />
                      </motion.div>
                    </motion.button>
                  </div>
                </div>
              </CardHeader>

              {/* Expandable Details */}
              <AnimatePresence>
                {expandedSourceId === source.id && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{
                      opacity: 1,
                      height: "auto",
                      transition: { duration: 0.3 },
                    }}
                    exit={{
                      opacity: 0,
                      height: 0,
                      transition: { duration: 0.2 },
                    }}
                    className="border-t"
                  >
                    <CardContent className="p-4">
                      {source.error && (
                        <div className="mb-4">
                          <ValidationDisplay
                            validation={{
                              isValid: false,
                              issues: [
                                {
                                  severity: "error",
                                  message: source.error.message,
                                  type: source.error.code || "Error",
                                  field: undefined,
                                },
                              ],
                              warnings: [],
                            }}
                            compact
                          />
                        </div>
                      )}

                      <div className="grid md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <p className="text-muted-foreground">Last Sync</p>
                          <p className="font-medium">
                            {source.lastSync
                              ? new Date(source.lastSync).toLocaleString()
                              : "Never"}
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Type Details</p>
                          <p className="font-medium capitalize">
                            {source.type}
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Created</p>
                          <p className="font-medium">
                            {new Date(source.createdAt).toLocaleString()}
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Updated</p>
                          <p className="font-medium">
                            {new Date(source.updatedAt).toLocaleString()}
                          </p>
                        </div>
                      </div>

                      {source.tags && source.tags.length > 0 && (
                        <div className="mt-4 flex flex-wrap gap-2">
                          {source.tags.map((tag, index) => (
                            <Badge key={index} variant="secondary">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </motion.div>
                )}
              </AnimatePresence>
            </Card>
          </motion.div>
        ))}
      </AnimatePresence>

      {sources.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-8 text-muted-foreground"
        >
          <p>No data sources found</p>
          <p className="text-sm mt-2">Add a new data source to get started</p>
        </motion.div>
      )}
    </motion.div>
  );
};
