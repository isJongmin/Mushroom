# 버섯마을 전체 진입 경험 및 UI 개편

## 화면 흐름

세션이 없는 새 방문과 재방문은 새 시작 화면에서 출발한다. 모험 시작은 신규 사용자에게 캐릭터 작업실을, 기존 사용자에게 로비를 연다. 꾸미기 버튼은 신규 생성 또는 기존 편집으로 연결한다. 방 세션이 있으면 기존 재접속 흐름을 유지한다.

1. 시작 화면: 전용 숲속 마을 키 아트, 시작/이어가기, 캐릭터 작업실, 네 지역 소개.
2. 캐릭터 작업실: 크게 보이는 캐릭터 무대, 추천/랜덤 코디, 원래 모습 복원, 부위별 선택, 닉네임, 저장. 잠긴 보상 의상은 접을 수 있는 보관함에 둔다.
3. 모험 로비: 캐릭터 패스와 레벨/지역/펫/골드 요약, 추천 참가, 방 검색, 방 만들기, 비밀번호 방과 기존 삭제·입장 검사.
4. 게임: 기존 숲속 모험책 HUD와 같은 팔레트로 가방·상점·수련·특성·택시·채팅·부활·이벤트 패널을 정돈한다.

## 동작과 안전성

- 저장 형식, 장비·펫·경제 명령, 방 정원·암호 검증은 변경하지 않는다.
- 추천은 참가 가능한 공개 방만 고른다. 내 방 → 접속자 수 → 이름 순서이며, 배열을 변경하지 않는다. 후보가 없으면 생성 확인 창을 연다.
- 방 검색은 이름에 대해 공백을 정리하고 대소문자를 구분하지 않는다. 입장/생성 중에는 검색과 시작 화면 이동을 막는다.
- 캐릭터 미리보기는 지도 이미지를 기다리지 않는다. 별도의 캔버스 무대를 사용하고 아바타 에셋만 준비한다.
- 로비의 모험가 패스는 브라우저의 저장 요약이며, 서버 계정 동기화를 표시하지 않는다. 기기 간 자동 공유가 없다는 안내를 제공한다.
- 기존 테스트의 열린 방 재접속은 유지한다. 테스트 공통 진입 함수는 타이틀의 시작 버튼을 거쳐 기존 프로필/로비 검사로 이어진다.

## 아트

- 프로젝트 아트: `assets/ui/forest-keyart-v1.webp`, 1536×1024, 약 338KiB. 원본을 전송용 WebP로 변환했다.
- 생성 방법: 내장 이미지 생성. 새 시작 화면의 배경으로 사용하며 실제 전투 스크린샷으로 표시하지 않는다.
- 최종 프롬프트: “Use case: stylized-concept. Asset type: final wide key art background for the title screen of a Korean cozy 2D online action RPG called Mushroom Village. Create a premium, art-directed panoramic landscape, 1536x1024 or wider landscape, no text anywhere. Scene: a tiny enchanted forest settlement of charming mushroom-roof timber cottages tucked into enormous mossy trees and terraced grassy islands, a winding stone footpath leading from foreground into the village, small warm window lights, hanging lanterns, fern gardens, soft morning mist and subtle floating spores. The existing game has sculpted block-like voxel foliage, warm coral mushroom roofs, mint-green slimes and a hand-crafted storybook atmosphere; interpret those cues as a cohesive exquisite painterly miniature world, not generic game clipart. Strong atmospheric depth, believable architecture and intentional architectural rhythm, highly crafted materials, cinematic but peaceful. Composition: the settlement and dominant tall tree fill the RIGHT 60 percent; LEFT 40 percent is restrained dark teal foliage, mist and quiet negative space so real HTML title typography can sit there legibly. Warm honey sunlight through upper-right foliage, forest emerald, desaturated jade and sage, cream and terracotta accents. Wide landscape composition with foreground framing leaves. No humans, no huge foreground creatures, no UI, no letters, no words, no logo, no watermark, no glossy plastic, no neon. This will be used as an actual shipped game title-screen art asset.”

## 검증

`portal-experience.test.mjs`에서 저장 요약·저장 차단·손상 데이터·검색·추천 우선순위·첫 방문/재방문 진입·화면 제거 후 이벤트 해제를 검사한다. 기존 성장·전투·워드로브·로딩 회귀 검사를 함께 실행한다. 전체 MMO 서버 권위 전환과 신규 대규모 전투 콘텐츠는 별도 제작 과제다.
