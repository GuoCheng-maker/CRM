def initial_session(user,request):
    #方案二
    permissions = user.roles.all().values("permissions__url","permissions__group_id","permissions__action").distinct()
    # print(permissions)
    permission_dict = {}
    temp = []
    for item in permissions:
        gid = item.get('permissions__group_id')
        if not gid in permission_dict:
            permission_dict[gid] = {
                "urls": [item["permissions__url"], ],
                "actions": [item["permissions__action"], ]
            }
        else:
            permission_dict[gid]["urls"].append(item["permissions__url"])
            permission_dict[gid]["actions"].append(item["permissions__action"])
    # print(permission_dict)
    request.session["permission_dict"]=permission_dict

    #注册菜单权限
    permissions = user.roles.all().values("permissions__url", "permissions__title", "permissions__action").distinct()
    menu_permission_list=[]
    for item in permissions:
        if item["permissions__action"] == "list":
            menu_permission_list.append((item["permissions__url"],item["permissions__title"]))

    #注册到session中
    request.session["menu_permission_list"]=menu_permission_list