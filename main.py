import json
from pydub import AudioSegment

def load_audio(file_path):
    return AudioSegment.from_file(file_path)

def generate_click_track(song, downbeat_file, non_downbeat_file, output_file):
    downbeat = load_audio(downbeat_file)
    non_downbeat = load_audio(non_downbeat_file)
    
    final_track = AudioSegment.silent(duration=0)
    
    for signature in song['time_signatures']:
        beat_duration_ms = (60 / signature['bpm']) * 1000  # convert to milliseconds
        
        for measure in range(signature['measures']):
            for beat in range(signature['numerator']):
                if beat == 0:
                    final_track += downbeat[:beat_duration_ms]
                else:
                    final_track += non_downbeat[:beat_duration_ms]
    
    return final_track

def overlay_click_track(song_file, click_track, output_file, offset_ms):
    song = load_audio(song_file)
    
    if offset_ms > 0:
        # Positive offset: add silence at the beginning of the click track
        click_track = AudioSegment.silent(duration=offset_ms) + click_track
    elif offset_ms < 0:
        # Negative offset: add silence at the beginning of the song
        song = AudioSegment.silent(duration=-offset_ms) + song
    
    # Ensure the click track matches the song length
    if len(click_track) > len(song):
        click_track = click_track[:len(song)]
    else:
        click_track = click_track + AudioSegment.silent(duration=(len(song) - len(click_track)))
    
    overlaid_track = song.overlay(click_track)
    overlaid_track.export(output_file, format="wav")
    print(f"Overlaid track generated successfully: {output_file}")

input_file_path = 'Atlas Stone.json'
downbeat_file_path = 'down.mp3'
non_downbeat_file_path = 'up.mp3'
song_file_path = "C:/Users/Tyson/Music/iTunes/iTunes Media/Music/Haken/The Mountain/02 Atlas Stone.m4a"
output_file_path = 'output.wav'

with open(input_file_path, 'r') as file:
    song = json.load(file)

click_track = generate_click_track(song, downbeat_file_path, non_downbeat_file_path, output_file_path)
overlay_click_track(song_file_path, click_track, output_file_path, song["initial_offset_ms"])