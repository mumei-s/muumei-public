/** Bound the UI wait even when a provider is stalled before it starts fetch. */
export async function withDeadline<T>(task:PromiseLike<T>,ms=12000,message='読み込みに時間がかかっています。通信状態を確認して、もう一度お試しください。'):Promise<T>{
 let timer:ReturnType<typeof setTimeout>|undefined;
 try{return await Promise.race([Promise.resolve(task),new Promise<never>((_,reject)=>{timer=setTimeout(()=>reject(new Error(message)),ms)})])}
 finally{if(timer)clearTimeout(timer)}
}
