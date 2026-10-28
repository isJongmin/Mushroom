"""2D 리그: 13프레임 포즈 -> 관절 위치. 단위는 '로컬 단위'(출력 px = 단위 x SCALE), 원점 = 기준점(발 중앙 바닥), y 아래 +.

각도 규칙: 팔/다리 각도 a는 '아래로 곧게'가 0, 진행 방향(+x, 오른쪽)으로 들수록 +. 방향 = (sin a, cos a).
몸통/머리 각도는 화면 시계방향 +(오른쪽으로 숙임).
"""
import math
import numpy as np
from raster import Xf, fig as _fig, paint as _paint, stroke as _stroke, Layer, AX, AY, rgb

SCALE = 1.15
HEAD_K = 0.93               # 머리(머리카락, 모자 포함) 배율
UA, FA = 10.0, 9.0         # 위팔, 아래팔
TH, SH, ANK = 16.0, 15.0, 4.6   # 허벅지, 정강이, 발목 높이
HIP_Y = -(TH + SH + ANK)
TORSO = 25.0               # 엉덩이 -> 어깨
NECK_Y = -27.0             # 몸통 로컬: 머리 원점(턱 밑)

FRAMES = ['front', 'front_b', 'side', 'walk0', 'walk1', 'walk2', 'walk3', 'back', 'jump', 'fall', 'prone',
          'attack0', 'attack1']

# 관절 로컬 위치 (보기별)
SHOULDER = {'front': ((-11.5, -23.0), (11.5, -23.0)), 'back': ((-11.5, -23.0), (11.5, -23.0)),
            'q': ((-3.5, -23.0), (6.5, -23.5))}
HIPJ = {'front': ((-5.4, -1.0), (5.4, -1.0)), 'back': ((-5.4, -1.0), (5.4, -1.0)),
        'q': ((-2.0, -1.0), (4.0, -1.5))}
NECK = {'front': (0.0, NECK_Y), 'back': (0.0, NECK_Y), 'q': (1.5, NECK_Y)}


def P(view='q', hip=None, torso=0.0, head=0.0, armN=(0, 0), armF=(0, 0), legN=(0, 0, 0), legF=(0, 0, 0),
      ground=True, sway=0.0, lift=0.0, blink=False, breathe=0.0, prone=False):
    return dict(view=view, hip=hip, torso=torso, head=head, armN=armN, armF=armF, legN=legN, legF=legF,
                ground=ground, sway=sway, lift=lift, breathe=breathe, prone=prone)


POSES = {
    'front': P('front', armN=(7, -6), armF=(7, -6), legN=(-2, 0, 0), legF=(2, 0, 0)),
    'front_b': P('front', hip=(0, HIP_Y + 0.7), armN=(10, -8), armF=(10, -8), legN=(-2, 0, 0), legF=(2, 0, 0),
                 head=0, breathe=1.0, sway=0.3),
    'side': P('q', torso=2, head=-2, armN=(-8, 10), armF=(10, 14), legN=(-5, 0, 0), legF=(6, -2, 0)),
    'walk0': P('q', torso=4, head=-1, armN=(-30, 14), armF=(28, 22), legN=(25, -6, -14), legF=(-22, -16, 16),
               sway=-0.6),
    'walk1': P('q', torso=3, head=-2, armN=(-8, 10), armF=(8, 16), legN=(3, -2, 0), legF=(14, -50, 18), sway=-1.0),
    'walk2': P('q', torso=4, head=-1, armN=(26, 22), armF=(-28, 14), legN=(-22, -16, 16), legF=(25, -6, -14),
               sway=-0.6),
    'walk3': P('q', torso=3, head=-2, armN=(6, 16), armF=(-6, 10), legN=(14, -50, 18), legF=(3, -2, 0), sway=-1.0),
    'back': P('back', armN=(7, -6), armF=(7, -6), legN=(-2, 0, 0), legF=(2, 0, 0)),
    'jump': P('q', hip=(0, HIP_Y - 4), torso=-3, head=-5, armN=(150, -25), armF=(128, -10), legN=(62, -100, 15),
              legF=(-6, -38, 22), ground=False, sway=1.6, lift=1.0),
    'fall': P('q', hip=(0, HIP_Y - 1), torso=3, head=4, armN=(-62, -20), armF=(78, 20), legN=(16, -10, 10),
              legF=(-16, -16, 22), ground=False, sway=-1.8, lift=-1.0),
    'prone': P('q', hip=(-13.0, -9.6), torso=90, head=-80, armN=(176, -94), armF=(170, -100),
               legN=(-90, -72, 0), legF=(-86, -48, 0), ground=False, sway=0.4, prone=True),
    'attack0': P('q', torso=-8, head=-6, armN=(205, -30), armF=(40, 34), legN=(-16, -4, 0), legF=(22, -10, -6),
                 sway=0.8),
    'attack1': P('q', torso=13, head=6, armN=(78, 8), armF=(-38, 18), legN=(-24, -6, 4), legF=(28, -22, -8),
                 sway=-1.2),
}


