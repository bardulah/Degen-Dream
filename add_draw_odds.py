with open('web/templates/dashboard.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Add draw odds to JavaScript handler (after line 618 which is index 617)
lines.insert(619, "            document.getElementById('drawOdds').innerText = game.draw_odds || '---';\r\n")

# Find the game header and add draw odds display
for i, line in enumerate(lines):
    if '<div class="vs-divider">VS</div>' in line:
        # Replace VS divider with draw odds display
        lines[i] = line.replace(
            '<div class="vs-divider">VS</div>',
            '''<div class="vs-divider">
                    <div style="text-align: center;">
                        <span style="display: block; font-size: 9px; color: #666;">DRAW</span>
                        <span id="drawOdds" style="color: var(--text-primary); font-weight: bold;">---</span>
                    </div>
                </div>'''
        )
        break

with open('web/templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Draw odds added successfully!")
