"""유령, 비석, 드롭 반짝이, 공격 슬래시."""
import math
import os

import numpy as np
from PIL import Image

from vec import (Canvas, Mat, hx, mix, tone, ellipse, path, bez, star, rrect, xform, polar,
                 eye, blush, ground_shadow, twinkle, sparkle, WHITE)

TAU = 2 * math.pi

GHOST = dict(frame=(84, 99), anchor=(42, 96))
TOMB = dict(frame=(60, 72), anchor=(30, 69))
DROP = dict(frame=(72, 72), anchor=(36, 66))
SLASH = dict(frame=(150, 135), anchor=(24, 128))

MANIFEST = {
    'ghost': {
        'sheet': 'assets/mob/ghost.png', 'frame': {'w': GHOST['frame'][0], 'h': GHOST['frame'][1]},
        'anchor': {'x': GHOST['anchor'][0], 'y': GHOST['anchor'][1]}, 'size': {'w': 50, 'h': 60},
        'frames': 2, 'animations': {'idle': [0, 1]}, 'fps': 3,
        'note': '반투명이 PNG에 들어 있다(추가 alpha 불필요). 기준점 = 캐릭터 발 위치. 오른쪽 기본, 좌우 반전.',
    },
    'tombstone': {
        'sheet': 'assets/mob/tombstone.png', 'frame': {'w': TOMB['frame'][0], 'h': TOMB['frame'][1]},
        'anchor': {'x': TOMB['anchor'][0], 'y': TOMB['anchor'][1]}, 'size': {'w': 34, 'h': 44},
        'note': '기준점 = 바닥 중앙(땅에 꽂히는 선). 좌우 반전하지 않는다.',
    },
    'dropBag': {
        'sheet': 'assets/mob/drop_bag.png', 'frame': {'w': DROP['frame'][0], 'h': DROP['frame'][1]},
        'anchor': {'x': DROP['anchor'][0], 'y': DROP['anchor'][1]}, 'frames': 2, 'fps': 3,
        'note': '드롭 아이템 아래 깔리는 반짝이 받침. 아이콘(64x64)은 기준점 위 월드 약 6 높이에 32x32 월드로 얹는 것을 권장.',
    },
    'fx': {
        'slash': {
            'sheet': 'assets/fx/slash.png', 'frame': {'w': SLASH['frame'][0], 'h': SLASH['frame'][1]},
            'anchor': {'x': SLASH['anchor'][0], 'y': SLASH['anchor'][1]}, 'frames': 2, 'fps': 16,
            'note': '기준점 = 공격자 발 위치. 오른쪽 공격 기준, 왼쪽은 좌우 반전. 호가 판정 상자(앞 70 x 발 위 5~75)를 덮는다.',
        },
    },
}


# ------------------------------------------------------------------ 유령
G_MAT = Mat('#FFFFFF', sh='#DCE0F8', hl='#FFFFFF', line='#8C8FC4')


