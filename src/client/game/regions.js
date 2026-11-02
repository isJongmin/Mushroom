export const REGIONS={
 village:{event:'버섯마을 지키기',boss:'버섯왕 모스',scale:1,petPower:1,petPrice:1},
 quarry:{event:'수정 채굴장 방어',boss:'수정 거신 크래그',scale:3,petPower:2.5,petPrice:4},
 forest:{event:'세계수 뿌리 수호',boss:'고대 고목 엘더루트',scale:7,petPower:5,petPrice:12},
 frost:{event:'얼음 봉인 수호',boss:'빙하 군주 프로스트',scale:14,petPower:9,petPrice:30}
};
export const regionOf=id=>REGIONS[id]||REGIONS.village;
