// find_nearest_nodes.js
// This script reads nodes.json, prompts for two coordinate pairs (latitude,longitude in degrees),
// and prints the IDs of the nearest nodes for each pair.
// Usage: node find_nearest_nodes.js

const fs = require('fs');
const path = require('path');
const readline = require('readline');

// Load the nodes.json file from the same folder
const nodesPath = path.join(__dirname, 'nodes.json');
let nodesData;
try {
  const data = fs.readFileSync(nodesPath, 'utf8');
  nodesData = JSON.parse(data);
} catch (err) {
  console.error('Error reading or parsing nodes.json:', err);
  process.exit(1);
}

// Create a readline interface for terminal input
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

// Helper function for prompting the user
function prompt(query) {
  return new Promise(resolve => rl.question(query, resolve));
}

// Convert degrees to nanodegrees (1 degree = 10^9 nanodegrees)
function toNanodegrees(value) {
  return Math.round(value * 1e9);
}

// Calculate squared Euclidean distance (no need to compute square roots for comparison)
function distanceSquared(lon1, lat1, lon2, lat2) {
  const dx = lon1 - lon2;
  const dy = lat1 - lat2;
  return dx * dx + dy * dy;
}

// Function to find the nearest node for a given coordinate pair
function findNearestNode(coord) {
  const coordLonNano = toNanodegrees(coord.lon);
  const coordLatNano = toNanodegrees(coord.lat);

  let nearestNode = null;
  let minDist = Infinity;

  nodesData.forEach(node => {
    const d = distanceSquared(coordLonNano, coordLatNano, node.lon, node.lat);
    if (d < minDist) {
      minDist = d;
      nearestNode = node;
    }
  });

  return nearestNode;
}

// Main async function to run the script
async function main() {
  console.log('Enter the coordinate pairs in the format: latitude,longitude');
  const input1 = await prompt('Enter the first coordinate pair: ');
  const input2 = await prompt('Enter the second coordinate pair: ');

  // Parse the input string into numbers
  function parseInput(input) {
    const parts = input.split(',');
    if (parts.length !== 2) {
      throw new Error('Invalid format. Expected format: latitude,longitude');
    }
    const lat = parseFloat(parts[0].trim());
    const lon = parseFloat(parts[1].trim());
    if (isNaN(lat) || isNaN(lon)) {
      throw new Error('Invalid numbers. Please enter valid numeric values.');
    }
    return { lat, lon };
  }

  let coord1, coord2;
  try {
    coord1 = parseInput(input1);
    coord2 = parseInput(input2);
  } catch (err) {
    console.error(err.message);
    rl.close();
    process.exit(1);
  }

  const nearest1 = findNearestNode(coord1);
  const nearest2 = findNearestNode(coord2);

  console.log('\nNearest node for the first coordinate pair:');
  console.log(`ID: ${nearest1.id} (Lat: ${nearest1.lat / 1e9}, Lon: ${nearest1.lon / 1e9})`);

  console.log('\nNearest node for the second coordinate pair:');
  console.log(`ID: ${nearest2.id} (Lat: ${nearest2.lat / 1e9}, Lon: ${nearest2.lon / 1e9})`);

  rl.close();
}

main();
