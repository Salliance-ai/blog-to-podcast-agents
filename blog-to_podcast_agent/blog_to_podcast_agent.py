<REAL_APP_CODE_HERE
import streamlit as st
import requests
from bs4 import BeautifulSoup
import openai
import os
from io import BytesIO
import asyncio
import edge_tts
from pydub import AudioSegment
import zipfile

openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="Blog to Podcast Agent", layout="centered")

st.image("logo.png", width=120)
st.title("📰 → 🎙️ Blog to Podcast Agent")
st.caption("Turn written content into warm, engaging audio experiences.")

url = st.text_input("Enter blog post URL", value="https://www.nimh.nih.gov/health/topics/depression")

# Voice options
voice_options = {
    "Jenny (Female, Warm)": "en-US-JennyNeural",
    "Guy (Male, Conversational)": "en-US-GuyNeural",
    "Davis (Male, Calm)": "en-US-DavisNeural",
    "Aria (Female, Formal)": "en-US-AriaNeural"
}
selected_voice = st.selectbox("Select voice style", list(voice_options.keys()))
voice_id = voice_options[selected_voice]

async def generate_edge_tts_audio(text, voice="en-US-JennyNeural"):
    communicate = edge_tts.Communicate(text, voice)
    mp3_fp = BytesIO()
    await communicate.save_stream(mp3_fp)
    mp3_fp.seek(0)
    return mp3_fp

def load_intro():
    try:
        return AudioSegment.from_file("intro.mp3")
    except Exception:
        return None

if url and st.button("Generate Script & Audio"):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        paragraphs = soup.find_all('p')
        blog_text = "\n\n".join(p.get_text() for p in paragraphs if p.get_text().strip())

        if not blog_text:
            st.error("No readable text found at this URL.")
        else:
            prompt = f"""
You are a compassionate mental health podcast host.

Convert the following blog into a script with:
- A soothing tone
- A clear 2-minute length (approx. 300-350 words)
- A short intro, 2–3 key insights, and an encouraging outro

Make it conversational, as if speaking to someone who may be struggling.

Blog content:
{blog_text}
"""
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            script = response.choices[0].message.content.strip()
            st.subheader("🎙️ Podcast Script")
            st.text_area("Generated Podcast Script", script, height=400)

            st.subheader("🔊 Generating Audio...")
            audio_bytes = asyncio.run(generate_edge_tts_audio(script, voice=voice_id))

            intro = load_intro()
            if intro:
                speech = AudioSegment.from_file(audio_bytes, format="mp3")
                combined = intro + speech
                combined_buffer = BytesIO()
                combined.export(combined_buffer, format="mp3")
                combined_buffer.seek(0)
                audio_data = combined_buffer
            else:
                audio_data = audio_bytes

            st.audio(audio_data, format="audio/mp3")
            st.download_button("⬇️ Download MP3", audio_data, "podcast_audio.mp3", "audio/mp3")

            # ZIP bundle
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                zip_file.writestr("podcast_script.txt", script)
                zip_file.writestr("podcast_audio.mp3", audio_data.getvalue())
            zip_buffer.seek(0)
            st.download_button("📦 Download Script + Audio (ZIP)", zip_buffer, "podcast_bundle.zip", "application/zip")

    except Exception as e:
        st.error(f"Error fetching or processing the blog: {e}")
