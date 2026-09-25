const loginForm=document.querySelector("#login-form");
const errorBox=document.querySelector("#error");

async function loginApi(path,options={}){
  const response=await fetch(path,options);
  const body=await response.json().catch(()=>({}));
  if(!response.ok)throw Error(body.detail||"No pudimos ingresar.");
  return body;
}

async function redirectForExistingSession(){
  const savedToken=sessionStorage.getItem("maxio_token");
  if(!savedToken)return;
  try{
    const user=await loginApi("/maxio/users/me",{headers:{Authorization:`Bearer ${savedToken}`}});
    window.location.replace(user.is_admin?"/web/admin":"/web/player");
  }catch{
    sessionStorage.removeItem("maxio_token");
  }
}

loginForm.addEventListener("submit",async event=>{
  event.preventDefault();
  errorBox.textContent="";
  const values=Object.fromEntries(new FormData(loginForm));
  if(!values.username?.trim()||!values.password){
    errorBox.textContent="Ingresá tu usuario y contraseña.";
    return;
  }
  const submit=loginForm.querySelector("button");
  submit.disabled=true;
  try{
    const session=await loginApi("/auth/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(values)});
    const user=await loginApi("/maxio/users/me",{headers:{Authorization:`Bearer ${session.access_token}`}});
    sessionStorage.setItem("maxio_token",session.access_token);
    window.location.replace(user.is_admin?"/web/admin":"/web/player");
  }catch(error){
    sessionStorage.removeItem("maxio_token");
    errorBox.textContent=error.message;
    submit.disabled=false;
  }
});

redirectForExistingSession();
