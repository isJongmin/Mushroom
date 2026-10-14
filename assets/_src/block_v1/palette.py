"""버섯마을 픽셀 팔레트 (docs/design/style-guide.md 1.1절, 42색 정본) + 블록 재질 램프.

블록 스타일 규칙: 상자의 면마다 톤이 정해진다.
  윗면(top) = 밝게, 정면(front) = 기본, 옆면(side, 오른쪽) = 어둡게, line = 외곽선 버전에서만 사용.
재질 램프는 밝은 쪽 -> 어두운 쪽 순서의 색 리스트이고, (top, front, side) 인덱스를 가진다.
텍스처의 delta(-1 밝게 / +1 어둡게)는 이 인덱스를 옮긴다 (노이즈, 주머니 등 디테일).
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


def rgba(name):
    h = PAL[name]
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), 255)


class Mat:
    """ramp: 밝음->어두움 색 토큰. t/f/s: 윗면/정면/옆면 인덱스. line: 외곽선 색."""
    def __init__(self, ramp, t, f, s, line):
        self.ramp, self.t, self.f, self.s, self.line = ramp, t, f, s, line

    def color(self, tone, delta=0):
        i = {'top': self.t, 'front': self.f, 'side': self.s}[tone] + delta
        i = max(0, min(len(self.ramp) - 1, i))
        return self.ramp[i]


MATS = {
    # 피부: 윗면/정면 s1, 옆면 s2. delta +1 = s2/s3 (볼 그늘 등)
    'skin':      Mat(['s1', 's1', 's2', 's3'], 0, 1, 2, 'w2'),
    # 머리카락
    'hair_black': Mat(['st2', 'hb1', 'hb2', 'ink'], 1, 2, 3, 'ink'),
    'hair_pink':  Mat(['white', 'p1', 'p2', 'p3'], 1, 2, 3, 'p3'),
    'hair_brown': Mat(['w1', 'w2', 'w3', 'w4'], 1, 2, 3, 'w4'),
    'hair_blonde': Mat(['white', 'y1', 'y2', 'y3', 'y4'], 1, 2, 3, 'y4'),
    # 원단
    'cloth_black': Mat(['st2', 'hb1', 'hb2', 'ink'], 0, 1, 2, 'ink'),   # 검은 후드: 머리(hb2 정면)보다 한 톤 밝게
    'cloth_white': Mat(['white', 'white', 'c1', 'c2', 'c3'], 0, 2, 3, 'c3'),
    'cloth_navy':  Mat(['u3', 'u4', 'ink'], 0, 1, 2, 'ink'),
    'cloth_pink':  Mat(['white', 'p1', 'p2', 'p3'], 1, 2, 3, 'p3'),
    'cloth_green': Mat(['g1', 'g2', 'g3', 'g4'], 0, 1, 2, 'g4'),
    'cloth_dark':  Mat(['hb1', 'hb2', 'ink'], 0, 1, 2, 'ink'),          # 검은 바지
    'cloth_red':   Mat(['r1', 'r2', 'r3'], 0, 1, 2, 'r3'),
    'cloth_cream': Mat(['white', 'c1', 'c2', 'c3'], 0, 1, 2, 'c3'),
    'shoe_white':  Mat(['white', 'c1', 'c2', 'c3'], 0, 1, 2, 'c3'),
    'shoe_red':    Mat(['r1', 'r2', 'r3'], 0, 1, 2, 'r3'),
    'shoe_brown':  Mat(['w2', 'w3', 'w4'], 0, 1, 2, 'w4'),
    'gold':        Mat(['y1', 'y2', 'y3', 'y4'], 0, 1, 2, 'y4'),
    # 소품/지형
    'cap_red':   Mat(['r1', 'r2', 'r3'], 0, 1, 2, 'r3'),
    'dot':       Mat(['white', 'c1', 'c2'], 0, 0, 1, 'c2'),
    'stem':      Mat(['white', 'c1', 'c2', 'c3'], 1, 1, 2, 'c3'),
    'wood':      Mat(['w1', 'w2', 'w3', 'w4'], 0, 1, 2, 'w4'),
    'leaf':      Mat(['g1', 'g2', 'g3', 'g4'], 0, 1, 2, 'g4'),
    'stone':     Mat(['st1', 'st2', 'hb1'], 0, 1, 2, 'hb1'),
    'glass':     Mat(['white', 'y1', 'y2'], 1, 1, 2, 'y4'),
    'cloud':     Mat(['white', 'white', 'k5', 'k4'], 0, 1, 2, 'k4'),
}
