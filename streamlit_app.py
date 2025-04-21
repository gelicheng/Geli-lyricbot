import streamlit as st
from openai import OpenAI
import time
import re
import requests

placeholderstr = "Please input your command"
user_name = "Geli"
user_image = "https://www.w3schools.com/howto/img_avatar.png"

# Get access token
CLIENT_ID = "b9e0979d54c449d4a1b7f23a1be1d329"
CLIENT_SECRET = "03559d2dc6b643e8af412d5930ee4ec2"

auth_url = "https://accounts.spotify.com/api/token"
auth_response = requests.post(
    auth_url,
    data={"grant_type": "client_credentials"},
    auth=(CLIENT_ID, CLIENT_SECRET)
)

# Extract the access token
access_token = auth_response.json().get("access_token")
if not access_token:
    raise Exception("Failed to get Spotify access token")

def stream_data(stream_str):
    for word in stream_str.split(" "):
        yield word + " "
        time.sleep(0.15)

def main():
    st.set_page_config(
        page_title='K-Assistant - The Residemy Agent',
        layout='wide',
        initial_sidebar_state='auto',
        menu_items={
            'Get Help': 'https://streamlit.io/',
            'Report a bug': 'https://github.com',
            'About': 'About your application: **Hello world**'
            },
        page_icon="img/favicon.ico"
    )

    # Show title and description.
    st.title(f"💬 {user_name}'s Lyricbot")
    st.markdown("Welcome! 👋 This chatbot can get you lyrics from a Spotify playlist. Just paste a playlist link and I'll do the rest! 🎧")


    with st.sidebar:
        selected_lang = st.selectbox("Language", ["English", "繁體中文"], index=1)
        if 'lang_setting' in st.session_state:
            lang_setting = st.session_state['lang_setting']
        else:
            lang_setting = selected_lang
            st.session_state['lang_setting'] = lang_setting

        st_c_1 = st.container(border=True)
        with st_c_1:
            st.image("https://www.w3schools.com/howto/img_avatar.png")

    st_c_chat = st.container(border=True)

    if "messages" not in st.session_state:
        st.session_state.messages = []
    else:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                if user_image:
                    st_c_chat.chat_message(msg["role"],avatar=user_image).markdown((msg["content"]))
                else:
                    st_c_chat.chat_message(msg["role"]).markdown((msg["content"]))
            elif msg["role"] == "assistant":
                st_c_chat.chat_message(msg["role"]).markdown((msg["content"]))
            else:
                try:
                    image_tmp = msg.get("image")
                    if image_tmp:
                        st_c_chat.chat_message(msg["role"],avatar=image_tmp).markdown((msg["content"]))
                except:
                    st_c_chat.chat_message(msg["role"]).markdown((msg["content"]))

    def generate_response(prompt):
        # Check if prompt is a Spotify playlist
        if "open.spotify.com/playlist/" in prompt:
            playlist_id = extract_playlist_id(prompt)

            try:
                tracks = get_playlist_tracks(access_token, playlist_id)
                track_record = []

                for track in tracks:
                    artist = track["track"]["artists"][0]["name"]
                    title = track["track"]["name"]
                    lyrics = get_lyrics(artist, title)

                    if lyrics:
                        track_record.append((artist, title, lyrics))

                if not track_record:
                    return "No lyrics found for any songs in this playlist."

                # Just return the first 3 songs for brevity
                response = "Here's a sample of the lyrics I found:\n\n"
                for artist, title, lyrics in track_record[:3]:
                    response += f"**{title}** by *{artist}*\n\n{lyrics[:300]}...\n\n"

                response += f"Total with lyrics: {len(track_record)} out of {len(tracks)}"
                return response

            except Exception as e:
                return f"Oops! Failed to process playlist. Error: {e}"

        else:
            return "Please send me a Spotify playlist link to fetch lyrics"

    def extract_playlist_id(playlist_url):
        return playlist_url.split("/")[-1].split("?")[0]

    def get_lyrics(artist, title):
        formatted_artist = artist.strip().lower().replace(" ", "%20")
        formatted_title = title.strip().lower().replace(" ", "%20")

        url = f"https://api.lyrics.ovh/v1/{formatted_artist}/{formatted_title}"
        response = requests.get(url)

        if response.status_code == 200:
            return response.json().get("lyrics")
        else:
            return None

    def get_playlist_tracks(access_token, playlist_id):
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        tracks = []

        while url:
            response = requests.get(url, headers=headers)
            data = response.json()
            tracks.extend(data["items"])
            url = data.get("next")

        return tracks

    # Chat function section (timing included inside function)
    def chat(prompt: str):
        st_c_chat.chat_message("user",avatar=user_image).write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        response = generate_response(prompt)
        # response = f"You type: {prompt}"
        st.session_state.messages.append({"role": "assistant", "content": response})
        st_c_chat.chat_message("assistant").write_stream(stream_data(response))

    
    if prompt := st.chat_input(placeholder=placeholderstr, key="chat_bot"):
        chat(prompt)

if __name__ == "__main__":
    main()
