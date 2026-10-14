"""버섯마을 픽셀 팔레트 (docs/design/style-guide.md 1.1절, 42색 정본) + 블록 재질 램프.

블록 스타일 규칙: 상자의 면마다 톤이 정해진다.
  윗면(top) = 밝게, 정면(front) = 기본, 옆면(side, 오른쪽) = 어둡게.
재질 램프(Mat)는 밝은 쪽 -> 어두운 쪽 색 토큰 리스트이고 (top, front, side) 인덱스를 가진다.
텍스처의 delta(-1 밝게 / +1 어둡게)는 이 인덱스를 옮긴다 (결, 주름, 깊이 경계 그늘, 먼 쪽 팔다리).
"""

PAL = {
    'ink': '#1A1626', 'hb1': '#4A4560', 'hb2': '#2E2A3E',
    'w1': '#E0A868', 'w2': '#B97A4A', 'w3': '#8A5232', 'w4': '#5E3620',
    's1': '#FFE3CC', 's2': '#F5C29A', 's3': '#D99464',
    'white': '#FFFFFF',
    'y1': '#FFF2A8', 'y2': '#F7C948', 'y3': '#F08A2E', 'y4': '#A84A1E',
    'p1': '#FFC8DC', 'p2': '#F58AB4', 'p3': '#B04A78',
    'r1': '#FF8E7A', 'r2': '#E8483E', 'r3': '#9E2838',
    'u1': '#9CC8FF', 'u2': '#4D7CFE', 'u3': '#2E3E9E', 'u4': '#232A5E',
    'g1': '#B6E86A', 'g2': '#6CC443', 'g3': '#3E8A2E', 'g4': '#23562A',
    'c1': '#FFF6E4', 'c2': '#F2DDB8', 'c3': '#C9A47A',
    'm1': '#BFF0DC', 'm2': '#7ED6B4', 'm3': '#3E9A86',
    'k1': '#6EC6F5', 'k2': '#86D2F8', 'k3': '#A0DDFA', 'k4': '#BBE8FC', 'k5': '#D8F3FE',
    'st1': '#C8C4D0', 'st2': '#8E88A0',
}
assert len(PAL) == 42


def rgba(name):
    h = PAL[name]
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), 255)


HEX2TOK = {v: k for k, v in PAL.items()}

# 고정색(재질 없는 픽셀)을 한 톤 어둡게 할 때 (옆모습 먼 쪽 팔다리)
DARKER = {
    'white': 'c2', 'c1': 'c2', 'c2': 'c3', 'c3': 'w3', 'ink': 'ink', 'hb1': 'hb2', 'hb2': 'ink',
    'w1': 'w2', 'w2': 'w3', 'w3': 'w4', 'w4': 'ink', 's1': 's2', 's2': 's3', 's3': 'w3',
    'y1': 'y2', 'y2': 'y3', 'y3': 'y4', 'y4': 'w4', 'p1': 'p2', 'p2': 'p3', 'p3': 'hb2',
    'r1': 'r2', 'r2': 'r3', 'r3': 'hb2', 'u1': 'u2', 'u2': 'u3', 'u3': 'u4', 'u4': 'ink',
    'g1': 'g2', 'g2': 'g3', 'g3': 'g4', 'g4': 'ink', 'm1': 'm2', 'm2': 'm3', 'm3': 'g4',
    'k1': 'u2', 'k2': 'k1', 'k3': 'k2', 'k4': 'k3', 'k5': 'k4', 'st1': 'st2', 'st2': 'hb1',
}

# 합성 실루엣 외곽선: 팔레트 색 -> line 색 (assets/avatar/outline.json 의 원본)
LINE = {
    'ink': 'ink', 'hb1': 'ink', 'hb2': 'ink',
    'w1': 'w4', 'w2': 'w4', 'w3': 'w4', 'w4': 'ink',
    's1': 'w2', 's2': 'w3', 's3': 'w3',
    'white': 'c3', 'c1': 'c3', 'c2': 'c3', 'c3': 'w3',
    'y1': 'y4', 'y2': 'y4', 'y3': 'y4', 'y4': 'w4',
    'p1': 'p3', 'p2': 'p3', 'p3': 'hb2',
    'r1': 'r3', 'r2': 'r3', 'r3': 'hb2',
    'u1': 'u3', 'u2': 'u3', 'u3': 'u4', 'u4': 'ink',
    'g1': 'g4', 'g2': 'g4', 'g3': 'g4', 'g4': 'ink',
    'm1': 'm3', 'm2': 'm3', 'm3': 'g4',
    'k1': 'u3', 'k2': 'u3', 'k3': 'u3', 'k4': 'u3', 'k5': 'u3',
    'st1': 'hb1', 'st2': 'hb1',
}


class Mat:
    """ramp: 밝음->어두움 색 토큰. t/f/s: 윗면/정면/옆면 인덱스."""
    def __init__(self, ramp, t, f, s):
        self.ramp, self.t, self.f, self.s = ramp, t, f, s

    def color(self, tone, delta=0):
        i = {'top': self.t, 'front': self.f, 'side': self.s}[tone] + delta
        i = max(0, min(len(self.ramp) - 1, i))
        return self.ramp[i]


