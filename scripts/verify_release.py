"""Readback verification in a new temporary extraction; does not recollect HTTP campaigns."""
from pathlib import Path
import sys,subprocess,tempfile,shutil,json,csv,hashlib,time
ROOT=Path(__file__).resolve().parents[1]
def run(cmd,cwd):
 print('RUN '+' '.join(map(str,cmd)),flush=True)
 subprocess.run([sys.executable,*map(str,cmd)],cwd=cwd,check=True)
def main():
 begin=time.monotonic()
 if (ROOT/'CHECKSUMS.json').exists():
  for n,h in json.loads((ROOT/'CHECKSUMS.json').read_text()).items():
   assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,('Checksum mismatch',n)
 with tempfile.TemporaryDirectory(prefix='syscon-reproduce-') as tmp:
  work=Path(tmp)/'artifact'
  shutil.copytree(ROOT,work,ignore=shutil.ignore_patterns('__pycache__','.git','.venv'))
  # No pip installation, package import side effects, or services outside loopback.
  run(['-m','unittest','discover','-s','stage4','-p','test_*.py'],work)
  run(['independent_v8/experiment/test_plant.py'],work)
  original=work/'reproduced_original'
  run(['original_http/analysis/analyze_stage5.py','--archive','original_http/stage4_results_full_windows_v1.zip','--out',original],work)
  for name in ['strategy_summary.csv','scenario_outcomes.csv','paired_gate_v2_gate_v3.csv','paired_intervals.csv','latency_by_scenario.csv','scenario_weight_sensitivity.csv']:
   # CSV metadata-independent, compare exact retained numeric/text cells.
   old=list(csv.reader((work/'original_http/analysis/outputs'/name).open()))
   new=list(csv.reader((original/name).open()))
   assert old==new,('Original CSV differs',name)
  run(['scripts/window_sensitivity.py','--input',original/'input/stage4_results_full_windows_v1','--out',work/'sensitivity_reproduced.json'],work)
  held=json.loads((work/'validation/analysis.json').read_text())
  run(['validation/analyze_validation.py'],work)
  assert held==json.loads((work/'validation/analysis.json').read_text()),'Held-out analysis differs'
  nl=work/'independent_v8/experiment'
  old=json.loads((nl/'analysis.json').read_text())
  run(['independent_v8/experiment/audit_analyze.py'],work)
  assert old==json.loads((nl/'analysis.json').read_text()),'Nonlinear analysis differs'
  run(['independent_v8/experiment/check_trajectories.py'],work)
  run(['independent_v8/experiment/check_measurement_cases.py'],work)
  run(['independent_v8/experiment/make_outputs.py'],work)
  run(['scripts/reproduce_paper_tables.py','--out',work/'reproduced_paper'],work)
  for name in ['table_IV.csv','table_V.csv','table_VI.csv','table_VII.csv','table_VIII.csv']:
   assert (work/'reproduced_paper'/name).read_bytes()==(work/'paper_outputs'/name).read_bytes(),name
 print(json.dumps({'status':'PASS','elapsed_seconds':round(time.monotonic()-begin,2),'original_samples':27300,'heldout_samples':19200,'nonlinear_samples':1733760,'assessments':50040,'new_http_campaign_collected':False,'nonlinear_process_trajectories_numerically_checked':320}),flush=True)
if __name__=='__main__':main()
