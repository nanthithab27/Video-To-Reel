import os
import random
import re
import string
import tempfile
import requests
import time
from dotenv import load_dotenv
import psycopg2
import streamlit as st
from moviepy.editor import VideoFileClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
import whisper
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import yt_dlp as youtube_dl

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
    
    try:
        with VideoFileClip(video_path) as video:
            for segment in segments:
                start_time = segment['start']
                end_time = segment['end']
                
                # Ensure segment is within the video duration and trim to 1 minute (60 seconds)
                if 0 <= start_time < video.duration and 0 < end_time <= video.duration and start_time < end_time:
                    # Extract the video segment
                    video_segment = video.subclip(start_time, end_time)
                    
                    # Trim the video segment to 1 minute if it's longer
                    if video_segment.duration > 60:
                        video_segment = video_segment.subclip(0, 60)
                    
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

def download_video_from_youtube(url, username):
    try:
        # Create a directory to save the video
        video_dir = f"uploads/videos/{username}"
        os.makedirs(video_dir, exist_ok=True)

        # Define options for yt-dlp (downloading video with audio)
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': os.path.join(video_dir, '%(title)s.%(ext)s'),
            'quiet': True,
        }

        # Download the video
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_file_path = ydl.prepare_filename(info_dict)
            
        return video_file_path
    except Exception as e:
        st.error(f"Error downloading video: {e}")
        return None
    
# Random fact function
def show_random_fact(progress_percentage=None):
    facts = [
        "Did you know? The longest video ever uploaded to YouTube is over 35 days long!",
        "Fun Fact: The first video ever uploaded on YouTube was titled 'Me at the zoo.'",
        "Here’s something cool: 500 hours of video are uploaded to YouTube every minute!",
        "Interesting fact: Over 80% of YouTube views come from outside the US.",
        "Did you know? The first-ever YouTube ad was launched in 2005 by the burger chain, Burger King!",
        "A fun fact: The world’s most viewed video on YouTube is 'Baby Shark' with over 12 billion views!",
        "Interesting: The average length of a YouTube video is just under 15 minutes.",
        "Cool fact: YouTube’s logo was created by co-founder Jawed Karim.",
        "Fun Fact: YouTube was created by former PayPal employees in 2005."
    ]
    fact = random.choice(facts)
    if progress_percentage:
        st.text(f"🔍 Progress: {progress_percentage}% - {fact}")
    else:
        st.text(f"💡 Random Fact: {fact}")

def process_video_upload(video_file=None, youtube_url=None, username=None, language="English"):
    # Initialize the progress bar
    progress = st.progress(0)
    
    # Create an empty placeholder for random facts
    random_fact_placeholder = st.empty()

    # List of facts
    facts = [
        "Did you know? The longest video ever uploaded to YouTube is over 35 days long!",
        "Fun Fact: The first video ever uploaded on YouTube was titled 'Me at the zoo.'",
        "Here’s something cool: 500 hours of video are uploaded to YouTube every minute!",
        "Interesting fact: Over 80% of YouTube views come from outside the US.",
        "Did you know? The first-ever YouTube ad was launched in 2005 by the burger chain, Burger King!",
        "A fun fact: The world’s most viewed video on YouTube is 'Baby Shark' with over 12 billion views!",
        "Interesting: The average length of a YouTube video is just under 15 minutes.",
        "Cool fact: YouTube’s logo was created by co-founder Jawed Karim.",
        "Fun Fact: YouTube was created by former PayPal employees in 2005."
    ]
    
    # Start processing the video
    with st.spinner("Processing video..."):
        video_path = None
        
        # Check if a YouTube URL is provided
        if youtube_url:
            st.text("Downloading video from YouTube...")
            video_path = download_video_from_youtube(youtube_url, username)
            if not video_path:
                return None, None, []  # Early return if video download fails
        elif video_file:
            # Save the uploaded video as a temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
                temp_video.write(video_file.getbuffer())
                video_path = temp_video.name

        if not video_path:
            return None, None, []

        # Step 2: Extract audio from the video
        audio_path = f"uploads/audio/{username}_{os.path.basename(video_path)}.wav"
        st.text("Extracting audio...")
        if not extract_audio_from_video(video_path, audio_path):
            return None, None, []  # Early return if audio extraction fails

        # Update progress (20% complete) and show a random fact
        progress.progress(20)
        random_fact_placeholder.text(f"🔍 Progress: 20% - {random.choice(facts)}")

        # Step 3: Transcribe the extracted audio
        st.text("Transcribing audio...")

        # Simulate the transcription process with periodic fact updates
        segments = None
        total_steps = 10  # Simulate 10 steps of progress during transcription
        for step in range(total_steps):
            time.sleep(2)  # Sleep for 2 seconds to simulate transcription time
            
            # Update progress
            progress.progress(int((step + 1) * 100 / total_steps))  # Simulate progress
            
            # Show a new random fact
            random_fact_placeholder.text(f"🔍 Progress: {int((step + 1) * 100 / total_steps)}% - {random.choice(facts)}")
        
        # After the loop, transcribe the audio
        segments = transcribe_audio_whisper(audio_path, language)
        
        # If transcription failed, return early
        if not segments:
            return None, None, []  # Early return if transcription fails
        
        # Clear random fact placeholder after transcription is complete
        random_fact_placeholder.empty()

        # Step 4: Perform sentiment analysis on the transcribed segments
        st.text("Analyzing sentiment...")
        important_segments = analyze_sentiment(segments)

        # Update progress (60% complete)
        progress.progress(60)

        # Step 5: Generate motivational content based on sentiment
        st.text("Creating motivational content...")
        motivational_contents = create_motivational_reel(important_segments)

        # Update progress (80% complete)
        progress.progress(80)

        # Step 6: Create reels from the processed segments
        reels_paths = []
        if len(important_segments) >= 3:
            # Divide segments into three groups based on sentiment or other criteria
            segment_count = len(important_segments) // 3
            for i in range(3):
                start_index = i * segment_count
                end_index = start_index + segment_count
                group_segments = important_segments[start_index:end_index]
                reel_path = create_reel(group_segments, video_path, username, i + 1)  # Create individual reels
                reels_paths.append(reel_path)

        # Step 7: Save the transcript of the important segments
        st.text("Saving transcript...")
        transcript_path = save_transcript(important_segments, os.path.basename(video_path), username)

        # Update progress to 100% complete
        progress.progress(100)

        # Clean up temporary files
        os.unlink(video_path)  # Delete temporary video file

        return motivational_contents, transcript_path, reels_paths, important_segments

