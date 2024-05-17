import pyaudio
import wave
from pydub import AudioSegment
import io

class AudioRecorder:
    """
    Class to record audio from the microphone.
    """
    def __init__(self, format=pyaudio.paInt16, channels=1, rate=44100, chunk=1024):
        self.format = format
        self.channels = channels
        self.rate = rate
        self.chunk = chunk
        self.frames = []
        self.stream = None
        self.audio = pyaudio.PyAudio()

    def start(self):
        """
        Start recording audio with callback.
        """
        self.stream = self.audio.open(format=self.format, channels=self.channels,
                                      rate=self.rate, input=True, frames_per_buffer=self.chunk,
                                      stream_callback=self.record_callback)
        self.frames = []
        self.stream.start_stream()
        print("Recording started.")

    def stop(self):
        """
        Stop the recording and close the stream.
        """
        self.stream.stop_stream()
        self.stream.close()
        print("Recording stopped.")

    def convert_to_audiosegment(self):
        """
        Convert the recorded frames to a pydub AudioSegment directly from raw data.
        """
        # Combine frames into a byte buffer
        raw_data = b''.join(self.frames)

        audio_segment = AudioSegment(
            data=raw_data,
            sample_width=self.audio.get_sample_size(self.format),
            frame_rate=self.rate,
            channels=self.channels
        )
        return audio_segment

    def record_callback(self, in_data, frame_count, time_info, status):
        """
        Callback function to collect frames from the audio stream.
        """
        self.frames.append(in_data)
        return (in_data, pyaudio.paContinue)
