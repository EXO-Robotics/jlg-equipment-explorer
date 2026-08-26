#!/usr/bin/env node
import { JLG742_MECHANISM, solve742ForkVertices, solve742RigGeometry, solve742State } from "../machines/742/solver.js";

const dist=([a,b,c],[x,y,z])=>Math.hypot(a-x,b-y,c-z);
const sub=([a,b,c],[x,y,z])=>[a-x,b-y,c-z];
const dot=(a,b)=>a.reduce((sum,value,index)=>sum+value*b[index],0);
const segmentLength=(segment)=>dist(segment[0],segment[1]);
const distanceToSegment=(point,[start,end])=>{const axis=sub(end,start),relative=sub(point,start),amount=Math.max(0,Math.min(1,dot(relative,axis)/dot(axis,axis)));return dist(point,start.map((value,index)=>value+axis[index]*amount));};
const segmentDistance=(first,second)=>{const u=sub(first[1],first[0]),v=sub(second[1],second[0]),w=sub(first[0],second[0]),a=dot(u,u),b=dot(u,v),c=dot(v,v),d=dot(u,w),e=dot(v,w),den=a*c-b*b,eps=1e-14;let sn,sd=den,tn,td=den;if(den<eps){sn=0;sd=1;tn=e;td=c;}else{sn=b*e-c*d;tn=a*e-b*d;if(sn<0){sn=0;tn=e;td=c;}else if(sn>sd){sn=sd;tn=e+b;td=c;}}if(tn<0){tn=0;if(-d<0)sn=0;else if(-d>a)sn=sd;else{sn=-d;sd=a;}}else if(tn>td){tn=td;if(-d+b<0)sn=0;else if(-d+b>a)sn=sd;else{sn=-d+b;sd=a;}}const sc=Math.abs(sn)<eps?0:sn/sd,tc=Math.abs(tn)<eps?0:tn/td;return Math.hypot(...w.map((value,index)=>value+sc*u[index]-tc*v[index]));};
const chainNames=(prefix)=>[prefix,`${prefix}_Wrap`,...Array.from({length:JLG742_MECHANISM.chainWrapSegments-1},(_,index)=>`${prefix}_Wrap_${index+1}`),`${prefix}_Moving`];
const chainLength=(beams,prefix)=>chainNames(prefix).reduce((sum,name)=>sum+segmentLength(beams[name]),0);
const hoseNames=(prefix)=>Array.from({length:prefix.startsWith("Lift")?3:JLG742_MECHANISM.boomHoseArcSegments+2},(_,index)=>`${prefix}_${index}`);
const hoseLength=(beams,prefix)=>hoseNames(prefix).reduce((sum,name)=>sum+segmentLength(beams[name]),0);
const normalizedTangentError=(segment,center,contactIndex)=>{const direction=sub(segment[1],segment[0]),radius=sub(segment[contactIndex],center);return Math.abs(dot(direction,radius))/(Math.hypot(...direction)*Math.hypot(...radius));};
const boomWorldSegment=(segment,angle)=>segment.map(([x,y,z])=>[-2.158+Math.cos(angle)*x-Math.sin(angle)*y,1.838+Math.sin(angle)*x+Math.cos(angle)*y,.30+z]);
const segmentAabbSurfaceClearance=(segment,bounds,radius)=>{const minimum=segment[0].map((value,axis)=>Math.min(value,segment[1][axis])),maximum=segment[0].map((value,axis)=>Math.max(value,segment[1][axis])),gaps=minimum.map((value,axis)=>Math.max(bounds[0][axis]-maximum[axis],value-bounds[1][axis],0));return Math.hypot(...gaps)-radius;};

