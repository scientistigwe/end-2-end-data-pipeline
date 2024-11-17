import { useState } from "react";
import ApiClient from "../utils/api-client";

const useFileSource = (baseURL) => {
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);
  const apiClient = new ApiClient(baseURL);

  const handleApiRequest = async (formData, actionType) => {
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      if (actionType === "upload") {
        if (!formData.get("files")) {
          throw new Error("No files selected.");
        }

        const result = await apiClient.postFileSource(formData);
        setResponse(result);
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
