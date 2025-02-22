"use client";

import React from 'react';
import { LoadScript, GoogleMap, Marker } from '@react-google-maps/api';
import styles from './styles/example.module.css';

const center = { lat: 40.902771, lng: -73.133850 }; //stony's coordinates

export default function Example() {
  return (
    <div className={styles.mapContainer}>
      <LoadScript googleMapsApiKey={process.env.NEXT_PUBLIC_MAPS_KEY}>
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
