"""버섯마을 픽셀 팔레트 (style-guide v2.0 1.1, 42색 정본). 새 색을 추가하지 않는다."""

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


def rgb(token):
    h = PAL[token].lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgba(token):
    return rgb(token) + (255,)


PAL_RGB = {rgb(k) for k in PAL}

# 재료별 램프 (style-guide 1.2): (hl, base, shade, line)
RAMP = {
    # 피부: hl 없음 -> base로 대체
    'skin-light': ('s1', 's1', 's2', 'w2'),
    'skin-tan': ('s2', 's2', 's3', 'w3'),
    'skin-dark': ('w2', 'w2', 'w3', 'w4'),
    # 머리
    'black': ('hb1', 'hb2', 'ink', 'ink'),
    'chestnut': ('w2', 'w3', 'w4', 'w4'),
    'blonde': ('y1', 'y2', 'y4', 'y4'),
    'pink': ('p1', 'p2', 'p3', 'p3'),
    'mint': ('m1', 'm2', 'm3', 'm3'),
    # 원단
    'red': ('r1', 'r2', 'r3', 'r3'),
    'blue': ('u1', 'u2', 'u3', 'u3'),
    'navy': ('u3', 'u4', 'ink', 'ink'),
    'fpink': ('p1', 'p2', 'p3', 'p3'),
    'green': ('g1', 'g2', 'g3', 'g4'),
    'cream': ('white', 'c1', 'c3', 'c3'),
    # 신발
    'shoe-brown': ('w2', 'w3', 'w4', 'w4'),
    'shoe-red': ('r1', 'r2', 'r3', 'r3'),
    # 버섯 갓
    'cap-red': ('r1', 'r2', 'r3', 'r3'),
    'cap-orange': ('y2', 'y3', 'y4', 'y4'),
    'cap-blue': ('u1', 'u2', 'u3', 'u3'),
}
