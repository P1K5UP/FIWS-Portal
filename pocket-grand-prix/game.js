(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const menu = $("menu-screen"), race = $("race-screen"), canvas = $("race-canvas");
  const ctx = canvas.getContext("2d", { alpha: false });
  const WORLD = { w: 1600, h: 1100 };
  const TRACK = {
    name: "VANTAGE PARK",
    subtitle: "GRAND PRIX · HIGH-SPEED FLOW",
    width: 184,
    points: [
      [280, 760], [280, 430], [390, 285], [610, 245],
      [830, 315], [1030, 225], [1270, 270], [1430, 440],
      [1390, 655], [1230, 820], [1010, 875], [820, 780],
      [600, 880], [390, 850]
    ]
  };
  const controls = { left:false, right:false, throttle:false, brake:false };
  const keys = new Set();
  let samples = [], path = new Path2D(), scale = 1, offsetX = 0, offsetY = 0, dpr = 1;
  let running = false, paused = false, countdown = 0, lastFrame = 0, raf = 0;
  let elapsed = 0, lapElapsed = 0, lapCount = 0, lapStarted = false, lastCrossY = null, toastTimer = 0;
  let soundOn = false;
  const car = { x:280, y:650, vx:0, vy:-18, angle:-Math.PI/2, speed:0, steer:0 };
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
    ctx.fillStyle="#234b3d";ctx.fillRect(0,0,WORLD.w,WORLD.h);
    ctx.save();ctx.globalAlpha=.18;ctx.strokeStyle="#b9d69a";ctx.lineWidth=3;
    for(let x=-500;x<2200;x+=42){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x+560,WORLD.h);ctx.stroke();}
    ctx.restore();
    ctx.save();ctx.strokeStyle="#172f2a";ctx.lineWidth=TRACK.width+48;ctx.lineCap="round";ctx.lineJoin="round";ctx.stroke(path);ctx.restore();
    ctx.save();ctx.strokeStyle="#e9e5d7";ctx.lineWidth=TRACK.width+25;ctx.lineCap="round";ctx.lineJoin="round";ctx.stroke(path);ctx.restore();
    ctx.save();ctx.strokeStyle="#dc5149";ctx.lineWidth=TRACK.width+17;ctx.setLineDash([24,24]);ctx.lineCap="butt";ctx.stroke(path);ctx.restore();
    ctx.save();ctx.strokeStyle="#f4f0df";ctx.lineWidth=TRACK.width+17;ctx.setLineDash([24,24]);ctx.lineDashOffset=22;ctx.lineCap="butt";ctx.stroke(path);ctx.restore();
    ctx.save();ctx.strokeStyle="#29343b";ctx.lineWidth=TRACK.width;ctx.lineCap="round";ctx.lineJoin="round";ctx.stroke(path);ctx.restore();
    ctx.save();ctx.strokeStyle="#3b4850";ctx.lineWidth=TRACK.width-16;ctx.lineCap="round";ctx.lineJoin="round";ctx.stroke(path);ctx.restore();
    ctx.save();ctx.strokeStyle="#ffffff";ctx.globalAlpha=.18;ctx.lineWidth=3;ctx.setLineDash([28,34]);ctx.stroke(path);ctx.restore();
    // Start/finish gantry and timing line.
    // Horizontal start/finish stripe across the full racing surface.
    ctx.save();ctx.translate(280,565);ctx.fillStyle="#e8ece6";ctx.fillRect(-TRACK.width/2,-5,TRACK.width,10);
    for(let i=0;i<10;i++){ctx.fillStyle=i%2?"#17232b":"#f4f4e9";ctx.fillRect(-TRACK.width/2+i*TRACK.width/10,-5,TRACK.width/10,10);}
    ctx.fillStyle="#e8ece6";ctx.fillRect(-TRACK.width/2,-TRACK.width/2-18,8,TRACK.width+36);ctx.fillRect(TRACK.width/2-8,-TRACK.width/2-18,8,TRACK.width+36);
    ctx.fillStyle="#101c24";ctx.fillRect(-30,-TRACK.width/2-37,60,18);ctx.fillStyle="#d8f7f5";ctx.font="bold 11px monospace";ctx.textAlign="center";ctx.fillText("FIWS",0,-TRACK.width/2-24);ctx.restore();
    // Trackside advertising, grandstands and paddock blocks.
    const boards=[[540,135,"VANTAGE"],[1040,125,"FIWS"],[1500,535,"RACE"],[940,990,"PIT LANE"],[125,930,"FIWS"],[760,480,"POCKET GP"]];
    for(const [x,y,label] of boards){ctx.save();ctx.translate(x,y);ctx.fillStyle="#0b2029";ctx.fillRect(-46,-12,92,24);ctx.fillStyle="#49d5dc";ctx.fillRect(-46,-12,4,24);ctx.fillStyle="#e9f1ed";ctx.font="bold 10px monospace";ctx.textAlign="center";ctx.textBaseline="middle";ctx.fillText(label,2,1);ctx.restore();}
    ctx.fillStyle="#263e3a";ctx.fillRect(520,470,170,82);ctx.fillRect(740,450,120,66);ctx.fillRect(1030,520,170,90);
    ctx.fillStyle="#3a5148";ctx.fillRect(531,480,148,60);ctx.fillRect(750,459,100,48);ctx.fillRect(1041,531,148,68);
    ctx.fillStyle="#b7c8b9";ctx.font="bold 11px monospace";ctx.fillText("PADDOCK",555,514);ctx.fillText("PIT CONTROL",1055,570);
    // Grandstand rows along the outer straight.
    for(let i=0;i<9;i++){ctx.fillStyle=i%2?"#263c45":"#344f58";ctx.fillRect(450+i*24,155,18,48);}
  }
  function drawCar(x,y,angle,color="#42d6df",ghost=false) {
    ctx.save();ctx.translate(x,y);ctx.rotate(angle + Math.PI/2);
    ctx.globalAlpha=ghost?.58:1;
    // Soft ground shadow and wide exposed slicks.
    ctx.fillStyle="#071017";ctx.shadowColor="#000b";ctx.shadowBlur=ghost?0:16;ctx.shadowOffsetY=8;
    ctx.beginPath();ctx.ellipse(0,0,24,39,0,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;ctx.shadowOffsetY=0;
    ctx.fillStyle="#101519";
    ctx.fillRect(-23,-25,12,22);ctx.fillRect(11,-25,12,22);
    ctx.fillRect(-23,18,12,22);ctx.fillRect(11,18,12,22);
    ctx.fillStyle="#52616a";ctx.fillRect(-22,-23,2,17);ctx.fillRect(20,-23,2,17);ctx.fillRect(-22,20,2,17);ctx.fillRect(20,20,2,17);
    // Sculpted front wing, endplates and rear wing.
    ctx.fillStyle="#111b22";ctx.fillRect(-28,-34,56,7);ctx.fillRect(-30,29,60,8);
    ctx.fillStyle=color;ctx.fillRect(-25,-33,50,2);ctx.fillRect(-27,34,54,2);
    ctx.fillStyle="#d9e4e6";ctx.fillRect(-28,-35,3,9);ctx.fillRect(25,-35,3,9);
    // Narrow monocoque and tapered nose.
    ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(-10,29);ctx.lineTo(-9,-16);ctx.lineTo(-6,-29);ctx.lineTo(-3,-42);ctx.lineTo(0,-48);ctx.lineTo(3,-42);ctx.lineTo(6,-29);ctx.lineTo(9,-16);ctx.lineTo(10,29);ctx.closePath();ctx.fill();
    ctx.fillStyle="#f4f7f4";ctx.fillRect(-2,-44,4,18);
    // Sidepods, cockpit halo and driver.
    ctx.fillStyle="#17252d";ctx.beginPath();ctx.moveTo(-10,8);ctx.lineTo(-19,-5);ctx.lineTo(-17,17);ctx.lineTo(-9,23);ctx.closePath();ctx.fill();
    ctx.beginPath();ctx.moveTo(10,8);ctx.lineTo(19,-5);ctx.lineTo(17,17);ctx.lineTo(9,23);ctx.closePath();ctx.fill();
    ctx.fillStyle="#08131b";ctx.beginPath();ctx.ellipse(0,-3,7,13,0,0,Math.PI*2);ctx.fill();
    ctx.strokeStyle="#d8e5e5";ctx.lineWidth=2;ctx.beginPath();ctx.arc(0,-5,9,Math.PI,Math.PI*2);ctx.stroke();
    ctx.fillStyle="#e9bd8c";ctx.beginPath();ctx.arc(0,-5,3.4,0,Math.PI*2);ctx.fill();
    ctx.fillStyle="#fff";ctx.globalAlpha=ghost?.6:.9;ctx.fillRect(-4,25,8,2);
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
    $("speed-value").textContent=String(Math.round(Math.hypot(car.vx,car.vy)*1.15)).padStart(3,"0");
  }
  function showToast(message) {
    const el=$("toast");el.textContent=message;el.classList.remove("hidden");
    clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.add("hidden"),1800);
  }
  function resetCar() {
    car.x=280;car.y=650;car.vx=0;car.vy=-18;car.speed=0;car.angle=-Math.PI/2;car.steer=0;
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
    const maxSteer=2.05, steerTarget=(right?1:0)-(left?1:0);
    car.steer+=(steerTarget-car.steer)*Math.min(1,dt*16);
    const grip=onRoad?13.5:2.0;
    const forwardX=Math.cos(car.angle),forwardY=Math.sin(car.angle);
    const forwardSpeed=car.vx*forwardX+car.vy*forwardY;
    const steeringEffect=Math.min(1.15,Math.abs(forwardSpeed)/72);
    car.angle+=car.steer*maxSteer*steeringEffect*dt*(forwardSpeed>=0?1:-1);
    if(throttle) {car.vx+=Math.cos(car.angle)*390*dt;car.vy+=Math.sin(car.angle)*390*dt;}
    if(brake){car.vx*=Math.pow(.16,dt);car.vy*=Math.pow(.16,dt);}
    const fx=Math.cos(car.angle),fy=Math.sin(car.angle);
    const longitudinal=car.vx*fx+car.vy*fy;
    const lateralX=car.vx-longitudinal*fx,lateralY=car.vy-longitudinal*fy;
    car.vx-=lateralX*Math.min(1,grip*dt);car.vy-=lateralY*Math.min(1,grip*dt);
    const drag=onRoad?.994:.965;
    car.vx*=Math.pow(drag,dt*60);car.vy*=Math.pow(drag,dt*60);
    const maxSpeed=onRoad?430:125;
    const current=Math.hypot(car.vx,car.vy);
    if(current>maxSpeed){car.vx*=maxSpeed/current;car.vy*=maxSpeed/current;}
    car.x+=car.vx*dt;car.y+=car.vy*dt;
    // Soft world boundary keeps a lost car in the playable scene.
    if(car.x<25||car.x>WORLD.w-25||car.y<25||car.y>WORLD.h-25){car.vx*=-.32;car.vy*=-.32;car.x=Math.max(25,Math.min(WORLD.w-25,car.x));car.y=Math.max(25,Math.min(WORLD.h-25,car.y));}
    if(!onRoad&&speed>65&&Math.random()<dt*2)showToast("OFF THE RACING LINE");
    // Timing line: a northbound crossing starts the clock and completes subsequent laps.
    if(lastCrossY!==null&&lastCrossY>565&&car.y<=565&&Math.abs(car.x-280)<92&&car.vy<0){
      if(!lapStarted){lapStarted=true;lapElapsed=0;showToast("LAP STARTED");}
      else if(lapElapsed>5000){lapCount++;if(!best||lapElapsed<best){best=lapElapsed;localStorage.setItem("fiws-pgp-vantage-best",String(best));showToast("PERSONAL BEST  //  "+formatTime(best));}else showToast("LAP "+lapCount+"  //  "+formatTime(lapElapsed));lapElapsed=0;}
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