const cylinderRanges=Object.fromEntries(["lift","telescope","compensation","carriageTilt","frameLevel","rearAxleStabilizer"].map(name=>[name,{min:Infinity,max:-Infinity,barrelMin:Infinity,barrelMax:-Infinity,rodMin:Infinity}]));
const rigidRanges=Object.fromEntries(["BoomAngleSensorCrank","BoomAngleSensorLink","CarriageTiltLink","FrontSteerBarLeft","FrontSteerBarRight","RearSteerBarLeft","RearSteerBarRight"].map(name=>[name,{min:Infinity,max:-Infinity}]));
const chainRanges=Object.fromEntries(["ExtendChain_L","ExtendChain_R","RetractChain_C"].map(name=>[name,{min:Infinity,max:-Infinity,minSegment:Infinity}]));
const hoseRanges=Object.fromEntries([...Array.from({length:2},(_,lane)=>`LiftHose_${lane}`),...Array.from({length:4},(_,lane)=>`BoomHose_${lane}`)].map(name=>[name,{min:Infinity,max:-Infinity,minSegment:Infinity}]));
let samples=0,minForkY=Infinity,maxForkY=-Infinity,maxHeight=-Infinity,maxCenterSpread=0,maxCenterRelativeSpread=0,maxAckermannFitError=0,maxAckermannRelativeError=0,maxFrontModeRelativeError=0,maxFrontModeAngle=0;
let maximumCrabHeadingSpread=0,maximumCrabCorrespondingError=0;
let minimumSteerRodLength=Infinity,maximumSteerRodSpanDrift=0,maximumSteerBarClosureError=0;
let minimumChainSheaveClearance=Infinity,maximumChainTangentError=0,maximumChainEndpointStep=0,priorChainEndpoints=null;
let maximumHoseEndpointStep=0,priorHoseEndpoints=null,minimumBoomHoseTubeClearance=Infinity,maximumBoomHoseDirectionChange=0;
let minimumServiceCabClearance=Infinity,minimumServiceEngineClearance=Infinity,serviceClearanceSamples=0,serviceCabLimiter=null,serviceEngineLimiter=null;
let maxEndpointStep=0,priorGrid=new Map();
const liftValues=Array.from({length:21},(_,i)=>i/20),telescopeValues=Array.from({length:21},(_,i)=>i/20);
const tiltValues=[-1,-.5,0,.25,.5,.75,1],levelValues=Array.from({length:9},(_,i)=>-1+i/4),steerValues=[-1,-.5,0,.5,1],modes=["circle","crab","front"];
const cabInnerHandrail=[[.25,1.18,-.13],[1.48,2.30,-.13]],cabHandrailRadius=.025;
const engineObstacleAabbs=[
  {name:"EngineHoodLower",bounds:[[-1.725,.77,.17],[.625,1.31,1.09]]},
  {name:"EngineHoodUpper",bounds:[[-1.58,1.27,.71],[-.08,1.51,1.21]]},
  {name:"EngineHoodSpine",bounds:[[-1.53,1.49,.71],[-.19,1.55,1.21]]},
  {name:"MainValveBank",bounds:[[-.01,1.11,.40],[.37,1.39,.72]]},
  {name:"ValveSolenoids",bounds:[[-.006,1.26,.534],[.371,1.42,.586]]},
];

for(let liftIndex=0;liftIndex<=200;liftIndex+=1)for(let telescopeIndex=0;telescopeIndex<=200;telescopeIndex+=1){
  const state=solve742State({lift:liftIndex/200,telescope:telescopeIndex/200,tilt:0,steer:0,level:0,steerMode:"circle"}),geometry=solve742RigGeometry(state);serviceClearanceSamples+=1;
  for(const[name,localSegment]of Object.entries(geometry.beams)){
    if(!name.startsWith("BoomHose_")&&!name.startsWith("RetractChain_")&&!name.startsWith("ExtendChain_"))continue;
    const radius=name.startsWith("BoomHose_")?.014:.012,worldSegment=boomWorldSegment(localSegment,state.boomAngle),cabClearance=segmentDistance(worldSegment,cabInnerHandrail)-radius-cabHandrailRadius;
    if(cabClearance<minimumServiceCabClearance){minimumServiceCabClearance=cabClearance;serviceCabLimiter={node:name,lift:state.lift,telescope:state.telescope};}
    for(const obstacle of engineObstacleAabbs){const engineClearance=segmentAabbSurfaceClearance(worldSegment,obstacle.bounds,radius);if(engineClearance<minimumServiceEngineClearance){minimumServiceEngineClearance=engineClearance;serviceEngineLimiter={node:name,obstacle:obstacle.name,lift:state.lift,telescope:state.telescope};}}
  }
}

