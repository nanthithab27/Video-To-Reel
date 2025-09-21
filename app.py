import os
import re
import string
import streamlit as st
import psycopg2
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from user.env file
load_dotenv("C:\\Users\\nanth\\Desktop\\Week 1-2\\user.env") 

# Create uploads directory if it doesn't exist
if not os.path.exists('uploads'):
    os.makedirs('uploads')

# Database connection function
def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),  # Database name
            user=os.getenv('DB_USER'),    # PostgreSQL username
            password=os.getenv('DB_PASSWORD'),  # PostgreSQL password
            host=os.getenv('DB_HOST'),     # PostgreSQL host
            port=os.getenv('DB_PORT')      # PostgreSQL port
        )
        return conn
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

# Function to validate email address
def is_valid_email(email):
    return re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email) is not None

# Function to validate password strength
def is_strong_password(password):
    return (len(password) >= 8 and
            any(c.isdigit() for c in password) and
            any(c.islower() for c in password) and
            any(c.isupper() for c in password) and
            any(c in string.punctuation for c in password))

# Function to delete all users before registration (optional)
def delete_all_users():
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users")  # Remove this line if you want to keep existing users
            conn.commit()
            cursor.close()
        except Exception as e:
            st.error(f"Error deleting users: {e}")
        finally:
            conn.close()

# Function to register user
def register_user(full_name, email, password, phone, profession, dob, short_desc, profile_picture_path):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (full_name, email, password, phone, profession, dob, short_desc, profile_picture)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (full_name, email, password, phone, profession, dob.strftime('%Y-%m-%d'), short_desc, profile_picture_path)
            )
            conn.commit()  # Commit changes
            cursor.close()
            return True  # Indicate success
        except Exception as e:
            st.error(f"Error during registration: {e}")
            return False
        finally:
            conn.close()

# Function to verify user credentials
def verify_user(email, password):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
            user = cursor.fetchone()
            cursor.close()
            return user  # Return user data if credentials are valid
        except Exception as e:
            st.error(f"Error during user verification: {e}")  # Log error to console
            return None
        finally:
            conn.close()

# Function to display footer content
def display_footer_content():
    st.markdown(""" 
        <div style="color: white; text-align: left; font-size: 12px; font-family: Arial, sans-serif;">
           <b> © 2024 Nanthitha Balamurugan
            <a href="https://www.linkedin.com/in/nanthithabalamurugan/" target="_blank" style="color: white;">LinkedIn</b></a><br>
           <i><b> Made with ❤️ </i></b>
        </div>
    """, unsafe_allow_html=True)

# Main application function
def main():
    st.title(" 🎬 Reelify 🎥")
    st.write("Your one-stop app for video reel creation!")

    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state.page = 'login'
        st.session_state.logged_in = False
        st.session_state.email = ""
        st.session_state.phone = ""
        st.session_state.profile_picture_path = None
        st.session_state.profession = ""
        st.session_state.full_name = ""
        st.session_state.dob = ""
        st.session_state.short_desc = ""

    # Get the current year for date input validation
    current_year = datetime.now().year
    min_dob = datetime(year=1900, month=1, day=1)
    max_dob = datetime(year=current_year, month=12, day=31)

    # Login Page
    if st.session_state.page == 'login':
        st.subheader("Login")
        email = st.text_input("Email Address", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login"):
            user = verify_user(email, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.email = email
                st.session_state.phone = user[4]  # Assuming phone is the 5th column in the user table
                st.session_state.profession = user[5]  # Assuming profession is the 6th column in the user table
                st.session_state.full_name = user[1]  # Assuming full_name is the 2nd column in the user table
                st.session_state.dob = user[6]  # Assuming dob is the 7th column in the user table
                st.session_state.short_desc = user[8]  # Assuming short_desc is the 9th column
                st.session_state.profile_picture_path = user[7]  # Assuming profile_picture is the 8th column
                st.session_state.page = 'profile'  # Go to profile page
                st.success("Login successful!")
            else:
                st.error("Invalid email or password. Please try again.")

        if st.button("Register"):
            st.session_state.page = 'register'

    # Registration Page
    elif st.session_state.page == 'register':
        st.subheader("Register")
        
        full_name = st.text_input("Full Name", key="reg_full_name")
        dob = st.date_input("Date of Birth", min_value=min_dob, max_value=max_dob, key="reg_dob")
        new_email = st.text_input("Email Address", key="reg_email")
        new_password = st.text_input(
            "Password", 
            type="password", 
            key="reg_password", 
            help="At least 8 characters long, at least one uppercase letter, at least one lowercase letter, at least one number, and at least one special character."
        )
        confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm_password")
        new_phone = st.text_input("Phone Number", max_chars=10, key="reg_phone")
        profession = st.text_input("Profession", key="reg_profession")
        short_desc = st.text_area("Short Description", max_chars=200, key="reg_short_desc")  # Short description input

        # Profile Picture Upload
        profile_picture = st.file_uploader("Upload Profile Picture", type=["jpg", "jpeg", "png"], key="reg_profile_picture")

        if st.button("Register"):
            delete_all_users()  # Delete all users before new registration (optional)
            if not is_valid_email(new_email):
                st.error("Invalid email format.")
            elif not is_strong_password(new_password):
                st.error("Password must meet the specified requirements.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                profile_picture_path = f"uploads/{profile_picture.name}" if profile_picture else None
                if profile_picture:
                    with open(profile_picture_path, "wb") as f:
                        f.write(profile_picture.getbuffer())

                registration_success = register_user(full_name, new_email, new_password, new_phone, profession, dob, short_desc, profile_picture_path)
                if registration_success:
                    st.success("Registration successful! Please log in.")
                    st.session_state.page = 'login'  # Redirect to login after successful registration

        # Back to Login Button
        if st.button("Back to Login"):
            st.session_state.page = 'login'

    # Profile Page
    elif st.session_state.page == 'profile':
        st.subheader("Profile Details")

        # Display the profile picture at the top
        if st.session_state.profile_picture_path:
            st.image(st.session_state.profile_picture_path, caption="Profile Picture", width=150)

        # Display profile details below the profile picture
        st.write(f"**Name:** {st.session_state.full_name}")
        st.write(f"**Email:** {st.session_state.email}")
        st.write(f"**Phone:** {st.session_state.phone}")
        st.write(f"**Profession:** {st.session_state.profession}")
        st.write(f"**Date of Birth:** {st.session_state.dob}")
        st.write(f"**Short Description:** {st.session_state.short_desc}")

        # Upload MP4 Video Button
        if st.button("Upload MP4 Video"):
            st.session_state.page = 'upload_video'

    # Upload Video Page
    elif st.session_state.page == 'upload_video':
        st.subheader("Upload MP4 Video")
        
        video_file = st.file_uploader("Choose an MP4 file", type=["mp4"], key="video_file")
        
        if video_file:
            # Save the uploaded video file
            video_path = os.path.join('uploads', video_file.name)
            with open(video_path, "wb") as f:
                f.write(video_file.getbuffer())
            st.success("Video uploaded successfully!")

        # Threshold scaler
        threshold = st.slider("Select threshold for reel generation", 0, 100, 50)

        # Generate Reel button
        if st.button("Generate Reel"):
            if video_file:
                # Placeholder for reel generation logic
                st.success(f"Reel generated with threshold set to {threshold} for video: {video_file.name}")
            else:
                st.error("Please upload a video file before generating a reel.")

        # Back to Profile Button
        if st.button("Back to Profile"):
            st.session_state.page = 'profile'

    display_footer_content()

# Run the application
if __name__ == "__main__":
    main()
