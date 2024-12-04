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
      const cleanData = JSON.parse(JSON.stringify(data), (key, value) => {
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
          // Upload file
          const result = await apiClient.postFileSource(formData);

          // Parse and validate response
          const parsedResult = safeParseResponse(result);
          if (!parsedResult) {
            throw new Error("Failed to parse file upload response");
          }

          // Handle successful upload
          setResponse(parsedResult);

          // Check if upload was successful before triggering pipeline
          if (parsedResult.status === 'success') {
            console.log('File upload successful, triggering pipeline monitoring');
            triggerPipelineMonitoring();
          } else {
            console.warn('File upload completed but status was not success:', parsedResult.status);
          }

          return parsedResult; // Return for component use if needed

        } catch (uploadError) {
          console.error('File upload error:', uploadError);
          const errorMessage = uploadError.message || "File upload failed";
          setError({
            message: errorMessage,
            details: uploadError.response || uploadError
          });
          throw uploadError; // Re-throw for component handling
        }

      } else if (actionType === "metadata") {
        const result = await apiClient.getFileMetadata();
        const parsedResult = safeParseResponse(result);

        if (parsedResult) {
          setResponse(parsedResult);
          return parsedResult;
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
      throw error; // Allow components to handle errors

    } finally {
      setLoading(false);
    }
  };

  const uploadFile = async (formData) => {
    try {
      const result = await handleApiRequest(formData, "upload");
      return result;
    } catch (error) {
      console.error('Upload failed:', error);
      throw error;
    }
  };

  const getMetadata = async () => {
    try {
      const result = await handleApiRequest(null, "metadata");
      return result;
    } catch (error) {
      console.error('Metadata fetch failed:', error);
      throw error;
    }
  };

  return {
    uploadFile,
    getMetadata,
    response,
    loading,
    error,
  };
};

export default useFileSource;