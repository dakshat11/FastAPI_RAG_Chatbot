"""
CareerMind — AI Voice Chatbot Frontend
Streamlit demo app for the FastAPI RAG Voice Agent backend.

Tabs:
  1. Text Chat   — full conversation with memory
  2. Voice Chat  — speak → agent replies in audio
  3. Documents   — upload PDF, check status

Install:
  pip install streamlit requests audiorecorder

Run:
  cd frontend
  streamlit run app.py
"""

import io
import os
import uuid

import requests
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CareerMind AI",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0f1117; }
    [data-testid="stSidebar"] { background-color: #1a1d27; border-right: 1px solid #2d3142; }

    .user-bubble {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        margin: 8px 0 8px 15%;
        font-size: 15px; line-height: 1.5;
    }
    .bot-bubble {
        background: #1e2130;
        color: #e8eaf6;
        padding: 12px 18px;
        border-radius: 18px 18px 18px 4px;
        margin: 8px 15% 8px 0;
        font-size: 15px; line-height: 1.5;
        border: 1px solid #2d3142;
    }
    .bubble-label { font-size: 11px; color: #888; margin: 12px 0 4px 0; }
    .info-card {
        background: #1e2130;
        border: 1px solid #2d3142;
        border-radius: 12px;
        padding: 16px 20px; margin: 8px 0;
    }
    .status-ok  { color: #4caf50; font-weight: 600; }
    .status-err { color: #f44336; font-weight: 600; }
    header[data-testid="stHeader"] { display: none; }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; border: none; border-radius: 8px;
        font-weight: 600; padding: 8px 20px;
    }
    .stTabs [data-baseweb="tab"] { color: #aaa; font-size: 15px; font-weight: 600; }
    .stTabs [aria-selected="true"] { color: #667eea; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "thread_id"    not in st.session_state: st.session_state.thread_id    = str(uuid.uuid4())[:8]
if "messages"     not in st.session_state: st.session_state.messages     = []
if "api_base"     not in st.session_state: st.session_state.api_base     = os.environ.get("API_URL", "http://localhost:8000")
if "doc_uploaded" not in st.session_state: st.session_state.doc_uploaded = False
if "doc_name"     not in st.session_state: st.session_state.doc_name     = None

# ── Backend helper ────────────────────────────────────────────────────────────
def api(method: str, path: str, **kwargs):
    url = f"{st.session_state.api_base}{path}"
    try:
        return getattr(requests, method)(url, timeout=60, **kwargs)
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot reach the backend. Is FastAPI running on localhost:8000?")
    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out. The model may be slow — try again.")
    return None

def backend_ok() -> bool:
    r = api("get", "/health")
    return r is not None and r.status_code == 200

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎙️ CareerMind AI")
    st.markdown("*RAG · Voice · Memory · Tools*")
    st.divider()

    if backend_ok():
        st.markdown('<span class="status-ok">● Backend connected</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-err">● Backend offline</span>', unsafe_allow_html=True)

    st.divider()
    st.markdown("### 💬 Conversation")

    thread_input = st.text_input("Thread ID", value=st.session_state.thread_id)
    if thread_input != st.session_state.thread_id:
        st.session_state.thread_id    = thread_input
        st.session_state.messages     = []
        st.session_state.doc_uploaded = False
        st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔀 New", use_container_width=True):
            st.session_state.thread_id    = str(uuid.uuid4())[:8]
            st.session_state.messages     = []
            st.session_state.doc_uploaded = False
            st.session_state.doc_name     = None
            st.rerun()
    with c2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    st.divider()
    st.markdown("### 📄 Document")
    if st.session_state.doc_uploaded:
        st.markdown(
            f'<div class="info-card">✅ <b>{st.session_state.doc_name}</b><br>'
            f'<small>Thread: <code>{st.session_state.thread_id}</code></small></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="info-card">📭 No document uploaded.</div>', unsafe_allow_html=True)

    st.divider()
    with st.expander("⚙️ Settings"):
        new_base = st.text_input("API Base URL", value=st.session_state.api_base)
        if new_base != st.session_state.api_base:
            st.session_state.api_base = new_base

    st.markdown("### 🛠️ Active Tools")
    st.markdown("- 🔍 Web search\n- 📄 Document RAG\n- 🧮 Calculator\n- 📈 Stock prices")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# CareerMind AI Agent")
st.markdown(
    f"**Thread:** `{st.session_state.thread_id}` &nbsp;|&nbsp; "
    f"**Messages:** `{len(st.session_state.messages)}`"
)
st.divider()

tab_text, tab_voice, tab_docs = st.tabs(["💬 Text Chat", "🎙️ Voice Chat", "📄 Documents"])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — TEXT CHAT
# ─────────────────────────────────────────────────────────────────────────────
with tab_text:

    # Render history
    if not st.session_state.messages:
        st.markdown("""
        <div style="text-align:center;color:#555;padding:60px 0;">
            <div style="font-size:48px;">🤖</div>
            <div style="font-size:18px;margin-top:12px;">Ask me anything.</div>
            <div style="font-size:14px;color:#444;margin-top:8px;">
                Upload a PDF first to enable document Q&A.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown('<div class="bubble-label">You</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="user-bubble">{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="bubble-label">CareerMind</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="bot-bubble">{msg["content"]}</div>', unsafe_allow_html=True)

    st.divider()

    # Input
    col_i, col_s = st.columns([5, 1])
    with col_i:
        user_input = st.text_input(
            "Message", placeholder="Type your message here…",
            label_visibility="collapsed", key="chat_input"
        )
    with col_s:
        send_btn = st.button("Send →", use_container_width=True)

    if send_btn and user_input.strip():
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.spinner("Thinking…"):
            r = api("post", "/api/v1/chat/",
                    json={"thread_id": st.session_state.thread_id, "message": user_input})
        if r and r.status_code == 200:
            reply = r.json().get("reply", "")
            st.session_state.messages.append({"role": "assistant", "content": reply})
        elif r:
            st.error(f"API error {r.status_code}: {r.text}")
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — VOICE CHAT
# ─────────────────────────────────────────────────────────────────────────────
with tab_voice:

    st.markdown("### 🎙️ Voice Chat")
    st.markdown(
        "Record or upload audio → agent transcribes, thinks, and replies in speech."
    )

    col_in, col_out = st.columns([1, 1])

    with col_in:
        st.markdown("#### 🎤 Input")
        audio_bytes_to_send = None
        audio_filename = "audio.mp3"

        # ── File upload ──
        st.markdown("**Upload an audio file:**")
        uploaded_voice = st.file_uploader(
            "Upload audio", type=["mp3", "wav", "m4a", "webm", "ogg"],
            label_visibility="collapsed", key="voice_file"
        )
        if uploaded_voice:
            audio_bytes_to_send = uploaded_voice.read()
            audio_filename = uploaded_voice.name
            ext = audio_filename.split(".")[-1]
            st.audio(audio_bytes_to_send, format=f"audio/{ext}")

        send_voice_btn = st.button(
            "🚀 Send to Agent", use_container_width=True,
            disabled=(audio_bytes_to_send is None)
        )

    with col_out:
        st.markdown("#### 🔊 Response")

        if send_voice_btn and audio_bytes_to_send:
            ext = audio_filename.split(".")[-1]
            with st.spinner("Transcribing → Thinking → Speaking…"):
                r = api(
                    "post",
                    f"/api/v1/voice/chat?thread_id={st.session_state.thread_id}",
                    files={"file": (audio_filename, audio_bytes_to_send, f"audio/{ext}")},
                )

            if r and r.status_code == 200:
                transcript = r.headers.get("X-Transcript", "")
                reply_text = r.headers.get("X-Reply-Text", "")

                if transcript:
                    st.markdown("**You said:**")
                    st.markdown(f'<div class="info-card">🗣️ {transcript}</div>',
                                unsafe_allow_html=True)
                    st.session_state.messages.append(
                        {"role": "user", "content": f"🎙️ {transcript}"}
                    )

                if reply_text:
                    st.markdown("**Agent replied:**")
                    st.markdown(f'<div class="info-card">🤖 {reply_text}</div>',
                                unsafe_allow_html=True)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": reply_text}
                    )

                st.markdown("**Listen:**")
                st.audio(r.content, format="audio/mp3", autoplay=True)
                st.download_button(
                    "⬇️ Download reply audio", data=r.content,
                    file_name="agent_reply.mp3", mime="audio/mpeg",
                    use_container_width=True,
                )
            elif r:
                st.error(f"Error {r.status_code}: {r.text}")

        else:
            st.markdown("""
            <div style="text-align:center;color:#444;padding:80px 0;">
                <div style="font-size:48px;">🔊</div>
                <div style="margin-top:12px;">Audio reply appears here.</div>
            </div>
            """, unsafe_allow_html=True)

    # Show shared conversation
    if st.session_state.messages:
        with st.expander("📜 Conversation history (last 6)"):
            for msg in st.session_state.messages[-6:]:
                icon = "🧑" if msg["role"] == "user" else "🤖"
                st.markdown(f"**{icon}** {msg['content']}")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — DOCUMENTS
# ─────────────────────────────────────────────────────────────────────────────
with tab_docs:

    st.markdown("### 📄 PDF Document Upload")
    st.markdown(
        "Upload a PDF to enable document-aware conversations. "
        "Chunks are embedded into Pinecone under your thread namespace."
    )

    col_up, col_st = st.columns([1, 1])

    with col_up:
        st.markdown("#### Upload")
        pdf_file = st.file_uploader(
            "Choose PDF", type=["pdf"],
            label_visibility="collapsed", key="pdf_file"
        )

        if pdf_file:
            st.markdown(
                f'<div class="info-card">📄 <b>{pdf_file.name}</b><br>'
                f'<small>{round(pdf_file.size / 1024, 1)} KB</small></div>',
                unsafe_allow_html=True,
            )
            if st.button("⬆️ Upload & Index", use_container_width=True):
                with st.spinner(f"Embedding {pdf_file.name} into Pinecone…"):
                    r = api(
                        "post",
                        f"/api/v1/pdf/upload?thread_id={st.session_state.thread_id}",
                        files={"file": (pdf_file.name, pdf_file.getvalue(), "application/pdf")},
                    )

                if r and r.status_code == 200:
                    data = r.json()
                    st.success("✅ Document indexed!")
                    st.session_state.doc_uploaded = True
                    st.session_state.doc_name = pdf_file.name

                    ca, cb, cc = st.columns(3)
                    ca.metric("Pages", data.get("documents", "—"))
                    cb.metric("Chunks", data.get("chunks", "—"))
                    cc.metric("Thread", st.session_state.thread_id)

                    st.info(
                        "Switch to **Text Chat** or **Voice Chat** and ask:\n"
                        "*\"Summarise this document\"*"
                    )
                    st.rerun()
                elif r:
                    st.error(f"Upload failed {r.status_code}: {r.text}")

    with col_st:
        st.markdown("#### Thread Status")
        if st.button("🔄 Check", use_container_width=True):
            r = api("get", f"/api/v1/threads/{st.session_state.thread_id}")
            if r and r.status_code == 200:
                data = r.json()
                has_doc  = data.get("has_document", False)
                doc_name = data.get("filename", "Unknown")
                chunks   = data.get("chunks", 0)

                st.markdown(
                    f'<div class="info-card">'
                    f'<b>Thread:</b> <code>{st.session_state.thread_id}</code><br><br>'
                    f'<b>Document:</b> {"✅ " + doc_name if has_doc else "❌ None"}<br>'
                    f'{"<b>Chunks:</b> " + str(chunks) if has_doc else ""}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if has_doc:
                    st.session_state.doc_uploaded = True
                    st.session_state.doc_name     = doc_name

        st.divider()
        st.markdown("#### How RAG Works")
        st.code(
            "PDF → split into chunks\n"
            "    → embed with OpenAI\n"
            "    → store in Pinecone\n"
            "       namespace=thread_id\n\n"
            "Query → embed question\n"
            "      → top-4 similar chunks\n"
            "      → LLM reads + answers",
            language="text",
        )

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    f"<div style='text-align:center;color:#444;font-size:13px;'>"
    f"CareerMind AI · FastAPI + LangGraph + Pinecone + OpenAI · "
    f"Thread: <code>{st.session_state.thread_id}</code></div>",
    unsafe_allow_html=True,
)