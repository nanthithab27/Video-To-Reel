import os
import re
import string
import streamlit as st
import psycopg2
from dotenv import load_dotenv
from datetime import datetime
import tempfile
from moviepy.editor import VideoFileClip
import whisper
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Download VADER lexicon if not already downloaded
nltk.download('vader_lexicon', quiet=True)

# Load environment variables
load_dotenv("users.env")
load_dotenv("apikey.env")

# Set API keys
infosys_api_key = os.getenv('INFOSYS_API_KEY')

# Ensure uploads directory exists
os.makedirs('uploads', exist_ok=True)
os.makedirs('uploads/audio', exist_ok=True)
os.makedirs('uploads/transcripts', exist_ok=True)
os.makedirs('uploads/profile_pictures', exist_ok=True)

# Initialize Whisper model
whisper_model = whisper.load_model("base")

# Initialize Sentiment Analyzer
sentiment_analyzer = SentimentIntensityAnalyzer()

# Database connection function
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

# Video processing functions
def extract_audio_from_video(video_path, output_audio_path):
    """Extract audio from video file"""
    try:
        video = VideoFileClip(video_path)
        audio = video.audio
        audio.write_audiofile(output_audio_path)
        video.close()
        audio.close()
        return True
    except Exception as e:
        st.error(f"Error extracting audio: {e}")
        return False

def transcribe_audio_whisper(audio_path, language="English"):
    """Transcribe audio using Whisper"""
    try:
        language_codes = {
            "English": "en",
            "Hindi": "hi",
            "Tamil": "ta",
            "Malayalam": "ml"
        }
        
        result = whisper_model.transcribe(
            audio_path,
            language=language_codes.get(language, "en")
        )
        return result["segments"]
    except Exception as e:
        st.error(f"Error during transcription: {e}")
        return None

def save_transcript(transcript, filename, username):
    """Save transcript to file"""
    transcript_path = f"uploads/transcripts/{username}_{filename}.txt"
    try:
        with open(transcript_path, "w", encoding="utf-8") as f:
            for segment in transcript:
                f.write(f"[{segment['start']:.2f}s - {segment['end']:.2f}s]: {segment['text']}\n")
        return transcript_path
    except Exception as e:
        st.error(f"Error saving transcript: {e}")
        return None