# Function to handle logout logic
def logout():
    # Clear session state and set is_authenticated to False
    st.session_state.is_authenticated = False
    st.session_state.user_data = None  # Clear the user data
    st.success("You have successfully logged out.")
    st.session_state.redirect_to_login = True  # Flag to show the login page after logout

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

    menu = ["Home", "Login", "Register", "User Profile", "Process Video"]
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
        st.image("images/reel.jpg", width=300)  # Update with actual image path

        st.subheader("⚡ Features")
        st.write("- **Transcribe your videos**: Automatically convert spoken content into accurate text.")
        st.write("- **Sentiment Analysis**: Gain valuable insights into the mood and tone of your content.")
        st.write("- **Create stunning reels**: Craft attention-grabbing video reels with captions and effects.")
        st.write("- **Intuitive, user-friendly interface**: Easily navigate through the app and start creating in minutes.")
    elif choice == "Login":
        st.title("🔐 Login")
        st.write("Log in to access exclusive features and enjoy a fully personalized experience.")
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
        st.write("Create an account to get started and unlock all features.")
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
            profile_picture_path = user_data[7]
            st.image(profile_picture_path, width=400)
            # Increase font size for profile details using st.markdown with custom styles
        st.markdown(f"<h3 style='font-size: 24px; color: #ffffff; font-weight: bold;'>Full Name: {user_data[1]} 👤</h3>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='font-size: 20px; color: #ffffff; font-weight: bold;'>Username: {user_data[9]}</h4>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='font-size: 20px; color: #ffffff;'>Email: {user_data[2]} 📧</h4>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='font-size: 20px; color: #ffffff;'>Phone: {user_data[4]} 📞</h4>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='font-size: 20px; color: #ffffff;'>Profession: {user_data[5]} 💼</h4>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='font-size: 20px; color: #ffffff;'>Date of Birth: {user_data[6]} 🎂</h4>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='font-size: 20px; color: #ffffff;'>Short Description: {user_data[8]} 📝</h4>", unsafe_allow_html=True)

    elif choice == "Process Video" and st.session_state.is_authenticated:
        st.title(" 🎥 Video Processing")
        video_file = st.file_uploader("Upload a video file", type=["mp4"])
        youtube_url = st.text_input("Or provide a YouTube URL (optional)")
        language = st.selectbox("Select Language", ["English", "Hindi", "Tamil", "Malayalam"])

        if video_file:
            st.video(video_file)  # Display the uploaded video
        elif youtube_url:
            st.video(youtube_url)
            st.text("Video from YouTube will be processed shortly...")

        if st.button("Process"):
            username = st.session_state.user_data[9]  # Access username from session state
            motivational_summary, transcript_path, reels_paths, important_segments = process_video_upload(video_file, youtube_url, username, language)

            # Add progress bar
            progress = st.progress(0)
            for i in range(100):
                progress.progress(i + 1)

        summary_option = st.radio("Would you like to see a motivational summary?", ["Yes", "No"])
        if summary_option == "Yes" and motivational_summary:
            st.subheader("🏆 Motivational Summary")
            st.write(motivational_summary)

        # Display reels in separate tabs if available
        if reels_paths:
            st.subheader("🎞️ Reels")

    # Create tabs for each reel
            tab_labels = [f"Reel {i + 1}" for i in range(len(reels_paths))]  # Labels for the tabs
            tabs = st.tabs(tab_labels)

    # Loop through each tab and display the corresponding reel
            for i, tab in enumerate(tabs):
                with tab:
                    st.subheader(f"Reel {i + 1}")
                    st.video(reels_paths[i])  # Display the corresponding reel
                    st.download_button(
                label=f"Download Reel {i + 1}",
                data=reels_paths[i],
                file_name=f"{username}_reel_{i + 1}.mp4",
                key=f"reel_download_{i + 1}"
            )
        else:
            st.warning("No reels were created.")

    elif choice == "Logout":
        st.title("Logout")
        logout_confirmation = st.radio("Are you sure you want to logout?", ["No", "Yes"])
        if logout_confirmation == "Yes":
            logout()  # Call the logout function cmdto clear session state
            st.session_state.is_authenticated = False  # Explicitly set authentication to False
            st.session_state.user_data = None  # Clear the user data
        else:
            st.write("You're still logged in.")
    display_footer_content()

if __name__ == "__main__":
    main()