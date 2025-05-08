# Audio Translation Web Application

A Flask web application that translates audio between different languages using the SarvamAI API.

## Features
- Audio recording and playback
- Speech-to-text conversion
- Text translation between multiple languages
- Text-to-speech conversion
- Modern UI with NIT Trichy branding

## Deployment Instructions

### Local Development
1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file with your API key:
   ```
   API_KEY=your_api_key_here
   ```
5. Run the application:
   ```bash
   python app.py
   ```

### Deployment on PythonAnywhere
1. Sign up for a free account at [PythonAnywhere](https://www.pythonanywhere.com)
2. Go to the Web tab and click "Add a new web app"
3. Choose "Flask" and select Python 3.9
4. Upload your files:
   - app.py
   - dashboard.html
   - app.png
   - requirements.txt
5. In the Web tab, set up your virtual environment:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.9 myenv
   pip install -r requirements.txt
   ```
6. Add your API key in the Web tab's Environment variables section:
   ```
   API_KEY=your_api_key_here
   ```
7. Configure the WSGI file to use your app
8. Reload the web app

## Environment Variables
- `API_KEY`: Your SarvamAI API key

## Dependencies
See requirements.txt for a complete list of dependencies. 