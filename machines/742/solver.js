// Pure, deterministic 742 presentation solver shared by browser, Blender, and
// validators. No DOM or Three.js dependency is allowed here.
const radians = (degrees) => degrees * Math.PI / 180;
export const JLG742_MECHANISM = Object.freeze({
  boomMinimum: radians(0), boomMaximum: radians(69), midTravel: 3.604, flyTravel: 3.604,
  carriageTiltDown: radians(5), carriageTiltUp: radians(12), steerMaximum: radians(55),
  wheelbase: 3.42, wheelCenterTrack: 2.1005, frameLevelMaximum: radians(10),
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
function fixedCylinder(beams,barrelName,rodName,base,anchor,barrelLength){const direction=sub(anchor,base),pinDistance=length(direction);if(pinDistance<=barrelLength)throw new Error(`${barrelName} pin distance is shorter than its fixed barrel`);const axis=scale(direction,1/pinDistance),barrelEnd=add(base,scale(axis,barrelLength)),rodStart=add(barrelEnd,scale(axis,-JLG742_MECHANISM.rodOverlap));beams[barrelName]=[base,barrelEnd];beams[rodName]=[rodStart,anchor];return Object.freeze({pinDistance,barrelLength,rodExposure:pinDistance-barrelLength});}
function ackermannOuter(inner,axleSpan){const magnitude=Math.abs(inner);if(magnitude<1e-7)return 0;const radiusToCenter=JLG742_MECHANISM.wheelCenterTrack/2+axleSpan/Math.tan(magnitude);return Math.atan(axleSpan/(radiusToCenter+JLG742_MECHANISM.wheelCenterTrack/2));}
function wheelAngles(steerAngle,mode){if(Math.abs(steerAngle)<1e-7)return Object.freeze({FL:0,FR:0,RL:0,RR:0});if(mode==="crab")return Object.freeze({FL:steerAngle,FR:steerAngle,RL:steerAngle,RR:steerAngle});const positive=steerAngle>0,inner=Math.abs(steerAngle),axleSpan=mode==="circle"?JLG742_MECHANISM.wheelbase/2:JLG742_MECHANISM.wheelbase,outer=ackermannOuter(inner,axleSpan);if(mode==="front")return positive?Object.freeze({FL:outer,FR:inner,RL:0,RR:0}):Object.freeze({FL:-inner,FR:-outer,RL:0,RR:0});return positive?Object.freeze({FL:outer,FR:inner,RL:-outer,RR:-inner}):Object.freeze({FL:-inner,FR:-outer,RL:inner,RR:outer});}
function steeringJoint(centerX,centerLateral,angle){const inward=centerLateral<0?.16:-.16,cosine=Math.cos(-angle),sine=Math.sin(-angle);return[centerX-.12*cosine-inward*sine,.59,centerLateral-.12*sine+inward*cosine];}

export function solve742State(input){const lift=unit(input.lift),telescope=unit(input.telescope),tilt=signed(input.tilt),steer=signed(input.steer),level=signed(input.level),steerMode=["circle","crab","front"].includes(input.steerMode)?input.steerMode:"circle",boomAngle=JLG742_MECHANISM.boomMinimum+(JLG742_MECHANISM.boomMaximum-JLG742_MECHANISM.boomMinimum)*lift,steerAngle=steer*JLG742_MECHANISM.steerMaximum,carriageTiltAngle=tilt<0?tilt*JLG742_MECHANISM.carriageTiltDown:tilt*JLG742_MECHANISM.carriageTiltUp;return Object.freeze({lift,telescope,tilt,steer,level,steerMode,boomAngle,midTranslation:telescope*JLG742_MECHANISM.midTravel,flyTranslation:telescope*JLG742_MECHANISM.flyTravel,carriageAngle:-boomAngle+carriageTiltAngle,carriageTiltAngle,frameAngle:level*JLG742_MECHANISM.frameLevelMaximum,steerAngle,wheelAngles:wheelAngles(steerAngle,steerMode)});}

export function solve742RigGeometry(input,authored={midX:.12,flyX:.12}){const state=input?.boomAngle===undefined?solve742State(input):input,beams={},points={},cylinders={},pivot=[-2.158,1.838,0];
  const liftBase=[-1.8,.7,0],liftAnchor=add(pivot,rotateBoom([1.921964313743242,-.1593667589837514,0],state.boomAngle));cylinders.lift=fixedCylinder(beams,"LiftCylinderBarrel","LiftCylinderRod",liftBase,liftAnchor,JLG742_MECHANISM.barrelLengths.lift);points.LiftCylinderRodPin=liftAnchor;
  for(let lane=0;lane<2;lane+=1){const lateral=lane===0?-.16:-.23,start=[-1.88,lane===0?.74:.70,lateral],end=[liftAnchor[0],liftAnchor[1],lateral],path=[start,add(lerpPoint(start,end,.34),[0,-.12,0]),add(lerpPoint(start,end,.70),[0,-.09,0]),end];for(let segment=0;segment<3;segment+=1)beams[`LiftHose_${lane}_${segment}`]=[path[segment],path[segment+1]];}
  cylinders.telescope=fixedCylinder(beams,"TelescopeCylinderBarrel","TelescopeCylinderRod",[.55,-.22,0],[3.36+state.midTranslation,-.22,0],JLG742_MECHANISM.barrelLengths.telescope);
  const compensationBase=[-2,1.5,-.31],compensationAnchor=add(pivot,rotateBoom([.6226421237161451,.2334907963935544,-.31],state.boomAngle));cylinders.compensation=fixedCylinder(beams,"CompensationCylinderBarrel","CompensationCylinderRod",compensationBase,compensationAnchor,JLG742_MECHANISM.barrelLengths.compensation);
  const midX=authored.midX+state.midTranslation,flyX=authored.flyX+state.flyTranslation,movingHoseEndX=midX+flyX+5.05;
  [-.27,-.20,.20,.27].forEach((lateral,lane)=>{const start=[.15,-.34,lateral],end=[movingHoseEndX,-.28,lateral],path=[start,add(lerpPoint(start,end,.34),[0,-.08,0]),add(lerpPoint(start,end,.69),[0,-.06,0]),end];for(let segment=0;segment<3;segment+=1)beams[`BoomHose_${lane}_${segment}`]=[path[segment],path[segment+1]];});
  for(const[side,lateral]of[["L",-.24],["R",.24]])beams[`ExtendChain_${side}`]=[[.4,-.22,lateral],[midX+flyX+4.7,-.22,lateral]];
  const retractSheaveX=midX+.15,retractAttachmentX=midX+flyX+.7;beams.RetractChain_C=[[5.1,-.25,0],[retractSheaveX,-.25,0]];beams.RetractChain_C_Wrap=[[retractSheaveX,-.25,0],[retractSheaveX,-.43,0]];beams.RetractChain_C_Moving=[[retractSheaveX,-.43,0],[retractAttachmentX,-.43,0]];
  const carriagePivot=[5.296,-.8,0],tiltBase=[4.216,-1.21,.42],tiltAnchor=add(carriagePivot,rotateBoom([-.14058832771272575,.34865041470688394,.42],state.carriageAngle)),tiltLinkAnchor=add(carriagePivot,rotateBoom([-.08,.58,.42],state.carriageAngle));cylinders.carriageTilt=fixedCylinder(beams,"CarriageTiltCylinderBarrel","CarriageTiltCylinderRod",tiltBase,tiltAnchor,JLG742_MECHANISM.barrelLengths.carriageTilt);beams.CarriageTiltLink=[tiltAnchor,tiltLinkAnchor];
  const levelBase=[-.0133,.6054,.4865],levelAnchor=rollFrame([.1121,1.2428,1.1607],state.frameAngle);cylinders.frameLevel=fixedCylinder(beams,"FrameLevelCylinderBarrel","FrameLevelCylinderRod",levelBase,levelAnchor,JLG742_MECHANISM.barrelLengths.frameLevel);
  const rasBase=[-1.95,.64,-.45],rasAnchor=rollFrame([-1.55,.92,-.65],state.frameAngle);cylinders.rearAxleStabilizer=fixedCylinder(beams,"RearAxleStabilizerBarrel","RearAxleStabilizerRod",rasBase,rasAnchor,JLG742_MECHANISM.barrelLengths.rearAxleStabilizer);
  const sensorAnchor=add(pivot,rotateBoom([.35,-.1,-.56],state.boomAngle));beams.BoomAngleSensorLink=[[-2.15,1.64,-.56],sensorAnchor];points.BoomAngleSensorBoomJoint=sensorAnchor;
  for(const[axle,x,left,right]of[["Front",1.71,"FL","FR"],["Rear",-1.71,"RL","RR"]]){const leftCap=[x,.76,-.46],rightCap=[x,.76,.46],axleMean=(state.wheelAngles[left]+state.wheelAngles[right])/2,pistonShift=axleMean/JLG742_MECHANISM.steerMaximum*.12,leftRodEnd=[x,.76,-.72+pistonShift],rightRodEnd=[x,.76,.72+pistonShift];beams[`${axle}SteerCylinderBarrel`]=[leftCap,rightCap];beams[`${axle}SteerCylinderRodLeft`]=[leftCap,leftRodEnd];beams[`${axle}SteerCylinderRodRight`]=[rightCap,rightRodEnd];beams[`${axle}SteerBarLeft`]=[leftRodEnd,steeringJoint(x,-1.05025,state.wheelAngles[left])];beams[`${axle}SteerBarRight`]=[rightRodEnd,steeringJoint(x,1.05025,state.wheelAngles[right])];}
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
