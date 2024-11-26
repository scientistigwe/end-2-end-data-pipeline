export default class ApiClient {
  constructor(baseURL = "http://127.0.0.1:5000/api") {
    this.baseURL = baseURL;
  }

  // Generic error handler
  async handleResponse(response) {
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data.data; // Extract the data from the standardized response
  }

  async postFileSource(formData) {
    try {
      console.log("Sending FormData contents:");

      const response = await fetch(`${this.baseURL}/files/upload`, {
        method: "POST",
        headers: {
          Accept: "application/json",
        },
        credentials: "include",  // Ensure credentials are included
        body: formData,
      });

      const contentType = response.headers.get("content-type");
      if (!contentType || !contentType.includes("application/json")) {
        throw new Error(`Received non-JSON response: ${await response.text()}`);
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}, Message: ${data.message || "Unknown error"}`);
      }

      return data;
    } catch (error) {
      console.error("Error details:", {
        message: error.message,
        stack: error.stack,
        cause: error.cause,
      });

      if (error.message.includes("CORS")) {
        alert("CORS Error: Please ensure the backend allows requests from this origin.");
      }

      throw error;
    }
  }

  async getFileMetadata() {
    try {
      const response = await fetch(`${this.baseURL}/files/metadata`, {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
        credentials: "include",  // Ensure credentials are included
      });

      return await this.handleResponse(response);
    } catch (error) {
      console.error('Error Fetching Metadata:', error);
      if (error.message.includes("CORS")) {
        alert("CORS Error: Please ensure the backend allows requests from this origin.");
      }
      throw error;
    }
  }

  async getPipelineStatus() {
    try {
      const response = await fetch(`${this.baseURL}/pipelines/status`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json', // Ensure content type is correct
        },
        credentials: 'include'  // Ensure credentials are included
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error getting pipeline status:', error);
      if (error.message.includes("CORS")) {
        alert("CORS Error: Please ensure the backend allows requests from this origin.");
      }
      throw error;
    }
  }

  async startPipeline(config) {
    try {
      const response = await fetch(`${this.baseURL}/pipelines/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(config),
      });

      return await this.handleResponse(response);
    } catch (error) {
      console.error('Error starting pipeline:', error);
      throw error;
    }
  }

  async stopPipeline(pipelineId) {
    try {
      const response = await fetch(`${this.baseURL}/pipelines/${pipelineId}/stop`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      });

      return await this.handleResponse(response);
    } catch (error) {
      console.error('Error stopping pipeline:', error);
      throw error;
    }
  }

  async makePipelineDecision(pipelineId, decision) {
    try {
      const response = await fetch(`${this.baseURL}/pipelines/${pipelineId}/decision`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ decision }),
      });

      return await this.handleResponse(response);
    } catch (error) {
      console.error('Error making pipeline decision:', error);
      throw error;
    }
  }

  async getPipelineLogs(pipelineId) {
    try {
      const response = await fetch(`${this.baseURL}/pipelines/${pipelineId}/logs`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });

      return await this.handleResponse(response);
    } catch (error) {
      console.error('Error getting pipeline logs:', error);
      throw error;
    }
  }
}
