import os
import random
import re
import string
import tempfile
import requests
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
import streamlit as st
from moviepy.editor import VideoFileClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
import whisper
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Download VADER lexicon if not already downloaded
nltk.download('vader_lexicon', quiet=True)

# Load environment variables
load_dotenv("users.env")
load_dotenv("apikey.env")

# API key
infosys_api_key = os.getenv('INFOSYS_API_KEY')

# Ensure required directories exist
upload_dirs = ['uploads', 'uploads/audio', 'uploads/transcripts', 'uploads/profile_pictures', 'uploads/reels']
for directory in upload_dirs:
    os.makedirs(directory, exist_ok=True)

# Initialize Whisper model and Sentiment Analyzer
whisper_model = whisper.load_model("base")
sentiment_analyzer = SentimentIntensityAnalyzer()

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT')
        )
        return conn
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

# Validation functions
def is_valid_email(email):
    return re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email) is not None

def is_valid_username(username):
    return re.match(r"^@[a-zA-Z][\w_.]*$", username) is not None

def is_strong_password(password):
    return (
        len(password) >= 8 and
        any(c.isdigit() for c in password) and
        any(c.islower() for c in password) and
        any(c.isupper() for c in password) and
        any(c in string.punctuation for c in password)
    )

def is_valid_full_phone(phone):
    return re.match(r"^[962]\d{9}$", phone) is not None

# User registration and login functions
def register_user(full_name, username, email, password, phone, profession, dob, short_desc, profile_picture_path, country_code):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (full_name, username, email, password, phone, profession, dob, short_desc, profile_picture, country_code)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (full_name, username, email, password, phone, profession, dob.strftime('%Y-%m-%d'), short_desc, profile_picture_path, country_code)
                )
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Error during registration: {e}")
            return False
        finally:
            conn.close()

def verify_user(email, password):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
                return cursor.fetchone()
        except Exception as e:
            st.error(f"Error during user verification: {e}")
            return None
        finally:
            conn.close()

# Video processing functions
def extract_audio_from_video(video_path, output_audio_path):
    try:
        with VideoFileClip(video_path) as video:
            audio = video.audio
            audio.write_audiofile(output_audio_path, codec='pcm_s16le')
        return True
    except Exception as e:
        st.error(f"Error extracting audio: {e}")
        return False

def transcribe_audio_whisper(audio_path, language="English"):
    language_codes = {
        "English": "en",
        "Hindi": "hi",
        "Tamil": "ta",
        "Malayalam": "ml"
    }
    try:
        result = whisper_model.transcribe(audio_path, language=language_codes.get(language, "en"))
        return result["segments"]
    except Exception as e:
        st.error(f"Error during transcription: {e}")
        return None

def save_transcript(transcript, filename, username):
    transcript_path = f"uploads/transcripts/{username}_{filename}.txt"
    try:
        with open(transcript_path, "w", encoding="utf-8") as f:
            for segment in transcript:
                f.write(f"[{segment['start']:.2f}s - {segment['end']:.2f}s]: {segment['text']}\n")
        return transcript_path
    except Exception as e:
        st.error(f"Error saving transcript: {e}")
        return None

def analyze_sentiment(segments):
    return [segment for segment in segments if sentiment_analyzer.polarity_scores(segment['text'])['compound'] > 0.05]

