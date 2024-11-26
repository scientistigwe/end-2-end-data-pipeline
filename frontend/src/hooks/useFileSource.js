import { useState } from "react";
import ApiClient from "../utils/api-client";
import usePipeline from "./usePipeline";

const useFileSource = () => {
  const baseURL = process.env.REACT_APP_API_BASE_URL || "http://127.0.0.1:5000/api"; // Ensure /api is included
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  // Create ApiClient with the correct base URL
  const apiClient = new ApiClient(baseURL);

  // Use the usePipeline hook with the same apiClient
  const { triggerPipelineMonitoring } = usePipeline(apiClient);

  const handleApiRequest = async (formData, actionType) => {
    try {
      setLoading(true);
      setError(null);
      setResponse(null);

      if (actionType === "upload") {
        if (!formData.get("files")) {
          throw new Error("No files selected.");
        }

        const result = await apiClient.postFileSource(formData);
        setResponse(result);

        // Trigger pipeline monitoring after successful file upload
        triggerPipelineMonitoring();
      } else if (actionType === "metadata") {
        const result = await apiClient.getFileMetadata();
        setResponse(result);
      } else {
        throw new Error("Invalid action type.");
      }
    } catch (err) {
      setError(err.message || "An error occurred during the request.");
      console.error("Error:", err);
    } finally {
      setLoading(false);
    }
  };

  return { handleApiRequest, response, loading, error };
};

export default useFileSource;