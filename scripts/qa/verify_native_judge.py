import os,time,uuid,json
import frappe
os.chdir('/home/frappe/bench-data/frappe-bench/sites')
frappe.init(site='school.localhost');frappe.connect();frappe.set_user('Administrator')
from lms.lms.judge_service import run_programming_exercise,submit_programming_exercise,get_programming_submission_status
exercise='kg44c3uvm5'
codes={'Python': 'import sys\nfor x in sys.stdin.read().split():\n whole, _, frac = x.partition(".")\n print(int(whole or "0") + int(bool(frac) and frac[0] >= "5"))\n', 'C++': '#include <iostream>\n#include <string>\nint main(){std::string s;while(std::cin>>s){auto p=s.find(\'.\');std::string n=s.substr(0,p);if(n.empty())n="0";if(p!=std::string::npos && p+1<s.size() && s[p+1]>=\'5\'){int i=(int)n.size()-1;while(i>=0 && n[i]==\'9\'){n[i]=\'0\';--i;}if(i<0)n="1"+n;else ++n[i];}auto z=n.find_first_not_of(\'0\');std::cout<<(z==std::string::npos?"0":n.substr(z))<<"\\n";}}\n'}
created=[];results=[]
try:
 for language,code in codes.items():
  run=run_programming_exercise(exercise=exercise,code=code,language=language)
  print(json.dumps({'language':language,'run':run}),flush=True)
  assert run['status']=='ACCEPTED',run
  sub=submit_programming_exercise(exercise=exercise,code=code,language=language,client_request_id='native-e2e-'+uuid.uuid4().hex)
  created.append(sub['submission']);frappe.db.commit()
  print('Queued',language,sub['submission'],flush=True)
  # Observe real worker dispatch and authenticated callback; do not dispatch manually.
  for _ in range(120):
   frappe.db.rollback()
   doc=frappe.get_doc('LMS Programming Exercise Submission',sub['submission'])
   if doc.status not in ('Queued','Compiling','Running'):break
   time.sleep(1)
  result={'language':language,'submission':doc.name,'status':doc.status,'score':doc.score,'passed_tests':doc.passed_tests,'total_tests':doc.total_tests,'memory_kb':doc.memory_kb,'time_ms':doc.time_ms,'status_version':doc.status_version,'event_id':doc.event_id,'judge_request_id':doc.judge_request_id}
  print(json.dumps(result),flush=True)
  assert doc.status=='Passed' and doc.score==100 and doc.passed_tests==doc.total_tests==13,result
  assert doc.status_version and doc.event_id, 'Missing callback receipt'
  visible=get_programming_submission_status(doc.name);frappe.db.commit()
  assert visible['status']=='Passed',visible
  results.append(result)
 print('E2E_PASSED',json.dumps(results),flush=True)
finally:
 frappe.db.rollback()
 for name in created:
  frappe.delete_doc('LMS Programming Exercise Submission',name,ignore_permissions=True)
 frappe.db.commit();frappe.destroy()
