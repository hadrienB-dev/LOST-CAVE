import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.entites import EntitesNiveau
from tools.level_entity_editor import default_entity


class LevelEntitiesRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        folder = Path(self.temporary_directory.name)
        self.map_path = folder / "test-map.json"
        entity_path = folder / "test-map.entities.json"
        entity = default_entity("enemy", 1, 96, 192)
        entity["sprite"] = str(
            Path(__file__).resolve().parents[1] / "assets" / "sprites" / "monster_1.png"
        )
        entity["movement"]["type"] = "stationary"
        entity_path.write_text(
            json.dumps({"entities": [entity]}),
            encoding="utf-8",
        )

    def test_saved_editor_enemy_is_loaded_with_its_sprite_and_position(self):
        entities = EntitesNiveau(self.map_path)

        self.assertEqual(len(entities.entites), 1)
        enemy = entities.entites[0]
        self.assertEqual((enemy["x"], enemy["y"]), (96, 192))
        self.assertEqual(enemy["category"], "enemy")
        self.assertIn(enemy["id"], entities.images)
        self.assertEqual(
            entities._hitbox(enemy),
            {"x": 4, "y": 16, "width": 24, "height": 16},
        )

    def test_loaded_sprite_is_drawn_at_saved_world_position(self):
        entities = EntitesNiveau(self.map_path)

        with patch("scripts.entites.pyxel.blt") as draw:
            entities.dessiner()

        draw.assert_called_once()
        arguments = draw.call_args.args
        self.assertEqual(arguments[:2], (96, 192))
        self.assertEqual(arguments[3:8], (0, 0, 32, 32, 8))

    def test_sprite_keeps_opaque_black_separate_from_transparency(self):
        image = EntitesNiveau(self.map_path).images["enemy-1"]

        self.assertEqual(image.pget(0, 0), 8)
        self.assertEqual(image.pget(9, 6), 0)

    def test_direction_sequences_select_cells_and_obey_frame_delay(self):
        entities = EntitesNiveau(self.map_path)
        enemy = entities.entites[0]
        enemy["animation"]["frame_delay_ms"] = 100
        enemy["animation"]["sequences"] = {
            "left": [
                {"column": 0, "row": 0},
                {"column": 1, "row": 1},
            ],
            "right": [{"column": 2, "row": 2}],
            "death": [],
        }
        enemy["movement"].update(
            type="steps",
            speed=1,
            steps=[{"direction": "left", "steps": 2}],
        )
        entities.distance_restante[enemy["id"]] = 2
        player = SimpleNamespace(x=0, y=0)
        entities._mettre_a_jour_mouvement(enemy, player)
        self.assertEqual(entities.orientations[enemy["id"]], "left")
        entities.debut_animations = 0

        with patch("scripts.entites.time.perf_counter", return_value=0.15):
            with patch("scripts.entites.pyxel.blt") as draw:
                entities.dessiner()

        self.assertEqual(draw.call_args.args[3:5], (32, 32))

        enemy["movement"]["steps"] = [{"direction": "right", "steps": 2}]
        entities.pas_courants[enemy["id"]] = 0
        entities.distance_restante[enemy["id"]] = 2
        entities._mettre_a_jour_mouvement(enemy, player)
        self.assertEqual(entities.orientations[enemy["id"]], "right")
        with patch("scripts.entites.time.perf_counter", return_value=0.15):
            with patch("scripts.entites.pyxel.blt") as draw:
                entities.dessiner()

        self.assertEqual(draw.call_args.args[3:5], (64, 64))

    def test_direction_sequence_uses_its_own_delay_and_flip_settings(self):
        entities = EntitesNiveau(self.map_path)
        enemy = entities.entites[0]
        enemy["animation"].update(frame_delay_ms=200, flip_y=True)
        enemy["animation"]["sequences"]["left"] = [
            {"column": 0, "row": 0},
            {"column": 1, "row": 1},
        ]
        enemy["animation"]["direction_settings"]["left"] = {
            "frame_delay_ms": 50,
            "flip_x": True,
            "flip_y": False,
        }
        entities.orientations[enemy["id"]] = "left"
        entities.debut_animations = 0

        with patch("scripts.entites.time.perf_counter", return_value=0.075):
            with patch("scripts.entites.pyxel.blt") as draw:
                entities.dessiner()

        self.assertEqual(draw.call_args.args[3:7], (32, 32, -32, 32))

    def test_death_sequence_uses_direction_condition_and_its_own_delay(self):
        entities = EntitesNiveau(self.map_path)
        enemy = entities.entites[0]
        enemy["animation"].update(frame_delay_ms=200, flip_x=False)
        enemy["animation"]["sequences"]["death"] = [
            {"column": 0, "row": 0},
            {"column": 1, "row": 1},
        ]
        enemy["animation"]["direction_settings"]["death"] = {
            "frame_delay_ms": 50,
            "flip_x": "direction_left",
            "flip_y": "direction_right",
        }
        entities.orientations[enemy["id"]] = "left"
        enemy["enabled"] = False
        entities.morts[enemy["id"]] = 0

        with patch("scripts.entites.time.perf_counter", return_value=0.075):
            with patch("scripts.entites.pyxel.blt") as draw:
                entities.dessiner()

        self.assertEqual(draw.call_args.args[3:7], (32, 32, -32, 32))

        with patch("scripts.entites.time.perf_counter", return_value=0.11):
            entities.mettre_a_jour(SimpleNamespace(x=0, y=0, velocity_y=0))

        self.assertNotIn(enemy["id"], entities.morts)

    def test_contact_damage_requests_existing_player_respawn(self):
        entities = EntitesNiveau(self.map_path)
        player = SimpleNamespace(
            x=100,
            y=192,
            velocity_y=0,
            reapparition_demandee=False,
        )

        entities.mettre_a_jour(player)

        self.assertTrue(player.reapparition_demandee)

    def test_enemy_outside_contact_does_not_request_respawn(self):
        entities = EntitesNiveau(self.map_path)
        player = SimpleNamespace(
            x=64,
            y=192,
            velocity_y=0,
            reapparition_demandee=False,
        )

        entities.mettre_a_jour(player)

        self.assertFalse(player.reapparition_demandee)

    def test_custom_hitbox_filters_collision_even_when_sprite_overlaps(self):
        entities = EntitesNiveau(self.map_path)
        enemy = entities.entites[0]
        enemy["hitbox"] = {"x": 8, "y": 16, "width": 12, "height": 12}
        player = SimpleNamespace(
            x=80,
            y=192,
            velocity_y=0,
            reapparition_demandee=False,
        )

        entities.mettre_a_jour(player)

        self.assertFalse(player.reapparition_demandee)

    def test_killable_enemy_is_defeated_by_landing_from_above(self):
        entities = EntitesNiveau(self.map_path)
        enemy = entities.entites[0]
        enemy["killable"] = True
        player = SimpleNamespace(
            x=100,
            y=180,
            velocity_y=0,
            au_sol=False,
            duree_saut=3,
            saut_en_attente=0,
            reapparition_demandee=False,
        )

        entities.mettre_a_jour(player, ancienne_y=170, ancienne_vitesse_y=5)

        self.assertFalse(enemy["enabled"])
        self.assertEqual(player.y, 176)
        self.assertLess(player.velocity_y, 0)
        self.assertFalse(player.reapparition_demandee)

    def test_stomp_plays_death_sequence_then_removes_enemy(self):
        entities = EntitesNiveau(self.map_path)
        enemy = entities.entites[0]
        enemy["killable"] = True
        enemy["animation"]["frame_delay_ms"] = 100
        enemy["animation"]["sequences"]["death"] = [
            {"column": 0, "row": 0},
            {"column": 1, "row": 1},
        ]
        player = SimpleNamespace(
            x=100,
            y=180,
            velocity_y=0,
            au_sol=False,
            duree_saut=3,
            saut_en_attente=0,
            reapparition_demandee=False,
        )

        with patch("scripts.entites.time.perf_counter", return_value=5.0):
            entities.mettre_a_jour(player, ancienne_y=170, ancienne_vitesse_y=5)

        self.assertFalse(enemy["enabled"])
        self.assertIn(enemy["id"], entities.morts)
        with patch("scripts.entites.time.perf_counter", return_value=5.15):
            with patch("scripts.entites.pyxel.blt") as draw:
                entities.dessiner()
        self.assertEqual(draw.call_args.args[3:5], (32, 32))

        with patch("scripts.entites.time.perf_counter", return_value=5.2):
            entities.mettre_a_jour(player)
            with patch("scripts.entites.pyxel.blt") as draw:
                entities.dessiner()
        draw.assert_not_called()
        self.assertNotIn(enemy["id"], entities.morts)

    def test_stomping_enemy_plays_and_caches_its_configured_sound(self):
        entities = EntitesNiveau(self.map_path)
        enemy = entities.entites[0]
        enemy["killable"] = True
        enemy["effects"]["sound"] = "assets/audio/kill_ennemy.ogg"
        player = SimpleNamespace(
            x=100,
            y=180,
            velocity_y=0,
            au_sol=False,
            duree_saut=3,
            saut_en_attente=0,
            reapparition_demandee=False,
        )
        sound = unittest.mock.Mock()

        with patch("scripts.entites.pygame.mixer.Sound", return_value=sound) as load_sound:
            entities.mettre_a_jour(player, ancienne_y=170, ancienne_vitesse_y=5)
            entities.mettre_a_jour(player, ancienne_y=170, ancienne_vitesse_y=5)

        load_sound.assert_called_once()
        sound.play.assert_called_once_with()

    def test_non_killable_enemy_still_damages_player_from_above(self):
        entities = EntitesNiveau(self.map_path)
        entities.entites[0]["killable"] = False
        player = SimpleNamespace(
            x=100,
            y=180,
            velocity_y=0,
            au_sol=False,
            duree_saut=0,
            saut_en_attente=0,
            reapparition_demandee=False,
        )

        entities.mettre_a_jour(player, ancienne_y=170, ancienne_vitesse_y=5)

        self.assertTrue(player.reapparition_demandee)

    def test_loop_movement_wraps_to_spawn_position(self):
        entities = EntitesNiveau(self.map_path)
        enemy = entities.entites[0]
        enemy["movement"].update(
            type="loop",
            axis="x",
            speed=3,
            range=40,
        )
        player = SimpleNamespace(x=0, y=0, velocity_y=0, reapparition_demandee=False)
        enemy["x"] = 134

        entities.mettre_a_jour(player)

        self.assertEqual(enemy["x"], 97)

    def test_step_sequence_moves_in_order_and_repeats_forever(self):
        entities = EntitesNiveau(self.map_path)
        enemy = entities.entites[0]
        enemy["movement"].update(
            type="steps",
            speed=2,
            steps=[
                {"direction": "right", "steps": 3},
                {"direction": "down", "steps": 2},
            ],
        )
        entities.distance_restante[enemy["id"]] = 3
        player = SimpleNamespace(x=0, y=0, velocity_y=0, reapparition_demandee=False)

        for _ in range(2):
            entities.mettre_a_jour(player)
        self.assertEqual((enemy["x"], enemy["y"]), (99, 193))

        for _ in range(2):
            entities.mettre_a_jour(player)
        self.assertEqual((enemy["x"], enemy["y"]), (102, 194))
        self.assertEqual(entities.pas_courants[enemy["id"]], 1)
        self.assertEqual(entities.distance_restante[enemy["id"]], 2)

        entities.mettre_a_jour(player)
        self.assertEqual((enemy["x"], enemy["y"]), (102, 196))
        self.assertEqual(entities.pas_courants[enemy["id"]], 0)
        self.assertEqual(entities.distance_restante[enemy["id"]], 3)


if __name__ == "__main__":
    unittest.main()
