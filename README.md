# 🎬 YouTube Video Q&A — AI Powered

Ask any question about any YouTube video using Claude AI.

## How it works
1. Paste a YouTube URL
2. Copy the transcript from YouTube and paste it
3. Ask questions — Claude answers based on the video content

## Deploy on Streamlit Cloud (Free)

### Step 1 — Push to GitHub
1. Create a free account at github.com
2. Create a new repository (e.g. `youtube-qa-app`)
3. Upload both files: `app.py` and `requirements.txt`

### Step 2 — Deploy on Streamlit Cloud
1. Go to share.streamlit.io
2. Sign in with GitHub
3. Click "New app"
4. Select your repository and set main file as `app.py`
5. Click "Deploy" — it goes live in ~2 minutes!

### Step 3 — Get Anthropic API Key (Free)
1. Go to console.anthropic.com
2. Sign up for a free account
3. Go to API Keys → Create Key
4. New accounts get free credits — enough to demo!

## Tech Stack
- **Frontend**: Streamlit
- **AI**: Claude (Anthropic API)
- **Language**: Python

## Features
- Paste any YouTube video URL
- Thumbnail preview of the video
- Multi-turn conversation (remembers previous questions)
- Quick suggestion chips
- Clean dark UI
