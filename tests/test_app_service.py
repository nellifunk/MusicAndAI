from pathlib import Path

from artwork_music.app_service import ArtworkMusicService


class FakePlayer:
    def play(self, path):
        self.path = path
        return f"played {path.name}"


def test_service_exposes_region_and_reuses_session():
    composition = Path(__file__).parents[1] / "output_klimt_kuss" / "composition.json"
    player = FakePlayer()
    service = ArtworkMusicService(composition, player=player)
    try:
        info = service.get_region_info(0)
        assert info["index"] == 0
        assert "relative_entropy" in info
        assert service.play_region(0).startswith("played cell_0_0")
        assert service.selected_index == 0
    finally:
        service.close()
