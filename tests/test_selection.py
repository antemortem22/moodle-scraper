import unittest
from unittest.mock import patch

from main import select_sections
from models import Section
from scraper.sections import normalize_sections
from selection import parse_section_selection


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.sections = [Section("General" if i == 1 else f"Unidad {i}", i) for i in range(1, 8)]

    def test_formats_order_and_duplicates(self):
        cases = {
            "3": [3], "2,3,5": [2, 3, 5], "2-5": [2, 3, 4, 5],
            "1,3-5,7": [1, 3, 4, 5, 7], "5,2,3-5": [2, 3, 4, 5],
            " 1 , 3 - 5 , 7 ": [1, 3, 4, 5, 7], "2,2,2-2": [2],
            "all": list(range(1, 8)), " ALL ": list(range(1, 8)),
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                result = parse_section_selection(value, self.sections)
                self.assertEqual([s.position for s in result], expected)
                for section in result:
                    self.assertIs(section, self.sections[section.position - 1])

    def test_invalid_input(self):
        for value in ("", " ", "0", "8", "-1", "2-8", "5-2", "1,", ",1", "1,,2", "all,2", "abc", "2.5", "1-2-3", "1 2", "1-999999999999"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_section_selection(value, self.sections)
        with self.assertRaises(ValueError):
            parse_section_selection("all", [])

    def test_restricted_sections(self):
        sections = [Section("General", 1), Section("Semana futura", 2, is_available=False), Section("Unidad", 3)]
        self.assertEqual(parse_section_selection("all", sections), [sections[0], sections[2]])
        self.assertEqual(parse_section_selection("3,1", sections), [sections[0], sections[2]])
        for value in ("2", "1,2", "1-3"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Moodle restringe"):
                parse_section_selection(value, sections)
        with patch("builtins.input", side_effect=["2", "all"]), patch("builtins.print") as output:
            self.assertEqual(select_sections(sections), [sections[0], sections[2]])
            self.assertIn("Semana futura", output.call_args.args[0])

    def test_all_restricted(self):
        sections = [Section("Futura", 1, is_available=False)]
        self.assertEqual(parse_section_selection("all", sections), [])
        with patch("builtins.input") as prompt, patch("builtins.print"):
            self.assertEqual(select_sections(sections), [])
            prompt.assert_not_called()

    def test_retry_in_console(self):
        with patch("builtins.input", side_effect=["abc", "0", "1,3"]), patch("builtins.print") as output:
            self.assertEqual(select_sections(self.sections), [self.sections[0], self.sections[2]])
            self.assertEqual(output.call_count, 2)

    def test_empty_list_does_not_prompt(self):
        with patch("builtins.input") as prompt:
            self.assertEqual(select_sections([]), [])
            prompt.assert_not_called()

    def test_fallback_only_for_untitled_first_section(self):
        for first, expected in ((" \n ", "General"), (" Bienvenida ", "Bienvenida")):
            rows = [{"key": "0", "name": first, "url": ""}, {"key": "1", "name": "", "url": ""}]
            result = normalize_sections(rows, "https://example.test/course")
            self.assertEqual([s.name for s in result], [expected, "Sección sin título (2)"])


if __name__ == "__main__":
    unittest.main()
