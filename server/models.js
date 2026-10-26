import mongoose from 'mongoose';
const O=mongoose.Schema.Types.ObjectId, mixed=mongoose.Schema.Types.Mixed;
const definitions={
 batches:{name:{type:String,required:true,maxlength:120},source:{type:String,enum:['IMPORTED','SYNTHETIC'],required:true},created:String,hash:String,rows:Number,components:Number,health:Number,metadata:mixed,archived:{type:Boolean,default:false}},
 runs:{batch_id:{type:O,required:true,index:true},model_id:O,policy_id:O,stage:Number,created:String,summary:mixed},
 models:{created:String,manifest:mixed}, policies:{created:String,hash:String,config:mixed},
 reviews:{run_id:{type:O,required:true},component_id:{type:String,required:true},state:{type:String,enum:['Unreviewed','In review','Reviewed']},note:{type:String,maxlength:2000},updated:String},
 events:{timestamp:String,action:String,batch_id:O,outcome:String,details:mixed},
 reports:{kind:String,created:String,context:mixed},scenarios:{created:String,settings:mixed,baseline_batch:O,batch_id:O},settings:{key:String,value:mixed}
};
export const models=Object.fromEntries(Object.entries(definitions).map(([name,fields])=>{
 const s=new mongoose.Schema(fields,{collection:name,versionKey:false,strict:'throw'});
 if(fields.created)s.index({created:-1});
 if(name==='batches')s.index({name:1,source:1});
 if(name==='reviews')s.index({run_id:1,component_id:1},{unique:true});
 if(name==='policies')s.index({hash:1},{unique:true});
 if(name==='settings')s.index({key:1},{unique:true});
 if(name==='events')s.index({timestamp:-1});
 return [name,mongoose.model(name,s)];
}));
