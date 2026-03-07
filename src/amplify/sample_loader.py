import librosa
import os

def load_sample(file_path):
    """
    Core logic to load audio. 
    Raises FileNotFoundError, ValueError, or RuntimeError.
    """
    # 1. Existence Check
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file '{file_path}' does not exist.")

    # 2. Format Guard Clause
    supported = ('.wav', '.mp3')
    if not file_path.lower().endswith(supported):
        raise ValueError(f"Unsupported format. Amplify only accepts {supported}.")

    try:
        # 3. Actual Loading
        # sr=None preserves original sample rate
        signal, sr = librosa.load(file_path, sr=None)
        return signal, sr
        
    except Exception as e:
        # Catch corruption or decoding failures
        raise RuntimeError(f"Audio decoding failed: {e}")