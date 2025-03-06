# Seawolf Accessibility

## Getting Started

### 1. Install Node Dependencies
Run the following command in the **root directory**:

```bash
npm install
```

### 2. Set Up the Python Backend
Navigate to the backend directory:
```bash
cd backend/
```
Create a Python virtual environment and activate it:
```bash
python3 -m venv venv
source venv/bin/activate
```
Install the required Python dependencies from requirements.txt:
 ```bash 
pip install -r requirements.txt
```

### 3. Configuration
Make sure that you have a `.env` file in the root directory containing the Google Maps API key environment variables.

### 4. Start the Servers
Start the Python backend by running the following command inside the backend directory:
```bash
uvicorn routingBeta:app --reload
```
Then, in the app directory, start the Next.js frontend:
```bash
cd ../app/
npm run dev
```
