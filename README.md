# GPX Combiner Web App

A professional, lightweight, and Pythonic web app to combine multiple GPX files in order, with live map previews. Built with FastAPI, mobile-friendly, and ready for Railway deployment.

## Features
- Upload multiple GPX files in order
- See a map preview after each file is added (routes plotted in order)
- Download the combined GPX file
- Modern, mobile-friendly UI
- Safe, robust, and public code

## Tech Stack
- **Backend:** FastAPI
- **Frontend:** HTML5, Tailwind CSS, Leaflet.js
- **GPX Handling:** gpxpy
- **Testing:** pytest

## Setup
1. Clone the repo
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   uvicorn app.main:app --reload
   ```

## Deployment
- Ready for Railway or any cloud platform supporting FastAPI.

## License
MIT 