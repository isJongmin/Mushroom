"""2D 리그: 13프레임 포즈 -> 관절 위치. 단위는 '로컬 단위'(출력 px = 단위 x SCALE), 원점 = 기준점(발 중앙 바닥), y 아래 +.

각도 규칙: 팔/다리 각도 a는 '아래로 곧게'가 0, 진행 방향(+x, 오른쪽)으로 들수록 +. 방향 = (sin a, cos a).
몸통/머리 각도는 화면 시계방향 +(오른쪽으로 숙임).
"""
import math
import numpy as np
from raster import Xf, fig as _fig, paint as _paint, stroke as _stroke, Layer, AX, AY, rgb

SCALE = 1.15
HEAD_SX, HEAD_SY = 0.58, 0.62   # 머리(머리카락, 모자 포함) 배율: 머리 로컬 60x54.5 -> 약 36x36 단위 (약 4.2등신)
UA, FA = 17.5, 15.5        # 위팔, 아래팔
TH, SH, ANK = 29.5, 28.5, 4.2   # 허벅지, 정강이, 발목 높이
HIP_Y = -(TH + SH + ANK)
SHOE_K = 1.36              # 신발 배율 (shoes.py 와 같음)
TSX, TSY = 1.12, 1.30      # 몸통 로컬 -> 단위 배율 (옷 좌표는 몸통 로컬 25 높이 기준으로 쓴다)
NECK_Y = -30.5             # 몸통 로컬: 머리 원점(턱 밑). 어깨(-23)보다 위 = 목

FRAMES = ['front', 'front_b', 'side', 'walk0', 'walk1', 'walk2', 'walk3', 'back', 'jump', 'fall', 'prone',
          'attack0', 'attack1']

# 관절 로컬 위치 (보기별)
SHOULDER = {'front': ((-10.6, -22.6), (10.6, -22.6)), 'back': ((-10.6, -22.6), (10.6, -22.6)),
            'q': ((-3.0, -22.6), (6.0, -23.0))}
HIPJ = {'front': ((-5.0, -0.5), (5.0, -0.5)), 'back': ((-5.0, -0.5), (5.0, -0.5)),
        'q': ((-1.5, -0.5), (3.5, -1.0))}
NECK = {'front': (0.0, NECK_Y), 'back': (0.0, NECK_Y), 'q': (1.5, NECK_Y)}


def P(view='q', hip=None, torso=0.0, head=0.0, armN=(0, 0), armF=(0, 0), legN=(0, 0, 0), legF=(0, 0, 0),
      ground=True, sway=0.0, lift=0.0, blink=False, breathe=0.0, prone=False, head_off=(0, 0), head_sq=1.0):
    return dict(view=view, hip=hip, torso=torso, head=head, armN=armN, armF=armF, legN=legN, legF=legF,
                ground=ground, sway=sway, lift=lift, breathe=breathe, prone=prone, head_off=head_off, head_sq=head_sq)


POSES = {
    'front': P('front', armN=(7, -6), armF=(7, -6), legN=(-2, 0, 0), legF=(2, 0, 0)),
    'front_b': P('front', hip=(0, HIP_Y + 0.7), armN=(10, -8), armF=(10, -8), legN=(-2, 0, 0), legF=(2, 0, 0),
                 head=0, breathe=1.0, sway=0.3),
    'side': P('q', torso=2, head=-2, armN=(-8, 10), armF=(10, 14), legN=(-5, 0, 0), legF=(6, -2, 0)),
    'walk0': P('q', torso=3, head=-1, armN=(-22, 12), armF=(20, 18), legN=(17, -5, -12), legF=(-15, -14, 14),
               sway=-0.6),
    'walk1': P('q', torso=2, head=-2, armN=(-6, 10), armF=(6, 14), legN=(2, -2, 0), legF=(12, -40, 16), sway=-1.0),
    'walk2': P('q', torso=3, head=-1, armN=(20, 18), armF=(-22, 12), legN=(-15, -14, 14), legF=(17, -5, -12),
               sway=-0.6),
    'walk3': P('q', torso=2, head=-2, armN=(6, 14), armF=(-6, 10), legN=(12, -40, 16), legF=(2, -2, 0), sway=-1.0),
    'back': P('back', armN=(7, -6), armF=(7, -6), legN=(-2, 0, 0), legF=(2, 0, 0)),
    'jump': P('q', hip=(0, HIP_Y - 2), torso=-3, head=-5, armN=(58, -20), armF=(150, -20), legN=(62, -100, 15),
              legF=(-6, -38, 22), ground=False, sway=1.6, lift=1.0),
    'fall': P('q', hip=(0, HIP_Y - 1), torso=3, head=4, armN=(-48, -24), armF=(56, 26), legN=(16, -10, 10),
              legF=(-16, -16, 22), ground=False, sway=-1.8, lift=-1.0),
    'prone': P('q', hip=(-16.0, -9.6), torso=90, head=-92, armN=(66, 104), armF=(168, 24), head_off=(4.0, 9.5),
               head_sq=0.9,
               legN=(-86, -128, 0), legF=(-82, -108, 0), ground=False, sway=0.4, prone=True),
    'attack0': P('q', torso=-7, head=-5, armN=(-104, -28), armF=(36, 34), legN=(-12, -4, 0), legF=(16, -10, -6),
                 sway=0.8),
    'attack1': P('q', torso=10, head=4, armN=(80, 8), armF=(-34, 18), legN=(-18, -6, 4), legF=(22, -20, -8),
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
        Tt0 = Xf.T(*hip) @ Xf.R(self.torso_a) @ Xf.S(TSX, TSY)
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
            low = -1e9
            for L in legs.values():
                r = -L['sa'] * 0.35 + L['f']
                for fx in (-6.4 * SHOE_K, 11.0 * SHOE_K):
                    q = Xf.R(r)(np.array([fx, ANK]))
                    low = max(low, L['ank'][1] + q[1])
            dy = -low
            for L in legs.values():
                for key in ('hip', 'knee', 'ank'):
                    L[key] = L[key] + (0, dy)
            hip = hip + (0, dy)
        self.hip = hip
        self.Tr = Xf.T(*hip) @ Xf.R(self.torso_a)
        self.Tt = self.Tr @ Xf.S(TSX, TSY)
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
        self.Th = Xf.T(*p['head_off']) @ self.Tr @ Xf.T(neck[0] * TSX, (neck[1] + self.breathe * 0.6) * TSY) \
            @ Xf.R(p['head']) @ Xf.S(HEAD_SX, HEAD_SY * p['head_sq'])
        if self.prone and not getattr(self, '_fitted', False):
            # 엎드리기: 화면 최저점(턱, 팔꿈치, 손, 몸통)을 기준선에 맞춘다
            from body import head_poly, torso_poly
            lows = [self.Th(head_poly('q'))[:, 1].max(), self.Tt(torso_poly('q'))[:, 1].max()]
            for a in arms.values():
                lows += [a['el'][1] + 2.9, a['wr'][1] + a['d2'][1] * 2.6 + 3.6]
            dy = -max(lows)
            xs = [self.Th(head_poly('q'))[:, 0].max() + 3.0, self.Tt(torso_poly('q'))[:, 0].min()]
            for g in legs.values():
                xs += [g['knee'][0] - 6.0, g['ank'][0] - 8.0, g['ank'][0] + 8.0]
            dx = -(max(xs) + min(xs)) / 2
            self._fitted = True
            self.p = dict(p, hip=(hip[0] + dx, hip[1] + dy))
            self._solve()

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
