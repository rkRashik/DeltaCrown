import re

with open('templates/tournaments/detail.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

stack = []
for i, line in enumerate(lines, 1):
    # Only count {% if %} tags (not elif or else)
    if_match = re.search(r'{%\s*if\s', line)
    endif_match = re.search(r'{%\s*endif\s*%}', line)
    
    if if_match:
        stack.append(('if', i, line.strip()))
    if endif_match:
        if stack:
            stack.pop()
        else:
            print(f'Extra endif at line {i}')

print(f'Unclosed ifs ({len(stack)} total):')
for item in stack:
    print(f'Line {item[1]}: {item[2]}')
