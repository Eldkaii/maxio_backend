var ownUsername="";
const profileWithAvatar=profile;profile=function(p){profileWithAvatar(p);ownUsername=p.name;const image=`/player/${encodeURIComponent(p.name)}/photo?${Date.now()}`;document.querySelector("#avatar").src=image;document.querySelector("#avatar-preview").src=image;document.querySelector("#name").dataset.username=p.name};
document.querySelector("#edit-avatar").addEventListener("click",()=>{ownUsername=document.querySelector("#name").dataset.username||ownUsername});