for(let index=0;index<=2000;index+=1){
  const telescope=index/2000,geometry=solve742RigGeometry({lift:0,telescope,tilt:0,steer:0,level:0,steerMode:"circle"}),midX=geometry.authored.midX;
  for(const prefix of Object.keys(chainRanges)){
    const range=chainRanges[prefix],names=chainNames(prefix),segments=names.map(name=>geometry.beams[name]),total=chainLength(geometry.beams,prefix);
    range.min=Math.min(range.min,total);range.max=Math.max(range.max,total);
    for(const segment of segments)range.minSegment=Math.min(range.minSegment,segmentLength(segment));
    const extend=prefix.startsWith("Extend"),center=extend?[midX+4.8,-.22,prefix.endsWith("L")?-.24:.24]:[midX+.15,-.34,0],sheaveRadius=extend?JLG742_MECHANISM.extendSheaveRadius:JLG742_MECHANISM.retractSheaveRadius;
    maximumChainTangentError=Math.max(maximumChainTangentError,normalizedTangentError(segments[0],center,1),normalizedTangentError(segments.at(-1),center,0));
    for(const segment of segments.slice(1,-1))minimumChainSheaveClearance=Math.min(minimumChainSheaveClearance,distanceToSegment(center,segment)-sheaveRadius-.012);
  }
  const endpoints=Object.keys(chainRanges).flatMap(prefix=>chainNames(prefix).flatMap(name=>geometry.beams[name]));
  if(priorChainEndpoints)for(let point=0;point<endpoints.length;point+=1)maximumChainEndpointStep=Math.max(maximumChainEndpointStep,dist(endpoints[point],priorChainEndpoints[point]));
  priorChainEndpoints=endpoints;
  const liftGeometry=solve742RigGeometry({lift:telescope,telescope:0,tilt:0,steer:0,level:0,steerMode:"circle"});
  for(const prefix of Object.keys(hoseRanges)){
    const source=prefix.startsWith("Lift")?liftGeometry:geometry,range=hoseRanges[prefix],segments=hoseNames(prefix).map(name=>source.beams[name]),total=hoseLength(source.beams,prefix);
    range.min=Math.min(range.min,total);range.max=Math.max(range.max,total);
    for(const segment of segments)range.minSegment=Math.min(range.minSegment,segmentLength(segment));
  }
  const rigidTubes=[[-.29],[-.24],[.24]].map(([lateral])=>[[.35,-.34,lateral],[5.05,-.34,lateral]]);
  for(let lane=0;lane<4;lane+=1){const segments=hoseNames(`BoomHose_${lane}`).map(name=>geometry.beams[name]);
    for(const segment of segments)for(const tube of rigidTubes)minimumBoomHoseTubeClearance=Math.min(minimumBoomHoseTubeClearance,segmentDistance(segment,tube)-.025);
    for(let index=1;index<segments.length;index+=1){const before=sub(segments[index-1][1],segments[index-1][0]),after=sub(segments[index][1],segments[index][0]),cosine=Math.max(-1,Math.min(1,dot(before,after)/(Math.hypot(...before)*Math.hypot(...after))));maximumBoomHoseDirectionChange=Math.max(maximumBoomHoseDirectionChange,Math.acos(cosine));}
  }
  const hoseEndpoints=Object.keys(hoseRanges).flatMap(prefix=>{const source=prefix.startsWith("Lift")?liftGeometry:geometry;return hoseNames(prefix).flatMap(name=>source.beams[name]);});
  if(priorHoseEndpoints)for(let point=0;point<hoseEndpoints.length;point+=1)maximumHoseEndpointStep=Math.max(maximumHoseEndpointStep,dist(hoseEndpoints[point],priorHoseEndpoints[point]));
  priorHoseEndpoints=hoseEndpoints;
  if(index>0){
    const command=index/2000,state=solve742State({lift:0,telescope:0,tilt:0,steer:command,level:0,steerMode:"circle"}),outer=Math.abs(state.wheelAngles.FL),inner=Math.abs(state.wheelAngles.FR),fromInner=JLG742_MECHANISM.wheelCenterTrack/2+(JLG742_MECHANISM.wheelbase/2)/Math.tan(inner),fromOuter=(JLG742_MECHANISM.wheelbase/2)/Math.tan(outer)-JLG742_MECHANISM.wheelCenterTrack/2,error=Math.abs(fromInner-fromOuter);
    maxAckermannFitError=Math.max(maxAckermannFitError,error);maxAckermannRelativeError=Math.max(maxAckermannRelativeError,error/Math.max(fromInner,fromOuter));
    const halfBase=JLG742_MECHANISM.wheelbase/2,halfTrack=JLG742_MECHANISM.wheelCenterTrack/2,centers=[[-halfTrack,halfBase,state.wheelAngles.FL],[halfTrack,halfBase,state.wheelAngles.FR],[-halfTrack,-halfBase,state.wheelAngles.RL],[halfTrack,-halfBase,state.wheelAngles.RR]].map(([z,x,angle])=>z+x/Math.tan(angle)),spread=Math.max(...centers)-Math.min(...centers);
    maxCenterSpread=Math.max(maxCenterSpread,spread);maxCenterRelativeSpread=Math.max(maxCenterRelativeSpread,spread/Math.max(...centers.map(Math.abs)));
    const crab=solve742State({lift:0,telescope:0,tilt:0,steer:command,level:0,steerMode:"crab"}),headings=Object.values(crab.wheelAngles),crabSpread=Math.max(...headings)-Math.min(...headings);
    maximumCrabHeadingSpread=Math.max(maximumCrabHeadingSpread,crabSpread);maximumCrabCorrespondingError=Math.max(maximumCrabCorrespondingError,Math.abs(crab.wheelAngles.FL-crab.wheelAngles.RL),Math.abs(crab.wheelAngles.FR-crab.wheelAngles.RR));
    const front=solve742State({lift:0,telescope:0,tilt:0,steer:command,level:0,steerMode:"front"}),frontCenters=[-halfTrack+JLG742_MECHANISM.wheelbase/Math.tan(front.wheelAngles.FL),halfTrack+JLG742_MECHANISM.wheelbase/Math.tan(front.wheelAngles.FR)],frontSpread=Math.abs(frontCenters[0]-frontCenters[1]);
    maxFrontModeRelativeError=Math.max(maxFrontModeRelativeError,frontSpread/Math.max(...frontCenters.map(Math.abs)));maxFrontModeAngle=Math.max(maxFrontModeAngle,Math.abs(front.wheelAngles.FL),Math.abs(front.wheelAngles.FR));
  }
}

