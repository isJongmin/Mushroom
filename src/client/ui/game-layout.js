// Shared viewport rules for phones, landscape play and coarse-pointer tablets.
export const touchLayout=(width,height,coarse=false)=>width<720||(width<=1100&&height<=600)||(coarse&&width<=1180);
export const combatReserve=(width,height,chat=false)=>chat?64:(width>height?112:166);
