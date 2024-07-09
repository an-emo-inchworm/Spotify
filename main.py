from flask import Flask, redirect, request, session, url_for, jsonify
import requests
import base64
import json
import urllib
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import csv

app = Flask(__name__)
app.secret_key = "" 

CLIENT_ID = "cfcb209cefd34a33bb6923bbee744b01"
CLIENT_SECRET = "9d30dbad4fe0453ca47458dbdcb09180"
REDIRECT_URI = "http://localhost:5000/callback" 

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE_URL = "https://api.spotify.com/v1/me/top/tracks"
AUDIO_FEATURES_URL = "https://api.spotify.com/v1/audio-features"
RECOMMENDATIONS_URL = "https://api.spotify.com/v1/recommendations"

sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET))

info = []
features = []
genres = []

@app.route("/")
def home():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "user-top-read",
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if code:
        auth_token = get_access_token(code)
        session["token"] = auth_token
        return redirect(url_for("get_top_tracks"))
    else:
        return "Authorization failed."

def get_access_token(code):
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Authorization": f"Basic {auth_header}"}
    response = requests.post(TOKEN_URL, data=data, headers=headers)
    return json.loads(response.text).get("access_token")

@app.route("/top-tracks")

def get_top_tracks():
    if "token" in session:
        headers = {
            "Authorization": f"Bearer {session['token']}"
        }

        response = requests.get(API_BASE_URL, headers=headers)
        temp_genre = []
        if response.status_code == 200:
            songs = json.loads(response.text)
            for t in songs["items"]:
                # print(songs["items"])
                id = t['id']
                name = t["name"]

                artists = ", ".join([artist["name"] for artist in t["artists"]])
                # info.append({"name": name, "artists": artists, "genres": ""})
                temp = get_audio_features(id)
                features.append(temp) 


                result = sp.search(artists)
                track = result['tracks']['items'][0]

                artist = sp.artist(track["artists"][0]["external_urls"]["spotify"])

                for i in artist["genres"]:
                    temp_genre.append(i)

                info.append({
                    "name": name,
                    "artists": artists,
                    "acousticness": temp['acousticness'],
                    "energy": temp['energy'],
                    "instrumentalness": temp['instrumentalness'],
                    "key": temp['key'],
                    "loudness": temp['loudness'],
                    "tempo": temp['tempo'],
                    "valence": temp['valence'],
                    "genres": ', '.join(temp_genre)
                })
                
            match(temp_genre, [
                "acoustic", "afrobeat", "alt-rock", "alternative", "ambient", "anime", "black-metal", "bluegrass", "blues",
                "bossanova", "brazil", "breakbeat", "british", "cantopop", "chicago-house", "children", "chill", "classical",
                "club", "comedy", "country", "dance", "dancehall", "death-metal", "deep-house", "detroit-techno", "disco",
                "disney", "drum-and-bass", "dub", "dubstep", "edm", "electro", "electronic", "emo", "folk", "forro", "french",
                "funk", "garage", "german", "gospel", "goth", "grindcore", "groove", "grunge", "guitar", "happy", "hard-rock",
                "hardcore", "hardstyle", "heavy-metal", "hip-hop", "holidays", "honky-tonk", "house", "idm", "indian", "indie",
                "indie-pop", "industrial", "iranian", "j-dance", "j-idol", "j-pop", "j-rock", "jazz", "k-pop", "kids", "latin",
                "latino", "malay", "mandopop", "metal", "metal-misc", "metalcore", "minimal-techno", "movies", "mpb", "new-age",
                "new-release", "opera", "pagode", "party", "philippines-opm", "piano", "pop", "pop-film", "post-dubstep", "power-pop",
                "progressive-house", "psych-rock", "punk", "punk-rock", "r-n-b", "rainy-day", "reggae", "reggaeton", "road-trip",
                "rock", "rock-n-roll", "rockabilly", "romance", "sad", "salsa", "samba", "sertanejo", "show-tunes", "singer-songwriter",
                "ska", "sleep", "songwriter", "soul", "soundtracks", "spanish", "study", "summer", "swedish", "synth-pop", "tango",
                "techno", "trance", "trip-hop", "turkish", "work-out", "world-music"
            ])

            save_to_csv(info, "top_tracks.csv") 
            info2 = redirect('/recommendations')
            return info2
        else:
            return f"Error: {response.status_code} - {response.text}"
    else:
        return "Please log in."

