import json
from pydub import AudioSegment
from moviepy.editor import *

def load_audio(file_path):
    return AudioSegment.from_file(file_path)

def generate_click_track(song, downbeat_file, non_downbeat_file, output_file):
    downbeat = load_audio(downbeat_file) + 10
    non_downbeat = load_audio(non_downbeat_file) + 10
    
    final_track = AudioSegment.silent(duration=0)
    
    for signature in song['time_signatures']:
        beat_duration_ms = (60 / signature['bpm']) * 1000  # convert to milliseconds
        offset = signature.get('offset', 0)  # get the offset, default to 0 if not provided

        if offset > 0:
            final_track += AudioSegment.silent(duration=offset)
        
        for measure in range(signature['measures']):
            for beat in range(signature['numerator']):
                if beat == 0:
                    final_track += downbeat[:beat_duration_ms]
                else:
                    final_track += non_downbeat[:beat_duration_ms]

        if offset < 0:
            final_track += AudioSegment.silent(duration=-offset)
    
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

def create_video_with_text(song, output_audio, output_video, album_art_path):
    clips = []

    # Positioning of album art and time signature information
    album_art_position_y = (720 - 360) / 2  # Center vertically with a 720p height, album art height is 360
    time_signature_y = album_art_position_y + 360 + 40  # Position time signatures just below the album art
    
    current_time = 0.0
    current_measure = 1
    for signature in song['time_signatures']:
        bpm = signature['bpm']
        time_signature = f"{signature['numerator']}/{signature['denominator']}"
        measures = signature['measures']
        offset = signature.get('offset', 0) / 1000.0  # convert to seconds
        
        if offset > 0:
            current_time += offset
        
        beat_duration = 60.0 / bpm
        measure_duration = beat_duration * signature['numerator']
        
        for _ in range(1, measures + 1):
            txt = f"Time Signature: {time_signature}\nTempo: {bpm} BPM\nMeasure: {current_measure}"
            txt_clip = TextClip(txt, fontsize=24, color='white').set_duration(measure_duration)
            txt_clip = txt_clip.set_position(('center', time_signature_y)).set_start(current_time)
            clips.append(txt_clip)
            current_time += measure_duration
            current_measure += 1
        
        if offset < 0:
            current_time += abs(offset)
    
    # Load album art
    album_art = ImageClip(album_art_path).set_start(0).set_duration(current_time).resize(height=360).set_position(('center', 'center'))  # Adjust size as needed

    # Title and album text
    title_clip = TextClip(song["title"], fontsize=40, color='white', bg_color='black').set_start(0).set_duration(current_time)
    album_clip = TextClip(song["album"], fontsize=30, color='white', bg_color='black').set_start(0).set_duration(current_time)
    artist_clip = TextClip(song["artist"], fontsize=30, color='white', bg_color='black').set_start(0).set_duration(current_time)
    
    title_clip = title_clip.set_position(('center', 'top')).margin(top=20)
    album_clip = album_clip.set_position(('center', title_clip.size[1]))
    artist_clip = artist_clip.set_position(('center', album_clip.size[1] + title_clip.size[1]))

    clips.insert(0, title_clip)
    clips.insert(1, album_clip)
    clips.insert(2, artist_clip)
    clips.insert(3, album_art)

    video = CompositeVideoClip(clips, size=(1280, 720)).set_duration(current_time)
    audio = AudioFileClip(output_audio).set_duration(current_time)
    video = video.set_audio(audio)
    video.write_videofile(output_video, codec='libx264', fps=24)
    print(f"Video generated successfully: {output_video}")

input_file_path = 'Atlas Stone.json'
downbeat_file_path = 'down.wav'
non_downbeat_file_path = 'up.wav'
song_file_path = "C:/Users/Tyson/Music/iTunes/iTunes Media/Music/Haken/The Mountain/02 Atlas Stone.m4a"
output_file_path = 'output.wav'
output_video_path = 'output.mp4'
album_art_path = 'The Mountain Album Art.jpg'

with open(input_file_path, 'r') as file:
    song = json.load(file)

click_track = generate_click_track(song, downbeat_file_path, non_downbeat_file_path, output_file_path)
overlay_click_track(song_file_path, click_track, output_file_path, song["initial_offset_ms"])
create_video_with_text(song, output_file_path, output_video_path, album_art_path)