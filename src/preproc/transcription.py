"""
This file contains the code for the transcription of audio files using the Whisper library.
"""

from faster_whisper import WhisperModel


def transcribe_audio(audio_filepaths, transcription_kwargs):
    """
    Transcribe a list of audio filepaths using Whisper.
    """
    model = WhisperModel(
        "large-v3",
        device="cuda",
        compute_type="float16",
        download_root="/scr/verbal-protocol/whisper",
    )
    # batched_pipeline = BatchedInferencePipeline(model=model)

    all_segments = []
    for filepath in audio_filepaths:
        if filepath == "NONE":
            segments = []
        else:
            segments, _ = model.transcribe(
                filepath,
                **transcription_kwargs,
            )
        all_segments.append(segments)

    texts = []
    for segments in all_segments:
        text = "".join([s.text for s in segments])
        # These lines occur a lot in hallucinations and aren't relevant, so we can manually remove them
        text = text.replace(
            " You will play a mathematical game where you start with a set of 4 numbers and have to make the number 24.",
            "",
        )
        text = text.replace(
            " As you perform the task, try to say aloud everything that comes to mind.",
            "",
        )
        texts.append(text)

    return texts
