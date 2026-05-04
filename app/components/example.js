"use client";

import React, { useRef, useState, useCallback, useEffect } from 'react';
import {
  LoadScript,
  GoogleMap,
  Marker,
  Polyline,
  DirectionsRenderer
} from '@react-google-maps/api';
import styles from './styles/example.module.css';

const center = { lat: 40.910412, lng: -73.124705 }; // stony's coordinates

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
  const polylineRefs = useRef([]); // Stores polyline instances
  const [mapKey, setMapKey] = useState(0); // We still update this if needed
  const [mapType, setMapType] = useState("roadmap");
  const [isDarkMode, setIsDarkMode] = useState(false);

  const [startLocation, setStartLocation] = useState("");
  const [endLocation, setEndLocation] = useState("");
  const [activeField, setActiveField] = useState(null);

  const [selectedPoints, setSelectedPoints] = useState({ start: null, end: null });
  const [directionsResponse, setDirectionsResponse] = useState(null);
  const [routePath, setRoutePath] = useState([]);

  const onMapLoad = useCallback((map) => {
    mapRef.current = map;
    console.log("Map loaded:", map);
  }, []);

  const toggleMapType = () => {
    if (mapRef.current) {
      const nextType = mapType === "roadmap" ? "satellite" : "roadmap";
      mapRef.current.setMapTypeId(nextType);
      setMapType(nextType);
    }
  };

  const toggleDarkMode = () => {
    setIsDarkMode((prev) => !prev);
  };

  // Clear function for all polyline instances.
  const clearAllPolylines = () => {
    console.log("Clearing polyline instances:", polylineRefs.current.length);
    polylineRefs.current.forEach((poly) => {
      if (poly) {
        poly.setMap(null);
      }
    });
    polylineRefs.current = [];
    setRoutePath([]);
  };

  // When a new start marker is placed, ensure old polylines are cleared.
  useEffect(() => {
    if (selectedPoints.start) {
      console.log("New first marker placed, clearing any old polylines.");
      clearAllPolylines();
    }
  }, [selectedPoints.start]);

  const handleMapClick = (e) => {
    // Clear any overlays when the map is clicked.
    setDirectionsResponse(null);
    clearAllPolylines();

    const clickedCoord = { lat: e.latLng.lat(), lng: e.latLng.lng() };
    const coordStr = `${clickedCoord.lat.toFixed(6)},${clickedCoord.lng.toFixed(6)}`;
    console.log("Map clicked. Coordinate:", clickedCoord, coordStr);

    if (activeField === "start") {
      setStartLocation(coordStr);
      setSelectedPoints((prev) => ({ ...prev, start: clickedCoord }));
    } else if (activeField === "end") {
      setEndLocation(coordStr);
      setSelectedPoints((prev) => ({ ...prev, end: clickedCoord }));
    } else {
      if (!selectedPoints.start) {
        setStartLocation(coordStr);
        setSelectedPoints({ start: clickedCoord, end: null });
      } else if (!selectedPoints.end) {
        setEndLocation(coordStr);
        setSelectedPoints((prev) => ({ ...prev, end: clickedCoord }));
      } else {
        // If both markers exist, treat this as resetting the start.
        setStartLocation(coordStr);
        setSelectedPoints({ start: clickedCoord, end: null });
        setEndLocation("");
      }
    }
  };

  const handleStartInputChange = (e) => {
    setStartLocation(e.target.value);
    setDirectionsResponse(null);
    clearAllPolylines();
  };

  const handleEndInputChange = (e) => {
    setEndLocation(e.target.value);
    setDirectionsResponse(null);
    clearAllPolylines();
  };

  const calculateRoute = async () => {
    console.log("calculateRoute called: clearing overlays");
    // Clear any existing overlays
    setDirectionsResponse(null);
    clearAllPolylines();
    // Optionally force a full remount of the map if needed:
    setMapKey(prev => prev + 1);

    if (!startLocation || !endLocation) return;
    try {
      console.log("Fetching directions for:", startLocation, endLocation);
      const backendUrl = process.env.NODE_ENV === 'production' ? process.env.NEXT_PUBLIC_BACKEND_URL : 'http://127.0.0.1:8000';
      const response = await fetch(
        `${backendUrl}/api/directions?start=${encodeURIComponent(startLocation)}&end=${encodeURIComponent(endLocation)}`
      );      
      if (!response.ok) {
        console.error("Failed to fetch directions", await response.text());
        return;
      }
      let data = await response.json();
      if (!data.routes || !Array.isArray(data.routes)) {
        data = { routes: [data] };
      }
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
      if (!data.request) {
        data.request = {
          travelMode: 'WALKING',
          origin: startLocation,
          destination: endLocation,
        };
      }
      if (!data.geocoded_waypoints) {
        data.geocoded_waypoints = [];
      }
      console.log("Formatted directions object:", data);
      setDirectionsResponse(data);
      if (data.routes[0].overview_polyline && data.routes[0].overview_polyline.points) {
        const decodedPath = window.google.maps.geometry.encoding.decodePath(
          data.routes[0].overview_polyline.points
        );
        setRoutePath(decodedPath);
        console.log("Decoded polyline path:", decodedPath);
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
            onChange={handleStartInputChange}
          />
          <input
            type="text"
            placeholder="End location"
            value={endLocation}
            onFocus={() => setActiveField("end")}
            onChange={handleEndInputChange}
          />
          <button onClick={calculateRoute}>Get Directions</button>
        </div>
        <LoadScript
          googleMapsApiKey={process.env.NEXT_PUBLIC_MAPS_KEY}
          libraries={["geometry"]}
        >
          <GoogleMap
            key={mapKey}
            onLoad={onMapLoad}
            onClick={handleMapClick}
            mapContainerStyle={{ width: "100%", height: "100%" }}
            center={center}
            zoom={14.45}
            options={{
              mapTypeControl: false,
              styles: isDarkMode ? darkMapStyles : [],
              minZoom: 14.2,
              restriction: {
                latLngBounds: {
                  north: 40.942273,
                  south: 40.876240,
                  west: -73.196586,
                  east: -73.050875,
                },
                strictBounds: true,
              },
            }}
          >
            {selectedPoints.start && (
              <Marker position={selectedPoints.start} label="A" />
            )}
            {selectedPoints.end && (
              <Marker position={selectedPoints.end} label="B" />
            )}
            {routePath.length > 0 && (
              <Polyline
                key={JSON.stringify(routePath)}
                path={routePath}
                onLoad={(polyline) => {
                  polylineRefs.current.push(polyline);
                }}
                options={{
                  strokeColor: "#FF0000",
                  strokeOpacity: 0.8,
                  strokeWeight: 4,
                }}
              />
            )}
            {directionsResponse && (
              <DirectionsRenderer
                key={JSON.stringify(directionsResponse)}
                options={{
                  directions: directionsResponse,
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