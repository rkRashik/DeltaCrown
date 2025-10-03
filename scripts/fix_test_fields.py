with open('tests/test_tournament_capacity.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('title="', 'name="')

with open('tests/test_tournament_capacity.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed all 'title=' to 'name=' in test file")
