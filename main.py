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

def overlay_click_track(song_file, click_track, output_file, global_offset_ms):
    song = load_audio(song_file)
    
    if global_offset_ms > 0:
        click_track = AudioSegment.silent(duration=global_offset_ms) + click_track
    elif global_offset_ms < 0:
        song = AudioSegment.silent(duration=-global_offset_ms) + song
    
    # Ensure the click track is at least as long as the song
    if len(click_track) < len(song):
        click_track += AudioSegment.silent(duration=(len(song) - len(click_track)))
    
    overlaid_track = song.overlay(click_track)
    overlaid_track.export(output_file, format="wav")
    print(f"Overlaid track generated successfully: {output_file}")

    return len(overlaid_track) / 1000.0

def create_video_with_text(song, output_audio, output_video, album_art_path, total_duration):
    clips = []

    # Positioning of album art and time signature information
    album_art_position_y = (720 - 360) / 2  # Center vertically with a 720p height, album art height is 360
    time_signature_y = album_art_position_y + 360 + 40  # Position time signatures just below the album art
    
    current_time = 0.0
    current_measure = 1
    last_clip = None
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
            last_clip = txt_clip
        
        if offset < 0:
            current_time += abs(offset)
    
    if last_clip is not None:
        last_clip = last_clip.set_duration(total_duration - last_clip.start)
        clips.append(last_clip)


    # Load album art
    album_art = ImageClip(album_art_path).set_start(0).set_duration(total_duration).resize(height=360).set_position(('center', 'center'))  # Adjust size as needed

    # Title and album text
    title_clip = TextClip(song["title"], fontsize=40, color='white', bg_color='black').set_start(0).set_duration(total_duration)
    album_clip = TextClip(song["album"], fontsize=30, color='white', bg_color='black').set_start(0).set_duration(total_duration)
    artist_clip = TextClip(song["artist"], fontsize=30, color='white', bg_color='black').set_start(0).set_duration(total_duration)
    
    title_clip = title_clip.set_position(('center', 'top')).margin(top=20)
    album_clip = album_clip.set_position(('center', title_clip.size[1]))
    artist_clip = artist_clip.set_position(('center', album_clip.size[1] + title_clip.size[1]))

    clips.insert(0, title_clip)
    clips.insert(1, album_clip)
    clips.insert(2, artist_clip)
    clips.insert(3, album_art)

    video = CompositeVideoClip(clips, size=(1280, 720)).set_duration(total_duration)
    audio = AudioFileClip(output_audio).set_duration(total_duration)
    video = video.set_audio(audio)
    video.write_videofile(output_video, codec='libx264', fps=24)
    print(f"Video generated successfully: {output_video}")

input_file_path = 'Sempiternal Beings.json'
downbeat_file_path = 'down.wav'
non_downbeat_file_path = 'up.wav'
song_file_path = r"C:\Users\Tyson\Music\iTunes\iTunes Media\Music\Haken\Fauna\1-04 Sempiternal Beings.m4a"
output_file_path = 'output.wav'
output_video_path = 'output.mp4'
album_art_path = 'The Mountain Album Art.jpg'

with open(input_file_path, 'r') as file:
    song = json.load(file)

click_track = generate_click_track(song, downbeat_file_path, non_downbeat_file_path, output_file_path)
total_length = overlay_click_track(song_file_path, click_track, output_file_path, song["initial_offset_ms"])
# create_video_with_text(song, output_file_path, output_video_path, album_art_path, total_length)