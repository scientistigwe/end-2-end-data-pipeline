import React, { useState } from 'react';
import { TextField, Button, FormControl, FormControlLabel, RadioGroup, Radio, Typography, Checkbox } from '@mui/material';

const FileSystemForm = () => {
  const [inputMethod, setInputMethod] = useState('upload'); // 'upload' or 'path'
  const [files, setFiles] = useState(null);
  const [filePath, setFilePath] = useState('');
  const [fileFormat, setFileFormat] = useState('');
  const [isDirectory, setIsDirectory] = useState(false);

  const allowedFormats = ['.csv', '.json', '.parquet', '.xlsx'];

  const handleFileChange = (event) => {
    setFiles(event.target.files);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (inputMethod === 'upload') {
      if (!files || files.length === 0) {
        alert('Please upload at least one file.');
        return;
      }
      for (let i = 0; i < files.length; i++) {
        const fileExtension = files[i].name.split('.').pop();
        if (!allowedFormats.includes(`.${fileExtension}`)) {
          alert(`Invalid file format: ${files[i].name}. Allowed formats: ${allowedFormats.join(', ')}`);
          return;
        }
      }
    } else {
      if (!filePath) {
        alert('Please provide a valid file or directory path.');
        return;
      }
      if (!isDirectory && !allowedFormats.includes(fileFormat)) {
        alert(`Invalid file format for path. Allowed formats: ${allowedFormats.join(', ')}`);
        return;
      }
    }

    const formData = new FormData();
    if (inputMethod === 'upload') {
      for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
      }
    } else {
      formData.append('filePath', filePath);
      formData.append('fileFormat', fileFormat);
      formData.append('isDirectory', isDirectory);
    }

    try {
      const response = await fetch('/api/file-source', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();
      if (result.status === 'success') {
        alert('File(s) submitted successfully!');
      } else {
        alert('Error: ' + result.message);
      }
    } catch (error) {
      console.error('Error submitting the form:', error);
      alert('An error occurred while submitting the form.');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <FormControl component="fieldset">
        <Typography variant="h6">Select Input Method</Typography>
        <RadioGroup
          row
          value={inputMethod}
          onChange={(e) => setInputMethod(e.target.value)}
        >
          <FormControlLabel value="upload" control={<Radio />} label="Upload File(s)" />
          <FormControlLabel value="path" control={<Radio />} label="File/Directory Path" />
        </RadioGroup>
      </FormControl>

      {inputMethod === 'upload' ? (
        <div>
          <input
            type="file"
            multiple
            onChange={handleFileChange}
            accept={allowedFormats.join(',')}
          />
        </div>
      ) : (
        <div>
          <TextField
            label="File Path / Directory Path (File formats: .csv, .json, .parquet, .xlsx)"
            fullWidth
            margin="normal"
            value={filePath}
            onChange={(e) => setFilePath(e.target.value)}
            placeholder="Enter file or directory path"
          />
          <FormControlLabel
            control={<Checkbox />}
            checked={isDirectory}
            onChange={(e) => setIsDirectory(e.target.checked)}
            label="This is a directory"
          />
        </div>
      )}

      <Button type="submit" variant="contained" color="primary">
        Submit
      </Button>
    </form>
  );
};

export default FileSystemForm;
