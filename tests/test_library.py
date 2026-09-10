import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from ui.library import checked_path, delete_local, export_zip


class LibraryTests(unittest.TestCase):
    def test_zip_preserves_files_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            section = root/'Curso'/'Semana'
            (section/'Subcarpeta').mkdir(parents=True)
            (section/'a.pdf').write_bytes(b'original pdf')
            (section/'Subcarpeta'/'b.docx').write_bytes(b'original docx')
            first = export_zip(root,section)
            second = export_zip(root,section)
            self.assertNotEqual(first,second)
            self.assertEqual(first.parent,section.parent.resolve())
            with ZipFile(first) as archive:
                self.assertEqual(archive.read('Semana/a.pdf'),b'original pdf')
                self.assertEqual(archive.read('Semana/Subcarpeta/b.docx'),b'original docx')
                self.assertIsNone(archive.testzip())
            self.assertEqual((section/'a.pdf').read_bytes(),b'original pdf')

    def test_deletion_confined_to_downloads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/'downloads'
            root.mkdir()
            outside = Path(directory)/'outside.txt'
            outside.write_text('keep')
            for target in (root,outside):
                with self.assertRaises(ValueError):
                    delete_local(root,target)
            section = root/'Semana'
            section.mkdir()
            (section/'file.txt').write_text('remove')
            delete_local(root,section)
            self.assertFalse(section.exists())
            self.assertEqual(outside.read_text(),'keep')


if __name__ == '__main__':
    unittest.main()
