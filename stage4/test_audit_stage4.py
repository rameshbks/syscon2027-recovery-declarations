import json
import shutil
import tempfile
import unittest
from pathlib import Path
from audit_stage4 import audit


class AuditTests(unittest.TestCase):
    def test_changed_signed_packet_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            dest=Path(folder)/'results'
            shutil.copytree(Path(__file__).parent/'validation_pilot_linux_stage4',dest)
            p=dest/'traces.jsonl'
            lines=p.read_text().splitlines()
            row=json.loads(lines[0])
            row['packet']['body']['payload']['observed_level']=99
            lines[0]=json.dumps(row)
            p.write_text('\n'.join(lines)+'\n')
            with self.assertRaisesRegex(ValueError,'authentication decisions'):
                audit(dest)

    def test_missing_strategy_row_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            dest=Path(folder)/'results'
            shutil.copytree(Path(__file__).parent/'validation_pilot_linux_stage4',dest)
            p=dest/'runs.csv'
            p.write_text('\n'.join(p.read_text().splitlines()[:-1])+'\n')
            with self.assertRaisesRegex(ValueError,'evaluation count'):
                audit(dest)


if __name__=='__main__':
    unittest.main()
