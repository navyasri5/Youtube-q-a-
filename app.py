import streamlit as st
import requests
import re
import json
import xml.etree.ElementTree as ET
import html as html_module

st.set_page_config(page_title="YouTube Q&A", page_icon="🎬", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
.stApp { background: #0a0a0f; color: #e8e8f0; }
.main-header { text-align: center; padding: 1.5rem 0 0.5rem 0; }
.main-header h1 { font-size: 2.2rem; font-weight: 600;
    background: linear-gradient(135deg, #f97316, #facc15, #4ade80);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.main-header p { color: #6b7280; font-size: 0.9rem; }
.info-box { background: #111827; border: 1px solid #1f2937;
    border-left: 3px solid #f97316; border-radius: 8px;
    padding: 0.9rem 1.1rem; margin: 0.7rem 0; font-size: 0.87rem; color: #9ca3af; line-height: 1.7; }
.info-box code { background: #1f2937; padding: 2px 6px; border-radius: 4px; color: #facc15; font-size: 0.8rem; }
.chat-user { background: #1c1108; border: 1px solid #92400e;
    border-radius: 12px 12px 2px 12px; padding: 0.75rem 1rem;
    margin: 0.4rem 0; margin-left: 15%; color: #fed7aa; font-size: 0.92rem; }
.chat-bot { background: #111827; border: 1px solid #1f2937;
    border-radius: 12px 12px 12px 2px; padding: 0.75rem 1rem;
    margin: 0.4rem 0; margin-right: 15%; color: #d1d5db; font-size: 0.92rem; line-height: 1.65; }
.success-box { background: #052e16; border: 1px solid #166534;
    border-radius: 8px; padding: 0.75rem 1.1rem; color: #86efac; font-size: 0.88rem; margin: 0.5rem 0; }
.stTextInput > div > div > input, .stTextArea > div > div > textarea {
    background: #111827 !important; border: 1px solid #1f2937 !important;
    border-radius: 8px !important; color: #e8e8f0 !important; font-family: 'Space Grotesk', sans-serif !important; }
.stButton > button { background: linear-gradient(135deg, #ea580c, #d97706);
    color: white; border: none; border-radius: 8px;
    font-family: 'Space Grotesk', sans-serif; font-weight: 500; width: 100%; }
.stButton > button:hover { opacity: 0.88; border: none; color: white; }
.footer { text-align: center; padding: 1.5rem 0 0.5rem; color: #374151; font-size: 0.78rem; }
</style>
<div class="main-header">
    <h1>🎬 YouTube Q&A</h1>
    <p>Paste a YouTube link — ask anything — powered by Groq AI</p>
</div>
""", unsafe_allow_html=True)


# ── helpers ──────────────────────────────────────────────────────────

def extract_video_id(url):
    for pat in [r'(?:v=|\/)([0-9A-Za-z_-]{11})', r'youtu\.be\/([0-9A-Za-z_-]{11})']:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def fetch_transcript(video_id):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        r = requests.get(f"https://www.youtube.com/watch?v={video_id}", headers=headers, timeout=15)
        html_content = r.text
        match = re.search(r'"captionTracks":(\[.*?\])', html_content)
        if not match:
            return None, "no_captions"
        tracks = json.loads(match.group(1))
        if not tracks:
            return None, "no_captions"
        base_url = None
        for track in tracks:
            if "en" in track.get("languageCode", "").lower():
                base_url = track.get("baseUrl")
                break
        if not base_url:
            base_url = tracks[0].get("baseUrl")
        r2 = requests.get(base_url, headers=headers, timeout=15)
        root = ET.fromstring(r2.text)
        lines = []
        for elem in root.findall(".//text"):
            raw = elem.text or ""
            clean = html_module.unescape(raw)
            clean = re.sub(r'<[^>]+>', '', clean).strip()
            if clean:
                lines.append(clean)
        transcript = re.sub(r'\s+', ' ', " ".join(lines)).strip()
        if len(transcript) > 100:
            return transcript, None
    except Exception:
        pass
    return None, "no_captions"


def chunk_text(text, size=700, overlap=80):
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunks.append(" ".join(words[i:i+size]))
        i += size - overlap
    return chunks


def find_relevant_chunks(transcript, question, top_k=4):
    chunks = chunk_text(transcript)
    q_words = set(re.sub(r'[^\w\s]', '', question.lower()).split())
    scored = sorted(chunks, key=lambda c: len(q_words & set(c.lower().split())), reverse=True)
    return "\n\n---\n\n".join(scored[:top_k])


def ask_groq(api_key, transcript, question, history):
    context = find_relevant_chunks(transcript, question)

    messages = [
        {
            "role": "system",
            "content": f"""You are a helpful assistant that answers questions based ONLY on the YouTube video transcript below.
Be concise, clear and accurate. If the answer is not in the transcript, say "I could not find this in the video."

TRANSCRIPT:
{context}"""
        }
    ]
    for h in history[-4:]:
        messages.append({"role": "user", "content": h["question"]})
        messages.append({"role": "assistant", "content": h["answer"]})
    messages.append({"role": "user", "content": question})

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.1-8b-instant",
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.4
        },
        timeout=30
    )
    if r.status_code == 200:
        return r.json()["choices"][0]["message"]["content"].strip()
    else:
        raise Exception(f"Groq API error: {r.text}")


# ── session state ─────────────────────────────────────────────────────
for k, v in [("transcript", ""), ("chat_history", []), ("video_loaded", False), ("video_id", "")]:
    if k not in st.session_state:
        st.session_state[k] = v


# ── STEP 1: API Key ───────────────────────────────────────────────────
st.markdown("### 🔑 Enter Groq API Key")
groq_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...", label_visibility="collapsed")

st.markdown("""
<div class="info-box">
    ✅ <strong>100% Free — No credit card needed!</strong><br><br>
    1. Go to <code>console.groq.com</code><br>
    2. Sign up with Google / GitHub<br>
    3. Click <code>API Keys</code> → <code>Create API Key</code><br>
    4. Copy the <code>gsk_...</code> key and paste above<br><br>
    Free tier: <strong>14,400 requests/day</strong> — more than enough!
</div>
""", unsafe_allow_html=True)

st.divider()

# ── STEP 2: YouTube URL ───────────────────────────────────────────────
st.markdown("### 🔗 Paste YouTube URL")
col1, col2 = st.columns([4, 1])
with col1:
    yt_url = st.text_input("url", placeholder="https://www.youtube.com/watch?v=...", label_visibility="collapsed")
with col2:
    load_btn = st.button("Load ▶")

if load_btn:
    if not groq_key.strip():
        st.error("Please enter your Groq API key first.")
    elif not yt_url.strip():
        st.warning("Please paste a YouTube URL.")
    else:
        video_id = extract_video_id(yt_url)
        if not video_id:
            st.error("Invalid YouTube URL.")
        else:
            with st.spinner("⏳ Fetching transcript automatically..."):
                transcript, error = fetch_transcript(video_id)
                if error:
                    st.error("❌ Could not auto-fetch transcript for this video.")
                    st.markdown("""
                    <div class="info-box">
                        👇 <strong>Use Manual Paste below</strong> — takes 30 seconds:<br>
                        1. Open video on YouTube<br>
                        2. Click <code>(...) More</code> → <code>Show transcript</code><br>
                        3. Select all → Copy → Paste in the box below
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.session_state.transcript = transcript
                    st.session_state.video_id = video_id
                    st.session_state.chat_history = []
                    st.session_state.video_loaded = True

if st.session_state.video_id:
    st.image(f"https://img.youtube.com/vi/{st.session_state.video_id}/0.jpg", use_container_width=True)

if st.session_state.video_loaded:
    wc = len(st.session_state.transcript.split())
    st.markdown(f'<div class="success-box">✅ Transcript loaded — {wc} words — Ask anything below!</div>', unsafe_allow_html=True)

# Manual paste fallback
with st.expander("📋 Manual Paste (if auto-fetch fails)"):
    st.markdown('<div class="info-box">On YouTube: Open video → <code>(...) More</code> → <code>Show transcript</code> → Select all → Copy → Paste below</div>', unsafe_allow_html=True)
    manual_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...", key="manual_url")
    manual_text = st.text_area("Paste transcript here", height=150, key="manual_transcript")
    if st.button("Use This Transcript"):
        if manual_text and len(manual_text.strip()) > 50:
            st.session_state.transcript = manual_text.strip()
            st.session_state.chat_history = []
            st.session_state.video_loaded = True
            if manual_url:
                vid = extract_video_id(manual_url)
                if vid:
                    st.session_state.video_id = vid
            st.success(f"✅ Transcript loaded! {len(manual_text.split())} words")
            st.rerun()
        else:
            st.error("Please paste a longer transcript.")

st.divider()

# ── CHAT ──────────────────────────────────────────────────────────────
st.markdown("### 💬 Ask Anything About the Video")

if not st.session_state.video_loaded:
    st.markdown('<div class="info-box">Complete the steps above to start chatting.</div>', unsafe_allow_html=True)
else:
    suggestions = ["What is this video about?", "Summarize the key points", "What are the main takeaways?", "List any tips mentioned"]
    cols = st.columns(2)
    for i, s in enumerate(suggestions):
        if cols[i % 2].button(s, key=f"chip_{i}"):
            st.session_state["prefill"] = s

    for chat in st.session_state.chat_history:
        st.markdown(f'<div class="chat-user">🧑 {chat["question"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="chat-bot">🤖 {chat["answer"]}</div>', unsafe_allow_html=True)

    prefill = st.session_state.pop("prefill", "")
    question = st.text_input("question", value=prefill,
                              placeholder="e.g. What does the speaker say about AI?",
                              label_visibility="collapsed", key="q_input")

    if st.button("Ask →"):
        if not groq_key.strip():
            st.error("Please enter your Groq API key at the top.")
        elif not question.strip():
            st.warning("Please type a question.")
        else:
            with st.spinner("🤖 Thinking..."):
                try:
                    answer = ask_groq(groq_key, st.session_state.transcript, question, st.session_state.chat_history)
                    st.session_state.chat_history.append({"question": question, "answer": answer})
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")

    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()

st.markdown('<div class="footer">Built with Streamlit + Groq AI (Llama 3) — 100% Free ✨</div>', unsafe_allow_html=True)
