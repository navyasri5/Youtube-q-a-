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
.tab-box { background: #111827; border: 1px solid #1f2937; border-radius: 10px; padding: 1rem; margin-bottom: 1rem; }
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


def fetch_transcript_method1(video_id):
    """Method 1: Fetch via YouTube timedtext API directly."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    session = requests.Session()

    # Get the YouTube page
    r = session.get(f"https://www.youtube.com/watch?v={video_id}", headers=headers, timeout=15)
    html_content = r.text

    # Try multiple regex patterns to find caption data
    patterns = [
        r'"captionTracks":(\[.*?\])',
        r'"captions".*?"captionTracks":(\[.*?\])',
        r'playerCaptionsTracklistRenderer.*?"captionTracks":(\[.*?\])',
    ]

    tracks = None
    for pattern in patterns:
        match = re.search(pattern, html_content)
        if match:
            try:
                tracks = json.loads(match.group(1))
                if tracks:
                    break
            except Exception:
                continue

    if not tracks:
        return None

    # Prefer English
    base_url = None
    for track in tracks:
        lang = track.get("languageCode", "")
        if "en" in lang.lower():
            base_url = track.get("baseUrl")
            break
    if not base_url:
        base_url = tracks[0].get("baseUrl")

    if not base_url:
        return None

    # Fetch transcript XML
    r2 = session.get(base_url, headers=headers, timeout=15)
    xml_text = r2.text

    # Parse XML
    try:
        root = ET.fromstring(xml_text)
        lines = []
        for elem in root.findall(".//text"):
            raw = elem.text or ""
            clean = html_module.unescape(raw)
            clean = re.sub(r'<[^>]+>', '', clean).strip()
            if clean:
                lines.append(clean)
        transcript = " ".join(lines)
        transcript = re.sub(r'\s+', ' ', transcript).strip()
        if len(transcript) > 100:
            return transcript
    except Exception:
        pass

    return None


def fetch_transcript_method2(video_id):
    """Method 2: Use youtubetranscript.com free API."""
    try:
        r = requests.get(
            f"https://youtubetranscript.com/?server_vid2={video_id}",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        if r.status_code == 200:
            # Parse XML response
            root = ET.fromstring(r.text)
            lines = []
            for elem in root.findall(".//text"):
                raw = elem.text or ""
                clean = html_module.unescape(raw).strip()
                clean = re.sub(r'<[^>]+>', '', clean).strip()
                if clean:
                    lines.append(clean)
            transcript = " ".join(lines)
            transcript = re.sub(r'\s+', ' ', transcript).strip()
            if len(transcript) > 100:
                return transcript
    except Exception:
        pass
    return None


def fetch_transcript_method3(video_id):
    """Method 3: supadata.ai free transcript API."""
    try:
        r = requests.get(
            f"https://api.supadata.ai/v1/youtube/transcript?videoId={video_id}&lang=en",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        if r.status_code == 200:
            data = r.json()
            content = data.get("content", "") or data.get("transcript", "")
            if isinstance(content, list):
                content = " ".join([c.get("text","") for c in content])
            if content and len(content) > 100:
                return content.strip()
    except Exception:
        pass
    return None


def fetch_transcript(video_id):
    """Try all methods in order."""
    transcript = fetch_transcript_method1(video_id)
    if transcript:
        return transcript, None

    transcript = fetch_transcript_method2(video_id)
    if transcript:
        return transcript, None

    transcript = fetch_transcript_method3(video_id)
    if transcript:
        return transcript, None

    return None, "Could not auto-fetch transcript for this video."


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
    convo = ""
    for h in history[-4:]:
        convo += f"User: {h['question']}\nAssistant: {h['answer']}\n"

    prompt = f"""<s>[INST] You are a helpful AI assistant. Answer based ONLY on the transcript excerpt below. Be concise and accurate. If not found, say "I could not find this in the video."

TRANSCRIPT:
{context}

{convo}User: {question} [/INST]"""

    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 400, "temperature": 0.4, "return_full_text": False, "do_sample": True}
    }

    hf_headers = {}
    try:
        hf_headers = {"Authorization": f"Bearer {st.secrets['HF_TOKEN']}"}
    except Exception:
        pass

    for model_id in ["mistralai/Mistral-7B-Instruct-v0.3", "HuggingFaceH4/zephyr-7b-beta", "tiiuae/falcon-7b-instruct"]:
        try:
            r = requests.post(f"https://api-inference.huggingface.co/models/{model_id}",
                              headers=hf_headers, json=payload, timeout=60)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and data:
                    ans = data[0].get("generated_text", "").strip()
                    if ans:
                        return ans
        except Exception:
            continue

    return "⚠️ AI model is loading. Please wait 20 seconds and try again."


# ── session state ─────────────────────────────────────────────────────
for k, v in [("transcript", ""), ("chat_history", []), ("video_loaded", False), ("video_id", "")]:
    if k not in st.session_state:
        st.session_state[k] = v


# ── UI ────────────────────────────────────────────────────────────────

st.markdown("### 🔗 Paste YouTube URL")
col1, col2 = st.columns([4, 1])
with col1:
    yt_url = st.text_input("url", placeholder="https://www.youtube.com/watch?v=...", label_visibility="collapsed")
with col2:
    load_btn = st.button("Load ▶")

if load_btn:
    if not yt_url.strip():
        st.warning("Please paste a YouTube URL.")
    else:
        video_id = extract_video_id(yt_url)
        if not video_id:
            st.error("Invalid YouTube URL.")
        else:
            with st.spinner("⏳ Fetching transcript (trying multiple methods)..."):
                transcript, error = fetch_transcript(video_id)
                if error:
                    st.error("❌ Could not auto-fetch transcript.")
                    st.markdown("""
                    <div class="info-box">
                        <strong>YouTube is blocking auto-fetch for this video.</strong><br><br>
                        👇 <strong>Use the Manual Paste tab below</strong> — it takes 30 seconds:<br>
                        1. Open the video on YouTube<br>
                        2. Click <code>(...) More</code> → <code>Show transcript</code><br>
                        3. Select all transcript text → Copy → Paste below
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.session_state.transcript = transcript
                    st.session_state.video_id = video_id
                    st.session_state.chat_history = []
                    st.session_state.video_loaded = True

# Show thumbnail
if st.session_state.video_id:
    st.image(f"https://img.youtube.com/vi/{st.session_state.video_id}/0.jpg", use_container_width=True)

if st.session_state.video_loaded:
    wc = len(st.session_state.transcript.split())
    st.markdown(f'<div class="success-box">✅ Transcript loaded — {wc} words — Ask anything below!</div>', unsafe_allow_html=True)

# Manual paste fallback
with st.expander("📋 Manual Paste (if auto-fetch fails)"):
    st.markdown("""
    <div class="info-box">
        On YouTube: Open video → <code>(...) More</code> → <code>Show transcript</code> → Select all → Copy → Paste below
    </div>
    """, unsafe_allow_html=True)
    manual_url = st.text_input("YouTube URL (for thumbnail)", placeholder="https://www.youtube.com/watch?v=...", key="manual_url")
    manual_text = st.text_area("Paste transcript here", height=150, placeholder="Paste transcript here...", key="manual_transcript")
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
    st.markdown('<div class="info-box">Paste a YouTube URL above and click <code>Load ▶</code> to begin.</div>', unsafe_allow_html=True)
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
    question = st.text_input("question", value=prefill, placeholder="e.g. What does the speaker say about AI?",
                              label_visibility="collapsed", key="q_input")

    if st.button("Ask →"):
        if not question.strip():
            st.warning("Please type a question.")
        else:
            with st.spinner("🤖 Thinking..."):
                answer = ask_llm(st.session_state.transcript, question, st.session_state.chat_history)
                st.session_state.chat_history.append({"question": question, "answer": answer})
                st.rerun()

    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()

st.markdown('<div class="footer">Built with Streamlit — Zero API Keys — 100% Free ✨</div>', unsafe_allow_html=True)
