"use client";

import React, { useRef, useState, useCallback } from 'react'; 
import {
  LoadScript,
  GoogleMap,
  Marker,
  DirectionsRenderer
} from '@react-google-maps/api';
import styles from './styles/example.module.css';

const center = { lat: 40.902771, lng: -73.133850 }; // stony's coordinates

// A minimal dark mode style array for the map.
const darkMapStyles = [
  { elementType: 'geometry', stylers: [{ color: '#242f3e' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#242f3e' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#746855' }] },
  {
    featureType: 'administrative.locality',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#d59563' }]
  },
  {
    featureType: 'poi',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#d59563' }]
  },
  {
    featureType: 'poi.park',
    elementType: 'geometry',
    stylers: [{ color: '#263c3f' }]
  },
  {
    featureType: 'poi.park',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#6b9a76' }]
  },
  {
    featureType: 'road',
    elementType: 'geometry',
    stylers: [{ color: '#38414e' }]
  },
  {
    featureType: 'road',
    elementType: 'geometry.stroke',
    stylers: [{ color: '#212a37' }]
  },
  {
    featureType: 'road',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#9ca5b3' }]
  },
  {
    featureType: 'road.highway',
    elementType: 'geometry',
    stylers: [{ color: '#746855' }]
  },
  {
    featureType: 'road.highway',
    elementType: 'geometry.stroke',
    stylers: [{ color: '#1f2835' }]
  },
  {
    featureType: 'road.highway',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#f3d19c' }]
  },
  {
    featureType: 'transit',
    elementType: 'geometry',
    stylers: [{ color: '#2f3948' }]
  },
  {
    featureType: 'transit.station',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#d59563' }]
  },
  {
    featureType: 'water',
    elementType: 'geometry',
    stylers: [{ color: '#17263c' }]
  },
  {
    featureType: 'water',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#515c6d' }]
  },
  {
    featureType: 'water',
    elementType: 'labels.text.stroke',
    stylers: [{ color: '#17263c' }]
  }
];

export default function Example() {
  const mapRef = useRef(null);
  const [mapType, setMapType] = useState("roadmap");
  const [isDarkMode, setIsDarkMode] = useState(false);
  
  // For manual direction input (coordinates as "lat,lng")
  const [startLocation, setStartLocation] = useState("");
  const [endLocation, setEndLocation] = useState("");
  // Track the currently active input field ("start" or "end")
  const [activeField, setActiveField] = useState(null);
  
  // For displaying markers
  const [selectedPoints, setSelectedPoints] = useState({ start: null, end: null });
  // For storing directions from the backend
  const [directionsResponse, setDirectionsResponse] = useState(null);

  const onMapLoad = useCallback((map) => {
    mapRef.current = map;
  }, []);

  const toggleMapType = () => {
    if (mapRef.current) {
      const nextType = mapType === "roadmap" ? "satellite" : "roadmap";
      mapRef.current.setMapTypeId(nextType);
      setMapType(nextType);
    }
  };

  const toggleDarkMode = () => {
    setIsDarkMode(prev => !prev);
  };

  // When the user clicks on the map, update the active input's coordinate.
  const handleMapClick = (e) => {
    const clickedCoord = { lat: e.latLng.lat(), lng: e.latLng.lng() };
    const coordStr = `${clickedCoord.lat.toFixed(6)},${clickedCoord.lng.toFixed(6)}`;
    // If an input is active, update that coordinate.
    if (activeField === "start") {
      setStartLocation(coordStr);
      setSelectedPoints(prev => ({ ...prev, start: clickedCoord }));
    } else if (activeField === "end") {
      setEndLocation(coordStr);
      setSelectedPoints(prev => ({ ...prev, end: clickedCoord }));
    } else {
      // If no input is active, default to first setting start then end.
      if (!selectedPoints.start) {
        setStartLocation(coordStr);
        setSelectedPoints({ start: clickedCoord, end: null });
      } else if (!selectedPoints.end) {
        setEndLocation(coordStr);
        setSelectedPoints(prev => ({ ...prev, end: clickedCoord }));
      } else {
        // Both are set; reset start.
        setStartLocation(coordStr);
        setSelectedPoints({ start: clickedCoord, end: null });
        setEndLocation("");
      }
    }
    // Clear any directions when coordinates change
    setDirectionsResponse(null);
  };

  // Calls the backend API (routingBeta.py) for walking directions.
  const calculateRoute = async () => {
    if (!startLocation || !endLocation) return;
    try {
      const response = await fetch(`http://localhost:8000/api/directions?start=${encodeURIComponent(startLocation)}&end=${encodeURIComponent(endLocation)}`);
      if (!response.ok) {
        console.error("Failed to fetch directions", await response.text());
        return;
      }
      const data = await response.json();
      setDirectionsResponse(data);
    } catch (err) {
      console.error("Error fetching directions:", err);
    }
  };

  return (
    <div className={styles.container}>
      <video className={styles.videoBackground} autoPlay loop muted>
        <source src="/pics/waves (online-video-cutter.com).mp4" type="video/mp4" />
        Your browser does not support the video tag.
      </video>
      <div className={styles.mapContainer}>
        {/* Directions input bar placed on top of map */}
        <div className={styles.directionsInput}>
          <input
            type="text"
            placeholder="Start location"
            value={startLocation}
            onFocus={() => setActiveField("start")}
            onChange={(e) => setStartLocation(e.target.value)}
          />
          <input
            type="text"
            placeholder="End location"
            value={endLocation}
            onFocus={() => setActiveField("end")}
            onChange={(e) => setEndLocation(e.target.value)}
          />
          <button onClick={calculateRoute}>Get Directions</button>
        </div>
        <LoadScript googleMapsApiKey={process.env.NEXT_PUBLIC_MAPS_KEY}>
          <GoogleMap
            onLoad={onMapLoad}
            onClick={handleMapClick}
            mapContainerStyle={{ width: '100%', height: '100%' }}
            center={center}
            zoom={15}
            options={{
              mapTypeControl: false,
              styles: isDarkMode ? darkMapStyles : []
            }}
          >
            {/* Base center marker */}
            <Marker position={center} />
            {/* Markers for start/end points from input */}
            {selectedPoints.start && (
              <Marker position={selectedPoints.start} label="A" />
            )}
            {selectedPoints.end && (
              <Marker position={selectedPoints.end} label="B" />
            )}
            {/* Display route from the backend when available */}
            {directionsResponse && (
              <DirectionsRenderer
                options={{
                  directions: directionsResponse
                }}
              />
            )}
            {/* Custom Toggle Button for Satellite/Map */}
            <div className={styles.customControl} onClick={toggleMapType}>
              {mapType === "roadmap" ? "Satellite View" : "Map View"}
            </div>
            {/* Light/Dark Mode Toggle Button */}
            <div
              className={`${styles.lightDarkToggle} ${isDarkMode ? styles.darkMode : ""}`}
              onClick={toggleDarkMode}
            >
              {isDarkMode ? "☀️" : "🌙"}
            </div>
          </GoogleMap>
        </LoadScript>
      </div>
    </div>
  );
}