def ghost(c, f):
    bob = -3.0 * f
    w = 1.0 if f == 0 else -1.0  # 꼬리 흔들림
    sub = c.blank()
    sub.push(dy=bob - 6.0)
    # 몸: 둥근 머리 + 왼쪽 뒤로 말린 꼬리
    body = path((-17.0, -34.0), [((-17.0, -50.0), (-6.0, -58.0), (3.0, -58.0)),
                                  ((14.0, -58.0), (22.0, -49.0), (22.0, -36.0)),
                                  ((22.0, -22.0), (17.0, -12.0), (8.0, -8.0)),
                                  ((0.0, -4.0), (-8.0, -6.0 + w), (-14.0, -3.0 + w)),
                                  ((-19.0, -0.5 + w), (-24.0, -2.0 + w * 1.5), (-23.0, -6.5 + w * 1.5)),
                                  ((-21.5, -10.0), (-17.5, -9.0), (-16.5, -14.0)),
                                  ((-15.5, -20.0), (-17.0, -27.0), (-17.0, -34.0))], n=16)
    # 팔(작은 뭉툭)
    armB = ellipse(-15.5, -26.0, 4.0, 2.8, rot=0.6 + 0.1 * w)
    armF = ellipse(21.0, -27.0 - 1.0 * w, 4.4, 3.0, rot=-0.5)
    sub.part(armB, G_MAT, ol=1.6, shade=(-0.6, -0.8))
    m = sub.part(body, G_MAT, ol=1.9, shade=(-3.0, -3.0), shade_sc=0.97, ret=True,
                 hl=[ellipse(-7.0, -49.0, 5.0, 2.6, rot=-0.5)], hl_a=1.0)
    sub.part(armF, G_MAT, ol=1.6, shade=(-0.6, -0.8))
    # 얼굴: 동그란 눈
    ex, ey = 6.5, -37.0
    col = hx('#3A3560')
    for dx, r in ((0.0, 3.6), (9.0, 3.3)):
        sub.fill(ellipse(ex + dx, ey, r * 0.92, r), col)
        sub.fill(ellipse(ex + dx + r * 0.25, ey - r * 0.35, r * 0.42, r * 0.38), WHITE)
        sub.fill(ellipse(ex + dx - r * 0.3, ey + r * 0.38, r * 0.2, r * 0.18), WHITE)
    sub.fill(ellipse(ex + 4.6, ey + 6.5, 1.5, 1.9), col)  # 'o' 입
    blush(sub, ex - 3.0, ey + 5.0, 2.6, 1.3, a=0.45)
    blush(sub, ex + 12.0, ey + 5.0, 1.9, 1.2, a=0.45)
    sub.pop()
    c.over(sub, 0.80)
    # 반짝 입자
    twinkle(c, -22.0, -50.0 + bob * (1 if f else 0.5), 2.6 if f == 0 else 1.8, 0.8, '#E8ECFF')
    twinkle(c, 25.0, -16.0 + bob, 1.6 if f == 0 else 2.4, 0.7, '#E8ECFF')


# ------------------------------------------------------------------ 비석
T_STONE = Mat('#C6C0D2', sh='#9690AA', hl='#EEEAF6', line='#4A4460')
T_BASE = Mat('#ABA4BC', sh='#857E9C', hl='#D6D0E4', line='#423C58')
T_MOSS = Mat('#8CCB5A', sh='#5E9E3E', hl='#CBF08C', line='#2E5A26')
DIRT = Mat('#B98352', sh='#8E5C36', hl='#D9A878', line='#5A3620')


