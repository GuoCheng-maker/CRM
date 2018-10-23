from django.shortcuts import render,HttpResponse,redirect

from rbac.models import *
from rbac.service.perssions import initial_session
# Create your views here.
def login(request):
    if request.method =="POST":
        user=request.POST.get("user")
        pwd=request.POST.get("pwd")
        user=User.objects.filter(name=user,pwd=pwd).first()
        if user:
            #将user_id放到session中。
            request.session["user_id"]=user.pk

            #注册权限到session中.
            initial_session(user,request)
            return HttpResponse("登录成功")

    return render(request,"login.html",locals())