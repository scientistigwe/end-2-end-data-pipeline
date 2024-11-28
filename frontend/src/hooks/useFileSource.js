import { useState } from "react";
import ApiClient from "../utils/api-client";
import usePipeline from "./usePipeline";

const useFileSource = () => {
  const baseURL = process.env.REACT_APP_API_BASE_URL || "http://127.0.0.1:5000/api";
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);

  const apiClient = new ApiClient(baseURL);
  const { triggerPipelineMonitoring } = usePipeline(apiClient);

  const safeParseResponse = (data) => {
    try {
      // Handle potential NaN or undefined values
      const cleanData = JSON.parse(JSON.stringify(data), (key, value) => {
        // Replace NaN, null, and undefined with null
        if (value === null || value === 'null' || value === 'NaN' || value === undefined) {
          return null;
        }
        return value;
      });
      return cleanData;
    } catch (parseError) {
      console.error('Response parsing error:', parseError);
      console.error('Original response:', data);
      return null;
    }
  };

  const handleApiRequest = async (formData, actionType) => {
    try {
      setLoading(true);
      setError(null);
      setResponse(null);

      if (actionType === "upload") {
        if (!formData.get("files")) {
          throw new Error("No files selected.");
        }

        try {
          const result = await apiClient.postFileSource(formData);

          // Safely parse the result
          const parsedResult = safeParseResponse(result);

          if (parsedResult) {
            setResponse(parsedResult);
            // Trigger pipeline monitoring after successful file upload
            triggerPipelineMonitoring();
          } else {
            throw new Error("Failed to parse file upload response");
          }
        } catch (uploadError) {
          console.error('File upload error:', uploadError);
          setError({
            message: uploadError.message || "File upload failed",
            details: uploadError.response || uploadError
          });
        }
      } else if (actionType === "metadata") {
        const result = await apiClient.getFileMetadata();
        const parsedResult = safeParseResponse(result);

        if (parsedResult) {
          setResponse(parsedResult);
        } else {
          throw new Error("Failed to parse metadata response");
        }
      } else {
        throw new Error("Invalid action type.");
      }
    } catch (error) {
      console.error('Full error details:', error);
      setError({
        message: error.message || "An unexpected error occurred",
        details: error.response || error
      });
    } finally {
      setLoading(false);
    }
  };

  return { handleApiRequest, response, loading, error };
};

export default useFileSource;