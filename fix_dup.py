f = '/opt/forgebase/app/admin/src/app/(dashboard)/dashboard/content-optimizer/page.tsx'
lines = open(f, encoding='utf-8').readlines()
# Find second occurrence of '"use client";'
marker = '"use client";\n'
start = 0
count = 0
for i, line in enumerate(lines):
    if line == marker:
        count += 1
        if count == 2:
            start = i
            break
if start > 0:
    clean = lines[start:]
    open(f, 'w', encoding='utf-8').writelines(clean)
    print(f'Kept lines {start+1}-{len(lines)}, new total: {len(clean)}')
else:
    print('Only one use client found - no action')