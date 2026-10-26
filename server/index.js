import mongoose from 'mongoose';import {createApp} from './app.js';import {models} from './models.js';
if(!process.env.MONGO_URI||!process.env.ADMIN_TOKEN||process.env.ADMIN_TOKEN.length<32)throw new Error('Set MONGO_URI and an ADMIN_TOKEN of at least 32 characters');
if(process.env.ADMIN_TOKEN.startsWith('replace-')||process.env.VIEWER_TOKEN?.startsWith('replace-'))throw new Error('Replace placeholder access tokens');
if(process.env.VIEWER_TOKEN&&(process.env.VIEWER_TOKEN.length<32||process.env.VIEWER_TOKEN===process.env.ADMIN_TOKEN))throw new Error('Viewer token must be distinct and at least 32 characters');
await mongoose.connect(process.env.MONGO_URI,{dbName:process.env.MONGO_DB||'ess_sentinel',serverSelectionTimeoutMS:5000});await Promise.all(Object.values(models).map(m=>m.init()));
const server=createApp().listen(process.env.PORT||3001,()=>console.log('ESS API listening'));
process.on('SIGTERM',()=>server.close(async()=>{await mongoose.disconnect();process.exit(0)}));
