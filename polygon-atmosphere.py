"""Build the local, resolution-independent crimson crystal atmosphere.

The SVGs use declarative SMIL animation because Feishin 1.17.0's custom-CSS
sanitizer drops CSS @keyframes openings. No scripts, fetches or assets needed.
Run this file to regenerate polygon-atmosphere.css; do not edit the CSS by hand.
"""

from math import cos, sin, sqrt, pi
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
PHI = (1 + sqrt(5)) / 2
VERTICES = [
    (-1, PHI, 0), (1, PHI, 0), (-1, -PHI, 0), (1, -PHI, 0),
    (0, -1, PHI), (0, 1, PHI), (0, -1, -PHI), (0, 1, -PHI),
    (PHI, 0, -1), (PHI, 0, 1), (-PHI, 0, -1), (-PHI, 0, 1),
]
FACES = [
    (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
    (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
    (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
    (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1),
]


def unit(v):
    length = sqrt(sum(a * a for a in v))
    return tuple(a / length for a in v)


def normal(a, b, c):
    u = tuple(b[i] - a[i] for i in range(3))
    v = tuple(c[i] - a[i] for i in range(3))
    return unit((u[1] * v[2] - u[2] * v[1],
                 u[2] * v[0] - u[0] * v[2],
                 u[0] * v[1] - u[1] * v[0]))


def rotate(p, angles):
    x, y, z = p
    a, b, c = [v * pi / 180 for v in angles]
    y, z = y * cos(a) - z * sin(a), y * sin(a) + z * cos(a)
    x, z = x * cos(b) + z * sin(b), -x * sin(b) + z * cos(b)
    x, y = x * cos(c) - y * sin(c), x * sin(c) + y * cos(c)
    return x, y, z


def rgb(red, scale):
    # Crimson lacquer, with almost-black facets on the unlit side.
    if red:
        return '#%02x%02x%02x' % (round(16 + 211 * scale),
                                 round(4 + 28 * scale),
                                 round(10 + 42 * scale))
    return '#%02x%02x%02x' % (round(8 + 76 * scale),
                             round(8 + 16 * scale),
                             round(11 + 23 * scale))


def crystal(index, *, x, y, size, angles, red, opacity, animated, travel, period):
    # Perspective-projected irregular icosahedra: elongated, solid forms with
    # correctly ordered faces and directional lighting, rather than flat icons.
    points = [rotate((vx * 0.72, vy * 1.28, vz * 0.68), angles)
              for vx, vy, vz in VERTICES]
    light = unit((-0.6, -0.8, 1.0))
    view = unit((-0.15, -0.22, 1.0))
    visible = []
    for face in FACES:
        triangle = [points[i] for i in face]
        n = normal(*triangle)
        if n[2] <= 0:
            continue
        intensity = max(0, sum(n[i] * light[i] for i in range(3)))
        sheen = max(0, sum(n[i] * view[i] for i in range(3))) ** 14
        visible.append((sum(v[2] for v in triangle), triangle, intensity, sheen))
    definitions, surfaces, seams = [], [], []
    for f, (_, triangle, intensity, sheen) in enumerate(sorted(visible)):
        name = f'face-{index}-{f}'
        points_2d = [(px * size / (1 - pz / 11), py * size / (1 - pz / 11))
                     for px, py, pz in triangle]
        point_string = ' '.join(f'{px:.2f},{py:.2f}' for px, py in points_2d)
        bright = min(1, 0.06 + intensity * 0.83 + sheen * 0.11)
        definitions.append(
            f'<linearGradient id="{name}" x1="0" y1="0" x2="0.85" y2="1">'
            f'<stop stop-color="{rgb(red, bright)}"/>'
            f'<stop offset=".52" stop-color="{rgb(red, bright * .72)}"/>'
            f'<stop offset="1" stop-color="{rgb(red, bright * .36)}"/>'
            '</linearGradient>')
        surfaces.append(f'<polygon points="{point_string}" fill="url(#{name})" '
                        f'stroke="{rgb(red, bright * .6)}" stroke-width=".65" '
                        'stroke-linejoin="round"/>')
        # Restrained edge light makes the object feel dimensional at small size.
        if intensity > .45:
            strength = .08 + intensity * (.25 if red else .16)
            seams.append(f'<polyline points="{point_string}" fill="none" '
                         f'stroke="#ff6871" stroke-opacity="{strength:.2f}" '
                         'stroke-width=".65" stroke-linejoin="round"/>')
    drift = rotation = ''
    if animated:
        dx, dy = travel
        drift = (f'<animateTransform attributeName="transform" type="translate" '
                 f'values="0 0;{dx} {dy};0 0" dur="{period}s" '
                 'calcMode="spline" keyTimes="0;.5;1" '
                 'keySplines=".42 0 .58 1;.42 0 .58 1" repeatCount="indefinite"/>')
        rotation = (f'<animateTransform attributeName="transform" type="rotate" '
                    f'values="-2;3;-2" dur="{period + 8}s" '
                    'calcMode="spline" keyTimes="0;.5;1" '
                    'keySplines=".42 0 .58 1;.42 0 .58 1" repeatCount="indefinite"/>')
    return ''.join(definitions), (
        f'<g transform="translate({x} {y})" opacity="{opacity}">'
        f'<g>{drift}<g>{rotation}{"".join(surfaces)}{"".join(seams)}</g></g></g>')


def atmosphere(mobile=False, animated=True):
    width, height = (430, 932) if mobile else (1600, 1000)
    # x, y, size, Euler rotation, red material, opacity, drift, duration.
    shapes = [
        (-55, 200, 93, (24, 36, -36), False, .82, (12, -16), 37),
        (520, -32, 102, (12, 52, 56), True, .68, (-13, 18), 31),
        (1465, 185, 106, (24, -32, 24), True, .74, (-19, 13), 33),
        (1615, 615, 125, (41, 12, -36), False, .9, (-16, -21), 43),
        (1265, 1015, 116, (-28, 42, 64), True, .65, (15, -23), 39),
        (615, 1030, 83, (-19, 28, -22), False, .82, (10, -16), 35),
        (282, 661, 42, (31, 48, 38), True, .42, (-9, -19), 29),
    ] if not mobile else [
        (126, -46, 57, (12, 52, 56), True, .60, (8, 12), 31),
        (446, 176, 67, (24, -32, 24), True, .65, (-9, 9), 33),
        (-36, 465, 75, (41, 12, -36), False, .94, (9, -13), 43),
        (420, 850, 82, (-28, 42, 64), True, .60, (-10, -14), 39),
        (44, 954, 58, (-19, 28, -22), False, .84, (6, -10), 35),
    ]
    defs, fragments = [], []
    for index, (x, y, size, angles, red, opacity, travel, period) in enumerate(shapes):
        definition, fragment = crystal(index, x=x, y=y, size=size, angles=angles,
                                       red=red, opacity=opacity, animated=animated,
                                       travel=travel, period=period)
        defs.append(definition)
        fragments.append(fragment)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid slice">'
            f'<defs>{"".join(defs)}</defs>{"".join(fragments)}</svg>')


def image_value(mobile, animated):
    # URL-escape all markup; CSS sanitization permits data URLs and nothing here
    # contains executable SVG, external references, text, or embedded scripts.
    return 'url("data:image/svg+xml,' + quote(atmosphere(mobile, animated), safe='') + '")'


def hero_image(animated=True):
    """A deliberately bolder, close-up composition for the home masthead.

    Keep the first 460 logical pixels empty for the heading and actions. The
    large wine-black form crops at the right edge, framing the hero red crystal.
    """
    shapes = [
        (1080, 175, 106, (41, 12, -36), False, 1, (-9, -12), 43),
        (827, 143, 82, (15, -38, 28), True, 1, (7, 9), 35),
        (592, 238, 40, (31, 48, 38), True, .95, (-5, -11), 29),
    ]
    definitions, fragments = [], []
    for index, (x, y, size, angles, red, opacity, travel, period) in enumerate(shapes):
        definition, fragment = crystal(f'hero-{index}', x=x, y=y, size=size,
                                       angles=angles, red=red, opacity=opacity,
                                       animated=animated, travel=travel, period=period)
        definitions.append(definition)
        fragments.append(fragment)
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="300" '
           'viewBox="0 0 1100 300" preserveAspectRatio="xMidYMid slice">'
           f'<defs>{"".join(definitions)}</defs>{"".join(fragments)}</svg>')
    return 'url("data:image/svg+xml,' + quote(svg, safe='') + '")'


def main():
    desktop = image_value(False, True)
    phone = image_value(True, True)
    still_desktop = image_value(False, False)
    still_phone = image_value(True, False)
    hero = hero_image(True)
    still_hero = hero_image(False)
    css = f'''/* Generated by polygon-atmosphere.py. Local faceted geometry; no external assets.
   Specificity is intentional: Feishin's CSS sanitizer reverses rule ordering. */
:root:root {{ --snow-crystal-hero-image: {hero}; }}
html body {{ isolation: isolate; }}
html body::before {{
  content: "";
  position: fixed;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background-image: {desktop};
  background-position: center;
  background-size: cover;
  background-repeat: no-repeat;
}}
@media (max-width: 700px) {{
  html:root body::before {{
    background-image: {phone};
  }}
}}
@media (prefers-reduced-motion: reduce) {{
  :root:root:root {{ --snow-crystal-hero-image: {still_hero}; }}
  html:root:root body::before {{
    background-image: {still_desktop};
  }}
}}
@media (prefers-reduced-motion: reduce) and (max-width: 700px) {{
  html:root:root:root body::before {{
    background-image: {still_phone};
  }}
}}
'''
    path = ROOT / 'polygon-atmosphere.css'
    path.write_text(css, encoding='utf-8')
    print(f'Wrote {path.name}: {len(css):,} bytes; desktop/mobile, animated/reduced-motion.')


if __name__ == '__main__':
    main()
