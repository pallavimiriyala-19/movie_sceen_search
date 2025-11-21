import os
import tempfile
import unittest

from indexer.utils import extract_scene_id, validate_paths


class TestUtils(unittest.TestCase):
    def test_extract_scene_id_success(self):
        self.assertEqual(extract_scene_id('movie_01_scene_123.jpg'), 123)
        self.assertEqual(extract_scene_id('anyprefix_scene_45.png'), 45)
        self.assertEqual(extract_scene_id('prefix_scene_0007.jpeg'), 7)

    def test_extract_scene_id_failure(self):
        self.assertIsNone(extract_scene_id('no_scene_here.jpg'))
        self.assertIsNone(extract_scene_id('scene_abc.jpg'))
        self.assertIsNone(extract_scene_id(''))

    def test_validate_paths(self):
        with tempfile.TemporaryDirectory() as td:
            a = os.path.join(td, 'a')
            b = os.path.join(td, 'b')
            open(a, 'w').close()
            # b does not exist
            self.assertFalse(validate_paths(a, b))
            self.assertTrue(validate_paths(a))


if __name__ == '__main__':
    unittest.main()