def create_motivational_reel(segments):
    text_batch = "\n".join(segment['text'] for segment in segments)
    messages = [
        {"role": "system", "content": "You are a helpful assistant specializing in generating motivational content based on sentiment."},
        {"role": "user", "content": f"Analyze the sentiment of the following texts and provide a motivational summary: {text_batch}"}
    ]

    headers = {
        "Authorization": f"Bearer {infosys_api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-3.5-turbo",
        "messages": messages,
        "max_tokens": 150
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        st.error("Failed to generate motivational content.")
        return None

def create_reel(segments, video_path, username, reel_index):
    video_clips = []
    
    # Load the video file once at the beginning
    try:
        with VideoFileClip(video_path) as video:
            for segment in segments:
                start_time = segment['start']
                end_time = segment['end']
                
                # Ensure segment is within the video duration
                if 0 <= start_time < video.duration and 0 < end_time <= video.duration and start_time < end_time:
                    # Extract the video segment
                    video_segment = video.subclip(start_time, end_time)
                    video_clips.append(video_segment)
                else:
                    print(f"Invalid segment: start={start_time}, end={end_time}. Skipping this segment.")

            # Check if any valid clips were added
            if not video_clips:
                raise ValueError("No valid video clips were created.")

            # Concatenate all the clips into one reel
            final_reel = concatenate_videoclips(video_clips)
            
            # Save the reel to a file
            reel_path = f"uploads/reels/{username}_reel_{reel_index}.mp4"
            final_reel.write_videofile(reel_path, codec="libx264", audio_codec="aac")
            return reel_path
    
    except Exception as e:
        print(f"Error while creating the reel: {e}")
        return None  # Return None if an error occurs

def process_video_upload(video_file, username, language):
    with st.spinner("Processing video..."):
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
            temp_video.write(video_file.getbuffer())
            video_path = temp_video.name

        audio_path = f"uploads/audio/{username}_{video_file.name}.wav"
        
        st.text("Extracting audio...")
        if not extract_audio_from_video(video_path, audio_path):
            return None, None, []  # Return three values: None for motivational contents, None for transcript path, empty list for reels

        st.text("Transcribing audio...")
        segments = transcribe_audio_whisper(audio_path, language)
        if not segments:
            return None, None, []  # Return three values

        st.text("Analyzing sentiment...")
        important_segments = analyze_sentiment(segments)

        st.text("Creating motivational content...")
        motivational_contents = create_motivational_reel(important_segments)

        # Create three different reels from the important segments
        reels_paths = []
        if len(important_segments) >= 3:
            # Divide segments into three groups based on sentiment or other criteria
            segment_count = len(important_segments) // 3
            for i in range(3):
                start_index = i * segment_count
                end_index = start_index + segment_count
                group_segments = important_segments[start_index:end_index]
                reel_path = create_reel(group_segments, video_path, username, i + 1)  # Pass video_path here
                reels_paths.append(reel_path)

        st.text("Saving transcript...")
        transcript_path = save_transcript(important_segments, video_file.name, username)

        os.unlink(video_path)
        
        return motivational_contents, transcript_path, reels_paths, important_segments  # Ensure four values are returned


def display_footer_content():
    st.markdown(""" 
        <div style="color: gray; text-align: center; font-size: 12px; font-family: Arial, sans-serif;">
            <b> ©️ 2024 Nanthitha Balamurugan | 
            <a href="https://www.linkedin.com/in/nanthithabalamurugan/" target="_blank" style="color: gray;">LinkedIn</a></b><br>
            <i><b> Made with ❤️ </i></b>
        </div>
    """, unsafe_allow_html=True)

def main():
    st.set_page_config(page_title="Video Summary & Reel Generator")

    if "is_authenticated" not in st.session_state:
        st.session_state.is_authenticated = False

    menu = ["Home", "Login", "Register", "Process Video", "User Profile"]
    if st.session_state.is_authenticated:
        menu.append("Logout")
        
    choice = st.sidebar.selectbox("Menu", menu)

    motivational_summary = None  # Initialize the variable
    transcript_path = None        # Initialize the variable
    reels_paths = []              # Initialize the variable
    important_segments = []       # Initialize the variable

    if choice == "Home":
        st.title("🎬 Welcome to Reelify 🎬")
        st.write("Your one-stop app for video reel creation!")
        st.image("C:\\Users\\nanth\\Desktop\\Milestone 2\\images.jpg", width=300)  # Update with actual image path

        st.subheader("⚡ Features")
        st.write("- Transcribe videos to text")
        st.write("- Analyze sentiment of your content")
        st.write("- Create motivational reels")
        st.write("- User-friendly interface")

        if st.button("Login"):
            st.session_state.menu_choice = "Login"

        if st.button("Register"):
            st.session_state.menu_choice = "Register"
    elif choice == "Login":
        st.title("🔐 Login")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user_data = verify_user(email, password)
            if user_data:
                st.session_state.is_authenticated = True
                st.session_state.user_data = user_data
                st.success("Logged in successfully!")
            else:
                st.error("Invalid credentials. Please try again.")

    elif choice == "Register":
        st.title("📝 Register")
        full_name = st.text_input("Full Name")
        username = st.text_input("Username (starting with @)")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        phone = st.text_input("Phone (starting with 9 or 6)")
        profession = st.text_input("Profession")
        dob = st.date_input("Date of Birth")
        short_desc = st.text_area("Short Description")
        profile_picture = st.file_uploader("Upload Profile Picture", type=["jpg", "png"])

        if st.button("Register"):
            if (is_valid_email(email) and is_valid_username(username) and
                is_strong_password(password) and is_valid_full_phone(phone)):
                profile_picture_path = f"uploads/profile_pictures/{username}.jpg"
                if profile_picture:
                    with open(profile_picture_path, "wb") as f:
                        f.write(profile_picture.getbuffer())
                if register_user(full_name, username, email, password, phone, profession, dob, short_desc, profile_picture_path, country_code="IN"):
                    st.success("Registration successful! You can now login.")
                else:
                    st.error("Registration failed. Please try again.")
            else:
                st.error("Please check your input fields for errors.")

    elif choice == "User Profile":
        st.title("👥 User Profile")
        if st.session_state.is_authenticated:
            user_data = st.session_state.user_data
            st.write(f"**Full Name:** {user_data[1]} 👤")
            st.write(f"**Username:** {user_data[9]}")
            st.write(f"**Email:** {user_data[2]} 📧")
            st.write(f"**Phone:** {user_data[4]} 📞")
            st.write(f"**Profession:** {user_data[5]} 💼")
            st.write(f"**Date of Birth:** {user_data[6]} 🎂")
            st.write(f"**Short Description:** {user_data[8]} 📝")
            if user_data[7]:
                st.image(user_data[7], width=100)
        else:
            st.warning("You need to log in to view your profile.")

    elif choice == "Process Video" and st.session_state.is_authenticated:
        st.title(" 🎥 Video Processing")

        video_file = st.file_uploader("Upload a video file", type=["mp4"])
        language = st.selectbox("Select Language", ["English", "Hindi", "Tamil", "Malayalam"])

        if video_file:
            st.video(video_file)  # Display the uploaded video
    
        if st.button("Process"):
            username = st.session_state.user_data[9]  # Access username from session state
            motivational_summary, transcript_path, reels_paths, important_segments = process_video_upload(video_file, username, language)
        
        if motivational_summary:
            st.subheader("🏆 Motivational Summary")
            st.write(motivational_summary)

        st.subheader("⏳ Important Segments")
        if important_segments:  # Check if important_segments is defined and not empty
            for segment in important_segments:
                start_time = segment['start']
                end_time = segment['end']
                text = segment['text']
                st.write(f"[{start_time:.2f}s - {end_time:.2f}s]: {text}")
        else:
            st.write("No important segments found.")

        st.subheader("📄 Transcript")
        if transcript_path:
            st.download_button("Download Transcript", transcript_path, key="transcript_download")

        st.subheader("🎞 Reels")
        for i, reel_path in enumerate(reels_paths):
            st.video(reel_path)  # Display each created reel
            st.download_button(
                label=f"Download Reel {i + 1}",
                data=reel_path,
                file_name=f"{username}_reel_{i + 1}.mp4",
                key=f"reel_download_{i}"  # Unique key for each download button
            )

    display_footer_content()
if __name__ == "__main__":
     main()