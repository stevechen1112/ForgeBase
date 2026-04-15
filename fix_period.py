import re
f = '/opt/forgebase/app/admin/src/app/(dashboard)/dashboard/content-optimizer/page.tsx'
c = open(f, 'rb').read()
new_block = b'const PERIOD_OPTIONS = [\n  { value: 7,  label: \"\xe8\xbf\x917 \xe5\xa4\xa9\" },\n  { value: 30, label: \"\xe8\xbf\x9130 \xe5\xa4\xa9\" },\n  { value: 90, label: \"\xe8\xbf\x9190 \xe5\xa4\xa9\" },\n];'
result = re.sub(rb'const PERIOD_OPTIONS = \[.*?\];', new_block, c, flags=re.DOTALL)
open(f, 'wb').write(result)
print('fixed', result.count(b'\n'), 'lines')
