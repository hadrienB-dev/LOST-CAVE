import json
import tempfile
import unittest
from pathlib import Path

from tools.level_entity_editor import (
    default_entity,
    duplicate_entity,
    entities_file_for,
    load_document,
    normalize_entity,
    save_document,
    validate_entity,
)


class LevelEntityDocumentTests(unittest.TestCase):
    def test_duplicate_entity_copies_all_settings_and_nested_values(self):
        entity = default_entity("enemy", 3, 64, 96)
        entity["animation"]["direction_settings"]["death"]["frame_delay_ms"] = 50
        entity["effects"]["sound"] = "assets/audio/kill_ennemy.ogg"
        entity["custom_data"] = {"loot": ["key"]}

        duplicate = duplicate_entity(entity, 4)
        duplicate["animation"]["direction_settings"]["death"]["frame_delay_ms"] = 80
        duplicate["custom_data"]["loot"].append("gem")

        self.assertEqual(duplicate["id"], "enemy-4")
        self.assertEqual(duplicate["name"], "Ennemi 3 (copie)")
        self.assertEqual((duplicate["x"], duplicate["y"]), (96, 128))
        self.assertEqual(duplicate["effects"]["sound"], "assets/audio/kill_ennemy.ogg")
        self.assertEqual(
            entity["animation"]["direction_settings"]["death"]["frame_delay_ms"], 50
        )
        self.assertEqual(entity["custom_data"], {"loot": ["key"]})

    def test_default_entity_has_editable_animation_movement_and_effects(self):
        entity = default_entity("enemy", 3, 64, 96)

        self.assertEqual((entity["x"], entity["y"]), (64, 96))
        self.assertEqual(entity["animation"]["frame_count"], 1)
        self.assertEqual(entity["animation"]["frame_delay_ms"], 125)
        self.assertEqual(
            entity["animation"]["sequences"],
            {"left": [], "right": [], "death": []},
        )
        self.assertEqual(entity["movement"]["type"], "stationary")
        self.assertEqual(entity["movement"]["steps"], [])
        self.assertEqual(entity["effects"]["action"], "damage")
        self.assertEqual(entity["hitbox"], {"x": 4, "y": 16, "width": 24, "height": 16})
        self.assertFalse(entity["killable"])

    def test_normalize_preserves_custom_fields_and_adds_new_defaults(self):
        entity = normalize_entity(
            {
                "id": "old",
                "category": "item",
                "animation": {"fps": 2},
                "movement": {"speed": 2},
                "custom": 7,
            },
            1,
        )

        self.assertEqual(entity["custom"], 7)
        self.assertEqual(entity["movement"]["speed"], 2)
        self.assertEqual(entity["movement"]["type"], "stationary")
        self.assertEqual(entity["animation"]["frame_delay_ms"], 500)
        self.assertEqual(entity["effects"]["trigger"], "contact")

    def test_sidecar_path_sits_next_to_level(self):
        self.assertEqual(
            entities_file_for(Path("levels/cave.json")),
            Path("levels/cave.entities.json"),
        )

    def test_save_and_load_keeps_entity_settings_and_map_unmodified(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            map_path = folder / "level.json"
            entity_path = entities_file_for(map_path)
            map_data = {"width": 4, "height": 3, "layers": [], "tilesets": []}
            map_path.write_text(json.dumps(map_data), encoding="utf-8")
            entity = default_entity("special", 1, 32, 64)
            entity["movement"]["type"] = "path"
            entity["movement"]["waypoints"] = [[32, 64], [96, 64]]
            entity["movement"]["type"] = "loop"
            entity["movement"]["steps"] = [
                {"direction": "right", "steps": 80},
                {"direction": "left", "steps": 80},
            ]
            entity["hitbox"] = {"x": 8, "y": 20, "width": 12, "height": 10}
            entity["killable"] = True
            entity["animation"]["frame_delay_ms"] = 75
            entity["animation"]["sequences"] = {
                "left": [{"column": 1, "row": 0}],
                "right": [{"column": 2, "row": 1}],
                "death": [{"column": 0, "row": 2}],
            }
            entity["custom_data"] = {"script": "door"}

            save_document(map_path, entity_path, [entity])
            loaded_map, loaded_entities_path, loaded_map_data, entities = load_document(map_path)

            self.assertEqual(loaded_map, map_path.resolve())
            self.assertEqual(loaded_entities_path, entity_path.resolve())
            self.assertEqual(loaded_map_data, map_data)
            self.assertEqual(entities[0]["movement"]["type"], "loop")
            self.assertEqual(
                entities[0]["movement"]["steps"],
                [
                    {"direction": "right", "steps": 80},
                    {"direction": "left", "steps": 80},
                ],
            )
            self.assertEqual(entities[0]["hitbox"], {"x": 8, "y": 20, "width": 12, "height": 10})
            self.assertTrue(entities[0]["killable"])
            self.assertEqual(entities[0]["animation"]["frame_delay_ms"], 75)
            self.assertEqual(
                entities[0]["animation"]["sequences"]["death"],
                [{"column": 0, "row": 2}],
            )
            self.assertEqual(entities[0]["custom_data"], {"script": "door"})
            self.assertEqual(json.loads(map_path.read_text(encoding="utf-8")), map_data)

    def test_validation_rejects_non_positive_dimensions(self):
        entity = default_entity("item", 1)
        entity["width"] = 0

        with self.assertRaisesRegex(ValueError, "positives"):
            validate_entity(entity)

    def test_validation_rejects_invalid_movement_step(self):
        entity = default_entity("enemy", 1)
        entity["movement"]["steps"] = [{"direction": "diagonal", "steps": 20}]

        with self.assertRaisesRegex(ValueError, "direction"):
            validate_entity(entity)

    def test_validation_rejects_frame_outside_sequence_schema(self):
        entity = default_entity("enemy", 1)
        entity["animation"]["sequences"]["left"] = [{"column": -1, "row": 0}]

        with self.assertRaisesRegex(ValueError, "colonne"):
            validate_entity(entity)

    def test_validation_rejects_non_positive_frame_delay(self):
        entity = default_entity("enemy", 1)
        entity["animation"]["frame_delay_ms"] = 0

        with self.assertRaisesRegex(ValueError, "frame_delay_ms"):
            validate_entity(entity)

    def test_death_flip_can_be_conditional_on_enemy_direction(self):
        entity = default_entity("enemy", 1)
        entity["animation"]["direction_settings"]["death"]["flip_x"] = "direction_right"

        validate_entity(entity)

    def test_directional_flip_condition_is_only_valid_for_death(self):
        entity = default_entity("enemy", 1)
        entity["animation"]["direction_settings"]["left"]["flip_x"] = "direction_right"

        with self.assertRaisesRegex(ValueError, "direction_settings.left.flip_x"):
            validate_entity(entity)


if __name__ == "__main__":
    unittest.main()
