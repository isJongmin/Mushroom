"""v2 감성 팔레트 (사이클 9 재작업): 세이지, 올리브, 크림, 웜그레이, 테라코타, 더스티 블루.
원색 빨강, 노랑은 쓰지 않는다. 외곽선은 같은 색조의 어두운 톤이고 얇다.
"""
from vec import mix

M = {
    'grass': dict(hi='#D3DBA8', base='#A3B27A', shade='#82935F', deep='#66764B', line='#4C5A3A'),
    'moss': dict(hi='#C4CF94', base='#97A668', shade='#77874F', deep='#5D6C3F', line='#435032'),
    'soil': dict(hi='#C4A88C', base='#A88C70', shade='#8D735E', deep='#735E4E', line='#4C3F37'),
    'stone': dict(hi='#E6DDCF', base='#C4B8A6', shade='#A69A89', deep='#887D6F', line='#5F564C'),
    'wood': dict(hi='#D8BC98', base='#B69673', shade='#94765A', deep='#755C47', line='#523F31'),
    'darkwood': dict(hi='#A48B74', base='#836A57', shade='#685445', deep='#514137', line='#372C26'),
    'plaster': dict(hi='#FCF8EF', base='#F2EBDD', shade='#E0D5C2', deep='#C9BCA6', line='#8E7F6B'),
    'terracotta': dict(hi='#E3B096', base='#CC8466', shade='#B06C52', deep='#925843', line='#6B4032'),
    'sage': dict(hi='#CDD6BE', base='#AEBC9F', shade='#91A083', deep='#77876B', line='#58654F'),
    'olive': dict(hi='#B9BF8C', base='#949A62', shade='#777D4C', deep='#5E633C', line='#43472C'),
    'dustyblue': dict(hi='#C8D5E0', base='#97ADC1', shade='#7E95AA', deep='#677E93', line='#4A5D6F'),
    'cream': dict(hi='#FFFBF2', base='#F4EAD6', shade='#E2D3B8', deep='#CDBA9A', line='#8E7A5E'),
    'warmgray': dict(hi='#D8D0C6', base='#B4AA9E', shade='#978D82', deep='#7C736A', line='#59524B'),
    'rose': dict(hi='#F2E0D8', base='#DFC2B7', shade='#C8A498', deep='#AD887D', line='#80625A'),
    'leaf': dict(hi='#C3CB98', base='#96A26C', shade='#768352', deep='#5D6942', line='#454F33'),
    'leaf2': dict(hi='#ABB98C', base='#7D8E62', shade='#62724D', deep='#4C5A3E', line='#35422E'),
    'trunk': dict(hi='#A28B77', base='#806A5A', shade='#665446', deep='#4F4138', line='#382E28'),
    'metal': dict(hi='#8A8784', base='#64615E', shade='#4D4A48', deep='#3B3937', line='#2A2827'),
    'glow': dict(hi='#FFF6E2', base='#F8E2B8', shade='#EDC995', deep='#D9AE78', line='#7A5E44'),
    'glass': dict(hi='#E6EDF0', base='#A9BCC6', shade='#8DA2AE', deep='#738995', line='#4E5F69'),
}

HAZE = '#D9D6D0'


def tone(name, t=0.0, to=HAZE):
    m = M[name]
    return {k: mix(v, to, t) for k, v in m.items()} if t > 0 else dict(m)
