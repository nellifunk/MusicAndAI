import argparse
import hashlib
import logging
import os
import sys
from pathlib import Path

from .models import Artwork, Era, Model, SemanticAnalysis


class SemanticCache(Model):
    image_sha256: str
    artwork: Artwork
    model: str
    semantics: SemanticAnalysis


def resolve_semantics(args, rgb, artwork):
    from .analysis.semantic_base import SemanticProviderError
    from .analysis.semantic_sidecar import SidecarSemanticAnalyzer
    from .storage import write_json
    sidecar = args.semantic_sidecar
    conventional = args.image.with_suffix(".semantic.json")
    if sidecar is None and conventional.is_file():
        sidecar = conventional
    if sidecar is not None:
        return SidecarSemanticAnalyzer(sidecar).analyze(rgb, artwork)
    model = args.vision_model or os.environ.get("OPENAI_VISION_MODEL", "")
    digest = hashlib.sha256(str(rgb.shape).encode() + rgb.tobytes()).hexdigest()
    cache_path = args.output / "semantic_cache.json"
    if cache_path.is_file() and not args.refresh_semantics:
        cache = SemanticCache.model_validate_json(cache_path.read_text(encoding="utf-8"))
        if cache.image_sha256 == digest and cache.artwork == artwork and (not model or cache.model == model):
            print("Reusing cached semantic analysis.")
            return cache.semantics
    if not os.environ.get("OPENAI_API_KEY"):
        raise SemanticProviderError(
            "Semantic analysis unavailable. Supply --semantic-sidecar FILE (see examples/demo.semantic.json), "
            "or configure OPENAI_API_KEY and --vision-model / OPENAI_VISION_MODEL."
        )
    from .analysis.semantic_openai import OpenAISemanticAnalyzer
    print("Analyzing semantics with the configured vision provider…")
    semantics = OpenAISemanticAnalyzer(model).analyze(rgb, artwork)
    write_json(cache_path, SemanticCache(image_sha256=digest, artwork=artwork, model=model, semantics=semantics))
    return semantics


def analyze(args):
    from .analysis.image_grid import grid_overlay, load_rgb
    from .analysis.pipeline import analyze_image
    from .music.ensemble import compose
    from .music.eras import music_era
    from .music.global_mapping import load_palette
    from .music.scales import tonic_pitch_class
    from .storage import write_composition, write_json
    era = music_era(args.year, args.music_era_override)
    artwork = Artwork(title=args.title, artist=args.artist, year=args.year,
                      art_movement=args.art_movement, music_era=era)
    tonic_pitch_class(args.tonic)
    instruments = load_palette(era, args.palette)
    rgb = load_rgb(args.image)
    semantics = resolve_semantics(args, rgb, artwork)
    print("Measuring full artwork and 16 grid cells…")
    raw = analyze_image(rgb, artwork, semantics)
    print("Composing 16 deterministic layered phrases…")
    composition = compose(raw, tonic=args.tonic, instruments=instruments)
    write_json(args.output / "analysis_raw.json", raw)
    write_json(args.output / "semantic_analysis.json", semantics)
    grid_overlay(rgb, args.output / "grid_overlay.png")
    write_composition(args.output, composition)
    music = composition.global_music
    print(f"Saved {args.output.resolve()}: {music.tonic} {music.mode}, {music.tempo_bpm} BPM, {era.value}.")
    print("16 cell MIDI files and overview.mid are ready.")
    from .music.diagnostics import format_diagnostics
    print(format_diagnostics(composition.diagnostics))


def recompose(args):
    from .music.ensemble import compose
    from .music.diagnostics import format_diagnostics
    from .storage import load_composition, write_composition, write_json
    previous = load_composition(args.composition)
    character = previous.global_music.character
    if args.character:
        from .music.character import character_for_artwork
        character = character or character_for_artwork(previous.artwork, previous.raw_global_visual)
    composition = compose(previous.raw_analysis(), previous.interpretation,
                          character.tonic if character else previous.global_music.tonic,
                          previous.global_music.instruments, character=character)
    write_composition(args.output, composition)
    write_json(args.output / "analysis_raw.json", previous.raw_analysis())
    print(f"Recomposed all 16 cells without image/API analysis: {args.output.resolve()}")
    print(format_diagnostics(composition.diagnostics))


def interact(args):
    from .controller.repl import TerminalController
    from .controller.session import InterpretationSession
    from .render.midi_player import MidoOutput
    with InterpretationSession(args.composition, player=MidoOutput(args.midi_port)) as session:
        if not args.classic and session.composition.global_music.character is None:
            session.enable_artwork_character()
        TerminalController(session).cmdloop()


