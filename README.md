# 🍳🎤 Video to Reel Generator
## -Nanthitha Balamurugan

## Overview
This project is designed to transform lengthy video files into engaging and shareable reels, making it ideal for talks, interviews, and recipe videos. 🎥 The process begins with a user-friendly interface built using Streamlit, allowing users to seamlessly upload MP4 files. 📤 The videos are then converted to MP3 format using FFmpeg for audio extraction. 🎧 The audio files undergo further processing with OpenAI Whisper, which generates accurate transcriptions 📝 along with detailed timestamps ⏱️. Sentiment analysis is applied to identify key moments of interest within the content. 📊 The video is then segmented into meaningful portions, with three reels generated from the most engaging highlights. 🎬 During the processing stage, interesting facts relevant to the video content are seamlessly incorporated to enhance the appeal and engagement of the reels. 💡 Each reel is carefully curated to emphasize different aspects of the video, ensuring that the final output is both captivating and informative, ready for sharing on platforms like Instagram and YouTube. 📲

🗂️ Table of Contents
1. Requirements
2.Setup
3. Usage
4. Commands
5. Outputs
6. Instructions
7. License
   
Requirements
Before you start, ensure you have the following installed:

1. Python 3.x
2. FFmpeg
3. Streamlit
4. OpenAI Whisper

# Setup
Clone the repository to your local system:
```markdown
git clone https://github.com/Springboard-Internship-2024/Video-to-Reels_oct_2024.git
cd <repository_directory>
```

Install required Python packages:
```markdown
bash
pip install streamlit openai-whisper
```

Ensure FFmpeg is installed:
For Windows, download it from FFmpeg official website.
For macOS, install it using Homebrew:

```markdown
```python
bash
brew install ffmpeg
For Linux, install via your package manager (e.g., sudo apt-get install ffmpeg).
```

Usage
Navigate to the project directory:
```markdown
```python
bash
cd C:\Users\nanth\Desktop\Milestone 1
```
Run the Streamlit application:
```markdown
bash
streamlit run video_to_reel.py
```
This will start a local server and open the app in your web browser.

The application will guide you through the following steps:

Login Page: 
Enter your credentials to access the application.
Registration Page:
If you are a new user, register to create an account.
Profile Page: 
View your profile details and upload MP4 files.
Upload your MP4 video file.

The application will convert the MP4 video to MP3 format using FFmpeg.

The MP3 file will then be processed using OpenAI Whisper to generate transcriptions with timestamps and perform sentiment analysis.

View the results in the Streamlit app.

Commands
Here are some essential commands used in the project:

Convert MP4 to MP3:
```markdown
bash
ffmpeg -i input_video.mp4 -q:a 0 -map a output_audio.mp3
```

Run Streamlit app:
```markdown
bash
streamlit run video_to_reel.py
```

In order to push,commit code in git:
Step 1: Clone the Repository
Open your terminal or command prompt and run the following command to clone the repository to your local machine:
```markdown
bash
Copy code
git clone https://github.com/Video-to-Reels_oct_2024.git
```

Step 2: Navigate to the Directory
Change into the directory of the cloned repository:
```markdown
bash
cd Video-to-Reels_oct_2024
```
Step 3: Create a New Branch
Create a new branch (replace your-branch-name with your desired branch name):
```markdown
bash
Copy code
git checkout -b your-branch-name
```

Step 4: Add Your Files
Now, add your files or make changes to the existing files in the repository.

Step 5: Stage Your Changes
After adding or modifying files, stage them for commit:
```markdown
bash
git add .
```

This stages all changes. If you want to stage specific files, replace . with the file names.

Step 6: Commit Your Changes
Commit your staged changes with a message:
```markdown
bash
git commit -m "Milestone completed"
```
Step 7: Push Your Changes to the New Branch
Push the new branch with your committed changes to the remote repository:

```markdown
bash
git push origin your-branch-name
```

Step 8: (Optional) Create a Pull Request
After pushing, you can go to the GitHub repository page to create a pull request for your new branch, merging it into the main branch if desired.

## Summary of Commands:
```markdown
bash
git clone https://github.com/Video-to-Reels_oct_2024.git
cd Video-to-Reels_oct_2024
git checkout -b your-branch-name
# Make changes or add files
git add .
git commit -m "Your commit message here"
git push origin your-branch-name
```
This process will allow you to work on your code independently and push your changes to a new branch without affecting the main branch.

# Instructions
🌟 Application Workflow

Login Page:
🔐 Enter your credentials to access the app and proceed with video processing.

Registration Page:
📝 If you're a new user, register to create an account and enjoy personalized services.

Profile Page:
👤 View and manage your account details, along with any uploaded files.

Upload MP4 Video:
📤 Upload your MP4 video to the app. The app will then:

🔄 Convert the MP4 file to MP3 using FFmpeg.
🎧 Process the MP3 file using OpenAI Whisper to generate:
📝 Transcriptions with timestamps for easy reference.
📊 Sentiment analysis for each segment, highlighting key moments.
Reel Creation:
🎬 Extract key highlights and create 3 engaging reels from the video content.

View Outputs:
📑 Summary and the generated reels are displayed on the results page for easy review and sharing.

⚠️ Disclaimer:
⚠️ Please upload only talks, interviews, or recipe videos. Other video formats may not be supported or suitable for the reel generation process.
# Outputs
Below are examples of the application's user interface:

## Home Page:
<img width="959" alt="home page" src="https://github.com/user-attachments/assets/126dce69-d1dd-4b95-b1fc-1ca7ccc86f1d">

## Login Page:
<img width="959" alt="login page" src="https://github.com/user-attachments/assets/a33e0307-0afd-4ce6-8e5e-c8fd2b84e891">

## Registration Page:
<img width="959" alt="register page" src="https://github.com/user-attachments/assets/0883a956-71d6-439c-b650-4df377123d00">

## Profile Page:
<img width="959" alt="user profile page" src="https://github.com/user-attachments/assets/3dac8acf-00d4-412f-a0ce-22e33cb11b0f">

## Upload MP4 Details:
<img width="959" alt="process page" src="https://github.com/user-attachments/assets/b92da752-6619-4b00-ac4c-f5ce9fc1e029">

## Youtube url feature:
<img width="955" alt="url and facts" src="https://github.com/user-attachments/assets/a39aa609-d9fd-4e9a-bd66-f3e55c33348e">

## Summary and Reel Generation:
<img width="956" alt="summary+reel1" src="https://github.com/user-attachments/assets/cb0b831c-7ef5-4424-bc1e-aca34a69ab7f">

## Backend Process:
<img width="956" alt="backend" src="https://github.com/user-attachments/assets/0fa96064-5a20-4f3b-9778-495f513a71bc">