for(let li=0;li<liftValues.length;li+=1)for(let ti=0;ti<telescopeValues.length;ti+=1){
  const lift=liftValues[li],telescope=telescopeValues[ti],base=solve742State({lift,telescope,tilt:0,steer:0,level:0,steerMode:"circle"}),center=solve742ForkVertices(base)[0],key=`${li}:${ti}`;
  for(const neighbor of[`${li-1}:${ti}`,`${li}:${ti-1}`])if(priorGrid.has(neighbor))maxEndpointStep=Math.max(maxEndpointStep,dist(center,priorGrid.get(neighbor)));priorGrid.set(key,center);
  for(const tilt of tiltValues)for(const level of levelValues)for(const mode of modes)for(const steer of steerValues){
    const state=solve742State({lift,telescope,tilt,steer,level,steerMode:mode}),geometry=solve742RigGeometry(state),forks=solve742ForkVertices(state);samples+=1;
    for(const point of forks){minForkY=Math.min(minForkY,point[1]);maxForkY=Math.max(maxForkY,point[1]);}
    if(lift===1&&telescope===1&&tilt===0&&level===0)maxHeight=Math.max(maxHeight,...forks.filter((_,index)=>Math.floor(index/2)%2===1).map(point=>point[1]));
    for(const[name,data]of Object.entries(geometry.cylinders)){const range=cylinderRanges[name],barrelName={lift:"LiftCylinderBarrel",telescope:"TelescopeCylinderBarrel",compensation:"CompensationCylinderBarrel",carriageTilt:"CarriageTiltCylinderBarrel",frameLevel:"FrameLevelCylinderBarrel",rearAxleStabilizer:"RearAxleStabilizerBarrel"}[name];range.min=Math.min(range.min,data.pinDistance);range.max=Math.max(range.max,data.pinDistance);const barrel=segmentLength(geometry.beams[barrelName]);range.barrelMin=Math.min(range.barrelMin,barrel);range.barrelMax=Math.max(range.barrelMax,barrel);range.rodMin=Math.min(range.rodMin,data.rodExposure);}
    for(const[name,range]of Object.entries(rigidRanges)){const value=segmentLength(geometry.beams[name]);range.min=Math.min(range.min,value);range.max=Math.max(range.max,value);}
    for(const axle of["Front","Rear"]){const leftRod=geometry.beams[`${axle}SteerCylinderRodLeft`],rightRod=geometry.beams[`${axle}SteerCylinderRodRight`],leftBar=geometry.beams[`${axle}SteerBarLeft`],rightBar=geometry.beams[`${axle}SteerBarRight`];minimumSteerRodLength=Math.min(minimumSteerRodLength,segmentLength(leftRod),segmentLength(rightRod));maximumSteerRodSpanDrift=Math.max(maximumSteerRodSpanDrift,Math.abs(dist(leftRod[1],rightRod[1])-2*JLG742_MECHANISM.steeringRackHalfWidth));maximumSteerBarClosureError=Math.max(maximumSteerBarClosureError,dist(leftRod[1],leftBar[0]),dist(rightRod[1],rightBar[0]));}
  }
}