def save_to_csv(data, filename):
    
    print("saving")
    keys = data[0].keys()
    with open(filename, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(data)

def get_audio_features(track_id):
    headers = {"Authorization": f"Bearer {session['token']}"}
    url = f"{AUDIO_FEATURES_URL}/{track_id}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        audio_features = json.loads(response.text)
        return audio_features
    else:
        return f"Error: {response.status_code} - {response.text}"
    
def match(personalized, basic):
    for i in personalized:
        if(contains(i, basic) and contains(i, genres) == False):
            genres.append(i)
    print(genres)

def contains(song, basic):
    for i in basic:
        if i == song:
            return True
    return False

@app.route("/recommendations")
def get_recommendations():
    minacc, maxacc, mine, maxe, mininstr, maxinstr, minloud, maxloud, mintemp, maxtemp, minval, maxval = process(features)
    if "token" in session:
        headers = {"Authorization": f"Bearer {session['token']}"}

        seed_genres = genres
        min_acousticness = minacc 
        max_acousticness = maxacc 

        params = {
            "seed_genres": seed_genres,
            "min_acousticness": min_acousticness,
            "max_acousticness": max_acousticness,
            "min_energy" : mine,
            "max_energy" : maxe,
            "min_instrumentalness" : mininstr,
            "max_instrumentalness" : maxinstr,
            "min_loudness" : minloud,
            "max_loudness" : maxloud,
            "min_tempo" : mintemp,
            "max_tempo" : maxtemp,
            "min_valence" : minval,
            "max_valence" : maxval
        }

        response = requests.get(RECOMMENDATIONS_URL, headers=headers, params=params)

        if response.status_code == 200:
            recommendations = json.loads(response.text)
            
            recommended_tracks = []
            for track in recommendations["tracks"]:
                track_name = track["name"]
                artists = ", ".join([artist["name"] for artist in track["artists"]])
                recommended_tracks.append({"name": track_name, "artists": artists})

            save_to_csv(recommended_tracks, "recs.csv") 

            return jsonify(recommended_tracks)
        else:
            return f"Error: {response.status_code} - {response.text}"
    else:
        return "Unauthorized. Please log in."

def get_audio_features(track_id):
    headers = {"Authorization": f"Bearer {session['token']}"}
    url = f"{AUDIO_FEATURES_URL}/{track_id}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        audio_features = json.loads(response.text)
        return audio_features
    else:
        return f"Error: {response.status_code} - {response.text}"

def get_stats(acc):
    acc.sort()
    mid = len(acc)//2
    med = (acc[mid] + acc[mid+1])/2
    mean = sum(acc) / len(acc) 
    variance = sum([((x - mean) ** 2) for x in acc]) / len(acc) 
    std = variance ** 0.5
    return med, std

# def get_key(acc):
#     pass

def process(fe):
    acousticness = []
    energy = []
    instrumentalness = []
    key = []
    loudness = []
    tempo = []
    valence = []

    for f in fe:
        acousticness.append(f['acousticness'])
        energy.append(f['energy'])
        instrumentalness.append(f['instrumentalness'])
        key.append(f['key'])
        loudness.append(f['loudness'])
        tempo.append(f['tempo'])
        valence.append(f['valence'])
    accmedian, accstd = get_stats(acousticness)
    minacc = accmedian - accstd
    maxacc = accmedian + accstd
    energymed, energystd = get_stats(energy)
    mine = energymed - energystd
    maxe = energymed + energystd
    instrmed, instrstd = get_stats(instrumentalness)
    mininstr = instrmed - instrstd
    maxinstr = instrmed + instrstd
    loudmed, loudstd = get_stats(loudness)
    minloud = loudmed - loudstd
    maxloud = loudmed + loudstd
    tempmed, tempstd = get_stats(tempo)
    mintemp = tempmed - tempstd
    maxtemp = tempmed + tempstd
    valmed, valstd = get_stats(valence)
    minval = valmed - valstd
    maxval = valmed + valstd

    return minacc, maxacc, mine, maxe, mininstr, maxinstr, minloud, maxloud, mintemp, maxtemp, minval, maxval

if __name__ == "__main__":
    app.run(host = '0.0.0.0', debug=True)