import streamlit as st
import requests
import re
import json

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
    <p>Paste a YouTube link — ask anything — zero API keys</p>
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
    """Fetch transcript via YouTube's timedtext API — no key needed."""
    # Step 1: get the page to find timedtext URL
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    r = requests.get(url, headers=headers, timeout=15)
    html = r.text

    # Step 2: extract caption tracks from page JS
    match = re.search(r'"captionTracks":(\[.*?\])', html)
    if not match:
        return None, "No captions found for this video. Try a video with subtitles enabled."

    try:
        tracks = json.loads(match.group(1))
    except Exception:
        return None, "Could not parse caption data."

    if not tracks:
        return None, "No caption tracks available."

    # Prefer English
    base_url = None
    for track in tracks:
        lang = track.get("languageCode", "")
        if lang.startswith("en"):
            base_url = track.get("baseUrl")
            break
    if not base_url:
        base_url = tracks[0].get("baseUrl")

    if not base_url:
        return None, "Could not find caption URL."

    # Step 3: fetch the actual transcript XML
    r2 = requests.get(base_url + "&fmt=json3", headers=headers, timeout=15)
    data = r2.json()

    events = data.get("events", [])
    lines = []
    for event in events:
        segs = event.get("segs", [])
        text = "".join(s.get("utf8", "") for s in segs).strip()
        if text and text != "\n":
            lines.append(text)

    transcript = " ".join(lines)
    transcript = re.sub(r'\s+', ' ', transcript).strip()

    if len(transcript) < 50:
        return None, "Transcript too short or empty."

    return transcript, None


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


def ask_llm(transcript, question, history):
    context = find_relevant_chunks(transcript, question)

    # Build conversation
    convo = ""
    for h in history[-4:]:
        convo += f"User: {h['question']}\nAssistant: {h['answer']}\n"

    prompt = f"""<s>[INST] You are a helpful AI assistant. Answer the user's question based ONLY on the YouTube video transcript excerpt provided below.
Be concise, clear and accurate. If the answer is not in the transcript, say "I could not find this in the video."

TRANSCRIPT EXCERPT:
{context}

{convo}User: {question} [/INST]"""

    headers_hf = {"Authorization": "Bearer " + st.secrets.get("HF_TOKEN", "")} if "HF_TOKEN" in st.secrets else {}

    models = [
        "mistralai/Mistral-7B-Instruct-v0.3",
        "HuggingFaceH4/zephyr-7b-beta",
        "tiiuae/falcon-7b-instruct",
    ]

    # Try without token first (some models allow anonymous)
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 400, "temperature": 0.4, "return_full_text": False, "do_sample": True}
    }

    for model_id in models:
        url = f"https://api-inference.huggingface.co/models/{model_id}"
        try:
            r = requests.post(url, headers=headers_hf, json=payload, timeout=60)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and data:
                    ans = data[0].get("generated_text", "").strip()
                    if ans:
                        return ans
            elif r.status_code == 503:
                continue
        except Exception:
            continue

    return "The AI model is currently loading. Please wait 20 seconds and try again."


# ── session state ─────────────────────────────────────────────────────

for k, v in [("transcript", ""), ("chat_history", []), ("video_loaded", False), ("video_id", ""), ("video_title", "")]:
    if k not in st.session_state:
        st.session_state[k] = v


# ── STEP 1: Paste YouTube URL ─────────────────────────────────────────

st.markdown("### 🔗 Paste YouTube URL")

col1, col2 = st.columns([4, 1])
with col1:
    yt_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...", label_visibility="collapsed")
with col2:
    load_btn = st.button("Load ▶")

if load_btn and yt_url:
    video_id = extract_video_id(yt_url)
    if not video_id:
        st.error("Invalid YouTube URL. Please check and try again.")
    else:
        with st.spinner("Fetching transcript automatically..."):
            transcript, error = fetch_transcript(video_id)
            if error:
                st.error(f"Could not fetch transcript: {error}")
                st.markdown("""
                <div class="info-box">
                    <strong>Tips:</strong><br>
                    • Make sure the video has <code>subtitles / CC</code> enabled<br>
                    • Try a different YouTube video<br>
                    • Educational videos, TED Talks, tutorials usually work best
                </div>
                """, unsafe_allow_html=True)
            else:
                st.session_state.transcript = transcript
                st.session_state.video_id = video_id
                st.session_state.chat_history = []
                st.session_state.video_loaded = True

# Show thumbnail if video loaded
if st.session_state.video_id:
    st.image(f"https://img.youtube.com/vi/{st.session_state.video_id}/0.jpg", use_container_width=True)

if st.session_state.video_loaded:
    word_count = len(st.session_state.transcript.split())
    st.markdown(f'<div class="success-box">✅ Transcript fetched automatically — {word_count} words — Ready to chat!</div>', unsafe_allow_html=True)

st.divider()

# ── STEP 2: Chat ──────────────────────────────────────────────────────

st.markdown("### 💬 Ask Anything About the Video")

if not st.session_state.video_loaded:
    st.markdown('<div class="info-box">Paste a YouTube URL above and click <code>Load</code> to start.</div>', unsafe_allow_html=True)
else:
    # Quick chips
    suggestions = ["What is this video about?", "Summarize the key points", "What are the main takeaways?", "List any tips mentioned"]
    cols = st.columns(2)
    for i, s in enumerate(suggestions):
        if cols[i % 2].button(s, key=f"chip_{i}"):
            st.session_state["prefill"] = s

    # Chat history
    for chat in st.session_state.chat_history:
        st.markdown(f'<div class="chat-user">🧑 {chat["question"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="chat-bot">🤖 {chat["answer"]}</div>', unsafe_allow_html=True)

    prefill = st.session_state.pop("prefill", "")
    question = st.text_input("Your question", value=prefill,
                              placeholder="e.g. What does the speaker say about AI?",
                              label_visibility="collapsed", key="q_input")

    if st.button("Ask →"):
        if not question.strip():
            st.warning("Please type a question.")
        else:
            with st.spinner("Thinking..."):
                answer = ask_llm(st.session_state.transcript, question, st.session_state.chat_history)
                st.session_state.chat_history.append({"question": question, "answer": answer})
                st.rerun()

    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()

st.markdown('<div class="footer">Built with Streamlit — Zero API Keys — 100% Free ✨</div>', unsafe_allow_html=True)
