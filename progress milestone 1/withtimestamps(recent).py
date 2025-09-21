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

# Load environment variables
load_dotenv("users.env")
load_dotenv("apikey.env")

# Set API keys
infosys_api_key = os.getenv('INFOSYS_API_KEY')

# Ensure uploads directory exists
os.makedirs('uploads', exist_ok=True)
os.makedirs('uploads/audio', exist_ok=True)
os.makedirs('uploads/transcripts', exist_ok=True)

# Initialize Whisper model
whisper_model = whisper.load_model("base")

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
            "Tamil": "ta",
            "Malayalam": "ml",
            "Hindi": "hi"
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

        # Save transcript
        transcript_path = save_transcript(segments, video_file.name, username)

        # Cleanup temporary files
        os.unlink(video_path)
        
        return segments, transcript_path

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
                st.error("Invalid email or password.")

        if st.button("Register", key="register_button"):
            st.session_state.page = 'register'

    # Registration page
    elif st.session_state.page == 'register':
        st.subheader("Register")

        full_name = st.text_input("Full Name", key="reg_full_name")
        username = st.text_input("Username (start with @)", key="reg_username", placeholder="@your_username")
        dob = st.date_input("Date of Birth", min_value=min_dob, max_value=max_dob, key="reg_dob")
        email = st.text_input("Email Address", key="reg_email")
        profession = st.text_input("Profession", key="reg_profession")
        country_code = st.selectbox("Country Code", country_codes.keys(), key="reg_country_code")
        phone = st.text_input("Phone Number (10 digits)", key="reg_phone")
        password = st.text_input("Password", type="password", key="reg_password")
        short_desc = st.text_area("Short Description", max_chars=200, key="reg_short_desc", placeholder="Tell us about yourself!")
        profile_picture = st.file_uploader("Upload Profile Picture", type=["png", "jpg", "jpeg"])

        # Ensure that the button key is unique
        if st.button("Register", key="register_button"):
            # Validate input fields
            if not is_valid_full_phone(phone):
                st.error("Invalid phone number. It should start with 9, 6, or 2 and have 10 digits.")
            elif not is_valid_email(email):
                st.error("Invalid email address.")
            elif not is_valid_username(username):
                st.error("Invalid username. It should start with '@'.")
            elif not is_strong_password(password):
                st.error("Password must be at least 8 characters long, contain upper and lower case letters, numbers, and special characters.")
            elif not profile_picture:
                st.error("Please upload a profile picture.")
            else:
                # Save profile picture
                profile_picture_path = f"uploads/profile_pictures/{username}.jpg"
                with open(profile_picture_path, "wb") as f:
                    f.write(profile_picture.getbuffer())

                # Register the user
                if register_user(full_name, username, email, password, phone, profession, dob, short_desc, profile_picture_path, country_codes[country_code]):
                    st.success("Registration successful! You can now log in.")
                    st.session_state.page = 'login'
                 # Add a button to go back to login
        if st.button("Back to Login", key="back_to_login_button"):
            st.session_state.page = 'login'

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
        video_file = st.file_uploader("Upload MP4 Video", type=["mp4"])
        language = st.selectbox("Select Language for Transcription", ["English", "Tamil", "Malayalam", "Hindi"])

        if st.button("Process Video", key="process_video_button"):
            if video_file is not None:
                segments, transcript_path = process_video_upload(video_file, st.session_state.user_data['username'], language)
                if segments:
                    st.success("Video processed successfully!")
                    
                    # Display the uploaded video
                    st.video(video_file)

                    st.write("Transcription Segments:")
                    for segment in segments:
                        st.write(f"[{segment['start']:.2f}s - {segment['end']:.2f}s]: {segment['text'].strip()}")

                    st.write(f"Download Transcript: [here]({transcript_path})")
            else:
                st.error("Please upload a video.")

    # Display footer
    display_footer_content()

# Run the application
if __name__ == "__main__":
    main() 