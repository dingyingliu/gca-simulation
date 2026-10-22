(function(){
  // ---------- Fixed case. Invented, deterministic. ----------
  const MK={BR:'Brazil',TR:'Türkiye',SG:'Singapore'};
  const LEAD={BR:'Ana',TR:'Deniz',SG:'Mei'};
  // checkable: what written rule, if any, the agent could test this draft against.
  //   'policy'  = the written policy limits, always available to the agent
  //   'records' = the regional agreements, available only if shared
  //   'none'    = nothing written to check against
  const Q=[
    {id:'Q01',mk:'BR',cust:'Aster',kind:'std',day:1,val:2400,record:'Standard catalogue, 30-day terms.',draftWrong:null,checkable:'none'},
    {id:'Q02',mk:'BR',cust:'Nexa',kind:'loc',day:1,val:8200,record:'Nexa distributor agreement, 60-day payment terms, negotiated by Ana.',draftWrong:'30-day terms instead of the agreed 60',fixedByRecords:true,checkable:'records',catch:{regional:true,ho:'records',other:'records'}},
    {id:'Q03',mk:'TR',cust:'Linden',kind:'std',day:1,val:4400,record:'Standard catalogue, 30-day terms.',draftWrong:null,checkable:'none'},
    {id:'Q04',mk:'TR',cust:'Orion',kind:'pol',day:1,val:14500,record:'Orion asked for 18 per cent. The written limit is 10.',draftWrong:'18 per cent discount, written limit is 10',checkable:'policy',catch:{regional:true,ho:true}},
    {id:'Q05',mk:'TR',cust:'Deren',kind:'loc',day:2,val:3200,record:"Deren's contract requires the delivery term stated on every quote. Deren rejects quotes without it.",draftWrong:'no delivery term stated',fixedByRecords:true,checkable:'records',catch:{regional:true,ho:false,other:false}},
    {id:'Q06',mk:'SG',cust:'Vela',kind:'std',day:2,val:17000,record:'Standard catalogue, 30-day terms.',draftWrong:null,checkable:'none'},
    {id:'Q07',mk:'SG',cust:'Nexa',kind:'loc',day:2,val:8200,record:"Same Nexa agreement as Q02, held by Ana in Brazil. Singapore's template does not have it.",draftWrong:'30-day terms instead of the agreed 60',fixedByRecords:true,checkable:'records',cross:'BR',catch:{regional:'records',ho:'records',other:true}},
    {id:'Q08',mk:'BR',cust:'Pine',kind:'std',day:2,val:2900,record:'Standard catalogue, 30-day terms.',draftWrong:null,checkable:'none'},
    {id:'Q09',mk:'SG',cust:'Sol',kind:'std',day:3,val:6800,record:'Standard catalogue. The request said 40 units.',draftWrong:'quoted for 4 units, not 40',fixedByRecords:false,checkable:'none',missReason:'quantity',catch:{regional:true,ho:true,other:true}},
    {id:'Q10',mk:'BR',cust:'Cedar',kind:'loc',day:3,val:5100,record:'Cedar distributor agreement, minimum unit price €105.',draftWrong:'€99 per unit, below the €105 floor',fixedByRecords:true,checkable:'records',catch:{regional:true,ho:'records',other:'records'}},
    {id:'Q11',mk:'TR',cust:'Tern',kind:'std',day:3,val:4100,record:'Standard catalogue, 30-day terms.',draftWrong:null,checkable:'none'},
    {id:'Q12',mk:'SG',cust:'Vega',kind:'pol',day:3,val:9900,record:'Vega asked for 90-day terms. The written limit is 60. Mei does not know the limit.',draftWrong:'90-day terms, written limit is 60',checkable:'policy',catch:{regional:false,ho:true}},
    {id:'Q13',mk:'BR',cust:'Iris',kind:'std',day:4,val:3300,record:'Standard catalogue, 30-day terms.',draftWrong:null,checkable:'none'},
    {id:'Q14',mk:'SG',cust:'Lotus',kind:'loc',day:4,val:7600,record:'Lotus was promised tax-inclusive pricing in a meeting. Written nowhere.',draftWrong:'price quoted before tax',fixedByRecords:false,checkable:'none',missReason:'verbal',catch:{regional:true,ho:false,other:false}},
    {id:'Q15',mk:'TR',cust:'Birch',kind:'std',day:4,val:2100,record:'Standard catalogue, 30-day terms.',draftWrong:null,checkable:'none'},
    {id:'Q16',mk:'SG',cust:'Elm',kind:'std',day:4,val:5400,record:'Standard catalogue, 30-day terms.',draftWrong:null,checkable:'none'},
    {id:'Q17',mk:'TR',cust:'Barut',kind:'loc',day:5,val:6100,record:"Barut agreed minimum price €88, from last year's negotiation.",draftWrong:'€84 per unit, below the agreed €88',fixedByRecords:true,checkable:'records',catch:{regional:true,ho:'records',other:'records'}},
    {id:'Q18',mk:'BR',cust:'Onda',kind:'pol',day:5,val:12800,record:'Onda asked for free shipping on a €12,800 order. The written limit allows it above €20,000.',draftWrong:'free shipping below the written threshold',checkable:'policy',catch:{regional:true,ho:true}},
    {id:'Q19',mk:'BR',cust:'Ravi',kind:'std',day:5,val:1900,record:'Standard catalogue, 30-day terms.',draftWrong:null,checkable:'none'},
    {id:'Q20',mk:'TR',cust:'Sana',kind:'std',day:5,val:2600,record:'Standard catalogue, 30-day terms.',draftWrong:null,checkable:'none'}
  ];
  const CAP={regional:4,ho:3};
  const DELAY={agent:.5,regional:1,ho:2.5};
  const BYPASS=3;              // days a quote waits before the sales team sends it itself
  const QUEUE_PER_OVER=1.5;    // days of wait added by each quote beyond a reviewer's capacity
  const KIND={std:'Standard',loc:'Local knowledge',pol:'Beyond policy'};
  const ACTION={agent:'Agent checks and sends',regional:'Regional review',ho:'Head-office review'};
  const ACCT={team:'the team, through its rule',regional:'the regional lead',ho:'head office',nobody:'no approval recorded'};
  const PRESET={review:{std:'regional',loc:'regional',pol:'regional',share:false,cross:false,owner:'regional'},
                limits:{std:'agent',loc:'agent',pol:'ho',share:true,cross:false,owner:'ho'},
                local:{std:'agent',loc:'regional',pol:'ho',share:false,cross:true,owner:'regional'}};
  const PNAME={review:'Review every quote',limits:'Release within shared limits',local:'Refer local exceptions'};

  function canSee(q,who,d){
    if(!q.draftWrong) return false;
    const v=(q.catch||{})[who];
    if(v==='records') return d.share;
    return !!v;
  }
  // what the agent can verify its own draft against
  function agentCanCheck(q,d){
    if(q.checkable==='policy') return true;
    if(q.checkable==='records') return !!d.share;
    return false;
  }

  function simulate(d){
    const queues={BR:[],TR:[],SG:[],HO:[]};
    const rows=Q.map(q=>{
      const t=[]; const r={...q,trace:t};
      let wrong=q.draftWrong;
      // the agent drafts from what it can reach
      if(wrong && d.share && q.fixedByRecords) wrong=null;
      t.push({cls:'',k:'The request',v:`${q.cust}, ${MK[q.mk]}, €${q.val.toLocaleString('en-GB')}, day ${q.day}. ${q.record}`});
      t.push({cls:'agent',k:'The agent drafts',v:wrong?`From the standard template: ${wrong}.`:(q.draftWrong?'Correctly. The regional agreement was available to it, and the standard template alone would have got this wrong.':'Correctly.')});
      let route=d[q.kind]; let reviewerMk=q.mk;
      if(q.cross && d.cross && route!=='agent'){route='regional'; reviewerMk=q.cross;}
      r.route=route;

      if(route==='agent'){
        const flagged = wrong && agentCanCheck(q,d);
        if(!flagged){
          t.push({cls:'',k:'The agent checks',v:wrong
            ? `Against the written limits, and against the regional agreements ${d.share?'it has been given':'it has not been given'}. Nothing it can read contradicts this draft, so it passes. ${q.checkable!=='none'?'The agreement that would have caught it sits with a lead.':(q.missReason==='quantity'?'The quantity was in the original request, but this agent’s check does not compare quantities against the request.':'What this quote turns on was agreed verbally and written nowhere.')}`
            : 'Against the written limits. Nothing to correct.'});
          t.push({cls:'',k:'Released',v:'Sent without human approval, under the rule the team wrote. Accountability sits with the team.'});
          r.out=q.day+DELAY.agent; r.acct='team'; r.err=wrong;
        }else{
          t.push({cls:'okdot',k:'The agent checks',v:`It can read the rule this draft breaks, so it does not send. Held and escalated to head office.`});
          const qu=queues.HO; qu.push(q.id); const pos=qu.length;
          if(pos<=CAP.ho){
            t.push({cls:'',k:'Head office',v:`Reviews the flagged draft and corrects it. ${DELAY.ho} days added. Escalation ${pos} of ${CAP.ho} head office can take this week.`});
            r.out=q.day+DELAY.agent+DELAY.ho; r.acct='ho'; r.err=null; r.fixed=true; r.escalated=true;
          }else{
            const wait=(pos-CAP.ho)*QUEUE_PER_OVER;
            if(wait>=BYPASS){
              t.push({cls:'gapdot',k:'The queue',v:`Head office already had ${CAP.ho} escalations. This one would have waited ${r1(wait)} days. After ${BYPASS} days the sales team sends the draft itself, so it went out on day ${q.day+BYPASS}, unreviewed and with no approval recorded.`});
              r.out=q.day+BYPASS; r.acct='nobody'; r.err=wrong; r.bypass=true;
            }else{
              t.push({cls:'',k:'Head office',v:`Waited ${r1(wait)} days behind other escalations, then corrected. ${DELAY.ho} days of review added.`});
              r.out=q.day+DELAY.agent+DELAY.ho+wait; r.acct='ho'; r.err=null; r.fixed=true; r.escalated=true;
            }
          }
        }
      }else{
        const key=route==='ho'?'HO':reviewerMk; const qu=queues[key]; qu.push(q.id); const pos=qu.length;
        const cap=route==='ho'?CAP.ho:CAP.regional;
        const who=route==='ho'?'Head office':`${LEAD[reviewerMk]}, ${MK[reviewerMk]} lead`;
        const base=route==='ho'?DELAY.ho:DELAY.regional;
        const wait=pos>cap?(pos-cap)*QUEUE_PER_OVER:0;
        t.push({cls:'',k:'The route',v:(q.cross&&d.cross?`Referred to ${who}, who holds the Nexa agreement.`:`${ACTION[route]}: ${who}.`)+` Quote ${pos} of ${cap} this reviewer can take this week.`});
        if(wait>=BYPASS){
          t.push({cls:'gapdot',k:'The queue',v:`${who} already had ${cap} quotes. This one would have waited ${r1(wait)} days for review. After ${BYPASS} days this company's sales team sends the quote itself, so it went out on day ${q.day+BYPASS}, unreviewed and with no approval recorded.`});
          r.out=q.day+BYPASS; r.acct='nobody'; r.err=wrong; r.bypass=true;
        }else{
          let sees = route==='ho' ? canSee(q,'ho',d) : (reviewerMk===q.mk ? canSee(q,'regional',d) : canSee(q,'other',d));
          const waited = wait>0 ? `Waited ${r1(wait)} days in the queue. ` : '';
          if(wrong && sees){
            r.err=null; r.fixed=true;
            t.push({cls:'okdot',k:'The review',v:`${waited}${who} sees it and corrects it. ${base} ${base===1?'day':'days'} added.`});
          }else if(wrong){
            r.err=wrong;
            t.push({cls:'',k:'The review',v:`${waited}${who} reads it and passes it. ${route==='ho'?'Head office does not hold the regional agreement.':(reviewerMk!==q.mk?"The agreement sits with another market's lead.":'Not visible from what this lead knows.')} ${base} ${base===1?'day':'days'} added.`});
          }else{
            t.push({cls:'',k:'The review',v:`${waited}${who} reads it and passes it. Nothing to correct. ${base} ${base===1?'day':'days'} of review time spent.`});
          }
          r.out=q.day+base+wait; r.acct=route;
        }
      }

      r.days=Math.round((r.out-q.day)*10)/10;
      t.push({cls:r.err?'gapdot':'okdot',k:'The customer',v:`Receives it on day ${r1(r.out)}, ${r1(r.days)} ${r.days===1?'day':'days'} after asking.${r.err?' It is wrong: '+r.err+'.':' It is right.'}`});
      const ownerTxt=d.owner==='regional'?`${LEAD[q.mk]} calls ${q.cust}.`:d.owner==='ho'?`The head of sales calls ${q.cust}.`:`Nobody is named to call ${q.cust}. The rules left this open.`;
      t.push({cls:(r.err&&d.owner==='none')?'gapdot':'',k:'Accountability',v:(r.acct==='nobody'?`No approval was recorded. The quote left under the company's three-day practice, which the team's rules did not authorise. The team remains accountable for the rule that created the queue.`:`Approved by: ${ACCT[r.acct]}.`)+(r.err?' '+ownerTxt:'')});
      return r;
    });
    const n=rows.length;
    const time=rows.reduce((a,r)=>a+r.days,0)/n;
    const load={BR:queues.BR.length,TR:queues.TR.length,SG:queues.SG.length,HO:queues.HO.length};
    const errs=rows.filter(r=>r.err);
    const acct={team:0,regional:0,ho:0,nobody:0};
    rows.forEach(r=>acct[r.acct]++);              // over ALL twenty quotes
    const unsigned=rows.filter(r=>r.acct==='nobody').length;
    const unownedErrs=d.owner==='none'?errs.length:0;
    return {rows,time,load,errs,acct,unsigned,unownedErrs,
            regUsed:load.BR+load.TR+load.SG,hoUsed:load.HO};
  }

  // ---------- UI ----------
  const $=id=>document.getElementById(id);
  const wrap=$('wrap');
  function r1(x){return (Math.round(x*10)/10).toFixed(1);}
  function design(){return {std:$('c-std').value,loc:$('c-loc').value,pol:$('c-pol').value,share:$('c-share').checked,cross:$('c-cross').checked,owner:$('c-owner').value};}
  function setSigns(){
    const map={agent:'the team, through its rule',regional:'the regional lead',ho:'head office'};
    [['std','s-std'],['loc','s-loc'],['pol','s-pol']].forEach(([k,id])=>{$(id).innerHTML='Accountable: <b>'+map[$('c-'+k).value]+'</b>';});
  }
  function motion(){return matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth';}

  let runN=0, current=null, currentDesign=null, baseline=null, last=null, selected=null, worked=false;

  function summary(o){
    const p=[];
    p.push(`${o.errs.length} wrong ${o.errs.length===1?'quote':'quotes'} reached customers`);
    p.push(`${r1(o.time)} days average to the customer`);
    p.push(`the leads were sent ${o.regUsed} quotes for ${CAP.regional*3} review slots`);
    if(o.unsigned) p.push(`${o.unsigned} went out with no approval recorded`);
    if(o.unownedErrs) p.push(`no follow-up owner named for the ${o.unownedErrs} wrong ${o.unownedErrs===1?'quote':'quotes'}`);
    return p.join(', ')+'.';
  }
  function deltaText(o){
    if(!baseline) return '';
    const b=baseline.o;
    const de=o.errs.length-b.errs.length, dt=Math.round((o.time-b.time)*10)/10, du=o.unsigned-b.unsigned;
    const bits=[];
    bits.push(de===0?'the same number of wrong quotes':(de<0?`${-de} fewer wrong ${-de===1?'quote':'quotes'}`:`${de} more wrong ${de===1?'quote':'quotes'}`));
    bits.push(dt===0?'the same release time':(dt<0?`${r1(-dt)} days faster`:`${r1(dt)} days slower`));
    if(du) bits.push(du<0?`${-du} fewer without a recorded approval`:`${du} more without a recorded approval`);
    return `Against the baseline, run ${baseline.n} (${baseline.name}): ${bits.join(', ')}.`;
  }
  function designName(d){
    for(const k in PRESET){const p=PRESET[k];
      if(p.std===d.std&&p.loc===d.loc&&p.pol===d.pol&&p.share===d.share&&p.cross===d.cross&&p.owner===d.owner) return PNAME[k];}
    return 'your design';
  }

  function render(o,d){
    runN++; current=o; currentDesign=d;
    if(!baseline) baseline={o:o,n:runN,name:designName(d)};
    $('resultsWrap').hidden=false; $('setbase').hidden=false;
    $('s3sub').textContent='The same twenty quotes run through your rules.';
    $('runN').textContent='Run '+runN;
    $('delta').textContent=summary(o)+(baseline.n===runN?'':' '+deltaText(o));
    const set=(id,h)=>$(id).innerHTML=h;
    set('o-time',r1(o.time)+'<em>days, average</em>');
    set('o-load',Math.round(100*o.regUsed/(CAP.regional*3))+"%<em>of the leads' capacity</em>");
    set('o-err',o.errs.length+'<em>of 20</em>');
    set('o-gap',(o.unsigned?'<span class="gap">'+o.unsigned+'</span>':'0')+'<em>of 20 with no approval recorded</em>');
    const b=baseline&&baseline.n!==runN?baseline.o:null;
    const prev=(id,txt)=>set(id,b?'Baseline: '+txt:'');
    prev('p-time',b?r1(b.time)+' days':''); prev('p-load',b?Math.round(100*b.regUsed/(CAP.regional*3))+'%':'');
    prev('p-err',b?b.errs.length+' of 20':''); prev('p-gap',b?b.unsigned+' with no approval recorded':'');
    const byKind=k=>{const rs=o.rows.filter(r=>r.kind===k); return r1(rs.reduce((a,r)=>a+r.days,0)/rs.length);};
    set('o-time-l',['std','loc','pol'].map(k=>`<li><span>${KIND[k]}</span><span>${byKind(k)} d</span></li>`).join(''));
    set('o-load-l',`<li><span>Ana, Brazil</span><span>${o.load.BR} of ${CAP.regional}</span></li><li><span>Deniz, Türkiye</span><span>${o.load.TR} of ${CAP.regional}</span></li><li><span>Mei, Singapore</span><span>${o.load.SG} of ${CAP.regional}</span></li><li><span>Head office</span><span>${o.load.HO} of ${CAP.ho}</span></li>`);
    set('o-err-l',o.errs.length?o.errs.map(r=>`<li><span>${r.id} ${r.cust}</span><span>${KIND[r.kind].toLowerCase()}</span></li>`).join(''):'<li><span class="okc">Every quote right at the customer</span><span></span></li>');
    set('o-gap-l',`<li><span>The team, through its rules</span><span>${o.acct.team}</span></li><li><span>A regional lead</span><span>${o.acct.regional}</span></li><li><span>Head office</span><span>${o.acct.ho}</span></li>`
      +(o.acct.nobody?`<li><span class="gap">No approval recorded, sent round the process</span><span class="gap">${o.acct.nobody}</span></li>`:'')
      +(o.unownedErrs?`<li><span class="gap">Wrong quotes with no follow-up owner</span><span class="gap">${o.unownedErrs}</span></li>`:''));
    $('rows').innerHTML=o.rows.map(r=>`<tr data-id="${r.id}"><td><span class="id">${r.id}</span> <span class="mk">${r.cust}, ${MK[r.mk]}${r.cross?' (agreement in Brazil)':''}</span></td><td><span class="tag">${KIND[r.kind]}</span></td><td>${r.bypass?'<span class="gap">No approval recorded</span>':(r.escalated?'Agent check, then head office':(r.route==='agent'?'Agent, then sent':r.route==='ho'?'Head office':(r.cross&&d.cross?LEAD[r.cross]+' (Brazil)':LEAD[r.mk])))}</td><td>day ${r1(r.out)}</td><td>${r.err?'<span class="gap">Wrong: '+r.err+'</span>':(r.fixed?'<span class="okc">Corrected before sending</span>':'Right')}</td><td>${r.acct==='nobody'?'<span class="gap">nobody</span>':ACCT[r.acct]}</td></tr>`).join('');
    document.querySelectorAll('#rows tr').forEach(tr=>tr.addEventListener('click',()=>{
      selected=tr.dataset.id; showTrace();
      document.querySelectorAll('#rows tr').forEach(x=>x.classList.toggle('sel',x.dataset.id===selected));
      $('s3').scrollIntoView({behavior:motion(),block:'start'});
    }));
    const worst=o.errs.slice().sort((a,b2)=>(b2.acct==='nobody')-(a.acct==='nobody')||b2.val-a.val)[0];
    selected=worst?worst.id:o.rows.slice().sort((a,b2)=>b2.days-a.days)[0].id;
    document.querySelectorAll('#rows tr').forEach(x=>x.classList.toggle('sel',x.dataset.id===selected));
    showTrace();
    last=o;
    $('status').textContent='Run '+runN+' complete. Change a rule and run again.';
    $('status').classList.remove('changed');
  }

  function showTrace(){
    const r=current.rows.find(x=>x.id===selected); if(!r) return;
    $('chain-label').textContent=`${r.id} · ${r.cust}, ${MK[r.mk]} · followed back`;
    $('chain').innerHTML=r.trace.map(s=>`<li class="${s.cls}"><b>${s.k}</b>${s.v}</li>`).join('');
    const d=currentDesign;
    let mech,q;
    if(r.bypass){
      mech='This quote was never reviewed. The rules sent more quotes to a reviewer than that reviewer had slots for, and this company releases anything still waiting after three days. A control nobody has the capacity to run stops being a control and becomes an unrecorded route out of the company.';
      q='What would you give up to bring the review load inside capacity, and which errors would you then be accepting on purpose?';
    }else if(r.err && r.route==='agent' && r.missReason==='quantity'){
      mech='The quantity was in the original request, but this agent’s check does not compare quantities against the request. It tests a draft against the written rules, not against the thing it was asked to quote for. Nothing in the rules the team wrote closes that gap either.';
      q='Would you route every standard quote to a person to catch one error of this kind a week, or ask for a check that reads the request back? What does each cost?';
    }else if(r.err && r.route==='agent' && r.checkable==='none'){
      mech='What this quote turned on was agreed verbally and written nowhere, so neither the template nor the shared agreements contain it and the agent’s check had nothing to test it against. This is a limit of checking against records, not a failure of the check.';
      q='Is this the kind of error you route to the person who was in the room, or the kind you accept and price in? What does your answer cost on the other nineteen quotes?';
    }else if(r.err && r.route==='agent'){
      mech='The agent drafted from the standard template and its check had nothing to test the draft against, because the agreement that governs this customer sits with a regional lead and was not made available to it.';
      q='Would you make that agreement available to the agent, or move the decision to the lead who holds it? Compare what each costs in review time.';
    }else if(r.err){
      mech='A person read this quote and passed it. The reviewer was not looking in the wrong place: what the quote turns on was not visible from where that reviewer sits. Adding a checkpoint above the information does not catch an error defined by the information.';
      q='Which reviewer could have seen it, and what does routing this kind of quote to that person cost the rest of the week?';
    }else if(r.escalated){
      mech='The agent could read the rule this draft broke, so it held the quote rather than sending it. The check did not remove the approval, it routed it: the quote still consumed a head-office slot and the head-office delay.';
      q='If automation moves work to the bottleneck rather than removing it, where should the capacity go?';
    }else{
      mech='This quote went through as designed. The interesting cases are the ones that did not, so open the full list and follow a quote that reached a customer wrong or went out without a recorded approval.';
      q='Which of the twenty did your rules get wrong, and was that a choice you would defend?';
    }
    $('why-mech').textContent=mech; $('why-q').textContent=q;
  }


  const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

  function dText(d){
    return `Regional agreements ${d.share?'available to the agent and head office':'not shared'}. Standard quotes: ${ACTION[d.std].toLowerCase()}. Local-knowledge quotes: ${ACTION[d.loc].toLowerCase()}. Beyond-policy quotes: ${ACTION[d.pol].toLowerCase()}. Cross-market accounts ${d.cross?'referred to the lead who holds the agreement':'treated like any other quote'}. Follow-up owner: ${d.owner==='regional'?'the regional lead':d.owner==='ho'?'the head of sales':'not specified'}.`;
  }
  function compile(){
    if(!current){$('cstatus').textContent='Run the week first, so the submission has a result in it.';return;}
    const o=current,d=currentDesign;
    const nm=$('f-name').value.trim()||'Unnamed, role not given';
    let h=`<h3>Delegation design and trace</h3><p class="meta">${esc(nm)} · Team 4 · run ${runN}${baseline&&baseline.n!==runN?', baseline run '+baseline.n:''}</p>`;
    h+=`<h4>The rules</h4><p>${esc(dText(d))}</p>`;
    h+=`<h4>What the week produced</h4><div class="grid2"><div><span>Wrong quotes at customers</span><span>${o.errs.length}</span></div><div><span>Average days to customer</span><span>${r1(o.time)}</span></div><div><span>Quotes sent to the leads</span><span>${o.regUsed} for ${CAP.regional*3} slots</span></div><div><span>No approval recorded</span><span>${o.unsigned}</span></div></div>`;
    const r=o.rows.find(x=>x.id===selected);
    if(r) h+=`<h4>Quote followed</h4><p>${r.id}, ${esc(r.cust)}, ${MK[r.mk]}. ${r.err?'Wrong at the customer: '+esc(r.err)+'.':(r.fixed?'Corrected before sending.':'Right at the customer.')} Accountable: ${ACCT[r.acct]}.</p>`;
    [['The trace','f-trace'],['The revision and its cost','f-rat'],['What it still cannot handle','f-limit']].forEach(([lab,id])=>{
      const v=$(id).value.trim();
      h+=`<h4>${lab}</h4>`+(v?`<p class="sresp">${esc(v)}</p>`:'<p class="empty">Not yet written.</p>');
    });
    h+=`<p style="margin-top:14px;color:var(--grey);font-size:13px">Assembled from this page. Faculty assess the reasoning against the four rubric criteria, not the company's numbers.</p>`;
    $('report').innerHTML=h; $('reportbox').hidden=false; $('reportbox').open=true;
    $('cstatus').textContent='Preview updated.';
  }

  // ---------- events ----------
  function loadPreset(k){const p=PRESET[k];$('c-std').value=p.std;$('c-loc').value=p.loc;$('c-pol').value=p.pol;$('c-share').checked=p.share;$('c-cross').checked=p.cross;$('c-owner').value=p.owner;setSigns();}
  document.querySelectorAll('.preset').forEach(b=>b.addEventListener('click',()=>{
    const before=design();
    document.querySelectorAll('.preset').forEach(x=>x.classList.toggle('on',x===b));
    loadPreset(b.dataset.p); dirty();
    const after=design();
    const changed=Object.keys(after).filter(k=>after[k]!==before[k]);
    document.querySelectorAll('.contract .row').forEach(row=>row.classList.remove('flash'));
    if(changed.length){
      const idmap={share:'c-share',std:'c-std',loc:'c-loc',pol:'c-pol',cross:'c-cross',owner:'c-owner'};
      changed.forEach(k=>{const el=document.getElementById(idmap[k]); if(el){const row=el.closest('.row'); if(row){row.classList.remove('flash'); void row.offsetWidth; row.classList.add('flash');}}});
      $('status').textContent=`Filled in the rules below. ${changed.length} of the six ${changed.length===1?'line':'lines'} changed. Run the week, or change any line first.`;
    }else{
      $('status').textContent='Those rules were already set. Run the week, or change any line first.';
    }
    $('status').classList.add('changed');
  }));
  function dirty(){$('status').textContent=current?'Rules changed. Run the week to see what they do.':'Choose your rules, then run the week.';$('status').classList.add('changed');}
  ['c-std','c-loc','c-pol','c-share','c-cross','c-owner'].forEach(id=>$(id).addEventListener('change',()=>{setSigns();document.querySelectorAll('.preset').forEach(x=>x.classList.remove('on'));dirty();}));
  $('run').addEventListener('click',()=>{const d=design(); render(simulate(d),d); $('s3').scrollIntoView({behavior:motion(),block:'start'});});
  $('setbase').addEventListener('click',()=>{baseline={o:current,n:runN,name:designName(currentDesign)}; $('delta').textContent=summary(current); $('status').textContent='Run '+runN+' is now the baseline.';});
  $('compile').addEventListener('click',compile);

  // worked example
  const WX={trace:"Q14, Lotus, went out priced before tax. The agent drafted it from the standard template and its check passed, because the tax-inclusive price was promised to Lotus verbally and appears in no record the agent can read. That is not an agent error and not a review that missed it. Our rule sent a quote whose correctness depended on something written nowhere.",
    rat:"We moved local-knowledge quotes to the regional lead. Errors fell and the average release time rose, using six of the leads' twelve review slots. We rejected reviewing everything: that design sends 20 quotes for 12 available slots, so five waited past the three-day point and went out with no approval recorded, and four were still wrong at the customer.",
    limit:"Q09 still goes out wrong. The agent quoted four units where the customer asked for forty, and no rule in our design compares the draft against the original request. Routing it to a lead would catch it, but that means reviewing all eleven standard quotes for one error a week.",
    name:"Illustrative submission, head office pricing"};
  $('wx-open').addEventListener('click',()=>{
    worked=true; $('wxbanner').hidden=false;
    baseline=null; runN=0;
    loadPreset('limits'); document.querySelectorAll('.preset').forEach(x=>x.classList.toggle('on',x.dataset.p==='limits'));
    let d=design(); render(simulate(d),d);
    loadPreset('local'); document.querySelectorAll('.preset').forEach(x=>x.classList.toggle('on',x.dataset.p==='local'));
    d=design(); render(simulate(d),d);
    $('f-trace').value=WX.trace; $('f-rat').value=WX.rat; $('f-limit').value=WX.limit; $('f-name').value=WX.name;
    compile(); $('reportbox').open=false;
    $('wxbanner').scrollIntoView({behavior:motion(),block:'start'});
  });
  $('wx-clear').addEventListener('click',()=>{
    worked=false; $('wxbanner').hidden=true;
    ['f-trace','f-rat','f-limit','f-name'].forEach(id=>$(id).value='');
    $('resultsWrap').hidden=true; $('reportbox').hidden=true; $('setbase').hidden=true;
    baseline=null; last=null; current=null; runN=0;
    $('s3sub').textContent='The same twenty quotes run through your rules. Nothing is shown until you run the week.';
    $('status').textContent='Choose your rules, then run the week.'; $('status').classList.remove('changed');
    document.querySelectorAll('.preset').forEach(x=>x.classList.remove('on'));
    $('s2').scrollIntoView({behavior:motion(),block:'start'});
  });

  // opening state: nothing run
  loadPreset('local'); document.querySelectorAll('.preset').forEach(x=>x.classList.toggle('on',x.dataset.p==='local'));
  setSigns();
})();