def register_user(full_name, username, email, password, phone, profession, dob, short_desc, profile_picture_path, country_code):
    """Register a new user in the database"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
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
            cursor.close()
            conn.close()

# User verification function
def verify_user(email, password):
    """Verify user credentials for login"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
            user = cursor.fetchone()
            return user
        except Exception as e:
            st.error(f"Error during user verification: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

def analyze_sentiment(segments):
    """Analyze sentiment and return important segments"""
    important_segments = []
    for segment in segments:
        sentiment_score = sentiment_analyzer.polarity_scores(segment['text'])
        # Consider a positive sentiment as important; you can adjust the threshold as needed
        if sentiment_score['compound'] > 0.05:  # Positive sentiment
            important_segments.append(segment)
    return important_segments

def process_video_upload(video_file, username, language):
    """Process uploaded video file"""
    with st.spinner("Processing video..."):
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
            temp_video.write(video_file.getbuffer())
            video_path = temp_video.name

        audio_path = f"uploads/audio/{username}_{video_file.name}.wav"
        
        # Extract audio
        st.text("Extracting audio...")
        if not extract_audio_from_video(video_path, audio_path):
            return None, None

        # Transcribe audio
        st.text("Transcribing audio...")
        segments = transcribe_audio_whisper(audio_path, language)
        if not segments:
            return None, None

        # Analyze sentiment and filter important segments
        important_segments = analyze_sentiment(segments)

        # Save transcript of important segments
        transcript_path = save_transcript(important_segments, video_file.name, username)

        # Cleanup temporary files
        os.unlink(video_path)
        
        return important_segments, transcript_path

# Function to display footer content
def display_footer_content():
    st.markdown(""" 
        <div style="color: gray; text-align: center; font-size: 12px; font-family: Arial, sans-serif;">
            <b> ©️ 2024 Nanthitha Balamurugan | 
            <a href="https://www.linkedin.com/in/nanthithabalamurugan/" target="_blank" style="color: gray;">LinkedIn</a></b><br>
            <i><b> Made with ❤️ </i></b>
        </div>
    """, unsafe_allow_html=True)

# Main application function
def main():
    st.title("🎬 Reelify 🎥")
    st.write("Your one-stop app for video reel creation!")

    # Initialize session state if not present
    if 'page' not in st.session_state:
        st.session_state.page = 'login'
        st.session_state.logged_in = False
        st.session_state.user_data = {}

    current_year = datetime.now().year
    min_dob = datetime(year=1900, month=1, day=1)
    max_dob = datetime(year=current_year, month=12, day=31)

    # Country codes for selection
    country_codes = {
        '🇮🇳 +91': '91',
        '🇺🇸 +1': '1',
        '🇬🇧 +44': '44',
    }

    # Login page
    if st.session_state.page == 'login':
        st.subheader("Login")
        email = st.text_input("Email Address", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login", key="login_button"):
            user = verify_user(email, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_data = {
                    "full_name": user[1],
                    "username": user[2],
                    "email": email,
                    "phone": user[4],
                    "profession": user[5],
                    "dob": user[6],
                    "short_desc": user[8],
                    "profile_picture": user[7],
                }
                st.session_state.page = 'profile'
                st.success("Login successful!")
            else:
                st.error("Invalid credentials. Please try again.")

    # Registration page
    elif st.session_state.page == 'register':
        st.subheader("Register")
        full_name = st.text_input("Full Name", key="reg_full_name")
        username = st.text_input("Username (starts with @)", key="reg_username")
        dob = st.date_input("Date of Birth", min_value=min_dob, max_value=max_dob, key="reg_dob")
        email = st.text_input("Email Address", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_password")
        profession = st.text_input("Profession", key="reg_profession")
        short_desc = st.text_area("Short Description", key="reg_short_desc")
        phone = st.text_input("Phone Number", key="reg_phone")
        country_code = st.selectbox("Select Country Code", options=list(country_codes.keys()), index=0)
        profile_picture = st.file_uploader("Upload Profile Picture", type=["jpg", "png"], key="reg_profile_pic")

        if st.button("Register", key="register_action_button"):
            country_code_value = country_codes[country_code]
            if (is_valid_email(email) and is_valid_username(username) and 
                is_strong_password(password) and 
                is_valid_full_phone(phone) and 
                profile_picture is not None):
                
                # Save profile picture to uploads
                profile_picture_path = f"uploads/profile_pictures/{username}_profile.jpg"
                with open(profile_picture_path, "wb") as f:
                    f.write(profile_picture.getbuffer())

                if register_user(full_name, username, email, password, phone, profession, dob, short_desc, profile_picture_path, country_code_value):
                    st.success("Registration successful!")
                    st.session_state.page = 'login'
                else:
                    st.error("Registration failed. Please try again.")
            else:
                st.error("Please ensure all fields are filled out correctly.")

    # Profile page
    elif st.session_state.page == 'profile':
        st.subheader("Profile")
        st.image(st.session_state.user_data['profile_picture'], width=150)
        st.write(f"**Full Name:** {st.session_state.user_data['full_name']}")
        st.write(f"**Username:** {st.session_state.user_data['username']}")
        st.write(f"**Email:** {st.session_state.user_data['email']}")
        st.write(f"**Phone:** {st.session_state.user_data['phone']}")
        st.write(f"**Profession:** {st.session_state.user_data['profession']}")
        st.write(f"**Date of Birth:** {st.session_state.user_data['dob']}")
        st.write(f"**Short Description:** {st.session_state.user_data['short_desc']}")

        st.subheader("Upload Video")
        video_file = st.file_uploader("Upload MP4 Video", type=["mp4"], key="upload_video")
        
        # Language selection for transcription
        language = st.selectbox("Select Language for Transcription", ["English", "Hindi", "Tamil", "Malayalam"])

        if st.button("Process Video", key="process_video_button"):
            if video_file is not None:
                important_segments, transcript_path = process_video_upload(video_file, st.session_state.user_data['username'], language)
                if important_segments:
                    st.success("Video processed successfully!")
                    
                    # Display the uploaded video
                    st.video(video_file)

                    st.write("Important Transcription Segments:")
                    for segment in important_segments:
                        st.write(f"[{segment['start']:.2f}s - {segment['end']:.2f}s]: {segment['text'].strip()}")

                    st.write(f"Download Transcript: [here]({transcript_path})")
            else:
                st.error("Please upload a video.")

    # Display footer
    display_footer_content()

# Run the main application
if __name__ == "__main__":
    main()
