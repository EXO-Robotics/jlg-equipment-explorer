// Pure, deterministic 742 presentation solver shared by browser, Blender, and
// validators. No DOM or Three.js dependency is allowed here.
const radians = (degrees) => degrees * Math.PI / 180;
export const JLG742_MECHANISM = Object.freeze({
  boomMinimum: radians(0), boomMaximum: radians(69), midTravel: 3.604, flyTravel: 3.604,
  carriageTiltDown: radians(5), carriageTiltUp: radians(12), steerMaximum: radians(55),
  wheelbase: 3.42, wheelCenterTrack: 2.1005, frameLevelMaximum: radians(10),
  extendSheaveRadius: .105, retractSheaveRadius: .095, chainCenterlineOffset: .018, chainWrapSegments: 8,
  steeringArmRearward: .35, steeringArmInward: .05, steeringRackHalfWidth: .70,
  steeringRackMaximumShift: .2155573833112573, steeringBarLength: .4914774282711261,
  barrelLengths: Object.freeze({ lift: 1.65, telescope: 2.10, compensation: 0.65,
    carriageTilt: 0.82, frameLevel: 0.60, rearAxleStabilizer: 0.34 }), rodOverlap: 0.08,
});
const unit=(value)=>Math.max(0,Math.min(1,Number(value)||0));
const signed=(value)=>Math.max(-1,Math.min(1,Number(value)||0));
const add=(a,b)=>a.map((value,index)=>value+b[index]);
const sub=(a,b)=>a.map((value,index)=>value-b[index]);
const scale=(a,amount)=>a.map((value)=>value*amount);
const length=(a)=>Math.hypot(...a);
const lerpPoint=(a,b,amount)=>add(a,scale(sub(b,a),amount));
const rotateBoom=([x,y,z=0],angle)=>[Math.cos(angle)*x-Math.sin(angle)*y,Math.sin(angle)*x+Math.cos(angle)*y,z];
function rollFrame([x,y,z],angle){const py=y-.82;return[x,.82+Math.cos(angle)*py-Math.sin(angle)*z,Math.sin(angle)*py+Math.cos(angle)*z];}
function circleLinkJoint(center,centerRadius,target,targetRadius,lateral){const delta=[target[0]-center[0],target[1]-center[1]],distance=Math.hypot(...delta);if(distance>centerRadius+targetRadius||distance<Math.abs(centerRadius-targetRadius))throw new Error("742 boom-angle sensor linkage cannot close");const along=(centerRadius**2-targetRadius**2+distance**2)/(2*distance),height=Math.sqrt(Math.max(0,centerRadius**2-along**2)),unitDelta=delta.map(value=>value/distance),base=[center[0]+unitDelta[0]*along,center[1]+unitDelta[1]*along];return[base[0]-unitDelta[1]*height,base[1]+unitDelta[0]*height,lateral];}
function fixedCylinder(beams,barrelName,rodName,base,anchor,barrelLength){const direction=sub(anchor,base),pinDistance=length(direction);if(pinDistance<=barrelLength)throw new Error(`${barrelName} pin distance is shorter than its fixed barrel`);const axis=scale(direction,1/pinDistance),barrelEnd=add(base,scale(axis,barrelLength)),rodStart=add(barrelEnd,scale(axis,-JLG742_MECHANISM.rodOverlap));beams[barrelName]=[base,barrelEnd];beams[rodName]=[rodStart,anchor];return Object.freeze({pinDistance,barrelLength,rodExposure:pinDistance-barrelLength});}
function steeringAngleFromRack(side,rackShift){
  const trackHalf=JLG742_MECHANISM.wheelCenterTrack/2,a=JLG742_MECHANISM.steeringArmRearward,
    b=JLG742_MECHANISM.steeringArmInward,r=JLG742_MECHANISM.steeringRackHalfWidth,
    horizontalBarSquared=JLG742_MECHANISM.steeringBarLength**2-.17**2,
    dz=side*(trackHalf-r)-rackShift,
    cosineTerm=(horizontalBarSquared-a*a-b*b-dz*dz)/(2*dz),
    armRadius=Math.hypot(a,b),phase=Math.atan2(side*b,a);
  return Math.max(-JLG742_MECHANISM.steerMaximum,Math.min(JLG742_MECHANISM.steerMaximum,
    phase+Math.asin(Math.max(-1,Math.min(1,cosineTerm/armRadius)))));
}
function axleWheelAngles(command){const rackShift=command*JLG742_MECHANISM.steeringRackMaximumShift;return Object.freeze({left:steeringAngleFromRack(-1,rackShift),right:steeringAngleFromRack(1,rackShift),rackShift});}
function wheelAngles(steerCommand,mode){
  if(Math.abs(steerCommand)<1e-9)return Object.freeze({FL:0,FR:0,RL:0,RR:0});
  const front=axleWheelAngles(steerCommand),rear=axleWheelAngles(mode==="circle"?-steerCommand:mode==="crab"?steerCommand:0);
  return Object.freeze({FL:front.left,FR:front.right,RL:rear.left,RR:rear.right});
}
function steeringJoint(centerX,side,angle){const a=JLG742_MECHANISM.steeringArmRearward,b=JLG742_MECHANISM.steeringArmInward,cosine=Math.cos(angle),sine=Math.sin(angle);return[centerX-a*cosine-side*b*sine,.59,side*JLG742_MECHANISM.wheelCenterTrack/2+a*sine-side*b*cosine];}
function addSemicircle(beams,prefix,center,radius,lateral,rightSide){const points=[];for(let index=0;index<=JLG742_MECHANISM.chainWrapSegments;index+=1){const amount=index/JLG742_MECHANISM.chainWrapSegments,angle=Math.PI/2+(rightSide?-1:1)*Math.PI*amount;points.push([center[0]+radius*Math.cos(angle),center[1]+radius*Math.sin(angle),lateral]);}for(let index=0;index<JLG742_MECHANISM.chainWrapSegments;index+=1)beams[index===0?prefix:`${prefix}_${index}`]=[points[index],points[index+1]];return points;}

