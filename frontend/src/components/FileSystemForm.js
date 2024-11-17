import React, { useState } from "react";
import {
  Button,
  FormControl,
  FormControlLabel,
  RadioGroup,
  Radio,
  Typography,
  Card,
  CardContent,
  Alert,
  Stack,
  Box,
  CircularProgress,
} from "@mui/material";
import useFileSource from "../hooks/useFileSource";

const FileSystemForm = () => {
  const [uploadType, setUploadType] = useState("single");
  const [selectedFiles, setSelectedFiles] = useState(null);
  const { handleApiRequest, response, loading, error } = useFileSource(
    "http://127.0.0.1:5000"
  );
  const allowedFormats = [".csv", ".json", ".parquet", ".xlsx"];

  const handleFileChange = (event) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      if (uploadType === "single" && files.length > 1) {
        const fileArray = new DataTransfer();
        fileArray.items.add(files[0]);
        setSelectedFiles(fileArray.files);
      } else {
        setSelectedFiles(files);
      }
    } else {
      setSelectedFiles(null);
    }
  };

  const validateFiles = (files) => {
    if (!files || files.length === 0) {
      throw new Error("Please select file(s) to upload");
    }

    for (let i = 0; i < files.length; i++) {
      const fileExtension = files[i].name.split(".").pop().toLowerCase();
      if (!allowedFormats.includes(`.${fileExtension}`)) {
        throw new Error(
          `Invalid file format: ${
            files[i].name
          }. Allowed formats: ${allowedFormats.join(", ")}`
        );
      }
    }
    return true;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    try {
      validateFiles(selectedFiles);

      const formData = new FormData();
      formData.append("inputMethod", "upload");
      formData.append("uploadType", uploadType);

      // Append each file with the same key name 'files'
      Array.from(selectedFiles).forEach((file) => {
        formData.append("files", file);
      });

      // Call handleApiRequest with the actionType as "upload" for file upload
      await handleApiRequest(formData, "upload");
    } catch (err) {
      console.error("Submission error:", err.message);
    }
  };

  return (
    <Box maxWidth="md" margin="auto" padding={3}>
      <Card>
        <CardContent>
          <Typography variant="h5" gutterBottom>
            File Upload System
          </Typography>

          <form onSubmit={handleSubmit}>
            <Stack spacing={3}>
              <FormControl component="fieldset">
                <Typography variant="subtitle2" gutterBottom>
                  Upload Type
                </Typography>
                <RadioGroup
                  row
                  value={uploadType}
                  onChange={(e) => {
                    setUploadType(e.target.value);
                    setSelectedFiles(null);
                  }}
                >
                  <FormControlLabel
                    value="single"
                    control={<Radio />}
                    label="Single File"
                  />
                  <FormControlLabel
                    value="multiple"
                    control={<Radio />}
                    label="Multiple Files"
                  />
                </RadioGroup>
              </FormControl>

              <Box>
                <input
                  type="file"
                  multiple={uploadType === "multiple"}
                  onChange={handleFileChange}
                  accept={allowedFormats.join(",")}
                  style={{ marginBottom: "8px" }}
                  key={uploadType}
                />
                <Typography
                  variant="caption"
                  color="textSecondary"
                  display="block"
                >
                  Allowed formats: {allowedFormats.join(", ")}
                </Typography>
                {selectedFiles && (
                  <Typography variant="caption" color="primary" display="block">
                    Selected:{" "}
                    {Array.from(selectedFiles)
                      .map((f) => f.name)
                      .join(", ")}
                  </Typography>
                )}
              </Box>

              <Button
                type="submit"
                variant="contained"
                color="primary"
                disabled={loading || !selectedFiles}
                startIcon={
                  loading && <CircularProgress size={20} color="inherit" />
                }
              >
                {loading ? "Processing..." : "Submit"}
              </Button>

              {error && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {error}
                </Alert>
              )}

              {response && (
                <Alert severity="success" sx={{ mt: 2 }}>
                  <Typography variant="subtitle2">Response:</Typography>
                  <pre
                    style={{
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      marginTop: "8px",
                      fontSize: "0.875rem",
                    }}
                  >
                    {JSON.stringify(response, null, 2)}
                  </pre>
                </Alert>
              )}
            </Stack>
          </form>
        </CardContent>
      </Card>
    </Box>
  );
};

export default FileSystemForm;
