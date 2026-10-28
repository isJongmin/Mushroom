"""2D 맵 팔레트. 재질마다 (hi, base, shade, deep, line) 톤. 외곽선은 검정이 아니라 재질의 진한 톤."""
from vec import mix

M = {
    'grass': dict(hi='#C8F27A', base='#8ED957', shade='#5EB843', deep='#43993A', line='#2A6A2C'),
    'dirt': dict(hi='#E8B07A', base='#CF8F58', shade='#AD6D40', deep='#8C5334', line='#5A3220'),
    'stone': dict(hi='#F0ECF6', base='#CFC8DE', shade='#A9A1BF', deep='#8B83A3', line='#5C5574'),
    'wood': dict(hi='#F6CC90', base='#E2A866', shade='#BE7E48', deep='#97603A', line='#5E3620'),
    'darkwood': dict(hi='#C88A5A', base='#A46A42', shade='#81502F', deep='#653C22', line='#3E2414'),
    'rope': dict(hi='#FBE7B8', base='#E8C88E', shade='#C49C62', deep='#A07A48', line='#76522E'),
    'leaf': dict(hi='#B4EA6A', base='#78CF4E', shade='#4FAE3E', deep='#3A8F36', line='#215A28'),
    'leaf2': dict(hi='#A6E07E', base='#62BE5E', shade='#3E9C4C', deep='#2E7E42', line='#1B4E2E'),
    'cherry': dict(hi='#FFEAF3', base='#FFC4DE', shade='#F497C0', deep='#E07AA8', line='#A8487A'),
    'trunk': dict(hi='#C08458', base='#9E6642', shade='#7C4A2E', deep='#5E3620', line='#3E2214'),
    'stem': dict(hi='#FFFDF4', base='#FFF1D6', shade='#F0D3A8', deep='#DDB688', line='#94643E'),
    'cap_red': dict(hi='#FF9C88', base='#F2574B', shade='#CC3B3D', deep='#A82C38', line='#7A1A28'),
    'cap_orange': dict(hi='#FFC888', base='#FF9A42', shade='#E8752C', deep='#C65A20', line='#83360F'),
    'cap_blue': dict(hi='#A8D2FF', base='#62A6F2', shade='#4581D6', deep='#3466B8', line='#1D3A86'),
    'cap_yellow': dict(hi='#FFF0A0', base='#FFD24A', shade='#F2AE2E', deep='#D88E22', line='#8A5214'),
    'cap_purple': dict(hi='#E8C8FF', base='#C08AF0', shade='#9A66D2', deep='#7E4EB6', line='#4A2A7E'),
    'cap_pink': dict(hi='#FFD8E8', base='#FF9CC4', shade='#F07AA8', deep='#D85C8E', line='#8E2E5A'),
    'water': dict(hi='#E6FAFF', base='#8ED8F8', shade='#5ABCEE', deep='#3E9ADA', line='#2A6AA8'),
    'cloud': dict(hi='#FFFFFF', base='#FFFFFF', shade='#E2EEFB', deep='#C9DCF3', line='#9DBEE6'),
    'window': dict(hi='#FFFBE0', base='#FFE58A', shade='#F7C948', deep='#E8A93A', line='#8A5232'),
    'metal': dict(hi='#8E8AA8', base='#5E5A78', shade='#46425E', deep='#34304A', line='#221E34'),
}

HAZE = '#CDEBFA'


def haze(mat, t, to=HAZE):
    """재질 톤을 대기색 쪽으로 t 만큼 섞는다(원경)."""
    return {k: mix(v, to, t) for k, v in mat.items()}


def H(name, t=0.0, to=HAZE):
    m = M[name]
    return haze(m, t, to) if t > 0 else dict(m)