export function solve742State(input){const lift=unit(input.lift),telescope=unit(input.telescope),tilt=signed(input.tilt),steer=signed(input.steer),level=signed(input.level),steerMode=["circle","crab","front"].includes(input.steerMode)?input.steerMode:"circle",boomAngle=JLG742_MECHANISM.boomMinimum+(JLG742_MECHANISM.boomMaximum-JLG742_MECHANISM.boomMinimum)*lift,steerAngle=steer*JLG742_MECHANISM.steerMaximum,carriageTiltAngle=tilt<0?tilt*JLG742_MECHANISM.carriageTiltDown:tilt*JLG742_MECHANISM.carriageTiltUp;return Object.freeze({lift,telescope,tilt,steer,level,steerMode,boomAngle,midTranslation:telescope*JLG742_MECHANISM.midTravel,flyTranslation:telescope*JLG742_MECHANISM.flyTravel,carriageAngle:-boomAngle+carriageTiltAngle,carriageTiltAngle,frameAngle:level*JLG742_MECHANISM.frameLevelMaximum,steerAngle,wheelAngles:wheelAngles(steer,steerMode)});}

export function solve742RigGeometry(input,authored={midX:.12,flyX:.12}){const state=input?.boomAngle===undefined?solve742State(input):input,beams={},points={},cylinders={},pivot=[-2.158,1.838,0];
  const liftBase=[-1.8,.7,0],liftAnchor=add(pivot,rotateBoom([1.921964313743242,-.1593667589837514,0],state.boomAngle));cylinders.lift=fixedCylinder(beams,"LiftCylinderBarrel","LiftCylinderRod",liftBase,liftAnchor,JLG742_MECHANISM.barrelLengths.lift);points.LiftCylinderRodPin=liftAnchor;
  for(let lane=0;lane<2;lane+=1){const lateral=lane===0?-.16:-.23,start=[-1.88,lane===0?.74:.70,lateral],end=[liftAnchor[0],liftAnchor[1],lateral],path=[start,add(lerpPoint(start,end,.34),[0,-.12,0]),add(lerpPoint(start,end,.70),[0,-.09,0]),end];for(let segment=0;segment<3;segment+=1)beams[`LiftHose_${lane}_${segment}`]=[path[segment],path[segment+1]];}
  cylinders.telescope=fixedCylinder(beams,"TelescopeCylinderBarrel","TelescopeCylinderRod",[.55,-.22,0],[3.36+state.midTranslation,-.22,0],JLG742_MECHANISM.barrelLengths.telescope);
  const compensationBase=[-2,1.5,-.31],compensationAnchor=add(pivot,rotateBoom([.6226421237161451,.2334907963935544,-.31],state.boomAngle));cylinders.compensation=fixedCylinder(beams,"CompensationCylinderBarrel","CompensationCylinderRod",compensationBase,compensationAnchor,JLG742_MECHANISM.barrelLengths.compensation);
  const midX=authored.midX+state.midTranslation,flyX=authored.flyX+state.flyTranslation,movingHoseEndX=midX+flyX+5.05;
  [-.27,-.20,.20,.27].forEach((lateral,lane)=>{const start=[.15,-.34,lateral],end=[movingHoseEndX,-.28,lateral],path=[start,add(lerpPoint(start,end,.34),[0,-.08,0]),add(lerpPoint(start,end,.69),[0,-.06,0]),end];for(let segment=0;segment<3;segment+=1)beams[`BoomHose_${lane}_${segment}`]=[path[segment],path[segment+1]];});
  const extendSheave=[midX+4.8,-.22],extendAttachmentX=midX+flyX+.70;
  for(const[side,lateral]of[["L",-.24],["R",.24]]){const prefix=`ExtendChain_${side}`,radius=JLG742_MECHANISM.extendSheaveRadius+JLG742_MECHANISM.chainCenterlineOffset,wrap=addSemicircle(beams,`${prefix}_Wrap`,extendSheave,radius,lateral,true);beams[prefix]=[[.4,extendSheave[1]+radius,lateral],wrap[0]];beams[`${prefix}_Moving`]=[wrap.at(-1),[extendAttachmentX,extendSheave[1]-radius,lateral]];}
  const retractSheave=[midX+.15,-.34],retractRadius=JLG742_MECHANISM.retractSheaveRadius+JLG742_MECHANISM.chainCenterlineOffset,retractAttachmentX=midX+flyX+.7,retractWrap=addSemicircle(beams,"RetractChain_C_Wrap",retractSheave,retractRadius,0,false);beams.RetractChain_C=[[5.1,retractSheave[1]+retractRadius,0],retractWrap[0]];beams.RetractChain_C_Moving=[retractWrap.at(-1),[retractAttachmentX,retractSheave[1]-retractRadius,0]];
  const carriagePivot=[5.296,-.8,0],tiltBase=[4.216,-1.21,.42],tiltAnchor=add(carriagePivot,rotateBoom([-.14058832771272575,.34865041470688394,.42],state.carriageAngle)),tiltLinkAnchor=add(carriagePivot,rotateBoom([-.08,.58,.42],state.carriageAngle));cylinders.carriageTilt=fixedCylinder(beams,"CarriageTiltCylinderBarrel","CarriageTiltCylinderRod",tiltBase,tiltAnchor,JLG742_MECHANISM.barrelLengths.carriageTilt);beams.CarriageTiltLink=[tiltAnchor,tiltLinkAnchor];
  const levelBase=[-.0133,.6054,.4865],levelAnchor=rollFrame([.1121,1.2428,1.1607],state.frameAngle);cylinders.frameLevel=fixedCylinder(beams,"FrameLevelCylinderBarrel","FrameLevelCylinderRod",levelBase,levelAnchor,JLG742_MECHANISM.barrelLengths.frameLevel);
  const rasBase=[-1.95,.64,-.45],rasAnchor=rollFrame([-1.55,.92,-.65],state.frameAngle);cylinders.rearAxleStabilizer=fixedCylinder(beams,"RearAxleStabilizerBarrel","RearAxleStabilizerRod",rasBase,rasAnchor,JLG742_MECHANISM.barrelLengths.rearAxleStabilizer);
  const sensorShaft=[-2.25,1.72,-.56],sensorBoomJoint=add(pivot,rotateBoom([.35,0,-.56],state.boomAngle)),sensorCrankJoint=circleLinkJoint(sensorShaft,.10,sensorBoomJoint,.42,-.56);beams.BoomAngleSensorCrank=[sensorShaft,sensorCrankJoint];beams.BoomAngleSensorLink=[sensorCrankJoint,sensorBoomJoint];points.BoomAngleSensorFrameJoint=sensorShaft;points.BoomAngleSensorCrankJoint=sensorCrankJoint;points.BoomAngleSensorBoomJoint=sensorBoomJoint;
  for(const[axle,x,left,right]of[["Front",1.71,"FL","FR"],["Rear",-1.71,"RL","RR"]]){const axleCommand=axle==="Front"?state.steer:state.steerMode==="circle"?-state.steer:state.steerMode==="crab"?state.steer:0,rackShift=axleCommand*JLG742_MECHANISM.steeringRackMaximumShift,leftCap=[x,.76,-.34],rightCap=[x,.76,.34],leftRodEnd=[x,.76,-JLG742_MECHANISM.steeringRackHalfWidth+rackShift],rightRodEnd=[x,.76,JLG742_MECHANISM.steeringRackHalfWidth+rackShift];beams[`${axle}SteerCylinderBarrel`]=[leftCap,rightCap];beams[`${axle}SteerCylinderRodLeft`]=[leftCap,leftRodEnd];beams[`${axle}SteerCylinderRodRight`]=[rightCap,rightRodEnd];beams[`${axle}SteerBarLeft`]=[leftRodEnd,steeringJoint(x,-1,state.wheelAngles[left])];beams[`${axle}SteerBarRight`]=[rightRodEnd,steeringJoint(x,1,state.wheelAngles[right])];}
  return Object.freeze({state,authored:Object.freeze({midX,flyX}),beams:Object.freeze(beams),points:Object.freeze(points),cylinders:Object.freeze(cylinders)});}

export function solve742ForkVertices(input){const state=input?.boomAngle===undefined?solve742State(input):input;
  const reach=.12+state.midTranslation+.12+state.flyTranslation+5.296;
  const carriageCenter=add([-2.158,1.838,0],rotateBoom([reach,-.8,0],state.boomAngle));
  const vertices=[];
  for(const x of[0,1.2192])for(const y of[-.71,-.65])for(const z of[-.391,.391]){
    const local=rotateBoom([x,y,z],state.carriageTiltAngle),world=add(carriageCenter,local);
    vertices.push(rollFrame(world,state.frameAngle));
  }
  return Object.freeze(vertices.map((point)=>Object.freeze(point)));
}
