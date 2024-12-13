// src/analysis/pages/AnalysisPage.tsx
import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/common/components/ui/tabs";
import { Alert, AlertDescription } from "@/common/components/ui/alert";
import { useAnalysis } from "../hooks/useAnalysis";
import { useAnalysisDetails } from "../hooks/useAnalysisDetails";
import { AnalysisForm } from "../components/forms/AnalysisForm";
import { AnalysisStatus } from "../components/status/AnalysisStatus";
import { QualityReport } from "../components/reports/QualityReport";
import { InsightReport } from "../components/reports/InsightReport";
import type { 
  QualityConfig, 
  InsightConfig, 
  AnalysisFormConfig 
} from "../types/analysis";

const AnalysisPage: React.FC = () => {
  const { analysisId } = useParams();
  const [activeTab, setActiveTab] = useState<"quality" | "insight">("quality");
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    selectedAnalysis,
    selectedQualityReport,
    selectedInsightReport,
    startQualityAnalysis,
    startInsightAnalysis,
    getQualityReport,
    getInsightReport,
    pollAnalysisStatus
  } = useAnalysis();

  const {
    getCorrelations,
    getAnomalies,
    getTrends
  } = useAnalysisDetails();

  useEffect(() => {
    if (analysisId) {
      pollAnalysisStatus(analysisId).catch(err => {
        setError("Failed to load analysis status");
        console.error(err);
      });
    }
  }, [analysisId, pollAnalysisStatus]);

  const handleSubmit = async (config: AnalysisFormConfig) => {
    setIsStarting(true);
    setError(null);
    
    try {
      if (config.type === "quality") {
        const analysis = await startQualityAnalysis(config);
        await pollAnalysisStatus(analysis.id);
        await getQualityReport(analysis.id);
      } else {
        const analysis = await startInsightAnalysis(config);
        await pollAnalysisStatus(analysis.id);
        await Promise.all([
          getInsightReport(analysis.id),
          getCorrelations(analysis.id),
          getAnomalies(analysis.id),
          getTrends(analysis.id)
        ]);
      }
    } catch (err) {
      setError(`Failed to start ${config.type} analysis`);
      console.error(err);
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      <header className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Analysis</h1>
      </header>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Tabs 
        value={activeTab} 
        onValueChange={(value) => setActiveTab(value as "quality" | "insight")}
      >
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="quality">Quality Analysis</TabsTrigger>
          <TabsTrigger value="insight">Insight Analysis</TabsTrigger>
        </TabsList>

        <TabsContent value="quality" className="space-y-6">
          <AnalysisForm
            type="quality"
            onSubmit={handleSubmit}
            isLoading={isStarting}
          />
          {selectedAnalysis && (
            <AnalysisStatus analysis={selectedAnalysis} />
          )}
          {selectedQualityReport && (
            <QualityReport report={selectedQualityReport} />
          )}
        </TabsContent>

        <TabsContent value="insight" className="space-y-6">
          <AnalysisForm
            type="insight"
            onSubmit={handleSubmit}
            isLoading={isStarting}
          />
          {selectedAnalysis && (
            <AnalysisStatus analysis={selectedAnalysis} />
          )}
          {selectedInsightReport && (
            <InsightReport report={selectedInsightReport} />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AnalysisPage;