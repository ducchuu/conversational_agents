from pathlib import Path

from setuptools import find_packages, setup

HERE = Path(__file__).resolve().parent
REQUIREMENTS_FILE = HERE / "requirements.txt"


def read_requirements(path):
    """Single source of truth for pinned runtime dependencies (also used by the Dockerfile)."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


requirements = [
    "numpy",
    "requests",
    "six",
]

extras_require = {
    "dev": [
        "black==24.10.0",
        "isort==5.13.2",
        "pre-commit==4.0.1",
        "pytest>=8.0.0",
        "pytest-asyncio",
        "ruff",
    ],
    "nlu": [
        "onnxruntime==1.31.0",
        "tokenizers==0.20.3",
        "torch==2.4.1",
        "transformers==4.45.2",
        "scikit-learn==1.5.2",
        "tqdm",
    ],
    "webserver": read_requirements(REQUIREMENTS_FILE),
    "dialogflow": [
        "google-cloud-dialogflow",
    ],
    "whisper-speech-to-text": [
        "openai>=1.52.2",
        "SpeechRecognition>=3.11.0",
        "openai-whisper",
        "soundfile",
        "python-dotenv",
    ],
    "text2speech": [
        "google-cloud-texttospeech",
    ],
    "google-stt": [
        "google-cloud-speech",
    ],
}

readme_text = "Social Interaction Cloud — CookingBroski Conversational Agent"
try:
    with open("README.md", "r", encoding="utf-8") as f:
        readme_text = f.read()
except (FileNotFoundError, OSError):
    pass

setup(
    name="social-interaction-cloud",
    version="2.1.0",
    author="Koen Hindriks",
    author_email="k.v.hindriks@vu.nl",
    long_description=readme_text,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    package_data={
        "sic_framework.services.nlu.utils": [
            "data/synonyms.json",
            "data/ontology.json",
            "data/vocab.txt",
            "checkpoints/*.pt",
            "checkpoints/*.onnx",
            "data/*.json",
        ],
        "sic_framework.services.webserver": [
            "static/**/*",
            "templates/*.html",
        ],
    },
    install_requires=requirements,
    extras_require=extras_require,
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "run-webserver=sic_framework.services.webserver.webserver_pca:main",
            "train-nlu=sic_framework.services.nlu.train_and_export:main",
            "audit-nlu-data=sic_framework.services.nlu.utils.dataset_audit:main",
            "run-dialogflow=sic_framework.services.dialogflow.dialogflow:main",
            "run-whisper=sic_framework.services.openai_whisper_speech_to_text.whisper_speech_to_text:main",
            "run-text2speech=sic_framework.services.text2speech.text2speech_service:main",
            "run-google-stt=sic_framework.services.google_stt.google_stt:main",
        ],
    },
)