def tomb(c):
    ground_shadow(c, 18, 2.8, a=0.25)
    # 흙 둔덕
    mound = path((-19.0, 0.0), [((-16.0, -4.5), (16.0, -4.5), (19.0, 0.0)), ((8, 0.6), (-8, 0.6), (-19.0, 0.0))], n=12)
    c.part(mound, DIRT, ol=1.5, shade=(-1, -1.2))
    # 받침
    base = rrect(-16.0, -8.5, 16.0, -1.0, 2.0)
    c.part(base, T_BASE, ol=2.0, shade=(-1.6, -1.6), hl=[ellipse(-9, -7.0, 4.0, 0.9)])
    # 본체(둥근 머리 판)
    slab = path((-12.5, -7.0), [((-12.5, -20.0), (-12.5, -30.0), (-12.5, -32.0)),
                                ((-12.5, -42.0), (-6.0, -44.5), (0.0, -44.5)),
                                ((6.0, -44.5), (12.5, -42.0), (12.5, -32.0)),
                                ((12.5, -28.0), (12.5, -15.0), (12.5, -7.0)),
                                ((4.0, -7.0), (-4.0, -7.0), (-12.5, -7.0))], n=14)
    m = c.part(slab, T_STONE, ol=2.2, shade=(-2.8, -2.4), shade_sc=0.98, sh2=(-0.8, -0.6), ret=True,
               hl=[ellipse(-6.5, -38.5, 3.4, 1.8, rot=-0.6), ellipse(-9.0, -26.0, 0.9, 5.0)], hl_a=0.95)
    # 안쪽 테두리 홈
    inner = xform(slab, sx=0.78, sy=0.84, ox=0, oy=-22.0)
    c.line(inner, T_STONE.sh, 1.1, closed=True, clip=m)
    # 십자 새김(어두운 홈 + 아래 밝은 모서리)
    cross = [rrect(-1.9, -38.0, 1.9, -17.0, 0.8), rrect(-7.5, -32.5, 7.5, -28.8, 0.8)]
    for p in cross:
        c.fill(xform(p, 0.0, 0.7), T_STONE.hl, 1.0, clip=m)
    for p in cross:
        c.fill(p, tone(T_STONE.sh, 0.78, 1.1), 1.0, clip=m)
    # 'RIP' 대신 작은 점 세 개(장식)
    for x in (-4.0, 0.0, 4.0):
        c.fill(ellipse(x, -12.0, 0.9, 0.9), T_STONE.sh, 1.0, clip=m)
    # 금
    c.line(np.array([(9.5, -44.0 + 4), (7.5, -38.5), (9.0, -35.5)]), T_STONE.line, 1.0, clip=m, a=0.8)
    # 이끼(왼쪽 위 어깨, 받침 오른쪽)
    moss1 = path((-12.8, -27.0), [((-14.5, -36.0), (-9.0, -44.0), (-3.0, -44.6)),
                                  ((-4.0, -41.5), (-7.5, -41.0), (-8.0, -38.0)),
                                  ((-8.5, -35.5), (-11.0, -35.0), (-10.5, -31.5)),
                                  ((-10.3, -29.0), (-11.8, -28.0), (-12.8, -27.0))], n=10)
    c.part(moss1, T_MOSS, ol=1.3, shade=(-0.8, -1.0), hl=[ellipse(-9.5, -40.0, 2.5, 0.8, rot=-0.8)])
    moss2 = path((6.0, -8.6), [((8.0, -11.5), (14.0, -11.5), (16.3, -8.4)), ((13.0, -7.0), (9.0, -7.5), (6.0, -8.6))], n=10)
    c.part(moss2, T_MOSS, ol=1.2, shade=(-0.6, -0.6))
    # 풀 몇 가닥 + 작은 꽃
    for (x, h, lean) in ((-17.5, 5.0, -0.5), (-15.0, 6.5, 0.2), (15.5, 5.5, 0.4), (17.8, 4.0, 0.8)):
        blade = path((x - 1.0, -0.5), [((x - 0.5, -h * 0.5), (x + lean * 2, -h * 0.9), (x + lean * 3, -h)),
                                       ((x + 0.6, -h * 0.6), (x + 1.0, -h * 0.3), (x + 1.0, -0.5))], n=8)
        c.part(blade, T_MOSS, ol=0.9, shade=None)
    for k in range(5):
        a = -math.pi / 2 + TAU * k / 5
        c.part(ellipse(-15.2 + 1.5 * math.cos(a), -7.0 + 1.5 * math.sin(a), 1.2, 1.2, n=16), Mat('#FFFFFF', line='#C77A9A'), ol=0.6, shade=None)
    c.fill(ellipse(-15.2, -7.0, 0.9, 0.9), hx('#FFD34A'))


# ------------------------------------------------------------------ 드롭 반짝이
def drop_bag(c, f):
    sub = c.blank()
    for i, (rx, a) in enumerate(((19, 0.18), (15, 0.22), (11, 0.28), (7, 0.32))):
        sub.fill(ellipse(0, -2.0, rx, rx * 0.3), hx('#FFE58A'), a)
    # 위로 퍼지는 빛기둥
    for i, (x, h, wd) in enumerate(((-8.0, 18, 2.2), (0.0, 26, 3.0), (8.0, 16, 2.0))):
        hh = h * (1.0 if (i + f) % 2 == 0 else 0.78)
        beam = path((x - wd, -2.0), [((x - wd, -hh * 0.5), (x - wd * 0.4, -hh * 0.9), (x, -hh)),
                                     ((x + wd * 0.4, -hh * 0.9), (x + wd, -hh * 0.5), (x + wd, -2.0))], n=10)
        sub.fill(beam, hx('#FFF4C2'), 0.28)
    c.over(sub, 1.0)
    c.line(ellipse(0, -2.0, 15, 4.5, n=60), hx('#FFD34A'), 1.2, closed=True, a=0.65)
    if f == 0:
        twinkle(c, -12.0, -16.0, 3.6, 0.95)
        twinkle(c, 11.0, -24.0, 2.4, 0.85, '#FFF4C2')
        sparkle(c, 14.0, -8.0, 2.4, 0.9)
    else:
        twinkle(c, 12.5, -15.0, 3.8, 0.95)
        twinkle(c, -10.0, -26.0, 2.6, 0.85, '#FFF4C2')
        sparkle(c, -14.5, -7.0, 2.2, 0.9)


