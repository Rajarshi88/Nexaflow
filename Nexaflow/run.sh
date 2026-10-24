#!/bin/bash

echo "=========================================="
echo "  NexaFlow - Starting Application"
echo "=========================================="
echo ""

# Check Python
if ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3.10+"
    exit 1
fi

# Check Node
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node 18+"
    exit 1
fi

echo "✅ Python and Node.js found"
echo ""

# Backend setup
echo "📦 Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python -m venv venv
fi

echo "Activating virtual environment..."
source venv/Scripts/activate 2>/dev/null || source venv/bin/activate

echo "Installing backend dependencies..."
pip install -q -r requirements.txt

# Check if database exists
if [ ! -f "nexaflow.db" ]; then
    echo "🌱 Seeding database (first run)..."
    python seed.py
else
    echo "✅ Database already exists"
fi

echo ""
echo "🚀 Starting backend server on http://localhost:8000"
python main.py &
BACKEND_PID=$!

cd ..

# Frontend setup
echo ""
echo "📦 Setting up frontend..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

echo ""
echo "🚀 Starting frontend server on http://localhost:5173"
npm run dev &
FRONTEND_PID=$!

cd ..

echo ""
echo "=========================================="
echo "  ✅ NexaFlow is running!"
echo "=========================================="
echo ""
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo ""
echo "  Press Ctrl+C to stop both servers"
echo ""

# Wait for Ctrl+C
trap "echo ''; echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
