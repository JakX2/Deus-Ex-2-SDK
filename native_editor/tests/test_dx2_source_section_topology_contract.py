from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[2]
class ContractTests(unittest.TestCase):
    def test_topology_contract(self):
        source = (ROOT / 'native_editor/godot_editor/collision_source_picker.gd').read_text('utf-8')
        self.assertIn('func section_topology_details', source)
if __name__ == '__main__':
    unittest.main()
