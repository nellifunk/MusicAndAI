"""Local NiceGUI frontend for the artwork-to-music prototype."""
from __future__ import annotations
import argparse
import json
import re
import subprocess
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from nicegui import app, run, ui
except ImportError as exc:  # pragma: no cover - exercised only without optional dependency
    raise SystemExit("NiceGUI is not installed. Run: pip install -e '.[frontend]'") from exc

from artwork_music.app_service import ArtworkMusicService
from artwork_music.render.midi_player import MidoOutput


def create_app(composition_path: Path, image_path: Path | None = None, midi_port: str | None = None):
    service = ArtworkMusicService(composition_path, player=MidoOutput(midi_port) if midi_port else None)
    composition = service.get_composition()
    selected = {"index": None}
    load_state = {"request": 0, "active": False, "pending_index": None}
    playback_state = {"request": 0}
    image_url = None
    if image_path:
        image_path = image_path.resolve()
        app.add_static_files('/artwork', str(image_path.parent))
        image_url = f"/artwork/{image_path.name}"
    manifest_path = Path(__file__).parent / "data" / "artworks.json"
    catalog = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    project_root = Path(__file__).parent.resolve()
    app.add_static_files('/catalog', str(project_root))

    ui.colors(primary="#d4b483", secondary="#28323c", accent="#e6c58e",
              dark="#101417", positive="#9bbf9a", negative="#d78686")
    ui.dark_mode().enable()
    with ui.header().classes("items-center justify-between bg-[#11171b] px-6 py-3"):
        ui.label("ARTWORK / MUSIC").classes("text-lg tracking-[0.25em] text-[#e6c58e]")
        ui.label("RESEARCH PROTOTYPE").classes("text-xs tracking-[0.2em] text-gray-500")
    with ui.expansion("Choose an Artwork", icon="collections_bookmark").classes("mx-6 mt-4 bg-[#171d21] text-[#e6c58e]") as gallery:
        ui.label("Curated public-domain collection").classes("mb-3 text-xs tracking-[0.15em] text-gray-500")
        with ui.grid(columns=4).classes("w-full gap-3"):
            for artwork in catalog:
                asset = Path(__file__).parent / artwork["image"]
                with ui.card().classes("cursor-pointer bg-[#20272b] p-0 transition hover:bg-[#303034]") as card:
                    if asset.exists():
                        relative_asset = asset.resolve().relative_to(project_root).as_posix()
                        ui.image(f"/catalog/{relative_asset}").classes("h-32 w-full object-cover")
                    else:
                        with ui.element("div").classes("flex h-32 items-center justify-center bg-[#15191c] text-xs text-gray-600"):
                            ui.label("Image pending")
                    ui.label(artwork["title"]).classes("px-3 pt-2 text-sm text-[#f0dfc0]")
                    ui.label(f'{artwork["artist"]} · {artwork["year"]}').classes("px-3 pb-3 text-xs text-gray-500")
                    card.on("click", lambda a=artwork: select_catalog_artwork(a))
    with ui.row().classes("w-full gap-0 p-6 lg:p-10"):
        with ui.column().classes("w-full lg:w-3/5 gap-4"):
            with ui.card().classes("relative w-full overflow-hidden bg-[#171d21] p-0"):
                if image_url:
                    image_element = ui.image(image_url).classes("pointer-events-none block h-auto w-full")
                else:
                    image_element = None
                    ui.label("No artwork image supplied").classes("m-12 text-gray-500")
                cells = []
                with ui.element("div").classes("absolute inset-0 z-10 grid grid-cols-4 grid-rows-4"):
                    for index in range(16):
                        cell = ui.element("div").classes(
                            "z-20 cursor-pointer border border-white/25 bg-transparent transition-colors duration-150 "
                            "hover:bg-[#a94b3f]/35 hover:border-[#e6c58e]/80"
                        )
                        cell.style("background-color: transparent;")
                        cell.on("click", lambda e=None, i=index: select(i))
                        cells.append(cell)
            title_label = ui.label(composition.artwork.title).classes("text-xl tracking-wide text-[#f0dfc0]")
            metadata_label = ui.label(f"{composition.artwork.artist} · {composition.artwork.year or 'Year unknown'}").classes("text-sm text-gray-500")
            ui.button("Change Artwork", on_click=lambda: gallery.open()).props("flat")
        with ui.column().classes("w-full lg:w-2/5 gap-4 px-0 lg:px-8"):
            status = ui.label("Ready").classes("text-sm text-[#e6c58e]")
            with ui.card().classes("bg-[#171d21] p-5"):
                ui.label("REGION ANALYSIS").classes("mb-3 text-xs tracking-[0.2em] text-gray-500")
                with ui.column().classes("gap-1"):
                    analysis_prompt = ui.label("Select a region to view its analysis.").classes("text-sm text-gray-400")
                    analysis_lines = {
                        key: ui.label("").classes("text-xs text-gray-300")
                        for key in ("relative_entropy", "relative_movement", "relative_edge_density",
                                    "relative_lightness", "orientation_deg", "lead_note_onsets",
                                    "accompaniment_template", "bass_template")
                    }
            with ui.card().classes("bg-[#171d21] p-5"):
                ui.label("INTERPRETATION").classes("mb-3 text-xs tracking-[0.2em] text-gray-500")
                sliders = {}
                for label, key in (("Mood / Valence", "valence"), ("Energy / Movement", "movement"), ("Complexity / Entropy", "complexity"), ("Brightness / Lightness", "lightness")):
                    with ui.row().classes("w-full items-center"):
                        ui.label(label).classes("w-40 text-xs")
                        sliders[key] = ui.slider(min=-0.5, max=0.5, step=0.01, value=0).classes("flex-1")
                with ui.row().classes("mt-4 gap-2"):
                    ui.button("Reinterpret Artwork", on_click=lambda: rebuild()).props("unelevated")
                    ui.button("Reset", on_click=lambda: reset()).props("flat")
            with ui.card().classes("bg-[#171d21] p-5"):
                ui.label("COMPOSITION").classes("mb-3 text-xs tracking-[0.2em] text-gray-500")
                instruments = composition.global_music.instruments
                def instrument_text(value):
                    return ", ".join(value) if isinstance(value, tuple) else value
                composition_labels = {}
                for label, value in (
                    ("Tonic", composition.global_music.tonic),
                    ("Mode", composition.global_music.mode.capitalize()),
                    ("Tempo", f"{composition.global_music.tempo_bpm} BPM"),
                    ("Era", composition.artwork.music_era.value),
                    ("Lead instruments", instrument_text(instruments.lead)),
                    ("Accompaniment instruments", instrument_text(instruments.accompaniment)),
                    ("Bass instruments", instrument_text(instruments.bass)),
                ):
                    composition_labels[label] = ui.label(f"{label}: {value}").classes("text-sm")
                save_name = ui.input("Save name", value="web-interpretation").classes("w-full")
                ui.button("Save Interpretation", on_click=lambda: save(save_name.value)).props("flat")

    async def select(index):
        try:
            if load_state["active"]:
                load_state["pending_index"] = index
                selected["index"] = index
                ui.notify("The composition is still loading. Please wait a moment.", type="warning")
                return
            selected["index"] = index
            active_service = service
            active_service.stop_playback()
            render_info(active_service.get_region_info(index))
            for i, cell in enumerate(cells):
                if i == index:
                    cell.style("background-color: rgba(169, 75, 63, 0.45); border: 2px solid #e6c58e;")
                else:
                    cell.style("background-color: transparent; border: 1px solid rgba(255,255,255,0.25);")
            playback_state["request"] += 1
            playback_request = playback_state["request"]
            status.set_text(f"Region {index + 1}: playing…")
            result = await run.io_bound(active_service.play_region, index)
            if playback_request != playback_state["request"] or active_service is not service:
                return
            status.set_text(f"Region {index + 1}: {result}")
            ui.notify(f"Region {index + 1} selected", type="positive")
        except Exception as exc:
            ui.notify(str(exc), type="negative")

    async def select_catalog_artwork(artwork):
        nonlocal service, image_element
        asset = Path(__file__).parent / artwork["image"]
        if not asset.exists():
            ui.notify(f'Asset not available locally yet: {artwork["title"]}', type="warning")
            return
        load_state["request"] += 1
        request_id = load_state["request"]
        load_state["active"] = True
        load_state["pending_index"] = None
        selected["index"] = None
        analysis_prompt.set_visibility(True)
        for label in analysis_lines.values():
            label.set_text("")
        # Collapse the picker before starting the analysis. The analysis command
        # can take a few seconds, so it must run off the NiceGUI event loop or
        # the browser cannot receive this update until the command finishes.
        gallery.value = False
        relative_asset = asset.resolve().relative_to(project_root).as_posix()
        # Show the selected artwork immediately. The composition is swapped in
        # when analysis completes, so the interface never looks stuck on the
        # previous artwork during the expensive first-time analysis.
        if image_element is not None:
            image_element.set_source(f"/catalog/{relative_asset}")
        title_label.set_text(artwork["title"])
        metadata_label.set_text(f'{artwork["artist"]} · {artwork["year"]}')
        status.set_text(f"Loading {artwork['title']}…")
        output_dir = Path(__file__).parent / "output_frontend" / artwork["id"]
        composition_file = output_dir / "composition.json"
        year_match = re.search(r"\d{4}", artwork["year"])
        command = [sys.executable, "main.py", "analyze", "--image", str(asset),
                   "--title", artwork["title"], "--artist", artwork["artist"],
                   "--year", year_match.group(0) if year_match else "0",
                   "--art-movement", artwork["movement"], "--output", str(output_dir),
                   "--semantic-sidecar", str(Path(__file__).parent / "examples" / "demo.semantic.json")]
        try:
            if not composition_file.is_file():
                await run.io_bound(
                    subprocess.run, command, cwd=Path(__file__).parent, text=True,
                    capture_output=True, check=True,
                )
            if request_id != load_state["request"]:
                return
            service.stop_playback()
            service.close()
            service = ArtworkMusicService(composition_file,
                                          player=MidoOutput(midi_port) if midi_port else None)
            updated = service.get_composition()
            updated_instruments = updated.global_music.instruments
            for label, value in (
                ("Tonic", updated.global_music.tonic),
                ("Mode", updated.global_music.mode.capitalize()),
                ("Tempo", f"{updated.global_music.tempo_bpm} BPM"),
                ("Era", updated.artwork.music_era.value),
                ("Lead instruments", instrument_text(updated_instruments.lead)),
                ("Accompaniment instruments", instrument_text(updated_instruments.accompaniment)),
                ("Bass instruments", instrument_text(updated_instruments.bass)),
            ):
                composition_labels[label].set_text(f"{label}: {value}")
            load_state["active"] = False
            pending_index = load_state["pending_index"]
            load_state["pending_index"] = None
            status.set_text(f"Loaded {artwork['title']}")
            # Keep the picker closed after the asynchronous update as well.
            gallery.value = False
            ui.notify(f"Analyzed and loaded {artwork['title']}", type="positive")
            if pending_index is not None:
                await select(pending_index)
        except subprocess.CalledProcessError as exc:
            if request_id == load_state["request"]:
                load_state["active"] = False
            detail = (exc.stderr or exc.stdout or "analysis failed").strip().splitlines()[-1]
            status.set_text("Analysis failed")
            ui.notify(detail, type="negative")
        except Exception as exc:
            if request_id == load_state["request"]:
                load_state["active"] = False
            status.set_text("Could not load artwork")
            ui.notify(str(exc), type="negative")

    def render_info(data):
        analysis_prompt.set_visibility(False)
        for key, label in analysis_lines.items():
            value = data.get(key)
            label.set_text(f"{key.replace('_', ' ').title()}: {value}" if value is not None else "")

    def rebuild():
        try:
            result = service.rebuild_interpretation(*(sliders[k].value for k in ("valence", "movement", "complexity", "lightness")))
            status.set_text(f"Rebuilt: {result.global_music.mode}, {result.global_music.tempo_bpm} BPM")
        except Exception as exc: ui.notify(str(exc), type="negative")

    def reset():
        try:
            service.reset_interpretation()
            for slider in sliders.values(): slider.value = 0
            status.set_text("Interpretation reset")
        except Exception as exc: ui.notify(str(exc), type="negative")

    def save(name):
        try:
            destination = service.save_interpretation(name)
            ui.notify(f"Saved to {destination}", type="positive")
        except Exception as exc: ui.notify(str(exc), type="negative")

    return service


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("composition", type=Path)
    parser.add_argument("--image", type=Path)
    parser.add_argument("--midi-port", help="MIDI output name or unique substring, e.g. 'FLUID Synth'")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    create_app(args.composition, args.image, args.midi_port)
    ui.run(host="127.0.0.1", port=args.port, title="Artwork / Music", reload=False)
