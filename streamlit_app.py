import streamlit as st
from openai import OpenAI
import time
import re
import requests
import numpy as np
import plotly.graph_objects as go
from sklearn.decomposition import PCA
from gensim.models import Word2Vec
from gensim.utils import simple_preprocess
from gensim.parsing.preprocessing import remove_stopwords

# === Basic settings ===
placeholderstr = "Please input your command"
user_name = "Geli"
user_image = "https://www.w3schools.com/howto/img_avatar.png"

# === Spotify Auth ===
CLIENT_ID = "b9e0979d54c449d4a1b7f23a1be1d329"
CLIENT_SECRET = "03559d2dc6b643e8af412d5930ee4ec2"

auth_url = "https://accounts.spotify.com/api/token"
auth_response = requests.post(
    auth_url,
    data={"grant_type": "client_credentials"},
    auth=(CLIENT_ID, CLIENT_SECRET)
)

access_token = auth_response.json().get("access_token")
if not access_token:
    raise Exception("Failed to get Spotify access token")


# === Helper Functions ===
def stream_data(stream_str):
    for word in stream_str.split(" "):
        yield word + " "
        time.sleep(0.15)

def extract_playlist_id(playlist_url):
    return playlist_url.split("/")[-1].split("?")[0]

def get_lyrics(artist, title):
    formatted_artist = artist.strip().lower().replace(" ", "%20")
    formatted_title = title.strip().lower().replace(" ", "%20")
    url = f"https://api.lyrics.ovh/v1/{formatted_artist}/{formatted_title}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("lyrics")
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

def generate_response(prompt):
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
            response = "Here's a sample of the lyrics I found:\n\n"
            for artist, title, lyrics in track_record[:3]:
                response += f"**{title}** by *{artist}*\n\n{lyrics[:300]}...\n\n"
            response += f"Total with lyrics: {len(track_record)} out of {len(tracks)}"
            return response
        except Exception as e:
            return f"Oops! Failed to process playlist. Error: {e}"
    else:
        return "Please send me a Spotify playlist link to fetch lyrics"

# === Sub-pages ===
def run_chatbot():
    st_c_chat = st.container()
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st_c_chat.chat_message("user", avatar=user_image).markdown(msg["content"])
        else:
            st_c_chat.chat_message("assistant").markdown(msg["content"])

    def chat(prompt: str):
        st_c_chat.chat_message("user", avatar=user_image).write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        response = generate_response(prompt)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st_c_chat.chat_message("assistant").write_stream(stream_data(response))

    if prompt := st.chat_input(placeholder=placeholderstr, key="chat_bot"):
        chat(prompt)
        
def run_q1_plot():
    st.title("Q1-1: 2D and 3D Visualization of Lyrics")
    lyrics_input = st.text_area("Enter 10 lines of lyrics separated by periods (.)", key="q1_input")
    if lyrics_input:
        lyrics_lines = lyrics_input.split(".")
        tokenized_lyrics = [simple_preprocess(line) for line in lyrics_lines if line.strip()]
        model = Word2Vec(tokenized_lyrics, vector_size=100, window=5, min_count=1, workers=4)
        word_vectors = np.array([model.wv[word] for word in model.wv.index_to_key])
        pca = PCA(n_components=3)
        reduced_vectors = pca.fit_transform(word_vectors)
        color_map = {i: c for i, c in enumerate(["red", "blue", "green", "purple", "orange", "cyan", "magenta", "yellow", "pink", "brown"])}
        word_colors = []
        for word in model.wv.index_to_key:
            for i, sentence in enumerate(tokenized_lyrics):
                if word in sentence:
                    word_colors.append(color_map[i % len(color_map)])
                    break
        scatter = go.Scatter3d(
            x=reduced_vectors[:, 0],
            y=reduced_vectors[:, 1],
            z=reduced_vectors[:, 2],
            mode='markers+text',
            text=model.wv.index_to_key,
            textposition='top center',
            marker=dict(color=word_colors, size=4)
        )
        line_traces = []
        for i, sentence in enumerate(tokenized_lyrics):
            line_vectors = [reduced_vectors[model.wv.key_to_index[word]] for word in sentence if word in model.wv]
            if line_vectors:
                line_trace = go.Scatter3d(
                    x=[vec[0] for vec in line_vectors],
                    y=[vec[1] for vec in line_vectors],
                    z=[vec[2] for vec in line_vectors],
                    mode='lines',
                    line=dict(color=color_map[i % len(color_map)], width=2),
                    showlegend=False
                )
                line_traces.append(line_trace)
        fig = go.Figure(data=[scatter] + line_traces)
        fig.update_layout(scene=dict(xaxis_title="X", yaxis_title="Y", zaxis_title="Z"), title="3D Visualization of Lyrics Word Embeddings", width=1000, height=800)
        st.plotly_chart(fig)

