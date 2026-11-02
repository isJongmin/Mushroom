const avatar=(hair,hat,top,bottom,shoes,skin='medium',face='smile')=>({hair,hat,top,bottom,shoes,skin,face});
export const NPC_ROSTER={
 village:{quest:{name:'숲지기 모리',avatar:avatar('brown-short','explorer-brown','archer-ranger','ranger-trousers','ranger-boots')},pet:{name:'펫 조련사 루루',avatar:avatar('pink-bridge-ponytail','ribbon-pink','cardigan-cream','skirt-pink','maryjane-red','light')}},
 quarry:{quest:{name:'광산 감독 브론',avatar:avatar('espresso-crop','beanie-yellow','overalls-green','cargo-black','boots-brown','dark','basic')},pet:{name:'광물 연구가 토비',avatar:avatar('mohawk','cap-black','varsity-navy','pants-navy','hightop-black')}},
 forest:{quest:{name:'고목 현자 세이지',avatar:avatar('silver-bob','mage-hat','mage-robe','mage-trousers','mage-boots','light','sleepy')},pet:{name:'정령지기 리프',avatar:avatar('mint-curly','ranger-cap','cardigan-sage','shorts-brown','ranger-boots')}},
 frost:{quest:{name:'설원 순찰대장 이스',avatar:avatar('sky-bob','warrior-circlet','puffer-mint','widepants-cream','chunky-white','light','basic')},pet:{name:'오로라 조련사 유키',avatar:avatar('black-seethrough','beanie-sage','cape-blue','skirt-check','boots-brown','light','wink')}}
};
export const npcRoster=area=>NPC_ROSTER[area]||NPC_ROSTER.village;
