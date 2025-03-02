from typing import Callable, Literal, Union
import json5
from pydub import AudioSegment
from moviepy.editor import TextClip, ImageClip, CompositeVideoClip, AudioFileClip
from dataclasses import dataclass


def load_audio(file_path: str) -> AudioSegment:
    return AudioSegment.from_file(file_path)


@dataclass
class Signature:
    numerator: int
    denominator: int
    offset_ms: int
    bpm: float
    beat_duration_ms: float
    measure_duration_ms: float
    beats_in_measure: int
    measures: int
    get_beat_type: Callable[[int], Union[Literal["down"], Literal["up"], Literal["sub"]]]


def decode_signature(signature) -> Signature:
    offset_ms = signature.get("offset", 0)
    bpm = signature['bpm']
    beat_duration_ms = (60 / signature['bpm']) * 1000
    measure_duration = beat_duration_ms * signature['numerator']
    measures = signature["measures"]

    subbeats_as_uppeats = signature.get("sub_beats_as_upbeats", False)
    sub_beat_multiplier = signature.get("sub_beat_multiplier", None)

    if sub_beat_multiplier is None:
        subbeats_as_uppeats = False

    if sub_beat_multiplier is not None and signature["numerator"] % sub_beat_multiplier != 0:
        raise Exception("Subbeat multiplier must evently divide the signature numerator")

    beats_in_measure = signature['numerator']
    if sub_beat_multiplier is not None and subbeats_as_uppeats:
        beats_in_measure /= sub_beat_multiplier
        bpm /= sub_beat_multiplier
        beat_duration_ms *= sub_beat_multiplier

    def get_beat_type(beat_index: int):
        if beat_index >= beats_in_measure:
            raise Exception("Beat index out of range")

        # The first beat is always down
        if beat_index == 0:
            return "down"

        # If we're using subbeats as upbeats, then the beats in the measure has already been divided out. The subbeats got turned into upbeats.
        if subbeats_as_uppeats:
            return "up"

        # If we aren't using subbeats as upbeats, and if the user didn't provide us with a sub_beat_multiplier, there are no subbeats.
        if sub_beat_multiplier is None:
            return "up"

        # If this beat landed on a subbeat multiplier, do a subbeat.
        if beat_index % sub_beat_multiplier == 0:
            return "sub"

        # Otherwise, do an up beat.
        return "up"

    return Signature(int(signature["numerator"]), int(signature["denominator"]), int(offset_ms), bpm, beat_duration_ms, measure_duration, int(beats_in_measure), int(measures), get_beat_type)


def generate_click_track(song, downbeat_file: str, non_downbeat_file: str) -> AudioSegment:
    downbeat = load_audio(downbeat_file) + 10
    non_downbeat = load_audio(non_downbeat_file) + 10
    subbeat = load_audio(subbeat_file_path) + 10

    final_track = AudioSegment.silent(duration=0)

    for signature in song['time_signatures']:
        sig = decode_signature(signature)

        # If the offset is positive, we will put the specified duration in silence at the beginning of this signature.
        if sig.offset_ms > 0:
            final_track += AudioSegment.silent(duration=sig.offset_ms)

        for _ in range(sig.measures):
            for beat in range(sig.beats_in_measure):
                beat_type = sig.get_beat_type(beat)

                if beat_type == "down":
                    final_track += downbeat[:sig.beat_duration_ms]
                elif beat_type == "up":
                    final_track += non_downbeat[:sig.beat_duration_ms]
                elif beat_type == "sub":
                    final_track += subbeat[:sig.beat_duration_ms]

        # TODO: Verify this actually works as intended.
        if sig.offset_ms < 0:
            final_track += AudioSegment.silent(duration=-sig.offset_ms)

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


def create_video_with_text(song, output_audio, output_video, album_art_path, total_duration, global_offset_ms):
    clips = []

    # Positioning of album art and time signature information
    # Center vertically with a 720p height, album art height is 360
    album_art_position_y = (720 - 360) / 2
    # Position time signatures just below the album art
    time_signature_y = album_art_position_y + 360 + 40

    current_time = global_offset_ms / 1000.0  # Start after the global offset
    current_measure = 1
    last_clip = None
    for signature in song['time_signatures']:
        sig = decode_signature(signature)
        time_signature_str = f"{sig.numerator}/{sig.denominator}"
        if sig.numerator != sig.beats_in_measure:
            time_signature_str = f"{sig.numerator}/{sig.denominator} (in {sig.beats_in_measure})"
        measures = sig.measures
        offset_seconds = sig.offset_ms / 1000.0
        measure_duration_seconds = sig.measure_duration_ms / 1000.0

        if offset_seconds > 0:
            current_time += offset_seconds

        for _ in range(1, measures + 1):
            txt = f"Time Signature: {time_signature_str}\nTempo: {sig.bpm} BPM\nMeasure: {current_measure}"
            txt_clip = TextClip(txt, fontsize=24, color='white').set_duration(measure_duration_seconds)
            txt_clip = txt_clip.set_position(('center', time_signature_y)).set_start(current_time)
            clips.append(txt_clip)
            current_time += measure_duration_seconds
            current_measure += 1
            last_clip = txt_clip

        if offset_seconds < 0:
            current_time += abs(offset_seconds)

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


input_file_path = 'songs/Panic Attack.jsonc'
downbeat_file_path = 'down.wav'
non_downbeat_file_path = 'up.wav'
subbeat_file_path = "subbeat.wav"
song_file_path = r"C:\Users\Tyson\Music\iTunes\iTunes Media\Music\Dream Theater\Octavarium\05 Panic Attack.m4a"
output_file_path = 'output.wav'
output_video_path = 'output.mp4'
album_art_path = 'art/Virus Album Art.jpg'

with open(input_file_path, 'r') as file:
    song = json5.load(file)

click_track = generate_click_track(song, downbeat_file_path, non_downbeat_file_path)
total_length = overlay_click_track(song_file_path, click_track, output_file_path, song["initial_offset_ms"])
# create_video_with_text(song, output_file_path, output_video_path, album_art_path, total_length, song["initial_offset_ms"])
