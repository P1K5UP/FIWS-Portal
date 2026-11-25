(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const menu = $("menu-screen"), race = $("race-screen"), canvas = $("race-canvas");
  const ctx = canvas.getContext("2d", { alpha: false });
  const WORLD = { w: 1200, h: 820 };
  const TRACK = {
    name: "VANTAGE PARK",
    subtitle: "GRAND PRIX · TECHNICAL FLOW",
    width: 146,
    points: [
      [205, 525], [210, 300], [335, 190], [525, 170],
      [710, 225], [905, 185], [1030, 295], [1010, 475],
      [875, 610], [680, 595], [515, 675], [315, 650]
    ]
  };
  const controls = { left:false, right:false, throttle:false, brake:false };
  const keys = new Set();
  let samples = [], path = new Path2D(), scale = 1, offsetX = 0, offsetY = 0, dpr = 1;
  let running = false, paused = false, countdown = 0, lastFrame = 0, raf = 0;
  let elapsed = 0, lapElapsed = 0, lapCount = 0, lapStarted = false, lastCrossY = null, toastTimer = 0;
  let soundOn = false;
  const car = { x:210, y:465, vx:0, vy:-10, angle:-Math.PI/2, speed:0, steer:0 };
  let best = Number(localStorage.getItem("fiws-pgp-vantage-best") || 0);

  function buildTrack() {
    const pts = TRACK.points.map(([x,y]) => ({x,y}));
    path = new Path2D();
    const mid = (a,b) => ({x:(a.x+b.x)/2,y:(a.y+b.y)/2});
    const first = mid(pts[pts.length-1], pts[0]);
    path.moveTo(first.x, first.y);
    samples = [];
    for (let i=0;i<pts.length;i++) {
      const p = pts[i], next = pts[(i+1)%pts.length], end = mid(p,next);
      path.quadraticCurveTo(p.x,p.y,end.x,end.y);
      const start = mid(pts[(i+pts.length-1)%pts.length],p);
      for (let s=0;s<=24;s++) {
        const t=s/24, u=1-t;
        samples.push({x:u*u*start.x+2*u*t*p.x+t*t*end.x,y:u*u*start.y+2*u*t*p.y+t*t*end.y});
      }
    }
    samples.push(samples[0]);
  }
  function resize() {
    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(rect.width*dpr);
    canvas.height = Math.round(rect.height*dpr);
    scale = Math.min(canvas.width/WORLD.w, canvas.height/WORLD.h);
    offsetX = (canvas.width-WORLD.w*scale)/2;
    offsetY = (canvas.height-WORLD.h*scale)/2;
    draw();
  }
  function nearestTrackDistance(x,y) {
    let min = Infinity;
    for (let i=0;i<samples.length-1;i++) {
      const a=samples[i], b=samples[i+1], dx=b.x-a.x, dy=b.y-a.y;
      const t=Math.max(0,Math.min(1,((x-a.x)*dx+(y-a.y)*dy)/(dx*dx+dy*dy||1)));
      const px=a.x+t*dx, py=a.y+t*dy;
      min=Math.min(min,Math.hypot(x-px,y-py));
    }
    return min;
  }
  function drawGround() {
    ctx.fillStyle="#315d45";ctx.fillRect(0,0,WORLD.w,WORLD.h);
    ctx.save();ctx.globalAlpha=.14;ctx.strokeStyle="#b1d28b";ctx.lineWidth=2;
    for(let x=-500;x<1600;x+=34){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x+430,WORLD.h);ctx.stroke();}
    ctx.restore();
    ctx.save();ctx.strokeStyle="#254c3b";ctx.lineWidth=TRACK.width+38;ctx.lineCap="round";ctx.lineJoin="round";ctx.stroke(path);ctx.restore();
    ctx.save();ctx.strokeStyle="#e8e5d7";ctx.lineWidth=TRACK.width+18;ctx.lineCap="round";ctx.lineJoin="round";ctx.stroke(path);ctx.restore();
    ctx.save();ctx.strokeStyle="#d94b43";ctx.lineWidth=TRACK.width+13;ctx.setLineDash([22,22]);ctx.lineCap="butt";ctx.stroke(path);ctx.restore();
    ctx.save();ctx.strokeStyle="#f4f0df";ctx.lineWidth=TRACK.width+13;ctx.setLineDash([22,22]);ctx.lineDashOffset=22;ctx.lineCap="butt";ctx.stroke(path);ctx.restore();
    ctx.save();ctx.strokeStyle="#343d43";ctx.lineWidth=TRACK.width;ctx.lineCap="round";ctx.lineJoin="round";ctx.stroke(path);ctx.restore();
    ctx.save();ctx.strokeStyle="#424c51";ctx.lineWidth=TRACK.width-12;ctx.lineCap="round";ctx.lineJoin="round";ctx.stroke(path);ctx.restore();
    ctx.save();ctx.strokeStyle="#ffffff";ctx.globalAlpha=.12;ctx.lineWidth=2;ctx.setLineDash([20,28]);ctx.stroke(path);ctx.restore();
    // Start/finish gantry and timing line.
    ctx.save();ctx.translate(210,410);ctx.fillStyle="#e8ece6";ctx.fillRect(-5,-74,10,148);
    for(let i=0;i<8;i++){ctx.fillStyle=i%2?"#17232b":"#f4f4e9";ctx.fillRect(-5,-74+i*18,10,18);}
    ctx.fillStyle="#101c24";ctx.fillRect(-9,-91,18,15);ctx.fillStyle="#d8f7f5";ctx.font="bold 9px monospace";ctx.textAlign="center";ctx.fillText("FIWS",0,-80);ctx.restore();
    // Small trackside boards add scale and identity.
    const boards=[[430,104,"VANTAGE"],[810,130,"FIWS"],[1080,410,"RACE"],[720,690,"PIT"],[150,660,"FIWS"]];
    for(const [x,y,label] of boards){ctx.save();ctx.translate(x,y);ctx.fillStyle="#0c202b";ctx.fillRect(-31,-9,62,18);ctx.fillStyle="#49d5dc";ctx.fillRect(-31,-9,3,18);ctx.fillStyle="#e9f1ed";ctx.font="bold 8px monospace";ctx.textAlign="center";ctx.textBaseline="middle";ctx.fillText(label,2,1);ctx.restore();}
    // Infield service buildings.
    ctx.fillStyle="#263e3a";ctx.fillRect(430,350,155,70);ctx.fillRect(620,360,92,54);
    ctx.fillStyle="#3a5148";ctx.fillRect(440,359,135,52);ctx.fillRect(630,368,72,38);
    ctx.fillStyle="#a7b6a6";ctx.font="9px monospace";ctx.fillText("PADDOCK",475,390);
  }
  function drawCar(x,y,angle,color="#42d6df",ghost=false) {
    ctx.save();ctx.translate(x,y);ctx.rotate(angle + Math.PI/2);
    ctx.globalAlpha=ghost?.55:1;
    ctx.fillStyle="#071017";ctx.shadowColor="#0009";ctx.shadowBlur=ghost?0:9;ctx.shadowOffsetY=4;
    ctx.fillRect(-18,-15,37,30);ctx.shadowBlur=0;ctx.shadowOffsetY=0;
    // Four exposed wheels.
    ctx.fillStyle="#101519";
    ctx.fillRect(-13,-20,10,9);ctx.fillRect(7,-20,10,9);ctx.fillRect(-13,11,10,9);ctx.fillRect(7,11,10,9);
    ctx.fillStyle="#69757a";ctx.fillRect(-12,-19,8,2);ctx.fillRect(8,-19,8,2);ctx.fillRect(-12,17,8,2);ctx.fillRect(8,17,8,2);
    // Front and rear wings.
    ctx.fillStyle="#151e23";ctx.fillRect(-17,-23,34,5);ctx.fillRect(-19,18,38,5);
    ctx.fillStyle=color;ctx.fillRect(-15,-22,30,2);ctx.fillRect(-17,20,34,2);
    // Monocoque and nose.
    ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(-8,17);ctx.lineTo(-7,-12);ctx.lineTo(-4,-22);ctx.lineTo(0,-28);ctx.lineTo(4,-22);ctx.lineTo(7,-12);ctx.lineTo(8,17);ctx.closePath();ctx.fill();
    ctx.fillStyle="#eaf2ec";ctx.globalAlpha=ghost?.7:.9;ctx.fillRect(-2,-22,4,8);
    ctx.globalAlpha=ghost?.55:1;ctx.fillStyle="#17242c";ctx.beginPath();ctx.ellipse(0,2,5,8,0,0,Math.PI*2);ctx.fill();
    ctx.fillStyle="#f1c48e";ctx.beginPath();ctx.arc(0,1,3,0,Math.PI*2);ctx.fill();
    ctx.restore();
  }
  function draw() {
    if(!ctx)return;
    ctx.setTransform(1,0,0,1,0,0);ctx.fillStyle="#315d45";ctx.fillRect(0,0,canvas.width,canvas.height);
    ctx.setTransform(scale*dpr,0,0,scale*dpr,offsetX,offsetY);
    drawGround();
    drawCar(car.x,car.y,car.angle);
    ctx.setTransform(1,0,0,1,0,0);
  }
  function formatTime(ms) {
    if(!ms || !Number.isFinite(ms))return "--:--.---";
    const m=Math.floor(ms/60000),s=Math.floor(ms/1000)%60,th=Math.floor(ms%1000);
    return String(m).padStart(2,"0")+":"+String(s).padStart(2,"0")+"."+String(th).padStart(3,"0");
  }
  function updateHud() {
    $("lap-display").textContent=lapCount?String(lapCount).padStart(2,"0"):"OUT";
    $("lap-time").textContent=formatTime(lapStarted?lapElapsed:0);
    $("best-time").textContent=formatTime(best);
    $("menu-best").textContent=formatTime(best);
    $("speed-value").textContent=String(Math.round(Math.hypot(car.vx,car.vy)*1.65)).padStart(3,"0");
  }
  function showToast(message) {
    const el=$("toast");el.textContent=message;el.classList.remove("hidden");
    clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.add("hidden"),1800);
  }
  function resetCar() {
    car.x=210;car.y=465;car.vx=0;car.vy=-12;car.speed=0;car.angle=-Math.PI/2;car.steer=0;
    elapsed=0;lapElapsed=0;lapCount=0;lapStarted=false;lastCrossY=car.y;
    updateHud();
  }
  function startSession() {
    menu.classList.add("hidden");race.classList.remove("hidden");$("pause-overlay").classList.add("hidden");
    resetCar();paused=false;running=true;countdown=2.5;$("countdown").classList.remove("hidden");
    if(window.matchMedia("(max-width:760px)").matches) { try{screen.orientation?.lock?.("landscape").catch(()=>{});}catch(e){} }
    resize();lastFrame=performance.now();cancelAnimationFrame(raf);raf=requestAnimationFrame(frame);
  }
  function endSession() {
    running=false;paused=false;cancelAnimationFrame(raf);race.classList.add("hidden");$("pause-overlay").classList.add("hidden");menu.classList.remove("hidden");
    try{screen.orientation?.unlock?.();}catch(e){}
    updateHud();
  }
  function setPaused(value) {
    if(!running)return;paused=value;$("pause-overlay").classList.toggle("hidden",!paused);
    if(!paused){lastFrame=performance.now();raf=requestAnimationFrame(frame);}
  }
  function input(name) {
    if(controls[name])return true;
    if(name==="left")return keys.has("ArrowLeft")||keys.has("a");
    if(name==="right")return keys.has("ArrowRight")||keys.has("d");
    if(name==="throttle")return keys.has("ArrowUp")||keys.has("w");
    if(name==="brake")return keys.has("ArrowDown")||keys.has("s");
    return false;
  }
  function physics(dt) {
    const throttle=input("throttle"),brake=input("brake"),left=input("left"),right=input("right");
    const onRoad=nearestTrackDistance(car.x,car.y)<TRACK.width/2-5;
    const speed=Math.hypot(car.vx,car.vy);
    const maxSteer=1.0, steerTarget=(right?1:0)-(left?1:0);
    car.steer+=(steerTarget-car.steer)*Math.min(1,dt*9);
    const grip=onRoad?5.6:1.3;
    const forwardX=Math.cos(car.angle),forwardY=Math.sin(car.angle);
    const forwardSpeed=car.vx*forwardX+car.vy*forwardY;
    const steeringEffect=Math.min(1.15,Math.abs(forwardSpeed)/105);
    car.angle+=car.steer*maxSteer*steeringEffect*dt*(forwardSpeed>=0?1:-1);
    if(throttle) {car.vx+=Math.cos(car.angle)*205*dt;car.vy+=Math.sin(car.angle)*205*dt;}
    if(brake){car.vx*=Math.pow(.16,dt);car.vy*=Math.pow(.16,dt);}
    const fx=Math.cos(car.angle),fy=Math.sin(car.angle);
    const longitudinal=car.vx*fx+car.vy*fy;
    const lateralX=car.vx-longitudinal*fx,lateralY=car.vy-longitudinal*fy;
    car.vx-=lateralX*Math.min(1,grip*dt);car.vy-=lateralY*Math.min(1,grip*dt);
    const drag=onRoad?.986:.94;
    car.vx*=Math.pow(drag,dt*60);car.vy*=Math.pow(drag,dt*60);
    const maxSpeed=onRoad?235:82;
    const current=Math.hypot(car.vx,car.vy);
    if(current>maxSpeed){car.vx*=maxSpeed/current;car.vy*=maxSpeed/current;}
    car.x+=car.vx*dt;car.y+=car.vy*dt;
    // Soft world boundary keeps a lost car in the playable scene.
    if(car.x<25||car.x>WORLD.w-25||car.y<25||car.y>WORLD.h-25){car.vx*=-.32;car.vy*=-.32;car.x=Math.max(25,Math.min(WORLD.w-25,car.x));car.y=Math.max(25,Math.min(WORLD.h-25,car.y));}
    if(!onRoad&&speed>65&&Math.random()<dt*2)showToast("OFF THE RACING LINE");
    // Timing line: a northbound crossing starts the clock and completes subsequent laps.
    if(lastCrossY!==null&&lastCrossY>410&&car.y<=410&&Math.abs(car.x-210)<72&&car.vy<0){
      if(!lapStarted){lapStarted=true;lapElapsed=0;showToast("LAP STARTED");}
      else if(lapElapsed>8000){lapCount++;if(!best||lapElapsed<best){best=lapElapsed;localStorage.setItem("fiws-pgp-vantage-best",String(best));showToast("PERSONAL BEST  //  "+formatTime(best));}else showToast("LAP "+lapCount+"  //  "+formatTime(lapElapsed));lapElapsed=0;}
    }
    lastCrossY=car.y;
  }
  function frame(now) {
    if(!running||paused)return;
    const dt=Math.min(.033,Math.max(0,(now-lastFrame)/1000));lastFrame=now;
    if(countdown>0){countdown-=dt;const n=Math.ceil(countdown);$("countdown").textContent=n>0?String(n):"GO";if(countdown<=0){$("countdown").classList.add("hidden");showToast("GOOD LUCK. DRIVE CLEAN.");}}
    else {physics(dt);if(lapStarted){elapsed+=dt*1000;lapElapsed+=dt*1000;}}
    draw();updateHud();raf=requestAnimationFrame(frame);
  }
  function bindControls() {
    document.addEventListener("keydown",(e)=>{
      const key=e.key.toLowerCase();
      if(["arrowup","arrowdown","arrowleft","arrowright"," "].includes(key))e.preventDefault();
      if(key==="escape"&&running){setPaused(!paused);return;}
      keys.add(key);
    },{passive:false});
    document.addEventListener("keyup",(e)=>keys.delete(e.key.toLowerCase()));
    document.querySelectorAll("[data-control]").forEach(button=>{
      const name=button.dataset.control;
      const down=(e)=>{e.preventDefault();controls[name]=true;button.classList.add("active");};
      const up=(e)=>{e.preventDefault();controls[name]=false;button.classList.remove("active");};
      button.addEventListener("pointerdown",down);button.addEventListener("pointerup",up);button.addEventListener("pointercancel",up);button.addEventListener("lostpointercapture",up);button.addEventListener("contextmenu",e=>e.preventDefault());
    });
    window.addEventListener("blur",()=>{if(running&&!paused)setPaused(true);});
    window.addEventListener("resize",resize);
    document.addEventListener("visibilitychange",()=>{if(document.hidden&&running&&!paused)setPaused(true);});
  }
  $("start-button").addEventListener("click",startSession);
  $("pause-button").addEventListener("click",()=>setPaused(true));
  $("resume-button").addEventListener("click",()=>setPaused(false));
  $("exit-button").addEventListener("click",endSession);
  $("pause-exit-button").addEventListener("click",endSession);
  $("restart-button").addEventListener("click",()=>{resetCar();countdown=2.5;$("countdown").textContent="3";$("countdown").classList.remove("hidden");lastFrame=performance.now();});
  $("sound-toggle").addEventListener("click",()=>{soundOn=!soundOn;$("sound-toggle").textContent=soundOn?"♫":"♪";$("sound-toggle").title=soundOn?"Sound enabled (audio coming soon)":"Sound off";});
  document.querySelectorAll("[data-mode]").forEach(button=>button.addEventListener("click",()=>{if(button.dataset.mode==="grand-prix")return;document.querySelectorAll("[data-mode]").forEach(b=>b.classList.toggle("selected",b===button));}));
  buildTrack();updateHud();bindControls();
})();