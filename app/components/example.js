"use client";

import React from 'react';
import { LoadScript, GoogleMap, Marker } from '@react-google-maps/api';
import styles from './styles/example.module.css';

const center = { lat: 40.680, lng: -73.998 }; // Arbitrary chosen location

export default function Example() {
  return (
    <div className={styles.mapContainer}>
      <LoadScript googleMapsApiKey={process.env.GOOGLE_MAPS_API_KEY}>
        <GoogleMap
          mapContainerStyle={{ width: '100%', height: '100%' }}
          center={center}
          zoom={15}
        >
          <Marker position={center} />
        </GoogleMap>
      </LoadScript>
    </div>
  );
}
