// src/hooks/useFileSource.js
import { useState } from "react";
import ApiClient from "../utils/ApiClient";

const useFileSource = (baseURL) => {
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState(null);
  const apiClient = new ApiClient(baseURL);

  const uploadFiles = async (files) => {
    setLoading(true);
    setError(null);

    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));

    try {
      const result = await apiClient.postFileSource(formData);
      setResponse(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchMetadata = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.getFileMetadata();
      setResponse(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return { uploadFiles, fetchMetadata, response, loading, error };
};

export default useFileSource;