# ------------------------------------------------------------------ 슬래시
def _crescent(cx, cy, R, th, a0, a1, n=56, ex=1.25):
    """초승달 호. 두께는 진행 끝(a1) 쪽이 두껍고 시작 쪽이 가늘다. ex = 가로 늘림."""
    outer, inner = [], []
    for i in range(n + 1):
        u = i / n
        a = a0 + (a1 - a0) * u
        t = th * math.sin(math.pi * (u ** 0.6)) ** 0.9
        r2 = R - max(0.08, t)
        outer.append((cx + R * ex * math.cos(a), cy + R * math.sin(a)))
        inner.append((cx + r2 * ex * math.cos(a), cy + r2 * math.sin(a)))
    return np.array(outer + inner[::-1], np.float32)


def slash(c, f):
    cx, cy, R = 8.0, -42.0, 38.0
    if f == 0:
        a0, a1, th, al = -1.75, -0.15, 9.0, 0.95
    else:
        a0, a1, th, al = -1.35, 1.45, 12.0, 0.9
    sub = c.blank()
    sub.fill(_crescent(cx, cy, R + 2.5, th + 5.0, a0 - 0.05, a1 + 0.05), hx('#9EE6FF'), 0.35)
    sub.fill(_crescent(cx, cy, R, th, a0, a1), hx('#DDF8FF'), 0.95)
    sub.fill(_crescent(cx, cy, R - 1.2, th * 0.5, a0 + 0.12, a1 - 0.04), WHITE, 1.0)
    sub.line(_crescent(cx, cy, R, th, a0, a1), hx('#4AA6E0'), 1.2, closed=True, a=0.55)
    # 바깥쪽 속도선
    for da, dr in ((0.3, 5.0), (0.55, 8.0), (0.8, 5.5)):
        a = a0 + (a1 - a0) * da
        r1 = R + dr
        sub.line(np.array([(cx + r1 * 1.25 * math.cos(a - 0.25), cy + r1 * math.sin(a - 0.25)),
                           (cx + r1 * 1.25 * math.cos(a - 0.05), cy + r1 * math.sin(a - 0.05))]), hx('#BFF0FF'), 1.5, a=0.75)
    c.over(sub, al)
    tx, ty = cx + (R - 3) * 1.25 * math.cos(a1 - 0.08), cy + (R - 3) * math.sin(a1 - 0.08)
    twinkle(c, tx, ty, 5.5 if f == 0 else 4.0, 1.0)


# ------------------------------------------------------------------ 빌드
def _sheet(spec, n, fn):
    fw, fh = spec['frame']
    ax, ay = spec['anchor']
    out = Image.new('RGBA', (fw * n, fh), (0, 0, 0, 0))
    for i in range(n):
        c = Canvas(fw, fh, ax, ay)
        fn(c, i)
        out.paste(c.image(), (i * fw, 0))
    return out


def build(mob_dir, fx_dir):
    _sheet(GHOST, 2, ghost).save(os.path.join(mob_dir, 'ghost.png'), optimize=True)
    _sheet(TOMB, 1, lambda c, i: tomb(c)).save(os.path.join(mob_dir, 'tombstone.png'), optimize=True)
    _sheet(DROP, 2, drop_bag).save(os.path.join(mob_dir, 'drop_bag.png'), optimize=True)
    _sheet(SLASH, 2, slash).save(os.path.join(fx_dir, 'slash.png'), optimize=True)