MATS = {
    # 피부 (style-guide 1.2: light s1/s2, medium s2/s3, dark w2/w3)
    'skin_light':  Mat(['s1', 's1', 's2', 's3'], 0, 1, 2),
    'skin_medium': Mat(['s2', 's2', 's3', 'w3'], 0, 1, 2),
    'skin_dark':   Mat(['w2', 'w2', 'w3', 'w4'], 0, 1, 2),
    # 머리카락 (윗면 hl, 정면 base, 옆면 shade)
    'hair_black':  Mat(['st2', 'hb1', 'hb2', 'ink'], 1, 2, 3),
    'hair_brown':  Mat(['w1', 'w2', 'w3', 'w4'], 1, 2, 3),      # 밤색
    'hair_tan':    Mat(['w2', 'y4', 'w4', 'ink'], 0, 1, 2),        # 갈색(적갈색) - 모든 피부/밤색 머리와 구분
    'hair_blonde': Mat(['white', 'y1', 'y2', 'y3', 'y4'], 1, 2, 3),
    'hair_pink':   Mat(['white', 'p1', 'p2', 'p3'], 1, 2, 3),
    'hair_sky':    Mat(['white', 'k4', 'k2', 'k1', 'u2'], 1, 2, 3),
    'hair_mint':   Mat(['white', 'm1', 'm2', 'm3', 'g4'], 1, 2, 3),
    # 원단
    'cloth_black': Mat(['st2', 'hb1', 'hb2', 'ink'], 0, 1, 2),   # 검은 후드: 흑발(hb2 정면)보다 한 톤 밝게
    'cloth_white': Mat(['white', 'white', 'c1', 'c2', 'c3'], 0, 2, 3),
    'cloth_cream': Mat(['white', 'c1', 'c2', 'c3'], 0, 1, 2),
    'cloth_navy':  Mat(['u3', 'u4', 'ink'], 0, 1, 2),
    'cloth_dark':  Mat(['hb1', 'hb2', 'ink'], 0, 1, 2),          # 검은 바지
    'cloth_pink':  Mat(['white', 'p1', 'p2', 'p3'], 1, 2, 3),
    'cloth_green': Mat(['g1', 'g2', 'g3', 'g4'], 0, 1, 2),
    'cloth_red':   Mat(['r1', 'r2', 'r3'], 0, 1, 2),
    'cloth_blue':  Mat(['u1', 'u2', 'u3', 'u4'], 0, 1, 2),
    'cloth_jean':  Mat(['u1', 'u2', 'u3', 'u4'], 0, 1, 2),
    'cloth_brown': Mat(['w1', 'w2', 'w3', 'w4'], 0, 1, 2),
    'cloth_tan':   Mat(['w3', 'w4', 'ink'], 0, 1, 2),               # 갈색 반바지 (모든 피부와 구분되는 짙은 갈색)
    'cloth_yellow': Mat(['y1', 'y2', 'y3', 'y4'], 0, 1, 2),
    'cloth_deep':  Mat(['u2', 'u3', 'u4', 'ink'], 0, 1, 2),       # 망토 (짙은 파랑)
    'gold':        Mat(['y1', 'y2', 'y3', 'y4'], 0, 1, 2),
    'shoe_white':  Mat(['white', 'c1', 'c2', 'c3'], 0, 1, 2),
    'shoe_red':    Mat(['r1', 'r2', 'r3'], 0, 1, 2),
    'shoe_brown':  Mat(['w2', 'w3', 'w4', 'ink'], 0, 1, 2),
    'shoe_black':  Mat(['hb1', 'hb2', 'ink'], 0, 1, 2),
    # 버섯
    'cap_red':    Mat(['r1', 'r2', 'r3'], 0, 1, 2),
    'cap_orange': Mat(['y2', 'y3', 'y4'], 0, 1, 2),
    'cap_blue':   Mat(['u1', 'u2', 'u3'], 0, 1, 2),
    'cap_purple': Mat(['p2', 'p3', 'hb1', 'hb2'], 0, 1, 2),
    'dot':        Mat(['white', 'c1', 'c2'], 0, 0, 1),
    'stem':       Mat(['white', 'c1', 'c2', 'c3'], 1, 1, 2),
    # 지형/소품
    'wood':       Mat(['w1', 'w2', 'w3', 'w4'], 0, 1, 2),
    'plank':      Mat(['w1', 'w2', 'w3', 'w4'], 0, 1, 2),
    'leaf':       Mat(['g1', 'g2', 'g3', 'g4'], 0, 1, 2),
    'pine':       Mat(['g2', 'g3', 'g4', 'ink'], 0, 1, 2),
    'stone':      Mat(['st1', 'st2', 'hb1', 'hb2'], 0, 1, 2),
    'dark':       Mat(['hb1', 'hb2', 'ink'], 0, 1, 2),
    'glass':      Mat(['white', 'y1', 'y2'], 1, 1, 2),
    'water':      Mat(['k3', 'k1', 'u2', 'u3'], 0, 1, 2),
    'cloud':      Mat(['white', 'white', 'k5', 'k4'], 0, 1, 2),
    'far':        Mat(['white', 'm1', 'k5', 'k4'], 0, 1, 2),
    'midleaf':    Mat(['m1', 'm2', 'm3', 'g4'], 0, 1, 2),
    'midwood':    Mat(['m2', 'm3', 'g4'], 0, 1, 2),
    'grass':      Mat(['g1', 'g2', 'g3', 'g4'], 0, 1, 2),
}

for _m in MATS.values():
    for _c in _m.ramp:
        assert _c in PAL, _c
for _k, _v in list(DARKER.items()) + list(LINE.items()):
    assert _k in PAL and _v in PAL
