import { useState } from 'react';
import axios from 'axios';

export default function Home() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getRoute = async () => {
    setLoading(true);
    setError(null);
    const start = "300 Circle Rd, Stony Brook, NY 11790";
    const end = "Student Activities Center, Suite 220, Stony Brook, NY 11790";

    try {
      const directionsResponse = await axios.post('http://localhost:5000/api/directions', {
        start_loc: start,
        end_loc: end,
        mode: 'walking'
      });
      const directions = directionsResponse.data;

      const segmentsResponse = await axios.post('http://localhost:5000/api/route_segments', {
        directions
      });
      const segments = segmentsResponse.data;

      let elevation = null;
      if (segments.length > 0) {
        const polyline = segments[0].polyline;
        const elevationResponse = await axios.post('http://localhost:5000/api/elevation', {
          polyline
        });
        elevation = elevationResponse.data;
      }

      setData({ directions, segments, elevation });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <h1>Route Information</h1>
      <button onClick={getRoute} disabled={loading}>
        {loading ? 'Loading...' : 'Get Route'}
      </button>

      {error && <p style={{ color: 'red' }}>Error: {error}</p>}

      {data && (
        <pre style={{ background: '#f5f5f5', padding: '10px', borderRadius: '5px' }}>
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}