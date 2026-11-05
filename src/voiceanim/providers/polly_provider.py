"""AWS Polly text-to-speech provider with native SpeechMarks word-level alignment."""

from __future__ import annotations

import json
import os
import wave
from pathlib import Path
from typing import Any

from ..cache import AudioCache
from ..schema import AudioClip, SentenceTimestamp, WordTimestamp
from .base import BaseVoiceProvider

try:
    import boto3

    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


class PollyProvider(BaseVoiceProvider):
    """AWS Polly text-to-speech provider.

    Leverages AWS Polly Neural and Generative engines, and extracts native
    word-level and sentence-level SpeechMarks for precise whiteboard visual sync.
    """

    name = "polly"
    default_voice = "Matthew"
    supported_voices = [
        "Matthew",  # Neural / Generative male (flagship)
        "Ruth",  # Generative / Neural female
        "Joanna",  # Neural female
        "Stephen",  # Neural male
        "Danielle",  # Neural female
        "Gregory",  # Neural male
        "Amy",  # Generative British female
        "Olivia",  # Neural Australian female
    ]

    def __init__(
        self,
        engine: str = "neural",
        region_name: str | None = None,
        cache: AudioCache | None = None,
    ):
        self.engine = engine
        self.region_name = region_name or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        self.cache = cache or AudioCache()
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not HAS_BOTO3:
            raise ImportError(
                "AWS Polly provider requires 'boto3'. Install with:\n    poetry run pip install boto3"
            )
        self._client = boto3.client("polly", region_name=self.region_name)
        return self._client

    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float = 1.0,
        instruct: str | None = None,
        output_path: str | Path | None = None,
        **kwargs: Any,
    ) -> AudioClip:
        voice = voice or self.default_voice
        client = self._get_client()

        key = self.cache.compute_key(
            provider=self.name,
            voice=voice,
            text=text,
            speed=speed,
            model=self.engine,
            instruct=instruct,
        )

        # 1. Check content-addressed cache
        cached_clip = self.cache.get(key)
        if cached_clip is not None:
            if output_path and str(Path(output_path).resolve()) != str(Path(cached_clip.audio_path).resolve()):
                import shutil

                shutil.copyfile(cached_clip.audio_path, str(output_path))
                cached_clip.audio_path = str(output_path)
            return cached_clip

        # 2. Query Speech Marks (word and sentence timestamps)
        speech_marks_resp = client.synthesize_speech(
            Text=text,
            VoiceId=voice,
            Engine=self.engine,
            OutputFormat="json",
            SpeechMarkTypes=["word", "sentence"],
        )

        marks_raw = speech_marks_resp["AudioStream"].read().decode("utf-8")
        marks = [json.loads(line) for line in marks_raw.strip().splitlines() if line.strip()]

        # 3. Query Audio Stream (24kHz 16-bit PCM)
        sample_rate = 24000
        audio_resp = client.synthesize_speech(
            Text=text,
            VoiceId=voice,
            Engine=self.engine,
            OutputFormat="pcm",
            SampleRate=str(sample_rate),
        )

        pcm_bytes = audio_resp["AudioStream"].read()
        total_samples = len(pcm_bytes) // 2  # 16-bit = 2 bytes per sample
        duration = float(total_samples) / float(sample_rate)

        # 4. Save WAV file
        target_path = output_path or (self.cache.cache_dir / f"{key}.wav")
        Path(target_path).parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(target_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)

        # 5. Parse Speech Marks into WordTimestamp and SentenceTimestamp
        word_marks = [m for m in marks if m.get("type") == "word"]
        sentence_marks = [m for m in marks if m.get("type") == "sentence"]

        word_timings: list[WordTimestamp] = []
        for i, wm in enumerate(word_marks):
            start_sec = float(wm["time"]) / 1000.0
            if i + 1 < len(word_marks):
                next_start = float(word_marks[i + 1]["time"]) / 1000.0
                end_sec = min(next_start, start_sec + 0.8)
            else:
                end_sec = min(duration, start_sec + 0.6)

            word_timings.append(
                WordTimestamp(
                    word=wm["value"],
                    start=round(start_sec, 3),
                    end=round(end_sec, 3),
                    confidence=1.0,
                )
            )

        sentences: list[SentenceTimestamp] = []
        for sm in sentence_marks:
            start_sec = float(sm["time"]) / 1000.0
            # Gather words belonging to this sentence span
            sent_words = [w for w in word_timings if w.start >= start_sec - 0.05]
            end_sec = sent_words[-1].end if sent_words else start_sec + 1.0
            sentences.append(
                SentenceTimestamp(
                    text=sm["value"],
                    start=round(start_sec, 3),
                    end=round(end_sec, 3),
                    words=sent_words,
                )
            )

        if not sentences and word_timings:
            sentences = self.extract_sentences(text, word_timings)

        clip = AudioClip(
            audio_path=str(target_path),
            duration=round(duration, 3),
            sample_rate=sample_rate,
            text=text,
            words=word_timings,
            sentences=sentences,
            provider=self.name,
            voice=voice,
            instruct=instruct,
            metadata={"engine": self.engine, "region": self.region_name},
        )

        # 6. Put into cache
        self.cache.put(key, clip)
        if output_path:
            clip.audio_path = str(output_path)
        return clip
