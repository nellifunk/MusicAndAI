import cmd
import json
import shlex

from .base import ControllerAdapter

HELP = """Commands (rows and columns are 0..3):
  ports                  List available MIDI outputs (numbered from 1)
  port NUMBER            Select an output from that list
  play ROW COL           Play current cell, or report its MIDI file
  show ROW COL           Inspect features, constraints, costs, and notes
  set valence VALUE      Emotional offset, -0.5..0.5
  set energy VALUE       Movement offset, -0.5..0.5
  set complexity VALUE   Entropy offset, -0.5..0.5
  set brightness VALUE   Lightness offset, -0.5..0.5
  rebuild                Apply pending offsets to all 16 phrases
  reset                  Set all offsets to zero and rebuild
  save NAME              Save a new personal interpretation
  status                 Display current and pending settings
  diagnostics            Report musical diversity and duplicate lead sequences
  help / quit
The original input composition is preserved. Unsaved previews expire on exit."""


class TerminalController(cmd.Cmd, ControllerAdapter):
    prompt = "artwork> "
    intro = HELP

    def __init__(self, session, stdin=None, stdout=None):
        super().__init__(stdin=stdin, stdout=stdout)
        self.session = session
        if stdin is not None:
            self.use_rawinput = False
        if session.composition.schema_version == "1.0":
            self.intro = HELP + "\nLegacy composition loaded; rebuild/reset upgrades its music to engine 1.2."

    def select_cell(self, row, col):
        return self.session.play(row, col)

    def set_valence(self, value):
        self.session.set_offset("valence", value)

    def set_energy(self, value):
        self.session.set_offset("energy", value)

    def set_complexity(self, value):
        self.session.set_offset("complexity", value)

    def set_brightness(self, value):
        self.session.set_offset("brightness", value)

    def save_interpretation(self, name):
        return self.session.save(name)

    def onecmd(self, line):
        try:
            return super().onecmd(line)
        except KeyboardInterrupt:
            self.stdout.write("\nPlayback or command interrupted.\n")
        except (ValueError, OSError, RuntimeError) as exc:
            self.stdout.write(f"Error: {exc}\n")
        return False

    def emptyline(self):
        return None

    def do_help(self, arg):
        self.stdout.write(HELP + "\n")

    def _coordinates(self, arg):
        parts = shlex.split(arg)
        if len(parts) != 2:
            raise ValueError("Expected ROW COL, for example: 0 2")
        return tuple(int(p) for p in parts)

    def do_play(self, arg):
        self.stdout.write(self.select_cell(*self._coordinates(arg)) + "\n")

    def do_ports(self, arg):
        if arg.strip():
            raise ValueError("ports takes no arguments")
        ports = self.session.player.output_names()
        if not ports:
            self.stdout.write("No MIDI output ports available. Check the device connection.\n")
        for number, name in enumerate(ports, start=1):
            self.stdout.write(f"{number}: {name}\n")
        if ports:
            self.stdout.write("Select your instrument with port NUMBER, then play ROW COL.\n")

    def do_port(self, arg):
        try:
            number = int(arg.strip())
        except ValueError as exc:
            raise ValueError("Expected: port NUMBER. Run ports to list available outputs.") from exc
        ports = self.session.player.output_names()
        if not 1 <= number <= len(ports):
            raise ValueError("Invalid port number. Run ports to list available outputs.")
        self.session.player.select_port(ports[number - 1])
        self.stdout.write(f"Selected MIDI output: {ports[number - 1]}\n")

    def do_show(self, arg):
        cell = self.session.cell(*self._coordinates(arg))
        self.stdout.write(f"Cell ({cell.row},{cell.column})\n")
        self.stdout.write(json.dumps(cell.model_dump(mode="json"), indent=2) + "\n")
        self.stdout.write("Ensemble: " + self.session.composition.global_music.instruments.model_dump_json() + "\n")

    def do_set(self, arg):
        parts = shlex.split(arg)
        if len(parts) != 2:
            raise ValueError("Expected: set DIMENSION VALUE")
        self.session.set_offset(parts[0], float(parts[1]))
        self.stdout.write("Offset staged. Run rebuild to apply it.\n")

    def do_rebuild(self, arg):
        if arg.strip():
            raise ValueError("rebuild takes no arguments")
        composition = self.session.rebuild()
        music = composition.global_music
        self.stdout.write(f"Rebuilt 16 cells: {music.tonic} {music.mode}, {music.tempo_bpm} BPM.\n")
        self.do_diagnostics("")

    def do_reset(self, arg):
        if arg.strip():
            raise ValueError("reset takes no arguments")
        self.session.reset()
        self.stdout.write("Offsets reset to zero; rebuilt 16 cells.\n")
        self.do_diagnostics("")

    def do_diagnostics(self, arg):
        if arg.strip():
            raise ValueError("diagnostics takes no arguments")
        from ..music.diagnostics import diagnose, format_diagnostics
        composition = self.session.composition
        self.stdout.write(format_diagnostics(composition.diagnostics or diagnose(composition.cells, composition.global_music)) + "\n")

    def do_save(self, arg):
        parts = shlex.split(arg)
        if len(parts) != 1:
            raise ValueError("Expected: save NAME")
        self.stdout.write(f"Saved {self.save_interpretation(parts[0])}\n")

    def do_status(self, arg):
        self.stdout.write("Current: " + self.session.composition.interpretation.model_dump_json() + "\n")
        self.stdout.write("Pending: " + self.session.pending.model_dump_json() + "\n")

    def do_quit(self, arg):
        return True

    def do_exit(self, arg):
        return True

    def do_EOF(self, arg):
        self.stdout.write("\n")
        return True
