import * as THREE from "three";
import { JLG742_MECHANISM, solve742RigGeometry, solve742State } from "./solver.js?v=1.1.8";

export { JLG742_MECHANISM, solve742RigGeometry, solve742State };

function required(root,name){const node=root.getObjectByName(name);if(!node)throw new Error(`742 asset is missing ${name}`);return node;}
const DYNAMIC_NAMES=["LiftCylinderBarrel","LiftCylinderRod","LiftCylinderRodPin","TelescopeCylinderBarrel","TelescopeCylinderRod","CompensationCylinderBarrel","CompensationCylinderRod","CarriageTiltCylinderBarrel","CarriageTiltCylinderRod","CarriageTiltLink","CarriageTiltCylinderRodPin","CarriageTiltLinkPin","FrameLevelCylinderBarrel","FrameLevelCylinderRod","RearAxleStabilizerBarrel","RearAxleStabilizerRod","FrontSteerCylinderBarrel","FrontSteerCylinderRodLeft","FrontSteerCylinderRodRight","RearSteerCylinderBarrel","RearSteerCylinderRodLeft","RearSteerCylinderRodRight","BoomAngleSensorCrank","BoomAngleSensorLink","BoomAngleSensorFrameJoint","BoomAngleSensorCrankJoint","BoomAngleSensorBoomJoint",
  ...Array.from({length:2},(_,lane)=>Array.from({length:3},(_,segment)=>`LiftHose_${lane}_${segment}`)).flat(),
  ...Array.from({length:4},(_,lane)=>Array.from({length:10},(_,segment)=>`BoomHose_${lane}_${segment}`)).flat(),
  "FrontSteerBarLeft","FrontSteerBarRight","RearSteerBarLeft","RearSteerBarRight",
  ...["L","R"].flatMap(side=>["", "_Moving", ...Array.from({length:8},(_,index)=>index===0?"_Wrap":`_Wrap_${index}`)].map(suffix=>`ExtendChain_${side}${suffix}`)),
  "RetractChain_C","RetractChain_C_Moving",...Array.from({length:8},(_,index)=>index===0?"RetractChain_C_Wrap":`RetractChain_C_Wrap_${index}`)];

export function create742Rig(root){const dynamic=Object.fromEntries(DYNAMIC_NAMES.map(name=>[name,required(root,name)]));return Object.freeze({root:required(root,"742_ROOT"),frame:required(root,"FrameLevelPivot"),boom:required(root,"BoomLiftPivot"),mid:required(root,"BoomMid"),fly:required(root,"BoomFly"),carriage:required(root,"CarriageTiltPivot"),wheels:Object.freeze({FL:required(root,"SteerPivot_FL"),FR:required(root,"SteerPivot_FR"),RL:required(root,"SteerPivot_RL"),RR:required(root,"SteerPivot_RR")}),dynamic:Object.freeze(dynamic),authored:Object.freeze({midX:required(root,"BoomMid").position.x,flyX:required(root,"BoomFly").position.x,lengths:Object.freeze(Object.fromEntries(DYNAMIC_NAMES.filter(name=>dynamic[name].isMesh).map(name=>[name,Number(dynamic[name].userData.authored_length_m)||1])))})});}

const Y_AXIS=new THREE.Vector3(0,1,0);
function logicalVector([x,y,z=0]){return new THREE.Vector3(x,z,-y);}
function setBeam(rig,name,endpoints){const node=rig.dynamic[name],start=logicalVector(endpoints[0]),end=logicalVector(endpoints[1]),direction=end.clone().sub(start),beamLength=direction.length();if(beamLength<1e-6)throw new Error(`742 ${name} collapsed below a visible length`);node.position.copy(start).addScaledVector(direction,.5);node.quaternion.setFromUnitVectors(Y_AXIS,direction.normalize());node.scale.set(1,beamLength/rig.authored.lengths[name],1);}

export function apply742State(rig,state){rig.frame.rotation.x=state.frameAngle;rig.boom.rotation.y=state.boomAngle;rig.mid.position.x=rig.authored.midX+state.midTranslation;rig.fly.position.x=rig.authored.flyX+state.flyTranslation;rig.carriage.rotation.y=state.carriageAngle;for(const corner of["FL","FR","RL","RR"])rig.wheels[corner].rotation.z=-state.wheelAngles[corner];const geometry=solve742RigGeometry(state,rig.authored);for(const[name,endpoints]of Object.entries(geometry.beams))setBeam(rig,name,endpoints);for(const[name,point]of Object.entries(geometry.points))rig.dynamic[name].position.copy(logicalVector(point));rig.root.updateMatrixWorld(true);}
