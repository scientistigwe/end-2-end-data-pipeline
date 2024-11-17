// src/utils/ApiClient.js

export default class ApiClient {
  constructor(baseURL = "http://127.0.0.1:5000") {
    this.baseURL = baseURL;
  }

  async postFileSource(formData) {
    try {
      const response = await fetch(`${this.baseURL}/file-source`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error("Error in postFileSource:", error);
      throw error;
    }
  }

  async getFileMetadata() {
    try {
      const response = await fetch(`${this.baseURL}/file-metadata`, {
        method: "GET",
      });
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error("Error in getFileMetadata:", error);
      throw error;
    }
  }
}
