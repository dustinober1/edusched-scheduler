# EduSched Frontend

The React frontend application for EduSched educational scheduling system.

## Prerequisites

- Node.js 18+ and npm
- EduSched backend API running on `http://localhost:8000`

## Installation

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Edit .env if needed to match your backend configuration
```

## Development

```bash
# Start development server
npm run dev

# The app will be available at http://localhost:3000
# API requests will be proxied to http://localhost:8000
```

## Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## Features

- **Dashboard**: Real-time overview of scheduling statistics and recent activities
- **Schedule Editor**: Interactive calendar with drag-and-drop scheduling
- **Resource Management**: View and manage rooms, labs, and equipment
- **Constraint Builder**: Visual interface for creating and managing scheduling constraints
- **Optimization**: Run schedule optimization with different solvers and objectives
- **Integrations**: Connect external systems (SIS, calendars, notifications)
- **Settings**: Configure application preferences and system settings

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **React Query** - Server state management
- **React Router** - Client-side routing
- **Axios** - HTTP client
- **FullCalendar** - Interactive calendar component
- **Heroicons** - Icon library

## Project Structure

```
src/
├── api/              # API client and endpoints
├── components/       # Reusable UI components
├── contexts/         # React contexts (WebSocket, etc.)
├── hooks/            # Custom React hooks
├── pages/            # Page components
├── types/            # TypeScript type definitions
├── utils/            # Utility functions
└── main.tsx          # Application entry point
```

## Environment Variables

See `.env.example` for available configuration options.

## API Integration

The frontend automatically connects to the EduSched backend API for:
- Schedule CRUD operations
- Real-time updates via WebSocket
- Resource management
- Constraint validation
- Optimization jobs
- Analytics and reporting

## Contributing

1. Follow the existing code style
2. Use TypeScript for all new code
3. Add components to the appropriate directories
4. Update types when adding new data structures
5. Test with both light and dark themes