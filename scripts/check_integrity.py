"""Check exact distributed bytes before running analyses; exits nonzero on failure."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
 manifest=json.loads((ROOT/'CHECKSUMS.json').read_text())
 errors=[]
 for name,want in manifest.items():
  p=ROOT/name
  if not p.is_file():errors.append((name,'missing'))
  elif hashlib.sha256(p.read_bytes()).hexdigest()!=want:errors.append((name,'SHA-256 mismatch'))
 if errors:
  for name,issue in errors:print(f'{issue}: {name}')
  return 1
 print(f'PASS: {len(manifest)} file SHA-256 checks match.')
 return 0
if __name__=='__main__':sys.exit(main())
