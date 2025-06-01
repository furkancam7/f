# User Authentication System

A simple Gradio web application with MongoDB integration for user authentication.

## Prerequisites

- Python 3.x
- MongoDB server running locally on default port (27017)
- Virtual environment (recommended)

## Setup

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with the following content:
```
MONGODB_URI=mongodb://localhost:27017/
DB_NAME=SENG472
COLLECTION_NAME=user
```

4. Make sure MongoDB is running locally on port 27017

## Running the Application

1. Activate the virtual environment (if not already activated):
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Run the application:
```bash
python app.py
```

3. Open your web browser and navigate to the URL shown in the terminal (typically http://127.0.0.1:7860)

## Features

- User signup with email and password
- User login verification
- MongoDB integration with singleton pattern
- Environment variable configuration 