from abc import ABC, abstractmethod
from pathlib import Path
import sys
from threading import Event, Lock


class MidiUnavailable(RuntimeError):
    """Backend or device access is unavailable; file rendering is unaffected."""


def backend_error(exc: Exception) -> str:
    if isinstance(exc, ImportError):
        return ("The MIDI backend is not installed in this Python environment. "
                "Run: python -m pip install python-rtmidi, then restart the program. "
                f"Details: {exc}")
    if sys.platform.startswith("linux") and not Path("/dev/snd/seq").exists():
        return ("The ALSA MIDI device /dev/snd/seq is not accessible in this environment. "
                "Run the prototype in a terminal on the computer connected to the MIDI device. "
                f"Details: {exc}")
    return f"{type(exc).__name__}: {exc}"


class MidiOutput(ABC):
    @abstractmethod
    def output_names(self) -> tuple[str, ...]:
        """Enumerate available destinations, or raise MidiUnavailable."""
        raise NotImplementedError

    @abstractmethod
    def select_port(self, name: str) -> None:
        """Select an available output by its exact name."""
        raise NotImplementedError

    @abstractmethod
    def play(self, path: Path) -> str:
        """Play a file, or return a human-readable fallback containing its path."""
        raise NotImplementedError

    def stop(self) -> None:
        """Stop the current playback, if the output supports interruption."""
        return None


class MidoOutput(MidiOutput):
    def __init__(self, port_name: str | None = None, prefer_chordcat: bool = True):
        self.port_name = port_name
        self.prefer_chordcat = prefer_chordcat
        self._playback_lock = Lock()
        self._stop_event = Event()

    def stop(self) -> None:
        with self._playback_lock:
            self._stop_event.set()

    def _begin_playback(self) -> Event:
        with self._playback_lock:
            self._stop_event.set()
            self._stop_event = Event()
            return self._stop_event

    def output_names(self) -> tuple[str, ...]:
        import mido
        try:
            return tuple(mido.get_output_names())
        except (ImportError, OSError, RuntimeError, SystemError, ValueError) as exc:
            raise MidiUnavailable(backend_error(exc)) from exc

    def select_port(self, name: str) -> None:
        resolved = self._resolve_port(name, self.output_names())
        if resolved is None:
            raise ValueError(f"MIDI output {name!r} is not available. Run ports to list outputs.")
        self.port_name = resolved

    @staticmethod
    def _resolve_port(requested: str, ports: tuple[str, ...]) -> str | None:
        if requested in ports:
            return requested
        matches = [p for p in ports if requested.casefold() in p.casefold()]
        return matches[0] if len(matches) == 1 else None

    def play(self, path: Path) -> str:
        import mido
        # Importing/initializing rtmidi may itself fail without a MIDI/ALSA server.
        stop_event = self._begin_playback()
        try:
            ports = self.output_names()
            if not ports:
                return f"No MIDI output port available. MIDI file: {path}"
            if self.port_name:
                name = self._resolve_port(self.port_name, ports)
                if name is None:
                    return f"MIDI port {self.port_name!r} is unavailable. MIDI file: {path}"
            else:
                # Prefer the connected CHORDCAT when it exposes an output;
                # falling back to the first available port preserves legacy use.
                hardware = [p for p in ports if "chordcat" in p.lower() or "alphatheta" in p.lower()] if self.prefer_chordcat else []
                name = hardware[0] if hardware else ports[0]
            with mido.open_output(name) as port:
                try:
                    # Use an interruptible clock instead of MidiFile.play(),
                    # whose internal sleep would keep the previous region
                    # audible until its next scheduled event.
                    for message in mido.MidiFile(str(path)):
                        if stop_event.wait(max(0.0, message.time)):
                            break
                        if message.is_meta:
                            continue
                        # CHORDCAT's internal playback listens on MIDI channel
                        # 5. Its port is also
                        # exposed as an output, so collapse generated layers
                        # onto that receive channel when targeting CHORDCAT.
                        if "chordcat" in name.lower() or "alphatheta" in name.lower():
                            if hasattr(message, "channel"):
                                message = message.copy(channel=5)
                        port.send(message)
                finally:
                    # Includes interrupted playback; avoid hanging notes.
                    port.reset()
            return f"Played {path.name} through {name}"
        except (ImportError, OSError, RuntimeError, SystemError, ValueError) as exc:
            details = str(exc) if isinstance(exc, MidiUnavailable) else backend_error(exc)
            return f"Real-time MIDI unavailable: {details}\nMIDI file: {path}"