def run_q2_skipgram():
    st.title("Q2: Skip-gram Test")
    lyrics_input = st.text_area("Enter your lyrics line by line. Separate each line with a period (.)", key="q2_input")
    if lyrics_input:
        lyrics_lines = lyrics_input.split(".")
        tokenized_lyrics = [simple_preprocess(remove_stopwords(line)) for line in lyrics_lines if line.strip()]
        model = Word2Vec(tokenized_lyrics, vector_size=100, window=5, min_count=1, workers=4, sg=1)
        target_word = st.text_input("Enter a word you want to check:", key="q2_target")
        if target_word and target_word.lower().strip() in model.wv:
            st.write(f"Vector for '{target_word}':")
            st.write(model.wv[target_word.lower().strip()])
            st.write(f"Most similar words to '{target_word}':")
            similar_words = model.wv.most_similar(target_word.lower().strip())
            for word, similarity in similar_words:
                st.write(f"{word}: {similarity:.4f}")
        elif target_word:
            st.write(f"'{target_word}' not found in vocabulary.")

def run_q3_cbow():
    st.title("Q3: CBOW Test")
    lyrics_input = st.text_area("Enter your lyrics line by line. Separate each line with a period (.)", key="q3_input")
    if lyrics_input:
        lyrics_lines = lyrics_input.split(".")
        tokenized_lyrics = [simple_preprocess(remove_stopwords(line)) for line in lyrics_lines if line.strip()]
        model = Word2Vec(tokenized_lyrics, vector_size=100, window=5, min_count=1, workers=4, sg=0)
        target_word = st.text_input("Enter a word you want to check:", key="q3_target")
        if target_word and target_word.lower().strip() in model.wv:
            st.write(f"Vector for '{target_word}':")
            st.write(model.wv[target_word.lower().strip()])
            st.write(f"Most similar words to '{target_word}':")
            similar_words = model.wv.most_similar(target_word.lower().strip())
            for word, similarity in similar_words:
                st.write(f"{word}: {similarity:.4f}")
        elif target_word:
            st.write(f"'{target_word}' not found in vocabulary.")


# === Main App ===
def main():
    st.set_page_config(
        page_title="K-Assistant - The Residemy Agent",
        layout="wide",
        initial_sidebar_state="auto",
        menu_items={'Get Help': 'https://streamlit.io/', 'Report a bug': 'https://github.com', 'About': 'Hello world'},
        page_icon="img/favicon.ico"
    )

    st.title(f"💬 {user_name}'s Lyricbot")
    st.markdown("Welcome! 👋 This chatbot can get you lyrics from a Spotify playlist. Just paste a playlist link and I'll do the rest! 🎧")

    with st.sidebar:
        selected_lang = st.selectbox("Language", ["English", "繁體中文"], index=0)
        if 'lang_setting' not in st.session_state:
            st.session_state['lang_setting'] = selected_lang

        st.image(user_image)
        page = st.selectbox("Select a Page", ["Chatbot (Fetch Lyrics)", "Q1-1 2D & 3D Plot", "Q2 SKIP-GRAM Test", "Q3 CBOW Test"])

    if page == "Chatbot (Fetch Lyrics)":
        run_chatbot()
    elif page == "Q1-1 2D & 3D Plot":
        run_q1_plot()
    elif page == "Q2 SKIP-GRAM Test":
        run_q2_skipgram()
    elif page == "Q3 CBOW Test":
        run_q3_cbow()

if __name__ == "__main__":
    main()