const stow=solve742State({lift:0,telescope:0,tilt:0,steer:0,level:0,steerMode:"circle"}),stowForks=solve742ForkVertices(stow),stowTip=Math.max(...stowForks.map(point=>point[0])),stowSurface=Math.max(...stowForks.map(point=>point[1])),stowBottom=Math.min(...stowForks.map(point=>point[1]));
const maxCircle=solve742State({lift:0,telescope:0,tilt:0,steer:1,level:0,steerMode:"circle"}).wheelAngles,inner=Math.max(...Object.values(maxCircle).map(Math.abs)),centerRadius=JLG742_MECHANISM.wheelCenterTrack/2+(JLG742_MECHANISM.wheelbase/2)/Math.tan(inner),visualOutsideWheelCenterRadius=Math.hypot(centerRadius+JLG742_MECHANISM.wheelCenterTrack/2,JLG742_MECHANISM.wheelbase/2);
const reachState=solve742State({lift:3/69,telescope:1,tilt:0,steer:0,level:0,steerMode:"circle"}),reachForks=solve742ForkVertices(reachState),forkHeelX=Math.min(...reachForks.map(point=>point[0])),loadCenterX=forkHeelX+.6096;
if(minimumBoomHoseTubeClearance<.005)throw new Error(`boom-hose rigid-tube clearance ${minimumBoomHoseTubeClearance} is below 5 mm`);
if(maximumBoomHoseDirectionChange>Math.PI/8+.01)throw new Error(`boom-hose adjacent direction change ${maximumBoomHoseDirectionChange} exceeds curved-loop limit`);
if(serviceClearanceSamples!==201*201||minimumServiceCabClearance<.01||minimumServiceEngineClearance<.01)throw new Error(`dense boom-service chassis clearance failed: samples=${serviceClearanceSamples}, cab=${minimumServiceCabClearance}, engine=${minimumServiceEngineClearance}`);
const maximumFrontState=solve742State({lift:0,telescope:0,tilt:0,steer:1,level:0,steerMode:"front"}),maximumCrabState=solve742State({lift:0,telescope:0,tilt:0,steer:1,level:0,steerMode:"crab"}),maximumFrontWheelAngle=Math.max(Math.abs(maximumFrontState.wheelAngles.FL),Math.abs(maximumFrontState.wheelAngles.FR)),maximumCrabWheelAngle=Math.max(...Object.values(maximumCrabState.wheelAngles).map(Math.abs));
if(maximumFrontWheelAngle<35*Math.PI/180||maximumCrabWheelAngle<20*Math.PI/180||inner<35*Math.PI/180)throw new Error("steering modes do not achieve useful reconstructed travel");
if(maximumCrabHeadingSpread>Math.PI/180)throw new Error("static-linkage crab toe exceeds one degree");
const output={status:"PASS",canonical_solver:"machines/742/solver.js",unique_multidimensional_state_samples:samples,sample_axes:{lift:21,telescope:21,tilt:7,frame_level:9,steer:5,steering_modes:3},continuous_retract_chain_samples:2001,continuous_all_chain_samples:2001,continuous_hose_samples:2001,minimum_retract_chain_segment_m:chainRanges.RetractChain_C.minSegment,minimum_retract_leg_vertical_separation_m:2*(JLG742_MECHANISM.retractSheaveRadius+JLG742_MECHANISM.chainCenterlineOffset),maximum_retract_endpoint_step_m:maximumChainEndpointStep,maximum_chain_endpoint_step_m:maximumChainEndpointStep,chain_paths:Object.fromEntries(Object.entries(chainRanges).map(([name,range])=>[name,{total_length_range_m:[range.min,range.max],maximum_total_length_drift_m:range.max-range.min,minimum_segment_length_m:range.minSegment,wrap_degrees:180}])),hose_paths:Object.fromEntries(Object.entries(hoseRanges).map(([name,range])=>[name,{total_length_range_m:[range.min,range.max],maximum_total_length_drift_m:range.max-range.min,minimum_segment_length_m:range.minSegment}])),maximum_hose_endpoint_step_m:maximumHoseEndpointStep,maximum_chain_tangent_dot_error:maximumChainTangentError,minimum_chain_to_sheave_surface_clearance_m:minimumChainSheaveClearance,maximum_adjacent_carriage_endpoint_step_m:maxEndpointStep,minimum_fork_blade_y_m:minForkY,maximum_fork_y_m:maxForkY,maximum_level_fork_surface_y_m:maxHeight,stow:{boom_angle_degrees:stow.boomAngle*180/Math.PI,fork_bottom_m:stowBottom,fork_load_surface_m:stowSurface,total_length_rear_plane_to_fork_tip_m:stowTip+2.38},maximum_reach_pose:{boom_angle_degrees:3,fork_heel_x_m:forkHeelX,load_center_world_x_m:loadCenterX,front_tire_tread_plane_x_m:null,forward_reach_m:null,load_center_m:.6096,pose_authority:"selected reconstructed visual pose"},cylinder_ranges:Object.fromEntries(Object.entries(cylinderRanges).map(([name,range])=>[name,{pin_distance_m:[range.min,range.max],stroke_usage_m:range.max-range.min,fixed_barrel_length_range_m:[range.barrelMin,range.barrelMax],minimum_rod_exposure_m:range.rodMin}])),rigid_link_ranges_m:Object.fromEntries(Object.entries(rigidRanges).map(([name,range])=>[name,[range.min,range.max]])),steering_linkage:{minimum_straight_rod_length_m:minimumSteerRodLength,steering_bar_nominal_length_m:JLG742_MECHANISM.steeringBarLength,maximum_steering_bar_length_drift_m:Math.max(...Object.entries(rigidRanges).filter(([name])=>name.includes("SteerBar")).map(([,range])=>range.max-range.min)),maximum_opposed_rod_joint_span_drift_m:maximumSteerRodSpanDrift,maximum_rod_bar_closure_error_m:maximumSteerBarClosureError,maximum_inner_wheel_angle_degrees:inner*180/Math.PI,maximum_ackermann_fit_error_m:maxAckermannFitError,maximum_ackermann_relative_error:maxAckermannRelativeError,maximum_four_wheel_icr_spread_m:maxCenterSpread,maximum_four_wheel_icr_relative_spread:maxCenterRelativeSpread,maximum_crab_heading_spread_degrees:maximumCrabHeadingSpread*180/Math.PI,maximum_crab_corresponding_heading_error_degrees:maximumCrabCorrespondingError*180/Math.PI,maximum_front_mode_icr_relative_spread:maxFrontModeRelativeError,ackermann_authority:"reconstructed rack-and-rigid-bar approximation; not factory steering or crab calibration",crab_parallelism_boundary:"exact nonzero parallel crab and Ackermann split are incompatible in this continuous-rack/fixed-bar topology; crab travel is conservatively scaled and its residual toe is measured"},maximum_ackermann_center_error_m:maxAckermannFitError,maximum_reconstructed_circle_center_spread_m:maxCenterSpread,visual_circle_outside_wheel_center_radius_m:visualOutsideWheelCenterRadius,published_outside_turning_radius_m:3.66,radius_semantics:"published reference locus is unresolved and is not equated to the reconstructed wheel-center or tire/body swept envelopes",boundary:"owned presentation geometry only; not manufacturer dynamics, load, stability, interlock, service, or safety authority"};
output.steering_linkage.maximum_front_mode_wheel_angle_degrees=maximumFrontWheelAngle*180/Math.PI;
output.steering_linkage.maximum_crab_mode_wheel_angle_degrees=maximumCrabWheelAngle*180/Math.PI;
output.steering_linkage.minimum_useful_mode_angle_degrees=35;
output.steering_linkage.static_linkage_authority="one fixed axle-mounted double-rod cylinder and two invariant tie bars per axle; identical full front-rack mapping in every mode; rear rack opposite phase in circle, held in front, same phase in crab";
output.steering_linkage.scrub_boundary="front/circle ICR residuals are reconstructed diagnostics, not Ackermann acceptance gates; exact pickup coordinates and factory toe are unresolved";
output.steering_linkage.crab_parallelism_boundary="maximum dense-sweep within-axle toe is measured on the one static linkage and limited to one degree; no mode-dependent toe or hidden selector linkage";
output.minimum_boom_hose_to_rigid_tube_surface_clearance_m=minimumBoomHoseTubeClearance;
output.maximum_boom_hose_adjacent_direction_change_degrees=maximumBoomHoseDirectionChange*180/Math.PI;
output.boom_hose_nominal_centerline_length_m=JLG742_MECHANISM.boomHoseTotalLength;
output.service_line_chassis_clearance_sweep={samples:serviceClearanceSamples,lift_samples:201,telescope_samples:201,minimum_cab_surface_clearance_m:minimumServiceCabClearance,minimum_engine_proxy_surface_clearance_m:minimumServiceEngineClearance,cab_limiting_pair:serviceCabLimiter,engine_limiting_pair:serviceEngineLimiter,segments:"every BoomHose, ExtendChain, and RetractChain segment",authority:"owned reconstructed chassis proxies; not manufacturer clearance authority"};
process.stdout.write(JSON.stringify(output));
