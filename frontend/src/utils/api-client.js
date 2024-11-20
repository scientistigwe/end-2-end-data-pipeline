export default class ApiClient {
  constructor(baseURL = "http://127.0.0.1:5000") {
    this.baseURL = baseURL;
  }

  async postFileSource(formData) {
    try {
      // Log the FormData contents before sending
      console.log("Sending FormData contents:");
      for (let [key, value] of formData.entries()) {
        console.log(
          `${key}:`,
          value instanceof File ? `File: ${value.name}` : value
        );
      }

      const response = await fetch(`${this.baseURL}/pipeline-api/file-source`, {
        method: "POST",
        // Remove the Content-Type header to let the browser set it automatically with the boundary
        headers: {
          // Add CORS headers if needed
          Accept: "application/json",
        },
        // Important: Include credentials if you need to handle cookies
        credentials: "include",
        body: formData,
      });

      // Log the raw response for debugging
      console.log("Raw response:", response);

      // Handle non-JSON responses
      const contentType = response.headers.get("content-type");
      if (!contentType || !contentType.includes("application/json")) {
        throw new Error(`Received non-JSON response: ${await response.text()}`);
      }

      const data = await response.json();

      // Log the parsed response data
      console.log("Parsed response data:", data);

      if (!response.ok) {
        throw new Error(
          `HTTP error! Status: ${response.status}, Message: ${
            data.message || "Unknown error"
          }`
        );
      }

      return data;
    } catch (error) {
      console.error("Error details:", {
        message: error.message,
        stack: error.stack,
        cause: error.cause,
      });
      throw error;
    }
  }

  async getFileMetadata() {
    try {
      const response = await fetch(
        `${this.baseURL}/pipeline-api/file-metadata`,
        {
          method: "GET",
          headers: {
            Accept: "application/json",
          },
          credentials: "include",
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          `HTTP error! Status: ${response.status}, Message: ${
            errorData.message || "Unknown error"
          }`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("Error in getFileMetadata:", error);
      throw error;
    }
  }

  async getPipelineStatus() {
    const response = await fetch(`${this.baseURL}/pipeline-api/pipelines/status`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  async startPipeline(config) {
    const response = await fetch(`${this.baseURL}/pipeline-api/pipelines/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(config)
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  async stopPipeline(pipelineId) {
    const response = await fetch(`${this.baseURL}/pipeline-api/pipelines/${pipelineId}/stop`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  async makePipelineDecision(pipelineId, decision) {
    const response = await fetch(`${this.baseURL}/pipeline-api/pipelines/${pipelineId}/decision`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ decision })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  async getPipelineLogs(pipelineId) {
    const response = await fetch(`${this.baseURL}/pipeline-api/pipelines/${pipelineId}/logs`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }
}
