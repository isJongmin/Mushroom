// Results are committed once before presentation. Revealing never performs another draw.
export function createPetReveal(results) {
 let index=-1,phase='sealed';
 return {
  get index(){return index;},get phase(){return phase;},get current(){return index>=0?results[index]:null;},
  get total(){return results.length;},get shown(){return results.slice(0,index+1);},
  begin(){if(phase!=='sealed')return false;phase='charging';return true;},
  reveal(){if(phase!=='charging')return false;index++;phase=index===results.length-1?'complete':'revealed';return true;},
  next(){if(phase!=='revealed')return false;phase='sealed';return true;},
  skip(){index=results.length-1;phase='summary';},
  summary(){if(phase==='complete')phase='summary';},
 };
}
