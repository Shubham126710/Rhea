# Rhea

Rhea is a premium research-oriented web application demonstrating a novel dual-layer Graph Neural Network (GNN) approach to structural misinformation and fake-news detection.

## What It Is
Rhea serves as an experimental analytical workstation that ingests unstructured claims, represents them as computational topologies, and surfaces structural contradictions against a reference corpus. It is designed not as a generic SaaS dashboard, but as a sophisticated research instrument.

## Research Problem
Modern misinformation relies heavily on structural manipulation rather than simple factual fabrication. Bad actors frequently reconstruct isolated true statements into fundamentally false structural relationships. Traditional natural language processing (NLP) struggles to detect these systemic realignments because the individual textual components may pass basic fact-checking filters.

## Core Concept
Instead of analyzing text purely sequentially, Rhea maps the structural architecture of a claim. By converting language into a relational topology (entities, actions, dependencies, and causal links), the system can mathematically evaluate the structural integrity of a narrative against a known corpus of truth.

## Dual-Layer GNN Approach
Rhea’s analytical engine operates on two distinct graph layers:
1.  **Linguistic Graph (Layer 1):** Maps the syntactic and semantic relationships within the input claim itself (e.g., subject-predicate-object triads).
2.  **Contextual Graph (Layer 2):** Projects the extracted entities into a broader knowledge graph derived from verified sources, computing the structural distance and relational consistency between the claim's topology and the reference topology.

## How the System Works
The operational pipeline is defined by five key stages:
*   **INGEST:** Extract unstructured information and metadata from user input.
*   **REPRESENT:** Convert language and evidence into computational representations.
*   **CONNECT:** Identify relationships between entities, claims, and sources.
*   **ANALYZE:** Detect patterns, contradictions, and structural relationships using the dual-layer GNN.
*   **SURFACE:** Present evidence and relationships in an interpretable visual form.

## Main Application Features
*   **Cinematic Loading Sequence:** A bespoke, typographic loading routine.
*   **Editorial Landing Environment:** Explains the methodology and research goals using a restrained, Swiss-editorial aesthetic.
*   **Analytical Workspace:** The core operational dashboard allowing researchers to input Text, URLs, or Files for structural analysis.
*   **Topological Visualization:** Renders the resulting entity relationships and structural confidence signals interactively.
*   **Archival History:** A clean, ledger-style history of previous structural analyses.

## Architecture
The application follows a decoupled client-server architecture:
*   **Frontend:** A React Single Page Application (SPA) handling the complex visual interface, routing, and state management. It communicates with the backend via a REST API using secure HttpOnly cookies for session state.
*   **Backend (Not included in this repo/scope):** A Python-based service responsible for the NLP extraction, graph construction, and GNN inference.

## Tech Stack
*   **Core:** React 18, Vite
*   **Routing:** React Router v6
*   **Styling:** Tailwind CSS (customized for the "Rhea Cobalt" and "Rhea Ivory" design system)
*   **Animation:** Framer Motion
*   **Icons:** Google Material Symbols

## Project Structure
```text
frontend/
├── index.html           # Main entry point and document structure
├── package.json         # Dependencies and scripts
├── tailwind.config.js   # Custom Rhea design system tokens
├── vite.config.js       # Vite configuration
├── vercel.json          # Vercel deployment configuration for SPA fallback
└── src/
    ├── api/             # API client methods (client.js)
    ├── components/      # Reusable UI components (landing, layout)
    ├── context/         # React Context providers (AuthContext.jsx)
    ├── lib/             # Utility functions (utils.js, toast.jsx)
    ├── pages/           # Route-level components (Landing, Workspace, etc.)
    └── main.jsx         # React application root
```

## Local Development Setup
1. Ensure Node.js (v18+) is installed.
2. Navigate to the frontend directory: `cd frontend`
3. Install dependencies: `npm install`

## Environment Variables
Create a `.env` file in the root of the `frontend` directory:
```env
VITE_API_BASE_URL=http://localhost:8000
```
*Note: If `VITE_API_BASE_URL` is omitted, the API client defaults to `http://localhost:8000`.*

## Running the Project
Start the Vite development server:
```bash
npm run dev
```
The application will be available at `http://localhost:5173`.

## Production Build
To create a production-optimized build:
```bash
npm run build
```
The output will be generated in the `dist/` directory.

## Vercel Deployment
The repository is configured for immediate deployment on Vercel. 
The included `vercel.json` file ensures that the React Router SPA fallback (`index.html`) is correctly served for all nested routes in production, preventing 404 errors on refresh.

## Important Implementation Details
*   **Auth State:** The frontend does not store JWTs or tokens in `localStorage`. Authentication relies entirely on `credentials: "include"` passing secure cookies managed by the backend.
*   **Design System:** The UI deliberately avoids generic SaaS components (like thick rounded cards or heavy drop shadows) in favor of thin 1px rules, deep electric cobalt backgrounds, and stark ivory typography to maintain the research-instrument aesthetic.

## Limitations & Current Scope
*   **Mocked Analysis:** The current frontend `Demo.jsx` component simulates the API delay and returns a mocked topology graph for demonstration purposes.
*   **Backend Dependency:** Full analytical capabilities require the Python backend to be running and accessible via the configured API URL.

## Future Research Directions
*   Integration with live knowledge-graph databases (e.g., Neo4j).
*   Real-time streaming of the GNN inference steps to the frontend for deeper interpretability.
*   Support for multi-modal ingestion (e.g., video and audio transcripts).