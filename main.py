import json
from pydub import AudioSegment
from moviepy.editor import *

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

def create_video_with_text(song, output_audio, output_video):
    clips = []
    
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
            txt_clip = TextClip(txt, fontsize=24, color='white', bg_color='black', size=(1280, 720)).set_duration(measure_duration)
            txt_clip = txt_clip.set_start(current_time)
            clips.append(txt_clip)
            current_time += measure_duration
            current_measure += 1
        
        if offset < 0:
            current_time += abs(offset)
    
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

with open(input_file_path, 'r') as file:
    song = json.load(file)

click_track = generate_click_track(song, downbeat_file_path, non_downbeat_file_path, output_file_path)
overlay_click_track(song_file_path, click_track, output_file_path, song["initial_offset_ms"])
create_video_with_text(song, output_file_path, output_video_path)