import streamlit as st
import google.generativeai as genai
import re

st.set_page_config(
    page_title="YouTube Video Q&A",
    page_icon="🎬",
    layout="centered"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
.stApp { background: #0a0a0f; color: #e8e8f0; }
.main-header { text-align: center; padding: 2rem 0 1rem 0; }
.main-header h1 { font-size: 2.5rem; font-weight: 600; background: linear-gradient(135deg, #a78bfa, #60a5fa, #34d399); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem; }
.main-header p { color: #6b7280; font-size: 1rem; }
.step-badge { display: inline-block; background: #1a1a2e; border: 1px solid #2d2d4e; color: #a78bfa; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; padding: 2px 10px; border-radius: 20px; margin-bottom: 0.5rem; }
.info-box { background: #111827; border: 1px solid #1f2937; border-left: 3px solid #a78bfa; border-radius: 8px; padding: 1rem 1.2rem; margin: 1rem 0; font-size: 0.9rem; color: #9ca3af; }
.info-box code { background: #1f2937; padding: 2px 6px; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #60a5fa; }
.chat-user { background: #1e1b4b; border: 1px solid #312e81; border-radius: 12px 12px 2px 12px; padding: 0.8rem 1.1rem; margin: 0.5rem 0; margin-left: 20%; color: #e0e7ff; font-size: 0.95rem; }
.chat-bot { background: #111827; border: 1px solid #1f2937; border-radius: 12px 12px 12px 2px; padding: 0.8rem 1.1rem; margin: 0.5rem 0; margin-right: 20%; color: #d1d5db; font-size: 0.95rem; line-height: 1.6; }
.transcript-loaded { background: #052e16; border: 1px solid #166534; border-radius: 8px; padding: 0.8rem 1.2rem; color: #86efac; font-size: 0.9rem; margin: 0.5rem 0; }
.stTextInput > div > div > input, .stTextArea > div > div > textarea { background: #111827 !important; border: 1px solid #1f2937 !important; border-radius: 8px !important; color: #e8e8f0 !important; font-family: 'Space Grotesk', sans-serif !important; }
.stButton > button { background: linear-gradient(135deg, #7c3aed, #4f46e5); color: white; border: none; border-radius: 8px; padding: 0.5rem 1.5rem; font-family: 'Space Grotesk', sans-serif; font-weight: 500; width: 100%; }
.stButton > button:hover { opacity: 0.9; border: none; color: white; }
.footer { text-align: center; padding: 2rem 0 1rem; color: #374151; font-size: 0.8rem; }
</style>
<div class="main-header">
    <h1>🎬 YouTube Q&A</h1>
    <p>Ask anything about any YouTube video — 100% Free</p>
</div>
""", unsafe_allow_html=True)


def extract_video_id(url: str):
    patterns = [r'(?:v=|\/)([0-9A-Za-z_-]{11})', r'youtu\.be\/([0-9A-Za-z_-]{11})']
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def ask_gemini(transcript: str, question: str, history: list) -> str:
    genai.configure(api_key=st.session_state.api_key)

    # Build conversation messages
    messages = []
    for h in history:
        messages.append({"role": "user", "parts": [h["question"]]})
        messages.append({"role": "model", "parts": [h["answer"]]})
    messages.append({"role": "user", "parts": [question]})

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=f"""You are a helpful assistant that answers questions based ONLY on the provided YouTube video transcript.
Be concise, clear, and accurate. If the answer is not found in the transcript, say so honestly.
Do not make up information.

VIDEO TRANSCRIPT:
{transcript[:8000]}"""
    )

    response = model.generate_content(messages)
    return response.text


# --- Session State ---
for key, val in [("transcript", ""), ("chat_history", []), ("video_loaded", False), ("api_key", "")]:
    if key not in st.session_state:
        st.session_state[key] = val


# --- STEP 1: API Key ---
st.markdown('<div class="step-badge">STEP 1 — FREE API KEY</div>', unsafe_allow_html=True)
st.markdown("**Enter your Google Gemini API Key**")
api_key = st.text_input("API Key", type="password", placeholder="AIza...", label_visibility="collapsed")
if api_key:
    st.session_state.api_key = api_key

st.markdown("""
<div class="info-box">
    ✅ <strong>100% Free — No credit card needed!</strong><br><br>
    1. Go to <code>aistudio.google.com</code><br>
    2. Sign in with Google<br>
    3. Click <code>Get API Key</code> → <code>Create API key</code><br>
    4. Copy and paste it above
</div>
""", unsafe_allow_html=True)

st.divider()

# --- STEP 2: YouTube URL ---
st.markdown('<div class="step-badge">STEP 2 — YOUTUBE URL</div>', unsafe_allow_html=True)
st.markdown("**Paste a YouTube URL**")
yt_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...", label_visibility="collapsed")

video_id = None
if yt_url:
    video_id = extract_video_id(yt_url)
    if video_id:
        st.image(f"https://img.youtube.com/vi/{video_id}/0.jpg", use_container_width=True)
    else:
        st.warning("Please enter a valid YouTube URL.")

st.divider()

# --- STEP 3: Transcript ---
st.markdown('<div class="step-badge">STEP 3 — PASTE TRANSCRIPT</div>', unsafe_allow_html=True)
st.markdown("**Paste the video transcript**")
st.markdown("""
<div class="info-box">
    On YouTube: Open video → click <code>(...) More</code> below video → <code>Show transcript</code> → Select all → Copy → Paste below.
</div>
""", unsafe_allow_html=True)

transcript_input = st.text_area("Transcript", placeholder="Paste the full transcript here...", height=180, label_visibility="collapsed")

if st.button("✅ Load Transcript & Start Q&A"):
    if not st.session_state.api_key:
        st.error("Please enter your Gemini API key first.")
    elif not video_id:
        st.error("Please enter a valid YouTube URL.")
    elif not transcript_input or len(transcript_input.strip()) < 50:
        st.error("Please paste a transcript with enough content.")
    else:
        st.session_state.transcript = transcript_input.strip()
        st.session_state.chat_history = []
        st.session_state.video_loaded = True
        st.success(f"✅ Transcript loaded! ({len(transcript_input.split())} words) — Ready for Q&A!")

st.divider()

# --- STEP 4: Chat ---
st.markdown('<div class="step-badge">STEP 4 — ASK QUESTIONS</div>', unsafe_allow_html=True)
st.markdown("**Ask anything about the video**")

if not st.session_state.video_loaded:
    st.markdown('<div class="info-box">Complete steps 1–3 above to start chatting with the video.</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="transcript-loaded">✅ Transcript ready — {len(st.session_state.transcript.split())} words loaded</div>', unsafe_allow_html=True)

    suggestions = ["What is this video about?", "Summarize the key points", "What are the main takeaways?", "List any tips mentioned"]
    cols = st.columns(2)
    for i, s in enumerate(suggestions):
        if cols[i % 2].button(s, key=f"chip_{i}"):
            st.session_state["prefill_question"] = s

    for chat in st.session_state.chat_history:
        st.markdown(f'<div class="chat-user">🧑 {chat["question"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="chat-bot">🤖 {chat["answer"]}</div>', unsafe_allow_html=True)

    prefill = st.session_state.pop("prefill_question", "")
    question = st.text_input("Your question", value=prefill, placeholder="e.g. What are the main topics discussed?", label_visibility="collapsed", key="question_input")

    if st.button("Ask →"):
        if not question.strip():
            st.warning("Please type a question.")
        else:
            with st.spinner("Thinking..."):
                try:
                    answer = ask_gemini(st.session_state.transcript, question, st.session_state.chat_history)
                    st.session_state.chat_history.append({"question": question, "answer": answer})
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")

    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()

st.markdown('<div class="footer">Built with Streamlit + Google Gemini 2.0 Flash — 100% Free ✨</div>', unsafe_allow_html=True)
