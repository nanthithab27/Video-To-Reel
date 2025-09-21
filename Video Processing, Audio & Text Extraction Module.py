import os
import subprocess
import tkinter as tk
from tkinter import filedialog
import whisper
import warnings
from textblob import TextBlob

# Set the output directory for audio and transcription files
OUTPUT_DIRECTORY = r"C:\Users\nanth\Desktop\Week 1-2"

def select_video_file():
    """Open a file dialog to select a video file."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    file_path = filedialog.askopenfilename(
        title="Select MP4 Video File",
        filetypes=[("MP4 files", "*.mp4")]  # Restrict to MP4 files
    )
    return file_path

def convert_video_to_audio(video_path, output_path):
    """Extract audio from the video file using FFmpeg."""
    try:
        ffmpeg_command = [
            'ffmpeg',
            '-i', video_path,
            '-vn',  # Disable video
            '-acodec', 'libmp3lame',
            '-q:a', '2',  # Variable bitrate quality
            output_path
        ]

        # Run the FFmpeg command
        subprocess.run(ffmpeg_command, check=True, stderr=subprocess.PIPE)
        print(f"Audio extracted successfully to: {output_path}")

        # Verify the audio file creation
        if not os.path.exists(output_path):
            print(f"Audio file does not exist after extraction: {output_path}")
            return False
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e}")
        print(f"FFmpeg error output: {e.stderr.decode()}")
        return False

def analyze_sentiment(text):
    """Analyze the sentiment of the provided text and determine the tone."""
    analysis = TextBlob(text)
    polarity = analysis.sentiment.polarity  # Polarity score
    tone = "Neutral"
    
    if polarity > 0.1:
        tone = "Positive"
    elif polarity < -0.1:
        tone = "Negative"
    
    return polarity, tone  # Return polarity score and tone

def transcribe_audio_with_timestamps(audio_path):
    """Transcribe the audio file using OpenAI Whisper with timestamps and sentiment."""
    warnings.filterwarnings("ignore", category=UserWarning)  # Suppress specific warnings

    try:
        print("Loading Whisper model...")
        model = whisper.load_model("base")  # Load Whisper model
        print("Whisper model loaded successfully.")

        if not os.path.exists(audio_path):
            print(f"Audio file does not exist: {audio_path}")
            return ""

        print("Transcribing audio...")
        result = model.transcribe(audio_path, language="en")

        segments = result.get('segments', [])
        if not segments:
            print("No segments found in transcription.")
            return ""

        transcription_with_timestamps = []
        for segment in segments:
            start_time = segment['start']
            end_time = segment['end']
            text = segment['text'].strip()
            sentiment_score, tone = analyze_sentiment(text)
            formatted_text = f"[{start_time:.2f} - {end_time:.2f}] {text} (Sentiment: {sentiment_score:.2f}, Tone: {tone})"
            transcription_with_timestamps.append(formatted_text)

        print(f"Transcribed {len(segments)} segments.")
        return "\n".join(transcription_with_timestamps)

    except Exception as e:
        print(f"Error during transcription: {e}")
        return ""

def save_transcription(transcription, output_file):
    """Save the transcription to a text file."""
    if not transcription:  # Check if transcription is empty
        print("No transcription to save.")
        return

    try:
        with open(output_file, "w") as f:
            f.write(transcription)
        print(f"Transcription saved to: {output_file}")

    except Exception as e:
        print(f"Error saving transcription: {e}")

def main():
    print("Video to Audio Converter and Transcriber with Timestamps, Sentiment, and Tone")
    print("--------------------------------------------------------")

    # Select the video file
    video_path = select_video_file()
    if not video_path:
        print("No file selected. Exiting.")
        return

    # Create output path for audio
    audio_output_path = os.path.join(OUTPUT_DIRECTORY, os.path.splitext(os.path.basename(video_path))[0] + '.mp3')

    # Convert video to audio
    if not convert_video_to_audio(video_path, audio_output_path):
        print("Audio extraction failed. Exiting.")
        return

    # Transcribe audio to text with timestamps, sentiment, and tone
    transcription = transcribe_audio_with_timestamps(audio_output_path)

    # Save the transcription to a file
    transcription_output_path = os.path.join(OUTPUT_DIRECTORY, f"{os.path.splitext(os.path.basename(video_path))[0]}_transcription_with_timestamps.txt")
    save_transcription(transcription, transcription_output_path)

if __name__ == "__main__":
    main()