def chordcat(args):
    from .controller.chordcat import calibrate, run
    from .controller.session import InterpretationSession
    from .render.midi_player import MidoOutput
    xy_mapping = None
    if args.calibrate:
        calibration_path = args.composition.parent / "chordcat_mapping.json"
        xy_mapping = calibrate(args.midi_input, calibration_path)
    target = args.playback_target
    if target is None:
        answer = input("Playback target: [1] CHORDCAT  [2] laptop MIDI output: ").strip().lower()
        target = "laptop" if answer in {"2", "laptop", "midi"} else "chordcat"
    if target == "chordcat":
        player = MidoOutput(args.midi_port, prefer_chordcat=True)
    else:
        player = MidoOutput(args.midi_port, prefer_chordcat=False)
    print(f"Playback target: {target}")
    with InterpretationSession(args.composition, player=player) as session:
        if not args.classic and session.composition.global_music.character is None:
            session.enable_artwork_character()
        run(session, args.midi_input, args.debug, args.ambiguous, xy_mapping)


def list_ports(args):
    from .render.midi_player import MidoOutput
    ports = MidoOutput().output_names()
    if not ports:
        print("No MIDI output ports available. Check the device connection.")
    for number, name in enumerate(ports, start=1):
        print(f"{number}: {name}")


def parser():
    root = argparse.ArgumentParser(description="Explore an artwork as 16 deterministic layered musical phrases.")
    commands = root.add_subparsers(dest="command", required=True)
    ports = commands.add_parser("ports", help="List MIDI output ports or explain backend failures")
    ports.set_defaults(handler=list_ports)
    rebuild = commands.add_parser("recompose", help="Recompose saved raw features using the current engine")
    rebuild.add_argument("composition", type=Path)
    rebuild.add_argument("--output", type=Path, required=True)
    rebuild.add_argument("--character", action="store_true", help="Compose with the artwork's authored motif and rhythm family")
    rebuild.set_defaults(handler=recompose)
    analysis = commands.add_parser("analyze", help="Analyze an image and render all MIDI outputs")
    analysis.add_argument("--image", type=Path, required=True)
    analysis.add_argument("--title", required=True)
    analysis.add_argument("--artist", required=True)
    analysis.add_argument("--year", type=int)
    analysis.add_argument("--art-movement", required=True)
    analysis.add_argument("--music-era-override", choices=[e.value for e in Era])
    analysis.add_argument("--semantic-sidecar", type=Path)
    analysis.add_argument("--vision-model", help="Vision model ID; alternatively OPENAI_VISION_MODEL")
    analysis.add_argument("--refresh-semantics", action="store_true", help="Explicitly discard matching API semantic cache")
    analysis.add_argument("--tonic", default="D")
    analysis.add_argument("--palette", type=Path, help="Alternate instrument_palettes.yaml")
    analysis.add_argument("--output", type=Path, default=Path("output"))
    analysis.set_defaults(handler=analyze)
    interactive = commands.add_parser("interact", help="Explore and reinterpret a saved composition")
    interactive.add_argument("composition", type=Path)
    interactive.add_argument("--midi-port", help="Exact MIDI output name; defaults to first available port")
    interactive.add_argument("--classic", action="store_true", help="Play the saved notes without adding an artwork theme")
    interactive.set_defaults(handler=interact)
    chord = commands.add_parser("chordcat", help="Control a saved composition from an AlphaTheta CHORDCAT")
    chord.add_argument("composition", type=Path)
    chord.add_argument("--midi-port", help="MIDI output for playback")
    chord.add_argument("--classic", action="store_true", help="Play the saved notes without adding an artwork theme")
    chord.add_argument("--playback-target", choices=["chordcat", "laptop"],
                       help="Playback destination; prompts at startup when omitted")
    chord.add_argument("--midi-input", help="Exact CHORDCAT MIDI input name; auto-detected when possible")
    chord.add_argument("--calibrate", action="store_true",
                       help="Capture mood keys 1, 7, 13 and 16 XY cells for each before playback")
    chord.add_argument("--debug", action="store_true", help="Print non-clock MIDI events and unknown signatures")
    chord.add_argument("--ambiguous", choices=["reject", "xy", "mood"], default="xy",
                       help="Policy for signatures shared by XY pad and mood keys (default: xy)")
    chord.set_defaults(handler=chordcat)
    return root


def main(argv=None):
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    args = parser().parse_args(argv)
    try:
        args.handler(args)
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except (ValueError, OSError, RuntimeError, ImportError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
