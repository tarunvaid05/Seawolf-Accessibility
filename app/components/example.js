//// filepath: /Users/tarun/CS/Projects/HopperHacks25/app/components/example.js
"use client";

import React, { useRef, useState, useCallback } from 'react';
import {
  LoadScript,
  GoogleMap,
  Marker,
  Polyline, // import Polyline
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
  // For storing directions from the backend (if needed)
  const [directionsResponse, setDirectionsResponse] = useState(null);
  // For storing the decoded polyline route coordinates.
  const [routePath, setRoutePath] = useState([]);

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
    if (activeField === "start") {
      setStartLocation(coordStr);
      setSelectedPoints(prev => ({ ...prev, start: clickedCoord }));
    } else if (activeField === "end") {
      setEndLocation(coordStr);
      setSelectedPoints(prev => ({ ...prev, end: clickedCoord }));
    } else {
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
    // Clear any directions or polyline on coordinate change.
    setDirectionsResponse(null);
    setRoutePath([]);
  };

  // Modify calculateRoute to decode the overview_polyline and set it as routePath.
  const calculateRoute = async () => {
    if (!startLocation || !endLocation) return;
    try {
      const response = await fetch(
        `http://localhost:8000/api/directions?start=${encodeURIComponent(startLocation)}&end=${encodeURIComponent(endLocation)}`
      );
      if (!response.ok) {
        console.error("Failed to fetch directions", await response.text());
        return;
      }
      let data = await response.json();
      // Wrap data in a routes array if not already.
      if (!data.routes || !Array.isArray(data.routes)) {
        data = { routes: [data] };
      }
      // Convert bounds if they exist:
      if (
        data.routes[0] &&
        data.routes[0].bounds &&
        data.routes[0].bounds.northeast &&
        data.routes[0].bounds.southwest
      ) {
        const { northeast, southwest } = data.routes[0].bounds;
        data.routes[0].bounds = {
          north: northeast.lat,
          east: northeast.lng,
          south: southwest.lat,
          west: southwest.lng,
        };
      }
      // Ensure request property exists.
      if (!data.request) {
        data.request = {
          travelMode: 'WALKING',
          origin: startLocation,
          destination: endLocation
        };
      }
      if (!data.geocoded_waypoints) {
        data.geocoded_waypoints = [];
      }
      console.log("Formatted directions object:", data);
      // Optionally set the directions response if you still want to use DirectionsRenderer.
      setDirectionsResponse(data);

      // Use the overview_polyline from the first route to draw the path.
      if (data.routes[0].overview_polyline && data.routes[0].overview_polyline.points) {
        // Decode the polyline using the Google Maps geometry library.
        const decodedPath = window.google.maps.geometry.encoding.decodePath(data.routes[0].overview_polyline.points);
        setRoutePath(decodedPath);
      } else {
        console.error("No overview_polyline found in route data.");
      }
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
        <LoadScript googleMapsApiKey={process.env.NEXT_PUBLIC_MAPS_KEY} libraries={["geometry"]}>
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
            <Marker position={center} />
            {selectedPoints.start && (
              <Marker position={selectedPoints.start} label="A" />
            )}
            {selectedPoints.end && (
              <Marker position={selectedPoints.end} label="B" />
            )}
            {/* Render the polyline if available */}
            {routePath.length > 0 && (
              <Polyline
                path={routePath}
                options={{
                  strokeColor: '#FF0000',
                  strokeOpacity: 0.8,
                  strokeWeight: 4,
                }}
              />
            )}
            {/* Optionally render the DirectionsRenderer if needed */}
            {directionsResponse && (
              <DirectionsRenderer
                options={{
                  directions: directionsResponse
                }}
              />
            )}
            <div className={styles.customControl} onClick={toggleMapType}>
              {mapType === "roadmap" ? "Satellite View" : "Map View"}
            </div>
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