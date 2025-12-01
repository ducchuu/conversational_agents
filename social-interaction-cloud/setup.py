from setuptools import find_packages, setup

# Basic (bare minimum) requirements for local machine
requirements = [
    "numpy",
    "opencv-python",
    "paramiko",
    "Pillow",
    "pyaudio",
    "PyTurboJPEG",
    "pyspacemouse",
    "redis",
    "scp",
    "six",
]

# Dependencies specific to each component or server
extras_require = {
    "dev": [
        "black==24.10.0",
        "isort==5.13.2",
        "pre-commit==4.0.1",
        "twine",
        "wheel",
    ],
    "dialogflow": [
        "google-cloud-dialogflow",
    ],

    "nlu": [
        "torch~=2.4.1",
        "transformers~=4.45.1",
        "scikit-learn~=1.5.2",
    ],
    "webserver": [
        "Flask",
        "Flask-SocketIO",
    ],
    "whisper-speech-to-text": [
        "openai>=1.52.2",
        "SpeechRecognition>=3.11.0",
        "openai-whisper",
        "soundfile",
        "python-dotenv",
    ],
    "text2speech": [  # Adding text2speech dependencies
        "google-cloud-texttospeech",
    ],


}

setup(
    name="social-interaction-cloud",
    version="2.0.23",
    author="Koen Hindriks",
    author_email="k.v.hindriks@vu.nl",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    package_data={
"sic_framework.services.nlu.utils":  ["data/synonyms.json","data/ontology.json", "checkpoints/*.pt" ],
        "sic_framework.services.webserver": [
             "static/**/*",  "templates/*.html",
        ],
        "sic_framework.services.eis": ["dialogflow-keyfile.json"]
    },
    install_requires=requirements,
    extras_require=extras_require,
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*, !=3.6.*, !=3.7.*, !=3.8.*, !=3.9.*, <3.13",
    entry_points={
        "console_scripts": [
            "run-dialogflow=sic_framework.services.dialogflow:main",
            "run-nlu=sic_framework.services.nlu.bert_nlu:main",
            "run-whisper=sic_framework.services.openai_whisper_speech_to_text:main",
            "run-text2speech=sic_framework.services.text2speech.text2speech_service:main",
            "run-webserver=sic_framework.services.webserver.webserver_pca:main",
            "run-eis=sic_framework.services.eis.run_eis:main",
            "start-framework=sic_framework.services.eis.eiscomponent:main",

        ],
    },
)
