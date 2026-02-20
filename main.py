import sys
import time
import subprocess
from pathlib import Path

import soundfile as sf
import sounddevice as sd
from PyQt6.QtWidgets import QApplication, QComboBox, QGridLayout, QLabel, QMainWindow, QPushButton, QScrollArea, QVBoxLayout, QHBoxLayout, QWidget

SINK_NAME = "virt_mic_sink"
SOURCE_NAME = "virt_mic"
SOUNDS_DIR = Path(__file__).parent / "sounds"
AUDIO_EXTS = {".wav"}


def pactl_command(args):
    return subprocess.check_output(["pactl"] + args.split(), text=True).strip()


def get_virtualmic_device():
    for i, d in enumerate(sd.query_devices()):
        if d["max_output_channels"] > 0 and "virtualmic" in d["name"].lower():
            return i


class App(QMainWindow):
    def __init__(self):
        super().__init__()

        self.device_index = None
        self.setWindowTitle("Soundboard")

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        row = QHBoxLayout()

        self.mic_combo = QComboBox()
        lines = pactl_command("list short sources").splitlines()
        mics = [l.split("\t")[1] for l in lines if l and not l.split("\t")[1].endswith(".monitor") and l.split("\t")[1] != SOURCE_NAME]
        self.mic_combo.addItems(mics)

        self.create_btn = QPushButton("Create Virtual Mic")
        self.create_btn.clicked.connect(self._create)

        row.addWidget(QLabel("Mic:"))
        row.addWidget(self.mic_combo, 1)
        row.addWidget(self.create_btn)

        layout.addLayout(row)

        self.status = QLabel("No virtual mic. Select a mic and click Create.")
        layout.addWidget(self.status)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        inner = QWidget()
        self.grid = QGridLayout(inner)

        scroll.setWidget(inner)
        layout.addWidget(scroll)

        SOUNDS_DIR.mkdir(exist_ok=True)
        self._load_sounds()

        existing = get_virtualmic_device()
        if existing is not None:
            self._ready(existing)

    def _create(self):
        self.status.setText("Setting up...")
        QApplication.processEvents()

        mic = self.mic_combo.currentText()
        sinks = pactl_command("list short sinks").splitlines()

        if not any(l.split("\t")[1] == SINK_NAME for l in sinks if l):
            pactl_command(f"load-module module-null-sink sink_name={SINK_NAME} sink_properties=device.description=VirtualMic")

        sources = pactl_command("list short sources").splitlines()

        if not any(l.split("\t")[1] == SOURCE_NAME for l in sources if l):
            pactl_command(f"load-module module-remap-source master={SINK_NAME}.monitor source_name={SOURCE_NAME} source_properties=device.description=VirtualMic")

        pactl_command(f"load-module module-loopback source={mic} sink={SINK_NAME} latency_msec=10")

        for _ in range(20):
            sd._terminate()
            sd._initialize()
            idx = get_virtualmic_device()
            if idx is not None:
                self._ready(idx)
                return
            time.sleep(0.1)

        self.status.setText("Device not found.")

    def _ready(self, idx):
        self.device_index = idx
        self.mic_combo.setEnabled(False)
        self.create_btn.setEnabled(False)
        self.status.setText("Virtual mic ready. Play sounds!")

        for i in range(self.grid.count()):
            self.grid.itemAt(i).widget().setEnabled(True)

    def _load_sounds(self):
        for i in reversed(range(self.grid.count())):
            self.grid.itemAt(i).widget().deleteLater()

        files = sorted(f for f in SOUNDS_DIR.iterdir() if f.suffix.lower() in AUDIO_EXTS)

        for n, f in enumerate(files):
            btn = QPushButton(f.stem)
            btn.setFixedHeight(60)
            btn.setEnabled(self.device_index is not None)
            btn.clicked.connect(lambda _, p=f: self._play(p))

            self.grid.addWidget(btn, n // 4, n % 4)

    def _play(self, path):
        data, sr = sf.read(str(path), dtype="float32")
        sd.play(data, sr, device=self.device_index, blocking=False)


app = QApplication(sys.argv)
window = App()
window.resize(600, 400)
window.show()
sys.exit(app.exec())
