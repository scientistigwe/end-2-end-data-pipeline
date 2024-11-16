// StreamSourceForm.js
import React, { useState } from 'react';

const StreamSourceForm = () => {
  const [sourceType, setSourceType] = useState('');
  const [credentials, setCredentials] = useState({
    bootstrapServers: '',
    groupId: '',
    topic: '',
    region: '',
    streamName: '',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setCredentials((prevState) => ({
      ...prevState,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const response = await fetch('http://localhost:5000/api/stream-source', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ sourceType, credentials }),
    });
    if (response.ok) {
      console.log('Stream source configured successfully');
    } else {
      console.log('Error configuring stream source');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <label>
        Source Type:
        <select
          name="sourceType"
          value={sourceType}
          onChange={(e) => setSourceType(e.target.value)}
        >
          <option value="kafka">Kafka</option>
          <option value="kinesis">AWS Kinesis</option>
        </select>
      </label>
      <label>
        Bootstrap Servers:
        <input
          type="text"
          name="bootstrapServers"
          value={credentials.bootstrapServers}
          onChange={handleChange}
        />
      </label>
      <label>
        Group ID:
        <input
          type="text"
          name="groupId"
          value={credentials.groupId}
          onChange={handleChange}
        />
      </label>
      <label>
        Topic:
        <input
          type="text"
          name="topic"
          value={credentials.topic}
          onChange={handleChange}
        />
      </label>
      <label>
        Region:
        <input
          type="text"
          name="region"
          value={credentials.region}
          onChange={handleChange}
        />
      </label>
      <label>
        Stream Name:
        <input
          type="text"
          name="streamName"
          value={credentials.streamName}
          onChange={handleChange}
        />
      </label>
      <button type="submit">Submit</button>
    </form>
  );
};

export default StreamSourceForm;