def dir_(a):
    r = math.radians(a)
    return np.array([math.sin(r), math.cos(r)])


class Ctx:
    """한 프레임의 포즈 + 레이어 묶음. 파츠 함수는 로컬 단위 좌표를 넘긴다."""

    def __init__(self, fname, layers=None):
        self.fname = fname
        p = dict(POSES[fname])
        self.p = p
        self.view = p['view']
        self.q = self.view == 'q'
        self.front = self.view == 'front'
        self.back = self.view == 'back'
        self.prone = p['prone']
        self.sway = p['sway']
        self.lift = p['lift']
        self.breathe = p['breathe']
        self.root = Xf.T(AX, AY) @ Xf.S(SCALE)
        self.layers = layers if layers is not None else {}
        self._solve()

    # -------------------------------------------------------------- 뼈
    def _solve(self):
        p = self.p
        v = 'q' if self.q else self.view
        hip = np.array(p['hip'] if p['hip'] is not None else (0.0, HIP_Y), float)
        self.torso_a = p['torso']
        sh = SHOULDER[v]; hj = HIPJ[v]
        Tt0 = Xf.T(*hip) @ Xf.R(self.torso_a)
        # 다리 (절대 각도). 엉덩이 관절은 몸통과 함께 돈다
        legs = {}
        for k, (a, kb, f), hp in (('N', p['legN'], hj[0]), ('F', p['legF'], hj[1])):
            h = Tt0(np.array(hp, float))
            if self.front or self.back:
                a = a  # 정면: 바깥쪽 벌림은 x 부호로
            d1 = dir_(a)
            knee = h + d1 * TH
            sa = a + kb
            ank = knee + dir_(sa) * SH
            legs[k] = dict(hip=h, knee=knee, ank=ank, a=a, sa=sa, f=f)
        if p['ground']:
            low = max(legs['N']['ank'][1], legs['F']['ank'][1]) + ANK
            dy = -low
            for L in legs.values():
                for key in ('hip', 'knee', 'ank'):
                    L[key] = L[key] + (0, dy)
            hip = hip + (0, dy)
        self.hip = hip
        self.Tt = Xf.T(*hip) @ Xf.R(self.torso_a)
        self.legs = legs
        # 팔 (몸통 기준 상대 각도)
        arms = {}
        for k, (a, e), sp in (('N', p['armN'], sh[0]), ('F', p['armF'], sh[1])):
            s = self.Tt(np.array(sp, float) + (0, self.breathe * 0.6))
            if self.front or self.back:
                sg = -1 if k == 'N' else 1
                d1 = np.array([sg * math.sin(math.radians(a)), math.cos(math.radians(a))])
                d1 = Xf.R(self.torso_a).lin(d1)
                d2 = np.array([sg * math.sin(math.radians(a + e)), math.cos(math.radians(a + e))])
                d2 = Xf.R(self.torso_a).lin(d2)
            else:
                d1 = Xf.R(self.torso_a).lin(dir_(a))
                d2 = Xf.R(self.torso_a).lin(dir_(a + e))
            el = s + d1 * UA
            wr = el + d2 * FA
            arms[k] = dict(sh=s, el=el, wr=wr, a=a, e=e, d2=d2)
        self.arms = arms
        neck = NECK[v]
        self.Th = self.Tt @ Xf.T(neck[0], neck[1] + self.breathe * 0.8) @ Xf.R(p['head']) @ Xf.S(HEAD_K)

    # 보기 편의
    def side_sign(self, k):
        return -1 if k == 'N' else 1

    def limb_layer(self, base, k):
        """팔다리 레이어: 옆 보기의 먼 쪽은 *_far / top_far, 가까운 팔은 *_near."""
        return base

    # -------------------------------------------------------------- 그리기
    def L(self, name):
        if name not in self.layers:
            self.layers[name] = Layer()
        return self.layers[name]

    def _r(self, poly):
        return self.root(np.asarray(poly, float))

    def fig(self, layer, poly, col, shapes=(), **kw):
        sh = [(self._r(s[0]),) + tuple(s[1:]) for s in shapes if s is not None and s[0] is not None]
        _fig(self.L(layer), self._r(poly), col, shapes=sh, **kw)

    def paint(self, layer, poly, col, alpha=1.0):
        _paint(self.L(layer), self._r(poly), col, alpha)

    def stroke(self, layer, pts, col, w, alpha=1.0):
        _stroke(self.L(layer), self._r(pts), col, w * SCALE, alpha)
